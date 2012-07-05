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
import threading
import traceback
try:
        import cStringIO as StringIO
except ImportError:
        import StringIO

from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto import rfc1902

__version__ = "0.1"
__revision__ = "$Rev$"
__all__ = ['Thermometer', 'PDU', 'TrippLite', 'APC', '__version__', '__revision__', '__all__']


shlThreadsLogger = logging.getLogger('__main__')


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
		self.network = cmdgen.UdpTransportTarget((self.ip, self.port))

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
			
			toDataLog = '%.2f,%.2f' % (time.time(), self.temp if self.temp is not None else -1)
			fh = open('/data/thermometer%02i.txt' % self.id, 'a+')
			fh.write('%s\n' % toDataLog)
			fh.close()
				
			# Stop time
			tStop = time.time()
			shlThreadsLogger.debug('Finished updating temperature in %.3f seconds', tStop - tStart)
			
			# Make sure we aren't critical
			if self.SHLCallbackInstance is not None:
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
		self.status = {}
		for i in xrange(1, self.nOutlets+1):
			self.status[i] = "UNK"

		# Setup the SNMP UDP connection
		self.community = community
		self.network = cmdgen.UdpTransportTarget((self.ip, self.port))
		
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
					shlThreadsLogger.error("PDU: monitorThread failed with: %s at line %i", str(e), traceback.tb_lineno(exc_traceback))
					
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
					shlThreadsLogger.error("PDU: monitorThread failed with: %s at line %i", str(e), traceback.tb_lineno(exc_traceback))
					
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
					shlThreadsLogger.error("PDU: monitorThread failed with: %s at line %i", str(e), traceback.tb_lineno(exc_traceback))
					
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
						shlThreadsLogger.error("%s: monitorThread failed with: %s at line %i", type(self).__name__, str(e), traceback.tb_lineno(exc_traceback))
						
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
		