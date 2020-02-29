#!/usr/bin/env python

# General script to tune KIDs
# Ideally we eventually stick most of this functionality into mux_channel

_logger = _logging.getLogger(__name__)

from .. import ROACH_LIST, mux_channel

def main(muxch):
    _logger.info( "SCRIPT: tune_kids" )

    # if we haven't already swept, do the first sweep
    if not muxch.sweep.dirfile or force_first_sweep == True:
        # sweep
        muxch.sweep_lo(**swpkwargs)

    # remove blind tones/ don't retune blind tones

    # analyse sweep - tone_freqs = None returns parameters at that F0, and can be used to find F0s
    muxch.sweep.calc_sweep_cal_params( tonefreqs = None, method = findf0_method )
    muxch.sweep.write_sweep_cal_params(overwrite = True)
    # use method to find F0s from KID rountines
    _logger.debug( "new f0s found- {0}".format(muxch.sweep.calparams['f0s']) )
    # change frequencies in self.toneslist
    muxch.toneslist.bb_freqs = muxch.sweep.calparams['f0s'] - muxch.toneslist.lo_freq
    # write to qdr (optional)
    muxch.write_freqs_to_fpga( auto_write = True )
    # resweep with new tones
    muxch.sweep_lo(**swpkwargs)
    # recalculate sweep cal params, this time with the written tones
    muxch.sweep.calc_sweep_cal_params( tonefreqs = muxch.toneslist.rf_freqs, method = findf0_method )
    # write these to the new sweep file
    muxch.sweep.write_sweep_cal_params(overwrite = True)
