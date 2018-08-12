#!/usr/bin/env python
# 20171230 - PB

# This file is a script that mimics the Roach2 UDP packets and send dummy roach packets
# to a network.
# configure a socket server and send to ip address

import sys, socket, time, string, struct # stdlib imports
from random import choice
import numpy as np

SERVERPORT = 12345 # server port does not appear to be used in SG's code
DESTADDR = "localhost"
DESTPORT = 12347

ROACHUDPADDR = "192.168.40.1" # this mimics the source address contained in the packet, used to filter received packets
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# packet lengths (will eventually be read from a configuraiton file)
HDRLEN = 42
NTONES = 1024 # i think with timestamps, there are acutally only 1023 tones
DATALEN = NTONES * 4 * 2 # in bytes = 1024 4 byte (32 bit) i,q numbers
PACKETLEN =  DATALEN + HDRLEN

print PACKETLEN

hdr = "".join(choice(string.lowercase) for i in range(HDRLEN)) # generate random header with length 42
hdr = hdr[:26] + socket.inet_aton(ROACHUDPADDR) + hdr[30:] # insert the source address at the correct position

try:
    while True:
        time.sleep(1)

        data = np.random.randint(1000, size = 1024*2).astype(np.float32)
        # i am presuming the ntp timestamp has two 32bit ints one for sec, other for sub second accuracy
        # timestamp in real packets might be at the end? possibly 4 bytes? TODO Confirm this with SG
        data[:2] = divmod(time.time(), 1)
        packet = hdr + data.tostring() # convert data to bytes and join to finalise packet

        print "Sending packet to {ip} at port {port}".format(ip=DESTADDR, port=DESTPORT)

        s = server_socket.sendto(packet, (DESTADDR, DESTPORT))
        print s
except KeyboardInterrupt:
    print "Exiting..."
    sys.exit(0)


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
