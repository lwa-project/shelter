// LWA_MCS.h: S.W. Ellingson, Virginia Tech, 2009 Aug 17
// ---
// Header file defining things used for LWA MCS software 
// See end of this file for history.

#include <string.h>
#include <time.h>
#include <sys/time.h>

#include "LWA_MCS_subsystems.h"

#define MIB_REC_TYPE_BRANCH 0 
#define MIB_REC_TYPE_VALUE  1 
#define MIB_INDEX_FIELD_LENGTH 12
#define MIB_LABEL_FIELD_LENGTH 32
#define MIB_VAL_FIELD_LENGTH 256

/* record structure for dbm */
struct dbm_record {
                    /* Note MIB index is used to key the dbm database;
                       thus this appears in a separare structure */
  int  eType;       /* branch or value; use MIB_REC_TYPE_* */
  char index[MIB_INDEX_FIELD_LENGTH];   /* MIB index. Stored as char */
  char val[MIB_VAL_FIELD_LENGTH];    /* MIB value.  Always stored as char. */
  char type_dbm[6]; /* Indicates data type used in dbm database. */  
                    /*   See elsewhere for defs */
  char type_icd[6]; /* Indicates data type/format for MCS ICD "RPT" responses. */ 
                    /*   See elsewhere for defs */
  struct timeval last_change; /* Indicates time this entry was last changed */
                       /* .tv_sec is seconds into current epoch */
                       /* .tv_usec is fractional remainder in microseconds */
  };


// Data type/format codes:
// ------------------------
// NUL:   No data stored (e.g., branch head entry)
// a####: printable (i.e., ASCII minus escape codes), #### = number of characters
//        e.g., "a3" means 3 printable ASCII-encoded characters
// r####: raw data (not printable), #### = number of bytes
//        e.g., "r1024" means 1024 bytes of raw data
// i1u:   integer, 1 byte,  unsigned, big-endian (=uint8)
// i2u:   integer, 2 bytes, unsigned, big-endian (=uint16)
// i4u:   integer, 4 bytes, unsigned, big-endian (=uint32)
// f4:    float, 4 bytes, big-endian (=float32)



//#define MQ_MAX_TEXT 512
#define MQ_MS_KEY   1000 /* key for scheduler receive queue */
                         /* (the one that the mcic's send to */
/* note: queue keys for subsystems = MQ_MS_KEY + LWA_SID_* */


/* === sockets === */
/* check /etc/services for ports already assigned */

#define LWA_IP_MSE   "127.0.0.1" /* IP address of MCS Scheduler "ms_exec" process */
#define LWA_PORT_MSE 9734        /* port for MCS Scheduler "ms_exec" process */

#define LWA_CMD_STRUCT_DATA_FIELD_LENGTH 256

struct LWA_cmd_struct {
  long int sid; /* subsystem ID.  Must be "long int" to accomodate message queue use */
  long int ref; /* REFERENCE number */
  int  cid; /* command ID */
  //int  subslot; /* subslot for  */
  int  bScheduled; /* = 0 means "not scheduled (do as time permits)"; */
                   /* = 1 means "do as close as posible to time indicated by tv field" */  
  struct timeval tv; /* Indicates time this command is to take effect */
                     /* .tv_sec is seconds into current epoch */
                     /* .tv_usec is fractional remainder in microseconds */
  int  bAccept; /* response: see LWA_MSELOG_TP_* */
  int  eSummary; /* summary; see LWA_SIDSUM_* macrodefines */
  int  eMIBerror; /* >0 if ms_mcic had a problem with the MIB.  see LWA_MIBERR_* */
  char data[LWA_CMD_STRUCT_DATA_FIELD_LENGTH]; /* DATA on way out, R-COMMENT on way back */   
  int  datalen; /* -1 for (printable) string; 0 for zero-length; otherwise number of significant bytes */
  };


#define LWA_MSELOG_TP_AVAIL     0 /* no task; used to make task queue slots as available */
#define LWA_MSELOG_TP_QUEUED    1  
#define LWA_MSELOG_TP_SENT      2 
#define LWA_MSELOG_TP_SUCCESS   3 /* subsystem accepted ("A") */
#define LWA_MSELOG_TP_FAIL_EXEC 4 
#define LWA_MSELOG_TP_FAIL_MCIC 5 
#define LWA_MSELOG_TP_FAIL_REJD 6 /* subsystem rejected ("R") */
#define LWA_MSELOG_TP_DONE_UNK  7 /* ms_mcic happy, but subsystem response not clear */ 
                                  /* (task considered done) */
#define LWA_MSELOG_TP_DONE_PTQT 8 /* ms_mcic reporting PTQ timeout (i.e., subsystem response timed out) */ 
                                  /* (task considered done) */

/* Using approach of bit-flagging (note power-of-two values) so these can be added: */
#define LWA_MIBERR_OK         0 /* no error to report */
#define LWA_MIBERR_CANTOPEN   1 /* couldn't open MIB dbm */
#define LWA_MIBERR_CANTSTORE  2 /* couldn't store to MIB dbm */
#define LWA_MIBERR_REF_UNK    4 /* REFERENCE was unrecognized, so not sure what this message is */
                                /* in response to.  Other than SUMMARY, MIB may not have been */
                                /* properly updated. */
#define LWA_MIBERR_CANTFETCH  8 /* couldn't fetch from MIB dbm */
#define LWA_MIBERR_SID_UNK   16 /* Subsystem ID (3-char) was unrecognized. Other than SUMMARY, */
                                /* MIB may not have been properly updated. */
#define LWA_MIBERR_SID_CID   32 /* Command is something this subsystem shouldn't have supported */
                                /* e.g., NU# doing something other than PNG, RPT, or SHT */
                                /* e.g., Receiving MCS as a subsystem ID */  
                                /* e.g., Subsystem MIB handler (ms_mcic_XXX.c) didn't recognize command */ 
#define LWA_MIBERR_OTHER     64 /* MIB may be out of sync for other reasons.  For example: */
                                /* - PTQ timeout, so not sure if command was acted up or not */ 

/* Subsystem SUMMARY (MIB 1.1) values */
#define LWA_SIDSUM_NULL    0 
#define LWA_SIDSUM_NORMAL  1
#define LWA_SIDSUM_WARNING 2
#define LWA_SIDSUM_ERROR   3
#define LWA_SIDSUM_BOOTING 4
#define LWA_SIDSUM_SHUTDWN 5

int LWA_getsum( char *summary ) {
  /* "summary" is the 7 character (max) R-SUMMARY */
  /* returns the LWA_SIDSUM_* code, or 0 if there is an error or "NULL" */
  char summary2[8];
  int eSummary = LWA_SIDSUM_NULL;

  sscanf(summary,"%s",summary2); /* strips off any leading or trailing whitespace */

  if (!strcmp( summary2 ,"NULL"   )) eSummary = LWA_SIDSUM_NULL;
  if (!strcmp( summary2 ,"NORMAL" )) eSummary = LWA_SIDSUM_NORMAL;
  if (!strcmp( summary2 ,"WARNING")) eSummary = LWA_SIDSUM_WARNING;
  if (!strcmp( summary2 ,"ERROR"  )) eSummary = LWA_SIDSUM_ERROR;
  if (!strcmp( summary2 ,"BOOTING")) eSummary = LWA_SIDSUM_BOOTING;
  if (!strcmp( summary2 ,"SHUTDWN")) eSummary = LWA_SIDSUM_SHUTDWN;

  return eSummary;
  } /* LWA_getsum() */

 
#define LWA_MAX_REFERENCE 999999999 /* largest reference number before roll-over */

/* these are for ms_mcic's (pending) task queue */
#define LWA_PTQ_SIZE 500  /* because DP limits us to 120 commands/slot (times 3 seconds for timeout) */
#define LWA_PTQ_TIMEOUT 4 /* timeout in seconds */

/* these are for ms_exec's task queue */
#define LWA_MS_TASK_QUEUE_LENGTH 740
#define LWA_MS_TASK_QUEUE_TIMEOUT 6 /* timeout in seconds. */
                                    /* slightly longer so ms_mcic always times out before ms_exec */ 

/* === message queue === */

size_t LWA_msz() {
  /* returns size of mq_struc structure, minus sid field, */
  /* for use in message queue commands */
  //struct mq_struct mqs;
  struct LWA_cmd_struct mqs;
  return sizeof(mqs) - sizeof(mqs.sid);
  }

/* === time === */

void LWA_timeval( 
                 struct timeval *tv, /* time as a timeval struct */
                 long int *mjd,      /* MJD */
                 long int *mpm       /* MPM */  
                 ) {
  /* converts a timeval to MJD and MPM */
  struct tm *tm;      /* from sys/time.h */
  long int a,y,m,p,q;
  
  tm = gmtime(&(tv->tv_sec));
  //printf("LWA_timeval: %02d:%02d:%02d %ld\n", tm->tm_hour, tm->tm_min, tm->tm_sec,           
  //                                            tv->tv_usec);

  /* construct the MJD field */
  /* adapted from http://paste.lisp.org/display/73536 */
  /* can check result using http://www.csgnetwork.com/julianmodifdateconv.html */
  a = (14 - tm->tm_mon) / 12; 
  y = ( tm->tm_year + 1900) + 4800 - a; // tm->tm_year is the number of years since 1900
  m = ( tm->tm_mon + 1) + (12 * a) - 3; // tm->tm_mon is number of months since Jan (0..11)
  p = tm->tm_mday + (((153 * m) + 2) / 5) + (365 * y); 
  q = (y/4) - (y/100) + (y/400) - 32045; 
  *mjd = (p+q) - 2400000.5;

  *mpm = ( (tm->tm_hour)*3600 + (tm->tm_min)*60 + (tm->tm_sec) ) * 1000
                    + (tv->tv_usec)/1000 ; 

  return;
  } /* LWA_timeval() */


void LWA_time2tv( 
               struct timeval *tv,
               long int mjd, /* MJD */
               long int mpm  /* MPM */  
               ) {
  /* gets current time; returns MJD and MPM, returns the associated timeval */
  /* essentially, this is LWA_timeval() in reverse */

  struct timeval tv_ref;  /* from sys/time.h */
  struct timezone tz;     /* set but useless; see notes below */
  long int mjd_ref;
  long int mpm_ref;
  long int nmd;
  long int dmpm;
  long int dsec;

  /* get the current tv, and the associated MJD and MPM */
  gettimeofday( &tv_ref, &tz );     /* tz is set, but useless; see notes below */
  LWA_timeval( &tv_ref, &mjd_ref, &mpm_ref ); /* determine MPM, MJD */
  
  /* Figure out dmpm, the (signed) number of milliseconds between */
  /* MJD/MPM and the reference time */
  nmd = 24 * 3600 * 1000; /* number of milliseconds in a day */
                          /* does not account for skip seconds, etc... */
  if ( mjd = mjd_ref ) { dmpm =                       mpm - mpm_ref;           }
  if ( mjd > mjd_ref ) { dmpm = (mjd-mjd_ref-1)*nmd + mpm + ( nmd - mpm_ref ); }
  if ( mjd < mjd_ref ) { dmpm = (mjd_ref-mjd-1)*nmd + mpm_ref + ( nmd - mpm ); }
    
  dsec = dmpm/999; /* dividing by 999 as opposed to 1000 solves a problem */
  tv->tv_sec  = tv_ref.tv_sec  + (time_t)      dsec; 
  tv->tv_usec = ( ( tv_ref.tv_usec + (suseconds_t) (dmpm-(dsec*1000))*1000 ) / 1000 )*1000;

  //printf("%ld %ld %ld\n",dmpm,dsec,(dmpm-(dsec*1000))*1000);

  return;
  } /* LWA_time2tv() */


void LWA_time( 
               long int *mjd,      /* MJD */
               long int *mpm       /* MPM */  
               ) {
  /* gets current time; returns MJD and MPM */

  struct timeval tv;  /* from sys/time.h */
  struct timezone tz; /* set but useless; see notes below */

  gettimeofday( &tv, &tz );     /* tz is set, but useless; see notes below */
  LWA_timeval( &tv, mjd, mpm ); /* determine MPM, MJD */
  //printf("%ld %ld\n",mjd,mpm);
  
  return;
  } /* LWA_time() */


/* === utility === */

void LWA_raw2hex( char *raw, char *hex, int n ) {
  /* creates a string hex[ 0 .. 2*n ] (including \0) which is the printable */
  /* hex represenation of the bytes raw[ 0 .. n-1 ] */

  int i;
  for (i=0; i<n; i++) {
    sprintf( &(hex[2*i]), "%02x", (unsigned char) raw[i] );  
    }
  hex[2*n] = '\0';   

  return;
  } /* LWA_raw2hex() */


int LWA_isMCSRSVD(char *label) {
  /* returns 1 if first characters of label correspond to an MCS-RESERVED MIB entry; */
  /* otherwise, 0 */
  int b = 0;
  if (!strcmp(label,"SUMMARY"))   { b=1; }
  if (!strcmp(label,"INFO"))      { b=1; }
  if (!strcmp(label,"LASTLOG"))   { b=1; }
  if (!strcmp(label,"SUBSYSTEM")) { b=1; }
  if (!strcmp(label,"SERIALNO"))  { b=1; }
  if (!strcmp(label,"VERSION"))   { b=1; }
  return b;
  } /* LWA_isMCSRSVD() */


//==================================================================================
//=== HISTORY ======================================================================
//==================================================================================
// Aug 25, 2009: Got rid of "subslot" field
// Aug 17, 2009: Added LWA_isMCSRSVD()
// Aug 16, 2009: Added LWA_raw2hex(); added datalen to LWA_cmd_struct
// Aug 15, 2009: Revising codes used in type_dbm and type_icd
// Jul 31, 2009: Added LWA_MS_TASK_QUEUE_TIMEOUT
//               Separated out LWA_MCS_subsystems.h (svn rev 17)
// Jul 30, 2009: Minor changes/fixes (svn rev 16)
// Jul 30, 2009: (svn rev 15)
// Jul 28, 2009: Attempting to straighten out timekeeping:
//               time_t replacing explicit typing (long ints)
//               gmtime() replacing localtime()               (svn rev 12)
//               added LWA_time2tv(); fixed time-related bugs (svn rev 13)
// Jul 28, 2009: (svn rev 11)
// Jul 26, 2009: Fleshing out LWA_getsum(), added LWA_MIBERR_*
//               Swapping index and label for use in dbm files (svn rev 10)
// Jul 24, 2009: Added LWA_getsum() (svn rev 9)
// Jul 24, 2009: Added LWA_time() (svn rev 8)
// Jul 23, 2009: Added LWA_sid2str(), LWA_cmd2str(), LWA_timeval() functions (svn rev 7)
// Jul 20, 2009: Modified LWA_cmd_struct to include a timeval struct field
// Jul 17, 2009: Removed "mq_struct", replaced with LWA_cmd_struct
// Jul 13, 2009: Renamed "LWA_MCS.h" (was "mib.h")

//==================================================================================
//=== NOTES ========================================================================
//==================================================================================
//
// Program "ME" Codes
// 1 ms_init.c
// 2 ms_exec.c
// 3 ms_mcic1.c (MCS Common ICD Client, frontend) -- depricated
// 4 ms_mcic2.c (MCS Common ICD Client, backend) -- depricated
// 5 dat2dbm.c
// 6 ms_mcic.c  (MCS Common ICD Client, replaces 3 and 4)
// 7 msei.c  
// 8 ms_mdr.c  (MCS/Scheduler MIB dbm-file reader)
// 9 ms_mdre.c (MCS/Scheduler MIB dbm-file reader for entries)
// 10 ms_makeMIB_ASP.c 
// 11 ms_makeMIB_DP.c 

//==================================================================================
//=== TO DO LIST ===================================================================
//==================================================================================


//==================================================================================
//=== NOTES ========================================================================
//==================================================================================

