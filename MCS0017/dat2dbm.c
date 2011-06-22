// dat2dbm.c: S.W. Ellingson, Virginia Tech, 2009 Aug 16
// ---
// COMPILE: gcc -o dat2dbm -I/usr/include/gdbm dat2dbm.c -lgdbm_compat -lgdbm
// In Ubuntu, needed to install package libgdbm-dev
// ---
// COMMAND LINE: dat2dbm <MIB_init_file> <ip_address> <tx-port> <rx-port>
//   <MIB_init_file> subsystem MIB initialization ".dat" file 
//   <ip_address> IP address (in "dotted quad" form) for subsystem; appended to MIB dbm
//   <tx-port> transmit port for subsystem; appended to MIB dbm
//   <rx-port> transmit port for subsystem; appended to MIB dbm
// ---
// REQUIRES: 
//   LWA_MCS.h
// ---
// Creates a "dbm" database from a subsystem MIB initialization ".dat" file 
// See end of this file for history.

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <gdbm-ndbm.h>

#include "LWA_MCS.h" 

#define MY_NAME "dat2dbm (v.20090816.2)"
#define ME "5" 

main ( int narg, char *argv[] ) {

  /*=================*/
  /*=== Variables ===*/
  /*=================*/

  char dat_filename[256];
  char ip_address[20];
  int tx_port;
  int rx_port;

  FILE* fid_dat; 

  char line_type[ 2];   
  char index[MIB_INDEX_FIELD_LENGTH];     
  char label[MIB_LABEL_FIELD_LENGTH];      /* this becomes the key for dbm */
  char val[256];
  char type_dbm[6];
  char type_icd[6];

  /* dbm-related variables */
  char dbm_filename[256];
  DBM *dbm_ptr;
  struct dbm_record record;
  datum datum_key;
  datum datum_data;

  int result;

  struct timezone tz; /* from sys/time.h; included in LWA_MCS.h */

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

  /*==================*/
  /*=== Initialize ===*/
  /*==================*/

  /* First, announce thyself */
  printf("[%s] I am %s\n",ME,MY_NAME);

  /* --- Process command line arguments ---*/

  if (narg>1) { 
    sprintf(dat_filename,"%s_MIB_init.dat",argv[1]);
    //printf("dat_filename: <%s>\n",dat_filename);
    }
    else {
    printf("[%s] FATAL: dat_filename not provided\n",ME);
    exit(EXIT_FAILURE);
    } 

  if (narg>2) { 
    strcpy(ip_address,argv[2]);
    //printf("ip_address: <%s>\n",ip_address);
    }
    else {
    printf("[%s] FATAL: ip_address not provided\n",ME);
    exit(EXIT_FAILURE);
    }

  if (narg>3) { 
    sscanf(argv[3],"%d",&tx_port);
    //printf("tx_port: %d\n",tx_port);
    }
    else {
    printf("[%s] FATAL: tx_port not provided\n",ME);
    exit(EXIT_FAILURE);
    }

  if (narg>4) { 
    sscanf(argv[4],"%d",&rx_port);
    //printf("rx_port: %d\n",rx_port);
    }
    else {
    printf("[%s] FATAL: rx_port not provided\n",ME);
    exit(EXIT_FAILURE);
    }

  /*--- Open dat file --- */

  fid_dat = fopen(dat_filename,"r");
  if (!fid_dat) { 
    printf("[%s] FATAL: Can't read file <%s>\n",ME,dat_filename); 
    exit(EXIT_FAILURE); 
    }  
 
  /* Construct filename for dbm file */
  memset( dbm_filename,'\0',sizeof(dbm_filename)); /* avoids problem with next line: */  
  strncpy(dbm_filename,dat_filename,3);
  //printf("|%s|\n",dbm_filename);

  /* Open dbm file */
  dbm_ptr = dbm_open(dbm_filename, O_RDWR | O_CREAT | O_TRUNC, 0666);
  /*                                        ^-- create if it doesn't already exist */
  /*                                                  ^-- zero it if it does already exit */
  if (!dbm_ptr) {
    printf("[%s] FATAL: Failed to open database\n",ME);
    exit(EXIT_FAILURE);
    }

  /*==================*/
  /*=== Main Loop ====*/
  /*==================*/
  /* Read dat line-by-line, taking action as each line is read. */

  while (!feof(fid_dat)) {

    /* read next line */
    fscanf(fid_dat,"%1s %s %s %s %s %s\n",
      line_type,
      index,
      label,
      val,
      type_dbm,
      type_icd);
    //printf("|%s|%s|%s|%s|%s|%s|\n",
    //  line_type,
    //  index,
    //  label,
    //  val,
    //  type_dbm,
    //  type_icd);

    /* Fill up space with string nulls to avoid problems with strings */
    memset( &record,   '\0', sizeof(record) );
    //memset( keystring, '\0', sizeof(keystring));
    //strncpy(keystring,index,strlen(index));

    if (!strcmp(line_type,"B")) { 
      record.eType = MIB_REC_TYPE_BRANCH;
      } else {
      record.eType = MIB_REC_TYPE_VALUE;
      }
    strcpy( record.index,    index     );

    /* Stuffing record.val: Depends on type_dbm: */
    if (!strncmp(type_dbm,"NUL",3)) {        /* if it's "NUL", just say so */
      strcpy( record.val,      val       );  
      }
    if (!strncmp(type_dbm,"a",1)) {          /* if it's printable, do so */
      strcpy( record.val,      val       );  
      }
    if (!strncmp(type_dbm,"r",1)) {          /* if it's raw: */
      /* nothing to do; just let it remain "\0" */ 
      }
    if (!strncmp(type_dbm,"i1u",3)) {        /* save as a uint8 */
      ///* just let it remain "\0" */ 
      //printf("[%s] Not expecting to see i1u as a type_dbm.  Doing nothing.\n",ME);
      sscanf(val,"%hu",&(i2u.i));   /* get as an unsigned short int */
      record.val[0] = i2u.b[0];     /* raw-write low-order byte into the string array */
      }
    if (!strncmp(type_dbm,"i2u",3)) {        /* save as a uint16 */
      ///* just let it remain "\0" */ 
      //printf("[%s] Not expecting to see i2u as a type_dbm.  Doing nothing.\n",ME);
      sscanf(val,"%hu",&(i2u.i));   /* get as a unit16 */
      record.val[0] = i2u.b[0];    /* raw-write into the string array */
      record.val[1] = i2u.b[1];
      }
    if (!strncmp(type_dbm,"i4u",3)) {        /* save as a uint32 */
      ///* just let it remain "\0" */ 
      //printf("[%s] Not expecting to see i4u as a type_dbm.  Doing nothing.\n",ME);
      sscanf(val,"%u",&(i4u.i));   /* get as a unit32 */
      record.val[0] = i4u.b[0];    /* raw-write into the string array */
      record.val[1] = i4u.b[1];
      record.val[2] = i4u.b[2];
      record.val[3] = i4u.b[3];
      }
    if (!strncmp(type_dbm,"f4",2)) {         /* save as a float32 */
      sscanf(val,"%f",&(f4.f));   /* get as a float32 */
      record.val[0] = f4.b[0];    /* raw-write into the string array */
      record.val[1] = f4.b[1];
      record.val[2] = f4.b[2];
      record.val[3] = f4.b[3];
      }

    gettimeofday(&record.last_change,&tz); 

    strcpy( record.type_dbm, type_dbm  );
    strcpy( record.type_icd, type_icd  );

    datum_key.dptr   = (void *)label;
    datum_key.dsize  = strlen(label);
    datum_data.dptr  = (void *) &record;
    datum_data.dsize = sizeof(struct dbm_record); 

    result = dbm_store( dbm_ptr, datum_key, datum_data, DBM_REPLACE);
    if (result != 0) {
      printf("[%s] FATAL: dbm_store failed on key <%s>\n",ME,label);
      exit(EXIT_FAILURE);
      }

    } /* while (!feof(fid_dat)) */

  /* Close dat file */
  close(fid_dat);
  
  /*===============================================*/
  /*=== Adding in ip_address, tx_port, rx_port ====*/
  /*===============================================*/

  /* add IP address as INDEX="0.1", label="MCH_IP_ADDRESS", type_dbm="a15", type_icd="NUL" */
  memset( &record, '\0', sizeof(record) );
  record.eType = MIB_REC_TYPE_VALUE;  
  strcpy( record.index, "0.1");
  strcpy( record.val,   ip_address  );
  gettimeofday(&record.last_change,&tz); 
  strcpy( record.type_dbm, "a15" );
  strcpy( record.type_icd, "NUL" );
  strcpy( label, "MCH_IP_ADDRESS" ); //printf("index <%s>\n",index);
  datum_key.dptr   = (void *)label;
  datum_key.dsize  = strlen(label);
  datum_data.dptr  = (void *) &record;
  datum_data.dsize = sizeof(struct dbm_record); 
  result = dbm_store( dbm_ptr, datum_key, datum_data, DBM_REPLACE);
  if (result != 0) {
    printf("[%s] FATAL: dbm_store failed to store ip_address <%s>\n",ME,ip_address);
    exit(EXIT_FAILURE);
    }

  /* add tx_port as INDEX="0.2", label="MCH_TX_PORT", type_dbm="a5", type_icd="NUL" */
  memset( &record, '\0', sizeof(record) );
  record.eType = MIB_REC_TYPE_VALUE;  
  strcpy( record.index, "0.2");
  sprintf( record.val, "%d", tx_port  );
  gettimeofday(&record.last_change,&tz); 
  strcpy( record.type_dbm, "a5" );
  strcpy( record.type_icd, "NUL" );
  strcpy( label, "MCH_TX_PORT" ); //printf("index <%s>\n",index);
  datum_key.dptr   = (void *)label;
  datum_key.dsize  = strlen(label);
  datum_data.dptr  = (void *) &record;
  datum_data.dsize = sizeof(struct dbm_record); 
  result = dbm_store( dbm_ptr, datum_key, datum_data, DBM_REPLACE);
  if (result != 0) {
    printf("[%s] FATAL: dbm_store failed to store tx_port <%d>\n",ME,tx_port);
    exit(EXIT_FAILURE);
    }

  /* add rx_port as INDEX="0.3", label="MCH_RX_PORT", type_dbm="a5", type_icd="NUL" */
  memset( &record, '\0', sizeof(record) );
  record.eType = MIB_REC_TYPE_VALUE;  
  strcpy( record.index, "0.3");
  sprintf( record.val, "%d", rx_port  );
  gettimeofday(&record.last_change,&tz); 
  strcpy( record.type_dbm, "a5" );
  strcpy( record.type_icd, "NUL" );
  strcpy( label, "MCH_RX_PORT" ); //printf("index <%s>\n",index);
  datum_key.dptr   = (void *)label;
  datum_key.dsize  = strlen(label);
  datum_data.dptr  = (void *) &record;
  datum_data.dsize = sizeof(struct dbm_record); 
  result = dbm_store( dbm_ptr, datum_key, datum_data, DBM_REPLACE);
  if (result != 0) {
    printf("[%s] FATAL: dbm_store failed to store rx_port <%d>\n",ME,rx_port);
    exit(EXIT_FAILURE);
    }

  /* Close dbm file */
  dbm_close(dbm_ptr);

  printf("[%s] exit(EXIT_SUCCESS)\n",ME); 
  exit(EXIT_SUCCESS);
  } /* main() */

//==================================================================================
//=== HISTORY ======================================================================
//==================================================================================
// dat2dbm.c: S.W. Ellingson, Virginia Tech, 2009 Aug 16
//   .1 Adding support for non-printable fields in dbm file
//   .2 Adding more support for non-printable fields (namely, integers)
// dat2dbm.c: S.W. Ellingson, Virginia Tech, 2009 Jul 26
//   .1 Implementing swap of index and label for dbm key (svn rev 10)
// dat2dbm.c: S.W. Ellingson, Virginia Tech, 2009 Jul 21
//   .1 adding command line arguments for socket communications
// dat2dbm.c: S.W. Ellingson, Virginia Tech, 2009 Jul 13
//   .1 brought into common codeset; mib.h -> LWA_MCS.h
// dat2dbm.c: S.W. Ellingson, Virginia Tech, 2009 Jul 04 

//==================================================================================
//=== dat file format ==============================================================
//==================================================================================
// Columns are:
//   "B" for branch, "V" for value
//   MIB index
//   MIB label
//   value for initialization: branches should be "NUL", "UNK" means unknown.
//   format for local database: (see LWA_MCS.h for explanation)
//   format for MCS ICD exchanges: (see LWA_MCS.h for explanation)
