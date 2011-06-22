# mch_minimal_server.py - S. Ellingson, VT - 2009 Jul 22
# usage:
#   $ python mch_minimal_server.py <subsystem> <ip_address> <tx_port> <rx_port>
#     <subsystem> = three letter subsystem designator; e.g., "NU1", "SHL"
#     <ip_address> = IP address of the *client* as a dotted-quad; e.g., "127.0.0.1" 
#     <tx_port> = port address for transmit; e.g., 1739
#     <rx_port> = port address for receive; e.g., 1738
# This is the "server" side; the other end is MCS ("client") 
# Minimum implementation of the MCS Common ICD for controlled subsystems:
# -- Minimum MIB: MCS-RESERVED section only
# -- PNG supported
# -- RPT supported, but is limited to 1 index at a time (no branches)
# -- SHT will simply change STATUS to SHTDOWN.  But, it will return correctly.
# This code runs forever -- use CTRL-C or "kill <pid>" to crash out when done.
# The MIB is implemented completely in memory.  See code for initial values.
# Some notes:
# -- Intended to be compliant with MCS Common ICD v.1.0, except as noted above
# -- This is not production code.  It is not really even alpha code.  Don't worry.  Be happy.
# -- Example command line:
# -- $ python mch_minimal_server.py NU1 127.0.0.1 1739 1738


import socket
import time
import datetime
import math
import string
import struct   # for packing of binary to/from strings
import sys


# Below are things that shouldn't be changed
B = 8192                    # [bytes] Max message size


# ------------------------------
# Reading command line arguments
# ------------------------------

# Check for required command line argument <CMD> 
if len(sys.argv)<5: 
    print 'Proper usage is "mch_minimal_server.py <subsystem> <ip_address> <tx_port> <rx_port>".'
    print 'No action taken.'
    exit()
else:               
    subsystem  =     string.strip(sys.argv[1]) 
    ip_address =     string.strip(sys.argv[2])
    tx_port    = int(string.strip(sys.argv[3]))
    rx_port    = int(string.strip(sys.argv[4]))   
    
# print 'subsystem <'+subsystem+'>'
# print 'ip_address <'+ip_address+'>'
# print 'tx_port ', tx_port
# print 'rx_port ', rx_port
# exit()


# --------------------------
# Set up the MIB
# --------------------------

#print 'Setting up the MIB...'

ml = [] # this becomes a list of MIB labels
me = [] # this becomes a list of MIB entries (data)
ml.append('SUMMARY');   me.append('NORMAL')
ml.append('INFO');      me.append('This is mock INFO from '+subsystem)
ml.append('LASTLOG');   me.append('This is mock LASTLOG from '+subsystem)
ml.append('SUBSYSTEM'); me.append(subsystem)
ml.append('SERIALNO');  me.append(subsystem+'-1')
ml.append('VERSION');   me.append('mch_minimal_server.py_'+subsystem);

#print ml[0]+' '+me[0]
#print ml[1]+' '+me[1]
#print ml[2]+' '+me[2]
#print ml[3]+' '+me[3]
#print ml[4]+' '+me[4]
#print ml[5]+' '+me[5]

#print 'I am '+me[3]+'.'


# --------------------------
# Set up comms
# --------------------------

# Set up the receive socket for UDP
r = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
r.bind(('',rx_port)) # Accept connections from anywhere
r.setblocking(1)   # Blocking on this sock

# Set up the transmit socket for UDP
t = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
t.connect((ip_address,tx_port)) 

#print 'Running...'

while 1:

    payload = r.recv(B)  # wait for something to appear

    # Say what was received
    #print 'rcvd> '+payload+'|'

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
        
    #print 'DESTINATION: |'+destination+'|'
    #print 'SENDER:      |'+sender+'|'
    #print 'TYPE:        |'+command+'|'
    #print 'REFERENCE: ', reference
    #print 'DATALEN:   ', datalen
    #print 'MJD:       ', mjd
    #print 'MPM:       ', mpm
    #print 'DATA: |'+data+'|'

    if (destination==me[3]) or (destination=='ALL'): # comparing to MIB entry 1.4, "SUBSYSTEM"              

        bRespond = True
        response = 'R'+string.rjust(str(me[0]),7)+' Command not recognized' # use this until we find otherwise

        if command=='PNG':
            response = 'A'+string.rjust(str(me[0]),7) 

        if command=='RPT':
            response = 'R'+string.rjust(str(me[0]),7)+' Invalid MIB label' # use this until we find otherwis
            mib_label = string.strip(data)
            #print '|'+mib_label+'|'
            #print '|'+data+'|'
            # find in mib  
            response = 'R'+string.rjust(str(me[0]),7)+' MIB label not recognized'  
            for i in range(len(ml)):
                if ml[i]==mib_label:
                    response = 'A'+string.rjust(str(me[0]),7)+' '+me[i] 
	            bDone=1;

        if command=='SHT':
            response = 'A'+string.rjust(str(me[0]),7)  # use this until we find otherwis
            arg = string.strip(data)
            me[0] = "SHTDOWN"
            # verify arguments
            while len(arg)>0:
               args = string.split(arg,' ',1)
               args[0] = string.strip(args[0])
               #print '>'+args[0]+'|'
               if (not(args[0]=='SCRAM') and not(args[0]=='RESTART')):
                   response = 'R'+string.rjust(str(me[0]),7)+' Invalid extra arguments' 
               if len(args)>1:
                   arg = args[1]
               else:
                   arg = '' 
                
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
        #print '#'+payload+'#' 

        t.send(payload)      # send it 

    #print 'sent> '+payload+'|' # say what was sent 

# never get here, but what the heck.
s.close()
t.close()

#==================================================================================
#=== HISTORY ======================================================================
#==================================================================================
# mch_minimal_server.py: S.W. Ellingson, Virginia Tech, 2009 Jul 22
#   .1: Adding command line args <subsystem> <ip_address> <tx_port> <rx_port>
#       Also, makes it's own MIB file upon start-up (svn rev 7)
# mch_minimal_server.py: S.W. Ellingson, Virginia Tech, 2009 Jul 20
#   .1: Porting into project
# mch_mins_3.py - S. Ellingson, VT - 2009 Jun 30
