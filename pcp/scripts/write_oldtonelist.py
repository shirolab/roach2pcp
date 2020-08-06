#!/usr/bin/env python
"""
Script to rewrite a set of tones from a tonelist
"""

import logging as _logging
_logger = _logging.getLogger(__name__)

import pcp

def main(muxch, timestamp):

    _logger.info("SCRIPT: write_oldtonelist")

    # check timestamp is valid
    valid_ts = muxch.toneslist.tonehistory.keys()
    assert timestamp in valid_ts, "not a valid timestamp - must be one of {0}".format(valid_ts)

    # load the tone history file
    lofreq, atten_in, atten_out, bb_freqs, amps, phases = muxch.toneslist.load_tonehistfile(timestamp)

    # modify the toneslist with the parameters from the loaded tone history file
    muxch.toneslist.amps     = amps
    muxch.toneslist.phases   = phases
    muxch.toneslist.bb_freqs = bb_freqs

    # set the lo-frequencies for both toneslist and synth
    muxch.toneslist.lo_freq  = lofreq
    muxch.synth_lo.frequency = lofreq

    # set attenuations
    muxch.atten_in.attenuation  = atten_in
    muxch.atten_out.attenuation = atten_out

    # write the new tones ( uses values from the updated tonelist )
    muxch.write_freqs_to_fpga(auto_write = True, check = False)
