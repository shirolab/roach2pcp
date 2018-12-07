# functions for control and configuration of the fpga/ppc

import time as _time
from ..configuration import firmware_registers as _firmware_registers, roach_config as _roach_config, network_config as _network_config
from . import lib_qdr as _lib_qdr

def upload_firmware_file(fpga, firmware_file):
    """

    Upload a firmware file (fpg)

    """
    print 'Connecting...'
    t1 = _time.time()
    while not fpga.is_connected():
        if (time.time() - t1) > 10:
            print "Connection timeout to roach. Nothing done."
        return

    _time.sleep(0.1)
    if fpga.is_connected():
        print 'Connected to', fpga.host
        fpga.upload_to_ram_and_program(firmware_file)
    else:
        print 'No connection to the ROACH'
        return
    _time.sleep(0.5)
    print 'Uploaded', firmware_file
    return fpga

def write_to_fpga_register(fpga, register_dict):
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
        fpga.write_int( _firmware_registers[firmware_key],  int(register_value) )
        _time.sleep(0.1)


def configure_downlink_registers(fpga, roachid):
    """Given an fpga instance, configure GbE parameters for a given roachid"""

    config = _network_config[roachid]

    udp_src_mac =  config['udp_source_mac']
    udp_dest_mac = config['udp_dest_mac']

    udp_src_ip   = config['udp_source_ip']
    udp_src_port = config['udp_source_port']

    udp_dest_ip   = config['udp_dest_ip']
    udp_dest_port = config['udp_dest_port']

    # Write the mac addresses for the udp source (fpga) and destination (computer)
    fpga.write_int( _firmware_registers['udp_srcmac0_reg'],  int(udp_src_mac[4:], 16)   )
    _time.sleep(0.05)
    fpga.write_int( _firmware_registers['udp_srcmac1_reg'],  int(udp_src_mac[0:4], 16)  )
    _time.sleep(0.05)
    fpga.write_int( _firmware_registers['udp_destmac0_reg'], int(udp_dest_mac[4:], 16)  )
    _time.sleep(0.05)
    fpga.write_int( _firmware_registers['udp_destmac1_reg'], int(udp_dest_mac[0:4], 16) )
    _time.sleep(0.05)

    # Write the ip addresses for the udp source (fpga) and destination (computer)
    fpga.write_int( _firmware_registers['udp_srcip_reg'], udp_src_ip)
    _time.sleep(0.05)
    fpga.write_int( _firmware_registers['udp_destip_reg'], udp_dest_ip)
    _time.sleep(0.1)
    fpga.write_int( _firmware_registers['udp_destport_reg'], udp_dest_port)
    _time.sleep(0.1)
    fpga.write_int( _firmware_registers['udp_srcport_reg'], udp_src_port)
    _time.sleep(0.1)

    # Write the mac addresses for the udp source (fpga) and destination (computer)
    fpga.write_int( _firmware_registers['udp_start_reg'], 0)
    _time.sleep(0.1)
    fpga.write_int( _firmware_registers['udp_start_reg'], 1)
    _time.sleep(0.1)
    fpga.write_int( _firmware_registers['udp_start_reg'], 0)
    return


def calibrate_qdr(fpga):
# Calibrates the QDRs. Run after writing to QDR.
    write_to_fpga_register(fpga, { 'dac_reset_reg': 1 } )

    print 'DAC on'
    bFailHard = False
    calVerbosity = 1

    qdrMemName = _firmware_registers['qdr0_reg']
    qdrNames   = [_firmware_registers['qdr0_reg'], _firmware_registers['qdr1_reg']] # <- not used?

    print 'Fpga Clock Rate =', fpga.estimate_fpga_clock()
    fpga.get_system_information()
    results = {}
    for qdr in fpga.qdrs:
        print qdr
        mqdr = _lib_qdr.Qdr.from_qdr(qdr)
        results[qdr.name] = mqdr.qdr_cal2(fail_hard=bFailHard)
    print 'qdr cal results:',results
    for qdrName in ['qdr0','qdr1']:
        if not results[qdr.name]:
            print 'Calibration Failed'
            return -1
    print '\n************ QDR Calibrated ************'
    return 0

def define_DDS_LUT(self, freqs):
# Builds the DDS look-up-table from I and Q given by freq_comb. freq_comb is called with the sample rate equal to the sample rate for a single FFT bin. There are two bins returned for every fpga clock, so the bin sample rate is 256 MHz / half the fft length
    freq_residuals = self.select_bins(freqs)
    I_dds, Q_dds = np.array([0.]*(self.LUTbuffer_len)), np.array([0.]*(self.LUTbuffer_len))
    for m in range(len(freq_residuals)):
        I, Q = self.freqComb(np.array([freq_residuals[m]]), self.fpga_samp_freq/(self.fft_len/2.), self.dac_freq_res, random_phase = False, DAC_LUT = False)
        I_dds[m::self.fft_len] = I
        Q_dds[m::self.fft_len] = Q
    return I_dds, Q_dds

def pack_luts(self, freqs, transfunc = False, **kwargs):
# packs the I and Q look-up-tables into strings of 16-b integers, in preparation to write to the QDR. Returns the string-packed look-up-tables
    if transfunc:
        I_dac, Q_dac = self.freqComb(freqs, self.dac_samp_freq, self.dac_freq_res, random_phase = True, apply_transfunc = True, **kwargs)
    else:
        I_dac, Q_dac = self.freqComb(freqs, self.dac_samp_freq, self.dac_freq_res, random_phase = True)
        I_dds, Q_dds = self.define_DDS_LUT(freqs)
        self.I_dds = I_dds
        I_lut, Q_lut = np.zeros(self.LUTbuffer_len*2), np.zeros(self.LUTbuffer_len*2)
        I_lut[0::4] = I_dac[1::2]
        I_lut[1::4] = I_dac[0::2]
        I_lut[2::4] = I_dds[1::2]
        I_lut[3::4] = I_dds[0::2]
        Q_lut[0::4] = Q_dac[1::2]
        Q_lut[1::4] = Q_dac[0::2]
        Q_lut[2::4] = Q_dds[1::2]
        Q_lut[3::4] = Q_dds[0::2]
        I_lut_packed = I_lut.astype('>i2').tostring()
        Q_lut_packed = Q_lut.astype('>i2').tostring()
    return I_lut_packed, Q_lut_packed

def writeQDR(self, freqs, transfunc = False, **kwargs):
# Writes packed LUTs to QDR
    if transfunc:
    	I_lut_packed, Q_lut_packed = self.pack_luts(freqs, transfunc = True, **kwargs)
    else:
    	I_lut_packed, Q_lut_packed = self.pack_luts(freqs, transfunc = False)
        self.fpga.write_int(self.regs[np.where(self.regs == 'dac_reset_reg')[0][0]][1],1)
        self.fpga.write_int(self.regs[np.where(self.regs == 'dac_reset_reg')[0][0]][1],0)
        self.fpga.write_int(self.regs[np.where(self.regs == 'start_dac_reg')[0][0]][1],0)
        self.fpga.blindwrite(self.regs[np.where(self.regs == 'qdr0_reg')[0][0]][1],I_lut_packed,0)
        self.fpga.blindwrite(self.regs[np.where(self.regs == 'qdr1_reg')[0][0]][1],Q_lut_packed,0)
        self.fpga.write_int(self.regs[np.where(self.regs == 'start_dac_reg')[0][0]][1],1)
        self.fpga.write_int(self.regs[np.where(self.regs == 'accum_reset_reg')[0][0]][1], 0)
        self.fpga.write_int(self.regs[np.where(self.regs == 'accum_reset_reg')[0][0]][1], 1)
        np.save("last_freq_comb.npy", self.freq_comb)
        self.fpga.write_int(self.regs[np.where(self.regs == 'write_comb_len_reg')[0][0]][1], len(self.freq_comb))
        print 'Done.'
        return
