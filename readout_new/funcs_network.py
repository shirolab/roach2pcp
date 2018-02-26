#

# Functions used to handle dirfile data saving

# take sam gs code
# function to return an object with all relevant information
# function to configure socket

import os, socket

def generate_socket(sockettype = 'raw', **socketkwargs):
    """
    Function to generate and return a socket instance.

    """
    assert sockettype in ['raw', 'udp']

    if sockettype == 'udp':
        return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    elif sockettype == 'raw':
        return socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
    else:
        raise socket.error

def configure_socket_and_bind(socketinstance, bindaddress, bindport, buffer_size):

    """Configure socket parameters"""

    assert type(socketinstance) is socket._socketobject

    # should be able to determine socket type using socketinstance._sock and
    # the options are different depending on the socket protocol
    socketinstance.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    socketinstance.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, buffer_size) # this might not be required for the UDP interface
    socketinstance.setblocking(0)

    try:

        if socketinstance.proto == 0: # corresponding to AF_INET
    		socketinstance.bind((bindaddress, bindport))
        elif socketinstance.proto == 768 # corresponding to AF_PACKET (i think)
            socketinstance.bind((bindaddress, 3))
        else raise
    except socket.error, v:
        errorcode = v[0]
        if errorcode == 19:
            print "Ethernet device could not be found"
            pass
    return
