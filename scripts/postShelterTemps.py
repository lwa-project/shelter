#!/usr/bin/env python3

import time
import requests
import subprocess
from socket import gethostname

from lwa_auth import KEYS as LWA_AUTH_KEYS
from lwa_auth.signed_requests import post as signed_post


URL = "https://lwalab.phys.unm.edu/OpScreen/update"
SITE = gethostname().split("-",1)[0]
SUBSYSTEM = "SHL"

# Get the last line of the log file
if os.path.exists('/data/enviromux.txt'):
    ## Prefer to report enviromux data
    test = subprocess.check_output(["tail", "-n1", '/data/enviromux.txt'], stderr=subprocess.DEVNULL)
    test = test.decode('ascii')
    test = test.replace('\n', '')
    ## Only keep the first three entries that should contain the time and temperatures
    fields = test.split(',')[:3]
    test = ','.join(fields)
else:
    test = subprocess.check_output(["tail", "-n1", '/data/thermometer01.txt'], stderr=subprocess.DEVNULL)
    test = test.decode('ascii')
    test = test.replace('\n', '')
    
# Get the HVAC status
try:
    lls = subprocess.check_output(['/usr/local/bin/lead_lag_status',], stderr=subprocess.DEVNULL)
    lls = lls.decode('ascii')
    lls = lls.strip().rstrip().split(None, 1)[1]
    if lls.find('unk') != -1:
        lls = 'NaN'
        
    c1s = subprocess.check_output(['/usr/local/bin/compressor1_status',], stderr=subprocess.DEVNULL)
    c1s = c1s.decode('ascii')
    c1s = '1' if c1s.find('on') != -1 else c1s
    c1s = '-1' if c1s.find('disabled') != -1 else c1s
    c1s = '0' if c1s.find('off') != -1 else c1s
    c1s = 'NaN' if c1s.find('unk') != -1 else c1s
    
    c2s = subprocess.check_output(['/usr/local/bin/compressor2_status',], stderr=subprocess.DEVNULL)
    c2s = c2s.decode('ascii')
    c2s = '1' if c2s.find('on') != -1 else c2s
    c2s = '-1' if c2s.find('disabled') != -1 else c2s
    c2s = '0' if c2s.find('off') != -1 else c2s
    c2s = 'NaN' if c2s.find('unk') != -1 else c2s
    
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
f = signed_post(LWA_AUTH_KEYS.get('shl', kind='private'), URL,
                data={'site': SITE, 'subsystem': SUBSYSTEM, 'data': test})
f.close()
