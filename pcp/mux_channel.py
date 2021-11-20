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

import os, sys, time, logging as _logging, numpy as np, dateutil as _dateutil, warnings

import multiprocessing as _multiprocessing
import multiprocessing.pool as _multiprocessing_pool

import pcp, pcp.configuration.color_msg as cm

import atexit as _atexit
from functools import wraps as _wraps
from tqdm import tqdm as _tqdm
import pandas as _pd, pygetdata as _gd

_logger = _logging.getLogger(__name__)

try:
    import casperfpga
except ImportError:
    _logger.warning( "can't find casperfpga module - limited functionality available" )
    casperfpga = None
    pass


# from .configuration import ROOTDIR, filesys_config, roach_config, network_config, hardware_config, general_config

# import the synth dictionary from
# from .drivers.synthesizer import SYNTH_HW_DICT as _SYNTH_HW_DICT # note that we might need to be careful of import order here

from . import toneslist, datalog_mp, sweep
from .lib import lib_dirfiles as _lib_dirfiles, lib_fpga as _lib_fpga

#from .configuration import color_msg as cm
#
# #from .lib.lib_hardware import usb_detector
#
# from .lib.lib_hardware import initialise_connected_synths as _initialise_connected_synths
# SYNTHS_IN_USE = _initialise_connected_synths()
#
# from .lib.lib_hardware import initialise_connected_attens as _initialise_connected_attens
# ATTENS_IN_USE = _initialise_connected_attens()
#
#import kid.resonator_routines as _resonator_routines

class muxChannel(object):
    def __init__(self, roachid):

        _atexit.register(self.shutdown)

        self.roachid  = roachid
        # grab the root directory from

        assert pcp.ROOTDIR, "ROOTDIR not found. Run pcp initialisation script to set up configuration correctly"
        self.ROOTDIR = pcp.ROOTDIR
        self.GENERAL_CFG = pcp.GENERAL_CONFIG

        # initialise/create the file structure for data saving + the sourcefile
        self._initialise_folders()

        #self.fpga            = _lib_fpga.get_fpga_instance(roachid)
        self.ri     = _lib_fpga.roachInterface( roachid )

        # initialise writer daemon
        self.writer_daemon = self._initialise_daemon_writer()

        # configure the tonelist - added functionality to modify datapacket_dict when the toneslist changes
        self.tl = toneslist.Toneslist(roachid, loader_function = _pd.read_csv)
        self.writer_daemon.initialise_datapacket_dict( self.tl.tonenames_sorted  )
        self.tl.load_tonelist = self._decorate_tonelist_loader( self.tl.load_tonelist )

        # set up the sweep object (used for storing saved data)
        self.sweep = sweep.pcpSweep(outputdir = os.path.join( self.TUNINGDIR, 'sweeps') )

        self._last_written_bb_freqs = None

        self.synth_lo        = None
        self.synth_clk       = None

        self.loswitch        = True # used to turn off LO swtiching during sweep

        self.atten_in     = None
        self.atten_out    = None

        self.current_dirfile = None

        # get configuration for specific roach
        self.ROACH_CFG = pcp.ROACH_CONFIG[self.roachid]
        self.sample_rate = self.ROACH_CFG["dac_bandwidth"] / ( 2**self.ROACH_CFG["roach_accum_len"] + 1 )

        # initialise the various pieces of hardware
        self.initialise_hardware()

################################################################################
################################################################################
    def _decorate_tonelist_loader(self, original_loader_function):
        @_wraps(original_loader_function)
        def load_and_update_datapacket_dict(*args, **kwargs):
            original_loader_function(*args, **kwargs)
            #self._refresh_datapacket_dict()
            self.writer_daemon.initialise_datapacket_dict( self.tl.tonenames_sorted )
        return load_and_update_datapacket_dict

    def _initialise_folders(self):
        """Function to initialise the file structure for data saving for the mux channel"""

        # generate directory path for data saving and tonehistory
        self.DIRFILE_SAVEDIR  = os.path.join(self.ROOTDIR, pcp.FILESYS_CONFIG['savedatadir'], self.roachid)
        self.TUNINGDIR        = os.path.join(self.ROOTDIR, pcp.FILESYS_CONFIG['tuningdir'],   self.roachid)
        self.TONEHISTDIR      = os.path.join(self.ROOTDIR, pcp.FILESYS_CONFIG['tonehistdir'], self.roachid)
        self.AMPCORRDIR       = os.path.join(self.ROOTDIR, pcp.FILESYS_CONFIG['ampcorrdir'],  self.roachid)

        # create dirs if doesn't exist already
        os.makedirs(self.DIRFILE_SAVEDIR) if not os.path.exists(self.DIRFILE_SAVEDIR) else None
        os.makedirs(self.TUNINGDIR)       if not os.path.exists(self.TUNINGDIR)       else None
        os.makedirs(self.TONEHISTDIR)     if not os.path.exists(self.TONEHISTDIR)     else None
        os.makedirs(self.AMPCORRDIR)      if not os.path.exists(self.AMPCORRDIR)      else None

        # create kst sourcefile in directory if it already doesn't exist
        sourcefilename = os.path.join(self.DIRFILE_SAVEDIR, 'sf.txt')
        open(sourcefilename,'a').close()

        # open kst source file for later writing. 'r+' needed for writing to top of file
        self._srcfile = open( sourcefilename, 'r+')

        self._timespan = pcp.GENERAL_CONFIG["srcfile_timespan"]

    def _initialise_daemon_writer(self):
        writer_daemon = datalog_mp.dataLogger( self.roachid )
        writer_daemon.start_daemon()
        return writer_daemon

    def _refresh_connections(self):
        # global SYNTHS_IN_USE
        # global ATTENS_IN_USE

        pcp.SYNTHS_IN_USE = pcp.configuration.lib_config._initialise_connected_synths()
        pcp.ATTENS_IN_USE = pcp.configuration.lib_config._initialise_connected_attens()

        self.initialise_hardware()

    def _check_connections(self):
        # Check Connection status
        for synth in pcp.SYNTHS_IN_USE:
            dev = pcp.SYNTHS_IN_USE[synth].synthobj
            # Try to get the frequency
            try:
                get_freq = dev.frequency
                print "[ " + cm.OKGREEN + "ok" + cm.ENDC +" ] {synth} Connected :)".format(synth = synth)
            except:
                print "[ " + cm.FAIL + "fail" + cm.ENDC +" ] {synth} Not connected :)".format(synth = synth)

        for atten in pcp.ATTENS_IN_USE:
            dev = pcp.ATTENS_IN_USE[atten].attenobj
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

    def initialise_fpga(self,*args,**kwargs):
        self.ri.initialise_fpga(*args,**kwargs)

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
            self.synth_lo = pcp.SYNTHS_IN_USE[synthid_lo].synthobj
            self.synth_lo.frequency = self.tl.lo_freq
        except KeyError:
            logger.warning("synthid = {0} not recognised. Check configuration file".format(synthid_lo))

    def _initialise_synth_clk(self):

        synthid_clk = self.ROACH_CFG["synthid_clk"]

        if synthid_clk is not None:
            # get the dictionary of live synths and initialise
            self.synth_clk = pcp.SYNTHS_IN_USE[synthid_clk].synthobj

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
            self.atten_in = pcp.ATTENS_IN_USE[att_in].attenobj
            #set the input attenuation
            self.atten_in.attenuation = 15

        else:
            self.atten_in = None

    def _initialise_atten_out(self):
        # get configuration for attenuators
        att_out = self.ROACH_CFG["att_out"]

        if att_out is not None:
            # get the dictionary of live attenuators and initialise
            self.atten_out = pcp.ATTENS_IN_USE[att_out].attenobj
            #set the input attenuation
            self.atten_out.attenuation = 15

        else:
            self.atten_out = None

    def write_int(self, register, int):
        """ Write to FPGA register - e.g. to indicate status
            r0.write_int('GbE_packet_info', 1)
        """
        self.ri.fpga.write_int(register, int)

    def read_int(self, register):
        """ r0.read_int('GbE_packet_info')"""
        self.ri.fpga.read_int(register)

    def write_freqs_to_fpga(self, auto_write = False, corrtouse = None, check = True):
        """High level function to write the current toneslist frequencies to the QDR
           To use an amplitude correction: corrtouse = 'total' or timestamp of requested"""

        # make sure fpga looks like its running
        if not ( self.ri.fpga and self.ri.fpga.is_connected() ):
            _logger.warning("fpga instance appears to be broken. Returning.")
            self._last_written_bb_freqs = None
            return
        # check if new tones equal old tones, return if True
        if check:
            if all(self.tl.bb_freqs == self._last_written_bb_freqs):
                _logger.info("It looks like this set of tones has already been uploaded. Nothing done.")
                return

        # check that toneslist LO and synth LO match - if not yell and or ask to change the LO
        assert self.tl.lo_freq == self.synth_lo.frequency, "synth frequency doesn't match toneslist.lo_freq"

        # If requested, use amplitude correction
        if corrtouse is not None:
            if corrtouse == 'total':
                self.tl.amps = self.tl.ampcorr[corrtouse]()
            else:
                self.tl.amps = self.tl.ampcorr[corrtouse] # should be a timestamp

        # write_freqs_to_qdr
        if auto_write or raw_input("Write new tones to qdr? [y/n]").lower() == 'y':
            self.ri.write_freqs_to_qdr(self.tl.bb_freqs, self.tl.amps, self.tl.phases)
        else:
            _logger.info("new tones loaded but not written to qdr.")

        # write newly written tones to hidden variable for future checks
        self._last_written_bb_freqs = self.tl.bb_freqs

        # lofreq, atten_in, atten_out, amps, phases, bb_freqs
        self.tl.write_tonehistfile(self.synth_lo.frequency,  \
                                        self.atten_in.attenuation,  \
                                        self.atten_out.attenuation, \
                                        self.tl._bb_freqs.tolist(),\
                                        self.tl._amps.tolist(),\
                                        self.tl._phases.tolist(),
                                        self.tl.tonelistfile )

    def set_active_dirfile(self, dirfile_name = "", filename_suffix = "", inc_derived_fields = False, **kwargs ):
        # if an empty string is given (default), then we pass the DIRFILE_SAVEDIR as the filename to lib_dirfile.create_dirfile,
        # which generates a new filename with the filename format given general_config['default_datafilename_format']).
        # This is likely to be the most used case
        timestr_fmt = self.GENERAL_CFG['default_datafilename_format']
        if not dirfile_name:
            dirfile_name = os.path.join( self.DIRFILE_SAVEDIR, time.strftime( timestr_fmt ) )

        # store last open filename for convenience
        self._last_closed_dirfile  = self.current_dirfile
        self._last_closed_filename = self.current_dirfile.name if isinstance(self.current_dirfile, _gd.dirfile) else None

        # check type of new_dirfile
        if type(dirfile_name) == _gd.dirfile:
            _logger.info( "dirfile file handle given. Nothing done" )
            pass # unnecessary, but just to be explicit

        elif type(dirfile_name) == str:
            # create a new dirfile with the field names taken from the currently loaded tones-list
            _logger.info( "filename given: {0}".format(dirfile_name) )
            dirfile_name = _lib_dirfiles.create_pcp_dirfile( self.roachid, \
                                                            dfname          = dirfile_name,    \
                                                            tonenames       = self.tl.tonenames, \
                                                            filename_suffix = filename_suffix,
                                                            **kwargs )
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

        # add tone information to the dirfile
        self.current_dirfile.put_carray(   "bbfreqs", self.tl.bb_freqs)
        self.current_dirfile.put_constant( "lofreq",  self.tl.lo_freq )
        self.current_dirfile.put_sarray(   "tonenames", list(self.tl.tonenames) )
        self.current_dirfile.flush()
        # add the file to the source file
        _lib_dirfiles.append_dirfile_to_sourcefile(self._srcfile,
                                    self.current_dirfile.name,
                                    timespan = self._timespan )

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

        filename_suffix : str
            allows the user to append an additional string to the end of the filename
        """
        # create the stop event for use when running all roaches at once through the muxChannelList
        stop_event = _multiprocessing.Event() if not isinstance( stop_event, _multiprocessing.synchronize.Event ) else stop_event

        # configure sweep parameters and start writing
        sweep_params = self._configure_sweep_and_start_writing(**sweep_kwargs)

        # # get time for avg factor + 10%
        sleeptime = np.round( sweep_params["sweep_avgs"] / self.sample_rate * 1.1, decimals = 3 )
        _logger.debug( "sleep time for sweep is {0}".format(sleeptime) )

        step_times = []

        # acutally do the sweep - loop over LO frequencies, while saving time at lo_step
        try:
            sweepdirection = np.sign( np.diff(self.tl.sweep_lo_freqs) )[0] # +/- 1 for forward/backward - not used right now
            _logger.info('Sweeping LO %3.1f kHz around %3.3f MHz in %1.1f kHz steps' % (np.ptp(self.tl.sweep_lo_freqs/1.e3),
                                                                                        np.mean(self.tl.sweep_lo_freqs/1.e6),
                                                                                        np.median(np.diff(self.tl.sweep_lo_freqs)) / 1.e3))
            for ix, lo_freq in enumerate(self.tl.sweep_lo_freqs):

                if self.loswitch == True: # only switch if the muxchannel is configured to do so
                    self.synth_lo.frequency = lo_freq
                else:
                    # wait until synth_lo.frequency => lo_freq
                    t0 = time.time()
                    while self.synth_lo.frequency <= lo_freq and time.time() <= t0 + sleeptime :
                        time.sleep(sleeptime / 100.)
                pytime = self.writer_daemon.pytime.value
                step_times.append( pytime )
                #print "lo stepped at ", pytime
                #_logger.info('LO stepped to ' + str(lo_freq/1.e6))
                # check the stop event to break out of the loop
                if stop_event.is_set():
                    break
                #pbar.set_description(cm.BOLD + "LO: %i" % lo_freq + cm.ENDC)
                time.sleep(sleeptime)

                # should we wait for a number of samples per frequency? can sample self.current_dirfile.nframes

            #pbar.close()
            #print cm.OKGREEN + "Sweep done!" + cm.ENDC
        except KeyboardInterrupt:
            pass

        # sweep has finished, pause the writing and continue to process the data
        #time.sleep(2.5)
        _logger.debug( "pausing writing at ", self.writer_daemon.pytime.value )

        self.writer_daemon.pause_writing()

        #  get only the indexes that were swept
        lofreqs_that_were_swept = self.tl.sweep_lo_freqs[np.arange(ix+1)]
        #lofreqs_that_were_swept = self.tl.sweep_lo_freqs
        # Back to the central frequency
        if self.loswitch == True:
            self.synth_lo.frequency = self.tl.lo_freq

        # save lostep_times to current timestream dirfile (why are these not arrays?)
        self.current_dirfile.add( _gd.entry(_gd.RAW_ENTRY, "lo_freqs"    , 0, (_gd.FLOAT64, 1) ) )
        self.current_dirfile.add( _gd.entry(_gd.RAW_ENTRY, "lostep_times", 0, (_gd.FLOAT64, 1) ) )

        self.current_dirfile.putdata("lo_freqs"    , np.ascontiguousarray( lofreqs_that_were_swept, dtype = np.float64 ))
        self.current_dirfile.putdata("lostep_times", np.ascontiguousarray( step_times,              dtype = np.float64 ))

        # on mac, we need to close and reopen the dirfile to flush the data before reading back in the data
        # - not sure why, or if this is a problem on linux - it doesn't hurt too much though
        self.current_dirfile.close()
        self.current_dirfile = _gd.dirfile(self.writer_daemon.current_filename, _gd.RDWR)

        #delay appears to be required to finish write/open operations before continuing
        time.sleep(0.5)
        # analyse the raw sweep dirfile and write to disk
        self.reduce_and_write_sweep_data(self.current_dirfile)

    def _configure_sweep_and_start_writing(self, **sweep_kwargs):

        valid_kwargs = ["sweep_span", "sweep_step", "sweep_avgs", "save_data"]

        # parse the keyword arguments
        timeout    = np.int32  ( sweep_kwargs.pop("timeout", 2.) )
        sweep_span = np.float32( sweep_kwargs.pop("sweep_span", self.ROACH_CFG["sweep_span"]) )
        sweep_step = np.float32( sweep_kwargs.pop("sweep_step", self.ROACH_CFG["sweep_step"]) )
        sweep_avgs = np.int32  ( sweep_kwargs.pop("sweep_avgs", self.ROACH_CFG["sweep_avgs"]) )

        # configure the lo_frequencies for the sweep. Assumes the central LO frequency give in mc.tonelist.lo_freq
        self.tl.calc_sweep_lo_freqs(sweep_span, sweep_step)

        # add an additional filename suffix if neccessary
        filename_suffix = sweep_kwargs.pop("filename_suffix", "")

        # not used at the moment - all data is saved
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

        # create new dirfile and set it as the active file. Note that data writing is off by default.
        self.set_active_dirfile( filename_suffix = "sweep" + filename_suffix )
        # alias to current dirfile for convenience
        self.current_dirfile = self.writer_daemon.current_dirfile

        # Set LO to first freq
        self.synth_lo.frequency = self.tl.sweep_lo_freqs[0]

        # start writing data to file...
        _logger.debug( "starting to write data" )
        self.writer_daemon.start_writing()

        # and wait until writing starts
        t0 = time.time()
        while not self.writer_daemon.is_writing:
            time.sleep(0.01)
            if time.time() >= t0 + timeout : # wait for 2 seconds
                _logger.error( "timeout waiting for writer daemon to start writing. check to see if something went wrong." )
                return
            else:
                continue
        # return the span, step and navgs for the sweep
        return {'sweep_span': sweep_span,
                'sweep_step': sweep_step,
                'sweep_avgs': sweep_avgs}

    def reduce_and_write_sweep_data(self, rawsweep_dirfile, startidx = 0, stopidx = None, save_data = True):
        """Function to read a raw sweep file (i.e. a timestream of I and Q), reduce the data and create an analyzed sweep dirfile.

        Parameters
        ----------
        rawsweep_dirfile: pygetdata.dirfile
            Handle to an open dirfile instance that contains the raw sweep data. Checks are made to ensure that
            the fields (lo_times, python_timestamp) required to reduce the data are present.


        """

        # Check that the dirfile is open, and that the fields are present
        reqfields = {"lostep_times", "python_timestamp"}
        assert reqfields.issubset( set( rawsweep_dirfile.field_list() ) ) , "it doesn't look like that {0} is a raw sweep file".format(rawsweep_dirfile.name)

        # with the raw sweep data available, create the derived sweep file and save to the current dirfile (from lib_dirfiles)
        lotimes = self.current_dirfile.getdata( "lostep_times" )
        ptimes  = self.current_dirfile.getdata( "python_timestamp" ) # way to get the python_timestamp field with knowing any field suffix
        lofreqs = self.current_dirfile.getdata( "lo_freqs" )

        # align LO steps with python timestreams
        idxs = np.searchsorted(ptimes, lotimes)[1:] # miss out the first point (should always be 0)

        timestr_fmt = self.GENERAL_CFG['default_datafilename_format']
        # get the filename and extract the datetime string to match the raw sweep file
        dt = _dateutil.parser.parse(os.path.basename(rawsweep_dirfile.name), fuzzy=True)
        swpdfname = os.path.join( os.path.dirname(rawsweep_dirfile.name), dt.strftime( timestr_fmt ) )

        # create new sweep dirfile and keep hold of it
        swpdf = _lib_dirfiles.generate_sweep_dirfile( self.roachid, swpdfname, self.tl.tonenames, numpoints = len(lotimes))

        #print lotimes, lofreqs
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
                    _logger.warning ( "the field name {0} doesn't appear to be of the correct format".format(field) )
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

        # save the data to the new sweep dirfile
        swpdf = _lib_dirfiles.write_sweepdata_to_sweepdirfile(swpdf, self.tl.bb_freqs, \
                                                            lofreqs,
                                                            self.tl.tonenames,\
                                                            sweep_data_dict)
        # add metadata
        _lib_dirfiles.add_metadata_to_dirfile(swpdf, {"raw_sweep_filename": self.current_dirfile.name})
        #
        # # load the sweep into mc.sweep
        self.sweep.load_sweep_dirfile(swpdf)

    # def test_loop(self):
    #     step_times = []
    #     sleeptime = 1.
    #     #self.set_active_dirfile()
    #     #self.writer_daemon.start_writing()
    #     try:
    #         for lo_freq in self.tl.sweep_lo_freqs:
    #             self.synth_lo.frequency = lo_freq
    #             step_times.append( time.time() )
    #             time.sleep(sleeptime)
    #
    #     except KeyboardInterrupt:
    #         print "out of loop"
    #     #self.writer_daemon.pause_writing()

    def retune_kids(self, force_first_sweep = False, findf0_method = "maxspeed", **swpkwargs):
        """
        Function to retune resonators.  UNDER DEVELOPMENT - USE SCRIPT FOR NOW
        """
        _logger.info('starting resonator tuning process on {0}'.format(self.roachid) )
        # if we haven't already swept, do the first sweep
        if not self.sweep.dirfile or force_first_sweep == True:
            # sweep
            self.sweep_lo(**swpkwargs)

        # analyse sweep - tone_freqs = None returns parameters at that F0, and can be used to find F0s
        self.sweep.calc_sweep_cal_params( tonefreqs      = None, \
                                            method       = findf0_method, \
                                            exclude_idxs = self.tl.blindidxs )
        # write the cal parameters to file - is this ever used?
        self.sweep.write_sweep_cal_params(overwrite = True)
        # use method to find F0s from KID rountines
        _logger.debug( "new f0s found- {0}".format(self.sweep.calparams['f0s']) )

        # change frequencies in self.tl
        self.tl.bb_freqs = self.sweep.calparams['f0s'] - self.tl.lo_freq

        # write to qdr (optional)
        self.write_freqs_to_fpga( auto_write = True )

        # resweep with new tones
        self.sweep_lo(**swpkwargs)

        # recalculate sweep cal params, this time with the written tones
        self.sweep.calc_sweep_cal_params( tonefreqs      = self.tl.rf_freqs, \
                                            method       = findf0_method, \
                                            exclude_idxs = self.tl.blindidxs )
        # write these to the new sweep file
        self.sweep.write_sweep_cal_params(overwrite = True)

    #@profile
    def start_stream(self, **stream_kwargs):
        """

        Function to use to stream data to disk.

        Valid keyword arguements:
            filename_suffix - str, default ""
            stream_time - numeric value for length of time to stream data for, default None - streams forever

        """
        #dirfilename - give path to a dirfile to use and append to an existing file

        filename_suffix = stream_kwargs.pop("filename_suffix", "")
        stream_time     = stream_kwargs.pop("stream_time", None)
        save_data       = stream_kwargs.pop("save_data", True) # currently not used
        dont_ask        = stream_kwargs.pop("dont_ask", False)
        symlink         = stream_kwargs.pop("symlink_sweep", True)

        dirfile_name = stream_kwargs.pop("dirfilename", "") # allow the user to pass in and append to an existing dirfile

        # check that sweep exists - warn if not and give option to proceed
        if self.sweep.dirfile is None:
            if dont_ask==False:
                response = raw_input(" no sweep file available - limited functionality available - Proceed? [y/n] ")
                if response == "n":
                    return

            _logger.warning( "no sweep file found - continuing with limited functionality " )

        # create a new dirfile for the observation
        self.set_active_dirfile( dirfile_name = dirfile_name, filename_suffix = filename_suffix )

        if isinstance( self.sweep.dirfile , _gd.dirfile ):
            # add sweepdirfile as a new fragment to the new dirfile
            _lib_dirfiles.add_subdirfile_to_existing_dirfile( self.sweep.dirfile, self.current_dirfile,
                                                            namespace = "sweep",
                                                            symlink=symlink )
            # update stream calibration parameters from sweep
            self.sweep.write_stream_cal( self.current_dirfile )

        # alias to current dirfile for convenience
        self.current_dirfile = self.writer_daemon.current_dirfile

        _logger.info( "starting to write data on {0}".format( self.roachid ))
        self.writer_daemon.start_writing()

        # wait until writing starts and timeout after 2 seconds
        tnow = time.time()
        while not self.writer_daemon.is_writing:
            time.sleep(0.1)
            if time.time() - tnow > 2:
                _logger.error( "waiting for response from writer_daemon has timed out." )
                break
            else:
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
            _logger.info( "writer doesn't appear to be running. Nothing done." )

    def shutdown(self):
        """Shutdown procedure for the roach interface"""

        # terminate writer daemon threads
        self.writer_daemon.terminate()

        # close all local file descriptors
        self._srcfile.close()

        try:
            self.current_dirfile.close()
            self.sweep.dirfile.close()

            if self.loswitch == True:
                self.synth_lo.device.close()
                self.synth_clk.device.close()

        except AttributeError:
            pass
        # close hardware connections
        if self.ri.fpga:
            #self.ri.fpga._disconnect()
            #updated for casperfpga==0.1.1
            self.ri.fpga.transport._timeout = 0.0
            self.ri.fpga.transport.disconnect()



class muxChannelList(object):

    def __init__(self, channel_list,channel_nums=None):

        
        channel_list = list(np.atleast_1d(channel_list))
        _logger.debug("initialising muxChannelList with channel list {0}".format( channel_list ) )

        assert isinstance(channel_list, (list, tuple)) and len(channel_list) > 0 , "input {0} not recognised".format( type(channel_list) )

        self.channels = channel_list
        
        num_chans = 0
        # determine if the elements of the list are instantiated muxChannel objects
        if all( [isinstance(el, muxChannel) for el in channel_list]):
            _logger.debug("found a list of existing muxchannels with roachids: {0}".format( [el.roachid for el in channel_list] ) )

        elif set(channel_list).issubset(self.channels):
            # create the muxchannels
            for roachid in channel_list:
                _logger.info("initialising mux channel - {roachid} ".format( roachid=roachid ) )
                setattr( self, roachid, muxChannel(roachid) )
                num_chans+=1
        
        self.channel_nums = channel_nums
        if channel_nums is None:
            self.channel_nums = range(num_chans)

    def __getitem__(self,channel):
        if self.channel_nums is None:
            pass
        else:
            if type(channel)==int:
                return getattr(self, self.channels[self.channel_nums.index(channel)])
            elif type(channel)==str:
                return getattr(self, self.channels[self.channels.index(channel)])
    
    def __iter__(self):
        if self.channel_nums is None:
            return (getattr(self,roachid) for roachid in self.channels)
        else:
            return (self[chnum] for chnum in self.channel_nums)

    def _verify_channel_list_valid(self, channel_list):
        assert set(channel_list).issubset(self.channels), "channels given are not valid {0}".format(set(channel_list).difference(self.channels))
        return True

    def init_channel_list(self, interactive=True):
        """Function to initialise the current channel list"""
        assert len(self.channels) > 0, "channel list appears to be empty"

        # assert all hardware is connected and working
            # check firmware loaded
            # check synth_los are all connected and respond
            # check attenuator objects respond


        # check toneslists are all loaded

        # write tones to qdr (in parallel)

        # confirm packets streaming on all roaches

        # return

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

            handle_to_atten = getattr( getattr( self, roachid  ), "atten_in")

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

    def retune_kids(self, exclude=[]):
        # run the retune script on all of the roaches
        pass

    def start_stream_multi(self, channels_to_stream, *stream_args):
        pass
        # stream all

    def stop_stream_multi(self, channels_to_stream, *stream_args):
        pass

    def shutdown_all(self, which = None):
        for roachid in self.channels:
            try:
                getattr(self, roachid).shutdown()
            except:
                _logger.exception("shutdown not successful.")

    def plot_sweeps(self):
        pass
        # function to call visualisation to plot all the sweeps in a single sindow?


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
# - This should then return a list of the roach interface objects, with everything initialised and running, to be used
# for subsequent tasks (e.g. biasing, streaming...etc)


# logging





























class test_mclist(object):
    """
    NOT FULLY TESTED

    An adaption of the muxChannelList class above.

    Trying to run muxChannels in parallel.

    Constructed with a list of muxChannel.roachid strings.

    Does not inherit from list, but has __iter__ and __getitem__ for list-like behaviour.

    Holds a 'list' of muxChannels, indexable by name or number.

    Channel number can be set arbitrarily on construction, does not have to be 0,1,2,3...

    Pass the name of a muxChannel.method as a string to self.call_mc_method_in_parallell to run that method on all muxChannels in the list in a thread pool.

    Any args and/or kwargs are forwarded to the all of the muxChannel.method

    Currently only able to pass the same args/kwargs to all muxChannels

    muxChannel dependent args will need to passed in and run in serially in a loop.

    Tested so far:
        test_mclist.call_mc_method_in_parallel('initialise_hardware')
        test_mclist.call_mc_method_in_parallel('initialise_fpga',force_reupload=True)
        test_mclist.call_mc_method_in_parallel('write_freqs_to_fpga',auto_write=True)
        test_mclist.call_mc_method_in_parallel('sweep_lo')
        test_mclist.call_mc_method_in_parallel('sweep_lo')
        test_mclist.call_mc_method_in_parallel('start_stream',dont_ask=True,stream_time=duration) 
        test_mclist.call_mc_method_in_parallel('start_stream',dont_ask=True) 
        test_mclist.call_mc_method_in_parallel('stop_stream',dont_ask=True) 

    Probably going to have to whitelist desired methods as not all should be allowed to be called.

    Also, cannot access methods of attributes eg muxChannel.sweep.plot_sweep etc...

    """
    def __init__(self, channel_list,channel_nums=None):

        
        channel_list = list(np.atleast_1d(channel_list))
        _logger.debug("initialising muxChannelList with channel list {0}".format( channel_list ) )

        assert isinstance(channel_list, (list, tuple)) and len(channel_list) > 0 , "input {0} not recognised".format( type(channel_list) )

        self.channel_names = channel_list
        self.num_channels  = len(channel_list)
        
        self.channel_nums  = channel_nums
        if self.channel_nums is None:
            self.channel_nums = range(self.num_channels)
        
        #################################################################################
        ##start the muxChannels in serial
        
        #self._mclist = []
        #for ch in self.channel_names:
            #mc=muxChannel(ch)
            #self._mclist.append(mc)
            #setattr( self, ch, mc )
        
        #################################################################################
        ##start the mux channels in parallel:
        
        mp_pool = _multiprocessing_pool.ThreadPool( processes = self.num_channels )
        res=[]
        for ch in self.channel_names:
            _logger.info("initialising mux channel - {roachid} ".format( roachid=ch ) )
            res.append(mp_pool.apply_async(muxChannel, (ch,) ) )
        
        while not all([r.ready() for r in res]): time.sleep(0.1)
        mp_pool.close()
        mp_pool.join()
        
        mux_channels = []
        for r in range(len(res)):
            try:
                mux_channels.append(res[r].get())
            except Exception as e:
                print "EXCEPTION IN THREAD:",self.channel_names[r],'\n',e.__repr__()
                mux_channels.append(e)
        
        self._mclist = []
        for ch, mc in zip(self.channel_names,mux_channels):
            if isinstance(mc,Exception):
                raise mc
            setattr( self, ch, mc )
            self._mclist.append(mc)
        #################################################################################


    def __getitem__(self,channel):
        if type(channel)==int:
            return getattr(self, self.channel_names[self.channel_nums.index(channel)])
        elif type(channel)==str:
            return getattr(self, self.channel_names[self.channel_names.index(channel)])
    
    def __iter__(self):
        return (self[chnum] for chnum in self.channel_nums)

    def _verify_channel_list_valid(self, channel_list):
        assert set(channel_list).issubset(self.channel_names), "channels given are not valid {0}".format(set(channel_list).difference(self.channel_names))
        return True

    def do_in_parallel(self,methods,meth_args,meth_kwargs):
        mp_pool = _multiprocessing_pool.ThreadPool( processes = len(self.channel_names) )
        
        res=[]
        for method,args,kwargs in zip(methods,meth_args,meth_kwargs):
            res.append(mp_pool.apply_async(method, args, kwargs) )

        while not all([r.ready() for r in res]):
            time.sleep(0.5)
            #plt.pause(0.5)

        mp_pool.close()
        mp_pool.join()
        
        ret=[]
        for r in range(len(res)):
            try:
                ret.append(res[r].get())
            except Exception as e:
                print "EXCEPTION IN THREAD:",self.channel_names[r],':\n',e.__repr__()
                ret.append(e)
        print ret
        for r in ret:
            if isinstance(r, Exception):
                raise r
        return ret

    def call_mc_method(self,mc,method,*args,**kwargs):
        m = getattr(self[mc],method)
        return m(*args,**kwargs)

    def call_mc_method_in_parallel(self, methodname, *args, **kwargs):
        methods = [getattr(self._mclist[j],methodname) for j in range(self.num_channels)]
        return self.do_in_parallel(methods,[args]*len(methods),[kwargs]*len(methods))
    
    
    
    
    
        