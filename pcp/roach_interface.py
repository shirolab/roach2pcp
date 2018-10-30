#!/usr/bin/env python

# holds the code for the Roach interface class.

# Each ri will have the following data
#       - fpga (as before, class defined in capserfpga)
#       - synth - generic object that will control the various synths
#            - in an attempt to handle Nroaches != Nsynths, each roach defined in network_config
#            will have a synthid entry, that matches one of the synth entries in hardware_config.
#            Upon initialisation, each synth is initialised into a synth object, which is then
#            passed to the corresponding roach interface. This way, multiple roaches can reference
#            the same synth. When multiple roaches use the same synth, care needs to be taken when
#            manipulating synths in parallel, but this should be an easy check of the ri.synth.synthid
#       - daemon tracker - associated information regarding the daemon packet receiving daemonself.
#           - this should have a live status update of whether saving is on/off...etc

import os, sys, time, numpy as np

try:
    import casperfpga
except ImportError:
    print "can't find casperfpga module - limited functionality available"
    casperfpga = None
    pass

from .configuration import ROOTDIR, filesys_config, roach_config, network_config, hardware_config, general_config

# import the synth dictionary from
from .synthesizer import SYNTH_HW_DICT as _SYNTH_HW_DICT # note that we might need to e careful of import order here

import datalog_mp

from .lib.lib_hardware import initialise_connected_synths as _initialise_connected_synths
SYNTHS_IN_USE = _initialise_connected_synths()

class roachInterface(object):
    def __init__(self, roachid):

        self.roachid  = roachid

        self.fpga            = None
        self.tonelist        = None
        self.writer_daemon   = None
        self.synth_lo        = None
        self.synth_clk       = None
        self.input_atten     = None
        self.output_atten    = None

        # get configuration for specific roach
        self.ROACH_CFG = roach_config['roach_params'][roachid]
        # check configurations are all appropriate (this should be done in configuration __init__ )

        # generate directory path for data saving
        self.save_data_dir  = os.path.join(ROOTDIR, filesys_config['savedatadir'], roachid)
        # create if doesn't exist already
        os.makedirs(self.save_data_dir) if not os.path.exists(self.save_data_dir) else None

        # initialise all the hardware and return objects
        self.initialse_hardware()
        self._initialise_daemon_writer(roachid)

    def _initialise_daemon_writer(self, roachid):
        self.writer_daemon = datalog_mp.dataLogger(roachid)
        self.writer_daemon.start_daemon()

    def initialse_hardware(self):
        # initialise all the hardware
        self.fpga = self._initialise_fpga(self.roachid)

        self._initialise_synth_clk(self.roachid)
        self._initialise_synth_lo(self.roachid)

        #self._initialise_gbe(self.roachid)

    def _initialise_fpga(self, roachid):
        if casperfpga is None:
            print "casperfpga module not loaded. No active FPGA instance"
            return
        try:
            return casperfpga.katcp_fpga.KatcpFpga(ppc_ipaddr, timeout = 120.)
        except RuntimeError:
            # bad things have happened, and nothing else should proceed
            return

    def _initialise_synth_lo(self, roachid):
        # get configuration
        synthid_lo = self.ROACH_CFG["synthid_lo"]

        try:
            self.synth_lo = SYNTHS_IN_USE[synthid_lo].synthobj()
        except KeyError:
            print "synthid not recognised. Check configuration file"

    def _initialise_synth_clk(self, roachid):

        synthid_clk = self.ROACH_CFG["synthid_clk"]

        if synthid_clk is not None:
            # get the dictionary of live synths and initialise
            self.synth_clk = SYNTHS_IN_USE[synthid_clk]
            pass
        else:
            self.synth_clk = None

    def _initialise_attenuation(self, roachid):
        # get configuration for attenuators for roachid
        pass

    def sweep_lo(self, **sweep_kwargs):
        """
        Function to sweep the LO. Takes in a number of optional keyword arugments. If not given,
        defaults from the configuration files are assumed.

        Keyword Arguments
        -----------------

        sweep_span : float
            Frequency span in Hz about which to sweep the LO around its currently set value.

        sweep_step : float
            Frequency step in Hz in which to sweep the LO around its currently set value. Note that some
            synthesiers have a minimum step size. Every attempt has been made to try to make the user know
            if the hardware is limiting the step, but care should still be taken.

        sweep_avgs : float
            Number of packets to average per LO frequency. This is used to calculate an approximate integration
            time to collect sweep_avgs. There is a 5% time addition to ensure that at least this many packets are
            collected.

        save_data : bool
            Flag to turn off data writing. Mainly for testing purposes. Default is, of course, True.

        # TODO:
            - implement a method to determine if packets are being captured correctly?

        """
        valid_kwargs = ["sweep_span", "sweep_step", "sweep_avgs", "save_data"]
        # parse the keyword arguments
        sweep_span = np.float32( sweep_kwargs.pop("sweep_span", self.ROACH_CFG["sweep_span"]) )
        sweep_step = np.float32( sweep_kwargs.pop("sweep_step", self.ROACH_CFG["sweep_step"]) )
        sweep_avgs = np.int32  ( sweep_kwargs.pop("sweep_avgs", self.ROACH_CFG["sweep_avgs"]) )

        save_data = sweep_kwargs.pop("save_data", True)

        if sweep_kwargs.keys():
            print "Error: Optional argument(s) {0} not processed. Valid kwargs are {1}. Sweep not completed."\
            .format(sweep_kwargs.keys(), valid_kwargs)
            return

        # check that daemonwriter is not currently writing, return if not as something has probably gone wrong
        if self.writer_daemon.is_writing == True:
            print "Writer is already running. Aborting sweep. Stop current file and retry."
            return

        # perform a quick check that packets are being streamed to the roach

        # get list of LO frequencies for sweeping
        # roachcontainer.losweep_freqs # this is calculated from the LO freq, sweep bandwidths
        sweep_freqs = np.arange(self.synth_lo.frequency - sweep_span/2., \
                                self.synth_lo.frequency + sweep_span/2., \
                                sweep_step,\
                                dtype = np.float32)

        # create new dirfile and set it as the active file. Note that data writing is off by default.
        self.writer_daemon.set_active_dirfile(datatag = "sweep")
        self.current_dirfile = self.writer_daemon.current_dirfile

        # set up sweep timing parameters
        step_times = []
        # # get time for avg factor
        sleeptime = np.round( sweep_avgs / 488. * 1.05, decimals = 3 )#self.fpga.sample_rate) * 1.05 # num avgs / sample_rate + 5%
        print "sleep time for sweep is {0}".format(sleeptime)

        # start writing data to file
        print "starting to write data"
        self.writer_daemon.start_writing()

        # loop over LO frequencies, while saving time at lo_step
        try:
            for lofreq in sweep_freqs:
                self.synth_lo.frequency = lofreq
                step_times.append( time.time() )
                time.sleep(sleeptime)
        except KeyboardInterrupt:
            pass

        self.writer_daemon.pause_writing()

        return np.array(step_times, dtype = np.float64)

        # close dirfile to prevent further writing

        # now sweep has finished, create the derived sweep file and save to the current dirfile (from lib_dirfiles)

            # stop file write
            # get dirfilehandle
            # align LO steps with python timestreams
            # read in IQ data and split up according to LO steps
            # discard first Npoints (user definable)
            # average together to get f, I, Q
            # save as a new file in the dirfile
            # add to format file
            # retain reference to dirfile here
            # link to visualisation.py for plotting (or scraps)

    def shutdown():
        pass



# This script is the first code to be run after all hardware in connected and switched on


# We could write a small helper script to check things are connected would be useful for initial configuration testing
#   - check dnsmasq is running
#   - check roach(s) are connected
#

# the goal of this is to read information from a set of configuration files that contain all the
# neccessary information regarding Roaches/synths/ip addresses/ports...etc.

# Read from YAML/JSON for configuration file handling http://camel.readthedocs.io/en/latest/yamlref.html

# - instantiate a roach interface class (similar to SG original code) for each available Roach board.
# Each roach interface class should have the following information:
#   - upon init: roach fpga ip, roach ppc ip, local port ip, fpga instance, individual roach parameters( dds_shift, sample rate, accum_len)
# synthesiser handle (which should be a sub-class), attenuators (again, subclass)
#   - configuration of logging files. Have log file for each Roach independently, or all in one? (doesn't really matter,
# we can pass the log file handle to each roach instance)
#  - spawn a datalog.py instance for each Roach
# - This should then return a list of the roach interface objects, with everything initalised and running, to be used
# for subsequent tasks (e.g. biasing, streaming...etc)


# logging
