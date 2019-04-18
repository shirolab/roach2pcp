# functions for control and configuration of the fpga/ppc

import time as _time, os as _os, logging as _logging, struct as _struct, socket as _socket # inet_aton as _inet_aton
import threading as _threading, tqdm as _tqdm, functools as _functools, time as _time
from ..configuration import color_msg as cm

import numpy as _np

from ..configuration import firmware_registers as _firmware_registers,\
                            roach_config as _roach_config, \
                            network_config as _network_config,\
                            filesys_config as _filesys_config,\
                            FIRMWARE_REG_DICT

from . import lib_qdr as _lib_qdr

_logger = _logging.getLogger(__name__)

try:
    import casperfpga as _casperfpga

except ImportError:
    _logger.warning( "can't find casperfpga module - limited functionality available" )
    _casperfpga = None
    pass

def check_registers_are_valid(registers, firmware_reg_list):

    assert type(registers) in [str, list], "enter either a single string, or a list of strings to check. Given type = {0}".format(type(registers))
    registers = _np.atleast_1d(registers).astype(str)

    # check that the register names match the ones defined in the firmware

    # TODO check with fpga.listdev too

    if not set( firmware_reg_list ).issuperset( registers ):
        print "given register names are not included in the fpga devlist", registers.keys()
        return False

    else:
        return True

def write_to_fpga_register(fpga, regs_to_write, firmware_reg_list, sleep_time = 0.1):
    """
    General function to write a set of registers from a dictionary.

    """
    if check_registers_are_valid( regs_to_write.keys(), firmware_reg_list.keys() ):
        # write the registers
        for firmware_key, register_value in regs_to_write.iteritems():
            fpga.write_int( firmware_reg_list[firmware_key],  int(register_value) )
            _time.sleep(sleep_time)

def read_from_fpga_register(fpga, regs_to_read, firmware_reg_list):
    """
    Function to read a dictionary of reg_name: size_to_read from the current fpga firmware. Function returns a dictionary with
    register names as keys, and returned values as dictionary values.

    NOT TESTED YET - 20190119
    FIXED AND TESTED - 20190226
    """
    data_dict = dict.fromkeys(regs_to_read.keys())

    if check_registers_are_valid( regs_to_read.keys(), firmware_reg_list.keys() ):
        # read data from the fpga
        for regname, sizetoread in regs_to_read.iteritems():
            data_dict[regname] = fpga.read(firmware_reg_list[regname], sizetoread )

    return data_dict

def get_fpga_instance(ipaddress):
    """

    Function to return an fpga instance for a given roachid. Parameters are read from the configuration
    file.

    Returns _casperfpga.katcp_fpga.KatcpFpga instance if successful, None otherwise.

    """
    if _casperfpga is None:
        print "casperfpga module not loaded. No active FPGA instance"
        return

    try:
        return _casperfpga.katcp_fpga.KatcpFpga( ipaddress, timeout = 10. )
    except RuntimeError:
        # bad things have happened, and nothing else should proceed
        _logger.exception( "Error, fpga not connected." )
        return None
    except:
        _logger.exception( 'Error connecting to \'{0}\'. Is it switched on? Check network settings!'.format(ipaddress) )
        return None


# ---------------------------Progress bar-----------------------------------
# This should be in another place

# Based in the code of duckythescientist: 
# https://gist.github.com/duckythescientist/c06d87617b5d6ac1e00a622df760709d

def progress_bar(function, estimated_time, description, tstep=0.2, tqdm_kwargs={}, args=[], kwargs={}):
    """Tqdm wrapper for a function
    args:
        function - function to run
        estimated_time - how long you expect the function to take
        tstep - time delta (seconds) for progress bar updates
        tqdm_kwargs - kwargs to construct the progress bar
        args - args to pass to the function
        kwargs - keyword args to pass to the function
    ret:
        function(*args, **kwargs)
    """
    ret = [None]  # Mutable var so the function can store its return value
    def myrunner(function, ret, *args, **kwargs):
        ret[0] = function(*args, **kwargs)

    thread = _threading.Thread(target=myrunner, args=(function, ret) + tuple(args), kwargs=kwargs)
    pbar = _tqdm.tqdm(total=estimated_time, ncols=75, desc=description ,**tqdm_kwargs)

    thread.start()
    while thread.is_alive():
        thread.join(timeout=tstep)
        pbar.update(tstep)

    pbar.close()
    return ret[0]

def progress_wrapped(estimated_time, description, tstep=0.25, tqdm_kwargs={}):
    """Decorate a function to add a progress bar"""
    def decorator(function):
        @_functools.wraps(function)
        def wrapper(*args, **kwargs):
            #estimated_time = kwargs["estimated_time"]
            return progress_bar(function, estimated_time=estimated_time, description=description, tstep=tstep, tqdm_kwargs=tqdm_kwargs, args=args, kwargs=kwargs)
        return wrapper
    return decorator
# ----------------------------------------------------------------------------

class roachInterface(object):
    """
    Object to handle all the functions that interact directly with the PPC on a single Roach channel.

    Functionality:
        - hold the current firmware file (which is nominally read from the config file )
        - upload a firmware file
        - store and read QDR LUTs?

    """

    def __init__(self, roachid):

        # get configuration from file for given roachid
        self.network_config     = _network_config[roachid]
        self.roach_config       = _roach_config[roachid]
        self.firmware_reg_list  = FIRMWARE_REG_DICT[roachid]

        # try to get an fpga instance for the given roachid
        self.fpga = get_fpga_instance( self.network_config["roach_ppc_ip"] )

        if self.fpga == None:
            _logger.warning( " No fpga instance present. If running a dummy, this is expected. Otherwise, something has gone wrong. " )
            return

        self.fpg_uploaded  = self.fpga.is_running()

        self.firmware_file = _os.path.join(_filesys_config["firmwaredir"] , self.roach_config["firmware_file"])
        assert _os.path.exists(self.firmware_file)

        # these should be read from the config file
        self.FPGA_SAMP_FREQ = 256.e6
        self.FFT_LEN        = 1024
        self.DAC_SAMP_FREQ  = 512.e6
        self.LUTBUF_LEN     = 2097152 # 2**21
        self.DAC_FREQ_RES   = 2 * self.DAC_SAMP_FREQ / self.LUTBUF_LEN


    #@progress_wrapped(estimated_time=5)
    def initialise_fpga(self, force_reupload = False):

        """
        High level function to run all of the functions to intialise the roach
        """

        if not self.fpga.is_connected():
            print "it looks like the fpga is not connected"
            return

        # try to upload self.firmware_file. This function checks to see if a firmware is already running,
        # and if the versions match.
        we_uploaded_a_firmware = self.upload_firmware_file( force_reupload = force_reupload )

        # calibrate qdr if uploading formware
        if we_uploaded_a_firmware:
            if self.calibrate_qdr() < 0:
                print "qdr calibration failed."
            else:
                write_to_fpga_register(self.fpga, { 'write_qdr_status_reg': 1 }, self.firmware_reg_list )

        # write registers (dds_shift + accum_len)

        write_to_fpga_register(self.fpga, { 'accum_len_reg': 2**(self.roach_config['roach_accum_len'])-1, \
                                            'dds_shift_reg': self.roach_config['dds_shift']  }, self.firmware_reg_list)

        # configure downlink
        self.configure_downlink_registers()

        # activate PPS
        self.active_pps()

    @progress_wrapped(description=cm.BOLD+"Firmware"+cm.ENDC, estimated_time=2.83)
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
        if firmware_file != None and type(firmware_file) is str and _os.path.splitext(firmware_file)[-1] == ".fpg":
            pass
        else:
            firmware_file = self.firmware_file

        tnow = _time.time()
        #while not ( self.fpga.is_connected() and self.fpga.test_connection() ):
        while not ( self.fpga.is_connected() ):
            if (_time.time() - tnow) > 1:
                pass
            raise RuntimeError(cm.ERROR + "Connection timeout to roach." + cm.ENDC)

        _time.sleep(0.1)
        print cm.OKGREEN + 'Connected to ' + cm.BOLD, self.fpga.host, cm.ENDC

        # check if a firmware is running, and if so, check if it is the same version as we're trying to upload
        if self.fpga.is_running() and not force_reupload:

            print "An existing firmware is already running. Checking versions..."
            # read info from new firmware file to compare?
            running_devinfo = self.fpga._read_design_info_from_host()["77777"] # <-- dictionary of metadata from fpg
            new_devinfo     = _casperfpga.utils.parse_fpg(firmware_file)[0]["77777"] # parse firmware file and return devinfo only

            if running_devinfo['builddate'] == new_devinfo['builddate'] and running_devinfo['system'] == new_devinfo['system']:
                print "It looks like the same version. Use 'force_reupload = True' to re-upload the same firmware. Returning. "
                return False
            else:
                print "Currently running - " , running_devinfo
                print "New file to upload - ", new_devinfo

                if raw_input("Continue uploading new firmware? (y/n)") =='n':
                    "Operation cancelled. Nothing done. "
                    self.fpg_uploaded = True
                    return False

        print cm.OKBLUE + "uploading firmware file \'{0}\' to roach".format(firmware_file) + cm.ENDC
        success = self.fpga.upload_to_ram_and_program(firmware_file, timeout = 10.)
        _time.sleep(0.5)
        if success == None:
            print cm.OKGREEN + 'Successfully uploaded:', firmware_file, cm.ENDC
            self.firmware_file = firmware_file
            self.fpg_uploaded = True
            return True
        else:
            print success
            self.fpg_uploaded = False
            raise RuntimeError("Firmware upload failed.")

    # ---------------------------------------------------------------------------------------------------------
    @progress_wrapped(description=cm.BOLD+"QDR Calibration"+cm.ENDC, estimated_time=5.7)
    def calibrate_qdr(self):
    # Calibrates the QDRs. Run after loading firmware
        write_to_fpga_register(self.fpga, { 'dac_reset_reg': 1 }, self.firmware_reg_list )
        print cm.OKGREEN + 'DAC on' + cm.ENDC

        bFailHard = False
        calVerbosity = 1

        qdrMemName = self.firmware_reg_list['qdr0_reg']
        qdrNames   = [self.firmware_reg_list['qdr0_reg'], self.firmware_reg_list['qdr1_reg']] # <- not used?

        print cm.OKBLUE + 'Fpga Clock Rate =' + cm.BOLD, self.fpga.estimate_fpga_clock(), cm.ENDC
        self.fpga.get_system_information()
        results = {}
        for qdr in self.fpga.qdrs:
            print qdr, qdr.name
            mqdr = _lib_qdr.Qdr.from_qdr(qdr)
            results[qdr.name] = mqdr.qdr_cal2(fail_hard=bFailHard)
        print 'qdr cal results:',results
        for qdr in self.fpga.qdrs:
            if not results[qdr.name]:
                print cm.ERROR + '\n************ QDR Calibration FAILED ************' + cm.ENDC
                return -1
        print cm.OKGREEN + 'QDR Calibrated' + cm.ENDC
        return 0

    def configure_downlink_registers(self):

        """Configure GbE registers and parameters"""

        udp_src_mac =  self.network_config['udp_source_mac']
        udp_dest_mac = self.network_config['udp_dest_mac']

        udp_src_ip   = _struct.unpack( '!L', _socket.inet_aton(self.network_config['udp_source_ip']) )[0]
        udp_src_port = self.network_config['udp_source_port']

        udp_dest_ip   = _struct.unpack( '!L', _socket.inet_aton(self.network_config['udp_dest_ip']) )[0]
        udp_dest_port = self.network_config['udp_dest_port']

        # Write the mac addresses for the udp source (fpga) and destination (computer)
        write_to_fpga_register(self.fpga, { 'udp_srcmac0_reg' : int(udp_src_mac[4:]  , 16), \
                                            'udp_srcmac1_reg' : int(udp_src_mac[0:4] , 16), \
                                            'udp_destmac0_reg': int(udp_dest_mac[4:] , 16), \
                                            'udp_destmac1_reg': int(udp_dest_mac[0:4], 16)  }, self.firmware_reg_list, sleep_time = 0.05 )

        write_to_fpga_register(self.fpga, { 'udp_srcip_reg'   : udp_src_ip,   \
                                            'udp_destip_reg'  : udp_dest_ip,  \
                                            'udp_destport_reg': udp_dest_port,\
                                            'udp_srcport_reg' : udp_src_port  }, self.firmware_reg_list, sleep_time = 0.05 )

        write_to_fpga_register(self.fpga, { 'udp_start_reg': 0 }, self.firmware_reg_list, sleep_time = 0.1 ) # require separate calls for the same register
        write_to_fpga_register(self.fpga, { 'udp_start_reg': 1 }, self.firmware_reg_list, sleep_time = 0.1 )
        write_to_fpga_register(self.fpga, { 'udp_start_reg': 0 }, self.firmware_reg_list, sleep_time = 0.1 )

        print cm.OKGREEN + "Downlink registers configured" + cm.ENDC

        return

    def gen_waveform_from_freqs(self, freqs, amps = None, phases = None, which = "dac_lut",iq_correction=None,phase_error_radians=None):
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
        _logger.debug("frequencies being generated: {0}".format(freqs) )

        freqs = _np.round( freqs / self.DAC_FREQ_RES) * self.DAC_FREQ_RES
        amp_full_scale = (2**15 - 1)

        assert which in ['dac_lut', 'dds_lut']

        # For the DDS_LUT, there are two bins returned for every fpga clock, so the bin sample rate is 256 MHz / half the fft length
        fft_len   = self.LUTBUF_LEN    if which == "dac_lut" else self.LUTBUF_LEN/self.FFT_LEN          if which == "dds_lut" else None
        samp_freq = self.DAC_SAMP_FREQ if which == "dac_lut" else self.FPGA_SAMP_FREQ/(self.FFT_LEN/2.) if which == "dds_lut" else None

        fft_bin_index = _np.round((freqs / samp_freq) * fft_len).astype('int')
        fft_neg_bin_index = _np.round((-1*freqs / samp_freq) *fft_len).astype('int')

        if which == "dds_lut":
            phases, amps = ( _np.zeros_like(fft_bin_index), _np.ones_like(fft_bin_index) )
            if iq_correction is None:
                iq_correction = _np.ones_like(fft_bin_index) + 1j*_np.ones_like(fft_bin_index)
            if phase_error_radians is None:
                phase_error_radians = _np.zeros_like(fft_bin_index)
        else:
            amps, phases = ( _np.ones_like(freqs) if amps is None else amps,\
                            _np.random.uniform(0., 2.*_np.pi, len(freqs)) if phases is None else phases )
            if iq_correction is None:
                iq_correction = _np.ones_like(freqs) + 1j*_np.ones_like(freqs)
            if phase_error_radians is None:
                phase_error_radians = _np.zeros_like(freqs)

        _logger.debug( "amps and phases to write: {0}, {1}".format(amps, phases) )

        spec = _np.zeros(fft_len, dtype='complex')
        spec[fft_bin_index] = amps * _np.exp( 1j * phases )
        wave = _np.fft.ifft(spec)
        
        #iq amplitude correction
        ispec = _np.fft.fft(wave.real)
        ispec[fft_bin_index] /= iq_correction.real
        ispec[fft_neg_bin_index] /= iq_correction.real
        iwave = _np.fft.ifft(ispec)

        qspec = _np.fft.fft(wave.imag)
        qspec[fft_bin_index] /= iq_correction.imag
        qspec[fft_neg_bin_index] /= iq_correction.imag
        qwave = _np.fft.ifft(qspec)

        #phase error correction
        qspec = _np.fft.fft(qwave)
        phase = _np.exp(-1j*phase_error_radians)
        qspec[fft_bin_index] *= phase
        qspec[fft_neg_bin_index] *= phase
        qwave = _np.fft.ifft(qspec)

        wave    = iwave + 1j*qwave
        waveMax = _np.max(_np.abs(wave))
        
        if which=='dac_lut':
            print 'waveMax:',waveMax
        
        waveMax = 6e-5
        return (wave.real/waveMax)*(amp_full_scale), (wave.imag/waveMax)*(amp_full_scale)  # <-- I, Q

    def select_bins(self, freqs):
        # Calculates the offset from each bin center, to be used as the DDS LUT frequencies, and writes bin numbers to RAM
        fft_bin_index = _np.round( (freqs/2/self.FPGA_SAMP_FREQ) * self.FFT_LEN ).astype('int')
        f_bin = fft_bin_index * self.DAC_SAMP_FREQ/self.FFT_LEN
        fft_bin_index[ fft_bin_index < 0 ] += self.FFT_LEN
        freq_residuals = freqs - f_bin
        bin_freqs = _np.unique(f_bin)

        # this is a bit slow...
        for ch, idx in enumerate(fft_bin_index):
            write_to_fpga_register(self.fpga, { 'bins_reg': idx, \
                                                'load_bins_reg': 2*ch + 1}, self.firmware_reg_list, sleep_time = 0. )
            write_to_fpga_register(self.fpga, {'load_bins_reg': 0 }, self.firmware_reg_list, sleep_time = 0. )

                                                #enable write ram at address i

        # --- From Sam R's Blastfirmware code, but doesn't appear to included in kidPy ---
        # # This is done to clear any unused channelizer RAM addresses
        # for n in range(1024 - len(bins)):
        #   self.fpga.write_int('bins', 0)#have fft_bin waiting at ram gate
        #   self.fpga.write_int('load_bins', 2*ch + 1)#enable write ram at address i
        #   self.fpga.write_int('load_bins', 0)#disable write
        #   ch += 1
        #   n += 1

        return freq_residuals

    def define_dds_lut(self, freqs): # SLOW - takes ~1 s to run with 101 tones
        # Builds the DDS look-up-table from I and Q given by freq_comb. freq_comb is called with the sample rate equal to the
        # sample rate for a single FFT bin.
        # There are two bins returned for every fpga clock, so the bin sample rate is 256 MHz / half the fft length
        freq_residuals = self.select_bins(freqs)
        I_dds, Q_dds = _np.zeros( (2, self.LUTBUF_LEN) )

        for idx, freq in enumerate(freq_residuals):
            I, Q = self.gen_waveform_from_freqs(freq, amps=None, phases=None, which='dds_lut')
            I_dds[idx::self.FFT_LEN] = I
            Q_dds[idx::self.FFT_LEN] = Q
        # store this somewhere useful?

        return I_dds, Q_dds

    def pack_luts(self, freqs, amps, phases,iq_correction=None,phase_error_radians=None):
        # packs the I and Q look-up-tables into strings of 16-b integers, in preparation to write to the QDR.
        # Returns the string-packed look-up-tables

        I_dac, Q_dac = self.gen_waveform_from_freqs(freqs, amps, phases, which = "dac_lut",iq_correction=iq_correction,phase_error_radians=phase_error_radians)
        I_dds, Q_dds = self.define_dds_lut(freqs)

        self._I_dds = I_dds
        self._Q_dds = Q_dds

        I_lut, Q_lut = _np.zeros( (2, 2 * self.LUTBUF_LEN) )
        I_lut[0::4] = I_dac[1::2]
        I_lut[1::4] = I_dac[0::2]
        I_lut[2::4] = I_dds[1::2]
        I_lut[3::4] = I_dds[0::2]
        Q_lut[0::4] = Q_dac[1::2]
        Q_lut[1::4] = Q_dac[0::2]
        Q_lut[2::4] = Q_dds[1::2]
        Q_lut[3::4] = Q_dds[0::2]

        return I_lut.astype('>i2').tostring(), Q_lut.astype('>i2').tostring() # I_lut_packed, Q_lut_packed

    
  #   def gen_waveform_from_freqs(self, freqs, amps = None, phases = None, which = "dac_lut"):
  #       """
  #       Method to generate the I and Q waveforms that will be sent to the DAC and DDS look-up tables.

  #       Parameters:

  #           freqs: array_like
  #               Array of frequencies of the tones to write

  #           amps: array_like, len(freqs)
  #               Array of amplitudes, normalised to 1 that is used to set the relative tone powers. If not given, defaults to
  #               np.ones_like(freqs).

  #           phases: array_like, len(freqs)
  #               Array of phases of the tones. If not given, defaults to np.zeros_like(freqs). This is usually set so that
  #               each tone has a random phase.

  #           which: str, one of ['dac_lut' or 'dds_lut']
  #               Switch used to return a waveform for the DAC_LUT or DDS_LUT, respectively.

  #       Returns
  #           I, Q:
  #           Arrays of I and Q waveforms ready to be written to the DAC and DDS.
  #       """
  #       # Generates a frequency comb for the DAC or DDS look-up-tables. DAC_LUT = True for the DAC LUT. Returns I and Q
  #       _logger.debug("frequencies being generated: {0}".format(freqs) )

  #       freqs = _np.round( freqs / self.DAC_FREQ_RES) * self.DAC_FREQ_RES
  #       amp_full_scale = (2**15 - 1)

  #       assert which in ['dac_lut', 'dds_lut']

  #       # For the DDS_LUT, there are two bins returned for every fpga clock, so the bin sample rate is 256 MHz / half the fft length
  #       fft_len   = self.LUTBUF_LEN    if which == "dac_lut" else self.LUTBUF_LEN/self.FFT_LEN          if which == "dds_lut" else None
  #       samp_freq = self.DAC_SAMP_FREQ if which == "dac_lut" else self.FPGA_SAMP_FREQ/(self.FFT_LEN/2.) if which == "dds_lut" else None

  #       fft_bin_index = _np.round((freqs / samp_freq) * fft_len).astype('int')

  #       if which == "dds_lut":
  #           phases, amps = ( _np.zeros_like(fft_bin_index), _np.ones_like(fft_bin_index) )
  #       else:
  #           phases, amps = (_np.random.uniform(0., 2.*_np.pi, len(freqs)) if phases is None else phases,\
  #                           _np.ones_like(freqs) if amps is None else amps)

  #       _logger.debug( "amps and phases to write: {0}, {1}".format(amps, phases) )

  #       spec = _np.zeros(fft_len, dtype='complex')
  #       spec[fft_bin_index] = amps * _np.exp( 1j * phases )
  #       wave = _np.fft.ifft(spec)
  #       waveMax = _np.max(_np.abs(wave))

  #   	return (wave.real/waveMax)*(amp_full_scale), (wave.imag/waveMax)*(amp_full_scale)  # <-- I, Q

  #   def select_bins(self, freqs):
  #       # Calculates the offset from each bin center, to be used as the DDS LUT frequencies, and writes bin numbers to RAM
  #       fft_bin_index = _np.round( (freqs/2/self.FPGA_SAMP_FREQ) * self.FFT_LEN ).astype('int')
  #       f_bin = fft_bin_index * self.DAC_SAMP_FREQ/self.FFT_LEN
  #       fft_bin_index[ fft_bin_index < 0 ] += self.FFT_LEN
  #       freq_residuals = freqs - f_bin
  #       bin_freqs = _np.unique(f_bin)

  #       # this is a bit slow...
  #       for ch, idx in enumerate(fft_bin_index):
  #           write_to_fpga_register(self.fpga, { 'bins_reg': idx, \
  #                                               'load_bins_reg': 2*ch + 1}, self.firmware_reg_list, sleep_time = 0. )
  #           write_to_fpga_register(self.fpga, {'load_bins_reg': 0 }, self.firmware_reg_list, sleep_time = 0. )

  #                                               #enable write ram at address i

  #       # --- From Sam R's Blastfirmware code, but doesn't appear to included in kidPy ---
		# # # This is done to clear any unused channelizer RAM addresses
		# # for n in range(1024 - len(bins)):
		# # 	self.fpga.write_int('bins', 0)#have fft_bin waiting at ram gate
		# #   self.fpga.write_int('load_bins', 2*ch + 1)#enable write ram at address i
		# #   self.fpga.write_int('load_bins', 0)#disable write
		# # 	ch += 1
		# # 	n += 1

  #       return freq_residuals

  #   def define_dds_lut(self, freqs): # SLOW - takes ~1 s to run with 101 tones
  #       # Builds the DDS look-up-table from I and Q given by freq_comb. freq_comb is called with the sample rate equal to the
  #       # sample rate for a single FFT bin.
  #       # There are two bins returned for every fpga clock, so the bin sample rate is 256 MHz / half the fft length
  #       freq_residuals = self.select_bins(freqs)
  #       I_dds, Q_dds = _np.zeros( (2, self.LUTBUF_LEN) )

  #       for idx, freq in enumerate(freq_residuals):
  #           I, Q = self.gen_waveform_from_freqs(freq, amps=None, phases=None, which='dds_lut')
  #           I_dds[idx::self.FFT_LEN] = I
  #           Q_dds[idx::self.FFT_LEN] = Q
  #       # store this somewhere useful?

  #       return I_dds, Q_dds

  #   def pack_luts(self, freqs, amps, phases):
  #       # packs the I and Q look-up-tables into strings of 16-b integers, in preparation to write to the QDR.
  #       # Returns the string-packed look-up-tables

  #       I_dac, Q_dac = self.gen_waveform_from_freqs(freqs, amps, phases, which = "dac_lut")
  #       I_dds, Q_dds = self.define_dds_lut(freqs)

  #       self._I_dds = I_dds
  #       self._Q_dds = Q_dds

  #       I_lut, Q_lut = _np.zeros( (2, 2 * self.LUTBUF_LEN) )
  #       I_lut[0::4] = I_dac[1::2]
  #       I_lut[1::4] = I_dac[0::2]
  #       I_lut[2::4] = I_dds[1::2]
  #       I_lut[3::4] = I_dds[0::2]
  #       Q_lut[0::4] = Q_dac[1::2]
  #       Q_lut[1::4] = Q_dac[0::2]
  #       Q_lut[2::4] = Q_dds[1::2]
  #       Q_lut[3::4] = Q_dds[0::2]

  #       return I_lut.astype('>i2').tostring(), Q_lut.astype('>i2').tostring() # I_lut_packed, Q_lut_packed

    @progress_wrapped(description=cm.BOLD+"Writting tones"+cm.ENDC, estimated_time=15.75)
    def write_freqs_to_qdr(self, freqs, amps, phases, iq_correction=None,phase_error_radians=None, **kwargs):
        # Writes packed LUTs to QDR

        #write fft_shift ?
        fft_shift = 2**5 if len(freqs) >= 400 else 2**9
        write_to_fpga_register(self.fpga, { "fft_shift_reg": fft_shift - 1} , self.firmware_reg_list, sleep_time = 0. )

        I_lut_packed, Q_lut_packed = self.pack_luts(freqs, amps, phases, iq_correction=iq_correction, phase_error_radians=phase_error_radians)
        write_to_fpga_register(self.fpga, { "dac_reset_reg": 1} , self.firmware_reg_list, sleep_time = 0. )
        write_to_fpga_register(self.fpga, { "dac_reset_reg": 0, \
                                            "start_dac_reg": 0 }, self.firmware_reg_list, sleep_time = 0. )
        # blindwrites takes around 8-9 seconds each
        self.fpga.blindwrite(self.firmware_reg_list['qdr0_reg'], I_lut_packed, offset = 0)
        self.fpga.blindwrite(self.firmware_reg_list['qdr1_reg'], Q_lut_packed, offset = 0)

        write_to_fpga_register(self.fpga, { "start_dac_reg"  : 1, \
                                            "accum_reset_reg": 0 }, self.firmware_reg_list, sleep_time = 0. )

        write_to_fpga_register(self.fpga, { "accum_reset_reg": 1, \
                                            "write_comb_len_reg": len(freqs) }, self.firmware_reg_list, sleep_time = 0. )
        print cm.OKGREEN + 'Tones written.' + cm.ENDC

    def make_freq_comb(self, nfreq = 101):

        # Number of frequencies in test comb
        #Nfreq = 101
        # Maximum positive frequency, Hz
        max_pos_freq = 246.001234e6
        # Minimum positive frequency, Hz
        min_pos_freq = 1.02342e6
        # Maximum negative frequency, Hz
        max_neg_freq = -1.02342e6
        # Minimum negative frequency, Hz
        min_neg_freq = -246.001234e6
        # Offset between positive and negative combs, Hz
        symm_offset = 250.0e3

        neg_freqs, neg_delta = _np.linspace(min_neg_freq + symm_offset, max_neg_freq + symm_offset, nfreq/2, retstep = True)
        pos_freqs, pos_delta = _np.linspace(min_pos_freq, max_pos_freq, nfreq/2, retstep = True)
        freq_comb = _np.concatenate((neg_freqs, pos_freqs))
        freq_comb = freq_comb[freq_comb != 0]
        freq_comb = _np.roll(freq_comb, - _np.argmin(_np.abs(freq_comb)) - 1)
        #if len(freq_comb) > 400:
        #    self.fpga.write_int(self.regs[np.where(self.regs == 'fft_shift_reg')[0][0]][1], 2**5 -1)
        #    time.sleep(0.1)
        #else:
        #    self.fpga.write_int(self.regs[np.where(self.regs == 'fft_shift_reg')[0][0]][1], 2**9 -1)
        #    time.sleep(0.1)
        #self.freq_comb = freq_comb
        return freq_comb

    def read_QDR_katcp(self):
        # Reads out QDR buffers with KATCP, as 16-b signed integers.
        self.QDR0 = np.fromstring(self.fpga.read('qdr0_memory', 8 * 2**20), dtype = '>i2')
        self.QDR1 = np.fromstring(self.fpga.read('qdr1_memory', 8 * 2**20), dtype = '>i2')
        self.I_katcp = self.QDR0.reshape(len(self.QDR0)/4., 4.)
        self.Q_katcp = self.QDR1.reshape(len(self.QDR1)/4., 4.)
        #self.I_dac_katcp = np.hstack(zip(self.I_katcp[:,1],self.I_katcp[:,0]))
        #self.Q_dac_katcp = np.hstack(zip(self.Q_katcp[:,1],self.Q_katcp[:,0]))
        #self.I_dds_katcp = np.hstack(zip(self.I_katcp[:,3],self.I_katcp[:,2]))
        #self.Q_dds_katcp = np.hstack(zip(self.Q_katcp[:,3],self.Q_katcp[:,2]))
        self.I_dac_katcp = np.dstack((self.I_katcp[:,1], self.I_katcp[:,0])).ravel()
        self.Q_dac_katcp = np.dstack((self.Q_katcp[:,1], self.Q_katcp[:,0])).ravel()
        self.I_dds_katcp = np.dstack((self.I_katcp[:,3], self.I_katcp[:,2])).ravel()
        self.Q_dds_katcp = np.dstack((self.Q_katcp[:,3], self.Q_katcp[:,2])).ravel()

    #Active PPS
    def active_pps(self, active=True):
        if active:
            write_to_fpga_register(self.fpga,{'pps_start_reg':1}, self.firmware_reg_list)
            print cm.OKGREEN + "PPS Registers Enabled" + cm.ENDC
        else:
            write_to_fpga_register(self.fpga,{'pps_start_reg':0}, self.firmware_reg_list)
            print cm.OKGREEN + "PPS Registers Disabled" + cm.ENDC

    # KidPy functions
    # 1. Read ADC
    # 2. Read FFT
    # 3. Digital Down Converter Time Domain
    # 4. Downsampled Channel Magnitudes
    def read_ADC(self,n=2**11):
        write_to_fpga_register(self.fpga, { 'adc_snap_ctrl_reg': 0 }, self.firmware_reg_list )
        write_to_fpga_register(self.fpga, { 'adc_snap_ctrl_reg': 1 }, self.firmware_reg_list )
        write_to_fpga_register(self.fpga, { 'adc_snap_ctrl_reg': 0 }, self.firmware_reg_list )
        write_to_fpga_register(self.fpga, { 'adc_snap_trig_reg': 1 }, self.firmware_reg_list )
        write_to_fpga_register(self.fpga, { 'adc_snap_trig_reg': 0 }, self.firmware_reg_list )

        # Read I and Q signals from ADC
        adc = (_np.fromstring(read_from_fpga_register(self.fpga, { 'adc_snap_bram_reg': (n/2)*8 }, self.firmware_reg_list)['adc_snap_bram_reg'] ,dtype='>i2')).astype('float')

        adc /= 2.0**15
        # ADC full scale is 2.2 V
        #adc *= 0.909091
        #I = np.hstack(zip(adc[0::4],adc[1::4]))
        #Q = np.hstack(zip(adc[2::4],adc[3::4]))
        I = _np.dstack((adc[0::4],adc[1::4])).ravel()
        Q = _np.dstack((adc[2::4],adc[3::4])).ravel()
        return I,Q

    def read_FFT(self):
        write_to_fpga_register(self.fpga, { 'fft_snap_ctrl_reg': 0 }, self.firmware_reg_list )
        write_to_fpga_register(self.fpga, { 'fft_snap_ctrl_reg': 1 }, self.firmware_reg_list )

        # Read the FFT
        fft_snap = (_np.fromstring(read_from_fpga_register(self.fpga, {'fft_snap_bram_reg':(2**9)*8}, self.firmware_reg_list)['fft_snap_bram_reg'], dtype='>i2')).astype('float')

        I0 = fft_snap[0::4]
        Q0 = fft_snap[1::4]
        I1 = fft_snap[2::4]
        Q1 = fft_snap[3::4]

        fft_mag0 = _np.sqrt(I0**2 + Q0**2)
        fft_mag0 = 20*_np.log10(fft_mag0)

        fft_mag1 = _np.sqrt(I1**2 + Q1**2)
        fft_mag1 = 20*_np.log10(fft_mag1)

        return fft_mag0, fft_mag1

    def read_mixer_snaps(self, chan, mixer_out = True, fir = True):
        if (chan % 2) > 0: # if chan is odd
            write_to_fpga_register(self.fpga, { 'DDC_chan_sel_reg': (chan - 1) / 2 }, self.firmware_reg_list )
        else:
            write_to_fpga_register(self.fpga, { 'DDC_chan_sel_reg': chan/ 2 }, self.firmware_reg_list )

        write_to_fpga_register(self.fpga, { 'DDC_fftbin_ctrl_reg': 0}, self.firmware_reg_list )
        write_to_fpga_register(self.fpga, { 'DDC_mixerout_ctrl_reg': 0 }, self.firmware_reg_list )

        if fir:
            write_to_fpga_register(self.fpga, { 'fir_snap_ctrl_reg': 0}, self.firmware_reg_list )
            write_to_fpga_register(self.fpga, { 'fir_snap_ctrl_reg': 1}, self.firmware_reg_list )

        write_to_fpga_register(self.fpga, { 'DDC_fftbin_ctrl_reg': 1}, self.firmware_reg_list )
        write_to_fpga_register(self.fpga, { 'DDC_mixerout_ctrl_reg': 1}, self.firmware_reg_list )

        mixer_in = (_np.fromstring(read_from_fpga_register(self.fpga, {'DDC_fftbin_bram_reg': 16*2**14}, self.firmware_reg_list)['DDC_fftbin_bram_reg'],dtype='>i2')).astype('float')

        if mixer_out:
            mixer_out = (_np.fromstring(read_from_fpga_register(self.fpga, {'DDC_mixerout_bram_reg': 8*2**14}, self.firmware_reg_list)['DDC_mixerout_bram_reg'],dtype='>i2')).astype('float')
            if fir:
                lpf_out = (_np.fromstring(read_from_fpga_register(self.fpga, {'DDC_fftbin_bram_reg': 8*2**14}, self.firmware_reg_list)['DDC_fftbin_bram_reg'],dtype='>i2')).astype('float')
            else:
                lpf_out = []
            return mixer_in, mixer_out, lpf_out
        else:
            return mixer_in

    def read_chan_snaps(self):
        # Reads the snap blocks at the bin select RAM and channelizer mux
        write_to_fpga_register(self.fpga, { 'buffer_out_ctrl': 0}, self.firmware_reg_list )
        write_to_fpga_register(self.fpga, { 'buffer_out_ctrl': 1}, self.firmware_reg_list )

        self.chan_data = _np.fromstring(read_from_fpga_register(self.fpga, {'buffer_out_bram': 8*2**9}, self.firmware_reg_list)['buffer_out_bram'],dtype = '>H')

        write_to_fpga_register(self.fpga, { 'chan_bins_ctrl': 0}, self.firmware_reg_list )
        write_to_fpga_register(self.fpga, { 'chan_bins_ctrl': 1}, self.firmware_reg_list )

        self.chan_bins = _np.fromstring(read_from_fpga_register(self.fpga, {'chan_bins_bram':4*2**14}, self.firmware_reg_list)['chan_bins_bram'],dtype = '>H')

        return

    def read_accum_snap(self):
        # Reads the avgIQ buffer. Returns I and Q as 32-b signed integers
        write_to_fpga_register(self.fpga, { 'accum_snap_ctrl_reg': 0}, self.firmware_reg_list )
        write_to_fpga_register(self.fpga, { 'accum_snap_ctrl_reg': 1}, self.firmware_reg_list )

        accum_data = (_np.fromstring(read_from_fpga_register(self.fpga, {'accum_snap_bram_reg': 16*2**9}, self.firmware_reg_list)['accum_snap_bram_reg'],dtype='>i')).astype('float')

        accum_data /= 2.0**17
        accum_data /= ((self.roach_config['roach_accum_len'])/512.)

        I0 = accum_data[0::4]
        Q0 = accum_data[1::4]
        I1 = accum_data[2::4]
        Q1 = accum_data[3::4]
        #I = np.hstack(zip(I0, I1))
        #Q = np.hstack(zip(Q0, Q1))
        I = _np.dstack((I0, I1)).ravel()
        Q = _np.dstack((Q0, Q1)).ravel()

        return I, Q




# Moved and saved from mux_channel
    # def _initialise_fpga(self):
    #
    #     if casperfpga is None:
    #         print "casperfpga module not loaded. No active FPGA instance"
    #         return
    #
    #     try:
    #         fpga = casperfpga.katcp_fpga.KatcpFpga( network_config[self.roachid]['roach_ppc_ip'], timeout = 10. )
    #     except RuntimeError:
    #         # bad things have happened, and nothing else should proceed
    #         print "Error, fpga not connected. "
    #         return
	# except:
    #         print 'Error connecting to \'%s\'. Is it switched on? Check network settings!'%(self.roachid)
    #
    #     we_uploaded_a_firmware = 0
    #
    #     firmware_file = os.path.join(filesys_config['rootdir'],general_config['firmware_file'])
    #
    #     if not fpga.is_connected():
    #         print "it looks like the fpga is not connected"
    #         return fpga
    #
    #     if not fpga.is_running():
    #         fpga = _lib_fpga.upload_firmware_file(fpga, firmware_file )
    #         we_uploaded_a_firmware = 1
    #
    #     else:
    #         fpga.get_system_information()
    #         sysinfo = fpga.system_info['system']
    #         if firmware_file.find(sysinfo)>=0:
    #             print 'Firmware already running (but not checked build date)'
    #         else:
    #             fpga = _lib_fpga.upload_firmware_file(fpga, firmware_file )
    #             we_uploaded_a_firmware = 1
    #
    #     # calibrate qdr if uploading firmware
    #     if we_uploaded_a_firmware:
    #         if _lib_fpga.calibrate_qdr(fpga) < 0:
    #             print "qdr calibration failed."
    #         else:
    #             _lib_fpga.write_to_fpga_register(fpga, { 'write_qdr_status_reg': 1 } )
    #
    #     # write registers (dds_shift + accum_len)
    #     _lib_fpga.write_to_fpga_register(fpga, { 'accum_len_reg': self.ROACH_CFG['roach_accum_len'], \
    #                                             'dds_shift_reg': self.ROACH_CFG['dds_shift']  } )
    #
    #     # configure downlink
    #     _lib_fpga.configure_downlink_registers(fpga, self.roachid)
    #
    #     return fpga
