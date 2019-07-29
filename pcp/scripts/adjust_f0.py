import numpy as np
import pygetdata as gd
import glob
import os

def main(roach):

    print roach.toneslist.bb_freqs
    # Take a sweep
    roach.sweep_lo()

    # Load it up
    list_of_sweeps = glob.glob('/data/dirfiles/roach0/20??????_??????_sweep')
    latest_sweep = max(list_of_sweeps, key = os.path.getctime)

    df = gd.dirfile(latest_sweep, gd.RDONLY | gd.UNENCODED)
    lo = df.get_carray('sweep.lo_freqs')
    bb = df.get_carray('sweep.bb_freqs')

    # Standard LO freq
    lo_cent = roach.synth_lo.frequency
    # For each KID (as labeled by field list), find the lo that maximizes responsivity
    dfdict = {}
    for key in df.field_list():
        if key[-4] == 'K':
            thiskid = key[-4:]
            thissweep = df.get_carray('sweep.' + thiskid)

            dSdf = np.gradient(np.real(thissweep))**2 + np.gradient(np.imag(thissweep))**2

            dlo = lo[ np.argmax(dSdf) ] - lo_cent # if max is to left, want negative df

            # Apply to roach.toneslist.data
            # I am a total idiot and can't figure out how to just access keys directly in pandas

            for ii in range(np.shape(roach.toneslist.data)[0]):
                if roach.toneslist.data.name[ii] == thiskid:
                    #print dlo
                    roach.toneslist.data.freq[ii] = roach.toneslist.data.freq[ii] + dlo


    # Reset lo freq to get new bb freqs
    roach.toneslist.lo_freq = lo_cent
    print roach.toneslist.bb_freqs
    # Rewrite tones
    # roach.toneslist.amps = np.ones_like(roach.toneslist.bb_freqs)
    # roach.toneslist.set_phases()
    roach.roach_iface.write_freqs_to_qdr(roach.toneslist.bb_freqs,
                                         roach.toneslist.amps,
                                         roach.toneslist.phases)
    roach.sweep_lo()
