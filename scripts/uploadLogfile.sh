#!/bin/bash

ls /lwa/runtime/runtime*.gz | xargs -n1 ~ops/uploadLogfile.py
ls /data/*.gz | xargs -n1 ~ops/uploadLogfile.py

