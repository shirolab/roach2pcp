#!/usr/bin/env python
# 20171230 - PB
"""
logDaemon
=====

Provides
    1. A standalone logging daemon program that reads, parses and handles log entries from
    multiple processes and writes to a common log file.

Code Overview
----------------------------
    - Configures a ThreadedSocketServer to listen on a TCP port
    - A custom LogRecordStreamHandler is attached to the server to handle the received log records
    - The entire code is then wrapped up and spawned into an independant daemon process that runs until explicity closed
    by signal.SIGTERM.

Comments
----------------------------
    - This code uses the stdlib logging module to handle log events
    - The SocketServer code is shamelessly adapated from the cookbook example given here
        https://docs.python.org/2/howto/logging-cookbook.html#sending-and-receiving-logging-events-across-a-network

    - The daemon process is configured with the python-daemon module. See the following documentation for more
    information as to why this is the correct implementation.
        https://pypi.python.org/pypi/python-daemon/
        https://pagure.io/python-daemon/
        https://www.python.org/dev/peps/pep-3143/

    - To test this module, you can run it as a standalone program by calling it from the mutltitone directory with
    "sudo python -m readout_new.logging.logdaemon" which will run the script with __name__ = __main__ .

"""

# TODO
# include configuration file reading to set up log
#   - handle log files save desitination correctly
# clean up socketserver on exit
# implement rotating file handler for each day

#------------------------------------------------------------------------------------------------------------
#--------------------------------------------- Code begins here ---------------------------------------------
#------------------------------------------------------------------------------------------------------------

# imports for tcp socket server
import os, sys, pickle, struct
import logging, logging.handlers
import SocketServer

# imports for daemon creation
import signal, daemon, daemon.pidfile

# Get the pid file directory from the configuration file
from ..configuration import filesys_config
pidfiledir = filesys_config.config['pidfiledir']

# Ensure that the logging path directory exsists
if not os.path.exists(pidfiledir): os.mkdir(pidfiledir)

# specify the logname for this script for easy modification later on if required
LOGNAME = 'roachreadout.logdaemon'

#  ------  Class definitions ------

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

    def handleLogRecord(self, logrecord):
        # if a name is specified, we use the named logger rather than the one
        # implied by the record.
        # if self.server.logname is not None: # this might not be neccessary as we always want to log with the logrecord.name
        #     name = self.server.logname
        # else:
        name = logrecord.name
        print "Using log name: {logname}".format(logname = name)

        logger = logging.getLogger(name)
        print logger.handlers, logger.parent.handlers
        # N.B. EVERY record gets logged. This is because Logger.handle
        # is normally called AFTER logger-level filtering. If you want
        # to do filtering, do it at the client end.
        logger.handle(logrecord)

class LogRecordSocketReceiver(SocketServer.ThreadingTCPServer):
    """
    Simple TCP socket-based logging receiver to receive log entries from other parts of the application.

    See here for detailed documentation:
    https://docs.python.org/2/library/socketserver.html#request-handler-objects

    This works by setting up a local asynchronous TCP server on port 9020 (i.e. threaded so that
    simultaneous requests are handled correctly) which uses the handler defined by the LogRecordStreamHandler.

    """

    allow_reuse_address = 1

    def __init__(self, host='localhost',
                 port = logging.handlers.DEFAULT_TCP_LOGGING_PORT,
                 handler = LogRecordStreamHandler):

        SocketServer.ThreadingTCPServer.__init__(self, (host, port), handler)
        self.abort = 0
        self.timeout = 1
        self.logname = None

    def serve_until_stopped(self):
        import select
        abort = 0
        while not abort:
            rd, wr, ex = select.select([self.socket.fileno()],
                                       [], [],
                                       self.timeout)
            if rd:
                self.handle_request() # is a method in ThreadingTCPServer that uses the handler to process the request
            abort = self.abort


# Class to create the logging daemon process

class loggingDaemon(object):
    def __init__(self):
        """ Class for the logging daemon process.
        Sets up PID file called roachlog.pid in the pidfiledir defined in filesys_config.yaml

        """

        # Configure logger for the log configuration ;-)
        self.logger = logging.getLogger(LOGNAME)

        # need a test/check to handle if the pid file is already locked - as this is currently silent if it exisits
        self.pidf = daemon.pidfile.TimeoutPIDLockFile( os.path.join( pidfiledir, 'roachlog.pid' ) )

        if self.pidf.is_locked() and not self.pidf.i_am_locking():
            # then the file is locked by another process - most likely an error from previous processes
            # send warning to log, and break the lock
            self.logger.warning("logging pid file was locked by another process")
            self.pidf.break_lock()
            self.logger.debug("broke existing lock")
            self.pidf.acquire()
            self.logger.debug( "Lock transferred and is being held by me: {0}".format(self.pidf.i_am_locking()) )

        # debugging of logging

    def run(self):
        self.logger.debug("Entered run")

        context = daemon.DaemonContext( working_directory=".",
                                        umask=0o002, # sets permissions - we might want to change later
                                        stdout = sys.stdout,
                                        pidfile = self.pidf,
                                        files_preserve = [self.logger.parent.handlers[0].stream] )
                                        # Note that this is crucial to preserve the logging once the process is daemonised!
                                        # The .parent seems hackish, and should probably be changed later

        context.signal_map = { signal.SIGTERM: self.daemon_stop }
        self.logger.debug("starting context")

        with context:
            print self.logger.parent.handlers
            self.logger.info( "Running with PID {pid}\r".format(pid = self.pidf.read_pid()) )
            print "Running with PID {pid}\r".format(pid = self.pidf.read_pid())
            sys.stdout.flush()
            self.logger.debug( "cwd = {0}".format( os.getcwd() ) )
            # code to run goes here
            tcpserver = LogRecordSocketReceiver()
            self.logger.debug("About to start TCP server...")
            print "About to start TCP server..."

            tcpserver.serve_until_stopped()

    def configure_log(self):
        filename = 'example.log'
        self.filename = filename
        print "Logging file created at {filename}".format( filename = os.path.abspath(filename) )
        logging.basicConfig(
            filename = filename,
            format = '%(relativeCreated)5d %(name)-15s %(levelname)-8s %(message)s')

    def daemon_stop(self, signum, frame):
        print "Stopped Daemon\n"

        #logname = self.find_logfile()
        #with open(logname, "a") as f:
        #    f.write("Logger stopped\r")
        #os.kill(self.pidf.read_pid(), signal.SIGINT) # SIGINT appears to handle closing of the pid file correctly
        sys.exit(0)

def initialise_logger(verbosity=0):
    """
    Initialise the logging server. When run, this script spawns a daemon process that will listen on
    a TCP port for incoming logging entries and save them to the log file defined in the configuration
    file located in the configuration/ directory.

    Parameters
    ----------
    verbosity : int
        Level of versobity required for the log file.
            -1 - quiet mode. Only prints logging.WARNING and above
            +0 - level = logging.INFO messages and above [Default]
            +1 - level = logging.DEBUG, should be used for debugging only, as this will fill the
                        log file quickly!
    Returns
    -------

    References
    -------

    """

    # read logging configuration here

    # ideally want to have logging configured here!
    logger = logging.getLogger(LOGNAME)

    logger.info('starting loggingDaemon')
    d = loggingDaemon()
    logger.debug('instantiated loggingDaemon succesfully')
    d.run()

# main script for testing purposes
if __name__ == '__main__':
    print "Running main..."

    # for testing only - this will be removed and configuration will be handled in the
    # initialise_logger funciton
    filename = 'example.log'
    logging.basicConfig(
        filename = os.path.abspath(filename),
        format = '%(relativeCreated)5d %(name)-15s %(levelname)-8s %(message)s',
        level=logging.DEBUG)

    initialise_logger()
