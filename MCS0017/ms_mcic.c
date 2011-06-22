// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Aug 25
// ---
// COMPILE: gcc -o ms_mcic -I/usr/include/gdbm ms_mcic.c -lgdbm_compat -lgdbm
// In Ubuntu, needed to install package libgdbm-dev
// ---
// COMMAND LINE: ms_mcic <subsystem>
//   <subsystem> is the 3-character subsystem designator 
// ---
// REQUIRES: 
//   LWA_MCS.h
//   ms_mcic_mib.c
//   dbm database representing MIB for indicated subsystem must exist
//     perhaps generated using dat2dbm
// ---
// MCS/Scheduler MCS Common ICD Client Process
// This is decended from and replaces ms_mcic1.c and mc_mcic2.c
// See end of this file for history.

#include <stdlib.h>
#include <stdio.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <netinet/in.h> /* for network sockets */
#include <arpa/inet.h>  /* for network sockets */

#include <string.h>
#include <fcntl.h>
#include <gdbm-ndbm.h>

#include <sys/msg.h>

#include "LWA_MCS.h" 

#define MY_NAME "ms_mcic (v.20090825.1)"
#define ME "6" 

/* Things that should eventually be obtained from a .h file */
#define B         8192            /* [bytes] Max message size */
#define R_SUMMARY_STRING_LENGTH 8


#define LWA_PTQ_MAX_DATA_FIELD_LENGTH 256 
/* This is used to avoid copying mammoth DATA fields to the pending task queue */


#include "ms_mcic_mib.c" /* this must follow all other macro defines; */
                         /* especially those for MY_NAME and ME */

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
  struct timezone tz; /* set but useless */
  struct tm *tm;      /* from sys/time.h; included via LWA_MCS.h */

  char key[MIB_LABEL_FIELD_LENGTH];

  int mqtid;          /* transmit (to ms_init or ms_exec) message queue */
  int mqrid;          /* receive (from ms_init or ms_exec) message queue */
  //struct mq_struct mq_msg;
  struct LWA_cmd_struct mq_msg;

  int sid;            /* subsystem ID (see LWA_MCS.h) */

  key_t mqrkey;       /* key for receive message queue */

  char ip_address[15];
  int tx_port;
  int rx_port;

  int sfdt;                    /* transmit socket file discriptor */
  struct sockaddr_in addresst; /* transmit address */
  int sfdr;                    /* receive socket file discriptor */
  struct sockaddr_in addressr; /* receive address */
  int eResult;

  /* probably left over stuff...*/
  int len;
  char message_string[B];

  long int mjd;
  long int mpm;

  char dest[4]; //3
  char sids[4]; //3
  char cids[4]; //3
  long int ref;
  char r_response[2]; //1
  char r_summary[R_SUMMARY_STRING_LENGTH]; //7
  char data[B];

  char cmdata[LWA_PTQ_MAX_DATA_FIELD_LENGTH];

  int result;

  /* PTQ = pending task queue; used to keep track of DATA and time-sent */
  /* for outbound command messages, as a function of REFERENCE */
  long int       ptq_ref[ LWA_PTQ_SIZE];
  struct timeval ptq_tv[  LWA_PTQ_SIZE];
  char           ptq_data[LWA_PTQ_SIZE][LWA_PTQ_MAX_DATA_FIELD_LENGTH];
  int ptq_ptr;
  int ptq_ptr_end;
  int eDone;

  int i;

  char hex[B];

  /*======================================*/
  /*=== Initialize: Command line stuff ===*/
  /*======================================*/
    
  /* First, announce thyself */
  printf("[%s/%d] I am %s \n",ME,getpid(),MY_NAME);

  /* Process command line arguments */
  if (narg>1) { 
      printf("[%s/%d] %s specified\n",ME,getpid(),argv[1]);
      sprintf(dbm_filename,"%s",argv[1]);
    } else {
      printf("[%s/%d] FATAL: subsystem not specified\n",ME,getpid());
      exit(EXIT_FAILURE);
    } 

  sid = LWA_getsid(argv[1]); /* get subsystem ID */
  //printf("[%s/%d] sid=%d\n",ME,getpid(),sid);

  /*======================================*/
  /*=== Initialize: dbm file =============*/
  /*======================================*/
  /* Open, get ip_address, tx_port, rx_port */

  /* Open dbm file */
  dbm_ptr = dbm_open(dbm_filename, O_RDONLY);
  if (!dbm_ptr) {
    printf("[%s/%d] FATAL: Failed to open dbm <%s>\n",ME,getpid(),dbm_filename);
    exit(EXIT_FAILURE);
    }

  /* Pulling IP_ADDRESS out of dbm file */
  //printf("[%s/%d] Seeking IP_ADDRESS in dbm file:\n",ME,getpid());
  sprintf(key,"MCH_IP_ADDRESS");
  datum_key.dptr = key;
  datum_key.dsize = strlen(key);
  datum_data = dbm_fetch(dbm_ptr,datum_key);
  if (datum_data.dptr) {
      memcpy( &record, datum_data.dptr, datum_data.dsize );
      strncpy(ip_address,record.val,15);
      printf("[%s/%d] IP_ADDRESS <%s>\n", ME, getpid(),ip_address);
    } else {
      printf("[%s/%d] Failed to find IP_ADDRESS in dbm.\n", ME, getpid());
    }

  /* Pulling TX_PORT out of dbm file */
  sprintf(key,"MCH_TX_PORT");
  datum_key.dptr = key;
  datum_key.dsize = strlen(key);
  datum_data = dbm_fetch(dbm_ptr,datum_key);
  if (datum_data.dptr) {
      memcpy( &record, datum_data.dptr, datum_data.dsize );
      sscanf(record.val,"%d",&tx_port);
      printf("[%s/%d] TX_PORT = %d\n", ME, getpid(),tx_port);
    } else {
      printf("[%s/%d] Failed to find TX_PORT in dbm.\n", ME, getpid());
    }

  /* Pulling RX_PORT out of dbm file */
  sprintf(key,"MCH_RX_PORT");
  datum_key.dptr = key;
  datum_key.dsize = strlen(key);
  datum_data = dbm_fetch(dbm_ptr,datum_key);
  if (datum_data.dptr) {
      memcpy( &record, datum_data.dptr, datum_data.dsize );
      sscanf(record.val,"%d",&rx_port);
      printf("[%s/%d] RX_PORT = %d\n", ME, getpid(),rx_port);
    } else {
      printf("[%s/%d] Failed to find RX_PORT in dbm.\n", ME, getpid());
    }

  /* Close dbm file */
  dbm_close(dbm_ptr);


  /*======================================================*/
  /*=== Initialize: set up sockets interface =============*/
  /*======================================================*/

  /* create receive socket & bind to address */
  sfdr = socket(
                AF_INET,    
                SOCK_DGRAM, /* type (UDP-like) */
                0);         /* protocol (normally 0) */  
  addressr.sin_family = AF_INET;
  addressr.sin_addr.s_addr = htonl(INADDR_ANY);
  addressr.sin_port = htons(rx_port);
  bind( sfdr, (struct sockaddr *) &addressr, sizeof(addressr) );

  /* create transmit socket */
  sfdt = socket(
                AF_INET,    
                SOCK_DGRAM, /* type (UDP-like) */
                0);         /* protocol (normally 0) */
  /* name socket */
  addresst.sin_family = AF_INET;
  addresst.sin_addr.s_addr = inet_addr(ip_address);
  addresst.sin_port = htons(tx_port);


  /*======================================================*/
  /*=== Initialize: set up message queue =================*/
  /*======================================================*/

  mqrkey = MQ_MS_KEY + sid;

  /* Set up for receiving from message queue */
  mqrid = msgget( mqrkey, 0666 | IPC_CREAT );
  if (mqrid==-1) {
    printf("[%s/%d] FATAL: Receive message queue setup failed with code %d\n",ME,getpid(),mqrid);  
    exit(EXIT_FAILURE); 
    }
  /* Clear out message queue */
  while ( msgrcv( mqrid, (void *)&mq_msg, LWA_msz(), 0, IPC_NOWAIT ) > 0 ) ;

  /* Set up transmit message queue */
  mqtid = msgget( (key_t) MQ_MS_KEY, 0666 | IPC_CREAT );
  if (mqtid==-1) {
    printf("[%s/%d] FATAL: Could not msgget() message queue\n",ME,getpid());
    exit(EXIT_FAILURE);
    }
  
  /* Send message to signal I'm up and running */
  mq_msg.sid  = (long int) sid;
  mq_msg.cid = LWA_CMD_PNG;   //was: mq_msg.type = LWA_MTYPE_PING;
  mq_msg.ref  = 0;                /* doesn't matter since this isn't a response */ 
  strcpy(mq_msg.data,"I'm up and running");
  if ( msgsnd( mqtid, (void *)&mq_msg, LWA_msz(), 0) == -1 ) {
    printf("[%s/%d] FATAL: Could not msgsnd()\n",ME,getpid());
    exit(EXIT_FAILURE);
    } 

  /* stall until ms_init responds on the message queue */
  if ( msgrcv( mqrid, (void *)&mq_msg, LWA_msz(), 0, 0) == -1) {
    printf("[%s/%d] FATAL: Could not msgrcv()\n",ME,getpid());
    exit(EXIT_FAILURE);
    }

  /* Respond to PNG from ms_init */
  mq_msg.sid  = (long int) sid;
  mq_msg.cid = LWA_CMD_PNG;
  mq_msg.ref  = 0;                /* doesn't matter since this isn't a response */ 
  strcpy(mq_msg.data,"I saw a PNG");
  if ( msgsnd( mqtid, (void *)&mq_msg, LWA_msz(), 0) == -1 ) {
    printf("[%s/%d] FATAL: Could not msgsnd()\n",ME,getpid());
    exit(EXIT_FAILURE);
    } 


  /*======================================================*/
  /*=== Initialize: Set up pending task queue ============*/
  /*======================================================*/

  for ( i=0; i < LWA_PTQ_SIZE; i++ ) ptq_ref[i] = 0;
  ptq_ptr = 0;


  /*======================================================*/
  /*=== MAIN LOOP ========================================*/
  /*======================================================*/

  while (1) {


    /*======================================================================*/
    /* Check to see if there is anything for us on the message queue (from ms_exec (and don't block) */
    /*======================================================================*/

    if ( msgrcv( mqrid, (void *)&mq_msg, LWA_msz(), 0, IPC_NOWAIT ) > -1) { /* there is a message */

      //printf("[%s/%d] Rcvd: sid=%ld, ref=%ld, cid=%d, subslot=%d, data=<%s> ",ME,getpid(),
      //  mq_msg.sid, mq_msg.ref, mq_msg.cid, mq_msg.subslot, mq_msg.data );
     
      /* First, check to see if this is a request to shut me (as opposed to my subsystem) down */
      if (mq_msg.cid==LWA_CMD_MCSSHT) {
        printf("[%s/%d] Directed to shut down. I'm out...\n",ME,getpid());
        close(sfdr); /* close sockets */
        close(sfdt); 
        /* ms_exec() takes care of message queues */
        exit(EXIT_SUCCESS);      
        }

      /* convert message to MCS Common ICD form */

      LWA_timeval( &(mq_msg.tv), &mjd, &mpm ); /* determine MPM, MJD */
      //LWA_time( &mjd, &mpm ); /* determine MPM, MJD */
      //printf("%ld %ld\n",mjd,mpm);

      if (mq_msg.datalen==-1) { 
          len = strlen(mq_msg.data); /* need this to convert from size_t to int in sprintf() */
        } else {
          len = mq_msg.datalen;
        }
      sprintf( message_string,
               "%3s%3s%3s%9ld%4d%6ld%9ld %s",
               LWA_sid2str(mq_msg.sid), /* %3s DESTINATION */
               "MCS",                   /* %3s SOURCE */
               LWA_cmd2str(mq_msg.cid), /* %3s TYPE */
               mq_msg.ref,              /* %9ld REFERENCE */
               len,                     /* %4d data length */ 
               mjd,                     /* %6ld MJD */
               mpm,                     /* %9ld MPM */
               mq_msg.data              /* %s DATA */
               );
      //printf("sent: <%s> mpm=%ld\n",message_string,mpm);

      /* if "mq_msg.data" was raw binary (i.e., mq_msg.datalen != 1), then */
      /* it may not have copied correctly above.  So, we do it again... */
      if (mq_msg.datalen>0) {
        memcpy( &(message_string[47]), mq_msg.data, mq_msg.datalen ); 
        }

      /* send message to subsystem */
      eResult = sendto( 
                       sfdt, 
                       message_string, strlen(message_string), 
                       MSG_DONTWAIT, 
                       (struct sockaddr *) &addresst, sizeof(addresst)
                      ); 

      /* if sendto() fails, let ms_exec know. Otherwise, no action */
      if ( eResult == -1 ) { /* sendto() failed */

          /* Our response is to tell ms_exec that sendto() failed */
          mq_msg.bAccept  = LWA_MSELOG_TP_FAIL_MCIC;  /* signal a problem */
          mq_msg.eSummary = LWA_SIDSUM_NULL;
          strcpy(mq_msg.data,"sendto() failed");             /* just something to say */
          mq_msg.datalen = -1;
          if ( msgsnd( mqtid, (void *)&mq_msg, LWA_msz(), 0) == -1 ) {
            printf("[%s/%d] WARNING: Could not msgsnd()\n",ME,getpid());
            }    
          //printf("[%s/%d] Responded to task %ld\n",ME,getpid(),mq_msg.ref);

        } else { /* sendto() succeeded */

          /* Don't need to tell ms_exec() anything (success assumed) */

          /* Remember the DATA field and time sent for use in */
          /* dealing with response message, or sensing timeout: */

          /* get next ptq_ptr */
          ptq_ptr_end = ptq_ptr - 1; /* this is the last one we check before */
                                     /* realizing we've checked them all! */
            if (ptq_ptr_end < 0) { ptq_ptr_end = LWA_PTQ_SIZE - 1; }
          eDone = 0;
          while ( eDone == 0 ) {
            ptq_ptr++;
            if ( ptq_ptr >= LWA_PTQ_SIZE ) { ptq_ptr = 0; } /* wrap around */
            if ( ptq_ptr == ptq_ptr_end )  { eDone = 2; }   /* this is it; if not available we're done, but failed */
            if ( ptq_ref[ ptq_ptr ] == 0 ) { eDone = 1; }   /* found a space */
            //printf("[%s/%d] ptq_ptr=%d eDone=%d\n",ME,getpid(), ptq_ptr, eDone );
            } /* while ( eDone == 0 ) */

          if (eDone == 2) { /* we're here because task queue is full */

              printf("[%s/%d] ERRROR: Pending task queue full\n",ME,getpid());
              /* This means we will not recognize response message. 
                 Not a problem except MIB will not be properly updated, and also
                 ms_exec() will hear about it */

            } else { /* we found a place in the queue for this */
  
              /* add current message to the pending task queue */  
              ptq_ref[ ptq_ptr ] = mq_msg.ref;
              //ptq_tv[  ptq_ptr ] = mq_msg.tv;
              gettimeofday( &(ptq_tv[ptq_ptr]), &tz );  /* remember what time this got shipped out */
              strncpy( ptq_data[ ptq_ptr ], mq_msg.data, LWA_PTQ_MAX_DATA_FIELD_LENGTH ); 

            }

        } /* if ( eResult */

      } /* if ( msgrcv( */


    /*======================================================================*/
    /*=== Check for anything via socket from subsystem (and don't block) ===*/
    /*======================================================================*/

    /* Don't do line below! (Causes recvfrom to crash process!) */
    //strcpy(message_string,NULL); /* keep junk from last time from being carried forward */

    /* fill string with nulls so that we dont get confused by stuff left over from last time */
    memset(message_string, '\0', sizeof(message_string)); 
   
    len = sizeof(addressr);
    eResult = recvfrom(
                       sfdr,                            /* socket descriptor */
                       message_string,                  /* buffer */
                       sizeof(message_string),          /* length in bytes of the buffer pointed to by the buffer argument */
                       MSG_DONTWAIT,                    /* flags */
                       (struct sockaddr *) &addressr,   /* A null pointer, or points to a sockaddr structure in which the sending address */
                                                        /* is to be stored. The length and format of the address depend on the address family of the socket. */
                       &len                             /* Specifies the length of the sockaddr structure pointed to by the address argument */
                      );  
    /* http://www.opengroup.org/onlinepubs/007908799/xns/recvfrom.html */
    //printf("[%s/%d] subsystem says <%s>\n",ME,getpid(),message_string);

    //printf("[%s/%d] Mark 3\n",ME,getpid());
    
    /* If we received something from a subsystem, act on it and tell ms_exec */
    if (eResult>0) {

      /* Parse message into fields */
      sscanf( message_string,
               "%3s%3s%3s%9ld%4d%6ld%9ld %1s%7s",
               dest, /* %3s DESTINATION */
               sids, /* %3s SOURCE */
               cids,  /* %3s TYPE */
              &ref, /* %9ld REFERENCE */
              &len,  /* %4d data length */ 
              &mjd,  /* %6ld MJD */
              &mpm,  /* %9ld MPM */
               r_response, /* %1s R-RESPONSE */
               r_summary  /* %7s R-SUMMARY */
               );

       memset(data, '\0', sizeof(data)); /* This ensures a trailing '\0' after the memcpy below, so strings will be properly terminated */ 
       //if (strlen(message_string)>47) {
       if (len>8) {
         memcpy( data, &(message_string[47]), len-8 ); /* copy remaining bytes from message into character array */
         }

       //printf("[%s/%d] message_string: <%s>, strlen=%d\n",ME,getpid(),message_string,(int)strlen(message_string));
       //printf("[%s/%d] dest <%s> sids <%s> cids <%s> ref %ld len %d mjd %ld mpm %ld r_response <%s> r_summary <%s> data <%s>\n",ME,getpid(),
       //       dest,sids,cids,ref,len,mjd,mpm,r_response,r_summary,data);

       /* organize parsed data into a LWA_cmd_struct */
       mq_msg.sid = LWA_getsid(sids);
       mq_msg.ref = ref;
       mq_msg.cid = LWA_getcmd(cids);
       LWA_time2tv( &mq_msg.tv, mjd, mpm );
       switch (r_response[0]) { /* should be either "A" or "R" */
         case 'A': mq_msg.bAccept = LWA_MSELOG_TP_SUCCESS;   break; /* accepted by subsystem */
         case 'R': mq_msg.bAccept = LWA_MSELOG_TP_FAIL_REJD; break; /* rejected by subsystem */
	 default:  mq_msg.bAccept = LWA_MSELOG_TP_DONE_UNK;  break; /* subsystem response not clear */
         } /* switch() */
       mq_msg.eMIBerror = LWA_MIBERR_OK;
       mq_msg.eSummary  = LWA_getsum(r_summary);
       //strcpy(mq_msg.data,data); 
       memset(mq_msg.data, '\0', sizeof(mq_msg.data)); 
       memcpy(mq_msg.data, data, len-8);
       mq_msg.datalen = -1; /* assume it's a string (will straighten this out below) */

       /* Look it up in the pending task queue */
       i = 0;
       while( (ptq_ref[i] != ref ) && ( i < (LWA_PTQ_SIZE-1) ) ) { 
         //printf("[%s/%d] i=%d ptq_ref[i]=%ld ref=%ld.\n",ME,getpid(),i,ptq_ref[i],ref);        
         i++; 
         }
       if ( ptq_ref[i] != ref ) { /* we don't recognize this reference number */

            strcpy( cmdata, "" ); /* don't know nothin' about what was sent */
            mq_msg.eMIBerror += LWA_MIBERR_REF_UNK;
            printf("[%s/%d] REFERENCE=%ld not recognized.\n",ME,getpid(),ref);

         } else { /* we recognize this reference number */

            strcpy( cmdata, ptq_data[i] );
            ptq_ref[i] = 0; /* clear that spot in the queue */

         } 

       /* Update MIB based on response */
       /* Will always update SUMMARY.  */
       /* Other things get updated if bAccept = LWA_MSELOG_TP_SUCCESS or LWA_MSELOG_TP_DONE_UNK */
       mq_msg.eMIBerror += mib_update(                 /* see ms_mcic.h */
                                      mq_msg.sid,      /* subsystem, so we know what handler to use */
                                      mq_msg.cid,      /* command, so handler knows how to deal with it */
                                      mq_msg.tv,  
                                      mq_msg.bAccept,  /* R-RESPONSE, except enumerated */
                                      r_summary,       /* R-SUMMARY */
                                      data,            /* R-COMMENT (using form exactly as received) */
                                      len-8,           /* number of significant bytes in "data" (exactly as received) */
                                      cmdata,          /* the DATA field from the *command* message */
                                      dbm_filename
                                     );
   
       //printf("[%s/%d] Sending mq_msg.ref = %ld\n",ME,getpid(),mq_msg.ref);
       //printf("[%s/%d] Sending mq_msg.datalen = %d\n",ME,getpid(),mq_msg.datalen);


       /* DP sends back raw binary in R-COMMENT when an RPT command for DP-specific info is accepted ("A"). */
       /* (If RPT but not accepted, we get printable text; if not RPT, we get nothing) */
       /* To accomodate this, we convert the data field to a printable hex representation: */
       if ( (mq_msg.sid==LWA_SID_DP_) && 
            (mq_msg.cid==LWA_CMD_RPT) && 
            (!LWA_isMCSRSVD(cmdata)) &&
            (mq_msg.bAccept!=LWA_MSELOG_TP_FAIL_REJD) ) {
         mq_msg.datalen = len-8;                             /* fix this (assumed it was a string, above) */  
         i = mq_msg.datalen; if ( (2*i) > 32 ) { i=16; }      
         LWA_raw2hex( data, hex, i );         
         memcpy( mq_msg.data, hex, (2*i)+1 );          
         }
       //printf("[%s/%d] *** %d <%s>\n",ME,getpid(),LWA_isMCSRSVD(cmdata),cmdata);

       /* tell ms_exec about it */
       if ( msgsnd( mqtid, (void *)&mq_msg, LWA_msz(), 0) == -1 ) {
         printf("[%s/%d] WARNING: Could not msgsnd()\n",ME,getpid());
         }     

      } /* if (eResult>0) */
    
    //printf("[%s/%d] Mark 4\n",ME,getpid());

    /*======================================================================*/
    /*=== Housekeeping on pending task queue  ==============================*/
    /*======================================================================*/

    for ( i=0; i < LWA_PTQ_SIZE; i++) { /* for every slot in queue */
      if ( ptq_ref[i] > 0 ) { /* this is a pending task */

        gettimeofday( &mq_msg.tv, &tz );   
        if ( difftime( mq_msg.tv.tv_sec, ptq_tv[i].tv_sec ) >= LWA_PTQ_TIMEOUT ) { 
          /* time to close this puppy down */
  
          /* organize parsed data into a LWA_cmd_struct */
          mq_msg.sid = (long int) sid;
          mq_msg.ref = ptq_ref[i];
          mq_msg.cid = 0;        /* we have no record of what this was */
          //mq_msg.subslot = 0;    /* we have no record of what this was */ 
          mq_msg.bScheduled = 0; /* we have no record of what this was */
          /* already have mq_msg.tv (from difftime calculation) */
          mq_msg.bAccept =   LWA_MSELOG_TP_DONE_PTQT;
          mq_msg.eSummary =  LWA_SIDSUM_NULL;
          mq_msg.eMIBerror = LWA_MIBERR_OTHER;
          strcpy(mq_msg.data,"Timed out at subsystem"); 
          mq_msg.datalen = -1;

          /* tell ms_exec about it */
          if ( msgsnd( mqtid, (void *)&mq_msg, LWA_msz(), 0) == -1 ) {
            printf("[%s/%d] WARNING: Could not msgsnd()\n",ME,getpid());
            }  

          /* free up this spot on the task queue */
          ptq_ref[i] = 0; 
          
          } /* if ( difftime( */

        } /* if ( ptq_ref[i] > 0 ) */
      } /* for ( i  */


    /* avoiding busy wait */
    usleep(1); /* Go to sleep for 1 microsecond */
    /* 1 microsecond sleep (usleep(1)) is enough to reduce CPU utilization */
    /* from near 100% to a level which is comparable to quiescent activity; */
    /* i.e., 10% or less */   

    /*======================================================================*/
    /*=== End of the main loop  ============================================*/
    /*======================================================================*/
    } /* while () */

  /* close down sockets interface */
  close(sfdr);
  close(sfdt); 

  printf("[%s/%d] exit(EXIT_SUCCESS)\n",ME,getpid());
  exit(EXIT_SUCCESS);
  } /* main() */


//==================================================================================
//=== HISTORY ======================================================================
//==================================================================================
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Aug 25
//   .1: Got rid of "subslot" field
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Aug 17
//   .1: Dealing with quirks in DP binary vs. string responses (added LWA_isMCSRSVD())
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Aug 16
//   .1: Accomodating possibility that "data" field of LWA_cmd_struct is not a string
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Aug 15
//   .1: R-COMMENT (a.k.a. "data") was assumed to be a string; now accomodating raw binary (primarily for DP)
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Aug 02
//   .1: implementing shutdown via message queue (svn rev 21)
//   .2: Cleaning up, including console messages and data fields; implemented usleep(1) (svn rev 22)
//   .3: More cleanup of console messages
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Jul 31
//   .1: minor changes  (svn rev 17,18)
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Jul 30 
//   .1: remove ptq entries when they time out (~3 seconds) (svn rev 16)
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Jul 28 
//   .1: Now using LWA_time2tv() to send time back to ms_exec in response messages (svn rev 13)
//   .2: Remembering DATA field of outbound messages for use in response message processing (svn rev 14)
//   (svn rev 15)
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Jul 27 
//   .1: Now beginning implemention of MIB updates based on subsystem responses (svn rev 11)
//   .2: Fixed bug in call to LWA_timeval; forgot to initialize tv (svn rev 12)
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Jul 26 
//   .1: Moved initial read of whole dbm to new code ms_mdr.c,
//       Implementing MIB update in response to received subsystem messages
//   .2: Implementing swap of index/label for MIB dbm key (svn rev 10)
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Jul 24 
//   .1: Working on task progress, interaction with ms_exec, logging
//   .2: Decoupling MCS Common ICD transmit and receive operations (svn rev 9)
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Jul 23 
//   .1: Translating message queue info into proper ICD message (svn rev 7)
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Jul 22 
//   .1: Re-implementing sockets comm with subsystem.  Rudimentary check for now.
//   .2: Incorporating sockets comm into main loop.  Still rudimentary (svn rev 6)
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Jul 21
//   .1: Checking implementation of IP_ADDRESS, TX_PORT, and RX_PORT in dbm file
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Jul 20
//   .1: Cleaning up time handling
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Jul 17
//   .1: Change from msg_struct to LWA_cmd_struct
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Jul 13
//   .1: Bringing into common codeset; mib.h -> LWA_MCS.h
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Jul 08
//   .1: reports it's own pid; runs in loop responding to pings
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Jul 07
//   .1: working on message queue
//   .2 implementing handshake via message queue with ms_init
//   .3
// ms_mcic.c: S.W. Ellingson, Virginia Tech, 2009 Jul 05
//   .1: adding dbm read check upon startup
//   .2: adding message queue
// ms_mcic2.c: S.W. Ellingson, Virginia Tech, 2009 Jul 04
//   setting up message queue; adding response to ms_init -- never did this
// ms_mcic2.c: S.W. Ellingson, Virginia Tech, 2009 Jul 02

//==================================================================================
//=== BELOW THIS LINE IS SCRATCH ===================================================
//==================================================================================
//


