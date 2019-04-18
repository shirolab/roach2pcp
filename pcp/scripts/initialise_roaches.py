#!/usr/bin/env python

# initliation script.
# This script is the first code to be run after all hardware in connected and switched on
# run as

# We could write a small helper script to check things are connected would be useful for initial configuration testing
#   - check dnsmasq is running
#   - check roach(s) are connected
#
import logging as _logging
_logger = _logging.getLogger(__name__)

from ..configuration import color_msg as cm

from .. import ROACH_LIST, mux_channel

def print_current_roaches(muxchannel):

    print "this is {roachid}".format(roachid = muxchannel.roachid)

def verify_configuration():
    pass

def _check_firmware_loaded(roaches, upload_firm):
    for roach in roaches:
        if roach.roach_iface.fpg_uploaded:
            print "[ " + cm.OKBLUE + "ok" + cm.ENDC +" ] Firmware Roach: {roachid}".format(roachid = roach.roachid) 
        else:
            print "[ " + cm.WARNING + "fail" + cm.ENDC +" ] Not Firmware in Roach: {roachid}".format(roachid = roach.roachid) 
            if upload_firm:
                roach.roach_iface.upload_firmware_file(force_reupload=True)

def _check_packets_received(roaches):
    flag_roaches = []
    for roach in roaches:
        if roach.writer_daemon.check_packets_received:
            print "[ " + cm.OKBLUE + "ok" + cm.ENDC +" ] {roachid} Packets received :)".format(roachid = roach.roachid) 
            flag_roaches.append(True)
        else:
            print "[ " + cm.WARNING + "fail" + cm.ENDC +" ] {roachid} No packets received :(".format(roachid = roach.roachid) 
            flag_roaches.append(False)

    return flag_roaches

def main(roach_list, force_reupload=False):
    _logger.info( "this is the function that is run" )

    roaches = []
    for roachid in roach_list:
    	roaches.append(mux_channel.muxChannel( roachid ))

    # Reload everything
    if force_reupload:
        for roach in roaches:
            roach.initialse_hardware()
            roach.roach_iface.initialise_fpga(force_reupload=True)
    else:
        # Check Firmware
        _check_firmware_loaded(roaches, upload_firm=False)

        # Check Packets received
        active_roach = _check_packets_received(roaches)

        for i in range(len(roaches)):
            if not active_roach[i]:
                roaches[i].roach_iface.initialise_fpga(force_reupload=True)
            roaches[i].initialse_hardware()

    roach_dict = {}
    for roach in roaches:
        roach_dict[roach.roachid] = roach

    return roach_dict