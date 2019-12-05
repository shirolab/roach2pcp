#
# Plotting routines to visualise various data products

# Demo visualisation tool
#   [20190304] Plot for averaged data completed. It shows sweeps, IQ circles and speed figures
#
# 	[20181217] So far you can plot the data from a the raw directory, but it has to be able to read it from the sweep folder as well.
#	It just plot the magnitude vs frequency and IQ circles, the rest of the options are empty. The plot functions need to take in consideration
#	the tonelist and the central frequency to correct the x-axis
#
#	To run:
#
#   bb-> For the moment comes from toneslist, but in future it should be in the directories
#	>> dirfile = "./pcp/testing/run/data/dummyroach/20181125_172118_sweep_raw/"
#	>> plot_sweep_data(dirfile,bb)

import os as _os
import numpy as _np

from scipy.signal import savgol_filter

import cmath as _cmath
import pygetdata as _gd

def get_sweep_data(diryfile):
    """
    Get data from a sweep dirfile which is the averaged data from raw directories
    """

    sweep_dirfile = _gd.dirfile(diryfile, _gd.RDONLY)

    field_lo = "sweep.lo_freqs"
    field_bb_freqs = "sweep.bb_freqs"

    kids_fields = [field[6:] for field in sweep_dirfile.field_list() if field.startswith("sweep.") and field != field_lo and field != field_bb_freqs]

    sweep_lo = sweep_dirfile.get_carray(field_lo)
    bb_freqs = sweep_dirfile.get_carray(field_bb_freqs)

    # Sweep data, like complex numbers
    sweep_data = dict()
    lo_freqs = dict()

    n = 0
    for kid in kids_fields:
        lo_freqs[kid] = sweep_lo + bb_freqs[n]
        sweep_data[kid] = sweep_dirfile.get_carray("sweep." + kid)
        n += 1

    return lo_freqs, sweep_data

def get_stream_data(diryfile):
    """
    Get data from time stream dirfile
    """

    time_dirfile = _gd.dirfile(diryfile, _gd.RDONLY)

    time_field = "python_timestamp"
    fields_forbiden = ['metadata.type','metadata.raw_sweep_filename','INDEX', 'gpio_reg', 'raw_packet', 'packet_count', 'pps_timestamp', 'fine_timestamp', 'roach_checksum', 'packet_info_reg', 'python_timestamp']
    kids_fields = [field for field in time_dirfile.field_list() if not (field in fields_forbiden or field.startswith("sweep."))]

    time = time_dirfile.getdata(time_field)

    # Time data
    time_stream = dict()

    for kid in kids_fields:
        time_stream[kid] = time_dirfile.getdata(kid)

    return time, time_stream

def get_dxdf(freqs, x, smooth=True, order=3, npoints=15):
    """
    Get dx/df, where x could be i or q
    """
    if smooth:
        x = savgol_filter(x, npoints, order)

    dx_df = _np.gradient(x)/_np.gradient(freqs)

    return dx_df, x

def get_df(I, Q, I_sweep, Q_sweep, didf, dqdf, f0):
    """
    Get df. Variability in resonance frequency
    """
    speed_mag = (didf[f0]**2)+(dqdf[f0]**2)
    df = (((I_sweep[f0]-I)*didf[f0]) + ((Q_sweep[f0]-Q)*dqdf[f0])) / speed_mag
    return df

def get_mag_from_IQ(I, Q):
    """
    Get the magnitude from I and Q
    """
    return _np.sqrt(I**2 + Q**2)

def get_mag(cmplx):
    """
    Get the magnitude from complex value
    """
    return abs(cmplx)

def get_mag_log(cmplx):
    """
    Get the magnitude from I and Q
    """
    return 10*_np.log10(abs(cmplx))

def get_phase(cplx_IQ, deg=False):
    """
    Get the phase from I,Q signals
    """
    phase = _cmath.phase(cplx_IQ)
    if deg:
        return phase*180/_np.pi
    else:
        return phase

def get_speed(freqs, cplx_IQ):
    """
    Get the speed from I,Q signals
    """
    di_df = _np.gradient(cplx_IQ.real)/_np.gradient(freqs)
    dq_df = _np.gradient(cplx_IQ.imag)/_np.gradient(freqs)

    speed = _np.sqrt(di_df**2 + dq_df**2)

    return freqs, speed

def main():
    print "Functions to get S21, time streams, df, PSD, etc... loaded"
