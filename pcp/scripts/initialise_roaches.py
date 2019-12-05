#!/usr/bin/env python

# initialization script.
# This script is the first code to be run after all hardware in connected and switched on
# run as
# >> import pcp
# >> pcp.script.initialise_roaches()

# We could write a small helper script to check things are connected would be useful for initial configuration testing
#   - check dnsmasq is running
#   - check roach(s) are connected


import logging as _logging
from .. import color_logs as CL
_logger = _logging.getLogger(__name__)

from .. import ROACH_LIST, mux_channel
from . import set_muscat_init_synth as set_synth_MUSCAT
import numpy as np


def print_current_roaches(muxchannel):

    print "this is {roachid}".format(roachid = muxchannel.roachid)

def verify_configuration():
    pass

def _check_firmware_loaded(mux_channel_list, upload_firm=False):
    for mux_channel in mux_channel_list:
        if mux_channel.roach_iface.fpg_uploaded:
            print "[ %sok%s ] Channel {roachid}: Firmware {roachid}".format(roachid = mux_channel.roachid)%(CL.OKBLUE, CL.ENDC)
            _logger.info("Channel %s: Firmware loaded"%mux_channel.roachid)
        else:
            print "[ %sfail%s ] Not Firmware in Roach: {roachid}".format(roachid = mux_channel.roachid)%(CL.FAIL, CL.ENDC)
            _logger.warning("Channel -%s: Firmware failed"%mux_channel.roachid)
            if upload_firm:
                mux_channel.roach_iface.upload_firmware_file(force_reupload=True)

def _check_packets_received(mux_channel_list):
    mux_channel_packets_flag  = {}

    for mux_channel in mux_channel_list:
        if mux_channel.writer_daemon.check_packets_received:
            print "[ %sok%s ] {roachid} Packets received :)".format(roachid = mux_channel.roachid)%(CL.OKBLUE, CL.ENDC)
            _logger.info("%s Packets received"%mux_channel.roachid)
            mux_channel_packets_flag[mux_channel.roachid] = True
        else:
            print "[ %sfail%s ] {roachid} No packets received :(".format(roachid = mux_channel.roachid)%(CL.FAIL, CL.ENDC)
            _logger.warning("%s No packets received"%mux_channel.roachid)
            mux_channel_packets_flag[mux_channel.roachid] = False

    return mux_channel_packets_flag

def _verify_channel(mux_channel_list):
    # check firmware
    _check_firmware_loaded(mux_channel_list)

    # check if packets are received
    _check_packets_received(mux_channel_list)


def _set_default_MUSCAT_hw(mux_chan, ref=0, ref_freq=10e6, clk_freq=512e6, clk_pow=0, lo_pow=15.75, atten_in=None, atten_out=None):

    mux_chan.initialise_hardware()

    # set the synthesizer
    set_synth_MUSCAT.main(mux_chan, ref, ref_freq, clk_freq, clk_pow, lo_pow)
    print "%sSynthesizer set to MUSCAT default parameters%s"%(CL.OKBLUE, CL.ENDC)

    # set attenuators
    if atten_in:
        mux_chan.input_atten.att = atten_in
    if atten_out:
        mux_chan.output_atten.att = atten_out
    print "%sAttenuators set to MUSCAT default parameters%s"%(CL.OKBLUE, CL.ENDC)

def main(mux_channel_list, tones=None, init_packets=True, set_MUSCAT_hardware=True, force_reupload=False):
    _logger.info( "Initialising channels..." )

    mux_chan_dict = {}
    for mux_chan_id in mux_channel_list:
        #mux_channels.append(mux_channel.muxChannel( mux_channel_id ))

        mux_chan_dict[mux_chan_id] = mux_channel.muxChannel( mux_chan_id )

        # set MUSCAT default params
        if set_MUSCAT_hardware:
            _set_default_MUSCAT_hw(mux_chan_dict[mux_chan_id])

        # set firmware
	if force_reupload or (not mux_chan_dict[mux_chan_id].roach_iface.fpg_uploaded):
            mux_chan_dict[mux_chan_id].roach_iface.upload_firmware_file(force_reupload=True)
            print "%sChannel {roachid}: Loading firmware%s".format(roachid = mux_chan_dict[mux_chan_id].roachid)%(CL.OKBLUE, CL.ENDC)
        else:
            print "%sChannel {roachid}: Firmware loaded already%s".format(roachid = mux_chan_dict[mux_chan_id].roachid)%(CL.OKGREEN, CL.ENDC)

        # loading tones
        print "%sWriting tones%s"%(CL.OKBLUE, CL.ENDC)
        if tones:
            if len(tones) == 3 and (len(bb_freqs) == len(amps)) and (len(amps) == len(phases)):
                bb_freqs = tones[0]
                amps = tones[1]
                phases = tones[2]
                mux_chan_dict[mux_chan_id].roach_iface.write_freqs_to_qdr(bb_freqs, amps, phases)
            else:
                print "%sLength of the tones array does not match. Check again your tones%s"%(CL.WARNING, CL.ENDC)

        else:
            if init_packets:
                if mux_chan_dict[mux_chan_id].writer_daemon.check_packets_received:
		    print "[ %sactive%s ] {roachid} Packets reception".format(roachid = mux_chan_dict[mux_chan_id].roachid)%(CL.OKGREEN, CL.ENDC)
		else:
		    # define default values. Just write one tone
                    print "%sWriting a tone to start packets reception%s"%(CL.OKBLUE, CL.ENDC)

                    bb_freqs = np.array([100e6])
                    amps = np.array([1.0])
                    phases = np.array([0.5])

                    mux_chan_dict[mux_chan_id].roach_iface.write_freqs_to_qdr(bb_freqs, amps, phases)

    _verify_channel(mux_chan_dict.values())

    return mux_chan_dict
