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
ALLCHNUMS = [0, 1, 2, 3, 4, 5];#,1,2,3,4,5];
ALLNAMES  = ['roach0', 'roach1', 'roach2', 'roach3', 'roach4', 'roach5'];#,'r1','r2','r3','r4','r5'];


#The ones we are going to use:
#CHNUMS    = [1,2,3,4,5,6]
CHNUMS    = [1,2,3]
CHNAMES   = [ALLNAMES[n] for n in CHNUMS]
NCHANS    = len(CHNUMS)


#The initial tonelist files:
TL_DIR    = '/data/tonelists/'
#TL_FILES    = [TL_DIR+'tonelist_r%d.txt' %(ch) for ch in CHNUMS]
#LO_FILES    = [TL_DIR+'lo_r%d.txt' %(ch) for ch in CHNUMS]
#ATTIN_FILES    = [TL_DIR+'attin_r%d.txt' %(ch) for ch in CHNUMS]
#DWM_FILES    = [TL_DIR+'dwm_r%d.txt'%(ch) for ch in CHNUMS]

TL_FILES    = [TL_DIR+'CD062_devE_mirror_toneslist.txt', TL_DIR+'CD074_devD_tonelist_cold_wellsep.txt', TL_DIR+'CD062_devE_mirror_toneslist.txt']
LO_FILES    = [TL_DIR+'lo_r%d.txt' %(ch) for ch in CHNUMS]
ATTIN_FILES    = [TL_DIR+'attin_r%d.txt' %(ch) for ch in CHNUMS]
ATTOUT_FILES    = [TL_DIR+'attout_r%d.txt' %(ch) for ch in CHNUMS]
DWM_FILES    = [TL_DIR+'dwm_r%d.txt'%(ch) for ch in CHNUMS]

#The log file names:
CONLOG_FILENAME     ='/data/log/conlog.txt'
CONLOG_BACKUP_FILENAME  = '/home/superspec/Documents/conlog.txt'


#Miscellanea
FFT_SHIFT = 0b1111111
LOCATION  = 'CALTECH_LAB'


class MuxController(object):
    """
    High level code to perform observations with MUSCAT.
    
    Can be run in an interactive interpreter (eg lab testing),
    or as a part client/server system (eg at telescope)
    """
    def __init__(self, 
                 pcp       =True,
                 clfn      =CONLOG_FILENAME):
        
        self.clfn           = clfn
        self.mclist         = None
        self.stream_flag    = 0
        self.tune_flag      = 0
        
        
        """The muscat controller is starting..."""
        print 'Starting SuperSpec Control\n'
        
        self.write_conlog_entry('MuxController')
        self.write_conlog_entry('Observation log file location: %s'%self.clfn)
        
        atexit.register(self.shutdown)
   
        if pcp:
            self.pcp_init_hw(CHNUMS, CHNAMES)
            self.pcp_init_tones(TL_FILES, LO_FILES, ATTIN_FILES, ATTOUT_FILES, DWM_FILES)
        return



    def shutdown(self):
        if self.mclist is not None:
            for j in self.mclist:
		j.shutdown() 
		time.sleep(0.5)

        self.write_conlog_entry('Shutting down mux channels.')
        return
    
    
    
    def write_conlog_raw(self,string):
        with open(self.clfn,'a') as lfile:
            lfile.write(string)
            lfile.flush()
        return
    
    def write_conlog_entry(self,string):
        t=datetime.datetime.utcnow().isoformat()
        line = t+' '+string.strip()+'\n'
        self.write_conlog_raw(line)
        os.system('cp %s %s'%(self.clfn,self.clfn+'.bak'))
        os.system('cp %s %s'%(self.clfn, CONLOG_BACKUP_FILENAME))
        return
        
        
        
        
    def pcp_init_hw(self,chnums,chnames):
        """start the pcp software, init the roach boards and other hardware"""
        self.write_conlog_entry('pcp_init_hw: mclist: %s %s'%
                                (chnums,chnames) )
        
        if self.mclist is not None:
            print 'Stopping existing PCP processes...'
            self.write_conlog_entry(
                'pcp_init_hw: mclist exists already, stopping the old one.' )
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
        
        self.write_conlog_entry('pcp_init_hw: all done.')
        
        return
    
    
    
    
    def pcp_init_tones(self, tl_files, lo_files, attin_files, attout_files, dwm_files):    
        """init the toneslists in the pcp mux channles"""
        
        self.mclist.init_toneslists(tl_files, lo_files, attin_files, attout_files, dwm_files)
        
        self.write_conlog_entry('pcp_init_tones: tl_files = %s'%tl_files)
        self.write_conlog_entry('pcp_init_tones: lo_files = %s'%lo_files)
        self.write_conlog_entry('pcp_init_tones: attin_files = %s'%attin_files)
	self.write_conlog_entry('pcp_init_tones: attout_files = %s'%attout_files)
        self.write_conlog_entry('pcp_init_tones: dwm_files = %s'%dwm_files)

        #self.write_conlog_entry('pcp_init_tones: extra_attin = %s'%extra_attin)
        #self.write_conlog_entry('pcp_init_tones: diff_attinout = %s'%diff_attinout)

        self.mclist.call_mc_method_in_parallel('write_freqs_to_fpga',
                                                auto_write=True,
                                                check=False,
                                                useoffsetatt=True,
                                                fft_shift=FFT_SHIFT)
        self.write_conlog_entry('pcp_init_tones: waveforms written to roaches.')
                
        return
    
        
        
    
    def sweep_only(self,span,step,start,stop,averaging):

        self.write_conlog_entry(
            'sweep_only: span,step,startidx,stopidx,averages = %s'%
            [span,step,start,stop,averaging])

        self.mclist.sweep_lo(sweep_span = span,
                            sweep_step  = step,
                            startidx    = start,
                            stopidx     = start+averaging, 
                            sweep_avgs  = start+averaging+stop)
        self.write_conlog_entry('sweep_only: %s'%
            ','.join([j.sweep.dirfile.name for j in self.mclist]))
        
        for j in self.mclist: j.sweep.calc_sweep_cal_params(despike_window=5)
        self.write_conlog_entry('sweep_only: update_cal_params: %s'%
            ','.join([j.sweep.dirfile.name for j in self.mclist]))
        
        dirfiles = [j.sweep.dirfile.name for j in self.mclist]
        
            
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
        
        self.write_conlog_entry(
            'sweep_and_place_tones: tone_placement_accuracy_hz = %s'%
            tone_placement_accuracy_hz)
        self.write_conlog_entry(
            'sweep_and_place_tones: search_bw_hz = %s'%
            search_bw_hz)
        self.write_conlog_entry(
            'sweep_and_place_tones: averaging,start,stop = %s %s %s'%
            (averaging,start,stop))
                
        self.sweep_only(search_bw_hz,
                        tone_placement_accuracy_hz,
                        start,
                        stop,
                        averaging)

        
        for j in self.mclist: j.tl.rf_freqs = j.sweep.calparams['f0s']
        self.write_conlog_entry(
            'sweep_and_place_tones: updated toneslists')
        
        self.mclist.call_mc_method_in_parallel('write_freqs_to_fpga',
                                          auto_write=True,
                                          check=False,
                                          useoffsetatt=True,
                                          fft_shift=FFT_SHIFT)
        self.write_conlog_entry(
            'sweep_and_place_tones: waveforms written to roaches.')
        

        return
       
    
    def retune_only(self,search_span = 100000.,
                    search_step = 1000.,
                    search_start = 25, search_stop  = 10,search_avg = 25, 
                    sweep_span = 100000.,
                    sweep_step = 1000.,
                    sweep_start = 25, sweep_stop = 10,sweep_avg  = 25):
        """ Sweep, tune onto resonances, sweep again."""
                
        self.write_conlog_entry('retune:')
            
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
        
        self.write_conlog_entry('retune: %s'%','.join([j.sweep.dirfile.name for j in self.mclist]))


        return




    
    def record_only(self,duration):
        """ Record a timestream."""

        self.write_conlog_entry(
            'record_only: duration = %s'%duration)
        self.mclist.stream_for_duration(duration)

        return
    
    def start_recording(self):


        self.mclist.stream_start()
        self.write_conlog_entry('start_recording: %s'%
                                (','.join([j.current_dirfile.name for j in self.mclist])))
        
    def stop_recording(self):

        self.mclist.stream_stop()
        time.sleep(3)
        self.write_conlog_entry('stop_recording: %s'%
                                (','.join([j.current_dirfile.name for j in self.mclist])))
    
    
    def sweep_and_record(self,duration, span, step,start=25,stop=10, averaging=10):


        """ Sweep and record a timestream, but dont retune."""
        self.write_conlog_entry(
            'sweep_and_record: duration, span, step,start,stop, averaging = %s'%
            [duration, span, step,start,stop, averaging])
        self.sweep_only(span,step,start,stop,averaging)
        self.record_only(duration)
        self.write_conlog_entry('sweep_and_record: done')
                

        return

    def sweep_and_start_recording(self, span, step, start=25,stop=10, averaging=10):
        
        """ Sweep and start record a timestream, no retuning, need to manually stop."""
        self.write_conlog_entry(
            'sweep_and_start_recording: span, step,start,stop, averaging = %s'%
            [span, step,start,stop, averaging])
        self.sweep_only(span,step,start,stop,averaging)
        self.write_conlog_entry('sweep_and_start_recording: started')
        self.start_recording()
        
        return
    

    def retune_and_record(self, 
                        duration,
                        search_span = 100000.,
                        search_step = 1000.,
                        search_start = 25, search_stop  = 10,search_avg = 25,
                        sweep_span = 100000.,
                        sweep_step = 1000.,
                        sweep_start = 25, sweep_stop = 10,sweep_avg  = 25):
        """ Sweep, tune onto resonances, sweep again and record a timestream."""  
        
        self.write_conlog_entry('retune_and_record:')
        
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
        self.write_conlog_entry('retune_and_record: %s'%','.join([j.current_dirfile.name for j in self.mclist]))

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
        
        self.write_conlog_entry('retune_and_start_record:')
        
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
        self.write_conlog_entry('retune_and_start_recording: started%s'%','.join([j.current_dirfile.name for j in self.mclist]))

        return
    
    

    def tune(self):
        self.retune_only()
        
        print 'Done Tuning'
        time.sleep(1)
        return 0

    
def check_sweep_lo_steps(dirfile,kidnum,startidx=25,stopidx=35):
    import pygetdata as gd
    df = gd.dirfile(dirfile,gd.RDONLY)
    z  = df.getdata('K%03d_z'%kidnum)
    lotimes = df.getdata( "lostep_times" )
    ptimes  = df.getdata( "python_timestamp" ) # way to get the python_timestamp field with knowing any field suffix
    lofreqs = df.getdata( "lo_freqs" )

    # align LO steps with python timestreams
    idxs = np.searchsorted(ptimes, lotimes) # miss out the first point (should always be 0)
    plt.figure()
    plt.plot(abs(z))
    [plt.axvline(i,color='k') for i in idxs]
    [plt.axvline(i+startidx,color='g') for i in idxs]
    [plt.axvline(i+stopidx,color='r') for i in idxs]
    plt.title(dirfile + ': K%03d_z'%kidnum)
    plt.show()
    
    





if __name__=='__main__':
    M = MuxController()
    
    
