#ifndef __HVAC_COMMON_HPP
#define __HVAC_COMMON_HPP

/*
  hvacCommon.h - Header library with common values needed for using the SUB-20
  device.
*/

#include <string>
#include <cstring>
#include <stdexcept>
#include <list>
#include <mutex>

#include "libsub.h"

// SUB-20 device opening control
#define SUB20_OPEN_MAX_ATTEMPTS 20
#define SUB20_OPEN_WAIT_MS  5


// Reference voltage for the ADCs
#define SUB20_VREF_ADC  5.0


// Get a list of all SUB-20 serial numbers
std::list<std::string> list_sub20s();


// Class to simplify interfacing with a SUB-20 via the libsub library
class Sub20 {
private:
  std::string _sn;
  sub_handle  _fh;
  bool        _adc_ready;
  std::mutex  _gpio_lock;
  int32_t     _gpio_status;
  
  inline bool enable_adc() {
    int status;
    status = sub_adc_config(_fh, ADC_ENABLE|ADC_REF_VCC);
    _adc_ready = (status == 0);
    return _adc_ready;
  }
public:
  Sub20(std::string sn): _sn(""), _fh(NULL), _adc_ready(false), _gpio_status(0) {
    _sn = sn;
  }
  ~Sub20() {
    if( _fh != nullptr ) {
      sub_close(_fh);
    }
  }
  bool open();
  std::list<uint8_t> list_i2c_devices();
  inline bool read_i2c(uint8_t addr, uint8_t reg, char* data, int size) {
    int status;
    status = sub_i2c_read(_fh, addr, reg, 1, data, size);
    return (status == 0);
  }
  inline bool write_i2c(uint8_t addr, uint8_t reg, char* data, int size) {
    int status;
    status = sub_i2c_write(_fh, addr, reg, 1, data, size);
    return (status == 0);
  }
  inline int read_gpio(int32_t mux) {
    int config, status;
    status = sub_gpio_read(_fh, &config);
    if( status == 0) {
      config = (config >> mux) & 1;
    } else {
      config = -1;
    }
    return config;
  }
  inline bool write_gpio(int32_t value, int32_t mux) {
    int config, status;
    _gpio_lock.lock();
    status = sub_gpio_config(_fh, 1<<mux, &_gpio_status, 1<<mux);
    _gpio_lock.unlock();
    
    if( status == 0 ) {
      config = 0;
      status = sub_gpio_write(_fh, value<<mux, &config, 1<<mux);
    }
    
    return (status == 0);
  }
  float read_adc(int32_t mux);
};

#endif // __HVAC_COMMON_HPP
