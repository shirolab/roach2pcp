import numpy as np
import os
import time,sys
import netCDF4 as nc

# packets coming from the Roach will contain a bunch of info (possibly will be changed
# in future firmaware updates). but will contain at least packet_count, time, I and Q data for 1024 channels

# to test whether netcdf4 file is viable, write fake data to a file continuously at ~ 500 Hz,
# and see if it handles it. Additionally, try to open the file while wiriting. Lastly, try to open in KST

# genrate fake data

def gen_fake_roach_packet(ndata):
    # want time, packet count, data
    return time.time(), np.random.randint(1000, size=ndata)


# now to read while writing?
# testing appending in real time
filename = os.path.join('run', 'testdatawrite_kidsasvars.nc')

ntones = 1024

rootgrp = nc.Dataset(filename, "w", format="NETCDF3_64BIT_OFFSET")
rootgrp.createDimension("time", None)
rootgrp.createDimension("ntones", ntones)

#**`createVariable(self, varname, datatype, dimensions=(), zlib=False,
#  complevel=4, shuffle=True, fletcher32=False, contiguous=False, chunksizes=None,
#  endian='native', least_significant_digit=None, fill_value=None)`**

rootgrp.createVariable( varname = "timestamps" ,\
                        datatype = np.dtype(np.float).char ,\
                        dimensions = ("time",) )

rootgrp.createVariable( varname = "iqdata" ,\
                        datatype = np.dtype(np.float).char ,\
                        dimensions = ("time", "ntones") )

# Write a version that instead of creating single variable for all I and Q data,
# have individual dimension for each resonator. Need to test impact on timing

# kidlist = ['KID{kidnum:04d}'.format(kidnum=i) for i in range(ntones)]
#
# for kid in kidlist:
#     rootgrp.createVariable( varname = kid ,\
#                             datatype = np.dtype(np.float).char ,\
#                             dimensions = ("time",) ) # add 2 here to write I and Q for each detector

rootgrp.description = "example script"
rootgrp.history = "Created " + time.ctime(time.time())

rootgrp.close()

def test_write_to_nc(f, lenbuffer, dataset):
    """Given an open netcdf file handle, write dummy data to file for performance checking.
    For this test function, lenbuffer is equivalent to the number of packets in the buffer.
    dataset is a dummy packet with timestamp, and iqdata. """

    # currently this is inefficient, modify to save the full chunk instead of single value
    # to reduce the looping overhead.

    # the input data should be in a 2d numpy array
    datatowrite = np.repeat(dataset[np.newaxis,:], lenbuffer, axis=0)

    assert len(rootgrp.variables) == datatowrite.shape[-1]

    currentsize = rootgrp.dimensions['time'].size
    #print currentsize
    for kid, datachunk in zip(f.variables.itervalues(), datatowrite.T): # loop over resonators

        kid[currentsize:] = datachunk  # write the packet.
        # Note that currently, all variables are the same size as the time dimension, which is updated first

    #print "syncing"
    f.sync() # finally sync the data to file


if __name__ == '__main__':

    try:
        with nc.Dataset(filename, 'a') as f:
        #with open('simple.txt', 'a') as f:
            print f.isopen()
            cnt = 0
            chunksize = 25
            timevar = f.variables['timestamps']
            #datavar = f.variables['iqdata']

            while True:

                time.sleep(0.1)
                fakedata = gen_fake_roach_packet(ntones)
                print cnt, fakedata

                #timevar[cnt], datavar[cnt, :] = fakedata
                timevar[cnt] = fakedata[0]

                for idx, kid in enumerate(f.variables.values()[1:]): # skip over time dimension
                    kid[cnt] = fakedata[1][idx]

                if np.mod(cnt, chunksize)==0:
                    print "syncing"
                    f.sync()

                #f.write("%.3f\n"%gen_fake_roach_packet()[0]); f.flush()
                cnt=cnt+1 # this c/should be done more elegantly

    except KeyboardInterrupt:

        print 'closing'
        sys.exit(0)

# want to time sync() call





#https://docs.scipy.org/doc/scipy-0.15.1/reference/generated/scipy.io.netcdf.netcdf_file.html
#from scipy.io import netcdf
#import signal
# f = netcdf.netcdf_file('simple.nc', 'w', version=2)
#
# f.history = 'Created for a test'
# f.createDimension('time', None)
# tnow = f.createVariable('time', 'f', ('time',))
# tnow.units = 'days since 2008-01-01'
# tnow[:] = np.arange(10)
# f.close()
