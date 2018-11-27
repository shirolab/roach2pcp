#!

# functions to handle and parse the datapackets
# most of this code is taken from Sam Gordons kidpy module https://github.com/sbg2133/kidPy

import os, sys, socket, time, string, struct # stdlib imports
from random import choice
import numpy as np
import pygetdata as _gd

from .. import configuration as configuration; reload(configuration)

# read in relevant config files

from ..configuration import roach_config

# parse configuration input to get slice objects and list for data

ntones        = configuration.roach_config["packet_structure"]["ntones"]
#ntones = 7 # for testing
header_len     = configuration.roach_config["packet_structure"]["header_len"]
aux_field_cfg = configuration.roach_config["packet_structure"]["aux_field_cfg"]
kid_field_cfg = configuration.roach_config["packet_structure"]["kid_field_cfg"]

kidentry_type       = kid_field_cfg["entry_type"]
kid_field_datatype  = kid_field_cfg["field_datatype"]
kid_datatype        = kid_field_cfg["datatype"]

kid_fields_Ieven = {"K{kidnum:04d}_I".format(kidnum=i): [kidentry_type, kid_field_datatype, (i/2), (i/2+4), None, kid_datatype] for i in range(ntones)[::2]}
kid_fields_Qeven = {"K{kidnum:04d}_Q".format(kidnum=i): [kidentry_type, kid_field_datatype, (512 + i/2), (512+i/2 + 4), None, kid_datatype] for i in range(ntones)[::2]}

kid_fields_Iodd = {"K{kidnum:04d}_I".format(kidnum=i): [kidentry_type, kid_field_datatype, (1024 + i/2), (1024+i/2 + 4), None, kid_datatype] for i in range(ntones)[1::2]}
kid_fields_Qodd = {"K{kidnum:04d}_Q".format(kidnum=i): [kidentry_type, kid_field_datatype, (1536 + i/2), (1536+i/2 + 4), None, kid_datatype] for i in range(ntones)[1::2]}

# concatenate all the dicts together to make a master kid_field list that contains the correct slicing information
kid_fields = reduce(lambda x,y: dict(x, **y), (kid_fields_Ieven, kid_fields_Qeven, kid_fields_Iodd, kid_fields_Qodd))

# construct a dictionary that contains the dirfile field names as keys, and values comprise [slice object, data_container]
# can either use single fields for kids using single slice object, or sort into ordered list (but, dictionary isn't ordered)

datapacket_dict = {}
for field_name, (entry_type, field_datatype, startidx, stopidx, stepidx, datatype) in aux_field_cfg.items() + kid_fields.items():
    datapacket_dict.update( {field_name:[str(entry_type), str(field_datatype), datatype, slice(startidx,stopidx,stepidx), []] } )

# now parse the data and put it into this structure !

def parse_datapacket_dict(packets):
    # handle both single and multiple packets
    packets = packets if isinstance(packets, list) else [packets] # fast way to ensure input is a list

    for packet in packets:
        assert len(packet) == 2 and type(packet) == tuple
        packet, python_time = packet

        for field_name, item in datapacket_dict.items():
            data = np.frombuffer( packet[header_len:][item[-2]], dtype = item[2] )
            item[-1].append( data ) if data.size > 0 else None
            #item[-1].append( struct.unpack( item[2], packet[header_len:][item[-2]] ) )

        # write python_timestamp and raw_packet manually
        datapacket_dict["raw_packet"][-1].append(packet)
        datapacket_dict["python_timestamp"][-1].append(python_time)
        print python_time
    return datapacket_dict


def parse_datapacket(rawpacket):
    """Parses packet data, filters reception based on source IP outputs:
    packet: The original data packet
       float data: Array of channel data
       header: String packed IP/ETH header
       saddr: The packet source address"""

    if not rawpacket:
        print "Non-Roach packet received"
        return
    data = np.fromstring(rawpacket[header_len:], dtype = '<i').astype('float')
    ### Parse Header ###
    header = rawpacket[:header_len]
    saddr = np.fromstring(header[26:30], dtype = "<I")
    saddr = socket.inet_ntoa(saddr) # source addr
    daddr = np.fromstring(header[30:34], dtype = "<I")
    daddr = socket.inet_ntoa(daddr) # dest addr
    smac = np.fromstring(header[6:12], dtype = "<B")
    dmac = np.fromstring(header[:6], dtype = "<B")
    src = np.fromstring(header[34:36], dtype = ">H")[0]
    dst = np.fromstring(header[36:38], dtype = ">H")[0]
    ### Parse packet data ###
    roach_checksum = (np.fromstring(rawpacket[-21:-17],dtype = '>I'))
    # seconds elapsed since 'pps_start'
    sec_ts = (np.fromstring(rawpacket[-17:-13],dtype = '>I'))
    # milliseconds since PPS
    fine_ts = np.round((np.fromstring(rawpacket[-13:-9],dtype = '>I').astype('float')/256.0e6)*1.0e3,3)
    # raw packet count since 'pps_start'
    packet_count = (np.fromstring(rawpacket[-9:-5],dtype = '>I'))
    packet_info_reg = (np.fromstring(rawpacket[-5:-1],dtype = '>I'))
    gpio_reg = (np.fromstring(rawpacket[-1:],dtype = np.uint8))
    #print gpio_reg
        ### Filter on source IP ###
    #if (saddr != self.nc['udp_source_ip']):
    #    print "Non-Roach packet received"
    #    return
    return rawpacket, data, header, saddr, daddr, smac, dmac, src, dst, roach_checksum, sec_ts, fine_ts, packet_count, packet_info_reg, gpio_reg


# ---- Function for generating fake roach packet - for testing purposes only

# get packet from saved example packet
TESTPACKETFILE = os.path.abspath( os.path.join (os.path.dirname(__file__), os.pardir, "testing/20180324_testpacket") )
print TESTPACKETFILE
assert os.path.exists(TESTPACKETFILE)
# read packet and store
with open (TESTPACKETFILE) as fin:
    TESTPACKET = fin.read()

def gen_fake_roach_packet(use_test_packet = False):
    ROACHUDPADDR = "192.168.40.1" # this mimics the source address contained in the packet, used to filter received packets

    HDRLEN = 42
    NTONES = 1000 # i think with timestamps, there are acutally only 1023 tones
    DATALEN = NTONES * 4 * 2 # in bytes = 1024 4 byte (32 bit) i,q numbers
    PACKETLEN =  DATALEN + HDRLEN

    #print PACKETLEN
    if use_test_packet == True:
        return TESTPACKET
        # add noise to packet?

    else:
        hdr = "".join(choice(string.lowercase) for i in range(HDRLEN)) # generate random header with length 42
        hdr = hdr[:26] + socket.inet_aton(ROACHUDPADDR) + hdr[30:] # insert the source address at the correct position

        data = np.random.randint(1000, size = 2*NTONES).astype(np.int32)
        # i am presuming the ntp timestamp has two 32bit ints one for sec, other for sub second accuracy
        # timestamp in real packets might be at the end? possibly 4 bytes? TODO Confirm this with SG
        data[-5:] = (np.int32(4200), np.int32(12345), np.int32(54321), np.int32(321), np.int32(time.time() )) #(chksum, cts, fts, cnt, pinfo)
        packet = hdr + data.tostring() # convert data to bytes and join to finalise packet
        return packet


# ================================================================================================================
# ================================================ Code graveyard ================================================
# ================================================================================================================
#class roachdatapacket(object):

# def parse_datapacket(datapacket, numchannels=1021, headerlen = 42, timinglen = 20, out=None):
#     """
#     parse_datapacket(packet, numchannels = 1021, header = 42[, out])
#
#     Parses packet data into header, I and Q. Assumes that a check for validity has been performed beforehand.
#
#     Not implemented: If out is given and is an array, then the value is appended to the end of out.
#
#     Parameters
#     ----------
#     datapacket : roachpacket
#         Input datapacket
#
#     numchannels : int
#         Number of channels to read. As of Feb 2018, the maxmimum is currently 1021.
#
#     headerlen : int
#         Length of the datapacket header
#
#     timinglen : int
#         Length of the timing information in bytes. Assumed to be at the end of the file
#
#     Returns
#     -------
#
#     Example
#     --------
#
#
#     """
#     # scale factor to convert i and q to volts?
#     #scale_factor = 2.0**17 / (self.accum_len/512.)
#
#     header = datapacket[:headerlen]
#     data = np.fromstring(datapacket[headerlen:], dtype = '<i').astype('float')
#
#     # check that the number of channels requested fits in the packet, otherwise coerce
#     #assert numchannels <
#
#     # coerce the number of channels to ensure the correct maximum number of channels
#     numchannels = numchannels if numchannels < MAXCHANNELS else MAXCHANNELS
#
#     lenchannels = np.arange(numchannels)
#
#     # extract i and q data
#     iodd = data[1024 + ((lenchannels[1::2] - 1) / 2)]      # 1024 - 1535: Channels 513 - 1024, I values
#     qodd = data[1536 + ((lenchannels[1::2] - 1) /2)]       # 1536 - 2047: Channels 513 - 1024, Q values
#     ieven = data[0 + (lenchannels[0::2]/2)]                # 000 - 511: Channels 0 - 512, I even values
#     qeven = data[512 + (lenchannels[0::2]/2)]              # 512 - 1023: Channels 0 - 512, Q values
#
#     # extract timing - which is currently the last 20 bytes or, (20 bytes) / (4. bytes/value) = 5 values of the packet
#     timinginfo = data[-int(timinglen/4):]
#
#     # interleave the even and odd arrays for both i and q.
#     # This method appears to be quickest https://stackoverflow.com/questions/5347065/interweaving-two-numpy-arrays
#     iall = np.empty((ieven.size + iodd.size,), dtype=ieven.dtype)
#     iall[0::2] = ieven; iall[1::2] = iodd
#
#     qall = np.empty((qeven.size + qodd.size,), dtype=qeven.dtype)
#     qall[0::2] = qeven; qall[1::2] = qodd
#
#     return header, iall, qall, timinginfo


# lenchannels = np.arange(ntones)
#
# # extract i and q data
#
# testarray = np.arange(2048)
#
# idxiodd = 1024 + ((lenchannels[1::2] - 1) / 2)
# iodd = slice(1024, 1024 + int(np.ceil((ntones-1)/2.)))      # 1024 - 1535: Channels 513 - 1024, I values
# print all(testarray[idxiodd] == testarray[iodd])
#
# idxqodd = 1536 + ((lenchannels[1::2] - 1) /2)
# qodd = slice(1536, 1536 + int(np.ceil((ntones-1)/2.)))      # 1024 - 1535: Channels 513 - 1024, I values
# print all(testarray[idxqodd] == testarray[qodd])
#
# idxieven = 0 + (lenchannels[0::2]/2)
# ieven = slice(0, int(np.ceil((ntones)/2.)))
# print all(testarray[idxieven] == testarray[ieven])
#
# idxqeven = 512 + (lenchannels[0::2]/2)
# qeven = slice(512, 512 + int(np.ceil((ntones)/2.)))
# print all(testarray[idxqeven] == testarray[qeven])
#
