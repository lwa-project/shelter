all: compressor2_status

compressor2_status: compressor1_status
	sed -e 's/HVAC_UNIT_ID = 1/HVAC_UNIT_ID = 2/;' compressor1_status > compressor2_status
	chmod +x compressor2_status

install:
	ln -sf controller_status /usr/local/bin/controller_status
	ln -sf compressor1_status /usr/local/bin/compressor1_status
	ln -sf compressor2_status /usr/local/bin/compressor2_status
	ln -sf lead_lag_status /usr/local/bin/lead_lag_status
