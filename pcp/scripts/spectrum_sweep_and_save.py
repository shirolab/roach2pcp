import imp
import sys
import os
import matplotlib.pyplot as plt
import numpy as np
import time
spec_analyzer_path = os.path.join(os.sep, 'home', 'kids', 'Documents', 'Roach_characterization_2019', 'scripts', 'FPC1000.py')

spec_analyzer = imp.load_source('FPC1000', spec_analyzer_path)


'''
This script will take a targeted spectrum sweep with FPC spectrum analyzer.
Uses the curent uploaded toneslist/LO settings to do windowed sweep
centered on each tone with a variable span, resolution bandwidth, and
video bandwidth.

Saves the outputs of the spectrum sweep to savedir
'''

def main(roach, savedir, savestr, span, rbw, vbw, save = False, baseband=False, ret=False):
    #instantiate class connection to FPC1000
    FPC = spec_analyzer.FPC1000()
    #calculate the frequencies to be targeted
    if baseband==False:
        tone_array = np.sort(roach.toneslist.rf_freqs.values )
    else:
        tone_array = np.sort(np.abs(roach.toneslist.bb_freqs.values))
    #do targeted sweep
    full_freq, sweep_data, maxes, maxes_freq = FPC.targeted_sweep(tone_array, span, rbw, vbw)
    if save == True:
        full_save_path = os.path.join(savedir, savestr)
        np.savez(full_save_path,freq=full_freq, sweep = sweep_data, maxes = maxes, maxes_freq = maxes_freq)
    if ret == True:
        return full_freq, sweep_data, maxes, maxes_freq

