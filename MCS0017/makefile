all: ms_init dat2dbm ms_mcic ms_exec msei ms_mdr ms_mdre ms_makeMIB_ASP ms_makeMIB_DP

ms_init: ms_init.c LWA_MCS.h LWA_MCS_subsystems.h
	gcc -o ms_init ms_init.c 

dat2dbm: dat2dbm.c LWA_MCS.h LWA_MCS_subsystems.h
	gcc -o dat2dbm -I/usr/include/gdbm dat2dbm.c -lgdbm_compat -lgdbm 

ms_mcic: ms_mcic.c LWA_MCS.h LWA_MCS_subsystems.h ms_mcic_mib.c ms_mcic_SHL.c ms_mcic_ASP.c ms_mcic_DP_.c 
	gcc -o ms_mcic -I/usr/include/gdbm ms_mcic.c -lgdbm_compat -lgdbm 

ms_exec: ms_exec.c LWA_MCS.h LWA_MCS_subsystems.h ms_exec_log.c 
	gcc -o ms_exec ms_exec.c 

msei: msei.c LWA_MCS.h LWA_MCS_subsystems.h
	gcc -o msei msei.c 

ms_mdr: ms_mdr.c LWA_MCS.h LWA_MCS_subsystems.h
	gcc -o ms_mdr -I/usr/include/gdbm ms_mdr.c -lgdbm_compat -lgdbm 

ms_mdre: ms_mdre.c LWA_MCS.h LWA_MCS_subsystems.h
	gcc -o ms_mdre -I/usr/include/gdbm ms_mdre.c -lgdbm_compat -lgdbm 

ms_makeMIB_ASP: ms_makeMIB_ASP.c 
	gcc -o ms_makeMIB_ASP ms_makeMIB_ASP.c

ms_makeMIB_DP: ms_makeMIB_DP.c 
	gcc -o ms_makeMIB_DP ms_makeMIB_DP.c

clean:
	rm *.dir *.pag
