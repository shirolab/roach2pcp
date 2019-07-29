# Quickly plot up last sweep and save pngs

import matplotlib.pyplot as plt
import numpy as np
import pygetdata as gd
import glob
import os

list_of_sweeps = glob.glob('/data/dirfiles/roach0/20??????_??????_sweep')
latest_sweep = max(list_of_sweeps, key = os.path.getctime)

figdir = '/data/tuning/roach0/' + latest_sweep[-21:-6]
if not os.path.isdir(figdir):
    os.mkdir(figdir)

df = gd.dirfile(latest_sweep, gd.RDONLY | gd.UNENCODED)
lo = df.get_carray('sweep.lo_freqs')

for key in df.field_list():

    if (key[-4] == 'K') or (key[-4] == 'B'):

        sweep = df.get_carray('sweep.' + key[-4:])

        plt.figure(1)
        plt.plot((lo-np.mean(lo))/1e3, 20*np.log10(np.abs(sweep)))
        plt.grid()
        plt.xlabel('Offset Frequency [kHz]')
        plt.ylabel('20*log10(mag)')
        plt.title(key[-4:] + ': ' + latest_sweep[-21:-6])

        plt.savefig(figdir + '/' + key[-4:] + '.png') 
        plt.clf()
        
plt.close()
