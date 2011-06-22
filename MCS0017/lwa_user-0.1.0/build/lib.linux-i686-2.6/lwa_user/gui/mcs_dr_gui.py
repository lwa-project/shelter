"""
GUI window definitions for MCS-DR subsystem.
"""

# $Id: mcs_dr_gui.py 52 2010-03-10 16:16:01Z dwood $


import Tix


__revision__ = "$Revision: 52 $"
__version__ = '0.1.0'


class McsDrWindow(Tix.Toplevel):
  """
  MCS-DR subsystem window.
  """
  
  def __init__(self, mcs, config):
    """
    Create MCS-DR window.
    """
    
    Tix.Toplevel.__init__(self)
    self.mcs = mcs
    self.title('MCS-DR')
    self.resizable(False, False)
