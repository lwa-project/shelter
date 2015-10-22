#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pytz
import time
import subprocess
from datetime import datetime
from socket import gethostname

import smtplib
from email.mime.text import MIMEText

# Timezones
UTC = pytz.utc
MST = pytz.timezone('US/Mountain')

# Site
SITE = gethostname().split('-', 1)[0]

# Time (min) after a warning e-mail is sent for an "all-clear"
CLEAR_TIME = 15

# E-mail Users
TO = ['lwa1ops@phys.unm.edu',]

# SMTP user and password
if SITE == 'lwa1':
	FROM = 'lwa.station.1@gmail.com'
	PASS = '1mJy4LWA'
elif SITE == 'lwasv':
	FROM = 'lwa.station.sv@gmail.com'
	PASS = '1mJy4LWA'
else:
	raise RuntimeError("Unknown site '%s'" % SITE)

# State directory
STATE_DIR = '/home/ops/.shl-state/'
if not os.path.exists(STATE_DIR):
	os.mkdir(STATE_DIR)
else:
	if not os.path.isdir(STATE_DIR):
		raise RuntimeError("'%s' is not a directory" % STATE_DIR)

# Data directory
DATA_DIR = '/data/'

# Racks to check
if SITE == 'lwa1':
	filesToCheck = ['rack01.txt', 'rack02.txt', 'rack03.txt', 'rack05.txt', 'rack07.txt']
elif SITE == 'lwasv':
	filesToCheck = ['rack02.txt', 'rack04.txt', 'rack05.txt']
else:
	filesToCheck = []


def getLast(filename, N):
	"""
	Function that takes in a filename and returns the last N lines of the file.
	"""
	
	proc = subprocess.Popen(['tail', '-n%i' % int(N), filename], stdout=subprocess.PIPE)
	output, error = proc.communicate()
	output = output.split('\n')[:-1]
	
	return output


# Parse the various files and see if there is anything to report
failureCount = 0
failureTime = []
failureType = []
for filename in filesToCheck:
	if not os.path.exists( os.path.join(DATA_DIR, filename) ):
		continue
		
	## Get the last 48 lines (about six minutes of logs)
	lines = getLast(os.path.join(DATA_DIR, filename), 48)
	for line in lines:
		### 
		fields = line.split(',')
		shlTime, junkF, shlVolt, junkC = [float(f) for f in fields[:4]]
		if len(fields) == 7:
			shlInput, shlCharge = fields[4], float(fields[6])
		else:
			shlInput, shlCharge = 'Normal', 100.0
			
		### Is it recent?
		if shlTime < time.time() - 300:
			continue
			
		### Does it have the hallmarks of a failure?
		if shlVolt < 100.0:
			failureCount += 1
			failureTime.append( shlTime )
			failureType.append( '%s input voltage at %i VAC' % (filename, shlVolt) )
			break
			
		elif shlInput not in ('Normal', 'None'):
			failureCount += 1
			failureTime.append( shlTime )
			failureType.append( '%s input source is \'%s\'' % (filename, shlInput) )
			break
			
		elif shlCharge < 100.0:
			failureCount += 1
			failureTime.append( shlTime )
			failureType.append( '%s battery charge at %i%%' % (filename, shlCharge) )
			break
			
# If there are enough signs, send out an e-mail
if failureCount >= 2:
	shlTime = datetime.utcfromtimestamp(shlTime)
	shlTime = UTC.localize(shlTime)
	shlTime = shlTime.astimezone(MST)
	tNow = shlTime.strftime("%B %d, %Y %H:%M:%S %Z")
	
	text = ""
	for tm,ty in zip(failureTime, failureType):
		## Timestamp to time
		tm = datetime.utcfromtimestamp(tm)
		tm = UTC.localize(tm)
		tm = shlTime.astimezone(MST)
		
		text = "%s  * %s - %s\n" % (text, tm, ty)
		
	msg = MIMEText("At %s there were %i indications of a power loss or bronwout in the last five minutes.\n\nThe indicators are:\n%s" % (tNow, failureCount, text))
	msg['Subject'] = '%s - Possible Shelter Power Loss/Brownout' % (SITE.upper(),)
	msg['From'] = FROM
	msg['To'] = ','.join(TO)
	msg.add_header('reply-to', TO[0])
	
	if not os.path.exists(os.path.join(STATE_DIR, 'inPowerFailure')):
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
		fh = open(os.path.join(STATE_DIR, 'inPowerFailure'), 'w')
		fh.write('%s\n' % tNow)
		fh.close()
	except Exception, e:
		print str(e)
		
else:
	if os.path.exists(os.path.join(STATE_DIR, 'inPowerFailure')):
		# Check the age of the holding file to see if we have entered the "all-clear"
		age = time.time() - os.path.getmtime(os.path.join(STATE_DIR, 'inPowerFailure'))
		
		if age >= CLEAR_TIME*60:
			shlTime = datetime.utcfromtimestamp(shlTime)
        		shlTime = UTC.localize(shlTime)
        		shlTime = shlTime.astimezone(MST)
			tNow = shlTime.strftime("%B %d, %Y %H:%M:%S %Z")
			
			msg = MIMEText("At %s the shelter power loss/bronwout indicators have cleared.  All monitored log files are normal.\n" % (tNow,))
			msg['Subject'] = '%s - Possible Shelter Power Loss/Brownout - Cleared' % (SITE.upper(),)
			msg['From'] = FROM
			msg['To'] = ','.join(TO)
			msg.add_header('reply-to', TO[0])
			
			try:
				server = smtplib.SMTP('smtp.gmail.com', 587)
				server.starttls()
				server.login(FROM, PASS)
				server.sendmail(FROM, TO, msg.as_string())
				server.close()
				
				os.unlink(os.path.join(STATE_DIR, 'inPowerFailure'))
			except Exception, e:
				print str(e)
				
