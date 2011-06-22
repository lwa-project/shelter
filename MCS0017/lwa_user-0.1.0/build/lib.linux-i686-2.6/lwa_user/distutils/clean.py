"""
Extensions to distutils clean commands.
"""

# $Id: clean.py 8 2010-02-04 17:11:36Z dwood $


__revision__ = "$Revision: 8 $"
__version__ = '0.1.0'


import os

from distutils.command.clean import clean as clean_base
from distutils.sysconfig import get_config_var


class clean(clean_base):
    """
    Definition for a clean command overlay.
    """
    
    description = clean_base.description + " [overlay]"

    def run(self):
        
        clean_base.run(self)
        
        if self.all and self.distribution.has_ext_modules():
        
            # clean any inplace build products "python setup.py build_ext --inplace"
        
            for ext in self.distribution.ext_modules:
                fileName = self.__get_ext_filename(ext.name)
                if os.path.exists(fileName):
                    self.execute(os.remove, (fileName,), "removing %s" % fileName)    
        

    @staticmethod
    def __get_ext_filename(ext_name):
        """
        Convert the name of an extension (eg. "foo.bar") into the name
        of the file from which it will be loaded (eg. "foo/bar.so", or
        "foo\bar.pyd").
        """

        ext_path = ext_name.split('.')
        # OS/2 has an 8 character module (extension) limit :-(
        if os.name == "os2":
            ext_path[len(ext_path) - 1] = ext_path[len(ext_path) - 1][:8]
        # extensions in debug_mode are named 'module_d.pyd' under windows
        so_ext = get_config_var('SO')
        if os.name == 'nt' and self.debug:
            return apply(os.path.join, ext_path) + '_d' + so_ext
        return apply(os.path.join, ext_path) + so_ext
        

