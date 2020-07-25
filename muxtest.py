import pcp
from numpy import *
from matplotlib.pyplot import *
import fitting
import toneslist_tools
import multiprocessing.pool as _multiprocessing_pool

import power_tuning

name = ['phantom','clones','sith','hope','empire','jedi']
mc = pcp.mux_channel.muxChannelList(name)
mclist = [eval('mc.'+mcname) for mcname in name]; 
mc.muscat_init(name)

#[ch.input_atten.set_atten(3) for ch in mclist]
#mc.phantom.input_atten.set_atten(0)
[ch.input_atten.set_atten(att) for ch,att in zip(mclist,[0.0,6.75,10.5,8.75,8.25,6.5])]

#[ch.output_atten.set_atten(9) for ch in mclist]
#mc.sith.output_atten.set_atten(0)
[ch.output_atten.set_atten(att) for ch,att in zip(mclist,[1.75,0.5,0.5,0.0,0.25])]




mc.sweep_lo(name,sweep_avgs=50,startidx=20,sweep_step = 1000,sweep_span=250e3)

sp = subplots(3,2,sharex=True,sharey=True,num='ss')[1].ravel()
sa = subplots(3,2,sharex=True,sharey=True,num='aa')[1].ravel()
show()

for ch in mclist:
        print 'plotting...',ch.chidx
        for k,(ff,zz,ss) in enumerate(zip(ch.sweep.rf_freqs,ch.sweep.data,ch.sweep.fit_s21)):
            #fit,params,guess=fitting.fit_nonlinear_resonator(ff,zz,method='least_squares')
            sp[ch.chidx].plot(ff,20*log10(abs(zz)),'x',color='k')
            sp[ch.chidx].plot(ff,20*log10(abs(ss)),'-',color='k')
            sp[ch.chidx].plot(ff,20*log10(abs(gradient(zz,ff))),'-',color='k')
    
        sa[ch.chidx].plot(ch.lo+ch.sweep._bb_freqs,ch.sweep.fit_a,'o',color='k')
        pause(0.1)


N=5
colors=cm.rainbow(linspace(0,1,N))
    
a_min = 0.05
a_max = 0.1
p_up=0.25
p_down=-0.25

finished=[0,0,0,0,0,0]

parallel =True

for n in range(N):
    if all([fin==len(ch.freqs) for fin,ch in zip(finished,mclist)]):
        print 'All done'
        break
    
    if n==0:
        pass
    
    if parallel:
        #pass
        mp_pool = _multiprocessing_pool.ThreadPool( processes = len(mclist) )
        res = [mp_pool.apply_async(power_tuning.change_power_level,(ch,a_min,a_max,p_up,p_down))  for ch in mclist ]
        # wait for processing to finish 
        while not all([r.ready() for r in res]):
            time.sleep(0.5)
        # close and join the ThreadPool
        mp_pool.close()
        mp_pool.join()
        finished=[r.get() for r in res]
        print finished
    else:
        for ch in mclist:
            ret = power_tuning.change_power_level(ch,a_min,a_max,p_up,p_down)
            finished[ch.chidx] = ret
        print finished
   
    #pause(1)
    mc.sweep_lo(name,sweep_avgs=50,startidx=20,sweep_step =1000,sweep_span=250e3)
    #pause(1)
    #sa = subplots(3,2,sharex=True,sharey=True,num='aa')[1].ravel())
    #sp = subplots(3,2,sharex=True,sharey=True,num='ss')[1].ravel())
    for ch in mclist:
        print 'plotting...',ch.chidx
        #for k,(ff,zz,ss) in enumerate(zip(ch.sweep.rf_freqs,ch.sweep.data,ch.sweep.fit_s21)):            #fit,params,guess=fitting.fit_nonlinear_resonator(ff,zz,method='least_squares')
            #sp[ch.chidx].plot(ff,20*log10(abs(zz)),'x',color=colors[n])
            #sp[ch.chidx].plot(ff,20*log10(abs(ss)),'-',color=colors[n])
            #sp[ch.chidx].plot(ff,20*log10(abs(gradient(zz,ff))),'-',color=colors[n])
    
        sa[ch.chidx].plot(ch.lo + 
                    ch.sweep._bb_freqs,ch.sweep.fit_a,'o',color=colors[n])
        draw()
        
        #pause(0.1)
            
