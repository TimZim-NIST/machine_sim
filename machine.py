#!/usr/bin/env python

import sys, time, logging, traceback, os, signal

class Machine:

    ID                  = 999
    MACH_TIME           = 6.0
    OP_STATES           = { "OPEN":0, "CLOSED":1 }
    MACHINE_STATES      = { "UNLOADED":0,"LOADED":1,"ACTIVE":2,"FINISHED":3, "STOPPED":4, "TROUBLE":5 }
    PART_RESET_STATES   = { "OFF":0, "ON":1 }
    VERSION             = 9999

    state               = MACHINE_STATES["UNLOADED"]
    last_state          = -1
    mach_start_time     = None
    mach_end_time       = None
    door_state          = OP_STATES["OPEN"]
    chuck_state         = OP_STATES["OPEN"]
    reset_partctr       = PART_RESET_STATES["OFF"]
    estop_state         = True
    heartbeat           = 0
    machine_mode        = 0
    part_count          = 0
    progress            = 0
    stock_present       = False
    mbtcp_in_robotprox  = False
    repair_time         = 10.0
    repair_end_time     = None
    trouble_counter     = 0
    inspect_pass        = False
    inspect_fail        = False
    passed_parts        = 0
    failed_parts        = 0

    mbtcp_anomaly_invalidstate = None
    mbtcp_anomaly_troublecall  = None
    mbtcp_anomaly_shutdown     = None 
    mbtcp_anomaly_doorsensor   = None

    statelogger = None

    # http://stackoverflow.com/questions/483666/python-reverse-invert-a-mapping
    STATE_STRING_LOOKUP = {v: k for k, v in MACHINE_STATES.iteritems()}

    # Configure logging
    log = logging.getLogger()

    def __init__(self,m_t,ver,m_id,cfg_statelogger):
        self.MACH_TIME = m_t
        self.VERSION = ver
        self.log.info("Software version: " + str(self.VERSION))
        self.ID = m_id
        self.log.info("Station number: " + str(self.ID))
        self.enable_statelogger = cfg_statelogger

    ####################
    ## HELPER METHODS ##
    ####################
    def __door(self, op):
        if not self.mbtcp_anomaly_doorsensor:
            if op == "OPEN" and self.door_state == self.OP_STATES["CLOSED"]:
                self.door_state = self.OP_STATES["OPEN"]
                self.log.info("Door is OPEN")
            elif op == "CLOSED" and self.door_state == self.OP_STATES["OPEN"]:
                self.door_state = self.OP_STATES["CLOSED"]
                self.log.info("Door is CLOSED")

    def __chuck(self, op):
        if op == "OPEN" and self.chuck_state == self.OP_STATES["CLOSED"]:
            self.chuck_state = self.OP_STATES["OPEN"]
            self.log.info("Chuck is OPEN")
        elif op == "CLOSED" and self.chuck_state == self.OP_STATES["OPEN"]:
            self.chuck_state = self.OP_STATES["CLOSED"]
            self.log.info("Chuck is CLOSED")

    def __get_machinestate(self):
        if self.mbtcp_anomaly_invalidstate: 
            return 35210 
        else: 
             return self.state

    def __inspection(self):
        # Don't continue if we've already inspected the part
        if not(self.inspect_pass or self.inspect_fail):
            # Accept all parts for now, except when inspection failure anomaly is enabled
            if self.mbtcp_anomaly_inspectfail:
                self.failed_parts = self.failed_parts + 1
                self.inspect_fail = True
                return True
            else:
                self.passed_parts = self.passed_parts + 1
                self.inspect_pass = True
                return False



    ###################
    ## MBTCP METHODS ##
    ###################
    def __parse_mbtcp_in(self, context):
        # COILS
        mbtcp_co = context.getValues(1, 0x00, count=9)
        self.mbtcp_in_estop             = mbtcp_co[0]
        self.mbtcp_in_reset_part        = mbtcp_co[1]
        self.mbtcp_in_robotprox         = mbtcp_co[2]
        self.mbtcp_in_force_shutdown    = mbtcp_co[3]
        self.mbtcp_anomaly_invalidstate = mbtcp_co[4]
        self.mbtcp_anomaly_troublecall  = mbtcp_co[5]
        self.mbtcp_anomaly_shutdown     = mbtcp_co[6]
        self.mbtcp_anomaly_inspectfail  = mbtcp_co[7]
        self.mbtcp_anomaly_doorsensor   = mbtcp_co[8]
        # HOLDING REGISTERS
        mbtcp_hr = context.getValues(3, 0x00, count=2)
        self.mbtcp_in_mode = mbtcp_hr[1]
        if mbtcp_hr[0] < 100:
            mbtcp_out_machtime = self.MACH_TIME * 1000
            context.setValues(3, 0x00, [mbtcp_out_machtime])
        else: 
            self.MACH_TIME = mbtcp_hr[0] / 1000.0

    def __push_mbtcp_out(self, context):
        mbtcp_di = [self.estop_state,self.door_state,self.chuck_state,self.stock_present,self.inspect_pass,self.inspect_fail]
        mbtcp_ir = [self.__get_machinestate(),self.machine_mode,self.progress,self.part_count,self.heartbeat,self.ID,self.VERSION,self.passed_parts,self.failed_parts]
        mbtcp_co = [self.mbtcp_in_reset_part]
        context.setValues(2, 0x00, mbtcp_di)
        context.setValues(4, 0x00, mbtcp_ir)
        context.setValues(1, 0x01, mbtcp_co)
        
    ##################################
    ## MACHINE STATE LOGGER METHODS ##
    ##################################

    def __start_statelogger(self):
        if self.enable_statelogger == False: return
        try:
            fname = "/dev/shm/" + time.strftime("%m-%d-%Y") + "_" + time.strftime("%H-%M") + "_Sta" + str(self.ID) + "_States.dat"
            self.statelogger = open(fname,'w')
            self.statelogger.write("time,state,part\n")
        except:
            pass

    def __stop_statelogger(self):
        if self.enable_statelogger == False: return
        if not (self.statelogger == None):
            self.statelogger.close()
        self.statelogger = None

    def __log_statechange(self,s):
        if self.enable_statelogger == False: return
        if self.statelogger == None: return
        try:
            ts = format(time.time(),'0.3f')
            self.statelogger.write(ts + "," + s + "," + str(self.part_count) + "\n")
        except:
            pass

    ###########################
    ## MACHINE STATE METHODS ##
    ###########################

    def __state_unloaded(self):
        self.__door("OPEN")
        self.__chuck("OPEN")
        # If stock gets placed in the machine, we switch to the LOADED state
        if self.stock_present == True:
            self.state = self.MACHINE_STATES["LOADED"]
        # If the stop switch is toggled we go to the STOPPED state
        if self.mbtcp_in_mode == 0 or self.mbtcp_anomaly_shutdown:
            self.state = self.MACHINE_STATES["STOPPED"]
        return

    def __state_loaded(self):
        # Close the chuck
        self.__chuck("CLOSED")
        if self.mbtcp_in_robotprox == False and self.stock_present == True:
            if self.mbtcp_anomaly_troublecall:
                self.state = self.MACHINE_STATES["TROUBLE"]
            else:
                self.state = self.MACHINE_STATES["ACTIVE"]
        elif self.stock_present == False:
            self.state = self.MACHINE_STATES["UNLOADED"]
        return

    def __state_active(self):
        # Close the door
        self.__door("CLOSED")
        t = time.time()
        if self.mach_end_time == None:
            self.mach_start_time = t
            self.mach_end_time = t + self.MACH_TIME
        if self.stock_present == False and t < self.mach_end_time:
            self.log.error("Stock removed from chuck!")
            self.progress = 0
            self.mach_end_time = None
            self.state = self.MACHINE_STATES["FINISHED"]
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
        if self.ID == 4 and self.progress == 100: 
            self.__inspection()
        # Wait for robot to retrieve part
        if self.stock_present == False:
            self.progress = 0
            if self.ID == 4: 
                self.inspect_pass = False
                self.inspect_fail = False
            self.state = self.MACHINE_STATES["UNLOADED"]
        return

    def __state_stopped(self):
        self.log.debug("STOPPED")
        self.__stop_statelogger()
        if self.mbtcp_in_mode == 1 and not self.mbtcp_anomaly_shutdown:
            self.__start_statelogger()
            if self.stock_present == True:
                self.state = self.MACHINE_STATES["LOADED"]
            else:
                self.state = self.MACHINE_STATES["UNLOADED"]
        self.machine_mode = self.mbtcp_in_mode
        return

    def __state_trouble(self):
        self.__door("OPEN")
        t = time.time()
        self.log.info("TROUBLE CALL")
        if self.repair_end_time == None:
            self.repair_end_time = t + self.repair_time
        elif t >= self.repair_end_time:
            self.repair_end_time = None
            self.__door("CLOSED")
            self.log.info("TROUBLE CLEARED")
            self.state = self.MACHINE_STATES["ACTIVE"]
            self.trouble_counter = 1 + self.trouble_counter
        return

    def __part_reset(self):
        if self.mbtcp_in_reset_part == True:
            self.part_count   = 0
            self.passed_parts = 0
            self.failed_parts = 0
            self.mbtcp_in_reset_part = False
        return

    def __force_shutdown(self):
        if self.mbtcp_in_force_shutdown == True:
            self.mbtcp_in_force_shutdown = False
            os.system("/home/machine/Projects/machine_sim/machine_check.sh &")
            os.kill(os.getpid(), signal.SIGKILL)

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
            #self.machine_mode = 1
            self.__parse_mbtcp_in(a[0])
            self.stock_present = stock
            # Report any state changes from the last iteration
            if self.state != self.last_state:
                self.log.info("Machine is [" + self.STATE_STRING_LOOKUP[self.state] + "]")
                self.__log_statechange(self.STATE_STRING_LOOKUP[self.state])
                self.prev_state = self.last_state
                self.last_state = self.state
            # State Machine
            if   self.state == self.MACHINE_STATES["UNLOADED"]:
                self.__state_unloaded()
            elif self.state == self.MACHINE_STATES["LOADED"]:
                self.__state_loaded()
            elif self.state == self.MACHINE_STATES["ACTIVE"]:
                self.__state_active()
            elif self.state == self.MACHINE_STATES["FINISHED"]:
                self.__state_finished()
            elif self.state == self.MACHINE_STATES["STOPPED"]:
                self.__state_stopped()
            elif self.state == self.MACHINE_STATES["TROUBLE"]:
                self.__state_trouble()
            else:
                print "ERROR: Invalid State"
                exit()
            self.__part_reset()
            self.__heartbeat()
            self.__force_shutdown()
            self.__push_mbtcp_out(a[0])
            return [self.state, self.progress, self.part_count, self.mbtcp_in_robotprox]
        except:
            print "Unexpected error: " + str(traceback.print_exc())
            raise

def main():
    m = Machine(6.0)

if __name__ == '__main__':
    main()
