"""
Extensions for distutils uninstall command.
"""

# $Id: uninstall.py 8 2010-02-04 17:11:36Z dwood $


import os
import sys
import glob

from distutils.core import Command
from distutils.command.install import install
from distutils.fancy_getopt import longopt_xlate


__revision__ = "$Revision: 8 $"
__version__ = '0.1.0'


class uninstall(Command):
    """
    Definition for an uninstall command extension.
    """
    
    description = "uninstall (remove) package file set [extension]"
    
    user_options = [\
        ('prefix=', None, "installation prefix")]
    
    
    def initialize_options(self):
    
        self.prefix = None
        
        
    def finalize_options(self):
    
        if self.prefix is None:
            self.prefix = sys.prefix
                
                
    def run(self):
    
        self.announce('running uninstall')
        
        # get a copy of the install manifest
        # this is stored in a file <prefix>/share/install/<package>-<version>.txt
        
        idir = os.path.join(self.prefix, 'share', 'install')
        if (not os.path.exists(idir)) or (not os.path.isdir(idir)):
            self.warn("install record directory %s does not exist" % idir)
            return
            
        # look for an install record file with the same name as this package
            
        installFiles = glob.glob(os.path.join(idir, "*-*.txt"))
        ifile = None
    
        for iname in installFiles:
        
            (istr, ext) = os.path.splitext(os.path.basename(iname))
            (package, version) = istr.split('-')
            if package == self.distribution.get_name():
                ifile = iname
                break
                
        if ifile is None:
            self.warn("install record file for package %s not found in directory %s" % \
                (self.distribution.get_name(), idir))
            return
            
        self.debug_print("using install record file %s" % ifile)
        
        # remove all files listed in the install record
        
        ifd = open(ifile)
        itext = ifd.readlines()
        ifd.close()
        
        for name in itext:
            name = name.strip()
            self.__remove_file(name)
            
        # remove the install record file itself
        
        self.__remove_file(ifile)
     
    
    def __remove_file(self, name):   
        """
        Remove a file if it exists; otherwise issue a warning.
        """
        
        if (not os.path.exists(name)) or (not os.path.isfile(name)):
            self.warn("recorded file %s does not exist" % name)
            return
        self.execute(os.remove, (name,), "removing %s" % name)
    

    
    
             
        
            
        
        
