"""
toneslist class for handling everything to do with tones
"""

### === Importation === ###

import os as _os, csv as _csv, datetime as _dt, logging as _logging, time as _time, yaml as _yaml
import numpy as _np, pandas as _pd, matplotlib.pyplot as _plt

_logger = _logging.getLogger(__name__)

from .configuration import ROOTDIR, AMPCORRDIR, TONELISTDIR, TONEHISTDIR, filesys_config, roach_config

def load_pcp_tonelist(tonelist_file):
	"""

	Function used to load in the pcp tonelist file, and return a standardised format
	that will be read in by the tonesList class.

	"""
	return

def get_tone_fields( tones ):
    """
    Function to return an array of field names for a tone list. Can be either a number, for a number of tones,
    or an array-type containing the required the fields that will be used in the dirfiles. If a number is given,
    then a default [K0000...K{ntones}] list will be generated.
    """

    tonetype = type(tones)
    if type(tones) in [int, _np.int32, _np.int64]:
        tones = _np.array( [ "K{kidnum:04d}".format(kidnum = i) for i in range(int(tones)) ]  )

    elif type(tones) in [list, _np.ndarray, _pd.Series]:
        tones = _np.array(tones, dtype = str) # convert type to string (will allow list of frequencies)

    elif type(tones) == Toneslist:
        tones = _np.array(tones.data.name, dtype = str)# convert type to string (will allow list of frequencies)

    else:
        raise TypeError( "Type of tones ({0}) is not recognised".format( type(tones) ) )

    return tones
#
def gen_tone_iq_fields(tones, namespace="", field_suffix=""):

	#field_suffix = "_" + field_suffix if field_suffix is not "" else ""
	namespace = namespace + "." if namespace is not "" else ""

	# get array of field names from either tonelist, or automatically generated
	field_names = _np.core.defchararray.add( "{namespace}".format(namespace=namespace), get_tone_fields(tones) )

	kid_fields_I = _np.core.defchararray.add(field_names, "_I{suffix}".format(suffix = field_suffix))
	kid_fields_Q = _np.core.defchararray.add(field_names, "_Q{suffix}".format(suffix = field_suffix))

	return kid_fields_I, kid_fields_Q

def write_tonelist_file(tonearray, outputfile):
	"""Simple function to write an array to a toneslist file.

	"""
	# check type of input array and convert to pandas dataframe
	if isinstance(tonearray, _np.ndarray) and len(tonearray.shape) == 1: #
		# create list of names
		datatowrite = _np.array([ ['K{0:04d}'.format(v) for v in _np.arange(len(tonearray))], \
						tonearray, _np.zeros_like(tonearray) ]).T
		datatowrite = _pd.DataFrame(data = datatowrite)

	elif isinstance(tonearray, Toneslist):
		datatowrite = tonearray.data

	datatowrite.to_csv(outputfile, sep='\t', index=False)

### === Toneslist class === ###

class Toneslist(object):
	# -- basic functionality --
	# read in an array of resonator frequencies (GHz)
	# convert to bb_freqs for writing to roach (need LO)
	# placement of blind tones
	# plot routines to visualise toneslist
	# include "phases"
	#	- random
	#	- other? Sam R has nice routines to reduce sideband leakage

	# include "amplitudes"
	#	- for each tone, specify a tone power (normalised to 1) --> used when writing to roach
	#	- have this connected to dBm bifurcation powers
	# calibration routines
		# - add functions to pass in a file of calibration data in order to offset tones

	# -- ideal functionality --
	# interactive modification of toneslist to include/exclude tones (code exists in kidpy by JW)
	# have a "loader" that allows anyone to write a loader function and provide an interface to a custom tonesfile format

	# -- sweep functionality --
	#
	_DTFMT = "%Y%m%d-%H%M%S"
	def __init__(self, roachid,
						loader_function = _pd.read_csv,\
						auto_load = True,\
						synth_res = 1.,\
						**loaderkwargs):
		"""
		Tonelist object for storing and manipulating a set of tones for a given a Roach.

		All frequencies should be in Hz.

		Parameters
		----------
		roachid : str
		  	A roachid string used to index the configuration files. Must be contained in pcp.ROACH_LIST

		loader_function : callable
			A callable function that is used to read in a tonelist file. This allows the user to write a function
			to load in a custom tonelist format.

			The signature lloader_function (filename, **loaderkwargs )  should at a minimum take a filename, and return a pandas dataframe
			with columns "name", "freq", "power". Currently, self.load_tonelist does handle returning of a single 1d array of frequencies.

			Default function is pandas.read_csv, which works well the the Cardiff and Chicago toneslist format

		auto_load : bool
		 	Allows the user to chose not to automatically load the tonelist specified in the configuration file. This will mainly be used
			for debugging and special use cases. Default is True.

			When True, the tonesfile filename given in the corresponding roach_config file.

		synth_res : float
			Frequency resolution of the synthesizer (Hz), used to constrain the available frequencies for the LO.
			Default = 1 Hz.

		**loaderkwargs : dict
			Any keyword arguments to be passed into the user defined loader function

		Methods
		----------

		self.list_tonelistdir - lists all files contained in the pcp.configuration.TONELISTDIR.

		self.find_optimum_lo - finds the optimum lo frequency for a given set of tones.

		self.place_blind_tones - not implmeneted yet

		self.plot_tonedata - simple plotting routine to visualise currently loaded tone data

		Examples
		--------

		Automatic reading

		>>> import pcp, pandas as pd
		>>> tl = pcp.toneslist.Toneslist("dummyroach", pd.read_csv)
		>>> tl.plot_tonedata()

		Manual reading

		>>> import pcp, pandas as pd
		>>> tl = pcp.toneslist.Toneslist("dummyroach", auto_load = False )
		>>> tl.loader_function = pd.read_csv
		>>> tl.load_tonelist( tl.list_tonelistdir()[0] )
		>>> tl.lo_freq = tl.find_optimum_lo()
		>>> tl.plot_tonedata()

		Manually adjust lo_freq

		>>> import pcp, pandas as pd
		>>> tl = pcp.toneslist.Toneslist("dummyroach", pd.read_csv)
		>>> tl.lo_freq = 100.e6
		>>> tl.plot_tonedata()

		"""

		# load config for given roachid
		self.roachid   = roachid
		self.ROACH_CFG = roach_config[self.roachid]

		# set usable bandwidth
		self._bandwidth = self.ROACH_CFG["max_pos_freq"] - self.ROACH_CFG["min_neg_freq"]

		self.synth_resolution = synth_res # resolution of the synthesizer in Hz

		# load the tonelist given in
		self.tonelistfile = _os.path.join(TONELISTDIR, self.ROACH_CFG["tonelist_file"])

		# get a handle to the tonehistdir
		self.tonehistdir = _os.path.join(TONEHISTDIR, self.roachid)
		self.tonehistory = {}
		self._load_tonehistdir()

		# get a handle to the ampcorr directory
		self.ampcorrdir = _os.path.join(AMPCORRDIR, self.roachid)
		# dictionary to store amplitude corrections (total points to the class method to calculate the product)
		self.ampcorr    = {"total": self._calcampcorr }
		self.ampcorrfiles = {}
		self._load_ampcorrdir()

		# check that loader function looks like a function
		assert( callable(loader_function) ) # this should probably go further down
		self.loader_function = loader_function

		self._counts = None

		# containers for tone data
		self.data 		 = None # full tonelist data, not intended to be modified
		self.blind_freqs = None # container for blind tones (if present)

		self.tonenames = None

		self.lo_freq     = None #
		self.rf_freqs    = None
		self.bb_freqs    = None

		self.amps   = None
		self.phases = None

		self.sweep_lo_freqs = None

		# load automatically if auto_load flag is set (default behaviour)
		if auto_load == True:
			# load tonelist - also finds optimum lo frequency for the newly loaded tonelist
			self.load_tonelist( self.tonelistfile, **loaderkwargs )
		else:
			_logger.info( """no data loaded. working in manual mode.
					use self.load_tonelist( tonefilename, **loaderkwargs) to load tone list and find optimum lo freq
					use self.lo_freq = ... to change the required lo frequency. This automatically modifies the bb_freqs
					""" )

	def _load_tonehistdir(self):
		""" Function to load and return the tonehistory """
		if self.tonehistdir:
			for tonefile in [f for f in _os.listdir(self.tonehistdir) if not f.startswith(".")]:
				name, ext = _os.path.splitext(tonefile)
				self.tonehistory[name] = _os.path.join(self.tonehistdir, tonefile)
		else:
			_logger.warning("no tonehistory directory given. limited functionality")

	def load_tonehistfile(self, datetime_tag, dont_ask = False):
		"""Load a file from the tonehistory directory. """

		# make sure datetime_tag exists
		assert datetime_tag in self.tonehistory.keys(), "given datatime tag is not in the history. available keys are: {0}".format(self.tonehistory.keys())

		# open and read the file
		with open(self.tonehistory[datetime_tag]) as fin:
			tonedict = _yaml.safe_load(fin)
			amps     = _np.array(tonedict['amps'])
			phases   = _np.array(tonedict['phases'])
			bb_freqs = _np.array(tonedict['freqs'])

		ask = False
		# check to see if current tonelist matches new tones by comparing number of tones and fractional shift in bb_freqs
		if len(self.tonenames) != len(amps) :
			warn = "Length of new tones does not appear to match the currently loaded toneslist -- "
			ask = True

		elif any( _np.abs( (bb_freqs - self.bb_freqs)/self.bb_freqs * 100 ) > 30.):
			warn = "Absolute positions of frequencies appear to be significantly different -- "
			ask = True

		if ask==True and dont_ask==False:
		    response = raw_input( warn + " Proceed? [y/n] ")
		    if response == "n":
		        return

		self.amps = amps; self.phases = phases; self.bb_freqs = bb_freqs
		_logger.info("new tones loaded from {0}".format( _os.path.basename( self.tonehistory[datetime_tag])) )
		_time.sleep(0.1)

	def write_tonehistfile(self):
		""" Write the current tone parameters to a timestamped .tone file in the tonehistdir for the given
		roachid. """

		assert all(((self.amps is not None),\
					(self.bb_freqs is not None),\
					(self.phases is not None) )), "amps,phases,freqs don't appear to be valid. Nothing done."

		timenow = _dt.datetime.now()
		datetag = _dt.datetime.strftime(timenow, self._DTFMT) + ".tone"

		data = {'date'  : _dt.datetime.strftime(timenow, '%Y%m%d'),\
				'time'  : _dt.datetime.strftime(timenow, '%H%m%S'),\
				'freqs' : self.bb_freqs.tolist(),\
				'amps'  : self.amps.tolist(),\
				'phases': self.phases.tolist() }

		outfname = _os.path.join( self.tonehistdir, datetag )
		with open(outfname, 'w') as outfile:
			_yaml.dump(data, outfile, default_flow_style=False)

		self._load_tonehistdir() # reload the tonehistory directory to include the new file

	@property
	def lo_freq(self):
		"""Get or set the frequency of the synthesizer. Units should all be in Hz."""
		return self._lo_freq

	@lo_freq.setter
	def lo_freq(self, lo_freq, reset_all = False):
		# coerce new value to given resolution
		lo_freq = self.synth_resolution * round( float(lo_freq) / self.synth_resolution) if lo_freq is not None else None
		# set the lo frequency
		self._lo_freq = lo_freq
		# recalculate bb_freqs
		self._update_frequencies(reset_all = False)
		# check tones fit in bandwidth?

	@property
	def bb_freqs(self):
		"""Get or set the frequency of the synthesizer. Units should all be in Hz."""
		return self._bb_freqs

	@bb_freqs.setter
	def bb_freqs(self, bb_freqs):
		# before setting the bb_freqs, check that they fit within the available bandwidth

		if isinstance(bb_freqs, (_np.ndarray, _pd.Series) ) :

			valid_idxs = self._get_valid_tone_idxs( bb_freqs )
			if len(valid_idxs) != len( bb_freqs ) :
				clipped_idxs = set( _np.arange( len(bb_freqs) ) ).difference(valid_idxs)
				_logger.warning( " some bb_freqs don't appear to fit into the bandwidth. The following have been clipped from bb_freqs:\n{0}".format(bb_freqs[clipped_idxs]) )

			# set only valid indices as bb_freqs
			self._bb_freqs   = bb_freqs[valid_idxs]
			self._valid_idxs = valid_idxs

		else:
			_logger.info ( "bb_freqs = {0}".format(bb_freqs) )
			self._bb_freqs = bb_freqs

	def _calcampcorr(self):
		return  _np.prod([a for k, a in self.ampcorr.items() if k not in ['total']], axis = 0)

	def _load_ampcorrdir(self):
		""" Function to load and return the tonehistory """
		if self.ampcorrdir:
			for acfile in [f for f in _os.listdir(self.ampcorrdir) if not f.startswith(".")]:
				name, ext = _os.path.splitext(acfile)
				self.ampcorrfiles[name.split("_")[0]] = _os.path.join(self.ampcorrdir, acfile)
		else:
			_logger.warning("no ampcorr directory given. limited functionality")

	def _read_ampcorrfile(self, datetag):
		assert datetag in self.ampcorrfiles.keys(), "given datatime tag is not present. available keys are: {0}".format(self.ampcorrfiles.keys())
		# open and read the file
		with open(self.ampcorrfiles[datetag], 'r') as fin:
			data = _yaml.safe_load(fin)

		# turn all values into np.arrays
		_ = [ data.update( {k: _np.array(v) }) for k,v in data.items()]

		# update the ampcorr dict with the new values from the file
		self.ampcorr.update( data )


	def _write_ampcorrfile(self, ignore_dups = False):
		"""Write the current ampcorr data to a numpy file. This is tied to the tonelist file..."""
		# get the data

		tonelistfname = _os.path.splitext (_os.path.basename(self.tonelistfile).lower())[0]

		# check to see if toneslist file already exists in here and warn?
		dups =  map( lambda x: tonelistfname in x, self.ampcorrfiles.values() )

		if any( dups ) and not ignore_dups:
			_logger.error ( "possible duplicate using same toneslist already exists. To continue, re-run with ignore_dups = True" )
			_time.sleep(0.1)
			return

		# filename? date + toneslistname?
		fname = _dt.datetime.strftime(_dt.datetime.now(), self._DTFMT) + "_" + tonelistfname + ".ac"

		# file format? human readable?
		data = dict( ( k, v.tolist() ) for (k, v) in self.ampcorr.items() if k not in ['total'] )

		with open( _os.path.join(self.ampcorrdir, fname), 'w') as outfile:
			_yaml.dump(data, outfile, default_flow_style=False)

		#update the current directory to include the new file
		self._load_ampcorrdir()

	def _update_frequencies(self, reset_all = False):
		"""
		Function to update the class variables that store the frequency lists "rf_freqs", "bb_freqs"...etc
		"""

		# fill in all the local variables for use later
		if self._lo_freq is not None:
			self.rf_freqs = _np.array( self.data['freq'] ) #if not baseband else data['freq'] + self.lo_freq
			self.bb_freqs = _np.array( self.data['freq'] - self.lo_freq )#if     baseband else data['freq'] - self.lo_freq
			if reset_all == True:
				self.amps     = None
				self.phases   = None

		else:
			_logger.warning( 'LO frequency must be set when loading RF frequencies.' )

	def _get_valid_tone_idxs(self, bb_freqs ):
		"""Check that a list of bb_freqs fits in the given bandwidth.

		Returns list of valid indexes
		"""
		if bb_freqs is not None:
 			return _np.argwhere( _np.abs( bb_freqs ) <= self._bandwidth/2. ).flatten()

	def list_tonelistdir(self, full_path = True):
		"""
		Utility function to return a list of all the files contained in a directory.
		Optionally allow full path to be returned (default).
		"""
		assert _os.path.exists(TONELISTDIR)
		tonefilelist = _os.listdir(TONELISTDIR)

		return map( lambda x: _os.path.join(TONELISTDIR, x), tonefilelist ) if full_path else tonefilelist

	def set_phases(self, how = 'random'):
		"""Function to calculate a set of set of phases to be used for the writing of the tones"""

		valid_how =  ['random', 'opposite', 'none']

		assert how in valid_how, "given 'which' parameter not recognised -- currently implemented = {0}".format(valid_how)
		assert self.bb_freqs is not None, "no tonelist loaded. load and try again"

		if how == "random":
			_np.random.seed()
			self.phases = _np.random.uniform(0., 2.*_np.pi, len(self.bb_freqs))

		elif how == "none":
			self.phases = _np.zeros_like(self.bb_freqs)

		elif how == "opposite":
			_logger.warning("opposite not currently implmented. defaulting to zeros")
			self.phases = _np.zeros_like(self.bb_freqs) # <-- need to implement opposite phase for improved sideband leakage

	def load_tonelist(self, tonelistfile = "", **loaderkwargs):
		if not self.loader_function:
			_logger.error( "no loader function available. set one and try again." )
			return

		# read the default file unless specified
		file_to_read = self.tonelistfile if not tonelistfile else tonelistfile

		# make sure that the file exists
		assert _os.path.exists(file_to_read), "Given filename {0} doesn't appear to exist.".format(file_to_read)

		# attempt to find the delimeter argument. Override if its given by user ( this then requires loader_function to take a "delimiter" keyword )
		with open(self.tonelistfile) as fin:
			delimiter = loaderkwargs.pop( "delimiter", _csv.Sniffer().sniff(fin.read(1024)).delimiter )
			loaderkwargs["delimiter"] = delimiter

		# load the file using the specified loader function
		data = self.loader_function ( file_to_read, **loaderkwargs )

		# try to inspect the output type (ideally it should be a pandas data frame, with at least Name, Freq, Power)
		if type(data) == _pd.DataFrame:
			# if its a data frame, then great. ensure that labels are all lower case, and that name and power exist
			data.rename({x:x.lower() for x in data.columns}, axis='columns', inplace=True)
			assert 'freq' in data.columns, "there doesn't appear to be a frequency axis - {0}".format( data.columns )

			if 'name' not in data.columns:
				data.insert(0, 'name', _pd.Series( ['K{0:04d}'.format(v) for v in _np.arange(len(data))] , index=data.index))
			if 'power' not in data.columns:
				data.insert(2, 'power', _pd.Series( _np.zeros_like(data.index) , index=data.index))

			self.data = data

		elif type(data) in [np.ndarray, list, tuple]:
			# if the toneslist is an array, try to create a dataframe
			if len(data) == 1:
				# assume that only a frequency list is given - create name and power arrays
				data = _np.array([ ['K{0:04d}'.format(v) for v in _np.arange(len(data))], \
								data,\
								np.zeros_like(data)]\
								)
			if len(data) == 3:
				# assume that data is an iterable with 3 cols, name, freq, power
				data = {name: val for (name, val) in zip(['name', 'freq', 'power'], data) }

			self.data = _pd.DataFrame(data = data)

		else:
			_logger.error( """Couldn't parse data into a sensible format. Data has been returned, but is likely not usable.
			Check the output of the loader function""" )
			self.data = data
			return

		# get an array of the tonenames for convenience
		self.tonenames = self.data['name'].get_values()

		# if successful, try to find the optimum LO frequency automatically
		self.lo_freq = self.find_optimum_lo() # this will trigger the frequency lists to be updated

		# update the amps and phases to default values
		self.amps   = _np.ones(self.tonenames.shape)
		self.set_phases(how = "random")
		self.ampcorr.update({'default': _np.ones(self.tonenames.shape)})

		_logger.info("Successfully loaded toneslist file {0}".format(file_to_read) )
		_time.sleep(0.1)

	def find_optimum_lo(self):
		"""For a given set of tones, this function will find the optimum LO frequency to
		maximise the number of tones in the available bandwidth, and return a modified tonelist
		and LO frequency. Tones should be in Hz """

		# TODO: could try to make this more interactive to include optimisation of lo-placement to
		# keep tones too close to band edge... etc
		# = need to take into account the resolution of the lo-frequency

		data_range = self.data["freq"].max()/1.e6 - self.data["freq"].min()/1.e6

		#lo_placement_resolution = 10.
		#npoints = int( _np.ceil( data_range / lo_placement_resolution) ) + 1
		npoints = 101

		lo_freqs = _np.linspace(self.data["freq"].min(), self.data["freq"].max(), npoints)/1.e6

		self._lo_freqs = lo_freqs * 1.e6 # save this for plotting
		startvals = lo_freqs - self._bandwidth/2./1.e6
		stopvals  = lo_freqs + self._bandwidth/2./1.e6

		counts = []
		for startval, stopval in zip(startvals, stopvals):
			counts.append(_np.histogram(self.data["freq"]/1.e6, bins=(startval, stopval))[0])
		self._counts = _np.array(counts).flatten()

		# find maximum of values where
		maxvals, = _np.where(self._counts == self._counts.max())

		if all(_np.diff(maxvals) == 1):
			# all values are consecutive, so, try to choose the one that is furthest away from tones
			lo_optimum_idx = maxvals[ _np.argmax([abs(self.data['freq']/1.e6 - v).min() for v in lo_freqs[maxvals]]) ]

		else:
			# there appears to be multiple 'optimum' locations
			lo_optimum_idx = maxvals[0]

		return lo_freqs[lo_optimum_idx] * 1.e6

	def place_blind_tones(self):
		return

	def calc_sweep_lo_freqs(self, sweep_span, sweep_step):
		"""
		Function to get a set of LO frequencies from a given span and step size (in Hz). This function will ensure that
	    the number of points is odd to include the centre frequency.

		"""
		if self.lo_freq is None:
			_logger.warning( "no LO frequency set. Nothing done." )
			return

		npoints = int( sweep_span/sweep_step )
		assert sweep_span > 2 * sweep_step, "sweep span is less than the step resulting in a {0} point sweep".format(npoints)
		# ensure that the number of sweep points is odd to capture the centre frequency
		npoints = npoints + 1 if npoints % 2 == 0 else npoints
	    # create sweep_lo_freqs in toneslist
		self.sweep_lo_freqs = _np.linspace(self.lo_freq - sweep_span/2., \
											self.lo_freq + sweep_span/2., \
												npoints, dtype = _np.float64 )

		_logger.debug( "set sweep LO frequencies - {0}".format( self.sweep_lo_freqs ) )

	def plot_tonedata(self, units = "mhz"):
		"""Plotting routine to check the loaded tonelist.  """

		assert units.lower() in ['hz', 'khz', 'mhz', 'ghz']

		multiplier = {'hz':1., 'khz':1.e3, 'mhz':1.e6, 'ghz':1.e9} [units.lower()]

		numplots = 2 if self._counts is not None else 1  # if find_optimum_lo has been run, self._counts != None

		fig, ax = _plt.subplots(numplots,1, figsize = [6.5, 3], sharex=True, gridspec_kw = {'height_ratios':[3, 1]} )
		ax = _np.atleast_1d(ax)

		plots = [ ax[0].axvline(l) for l in self.data['freq']/multiplier ]
		ax[0].axvline(self.lo_freq/multiplier, color = 'r', lw=2)
		ax[0].axvspan(self.lo_freq/multiplier - self._bandwidth/2./multiplier, self.lo_freq/multiplier + self._bandwidth/2/multiplier, color = 'b', alpha=0.25)
		if len(ax) > 1:
			ax[1].plot(self._lo_freqs/multiplier, self._counts, marker = 'o', ls = '')

		fig.tight_layout()
		fig.show()
		return fig, ax


	# def compile_toneslist(self):
	#
	# 	"""
	# 		Description:
	# 			Generate the toneslist as a pandas dataframe containing, for each instance:
	#
	# 				roach_id (string): Identification of the ROACHs,
	# 				date (time): Date when the broadband VNA sweep has been operated,
	# 				time (time): Time when the broadband VNA sweep has been operated,
	# 				run (string): Identification of the run from which the chip has been issued (eg.: CU-R001),
	# 				array (string): Identification of the array from which the chip has been issued (eg.: INAOE-A3 -SiW20nm),
	# 				chip (string): Identification of the chip (eg.: A3),
	# 				temp (float): Temperature at which the resonant frequencies have been measured, in C,
	# 				pow_in_cryo (float): Power of the attenuation sat up for the signal going into the cryostat, in dBm,
	# 				pow_out_cryo (float): Power of the attenuation sat up for the signal coming out of the crystat, in dBm,
	#
	# 				res_id_design (array of string): Identification of the resonator associated with a resonance frequency (eg.: KID000),
	# 				f_res_design (array of float): Design resonnant frequency of a resonator, in Hz,
	# 				res_q_design (array of int): Estimated Q for each resonators, from design data,
	#
	# 				res_id_sweep (array of string): Identification of the resonator associated with a resonance frequency (eg.: RES000),
	# 				f_res_sweep (array of float): Measured resonnant frequency of a resonator, in Hz,
	# 				pow_res_sweep (array of int): Output optimal power from cryostat measured, in dBm,
	# 				res_q_sweep (array of int): Estimated Q for each measured resonators,
	#
	# 				lo_frequency (float): Median frequency to be taken as the Local Oscillator [LO] lo_frequency,
	# 				bb_freqs (array of floats): Baseband resonnant frequencies to be used to generate the frequency comb.
	#
	# 		Return:
	# 			toneslist (pandas dataframe): The desired toneslist.
	# 	"""
	#
	# 	toneslist = _pd.DataFrame()
	#
	# 	# Generate the toneslist's base , incorporate global data
	# 	toneslist_config = self.toneslist_config["toneslist_config"].copy()
	# 	for roach_id, param in toneslist_config.items():
	#
	# 		idx = [roach_id]
	#
	# 		content = [(param["date"], param["time"], param["run"], param["array"], param["chip"], param["temp"], param["pow_in_cryo"], param["pow_out_cryo"])]
	# 		col_names = ['date', 'time', 'run', 'array', 'chip', 'temp', 'pow_in_cryo', 'pow_out_cryo']
	# 		sub_toneslist_param = _pd.DataFrame(content, columns = col_names, index = idx)
	#
	# 		# Add the design toneslist data
	# 		res_id_design = []
	# 		f_res_design = []
	# 		res_q_design = []
	#
	#
	# 		res_data_design = _np.load(param["toneslist_init_design_path"]) # ??? path needs to be changed for something more accurate, regarding dirfile lib
	# 		res_id_design.append(res_data_design[0, :].astype(str))
	# 		f_res_design.append(res_data_design[1, :].astype(float))
	# 		res_q_design.append(res_data_design[2, :].astype(int))
	#
	# 		content = [(res_id_design, f_res_design, res_q_design)]
	# 		col_names = ['res_id_design', 'f_res_design', 'q_res_design']
	# 		sub_toneslist_design = _pd.DataFrame(content, columns = col_names, index = idx)
	#
	# 		# Add the broadband VNA sweep toneslist data and their BB transformation
	# 		res_id_sweep = []
	# 		f_res_sweep = []
	# 		pow_res_sweep = []
	# 		res_q_sweep = []
	# 		f_center = []
	# 		bb_freqs = []
	#
	# 		res_data_sweep = _np.load(param["toneslist_init_sweep_path"]) # ??? path needs to be changed for something more accurate, regarding dirfile lib
	# 		f_res_tmp = res_data_sweep[1, :].astype(float)
	# 		res_id_sweep.append(res_data_sweep[0, :].astype(str))
	# 		f_res_sweep.append(res_data_sweep[1, :].astype(float))
	# 		pow_res_sweep.append(res_data_sweep[2, :].astype(int))
	# 		res_q_sweep.append(res_data_sweep[3, :].astype(int))
	#
	# 		# LO calculation
	# 		lo_frequency = sum(f_res_tmp) / len(f_res_tmp)
	#
	# 		# Baseband frequency tranformation
	# 		bb_freqs.append(f_res_tmp - lo_frequency)
	#
	# 		content = [(res_id_sweep, f_res_sweep, pow_res_sweep, res_q_sweep)]
	# 		col_names = ['res_id_sweep', 'f_res_sweep', 'pow_res_sweep', 'q_res_sweep']
	# 		sub_toneslist_sweep = _pd.DataFrame(content, columns = col_names, index = idx)
	#
	# 		content = [(lo_frequency, bb_freqs)]
	# 		col_names = ['lo_frequency', 'bb_freqs']
	# 		sub_toneslist_bb = _pd.DataFrame(content, columns = col_names, index = idx)
	#
	# 		sub_toneslist = _pd.concat([sub_toneslist_param, sub_toneslist_design, sub_toneslist_sweep, sub_toneslist_bb], axis = 1)
	# 		toneslist = _pd.concat([toneslist, sub_toneslist])
	#
	# 	return toneslist
	#
	##

	### === Optimisation functions === ###

	# def check_freq_distance(self, toneslist, threshold, update_toneslist = False):
	# 	"""
	# 		Description:
	# 			Check if any resonators are too far from their expected resonnant freaquency, regarding the design.
	#
	# 		Parameters:
	# 			toneslist (pandas dataframe): The main toneslist for which the checking needs to be conducted,
	# 			threshold (float): Minimal relative difference in frequency admissible between a resonator and its expected resonnant frequency, in Hz,
	# 			update_toneslist (bool): Option to update the main toneslist by removing the far away resonator and its related parameters (res_id, f_res, Q)
	#
	# 		Return:
	# 			dataset_freqd (pandas dataframe): A dictionary listing, for each ROACHs:
	# 				res_id_freqd (dataframe as an array of string): List of the resonators too far from design,
	# 				freqs_rm_freqd (dataframe as an array of floats): List of the related resonnant frequencies,
	# 				q_rm_freqd (dataframe as an array of ints): List of the associated Qs.
	#
	# 	"""
	#
	# 	# Parameters validation
	# 	col = ['date', 'time', 'run', 'array', 'chip', 'temp',
	# 									'pow_in_cryo', 'pow_out_cryo', 'res_id_design',
	# 									'f_res_design', 'q_res_design', 'res_id_sweep',
	# 									'f_res_sweep', 'pow_res_sweep', 'q_res_sweep', 'lo_frequency', 'bb_freqs']
	# 	assert all(toneslist.columns == col), "The toneslist parameter is not a toneslist or is missing data."
	#
	# 	assert type(threshold) == float, "The threshold parameter is not a float."
	# 	assert threshold > 0.5e6, "The threshold value is too low."
	#
	# 	# Initialisation of the f distance identification
	# 	dataset_freqd = _pd.DataFrame()
	#
	# 	# Generation of the dataset for each ROACHs
	# 	for idx in toneslist.index:
	#
	# 		# Initialisation of the calculation
	# 		sub_toneslist = toneslist.loc[idx]
	# 		res_id_sweep = sub_toneslist.res_id_sweep
	# 		f_res_sweep = sub_toneslist.f_res_sweep
	# 		pow_res_sweep = sub_toneslist.pow_res_sweep
	# 		q_res_sweep = sub_toneslist.q_res_sweep
	# 		f_res_design = sub_toneslist.f_res_design
	#
	# 		idx_rm = []
	# 		delta_f = 0
	#
	# 		# Threshold testing
	# 		for i in range(0, len(f_res_design[0])):
	# 			delta_f = abs(f_res_sweep[0][i] - f_res_design[0][i])
	#
	# 			if delta_f >= threshold:
	# 				res_id_freqd_sub = res_id_sweep[0][i]
	# 				freqs_rm_freqd_sub = f_res_sweep[0][i]
	# 				pow_rm_freqd_sub = pow_res_sweep[0][i]
	# 				q_rm_freqd_sub = q_res_sweep[0][i]
	# 				idx_rm.append(i)
	#
	# 		# Generation of the dataset
	# 		if not (not idx_rm):
	# 			content = [(res_id_freqd_sub, freqs_rm_freqd_sub, pow_rm_freqd_sub, q_rm_freqd_sub)]
	# 			col_names = ['res_id_sweep', 'f_res_sweep', 'pow_res_sweep', 'res_q_sweep']
	# 			sub_dataset_freqd = _pd.DataFrame(content, columns = col_names, index = [idx])
	#
	# 			dataset_freqd = _pd.concat([dataset_freqd, sub_dataset_freqd])
	#
	# 		# Optionnal removal of the clashes from the main toneslist
	# 		if update_toneslist == True and not (not idx_rm):
	# 			res_id_new = _np.delete(res_id_sweep, idx_rm)
	# 			freqs_new = _np.delete(f_res_sweep, idx_rm)
	# 			pow_new = _np.delete(pow_res_sweep, idx_rm)
	# 			q_new = _np.delete(q_res_sweep, idx_rm)
	#
	# 			# LO calculation
	# 			lo_frequency = sum(freqs_new) / len(freqs_new)
	#
	# 			# Baseband frequency tranformation
	# 			bb_freqs = freqs_new - lo_frequency
	#
	# 			toneslist.at[idx, "res_id_sweep"] = [res_id_new]
	# 			toneslist.at[idx, "f_res_sweep"] = [freqs_new]
	# 			toneslist.at[idx, "pow_res_sweep"] = [pow_new]
	# 			toneslist.at[idx, "q_res_sweep"] = [q_new]
	# 			toneslist.at[idx, "lo_frequency"] = lo_frequency
	# 			toneslist.at[idx, "bb_freqs"] = bb_freqs
	#
	# 			print("Toneslist updated for the " + idx)
	#
	# 	return dataset_freqd
	#
	# def check_clashes(self, toneslist, threshold, update_toneslist = False):
	#
	# 	"""
	# 		Description:
	# 			Check and list any clashing resonators, removing them from the baseband frequency list.
	# 			The function simply compares the spacing between two consecutive resonnant frequencies along the BB frequency list to a threshold.
	# 			Any value above the threshold gets removed and the related resonators ids are provided as an output for the user.
	#
	# 		Parameters:
	# 			toneslist (pandas dataframe): The main toneslist for which the clashes needs to be found,
	# 			threshold (float): Minimal relative difference in frequency admissible between two resonators, in Hz,
	# 			update_toneslist (bool): Option to update the main toneslist by removing the calculated clashes and their related parameters (res_id, f_res, Q)
	#
	# 		Return:
	# 			dataset_clashes (pandas dataframe): A dictionary listing, for each ROACHs:
	# 				res_id_clashes (array of strings): List of the clashing resonator's ID,
	# 				f_rm_clashes (array of floats): Related resonnant frequencies,
	# 				q_rm_clashes (array of int): Associated Qs.
	# 	"""
	#
	# 	# Parameters validation
	# 	col = ['date', 'time', 'run', 'array', 'chip', 'temp',
	# 									'pow_in_cryo', 'pow_out_cryo', 'res_id_design',
	# 									'f_res_design', 'q_res_design', 'res_id_sweep',
	# 									'f_res_sweep', 'pow_res_sweep', 'q_res_sweep', 'lo_frequency', 'bb_freqs']
	# 	assert all(toneslist.columns == col), "The toneslist parameter is not a toneslist."
	#
	# 	assert type(threshold) == float, "The threshold parameter is not a float."
	# 	assert threshold > 0.5e6, "The threshold value is too low."
	#
	# 	# Initialisation of the clashes calculation
	# 	dataset_clashes = _pd.DataFrame()
	#
	# 	# Generation of the dataset for each ROACHs
	# 	for idx in toneslist.index:
	#
	# 		# Initialisation of the clashes identification
	# 		sub_toneslist = toneslist.loc[idx]
	# 		res_id_sweep = sub_toneslist.res_id_sweep
	# 		f_res_sweep = sub_toneslist.f_res_sweep
	# 		pow_res_sweep = sub_toneslist.pow_res_sweep
	# 		q_res_sweep = sub_toneslist.q_res_sweep
	# 		bb_freqs = sub_toneslist.bb_freqs
	#
	# 		idx_rm = []
	# 		delta_f = 0
	#
	# 		# Threshold testing
	# 		for i in range(0, len(f_res_sweep[0]) - 1):
	# 			delta_f = abs(f_res_sweep[0][i + 1] - f_res_sweep[0][i])
	#
	# 			if delta_f <= threshold:
	# 				res_id_clashes = [res_id_sweep[0][i]]
	# 				res_id_clashes.append(res_id_sweep[0][i + 1])
	# 				f_rm_clashes = [f_res_sweep[0][i]]
	# 				f_rm_clashes.append(f_res_sweep[0][i + 1])
	# 				pow_rm_clashes = [pow_res_sweep[0][i]]
	# 				pow_rm_clashes.append(pow_res_sweep[0][i + 1])
	# 				q_rm_clashes = [q_res_sweep[0][i]]
	# 				q_rm_clashes.append(q_res_sweep[0][i + 1])
	# 				if not i in idx_rm:
	# 					idx_rm.append(i)
	# 					idx_rm.append(i + 1)
	#
	# 		# Generation of the dataset
	# 		if not (not idx_rm):
	# 			content = [(res_id_clashes, f_rm_clashes, pow_rm_clashes, q_rm_clashes)]
	# 			col_names = ['res_id_clashes', 'f_rm_clashes', 'pow_rm_clashes', 'q_rm_clashes']
	# 			sub_dataset_clashes = _pd.DataFrame(content, columns = col_names, index = [idx])
	#
	# 			dataset_clashes = _pd.concat([dataset_clashes, sub_dataset_clashes])
	#
	# 		# Optionnal removal of the clashes from the main toneslist
	# 		if update_toneslist == True and not (not idx_rm):
	# 			res_id_new = _np.delete(res_id_sweep, idx_rm)
	# 			freqs_new = _np.delete(f_res_sweep, idx_rm)
	# 			pow_new = _np.delete(pow_res_sweep, idx_rm)
	# 			q_new = _np.delete(q_res_sweep, idx_rm)
	#
	# 			# LO calculation
	# 			lo_frequency = sum(freqs_new) / len(freqs_new)
	#
	# 			# Baseband frequency tranformation
	# 			bb_freqs = freqs_new - lo_frequency
	#
	# 			toneslist.at[idx, "res_id_sweep"] = [res_id_new]
	# 			toneslist.at[idx, "f_res_sweep"] = [freqs_new]
	# 			toneslist.at[idx, "pow_res_sweep"] = [pow_new]
	# 			toneslist.at[idx, "q_res_sweep"] = [q_new]
	# 			toneslist.at[idx, "lo_frequency"] = lo_frequency
	# 			toneslist.at[idx, "bb_freqs"] = bb_freqs
	#
	# 			print("Toneslist updated for the " + idx)
	#
	# 	return dataset_clashes
	# #
	#
	# def check_missings(self, toneslist):
	#
	# 	"""
	# 		Description:
	# 			Compare the resonators data obtained from the VNA broadband sweep to the design ones to check if resonators are missing.
	#
	# 		Notes:
	# 			Will be modifyied later to incorporate a large array case, where the bandwith [-256MHz; 256MHz] is not offering enough spacing.
	# 			Will also contain a list of the estimated missing resonators
	#
	# 		Parameters:
	# 			toneslist (pandas dataframe): The main toneslist for which the missing resonators needs to be found,
	#
	# 		Return:
	# 			dataset_missings (pandas dataframe): A dictionary listing, for each ROACHs:
	# 				warning (bool): 0 if none are found, 1 if there are missing resonators
	# 	"""
	#
	# 	# Parameters validation
	# 	col = ['date', 'time', 'run', 'array', 'chip', 'temp',
	# 									'pow_in_cryo', 'pow_out_cryo', 'res_id_design',
	# 									'f_res_design', 'q_res_design', 'res_id_sweep',
	# 									'f_res_sweep', 'q_res_sweep', 'pow_res_sweep', 'lo_frequency', 'bb_freqs']
	# 	assert all(toneslist.columns == col), "The toneslist parameter is not a toneslist."
	#
	# 	# Initialisation of the missings calculation
	# 	dataset_missings = _pd.DataFrame()
	#
	# 	for idx in toneslist.index:
	#
	# 		# Initialisation of the clashes identification
	# 		warning = 0
	# 		# missings = []
	# 		sub_toneslist = toneslist.loc[idx]
	# 		res_id_sweep = sub_toneslist.res_id_sweep
	# 		# f_res_sweep = sub_toneslist.f_res_sweep
	# 		# q_res_sweep = sub_toneslist.q_res_sweep
	#
	# 		res_id_design = sub_toneslist.res_id_design
	# 		# f_res_design = sub_toneslist.f_res_design
	# 		# q_res_design = sub_toneslist.q_res_design
	#
	# 		if len(res_id_design[0]) != len(res_id_sweep[0]):
	# 			warning = 1
	#
	# 		# for i in range(0, len(res_id_design[0])):
	# 		# 	missings =
	# 		#
	# 		# if not missings:
	# 		# 	warning = 0
	# 		# else:
	# 		# 	warning = 1
	#
	# 		# Generation of the dataset
	# 		if warning:
	# 			content = [(warning)]
	# 			col_names = ['warning']
	# 			sub_dataset_missings = _pd.DataFrame(content, columns = col_names, index = [idx])
	#
	# 			dataset_missings = _pd.concat([dataset_missings, sub_dataset_missings])
	#
	# 	return dataset_missings
	# #
    #     ##
	#
	# ### === Design and Sweep Toneslist generation === ###
	#
	# def compile_sd_toneslist(self, sd_data, save_sd_toneslist = False):
	#
	# 	"""
	# 		Description:
	# 			Compile sweep or design toneslist in a numpy array format, from data either in txt, csv, list or array format
	#
	# 		Parameters:
	# 			sd_data (txt, csv, list or array): The toneslist data containing:
	# 				resonators ID (list of string),
	# 				resonnance frequency (list of floats) in Hz,
	# 				absolute power if sweep (list of int), in dBm,
	# 				Qs (list of int).
	# 			save_sd_toneslist (bool): Option to save the compiled sweep / design toneslist.
	#
	# 		Return:
	# 			sd_toneslist (numpy array): The compiled toneslist in the right format to be used by the compile_toneslist function
	#
	# 	"""
	#
	# 	# Parameter validation
	# 	if sd_data.endswith('.txt') or sd_data.endswith('.csv'):
	#
	# 		# Reading data
	# 		data = _pd.read_csv(sd_data, delim_whitespace=True, skipinitialspace=True)
	#
	# 		if len(data.columns) == 4: datatype_flag = 1
	# 		elif len(data.columns) == 3: datatype_flag = 1
	# 		else: datatype_flag = 0
	#
	# 	elif type(sd_data) == list or type(sd_data) == numpy.ndarray:
	# 		if len(sd_data) == 3 or len(sd_data) == 4: datatype_flag = 1
	#
	# 	else: datatype_flag = 0
	#
	# 	assert datatype_flag == 1, "Data format error."
	#
	# 	# Compilation from txt or csv
	# 	if sd_data.endswith('.txt') or sd_data.endswith('.csv'):
	# 		sd_data_header = data.columns
	# 		if len(sd_data_header) == 4:
	# 			sd_toneslist = _np.array([data[sd_data_header[0]],data[sd_data_header[1]], data[sd_data_header[2]], data[sd_data_header[3]]])
	# 		elif len(sd_data_header) == 3:
	# 			sd_toneslist = _np.array([data[sd_data_header[0]],data[sd_data_header[1]], data[sd_data_header[2]]])
	#
	# 	# Compilation from list
	# 	elif type(sd_data) == list:
	# 		sd_toneslist = _np.array(sd_data)
	#
	# 	# Saving the compiled toneslist
	# 	if save_sd_toneslist == True:
	# 		if len(sd_toneslist) == 3: _np.save('./last_design_toneslist.npy',sd_toneslist)
	# 		elif len(sd_toneslist) == 4: _np.save('./last_sweep_toneslist.npy',sd_toneslist)
	#
	# 	return sd_toneslist

### END ###
