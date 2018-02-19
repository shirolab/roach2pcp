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
fpga = kp.getFPGA()

# UDP socket
s = socket(AF_PACKET, SOCK_RAW, htons(3))
#s.setsockopt(SOL_SOCKET,SO_RCVBUF,buf_size)
#s.bind((gc[np.where(gc=='udp_dest_device')[0][0]][1],3))

# Valon synthesizer instance
valon = kp.getValon()
    
# Roach interface
ri = roachInterface(fpga, gc, regs, valon)

# GbE interface
udp = roachDownlink(ri, fpga, gc, regs, s, ri.accum_freq)
udp.configSocket() # already configured up top

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






 
