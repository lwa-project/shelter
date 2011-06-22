----------------------------------------------------------------------
README file for lwa_user package.
----------------------------------------------------------------------

$Id: LWA-USER-README.txt 71 2010-03-17 15:04:28Z dwood $


----------------------------------------------------------------------
DESCRIPTION
----------------------------------------------------------------------

High-level user interface for LWA.

Applications
----------------------------
All applications provide a '-h/--help' command line option to print
out the help contents.

lwa_gui.py - GUI application to provide control and status display
             for LWA subsystems.  The MCS software must be installed
             and running as well as the MCS executables in the 'PATH'
             environment.  An application configuration file must be
             provided.  Set 'LWA_GUI_CONFIG' environment to this 
             config file, or use the '-c/--config-file' command line 
             option. A sample config file is located at 
             'lwa_user/config/lwa_gui.cfg' in the source distribution.
             Use the '-l/--log-file' command line option to save log
             messages to an output file.  Including the '-v/--verbose'
             command line option enables debug messages to be output
             to the log.
             

----------------------------------------------------------------------  
INSTALLATION
---------------------------------------------------------------------- 

This package requires Python version 2.6.x.

The lwa_user software is installed as a regular Python package using
distutils.  Unzip and untar the source distribution. Setup the python 
interpreter you wish to use for running the package applications and
switch to the root of the source distribution tree.

Run 'python setup.py build' to build the package.

Run 'python setup.py install [--prefix=<prefix>]' to install the package.
If the '--prefix' option is not provided, then the installation tree
root directory is the same as for the python interpreter used to run 
setup.py.  For instance, if the python interpreter is in 
/usr/local/bin/python, then <prefix> will be set to '/usr/local'.
Otherwise, the explicit <prefix> value is taken from the command line
option.  The package will install files in the following locations:

<prefix>/bin
<prefix>/lib/python2.6/site-packages
<prefix>/share/doc
<prefix>/share/install

If an alternate <prefix> value is provided, you should set the PATH
environment to include directory '<prefix>/bin' and the PYTHONPATH
environment to include directory '<prefix>/lib/python2.6/site-packages'.

For development work, the package may be run from the source 
distribution tree. Switch to the root of the source distribution tree,
and run 'source setup_dev.[c]sh'.  This script will setup the 
environment to include 'lwa_user/scripts' in the PATH list and to
include 'lwa_user' in the PYTHONPATH list.  Changes may then be made
to the source distribution files, and these changes will take effect
in the current environment.


----------------------------------------------------------------------  
UNIT TESTS
----------------------------------------------------------------------


----------------------------------------------------------------------  
RELEASE NOTES
---------------------------------------------------------------------- 


Version 0.1.0
---------------------------------------------
- Moved to Tix Tk extensions for underlying widget set for lwa_gui.py
    * Allows ARX board windows and SHL power rack windows to be
      collected in tabbed notebooks
    * Increased size to spinbox widget arrow buttons
    * Default, useful keyboard bindings come automatically with many
      of the Tix widgets
- Added 'Filter OFF' button to ARX channel controls
- Added 'Shutdown' command button to ASP window
- Added 'Initialize' and 'Shutdown' command buttons to SHL window
- Added displays for MCS Reserved MIB items in the ASP and SHL windows


Version 0.0.0
---------------------------------------------
- First trial version for J.Craig to test with ASP development.
- Support for ASP and SHL sub-systems, with limited support for update
  of status display items.
  

