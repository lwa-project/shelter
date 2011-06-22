// ms_makeMIB_DP.c: S.W. Ellingson, Virginia Tech, 2009 Aug 16
// ---
// COMPILE: gcc -o ms_makeMIB_DP ms_makeMIB_DP.c
// ---
// COMMAND LINE: ms_makeMIB_DP
//
// ---
// REQUIRES: 
// ---
// Creates DP_MIB_init.dat.  
// See end of this file for history.

#include <stdio.h>

//#include "LWA_MCS.h"

#define MY_NAME "ms_makeMIB_DP (v.20090816.1)"
#define ME "11" 

main ( int narg, char *argv[] ) {

  /*=================*/
  /*=== Variables ===*/
  /*=================*/

  FILE *fp;
  int i;


  /*==================*/
  /*=== Initialize ===*/
  /*==================*/
    
  /* First, announce thyself */
  printf("I am %s [%s]\n",MY_NAME,ME);

  //if (narg>1) { 
  //  sscanf(argv[1],"%d",&n_ARXSUPPLY_NO);
  //  } else {
  //  printf("[%s] FATAL: ARXSUPPLY-NO not provided\n",ME);
  //  return;
  //  } 

  /* create file */
  fp = fopen("DP__MIB_init.dat","w");

  /* lay in added MIB Entries */
  //fprintf(fp,"B 0.9  \t\tMCS-SUPPLEMENTAL 	NUL 	NUL 	NUL\n");
  //fprintf(fp,"V 0.9.1\t\tN-BOARDS	 	UNK 	a3 	a3\n");  // Number of boards (see INI command)

  /* lay in MCS-RESERVED */

  fprintf(fp,"B 1 		MCS-RESERVED 		NUL 	NUL 	NUL\n");
  fprintf(fp,"V 1.1 		SUMMARY			UNK	a7	a7\n");
  fprintf(fp,"V 1.2 		INFO      		UNK	a256	a256\n");
  fprintf(fp,"V 1.3 		LASTLOG   		UNK	a256	a256\n");
  fprintf(fp,"V 1.4 		SUBSYSTEM 		UNK	a3	a3\n");
  fprintf(fp,"V 1.5 		SERIALNO  		UNK	a5	a5\n");
  fprintf(fp,"V 1.6 		VERSION   		UNK	a256	a256\n");

  /* DP-specific */

  fprintf(fp,"V 2 		TBW_STATUS		0	i1u	i1u\n");

  fprintf(fp,"V 3 		NUM_TBN_BITS		1	i1u	i1u\n");

  fprintf(fp,"V 4.1 		NUM_DRX_TUNINGS		2	i1u	i1u\n");
  fprintf(fp,"V 4.2 		NUM_BEAMS		4	i1u	i1u\n"); 
  fprintf(fp,"V 4.3 		NUM_STANDS		260	i2u	i2u\n");
  fprintf(fp,"V 4.4 		NUM_BOARDS		255	i1u	i1u\n");
  fprintf(fp,"V 4.5 		BEAM_FIR_COEFFS		32	i1u	i1u\n");
  fprintf(fp,"B 4.6 		T_NOM			NUL	NUL	NUL\n");
  fprintf(fp,"V 4.6.1\t\tT_NOM1			0	i2u	i2u\n");
  fprintf(fp,"V 4.6.2\t\tT_NOM2			1	i2u	i2u\n");
  fprintf(fp,"V 4.6.3\t\tT_NOM3			2	i2u	i2u\n");
  fprintf(fp,"V 4.6.4\t\tT_NOM4			4	i2u	i2u\n");
  fprintf(fp,"V 4.6.5\t\tT_NOM5			8	i2u	i2u\n");
  fprintf(fp,"V 4.6.6\t\tT_NOM6			16	i2u	i2u\n");
  fprintf(fp,"V 4.6.7\t\tT_NOM7			32	i2u	i2u\n");
  fprintf(fp,"V 4.6.8\t\tT_NOM8			64	i2u	i2u\n");
  fprintf(fp,"V 4.6.9\t\tT_NOM9			128	i2u	i2u\n");
  fprintf(fp,"V 4.6.10\tT_NOM10			256	i2u	i2u\n");
  fprintf(fp,"V 4.6.11\tT_NOM11			512	i2u	i2u\n");
  fprintf(fp,"V 4.6.12\tT_NOM12			1024	i2u	i2u\n");
  fprintf(fp,"V 4.6.13\tT_NOM13			2048	i2u	i2u\n");
  fprintf(fp,"V 4.6.14\tT_NOM14			4096	i2u	i2u\n");
  fprintf(fp,"V 4.6.15\tT_NOM15			32768	i2u	i2u\n");
  fprintf(fp,"V 4.6.16\tT_NOM16			65535	i2u	i2u\n");

  fprintf(fp,"B 5 		FIR			NUL	NUL	NUL\n");
  fprintf(fp,"V 5.1 		FIR1			NUL	r1024	r1024\n");
  fprintf(fp,"V 5.2 		FIR2			NUL	r1024	r1024\n");
  fprintf(fp,"V 5.3 		FIR3			NUL	r1024	r1024\n");
  fprintf(fp,"V 5.4 		FIR4			NUL	r1024	r1024\n");
  fprintf(fp,"V 5.5 		FIR_CHAN_INDEX		0	i2u	i2u\n");

  fprintf(fp,"B 6 		CLK_VAL			0	i4u	i4u\n");
 
  for ( i=0; i<9; i++ ) {
    fprintf(fp,"B 7.%d\t\tANT%d_STAT 		NUL 	NUL 	NUL\n",i+1,i+1); 
    fprintf(fp,"V 7.%d.1\t\tANT%d_RMS\t\t0 	f4 	f4\n",i+1,i+1);
    fprintf(fp,"V 7.%d.2\t\tANT%d_DCOFFSET\t\t0 	f4 	f4\n",i+1,i+1);
    fprintf(fp,"V 7.%d.3\t\tANT%d_SAT\t\t0 	i4u 	i4u\n",i+1,i+1);
    }
  for ( i=9; i<520; i++ ) {
    fprintf(fp,"B 7.%d\t\tANT%d_STAT 		NUL 	NUL 	NUL\n",i+1,i+1); 
    fprintf(fp,"V 7.%d.1\tANT%d_RMS\t\t0 	f4 	f4\n",i+1,i+1);
    fprintf(fp,"V 7.%d.2\tANT%d_DCOFFSET\t\t0 	f4 	f4\n",i+1,i+1);
    fprintf(fp,"V 7.%d.3\tANT%d_SAT\t\t99 	i4u 	i4u\n",i+1,i+1);
    }
  fprintf(fp,"V 7.521 	STAT_SAMP_SIZE 		0 	i4u 	i4u\n"); 

  fprintf(fp,"B 8 		BOARD_STAT		NUL	NUL	NUL\n");
  for ( i=0; i<28; i++ ) {
    fprintf(fp,"V 8.%d\t\tBOARD%d_STAT 		0 	i4u 	i4u\n",i+1,i+1); 
    }

  //fprintf(fp,"V 8.29\t\tBOARD29_STAT 		1 	i4u 	i4u\n"); 
  //fprintf(fp,"V 8.29\t\tBOARD30_STAT 		255 	i4u 	i4u\n");
  //fprintf(fp,"V 8.29\t\tBOARD31_STAT 		65536 	i4u 	i4u\n");
  //fprintf(fp,"V 8.29\t\tBOARD32_STAT 		16777215 	i4u 	i4u\n");
  //fprintf(fp,"V 8.29\t\tBOARD33_STAT 		3999999999 	i4u 	i4u\n"); 

  fprintf(fp,"V 9 		CMD_STAT 		NUL 	r606 	r606\n"); 

  close(fp);
  } /* main() */

//==================================================================================
//=== HISTORY ======================================================================
//==================================================================================
// ms_makeMIB_DP.c: S.W. Ellingson, Virginia Tech, 2009 Aug 16
//   .1: Modifying choice of type_dbm format specifiers
// ms_makeMIB_DP.c: S.W. Ellingson, Virginia Tech, 2009 Aug 14
//   .1: Initial version

//==================================================================================
//=== BELOW THIS LINE IS SCRATCH ===================================================
//==================================================================================

