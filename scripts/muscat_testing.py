import sys,os,time
from matplotlib.pyplot import *; ion()
from numpy import *

initstart=time.time()

import pcp


pcp.scripts.init_pcp()
print '\nPCP INIT DONE\n\n\n'
#pcp.logfile.set_log_level_debug() #too much information

allchnums  = [1,2,3,4,5,6]
allnames   = ['phantom','clones','sith','hope','empire','jedi']
chnums  = [2,4,5,6]
#chnums  = [6]
chnums  = [1,2,3,4,5,6]
chnames = [allnames[n-1] for n in chnums]

mclist  = pcp.mux_channel.test_mclist(chnames,chnums)

mclist.call_mc_method_in_parallel('initialise_hardware')
mclist.call_mc_method_in_parallel('initialise_fpga',force_reupload=True)

tlfiles = ['/home/muscat/multitone2020-08-13/roach2pcp/data/tonelists/t%d_20200903-130mk.txt'%ch for ch in chnums]

for chidx in range(len(chnums)):
    chnum  = chnums[chidx]
    chname = chnames[chidx]
    tlfile = tlfiles[chidx]
    mc     = mclist[chnum] 
    mc.tl.load_tonelist(tlfile)
    mc.synth_lo.frequency = mc.tl.lo_freq

mclist.call_mc_method_in_parallel('write_freqs_to_fpga',auto_write=True)
#mclist.jedi.sweep_lo()
#mclist.jedi.sweep.calc_sweep_cal_params()
#mclist.jedi.sweep.plot_sweep()

sweepstart=time.time()

mclist.call_mc_method_in_parallel('sweep_lo')

for chidx in range(len(chnums)):
    chnum  = chnums[chidx]
    chname = chnames[chidx]
    mc     = mclist[chnum]
    mc.sweep.calc_sweep_cal_params()
    #mc.sweep.plot_sweep()

print 'streaming in...',;sys.stdout.flush()
for j in range(3):
    print 3-j,;sys.stdout.flush()
    time.sleep(1)
print 

streamstart = time.time()

duration = 10 #s
if 0:
    t0=time.time()
    mclist.jedi.start_stream(dont_ask=True,stream_time=duration)
    print 'Seconds requested:',duration, 'Time taken:', time.time()-t0
    print [j.current_dirfile.nframes for j in mclist]

if 0:
    t0=time.time()
    mclist.call_mc_method_in_parallel('start_stream',dont_ask=True,stream_time=duration)
    print 'Seconds requested:',duration, 'Time taken:', time.time()-t0
    print [j.current_dirfile.nframes for j in mclist]

streamstop = time.time()

if 0:
    t0=time.time()
    mclist.call_mc_method_in_parallel('start_stream',dont_ask=True)
    time.sleep(duration)
    mclist.call_mc_method_in_parallel('stop_stream')
    t=time.time()-t0


print 'total:',streamstop-initstart
print 'to sweep start:', sweepstart-initstart
print 'to do the sweep:', streamstart - sweepstart
print 'to get 2x 30s data:',streamstop-streamstart