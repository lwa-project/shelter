#include <iostream>
#include <string>
#include <list>

#include "libsub.h"
#include "hvac_config.hpp"
#include "hvac_common.hpp"

int main() {
  std::list<std::string> sub20s = list_sub20s();
  
  bool found = false;
  for(std::string& sn: sub20s) {
    Sub20 *sub20 = new Sub20(sn);
    
    bool success = sub20->open();
    if( success ) {
      found = true;
      sub20->write_gpio(ENABLE_DISABLE_DIR, CONTROLLER_GPIO);
      int is_disabled = sub20->read_gpio(CONTROLLER_GPIO);
      if( is_disabled > 0 ) {
        std::cout << "controller: disabled" << std::endl;
      } else {
        std::cout << "controller: enabled" << std::endl;
      }
      
      break;
    }
    
    delete sub20;
  }
  
  if( !found ) {
    std::cerr << "No device found, exiting!" << std::endl;
    std::exit(EXIT_FAILURE);
  }
  
  std::exit(EXIT_SUCCESS);
}
