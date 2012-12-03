#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import pytz
import time
from datetime import datetime
import subprocess

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

## Read in the last few log entries from Rack #07
proc = subprocess.Popen(['tail', '-n15', '/data/rack07.txt'], stdout=subprocess.PIPE)
output = proc.communicate()[0]
output = output.split('\n')

## Check for brownouts and power loss:
powerLoss = False
powerLossTime = 0
powerLossReason = None
for line in output:
	if len(line) == 0:
		continue

	fields = line.split(',')
	if fields[-3] != 'Normal':
		# Guard against the output power source being None because of failed communications
		if float(fields[-1]) > 0:
			powerLoss = True
			powerLossTime = float(fields[0]) 
			powerLossReason = "Output power source is '%s'" % fields[-3]
		else:
			sys.stderr.write("Output power power is '%s' but the corresponding log entry is:\n%s\n" % (fields[-3], line))
	elif float(fields[-1]) < 100:
		powerLoss = True
		powerLossTime = float(fields[0])
		powerLossReason = "Battery at %i%%" % float(fields[-1])
	else:
		pass

# If there has been a power loss
if powerLoss:
	## Timestamp to time
	powerLossTime = datetime.utcfromtimestamp(powerLossTime)
	powerLossTime = UTC.localize(powerLossTime)
	powerLossTime = powerLossTime.astimezone(MST)

	tNow = powerLossTime.strftime("%B %d, %Y %H:%M:%S %Z")
	
	msg = MIMEText("At %s, there was a potential power loss or brownout.\n\nReason for warning: %s" % (tNow, powerLossReason))
	msg['Subject'] = 'Possible Shelter Power Loss/Brownout'
	msg['From'] = FROM
	msg['To'] = ','.join(TO)
	
	try:
		server = smtplib.SMTP('smtp.gmail.com', 587)
		server.starttls()
		server.login(FROM, PASS)
		server.sendmail(FROM, TO, msg.as_string())
		server.close()
	except Exception, e:
		print str(e)
