"""
Script that is run to initialise pcp. This will take the place of the original module init, but won't be run automatically.
This reduces the amount of code run upon importing pcp, facilitating any debugging requirements.


"""

import os, sys, logging.config
import multiprocessing_logging as mplogging

# import top level pcp
import pcp

# create script logger
logger = logging.getLogger(__name__)

def _config_configuration():

    pcp.GENERAL_CONFIG,\
    pcp.HARDWARE_CONFIG,\
    pcp.FILESYS_CONFIG,\
    pcp.LOGGING_CONFIG,\
    pcp.NETWORK_CONFIG,\
    pcp.ROACH_CONFIG,\
    pcp.FIRMWARE_REGS   = pcp.configuration.lib_config.load_config('all')

    logger.info("successfully loaded configuration files")

def _config_filesystem():

    #filesys_config, logging_config = pcp.configuration.lib_config.load_config(['filesys_config','logging_config'])
    filesys_config, logging_config = pcp.FILESYS_CONFIG, pcp.LOGGING_CONFIG

    ROOTDIR = filesys_config['rootdir']

    FIRMWAREDIR = filesys_config['firmwaredir'] if os.path.isabs(filesys_config['firmwaredir']) \
                                                else os.path.join(ROOTDIR, filesys_config['firmwaredir'])
    SAVEDATADIR = filesys_config['savedatadir'] if os.path.isabs(filesys_config['savedatadir']) \
                                                else os.path.join(ROOTDIR, filesys_config['savedatadir'])
    TUNINGDIR   = filesys_config['tuningdir']   if os.path.isabs(filesys_config['tuningdir']) \
                                                else os.path.join(ROOTDIR, filesys_config['tuningdir'])
    TONELISTDIR = filesys_config['tonelistdir'] if os.path.isabs(filesys_config['tonelistdir']) \
                                                else os.path.join(ROOTDIR, filesys_config['tonelistdir'])
    TONEHISTDIR = filesys_config['tonehistdir'] if os.path.isabs(filesys_config['tonehistdir']) \
                                                else os.path.join(ROOTDIR, filesys_config['tonehistdir'])
    AMPCORRDIR  = filesys_config['ampcorrdir'] if os.path.isabs(filesys_config['ampcorrdir']) \
                                                else os.path.join(ROOTDIR, filesys_config['ampcorrdir'])
    PIDFILEDIR  = filesys_config['pidfiledir'] if os.path.isabs(filesys_config['pidfiledir']) \
                                                else os.path.join(ROOTDIR, filesys_config['pidfiledir'])
    LIVEFILEDIR = filesys_config['livefiledir'] if os.path.isabs(filesys_config['livefiledir']) \
                                                else os.path.join(ROOTDIR, filesys_config['livefiledir'])
    LOGFILEDIR  = logging_config['logfiledir'] if os.path.isabs(logging_config['logfiledir']) \
                                                else os.path.join(ROOTDIR, logging_config['logfiledir'])

    # set up file system according to the configuration files - no checks on permissions...
    if not os.path.exists(ROOTDIR)    : os.makedirs(ROOTDIR)
    if not os.path.exists(PIDFILEDIR) : os.makedirs(PIDFILEDIR)
    if not os.path.exists(LOGFILEDIR) : os.makedirs(LOGFILEDIR)
    if not os.path.exists(SAVEDATADIR): os.makedirs(SAVEDATADIR)
    if not os.path.exists(TUNINGDIR)  : os.makedirs(TUNINGDIR)
    if not os.path.exists(TONELISTDIR): os.makedirs(TONELISTDIR)
    if not os.path.exists(TONEHISTDIR): os.makedirs(TONEHISTDIR)
    if not os.path.exists(AMPCORRDIR) : os.makedirs(AMPCORRDIR)
    if not os.path.exists(LIVEFILEDIR): os.makedirs(LIVEFILEDIR)

    # create a dictionary that contains the firmware regsiters for each roachid
    #FIRMWARE_REG_DICT = {} <- now instantiated in top level pcp.__init__()
    for roachid in pcp.ROACH_CONFIG.keys():
        pcp.FIRMWARE_REG_DICT[roachid] = pcp.configuration.lib_config.get_firmware_register_dict(pcp.FIRMWARE_REGS, pcp.ROACH_CONFIG[roachid]["firmware_file"]) ["registers"]

    # if the firmware directory doesn't exist already, there will likely be a problem, so raise an exception
    # ( this should be moved to the filesys consistency checking code )

    if not os.path.exists(FIRMWAREDIR):
        raise OSError("Firmware directory doesn't exist. Please point to a valid directory ")
    elif not any( map(lambda x: os.path.splitext(x)[-1]=='.fpg', os.listdir(FIRMWAREDIR) ) ):
        raise AttributeError("Firmware directory doesn't appear to contain any .fpg files. Please point to a valid directory ")

    # update modulewide variables
    pcp.ROOTDIR     = ROOTDIR
    pcp.FIRMWAREDIR = FIRMWAREDIR
    pcp.LOGFILEDIR  = LOGFILEDIR
    pcp.SAVEDATADIR = SAVEDATADIR
    pcp.TUNINGDIR   = TUNINGDIR
    pcp.TONELISTDIR = TONELISTDIR
    pcp.TONEHISTDIR = TONEHISTDIR
    pcp.AMPCORRDIR  = AMPCORRDIR
    pcp.PIDFILEDIR  = PIDFILEDIR
    pcp.LIVEFILEDIR = LIVEFILEDIR

    pcp.ROACH_LIST = pcp.ROACH_CONFIG.keys()
    pcp.SYNTH_LIST = pcp.HARDWARE_CONFIG['synth_config'].keys()
    pcp.ATTEN_LIST = pcp.HARDWARE_CONFIG['atten_config'].keys()

def _config_logging(rootlogger, force = False):
    # load the logging config file
    logging_config = pcp.LOGGING_CONFIG

    # modify the filename
    logfilename = logging_config['handlers']['filelog']['filename']
    logging_config['handlers']['filelog']['filename'] = os.path.join(pcp.LOGFILEDIR, logfilename)

    # check that MultiProcessingHandler is not already running
    mploggers = [isinstance(x, mplogging.MultiProcessingHandler) for x in rootlogger.handlers]
    if any(mploggers):
        if force == True:
            [x.close() for x in rootlogger.handlers]
        else:
            rootlogger.warning("It appears that the multiprocessing logger is already running. Use force=True")
            return
        # configure and start

     # configure here
    logging.config.dictConfig(logging_config)
    rootlogger.info("updated logging configuration")

    mplogging.install_mp_handler(rootlogger)
    rootlogger.info("started multiprocessing logging server")

def _config_hardware():

    # import the synth dictionary from the drivers module
    from pcp.drivers.synthesizer import SYNTH_HW_DICT # note that we might need to be careful of import order here
    pcp.SYNTH_HW_DICT = SYNTH_HW_DICT
    logger.debug("synth dict : {0}".format( SYNTH_HW_DICT ) )

    from pcp.drivers.attenuator import ATTEN_HW_DICT
    pcp.ATTEN_HW_DICT = ATTEN_HW_DICT
    logger.debug("atten dict : {0}".format( ATTEN_HW_DICT ) )

    # #from .lib.lib_hardware import usb_detector - commented out before moving here
    #
    from pcp.lib.lib_hardware import initialise_connected_synths, initialise_connected_attens
    pcp.SYNTHS_IN_USE = initialise_connected_synths()
    pcp.ATTENS_IN_USE = initialise_connected_attens()

    #check dnsmasq is running
    from pcp.lib.check_dnsmasq import check_dnsmasq
    check_dnsmasq()

def main(interactive=False, force_log_restart = False):
    """
    Initialisation script that is used to configure pcp after the initial module import. Sets up the
    file configuration, configures logging

    """
    logger.info("running initialisation script")
    _config_configuration()
    _config_filesystem()
    _config_logging(logger.root, force=force_log_restart)
    _config_hardware()





# # import logging as _logging, logging.config as _logconfig
# import multiprocessing_logging as _multiprocessing_logging
# #import sub-libraries required for logger (these packages are needed first)
# import configuration, lib, logfile
#
# # setup the logging configuration according to the configuration file
# _logconfig.dictConfig(configuration.logging_config)
#
# # set up the root logger to be able to print from each process
# _multiprocessing_logging.install_mp_handler()
#
# # create a top level logger (used for interactive logging)
# logger = _logging.getLogger(__name__)
#
# # lists of important information defined at the top level for convenience (i.e. pcp.ROACH_LIST)
# # will show the list of roaches defined in the confiruation files
# ROACH_LIST = configuration.roach_config.keys()
# SYNTH_LIST = configuration.pcp.HARDWARE_CONFIG['synth_config'].keys()
# ATTEN_LIST = configuration.pcp.HARDWARE_CONFIG['atten_config'].keys()
#
# # import all other sub-libraries
# import kid, unittests, mux_channel, datalog_mp, toneslist, scripts
# from drivers import synthesizer, attenuator
#
# # import aliases for convenience functions to top level
# from lib.lib_misc import help_screen as help
# from logfile import set_log_level as set_log_level
#
# #check dnsmasq is running
# from lib.check_dnsmasq import check_dnsmasq as _check_dnsmasq
# _check_dnsmasq()
