#!/usr/bin/env python


import logging as _logging
_logger = _logging.getLogger(__name__)

from .. import ROACH_LIST, mux_channel

def main(muxch):
    _logger.info("SCRIPT: upload_fpgas")

    # Need to expand this to dict of ROACHes (ROACH_LIST???)
    muxch.ri.initialise_fpga(force_reupload = True)
