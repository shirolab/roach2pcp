#!/usr/bin/env python
# 20171230 - PB

# Code to be run as a python-daemon in the background and be used to collect UDP packets
# and save to disk. Philosophy is to keep this simple as possible!


# ----- Running changlog (during development) -----
# 20171230 - basic daemon framework up and running. Code moved into /testing.


# ----- Basic functionality of program -----

# - This file will essentially be an executable, standalone, script that will take a number of command line arguments
# and spawn a dameon process whose sole job is to read Roach2 data packets from a specified network interface
# and write the contents to disk.

# - Command line arguments required are as follows:
#   - Directory to save data files
#        - data filenames are to be finalised upon, but yyyymmdd_hhmmss_obs_*num* seems sensible
#        - new file is created whenever logger is restarted
#   - Roach UDP network info - read from configuration file. Note that Roach configuration is not done in here. However, opening the
# socket and binding could be done here?
#       - udp_src_ip, udp_dest_ip/ethXXX, buffer_len/packet size,
#    - RoachID - a unique idenitifer (uuid) used to distinguish a particular roach connection
#        - this will identify the pid file, allowing the main script to access pid of each daemon
#
# - Logging is implemented using the Python logging module. As this script is primarily intended to be called from a
# main script (for multiple roach boards), the logname is taken from the RoachID.
#
# - Network configuration is handled using the socket and select modules, and is largely taken from Sam Gordon's original code.
#   - select.select is used to monitor the port until data is present
#
# - Data wirting is implemented using the combination of getdata+dirfile libraries.
#   - Testing on a single Roach suggests that this works well for our needs, and it works with kst-plot out of the box
#   - Efficient data writing is achieved by implmented a simple dual-threaded producer-consumer architecture.
#
# - Communication to the daemon process is possible through use of pre-defined *nix signals.
#   - Start/Stop data saving on demand (signal.SIGCONT)
#        - SIGCONT (kill -17) will start a new file
#   - stop/kill the daemon process (with kill [PID] from command line, or os.kill(pid, signal.SIGTERM) from python.
#        - TODO get ctrl-c working (signal.SIGINT)
#        - implement signal.SIGINFO to log current status to logfile
#
# - Sweeping?

# - Possible extensions:
#   - include flag for each data point read from status.live file (maybe uneccessary)
#   - add FIFO functionality for more advanced communiation to the daemon (i.e. data sending)
#   - use 'runner' to get it to act like a service? maybe this isn't neccessary.
#   - define the class in such a way as to keep an object that has methods to call, kill the process

# TODO
# read in command line arugments as above. Currently, the expected arguments are a file directory for data saving,
# and a roach uuid. This uuid should be the same as given in the configuraiton file.

#
# as above intended command line arguments required would be
#   - udpip, local ip, roachid
# set up socket to udp and use select.select to monitor network interface
# save file
# from inialise.py spawn this program with subprocess.Popen() with command line arguments
# exception handling at the moment is apparently silent... not good!
# no exception raised if pidfile is locked - therefore check for lock before running
# no exceptions raised when there is an error in the code

# -- pseudocode --
# initialise from configuration files
# set up process-id lockfile
# configure threading for producer consumer loop
# dirfile generation - when to do this?
#   - this should be handled with the start/stop of data saving
# start/stop data saving

import os, sys, time, argparse, signal, threading   # import stdlibs
import numpy as np
from collections import deque                       # fast queue for passing data between two threads
import daemon, daemon.pidfile                       # python-daemon module for creating well behaved daemon process
import pygetdata                                    # getdata/dirfile module

# read in relevant config files
from ..configuration import general_config, filesys_config, network_config

# get pid file location from config file (default is /var/run/roachreadout/)
PIDFILEDIR = filesys_config.config['pidfiledir']
assert os.path.exists(PIDFILEDIR) # paranoia check, probably not required

SAVEDATADIR = filesys_config.config['savedatadir']
assert os.path.exists(SAVEDATADIR) # paranoia check, probably not required

NTONES = general_config.config['ntones']

# --------------------- Main class definition of datalogger ---------------------

class datalogDaemon(object):
    def __init__(self, roachid):
        """
        datalogDaemon(roachid)

        Main datalog daemon for the Roach2 KID readout system.

        Parameters
        ----------
        roachid  :  str
            A (unique) string that identifies an individual Roach board. This value should be contained in
            the 'network_config.yml' configuration file and will point to the various network config details required
            to configure the Roach readout. A check is done to ensure this is the case, returning an error if it fails.

        Returns
        -------

        Example
        --------

        """

        self.roachid = roachid

        # check that the given rochid matches the configuration file
        try:
            assert roachid in network_config.config.keys()
        except AssertionError:
            print "roachid not matched to entry in configuration file" # TODO print this to log in debug

        # configure logger with roachid as name

        # need a test/check to handle if the pid file is already locked?
        self.pidf = daemon.pidfile.TimeoutPIDLockFile( os.path.join( PIDFILEDIR, 'roach{0:}.pid'.format(roachid) ) )
        self._check_pidfile()

        # configure the multi-threading for data Saving
        self.threadqueue = deque()
        self.filewritethread = threading.Thread(name = 'writer_thread', target = self.append_to_dirfile )
        self.filewritethread.setDaemon(True) # setting daemon here ensures that the child thread ends with the main thread

        # dirfile generation? need to create format file
        self.dirfilehandle = self.gen_dirfilehandle()

    def _check_pidfile(self):

        if self.pidf.is_locked() and not self.pidf.i_am_locking():
            # then the file is locked by another process - most likely an error from previous processes
            # send warning to log, and break the lock
            self.logger.warning("Logging p-id file was locked by another process")
            self.pidf.break_lock()
            self.logger.debug("broke existing lock")
            self.pidf.acquire()
            self.logger.debug( "Lock transferred and is being held by me: {0}".format(self.pidf.i_am_locking()) )
        else:
            return

    def _daemon_exit(self, signum, frame):
        """Function called when the daemon receives signal.SIGTERM
        """
        self.logger.warning("Roach daemon (id:{0:}) exited cleanly.".format(roachid) )
        os.kill(self.pidf.read_pid(), signal.SIGINT) # SIGINT appears to handle closing of the pid file correctly

    def _daemon_stop(self, signum, frame):
        """Function called when the daemon receives signal.SIGSTOP
        """
        self.logger.warning("Roach daemon (id:{0:}) exited cleanly.".format(roachid) )
        os.kill(self.pidf.read_pid(), signal.SIGSTOP) # SIGINT appears to handle closing of the pid file correctly

    def _daemon_handle_signal(self, signum, frame):
        """Function called when the daemon receives signal.SIGSTOP
        """
        if signum == signal.SIGINT:
            self.logger.warning("Roach daemon (id:{0:}) exited cleanly.".format(roachid) )
        elif signum == signal.SIGSTOP:
            self.logger.warning("Roach daemon stopped cleanly.".format(roachid) )
        elif signum == signal.SIGCONT:
            self.logger.warning("Roach daemon resumed cleanly.".format(roachid) )

        os.kill(self.pidf.read_pid(), signum)

    def _daemon_start(self, text):
        context = daemon.DaemonContext(
                            working_directory=".", # change this?
                            umask=0o002,
                            stdout = sys.stdout,\
                            pidfile = self.pidf,
                            files_preserve = [self.logger.parent.handlers[0].stream] )
                            # Note that this is crucial to preserve the logging once the process is daemonised!
                            # The .parent seems hackish and not robust, and should probably be changed later
        context.signal_map = { \
                #signal.SIGHUP: self.daemon_stop,\
                signal.SIGTERM: self.daemon_exit\
                }
        # The process becomes daemonised when this is run, and so the main function is located here
        with context:
            print "Running with PID {pid}\r".format(pid = self.pidf.read_pid())

            self.log_data(text)

    def log_data(self):
        """ The main function that is run during the
        """
        while True:

    def gen_dirfilehandle(self, *dirfileflags):
        """ Function to generate new dirfile with name , and return a handle to the new file.
        """
        # check to see if current handle is a valid open file, and close as appropriate
        # TODO read from stdin to get a filename ID to add to
        # test encodings to see if the data size can be reduced significantly

        # create new file as appropriate, with file name format as YYYYMMDD_HHMMSS_OBS (can be redefined if required)

        dirfilename = os.path.join(SAVEDATADIR, time.strftime("%Y%m%d-%H%M%S") + "OBS" )

        dirfileflagint = np.bitwise_or.reduce(dirfileflags) if dirfileflags \
                                                            else gd.CREAT|gd.RDWR|gd.UNENCODED|gd.EXCL
        try:
            dirfilehandle = gd.dirfile( dirfilename, dirfileflagint )
            return dirfilehandle

        except gd.ExistsError:
            print "Dirfile exists somehow. We can deal with this later. For now returning None."
            return None

    def gen_formatfile(self):
        """ create a dirfile and populate the format file """

        #TODO  include dervied fields, constants, sweeps, metadata...etc
        dirfilehandle = self.dirfilehandle if hasattr(self.dirfilehandle, "name") else self.gen_dirfilehandle()

        dirfilehandle.add_spec('ctime' +  ' RAW FLOAT64 1')     # add fields (can use either add_spec or add)

        kidlist = ["KID{kidnum:04d} RAW COMPLEX128 1".format(kidnum=i) for i in range(NTONES)]
        l = map(dirf.add_spec, kidlist)














if __name__ == "__main__":
    # this script is designed to be called from a high-level caller script, and
    # so won't be run as "__main__". Therefore, this is for testing only.


    # Build up testing

    # -x mimic roach2 packets by creating a separate script that sends packets to localhost
    # -x in the configuration file, should be able to just add this as roachid1 and it should work as expected
    # -x set up logging and write various files to log file
    # -x write data to file
    # -
    # network config.
    #    roachudp is sending packets (to where?)

    parser = argparse.ArgumentParser(description="Example daemon in Python")
    parser.add_argument('text', help = "string for text to be printed")

    parser.add_argument('-p', '--pid-file', default='/var/run/eg_daemon.pid')
    parser.add_argument('-l', '--log-file', default='/var/log/eg_daemon.log')

    args = parser.parse_args()

    #start_daemon(pidf=args.pid_file, logf=args.log_file)

    d = datalogDaemon()
    d.run(args.text)
