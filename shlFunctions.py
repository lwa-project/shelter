# -*- coding: utf-8 -*-
"""
Module for dealing with all of the stuff the SHL deals with (INI, SHT, 
turning on/off ports, etc.)
"""

import os
import time
import logging
import threading
from functools import reduce

from pysnmp.entity.rfc3413.oneliner import cmdgen

from shlThreads import *
from shlQube import *

__version__ = "0.5"
__all__ = ["commandExitCodes", "isHalfIncrements", "ShippingContainer"]


shlFunctionsLogger = logging.getLogger('__main__')


# Create a semaphore to make sure not too many threads process the unreachable list at a time
ListLock = threading.Semaphore()


commandExitCodes = {0x00: 'Process accepted without error', 
                    0x01: 'Invalid temperature set point', 
                    0x02: 'Invalid temperature differential', 
                    0x03: 'Invalid PDU rack number', 
                    0x04: 'Invalid PDU port number', 
                    0x05: 'Invalid PDU control keyword', 
                    0x06: 'Invalid command arguments', 
                    0x07: 'Blocking operation in progress', 
                    0x08: 'Subsystem already initialized', 
                    0x09: 'Subsystem needs to be initialized'}


def isHalfIncrements(value):
    """
    Check if a value is one half-increments, i.e., 0.0 or 0.5, or not.  Return True
    if it is and False if its not.
    """
    
    valueTen = value*10.0
    if valueTen % 5 != 0:
        return False
    else:
        return True


class ShippingContainer(object):
    """
    Class for interacting with the Shelter subsystem.
    
    A note about exit codes from control commands (INI, TMP, etc.):
     * See commandExitCodes
    """
    
    def __init__(self, config):
        self.config = config
        
        # SHL system information
        self.subSystem = 'SHL'
        self.serialNumber = self.config['serial_number']
        self.version = str(__version__)
        
        # SHL system state
        self.currentState = {}
        self.currentState['status'] = 'SHUTDWN'
        self.currentState['info'] = 'Need to INI SHL'
        self.currentState['lastLog'] = 'Welcome to SHL S/N %s, version %s' % (self.serialNumber, self.version)
        
        ## Operational state
        self.currentState['ready'] = False
        self.currentState['activeProcess'] = []
        self.currentState['setPoint'] = 0
        self.currentState['diffPoint'] = 0
        self.currentState['nRacks'] = 0
        self.currentState['rackPresent'] = []
        self.currentState['unreachableDevices'] = {}
        
        ## Monitoring and background threads
        self.currentState['tempThreads'] = None
        self.currentState['enviroThread'] = None
        self.currentState['pduThreads'] = None
        self.currentState['wxThread'] = None
        self.currentState['strikeThread'] = None
        self.currentState['outageThread'] = None
        
        ## Scheduler for clearing the unreachable device list
        self.scheduler = None
        
        # Update the configuration
        self.updateConfig()
        
    def updateConfig(self, config=None):
        """
        Update the stored configuration.
        """
        
        if config is not None:
            self.config = config
        return True
        
    def getState(self):
        """
        Return the current system state as a dictionary.
        """
        
        return self.currentState
        
    def ini(self, data, config=None):
        """
        Initialize SHL (in a separate thread).
        """
        
        # Check for other operations in progress that could be blocking (INI or SHT)
        if 'INI' in self.currentState['activeProcess'] or 'SHT' in self.currentState['activeProcess']:
            shlFunctionsLogger.warning("INI command rejected due to process list %s", ' '.join(self.currentState['activeProcess']))
            self.currentState['lastLog'] = 'INI: %s - %s is active and blocking' % (commandExitCodes[0x07], self.currentState['activeProcess'])
            return False, 0x07
            
        # Check to see if the system has already been initialized
        if self.currentState['ready']:
            shlFunctionsLogger.warning("INI command rejected due to system already running")
            self.currentState['lastLog'] = 'INI: %s' % commandExitCodes[0x08]
            return False, 0x08
            
        # Check to see if there is a valid number of command arguments
        fields = data.strip().split('&')
        if len(fields) != 3:
            shlFunctionsLogger.warning("INI command rejected due to invalid &-separated argument count")
            self.currentState['lastLog'] = 'INI: %s' % commandExitCodes[0x06]
            return False, 0x06
        
        # Convert data to numbers/strings - there should be three
        setPoint  = float(fields[0])
        diffPoint = float(fields[1])
        nRacks    = fields[2]
        
        # Validate the temperatures
        if not isHalfIncrements(setPoint) or setPoint < self.config['hvac']['temp_min'] or setPoint > self.config['hvac']['temp_max']:
            shlFunctionsLogger.warning("INI command rejected due to invalid set point")
            self.currentState['lastLog'] = 'INI: %s' % commandExitCodes[0x01]
            return False, 0x01
            
        # Validate differential
        if not isHalfIncrements(diffPoint) or diffPoint < self.config['hvac']['diff_min'] or diffPoint > self.config['hvac']['diff_max']:
            shlFunctionsLogger.warning("INI command rejected due to invalid differential")
            self.currentState['lastLog'] = 'INI: %s' % commandExitCodes[0x02]
            return False, 0x02
            
        # Update the configuration
        self.updateConfig(config=config)
        
        # Start the process in the background
        thread = threading.Thread(target=self.__iniProcess, args=(setPoint, diffPoint, nRacks))
        thread.setDaemon(1)
        thread.start()
        
        return True, 0
        
    def __iniProcess(self, setPoint, diffPoint, nRacks):
        """
        Thread base to initialize ASP.  Update the current system state as needed.
        """
        
        # Start the timer
        tStart = time.time()
        
        # Update system state
        self.currentState['ready'] = False
        self.currentState['status'] = 'BOOTING'
        self.currentState['info'] = 'Running INI sequence'
        self.currentState['activeProcess'].append('INI')
        
        # Stop all threads.  If the don't exist yet, create them.
        ## Scheduler
        if self.scheduler is not None:
            self.scheduler.stop()
        else:
            self.scheduler = EventScheduler()
        ## Enviromenal monitor
        if self.currentState['enviroThread'] is not None:
            self.currentState['enviroThread'].stop()
        else:
            self.currentState['enviroThread'] = None
            for c,k in enumerate(sorted(self.config['enviromux']['devices'].keys())):
                v = self.config['enviromux']['devices'][k]
                
                nT = EnviroMux(v['ip'], v['port'], cmdgen.CommunityData(*v['security_model']),
                               c+1, sensorList=v['sensor_list'], description=v['description'], 
                               MonitorPeriod=self.config['enviromux']['monitor_period'], SHLCallbackInstance=self)
                self.currentState['enviroThread'] = nT
                break
        ## Temperature
        if self.currentState['tempThreads'] is not None:
            for t in self.currentState['tempThreads']:
                t.stop()
        else:
            self.currentState['tempThreads'] = []
            for c,k in enumerate(sorted(self.config['thermometers']['devices'].keys())):
                v = self.config['thermometers']['devices'][k]
                
                ### Figure out the thermometer type
                if v['type'] == 'Comet':
                    ThermoBaseType = Comet
                else:
                    ThermoBaseType = HWg
                    
                nT = ThermoBaseType(v['ip'], v['port'], cmdgen.CommunityData(*v['security_model']),
                                c+1, nSensors=v['nsensor'], description=v['description'], 
                                MonitorPeriod=self.config['thermometers']['monitor_period'], SHLCallbackInstance=self)
                self.currentState['tempThreads'].append(nT)
        ## PDUs
        if self.currentState['pduThreads'] is not None:
            for t in self.currentState['pduThreads']:
                t.stop()
        else:
            self.currentState['pduThreads'] = []
            for c,k in enumerate(sorted(self.config['pdus']['devices'].keys())):
                v = self.config['pdus']['devices'][k]
                
                ### Figure out the PDU type
                if v['type'] == 'TrippLite':
                    PDUBaseType = TrippLite
                elif v['type'] == 'TrippLiteUPS':
                    PDUBaseType = TrippLiteUPS
                elif v['type'] == 'Raritan':
                    PDUBaseType = Raritan
                elif v['type'] == 'Dominion':
                    PDUBaseType = Dominion
                elif v['type'] == 'APC':
                    PDUBaseType = APC
                else:
                    PDUBaseType = APCUPS
                    
                nP = PDUBaseType(v['ip'], v['port'], cmdgen.CommunityData(*v['security_model']),
                                 c+1, nOutlets=v['noutlet'], description=v['description'], 
                                 MonitorPeriod=self.config['pdus']['monitor_period'], SHLCallbackInstance=self)
                                
                self.currentState['pduThreads'].append(nP)
        ## Weather station
        if self.currentState['wxThread'] is not None:
            self.currentState['wxThread'].stop()
        else:
            self.currentState['wxThread'] = Weather(self.config, MonitorPeriod=self.config['weather']['monitor_period'],
                                                    SHLCallbackInstance=self)
        ## Lightning monitor
        if self.currentState['strikeThread'] is not None:
            self.currentState['strikeThread'].stop()
        else:
            self.currentState['strikeThread'] = Lightning(self.config, SHLCallbackInstance=self)
        ## Line voltage monitor
        if self.currentState['outageThread'] is not None:
            self.currentState['outageThread'].stop()
        else:
            self.currentState['outageThread'] = Outage(self.config, SHLCallbackInstance=self)
            
        # Set configuration values
        self.currentState['setPoint'] = setPoint
        self.currentState['diffPoint'] = diffPoint
        self.currentState['nRacks'] = reduce(lambda x, y: x+y, [int(i) for i in nRacks])
        self.currentState['rackPresent'] = [int(i) for i in nRacks]
        ## Extend self.currentState['rackPresent'] for racks in shlCommon but not in the INI
        while len(self.currentState['pduThreads']) > len(self.currentState['rackPresent']):
            self.currentState['rackPresent'].append(0)
        ## Reset the unreacable device list
        self.currentState['unreachableDevices'] = {}
        
        # Print out some rack status
        shlFunctionsLogger.info('-----------------')
        shlFunctionsLogger.info(' SHL Rack Status ')
        shlFunctionsLogger.info('-----------------')
        for n,(r,p) in enumerate(zip(self.currentState['pduThreads'], self.currentState['rackPresent'])):
            shlFunctionsLogger.info('Rack #%i: %s -> %s', n+1, 'installed' if p else 'not installed', r.description)
        shlFunctionsLogger.info('Total Number of Racks: %i', self.currentState['nRacks'])
        shlFunctionsLogger.info('-----------------')
        
        # Update the HVAC set point
        if 'ip' in self.config['hvac'].keys():
            setPoint = get_iceqube_setpoint(self.config['hvac']['ip'][0])
            if setPoint is not None:
                self.currentState['setPoint'] = setPoint
                
        # Update the HVAC cooling offset
        if 'ip' in self.config['hvac'].keys():
            diffPoint = get_iceqube_cooling_offset(self.config['hvac']['ip'][0])
            if diffPoint is not None:
                self.currentState['diffPoint'] = diffPoint
                
        # Start the monitoring threads back up
        self.scheduler.start()
        if self.currentState['enviroThread'] is not None:
            self.currentState['enviroThread'].start()
        for t in self.currentState['tempThreads']:
            t.start()
        for t,p in zip(self.currentState['pduThreads'], self.currentState['rackPresent']):
            if p:
                t.start()
        if self.config['weather']['monitor_period'] > 0:
            self.currentState['wxThread'].start()
        self.currentState['strikeThread'].start()
        self.currentState['outageThread'].start()
        
        # Update the current state
        self.currentState['ready'] = True
        self.currentState['status'] = 'NORMAL'
        self.currentState['info'] = 'SHL ready'
        self.currentState['lastLog'] = 'INI: finished in %.3f s' % (time.time() - tStart,)
        
        shlFunctionsLogger.info("Finished the INI process in %.3f s", time.time() - tStart)
        self.currentState['activeProcess'].remove('INI')
        
        return True, 0
        
    def sht(self, mode=''):
        """
        Issue the SHT command to SHL.
        """
        
        # Check for other operations in progress that could be blocking (INI and SHT)
        if 'INI' in self.currentState['activeProcess'] or 'SHT' in self.currentState['activeProcess']:
            self.currentState['lastLog'] = 'SHT: %s - %s is active and blocking' % (commandExitCodes[0x07], self.currentState['activeProcess'])
            return False, 0x07
        
        # Validate SHT options
        if mode not in ("", "SCRAM", "RESTART", "SCRAM RESTART"):
            self.currentState['lastLog'] = 'SHT: %s - unknown mode %s' % (commandExitCodes[0x06], mode)
            return False, 0x06
            
        ## Check if we can even run SHT
        #if not self.currentState['ready']:
            #self.currentState['lastLog'] = 'SHT: %s' % commandExitCodes[0x09]
            #return False, 0x09
        
        thread = threading.Thread(target=self.__shtProcess, kwargs={'mode': mode})
        thread.setDaemon(1)
        thread.start()
        return True, 0
        
    def __shtProcess(self, mode=""):
        """
        Thread base to shutdown ASP.  Update the current system state as needed.
        """
        
        # Start the timer
        tStart = time.time()
        
        # Update system state
        self.currentState['status'] = 'SHUTDWN'
        self.currentState['info'] = 'System is shutting down'
        self.currentState['activeProcess'].append('SHT')
        self.currentState['ready'] = False
        
        # Stop all threads.
        ## Enviromenal monitor
        if self.currentState['enviroThread'] is not None:
            self.currentState['enviroThread'].stop()
        ## Temperature
        if self.currentState['tempThreads'] is not None:
            for t in self.currentState['tempThreads']:
                t.stop()
        ## PDUs
        if self.currentState['pduThreads'] is not None:
            for t in self.currentState['pduThreads']:
                t.stop()
        ## Weather station
        if self.currentState['wxThread'] is not None:
            self.currentState['wxThread'].stop()
        ## Lightning monitor
        if self.currentState['strikeThread'] is not None:
            self.currentState['strikeThread'].stop()
        ## Line voltage monitor
        if self.currentState['outageThread'] is not None:
            self.currentState['outageThread'].stop()
            
        # Stop the scheduler
        self.scheduler.stop()
        
        # Update the state
        self.currentState['status'] = 'SHUTDWN'
        self.currentState['info'] = 'System has been shut down'
        self.currentState['lastLog'] = 'System has been shut down'
        ## Reset the unreachable device list
        self.currentState['unreachableDevices'] = {}
        
        shlFunctionsLogger.info("Finished the SHT process in %.3f s", time.time() - tStart)
        self.currentState['activeProcess'].remove('SHT')
        
        return True, 0
        
    def tmp(self, setPoint):
        """
        Issue the TMP command to SHL.
        """
        
        # Check if we are ready
        if not self.currentState['ready']:
            self.currentState['lastLog'] = 'TMP: %s' % commandExitCodes[0x09]
            return False, 0x09
            
        # Validate the temperatures
        if not isHalfIncrements(setPoint) or setPoint < self.config['temp_min'] or setPoint > self.config['temp_max']:
            shlFunctionsLogger.warning("TMP command rejected due to invalid set point")
            self.currentState['lastLog'] = 'TMP: %s' % commandExitCodes[0x01]
            return False, 0x01
            
        thread = threading.Thread(target=self.__tmpProcess, args=(setPoint,))
        thread.setDaemon(1)
        thread.start()
        return True, 0
        
    def __tmpProcess(self, setPoint):
        """
        Thread base to set the temperature set point.
        """
        
        status = False
        if 'ip' in self.config['hvac'].keys():
            status = set_iceqube_setpoint(setPoint)
            if status:
                setPoint = get_iceqube_setpoint(self.config['hvac']['ip'][0])
                if setPoint is not None:
                    self.currentState['setPoint'] = setPoint
                    
        return status, self.currentState['setPoint']
        
    def dif(self, diffPoint):
        """
        Issue the DIF command to SHL.
        """
        
        # Check if we are ready
        if not self.currentState['ready']:
            self.currentState['lastLog'] = 'TMP: %s' % commandExitCodes[0x09]
            return False, 0x09
            
        # Make sure the differential is valid
        if not isHalfIncrements(diffPoint) or diffPoint < self.config['diff_min'] or diffPoint > self.config['diff_max']:
            shlFunctionsLogger.warning("DIF command rejected due to invalid differential")
            self.currentState['lastLog'] = 'DIF: %s' % commandExitCodes[0x02]
            return False, 0x02
            
        thread = threading.Thread(target=self.__difProcess, args=(diffPoint,))
        thread.setDaemon(1)
        thread.start()
        return True, 0
        
    def __difProcess(self, diffPoint):
        """
        Thread base to set the temperature differential set point.
        """
        
        status = False
        if 'ip' in self.config['hvac'].keys():
            status = set_iceqube_cooling_offset(diffPoint)
            if status:
                diffPoint = get_iceqube_cooling_offset(self.config['hvac']['ip'][0])
                if diffPoint is not None:
                    self.currentState['diffPoint'] = value
                    
        return status, self.currentState['diffPoint']
        
    def pwr(self, rack, port, control):
        """
        Issue the PWR command to SHL.
        """
        
        # Check if we are ready
        if not self.currentState['ready']:
            self.currentState['lastLog'] = 'TMP: %s' % commandExitCodes[0x09]
            return False, 0x09
            
        # Validate the rack,port,control combo
        ## Rack
        if rack == 0 or rack > len(self.currentState['rackPresent']):
            shlFunctionsLogger.warning("PWR command rejected due to invalid rack number")
            self.currentState['lastLog'] = 'PWR: %s - rack' % commandExitCodes[0x03]
            return False, 0x03
        if not self.currentState['rackPresent'][rack-1]:
            shlFunctionsLogger.warning("PWR command rejected due to rack #%i not present", rack)
            self.currentState['lastLog'] = 'PWR: %s - rack' % commandExitCodes[0x03]
            return False, 0x03
        ## Port
        if port not in self.currentState['pduThreads'][rack-1].status.keys():
            shlFunctionsLogger.warning("PWR command rejected due to invalid port number")
            self.currentState['lastLog'] = 'PWR: %s - port' % commandExitCodes[0x04]
            return False, 0x04
        ## Control word
        if control not in ('ON ', 'OFF'):
            shlFunctionsLogger.warning("PWR command rejected due to invalid control word")
            self.currentState['lastLog'] = 'PWR: %s' % commandExitCodes[0x05]
            return False, 0x05
            
        thread = threading.Thread(target=self.__pwrProcess, args=(rack, port, control))
        thread.setDaemon(1)
        thread.start()
        return True, 0
        
    def __pwrProcess(self, rack, port, control):
        """
        Thread base for changing the power status of an outlet.
        """
        
        self.currentState['pduThreads'][rack-1].setStatus(outlet=port, status=control)
        
        return True, 0
        
    def getMeanTemperature(self, DegreesF=True):
        """
        Return the current mean shelter temperature as a two-element tuple 
        (success, value) where success is a boolean related to if the temperature 
        values were found.  See the currentState['lastLog'] entry for the reason for 
        failure if the returned success value is False.
        """
        
        i = 0
        meanTemp = 0
        if self.currentState['enviroThread'] is not None:
            if self.currentState['enviroThread'].alive.isSet():
                try:
                    meanTemp += self.currentState['enviroThread'].getTemperature(DegreesF=DegreesF)
                    i += 1
                except TypeError:
                    pass
                    
        for t in self.currentState['tempThreads']:
            # Make sure the monitoring thread is running
            if t.alive.isSet():
                try:
                    meanTemp += t.getTemperature(DegreesF=DegreesF)
                    i += 1
                except TypeError:
                    pass
                     
        # Make sure we have actual values to average
        if i == 0:
            self.currentState['lastLog'] = 'No temperature monitoring threads are running'
            return False, 0
            
        meanTemp /= float(i)
        
        return True, meanTemp
        
    def getSmokeDetected(self):
        """
        Poll the EnivroMux for the state of the smoke detector and return a two-
        element tuple (sucess, value) where success is a boolean related to if
        the smoke detector state was found.  See the currentState['lastLog']
        entry for the reason for failure if the returned success value is False.
        """
        
        if self.currentState['enviroThread'] is None:
            self.currentState['lastLog'] = 'No enviromental monitoring system configured'
            return False, False
            
        if not self.currentState['enviroThread'].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for the enviromental system is not running'
            return False, False
            
        out = self.currentState['enviroThread'].getSmokeDetected()
        if out is None:
            self.currentState['lastLog'] = 'Monitoring thread does not have a smoke detector'
            return False, False
        else:
            return True, out
            
    def getWaterDetected(self):
        """
        Poll the EnivroMux for the state of the water leak detector and return a
        two-element tuple (sucess, value) where success is a boolean related to
        if the water leak detector state was found.  See the
        currentState['lastLog'] entry for the reason for failure if the returned
        success value is False.
        """
        
        if self.currentState['enviroThread'] is None:
            self.currentState['lastLog'] = 'No enviromental monitoring system configured'
            return False, False
            
        if not self.currentState['enviroThread'].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for the enviromental system is not running'
            return False, False
            
        out = self.currentState['enviroThread'].getWaterDetected()
        if out is None:
            self.currentState['lastLog'] = 'Monitoring thread does not have a water sensor'
            return False, False
        else:
            return True, out
            
    def getDoorOpen(self):
        """
        Poll the EnivroMux for the state of the door and return a two-element
        tuple (sucess, value) where success is a boolean related to if the door
        state was found.  See the currentState['lastLog'] entry for the reason
        for failure if the returned success value is False.
        """
        
        if self.currentState['enviroThread'] is None:
            self.currentState['lastLog'] = 'No enviromental monitoring system configured'
            return False, False
            
        if not self.currentState['enviroThread'].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for the enviromental system is not running'
            return False, False
            
        out = self.currentState['enviroThread'].getDoorOpen()
        if out is None:
            self.currentState['lastLog'] = 'Monitoring thread does not have a door sensor'
            return False, False
        else:
            return True, out
            
    def getOutletCount(self, rack):
        """
        Given a rack return the current power draw of all outlets as a two-elements 
        tuple (success, value) where success is a boolean related to if the outlet
        count was found.  See the currentState['lastLog'] entry for the reason for 
        failure if the returned success value is False.
        """
        
        # Check the rack number
        if rack == 0 or rack > len(self.currentState['rackPresent']):
            self.currentState['lastLog'] = 'Invalid rack number %i' % rack
            return False, 0
        if not self.currentState['rackPresent'][rack-1]:
            self.currentState['lastLog'] = 'Rack #%i not present during INI call' % rack
            return False, 0
            
        return True, self.currentState['pduThreads'][rack-1].nOutlets
        
    def getPowerState(self, rack, port):
        """
        Given a rack, port combo, return the current power state of the outlets as a
        two-elements tuple (success, value) where success is a boolean related to if 
        the state was found.  See the currentState['lastLog'] entry for the reason for 
        failure if the returned success value is False.
        """
        
        # Check the rack number
        if rack == 0 or rack > len(self.currentState['rackPresent']):
            self.currentState['lastLog'] = 'Invalid rack number %i' % rack
            return False, 'UNK'
        if not self.currentState['rackPresent'][rack-1]:
            self.currentState['lastLog'] = 'Rack #%i not present during INI call' % rack
            return False, 'UNK'
            
        # Check the port (outlet) number
        if port not in self.currentState['pduThreads'][rack-1].status.keys():
            self.currentState['lastLog'] = 'Invalid port number %i for rack %i' % (port, rack)
            return False, 'UNK'
        
        return True, self.currentState['pduThreads'][rack-1].getStatus(outlet=port)
        
    def getInputFrequency(self, rack):
        """
        Given a rack return the input line frequency as a two-element tuple 
        (success, value) where success is a boolean related to if the frequency was 
        found.  See the currentState['lastLog'] entry for the reason for failure if 
        the returned success value is False.
        """
        
        # Check the rack number
        if rack == 0 or rack > len(self.currentState['rackPresent']):
            self.currentState['lastLog'] = 'Invalid rack number %i' % rack
            return False, 0
        if not self.currentState['rackPresent'][rack-1]:
            self.currentState['lastLog'] = 'Rack #%i not present during INI call' % rack
            return False, 0
            
        # Make sure the monitoring thread is running
        if not self.currentState['pduThreads'][rack-1].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for Rack #%i is not running' % rack
            return False, 0
            
        return True, self.currentState['pduThreads'][rack-1].getFrequency()
        
    def getInputVoltage(self, rack):
        """
        Given a rack return the input line voltage of all outlets as a two-elements 
        tuple (success, value) where success is a boolean related to if the voltage 
        was found.  See the currentState['lastLog'] entry for the reason for failure 
        if the returned success value is False.
        """
        
        # Check the rack number
        if rack == 0 or rack > len(self.currentState['rackPresent']):
            self.currentState['lastLog'] = 'Invalid rack number %i' % rack
            return False, 0
        if not self.currentState['rackPresent'][rack-1]:
            self.currentState['lastLog'] = 'Rack #%i not present during INI call' % rack
            return False, 0
            
        # Make sure the monitoring thread is running
        if not self.currentState['pduThreads'][rack-1].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for Rack #%i is not running' % rack
            return False, 0
            
        return True, self.currentState['pduThreads'][rack-1].getVoltage()
        
    def getCurrentDraw(self, rack):
        """
        Given a rack return the current power draw of all outlets as a two-elements 
        tuple (success, value) where success is a boolean related to if the current 
        draw was found.  See the currentState['lastLog'] entry for the reason for 
        failure if the returned success value is False.
        """
        
        # Check the rack number
        if rack == 0 or rack > len(self.currentState['rackPresent']):
            self.currentState['lastLog'] = 'Invalid rack number %i' % rack
            return False, 0
        if not self.currentState['rackPresent'][rack-1]:
            self.currentState['lastLog'] = 'Rack #%i not present during INI call' % rack
            return False, 0
            
        # Make sure the monitoring thread is running
        if not self.currentState['pduThreads'][rack-1].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for Rack #%i is not running' % rack
            return False, 0
            
        return True, self.currentState['pduThreads'][rack-1].getCurrent()
        
    def getBatteryCharge(self, rack):
        """
        Given a rack return the battery charge percentage as a two-element tuple 
        (success, value) where success is a boolean related to if the battery 
        charge was found.  See the currentState['lastLog'] entry for the reason for 
        failure if the returned success value is False.
        """
        
        # Check the rack number
        if rack == 0 or rack > len(self.currentState['rackPresent']):
            self.currentState['lastLog'] = 'Invalid rack number %i' % rack
            return False, 0
        if not self.currentState['rackPresent'][rack-1]:
            self.currentState['lastLog'] = 'Rack #%i not present during INI call' % rack
            return False, 0
            
        # Make sure the monitoring thread is running
        if not self.currentState['pduThreads'][rack-1].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for Rack #%i is not running' % rack
            return False, 0
            
        # Make sure the rack corresponds to a UPS
        if not self.currentState['pduThreads'][rack-1].isUPS:
            self.currentState['lastLog'] = 'Rack #%i is not a UPS' % rack
            return False, 0
            
        return True, self.currentState['pduThreads'][rack-1].getBatteryCharge()
        
    def getBatteryStatus(self, rack):
        """
        Given a rack return the battery status as a two-element tuple (success, value) 
        where success is a boolean related to if the battery status was found.  See 
        the currentState['lastLog'] entry for the reason for failure if the returned 
        success value is False.
        """
        
        # Check the rack number
        if rack == 0 or rack > len(self.currentState['rackPresent']):
            self.currentState['lastLog'] = 'Invalid rack number %i' % rack
            return False, 0
        if not self.currentState['rackPresent'][rack-1]:
            self.currentState['lastLog'] = 'Rack #%i not present during INI call' % rack
            return False, 0
            
        # Make sure the monitoring thread is running
        if not self.currentState['pduThreads'][rack-1].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for Rack #%i is not running' % rack
            return False, 0
            
        # Make sure the rack corresponds to a UPS
        if not self.currentState['pduThreads'][rack-1].isUPS:
            self.currentState['lastLog'] = 'Rack #%i is not a UPS' % rack
            return False, 0
            
        return True, self.currentState['pduThreads'][rack-1].getBatteryStatus()
        
    def getOutputSource(self, rack):
        """
        Given a rack return the output power source as a two-element tuple 
        (success, value) where success is a boolean related to if the output 
        source was found.  See the currentState['lastLog'] entry for the reason for 
        failure if the returned success value is False.
        """
        
        # Check the rack number
        if rack == 0 or rack > len(self.currentState['rackPresent']):
            self.currentState['lastLog'] = 'Invalid rack number %i' % rack
            return False, 0
        if not self.currentState['rackPresent'][rack-1]:
            self.currentState['lastLog'] = 'Rack #%i not present during INI call' % rack
            return False, 0
            
        # Make sure the monitoring thread is running
        if not self.currentState['pduThreads'][rack-1].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for Rack #%i is not running' % rack
            return False, 0
            
        # Make sure the rack corresponds to a UPS
        if not self.currentState['pduThreads'][rack-1].isUPS:
            self.currentState['lastLog'] = 'Rack #%i is not a UPS' % rack
            return False, 0
            
        return True, self.currentState['pduThreads'][rack-1].getOutputSource()
        
    def getWeatherUpdateTime(self):
        """
        Return the update weather update as a two-element tuple (success, value)
        where success is a boolean related to if the update time was found.  
        See the currentState['lastLog'] entry for the reason for failure if 
        the returned success value is False.
        """
        
        # Make sure the monitoring thread is running
        if not self.currentState['wxThread'].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for the weather station is not running'
            return False, 0
            
        out = self.currentState['wxThread'].getLastUpdateTime()
        if out is None:
            return True, None
        else:
            return True, out.strftime('%Y-%m-%d %H:%M:%S')	
            
    def getOutsideTemperature(self, DegreesF=True):
        """
        Return the outside temperature as a two-element tuple (success, value)
        where success is a boolean related to if the temperature was found.  
        See the currentState['lastLog'] entry for the reason for failure if 
        the returned success value is False.
        """
        
        # Make sure the monitoring thread is running
        if not self.currentState['wxThread'].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for the weather station is not running'
            return False, 0
            
        out = self.currentState['wxThread'].getTemperature(DegreesF=DegreesF)
        if out is None:
            return True, None
        else:
            return True, "%.2f" % out
            
    def getOutsideHumidity(self):
        """
        Return the barometric pressure as a two-element tuple (success, value)
        where success is a boolean related to if the pressure was found.  
        See the currentState['lastLog'] entry for the reason for failure if 
        the returned success value is False.
        """
        
        # Make sure the monitoring thread is running
        if not self.currentState['wxThread'].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for the weather station is not running'
            return False, 0
            
        out = self.currentState['wxThread'].getPressure()
        if out is None:
            return True, None
        else:
            return True, "%.2f" % out
            
    def getBarometricPressure(self):
        """
        Return the outside humidity as a two-element tuple (success, value)
        where success is a boolean related to if the humidity was found.  
        See the currentState['lastLog'] entry for the reason for failure if 
        the returned success value is False.
        """
        
        # Make sure the monitoring thread is running
        if not self.currentState['wxThread'].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for the weather station is not running'
            return False, 0
            
        out = self.currentState['wxThread'].getHumidity()
        if out is None:
            return True, None
        else:
            return True, "%.2f" % out
            
    def getWind(self, MPH=True):
        """
        Return the wind speed and direction as a two-element tuple 
        (success, value) where success is a boolean related to if the 
        wind was found.  See the currentState['lastLog'] entry for the 
        reason for failure if the returned success value is False.
        """
        
        # Make sure the monitoring thread is running
        if not self.currentState['wxThread'].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for the weather station is not running'
            return False, 0
            
        out = self.currentState['wxThread'].getWind(MPH=MPH)
        if out[0] is None:
            return True, None
        else:
            return True, "%.1f %s at %i degrees" % (out[0], 'mph' if MPH else 'kph', out[1])
            
    def getGust(self, MPH=True):
        """
        Return the wind gust speed and direction as a two-element tuple 
        (success, value) where success is a boolean related to if the 
        wind was found.  See the currentState['lastLog'] entry for the 
        reason for failure if the returned success value is False.
        """
        
        # Make sure the monitoring thread is running
        if not self.currentState['wxThread'].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for the weather station is not running'
            return False, 0
            
        out = self.currentState['wxThread'].getGust(MPH=MPH)
        if out[0] is None:
            return True, None
        else:
            return True, "%.1f %s at %i degrees" % (out[0], 'mph' if MPH else 'kph', out[1])
            
    def getRainfallRate(self, Inches=True):
        """
        Return the rainfall rate as a two-element tuple (success, value) 
        where success is a boolean related to if the rainfall rate was 
        found.  See the currentState['lastLog'] entry for the reason for 
        failure if the returned success value is False.
        """
        
        # Make sure the monitoring thread is running
        if not self.currentState['wxThread'].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for the weather station is not running'
            return False, 0
            
        out = self.currentState['wxThread'].getPercipitation(Inches=Inches)
        if out[0] is None:
            return True, None
        else:
            return True, "%.2f" % out[0]
            
    def getTotalRainfall(self, Inches=True):
        """
        Return the total rainfall as a two-element tuple (success, value) 
        where success is a boolean related to if the total rainfall was 
        found.  See the currentState['lastLog'] entry for the reason for 
        failure if the returned success value is False.
        """
        
        # Make sure the monitoring thread is running
        if not self.currentState['wxThread'].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for the weather station is not running'
            return False, 0
            
        out = self.currentState['wxThread'].getPercipitation(Inches=Inches)
        if out[1] is None:
            return True, None
        else:
            return True, "%.2f" % out[1]
            
    def getLightningStrikeCount(self, radius=15, interval=10):
        """
        Returns the number of lightning strikes seen within the specified 
        radius in km and time interval in minutes as a two-element tuple 
        (success, value) where success is a boolean related to if the number
        of strikes was found.  See the currentState['lastLog'] entry for 
        the reason for failure if the returned success value is False.
        """
        
        # Make sure the monitoring thread is running
        if not self.currentState['strikeThread'].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for the lightning monitor is not running'
            return False, 0
            
        out = self.currentState['strikeThread'].getStrikeCount(radius=radius, interval=interval)
        if out is None:
            return True, None
        else:
            return True, out
            
    def getPowerFlicker(self):
        """
        Returns whether or not a power flicker has occured within the 
        outage polling interval as a two-element tuple (success, value) 
        where success is a boolean related to whether or not a flicker was 
        detected.  See the currentState['lastLog'] entry for the reason 
        for failure if the returned success value is False.
        """
        
        # Make sure the monitoring thread is running
        if not self.currentState['outageThread'].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for the line voltage monitor is not running'
            return False, 0
            
        out = self.currentState['outageThread'].getFlicker()
        if out is None:
            return True, None
        else:
            return True, out
            
    def getPowerOutage(self):
        """
        Returns whether or not a power outage has occured within the 
        outage polling interval as a two-element tuple (success, value) 
        where success is a boolean related to whether or not an outage was 
        detected.  See the currentState['lastLog'] entry for the reason 
        for failure if the returned success value is False.
        """
        
        # Make sure the monitoring thread is running
        if not self.currentState['outageThread'].alive.isSet():
            self.currentState['lastLog'] = 'Monitoring thread for the line voltage monitor is not running'
            return False, 0
            
        out = self.currentState['outageThread'].getOutage()
        if out is None:
            return True, None
        else:
            return True, out
            
    def processShelterTemperature(self, currTemp):
        """
        Figure out what to do about the shelter temperature.  If things look really bad, take action.
        """
        
        if currTemp < self.config['thermometers']['warning_temp']:
            # Everything is OK
            if self.currentState['status'] == 'WARNING':
                ## From WARNING
                in_warning, message = self._merge_states(self.currentState['info'],
                                                         remove='TEMPERATURE')
                if not in_warning:
                    self.currentState['status'] = 'NORMAL'
                self.currentState['info'] = message
                
                shlFunctionsLogger.info('Shelter temperature warning condition cleared')
                
            elif self.currentState['status'] == 'ERROR' and self.currentState['info'].startswith('TEMPERATURE!'):
                ## From ERROR
                self.currentState['info'] = 'Error condition cleared, system operating normally'
                
                shlFunctionsLogger.info('Shelter temperature critical condition cleared')
                
        elif currTemp < self.config['thermometers']['critical_temp']:
            # We are in warning
            if self.currentState['status'] in ('NORMAL', 'WARNING'):
                ## Escalation
                _, message = self._merge_states(self.currentState['info'],
                                                append=('TEMPERATURE',
                                                        "Shelter temperature at %.2f" % currTemp))
                self.currentState['status'] = 'WARNING'
                self.currentState['info'] = message
                
                shlFunctionsLogger.warning('Shelter temperature warning at %.2f', currTemp)
                
            elif self.currentState['status'] == 'ERROR' and self.currentState['info'].startswith('TEMPERATURE!'):
                ## Descalation
                _, message = self._merge_states('',
                                                append=('TEMPERATURE',
                                                        "Shelter temperature at %.2f" % currTemp))
                self.currentState['status'] = 'WARNING'
                self.currentState['info'] = message
                
                shlFunctionsLogger.info('Shelter temperature critical condition cleared')
                shlFunctionsLogger.warning('Shelter temperature warning at %.2f', currTemp)
                
        else:
            # We are critical, take action
            ## Find out what ports we need to shut down
            criticalPortList = ','.join(["rack %i - port %i" % (r,p) for r,p in self.config['thermometers']['critical_list']])
            if len(self.config['thermometers']['critical_list']) == 0:
                criticalPortList = 'None listed'
                
            ## Change the system state
            self.currentState['status'] = 'ERROR'
            self.currentState['info'] = 'TEMPERATURE! Shelter temperature at %.2f, shutting down critical ports: %s' % (currTemp, criticalPortList)
            
            ## Try to shut off the ports
            for rack,port in self.config['thermometers']['critical_list']:
                try:
                    good, status = self.getPowerState(rack, port)
                    if status != 'OFF':
                        self.pwr(rack, port, 'OFF')
                except Exception as e:
                    shlFunctionsLogger.error('Cannot power off rack %i, port %i: %s', rack, port, str(e))
                    
            shlFunctionsLogger.critical('Shelter temperature at %.2f, shutting down critical ports: %s', currTemp, criticalPortList)
            
        return True
        
    def processSmokeDetector(self, smokeDetected):
        """
        Figure out what to do about the smoke alarm going off.
        """
        
        if not smokeDetected:
            # Everything is OK
            if self.currentState['status'] == 'ERROR' and self.currentState['info'].startswith('SMOKE!'):
                ## From ERROR
                self.currentState['info'] = 'Error condition cleared, system operating normally'
                
                shlFunctionsLogger.info('Shelter smoke detector condition cleared')
                
        else:
            ## Change the system state
            self.currentState['status'] = 'ERROR'
            self.currentState['info'] = 'SMOKE! Shelter smoke detector activated'
            
            shlFunctionsLogger.critical('Shelter smoke detector activated')
            
        return True
        
    def processWaterDetector(self, waterDetected):
        """
        Figure out what to do about the water sensor finding water.
        """
        
        if not waterDetected:
            # Everything is OK
            if self.currentState['status'] == 'ERROR' and self.currentState['info'].startswith('WATER!'):
                ## From ERROR
                self.currentState['info'] = 'Error condition cleared, system operating normally'
                
                shlFunctionsLogger.info('Shelter water sensor condition cleared')
                
        else:
            ## Change the system state
            self.currentState['status'] = 'ERROR'
            self.currentState['info'] = 'WATER! Shelter water sensor activated'
            
            shlFunctionsLogger.critical('Shelter water sensor activated')
            
        return True
        
    def processDoorState(self, state):
        """
        Figure out what to do about the shelter temperature.  If things look really bad, take action.
        """
        
        if state == 'closed':
            # Everything is OK
            if self.currentState['status'] == 'WARNING':
                ## From WARNING
                in_warning, message = self._merge_states(self.currentState['info'],
                                                         remove='DOOR')
                if not in_warning:
                    self.currentState['status'] = 'NORMAL'
                self.currentState['info'] = message
                
                shlFunctionsLogger.info('Shelter door open condition cleared')
                
        else:
            # We are in warning
            if self.currentState['status'] in ('NORMAL', 'WARNING'):
                ## Escalation
                _, message = self._merge_states(self.currentState['info'],
                                                append=('DOOR',
                                                        "Shelter door is open"))
                self.currentState['status'] = 'WARNING'
                self.currentState['info'] = message
                
                shlFunctionsLogger.warning('Shelter door open condition')
                
        return True
        
    def processUnreachable(self, unreachableDevice):
        """
        Deal with an unreachable device.
        """
        
        # Get the current time
        tNow = time.time()
        
        # Update the unreachable device list
        if unreachableDevice is not None:
            with ListLock:
                self.currentState['unreachableDevices'][unreachableDevice] = tNow
                shlFunctionsLogger.warning('Updated unreachable list - add %s', unreachableDevice)
                
        # Count the recently updated (<= 6 minutes since the last failure) entries
        nUnreachable = 0
        unreachable = {}
        for device in self.currentState['unreachableDevices']:
            age = tNow - self.currentState['unreachableDevices'][device]
            if age <= 360:
                nUnreachable += 1
                unreachable[device] = self.currentState['unreachableDevices'][device]
            else:
                shlFunctionsLogger.info('Updated unreachable list - remove %s', device)
        with ListLock:
            self.currentState['unreachableDevices'] = unreachable
            shlFunctionsLogger.debug('Unreachable list now contains %i entries', len(self.currentState['unreachableDevices']))
            
        # If there isn't anything in the unreachable list, quietly ignore it and clear the WARNING condition
        if nUnreachable == 0:
            if self.currentState['status'] == 'WARNING':
                in_warning, message = self._merge_states(self.currentState['info'],
                                                         remove='SUMMARY')
                if not in_warning:
                    self.currentState['status'] = 'NORMAL'
                self.currentState['info'] = message
            return False
            
        # Otherwise set a warning
        else:
            if self.currentState['status'] in ('NORMAL', 'WARNING'):
                _, message = self._merge_states(self.currentState['info'],
                                                append=('SUMMARY',
                                                        "%i Devices unreachable: %s" % (nUnreachable,
                                                                                        ', '.join(unreachable))))
                self.currentState['status'] = 'WARNING'
                self.currentState['info'] = message
                
            ## Make sure to check back later to see if this is still a problem
            if self.scheduler.empty():
                self.scheduler.enter(420, 1, self.processUnreachable, (None,))
                shlFunctionsLogger.debug('Scheduling another call of \'processUnreachable\' for seven minutes from now')
                
            return True
            
    def processPowerFlicker(self, flicker):
        """
        Deal with power flickers.
        """
        
        if flicker:
            if self.currentState['status'] in ('NORMAL', 'WARNING'):
                _, message = self._merge_states(self.currentState['info'],
                                                append=('POWER-FLICKER',
                                                        'Flicker in the shelter power'))
                self.currentState['status'] = 'WARNING'
                self.currentState['info'] = message
            return True
            
        else:
            if self.currentState['status'] == 'WARNING':
                in_warning, message = self._merge_states(self.currentState['info'],
                                                         remove='POWER-FLICKER')
                if not in_warning:
                    self.currentState['status'] = 'NORMAL'
                self.currentState['info'] = message
            return False
            
    def processPowerOutage(self, outage):
        """
        Deal with power outages.
        """
        
        if outage:
            self.currentState['status'] = 'ERROR'
            self.currentState['info'] = 'POWER-OUTAGE! Shelter power outage'
            return True
            
        else:
            if self.currentState['status'] == 'ERROR' and self.currentState['info'].startswith('POWER-OUTAGE!'):
                self.currentState['status'] = 'NORMAL'
                self.currentState['info'] = 'Power restored, system operating normally'
            return False
            
    @staticmethod
    def _merge_states(message, append=None, remove=None):
        """
        Merge multiple warning conditions together and return a unified message.
        Returns a two-element tuple of a Boolean of whether or not the message
        is a warning message and the message itself.
        """
        
        # Split it into the two parts:  MIBs and descriptions
        mibs = message.split('!')
        mibs, info = mibs[:-1], mibs[-1]
        descriptions = info.split(';')
        if len(mibs) == 0:
            descriptions = []
            
        # Clean
        mibs = [mib.strip().rstrip() for mib in mibs]
        descriptions = [description.strip().strip() for description in descriptions]
        
        # Append, if needed
        if append is not None:
            new_mib, new_description = append
            if new_mib not in mibs:
                ## Add
                mibs.append(new_mib)
                descriptions.append(new_description)
            else:
                ## Replace the description
                i = mibs.index(new_mib)
                descriptions[i] = new_description
                
        # Remove, if needed
        if remove is not None:
            old_mib = remove
            try:
                i = mibs.index(old_mib)
                del mibs[i]
                del descriptions[i]
            except (ValueError, IndexError):
                pass
                
        # Unify the message
        in_warning = True
        message = "%s! %s" % ('! '.join(mibs), '; '.join(descriptions))
        if len(mibs) == 0:
            in_warning = False
            message = 'Warning condition(s) cleared, system operating normally'
            
        return in_warning, message
