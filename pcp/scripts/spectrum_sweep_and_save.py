import os as _os
import numpy as _np


import logging as _logging
_logger = _logging.getLogger(__name__)

from ..drivers.ancillary import fpc1000

'''
This script will take a targeted spectrum sweep with FPC spectrum analyzer.
Uses the curent uploaded toneslist/LO settings to do windowed sweep
centered on each tone with a variable span, resolution bandwidth, and
video bandwidth.

Saves the outputs of the spectrum sweep to savedir
'''

#instantiate class connection to FPC1000

def main(roach, savedir, savestr, span, rbw, vbw, save = False, baseband=False, ret=False):
    try:
        fpcobj = fpc1000.FPC1000()
    except ValueError as err:
        _logger.error(err.message)

    #calculate the frequencies to be targeted
    if baseband==False:
        tone_array = _np.sort(roach.toneslist.rf_freqs.values )
    else:
        tone_array = _np.sort(_np.abs(roach.toneslist.bb_freqs.values))
    #do targeted sweep
    full_freq, sweep_data, maxes, maxes_freq = fpcobj.targeted_sweep(tone_array, span, rbw, vbw)
    if save == True:
        full_save_path = _os.path.join(savedir, savestr)
        _np.savez(full_save_path,freq=full_freq, sweep = sweep_data, maxes = maxes, maxes_freq = maxes_freq)
    if ret == True:
        return full_freq, sweep_data, maxes, maxes_freq
