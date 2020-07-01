#!/usr/bin/env python
"""
Welcome to the roach control program...

This is the main module docstring

"""

def help():
    print (
    """
    Welcome to the Roach 2 Python Control Program for readout of superconducting microsresonators .

    For help, use the pcp.help() at anytime to print available top-level options. Alternatively, use
    pcp.<SUBMODULE>.help() to get detailed help for a given <SUBMODULE>.

    To begin, run the initialision script as pcp.scripts.initpcp(). This will read the configuration files, configure logging,
    create a number of module wide variables (labelled as pcp.UPPERCASEVAR)

    """
    )


# initial script run upon importing the module. the goal of this __init__ is provide
# access to the various submodules and variables.
# first set up logging.

# import logging modules (preceding _ hides variable)
import logging as _logging
# # create a top level logger (used for interactive logging)
logger = _logging.getLogger(__name__)

# create configuration dicts
GENERAL_CONFIG  = {}
FILESYS_CONFIG  = {}
HARDWARE_CONFIG = {}
LOGGING_CONFIG  = {}
NETWORK_CONFIG  = {}
ROACH_CONFIG    = {}
FIRMWARE_REGS   = {}

FIRMWARE_REG_DICT = {}
# set up module wide variables
ROOTDIR     = None
FIRMWAREDIR = None
SAVEDATADIR = None
TONELISTDIR = None
TONEHISTDIR = None
AMPCORRDIR  = None
PIDFILEDIR  = None
LIVEFILEDIR = None
LOGFILEDIR  = None
TUNINGEDIR  = None

# lists of important information defined at the top level for convenience (i.e. pcp.ROACH_LIST)
# will show the list of roaches defined in the confiruation files
ROACH_LIST = []
SYNTH_LIST = []
ATTEN_LIST = []

# create lists for hardware
SYNTH_HW_DICT = {}
ATTEN_HW_DICT = {}

SYNTHS_IN_USE = []
ATTENS_IN_USE = []

# import lib submodules
# import all sub-modules to top namespace
import scripts, configuration, logfile, kid, unittests, mux_channel, datalog_mp, toneslist, visualisation


# import aliases for convenience functions to top level
#from logfile import set_log_level as set_log_level

# #import sub-libraries required for logger (these packages are needed first)
# import configuration, lib, logfile
#
# # setup the logging configuration according to the configuration file
# _logconfig.dictConfig(configuration.logging_config)
#
# # set up the root logger to be able to print from each process
# _multiprocessing_logging.install_mp_handler()
#

#
# # lists of important information defined at the top level for convenience (i.e. pcp.ROACH_LIST)
# # will show the list of roaches defined in the confiruation files
# ROACH_LIST = configuration.roach_config.keys()
# SYNTH_LIST = configuration.hardware_config['synth_config'].keys()
# ATTEN_LIST = configuration.hardware_config['atten_config'].keys()
#



# # import all other sub-libraries
# import kid, unittests, mux_channel, datalog_mp, toneslist, scripts
# from drivers import synthesizer, attenuator
#
#
# #check dnsmasq is running
# from lib.check_dnsmasq import check_dnsmasq as _check_dnsmasq
# _check_dnsmasq()
