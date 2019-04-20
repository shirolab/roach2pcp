#!/usr/bin/env python

# any code related to KID/resonator functions should be included here


def find_f0_from_sweep(freq, i, q, method="maxspeed", **kwargs):

    """
    Given arrays of frequency, I and Q, find the resonant frequency using the speicfied method.

    Arrays of I and Q can be 2D, but the length of the last dimension should be equal ot the length of freqs
    Available kwargs:

    filter_dict : a set of filter parameters to be used to filter the data before finding. Format
        is k,v where v is a list-like containing a filter function and any args to go along with that filter


    """

    assert method in ["maxspeed", "mins21"], "invalid method given {0}".format(method)

    assert i.shape[-1] == q.shape[-1] == freq.shape[0]

    # convert to at least 2d to vectorise processing for multiple resonators at once
    i,q = np.atleast_2d(i,q)

    ### parse kwargs ###

    # filter dict
    filter_dict = ( kwargs.pop("filter_dict", {"filter": []}) )

    if method == "mins21":
        return freq[ np.argmin(np.sqrt(i**2 + q**2), axis = 1) ]

    elif method == "maxspeed":
        di = np.gradient(i, axis = 1)
        dq = np.gradient(q, axis = 1)
        return freq[ np.argmax( np.sqrt(di**2 + dq**2), axis = 1) ]
