#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import pytz
import time
import pexpect
from datetime import datetime

import smtplib
from email.mime.text import MIMEText

# Timezones
UTC = pytz.utc
MST = pytz.timezone('US/Mountain')


# E-mail Users
TO = ['lwa1ops@phys.unm.edu',]

# SMTP user and password
FROM = 'lwa.station.1@gmail.com'
PASS = '1mJy4LWA'


def getUPSOnBattery(ipAddress, window=None, verbose=False):
	"""
	Given an IP address to the telnet interface on a TrippLite UPS, return
	a list of times when the UPS was on battery.  Optionally, specify a time
	window in seconds to search through or 'None' to return all (default 
	behaviour).
	"""
	
	# Event log example line
	#2)      07/16/2013 09:40:53 On Battery
	logRE = re.compile(r'(?P<datetime>\d{2}/\d{2}/\d{4}\s\d{2}\:\d{2}\:\d{2})\s(?P<event>.*)')
	
	# Get ready...
	proc = pexpect.spawn('telnet %s' % ipAddress)
	if verbose:
		proc.logfile = sys.stdout
		
	# Go!
	tNow = datetime.now()
	
	# Login
	proc.expect('login')
	proc.sendline('admin')
	proc.expect('Password')
	proc.sendline('admin')
	
	# Get to the event log
	proc.expect('> ')
	proc.sendline('1')
	proc.expect('> ')
	proc.sendline('1')
	proc.expect('> ')
	proc.sendline('4')
	proc.expect('> ')
	proc.sendline('1')
	
	# Get the event log
	proc.expect('> ')
	eventLog = proc.before
	proc.sendline('X')
	
	# Logout
	proc.expect('> ')
	proc.sendline('X')
	proc.expect('> ')
	proc.sendline('X')
	
	# Print the event log
	eventLog = eventLog.split('\n')
	
	onBatteryTimes = []
	for line in eventLog:
		if line.find('Battery') != -1:
			mtch = logRE.search(line)
			t = datetime.strptime(mtch.group('datetime'), '%m/%d/%Y %H:%M:%S')
			age = tNow - t
			age = int(age.total_seconds())
			
			if window is None:
				onBatteryTimes.append(t)
			elif age <= window:
				onBatteryTimes.append(t)
				
	return onBatteryTimes


def main(args):
	powerLoss = False
	powerLossTime = None
	powerLossReason = None
	
	# Check for brownouts and power loss
	ipAddress = '172.16.1.118'
	batteryTimes = getUPSOnBattery(ipAddress, window=930)
	if len(batteryTimes) > 0:
		powerLoss = True
		powerLossTime = batteryTimes[0]
		powerLossReason = 'UPS @ %s on battery' % ipAddress
		
	# If there has been a power loss
	if powerLoss:
		## Naive time to time to string
		powerLossTime = MST.localize(powerLossTime)
		tNow = powerLossTime.strftime("%B %d, %Y %H:%M:%S %Z")
		
		msg = MIMEText("At %s, there was a potential power loss or brownout.\n\nReason for warning: %s" % (tNow, powerLossReason))
		msg['Subject'] = 'Possible Shelter Power Loss/Brownout'
		msg['From'] = FROM
		msg['To'] = ','.join(TO)
		
		print msg
		
		try:
			server = smtplib.SMTP('smtp.gmail.com', 587)
			server.starttls()
			server.login(FROM, PASS)
			server.sendmail(FROM, TO, msg.as_string())
			server.close()
		except Exception, e:
			print str(e)


if __name__ == "__main__":
	main(sys.argv[1:])
	
