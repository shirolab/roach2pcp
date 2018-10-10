#!/usr/bin/env python

# ss_library.py
#
# This script is to be invoked upon starting ipython and:
#
# 1. Loads up all necessary modules, variables, aliases, etc. for
#    command-line interface with the ROACH.
#    Upon automatic invocation does NOT require communication with
#    the ROACH -- see if __name__ == "__main__" below    
#
# 2. Places a standard set of routines/functions in the workspace
#    which can be easily called to perform most generic operations
#    (many of these will require the ROACH to be active)

# Generic packages
import numpy as np
import sys
import os
import struct
import time
import yaml
# I REALLY don't like this...
#from socket import * # can we find all instances and prepend 'socket'?
import socket 
# Less-generic packages (but not developed by us)
import casperfpga
# Packages that live in kidPy
#sys.path.append('/sscontrol/kidPy')
import valon_synth9
# Had to change these enough that they just became separate files
from ss_roachInterface import roachInterface
from ss_gbeConfig import roachDownlink
#import kidPy as kp # as-is, kidPy requires general_config etc...

#################################################################
# Library functions, available to call at any time

# Based on kidPy/(main or systemInit)
# Sets up communication with ROACHes, no need to have firmware uploaded yet
# Takes us to "menu" part of kidPy
# Should this loop over ROACHes?
def systemInit1():
    print "Initializing FPGA instance."
    fpga = getFPGA()
    print "Initializing synthesizer instance."
    synth = getSynth()
    print "Initializing ROACH interface."
    ri = roachInterface(fpga, gen_cfg, reg_cfg, synth)
    print "Setting up UDP socket."
    # This seems to need sudo...
    s = None
    s = socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(3))
    print "Setting up GbE interface."
    udp = roachDownlink(ri, fpga, gen_cfg, net_cfg['roach1'],
                        reg_cfg, fsy_cfg, s, ri.accum_freq)
    udp.configSocket()
    return fpga, ri, udp, synth

# Second initialization step - need firmware uploaded for this
# Equivalent to option 2
def systemInit2(fpga, ri, udp, synth):
    print "Configuring synthesizer."
    initSynth(synth)
    # Write accum length - very necessary
    fpga.write_int(reg_cfg['accum_len_reg'], ri.accum_len - 1)
    time.sleep(0.1)
    fpga.write_int(reg_cfg['dds_shift_reg'], int(gen_cfg['dds_shift']))
    time.sleep(0.1)
    # ri.lpf(ri.boxcar) # commented out in kidPy, reg doesn't exist! 
    print "Calibrating QDR."
    ri.qdrCal()
    fpga.write_int(reg_cfg['write_qdr_status_reg'], 1)
    print "Configuring UDP downlink."
    udp.configDownlink()
    return fpga, ri, udp, synth

# Write a test tone list to fpga - either full or single tone (in gen_cfg)
# Based on kidPy/writeVnaComb
def writeTestcomb(cw = False):
    try:
        # Make frequency comb
        if cw:
            ri.freq_comb = np.float(gen_cfg['test_freq'])
        else:
            ri.makeFreqComb()
        # Make sure FFT shift can handle size of comb
        if (np.size(ri.freq_comb) > 400):
            fpga.write_int(reg_cfg['fft_shift_reg'], 2**5 - 1)
            time.sleep(0.1)
        else:
            fpga.write_int(reg_cfg['fft_shift_reg'], 2**9 - 1)
            time.sleep(0.1)
        # Upconvert frequencies using center_freq
        if (np.size(ri.freq_comb) > 1):
            ri.upconvert = np.sort(((ri.freq_comb + (ri.center_freq)*1.0e6))/1.0e6)
        else:
            ri.upconvert = (ri.freq_comb + (ri.center_freq)*1.0e6)/1.0e6
        print "Writing", np.size(ri.upconvert), "RF tones. "
        #print ri.upconvert
        # Write to QDR
        ri.writeQDR(ri.freq_comb, transfunc = False)
        # Change this to text file in right location
        np.save(fsy_cfg['tonelistdir'] + '/last_freq_comb.npy', ri.freq_comb)
        print "Tones written to QDR and saved to", \
            fsy_cfg['tonelistdir'], "/last_freq_comb.npy."
        if not (fpga.read_int(reg_cfg['dds_shift_reg'])):
            if reg_cfg['DDC_mixerout_bram_reg'] in fpga.listdev():
                shift = ri.return_shift(0)
                if (shift < 0):
                    print "Error finding DDS shift."
                    return
                else:
                    fpga.write_int(reg_cfg['dds_shift_reg'], ri.dds_shift)
    except KeyboardInterrupt:
        return
    return

# Write a stored tone list to fpga.
# If no argument given, uses current_tonelist - otherwise argument
def writeTonelist(tonelist = 'current_tonelist'):
    if not fpga:
        print "ROACH link down."
        return
    try:
        freq_comb = np.load(tonelist)
        freq_comb = freq_comb[freq_comb != 0]
        freq_comb = np.roll(freq_comb, - np.argmin(np.abs(freq_comb)) - 1)
        ri.freq_comb = freq_comb
        # Make sure FFT shift can handle size of comb
        if (len(ri.freq_comb) > 400):
            fpga.write_int(reg_cfg['fft_shift_reg'], 2**5 - 1)
            time.sleep(0.1)
        else:
            fpga.write_int(reg_cfg['fft_shift_reg'], 2**9 - 1)
            time.sleep(0.1)
        # Upconvert frequencies using center_freq
        ri.upconvert = np.sort(((ri.freq_comb + (ri.center_freq)*1.0e6))/1.0e6)
        print "RF tones: ", ri.upconvert
        # Write to QDR
        ri.writeQDR(ri.freq_comb, transfunc = False)
        # Change this to text file in right location
        np.save("last_freq_comb.npy", ri.freq_comb)
        print "Tones written to QDR and saved to last_freq_comb.npy."
    except KeyboardInterrupt:
        return
    return
    
# Based on kidPy/getFPGA
def getFPGA(roachnum = 'roach1'):
    try:
        fpga = casperfpga.katcp_fpga.KatcpFpga(
            net_cfg[roachnum]['roach_ppc_ip'], timeout = 120);
        return fpga
    except RuntimeError:
        print "No connection to ROACH."
        return None

# Based on kidPy/getValon
def getSynth():
    try:
        # Switch based on synth make
        if hdw_cfg['synthesizer']['synth1']['synthmake'] == 'valon':
            synth = valon_synth9.Synthesizer(
                hdw_cfg['synthesizer']['synth1']['synth_comm_port'])
            synth.make = hdw_cfg['synthesizer']['synth1']['synthmake']
            return synth
    except OSError:
        "Synth could not be initialized."
        return None

# Based on kidPy/initValon
def initSynth(synth):
    if synth.make == 'valon':
        synth.set_ref_select(0)
        synth.set_refdoubler(gen_cfg['CLOCK'], 0)
        synth.set_refdoubler(gen_cfg['LO'], 0)
        synth.set_pfd(gen_cfg['CLOCK'], 40.)
        synth.set_pfd(gen_cfg['LO'], 10.)
        synth.set_frequency(gen_cfg['LO'], np.float(gen_cfg['center_freq']))
        synth.set_frequency(gen_cfg['CLOCK'], 512.)
        synth.set_rf_level(gen_cfg['CLOCK'], 7)
        synth.set_rf_level(gen_cfg['LO'], 10)
    return

# Load config files into workspace - can recall if something changes
def get_config():
    gen_cfg = yaml.load(file('./configuration/general_config.cfg','r'))
    hdw_cfg = yaml.load(file('./configuration/hardware_config.cfg','r'))
    fsy_cfg = yaml.load(file('./configuration/filesys_config.cfg','r'))
    lgg_cfg = yaml.load(file('./configuration/logging_config.cfg','r'))
    net_cfg = yaml.load(file('./configuration/network_config.cfg','r'))
    rch_cfg = yaml.load(file('./configuration/roach_config.cfg','r'))
    reg_cfg = yaml.load(file('./configuration/firmware_registers.cfg','r'))
    return gen_cfg, hdw_cfg, fsy_cfg, lgg_cfg, net_cfg, rch_cfg, reg_cfg

# Based on kidPy/getSystemState (need to make more useful)
def getSystemState(fpga, ri, udp, synth):
    print "Current system state at", time.strftime("%Y-%m-%d %H:%M:%S",time.gmtime()), "UTC"
    print
    print "DDS shift:", fpga.read_int(reg_cfg['dds_shift_reg'])
    print "FFT shift:", fpga.read_int(reg_cfg['fft_shift_reg'])
    print "Number of tones:", fpga.read_int(reg_cfg['read_comb_len_reg'])
    print "QDR Cal status:", fpga.read_int(reg_cfg['read_qdr_status_reg'])
    print
    print "Data downlink:"
    print "Stream status:", fpga.read_int(reg_cfg['read_stream_status_reg'])
    print "Data rate: ", ri.accum_freq, "Hz", ", " + str(np.round(gen_cfg['buf_size'] * ri.accum_freq / 1.0e6, 2)) + " MB/s"
    print
    rmsI, rmsQ, crest_factor_I, crest_factor_Q = ri.rmsVoltageADC()
    print "ADC V_rms (I,Q):", rmsI, "mV, ", rmsQ, "mV"
    print "Crest factor (I,Q):", crest_factor_I, "dB, ", crest_factor_Q, "dB"
    print
    print "Synth state:"
    print "LO center freq:", ri.center_freq, "MHz"
    print "Current LO freq:", synth.get_frequency(gen_cfg['LO']), "MHz"
    print "Current LO power:", synth.get_rf_level(gen_cfg['LO']), "dBm"
    print "Current clock freq:", synth.get_frequency(gen_cfg['CLOCK']), "MHz"
    print "Current clock power:", synth.get_rf_level(gen_cfg['CLOCK']), "dBm"
    return
    
    
###################################################
# Initial execution for standard operation
if __name__ == "__main__":
    # Load config files
    gen_cfg, hdw_cfg, fsy_cfg, lgg_cfg, net_cfg, rch_cfg, reg_cfg = get_config()

"""
Standard sequence of events (after __main__ above is done):

fpga, ri, udp, synth = systemInit1() # Takes us to main_opt in kidPy
ri.uploadfpg() # Only if needed
fpga, ri, udp, synth = systemInit2(fpga, ri, udp, synth) # Todownlink config
writeTestcomb() # Definitely needed
udp.testDownlink(5) # Flush out packets, returns 0 for good
udp.printChanInfo(0,1) # Inspect packets explicitly
udp.saveDirfile_chanRangeIQ(time_interval = 10) 
# Stream data to /data/dirfiles for some time (can specify channels)

# To capture a packet:
sudo tshark -x -i DEVICE -c 1 > packet

"""
    
    
