#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import urllib
import subprocess


KEY = "c0843461abe746a4608dd9c897f9b261"
SUBSYSTEM = "SHL"


t = subprocess.Popen(["tail", "-n1", '/data/thermometer01.txt'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
test, junk = t.communicate()
test = test.replace('\n', '')

url = "http://lwalab.phys.unm.edu/OpScreen/test.php"

p = urllib.urlencode({'key': KEY, 'subsystem': SUBSYSTEM, 'data': test})
f = urllib.urlopen(url, p)
print f.read()

