#!/bin/bash

# Script to reset both HVC compressors at a station.  This is done by
# disabling the control signal for the lead compressor for ~3 minutes
# followed by disabling the signal for the lag compressor after that.

date > reset.log 2>&1

lead_one=`/usr/local/bin/lead_lag_status | grep 1 `
if [[ "${lead_one}" != "" ]]; then
        /usr/local/bin/compressor1_disable >> reset.log 2>&1
        sleep 190
        /usr/local/bin/compressor1_enable >> reset.log 2>&1
        sleep 10
        /usr/local/bin/compressor2_disable >> reset.log 2>&1
        sleep 190
        /usr/local/bin/compressor2_enable >> reset.log 2>&1
else
        /usr/local/bin/compressor2_disable >> reset.log 2>&1
        sleep 190
        /usr/local/bin/compressor2_enable >> reset.log 2>&1
        sleep 10
        /usr/local/bin/compressor1_disable >> reset.log 2>&1
        sleep 190
        /usr/local/bin/compressor1_enable >> reset.log 2>&1
fi

