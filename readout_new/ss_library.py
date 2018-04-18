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
sys.path.append('/sscontrol/kidPy')
import valon_synth9
# Had to change these enough that they just became separate files
from ss_roachInterface import roachInterface
from ss_gbeConfig import roachDownlink
#import kidPy as kp # as-is, kidPy requires general_config etc...

#################################################################
# Library functions, available to call at any time

# Based on kidPy/(main or systemInit)
# Sets up communication with ROACHes
# Should this loop over ROACHes?
def systemInit():
    print "Initializing FPGA instance."
    fpga = getFPGA()
    print "Initializing synthesizer instance."
    synth = getSynth(hdw_cfg)
    print "Initializing ROACH interface."
    ri = roachInterface(fpga, gen_cfg, reg_cfg, synth)
    print "Setting up UDP socket."
    # This seems to need sudo...
    s = None
    s = socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(3))
    print "Setting up GbE interface."
    udp = roachDownlink(ri, fpga, gen_cfg, net_cfg['roach1'],
                        reg_cfg, s, ri.accum_freq)
    udp.configSocket()
    return fpga, ri, udp, synth

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
def getSynth(hdw_cfg):
    try:
        # Here we want a switch based on
        # hc['synthesizer']['synth1']['synthmake']
        synth = valon_synth9.Synthesizer(
            hdw_cfg['synthesizer']['synth1']['synth_comm_port'])
        synth.make = hdw_cfg['synthesizer']['synth1']['synthmake']
        return synth
    except OSError:
        "Synth could not be initialized."
        return None

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
    
###################################################
# Initial execution for standard operation
if __name__ == "__main__":
    # Load config files
    gen_cfg, hdw_cfg, fsy_cfg, lgg_cfg, net_cfg, rch_cfg, reg_cfg = get_config()

"""
Standard sequence of events (after __main__ above is done):

fpga, ri, udp, synth = systemInit() # takes us to main_opt in kidPy

"""
    
    
