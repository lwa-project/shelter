# test5.sh: S.W. Ellingson, Virginia Tech, 2009 Aug 06
#
# This script tests MCS/Scheduler's handling of SHL
# using an emulator for SHL (although VERY easy to modify
# to use with actual SHL subsystem).
# 
# 1. Launches a subsystem emulator for SHL.
# 2. Brings up MCS/Scheduler with SHL as a defined subsystem.
# 3. Updates local MIB, one entry at a time, using the RPT command
# 4. Exercises SHL commands
# 5. Shuts down MCS/Scheduler and the subystem emulator
# When done, consider using "$ ms_mdr" to see entire MIB,
# and "$ cat mselog.txt" to see the log.
#
# Note this script assumes the SHL emulator of MCS0012 is present
# in the subdirectory Emulator_SHL/
# Note this script assumes all software running on the same computer
# (Otherwise, change 127.0.0.1 to appropriate IPs)

# Fire up a SHL emulator
# First refresh MIB init file
cd Emulator_SHL
cp MIB_shl_1_START.txt MIB_shl_1.txt
# Launch the emulator
python mch_shl_1.py &
sleep 1
cd ..

# Create an ms_init initialization file called "test5.dat" 
echo \
'mibinit SHL 127.0.0.1 1738 1739
mcic    SHL' > test5.dat

# MCS/Scheduler start (allow a few seconds to get everything running)
./ms_init test5.dat
sleep 5

# Send SHL the required first command "INI".
# 90; 2.5; rack 1 on, all other racks off
./msei SHL INI '00090&2.5&100000'
# Good idea to wait a moment, since it is required that SHL
# get INI before any other command:
sleep 1

# Get some SHL-specific MIB entries
# Good idea to update PORTS-AVAILABLE-R# for all racks, since
# there is no update reflecting rack availability after the INI
# command:
./msei SHL RPT PORTS-AVAILABLE-R1
./msei SHL RPT PORTS-AVAILABLE-R2
./msei SHL RPT PORTS-AVAILABLE-R3
./msei SHL RPT PORTS-AVAILABLE-R4
./msei SHL RPT PORTS-AVAILABLE-R5
./msei SHL RPT PORTS-AVAILABLE-R6
# SET-POINT is updated automatically in response to "INI";
#   no need to do that again
# DIFFERENTIAL is updated automatically in response to "INI";
#   no need to do that again

# Get MCS-RESERVED MIB entry values
# Note SUMMARY gets updated with every response, so no need to 
# explicitly get that
./msei SHL RPT INFO
./msei SHL RPT LASTLOG
./msei SHL RPT SUBSYSTEM
./msei SHL RPT SERIALNO
./msei SHL RPT VERSION


# Testing some commands
./msei SHL TMP '00091'
./msei SHL DIF '1.5'
./msei SHL PWR '104ON '

# Time for responses to be received/processed before shutting down
sleep 5

# Send MCS/Scheduler shutdown command 
./msei MCS SHT

# Shut down the subsystem emulator
killall -v python



