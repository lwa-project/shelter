#!/bin/bash

case "$1" in
'start')
  date >> /lwa/runtime/start
  echo "starting shl_cmnd.py" >> /lwa/runtime/runtime.log

  cd /lwa/software
  python /lwa/software/shl_cmnd.py -c /lwa/software/defaults.cfg -d -l /lwa/runtime/runtime.log
  ;;

'stop')
  pid=`pgrep -f shl_cmnd.py`
  kill -9 $pid
  ;;
esac
