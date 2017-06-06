#!/usr/bin/env python

import sys, time, logging, traceback

class Machine:

    ID                  = 999
    MACH_TIME           = 6.0
    OP_STATES           = { "OPEN":0, "CLOSED":1 }
    MACHINE_STATES      = { "UNLOADED":0,"LOADED":1,"ACTIVE":2,"FINISHED":3 }
    VERSION             = 9999

    state               = MACHINE_STATES["UNLOADED"]
    last_state          = -1
    mach_start_time     = None
    mach_end_time       = None
    door_state          = OP_STATES["OPEN"]
    chuck_state         = OP_STATES["OPEN"]
    estop_state         = True
    heartbeat           = 0
    machine_mode        = 0
    part_count          = 0
    progress            = 0
    stock_present       = False
    machine_mode        = 0
    mbtcp_in_robotprox  = False

    # http://stackoverflow.com/questions/483666/python-reverse-invert-a-mapping
    STATE_STRING_LOOKUP = {v: k for k, v in MACHINE_STATES.iteritems()}

    # Configure logging
    log = logging.getLogger()

    def __init__(self,m_t,ver,m_id):
        self.MACH_TIME = m_t
        self.VERSION = ver
        self.log.info("Software version: " + str(self.VERSION))
        self.ID = m_id
        self.log.info("Station number: " + str(self.ID))
    ####################
    ## HELPER METHODS ##
    ####################
    def __door(self, op):
        if op == "OPEN" and self.door_state == self.OP_STATES["CLOSED"]:
            self.door_state = self.OP_STATES["OPEN"]
            self.log.info("Door is OPEN")
        elif op == "CLOSE" and self.door_state == self.OP_STATES["OPEN"]:
            self.door_state = self.OP_STATES["CLOSED"]
            self.log.info("Door is CLOSED")

    def __chuck(self, op):
        if op == "OPEN" and self.chuck_state == self.OP_STATES["CLOSED"]:
            self.chuck_state = self.OP_STATES["OPEN"]
            self.log.info("Chuck is OPEN")
        elif op == "CLOSE" and self.chuck_state == self.OP_STATES["OPEN"]:
            self.chuck_state = self.OP_STATES["CLOSED"]
            self.log.info("Chuck is CLOSED")

    ###################
    ## MBTCP METHODS ##
    ###################
    def __parse_mbtcp_in(self, context):
        # COILS
        mbtcp_co = context.getValues(1, 0x00, count=3)
        self.mbtcp_in_estop      = mbtcp_co[0]
        self.mbtcp_in_reset      = mbtcp_co[1]
        self.mbtcp_in_robotprox  = mbtcp_co[2]
        # HOLDING REGISTERS
        mbtcp_hr = context.getValues(3, 0x00, count=2)
        if mbtcp_hr[0] < 1000: self.mbtcp_in_machiningtime = self.MACH_TIME
        else: self.mbtcp_in_machiningtime = mbtcp_hr[0]
        self.mbtcp_in_mode = mbtcp_hr[1]

    def __push_mbtcp_out(self, context):
        mbtcp_di = [self.estop_state,self.door_state,self.chuck_state,self.stock_present]
        mbtcp_ir = [self.state,self.machine_mode,self.progress,self.part_count,self.heartbeat,self.ID,self.VERSION]
        context.setValues(2, 0x00, mbtcp_di)
        context.setValues(4, 0x00, mbtcp_ir)

    ###########################
    ## MACHINE STATE METHODS ##
    ###########################
    def __state_unloaded(self):
        self.__door("OPEN")
        self.__chuck("OPEN")
        # If stock gets placed in the machine, we switch to the LOADED state
        if self.stock_present == True:
            self.state = self.MACHINE_STATES["LOADED"]
        return

    def __state_loaded(self):
        # Close the chuck
        self.__chuck("CLOSE")
        if self.mbtcp_in_robotprox == False and self.stock_present == True:
            self.state = self.MACHINE_STATES["ACTIVE"]
        elif self.stock_present == False:
            self.state = self.MACHINE_STATES["UNLOADED"]
        return

    def __state_active(self):
        # Close the door
        self.__door("CLOSE")
        if self.stock_present == False:
            self.log.error("Stock removed from chuck!")
            self.progress = 0
            self.state = self.MACHINE_STATES["FINISHED"]
        t = time.time()
        if self.mach_end_time == None:
            self.mach_start_time = t
            self.mach_end_time = t + self.MACH_TIME
        elif t >= self.mach_end_time:
            self.progress = 100
            self.mach_end_time = None
            self.state = self.MACHINE_STATES["FINISHED"]
            self.part_count = self.part_count + 1
        else:
            self.progress = int(100*((t - self.mach_start_time) / self.MACH_TIME))
            self.log.info("Progress: " + str(self.progress) + "%")
        return

    def __state_finished(self):
        self.__chuck("OPEN")
        self.__door("OPEN")
        # Wait for robot to retrieve part
        if self.stock_present == False:
            self.progress = 0
            self.state = self.MACHINE_STATES["UNLOADED"]
        return

        ###############
        ## HEARTBEAT ##
        ###############
    def __heartbeat(self):
        self.heartbeat = self.heartbeat + 1
        if self.heartbeat >= 64:
            self.heartbeat = 0
        return

    ###################
    ## SIM ITERATION ##
    ###################
    def iterate(self,a,stock):
        try:
            self.machine_mode = 1
            self.__parse_mbtcp_in(a[0])
            self.stock_present = stock
            # Report any state changes from the last iteration
            if self.state != self.last_state:
                self.log.info("Machine is [" + self.STATE_STRING_LOOKUP[self.state] + "]")
                self.prev_state = self.last_state
                self.last_state = self.state
            # State Machine
            if   self.state == self.MACHINE_STATES["UNLOADED"]:  self.__state_unloaded()
            elif self.state == self.MACHINE_STATES["LOADED"]:    self.__state_loaded()
            elif self.state == self.MACHINE_STATES["ACTIVE"]:    self.__state_active()
            elif self.state == self.MACHINE_STATES["FINISHED"]:  self.__state_finished()
            else:
                print "ERROR: Invalid State"
                exit()
            self.__heartbeat()
            self.__push_mbtcp_out(a[0])
        except:
            print "Unexpected error: " + str(traceback.print_exc())
            raise

def main():
    m = Machine(6.0)

if __name__ == '__main__':
    main()
