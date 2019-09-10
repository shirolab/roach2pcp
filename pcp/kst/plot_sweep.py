# Quickly plot sweep and save pngs

import matplotlib.pyplot as plt
import numpy as np
import pygetdata as gd
import glob
import os

def plot_sweep(sweepfile = 'latest', html=None):
    """ No slash when inputting sweepfile name
    HTML file - template to save in folder (as index.html)
    """

    if sweepfile == 'latest':
        list_of_sweeps = glob.glob('/data/dirfiles/roach0/20??????_??????_sweep')
        mysweep = max(list_of_sweeps, key = os.path.getctime)
    else:
        mysweep = sweepfile
        
    figdir = '/data/tuning/roach0/' + mysweep[-21:-6]
    if not os.path.isdir(figdir):
        os.mkdir(figdir)

    if html is not None:
        cmd = 'cp ' + html + ' ' + figdir + '/index.html'
        os.system(cmd)
        
    df = gd.dirfile(mysweep, gd.RDONLY | gd.UNENCODED)
    lo = df.get_carray('sweep.lo_freqs')
    off_freq = (lo - np.mean(lo))/1e3
    
    for key in df.field_list():
        
        if (key[-4] == 'K') or (key[-4] == 'B'):
            
            sweep = df.get_carray('sweep.' + key[-4:])
            s21 = 20*np.log10(np.abs(sweep))
            dSdf = np.gradient(np.real(sweep))**2 + \
                   np.gradient(np.imag(sweep))**2
            plt.figure(1, figsize=(13,5))
            plt.subplot(1,2,1)
            plt.plot(off_freq, s21)
            plt.plot(np.array([off_freq[np.argmax(dSdf)],off_freq[np.argmax(dSdf)]]),
                     np.array([np.min(s21), np.max(s21)]), '--r',
                     label='Max dSdf')
            plt.plot(np.array([0, 0]), np.array([np.min(s21), np.max(s21)]), '-k',
                     label='Current Tone')
            plt.grid()
            plt.legend(loc='best')
            plt.xlabel('Offset Frequency [kHz]')
            plt.ylabel('$20*\log_{10}(|S_{21}|)$, arb. offset')
            plt.title('$S_{21}$')
            
            plt.subplot(1,2,2)
            plt.plot(np.real(sweep)/1e5, np.imag(sweep)/1e5)
            plt.axis('scaled')
            plt.xlabel('I [arb]')
            plt.ylabel('Q [arb]')
            plt.grid()
            plt.title('I/Q')
            
            plt.suptitle(key[-4:] + ': ' + mysweep[-21:-6])
            plt.savefig(figdir + '/' + key[-4:] + '.png') 
            plt.clf()
                
    plt.close()
