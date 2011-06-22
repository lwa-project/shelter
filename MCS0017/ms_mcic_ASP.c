// ms_mcic_ASP.c: S.W. Ellingson, Virginia Tech, 2009 Aug 06
// ---
// COMPILE: This file is #include'd in ms_mcic.h.
// ---
// COMMAND LINE: (not applicable)
// ---
// REQUIRES: see ms_mcic.h.  Assumes functions defined there.
// ---
// See end of this file for history.




int LWA_mibupdate_ASP( 
                      DBM *dbm_ptr,    /* pointer to an open dbm file */
                      int cid,         /* command, so handler knows how to deal with it */ 
                                       /* Note: should not be PNG, RPT, or SHT! */
                      char *cmdata,    /* the DATA field from the *command* message */
                      char *r_comment, /* R-COMMENT */
                      int  datalen     /* number of significant bytes in "r_comment" */
                     ) {
  /* This is the handler for the SHL subsystem. */
  int eMIBerror = LWA_MIBERR_OK;

  int nBoards;
  char snBoards[3];
  int iStand, iPol, eSet;
  char s2[2];
  char s3[3];
  int i;

  char sMIBlabel[MIB_LABEL_FIELD_LENGTH];

  switch (cid) {

    case LWA_CMD_INI:

      /* parse the DATA field of the command message */
      sscanf(cmdata,"%d",&nBoards);      
      sprintf(snBoards,"%02d",nBoards);
      eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, "N-BOARDS", snBoards, strlen(snBoards) );
      break;

    case LWA_CMD_FIL:
      sscanf(cmdata,"%3d%2d",&iStand,&eSet);
      sprintf(s2,"%02d",eSet);
      if (iStand==0) { /* means "apply to all" */
          for ( i=0; i<260; i++) {
            sprintf(sMIBlabel,"FILTER_%d",i+1);
            eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, sMIBlabel, s2, strlen(s2) );
            }    
        } else { /* apply to indicated stand */
            sprintf(sMIBlabel,"FILTER_%d",iStand);
            eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, sMIBlabel, s2, strlen(s2) );
        }
      break;

    case LWA_CMD_AT1:
      sscanf(cmdata,"%3d%2d",&iStand,&eSet);
      sprintf(s2,"%02d",eSet);
      if (iStand==0) { /* means "apply to all" */
          for ( i=0; i<260; i++) {
            sprintf(sMIBlabel,"AT1_%d",i+1);
            eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, sMIBlabel, s2, strlen(s2) );
            }    
        } else { /* apply to indicated stand */
            sprintf(sMIBlabel,"AT1_%d",iStand);
            eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, sMIBlabel, s2, strlen(s2) );
        }
      break;

    case LWA_CMD_AT2:
      sscanf(cmdata,"%3d%2d",&iStand,&eSet);
      sprintf(s2,"%02d",eSet);
      if (iStand==0) { /* means "apply to all" */
          for ( i=0; i<260; i++) {
            sprintf(sMIBlabel,"AT2_%d",i+1);
            eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, sMIBlabel, s2, strlen(s2) );
            }    
        } else { /* apply to indicated stand */
            sprintf(sMIBlabel,"AT2_%d",iStand);
            eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, sMIBlabel, s2, strlen(s2) );
        }
      break;

    case LWA_CMD_ATS:
      sscanf(cmdata,"%3d%2d",&iStand,&eSet);
      sprintf(s2,"%02d",eSet);
      if (iStand==0) { /* means "apply to all" */
          for ( i=0; i<260; i++) {
            sprintf(sMIBlabel,"ATSPLIT_%d",i+1);
            eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, sMIBlabel, s2, strlen(s2) );
            }    
        } else { /* apply to indicated stand */
            sprintf(sMIBlabel,"ATSPLIT_%d",iStand);
            eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, sMIBlabel, s2, strlen(s2) );
        }
      break;

    case LWA_CMD_FPW:
      sscanf(cmdata,"%3d%d%2d",&iStand,&iPol,&eSet);
      if (eSet==0) { sprintf(s3,"OFF"); } else { sprintf(s3,"ON "); } 
      if (iStand==0) { /* means "apply to all" */
          for ( i=0; i<260; i++) {
            sprintf(sMIBlabel,"FEEPOL%dPWR_%d",iPol,i+1);
            eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, sMIBlabel, s2, strlen(s2) );
            }    
        } else { /* apply to indicated stand */
            sprintf(sMIBlabel,"FEEPOL%dPWR_%d",iPol,iStand);
            eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, sMIBlabel, s2, strlen(s2) );
        }
      break;

    case LWA_CMD_RXP:
      sscanf(cmdata,"%2d",&eSet);  
      if (eSet==0) { sprintf(s3,"OFF"); } else { sprintf(s3,"ON "); }    
      eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, "ARXSUPPLY", s3, strlen(s3) );
      break;

    case LWA_CMD_FEP:
      sscanf(cmdata,"%2d",&eSet);  
      if (eSet==0) { sprintf(s3,"OFF"); } else { sprintf(s3,"ON "); }    
      eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, "FEESUPPLY", s3, strlen(s3) );
      break;

    default:
      /* command was PNG, RPT, SHT, or something not recognized) */
      eMIBerror = eMIBerror | LWA_MIBERR_SID_CID;
      break; 

    } /* switch (cid) */

  return eMIBerror;
  } 


//==================================================================================
//=== HISTORY ======================================================================
//==================================================================================
// ms_mcic_ASP.c: S.W. Ellingson, Virginia Tech, 2009 Aug 06
//   initial version

//==================================================================================
//=== BELOW THIS LINE IS SCRATCH ===================================================
//==================================================================================
//
