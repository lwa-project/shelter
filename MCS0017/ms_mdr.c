// ms_mdr.c: S.W. Ellingson, Virginia Tech, 2009 Aug 16
// ---
// COMPILE: gcc -o ms_mdr -I/usr/include/gdbm ms_mdr.c -lgdbm_compat -lgdbm
// In Ubuntu, needed to install package libgdbm-dev
// ---
// COMMAND LINE: ms_mdr <subsystem>
//   <subsystem> is the 3-character subsystem designator 
// ---
// REQUIRES: 
//   LWA_MCS.h
//   dbm database representing MIB for indicated subsystem must exist
//     perhaps generated using dat2dbm
// ---
// MCS/Scheduler MIB dbm-file reader
// Note about values: what is shown depends on type_dbm:
//   NUL is shown as "NUL"
//   a#### is shown as is
//   r#### is shown as "@...."
//   i1u, i2u, and i4u are shown as "@", "@@" and "@@@@" respectively
//   f4 is shown as a human-readable float
// See end of this file for history.

#include <stdlib.h> /* needed for exit(); possibly other things */
#include <stdio.h>

#include <string.h>
#include <fcntl.h> /* needed for O_READONLY; perhaps other things */
#include <gdbm-ndbm.h>

#include "LWA_MCS.h" 

#define MY_NAME "ms_mdr (v.20090816.1)"
#define ME "8" 

main ( int narg, char *argv[] ) {

  /*=================*/
  /*=== Variables ===*/
  /*=================*/

  /* dbm-related variables */
  char dbm_filename[256];
  DBM *dbm_ptr;
  struct dbm_record record;
  datum datum_key;
  datum datum_data;

  struct timeval tv;  /* from sys/time.h; included via LWA_MCS.h */
  struct tm *tm;      /* from sys/time.h; included via LWA_MCS.h */

  char label[MIB_LABEL_FIELD_LENGTH];     /* this is the key for dbm */
  char key[MIB_LABEL_FIELD_LENGTH];

  char display[33];

  union {
    unsigned short int i;
    unsigned char b[2];
    } i2u;
  union {
    unsigned int i;
    unsigned char b[4];
    } i4u;
  union {
    float f;
    unsigned char b[4];
    } f4;

  /*======================================*/
  /*=== Initialize: Command line stuff ===*/
  /*======================================*/
    
  /* First, announce thyself */
  //printf("[%s/%d] I am %s \n",ME,getpid(),MY_NAME);

  /* Process command line arguments */
  if (narg>1) { 
      //printf("[%s/%d] %s specified\n",ME,getpid(),argv[1]);
      sprintf(dbm_filename,"%s",argv[1]);
    } else {
      printf("[%s/%d] FATAL: subsystem not specified\n",ME,getpid());
      exit(EXIT_FAILURE);
    } 

  //sid = LWA_getsid(argv[1]); /* get subsystem ID */
  //printf("[%s/%d] sid=%d\n",ME,getpid(),sid);

  /*======================================*/
  /*=== Initialize: dbm file =============*/
  /*======================================*/

  /* Open dbm file */
  dbm_ptr = dbm_open(dbm_filename, O_RDONLY);
  if (!dbm_ptr) {
    printf("[%s/%d] FATAL: Failed to open dbm <%s>\n",ME,getpid(),dbm_filename);
    exit(EXIT_FAILURE);
    }

  /* === Read dbm record-by-record === */
  for (
           datum_key = dbm_firstkey(dbm_ptr);
           datum_key.dptr;
           datum_key = dbm_nextkey(dbm_ptr)
        ) {

    /* read next line */
    datum_data = dbm_fetch(dbm_ptr,datum_key);

    memcpy( &record, datum_data.dptr, datum_data.dsize );

    memset( label, '\0', sizeof(label));
    strncpy(label,datum_key.dptr,datum_key.dsize);
    //printf(">%s|",label);
    printf("%-32s ",label);

    /* Decide how to show record.val: This depends on record.type_dbm: */
    if (!strncmp(record.type_dbm,"NUL",3)) { /* if the format is "NUL" (e.g., branch entries)... */
      strcpy(record.val,"NUL\0");            /* print "NUL" for value */
      }
    if (!strncmp(record.type_dbm,"a",1)) { 
                                             /* do nothing; fine the way it is */
      }    
    if (!strncmp(record.type_dbm,"r",1)) {   /* if the field is not printable... */
      strcpy(record.val,"@...\0");           /* just print "@" instead */
      }
    if (!strncmp(record.type_dbm,"i1u",3)) {  /* if the format is "i1u" */    
      //printf("[%s/%d] Not expecting to see i1u as a type_dbm.  Treating as raw.\n",ME,getpid());
      //strcpy(record.val,"@\0");              /* just print "@" instead */
      //i1u.b=record.val[0];           /* unpack the bytes into a union structure */
      //sprintf(record.val,"%hu\0",i1u.i); /* overwrite in human-readable representation */ 
      i2u.b[0]=record.val[0];           /* unpack the bytes into a union structure */
      i2u.b[1]=0;
      sprintf(record.val,"%hu\0",i2u.i); /* overwrite in human-readable representation */ 
      }
    if (!strncmp(record.type_dbm,"i2u",3)) {  /* if the format is "i2u" */   
      //printf("[%s/%d] Not expecting to see i2u as a type_dbm.  Treating as raw.\n",ME,getpid());
      //strcpy(record.val,"@@\0");              /* just print "@@" instead */
      i2u.b[0]=record.val[0];           /* unpack the bytes into a union structure */
      i2u.b[1]=record.val[1];
      sprintf(record.val,"%hu\0",i2u.i); /* overwrite in human-readable representation */ 
      }
    if (!strncmp(record.type_dbm,"i4u",3)) {  /* if the format is "i4u" */   
      //printf("[%s/%d] Not expecting to see i4u as a type_dbm.  Treating as raw.\n",ME,getpid());
      //strcpy(record.val,"@@@@\0");              /* just print "@@@@" instead */
      i4u.b[0]=record.val[0];           /* unpack the bytes into a union structure */
      i4u.b[1]=record.val[1];
      i4u.b[2]=record.val[2];
      i4u.b[3]=record.val[3];
      sprintf(record.val,"%u\0",i4u.i); /* overwrite in human-readable representation */  
      }
    if (!strncmp(record.type_dbm,"f4",2)) {  /* if the format is "f4" */
      f4.b[0]=record.val[0];           /* unpack the bytes into a union structure */
      f4.b[1]=record.val[1];
      f4.b[2]=record.val[2];
      f4.b[3]=record.val[3];
      sprintf(record.val,"%f\0",f4.f); /* overwrite in human-readable representation */    
      }

    //printf("%d|%s|%s|%s|%s|",
    //  record.eType,
    //  record.index,
    //  record.val,
    //  record.type_dbm,
    //  record.type_icd);
    //printf(" %-1d %-12s %-32s %-6s %-6s ",
    //  record.eType,
    //  record.index,
    //  record.val,
    //  record.type_dbm,
    //  record.type_icd);
    printf("%-1d ", record.eType);
    strncpy(display,record.index,    11); printf("%-12s ",display);
    strncpy(display,record.val,      31); printf("%-32s ",display);
    strncpy(display,record.type_dbm,  6); printf("%-6s ", display); 
    strncpy(display,record.type_icd,  6); printf("%-6s ", display); 

    /* convert, show time of last change */
    tv = record.last_change;
    tm = gmtime(&tv.tv_sec);
    printf("|%02d%02d%02d %02d:%02d:%02d\n", (tm->tm_year)-100, (tm->tm_mon)+1, tm->tm_mday, tm->tm_hour, tm->tm_min, tm->tm_sec);

    } /* for () */

  /* Close dbm file */
  dbm_close(dbm_ptr);

  printf("[%s/%d] exit(EXIT_SUCCESS)\n",ME,getpid());
  exit(EXIT_SUCCESS);
  } /* main() */


//==================================================================================
//=== HISTORY ======================================================================
//==================================================================================
// ms_mdr.c: S.W. Ellingson, Virginia Tech, 2009 Aug 16
//   .1: Dealing with unprintable fields -- now integers get printed
// ms_mdr.c: S.W. Ellingson, Virginia Tech, 2009 Aug 15
//   .1: Dealing with unprintable fields 
// ms_mdr.c: S.W. Ellingson, Virginia Tech, 2009 Aug 02
//   .1: Working on formatting (svn rev 23)
// ms_mdr.c: S.W. Ellingson, Virginia Tech, 2009 Jul 26 
//   .1: Very first version, adapted from segments of ms_mcic.c
//   .2: Implementing index/label swap in dbm database (svn rev 10)

//==================================================================================
//=== BELOW THIS LINE IS SCRATCH ===================================================
//==================================================================================

