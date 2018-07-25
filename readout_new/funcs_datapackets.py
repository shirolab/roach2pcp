#!

# functions to handle and parse the datapackets
# most of this code is taken from Sam Gordons kidpy module https://github.com/sbg2133/kidPy

import sys, socket, time, string, struct # stdlib imports
from random import choice
import numpy as np

import configuration; reload(configuration)

# read in relevant config files
from configuration import roach_config
MAXCHANNELS = roach_config.config["MAXCHANNELS"]


def parsePacketData_fullpacket(rawpacket, header_len=42):
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




def parse_datapacket(datapacket, numchannels=1021, headerlen = 42, timinglen = 20, out=None):
    """
    parse_datapacket(packet, numchannels = 1021, header = 42[, out])

    Parses packet data into header, I and Q. Assumes that a check for validity has been performed beforehand.

    Not implemented: If out is given and is an array, then the value is appended to the end of out.

    Parameters
    ----------
    datapacket : roachpacket
        Input datapacket

    numchannels : int
        Number of channels to read. As of Feb 2018, the maxmimum is currently 1021.

    headerlen : int
        Length of the datapacket header

    timinglen : int
        Length of the timing information in bytes. Assumed to be at the end of the file

    Returns
    -------

    Example
    --------


    """
    # scale factor to convert i and q to volts?
    #scale_factor = 2.0**17 / (self.accum_len/512.)

    header = datapacket[:headerlen]
    data = np.fromstring(datapacket[headerlen:], dtype = '<i').astype('float')

    # check that the number of channels requested fits in the packet, otherwise coerce
    #assert numchannels <

    # coerce the number of channels to ensure the correct maximum number of channels
    numchannels = numchannels if numchannels < MAXCHANNELS else MAXCHANNELS

    lenchannels = np.arange(numchannels)

    # extract i and q data
    iodd = data[1024 + ((lenchannels[1::2] - 1) / 2)]      # 1024 - 1535: Channels 513 - 1024, I values
    qodd = data[1536 + ((lenchannels[1::2] - 1) /2)]       # 1536 - 2047: Channels 513 - 1024, Q values
    ieven = data[0 + (lenchannels[0::2]/2)]                # 000 - 511: Channels 0 - 512, I even values
    qeven = data[512 + (lenchannels[0::2]/2)]              # 512 - 1023: Channels 0 - 512, Q values

    # extract timing - which is currently the last 20 bytes or, (20 bytes) / (4. bytes/value) = 5 values of the packet
    timinginfo = data[-int(timinglen/4):]

    # interleave the even and odd arrays for both i and q.
    # This method appears to be quickest https://stackoverflow.com/questions/5347065/interweaving-two-numpy-arrays
    iall = np.empty((ieven.size + iodd.size,), dtype=ieven.dtype)
    iall[0::2] = ieven; iall[1::2] = iodd

    qall = np.empty((qeven.size + qodd.size,), dtype=qeven.dtype)
    qall[0::2] = qeven; qall[1::2] = qodd

    return header, iall, qall, timinginfo


# ---- Function for generating fake roach packet - for testing purposes only
def gen_fake_roach_packet():
    ROACHUDPADDR = "192.168.40.1" # this mimics the source address contained in the packet, used to filter received packets

    HDRLEN = 42
    NTONES = 1024 # i think with timestamps, there are acutally only 1023 tones
    DATALEN = NTONES * 4 * 2 # in bytes = 1024 4 byte (32 bit) i,q numbers
    PACKETLEN =  DATALEN + HDRLEN

    print PACKETLEN

    hdr = "".join(choice(string.lowercase) for i in range(HDRLEN)) # generate random header with length 42
    hdr = hdr[:26] + socket.inet_aton(ROACHUDPADDR) + hdr[30:] # insert the source address at the correct position

    data = np.random.randint(1000, size = 2*NTONES).astype(np.int32)
    # i am presuming the ntp timestamp has two 32bit ints one for sec, other for sub second accuracy
    # timestamp in real packets might be at the end? possibly 4 bytes? TODO Confirm this with SG
    data[-5:] = (np.int32(4200), np.int32(12345), np.int32(54321), np.int32(321), np.int32(time.time() )) #(chksum, cts, fts, cnt, pinfo)
    packet = hdr + data.tostring() # convert data to bytes and join to finalise packet
    return packet
