#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>

#include "libsub.h"
#include "hvac_config.h"

sub_handle* fh = NULL;

int main(void) {
	int found, config;
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
	
	sub_gpio_config(fh, 1<<CONTROLLER_GPIO, &config, 1<<CONTROLLER_GPIO);
	sub_gpio_write(fh, 0, &config, 1<<CONTROLLER_GPIO);
	if( (config>>CONTROLLER_GPIO)&1 ) {
	    printf("controller: disabled\n");
	} else {
	    printf("controller: enabled\n");
	}
	
	sub_close(fh);
	
	return 0;
}
