#----------------------------------------------------------------------
# setup_dev.sh - create development environment for lwa_user
#                package
#
# $Id: setup_dev.sh 1 2010-01-29 03:35:25Z dwood $
#----------------------------------------------------------------------


# check command line

if [ ${#argv} == 0 ]; then
    root=`pwd`
elif [ ${#argv} == 1 ]; then
    root=$1
else
    echo "usage: source setup_dev.sh [working_dir]"
    return
fi    


# add working dirs to environment

if [ ${#PYTHONPATH} ]; then
    PYTHONPATH=$root:${PYTHONPATH}
else
    PYTHONPATH=$root
fi
export PYTHONPATH

if [ ${#PATH} ]; then
    PATH=$root/lwa_user/scripts:${PATH}
else
    PATH=$root/lwa_user/scripts
fi
export PATH

# build any extension modules (*.so) in-place

# python $root/setup.py build_ext --inplace

      
# clean up
       
unset root
