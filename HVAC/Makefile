#------------------------------------------------------------------------------
# Main Targets
#------------------------------------------------------------------------------
all: LIBSUB controller_enable controller_disable controller_status \
     compressor1_enable compressor1_disable compressor1_status \
     compressor2_enable compressor2_disable compressor2_status \
     lead_lag_status

#------------------------------------------------------------------------------
# Config
#------------------------------------------------------------------------------
OS = $(shell uname)

#------------------------------------------------------------------------------
# Compiler
#------------------------------------------------------------------------------

# C Compiler and Linker Executable
CC      := $(CROSS)gcc
CXX     := $(CROSS)g++


#------------------------------------------------------------------------------
# Inc && Lib 
#------------------------------------------------------------------------------
LDLIB   := 

#------------------------------------------------------------------------------
# Compiler Flags 
#------------------------------------------------------------------------------
CFLAGS  := -O2 -Wall

#------------------------------------------------------------------------------
# Linker Flags 
#------------------------------------------------------------------------------
LDFLAGS := -lsub -Llibsub
CFLAGS += -Ilibsub -I.
LDFLAGS += -L/usr/local/lib -lusb-1.0 -lm

#------------------------------------------------------------------------------
# Common rules
#------------------------------------------------------------------------------
%.o:	%.c  
	$(CC) -c $(CFLAGS) -o $@ $<
%.o:	%.cpp
	$(CXX) -c -std=c++11 $(CFLAGS) -o $@ $<

#------------------------------------------------------------------------------
# Target Builds
# 
#------------------------------------------------------------------------------
LIBSUB: 
	make -C libsub

controller_enable.o: controller_toggle.cpp hvac_config.hpp
	$(CXX) -c -std=c++11 $(CFLAGS) -DENABLE_DISABLE_DIR=0 -o $@ $<

controller_disable.o: controller_toggle.cpp hvac_config.hpp
	$(CXX) -c -std=c++11 $(CFLAGS) -DENABLE_DISABLE_DIR=1 -o $@ $<
	
controller_enable: controller_enable.o hvac_common.o
	$(CXX) -o $@ $^ $(LDFLAGS)
	
controller_disable: controller_disable.o hvac_common.o
	$(CXX) -o $@ $^ $(LDFLAGS)


controller_status: controller_status.o hvac_common.o
	$(CXX) -o $@ $^ $(LDFLAGS)


compressor2_toggle.cpp: compressor1_toggle.cpp
	sed -e 's/compressor1/compressor2/g;s/COMPRESSOR1/COMPRESSOR2/g' $^ > $@
	
compressor%_enable.o: compressor%_toggle.cpp hvac_config.hpp
	$(CXX) -c -std=c++11 $(CFLAGS) -DENABLE_DISABLE_DIR=0 -o $@ $<

compressor%_disable.o: compressor%_toggle.cpp hvac_config.hpp
	$(CXX) -c -std=c++11 $(CFLAGS) -DENABLE_DISABLE_DIR=1 -o $@ $<

compressor%_enable: compressor%_enable.o hvac_common.o
	$(CXX) -o $@ $^ $(LDFLAGS)
	
compressor%_disable: compressor%_disable.o hvac_common.o
	$(CXX) -o $@ $^ $(LDFLAGS)


compressor2_status.cpp: compressor1_status.cpp
	sed -e 's/compressor1/compressor2/g;s/COMPRESSOR1/COMPRESSOR2/g' $^ > $@
	
compressor%_status: compressor%_status.o hvac_common.o
	$(CXX) -o $@ $^ $(LDFLAGS)


lead_lag_status: lead_lag_status.o hvac_common.o
	$(CXX) -o $@ $^ $(LDFLAGS)

install:
	cp controller_*able /usr/local/bin/
	cp controller_status /usr/local/bin/
	cp compressor[12]_*able /usr/local/bin/
	cp compressor[12]_status /usr/local/bin/
	cp lead_lag_status /usr/local/bin/
	chown root:root /usr/local/bin/controller_* \
			/usr/local/bin/compressor[12]_* \
			/usr/local/bin/lead_lag_status
	chmod +s /usr/local/bin/controller_* \
                        /usr/local/bin/compressor[12]_* \
                        /usr/local/bin/lead_lag_status

clean:
	rm -f *.o *.out *.err *.exe *.a *.so
	rm -f *_enable *_disable *_status
	make -C libsub clean
