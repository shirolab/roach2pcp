# functions for control and configuration of the fpga/ppc

import time as _time
import struct as _struct
import socket as _socket # inet_aton as _inet_aton
from ..configuration import firmware_registers as _firmware_registers,\
                            roach_config as _roach_config, \
                            network_config as _network_config

from . import lib_qdr as _lib_qdr


def write_to_fpga_register(fpga, register_dict, sleep_time = 0.1):
    """
    General function to write a set of registers from a dictionary.

    """
    try:
        # check that the register names match the ones defined in the firmware
        if not set( fpga.listdev() ).issubset( register_dict.keys() ):
            print "given register names are not included in the fpga devlist", register_dict.keys()
            return

    except casperfpga.katcp_fpga.KatcpRequestFail:
        print "There doesn't appear to be any firmware running. Check and try again. "
        return

    # write the registers
    for firmware_key, register_value in register_dict.items():
        self.fpga.write_int( _firmware_registers[firmware_key],  int(register_value) )
        _time.sleep(sleep_time)


class roachInterface(object):
    """
    Object to handle all the functions that interact directly with the PPC on a single Roach channel.

    Functionality:
        - hold the current firmware file (which is nominally read from the config file )
        - upload a firmware file
        - store and read QDR LUTs?



    """

    def __init__(self, fpga, roachid):

        # can we run this with no fpga, or casperfpga?
        self.fpga          = fpga
        self.fpg_uploaded  = fpga.is_running()

        # get configuration from file for given roachid

        self.firmware_file = None

        self.network_config = _network_config[roachid]
        self.roach_config   = _roach_config[roachid]

        self.FPGA_SAMP_FREQ = None
        self.FFT_LEN        = None
        self.DAC_SAMP_FREQ  = None
        self.LUTBUFFER_LEN  = None
        self.DAC_FREQ_RES   = 2 * self.DAC_SAMP_FREQ / self.LUTBUFFER_LEN


    def initialise_fpga(self):
        pass


    def upload_firmware_file(self, firmware_file = None, force_reupload=False):
        """

        Upload a firmware file (fpg).


        Optional firmware_file key can be given to upload a different firmware file than given in the config file. If successful,
        the current firmware file is stored in the self.firmware_file variable.

        force_reupload will ignore any checks to see if firmware is currently running and upload the fpg file

        returns True if a new firmware was uploaded, false if not - note that DOES NOT mean that the firmware upload failed. In that
        case, an exception should be raised.

        TODO:
            - write new firmware file entry to configuration dict?

        """
        # allow the user to use a different firmware file if required, else use the file in the config file
        # and perform some checks to see if the firmware file is sensible
        if firmware_file != None and type(firmware_file) is str and os.path.splitext(firmware_file)[-1] == ".fpg":
            pass
        else:
            firmware_file = self.firmware_file

        print 'Connecting...'
        tnow = _time.time()
        while not ( self.fpga.is_connected() and self.fpga.test_connection() ):
            if (_time.time() - tnow) > 1:
                pass
            raise RuntimeError("Connection timeout to roach.")

        _time.sleep(0.1)
        print 'Connected to', self.fpga.host

        # check if firmware is running
        if self.fpga.is_running() and not force_reupload:

            print "An existing firmware is already running. Checking versions..."
            # read info from new firmware file to compare?
            running_devinfo = self.fpga._read_design_info_from_host()["77777"] # <-- dictionary of metadata from fpg
            new_devinfo     = casperfpga.utils.parse_fpg(firmware_file)[0]["77777"] # parse firmware file and return devinfo only

            if running_devinfo['builddate'] == new_devinfo['builddate'] and running_devinfo['system'] == new_devinfo['system']:
                print "It looks like the same version."
            else:
                print "Currently running - " , running_devinfo
                print "New file to upload - ", new_devinfo

                if raw_input("Continue uploading new firmware? (y/n)") =='n':
                    "Operation cancelled. Nothing done. "
                    self.fpg_uploaded = True
                    return False

        success = self.fpga.upload_to_ram_and_program(firmware_file, timeout = 10.)
        _time.sleep(0.5)
        if success == True:
            print 'Successfully uploaded:', firmware_file
            self.firmware_file = firmware_file
            self.fpg_uploaded = True
            return True
        else:
            self.fpg_uploaded = False
            raise RuntimeError("Firmware upload failed.")

    # ---------------------------------------------------------------------------------------------------------
    def calibrate_qdr(self):
    # Calibrates the QDRs. Run after loading firmware
        write_to_fpga_register(self.fpga, { 'dac_reset_reg': 1 } )
        print 'DAC on'

        bFailHard = False
        calVerbosity = 1

        qdrMemName = _firmware_registers['qdr0_reg']
        qdrNames   = [_firmware_registers['qdr0_reg'], _firmware_registers['qdr1_reg']] # <- not used?

        print 'Fpga Clock Rate =', self.fpga.estimate_fpga_clock()
        self.fpga.get_system_information()
        results = {}
        for qdr in self.fpga.qdrs:
            print qdr, qdr.name
            mqdr = _lib_qdr.Qdr.from_qdr(qdr)
            results[qdr.name] = mqdr.qdr_cal2(fail_hard=bFailHard)
        print 'qdr cal results:',results
        for qdr in self.fpga.qdrs:
            if not results[qdr.name]:
                print '\n************ QDR Calibration FAILED ************'
                return -1
        print 'QDR Calibrated'
        return 0

    def configure_downlink_registers(self):

        """Configure GbE registers and parameters"""

        udp_src_mac =  self.network_config['udp_source_mac']
        udp_dest_mac = self.network_config['udp_dest_mac']

        udp_src_ip   = _struct.unpack( '!L', _socket.inet_aton(network_config['udp_source_ip']) )[0]
        udp_src_port = self.network_config['udp_source_port']

        udp_dest_ip   = _struct.unpack( '!L', _socket.inet_aton(network_config['udp_dest_ip']) )[0]
        udp_dest_port = self.network_config['udp_dest_port']

        # Write the mac addresses for the udp source (fpga) and destination (computer)
        write_to_fpga_register(self.fpga, { 'udp_srcmac0_reg' : int(udp_src_mac[4:]  , 16), \
                                            'udp_srcmac1_reg' : int(udp_src_mac[0:4] , 16), \
                                            'udp_destmac0_reg': int(udp_dest_mac[4:] , 16), \
                                            'udp_destmac1_reg': int(udp_dest_mac[0:4], 16)  }, sleep_time = 0.05 )

        write_to_fpga_register(self.fpga, { 'udp_srcip_reg'   : udp_src_ip,   \
                                            'udp_destip_reg'  : udp_dest_ip,  \
                                            'udp_destport_reg': udp_dest_port,\
                                            'udp_srcport_reg' : udp_src_port  }, sleep_time = 0.05 )

        write_to_fpga_register(self.fpga, { 'udp_start_reg': 0, \
                                            'udp_start_reg': 1, \
                                            'udp_start_reg': 0  }, sleep_time = 0.1 )

        return
        # self.fpga.write_int( _firmware_registers['udp_srcmac0_reg'],  int(udp_src_mac[4:], 16)   )
        # _time.sleep(0.05)
        # self.fpga.write_int( _firmware_registers['udp_srcmac1_reg'],  int(udp_src_mac[0:4], 16)  )
        # _time.sleep(0.05)
        # self.fpga.write_int( _firmware_registers['udp_destmac0_reg'], int(udp_dest_mac[4:], 16)  )
        # _time.sleep(0.05)
        # self.fpga.write_int( _firmware_registers['udp_destmac1_reg'], int(udp_dest_mac[0:4], 16) )
        # _time.sleep(0.05)
        #
        # # Write the ip addresses for the udp source (fpga) and destination (computer)
        # print udp_src_ip,type(udp_src_ip)
        # self.fpga.write_int( _firmware_registers['udp_srcip_reg'], udp_src_ip)
        # _time.sleep(0.05)
        # self.fpga.write_int( _firmware_registers['udp_destip_reg'], udp_dest_ip)
        # _time.sleep(0.1)
        # self.fpga.write_int( _firmware_registers['udp_destport_reg'], udp_dest_port)
        # _time.sleep(0.1)
        # self.fpga.write_int( _firmware_registers['udp_srcport_reg'], udp_src_port)
        # _time.sleep(0.1)
        #
        # # Write the mac addresses for the udp source (fpga) and destination (computer)
        # self.fpga.write_int( _firmware_registers['udp_start_reg'], 0)
        # _time.sleep(0.1)
        # self.fpga.write_int( _firmware_registers['udp_start_reg'], 1)
        # _time.sleep(0.1)
        # self.fpga.write_int( _firmware_registers['udp_start_reg'], 0)



    #def gen_dac_freqs(self, freqs, samp_freq, resolution, random_phase = True, DAC_LUT = True, apply_transfunc = False, **kwargs):
    # I, Q = self.freqComb(np.array([freq_residuals[m]]), self.fpga_samp_freq/(self.fft_len/2.), self.dac_freq_res, random_phase = False, DAC_LUT = False)


    def gen_waveform_from_freqs(self, freqs, amps = None, phases = None, which = "dac_lut"):
        """
        Method to generate the I and Q waveforms that will be sent to the DAC and DDS look-up tables.

        Parameters:

            freqs: array_like
                Array of frequencies of the tones to write

            amps: array_like, len(freqs)
                Array of amplitudes, normalised to 1 that is used to set the relative tone powers. If not given, defaults to
                np.ones_like(freqs).

            phases: array_like, len(freqs)
                Array of phases of the tones. If not given, defaults to np.zeros_like(freqs). This is usually set so that
                each tone has a random phase.

            which: str, one of ['dac_lut' or 'dds_lut']
                Switch used to return a waveform for the DAC_LUT or DDS_LUT, respectively.

        Returns
            I, Q:
            Arrays of I and Q waveforms ready to be written to the DAC and DDS.
        """
        # Generates a frequency comb for the DAC or DDS look-up-tables. DAC_LUT = True for the DAC LUT. Returns I and Q
        amps   = np.ones_like(freqs)  if amps   is None else amps
        phases = np.zeros_like(freqs) if phases is None else phases

        freqs = np.round( freqs / self.DAC_FREQ_RES) * self.DAC_FREQ_RES
        amp_full_scale = (2**15 - 1)

        assert which in ['dac_lut', 'dds_lut']

        # For the DDS_LUT, there are two bins returned for every fpga clock, so the bin sample rate is 256 MHz / half the fft length

        fft_len   = self.LUTBUF_LEN    if which == "dac_lut" else self.LUTBUF_LEN/self.FFT_LEN         if which == "dds_lut" else None
        samp_freq = self.DAC_SAMP_FREQ if which == "dac_lut" else self.FPGA_SAMP_FREQ/(self.FFT_LEN/2.) if which == "dds_lut" else None

        phases, amps = ( np.zeros_like(k), np.ones_like(k) ) if which == "dds_lut" else (phases, amps)

        fft_bin_index = np.round((freqs / samp_freq) * fft_len).astype('int')

        spec = np.zeros(fft_len, dtype='complex')
        spec[fft_bin_index] = amps * np.exp( 1j * phases )
        wave = np.fft.ifft(spec)
        waveMax = np.max(np.abs(wave))

    	return (wave.real/waveMax)*(amp_full_scale), (wave.imag/waveMax)*(amp_full_scale)  # <-- I, Q

    def select_bins(self, bb_freqs):
    # Calculates the offset from each bin center, to be used as the DDS LUT frequencies, and writes bin numbers to RAM

        fft_bin_index = np.round( (bb_freqs/2/self.FPGA_SAMP_FREQ) * self.FFT_LEN ).astype('int')
        f_bin = fft_bin_index * self.DAC_SAMP_FREQ/self.FFT_LEN
        fft_bin_index[ fft_bin_index < 0 ] += self.FFT_LEN
        freq_residuals = freqs - f_bin
        bin_freqs = np.unique(f_bin)

        for ch, idx in enumerate(fft_bin_index):
            write_to_fpga_register(self.fpga, { 'bins_reg': idx, \
                                                'load_bins_reg': 2*ch + 1, \
                                                'load_bins_reg': 0 }, sleep_time = 0. )

                                                #enable write ram at address i

        # --- From Sam R's Blastfirmware code, but doesn't appear to included in kidPy ---
		# # This is done to clear any unused channelizer RAM addresses
		# for n in range(1024 - len(bins)):
		# 	self.fpga.write_int('bins', 0)#have fft_bin waiting at ram gate
		#   self.fpga.write_int('load_bins', 2*ch + 1)#enable write ram at address i
		#   self.fpga.write_int('load_bins', 0)#disable write
		# 	ch += 1
		# 	n += 1

        return freq_residuals

    def define_DDS_LUT(self, freqs):
        # Builds the DDS look-up-table from I and Q given by freq_comb. freq_comb is called with the sample rate equal to the
        # sample rate for a single FFT bin.
        # There are two bins returned for every fpga clock, so the bin sample rate is 256 MHz / half the fft length
        freq_residuals = self.select_bins(freqs)
        I_dds, Q_dds = np.array([0.]*(self.LUTBUFFER_LEN)), np.array([0.]*(self.LUTBUFFER_LEN))
        for idx, freq in enumerate(freq_residuals):
            I, Q = self.gen_waveform_from_freqs(np.array(freq), amps, phases, self.DAC_FREQ_RES)
            I_dds[idx::self.FFT_LEN] = I
            Q_dds[idx::self.FFT_LEN] = Q
        # store this somewhere useful?

        return I_dds, Q_dds

    def pack_luts(self, freqs, amps, phases):
        # packs the I and Q look-up-tables into strings of 16-b integers, in preparation to write to the QDR.
        # Returns the string-packed look-up-tables

        I_dac, Q_dac = self.gen_waveform_from_freqs(freqs, amps, phases, which = "dac_lut")
        I_dds, Q_dds = self.define_DDS_LUT(freqs)

        self._I_dds = I_dds
        self._Q_dds = Q_dds

        I_lut, Q_lut = np.zeros(2 * self.LUTBUF_LEN), np.zeros(2 * self.LUTBUF_LEN)
        I_lut[0::4] = I_dac[1::2]
        I_lut[1::4] = I_dac[0::2]
        I_lut[2::4] = I_dds[1::2]
        I_lut[3::4] = I_dds[0::2]
        Q_lut[0::4] = Q_dac[1::2]
        Q_lut[1::4] = Q_dac[0::2]
        Q_lut[2::4] = Q_dds[1::2]
        Q_lut[3::4] = Q_dds[0::2]

        return I_lut.astype('>i2').tostring(), Q_lut.astype('>i2').tostring() # I_lut_packed, Q_lut_packed

    def write_freqs_to_qdr(self, freqs):
        # Writes packed LUTs to QDR
        I_lut_packed, Q_lut_packed = self.pack_luts(freqs, amp, phases)

        write_to_fpga_register(self.fpga, { "dac_reset_reg": 1, \
                                            "dac_reset_reg": 0, \
                                            "start_dac_reg": 0 }, sleep_time = 0. )

        self.fpga.blindwrite(_firmware_registers['qdr0_reg'], I_lut_packed, 0)
        self.fpga.blindwrite(_firmware_registers['qdr1_reg'], Q_lut_packed, 0)

        write_to_fpga_register(self.fpga, { "start_dac_reg"  : 1, \
                                            "accum_reset_reg": 0, \
                                            "accum_reset_reg": 1}, sleep_time = 0. )

        write_to_fpga_register(self.fpga, { "write_comb_len_reg": len(freqs) },  sleep_time = 0. )

        print 'Done.'
