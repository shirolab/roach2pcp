#!/usr/bin/env python

# main script used to provide a textual ui?

# this is the main script, that handles any requests from the lmt interface, or from the ui, depending on which is chosen.
# This will be fairly similar to that of the current software layout, which works quite nicely - but will take some thought
# to make it compatible with multiple roaches simulataneously


# write a class that contains the daemon information?

# https://stackoverflow.com/questions/16768290/understanding-popen-communicate?noredirect=1&lq=1


# information to pass from

SCRIPT_PATH = "test_multiprocess.py"

import os, sys, subprocess, signal, select
class roachinterface(object):
    """
    Test class for what will eventually become the roach interface object.

    First test case is to open a test daemon, get the pid, and provide methods to iteract with the process

    """
    def __init__(self, roachid):
        self.roachid = roachid
        return

    def daemon_start(self, roachid):
        """
        Function to run the script that spawns a new daemon process.

        TODO
            - check whether a roach is already running?
            - get pid of new daemon processes
            - write methods to interact to kill, pause, start and stop data saving (based on unix signals)
            -

        Parameters
        ----------
        roachid : str
            Roach ID string. Must match an entry contained in the configuration file, and will be used
            to match all other configurations (e.g. data saving locations..etc.)

        Returns
        -------

        Examples
        --------

        """
        proc = subprocess.Popen([sys.executable, "-u", SCRIPT_PATH], \
                                    stdout = subprocess.PIPE, stdin=subprocess.PIPE)

        # read get pid from output
        line = proc.stdout.readline()
        print line
        self.proc = proc
        self.pid = int(line.split(":")[-1])

    def daemon_kill(self):
        os.kill(self.pid, signal.SIGTERM)
        # kill subprocess

    def daemon_read_output(self):
        try:
            while True:
                x=1
        except KeyboardInterrupt:
            return
