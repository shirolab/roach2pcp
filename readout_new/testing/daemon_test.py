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
# read in command line arugments to remove hard coded filenames and generalise
# intended command line arguments required would be
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
import threading, multiprocessing, select

class datalogDaemon(object):
    def __init__(self):
        # need a test/check to handle if the pid file is locked
        self.cwd = os.getcwd()
        pidfpath = os.path.join(self.cwd,"run/mydaemon.pid")
        self.pidf = daemon.pidfile.TimeoutPIDLockFile(pidfpath) # this will have to modified when running multiple instances

        #self.livefile = "run/.lftest.live"
        #os.mkfifo(self.fin) if not os.path.exists(self.fifo) else None

        self.logname = self.find_logfile()
        print self.logname
        self.RUNNING = 1

    def data_log(self, text):
        with open(self.logname, "a") as f:
            print "file opened"
            while True:
                timeout=0.1
                rlist, _, _ = select.select([sys.stdin], [], [], timeout)
                if rlist:
                    s = sys.stdin.readline()
                    print s
                else:
                    print "No input. Moving on..."

                if self.RUNNING==1:
                    f.write("The time is now " + time.strftime("%H:%M:%S", time.gmtime() ) + \
                    ". Text string: " + str(text) + "\n")
                    f.flush()
                else:
                    f.write("Logger currently paused...\r\n")
                    f.flush()
                time.sleep(5)

    def _run(self, text):
        #print sys.stdin
        #sys.stdin = open('/dev/tty') # this is a hack and probably not required...
        #print sys.stdin
        context = daemon.DaemonContext(
                            pidfile = self.pidf,
                            umask=0o002,
                            working_directory=".",
                            stdout = sys.stdout,
                            stdin = sys.stdin)


        context.signal_map = { \
                #signal.SIGHUP: self.daemon_stop,\
                #signal.INFO: self.daemon_stop,\    # implement to write current status to file (packet count, running/paused...etc)
                signal.SIGTERM: self.daemon_stop,\
                signal.SIGUSR1: self.daemon_pause,\
                signal.SIGCONT: self.daemon_resume
                }
        print "INFO: about to daemonise"
        with context:
            self.pid = self.pidf.read_pid()
            print "Running with PID {pid}\r".format(pid = self.pid)

            #with open(self.livefile, "w") as fin:
            #    fin.write("pid={pid}".format(pid = self.pid)) # add other stuff here for convenience

            sys.stdout.flush()

            self.data_log(text)

    def daemon_run(self, text):
        # thrd = threading.Thread(name = 'daemonthread', target = self._run, args = (text) )
        # thrd = threading.Thread(target = self._run, args = (text,))
        #
        # thrd.setDaemon(True)
        # thrd.start()

        self.prcs = multiprocessing.Process(target = self._run, args = (text,))
        #prcs = multiprocessing.Process(target = self.find_logfile)

        #self.prcs.daemon=True
        #self.prcs.start()
        #import subprocess
        #self.subprcs = subprocess.Popen([sys.executable, "daemon_test.py", text])

        #return

    def daemon_resume(self, signum, frame):
        print "Resumed!!!\n"
        with open(self.logname, "a") as f:
            f.write("Logger resumed from continued\r\n")
            f.flush()

    def daemon_stop(self, signum, frame):
        print "Stopped Daemon\n"
        with open(self.logname, "a") as f:
            f.write("Logger stopped\r\n")
            f.flush()

        os.kill(self.pidf.read_pid(), signal.SIGINT) # SIGINT appears to handle closing of the pid file correctly

    def daemon_pause(self, signum, frame):
        if self.RUNNING==1:
            with open(self.logname, "a") as f:
                f.write("Logger paused\r\n")
                f.flush()
                self.RUNNING = 0
        elif self.RUNNING==0:
            with open(self.logname, "a") as f:
                f.write("Logger resumed\r\n")
                f.flush()
                self.RUNNING = 1

        #os.kill(self.pidf.read_pid(), signal.SIGSTOP)

        return None

    def find_logfile(self):
        # Define location/name of logfile here
        # One logfile per day (YYYYMMDD.log)
        # logname = "run/current_time.txt"
        logname = str(time.strftime("%Y%m%d",time.gmtime()) + '.log')
        print "finding logfile"
        return os.path.join(self.cwd, "run", logname)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Example daemon in Python")
    parser.add_argument('text', help = "string for text to be printed")

    # parser.add_argument('-p', '--pid-file', default='/var/run/eg_daemon.pid')
    # parser.add_argument('-l', '--log-file', default='/var/log/eg_daemon.log')

    args = parser.parse_args()

    #start_daemon(pidf=args.pid_file, logf=args.log_file)

    d = datalogDaemon()
    print "Instatiated correctly"
    print args.text
    time.sleep(1)
    d._run(args.text)
    print "finished"


# could write to a file, or fifo, which is then picked up with a parent class
# containing the PID, and methods to kill, pause...etc the daemon
# start with
        #self.subprcs = subprocess.Popen([sys.executable, "daemon_test.py", text])

# how to get this running properly
#this will be run as a script,
#- ideally want to


# use subprocess.communicate to communicate using stdout
# i.e. write pid to stdout on initialise, then read as appropriate
