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
	int pin, adc, found, data;
	struct usb_device* dev = NULL;
	
	if( argc != 1+1 ) {
		fprintf(stderr, "Expected a single pin number, %i found\n", argc-1);
		return 1;
	}
	pin = strtod(argv[1], NULL);
	adc = adc_table[pin];
	printf("pin %i -> adc %i\n", pin, adc);
	
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
	while( found < 100 ) {
		sub_adc_single(fh, &data, adc);
		printf("%03i: %+0.3f V\n", found, data/1023.*5.0);
		usleep(1000);
		found++;
	}
	
	sub_close(fh);
	
	return 0;
}
