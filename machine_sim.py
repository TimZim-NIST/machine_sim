#!/usr/bin/env python
#
# Author: Timothy Zimmerman (timothy.zimmerman@nist.gov)
# Modified by: Christian Burns (christian.burns@nist.gov)
# Organization: National Institute of Standards and Technology
# U.S. Department of Commerce
# License: Public Domain
#
# See README for description and information

# Check if we are running on a BBB.
# Allows us to run the sim on a host without BBB packages.
# Pulls the MAC address from the host, and compares the first three
# octets with the expected 'b0d5cc'.
from uuid import getnode
BBB = (hex(getnode())[2:8] == 'b0d5cc')

if BBB:
    import Adafruit_BBIO.GPIO as GPIO
    import Adafruit_BBIO.UART as UART

from pymodbus.server.async     import StartTcpServer
from pymodbus.device           import ModbusDeviceIdentification
from pymodbus.datastore        import ModbusSequentialDataBlock
from pymodbus.datastore        import ModbusSlaveContext, ModbusServerContext
from twisted.internet          import reactor
from twisted.internet.task     import LoopingCall
from machine                   import Machine
from machine_webpage_generator import Generator

import time, signal, sys, logging, ConfigParser, serial

# Set this to True to see task performance on BBB pin GPIO1_28 (P9 PIN 12)
PERF_MON = False

# Machine_sim version increment upon major changes
SW_VERSION = 11
ser = None
cfg_station_number = None
last_lcd = ""
stopped_state_counter = 0
timer_limit = 3000 # 3000 = 5 minutes



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

def lcd_string_creator(machine_station_num, machine_state, machine_progress, machined_parts, prox):
    global last_lcd, stopped_state_counter
    if BBB:
        if ser.isOpen():

            if prox == True:
                p = "*"
            else:
                p = " "

            # UNLOADED
            if machine_state == 0:
                if machined_parts < 10:
                    lcd = "UNLOADED"+p+"  Sta:" + str(machine_station_num) + "Part Counter:  " + str(machined_parts)
                elif machined_parts > 99:
                    lcd = "UNLOADED"+p+"  Sta:" + str(machine_station_num) + "Part Counter:"  + str(machined_parts)
                elif machined_parts > 9:
                    lcd = "UNLOADED"+p+"  Sta:" + str(machine_station_num) + "Part Counter: "   + str(machined_parts)

            # LOADED
            elif machine_state == 1:
                if machined_parts < 10:
                    lcd = "LOADED"+ p +"    Sta:" + str(machine_station_num) + "Part Counter:  " + str(machined_parts)
                elif machined_parts > 99:
                    lcd = "LOADED"+ p +"    Sta:" + str(machine_station_num) + "Part Counter:"  + str(machined_parts)
                elif machined_parts > 9:
                    lcd = "LOADED"+ p +"    Sta:" + str(machine_station_num) + "Part Counter: "   + str(machined_parts)
            
            # ACTIVE
            elif machine_state == 2:
                total_bars = ""
                bars = int(machine_progress/10)
                total_spaces = ""
                spaces = abs(bars - 13)
                if machine_progress > 0:
                    for i in range(bars):
                        total_bars =  total_bars + b"\xff"
                    for j in range (spaces):
                        total_spaces = total_spaces + " "
                msg = "ACTIVE"+p+"   "
                if cfg_station_number == 4:
                    msg = "MEASURING"+p
                if machine_progress < 10:
                    total_spaces = "              "
                    lcd = msg + " Sta:" + str(machine_station_num) + total_bars + total_spaces + str(machine_progress) + "%"
                elif machine_progress >= 10 and machine_progress < 100:
                    lcd = msg + " Sta:" + str(machine_station_num) + total_bars + total_spaces + str(machine_progress) + "%"

            # FINISHED
            elif machine_state == 3:
                if machined_parts < 10:
                    lcd = "FINISHED"+p+"  Sta:" + str(machine_station_num) + "Part Counter:  " + str(machined_parts)
                elif machined_parts > 99:
                    lcd = "FINISHED"+p+"  Sta:" + str(machine_station_num) + "Part Counter:"   + str(machined_parts)
                elif machined_parts > 9:
                    lcd = "FINISHED"+p+"  Sta:" + str(machine_station_num) + "Part Counter: "  + str(machined_parts)

            # STOPPED
            elif machine_state == 4:
                if stopped_state_counter <= timer_limit: stopped_state_counter += 1
                if machined_parts < 10:
                    lcd = "STOPPED    Sta:" + str(machine_station_num) + "Part Counter:  " + str(machined_parts)
                elif machined_parts > 99:
                    lcd = "STOPPED    Sta:" + str(machine_station_num) + "Part Counter:" + str(machined_parts)
                elif machined_parts > 9:
                    lcd = "STOPPED    Sta:" + str(machine_station_num) + "Part Counter: " + str(machined_parts)

            # TROUBLE
            elif machine_state == 5:
                if machined_parts < 10:
                    lcd = "TROUBLE"+p+"   Sta:" + str(machine_station_num) + "Part Counter:  " + str(machined_parts)
                elif machined_parts > 99:
                    lcd = "TROUBLE"+p+"   Sta:" + str(machine_station_num) + "Part Counter:" + str(machined_parts)
                elif machined_parts > 9:
                    lcd = "TROUBLE"+p+"   Sta:" + str(machine_station_num) + "Part Counter: " + str(machined_parts)

            # Write to the lcd screen
            if last_lcd != lcd:
                if stopped_state_counter > 0: ser.write(b"\x7c\x9d")
                time.sleep(0.025)
                stopped_state_counter = 0
                last_lcd = lcd
                ser.write("\xfe\x80")
                ser.write(lcd)
            # Or we have a timeout, so turn off the LCD
            elif stopped_state_counter >= timer_limit:
                ser.write(b"\x7c\x80")
                time.sleep(0.025)
                    
# Iterate the state machine (used by LoopingCall)
def machine_iterate(a):
    global ser, cfg_station_number
    if BBB and PERF_MON: GPIO.output("GPIO1_28",1)
    machine_values =  a[0].iterate(a[1], __get_gpio("GPIO0_7"))
    lcd_string = lcd_string_creator(cfg_station_number, machine_values[0], machine_values[1], machine_values[2], machine_values[3])
    if BBB and PERF_MON: GPIO.output("GPIO1_28",0)

def www_update(a):
    a[0].update()

def main():
    global ser, cfg_station_number

    # Configure signal handler for KILL (CTRL+C)
    signal.signal(signal.SIGINT, signal_handler)

    # Configure the MODBUS server datastore
    store = ModbusSlaveContext(
        di = ModbusSequentialDataBlock(1, [0]*7),
        co = ModbusSequentialDataBlock(1, [0]*10),
        hr = ModbusSequentialDataBlock(1, [0]*3),
        ir = ModbusSequentialDataBlock(1, [0]*9))
    context = ModbusServerContext(slaves=store, single=True)

    # Configure logging
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    logging.basicConfig(format='%(created)f %(levelname)s:%(message)s')

    # Variables from Configuration file
    try:
        config = ConfigParser.RawConfigParser()
        config.read("./station.cfg")
        cfg_station_number = config.getint("Station","station_number")
        cfg_machine_time = config.getfloat("Station","machine_time")
        cfg_sensor_GPIO = config.get("Station","sensor_GPIO")
        cfg_simulation_frequency = config.getint("Station","simulation_frequency")
        cfg_generate_webpages = config.getboolean("Station","enable_webpages")
        cfg_generate_statelogger = config.getboolean("Station","enable_statelogger")
    except:
        log.error("Error while parsing configuration file.")
        exit()

    log.info("Station number: " + str(cfg_station_number))
    log.info("Machine time: " + str(cfg_machine_time))
    log.info("Sensor GPIO: " + cfg_sensor_GPIO)
    log.info("Simulation frequency: " + str(cfg_simulation_frequency))
    if cfg_generate_statelogger == True: log.info("State logger enabled!")

    # LCD splash-screen
    if BBB:
        UART.setup("UART1")
        ser = serial.Serial(port = "/dev/ttyO1", baudrate=9600)
        ser.close()
        ser.open() 
        t = 0
        if ser.isOpen():
            ser.write(b"\x7c\x9D")
            time.sleep(0.025)
            ser.write(b"\xfe\x01")
            ser.write("NIST Machine SimVersion " + str(SW_VERSION))
            time.sleep(2.0)
            ser.write(b"\xfe\x01")


    # Configure the I/O pin on the BBB
    # TODO: Create a device tree overlay for a different pin with a pull-up
    if BBB: GPIO.setup(cfg_sensor_GPIO,  GPIO.IN)  #
    if BBB and PERF_MON: GPIO.setup("GPIO1_28", GPIO.OUT)


    # Configuration file to obtain these parameters, and pass to object
    machine = Machine(cfg_machine_time, SW_VERSION, cfg_station_number, cfg_generate_statelogger)

    # Create the webpage generator
    if cfg_generate_webpages:
        webpage = Generator(cfg_station_number, context)

    # Create the machine loop using the Twisted framework
    machine_loop = LoopingCall(f=machine_iterate, a=(machine, context))
    machine_loop.start((1.0/cfg_simulation_frequency), now=False)

    # Create the webpage update loop
    if cfg_generate_webpages:
        www_loop = LoopingCall(f=www_update, a=(webpage, context))
        www_loop.start(1.0, now=False)

    # Start the MODBUS server
    StartTcpServer(context)

if __name__ == '__main__':
    main()
