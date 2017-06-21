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

if BBB:
    import Adafruit_BBIO.GPIO as GPIO
    import Adafruit_BBIO.UART as UART

from pymodbus.server.async import StartTcpServer
from pymodbus.device       import ModbusDeviceIdentification
from pymodbus.datastore    import ModbusSequentialDataBlock
from pymodbus.datastore    import ModbusSlaveContext, ModbusServerContext
from twisted.internet      import reactor
from twisted.internet.task import LoopingCall
from machine               import Machine

import time, signal, sys, logging, ConfigParser, serial

# Set this to True to see task performance on BBB pin GPIO1_28 (P9 PIN 12)
PERF_MON = False

# Machine_sim version increment upon major changes
SW_VERSION = 1
ser = None
cfg_station_number = None
last_lcd = ""



def signal_handler(signal, frame):
    print "Received the shutdown signal..."
    #ser.close()
    reactor.stop()
    sys.exit()

def __get_gpio(pin):
    if BBB:
        return not GPIO.input(pin)
    else:
        return 1

def lcd_string_creator(machine_station_num, machine_state, machine_progress, machined_parts):
    global last_lcd
    if BBB:
        if ser.isOpen():

    # UNLOADED

                if machined_parts < 10   and machine_state == 0:
                    lcd = "UNLOADED   Sta:" + str(machine_station_num) + "Part Counter:  " + str(machined_parts)
                elif machined_parts > 99 and machine_state == 0:
                    lcd = "UNLOADED   Sta:" + str(machine_station_num) + "Part Counter:"  + str(machined_parts)
                elif machined_parts > 9  and machine_state == 0:
                    lcd = "UNLOADED   Sta:" + str(machine_station_num) + "Part Counter: "   + str(machined_parts)
    # LOADED

                if machined_parts < 10   and machine_state == 1:
                    lcd = "LOADED     Sta:" + str(machine_station_num) + "Part Counter:  " + str(machined_parts)
                elif machined_parts > 99 and machine_state == 1:
                    lcd = "LOADED     Sta:" + str(machine_station_num) + "Part Counter:"  + str(machined_parts)
                elif machined_parts > 9  and machine_state == 1:
                    lcd = "LOADED     Sta:" + str(machine_station_num) + "Part Counter: "   + str(machined_parts)
    # ACTIVE

                total_bars = ""
                bars = int(machine_progress/10)
                total_spaces = ""
                spaces = abs(bars - 13)

                if machine_progress > 0:
                    for i in range(bars):
                        total_bars =  total_bars + b"\xff"
                    for j in range (spaces):
                        total_spaces = total_spaces + " "

                if machine_progress < 10 and machine_state == 2:
                    total_spaces = "              "
                    lcd = "ACTIVE     Sta:" + str(machine_station_num) + total_bars + total_spaces + str(machine_progress) + "%"
                elif machine_progress >= 10 and machine_progress < 100:
                    lcd = "ACTIVE     Sta:" + str(machine_station_num) + total_bars + total_spaces + str(machine_progress) + "%"
    # FINISHED

                if machined_parts < 10   and machine_state == 3:
                    lcd = "FINISHED   Sta:" + str(machine_station_num) + "Part Counter:  " + str(machined_parts)
                elif machined_parts > 99 and machine_state == 3:
                    lcd = "FINISHED   Sta:" + str(machine_station_num) + "Part Counter:"   + str(machined_parts)
                elif machined_parts > 9  and machine_state == 3:
                    lcd = "FINISHED   Sta:" + str(machine_station_num) + "Part Counter: "  + str(machined_parts)
    # STOPPED

                if machined_parts < 10   and machine_state == 4:
                    lcd = "STOPPED    Sta:" + str(machine_station_num) + "Part Counter: " + str(machined_parts)
                elif machined_parts < 99 and machine_state == 4:
                    lcd = "STOPPED    Sta:" + str(machine_station_num) + "Part Counter: " + str(machined_parts)
                elif machined_parts > 9  and machine_state == 4:
                    lcd = "STOPPED    Sta:" + str(machine_station_num) + "Part Counter: " + str(machined_parts)
    # TROUBLE

                if machined_parts < 10   and machine_state == 5:
                    lcd = "TROUBLE    Sta:" + str(machine_station_num) + "Part Counter: " + str(machined_parts)
                elif machined_parts < 99 and machine_state == 5:
                    lcd = "TROUBLE    Sta:" + str(machine_station_num) + "Part Counter: " + str(machined_parts)
                elif machined_parts > 9  and machine_state == 5:
                    lcd = "TROUBLE    Sta:" + str(machine_station_num) + "Part Counter: " + str(machined_parts)

   # Write to the lcd screen

                if last_lcd != lcd:
                    last_lcd = lcd
                    ser.write("\xfe\x80")
                    ser.write(lcd)
# Iterate the state machine (used by LoopingCall)
def machine_iterate(a):
    global ser, cfg_station_number

    if BBB and PERF_MON: GPIO.output("GPIO1_28",1)
    machine_values =  a[0].iterate(a[1], __get_gpio("GPIO0_7"))
    lcd_string = lcd_string_creator(cfg_station_number, machine_values[0], machine_values[1], machine_values[2])
    if BBB and PERF_MON: GPIO.output("GPIO1_28",0)

def main():
    global ser, cfg_station_number

    # Configure signal handler for KILL (CTRL+C)
    signal.signal(signal.SIGINT, signal_handler)

    # Configure the MODBUS server datastore
    store = ModbusSlaveContext(
        di = ModbusSequentialDataBlock(1, [0]*5),
        co = ModbusSequentialDataBlock(1, [0]*5),
        hr = ModbusSequentialDataBlock(1, [0]*3),
        ir = ModbusSequentialDataBlock(1, [0]*7))
    context = ModbusServerContext(slaves=store, single=True)

    # Configure logging
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    logging.basicConfig(format='%(asctime)-15s %(levelname)s:%(message)s')

    # Variables from Configuration file
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

    # LCD splash-screen
    if BBB:
        UART.setup("UART1")
        ser = serial.Serial(port = "/dev/ttyO1", baudrate=9600)
        ser.close()
        ser.open() 
        t = 0
        if ser.isOpen():
          ser.write(b"\xfe\x01")
          ser.write("NIST Machine SimVersion " + str(SW_VERSION))
          time.sleep(2.0)
          ser.write(b"\xfe\x01")


    # Configure the I/O pin on the BBB
    # TODO: Create a device tree overlay for a different pin with a pull-up
    if BBB: GPIO.setup(cfg_sensor_GPIO,  GPIO.IN)  #
    if BBB and PERF_MON: GPIO.setup("GPIO1_28", GPIO.OUT)


    # Configuration file to obtain these parameters, and pass to object
    machine = Machine(cfg_machine_time, SW_VERSION, cfg_station_number)

    # Create the loop using the Twisted framework
    loop = LoopingCall(f=machine_iterate, a=(machine, context))
    loop.start((1.0/cfg_simulation_frequency), now=False)

    # Start the MODBUS server
    StartTcpServer(context)

if __name__ == '__main__':
    main()
