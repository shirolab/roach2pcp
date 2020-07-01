#!/usr/bin/env python

# script to measure the amplitude correction.
# This script is intended only to be run once, for a given tonelist.

# A targeted spectrum sweep with a spectrum analyzer (that has to have a method targeted_sweep() ).
# Uses the curent uploaded toneslist/LO settings to do windowed sweep
# centered on each tone with a variable span, resolution bandwidth, and
# video bandwidth.
#
import os as _os, numpy as _np, logging as _logging, time as _time
_logger = _logging.getLogger(__name__)

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

def main(specan, freqs_to_sweep, span = 100e3, filetosave = None):
    """ """
    _logger.info( "Running spectrum analyser measurement" )

    # confirm that spectrum analyser is operational and works as expected
    assert _initialise_spec_analyser(specan)

    # sweep over the tones
    freqarr, dataarr = [],[]
    try:
        for f in freqs_to_sweep:
            freqs, data = specan.targeted_sweep(f, span)
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

    if filetosave is not None:
        # #check if path is a dir and exists
        # if so, then create timestamped filename
        if _os.path.abspath(filetosave) and not _os.path.exists(filetosave):
            fname = filetosave
        elif _os.path.isdir(filetosave) and _os.path.exists(filetosave):
            # create timestamped filename
            fname = _os.path.join( filetosave, _time.strftime("%Y%m%d-%H%M%S-spectrum") )
        else:
            _logger.warning("given filename appears to be neither a valid directory, or the path exists. ")




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
