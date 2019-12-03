# Standard initialization for SuperSpec
#
# Run this to import pcp and initialize ROACHes

import time
import numpy as np
import pcp

#logger = pcp.logfile.configure_logging()
log = pcp.logger
log.info('Starting initialization script')

#################################
# Initialize ROACHes
r0 = pcp.mux_channel.muxChannel('roach0')
r0.initialise_hardware()
r0.roach_iface.initialise_fpga(force_reupload=True)

log.info('r0: Setting tones list and writing to QDR')
r0.toneslist.amps = np.ones_like(r0.toneslist.bb_freqs)
r0.toneslist.set_phases()
r0.roach_iface.write_freqs_to_qdr(r0.toneslist.bb_freqs,
                                  r0.toneslist.amps,
                                  r0.toneslist.phases)
log.info('r0: Done writing tones list')

###############################
# Initialize synth

#log('Initializing synthesizer to ' + \
#    str(r0.toneslist.lo_freq/1e6) + ' MHz')
#r0.synth_lo.frequency = r0.toneslist.lo_freq
#r0.synth_lo.output_power = 8.0
#r0.synth_lo.rf_output = True

###############################
log.info('Checking that packets are streaming...')
r0.writer_daemon.check_packets_received()
log.info('Initialization complete')

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
