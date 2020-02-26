import sys
import os
import matplotlib.pyplot as plt
import numpy as np
import time
import glob
import pygetdata as gd

'''
-Purpose-
As a function of input/output attenuation, do lo sweep
and stream noise data

This assumes a current toneslist that is approx correct written
and that input/output atten are balanced so that ADC voltage is ok'''

def main(r0, atten_in, atten_out,stream_time,  logname, logpath, sweep_span=None, sweep_step=None):
    full_logpath = os.path.join(logpath, logname + '.txt')
    logfile = open(full_logpath, 'w+')
    logfile.write('atten_in, atten_out, dirfile_sweep_initial, dirfile_sweep_tuned, dirfile_ts'+'\n')

    Natten = len(atten_in)
    for ii in range(Natten):
        r0.output_atten.set_atten(atten_out[ii])
        r0.input_atten.set_atten(atten_in[ii])
        #do initial sweep_
        r0.sweep_lo(sweep_span=sweep_span, sweep_step=sweep_step)
        # Load up latest sweep
        initial_sweep = get_latest_sweep()
        load_sweep_and_retune(r0, initial_sweep)
        #retuning done, do another sweep
        r0.sweep_lo(sweep_span=sweep_span, sweep_step=sweep_step)
        tuned_sweep = get_latest_sweep()
        #tuning and sweep done, now take noise time stream
        r0.start_stream(stream_time = stream_time)
        ts_dirfile = get_latest_dirfile()

        logfile.write('{}, {}, {}, {}, {}'.format(str(atten_in[ii]), str(atten_out[ii]), initial_sweep, tuned_sweep, ts_dirfile)+'\n')

    logfile.close()
    return


def get_latest_sweep():
    list_of_sweeps = glob.glob('/data/dirfiles/roach0/20??????_??????_sweep')
    latest_sweep = max(list_of_sweeps, key = os.path.getctime)
    return latest_sweep

def get_latest_dirfile():
    list_of_dirfiles = glob.glob('/data/dirfiles/roach0/20??????_??????')
    latest_dirfile = max(list_of_dirfiles, key = os.path.getctime)
    return latest_dirfile

def load_sweep_and_retune(roach, sweepfile, edge_buffer = 5):

    df = gd.dirfile(sweepfile, gd.RDONLY | gd.UNENCODED)
    lo = df.get_carray('sweep.lo_freqs')
    bb = df.get_carray('sweep.bb_freqs')

    # Standard LO freq
    # lo_cent = roach.synth_lo.frequency
    lo_cent = lo[ len(lo)/2 ]
    '''note lo_cent above relies on center of sweep being lo_cent, and len(lo) is odd
    this is ensured by the function toneslist.get_sweep_lo_freqs()'''
    # For each KID (as labeled by field list), find the lo that maximizes responsivity
    dfdict = {}
    for key in df.field_list():
        if 'sweep.K' in key or 'sweep.B' in key:
            thiskid = key[-4:]
            thissweep = df.get_carray('sweep.' + thiskid)
            #thissweep_buf = thissweep[edge_buffer:-edge_buffer]#removed first and last 'edge_buffer' points
            #lo_buf = lo[edge_buffer:-edge_buffer]
            dSdf = np.gradient(np.real(thissweep))**2 + np.gradient(np.imag(thissweep))**2
            #dSdf = np.gradient(np.real(thissweep_buf))**2 + np.gradient(np.imag(thissweep_buf))**2
            #plt.ion()
            #plt.figure()
            #plt.plot(lo, dSdf)

            dlo = lo[ np.argmax(dSdf) ] - lo_cent # if max is to left, want negative df
            #dlo = lo_buf[ np.argmax(dSdf) ] - lo_cent # if max is to left, want negative df
            #plt.axvline(lo[ np.argmax(dSdf) ], label = 'mag grad')
            #plt.axvline(lo_cent, label = 'cent')
            #plt.legend()
            #plt.show()
            # Apply to roach.toneslist.data
            # I am a total idiot and can't figure out how to just access keys directly in pandas

            for ii in range(np.shape(roach.toneslist.data)[0]):
                if roach.toneslist.data.name[ii] == thiskid:
                    #print dlo
                    roach.toneslist.data.freq[ii] = roach.toneslist.data.freq[ii] + dlo
                    #roach.toneslist.rf_freqs[ii] = roach.toneslist.rf_freqs[ii] + dlo
    #have now retuned RF tones, need to reset the LO to set new bb_freqs
    roach.toneslist.lo_freq = lo_cent
    print roach.toneslist.bb_freqs
    #write new bb_freqs to qdr
    roach.ri.write_freqs_to_qdr(roach.toneslist.bb_freqs,
                                         roach.toneslist.amps,
                                         roach.toneslist.phases)
