#!/usr/bin/env python

# script to measure the amplitude correction.
# This script is intended only to be run once, for a given tonelist.

import numpy as _np, logging as _logging, time as _time
_logger = _logging.getLogger(__name__)

from .. import ROACH_LIST, mux_channel


def main(muxch, span = 100e3, baseband=False, save=True):
    _logger.info( "SCRIPT: ampcorr_wrapper" )

    # First, write the original tones list (equal amplitudes)
    muxch.write_freqs_to_fpga(auto_write = True)

    # Bring in FPC object
    from ..drivers.ancillary.fpc1000 import FPC1000
    fpcobj = FPC1000()

    # Measure correction (and save it)
    from .. import scripts
    scripts.measure_ampcorr(muxch, fpcobj)

    # Now write the new tones list
    muxch.write_freqs_to_fpga(auto_write = True, corrtouse = 'total', check = False)
