
How to use MCS/Scheduler as an Engineering Interface for SHL (or other subsystems)
S.W. Ellingson
Aug 13, 2009


Version 0.2 and greater of the MCS/Scheduler can be used as an "engineering interface" for SHL.  By "engineering interface", I mean a simple way to monitor and control SHL without necessarily using the full LWA MCS, and without writing software from scratch to do this.  This interface is through the command line and thus easily scripted, easily augmented with a GUI, etc.  This procedure is easily adapted for other subsystems.

To begin, at least skim the file "readme.txt" for the MCS/Scheduler software.  Follow the "Quick Start" section of that document to get the MCS/Scheduler software installed and checked out.  Also, try test case "test5.sh" (described in the same document) to make sure SHL is working OK.

Here's the scheme:


0. Shutdown MCS/Scheduler, if for some reason it should already be running.


1. Create a file "SHL_only.dat" -- contents shown below -- that tells MCS/Scheduler how to find SHL.  As shown below, this assumes SHL is at 127.0.0.1 (i.e., on the same PC using local loopback), and that MCS should transmit on port 1738 and receive on port 1739.  If your values are different, just substitute those values.  

mibinit SHL 127.0.0.1 1738 1739
mcic    SHL


2.  Get SHL (the MCS0012 emulator, or the actual thing) running.


3.  Get MCS/Scheduler running using the command line below:

$ ./ms_init SHL_only.dat


4.  Now initialize SHL (as required by the ICD for SHL) using "msei".  Using the command line below, SET-POINT will be "00090", DIFFERENTIAL will be "2.5", and rack 1 (and only rack 1) will be made available:

$ ./msei SHL INI '00090&2.5&100000'


5.  Sending command messages to SHL is simple; the command line is 
"msei SHL <cmd> <DATA field>".  Use quotes around the DATA field if there are significant spaces or control characters.  Here are some examples:

$ ./msei SHL PNG
$ ./msei SHL RPT PORTS-AVAILABLE-R1
$ ./msei SHL TMP '00091'
$ ./msei SHL DIF '1.5'
$ ./msei SHL PWR '104ON '

The local MIB is updated automatically when RPT response messages are received, and is also updated when other commands are returned from SHL with "A" ("accepted") status.


6.  To check the local MIB (i.e., what MCS thinks is happening), use "ms_mdr" or "ms_mdre".  Here, we ask MCS what is the value of the MIB entry "SUMMARY" for SHL.  It responds with the value, followed by the time that SUMMARY was last updated (yymmdd hh:mm:ss UT). 

$ ./ms_mdre SHL SUMMARY
NORMAL
090804 10:05:02

You can see the whole MIB at once as follows:

$ ./ms_mdr SHL
(output not shown; see readme.txt for an example)


7.  To cleanly shutdown the Scheduler (highly recommended):

$ ./msei MCS SHT


8.  At any time you can inspect MCS/Scheduler's log (see readme.txt for information about format, interpretation, etc):

$ cat mselog.txt








