#!/usr/bin/env python
# Analyze hot/cold sweeps
# Optionally, semi-interactively take the sweeps too
# NEED TO DO MULTIPLE ROACHES GRACEFULLY
# Add tuningdir to filesys_config?

import logging as _logging
_logger = _logging.getLogger(__name__)

from .. import sweep
from .. import ROACH_LIST, mux_channel
import numpy as np, time as _time, os as _os
from ..lib import lib_dirfiles
from ..configuration import filesys_config, logging_config

def main(muxch, interactive = False, df_hot = None, df_cold = None,
         T_hot = 300., T_cold = 77., tuningdir = '/data/tuning/roach0/cal/'):
    _logger.info("SCRIPT: hotcold")

    # Take interactive if needed
    if interactive == True:
        _logger.info("Taking hot sweep")
        _logger.info("Taking cold sweep")
    
    # Grab hot sweep data
    dfobj_h = lib_dirfiles.open_dirfile(df_hot)
    sweepobj_h = sweep.pcpSweep(dfobj_h)
    # Calculate f0 from sweep
    sweepobj_h.calc_sweep_cal_params(tonefreqs = None, exclude_endpoints = 2)
    hot_f0 = sweepobj_h.calparams['f0s']

    # Grab cold sweep data
    dfobj_c = lib_dirfiles.open_dirfile(df_cold)
    sweepobj_c = sweep.pcpSweep(dfobj_c)
    # Calculate f0 from sweep
    sweepobj_c.calc_sweep_cal_params(tonefreqs = None, exclude_endpoints = 2)
    cold_f0 = sweepobj_c.calparams['f0s']

    # Check that KID name arrays are identical between two sweeps
    assert np.array_equal(sweepobj_h.tonenames, sweepobj_c.tonenames),\
        "Sweeps don't have identical tonelists"
    
    dx = (cold_f0 - hot_f0)/hot_f0
    dx_per_K = dx / (T_hot - T_cold)

    # Save to human-readable text file
    save_textcalfile(hot_f0, cold_f0, dx_per_K,
                     tuningdir, sweepobj_h, sweepobj_c, T_hot, T_cold)
    
    
def save_textcalfile(hot_f0, cold_f0, dx_per_K,
                     tuningdir, sweepobj_h, sweepobj_c, T_hot, T_cold):
    
    tstamp = str(_time.strftime("%Y%m%d_%H%M%S",_time.gmtime()))
    filename = _os.path.join(tuningdir, tstamp + '_hotcold')
    _logger.info("Saving cal data to " + filename)
    # Construct header string
    hdr1 = "Hot/Cold Calibration " + tstamp
    hdr2 = str(T_hot) + " K sweep: " + sweepobj_h.name
    hdr3 = str(T_cold) + " K sweep: " + sweepobj_c.name
    hdr4 = "KID name, f0_hot, f0_cold, (df/f)/K"
    tothead = hdr1 + "\n" + hdr2 + "\n" + hdr3 + "\n" + hdr4

    # Convert stuff to string arrays for easy writing (since KID names are strings)
    # probably more elegant way...
    mytable = np.array([sweepobj_h.tonenames, hot_f0, cold_f0, dx_per_K])
    np.savetxt(filename, mytable.T, fmt='%s', header=tothead)
    
