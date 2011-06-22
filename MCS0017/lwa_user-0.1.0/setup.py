"""
Setup script for lwa_user package.
"""

# $Id: setup.py 46 2010-03-03 17:41:42Z dwood $


import os
                                  
from lwa_user.distutils.core import setup


__revision__ = "$Revision: 46 $"
__version__  = "dev"
__author__   = "D.L.Wood"


PACKAGE_NAME    = 'lwa_user'
PACKAGE_VERSION = '0.1.0'

SCRIPTS = []
PACKAGE_DATA = {PACKAGE_NAME : [],
  '%s.gui' % PACKAGE_NAME : [],
  '%s.distutils' % PACKAGE_NAME : []}            
DATA_FILES = []


# setup lwa_gui.py application

SCRIPTS.append(os.path.join(PACKAGE_NAME, 'scripts', 'lwa_gui.py'))

PACKAGE_DATA[PACKAGE_NAME].append(os.path.join('scripts', 'lwa_gui.py'))
PACKAGE_DATA[PACKAGE_NAME].append(os.path.join('config', 'lwa_gui.cfg'))


# package documentation

DATA_FILES.append(('share/doc/lwa_user',
  ['LWA-USER-README.txt']))


# perform setup of package

setup(name = PACKAGE_NAME,
      version = PACKAGE_VERSION,
      description = 'LWA high-level user interface',
      author = 'D.L.Wood',
      author_email = 'daniel.wood@nrl.navy.mil',
      url = 'TBD',
      packages = [PACKAGE_NAME,
        "%s.distutils" % PACKAGE_NAME,
        "%s.gui" % PACKAGE_NAME],
      scripts = SCRIPTS,
      package_data = PACKAGE_DATA,
      data_files = DATA_FILES 
      )
      
      
