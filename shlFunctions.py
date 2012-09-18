# -*- coding: utf-8 -*-
"""
Module for dealing with all of the stuff the SHL deals with (INI, SHT, 
turning on/off ports, etc.)

$Rev$
$LastChangedBy$
$LastChangedDate$
"""

import os
import time
import logging
import threading

from pysnmp.entity.rfc3413.oneliner import cmdgen

from shlCommon import *
from shlThreads import *

__version__ = "0.1"
__revision__ = "$Rev$"
__all__ = ["commandExitCodes", "isHalfIncrements", "ShippingContainer", "__version__", "__revision__", "__all__"]


shlFunctionsLogger = logging.getLogger('__main__')


commandExitCodes = {0x00: 'Process accepted without error', 
				0x01: 'Invalid temperature set point', 
				0x02: 'Invalid temperature differential', 
				0x03: 'Invalid PDU rack number', 
				0x04: 'Invalid PDU port number', 
				0x05: 'Invalid PDU control keyword', 
				0x06: 'Invalid command arguments', 
				0x07: 'Blocking operation in progress', 
				0x08: 'Subsystem already initialized', 
				0x09: 'Subsystem needs to be initialized'}


def isHalfIncrements(value):
	"""
	Check if a value is one half-increments, i.e., 0.0 or 0.5, or not.  Return True
	if it is and False if its not.
	"""
	
	valueTen = value*10.0
	if valueTen % 5 != 0:
		return False
	else:
		return True


class ShippingContainer(object):
	"""
	Class for interacting with the Shelter subsystem.
	
	A note about exit codes from control commands (INI, TMP, etc.):
	  * See commandExitCodes
	"""
	
	def __init__(self, config):
		self.config = config
		
		# SHL system information
		self.subSystem = 'SHL'
		self.serialNumber = '2'
		self.version = str(__version__)
		
		# SHL system state
		self.currentState = {}
		self.currentState['status'] = 'SHUTDWN'
		self.currentState['info'] = 'Need to INI SHL'
		self.currentState['lastLog'] = 'Welcome to SHL S/N %s, version %s' % (self.serialNumber, self.version)
		
		## Operational state
		self.currentState['ready'] = False
		self.currentState['activeProcess'] = []
		self.currentState['setPoint'] = 0
		self.currentState['diffPoint'] = 0
		self.currentState['nRacks'] = 0
		self.currentState['rackPresent'] = []
		
		## Monitoring and background threads
		self.currentState['tempThreads'] = None
		self.currentState['pduThreads'] = None
		
		# Update the configuration
		self.updateConfig()
		
	def updateConfig(self, config=None):
		"""
		Update the stored configuration.
		"""
		
		if config is not None:
			self.config = config
		return True
		
	def getState(self):
		"""
		Return the current system state as a dictionary.
		"""
		
		return self.currentState
		
	def ini(self, data, config=None):
		"""
		Initialize SHL (in a separate thread).
		"""
		
		# Check for other operations in progress that could be blocking (INI or SHT)
		if 'INI' in self.currentState['activeProcess'] or 'SHT' in self.currentState['activeProcess']:
			shlFunctionsLogger.warning("INI command rejected due to process list %s", ' '.join(self.currentState['activeProcess']))
			self.currentState['lastLog'] = 'INI: %s - %s is active and blocking' % (commandExitCodes[0x07], self.currentState['activeProcess'])
			return False, 0x07
			
		# Check to see if the system has already been initialized
		if self.currentState['ready']:
			shlFunctionsLogger.warning("INI command rejected due to system already running")
			self.currentState['lastLog'] = 'INI: %s' % commandExitCodes[0x08]
			return False, 0x08
			
		# Check to see if there is a valid number of command arguments
		fields = data.strip().split('&')
		if len(fields) != 3:
			shlFunctionsLogger.warning("INI command rejected due to invalid &-separated argument count")
			self.currentState['lastLog'] = 'INI: %s' % commandExitCodes[0x06]
			return False, 0x06
		
		# Convert data to numbers/strings - there should be three
		setPoint  = float(fields[0])
		diffPoint = float(fields[1])
		nRacks    = fields[2]
		
		# Validate the temperatures
		if not isHalfIncrements(setPoint) or setPoint < self.config['TEMPMIN'] or setPoint > self.config['TEMPMAX']:
			shlFunctionsLogger.warning("INI command rejected due to invalid set point")
			self.currentState['lastLog'] = 'INI: %s' % commandExitCodes[0x01]
			return False, 0x01
			
		# Validate differential
		if not isHalfIncrements(diffPoint) or diffPoint < self.config['DIFFMIN'] or diffPoint > self.config['DIFFMAX']:
			shlFunctionsLogger.warning("INI command rejected due to invalid differential")
			self.currentState['lastLog'] = 'INI: %s' % commandExitCodes[0x02]
			return False, 0x02
			
		# Update the configuration
		self.updateConfig(config=config)
		
		# Start the process in the background
		thread = threading.Thread(target=self.__iniProcess, args=(setPoint, diffPoint, nRacks))
		thread.setDaemon(1)
		thread.start()
		
		return True, 0
		
	def __iniProcess(self, setPoint, diffPoint, nRacks):
		"""
		Thread base to initialize ASP.  Update the current system state as needed.
		"""
		
		# Start the timer
		tStart = time.time()
		
		# Update system state
		self.currentState['ready'] = False
		self.currentState['status'] = 'BOOTING'
		self.currentState['info'] = 'Running INI sequence'
		self.currentState['activeProcess'].append('INI')
		
		# Stop all threads.  If the don't exist yet, create them.
		## Temperature
		if self.currentState['tempThreads'] is not None:
			for t in self.currentState['tempThreads']:
				t.stop()
		else:
			self.currentState['tempThreads'] = []
			for c,k in enumerate(sorted(THERMOMLIST.keys())):
				v = THERMOMLIST[k]
			
				nT = Thermometer(v['IP'], v['Port'], cmdgen.CommunityData(*v['SecurityModel']),
								c+1, description=v['Description'], 
								MonitorPeriod=self.config['TEMPMONITORPERIOD'], SHLCallbackInstance=self)
				self.currentState['tempThreads'].append(nT)
		## PDUs
		if self.currentState['pduThreads'] is not None:
			for t in self.currentState['pduThreads']:
				t.stop()
		else:
			self.currentState['pduThreads'] = []
			for c,k in enumerate(sorted(PDULIST.keys())):
				v = PDULIST[k]
				
				### Figure out the PDU type
				if v['Type'] == 'TrippLite':
					PDUBaseType = TrippLite
				else:
					PDUBaseType = APC
					
				nP = PDUBaseType(v['IP'], v['Port'], cmdgen.CommunityData(*v['SecurityModel']),
								c+1, nOutlets=v['nOutlets'], description=v['Description'], 
								MonitorPeriod=self.config['RACKMONITORPERIOD'])
								
				self.currentState['pduThreads'].append(nP)
				
		# Set configuration values
		self.currentState['setPoint'] = setPoint
		self.currentState['diffPoint'] = diffPoint
		self.currentState['nRacks'] = reduce(lambda x, y: x+y, [int(i) for i in nRacks])
		self.currentState['rackPresent'] = [int(i) for i in nRacks]
		## Extend self.currentState['rackPresent'] for racks in shlCommon but not in the INI
		while len(self.currentState['pduThreads']) > len(self.currentState['rackPresent']):
			self.currentState['rackPresent'].append(0)
		
		# Print out some rack status
		shlFunctionsLogger.info('-----------------')
		shlFunctionsLogger.info(' SHL Rack Status ')
		shlFunctionsLogger.info('-----------------')
		for n,(r,p) in enumerate(zip(self.currentState['pduThreads'], self.currentState['rackPresent'])):
			shlFunctionsLogger.info('Rack #%i: %s -> %s', n+1, 'installed' if p else 'not installed', r.description)
		shlFunctionsLogger.info('Total Number of Racks: %i', self.currentState['nRacks'])
		shlFunctionsLogger.info('-----------------')
		
		# Start the monitoring threads back up
		for t in self.currentState['tempThreads']:
			t.start()
		for t,p in zip(self.currentState['pduThreads'], self.currentState['rackPresent']):
			if p:
				t.start()
			
		# Update the current state
		self.currentState['ready'] = True
		self.currentState['status'] = 'NORMAL'
		self.currentState['info'] = 'SHL ready'
		self.currentState['lastLog'] = 'INI: finished in %.3f s' % (time.time() - tStart,)
		
		shlFunctionsLogger.info("Finished the INI process in %.3f s", time.time() - tStart)
		self.currentState['activeProcess'].remove('INI')
		
		return True, 0
		
	def sht(self, mode=''):
		"""
		Issue the SHT command to SHL.
		"""
		
		# Check for other operations in progress that could be blocking (INI and SHT)
		if 'INI' in self.currentState['activeProcess'] or 'SHT' in self.currentState['activeProcess']:
			self.currentState['lastLog'] = 'SHT: %s - %s is active and blocking' % (commandExitCodes[0x07], self.currentState['activeProcess'])
			return False, 0x07
		
		# Validate SHT options
		if mode not in ("", "SCRAM", "RESTART", "SCRAM RESTART"):
			self.currentState['lastLog'] = 'SHT: %s - unknown mode %s' % (commandExitCodes[0x06], mode)
			return False, 0x06
			
		## Check if we can even run SHT
		#if not self.currentState['ready']:
			#self.currentState['lastLog'] = 'SHT: %s' % commandExitCodes[0x09]
			#return False, 0x09
		
		thread = threading.Thread(target=self.__shtProcess, kwargs={'mode': mode})
		thread.setDaemon(1)
		thread.start()
		return True, 0
		
	def __shtProcess(self, mode=""):
		"""
		Thread base to shutdown ASP.  Update the current system state as needed.
		"""
		
		# Start the timer
		tStart = time.time()
		
		# Update system state
		self.currentState['status'] = 'SHUTDWN'
		self.currentState['info'] = 'System is shutting down'
		self.currentState['activeProcess'].append('SHT')
		self.currentState['ready'] = False
		
		# Stop all threads.
		## Temperature
		if self.currentState['tempThreads'] is not None:
			for t in self.currentState['tempThreads']:
				t.stop()
		## PDUs
		if self.currentState['pduThreads'] is not None:
			for t in self.currentState['pduThreads']:
				t.stop()
			
		# Update the state
		self.currentState['status'] = 'SHUTDWN'
		self.currentState['info'] = 'System has been shut down'
		self.currentState['lastLog'] = 'System has been shut down'
		
		shlFunctionsLogger.info("Finished the SHT process in %.3f s", time.time() - tStart)
		self.currentState['activeProcess'].remove('SHT')
		
		return True, 0
		
	def tmp(self, setPoint):
		"""
		Issue the TMP command to SHL.
		"""
		
		# Check if we are ready
		if not self.currentState['ready']:
			self.currentState['lastLog'] = 'TMP: %s' % commandExitCodes[0x09]
			return False, 0x09
			
		# Validate the temperatures
		if not isHalfIncrements(setPoint) or setPoint < self.config['TEMPMIN'] or setPoint > self.config['TEMPMAX']:
			shlFunctionsLogger.warning("TMP command rejected due to invalid set point")
			self.currentState['lastLog'] = 'TMP: %s' % commandExitCodes[0x01]
			return False, 0x01
			
		thread = threading.Thread(target=self.__tmpProcess, args=(setPoint,))
		thread.setDaemon(1)
		thread.start()
		return True, 0
		
	def __tmpProcess(self, setPoint):
		"""
		Thread base to set the temperature set point.
		"""
		
		self.currentState['setPoint'] = setPoint
		
		return True, 0
		
	def dif(self, diffPoint):
		"""
		Issue the DIF command to SHL.
		"""
		
		# Check if we are ready
		if not self.currentState['ready']:
			self.currentState['lastLog'] = 'TMP: %s' % commandExitCodes[0x09]
			return False, 0x09
			
		# Make sure the differential is valid
		if not isHalfIncrements(diffPoint) or diffPoint < self.config['DIFFMIN'] or diffPoint > self.config['DIFFMAX']:
			shlFunctionsLogger.warning("DIF command rejected due to invalid differential")
			self.currentState['lastLog'] = 'DIF: %s' % commandExitCodes[0x02]
			return False, 0x02
			
		thread = threading.Thread(target=self.__difProcess, args=(diffPoint,))
		thread.setDaemon(1)
		thread.start()
		return True, 0
		
	def __difProcess(self, diffPoint):
		"""
		Thread base to set the temperature differential set point.
		"""
		
		self.currentState['diffPoint'] = diffPoint
		
		return True, 0
		
	def pwr(self, rack, port, control):
		"""
		Issue the PWR command to SHL.
		"""
		
		# Check if we are ready
		if not self.currentState['ready']:
			self.currentState['lastLog'] = 'TMP: %s' % commandExitCodes[0x09]
			return False, 0x09
			
		# Validate the rack,port,control combo
		## Rack
		if rack == 0 or rack > self.currentState['nRacks']:
			shlFunctionsLogger.warning("PWR command rejected due to invalid rack number")
			self.currentState['lastLog'] = 'PWR: %s - rack' % commandExitCodes[0x03]
			return False, 0x03
		if not self.currentState['rackPresent'][rack-1]:
			shlFunctionsLogger.warning("PWR command rejected due to rack #%i not present", rack)
			self.currentState['lastLog'] = 'PWR: %s - rack' % commandExitCodes[0x03]
			return False, 0x03
		## Port
		if port not in self.currentState['pduThreads'][rack-1].status.keys():
			shlFunctionsLogger.warning("PWR command rejected due to invalid port number")
			self.currentState['lastLog'] = 'PWR: %s - port' % commandExitCodes[0x04]
			return False, 0x04
		## Control word
		if control not in ('ON ', 'OFF'):
			shlFunctionsLogger.warning("PWR command rejected due to invalid control word")
			self.currentState['lastLog'] = 'PWR: %s' % commandExitCodes[0x05]
			return False, 0x05
			
		thread = threading.Thread(target=self.__pwrProcess, args=(rack, port, control))
		thread.setDaemon(1)
		thread.start()
		return True, 0
		
	def __pwrProcess(self, rack, port, control):
		"""
		Thread base for changing the power status of an outlet.
		"""
		
		self.currentState['pduThreads'][rack-1].setStatus(outlet=port, status=control)
		
		return True, 0
		
	def getMeanTemperature(self, DegreesF=True):
		"""
		Return the current mean shelter temperature as a two-element tuple 
		(success, value) where success is a boolean related to if the temperature 
		values were found.  See the currentState['lastLog'] entry for the reason for 
		failure if the returned success value is False.
		"""
		
		i = 0
		meanTemp = 0
		for t in self.currentState['tempThreads']:
			# Make sure the monitoring thread is running
			if t.alive.isSet():
				meanTemp += t.getTemperature(DegreesF=DegreesF)
				i += 1
				
		# Make sure we have actual values to average
		if i == 0:
			self.currentState['lastLog'] = 'No temperature monitoring threads are running'
			return False, 0
		
		meanTemp /= float(i)
		
		return True, meanTemp
		
	def getOutletCount(self, rack):
		"""
		Given a rack return the current power draw of all outlets as a two-elements 
		tuple (success, value) where success is a boolean related to if the outlet
		count was found.  See the currentState['lastLog'] entry for the reason for 
		failure if the returned success value is False.
		"""
		
		# Check the rack number
		if rack == 0 or rack > self.currentState['nRacks']:
			self.currentState['lastLog'] = 'Invalid rack number %i' % rack
			return False, 0
		if not self.currentState['rackPresent'][rack-1]:
			self.currentState['lastLog'] = 'Rack #%i not present during INI call' % rack
			return False, 0
			
		return True, self.currentState['pduThreads'][rack-1].nOutlets
		
	def getPowerState(self, rack, port):
		"""
		Given a rack, port combo, return the current power state of the outlets as a
		two-elements tuple (success, value) where success is a boolean related to if 
		the state was found.  See the currentState['lastLog'] entry for the reason for 
		failure if the returned success value is False.
		"""
		
		# Check the rack number
		if rack == 0 or rack > self.currentState['nRacks']:
			self.currentState['lastLog'] = 'Invalid rack number %i' % rack
			return False, 'UNK'
		if not self.currentState['rackPresent'][rack-1]:
			self.currentState['lastLog'] = 'Rack #%i not present during INI call' % rack
			return False, 'UNK'
			
		# Check the port (outlet) number
		if port not in self.currentState['pduThreads'][rack-1].status.keys():
			self.currentState['lastLog'] = 'Invalid port number %i for rack %i' % (port, rack)
			return False, 'UNK'
		
		return True, self.currentState['pduThreads'][rack-1].getStatus(outlet=port)
		
	def getInputFrequency(self, rack):
		"""
		Given a rack return the input line frequency as a two-element tuple 
		(success, value) where success is a boolean related to if the frequency was 
		found.  See the currentState['lastLog'] entry for the reason for failure if 
		the returned success value is False.
		"""
		
		# Check the rack number
		if rack == 0 or rack > self.currentState['nRacks']:
			self.currentState['lastLog'] = 'Invalid rack number %i' % rack
			return False, 0
		if not self.currentState['rackPresent'][rack-1]:
			self.currentState['lastLog'] = 'Rack #%i not present during INI call' % rack
			return False, 0
			
		# Make sure the monitoring thread is running
		if not self.currentState['pduThreads'][rack-1].alive.isSet():
			self.currentState['lastLog'] = 'Monitoring thread for Rack #%i is not running'
			return False, 0
			
		return True, self.currentState['pduThreads'][rack-1].getFrequency()
		
	def getInputVoltage(self, rack):
		"""
		Given a rack return the input line voltage of all outlets as a two-elements 
		tuple (success, value) where success is a boolean related to if the voltage 
		was found.  See the currentState['lastLog'] entry for the reason for failure 
		if the returned success value is False.
		"""
		
		# Check the rack number
		if rack == 0 or rack > self.currentState['nRacks']:
			self.currentState['lastLog'] = 'Invalid rack number %i' % rack
			return False, 0
		if not self.currentState['rackPresent'][rack-1]:
			self.currentState['lastLog'] = 'Rack #%i not present during INI call' % rack
			return False, 0
			
		# Make sure the monitoring thread is running
		if not self.currentState['pduThreads'][rack-1].alive.isSet():
			self.currentState['lastLog'] = 'Monitoring thread for Rack #%i is not running'
			return False, 0
			
		return True, self.currentState['pduThreads'][rack-1].getVoltage()
		
	def getCurrentDraw(self, rack):
		"""
		Given a rack return the current power draw of all outlets as a two-elements 
		tuple (success, value) where success is a boolean related to if the current 
		draw was found.  See the currentState['lastLog'] entry for the reason for 
		failure if the returned success value is False.
		"""
		
		# Check the rack number
		if rack == 0 or rack > self.currentState['nRacks']:
			self.currentState['lastLog'] = 'Invalid rack number %i' % rack
			return False, 0
		if not self.currentState['rackPresent'][rack-1]:
			self.currentState['lastLog'] = 'Rack #%i not present during INI call' % rack
			return False, 0
			
		# Make sure the monitoring thread is running
		if not self.currentState['pduThreads'][rack-1].alive.isSet():
			self.currentState['lastLog'] = 'Monitoring thread for Rack #%i is not running'
			return False, 0
			
		return True, self.currentState['pduThreads'][rack-1].getCurrent()
		
	def processCriticalTemperature(self):
		"""
		Deal with a critical shelter temperature.  We are in error if this happens 
		and the critical list of ports are powered off.
		"""
		
		criticalPortList = ';'.join(["rack %i, port %i" % (r,p) for r,p in CRITICAL_LIST])
		if len(CRITICAL_LIST) == 0:
			criticalPortList = 'None listed'
		
		self.currentState['status'] = 'ERROR'
		self.currentState['info'] = 'Shelter temperature %.2f >= %.2f F, shutting down critical ports: %s' % (currTemp, CRITICAL_TEMP, criticalPortList)
			
		for rack,port in CRITICAL_LIST:
			try:
				good, status = self.getPowerState(rack, port)
				if status != 'OFF':
					self.pwr(rack, port, 'OFF')
			except:
				pass
				
		shlFunctionsLogger.critical('Shelter temperature %.2f >= %.2f F, shutting down critical ports: %s', currTemp, CRITICAL_TEMP, criticalPortList)
			
		return True
		
	def processSNMPUnrechable(self, unreachableList):
		"""
		Deal with unreachable devices.
		"""
		
		# If there isn't anything in the unreachable list, quietly ignore it and clear the WARNING condition
		if len(unreachableList) == 0:
			if self.currentState['status'] == 'WARNING':
				self.currentState['status'] = 'NORMAL'
				self.currentState['info'] = 'Warning condition cleared, system operating normally'
			return False
			
		# Otherwise set a warning
		else:
			if self.currentState['status'] in ('NORMAL', 'WARNING'):
				self.currentState['status'] = 'WARNING'
				self.currentState['info'] = 'SUMMARY! %i Devices unreachable via SNMP' % len(unreachableList)
				
			return True
			