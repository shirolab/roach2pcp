#!/usr/bin/env python

# General script to tune KIDs
# Ideally we eventually stick most of this functionality into mux_channel
import logging as _logging
_logger = _logging.getLogger(__name__)

from .. import ROACH_LIST, mux_channel
import pcp.visualisation as vis

def main(muxch, **swpkwargs):
    _logger.info( "SCRIPT: tune_kids" )

    muxch.sweep_lo(**swpkwargs)

    # analyse sweep - tone_freqs = None returns parameters at that F0, and can be used to find F0s
    muxch.sweep.calc_sweep_cal_params( tonefreqs = None, exclude_ends = 2)

    # change frequencies
    muxch.toneslist.data['freq'] = muxch.sweep.calparams['f0s']
    muxch.toneslist.lo_freq = muxch.toneslist.lo_freq # SUBJECT TO CHANGE
    # write to qdr (optional)
    muxch.write_freqs_to_fpga( auto_write = True, check = False)
    # resweep with new tones
    muxch.sweep_lo(**swpkwargs)
    # recalculate sweep cal params, this time with the written tones
    muxch.sweep.calc_sweep_cal_params( tonefreqs = muxch.toneslist.rf_freqs, exclude_ends = 2 )
    # write these to the new sweep file
    muxch.sweep.write_sweep_cal_params(overwrite = True)
