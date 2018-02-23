import numpy as np
import os
import time,sys
import pygetdata as gd

# packets coming from the Roach will contain a bunch of info (the content will possibly will be changed
# in future firmaware updates). but will contain at least packet_count, time, I and Q data for 1024 channels

# note that dirfiles can be encoded using a compression library - specify in the format file

def gen_fake_roach_packet(ndata):
    # want time, packet count, data
    x = np.random.randint(1000, size = ndata + 1)
    x[0] = time.time()
    return x

def test_write_to_dirfile(dirf, lenbuffer, dataset):
    """Given an open dirfile file handle, write dummy data to file for performance checking.
    For this test function, lenbuffer is equivalent to the number of packets in the buffer.
    dataset is a dummy packet with timestamp, and iqdata. """

    # the input data should be in a 2d numpy array
    datatowrite = np.repeat(dataset[np.newaxis,:], lenbuffer, axis=0)

    assert dirf.nentries(type = gd.RAW_ENTRY) == datatowrite.shape[-1]

    #currentsize = dirf.tell('ctime')
    currentsize = dirf.eof('ctime')

    #print currentsize
    for kid, datachunk in zip(dirf.field_list(gd.RAW_ENTRY), datatowrite.T): # loop over resonators
        dirf.putdata(kid, np.ascontiguousarray(datachunk), first_sample = currentsize)

    #print "syncing"
    #dirf.sync() # finally sync the data to file. Running this with no argument flushes the entire dirfile
    #dirf.flush() # finally sync the data to file. Running this with no argument flushes the entire dirfile

# --- create a dirfile and populate the format file ---
def create_format_file(filename, ntones):
    # include dervied fields, constants, sweeps, metadata...etc
    if not os.path.exists(filename):
        dirf = gd.dirfile(filename, gd.CREAT|gd.RDWR|gd.UNENCODED) # add GD_EXCL to stop accidental overwriting

        dirf.add_spec('ctime' +  ' RAW FLOAT64 1')     # add fields (can use either add_spec or add)

        kidlist = ["KID{kidnum:04d} RAW COMPLEX128 1".format(kidnum=i) for i in range(ntones)]
        l = map(dirf.add_spec, kidlist)

        dirf.close()

def append_to_dirfile(dirf, queue, maxchunksize=1000):
    """Function to act as the consumer, that will be given a 2d array of data
    comprising multiple packets, and will write the data to disk.
    """
    # choose how many samples to read from the queue - ideally this will be the entire queue
    while True:
        sizetoread = min(len(queue), maxchunksize)

        # currently not handling if queue is empty
        datatowrite = np.array( [dq.pop() for i in range(sizetoread)] )

        if datatowrite.shape[0] > 0:
            print "Read {numpackets} packets from queue".format(numpackets = datatowrite.shape[0])
            print dirf.nentries(type = gd.RAW_ENTRY), datatowrite.shape[-1]
            assert dirf.nentries(type = gd.RAW_ENTRY) == datatowrite.shape[-1]

            #currentsize = dirf.tell('ctime')
            currentsize = dirf.eof('ctime')
            print currentsize

            for kid, kiddata in zip(dirf.field_list(gd.RAW_ENTRY), datatowrite.T): # loop over resonators
                dirf.putdata(kid, np.ascontiguousarray( kiddata ), first_sample = currentsize)

            print 'syncing'
            dirf.flush()
            print 'datawritten succesfully'
        else:
            pass
#--------------------------------------------------------------------------------

from collections import deque

filename = os.path.join('run', 'testdatawrite_dirfile')

ntones = 1024

create_format_file(filename, ntones)


if __name__ == '__main__':

    dirf = gd.dirfile(filename, gd.CREAT|gd.RDWR|gd.UNENCODED) # add GD_EXCL to avoid accidental overwriting

    dq = deque()

    from threading import Thread

    filewritethread.start()

    try:
        cnt = 0

        while True:

            time.sleep(0.001)
            fakedata = gen_fake_roach_packet(ntones)
            print "sending data to queue"
            dq.appendleft(fakedata)

    except KeyboardInterrupt:

        print 'closing'
        dirf.close()
        print 'dirfile closed'
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
