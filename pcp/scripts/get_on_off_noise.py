#!/usr/bin/env python

# take ON/OFF time streams during a t time and n samples.
#   d_off :   Distance between off and on resonance
#   direction: off tone up or down the f0
#   auto_off: estimate the off resonance position
# run as
# >> import pcp
# >> pcp.script.get_on_off_noise(time_stream, samples, d_off)

# We could write a small helper script to check things are connected would be useful for initial configuration testing
#   - check dnsmasq is running
#   - check roach(s) are connected


import logging as _logging
from .. import color_logs as CL
_logger = _logging.getLogger(__name__)

from .. import ROACH_LIST, mux_channel
import numpy as _np
import time as _time
import psd_plot_functions as _psd_funcs


def _shift_lo(mux_channel_list, shift):
    for mux_channel in mux_channel_list:
	lo_freq = mux_channel.synth_lo.frequency
        _time.sleep(1)
        mux_channel.synth_lo.frequency = lo_freq + shift

        print "%s%s LO frequency: %s Hz%s"%(CL.OKGREEN, mux_channel.roachid, str(mux_channel.synth_lo.frequency), CL.ENDC)


def main(mux_channel_list, time_stream=10, samples=2, d_off=-100e3, avg_samples=True, auto_off=False):
    print "%sGet ON / OFF resonance frequency time streams%s"%(CL.OKBLUE, CL.ENDC)
    _logger.info( "Get ON / OFF resonance frequency time streams" )

    mux_sweep = {}

    mux_on_stream = {}
    mux_off_stream = {}

    on_stream_dirfiles = []
    off_stream_dirfiles = []

    # get sweep dirfiles for each channel
    for mux_channel in mux_channel_list:
        mux_sweep[mux_channel.roachid] = mux_channel.sweep.dirfile.name

        mux_on_stream[mux_channel.roachid] = []
        mux_off_stream[mux_channel.roachid] = []

    for sample in range(samples):

        print " [ %s%s%s ] Sample "%(CL.OKGREEN, str(sample + 1), CL.ENDC)

        # ON resonance
        print "%s * * * * *  O N   R E S O N A N C E * * * * * %s"%(CL.OKGREEN, CL.ENDC)
        for mux_channel in mux_channel_list:
            print "%sStarting streaming for %s: %s s%s"%(CL.OKBLUE, mux_channel.roachid, str(time_stream), CL.ENDC)
            _logger.info( "%sStarting streaming for %s: %s s%s"%(CL.OKBLUE, mux_channel.roachid, str(time_stream), CL.ENDC) )
            mux_channel.start_stream()

        t0 = _time.time()
        while True:
            if ( _time.time() - t0 ) > time_stream:
                break

        for mux_channel in mux_channel_list:
            print "%sStopping streaming for %s %s"%(CL.OKBLUE, mux_channel.roachid, CL.ENDC)
            _logger.info( "%sStopping streaming for %s %s"%(CL.OKBLUE, mux_channel.roachid, CL.ENDC) )
            mux_channel.stop_stream()
            mux_on_stream[mux_channel.roachid].append(mux_channel.current_dirfile.name)

        _time.sleep(2)

        # OFF resonance
        print "%s * * * * *  O F F   R E S O N A N C E * * * * * %s"%(CL.OKGREEN, CL.ENDC)

        # shift lo frequency
        _shift_lo(mux_channel_list, d_off)

        for mux_channel in mux_channel_list:
            print "%sStarting streaming for %s: %s s%s"%(CL.OKBLUE, mux_channel.roachid, str(time_stream), CL.ENDC)
            _logger.info( "%sStarting streaming for %s: %s s%s"%(CL.OKBLUE, mux_channel.roachid, str(time_stream), CL.ENDC) )
            mux_channel.start_stream()

        t0 = _time.time()
        while True:
            if ( _time.time() - t0 ) > time_stream:
                break

        for mux_channel in mux_channel_list:
            print "%sStopping streaming for %s %s"%(CL.OKBLUE, mux_channel.roachid, CL.ENDC)
            _logger.info( "%sStopping streaming for %s %s"%(CL.OKBLUE, mux_channel.roachid, CL.ENDC) )
            mux_channel.stop_stream()
            mux_off_stream[mux_channel.roachid].append(mux_channel.current_dirfile.name)

        _time.sleep(2)

        # return to resonance frequency
        _shift_lo(mux_channel_list, -d_off)

    # to average all the samples
    if avg_samples:
        KIDs_on = {}
        KIDs_off = {}

        print "%sAveraging all the samples...%s"%(CL.OKBLUE, CL.ENDC)

        for chan in mux_channel_list:
            print "%sChannel: %s%s"%(CL.OKBLUE, str(chan), CL.ENDC)
            KIDs_on[chan] = _psd_funcs.on_off_res([], mux_sweep[chan], mux_on_stream[chan], all_kids=True)
            KIDs_off[chan] = _psd_funcs.on_off_res([], mux_sweep[chan], mux_off_stream[chan], all_kids=True)

        print "%sDone%s"%(CL.OKGREEN, CL.ENDC)

	return KIDs_on, KIDs_off
    else:
        return mux_sweep, mux_on_stream, mux_off_stream

    #return mux_sweep, mux_on_stream, mux_off_stream
    #return KIDs_on, KIDs_off
