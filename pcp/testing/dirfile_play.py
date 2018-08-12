import pygetdata as gd
import os, datetime as dt
import numpy as np
# create dirfile

filename = os.path.join("testing", "run", "dirf_"+ dt.datetime.now().strftime("%Y%m%d"))

def create_dirfile(filename):

    dirf = gd.dirfile(filename, gd.CREAT|gd.RDWR|gd.UNENCODED) # add GD_EXCL to stop accidental overwriting

    #subdirf = gd.dirfile(os.path.join(filename, "sweep"), gd.CREAT|gd.RDWR|gd.UNENCODED)

    sweepfrag = dirf.include('sweep', flags=gd.CREAT)
    #sweepfrag = dirf.include(subdirf, flags=gd.CREAT)
    dirf.add(gd.entry(gd.CARRAY_ENTRY,'sweep_f_%04d'%(1), sweepfrag, (gd.FLOAT64,11)))
    dirf.put_carray('sweep_f_%04d'%(1), np.arange(11))

    dirf.add_spec('PACKETCOUNT' +  ' RAW UINT32 1') # Initialized to 0 with 'GbE_pps_start'

    kidlist = ["K{kidnum:04d} RAW COMPLEX128 1".format(kidnum=i) for i in range(10)]

    l = map(dirf.add_spec, kidlist)

    #dirf.close()
    return dirf
    
