#!/usr/bin/env python
#
# Author: Timothy Zimmerman (timothy.zimmerman@nist.gov)
# Organization: National Institute of Standards and Technology
# U.S. Department of Commerce
# License: Public Domain
#
# See README for description and information

from pymodbus.server.async import StartTcpServer
from pymodbus.device       import ModbusDeviceIdentification
from pymodbus.datastore    import ModbusSequentialDataBlock
from pymodbus.datastore    import ModbusSlaveContext, ModbusServerContext
from twisted.internet      import reactor
from twisted.internet.task import LoopingCall
from machine.py import Machine

import time, signal, sys
import Adafruit_BBIO.GPIO as GPIO

def signal_handler(signal, frame):
    print "Received the shutdown signal..."
    reactor.stop()
    sys.exit()

# Iterate the state machine (used by LoopingCall)
def machine_iterate(a):
    a[0].iterate(a[1], a[2], GPIO.input("GPIO0_7"))

def main():
    # Configure signal handler for KILL (CTRL+C)
    signal.signal(signal.SIGINT, signal_handler)

    # Define requency of machine iterations
    SIMULATION_FREQ_HZ = 10

    # Configure the MODBUS server datastore
    store = ModbusSlaveContext(
        di = ModbusSequentialDataBlock(1, [0]*5),
        co = ModbusSequentialDataBlock(1, [0]*4),
        hr = ModbusSequentialDataBlock(1, [1]*3),
        ir = ModbusSequentialDataBlock(1, [0]*6))
    context = ModbusServerContext(slaves=store, single=True)

    # Configure logging
    log.setLevel(logging.INFO)
    logging.basicConfig(format='%(asctime)-15s %(levelname)s:%(message)s',level=logging.INFO)

    # Configure the I/O pin on the BBB
    # TODO: Create a device tree overlay for a different pin with a pull-up
    GPIO.setup("GPIO0_7", GPIO.IN)

    # TODO: Add configuration file to obtain these parameters, and pass to object
    machine = Machine(6.0)

    # Create the loop using the Twisted framework
    loop = LoopingCall(f=machine_iterate, a=(machine, context))
    loop.start((1.0/SIMULATION_FREQ_HZ), now=False)

    # Start the MODBUS server
    StartTcpServer(context)

if __name__ == '__main__':
    main()
