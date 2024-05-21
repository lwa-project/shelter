#!/usr/bin/env python3

import os
import pytz
import time
import uuid
import subprocess
from datetime import datetime
from socket import gethostname

import smtplib
from email.mime.text import MIMEText

from lwa_auth import STORE as LWA_AUTH_STORE

# Timezones
UTC = pytz.utc
MST = pytz.timezone('US/Mountain')

# Site
SITE = gethostname().split('-', 1)[0]

# Critical shelter temperature (F)
CRITICAL_TEMP = 80.00
if SITE == 'lwa1':
    CRITICAL_TEMP = 83.00

# Time (min) after a warning e-mail is sent for an "all-clear"
CRITICAL_CLEAR_TIME = 30

# E-mail Users
TO = ['lwa1ops-l@list.unm.edu',]

# SMTP user and password
store_entry = LWA_AUTH_STORE.get('email')
FROM = store_entry.username
PASS = store_entry.password
ESRV = store_entry.url

# State directory
STATE_DIR = '/home/ops/.shl-state/'
if not os.path.exists(STATE_DIR):
    os.mkdir(STATE_DIR)
else:
    if not os.path.isdir(STATE_DIR):
        raise RuntimeError("'%s' is not a directory" % STATE_DIR)

# Data directory
DATA_DIR = '/data/'


def getLast(filename, N):
    """
    Function that takes in a filename and returns the last N lines of the file.
    """
    
    output = subprocess.check_output(['tail', '-n%i' % int(N), filename], stderr=subprocess.DEVNULL)
    output = output.decode('ascii')
    output = output.split('\n')[:-1]
    
    return output


def sendEmail(subject, message, debug=False):
    """
    Send an e-mail via the LWA1 operator list
    """
    
    message = "%s\n\nEmail ID: %s" % (message, str(uuid.uuid4()))
    
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = FROM
    msg['To'] = ','.join(TO)
    msg.add_header('reply-to', TO[0])
    
    try:
        server = smtplib.SMTP(ESRV, 587)
        if debug:
            server.set_debuglevel(1)
        server.starttls()
        server.login(FROM, PASS)
        server.sendmail(FROM, TO, msg.as_string())
        server.close()
        return True
    except Exception as e:
        print("ERROR: failed to send message - %s" % str(e))
        return False


## Read in the shelter temperature
output = getLast(os.path.join(DATA_DIR, 'thermometer01.txt'), 1)
output = output[0].split(',')
shlTime = float(output[0])
shlTemp = max([float(v) for v in output[1:]])

## Timestamp to time
shlTime = datetime.utcfromtimestamp(shlTime)
shlTime = UTC.localize(shlTime)
shlTime = shlTime.astimezone(MST)

## C to F
shlTemp = shlTemp*9./5. + 32.

## If critical, e-mail
if shlTemp >= CRITICAL_TEMP:
    tNow = shlTime.strftime("%B %d, %Y %H:%M:%S %Z")
    
    subject = '%s - Shelter Temperature Warning' % (SITE.upper(),)
    message = "At %s the shelter temperature reached %.1f F.\n\nWarning temperature value set to %.1f F.\n" % (tNow, shlTemp, CRITICAL_TEMP)
    
    if not os.path.exists(os.path.join(STATE_DIR, 'inTemperatureWarning')):
        # If the holding file does not exist, send out the e-mail
        sendEmail(subject, message)
        
    # Touch the file to update the modification time.  This is used to track
    # when the warning condition is cleared.
    try:
        fh = open(os.path.join(STATE_DIR, 'inTemperatureWarning'), 'w')
        fh.write('%s\n' % tNow)
        fh.close()
    except Exception as e:
        print("Set critical temperature lock file: %s" % str(e))
        
elif shlTemp < CRITICAL_TEMP and os.path.exists(os.path.join(STATE_DIR, 'inTemperatureWarning')):
    # Check the age of the holding file to see if we have entered the "all-clear"
    age = time.time() - os.path.getmtime(os.path.join(STATE_DIR, 'inTemperatureWarning'))
    
    if age >= CRITICAL_CLEAR_TIME*60:
        tNow = shlTime.strftime("%B %d, %Y %H:%M:%S %Z")
        
        subject = '%s - Shelter Temperature Warning - Cleared' % (SITE.upper(),)
        message = "At %s the shelter temperature warning was cleared.\n\nWarning temperature value set to %.1f F.\n" % (tNow, CRITICAL_TEMP)
        sendEmail(subject, message)
        
        try:
            os.unlink(os.path.join(STATE_DIR, 'inTemperatureWarning'))
        except Exception as e:
            print("Remove critical temperature lock file: %s" % str(e))
else:
    pass
