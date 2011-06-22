"""
Interface to LWA MCS subsystem.
"""

# $Id: mcs.py 63 2010-03-15 15:10:04Z dwood $



import logging
import subprocess



__revision__ = "$Revision: 63 $"
__version__ = '0.1.0'




class Mcs(object):
  """
  Interface to MCS subsystem.
  """
  
  
  # logging output for interface
    
  log = logging.getLogger('MCS')
  
  
  def __init__(self):
    """
    Create an interface instance to MCS.
    """
    
    # a local cache for subsystem MIB values
    
    self.mib_cache = {}

  
  def ms_mdre(self, subsystem, label): 
    """
    Run the ms_mdre application.
    Param: subsystem  - The LWA subsystem to query.
    Param: label      - The MIB label name to query.
    Returns: A tuple (status, output) where 'status' is the ms_mdre process
             return code and 'output' is the ms_mdre text output.
    """
    
    cmdLine = ['ms_mdre', subsystem, label]
    self.log.debug("running %s", cmdLine) 
    proc = subprocess.Popen(cmdLine, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdoutdata, stderrdata) = proc.communicate()
    if proc.returncode != 0:
      self.log.error("ms_mdre failed with status %d: %s", proc.returncode, stdoutdata)
    else:
      self.log.debug("ms_mdr ran successfully: %s", stdoutdata)
    return (proc.returncode, stdoutdata)
    
    
  def ms_mdr(self, subsystem):
    """
    Run the ms_mdr application.
    Param: subsystem - The LWA subsystem to query.
    Returns: A tuple (status, output) where 'status' is the ms_mdr process
             return code and 'output' is the ms_mdr text output.
    """
    
    cmdLine = ['ms_mdr', subsystem]
    self.log.debug("running %s", cmdLine)
    proc = subprocess.Popen(cmdLine, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdoutdata, stderrdata) = proc.communicate()
    if proc.returncode != 0:
      self.log.error("ms_mdr failed with status %d: %s", proc.returncode, stdoutdata)
    else:
      self.log.debug("ms_mdr ran successfully")
    return (proc.returncode, stdoutdata)
    
    
  def msei(self, subsystem, command, data):
    """
    Run the msei application.
    Param: subsystem  - The LWA subsystem to command.
    Param: command    - The command type.
    Param: data       - Command specific data
    Returns: The msei process return code.
    """
    
    cmdLine = ['msei', subsystem, command, data]
    self.log.debug("running %s", cmdLine)
    proc = subprocess.Popen(cmdLine, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdoutdata, stderrdata) = proc.communicate()
    if proc.returncode != 0:
      self.log.error("msei failed with status %d: %s", proc.returncode, stdoutdata)
    else:
      self.log.debug("msei ran successfully: %s", stdoutdata)
    return proc.returncode
    

  def query_mib(self, subsystem, label, method = 'ms_mdre'):
    """
    Query the MCS for an MIB value by label.
    Param: subsystem  - The LWA subsystem to query.
    Param: label      - The MIB label name to query.
    Param: method     - The method of querying the MIB:
                          ms_mdre - run the mdre application for each label
                          cache   - lookup the label in the local cache
                                    populated with the update_mib_cache() 
                                    method
    Returns: The MIB data value as a string, or None on error.
    """
    
    if method == 'ms_mdre':
    
      # run ms_mdre to lookup a single MIB entry
    
      (status, output) = self.ms_mdre(subsystem, label)
      if status != 0:
        return None
    
      # parse ms_mdre output
    
      return output.split('\n')[0].strip()
      
    elif method == 'cache':
    
      # find the MIB cache for subsystem
      # do an initial update of the subsystem cache if not present
      
      try:
        ssCache = self.mib_cache[subsystem]
      except KeyError:
        status = self.update_mib_cache(subsystem)
        if status != 0:
          return None
        ssCache = self.mib_cache[subsystem]
        
      # try to find label in MIB cache for subsystem
      
      try:
        value = ssCache[label]
      except KeyError:
        self.log.error("label %s not found in %s subsystem MIB cache",
          label, subsystem)
        return None
        
      return value
      
    else:
    
      raise ValueError, "unknown method %s" % method
      
      
  def update_mib_cache(self, subsystem, method = 'ms_mdr'):
    """
    Update the local MIB cache for a subsystem.
    Param: subsystem  - The LWA subsystem to query.
    Param: method     - The method of updating the cache.
                          ms_mdr - run the ms_mdr
    Returns: 0 if successful; non-zero otherwise.
    """
    
    if method == 'ms_mdr':
    
      # run ms_mdr to get all MIB values for a subsystem
      
      (status, output) = self.ms_mdr(subsystem)
      if status != 0:
        return status
        
      # create a subsystem entry in the cache if it does not exist
      
      try:
        ssCache = self.mib_cache[subsystem]
      except KeyError:
        self.log.debug("creating MIB cache entry for subsystem %s", subsystem)
        ssCache = {}
        self.mib_cache[subsystem] = ssCache
        
      # parse ms_mdr output and save label:value pair in subsystem cache
      
      for line in output.splitlines():
        line = line.split()
        if len(line) > 2:
          ssCache[line[0].strip()] = line[3].strip()
        
    else:
    
      raise ValueError, "unknown method %s" % method
      
    return 0
    

  def send_command(self, subsystem, command, data, method = 'msei'):
    """
    Send an MCS command to an LWA subsystem.
    Param: subsystem  - The LWA subsystem to command.
    Param: command    - The command type.
    Param: method     - The method of sending the command:
                          msei - run the msei application
    Returns: 0 if successful; non-zero otherwise.
    """
    
    if method == 'msei':
    
      # run msei to send command
    
      return self.msei(subsystem, command, data)
      
    else:
    
      raise ValueError, "unknown method %s" % method
    


