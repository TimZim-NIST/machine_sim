#!/bin/bash

# Author:       Timothy Zimmerman (timothy.zimmerman@nist.gov)
# Organization: National Institute of Standards and Technology
#               U.S. Department of Commerce
# License:      Public Domain
# Description:
# Simple test to see if the maching_sim is running...
# If we detect that it is not running, we restart it
# This should be executed as a cron job every minute as *ROOT*
#   crontab -e
#   * * * * * /home/machine/Projects/machine_sim/machine_check.sh

RESULT=`pgrep -f machine_sim.py`

if [ -z $RESULT ]; then
  # If the pgrep does not return a result, the python script is NOT running
  # so we need to start it (and dump the output to NULL)
  cd /home/machine/Projects/machine_sim
  ./machine_sim.py &> /dev/null &
fi

exit 1
