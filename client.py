#!/usr/bin/env python
'''
Pymodbus Synchronous Client Examples
--------------------------------------------------------------------------

The following is an example of how to use the synchronous modbus client
implementation from pymodbus.

It should be noted that the client can also be used with
the guard construct that is available in python 2.5 and up::

    with ModbusClient('127.0.0.1') as client:
        result = client.read_coils(1,10)
        print result
'''
#---------------------------------------------------------------------------#
# import the various server implementations
#---------------------------------------------------------------------------#
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
#from pymodbus.client.sync import ModbusUdpClient as ModbusClient
#from pymodbus.client.sync import ModbusSerialClient as ModbusClient

#---------------------------------------------------------------------------#
# configure the client logging
#---------------------------------------------------------------------------#
import logging, time
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.ERROR)

client = ModbusClient('localhost', port=502)
#client = ModbusClient(method='ascii', port='/dev/pts/2', timeout=1)
#client = ModbusClient(method='rtu', port='/dev/pts/2', timeout=1)
client.connect()

# read_coils,read_discrete_inputs,read_holding_registers,read_input_registers
co = client.read_coils(0,4).bits
di = client.read_discrete_inputs(0,5).bits
hr = client.read_holding_registers(0,3).registers
ir = client.read_input_registers(0,7).registers

# MBTCP BITS AND REGISTERS
# Discrete Inputs:  ESTOP_IN
#                   RESET
#                   ROBOT_PROXIMITY
# Input Registers   MACHINING_TIME
#                   MODE
# CO OUT:           ESTOP_OUT
#                   DOOR_STATE
#                   CHUCK_STATE
#                   STOCK_PRESENT
# HR OUT:           STATE
#                   MODE
#                   PROGRESS
#                   PART_COUNT
#                   HEARTBEAT_COUNTER

print "COILS:"
print "  ESTOP IN:\t\t" + str(co[0])
print "  RESET:\t\t" + str(co[1])
print "  ROBOT PROXIMITY:\t" + str(co[2])
print "  EXIT:\t" +str(co[3])
print ""
print "HOLDING REGISTERS:"
print "  MACHINING TIME:\t" + str(hr[0])
print "  MODE:\t\t\t" + str(hr[1])
print ""
print "DISCRETE INPUTS:"
print "  ESTOP OUT:\t\t" + str(di[0])
print "  DOOR CLOSED:\t\t" + str(di[1])
print "  CHUCK CLOSED:\t\t" + str(di[2])
print "  STOCK PRESENT:\t" + str(di[3])
print ""
print "INPUT REGISTERS:"
print "  STATE:\t\t" + str(ir[0])
print "  MODE:\t\t\t" + str(ir[1])
print "  PROGRESS:\t\t" + str(ir[2])
print "  PART COUNT:\t\t" + str(ir[3])
print "  HEATBEAT COUNTER:\t" + str(ir[4])
print "  MACHINE_ID:\t\t" + str(ir[5])
print "  SW_VERSION:\t\t" + str(ir[6])
print ""
#---------------------------------------------------------------------------#
# close the client
#---------------------------------------------------------------------------#
client.close()
