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
        return dirf

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

import funcs_network
from threading import Thread
from collections import deque

bindaddress = 'x.x.x.x'
bindport = 1234
buffer_size = 8234 # int * length of roach packet

if __name__ == '__main__':
    # generate dirfile
    ntones = 1024
    filename = os.path.join('run', 'testdatawrite_dirfile')
    dirf = create_format_file(filename, ntones)
    dirf = gd.dirfile(filename, gd.CREAT|gd.RDWR|gd.UNENCODED) # add GD_EXCL to stop accidental overwriting

    # configure socket
    s = funcs_network.generate_socket()
    funcs_network.configure_socket_and_bind(s, bindaddress, bindport, buffer_size)

    # create multi-threaded queue
    dq = deque()
    filewritethread = threading.Thread(name = 'writer_thread', target = append_to_dirfile, args=(dirf, dq,) )
    filewritethread.setDaemon(True) # setting daemon here ensures that the child thread ends with the main thread

    filewritethread.start()

    try:
        cnt = 0
        while True:

            time.sleep(0.001)
            #fakedata = gen_fake_roach_packet(ntones)

            # read data from socket
            packet = s.recv(8192)
            data = np.fromstring(packet,dtype = '<i').astype('float64')

            print "sending data to queue"
            dq.appendleft(data)

    except KeyboardInterrupt:

        print 'closing'
        dirf.close()
        print 'dirfile closed'
        sys.exit(0)



# configure socket
