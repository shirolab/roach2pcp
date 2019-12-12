# Write a tonelist file in our preferred CSV format

import csv

def write_tonelist(filename, kidnames, freqs):
    # Check that kidnames/freqs are the same length
    if len(kidnames) != len(freqs):
        raise Exception('kidnames and freqs are not the same length')
    
    with open(filename, mode='w') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter = '\t')
        csv_writer.writerow(['Name', 'Freq', 'Offset att', 'All', 'None'])

        for kk, kkv in enumerate(kidnames):
            csv_writer.writerow([kidnames[kk], str(int(freqs[kk])), '0', '1', '0'])

def gen_kidnames(numarr, prefix = 'K'):
    """ Prepend a numerical array with a prefix - max 999 tones
    """
    out = []
    for nn in numarr:
        out.append(prefix + '%03i' % nn)

    return out

"""
Example usage:
import write_tonelist as wt
import numpy as np
t_arr = wt.gen_kidnames(np.arange(0,300), prefix='K') # Primary
b_arr = wt.gen_kidnames(np.arange(0,300), prefix='B') # Blind
kidnames = t_arr + b_arr
f_arr = np.linspace(100e6, 399e6, len(t_arr)) # Primary freqs
g_arr = f_arr + 100e3 # Blind freqs
freqs = np.concatenate((f_arr, g_arr))
wt.write_tonelist('mytonelist.txt', kidnames, freqs)
"""
        
    
