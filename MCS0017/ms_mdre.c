// ms_mdre.c: S.W. Ellingson, Virginia Tech, 2009 Aug 16
// ---
// COMPILE: gcc -o ms_mdre -I/usr/include/gdbm ms_mdr.c -lgdbm_compat -lgdbm
// In Ubuntu, needed to install package libgdbm-dev
// ---
// COMMAND LINE: ms_mdre <subsystem> <MIB_label>
//   <subsystem> is the 3-character subsystem designator 
//   <MIB_label> is the alphanumeric label identifying the MIB entry 
// ---
// REQUIRES: 
//   LWA_MCS.h
//   dbm database representing MIB for indicated subsystem must exist
//     perhaps generated using dat2dbm
// ---
// MCS/Scheduler MIB dbm-file reader for entries
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

#define MY_NAME "ms_mdre (v.20090816.1)"
#define ME "9" 

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
  if (narg>2) { 
      //printf("[%s/%d] label <%s> specified\n",ME,getpid(),argv[2]);
      sprintf(label,"%s",argv[2]);
    } else {
      printf("[%s/%d] FATAL: MIB label not specified\n",ME,getpid());
      exit(EXIT_FAILURE);
    } 

  /*======================================*/
  /*=== Initialize: dbm file =============*/
  /*======================================*/

  /* Open dbm file */
  dbm_ptr = dbm_open(dbm_filename, O_RDONLY);
  if (!dbm_ptr) {
    printf("[%s/%d] FATAL: Failed to open dbm <%s>\n",ME,getpid(),dbm_filename);
    exit(EXIT_FAILURE);
    }

  sprintf(key,"%s",label);
  datum_key.dptr = key;
  datum_key.dsize = strlen(key);
  datum_data = dbm_fetch(dbm_ptr,datum_key);
  if (datum_data.dptr) {
      memcpy( &record, datum_data.dptr, datum_data.dsize );
      //strncpy(ip_address,record.val,15);
    } else {
      printf("[%s/%d] Failed to find label=<%s> in dbm.\n", ME, getpid(),label);
      exit(EXIT_FAILURE);
    }

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
    //i1u.b = record.val[0];           /* unpack the bytes into a union structure */
    //sprintf(record.val,"%c\0",i1u.i); /* overwrite in human-readable representation */    
    //printf("[%s/%d] Not expecting to see i1u as a type_dbm.  Treating as raw.\n",ME,getpid());
    //strcpy(record.val,"@\0");              /* just print "@" instead */
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

  //printf( "%-s %-s %-s |", record.index, label, record.val );
  printf( "%-s\n", record.val );

  /* convert, show time of last change */
  tv = record.last_change;
  tm = gmtime(&tv.tv_sec);
  printf("%02d%02d%02d %02d:%02d:%02d\n", (tm->tm_year)-100, (tm->tm_mon)+1, tm->tm_mday, tm->tm_hour, tm->tm_min, tm->tm_sec);

  /* Close dbm file */
  dbm_close(dbm_ptr);

  //printf("[%s/%d] exit(EXIT_SUCCESS)\n",ME,getpid());
  exit(EXIT_SUCCESS);
  } /* main() */


//==================================================================================
//=== HISTORY ======================================================================
//==================================================================================
// ms_mdre.c: S.W. Ellingson, Virginia Tech, 2009 Aug 16
//   .1: Dealing with unprintable fields -- integers now get printed
// ms_mdre.c: S.W. Ellingson, Virginia Tech, 2009 Aug 15
//   .1: Dealing with unprintable fields
// ms_mdre.c: S.W. Ellingson, Virginia Tech, 2009 Aug 02
//   .1: Initial version, adapted from ms_mdr.c (svn rev 23)
// ms_mdr.c: S.W. Ellingson, Virginia Tech, 2009 Aug 02
//   .1: Working on formatting
// ms_mdr.c: S.W. Ellingson, Virginia Tech, 2009 Jul 26 
//   .1: Very first version, adapted from segments of ms_mcic.c
//   .2: Implementing index/label swap in dbm database (svn rev 10)

//==================================================================================
//=== BELOW THIS LINE IS SCRATCH ===================================================
//==================================================================================

