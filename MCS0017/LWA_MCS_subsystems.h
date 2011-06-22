// LWA_MCS_subsystems.h: S.W. Ellingson, Virginia Tech, 2009 Aug 16
// ---
// Header file defining things used for LWA MCS software -- subsystem-specific 
// See end of this file for history.

#ifndef LWA_MCS_SUBSYSTEMS_H  /* this keeps this header from getting rolled in more than once */
#define LWA_MCS_SUBSYSTEMS_H

/* === LWA Subsystem IDs === */
#define LWA_MAX_SID 13 /* maximum subsystem code; also maximum number of subsystems */
#define LWA_SID_NU1  1 /* null subsystem #1 (used for testing) */
#define LWA_SID_NU2  2 /* null subsystem #2 (used for testing) */
#define LWA_SID_NU3  3 /* null subsystem #3 (used for testing) */
#define LWA_SID_NU4  4 /* null subsystem #4 (used for testing) */
#define LWA_SID_NU5  5 /* null subsystem #5 (used for testing) */
#define LWA_SID_NU6  6 /* null subsystem #6 (used for testing) */
#define LWA_SID_NU7  7 /* null subsystem #7 (used for testing) */
#define LWA_SID_NU8  8 /* null subsystem #8 (used for testing) */
#define LWA_SID_NU9  9 /* null subsystem #9 (used for testing) */
#define LWA_SID_MCS 10 /* MCS */
#define LWA_SID_SHL 11 /* SHL (shelter) */
#define LWA_SID_ASP 12 /* ASP */
#define LWA_SID_DP_ 13 /* DP */
/* When adding subsystems, remember to change LWA_MAX_SID ! */

int LWA_getsid( char *ssc ) {
  /* ssc is the three-character subsystem code */
  /* returns the LWA subsystem ID, or 0 if there is an error */
  int sid = 0;
  if (!strcmp(ssc,"NU1")) sid = LWA_SID_NU1;
  if (!strcmp(ssc,"NU2")) sid = LWA_SID_NU2;
  if (!strcmp(ssc,"NU3")) sid = LWA_SID_NU3;
  if (!strcmp(ssc,"NU4")) sid = LWA_SID_NU4;
  if (!strcmp(ssc,"NU5")) sid = LWA_SID_NU5;
  if (!strcmp(ssc,"NU6")) sid = LWA_SID_NU6;
  if (!strcmp(ssc,"NU7")) sid = LWA_SID_NU7;
  if (!strcmp(ssc,"NU8")) sid = LWA_SID_NU8;
  if (!strcmp(ssc,"NU9")) sid = LWA_SID_NU9;
  if (!strcmp(ssc,"MCS")) sid = LWA_SID_MCS;
  if (!strcmp(ssc,"SHL")) sid = LWA_SID_SHL;
  if (!strcmp(ssc,"ASP")) sid = LWA_SID_ASP;
  if (!strcmp(ssc,"DP_")) sid = LWA_SID_DP_;
  return sid;
  } /* LWA_getsid() */

char *LWA_sid2str( int sid ) {
  /* sid is the LWA subsystem ID */
  /* returns the associated three-character subsystem code */
  /* returns "XXX" if there is an error */
  if (sid == LWA_SID_NU1) return "NU1";
  if (sid == LWA_SID_NU2) return "NU2";
  if (sid == LWA_SID_NU3) return "NU3";
  if (sid == LWA_SID_NU4) return "NU4";
  if (sid == LWA_SID_NU5) return "NU5";
  if (sid == LWA_SID_NU6) return "NU6";
  if (sid == LWA_SID_NU7) return "NU7";
  if (sid == LWA_SID_NU8) return "NU8";
  if (sid == LWA_SID_NU9) return "NU9";
  if (sid == LWA_SID_MCS) return "MCS";
  if (sid == LWA_SID_SHL) return "SHL";
  if (sid == LWA_SID_ASP) return "ASP";
  if (sid == LWA_SID_DP_) return "DP_";
  return "XXX";
  } /* LWA_sid2str() */

/* === LWA Command (TYPE) IDs === */
#define LWA_MAX_CMD  20 /* maximum code; also maximum number of commands */
#define LWA_CMD_MCSSHT 0 /* Not a subsystem command.  Directs ms_mcic to shutdown */
#define LWA_CMD_PNG    1 /* PNG */
#define LWA_CMD_RPT    2 /* RPT */
#define LWA_CMD_SHT    3 /* SHT */
#define LWA_CMD_INI    4 /* INI (SHL,ASP,DP_) */
#define LWA_CMD_TMP    5 /* TMP (SHL) */
#define LWA_CMD_DIF    6 /* DIF (SHL) */
#define LWA_CMD_PWR    7 /* PWR (SHL) */
#define LWA_CMD_FIL    8 /* FIL (ASP) */
#define LWA_CMD_AT1    9 /* AT1 (ASP) */
#define LWA_CMD_AT2   10 /* AT2 (ASP) */
#define LWA_CMD_ATS   11 /* ATS (ASP) */
#define LWA_CMD_FPW   12 /* FPW (ASP) */
#define LWA_CMD_RXP   13 /* RXP (ASP) */
#define LWA_CMD_FEP   14 /* FEP (ASP) */
#define LWA_CMD_TBW   15 /* TBW (DP_) */
#define LWA_CMD_TBN   16 /* TBN (DP_) */
#define LWA_CMD_DRX   17 /* DRX (DP_) */
#define LWA_CMD_BAM   18 /* BAM (DP_) */
#define LWA_CMD_FST   19 /* FST (DP_) */
#define LWA_CMD_CLK   20 /* CLK (DP_) */
/* When adding commands, remember to change LWA_MAX_CMD ! */

int LWA_getcmd( char *ssc ) {
  /* ssc is the three-character command (TYP) */
  /* returns the LWA command ("TYPE"), or 0 if there is an error */
  int cmd = 0;
  if (!strcmp(ssc,"PNG")) cmd = LWA_CMD_PNG;
  if (!strcmp(ssc,"RPT")) cmd = LWA_CMD_RPT;
  if (!strcmp(ssc,"SHT")) cmd = LWA_CMD_SHT;
  if (!strcmp(ssc,"INI")) cmd = LWA_CMD_INI;
  if (!strcmp(ssc,"TMP")) cmd = LWA_CMD_TMP;
  if (!strcmp(ssc,"DIF")) cmd = LWA_CMD_DIF;
  if (!strcmp(ssc,"PWR")) cmd = LWA_CMD_PWR;
  if (!strcmp(ssc,"FIL")) cmd = LWA_CMD_FIL;
  if (!strcmp(ssc,"AT1")) cmd = LWA_CMD_AT1;
  if (!strcmp(ssc,"AT2")) cmd = LWA_CMD_AT2;
  if (!strcmp(ssc,"ATS")) cmd = LWA_CMD_ATS;
  if (!strcmp(ssc,"FPW")) cmd = LWA_CMD_FPW;
  if (!strcmp(ssc,"RXP")) cmd = LWA_CMD_RXP;
  if (!strcmp(ssc,"FEP")) cmd = LWA_CMD_FEP;
  if (!strcmp(ssc,"TBW")) cmd = LWA_CMD_TBW;
  if (!strcmp(ssc,"TBN")) cmd = LWA_CMD_TBN;
  if (!strcmp(ssc,"DRX")) cmd = LWA_CMD_DRX;
  if (!strcmp(ssc,"BAM")) cmd = LWA_CMD_BAM;
  if (!strcmp(ssc,"FST")) cmd = LWA_CMD_FST;
  if (!strcmp(ssc,"CLK")) cmd = LWA_CMD_CLK;
  return cmd;
  } /* LWA_getcmd() */

char *LWA_cmd2str( int cmd ) {
  /* ssc is the three-character command (TYP) */
  /* returns the LWA command ("TYPE"), or "   " if there is an error */
  if (cmd == LWA_CMD_MCSSHT) return "SHT";
  if (cmd == LWA_CMD_PNG)    return "PNG";
  if (cmd == LWA_CMD_RPT)    return "RPT";
  if (cmd == LWA_CMD_SHT)    return "SHT";
  if (cmd == LWA_CMD_INI)    return "INI";
  if (cmd == LWA_CMD_TMP)    return "TMP";
  if (cmd == LWA_CMD_DIF)    return "DIF";
  if (cmd == LWA_CMD_PWR)    return "PWR";
  if (cmd == LWA_CMD_FIL)    return "FIL";
  if (cmd == LWA_CMD_AT1)    return "AT1";
  if (cmd == LWA_CMD_AT2)    return "AT2";
  if (cmd == LWA_CMD_ATS)    return "ATS";
  if (cmd == LWA_CMD_FPW)    return "FPW";
  if (cmd == LWA_CMD_RXP)    return "RXP";
  if (cmd == LWA_CMD_FEP)    return "FEP";
  if (cmd == LWA_CMD_TBW)    return "TBW";
  if (cmd == LWA_CMD_TBN)    return "TBN";
  if (cmd == LWA_CMD_DRX)    return "DRX";
  if (cmd == LWA_CMD_BAM)    return "BAM";
  if (cmd == LWA_CMD_FST)    return "FST";
  if (cmd == LWA_CMD_CLK)    return "CLK";
  return "   ";
  } /* LWA_getsid() */

///* types of messages that can be sent to ms_mcic subsystem handlers */
//#define LWA_MTYPE_PING 1 /* ping; just checking */

#endif /* #ifndef LWA_MCS_SUBSYSTEMS_H */

//==================================================================================
//=== HISTORY ======================================================================
//==================================================================================
// Aug 16, 2009: Added DP support
// Aug 05, 2009: Added ASP support
// Aug 05, 2009: Added SHL commands 
// Aug 02, 2009: Added LWA_CMD_MCSSHT (svn rev 21)
// Aug 01, 2009: Added UT Day/Time to log files (svn rev 19)
//               (svn rev 20)
// Jul 31, 2009: Pulled out from LWA_MCS.h  (svn rev 18)
