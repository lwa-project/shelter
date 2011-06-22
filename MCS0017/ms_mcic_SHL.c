// ms_mcic_SHL.c: S.W. Ellingson, Virginia Tech, 2009 Aug 06
// ---
// COMPILE: This file is #include'd in ms_mcic.h.
// ---
// COMMAND LINE: (not applicable)
// ---
// REQUIRES: see ms_mcic.h.  Assumes functions defined there.
// ---
// See end of this file for history.
//
// Notes:
//
// 1. For "INI", SET-POINT and DIFFERENTIAL are updated in the local MIB, but
// there is no indication in the local MIB of which racks are available.
// This is because the only way to do this in the SHL MIB structure is through 
// PORTS-AVAILABLE-R1 through -R6, but only SHL knows how many ports 
// are available per rack.  In other words, there is nothing in the local MIB
// which indicates which racks are available even after an INI command. 



int LWA_mibupdate_SHL( 
                      DBM *dbm_ptr,    /* pointer to an open dbm file */
                      int cid,         /* command, so handler knows how to deal with it */ 
                                       /* Note: should not be PNG, RPT, or SHT! */
                      char *cmdata,    /* the DATA field from the *command* message */
                      char *r_comment, /* R-COMMENT */
                      int datalen      /* number of significant bytes in r_comment */
                     ) {
  /* This is the handler for the SHL subsystem. */
  int eMIBerror = LWA_MIBERR_OK;

  char sSHL_SET_POINT[5];
  char sSHL_DIFFERENTIAL[3];
  int b1,b2,b3,b4,b5,b6;
  int eRack;
  int ePort;
  char sState[3];
  char sMIBlabel[MIB_LABEL_FIELD_LENGTH];

  switch (cid) {

    case LWA_CMD_INI:

      /* parse the DATA field of the command message */
      sscanf(cmdata,"%5s&%3s&%1d%1d%1d%1d%1d%1d",
             sSHL_SET_POINT,
             sSHL_DIFFERENTIAL,
             &b1,&b2,&b3,&b4,&b5,&b6);
      //printf("=> %5s&%3s&%1d%1d%1d%1d%1d%1d\n",
      //       sSHL_SET_POINT,
      //       sSHL_DIFFERENTIAL,
      //       b1,b2,b3,b4,b5,b6);      
      eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, "SET-POINT",    sSHL_SET_POINT, strlen(sSHL_SET_POINT) );
      eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, "DIFFERENTIAL", sSHL_DIFFERENTIAL, strlen(sSHL_DIFFERENTIAL) );
      /* Nothing we can do with b1 .. b6; see notes at top of file */

      break;

    case LWA_CMD_TMP:
      sscanf(cmdata,"%5s",sSHL_SET_POINT);     
      eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, "SET-POINT",    sSHL_SET_POINT, strlen(sSHL_SET_POINT) );
      break;

    case LWA_CMD_DIF:
      sscanf(cmdata,"%3s",sSHL_DIFFERENTIAL);     
      eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, "DIFFERENTIAL", sSHL_DIFFERENTIAL, strlen(sSHL_DIFFERENTIAL) );
      break;

    case LWA_CMD_PWR:
      sscanf(cmdata,"%1d%02d%3s",&eRack,&ePort,sState);
      sprintf(sMIBlabel,"PWR-R%1d-%d",eRack,ePort);     
      eMIBerror = eMIBerror | LWA_mibupdate_RPT( dbm_ptr, sMIBlabel, sState, strlen(sState) );
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
// ms_mcic_SHL.c: S.W. Ellingson, Virginia Tech, 2009 Aug 06
//   completed
// ms_mcic_SHL.c: S.W. Ellingson, Virginia Tech, 2009 Jul 30
//   initial (skeleton) version. (svn rev 15)

//==================================================================================
//=== BELOW THIS LINE IS SCRATCH ===================================================
//==================================================================================
//
