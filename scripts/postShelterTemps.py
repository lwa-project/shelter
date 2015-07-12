#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import urllib
import subprocess
from socket import gethostname


URL = "http://lwalab.phys.unm.edu/OpScreen/update.php"
KEY = "c0843461abe746a4608dd9c897f9b261"
SITE = gethostname().split("-",1)[0]
SUBSYSTEM = "SHL"

# Get the last line of the log file
t = subprocess.Popen(["tail", "-n1", '/data/thermometer01.txt'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
test, junk = t.communicate()
test = test.replace('\n', '')

# Check to see if the log is actually getting updated.  If not, send NaNs
try:
	lastUpdated, junk = test.split(',', 1)
except ValueError:
	lastUpdated = 0.0
	junk = 0.0
lastUpdated = float(lastUpdated)
if time.time() > lastUpdated + 300:
	test = "%.2f,NaN" % time.time()

# Send the update to lwalab
p = urllib.urlencode({'key': KEY, 'site': SITE, 'subsystem': SUBSYSTEM, 'data': test})
f = urllib.urlopen(URL, p)

