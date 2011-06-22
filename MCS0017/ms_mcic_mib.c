// ms_mcic_mib.c: S.W. Ellingson, Virginia Tech, 2009 Jul 31
// ---
// COMPILE: This file is #include'd in ms_mcic.c.
// ---
// COMMAND LINE: (not applicable)
// ---
// REQUIRES: see ms_mcic.c
// ---
// See end of this file for history.

/* ======================================================================= */
/* ======================================================================= */
/* ======================================================================= */
int LWA_dbm_fetch( 
                  DBM *dbm_ptr,              /* pointer to an open dbm file */
                  char *label,               /* key */
                  struct dbm_record *record  /* (output) record for that key */                   
                 ) {
  datum datum_key;
  datum datum_data;
  char key[MIB_LABEL_FIELD_LENGTH];
  int eMIBerror = LWA_MIBERR_OK;

  strncpy(key,label,MIB_LABEL_FIELD_LENGTH);
  datum_key.dptr   = (void *) key;
  datum_key.dsize  = strlen(key);
  datum_data = dbm_fetch(dbm_ptr,datum_key);
  if (datum_data.dptr) {
      memcpy( record, datum_data.dptr, datum_data.dsize );
    } else { 
      eMIBerror = eMIBerror | LWA_MIBERR_CANTFETCH;
      printf("[%s/%d] LWA_dbm_fetch() failed; label=<%s>\n",ME,getpid(),label);
    }

  return eMIBerror;
  }

/* ======================================================================= */
/* ======================================================================= */
/* ======================================================================= */
int LWA_dbm_store( 
                  DBM *dbm_ptr,              /* pointer to an open dbm file */
                  char *label,               /* key */
                  struct dbm_record *record  /* (output) record for that key */                    
                 ) {
  datum datum_key;
  datum datum_data;
  char key[MIB_LABEL_FIELD_LENGTH];
  int eMIBerror = LWA_MIBERR_OK;
  int result;
  struct timezone tz; /* from sys/time.h; included in LWA_MCS.h */

  gettimeofday( &(record->last_change), &tz ); /* updating .last_change */

  strncpy(key,label,MIB_LABEL_FIELD_LENGTH);
  datum_key.dptr   = (void *) key;
  datum_key.dsize  = strlen(key);
  datum_data.dptr  = (void *) record;
  datum_data.dsize = sizeof(struct dbm_record); 
    
  result = dbm_store( dbm_ptr, datum_key, datum_data, DBM_REPLACE);
  if (result != 0) {
    eMIBerror = eMIBerror | LWA_MIBERR_CANTSTORE;
    printf("[%s/%d] LWA_dbm_store() failed; label=<%s>\n",ME,getpid(),label);
    }

  return eMIBerror;
  }


/* ======================================================================= */
/* ======================================================================= */
/* ======================================================================= */
int LWA_mibupdate_RPT( 
                      DBM *dbm_ptr,    /* pointer to an open dbm file */
                      char *cmdata,    /* the DATA field from the *command* message */
                                       /* For RPT, this should be a MIB label */
                      char *r_comment, /* R-COMMENT */
                                       /* For RPT, this should be the returned value */
                      int datalen      /* number of significant bytes in r_comment, or -1 if a string */
                     ) {
  /* This is the handler for the RPT command.  (Same for all subsytems) */

  struct dbm_record record;
  int eMIBerror = LWA_MIBERR_OK;

  if (datalen==-1) datalen = strlen(r_comment);

  eMIBerror = eMIBerror | LWA_dbm_fetch( dbm_ptr, cmdata, &record );
  //strncpy( record.val, r_comment, MIB_VAL_FIELD_LENGTH );  
  memset(record.val, '\0', sizeof(record.val)); 
  memcpy(record.val, r_comment, datalen);
  eMIBerror = eMIBerror | LWA_dbm_store( dbm_ptr, cmdata, &record );

  return eMIBerror;
  } 


/* ======================================================================= */
/* ======================================================================= */
/* ======================================================================= */
/* #include's for subsystem-specific handlers go here */
/* Each file has the form "ms_mcic_XXX.c" where XXX is the subsystem ID */
/* Each file contains just one function call, "LWA_mibupdate_XXX()" */ 
#include "ms_mcic_SHL.c" /* LWA_mibupdate_SHL() */
#include "ms_mcic_ASP.c" /* LWA_mibupdate_ASP() */
#include "ms_mcic_DP_.c" /* LWA_mibupdate_DP_() */

/* ======================================================================= */
/* ======================================================================= */
/* ======================================================================= */
int mib_update( 
                long int  sid,       /* subsystem, so we know what handler to use */
                int       cid,       /* command, so handler knows how to deal with it */ 
                struct timeval tv,
                int       eAccept,   /* R-RESPONSE, except enumerated */
                char     *r_summary, /* R-SUMMARY */
                char     *r_comment, /* R-COMMENT */
                int      datalen,    /* number of significant bytes in "r_comment", or -1 if a string */
                char     *cmdata,    /* the DATA field from the *command* message */
                char     *dbm_filename
              ) {
  /* note that most of these arguments mirror arguments in LWA_cmd_struct; hence the type assignments */
  /* Updates MIB based on response */
  /* Will always update SUMMARY.  */
  /* Other things get updated if eAccept = LWA_MSELOG_TP_SUCCESS or LWA_MSELOG_TP_DONE_UNK */

  DBM *dbm_ptr;
  struct dbm_record record;

  int eMIBerror = LWA_MIBERR_OK; /* returned value; see LWA_MIBERR_* in LWA_MCS.h */

  /* print out what was passed here: */
  //printf("[%s/%d] mib_update() rcvd: sid=%ld\n",ME,getpid(),sid);
  //printf("[%s/%d] mib_update() rcvd: cid=%d \n",ME,getpid(),cid);
  //printf("[%s/%d] mib_update() rcvd: eAccept=%d \n",ME,getpid(),eAccept);
  //printf("[%s/%d] mib_update() rcvd: r_summary=<%s> \n",ME,getpid(),r_summary);
  //printf("[%s/%d] mib_update() rcvd: r_comment=<%s> \n",ME,getpid(),r_comment);
  //printf("[%s/%d] mib_update() rcvd: cmdata=<%s> \n",ME,getpid(),cmdata);
  //printf("[%s/%d] mib_update() rcvd: dbm_filename=<%s> \n",ME,getpid(),dbm_filename);

  /* Open dbm file */
  dbm_ptr = dbm_open(dbm_filename, O_RDWR); /* open for both read and write */
  if (!dbm_ptr) { /* failed to open database */

      eMIBerror = LWA_MIBERR_CANTOPEN;
      printf("[%s/%d] mib_update() failed to open dbm <%s>\n",ME,getpid(),dbm_filename);

    } else { /* successfully opened database */

      //printf("[%s/%d] mib_update: r_summary=<%s> r_comment=<%s> cmdata=<%s>\n",ME,getpid(), r_summary, r_comment, cmdata );

      /* update SUMMARY (since this is ALWAYS part of the response) */
      eMIBerror = eMIBerror | LWA_dbm_fetch( dbm_ptr, "SUMMARY", &record );
      strncpy( record.val, r_summary, MIB_VAL_FIELD_LENGTH );  
      eMIBerror = eMIBerror | LWA_dbm_store( dbm_ptr, "SUMMARY", &record );

      /* If eAccept == LWA_MSELOG_TP_SUCCESS or LWA_MSELOG_TP_DONE_UNK, */
      /* then we figure out what MIB entry that refers to, and update it */

      if ( (eAccept == LWA_MSELOG_TP_SUCCESS ) || 
           (eAccept == LWA_MSELOG_TP_DONE_UNK)   ) {

        switch (cid) {

          case LWA_CMD_PNG:
          case LWA_CMD_SHT:
            /* for PNG and SHT, there is nothing else to do.  So trap these here */
            /* and only proceed to subsystem handlers for other commands */
            break;

          case LWA_CMD_RPT:
            /* for RPT, can handle that using the same handler for all subsystems */
            eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, cmdata, r_comment, datalen ); 
            break;

          default:
            /* for any other command, we may need a subsystem-specific handler */

            switch (sid) {

              case LWA_SID_NU1:
              case LWA_SID_NU2: 
              case LWA_SID_NU3: 
              case LWA_SID_NU4: 
              case LWA_SID_NU5: 
              case LWA_SID_NU6: 
              case LWA_SID_NU7: 
              case LWA_SID_NU8: 
              case LWA_SID_NU9:  
                /* The mock subsystems support only PNG, RPT, and SHT.  If we're here, */
                /* Then something has gone wrong */  
                eMIBerror = eMIBerror | LWA_MIBERR_SID_CID;              
                break;

              case LWA_SID_MCS:
                /* We're MCS.  So if we get this, */
                /* Then something has gone wrong */ 
                 eMIBerror = eMIBerror | LWA_MIBERR_SID_CID; 
                 break;

              case LWA_SID_SHL:
                eMIBerror = eMIBerror | LWA_mibupdate_SHL( dbm_ptr, cid, cmdata, r_comment, datalen );                
                break;

              case LWA_SID_ASP:
                eMIBerror = eMIBerror | LWA_mibupdate_ASP( dbm_ptr, cid, cmdata, r_comment, datalen );                
                break;

              case LWA_SID_DP_:
                eMIBerror = eMIBerror | LWA_mibupdate_DP_( dbm_ptr, cid, cmdata, r_comment, datalen );                
                break;

              default:
                 eMIBerror = eMIBerror | LWA_MIBERR_SID_UNK; 
                 break;

              } /* switch (sid) */

            break;

          } /* switch (cid) */         

        } /* if ( (eAccept */

      /* Close dbm file */
      dbm_close(dbm_ptr);
          
    } /* if (!dbm_ptr) */

  return eMIBerror;
  }


//==================================================================================
//=== HISTORY ======================================================================
//==================================================================================
// ms_mcic_mib.c: S.W. Ellingson, Virginia Tech, 2009 Aug 16
//   Added DP
// ms_mcic_mib.c: S.W. Ellingson, Virginia Tech, 2009 Aug 06
//   Added ASP
// ms_mcic_mib.c: S.W. Ellingson, Virginia Tech, 2009 Aug 02
//   Cleanup of console messages (svn rev 23)
// ms_mcic_mib.c: S.W. Ellingson, Virginia Tech, 2009 Jul 31
//   Renamed since this wasn't really header file  (svn rev 17,18)
// ms_mcic.h: S.W. Ellingson, Virginia Tech, 2009 Jul 29
//   Consolidated fetch/store code segments into function calls
//   Added code for routing to subsystem handlers for updating MIB dbm (svn rev 15)
// ms_mcic.h: S.W. Ellingson, Virginia Tech, 2009 Jul 28 
//   Initial version; formed from segment cut out of ms_mcic.c (svn rev 11)
//   Update mib_update() args to include timeval (svn rev 13)
//   Adding some error-checking (svn rev 14)

//==================================================================================
//=== BELOW THIS LINE IS SCRATCH ===================================================
//==================================================================================
//
