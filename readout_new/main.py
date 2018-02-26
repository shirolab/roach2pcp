#!/usr/bin/env python

# This is the main script that
# - Offers a text-based command-line interface through
#   which standard routines maybe run
# - Handles requests from the LMT interface
# - Right now only gets the ROACH into a state in which it is
#   outputting packets that make sense

import numpy as np
import sys, os
import struct
import casperfpga
import valon_synth9
from socket import *
from roachInterface import roachInterface
from gbeConfig import roachDownlink
import time
import matplotlib.pyplot as plt
from sean_psd import amplitude_and_power_spectrum as sean_psd
from scipy import signal, ndimage, fftpack
import find_kids_interactive as fk
import kidPy as kp
plt.ion()

# Load general settings
gc = np.loadtxt("./general_config", dtype = "str")
firmware = gc[np.where(gc == 'FIRMWARE_FILE')[0][0]][1]
vna_savepath = gc[np.where(gc == 'VNA_SAVEPATH')[0][0]][1]
targ_savepath = gc[np.where(gc == 'TARG_SAVEPATH')[0][0]][1]
dirfile_savepath = gc[np.where(gc == 'DIRFILE_SAVEPATH')[0][0]][1]

# Load list of firmware registers
# (note: must manually update for different versions)
regs = np.loadtxt("./firmware_registers", dtype = "str")

# UDP packet
buf_size = int(gc[np.where(gc == 'buf_size')[0][0]][1])
header_len = int(gc[np.where(gc == 'header_len')[0][0]][1])

# Valon Synthesizer params
CLOCK = 2
LO = 1
lo_step = np.float(gc[np.where(gc == 'lo_step')[0][0]][1])
center_freq = np.float(gc[np.where(gc == 'center_freq')[0][0]][1])

# Optional test frequencies
test_freq = np.float(gc[np.where(gc == 'test_freq')[0][0]][1])
test_freq = np.array([test_freq])
freq_list = gc[np.where(gc == 'freq_list')[0][0]][1]

# Parameters for resonator search
smoothing_scale = np.float(gc[np.where(gc == 'smoothing_scale')[0][0]][1])
peak_threshold = np.float(gc[np.where(gc == 'peak_threshold')[0][0]][1])
spacing_threshold  = np.float(gc[np.where(gc == 'spacing_threshold')[0][0]][1])

###################################################
# Minimal set of things to initialize
# taken from kidPy/main

s = None
fpga = casperfpga.katcp_fpga.KatcpFpga(gc[np.where(gc == 'roach_ppc_ip')[0][0]][1], timeout = 120.)
#fpga = kp.getFPGA()

# UDP socket
s = socket(AF_PACKET, SOCK_RAW, htons(3))
#s.setsockopt(SOL_SOCKET,SO_RCVBUF,buf_size)
#s.bind((gc[np.where(gc=='udp_dest_device')[0][0]][1],3))

# Valon synthesizer instance
valon = valon_synth9.Synthesizer(gc[np.where(gc == 'valon_comm_port')[0][0]][1])
#valon = kp.getValon()
    
# Roach interface
ri = roachInterface(fpga, gc, regs, valon)

# GbE interface
udp = roachDownlink(ri, fpga, gc, regs, s, ri.accum_freq)
udp.configSocket()

# At this point in the main script we go to main_opt

# 0: Test connection to ROACH
result = kp.testConn(fpga)

# 1: Upload firmware
ri.uploadfpg()

# 2: Initialize system & UDP conn
kp.initValon(valon)
fpga.write_int(regs[np.where(regs == 'accum_len_reg')[0][0]][1], ri.accum_len - 1) # VERY necessary
#time.sleep(0.1)
#ri.qdrCal() # not necessary
#fpga.write_int(regs[np.where(regs == 'write_qdr_status_reg')[0][0]][1], 1) # not necessary...
udp.configDownlink()

# 3: Write test comb
ri.makeFreqComb()
#fpga.write_int(regs[np.where(regs == 'fft_shift_reg')[0][0]][1], 2**5 -1) # not necessary...
time.sleep(0.1)
ri.upconvert = np.sort(((ri.freq_comb + (center_freq)*1.0e6))/1.0e6)
#print "RF tones =", ri.upconvert
ri.writeQDR(ri.freq_comb, transfunc = False) # SUPER necessary
#np.save("last_freq_comb.npy", ri.freq_comb)
""" None of this shit needed!!!
if not (fpga.read_int(regs[np.where(regs == 'dds_shift_reg')[0][0]][1])):
    if regs[np.where(regs == 'DDC_mixerout_bram_reg')[0][0]][1] in fpga.listdev():
        shift = ri.return_shift(0)
        if (shift < 0):
            print "\nError finding dds shift: Try writing full frequency comb"
            
        else:
            fpga.write_int(regs[np.where(regs == 'dds_shift_reg')[0][0]][1], shift)
            print "Wrote DDS shift (" + str(shift) + ")"
    else:
        fpga.write_int(regs[np.where(regs == 'dds_shift_reg')[0][0]][1], ri.dds_shift)
"""        
# 7: Get system state
kp.getSystemState(fpga, ri, udp, valon)

# 8: Test downlink
udp.testDownlink(5)
# if ok (returns 0), write to this reg...
fpga.write_int(regs[np.where(regs == 'write_stream_status_reg')[0][0]][1], 1)

"""
# 9: Stream 
time_interval = 0.1 # or whatever
chan = 0 # or whatever
udp.printChanInfo(chan, time_interval)

######################################################
# To read out a packet:

# Use this to flush out any junk
udp.testDownlink(5)

# Grab a test packet
packet, data, header, saddr = udp.parsePacketData()

#######################################################
# To jankily write the time to packets continually:
while True:
    fpga.write_int('GbE_ctime',time.time())

"""




 
