#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pytz
import time
from datetime import datetime
import subprocess

import smtplib
from email.mime.text import MIMEText

# Timezones
UTC = pytz.utc
MST = pytz.timezone('US/Mountain')

# Critical shelter temperature (F)
CRITICAL_TEMP = 80.00

# Time (min) after a warning e-mail is sent for an "all-clear"
CLEAR_TIME = 30

# E-mail Users
TO = ['lwa1staff@panda3.phys.unm.edu',]

# SMTP user and password
FROM = 'lwa.station.1@gmail.com'
PASS = '1mJy4LWA'

## Read in the shelter temperature
proc = subprocess.Popen(['tail', '-n1', '/data/thermometer01.txt'], stdout=subprocess.PIPE)
output = proc.communicate()[0]
output = output.split('\n')[0]
output = output.split(',', 1)
shlTime = float(output[0])
shlTemp = float(output[1])

## Timestamp to time
shlTime = datetime.utcfromtimestamp(shlTime)
shlTime = UTC.localize(shlTime)
shlTime = shlTime.astimezone(MST)

## C to F
shlTemp = shlTemp*9./5. + 32.

## If critical, e-mail
if shlTemp >= CRITICAL_TEMP:
	tNow = shlTime.strftime("%B %d, %Y %H:%M:%S %Z")
	
	msg = MIMEText("At %s, the shelter temperature reached %.2f F\n\nWarning temperature value set to %.2f F\n" % (tNow, shlTemp, CRITICAL_TEMP))
	msg['Subject'] = 'Shelter Temperature Warning'
	msg['From'] = FROM
	msg['To'] = ','.join(TO)
	
	if not os.path.exists('/tmp/inWarning'):
		# If the holding file does not exist, send out the e-mail
		try:
			server = smtplib.SMTP('smtp.gmail.com', 587)
			server.starttls()
			server.login(FROM, PASS)
			server.sendmail(FROM, TO, msg.as_string())
			server.close()
		except Exception, e:
			print str(e)
			
	# Touch the file to update the modification time.  This is used to track
	# when the warning condition is cleared.
	try:
		fh = open('/tmp/inWarning', 'w')
		fh.write('%s\n' % tNow)
		fh.close()
	except Exception, e:
		print str(e)

elif shlTemp < CRITICAL_TEMP and os.path.exists('/tmp/inWarning'):
	# Check the age of the holding file to see if we have entered the "all-clear"
	age = time.time() - os.path.getmtime('/tmp/inWarning')
	
	if age >= CLEAR_TIME*60:
		tNow = shlTime.strftime("%B %d, %Y %H:%M:%S %Z")
		
		msg = MIMEText("At %s, the shelter temperature warning was cleared.\n\nWarning temperature value set to %.2f F\n" % (tNow, CRITICAL_TEMP))
		msg['Subject'] = 'Shelter Temperature Warning Cleared'
		msg['From'] = FROM
		msg['To'] = ','.join(TO)

		try:
			server = smtplib.SMTP('smtp.gmail.com', 587)
			server.starttls()
			server.login(FROM, PASS)
			server.sendmail(FROM, TO, msg.as_string())
			server.close()

			os.unlink('/tmp/inWarning')
		except Exception, e:
			print str(e)

else:
	pass
