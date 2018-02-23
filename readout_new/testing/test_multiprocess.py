#!/usr/bin/env python

# test of multiprocessing error observed with daemon code

#
# import subprocess, sys
# proc = subprocess.Popen("ping google.com",shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
# while proc.poll() is None:
#     try:
#         out = proc.stdout.readline()
#         sys.stdout.flush
#         print out
#     except KeyboardInterrupt:
#         proc.kill()
#

import os, time, select, sys
i=0


#print "Something to print"
sys.stdout.write("pid:{0}\n".format(os.getpid()))

while True:
    sys.stdout.write("info: iteration {0}\n".format(i))

    r, _, _ = select.select([sys.stdin], [], [], 0.1)

    #r = raw_input()
    if r:
        print r
        #print "exiting"
        out = r[0].readline()
        sys.stdout.write(out)
        sys.stdout.write("Exiting")
        break
    else:
        #print "continuing"
        sys.stdout.write("info: continuing")

    sys.stdout.flush()
    time.sleep(1)

# need a line termination for select to work!


# for i in range(10): # repeat several times to show that it works
#     print >>subp.stdin, i # write input
#     subp.stdin.flush() # not necessary in this case
#     print subp.stdout.readline(), # read output
#
#
# # while True:
# #     #print "iteration {0}".format(i)
# #     sys.stdout.write("iteration {0}\n".format(i))
# #
# #     rlist, _, _ = select.select([sys.stdin], [], [], 0.01)
# #
# #     if rlist:
# #         sys.stdout.write("message received")
# #         s = sys.stdin.readline()
# #         sys.stdout.write(s)
# #
# #         #print s
# #
# #     sys.stdout.flush()
# #
# #     i += 1
# #     time.sleep(1)
