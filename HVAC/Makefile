#------------------------------------------------------------------------------
# Main Targets
#------------------------------------------------------------------------------
all: LIBSUB controller_enable controller_disable controller_status \
     compressor1_enable compressor1_disable compressor1_status \
     compressor2_enable compressor2_disable compressor2_status \
     lead_lag_status \
     gpio_on gpio_off \
     adc_read

#------------------------------------------------------------------------------
# Config
#------------------------------------------------------------------------------
OS = $(shell uname)

#------------------------------------------------------------------------------
# Compiler
#------------------------------------------------------------------------------

# C Compiler and Linker Executable
CC      := $(CROSS)gcc


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
CFLAGS += -Ilibsub
LDFLAGS += -L/usr/local/lib -lusb-1.0 -lm

#------------------------------------------------------------------------------
# Common rules
#------------------------------------------------------------------------------
%.o:	%.c  
	$(CC) -c $(CFLAGS) -o $@ $<


#------------------------------------------------------------------------------
# Target Builds
# 
#------------------------------------------------------------------------------
LIBSUB: 
	make -C libsub

controller_enable: controller_enable.o hvac_config.h
	$(CC) -o $@ $^ $(LDFLAGS)

controller_disable: controller_disable.o hvac_config.h
	$(CC) -o $@ $^ $(LDFLAGS)

controller_status: controller_status.o utils.o hvac_config.h
	$(CC) -o $@ $^ $(LDFLAGS)

compressor1_enable: compressor1_enable.o hvac_config.h
	$(CC) -o $@ $^ $(LDFLAGS)

compressor1_disable: compressor1_disable.o hvac_config.h
	$(CC) -o $@ $^ $(LDFLAGS)

compressor1_status: compressor1_status.o utils.o hvac_config.h
	$(CC) -o $@ $^ $(LDFLAGS)

compressor2_enable: compressor2_enable.o hvac_config.h
	$(CC) -o $@ $^ $(LDFLAGS)

compressor2_disable: compressor2_disable.o hvac_config.h
	$(CC) -o $@ $^ $(LDFLAGS)

compressor2_status: compressor2_status.o utils.o hvac_config.h
	$(CC) -o $@ $^ $(LDFLAGS)

lead_lag_status: lead_lag_status.o utils.o hvac_config.h
	$(CC) -o $@ $^ $(LDFLAGS)

gpio_on: gpio_on.o
	$(CC) -o $@ $^ $(LDFLAGS)

gpio_off: gpio_off.o
	$(CC) -o $@ $^ $(LDFLAGS)
	
adc_read: adc_read.o utils.o hvac_config.h
	$(CC) -o $@ $^ $(LDFLAGS)

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
	rm -f *_enable *_disable *_status gpio_on gpio_off adc_read
	make -C libsub clean

