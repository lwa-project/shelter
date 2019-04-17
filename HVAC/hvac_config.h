#ifndef __HVAC_CONFIG_H
#define __HVAC_CONFIG_H

// GPIO setup for the relays
//// pin 9
#define CONTROLLER_GPIO  24
//// pin 10
#define COMPRESSOR1_GPIO 25
//// pin 11
#define COMPRESSOR2_GPIO 26

// ADC setup for the voltage detection
//// pin 30
#define CONTROLLER1_VOLTAGE_ADC  2
//// pin 29
#define COMPRESSOR1_VOLTAGE_ADC  3
//// pin 28
#define CONTROLLER2_VOLTAGE_ADC  4
//// pin 27
#define COMPRESSOR2_VOLTAGE_ADC  5 

// ADC setup for the lead/lag unit determination
//// pin 32
#define LEADLAG_UNIT1_ADC  0
//// pin 31
#define LEADLAG_UNIT2_ADC  1

// Number of times to poll the ADC value
#define N_POLL_ADC  10

// Reference voltage for the ADCs
#define VREF_ADC  5.0

#endif
