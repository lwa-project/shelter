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
__all__ = ['THERMOMLIST', 'PDULIST', 'CRITICAL_TEMP', 'CRITICAL_LIST', '__version__', '__revision__', '__all__']

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
PDULIST[7] = {'Type': 'TrippLiteUPS', 'IP': '172.16.1.119', 'Port': 161, 
		    'SecurityModel': ('my-agent', 'public', 0), 
		    'nOutlets': 3, 'Description': "UPS #1"}
PDULIST[8] = {'Type': 'TrippLiteUPS', 'IP': '172.16.1.118', 'Port': 161, 
		    'SecurityModel': ('my-agent', 'public', 0), 
		    'nOutlets': 3, 'Description': "UPS #2"}

# Define the critical shutdown list
CRITICAL_TEMP = 90.0			# Degrees F
CRITICAL_LIST = []	# List of (rack, port) combos. to turn off
