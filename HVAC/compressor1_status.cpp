#include <iostream>
#include <string>
#include <list>
#include <thread>
#include <chrono>

#include "libsub.h"
#include "hvac_config.hpp"
#include "hvac_common.hpp"

int main(void) {
  std::list<std::string> sub20s = list_sub20s();
  
  bool found = false;
  for(std::string& sn: sub20s) {
    Sub20 *sub20 = new Sub20(sn);
    
    bool success = sub20->open();
    if( success ) {
      found = true;
      
      int is_disabled = sub20->read_gpio(COMPRESSOR1_GPIO);
      
      float mean = 0.0;
      int count = 0;
      float temp;
      for(int i=0; i<N_POLL_ADC; i++) {
        temp = sub20->read_adc(COMPRESSOR1_VOLTAGE_ADC);
        if( temp >= 0 ) {
          mean += temp;
          count++;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
      }
      if( count > 0 ) {
        mean /= count;
      } else {
        mean = -1.0;
      }
      
      std::cout << "compressor1: ";
      if( is_disabled ) {
        std::cout << "disabled ";
      } else {
        std::cout << "enabled ";
      }
      if( mean > 2.5 ) {
        std::cout << "off ";
      } else if( mean >= 0 ) {
        std::cout << "on ";
      } else {
        std::cout << "unk ";
      }
      std::cout << std::endl;
      
      break;
    }
  }
  
  if( !found ) {
    std::cout << "No device found, exiting!" << std::endl;
    std::exit(EXIT_FAILURE);
  }
  
  std::exit(EXIT_SUCCESS);
}
