#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import urllib
import subprocess


URL = "http://lwalab.phys.unm.edu/OpScreen/test.php"
KEY = "c0843461abe746a4608dd9c897f9b261"
SUBSYSTEM = "SHL"

# Get the last line of the log file
t = subprocess.Popen(["tail", "-n1", '/data/thermometer01.txt'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
test, junk = t.communicate()
test = test.replace('\n', '')

# Check to see if the log is actually getting updated.  If not, send NaNs
lastUpdated, junk = test.split(',', 1)
lastUpdated = float(lastUpdated)
if time.time() > lastUpdated + 300:
	test = "%.2f,NaN" % time.time()

# Send the update to lwalab
p = urllib.urlencode({'key': KEY, 'subsystem': SUBSYSTEM, 'data': test})
f = urllib.urlopen(URL, p)
print f.read()

