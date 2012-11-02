# -*- coding: utf-8 -*-
"""
Background threads to interacting with temperature sensors and PDUs.

$Rev$
$LastChangedBy$
$LastChangedDate$
"""

import os
import sys
import time
import logging
import sqlite3
import threading
import traceback
from datetime import datetime
try:
        import cStringIO as StringIO
except ImportError:
        import StringIO

from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto import rfc1902

from shlCommon import CRITICAL_TEMP

__version__ = "0.3"
__revision__ = "$Rev$"
__all__ = ['Thermometer', 'PDU', 'TrippLite', 'APC', 'TrippLiteUPS', 'Weather', '__version__', '__revision__', '__all__']


shlThreadsLogger = logging.getLogger('__main__')


# Create a semaphore to make sure not too many threads poll all at once
SNMPLock = threading.Semaphore(2)


class Thermometer(object):
	"""
	Class for communicating with a network thermometer via SNMP and regularly polling
	the temperature.  The temperature value is stored in the "temp" attribute.
	"""

	oidTemperatureEntry = (1,3,6,1,4,1,22626,1,5,2,1,2,0)

	def __init__(self, ip, port, community, id, description=None, SHLCallbackInstance=None, MonitorPeriod=5.0):
		self.ip = ip
		self.port = port
		self.id = id
		self.description = description
		self.SHLCallbackInstance = SHLCallbackInstance
		self.MonitorPeriod = MonitorPeriod

		# Setup the SNMP UDP connection
		self.community = community
		self.network = cmdgen.UdpTransportTarget((self.ip, self.port), timeout=1.0, retries=3)

		# Setup threading
		self.thread = None
		self.alive = threading.Event()
		self.lastError = None
		
		# Setup temperature
		self.temp = None
		
	def __str__(self):
		t = self.getTemperature(DegreesF=True)
		
		output = ''
		if description is None:
			output = "Thermometer at IP %s: " % self.ip
		else:
			output = "Thermometer '%s' at IP %s: " % (self.description, self.ip)
		
		if t is None:
			output += "current temperature is unknown"
		else:
			output += "current temperature is %.1f F" % t
			
		return output

	def start(self):
		"""
		Start the monitoring thread.
		"""

		if self.thread is not None:
			self.stop()
			
		self.thread = threading.Thread(target=self.monitorThread)
		self.thread.setDaemon(1)
		self.alive.set()
		self.thread.start()

	def stop(self):
		"""
		Stop the monitor thread, waiting until it's finished.
		"""

		if self.thread is not None:
			self.alive.clear()          #clear alive event for thread
			self.thread.join()          #wait until thread has finished
			self.thread = None
			self.lastError = None

	def monitorThread(self):
		"""
		Create a monitoring thread for the temperature.
		"""

		while self.alive.isSet():
			tStart = time.time()
			
			SNMPLock.acquire()
			
			# Read the networked thermometer and store values to temp.
			# NOTE: self.temp is in Celsius
			try:
				errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(self.community, self.network, self.oidTemperatureEntry)
				
				# Check for SNMP errors
				if errorIndication:
					raise RuntimeError("SNMP error indication: %s" % errorIndication)
				if errorStatus:
					raise RuntimeError("SNMP error status: %s" % errorStatus.prettyPrint())
				
				name, value = varBinds[0]
				
				self.temp = float(unicode(value))
				self.lastError = None
				
			except Exception, e:
				exc_type, exc_value, exc_traceback = sys.exc_info()
				shlThreadsLogger.error("%s: monitorThread failed with: %s at line %i", type(self).__name__, str(e), traceback.tb_lineno(exc_traceback))
				
				## Grab the full traceback and save it to a string via StringIO
				fileObject = StringIO.StringIO()
				traceback.print_tb(exc_traceback, file=fileObject)
				tbString = fileObject.getvalue()
				fileObject.close()
				## Print the traceback to the logger as a series of DEBUG messages
				for line in tbString.split('\n'):
					shlThreadsLogger.debug("%s", line)
				
				self.temp = None
				self.lastError = str(e)
				
			SNMPLock.release()
			
			toDataLog = '%.2f,%.2f' % (time.time(), self.temp if self.temp is not None else -1)
			fh = open('/data/thermometer%02i.txt' % self.id, 'a+')
			fh.write('%s\n' % toDataLog)
			fh.close()
				
			# Stop time
			tStop = time.time()
			shlThreadsLogger.debug('Finished updating temperature in %.3f seconds', tStop - tStart)
			
			# Make sure we aren't critical
			if self.SHLCallbackInstance is not None and self.temp is not None:
				if 1.8*self.temp  + 32 >= CRITICAL_TEMP:
					self.SHLCallbackInstance.processCriticalTemperature()
			
			# Sleep for a bit
			sleepCount = 0
			sleepTime = self.MonitorPeriod - (tStop - tStart)
			while (self.alive.isSet() and sleepCount < sleepTime):
				time.sleep(0.2)
				sleepCount += 0.2

	def getTemperature(self, DegreesF=True):
		"""
		Convenience function to get the temperature.
		"""

		if self.temp is None:
			return None

		if DegreesF:
			return 1.8*self.temp + 32
		else:
			return self.temp


class PDU(object):
	"""
	Class for communicating with a network PDU via SNMP and regularly polling
	the current and port states.
	
	.. note::
		This way this class is written the attributes "oidCurrentEntry", 
		"oidOutletStuatusBaseEntry", and "oidOutletChangeEntry" need to be over-
		ridden with the appropriate values when it is sub-classed.
	"""
	
	isUPS = False
	
	oidFrequencyEntry = None
	oidVoltageEntry = None
	oidCurrentEntry = None
	oidOutletStatusBaseEntry = None
	oidOutletChangeBaseEntry = None
	
	outletStatusCodes = {1: "OFF", 2: "ON"}
	
	def __init__(self, ip, port, community, id, nOutlets=8, description=None, SHLCallbackInstance=None, MonitorPeriod=1.0):
		self.ip = ip
		self.port = port
		self.id = id
		self.description = description
		self.SHLCallbackInstance = SHLCallbackInstance
		self.MonitorPeriod = MonitorPeriod
		
		# Setup the outlets, their currents and status codes
		self.nOutlets = nOutlets
		self.voltage = None
		self.current = None
		self.frequency = None
		self.status = {}
		for i in xrange(1, self.nOutlets+1):
			self.status[i] = "UNK"

		# Setup the SNMP UDP connection
		self.community = community
		self.network = cmdgen.UdpTransportTarget((self.ip, self.port), timeout=1.0, retries=3)
		
		# Setup threading
		self.thread = None
		self.alive = threading.Event()
		self.lastError = None
		
	def __str__(self):
		sString = ','.join(self.status)
		cString = "%.1f Amps" % self.current if self.current is not None else "Unknown"
		
		if description is None:
			return "PDU at IP %s:  outlet status: %s, current: %s" % (self.ip, sString, cString)
		else:
			return "PDU '%s' at IP %s:  outlet status: %s, current: %s" % (self.description, self.ip, sString, cString)

	def start(self):
		"""
		Start the monitoring thread.
		"""

		if self.thread is not None:
			self.stop()
			
		self.thread = threading.Thread(target=self.monitorThread)
		self.thread.setDaemon(1)
		self.alive.set()
		self.thread.start()

	def stop(self):
		"""
		Stop the monitor thread, waiting until it's finished.
		"""

		if self.thread is not None:
			self.alive.clear()          #clear alive event for thread
			self.thread.join()          #wait until thread has finished
			self.thread = None
			self.lastError = None

	def monitorThread(self):
		"""
		Create a monitoring thread for the current and outlet states.  Current 
		is stored in the "current" attribute and the outlets in the "status"
		attribute.
		"""

		while self.alive.isSet():
			tStart = time.time()
			
			SNMPLock.acquire()
			
			if self.oidFrequencyEntry is not None:
				try:
					# Get the current input frequency
					errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(self.community, self.network, self.oidFrequencyEntry)
					
					# Check for SNMP errors
					if errorIndication:
						raise RuntimeError("SNMP error indication: %s" % errorIndication)
					if errorStatus:
						raise RuntimeError("SNMP error status: %s" % errorStatus.prettyPrint())
							
					name, PWRfreq = varBinds[0]
					self.frequency = float(unicode(PWRfreq)) / 10.0
					self.lastError = None
					
				except Exception, e:
					exc_type, exc_value, exc_traceback = sys.exc_info()
					shlThreadsLogger.error("PDU %s: monitorThread failed with: %s at line %i", str(self.id), str(e), traceback.tb_lineno(exc_traceback))
					
					## Grab the full traceback and save it to a string via StringIO
					fileObject = StringIO.StringIO()
					traceback.print_tb(exc_traceback, file=fileObject)
					tbString = fileObject.getvalue()
					fileObject.close()
					## Print the traceback to the logger as a series of DEBUG messages
					for line in tbString.split('\n'):
						shlThreadsLogger.debug("%s", line)
					
					self.frequency = None
					self.lastError = str(e)
			
			if self.oidVoltageEntry is not None:
				try:
					# Get the current input voltage
					errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(self.community, self.network, self.oidVoltageEntry)
					
					# Check for SNMP errors
					if errorIndication:
						raise RuntimeError("SNMP error indication: %s" % errorIndication)
					if errorStatus:
						raise RuntimeError("SNMP error status: %s" % errorStatus.prettyPrint())
							
					name, PWRvoltage = varBinds[0]
					self.voltage = float(unicode(PWRvoltage))
					self.lastError = None
					
				except Exception, e:
					exc_type, exc_value, exc_traceback = sys.exc_info()
					shlThreadsLogger.error("PDU %s: monitorThread failed with: %s at line %i", str(self.id), str(e), traceback.tb_lineno(exc_traceback))
					
					## Grab the full traceback and save it to a string via StringIO
					fileObject = StringIO.StringIO()
					traceback.print_tb(exc_traceback, file=fileObject)
					tbString = fileObject.getvalue()
					fileObject.close()
					## Print the traceback to the logger as a series of DEBUG messages
					for line in tbString.split('\n'):
						shlThreadsLogger.debug("%s", line)
					
					if self.lastError is not None:
						self.lastError = "%s; %s" % (self.lastError, str(e))
					else:
						self.lastError = str(e)
					self.voltage = None
			
			if self.oidCurrentEntry is not None:
				try:
					# Get the current draw of outlet #(i+1)
					errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(self.community, self.network, self.oidCurrentEntry)
					
					# Check for SNMP errors
					if errorIndication:
						raise RuntimeError("SNMP error indication: %s" % errorIndication)
					if errorStatus:
						raise RuntimeError("SNMP error status: %s" % errorStatus.prettyPrint())
							
					name, PWRcurrent = varBinds[0]
					self.current = float(unicode(PWRcurrent)) / 10
					self.lastError = None
					
				except Exception, e:
					exc_type, exc_value, exc_traceback = sys.exc_info()
					shlThreadsLogger.error("PDU %s: monitorThread failed with: %s at line %i", str(self.id), str(e), traceback.tb_lineno(exc_traceback))
					
					## Grab the full traceback and save it to a string via StringIO
					fileObject = StringIO.StringIO()
					traceback.print_tb(exc_traceback, file=fileObject)
					tbString = fileObject.getvalue()
					fileObject.close()
					## Print the traceback to the logger as a series of DEBUG messages
					for line in tbString.split('\n'):
						shlThreadsLogger.debug("%s", line)
					
					if self.lastError is not None:
						self.lastError = "%s; %s" % (self.lastError, str(e))
					else:
						self.lastError = str(e)
					self.current = None
			
			if self.oidOutletStatusBaseEntry is not None:
				for i in xrange(1, self.nOutlets+1):
					# Get the status of outlet #(i+1).
					# NOTE:  Since the self.oidOutletStatusBaseEntry is just a base entry, 
					# we need to append on the outlet number (1-indexed) before we can use
					# it
					oidOutletStatusEntry = self.oidOutletStatusBaseEntry+(i,)
					
					try:
						errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(self.community, self.network, oidOutletStatusEntry)
						
						# Check for SNMP errors
						if errorIndication:
							raise RuntimeError("SNMP error indication: %s" % errorIndication)
						if errorStatus:
							raise RuntimeError("SNMP error status: %s" % errorStatus.prettyPrint())
						
						name, PortStatus = varBinds[0]
						PortStatus = int(unicode(PortStatus))
						
						try:
							self.status[i] = self.outletStatusCodes[PortStatus]
						except KeyError:
							self.status[i] = "UNK"
						if self.lastError is not None:
							self.lastError = None
							
					except Exception, e:
						exc_type, exc_value, exc_traceback = sys.exc_info()
						shlThreadsLogger.error("%s %s: monitorThread failed with: %s at line %i", type(self).__name__, str(self.id), str(e), traceback.tb_lineno(exc_traceback))
						
						## Grab the full traceback and save it to a string via StringIO
						fileObject = StringIO.StringIO()
						traceback.print_tb(exc_traceback, file=fileObject)
						tbString = fileObject.getvalue()
						fileObject.close()
						## Print the traceback to the logger as a series of DEBUG messages
						for line in tbString.split('\n'):
							shlThreadsLogger.debug("%s", line)
						
						if self.lastError is not None:
							self.lastError = "%s; %s" % (self.lastError, str(e))
						else:
							self.lastError = str(e)
						self.status[i] = "UNK"
			
			SNMPLock.release()
			
			toDataLog = "%.2f,%.2f,%.2f,%.2f" % (time.time(), self.frequency if self.frequency is not None else -1, self.voltage if self.voltage is not None else -1, self.current if self.current is not None else -1)
			fh = open('/data/rack%02i.txt' % self.id, 'a+')
			fh.write('%s\n' % toDataLog)
			fh.close()
			
			# Stop time
			tStop = time.time()
			shlThreadsLogger.debug('Finished updating current and port status in %.3f seconds', tStop - tStart)
			
			# Sleep for a bit
			sleepCount = 0
			sleepTime = self.MonitorPeriod - (tStop - tStart)
			while (self.alive.isSet() and sleepCount < sleepTime):
				time.sleep(0.2)
				sleepCount += 0.2

	def getFrequency(self):
		"""
		Return the input frequency of the DPU in Hz or None if it is unknown.
		"""
		
		return self.frequency

	def getVoltage(self):
		"""
		Return the input voltage of the PDU in volts AC or None if it is unknown.
		"""
		
		return self.voltage

	def getCurrent(self):
		"""
		Return the current associated with the PDU in amps or None if it is unknown.
		"""
		
		return self.current
	
	def getStatus(self, outlet=None):
		"""
		Return the status associated with a particular outlet or, if outlet
		is None, a list of all outlets.
		"""

		if outlet is None:
			return [self.status[k] for k in sorted(self.status.keys())]
		else:
			return self.status[outlet]
	
	def setStatus(self, outlet=None, status=None):
		"""
		Change the status of an outlet to a new value or, if outlet is None,
		change the status of all outlets.  Return True on successful completion
		of the change and False otherwise.
		"""
		
		if status is None:
			return False
			
		if outlet is None:
			# If outlet is None, loop over all outlets and return a list of
			# the individual operation result codes
			ret = [False]*self.nOutlets
			for i in xrange(1, self.nOutlets+1):
				ret[i] = self.setStatus(outlet=i, status=status)
				
			return ret
		else:
			# First, convert the string status code to a number via the 
			# self.outletStatusCodes dictionary.  We default to -1 so we
			# can catch bad values.
			numericCode = -1
			for k in self.outletStatusCodes.keys():
				if self.outletStatusCodes[k] == status.upper().strip():
					numericCode = k
					break
					
			if numericCode < 0:
				return False
			else:
				# NOTE:  Since the self.oidOutletChangeBaseEntry is just a base entry, 
				# we need to append on the outlet number (1-indexed) before we can use
				# it
				oidOutletChangeEntry = self.oidOutletChangeBaseEntry + (outlet,)
				
				try:
					errorIndication, errorStatus, errorIndex, varBinds =                                                                          cmdgen.CommandGenerator().setCmd(self.community, self.network, (oidOutletChangeEntry, rfc1902.Integer(numericCode)))
					
				except Exception, e:
					exc_type, exc_value, exc_traceback = sys.exc_info()
					shlThreadsLogger.error("%s: setStatus failed with: %s at line %i", type(self).__name__, str(e), traceback.tb_lineno(exc_traceback))
						
					## Grab the full traceback and save it to a string via StringIO
					fileObject = StringIO.StringIO()
					traceback.print_tb(exc_traceback, file=fileObject)
					tbString = fileObject.getvalue()
					fileObject.close()
					## Print the traceback to the logger as a series of DEBUG messages
					for line in tbString.split('\n'):
						shlThreadsLogger.debug("%s", line)
						
					return False
				
				return True


class TrippLite(PDU):
	"""
	Sub-class of the PDU class for TrippLite PDUs.
	"""
	
	def __init__(self, ip, port, community, id, nOutlets=8, description=None, MonitorPeriod=1.0):
		super(TrippLite, self).__init__(ip, port, community, id, nOutlets=nOutlets, description=description, MonitorPeriod=MonitorPeriod)
		
		# Setup the OID values
		self.oidFrequencyEntry = (1,3,6,1,2,1,33,1,3,3,1,2)
		self.oidVoltageEntry = (1,3,6,1,2,1,33,1,3,3,1,3)
		self.oidCurrentEntry = (1,3,6,1,2,1,33,1,4,4,1,3,1)
		self.oidOutletStatusBaseEntry = (1,3,6,1,4,1,850,100,1,10,2,1,2,)
		self.oidOutletChangeBaseEntry = (1,3,6,1,4,1,850,100,1,10,2,1,4,)
		
		# Setup the status codes
		self.outletStatusCodes = {1: "OFF", 2: "ON"}


class APC(PDU):
	"""
	Sub-class of the PDU class for the APC PDU on PASI.
	"""
	
	def __init__(self, ip, port, community, id, nOutlets=8, description=None, MonitorPeriod=1.0):
		super(APC, self).__init__(ip, port, community, id, nOutlets=nOutlets, description=description, MonitorPeriod=MonitorPeriod)
		
		# Setup the OID values
		self.oidFrequencyEntry = None
		self.oidVoltageEntry = None
		self.oidCurrentEntry = None
		self.oidOutletStatusBaseEntry = (1,3,6,1,4,1,318,1,1,4,4,2,1,3,)
		self.oidOutletChangeBaseEntry = (1,3,6,1,4,1,318,1,1,4,4,2,1,3,)
		
		# Setup the status codes
		self.outletStatusCodes = {1: "ON", 2: "OFF"}


class TrippLiteUPS(PDU):
	"""
	Sub-class of the PDU class for TrippLite UPSs.
	
	MIB sources:
	  http://www.coisoftware.com/support/?wtpaper=011_snmp_tags
	  http://www.simpleweb.org/ietf/mibs/modules/IETF/txt/UPS-MIB
	"""
	
	def __init__(self, ip, port, community, id, nOutlets=8, description=None, MonitorPeriod=1.0):
		super(TrippLiteUPS, self).__init__(ip, port, community, id, nOutlets=nOutlets, description=description, MonitorPeriod=MonitorPeriod)
		
		# This is a UPS
		self.isUPS = True
		
		# Setup the OID values
		self.oidFrequencyEntry = (1,3,6,1,2,1,33,1,3,3,1,2,1)
		self.oidVoltageEntry = (1,3,6,1,2,1,33,1,3,3,1,3,1)
		self.oidCurrentEntry = (1,3,6,1,2,1,33,1,4,4,1,3,1)
		self.oidUPSOutputEntry = (1,3,6,1,2,1,33,1,4,1,0)
		self.oidBatteryChargeEntry = (1,3,6,1,2,1,33,1,2,4,0)
		self.oidBatteryStatusEntry = (1,3,6,1,2,1,33,1,2,1,0)
		self.oidOutletStatusBaseEntry = (1,3,6,1,4,1,850,100,1,10,2,1,2,)
		self.oidOutletChangeBaseEntry = (1,3,6,1,4,1,850,100,1,10,2,1,4,)
		
		# Setup the status codes
		self.batteryStatusCodes = {1: "Unknown", 2: "Normal", 3: "Low", 4: "Depleted"}
		self.upsOutputCodes = {1: "Other", 2: "None", 3: "Normal", 4: "Bypass", 5: "Battery", 6: "Booster", 7: "Reducer"}
		self.outletStatusCodes = {1: "OFF", 2: "ON"}
		
		# Setup holders
		self.upsOutput = 'UNK'
		self.batteryStatus = 'UNK'
		self.batteryCharge = 0.0
		
	def monitorThread(self):
		"""
		Create a monitoring thread for the current and outlet states.  Current 
		is stored in the "current" attribute and the outlets in the "status"
		attribute.
		"""

		while self.alive.isSet():
			tStart = time.time()
			
			SNMPLock.acquire()
			
			if self.oidFrequencyEntry is not None:
				try:
					# Get the current input frequency
					errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(self.community, self.network, self.oidFrequencyEntry)
					
					# Check for SNMP errors
					if errorIndication:
						raise RuntimeError("SNMP error indication: %s" % errorIndication)
					if errorStatus:
						raise RuntimeError("SNMP error status: %s" % errorStatus.prettyPrint())
							
					name, PWRfreq = varBinds[0]
					self.frequency = float(unicode(PWRfreq)) / 10.0
					self.lastError = None
					
				except Exception, e:
					exc_type, exc_value, exc_traceback = sys.exc_info()
					shlThreadsLogger.error("PDU %s: monitorThread failed with: %s at line %i", str(self.id), str(e), traceback.tb_lineno(exc_traceback))
					
					## Grab the full traceback and save it to a string via StringIO
					fileObject = StringIO.StringIO()
					traceback.print_tb(exc_traceback, file=fileObject)
					tbString = fileObject.getvalue()
					fileObject.close()
					## Print the traceback to the logger as a series of DEBUG messages
					for line in tbString.split('\n'):
						shlThreadsLogger.debug("%s", line)
					
					self.frequency = None
					self.lastError = str(e)
			
			if self.oidVoltageEntry is not None:
				try:
					# Get the current input voltage
					errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(self.community, self.network, self.oidVoltageEntry)
					
					# Check for SNMP errors
					if errorIndication:
						raise RuntimeError("SNMP error indication: %s" % errorIndication)
					if errorStatus:
						raise RuntimeError("SNMP error status: %s" % errorStatus.prettyPrint())
							
					name, PWRvoltage = varBinds[0]
					self.voltage = float(unicode(PWRvoltage))
					self.lastError = None
					
				except Exception, e:
					exc_type, exc_value, exc_traceback = sys.exc_info()
					shlThreadsLogger.error("PDU %s: monitorThread failed with: %s at line %i", str(self.id), str(e), traceback.tb_lineno(exc_traceback))
					
					## Grab the full traceback and save it to a string via StringIO
					fileObject = StringIO.StringIO()
					traceback.print_tb(exc_traceback, file=fileObject)
					tbString = fileObject.getvalue()
					fileObject.close()
					## Print the traceback to the logger as a series of DEBUG messages
					for line in tbString.split('\n'):
						shlThreadsLogger.debug("%s", line)
					
					if self.lastError is not None:
						self.lastError = "%s; %s" % (self.lastError, str(e))
					else:
						self.lastError = str(e)
					self.voltage = None
			
			if self.oidCurrentEntry is not None:
				try:
					# Get the current draw of outlet #(i+1)
					errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(self.community, self.network, self.oidCurrentEntry)
					
					# Check for SNMP errors
					if errorIndication:
						raise RuntimeError("SNMP error indication: %s" % errorIndication)
					if errorStatus:
						raise RuntimeError("SNMP error status: %s" % errorStatus.prettyPrint())
							
					name, PWRcurrent = varBinds[0]
					self.current = float(unicode(PWRcurrent)) / 10
					self.lastError = None
					
				except Exception, e:
					exc_type, exc_value, exc_traceback = sys.exc_info()
					shlThreadsLogger.error("PDU %s: monitorThread failed with: %s at line %i", str(self.id), str(e), traceback.tb_lineno(exc_traceback))
					
					## Grab the full traceback and save it to a string via StringIO
					fileObject = StringIO.StringIO()
					traceback.print_tb(exc_traceback, file=fileObject)
					tbString = fileObject.getvalue()
					fileObject.close()
					## Print the traceback to the logger as a series of DEBUG messages
					for line in tbString.split('\n'):
						shlThreadsLogger.debug("%s", line)
					
					if self.lastError is not None:
						self.lastError = "%s; %s" % (self.lastError, str(e))
					else:
						self.lastError = str(e)
					self.current = None
					
			if self.oidUPSOutputEntry is not None:
				try:
					# Get the current draw of outlet #(i+1)
					errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(self.community, self.network, self.oidUPSOutputEntry)
					
					# Check for SNMP errors
					if errorIndication:
						raise RuntimeError("SNMP error indication: %s" % errorIndication)
					if errorStatus:
						raise RuntimeError("SNMP error status: %s" % errorStatus.prettyPrint())
							
					name, UPSoutput = varBinds[0]
					try:
						self.upsOutput = self.upsOutputCodes[int(unicode(UPSoutput))]
					except KeyError:
						self.upsOutput = "UNK"
					self.lastError = None
					
				except Exception, e:
					exc_type, exc_value, exc_traceback = sys.exc_info()
					shlThreadsLogger.error("PDU %s: monitorThread failed with: %s at line %i", str(self.id), str(e), traceback.tb_lineno(exc_traceback))
					
					## Grab the full traceback and save it to a string via StringIO
					fileObject = StringIO.StringIO()
					traceback.print_tb(exc_traceback, file=fileObject)
					tbString = fileObject.getvalue()
					fileObject.close()
					## Print the traceback to the logger as a series of DEBUG messages
					for line in tbString.split('\n'):
						shlThreadsLogger.debug("%s", line)
					
					if self.lastError is not None:
						self.lastError = "%s; %s" % (self.lastError, str(e))
					else:
						self.lastError = str(e)
					self.upsOutput = None
					
			if self.oidBatteryChargeEntry is not None:
				try:
					# Get the current draw of outlet #(i+1)
					errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(self.community, self.network, self.oidBatteryChargeEntry)
					
					# Check for SNMP errors
					if errorIndication:
						raise RuntimeError("SNMP error indication: %s" % errorIndication)
					if errorStatus:
						raise RuntimeError("SNMP error status: %s" % errorStatus.prettyPrint())
							
					name, BTYcharge = varBinds[0]
					self.batteryCharge = float(unicode(BTYcharge))
					self.lastError = None
					
				except Exception, e:
					exc_type, exc_value, exc_traceback = sys.exc_info()
					shlThreadsLogger.error("PDU %s: monitorThread failed with: %s at line %i", str(self.id), str(e), traceback.tb_lineno(exc_traceback))
					
					## Grab the full traceback and save it to a string via StringIO
					fileObject = StringIO.StringIO()
					traceback.print_tb(exc_traceback, file=fileObject)
					tbString = fileObject.getvalue()
					fileObject.close()
					## Print the traceback to the logger as a series of DEBUG messages
					for line in tbString.split('\n'):
						shlThreadsLogger.debug("%s", line)
					
					if self.lastError is not None:
						self.lastError = "%s; %s" % (self.lastError, str(e))
					else:
						self.lastError = str(e)
					self.batteryCharge = None
					
			if self.oidBatteryStatusEntry is not None:
				try:
					# Get the current draw of outlet #(i+1)
					errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(self.community, self.network, self.oidBatteryStatusEntry)
					
					# Check for SNMP errors
					if errorIndication:
						raise RuntimeError("SNMP error indication: %s" % errorIndication)
					if errorStatus:
						raise RuntimeError("SNMP error status: %s" % errorStatus.prettyPrint())
							
					name, BTYstatus = varBinds[0]
					try:
						self.batteryStatus = self.batteryStatusCodes[int(unicode(BTYstatus))]
					except KeyError:
						self.batteryStatus = "UNK"
					self.lastError = None
					
				except Exception, e:
					exc_type, exc_value, exc_traceback = sys.exc_info()
					shlThreadsLogger.error("PDU %s: monitorThread failed with: %s at line %i", str(self.id), str(e), traceback.tb_lineno(exc_traceback))
					
					## Grab the full traceback and save it to a string via StringIO
					fileObject = StringIO.StringIO()
					traceback.print_tb(exc_traceback, file=fileObject)
					tbString = fileObject.getvalue()
					fileObject.close()
					## Print the traceback to the logger as a series of DEBUG messages
					for line in tbString.split('\n'):
						shlThreadsLogger.debug("%s", line)
					
					if self.lastError is not None:
						self.lastError = "%s; %s" % (self.lastError, str(e))
					else:
						self.lastError = str(e)
					self.batteryStatus = None
			
			if self.oidOutletStatusBaseEntry is not None:
				for i in xrange(1, self.nOutlets+1):
					# Get the status of outlet #(i+1).
					# NOTE:  Since the self.oidOutletStatusBaseEntry is just a base entry, 
					# we need to append on the outlet number (1-indexed) before we can use
					# it
					oidOutletStatusEntry = self.oidOutletStatusBaseEntry+(i,)
					
					try:
						errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(self.community, self.network, oidOutletStatusEntry)
						
						# Check for SNMP errors
						if errorIndication:
							raise RuntimeError("SNMP error indication: %s" % errorIndication)
						if errorStatus:
							raise RuntimeError("SNMP error status: %s" % errorStatus.prettyPrint())
						
						name, PortStatus = varBinds[0]
						PortStatus = int(unicode(PortStatus))
						
						try:
							self.status[i] = self.outletStatusCodes[PortStatus]
						except KeyError:
							self.status[i] = "UNK"
						if self.lastError is not None:
							self.lastError = None
							
					except Exception, e:
						exc_type, exc_value, exc_traceback = sys.exc_info()
						shlThreadsLogger.error("%s %s: monitorThread failed with: %s at line %i", type(self).__name__, str(self.id), str(e), traceback.tb_lineno(exc_traceback))
						
						## Grab the full traceback and save it to a string via StringIO
						fileObject = StringIO.StringIO()
						traceback.print_tb(exc_traceback, file=fileObject)
						tbString = fileObject.getvalue()
						fileObject.close()
						## Print the traceback to the logger as a series of DEBUG messages
						for line in tbString.split('\n'):
							shlThreadsLogger.debug("%s", line)
						
						if self.lastError is not None:
							self.lastError = "%s; %s" % (self.lastError, str(e))
						else:
							self.lastError = str(e)
						self.status[i] = "UNK"
			
			SNMPLock.release()
			
			toDataLog = "%.2f,%.2f,%.2f,%.2f,%s,%s,%.2f" % (time.time(), self.frequency if self.frequency is not None else -1, self.voltage if self.voltage is not None else -1, self.current if self.current is not None else -1, self.upsOutput, self.batteryStatus, self.batteryCharge if self.batteryCharge is not None else -1)
			fh = open('/data/rack%02i.txt' % self.id, 'a+')
			fh.write('%s\n' % toDataLog)
			fh.close()
			
			# Stop time
			tStop = time.time()
			shlThreadsLogger.debug('Finished updating current and port status in %.3f seconds', tStop - tStart)
			
			# Sleep for a bit
			sleepCount = 0
			sleepTime = self.MonitorPeriod - (tStop - tStart)
			while (self.alive.isSet() and sleepCount < sleepTime):
				time.sleep(0.2)
				sleepCount += 0.2
				
	def getOutputSource(self):
		"""
		Return the current power source.
		"""
		
		return self.upsOutput
		
	def getBatteryCharge(self):
		"""
		Return the battery change percentage.
		"""
		
		return self.batteryCharge
	
	def getBatteryStatus(self):
		"""
		Return the battery status.
		"""
		
		return self.batteryStatus


class Weather(object):
	"""
	Class for reading in values from the weather station database.
	"""

	def __init__(self, config, MonitorPeriod=120.0):
		self.config = config
		self.MonitorPeriod = MonitorPeriod

		# Update the configuration
		self.updateConfig()

		# Setup threading
		self.thread = None
		self.alive = threading.Event()
		self.lastError = None
		
		# Setup variables
		self.updatetime = None
		self.usUnits = False
		self.pressure = None
		self.temperature = None
		self.humidity = None
		self.windSpeed = None
		self.windDir = None
		self.windGust = None
		self.windGustDir = None
		self.rain = None
		self.rainRate = None

	def updateConfig(self, config=None):
		"""
		Using the configuration file, update the database file.
		"""
		
		# Update the current configuration
		if config is not None:
			self.config = config
		self.database = self.config['WEATHERDATABASE']

	def start(self):
		"""
		Start the monitoring thread.
		"""

		if self.thread is not None:
			self.stop()
			
		self.thread = threading.Thread(target=self.monitorThread)
		self.thread.setDaemon(1)
		self.alive.set()
		self.thread.start()

	def stop(self):
		"""
		Stop the monitor thread, waiting until it's finished.
		"""

		if self.thread is not None:
			self.alive.clear()          #clear alive event for thread
			self.thread.join()          #wait until thread has finished
			self.thread = None
			self.lastError = None

	def monitorThread(self):
		"""
		Create a monitoring thread for the temperature.
		"""

		while self.alive.isSet():
			tStart = time.time()

			try:
				# Make sure we don't try near the edge of a minute
				tNow = int(time.time())
				while ((tNow % 60) < 10) or ((tNow % 60) > 50):
					time.sleep(5)
					tNow = int(time.time())
				while os.system("lsof %s" % self.database) == 0:
					time.sleep(5)
								
				conn = sqlite3.connect(self.database, timeout=15)
				conn.row_factory = sqlite3.Row

				c = conn.cursor()
				c.execute("SELECT * FROM archive ORDER BY dateTime DESC")
				row = c.fetchone()

				self.updatetime = int(row['dateTime'])
				self.usUnits = bool(row['usUnits'])
				self.pressure = float(row['barometer'])
				self.temperature = float(row['outTemp'])
				self.humidity = float(row['outHumidity'])
				self.windSpeed = float(row['windSpeed'])
				self.windDir = float(row['windDir'])
				self.windGust = float(row['windGust'])
				self.windGustDir = float(row['windGustDir'])
				self.rain = float(row['rain'])
				self.rainRate = float(row['rainRate'])

				conn.close()

			except Exception, e:
				exc_type, exc_value, exc_traceback = sys.exc_info()
				shlThreadsLogger.error("Weather: monitorThread failed with: %s at line %i", str(e), traceback.tb_lineno(exc_traceback))
					
				## Grab the full traceback and save it to a string via StringIO
				fileObject = StringIO.StringIO()
				traceback.print_tb(exc_traceback, file=fileObject)
				tbString = fileObject.getvalue()
				fileObject.close()
				## Print the traceback to the logger as a series of DEBUG messages
				for line in tbString.split('\n'):
					shlThreadsLogger.debug("%s", line)
				
				if self.lastError is not None:
					self.lastError = "%s; %s" % (self.lastError, str(e))
				else:
					self.lastError = str(e)
				self.updatetime = None
				self.usUnits = False
				self.pressure = None
				self.temperature = None
				self.humidity = None
				self.windSpeed = None
				self.windDir = None
				self.windGust = None
				self.windGustDir = None
				self.rain = None
				self.rainRate = None

			# Stop time
			tStop = time.time()
			shlThreadsLogger.debug('Finished updating weather station data in %.3f seconds', tStop - tStart)
			
			# Sleep for a bit
			sleepCount = 0
			sleepTime = self.MonitorPeriod - (tStop - tStart)
			while (self.alive.isSet() and sleepCount < sleepTime):
				time.sleep(1.0)
				sleepCount += 1.0
				
	def getLastUpdateTime(self):
		"""
		Return the time of last update as a datetime object in UTC.
		"""

		if self.updatetime is None:
			return None
			
		return datetime.utcfromtimestamp(self.updatetime)

	def getTemperature(self, DegreesF=True):
		"""
		Return the outside temperature in degrees F.
		"""
		
		if self.temperature is None:
			return None

		if self.usUnits:
			f =  self.temperature
		else:
			f = 1.8*self.temperature + 32

		if DegreesF:
			return f
		else:
			return (f - 32)/1.8

	def getHumidity(self):
		"""
		Return the outside humdity.
		"""

		return self.humidity

	def getPressure(self):
		"""
		Return the barometric pressure.
		"""

		return self.pressure

	def getWind(self, MPH=True):
		"""
		Return a two-element tuple of wind speed and direction.
		"""

		if self.windSpeed is None or self.windDir is None:
			return (None, None)

		if self.usUnits:
			m = self.windSpeed
		else:
			m = self.windSpeed / 1.60934

		if MPH:
			return (m, self.windDir)
		else:
			return (m*1.60934, self.windDir)

	def getGust(self, MPH=True):
		"""
		Return a two-element tuple of wind gust speed and direction.
		"""

		if self.windGust is None or self.windGustDir is None:
			return (None, None)

		if self.usUnits:
			m = self.windGust
		else:
			m = self.windGust / 1.60934

		if MPH:
			return (m, self.windGustDir)
		else:
			return (m*1.60934, self.windGustDir)

	def getPercipitation(self, Inches=True):
		"""
		Return a two-element tuple of rainfall rate and total 
		rainfall.
		"""

		if self.rainRate is None or self.rain is None:
			return (None, None)

		if self.usUnits:
			rri = self.rainRate
			rfi = self.rain
		else:
			rri = self.rainRate / 25.4
			rfi = self.rain / 25.4

		if Inches:
			return (rri, rfi)
		else:
			return (rri*25.4, rfi*25.4)

			
