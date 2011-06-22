import threading
from pysnmp.entity.rfc3413.oneliner import cmdgen
import time

# ======================= Initialize Thermometer SNMP Interface ================

tSecurity = cmdgen.CommunityData('arbitrary', 'public', 0)
tNetwork = cmdgen.UdpTransportTarget(('172.16.1.111', 161))
tEntry = (1,3,6,1,4,1,22626,1,5,2,1,2,0)

tempF = 0.0
running = 1

class MyThread ( threading.Thread ):
	def run (self):
		global tempF
		while running: 
			# ================== Read the networked thermometer and store values to MIB, every 2 sec
		 	errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(tSecurity, tNetwork, tEntry)
        	 	name, value = varBinds[0]
        	 	tempF = 1.8*float(unicode(value)) + 32
        	 	print "Temperature is", tempF, "Degrees F."

MyThread().start()

while 1:
	try:
		print "Temperature from main is", tempF, "Degrees F."
		time.sleep(1)
	except KeyboardInterrupt:
		print "killed"
		running = 0
		break
	
