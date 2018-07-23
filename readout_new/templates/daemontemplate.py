#!/usr/bin/env python
# 20171230 - PB
"""
Daemon template
=====

Provides
    1. A template daemon class that is used for all other sub-programs that are intended to be daemonised.

Code Overview
----------------------------
    - Configures a ThreadedSocketServer to listen on a TCP port
    - A custom LogRecordStreamHandler is attached to the server to handle the received log records
    - The entire code is then wrapped up and spawned into an independant daemon process that runs until explicity closed
    by signal.SIGTERM.

Comments
----------------------------
    - The daemon process is configured with the python-daemon module. See the following documentation for more
    information as to why this is the correct implementation.
        https://pypi.python.org/pypi/python-daemon/
        https://pagure.io/python-daemon/
        https://www.python.org/dev/peps/pep-3143/

    - To test this module ... etc

"""


#------------------------------------------------------------------------------------------------------------
#--------------------------------------------- Code begins here ---------------------------------------------
#------------------------------------------------------------------------------------------------------------

# stdlib imports
import os, sys, psutil, struct, logging, logging.handlers
# imports for daemon creation
import daemon, daemon.pidfile

# Get location to which PID files should be written
#from ..configuration import filesys_config
#
from .. import ROOTDIR
#print ROOTDIR
#ROOTDIR = filesys_config.config['rootdir']
#PIDFILEDIR = os.path.join(ROOTDIR, filesys_config.config['pidfiledir'])

#  ------  Class definitions ------

class daemonTemplate(object):
    def __init__(self, daemonname):
        """ Class template for configuring a daemon process. The goal is to use this template for
        all subprograms that will use a daemon process.

        Can subclass this template to add additional functionality if required, by redefining certain functions.

        Requires:
        daemonname :: str

        """
        self.daemonname = daemonname
        # Configure a logger.
        # Ensure that the name is a str (lots of test cases here - maybe not all of them are caught as it stands)
        assert type(daemonname) == str, "Given name is not a string"

        daemonname = daemonname if daemonname is not "" else "default"

        # create logging instance. If no handlers exist, before daemonisation, this automatically writes to stdout
        self.logger = logging.getLogger("daemon." + daemonname)

        # configure a daemon.TimeoutPIDLockFile. Note that the file isn't created until the daemon process is created,
        # and deletes it when process is killed
        self.pidf = daemon.pidfile.TimeoutPIDLockFile( os.path.join( PIDFILEDIR, daemonname + ".pid" ) )

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

    def run(self, function_to_run, *funargs, **daemoncontext_kwargs):
        self.logger.debug("Entered the run function. Configuring daemon context.")

        # check that the function to run in the daemon is actually a function.
        assert isinstance(function_to_run, (types.FunctionType, types.MethodType, types.BuiltinFunctionType, types.BuiltinMethodType)), \
                                            "The function given to run in the daemon does not appear to be a function."

        # remove signal map from kwargs as we'll define it later
        signal_map = daemoncontext_kwargs.pop('signal_map', None)

        signal_map = { signal.SIGTERM: self.daemon_terminate } if signal_map is None else signal_map

        # configure the daemon context
        context = daemon.DaemonContext( working_directory=".",
                                        umask=0o002, # sets permissions - we might want to change later
                                        stdout = sys.stdout,
                                        pidfile = self.pidf,
                                        files_preserve = [self.logger.parent.handlers[0].stream],
                                        signal_map = signal_map,
                                        **daemoncontext_kwargs )
                                        # Note that this last line is crucial to preserve the logging once the process is daemonised!
                                        # The .parent seems hackish and fragile, and should probably be changed later

        if self.ISRUNNING:

            pid = self.pidf.read_pid()
            sys.stdout.write("pid:{0}\n".format(pid))
            self.logger.debug("Not going to daemonise process... already running")
            return

        self.logger.debug("About to daemonise process...")

        with context:
            #print self.logger.parent.handlers
            pid = self.pidf.read_pid()
            self.logger.info( "Sucessfully daemonised. Running with PID {pid}\r".format(pid = pid) )

            # write PID to stdout so
            sys.stdout.write("pid:{0}\n".format(pid))
            #print "Running with PID {pid}\r".format(pid = self.pidf.read_pid())
            sys.stdout.flush()
            self.logger.debug( "cwd = {0}".format( os.getcwd() ) )
            # code to run goes here

            function_to_run(*funargs)

    def daemon_stop(self, signum, frame):
        #print "Stopped Daemon\n"
        self.logger.info( "Logging daemon stopped. Start up again by sending 'kill -19 {pid}' ".format(pid=self.pidf.read_pid()) )
        os.kill(self.pidf.read_pid(), signal.SIGSTOP) # SIGINT appears to handle closing of the pid file correctly

    def daemon_terminate(self, signum, frame):
        #print "Stopped Daemon\n"
        self.logger.info( "Logging daemon terminated" )
        os.kill(self.pidf.read_pid(), signal.SIGINT) # SIGINT appears to handle closing of the pid file correctly


# main script for testing purposes
if __name__ == '__main__':
    print "Running main..."
