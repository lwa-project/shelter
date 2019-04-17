#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>

#include "libsub.h"
#include "hvac_config.h"
#include "utils.h"

sub_handle* fh = NULL;

int main(void) {
	int found, config, count;
	float data, value;
	char status[256];
	struct usb_device* dev = NULL;
	
	found = 0;
	while( (dev = sub_find_devices(dev)) ) {
		// Open the USB device (or die trying)
		fh = sub_open(dev);
		if( !fh ) {
			continue;
		}
		found = 1;
	}
	if( !found ) {
		fprintf(stderr, "No device found, exiting!\n");
		return 1;
	}
	
	gpio_single_value(fh, &config, COMPRESSOR2_GPIO);
	if( config ) {
	    sprintf(status, "disabled");
	} else {
	    sprintf(status, "enabled");
	}
	
	sub_adc_config(fh, ADC_ENABLE|ADC_REF_VCC);
	count = 0;
	value = 0.0;
	while( count < N_POLL_ADC ) {
		adc_single_value(fh, &data, COMPRESSOR2_VOLTAGE_ADC);
		value += data;
		count++;
		usleep(1000);
	}
	value /= count;
	if( value > 2.5 ) {
		sprintf(status, "%s off", status);
	} else {
		sprintf(status, "%s on", status);
	}
	printf("compressor2: %s\n", status);
	
	sub_close(fh);
	
	return 0;
}
