#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <dirent.h>
#include <errno.h>
#include <unistd.h>
#include <sys/file.h>
#include <sys/stat.h>

#include "libsub.h"
#include "utils.h"

/*
  GPIO wrapping functions
*/

int gpio_single_value(sub_handle hndl, int* data, int mux) {
    int config, status;
    status = sub_gpio_read(hndl, &config);
    *data = (config>>mux)&1;
    return status;
}

int gpio_read_value(sub_handle hndl, int* data, int* mux, int reads) {
    int config, status, i;
    status = sub_gpio_read(hndl, &config);
    for(i=0; i<reads; i++) {
        *(data + i) = (config>>*(mux + i))&1;
    }
    return status;
}


/*
  ADC wrapping functions
*/

// Reference voltage for the ADCs
#define VREF_ADC  5.0

float adc_to_value(int adc) {
    return (adc/1023.0)*VREF_ADC;
}

int adc_single_value(sub_handle hndl, float* data, int mux) {
    int raw, status;
    status = sub_adc_single(hndl, &raw, mux);
    *data = adc_to_value(raw);
    return status;
}
    
int adc_read_value(sub_handle hndl, float* data, int* mux, int reads) {
    int *raw, status, i;
    raw = (int*) malloc(reads*sizeof(int));
    status = sub_adc_read(hndl, raw, mux, reads);
    for(i=0; i<reads; i++) {
        *(data + i) = adc_to_value(*(raw + i));
    }
    free(raw);
    return status;
}


/*
  Device locking functions
*/

// File-backed lockout directory
#define LOCK_DIRECTORY "/dev/shm/HVAC"

// Lockout expiration in seconds
#define LOCK_EXPIRATION 180

int expiring_lockout(char* name) {
    int status, rc;
    char dirname[256], filename[256], command[256];
    sprintf(dirname, "%s", LOCK_DIRECTORY);
    sprintf(filename, "%s/%s", dirname, name);
    
    // Make sure we have a directory to save to for state
    DIR* d = opendir(dirname);
    if( d ) {
        // Good, we have one
        closedir(d);
    } else if (ENOENT == errno) { 
        // Ok, we need to make one
        sprintf(command, "mkdir %s", dirname);
        rc = system(command);
        if( rc == -1 ) {
            return -1;
        }
    } else {
        // Bad, something else has occurred
        return -2;
    }
    
    // Lock us up to prevent multiple commands from changing the state at the same time
    sprintf(dirname, "%s/hvac.lock", dirname);
    int ld = open(dirname, O_RDWR);
    flock(ld, LOCK_EX);
    
    // See if we have an existing lock file to use
    FILE* f = fopen(filename, "r");
    struct stat attrib;
    unsigned long now = (unsigned long) time(NULL);
    if( f ) {
        // Good, read in the timestamp and decide what to do
        fclose(f);
        stat(filename, &attrib);
        if( now-attrib.st_mtime >= LOCK_EXPIRATION ) {
            // It's an old file, update it and say that we are good to go
            sprintf(command, "touch %s", filename);
            rc = system(command);
            if( rc == -1 ) {
                status = -3;
            } else {
                status = 1;
            }
        } else {
            // It's a new file, leave it alone and say that we are *not* good to go
            status = 0;
        }
        
    } else if (ENOENT == errno) {
        // Ok, we need to make the lock file and stick in the timestamp
        sprintf(command, "touch %s", filename);
        rc = system(command);
        if( rc == -1 ) {
            status = -3;
        } else {
            status = 1;
        }
    } else {
        // Bad, something else has occurred
        status = -4;
    }
    
    // Unlock
    flock(ld, LOCK_UN);
    close(ld);
    unlink(dirname);
    
    return status;
}
