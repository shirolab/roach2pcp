#!/usr/bin/env python

import logging as _logging
_logger = _logging.getLogger(__name__)

import time
from tqdm import tqdm as _tqdm

from ..configuration import color_msg as cm

def main(roach, nsamples, t):
    _logger.info( "starting streaming for: " + str(t) )

    # for i in range(nsamples):
    #     print cm.OKBLUE + "Start streaming for: " + cm.BOLD + str(t) + "s" + cm.ENDC
    #     roach.start_stream()
    #     time.sleep(t)
    #     roach.stop_stream()
    #     print cm.WARNING + "Stop streaming for: " + cm.BOLD + str(t) + "s" + cm.ENDC
