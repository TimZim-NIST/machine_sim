#!/usr/bin/env python
#
# Author: Timothy Zimmerman (timothy.zimmerman@nist.gov)
# Modified by: Christian Burns (christian.burns@nist.gov)
# Organization: National Institute of Standards and Technology
# U.S. Department of Commerce
# License: Public Domain
#
# See README for description and information

# Check if we are running on a BBB
# Allows us to run the sim on a host without BBB packages
import platform
BBB = (platform.uname()[1] == "beaglebone")

if BBB: import Adafruit_BBIO.GPIO as GPIO

from pymodbus.server.async import StartTcpServer
from pymodbus.device       import ModbusDeviceIdentification
from pymodbus.datastore    import ModbusSequentialDataBlock
from pymodbus.datastore    import ModbusSlaveContext, ModbusServerContext
from twisted.internet      import reactor
from twisted.internet.task import LoopingCall
from machine               import Machine

import time, signal, sys, logging, ConfigParser

# Set this to True to see task performance on BBB pin GPIO1_28 (P9 PIN 12)
PERF_MON = True

# Machine_sim version increment upon major changes
SW_VERSION = 1

def signal_handler(signal, frame):
    print "Received the shutdown signal..."
    reactor.stop()
    sys.exit()

def __get_gpio(pin):
    if BBB:
        return GPIO.input(pin)
    else:
        return 0

# Iterate the state machine (used by LoopingCall)
def machine_iterate(a):
    if BBB and PERF_MON: GPIO.output("GPIO1_28",1)
    a[0].iterate(a[1], __get_gpio("GPIO0_7"))
    if BBB and PERF_MON: GPIO.output("GPIO1_28",0)

def main():
    # Configure signal handler for KILL (CTRL+C)
    signal.signal(signal.SIGINT, signal_handler)

    # Configure the MODBUS server datastore
    store = ModbusSlaveContext(
        di = ModbusSequentialDataBlock(1, [0]*5),
        co = ModbusSequentialDataBlock(1, [0]*5),
        hr = ModbusSequentialDataBlock(1, [1]*3),
        ir = ModbusSequentialDataBlock(1, [0]*7))
    context = ModbusServerContext(slaves=store, single=True)

    # Configure logging
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    logging.basicConfig(format='%(asctime)-15s %(levelname)s:%(message)s')

    # Pull in variables from Configuration file
    try:
        config = ConfigParser.RawConfigParser()
        config.read("./station.cfg")
        cfg_station_number = config.getint("Station","station_number")
        cfg_machine_time = config.getfloat("Station","machine_time")
        cfg_sensor_GPIO = config.get("Station","sensor_GPIO")
        cfg_simulation_frequency = config.getint("Station","simulation_frequency")
    except:
        log.error("Error while parsing configuration file.")
        exit()

    log.info("Station number: " + str(cfg_station_number))
    log.info("Machine time: " + str(cfg_machine_time))
    log.info("Sensor GPIO: " + cfg_sensor_GPIO)
    log.info("Simulation frequency: " + str(cfg_simulation_frequency))


    # Configure the I/O pin on the BBB
    # TODO: Create a device tree overlay for a different pin with a pull-up
<<<<<<< HEAD
    if bbb: GPIO.setup(cfg_sensor_GPIO, GPIO.IN)
=======
    if BBB: GPIO.setup("GPIO0_7",  GPIO.IN)  #
    if BBB and PERF_MON: GPIO.setup("GPIO1_28", GPIO.OUT)
>>>>>>> 1009d7120b11fe77a92939d9c4a4f82f287adbf5

    # TODO: Add configuration file to obtain these parameters, and pass to object
    machine = Machine(cfg_machine_time, SW_VERSION, cfg_station_number)

    # Create the loop using the Twisted framework
    loop = LoopingCall(f=machine_iterate, a=(machine, context))
    loop.start((1.0/cfg_simulation_frequency), now=False)

    # Start the MODBUS server
    StartTcpServer(context)

if __name__ == '__main__':
    main()
