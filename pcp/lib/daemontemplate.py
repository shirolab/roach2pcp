#!/usr/bin/env python
# 20171230 - PB
"""
Daemon template
=====

Provides
    1. A template daemon class that is used for all other sub-programs that are intended to be daemonised.

Code Overview
----------------------------
    - Requires a directory to save pid file


Comments
----------------------------
    - The daemon process is configured with the python-daemon module. See the following documentation for more
    information as to why this is the correct implementation.
        https://pypi.python.org/pypi/python-daemon/
        https://pagure.io/python-daemon/
        https://www.python.org/dev/peps/pep-3143/

"""


#------------------------------------------------------------------------------------------------------------
#--------------------------------------------- Code begins here ---------------------------------------------
#------------------------------------------------------------------------------------------------------------

# stdlib imports
import os, sys, psutil, types, time, select, signal, struct, logging, logging.handlers
# imports for daemon creation
import daemon, daemon.pidfile

from ..configuration import ROOTDIR, filesys_config
PIDFILEDIR = os.path.join(ROOTDIR, filesys_config['pidfiledir'])

#  ------  Class definitions ------

class daemonTemplate(object):

    def __init__(self, daemonname, loglevel = logging.WARNING):
        """ Class template for configuring a daemon process. The goal is to use this template for
        all subprograms that will use a daemon process.

        Can subclass this template to add additional functionality if required, by redefining certain functions.

        Requires:
        daemonname :: str

        Provides a number of methods, some of which are designed to be overridden when subclassing this template

        In particular, it creates a named pipe for simple communication between the standalone process. A signal.USR1 signal
        is sent which triggers the "handle request" method. This method will be specific to the functionality of the daemon process.


        """
        # define some class attributes
        self.daemonname = daemonname

        # Ensure that the name is a str (lots of test cases here - not all of them are caught as it stands
        assert type(daemonname) == str, "Given name is not a string"
        daemonname = daemonname or "default" # handle case of empty string for name

        # create logging instance for the daemon. If no handlers exist, write to stdout
        #self.logger = logging.getLogger("daemon." + daemonname)
        # remove
        logging.basicConfig(level = loglevel)
        self.logger = logging.getLogger(daemonname)

        #print self.logger.name, self.logger.level, self.logger.parent.name, self.logger.parent.level
        #print self.logger.handlers, self.logger.parent.handlers

        # Configure a daemon.TimeoutPIDLockFile.
        # Note that the file isn't created until the daemon process is created, and deletes it when process is terminated
        self.pidf = daemon.pidfile.TimeoutPIDLockFile( os.path.join( PIDFILEDIR, daemonname + ".pid" ) )

        # create the named-pipe/fifo that will be used for communication with the daemon
        self.fifoname = "." + self.daemonname + ".pipe"
        _ = os.mkfifo(self.fifoname) if not os.path.exists(self.fifoname) else None # this requires more checking
        self.logger.debug("Created fifo at {fifoname}".format(fifoname = self.fifoname))
        self.logger.critical("test message - delete")

        # Check to see if the PID file already exists
        if self.pidf.is_locked() and not self.pidf.i_am_locking():

            self.logger.warning("Logging p-id file was locked by another process")
            pid = self.pidf.read_pid()
            try:
                psutil.Process( pid )
                self.logger.warning("Logger already running with p-id {0} ".format(pid))
                self.ISRUNNING = 1

            except psutil.NoSuchProcess:
                self.logger.warning("p-id not found. Process doesn't appear to be running.")
                self.pidf.break_lock()
                self.logger.debug("Broke existing lock")
                self.ISRUNNING = 0

        else:
            self.ISRUNNING = 0

    def _open_fifo(self, mode=os.O_RDWR):
        """Helper function to open the fifo. Default kwarg for mode opens the socket in read/write mode,
        and so by default is non-blocking. (we may want to remove this option as I can't see a case where we wouldn't want this )"""
        # TODO add check to see if file exists and is open already?
        self._fifohandle = os.open(self.fifoname, mode)

    def _write_pid_to_fifo(self):
        _ = os.write(self._fifohandle, "DATA:PID:{pid}\n".format(pid = self.pidf.read_pid()) )

    def configure_context(self, **daemoncontext_kwargs):

        signal_map = daemoncontext_kwargs.pop('signal_map', None) or { signal.SIGTERM: self.daemon_terminate, \
                                                                        signal.SIGUSR1: self.handle_request }

        logfd_to_preserve = [handler.stream for handler in self.logger.handlers + self.logger.parent.handlers]
        commfd_to_preserve = [self._fifohandle]

        # make list of file descriptors to preserve, including any passed through kwargs
        fds_to_preserve = logfd_to_preserve + commfd_to_preserve + list(daemoncontext_kwargs.pop('files_preserve', []))
        # configure the daemon context
        return daemon.DaemonContext( working_directory=".",
                                        umask=0o002, # sets permissions - we might want to change later
                                        pidfile = self.pidf,
                                        files_preserve = fds_to_preserve, \
                                        signal_map = signal_map,
                                        **daemoncontext_kwargs )

    def run(self, function_to_run, *funargs, **daemoncontext_kwargs):
        self.logger.debug("Entered the function that. Configuring daemon context.")

        self._open_fifo()
        self.logger.debug("Opened fifo at {fifoname}".format(fifoname = self.fifoname))

        # check that the function to run in the daemon is actually a function.
        assert isinstance(function_to_run, (types.FunctionType, types.MethodType, types.BuiltinFunctionType, types.BuiltinMethodType)), \
                                        self.logger.warning("The function given to run in the daemon does not appear to be a function.")

        if self.ISRUNNING:
            self.logger.info("Not going to daemonise process... process appears to be already running")
            self._write_pid_to_fifo()
            return

        self.logger.debug("About to daemonise process...")

        with self.configure_context(**daemoncontext_kwargs):

            # add information about which daemonname is succesfully running
            self.logger.info( "Sucessfully daemonised. Running with PID {pid}\r".format(pid = self.pidf.read_pid()) )

            # write PID to pipe so that it can be read by the controlling script
            self._write_pid_to_fifo()
            self.logger.debug( "pid written to fifo" )

            # add some debugging logs as a check to see that the daemon is running as expected
            self.logger.debug( "cwd = {0}".format( os.getcwd() ) )

            # code to run goes here
            self.logger.debug( " about to enter the main program function " )
            function_to_run(*funargs)

    def handle_request(self, signum, frame):
        """
        This is a method to handle any request when the daemon receives a signal.SIGUSR1 (30) signal. To implement this
        functionalty, this method should be overridden when sub-classing the daemon to handle and required commands.

        Note that this function (i believe) will halt the "function_to_run" immediately, which could be problematic, and any clean up
        should be handled appropriately by this method.

        Defined by this function (8 byte string commands):
            - "GET_PID\n" - returns the PID of this process

        """
        # example code to pass back the PID of the running process

        # read info from the named pipe
        self.logger.info( "received user signal. processing request" )

        try:
            read, write, err = select.select([self._fifohandle], [],[], .1)
            if read:
                strcommand = os.read(self._fifohandle, 16).rstrip()
            else:
                strcommand = ""

            self.logger.debug( "command received: {command}".format(command = strcommand) )

        except select.error:
            if err.args[0] == 9:
                self.logger.warning( "caught select error 9" )# bad file descriptor - how to fix?
                return
            else:
                raise
        # process received command here
        self._process_message(strcommand)

    def _write_to_fifo( self, data ):
        try:
            os.write(self._fifohandle, data + "\n" )
        except:
            self.logger.warning( " Unable to write to fifo " )

    def _process_message(self, message):

        if message == "GET_PID":
            #os.write(self._fifohandle, str( self.pidf.read_pid() ) + "\n" )
            self._write_to_fifo( str( self.pidf.read_pid() ) )

        elif message.split(":")[0] == "SET_LOGLEVEL":
            loglevel = int(message.split(":")[1])
            self.set_logging_level(loglevel)

        # elif message == "GET_ISRUNNING":
        #     try:
        #         os.kill(self.pidf.read_pid(), 0)
        #         isrunning = True
        #     except OSError as err:
        #         if err.errno == 3:
        #             isrunning = False
        #         else:
        #             raise
        #   self._write_to_fifo(str(isrunning))

    def set_logging_level(self, logging_level):
        self.logger.setLevel(logging_level)
        self.logger.info( "daemon logger level changed to {logging_level}".format(logging_level=logging_level) )

    def daemon_stop(self, signum, frame):
        #print "Stopped Daemon\n"
        self.logger.info( "Logging daemon stopped. Start up again by sending 'kill -19 {pid}' ".format(pid=self.pidf.read_pid()) )
        os.kill(self.pidf.read_pid(), signal.SIGSTOP) # SIGINT appears to handle closing of the pid file correctly

    def daemon_terminate(self, signum, frame):
        #print "Stopped Daemon\n"
        self.logger.info( "Logging daemon terminated" )
        os.close(self._fifohandle)
        self.logger.debug( "closed fifo" )
        os.remove(self.fifoname)
        self.logger.debug( "removed fifo successfuly" )
        os.kill(self.pidf.read_pid(), signal.SIGINT)
        # this will cause an KeyboardInterrupt exception, so all closing stuff should be handled in try, except, finally in function_to_run

        # signal.SIGHUP should be used to restart program for reconfiguration

class daemonControl(object):
    """
    Container object that will be used to control and monitor the daemon process

    Given a "daemonname" string, this class will configure a set of commands that will be used to
    control and communicate (via a fifo) with a new daemon process.

    Note that because this class is intended to be used in the main process, print statements should be ok to use
    """
    def __init__(self, daemonname):

        self.daemonname = daemonname
        self.fifo_fname = ".{name}.pipe".format(name=daemonname)

        # open fifo (TODO some checking here is needed )
        if os.path.exists(self.fifo_fname):
            self.fifo_fd = os.open(self.fifo_fname, os.O_RDWR)
        else:
            print "fifo doesn't exist"
            return

        # get pid of the new daemon process
        self.pid = self._get_pid()

    def _read_from_fifo(self, fifo_fd):
        for i in range(10):
            read, write, err = select.select([fifo_fd], [],[], .2)
            if read:
                cmd = os.read(fifo_fd, 16).rstrip().split(":")
                break
            else:
                cmd = ""
        return cmd

    def _send_signal(self, signum):

        os.kill(self.pid, signum)

    def _get_pid(self):
        cmd_received = self._read_from_fifo(self.fifo_fd) or ""
        pid = cmd_received[-1] if "PID" in cmd_received else None

        if not pid:
            print "didn't receive pid from process through the fifo"
        else:
            return int(pid)

    def is_running(self):
        try:
            os.kill(self.pid, 0)
            return True
        except OSError as err:
            if err.errno == 3:
                return False
            else:
                raise

    def terminate(self, force=False):
        self._send_signal(signal.SIGTERM)
        time.sleep(0.5)
        if self.is_running():
            print "still running after attempted termination. Something has gone wrong. Try again with force=True"
        if self.is_running and force == True:
            self._send_signal(signal.SIGKILL)

    def send_message(self, message):
        # send the usr1 signal to tell the daemon to read the fifo
        self._send_signal(signal.SIGUSR1)
        # then write the message to fifo
        _ = os.write(self.fifo_fd, message )
