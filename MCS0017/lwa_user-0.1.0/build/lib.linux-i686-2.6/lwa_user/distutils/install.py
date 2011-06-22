"""
Extensions for distutils install command.
"""

# $Id: install.py 8 2010-02-04 17:11:36Z dwood $


import os

from distutils.file_util import write_file
from distutils.command.install import install as install_base


__revision__ = "$Revision: 8 $"
__version__ = '0.1.0'



class install(install_base):
    """
    Definition for an install command overlay.
    """
    
    description = install_base.description + " [overlay]"
            
            
    def run(self):
    
        # first attempt to uninstall current version of package
        
        odict = self.distribution.get_option_dict('uninstall')
        odict['prefix'] = ('install command', self.prefix)
        self.run_command('uninstall')
    
        # run the normal install process
    
        install_base.run(self)
        
        # get a copy of the install manifest
        # this is stored in a file <prefix>/share/install/<package>-<version>.txt
        
        idir = os.path.join(self.prefix, 'share', 'install')
        self.mkpath(idir)
        
        ifile = os.path.join(idir, '%s-%s.txt' % \
            (self.distribution.get_name(), self.distribution.get_version()))
        
        outputs = self.get_outputs()
        if self.root:
            root_len = len(self.root)
            for counter in xrange(len(outputs)):
                outputs[counter] = outputs[counter][root_len:]
        self.execute(write_file, (ifile, outputs), "writing list of installed files to '%s'" % ifile)
         
