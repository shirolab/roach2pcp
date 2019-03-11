#!/usr/bin/env python

print ( \
"""
Welcome to the Python Control Program for readout of kinetic inductance detectors
using Roach2 control boards.

This initialisation script will load all submodules...

For help, use the pcp.help() at anytime to print available top-level options. Alternatively, use
pcp.<SUBMODULE>.help() to get detailed help for a given <SUBMODULE>.

"""
)

# stdlib imports
import sys as _sys, pkgutil as _pkgutil, time as _time, logging as _logging, logging.config as _logconfig

import multiprocessing_logging as _multiprocessing_logging
#import sub-libraries required for logger (these packages are needed first)
import configuration, lib, logfile

# setup the logging configuration according to the configuration file
_logconfig.dictConfig(configuration.logging_config)

# set up the root logger to be able to print from each process
_multiprocessing_logging.install_mp_handler()

# lists of important information defined at the top level for convenience (i.e. pcp.ROACH_LIST)
# will show the list of roaches defined in the confiruation files
ROACH_LIST = configuration.roach_config.keys()
SYNTH_LIST = configuration.hardware_config['synth_config'].keys()
ATTEN_LIST = configuration.hardware_config['atten_config'].keys()

# import all other sub-libraries
import kid, synthesizer, unittests, mux_channel, datalog_mp, toneslist, scripts, attenuator

_logger = _logging.getLogger(__name__)
_logger.info("Logging configuration completed - current loglevel = {0}".format(_logging.getLevelName(_logger.root.handlers[0].level)))

# import aliases for convenience functions to top level
from lib.lib_misc import help_screen as help
from logfile import set_log_level as set_log_level

#check dnsmasq is running
from lib.check_dnsmasq import check_dnsmasq as _check_dnsmasq
_check_dnsmasq()
