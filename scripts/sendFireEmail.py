#!/usr/bin/env python3

import os
import pytz
import time
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

# Time (min) after a warning e-mail is sent for an "all-clear"
FIRE_CLEAR_TIME = 60

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


## Read in the enviromux smoke detector status
output = getLast(os.path.join(DATA_DIR, 'enviromux.txt'), 1)
output = output[0].split(',', 1)
shlTime = float(output[0])
shlFire = (output[1].find('smoke=True') != -1)

## Timestamp to time
shlTime = datetime.utcfromtimestamp(shlTime)
shlTime = UTC.localize(shlTime)
shlTime = shlTime.astimezone(MST)

## If critical, e-mail
if shlFire:
    tNow = shlTime.strftime("%B %d, %Y %H:%M:%S %Z")
    
    subject = '%s - Shelter Fire' % (SITE.upper(),)
    message = "At %s the shelter smoke detector was activated.\n" % (tNow,)
    
    if not os.path.exists(os.path.join(STATE_DIR, 'inFireDetected')):
        # If the holding file does not exist, send out the e-mail
        sendEmail(subject, message)
        
    # Touch the file to update the modification time.  This is used to track
    # when the warning condition is cleared.
    try:
        fh = open(os.path.join(STATE_DIR, 'inFireDetected'), 'w')
        fh.write('%s\n' % tNow)
        fh.close()
    except Exception as e:
        print("Set fire lock file: %s" % str(e))
        
elif os.path.exists(os.path.join(STATE_DIR, 'inFireDetected')):
    # Check the age of the holding file to see if we have entered the "all-clear"
    age = time.time() - os.path.getmtime(os.path.join(STATE_DIR, 'inFireDetected'))
    
    if age >= FIRE_CLEAR_TIME*60:
        tNow = shlTime.strftime("%B %d, %Y %H:%M:%S %Z")
        
        subject = '%s - Shelter Fire - Cleared' % (SITE.upper(),)
        message = "At %s the shelter smoke detector was cleared.\n" % (tNow,)
        sendEmail(subject, message)
        
        try:
            os.unlink(os.path.join(STATE_DIR, 'inFireDetected'))
        except Exception as e:
            print("Remove fire lock file: %s" % str(e))
else:
    pass
