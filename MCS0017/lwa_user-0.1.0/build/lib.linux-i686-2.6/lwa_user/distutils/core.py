"""
Extensions to distutils tools.
"""

# $Id: core.py 8 2010-02-04 17:11:36Z dwood $


import sys
import string

import distutils.core

import install
import uninstall
import build
import clean


__revision__ = "$Revision: 8 $"
__version__ = '0.1.0'
            


def setup(**attrs): 
    """
    Replacement for distutils.core.setup() function.
    The distutils setup base function is run after first
    installing overlays for some of the commands.
    The function paramters are the same as for distutils.core.setup().
    """
    
    cmdclass = \
    {
        'install'       : install.install,
        'uninstall'     : uninstall.uninstall,
        'build_py'      : build.build_py,
        'build_scripts' : build.build_scripts,
        'clean'         : clean.clean
    }   
    
    # overlay commands
    
    if not attrs.has_key('cmdclass'):
        attrs['cmdclass'] = cmdclass
    
    # run distutils base setup function
    
    distutils.core.setup(**attrs)
      
      
