"""
GUI window definitions for ASP subsystem.
"""

# $Id: asp_gui.py 70 2010-03-16 19:57:02Z dwood $


import functools

import Tix
import tkMessageBox

from lwa_user.gui.common_gui import PowerWidget
from lwa_user.gui.common_gui import TabWidget
from lwa_user.gui.common_gui import TabWidget2
from lwa_user.gui.common_gui import SpinWidget
from lwa_user.gui.common_gui import McsReservedWidget



__revision__  = "$Revision: 70 $"
__version__   = "dev"
__author__    = "D.L.Wood"



class AspWindow(Tix.Toplevel):
  """
  ASP subsystem window.
  """
  
  def __init__(self, mcs, config):
    """
    Create ASP window.
    """
    
    # create window
    
    Tix.Toplevel.__init__(self)
    self.title('ASP Subsystem')
    self.resizable(False, False)
    
    # register window delete protocol handler
    
    self.protocol('WM_DELETE_WINDOW', self.delete_window)
    
    # save parameters
    
    self.mcs = mcs
    self.config = config
    self.num_arx = self.config.getint('ASP', 'arx_number_boards')
    
    # get ASP configuration values from MIB
    
    self.mcs.update_mib_cache('ASP')
    
    # setup update state machine
    
    period = config.getint('APP', 'update_period')
    self.update_period = (period * 1000) / 2
    self.update_state = 1
    
    # setup a list for holding ASP MIB items to report
    
    self.mib_report_labels = []
    
    # setup a slot for the power-temperature child window
    
    self.power_temp_window = None
    
    self.mib_report_labels.append('SUBSYSTEM')
    self.mib_report_labels.append('SERIALNO')
    self.mib_report_labels.append('VERSION')
    self.mib_report_labels.append('SUMMARY')
    self.mib_report_labels.append('INFO')
    self.mib_report_labels.append('LASTLOG')
    
    self.mib_report_labels.append('ARXCURR')
    self.mib_report_labels.append('FEECURR')
    self.mib_report_labels.append('ARXPWRUNIT_1')
    self.mib_report_labels.append('FEEPWRUNIT_1')
    self.mib_report_labels.append('TEMP-STATUS')
    
    numSensors = int(self.mcs.query_mib('ASP', 'TEMP-SENSE-NO', 'cache'), 10)
    for n in range(1, numSensors):
      self.mib_report_labels.append('SENSOR-DATA-%d' % n)
    
    # create ASP global buttons
    
    frame = Tix.Frame(self, padx = 0, pady = 0)
    frame.pack(fill = Tix.X, side = Tix.LEFT)
    
    button = Tix.Button(frame, text = 'Initialize', command = self.initialize_asp)
    button.pack(fill = Tix.X)
    
    button = Tix.Button(frame, text = 'Shutdown', command = self.shutdown_asp)
    button.pack(fill = Tix.X)
    
    button = Tix.Button(frame, text = 'Power-Temperature', command = self.open_power_temp)
    button.pack(fill = Tix.X)
    
    # create ARX board window buttons
    
    self.arx_buttons = [None]
    
    frame1 = Tix.LabelFrame(frame, label = 'ARX Boards', padx = 0, pady = 0)
    frame1.pack(side = Tix.BOTTOM)
    for m in range(2):
      frame2 = Tix.Frame(frame1.frame, padx = 0, pady = 0)
      frame2.pack(side = Tix.LEFT, fill = Tix.Y, expand = True)
      for n in range(1, 18):
        board = (m * 17) + n
        if board > 33:
          break
        if board > self.num_arx:
          state = Tix.DISABLED
        else:
          state = Tix.NORMAL
        hanlder = functools.partial(self.open_arx, board = board)
        button = Tix.Button(frame2, text = "ARX %d" % board, command = hanlder,
          state = state)
        button.pack(fill = Tix.X)
        if state == Tix.NORMAL:
          self.arx_buttons.append(button)
          
    # create ARX board window notebook
    
    frame = Tix.ScrolledWindow(self, scrollbar = "auto -y")
    frame.window.config(padx = 0, pady = 0)
    frame.pack(fill = Tix.BOTH, side = Tix.RIGHT)
    
    self.arx_notebook = Tix.NoteBook(frame.window, ipadx = 0, ipady = 0)
    self.arx_notebook.pack(fill = Tix.BOTH)
        
    # schedule first update unless update_period = 0, which disables updates
    
    if self.update_period > 0:
      self.after(0, self.update_status)
      
  
  def delete_window(self):
    """
    Handle the window deletion action for the ASP main window.
    Prevents the window from being closed if the power-temperature 
    window is still open.
    """
    
    if self.power_temp_window is None:
      self.destroy()
    else:
      tkMessageBox.showerror("Window Close Error", 
        "ASP child windows open; not closing", parent = self)
    
 
  def initialize_asp(self):
    """
    Send ASP initialization (INI) command.
    """
    
    self.mcs.send_command('ASP', 'INI', "%02d" % self.num_arx)
 
  
  def shutdown_asp(self):
    """
    Send ASP shutdown (SHT) command.
    """
    
    self.mcs.send_command('ASP', 'SHT', '')
    
    
  def open_power_temp(self):
    """
    Create or raise ASP power-temperature window.
    """
    
    if self.power_temp_window is None:
      self.power_temp_window = AspPowerTempWindow(self.mcs)
      self.power_temp_window.bind('<Destroy>', self.close_power_temp)
    else:
      self.power_temp_window.lift()
      
      
  def close_power_temp(self, event):
    """
    Notification for ASP power-temperature window closing.
    """
    
    self.power_temp_window = None
    
      
  def open_arx(self, board):
    """
    Create or delete an ARX board window as an ASP notebook page.
    """
    
    # get page widget name
    
    name = 'arx%d' % board
    
    if not hasattr(self.arx_notebook, name):
    
      # create new notebook page
    
      self.arx_notebook.add(name, label = 'ARX %d' % board)
      frame = getattr(self.arx_notebook, name)
      frame.config(padx = 0, pady = 0)
      window = ArxBoardWindow(frame, self.mcs, board)
      window.pack(fill = Tix.BOTH)
      self.arx_notebook.raise_page(name)
      
      # mark button
      
      self.arx_buttons[board].config(foreground = 'blue')
      
    else:
    
      # delete notebook page
    
      self.arx_notebook.delete(name)
      
      # mark button
      
      self.arx_buttons[board].config(foreground = 'black')
    
    
  def update_status(self):
    """
    Update window status displays.
    """
    
    # first state issues ASP RPT commands to MCS
    
    if self.update_state == 1:
    
      for label in self.mib_report_labels:
        self.mcs.send_command('ASP', 'RPT', label)
    
      self.update_state = 2
      
    # second state queries MIB for ASP values and updates windows
      
    elif self.update_state == 2:
    
      self.mcs.update_mib_cache('ASP')
    
      if self.power_temp_window is not None:
        self.power_temp_window.update_status()
        
      self.update_state = 1
    
    # re-shedule this method
    
    self.after(self.update_period, self.update_status)
    
    
    
class AspPowerTempWindow(Tix.Toplevel):
  """
  ASP power supply/temperature control and status window.
  """
  
  def __init__(self, mcs):
    """
    Create ASP power-temperature window.
    """
    
    # create window
    
    Tix.Toplevel.__init__(self)
    self.title("ASP Power-Temperature")
    self.resizable(False, False)
    
    # save parameters
    
    self.mcs = mcs
    self.num_sensor = int(self.mcs.query_mib('ASP', 'TEMP-SENSE-NO', 'cache'), 10)
    
    # create ASP MCS Reserved display tabs
    
    self.mcs_reserved_widget = McsReservedWidget(self, mcs, 'ASP',
      nameWidth = 10)
    self.mcs_reserved_widget.pack(fill = Tix.X)
    
    # create power supply controls
    
    frame = Tix.Frame(self)
    frame.pack(fill = Tix.X)
    
    self.fee_power_widget = PowerWidget(frame, 'FEE Power Supply', self.fee_power_on,
      self.fee_power_off)
    self.fee_power_widget.pack(side = Tix.LEFT, fill = Tix.X, expand = True)
    
    self.arx_power_widget = PowerWidget(frame, 'ARX Power Supply', self.arx_power_on,
      self.arx_power_off)
    self.arx_power_widget.pack(side = Tix.RIGHT, fill = Tix.X, expand = True)
    
    # create power supply displays
    
    frame = Tix.LabelFrame(self, label = 'Power Supplies', padx = 0, pady = 0)
    frame.pack(fill = Tix.X)
    
    self.arx_supply_tab = TabWidget2(frame.frame, 'ARX', nameWidth = 6)
    self.arx_supply_tab.pack(fill = Tix.X)
    
    self.fee_supply_tab = TabWidget2(frame.frame, 'FEE', nameWidth = 6)
    self.fee_supply_tab.pack(fill = Tix.X)
    
    # create temperature displays
    
    self.temp_sensor_tabs = [None]
    
    frame = Tix.LabelFrame(self, label = 'Temperatures', padx = 0, pady = 0)
    frame.pack(fill = Tix.X)
    
    self.temp_status_tab = TabWidget(frame.frame, 'Status', nameWidth = 7)
    self.temp_status_tab.pack(fill = Tix.X)
    
    for n in range(1, self.num_sensor + 1):
      sensorName = self.mcs.query_mib('ASP', 'SENSOR-NAME-%d' % n, 'cache')
      tab = TabWidget(frame.frame, sensorName, nameWidth = 8)
      tab.pack(fill = Tix.X)
      self.temp_sensor_tabs.append(tab)
      
      
  def fee_power_on(self):
    """
    Power on FEE power supply.
    """
    
    self.mcs.send_command('ASP', 'FEP', '11')
    self.fee_power_widget.status_on()
    
    
  def fee_power_off(self):
    """
    Power off FEE power supply.
    """
    
    self.mcs.send_command('ASP', 'FEP', '00')
    self.fee_power_widget.status_off()
    
  
  def arx_power_on(self):
    """
    Power on ARX power supply.
    """
    
    self.mcs.send_command('ASP', 'RXP', '11')
    self.arx_power_widget.status_on()
    
    
  def arx_power_off(self):
    """
    Power off ARX power supply.
    """
    
    self.mcs.send_command('ASP', 'RXP', '00')
    self.arx_power_widget.status_off()
  
  
  def update_status(self):
    """
    Update window status displays.
    """
    
    # update MCS reserved status
    
    self.mcs_reserved_widget.update_status()
    
    # update power supply status
    
    psStatus = self.mcs.query_mib('ASP', 'ARXPWRUNIT_1', 'cache')
    curValue = self.mcs.query_mib('ASP', 'ARXCURR', 'cache')
    self.arx_supply_tab.set_status_1(psStatus)
    self.arx_supply_tab.set_status_2("%s mA" % curValue.lstrip('0'))
    
    psStatus = self.mcs.query_mib('ASP', 'FEEPWRUNIT_1', 'cache')
    curValue = self.mcs.query_mib('ASP', 'FEECURR', 'cache')
    self.fee_supply_tab.set_status_1(psStatus)
    self.fee_supply_tab.set_status_2("%s mA" % curValue.lstrip('0'))
    
    # update temperature status
    
    tempStatus = self.mcs.query_mib('ASP', 'TEMP-STATUS', 'cache')
    self.temp_status_tab.set_status(tempStatus)
    if (tempStatus == 'OVER_TEMP') or (tempStatus == 'UNDER_TEMP'):
      color = 'red'
    else:
      color = 'green'
    self.temp_status_tab.set_color(color)
    
    # update temperature sensor values
    
    for n in range(1, self.num_sensor + 1):
      tempValue = self.mcs.query_mib('ASP', 'SENSOR-DATA-%d' % n, 'cache')
      self.temp_sensor_tabs[n].set_status("%s C" % tempValue.lstrip('0'))
      
    
    
class ArxBoardWindow(Tix.Frame):
  """
  ARX board control and status window.
  """
  
  def __init__(self, parent, mcs, board):
    """
    Create ARX window.
    """
    
    # create window
    
    Tix.Frame.__init__(self, parent, padx = 0, pady = 0)
    
    # save parameters
    
    self.mcs = mcs
    self.board = board
    
    # create ARX channel widgets 
      
    self.channel_widgets = [None]
      
    for channel in range(1, 9):
      widget = ArxChannelWidget(self, mcs, board, channel)
      widget.pack(side = Tix.LEFT)
      self.channel_widgets.append(widget)
    
    

class ArxChannelWidget(Tix.LabelFrame):
  """
  Collection of widgets for one ARX board channel.
  """
  
  def __init__(self, parent, mcs, board, channel):
    """
    Create ARX channel widget.
    """
    
    # create widget frame
    
    stand = ((board - 1) * 8) + channel
    Tix.LabelFrame.__init__(self, parent, label = "Channel %d (%d)" % (channel, stand),
      padx = 0, pady = 0)
    
    # save parameters
    
    self.mcs = mcs
    self.stand = stand
    self.board = board
    self.channel = channel
    
    # create FEE power widgets
    
    self.fee_power_widgets = [None]
    
    onHandler = functools.partial(self.power_on_fee, stand = stand, pol = 1)
    offHandler = functools.partial(self.power_off_fee, stand = stand, pol = 1)
    power = PowerWidget(self.frame, 'FEE Pol 1 Power', onHandler, offHandler)
    power.pack(side = Tix.TOP)
    self.fee_power_widgets.append(power)
    
    onHandler = functools.partial(self.power_on_fee, stand = stand, pol = 2)
    offHandler = functools.partial(self.power_off_fee, stand = stand, pol = 2)
    power = PowerWidget(self.frame, 'FEE Pol 2 Power', onHandler, offHandler)
    power.pack(side = Tix.TOP)
    self.fee_power_widgets.append(power)
    
    # create filter bandwidth widget
    
    self.filter_bw = ArxFilterBandwidthWidget(self.frame, self.mcs, stand)
    self.filter_bw.pack(fill = Tix.X)
    
    # create filter attenuation widgets
    
    handler = functools.partial(self.set_attenuation, name = 'AT1', stand = stand)
    self.filter_at1 = SpinWidget(self.frame, 'AT1', handler, from_ = 0, to = 30,
      increment = 2, nameWidth = 5)
    self.filter_at1.pack(fill = Tix.X)
    
    handler = functools.partial(self.set_attenuation, name = 'AT2', stand = stand)
    self.filter_at2 = SpinWidget(self.frame, 'AT2', handler, from_ = 0, to = 30,
      increment = 2, nameWidth = 5)
    self.filter_at2.pack(fill = Tix.X)
    
    handler = functools.partial(self.set_attenuation, name = 'ATS', stand = stand)
    self.filter_ats = SpinWidget(self.frame, 'ATS', handler, from_ = 0, to = 30,
      increment = 2, nameWidth = 5)
    self.filter_ats.pack(fill = Tix.X)
    
    self.filter_at1.enable()
    self.filter_at2.enable()
    self.filter_ats.enable()
    
    
  def power_on_fee(self, stand, pol):
    """
    Command FEE power on.
    """
    
    self.mcs.send_command('ASP', 'FPW', '%03d%d11' % (self.stand, pol))
    self.fee_power_widgets[pol].status_on()
 
 
  def power_off_fee(self, stand, pol):
    """
    Command FEE power off.
    """
    
    self.mcs.send_command('ASP', 'FPW', '%03d%d00' % (self.stand, pol))
    self.fee_power_widgets[pol].status_off()
    
    
  def set_attenuation(self, value, name, stand):
    """
    Command ARX channel filter attenuation.
    """
    
    # find corresponding spinbox widget and attenuation value
    
    widget = getattr(self, 'filter_%s' % name.lower())
    value = int(value)
    
    # send command
    
    self.mcs.send_command('ASP', name, '%03d%02d' % (stand, value / 2))
    widget.set_status('%s dB' % value)
    


class ArxFilterBandwidthWidget(Tix.LabelFrame):
  """
  ARX filter bandwidth control and status.
  """
  
  def __init__(self, parent, mcs, stand):
    """
    Create filter bandwidth widget.
    """
    
    # create widget frame
    
    Tix.LabelFrame.__init__(self, parent, label = 'Filter Bandwidth', 
      padx = 0, pady = 0)
    
    # save parameters
    
    self.mcs = mcs
    self.stand = stand
    
    # create command buttons
    
    self.full_button = Tix.Button(self.frame, text = 'Full BW', 
      command = self.filter_full)
    self.full_button.pack(fill = Tix.X)
    
    self.reduced_button = Tix.Button(self.frame, text = 'Reduced BW', 
      command = self.filter_reduced)
    self.reduced_button.pack(fill = Tix.X)
    
    self.split_button = Tix.Button(self.frame, text = 'Split BW', 
      command = self.filter_split)
    self.split_button.pack(fill = Tix.X)
    
    self.off_button = Tix.Button(self.frame, text = 'Filter Off',
      command = self.filter_off)
    self.off_button.pack(fill = Tix.X)
    
    # create status indicator
    
    self.status_label = Tix.Label(self.frame, text = 'OFF', foreground = 'blue')
    self.status_label.pack(fill = Tix.X)
    
    
  def filter_full(self):
    """
    Set channel ARX filter to full bandwidth configuration'
    """
    
    self.mcs.send_command('ASP', 'FIL', '%03d01' % self.stand)
    self.status_label.config(text = 'FULL')
    
    
  def filter_reduced(self):
    """
    Set channel ARX filter to reduced bandwidth configuration.
    """
    
    self.mcs.send_command('ASP', 'FIL', '%03d02' % self.stand)
    self.status_label.config(text = 'REDUCED')
    
    
  def filter_split(self):
    """
    Set channel ARX filter to split bandwidth configuration.
    """
    
    self.mcs.send_command('ASP', 'FIL', '%03d00' % self.stand)
    self.status_label.config(text = 'SPLIT')
 
  
  def filter_off(self):
    """
    Set channel ARX filter signal chain power off.
    """
    
    self.mcs.send_command('ASP', 'FIL', '%03d03' % self.stand)
    self.status_label.config(text = 'OFF')
 

    
    
    
