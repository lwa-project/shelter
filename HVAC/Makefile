all: compressor2_status

compressor2_status: compressor1_status
	sed -e 's/HVAC_UNIT_ID = 1/HVAC_UNIT_ID = 2/;' compressor1_status > compressor2_status
	chmod +x compressor2_status

install:
	cp controller_status /usr/local/bin/
	cp compressor[12]_status /usr/local/bin/
	cp lead_lag_status /usr/local/bin/

clean:
	rm -f compressor2_status *_disable *_enable *.o
