"""
Script that attemptes to reset the west unit at LWA-NA when it is in runaway
cooling.  The procedure is:
 * Save the current set point
 * Turn the HVAC off for 15 minutes at a time until the shelter warms to >77 F
 * Lower the set point to 75 F to start cooling
 * Wait until the unit stops cooling
 * Rest the set point to what it was when the script started
"""

import os
import sys
import time
sys.path.append('/lwa/software')

import shlQube

IP_ADDRESS = '172.16.1.150'

sp = shlQube.get_iceqube_setpoint(IP_ADDRESS)
print(f"Set point is currently {sp} F")

print("Entering warm up loop")
temps = shlQube.get_iceqube_temperatures(IP_ADDRESS)
nattempts = 0
while temps['enclosure'] < 77 and nattempts < 6:
    print(f"  Temperature is {temps['enclosure']} F, turning off unit for 15 minutes")
    shlQube.set_webrelay_state('172.16.1.152', [6,7], 1)
    time.sleep(15*60)

    print("  Turning unit back on for temperature check")
    shlQube.set_webrelay_state('172.16.1.152', [6,7], 0)
    time.sleep(10)

    temps = shlQube.get_iceqube_temperature(IP_ADDRESS)
    nattempts += 1
if nattempts == 6:
    raise RuntimeError(f"Failed to warm up after {nattempts} tries")

print(f"Temperature is now {temps['enclosure']} F, lowering setpoint to 75 F")
shlQube.set_iceqube_setpoint(IP_ADDRESS, 75)

print("Waiting for cooling status to turn on")
temps = shlQube.get_iceqube_temperatures(IP_ADDRESS)
status = shlQube.get_iceqube_status(IP_ADDRESS)
nattempts = 0
while not status['cooling'] and nattempts < 20:
    time.sleep(30)

    status = shlQube.get_iceqube_status(IP_ADDRESS)
    nattempts += 1
if nattempts == 20:
    raise RuntimeError(f"Failed to see cooling status turn on after {nattempts} tries")

print("Cooling status is on, waiting for it to turn back off")
status = shlQube.get_iceqube_status(IP_ADDRESS)
nattempts = 0
while status['cooling'] and nattempts < 40:
    time.sleep(30)

    status = shlQube.get_iceqube_status(IP_ADDRESS)
    nattempts += 1
if nattempts == 40:
    raise RuntimeError(f"Failed to see cooling turn back off after {nattempts} tries")

print(f"Resetting set point to {sp} F")
shlQube.set_iceqube_setpoint(IP_ADDRESS, sp)
