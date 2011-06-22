#!/usr/bin/env python
"""
GUI interface application for LWA.
"""

# $Id: lwa_gui.py 64 2010-03-15 15:10:41Z dwood $


import sys
import os
import time
import logging
import ConfigParser

import Tix
import tkMessageBox

from lwa_user.mcs import Mcs

from lwa_user.gui.asp_gui     import AspWindow
from lwa_user.gui.shl_gui     import ShlWindow
from lwa_user.gui.dp_gui      import DpWindow
from lwa_user.gui.mcs_dr_gui  import McsDrWindow



__revision__  = "$Revision: 64 $"
__version__   = "dev"
__author__    = "D.L.Wood"


class LwaGui(object):
  """
  Application main window.
  """

  def __init__(self, root, options):
    
    # save reference to main window and application options
    
    root.title('LWA GUI')
    root.resizable(False, False)
    self.root = root
    self.options = options
    self.cursor = root.cget('cursor')
    
    # setup application log
    
    if options.verbose:
      level = logging.DEBUG
    else:
      level = logging.INFO
    
    log = logging.getLogger()
    log.setLevel(level)
    formatter = FormatterGMT("%(asctime)s %(levelname)s %(name)s: %(message)s")
    
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)
    
    if options.log_file is not None:
      handler = logging.FileHandler(options.log_file)
      handler.setFormatter(formatter)
      log.addHandler(handler)    
    
    self.log = logging.getLogger('APP')
    self.log.info("%s, version %s", os.path.basename(sys.argv[0]), __version__)
    
    # parse the application configuration file
    
    self.config = ConfigParser.SafeConfigParser()
    self.config.read(options.config_file)
      
    self.log.debug("ASP config: %s", self.config.items('ASP'))
    self.log.debug("SHL config: %s", self.config.items('SHL'))
    self.log.debug("MCS config: %s", self.config.items('MCS'))
    self.log.debug("APP config: %s", self.config.items('APP'))
    
    # change working directory to MCS tools
    
    os.chdir(self.config.get('MCS', 'mcs_directory'))
    
    # create interface to MCS tools
    
    self.mcs = Mcs()
    
    # subsystem child window references
    
    self.asp_window = None
    self.shl_window = None
    self.dp_window = None
    self.mcs_dr_window = None
    
    # create main window subsystem buttons
    
    frame = Tix.LabelFrame(self.root, label = 'Subsystem')
    frame.pack(fill = Tix.X)
    
    button = Tix.Button(frame.frame, text = 'ASP', command = self.open_asp_1, width = 20)
    button.pack(fill = Tix.X)
    
    button = Tix.Button(frame.frame, text = 'SHL', command = self.open_shl_1, width = 20)
    button.pack(fill = Tix.X)
    
    button = Tix.Button(frame.frame, text = 'DP', command = self.open_dp, width = 20)
    button.pack(fill = Tix.X)
    
    button = Tix.Button(frame.frame, text = 'MCS-DR', command = self.open_mcs_dr, width = 20)
    button.pack(fill = Tix.X)
    
  
  def open_asp_1(self):
    """
    Create or raise ASP subsystem window.
    """
    
    if self.asp_window is None:
    
      # make sure number of ARX boards is available
    
      try:
        numBoards = self.config.getint('ASP', 'arx_number_boards')
      except ValueError:
        tkMessageBox.showerror("ASP Configuration Error",
          "config item [ASP]:arx_number_boards improper value \'%s\'" % \
          self.config.get('ASP', 'arx_number_boards'))
        return
    
      # prompt user for ASP INI command
      
      answer = tkMessageBox.askyesno('ASP Initialization', 
        'Run ASP INI command?', parent = self.root)
      if answer:
        self.mcs.send_command('ASP', 'INI', "%02d" % numBoards)
        delay = 1000
      else:
        delay = 0
        
      # schedule step 2 of window creation
      
      self.root.config(cursor = 'watch')
      self.root.after(delay, self.open_asp_2)
    
    else:
      
      self.asp_window.lift()
      

  def open_asp_2(self): 
    """
    Step 2 of ASP window creation.
    """
    
    # have ASP report minimum MIB entries for window definition
    
    self.mcs.send_command('ASP', 'RPT', 'TEMP-SENSE-NO')
    
    # schedule step 3 of window creation
    
    self.root.after(1000, self.open_asp_3)
    
    
  def open_asp_3(self):
    """
    Step 3 of ASP window creation.
    """
      
    # have ASP report minimum MIB entries for window definition
    
    try:
      numSensors = int(self.mcs.query_mib('ASP', 'TEMP-SENSE-NO'), 10)
    except ValueError:
      tkMessageBox.showerror("ASP MIB Error",
        "MIB item ASP/TEMP-SENSE-NO improper value \'%s\'" % \
        self.mcs.query_mib('ASP', 'TEMP-SENSE-NO'))
      self.root.config(cursor = self.cursor)
      return
        
    for n in range(1, numSensors):
      self.mcs.send_command('ASP', 'RPT', 'SENSOR-NAME-%d' % n)
      
    # schedule step 4 of window creation
    
    self.root.after(1000, self.open_asp_4)
    
      
  def open_asp_4(self):
    """
    Step 4 of ASP window creation.
    """
    
    self.asp_window = AspWindow(self.mcs, self.config)
    self.asp_window.bind('<Destroy>', self.close_asp)
    self.root.config(cursor = self.cursor)
      
      
  def close_asp(self, event):
    """
    Notification for ASP window closing.
    """
    
    self.asp_window = None
    
    
  def open_shl_1(self):
    """
    Create or raise SHL subsystem window.
    """
    
    if self.shl_window is None:
    
      # make sure number of power racks config item is available
    
      try:
        numRacks = self.config.getint('SHL', 'power_number_racks')
      except ValueError:
        tkMessageBox.showerror("SHL Configuration Error",
          "config item [SHL]:power_number_racks improper value \'%s\'" % \
          self.config.get('SHL', 'power_number_racks'))
        return
    
      # prompt user for SHL INI command
      
      answer = tkMessageBox.askyesno('SHL Initialization', 
        'Run SHL INI command?', parent = self.root)
        
      if answer:
      
        # get initial thermostat set point
      
        try:
          tempSetPoint = self.config.getfloat('SHL', 'thermostat_set_point')
        except ValueError:
          tkMessageBox.showerror("SHL Configuration Error",
            "config item [SHL]:thermostat_set_point improper value \'%s\'" % \
            self.config.get('SHL', 'thermostat_set_point'))
          return
            
        tempSetPoint = "%0.1f" % tempSetPoint
        
        # get initial differential set point
        
        try:
          diffSetPoint = self.config.getfloat('SHL', 'differential_set_point')
        except ValueError:
          tkMessageBox.showerror("SHL Configuration Error",
            "config item [SHL]:differential_set_point improper value \'%s\'" % \
            self.config.get('SHL', 'differential_set_point'))
          return
        
        diffSetPoint = "%0.1f" % diffSetPoint
        
        # format SHL INI command parameter string
        
        paramStr = "%s&%s&" % (tempSetPoint.zfill(5), diffSetPoint.zfill(3))
        for n in range(6):
          if n < numRacks:
            paramStr += '1'
          else:
            paramStr += '0'
            
        # send command
            
        self.mcs.send_command('SHL', 'INI', "%s" % paramStr)
        delay = 1000
      
      else:
        
        delay = 0
        
      # schedule step 2 of window creation
      
      self.root.config(cursor = 'watch')
      self.root.after(delay, self.open_shl_2)
    
    else:
      
      self.shl_window.lift()
      
      
  def open_shl_2(self):
    """
    Step 2 of SHL window creation.
    """
    
    # have SHL report minimum MIB entries for window definition
    
    for n in range(1, 6):
      self.mcs.send_command('SHL', 'RPT', 'PORT-STATUS-R%d' % n)
    
    # schedule step 3 of window creation
    
    self.root.after(1000, self.open_shl_3) 
    
      
  def open_shl_3(self):
    """
    Step 3 of SHL window creation.
    """
    
    self.shl_window = ShlWindow(self.mcs, self.config)
    self.shl_window.bind('<Destroy>', self.close_shl)
    self.root.config(cursor = self.cursor)
    

  def close_shl(self, event):
    """
    Notification for SHL window closing.
    """
    
    self.shl_window = None
    
    
  def open_dp(self):
    """
    Create or raise DP subsystem window.
    """
    
    if self.dp_window is None:
      self.dp_window = DpWindow(self.mcs, self.config)
      self.dp_window.bind('<Destroy>', self.close_dp)
    else:
      self.dp_window.lift()
      
      
  def close_dp(self, event):
    """
    Notification for DP window closing.
    """
    
    self.dp_window = None
    
    
  def open_mcs_dr(self):
    """
    Create or raise MCS-DR window.
    """
    
    if self.mcs_dr_window is None:
      self.mcs_dr_window = McsDrWindow(self.mcs, self.config)
      self.mcs_dr_window.bind('<Destroy>', self.close_mcs_dr)
    else:
      self.mcs_dr_window.lift()
      
      
  def close_mcs_dr(self, event):
    """
    Notification for MCS-DR window closing.
    """
    
    self.mcs_dr_window = None
    
    
    
class FormatterGMT(logging.Formatter):
  """
  Replacement for logging.Formatter which provides log message
  timstamps in GMT.
  """
    
  def formatTime(self, record, datefmt = None):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        
    
    
if __name__ == '__main__':

  import optparse
  
  # get environment
  
  try:
    configName = os.environ['LWA_GUI_CONFIG']
  except KeyError:
    configName = None
  
  # parse command line
  
  usage = "lwa_gui.py [options]"
  parser = optparse.OptionParser(usage = usage, description = __doc__,
    version = __version__)
  
  parser.add_option("-v", "--verbose", dest="verbose", action="store_true",
    help="enable verbose log message output (default=%default)")
  
  parser.add_option("-c", "--config-file", dest="config_file", action="store",
    help="application configuration file (default=%default)")
    
  parser.add_option("-l", "--log-file", dest="log_file", action="store",
    help="write log messages to file")
  
  parser.set_defaults(verbose = False, config_file = configName)
  (options, args) = parser.parse_args()
  
  if options.config_file is None:
    parser.error("no configuration file specified")
  if not os.path.exists(options.config_file):
    parser.error("configuration file %s does not exist" % options.config_file)
  
  # create a Tk main window
  
  tk = Tix.Tk()
  
  # run the application
  
  app = LwaGui(tk, options)
  try:
    tk.mainloop()
  except KeyboardInterrupt:
    pass
    


