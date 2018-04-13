import os, sys, time
import numpy as np
import pygetdata as gd

from configuration import filesys_config, roach_config
# packets coming from the Roach will contain a bunch of info (the content will possibly will be changed
# in future firmaware updates). but will contain at least packet_count, time, I and Q data for 1024 channels

# note that dirfiles can be encoded using a compression library - specify in the format file

# want to save a copy of the tone list that is currently written to the roach in the dirfile
# -> have a symlink to the last written tonelist for each roach. This information will be available in the daemon version of this
# for this code, it doesn't care, and just writes the full packet to disk, regardless of how many tones are written.

def gen_fake_roach_packet(testpacket = True):
    # want time, packet count, data
    NTONES=1021
    if testpacket:
        testpacketfile = os.path.join("testing", "20180324_testpacket")
        assert os.path.exists(testpacketfile)
        with open(testpacketfile) as fh:
            return fh.read()

    else:
        x = np.random.randint(1000, size = NTONES)
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

def create_format_file(filename, NTONES=1021):
    # include dervied fields, constants, sweeps, metadata...etc
    if not os.path.exists(filename):
        dirf = gd.dirfile(filename, gd.CREAT|gd.RDWR|gd.UNENCODED) # add GD_EXCL to stop accidental overwriting

        # if dirf is None - file exists...

        # currently:
        # headerlen = 0-42 bytes
        # iqdata:
        # 1 - 512: Channels 0 - 512, I values
        # 513 - 1024: Channels 0 - 512, Q values
        # 1025 - 1536: Channels 513 - 1024, I values
        # 1537 - 2048: Channels 513 - 1024, Q values
        # each i,q data point is 4 bytes -> 8 bytes for each datachannel

        # additional information contained in the packet
        # TODO add metadata specification for descirption of each field
        # TODO currently I can't reopen a file without recreating it. I think we need to write format file appropriately

        dirf.add_spec('PACKETCOUNT' +  ' RAW UINT32 1') # Initialized to 0 with 'GbE_pps_start'
        dirf.add_spec('COARSETIME'  +  ' RAW UINT32 1') # The number of PPS pulses elapsed since 'pps_start'
        dirf.add_spec('FINETIME'    +  ' RAW UINT32 1') # Clock cycles elapsed since last PPS pulse
        dirf.add_spec('CHECKSUM'    +  ' RAW UINT32 1') # Currently a constant placeholder, 42 (in progress)
        dirf.add_spec('PACKETINFO'  +  ' RAW UINT32 1') # Register for arbitrary info to be saved into udp packet before transmission.

        # TODO add derived fields for amp, phase, df

        # Add files for on resonance tones
        kidlist = ["K{kidnum:04d} RAW COMPLEX128 1".format(kidnum=i) for i in range(NTONES)]

        l = map(dirf.add_spec, kidlist)
        print dirf
        #dirf.close()
        return dirf

# dataidxs = np.hstack((np.arange(NTONES/2), \
#                         512 + np.arange(NTONES/2), \
#                         1024 + np.arange(NTONES/2), \
#                         1536 + np.arange(NTONES/2)))
#
#
# ilow, qlow, ihi, qhi = data[dataidxs]

def parse_packet_data(rawpacketdata, NTONES):
    """
    Convienience function to parse the packet data.

    Pass the packet (excluding header TODO handle the header eventually) and return the complex i and q data, along with any auxillary data contained
    in the packet.

    TODO:
        - speed function up. Currently 170 us to run -> should be able to reduce this by > x2
    """

    # Convert raw packet data into array. Handles multiple packets in list/array
    # Convert the auxillary data contained in the packet. AS: "should be unpacked as BIG-endian, unsigned"
    numauxbtyes = 5 # number of auxillary 4-byte numbers from the end of the packet - this should be read from .cfg file

    rawiqdata = []
    auxdata   = []

    rawpacketdata = [rawpacketdata] if isinstance(rawpacketdata, str) else rawpacketdata

    for packet in rawpacketdata:
        assert len(packet) == 8192
        rawiqdata.append( np.fromstring(packet, dtype = '<i4').astype('float64') )
        auxdata.append(   np.fromstring(packet, dtype = '>u4')[-numauxbtyes:]    )

    rawiqdata = np.atleast_2d(rawiqdata); auxdata = np.array(auxdata)

    chidxs = np.arange(NTONES)
    odd_chan = chidxs[1::2]
    even_chan = chidxs[0::2]

    ioddidx  = 1024 + ( (odd_chan - 1) /2)
    qoddidx  = 1536 + ( (odd_chan - 1) /2)
    ievenidx = 0    + ( even_chan /2 )
    qevenidx = 512  + ( even_chan /2 )

    ieven, qeven = rawiqdata[:, np.vstack((ievenidx, qevenidx))].swapaxes(0,1)
    iodd,  qodd  = rawiqdata[:, np.vstack((ioddidx, qoddidx))].swapaxes(0,1)

    evenshape = ieven.shape; oddshape = iodd.shape
    assert evenshape[0] == oddshape[0]

    zdata = np.empty((evenshape[0], evenshape[1] + oddshape[1]), dtype=np.complex128)
    zdata[:, 0::2] = ieven + 1j * qeven
    zdata[:, 1::2] = iodd  + 1j * qodd

    return auxdata, zdata

    # this should be in a dictionary, or keyed object to ensure that the data is written correctly
    #for k, v in zip(dirf.field_list(gd.RAW_ENTRY), )

#
# addinfokeys = ["CHECKSUM", "COARSETIME", "FINETIME", "PACKETCOUNT", "PACKETINFO"]
# addinfodict = dict.fromkeys(addinfokeys)
#
# [x for x in addinfodict.itervalues()]
#
# addinfodict = {k:v for k,v in zip(addinfokeys, \
#                                 np.array([np.fromstring(packet, dtype = '>u4')[-5:] \
#                                         for packet in np.atleast_1d(rawpacketdata)]).T) \
#                                         }

# need a dictionary or mapping to go from tonelist, which contains labels and indexes of data, to
# roach tones will be in order of frequency

#
# def append_data_to_dirfile(dirf, datatowrite):
#     """Function to act as the consumer, that will be given a 2d array of data
#     comprising multiple packets, and will write the data to disk.
#     """
#     # ensure that datatowrite has the correct shape. It should be a 2d array with iq data for each tone to write and number
#     # of packets, to write multiple packets at once
#     assert type(datatowrite) in [np.array, list]
#     datatowrite = np.array(datatowrite)
#
#     # need to figure ensure a mapping from roach tone order, to tonelist order
#
#
#     if datatowrite.shape[0] > 0:
#         print "Read {numpackets} packets from queue".format(numpackets = datatowrite.shape[0])
#         print dirf.nentries(type = gd.RAW_ENTRY), datatowrite.shape[-1]
#         assert dirf.nentries(type = gd.RAW_ENTRY) == ancdatatowrite.shape[-1] + iqdatatowrite.shape[-1] # ensures that the data shape matches the dirfile fields
#
#         #currentsize = dirf.tell('ctime')
#         currentsize = dirf.eof('PACKETCOUNT')
#         print currentsize
#
#         # loop over the field names and add the data to the corresponding field name
#         fieldlist = dirf.field_list(gd.RAW_ENTRY)
#
#
#         # this should be more robust, and use the fieldname to index the field in the array/dictionary
#         for fieldname, data in zip( dirf.field_list(gd.RAW_ENTRY) , np.hstack(iqdatatowrite, ancdatatowrite).T ): # loop over resonators
#             dirf.putdata(fieldname, np.ascontiguousarray( data ), first_sample = currentsize)
#
#         print 'syncing'
#         dirf.flush()
#         print 'datawritten succesfully'
#     else:
#         pass


def append_to_dirfile(dirf, queue, NTONES, maxchunksize=1000):
    """Function to act as the consumer, that will be given a 2d array of data
    comprising multiple packets, and will write the data to disk.
    """
    # choose how many samples to read from the queue - ideally this will be the entire queue
    while True:
        sizetoread = min( len(queue), maxchunksize )
        if sizetoread > 0:
        # currently not handling if queue is empty
            datafromqueue = [queue.pop() for i in range(sizetoread)] # could use numpy array with void to stop numpy stripping zeros from strings

            ancdatatowrite, iqdatatowrite = parse_packet_data(datafromqueue, NTONES)

            if ancdatatowrite.shape[0] > 0:
                print "Read {numpackets} packets from queue".format(numpackets = ancdatatowrite.shape[0])
                print dirf.nentries(type = gd.RAW_ENTRY), ancdatatowrite.shape[-1]
                assert dirf.nentries(type = gd.RAW_ENTRY) == ancdatatowrite.shape[-1] + iqdatatowrite.shape[-1]# ensures that the data shape matches the dirfile fields

                #currentsize = dirf.tell('ctime')
                currentsize = dirf.eof('PACKETCOUNT')
                print currentsize

                # loop over the field names and add the data to the corresponding field name

                for fieldname, data in zip( dirf.field_list(gd.RAW_ENTRY), np.hstack((iqdatatowrite, ancdatatowrite)).T ): # loop over resonators
                    dirf.putdata(fieldname, np.ascontiguousarray( data ), first_sample = currentsize)

                print 'syncing'
                dirf.flush()
                print 'datawritten succesfully'
            else:
                pass
        else:
            print "Queue empty"
            time.sleep(0.1)
    #--------------------------------------------------------------------------------

import funcs_network
import threading
from collections import deque

# NOT USED #
bindaddress = 'x.x.x.x'
bindport = 1234
buffer_size = 8234 # int * length of roach packet

if __name__ == '__main__':
#if False:

    # generate dirfile
    NTONES = 1021
    filename = os.path.join('testing', 'run', '20180413_testdatawrite_dirfile')
    dirf = create_format_file(filename, NTONES)
    #dirf = gd.dirfile(filename, gd.CREAT|gd.RDWR|gd.UNENCODED) # add GD_EXCL to stop accidental overwriting

    # configure socket
    #s = funcs_network.generate_socket()
    #funcs_network.configure_socket_and_bind(s, bindaddress, bindport, buffer_size)

    # create multi-threaded queue
    dq = deque()
    filewritethread = threading.Thread(name = 'writer_thread', target = append_to_dirfile, args=(dirf, dq, NTONES, ) )
    filewritethread.setDaemon(True) # setting daemon here ensures that the child thread ends with the main thread

    filewritethread.start()

    try:
        cnt = 0
        while True:

            time.sleep(1)
            #fakedata = gen_fake_roach_packet(ntones)

            # read data from socket
            #packet = s.recv(8192)
            #data = np.fromstring(packet,dtype = '<i').astype('float64')

            packet = gen_fake_roach_packet()
            data = packet[42:]
            print "sending data to queue"
            dq.appendleft(data)

    except KeyboardInterrupt:

        print 'closing'
        dirf.close()
        print 'dirfile closed'
        sys.exit(0)



# configure socket

# ---- Code graveyard ----

# TODO need to change this for the correct data organisation
# dataidxs = np.vstack((np.arange(ntones + nblinds), \
#                         512 + np.arange(ntones + nblinds), \
#                         1024 + np.arange(ntones + nblinds), \
#                         1536 + np.arange(ntones + nblinds)))
