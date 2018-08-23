#!/usr/bin/env python
# 20171230 - PB
"""
logfile
=====

Provides

    1. A standalone logging daemon program that reads, parses and handles log entries from multiple processes and writes to a
    common log file.

    2. start_logging_daemon() - the function to start the logging daemon. When run, this function will configure the logging according
    to logging.cfg, instantiate the daemon, and run the logging function. The function then returns a loggingController object that
    provides a simple interface to the newly spawned process (e.g. terminate, is_running...etc).

    3. get_new_logger(name, level) - a convenience function that configures a new logger that can log to the logging daemon.

Code Overview
----------------------------
    - Configures a ThreadedSocketServer to listen on a TCP port (determined from configuration/logging.cfg)
    - A custom LogRecordStreamHandler is attached to the server to handle the received log records
    - Create a custom logDaemon class that is based on the base daemonTemplate from templates/daemontemplate.py

Comments
----------------------------
    - This code uses the stdlib logging module to handle log events
    - The SocketServer code is shamelessly adapated from the cookbook example given here
        https://docs.python.org/2/howto/logging-cookbook.html#sending-and-receiving-logging-events-across-a-network

Usage
----------------------------

    - To test, play and bugfind, open an ipython console,
        >>> import pcp
        >>> logctrl = pcp.logfile.start_logging_daemon()

        # where logctrl is an object that provides a method to interact with the spawned process. See loggingController
        docs for more infomation.

    - The intended way to use this module will be run it from a higher level script, but this loggingController will be available
    to the user. In the near future, there will be more functionality added to expand the communication with the logging daemon
    (see todo list in the source code)

"""
#    - To test this module, you can run it as a standalone program by calling it from the mutltitone directory with
#    "python -m readout_new.logfile" which will run the script with __name__ = __main__ .


# TODO
# clean up socketserver on exit
# implement rotating file handler for each day?

# include how to set level?

# tests to perform in unit tests
# test initialisation of logger tc = rn.logfile.initalise_logging_daemon()
# handle re-use address appropriately
# test handler
# configure logging daemon from config file
# decide on naming convention for loggers
# set log level interactively (will need a function in logDaemon to control that)
# add option to print logger to screen as well for debugging purposes

#------------------------------------------------------------------------------------------------------------

# general stdlib imports
import os, sys, errno, time, logging, psutil, pickle, struct, select, subprocess as _subprocess
# imports for daemon creation
import signal, daemon, daemon.pidfile
# imports for socket server
import socket, SocketServer
# import daemon template and controller
from .lib.daemontemplate import daemonTemplate, daemonControl

# Load configuration files
from .configuration import filesys_config, logging_config

# Set up directories from configuration files
ROOTDIR = filesys_config['rootdir']
LOGFILEDIR = os.path.join(ROOTDIR, filesys_config['logfiledir'])
PIDFILEDIR = os.path.join(ROOTDIR, filesys_config['pidfiledir'])

# Ensure that those paths exist
if not os.path.exists(LOGFILEDIR): os.mkdir(LOGFILEDIR)
if not os.path.exists(PIDFILEDIR): os.mkdir(PIDFILEDIR)

# Specify the logname for this script for easy modification later on if required
LOGNAME = logging_config["logrootname"]
LOGFILENAME = os.path.join(LOGFILEDIR, logging_config["logfilename"])

# Get host and port from configuration file
LOGHOST = logging_config["serverconfig"]["host"]
LOGPORT = logging_config["serverconfig"]["port"]
LOGPORT = 9075 if LOGPORT == "default" else LOGPORT

# Set the name of the daemon process to be spawned (for logging purposes)
daemonname = "loggingdaemon"
# Create logger
#logger = logging.getLogger(daemonname)

#------------------------------------------------------------------------------------------------------------
#  ------  Class definitions ------
#------------------------------------------------------------------------------------------------------------

class LogRecordStreamHandler(SocketServer.StreamRequestHandler):
    """
    Handler for a streaming logging request, which is used by the TCPThreadedServer below
    to read and parse the logrecord and write it to the log file.

    """
    def handle(self):
        """
        Handle multiple requests - each expected to be a 4-byte length,
        followed by the LogRecord in pickle format. Logs the record
        according to whatever policy is configured locally.
        """
        while True:
            chunk = self.connection.recv(4)
            if len(chunk) < 4:
                break
            slen = struct.unpack('>L', chunk)[0]
            chunk = self.connection.recv(slen)
            while len(chunk) < slen:
                chunk = chunk + self.connection.recv(slen - len(chunk))
            obj = pickle.loads(chunk)
            logrecord = logging.makeLogRecord(obj)
            self.handleLogRecord(logrecord)
            time.sleep(0.1)

    def handleLogRecord(self, logrecord):
        logger = logging.getLogger(logrecord.name)
        logger.handle(logrecord)

class LogRecordSocketReceiver(SocketServer.ThreadingTCPServer):
    """
    Simple TCP socket-based logging receiver to receive log entries from other parts of the application.

    See here for detailed documentation:
    https://docs.python.org/2/library/socketserver.html#request-handler-objects

    This works by setting up a local asynchronous TCP server on port 9020 (i.e. threaded so that
    simultaneous requests are handled correctly) which uses the handler defined by the LogRecordStreamHandler.

    """
    logger = logging.getLogger(daemonname + ".logsocketserver")

    allow_reuse_address = True
    def __init__(self,  host = LOGHOST, port = LOGPORT, handler = LogRecordStreamHandler):

        # make sure that the port is not in use
        try:
            print host, port
            SocketServer.ThreadingTCPServer.__init__(self, (host, port), handler, False)
            self.allow_reuse_address = True # Prevent 'cannot bind to address' errors on restart
            self.server_bind()     # Manually bind, to support allow_reuse_address
            self.server_activate() # ( see above )

        except socket.error as err:
            if err.errno == errno.EADDRINUSE:
                # get and close the socket?
                self.logger.error("confiugration of tcpserver failed; address already in use")
                #print "error, check to see if logdaemon is already running"
            else:
                self.logger.exception("confiugration of tcpserver failed;")

        # these may not currently be in use
        self.abort = 0
        self.timeout = 0.2
        #self.logname = None

    def serve_until_stopped(self):
        """
        Function that monitors the tcp socket for logging entries. Shutdown is initiated by KeyboardInterrupt
        or equivalently, signal.SIGINT/ctrl+c.
        """
        while True: # this should be replaced by self.__shutdown_request, or something similar
            try:
                rd, wr, ex = select.select( [self.socket.fileno()], [], [], self.timeout )
                if rd:
                    self.handle_request() # is a method in ThreadingTCPServer that uses the handler to process the request

            # catch the system call interupt when using daemon
            except select.error as err:
                if err.args[0] == 4:
                    continue
                else:
                    self.logger.exception("tcpserver.serve_until_stopped; error reading from select")

            # catch signal.SIGINT sent from main process to shut down
            except KeyboardInterrupt:
                self.logger.info("tcpserver.serve_until_stopped; received keyboard interupt, stop serving")
                break

        # close the logger appropriately
        logging.shutdown()
        self.logger.info("tcpserver.serve_until_stopped; logger successfully shutdown")

class logDaemon(daemonTemplate):
    """
    Class for logging daemon, subclassed from the generic daemonTemplate.

    Adds new functionality regarding logging:

    """
    def __init__(self, daemonname):
        super(logDaemon, self).__init__(daemonname) # initalise the parent class

    #@self._process_message(message)
    # def _process_message(self, message):

# Class to create the controller for logging daemon process
class loggingController(daemonControl):
    def __init__(self, daemonname):
        super(loggingController, self).__init__(daemonname) # initalise the parent class

    # implement log level controller in here - it will write update local loggers as well as in the logging daemon

#  ------  Function definitions ------

def configure_logging():
    """
    Initialise the logging server. When run, this script reads the logging configuration file and configures the
    TCP server in preparation for starting the daemon.

    Parameters
    ----------

    Returns
    -------

    """
    # add command line argument parsing to pass through level severity - if we want to only run in well defined loglevels

    # create a FileHandler object and adds it to the root logger ( this will be replaced by a logging.fileConfig )
    logging.basicConfig(filename = os.path.abspath(LOGFILENAME),
                        format   = '%(relativeCreated)5d %(name)-15s %(levelname)-8s %(message)s', # to be read from the logging configuration file
                        level    = logging.DEBUG) # this needs to be changed to be more general

    # get the logger for the initialisation
    print "Logging file created at {filename}".format(filename = os.path.abspath(LOGFILENAME))

    logger = logging.getLogger(LOGNAME)
    logger.info('Logging configuration initialised as {logname}'.format(logname=LOGNAME))
    return logger

def initalise_tcpserver(serve_forever=False):

    logger = logging.getLogger(LOGNAME)
    #logger.debug('instantiated loggingDaemon succesfully')
    try:
        tcpserver = LogRecordSocketReceiver()
        logger.debug("Instantiated TCP server successfuly ")

        if serve_forever:
            tcpserver.serve_until_stopped()
        else:
            return tcpserver

    except socket.error as err:
        if err.errno == errno.EADDRINUSE:
            # get and close the socket?
            logger.exception(err.strerror)
        else:
            logger.exception("help")
            raise


def start_logging_daemon():
    """
    Initialise the logging server. When run, this script spawns a daemon process that will listen on
    a TCP port for incoming logging entries and save them to the log file defined in the configuration
    file located in the configuration/ directory.

    Parameters
    ----------

    Returns
    -------


    """

    command_to_run = ["python" , "-m", "pcp.logfile"]
    subp = _subprocess.Popen(command_to_run, stdout = sys.stdout)

    time.sleep(1) # wait a second for process to be generated
    subp.communicate() # kills zombie process left behind when daemon process spawns

    return loggingController(daemonname)


def get_new_logger(logname = "", initial_log_level = logging.NOTSET):
    """
    Function that will return a logging instance configured to write to the remote logging server. This can be called anywhere,
    in any process, and will add a socketHandler to logger specified by logname.

    From other scripts, call using "from readout_new.logfile import get_new_logger".

    As this is a socketHandler, there is no need to define a formatter, since a socket handler sends the event as
    an unformatted pickle. The formatter is defined by the server in the by the logging daemon (and configure logging)

    If not specified using optional argument inital_log_level, the level of the new logger will be logging.NOTSET. This will then
    inherit from the root logger in that process. If no string is passed for logname, the root logger will be returned.

    Parameters
    ----------
    logname : str, optional
        A string for the name of the logger. Default is an empty string and corresponds to the rootLogger.
        Lower level loggers can be nested such as log1.log2.log3

    initial_log_level : int, optional
        An int that corresponds to a log level. See https://docs.python.org/2/library/logging.html#levels for defaults values.

    Returns
    -------
    logger : logging.Logger
        The loggin.Logger object corresponding to the logname

    """

    assert type(logname) == str

    logger = logging.getLogger(logname)
    logger.setLevel(initial_log_level)
    socketHandler = logging.handlers.SocketHandler(LOGHOST, LOGPORT)

    # check if the specific logger already has socketHandler attached
    existing_sockethandlers = map(lambda x: type(x) == logging.handlers.SocketHandler \
                                    and x.host == LOGHOST \
                                    and x.port == LOGPORT, logger.handlers)

    if logger.handlers and any( existing_sockethandlers ):
        logger.warning("logfile.get_new_logger; a logger with a socketHandler to host {host} on port {port} already exists".format(host=LOGHOST, port = LOGPORT))
    else:
        logger.addHandler(socketHandler)

    return logger

if __name__ =="__main__":

    # this is the main script that is run in start_logging_daemon() to spawn the daemon process
    logger = configure_logging()
    # change this to logDaemon
    d = daemonTemplate(daemonname, loglevel = logging.INFO)
    d.run( initalise_tcpserver, True, stdout = sys.stdout, stderr = sys.stdout )