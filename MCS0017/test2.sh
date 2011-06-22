# test2.sh: S.W. Ellingson, Virginia Tech, 2009 Aug 14
# 
# 1. Launches a subsystem emulator for a minimal subsystem called NU1.
# 2. Brings up MCS/Scheduler with NU1 as a defined subsystem.
# 3. Updates local MIB, one entry at a time, using the RPT command
# 4. Shuts down MCS/Scheduler and the subystem emulator
# When done, consider using "$ ms_mdr" to see entire MIB,
# and "$ cat mselog.txt" to see the log.
#
# Note this script assumes all software running on the same computer
# (Otherwise, change 127.0.0.1 to appropriate IPs)

# Fire up a subsystem emulator for NU1
python mch_minimal_server.py NU1 127.0.0.1 1739 1738 &
sleep 1

# Create an ms_init initialization file called "test2.dat" 
echo \
'mibinit NU1 127.0.0.1 1738 1739
mcic    NU1' > test2.dat

# MCS/Scheduler start (allow a few seconds to get everything running)
./ms_init test2.dat
sleep 5

# Send commands to subsystem
# Note SUMMARY gets updated with every response, so no need to 
# explicitly get that
./msei NU1 RPT INFO
./msei NU1 RPT LASTLOG
./msei NU1 RPT SUBSYSTEM
./msei NU1 RPT SERIALNO
./msei NU1 RPT VERSION
sleep 5

# Send MCS/Scheduler shutdown command 
./msei MCS SHT

# Shut down the subsystem emulator
killall -v python



