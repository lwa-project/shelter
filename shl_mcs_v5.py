# -*- coding: utf-8 -*-

#
# shl_mcs.py - 2011 Feb 14
# author:  Joe Craig, UNM
#
# usage:
#    $ python shl_mcs_v2.py [verbose]
#    Version 2.0 implementation of the MCS Common ICD for the "Shelter" controlled subsystem
#    adopted from mch_shl_1.py (Steve Ellingson, VT)
# -- Since no HVAC control is implemented currently, the TMP & DIF commands do nothing, but are stored and reported in the MIB appropriately
#    The SET-POINT & DIFFERENTIAL MIB entries will report the MIB values, but do not reflect the shelter settings
#    The TEMPERATURE MIB entry contains the current temperature of the networked thermometer.
# -- Minimum MIB: MCS-RESERVED section, minimal implementation
# -- SHL MIB: SHL-POWER and SHL-ECS
# -- PNG supported
# -- RPT supported, but is limited to 1 index at a time (no branches)
# -- SHT supported, but doesn't actually do anything apart from setting SUMMARY to SHUTDWN  But, it will return correctly.
# -- INI supported, initializes the software to accept commands and sets number of racks, "Set-Point" & "Differential" do nothing 
# -- TMP supported, but does nothing
# -- DIF supported, but does nothing
# -- PWR supported, controls rack power ports appropriately
#
# This code runs forever -- use CTRL-C or whatever to crash out when done.
#
# About the MIB:
# -- The MIB is implemented as a text file: "MIB_shl.txt" 
# -- The file is provided by the subsystem software, and is read when this program starts
# -- The format is: one row per MIB entry; each row is index (space) label (space) value
# -- Upon receipt of INI, TMP, DIF or PWR command this file is overwritten to update MIB entries
# -- Upon receipt of a PNG or RPT command, the file is re-read to get values for the response 
#
# Some notes:
# -- Intended to be compliant with SHL Common ICD v C, except as noted above
# -- Only the Thermometer, PDU1, & PDU2 are installed, 1/3/11
#
# $Rev$
# $LastChangedBy$
# $LastChangedDate$
# 


import socket
import time
import datetime
import math
import string
import struct   
import sys
import optparse
import threading
import signal
import os
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto import rfc1902


################################
#                              #
# MCS Networking Configuration #
#                              #
################################
DEST_IP = '10.1.1.2'        # The IP address of the client (MCS)
PORTT = 1739                # The transmit port address
PORTR = 1738                # The receive port address

B = 8192                    # [bytes] Max message size
MIB_FILE = "/home/lwa1shelter/software/MIB_shl.txt"  # Name of the MIB File


##############################
#                            #
# Shelter Temperature Limits #
#                            #
##############################
MIN_SHL_TEMP =  60.0
MAX_SHL_TEMP = 110.0

MIN_SHL_DIFF = 0.5
MAX_SHL_DIFF = 5.0


class Thermometer(object):
	"""
	Class for communicating with a network thermometer via SNMP and regularly polling
	the temperature.  The temperature value is stored in the "temp" attribute.
	"""

	oidTemperatureEntry = (1,3,6,1,4,1,22626,1,5,2,1,2,0)

	def __init__(self, ip, port, community):
		self.ip = ip
		self.port = port

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
		if t is None:
			return "Thermometer at IP: %s, current temperature is unknown" % self.ip
		else:
			return "Thermometer at IP %s, current temperature is %.1f F" % (self.ip, t)

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
			except Exception as e:
				self.temp = None
				self.lastError = str(e)
			
			# Sleep for a bit
			time.sleep(0.5)

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
	
	oidCurrentEntry = None
	oidOutletStatusBaseEntry = None
	oidOutletChangeBaseEntry = None
	
	outletStatusCodes = {1: "OFF", 2: "ON"}
	
	def __init__(self, ip, port, community, nOutlets=8, description=None):
		self.ip = ip
		self.port = port
		self.description = description
		
		# Setup the outlets, their currents and status codes
		self.nOutlets = nOutlets
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
				except Exception as e:
					self.current = None
					self.lastError = str(e)
			
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
					except Exception as e:
						if self.lastError is not None:
							self.lastError = "%s; %s" % (self.lastError, str(e))
						self.status[i] = "UNK"
						
			# Sleep for a bit
			time.sleep(0.1)


	def getCurrent(self):
		"""
		Return the current associated with the PDU or None if it unknown.
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
				except Exception as e:
					print str(e)
					return False
				
				return True


class TrippLite(PDU):
	"""
	Sub-class of the PDU class for TrippLite PDUs.
	"""
	
	def __init__(self, ip, port, community, nOutlets=8, description=None):
		super(TrippLite, self).__init__(ip, port, community, nOutlets=nOutlets, description=description)
		
		# Setup the OID values
		self.oidCurrentEntry = (1,3,6,1,2,1,33,1,4,4,1,3,1)
		self.oidOutletStatusBaseEntry = (1,3,6,1,4,1,850,100,1,10,2,1,2,)
		self.oidOutletChangeBaseEntry = (1,3,6,1,4,1,850,100,1,10,2,1,4,)
		
		# Setup the status codes
		self.outletStatusCodes = {1: "OFF", 2: "ON"}


class APC(PDU):
	"""
	Sub-class of the PDU class for the APC PDU on PASI.
	"""
	
	def __init__(self, ip, port, community, nOutlets=8, description=None):
		super(APC, self).__init__(ip, port, community, nOutlets=nOutlets, description=description)
		
		# Setup the OID values
		self.oidCurrentEntry = None
		self.oidOutletStatusBaseEntry = (1,3,6,1,4,1,318,1,1,4,4,2,1,3,)
		self.oidOutletChangeBaseEntry = (1,3,6,1,4,1,318,1,1,4,4,2,1,3,)
		
		# Setup the status codes
		self.outletStatusCodes = {1: "ON", 2: "OFF"}


def readMIB(filename):
	"""
	Given a MIB filename, read in the contents of the file and return a dictionary
	of MIB indicies and MIB entries.
	"""

	# Read the file containing the MIB into a string
	fp = open(filename, 'r')

	# Parse the string into MIB entries
	mibIndex = {}
	mibEntry = {}
	for line in fp:
		line = line.replace('\n', '')
		column = string.split(line, ' ', 2) # split line into columns
		column[1] = column[1].upper()
		column[2] = column[2].strip()
		
		mibIndex[column[0]] = column[1]
		mibEntry[column[1]] = column[2]

	# Close out the file
	fp.close()
	
	return mibIndex, mibEntry


def writeMIB(filename, mibIndex, mibEntry):
	"""
	Given a filename, a dictionary of MIB index->label lookups, and a dictionary 
	of MIB entries, refresh the contents of the MIB file.
	"""
	
	# Open the file for writing
	fp = open(filename, 'w')

	# Loop over the sorted list of MIB indicies 
	for i in sorted(mibIndex.keys()):
		fp.write("%s %s %s\n" % (i, mibIndex[i], str(mibEntry[mibIndex[i]])))
	
	# Close out the file
	fp.close()
	
	return True


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


# Setup the shelter thermometer
shlThermo = Thermometer('172.16.1.111', 161, cmdgen.CommunityData('arbitrary', 'public', 0))

# Setup the PDUs
PDUs = {}
PDUs[1] = TrippLite('172.16.1.113', 161, cmdgen.CommunityData('my-agent', 'public', 0), nOutlets=8, 
				description="ASP")
PDUs[2] = TrippLite('172.16.1.114', 161, cmdgen.CommunityData('my-agent', 'public', 0), nOutlets=8, 
				description="DP - 120VAC")
PDUs[3] = TrippLite('172.16.1.117', 161, cmdgen.CommunityData('my-agent', 'public', 0), nOutlets=8, 
				description="DP - 240VAC")
PDUs[4] = TrippLite('172.16.1.112', 161, cmdgen.CommunityData('my-agent', 'public', 0), nOutlets=8, 
				description="3-Bay - 120VAC - #1")
PDUs[5] = TrippLite('172.16.1.115', 161, cmdgen.CommunityData('my-agent', 'public', 0), nOutlets=8, 
				description="3-Bay - 120VAC - #2")
PDUs[6] =       APC('172.16.1.116', 161, cmdgen.CommunityData('my-agent', 'private', 0), nOutlets=8, 
				description="3-Bay - PASI")


def main(args):
	"""
	Main function for dealing with the sending and receiving of data for MCS.
	"""
	
	# Below are things that should not be changed
	if len(args) > 0:
		if args[0] == 'verbose':
			verbose = True
	else:
		verbose = False
		
	################
	#              #
	# Load the MIB #
	#              #
	################
	if verbose:
		print 'Loading MIB...'

	# Read the file containing the MIB
	mibIndex, mibEntry = readMIB(MIB_FILE)

	if verbose:
		print 'I am '+mibEntry['SUBSYSTEM']+'.'


	#################################
	#                               #
	# Set up the MCS network socket #
	#                               #
	#################################

	# Set up the receive socket for UDP
	r = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
	r.bind(('',PORTR))  # Accept connections from anywhere
	r.setblocking(1)   # Blocking on this sock

	# Set up the transmit socket for UDP
	t = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	t.connect((DEST_IP,PORTT)) 

	if verbose == 1:
		print 'Running...'

	initialised = False		# To keep a check on whether the SHL has been initialized
	ReBoot = False			# flag to check if SHT was issued

	#####################
	#                   #
	# Deal with SIGTERM #
	#                   #
	#####################
	def HandleSignalExit(signum, frame, MIB_FILE=MIB_FILE, mibIndex=mibIndex, mibEntry=mibEntry):
		# Save the MIB as it currently is
		writeMIB(MIB_FILE, mibIndex, mibEntry)
		
		# Exit
		sys.exit(1)
		
	signal.signal(signal.SIGTERM, HandleSignalExit)


	#####################
	#                   #
	# Main program loop #
	#                   #
	#####################
	try:
		while True:
			if ReBoot:
				##################################################
				#                                                #
				# Stop threads for reading PDUs and temp. sensor #
				#                                                #
				##################################################
				shlThermo.stop()
				for k in PDUs.keys():
					PDUs[k].stop()
				
				# Reboot
				os.system("shutdown -r now")

			# Update MIB with global variables from other threads
			tempF  = shlThermo.getTemperature(DegreesF=True)
			mibEntry['TEMPERATURE'] = str(tempF) if tempF is not None else "0.0"
			if tempF is None and verbose:
				print "Threading Error: %s -> %s" % (str(shlThermo), shlThermo.lastError)
			
			for rack in PDUs.keys():
				current = PDUs[rack].getCurrent()
				mibEntry['CURRENT-R%i' % rack] = str(current) if current is not None else "0"
				
				for outlet in xrange(1, PDUs[rack].nOutlets+1):
					status = PDUs[rack].getStatus(outlet=outlet)
					mibEntry['PWR-R%i-%i' % (rack, outlet)] = str(status) if status is not None else "UNK"
					if status is None and verbose:
						print "Threading Error: %s -> %s" % (str(PDUs[rack]), PDUs[rack].lastError)
					
			writeMIB(MIB_FILE, mibIndex, mibEntry)
					
			payload = r.recv(B)  # wait for something to appear
			
			# Say what was received
			if verbose:
				print 'rcvd> '+payload+'|'

			########################################
			#                                      #
			# Analyze received command and process #
			#                                      #
			########################################

			# The default is that a response is not necessary:
			bRespond = False  

			# Now the possibilities are:
			# (1) The message is not for us; then no response should be made
			# (2) The message is for us but is not a PNG, RPT, or SHT message.  In this case, send "reject" response
			# (3) The message is for us and is a PNG, RPT, or SHT message.  In this case, respond appropriately  

			destination = payload[:3] 
			sender      = payload[3:6]
			command     = payload[6:9]
			reference   = int(payload[9:18])
			datalen     = int(payload[18:22]) 
			mjd         = int(payload[22:28]) 
			mpm         = int(payload[28:37]) 
			data        = payload[38:38+datalen]
			
			# If it isn't intended for us, ignore it
			if destination not in (mibEntry['SUBSYSTEM'], 'ALL'):
				continue

			bRespond = True

			# --- Reread the MIB ---
			mibIndex, mibEntry = readMIB(MIB_FILE)
			response = 'R'+string.rjust(mibEntry['SUMMARY'], 7)+' Command not recognized' # use this until we find otherwise

			if command == 'PNG':
				if initialised:
					response = 'A'+string.rjust(mibEntry['SUMMARY'], 7) 
				else:
					response = 'R'+string.rjust(mibEntry['SUMMARY'], 7)+' Initialize the SHL first'
					
			elif command == 'RPT':
				if initialised:
					mib_label = data.strip()
					try:
						response = 'A'+string.rjust(mibEntry['SUMMARY'],7)+' '+mibEntry[mib_label.upper()]
						if verbose:
							print "RPT response is", response 
					except KeyError:
						response = 'R'+string.rjust(mibEntry['SUMMARY'], 7)+' Invalid MIB label' # use this until we find otherwise
				else:
					response = 'R'+string.rjust(mibEntry['SUMMARY'], 7)+' Initialize the SHL first'

			elif command == 'SHT':
				if initialised:
					mibEntry['SUMMARY'] = 'SHUTDWN'
					response = 'A'+string.rjust(mibEntry['SUMMARY'], 7)  # use this until we find otherwise
					arg = data.strip()
					writeMIB(MIB_FILE, mibIndex, mibEntry)
					# verify arguments
					
					ReBoot = True	# flag to cleanup and restart
					while len(arg)>0:
						args = args.split(None, 1)
						args[0] = args[0].strip()
						
						if args[0] not in ('SCRAM', 'RESTART'):
							response = 'R'+string.rjust(mibEntry['SUMMARY'],7)+' Invalid extra arguments' 
						if len(args) > 1:
							arg = args[1]
						else:
							arg = '' 
				else:
					response = 'R'+string.rjust(mibEntry['SUMMARY'],7)+' Initialize the SHL first'

			elif command == 'INI':
				arg = data.strip()
				if len(arg) > 0:
					args = string.split(arg,'&',3)
					if len(args) < 3:
						response = 'R' + string.rjust(mibEntry['SUMMARY'],7)+' Invalid number of arguments'
					elif len(args[0]) not in (3, 5, 6):
						response = 'R' +  string.rjust(mibEntry['SUMMARY'],7)+ ' Invalid argument length'
					else: 
						set_point = args[0]
						diff_point = args[1]
						racks_install = args[2]
						
						if not isHalfIncrements(float(set_point)):
							response = 'R' + string.rjust(mibEntry['SUMMARY'],7) +' Set-Point should be between increments of 0.5 F'
						elif MAX_SHL_TEMP < float(set_point):
							response = 'R' + string.rjust(mibEntry['SUMMARY'],7) +' Set-Point should not be higher than %.1f F' % MAX_SHL_TEMP
						elif MIN_SHL_TEMP > float(set_point):
							response = 'R' + string.rjust(mibEntry['SUMMARY'],7) +' Set-Point should not be lower than %.1f F' % MIN_SHL_TEMP
						else:
							mibEntry['SET-POINT'] = set_point
							
							if not isHalfIncrements(float(diff_point)):
								response = 'R' + string.rjust(mibEntry['SUMMARY'],7) +' Differential Point should be in increments of 0.5 F'
							elif float(diff_point) > MAX_SHL_DIFF:
								response = 'R' + string.rjust(mibEntry['SUMMARY'],7) +' Differential Point should not be greater than %.1f F' % MAX_SHL_DIFF
							elif float(diff_point) < MIN_SHL_DIFF:
								response = 'R' + string.rjust(mibEntry['SUMMARY'],7) +' Differential Point should not be less than %.1f F' % MIN_SHL_DIFF
							else:
								mibEntry['DIFFERENTIAL'] = diff_point
								
								initialised = True # INI command passes
								
								###################################################
								#                                                 #
								# Start threads for reading PDUs and temp. sensor #
								#                                                 #
								###################################################
								shlThermo.start()
								for k in PDUs.keys():
									PDUs[k].start()
								
								ri = list(racks_install)
												
								for j in xrange(len(ri)):
									if (ri[j] == '1'): 
										mibEntry['PORTS-AVAILABLE-R%i' % (j+1,)] = str(PDUs[j+1].nOutlets)
										mibEntry['CURRENT-R%i' % (j+1,)] = '0'
										default_val = 'OFF' # setting all ports under the 'set' rack to OFF 
										for k in xrange(PDUs[j+1].nOutlets): # initializing 8 ports for the 'set' rack
											mibEntry['PWR-R%i-%i' % (j+1, k+1)] = default_val                       
									else:
										mibEntry['PORTS-AVAILABLE-R%i' % (j+1,)] = '0'
										
								mibEntry['SUMMARY'] = 'NORMAL'
								writeMIB(MIB_FILE, mibIndex, mibEntry)
								response = 'A'+string.rjust(mibEntry['SUMMARY'],7)     

			elif command == 'TMP':
				if initialised:
					arg = string.strip(data)
					if (len(arg)!=5):
						response = 'R' +string.rjust(mibEntry['SUMMARY'],7) + ' Invalid argument length'
					else:
						if not isHalfIncrements(float(arg)):
							response = 'R' + string.rjust(mibEntry['SUMMARY'],7) +' Set-Point should be between in increments of 0.5 F'
						elif MAX_SHL_TEMP < float(arg):
							response = 'R' + string.rjust(mibEntry['SUMMARY'],7) +' Set-Point should not be higher than %.1f F' % MAX_SHL_TEMP
						elif MIN_SHL_TEMP > float(arg):
							response = 'R' + string.rjust(mibEntry['SUMMARY'],7) +' Set-Point should not be lower than %.1f F' % MIN_SHL_TEMP
						else:
							mibEntry['SET-POINT'] = arg
							writeMIB(MIB_FILE, mibIndex, mibEntry)
				else:
					response = 'R' +string.rjust(mibEntry['SUMMARY'],7) +' Initialize the SHL first' 

			elif command == 'DIF':
				if initialised:
					arg = string.strip(data)
					if len(arg) != 3 :
						response = 'R' +string.rjust(mibEntry['SUMMARY'],7) +' Invalid argument length'
					else:
						if not isHalfIncrements(float(arg)):
							response = 'R' + string.rjust(mibEntry['SUMMARY'],7) +' Differential Set-Point should be increments of 0.5 F'
						elif MAX_SHL_DIFF < float(arg):
							response = 'R' + string.rjust(mibEntry['SUMMARY'],7) +' Differential Set-Point should not be greater than %.1f F' % MAX_SHL_DIFF
						elif MIN_SHL_DIFF > float(arg):
							response = 'R' + string.rjust(mibEntry['SUMMARY'],7) +' Differential Set-Point should not be less than %.1f F' % MIN_SHL_DIFF
						else:
							mibEntry['DIFFERENTIAL'] = arg
							writeMIB(MIB_FILE, mibIndex, mibEntry)
				else:
					response = 'R'+  string.rjust(mibEntry['SUMMARY'],7)+' Initialize the SHL first' 

			elif command == 'PWR':
				if initialised:
					response = 'A' +string.rjust(mibEntry['SUMMARY'],7) #assume this unless there is some error
					arg = data
					if len(arg) > 6:
						response = 'R' + string.rjust(mibEntry['SUMMARY'],7) + ' Invalid arguments | Larger than 6 bytes'
					else:
						rack = int(arg[:1])
						port = int(arg[1:3])
						control = arg[3:]    
						
						if rack not in PDUs:
							response = 'R' + string.rjust(mibEntry['SUMMARY'],7) + ' Invalid rack number'
						else: 
							if port not in PDUs[rack].status.keys():
								response = 'R' + string.rjust(mibEntry['SUMMARY'],7) + ' Invalid port number'
							elif control not in ('ON ', 'OFF'):
								response = 'R' + string.rjust(mibEntry['SUMMARY'],7) + ' Invalid control argument'
							else:
								PDUs[rack].setStatus(outlet=port, status=control)
								mibEntry['LASTLOG'] = 'rack %i, port %i, changed to %s' % (rack, port, control)
								if verbose:
									print "Rack %i, port %i has been changed to %s" % (rack, port, control)
								writeMIB(MIB_FILE, mibIndex, mibEntry)               
				else:
					response = 'R' +string.rjust(mibEntry['SUMMARY'],7) + ' Initialize the SHL first'
			
			else:
				# Do nothing
				pass


			##################################
			#                                #
			# Message preparation and return #
			#                                #
			##################################

			payload = '(nothing)' # default payload
			if bRespond:
				# determine current time
				dt = datetime.datetime.utcnow()
				year        = dt.year
				month       = dt.month
				day         = dt.day
				hour        = dt.hour
				minute      = dt.minute
				second      = dt.second
				millisecond = dt.microsecond / 1000        

				# compute MJD
				# adapted from http://paste.lisp.org/display/73536
				# can check result using http://www.csgnetwork.com/julianmodifdateconv.html
				a = (14 - month) // 12
				y = year + 4800 - a
				m = month + (12 * a) - 3
				p = day + (((153 * m) + 2) // 5) + (365 * y)
				q = (y // 4) - (y // 100) + (y // 400) - 32045
				mjdi = int(math.floor( (p+q) - 2400000.5))
				mjd = string.rjust(str(mjdi),6)
				#print '#'+mjd+'#'

				# compute MPM
				mpmi = int(math.floor( (hour*3600 + minute*60 + second)*1000 + millisecond ))
				mpm = string.rjust(str(mpmi),9) 
				#print '#'+mpm+'#'

				# Build the payload
				# Note we are just using a single, non-updating REFERENCE number in this case
				payload = 'MCS'+mibEntry['SUBSYSTEM']+command+string.rjust(str(reference),9)
				payload = payload + string.rjust(str(len(response)),4)+str(mjd)+str(mpm)+' '
				payload = payload + response
				t.send(payload)      # send it 

				if verbose:
					print 'sent> '+payload+'|' # say what was sent (exclude checksum)

	except KeyboardInterrupt:
		# Stop threads
		shlThermo.stop()
		for k in PDUs.keys():
			try:
				PDUs[k].stop()
			except:
				pass
		
		# Save the MIB as it currently is
		writeMIB(MIB_FILE, mibIndex, mibEntry)
		
		print ''


if __name__ == "__main__":
	main(sys.argv[1:])
	
