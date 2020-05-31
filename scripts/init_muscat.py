#!/usr/bin/env python

import time
import pcp

roaches = [phantom, clones, sith, hope, empire, jedi]
name_roaches = ['phantom', 'clones', 'sith', 'hope', 'empire', 'jedi']

i = 0
for roach in roaches:
    roach = pcp.mux_channel.muxChannel(name_roaches[i])
    roach.initialse_hardware()
    roach.roach_iface.initialise_fpga(force_reupload=True)
    roach.roach_iface.write_freqs_to_qdr(roach.toneslist.bb_freqs,roach.toneslist.amps,roach.toneslist.phases)
    i += 1