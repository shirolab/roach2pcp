#from numpy import *
#from matplotlib.pyplot import *; ion()
import numpy as np
import matplotlib.pyplot as plt; plt.ion()
import time
import datetime
import os
import sys
import atexit
import pygetdata as gd

#os.chdir('/home/muscat/multitone2020-08-13/roach2pcp/')
#sys.path.append('/home/muscat/multitone2020-08-13/roach2pcp/')
import pcp


#The muscat channels:
ALLCHNUMS = [0]
ALLNAMES  = ['roach0']


#The ones we are going to use:
CHNUMS    = [0]
CHNAMES   = [ALLNAMES[n] for n in CHNUMS]
NCHANS    = len(CHNUMS)


#The initial tonelist files:
TL_FILES    = ['/data/tonelists/CD073_devF_tonelist_test.txt']
LO_FILES    = ['/data/tonelists/lo_test.txt']
ATTIN_FILES    = ['/data/tonelists/attin_test.txt']
DWM_FILES    = ['/data/tonelists/dwm_test.txt']

#Miscellanea
FFT_SHIFT = 0b1111111
LOCATION  = 'CAL_LAB'

class fucking_awesome(object):
    pass


class MuxController(fucking_awesome):
    """
    High level code to perform observations with MUSCAT.
    
    Can be run in an interactive interpreter (eg lab testing),
    or as a part client/server system (eg at telescope)
    """
    def __init__(shit, 
                 pcp       =True):
        
        super(fucking_awesome,shit).__init__()
        self                = shit
        self.mclist         = None
        self.stream_flag    = 0
        self.tune_flag      = 0
        
        atexit.register(self.shutdown)
   
        if pcp:
            self.pcp_init_hw(CHNUMS, CHNAMES)
            self.pcp_init_tones(TL_FILES, LO_FILES, ATTIN_FILES, DWM_FILES,
                                extra_attin=0, diff_attinout=14.0)
        return

    def shutdown(self):
        if self.mclist is not None:
            [j.shutdown for j in self.mclist]
        return
    
    def pcp_init_hw(self,chnums,chnames):
        """start the pcp software, init the roach boards and other hardware"""
        
        if self.mclist is not None:
            print 'Stopping existing PCP processes...'
            [j.shutdown for j in self.mclist]   
            self.mclist = None

        pcp.scripts.init_pcp()

        self.mclist  = pcp.mux_channel.test_mclist(chnames,chnums)

        self.mclist.call_mc_method_in_parallel('initialise_hardware')
        self.mclist.call_mc_method_in_parallel('initialise_fpga',
                                                force_reupload=True)
        self.mclist.pps_timestamp_start()
        #time.sleep(1.5)
        #self.mclist.pps_timestamp_stop()
        
        return
    
    def pcp_init_tones(self, tl_files, lo_files, attin_files, dwm_files,
                       extra_attin=[0]*6, 
                       diff_attinout=14):    
        """init the toneslists in the pcp mux channles"""
        
        self.mclist.init_toneslists(tl_files, lo_files, attin_files,
                                    dwm_files,
                                    extra_attin=extra_attin,
                                    diff_attinout=diff_attinout)
        

        self.mclist.call_mc_method_in_parallel('write_freqs_to_fpga',
                                                auto_write=True,
                                                check=False,
                                                useoffsetatt=True,
                                                fft_shift=FFT_SHIFT)
                
        return
    
        
        
    
    def sweep_only(self,
                   span = 100000.,
                   step = 1000.,
                   start = 25,
                   stop = 10,
                   averaging = 25):

        self.mclist.sweep_lo(sweep_span = span,
                            sweep_step  = step,
                            startidx    = start,
                            stopidx     = start+averaging, 
                            sweep_avgs  = start+averaging+stop)
        
        for j in self.mclist: j.sweep.calc_sweep_cal_params(despike_window=5)
        
        return
    
        
    def sweep_and_place_tones(self,
                              search_bw_hz               = 100000.,
                              tone_placement_accuracy_hz = 1000.,
                              start = 25,stop  = 10,averaging = 25):
        """Only sets tones, still have to sweep before recording 
        Want this to be fast. Keep numbers low.
        #averages = 10 # pcp might fail if avergaing is less than 10
        #start    = 25 samples to wait at start. Do not set this lower than 25
        #stop     = 10 samples to wait at end. Don not set this lower than 10"""
         
                
        self.sweep_only(search_bw_hz,
                        tone_placement_accuracy_hz,
                        start,
                        stop,
                        averaging)

        
        for j in self.mclist: j.tl.rf_freqs = j.sweep.calparams['f0s']
        
        self.mclist.call_mc_method_in_parallel('write_freqs_to_fpga',
                                          auto_write=True,
                                          check=False,
                                          useoffsetatt=True,
                                          fft_shift=FFT_SHIFT)

        return
       
    
    def retune_only(self,search_span = 100000.,
                    search_step = 1000.,
                    search_start = 25, search_stop  = 10,search_avg = 25, 
                    sweep_span = 100000.,
                    sweep_step = 1000.,
                    sweep_start = 25, sweep_stop = 10,sweep_avg  = 25):

        """ Sweep, tune onto resonances, sweep again."""
            
        self.sweep_and_place_tones(search_span,
                                   search_step,
                                   search_start,
                                   search_stop,
                                   search_avg)
        
        self.sweep_only(sweep_span,
                        sweep_step,
                        sweep_start,
                        sweep_stop,
                        sweep_avg)
        
        return




    
    def record_only(self,duration):

        """ Record a timestream."""

        self.mclist.stream_for_duration(duration)

        return
    
    def start_recording(self):
        self.mclist.stream_start()

        
    def stop_recording(self):
        self.mclist.stream_stop()
        time.sleep(3)
    
    def sweep_and_record(self,duration, span, step,start=25,stop=10, averaging=10):

        """ Sweep and record a timestream, but dont retune."""
        self.sweep_only(span,step,start,stop,averaging)
        self.record_only(duration)

        return

    # CHECK ME
    def sweep_and_start_recording(self, span, step, start=25,stop=10, averaging=10):

        self.sweep_only(span,step,start,stop,averaging)
        self.start_recording()
    

    def retune_and_record(self, 
                        duration,
                        search_span = 100000.,
                        search_step = 1000.,
                        search_start = 25, search_stop  = 10,search_avg = 25,
                        sweep_span = 100000.,
                        sweep_step = 1000.,
                        sweep_start = 25, sweep_stop = 10,sweep_avg  = 25):
        """ Sweep, tune onto resonances, sweep again and record a timestream."""  
        
        self.retune_only(search_span = search_span,
                    search_step = search_step,
                    search_start = search_start,
                    search_stop  = search_stop,
                    search_avg = search_avg, 
                    sweep_span = sweep_span,
                    sweep_step = sweep_step,
                    sweep_start = sweep_start,
                    sweep_stop  = sweep_stop,
                    sweep_avg = sweep_avg)
        
        self.record_only(duration)

        return
    
    def retune_and_start_recording(self, 
                        search_span = 100000.,
                        search_step = 1000.,
                        search_start = 25, search_stop  = 10,search_avg = 25,
                        sweep_span = 100000.,
                        sweep_step = 1000.,
                        sweep_start = 25, sweep_stop = 10,sweep_avg  = 25):
        """ Sweep, tune onto resonances, sweep again and 
        start recording a timestream, need to stop manually."""
        
        self.retune_only(search_span = search_span,
                    search_step = search_step,
                    search_start = search_start,
                    search_stop  = search_stop,
                    search_avg = search_avg, 
                    sweep_span = sweep_span,
                    sweep_step = sweep_step,
                    sweep_start = sweep_start,
                    sweep_stop  = sweep_stop,
                    sweep_avg = sweep_avg)
        
        self.start_recording()

        return
    
    
    def tune(self):
        self.retune()
        
        if not self.ch.current_dirfile is None:
            self.ch.stop_stream()
            time.sleep(1)
            
        
        self.ch.sweep_lo(sweep_avgs=20,
                               startidx=10,
                               sweep_step = 2000,
                               sweep_span = 450e3)
        print 'Done Tuning'
        time.sleep(1)
        return 0


if __name__=='__main__':
    M = MuxController()
    
    
