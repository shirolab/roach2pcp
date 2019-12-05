#!/usr/bin/env python

import logging as _logging
_logger = _logging.getLogger(__name__)

import time
import numpy as np
import matplotlib.pyplot as plt

from .. import color_logs as CL

def main(roach, nsamples, t, points=10, step=1e3):

    span = step*points
    center_freq = roach.toneslist.lo_freq

    start = center_freq - span/2
    stop = center_freq + span/2

    lo_sweeps = np.linspace(start, stop, points)

    cmap = plt.get_cmap('gnuplot')
    colors = [cmap(i) for i in np.linspace(0, 1, points)]

    print colors

    c = 0
    for lo in lo_sweeps:

        tones = lo + roach.toneslist.bb_freqs
        for tone in tones:
            plt.axvline(tone, color=colors[c])

        roach.synth_lo.frequency = lo

        for i in range(nsamples):
            print "%sLO frequency: %s"%(CL.OKBLUE, str(lo))

            print "Starting streaming for: " + str(t)
            roach.start_stream()
            time.sleep(t)
            roach.stop_stream()
            print "Stoping streaming"

        c += 1
