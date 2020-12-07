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

import muscat_cryo
import muscat_blackbody
import xy_recv

os.chdir('/home/muscat/multitone2020-08-13/roach2pcp/')
#sys.path.append('/home/muscat/multitone2020-08-13/roach2pcp/')
import pcp


#The muscat channels:
ALLCHNUMS = [1,2,3,4,5,6]
ALLNAMES  = ['phantom','clones','sith','hope','empire','jedi']


#The ones we are going to use:
CHNUMS    = [1,2,3,4,5,6]
CHNAMES   = [ALLNAMES[n-1] for n in CHNUMS]
NCHANS    = len(CHNUMS)


#The initial tonelist files:
TL_HALF   = 'a'
TL_DIR    = '/home/muscat/toneslists/tones_20201016/run6_atts/'
TL_FILES    = [TL_DIR+'t%d%c_20201016-130mk-300k.txt'%(ch,TL_HALF) for ch in CHNUMS]
LO_FILES    = [TL_DIR+'lo%d%c.txt'%(ch,TL_HALF) for ch in CHNUMS]
ATTIN_FILES    = [TL_DIR+'attin%d%c_20201016-130mk-300k.txt'%(ch,TL_HALF) for ch in CHNUMS]
DWM_FILES    = [TL_DIR+'dacwavemax%d%c_20201016-130mk-300k.txt'%(ch,TL_HALF) for ch in CHNUMS]


TL_HALF_A   = 'a'
TL_FILES_A    = [TL_DIR+'t%d%c_20201016-130mk-300k.txt'%(ch,TL_HALF_A) for ch in CHNUMS]
LO_FILES_A    = [TL_DIR+'lo%d%c.txt'%(ch,TL_HALF_A) for ch in CHNUMS]
ATTIN_FILES_A    = [TL_DIR+'attin%d%c_20201016-130mk-300k.txt'%(ch,TL_HALF_A) for ch in CHNUMS]
DWM_FILES_A    = [TL_DIR+'dacwavemax%d%c_20201016-130mk-300k.txt'%(ch,TL_HALF_A) for ch in CHNUMS]

TL_HALF_B   = 'b'
TL_FILES_B    = [TL_DIR+'t%d%c_20201016-130mk-300k.txt'%(ch,TL_HALF_B) for ch in CHNUMS]
LO_FILES_B    = [TL_DIR+'lo%d%c.txt'%(ch,TL_HALF_B) for ch in CHNUMS]
ATTIN_FILES_B    = [TL_DIR+'attin%d%c_20201016-130mk-300k.txt'%(ch,TL_HALF_B) for ch in CHNUMS]
DWM_FILES_B   = [TL_DIR+'dacwavemax%d%c_20201016-130mk-300k.txt'%(ch,TL_HALF_B) for ch in CHNUMS]


#The log file names:
CONTROL_LOGFILENAME     ='/data1/obs/conlog.txt'
CONLOG_BACKUP_FILENAME  = '/home/muscat/conlog.txt'
OBSLOG_FILENAME         ='/data1/obs/obslog.txt'
OBSLOG_BACKUP_FILENAME  = '/home/muscat/obslog.txt'
RSYNC_FILENAME         = '/data1/obs/rsync_log.txt'
RSYNC_BACKUP_FILENAME  = '/home/muscat/rsync_log.txt'

#Data backup: copies dirfiles from data dir to backupdir after observations:
OBS_DATA_DIR            = '/data1/muscat/'
OBS_BACKUP_DIR          = '/data2/muscat/'

#Timestamp,LogAction,ObsProgram,ObsNum,SubObsNum,ScanNum,SourceName,Dirfiles  
OBS_DTYPE   = np.dtype([('Timestamp'  ,'|S64'),
                        ('LogAction'  ,'|S64'),
                        ('ObsProgram' ,'|S64'),
                        ('ObsNum'     ,'<i8'),
                        ('SubObsNum'  ,'<i8'),
                        ('ScanNum'    ,'<i8'),
                        ('SourceName' ,'|S64'),
                        ('Dirfiles'   ,'|S512')])


#Highest  temperature in Kelvin before issuing warnings
CRYO_WARNING_TEMP = 0.140
RED = '\033[31m'
RBG = '\033[41m'
END = '\033[0m'


#Miscellanea
FFT_SHIFT = 0b1111111
LOCATION  = 'CARDIFF_LAB'
#LOCATION  = 'LMT_LAB'
#LOCATION  = 'LMT_L29'


class fucking_awesome(object):
    pass


class MuxController(fucking_awesome):
    """
    High level code to perform observations with MUSCAT.
    
    Can be run in an interactive interpreter (eg lab testing),
    or as a part client/server system (eg at telescope)
    """
    def __init__(shit, 
                 cryo      =True,
                 bb =True,
                 xyz       =True,
                 pcp       =True,
                 clfn      =CONTROL_LOGFILENAME,
                 olfn      =OBSLOG_FILENAME):
        
        super(fucking_awesome,shit).__init__()
        self                = shit
        self.olfn           = olfn
        self.clfn           = clfn
        self.cryo           = None
        self.bb      = None
        self.xyz            = None
        self.mclist         = None
        self.stream_flag    = 0
        self.tune_flag      = 0
        
        
        """The muscat controller is starting..."""
        print '\nMae\'r rheolwr MUSCAT yn dechrau...\n'
        
        self.write_conlog_entry('MuxController')
        self.write_conlog_entry('Observation log file location: %s'%self.clfn)
        
        atexit.register(self.shutdown)
   
        if cryo:
            self.cryo_init()
        if bb:
            self.bb_init()
        if xyz:
            self.xyz_init()
        if pcp:
            self.pcp_init_hw(CHNUMS, CHNAMES)
            self.pcp_init_tones(TL_FILES, LO_FILES, ATTIN_FILES, DWM_FILES,
                                extra_attin=0, diff_attinout=14.0)
        return

    def shutdown(self):
        if self.mclist is not None:
            [j.shutdown for j in self.mclist]
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
        
        
        
        
        
    def write_obslog_raw(self,string):
        if not os.path.exists(self.olfn) or os.stat(self.olfn).st_size == 0:
            with open(self.olfn,'a') as lfile:
                lfile.write(' '.join(OBS_DTYPE.names)+'\n')
                lfile.flush()
        
        with open(self.olfn,'a') as lfile:
            lfile.write(string)
            lfile.flush()
        return
    
    def write_obslog_entry(self, 
                           LogAction,ObsProgram,ObsNum,SubObsNum,
                           ScanNum,SourceName,Dirfiles):
        entries = LogAction,ObsProgram,ObsNum,SubObsNum,ScanNum,SourceName,Dirfiles
        t       = datetime.datetime.utcnow().isoformat()
        line    = ' '.join([t]+[str(i) for i in entries])+'\n'
        print line
        self.write_obslog_raw(line)
        os.system('cp %s %s'%(self.olfn, self.olfn+'.bak'))
        os.system('cp %s %s'%(self.olfn, OBSLOG_BACKUP_FILENAME))
        return
        
    def get_obslog_entries(self,obsnum=None,subobsnum=None,scannum=None,sourcename=None,logaction='CLOSE'):
        if not os.path.exists(self.olfn):
            self.write_obslog_raw('')
        log = np.genfromtxt(self.olfn,unpack=True,dtype=OBS_DTYPE,skip_header=1)
        entries = log[log['LogAction']==logaction]
        
        if obsnum is not None:
            entries = entries[entries['ObsNum']==obsnum]
        if subobsnum is not None:
            entries = entries[entries['SubObsNum']==subobsnum]
        if scannum is not None:
            entries = entries[entries['ScanNum']==scannum]
        if sourcename is not None:
            entries = entries[entries['SourceName']==sourcename]
        if sourcename is not None:
            entries = entries[entries['SourceName']==sourcename]
        print entries
        return entries
        
            
    def get_dirfiles_from_obslog(self,obsnum,subobsnum=None,scannum=None,sourcename=None):
        entries = self.get_obslog_entries(obsnum,subobsnum,scannum,sourcename)
        return [i.split(',') for i in entries['Dirfiles']], entries
        
            
            
            
    def get_new_obsnum(self):
        if not os.path.exists(self.olfn):
            self.write_obslog_raw('')
        log = np.genfromtxt(self.olfn,unpack=True,dtype=OBS_DTYPE,skip_header=1)
        obsnum=0
        while True:
            obsnum+=1
            if obsnum in log['ObsNum']:
                continue
            else:
                break
        return obsnum
   
    def get_new_subobsnum(self,obsnum):
        if not os.path.exists(self.olfn):
            self.write_obslog_raw('')
        log = np.genfromtxt(self.olfn,unpack=True,dtype=OBS_DTYPE,skip_header=1)
        existing_subobsnums = log['SubObsNum'][log['ObsNum']==obsnum]
        largest_subobsnum = np.append(existing_subobsnums,0).max()
        return largest_subobsnum + 1
        




    def obs_open(self, obspgm, obsnum=None,subobsnum=None,scannum=None,sourcename=None):
        if obsnum is None:
            obsnum = self.get_new_obsnum()
        if subobsnum is None:
            subobsnum = self.get_new_subobsnum(obsnum)
        if scannum is None:
            scannum=-1
        if sourcename is None:
            sourcename is 'no_sourcename'
        self.write_obslog_entry('OPEN ',obspgm,obsnum,subobsnum,scannum,sourcename,',,,,,')
        return obspgm,obsnum,subobsnum,scannum,sourcename
            
    def obs_close(self, obspgm, obsnum, subobsnum, scannum,sourcename,dirfiles):
        dfstring = ','.join(dirfiles)
        self.write_obslog_entry('CLOSE',obspgm,obsnum,subobsnum,scannum,sourcename,dfstring)
        
        return
    
    
    
    
    
    def backup_obs(self, dirfiles,obspgm,obsnum,subobsnum,scannum,sourcename,datadir=None, backupdir=None):
        if datadir is None:
            datadir = OBS_DATA_DIR
        if backupdir is None:
            backupdir = OBS_BACKUP_DIR
        
        sources     = [f.replace(datadir,'') for f in dirfiles]
        destination = backupdir 
        
        echo1 = 'echo "RSYNC STARTING IN BACKGROUND"'
        cd    = 'cd %s'%datadir
        rsync = 'rsync -RKLrptgoDz %s %s'%(' '.join(sources),destination)
        echo2 = 'echo "RSYNC FINISHED. "'
        done1  = 'echo "%s %d %d %d %s" > %s'%(
            obspgm,obsnum,subobsnum,scannum,sourcename,RSYNC_FILENAME)
        done2  = 'echo "%s %d %d %d %s" > %s'%(
            obspgm,obsnum,subobsnum,scannum,sourcename,RSYNC_BACKUP_FILENAME)
        
        cmd = '%s && %s && %s && %s && %s && %s &'%(echo1,cd,rsync,echo2,done1, done2)
        os.system(cmd)
        self.write_conlog_entry('backup_obs: backup initiated, destinations: %s'%
                                ([j.replace(datadir, backupdir) for j in dirfiles]))

    
    
    
    
    def cryo_init(self):
        """load the cryo class to read the base temperaature"""
        self.cryo = muscat_cryo.muscat_cryo()
        live      = self.cryo.check_livefile_exists()
        log       = self.cryo.check_log_exists(time.time())
        temp      = self.cryo_base_temperature()       
        
        self.write_conlog_entry('cryo_init: livefile = %s'%(self.cryo.live_name))
        self.write_conlog_entry('cryo_init: logfile = %s'%(log))
        self.write_conlog_entry('cryo_init: base temperature = %.4f'%(temp))
        return
        
    def cryo_base_temperature(self):
        """print and return the base tempoerature"""
        if self.cryo.check_livefile_exists():
            mct   = self.cryo.base_temperature()
            if mct < CRYO_WARNING_TEMP:
                print 'MUSCAT BASE TEMPERATURE OK: %f K'%mct
                self.write_conlog_entry('cryo_base_temperature: %.4f'%mct)
            else:
                for j in range(5):
                    print (RED + 20*' '+'WARNING BASE TEMPERATURE HIGH: %.4f K'%
                           mct + 20*' '+ END)
                    print (RBG + 20*' '+'WARNING BASE TEMPERATURE HIGH: %.4f K'%
                           mct + 20*' '+ END)
                self.write_conlog_entry(
                'cryo_base_temperature: over-temperature warning: %.4f>%.4f'%
                (mct,CRYO_WARNING_TEMP))
            return mct
        else:
            for j in range(5):
                    print (RBG + 20*' '+'CANNOT READ TEMPERATURE LIVEFILE ' + 20*' '+ END)
                    print (RBG + self.cryo.livefile_name + END)

            self.write_conlog_entry('cryo_base_temperature: cannot read livefile:'
                +self.cryo.livefile_name)
            
            return -9999.9999
        
        
        
    def add_cryo_log_to_dirfiles(self,
                                 dirfiles,
                                 thermometers=['MC_2_Cald']):
        for d in dirfiles:
            df      = gd.dirfile(d,gd.RDWR)
            pyts    = df.getdata('python_timestamp')
            ts_int  = np.linspace(pyts.min(),pyts.max(),df.nframes)
            
            for tname in thermometers:
                t = self.cryo.get_temperature_interpolated(ts_int,
                                                           interp_method='previous', thermometer_name=tname, ret_time=False)
                entry   = gd.entry(gd.RAW_ENTRY, 
                                   "CRYOLOG_"+tname,
                                   0,
                                   (gd.FLOAT64, 1) )
                df.add(entry)
                df.putdata("CRYOLOG_"+tname, t)
            df.close()
        self.write_conlog_entry('add_cryo_log_to_dirfile: Done')


        
        
    def bb_init(self):
        """load the bb class to read the bb temperaatures"""
        self.bb = muscat_blackbody.muscat_blackbody()
        log       = self.bb.check_log_exists(time.time())
        temp      = self.bb_temperatures()       
        
        self.write_conlog_entry('bb_init: logfile = %s'%(log))
        self.write_conlog_entry('bb_init: (center,edge) = (%.3f, %.3f) K'%
                                (temp[0],temp[1]))
        return
    
    def bb_temperatures(self):
        """load the bb class to read the bb temperaatures"""
        t1=self.bb.get_last_t_centre()
        t2=self.bb.get_last_t_edge()
        self.write_conlog_entry('bb_temperatures: (center,edge) = (%.3f, %.3f) K'%
                                (t1,t2))

        return np.array([t1,t2])

    def add_bb_log_to_dirfiles(self,
                                      dirfiles,
                                      thermometers=['T_centre_K','T_edge_K']):
        for d in dirfiles:
            df      = gd.dirfile(d,gd.RDWR)
            pyts    = df.getdata('python_timestamp')
            ts_int  = np.linspace(pyts.min(),pyts.max(),df.nframes)
            
            for tname in thermometers:
                t = self.bb.get_temperature_interpolated(ts_int,
                                                           interp_method='previous', thermometer_name=tname, ret_time=False)
                entry   = gd.entry(gd.RAW_ENTRY, 
                                   "BB_"+tname,
                                   0,
                                   (gd.FLOAT64, 1) )
                df.add(entry)
                df.putdata("BB_"+tname, t)
            df.close()
        self.write_conlog_entry('add_bb_log_to_dirfile: Done')
        
    def add_bb_temperature_to_sweep_dir(self,
                                              sweep_dirfiles,
                                              thermometers=['T_centre_K','T_edge_K']):

        tc,te = self.bb.get_last_t_centre(), self.bb.get_last_t_edge()
        for j in sweep_dirfiles:
            with open(j+'/BB_TEMP_CENTRE.txt','a') as file:
                file.write('%.3f\n'%(tc))
            with open(j+'/BB_TEMP_EDGE.txt','a') as file:
                file.write('%.3f\n'%(te))
        self.write_conlog_entry('add_bb_temperature_to_sweep_dir: Done: %.1f %.1f'%
                                (tc,te))

        
                  
            
    
    
    
    def xyz_init(self,home=False):
        self.xyz = xy_recv.xyz_controller(printing = True)
        if home: 
            self.xyz.goto_home()
            self.write_conlog_entry('xyz_init: configured and homed.')
        else:
            self.write_conlog_entry('xyz_init: configured but not homed.')
        return
    
    def add_xyz_log_to_dirfiles(self, dirfiles, xyz_outfile):
        for d in dirfiles:
            df = gd.dirfile(d,gd.RDWR)
            pyts = df.getdata('python_timestamp')
            #ts_int  = np.linspace(pyts.min(),pyts.max(),df.nframes)

            isc,ix,iy,iz,its,ilt = self.xyz.interpolate_xy_outfile(xyz_outfile,pyts)
            names = ['XYZ_'+n for n in ['SCANNING','X','Y','Z','SCANNERTIME','LOCALTIME']]
            for arr, name in zip([isc,ix,iy,iz,its,ilt],names):
                entry   = gd.entry(gd.RAW_ENTRY,name,0,(gd.FLOAT64, 1) )
                df.add(entry)
                df.putdata(name, arr)
            df.close()
            for d in dirfiles:
                os.system('cp %s %s'%(xyz_outfile,d))
        self.write_conlog_entry('add_bb_log_to_dirfile: Done')

    
    
    
    
    
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
    
    
    
    
    def pcp_init_tones_a(self,extra_attin=[0]*6,diff_attinout=14):
        self.pcp_init_tones(TL_FILES_A,LO_FILES_A,ATTIN_FILES_A,DWM_FILES_A,
                            extra_attin,diff_attinout)
        
    def pcp_init_tones_b(self,extra_attin=[0]*6,diff_attinout=14):
        self.pcp_init_tones(TL_FILES_B,LO_FILES_B,ATTIN_FILES_B,DWM_FILES_B,
                            extra_attin,diff_attinout)
        
    
    def pcp_init_tones(self, tl_files, lo_files, attin_files, dwm_files,
                       extra_attin=[0]*6, 
                       diff_attinout=14):    
        """init the toneslists in the pcp mux channles"""
        
        self.mclist.init_toneslists(tl_files, lo_files, attin_files,
                                    dwm_files,
                                    extra_attin=extra_attin,
                                    diff_attinout=diff_attinout)
        
        self.write_conlog_entry('pcp_init_tones: tl_files = %s'%tl_files)
        self.write_conlog_entry('pcp_init_tones: lo_files = %s'%lo_files)
        self.write_conlog_entry('pcp_init_tones: attin_files = %s'%attin_files)
        self.write_conlog_entry('pcp_init_tones: dwm_files = %s'%dwm_files)
        self.write_conlog_entry('pcp_init_tones: extra_attin = %s'%extra_attin)
        self.write_conlog_entry('pcp_init_tones: diff_attinout = %s'%diff_attinout)

        self.mclist.call_mc_method_in_parallel('write_freqs_to_fpga',
                                                auto_write=True,
                                                check=False,
                                                useoffsetatt=True,
                                                fft_shift=FFT_SHIFT)
        self.write_conlog_entry('pcp_init_tones: waveforms written to roaches.')
                
        return
    
        
        
    
    def sweep_only(self,span,step,start,stop,averaging,
                   obsnum=None,subobsnum=None,scannum=None,sourcename=None, obs=False):
        if obs:
            obspgm,obsnum,subobsnum,scannum,sourcename = self.obs_open('sweep_only',
                obsnum,subobsnum,scannum,sourcename)
            

        self.write_conlog_entry(
            'sweep_only: span,step,startidx,stopidx,averages = %s'%
            [span,step,start,stop,averaging])
        self.cryo_base_temperature()

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
        if self.bb: self.add_bb_temperature_to_sweep_dir(dirfiles)
        
        if obs:
            self.obs_close(obspgm, obsnum, subobsnum, scannum,sourcename,dirfiles)
            self.backup_obs(dirfiles,obspgm, obsnum,subobsnum,scannum,sourcename)
            
        return
    
        
    def search_for_resonances(self):
        """wide ranging sweep to find resoances"""
        self.cryo_base_temperature()
        #Some new code here
        self.write_conlog_entry('search_for_resonances: not implemented')
        return
         
        
    def sweep_and_place_tones(self,
                              search_bw_hz               = 100000.,
                              tone_placement_accuracy_hz = 1000.,
                              start = 25,stop  = 10,averaging = 25,
                              obsnum=None,subobsnum=None,scannum=None,sourcename=None,
                              obs=False):
        """Only sets tones, still have to sweep before recording 
        Want this to be fast. Keep numbers low.
        #averages = 10 # pcp might fail if avergaing is less than 10
        #start    = 25 samples to wait at start. Do not set this lower than 25
        #stop     = 10 samples to wait at end. Don not set this lower than 10"""
        if obs:
            obspgm,obsnum,subobsnum,scannum,sourcename = self.obs_open('sweep_and_place_tones',
                obsnum,subobsnum,scannum,sourcename)
         
        
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
        
        if obs:
            dirfiles = [j.sweep.dirfile.name for j in self.mclist]
            self.obs_close(obspgm, obsnum, subobsnum, scannum,sourcename,dirfiles)
            self.backup_obs(dirfiles,obspgm, obsnum,subobsnum,scannum,sourcename)

        return
       
    
    def retune_only(self,search_span = 100000.,
                    search_step = 1000.,
                    search_start = 25, search_stop  = 10,search_avg = 25, 
                    sweep_span = 100000.,
                    sweep_step = 1000.,
                    sweep_start = 25, sweep_stop = 10,sweep_avg  = 25,
                    obsnum=None,subobsnum=None,scannum=None,sourcename=None, 
                    obs=False):
        """ Sweep, tune onto resonances, sweep again."""
        if obs:
            obspgm,obsnum,subobsnum,scannum,sourcename = self.obs_open('retune_only',
                obsnum,subobsnum,scannum,sourcename)
                
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

        if obs:
            dirfiles = [j.sweep.dirfile.name for j in self.mclist]
            self.obs_close(obspgm, obsnum, subobsnum, scannum,sourcename,dirfiles)
            self.backup_obs(dirfiles,obspgm, obsnum,subobsnum,scannum,sourcename)

        return




    
    def record_only(self,duration,
                    obsnum=None,subobsnum=None,scannum=None,sourcename=None,
                    obs=False):
        """ Record a timestream."""
        if obs:
            obspgm,obsnum,subobsnum,scannum,sourcename = self.obs_open('record_only',
                obsnum,subobsnum,scannum,sourcename)

        self.write_conlog_entry(
            'record_only: duration = %s'%duration)
        self.cryo_base_temperature()
        self.mclist.stream_for_duration(duration)

        if obs:
            dirfiles = [j.current_dirfile.name for j in self.mclist]
            self.obs_close(obspgm, obsnum, subobsnum, scannum,sourcename,dirfiles)
            self.add_cryo_log_to_dirfiles(dirfiles,thermometers=['MC_2_Cald'])
            if self.bb: self.add_bb_log_to_dirfiles(dirfiles)
            self.backup_obs(dirfiles,obspgm, obsnum,subobsnum,scannum,sourcename)
        return
    
    def start_recording(self,
                        obsnum=None,subobsnum=None,scannum=None,sourcename=None,
                        obs=False):
        if obs:
            obspgm,obsnum,subobsnum,scannum,sourcename = self.obs_open('start_recording',
                obsnum,subobsnum,scannum,sourcename)

        self.cryo_base_temperature()
        self.mclist.stream_start()
        self.write_conlog_entry('start_recording: %s'%
                                (','.join([j.current_dirfile.name for j in self.mclist])))
        
    def stop_recording(self,
                       obsnum=None,subobsnum=None,scannum=None,sourcename=None,
                       obs=False):
        self.mclist.stream_stop()
        time.sleep(3)
        self.write_conlog_entry('stop_recording: %s'%
                                (','.join([j.current_dirfile.name for j in self.mclist])))
        self.cryo_base_temperature()
        if obs:
            dirfiles = [j.current_dirfile.name for j in self.mclist]
            self.obs_close(obspgm, obsnum, subobsnum, scannum,sourcename,dirfiles)
            self.add_cryo_log_to_dirfiles(dirfiles,thermometers=['MC_2_Cald'])
            if self.bb: self.add_bb_log_to_dirfiles(dirfiles)
            self.backup_obs(dirfiles,obspgm, obsnum,subobsnum,scannum,sourcename)

        
        
    
    
    def sweep_and_record(self,duration, span, step,start=25,stop=10, averaging=10,
                        obsnum=None,subobsnum=None,scannum=None,sourcename=None,
                        obs=False):
        if obs:
            obspgm,obsnum,subobsnum,scannum,sourcename = self.obs_open('sweep_and_record',
                obsnum,subobsnum,scannum,sourcename)

        """ Sweep and record a timestream, but dont retune."""
        self.write_conlog_entry(
            'sweep_and_record: duration, span, step,start,stop, averaging = %s'%
            [duration, span, step,start,stop, averaging])
        self.sweep_only(span,step,start,stop,averaging)
        self.record_only(duration)
        self.write_conlog_entry('sweep_and_record: done')
                
        if obs:
            dirfiles = [j.current_dirfile.name for j in self.mclist]
            self.obs_close(obspgm, obsnum, subobsnum, scannum,sourcename,dirfiles)
            self.add_cryo_log_to_dirfiles(dirfiles,thermometers=['MC_2_Cald'])
            if self.bb: self.add_bb_log_to_dirfiles(dirfiles)
            self.backup_obs(dirfiles,obspgm, obsnum,subobsnum,scannum,sourcename)

        return

    def sweep_and_start_recording(self, span, step, start=25,stop=10, averaging=10,
                                  obsnum=None,subobsnum=None,scannum=None,sourcename=None,
                                  obs=False):
        if obs:
            obspgm,obsnum,subobsnum,scannum,sourcename = self.obs_open('sweep_and_start_recording',
                obsnum,subobsnum,scannum,sourcename)
        
        """ Sweep and start record a timestream, no retuning, need to manually stop."""
        self.write_conlog_entry(
            'sweep_and_start_recording: span, step,start,stop, averaging = %s'%
            [span, step,start,stop, averaging])
        self.sweep_only(span,step,start,stop,averaging)
        self.write_conlog_entry('sweep_and_start_recording: started')
        return
        self.start_recording()
    

    def retune_and_record(self, 
                        duration,
                        search_span = 100000.,
                        search_step = 1000.,
                        search_start = 25, search_stop  = 10,search_avg = 25,
                        sweep_span = 100000.,
                        sweep_step = 1000.,
                        sweep_start = 25, sweep_stop = 10,sweep_avg  = 25,
                        obsnum=None,subobsnum=None,scannum=None,sourcename=None,
                        obs=False):
        """ Sweep, tune onto resonances, sweep again and record a timestream."""  
        if obs:
            obspgm,obsnum,subobsnum,scannum,sourcename = self.obs_open('sweep_and_record',
                obsnum,subobsnum,scannum,sourcename)
        
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
        if obs:
            dirfiles = [j.current_dirfile.name for j in self.mclist]
            self.obs_close(obspgm, obsnum, subobsnum, scannum,sourcename,dirfiles)
            self.add_cryo_log_to_dirfiles(dirfiles,thermometers=['MC_2_Cald'])
            if self.bb: self.add_bb_log_to_dirfiles(dirfiles)
            self.backup_obs(dirfiles,obspgm, obsnum,subobsnum,scannum,sourcename)

        return
    
    def retune_and_start_recording(self, 
                        search_span = 100000.,
                        search_step = 1000.,
                        search_start = 25, search_stop  = 10,search_avg = 25,
                        sweep_span = 100000.,
                        sweep_step = 1000.,
                        sweep_start = 25, sweep_stop = 10,sweep_avg  = 25,
                        obsnum=None,subobsnum=None,scannum=None,sourcename=None,
                        obs=False):
        """ Sweep, tune onto resonances, sweep again and 
        start recording a timestream, need to stop manually."""
        if obs:
            obspgm,obsnum,subobsnum,scannum,sourcename = self.obs_open('retune_and_start_recording',
                obsnum,subobsnum,scannum,sourcename)

        
        
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
        if obs:
            dirfiles = [j.current_dirfile.name for j in self.mclist]
            self.obs_close(obspgm, obsnum, subobsnum, scannum,sourcename,dirfiles)
            self.add_cryo_log_to_dirfiles(dirfiles,thermometers=['MC_2_Cald'])
            if self.bb: self.add_bb_log_to_dirfiles(dirfiles)
            self.backup_obs(dirfiles,obspgm, obsnum,subobsnum,scannum,sourcename)
        return
    
    
    def xyz_beam_map(self,xmin,xmax,ymin,ymax,ysteps,xyz_outfile=None,
                     obsnum=None,subobsnum=None,scannum=None,sourcename=None,
                     obs=False):
        if obs:
            obspgm,obsnum,subobsnum,scannum,sourcename = self.obs_open('xyz_beam_map',
                obsnum,subobsnum,scannum,sourcename)
        self.write_conlog_entry('xyz_beam_map: xmin,xmax,ymin,ymax,ysteps,outfile:%s'%
                                ([xmin,xmax,ymin,ymax,ysteps,xyz_outfile]))
        self.start_recording()
        time.sleep(3)
        xyz_outfile = self.xyz.scan_and_log(xmin,xmax,ymin,ymax,ysteps,
                                            outfile=xyz_outfile)
        #os.system(xyz)
        self.write_conlog_entry('xyz_beam_map: scan finished,xyz_outfile:%s'%xyz_outfile)
        self.stop_recording()
        self.write_conlog_entry('xyz_beam_map: stopped recording. %s'%
                                (','.join([j.current_dirfile.name for j in self.mclist])))
        
        dirfiles = [j.current_dirfile.name for j in self.mclist]
        
        self.add_xyz_log_to_dirfiles(dirfiles, xyz_outfile)
        
        if obs:
            self.obs_close(obspgm, obsnum, subobsnum, scannum,sourcename,dirfiles)
            self.add_cryo_log_to_dirfiles(dirfiles,thermometers=['MC_2_Cald'])
            if self.bb: self.add_bb_log_to_dirfiles(dirfiles)
            self.backup_obs(dirfiles,obspgm, obsnum,subobsnum,scannum,sourcename)
        return
    


    def nep_measurement(self):
        "do something"
        log
        return
    
    
    def fts_measurement(self):
        "do something"
        log
        return
    
    
    

    
    
    
    
    def needs_tune(self):
        """ Find out how far off resonance we are."""
        self.cryo_base_temperature()
        #new code here
        #check df value from dirfiles versus q factors from sweep
        #(add estimated qfactors in mclist.mc.sweep)
        #even better, measure loss in NEP with detuning for each resonator
        #need responsivity of each detector and noise 
        return        
        


    def PGMMap(self,obsnum,subobsnum,scannum,sourcename,obspgm):
        
        obsdir = os.path.join('/data1/obs/',str(obsnum),str(scannum))
        if not os.path.exists(obsdir): os.makedirs(obsdir)
        print '*********',obsdir
        
        

        self.write_obslog('OPEN %s %s %s %s\n'%(obspgm,obsnum,scannum,obsdir))
        print '*********',t
        
        #add all metadata
        
        print 'obs dir:',obsdir
        self.ch.start_stream(dont_ask=True)
        while self.stream_flag:
            time.sleep(1)
            
        self.ch.stop_stream()
        
        #print 'stream_flag=0: writing_data: %s %s'%(self.ch.current_dirfile.name,obsdir)
        
        copycmd='cp -rL %s %s'%(self.ch.current_dirfile.name,obsdir)
        print copycmd
        os.system(copycmd)
        
        self.write_obslog('CLOSED %s %s %s %s\n'%(obspgm,obsnum,scannum,obsdir))
        
        
        print 'Done PGMMap'

        return 0
    
    
    def PGMLissajous(self,obsnum,subobsnum,scannum,sourcename,obspgm):
        obsdir = os.path.join('/data1/obs/',str(obsnum),str(scannum))
        if not os.path.exists(obsdir): os.makedirs(obsdir)

        self.write_obslog('OPEN %s %s %s %s\n'%(obspgm,obsnum,scannum,obsdir))
        
        print 'obs dir:',obsdir

        self.ch.start_stream(dont_ask=True)
        while self.stream_flag:
            time.sleep(1)
        self.ch.stop_stream()
        
        copycmd='cp -rL %s %s'%(self.ch.current_dirfile.name,obsdir)
        print copycmd
        os.system(copycmd)        

        self.write_obslog('CLOSED %s %s %s %s\n'%(obspgm,obsnum,scannum,obsdir))
        
        return 0

    
    
    def PGMSkydip(self,obsnum,subobsnum,scannum,sourcename,obspgm):
        """a skydip consists of a number of sweeps versus elevation.
        pgmskydip performs one sweep and closes, the tcs will request multiple pgmskydips and rsync the pointing file for each skydip"""
        print '0000000 in skydip'

        obsdir = os.path.join('/data1/obs/',str(obsnum),str(scannum))
        print '*****obsdir',obsdir
        
        if not os.path.exists(obsdir): os.makedirs(obsdir)
        print '++++++obsdir',obsdir
        self.write_obslog('%s OPEN %s %s %s %s\n'%(t,obspgm,obsnum,scannum,obsdir))    

        print '------obs dir:',obsdir

        self.ch.sweep_lo(sweep_avgs=20,
                               startidx=10,
                               sweep_step = 500,
                               sweep_span = 45e3)
        
        
        copycmd='cp -rL %s %s'%(self.ch.current_dirfile.name,obsdir)
        print copycmd
        os.system(copycmd)        
        
        self.write_obslog('CLOSED %s %s %s %s\n'%(obspgm,obsnum,scannum,obsdir))
        
        return 0
    
    
    
    
    def PGMOn(self,obsnum,subobsnum,scannum,sourcename,obspgm):
        obsdir = os.path.join('/data1/obs/',str(obsnum),str(scannum))
        if not os.path.exists(obsdir): os.makedirs(obsdir)

        self.write_obslog('OPEN %s %s %s %s\n'%(obspgm,obsnum,scannum,obsdir))
        
        print 'obs dir:',obsdir

        self.ch.start_stream(dont_ask=True)
        while self.stream_flag:
            time.sleep(1)
        self.ch.stop_stream()
        
        copycmd='cp -rL %s %s'%(self.ch.current_dirfile.name,obsdir)
        print copycmd
        os.system(copycmd)        
        
        self.write_obslog('CLOSED %s %s %s %s\n'%(obspgm,obsnum,scannum,obsdir))
        
        return 0
    
    

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
    
    