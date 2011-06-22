// ms_mcic_DP_.c: S.W. Ellingson, Virginia Tech, 2009 Aug 16
// ---
// COMPILE: This file is #include'd in ms_mcic.h.
// ---
// COMMAND LINE: (not applicable)
// ---
// REQUIRES: see ms_mcic.h.  Assumes functions defined there.
// ---
// See end of this file for history.


int LWA_mibupdate_DP_( 
                      DBM *dbm_ptr,   /* pointer to an open dbm file */
                      int cid,        /* command, so handler knows how to deal with it */ 
                                      /* Note: should not be PNG, RPT, or SHT! */
                      char *cmdata,   /* the DATA field from the *command* message */
                      char *r_comment, /* R-COMMENT */
                      int datalen      /* number of significant bytes in r_comment */
                     ) {
  /* This is the handler for the SHL subsystem. */
  int eMIBerror = LWA_MIBERR_OK;

  //char sMIBlabel[MIB_LABEL_FIELD_LENGTH];

  switch (cid) {

    case LWA_CMD_TBW:
      /* nothing to do, since the DATA field of the outbound command does not */
      /* correspond to anything in the MIB */ 
      //uint8 TBW_BITS;
      //uint32 TBW_TRIG_TIME;
      //uint32 TBW_SAMPLES;
      break;

    case LWA_CMD_TBN:
      /* nothing to do, since the DATA field of the outbound command does not */
      /* correspond to anything in the MIB */ 
      //float32 TBN_FREQ;
      //uint16 TBN_BW;
      //uint16 TBN_GAIN;
      //uint8 sub_slot;
      break;

    case LWA_CMD_DRX:
      /* nothing to do, since the DATA field of the outbound command does not */
      /* correspond to anything in the MIB */ 
      //uint8 DRX_BEAM;
      //uint8 DRX_TUNING;
      //float32 DRX_FREQ;
      //float32 DRX_BW;
      //uint16 DRX_GAIN;
      //uint8 sub_slot;
      break;

    case LWA_CMD_BAM:
      /* nothing to do, since the DATA field of the outbound command does not */
      /* correspond to anything in the MIB */ 
      //uint16 BEAM_ID;
      //uint16 BEAM_DELAY[520];
      //sint16 BEAM_GAIN[260][2][2];
      //uint8 sub_slot;
      break;

    case LWA_CMD_FST:
      /* Thinking about how to handle this.... */
      break;

    case LWA_CMD_CLK:
      /* nothing to do, since the DATA field of the outbound command does not */
      /* correspond to anything in the MIB */ 
      //float32 CLK_SET_TIME
      break;

    case LWA_CMD_INI:
      /* nothing to do */
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
// ms_mcic_DP_.c: S.W. Ellingson, Virginia Tech, 2009 Aug 16
//   initial version

//==================================================================================
//=== BELOW THIS LINE IS SCRATCH ===================================================
//==================================================================================
//
