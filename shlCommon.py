# -*- coding: utf-8 -*-

"""
Module to store "common" values used by SHL as well as the getTime() function for
finding out the current MJD and MPM values.

$Rev$
$LastChangedBy$
$LastChangedDate$
"""

import math
from datetime import datetime

__version__ = "0.1"
__revision__ = "$Rev$"
__all__ = ['THERMOMLIST', 'PDULIST', 'MCS_RCV_BYTES', 'getTime', 
		 '__version__', '__revision__', '__all__']

# Setup the thermometers
THERMOMLIST = {}
THERMOMLIST[1] = {'IP': '172.16.1.111', 'Port': 161, 
			   'SecurityModel': ('arbitrary', 'public', 0), 
			   'Description': "Shelter #1"}

# Setup the PDUs
PDULIST = {}
PDULIST[1] = {'Type': 'TrippLite', 'IP': '172.16.1.113', 'Port': 161, 
		    'SecurityModel': ('my-agent', 'public', 0), 
		    'nOutlets': 8, 'Description': "ASP"}
PDULIST[2] = {'Type': 'TrippLite', 'IP': '172.16.1.114', 'Port': 161, 
		    'SecurityModel': ('my-agent', 'public', 0), 
		    'nOutlets': 8, 'Description': "DP - 120VAC"}
PDULIST[3] = {'Type': 'TrippLite', 'IP': '172.16.1.117', 'Port': 161, 
		    'SecurityModel': ('my-agent', 'public', 0), 
		    'nOutlets': 8, 'Description': "DP - 240VAC"}
PDULIST[4] = {'Type': 'TrippLite', 'IP': '172.16.1.112', 'Port': 161, 
		    'SecurityModel': ('my-agent', 'public', 0), 
		    'nOutlets': 8, 'Description': "3-Bay - 120VAC - #1"}
PDULIST[5] = {'Type': 'TrippLite', 'IP': '172.16.1.115', 'Port': 161, 
		    'SecurityModel': ('my-agent', 'public', 0), 
		    'nOutlets': 8, 'Description': "3-Bay - 120VAC - #2"}
PDULIST[6] = {'Type': 'APC', 'IP': '172.16.1.116', 'Port': 161, 
		    'SecurityModel': ('my-agent', 'private', 0), 
		    'nOutlets': 8, 'Description': "3-Bay - PASI"}


# Maximum number of bytes to receive from MCS
MCS_RCV_BYTES = 16*1024


def getTime():
	"""
	Return a two-element tuple of the current MJD and MPM.
	"""
	
	# determine current time
	dt = datetime.utcnow()
	year        = dt.year             
	month       = dt.month      
	day         = dt.day    
	hour        = dt.hour
	minute      = dt.minute
	second      = dt.second     
	millisecond = dt.microsecond / 1000

	# compute MJD         
	# adapted from http://paste.lisp.org/display/73536
	# can check result using http://www.csgnetwork.com/julianmodifdateconv.html
	a = (14 - month) // 12
	y = year + 4800 - a          
	m = month + (12 * a) - 3                    
	p = day + (((153 * m) + 2) // 5) + (365 * y)   
	q = (y // 4) - (y // 100) + (y // 400) - 32045
	mjd = int(math.floor( (p+q) - 2400000.5))  

	# compute MPM
	mpm = int(math.floor( (hour*3600 + minute*60 + second)*1000 + millisecond ))

	return (mjd, mpm)