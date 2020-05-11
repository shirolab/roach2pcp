#!/usr/bin/env python

# General script to tune KIDs
# Ideally we eventually stick most of this functionality into mux_channel
import logging as _logging
_logger = _logging.getLogger(__name__)

from .. import ROACH_LIST, mux_channel
import pcp.visualisation as vis

def write_new_freqs(muxch, newfreqs, **swpkwargs):
    # change frequencies
    muxch.toneslist.data['freq'] = newfreqs
    muxch.toneslist.lo_freq = muxch.toneslist.lo_freq # SUBJECT TO CHANGE
    _logger.info('Writing new frequencies')
    muxch.write_freqs_to_fpga( auto_write = True, check = False)
    # resweep with new tones
    muxch.sweep_lo(**swpkwargs)
    # recalculate sweep cal params, this time with the written tones
    muxch.sweep.calc_sweep_cal_params( tonefreqs = muxch.toneslist.rf_freqs, exclude_endpoints = 2 )
    # write these to the new sweep file
    muxch.sweep.write_sweep_cal_params(overwrite = True)
    
def main(muxch, tunetype='auto', **swpkwargs):
    _logger.info( "SCRIPT: tune_kids" )

    muxch.sweep_lo(**swpkwargs)
    pretune_freq = muxch.sweep.tonefreqs

    # analyze sweep - tone_freqs = None returns parameters at that F0, and can be used to find F0s
    muxch.sweep.calc_sweep_cal_params( tonefreqs = None, exclude_endpoints = 2)

    if tunetype == 'auto':
        _logger.info('Choosing new frequencies automatically')
        posttune_freq = muxch.sweep.calparams['f0s']
        write_new_freqs(muxch, posttune_freq, **swpkwargs)
        print('Delta freq:', (posttune_freq - pretune_freq)/1.e3)
