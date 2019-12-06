import numpy as np
import os
import matplotlib.pyplot as plt
import pyvisa as visa
import time

class dummy_specan(object):
    def __init__(self):
        self.npoints  = int(1001)
        self._cenfreq = 100.e6
        self._span    = 1.e6

    def idn(self):
        return "dummy_spectrum_analyzer"

    def set_center_freq(self, freq):
        print "center frequency set to {0}".format(freq)
        self._cenfreq = freq
    def set_span(self, span):
        print "frequency span set to {0}".format(span)
        self._span = span

    def initiate_sweep(self):
        print "started sweep"

    def get_trace_data(self):
        return np.random.rand( self.npoints )

    def get_start_freq(self):
        return int(self._cenfreq - self._span/2.)
    def get_stop_freq(self):
        return int(self._cenfreq + self._span/2.)

    def execute_func_and_wait_until_complete(self, command, *args):
        """dummy function to immitate wait for OPC - just repeats the command"""
        command(*args)
        time.sleep(0.2)
        print "command completed - {0}".format(command.im_func.func_name)
        return

    def targeted_sweep(self, cenfreq, span):
        ''' units in Hz'''

        self.set_center_freq(cenfreq)
        self.execute_func_and_wait_until_complete(self.initiate_sweep)
        tracedata = self.get_trace_data()

        startf = self.get_start_freq()
        stopf  = self.get_stop_freq()
        freq   = np.linspace(startf, stopf, self.npoints)

        return freq, tracedata
