import numpy as _np, time as _time, shutil as _shutil

from .lib import lib_dirfiles as _lib_dirfiles
from .kid import resonator_routines as _resonator_routines
from .configuration import general_config, roach_config

import logging as _logging
_logger = _logging.getLogger(__name__)

# pcp Sweep object

# loads data from pcp sweep file
# calculate all the parameters
# write sweep cal parameters to the sweep dirfile

class pcpSweep(object):

    def __init__(self, roachid, dirfile = None):
        """
        A pcpSweepdata object. Used to contain and manipulate the current sweep data.

        """
        # set up class attributes

        self._bb_freqs = None
        self.lo_freqs  = None

        self._lo_freq  = None
        self.rf_freqs  = None

        self.data_fields = None
        self.data        = None

        self.calparam_fields = None
        self.calparams       = None

        self.caldata_fields = None
        self.caldata        = None

        # read in dirfile if given
        if dirfile:
            self.load_sweep_dirfile(dirfile)
        else:
            self.dirfile = None
            _logger.warning("No sweep dirfile loaded. Use load_sweep_dirfile(dirfile) to load data")

        self.filter_dict = {} # dictionary for a filter used to smooth the calibation data

    def load_sweep_dirfile(self, dirfile):
        """

        Function to load a dirfile into the sweep dirfile.

        """
        # check dirfile is a valid sweep file
        assert _lib_dirfiles.check_valid_sweep_dirfile(dirfile), "{0} doesn't appear to be a valid pcp sweep file".format(dirfile)

        self.dirfile = dirfile
        self.get_data()

    def get_data(self):
        """
        Function to return the data from the sweep dirfile.

        """
        assert self.dirfile, "no dirfile loaded. Try loading new dirfile and try again."

        # sweep_data_fields = filter(lambda x: x.startswith("sweep."), self.dirfile.entry_list())
        sweep_data_fields = _lib_dirfiles.get_fields_in_fragment(self.dirfile, "format", exclude_index = True) # get the main fragment

        self._bb_freqs = self.dirfile.get_carray( sweep_data_fields.pop(sweep_data_fields.index('bb_freqs') ))
        self.lo_freqs  = self.dirfile.get_carray( sweep_data_fields.pop(sweep_data_fields.index('lo_freqs') ))

        self._lo_freq  = self.lo_freqs[(self.lo_freqs.shape[0]-1)/2]
        self.rf_freqs  = _np.repeat(self._bb_freqs[:, _np.newaxis], self.lo_freqs.shape[0], axis=1) + self.lo_freqs

        self.data_fields = [s.split(".")[-1] for s in sweep_data_fields]
        self.data        = _np.array( [self.dirfile.get_carray(fc) for fc in sweep_data_fields] )

        cal_param_fields = filter(lambda x: x.startswith("cal."), self.dirfile.entry_list())
        self.calparam_fields = [s.split(".")[-1] for s in cal_param_fields]
        self.calparams       =  _np.array( [self.dirfile.get_carray(fc) for fc in cal_param_fields] )

        cal_data_fields = filter(lambda x: x.startswith("caldata."), self.dirfile.entry_list())
        self.caldata_fields = [s.split(".")[-1] for s in cal_data_fields]
        self.caldata        =  _np.array( [self.dirfile.get_carray(fc) for fc in cal_data_fields] )

        # anything else?

    def calc_sweep_cal_params(self):
        """
        Function to calculate the calibration parameters from the currently loaded sweep data and filter parameters.

        """

        _logger.info("Calculating new set of calibration parameters. To restore original parameters values, use self.get_data().\
                    Use self.write_sweep_cal_params to write the new calibration parameters to file to be used in streaming.")

        # add filter parameters here!

        self.calparams, self.caldata = _resonator_routines.calc_sweep_cal_params(self.rf_freqs, \
                                                                                self.data.real, \
                                                                                self.data.imag, \
                                                                                tone_freqs = self._bb_freqs + self._lo_freq )
    def set_filter_params(self):
        pass

    def write_sweep_cal_params(self, overwrite = False):
        """ Writes a new set of calibration parameters to the current dirfile. The overwrite switch allows the user to overwrite
        the existing parameters in the file. Overwriting is generally discouraged, but is used when writing data after creation of the
        sweep file. Default is False. """

        _, cal_frag_idx = _lib_dirfiles.check_fragment_valid(self.dirfile, "calibration")

        if not overwrite:
            # copy the calibration fragment file and append a unique datetime stamp
            _shutil.copy( self.dirfile.fragment(cal_frag_idx).name, \
                        "_".join( (self.dirfile.fragment(cal_frag_idx).name, _time.strftime(general_config["default_datafilename_format"]))) \
                        )

        _lib_dirfiles.write_sweep_cal_params(self.dirfile, self.calparams, dict(zip(self.caldata_fields, self.caldata)) )
        #_lib_dirfiles.write_sweep_cal_params(cal_params, cal_data)

    def calc_new_frequencies(self):
        pass

    def plot_sweep(self):
        pass
