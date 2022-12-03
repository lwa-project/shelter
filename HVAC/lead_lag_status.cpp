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
      
      float mean1 = 0.0, mean2 = 0.0;
      int count1 = 0, count2 = 0;
      float temp;
      for(int i=0; i<N_POLL_ADC; i++) {
        temp = sub20->read_adc(LEADLAG_UNIT1_ADC);
        if( temp >= 0 ) {
          mean1 += temp;
          count1++;
        }
        temp = sub20->read_adc(LEADLAG_UNIT2_ADC);
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
      
      if( (mean1 > mean2) && (mean1 >= 0.0) && (mean2 >= 0.0) ){
        std::cout << "lead: 1" << std::endl;
      } else if( (mean2 > 0.001) && (mean1 >= 0.0) && (mean2 >= 0.0) ) {
        std::cout << "lead: 2" << std::endl;
      } else {
        std::cout << "lead: unk" << std::endl;
      }
      
      break;
    }
  }
  
  if( !found ) {
    std::cout << "No device found, exiting!" << std::endl;
    std::exit(EXIT_FAILURE);
  }
  
  std::exit(EXIT_SUCCESS);
}
