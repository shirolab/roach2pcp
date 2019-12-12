import numpy as np
import os
import matplotlib.pyplot as plt
import pyvisa as visa
import time
import logging
class FPC1000(object):
    def __init__(self, boardnum = 0, ipaddress = "192.168.1.144"):

        self.logger = logging.getLogger(__name__)
        self.rm = visa.ResourceManager('@py')


        self.resource_string = "TCPIP{bn}::{ip}::INSTR".format(bn = boardnum, ip = ipaddress)
        self.inst = self.rm.open_resource(self.resource_string)

        self.inst.timeout = 100. # timeout milliseconds
        #when requesting data from fpc, only returns 1183 vals (one for each pixel)
        self.num_data_vals = 1183

        #setting some standard parameters
        self.reset_instrument()
        self.set_sweeptime_auto("ON")
        self.set_resolution_bandwidth_auto("OFF")
        self.set_power_units_dBm()
        self.set_ref_level_dBm(-10)
        self.set_sweep_mode_single()

        self.vbw = 3000
        self.rbw = 300

    '''BASIC FUNCTIONS'''
    def idn(self):
        reply = self.inst.query("*IDN?")
        return reply
    def reset_instrument(self):
        self.inst.write("*RST")
    def clear_status_registers(self):
        self.inst.write("*CST")
    def clear_status(self):
        self.inst.write("*CLS")
    def close_connection(self):
        self.inst.close()
    def opc(self):
        reply = self.inst.query("*OPC?")
        return reply
    def set_event_status_register(self, bitval):
        self.inst.write("*ESE {b}".format(b=bitval))
    def get_event_status_register(self):
        return self.inst.query_ascii_values("*ESE?")
    def poll_complete(self):
        return self.inst.query_ascii_values("*OPC; *ESR?")[0]

    '''FREQUENCY FUNCTIONS000'''
    #setting
    def set_start_freq(self, freq):
        self.inst.write("FREQ:STAR {f}HZ".format(f=freq))
    def set_stop_freq(self, freq):
        self.inst.write("FREQ:STOP {f}HZ".format(f=freq))
    def set_center_freq(self,freq):
        self.inst.write("FREQ:CENT {f}HZ".format(f=freq))
    def set_span(self, span):
        self.inst.write("FREQ:SPAN {f}Hz".format(f=span))
    #getting
    def get_start_freq(self):
        return self.inst.query_ascii_values("FREQ:STAR?")[0]
    def get_stop_freq(self):
        return self.inst.query_ascii_values("FREQ:STOP?")[0]
    def get_center_freq(self):
        return self.inst.query_ascii_values("FREQ:CENT?")[0]
    def get_span(self):
        return self.inst.query_ascii_values("FREQ:SPAN?")[0]


    '''POWER FUNCTIONS '''
    def set_power_units_dBm(self):
        self.inst.write("UNIT:POW DBM")
    def set_ref_level_dBm(self, ref_level):
        self.inst.write("DISP:TRAC:Y:RLEV {rf}".format(rf=ref_level))

    '''SWEEP FUNCTIONS'''
    def set_resolution_bandwidth_auto(self, ON_or_OFF):
        self.inst.write("BAND:RES:AUTO {s}".format(s=ON_or_OFF))
    def set_video_bandwidth_auto(self, ON_or_OFF):
        self.inst.write("BAND:VID:AUTO {s}".format(s=ON_or_OFF))
    def set_sweeptime_auto(self, ON_or_OFF):
        self.inst.write("SWE:TIME:AUTO {s}".format(s=ON_or_OFF))
    def set_video_bandwidth(self, video_bandwidth ):
        self.inst.write("BAND:VID {bw}HZ".format(bw=video_bandwidth))
    def set_resolution_bandwidth(self, resolution_bandwidth ):
        self.inst.write("BAND:RES {bw}HZ".format(bw=resolution_bandwidth))
    def initiate_sweep(self):
        self.inst.write("INIT")
    def set_sweep_mode_single(self):
        self.inst.write("INIT:CONT OFF")
    def set_sweep_averaging(self, Naverage):
        self.inst.write("DISP:TRAC:MODE AVER")
        self.inst.write("SWE:COUN {s}".format(s=int(Naverage)))

    '''TRACE/DATA FUNCTIONS'''
    def set_detector_mode(self, detector_str):
        '''detector_str = str representing detector mode types
        POS, NEG, SAMP, RMS, AVER, APEak
        Use RMS '''
        self.inst.write("DET {s}".format(s=detector_str))


    def get_trace_data(self, delay=None):
        data = self.inst.query_ascii_values("TRAC:DATA?", container=np.array, delay = delay)
        return data

    def execute_func_and_wait_until_complete(self, func, polltime, return_func_data, *args):
        #set event status register to 1
        self.set_event_status_register(1)
        #execute command
        funcout = func(*args)
        ESR  = 0
        while ESR != 1:
            time.sleep(polltime)
            ESR = int(self.poll_complete())
            print 'ESR = ', ESR
        print 'function completed execution'
        #when self.poll_complete() returns 1, execution completed
        if return_func_data == True:
            return ESR, funcout
        else:
            return ESR

    def wide_sweep(self, start, stop, df, Navg, rbw=3000.0):
        #setting sweep state
        self.set_resolution_bandwidth_auto('OFF')
        self.set_resolution_bandwidth(rbw)

        #averaging doesn't seem to work well...makes tones disappear
        # self.set_sweep_averaging(Navg)
        #calculating params for sweep windowing
        bw = stop - start
        bw_single_window = (self.num_data_vals - 1)*df
        N_points_total = np.ceil(bw/df) + 1
        Nwindow_total = np.ceil(bw / bw_single_window)
        #initializing first window of sweep
        lfreq = start
        rfreq = lfreq + bw_single_window
        f_array = np.linspace(lfreq, rfreq, self.num_data_vals)
        full_freq = np.array([])
        sweep_data = np.array([])
        Nwindow = 0
        print lfreq, rfreq
        while lfreq < stop:
            # print 'vid bandwidth' + self.inst.query("BAND:VID?")
            # print 'res bandwidth' + self.inst.query("BAND:RES?")
            self.set_start_freq(lfreq)
            self.set_stop_freq(rfreq)
            self.execute_func_and_wait_until_complete(self.initiate_sweep, 1, )
            print 'completed sweep {aa} of {bb}'.format(aa=Nwindow+1, bb=int(Nwindow_total))
            tracedata = self.get_trace_data()
            # print len(tracedata)
            #saving data to array
            full_freq = np.append(full_freq, f_array)
            sweep_data = np.append(sweep_data, tracedata)
            #calculate window and change params for next loop
            lfreq =  rfreq + df
            rfreq = lfreq + (self.num_data_vals -1)*df
            f_array = np.linspace(lfreq, rfreq, self.num_data_vals)
            Nwindow+=1
        return full_freq, sweep_data


    def targeted_sweep(self, f0, span):
        '''f0array in Hz'''
        #setup system for measurement
        self.set_resolution_bandwidth_auto('OFF')
        self.set_resolution_bandwidth(self.rbw)
        self.set_video_bandwidth_auto('OFF')
        self.set_video_bandwidth(self.vbw)
        self.set_span(span)
        self.set_detector_mode("RMS")

        self.set_center_freq(f0)

        self.execute_func_and_wait_until_complete(self.initiate_sweep, 0.1, False)

        tracenotdone = True
        while tracenotdone:
            try:
                tracedata = self.get_trace_data()
                tracenotdone = False
            except visa.VisaIOError:
                self.logger.info("timeout error, getting trace again")
                self.clear_status()
                pass

        freqs = np.linspace(self.get_start_freq(), self.get_stop_freq(), self.num_data_vals)

        return freqs, tracedata

        # for ii in range(Nf):
        #     ff = f0array[ii]
        #     self.set_center_freq(ff)
        #     time.sleep(0.1)
        #     self.execute_func_and_wait_until_complete(self.initiate_sweep, 1, False)
        #     #resp = self.inst.query("*OPC?")
        #
        #     ESR, tracedata = self.execute_func_and_wait_until_complete(self.get_trace_data, 1, True)
        #     resp = self.inst.query("*OPC?")
        #     print resp
        #     # tracedata = self.get_trace_data()
        #     #storing trace in sweep_data
        #     sweep_data[ii,:] = tracedata
        #     #calculating the frequency axis
        #     time.sleep(0.1)
        #     startf = self.get_start_freq()
        #     time.sleep(0.1)
        #     stopf = self.get_stop_freq()
        #     time.sleep(0.1)
        #     resp = self.inst.query("*OPC?")
        #     print resp
        #     tempf = np.linspace(startf, stopf, self.num_data_vals)
        #     #storing frequency array from sweep in full_freq
        #     full_freq[ii,:] = tempf
        #     #finding max and frequency it occurred at, and store in array
        #     max_index = np.argmax(tracedata)
        #     maxtemp = tracedata[max_index]
        #     maxfreqtemp = tempf[max_index]
        #     maxes[ii] = maxtemp
        #     maxes_freq[ii] = maxfreqtemp
        #     sweepcount+=1
        # return full_freq, sweep_data, maxes, maxes_freq

if __name__ == '__main__':

    pass
