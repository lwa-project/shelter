"""
GUI window definitions for SHL subsystem.
"""

# $Id: shl_gui.py 68 2010-03-16 01:48:55Z dwood $


import functools

import Tix
import tkMessageBox

from lwa_user.gui.common_gui import TabWidget
from lwa_user.gui.common_gui import SpinWidget
from lwa_user.gui.common_gui import PowerWidget
from lwa_user.gui.common_gui import McsReservedWidget


__revision__  = "$Revision: 68 $"
__version__   = "dev"
__author__    = "D.L.Wood"



class ShlWindow(Tix.Toplevel):
  """
  SHL subsystem window.
  """
  
  def __init__(self, mcs, config):
    """
    Create SHL window.
    """
    
    # create window
    
    Tix.Toplevel.__init__(self)
    self.title('SHL Subsystem')
    self.resizable(False, False)

    # save parameters
    
    self.mcs = mcs
    self.config = config
    self.num_rack = self.config.getint('SHL', 'power_number_racks')
    
    # SHL configuration values from MIB
    
    self.mcs.update_mib_cache('SHL')
    
    # setup update state machine
    
    period = config.getint('APP', 'update_period')
    self.update_period = (period * 1000) / 2
    self.update_state = 1
    
    # setup a list for holding SHL MIB items to report
    
    self.mib_report_labels = []
    
    frame = Tix.Frame(self, padx = 0, pady = 0)
    frame.pack(side = Tix.LEFT, fill = Tix.BOTH)
    
    # create power rack controls and displays
    
    frame1 = Tix.Frame(frame, padx = 0, pady = 0)
    frame1.pack(side = Tix.TOP)
    
    frame2 = Tix.Frame(frame1, padx = 0, pady = 0)
    frame2.pack(side = Tix.LEFT)
    
    # create SHL global buttons
    
    frame3 = Tix.Frame(frame2, padx = 0, pady = 0)
    frame3.pack(fill = Tix.X)
    
    button = Tix.Button(frame3, text = 'Initialize', command = self.initialize_shl)
    button.pack(fill = Tix.X)
    
    button = Tix.Button(frame3, text = 'Shutdown', command = self.shutdown_shl)
    button.pack(fill = Tix.X)
    
    # create power rack window buttons

    frame3 = Tix.LabelFrame(frame2, label = 'Power Racks', padx = 0, pady = 0)
    frame3.pack(fill = Tix.Y)
    
    self.rack_buttons = [None]
    
    for rack in range(1, 7):
      if rack > self.num_rack:
        state = Tix.DISABLED
      else:
        state = Tix.NORMAL
      handler = functools.partial(self.open_rack, rack = rack)
      button = Tix.Button(frame3.frame, text = "Rack %d" % rack,
        command = handler, state = state)
      if state == Tix.NORMAL:
        self.rack_buttons.append(button)
      button.pack(fill = Tix.X, side = Tix.TOP)
      
    # create SHL MCS Reserved display tabs
    
    self.mcs_reserved_widget = McsReservedWidget(frame1, mcs, 'SHL')
    self.mcs_reserved_widget.pack(fill = Tix.X)
    
    self.mib_report_labels.append('SUBSYSTEM')
    self.mib_report_labels.append('SERIALNO')
    self.mib_report_labels.append('VERSION')
    self.mib_report_labels.append('SUMMARY')
    self.mib_report_labels.append('INFO')
    self.mib_report_labels.append('LASTLOG')
      
    # create power rack current displays
    
    frame2 = Tix.LabelFrame(frame1, label = 'Currents', padx = 0, pady = 0)
    frame2.pack(fill = Tix.BOTH, side = Tix.RIGHT, expand = True)
    
    self.current_tabs = [None]
    
    for rack in range(1, self.num_rack + 1):
      widget = TabWidget(frame2.frame, 'Rack %d' % rack, nameWidth = 10,
        statusWidth = 20)
      widget.pack(side = Tix.TOP, fill = Tix.X, expand = True)
      self.current_tabs.append(widget)
      self.mib_report_labels.append('CURRENT-R%d' % rack)
      
    # create environmental controls and displays
    
    frame1 = Tix.LabelFrame(frame, label = 'Environmental Control', 
      padx = 0, pady = 0)
    frame1.pack(fill = Tix.X, side = Tix.BOTTOM)
    
    frame2 = Tix.Frame(frame1.frame, padx = 0, pady = 0)
    frame2.pack(fill = Tix.X, side = Tix.TOP)
    
    self.temperature_tab = TabWidget(frame2, 'Temperature')  
    self.temperature_tab.pack(side = Tix.TOP, fill = Tix.X)
    self.mib_report_labels.append('TEMPERATURE') 
    
    frame2 = Tix.Frame(frame1.frame, padx = 0, pady = 0)
    frame2.pack(fill = Tix.X, side = Tix.BOTTOM)
    
    self.thermostat_widget = SpinWidget(frame2, 'Thermostat',
      self.set_thermostat, from_ = 60.0, to = 110.0, increment = 0.5)
    self.thermostat_widget.pack(side = Tix.LEFT, fill = Tix.X,
      expand = True)
    self.thermostat_widget.spinbox_variable.set(self.config.getfloat('SHL',
      'thermostat_set_point'))
    
    self.differential_widget = SpinWidget(frame2, 'Differential',
      self.set_differential, from_ = 0.5, to = 5.0, increment = 0.5)
    self.differential_widget.pack(side = Tix.RIGHT, fill = Tix.X,
      expand = True)
    self.differential_widget.spinbox_variable.set(self.config.getfloat('SHL',
      'differential_set_point'))
      
    self.thermostat_widget.enable()
    self.differential_widget.enable()
      
    # create power rack window notebook
    
    frame = Tix.Frame(self, padx = 0, pady = 0)
    frame.pack(fill = Tix.BOTH, expand = True, side = Tix.RIGHT)
    
    self.rack_notebook = Tix.NoteBook(frame, ipadx = 0, ipady = 0)
    self.rack_notebook.pack(fill = Tix.BOTH, expand = True)
      
    # schedule firs update unless update_period = 0, which disables updates
    
    if self.update_period > 0:
      self.after(0, self.update_status)
    
      
  def initialize_shl(self):
    """
    Send SHL initialization (INI) command.
    """
    
    # get parameter values from config
    
    tempSetPoint = self.config.getfloat('SHL', 'thermostat_set_point')
    tempSetPoint = "%0.1f" % tempSetPoint
    
    diffSetPoint = self.config.getfloat('SHL', 'differential_set_point')
    diffSetPoint = "%0.1f" % diffSetPoint
        
    # format SHL INI command parameter string
        
    paramStr = "%s&%s&" % (tempSetPoint.zfill(5), diffSetPoint.zfill(3))
    for n in range(6):
      if n < self.num_rack:
        paramStr += '1'
      else:
        paramStr += '0'
            
    # send command
            
    self.mcs.send_command('SHL', 'INI', "%s" % paramStr)
 
  
  def shutdown_shl(self):
    """
    Send SHL shutdown (SHT) command.
    """
    
    self.mcs.send_command('SHL', 'SHT', '')
      
      
  def open_rack(self, rack):
    """
    Create or delete a power rack window as a SHL notebook page.
    """
    
    # get page name
    
    name = "rack%d" % rack
    
    if not hasattr(self.rack_notebook, name):
    
      # create new power rack page
      
      self.rack_notebook.add(name, label = "Rack %d" % rack)
      frame = getattr(self.rack_notebook, name)
      window = PowerRackWindow(frame, self.mcs, rack)
      window.pack(fill = Tix.BOTH, expand = True)
      self.rack_notebook.raise_page(name)
      
      # mark button
      
      self.rack_buttons[rack].config(foreground = 'blue')
      
    else:
    
      # delete notebook page
      
      self.rack_notebook.delete(name)
      
      # mark button
      
      self.rack_buttons[rack].config(foreground = 'black')
    

  def set_thermostat(self, value):
    """
    Send command to change SHL thermostat set point.
    """
    
    # get requested value
    
    value = '%0.1f' % float(value)
    
    # send command
    
    self.mcs.send_command('SHL', 'TMP', value.zfill(5))
    self.thermostat_widget.set_status("%s F" % value)
    

  def set_differential(self, value):
    """
    Send command to change SHL thermostat differential set point.
    """
    
    # get requested value
    
    value = '%0.1f' % float(value)
    
    # send command
    
    self.mcs.send_command('SHL', 'DIF', value.zfill(3))
    self.differential_widget.set_status("%s F" % value)
    
    
  def update_status(self):
    """
    Update window status displays.
    """
    
    # first state issues SHL RPT commands to MCS
    
    if self.update_state == 1:
    
      for label in self.mib_report_labels:
        self.mcs.send_command('SHL', 'RPT', label)
        
      self.update_state = 2
        
    # second state queries MIB for SHL values and updates windows
    
    elif self.update_state == 2:
    
      self.mcs.update_mib_cache('SHL')
      
      self.mcs_reserved_widget.update_status()
      
      tempValue = self.mcs.query_mib('SHL', 'TEMPERATURE', 'cache')
      self.temperature_tab.set_status("%s F" % tempValue.lstrip('0'))
      
      for rack in range(1, self.num_rack + 1):
        currValue = self.mcs.query_mib('SHL', 'CURRENT-R%d' % rack, 'cache')
        self.current_tabs[rack].set_status("%s A" % currValue.lstrip('0'))
      
      self.update_state = 1
      
    # re-schedule this method
    
    self.after(self.update_period, self.update_status)



class PowerRackWindow(Tix.Frame):
  """
  SHL power rack control and status window.
  """
  
  def __init__(self, parent, mcs, rack):
    """
    Create power rack window
    """
    
    # query SHL MIB values to get number of ports for this rack
    
    try:
      self.num_port = int(mcs.query_mib('SHL', 'PORTS-AVAILABLE-R%d' % rack,
        'cache'), 10)
    except ValueError:
      tkMessageBox.showerror("SHL MIB Error",
        "SHL MIB item PORTS-AVAILABLE-R%d improper value \'%s\'" % \
        (rack, mcs.query_mib('SHL', 'PORTS-AVAILABLE-R%d' % rack, 'cache')))
      return
    
    # create window
    
    Tix.Frame.__init__(self, parent, padx = 0, pady = 0)
    
    # save parameters
    
    self.mcs = mcs
    self.rack = rack
    
    # create power control widgets
    
    self.power_widgets = [None]
    
    for m in range(5):
      frame = Tix.Frame(self, padx = 0, pady = 0)
      frame.pack(side = Tix.TOP)
      for n in range(1, 11):
        port = (m * 10) + n
        if port <= self.num_port:
          onHandler = functools.partial(self.port_power_on, port = port)
          offHandler = functools.partial(self.port_power_off, port = port)
          widget = PowerWidget(frame, 'Port %d' % port, onHandler, offHandler)
          widget.pack(side = Tix.LEFT, fill = Tix.X)
          self.power_widgets.append(widget)
          
          
  def port_power_on(self, port):
    """
    Send a rack port power on command.
    """
    
    self.mcs.send_command('SHL', 'PWR', '%d%02dON ' % (self.rack, port))
    self.power_widgets[port].status_on()
    
    
  def port_power_off(self, port):
    """
    Send a rack port power off command.
    """
    
    self.mcs.send_command('SHL', 'PWR', '%d%02dOFF' % (self.rack, port))
    self.power_widgets[port].status_off()
    
    

        
        
