#!/usr/bin/env python3

"""
Script that implements a very simple thermostat that can be used as a failsafe
at NA to help with overcooling situations.
"""

import os
import sys
import time
import subprocess
from datetime import datetime
sys.path.append('/lwa/software')

import shlQube

from typing import Optional


# WebRelay setup
IP_ADDRESS = '172.16.1.152'
RELAY_PORTS = [6, 7]

# Temperature limits for turning the HVAC off/on
TEMP_HVAC_OFF_F = 65
TEMP_HVAC_ON_F = 75

# Off/on deadtimes for the HVAC
DEADTIME_OFF_SEC = 120
DEADTIME_ON_SEC = 300


def get_latest_temperature(sensor: int, max_age: int=300, nretry: int=5) -> Optional[float]:
    """
    Return the most recent enviromux temperature sensor value in C for the specified
    sensor index (zero-based).  If there is a problem reading from the file or if the
    temperature value is more than `max_age` s old, return None instead.
    """
    
    temp = None
    for i in range(nretry):
        tnow = time.time()
        try:
            last_entry = subprocess.check_output(['tail', '-n1', '/data/enviromux.txt'],
                                                 text=True)
            fields = last_entry.split(',')
            tupdated = float(fields[0])
            if tnow - tupdated < max_age:
                temp = float(fields[sensor+1])
                break
        except Exception as e:
            print(f"Failed to query temperature for sensor {sensor} on attempt {i+1}: {str(e)}")
            time.sleep(3)
            
    return temp


def main(args):
    # Report on the overall setup
    print(f"Starting {os.path.basename(__file__)} with settings:")
    print(f"  Temperature to turn off the HVAC: {TEMP_HVAC_OFF_F:.1f} F")
    print(f"  Off deadtime: {DEADTIME_OFF_SEC/60.:.1f} min")
    print(f"  Temperature to turn on the HVAC: {TEMP_HVAC_ON_F:.1f} F")
    print(f"  On deadtime: {DEADTIME_ON_SEC/60.:.1f} min")
    print("")
    
    tlast = 0.0
    while True:
        # Get the latest temperature reading for the west side
        tnow = datetime.utcnow()
        tnow_str = tnow.strftime("%Y-%m-%d %H:%M:%S")
        temp = get_latest_temperature(0)
        if temp is None:
            print(f"[{tnow_str}] Failed to query the temperature, retrying in 1 min")
            tlast = time.time()
            time.sleep(60)
            continue
            
        # Convert to F
        tempF = temp * 9/5 + 32
        
        # Make a decision based on the temperature
        if tempF < TEMP_HVAC_OFF_F:
            ## Too cold, turn off the HVAC and wait 2 min
            if not all(shlQube.get_webrelay_state(IP_ADDRESS, RELAY_PORTS)):
                print(f"[{tnow_str}] Temperature is {tempF:.1f} F, turning off HVAC")
                tlast = time.time()
                shlQube.set_webrelay_state(IP_ADDRESS, RELAY_PORTS, 1)
                time.sleep(DEADTIME_OFF_SEC)
                
        elif tempF > TEMP_HVAC_ON_F:
            ## Too warm, turn on the HVAC and wait 5 min
            if any(shlQube.get_webrelay_state(IP_ADDRESS, RELAY_PORTS)):
                print(f"[{tnow_str}] Temperature is {tempF:.1f} F, turning on HVAC")
                tlast = time.time()
                shlQube.set_webrelay_state(IP_ADDRESS, RELAY_PORTS, 0)
                time.sleep(DEADTIME_ON_SEC)
                
        # Periodic message to let users know we are still alive
        if time.time() - tlast > 1800:
            print(f"[{tnow_str}] Temperature is {tempF:.1f} F")
            tlast = time.time()


if __name__ == '__main__':
    main(sys.argv[1:])
