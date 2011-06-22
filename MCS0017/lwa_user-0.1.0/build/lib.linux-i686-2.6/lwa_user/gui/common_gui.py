"""
Shared GUI window definitions.
"""

# $Id: common_gui.py 69 2010-03-16 15:12:16Z dwood $


import textwrap

import Tix


__revision__  = "$Revision: 69 $"
__version__ = '0.1.0'
__author__    = "D.L.Wood"



class PowerWidget(Tix.LabelFrame):
  """
  Generic power control and status.
  """
  
  def __init__(self, parent, name, onHandler, offHandler):
    """
    Create widget.
    """
    
    # create widget frame
    
    Tix.LabelFrame.__init__(self, parent, label = name, padx = 0, pady = 0)
    
    # save parameters
    
    self.on_handler = onHandler
    self.off_handler = offHandler
    
    # create power command buttons
    
    frame = Tix.Frame(self.frame, padx = 0, pady = 0)
    frame.pack(side = Tix.TOP, fill = Tix.X)
    
    self.on_button = Tix.Button(frame, text = 'On', command = self.command_on,
      padx = 1, pady = 1)
    self.on_button.pack(side = Tix.LEFT, fill = Tix.X, expand = True)
    
    self.off_button = Tix.Button(frame, text = 'Off', command = self.command_off,
      padx = 1, pady = 1)
    self.off_button.pack(side = Tix.RIGHT, fill = Tix.X, expand = True)
    
    # create power status indicator
    
    self.status_label = Tix.Label(self.frame, text = 'OFF', background = 'red')
    self.status_label.pack(side = Tix.BOTTOM, fill = Tix.X) 
    
    
  def command_on(self):
    """
    Response to On button command.
    """
    
    # call user handler
    
    self.on_handler()
    
    
  def command_off(self):
    """
    Response to Off button command.
    """
    
    # call user handler
    
    self.off_handler()
    
   
  def status_on(self):
    """
    Set status indicator to ON state.
    """
    
    self.status_label.config(text = 'ON', background = 'green')
    
    
  def status_off(self):
  
    """
    Set status indicator to OFF state.
    """
    
    self.status_label.config(text = 'OFF', background = 'red') 
    
    

class TabWidget(Tix.Frame):
  """
  Generic tabular display widget for single value.
  """
  
  def __init__(self, parent, name, nameWidth = 15, statusWidth = 20,
      height = 1):
    """
    Create widget.
    """
    
    # create widget frame
    
    Tix.Frame.__init__(self, parent, padx = 0, pady = 0)
    
    # create entry label
    
    label = Tix.Label(self, text = name, width = nameWidth, anchor = Tix.W)
    label.pack(side = Tix.LEFT, fill = Tix.X, expand = True)
    
    # create value display
    
    self.status_label = Tix.Label(self, width = statusWidth, relief = Tix.SUNKEN,
      foreground = 'blue', height = height)
    if height > 1:
      self.status_label.config(justify = Tix.LEFT, anchor = Tix.W)
    self.status_label.pack(side = Tix.RIGHT, fill = Tix.X, expand = True)
    
    
  def set_status(self, value):
    """
    Set value for status display.
    """
    
    height = self.status_label.cget('height')
    if height > 1:
      width = self.status_label.cget('width')
      value = textwrap.fill(value, width)
    self.status_label.config(text = value)
    
    
  def set_color(self, color):
    """
    Set color of status display background.
    """
    
    self.status_label.config(background = color)
    
    

class TabWidget2(Tix.Frame):
  """
  Generic tabular display widget for two values.
  """
  
  def __init__(self, parent, name, nameWidth = 15, statusWidth = 20):
    """
    Create widget.
    """
    
    # create widget frame
    
    Tix.Frame.__init__(self, parent, padx = 0, pady = 0)
    
    # create entry label
    
    label = Tix.Label(self, text = name, width = nameWidth, anchor = Tix.W)
    label.pack(side = Tix.LEFT, fill = Tix.X, expand = True)
    
    # create value display 1
    
    self.status_label_1 = Tix.Label(self, width = statusWidth, relief = Tix.SUNKEN,
      foreground = 'blue')
    self.status_label_1.pack(side = Tix.LEFT, fill = Tix.X, expand = True)
    
    # create value display 2
    
    self.status_label_2 = Tix.Label(self, width = statusWidth, relief = Tix.SUNKEN,
      foreground = 'blue')
    self.status_label_2.pack(side = Tix.RIGHT, fill = Tix.X, expand = True)
    
  
  def set_status_1(self, value):
    """
    Set value for status display 1.
    """
    
    self.status_label_1.config(text = value)
    
    
  def set_status_2(self, value):
    """
    Set value for status display 2.
    """
    
    self.status_label_2.config(text = value)
    

  def set_color_1(self, color):
    """
    Set background color of status display 1.
    """
    
    self.status_label_1.config(background = color)
    
    
  def set_color_2(self, color):
    """
    Set background color of status display 2.
    """
    
    self.status_label_2.config(background = color)



class SpinWidget(Tix.Frame):
  """
  Generic spinbox widget with attached status display label.
  """
  
  def __init__(self, parent, name, cmdHandler, from_, to, increment,
      nameWidth = 14):
    """
    Create spinbox widget.  The cmdHandler callback is initially
    disabled to prevent a command request when widget is created.
    Call method enable() to enable the command callback.
    """
    
    # create widget frame
    
    Tix.Frame.__init__(self, parent, padx = 0, pady = 0, relief = Tix.GROOVE,
      borderwidth = 1)
    
    # create command spinbox
    
    self.spinbox_variable = Tix.StringVar()
    self.spinbox = Tix.Control(self, label = name, command = cmdHandler, 
      min = from_, max = to, step = increment, variable = self.spinbox_variable, 
      disablecallback = True, padx = 0, pady = 0)
    self.spinbox.label.config(width = nameWidth, padx = 0, pady = 0)
    self.spinbox.incr.config(width = 20, height = 8, padx = 0, pady = 0)
    self.spinbox.decr.config(width = 20, height = 8, padx = 0, pady = 0)
    self.spinbox.pack(fill = Tix.X)
    
    # create status indicator
    
    self.status_label = Tix.Label(self, foreground = 'blue')
    self.status_label.pack(fill = Tix.X)
    
    
  def enable(self):
    """
    Enable the command callback.
    """
    
    self.spinbox.config(disablecallback = False)
    
    
  def set_status(self, value):
    """
    Set spin widget status value.
    """
    
    self.status_label.config(text = value)



class McsReservedWidget(Tix.LabelFrame):
  """
  Definition for status display of a subsystem's MCS Reserved MIB items.
  These items have index values 1.x.
  """
  
  
  def __init__(self, parent, mcs, subsystem, nameWidth = 12, statusWidth = 22):
    """
    Create a new MCS Reserved item display.
    """
    
    # create widget frame
    
    Tix.LabelFrame.__init__(self, parent, label = "%s-MCS" % subsystem,
      padx = 0, pady = 0)
      
    # save parameters
    
    self.mcs = mcs
    self.subsystem = subsystem
    
    # create MIB item displays
    
    self.status_tabs = {}
    
    widget = TabWidget(self.frame, 'SUBSYSTEM', nameWidth = nameWidth,
      statusWidth = statusWidth)
    self.status_tabs['SUBSYSTEM'] = widget
    widget.pack(fill = Tix.X, side = Tix.TOP)
    
    widget = TabWidget(self.frame, 'SERIALNO', nameWidth = nameWidth,
      statusWidth = statusWidth)
    self.status_tabs['SERIALNO'] = widget
    widget.pack(fill = Tix.X, side = Tix.TOP)
    
    widget = TabWidget(self.frame, 'SUMMARY', nameWidth = nameWidth,
      statusWidth = statusWidth)
    self.status_tabs['SUMMARY'] = widget
    widget.pack(fill = Tix.X, side = Tix.TOP)
    
    widget = TabWidget(self.frame, 'VERSION', nameWidth = nameWidth,
      statusWidth = statusWidth, height = 3)
    self.status_tabs['VERSION'] = widget
    widget.pack(fill = Tix.X, side = Tix.TOP)
    
    widget = TabWidget(self.frame, 'INFO', nameWidth = nameWidth,
      statusWidth = statusWidth, height = 3)
    self.status_tabs['INFO'] = widget
    widget.pack(fill = Tix.X, side = Tix.TOP)
    
    widget = TabWidget(self.frame, 'LASTLOG', nameWidth = nameWidth,
      statusWidth = statusWidth, height = 3)
    self.status_tabs['LASTLOG'] = widget
    widget.pack(fill = Tix.X, side = Tix.TOP)
    

  def update_status(self):
    """
    Update window status displays.
    """
    
    # fetch items from subsystem MIB and update display widgets
    
    tab = self.status_tabs['SUBSYSTEM']
    value = self.mcs.query_mib(self.subsystem, 'SUBSYSTEM', 'cache')
    tab.set_status(value)
    
    tab = self.status_tabs['SERIALNO']
    value = self.mcs.query_mib(self.subsystem, 'SERIALNO', 'cache')
    tab.set_status(value)
    
    tab = self.status_tabs['SUMMARY']
    value = self.mcs.query_mib(self.subsystem, 'SUMMARY', 'cache')
    tab.set_status(value)
    
    tab = self.status_tabs['VERSION']
    value = self.mcs.query_mib(self.subsystem, 'VERSION', 'ms_mdre')
    tab.set_status(value)
    
    tab = self.status_tabs['INFO']
    value = self.mcs.query_mib(self.subsystem, 'INFO', 'ms_mdre')
    tab.set_status(value)
    
    tab = self.status_tabs['LASTLOG']
    value = self.mcs.query_mib(self.subsystem, 'LASTLOG', 'ms_mdre')
    tab.set_status(value)
    


    
