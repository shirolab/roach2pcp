#!/usr/bin/env python

# ---> Set muscat default parameters for the synthesizer <---
# As MUSCAT uses windfreak synthesizer, this script just work for Windfreak SynthHD model

import time as _time
import logging as _logging
_logger = _logging.getLogger(__name__)

#TODO. It has to be in other place. Script directory. Move to this directory and only use it here
from ..configuration import color_msg as cm
from ..configuration import hardware_config as hc
from ..synthesizer import windfreaksynth_v2 as w2

from .. import ROACH_LIST, mux_channel

def _set_MUSCAT_default_values(serial_number, ref=0, ref_freq=10e6, clk_freq=512e6, clk_pow=0, lo_pow=15.75):
    # Synthesizer device
    syn_dev = w2.SynthHDDevice(str(serial_number))

    # External reference
    syn_dev.setReferenceSelect(ref)
    # 10 MHz reference
    syn_dev.setPLLReferenceFrequency(ref_freq)

    # ----- Channel 0. CLK -----
    syn_src_0 = w2.SynthHDSource(syn_dev, 0)
    syn_src_0.setFrequency(clk_freq)
    syn_src_0.setPower(0)
    # set AM off
    syn_src_0.setAMRunContinuously(0)
    # set FM off
    #syn_src_0.setFMContinuosMode(0)

    _time.sleep(0.1)
    # Check PLL Status
    if not syn_src_0.getPLLPowerOn():
        syn_src_0.setPLLPowerOn(0)
        syn_src_0.setPLLPowerOn(1)

    # Validate CLK
    if syn_src_0.getPLLPowerOn():
        print "[ " + cm.OKBLUE + "ok" + cm.ENDC +" ] CLK configured with the default MUSCAT parameters"
	_logger.info('CLK configured with the default MUSCAT parameters')
    else:
        print "[ " + cm.WARNING + "fail" + cm.ENDC +" ] Fail settig the MUSCAT CLK parameters"
	_logger.info('Fail settig the MUSCAT CLK parameters')

    # ----- Channel 1. LO -----
    syn_src_1 = w2.SynthHDSource(syn_dev, 1)
    syn_src_1.setRFAmpOn(1)
    syn_src_1.setPower(lo_pow)
    # set AM off
    syn_src_1.setAMRunContinuously(0)
    # set FM off
    #syn_src_1.setFMContinuousMode(0)

    _time.sleep(0.1)
    # Check PLL Status
    if not syn_src_1.getPLLPowerOn():
        syn_src_1.setPLLPowerOn(0)
        syn_src_1.setPLLPowerOn(1)

    # Validate CLK
    if syn_src_1.getPLLPowerOn():
        print "[ " + cm.OKBLUE + "ok" + cm.ENDC +" ] LO configured with the default MUSCAT parameters"
        _logger.info('LO configured with the default MUSCAT parameters')
    else:
        print "[ " + cm.WARNING + "fail" + cm.ENDC +" ] Fail settig the MUSCAT LO parameters"
	_logger.info('Fail settig the MUSCAT LO parameters')

def main(muxchannel, ref=0, ref_freq=10e6, clk_freq=512e6, clk_pow=0, lo_pow=15.75):
    _logger.info( "setting MUSCAT synthesizer default parameters" )
    _logger.info("Channel: {roachid}".format(roachid = muxchannel.roachid))

    # get the synthesizer serial number of the channel
    serial_number = hc['synth_config'][muxchannel.ROACH_CFG['synthid_clk']]['serial']

    _set_MUSCAT_default_values(serial_number, ref, ref_freq, clk_freq, clk_pow, lo_pow)

    return 0
