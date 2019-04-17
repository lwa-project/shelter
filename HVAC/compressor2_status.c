#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>

#include "libsub.h"
#include "hvac_config.h"

sub_handle* fh = NULL;

int main(void) {
	int found, config, count, data;
	float value;
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
	
	sub_gpio_read(fh, &config);
	if( (config>>COMPRESSOR2_GPIO)&1 ) {
	    sprintf(status, "disabled");
	} else {
	    sprintf(status, "enabled");
	}
	
	sub_adc_config(fh, ADC_ENABLE|ADC_REF_VCC);
	count = 0;
	value = 0.0;
	while( count < N_POLL_ADC ) {
		sub_adc_single(fh, &data, COMPRESSOR2_VOLTAGE_ADC);
		value += data/1023.*VREF_ADC;
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
