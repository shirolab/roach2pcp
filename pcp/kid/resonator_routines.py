
#!/usr/bin/env python

# any code related to KID/resonator functions should be included here


import logging as _logging, numpy as _np
from ..lib.lib_dirfiles import SWEEP_CALPARAM_FIELDS

import scipy.ndimage as _snd


_logger = _logging.getLogger(__name__)

def calc_sweep_cal_params(sweep_f, sweep_i, sweep_q, tone_freqs = None , nanmask = None, **kwargs):

    """
    Given a sweep dataset, this function will return  I,Q,dI/df,dQ/df at f0. If a list of tone_freqs is specified,
    then the function returns calibration parameters at that frequency, otherwise the maximum values are calculated.

    """
    despike_window = kwargs.pop('despike_window',1)
    if despike_window is None: despike_window = 1
    
    assert sweep_i.shape[-1] == sweep_q.shape[-1] == sweep_f.shape[-1], "data does not appear to be in the correct shape"

    # convert to at least 2d to vectorise processing for multiple resonators at once
    sweep_f, sweep_i, sweep_q = _np.atleast_2d(sweep_f, sweep_i, sweep_q)

    # calculate gradient parameters
    df   = _np.gradient( sweep_f, axis=1 )
    didf = _np.gradient( sweep_i, axis=1 ) / df
    dqdf = _np.gradient( sweep_q, axis=1 ) / df
    didq2 = didf**2 + dqdf**2

    if tone_freqs is not None:

        tone_freqs = _np.atleast_1d(tone_freqs)

        assert len(tone_freqs) == sweep_f.shape[0], "length of written tones does not match the data shape"
        # check that the given tone frequencies are within the range of the sweep frequencies
        assert _np.logical_and( tone_freqs >= sweep_f.min(), tone_freqs <= sweep_f.max() ).all(),\
                                            "some frequencies appear to lie outside of the given sweep range"
        # find the frequency index in the sweep freq data that corresponds to the closest tone frequency
        idxs = _np.argmin( _np.abs(sweep_f - tone_freqs[:, _np.newaxis]), axis=1 )
    else:
        # return the maximum values
        # nanmask = nanmask if nanmask else _np.ones_like(didq2, dtype='bool')
        # didq2[nanmask] = _np.nan
        # idxs = _np.nanargmax( didq2, axis=1 )

        if nanmask is not None:
            dum = didq2
            dum[nanmask] = _np.nan
            idxs = _np.nanargmax(_snd.median_filter(dum,(1,despike_window)), axis=1)
        else:
            idxs = _np.argmax(_snd.median_filter(didq2,(1,despike_window)), axis=1 )


    # set up a 2D array to index along the second dimension all at once
    idxs = ( _np.arange(len(idxs)), idxs )

    # the values have to be in the same order as SWEEP_CALPARAM_FIELDS is defined
    calparamlist = [ sweep_f[idxs], sweep_i[idxs], sweep_q[idxs], didf[idxs], dqdf[idxs], didq2[idxs] ]
    assert len(calparamlist) == len(SWEEP_CALPARAM_FIELDS), "mismatch in length of cal parameters and available fields"

    calparams = {k: v for k,v in zip( SWEEP_CALPARAM_FIELDS, calparamlist) }

    return  calparams, (didf + 1j*dqdf)


def nonlinear_mag_sq(x,fr,Qr,amp,phi,a,b0,b1,flin):
    # x is the frequeciesn your iq sweep covers
    # fr is the center frequency of the resonator
    # Qr is the quality factor of the resonator
    # amp is Qr/Qc
    # phi is a rotation paramter for an impedance mismatch between the resonaotor and the readout system
    # a is the non-linearity paramter bifurcation occurs at a = 0.77
    # b0 DC level of s21 away from resonator
    # b1 Frequency dependant gain varation
    # flin is probably the frequency of the resonator when a = 0
    #
    # This is based of fitting code from MUSIC
    # The idea is we are producing a model that is described by the equation below
    # the frist two terms in the large parentasis and all other terms are farmilar to me
    # but I am not sure where the last term comes from though it does seem to be important for fitting
    #
    #                          /        (j phi)            (j phi)   \  2
    #|S21|^2 = (b0+b1 x_lin)* |1 -amp*e^           +amp*(e^       -1) |^
    #                         |   ------------      ----              |
    #                          \     (1+ 2jy)         2              /
    #
    # where the nonlineaity of y is described by the following eqution taken from Response of superconducting microresonators
    # with nonlinear kinetic inductance
    #                                     yg = y+ a/(1+y^2)  where yg = Qr*xg and xg = (f-fr)/fr
    #

    xlin = (x - flin)/flin
    xg = (x-fr)/fr
    yg = Qr*xg
    y = _np.zeros(x.shape[0])
    #find the roots of the y equation above
    for i in range(0,x.shape[0]):
        # 4y^3+ -4yg*y^2+ y -(yg+a)
        coeff = (4.0,-4.0*yg[i],1.0,-(yg[i]+a))
        roots = solve_cubic(coeff)
        #roots = np.roots((16.,-16.*yg[i],8.,-8.*yg[i]+4*a*yg[i]/Qr-4*a,1.,-yg[i]+a*yg[i]/Qr-a+a**2/Qr))   #more accurate version that doesn't seem to change the fit at al
        # only care about real roots
        where_real = _np.where(_np.imag(roots) == 0)
        y[i] = _np.max(_np.real(roots[where_real]))
    z = (b0 +b1*xlin)*_np.abs(1.0 - amp*_np.exp(1.0j*phi)/ (1.0 +2.0*1.0j*y) + amp/2.*(_np.exp(1.0j*phi) -1.0))**2
    return z

def solve_cubic(coeff):
    a, b, c, d = coeff
    #of the form ax^3 + bx^2 + cx + d = 0
    if (a == 0 and b == 0):                     # Case for handling Liner Equation
        return _np.array([(-d * 1.0) / c])                 # Returning linear root as numpy array.

    elif (a == 0):                              # Case for handling Quadratic Equations

        D = c * c - 4.0 * b * d                       # Helper Temporary Variable
        if D >= 0:
            D = _np.sqrt(D)
            x1 = (-c + D) / (2.0 * b)
            x2 = (-c - D) / (2.0 * b)
        else:
            D = _np.sqrt(-D)
            x1 = (-c + D * 1j) / (2.0 * b)
            x2 = (-c - D * 1j) / (2.0 * b)

        return _np.array([x1, x2])               # Returning Quadratic Roots as numpy array.

    f = ((3.0 * c / a) - ((b ** 2.0) / (a ** 2.0))) / 3.
    g = (((2.0 * (b ** 3.0)) / (a ** 3.0)) - ((9.0 * b * c) / (a **2.0)) + (27.0 * d / a)) /27.0
    h = ((g ** 2.0) / 4.0 + (f ** 3.0) / 27.0)

    if f == 0 and g == 0 and h == 0:            # All 3 Roots are Real and Equal
        if (d / a) >= 0:
            x = (d / (1.0 * a)) ** (1 / 3.0) * -1
        else:
            x = (-d / (1.0 * a)) ** (1 / 3.0)
        return _np.array([x, x, x])              # Returning Equal Roots as numpy array.

    elif h <= 0:                                # All 3 roots are Real

        i = _np.sqrt(((g ** 2.0) / 4.0) - h)   # Helper Temporary Variable
        j = i ** (1 / 3.0)                      # Helper Temporary Variable
        k = _np.arccos(-(g / (2 * i)))           # Helper Temporary Variable
        L = j * -1                              # Helper Temporary Variable
        M = _np.cos(k / 3.0)                   # Helper Temporary Variable
        N = _np.sqrt(3) * _np.sin(k / 3.0)    # Helper Temporary Variable
        P = (b / (3.0 * a)) * -1                # Helper Temporary Variable

        x1 = 2 * j * _np.cos(k / 3.0) - (b / (3.0 * a))
        x2 = L * (M + N) + P
        x3 = L * (M - N) + P

        return _np.array([x1, x2, x3])           # Returning Real Roots as numpy array.

    elif h > 0:                                 # One Real Root and two Complex Roots
        R = -(g / 2.0) + _np.sqrt(h)           # Helper Temporary Variable
        if R >= 0:
            S = R ** (1 / 3.0)                  # Helper Temporary Variable
        else:
            S = (-R) ** (1 / 3.0) * -1          # Helper Temporary Variable
        T = -(g / 2.0) - _np.sqrt(h)
        if T >= 0:
            U = (T ** (1 / 3.0))                # Helper Temporary Variable
        else:
            U = ((-T) ** (1 / 3.0)) * -1        # Helper Temporary Variable

        x1 = (S + U) - (b / (3.0 * a))
        x2 = -(S + U) / 2 - (b / (3.0 * a)) + (S - U) * _np.sqrt(3) * 0.5j
        x3 = -(S + U) / 2 - (b / (3.0 * a)) - (S - U) * _np.sqrt(3) * 0.5j

        return _np.array([x1, x2, x3])           # Returning One Real Root and two Complex Roots as numpy array.

    # return {"f0s": sweep_f[idxs], \
    #         "i0s": sweep_i[idxs], \
    #         "q0s": sweep_q[idxs], \
    #         "didf": didf[idxs], \
    #         "dqdf": dqdf[idxs], \
    #         "didf_sumdidq2": didf[idxs] / didq2[idxs],\
    #         "dqdf_sumdidq2": dqdf[idxs] / didq2[idxs],\
    #         "i0_didf_sumdidq2": sweep_i[idxs] * didf[idxs] / didq2[idxs] ,\
    #         "q0_dqdf_sumdidq2": sweep_q[idxs] * dqdf[idxs] / didq2[idxs] },  (didf + 1j*dqdf)


# def find_f0_from_sweep(freq, i, q, method="maxspeed", **kwargs):
#
#     """
#     Given arrays of frequency, I and Q, find the resonant frequency using the speicfied method.
#
#     Arrays of I and Q can be 2D, but the length of the last dimension should be equal to the length of freqs
#     Available kwargs:
#
#     filter_dict : a set of filter parameters to be used to filter the data before finding. Format
#         is k,v where v is a list-like containing a filter function and any args to go along with that filter
#
#
#     """
#
#     assert method in ["maxspeed", "mins21"], "invalid method given {0}".format(method)
#
#     assert i.shape[-1] == q.shape[-1] == freq.shape[0]
#
#     # convert to at least 2d to vectorise processing for multiple resonators at once
#     i,q = _np.atleast_2d(i,q)
#
#     ### parse kwargs ###
#
#     # filter dict
#     filter_dict = ( kwargs.pop("filter_dict", {"filter": []}) )
#
#     if method == "mins21":
#         return freq[ _np.argmin(_np.sqrt(i**2 + q**2), axis = 1) ]
#
#     elif method == "maxspeed":
#         di = _np.gradient(i, axis = 1)
#         dq = _np.gradient(q, axis = 1)
#         return freq[ _np.argmax( _np.sqrt(di**2 + dq**2), axis = 1) ]
