#Modified for ASP & SHL only  J. Craig - 12/29/09
#test6.sh: S.W. Ellingson, Virginia Tech, 2009 Aug 14
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

# Create ASP MIB initialization file for an ASP with
# 1 ARX power supplies, 1 FEE power supplies, and 11 temperature sensors
./ms_makeMIB_ASP 1 1 1


# Create an ms_init initialization file called "shl_asp.dat" 
echo \
'mibinit ASP 10.1.1.40 1738 1739
mcic    ASP
mibinit SHL 10.1.1.30
mcic    SHL' > shl_asp.dat

# MCS/Scheduler start (allow a few seconds to get everything running)
./ms_init shl_asp.dat
sleep 5

