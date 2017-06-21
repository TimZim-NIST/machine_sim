#!/bin/bash
# Author:       Timothy Zimmerman
# Organization: National Institute of Standards and Technology
#               U.S. Department of Commerce
# License:      Public Domain
# Description:
# Simple script to push updated code to our Beaglebone Black
# machine simulators. To avoid constant requests for the user
# password from scp, make sure to configure a ssh key.

function usage
{
  echo "usage: update [ all | 1 | 2 | 3 | 4 ]"
}
 
function push
{
  scp -q ./*.{py,sh} machine@station$STATION:/home/machine/Projects/machine_sim && echo "[OK] Updated Station $STATION" || echo "[ERROR] Failed to update Station $STATION"
} 

if [ $# != 1 ]; then
  echo "[ERROR] Script expects one argument."
  usage
  exit 1
fi

echo "Starting update..."
cd ~/Projects/machine_sim

case $1 in
  all )
    for i in `seq 1 4`;
    do
      STATION=$i
      push
    done
    ;;
  [1-4] )
    STATION=$1
    push
    ;;
  * )
    echo "[ERROR] Invalid argument."
    usage
    ;;
esac
