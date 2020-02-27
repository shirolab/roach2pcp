#!/usr/bin/env python


import logging as _logging
_logger = _logging.getLogger(__name__)

from .. import ROACH_LIST, mux_channel

def main(muxch, timestamp):
    _logger.info("SCRIPT: write_oldtonelist")

    muxch.toneslist.load_tonehistfile(timestamp)
    muxch.write_freqs_to_fpga(auto_write = True, check = False)
