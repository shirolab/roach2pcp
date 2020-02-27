#!/usr/bin/env python

# script to set up LO - right now just for UC

import numpy as _np, logging as _logging, time as _time
_logger = _logging.getLogger(__name__)

from .. import ROACH_LIST, mux_channel


def main(muxch, freq = 'default', power = 10.5):
    _logger.info("SCRIPT: lo_wrapper")

    if freq != 'default':
        muxch.toneslist.lo_freq = freq

    _logger.info('Initializing synthesizer to ' + str(muxch.toneslist.lo_freq/1e6) + ' MHz')

    muxch.synth_lo.frequency = muxch.toneslist.lo_freq

    muxch.synth_lo.output_power = power
    muxch.synth_lo.rf_output = True
