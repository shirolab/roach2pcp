import sys,os,time
from matplotlib.pyplot import *; ion()
from numpy import *

import muscat_cryo
mc=muscat_cryo.muscat_cryo()
mct = mc.base_temperature()
print 'MUSCAT BASE TEMPERATURE: %f'%mct


initstart=time.time()

import pcp
pcp.scripts.init_pcp()

print '\nPCP INIT DONE\n\n\n'
#pcp.logfile.set_log_level_debug() #too much information

allchnums  = [1,2,3,4,5,6]
allnames   = ['phantom','clones','sith','hope','empire','jedi']
#chnums  = [2,4,5,6]
#chnums  = [6]
chnums  = [1,2,3,4,5,6]
chnames = [allnames[n-1] for n in chnums]

mclist  = pcp.mux_channel.test_mclist(chnames,chnums)

mclist.call_mc_method_in_parallel('initialise_hardware')
mclist.call_mc_method_in_parallel('initialise_fpga',force_reupload=True)

#tlfiles = ['/home/muscat/multitone2020-08-13/roach2pcp/data/tonelists/t%d_20200903-130mk.txt'%ch for ch in chnums]
#tlfiles = ['/home/muscat/toneslists/tones_20201016/run3_fixed_crosstalk/t%d_20201016-130mk-300k.txt'%ch for ch in chnums]

##tl_halfs = ['a','b']
#tl_half = 'a'
#tlfiles = ['/home/muscat/toneslists/tones_20201016/run4_half_lists/t%d%c_20201016-130mk-300k.txt'%(ch,tl_half) for ch in chnums]
#lo_files = ['/home/muscat/toneslists/tones_20201016/run4_half_lists/lo%d%c.txt'%(ch,tl_half) for ch in chnums]

tl_half = 'b'
tl_half = 'b'
tlfiles = ['/home/muscat/toneslists/tones_20201016/run6_atts/t%d%c_20201016-130mk-300k.txt'%(ch,tl_half) for ch in chnums]
lo_files = ['/home/muscat/toneslists/tones_20201016/run6_atts/lo%d%c.txt'%(ch,tl_half) for ch in chnums]
attin_files = ['/home/muscat/toneslists/tones_20201016/run6_atts/attin%d%c_20201016-130mk-300k.txt'%(ch,tl_half) for ch in chnums]

mclist.init_toneslists(tlfiles,lo_files,attin_files,extra_attin=0,diff_attinout=14)

#lo_freqs = []
#for j in range(len(lo_files)):
    #with open(lo_files[j],'r') as file:
        #lo_freqs.append(int(file.read()))
#print lo_freqs

#for chidx in range(len(chnums)):
    
    #chnum  = chnums[chidx]
    #chname = chnames[chidx]
    #tlfile = tlfiles[chidx]
    #lo_freq = lo_freqs[chidx]
    #print chnum,tlfile, lo_freq
    
    #mc = mclist[chnum] 
    #mc.tl.load_tonelist(tlfile,lo_freq=lo_freq)
    #mc.synth_lo.frequency = mc.tl.lo_freq


#exit()
#mclist.jedi.sweep_lo()
#mclist.jedi.sweep.calc_sweep_cal_params()
#mclist.jedi.sweep.plot_sweep()

#attin_addition = 0


#if tl_half is 'a':
    #attinfiles = ['/home/muscat/toneslists/tones_20201016/run6_atts/attin%da_20201016-130mk-300k.txt'%(ch) for ch in chnums]
    #for j,attfile in zip(mclist,attinfiles):
        #attin = loadtxt(attfile).item() + attin_addition
        #j.atten_in.set_atten(attin)
        ##j.atten_out.set_atten(27.-attin)
        #j.atten_out.set_atten(max([0,14.-attin]))
    
#elif tl_half is 'b':
    #attinfiles = ['/home/muscat/toneslists/tones_20201016/run6_atts/attin%db_20201016-130mk-300k.txt'%(ch) for ch in chnums]
    #for j,attfile in zip(mclist,attinfiles):
        #attin = loadtxt(attfile).item() + attin_addition
        #j.atten_in.set_atten(attin)
        ##j.atten_out.set_atten(27.-attin)
        #j.atten_out.set_atten(max([0,14.-attin]))
    
#else:
    #[j.atten_in.set_atten(15) for j in mclist]
    #[j.atten_out.set_atten(15) for j in mclist]



#otherwise tl complains 
print [j.roachid for j in mclist]
self=j

fft_shift=0x111111
mclist.call_mc_method_in_parallel('write_freqs_to_fpga',auto_write=True,useoffsetatt=True,check=False,fft_shift=fft_shift)

span=100000
step=500
avgs=75
start=25
stop=50


mclist.sweep_lo(sweep_avgs=avgs,sweep_span =span, sweep_step=step,
                startidx=start, stopidx=stop)

[j.sweep.calc_sweep_cal_params() for j in mclist]
[j.sweep.plot_sweep() for j in mclist]

exit()

for j in mclist:
    j.tl.rf_freqs = j.sweep.calparams['f0s']

mclist.call_mc_method_in_parallel('write_freqs_to_fpga',auto_write=True,useoffsetatt=True,check=False,fft_shift=fft_shift)

span=100000
step=5000
avgs=50
start=25
stop=40

mclist.sweep_lo(sweep_avgs=avgs,sweep_span =span, sweep_step=step,
                startidx=start, stopidx=stop)
[j.sweep.calc_sweep_cal_params() for j in mclist]
[j.sweep.plot_sweep() for j in mclist]


t=70; mclist.call_mc_method_in_parallel('start_stream',stream_time=t,dont_ask=True)

exit()





#sweepstart=time.time()

#mclist.call_mc_method_in_parallel('sweep_lo',sweep_avgs=avgs,startidx=start,stopidx=stop,sweep_span=span,sweep_step=step)

#print '\n\ncalc_sweep_params\n\n'

#for chidx in range(len(chnums)):
    #chnum  = chnums[chidx]
    #chname = chnames[chidx]
    #mc     = mclist[chnum]
    #mc.sweep.calc_sweep_cal_params()
    ##mc.sweep.plot_sweep()

#print 'streaming in...',;sys.stdout.flush()
#for j in range(3):
    #print 3-j,;sys.stdout.flush()
    #time.sleep(1)
#print 

#streamstart = time.time()

#duration = 10 #s
#if 0:
    #t0=time.time()
    #mclist.jedi.start_stream(dont_ask=True,stream_time=duration)
    #print 'Seconds requested:',duration, 'Time taken:', time.time()-t0
    #print [j.current_dirfile.nframes for j in mclist]

#if 0:
    #t0=time.time()
    #mclist.call_mc_method_in_parallel('start_stream',dont_ask=True,stream_time=duration)
    #print 'Seconds requested:',duration, 'Time taken:', time.time()-t0
    #print [j.current_dirfile.nframes for j in mclist]

#streamstop = time.time()

#if 0:
    #t0=time.time()
    #mclist.call_mc_method_in_parallel('start_stream',dont_ask=True)
    #time.sleep(duration)
    #mclist.call_mc_method_in_parallel('stop_stream')
    #t=time.time()-t0


#print 'total:',streamstop-initstart
#print 'to sweep start:', sweepstart-initstart
#print 'to do the sweep:', streamstart - sweepstart
#print 'to get 2x 30s data:',streamstop-streamstart


def check_sweep_lo_steps(dirfile,kidnum,startidx=10,stopidx=20):
    import pygetdata as gd
    df = gd.dirfile(dirfile,gd.RDONLY)
    z  = df.getdata('K%03d_z'%kidnum)
    lotimes = df.getdata( "lostep_times" )
    ptimes  = df.getdata( "python_timestamp" ) # way to get the python_timestamp field with knowing any field suffix
    lofreqs = df.getdata( "lo_freqs" )

    # align LO steps with python timestreams
    idxs = np.searchsorted(ptimes, lotimes) # miss out the first point (should always be 0)
    figure()
    plot(abs(z))
    [axvline(i,color='k') for i in idxs]
    [axvline(i+startidx,color='g') for i in idxs]
    [axvline(i+stopidx,color='r') for i in idxs]
    title(dirfile + ': K%03d_z'%kidnum)
    show()
    



#t0=time.time()
#mclist.call_mc_method_in_parallel('sweep_lo',sweep_span = span,sweep_step=step,sweep_avgs=avgs,startidx=start,stopidx=stop)
#print 'old = ',time.time()-t0

#[j.sweep.calc_sweep_cal_params() for j in mclist]
##[j.sweep.plot_sweep() for j in mclist]
##[check_sweep_lo_steps(j.current_dirfile.name,24,startidx=start,stopidx=stop) for j in mclist]


#mclist.call_mc_method_in_parallel('write_freqs_to_fpga',auto_write=True)

#exit()

t0=time.time()
mclist.sweep_lo(sweep_avgs=avgs,sweep_span = span,sweep_step=step,startidx=start,stopidx=stop)
print 'new = ',time.time()-t0

[j.sweep.calc_sweep_cal_params() for j in mclist]
#[j.sweep.plot_sweep() for j in mclist]
#[check_sweep_lo_steps(j.current_dirfile.name,24,startidx=start,stopidx=stop) for j in mclist]

for j in mclist:
    j.tl.rf_freqs = j.sweep.calparams['f0s']

mclist.call_mc_method_in_parallel('write_freqs_to_fpga',auto_write=True,fft_shift=fft_shift)
mclist.sweep_lo(sweep_avgs=avgs,sweep_span = span,sweep_step=step,startidx=start,stopidx=stop)

[j.sweep.calc_sweep_cal_params() for j in mclist]
[j.sweep.plot_sweep() for j in mclist]


