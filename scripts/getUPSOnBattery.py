#!/usr/bin/env python

import os
import re
import sys
import time
import pexpect
from datetime import datetime

# Event log example line
#2)      07/16/2013 09:40:53 On Battery
logRE = re.compile(r'(?P<datetime>\d{2}/\d{2}/\d{4}\s\d{2}\:\d{2}\:\d{2})\s(?P<event>.*)')


def main(args):
	ipAddress = args[0]
	proc = pexpect.spawn('telnet %s' % ipAddress)#, logfile=sys.stdout)
	
	# Current time
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
	
	print "# Date [MT]         Age [s]"
	for line in eventLog:
		if line.find('Battery') != -1:
			mtch = logRE.search(line)
			t = datetime.strptime(mtch.group('datetime'), '%m/%d/%Y %H:%M:%S')
			age = tNow - t
			
			print t, int(age.total_seconds())


if __name__ == "__main__":
	main(sys.argv[1:])
	
