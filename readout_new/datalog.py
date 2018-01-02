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
#   - Roach UDP network info. Note that Roach configuration is not done in here. However, opening the
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
# - Data wirting is impleented using the combination of getdata+dirfile libraries.
#   - Testing on a single Roach suggests that this works well for our needs, and it works with kst-plot out of the box
#   - Efficient data writing is achieved by implmented a simple dual-threaded producer-consumer architecture.
#
# - Communication to the daemon process is possible through use of pre-defined *nix signals.
#   - Start/Stop data saving on demand (signal.SIGUSR1)
#   - stop/kill the daemon process (with kill [PID] from command line, or os.kill(pid, signal.SIGTERM) from python.
#        - TODO get ctrl-c working (signal.SIGINT)
#        - implement signal.SIGINFO to log current status to logfile
#
# - Sweeping?

# - Possible extensions:
#   - include flag for each data point read from status.live file (maybe uneccessary)
#   - add FIFO functionality for more advanced communiation to the daemon (i.e. data sending)
#   - use 'runner' to get it to act like a service? maybe this isn't neccessary.


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

import os, sys, time, argparse, signal
import daemon, daemon.pidfile

# read in relevant config files
from .configuration import filesys_config, network_config

# read in pid file location from config file (default is var/run/roachreadout/)
pidfiledir = filesys_config.config['pidfiledir']
#if not os.path.exists(pidfiledir): os.mkdir(pidfiledir) - this check is done in the logging configuration, which
#                                                              is the first thing to be started


# Main class definition
class datalogDaemon(object):
    def __init__(self, roachid, savedir):

        self.roachid = roachid
        self.savedir = savedir

        # need a test/check to handle if the pid file is already locked?
        self.pidf = daemon.pidfile.TimeoutPIDLockFile( os.path.join( pidfiledir, 'roach{0:}.pid'.format(roachid) ) )

    def data_log(self, text):
        logname = find_logfile()
        while True:
            with open(logname, "w") as f:
                f.write("The time is now " + time.gmtime()+". Text string: " + str(text) + "\n")
            time.sleep(5)

    def write_log(self, text):
        logname = self.find_logfile()
        with open(logname, "a") as f:
            f.write(str(time.strftime("%Y%m%d_%H%M%S",time.gmtime()) + ': ' + text))
            f.write('\n')
            #f.close # does this work here?

    def run(self, text):
        context = daemon.DaemonContext(
                            working_directory=".",
                            umask=0o002,
                            stdout = sys.stdout,\
                            pidfile = self.pidf)

        context.signal_map = { \
                #signal.SIGHUP: self.daemon_stop,\
                signal.SIGTERM: self.daemon_stop\
                }

        with context:
            print "Running with PID {pid}\r".format(pid = self.pidf.read_pid())
            sys.stdout.flush()
            self.data_log(text)

    def daemon_stop(self, signum, frame):
        print "Stopped Daemon\n"
        logname = self.find_logfile()
        with open(logname, "a") as f:
            f.write("Logger stopped\r")
        os.kill(self.pidf.read_pid(), signal.SIGINT) # SIGINT appears to handle closing of the pid file correctly

    def find_logfile():
        # Define location/name of logfile here
        # One logfile per day (YYYYMMDD.log)
        # logname = "run/current_time.txt"
        logname = str(time.strftime("%Y%m%d",time.gmtime()) + '.log')
        return logname


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Example daemon in Python")
    parser.add_argument('text', help = "string for text to be printed")

    parser.add_argument('-p', '--pid-file', default='/var/run/eg_daemon.pid')
    parser.add_argument('-l', '--log-file', default='/var/log/eg_daemon.log')

    args = parser.parse_args()

    #start_daemon(pidf=args.pid_file, logf=args.log_file)

    d = datalogDaemon()
    d.run(args.text)
