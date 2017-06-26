# This software is a work in progress. It is a console interface designed 
# to operate the BLAST-TNG ROACH2 firmware. 
#
# Copyright (C) May 23, 2016  Gordon, Sam <sbgordo1@asu.edu>
# Author: Gordon, Sam <sbgordo1@asu.edu>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import matplotlib, time, struct
import numpy as np
import shutil
np.set_printoptions(threshold=np.nan)
#matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import casperfpga 
from myQdr import Qdr as myQdr
import types
import logging
import glob  
import os
import sys
import valon_synth
from socket import *
from scipy import signal
import find_kids_superspec as fk 

class roachInterface(object):
    
    def __init__(self):
	self.center_freq = 2175.0e6  # this is the LO frequency in MHz
	self.v1 = valon_synth.Synthesizer('/dev/ttyUSB0')
	self.v1.set_frequency(8,512.0,0.01) # Clock 
	self.v1.set_frequency(0,2000.0,0.01) # LO
        self.lo_step = 2.5e3
	self.ip = '192.168.40.64'
	self.fpga = casperfpga.katcp_fpga.KatcpFpga(self.ip,timeout=120.) 
        self.dds_shift = 305  # this is a number specific to the firmware used. It will change with a new firmware. 
	self.dac_samp_freq = 512.0e6
        self.fpga_samp_freq = 256.0e6
	self.zeros = signal.firwin(29, 10.0e3, window='hanning',nyq = 0.5*self.fpga_samp_freq)[1:-1]
	#self.zeros = signal.remez(27, [0, 10.0e3, 10.0e3 + 1.0e3, 0.5*self.fpga_samp_freq],[1,0], Hz = self.fpga_samp_freq)
	neg_freqs, self.neg_delta = np.linspace(-245.001234e6 + 3.1123e4, -10.02342e6 + 3.1123e4, 500, retstep = True)
	pos_freqs, self.pos_delta = np.linspace(10.02342e6, 245.001234e6, 500, retstep = True)
	self.test_comb = np.concatenate((neg_freqs, pos_freqs))
	self.test_comb = np.array([50.00])*1.0e6
	self.test_comb = self.test_comb[ self.test_comb != 0]
	self.test_comb = np.roll(self.test_comb, - np.argmin(np.abs(self.test_comb)) - 1)
	self.chan_freqs = np.sort(self.test_comb/1.0e6  + self.center_freq)
	self.LUTbuffer_len = 2**21
        self.dac_freq_res = 2*self.dac_samp_freq/self.LUTbuffer_len
        self.fft_len = 1024
        self.accum_len = (2**19) 
        self.accum_freq = self.fpga_samp_freq/(self.accum_len - 1)
	self.s = socket(AF_PACKET, SOCK_RAW, htons(3))
        self.s.setsockopt(SOL_SOCKET, SO_RCVBUF, 8192 + 42)
	self.s.bind(('enp0s31f6', 3))
        self.main_prompt = '\n\t\033[33mKID-PY ROACH2 Readout\033[0m\n\t\033[35mChoose number and press Enter\033[0m'
        self.main_opts= ['Initialize','Write test comb', 'Write saved bb freqs','Print packet info to screen (UDP)','VNA sweep and plot','Locate resonances','Target sweep and plot', 'Plot channel phase PSD (quick look)','Plot channel amp PSD (quick look)', 'Save dirfile for all channels (I, Q, phase)', 'Save dirfile for all channels using centered phase (I, Q, phase)','Exit'] 
    	
    def lpf(self, zeros):
	zeros *=(2**31 - 1)
	for i in range(len(zeros)/2 + 1):
		coeff = np.binary_repr(int(zeros[i]), 32)
		coeff = int(coeff, 2)
		print 'b' + str(i + 1), coeff	
		self.fpga.write_int('b'+str(i + 1),coeff)
	return 

    def upload_fpg(self):
        print 'Connecting to ROACHII on',self.ip,'...'
        t1 = time.time()
        timeout = 10
        while not self.fpga.is_connected():
                if (time.time()-t1) > timeout:
                    raise Exception("Connection timeout to roach")
        time.sleep(0.1)
        if (self.fpga.is_connected() == True):
            print 'Connection established'
            self.fpga.upload_to_ram_and_program(self.bitstream)
        else:
                print 'Not connected to the FPGA'
        print 'Uploaded', self.bitstream
        time.sleep(3)
        return

    def qdrCal(self):    
    # Calibrates the QDRs. Run after writing to QDR.      
        self.fpga.write_int('dac_reset',1)
        print 'DAC on'
        bFailHard = False
        calVerbosity = 1
        qdrMemName = 'qdr0_memory'
        qdrNames = ['qdr0_memory','qdr1_memory']
        print 'Fpga Clock Rate =',self.fpga.estimate_fpga_clock()
        self.fpga.get_system_information()
        results = {}
        for qdr in self.fpga.qdrs:
            print qdr
            mqdr = myQdr.from_qdr(qdr)
            results[qdr.name] = mqdr.qdr_cal2(fail_hard=bFailHard,verbosity=calVerbosity)
        print 'qdr cal results:',results
        for qdrName in ['qdr0','qdr1']:
            if not results[qdr.name]:
                print 'Calibration Failed'
                break

    # calibrates QDR and initializes GbE block
    def initialize(self):
        self.v1 = valon_synth.Synthesizer('/dev/ttyUSB0')
	self.dest_ip  = 192*(2**24) + 168*(2**16) + 41*(2**8) + 2 # Set to FPGA IP in /etc/network/interfaces
        self.fabric_port= 60000 
        self.fpga.write_int('tx_destip',self.dest_ip)
        self.fpga.write_int('tx_destport',self.fabric_port)
        self.fpga.write_int('sync_accum_len', self.accum_len - 1)
        self.accum_freq = self.fpga_samp_freq / self.accum_len # FPGA clock freq / accumulation length    
	self.fpga.write_int('fft_shift', 2**8 -1)    
        if len(self.test_comb) > 1:
		self.fpga.write_int('fft_shift', 2**5 -1)    
        self.fpga.write_int('dds_shift', self.dds_shift)
        #self.lpf(self.zeros)
	#self.save_path = '/mnt/iqstream/'
	self.qdrCal()
	self.initialize_GbE()
        print '\n************ QDR Calibrated ************'
        print '************ Packet streaming activated ************\n'
    
    def rudinshapiro(self, N):
    	"""
    	Return first N terms of Rudin-Shapiro sequence
   	https://en.wikipedia.org/wiki/Rudin-Shapiro_sequence
        Confirmed correct output to N = 10000:
        https://oeis.org/A020985/b020985.txt
        """
    	def hamming(x):
        	"""
        	Hamming weight of a binary sequence
        	http://stackoverflow.com/a/407758/125507
        	"""
        	return bin(x).count('1')
    
   	out = np.empty(N, dtype=int)
    	for n in xrange(N):
        	b = hamming(n << 1 & n)
        	a = (-1)**b
        	out[n] = a
	return out	
    
    def fft_bin_index(self, freqs, fft_len, samp_freq):
    # returns the fft bin index for a given frequency, fft length, and sample frequency
        bin_index = np.round((freqs/samp_freq)*fft_len).astype('int')
        return bin_index

    def read_mixer_snaps(self, shift, chan, mixer_out = True):
    # returns snap data for the dds mixer inputs and outputs
        self.fpga.write_int('dds_shift', shift)
        if (chan % 2) > 0: # if chan is odd
            self.fpga.write_int('chan_select', (chan - 1) / 2)
        else:
            self.fpga.write_int('chan_select', chan/2)
        self.fpga.write_int('rawfftbin_ctrl', 0)
        self.fpga.write_int('mixerout_ctrl', 0)
        self.fpga.write_int('rawfftbin_ctrl', 1)
        self.fpga.write_int('mixerout_ctrl', 1)
        mixer_in = np.fromstring(self.fpga.read('rawfftbin_bram', 16*2**10),dtype='>i2').astype('float')
        mixer_in /= 2.0**15
        if mixer_out:
            mixer_out = np.fromstring(self.fpga.read('mixerout_bram', 8*2**10),dtype='>i2').astype('float')
            mixer_out /= 2.0**14
            return mixer_in, mixer_out
        else:
            return mixer_in

    def return_shift(self, chan):
    # Returns the dds shift
        dds_spec = np.abs(np.fft.rfft(self.I_dds[chan::self.fft_len],self.fft_len))
        dds_index = np.where(np.abs(dds_spec) == np.max(np.abs(dds_spec)))[0][0]
        print 'Finding LUT shift...' 
        for i in range(self.fft_len/2):
            print i
            mixer_in = self.read_mixer_snaps(i, chan, mixer_out = False)
            I0_dds_in = mixer_in[2::8]    
       	    print I0_dds_in[:100]
            #I0_dds_in[np.where(I0_dds_in > 32767.)] -= 65535.
            snap_spec = np.abs(np.fft.rfft(I0_dds_in,self.fft_len))
            snap_index = np.where(np.abs(snap_spec) == np.max(np.abs(snap_spec)))[0][0]
            if dds_index == snap_index:
                print 'LUT shift =', i
		shift = i
                break
        return shift

    def freq_comb(self, freqs, samp_freq, resolution, random_phase = True, DAC_LUT = True):
    # Generates a frequency comb for the DAC or DDS look-up-tables. DAC_LUT = True for the DAC LUT. Returns I and Q 
        freqs = np.round(freqs/self.dac_freq_res)*self.dac_freq_res
	amp_full_scale = (2**15 - 1)
        if DAC_LUT:
	    fft_len = self.LUTbuffer_len
            bins = self.fft_bin_index(freqs, fft_len, samp_freq)
	    if random_phase == True:
	    	np.random.seed()
            	phase = np.random.uniform(0., 2.*np.pi, len(bins))
	    else: 
   		phase = -np.pi*self.rudinshapiro(len(self.test_comb))
		phase[phase == -np.pi] = 0	 
	    #for i in range(len(freqs)/2):
	    #	phase[999 - i] = -1.*(phase[i] + np.pi/4.)
	    self.amps = np.array([1.]*len(bins))
	    self.spec = np.zeros(fft_len,dtype='complex')
	    self.spec[bins] = self.amps*np.exp(1j*(phase))
	    wave = np.fft.ifft(self.spec)
	    waveMax = np.max(np.abs(wave))
	    I = (wave.real/waveMax)*(amp_full_scale)
            Q = (wave.imag/waveMax)*(amp_full_scale)
        else:
            fft_len = (self.LUTbuffer_len/self.fft_len)
            bins = self.fft_bin_index(freqs, fft_len, samp_freq)
	    spec = np.zeros(fft_len,dtype='complex')
            amps = np.array([1.]*len(bins))
            phase = 0.
	    spec[bins] = amps*np.exp(1j*(phase))
            wave = np.fft.ifft(spec)
            #wave = signal.convolve(wave,signal.hanning(3), mode = 'same')
	    waveMax = np.max(np.abs(wave))
	    I = (wave.real/waveMax)*(amp_full_scale)
            Q = (wave.imag/waveMax)*(amp_full_scale)
	return I, Q    
    
    def select_bins(self, freqs):
    # Calculates the offset from each bin center, to be used as the DDS LUT frequencies, and writes bin numbers to RAM
        bins = self.fft_bin_index(freqs, self.fft_len, self.dac_samp_freq)
        bin_freqs = bins*self.dac_samp_freq/self.fft_len
	bins[ bins < 0 ] += self.fft_len
	self.freq_residuals = freqs - bin_freqs
        #for i in range(len(freqs)):
	#	print "bin, fbin, freq, offset:", bins[i], bin_freqs[i]/1.0e6, freqs[i]/1.0e6, self.freq_residuals[i]
	ch = 0
        for fft_bin in bins:
	    self.fpga.write_int('bins', fft_bin)
            self.fpga.write_int('load_bins', 2*ch + 1)
	    self.fpga.write_int('load_bins', 0)
            ch += 1
        return 
    
    def define_DDS_LUT(self,freqs):
# Builds the DDS look-up-table from I and Q given by freq_comb. freq_comb is called with the sample rate equal to the sample rate for a single FFT bin. There are two bins returned for every fpga clock, so the bin sample rate is 256 MHz / half the fft length  
        self.select_bins(freqs)
        I_dds, Q_dds = np.array([0.]*(self.LUTbuffer_len)), np.array([0.]*(self.LUTbuffer_len))
        for m in range(len(self.freq_residuals)):
            I, Q = self.freq_comb(np.array([self.freq_residuals[m]]), self.fpga_samp_freq/(self.fft_len/2.), self.dac_freq_res, random_phase = False, DAC_LUT = False)
            I_dds[m::self.fft_len] = I
            Q_dds[m::self.fft_len] = Q
        return I_dds, Q_dds
    
    def pack_luts(self, freqs):
    # packs the I and Q look-up-tables into strings of 16-b integers, in preparation to write to the QDR. Returns the string-packed look-up-tables
	self.I_dac, self.Q_dac = self.freq_comb(freqs, self.dac_samp_freq, self.dac_freq_res, random_phase = True)
	self.I_dds, self.Q_dds = self.define_DDS_LUT(freqs)
        self.I_lut, self.Q_lut = np.zeros(self.LUTbuffer_len*2), np.zeros(self.LUTbuffer_len*2)
        self.I_lut[0::4] = self.I_dac[1::2]         
        self.I_lut[1::4] = self.I_dac[0::2]
        self.I_lut[2::4] = self.I_dds[1::2]
        self.I_lut[3::4] = self.I_dds[0::2]
        self.Q_lut[0::4] = self.Q_dac[1::2]         
        self.Q_lut[1::4] = self.Q_dac[0::2]
        self.Q_lut[2::4] = self.Q_dds[1::2]
        self.Q_lut[3::4] = self.Q_dds[0::2]
        print 'String Packing LUT...',
        self.I_lut_packed = self.I_lut.astype('>h').tostring()
        self.Q_lut_packed = self.Q_lut.astype('>h').tostring()
        print 'Done.'
	return 
        
    def writeQDR(self, freqs):
    # Writes packed LUTs to QDR
	self.pack_luts(freqs)
        self.fpga.write_int('dac_reset',1)
        self.fpga.write_int('dac_reset',0)
        print 'Writing DAC and DDS LUTs to QDR...',
        self.fpga.write_int('start_dac',0)
        self.fpga.blindwrite('qdr0_memory',self.I_lut_packed,0)
        self.fpga.blindwrite('qdr1_memory',self.Q_lut_packed,0)
        self.fpga.write_int('start_dac',1)
        self.fpga.write_int('sync_accum_reset', 0)
        self.fpga.write_int('sync_accum_reset', 1)
        print 'Done.'
        return 

    def read_QDR_katcp(self):
    # Reads out QDR buffers with KATCP, as 16-b signed integers.    
        self.QDR0 = np.fromstring(self.fpga.read('qdr0_memory', 8 * 2**20),dtype='>i2')
        self.QDR1 = np.fromstring(self.fpga.read('qdr1_memory', 8* 2**20),dtype='>i2')
        self.I_katcp = self.QDR0.reshape(len(self.QDR0)/4.,4.)
        self.Q_katcp = self.QDR1.reshape(len(self.QDR1)/4.,4.)
        self.I_dac_katcp = np.hstack(zip(self.I_katcp[:,1],self.I_katcp[:,0]))
        self.Q_dac_katcp = np.hstack(zip(self.Q_katcp[:,1],self.Q_katcp[:,0]))
        self.I_dds_katcp = np.hstack(zip(self.I_katcp[:,3],self.I_katcp[:,2]))
        self.Q_dds_katcp = np.hstack(zip(self.Q_katcp[:,3],self.Q_katcp[:,2]))
        return        

    def read_QDR_snap(self):
    # Reads out QDR snaps
        self.fpga.write_int('QDR_LUT_snap_qdr_ctrl',0)
        self.fpga.write_int('QDR_LUT_snap_qdr_ctrl',1)
        qdr_snap = np.fromstring(self.fpga.read('QDR_LUT_snap_qdr_bram', 16 * 2**10),dtype='>i2').astype('float')
        self.QDRs = qdr_snap.reshape(len(qdr_snap)/8.,8.)
        self.I1_dds_snap = self.QDRs[:,0]
        self.I0_dds_snap = self.QDRs[:,1]
        self.I1_snap = self.QDRs[:,2]
        self.I0_snap = self.QDRs[:,3]
        self.Q1_dds_snap = self.QDRs[:,4]
        self.Q0_dds_snap = self.QDRs[:,5]
        self.Q1_snap = self.QDRs[:,6]
        self.Q0_snap = self.QDRs[:,7]
        self.I_dac_snap = np.hstack(zip(self.I0_snap,self.I1_snap))
        self.Q_dac_snap = np.hstack(zip(self.Q0_snap,self.Q1_snap))
        self.I_dds_snap = np.hstack(zip(self.I0_dds_snap,self.I1_dds_snap))
        self.Q_dds_snap = np.hstack(zip(self.Q0_dds_snap,self.Q1_dds_snap))
        return

    def read_select_bins(self):
    # Reads the snap blocks at the bin select RAM and channelizer mux
        self.fpga.write_int('chan_bins_ctrl', 0)
        self.fpga.write_int('chan_bins_ctrl', 1)
        self.chan_bins = np.fromstring(ri.fpga.read('chan_bins_bram', 8 * 2**9),dtype = '>H')
	self.chan_bins = np.hstack(zip(ri.chan_bins[2::4], self.chan_bins[3::4]))
        return

    def read_accum_snap(self):
        # Reads the avgIQ buffer. Returns I and Q as 32-b signed integers     
        self.fpga.write_int('accum_snap_ctrl', 0)
        self.fpga.write_int('accum_snap_ctrl', 1)
        accum_data = np.fromstring(self.fpga.read('accum_snap_bram', 16*2**11), dtype = '>i').astype('float')
        I0 = accum_data[0::4]    
        Q0 = accum_data[1::4]    
        I1 = accum_data[2::4]    
        Q1 = accum_data[3::4]    
        I = np.hstack(zip(I0, I1))
        Q = np.hstack(zip(Q0, Q1))
        return I, Q    

    def initialize_GbE(self):
        # Configure GbE Block. Run immediately after calibrating QDR.
        self.fpga.write_int('tx_rst',0)
        self.fpga.write_int('tx_rst',1)
        self.fpga.write_int('tx_rst',0)
        return

    def stream_UDP(self,chan,Npackets):
	self.fpga.write_int('pps_start', 1)
        count = 0
	while count < Npackets:
        	packet = self.s.recv(8234) # total number of bytes including 42 byte header
		try:
			data = np.fromstring(packet[42:],dtype = '<i').astype('float')
			forty_two = (np.fromstring(packet[-16:-12],dtype = '>I'))
			pps_count = (np.fromstring(packet[-12:-8],dtype = '>I'))
			time_stamp = np.round((np.fromstring(packet[-8:-4],dtype = '>I').astype('float')/self.fpga_samp_freq)*1.0e3,3)
			packet_count = (np.fromstring(packet[-4:],dtype = '>I'))
			if (chan % 2) > 0:
				I = data[1024 + ((chan - 1) / 2)]    
				Q = data[1536 + ((chan - 1) /2)]    
			else:
				I = data[0 + (chan/2)]    
				Q = data[512 + (chan/2)]    
			phase = np.arctan2([Q],[I])
			print forty_two, pps_count, time_stamp, packet_count, I, Q, phase
             		count += 1
	    	except ValueError:
	    		pass
	    	except AttributeError:
	    		pass
	    	except IndexError:
			pass
	return 

    def stream_cosmic(self,chan,time_interval):
	accum_len = 2**12
	self.fpga.write_int('sync_accum_len', accum_len - 1)
	accum_freq = self.fpga_samp_freq / (accum_len - 1)
	Npackets = int(time_interval * accum_freq)
	self.fpga.write_int('pps_start', 1)
        #running_sum = 0.
        #running_sum_sq = 0.
	#running_avg = 0.
	#running_std = 0.
	while 1:
		count = 0
		phases = np.zeros(Npackets)
		while count < Npackets:
		    packet = self.s.recv(8234) # total number of bytes including 42 byte header
		    data = np.fromstring(packet[42:],dtype = '<i').astype('float')
		    #forty_two = (np.fromstring(packet[-16:-12],dtype = '>I'))
		    #pps_count = (np.fromstring(packet[-12:-8],dtype = '>I'))
		    #time_stamp = np.round((np.fromstring(packet[-8:-4],dtype = '>I').astype('float')/self.fpga_samp_freq)*1.0e3,3)
		    packet_count = (np.fromstring(packet[-4:],dtype = '>I'))
		    if (chan % 2) > 0:
			I = data[1024 + ((chan - 1) / 2)]    
			Q = data[1536 + ((chan - 1) /2)]    
		    else:
			I = data[0 + (chan/2)]    
			Q = data[512 + (chan/2)]    
		    phases[count] = np.arctan2([Q],[I])
		    #running_sum += phase
		    #running_sum_sq += phase**2 
		    #running_avg = running_sum / count
		    #running_std = (running_sum_sq / count) - running_avg**2
		    count += 1
		std10 = 3.5*np.std(phases)
		mean = np.mean(phases)
		min_phase, max_phase = np.min(phases), np.max(phases)
		if ((min_phase - mean) < std10) | ((max_phase - mean) > std10 ):
			print 'outlier'
			np.save('/home/olimpo/data/cosmic/' + str(time.time()) + '_' + str(chan) + '.npy', phases)
		print count, mean, std10
	self.fpga.write_int('sync_accum_len', self.accum_len - 1)
	return 

    def dirfile_all_chan(self, time_interval):
	nchannel = input("Number of channels? ")
	channels = range(nchannel)
	data_path = "./data"
	sub_folder_1 = "meas"
	sub_folder_2 = raw_input("Insert subfolder name (e.g. single_tone): ")
	Npackets = np.int(time_interval * self.accum_freq)
	self.fpga.write_int('pps_start', 1)
        save_path = os.path.join(data_path, sub_folder_1, sub_folder_2)
	if not os.path.exists(save_path):
	    os.makedirs(save_path)
	#os.mkdir(save_path)
	shutil.copy(data_path + "/format", save_path + "/format")
	nfo_I = map(lambda x: save_path + "/chI_" + str(x), range(nchannel))
        nfo_Q = map(lambda y: save_path + "/chQ_" + str(y), range(nchannel))
        nfo_phase = map(lambda z: save_path + "/chP_" + str(z), range(nchannel))
	fo_I = map(lambda x: open(x, "ab"), nfo_I)
	fo_Q = map(lambda y: open(y, "ab"), nfo_Q)
	fo_phase = map(lambda z: open(z, "ab"), nfo_phase)
        fo_time = open(save_path + "/time", "ab")
  	fo_count = open(save_path + "/packet_count", "ab")	
	count = 0
	while count < Npackets:
		print Npackets - count
		ts = time.time()
            	packet = self.s.recv(8234) # total number of bytes including 42 byte header
           	data = np.fromstring(packet[42:],dtype = '<i').astype('float')
            	packet_count = (np.fromstring(packet[-4:],dtype = '>I'))
	    	for chan in channels:
	    		if (chan % 2) > 0:
               			I = data[1024 + ((chan - 1) / 2)]    
                		Q = data[1536 + ((chan - 1) /2)]    
            		else:
                		I = data[0 + (chan/2)]    
                		Q = data[512 + (chan/2)]    
			fo_I[chan].write(struct.pack('i',I))
	    		fo_Q[chan].write(struct.pack('i',Q))
	    		fo_phase[chan].write(struct.pack('f', np.arctan2([Q],[I])))
			fo_I[chan].flush()
			fo_Q[chan].flush()
			fo_phase[chan].flush()
	    	count += 1
		fo_time.write(struct.pack('d', ts))
		fo_count.write(struct.pack('L',packet_count))
		fo_time.flush()
		fo_count.flush()
	for chan in channels:
		fo_I[chan].close()
		fo_Q[chan].close()
		fo_phase[chan].close()
	fo_time.close()
	fo_count.close()
        return 

    def dirfile_phase_centered(self, time_interval):
    	target_path = raw_input('Absolute path to target sweep dir (e.g. /home/lazarus/sam_git/blast_readout/sweeps/target/0806_2): ')
	self.centers = np.load(target_path + '/centers.npy')
	I_center = self.centers.real
	Q_center = self.centers.imag
	nchannel = input("Number of channels? ")
	channels = range(nchannel)
	data_path = "./data"
	sub_folder_1 = "noise_measurements_0811"
	sub_folder_2 = raw_input("Insert subfolder name (e.g. single_tone): ")
	Npackets = np.int(time_interval * self.accum_freq)
	#channels = np.arange(21)
	self.fpga.write_int('pps_start', 1)
        save_path = os.path.join(data_path, sub_folder_1, sub_folder_2)
	os.mkdir(save_path)
	#shutil.copy(data_path + "/format", save_path + "/format")
	nfo_I = map(lambda x: save_path + "/chI_" + str(x), range(nchannel))
        nfo_Q = map(lambda y: save_path + "/chQ_" + str(y), range(nchannel))
        nfo_phase = map(lambda z: save_path + "/chP_" + str(z), range(nchannel))
	fo_I = map(lambda x: open(x, "ab"), nfo_I)
	fo_Q = map(lambda y: open(y, "ab"), nfo_Q)
	fo_phase = map(lambda z: open(z, "ab"), nfo_phase)
        fo_time = open(save_path + "/time", "ab")
  	fo_count = open(save_path + "/packet_count", "ab")	
	count = 0
	while count < Npackets:
		ts = time.time()
            	packet = self.s.recv(8234) # total number of bytes including 42 byte header
           	data = np.fromstring(packet[42:],dtype = '<i').astype('float')
            	packet_count = (np.fromstring(packet[-4:],dtype = '>I'))
	    	for chan in channels:
	    		if (chan % 2) > 0:
               			I = data[1024 + ((chan - 1) / 2)]    
                		Q = data[1536 + ((chan - 1) /2)]    
            		else:
                		I = data[0 + (chan/2)]    
                		Q = data[512 + (chan/2)]    
			fo_I[chan].write(struct.pack('i',I))
	    		fo_Q[chan].write(struct.pack('i',Q))
	    		fo_phase[chan].write(struct.pack('f', np.arctan2([Q - Q_center[chan]],[I - I_center[chan]])))
			fo_I[chan].flush()
			fo_Q[chan].flush()
			fo_phase[chan].flush()
	    	count += 1
		fo_time.write(struct.pack('d', ts))
		fo_count.write(struct.pack('L',packet_count))
		fo_time.flush()
		fo_count.flush()
	for chan in channels:
		fo_I[chan].close()
		fo_Q[chan].close()
		fo_phase[chan].close()
	fo_time.close()
	fo_count.close()
        return 
    
    def dirfile_avg_chan(self, time_interval):
	nchannel = input("Number of channels? ")
	channels = range(nchannel)
	data_path = "./data"
	sub_folder_1 = "noise_measurements_0811"
	sub_folder_2 = raw_input("Insert subfolder name (e.g. single_tone): ")
	Npackets = np.int(time_interval * self.accum_freq)
	self.fpga.write_int('pps_start', 1)
        save_path = os.path.join(data_path, sub_folder_1, sub_folder_2)
	if not os.path.exists(save_path):
	    os.makedirs(save_path)
	#shutil.copy(data_path + "/format", save_path + "/format")
	nfo_I = save_path + "/chI_avg_" + str(nchannel)
	nfo_Q = save_path + "/chQ_avg_" + str(nchannel)
	nfo_P = save_path + "/chP_avg_" + str(nchannel)
	fo_I = open(nfo_I, "ab")
	fo_Q = open(nfo_Q, "ab")
	fo_phase = open(nfo_P, "ab")
        fo_time = open(save_path + "/time", "ab")
  	fo_count = open(save_path + "/packet_count", "ab")	
	count = 0
	while count < Npackets:
		print Npackets - count
		I_sum = 0.
		Q_sum = 0.
		phase_sum = 0.
		ts = time.time()
            	packet = self.s.recv(8234) # total number of bytes including 42 byte header
           	data = np.fromstring(packet[42:],dtype = '<i').astype('float')
            	packet_count = (np.fromstring(packet[-4:],dtype = '>I'))
	    	for chan in channels:
	    		if (chan % 2) > 0:
               			I = data[1024 + ((chan - 1) / 2)]    
                		Q = data[1536 + ((chan - 1) /2)]    
            		else:
                		I = data[0 + (chan/2)]    
                		Q = data[512 + (chan/2)]    
			I_sum += I
			Q_sum += Q
		I_avg = I_sum / nchannel
		Q_avg = Q_sum / nchannel
		phase_avg = np.arctan2([Q_avg],[I_avg]) 
		fo_I.write(struct.pack('i',I_avg))
	    	fo_Q.write(struct.pack('i',Q_avg))
		fo_time.write(struct.pack('d', ts))
		fo_count.write(struct.pack('L',packet_count))
		fo_time.flush()
		fo_count.flush()
	    	fo_phase.write(struct.pack('f', phase_avg))
		fo_I.flush()
		fo_Q.flush()
		fo_phase.flush()
	    	count += 1
	fo_I.close()
	fo_Q.close()
	fo_phase.close()
	fo_time.close()
	fo_count.close()
        return 
    
    def IQ_grad(self, dark_sweep_path, plot_chan): 
	lo_freqs, I_dark, Q_dark = self.open_stored(dark_sweep_path)
	bb_freqs, delta_f = np.linspace(-200.0e6, 200.0e6, 500,retstep=True)
	#bb_freqs = np.load('/mnt/iqstream/last_bb_freqs.npy')
	channels = np.arange(len(bb_freqs))
        delta_lo = 5e3
	i_index = [np.where(np.abs(np.diff(I_dark[:,chan])) == np.max(np.abs(np.diff(I_dark[:,chan]))))[0][0] for chan in channels]
        q_index = [np.where(np.abs(np.diff(Q_dark[:,chan])) == np.max(np.abs(np.diff(Q_dark[:,chan]))))[0][0] for chan in channels]
        di_df = np.array([(I_dark[:,chan][i_index[chan] + 1] - I_dark[:,chan][i_index[chan] - 1])/(2*delta_lo) for chan in channels])
        dq_df = np.array([(Q_dark[:,chan][q_index[chan] + 1] - Q_dark[:,chan][q_index[chan] - 1])/(2*delta_lo) for chan in channels])
	I0 = np.array([I_dark[:,chan][i_index[chan]] for chan in channels])
	Q0 = np.array([Q_dark[:,chan][q_index[chan]] for chan in channels])
	rf_freqs = np.array([200.0e6 + bb_freqs[chan] for chan in channels])
	return di_df[plot_chan], dq_df[plot_chan], rf_freqs[plot_chan]
    
    def vna_sweep(self, center_freq, save_path = './sweeps/vna/', write = False, sweep = False):
	sweep_dir = raw_input('Insert new VNA sweep dir (e.g. 0805_1): ')
        save_path = os.path.join(save_path, sweep_dir)
	os.mkdir(save_path)
	self.v1.set_frequency(0, center_freq/1.0e6, 0.01)
        span = self.pos_delta
	start = center_freq - (span/2.)
        stop = center_freq + (span/2.) 
        sweep_freqs = np.arange(start, stop, self.lo_step)
        self.sweep_freqs = np.round(sweep_freqs/self.lo_step)*self.lo_step
	print "LO freqs =", self.sweep_freqs
	np.save(save_path + '/bb_freqs.npy',self.test_comb)
	np.save(save_path + '/sweep_freqs.npy',self.sweep_freqs)
	if write:
		self.writeQDR(self.test_comb)
        if sweep:
		for freq in self.sweep_freqs:
		    print 'Sweep freq =', freq/1.0e6
		    if self.v1.set_frequency(0, freq/1.0e6, 0.01): 
			self.store_UDP(100,freq,save_path,channels=len(self.test_comb)) 
		self.v1.set_frequency(0,center_freq / (1.0e6), 0.01) # LO
	self.plot_vna(save_path)
	#self.find_kids_olimpo.main(path)
	return 

    def target_sweep(self, center_freq, save_path = './sweeps/target', write = True, sweep = False):
        vna_path = raw_input('Absolute path to VNA sweep dir (e.g. /home/lazarus/sam_git/blast_readout/sweeps/vna/0805_1) ? ')
	self.target_freqs = np.load(vna_path + '/target_freqs.npy')
	sweep_dir = raw_input('Insert new target sweep dir (e.g. 0805_1): ')
        save_path = os.path.join(save_path, sweep_dir)
	os.mkdir(save_path)
	np.save(save_path + '/target_freqs.npy', self.target_freqs)
	#center_freq = (np.max(self.target_freqs) + np.min(self.target_freqs))/2.
        self.bb_target_freqs = ((self.target_freqs*1.0e6) - center_freq)
        #self.bb_target_freqs = (self.target_freqs - center_freq/2)
        self.bb_target_freqs = np.roll(self.bb_target_freqs, - np.argmin(np.abs(self.bb_target_freqs)) - 1)
	upconvert = np.sort((self.bb_target_freqs + center_freq)/1.0e6)
        print "RF tones =", upconvert
	self.v1.set_frequency(0,center_freq / (1.0e6), 0.01) # LO
	print '\nTarget baseband freqs (MHz) =', self.bb_target_freqs/1.0e6
	span = 100.0e3
	start = center_freq - (span/2.)
        stop = center_freq + (span/2.) 
        sweep_freqs = np.arange(start, stop, self.lo_step)
        sweep_freqs = np.round(sweep_freqs/step)*step
	print "LO freqs =", sweep_freqs
	np.save(save_path + '/bb_freqs.npy',self.bb_target_freqs)
	np.save(save_path + '/sweep_freqs.npy',sweep_freqs)
	if write:
		self.writeQDR(self.bb_target_freqs)
	if sweep:
		for freq in sweep_freqs:
		    print 'Sweep freq =', freq/1.0e6
		    if self.v1.set_frequency(0, freq/1.0e6, 0.01): 
			self.store_UDP(100,freq,save_path,channels=len(self.bb_target_freqs)) 
		self.v1.set_frequency(0,center_freq / (1.0e6), 0.01) # LO
	self.plot_targ(save_path)
	return
    
    def store_UDP(self, Npackets, LO_freq, save_path, skip_packets=2, channels = None):
	channels = np.arange(channels)
        I_buffer = np.empty((Npackets + skip_packets, len(channels)))
        Q_buffer = np.empty((Npackets + skip_packets, len(channels)))
        #self.fpga.write_int('pps_start', 1)
        count = 0
        while count < Npackets + skip_packets:
            packet = self.s.recv(8234) # total number of bytes including 42 byte header
	    if (not np.fromstring(packet[:256],dtype = '<B').astype('float')[26] == 192.):
	    	pass
	    try:
		data = np.fromstring(packet[42:],dtype = '<i').astype('float')
		ts = (np.fromstring(packet[-4:],dtype = '<i').astype('float')/ self.fpga_samp_freq)*1.0e3 # ts in ms
		odd_chan = channels[1::2]
		even_chan = channels[0::2]
		I_odd = data[1024 + ((odd_chan - 1) / 2)]    
		Q_odd = data[1536 + ((odd_chan - 1) /2)]    
		I_even = data[0 + (even_chan/2)]    
	 	Q_even = data[512 + (even_chan/2)]    
		even_phase = np.arctan2(Q_even,I_even)
		odd_phase = np.arctan2(Q_odd,I_odd)
	        if len(channels) % 2 > 0:
	        	if len(I_odd) > 0:
				I = np.hstack(zip(I_even[:len(I_odd)], I_odd))
			    	Q = np.hstack(zip(Q_even[:len(Q_odd)], Q_odd))
			    	I = np.hstack((I, I_even[-1]))    
			    	Q = np.hstack((Q, Q_even[-1]))    
			else:
			   	I = I_even[0]
			    	Q = Q_even[0]
			I_buffer[count] = I
			Q_buffer[count] = Q
            	else:
                	I = np.hstack(zip(I_even, I_odd))
                	Q = np.hstack(zip(Q_even, Q_odd))
                	I_buffer[count] = I
                	Q_buffer[count] = Q
            	count += 1
        	I_file = 'I' + str(LO_freq)
        	Q_file = 'Q' + str(LO_freq)
        	np.save(os.path.join(save_path,I_file), np.mean(I_buffer[skip_packets:], axis = 0)) 
        	np.save(os.path.join(save_path,Q_file), np.mean(Q_buffer[skip_packets:], axis = 0)) 
	    except ValueError:
	    	pass
	    except AttributeError:
	    	pass
	    except IndexError:
		pass
        return 

    def plot_vna(self, path):
    	plt.ion()
	plt.figure(5)
	plt.clf()
	sweep_freqs, Is, Qs = ri.open_stored(path)
	sweep_freqs = np.load(path + '/sweep_freqs.npy')
	bb_freqs = np.load(path + '/bb_freqs.npy')
	rf_freqs = np.zeros((len(bb_freqs),len(sweep_freqs)))
	for chan in range(len(bb_freqs)):
		rf_freqs[chan] = (sweep_freqs + bb_freqs[chan])/1.0e6
	Q = np.reshape(np.transpose(Qs),(len(Qs[0])*len(sweep_freqs)))
	I = np.reshape(np.transpose(Is),(len(Is[0])*len(sweep_freqs)))
	mag = np.sqrt(I**2 + Q**2)
	mag /= (2**17 - 1)
	mag /= ((self.accum_len) / (self.fft_len/2))
	mag = 20*np.log10(mag)
	mag = np.concatenate((mag[len(mag)/2:],mag[:len(mag)/2]))
	rf_freqs = np.hstack(rf_freqs)
	rf_freqs = np.concatenate((rf_freqs[len(rf_freqs)/2:],rf_freqs[:len(rf_freqs)/2]))
	plt.plot(rf_freqs, mag)
	plt.title('VNA sweep')
	plt.xlabel('frequency (MHz)')
        plt.ylabel('dB')
	return
    
    def plot_targ(self, path):
    	plt.ion()
	plt.figure(6)
	plt.clf()
	lo_freqs, Is, Qs = ri.open_stored(path)
	lo_freqs = np.load(path + '/sweep_freqs.npy')
	bb_freqs = np.load(path + '/bb_freqs.npy')
	channels = len(bb_freqs)
	mags = np.zeros((channels,len(lo_freqs))) 
	chan_freqs = np.zeros((channels,len(lo_freqs)))
        new_targs = np.zeros((channels))
	for chan in range(channels):
        	mags[chan] = np.sqrt(Is[:,chan]**2 + Qs[:,chan]**2)
		mags[chan] /= (2**15 - 1)
		mags[chan] /= ((self.accum_len - 1) / (self.fft_len/2))
		mags[chan] = 20*np.log10(mags[chan])
		chan_freqs[chan] = (lo_freqs + bb_freqs[chan])/1.0e6
	mags = np.concatenate((mags[len(mags)/2:],mags[:len(mags)/2]))
	#bb_freqs = np.concatenate(bb_freqs[len(b_freqs)/2:],bb_freqs[:len(bb_freqs)/2]))
	chan_freqs = np.concatenate((chan_freqs[len(chan_freqs)/2:],chan_freqs[:len(chan_freqs)/2]))
	new_targs = [chan_freqs[chan][np.argmin(mags[chan])] for chan in range(channels)]
	print new_targs
	for chan in range(channels):
		plt.plot(chan_freqs[chan],mags[chan])
	plt.title('Target sweep')
	plt.xlabel('frequency (MHz)')
        plt.ylabel('dB')
	return

    def store_UDP_noavg(self, Npackets, LO_freq, save_path, skip_packets=2, channels = None):
        #Npackets = np.int(time_interval * self.accum_freq)
        I_buffer = np.empty((Npackets + skip_packets, len(channels)))
        Q_buffer = np.empty((Npackets + skip_packets, len(channels)))
        self.fpga.write_int('pps_start', 1)
        count = 0
        while count < Npackets + skip_packets:
            packet = self.s.recv(8192 + 42) # total number of bytes including 42 byte header
	    if (not np.fromstring(packet[:256],dtype = '<B').astype('float')[26] == 192.):
	    	pass
	    try:
		data = np.fromstring(packet[42:],dtype = '<i').astype('float')
	    except (ValueError or AttributeError):
		pass
            ts = (np.fromstring(packet[-4:],dtype = '<i').astype('float')/ self.fpga_samp_freq)*1.0e3 # ts in ms
            odd_chan = channels[1::2]
            even_chan = channels[0::2]
            I_odd = data[1024 + ((odd_chan - 1) / 2)]    
            Q_odd = data[1536 + ((odd_chan - 1) /2)]    
            I_even = data[0 + (even_chan/2)]    
            Q_even = data[512 + (even_chan/2)]    
            even_phase = np.arctan2(Q_even,I_even)
            odd_phase = np.arctan2(Q_odd,I_odd)
            if len(channels) % 2 > 0:
                I = np.hstack(zip(I_even[:len(I_odd)], I_odd))
                Q = np.hstack(zip(Q_even[:len(Q_odd)], Q_odd))
                I = np.hstack((I, I_even[-1]))    
                Q = np.hstack((Q, Q_even[-1]))    
                I_buffer[count] = I
                Q_buffer[count] = Q
            else:
                I = np.hstack(zip(I_even, I_odd))
                Q = np.hstack(zip(Q_even, Q_odd))
                I_buffer[count] = I
                Q_buffer[count] = Q
            count += 1
        I_file = 'I' + str(LO_freq)
        Q_file = 'Q' + str(LO_freq)
        np.save(os.path.join(save_path,I_file), I_buffer[skip_packets:]) 
        np.save(os.path.join(save_path,Q_file), Q_buffer[skip_packets:]) 
        return 
    
    def open_stored(self, save_path = None):
        files = sorted(os.listdir(save_path))
        sweep_freqs = np.array([np.float(filename[1:-4]) for filename in files if (filename.startswith('I'))])
        I_list = [os.path.join(save_path, filename) for filename in files if filename.startswith('I')]
        Q_list = [os.path.join(save_path, filename) for filename in files if filename.startswith('Q')]
        Is = np.array([np.load(filename) for filename in I_list])
        Qs = np.array([np.load(filename) for filename in Q_list])
        return sweep_freqs, Is, Qs

    def get_kid_freqs(self, path):
	sweep_step = 2.5 # kHz
	smoothing_scale = 1500.0 # kHz
	peak_threshold = 0.4 # mag units
	spacing_threshold = 50.0 # kHz
	#find_kids_olimpo.get_kids(path, self.test_comb, sweep_step, smoothing_scale, peak_threshold, spacing_threshold)
	return
	
    def plot_sweep(self, bb_freqs, path):
        plot_sweep.plot_trace(bb_freqs, path)
	return
    
    def plot_kids(self, save_path = None, bb_freqs = None, channels = None):
        plt.ion()
	plt.figure(1)
	plt.clf()
	lo_freqs, Is, Qs = self.open_stored(save_path)
        #[ plt.plot((sweep_freqs[2:] + bb_freqs[chan])/1.0e9,10*np.log10(np.sqrt(Is[:,chan][2:]**2+Qs[:,chan][2:]**2))) for chan in channels]
        mags = np.zeros((channels,len(lo_freqs)))
	scaled_mags = np.zeros((channels,len(lo_freqs)))
        for chan in range(channels):
        	mags[chan] = 20*np.log10(np.sqrt(Is[:,chan]**2 + Qs[:,chan]**2))
	#for chan in range(channels):
	#	diff = 0. - np.mean(mags[chan])
	#	scaled_mags[chan] = diff + mags[chan]
		#plt.plot((lo_freqs + bb_freqs[chan])/1.0e9,scaled_mags[chan])
        	plt.plot((self.sweep_freqs + bb_freqs[chan])/1.0e9,mags[chan])
	plt.ylim((np.min(mags), np.max(mags)))
	plt.xlabel('frequency (GHz)')
        plt.ylabel('[dB]')
        #plt.savefig(os.path.join(save_path,'fig.png'))
        plt.show()
        return

    def get_stream(self, chan, time_interval):
        self.fpga.write_int('pps_start', 1)
        #self.phases = np.empty((len(self.freqs),Npackets))
	#save_path = raw_input('Absolute save path (e.g. /home/olimpo/data/python_psd/ctime) ')
        #os.mkdir(save_path)
	Npackets = np.int(time_interval * self.accum_freq)
        Is = np.empty(Npackets)
        Qs = np.empty(Npackets)
        phases = np.empty(Npackets)
        count = 0
        while count < Npackets:
        	packet = self.s.recv(8192 + 42) # total number of bytes including 42 byte header
               	data = np.fromstring(packet[42:],dtype = '<i').astype('float')
                #ts = (np.fromstring(packet[-4:],dtype = '<i').astype('float')/ self.fpga_samp_freq)*1.0e3 # ts in ms
                #To stream one channel, make chan an argument
                if (chan % 2) > 0:
                    I = data[1024 + ((chan - 1) / 2)]    
                    Q = data[1536 + ((chan - 1) /2)]    
                else:
                    I = data[0 + (chan/2)]    
                    Q = data[512 + (chan/2)]    
                phase = np.arctan2([Q],[I])
                Is[count]=I
                Qs[count]=Q
                phases[count]=phase
            	count += 1
        #np.save(save_path + '/phase_vals.npy', phases)
        #np.save(save_path + '/single_tone_I.npy', Is)
        #np.save(save_path + '/single_tone_Q.npy', Qs)
	return Is, Qs, phases
    
    def plot_phase_PSD(self, chan, time_interval):
	Npackets = np.int(time_interval * self.accum_freq)
        plot_range = (Npackets / 2) + 1
	figure = plt.figure(num= None, figsize=(12,12), dpi=120, facecolor='w', edgecolor='w')
	plt.suptitle('Chan ' + str(chan) + ' phase PSD')
	ax = figure.add_subplot(1,1,1)
	ax.set_xscale('log')
	ax.set_ylim((-160,-50))
        ax.set_ylabel('dBc/Hz', size = 20)
        ax.set_xlabel('log Hz', size = 20)
        plt.grid()
	Is, Qs, phases = self.get_stream(chan, time_interval)
	#phases -= np.mean(phases)
	phase_mags = 2*np.fft.rfft(phases)
	phase_vals = ( np.abs(phase_mags)**2 / Npackets ) * (1./self.accum_freq)
	phase_vals = 10*np.log10(phase_vals)
	ax.plot(np.linspace(0, self.accum_freq/2., (Npackets/2) + 1), phase_vals, color = 'b', linewidth = 1)
	#ax.axhline(10*np.log10(6.4e-8), linestyle = '--', c = 'g')
	plt.show()
	return
    
    def plot_amp_PSD(self, chan, time_interval):
	Npackets = np.int(time_interval * self.accum_freq)
        plot_range = (Npackets / 2) + 1
	figure = plt.figure(num= None, figsize=(20,12), dpi=200, facecolor='w', edgecolor='w')
	plt.suptitle('Chan ' + str(chan) + ' amplitude PSD')
	ax = figure.add_subplot(1,1,1)
	ax.set_xscale('log')
	#ax.set_ylim((-160,-50))
        ax.set_ylabel('dB/Hz', size = 20)
        ax.set_xlabel('log Hz', size = 20)
        plt.grid()
	Is, Qs, phases = self.get_stream(chan, time_interval)
	conversion_factor = (self.accum_len / 512.) * (2**19)
	Is, Qs = Is/conversion_factor, Qs/conversion_factor
	mags = 2*np.fft.rfft(np.sqrt(Is**2 + Qs**2))
	psd = ( np.abs(mags)**2 / Npackets ) * (1./self.accum_freq)
	psd = 10*np.log10(psd)
	ax.plot(np.linspace(0, self.accum_freq/2., (Npackets/2) + 1), psd, color = 'b', linewidth = 1)
	#ax.axhline(10*np.log10(6.4e-8), linestyle = '--', c = 'g')
	plt.show()
	return

    def stream_and_save(self, time_interval, LO_freq, save_path, skip_packets=0, channels = None):
        Npackets = np.int(time_interval * self.accum_freq)
        I_buffer = np.empty((Npackets + skip_packets, len(channels)))
        Q_buffer = np.empty((Npackets + skip_packets, len(channels)))
        #self.fpga.write_int('pps_start', 1)
        count = 0
        while count < Npackets + skip_packets:
            packet = self.s.recv(8234) # total number of bytes including 42 byte header
            data = np.fromstring(packet[42:],dtype = '<i').astype('float')
            odd_chan = channels[1::2]
            even_chan = channels[0::2]
            I_odd = data[1024 + ((odd_chan - 1) / 2)]    
            Q_odd = data[1536 + ((odd_chan - 1) /2)]    
            I_even = data[0 + (even_chan/2)]    
            Q_even = data[512 + (even_chan/2)]    
            even_phase = np.arctan2(Q_even,I_even)
            odd_phase = np.arctan2(Q_odd,I_odd)
            if len(channels) % 2 > 0:
                I = np.hstack(zip(I_even[:len(I_odd)], I_odd))
                Q = np.hstack(zip(Q_even[:len(Q_odd)], Q_odd))
                I = np.hstack((I, I_even[-1]))    
                Q = np.hstack((Q, Q_even[-1]))    
                I_buffer[count] = I
                Q_buffer[count] = Q
            else:
                I = np.hstack(zip(I_even, I_odd))
                Q = np.hstack(zip(Q_even, Q_odd))
                I_buffer[count] = I
                Q_buffer[count] = Q
            count += 1
        I_file = 'I' + str(LO_freq)
        Q_file = 'Q' + str(LO_freq)
        np.save(os.path.join(save_path,I_file), np.mean(I_buffer[skip_packets:], axis = 0)) 
        np.save(os.path.join(save_path,Q_file), np.mean(Q_buffer[skip_packets:], axis = 0)) 
        return 
    
    def programLO(self, freq=200.0e6, sweep_freq=0):
        self.vi.simple_set_freq(0,freq)
        return

    def menu(self,prompt,options):
        print '\t' + prompt + '\n'
        for i in range(len(options)):
            print '\t' +  '\033[32m' + str(i) + ' ..... ' '\033[0m' +  options[i] + '\n'
        opt = input()
        return opt
    
    def main_opt(self):
        while True:
            opt = self.menu(self.main_prompt,self.main_opts)
            if opt == 0:
                os.system('clear')
                self.initialize() 
            if opt == 1:
		try:
			self.chan_freqs = np.sort(((self.test_comb + (self.center_freq)*1.0e6))/1.0e6)
        		print "RF tones =", self.chan_freqs
			self.writeQDR(self.test_comb)
	    	except KeyboardInterrupt:
			pass
	    if opt == 2:
	    	file_path = raw_input('Absolute path to .npy file (list of baseband frequencies in any order, e.g. /home/lazarus/sam_git/blast_readout/sweeps/target/0806_2/bb_freqs.npy): ' )
		freqs = np.load(file_path)
		freqs = freqs[freqs != 0]
		freqs = np.roll(freqs, - np.argmin(np.abs(freqs)) - 1)
		rf_tones = np.sort((freqs + ((self.center_freq)*1.0e6))/1.0e6)
        	print "RF tones =", rf_tones
		self.writeQDR(freqs)
	    if opt == 3:
            	Npackets = input('\nNumber of UDP packets to stream? ' )
                chan = input('chan = ? ')
		try:
			self.stream_UDP(chan,Npackets)
		except KeyboardInterrupt:
			pass
	    if opt == 4:
	    	prompt = raw_input('Do sweep? (y/n) ')
		if prompt == 'y':
                	try:
				self.vna_sweep(center_freq = self.center_freq, sweep = True)
            		except KeyboardInterrupt:
				pass
		if prompt == 'n':
			try:
				self.vna_sweep()
            		except KeyboardInterrupt:
				pass
	    if opt == 5:
		path = raw_input("Absolute data path to a good VNA sweep dir (e.g. /home/lazarus/sam_git/blast_readout/sweeps/vna/0806_2): ")
                try:
			fk.main(path)
	    	except KeyboardInterrupt:
			pass
	    if opt == 6:
		prompt = raw_input('Do sweep? (y/n) ')
		if prompt == 'y':
                	try:
				self.target_sweep(center_freq = self.center_freq, sweep = True)
            		except KeyboardInterrupt:
				pass
		if prompt == 'n':
			try:
				self.target_sweep()
            		except KeyboardInterrupt:
				pass
	    if opt == 7:
		chan = input('Channel number = ? ')
		time_interval = input('Time interval (s) ? ')
	    	try:
			self.plot_phase_PSD(chan, time_interval)
		except KeyboardInterrupt:
			pass
	    if opt == 8:
		chan = input('Channel number = ? ')
		time_interval = input('Time interval (s) ? ')
	    	try:
			self.plot_amp_PSD(chan, time_interval)
		except KeyboardInterrupt:
			pass
	    if opt == 9:
		time_interval = input('Time interval (s) ? ')
		try:
			self.dirfile_all_chan(time_interval)
		except KeyboardInterrupt:
			pass 
	    if opt == 10:
		time_interval = input('Time interval (s) ? ')
	    	try:
			self.dirfile_phase_centered(time_interval)
		except KeyboardInterrupt:
			pass 
	    if opt == 11:
                sys.exit()
        return
    
    def main(self):
        os.system('clear')
        while True: 
            self.main_opt()

if __name__=='__main__':
    ri = roachInterface()
    ri.main()
