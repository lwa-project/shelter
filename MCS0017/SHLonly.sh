# Initialize MCS software to talk to SHL only

# Create an ms_init initialization file called "SHLonly.dat" 
echo \
'mibinit SHL 127.0.0.1 1738 1739
mcic    SHL' > SHLonly.dat

# MCS/Scheduler start (allow a few seconds to get everything running)
./ms_init SHLonly.dat
sleep 5

# Send SHL the required first command "INI".
# 75; 2.5; rack 1 on, all other racks off
./msei SHL INI '00075&2.5&100000'
# Good idea to wait a moment, since it is required that SHL
# get INI before any other command:
sleep 1


# Send MCS/Scheduler shutdown command
#./msei MCS SHT



