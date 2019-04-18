import pcp
import time
import sys

#pcp.set_log_level(level=10)

mc = []
for roach in ['phantom','clones','sith','hope','empire','jedi']:
	ch = pcp.mux_channel.muxChannel(roach)
	ch.initialse_hardware()
	ch.roach_iface.initialise_fpga(force_reupload=True)
	ch.roach_iface.write_freqs_to_qdr(ch.toneslist.bb_freqs,ch.toneslist.amps,ch.toneslist.phases)
	mc.append(ch)

for roach in mc:
	roach.start_stream(dont_ask=True)

time.sleep(60)

for roach in mc:
    roach.stop_stream()
    roach.shutdown()

sys.exit()