#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>

#include "libsub.h"

sub_handle* fh = NULL;

const int adc_table[33] = {-1, 
	-1, -1, -1, -1, -1, -1, -1, -1, 
	-1, -1, -1, -1, -1, -1, -1, -1, 
	-1, -1, -1, -1, -1, -1, -1, -1, 
	7, 6, 5, 4, 3, 2, 1, 0
};

int main(int argc, char* argv[]) {
	int pin[2], adc[2], found, data[2];
	float value[2];
	struct usb_device* dev = NULL;
	
	if( argc != 1 ) {
		fprintf(stderr, "Expected no arguments, %i found\n", argc-1);
		return 1;
	}
	pin[0] = 32;
	pin[1] = 21;
	adc[0] = adc_table[pin[0]];
	adc[1] = adc_table[pin[1]];
	printf("pin %i -> adc %i\n", pin[0], adc[0]);
	printf("pin %i -> adc %i\n", pin[1], adc[1]);
	
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
	
	sub_adc_config(fh, ADC_ENABLE|ADC_REF_VCC);
	found = 0;
	value[0] = 0.0;
	value[1] = 0.0;
	while( found < 10 ) {
		sub_adc_read(fh, data, adc, 2);
		value[0] += data[0]/1023.*5.0;
		value[1] += data[1]/1023.*5.0;
		found++;
		usleep(1000);
	}
	value[0] /= found;
	value[1] /= found;
	if( value[0] > value[1] ) {
		printf("lead: 1\n");
	} else {
		printf("lead: 2\n");
	}
	sub_close(fh);
	
	return 0;
}
