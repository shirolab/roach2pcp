#!/usr/bin/env python

# script to measure the amplitude correction.
# This script is intended only to be run once, for a given tonelist.

# A targeted spectrum sweep with a spectrum analyzer (that has to have a method targeted_sweep() ).
# Uses the curent uploaded toneslist/LO settings to do windowed sweep
# centered on each tone with a variable span, resolution bandwidth, and
# video bandwidth.
#
import numpy as _np, logging as _logging, time as _time
_logger = _logging.getLogger(__name__)

from .. import ROACH_LIST, mux_channel

# check that hardware is initialised
# fpga uploaded and running
# packets streaming
# LO and attenuators set

# initalise spectrum analyser (with rbw, vbw)
#
def _initialise_spec_analyser( specan ):
    # check that instrument is working - as for IDN?
    methods = [m for m in dir(specan) if not m.startswith("__") and callable(getattr(specan, m))]

    # search for 'idn' in methods
    idnsearch = [m for m in methods if 'idn' in m.lower()]

    try:
        getattr(specan, idnsearch[0])
    except IndexError:
        print "no idn method found in object"
        return 0
    except:
        print "error when trying to run the idn function {0}".format(idnsearch)
        return 0

    # check has method targeted_sweep()
    assert hasattr(specan, 'targeted_sweep'), " it appears that object {0} doesn't have a method targeted_sweep "
    return 1

def main(f0_array, specan, span = 100e3, save=True):
    _logger.info( "This is the function that is run" )

    # confirm that spectrum analyser is operational and works as expected
    assert _initialise_spec_analyser(specan)

    #calculate the frequencies to be targeted

    #Initialize settings for targeted sweep
    specan.setup_for_targeted_sweep(specan.rbw, specan.vbw)

    # sweep over the tones
    freqarr, dataarr = [],[]
    try:
        for tone in f0_array:
            freqs, data = specan.targeted_sweep(tone, span)
            freqarr.append(freqs); dataarr.append(data)

    except KeyboardInterrupt:
        print "interuppted - nothing done"
        return

    # convert to numpy arrays
    freqarr = _np.array(freqarr); dataarr = _np.array(dataarr)

    return freqarr, dataarr
