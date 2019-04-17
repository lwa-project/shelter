#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>

#include "libsub.h"
#include "hvac_config.h"

sub_handle* fh = NULL;

int main(void) {
	int found, count, adc[2], data[2];
	float value[2];
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
	
	adc[0] = LEADLAG_UNIT1_ADC;
	adc[1] = LEADLAG_UNIT2_ADC;
	sub_adc_config(fh, ADC_ENABLE|ADC_REF_VCC);
	count = 0;
	value[0] = 0.0;
	value[1] = 0.0;
	while( count < N_POLL_ADC ) {
		sub_adc_read(fh, data, adc, 2);
		value[0] += data[0]/1023.*VREF_ADC;
		value[1] += data[1]/1023.*VREF_ADC;
		count++;
		usleep(1000);
	}
	value[0] /= count;
	value[1] /= count;
	if( value[0] > value[1] ) {
		printf("lead: 1\n");
	} else {
		printf("lead: 2\n");
	}
	
	sub_close(fh);
	
	return 0;
}
