

# Create an ms_init initialization file called "test1.dat" 
# The first line converts "NU1_MIB_init.dat" into a dbm-format MIB file
#   and embeds information about where to find NU1 (the IP and ports used)
# The second line launches a subsystem handler process (an "mcic") for NU1
echo \
'mibinit SHL 127.0.0.1 1738 1739
mcic    SHL' > shl_only.dat

# MCS/Scheduler start (allow a few seconds to get everything running)
echo
echo '$ ./ms_init test1.dat'
./ms_init shl_only.dat
sleep 5

