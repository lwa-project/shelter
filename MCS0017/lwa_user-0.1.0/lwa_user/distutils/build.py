"""
Extensions to distutils build commands.
"""

# $Id: build.py 9 2010-02-04 17:45:43Z dwood $


__revision__ = "$Revision: 9 $"
__version__  = "dev"


import os
import re

from distutils.util import convert_path
from distutils.command.build_py import build_py as build_py_base
from distutils.command.build_scripts import build_scripts as build_scripts_base



_VERSION_RE = re.compile(r"^__version__\s*=\s*[\"\']dev[\'\"]")



class build_py(build_py_base):
    """
    Definition for a build_py command overlay.
    """
    
    description = build_py_base.description + " [overlay]"
    
    def run(self):
    
        build_py_base.run(self)
        
        outFiles = self.get_outputs(False)
        for name in outFiles:
            if os.path.splitext(name)[1] == '.py':
                self.execute(self.__adjust_py, (name,), "adjusting %s" % name)
            

    def __adjust_py(self, name):
    
        ofile = open(name, 'r')
        otext = ofile.readlines()
        ofile.close()
        
        ofile = open(name, 'w')
        for line in otext:
            if _VERSION_RE.match(line):
                line = "__version__ = '%s'\n" % self.distribution.get_version()
            ofile.write(line)
        ofile.close()
        
        
        
class build_scripts(build_scripts_base):
    """
    Definition for a build_scripts command overlay.
    """
    
    description = build_scripts_base.description + " [overlay]"
    
    def run(self):
    
        build_scripts_base.run(self)
        
        for inFile in self.get_source_files():
            inFile = convert_path(inFile)
            outFile = os.path.join(self.build_dir, os.path.basename(inFile))
            self.execute(self.__adjust_script, (outFile,), "adjusting %s" % outFile)
            
            
    def __adjust_script(self, name):
    
        ofile = open(name, 'r')
        otext = ofile.readlines()
        ofile.close()
        
        ofile = open(name, 'w')
        for line in otext:
            if _VERSION_RE.match(line):
                line = "__version__ = '%s'\n" % self.distribution.get_version()
            ofile.write(line)
        ofile.close()
        
