# test7.sh: S.W. Ellingson, Virginia Tech, 2009 Aug 25
#
# This script tests MCS/Scheduler's handling of DP
# using the Python-based generic emulator (although VERY easy to modify
# to use with actual DP subsystem).
# 
# 1. Launches generic subsystem emulator
# 2. Creates a MIB initialization file 
# 3. Brings up MCS/Scheduler with DP as a defined subsystem.
# 4. Updates local MIB, one entry at a time, using the RPT command
#    Note: the emulator supports only the MCS-RESERVED branch.
# 5. Exercises DP commands
#    Note: the emulator won't recognize DP-specific commands
# 6. Shuts down MCS/Scheduler and the subystem emulator
# When done, consider using "$ ms_mdr" to see entire MIB,
# and "$ cat mselog.txt" to see the log.
#
# Note this script assumes all software running on the same computer
# (Otherwise, change 127.0.0.1 to appropriate IPs)

# Fire up an emulator to play the role of ASP
python mch_minimal_server.py DP_ 127.0.0.1 1739 1738 &

# Create a DP MIB initialization file 
./ms_makeMIB_DP 

# Create an ms_init initialization file called "test7.dat" 
echo \
'mibinit DP_ 127.0.0.1 1738 1739
mcic    DP_' > test7.dat

# MCS/Scheduler start (allow a few seconds to get everything running)
./ms_init test7.dat
sleep 5

# Get MCS-RESERVED MIB entry values
# Note SUMMARY gets updated with every response, so no need to 
# explicitly get that
./msei DP_ RPT INFO
./msei DP_ RPT LASTLOG
./msei DP_ RPT SUBSYSTEM
./msei DP_ RPT SERIALNO
./msei DP_ RPT VERSION

# Here, it would be good to try to RPT some DP-specific MIB entries
# However, there is no point since these will fail with the generic emulator described above.
# Expect garbage unless a DP-capable emulator or the actual subsystem is used.



# Testing DP-specific commands
# Note these will be handled correctly by the MCS software, but will not be
# recognized by the limited subsystem emulator used here.  
./msei DP_ TBW 1 2 3
./msei DP_ TBN 38.0 7 15 99
./msei DP_ CLK 1
./msei DP_ INI

# Time for responses to be received/processed before shutting down
sleep 5

# Send MCS/Scheduler shutdown command 
./msei MCS SHT

# Shut down the subsystem emulator
killall -v python



