#!/usr/bin/python
import time
import os

def init_log():
    # One logfile per day (YYYYMMDD.log)
    logname = str('/data/log/' + time.strftime("%Y%m%d",time.gmtime()) + '.log')
    # If it doesn't exist yet, create it
    if not os.path.isfile(logname):
        f = open(logname,'a')
        f.write(str(time.strftime("%Y%m%d_%H%M%S",time.gmtime()) + ': Started log file'))
        f.write('\n')
        f.close()
        
def write_log(message):
    logname = str('/data/log/' + time.strftime("%Y%m%d",time.gmtime()) + '.log')
    f = open(logname,'a')
    print(str(time.strftime("%Y%m%d_%H%M%S",time.gmtime()) + ': ' + message))
    f.write(str(time.strftime("%Y%m%d_%H%M%S",time.gmtime()) + ': ' + message))
    f.write('\n')
    f.close()
