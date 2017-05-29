import matplotlib, time, struct
import numpy as np
np.set_printoptions(threshold=np.nan)
import matplotlib.pyplot as plt
matplotlib.use("TkAgg")
plt.ion()
import casperfpga 
#import corr
from myQdr import Qdr as myQdr
import types
import logging
import glob  
import os
import sys
#import valon_synth
#sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
#from ValonSynth_interface import valonInterface
from socket import *
from scipy import signal
import pygetdata as gd
import valon5009
import rudat_6000_30_usb
from lowpass_cosine import lowpass_cosine
#import SocketServer

def sprint(string):
	print 'ROACH Remote Control Log Entry - %s'%time.asctime()
	print string
	sys.stdout.flush()
	return
		
class roachInterface(object):
	
	#check DNSMASQ is running!!!
	
	
	def __init__(self, boot=False,reset_valon=False,remote=False):
		
		#self.vLO = valon_synth.Synthesizer('/dev/ttyUSB0')
		#self.vLO.set_frequency(8,512,0.01) # DAC/ADC
		if boot ==True:
			os.system('sudo service dnsmasq restart')
		self.LO_freq = 0.969e9
		self.v = valon5009.ValonDevice()
		self.vCLK = self.v.s1
		self.vLO = self.v.s2
		if boot or reset_valon:
			self.vCLK.frequency = 512e6
			self.vLO.frequency = self.LO_freq # LO
			self.vLO.attenuator = 0
			self.vLO.referenceDoubler = 0
			self.vLO.referenceDivider = 1

		self.a1 = rudat_6000_30_usb.rudats[161]
		self.a2 = rudat_6000_30_usb.rudats[162]
		self.a1.att = 0
		self.a2.att = 0
		
		self.dac_samp_freq = 512.0e6
		self.fpga_samp_freq = 256.0e6
		#self.dds_shift = 304 # blast_0120_ppstest_2016_Jan_25_1529.fpg
		self.dds_shift = 304 # roach2_4tap_wide_round_2016_Nov_03_1435.fpg
		#self.dds_shift = 304 # blast_0115_bigadcsnap_2016_Oct_31_1618.fpg
		#self.dds_shift = 304 # roach2_4tap_wide_2016_Nov_03_1431.fpg
		#self.dds_shift = 304 # roach2_4tap_wide_round_2016_Nov_03_1435.fpg
		self.port = 3000
		self.ip = '192.168.40.56' # Set to PPC IP in /etc/network/interfaces
		self.fpga = casperfpga.katcp_fpga.KatcpFpga(self.ip,timeout=120.)
		self.bitstream = '/home/sam/lib/blastfirmware/blast_0120_ppstest_2016_Jan_25_1529.fpg'
		#self.bitstream = '/home/sam/ips/wp3-readout/firmware/sam8tap/roach2_8tap_wide/bit_files/roach2_8tap_wide_2016_Sep_13_1055.fpg'
		#self.bitstream = '/home/sam/readout/firmware/blastfirmware_nist/blast_0115_bigadcsnap/bit_files/blast_0115_bigadcsnap_2016_Oct_31_1040.fpg'
		#self.bitstream ='/home/sam/readout/firmware/blastfirmware_nist/blast_0115_bigadcsnap/bit_files/blast_0115_bigadcsnap_2016_Oct_31_1618.fpg'
		
		#self.bitstream ='/home/sam/readout/firmware/sam4tap/roach2_4tap_wide/bit_files/roach2_4tap_wide_2016_Nov_03_1431.fpg'
		
		#self.bitstream ='/home/sam/readout/firmware/sam4tapround/roach2_4tap_wide_round/bit_files/roach2_4tap_wide_round_2016_Nov_03_1435.fpg'
		
		
		
		self.test_freq = np.array([50.0125]) * 1.0e6
		if boot:
			self.upload_fpg()
		#self.freqs = np.array(np.loadtxt('BLASTResonatorPositionsVer2.txt', delimiter=','))
		#self.freqs = np.linspace(751e6,851e6,100)
		#self.freqs = np.array(np.loadtxt('ColumbiaKidsRun1-500M.txt', delimiter='\n'))
		#self.freqs = np.array([50.125e6,450.125e6])
		#self.freqs = np.linspace(-250e6,250e6,256)+np.random.uniform(-0.5,0.5,256)*1e6
		#self.vLO.set_frequency(0,750.0, 0.01) # LO
		#self.phases = np.random.uniform(-np.pi,np.pi,len(self.freqs))
		self.freqs=np.loadtxt('/home/sam/readout/noise_model/testfreqs256.txt')
		self.phases=np.loadtxt('/home/sam/readout/noise_model/testphases256.txt')
		
		self.LUTbuffer_len = 2**21
		self.dac_freq_res = self.dac_samp_freq/self.LUTbuffer_len
		self.f_base = 300.0
		self.fft_len = 1024
		self.fft_bins = self.fft_bin_index(self.freqs, self.fft_len, self.dac_samp_freq)
		self.test_bin = self.fft_bin_index(self.test_freq, self.fft_len, self.dac_samp_freq)
		#self.vi = valonInterface() # If using a valon as DAC/ADC clock and LO, controlled in Linux
		self.main_prompt = '\n\t\033[35mROACHII mKID Readout\033[0m\n\t\033[33mChoose a number from the list and press Enter. 0 - 4 should be followed in order:\033[0m'
		self.main_opts= ['Calibrate QDR','Initialize GbE (Must toggle before writing first tone)','Write Test Tone','Write DAC, DDS LUTs','Stream UDP packets','VNA sweep and plot','Locate resonances','Target sweep and plot','Stream Responses','Exit'] 
		#sys.stdout.flush()
		self.dest_ip  = 192*(2**24) + 168*(2**16) + 41*(2**8) + 2 # Set to FPGA IP in /etc/network/interfaces
		self.fabric_port= 60000 
		self.fpga.write_int('tx_destip',self.dest_ip)
		self.fpga.write_int('tx_destport',self.fabric_port)
		self.accum_len = (2**20)-1 
		#self.accum_len = (2**18)-1 
		self.fpga.write_int('sync_accum_len', self.accum_len)
		self.accum_freq = self.fpga_samp_freq / self.accum_len # FPGA clock freq / accumulation length	
		self.UDP_IP = "192.168.41.2" 
		self.UDP_PORT = 60000 # Fabric Port
		self.fpga.write_int('fft_shift', 255)	
		self.fpga.write_int('rx_ack', 1)
		self.fpga.write_int('rx_rst', 0)
		#self.s = socket(AF_PACKET, SOCK_RAW, htons(3))
		#self.s.setsockopt(SOL_SOCKET, SO_RCVBUF, 8192 + 42)
		#self.s.bind(('eth2', 3))
		self.s=socket(AF_INET,SOCK_DGRAM)
		self.s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
		#self.s.setsockopt(SOL_SOCKET, SO_RCVBUF, int(8192*self.accum_freq))
		#self.s.settimeout(10./self.accum_freq)
		self.s.setblocking(0)
		self.s.bind((self.UDP_IP,self.UDP_PORT))
		#self.sockbufsize = self.s.getsockopt(SOL_SOCKET, SO_RCVBUF)
		
		self.fpga.write_int('dds_shift', self.dds_shift)
		self.save_path = '/mnt/iqstream/'
		
		Npackets = int(10*8000)
		self.I_buffer = np.empty((Npackets, 1024))
		self.Q_buffer = np.empty((Npackets, 1024))
		self.ts_buffer = np.empty(Npackets)
		
		
		if boot:
			print "Calibrating QDR Memory"
			self.qdrCal()
			print "Initialising Gigabit Ethernet"
			self.initialize_GbE()
			print "Writing test tones"
			self.writeQDR(self.freqs,phases=self.phases)
			self.fpga.write_int('sync_accum_reset', 0)
			self.fpga.write_int('sync_accum_reset', 1)
			print "Checking UDP stream (3 packets)"
			self.stream_UDP(0,3)
			print "OK"
			time.sleep(1)
		#self.main_opt()
		if remote:
			ri.commandServer()

	def set_freqs(self,freqs,phases=None,default=False,remove_cryostat_input_s21=False,lo_frequency=None,remove_electronics_input_response=False,gains=None,adjust_carrier_leakage=False,adjust_sideband_leakage=False,auto_fullscale=True,tweak=(0.04,0.,0.,0.)):
		if default:
			newfreqs = np.linspace(-250e6,250e6,1024)+np.random.uniform(-0.5,0.5,1024)*1e6
		else:
			newfreqs = freqs
		self.freqs = np.array([newfreqs]).flatten()
		if phases is not None:
			self.phases = np.array([phases]).flatten()
		self.writeQDR(self.freqs,phases=phases,gains=gains,remove_cryostat_input_s21=remove_cryostat_input_s21,lo_frequency=lo_frequency,remove_electronics_input_response=remove_electronics_input_response,adjust_carrier_leakage=adjust_carrier_leakage,adjust_sideband_leakage=adjust_sideband_leakage,auto_fullscale=auto_fullscale,tweak=tweak)
		self.fpga.write_int('sync_accum_reset', 0)
		self.fpga.write_int('sync_accum_reset', 1)
		
	
	#def commandServerUDP(self,port=6666):
		#local_ip = os.popen('ifconfig eth0 | grep "inet\ addr" | cut -d: -f2 | cut -d" " -f1').read().strip()
		#server = SocketServer.UDPServer((local_ip,port),self.commandHandlerUDP)
		#try:
			#server.serve_forever()
		#except KeyboardInterrupt:
			#server.shutdown()
			
		
	#class commandHandlerUDP(SocketServer.BaseRequestHandler):
		#def handle(self):
			#data = self.request[0]
			#socket = self.request[1]
			#print 'Data:'
			#print data
			#print 'Socket:'
			#print socket
		
		
	def clearUDP(self):
		size=self.s.getsockopt(SOL_SOCKET,SO_RCVBUF)
		print
		while size>0:
			r = self.s.recv(65536)
			l=len(r)
			if l==0:
				break
			size -= l
			print '\rclearing %d'%size,
		print
		
	
	def set_accum_len(self,length=2**20-1):
		self.accum_len = length 
		#self.accum_len = (2**18)-1 
		self.fpga.write_int('sync_accum_len', self.accum_len)
		self.fpga.write_int('sync_accum_reset', 0)
		self.fpga.write_int('sync_accum_reset', 1)
		self.accum_freq = self.fpga_samp_freq / self.accum_len # FPGA clock freq /

		
		
	def upload_fpg(self):
		print 'Connecting...'
		t1 = time.time()
		timeout = 10
		while not self.fpga.is_connected():
		    	if (time.time()-t1) > timeout:
				raise Exception("Connection timeout to roach")
		time.sleep(0.1)
		if (self.fpga.is_connected() == True):
			print 'Connection established to', self.ip
		    	self.fpga.upload_to_ram_and_program(str(self.bitstream))
			time.sleep(2)
			print 'Uploaded', self.bitstream
		else:
		    	print 'Not connected to the FPGA'
		return

	def qdrCal(self):	
	# Calibrates the QDRs. Run after writing to QDR.  	
		self.fpga.write_int('dac_reset',1)
		bQdrCal = True
		bQdrCal2 = True
		bFailHard = False
		calVerbosity = 1
		qdrMemName = 'qdr0_memory'
		qdrNames = ['qdr0_memory','qdr1_memory']
		print 'Fpga Clock Rate =',self.fpga.estimate_fpga_clock()
		if bQdrCal:
			self.fpga.get_system_information()
			results = {}
			for qdr in self.fpga.qdrs:
				print qdr
				if bQdrCal2:
					mqdr = myQdr.from_qdr(qdr)
					results[qdr.name] = mqdr.qdr_cal2(fail_hard=bFailHard,verbosity=calVerbosity)
				else:
					results[qdr.name] = qdr.qdr_cal(fail_hard=bFailHard,verbosity=calVerbosity)
			print 'qdr cal results:',results
			for qdrName in ['qdr0','qdr1']:
				if not results[qdr.name]:
					print 'Calibration Failed'
					break
			return results
	
	def toggle_dac(self):
		self.fpga.write_int('dac_reset',1)
		self.fpga.write_int('dac_reset',0)
		return
	
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
		mixer_in = np.fromstring(self.fpga.read('rawfftbin_bram', 16*2**14),dtype='>i2').astype('float')
		mixer_in /= 2.0**15
		if mixer_out:
			mixer_out = np.fromstring(self.fpga.read('mixerout_bram', 8*2**14),dtype='>i2').astype('float')
			mixer_out /= 2.0**14
			return mixer_in, mixer_out
		else:
			return mixer_in

	def return_shift(self, chan):
	# Returns the dds shift
		dds_spec = np.abs(np.fft.rfft(self.I_dds[chan::1024],1024))
		dds_index = np.where(np.abs(dds_spec) == np.max(np.abs(dds_spec)))[0][0]
		print 'Finding LUT shift...' 
		for i in range(1024):
			print i
			mixer_in = self.read_mixer_snaps(i, chan, mixer_out = False)
			I0_dds_in = mixer_in[2::8]	
			I0_dds_in[np.where(I0_dds_in > 32767.)] -= 65535.
			snap_spec = np.abs(np.fft.rfft(I0_dds_in,1024))
			snap_index = np.where(np.abs(snap_spec) == np.max(np.abs(snap_spec)))[0][0]
			if dds_index == snap_index:
				print 'LUT shift =', i
				shift = i
				break
		return shift

	def mixer_comp(self,chan, find_shift = True, I0 = True, plot = True):
	# Plots the dds mixer data at the shift found by return_shift 	
		if find_shift:
			shift = self.return_shift(chan)
		else: 
			shift = self.dds_shift
			#shift = input('Shift = ?')
		mixer_in, mixer_out = self.read_mixer_snaps(shift, chan)	
		if I0:
			I_in = mixer_in[0::8]
			Q_in = mixer_in[1::8]
			I_dds_in = mixer_in[2::8]
			Q_dds_in = mixer_in[3::8]
			I_out = mixer_out[0::4]
			Q_out = mixer_out[1::4]
		else:
			I_in = mixer_in[4::8]
			Q_in = mixer_in[5::8]
			I_dds_in = mixer_in[6::8]
			Q_dds_in = mixer_in[7::8]
			I_out = mixer_out[2::4]
			Q_out = mixer_out[3::4]
		# Mixer in 
		I_out_guess = ((I_in * I_dds_in) + (Q_in * Q_dds_in))
		Q_out_guess = (-1.*(I_in * Q_dds_in) + (Q_in * I_dds_in))
		# Mixer out 
		if plot:
			plt.figure()
			if I0:
				plt.suptitle('DDS Shift = ' + str(shift) + ', Freq = ' + str(self.test_freq/1.0e6) + ' MHz,' + ' I0')
			else:
				plt.suptitle('DDS Shift = ' + str(shift) + ', Freq = ' + str(self.test_freq/1.0e6) + ' MHz,' + ' I1')
			plt.subplot(2,3,1)
			plt.plot(I_in, label = 'I in', color = 'black', linewidth = 2)
			plt.plot(I_dds_in, label = 'I dds in', color = 'red')
			plt.xlim((0,300))
			plt.ylim((-1.0,1.0))
			plt.legend()
			plt.grid()
			plt.subplot(2,3,2)
			plt.legend()
			plt.grid()
			plt.plot(Q_in, label = 'Q in', color = 'green', linewidth = 2)
			plt.plot(Q_dds_in, label = 'Q dds in', color = 'blue')
			plt.xlim((0,300))
			plt.ylim((-1.0,1.0))
			plt.legend()
			plt.grid()
			plt.subplot(2,3,3)
			plt.plot(I_dds_in, label = 'I dds in', color = 'red')
			plt.plot(Q_dds_in, label = 'Q dds in', color = 'blue')
			plt.xlim((0,300))
			plt.ylim((-1.0,1.0))
			plt.legend()
			plt.grid()
			plt.subplot(2,3,4)
			plt.plot(I_in, label = 'I in', color = 'black', linewidth = 2)
			plt.plot(Q_in, label = 'Q in', color = 'green', linewidth = 2)
			plt.xlim((0,300))
			plt.ylim((-1.0,1.0))
			plt.legend()
			plt.grid()
			plt.subplot(2,3,5)
			plt.plot(I_out_guess, label = 'I out predict', color = 'black', linewidth = 2)
			plt.plot(Q_out_guess, label = 'Q out predict', color = 'green', linewidth = 2)
			plt.xlim((0,300))
			plt.ylim((-2.0,2.0))
			plt.legend()
			plt.grid()
			plt.subplot(2,3,6)
			plt.plot(I_out, label = 'I out', color = 'black', linewidth = 2)
			plt.plot(Q_out, label = 'Q out', color = 'green', linewidth = 2)
			plt.xlim((0,300))
			plt.ylim((-2.0,2.0))
			plt.legend()
			plt.grid()
			plt.show()
		return I_in, Q_in, I_dds_in, Q_dds_in, I_out, Q_out

	def plotMixer(self, chan):
		#chan = sys.argv[1]
		#chan = int(chan)
		figure = plt.figure(num= None, figsize=(12,12), dpi=80, facecolor='w', edgecolor='w')
		# I and Q
		plt.suptitle('Channel ' + str(chan) + ' , Freq = ' + str(self.freqs[chan]/1.0e6) + ' MHz') 
		plot1 = figure.add_subplot(311)
		plt.title('I/Q into mixer')
		line1, = plot1.plot(range(16384), np.zeros(16384), label = 'I in', color = 'green', linewidth = 1)
		line2, = plot1.plot(range(16384), np.zeros(16384), label = 'Q in', color = 'black', linewidth = 1)
		plt.xlim((0,500))
		plt.ylim((-1.0,1.0))
		plt.grid()
		# DDS I and Q
		plot2 = figure.add_subplot(312)
		plt.title('I/Q DDS into mixer')
		line3, = plot2.plot(range(16384), np.zeros(16384), label = 'I dds', color = 'red', linewidth = 1)
		line4, = plot2.plot(range(16384), np.zeros(16384), label = 'Q dds', color = 'black', linewidth = 1)
		plt.xlim((0,500))
		plt.ylim((-1.0,1.0))
		plt.grid()
		# Mixer output
		plot3 = figure.add_subplot(313)
		plt.title('I/Q mixer out')
		line5, = plot3.plot(range(16384), np.zeros(16384), label = 'I out', color = 'green', linewidth = 1)
		line6, = plot3.plot(range(16384), np.zeros(16384), label = 'Q out', color = 'black', linewidth = 1)
		plt.xlim((0,500))
		plt.ylim((-2.0, 2.0))
		plt.grid()
		plt.show(block = False)
		count = 0
		stop = 1.0e8
		while (count < stop):
			if (chan % 2) > 0:
				I_in, Q_in, I_dds_in, Q_dds_in, I_out, Q_out = self.mixer_comp(chan, find_shift = False, I0 = False, plot = False)
			else:
				I_in, Q_in, I_dds_in, Q_dds_in, I_out, Q_out = self.mixer_comp(chan, find_shift = False, plot = False)
			line1.set_ydata(I_in)
			line2.set_ydata(Q_in)
			line3.set_ydata(I_dds_in)
			line4.set_ydata(Q_dds_in)
			line5.set_ydata(I_out)
			line6.set_ydata(Q_out)
			plt.draw()
			count += 1
			plt.pause(0.1)

	def freq_comb(self, freqs, samp_freq, resolution,phase = np.array([0.]*1024), random_phase = True, DAC_LUT = True,phases=None,tweak=(0.04,0.,0.,0.),adjust_carrier_leakage=False,adjust_sideband_leakage=False,amplitude_offsets=None,phase_offsets=None,remove_cryostat_input_s21=False,lo_frequency=None,remove_electronics_input_response=False,gains=None,auto_fullscale=True):
	# Generates a frequency comb for the DAC or DDS look-up-tables. DAC_LUT = True for the DAC LUT. Returns I and Q 
		freqs = np.round(freqs/self.dac_freq_res)*self.dac_freq_res
		if DAC_LUT:
			fft_len = self.LUTbuffer_len
			bins = self.fft_bin_index(freqs, fft_len, samp_freq)
			ibins =  -1*bins #bins of sideband leakage images
			amps = np.array([1.]*len(bins))
			#amps[1] = 0.0001
			#tIa,tIb,tQa,tQb=tweak
			
			###refer to /home/sam/readout/rf-normalisation/rf-norm for details
			if remove_electronics_input_response:
				
				###TBD
				#select correct response file for the anticipated lo frequency,
				#the accuracy of these files vary by +-1.dB for 100MHz offsets on the lo.
				if lo_frequency is None:
					raise 'Error, must give LO frequency if removing cryostat input s21'
				
				elec_freqs,elec_response = np.load('/home/sam/readout/rf-normalisation/elec_response_1ghzLO.npy')
				elec_response_select = np.interp(freqs,elec_freqs,elec_response)
				amps /= elec_response_select
			if remove_cryostat_input_s21:
				if lo_frequency is None:
					raise 'Error, must give LO frequency if removing cryostat input s21'
				cryo_freqs, cryo_s21_i,cryo_s21_q = np.load('/home/sam/readout/rf-normalisation/cryostat_input.npy')
				cryo_s21_mag = abs(cryo_s21_i+1j*cryo_s21_q)
				
				cryo_s21_select = np.interp(freqs+lo_frequency,cryo_freqs,cryo_s21_mag)
				amps /= cryo_s21_select
			
			self.bins_latest = bins
			self.freqs_latest = freqs
			
		else:
			fft_len = (self.LUTbuffer_len/self.fft_len)
			bins = self.fft_bin_index(freqs, fft_len, samp_freq)
			amps = np.array([1.]*len(freqs))
			#tIa,tIb,tQa,tQb=(1.,0.,1.,0.)
		
		amp_full_scale = (2**15 - 1)
		spec = np.zeros(fft_len,dtype='complex')
		if random_phase:
			np.random.seed()
			phase = np.random.uniform(0., 2.*np.pi, len(bins))
		if phases is not None:
			phase = phases
		
		spec[bins] = amps*np.exp(1j*(phase))
		if DAC_LUT:
			self.amps_latest = amps
			self.phases_latest = phase
			self.spec=spec

		
		if adjust_sideband_leakage:
			if DAC_LUT:
				### Add image tones to cancel out RF images 
				if lo_frequency is None:
					raise 'Error, must give LO frequency if adjusting sideband leakage'
				
				#TBD: choose correct leakage file for this lo frequency:
				#get magnitudes:
				sb_freqs,sb_mags = np.load('/home/sam/readout/sideband-leakage/leakage_1ghzLO_freqs_mags.npy')
				sb_mag_select = np.interp(freqs,sb_freqs,sb_mags)
				#get phases:
				sb_freqs,sb_phases = np.load('/home/sam/readout/sideband-leakage/leakage_1ghzLO_freqs_phases.npy')
				sb_phase_select = np.deg2rad(np.interp(freqs,sb_freqs,sb_phases))
				
				#phase_poly = np.poly1d([ -6.37087084e-16,  -4.74683613e-08,   2.65110536e+02] )
				#phase_offsets = np.deg2rad(phase_poly(freqs))
				spec[ibins] = 10**(sb_mag_select/20.)*amps*np.exp(1j*(-1*phase+sb_phase_select))
				
				##testing
				#da,dp = tweak[0],tweak[1]
				##spec[ibins] = 10**(-da/20.)*amps*np.exp(1j*(phase+dp))
				#spec[ibins] = 10**(sb_mag_select/20.)*amps*np.exp(1j*(-1*phase+dp))
				##phase_offsets = np.deg2rad(266)
				
				self.spec=spec
				
		
		wave       = np.fft.ifft(spec)
		waveMax    = np.max(np.abs(wave))
		if DAC_LUT:
			print '*****wavemax = ',waveMax
			
		if auto_fullscale is False:
			if DAC_LUT:
				#an example value is 2.8e-5 for 256 tones with random phases and sideband image tones
				waveMax = 3e-5
				if remove_electronics_input_response:
					waveMax = 5.0e-5  
					#which gives tone powers of around -41.5 +-0.5 dBm at RF Out
					if remove_cryostat_input_s21:
						waveMax=0.001
						#which gives tone powers of around -60.5 +-0.5 dBm at array input (cryostat input loss is 27dB)
				elif remove_cryostat_input_s21:
					waveMax = 0.00075
				print '*****stored wavemax = ',waveMax
		
		if gains is not None:
			if DAC_LUT:
				#amps *= 10**(gains/20.)
				#spec[bins] = amps*np.exp(1j*(phase))
				spec[bins] = spec[bins].real*10**(gains/20.) + 1j*spec[bins].imag*10**(gains/20.)
				if adjust_sideband_leakage:
					spec[ibins] = spec[ibins].real*10**(gains/20.) + 1j*spec[ibins].imag*10**(gains/20.)
					self.spec=spec

				wave       = np.fft.ifft(spec)
				waveMax    = waveMax
				
		#I = (wave.real/waveMax)*(amp_full_scale)*1.0*tIa + tIb
		#Q = (wave.imag/waveMax)*(amp_full_scale)*1.0*tQa + tQb
		I = (wave.real/waveMax)*(amp_full_scale)
		Q = (wave.imag/waveMax)*(amp_full_scale)
		
		###Does not work: probably the DAC outputs are filtered to remove dc offsets.
		if None:
			if adjust_carrier_leakage:
				if DAC_LUT:
					I -= I.mean() 
					I += amp_full_scale/2
					Q -= Q.mean() 
					Q += amp_full_scale/2
					
					Ioff = tweak[2]
					Qoff = tweak[3]
					I += Ioff
					Q += Qoff
			
		#I=np.round(I)
		#Q=np.round(Q)
		return I, Q	
	
	def select_bins(self, freqs):
	# Adjusts the DAC frequencies to the DAC frequency resolution and calculates the offset from each bin center, to be used as the DDS LUT frequencies
		bins = self.fft_bin_index(freqs, self.fft_len, self.dac_samp_freq)
		#print 'Bin numbers = ', bins
		bin_freqs = bins*self.dac_samp_freq/self.fft_len
		#print 'Bin center freqs = ', bin_freqs/1.0e6
		self.freq_residuals = np.round((freqs - bin_freqs)/self.dac_freq_res)*self.dac_freq_res
		ch = 0
		for fft_bin in bins:
			self.fpga.write_int('bins', fft_bin)#have fft_bin waiting at ram gate
		    	self.fpga.write_int('load_bins', 2*ch + 1)#enable write ram at address i
		    	self.fpga.write_int('load_bins', 0)#disable write 
		    	ch += 1
		# This is done to clear any unused channelizer RAM addresses
		for n in range(1024 - len(bins)):
			self.fpga.write_int('bins', 0)#have fft_bin waiting at ram gate
		   	self.fpga.write_int('load_bins', 2*ch + 1)#enable write ram at address i
		    	self.fpga.write_int('load_bins', 0)#disable write 
			ch += 1
			n += 1
		return 
	
	def define_DDS_LUT(self,freqs,):
# Builds the DDS look-up-table from I and Q given by freq_comb. freq_comb is called with the sample rate equal to the sample rate for a single FFT bin. There are two bins returned for every fpga clock, so the bin sample rate is 256 MHz / half the fft length  
		self.select_bins(freqs)
		I_dds, Q_dds = np.array([0.]*(self.LUTbuffer_len)), np.array([0.]*(self.LUTbuffer_len))
		for m in range(len(self.freq_residuals)):
			I, Q = self.freq_comb(np.array([self.freq_residuals[m]]), self.fpga_samp_freq/(self.fft_len/2.), self.dac_freq_res, random_phase = False, DAC_LUT = False)
			I_dds[m::1024] = I
			Q_dds[m::1024] = Q
		return I_dds, Q_dds
	
	def pack_luts(self, freqs,phases=None,tweak=(0.04,0.,0.,0.),remove_cryostat_input_s21=False,lo_frequency=None,remove_electronics_input_response=False,gains=None,adjust_carrier_leakage=False,adjust_sideband_leakage=False,auto_fullscale=True):
	# packs the I and Q look-up-tables into strings of 16-b integers, in preparation to write to the QDR. Returns the string-packed look-up-tables
		self.I_dac, self.Q_dac = self.freq_comb(freqs, self.dac_samp_freq, self.dac_freq_res, phases=phases,tweak=tweak, remove_cryostat_input_s21=remove_cryostat_input_s21, lo_frequency=lo_frequency, remove_electronics_input_response=remove_electronics_input_response, gains=gains,adjust_carrier_leakage=adjust_carrier_leakage, adjust_sideband_leakage=adjust_sideband_leakage,auto_fullscale=auto_fullscale)
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
		#self.I_lut_packed = self.I_lut.astype('>i2').tostring()
		#self.Q_lut_packed = self.Q_lut.astype('>i2').tostring()
		#self.I_lut_packed = np.around(self.I_lut).astype('>i2').tostring()
		#self.Q_lut_packed = np.around(self.Q_lut).astype('>i2').tostring()
		self.I_lut_packed = np.around(self.I_lut).astype('>h').tostring()
		self.Q_lut_packed = np.around(self.Q_lut).astype('>h').tostring()
		print 'Done.'
		return 
		
	def writeQDR(self, freqs,phases=None,tweak=(0.04,0.,0.,0.),remove_cryostat_input_s21=False,lo_frequency=None,remove_electronics_input_response=False,gains=None,adjust_carrier_leakage=False,adjust_sideband_leakage=False,auto_fullscale=True):
	# Writes packed LUTs to QDR
		self.pack_luts(freqs,phases=phases,tweak=tweak, remove_cryostat_input_s21=remove_cryostat_input_s21, lo_frequency=lo_frequency, remove_electronics_input_response=remove_electronics_input_response,gains=gains,adjust_carrier_leakage=adjust_carrier_leakage,adjust_sideband_leakage=adjust_sideband_leakage,auto_fullscale=auto_fullscale)
		self.fpga.write_int('dac_reset',1)
		self.fpga.write_int('dac_reset',0)
		print 'Writing DAC and DDS LUTs to QDR...',;sys.stdout.flush()
		self.fpga.write_int('start_dac',0)
		self.fpga.blindwrite('qdr0_memory',self.I_lut_packed,0)
		self.fpga.blindwrite('qdr1_memory',self.Q_lut_packed,0)
		self.fpga.write_int('start_dac',1)
		print 'Done.'
		return 

	
	def generate_full_scale_white_noise_file(self):
		for j in ['i','q']:
			wn =  np.random.randn(self.LUTbuffer_len)
			wn -= wn.min()
			wn /= wn.max()
			wn *= 2**15-1
			wn -= 2**14
			np.savetxt('/home/sam/ips/wp3-readout/firmware/blastfirmware/white_noise_%s.txt'%j,np.round(wn).astype(int),fmt='%d')
		return
	
	def writeQDR_white_noise_full_scale(self):
		wni = np.loadtxt('/home/sam/ips/wp3-readout/firmware/blastfirmware/white_noise_i.txt')
		wnq = np.loadtxt('/home/sam/ips/wp3-readout/firmware/blastfirmware/white_noise_q.txt')
		freqs=self.freqs
		self.I_dac, self.Q_dac = wni,wnq
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
		self.I_lut_packed = self.I_lut.astype('>i2').tostring()
		self.Q_lut_packed = self.Q_lut.astype('>i2').tostring()
		print 'Done.'
		
		self.fpga.write_int('dac_reset',1)
		self.fpga.write_int('dac_reset',0)
		print 'Writing DAC and DDS LUTs to QDR...',
		self.fpga.write_int('start_dac',0)
		self.fpga.blindwrite('qdr0_memory',self.I_lut_packed,0)
		self.fpga.blindwrite('qdr1_memory',self.Q_lut_packed,0)
		self.fpga.write_int('start_dac',1)
		print 'Done.'
		return 
	
	def read_QDR_katcp(self):
	# Reads out QDR buffers with KATCP, as 16-b signed integers.	
		self.QDR0 = np.fromstring(self.fpga.read('qdr0_memory', 8 * 2**20),dtype='>i2')
		self.QDR1 = np.fromstring(self.fpga.read('qdr1_memory', 8* 2**20),dtype='>i2')
		self.I_katcp = self.QDR0.reshape(len(self.QDR0)/4.,4.)
		self.Q_katcp = self.QDR1.reshape(len(self.QDR1)/4.,4.)
		#self.I_dac_katcp = np.hstack(zip(self.I_katcp[:,1],self.I_katcp[:,0]))
		#self.Q_dac_katcp = np.hstack(zip(self.Q_katcp[:,1],self.Q_katcp[:,0]))
		#self.I_dds_katcp = np.hstack(zip(self.I_katcp[:,3],self.I_katcp[:,2]))
		#self.Q_dds_katcp = np.hstack(zip(self.Q_katcp[:,3],self.Q_katcp[:,2]))
		self.I_dac_katcp = np.dstack((self.I_katcp[:,1],self.I_katcp[:,0])).ravel()
		self.Q_dac_katcp = np.dstack((self.Q_katcp[:,1],self.Q_katcp[:,0])).ravel()
		self.I_dds_katcp = np.dstack((self.I_katcp[:,3],self.I_katcp[:,2])).ravel()
		self.Q_dds_katcp = np.dstack((self.Q_katcp[:,3],self.Q_katcp[:,2])).ravel()
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
		#self.I_dac_snap = np.hstack(zip(self.I0_snap,self.I1_snap))
		#self.Q_dac_snap = np.hstack(zip(self.Q0_snap,self.Q1_snap))
		#self.I_dds_snap = np.hstack(zip(self.I0_dds_snap,self.I1_dds_snap))
		#self.Q_dds_snap = np.hstack(zip(self.Q0_dds_snap,self.Q1_dds_snap))
		self.I_dac_snap = np.dstack((self.I0_snap,self.I1_snap)).ravel()
		self.Q_dac_snap = np.dstack((self.Q0_snap,self.Q1_snap)).ravel()
		self.I_dds_snap = np.dstack((self.I0_dds_snap,self.I1_dds_snap)).ravel()
		self.Q_dds_snap = np.dstack((self.Q0_dds_snap,self.Q1_dds_snap)).ravel()
		return

	def read_chan_snaps(self):
	# Reads the snap blocks at the bin select RAM and channelizer mux
		self.fpga.write_int('buffer_out_ctrl', 0)
		self.fpga.write_int('buffer_out_ctrl', 1)
		self.chan_data = np.fromstring(self.fpga.read('buffer_out_bram', 8 * 2**9),dtype = '>H')
		self.fpga.write_int('chan_bins_ctrl', 0)
		self.fpga.write_int('chan_bins_ctrl', 1)
		self.chan_bins = np.fromstring(self.fpga.read('chan_bins_bram', 4 * 2**14),dtype = '>H')
		return

	def read_accum_snap(self):
        # Reads the avgIQ buffer. Returns I and Q as 32-b signed integers 	
		self.fpga.write_int('accum_snap_ctrl', 0)
        	self.fpga.write_int('accum_snap_ctrl', 1)
        	accum_data = np.fromstring(self.fpga.read('accum_snap_bram', 16*2**9), dtype = '>i').astype('float')
		accum_data /= 2.0**17
		accum_data /= ((self.accum_len)/512.)
		I0 = accum_data[0::4]	
		Q0 = accum_data[1::4]	
		I1 = accum_data[2::4]	
		Q1 = accum_data[3::4]	
		#I = np.hstack(zip(I0, I1))
		#Q = np.hstack(zip(Q0, Q1))
		I = np.dstack((I0, I1)).ravel()
		Q = np.dstack((Q0, Q1)).ravel()
		return I, Q	

	def plotAccum(self):
	# Generates a plot stream from read_avgIQ_snap(). To view, run plotAvgIQ.py in a separate terminal
		figure1 = plt.figure(num= None, figsize=(12,12), dpi=80, facecolor='w', edgecolor='w')
		plt.suptitle('Averaged FFT, Accum. Frequency = ' + str(self.accum_freq), fontsize=14)
		plot1 = figure1.add_subplot(111)
		line1, = plot1.plot(np.arange(0,1024),np.zeros(1024), 'b')
		plt.xlabel('Channel #',fontsize = 12)
		plt.ylabel('Amplitude',fontsize = 12)
		plt.xticks(np.arange(0,1024,100))
		plt.xlim(-50,1075)
		plt.grid()
		plt.show(block = False)
		count = 0 
		stop = 1.0e6
		while(count < stop):
			I, Q = self.read_accum_snap()
			mags = np.sqrt(I**2 + Q**2)
			plt.ylim((0,np.max(mags) + 0.001))
			line1.set_ydata(mags)
			plt.draw()
			count += 1
		return

	def plotADC(self):
	# Plots the ADC timestream
	# Peak to peak should be 900 mV (from DAC)
		figure1 = plt.figure(num= None, figsize=(12,12), dpi=80, facecolor='w', edgecolor='w')
		plt.suptitle("RAW ADC data capture", fontsize=14)
		plot1 = figure1.add_subplot(211)
		line1, = plot1.plot(np.arange(0,2048), np.zeros(2048), 'g-')
		plt.title('I')
		plt.xlim(0,100)
		plt.ylim(-1.1,1.1)
		#plt.yticks(np.arange(-4e4, 4e4, 5000.))
		plt.grid()
		plot2 = figure1.add_subplot(212)
		line2, = plot2.plot(np.arange(0,2048), np.zeros(2048), 'r-')
		plt.title('Q')
		plt.xlim(0,100)
		plt.ylim(-1.1,1.1)
		#plt.yticks(np.arange(-4e4, 4e4, 5000.))
		plt.grid()
		plt.show(block = False)
		plt.pause(0.1)
		count = 0
		stop = 1.0e8
		while count < stop:	
			time.sleep(0.1)
			self.fpga.write_int('adc_snap_ctrl',0)
			self.fpga.write_int('adc_snap_ctrl',1)
			self.fpga.write_int('adc_snap_trig',0)    
			self.fpga.write_int('adc_snap_trig',1)    
			self.fpga.write_int('adc_snap_trig',0)
			adc = (np.fromstring(self.fpga.read('adc_snap_bram',(2**10)*8),dtype='>i2')).astype('float')
			print adc
			adc /= 2.0**15 
			# ADC full scale is 2.2 V
			#adc *= 0.909091
			#I = np.hstack(zip(adc[0::4],adc[1::4]))
			#Q = np.hstack(zip(adc[2::4],adc[3::4]))
			I = np.dstack((adc[0::4],adc[1::4])).ravel()
			Q = np.dstack((adc[2::4],adc[3::4])).ravel()
			#return I
			#raw_input()
			line1.set_ydata(I)
			line2.set_ydata(Q)
			plot1.relim()
			plot1.autoscale()
			plot2.relim()
			plot2.autoscale()
			plt.draw()
			count += 1
			plt.pause(0.1)

	
	def getADC(self,n=2**11):
		self.fpga.write_int('adc_snap_ctrl',0)
		self.fpga.write_int('adc_snap_ctrl',1)
		self.fpga.write_int('adc_snap_trig',0)    
		self.fpga.write_int('adc_snap_trig',1)    
		self.fpga.write_int('adc_snap_trig',0)
		adc = (np.fromstring(self.fpga.read('adc_snap_bram',(n/2)*8),dtype='>i2')).astype('float')
		#print adc
		adc /= 2.0**15 
		# ADC full scale is 2.2 V
		#adc *= 0.909091
		#I = np.hstack(zip(adc[0::4],adc[1::4]))
		#Q = np.hstack(zip(adc[2::4],adc[3::4]))
		I = np.dstack((adc[0::4],adc[1::4])).ravel()
		Q = np.dstack((adc[2::4],adc[3::4])).ravel()
		return I,Q
	
	def plotADCpsd(self):
	# Plots the ADC timestream
	# Peak to peak should be 900 mV (from DAC)
		figure1 = plt.figure(num= None, figsize=(16,8), dpi=80, facecolor='w', edgecolor='w')
		plt.suptitle("RAW ADC data capture", fontsize=14)
		plot1 = figure1.add_subplot(241)
		line1, = plot1.plot(np.arange(0,2048), np.zeros(2048), 'g-')
		plt.title('I')
		plt.xlim(0,100)
		plt.ylim(-1.1,1.1)
		#plt.yticks(np.arange(-4e4, 4e4, 5000.))
		plt.grid()
		plot2 = figure1.add_subplot(245)
		line2, = plot2.plot(np.arange(0,2048), np.zeros(2048), 'r-')
		plt.title('Q')
		plt.xlim(0,100)
		plt.ylim(-1.1,1.1)
		#plt.yticks(np.arange(-4e4, 4e4, 5000.))
		plt.grid()
		plot1p = figure1.add_subplot(242)
		line1p, = plot1p.plot(np.arange(0,1024), np.zeros(1024), 'g-')
		plt.title('I-PSD')
		#plt.xlim(0,100)
		#plt.ylim(-1.1,1.1)
		#plt.yticks(np.arange(-4e4, 4e4, 5000.))
		plt.grid()
		plot2p = figure1.add_subplot(246)
		line2p, = plot2p.plot(np.arange(0,1024), np.zeros(1024), 'r-')
		plt.title('Q-PSD')
		#plt.xlim(0,100)
		#plt.ylim(-1.1,1.1)
		#plt.yticks(np.arange(-4e4, 4e4, 5000.))
		plt.grid()
		plt.show(block = False)
		plot3 = figure1.add_subplot(122)
		plot3.set_aspect('equal','datalim')
		line3, = plot3.plot(np.arange(0,1024), np.zeros(1024), 'bx')
		line3r, = plot3.plot((0,0), (0,0), 'k-',marker='o')
		plt.title('IQ')
		plt.xlim(-1,1)
		plt.ylim(-1,1)
		#plt.yticks(np.arange(-4e4, 4e4, 5000.))
		plt.grid()
		plt.show(block = False)
		plt.pause(0.1)
		count = 0
		stop = 1.0e8
		while count < stop:	
			time.sleep(0.1)
			self.fpga.write_int('adc_snap_ctrl',0)
			self.fpga.write_int('adc_snap_ctrl',1)
			self.fpga.write_int('adc_snap_trig',0)    
			self.fpga.write_int('adc_snap_trig',1)    
			self.fpga.write_int('adc_snap_trig',0)
			adc = (np.fromstring(self.fpga.read('adc_snap_bram',(2**10)*8),dtype='>i2')).astype('float')
			print adc
			adc /= 2.0**15 
			# ADC full scale is 2.2 V
			#adc *= 0.909091
			#I = np.hstack(zip(adc[0::4],adc[1::4]))
			#Q = np.hstack(zip(adc[2::4],adc[3::4]))
			I = np.dstack((adc[0::4],adc[1::4])).ravel()
			Q = np.dstack((adc[2::4],adc[3::4])).ravel()
			Ipsd,Ifreqs = plt.mlab.psd(I,Fs=self.dac_samp_freq,NFFT=len(I))
			Qpsd,Qfreqs = plt.mlab.psd(Q,Fs=self.dac_samp_freq,NFFT=len(Q))
			#return I
			#raw_input()
			line1.set_ydata(I)
			line2.set_ydata(Q)
			line1p.set_ydata(10*np.log10(Ipsd))
			line2p.set_ydata(10*np.log10(Qpsd))
			line1p.set_xdata(Ifreqs/1e6)
			line2p.set_xdata(Qfreqs/1e6)
			line3.set_xdata(I)
			line3.set_ydata(Q)
			line3r.set_xdata((np.mean(I),np.sqrt(np.mean(I**2))))
			line3r.set_ydata((np.mean(Q),np.sqrt(np.mean(Q**2))))
			plot1.relim()
			plot1.autoscale()
			plot2.relim()
			plot2.autoscale()
			plot1p.relim()
			plot1p.autoscale()
			plot2p.relim()
			plot2p.autoscale()
			plot3.relim()
			plot3.autoscale()
			
			plt.draw()
			plt.pause(0.1)

			count += 1
	
	def plotFFT(self,logpower=False,autoscale=True):
	# Generates plot of the FFT output. To view, run plotFFT.py in a separate terminal
		figure1 = plt.figure(num= None, figsize=(12,12), dpi=80, facecolor='w', edgecolor='w')
		plot1 = figure1.add_subplot(111)
		line1, = plot1.plot( np.arange(0,512,0.5), np.zeros(1024), 'g-')
		plt.xlabel('freq (MHz)',fontsize = 12)
		if logpower:
			plt.ylabel('Power [dB]',fontsize = 12)
		else:
			plt.ylabel('Amplitude',fontsize = 12)
		
		plt.title('Pre-mixer FFT',fontsize = 12)
		plt.xticks(np.arange(0,512,50))
		plt.xlim((0,512))
		plt.grid()
		plt.show(block = False)
		count = 0 
		stop = 1.0e6
		while(count < stop):
			overflow = np.fromstring(self.fpga.read('overflow', 4), dtype = '>B')
			print overflow
			self.fpga.write_int('fft_snap_ctrl',0)
			self.fpga.write_int('fft_snap_ctrl',1)
			fft_snap = (np.fromstring(self.fpga.read('fft_snap_bram',(2**9)*8),dtype='>i2')).astype('float')
			I0 = fft_snap[0::4]
			Q0 = fft_snap[1::4]
			I1 = fft_snap[2::4]
			Q1 = fft_snap[3::4]
			mag0 = np.sqrt(I0**2 + Q0**2)
			mag1 = np.sqrt(I1**2 + Q1**2)
			if logpower:
				#fft_mags = 20*np.log10(np.hstack(zip(mag0,mag1)))
				fft_mags = 20*np.log10(np.dstack((mag0,mag1)).ravel())
				line1.set_ydata(fft_mags)
				plt.ylim((0,80))
			else:
				#fft_mags = np.hstack(zip(mag0,mag1))
				fft_mags = np.dstack((mag0,mag1)).ravel()
				line1.set_ydata(fft_mags)
				plt.ylim((0,np.max(fft_mags) + 300.))
			if autoscale:
				plot1.relim()
				plot1.autoscale()
			plt.draw()
			plt.pause(0.1)
			count += 1

	def getFFT(self):
		overflow = np.fromstring(self.fpga.read('overflow', 4), dtype = '>B')
		self.fpga.write_int('fft_snap_ctrl',0)
		self.fpga.write_int('fft_snap_ctrl',1)
		fft_snap = (np.fromstring(self.fpga.read('fft_snap_bram',(2**9)*8),dtype='>i2')).astype('float')
		I0 = fft_snap[0::4]
		Q0 = fft_snap[1::4]
		I1 = fft_snap[2::4]
		Q1 = fft_snap[3::4]
		#I  = np.hstack(zip(I0,I1))
		#Q  = np.hstack(zip(Q0,Q1))
		I  = np.dstack((I0,I1)).ravel()
		Q  = np.dstack((Q0,Q1)).ravel()
		return I + 1j*Q
	
	def plotPhase(self, chan):
		#chan = sys.argv[1]
		chan = int(chan) + 2
		count = 0 
		stop = 1.0e6
		while(count < stop):
			time.sleep(0.1)
			I, Q = self.read_accum_snap()
			phase = np.arctan2(Q[chan],I[chan])
			#phase = np.rad2deg(phase)
			print 'Phase =', np.round(phase,10), I[chan], Q[chan]
			count += 1
		return 

	def initialize_GbE(self):
		# Configure GbE Block. Run immediately after calibrating QDR.
		self.fpga.write_int('tx_rst',0)
		self.fpga.write_int('tx_rst',1)
		self.fpga.write_int('tx_rst',0)
		return
	
	def stream_UDP(self, chan, Npackets):
		self.fpga.write_int('pps_start', 1)
		#self.phases = np.empty((len(self.freqs),Npackets))
		phases = np.empty(Npackets)
		tss = np.empty(Npackets)
		count = 0
		while count < Npackets:
			#packet = self.s.recv(8192 + 42) # total number of bytes including 42 byte header
			packet = self.s.recv(8192 ) # total number of bytes including 42 byte header
			#print packet
			#header = np.fromstring(packet[:42],dtype = '<B')
			header=""
			#roach_mac = header[6:12]
			#filter_on = np.array([2, 68, 1, 2, 13, 33])
			#if np.array_equal(roach_mac,filter_on):
			#data = np.fromstring(packet[42:],dtype = '<i').astype('float')
			data = np.fromstring(packet,dtype = '<i').astype('float')
			data /= 2.0**17
			data /= (self.accum_len/512.)
			ts = (np.fromstring(packet[-4:],dtype = '<I').astype('float')/ self.fpga_samp_freq)*1.0e3 # ts in ms
			# To stream one channel, make chan an argument
			if (chan % 2) > 0:
				I = data[1024 + ((chan - 1) / 2)]	
				Q = data[1536 + ((chan - 1) /2)]	
			else:
				I = data[0 + (chan/2)]	
				Q = data[512 + (chan/2)]	
			phase = np.arctan2([Q],[I])
			"""
			odd_chan = self.channels[1::2]
			even_chan = self.channels[0::2]
			I_odd = data[1024 + ((odd_chan - 1) / 2)]	
			Q_odd = data[1536 + ((odd_chan - 1) /2)]	
			I_even = data[0 + (even_chan/2)]	
			Q_even = data[512 + (even_chan/2)]	
			even_phase = np.arctan2(Q_even,I_even)
			odd_phase = np.arctan2(Q_odd,I_odd)
			phase = np.hstack(zip(even_phase, odd_phase))
			self.phases[count] = phase
			"""
			phases[count]=phase
			tss[count]=ts
			print count,ts,phase
			count += 1
		#plt.plot(np.diff(tss))
		#print tss
		#plt.show()
		return 
	
	def target_sweep(self, save_path = '/mnt/iqstream/target_sweeps', write = True, span = 100.0e3):
		write = raw_input('Write ? (y/n) ')
		kid_freqs = np.load('/mnt/iqstream/last_kid_freqs.npy')
		sweep_dir = raw_input('Target sweep dir ? ')
		save_path = os.path.join(save_path, sweep_dir)
		#kid_freqs = np.array(np.loadtxt('BLASTResonatorPositionsVer2.txt', delimiter=','))
		center_freq = (np.max(kid_freqs) + np.min(kid_freqs))/2.   #Determine LO position to put tones centered around LO
		self.vLO.set_frequency(0,center_freq / (1.0e6), 0.01) # LO
		bb_freqs = kid_freqs - center_freq
		if np.all(bb_freqs < 0):
			pass
		elif np.all(bb_freqs > 0):
			pass
		else:
			bb_freqs = np.roll(bb_freqs, - np.argmin(np.abs(bb_freqs)) - 1)
		np.save('/mnt/iqstream/last_bb_freqs.npy',bb_freqs)
		rf_freqs = bb_freqs + center_freq
		np.save('/mnt/iqstream/last_rf_freqs.npy',rf_freqs)
		channels = np.arange(len(rf_freqs))
		np.save('/mnt/iqstream/last_channels.npy',channels)
		self.vLO.set_frequency(0,center_freq / (1.0e6), 0.01) # LO
		print '\nTarget baseband freqs (MHz) =', bb_freqs/1.0e6
		print '\nTarget RF freqs (MHz) =', rf_freqs/1.0e6
		if write == 'y':\
			self.writeQDR(bb_freqs)
		self.fpga.write_int('sync_accum_reset', 0)
		self.fpga.write_int('sync_accum_reset', 1)
		self.sweep_lo(Npackets_per = 10, channels = channels, center_freq = center_freq, span = span , save_path = save_path)
		last_target_dir = save_path
		np.save('/mnt/iqstream/last_target_dir.npy',np.array([last_target_dir]))
		self.plot_kids(save_path = last_target_dir, bb_freqs = bb_freqs, channels = channels)
		#plt.figure()
		#plt.plot()
		return

	def target_sweep_dirfile(self, save_path = '/mnt/iqstream/dirfiles', dirfile_dir=None,write = None, span = None,step=2.5e3,samples_per_point=10,color=None,center_freq=None,kid_freqs=None,lp=(1.0,0.1,0.1),adjust_sideband_leakage=True,auto_fullscale=False,remove_cryostat_input_s21=True,remove_electronics_input_response=True,despike=5.,gains=None,sleep=0.1):
		if write is None:
			write = raw_input('Write tones? (y/n) ')
		if kid_freqs is None:
			kid_freqs = np.load('/mnt/iqstream/last_kid_freqs.npy')
		if dirfile_dir is None:
			dirfile_dir = raw_input('dirfile dir ? ')
		if span is None:
			span = float(raw_input('sweep span [Hz] ? '))
			
		save_path = os.path.join(save_path, dirfile_dir+'_'+str(int(time.time())))
		os.system('mkdir -p %s'%save_path)
		#kid_freqs = np.array(np.loadtxt('BLASTResonatorPositionsVer2.txt', delimiter=','))
		if center_freq==None:
			center_freq = (np.max(kid_freqs) + np.min(kid_freqs))/2.
			center_freq = round(center_freq/1000)*1000
		
		#Determine LO position to put tones centered around LO
		#position to put tones centered around LO
		self.vLO.frequency = center_freq 
		bb_freqs = kid_freqs - center_freq
		if np.all(bb_freqs < 0):
			pass
		elif np.all(bb_freqs > 0):
			pass
		else:
			bb_freqs = np.roll(bb_freqs, - np.argmin(np.abs(bb_freqs)) - 1)
		np.save('/mnt/iqstream/last_bb_freqs.npy',bb_freqs)
		rf_freqs = bb_freqs + center_freq
		np.save('/mnt/iqstream/last_rf_freqs.npy',rf_freqs)
		channels = np.arange(len(rf_freqs))
		print channels
		np.save('/mnt/iqstream/last_channels.npy',channels)
		print '\nTarget baseband freqs (MHz) =', bb_freqs/1.0e6
		print '\nTarget RF freqs (MHz) =', rf_freqs/1.0e6
		if write == 'y':\
			self.writeQDR(bb_freqs,adjust_sideband_leakage=adjust_sideband_leakage,auto_fullscale=auto_fullscale,remove_cryostat_input_s21=remove_cryostat_input_s21,remove_electronics_input_response=remove_electronics_input_response,lo_frequency=center_freq,gains=gains)
		self.fpga.write_int('sync_accum_reset', 0)
		self.fpga.write_int('sync_accum_reset', 1)
		
		print save_path,gd.CREAT|gd.RDWR
		
		dirf = gd.dirfile(save_path,gd.CREAT|gd.RDWR)
		symlink_path = '/mnt/iqstream/active_dirfile.lnk'
		try:
			os.unlink(symlink_path)
		except:
			pass
		os.symlink(save_path,symlink_path)
		
		for chan in range(1024):
			dirf.add(gd.entry(gd.RAW_ENTRY,'I%04d'%chan,0,(gd.FLOAT64,1)))
			dirf.add(gd.entry(gd.RAW_ENTRY,'Q%04d'%chan,0,(gd.FLOAT64,1)))
		dirf.close()
		
		f,i,q = self.sweep_lo_dirfile(Npackets_per = samples_per_point, channels = channels, center_freq = center_freq, span = span, bb_freqs=bb_freqs,  save_path = save_path,step=step,sleep=sleep)
		
		fig=plt.figure('target sweep')
		p1=plt.subplot(211)
		plt.ylabel('S21 [dB]')
		for ch in range(len(f)):
			if color is None:
				plt.plot(f[ch],20*np.log10(np.sqrt(i[ch]**2+q[ch]**2)))
			else:
				plt.plot(f[ch],20*np.log10(np.sqrt(i[ch]**2+q[ch]**2)),color=color)
			text(f[ch][len(f[ch])/2],0,' '+str(ch))
		#p2=plt.subplot(212,sharex=p1)
		#plt.ylabel('Phase [rad]')
		#for ch in range(len(f)):
			#if color is None:
				#plt.plot(f[ch],np.unwrap(np.arctan2(q[ch],i[ch])))
			#else:
				#plt.plot(f[ch],np.unwrap(np.arctan2(q[ch],i[ch])),color=color)
		#plt.draw()
		p2=plt.subplot(212,sharex=p1)
		plt.ylabel('di**2+dq**2 ')
		for ch in range(len(f)):
			F,I,Q = f[ch],i[ch],q[ch]
			didq = np.sqrt((np.diff(I)/np.diff(F))**2+(np.diff(Q)/np.diff(F))**2)
			#didq_f = np.diff(lowpass_cosine(I,lp[0],lp[1],lp[2]))**2+np.diff(lowpass_cosine(Q,lp[0],lp[1],lp[2]))**2
			didq_f = lowpass_cosine(didq,lp[0],lp[1],lp[2])
				
			if color is None:
				p=plt.plot(F[1:],didq,   alpha=1)
				p=plt.plot(F[1:],didq_f, color=p[0].get_color(),alpha=0.5,lw=3)
				
			else:
				p=plt.plot(F[1:],didq,   alpha=1,color=color)
				p=plt.plot(F[1:],didq_f, color=color,alpha=0.5,lw=3)
			plt.vlines(F[len(F)/2.],0,didq_f[len(F)/2.-1],lw=4,alpha=0.5)
		plt.tight_layout()
		plt.draw()
		
		
		self.write_dirfile_format_file(save_path,f,i,q)
		
		last_target_dir = save_path
		np.save('/mnt/iqstream/last_target_dir.npy',np.array([last_target_dir]))
		#self.plot_kids_dirfile(save_path = last_target_dir, channels = channels)
		#plt.figure()
		#plt.plot()
		np.save('/mnt/iqstream/last_target_sweep.npy',np.array((f,i,q)))
		
		return f, i, q 

	def write_dirfile_format_file(self,dirfile_path, f, i, q):
		#print f
		#print i
		#print q
		
		print "Writing format file"
		dirf=gd.dirfile(dirfile_path,gd.RDWR)
		print 'including format file fragments...','format_sweep','format_calibration'
		sweepfrag = dirf.include('sweep',flags=gd.CREAT)
		calfrag   = dirf.include('calibration',flags=gd.CREAT)
		
		for chan,(ff,ii,qq) in enumerate(zip(f,i,q)):

			di = np.diff(ii)
			dq = np.diff(qq)
			mididx=ff.size//2
			df = ff[mididx+1]-ff[mididx]
			f_tone = ff[mididx]
			i_tone  = ii[mididx]
			q_tone  = qq[mididx]
			di_tone = di[mididx]
			dq_tone = dq[mididx]
			#di_tone = np.mean(di[mididx-1:mididx+1])
			#dq_tone = np.mean(dq[mididx-1:mididx+1])
			didf_tone = di_tone/df
			dqdf_tone = dq_tone/df
			c,r = self.least_sq_circle(ii,qq)
			phi_tone = np.arctan2(q_tone-c[1],i_tone-c[0])


			#Sweeps
			dirf.add(gd.entry(gd.CARRAY_ENTRY,'sweep_f_%04d'%chan,sweepfrag,(gd.FLOAT64,ff.size)))
			dirf.add(gd.entry(gd.CARRAY_ENTRY,'sweep_i_%04d'%chan,sweepfrag,(gd.FLOAT64,ff.size)))
			dirf.add(gd.entry(gd.CARRAY_ENTRY,'sweep_q_%04d'%chan,sweepfrag,(gd.FLOAT64,ff.size)))
			dirf.put_carray('sweep_f_%04d'%chan,ff)
			dirf.put_carray('sweep_i_%04d'%chan,ii)
			dirf.put_carray('sweep_q_%04d'%chan,qq)

			##Resonant Frequency
			#dirf.add(gd.entry(gd.CONST_ENTRY,'cal_res_freq_%04d'%chan,calfrag,(gd.FLOAT64,)))
			#dirf.put_constant('cal_res_freq_%04d'%chan,fres)

			#Tone Frequency
			dirf.add(gd.entry(gd.CONST_ENTRY,'_cal_tone_freq_%04d'%chan,calfrag,(gd.FLOAT64,)))
			dirf.put_constant('_cal_tone_freq_%04d'%chan,f_tone) 

			#i-i0 q-q0
			dirf.add(gd.entry(gd.LINCOM_ENTRY,'_cal_i_sub_i0_%04d'%chan,calfrag,
			(("I%04d"%chan,),(1,),(-1*i_tone,))))
			dirf.add(gd.entry(gd.LINCOM_ENTRY,'_cal_q_sub_q0_%04d'%chan,calfrag,
			(("Q%04d"%chan,),(1,),(-1*q_tone,))))
			

			#Complex values
			dirf.add(gd.entry(gd.LINCOM_ENTRY,'_cal_complex_%04d'%chan,calfrag,
			(("I%04d"%chan,"Q%04d"%chan),(1,1j),(0,0))))

			#Amplitude
			dirf.add(gd.entry(gd.PHASE_ENTRY,'amplitude_%04d'%chan,calfrag,
			(('_cal_complex_%04d.m'%chan),0)))

			#Phase
			dirf.add(gd.entry(gd.LINCOM_ENTRY,'phase_raw_%04d'%chan,calfrag,
			(('_cal_complex_%04d.a'%chan,),(1,1j),(0,))))
				
			#Complex_centered:    
			dirf.add(gd.entry(gd.LINCOM_ENTRY,'_cal_centred_%04d'%chan,calfrag,
			(("_cal_complex_%04d"%chan,),(1,),(-c[0]-1j*c[1],))))

			#Complex_rotated
			dirf.add(gd.entry(gd.LINCOM_ENTRY,'_cal_rotated_%04d'%chan,calfrag,
			(("_cal_centred_%04d"%chan,),(np.exp(-1j*phi_tone),),(0,))))

			#Phase
			dirf.add(gd.entry(gd.LINCOM_ENTRY,'phase_rotated_%04d'%chan,calfrag,
			(('_cal_rotated_%04d.a'%chan,),(1,),(0,))))
			
			#df = ((i[0]-i)(di/df) + (q[0]-q)(dq/df) ) / ((di/df)**2 + (dq/df)**2)
			dirf.add(gd.entry(gd.CONST_ENTRY,'_cal_didf_mult_%04d'%chan,calfrag,(gd.FLOAT64,)))
			dirf.add(gd.entry(gd.CONST_ENTRY,'_cal_dqdf_mult_%04d'%chan,calfrag,(gd.FLOAT64,)))
			dirf.put_constant('_cal_didf_mult_%04d'%chan,didf_tone/(didf_tone**2+dqdf_tone**2))
			dirf.put_constant('_cal_dqdf_mult_%04d'%chan,dqdf_tone/(didf_tone**2+dqdf_tone**2))
			dirf.add(gd.entry(gd.LINCOM_ENTRY,'_cal_i0_sub_i_%04d'%chan,calfrag,
				(("I%04d"%chan,),(-1,),(i_tone,))))
			dirf.add(gd.entry(gd.LINCOM_ENTRY,'_cal_q0_sub_q_%04d'%chan,calfrag,
				(("Q%04d"%chan,),(-1,),(q_tone,))))
			dirf.add(gd.entry(gd.LINCOM_ENTRY, 'delta_f_%04d'%chan, calfrag,
				(("_cal_i0_sub_i_%04d"%chan,"_cal_q0_sub_q_%04d"%chan),
				("_cal_didf_mult_%04d"%chan,"_cal_dqdf_mult_%04d"%chan),
				(0,0))))
			
			#x = df/f0
			dirf.add(gd.entry(gd.LINCOM_ENTRY,'x_%04d'%chan,calfrag,
				(('delta_f_%04d'%chan,),(1./f_tone,),(0,))))

		dirf.close()
	
	def least_sq_circle(self,x,y,xc_guess=None,yc_guess=None):
		"""
		Least squares fitting of circles to a 2d data set. 
		Calcultes jacobian matrix to speed up scipy.optimize.least_sq. 
		Complements to scipy.org
		Returns the center and radius of the circle ((xc,yc), r)
		"""
		from numpy import array, sqrt, empty, newaxis
		from scipy import optimize

		x,y = array(x),array(y)
		
		if xc_guess == None:
		  xc_guess = x.mean()
		if yc_guess == None:
		  yc_guess = y.mean()
		
		def calc_radius(xc, yc):
			""" calculate the distance of each data points from the center (xc, yc) """
			return sqrt((x-xc)**2 + (y-yc)**2)

		def f(c):
			""" calculate f, the algebraic distance between the 2D points and the mean circle centered at c=(xc, yc) """
			Ri 	= calc_radius(*c)
			return Ri - Ri.mean()

		def Df(c):
			""" Jacobian of f.The axis corresponding to derivatives must be coherent with the col_deriv option of leastsq"""
			xc, yc  	= c
			dfdc    	= empty((len(c), x.size))

			Ri 	= calc_radius(xc, yc)
			dfdc[0] 	= (xc - x)/Ri            # dR/dxc
			dfdc[1] 	= (yc - y)/Ri            # dR/dyc
			dfdc   	= dfdc - dfdc.mean(axis=1)[:, newaxis]

			return dfdc
		
		center_guess = xc_guess, yc_guess
		center, success = optimize.leastsq(f, center_guess, Dfun=Df, col_deriv=True)

		xc, yc = center
		Ri        = calc_radius(*center)
		R         = Ri.mean()
		residual  = sum((Ri - R)**2)
		
		return (xc,yc),R
	
	

	def vna_sweep(self, center_freq = 750.0e6, save_path = '/mnt/iqstream/vna_sweeps', write = True):
		write = raw_input('Write tones ? (y/n)')
		sweep_dir = raw_input('VNA sweep dir ? ')
		save_path = os.path.join(save_path, sweep_dir)
		bb_freqs, delta_f = np.linspace(-255.5e6, 255.5e6, 1023,retstep=True)
		bb_freqs = np.roll(bb_freqs, - np.argmin(np.abs(bb_freqs)) - 1)
		np.save('/mnt/iqstream/last_bb_freqs.npy',bb_freqs)
		rf_freqs = bb_freqs + center_freq
		np.save('/mnt/iqstream/last_rf_freqs.npy',rf_freqs)
		channels = np.arange(len(rf_freqs))
		np.save('/mnt/iqstream/last_channels.npy',channels)
		self.vLO.set_frequency(0,center_freq , 0.01) # LO
		print '\nVNA baseband freqs (MHz) =', bb_freqs/1.0e6
		print '\nVNA RF freqs (MHz) =', rf_freqs/1.0e6
		if write=='y':
			self.writeQDR(bb_freqs)
		self.fpga.write_int('sync_accum_reset', 0)
		self.fpga.write_int('sync_accum_reset', 1)
		self.sweep_lo(Npackets_per = 10, channels = channels, center_freq = center_freq, span = delta_f, save_path = save_path)
		last_vna_dir = save_path
                np.save('/mnt/iqstream/last_vna_dir.npy',np.array([last_vna_dir]))
		self.plot_kids(save_path = last_vna_dir, bb_freqs = bb_freqs, channels = channels)
		return
	
	def vna_sweep_dirfile(self, center_freq = None, save_path = '/mnt/iqstream/vna_sweeps', write = None,sweep_dir=None,randomiser=0,samples_per_point=10,num_tones=256,sweep_step=2.5e3,adjust_sideband_leakage=True,auto_fullscale=False,remove_cryostat_input_s21=True,remove_electronics_input_response=True,plot=True,gains=None):
		if write is None:
			write = raw_input('Write tones ? (y/n)')
		if sweep_dir is None:
			sweep_dir = raw_input('VNA sweep dir ? ')
		if center_freq is None:
			center_freq = float(raw_input('Center Frequency ? '))
		
		save_path = os.path.join(save_path, sweep_dir)
		
		bb_freqs, delta_f = np.linspace(-255.5e6, 255.5e6, num_tones,retstep=True)
		
		if randomiser is not None:
			bb_freqs += randomiser
		for ch in range(len(bb_freqs)-1):
			#if np.round(abs(bb_freqs[ch]),-3) in np.around(bb_freqs[ch+1:],-3):
			if (np.around(abs(bb_freqs[ch])/self.dac_freq_res))*self.dac_freq_res in np.around(bb_freqs[ch+1:]/self.dac_freq_res)*self.dac_freq_res:
				#print '*****FOUND******'
				bb_freqs[ch] += 2*self.dac_freq_res
		bb_freqs = np.roll(bb_freqs, - np.argmin(np.abs(bb_freqs)) - 1)
		np.save('/mnt/iqstream/last_bb_freqs.npy',bb_freqs)
		rf_freqs = bb_freqs + center_freq
		np.save('/mnt/iqstream/last_rf_freqs.npy',rf_freqs)
		channels = np.arange(len(rf_freqs))
		np.save('/mnt/iqstream/last_channels.npy',channels)
		#self.vLO.set_frequency(0,center_freq , 0.01) # LO
		self.vLO.frequency = center_freq
		print '\nVNA baseband freqs (MHz) =', bb_freqs/1.0e6
		print '\nVNA RF freqs (MHz) =', rf_freqs/1.0e6
		if write=='y' or write is True:
			self.writeQDR(bb_freqs,adjust_sideband_leakage=adjust_sideband_leakage,auto_fullscale=auto_fullscale,remove_cryostat_input_s21=remove_cryostat_input_s21,remove_electronics_input_response=remove_electronics_input_response,lo_frequency=center_freq,gains=gains)
		self.fpga.write_int('sync_accum_reset', 0)
		self.fpga.write_int('sync_accum_reset', 1)
		f,i,q = self.sweep_lo_dirfile(Npackets_per = samples_per_point, channels = channels, center_freq = center_freq, span = delta_f, save_path = save_path,bb_freqs=bb_freqs,step = sweep_step)
		last_vna_dir = save_path
                np.save('/mnt/iqstream/last_vna_dir.npy',np.array([last_vna_dir]))
		np.save('/mnt/iqstream/last_vna_sweep.npy',np.array([f,i,q]))
		#self.plot_kids(save_path = last_vna_dir, bb_freqs = bb_freqs, channels = channels)
		if plot:
			plt.figure('vna-sweep-dirfile')
			for ch in channels:
				plt.plot(f[ch],10*np.log10(i[ch]**2+q[ch]**2))
			plt.show()
		return f,i,q
	
	def vna_sweep_dirfile_BinCenter(self, center_freq = None, save_path = '/mnt/iqstream/vna_sweeps', write = True,randomiser=0,samples_per_point=10,num_tones=256,sweep_step=2.5e3):
		write = raw_input('Write tones ? (y/n)')
		sweep_dir = raw_input('VNA sweep dir ? ')
		if center_freq is None:
			center_freq = float(raw_input('Center Frequency ? '))
		
		save_path = os.path.join(save_path, sweep_dir)
		
		#set tone freqs to bin centers 
		bin_centers     = np.fft.fftshift(np.fft.fftfreq(self.fft_len,1./self.dac_samp_freq))
		bin_width       = bin_centers[1]-bin_centers[0]
		skip_bins_count = self.fft_len/num_tones
		
		bb_freqs       = bin_centers[skip_bins_count/2::skip_bins_count]
		delta_f        = bb_freqs[1]-bb_freqs[0]
		#bb_freqs[bb_freqs<0] += delta_f/2. #avoiding overlap of pos/neg bins?
		
		lo_center_freq = center_freq
		lo_span        = delta_f
		
		
		if randomiser is not None:
			bb_freqs += randomiser
		for ch in range(len(bb_freqs)-1):
			#if np.round(abs(bb_freqs[ch]),-3) in np.around(bb_freqs[ch+1:],-3):
			if (np.around(abs(bb_freqs[ch])/self.dac_freq_res))*self.dac_freq_res in np.around(bb_freqs[ch+1:]/self.dac_freq_res)*self.dac_freq_res:
				print '*****FOUND******'
				bb_freqs[ch] += self.dac_freq_res
		bb_freqs = np.roll(bb_freqs, - np.argmin(np.abs(bb_freqs)) - 1)
		np.save('/mnt/iqstream/last_bb_freqs.npy',bb_freqs)
		rf_freqs = bb_freqs + lo_center_freq
		np.save('/mnt/iqstream/last_rf_freqs.npy',rf_freqs)
		channels = np.arange(len(rf_freqs))
		np.save('/mnt/iqstream/last_channels.npy',channels)
		#self.vLO.set_frequency(0,center_freq , 0.01) # LO
		self.vLO.frequency = lo_center_freq
		print '\nVNA baseband freqs (MHz) =', bb_freqs/1.0e6
		print '\nVNA RF freqs (MHz) =', rf_freqs/1.0e6
		if write=='y':
			self.writeQDR(bb_freqs)
		self.fpga.write_int('sync_accum_reset', 0)
		self.fpga.write_int('sync_accum_reset', 1)
		f,i,q = self.sweep_lo_dirfile(Npackets_per = samples_per_point, channels = channels, center_freq = lo_center_freq, span = lo_span, save_path = save_path,bb_freqs=bb_freqs,step = sweep_step)
		last_vna_dir = save_path
                np.save('/mnt/iqstream/last_vna_dir.npy',np.array([last_vna_dir]))
		np.save('/mnt/iqstream/last_vna_sweep.npy',np.array([f,i,q]))
		#self.plot_kids(save_path = last_vna_dir, bb_freqs = bb_freqs, channels = channels)
		for ch in channels:
			plt.plot(f[ch],10*np.log10(i[ch]**2+q[ch]**2))
		plt.show()
		return f,i,q
	
	def sweep_lo(self, Npackets_per = 10, channels = None, center_freq = 750.0e6, span = 2.0e6, save_path = '/mnt/iqstream/lo_sweeps'):
		N = Npackets_per
		start = center_freq - (span/2.)
		stop = center_freq + (span/2.) 
		step = 2.5e3
		sweep_freqs = np.arange(start, stop, step)
		sweep_freqs = np.round(sweep_freqs/step)*step
		print 'Sweep freqs =', sweep_freqs
		if os.path.exists(save_path):
			[os.remove(os.path.join(save_path,fl)) for fl in os.listdir(save_path)]
		else:
			os.mkdir(save_path)
		for freq in sweep_freqs:
			print 'Sweep freq =', freq
			if self.vLO.set_frequency(0, freq, 0.01): 
				time.sleep(0.1)
				self.store_UDP(N,freq, save_path,channels=channels) 
		self.vLO.set_frequency(0,center_freq , 0.01) # LO
		return
        
        def sweep_lo_dirfile(self, Npackets_per = 10, channels = None,center_freq = 750.0e6, span = 2.0e6, bb_freqs=None,save_path = '/mnt/iqstream/lo_sweeps', skip_packets=1,step=1000.,sleep=0.1):
		if channels==None:
			channels = np.arange(len(self.freqs))
		if bb_freqs==None:
			bb_freqs = self.freqs-center_freq
		
		N = Npackets_per
		start = center_freq - (span/2.)
		stop = center_freq + (span/2.) 
		
		sweep_freqs = np.arange(start, stop, step)
		sweep_freqs = np.round(sweep_freqs/step)*step
		print 'Sweep freqs =', sweep_freqs,'       \r',;sys.stdout.flush()
	 	f=np.empty((len(channels),sweep_freqs.size))
	 	i=np.empty((len(channels),sweep_freqs.size))
		q=np.empty((len(channels),sweep_freqs.size))
		for count,freq in enumerate(sweep_freqs):
			print 'Sweep freq =', freq
			if self.vLO.set_frequency(2, freq, 0.01,fast=True): 
				#if count==0:
					#time.sleep(1)
				time.sleep(sleep)
				#flush udp buffer to get rid bad first few packets!!
				i_buffer,q_buffer = self.get_UDP(N, freq, skip_packets=skip_packets, channels=channels,clearbuf=True,fast_packets=True,silent=True)
				f[:,count]=freq+bb_freqs
				i[:,count]=np.mean(i_buffer,axis=0)
				q[:,count]=np.mean(q_buffer,axis=0)
			else:
				time.sleep(sleep)
				f[:,count]=freq+bb_freqs
				i[:,count]=np.nan
				q[:,count]=np.nan
		self.vLO.set_frequency(2,center_freq, 0.01,fast=True) # LO
		
		return f, i, q
	
	def get_timestamp(self,Npackets,clearbuf=True):
		ts = self.get_UDP(Npackets,timestamp=True,clearbuf=clearbuf)
	
	def get_df(self,i,q,sf,si,sq,tone_freq):
		di = np.diff(si)
		dq = np.diff(sq)
		tone_idx=np.argmin(abs(sf-tone_freq))
		df = (sf[tone_idx+1]-sf[tone_idx-1])/2.
		#tone_idx=sf.size//2
		f_tone = sf[tone_idx]
		i_tone  = si[tone_idx]
		q_tone  = sq[tone_idx]
		di_tone = di[tone_idx]
		dq_tone = dq[tone_idx]
		#di_tone = np.mean(di[tone_idx-1:tone_idx+1])
		#dq_tone = np.mean(dq[tone_idx-1:tone_idx+1])
		didf_tone = di_tone/df
		dqdf_tone = dq_tone/df
		
		df = ((i-i_tone)*(didf_tone) + (q-q_tone)*(dqdf_tone) ) / ((didf_tone)**2 + (dqdf_tone)**2)
		return df
	
	def get_UDP(self, Npackets, LO_freq=0, skip_packets=0, channels = None,clearbuf=False,timestamp=False,fast_packets = False,ret_df=False,sweep=None,silent=False):
		#Npackets = np.int(time_interval * self.accum_freq)
		
		if channels == None:
			channels = np.arange(1024)
		allchannels = np.arange(1024)
		self.fpga.write_int('pps_start', 1)
		
		#if clearbuf:
			#for i in range(8*self.sockbufsize/8192):
				#try:
					#dump = self.s.recv(8192)
				#except timeout:
					#break
		if clearbuf:
			while True:
				try:
					dump = self.s.recv(8192)
				except:
					break
		
		if fast_packets:
			if not silent:
				print 'Receiving...'
			#self.packet_dump = np.full(Npackets+skip_packets,'\xFF'*8192,dtype='|S8192')
			self.packet_dump = []
			for i in range(Npackets+skip_packets):
				#self.packet_dump[i] = self.s.recv(8192)
				while True:
					try:
						self.packet_dump.append(self.s.recv(8192))
						break
					except:
						continue
			if not silent:
				print 'Processing...'

		count = 0
		while count < Npackets + skip_packets:
			if fast_packets:
				packet = self.packet_dump[count]
			else:
				packet = self.s.recv(8192) 
			data = np.fromstring(packet,dtype = '<i',count=2048).astype('float')
			data /= 2.0**17
			data /= (self.accum_len/512.)
			if timestamp:
				ts = (np.fromstring(packet[-4:],dtype = '>I').astype('float')/self.fpga_samp_freq)*1.0e3 # ts in ms
				ts = (np.fromstring(packet[-8:-4],dtype = '>I').astype('float')/self.fpga_samp_freq)*1.0e3 # ts in ms
				self.ts_buffer[count] = ts
			
			#odd_chan = allchannels[1::2]
			#even_chan = allchannels[0::2]
			#I_odd = data[1024 + ((odd_chan - 1) / 2)]	
			#Q_odd = data[1536 + ((odd_chan - 1) /2)]	
			#I_even = data[0 + (even_chan/2)]	
			#Q_even = data[512 + (even_chan/2)]	
			##even_phase = np.arctan2(Q_even,I_even)
			##odd_phase = np.arctan2(Q_odd,I_odd)
			#if len(allchannels) % 2 > 0:
				#I = np.hstack(zip(I_even[:len(I_odd)], I_odd))
				#Q = np.hstack(zip(Q_even[:len(Q_odd)], Q_odd))
				#I = np.hstack((I, I_even[-1]))	
				#Q = np.hstack((Q, Q_even[-1]))	
				#self.I_buffer[count] = I
				#self.Q_buffer[count] = Q
			#else:
				#I = np.hstack(zip(I_even, I_odd))
				#Q = np.hstack(zip(Q_even, Q_odd))
				#self.I_buffer[count] = I
				#self.Q_buffer[count] = Q
			
			#odd_chan = allchannels[1::2]
			#even_chan = allchannels[0::2]
			I_odd = data[1024 + ((allchannels[1::2] - 1) / 2)]	
			Q_odd = data[1536 + ((allchannels[1::2] - 1) /2)]	
			I_even = data[0 + (allchannels[0::2]/2)]	
			Q_even = data[512 + (allchannels[0::2]/2)]	
			#even_phase = np.arctan2(Q_even,I_even)
			#odd_phase = np.arctan2(Q_odd,I_odd)
			if len(allchannels) % 2 > 0:
				#I = np.hstack(zip(I_even[:len(I_odd)], I_odd))
				#Q = np.hstack(zip(Q_even[:len(Q_odd)], Q_odd))
				I = np.dstack((I_even[:len(I_odd)], I_odd)).ravel()
				Q = np.dstack((Q_even[:len(Q_odd)], Q_odd)).ravel()
				I = np.hstack((I, I_even[-1]))
				Q = np.hstack((Q, Q_even[-1]))
				self.I_buffer[count] = I
				self.Q_buffer[count] = Q
			else:
				#I = np.hstack(zip(I_even, I_odd))
				#Q = np.hstack(zip(Q_even, Q_odd))
				I = np.dstack((I_even, I_odd)).ravel()
				Q = np.dstack((Q_even, Q_odd)).ravel()
				self.I_buffer[count] = I
				self.Q_buffer[count] = Q
			
				
			count += 1
		if timestamp == True:
			return self.ts_buffer[skip_packets:Npackets+skip_packets]
		else:
			if ret_df:
				print 'Calculating df...'
				I,Q = np.array([self.I_buffer[skip_packets:Npackets+skip_packets],self.Q_buffer[skip_packets:Npackets+skip_packets]])[:,:,channels]
				sf,si,sq,= sweep
				df= np.zeros((len(sf),len(I[:,0])),dtype=float)
				for j in range(len(sf)):
					df[j] = self.get_df(I[:,j],Q[:,j],sf[j],si[j],sq[j],sf[j][sf[j].size/2])
				
				return df
			else:
				return np.array([self.I_buffer[skip_packets:Npackets+skip_packets],self.Q_buffer[skip_packets:Npackets+skip_packets]])[:,:,channels]
				
        #def get_UDP(self, Npackets, LO_freq=0, skip_packets=2, channels = None,clearbuf=False,timestamp=False,fast_packets = False):
		##Npackets = np.int(time_interval * self.accum_freq)
		#if channels == None:
			#channels = np.arange(1024)
		
		#self.fpga.write_int('pps_start', 1)
		
		#if clearbuf:
			##self.s.settimeout(1)
			#for i in range(50):
				#try:
					#dump = self.s.recv(8192)
				#except timeout:
					#break
			##self.s.settimeout(None)
					
			
		#if fast_packets:
			#packet_dump = []
			#for i in range(Npackets+skip_packets):
				#packet_dump.append(self.s.recv(8192))
		
		#count = 0
		#while count < Npackets + skip_packets:
			#if fast_packets:
				#packet = packet_dump[count]
			#else:
				#packet = self.s.recv(8192) 
			#data = np.fromstring(packet,dtype = '<i').astype('float')
			#data /= 2.0**17
			#data /= (self.accum_len/512.)
			#if timestamp:
				#ts = (np.fromstring(packet[-4:],dtype = '<I').astype('float')/self.fpga_samp_freq)*1.0e3 # ts in ms
				#self.ts_buffer[count] = ts
			
			#odd_chan = channels[1::2]
			#even_chan = channels[0::2]
			#I_odd = data[1024 + ((odd_chan - 1) / 2)]	
			#Q_odd = data[1536 + ((odd_chan - 1) /2)]	
			#I_even = data[0 + (even_chan/2)]	
			#Q_even = data[512 + (even_chan/2)]	
			#even_phase = np.arctan2(Q_even,I_even)
			#odd_phase = np.arctan2(Q_odd,I_odd)
			#if len(channels) % 2 > 0:
				#I = np.hstack(zip(I_even[:len(I_odd)], I_odd))
				#Q = np.hstack(zip(Q_even[:len(Q_odd)], Q_odd))
				#I = np.hstack((I, I_even[-1]))	
				#Q = np.hstack((Q, Q_even[-1]))	
				#self.I_buffer[count] = I
				#self.Q_buffer[count] = Q
			#else:
				#I = np.hstack(zip(I_even, I_odd))
				#Q = np.hstack(zip(Q_even, Q_odd))
				#self.I_buffer[count] = I
				#self.Q_buffer[count] = Q
			
				
			#count += 1
		#if timestamp == True:
			#return self.ts_buffer[skip_packets:Npackets+skip_packets]
		#else:
			#return np.array([self.I_buffer[skip_packets:Npackets+skip_packets],self.Q_buffer[skip_packets:Npackets+skip_packets]])
			    
	def store_UDP(self, Npackets, LO_freq, save_path, skip_packets=0, channels = None):
		
		I_buffer,Q_buffer = self.get_UDP(self, Npackets, LO_freq=LO_freq, save_path=save_path, skip_packets=skip_packets, channels = channels)
		I_file = 'I' + str(LO_freq)
		Q_file = 'Q' + str(LO_freq)
		np.save(os.path.join(save_path,I_file), np.mean(I_buffer[skip_packets:], axis = 0)) 
		np.save(os.path.join(save_path,Q_file), np.mean(Q_buffer[skip_packets:], axis = 0)) 
		return 
	
	def stream_KID_response(self,t_window=5,update_time=5,measure='amplitude',normalise=True,channels=None,fftsize=None,lockin_f = 7.75,lockin_bw=1):
		fig=plt.figure('stream '+measure,figsize=(15,10))
		p1=plt.subplot(211)
		p2=plt.subplot(212)
		packets0 = int(self.accum_freq*t_window)
		i0,q0 = self.get_UDP(packets0,0,skip_packets=0)
		i0=i0.swapaxes(0,1)
		q0=q0.swapaxes(0,1)
		z0=i0+1j*q0
		if channels is None:
			channels = np.arange(len(z0))
		normA = 1
		normB = 0
		if   measure == 'amplitude':
			values = np.abs(z0)
			normA = np.mean(values,axis=1)
			normB = np.zeros_like(values)
		elif measure == 'phase':
			values = np.angle(z0)
			normA = np.ones_like(values)
			normB = np.mean(values,axis=1)
		elif measure == 'i':
			values = z0.real
			normA = np.mean(values,axis=1)
			normB = np.zeros_like(values)
		elif measure == 'q':
			values = z0.imag
			normA = np.mean(values,axis=1)
			normB = np.zeros_like(values)
		else:
			raise ValueError, 'unknown measurable: \'%s\''%measure
		mean0 = np.mean(values,axis=1)
		t=np.linspace(0,t_window,z0[0].size)
		#fftsize=len(
		if fftsize==None:
			fftsize=int(2**np.floor(np.log2(i0[0].size)))
		
		p1.set_ylabel(measure)
		p1.set_xlabel('time [s]')
		p2.set_ylabel('PSD(%s) [dB/Hz]'%measure)
		p2.set_xlabel('frequency [Hz]')
		p1.grid()
		p2.grid()
		p2.grid('on','minor','x')
		colours = plt.cm.Set1_r(np.linspace(0,1,len(channels)+1))
		l1=[]
		l2=[]
		for ch in range(len(channels)):
			#plot data
			#l1.append(p1.plot(t,values[ch]/normA[ch]-normB[ch],color=colours[ch],alpha=0.5)[0])
			#plot spectrum
			p,f = plt.mlab.psd(values[ch], fftsize, Fs=self.accum_freq, detrend=plt.mlab.detrend_linear, window=plt.mlab.window_hanning, noverlap=fftsize/2, pad_to=None, sides='default', scale_by_freq=True)
			l2.append(plt.semilogx(f,10*np.log10(p),color=colours[ch],alpha=0.5)[0])
			
			lockin_idx = np.where((f>=lockin_f-lockin_bw/2.) & (f<=lockin_f+lockin_bw/2.))
			print 10*np.log10(np.sum(p[lockin_idx]))
			
		p2.axvline(lockin_f-lockin_bw/2.)
		p2.axvline(lockin_f+lockin_bw/2.)
		p2.set_xlim(1./t_window*len(t)/fftsize,self.accum_freq/2.),
		plt.draw()
		packets = int(self.accum_freq*update_time)
		#t=np.linspace(0,time,z0[0].size)
		counter=0
		while True:
			counter+=1
			lockins = []
			t0=time.time()
			i,q = self.get_UDP(packets,0,skip_packets=0)
			i=i.swapaxes(0,1)
			q=q.swapaxes(0,1)
			z=i+1j*q
			values=np.roll(values,-1*packets,axis=1)
			if   measure == 'amplitude':
				values[:,-packets:] = np.abs(z)
			elif measure == 'phase':
				values[:,-packets:] = np.angle(z)
			elif measure == 'i':
				values[:,-packets:] = z.real
			elif measure == 'q':
				values[:,-packets:] = z.imag
			else:
				raise ValueError, 'unknown measurable: \'%s\''%measure
			plt.figure('stream phase')
			for ch in range(len(channels)):
				#plot data
				#l1[ch].set_ydata(values[ch]/normA[ch]-normB[ch])
				#plot spectrum
				p,f = plt.mlab.psd(values[ch], fftsize, Fs=self.accum_freq, detrend=plt.mlab.detrend_linear, window=plt.mlab.window_hanning, noverlap=fftsize/2, pad_to=None, sides='default', scale_by_freq=True)
				l2[ch].set_ydata(10*np.log10(p))
				
				lockin_idx = np.where((f>=lockin_f-lockin_bw/2.) & (f<=lockin_f+lockin_bw/2.))
				lockin_sum = np.sum(p[lockin_idx])
				print 10*np.log10(lockin_sum)
				lockins.append(lockin_sum)
			p1.relim()
			p1.autoscale_view(True,True,True)
			p2.relim()
			p2.autoscale_view(True,True,True)
			
			plt.pause(0.1)
			plt.figure('lockin')
			plt.plot(counter,5*np.log10(lockins[1]),'o')
			plt.draw()
			plt.pause(0.1)
			while time.time()-t0 < update_time:
				pass
				
			print time.time()-t0
	
	def stream_UDP_dirfile(self,save_path=None,bufsize = int(244*0.2),duration=np.inf):
		#open files
		"""
		must set max open files higher:
		>sysctl -2 fs.file-max=100000
		>echo fs.file-max=100000 >> /etc/sysctl.con
		>sysctl -p
		"""
		if save_path==None:
			save_path = '/mnt/iqstream/active_dirfile.lnk'
		channels=range(1024)
		print channels
		print save_path
		files=[]
		#even files
		for i in range(len(channels))[::2]:
			files.append(open(os.path.join(save_path,'I%04d'%i),'w'))
		for i in range(len(channels))[::2]:
			files.append(open(os.path.join(save_path,'Q%04d'%i),'w'))
		#odd files
		for i in range(len(channels))[1::2]:
			files.append(open(os.path.join(save_path,'I%04d'%i),'w'))
		for i in range(len(channels))[1::2]:
			files.append(open(os.path.join(save_path,'Q%04d'%i),'w'))

		#write to files
		buf=np.empty(len(channels)*2*bufsize,dtype='float64')
		packets = round(duration * self.accum_freq)
		scale_factor = 2.0**17 / (self.accum_len/512.)
		try:
			counter=0  
			while(counter < packets):
				for i in range(bufsize):
					packet=self.s.recv(8192)
					data=np.fromstring(packet,dtype = '<i').astype('float64')
					data /= scale_factor
					buf[i::bufsize]=data
				for i in range(len(channels)*2):
					files[i].write(buf[i*bufsize:(i+1)*bufsize].tostring())
		except KeyboardInterrupt:
			pass
		[i.close() for i in files]
		print 'closed'
		return
		
		
	
	def store_UDP_noavg(self, Npackets, LO_freq, save_path, skip_packets=2, channels = None):
		#Npackets = np.int(time_interval * self.accum_freq)
		I_buffer = np.empty((Npackets + skip_packets, len(channels)))
		Q_buffer = np.empty((Npackets + skip_packets, len(channels)))
		self.fpga.write_int('pps_start', 1)
		count = 0
		while count < Npackets + skip_packets:
			packet = self.s.recv(8192) # total number of bytes including 42 byte header
			data = np.fromstring(packet,dtype = '<i').astype('float')
			data /= 2.0**17
			data /= (self.accum_len/512.)
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
				#I = np.hstack(zip(I_even[:len(I_odd)], I_odd))
				#Q = np.hstack(zip(Q_even[:len(Q_odd)], Q_odd))
				I = np.dstack((I_even[:len(I_odd)], I_odd)).ravel()
				Q = np.dstack((Q_even[:len(Q_odd)], Q_odd)).ravel()
				I = np.hstack((I, I_even[-1]))	
				Q = np.hstack((Q, Q_even[-1]))	
				I_buffer[count] = I
				Q_buffer[count] = Q
			else:
				#I = np.hstack(zip(I_even, I_odd))
				#Q = np.hstack(zip(Q_even, Q_odd))
				I = np.dstack((I_even, I_odd)).ravel()
				Q = np.dstack((Q_even, Q_odd)).ravel()
				I_buffer[count] = I
				Q_buffer[count] = Q
				
			count += 1
		I_file = 'I' + str(LO_freq)
		Q_file = 'Q' + str(LO_freq)
		np.save(os.path.join(save_path,I_file), I_buffer[skip_packets:]) 
		np.save(os.path.join(save_path,Q_file), Q_buffer[skip_packets:]) 
		return 

	def open_stored(self, save_path = '/mnt/iqstream/lo_sweeps/'):
		files = sorted(os.listdir(save_path))
		sweep_freqs = np.array([np.float(filename[1:-4]) for filename in files if (filename.startswith('I'))])
		I_list = [os.path.join(save_path, filename) for filename in files if filename.startswith('I')]
		Q_list = [os.path.join(save_path, filename) for filename in files if filename.startswith('Q')]
		Is = np.array([np.load(filename) for filename in I_list])
		Qs = np.array([np.load(filename) for filename in Q_list])
		return sweep_freqs, Is, Qs

	def open_stored_dirfile(self, save_path = '/mnt/iqstream/lo_sweeps/'):
		df=gd.dirfile(save_path,gd.RDONLY)
		fields=df.field_list()
		numchannels = int(sorted([f for f in fields if f.startswith('Q')])[-1][1:])+1
		f=[]
		i=[]
		q=[]
		for chan in range(numchannels):
			f.append(df.get_carray('sweep_f_%04d'%chan,gd.FLOAT64))
			i.append(df.get_carray('sweep_i_%04d'%chan,gd.FLOAT64))
			q.append(df.get_carray('sweep_q_%04d'%chan,gd.FLOAT64))
		f=np.array(f)
		i=np.array(i)
		q=np.array(q)
		return f, i, q
	
	def plot_kids(self, save_path = None, bb_freqs = None, channels = None):
		sweep_freqs, Is, Qs = self.open_stored(save_path)
		[ plt.plot((sweep_freqs + bb_freqs[chan])/1.0e9,20*np.log10(np.sqrt(Is[:,chan]**2+Qs[:,chan]**2))) for chan in channels]
		plt.xlabel('Frequency (GHz)')
		plt.ylabel('20log (S21 mag) [dB]')
		plt.title('250 um sweep')
		plt.savefig(os.path.join(save_path,'fig.png'))
		plt.show()
		return

        def lowpass(self,data,f0,order=1):
		size=data.size
		n=size
		#n=np.int(2.**(1.0+np.fix(np.log2(size))))
		df  = np.fft.rfft(data,n=n)
		df /= (1.0+np.power(np.arange(n/2+1)/np.float(n)/f0, 2.0*order))
		data = np.fft.irfft(df)
		return data

	def find_kids_vna(self,save_path=None):
		bb_freqs = np.load(os.path.join(self.save_path,'last_bb_freqs.npy')) 
		if save_path==None:
			save_path = np.load('/mnt/iqstream/last_vna_dir.npy')[0]	
		sweep_freqs, Is, Qs = self.open_stored(save_path = save_path)
		#concatenate and sort sweeps
		channels = np.load('/mnt/iqstream/last_channels.npy')
		Icat = np.concatenate([Is[:,chan] for chan in channels])
		Qcat = np.concatenate([Qs[:,chan] for chan in channels])
		freqs_cat = np.concatenate([sweep_freqs + bb_freqs[chan] for chan in channels])
		Icat = Icat[np.argsort(freqs_cat)]
		Qcat = Qcat[np.argsort(freqs_cat)]
		freqs_cat = freqs_cat[np.argsort(freqs_cat)]
		#phase slope:
		dphi = np.diff(np.unwrap(np.arctan2(Qcat,Icat)))
		#remove step spikes
		dphi[len(sweep_freqs)-1::len(sweep_freqs)]=dphi[len(sweep_freqs)::len(sweep_freqs)]
		plt.figure(figsize = (22,16))
		threshold_pos = 0.1
		threshold_neg = -1.
		plt.subplot(3,1,1)
		plt.plot(freqs_cat[1:],dphi)
		plt.xlim((450.0e6, 1050.0e6))
		plt.ylabel('rad/sample')
		plt.title(r'Raw d$\phi$ (rad)')
		#smooth data
		dphi = signal.convolve(dphi,signal.gaussian(100,3),mode='same')
		#find maxima
		startidx = np.where(np.diff((dphi>=threshold_pos).astype(int)) > 0)[0]
		stopidx  = np.where(np.diff((dphi>=threshold_pos).astype(int)) < 0)[0] + 1
		stopidx = np.append(stopidx,-1)
		kididx_pos  = np.array([i0 + np.argmax(dphi[i0:i1]) for i0,i1 in zip(startidx,stopidx)])

		startidx = np.where(np.diff((dphi<=threshold_neg).astype(int)) > 0)[0]
		stopidx  = np.where(np.diff((dphi<=threshold_neg).astype(int)) < 0)[0] + 1
		stopidx = np.append(stopidx,-1)
		kididx_neg  = np.array([i0 + np.argmin(dphi[i0:i1]) for i0,i1 in zip(startidx,stopidx)])
		print kididx_pos, kididx_neg
		kididx = np.sort(np.append(kididx_pos,kididx_neg))
		print kididx
		kid_freqs = (freqs_cat[1:]-(freqs_cat[1]-freqs_cat[0])/2.)[kididx]
		print 'Resonances at: ', kid_freqs/1.0e9
		print 'Found %d kids'%len(kid_freqs)
		print len(freqs_cat[1:]),len(dphi)
		plt.subplot(3,1,2)
		plt.plot(freqs_cat[1:],dphi)
		plt.plot(freqs_cat[1:][kididx],dphi[kididx],'ro')
		plt.hlines([threshold_pos,threshold_neg],freqs_cat.min(),freqs_cat.max())
		plt.ylabel('rad/sample')
		plt.xlim((450.0e6, 1050.0e6))
		plt.title('Smoothed phase grad')
		#plt.show()
		plt.subplot(3,1,3)
		plt.plot(freqs_cat,10*np.log10(np.sqrt(Icat**2+Qcat**2)))
		plt.plot(kid_freqs,10*np.log10(np.sqrt(Icat**2+Qcat**2))[kididx],'ro')
		plt.xlim((450.0e6, 1050.0e6))
		plt.xlabel('Frequency (GHz)')
		plt.ylabel('10log (S21 mag) [dB]')
		plt.title(r'250 $\mu$$m$ VNA sweep')
		plt.tight_layout()
		#plt.suptitle(r'BLAST-TNG 250$\mu$m array, ROACH2 sweep, # KIDS found = %d'%(len(self.kid_freqs)))
		plt.savefig(os.path.join(save_path,'fig.png'))
		plt.show()
		np.save('/mnt/iqstream/last_kid_freqs.npy',kid_freqs)
		return

	def find_kids_vna_dirfile(self,fiq=None,save_path=None,expected_quality_factors = 10000,thresholds=(20e-9,-np.inf),lowpass_filter=(1,0.05),highpass_filter=(1.,0.01),thresh_didq=1e-9):
		#concatenate tone sweeps
		if fiq==None:
			fiq=np.load('/mnt/iqstream/last_vna_sweep.npy')
		f,i,q = fiq
		Icat = np.ravel(i)
		Qcat = np.ravel(q)
		freqs_cat = np.ravel(f)
		Icat = Icat[np.argsort(freqs_cat)]
		Qcat = Qcat[np.argsort(freqs_cat)]
		freqs_cat = freqs_cat[np.argsort(freqs_cat)]
		
		
		##stitch IQ
		#for step in range(len(f))[1:]:
			#Icat[len(f[0])*step:]-=Icat[len(f[0])*step]-Icat[len(f[0])*step-1]
			#Qcat[len(f[0])*step:]-=Qcat[len(f[0])*step]-Qcat[len(f[0])*step-1]
		
		
		#stitch amplitude
		amp = 10*np.log10(Icat**2+Qcat**2)
		for step in range(len(f))[1:]:
			amp[len(f[0])*step:]-=amp[len(f[0])*step]-amp[len(f[0])*step-1]
		#remove linear trend
		amp_d = signal.detrend(amp)
		#remove baseline
		z=np.polyfit(freqs_cat,amp_d,6)
		p=np.poly1d(z)
		amp_b = amp_d-p(freqs_cat)
		amp_b = amp_d
		
		#plot amplitude
		plt.figure(figsize = (20,10))
		plt.suptitle('Finding KIDs')
		f1=plt.subplot(3,1,1)
		f1.plot(freqs_cat/1e9,amp_b)
		f1.set_ylabel('mag(s21) [dB]')
		f1.set_xlabel('frequency [GHz]')
		
		#find kids from phase differential:
		
		##stitch phase
		phi = np.unwrap(np.arctan2(Qcat,Icat))
		dphi = np.diff(phi)/(f[0,1]-f[0,0])
		#didq = np.sqrt(np.diff(Icat)**2+np.diff(Qcat)**2)
		for step in range(len(f))[1:]:
			phi[len(f[0])*step:]-=phi[len(f[0])*step]-phi[len(f[0])*step-1]
		#dphi = signal.detrend(phi)
			
		dIdf=np.diff(Icat)/np.diff(freqs_cat)
		dQdf=np.diff(Qcat)/np.diff(freqs_cat)
		didq = np.sqrt(dIdf**2+dQdf**2)
		
		#remove step spikes
		#dphi[len(f[0])-1::len(f[0])] = np.nan
		dphi[len(f[0])-1 :: len(f[0])] = np.mean((
			dphi[len(f[0])-3 : len(dphi)-len(f[0]) : len(f[0])],
			dphi[len(f[0])-2 : len(dphi)-len(f[0]) : len(f[0])],
			dphi[len(f[0])   :: len(f[0])],
			dphi[len(f[0])+1 :: len(f[0])]),axis=0)
		didq[len(f[0])-1 :: len(f[0])] = np.mean((
			didq[len(f[0])-3 : len(didq)-len(f[0]) : len(f[0])],
			didq[len(f[0])-2 : len(didq)-len(f[0]) : len(f[0])],
			didq[len(f[0])   :: len(f[0])],
			didq[len(f[0])+1 :: len(f[0])]),axis=0)
		
		##smoothing...
		center_freq = np.mean(freqs_cat)
		fwhm = center_freq/expected_quality_factors		
		#remove mean
		dphi_m = dphi - dphi.mean()
		#didq_m = didq - didq.mean()
		#lowpass_cutoff = xxx/fwhm/xxx
		lowpass_order,lowpass_cutoff_cycles = lowpass_filter
		highpass_order,highpass_cutoff_cycles = highpass_filter
		#filter_a,filter_b = lowpass_filter
		#from lowpass_cosine import lowpass_cosine
		#print len(dphi_m), dphi_m.shape
		#dphi_l = lowpass_cosine(dphi_m, freqs_cat[1]-freqs_cat[0],filter_a*expected_quality_factors/np.mean(freqs_cat), filter_b*expected_quality_factors/np.mean(freqs_cat), padd_data=True)
		#N,wn = signal.buttord(wp=lowpass_cutoff_cycles,
			#ws=lowpass_cutoff_cycles*2, gpass=3, gstop=20.)
		#b, a = signal.butter(N,wn,'lowpass')
		b, a = signal.butter(lowpass_order,lowpass_cutoff_cycles,'lowpass')
		dphi_l = signal.filtfilt(b,a, dphi_m)
		#didq_l = signal.filtfilt(b,a, didq_m)
		##dphi_l = np.diff(dphi_l)/(f[0,1]-f[0,0])
		bh, ah = signal.butter(highpass_order,highpass_cutoff_cycles,'highpass')
		didq_h = signal.filtfilt(bh,ah, didq)
		didq_l = signal.filtfilt(b,a, didq_h)
	

		
		#baseline removal
		dphi_d = signal.detrend(dphi_l)
		z=np.polyfit(freqs_cat[1:],dphi_d,3)
		p=np.poly1d(z)
		dphi_b = dphi_d-p(freqs_cat[1:])
		#dphi_d=dphi_l
		#dphi_b = dphi_d
		
		#didq_d = signal.detrend(didq_l)
		#z=np.polyfit(freqs_cat[1:],didq_d,3)
		#p=np.poly1d(z)
		#didq_b = didq_d-p(freqs_cat[1:])
		##dphi_d=dphi_l
		##dphi_b = dphi_d
		
		##find the peaks
		threshold_pos,threshold_neg = thresholds
		
		#plot phase slope
		f2=plt.subplot(3,1,2,sharex=f1)
		f2.set_ylabel('phase velocity [x10^-9 rad/Hz]')
		#f2.plot(freqs_cat[1:],dphi_b)
		f2.plot(freqs_cat[1:]/1e9,dphi_m*10**9,color='gray')
		f2.plot(freqs_cat[1:]/1e9,dphi_b*10**9,color='blue',lw=2) 
		f2.hlines(threshold_pos*10**9, freqs_cat[0]/1e9,freqs_cat[-1]/1e9, 'r',linestyles='--',lw=3,zorder=3)

		#plot didq 
		f3=plt.subplot(3,1,3,sharex=f1)
		f3.set_ylabel('di/df**2+dq/df**2')
		#f3.plot(freqs_cat[1:],dphi_b)
		f3.plot(freqs_cat[1:]/1e9,didq_h,color='gray')
		f3.plot(freqs_cat[1:]/1e9,didq_l,color='blue',lw=2) 
		f3.hlines(thresh_didq, freqs_cat[0]/1e9,freqs_cat[-1]/1e9, 'r',linestyles='--',lw=3,zorder=3)




		#find maxima
		startidx = np.where(np.diff((dphi_b>=threshold_pos).astype(int)) > 0)[0]
		stopidx  = np.where(np.diff((dphi_b>=threshold_pos).astype(int)) < 0)[0] + 1
		startidx = np.where(np.diff((didq_l>=thresh_didq).astype(int)) > 0)[0]
		stopidx  = np.where(np.diff((didq_l>=thresh_didq).astype(int)) < 0)[0] + 1
		if len(startidx) ==0 or len(stopidx)==0:
			print "none found"
			plt.show()
			return
		if startidx[0]>stopidx[0]:
			stopidx = stopidx[1:]
		while len(startidx)>len(stopidx):
			#stopidx = np.append(stopidx,-1)
			startidx=startidx[:-1]
		#kididx_pos  = np.array([i0 + np.argmax(dphi_b[i0:i1]) for i0,i1 in zip(startidx,stopidx)])
		kididx_pos  = np.array([i0 + np.argmax(didq_l[i0:i1]) for i0,i1 in zip(startidx,stopidx)])
		if len(kididx_pos)==0:
			plt.show()
			return None
		#find minima
		#nstartidx = np.where(np.diff((dphi_b<=threshold_neg).astype(int)) > 0)[0]
		#nstopidx  = np.where(np.diff((dphi_b<=threshold_neg).astype(int)) < 0)[0] + 1
		#if len(nstartidx) ==0 or len(nstopidx==0):
			#pass
		#else:
			#if nstartidx[0]>nstopidx[0]:
				#nstopidx = nstopidx[1:]
			#while len(nstartidx)>len(nstopidx):
				#nstopidx = np.append(nstopidx,-1)
		#kididx_neg  = np.array([i0 + np.argmin(dphi_b[i0:i1]) for i0,i1 in zip(nstartidx,nstopidx)])
		kididx_neg=np.array([])
		
		#combine and find frequencies
		kididx = np.sort(np.append(kididx_pos,kididx_neg)).astype(int)+1
		print kididx
		kid_freqs = (freqs_cat[1:]-(freqs_cat[1]-freqs_cat[0])/2.)[kididx]
		f1.plot(freqs_cat[kididx]/1e9,amp_b[kididx],'ro')
		f2.plot(freqs_cat[kididx]/1e9,dphi_b[kididx]*10**9,'ro')
		f3.plot(freqs_cat[kididx]/1e9,didq_l[kididx],'ro')
		
		plt.xlabel('frequency [GHz]')
		
		print 'Resonances at: ', kid_freqs/1.0e9
		print 'Found %d kids'%len(kid_freqs)
		
		#plt.savefig(os.path.join(save_path,'fig.png'))
		f1.grid()
		f2.grid()
		f3.grid()
		plt.gcf().suptitle('Found %d KIDs'%(len(kid_freqs)))
		plt.show()
		np.save('/mnt/iqstream/last_kid_freqs.npy',kid_freqs)
		return kid_freqs

	def find_kids_target_dirfile(self,fiq=None,save_path=None,lp=(1.0,0.1,0.1)):
		kids = []
		plt.figure()
		for F,I,Q in zip(*fiq):
			didq = np.diff(I)**2+np.diff(Q)**2
			didq_f =lowpass_cosine(didq,lp[0],lp[1],lp[2])
			
			p=plt.plot(F[1:],didq,   alpha=1)
			p=plt.plot(F[1:],didq_f, color=p[0].get_color(),alpha=0.5,lw=3)
			kids.append(F[np.argmax(didq_f)])
		return np.array(kids)

	def get_stream(self, chan, time_interval):
		self.fpga.write_int('pps_start', 1)
		#self.phases = np.empty((len(self.freqs),Npackets))
		Npackets = np.int(time_interval * self.accum_freq)
		Is = np.empty(Npackets)
		Qs = np.empty(Npackets)
		phases = np.empty(Npackets)
		count = 0
		while count < Npackets:
			packet = self.s.recv(8192) # total number of bytes including 42 byte header
			#header = np.fromstring(packet,dtype = '<B')
			#roach_mac = header[6:12]
			#filter_on = np.array([2, 68, 1, 2, 13, 33])
			#if np.array_equal(roach_mac,filter_on):
			data = np.fromstring(packet,dtype = '<i').astype('float')
			data /= 2.0**17
			data /= (self.accum_len/512.)
			ts = (np.fromstring(packet[-4:],dtype = '<i').astype('float')/ self.fpga_samp_freq)*1.0e3 # ts in ms
			# To stream one channel, make chan an argument
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
		return Is, Qs, phases
	
	def plotPSD(self, chan, time_interval):
		Npackets = np.int(time_interval * self.accum_freq)
		plot_range = (Npackets / 2) + 1
		figure = plt.figure(num= None, figsize=(12,12), dpi=80, facecolor='w', edgecolor='w')
		# I 
		plt.suptitle('Channel ' + str(chan) + ' , Freq = ' + str((self.freqs[chan] + self.LO_freq)/1.0e6) + ' MHz') 
		plot1 = figure.add_subplot(311)
		plot1.set_xscale('log')
		#plot1.set_autoscale_on(True)
		plt.ylim((-180,-80))
		plt.xlim((0.001, 2*self.accum_freq/2.))
		plt.title('I')
		line1, = plot1.plot(np.linspace(0, self.accum_freq/2., (Npackets/2) + 1), np.zeros(plot_range), label = 'I', color = 'green', linewidth = 1)
		plt.grid()
		# Q
		plot2 = figure.add_subplot(312)
		plot2.set_xscale('log')
		plt.xlim((0.001, 2*self.accum_freq/2.))
		#plot2.set_autoscale_on(True)
		plt.ylim((-180,-80))
		plt.title('Q')
		line2, = plot2.plot(np.linspace(0, self.accum_freq/2., (Npackets/2) + 1), np.zeros(plot_range), label = 'Q', color = 'red', linewidth = 1)
		plt.grid()
		
		
		# Phase
		plot3 = figure.add_subplot(313)
		plot3.set_xscale('log')
		#plot3.set_autoscale_on(True)
		plt.ylim((-130,-30))
		plt.xlim((0.001, 2*self.accum_freq/2.))
		plt.title('Phase')
		plt.ylabel('dBc rad^2/Hz')
		plt.xlabel('log Hz')
		line3, = plot3.plot(np.linspace(0, self.accum_freq/2., (Npackets/2) + 1), np.zeros(plot_range), label = 'Phase', color = 'black', linewidth = 1)
		plt.grid()
		plt.show(block = False)
		count = 0
		stop = 1.0e10
		while count < stop:
			Is, Qs, phases = self.get_stream(chan, time_interval)
			I_mags = np.fft.rfft(Is, Npackets)
			Q_mags = np.fft.rfft(Is, Npackets)
			phase_mags = np.fft.rfft(phases, Npackets)
			I_vals = (np.abs(I_mags)**2 * ((1./self.accum_freq)**2 / (1.0*time_interval)))
			Q_vals = (np.abs(Q_mags)**2 * ((1./self.accum_freq)**2 / (1.0*time_interval)))
			phase_vals = (np.abs(phase_mags)**2 * ((1./self.accum_freq)**2 / (1.0*time_interval)))
			phase_vals = 10*np.log10(phase_vals)
			phase_vals -= phase_vals[0]
			#line1.set_ydata(Is)
			#line2.set_ydata(Qs)
			#line3.set_ydata(phases)
			line1.set_ydata(10*np.log10(I_vals))
			line2.set_ydata(10*np.log10(Q_vals))
			line3.set_ydata(phase_vals)
			plot1.relim()
			plot1.autoscale_view(True,True,True)
			#plot2.relim()
			#plot2.autoscale_view(True,True,True)
			#plot3.relim()
			#plot3.autoscale_view(True,True,True)
			plt.draw()
			count +=1
		return

	def programLO(self, freq=800.0e6, sweep_freq=0):
		self.vi.simple_set_freq(8,freq)
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
				self.qdrCal()
			if opt == 1:
				self.initialize_GbE()
			if opt == 2:
				print '\nTest tone (MHz) =', self.test_freq/1e6
				self.writeQDR(self.test_freq)
				self.fpga.write_int('sync_accum_reset', 0)
				self.fpga.write_int('sync_accum_reset', 1)
			if opt == 3:
				print '\nDAC freqs (MHz) =', self.freqs/1e6
				print 'Length of Freq Comb =', len(self.freqs)
				self.writeQDR(self.freqs)
				self.fpga.write_int('sync_accum_reset', 0)
				self.fpga.write_int('sync_accum_reset', 1)
			if opt == 4:
				Npackets = input('\nNumber of UDP packets to stream? ' )
				chan = input('chan = ? ')
				self.stream_UDP(chan,Npackets)
			if opt == 5:
				self.vna_sweep_dirfile()
			if opt == 6:
				self.find_kids_vna_dirfile()
			if opt == 7:
				self.target_sweep_dirfile()
			if opt == 8:
				self.stream_KID_response()	
			if opt == 9:
				sys.exit()

		return
	
	def main(self):
		os.system('clear')
		while True: 
			self.main_opt()

class roachRC():
	import beep
	#from socket import *
	
	def __init__(self):
		self.ri 		= None
		self.rootDir		= '/data/roach2remote/'
		self.cwd		= self.rootDir
		self.lastSweepFile      = '/mnt/iqstream/last_target_sweep.npy'
		self.lastStreamFile     = np.zeros((2,1,1024))
		
		self.local_ip           = os.popen('ifconfig eth0 | grep "inet\ addr" | cut -d: -f2 | cut -d" " -f1').read().strip()
		
		self.commandServer 	= socket(AF_INET,SOCK_STREAM)
		self.commandServerAddr  = (self.local_ip, 6666)
		self.commandServer.setsockopt(SOL_SOCKET,SO_REUSEADDR,1)
		self.commandServer.bind(self.commandServerAddr)
		self.commandServer.listen(0)
		
		self.dataServer 	= socket(AF_INET,SOCK_STREAM)
		self.dataServerAddr     = (self.local_ip, 6667)
		self.dataServer.setsockopt(SOL_SOCKET,SO_REUSEADDR,1)
		self.dataServer.bind(self.dataServerAddr)
		self.dataServer.listen(0)
		
		self.startCommandServer()
		
			
	def roachConnect(self,boot=False):
		self.ri = roachInterface(boot=boot,reset_valon=boot)
		
	def serveData(self,data):
		conn,addr = self.dataServer.accept()
		bytes = conn.send(data)
		conn.close()	
		return bytes
	
	
	def startCommandServer(self):
	
		
		
		sprint('Starting Command Server')
		try:
			while True:
				sprint('waiting for connections...')
				conn, addr = self.commandServer.accept()
				#conn.settimeout(0)
				sprint('connected to %s,%s'%addr)
				while True:
					try:
						sprint('waiting for commands...')
						data=''
						while True:
							data += conn.recv(8192)
							if not data:
								break
							if '\n' in data:
								break
							else:
								continue
						data=data.strip()
					except KeyboardInterrupt:
						raise KeyboardInterrupt
					except:
						sprint('exception caught on recv: %s,%s'%(addr,sys.exc_info()[1]))
						break
					if not data:
						break
					try:
						self.handleRequest(conn,data)
					except error:
						sprint('connection closed remotely')
						break
					except:
						sprint('Failed to handle message: %s '%(sys.exc_info()[1]))
							
				sprint('closing connection')
				conn.close()
		except KeyboardInterrupt:
			sprint('Stopping Command Server...')
			#self.commandServer.close()
			self.commandServer.shutdown(SHUT_RDWR)
			#self.dataServer.close()
			self.dataServer.shutdown(SHUT_RDWR)
			
			
				

	def handleRequest(self,conn,command):
		# Changes made by PB on 25/07/2016
		# INFO added to messages that require parsing on client (i.e. synth freq, dirs...etc.
		# Changed delimiter on Averages messages from ... to ,
		
		class FormatError(StandardError):
			pass
		class ConnectError(StandardError):
			pass
		class RangeError(StandardError):
			pass
		
		rcvd = command
		sprint('Command: %s'%rcvd)
		data = rcvd.split(' ')
		try:
			if data[0] == 'BOOT':
				sprint('BOOT')
				conn.send('Booting...\r\n')
				self.roachConnect(boot=True)
			
			elif data[0] == 'CONNECT':
				conn.send('Connecting...\r\n')
				self.roachConnect(boot=False)					
			
			#elif data[0] == 'CLOSE':
				#import thread
				#def kill_server(server):
					#server.shutdown()
				#thread.start_new_thread(kill_server,(self.server,))
			
			elif data[0] == 'MKDIR':
				if len(data)!=2:
					raise FormatError
				try:
					conn.send('Making directory...\r\n')
					
					
					newDir = os.path.join(self.rootDir,data[1])
					os.makedirs(newDir)
				except os.error:
					pass
				self.cwd = data[1]
				conn.send('INFO: CWD = %s\r\n'%self.cwd)
			
			elif data[0] == 'LISTDIRS':
				conn.send('Printing directories...\r\n')
				dirs = sorted([path for path,dirs,files in os.walk(self.rootDir)])
				dirs = ', '.join(dirs) # changed from '\r\n'.join(dirs)
				sprint(dirs)
				conn.send('INFO: %s\r\n'%dirs)
			
			elif data[0] == 'AVG?':
				conn.send('Printing number of FFT averages...\r\n')
				acc = self.ri.accum_len
				sprint('Averages = %s = 2**%s-1... Sample Rate = %s '%(acc, np.log2(acc+1),self.ri.fpga_samp_freq / acc))
				
				conn.send('INFO: Averages = %s = 2**%s-1, Sample Rate = %s\r\n'%(acc, 				np.log2(acc+1),self.ri.fpga_samp_freq / acc))
			
			elif data[0] == 'AVG':
				if len(data)!=2:
					raise FormatError
				try:
					avg=int(data[1])
				except:
					raise FormatError
				if avg not in (2**np.array([15,16,17,18,19,20,21,22,23,24])-1):
					raise RangeError
				if self.ri == None:
					raise ConnectError
				conn.send('Setting number of FFT averages to %s...\r\n'%avg)
				self.ri.set_accum_len(avg)
				acc = self.ri.accum_len
				sprint('New Averages = %s = 2**%s-1... Sample Rate = %s '%(acc, np.log2(acc+1),self.ri.fpga_samp_freq / acc))
				conn.send('INFO: Averages = %s = 2**%s-1... Sample Rate = %s\r\n'%(avg, np.log2(avg+1),self.ri.accum_freq))
			
			elif data[0] == 'LO?':
				if self.ri == None:
					raise ConnectError
				conn.send('Querying LO...\r\n')
				ret = self.ri.vLO.frequency
				sprint(ret)
				conn.send('INFO: %s\r\n'%ret)
			
			elif data[0] == 'LO':
				if len(data)!=2:
					raise FormatError
				try:
					lo=float(data[1])
				except:
					raise FormatError
				if self.ri == None:
					raise ConnectError
				conn.send('Setting LO...\r\n')
				try:
					self.ri.vLO.frequency = lo
				except AssertionError:
					raise RangeError
				ret = self.ri.vLO.frequency
				sprint(ret)
				conn.send('%s\r\n'%ret)
			
			elif data[0] == 'TONES':
				if len(data)<2:
					raise FormatError
				try:
					tones=np.array([np.float(i) for i in data[1:]])
				except:
					raise FormatError
				if self.ri == None:
					raise ConnectError
				if np.ptp(tones)>512e6:
					raise RangeError
				num_tones = len(tones)
				conn.send('Setting %d tones...\r\n'%num_tones)
				
				self.ri.set_freqs(tones)
				sprint('Done')
				conn.send('%s\r\n'%'Done')
			
			elif data[0] == 'TONES?':
				if self.ri == None:
					raise ConnectError
				conn.send('Querying tones...\r\n')
				tones = self.ri.freqs
				tones = ''.join(['%s'%(int(i)) for i in tones])
				sprint(tones)
				conn.send('INFO: %s\r\n'%tones)
			
			elif data[0] == 'SWEEP':
				if len(data)!=6:
					raise FormatError
				center,span,step,avg,filename = data [1:]
				try:
					center = float(center)
					print center
					span= float(span)
					print span
					step=float(step)
					print step
					avg = int(float(avg))
					print avg
					filename = filename
					#filename = filename+'_sweep.npy'
					print filename
				except:
					raise FormatError
				if self.ri == None:
					raise ConnectError
				conn.send('Starting sweep...\r\n')
				f,i,q = self.ri.sweep_lo_dirfile(center_freq = center,
								span = span,
								step = step,
								Npackets_per = avg)
				path = os.path.join(self.cwd,filename)
				conn.send('Saving sweep: %s\r\n'%path)
				self.lastSweepFile = path
				np.save(path,np.array((f,i,q)).astype('float64'))
				print 'Saved sweep: %s\r\n'%path
				conn.send('Saved sweep: %s\r\n'%path)
				
				
			elif data[0] == 'SWEEP?':
				sweep = np.load(self.lastSweepFile)
				data = sweep.tostring()
				print 'Sending: Sweep: %d bytes\r\n'%len(data)
				conn.send('Sending: Sweep: size = %d bytes, shape = (%s)\r\n'%(len(data), sweep.shape))
				
				bytes = self.serveData(data)
				sprint(bytes )
				print 'Sent sweep: %d bytes shape = (%s) \r\n'%(bytes,sweep.shape)
				conn.send('Sent sweep: %d bytes\r\n'%bytes)
			
			elif data[0] == 'STREAM':
				if len(data)!=3:
					raise FormatError
				
				try:
					packets = int(data[1])
					if packets <1:
						raise FormatError
					filename = data[2]
					#filename = data[2]+'_%ssec_timestream.npy'%int(duration)
				except:
					raise FormatError
				if self.ri == None:
					raise ConnectError
				sprint('Streaming data...')
				conn.send('Streaming data...\r\n')
				path = os.path.join(self.cwd,filename)
				stream = self.ri.get_UDP(packets,clearbuf=True,fast_packets=True)
				sprint('Saving stream: %s\r\n'%path)
				conn.send('Saving stream: %s\r\n'%path)
				self.lastStreamFile = path
				np.save(path,stream.astype('float64'))
				
				#stream_string = stream.tostring()
				#conn.send('Sending stream: %d bytes, array shape = (%s)\r\n'%(len(stream_string),stream.shape))
				
				#bytes = self.serveData(stream_string)
				#sprint('stream data sent, %d bytes'%bytes
			
			elif data[0] == 'STREAM?':
				stream = np.load(self.lastStreamFile)
				stream_string = stream.tostring()
				conn.send('Sending: Stream: size = %d bytes, shape = (%s)\r\n'%(len(stream_string),stream.shape))
				bytes = self.serveData(stream_string)
				sprint('stream data sent, %d bytes'%bytes)
			else:
				raise FormatError
			sprint('COMPLETE: \'%s\'\r\n'%rcvd)
			conn.send('COMPLETE: \'%s\'\r\n'%rcvd)
			
		except FormatError:
			sprint('ERROR: Unrecognised command: %s\r\n'%rcvd)
			conn.send('ERROR: Unrecognised command: %s\r\n'%rcvd)
		except ConnectError:
			sprint('ERROR: No roach instance connected..., must send "CONNECT"\r\n')
			conn.send('ERROR: No roach instance connected..., must send "CONNECT"\r\n')
		except RangeError:
			sprint('ERROR: Value not permitted.\r\n')
			conn.send('ERROR: Value not permitted.\r\n')
			
		except:
			sprint('ERROR: Unhandled exception: %s\r\n'%(sys.exc_info()[1]))
			conn.send('ERROR: Unhandled exception: %s\r\n'%(sys.exc_info()[1]))
			


		
	

if __name__=='__main__':
	ri = roachInterface()
	ri.main()
