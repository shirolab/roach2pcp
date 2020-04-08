#!/usr/bin/env python

# script to take sweeps at a bunch of power levels

import numpy as _np, logging as _logging, time as _time
_logger = _logging.getLogger(__name__)

from .. import ROACH_LIST, mux_channel


def main(muxch, input_att = None, output_att = None):
    _logger.info("SCRIPT: power_sweep")

    init_in = muxch.input_atten.att
    init_out = muxch.output_atten.att
    
    if input_att is None:
        input_att = np.array([30, 27, 24, 21, 18, 15, 12, 9, 6, 3, 0])

    if output_att is None:
        output_att = np.array([60, 50, 40, 30, 20, 10, 0])
    
    for aa in input_att:
        
        muxch.input_atten.att = aa

        for oo in output_att:

            muxch.output_atten.att = oo

            muxch.sweep_lo()
            _logger.info('IN: ' + str(muxch.input_atten.att) +
                         ', OUT: ' + str(muxch.output_atten.att) +
                         ', ' + muxch.sweep.name)

    muxch.input_atten.att = init_in
    muxch.output_atten.att = init_out

    
            
