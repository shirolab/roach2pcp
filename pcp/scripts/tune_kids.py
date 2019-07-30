#!/usr/bin/env python

# initliation script.
# This script is the first code to be run after all hardware in connected and switched on
# run as

# We could write a small helper script to check things are connected would be useful for initial configuration testing
#    - check dnsmasq is running
#   - check roach(s) are connected
#
import logging as _logging
_logger = _logging.getLogger(__name__)

from .. import ROACH_LIST, mux_channel

def print_current_roaches(muxchannel):

    print "this is {roachid}".format(roachid = muxchannel.roachid)

def verify_configuration():
    pass

def main():
    _logger.info( "this is the function that is run" )
