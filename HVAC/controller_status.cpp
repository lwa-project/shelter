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
      
      int is_disabled = sub20->read_gpio(CONTROLLER_GPIO);
      
      float mean1 = 0.0, mean2 = 0.0;
      int count1 = 0, count2 = 0;
      float temp;
      for(int i=0; i<N_POLL_ADC; i++) {
        temp = sub20->read_adc(CONTROLLER1_VOLTAGE_ADC);
        if( temp >= 0 ) {
          mean1 += temp;
          count1++;
        }
        temp = sub20->read_adc(CONTROLLER2_VOLTAGE_ADC);
        if( temp >= 0 ) {
          mean2 += temp;
          count2++;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
      }
      if( count1 > 0 ) {
        mean1 /= count1;
      } else {
        mean1 = -1.0;
      }
      if( count2 > 0 ) {
        mean2 /= count2;
      } else {
        mean2 = -1.0;
      }
      
      std::cout << "controller: ";
      if( is_disabled ) {
        std::cout << "disabled ";
      } else {
        std::cout << "enabled ";
      }
      if( mean1 > 2.5 ) {
        std::cout << "off ";
      } else if( mean1 >= 0 ) {
        std::cout << "on ";
      } else {
        std::cout << "unk ";
      }
      if( mean2 > 2.5 ) {
        std::cout << "off ";
      } else if( mean2 >= 0 ) {
        std::cout << "on ";
      } else {
        std::cout << "unk ";
      }
      std::cout << std::endl;
      
      break;
    }
    
    delete sub20;
  }
  
  if( !found ) {
    std::cout << "No device found, exiting!" << std::endl;
    std::exit(EXIT_FAILURE);
  }
  
  std::exit(EXIT_SUCCESS);
}
