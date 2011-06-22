# test3.sh: S.W. Ellingson, Virginia Tech, 2009 Aug 04
# 
# 1. Launches subsystem emulators for minimal subsystems called NU1, NU2, NU3, and NU4.
# 2. Brings up MCS/Scheduler with NU1-NU4 as defined subsystems.
# 3. Updates local MIB for each subsytem, one entry at a time, using the RPT command
# 4. Shuts down MCS/Scheduler and the subystem emulator
# When done, consider using "$ ms_mdr" to see entire MIB,
# and "$ cat mselog.txt" to see the log.
#
# Note this script assumes all software running on the same computer
# (Otherwise, change 127.0.0.1 to appropriate IPs)

# Fire up subsystem emulators for NU1 - NU4
python mch_minimal_server.py NU1 127.0.0.1 1739 1738 &
python mch_minimal_server.py NU2 127.0.0.1 1741 1740 &
python mch_minimal_server.py NU3 127.0.0.1 1743 1742 &
python mch_minimal_server.py NU4 127.0.0.1 1745 1744 &
sleep 1

# Create an ms_init initialization file called "test3.dat" 
echo \
'mibinit NU1 127.0.0.1 1738 1739
mcic    NU1
mibinit NU2 127.0.0.1 1740 1741
mcic    NU2
mibinit NU3 127.0.0.1 1742 1743
mcic    NU3
mibinit NU4 127.0.0.1 1744 1745
mcic    NU4' > test3.dat

# MCS/Scheduler start (allow a few seconds to get everything running)
./ms_init test3.dat
sleep 5

# Send commands to subsystem
# Note SUMMARY gets updated with every response, so no need to 
# explicitly get that
./msei NU1 RPT INFO
./msei NU2 RPT INFO
./msei NU3 RPT INFO
./msei NU4 RPT INFO
./msei NU1 RPT LASTLOG
./msei NU2 RPT LASTLOG
./msei NU3 RPT LASTLOG
./msei NU4 RPT LASTLOG
./msei NU1 RPT SUBSYSTEM
./msei NU2 RPT SUBSYSTEM
./msei NU3 RPT SUBSYSTEM
./msei NU4 RPT SUBSYSTEM
./msei NU1 RPT SERIALNO
./msei NU2 RPT SERIALNO
./msei NU3 RPT SERIALNO
./msei NU4 RPT SERIALNO
./msei NU1 RPT VERSION
./msei NU2 RPT VERSION
./msei NU3 RPT VERSION
./msei NU4 RPT VERSION
sleep 5

# Send MCS/Scheduler shutdown command 
./msei MCS SHT

# Shut down the subsystem emulator
killall -v python



