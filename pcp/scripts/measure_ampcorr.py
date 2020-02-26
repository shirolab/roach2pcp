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

def main(muxch, specan, span = 100e3, baseband=False, save=True):
    _logger.info( "SCRIPT: measure_ampcorr" )

    # confirm that spectrum analyser is operational and works as expected
    assert _initialise_spec_analyser(specan)

    #calculate the frequencies to be targeted
    if baseband==False:
        tones_to_sweep = muxch.toneslist.rf_freqs # check VALUES?
    else:
        tones_to_sweep = _np.abs( muxch.toneslist.bb_freqs )
    #Initialize settings for targeted sweep
    specan.setup_for_targeted_sweep(specan.rbw, specan.vbw)

    # sweep over the tones
    freqarr, dataarr = [],[]
    try:
        for tone in tones_to_sweep:
            freqs, data = specan.targeted_sweep(tone, span)
            freqarr.append(freqs); dataarr.append(data)

    except KeyboardInterrupt:
        print "interuppted - nothing done"
        return

    # convert to numpy arrays
    freqarr = _np.array(freqarr); dataarr = _np.array(dataarr)

    # find the maxes and return the frequencies
    maxargs  = _np.argmax(dataarr, axis=1)
    # set up a 2D array to index along the second dimension all at once
    maxidxs  = ( _np.arange(len(maxargs)), maxargs )
    fmaxes   = freqarr[maxidxs]
    tonemaxs = dataarr[maxidxs]

    dbchange = -1.0 * (tonemaxs - _np.min(tonemaxs))
    ampcorr = 10**( dbchange / 20.0 )

    # add new entry to mc.tonelist.ampcorr with unix time as the key
    muxch.toneslist.ampcorr.update( { str(int(_time.time())): ampcorr} )
    _logger.info('New amplitude correction saved')

    if save == True:
        # save to a new ampcorr file
        muxch.toneslist._write_ampcorrfile(ignore_dups=False)


# from ..drivers.ancillary import fpc1000
#
# '''
# This script will take a targeted spectrum sweep with FPC spectrum analyzer.
# Uses the curent uploaded toneslist/LO settings to do windowed sweep
# centered on each tone with a variable span, resolution bandwidth, and
# video bandwidth.
#
# Saves the outputs of the spectrum sweep to savedir
# '''
#
# #instantiate class connection to FPC1000
# try:
#     fpcobj = fpc1000.FPC1000()
# except ValueError as err:
#     _logger.error(err.message)
#
# def main(roach, savedir, savestr, span, rbw, vbw, save = False, baseband=False, ret=False):
#     #calculate the frequencies to be targeted
#     if baseband==False:
#         tone_array = _np.sort(roach.toneslist.rf_freqs.values )
#     else:
#         tone_array = _np.sort(_np.abs(roach.toneslist.bb_freqs.values))
#     #do targeted sweep
#     full_freq, sweep_data, maxes, maxes_freq = fpcobj.targeted_sweep(tone_array, span, rbw, vbw)
#     if save == True:
#         full_save_path = _os.path.join(savedir, savestr)
#         _np.savez(full_save_path,freq=full_freq, sweep = sweep_data, maxes = maxes, maxes_freq = maxes_freq)
#     if ret == True:
#         return full_freq, sweep_data, maxes, maxes_freq
