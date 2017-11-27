#!/usr/bin/env python

# code to be run as a python-daemon in the background and be used to collect UDP packets
# and save to disk. Ideally with flag for each data point read from status.live file.

# 20171126 - get basic framework up and running
# current status: some hack-type code to get basic daemon code together.
# - cd into the readout_new directory - we can now run 'python datalog.py [teststring]' from command line,
# (the requirement of being in readout_new will obviously change later on). Teststring is any string to test out commandline argparser.
# can run - "tail -f run/current_time.txt" will show the test file updating in real time
# - kill with kill [PID] from command line, or os.kill(pid, signal.SIGTERM) from python
# - multiple instances can be run in parallel (currently, run, change the hardcoded pid file manually, save and rerun to get second instance)

# TODO
# read in command line arugments
#   - udpip, local ip, roachid
# set up socket to udp and use select.select to monitor network interface
# save file
# from inialise.py spawn this program with subprocess.Popen() with command line arguments
# exception handling at the moment is apparently silent... not good!
# no exception raised if pidfile is locked - therefore check for lock before running
# no exceptions raised when there is an error in the code
# try to use runner to get it to act like a service? maybe this isn't neccessary.

import daemon, daemon.pidfile
import time
import sys
import argparse
import signal
import os

class datalogDaemon(object):
    def __init__(self):
        self.pidf = daemon.pidfile.TimeoutPIDLockFile("run/mydaemon1.pid") # this will have to modified when running multiple instances

    def data_log(self, text):
        while True:
            with open("run/current_time1.txt", "w") as f:
                f.write("The time is now " + time.ctime()+". Text string: " + str(text) + "\n")
            time.sleep(5)
            #print "The time is now " + time.ctime()+"\n"

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
            print "Running with PID {pid}\n".format(pid = self.pidf.read_pid())
            sys.stdout.flush()
            self.data_log(text)

    def daemon_stop(self, signum, frame):
        print "Stopped Daemon\n"
        with open("run/current_time1.txt", "w") as f:
            f.write("Logger stopped\r\n")
        os.kill(self.pidf.read_pid(), signal.SIGINT) # SIGINT appears to handle closing of the pid file correctly


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Example daemon in Python")
    parser.add_argument('text', help = "string for text to be printed")

    parser.add_argument('-p', '--pid-file', default='/var/run/eg_daemon.pid')
    parser.add_argument('-l', '--log-file', default='/var/log/eg_daemon.log')

    args = parser.parse_args()

    #start_daemon(pidf=args.pid_file, logf=args.log_file)

    d = datalogDaemon()
    d.run(args.text)
