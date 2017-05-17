# Machine Simulator

This script simulates MODBUS TCP server operations implemented by machine tools a typical manufacturing environment. The script was writtento be deployed on a Beaglebone Black. The machine operations are simulated with a simple state machine. MODBUS TCP registers are updated at the rate defined in SIMULATION_FREQ_HZ. The script does not operate in real-time, nor does the script attempt to compensate for any delays, so jitter will likely be present.

Modified from https://pymodbus.readthedocs.io/en/latest/examples/updating-server.html

Author: Timothy Zimmerman (timothy.zimmerman@nist.gov)
Organization: National Institute of Standards and Technology
U.S. Department of Commerce
License: Public Domain

### Dependencies

### MBTCP BITS AND REGISTERS
 Coils (RW):             [0] ESTOP_IN - Machine will go into ESTOP if TRUE
                         [1] RESET - Resets counters
                         [2] ROBOT_PROXIMITY - Informs if the robot is in proximity

 Holding Registers (RW): [0] MACHINING_TIME - Amount of time machining process takes
                         [1] MODE - Stop/Run

 Discrete Inputs (RO):   [0] ESTOP_OUT - Status of the ESTOP
                         [1] DOOR_STATE - Status of the door (True=CLOSED)
                         [2] CHUCK_STATE - Status of the chuck (True=CLOSED)
                         [3] STOCK_PRESENT - Stock is in the chuck

 Input Registers (RO):   [0] STATE - Numerical state of the state machine
                         [1] MODE - Run/Stop/Estop
                         [2] PROGRESS - 0-100% integer of machining progress
                         [3] PART_COUNT - Number of completed parts
                         [4] HEARTBEAT_COUNTER - Monitor to verify sim is running
                         [5] MACHINE_ID - ID value for the machine (station number)

### Setup the BBB
