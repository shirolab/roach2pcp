#!/usr/bin/env python
# 20171230 - PB
"""
logfile
-------

Provides an interface to the pcp logging framework. This is a vastly simplified implementation based on
the external multiprocessing_logging module (sudo pip install multiprocessing_logging).

IMPORTANT: note that when a muxChannel has been defined, it will adopt the current logging settings, and currently,
can not be changed. This means that once debugging has finished, shut down the muxChannel, change the log level, and
reinitialise the muxChannel.

Helper function pcp.logfile.set_log_level(); a simple function to set the logging level of all defined loggers

The pcpFormatter class that is used to format the log records, and add some small funcitonality above that
available in the python logging package.
"""
#
# General
# -------
# - When running normally, the functions contained in this module will be rarely used.
# - Upon first import of pcp, the logging configuration is set up and a top level logger is defined
# as pcp.logger for manual logging from the command line
# - The default settings configure both logging to a file, and logging to the screen. The level/severity of displayed
# messages can be tuned by using pcp.logfile.set_log_level(level)

#    - To test this module, you can run it as a standalone program by calling it from the mutltitone directory with
#    "python -m readout_new.logfile" which will run the script with __name__ = __main__ .


#------------------------------------------------------------------------------------------------------------

# general stdlib imports
#import os as os
import logging, logging.config
import multiprocessing_logging as mplogging

#access module wide variables
import pcp

# Load configuration files
# from .configuration import filesys_config, logging_config, LOGFILEDIR

# Create local level logger
_logger = logging.getLogger(__name__)

# modify the filename (this happens on initial import before logging.dictConfig happens)
# logfilename = logging_config['handlers']['filelog']['filename']
# logging_config['handlers']['filelog']['filename'] = os.path.join(LOGFILEDIR, logfilename)

#------------------------------------------------------------------------------------------------------------
#  ------  Class definitions ------
#------------------------------------------------------------------------------------------------------------
# Custom formatter to handle different formats for different logging levels
# https://stackoverflow.com/questions/1343227/can-pythons-logging-format-be-modified-depending-on-the-message-log-level

class pcpFormatter(logging.Formatter):
    def __init__(self):

        super(pcpFormatter, self).__init__()

        self.FORMATS = {logging.DEBUG : pcp.LOGGING_CONFIG['formatters']['debugformat'].get('format', None),
                        'DEFAULT'     : pcp.LOGGING_CONFIG['formatters']['fileformat'].get('format', None)}
                   #logging.INFO  : logging_config['formatters']['screenformat'].get('format', None),

    def format(self, record):

        self._fmt = self.FORMATS.get(record.levelno, self.FORMATS['DEFAULT'])

        #levelname_color = color_msg.COLOR_SEQ % color_msg.LOGCOLORS[record.levelname]) + levelname + RESET_SEQ

        return logging.Formatter.format(self, record)

# #  ------  Function definitions ------

def _get_logging_handlers(logger, get_all = True):
    """Helper function to return handlers for a given logger. If get_all is True, the function traverses
    the logger hierarcy up to root. """

    handler_dict = {logger.name: logger.handlers}

    if get_all:
        while logger.name is not "root":
            handler_dict[logger.name] = logger.handlers
            logger = logger.parent

        handler_dict[logger.root.name] = logger.root.handlers

    return handler_dict
#
# def configure_logging():
#     """
#     Reinitialise the logging configuration using dictConfig() and the current dictionary
#     defined by pcp.configuration.logging_config. Use pcp.configuration.reload_configfiles() to refresh
#     changes to configuration dictionaries, then run this function.
#
#     """
#
#     _logconfig.dictConfig(logging_config)
#
#     logger = logging.getLogger(__name__)
#     logger.info('Logging configuration (re)initialised as {logname}'.format(logname=logger.name))
#

def set_log_level(level, which = 'screen'):
    """
    Function to set the logging level of the defined logging handlers.

    Parameters
    ----------
    level : int
        Logging level - typically one of the logging levels (DEBUG, INFO, WARNING, CRITICAL, ERROR)

    which : str
        Which logging hanlder to change. Available options are ['screen', 'file', 'all'].

    """

    assert which in ['screen', 'file', 'all'], "Unknown option for which handler to set: {0}".format(which)
    logger = logging.getLogger(__name__).root # get the root logger

    #streamhandler = filter(lambda h: isinstance(h, logging.StreamHandler),          logger.handlers)[0]
    #filehandler   = filter(lambda h: isinstance(h, logging.handlers.SocketHandler), logger.handlers)[0]
    if len(logger.handlers) == 0:
        _logger.warning("No handlers available for {0}".format(logger.name))

    for handler in logger.handlers:
        assert isinstance(handler, mplogging.MultiProcessingHandler), "only multiprocessing logging currently implemented"
        #    handler = handler.sub_handler
        print handler.sub_handler
        if which == "all":
            handler.setLevel(level)
        elif which == "screen" and type(handler.sub_handler) is logging.StreamHandler:
            handler.setLevel(level)
        elif which == "file" and type(handler.sub_handler) in (logging.handlers.TimedRotatingFileHandler,
                                                            logging.handlers.RotatingFileHandler):
            handler.setLevel(level)

        logger.info("{handlertype} now logging with level: {level}".format( handlertype = type(handler.sub_handler),\
                                                                            level = logging.getLevelName(handler.level)) )
