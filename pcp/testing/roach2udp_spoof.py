#!/usr/bin/env python
# 20171230 - PB

# This file is a script that mimics the Roach2 UDP packets and send dummy roach packets
# to a network.
# configure a socket server and send to ip address

import sys, socket, time, string, struct # stdlib imports
from random import choice
import numpy as np
import pcp; from pcp.lib import lib_datapackets

SERVERPORT = 12345 # server port does not appear to be used in SG's code
DESTADDR = "localhost"
DESTPORT = 12348

ROACHUDPADDR = "192.168.40.1" # this mimics the source address contained in the packet, used to filter received packets
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# packet lengths (will eventually be read from a configuraiton file)
HDRLEN = 42
NTONES = 1024 # i think with timestamps, there are acutally only 1023 tones
DATALEN = NTONES * 4 * 2 # in bytes = 1024 4 byte (32 bit) i,q numbers
PACKETLEN =  DATALEN + HDRLEN

print PACKETLEN

try:
    while True:
        time.sleep(1)

        print "Sending packet to {ip} at port {port}".format(ip=DESTADDR, port=DESTPORT)

        packet = pcp.lib.lib_datapackets.gen_fake_roach_packet(use_test_packet=True)

        s = server_socket.sendto(packet, (DESTADDR, DESTPORT))

        print s

except KeyboardInterrupt:
    print "Exiting..."
    #sys.exit(0)


# Notes

# SG packet handling code follows as:
# - configures raw socket in main script with "s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))""
# - passes this socket to GbEconfig
# - configures socket options to set SO_RCVBUF length
# - binds to interface (read from config file)
# - then when running, write to the FPGA to start packet sending (cf. gbe.configDownlink()), which is called
# during system initialistion
# - when taking data select.select(socket) and parsing the packet as required


# def parseChanData(self, chan, data):
#     if (chan % 2) > 0:
#         I = data[1024 + ((chan - 1) / 2)]
#         Q = data[1536 + ((chan - 1) /2)]
#     else:
#         I = data[0 + (chan/21)]
#         Q = data[512 + (chan/2)]
#     return I, Q, np.arctan2([Q],[I])
