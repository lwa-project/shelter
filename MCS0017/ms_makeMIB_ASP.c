// ms_makeMIB_ASP.c: S.W. Ellingson, Virginia Tech, 2009 Aug 14
// ---
// COMPILE: gcc -o ms_makeMIB_ASP ms_makeMIB_ASP.c
// ---
// COMMAND LINE: ms_makeMIB_ASP <ARXSUPPLY-NO> <FEESUPPLY_NO>  <TEMP-SENSE-NO>
//
// ---
// REQUIRES: 
// ---
// Creates ASP_MIB_init.dat.  
// See end of this file for history.

#include <stdio.h>

//#include "LWA_MCS.h"

#define MY_NAME "ms_makeMIB_ASP (v.20090814.1)"
#define ME "10" 

main ( int narg, char *argv[] ) {

  /*=================*/
  /*=== Variables ===*/
  /*=================*/

  int n_ARXSUPPLY_NO = 0;
  int n_FEESUPPLY_NO = 0;
  int n_TEMPSENSE_NO = 0;

  FILE *fp;
  int i;


  /*==================*/
  /*=== Initialize ===*/
  /*==================*/
    
  /* First, announce thyself */
  printf("I am %s [%s]\n",MY_NAME,ME);

  if (narg>1) { 
    sscanf(argv[1],"%d",&n_ARXSUPPLY_NO);
    } else {
    printf("[%s] FATAL: ARXSUPPLY-NO not provided\n",ME);
    return;
    } 
  if (narg>2) { 
    sscanf(argv[2],"%d",&n_FEESUPPLY_NO);
    } else {
    printf("[%s] FATAL: FEESUPPLY_NO not provided\n",ME);
    return;
    } 
  if (narg>3) { 
    sscanf(argv[3],"%d",&n_TEMPSENSE_NO);
    } else {
    printf("[%s] FATAL: TEMPSENSE_NO not provided\n",ME);
    return;
    } 


  /* create file */
  fp = fopen("ASP_MIB_init.dat","w");

  /* lay in added MIB Entries */
  fprintf(fp,"B 0.9  \t\tMCS-SUPPLEMENTAL 	NUL 	NUL 	NUL\n");
  fprintf(fp,"V 0.9.1\t\tN-BOARDS	 	UNK 	a3 	a3\n");  // Number of boards (see INI command)

  /* lay in MCS-RESERVED */
  fprintf(fp,"B 1 		MCS-RESERVED 		NUL 	NUL 	NUL\n");
  fprintf(fp,"V 1.1 		SUMMARY			UNK	a7	a7\n");
  fprintf(fp,"V 1.2 		INFO      		UNK	a256	a256\n");
  fprintf(fp,"V 1.3 		LASTLOG   		UNK	a256	a256\n");
  fprintf(fp,"V 1.4 		SUBSYSTEM 		UNK	a3	a3\n");
  fprintf(fp,"V 1.5 		SERIALNO  		UNK	a5	a5\n");
  fprintf(fp,"V 1.6 		VERSION   		UNK	a256	a256\n");

  /* ASP-POWER */
  fprintf(fp,"B 2 		ASP-POWER 		NUL 	NUL 	NUL\n");
  fprintf(fp,"B 2.1 		ARXSUPPLY-INFO 		NUL 	NUL 	NUL\n");
  fprintf(fp,"V 2.1.1		ARXSUPPLY		UNK 	a3 	a3\n");
  fprintf(fp,"V 2.1.2		ARXSUPPLY-NO 		%02d 	a2 	a2\n",n_ARXSUPPLY_NO);
  fprintf(fp,"B 2.1.3		ARXSUPPLY-STATUS	NUL 	NUL 	NUL\n");
  for ( i=0; i<n_ARXSUPPLY_NO; i++) {
    fprintf(fp,"V 2.1.3.%d	ARXPWRUNIT_%d 		UNK 	a256 	a256\n",i+1,i+1);
    }
  fprintf(fp,"V 2.1.4		ARXCURR			0000000 a7 	a7\n");
  fprintf(fp,"B 2.2		FEESUPPLY-INFO		NUL	NUL 	NUL\n");
  fprintf(fp,"V 2.2.1		FEESUPPLY		UNK 	a3 	a3\n");
  fprintf(fp,"V 2.2.2		FEESUPPLY_NO 		%02d 	a2 	a2\n",n_FEESUPPLY_NO);
  fprintf(fp,"B 2.2.3		FEESUPPLY-STATUS	NUL 	NUL 	NUL\n");
  for ( i=0; i<n_FEESUPPLY_NO; i++) {
    fprintf(fp,"V 2.2.3.%d	FEEPWRUNIT_%d 		UNK 	a256 	a256\n",i+1,i+1);
    }
  fprintf(fp,"V 2.1.4		FEECURR			0000000 a7 	a7\n");

  /* ARX-FILTERS */
  fprintf(fp,"B 3 		ARX-FILTERS 		NUL 	NUL 	NUL\n");
  for ( i=0; i<260; i++ ) {
    fprintf(fp,"V 3.%d		FILTER_%d 		3 	a1 	a1\n",i+1,i+1);
    }

  /* ARX-ATTEN */
  fprintf(fp,"B 4 		ARX-ATTEN 		NUL 	NUL 	NUL\n");  
  fprintf(fp,"B 4.1 		ATTEN-1 		NUL 	NUL 	NUL\n");  
  for ( i=0; i<260; i++ ) {
    fprintf(fp,"V 4.1.%d 	AT1_%d\t\t\t00 	a2 	a2\n",i+1,i+1);
    }
  fprintf(fp,"B 4.2 		ATTEN-2 		NUL 	NUL 	NUL\n");  
  for ( i=0; i<260; i++ ) {
    fprintf(fp,"V 4.2.%d 	AT2_%d\t\t\t00 	a2 	a2\n",i+1,i+1);
    }
  fprintf(fp,"B 4.3 		ATTEN-SPLIT 		NUL 	NUL 	NUL\n");  
  for ( i=0; i<260; i++ ) {
    fprintf(fp,"V 4.3.%d 	ATSPLIT_%d		00 	a2 	a2\n",i+1,i+1);
    }

  /* FEE-PWR */
  fprintf(fp,"B 5 		FEE-PWR 		NUL 	NUL 	NUL\n");
  for ( i=0; i<260; i++ ) {
    fprintf(fp,"B 5.%d    \tFEEPWR_%d		NUL 	NUL 	NUL\n",i+1,i+1);
    fprintf(fp,"V 5.%d.1  \tFEEPOL1PWR_%d		UNK 	a3 	a3\n",i+1,i+1);
    fprintf(fp,"V 5.%d.2  \tFEEPOL2PWR_%d		UNK 	a3 	a3\n",i+1,i+1);
    }  
   
  /* ASP-TEMP */
  fprintf(fp,"B 6 		ASP-TEMP 		NUL 	NUL 	NUL\n");
  fprintf(fp,"V 6.1		TEMP-STATUS 		UNK 	a256 	a256\n");
  fprintf(fp,"V 6.2		TEMP-SENSE-NO 		%03d 	a3 	a3\n",n_TEMPSENSE_NO);
  fprintf(fp,"B 6.3		SENSOR-NAME 		NUL 	NUL 	NUL\n");
  for ( i=0; i<n_TEMPSENSE_NO; i++) {
    fprintf(fp,"V 6.3.%d  \tSENSOR-NAME-%d 		UNK 	a256 	a256\n",i+1,i+1);
    }
  fprintf(fp,"B 6.4		SENSOR-DATA 		NUL 	NUL 	NUL\n");
  for ( i=0; i<n_TEMPSENSE_NO; i++) {
    fprintf(fp,"V 6.4.%d  \tSENSOR-DATA-%d 		UNK 	a10 	a10\n",i+1,i+1);
    }

  close(fp);
  } /* main() */

//==================================================================================
//=== HISTORY ======================================================================
//==================================================================================
// ms_makeMIB_ASP.c: S.W. Ellingson, Virginia Tech, 2009 Aug 14
//   .1: Fixed bug
// ms_makeMIB_ASP.c: S.W. Ellingson, Virginia Tech, 2009 Aug 06
//   .1: Initial version

//==================================================================================
//=== BELOW THIS LINE IS SCRATCH ===================================================
//==================================================================================

