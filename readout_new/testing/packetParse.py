import numpy as np
import socket as sock
import sys

if __name__ == "__main__":
    fname = 'packet'
    header_len = 42
    data_len = 8192

    with open(fname,'r') as myfile:
        #packet saved through wireshark has some extra stuff to get rid of 
        wpacket = myfile.read()
        
    
    spacket = wpacket.split('\n')
    dspacket = [ll.split() for ll in spacket]
    #remove first and last element of each line, the first is a byte count of the first byte in the line, idk what last is
    #this is a remnant from wireshark, not true packet info
    packet_1 = [jj[1:-1] for jj in dspacket]
    #now rejoin 
    packet_2 = [' '.join(pp) for pp in packet_1]
    packet = ' '.join(packet_2)
    
    
    


    # '<i' means little endian signed integer
    # '>I' means big endian unsigned integer;
    # B = unsigned byte, H = unsigned short
    data = np.fromstring(packet[42:], dtype = '<i').astype('float')
    print data
    print len(data), 'len data'

    header = packet[:header_len]


    
    #udp source ip address
    saddr = np.fromstring(header[26:30], dtype = "<I")
    saddr = sock.inet_ntoa(saddr) # source addr
    #udp destination ip address
    daddr = np.fromstring(header[30:34], dtype = "<I")
    daddr = sock.inet_ntoa(daddr) # dest addr
    #source mac address
    smac = np.fromstring(header[6:12], dtype = "<B")
    #destination mac address
    dmac = np.fromstring(header[:6], dtype = "<B")
    #source port
    src = np.fromstring(header[34:36], dtype = ">H")[0]
    #destination port
    dst = np.fromstring(header[36:38], dtype = ">H")[0]



    ### PACKET DATA PARSE ###
    roach_checksum = (np.fromstring(packet[-21:-17],dtype = '>I'))
    # seconds elapsed since 'pps_start'
    sec_ts = (np.fromstring(packet[-17:-13],dtype = '>I'))
    # milliseconds since PPS
    clockcycles = (np.fromstring(packet[-13:-9],dtype = '>I').astype('float'))
    fine_ts = np.round((clockcycles/256.0e6)*1.0e3,3)
    # raw packet count since 'pps_start'
    packet_count = (np.fromstring(packet[-9:-5],dtype = '>I')) 
    packet_info_reg = (np.fromstring(packet[-5:-1],dtype = '>I'))
    gpio_reg = (np.fromstring(packet[-1:],dtype = '>I'))


    print "src MAC = %x:%x:%x:%x:%x:%x" % struct.unpack("BBBBBB", smac)
    print "dst MAC = %x:%x:%x:%x:%x:%x" % struct.unpack("BBBBBB", dmac)
    print "src IP : src port =", saddr,":", src
    print "dst IP : dst port  =", daddr,":", dst
    print "Roach chksum =", roach_checksum[0]
    print "PPS count since last 'pps_start' =", sec_ts[0]
    print "Clock cycles since pps_start =", fine_ts[0]
    print "Packet count =", packet_count[0]
    print "Packet info reg =", packet_info_reg[0]
    print "GPIO reg =", gpio_reg[0]




    
