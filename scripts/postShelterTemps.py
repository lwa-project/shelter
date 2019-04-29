#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import urllib
import subprocess
from socket import gethostname


URL = "https://lwalab.phys.unm.edu/OpScreen/update.php"
KEY = "c0843461abe746a4608dd9c897f9b261"
SITE = gethostname().split("-",1)[0]
SUBSYSTEM = "SHL"

# Get the last line of the log file
t = subprocess.Popen(["tail", "-n1", '/data/thermometer01.txt'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
test, _ = t.communicate()
test = test.replace('\n', '')
if SITE != 'lwasv':
    test += ',NaN'
    
# Get the HVAC status
try:
    t = subprocess.Popen(['/usr/local/bin/lead_lag_status',], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lls, _ = t.communicate()
    lls = lls.strip().rstrip().split(None, 1)[1]
    if lls.find('?') != -1:
        lls = 'NaN'
        
    t = subprocess.Popen(['/usr/local/bin/compressor1_status',], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    c1s, _ = t.communicate()
    c1s = '1' if c1s.find('on') != -1 else c1s
    c1s = '-1' if c1s.find('disabled') != -1 else c1s
    c1s = '0' if c1s.find('off') != -1 else c1s
    
    t = subprocess.Popen(['/usr/local/bin/compressor2_status',], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    c2s, _ = t.communicate()
    c2s = '1' if c2s.find('on') != -1 else c2s
    c2s = '-1' if c2s.find('disabled') != -1 else c2s
    c2s = '0' if c2s.find('off') != -1 else c2s
    
except (OSError, subprocess.CalledProcessError, IndexError, ValueError):
    lls = 'NaN'
    c1s = 'NaN'
    c2s = 'NaN'
test += ','+lls+','+c1s+','+c2s

# Check to see if the log is actually getting updated.  If not, send NaNs
try:
    lastUpdated, _ = test.split(',', 1)
except ValueError:
    lastUpdated = 0.0
lastUpdated = float(lastUpdated)
if time.time() > lastUpdated + 300:
    test = "%.2f,NaN,NaN" % time.time()
    test += ',NaN,NaN,NaN'
    
# Send the update to lwalab
p = urllib.urlencode({'key': KEY, 'site': SITE, 'subsystem': SUBSYSTEM, 'data': test})
f = urllib.urlopen(URL, p)

