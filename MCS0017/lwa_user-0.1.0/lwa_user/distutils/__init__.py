"""
Extensions to distutils tools.

To make use of the extensions change the following line in a setup.py script from:

from distutils.core import setup

to:

from lwda_util.distutils.core import setup

The lwda_user.distutils.core module provides a function setup() which is a 
wrapper for the standard distutils setup() function.  All of the arguments are the 
same.  The wrapper simply installs a few custom command classes before calling the 
base setup() function.  The command extensions are classes derived from the 
standard distutils.command package command classes.  They basically run the standard
command procedure and then fixup the outputs. 

The "build" command extension will search all of the installable python script (*.py)
files for a line similar to:

__version__ = "dev"

When found, the value of the __version__ attribute is set to the version value recorded 
in the setup.py script.  For instance:

__version__ = "v0.6.0"

These fixups will get copied into the install directory as part of the "install" 
command process. Any module or script should then be able to get its own version by 
referencing the __version__ attribute.  To get the version of an external package, 
you can reference the __version__ attribute of the pacakge header: 
"print lwda_util.__version__".  If you are running a test or local copy of the package, 
then the __version__ attribute's value will remain as "dev" to indicate an un-versioned 
copy of the software is being run.

The overlay for the "install" command runs the standard install procedure, but 
automatically makes use of the record file option for this command to record the file 
manifest of the install.  This serves two purposes:

1. A complete list of the files associated with a package/version is maintained so 
   that they may be cleanly removed by an uninstall process.
2. The prescience of the record file itself is an indicator that the package (and a 
   particular version) is installed.

The install command extension will put the record file in the "share" subdirectory of 
the installation prefix assigned with the "--prefix" option to the install command (or 
if not given, use the location of the python interpreter as the installation prefix).  
For example, installing the lwda_util package with a tagged copy of version "v0.6.0" 
on host with installation prefix "/opt/python2.4" will create the record file in location:

/opt/python2.4/share/install/lwda_util-v0.6.0.txt

To make the "install" command work correctly, it is necessary to include an "uninstall" 
command.  This may be run independently "python setup.py uninstall [--prefix=]", but it 
is automatically run as the first step in the "install" command overlay.  As you might 
guess, the uninstall command searches for the install record file for a package, removes
all of the files listed in the install record, and then removes the install record file 
itself.

The "clean" command has additional processing added which will attempt to find and
remove any in-place build products from package extension modules.  On UNIX, these will 
be *.so files which are built in the local package directory.  Addition "clean"
for in-place files is only run when the "--all" option is provided.
"""

# $Id: __init__.py 47 2010-03-03 17:42:50Z dwood $


__revision__  = "$Revision: 47 $"
__version__   = None
__author__    = "D.L.Wood"









