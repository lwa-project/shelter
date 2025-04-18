#!/usr/bin/env python3

"""
shl_cmnd.py -
"""

import os
import git
import sys
import json
import time
import signal
import socket
import string
import struct
import logging
import argparse
import json_minify
try:
        from logging.handlers import WatchedFileHandler
except ImportError:
        from logging import FileHandler as WatchedFileHandler
import traceback
try:
        from cStringIO import StringIO
except ImportError:
        from io import StringIO

from MCS import *

from shlThreads import *
from shlFunctions import ShippingContainer

__version__ = "0.3"
__all__ = ['DEFAULTS_FILENAME', 'MCSCommunicate']


#
# Default Configuration File
#
DEFAULTS_FILENAME = '/lwa/software/defaults.json'


class MCSCommunicate(Communicate):
    """
    Class to deal with the communicating with MCS.
    """
    
    def __init__(self, SubSystemInstance, config, opts):
            super(MCSCommunicate, self).__init__(SubSystemInstance, config, opts)
        
    def processCommand(self, data):
        """
        Interpret the data of a UDP packet as a SHL MCS command.
        """
        
        destination, sender, command, reference, datalen, mjd, mpm, data = self.parsePacket(data)
    
        # check destination and sender
        if destination in (self.SubSystemInstance.subSystem, 'ALL'):
            # PNG
            if command == 'PNG':
                status = True
                packed_data = ''
            
            # Report various MIB entries
            elif command == 'RPT':
                status = True
                packed_data = ''
                
                ## General Info.
                if data == 'SUMMARY':
                    summary = self.SubSystemInstance.currentState['status'][:7]
                    self.logger.debug('summary = %s', summary)
                    packed_data = summary
                elif data == 'INFO':
                    ### Trim down as needed
                    if len(self.SubSystemInstance.currentState['info']) > 256:
                        infoMessage = "%s..." % self.SubSystemInstance.currentState['info'][:253]
                    else:
                        infoMessage = self.SubSystemInstance.currentState['info'][:256]
                        
                    self.logger.debug('info = %s', infoMessage)
                    packed_data = infoMessage
                elif data == 'LASTLOG':
                    ### Trim down as needed
                    if len(self.SubSystemInstance.currentState['lastLog']) > 256:
                        lastLogEntry = "%s..." % self.SubSystemInstance.currentState['lastLog'][:253]
                    else:
                        lastLogEntry =  self.SubSystemInstance.currentState['lastLog'][:256]
                    if len(lastLogEntry) == 0:
                        lastLogEntry = 'no log entry'
                    
                    self.logger.debug('lastlog = %s', lastLogEntry)
                    packed_data = lastLogEntry
                elif data == 'SUBSYSTEM':
                    self.logger.debug('subsystem = %s', self.SubSystemInstance.subSystem)
                    packed_data = self.SubSystemInstance.subSystem
                elif data == 'SERIALNO':
                    self.logger.debug('serialno = %s', self.SubSystemInstance.serialNumber)
                    packed_data = self.SubSystemInstance.serialNumber
                elif data == 'VERSION':
                    self.logger.debug('version = %s', self.SubSystemInstance.version)
                    packed_data = self.SubSystemInstance.version
                    
                ## PDU State - Number of ports
                elif data[0:17] == 'PORTS-AVAILABLE-R':
                    rack = int(data[17:])
                    
                    status, count = self.SubSystemInstance.getOutletCount(rack)
                    if status:
                        packed_data = str(count)
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                        
                    self.logger.debug('%s = exited with status %s', data, str(status))
                ## PDU State - Current Draw
                elif data[0:9] == 'CURRENT-R':
                    rack = int(data[9:])
                    
                    status, current = self.SubSystemInstance.getCurrentDraw(rack)
                    if status:
                        if current is not None:
                            packed_data = str(current)
                        else:
                            packed_data = '0'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                        
                    self.logger.debug('%s = exited with status %s', data, str(status))
                ## PDU State - Input Voltage
                elif data[0:9] == 'VOLTAGE-R':
                    rack = int(data[9:])
                    
                    status, voltage = self.SubSystemInstance.getInputVoltage(rack)
                    if status:
                        if voltage is not None:
                            packed_data = str(voltage)
                        else:
                            packed_data = '0'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                        
                    self.logger.debug('%s = exited with status %s', data, str(status))
                ## PDU State - Input Frequency
                elif data[0:11] == 'FREQUENCY-R':
                    rack = int(data[11:])
                    
                    status, freq = self.SubSystemInstance.getInputFrequency(rack)
                    if status:
                        if freq is not None:
                            packed_data = str(freq)
                        else:
                            packed_data = '0'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                        
                    self.logger.debug('%s = exited with status %s', data, str(status))
                ## PDU State - Outlet Status
                elif data[0:5] == 'PWR-R':
                    rack, port = data[5:].split('-', 1)
                    rack = int(rack)
                    port = int(port)
                    
                    status, state = self.SubSystemInstance.getPowerState(rack, port)
                    if status:
                        packed_data = str(state)
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                        
                    self.logger.debug('%s = exited with status %s', data, str(status))
                ## UPS State - Battery Charge
                elif data[0:11] == 'BATCHARGE-R':
                    rack = int(data[11:])
                    
                    status, charge = self.SubSystemInstance.getBatteryCharge(rack)
                    if status:
                        if charge is not None:
                            packed_data = str(charge)
                        else:
                            packed_data = 'UNK'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                ## UPS State - Battery Status
                elif data[0:11] == 'BATSTATUS-R':
                    rack = int(data[11:])
                    
                    status, stat = self.SubSystemInstance.getBatteryStatus(rack)
                    if status:
                        if stat is not None:
                            packed_data = str(stat)
                        else:
                            packed_data = 'UNK'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                ## UPS State - Output Power Source
                elif data[0:11] == 'OUTSOURCE-R':
                    rack = int(data[11:])
                    
                    status, source = self.SubSystemInstance.getOutputSource(rack)
                    if status:
                        if source is not None:
                            packed_data = str(source)
                        else:
                            packed_data = 'UNK'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                
                ## Weather Station - Last Update
                elif data[0:14] == 'WX-UPDATED':
                    status, uptd = self.SubSystemInstance.getWeatherUpdateTime()
                    if status:
                        if uptd is not None:
                            packed_data = str(uptd)
                        else:
                            packed_data = 'UNK'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                ## Weather Station - Temperature
                elif data[0:14] == 'WX-TEMPERATURE':
                    status, temp = self.SubSystemInstance.getOutsideTemperature()
                    if status:
                        if temp is not None:
                            packed_data = str(temp)
                        else:
                            packed_data = 'UNK'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                ## Weather Station - Humidity
                elif data[0:11] == 'WX-HUMIDITY':
                    status, humid = self.SubSystemInstance.getOutsideHumidity()
                    if status:
                        if humid is not None:
                            packed_data = str(humid)
                        else:
                            packed_data = 'UNK'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                ## Weather Station - Pressure
                elif data[0:11] == 'WX-PRESSURE':
                    status, press = self.SubSystemInstance.getBarometricPressure()
                    if status:
                        if press is not None:
                            packed_data = str(press)
                        else:
                            packed_data = 'UNK'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                ## Weather Station - Wind
                elif data[0:7] == 'WX-WIND':
                    status, wind = self.SubSystemInstance.getWind()
                    if status:
                        if wind is not None:
                            packed_data = str(wind)
                        else:
                            packed_data = 'UNK'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                ## Weather Station - Gust
                elif data[0:7] == 'WX-GUST':
                    status, wind = self.SubSystemInstance.getWind()
                    if status:
                        if wind is not None:
                            packed_data = str(wind)
                        else:
                            packed_data = 'UNK'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                ## Weather Station - Rainfall Rate
                elif data[0:16] == 'WX-RAINFALL-RATE':
                    status, rain = self.SubSystemInstance.getRainfallRate()
                    if status:
                        if rain is not None:
                            packed_data = str(rain)
                        else:
                            packed_data = 'UNK'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                ## Weather Station - Rainfall Total
                elif data[0:17] == 'WX-RAINFALL-TOTAL':
                    status, rain = self.SubSystemInstance.getTotalRainfall()
                    if status:
                        if rain is not None:
                            packed_data = str(rain)
                        else:
                            packed_data = 'UNK'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                        
                ## Lightning - detection radius
                elif data[0:16] == 'LIGHTNING-RADIUS':
                    status, radius = True, 15.0
                    if status:
                        if radius is not None:
                            packed_data = str(radius)
                        else:
                            packed_data = 'UNK'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                ## Lightning - strikes within the last 10 minutes within the detection radius
                elif data[:15] == 'LIGHTNING-10MIN':
                    status, count = self.SubSystemInstance.getLightningStrikeCount(radius=15, interval=10)
                    if status:
                        if count is not None:
                            packed_data = str(count)
                        else:
                            packed_data = 'UNK'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                ## Lightning - strikes within the last 30 minutes within the detection radius
                elif data[:15] == 'LIGHTNING-30MIN':
                    status, count = self.SubSystemInstance.getLightningStrikeCount(radius=15, interval=30)
                    if status:
                        if count is not None:
                            packed_data = str(count)
                        else:
                            packed_data = 'UNK'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                        
                ## Line voltage - flicker
                elif data == 'POWER-FLICKER':
                    status, flicker = self.SubSystemInstance.getPowerFlicker()
                    if status:
                        if flicker is not None:
                            packed_data = str(flicker)
                        else:
                            packed_data = 'UNK'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                ## Line voltage - flicker
                elif data == 'POWER-OUTAGE':
                    status, outage = self.SubSystemInstance.getPowerOutage()
                    if status:
                        if outage is not None:
                            packed_data = str(outage)
                        else:
                            packed_data = 'UNK'
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                        
                ## Temperature set point
                elif data == 'SET-POINT':
                    packed_data = '%.1f' % self.SubSystemInstance.currentState['setPoint']
                    self.logger.debug('%s = %s', data, packed_data)
                    
                ## Temperature differential
                elif data == 'DIFFERENTIAL':
                    packed_data = '%.1f' % self.SubSystemInstance.currentState['diffPoint']
                    self.logger.debug('%s = %s', data, packed_data)
                    
                ## Current mean shelter temperature
                elif data == 'TEMPERATURE':
                    status, temp = self.SubSystemInstance.getMeanTemperature()
                    
                    if status:
                        packed_data = '%.2f' % temp
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                    
                    self.logger.debug('%s = exited with status %s', data, str(status))
                    
                ## Individual shelter temperature sensors
                elif data[:13] == 'TEMPERATURE-S':
                    sensor = int(data[13:])
                    
                    status, temp = self.SubSystemInstance.getTemperature(sensor)
                    
                    if status:
                        packed_data = '%.2f' % temp
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                    
                    self.logger.debug('%s = exited with status %s', data, str(status))
                    
                ## Smoke detector status
                elif data == 'SMOKE':
                    status, smoke = self.SubSystemInstance.getSmokeDetected()
                    
                    if status:
                        packed_data = str(smoke)
                    else:
                        packed_data = self.SubSystemInstance.currentState['lastLog']
                    
                    self.logger.debug('%s = exited with status %s', data, str(status))
                    
                ## Water sensor status
                elif data == 'WATER':
                        status, water = self.SubSystemInstance.getWaterDetected()
                        
                        if status:
                            packed_data = str(water)
                        else:
                            packed_data = self.SubSystemInstance.currentState['lastLog']
                        
                        self.logger.debug('%s = exited with status %s', data, str(status))
                        
                    ## Smoke detector status
                elif data == 'DOOR':
                        status, opened = self.SubSystemInstance.getDoorOpen()
                        
                        if status:
                            packed_data = 'OPEN' if opened else 'CLOSED'
                        else:
                            packed_data = self.SubSystemInstance.currentState['lastLog']
                        
                        self.logger.debug('%s = exited with status %s', data, str(status))
                        
                else:
                    status = False
                    packed_data = 'Unknown MIB entry: %s' % data
                    
                    self.logger.debug('%s = exited with status %s', data, str(status))
                    
                    
            #
            # Control Commands
            #
            
            # INI
            elif command == 'INI':
                # Re-read in the configuration file
                with open(self.opts.config, 'r') as ch:
                    config = json.loads(json_minify.json_minify(ch.read()))
                    
                # Refresh the configuration for the communicator and ASP
                self.updateConfig(config)
                self.SubSystemInstance.updateConfig(config)
                
                # Go
                status, exitCode = self.SubSystemInstance.ini(data)
                if status:
                    packed_data = ''
                else:
                    packed_data = "0x%02X! %s" % (exitCode, self.SubSystemInstance.currentState['lastLog'])
            
            # SHT
            elif command == 'SHT':
                status, exitCode = self.SubSystemInstance.sht(mode=data)
                if status:
                    packed_data = ''
                else:
                    packed_data = "0x%02X! %s" % (exitCode, self.SubSystemInstance.currentState['lastLog'])
                    
            # TMP
            elif command == 'TMP':
                setPoint = float(data)
                
                status, exitCode = self.SubSystemInstance.tmp(setPoint)
                if status:
                    packed_data = ''
                else:
                    packed_data = "0x%02X! %s" % (exitCode, self.SubSystemInstance.currentState['lastLog'])
                    
            # DIF
            elif command == 'DIF':
                diffPoint = float(data)
                
                status, exitCode = self.SubSystemInstance.dif(diffPoint)
                if status:
                    packed_data = ''
                else:
                    packed_data = "0x%02X! %s" % (exitCode, self.SubSystemInstance.currentState['lastLog'])
                    
            # PWR
            elif command == 'PWR':
                rack    = int(data[:1])
                port    = int(data[1:3])
                control = data[3:]
                
                status, exitCode = self.SubSystemInstance.pwr(rack, port, control)
                if status:
                    packed_data = ''
                else:
                    packed_data = "0x%02X! %s" % (exitCode, self.SubSystemInstance.currentState['lastLog'])
                    
                    
            # 
            # Unknown command catch
            #

            else:
                status = False
                self.logger.debug('%s = error, unknown command', command)
                packed_data = 'Unknown command: %s' % command

            # Return status, command, reference, and the result
            return sender, status, command, reference, packed_data


def main(args):
    """
    Main function of asp_cmnd.py.  This sets up the various configuration options 
    and start the UDP command handler.
    """
    
    # Setup logging
    logger = logging.getLogger(__name__)
    logFormat = logging.Formatter('%(asctime)s [%(levelname)-8s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    logFormat.converter = time.gmtime
    if args.log is None:
        logHandler = logging.StreamHandler(sys.stdout)
    else:
        logHandler = WatchedFileHandler(args.log)
    logHandler.setFormatter(logFormat)
    logger.addHandler(logHandler)
    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    # Get current MJD and MPM
    mjd, mpm = getTime()
    
    # Git information
    try:
        repo = git.Repo(os.path.dirname(os.path.abspath(__file__)))
        branch = repo.active_branch.name
        hexsha = repo.active_branch.commit.hexsha
        shortsha = hexsha[-7:]
        dirty = ' (dirty)' if repo.is_dirty() else ''
    except (git.exc.GitError, ValueError):
        branch = 'unknown'
        hexsha = 'unknown'
        shortsha = 'unknown'
        dirty = ''
        
    # Report on who we are
    logger.info('Starting shl_cmnd.py with PID %i', os.getpid())
    logger.info('Version: %s', __version__)
    logger.info('Revision: %s.%s%s', branch, shortsha, dirty)
    logger.info('Current MJD: %i', mjd)
    logger.info('Current MPM: %i', mpm)
    logger.info('All dates and times are in UTC except where noted')
    
    # Read in the configuration file
    with open(args.config, 'r') as ch:
        config = json.loads(json_minify.json_minify(ch.read()))
        
    # Setup ASP control
    lwaSHL = ShippingContainer(config)

    # Setup the communications channels
    mcsComms = MCSCommunicate(lwaSHL, config, args)
    mcsComms.start()
    
    # Initialize shelter
    lwaSHL.ini("72&1.0&%s" % ''.join(['1' for i in config['pdus']['devices'].keys()]))
    
    # Setup handler for SIGTERM so that we aren't left in a funny state
    def HandleSignalExit(signum, frame, logger=logger, MCSInstance=mcsComms):
        logger.info('Exiting on signal %i', signum)

        # Shutdown ASP and close the communications channels
        tStop = time.time()
        logger.info('Shutting down SHL, please wait...')
        MCSInstance.SubSystemInstance.sht(mode='SCRAM')
        while MCSInstance.SubSystemInstance.currentState['info'] != 'System has been shut down':
            time.sleep(1)
        logger.info('Shutdown completed in %.3f seconds', time.time() - tStop)
        MCSInstance.stop()
        
        # Exit
        logger.info('Finished')
        logging.shutdown()
        sys.exit(0)
    
    # Hook in the signal handler - SIGTERM
    signal.signal(signal.SIGTERM, HandleSignalExit)
    
    # Loop and process the MCS data packets as they come in - exit if ctrl-c is 
    # received
    logger.info('Ready to communicate')
    while True:
        try:
            mcsComms.receiveCommand()
            
        except KeyboardInterrupt:
            logger.info('Exiting on ctrl-c')
            break
            
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logger.error("asp_cmnd.py failed with: %s at line %i", str(e), exc_traceback.tb_lineno)
                
            ## Grab the full traceback and save it to a string via StringIO
            fileObject = StringIO()
            traceback.print_tb(exc_traceback, file=fileObject)
            tbString = fileObject.getvalue()
            fileObject.close()
            ## Print the traceback to the logger as a series of DEBUG messages
            for line in tbString.split('\n'):
                logger.debug("%s", line)
    
    # If we've made it this far, we have finished so shutdown ASP and close the 
    # communications channels
    tStop = time.time()
    print('\nShutting down SHL, please wait...')
    logger.info('Shutting down SHL, please wait...')
    lwaSHL.sht()
    while lwaSHL.currentState['info'] != 'System has been shut down':
        time.sleep(1)
    logger.info('Shutdown completed in %.3f seconds', time.time() - tStop)
    mcsComms.stop()
    
    # Exit
    logger.info('Finished')
    logging.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='control the SHL sub-system within the guidelines of the SHL and MCS ICDs',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    parser.add_argument('-c', '--config', type=str, default=DEFAULTS_FILENAME,
                        help='name of the SHL configuration file to use')
    parser.add_argument('-l', '--log', type=str,
                        help='name of the logfile to write logging information to')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='print debug messages as well as info and higher')
    args = parser.parse_args()
    main(args)
    
