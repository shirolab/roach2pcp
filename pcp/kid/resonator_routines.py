#!/usr/bin/env python

# any code related to KID/resonator functions should be included here


import logging as _logging, numpy as _np
from ..lib.lib_dirfiles import SWEEP_CALPARAM_FIELDS

_logger = _logging.getLogger(__name__)

def calc_sweep_cal_params(sweep_f, sweep_i, sweep_q, tone_freqs = None , **kwargs):

    """
    Given a sweep dataset, this function will return  I,Q,dI/df,dQ/df at f0. If a list of tone_freqs is specified, then the function returns calibration parameters at that
    frequency, otherwise the maximum values are calculated.

    """

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
        idxs = _np.argmax( didq2, axis=1 )

    # set up a 2D array to index along the second dimension all at once
    idxs = ( _np.arange(len(idxs)), idxs )

    # the values have to be in the same order as SWEEP_CALPARAM_FIELDS is defined
    calparamlist = [ sweep_f[idxs], sweep_i[idxs], sweep_q[idxs], didf[idxs], dqdf[idxs], didq2[idxs] ]
    assert len(calparamlist) == len(SWEEP_CALPARAM_FIELDS), "mismatch in length of cal parameters and available fields"

    calparams = {k: v for k,v in zip( SWEEP_CALPARAM_FIELDS, calparamlist) }

    return  calparams, (didf + 1j*dqdf)

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
