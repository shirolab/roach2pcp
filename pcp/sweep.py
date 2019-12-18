import os as _os, numpy as _np, time as _time, shutil as _shutil

from .lib import lib_dirfiles as _lib_dirfiles
from .kid import resonator_routines as _resonator_routines
from .configuration import general_config, roach_config

from copy import deepcopy

import logging as _logging
_logger = _logging.getLogger(__name__)

# pcp Sweep object

# loads data from pcp sweep file
# calculate all the parameters
# write sweep cal parameters to the sweep dirfile

histdictkeys = [ 'filename', \
                'rffreqs', 'bbfreqs', 'lofreqs',\
                'iqdata', '']

class pcpSweep(object):

    def __init__(self, dirfile = None):
        """
        A pcpSweepdata object. Used to contain and manipulate the current sweep data.

        """
        # set up class attributes

        self.name = None
        self.dirfile = dirfile

        self._bb_freqs = None
        self.lo_freqs  = None

        self._lo_freq  = None
        self.rf_freqs  = None

        self.tonefreqs = None
        self.tonenames = None

        self.data_fields = None
        self.data        = None

        self.calparams = None
        self.caldata   = None

        self.history       = []
        # read in dirfile if given
        if dirfile:
            self.load_sweep_dirfile(dirfile)
        else:
            _logger.warning("No sweep dirfile loaded. Use load_sweep_dirfile(dirfile) to load data")

        self.filter_dict = {} # dictionary for a filter used to smooth the calibation data

    def load_sweep_dirfile(self, dirfile, auto_analyse = False):
        """

        Function to load a dirfile into the sweep dirfile.

        """
        # check dirfile is a valid sweep file
        assert _lib_dirfiles.check_valid_sweep_dirfile(dirfile), "{0} doesn't appear to be a valid pcp sweep file".format(dirfile)

        # if data exists, save a copy to the history
        if self.dirfile is not None and _lib_dirfiles.is_dirfile_valid(self.dirfile):
            _logger.info("previous data appears to exist - saved a copy of {0} to history".format(_os.path.basename(self.dirfile.name)))
            #self.store_sweep()

        self.dirfile = dirfile
        self.name = _os.path.basename(dirfile.name)
        self.get_data()

        if auto_analyse:
            self.calc_sweep_cal_params()

    def get_data(self):
        """
        Function to return the data from the sweep dirfile.

        """
        assert self.dirfile, "no dirfile loaded. Try loading new dirfile and try again."

        # sweep_data_fields = filter(lambda x: x.startswith("sweep."), self.dirfile.entry_list())
        sweep_data_fields = _lib_dirfiles.get_fields_in_fragment(self.dirfile, "format", exclude_index = True) # get the main fragment

        self.tonenames = _np.array(self.dirfile.get_sarray( sweep_data_fields.pop(sweep_data_fields.index('tonenames') )))
        self._bb_freqs = self.dirfile.get_carray( sweep_data_fields.pop(sweep_data_fields.index('bb_freqs') ))
        self.lo_freqs  = self.dirfile.get_carray( sweep_data_fields.pop(sweep_data_fields.index('lo_freqs') ))

        self._lo_freq  = self.lo_freqs[(self.lo_freqs.shape[0]-1)/2]
        self.rf_freqs  = _np.repeat(self._bb_freqs[:, _np.newaxis], self.lo_freqs.shape[0], axis=1) + self.lo_freqs

        self.tonefreqs = self._bb_freqs + self._lo_freq
        #self.data_fields = [s.split(".")[-1] for s in sweep_data_fields]
        self.data        = _np.array( [self.dirfile.get_carray(fc) for fc in self.tonenames] )

        #calparam_fields = filter(lambda x: x.startswith("calparam."), self.dirfile.entry_list())
        calparam_fields = _lib_dirfiles.get_fields_in_fragment( self.dirfile, 'calparam' )
        self.calparams  = { s.split(".")[-1] : self.dirfile.get_carray(s) for s in calparam_fields}

        # self.calparam_fields = [s.split(".")[-1] for s in cal_param_fields]
        # self.calparams       =  _np.array( [self.dirfile.get_carray(fc) for fc in cal_param_fields] )

        caldata_fields = _lib_dirfiles.get_fields_in_fragment( self.dirfile, 'caldata' )
        self.caldata_fields = [s.split(".")[-1] for s in caldata_fields]
        self.caldata        =  _np.array( [self.dirfile.get_carray(fc) for fc in caldata_fields] )

        # caldata_fields = filter(lambda x: x.startswith("caldata."), self.dirfile.entry_list())
        # self.caldata_fields = [s.split(".")[-1] for s in cal_data_fields]
        # self.caldata        =  _np.array( [self.dirfile.get_carray(fc) for fc in cal_data_fields] )

        # anything else?

    def store_sweep(self):
        """Function to store a copy """
        self.history.append( deepcopy(self) )

    def calc_sweep_cal_params(self, tonefreqs = None, method = "maxspeed", exclude_idxs=[]):
        """
        Function to calculate the calibration parameters from the currently loaded sweep data and filter parameters.

        Set tonefreqs to calculate the sweep parameters at those frequencies. Otherwise, this function will return the
        true F0 and the parameters at those F0s, which may differ from the written tones.
        """
        assert method in ['maxspeed', 'mins21'], "Given method {0} for finding resonant frequencies not valid.".format(method)

        _logger.info("Calculating new set of calibration parameters. To restore original parameters values, use self.get_data()."\
                    "Use self.write_sweep_cal_params to write the new calibration parameters to file to be used in streaming.")

        # add filter parameters here!
        assert self.data is not None, "there doesn't appear to be any sweep data available. Do a sweep, or load an existing file and rerun"

        calparams, caldata = _resonator_routines.calc_sweep_cal_params(self.rf_freqs, \
                                                                                self.data.real, \
                                                                                self.data.imag, \
                                                                                tone_freqs = tonefreqs )
        # get the indexes of the data we want to analyse (default all of them )
        allidxs = _np.arange( len(self.data), dtype=_np.int )
        idxstoanalyse = list( set(allidxs).difference(exclude_idxs) )

        if (self.calparams is not None) and (self.caldata is not None):
            self.caldata[ idxstoanalyse ]    = caldata[ idxstoanalyse ]
            for key, val in self.calparams.items():
                self.calparams[key][ idxstoanalyse ]  = calparams[key][ idxstoanalyse ]
        else:
            self.caldata   = caldata
            self.calparams = calparams

    def set_filter_params(self):
        pass

    def write_sweep_cal_params(self, overwrite = False):
        """ Writes a new set of calibration parameters to the current dirfile. The overwrite switch allows the user to overwrite
        the existing parameters in the file. Overwriting is generally discouraged, but is used when writing data after creation of the
        sweep file. Default is False. """

        _, cal_frag_idx = _lib_dirfiles.check_fragment_valid(self.dirfile, "calparam")

        if not overwrite:
            # copy the calibration fragment file and append a unique datetime stamp
            _shutil.copy( self.dirfile.fragment(cal_frag_idx).name, \
                        "_".join( (self.dirfile.fragment(cal_frag_idx).name, _time.strftime(general_config["default_datafilename_format"]))) \
                        )

        self.write_sweep_cal_params_todisk(self.dirfile, self.calparams, dict(zip(self.caldata_fields, self.caldata)) )
        #_lib_dirfiles.write_sweep_cal_params(cal_params, cal_data)

    def write_sweep_cal_params_todisk(self, dirfile, calparams, caldata_dict):

        assert _lib_dirfiles.is_dirfile_valid(dirfile)

        assert isinstance(caldata_dict, dict), "cal data is required to be in a dictionary with tonename: caldata as key: value"

        # check that sweep cal fragments are available
        is_calparamfrag_valid, calparamfrag = _lib_dirfiles.check_fragment_valid(dirfile, "calparam")
        is_caldatafrag_valid,  caldatafrag  = _lib_dirfiles.check_fragment_valid(dirfile, "caldata")

        if not any([is_calparamfrag_valid, is_caldatafrag_valid]):
            _logger.warning("there doesn't appear to be a calibration fragment. Calibration parameters not written.")
            return

        calparam_ns = dirfile.fragment(calparamfrag).namespace
        caldata_ns  = dirfile.fragment(caldatafrag).namespace

        for calparam_field, calparam in calparams.items():
            dirfile.put_carray( ".".join([calparam_ns, calparam_field]) , calparam)

        for tonename, caldata in caldata_dict.items():
            dirfile.put_carray(".".join([caldata_ns, tonename]), caldata)

        dirfile.flush()

    def write_stream_cal(self, stream_dirfile):
        """Function to write the current calibration parameters to the ones required by the stream dirfiles. """

        assert _lib_dirfiles.is_dirfile_valid(stream_dirfile)

        # calparams to write for dff0 conversion
        is_calfrag_valid, calfrag = _lib_dirfiles.check_fragment_valid(stream_dirfile, "calibration")
        assert is_calfrag_valid, "calibration fragment appears to be invalid"
        cal_ns = stream_dirfile.fragment(calfrag).namespace

        calfields = _lib_dirfiles.get_fields_in_fragment(stream_dirfile, 'calibration')
        assert set(calfields).issubset( _lib_dirfiles.DERIVED_CALPARAM_FIELDS ), "calfields don't appear to match what is expected; {0} - {1}".format( calfields, _lib_dirfiles.DERIVED_CALPARAM_FIELDS)

        # these need to be in the same order as _lib_dirfiles.DERIVED_CALPARAM_FIELDS
        # currently = ['f0s','didf_sumdidq2', 'dqdf_sumdidq2', 'i0_didf_sumdidq2', 'q0_dqdf_sumdidq2']
        f0s = self._bb_freqs + self._lo_freq
        caldatalist = [f0s, \
                        self.calparams['didf0'] / self.calparams['didq2'] / f0s,\
                        self.calparams['dqdf0'] / self.calparams['didq2']/ f0s,\
                        self.calparams['didf0'] * self.calparams['i0'] / self.calparams['didq2'] / f0s,\
                        self.calparams['dqdf0'] * self.calparams['q0'] / self.calparams['didq2'] /f0s ]

        for calfield, calval in zip(_lib_dirfiles.DERIVED_CALPARAM_FIELDS, caldatalist):
            stream_dirfile.put_carray(".".join([cal_ns, calfield]), calval)

        # write the derived paramters to disk
        stream_dirfile.flush()


    def calc_new_frequencies(self):
        pass

    def plot_sweep(self, sweeplist, sortfreqs = False):
        from . import visualisation as vis

        #self.ip = vis.pcpInteractivePlot( sweeplist, sortfreqs=False)



        # how complicated do we want to get
        #
        # buttons for each KID would be nice?
        # ailitiy to browse with arrow keys
        # ability to modify data on the fly

        # "tabs" for each roach? - this would be in the muxChannelList
        # https://stackoverflow.com/questions/37346845/tabbed-window-for-matplotlib-figures-is-it-possible
