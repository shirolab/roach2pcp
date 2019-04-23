# Standard initialization for SuperSpec
#
# Run this to import pcp and initialize ROACHes

import time
import pcp
import numpy as np

#################################
# Initialize KSK's stupid-simple logger
pcp.ssLog.init_log()
log = pcp.ssLog.write_log

#################################
# Initialize ROACHes

log('Initializing ROACHes')
r0 = pcp.mux_channel.muxChannel('roach0')
r0.initialise_hardware()
r0.roach_iface.initialise_fpga(force_reupload=True)

log('Setting tones list and writing to QDR')
 Set tones amplitudes and frequencies
r0.toneslist.amps = np.ones_like(r0.toneslist.bb_freqs)
r0.toneslist.set_phases()
r0.roach_iface.write_freqs_to_qdr(r0.toneslist.bb_freqs,
                                  r0.toneslist.amps,
                                  r0.toneslist.phases)

###############################
# Initialize synth

log('Initializing synthesizer to ' + \
    str(r0.toneslist.lo_freq/1e6) + ' MHz')
r0.synth_lo.frequency = r0.toneslist.lo_freq
r0.synth_lo.rf_output = True

###############################
# Check packets, etc

r0.writer_daemon.check_packets_received()
log('Initialization complete')



