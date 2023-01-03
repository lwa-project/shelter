#include <iostream>
#include <stdexcept>
#include <thread>
#include <chrono>

#include "libsub.h"
#include "hvac_common.hpp"


std::list<std::string> list_sub20s() {
  std::list<std::string> sub20_sns;
  
  sub_device dev = nullptr;
  sub_handle fh = nullptr;
  
  char found_sn[20];
  int success, open_attempts = 0;
  while( (dev = sub_find_devices(dev)) ) {
    // Open the USB device (or die trying)
    fh = sub_open(dev);
    while( (fh == nullptr) && (open_attempts < SUB20_OPEN_MAX_ATTEMPTS) ) {
      open_attempts++;
      std::this_thread::sleep_for(std::chrono::milliseconds(SUB20_OPEN_WAIT_MS));
      
      fh = sub_open(dev);
    }
    if( fh == nullptr ) {
      continue;
    }
    
    success = sub_get_serial_number(fh, found_sn, sizeof(found_sn));
    if( !success ) {
      continue;
    }
    
    sub20_sns.push_back(std::string(found_sn));
    
    sub_close(fh);
  }
  
  return sub20_sns;
}

bool Sub20::open() {
  sub_device dev = nullptr;
  
  bool found = false;
  char found_sn[20];
  int success, open_attempts = 0;
  while( (!found) && (dev = sub_find_devices(dev)) ) {
    // Open the USB device (or die trying)
    _fh = sub_open(dev);
    while( (_fh == nullptr) && (open_attempts < SUB20_OPEN_MAX_ATTEMPTS) ) {
      open_attempts++;
      std::this_thread::sleep_for(std::chrono::milliseconds(SUB20_OPEN_WAIT_MS));
      
      _fh = sub_open(dev);
    }
    if( _fh == nullptr ) {
      continue;
    }
    
    success = sub_get_serial_number(_fh, found_sn, sizeof(found_sn));
    if( !success ) {
      continue;
    }
    
    if( !strcmp(found_sn, _sn.c_str()) ) {
      found = true;
    } else {
      sub_close(_fh);
    }
  }

  // Make sure we actually have a SUB-20 device
  if( !found ) {
    _fh = nullptr;
  }
  return found;
}


std::list<uint8_t> Sub20::list_i2c_devices() {
  std::list<uint8_t> i2c_addresses_list;
  
  int success, nDev;
  char i2c_addresses[128];
  success = sub_i2c_scan(_fh, &nDev, i2c_addresses);
  if( !success ) {
    for(int i=0; i<nDev; i++) {
      i2c_addresses_list.push_back(i2c_addresses[i]);
    }
  }
  
  return i2c_addresses_list;
}

float Sub20::read_adc(int32_t mux) {
  int status;
  bool success = _adc_ready;
  if( !success ) {
    success = this->enable_adc();
  }
  
  int raw;
  float value = -1.0;
  if( success ) {
    status = sub_adc_single(_fh, &raw, mux);
    if( !status ) {
      value = (raw/1023.0) * SUB20_VREF_ADC;
    }
  }
  
  return value;
}
