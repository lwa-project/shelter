
"""
Background threads to interacting with temperature sensors and PDUs.
"""

import os
import re
import sys
import time
import socket
import logging
import sqlite3
import threading
import traceback
from datetime import datetime, timedelta
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto import rfc1902

__version__ = "1.0"
__all__ = ['Thermometer', 'Comet', 'HWg', 'EnviroMux', 'PDU', 'TrippLite', 'APC', 'Raritan', 'Dominion', 'TrippLiteUPS', 'APCUPS', 'Weather', 'Lightning', 'Outage']


shlThreadsLogger = logging.getLogger('__main__')


# State directory
STATE_DIR = os.path.join(os.path.dirname(__file__), '.shl-state')
if not os.path.exists(STATE_DIR):
    os.mkdir(STATE_DIR)


def _LogThreadException(cls, exception, logger=None):
    """
    Function to help with logging exceptions within the monitoring threads.
    This will add a ERROR line to the logs and print the full traceback as
    DEBUG.
    """
    
    # Get the logger
    if logger is None:
        logger = logging.getLogger('__main__')
        
    # Extract the traceback and generate the ERROR message
    exc_type, exc_value, exc_traceback = sys.exc_info()
    cls_name = type(cls).__name__
    try:
        cls_name = "%s - %s" % (cls.id, cls_name)
    except AttributeError:
        pass
    fnc_name = traceback.extract_tb(exc_traceback, 1)[0][2]
    lineno = exc_traceback.tb_lineno
    logger.error("%s: %s failed with: %s at line %i", cls_name, fnc_name, str(exception), lineno)
    
    # Grab the full traceback and save it to a string via StringIO so that we
    # can print it to DEBUG
    fileObject = StringIO()
    traceback.print_tb(exc_traceback, file=fileObject)
    tbString = fileObject.getvalue()
    fileObject.close()
    ## Print the traceback to the logger as a series of DEBUG messages
    for line in tbString.split('\n'):
        logger.debug("%s", line)


class SNMPControl(object):
    """
    Class for wrapping SNMP commands such that only one command is executated at
    a time.
    """
    
    def __init__(self, ip, port, community, timeout=1.0, retries=3):
        self.community = community
        self.network = cmdgen.UdpTransportTarget((ip, port), timeout=timeout, retries=retries)
        self.generator = cmdgen.CommandGenerator()
        self.lock = threading.Lock()
        
        self.nfailure = 0
        
    def get(self, oid):
        """
        Query the given OID and return the results.
        """
        
        with self.lock:
            errorIndication, errorStatus, errorIndex, varBinds = \
              self.generator.getCmd(self.community, self.network, oid)
            
        # Check for SNMP errors
        if errorIndication:
            self.nfailure += 1
            raise RuntimeError("SNMP error indication: %s" % errorIndication)
        elif errorStatus:
            raise RuntimeError("SNMP error status: %s" % errorStatus.prettyPrint())
            
        return varBinds[0]
        
    def set(self, oid, value):
        """
        Set the given OID to the specified value and return the results.
        """
        
        with self.lock:
            errorIndication, errorStatus, errorIndex, varBinds = \
              self.generator.setCmd(self.community, self.network, (oid, value))
              
        if errorIndication:
            self.nfailure += 1
            raise RuntimeError("SNMP error indication: %s" % errorIndication)
        elif errorStatus:
            raise RuntimeError("SNMP error status: %s" % errorStatus.prettyPrint())
            
        return varBinds[0]


class Thermometer(object):
    """
    Class for communicating with a network thermometer via SNMP and regularly polling
    the temperature.  The temperature value is stored in the "temp" attribute and this
    class supports up to four sensors per device.
    """
    
    oidTemperatureEntry0 = None
    oidTemperatureEntry1 = None
    oidTemperatureEntry2 = None
    oidTemperatureEntry3 = None
    
    def __init__(self, ip, port, community, id, nSensors=1, description=None, SHLCallbackInstance=None, MonitorPeriod=5.0):
        self.ip = ip
        self.port = port
        self.id = id
        self.description = description
        self.SHLCallbackInstance = SHLCallbackInstance
        self.MonitorPeriod = MonitorPeriod
        
        # Setup the sensors
        self.nSensors = nSensors
        self.temp = [None for i in range(self.nSensors)]
        
        # Set the SNMP controller
        self.snmp = SNMPControl(self.ip, self.port, community)
        
        # Setup threading
        self.thread = None
        self.alive = threading.Event()
        self.lastError = None
        
    def __str__(self):
        t = self.getTemperature(DegreesF=True)
        
        output = ''
        if self.description is None:
            output = "Thermometer at IP %s: " % self.ip
        else:
            output = "Thermometer '%s' at IP %s: " % (self.description, self.ip)
        
        if t is None:
            output += "current temperature is unknown"
        else:
            output += "current temperature is %.1f F" % t
            
        return output
        
    def start(self):
        """
        Start the monitoring thread.
        """
        
        if self.thread is not None:
            self.stop()
            
        self.thread = threading.Thread(target=self.monitorThread)
        self.thread.setDaemon(1)
        self.alive.set()
        self.thread.start()
        
    def stop(self):
        """
        Stop the monitor thread, waiting until it's finished.
        """
        
        if self.thread is not None:
            self.alive.clear()          #clear alive event for thread
            self.thread.join()          #wait until thread has finished
            self.thread = None
            self.lastError = None
            
    def monitorThread(self):
        """
        Create a monitoring thread for the temperature.
        """
        
        was_unreachable = 0
        
        while self.alive.isSet():
            tStart = time.time()
            
            # Read the networked thermometers and store values to temp.
            # NOTE: self.temp is in Celsius
            nFailures = 0
            for s,oidEntry in enumerate((self.oidTemperatureEntry0,self.oidTemperatureEntry1,self.oidTemperatureEntry2,self.oidTemperatureEntry3)):
                if s >= self.nSensors:
                    break
                    
                if oidEntry is not None:
                    try:
                        _, value = self.snmp.get(oidEntry)
                        try:
                            self.temp[s] = float(unicode(value))
                        except NameError:
                            self.temp[s] = float(str(value))
                        self.lastError = None
                        
                    except Exception as e:
                        _LogThreadException(self, e, logger=shlThreadsLogger)
                        self.lastError = str(e)
                        nFailures += 1
                        self.temp[s] = None
                        
            # Log the data
            toDataLog = '%.2f,%s' % (time.time(), ','.join(["%.2f" % (self.temp[s] if self.temp[s] is not None else -1) for s in range(self.nSensors)]))
            with open('/data/thermometer%02i.txt' % self.id, 'a+') as fh:
                fh.write('%s\n' % toDataLog)
                
            # Make sure we aren't critical
            temps = [value for value in self.temp if value is not None]
            if self.SHLCallbackInstance is not None and len(temps) != 0:
                maxTemp = 1.8*max(temps) + 32
                self.SHLCallbackInstance.processShelterTemperature(maxTemp)
                
            # Make sure the device is reachable
            if self.SHLCallbackInstance is not None:
                if nFailures > 0:
                    was_unreachable = 5
                    self.SHLCallbackInstance.processUnreachable('%s-%s' % (type(self).__name__, str(self.id)))
                else:
                    if was_unreachable > 1:
                        was_unreachable -= 1
                    elif was_unreachable == 1:
                        was_unreachable = 0
                        self.SHLCallbackInstance.processUnreachable('cleared-%s-%s' % (type(self).__name__, str(self.id)))
                        
            # Stop time
            tStop = time.time()
            shlThreadsLogger.debug('Finished updating temperature in %.3f seconds', tStop - tStart)
            
            # Sleep for a bit
            sleepCount = 0
            sleepTime = self.MonitorPeriod - (tStop - tStart)
            while (self.alive.isSet() and sleepCount < sleepTime):
                time.sleep(0.2)
                sleepCount += 0.2
                
    def getTemperature(self, sensor=0, DegreesF=True):
        """
        Convenience function to get the temperature.  The 'sensor' keyword 
        controls which sensor to poll if multple sensors are supported.  
        This is a zero-based index and, by default, the first sensor is 
        returned.
        """
        
        if self.temp[sensor] is None:
            return None

        if DegreesF:
            return 1.8*self.temp[sensor] + 32
        else:
            return self.temp[sensor]
            
    def getAllTemperatures(self, DegreesF=True):
        """
        Similar to getTemperature() but returns a list with values for all 
        sensors.
        """
        
        output = []
        for value in self.temp:
            if value is None:
                output.append( None )
                
            if DegreesF:
                output.append( 1.8*value + 32 )
            else:
                output.append( value )
        return output


class Comet(Thermometer):
    """
    Class for communicating with a network thermometer via SNMP and regularly polling
    the temperature.  The temperature value is stored in the "temp" attribute.
    """
    
    def __init__(self, ip, port, community, id, nSensors=1, description=None, SHLCallbackInstance=None, MonitorPeriod=5.0):
        super(Comet, self).__init__(ip, port, community, id, nSensors=1, description=description, SHLCallbackInstance=SHLCallbackInstance, MonitorPeriod=MonitorPeriod)
        
        # Setup the OID values
        self.oidTemperatureEntry0 = (1,3,6,1,4,1,22626,1,5,2,1,2,0)


class HWg(Thermometer):
    """
    Class for communicating with a network thermometer via SNMP and regularly polling
    the temperature.  The temperature value is stored in the "temp" attribute.
    """
    
    def __init__(self, ip, port, community, id, nSensors=2, description=None, SHLCallbackInstance=None, MonitorPeriod=5.0):
        super(HWg, self).__init__(ip, port, community, id, nSensors=nSensors, description=description, SHLCallbackInstance=SHLCallbackInstance, MonitorPeriod=MonitorPeriod)
        
        # Setup the OID values
        self.oidTemperatureEntry0 = (1,3,6,1,4,1,21796,4,1,3,1,4,1)
        self.oidTemperatureEntry1 = (1,3,6,1,4,1,21796,4,1,3,1,4,2)


class EnviroMux(object):
    """
    Class for communicating with a network environmental monitor via SNMP and
    regularly polling the temperature, smoke detector, water detector, door, and
    airflow sensor.
    """
    
    oidTemperatureEntry0 = (1,3,6,1,4,1,3699,1,1,8,1,5,1,1,7,1)
    oidTemperatureEntry1 = (1,3,6,1,4,1,3699,1,1,8,1,5,1,1,7,3)
    oidDigitalBaseEntry  = (1,3,6,1,4,1,3699,1,1,8,1,6,1,1,7)
    oidRelayEntry        = (1,3,6,1,4,1,3699,1,1,8,1,8,1,1,3,1)
    
    def __init__(self, ip, port, community, id, nTemperature=2, sensorList=None, description=None, SHLCallbackInstance=None, MonitorPeriod=5.0):
        self.ip = ip
        self.port = port
        self.id = id
        self.description = description
        self.SHLCallbackInstance = SHLCallbackInstance
        self.MonitorPeriod = MonitorPeriod
        
        # Setup the sensors
        self.nTemperature = nTemperature
        self.temp = [None for i in range(self.nTemperature)]
        if sensorList is None:
            sensorList = [None for i in range(5)]
        self.oidSmokeEntry = None
        self.smoke_detected = None
        if 'smoke' in sensorList:
            idx = sensorList.index('smoke')
            self.oidSmokeEntry = self.oidDigitalBaseEntry+(idx+1,)
        self.oidWaterEntry = None
        self.water_detected = None
        if 'water' in sensorList:
            idx = sensorList.index('water')
            self.oidWaterEntry = self.oidDigitalBaseEntry+(idx+1,)
        self.oidDoorEntry = None
        self.door_open = None
        if 'door' in sensorList:
            idx = sensorList.index('door')
            self.oidDoorEntry = self.oidDigitalBaseEntry+(idx+1,)
        self.nAirflow = 0
        self.oidAirflowEntry0 = None
        self.oidAirflowEntry1 = None
        if 'airflow' in sensorList:
            idx = sensorList.index('airflow')
            self.oidAirflowEntry0 = self.oidDigitalBaseEntry+(idx+1,)
            self.nAirflow += 1
            sensorList[idx] = '_airflow'
            
            if 'airflow' in sensorList:
                idx = sensorList.index('airflow')
                self.oidAirflowEntry1 = self.oidDigitalBaseEntry+(idx+1,)
                self.nAirflow += 1
                sensorList[idx] = '_airflow'
        self.airflow = [None for i in range(self.nAirflow)]
        
        # Door opening tracking variable
        self.door_first_opened = None
        
        # Set the SNMP controller
        self.snmp = SNMPControl(self.ip, self.port, community)
        
        # Setup threading
        self.thread = None
        self.alive = threading.Event()
        self.lastError = None
        
    def start(self):
        """
        Start the monitoring thread.
        """
        
        if self.thread is not None:
            self.stop()
            
        self.thread = threading.Thread(target=self.monitorThread)
        self.thread.setDaemon(1)
        self.alive.set()
        self.thread.start()
        
    def stop(self):
        """
        Stop the monitor thread, waiting until it's finished.
        """
        
        if self.thread is not None:
            self.alive.clear()          #clear alive event for thread
            self.thread.join()          #wait until thread has finished
            self.thread = None
            self.lastError = None
            
    def monitorThread(self):
        """
        Create a monitoring thread for the temperature.
        """
        
        was_unreachable = 0
        
        while self.alive.isSet():
            tStart = time.time()
            
            # Read the networked thermometers and store values to temp.
            # NOTE: self.temp is in Celsius
            nFailures = 0
            for s,oidEntry in enumerate((self.oidTemperatureEntry0,self.oidTemperatureEntry1)):
                if s >= self.nTemperature:
                    break
                    
                if oidEntry is not None:
                    try:
                        _, value = self.snmp.get(oidEntry)
                        try:
                            self.temp[s] = float(unicode(value)) / 10.0
                        except NameError:
                            self.temp[s] = float(str(value)) / 10.0
                        self.lastError = None
                        
                    except Exception as e:
                        _LogThreadException(self, e, logger=shlThreadsLogger)
                        self.lastError = str(e)
                        nFailures += 1
                        self.temp[s] = None
                        
            if self.oidSmokeEntry is not None:
                try:
                    _, value = self.snmp.get(self.oidSmokeEntry)
                    try:
                        self.smoke_detected = bool(1-int(unicode(value), 10))
                    except NameError:
                        self.smoke_detected = bool(1-int(str(value), 10))
                    self.lastError = None
                    
                except Exception as e:
                    _LogThreadException(self, e, logger=shlThreadsLogger)
                    self.lastError = str(e)
                    nFailures += 1
                    self.smoke_detected = None
                    
            if self.oidWaterEntry is not None:
                try:
                    _, value = self.snmp.get(self.oidWaterEntry)
                    try:
                        self.water_detected = bool(1-int(unicode(value), 10))
                    except NameError:
                        self.water_detected = bool(1-int(str(value), 10))
                    self.lastError = None
                    
                except Exception as e:
                    _LogThreadException(self, e, logger=shlThreadsLogger)
                    self.lastError = str(e)
                    nFailures += 1
                    self.water_detected = None
                    
            if self.oidDoorEntry is not None:
                try:
                    _, value = self.snmp.get(self.oidDoorEntry)
                    try:
                        self.door_open = bool(int(unicode(value), 10))
                    except NameError:
                        self.door_open = bool(int(str(value), 10))
                    self.lastError = None
                    
                    # Track when the door was first opened
                    if self.door_open:
                        if self.door_first_opened is None:
                            self.door_first_opened = time.time()
                    else:
                        if self.door_first_opened is not None:
                            self.door_first_opened = None
                            
                except Exception as e:
                    _LogThreadException(self, e, logger=shlThreadsLogger)
                    self.lastError = str(e)
                    nFailures += 1
                    self.door_open = None
                    
            for s,oidEntry in enumerate((self.oidAirflowEntry0,self.oidAirflowEntry1)):
                if s >= self.nAirflow:
                    break
                    
                if oidEntry is not None:
                    try:
                        _, value = self.snmp.get(oidEntry)
                        try:
                            self.airflow[s] = bool(1-int(unicode(value), 10))
                        except NameError:
                            self.airflow[s] = bool(1-int(str(value), 10))
                        self.lastError = None
                        
                    except Exception as e:
                        _LogThreadException(self, e, logger=shlThreadsLogger)
                        self.lastError = str(e)
                        nFailures += 1
                        self.airflow[s] = None
                        
            # Log the data
            toDataLog = '%.2f,%s' % (time.time(), ','.join(["%.2f" % (self.temp[s] if self.temp[s] is not None else -1) for s in range(self.nTemperature)]))
            if self.oidSmokeEntry is not None:
                toDataLog += ',smoke=%s' % str(self.smoke_detected)
            if self.oidWaterEntry is not None:
                toDataLog += ',water=%s' % str(self.water_detected)
            if self.oidDoorEntry is not None:
                toDataLog += ',door=%s' % str(self.door_open)
            if self.nAirflow > 0:
                toDataLog += ',airflow=%s' % ';'.join([str(self.airflow[s]) for s in range(self.nAirflow)])
            with open('/data/enviromux.txt', 'a+') as fh:
                fh.write('%s\n' % toDataLog)
                
            # Make sure we aren't critical
            temps = [value for value in self.temp if value is not None]
            if self.SHLCallbackInstance is not None and len(temps) != 0:
                maxTemp = 1.8*max(temps) + 32
                self.SHLCallbackInstance.processShelterTemperature(maxTemp)
                
            # Check for smoke
            if self.SHLCallbackInstance is not None and self.smoke_detected is not None:
                self.SHLCallbackInstance.processSmokeDetector(self.smoke_detected)
                
            # Check for water
            if self.SHLCallbackInstance is not None and self.water_detected is not None:
                self.SHLCallbackInstance.processWaterDetector(self.water_detected)
                
            # Check for an open door
            if self.SHLCallbackInstance is not None:
                if self.door_first_opened is None:
                    self.SHLCallbackInstance.processDoorState('closed')
                else:
                    door_opened_age = time.time() - self.door_first_opened
                    if door_opened_age > 15*3600:
                        self.SHLCallbackInstance.processDoorState('open')
                        
            # Make sure the device is reachable
            if self.SHLCallbackInstance is not None:
                if nFailures > 0:
                    was_unreachable = 5
                    self.SHLCallbackInstance.processUnreachable('%s-%s' % (type(self).__name__, str(self.id)))
                else:
                    if was_unreachable > 1:
                        was_unreachable -= 1
                    elif was_unreachable == 1:
                        was_unreachable = 0
                        self.SHLCallbackInstance.processUnreachable('cleared-%s-%s' % (type(self).__name__, str(self.id)))
                        
            # Stop time
            tStop = time.time()
            shlThreadsLogger.debug('Finished updating enviromental conditions in %.3f seconds', tStop - tStart)
            
            # Sleep for a bit
            sleepCount = 0
            sleepTime = self.MonitorPeriod - (tStop - tStart)
            while (self.alive.isSet() and sleepCount < sleepTime):
                time.sleep(0.2)
                sleepCount += 0.2
                
    def getTemperature(self, sensor=0, DegreesF=True):
        """
        Convenience function to get the temperature.  The 'sensor' keyword 
        controls which sensor to poll if multple sensors are supported.  
        This is a zero-based index and, by default, the first sensor is 
        returned.
        """
        
        if self.temp[sensor] is None:
            return None

        if DegreesF:
            return 1.8*self.temp[sensor] + 32
        else:
            return self.temp[sensor]
            
    def getAllTemperatures(self, DegreesF=True):
        """
        Similar to getTemperature() but returns a list with values for all 
        sensors.
        """
        
        output = []
        for value in self.temp:
            if value is None:
                output.append( None )
            elif DegreesF:
                output.append( 1.8*value + 32 )
            else:
                output.append( value )
        return output
        
    def getSmokeDetected(self):
        """
        Convenience function to get whether or not smoke has been detected.
        """
        
        if self.smoke_detected is None:
            return None
            
        return self.smoke_detected
        
    def getWaterDetected(self):
        """
        Convenience function to get whether or not water has been detected.
        """
        
        if self.water_detected is None:
            return None
            
        return self.water_detected
        
    def getDoorOpen(self):
        """
        Convenience function to get whether or not the door is open.
        """
        
        if self.door_open is None:
            return None
            
        return self.door_open
        
    def getAirflow(self, sensor=0):
        """
        Convenience function to get whether or not airflow is detected.  The
        'sensor' keyword controls which sensor to poll if multple sensors are
        supported.  This is a zero-based index and, by default, the first sensor
        is returned.
        """
        
        if self.airflow[sensor] is None:
            return None

        return self.airflow[sensor]
            
    def getAllAirflow(self):
        """
        Similar to getAirflow() but returns a list with values for all 
        sensors.
        """
        
        output = []
        for value in self.airflow:
            if value is None:
                output.append( None )
                
            output.append( value )
        return output
        

class PDU(object):
    """
    Class for communicating with a network PDU via SNMP and regularly polling
    the current and port states.
    
    .. note::
        This way this class is written the attributes "oidCurrentEntry", 
        "oidOutletStuatusBaseEntry", and "oidOutletChangeEntry" need to be over-
        ridden with the appropriate values when it is sub-classed.
    """
    
    isUPS = False
    
    oidFirmwareEntry = None
    oidFrequencyEntry = None
    oidVoltageEntry = None
    oidCurrentEntry = None
    oidOutletStatusBaseEntry = None
    oidOutletChangeBaseEntry = None
    
    outletStatusCodes = {1: "OFF", 2: "ON", 3: "CYC"}
    
    def __init__(self, ip, port, community, id, nOutlets=8, description=None, SHLCallbackInstance=None, MonitorPeriod=1.0):
        self.ip = ip
        self.port = port
        self.id = id
        self.description = description
        self.SHLCallbackInstance = SHLCallbackInstance
        self.MonitorPeriod = MonitorPeriod
        
        # Setup the outlets, their currents and status codes
        self.nOutlets = nOutlets
        self.voltage = None
        self.current = None
        self.frequency = None
        self.firmwareVersion = None
        self.status = {}
        for i in range(1, self.nOutlets+1):
            self.status[i] = "UNK"
            
        # Set the SNMP controller
        self.snmp = SNMPControl(self.ip, self.port, community)
        
        # Setup threading
        self.thread = None
        self.alive = threading.Event()
        self.lastError = None
        
    def __str__(self):
        sString = ','.join(["%i=%s" % (o, self.status[o]) for o in self.status])
        cString = "%.1f Amps" % self.current if self.current is not None else "Unknown"
        
        if self.description is None:
            return "PDU at IP %s:  outlet status: %s, current: %s" % (self.ip, sString, cString)
        else:
            return "PDU '%s' at IP %s:  outlet status: %s, current: %s" % (self.description, self.ip, sString, cString)
            
    def start(self):
        """
        Start the monitoring thread.
        """
        
        if self.thread is not None:
            self.stop()
            
        self.thread = threading.Thread(target=self.monitorThread)
        self.thread.setDaemon(1)
        self.alive.set()
        self.thread.start()
        
    def stop(self):
        """
        Stop the monitor thread, waiting until it's finished.
        """
        
        if self.thread is not None:
            self.alive.clear()          #clear alive event for thread
            self.thread.join()          #wait until thread has finished
            self.thread = None
            self.lastError = None
            
    def monitorThread(self):
        """
        Create a monitoring thread for the current and outlet states.  Current 
        is stored in the "current" attribute and the outlets in the "status"
        attribute.
        """
        
        was_unreachable = 0
        
        while self.alive.isSet():
            tStart = time.time()
            
            nFailures = 0
            if self.oidFirmwareEntry is not None:
                try:
                    # Get the system firmware
                    _, self.firmwareVersion = self.snmp.get(self.oidFirmwareEntry)
                    
                except Exception as e:
                    _LogThreadException(self, e, logger=shlThreadsLogger)
                    self.lastError = str(e)
                    nFailures += 1
                    self.firmwareVersion = None
                    
            if self.oidFrequencyEntry is not None:
                try:
                    # Get the current input frequency
                    _, PWRfreq = self.snmp.get(self.oidFrequencyEntry)
                    try:
                        self.frequency = float(unicode(PWRfreq)) / 10.0
                    except NameError:
                        self.frequency = float(str(PWRfreq)) / 10.0
                    self.lastError = None
                    
                except Exception as e:
                    _LogThreadException(self, e, logger=shlThreadsLogger)
                    self.lastError = str(e)
                    nFailures += 1
                    self.frequency = None
                    
            if self.oidVoltageEntry is not None:
                try:
                    # Get the current input voltage
                    _, PWRvoltage = self.snmp.get(self.oidVoltageEntry)
                    try:
                        self.voltage = float(unicode(PWRvoltage))
                    except NameError:
                        self.voltage = float(str(PWRvoltage))
                    self.lastError = None
                    
                except Exception as e:
                    _LogThreadException(self, e, logger=shlThreadsLogger)
                    if self.lastError is not None:
                        self.lastError = "%s; %s" % (self.lastError, str(e))
                    else:
                        self.lastError = str(e)
                    nFailures += 1
                    self.voltage = None
                    
            if self.oidCurrentEntry is not None:
                try:
                    # Get the current draw of outlet #(i+1)
                    _, PWRcurrent = self.snmp.get(self.oidCurrentEntry)
                    try:
                        self.current = float(unicode(PWRcurrent))
                    except NameError:
                        self.current = float(str(PWRcurrent))
                    if self.firmwareVersion == '12.04.0053':
                        pass
                    else:
                        self.current = self.current / 10.0
                    self.lastError = None
                    
                except Exception as e:
                    _LogThreadException(self, e, logger=shlThreadsLogger)
                    if self.lastError is not None:
                        self.lastError = "%s; %s" % (self.lastError, str(e))
                    else:
                        self.lastError = str(e)
                    nFailures += 1
                    self.current = None
                    
            if self.oidOutletStatusBaseEntry is not None:
                for i in range(1, self.nOutlets+1):
                    # Get the status of outlet #(i+1).
                    # NOTE:  Since the self.oidOutletStatusBaseEntry is just a base entry, 
                    # we need to append on the outlet number (1-indexed) before we can use
                    # it
                    oidOutletStatusEntry = self.oidOutletStatusBaseEntry+(i,)
                    
                    try:
                        _, PortStatus = self.snmp.get(oidOutletStatusEntry)
                        try:
                            PortStatus = int(unicode(PortStatus))
                        except NameError:
                            PortStatus = int(str(PortStatus))
                            
                        try:
                            self.status[i] = self.outletStatusCodes[PortStatus]
                        except KeyError:
                            self.status[i] = "UNK"
                        if self.lastError is not None:
                            self.lastError = None
                            
                    except Exception as e:
                        _LogThreadException(self, e, logger=shlThreadsLogger)
                        if self.lastError is not None:
                            self.lastError = "%s; %s" % (self.lastError, str(e))
                        else:
                            self.lastError = str(e)
                        nFailures += 1
                        self.status[i] = "UNK"
                        
            toDataLog = "%.2f,%.2f,%.2f,%.2f" % (time.time(), self.frequency if self.frequency is not None else -1, self.voltage if self.voltage is not None else -1, self.current if self.current is not None else -1)
            with open('/data/rack%02i.txt' % self.id, 'a+') as fh:
                fh.write('%s\n' % toDataLog)
                
            # Make sure the device is reachable
            if self.SHLCallbackInstance is not None:
                if nFailures > 0:
                    was_unreachable = 5
                    self.SHLCallbackInstance.processUnreachable('%s-%s' % (type(self).__name__, str(self.id)))
                else:
                    if was_unreachable > 1:
                        was_unreachable -= 1
                    elif was_unreachable == 1:
                        was_unreachable = 0
                        self.SHLCallbackInstance.processUnreachable('cleared-%s-%s' % (type(self).__name__, str(self.id)))
                        
            # Stop time
            tStop = time.time()
            shlThreadsLogger.debug('Finished updating current and port status in %.3f seconds', tStop - tStart)
            
            # Sleep for a bit
            sleepCount = 0
            sleepTime = self.MonitorPeriod - (tStop - tStart)
            while (self.alive.isSet() and sleepCount < sleepTime):
                time.sleep(0.2)
                sleepCount += 0.2
                
    def getFrequency(self):
        """
        Return the input frequency of the DPU in Hz or None if it is unknown.
        """
        
        return self.frequency
        
    def getVoltage(self):
        """
        Return the input voltage of the PDU in volts AC or None if it is unknown.
        """
        
        return self.voltage
        
    def getCurrent(self):
        """
        Return the current associated with the PDU in amps or None if it is unknown.
        """
        
        return self.current
        
    def getFirmwareVersion(self):
        """
        Return the firmware version information or None if it is unknown.
        """
        
        return self.firmwareVersion
        
    def getStatus(self, outlet=None):
        """
        Return the status associated with a particular outlet or, if outlet
        is None, a list of all outlets.
        """
        
        if outlet is None:
            return [self.status[k] for k in sorted(self.status.keys())]
        else:
            return self.status[outlet]
            
    def setStatus(self, outlet=None, status=None):
        """
        Change the status of an outlet to a new value or, if outlet is None,
        change the status of all outlets.  Return True on successful completion
        of the change and False otherwise.
        """
        
        if status is None:
            return False
            
        if outlet is None:
            # If outlet is None, loop over all outlets and return a list of
            # the individual operation result codes
            ret = [False]*self.nOutlets
            for i in range(1, self.nOutlets+1):
                ret[i] = self.setStatus(outlet=i, status=status)
                
            return ret
        else:
            # First, convert the string status code to a number via the 
            # self.outletStatusCodes dictionary.  We default to -1 so we
            # can catch bad values.
            numericCode = -1
            for k in self.outletStatusCodes.keys():
                if self.outletStatusCodes[k] == status.upper().strip():
                    numericCode = k
                    break
                    
            if numericCode < 0:
                return False
            else:
                # NOTE:  Since the self.oidOutletChangeBaseEntry is just a base entry, 
                # we need to append on the outlet number (1-indexed) before we can use
                # it
                oidOutletChangeEntry = self.oidOutletChangeBaseEntry + (outlet,)
                
                success = False
                try:
                    _, value = self.snmp.set(oidOutletChangeEntry, rfc1902.Integer(numericCode))
                    success = True
                    
                except Exception as e:
                    _LogThreadException(self, e, logger=shlThreadsLogger)
                    
                return success


class TrippLite(PDU):
    """
    Sub-class of the PDU class for TrippLite PDUs.
    """
    
    def __init__(self, ip, port, community, id, nOutlets=8, description=None, SHLCallbackInstance=None, MonitorPeriod=1.0):
        super(TrippLite, self).__init__(ip, port, community, id, nOutlets=nOutlets, description=description,  SHLCallbackInstance=SHLCallbackInstance, MonitorPeriod=MonitorPeriod)
        
        # Setup the OID values
        self.oidFirmwareEntry = (1,3,6,1,2,1,33,1,1,4,0)
        self.oidFrequencyEntry = (1,3,6,1,2,1,33,1,4,2,0)
        self.oidVoltageEntry =   (1,3,6,1,2,1,33,1,4,4,1,2,1)
        self.oidCurrentEntry =   (1,3,6,1,2,1,33,1,4,4,1,3,1)
        self.oidOutletStatusBaseEntry = (1,3,6,1,4,1,850,100,1,10,2,1,2,)
        self.oidOutletChangeBaseEntry = (1,3,6,1,4,1,850,100,1,10,2,1,4,)
        
        # Setup the status codes
        self.outletStatusCodes = {1: "OFF", 2: "ON", 3: "CYC"}


class APC(PDU):
    """
    Sub-class of the PDU class for the APC AP7921B PDU.
    """
    
    def __init__(self, ip, port, community, id, nOutlets=8, description=None, SHLCallbackInstance=None, MonitorPeriod=1.0):
        super(APC, self).__init__(ip, port, community, id, nOutlets=nOutlets, description=description, SHLCallbackInstance=SHLCallbackInstance, MonitorPeriod=MonitorPeriod)
        
        # Setup the OID values
        self.oidFirmwareEntry = (1,3,6,1,4,1,318,1,1,12,1,3,0,)
        self.oidFrequencyEntry = None
        self.oidVoltageEntry = None
        self.oidCurrentEntry = (1,3,6,1,4,1,318,1,1,12,2,3,1,1,2,1,)
        self.oidOutletStatusBaseEntry = (1,3,6,1,4,1,318,1,1,4,4,2,1,3,)
        self.oidOutletChangeBaseEntry = (1,3,6,1,4,1,318,1,1,4,4,2,1,3,)
        
        # Setup the status codes
        self.outletStatusCodes = {1: "ON", 2: "OFF", 3:"CYC"}


class Raritan(PDU):
    """
    Sub-class of the PDU class for the new Raritan PDU on DP.
    """
    
    def __init__(self, ip, port, community, id, nOutlets=8, description=None, SHLCallbackInstance=None, MonitorPeriod=1.0):
        super(Raritan, self).__init__(ip, port, community, id, nOutlets=nOutlets, description=description, SHLCallbackInstance=SHLCallbackInstance, MonitorPeriod=MonitorPeriod)
        
        # Setup the OID values
        self.oidFirmwareEntry = (1,3,6,1,4,1,13742,6,3,2,3,1,6,1,1,1)
        self.oidFrequencyEntry = None
        self.oidVoltageEntry = (1,3,6,1,4,1,13742,6,5,2,3,1,4,1,1,4)
        self.oidCurrentEntry = (1,3,6,1,4,1,13742,6,5,2,3,1,4,1,1,1)
        self.oidOutletStatusBaseEntry = (1,3,6,1,4,1,13742,6,4,1,2,1,2,1,)
        self.oidOutletChangeBaseEntry = (1,3,6,1,4,1,13742,6,4,1,2,1,2,1,)
        
        # Setup the status codes
        self.outletStatusCodes = {1: "ON", 0: "OFF", 2: "CYC"}


class Dominion(PDU):
    """
    Sub-class of the PDU class for the new Raritan PDU on DP.
    """
    
    def __init__(self, ip, port, community, id, nOutlets=8, description=None, SHLCallbackInstance=None, MonitorPeriod=1.0):
        super(Dominion, self).__init__(ip, port, community, id, nOutlets=nOutlets, description=description, SHLCallbackInstance=SHLCallbackInstance, MonitorPeriod=MonitorPeriod)
        
        # Setup the OID values
        self.oidFirmwareEntry = (1,3,6,1,4,1,13742,4,1,1,1)
        self.oidFrequencyEntry = None
        self.oidVoltageEntry = (1,3,6,1,4,1,13742,4,1,20,2,1,8)
        self.oidCurrentEntry = (1,3,6,1,4,1,13742,4,1,20,2,1,7)
        self.oidOutletStatusBaseEntry = (1,3,6,1,4,1,13742,4,1,2,2,1,3,)
        self.oidOutletChangeBaseEntry = (1,3,6,1,4,1,13742,4,1,2,2,1,3,)
        
        # Setup the status codes
        self.outletStatusCodes = {1: "ON", 0: "OFF", 2: "CYC"}
        
    def getVoltage(self):
        """
        Return the input voltage of the PDU in volts AC or None if it is unknown.
        """
        
        return self.voltage / 1000.0
        
    def getCurrent(self):
        """
        Return the current associated with the PDU in amps or None if it is unknown.
        """
        
        return self.current / 100.0


class TrippLiteUPS(PDU):
    """
    Sub-class of the PDU class for TrippLite UPSs.
    
    MIB sources:
    http://www.coisoftware.com/support/?wtpaper=011_snmp_tags
    http://www.simpleweb.org/ietf/mibs/modules/IETF/txt/UPS-MIB
    """
    
    def __init__(self, ip, port, community, id, nOutlets=8, description=None, SHLCallbackInstance=None, MonitorPeriod=1.0):
        super(TrippLiteUPS, self).__init__(ip, port, community, id, nOutlets=nOutlets, description=description, SHLCallbackInstance=SHLCallbackInstance, MonitorPeriod=MonitorPeriod)
        
        # This is a UPS
        self.isUPS = True
        
        # Setup the OID values
        self.oidFirmwareEntry = (1,3,6,1,2,1,33,1,1,4,0)
        self.oidFrequencyEntry = (1,3,6,1,2,1,33,1,3,3,1,2,1)
        self.oidVoltageEntry = (1,3,6,1,2,1,33,1,3,3,1,3,1)
        self.oidCurrentEntry = (1,3,6,1,2,1,33,1,4,4,1,3,1)
        self.oidUPSOutputEntry = (1,3,6,1,2,1,33,1,4,1,0)
        self.oidBatteryChargeEntry = (1,3,6,1,2,1,33,1,2,4,0)
        self.oidBatteryStatusEntry = (1,3,6,1,2,1,33,1,2,1,0)
        self.oidOutletStatusBaseEntry = (1,3,6,1,4,1,850,100,1,10,2,1,2,)
        self.oidOutletChangeBaseEntry = (1,3,6,1,4,1,850,100,1,10,2,1,4,)
        
        # Setup the status codes
        self.batteryStatusCodes = {1: "Unknown", 2: "Normal", 3: "Low", 4: "Depleted"}
        self.upsOutputCodes = {1: "Other", 2: "None", 3: "Normal", 4: "Bypass", 5: "Battery", 6: "Booster", 7: "Reducer"}
        self.outletStatusCodes = {1: "OFF", 2: "ON", 3: "CYC"}
        
        # Setup holders
        self.upsOutput = 'UNK'
        self.batteryStatus = 'UNK'
        self.batteryCharge = 0.0
        
    def monitorThread(self):
        """
        Create a monitoring thread for the current and outlet states.  Current 
        is stored in the "current" attribute and the outlets in the "status"
        attribute.
        """
        
        was_unreachable = 0
        
        while self.alive.isSet():
            tStart = time.time()
            
            nFailures = 0
            if self.oidFirmwareEntry is not None:
                try:
                    # Get the system firmware
                    _, self.firmwareVersion = self.snmp.get(self.oidFirmwareEntry)
                    
                except Exception as e:
                    _LogThreadException(self, e, logger=shlThreadsLogger)
                    self.lastError = str(e)
                    nFailures += 1
                    self.firmwareVersion = None
                    
            if self.oidFrequencyEntry is not None:
                try:
                    # Get the current input frequency
                    _, PWRfreq = self.snmp.get(self.oidFrequencyEntry)
                    try:
                        self.frequency = float(unicode(PWRfreq)) / 10.0
                    except NameError:
                        self.frequency = float(str(PWRfreq)) / 10.0
                    self.lastError = None
                    
                except Exception as e:
                    _LogThreadException(self, e, logger=shlThreadsLogger)
                    self.lastError = str(e)
                    nFailures += 1
                    self.frequency = None
                    
            if self.oidVoltageEntry is not None:
                try:
                    # Get the current input voltage
                    _, PWRvoltage = self.snmp.get(self.oidVoltageEntry)
                    try:
                        self.voltage = float(unicode(PWRvoltage))
                    except NameError:
                        self.voltage = float(str(PWRvoltage))
                    self.lastError = None
                    
                except Exception as e:
                    _LogThreadException(self, e, logger=shlThreadsLogger)
                    if self.lastError is not None:
                        self.lastError = "%s; %s" % (self.lastError, str(e))
                    else:
                        self.lastError = str(e)
                    nFailures += 1
                    self.voltage = None
                    
            if self.oidCurrentEntry is not None:
                try:
                    # Get the current draw of outlet #(i+1)
                    _, PWRcurrent = self.snmp.get(self.oidCurrentEntry)
                    try:
                        self.current = float(unicode(PWRcurrent))
                    except NameError:
                        self.current = float(str(PWRcurrent))
                    if self.firmwareVersion == '12.04.0053':
                       pass
                    else:
                        self.current = self.current / 10.0
                    self.lastError = None
                    
                except Exception as e:
                    _LogThreadException(self, e, logger=shlThreadsLogger)
                    if self.lastError is not None:
                        self.lastError = "%s; %s" % (self.lastError, str(e))
                    else:
                        self.lastError = str(e)
                    nFailures += 1
                    self.current = None
                    
            if self.oidUPSOutputEntry is not None:
                try:
                    # Get the current draw of outlet #(i+1)
                    _, UPSoutput = self.snmp.get(self.oidUPSOutputEntry)
                    try:
                        try:
                            self.upsOutput = self.upsOutputCodes[int(unicode(UPSoutput))]
                        except NameError:
                            self.upsOutput = self.upsOutputCodes[int(str(UPSoutput))]
                    except KeyError:
                        self.upsOutput = "UNK"
                    self.lastError = None
                    
                except Exception as e:
                    _LogThreadException(self, e, logger=shlThreadsLogger)
                    if self.lastError is not None:
                        self.lastError = "%s; %s" % (self.lastError, str(e))
                    else:
                        self.lastError = str(e)
                    nFailures += 1
                    self.upsOutput = None
                    
            if self.oidBatteryChargeEntry is not None:
                try:
                    # Get the current draw of outlet #(i+1)
                    _, BTYcharge = self.snmp.get(self.oidBatteryChargeEntry)
                    try:
                        self.batteryCharge = float(unicode(BTYcharge))
                    except NameError:
                        self.batteryCharge = float(str(BTYcharge))
                    self.lastError = None
                    
                except Exception as e:
                    _LogThreadException(self, e, logger=shlThreadsLogger)
                    if self.lastError is not None:
                        self.lastError = "%s; %s" % (self.lastError, str(e))
                    else:
                        self.lastError = str(e)
                    nFailures += 1
                    self.batteryCharge = None
                    
            if self.oidBatteryStatusEntry is not None:
                try:
                    # Get the current draw of outlet #(i+1)
                    _, BTYstatus = self.snmp.get(self.oidBatteryStatusEntry)
                    try:
                        try:
                            self.batteryStatus = self.batteryStatusCodes[int(unicode(BTYstatus))]
                        except NameError:
                           self.batteryStatus = self.batteryStatusCodes[int(str(BTYstatus))]
                    except KeyError:
                        self.batteryStatus = "UNK"
                    self.lastError = None
                    
                except Exception as e:
                    _LogThreadException(self, e, logger=shlThreadsLogger)
                    if self.lastError is not None:
                        self.lastError = "%s; %s" % (self.lastError, str(e))
                    else:
                        self.lastError = str(e)
                    nFailures += 1
                    self.batteryStatus = None
                    
            if self.oidOutletStatusBaseEntry is not None:
                for i in range(1, self.nOutlets+1):
                    # Get the status of outlet #(i+1).
                    # NOTE:  Since the self.oidOutletStatusBaseEntry is just a base entry, 
                    # we need to append on the outlet number (1-indexed) before we can use
                    # it
                    oidOutletStatusEntry = self.oidOutletStatusBaseEntry+(i,)
                    
                    try:
                        _, PortStatus = self.snmp.get(oidOutletStatusEntry)
                        try:
                            PortStatus = int(unicode(PortStatus))
                        except NameError:
                            PortStatus = int(str(PortStatus))
                            
                        try:
                            self.status[i] = self.outletStatusCodes[PortStatus]
                        except KeyError:
                            self.status[i] = "UNK"
                        if self.lastError is not None:
                            self.lastError = None
                            
                    except Exception as e:
                        _LogThreadException(self, e, logger=shlThreadsLogger)
                        if self.lastError is not None:
                            self.lastError = "%s; %s" % (self.lastError, str(e))
                        else:
                            self.lastError = str(e)
                        nFailures += 1
                        self.status[i] = "UNK"
                            
            toDataLog = "%.2f,%.2f,%.2f,%.2f,%s,%s,%.2f" % (time.time(), self.frequency if self.frequency is not None else -1, self.voltage if self.voltage is not None else -1, self.current if self.current is not None else -1, self.upsOutput, self.batteryStatus, self.batteryCharge if self.batteryCharge is not None else -1)
            with open('/data/rack%02i.txt' % self.id, 'a+') as fh:
                fh.write('%s\n' % toDataLog)
                
            # Make sure the device is reachable
            if self.SHLCallbackInstance is not None:
                if nFailures > 0:
                    was_unreachable = 5
                    self.SHLCallbackInstance.processUnreachable('%s-%s' % (type(self).__name__, str(self.id)))
                else:
                    if was_unreachable > 1:
                        was_unreachable -= 1
                    elif was_unreachable == 1:
                        was_unreachable = 0
                        self.SHLCallbackInstance.processUnreachable('cleared-%s-%s' % (type(self).__name__, str(self.id)))
                        
            # Stop time
            tStop = time.time()
            shlThreadsLogger.debug('Finished updating current and port status in %.3f seconds', tStop - tStart)
            
            # Sleep for a bit
            sleepCount = 0
            sleepTime = self.MonitorPeriod - (tStop - tStart)
            while (self.alive.isSet() and sleepCount < sleepTime):
                time.sleep(0.2)
                sleepCount += 0.2
                
    def getOutputSource(self):
        """
        Return the current power source.
        """
        
        return self.upsOutput
        
    def getBatteryCharge(self):
        """
        Return the battery change percentage.
        """
        
        return self.batteryCharge
    
    def getBatteryStatus(self):
        """
        Return the battery status.
        """
        
        return self.batteryStatus


class APCUPS(TrippLiteUPS):
    """
    Sub-class of the TrippLiteUPS class for the APC UPS on ADP.
    
    MIB sources:
    http://www.simpleweb.org/ietf/mibs/modules/IETF/txt/UPS-MIB
    http://www.oidview.com/mibs/0/UPS-MIB.html
    http://www.oidview.com/mibs/318/PowerNet-MIB.html
    """
    
    def __init__(self, ip, port, community, id, nOutlets=8, description=None, SHLCallbackInstance=None, MonitorPeriod=1.0):
        super(APCUPS, self).__init__(ip, port, community, id, nOutlets=nOutlets, description=description, SHLCallbackInstance=SHLCallbackInstance, MonitorPeriod=MonitorPeriod)
        
        # Setup the OID values
        self.oidFirmwareEntry = (1,3,6,1,2,1,33,1,1,3,0)
        self.oidFrequencyEntry = (1,3,6,1,2,1,33,1,3,3,1,2,1)
        self.oidVoltageEntry = (1,3,6,1,2,1,33,1,3,3,1,3,1)
        self.oidCurrentEntry = (1,3,6,1,2,1,33,1,4,4,1,3,1)
        self.oidUPSOutputEntry = (1,3,6,1,2,1,33,1,4,1,0)
        self.oidBatteryChargeEntry = (1,3,6,1,2,1,33,1,2,4,0)
        self.oidBatteryStatusEntry = (1,3,6,1,2,1,33,1,2,1,0)
        self.oidOutletStatusBaseEntry =  (1,3,6,1,4,1,318,1,1,1,12,1,2,1,3,)
        self.oidOutletChangeBaseEntry = (1,3,6,1,4,1,318,1,1,1,12,3,2,1,3,)
        
        # Setup the status codes
        self.outletStatusCodes = {1: "ON", 2: "OFF", 3: "CYC"}


class Weather(object):
    """
    Class for reading in values from the weather station database.
    """

    def __init__(self, config, SHLCallbackInstance=None, MonitorPeriod=120.0):
        self.config = config
        self.SHLCallbackInstance = SHLCallbackInstance
        self.MonitorPeriod = MonitorPeriod
        
        # Update the configuration
        self.updateConfig()
        
        # Setup threading
        self.thread = None
        self.alive = threading.Event()
        self.lastError = None
        
        # Setup variables
        self.updatetime = None
        self.usUnits = False
        self.pressure = None
        self.temperature = None
        self.humidity = None
        self.windSpeed = None
        self.windDir = None
        self.windGust = None
        self.windGustDir = None
        self.rain = None
        self.rainRate = None
        
    def updateConfig(self, config=None):
        """
        Using the configuration file, update the database file.
        """
        
        # Update the current configuration
        if config is not None:
            self.config = config
        self.database = self.config['weather']['database']
        
    def start(self):
        """
        Start the monitoring thread.
        """
        
        if self.thread is not None:
            self.stop()
            
        self.thread = threading.Thread(target=self.monitorThread)
        self.thread.setDaemon(1)
        self.alive.set()
        self.thread.start()
        
    def stop(self):
        """
        Stop the monitor thread, waiting until it's finished.
        """
        
        if self.thread is not None:
            self.alive.clear()          #clear alive event for thread
            self.thread.join()          #wait until thread has finished
            self.thread = None
            self.lastError = None
            
    def monitorThread(self):
        """
        Create a monitoring thread for the temperature.
        """
        
        was_unreachable = 0
        
        while self.alive.isSet():
            tStart = time.time()
            
            updated_list = []
            updated_age = 86400
            
            try:
                # Make sure we don't try near the edge of a minute
                tNow = int(time.time())
                while ((tNow % 60) < 10) or ((tNow % 60) > 50):
                    time.sleep(5)
                    tNow = int(time.time())
                    
                conn = sqlite3.connect(self.database, timeout=15)
                conn.row_factory = sqlite3.Row
                
                c = conn.cursor()
                c.execute("SELECT * FROM archive ORDER BY dateTime DESC")
                row = c.fetchone()
                
                self.updatetime = int(row['dateTime'])
                updated_list.append('updatetime')
                updated_age = tStart - self.updatetime
                
                self.usUnits = bool(row['usUnits'])
                updated_list.append('usUnits')
                self.pressure = float(row['barometer'])
                updated_list.append('pressure')
                self.temperature = float(row['outTemp'])
                updated_list.append('temperature')
                self.humidity = float(row['outHumidity'])
                updated_list.append('humidity')
                self.windSpeed = float(row['windSpeed'])
                updated_list.append('windSpeed')
                self.windDir = float(row['windDir'])
                updated_list.append('windDir')
                self.windGust = float(row['windGust'])
                updated_list.append('windGust')
                self.windGustDir = float(row['windGustDir'])
                updated_list.append('windGustDir')
                self.rain = float(row['rain'])
                updated_list.append('rain')
                self.rainRate = float(row['rainRate'])
                updated_list.append('rainRate')
                
                conn.close()
                
            except Exception as e:
                _LogThreadException(self, e, logger=shlThreadsLogger)
                
                try:
                    conn.close()
                except:
                    pass
                    
                if self.lastError is not None:
                    self.lastError = "%s; %s" % (self.lastError, str(e))
                else:
                    self.lastError = str(e)
                if 'updatetime' not in updated_list:
                    self.updatetime = None
                    if os.path.exists(self.database):
                        updated_age = tStart - os.path.getmtime(self.database)
                        
                if 'usUnits' not in updated_list:
                    self.usUnits = False
                if 'pressure' not in updated_list:
                    self.pressure = None
                if 'temperature' not in updated_list:
                    self.temperature = None
                if 'humidity' not in updated_list:
                    self.humidity = None
                if 'windSpeed' not in updated_list:
                    self.windSpeed = None
                if 'windDir' not in updated_list:
                    self.windDir = None
                if 'windGust' not in updated_list:
                    self.windGust = None
                if 'windGustDir' not in updated_list:
                    self.windGustDir = None
                if 'rain' not in updated_list:
                    self.rain = None
                if 'rainRate' not in updated_list:
                    self.rainRate = None
                    
            if self.SHLCallbackInstance is not None:
                if updated_age > 900:
                    was_unreachable = 2
                    self.SHLCallbackInstance.processUnreachable('weather-station')
                else:
                    if was_unreachable > 1:
                        was_unreachable -= 1
                    elif was_unreachable == 1:
                        was_unreachable = 0
                        self.SHLCallbackInstance.processUnreachable('cleared-weather-station')
                        
            # Stop time
            tStop = time.time()
            shlThreadsLogger.debug('Finished updating weather station data in %.3f seconds', tStop - tStart)
            
            # Sleep for a bit
            sleepCount = 0
            sleepTime = self.MonitorPeriod - (tStop - tStart)
            while (self.alive.isSet() and sleepCount < sleepTime):
                time.sleep(1.0)
                sleepCount += 1.0
                
    def getLastUpdateTime(self):
        """
        Return the time of last update as a datetime object in UTC.
        """
        
        if self.updatetime is None:
            return None
            
        return datetime.utcfromtimestamp(self.updatetime)
        
    def getTemperature(self, DegreesF=True):
        """
        Return the outside temperature in degrees F.
        """
        
        if self.temperature is None:
            return None
            
        if self.usUnits:
            f =  self.temperature
        else:
            f = 1.8*self.temperature + 32
            
        if DegreesF:
            return f
        else:
            return (f - 32)/1.8
            
    def getHumidity(self):
        """
        Return the outside humdity.
        """
        
        return self.humidity
        
    def getPressure(self):
        """
        Return the barometric pressure.
        """
        
        return self.pressure
        
    def getWind(self, MPH=True):
        """
        Return a two-element tuple of wind speed and direction.
        """
        
        if self.windSpeed is None or self.windDir is None:
            return (None, None)
            
        if self.usUnits:
            m = self.windSpeed
        else:
            m = self.windSpeed / 1.60934
            
        if MPH:
            return (m, self.windDir)
        else:
            return (m*1.60934, self.windDir)
            
    def getGust(self, MPH=True):
        """
        Return a two-element tuple of wind gust speed and direction.
        """
        
        if self.windGust is None or self.windGustDir is None:
            return (None, None)
            
        if self.usUnits:
            m = self.windGust
        else:
            m = self.windGust / 1.60934
            
        if MPH:
            return (m, self.windGustDir)
        else:
            return (m*1.60934, self.windGustDir)
            
    def getPercipitation(self, Inches=True):
        """
        Return a two-element tuple of rainfall rate and total 
        rainfall.
        """
        
        if self.rainRate is None or self.rain is None:
            return (None, None)
            
        if self.usUnits:
            rri = self.rainRate
            rfi = self.rain
        else:
            rri = self.rainRate / 25.4
            rfi = self.rain / 25.4
            
        if Inches:
            return (rri, rfi)
        else:
            return (rri*25.4, rfi*25.4)


class Lightning(object):
    """
    Class for interfacing with the lightning detector via UDP.
    """
    
    def __init__(self, config, SHLCallbackInstance=None):
        self.config = config
        self.SHLCallbackInstance = SHLCallbackInstance
        
        self.address = self.config['lightning']['ip']
        self.port = self.config['lightning']['port']
        
        # Update the configuration
        self.updateConfig()
        
        # Setup threading
        self.thread = None
        self.alive = threading.Event()
        self.lastError = None
        
        # Setup variables
        self.lock = threading.RLock()
        self.strikes = {}
        self.aging = 32*60
        
    def updateConfig(self, config=None):
        """
        Using the configuration file, update the database file.
        """
        
        # Update the current configuration
        if config is not None:
            self.config = config
            
    def start(self):
        """
        Start the monitoring thread.
        """
        
        if self.thread is not None:
            self.stop()
            
        self.thread = threading.Thread(target=self.monitorThread)
        self.thread.setDaemon(1)
        self.alive.set()
        self.thread.start()
        
    def stop(self):
        """
        Stop the monitor thread, waiting until it's finished.
        """
        
        if self.thread is not None:
            self.alive.clear()          #clear alive event for thread
            self.thread.join()          #wait until thread has finished
            self.thread = None
            self.lastError = None
            
    def _connect(self, sock=None, timeout=60):
        """
        Create the UDP socket used for recieving notifications.
        """
        
        if sock is not None:
            sock.close()
            
        #create a UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        #allow multiple sockets to use the same PORT number
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        #Bind to the port that we know will receive multicast data
        sock.bind(("0.0.0.0", self.port))
        #tell the kernel that we are a multicast socket
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        #Tell the kernel that we want to add ourselves to a multicast group
        #The address for the multicast group is the third param
        status = sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                socket.inet_aton(self.address) + socket.inet_aton("0.0.0.0"))
        # Set the timeout
        sock.settimeout(timeout)
        
        return sock
        
    def monitorThread(self):
        """
        Create a monitoring thread for lightning.
        """
        
        dataRE = re.compile(r'^\[(?P<date>.*)\] (?P<type>[A-Z]*): (?P<data>.*)$')
        
        #create a UDP socket
        sock = self._connect()
        
        was_unreachable = 0
        
        tCull = time.time()
        while self.alive.isSet():
            try:
                tNow = time.time()
                try:
                    data, addr = sock.recvfrom(1024)
                    
                    if was_unreachable > 1:
                        was_unreachable -= 1
                    elif was_unreachable == 1:
                        was_unreachable = 0
                        self.SHLCallbackInstance.processUnreachable('cleared-lightning-detector')
                        
                except socket.timeout:
                    shlThreadsLogger.warning('Lightning: monitorThread timeout on socket, re-trying')
                    if self.SHLCallbackInstance is not None:
                        was_unreachable = 5
                        self.SHLCallbackInstance.processUnreachable('lightning-detector')
                        
                    sock = self._connect(sock)
                    continue
                    
                # RegEx matching for message date, type, and content
                try:
                    data = data.decode('ascii')
                except AttributeError:
                    pass
                mtch = dataRE.match(data)
                t = datetime.strptime(mtch.group('date'), "%Y-%m-%d %H:%M:%S.%f")
                
                # If we have a lightning strike, figure out it if is close
                # enough to warrant saving the strike info.
                if mtch.group('type') == 'LIGHTNING':
                    dist, junk = mtch.group('data').split(None, 1)
                    dist = float(dist)
                    
                    with self.lock:
                        self.strikes[t] = dist
                        
                # Cull the list of old strikes every two minutes
                if (time.time() - tCull) > 120:
                    pruneTime = t
                    with self.lock:
                        for k in self.strikes.keys():
                            if pruneTime - k > timedelta(seconds=self.aging):
                                del self.strikes[k]
                    tCull = time.time()
                    
            except Exception as e:
                _LogThreadException(self, e, logger=shlThreadsLogger)
                if self.lastError is not None:
                    self.lastError = "%s; %s" % (self.lastError, str(e))
                else:
                    self.lastError = str(e)
                    
        sock.close()
        
    def getStrikeCount(self, radius=15, interval=10):
        """
        Return the number of lightning strikes detected without the 
        specified radius in km and the spcified time interval in minutes.
        """
        
        tNow = datetime.utcnow()
        tWindow = tNow - timedelta(minutes=int(interval))
        counter = 0
        
        try:
            with self.lock:
                for k in self.strikes.keys():
                    if k >= tWindow:
                        if self.strikes[k] <= radius:
                            counter += 1
                            
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            shlThreadsLogger.error("Lightning: getStrikeCount failed with: %s at line %i", str(e), exc_traceback.tb_lineno)
            
            ## Grab the full traceback and save it to a string via StringIO
            fileObject = StringIO()
            traceback.print_tb(exc_traceback, file=fileObject)
            tbString = fileObject.getvalue()
            fileObject.close()
            ## Print the traceback to the logger as a series of DEBUG messages
            for line in tbString.split('\n'):
                shlThreadsLogger.debug("%s", line)
                
            counter = None
            
        return counter


class Outage(object):
    """
    Class for interfacing with the line voltage monitor via UDP.
    """
    
    def __init__(self, config, SHLCallbackInstance=None):
        self.config = config
        self.SHLCallbackInstance = SHLCallbackInstance
        
        self.address = self.config['outage']['ip']
        self.port = self.config['outage']['port']
        
        # Update the configuration
        self.updateConfig()
        
        # Setup threading
        self.thread = None
        self.alive = threading.Event()
        self.lastError = None
        
        # Setup variables
        self.flicker_120 = None
        self.flicker_240 = None
        self.outage_120 = None
        self.outage_240 = None
        self.aging = 300
        
    def updateConfig(self, config=None):
        """
        Using the configuration file, update the database file.
        """
        
        # Update the current configuration
        if config is not None:
            self.config = config
            
    def start(self):
        """
        Start the monitoring thread.
        """
        
        if self.thread is not None:
            self.stop()
            
        # Check for some state
        ## 120 VAC
        try:
            with open(os.path.join(STATE_DIR, 'inPowerFailure120'), 'r') as fh:
                t = datetime.strptime(fh.read(), "%Y-%m-%d %H:%M:%S.%f")
                
            self.outage_120 = t
            shlThreadsLogger.info('Outage: start - restored a saved power outage from disk - 120VAC')
            
            #os.unlink(os.path.join(STATE_DIR, 'inPowerFailure120'))
        except Exception as e:
            pass
        ### 240 VAC
        try:
            with open(os.path.join(STATE_DIR, 'inPowerFailure240'), 'r') as fh:
                t = datetime.strptime(fh.read(), "%Y-%m-%d %H:%M:%S.%f")
                
            self.outage_240 = t
            shlThreadsLogger.info('Outage: start - restored a saved power outage from disk - 240VAC')
            
            #os.unlink(os.path.join(STATE_DIR, 'inPowerFailure240'))
        except Exception as e:
            pass
            
        self.thread = threading.Thread(target=self.monitorThread)
        self.thread.setDaemon(1)
        self.alive.set()
        self.thread.start()
        
    def stop(self):
        """
        Stop the monitor thread, waiting until it's finished.
        """
        
        if self.thread is not None:
            self.alive.clear()          #clear alive event for thread
            self.thread.join()          #wait until thread has finished
            self.thread = None
            self.lastError = None
            
    def _connect(self, sock=None, timeout=60):
        """
        Create the UDP socket used for recieving notifications.
        """
        
        if sock is not None:
            sock.close()
            
        #create a UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        #allow multiple sockets to use the same PORT number
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        #Bind to the port that we know will receive multicast data
        sock.bind(("0.0.0.0", self.port))
        #tell the kernel that we are a multicast socket
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        #Tell the kernel that we want to add ourselves to a multicast group
        #The address for the multicast group is the third param
        status = sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                                 socket.inet_aton(self.address) + socket.inet_aton("0.0.0.0"))
        # Set the timeout
        sock.settimeout(timeout)
        
        return sock
           
    def monitorThread(self):
        """
        Create a monitoring thread for the power.
        """
        
        dataRE = re.compile(r'^\[(?P<date>.*)\] (?P<type>[A-Z0-9]*): (?P<data>.*)$')
        
        #create a UDP socket
        sock = self._connect()
        
        tCull = datetime.utcnow()
        deltaCull = timedelta(minutes=2)
        deltaAging = timedelta(seconds=int(self.aging))
        
        was_unreachable = 0
        
        while self.alive.isSet():
            try:
                tNow = datetime.utcnow()
                try:
                    data, addr = sock.recvfrom(1024)
                    
                    if was_unreachable > 1:
                        was_unreachable -= 1
                    elif was_unreachable == 1:
                        was_unreachable = 0
                        self.SHLCallbackInstance.processUnreachable('cleared-voltage-monitor')
                except socket.timeout:
                    shlThreadsLogger.warning('Outage: monitorThread timeout on socket, re-trying')
                    if self.SHLCallbackInstance is not None:
                        was_unreachable = 5
                        self.SHLCallbackInstance.processUnreachable('voltage-monitor')
                        
                    sock = self._connect(sock)
                    continue
                    
                # RegEx matching for message date, type, and content
                try:
                    data = data.decode('ascii')
                except AttributeError:
                    pass
                mtch = dataRE.match(data)
                tEvent = datetime.strptime(mtch.group('date'), "%Y-%m-%d %H:%M:%S.%f")
                
                # Figure out what to do with the notification
                if mtch.group('type') == 'FLICKER':
                    if mtch.group('data').find('120V') != -1:
                        shlThreadsLogger.info('Outage: monitorThread - flicker - 120VAC')
                        self.flicker_120 = tEvent
                    else:
                        shlThreadsLogger.info('Outage: monitorThread - flicker - 240VAC')
                        self.flicker_240 = tEvent
                        
                    if self.SHLCallbackInstance is not None:
                        self.SHLCallbackInstance.processPowerFlicker(False)
                        
                elif mtch.group('type') == 'OUTAGE':
                    if mtch.group('data').find('120V') != -1:
                        shlThreadsLogger.info('Outage: monitorThread - outage - 120VAC')
                        self.outage_120 = tEvent
                        
                        try:
                            with open(os.path.join(STATE_DIR, 'inPowerFailure120'), 'w') as fh:
                                fh.write(mtch.group('date'))
                        except (OSError, IOError) as e:
                            exc_type, exc_value, exc_traceback = sys.exc_info()
                            shlThreadsLogger.warning("Outage: monitorThread 120VAC save state failed with: %s at line %i", str(e), exc_traceback.tb_lineno)
                            
                    else:
                        shlThreadsLogger.info('Outage: monitorThread - outage - 240VAC')
                        self.outage_240 = tEvent
                        
                        try:
                            with open(os.path.join(STATE_DIR, 'inPowerFailure240'), 'w') as fh:
                                fh.write(mtch.group('date'))
                        except (OSError, IOError) as e:
                            exc_type, exc_value, exc_traceback = sys.exc_info()
                            shlThreadsLogger.warning("Outage: monitorThread 240VAC save state failed with: %s at line %i", str(e), exc_traceback.tb_lineno)
                            
                    if self.SHLCallbackInstance is not None:
                        self.SHLCallbackInstance.processPowerOutage(True)
                        
                elif mtch.group('type') == 'CLEAR':
                    if mtch.group('data').find('120V') != -1:
                        shlThreadsLogger.info('Outage: monitorThread - clear - 120VAC')
                        self.outage_120 = None
                        
                        try:
                            os.unlink(os.path.join(STATE_DIR, 'inPowerFailure120'))
                        except OSError:
                            pass
                    else:
                        shlThreadsLogger.info('Outage: monitorThread - clear - 240VAC')
                        self.outage_240 = None
                        
                        try:
                            os.unlink(os.path.join(STATE_DIR, 'inPowerFailure240'))
                        except OSError:
                            pass
                            
                    if self.SHLCallbackInstance is not None:
                        self.SHLCallbackInstance.processPowerOutage(False)
                        
                # Cull the list of old events every so often
                if (tNow - tCull) >= deltaCull:
                    refresh_state = False
                    if self.flicker_120 is not None:
                        if (tNow - self.flicker_120) >= deltaAging:
                            refresh_state = True
                            self.flicker_120 = None
                    if self.flicker_240 is not None:
                        if (tNow - self.flicker_240) >= deltaAging:
                            refresh_state = True
                            self.flicker_240 = None
                    tCull = tNow
                    
                    if refresh_state and self.SHLCallbackInstance is not None:
                        self.SHLCallbackInstance.processPowerFlicker(False)
                        
            except Exception as e:
                _LogThreadException(self, e, logger=shlThreadsLogger)
                if self.lastError is not None:
                    self.lastError = "%s; %s" % (self.lastError, str(e))
                else:
                    self.lastError = str(e)
                    
        sock.close()
        
    def getFlicker(self):
        try:
            flicker = False
            if self.flicker_120 is not None or self.flicker_240 is not None:
                flicker = True
                
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            shlThreadsLogger.error("Outage: getFlicker failed with: %s at line %i", str(e), exc_traceback.tb_lineno)
            
            ## Grab the full traceback and save it to a string via StringIO
            fileObject = StringIO()
            traceback.print_tb(exc_traceback, file=fileObject)
            tbString = fileObject.getvalue()
            fileObject.close()
            ## Print the traceback to the logger as a series of DEBUG messages
            for line in tbString.split('\n'):
                shlThreadsLogger.debug("%s", line)
                
            flicker = None
            
        return flicker
        
    def getOutage(self):
        try:
            outage = False
            if self.outage_120 is not None or self.outage_240 is not None:
                outage = True
                
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            shlThreadsLogger.error("Outage: getOutage failed with: %s at line %i", str(e), exc_traceback.tb_lineno)
            
            ## Grab the full traceback and save it to a string via StringIO
            fileObject = StringIO()
            traceback.print_tb(exc_traceback, file=fileObject)
            tbString = fileObject.getvalue()
            fileObject.close()
            ## Print the traceback to the logger as a series of DEBUG messages
            for line in tbString.split('\n'):
                shlThreadsLogger.debug("%s", line)
                
            outage = None
            
        return outage
