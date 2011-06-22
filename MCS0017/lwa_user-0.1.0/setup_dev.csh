#----------------------------------------------------------------------
# setup_dev.csh - create development environment for lwa_user
#                 package
#
# $Id: setup_dev.csh 1 2010-01-29 03:35:25Z dwood $
#----------------------------------------------------------------------


# check command line

if ($#argv == 0) then
    set root = $cwd
else if ($#argv == 1) then
    set root = $1
else
    echo "usage: source setup_dev.csh [working_dir]"
    goto done
endif    
    

# add working dirs to environment

if ($?PYTHONPATH == 1) then
    setenv PYTHONPATH "$root":${PYTHONPATH}
else
    setenv PYTHONPATH "$root"
endif

if ($?PATH == 1) then
    setenv PATH "$root"/lwa_user/scripts:${PATH}
else
    setenv PATH "$root"/lwa_user/scripts
endif

# build any extension modules (*.so) in-place

# python "$root"/setup.py build_ext --inplace

# clean up
       
unset root

done:
      
