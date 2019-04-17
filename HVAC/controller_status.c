#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>

#include "libsub.h"
#include "hvac_config.h"
#include "utils.h"

sub_handle* fh = NULL;

int main(void) {
	int found, config, count, adc[2];
	float data[2], value[2];
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
	
	gpio_single_value(fh, &config, CONTROLLER_GPIO);
	if( config ) {
	    sprintf(status, "disabled");
	} else {
	    sprintf(status, "enabled");
	}
	
	adc[0] = CONTROLLER1_VOLTAGE_ADC;
	adc[1] = CONTROLLER2_VOLTAGE_ADC;
	sub_adc_config(fh, ADC_ENABLE|ADC_REF_VCC);
	count = 0;
	value[0] = 0.0;
	value[1] = 0.0;
	while( count < N_POLL_ADC ) {
	    adc_read_value(fh, data, adc, 2);
		value[0] += data[0];
		value[1] += data[1];
		count++;
		usleep(1000);
	}
	value[0] /= count;
	value[1] /= count;
	if( value[0] > 2.5 ) {
	    sprintf(status, "%s off", status);
	} else {
	    sprintf(status, "%s on", status);
	}
	if( value[1] > 2.5 ) {
	    sprintf(status, "%s off", status);
	} else {
	    sprintf(status, "%s on", status);
	}
	printf("controller: %s\n", status);
	
	sub_close(fh);
	
	return 0;
}
