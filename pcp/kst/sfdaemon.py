# Simple daemon to continually search for new dirfiles
# and write their names to a 'source file'
# which can then be read by kst.  This takes care
# of auto-updating plots

import daemon
import os
import time

def write_dirfilename():
    while True:
        cmd = 'ls -1d /data/dirfiles/roach0/20??????_?????? > /home/superspec/Documents/ksk/multitone_20190419/pcp/kst/roach0_sf.txt'
        os.system(cmd)
        time.sleep(5)

def run():
    with daemon.DaemonContext():
        write_dirfilename()

if __name__ == "__main__":
    run()
