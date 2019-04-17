#ifndef __UTILS_H
#define __UTILS_H

#include "libsub.h"

/*
  GPIO wrapping functions
*/

int gpio_single_value(sub_handle hndl, int* data, int mux);

int gpio_read_value(sub_handle hndl, int* data, int* mux, int reads);


/*
  ADC wrapping functions
*/

float adc_to_value(int adc);

int adc_single_value(sub_handle hndl, float* data, int mux );

int adc_read_value(sub_handle hndl, float* data, int* mux, int reads);


/*
  Device locking functions
*/

int expiring_lockout(char* name);

#endif  // __UTILS_H
