#!/usr/bin/env python
# 20180105 - PB

# Script to test and confirm the capture of packets and reading from the configuraiton file

import sys, socket, time, struct, select # stdlib imports
import numpy as np


# set up socket listening on specific port
# select.select on the port
# print packet details


SERVERPORT = 12345 # server port does not appear to be used in SG's code
DESTADDR = "localhost"
DESTPORT = 12347

HDRLEN = 42
NTONES = 1024 # i think with timestamps, there are acutally only 1023 tones
DATALEN = NTONES * 4 * 2 # in bytes = 1024 4 byte (32 bit) i,q numbers
PACKETLEN =  DATALEN + HDRLEN
print PACKETLEN

def config_socket():
    #s_receive = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3)) # note that AF_PACKET is only available on linux
    s_receive = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # note that AF_PACKET is only available on linux
    print "open socket"
    try:
        s_receive.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2*PACKETLEN)
        print "Receive buffer is {rcvbuf} bytes".format(rcvbuf = s_receive.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF) )

        #s_receive.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #s_receive.setblocking(0)
        #s_receive.bind(('lo0', 0x0003))

        s_receive.bind((DESTADDR, DESTPORT))

        print "Bound to {ip} at port {port}".format(ip=DESTADDR, port=DESTPORT)
        return s_receive

    except socket.error, v:
        print "socket error", v
        errorcode = v[0]
        if errorcode == 19:
            print "Ethernet device could not be found"
            return


def waitForData(socket_handler):
    timeout = 1
    read, write, error = select.select([socket_handler], [], [socket_handler], timeout)
    print "select did something"
    if not (read or write or error):
        print "Socket timed out"
        return
    else:
        print "PACKET RECEIVED"
        for s in read:
            packet = s.recv(PACKETLEN)
            print packet
        # if len(packet) != PACKETLEN:
        #     packet = []

        return packet

if __name__ == '__main__':
    s = config_socket()
    while s:
        time.sleep(0.5)
        try:
            p = waitForData(s)
            #waitfordata1(s)

        except KeyboardInterrupt:
            sys.exit(0)
