// ms_init.c: S.W. Ellingson, Virginia Tech, 2009 Aug 02
// ---
// COMPILE: gcc -o ms_init ms_init.c
// ---
// COMMAND LINE: ms_init <ms_init_file> 
//   <ms_init_file> file containing information required for initialization (required)
// ---
// REQUIRES: 
// ---
// Initialization for MCS/Scheduler
// See end of this file for history.

#include <stdlib.h>
#include <stdio.h>
#include <unistd.h> 
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/wait.h>

#include "LWA_MCS.h"

#include <string.h>

#define MY_NAME "ms_init (v.20090802.1)"
#define ME "1" 

#define MAX_LINE_LENGTH 256
#define MAX_TOKENS 10

main ( int narg, char *argv[] ) {

  /*=================*/
  /*=== Variables ===*/
  /*=================*/

  char ms_init_filename[256]; /* command line arguments */

  FILE* fid;
  int bDone;

  char line[MAX_LINE_LENGTH];       /* used in parsing init file */
  char *snippet; 
  char token[MAX_TOKENS][MAX_LINE_LENGTH];
  int ntok;

  int err;
  pid_t ms_exec_pid; /* PID for ms_exec process */
  pid_t pid;

  int mqid;
  int mqt;
  struct LWA_cmd_struct mq_msg;

  int nsid;             /* number of subsystems defined */
  int sid[LWA_MAX_SID]; /* subsystem IDs defined */

  key_t mqtkey;       /* key for transmit message queue */

  char sidlist[9];     /* used to generate cmd line arg for ms_exec */
  int n;
  long int sidsum;

  /*==================*/
  /*=== Initialize ===*/
  /*==================*/
    
  /* First, announce thyself */
  printf("[%s] I am %s\n",ME,MY_NAME);

  /* Process command line arguments */
  if (narg>1) { 
    sprintf(ms_init_filename,"%s",argv[1]);
      printf("[%s] ms_init_filename: <%s>\n",ME,ms_init_filename);
    }
    else {
    printf("[%s] FATAL: ms_init_filename not provided\n",ME);
    exit(EXIT_FAILURE);
    } 

  /* Set number of subsystems to zero */
  nsid = 0;

  /* Set up for receiving from message queue */
  mqid = msgget(
                 (key_t) MQ_MS_KEY, /* identify message queue */
                 0666 | IPC_CREAT   /* create if it doesn't already exist */
                );
  if (mqid==-1) 
    printf("[%s] WARNING: Message queue setup failed with code %d\n",ME,mqid);   

  /* Clear out message queue */
  while ( msgrcv( mqid, (void *)&mq_msg, LWA_msz(), 0, IPC_NOWAIT ) > 0 ) ;

  /* Open ms_init_file */
  fid = fopen(ms_init_filename,"r");
  if (!fid) { 
    printf("[%s] FATAL: Can't read ms_init_file\n",ME); 
    exit(EXIT_FAILURE); 
    }  

  /*==================*/
  /*=== Main Loop ====*/
  /*==================*/
  /* Read ms_init_file line-by-line, taking action as each line is read. */

  while (!feof(fid)) {

    /* read next line */
    strcpy(line,""); /* keep last-line junk from screwing this up... */
    fgets(line, sizeof(line), fid);
    //printf("line = <%s>\n",line);

    /* parse line */
    /* when smoke clears, token[0] is the command, token[1..ntok-1] are */
    /* the arguments */
    ntok = 0;
    strcpy(token[ntok],""); /* initialize just in case */
    snippet = strtok( line, " \n"); /* delimiter will be any space, or \n */
    while (snippet != NULL) {
      //printf( "snippet = <%s>\n",snippet);
      //sscanf(token[ntok],"%s",snippet);
      strcpy(token[ntok],snippet);
      ntok++;
      //printf("token[%d] = <%s> from <%s>\n",ntok-1,token[ntok-1],snippet);     
      snippet = strtok( NULL, " \n"); /* note "NULL" is now the first argument! */
      }
    //printf("[%s] parsed line (%d): |",ME,ntok);
    //for (n=0;n<ntok;n++) {
    //  printf("%s|",token[n]);
    //  }
    //printf("\n");
  
    bDone=0;

    /* if first character in token[0] (the command) is "#" then we should ignore it */
    if (!strncmp(token[0],"#",1)) {      
      bDone=1;
      }

    /* Convert a text-form MIB init file to a dBm database */
    /* This blocks until done, and crashes out if not successful */
    /* -- blocking important so that mcic doesn't start before dbm is ready */
    if (!strncmp(token[0],"mibinit",7)) {
      bDone=1; /* remember that we found a match */
      printf("[%s] %s %s\n",ME,token[0],token[1]);
      
      pid = fork();               /* create duplicate process */
      switch (pid) {
        case -1: /* error */
          printf("[%s] FATAL: fork for mibinit failed\n",ME);
          exit(EXIT_FAILURE);
        case 0: /* fork() succeeded; we are now in the child process */
          err = execl("./dat2dbm","dat2dbm",token[1],token[2],token[3],token[4],NULL); /* launch dat2dbm */
          /* if we get to this point then we failed to launch dat2dbm */
          if (err==-1) {
            printf("[%s] FATAL: failed to exec() dat2dbm for %s\n",ME,token[1]); 
            }     
          exit(EXIT_FAILURE);
          break; 
        default: /* fork() succeeded; we are now in the parent process */        
          {
	  int stat_val;
          pid_t child_pid;
          child_pid = wait(&stat_val); /* this blocks until dat2dbm is done */
          if (!WIFEXITED(stat_val)) {
            printf("[%s] FATAL: dat2dbm's process exited abnormally\n",ME);     
            exit(EXIT_FAILURE);           
            }
          if (WEXITSTATUS(stat_val)==EXIT_FAILURE) {
            printf("[%s] FATAL: dat2dbm's process says it failed\n",ME);     
            exit(EXIT_FAILURE);           
            }  
          sleep(1); /* This prevents a problem in which ms_mcic tries to 
                       to open the database before the relevant file locks or
                       permissions are settled, resulting in an "open" error */       
          }
          break;
        } /* switch (pid) */
      }

    /* MCS Common ICD client */
    if (!strncmp(token[0],"mcic",4)) {
      bDone=1; /* remember that we found a match */
      printf("[%s] %s %s\n",ME,token[0],token[1]);

      nsid = nsid+1; /* one more subsystem has been defined */
      if (nsid>LWA_MAX_SID) {
        printf("[%s] FATAL: nsid=%d is greater than LWA_MAX_SID\n",ME,nsid);      
        exit(EXIT_FAILURE);
        }

      /* get system ID */
      sid[nsid-1] = LWA_getsid(token[1]);
      if (sid[nsid-1]==0) {
        printf("[%s] FATAL: LWA_getsid(%s) failed\n",ME,token[1]);      
        exit(EXIT_FAILURE);
        } 
      //printf("[%s] %s has sid=%d\n",ME,token[1],sid[nsid-1]);

      pid = fork();   /* create duplicate process */
      switch (pid) {

        case -1: /* error */

          printf("[%s] FATAL: fork for mcic failed\n",ME);
          exit(EXIT_FAILURE);

        case 0: /* fork() succeeded; we are now in the child process */

          err = execl("./ms_mcic","ms_mcic",token[1],NULL); /* launch mcic */
          /* if we get to this point then we failed to launch mcic */
          if (err==-1) {
            printf("[%s] FATAL: failed to exec() mcic for %s\n",ME,token[1]); 
            }     
          exit(EXIT_FAILURE);
          break; 

        default: /* fork() succeeded; we are now in the parent process */

          /* stall until the associated ms_mcic process responds on the message queue */
          if ( msgrcv( mqid, (void *)&mq_msg, LWA_msz(), sid[nsid-1], 0) == -1) {
            printf("[%s] FATAL: Could not msgrcv()\n",ME);
            exit(EXIT_FAILURE);
            }
          //printf("[%s] From message queue [%ld]: <%s>\n",ME,mq_msg.sid,mq_msg.data);
          printf("[%s] From %s's MQ: <%s>\n",ME,LWA_sid2str(mq_msg.sid),mq_msg.data);

          /* At this point we know process is alive and we can receive */
          /*   messages from it. So now: */
          /* Open new queue for message-passing in the other direction */

          /* Set up transmit message queue */
          mqtkey = MQ_MS_KEY + sid[nsid-1];
          //printf("[%s] mqtkey = %d\n",ME,mqtkey);
          mqt = msgget( mqtkey, 0666 | IPC_CREAT );
          if (mqt==-1) {
            printf("[%s] FATAL: Could not msgget() tx message queue\n",ME);
            exit(EXIT_FAILURE);
            }

          /* Send ping */
          mq_msg.sid = (long int) sid[nsid-1];
          mq_msg.cid = LWA_CMD_PNG;
          mq_msg.ref = 0;                /* doesn't matter since this isn't a response */ 
          strcpy(mq_msg.data,"ping!");
          if ( msgsnd( mqt, (void *)&mq_msg, LWA_msz(), 0) == -1 ) {
            printf("[%s] FATAL: Could not msgsnd()\n",ME);
            exit(EXIT_FAILURE);
            } 

          /* Stall until the associated ms_mcic process responds on the message queue */
          if ( msgrcv( mqid, (void *)&mq_msg, LWA_msz(), sid[nsid-1], 0) == -1) {
            printf("[%s] FATAL: Could not msgrcv()\n",ME);
            exit(EXIT_FAILURE);
            }
          //printf("[%s] From message queue [%ld]: <%s>\n",ME,mq_msg.sid,mq_msg.data);
          printf("[%s] From %s's MQ: <%s>\n",ME,LWA_sid2str(mq_msg.sid),mq_msg.data);

          break;

        } /* switch (pid) */
      }

    /* if we didn't find a match we should print a warning */
    if (!bDone) { 
      printf("[%s] WARNING: ms_init_file command <%s> not recognized (ignored)\n",ME,token[0]);
      } else {
      //printf("[%s] Did this: %s %s\n",ME,token[0],token[1]);     
      }

    } /* while (!feof(fid)) */

  fclose(fid);  
  printf("[%s] Completed ms_init start-up script\n",ME);
  printf("[%s] Handing off to ms_exec\n",ME);

  /* encode list of subsystem IDs activated for use in ms_exec invocation*/
  /* encoded as a single base-10 number, whose bits in base-2 representation */
  /* indicate the presense/absence of that subsystem ID */
  sidsum = 0;
  for (n=0;n<nsid;n++) sidsum += (1 << (sid[n]-1));
  sprintf(sidlist,"%ld",sidsum); 
  //printf("sidlist: <%s>\n",sidlist);

  /* Launch executive */
  ms_exec_pid = fork();               /* create duplicate process */
  switch (ms_exec_pid) {
    case -1: /* error */
      printf("[%s] FATAL: fork for ms_exec failed\n",ME);
      exit(EXIT_FAILURE);
    case 0: /* fork() succeeded; we are now in the child process */
      //err = execl("./ms_exec","ms_exec",NULL); /* launch ms_exec */
      err = execl("./ms_exec","ms_exec",sidlist,NULL); /* launch ms_exec */
      /* if we get to this point then we failed to launch mcic */
      if (err==-1) {
        printf("[%s] FATAL: failed to exec() ms_exec\n",ME); 
        }     
      exit(EXIT_FAILURE);
      break; 
    default: /* fork() succeeded; we are now in the parent process */
      break;
    } /* switch (ms_exec_pid) */
  
  /* process continues to run */
  sleep(3);

  printf("[%s] exit(EXIT_SUCCESS)\n",ME);  
  exit(EXIT_SUCCESS);
  } /* main() */

//==================================================================================
//=== HISTORY ======================================================================
//==================================================================================
// ms_init.c: S.W. Ellingson, Virginia Tech, 2009 Aug 02
//   .1 Cleaning up console messages (svn rev 22) (svn rev 23)
// ms_init.c: S.W. Ellingson, Virginia Tech, 2009 Jul 21
//   .1 implementing expanded command line for dat2dbm (IP_ADDRESS etc.)
// ms_init.c: S.W. Ellingson, Virginia Tech, 2009 Jul 20
//   .1 init file can now have >1 argument
// ms_init.c: S.W. Ellingson, Virginia Tech, 2009 Jul 17
//   .1 change from mq_struct to LWA_cmd_struct for message passing
// ms_init.c: S.W. Ellingson, Virginia Tech, 2009 Jul 13
//   .1 bringing into common codeset; mib.h -> LWA_MCS.h
// ms_init.c: S.W. Ellingson, Virginia Tech, 2009 Jul 07 
//   .1 expanding use of message queues
//   .2 mc_mcic handshake using message queue
//   .3 implementing null subsystems
// ms_init.c: S.W. Ellingson, Virginia Tech, 2009 Jul 05 
//   -- adding mibinit command
//   -- added message queue (very preliminary)
// ms_init.c: S.W. Ellingson, Virginia Tech, 2009 Jul 01
//   -- ms_exec now forks; ms_init stays alive 
// ms_init.c: S.W. Ellingson, Virginia Tech, 2009 Jun 27 

//==================================================================================
//=== BELOW THIS LINE IS SCRATCH ===================================================
//==================================================================================


