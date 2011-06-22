
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Aug 25
// ---
// COMPILE: gcc -o ms_exec ms_exec.c
// ---
// COMMAND LINE: ms_exec sidlist
//   sidlist is a base-10 number whose bits in base-2 representation indicate
//           the presense/absense of a particular subsystem ID.
//           Set to 0 (="no subsystems") to test without message queue errors
//           Note "MCS" is always added as a subsystem, even if sidlist is 0
// ---
// REQUIRES: 
//	Intended to be launched (using exec()) from ms_init, which gets things set up.
//	LWA_MCS.h
//      ms_exec_log.c: contains logging code
// ---
// Initialization for MCS/Exec
// See end of this file for history.

#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <time.h>
#include <sys/time.h>

#include <sys/types.h>
#include <sys/ipc.h>
//#include <sys/wait.h>

#include <string.h>

#include <sys/socket.h>
#include <sys/un.h>
#include <netinet/in.h> /* for network sockets */
#include <arpa/inet.h>  /* for network sockets */
#include <fcntl.h>      /* for F_GETFL, other possibly other stuff */

#define MY_NAME "ms_exec (v.20090825.1)"
#define ME "2" 

#include "LWA_MCS.h"
#include "ms_exec_log.c"


main ( int narg, char *argv[] ) {

  /*=================*/
  /*=== Variables ===*/
  /*=================*/

  long int sidlist;     /* command line argument */
  int nsid = 0;         /* number of subsystems. initialize to zero */
  int sid[LWA_MAX_SID+1]; /* subsystem IDs; 0..nsid-1 are valid indices */

  int test; 
  int sid_candidate;

  int mqrid;
  int mqtid[LWA_MAX_SID+1];
  struct LWA_cmd_struct mq_msg; //was: struct mq_struct mq_msg;
  key_t mqtkey;       /* key for transmit message queue */

  int n;

  int server_len;
  int client_len;  
  int server_sockfd;                
  int client_sockfd;   
  struct sockaddr_in server_address; /* for network sockets */
  struct sockaddr_in client_address; /* for network sockets */

  int flags; /* used as part of scheme for changing accept()'s blocking behavior */

  struct LWA_cmd_struct c;

  long int reference; /* "REFERENCE" field in MCS common ICD */

  int b_valid_sid;

  /* task queue */
  int tqp;                                              /* task queue pointer */
  int tql;                                              /* task queue length */
  int tqfai;                                            /* first available index into task queue */
  int tq[LWA_MS_TASK_QUEUE_LENGTH];                     /* task queue: */
							/* 0 = available (no entry) */
                                                        /* 1 = task queued for sending */
                                                        /* 2 = task sent, but no response yet */
  struct LWA_cmd_struct task[LWA_MS_TASK_QUEUE_LENGTH]; /* tasks */

  int tqp_stop;
  int eDone;

  int tqp2;

  struct timeval tv;  /* from sys/time.h; included via LWA_MCS.h */
  struct timezone tz;

  FILE *fpl; /* pointer to log file */
  char logmsg[LWA_MSELOG_LENGTH];

  int eSummary = LWA_SIDSUM_NORMAL; /* beginnings of an MCS MIB */

  int i;

  /*==================*/
  /*=== Initialize ===*/
  /*==================*/
    
  /* initialize log file */
  fpl = fopen(LWA_MSELOG_FILENAME,"w"); /* clobber any existing file */

  /* First, announce thyself */
  printf("[%s] I am %s\n",ME,MY_NAME);
  sprintf(logmsg,"I am %s [%s]",MY_NAME,ME);
  LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 );

  /* add log message showing command line used to call me */
  if (narg>1) {
    sprintf(logmsg,"Command line: %s %s",argv[0],argv[1]);
    LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 );
    }

  /* add MCS (me) to list of subsystems */
  sid[nsid] = LWA_SID_MCS;
  nsid += 1;
  sprintf(logmsg,"Added subsystem %s",LWA_sid2str(sid[nsid-1]));
  LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 );

  /* Process command line arguments */
  if (narg>1) { 
    sscanf(argv[1],"%ld",&sidlist);
    //printf("[%s] sidlist = %ld\n",ME,sidlist);

    /* break down into sid[ 0 .. nsid-1 ] */
    sid_candidate = 1;     
    test = 1;
    while (sidlist>0) {
      while ( !( sidlist & test ) ) { 
        test *= 2; 
        sid_candidate++; 
        }
      sidlist = sidlist ^ test; /* reset that bit */
      nsid += 1;
      sid[nsid-1] = sid_candidate;
      //sprintf(logmsg,"Added subsystem: sid[%d]=%d",nsid-1,sid[nsid-1]); 
      sprintf(logmsg,"Added subsystem %s",LWA_sid2str(sid[nsid-1]));
      LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 );   
      //printf("%s %ld %d\n",logmsg,sidlist,test);  strcpy(logmsg,"X");
      }
    //printf("[%s] nsid=%d\n",ME,nsid);
   
    } else {

    sprintf(logmsg,"FATAL: sidlist not provided");
    LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 ); 
    exit(EXIT_FAILURE);

    } 


  /* initialize reference number */
  reference = 1; /* reference number = 0 reserved for error condition */

  /* Set up for receiving from message queue */
  if (nsid>1) { /* if there is at least one subsystem other than MCS... */
    mqrid = msgget( (key_t) MQ_MS_KEY, 0666 );
    if (mqrid==-1) {
      sprintf(logmsg,"WARNING: Message queue setup failed with code %d",mqrid);
      LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 ); 
      }  
    }


  /* Set up transmit message queues */
  for ( n=1; n<nsid; n++ ) { /* start at n=1 since n=0 is MCS (me) */ 
    mqtkey = MQ_MS_KEY + sid[n];
    //printf("[%s] mqtkey = %d\n",ME,mqtkey);
    mqtid[sid[n]] = msgget( mqtkey, 0666 );
    if (mqtid[sid[n]]==-1) {
      //perror(" ");
      sprintf(logmsg,"FATAL: Could not msgget() tx message queue\n");
      LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 ); 
      exit(EXIT_FAILURE);
      } 
    }


  /* set up sockets interface for communicating with MCS/Exec and others... */ 
  server_sockfd = socket(             /* create socket */
                         AF_INET,     /* domain; network sockets */
                         SOCK_STREAM, /* type (TCP-like) */
                         0);          /* protocol (normally 0) */
  if (server_sockfd == -1) {
    printf("[%s] FATAL: socket() failed\n",ME);
    perror("ms_exec");
    sprintf(logmsg,"FATAL: socket() failed\n");
    LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 ); 
    exit(EXIT_FAILURE); 
    }
  /* name socket */
  server_address.sin_family      = AF_INET;                /* network sockets */  
  server_address.sin_addr.s_addr = inet_addr(LWA_IP_MSE);  /* network sockets */
  server_address.sin_port        = htons(LWA_PORT_MSE);    /* network sockets */
  server_len = sizeof(server_address);

  i = bind( server_sockfd, 
           (struct sockaddr *) &server_address, 
            server_len );
  if (i == -1) {
    printf("[%s] FATAL: bind() failed (see error message below)\n",ME);
    perror("ms_exec");
    printf("[%s] If message above is ``Address already in use'':\n",ME);
    printf("[%s]   (1) Kill any ms_mcic processes (e.g., $ sh ./ms_shutdown).\n",ME);
    printf("[%s]   (2) Wait a few seconds before trying this again.\n",ME);
    sprintf(logmsg,"FATAL: bind() failed\n");
    LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 ); 
    exit(EXIT_FAILURE); 
    }

  /* create a connection queue */
  i = listen(server_sockfd,
             5 );           /* backlog */
  if (i == -1) {
    printf("[%s] FATAL: listen() failed\n",ME);
    perror("ms_exec");
    sprintf(logmsg,"FATAL: listen() failed\n");
    LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 ); 
    exit(EXIT_FAILURE); 
    }
  /* change accept() from blocking to non-blocking */
  flags = fcntl( server_sockfd, F_GETFL, 0 );
  fcntl( server_sockfd, F_SETFL, O_NONBLOCK|flags );

  /* initialize task queue */
  tql = 1;   /* task queue length is zero */
  tqp = 0;   /* point to next task */
  tqfai = 0; /* first index is available */
  tq[tqfai] = 0; 


  /*==================*/
  /*==================*/
  /*=== Main Loop ====*/
  /*==================*/
  /*==================*/

  while ( eSummary > LWA_SIDSUM_NULL ) {

    /*=========================================================================*/
    /*=== Check inbound message queue for messages from the ms_mcic's =========*/
    /*=========================================================================*/ 

    /* Accepts messages of all types and does not block */
    if (nsid>0) { /* if there is at least one subsystem... */        

      if ( msgrcv( mqrid, (void *)&mq_msg, LWA_msz(), 0, IPC_NOWAIT) == -1) {
        
          /* No messages to receive -- Nothing to do */

        } else {
      
          /* Got a message.  Do something about it... */
          
          //sprintf(logmsg,"MQ rcvd: sid=%ld, ref=%ld, cid=%d, subslot=%d, data=<%s>",
          //  mq_msg.sid, mq_msg.ref, mq_msg.cid, mq_msg.subslot, mq_msg.data );
          //LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 ); 

          /* Two possibilities: */
          /* (1) This is the response to a command sent earlier, or */
          /* (2) This is an unsolicited message (as implemented now, this is an error) */
          
          /* check to see if is a response.  */
          /* Do this by matching reference numbers: */
          tqp2 = 0;
          while ( (tqp2<tql) && !(task[tqp2].ref==mq_msg.ref) ) tqp2++;
          if (tqp2==tql) { /* We didn't find a match */

               sprintf(logmsg,"ms_mcic used an unrecognized REF: %ld (ignoring it)",mq_msg.ref);
               LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 ); 

             } else { /* we DID find a match */

               tq[tqp2] = LWA_MSELOG_TP_AVAIL; /* flag this slot in queue as being available */    

               /* OK, so this a response we recognize. Now possibilities are: */
               /* (1) subsystem accepted it (LWA_MSELOG_TP_SUCCESS) */
               /* (2) subsystem rejected it (LWA_MSELOG_TP_FAIL_REJD) */ 
               /* (3) subsystem or ms_mcic response is ambiguous (LWA_MSELOG_TP_DONE_UNK) */
               /* (4) ms_mcic is saying something went wrong (LWA_MSELOG_TP_FAIL_MCIC) */
 
               // sprintf(logmsg,"Received response to ref=%ld",mq_msg.ref);
               // LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 );  
                
               switch (mq_msg.bAccept) {

                 case LWA_MSELOG_TP_SUCCESS:     /* accepted by subsystem */
	           LWA_mse_log( fpl, LWA_MSELOG_MTYPE_TASK, mq_msg.ref, 
                                LWA_MSELOG_TP_SUCCESS, 
                                mq_msg.sid, mq_msg.cid, mq_msg.data, mq_msg.datalen ); 
                   break;
		
		 case LWA_MSELOG_TP_FAIL_REJD: /* rejected by subsystem */
	           LWA_mse_log( fpl, LWA_MSELOG_MTYPE_TASK, mq_msg.ref, 
                                LWA_MSELOG_TP_FAIL_REJD, 
                                mq_msg.sid, mq_msg.cid, mq_msg.data, mq_msg.datalen ); 
                   break;

		 case LWA_MSELOG_TP_DONE_UNK: /* ms_mcic didn't understand subsytem response */
	           LWA_mse_log( fpl, LWA_MSELOG_MTYPE_TASK, mq_msg.ref, 
                                LWA_MSELOG_TP_DONE_UNK, 
                                mq_msg.sid, mq_msg.cid, mq_msg.data, mq_msg.datalen ); 
                   break;

                 case LWA_MSELOG_TP_FAIL_MCIC: /* ms_mcic had a problem with it */
	           LWA_mse_log( fpl, LWA_MSELOG_MTYPE_TASK, mq_msg.ref, 
                                LWA_MSELOG_TP_FAIL_MCIC, 
                                mq_msg.sid, mq_msg.cid, mq_msg.data, mq_msg.datalen ); 
                   break;

		 default: /* other valid bAccept codes, or perhaps bAccept is invalid */
	           LWA_mse_log( fpl, LWA_MSELOG_MTYPE_TASK, mq_msg.ref, 
                                mq_msg.bAccept, 
                                mq_msg.sid, mq_msg.cid, mq_msg.data, mq_msg.datalen );
                   //sprintf(logmsg,"Previous message: bAccept = %d",mq_msg.bAccept);
                   //LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg );    
                   break;

                 } /* switch (mq_msg.bAccept) */

             /* also note if ms_mcic had a problem writing to it's MIB. */
             if (mq_msg.eMIBerror > 0) {
               sprintf(logmsg,"Previous message: eMIBerror=%d",mq_msg.eMIBerror);
               LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 );  
               }
           
             }
  
        } /* if ( msgrcv(... */

      } /* if (nsid>0) */


    /*=========================================================================*/
    /*=== Check inbound socket for messages from MCS/Exec or other entities ===*/
    /*=========================================================================*/ 


    /* Check socket interface for MCS/Exec or other inbound connections */
    client_len = sizeof(client_address);
    client_sockfd = accept( server_sockfd,
                            (struct sockaddr *) &client_address, 
                            &client_len );  

    if (!(client_sockfd==-1)) { /* we have a connection... */                          

      /* read it into a LWA_cmd_struct structure */
      read(client_sockfd,&c,sizeof(struct LWA_cmd_struct));
      //printf("saw %d %d\n",c.sid,c.cid);

      /* Determine if this is for a valid subsystem */
      //printf("[%s] Inbound sockets message has destination field = %d\n",ME,c.sid);
      b_valid_sid = 0;
      for ( n=0; n<nsid; n++ ) {
        if (sid[n]==c.sid) b_valid_sid = 1; 
        //printf("[%s] sid[%d]=%d, c.sid=%ld b_valid_sid=%d\n",ME,n,sid[n],c.sid,b_valid_sid);
        }

      if ( b_valid_sid && (eSummary != LWA_SIDSUM_SHUTDWN) ) { /* if a valid subsystem and */
                                                               /* we aren't in the process of shutting down... */

        /* If the destination subsystem is MCS, then we deal with it now (as opposed to queuing it) */

        if (c.sid==LWA_SID_MCS) { /* this is for me (MCS) */

          /* Commands directed to MCS are executed immediately and do not go into the queue */

          /* dummy/placeholder code for now */          
          c.ref = 0;                          /* not queued, so no reference number */
          gettimeofday( &c.tv, &tz );         /* note the current time */
          c.bAccept = 1;                      /* indicate acceptance */

          c.eMIBerror = LWA_MIBERR_OK;    

          switch (c.cid) {

            case LWA_CMD_SHT:

              eSummary = LWA_SIDSUM_SHUTDWN;  /* remember that we are shutting down */

              /* response to sender of SHT command */
              c.eSummary = eSummary;
              strcpy(c.data,"Starting shutdown");

              sprintf(logmsg,"Starting shutdown...");
              LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 );  

              /*=== In this section, we generate a task to send to each ms_mcic ===*/
              /*=== The task tells the ms_mcic to shut down.  It is assumed =======*/
              /*=== That the subsystem has already been told to shutdown ==========*/
              
              for ( i=0; i<nsid; i++ ) { /* for each subsystem */

                if (sid[i] != LWA_SID_MCS) { /* other than MCS */ 

                  /* assign reference number */
                  reference += 1;
                  if (reference > LWA_MAX_REFERENCE) reference=1; /* reference=0  used for error flag */

                  /* push into the task queue */
                  tq[tqfai] = LWA_MSELOG_TP_QUEUED;
                  task[tqfai].sid        = sid[i];
                  task[tqfai].ref        = reference;
                  task[tqfai].cid        = LWA_CMD_MCSSHT;  /* tells ms_mcic that *it* should shut down */ 
                  //task[tqfai].subslot    = c.subslot;       /* ignored */
                  task[tqfai].bScheduled = c.bScheduled;    /* ignored */
                  task[tqfai].tv         = c.tv;            /* ignored */
                  task[tqfai].bAccept    = 0;               /* outbound value doesn't matter */
                  task[tqfai].eSummary   = LWA_SIDSUM_NULL; /* outbound value doesn't matter */
                  strcpy( task[tqfai].data, "Request ms_mcic shutdown" );
                  task[tqfai].datalen    = -1;              /* string */   

                  /* log task progress */
	          LWA_mse_log( fpl, LWA_MSELOG_MTYPE_TASK, task[tqfai].ref, 
                         LWA_MSELOG_TP_QUEUED, 
                         task[tqfai].sid, task[tqfai].cid, task[tqfai].data, task[tqfai].datalen ); 

                  /* find new "first available index" (tqfai) */
                  tqfai = 0;                                       /* start looking at beginning of queue */ 
                  while ( tq[tqfai] && ( tqfai<tql ) ) tqfai += 1; /* search for next tq[] that is zero */
                  if ( tqfai>=tql ) {                   /* need to increase queue size */
                    if (tql<LWA_MS_TASK_QUEUE_LENGTH) { /* we have room so: */
                        tql += 1;                         /* ...increase queue length */
                        tq[tqfai] = 0;                    /* ...mark newly available space as available */      
                      } else {                            /* we don't have room, so do nothing */
                        sprintf(logmsg,"Task queue length is at maximum.");
                        LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 ); 
                      } /* if (tql<LWA_MS_TASK_QUEUE_LENGTH) */
                    }  /* if ( tqfai>=tql ) */

                  } /* if (sid[i] != LWA_SID_MCS */
                } /* for ( i=0 */

              break;  


            default:

              c.eSummary = eSummary;   
              strcpy(c.data,"Unimplemented MCS command");
              c.datalen = -1; 

              sprintf(logmsg,"Unimplemented MCS command; no action taken");
              LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 ); 

              break;

            } /* switch (c.cid) */

          } /* if (c.sid */

         /* Tasks for other subsystems go into the task queue, if there is room in the queue: */

        if (    (!(c.sid==LWA_SID_MCS))    /* if not for me (MCS)... */
             && (tqfai>=tql)            ){ /* and there is NO available slot in queue ... */

          /* message to report back */
          c.ref = 0;
          c.bAccept = 0;                      /* indicate rejection */
          c.eSummary = LWA_SIDSUM_NULL;       
          strcpy(c.data,"Task queue full");
          c.datalen = -1;

          /* log it as a failed task */
	  LWA_mse_log( fpl, LWA_MSELOG_MTYPE_TASK, c.ref, 
                       LWA_MSELOG_TP_FAIL_EXEC, c.sid, c.cid, c.data, c.datalen );
                            
          } 


        /* ...room in the queue */
        if (    (!(c.sid==LWA_SID_MCS))    /* if not for me (MCS)... */
             && (tqfai<tql)             ){ /* and there is an available slot in queue ... */

          /* assign reference number */
          reference += 1;
          if (reference > LWA_MAX_REFERENCE) reference=1; /* reference=0  used for error flag */
          c.ref = reference; 

          /* push into the task queue */
          tq[tqfai] = LWA_MSELOG_TP_QUEUED;
          task[tqfai].sid        = c.sid;
          task[tqfai].ref        = c.ref;
          task[tqfai].cid        = c.cid; 
          //task[tqfai].subslot    = c.subslot;
          task[tqfai].bScheduled = c.bScheduled;
          task[tqfai].tv         = c.tv;      
          task[tqfai].bAccept    = 0;               /* outbound value doesn't matter */
          task[tqfai].eSummary   = LWA_SIDSUM_NULL; /* outbound value doesn't matter */
          if (c.datalen==-1) {
              strcpy( task[tqfai].data, c.data );
            } else {
              memset( task[tqfai].data, '\0', sizeof(task[tqfai].data) );
              memcpy( task[tqfai].data, c.data, c.datalen );
            }
          task[tqfai].datalen    = c.datalen;

          /* log task progress */
	  LWA_mse_log( fpl, LWA_MSELOG_MTYPE_TASK, task[tqfai].ref, 
                       LWA_MSELOG_TP_QUEUED, 
                       task[tqfai].sid, task[tqfai].cid, task[tqfai].data, task[tqfai].datalen ); 

          /* message to report back */
          c.bAccept = 1;                      /* indicate acceptance */
          c.eSummary = LWA_SIDSUM_NULL;       
          strcpy(c.data,"Task has been queued");
          c.datalen = -1;

          /* find new "first available index" (tqfai) */
          tqfai = 0;                                       /* start looking at beginning of queue */ 
          while ( tq[tqfai] && ( tqfai<tql ) ) tqfai += 1; /* search for next tq[] that is zero */
          if ( tqfai>=tql ) {                   /* need to increase queue size */
            if (tql<LWA_MS_TASK_QUEUE_LENGTH) { /* we have room so: */
                tql += 1;                         /* ...increase queue length */
                tq[tqfai] = 0;                    /* ...mark newly available space as available */      
              } else {                            /* we don't have room, so do nothing */
                sprintf(logmsg,"Task queue length is at maximum.");
                LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 ); 
              } /* if (tql<LWA_MS_TASK_QUEUE_LENGTH) */
            }  /* while ( tqfai>=tql ) */
         
          } /* if ( (!(c.sid==LWA_SID_MCS)) && (tqfai<tql) ) */


        } else { /* invalid sid or we are shutting down */


          c.ref = 0;                        
          c.bAccept = 0;                      /* indicate rejection */
          c.eSummary = eSummary;       
          strcpy(c.data,"Invalid sid or we're shutting down");
          c.datalen = -1;

          /* log task progress */
	  LWA_mse_log( fpl, LWA_MSELOG_MTYPE_TASK, c.ref, 
                       LWA_MSELOG_TP_FAIL_EXEC, 
                       c.sid, c.cid, c.data, c.datalen ); 
   
        } /* if (!b_valid_sid) */


      /* report back to requester, and close connection */
      write(client_sockfd,&c,sizeof(struct LWA_cmd_struct));
      close(client_sockfd);

      //for (n=0;n<tql;n++) {
      //   printf("[%s] tq[%d] = %d\n",ME,n,tq[n]);
      //   }

      } /* if (!(client_sockfd==-1)) {   ...we have a connection... */    


    /*=================================*/
    /*=== Do a task from task queue ===*/
    /*=================================*/    

    /* advance task queue pointer to next pending task, implementing a circular buffer */
    tqp_stop = tqp;   /* this is the last index we should check (first one is tqp+1) */
    eDone = 0;        /* =1 means exiting with a pending task, =2 means exiting without a pending task */ 
    while ( eDone==0 ) { 
      tqp++;                                      /* advance pointer */  
      if (tqp>=tql)                      tqp=0;   /* wrap around */
      if (tqp==tqp_stop)                 eDone=2; /* we've checked the whole queue. */
      if (tq[tqp]==LWA_MSELOG_TP_QUEUED) eDone=1; /* found a task that's ready to send */
      }

    if (eDone==1) { /* Found a pending task */

      /* load up a message structure and send it! */
      mq_msg.sid        = task[tqp].sid;
      mq_msg.ref        = task[tqp].ref; 
      mq_msg.cid        = task[tqp].cid; 
      //mq_msg.subslot    = task[tqp].subslot;   
      mq_msg.bScheduled = task[tqp].bScheduled;
      mq_msg.tv         = task[tqp].tv;
      mq_msg.bAccept = 0;                /* outbound value doesn't matter */ 
      mq_msg.eSummary = LWA_SIDSUM_NULL; /* outbound value doesn't matter */ 
      //strcpy( mq_msg.data, task[tqp].data );
      if (task[tqp].datalen==-1) {
          strcpy( mq_msg.data, task[tqp].data );
        } else {
          memset( mq_msg.data, '\0', sizeof(mq_msg.data) );
          memcpy( mq_msg.data, task[tqp].data, task[tqp].datalen );
        }
      mq_msg.datalen    = task[tqp].datalen;               

      if ( msgsnd( mqtid[task[tqp].sid], (void *)&mq_msg, LWA_msz(), 0) == -1 ) {

          sprintf(logmsg,"FATAL: Could not msgsnd()");
	  LWA_mse_log( fpl, LWA_MSELOG_MTYPE_TASK, task[tqp].ref, 
                       LWA_MSELOG_TP_FAIL_EXEC, 
                       task[tqp].sid, task[tqp].cid, task[tqp].data, task[tqp].datalen ); 

          tq[tqp] = 0; /* reallocate this slot in the message queue */

        } else {

          sprintf(logmsg,"Sent task to ms_mcic");
          LWA_mse_log( fpl, LWA_MSELOG_MTYPE_TASK, task[tqp].ref, 
                       LWA_MSELOG_TP_SENT, 
                       task[tqp].sid, task[tqp].cid, task[tqp].data, task[tqp].datalen );  

          /* Mark this slot in the task queue as "sent, but no response yet" */
          tq[tqp]=LWA_MSELOG_TP_SENT;

        } /*  */

      } /* if (eDone==1) */

    if ( (eDone==2) && (eSummary==LWA_SIDSUM_SHUTDWN) ) {
      /* We're shutting down and the task queue is now empty, */
      /* so we know that the ms_mcic shutdown commands are in the message queue */
      eSummary = LWA_SIDSUM_NULL; /* break out of main (while) loop */
      }

    /*=========================================================================*/
    /*=== Check task queue for things which have become stale at an ms_mcic ===*/
    /*=========================================================================*/

    for ( i=0; i<tql; i++ ) {

       if ( tq[i] == LWA_MSELOG_TP_SENT ) { 
         /* this is a task which is sent but not yet heard from */

         gettimeofday( &tv, &tz );   
         if ( difftime( tv.tv_sec, task[i].tv.tv_sec ) >= LWA_MS_TASK_QUEUE_TIMEOUT ) { 
           /* time to close this puppy down */

           tq[i] = LWA_MSELOG_TP_AVAIL; /* tag it as available */

           /* log it as failed */
	   LWA_mse_log( fpl, 
                        LWA_MSELOG_MTYPE_TASK, 
                        task[i].ref, 
                        LWA_MSELOG_TP_FAIL_MCIC, 
                        task[i].sid, 
                        task[i].cid, 
                        "Timed out at ms_mcic", -1 ); 
       
           } /* if ( difftime */
         } /* if ( tq[i] */
       } /* for ( i=0; */


    /* avoiding busy wait */
    usleep(1); /* Go to sleep for 1 microsecond */
    /* 1 microsecond sleep (usleep(1)) is enough to reduce CPU utilization */
    /* from near 100% to a level which is comparable to quiescent activity; */
    /* i.e., 10% or less */    

    } /* while ( eSummary > LWA_SIDSUM_NULL  */

  /*=========================*/
  /*=========================*/
  /*=== END of Main Loop ====*/
  /*=========================*/
  /*=========================*/

  close(server_sockfd);     /* shutdown the socket connection */

  sleep(1);                 /* Wait a second to make sure ms_mcic's get shutdown command. */

  msgctl(mqrid,IPC_RMID,0); /* delete the receive message queue */

  /* delete transmit message queues */
  for (i=0;i<nsid;i++) {
    if (sid[i] != LWA_SID_MCS) { /* since MCS has no message queue to itself */
      msgctl(mqtid[sid[i]],IPC_RMID,0); 
      sprintf(logmsg,"Deleting tx msg queue for %s",LWA_sid2str(sid[i]));
      LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 );
      }         
    }

  sprintf(logmsg,"ms_exec shutdown complete");
  LWA_mse_log( fpl, LWA_MSELOG_MTYPE_INFO,0,0,0,0, logmsg, -1 );  
  fclose(fpl); /* close log */
 
  exit(EXIT_SUCCESS);
  } /* main() */


//==================================================================================
//=== HISTORY ======================================================================
//==================================================================================
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Aug 25
//   .1: Got rid of "subslot" field
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Aug 16
//   .1: Accomodating possibility that "data" field of LWA_cmd_struct is not a string
//   .2: Accomodating ms_exec_log.c change to accomodate binary data
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Aug 14
//   .1: Fixed bug (array range overrun in sid[] (svn rev 28)
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Aug 02
//   .1: Modifying MCS SHT to result in tasks shutting down the ms_mcic's (svn rev 21)
//   .2: Cleaning up console messages, implemented usleep(1) (svn rev 22)
//   .3: Added some error trapping to socket start-up (svn rev 23)
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Aug 01
//   .1: Cleaned up (unimplemented) response to commands directed to MCS 
//       Added logging of command line to log file 
//       When adding subsystems, showing sid strings as opposed to numbers (svn rev 19)
//   .2: Implementing orderly shutdown (rudimentary MCS SHT) (svn rev 20)
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Jul 31
//   .1: Added timeout for tasks marked as "SENT" (svn rev 17,18)
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Jul 30
//   .1: Minor fixes (svn rev 16)
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Jul 26
//   .1: Handling new .eMIBerror field in LWA_cmd_struct (svn rev 10)
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Jul 24
//   .1: File logging implemented through ms_exec.h (svn rev 8)
//   .2: Completing logging of "task progress" messages (svn rev 9)
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Jul 23
//   .1: Implemented crude response to MCS SHT (svn rev 7)
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Jul 20
//   .1: Cleaning up handling ot time; implementing .bScheduled and .tv fields 
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Jul 17
//   .1: Cleaning up task queue handler, change from msg_struct to LWA_cmd_struct
//   .2: Adding pending (sent, but no response yet) state to task queue
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Jul 15
//   .1: MCS is always added as the first subsystem (with no message queue)
//   .2: Implementing message queue to ms_mcic, setting up task queue
//   .3: Implementing task queue
//   .4: Task queue actually doing tasks
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Jul 13
//   .1: working on sockets communications/command
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Jul 10
//   implementing control loop, sockets communications
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Jul 08
//   .1: implementing MS/Exec-side sockets interface.  This code is the server.
//   .2: sockets data format change
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Jul 08
//   .1: now pinging ms_ncic's 
//   .2: properly establishing all message_queues; laying in main loop
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Jul 07
//   .1: modified command line to accept list-of-subsystems argument
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Jul 01
// ms_exec.c: S.W. Ellingson, Virginia Tech, 2009 Jun 27 

//==================================================================================
//=== BELOW THIS LINE IS SCRATCH ===================================================
//==================================================================================










