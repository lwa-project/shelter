
"""
Base module for dealing with MCS communication.  This module provides the
MCSComminunicate framework that specified how to processes MCS commands that
arrive via UDP.  All that is needed for a sub-system is to overload the 
MCSCommunicate.processCommand() function to deal with the subsystem-specific
MIBs and commands.
"""

import sys
import math
import time
import select
import socket
import string
import logging
import traceback

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
    
from datetime import datetime

__version__ = "0.3"
__all__ = ['MCS_RCV_BYTES', 'getTime', 'Communicate']


# Maximum number of bytes to receive from MCS
MCS_RCV_BYTES = 16*1024


def getTime():
    """
    Return a two-element tuple of the current MJD and MPM.
    """
    
    # determine current time
    dt = datetime.utcnow()
    year        = dt.year             
    month       = dt.month      
    day         = dt.day    
    hour        = dt.hour
    minute      = dt.minute
    second      = dt.second     
    millisecond = dt.microsecond / 1000
    
    # compute MJD         
    # adapted from http://paste.lisp.org/display/73536
    # can check result using http://www.csgnetwork.com/julianmodifdateconv.html
    a = (14 - month) // 12
    y = year + 4800 - a          
    m = month + (12 * a) - 3                    
    p = day + (((153 * m) + 2) // 5) + (365 * y)   
    q = (y // 4) - (y // 100) + (y // 400) - 32045
    mjd = int(math.floor( (p+q) - 2400000.5))  
    
    # compute MPM
    mpm = int(math.floor( (hour*3600 + minute*60 + second)*1000 + millisecond ))
    
    return (mjd, mpm)


class Communicate(object):
    """
    Class to deal with the communcating with MCS.
    """
    
    def __init__(self, SubSystemInstance, config, opts):
        self.config = config
        self.opts = opts
        self.SubSystemInstance = SubSystemInstance
        
        # Update the socket configuration
        self.updateConfig()
        
        # Setup the poller
        self.poller = None
        
        # Set the logger
        self.logger = logging.getLogger('__main__')
        
    def updateConfig(self, config=None):
        """
        Using the configuration file, update the list of boards.
        """
        
        # Update the current configuration
        if config is not None:
            self.config = config
            
    def start(self):
        """
        Start the recieve thread - send will run only when needed.
        """
        
        # Setup the various sockets
        ## Receive
        try:
            self.socketIn =  socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socketIn.bind(("0.0.0.0", self.config['mcs']['message_in_port']))
            #self.socketIn.setblocking(0)
        except socket.error as err:
            code, e = err
            self.logger.critical('Cannot bind to listening port %i: %s', self.config['mcs']['message_in_port'], str(e))
            self.logger.critical('Exiting on previous error')
            logging.shutdown()
            sys.exit(1)
            
        ## Send
        try:
            self.socketOut = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.destAddress = (self.config['mcs']['message_host'], self.config['mcs']['message_out_port'])
            #self.socketIn.setblocking(0)
        except socket.error as err:
            code, e = err
            self.logger.critical('Cannot bind to sending port %i: %s', self.config['mcs']['message_out_port'], str(e))
            self.logger.critical('Exiting on previous error')
            logging.shutdown()
            sys.exit(1)
            
        # Create the incoming socket poller
        self.poller = select.poll()
        self.poller.register(self.socketIn, select.POLLIN | select.POLLPRI)
            
    def stop(self):
        """
        Stop the receive thread, waiting until it's finished.
        """
        
        # Stop the poller
        self.poller.unregister(self.socketIn)
        self.poller = None
        
        # Close the sockets
        self.socketIn.close()
        self.socketOut.close()
        
    def receiveCommand(self):
        """
        Recieve and process MCS command over the network and add it to the packet 
        processing queue.
        """
        
        ngood = 0
        nerr = 0
        for fd,flag in self.poller.poll(1000):
            # Read - we are only listening to one socket
            data, addr = self.socketIn.recvfrom(MCS_RCV_BYTES)
            try:
                data = data.decode('ascii')
            except AttributeError:
                pass
                
            # Process
            try:
                sender, status, command, reference, packed_data = self.processCommand(data)
            except Exception as e:
                nerr += 1
                self.logger.error("processCommand failed with: %s", str(e))
                continue
                
            # Respond
            try:
                self.sendResponse(sender, status, command, reference, packed_data)
            except Exception as e:
                nerr += 1
                self.logger.error("sendResponse failed with: %s", str(e))
                continue
                
            # Increment
            ngood += 1
            
        return ngood, nerr
                
    def sendResponse(self, destination, status, command, reference, data):
        """
        Send a response to MCS via UDP.
        """
        
        if status:
            response = 'A'
        else:
            response = 'R'
            
        # Set the sender
        sender = self.SubSystemInstance.subSystem
        
        # Get current time
        (mjd, mpm) = getTime()
        
        # Get the current system status
        systemStatus = self.SubSystemInstance.currentState['status']
        
        # Build the payload
        payload = "%3s%3s%3s%9i" % (destination, sender, command, reference)
        payload += "%4i%6i%9i" % (len(data)+8, mjd, mpm)
        payload += ' ' + response + ("%7s" % systemStatus) + data
        try:
            payload = bytes(payload, 'ascii')
        except TypeError:
            pass
            
        bytes_sent = self.socketOut.sendto(payload, self.destAddress)
        self.logger.debug("mcsSend - Sent to MCS '%s'", payload)
        return True
        
    def parsePacket(self, data):
        """
        Given a MCS UDP command packet, break it into its various parts and return
        them as an eight-element tuple.  The parts are:
          1. Destination
          2. Sender
          3. Command
          4. Reference number
          5. Data section length
          6. MJD
          7. MPM
          8. Data section
        """
        
        destination = data[:3]
        sender      = data[3:6]
        command     = data[6:9]
        reference   = int(data[9:18])
        datalen     = int(data[18:22]) 
        mjd         = int(data[22:28]) 
        mpm         = int(data[28:37]) 
        data        = data[38:38+datalen]
        
        return destination, sender, command, reference, datalen, mjd, mpm, data
        
    def processCommand(self, data):
        """
        Interperate the data of a UDP packet as a DP MCS command.
        
        Returns a five-elements tuple of:
          * sender
          * status of the command (True=accepted, False=rejected)
          * command anme
          * reference number
          * packed response
          
        .. note:
            This function should be replaced by the particulars for
            the subsystem being controlled.
        """
        
        destination, sender, command, reference, datalen, mjd, mpm, data = self.parsePacket(data)
        
        sender = 'MCS'
        status = True
        command = 'PNG'
        reference = 1
        packed_data = ''
        
        # Return status, command, reference, and the result
        return sender, status, command, reference, packed_data
