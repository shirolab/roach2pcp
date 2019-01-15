#!/usr/bin/env python

# holds the code for the muxChannel class, an object that will contain all of the functionality to
# control a single roach and associated hardware (synth, attenuator...etc)

# Each mc will have the following data
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

import atexit

import pygetdata as _gd

try:
    import casperfpga
except ImportError:
    print "can't find casperfpga module - limited functionality available"
    casperfpga = None
    pass

from .configuration import ROOTDIR, filesys_config, roach_config, network_config, hardware_config, general_config

# import the synth dictionary from
from .synthesizer import SYNTH_HW_DICT as _SYNTH_HW_DICT # note that we might need to e careful of import order here
from . import toneslist
from . import datalog_mp

from .lib import lib_dirfiles as _lib_dirfiles, lib_fpga as _lib_fpga

from .lib.lib_hardware import initialise_connected_synths as _initialise_connected_synths
SYNTHS_IN_USE = _initialise_connected_synths()

class newTonelist (toneslist.Toneslist):
    def __init__(self, roachid, loader_function):
        super(newTonelist, self).__init__(roachid, loader_function)

class muxChannel(object):
    def __init__(self, roachid):

        atexit.register(self.shutdown)

        self.roachid  = roachid

        self.fpga            = _lib_fpga.get_fpga_instance(roachid)
        self.roach_iface     = _lib_fpga.roachInterface(self.fpga, roachid)
        self.tonelist        = None
        self.writer_daemon   = None
        self.synth_lo        = None
        self.synth_clk       = None
        self.input_atten     = None
        self.output_atten    = None

        self.current_dirfile       = None
        self.current_sweep_dirfile = None

        # get configuration for specific roach
        self.ROACH_CFG = roach_config['roach_params'][self.roachid]
        # check configurations are all appropriate (this should be done in configuration __init__ )

        # generate directory path for data saving
        self.save_data_dir  = os.path.join(ROOTDIR, filesys_config['savedatadir'], self.roachid)
        # create if doesn't exist already
        os.makedirs(self.save_data_dir) if not os.path.exists(self.save_data_dir) else None

        # initialise all the hardware and return objects

        self._initialise_daemon_writer()
        #self.initialse_hardware()

################################################################################
################################################################################
    def _decorate_tonelist_loader(self, original_loader_function):
        def load_and_update_datapacket_dict(*args, **kwargs):
            original_loader_function(*args, **kwargs)
            self._refresh_datapacket_dict()
        return load_and_update_datapacket_dict

    def _refresh_datapacket_dict(self):
        print "i did something else in a new function"
        # this function is run when a new toneslist is loaded
        # check writer_daemon is running correctly

        # refresh datapacket_dict
        self.writer_daemon.reinitialise_datapacket_dict( self.toneslist )

    def _initialise_daemon_writer(self):
        self.writer_daemon = datalog_mp.dataLogger(self.roachid)
        self.writer_daemon.start_daemon()

    def initialse_hardware(self):
        # initialise the synthesisers
        self._initialise_synth_clk()
        self._initialise_synth_lo()

    def _initialise_synth_lo(self):
        # get configuration
        synthid_lo = self.ROACH_CFG["synthid_lo"]

        try:
            self.synth_lo = SYNTHS_IN_USE[synthid_lo].synthobj
        except KeyError:
            print "synthid not recognised. Check configuration file"

    def _initialise_synth_clk(self):

        synthid_clk = self.ROACH_CFG["synthid_clk"]

        if synthid_clk is not None:
            # get the dictionary of live synths and initialise
            self.synth_clk = SYNTHS_IN_USE[synthid_clk].synthobj
            #set the clk frequency
            self.synth_clk.clk_or_lo = 'clk'
            self.synth_clk.frequency = 512.0e6

        else:
            self.synth_clk = None

    def _initialise_attenuation(self):
        # get configuration for attenuators for self.roachid
        pass


    def set_active_dirfile(new_dirfile = ""):
        # if an empty string is given (default), then we pass the DIRFILE_SAVEDIR as the filename to lib_dirfile.create_dirfile,
        # which generates a new filename with the filename format given general_config['default_datafilename_format']).
        # This is likely to be the most used case
        new_dirfile = self.DIRFILE_SAVEDIR if not new_dirfile else new_dirfile

        # store last open filename for convenience
        self._last_closed_dirfile  = self.current_dirfile
        self._last_closed_filename = self.current_filename

        # check type of new_dirfile
        if type(new_dirfile) == _gd.dirfile:
            print "dirfile file handle given. Nothing done"
            pass # unnecessary, but just to be explicit

        elif type(new_dirfile) == str: #and not os.path.exists(new_dirfile):
            # create new dirfile with max tones assuming newdirfile is a path. lib_dirfiles.create_dirfile handles existing paths
            field_names = roach_config["packet_structure"]["max_ntones"] if not field_names else field_names

            # create a new dirfile with the field names taken from the currently loaded tones-list
            new_dirfile = lib_dirfiles.create_dirfile(dirfilename = new_dirfile, tones = field_names, datatag = datatag)

            # close previous dirfile
            lib_dirfiles.close_dirfile(self._last_closed_dirfile)

        else:
            print "Unrecognised input - {0}. Try again.".format(new_dirfile)

    def read_existing_sweep_file(self, path_to_sweep):
        # check if filename appears to be a valid dirfile
        assert _lib_dirfiles.is_path_a_dirfile(path_to_sweep)
        self.current_sweep_dirfile = _gd.dirfile(path_to_sweep, _gd.RDWR)

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
            - implement a method to determine if packets are being captured correctly? this is done!

        """
        valid_kwargs = ["sweep_span", "sweep_step", "sweep_avgs", "save_data"]

        # parse the keyword arguments
        sweep_span = np.float32( sweep_kwargs.pop("sweep_span", self.ROACH_CFG["sweep_span"]) )
        sweep_step = np.float32( sweep_kwargs.pop("sweep_step", self.ROACH_CFG["sweep_step"]) )
        sweep_avgs = np.int32  ( sweep_kwargs.pop("sweep_avgs", self.ROACH_CFG["sweep_avgs"]) )

        save_data = sweep_kwargs.pop("save_data", True)

        if sweep_kwargs.keys():
            print "Error: Optional argument(s) {0} not processed. Valid kwargs are {1}. Sweep not completed.".format(sweep_kwargs.keys(), valid_kwargs)
            return

        # check that daemonwriter is not currently writing, return if not as something has probably gone wrong
        if self.writer_daemon.is_writing == True:
            print "Writer is already running. Aborting sweep. Stop current file and retry."
            return

        # perform a quick check that packets are being streamed to the roach

        # get list of LO frequencies for sweeping
        # roachcontainer.losweep_freqs # this is calculated from the LO freq, sweep bandwidths
        lo_freqs = np.arange(self.synth_lo.frequency - sweep_span/2., \
                                self.synth_lo.frequency + sweep_span/2., \
                                sweep_step,\
                                dtype = np.float32)

        # create new dirfile and set it as the active file. Note that data writing is off by default.
        self.writer_daemon.set_active_dirfile(datatag = "sweep_raw")

        time.sleep(1)

        # set up sweep timing parameters
        step_times = []
        # # get time for avg factor
        sleeptime = np.round( sweep_avgs / 488. * 1.05, decimals = 3 )#self.fpga.sample_rate) * 1.05 # num avgs / sample_rate + 5%
        print "sleep time for sweep is {0}".format(sleeptime)

        # alias to current dirfile for convenience
        self.current_dirfile = self.writer_daemon.current_dirfile

        # start writing data to file
        print "starting to write data"
        self.writer_daemon.start_writing()

        # wait until writing starts
        while not self.writer_daemon.is_writing:
            time.sleep(0.1)
            continue

        #time.sleep(2)
        #loop over LO frequencies, while saving time at lo_step
        try:
            for lo_freq in lo_freqs:
                self.synth_lo.frequency = lo_freq
                step_times.append( time.time() )
                time.sleep(sleeptime)
        except KeyboardInterrupt:
            pass

        self.writer_daemon.pause_writing()

        # save lostep_times to current dirfile
        self.current_dirfile.add(_gd.entry(_gd.RAW_ENTRY, "lo_freqs",     0, (_gd.FLOAT64, 1)))
        self.current_dirfile.add(_gd.entry(_gd.RAW_ENTRY, "lostep_times", 0, (_gd.FLOAT64, 1)))

        self.current_dirfile.putdata("lo_freqs",     np.ascontiguousarray( lo_freqs,   dtype = np.float64 ))
        self.current_dirfile.putdata("lostep_times", np.ascontiguousarray( step_times, dtype = np.float64 ))

        # on my mac, we need to close and reopen the dirfile to flush the data before reading back in the data
        # - not sure why, or if this is a problem on linux
        self.current_dirfile.close()
        self.current_dirfile = _gd.dirfile(self.writer_daemon.current_filename, _gd.RDWR)

        # with the raw sweep data available, create the derived sweep file and save to the current dirfile (from lib_dirfiles)

        lotimes = self.current_dirfile.getdata("lostep_times")
        ptimes  = self.current_dirfile.getdata("python_timestamp")

        # align LO steps with python timestreams
        idxs = np.searchsorted(ptimes, lotimes)[1:] # miss out the first point (should always be 0)
        #print "indexes",idxs

        # read in IQ data and split up according to LO steps and store in a dictionary
        sweep_data_dict = {}
        startidx = 0 # user defined number of samples to skip after lo switch (to be read from config, or set at run time)
        stopidx  = None # same, but at the other end (None reads all samples)

        for field in self.current_dirfile.field_list():

            # currently are only averaging the tones K <- this is not good enough...
            if field.startswith("K"):

                # get the field data, split and average the lo switch indexes, taking data between startidx and stopidx, and pass to an array
                data = np.array([np.mean(l[startidx:stopidx]) for l in np.split(self.current_dirfile.getdata(field), idxs)])

                # split the field to get the tone name, and I or Q
                try:
                    tonenum, i_or_q = field.split('_')
                except ValueError:
                    print "the field name {0} doesn't appear to be of the correct format".format(field)
                    continue # continue to next iteration

                # add new key to dictionary if data doesn't already exist
                sweep_data_dict[tonenum] = np.zeros_like(data, dtype=np.complex64) if tonenum not in sweep_data_dict.keys() else sweep_data_dict[tonenum]
                if i_or_q.lower() == "i":
                    sweep_data_dict[tonenum].real = data
                elif i_or_q.lower() == "q":
                    sweep_data_dict[tonenum].imag = data
                else:
                    print "unknown field name - something went wrong. "
                    continue


        # create new sweep dirfile and keep hold of it
        self.current_sweep_dirfile = _lib_dirfiles.generate_sweep_dirfile(self.writer_daemon.DIRFILE_SAVEDIR, lo_freqs, sweep_data_dict)

        # add metadata for
        _lib_dirfiles.add_metadata_to_dirfile(self.current_sweep_dirfile, {"raw_sweep_filename": self.current_dirfile.name})

        #return sweep_data_dict
        # close dirfile to prevent further writing
        #self.current_dirfile.close()




        # stop file write
        # get dirfilehandle
        # discard first Npoints (user definable)
        # average together to get f, I, Q
        # save as a new file in the dirfile
        # add to format file
        # retain reference to dirfile here
        # link to visualisation.py for plotting (or scraps)
        # post process sweep to find F0s...etc

        # playing with subdirfiles

    def stop_stream(self, **streamkwargs):
        """

        Function to use to stop streaming data to disk.

        """
        if self.writer_daemon.is_writing:
            self.writer_daemon.pause_writing()

            self.current_dirfile.close()
            self.current_dirfile = _gd.dirfile(self.writer_daemon.current_filename, _gd.RDWR)

        else:
            print "writer doesn't appear to be running. Nothing done."


    def start_stream(self, **stream_kwargs):
        """

        Function to use to stream data to disk.

        """

        stream_time = stream_kwargs.pop("stream_time", None)
        save_data   = stream_kwargs.pop("save_data", True) # currently not used

        # check that sweep exists - warn if not and give option to proceed?
        if self.current_sweep_dirfile is None:
            print "warning: no sweep file available - limited functionality available"

        # create a new dirfile for the observation
        self.writer_daemon.set_active_dirfile(datatag = "stream")
        time.sleep(1)

        # alias to current dirfile for convenience
        self.current_dirfile = self.writer_daemon.current_dirfile

        print "starting to write data"
        self.writer_daemon.start_writing()

        # wait until writing starts
        while not self.writer_daemon.is_writing:
            time.sleep(0.1)
            continue

        # run for designated period of time if set, otherwise finish
        if stream_time is not None:
            tstart = time.time()
            while time.time() < tstart + stream_time:
                time.sleep(stream_time/10.)
                continue

            self.stop_stream()



    def shutdown(self):
        """Shutdown procedure for the roach interface"""

        # terminate writer daemon threads
        self.writer_daemon.terminate()
        # close all local file descriptors
        try:
            self.current_dirfile.close()
            self.current_sweep_dirfile.close()
        except AttributeError:
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
