#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>

#include "libsub.h"

sub_handle* fh = NULL;

const int gpio_table[33] = {-1, 
    8, 9, 10, 11, 12, 13, 14, 15, 
    24, 25, 26, 27, 28, 29, 30, 31, 
    0, 1, 2, 3, 4, 5, 6, 7, 
    23, 22, 21, 20, 19, 18, 17, 16
};

int main(int argc, char* argv[]) {
    int pin, gpio, found, config;
    struct usb_device* dev = NULL;
    
    if( argc != 1+1 ) {
        fprintf(stderr, "Expected a single pin number, %i found\n", argc-1);
        return 1;
    }
    pin = strtod(argv[1], NULL);
    gpio = gpio_table[pin];
    printf("pin %i -> gpio %i\n", pin, gpio);
    
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
    
    sub_gpio_config(fh, 1<<gpio, &config, 1<<gpio);
    printf("Pin %i Direction: %i\n", pin, (config>>gpio)&1);
    sub_gpio_write(fh, 1<<gpio, &config, 1<<gpio);
    printf("Pin %i State: %i\n", pin, (config>>gpio)&1);
    
    sub_close(fh);
    
    return 0;
}
