import numpy as np
import os, sys, time

import scapy.all as sp

import funcs_datapackets as dp


if __name__ == "__main__":
    # hardcode interface to capture on 
    iface = "enp3s0" #"enp0s31f6"
    # hardcode srcip address to use a filter for tshark
    srcip = '192.168.40.71'
    # allow the user to specify the number of packets to be captured using a command line arguement. 
    assert len(sys.argv) <= 2
    count = 100 if len(sys.argv) < 2 else sys.argv[-1] # set count to 100 if not specified by user
  
    # set up save directory. This assumes that we are running this from the /sscontrol/multitone/readout_new
    # all files are saved in readout_new/testing/packetTest - raises an assertionerror if this is not the case

    savedir = os.path.join(os.getcwd(), "testing", "packetTest")
    assert os.path.exists(savedir)
    packetfilename = os.path.join(savedir, time.strftime('%Y%m%d_%H%M%S',time.gmtime()) + '.pcap')
    print packetfilename

    # run wireshark
    os.system("tshark -i {iface} -w {fname} -F pcap -c {count} host {srcip}".format(iface= iface, fname = packetfilename, count = count, srcip = srcip))
    
    # read in the pcap file to get the packets into python. Returns a "list" of packets
    packets = sp.rdpcap(packetfilename)
    rawpackets = [packet.original for packet in packets]

    # process raw packets using the parsedatapacket function from funcs_datapackets
    keys = "rawpacket, data, header, saddr, daddr, smac, dmac, src, dst, roach_checksum, sec_ts, fine_ts, packet_count, packet_info_reg, gpio_reg".split(", ")

    #create a dictionary to contain all of the 
    packetdict = {key: [] for key in keys}
    for packet in rawpackets:
        for k,vals in zip(keys, dp.parsePacketData_fullpacket(packet)):
            packetdict[k].append(vals)
    

    print "{0}/{1} packets lost".format( sum( np.diff(np.array(packetdict["packet_count"]).flatten()) > 1), count)


def read_large_pcap(filename):
    myreader = sp.PcapReader(filename)
    rawpackets = []
    while True: 
        packet = myreader.read_packet()
        if packet is None:
            break
    
        rawpackets.append(packet.original)

    return rawpackets

