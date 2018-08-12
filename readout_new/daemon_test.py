#!/usr/bin/env python

# code to test out the daemon running program using the templates.daemontemplate method
from .templates.daemontemplate import daemonTemplate, daemonControl
import os, sys, time, logging, signal, select, subprocess as _subprocess

daemonname = "daemontest"
testfile = "test.log"

class testdaemon(daemonControl):
    def __init__(self, daemonname):
        super(testdaemon, self).__init__(daemonname) # initalise the parent class

def function_to_run(startval):
    i = startval
    try:
        while True:
            with open(testfile, 'a') as fin:
                fin.write(time.strftime("%H%M%S") + "- iteration - {0}\n".format(i) )
                time.sleep(2)
                i+=1
    except KeyboardInterrupt:
        print "goodbye"
    finally:
        print fin # file should be closed as was opened with context manager


def start_daemontest():
    command_to_run = ["python" , "-m", "readout_new.daemon_test"]
    subp = _subprocess.Popen(command_to_run, stdout = sys.stdout)

    time.sleep(1) # wait a second for process to be generated
    # open the fifo_fd
    return testdaemon(daemonname)

#         #    logging.basicConfig(level = loglevel)

if __name__ =="__main__":

    d = daemonTemplate(daemonname, loglevel = logging.DEBUG)
    d.run( function_to_run , 2, stdout = sys.stdout, stderr = sys.stdout )




#
