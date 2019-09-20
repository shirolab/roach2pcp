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

#from memory_profiler import profile

import os, sys, time, logging as _logging, numpy as np, pandas as _pd
import multiprocessing as _multiprocessing
import multiprocessing.pool as _multiprocessing_pool

import atexit
from functools import wraps as _wraps
from tqdm import tqdm as _tqdm
import pygetdata as _gd

_logger = _logging.getLogger(__name__)

try:
    import casperfpga
except ImportError:
    _logger.warning( "can't find casperfpga module - limited functionality available" )
    casperfpga = None
    pass

from . import ROACH_LIST
from .configuration import ROOTDIR, filesys_config, roach_config, network_config, hardware_config, general_config

# import the synth dictionary from
from .synthesizer import SYNTH_HW_DICT as _SYNTH_HW_DICT # note that we might need to be careful of import order here

from . import toneslist, datalog_mp, sweep
from .lib import lib_dirfiles as _lib_dirfiles, lib_fpga as _lib_fpga

from .configuration import color_msg as cm

#from .lib.lib_hardware import usb_detector

from .lib.lib_hardware import initialise_connected_synths as _initialise_connected_synths
SYNTHS_IN_USE = _initialise_connected_synths()

from .lib.lib_hardware import initialise_connected_attens as _initialise_connected_attens
ATTENS_IN_USE = _initialise_connected_attens()

import kid.resonator_routines as _resonator_routines

class muxChannel(object):
    def __init__(self, roachid):

        atexit.register(self.shutdown)

        self.roachid  = roachid

        #self.fpga            = _lib_fpga.get_fpga_instance(roachid)
        self.roach_iface     = _lib_fpga.roachInterface( roachid )

        # initialise writer daemon
        self.writer_daemon   = self._initialise_daemon_writer()

        # configure the tonelist - add functionality to modify datapacket_dict when the toneslist changes
        self.toneslist       = toneslist.Toneslist(roachid, loader_function = _pd.read_csv)
        self.writer_daemon.initialise_datapacket_dict( self.toneslist )
        self.toneslist.load_tonelist = self._decorate_tonelist_loader( self.toneslist.load_tonelist )

        # set up the sweep object
        self.sweep = sweep.pcpSweep()

        self._last_written_bb_freqs = None

        self.synth_lo        = None
        self.synth_clk       = None

        self.loswitch        = True # used to turn off LO swtiching during sweep

        self.input_atten     = None
        self.output_atten    = None

        self.current_dirfile       = None
        self.current_sweep_dirfile = None

        # start usb monitoring
        #self.usb_device = usb_detector()

        # get configuration for specific roach
        self.ROACH_CFG = roach_config[self.roachid]
        self.sample_rate = self.ROACH_CFG["dac_bandwidth"] / ( 2**self.ROACH_CFG["roach_accum_len"] )

        # generate directory path for data saving
        self.DIRFILE_SAVEDIR  = os.path.join(ROOTDIR, filesys_config['savedatadir'], self.roachid)
        # create if doesn't exist already
        os.makedirs(self.DIRFILE_SAVEDIR) if not os.path.exists(self.DIRFILE_SAVEDIR) else None

        # create kst sourcefile in directory if it already doesn't exist
        self._srcfile = open( os.path.join(self.DIRFILE_SAVEDIR, 'sf.txt'), 'w+')

        # convenience access for writing to packet
        self.write_int = self.roach_iface.fpga.write_int
        self.read_int = self.roach_iface.fpga.read_int
        
        self.initialise_hardware()

################################################################################
################################################################################
    def _decorate_tonelist_loader(self, original_loader_function):
        @_wraps(original_loader_function)
        def load_and_update_datapacket_dict(*args, **kwargs):
            original_loader_function(*args, **kwargs)
            #self._refresh_datapacket_dict()
            self.writer_daemon.initialise_datapacket_dict( self.toneslist )
        return load_and_update_datapacket_dict

    def _initialise_daemon_writer(self):
        writer_daemon = datalog_mp.dataLogger( self.roachid )
        writer_daemon.start_daemon()
        return writer_daemon

    def refresh_connections(self):
        global SYNTHS_IN_USE
        global ATTENS_IN_USE

        SYNTHS_IN_USE = _initialise_connected_synths()
        ATTENS_IN_USE = _initialise_connected_attens()

        self.initialise_hardware()

    def _check_connections(self):
        # Check Connection status
        for synth in SYNTHS_IN_USE:
            dev = SYNTHS_IN_USE[synth].synthobj
            # Try to get the frequency
            try:
                get_freq = dev.frequency
                print "[ " + cm.OKGREEN + "ok" + cm.ENDC +" ] {synth} Connected :)".format(synth = synth)
            except:
                print "[ " + cm.FAIL + "fail" + cm.ENDC +" ] {synth} Not connected :)".format(synth = synth)

        for atten in ATTENS_IN_USE:
            dev = ATTENS_IN_USE[atten].attenobj
            # Try to get the frequency
            try:
                get_atten = dev.attenuation
                print "[ " + cm.OKGREEN + "ok" + cm.ENDC +" ] {atten} Connected :)".format(atten = atten)
            except:
                print "[ " + cm.FAIL + "fail" + cm.ENDC +" ] {atten} Not connected :)".format(atten = atten)

    def initialise_hardware(self):
        # initialise the synthesisers
        self._initialise_synth_clk()
        self._initialise_synth_lo()

        # initialise the attenuators
        self._initialise_atten_in()
        self._initialise_atten_out()

    # def shutdown_hardware(self):
    #     #close connections to hardware
    #     self._shutdown_synth_connections()
    #
    # def _shutdown_synth_connections(self):
    #     if self.synth_lo not None:
    #         self.synth_lo.device.close()

    def _initialise_synth_lo(self):
        # get configuration
        synthid_lo = self.ROACH_CFG["synthid_lo"]

        try:
            self.synth_lo = SYNTHS_IN_USE[synthid_lo].synthobj
            self.synth_lo.frequency = self.toneslist.lo_freq
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

    def _initialise_atten_in(self):
        # get configuration for attenuators
        att_in = self.ROACH_CFG["att_in"]

        if att_in is not None:
            # get the dictionary of live attenuators and initialise
            self.input_atten = ATTENS_IN_USE[att_in].attenobj
            #set the input attenuation
            self.input_atten.attenuation = 15

        else:
            self.input_atten = None

    def _initialise_atten_out(self):
        # get configuration for attenuators
        att_out = self.ROACH_CFG["att_out"]

        if att_out is not None:
            # get the dictionary of live attenuators and initialise
            self.output_atten = ATTENS_IN_USE[att_out].attenobj
            #set the input attenuation
            self.output_atten.attenuation = 15

        else:
            self.output_atten = None

    def write_freqs_to_fpga(self, auto_write = False):
        """High level function to write the current toneslist frequencies to the QDR"""

        # make sure fpga looks like its running
        if not ( self.roach_iface.fpga and self.roach_iface.fpga.is_connected() ):
            _logger.warning("fpga instance appears to be broken. Returning.")
            self._last_written_bb_freqs = None
            return
        # check if new tones equal old tones, return if True
        if all(self.toneslist.bb_freqs == self._last_written_bb_freqs):
            _logger.info("It looks like this set of tones has already been uploaded. Nothing done.")
            return

        # check that toneslist LO and synth LO match - if not yell and or ask to change the LO
        assert self.toneslist.lo_freq == self.synth_lo.frequency, "synth frequency doesn't match toneslist.lo_freq"

        # write_freqs_to_qdr
        if auto_write or raw_input("Write new tones to qdr? [y/n]").lower() == 'y':
            self.roach_iface.write_freqs_to_qdr(self.toneslist.bb_freqs, self.toneslist.amps, self.toneslist.phases)
        else:
            _logger.info("new tones loaded but not written to qdr.")

        # write newly written tones to hidden variable for future checks
        self._last_written_bb_freqs = self.toneslist.bb_freqs

    def set_active_dirfile(self, dirfile_name = "", dirfile_type = "stream", filename_suffix = "", inc_derived_fields = False ):#, field_suffix = ""):
        # if an empty string is given (default), then we pass the DIRFILE_SAVEDIR as the filename to lib_dirfile.create_dirfile,
        # which generates a new filename with the filename format given general_config['default_datafilename_format']).
        # This is likely to be the most used case
        dirfile_name = self.DIRFILE_SAVEDIR if not dirfile_name else dirfile_name

        # store last open filename for convenience
        self._last_closed_dirfile  = self.current_dirfile
        self._last_closed_filename = self.current_dirfile.name if isinstance(self.current_dirfile, _gd.dirfile) else None

        # check type of new_dirfile
        if type(dirfile_name) == _gd.dirfile:
            _logger.info( "dirfile file handle given. Nothing done" )
            pass # unnecessary, but just to be explicit

        elif type(dirfile_name) == str:
            # create a new dirfile with the field names taken from the currently loaded tones-list
            dirfile_name = _lib_dirfiles.create_pcp_dirfile( self.roachid, \
                                                            dirfilename        = dirfile_name,    \
                                                            tones              = self.toneslist, \
                                                            filename_suffix    = filename_suffix )
            # close previous dirfile
            _lib_dirfiles.close_dirfile(self._last_closed_dirfile)

        else:
            _logger.warning( "Unrecognised input - {0}. Try again.".format(dirfile_name) )
            return

        # now set active dirfile in writer daemon
        if self.writer_daemon.is_daemon_running():
            self.writer_daemon.set_active_dirfile( dirfile_name )
        else:
            _logger.warning( "daemon writer doesn't appear to be running. Check and try again." )

        self.current_dirfile = dirfile_name
        time.sleep(0.1)

        # add the file to the source file
        _lib_dirfiles.append_dirfile_to_sourcefile(self._srcfile,
                                    self.current_dirfile.name,
                                    timespan = general_config["srcfile_timespan"] )


    def read_existing_sweep_file(self, path_to_sweep):
        # check if filename appears to be a valid dirfile
        assert _lib_dirfiles.is_path_a_dirfile(path_to_sweep)
        self.current_sweep_dirfile = _gd.dirfile(path_to_sweep, _gd.RDWR)

    def sweep_lo(self, stop_event = None, **sweep_kwargs):
        """
        Function to sweep the LO. Takes in a number of optional keyword arugments. If not given,
        defaults from the configuration files are assumed.

        Keyword Arguments
        -----------------

        sweep_span : float
            Frequency span, in Hz, about which to sweep the LO around its currently set value.

        sweep_step : float
            Frequency step, in Hz, in which to sweep the LO around its currently set value. Note that some
            synthesiers have a minimum step size. Every attempt has been made to try to make the user know
            if the hardware is limiting the step, but care should still be taken.

        sweep_avgs : int
            Number of packets to average per LO frequency. This is used to calculate an approximate integration
            time to collect sweep_avgs. There is a 5% time addition to ensure that at least this many packets are
            collected.

        startidx : int
            user defined number of samples to skip after lo switch (to be read from config, or set at run time)

        stopidx : int
            same as startidx, but for the other end (None reads all samples up to lo_switch)
        save_data : bool
            Flag to turn off data writing. Mainly for testing purposes. Default is, of course, True.

        # TODO:
            - implement a method to determine if packets are being captured correctly? this is done!

        """
        stop_event = _multiprocessing.Event() if not isinstance( stop_event, _multiprocessing.synchronize.Event ) else stop_event

        valid_kwargs = ["sweep_span", "sweep_step", "sweep_avgs", "startidx", "stopidx", "save_data"]

        # parse the keyword arguments

        timeout    = np.int32  ( sweep_kwargs.pop("timeout", 2.) )

        sweep_span = np.float32( sweep_kwargs.pop("sweep_span", self.ROACH_CFG["sweep_span"]) )
        sweep_step = np.float32( sweep_kwargs.pop("sweep_step", self.ROACH_CFG["sweep_step"]) )
        sweep_avgs = np.int32  ( sweep_kwargs.pop("sweep_avgs", self.ROACH_CFG["sweep_avgs"]) )

        self.toneslist.get_sweep_lo_freqs(sweep_span, sweep_step)

        startidx   = sweep_kwargs.pop("startidx", 0 )    #startidx = 0 # user defined number of samples to skip after lo switch (to be read from config, or set at run time)
        stopidx    = sweep_kwargs.pop("stopidx" , None ) #stopidx  = None # same, but at the other end (None reads all samples)

        filename_suffix = sweep_kwargs.pop("filename_suffix", "")
        #field_suffix    = sweep_kwargs.pop("field_suffix"   , "")

        save_data = sweep_kwargs.pop("save_data", True) # not implmented yet (20190120)

        if sweep_kwargs.keys():
            _logger.error( "Error: Optional argument(s) {0} not processed. Valid kwargs are {1}. Sweep not completed.".format(sweep_kwargs.keys(), valid_kwargs) )
            return
        # check that daemonwriter is not currently writing, return if not as something has probably gone wrong
        if self.writer_daemon.is_writing == True:
            _logger.info( "Writer is already running. Aborting sweep. Stop current file and retry." )
            return

        # perform a quick check that packets are being streamed to the roach
        assert self.synth_lo is not None, "synthesiser doesn't appear to be initialised. "
        assert self.writer_daemon.check_packets_received(), "packets don't appear to be streaming. Check roaches and try again."

        # create new dirfile and set it as the active file. Note that data writing is off by default.
        self.set_active_dirfile( filename_suffix = "sweep_raw" + filename_suffix )

        # set up sweep timing parameters
        step_times = []
        # # get time for avg factor
        sleeptime = np.round( sweep_avgs / self.sample_rate * 1.1, decimals = 3 )
        _logger.debug( "sleep time for sweep is {0}".format(sleeptime) )

        # alias to current dirfile for convenience
        self.current_dirfile = self.writer_daemon.current_dirfile

        # start writing data to file
        _logger.debug( "starting to write data" )
        self.writer_daemon.start_writing()

        # wait until writing starts
        t0 = time.time()
        while not self.writer_daemon.is_writing:
            time.sleep(0.01)
            if time.time() >= t0 + timeout : # wait for 2 seconds
                _logger.error( "timeout waiting for writer daemon to start writing. check to see if something went wrong." )
                return
            else:
                continue

        #loop over LO frequencies, while saving time at lo_step
        try:
            #for lo_freq in lo_freqs
            #pbar = _tqdm(self.toneslist.sweep_lo_freqs, ncols=75)
            #for lo_freq in pbar:
            sweepdirection = np.sign( np.diff(self.toneslist.sweep_lo_freqs) )[0] # +/- 1 for forward/backward
            for lo_freq in self.toneslist.sweep_lo_freqs:

                if self.loswitch == True:
                    self.synth_lo.frequency = lo_freq
                else:
                    # wait until synth_lo.frequency => lo_freq
                    t0 = time.time()
                    while self.synth_lo.frequency <= lo_freq and time.time() <= t0 + sleeptime :
                        time.sleep(sleeptime / 10.)

                step_times.append( time.time() )

                if stop_event.is_set():
                    break
                #pbar.set_description(cm.BOLD + "LO: %i" % lo_freq + cm.ENDC)
                time.sleep(sleeptime)

            #pbar.close()
            #print cm.OKGREEN + "Sweep done!" + cm.ENDC
        except KeyboardInterrupt:
            pass

        self.writer_daemon.pause_writing()

        # Back to the central frequency
        if self.loswitch == True:
            self.synth_lo.frequency = self.toneslist.lo_freq

        # save lostep_times to current dirfile
        self.current_dirfile.add( _gd.entry(_gd.RAW_ENTRY, "lo_freqs"    , 0, (_gd.FLOAT64, 1) ) )
        self.current_dirfile.add( _gd.entry(_gd.RAW_ENTRY, "lostep_times", 0, (_gd.FLOAT64, 1) ) )

        self.current_dirfile.putdata("lo_freqs"    , np.ascontiguousarray( self.toneslist.sweep_lo_freqs, dtype = np.float64 ))
        self.current_dirfile.putdata("lostep_times", np.ascontiguousarray( step_times,                    dtype = np.float64 ))

        # on mac, we need to close and reopen the dirfile to flush the data before reading back in the data
        # - not sure why, or if this is a problem on linux - it doesn't hurt too much though
        self.current_dirfile.close()
        self.current_dirfile = _gd.dirfile(self.writer_daemon.current_filename, _gd.RDWR)

        # with the raw sweep data available, create the derived sweep file and save to the current dirfile (from lib_dirfiles)
        lotimes = self.current_dirfile.getdata( "lostep_times" )
        ptimes  = self.current_dirfile.getdata( "python_timestamp" ) # way to get the python_timestamp field with knowing any field suffix

        # align LO steps with python timestreams
        idxs = np.searchsorted(ptimes, lotimes)[1:] # miss out the first point (should always be 0)
        #print "indexes",idxs

        # read in IQ data and split up according to LO steps and store in a dictionary
        sweep_data_dict = {}

        startidx = np.int32(startidx)
        stopidx  = np.int32(stopidx) if stopidx is not None else stopidx

        for field in _tqdm(self.current_dirfile.field_list( _gd.RAW_ENTRY ), desc=cm.BOLD+"Writing data"+cm.ENDC, ncols=75):

            if ("_I" in field) or ("_Q" in field): #field.startswith("K"):

                # get the field data, split and average the lo switch indexes, taking data between startidx and stopidx, and pass to an array
                data = np.array([np.mean(l[startidx:stopidx]) for l in np.split(self.current_dirfile.getdata(field), idxs)])

                # split the field to get the tone name, and I or Q
                try:
                    tonenum, i_or_q = field.split('_')
                except ValueError:
                    print "the field name {0} doesn't appear to be of the correct format".format(field)
                    continue # continue to next iteration

                # add new key to dictionary if data doesn't already exist
                sweep_data_dict[tonenum] = np.zeros_like(data, dtype=np.complex64) if tonenum not in sweep_data_dict.keys() \
                                                                                    else sweep_data_dict[tonenum]
                if i_or_q.lower() == "i":
                    sweep_data_dict[tonenum].real = data
                elif i_or_q.lower() == "q":
                    sweep_data_dict[tonenum].imag = data
                else:
                    _logger.error( "unknown field name - something went wrong. " )
                    continue

        # create new sweep dirfile and keep hold of it
        self.sweep.load_sweep_dirfile( _lib_dirfiles.generate_sweep_dirfile(self.roachid, \
                                                                            self.DIRFILE_SAVEDIR,
                                                                            self.toneslist.sweep_lo_freqs, \
                                                                            self.toneslist.bb_freqs.get_values(),\
                                                                            sweep_data_dict) )
        # # add metadata
        _lib_dirfiles.add_metadata_to_dirfile(self.sweep.dirfile, {"raw_sweep_filename": self.current_dirfile.name})

        # -- add calibration parameters for sweep

        self.sweep.calc_sweep_cal_params()
        self.sweep.write_sweep_cal_params(overwrite=True) # overwrite

    # def test_loop(self):
    #     step_times = []
    #     sleeptime = 1.
    #     #self.set_active_dirfile()
    #     #self.writer_daemon.start_writing()
    #     try:
    #         for lo_freq in self.toneslist.sweep_lo_freqs:
    #             self.synth_lo.frequency = lo_freq
    #             step_times.append( time.time() )
    #             time.sleep(sleeptime)
    #
    #     except KeyboardInterrupt:
    #         print "out of loop"
    #     #self.writer_daemon.pause_writing()


    def tune_resonators(self, method = "maxspeed"):
        """
        Function to find resonator frequencies from a sweep
        """
        assert method in ['maxspeed', 'mins21'], "Given method {0} for finding resonant frequencies not valid.".format(method)

        #_lib_dirfiles.open_dirfile(dirfilename, **dirfile_flags):

        if self.current_sweep_dirfile:
            sweep_data, = _lib_dirfiles.read_sweep_dirfile( self.current_sweep_dirfile )

        else:
            _logger.warning("no sweep dirfile set. Nothing done.")

        # remove blind tones/ don't retune blind tones

        # use method to find F0s from KID rountines

        # change frequencies in self.toneslist

        # write to qdr (optional)

        #return sweep_data_dict
        # close dirfile to prevent further writing
        #self.current_dirfile.close()



    #@profile
    def start_stream(self, **stream_kwargs):
        """

        Function to use to stream data to disk.

        Valid keyword arguements:
            filename_suffix - str, default ""
            stream_time - numeric value for length of time to stream data for, default None - streams forever

        """
        filename_suffix = stream_kwargs.pop("filename_suffix", "")
        stream_time     = stream_kwargs.pop("stream_time", None)
        save_data       = stream_kwargs.pop("save_data", True) # currently not used
        dont_ask        = stream_kwargs.pop("dont_ask", False)

        dirfile_name = stream_kwargs.pop("dirfilename", "") # allow the user to pass in and append to an existing dirfile

        # check that sweep exists - warn if not and give option to proceed
        if self.current_sweep_dirfile is None:
            _logger.warning( "no sweep file available - limited functionality available" )
            if dont_ask==False:
                response = raw_input("Proceed? [y/n] ")
                if response == "n":
                    return
            #

        #     else:
        #         response='y'
        # else:

        # create a new dirfile for the observation
        self.set_active_dirfile( dirfile_name = dirfile_name, filename_suffix = filename_suffix )

        # add sweepdirfile as a new fragment to the new dirfile

        if isinstance( self.current_sweep_dirfile , _gd.dirfile ):
            _lib_dirfiles.add_subdirfile_to_existing_dirfile(self.current_sweep_dirfile, self.current_dirfile)

        # alias to current dirfile for convenience
        self.current_dirfile = self.writer_daemon.current_dirfile

        print "starting to write data"
        self.writer_daemon.start_writing()

        # wait until writing starts
        while not self.writer_daemon.is_writing:
            print "waiting for writer to start"
            time.sleep(0.1)
            continue

        # run for designated period of time if set, otherwise finish
        if stream_time is not None:
            stream_time = float(stream_time)
            tstart = time.time()
            while time.time() < tstart + stream_time:
                time.sleep(stream_time/10.)
                continue

            self.stop_stream()

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


    def shutdown(self):
        """Shutdown procedure for the roach interface"""

        # terminate writer daemon threads
        self.writer_daemon.terminate()

        # close all local file descriptors
        self._srcfile.close()

        try:
            self.current_dirfile.close()
            self.current_sweep_dirfile.close()
        except AttributeError:
            pass

class muxChannelList(object):

    def __init__(self, channel_list):

        channel_list = list(np.atleast_1d(channel_list))
        _logger.debug("initialising muxChannelList with channel list {0}".format( channel_list ) )

        assert isinstance(channel_list, (list, tuple)) and len(channel_list) > 0 , "input {0} not recognised".format( type(channel_list) )

        self.ROACH_LIST = channel_list

        # determine if the elements of the list are instantiated muxChannel objects
        if all( [isinstance(el, muxChannel) for el in channel_list]):
            _logger.debug("found a list of existing muxchannels with roachids: {0}".format( [el.roachid for el in channel_list] ) )

        elif set(channel_list).issubset(ROACH_LIST):
            # create the muxchannels
            for roachid in channel_list:
                _logger.debug("initialising muxChannel({roachid}) ".format( roachid=roachid ) )
                setattr( self, roachid, muxChannel(roachid) )

    def _verify_channel_list_valid(self, channel_list):
        assert set(channel_list).issubset(self.ROACH_LIST), "channels given are not valid {0}".format(set(channel_list).difference(self.ROACH_LIST))
        return True

    def set_attenuation(self, new_vals, channels_to_change, mode = "increment"):
        """
        Sets the attenuations. Does this in serial, as this should be a quick process that isn't done regularly
        """
        new_vals           = np.atleast_1d(new_vals)
        channels_to_change = np.atleast_1d(channels_to_change)

        self._verify_channel_list_valid(channels_to_change)

        # Currently implemented modes - aboslute or incremental
        assert mode in ["increment", "absolute"], "given mode unknown {0}".format(mode)
        # Accepts either a single value, or a list of same length as the channel list
        assert (len(new_vals) == len(channels_to_change)) or (len(new_vals) == 1 ), "length of new_vals is confusing"

        new_vals = np.ones_like(channels_to_change, dtype=float) * new_vals if len(new_vals) == 1 else new_vals

        for att_val, roachid in zip(new_vals, channels_to_change):

            handle_to_atten = getattr( getattr( self, roachid  ), "input_atten")

            if mode == "absolute":
                handle_to_atten.attenuation = att_val
            elif mode == "increment":
                handle_to_atten.attenuation += att_val
            else:
                _logger.warning("mode not recognised. Nothing done")

    def sweep_lo(self, channels_to_sweep, **sweep_kwargs):
        """
        Function to perform an LO sweep of a set of roaches given by channels_to_sweep.

        This function creates a process pool to perform the sweeps in parallel.

        """
        channel_obj_list = [getattr(self, instance) for instance in np.atleast_1d(channels_to_sweep)]

        synth_list = [mc.synth_lo for mc in channel_obj_list]

        # check to see if muxchannels are using the same synths and return repeated indexs
        unique_synths, idx, inv = np.unique( synth_list, return_index = True, return_inverse = True )

        # turn off loswitching on duplicates
        for dupidx in set( np.arange( len(synth_list) ) ).difference(idx):
            channel_obj_list[dupidx].loswitch = False

        # create multiprocesing.ThreadPool - threads required as synchronisation is based on reading of synth_lo objects
        mp_pool = _multiprocessing_pool.ThreadPool( processes = len(channels_to_sweep) )

        stop_sweep = _multiprocessing.Event()
        sweep_kwargs.update( {"stop_event": stop_sweep} )

        # start the sweeps
        try:
            res = [mp_pool.apply_async(obj.sweep_lo, (), sweep_kwargs)  for obj in channel_obj_list ]

            # wait for sweeps to finish - allows
            while not all([r.ready() for r in res]):
                time.sleep(0.5)

        except KeyboardInterrupt:
            stop_sweep.set()
            _logger.info( "sweeps interuptted" )

        # close and join the ThreadPool
        mp_pool.close()
        mp_pool.join()

        # reset the stop Event
        stop_sweep.clear()

        assert not all( [r.get() for r in res] ) # all results should be None, unless something bad happened

        # finally, switch lo back to on for all
        for ch in channel_obj_list:
            ch.loswitch = True

        #return res

    def start_stream_multi(self, channels_to_stream, *stream_args):
        pass
        # stream all

    def stop_stream_multi(self, channels_to_stream, *stream_args):
        pass

    def shutdown_all(self, which = None):
        for roachid in self.ROACH_LIST:
            try:
                getattr(self, roachid).shutdown()
            except:
                _logger.exception("shutdown not successful.")

def _worker(arg):
    print arg
    for i in range(10):
        print i
    #obj, methname = arg[:2]
    #print obj, methname, arg[2:]
    #return getattr(obj, methname)()


# def dummy_sweep(i, **kwargs):
#     stop_event = kwargs.pop("stop_event", _multiprocessing.Event() )
#     print "loop {0}".format(i), kwargs
#     try:
#         for i in range(10):
#             time.sleep(1)
#             if stop_event.is_set():
#                 break
#
#     except KeyboardInterrupt:
#         print "loop{0} interuptted".format(i)
#
#     print "loop {0} finished".format(i)
#
# #res = [mp_pool.apply_async(obj.sweep_lo, (i,), {'arg1':1, 'arg2':2} ) for i in range(3) ]

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
