
MCS/Scheduler Software
Version 0.3 (pre-alpha)
S.W. Ellingson
Aug 25, 2009


Major changes in this version
=============================

1. DP is now partially supported, in addition to the previously-supported subsystems SHL, ASP, and the mock subsystems (NU1..NU4).  For DP, the MIB is fully supported as well as the commands TBW, TBN, CLK, and INI.  The DP commands DRX, BAM, and FST are not yet supported.

2. Although it should not be apparent to users of the previous version, many changes have been made in order to accommodate the raw binary parameters specified in the DP ICD.  Many changes have been made in order to make sure values are displayed in a reasonable, consistent way (e.g., as an integer when the data represents an integer, regardless of whether the data is being transported as characters or as raw binary) in log messages and ms_mdr(e) output.    


Introduction
============

This is software developed for the MCS "Scheduler" computer.  The Scheduler computer accepts commands from the MCS "Executive" computer (or, for development/testing purposes, something emulating the Executive) and interfaces with subsystems (or things emulating subsystems).  Also provided are software and scripts which can be used to demonstrate and evaluate the software, including control programs and a subsystem emulation program.  

Note that the software is designed such that everything can be run on a single computer without modification; the difference between "scheduler and subsystems on separate PCs" operation and "everything on a single PC" operation is simply whether interprocess communications are directed to separate computers using network IP addresses, or to local processes using the loopback (127.0.0.1) IP address, respectively.

The software is written entirely in ANSI C and was developed on Ubuntu Linux 9.04 (AMD64 Desktop).  Shell scripts (provided) are used for demonstration and testing.  Subsystem emulators (also provided) are written in Python.

This software is considered "pre-alpha". Specifically, it is functional and released to facilitate review and comment; but not all required features are implemented, and thorough testing has not yet been done.  This software exists in the author's Subversion archive as revision 34. 

Limitations of this release of the software include:

-- Only SHL, ASP, DP, and the mock subsystems (NU1, NU2, etc.) are explicitly supported. (It is probably possible to PNG, RPT, and SHT other subsystems, but this has not been tested.)  The mock subsystems behave as actual LWA subsystems, but are limited to the commands PNG, RPT, and SHT and implement only the MCS-RESERVED branch of the MIB. 

-- The DP commands DRX, BAM, and FST are not yet supported.

-- The software currently sends commands to subsystems as quickly as possible, without regard for scheduling.  That is, the Scheduler (ironically) does not yet respect requests to queue tasks until a predefined future time.  (The task queue architecture for doing this exists and is used; it is simply that the Scheduler does not yet use scheduled time as a criterion for when to send commands to subsystems.)

-- A fully-functional emulator is provided for SHL, which makes comprehensive testing of the software as an interface to SHL very simple.  A limited "generic" emulator is also provided, which makes possible limited testing of the interface to ASP and DP.  The generic emulator fully supports the mock subsystems.


File Inventory
==============

readme.txt
-- This file.

readme_SHL_EI.txt
-- How to use MCS/Scheduler as an Engineering Interface for SHL (applicable to ASP, DP, etc. as well)

makefile
-- "$ make" compiles everything needed and places executibles in target directory.

ms_init.c
-- Using a script (specified in the command line), this process initializes locally-maintained MIB files, launches subsystem handling processes (ms_mcic's), sets up interprocess communications (using POSIX message queues), launches the scheduler's executive process (ms_exec), and terminates.

ms_exec.c
ms_exec_log.c
-- The scheduler's executive process.  On the user side, accepts commands via a TCP connection at port 9734 (can be changed; see LWA_PORT_MSE in LWA_MCS.h).  Communicates with subsystem handlers (ms_mcic's) via POSIX message queues. 

ms_mcic.c
ms_mcic_mib.c
ms_mcic_SHL.c
ms_mcic_ASP.c
ms_mcic_DP_.c
-- Code for the subsystem handler process "ms_mcic".  One instance of ms_mcic is launched for each subsystem to be managed. 

dat2dbm.c
-- This program converts initial subsystem MIBs from human-readable text format to the "dbm" format used by the scheduler software.  (See the section "Why dbm Files?" below for more information.) Called by ms_init once for each subsystem.

LWA_MCS.h
LWA_MCS_subsystems.h
-- Header files used by the software above.

ms_makeMIB_ASP.c
ms_makeMIB_DP.c
-- Automates process of creating a text-format MIB init files for ASP and DP (required by ms_init), respectively.

That's it for actual MCS/Scheduler software.  The following programs are support programs to facilitate testing and development:

msei.c
-- Program that can be used to send commands to the Scheduler software (specifically, to ms_exec) in lieu of MCS/Executive.

ms_mdr.c
ms_mdre.c
-- Programs that can be used to read the dbm-format MIB files used by MCS/Scheduler software.  ms_mdr displays all content of a MIB file.  ms_mdre displays only a specified entry (handy especially for use in scripts).  In all cases, the time of last update is indicated.

test1.sh
test2.sh
test3.sh
test4.sh
test5.sh
test6.sh
test7.sh
-- Shell scripts used to demonstrate and test the software.  See the "Quick Start" and "Defined Test Cases" sections below for more information.

ms_shutdown.sh
-- A simple shell script that kills ms_exec and any ms_mcic processes in the event that these processes have not (or cannot) be shut down in an orderly way.

NU1_MIB_init.dat
NU2_MIB_init.dat
NU3_MIB_init.dat
NU4_MIB_init.dat
SHL_MIB_init.dat
-- These are human-readable/editable text-format MIB files used by ms_init (via dat2dbm) to generate dbm-format MIB files for SHL and the mock subsystems (NU1, NU2, NU3, and NU4).  (The corresponding file for ASP is generated by ms_makeMIB_ASP.c)  These files tell MCS/Scheduler the necessary details about the structure of the subsystem's MIB.   

mch_minimal_server.py
-- A python script which can be used to emulate a minimally-functional MCS Common ICD-compliant subsystem.  One of the command line arguments is the subsystem three-letter name, so this script can be used to emulate any subsystem, although at a very limited level.


Quick Start
===========

In the procedure below, the software is compiled and a simple test is performed to demonstrate the functioning of the software.

(1)  If not done already, place all files in a single directory and cd to that directory.

(2)  Make the software ($ make).  Although it is very popular, not all computers will have the necessary gdbm library (used to handle the dbm-format MIB files) installed, and others will call it by another name. If make complains about this being unavailable, see the "Troubleshooting" section below. 

(3)  Ensure that ports 1738 and 1739 are not in use on your computer.  (On Ubuntu, 
"$ cat /etc/services" shows you a list of all committed ports.)  If these ports are in use, you will need to modify test1.sh; simply change all instances of these ports to ports which are available.

(4)  Run test1.sh ("$ sh ./test1.sh" should do it).  This script does the following things: 
-- Launches a subsystem emulator for a minimal (mock) subsystem called NU1.
-- Brings up MCS/Scheduler with NU1 as a defined subsystem.
-- Shows the current value of SUMMARY for NU1 ("UNK" for unknown) using ms_mdre.
-- Sends NU1 a PNG.
-- Shows the new value of SUMMARY for NU1 ("NORMAL") using ms_mdre
-- Shuts down MCS/Scheduler and the NU1 subystem emulator
The console output will look something like this ("**" indicates comments added here which do not actually appear in the output)

$ ./ms_init test1.dat
[1] I am ms_init (v.20090802.1)
[1] ms_init_filename: <test1.dat>
[1] mibinit NU1
[5] I am dat2dbm (v.20090816.2)
[5] exit(EXIT_SUCCESS)
[1] mcic NU1
[6/6388] I am ms_mcic (v.20090825.1) 
[6/6388] NU1 specified
[6/6388] IP_ADDRESS <127.0.0.1>
[6/6388] TX_PORT = 1738
[6/6388] RX_PORT = 1739
[1] From NU1's MQ: <I'm up and running>
[1] From NU1's MQ: <I saw a PNG>
[1] WARNING: ms_init_file command <> not recognized (ignored)
[1] Completed ms_init start-up script
[1] Handing off to ms_exec
[2] I am ms_exec (v.20090825.1)
[1] exit(EXIT_SUCCESS)

** ms_init ("[1]") runs, sets everything up, launches ms_exec ("[2]"), and quits. 
** "[6]" is the ms_mcic process talking.

$ ./ms_mdre NU1 SUMMARY
UNK
090825 18:02:55

** "UNK" means unknown.  The time (UT, yymmdd hh:mm:ss) of last update is shown in the next line.

$ ./msei NU1 PNG
[7] ref=2, bAccept=1, eSummary=0, data=<Task has been queued>

** msei ("[7]") instructs MCS/Scheduler (via ms_exec) to send PNG to NU1.  msei does not wait for, or provide, a response.  

$ ./ms_mdre NU1 SUMMARY
NORMAL
090825 18:03:04

** note MIB entry has now been updated to NORMAL (note also time).     

$ ./msei MCS SHT
[6/8053] Directed to shut down. I'm out...
[7] ref=0, bAccept=1, eSummary=5, data=<Starting shutdown>

** MCS can be sent PNG and SHT commands just like subsystems.  If you tell MCS to SHT, ms_exec will shut down the ms_mcic's and associated message queues in an orderly way, and then exits itself.  

Killed python(8044) with signal 15


(5)  Check out the file mselog.txt, which is a log file created by ms_exec.  It should look something like this:

$ cat mselog.txt 
090825 18:02:56  55068  64976782 N I am ms_exec (v.20090825.1) [2]
090825 18:02:56  55068  64976782 N Command line: ms_exec 1
090825 18:02:56  55068  64976782 N Added subsystem MCS
090825 18:02:56  55068  64976782 N Added subsystem NU1
090825 18:03:04  55068  64984790 T         2 1 NU1 PNG |
090825 18:03:04  55068  64984790 T         2 2 NU1 PNG |
090825 18:03:04  55068  64984796 T         2 3 NU1 PNG |
090825 18:03:05  55068  64985803 N Starting shutdown...
090825 18:03:05  55068  64985803 T         3 1 NU1 SHT Request ms_mcic shutdown|
090825 18:03:05  55068  64985804 T         3 2 NU1 SHT Request ms_mcic shutdown|
090825 18:03:06  55068  64986804 N Deleting tx msg queue for NU1
090825 18:03:06  55068  64986804 N ms_exec shutdown complete

The first 5 columns are: yymmdd hh:mm:ss (UT), MJD, MPM, "N" (for "info" messages) or "T" (for "task progress" messages).  Info messages conclude with remarks.  Task progress ("T") messages have 5 more columns:  REFERENCE, task progress, subsystem, command, and remarks.  Task progress is indicated as a number (defined in LWA_MCS.h).  Here, 1 (LWA_MSELOG_TP_QUEUED) means the task has been queued by ms_exec, but not yet sent to the ms_mcic, 2 (LWA_MSELOG_TP_SENT) means the task has been sent to the ms_mcic, and 3 (LWA_MSELOG_TP_SUCCESS) means the task has completed successfully (i.e., ms_mcic reports that the subsystem responded, and that it has successfully updated the local MIB). The pipe ("|") symbols are used to denote the end of a data field.

(6)  Check out the current MIB for NU1 (as known to the scheduler) using ms_mdr ($ ms_mdr NU1).  It should look something like this (This is a wide display so if you see line wrapping, increase the width of your display):

$ ./ms_mdr NU1
MCH_TX_PORT                      1 0.2          1738                             a5     NUL    |090825 18:02:55
INFO                             1 1.2          UNK                              a256   a256   |090825 18:02:55
SUBSYSTEM                        1 1.4          UNK                              a3     a3     |090825 18:02:55
MCS-RESERVED                     0 1            NUL                              NUL    NUL    |090825 18:02:55
SERIALNO                         1 1.5          UNK                              a5     a5     |090825 18:02:55
MCH_RX_PORT                      1 0.3          1739                             a5     NUL    |090825 18:02:55
LASTLOG                          1 1.3          UNK                              a256   a256   |090825 18:02:55
SUMMARY                          1 1.1          NORMAL                           a7     a7     |090825 18:03:04
MCH_IP_ADDRESS                   1 0.1          127.0.0.1                        a15    NUL    |090825 18:02:55
VERSION                          1 1.6          UNK                              a256   a256   |090825 18:02:55
[8/6607] exit(EXIT_SUCCESS)

The columns are: MIB label, "0" or "1" (indicating branch or value, respectively), MIB index, value, a format indicator (for internal use only), another format indicator (for internal use only), and the UT date/time.  Note most MIB entries are "UNK" (unknown) because we never asked for them.  Only SUMMARY has been updated (as a result of the PNG command). Several MIB entries ("MCH_IP_ADDRESS", "MCH_TX_PORT", and "MCH_RX_PORT") were not part of the initial MIB, but are added by ms_init (via dat2dbm).  The entries stored in dbm files are in no particular order, and ms_mdr makes no attempt to sort them. 


Defined Test Cases
==================

Shell scripts are provided to evaluate the software:

test1.sh
This is the script used in the "Quick Start" section, above. 

test2.sh
Similar to test1.sh, except the entire MIB (not just summary) is updated.  Thus, demonstrates the "RPT" command.  Witness the results using "$ ./ms_mdr NU1" to see the updated MIB, and "$ cat mselog.txt" to see the log.

test3.sh
Similar to test2.sh, except does this for a system of *four* mock subsystems.  These subsystems are called NU1, NU2, NU3, and NU4.  These mock subsystems come up with unique MIB values so as to allow the user to verify that MCS/Scheduler is accessing the correct subsystem; for example, VERSION for NU3 is "NU3-1".

test4.sh
Brings MCS/Scheduler with the four mock subsystems NU1, NU2, NU3, and NU4.  Then, sends each 120 "PNG" commands as quickly as possible.  This tests MCS/Scheduler's ability to juggle this without overflowing an internal task queue or experiencing some other load-related error.  To verify success, check mselog.txt and make sure that there are no "task progress" indicators greater than 3; i.e., that all tasks terminate with status "3" ("LWA_MSELOG_TP_SUCCESS").

test5.sh (SHL demo)
Brings up SHL (using the MCS0012 emulator, but easily modified to accomodate the actual SHL), updates a few MIB entries using RPT, and tests the SHL-specific commands.  You have to install the MCS0012 into a subdirectory "Emulator_SHL" first; see the comments at the top of the script.

test6.sh (Crude ASP demo)
Brings up ASP (using the generic python-based subsystem emulator, but easily modified to accomodate an ASP-savvy emulator or the actual ASP), updates a few MIB entries using RPT, and tests ASP-specific commands.  Also demonstrates use of ms_makeMIB_ASP.c to generate an initial MIB for ASP.  Note that the emulator won't recognize the ASP-specific MIB entries and commands, but at least you'll see that that MCS/Scheduler is recognizing the commands and handling the errors being returned by the emulator in a reasonable way.

test7.sh (Crude DP demo) 
Brings up DP (using the generic python-based subsystem emulator, but easily modified to accomodate an DP-savvy emulator or the actual DP), updates a few MIB entries using RPT, and tests DP-specific commands.  Also demonstrates use of ms_makeMIB_DP.c to generate an initial MIB for ASP.  Note that the emulator won't recognize the DP-specific MIB entries and commands, but at least you'll see that that MCS/Scheduler is recognizing the commands and handling the errors being returned by the emulator in a reasonable way.


Modifying Test Cases for Network Operation
==========================================

As mentioned above and explained in the scripts, the difference between running everything on one computer (e.g., for development and test) and running processes on different computers (e.g., the actual operational condition, where ms_exec and the ms_mcic's are on one computer, and the subsystems are on other computers) is trivial -- just replace the loopback IP (127.0.0.1), whereever it appears in the test scripts (test#.sh), with the appropriate IP address.   


Why dbm Files?
==============

The reader may be curious as to why this software uses the "dbm" facility as opposed to some other method (e.g., ASCII files, packed/binary files, XML, SQL) to store MIB information.  The primary reason is that the dbm facility provides a C-friendly database capability that is lightweight, compact, very fast, requires no separate server (in contrast to something like SQL), and is very popular and well-documented. Also, Python enthusiasts should note that Python can easily read/manipulate dbm files ("batteries included", as always).      


Troubleshooting / Known Bugs
============================

-- For problems related to the dbm library, the book "Beginning Linux Programming" (N. Matthew and R. Stones, 4th Ed, Wrox Press, 2008) is recommended. The dbm library is not necessarily preinstalled on all *nix distributions, and sometimes goes by different names; the book will be helpful in figuring how to get dbm installed if you are using something other than Ubuntu 9.04.

-- User-side communication with the ms_exec process is via a TCP socket connection.  If ms_exec process is restarted within a few seconds of being killed, it is possible that the operating system will not yet have released the socket address. In this case, ms_exec will experience a fatal error during start up, including a console message reading something like "ms_exec: Address already in use", possibly also referring to an error in the "bind()" operation.  If this happens, simply kill all Scheduler processes (you can use ms_shutdown.sh for this) and wait a few seconds longer before beginning again.  Note that this is not a bug; it simply reflects the fact that the operating system requires several seconds to free socket addresses even when the associated sockets are properly and explicitly closed. 

-- If the software behaves strangely, then it could be because some leftover process(es) from a previous (aborted) test are getting in the way.  A simple way to make sure this is not the case is as follows:
$ sh ./ms_shutdown.sh
$ killall -v python 
Wait a few seconds, then try again.  This kills any ms_init, ms_exec, and ms_mcic processes, as well as anything that was started using "$ python ..." (e.g., the subsystem emulators).

-- The function LWA_time2tv() currently assumes that the number of milliseconds in a day is a constant.  This will eventually produce intermittent small errors since this is not exactly true.  

-- "[1] WARNING: ms_init_file command <> not recognized (ignored)" is of no consequence (just a wart I have yet to fix...).


Other Notes & Issues 
====================

-- I assumed that the argument for DP's CLK command is supposed to be uint32 (as opposed float32, which is what the DP ICD says).  

-- The DP ICD (v.G) says TBN filter codes go from 1..6 in the command description, but indicate 1..7 in the appendix.  I have assumed latter is correct (changes nothing other than what appears as "help" in msei).

-- The program which generates DP initial MIB text files -- ms_makeMIB_DP.c -- currently initializes values to numbers which are "interesting" (i.e., not all zero or NUL) so that it can be verified that ms_mdr and ms_mdre are able to read non-trivial values.  Eventually, this should be undone.





