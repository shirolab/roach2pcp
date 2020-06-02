# Set of high-level functions that will be used to control a roach container interface

import time
def create_new_dirfile(roachcontainer):
    pass
    #return roachcontainer.dirfilename

def lo_sweep_single(roachcontainer, tag = "cal"):
    """Given a roach """

    # set the datatag
    datatag = "_losweep"

    # initial checks
    # assert type(roachcontainer) == roachContainer

    # check that daemonwriter is not currently writing, return if not as something has probably gone wrong
    # assert roachcontainer.writer_daemon.isrunning() == False, return

    # check if current sweepdirfile exists (there should be a function that create a new file )
    # if it does, get the filename and append unique id (_#)

    # get list of LO frequencies for sweeping
    # roachcontainer.losweep_freqs # this is calculated from the LO freq, +/- sweep bandwidths

    # set dirfile for writer
    # roachcontainer.set_new_file()

    # start_writer
    # roachcontainer.start_writing()

    # loop over LO frequencies, while saving time at lo_step
    # step_times = []
    # # get time for avg factor
    # sleeptime = (roachcontainer.losweep_avgs / roachcontainer.fpga.sample_rate) * 1.05 # num avgs / sample_rate + 5%
    # for lofreq in roachcontainer.losweep_freqs:
    #     roachcontainer.synth.set_freq(lofreq)
    #     step_times.append( time.time() )
    #     time.sleep(sleeptime)

    # now sweep has finished, create the derived sweep file and save to the current dirfile

def reduce_and_make_sweep_file(roachcontainer):
    pass
