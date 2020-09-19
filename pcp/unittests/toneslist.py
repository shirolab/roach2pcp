# tests various functionalities for the toneslist

# import the tonelist functions
import pcp.toneslist
import time, numpy as np
import logging as logging
_logger = logging.getLogger(__name__)

_logger.info("Starting unit-testing of tonelist functionality")

# test parameters
roachid = 'dummyroach'

# --- test basic functionality ( without autoload ) ---
_logger.info("-------------------------------------------------")
_logger.info("testing of various methods of initialisation")

_logger.info("1. auto-load = False, lo_freq = None")
tl = pcp.toneslist.Toneslist(roachid, auto_load=0)
_logger.info("1a. load file with lo_freq")
tl.load_tonelist(tl.tonelistfile, lo_freq=100)
_logger.info("1b. load file without lo_freq")
tl.load_tonelist(tl.tonelistfile, lo_freq=None)

_logger.info("2. auto-load = False, lo_freq = 100")
tl = pcp.toneslist.Toneslist(roachid, auto_load=0, lo_freq = 100)
_logger.info("2a. load file with lo_freq")
tl.load_tonelist(tl.tonelistfile, lo_freq=100)
_logger.info("2a. load file without lo_freq")
tl.load_tonelist(tl.tonelistfile, lo_freq=None)

_logger.info("3. auto-load = True, lo_freq = None")
tl = pcp.toneslist.Toneslist(roachid, auto_load=1)
_logger.info("4. auto-load = True, lo_freq = 100")
tl = pcp.toneslist.Toneslist(roachid, auto_load=1, lo_freq = 100)

_logger.info("-------------------------------------------------")
_logger.info("testing of check_for_overlap_freqs function")
_logger.info("1. single bb_freqs check")
freqlist = tl.bb_freqs
isbad, _ = pcp.toneslist.check_for_overlap_freqs(freqlist, tl.fft_binwidth)
_logger.info("passed: single bb_freq list")

_logger.info("2. multiple bb_freqs check using calc_sweep_lo_freqs function")
span = 100e6
step = span/101 # points
tl.calc_sweep_lo_freqs(span, step)
lo_freqs = tl.sweep_lo_freqs
_logger.info("passed: calc_sweep_lo_freqs function")

freqlist = (np.tile(tl.rf_freqs, ( len(lo_freqs), 1 ) ).T - lo_freqs).T
isbad, _ = pcp.toneslist.check_for_overlap_freqs(freqlist, tl.fft_binwidth)
_logger.info("passed: check_for_overlap_freqs multiple ")

time.sleep(1e-3) # let the log messages finish before returning 
