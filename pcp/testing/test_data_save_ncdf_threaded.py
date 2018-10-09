import os, sys, time, numpy as np
import netCDF4 as nc

import Queue, threading

# Dummy script to test out parallel processing (via threads) for the data saving routine to be used in
# the daemon processes. If we decide to use either dirfile, or netcdf formats that are compatible with
# KST plotting, then we need to loop over files/varibles when saving the data, which is a time expensive process.
# Therefore, to make this an efficient process, one idea is to implement a FIFO-based producer/consumer scheme where the
# main thread reads data from the socket and passes it to a FIFO queue which is consumed by a concurrent thread
# that saves the data to disk. Assuming that the file writing takes longer than the time between subsequent packets, then
# multiple data points will be in the FIFO and processed each time the consumer loop runs, resulting in an equilibrium
# (thats the idea anyway!)

# --- log of timeit tests ---

# x = np.array(range(1024))
# q = Queue.Queue()

# In [27]: %timeit [q.put(x) for i in range(1001)]
# 100 loops, best of 3: 5.59 ms per loop
#
# In [28]: %timeit [(q.get_nowait(), q.task_done()) for i in range(1001)]
# 100 loops, best of 3: 7.86 ms per loop
#
# In [31]: %timeit [(q.get(), q.task_done()) for i in range(1001)]
# 100 loops, best of 3: 7.87 ms per loop

# Alternatively use collections.deque (purports to be faster, and thread-safe)

# In [44]: %timeit [dq.append(x) for i in range(1001)]
# 1000 loops, best of 3: 343 µs per loop
#
# In [45]: %timeit [dq.pop() for i in range(1001)]
# 1000 loops, best of 3: 293 µs per loop



# ---------------------------------------------------------

def read_queue_all(queue, maxsize=1000):
    """Using the collection.deque object, """
    sizetoread = min(len(queue), maxsize) # takes a snapshot of the Queue
    # read this much data, as well as finishing task
    qdata = [dq.pop() for i in range(sizetoread)]


# define an example consumer function that will eventually save the data to disk.
def write_data(queue):
    """Function to pull data from a queue and process. """
    # want a function to get all data from a queue (doesn't exist in the queue module)


# can sub class thread to add a run() method
# https://stackoverflow.com/questions/31905255/how-to-terminate-producer-consumer-threads-from-main-thread-in-python





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

# rootgrp.createVariable( varname = "iqdata" ,\
#                         datatype = np.dtype(np.float).char ,\
#                         dimensions = ("time", "ntones") )

# Write a version that instead of creating single variable for all I and Q data,
# have individual dimension for each resonator. Need to test impact on timing

kidlist = ['KID{kidnum:04d}'.format(kidnum=i) for i in range(ntones)]

for kid in kidlist:
    rootgrp.createVariable( varname = kid ,\
                            datatype = np.dtype(np.float).char ,\
                            dimensions = ("time",) )

rootgrp.description = "example script"
rootgrp.history = "Created " + time.ctime(time.time())

rootgrp.close()


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
