#!/usr/bin/env python

import logging as _logging
_logger = _logging.getLogger(__name__)

import time
from tqdm import tqdm as _tqdm

from .. import color_logs as CL

def main(roach, nsamples, t):
    _logger.info( "starting streaming for: " + str(t) )

    for i in range(nsamples):
        print "%sStart streaming for: %d s"%(CL.BOLD, str(t))
        roach.start_stream()
        time.sleep(t)
        roach.stop_stream()
        print "%sStop streaming for: %d s"%(CL.BOLD, str(t))
