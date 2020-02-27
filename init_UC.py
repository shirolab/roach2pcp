# Standard initialization for SuperSpec
#
# Run this to import pcp and initialize ROACHes

import time
import numpy as np
import pcp

log = pcp.logger

#################################
# Initialize ROACHes
log.info('Initializing r0')
r0 = pcp.mux_channel.muxChannel('roach0')

#################################
# EVERYTHING BELOW should operate on variables that already
# exist in the workspace, so should be done with scripts
"""
# Upload fpga firmware
pcp.scripts.upload_fpgas(r0)

# Initialize synth (do this first since ampcorr is dependent on LO location)
pcp.scripts.lo_wrapper(r0) # can send in user-defined freq here

# If for this toneslist/LO you haven't yet measured the amplitude correction...
pcp.scripts.ampcorr_wrapper(r0) # saves the correction
# We have now written a corrected toneslist and that file was printed to screen

# Assuming we have a good previous tone history file (write it down for each session!)
pcp.scripts.write_oldtonelist(r0, '20200227-165025')

log.info('Checking that packets are streaming')
r0.writer_daemon.check_packets_received()
"""
###############################
# For e.g. observations, may want to flag when in different
# datataking modes
"""
log('Staring at source')
r0.write_int('GbE_packet_info',1)
r0.start_stream(dont_ask=True)
time.sleep(5)
r0.stop_stream(dont_ask=True)
r0.write_int('GbE_packet_info',0)
log('Off source')
"""

"""
# Minimal list for testing output

import pcp
import numpy as np
import os
import matplotlib.pyplot as plt

r0 = pcp.mux_channel.muxChannel('roach0')
r0.initialise_hardware()
r0.roach_iface.initialise_fpga(force_reupload=True)
r0.toneslist.amps = np.ones_like(r0.toneslist.bb_freqs)
r0.toneslist.set_phases()
r0.toneslist.lo_freq = 200e6
r0.roach_iface.write_freqs_to_qdr(r0.toneslist.bb_freqs,
                                  r0.toneslist.amps,
                                  r0.toneslist.phases)
r0.synth_lo.frequency = r0.toneslist.lo_freq
r0.synth_lo.output_power = 8.0
r0.synth_lo.rf_output = True
r0.input_atten.att = 6.0

r0.synth_lo.device.close()

"""
