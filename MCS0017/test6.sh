# test6.sh: S.W. Ellingson, Virginia Tech, 2009 Aug 14
#
# This script tests MCS/Scheduler's handling of ASP
# using the Python-based emulator (although VERY easy to modify
# to use with actual SHL subsystem).
# 
# 1. Launches a subsystem emulator for ASP.
# 2. Creates a MIB initialization file for an ASP 
# 3. Brings up MCS/Scheduler with ASP as a defined subsystem.
# 4. Updates local MIB, one entry at a time, using the RPT command
#    Note: the emulator supports only the MCS-RESERVED branch.
# 5. Exercises SHL commands
#    Note: the emulator won't recognize ASP-specific commands
# 6. Shuts down MCS/Scheduler and the subystem emulator
# When done, consider using "$ ms_mdr" to see entire MIB,
# and "$ cat mselog.txt" to see the log.
#
# Note this script assumes all software running on the same computer
# (Otherwise, change 127.0.0.1 to appropriate IPs)

# Fire up an emulator to play the role of ASP
python mch_minimal_server.py ASP 127.0.0.1 1739 1738 &

# Create ASP MIB initialization file for an ASP with
# 3 ARX power supplies, 2 FEE power supplies, and 10 temperature sensors
./ms_makeMIB_ASP 3 2 10

# Create an ms_init initialization file called "test6.dat" 
echo \
'mibinit ASP 127.0.0.1 1738 1739
mcic    ASP' > test6.dat

# MCS/Scheduler start (allow a few seconds to get everything running)
./ms_init test6.dat
sleep 5

# Send ASP the required first command "INI".
# Specify 16 boards
./msei ASP INI 16
# Good idea to wait a moment, since it is required that SHL
# get INI before any other command:
sleep 1

# Get MCS-RESERVED MIB entry values
# Note SUMMARY gets updated with every response, so no need to 
# explicitly get that
./msei ASP RPT INFO
./msei ASP RPT LASTLOG
./msei ASP RPT SUBSYSTEM
./msei ASP RPT SERIALNO
./msei ASP RPT VERSION

# Get some ASP-specific MIB entries
# Note these will fail with the generic emulator described above.
# Expect garbage unless an improved emulator or the actual subsystem is used.
./msei ASP RPT ARXSUPPLY-NO
./msei ASP RPT FEESUPPLY_NO
./msei ASP RPT TEMP-SENSE-NO

# Testing ASP-specific commands
# Note these will fail with the generic emulator described above.
# Expect garbage unless an improved emulator or the actual subsystem is used.
# Parameters are from the examples in the ASP ICD
./msei ASP FIL '02702'
./msei ASP AT1 '02708'
./msei ASP AT2 '02708'
./msei ASP ATS '02708'
./msei ASP FPW '027211'
./msei ASP RXP '00'
./msei ASP FEP '00'

# Time for responses to be received/processed before shutting down
sleep 5

# Send MCS/Scheduler shutdown command 
./msei MCS SHT

# Shut down the subsystem emulator
killall -v python



