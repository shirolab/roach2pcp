#!/usr/bin/env python
# Adjust attenuators
# for OUTPUT: adjust output attenuation until ADC range is maximized (while still being safe)

import logging as _logging
_logger = _logging.getLogger(__name__)

from .. import ROACH_LIST, mux_channel
import numpy as np

def maximize_outputatten(muxch, outputmax, outputstep, maxADCval):
    # Always start at maximum attenuation so that we don't damage anything
    att_arr = np.arange(outputmax, -1*np.abs(outputstep), -1*np.abs(outputstep))
    for aa, aav in enumerate(att_arr):
        muxch.output_atten.att = aav
        i, q = muxch.ri.read_ADC()
        print aav, np.max(np.abs(i)), np.max(np.abs(q))
        if (np.max(np.abs(i)) < maxADCval) & (np.max(np.abs(q)) < maxADCval):
            continue
        else:
            break

    if (aa+1) < len(att_arr):  # If we stopped early, set to att just before this one
        max_ind = aa-1
    else: # If we never hit the max ADC, set to last (lowest) att
        max_ind = aa

    _logger.info('Setting output attenuation to ' + str(att_arr[max_ind]) + ' dB')
    muxch.output_atten.att = att_arr[max_ind]


def main(muxch, type = 'output', outputmax = 30, outputstep = 3, maxADCval = 0.5):
    _logger.info("SCRIPT: adjust_att")

    if type == 'output':
        _logger.info('Adjusting output attenuation')
        _logger.info('Maximizing ADC voltage below ' + str(maxADCval) + ' V threshold')
        maximize_outputatten(muxch, outputmax, outputstep, maxADCval)
