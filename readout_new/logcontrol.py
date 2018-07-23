#!/usr/bin/env python
# 20180510 - PB


# start logging daemon process
#subp = subprocess.Popen(["python" , "-m", "readout_new.logfile.logdaemon"], cwd = r"/Users/PeteBarry/Documents/analysiscode/multitone/")
#subp.communicate() # kills zombie process left behind

# return a handle to the logger?

# turn into a class, or module?
# include the configure_sockethandler function here, to return a new logging instance as required

#https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output

import os as _os, signal as _signal, select as _select, subprocess as _subprocess

INFO = {}

def start_logging_daemon():
    global INFO

    # runs the script that starts the logging daemon
    subp = _subprocess.Popen(["python" , "-m", "readout_new.logdaemon"], \
                                cwd    = r".",\
                                stdout = _subprocess.PIPE)
    # subp = _subprocess.Popen(["python" , "readout_new/logfile/logdaemon.py"], \
    #                             cwd    = r"/Users/PeteBarry/Documents/analysiscode/multitone/",\
    #                             stdout = _subprocess.PIPE)
    # read startup information from logger
    info = []

    while True:
        r, _, _ = _select.select([subp.stdout], [], [], 1)
        if r:
            line = r[0].readline()
            if line:
                info.append(line)
            else:
                break
        else:
            break

    subp.poll() # kills zombie process left behind
    INFO = [item for item in info]

    INFO = {item.split(':')[0] : item.split(':')[1] for item in info}

def stop_logging_daemon(pid = None):
    global INFO
    _os.kill(int(INFO['pid']), _signal.SIGTERM)


# test this code to extract INFO to pass to stop_loggin_daemon


# def start_logging_daemon():
#     global INFO
#
#     # read startup information from logger
#     info = []
#     while True:
#         r, _, _ = _select.select([subp.stdout], [], [], 1)
#         if r:
#             info.append(r[0].readline())
#         else:
#             break
#
#     subp.poll() # kills zombie process left behind
#
#     INFO = {item.split(':')[0] : item.split(':')[1] for item in info}
#
