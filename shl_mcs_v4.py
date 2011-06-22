# -*- coding: utf-8 -*-

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
# This code runs forever -- use CTRL-C or whatever to crash out when done.
# About the MIB:
# -- The MIB is implemented as a text file: "MIB_shl.txt" 
# -- The file is provided by the subsystem software, and is read when this program starts
# -- The format is: one row per MIB entry; each row is index (space) label (space) value
# -- Upon receipt of INI,TMP,DIF or PWR command this file is overwritten to update MIB entries
# -- Upon receipt of a PNG or RPT command, the file is re-read to get values for the response 
# Some notes:
# -- Intended to be compliant with SHL Common ICD v C, except as noted above
# -- Only the Thermometer, PDU1, & PDU2 are installed, 1/3/11


import socket
import time
import datetime
import math
import string
import struct   
import sys
import optparse
import threading
import os
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto import rfc1902

DEST_IP = '10.1.1.2'        # The IP address of the client (MCS)
PORTT = 1739                # The transmit port address
PORTR = 1738                # The receive port address

B = 8192                    # [bytes] Max message size
MIB_FILE = "/home/lwa1shelter/software/MIB_shl.txt"  # Name of the MIB File

# Thermometer SNMP Interface
tNetwork = cmdgen.UdpTransportTarget(('172.16.1.111', 161))
# Power Distribution Unit (PDU) SNMP Interface
pPDUNetwork = []        # list of PDU Network address'
pPDUAPChuh = []         # list of whether or not the PDU is an APC or not
# PDU (rack 1, ASP)
pPDUNetwork.append(cmdgen.UdpTransportTarget(('172.16.1.113', 161)))
pPDUAPChuh.append(False)
# PDU (rack 2, DP 120VAC)
pPDUNetwork.append(cmdgen.UdpTransportTarget(('172.16.1.114', 161)))
pPDUAPChuh.append(False)
# PDU (rack 3, DP 240 VAC)
pPDUNetwork.append(cmdgen.UdpTransportTarget(('172.16.1.117', 161)))
pPDUAPChuh.append(False)
# PDU (rack 4, 3-Bay 120VAC 1)
pPDUNetwork.append(cmdgen.UdpTransportTarget(('172.16.1.112', 161)))
pPDUAPChuh.append(False)
# PDU (rack 5, 3-Bay 120VAC 2)
pPDUNetwork.append(cmdgen.UdpTransportTarget(('172.16.1.115', 161)))
pPDUAPChuh.append(False)
# PDU (rack 6), 3-Bay PASI
pPDUNetwork.append(cmdgen.UdpTransportTarget(('172.16.1.116', 161)))
pPDUAPChuh.append(True)

# Other SNMP Interface info
tSecurity = cmdgen.CommunityData('arbitrary', 'public', 0)
tEntry = (1,3,6,1,4,1,22626,1,5,2,1,2,0)
pSecurity = cmdgen.CommunityData('my-agent', 'public', 0)
ePWRcurrent = (1,3,6,1,2,1,33,1,4,4,1,3,1)
eOutletStatus = []
eOutletCTL = []
for i in range(8):      # Hardcoded for 8 port available on each PDU
	eOutletStatus.append((1,3,6,1,4,1,850,100,1,10,2,1,2,i+1))
	eOutletCTL.append((1,3,6,1,4,1,850,100,1,10,2,1,4,i+1))
APCeOutletStatus = []
APCeOutletCTL = []
for i in range(8):      # Hardcoded for 8 port available on each APC PDU
	APCeOutletStatus.append((1,3,6,1,4,1,318,1,1,4,4,2,1,3,i+1))
	APCeOutletCTL.append((1,3,6,1,4,1,318,1,1,4,4,2,1,3,i+1))

# Below are things that should not be changed
if len(sys.argv) > 1:
        if sys.argv[1] == 'verbose':
                verbose = 1
else:
        verbose = 0
        
# --------------------------
# Load the MIB
# --------------------------
if verbose:
        print 'Loading MIB...'

# Read the file containing the MIB into a string
fp = open(MIB_FILE,'r')
file = fp.read()
fp.close()

# Parse the string into MIB entries
mi = [] # this becomes a list of MIB labels
me = [] # this becomes a list of MIB entries (data)
mind = [] # this becomes a list of MIB indices
line = file.splitlines()   # split file into lines
for i in range(len(line)):
        column = string.split(line[i],' ',2) # split line into columns
        mind.append(column[0])
        mi.append(column[1])
        me.append(string.strip(column[2]))

if verbose:
        print 'I am '+me[3]+'.'
	
# --------------------------
# Set up comms
# --------------------------

# Set up the receive socket for UDP
r = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
r.bind(('',PORTR))  # Accept connections from anywhere
r.setblocking(1)   # Blocking on this sock

# Set up the transmit socket for UDP
t = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
t.connect((DEST_IP,PORTT)) 

if verbose == 1:
        print 'Running...'
        
# -----------------------------------------
# Threads for reading PDUs and temp sensor
# -----------------------------------------
tRunning = 1                    # Used to crash out of threads when ctrl-c happens in main
tempF = 0.0                     
tCurrent = [0, 0, 0, 0, 0, 0]   # Hardcoded for 6 PDUs

# Initialize a multidimensional list to store PDU port status', hardcoded for 6 PDUs, 8 ports each
tStatus = ['UNK']*6
for i in range(6):
	tStatus[i] = ['UNK']*8

class tTemp ( threading.Thread ):
	def run (self):
		global tempF
		while tRunning:
			# ================== Read the networked thermometer and store values to tempF
			errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(tSecurity, tNetwork, tEntry)
			name, value = varBinds[0]
			tempF = 1.8*float(unicode(value)) + 32
                        
class tPDUc ( threading.Thread ):
	def run (self):
		global tCurrent
		while tRunning:                
			if initialised:
					for j in range(len(ri)):
						if (ri[j] == '1'):
								# ================== Read the Power Distribution Units' Current and store value to tCurrent for PDU j+1
								if not pPDUAPChuh[j]:
									errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(pSecurity, pPDUNetwork[j], ePWRcurrent)
									name, PWRcurrent = varBinds[0]
									tCurrent[j] = PWRcurrent/10
								else:
									print 'PDU Current not avaliable for rack'+j+'.'
						else:
								print 'PDU Current not found for rack'+j+'.'

class tPDUs ( threading. Thread ):
	def run (self):
		global tStatus
		while tRunning:
			if initialised:
			#start = time.time()
				for j in range(len(ri)):
					if (ri[j] == '1'):
						# ================== Read the Power Distribution Units' port status and store value to tStatus for PDU j+1
						for i in range(len(mi)):
							if mi[i]=='PORTS-AVAILABLE-R'+str(j+1):	#find how many port are active in rack j+1
								numPorts = int(me[i])
						for k in range(numPorts):	                #read each port status and overwrite tStatus
							if not pPDUAPChuh[j]:
								errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(pSecurity, pPDUNetwork[j], eOutletStatus[k])
								name, PortStatus = varBinds[0]
								if PortStatus == 1:
									status = 'OFF'
								elif PortStatus == 2:
									status = 'ON '
								else:
									status = 'UNK'
								tStatus[j][k] = status
							else:
								errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(pSecurity, pPDUNetwork[j], APCeOutletStatus[k])
								name, PortStatus = varBinds[0]
								if PortStatus == 2:
									status = 'OFF'
								elif PortStatus == 1:
									status = 'ON '
								else:
									status = 'UNK'
								tStatus[j][k] = status
			#print "Reading all PDU port status took", time.time() - start, "seconds."
   
initialised = False     # To keep a check on whether the SHL has been initialised
ReBoot = False		# flag to check if SHT was issued
tTemp().start()         # Start temperature sensor thread
tPDUc().start()         # Start PDU thread to read current
tPDUs().start()         # Start PDU thread to read port status'

while 1:
        try:
		if (ReBoot == True):
			tRunning = 0	# kill threads
			os.system("shutdown -r now")	# reboot

                # Update MIB with global variables from other threads
                fp = open(MIB_FILE, 'w')
                for i in range(len(mi)):	                        # cycle through all MIB labels
                        if (mi[i]=='TEMPERATURE'):
                                me[i] = str(tempF)
                        for j in range(len(tCurrent)):                                                                                          
                                if (mi[i]=='CURRENT-R'+str(j+1)):
                                        me[i] = str(tCurrent[j])
                        for j in range(len(tStatus)):
                                for k in range(len(tStatus[j])):
                                        if (mi[i]=='PWR-R'+str(j+1)+'-'+str(k+1)):
                                                me[i] = tStatus[j][k]                                                                                       
			fp.writelines(mind[i]+' '+mi[i]+' '+me[i]+'\n')	# write all lines to MIB
                fp.close

                        
                payload = r.recv(B)  # wait for something to appear		
                                                                                                        
                        
                # Say what was received
                if verbose == 1:
                        print 'rcvd> '+payload+'|'

                # --------------------------
                # Analyzing received command
                # --------------------------

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

                if (destination==me[3]) or (destination=='ALL'): # comparing to MIB entry 1.4, "SUBSYSTEM"              

                        bRespond = True

                        # --- Reread the MIB ---
                        # Read the file containing the MIB into a string
                        fp = open(MIB_FILE,'r')
                        file = fp.read()
                        fp.close()
                        # Parse the string into MIB entries
                        mi = [] # this becomes a list of MIB labels
                        me = [] # this becomes a list of MIB entries (data)
                        mind =[] # this becomes a list of MIB indices
                        line = file.splitlines()   # split file into lines
                        for i in range(len(line)):
                            column = string.split(line[i],' ',2) # split line into columns
                            mi.append(column[1])
                            me.append(string.strip(column[2]))
                            mind.append(column[0])
                            response = 'R'+string.rjust(str(me[0]),7)+' Command not recognized' # use this until we find otherwise

                        if command=='PNG':
                            if initialised:
                               response = 'A'+string.rjust(str(me[0]),7) 
                            else:
                               response = 'R'+string.rjust(str(me[0]),7)+' Initialise the SHL first'
                             
                        if command=='RPT':
                            if initialised:
                               response = 'R'+string.rjust(str(me[0]),7)+' Invalid MIB label' # use this until we find otherwise
                               mib_label = string.strip(data)
                               for i in range(len(mi)):
                                   if mi[i]==mib_label:
                                       response = 'A'+string.rjust(str(me[0]),7)+me[i]
                                       if verbose == 1:
                                           print "RPT response is", response 
                            else:
                               response = 'R'+string.rjust(str(me[0]),7)+' Initialise the SHL first'

                        if command=='SHT':
                            if initialised:
                               me[0] = 'SHUTDWN'
                               response = 'A'+string.rjust(str(me[0]),7)  # use this until we find otherwise
                               arg = string.strip(data)
                               fp = open(MIB_FILE,'w')
                               for i in range(len(line)):
                                        fp.writelines(mind[i]+' '+mi[i]+' '+me[i]+'\n')
                               fp.close()
                               # verify arguments
			       ReBoot = True	# flag to cleanup and restart
                               while len(arg)>0:
                                  args = string.split(arg,' ',1)
                                  args[0] = string.strip(args[0])
                                  if (not(args[0]=='SCRAM') and not(args[0]=='RESTART')):
                                      response = 'R'+string.rjust(str(me[0]),7)+' Invalid extra arguments' 
                                  if len(args)>1:
                                      arg = args[1]
                                  else:
                                      arg = '' 
                            else:
                               response = 'R'+string.rjust(str(me[0]),7)+' Initialise the SHL first'

                        if  command=='INI':
                             arg = string.strip(data)
                             if len(arg)>0:
                                args = string.split(arg,'&',3)
                                if (len(args)<3):
                                    response = 'R' + string.rjust(str(me[0]),7)+' Invalid number of arguments'

                                elif (len(args[0])!=5 or len(args[1])!=3 or len(args[2])!=6):
                                      response = 'R' +  string.rjust(str(me[0]),7)+ ' Invalid argument length'
                                else: 
                                     set_point = args[0]
                                     diff_point = args[1]
                                     racks_install = args[2]
                                     min_tmp = 60       # Min valid temperature 
                                     max_tmp = 110      # Max valid temperature
                                     check = min_tmp
                                     while (check<=max_tmp): 
                                        if (float(set_point) == check):
                                            break
                                        else:
                                            check = check+0.5 # Valid increment
                                     if (check>max_tmp):
                                        response = 'R' + string.rjust(str(me[0]),7) + ' Set-Point should be between 60 F and 110 F in increments of 0.5 F'
                                     elif (min_tmp>float(set_point)):
                                        response = 'R' + string.rjust(str(me[0]),7)+' Set-Point should not be lesser than 60F'
                                     else:
                                        inc = 0.5
                                        while (inc<=5): # Checks for validity of differential point
                                           if (float(diff_point)==inc):
                                               break
                                           else:
                                               inc=inc+0.5
                                        if (inc>5):
                                           response = 'R' + string.rjust(str(me[0]),7)+' Differential Point should be in increments of 0.5 between 0.5 and 5'
                                        elif (float(diff_point)<0.5):
                                           response = 'R' + string.rjust(str(me[0]),7)+' Differential should not be lesser than 0.5'
                                        else:
                                           initialised = True # INI command passes
                                           fp = open(MIB_FILE,'w')
                                           ri = list(racks_install)
                                           init = False #flag to check if MIB has already been appended with new values
                                           for i in range(len(mi)):  
                                               if (mi[i] == 'SUMMARY'):
                                                   me[i] = 'NORMAL'
                                                   fp.writelines(mind[i]+' '+mi[i]+' '+me[i]+'\n')
                                               elif (mi[i] == 'INFO' or mi[i] == 'LASTLOG' or mi[i] == 'SUBSYSTEM'):
                                                   fp.writelines(line[i]+'\n')
                                               elif (mi[i] == 'SERIALNO' or mi[i] == 'VERSION'):
                                                   fp.writelines(line[i]+'\n') 
                                           if not init:
                                                init = True # MIB being updated                                
                                                for j in range(len(ri)):
                                                      app_index = '2.'+str(j+1)+'.1'
                                                      app_label = 'PORTS-AVAILABLE-R'+str(j+1)
                                                      if (ri[j] == '1'): 
                                                          no_ports = '08' # Set number of ports available to 08 when initialised
                                                          fp.writelines(app_index+' '+app_label+' '+no_ports+'\n')
                                                          k = 1
                                                          default_val = 'OFF' # setting all ports under the 'set' rack to OFF 
                                                          while (k<=8): # initialising 8 ports for the 'set' rack
                                                              new_index = '2.'+str(j+1)+'.2'+'.'+str(k)  
                                                              new_label = 'PWR-R'+str(j+1)+'-'+str(k) 
                                                              fp.writelines(new_index+' '+new_label+' '+default_val+'\n')
                                                              k = k+1
                                                          current = 0 # setting a default value to 0 
                                                          fp.writelines('2.'+str(j+1)+'.3 '+'CURRENT-R'+str(j+1)+' '+str(current)+'\n')                                     
                                                      else:
                                                          no_ports = '0' # Number of ports made zero when rack is not set
                                                          fp.writelines(app_index+' '+app_label+' '+no_ports+'\n')
                                           if init:
                                               sp_index = '3.1' # MIB index for Set-Point
                                               dp_index = '3.2' # MIB index for Differential
                                               temp_index = '3.3'# MIB index for Temperature
                                               fp.writelines(sp_index+' '+'SET-POINT'+' '+str(set_point)+'\n')
                                               fp.writelines(dp_index+' '+'DIFFERENTIAL'+' '+str(diff_point)+'\n')
                                               fp.writelines(temp_index+' '+'TEMPERATURE'+' '+str(set_point)) # Setting temperature to set_point
                                               response = 'A'+string.rjust(str(me[0]),7)     
                                           fp.close()

                        if command == 'TMP':
                           if initialised:
                              arg = string.strip(data)
                              if (len(arg)!=5):
                                  response = 'R' + string.rjust(str(me[0]),7) + ' Invalid argument length'
                              else:
                                  min_tmp = 60 # Min valid temperature
                                  max_tmp = 110 # Max valid temperature
                                  check = min_tmp
                                  int_arg = float(arg)
                                  while (check<=max_tmp):
                                      if (float(arg) == check):
                                         break
                                      else:
                                         check = check+0.5 # Valid increments
                                  if (check>max_tmp):
                                     response = 'R' + string.rjust(str(me[0]),7) + ' Set-Point should be between 60 F and 110 F in increments of 0.5 F'
                                  elif (min_tmp>float(arg)):
                                     response = 'R' + string.rjust(str(me[0]),7)+' Set-Point should not be lesser than 60F'  
                                  else:
                                     fp = open(MIB_FILE,'w')
                                     response = 'A' + string.rjust(str(me[0]),7)
                                     for i in range(len(mi)):
                                         if (mi[i]=='SET-POINT'):
                                            fp.writelines(mind[i]+' '+'SET-POINT'+' '+str(arg)+'\n')
                                         elif (mi[i]=='TEMPERATURE'):
                                            fp.writelines(mind[i]+' '+'TEMPERATURE'+' '+str(arg)+'\n')
                                         else:
                                            fp.writelines(line[i]+'\n')
                                     fp.close()
                           else:
                              response = 'R'+  string.rjust(str(me[0]),7)+' Initialise the SHL first' 

                        if command == 'DIF':
                           if initialised:
                              arg = string.strip(data)
                              if (len(arg)!=3):
                                  response = 'R' + string.rjust(str(me[0]),7) + ' Invalid argument length'
                              else:
                                  min_diff = 0.5 # Min Valid differential set-point
                                  max_diff = 5 # Max valid differential set-point
                                  check = min_diff
                                  while (check<=max_diff):
                                      if (float(arg) == check):
                                         break
                                      else:
                                         check = check+0.5
                                  if (check>max_diff):
                                     response = 'R' + string.rjust(str(me[0]),7) + ' Differential Set-Point should be between 0.5 F and 5 F in increments of 0.5 F'
                                  elif (min_diff>float(arg)):
                                     response = 'R' + string.rjust(str(me[0]),7)+' Differential Set-Point should not be lesser than 0.5 F'

                                  else:
                                     fp = open(MIB_FILE,'w')
                                     response = 'A' + string.rjust(str(me[0]),7)
                                     for i in range(len(mi)):
                                         if (mi[i]=='DIFFERENTIAL'):
                                            fp.writelines(mind[i]+' '+'DIFFERENTIAL'+' '+str(arg)+'\n')
                                         else:
                                            fp.writelines(line[i]+'\n')
                                     fp.close()
                           else:
                              response = 'R'+  string.rjust(str(me[0]),7)+' Initialise the SHL first' 

                        if command == 'PWR':
                           if initialised:
                              response = 'A' +string.rjust(str(me[0]),7) #assume this unless there is some error
                              arg = data
                              if (len(arg)>6):
                                 response = 'R' + string.rjust(str(me[0]),7) + ' Invalid arguments | Larger than 6 bytes'
                              else:
                                 rack = arg[:1]
                                 port = arg[1:3]
                                 control = arg[3:]    
                                 if (int(rack)>6 or int(rack)==0):
                                    response = 'R' + string.rjust(str(me[0]),7) + ' Invalid rack number'
                                 else: 
                                    rack_index = 'PORTS-AVAILABLE-R'+rack
                                    for i in range(len(mi)):
                                        if mi[i]==rack_index:
                                           if (int(port)>int(me[i]) or int(port)==0):
                                              response = 'R' + string.rjust(str(me[0]),7) + ' Invalid port number'
                                           else:
                                              if (control!='ON ' and control!='OFF'):
                                                 response = 'R' + string.rjust(str(me[0]),7) + ' Invalid control argument'
                                              else:
                                                 port_index = 'PWR-R'+rack+'-'+str(int(port))
                                                 for j in range(i,len(mi)):
                                                     if mi[j]==port_index:
                                                        me[j] = control
                                                        #================ Set Power Port ================
                                                        for k in range(7):
                                                                if (rack == str(k+1)):
                                                                        if not pPDUAPChuh[k]:
                                                                                if (control == 'ON '):
                                                                                        pdata = rfc1902.Integer(2)
                                                                                if (control == 'OFF'):
                                                                                        pdata = rfc1902.Integer(1)
                                                                                errorIndication, errorStatus, errorIndex, varBinds = \
                                                                                cmdgen.CommandGenerator().setCmd(pSecurity, pPDUNetwork[k], (eOutletCTL[int(port)-1], pdata))
                                                                                # Change LASTLOG
                                                                                fp = open(MIB_FILE,'w')
                                                                                for i in range(len(mi)):
                                                                                        if (mi[i]=='LASTLOG'):
                                                                                                fp.writelines(mind[i]+' '+'LASTLOG'+' '+str(control)+'\n')
                                                                                                me[i] = 'rack '+str(k+1)+', port '+str(port)+', changed to '+str(control)
                                                                                        else:
                                                                                                fp.writelines(line[i]+'\n')
                                                                                fp.close()
                                                                                if verbose:
                                                                                        print "Rack", k+1, "Port", str(port), "has been changed to", str(control)
                                                                        else:
                                                                                if (control == 'ON '):
                                                                                        pdata = rfc1902.Integer(1)
                                                                                if (control == 'OFF'):
                                                                                        pdata = rfc1902.Integer(2)
                                                                                errorIndication, errorStatus, errorIndex, varBinds = \
                                                                                cmdgen.CommandGenerator().setCmd(pSecurity, pPDUNetwork[k], (APCeOutletCTL[int(port)-1], pdata))
                                                                                # Change LASTLOG
                                                                                fp = open(MIB_FILE,'w')
                                                                                for i in range(len(mi)):
                                                                                        if (mi[i]=='LASTLOG'):
                                                                                                fp.writelines(mind[i]+' '+'LASTLOG'+' '+str(control)+'\n')
                                                                                                me[i] = 'rack '+str(k+1)+', port '+str(port)+', changed to '+str(control)
                                                                                        else:
                                                                                                fp.writelines(line[i]+'\n')
                                                                                fp.close()
                                                                                if verbose:
                                                                                        print "Rack", k+1, "Port", str(port), "has been changed to", str(control)
                                                                                
                                    fp = open(MIB_FILE,'w')
                                    for i in range(len(line)):
                                        fp.writelines(mind[i]+' '+mi[i]+' '+me[i]+'\n')
                                    fp.close()                    
                           else:
                              response = 'R' +string.rjust(str(me[0]),7) + ' Initialise the SHL first'


                        # -------------------
                        # Message Preparation
                        # -------------------

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
                                payload = 'MCS'+me[3]+command+string.rjust(str(reference),9)
                                payload = payload + string.rjust(str(len(response)),4)+str(mjd)+str(mpm)+' '
                                payload = payload + response
                                t.send(payload)      # send it 

                        if verbose:
                                print 'sent> '+payload+'|' # say what was sent (exclude checksum)

        except KeyboardInterrupt:
                tRunning = 0
                break
