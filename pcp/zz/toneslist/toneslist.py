"""
Description:
Toneslist library (library) provides a set of functions to generate the resonators tone list:
	- Fullband VNA sweep and associated toneslist is provided by a separate module,
	- Toneslist generation from sweep data, with respect to the number of ROACHs and the size of the array.
		This provides both the list of tones in the baseband [BB] frequency domain (f_LO - 256MHz; f_LO + 256MHz) and the radiofrequency [RF] one.

Notes:
Later on, the following features will be implemented:
- Adjust or provide optimal power for the specifyied set of tones,
- Improve checking for missing tones and generate a warning subsequently,
- Provide a dirfile compatible version.
- Discuss about the LO correction regarding the tests functions (if a resonator is removed from the list, do we want to recalculate the LO?)

Authors: Dr Pete Barry, Dr Samuel Rowe, Mr Marcial Tapia, Mr Thomas Gascard, Dr Kirit Karkare, Dr Salvador Ventura.
Version: 0.1
Date: 19.10.2018
"""

### === Importation === ###

import numpy as np
import pandas as pd
from .. import configuration as configuration; reload(configuration)

# Read in relevant config files
#from ..configuration import toneslist_config
#


def load_pcp_tonelist(tonelist_file):
	"""

	Function used to load in the pcp tonelist file, and return a standardised format
	that will be read in by the tonesList class.

	"""
	return

### === Toneslist class === ###

class Toneslist(object):
	# -- basic functionality --
	# read in an array of resonator frequencies (GHz)
	# convert to bb_freqs for writing to roach (need LO)
	# placement of blind tones
	# plot routines to visualise toneslist
	# include "phases"
	#	- random
	#	- other? Sam R has nice routines to reduce sideband leakage (sacrificing 500 tones)

	# include "amplitudes"
	#	- for each tone, specify a tone power (normalised to 1) --> used when writing to roach
	#	- have this connected to dBm bifurcation powers
	# calibration routines
		# - add functions to pass in a file of calibration data in order to offset tones

	# -- ideal functionality --
	# interactive modification of toneslist to include/exclude tones (code exists in kidpy by JW)
	# have a "loader" that allows anyone to write a loader function and provide a


	def __init__(self, loader_function ):

		self.loader_function = loader_function

		assert( callable(loader_function) ) # this should probably go further down

		self.rf_freqs    = None
		self.lo_freq     = None
		self.blind_freqs = None

		self.bb_freqs    = None

		self.amps   = None
		self.phases = None


		#self.toneslist_config = configuration.toneslist_config
		# set dirfile here
	#

	### = Toneslist generation functions = ###
	@staticmethod
	def convert_rf_to_bb_freqs(rf_freqs, lo_freq):
		return rf_freqs - lo_freq

	def place_blind_tones(self):
		return

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
	# 	toneslist = pd.DataFrame()
	#
	# 	# Generate the toneslist's base , incorporate global data
	# 	toneslist_config = self.toneslist_config["toneslist_config"].copy()
	# 	for roach_id, param in toneslist_config.items():
	#
	# 		idx = [roach_id]
	#
	# 		content = [(param["date"], param["time"], param["run"], param["array"], param["chip"], param["temp"], param["pow_in_cryo"], param["pow_out_cryo"])]
	# 		col_names = ['date', 'time', 'run', 'array', 'chip', 'temp', 'pow_in_cryo', 'pow_out_cryo']
	# 		sub_toneslist_param = pd.DataFrame(content, columns = col_names, index = idx)
	#
	# 		# Add the design toneslist data
	# 		res_id_design = []
	# 		f_res_design = []
	# 		res_q_design = []
	#
	#
	# 		res_data_design = np.load(param["toneslist_init_design_path"]) # ??? path needs to be changed for something more accurate, regarding dirfile lib
	# 		res_id_design.append(res_data_design[0, :].astype(str))
	# 		f_res_design.append(res_data_design[1, :].astype(float))
	# 		res_q_design.append(res_data_design[2, :].astype(int))
	#
	# 		content = [(res_id_design, f_res_design, res_q_design)]
	# 		col_names = ['res_id_design', 'f_res_design', 'q_res_design']
	# 		sub_toneslist_design = pd.DataFrame(content, columns = col_names, index = idx)
	#
	# 		# Add the broadband VNA sweep toneslist data and their BB transformation
	# 		res_id_sweep = []
	# 		f_res_sweep = []
	# 		pow_res_sweep = []
	# 		res_q_sweep = []
	# 		f_center = []
	# 		bb_freqs = []
	#
	# 		res_data_sweep = np.load(param["toneslist_init_sweep_path"]) # ??? path needs to be changed for something more accurate, regarding dirfile lib
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
	# 		sub_toneslist_sweep = pd.DataFrame(content, columns = col_names, index = idx)
	#
	# 		content = [(lo_frequency, bb_freqs)]
	# 		col_names = ['lo_frequency', 'bb_freqs']
	# 		sub_toneslist_bb = pd.DataFrame(content, columns = col_names, index = idx)
	#
	# 		sub_toneslist = pd.concat([sub_toneslist_param, sub_toneslist_design, sub_toneslist_sweep, sub_toneslist_bb], axis = 1)
	# 		toneslist = pd.concat([toneslist, sub_toneslist])
	#
	# 	return toneslist
	#
	##

	### === Optimisation functions === ###

	def check_freq_distance(self, toneslist, threshold, update_toneslist = False):
		"""
			Description:
				Check if any resonators are too far from their expected resonnant freaquency, regarding the design.

			Parameters:
				toneslist (pandas dataframe): The main toneslist for which the checking needs to be conducted,
				threshold (float): Minimal relative difference in frequency admissible between a resonator and its expected resonnant frequency, in Hz,
				update_toneslist (bool): Option to update the main toneslist by removing the far away resonator and its related parameters (res_id, f_res, Q)

			Return:
				dataset_freqd (pandas dataframe): A dictionary listing, for each ROACHs:
					res_id_freqd (dataframe as an array of string): List of the resonators too far from design,
					freqs_rm_freqd (dataframe as an array of floats): List of the related resonnant frequencies,
					q_rm_freqd (dataframe as an array of ints): List of the associated Qs.

		"""

		# Parameters validation
		col = ['date', 'time', 'run', 'array', 'chip', 'temp',
										'pow_in_cryo', 'pow_out_cryo', 'res_id_design',
										'f_res_design', 'q_res_design', 'res_id_sweep',
										'f_res_sweep', 'pow_res_sweep', 'q_res_sweep', 'lo_frequency', 'bb_freqs']
		assert all(toneslist.columns == col), "The toneslist parameter is not a toneslist or is missing data."

		assert type(threshold) == float, "The threshold parameter is not a float."
		assert threshold > 0.5e6, "The threshold value is too low."

		# Initialisation of the f distance identification
		dataset_freqd = pd.DataFrame()

		# Generation of the dataset for each ROACHs
		for idx in toneslist.index:

			# Initialisation of the calculation
			sub_toneslist = toneslist.loc[idx]
			res_id_sweep = sub_toneslist.res_id_sweep
			f_res_sweep = sub_toneslist.f_res_sweep
			pow_res_sweep = sub_toneslist.pow_res_sweep
			q_res_sweep = sub_toneslist.q_res_sweep
			f_res_design = sub_toneslist.f_res_design

			idx_rm = []
			delta_f = 0

			# Threshold testing
			for i in range(0, len(f_res_design[0])):
				delta_f = abs(f_res_sweep[0][i] - f_res_design[0][i])

				if delta_f >= threshold:
					res_id_freqd_sub = res_id_sweep[0][i]
					freqs_rm_freqd_sub = f_res_sweep[0][i]
					pow_rm_freqd_sub = pow_res_sweep[0][i]
					q_rm_freqd_sub = q_res_sweep[0][i]
					idx_rm.append(i)

			# Generation of the dataset
			if not (not idx_rm):
				content = [(res_id_freqd_sub, freqs_rm_freqd_sub, pow_rm_freqd_sub, q_rm_freqd_sub)]
				col_names = ['res_id_sweep', 'f_res_sweep', 'pow_res_sweep', 'res_q_sweep']
				sub_dataset_freqd = pd.DataFrame(content, columns = col_names, index = [idx])

				dataset_freqd = pd.concat([dataset_freqd, sub_dataset_freqd])

			# Optionnal removal of the clashes from the main toneslist
			if update_toneslist == True and not (not idx_rm):
				res_id_new = np.delete(res_id_sweep, idx_rm)
				freqs_new = np.delete(f_res_sweep, idx_rm)
				pow_new = np.delete(pow_res_sweep, idx_rm)
				q_new = np.delete(q_res_sweep, idx_rm)

				# LO calculation
				lo_frequency = sum(freqs_new) / len(freqs_new)

				# Baseband frequency tranformation
				bb_freqs = freqs_new - lo_frequency

				toneslist.at[idx, "res_id_sweep"] = [res_id_new]
				toneslist.at[idx, "f_res_sweep"] = [freqs_new]
				toneslist.at[idx, "pow_res_sweep"] = [pow_new]
				toneslist.at[idx, "q_res_sweep"] = [q_new]
				toneslist.at[idx, "lo_frequency"] = lo_frequency
				toneslist.at[idx, "bb_freqs"] = bb_freqs

				print("Toneslist updated for the " + idx)

		return dataset_freqd

	def check_clashes(self, toneslist, threshold, update_toneslist = False):

		"""
			Description:
				Check and list any clashing resonators, removing them from the baseband frequency list.
				The function simply compares the spacing between two consecutive resonnant frequencies along the BB frequency list to a threshold.
				Any value above the threshold gets removed and the related resonators ids are provided as an output for the user.

			Parameters:
				toneslist (pandas dataframe): The main toneslist for which the clashes needs to be found,
				threshold (float): Minimal relative difference in frequency admissible between two resonators, in Hz,
				update_toneslist (bool): Option to update the main toneslist by removing the calculated clashes and their related parameters (res_id, f_res, Q)

			Return:
				dataset_clashes (pandas dataframe): A dictionary listing, for each ROACHs:
					res_id_clashes (array of strings): List of the clashing resonator's ID,
					f_rm_clashes (array of floats): Related resonnant frequencies,
					q_rm_clashes (array of int): Associated Qs.
		"""

		# Parameters validation
		col = ['date', 'time', 'run', 'array', 'chip', 'temp',
										'pow_in_cryo', 'pow_out_cryo', 'res_id_design',
										'f_res_design', 'q_res_design', 'res_id_sweep',
										'f_res_sweep', 'pow_res_sweep', 'q_res_sweep', 'lo_frequency', 'bb_freqs']
		assert all(toneslist.columns == col), "The toneslist parameter is not a toneslist."

		assert type(threshold) == float, "The threshold parameter is not a float."
		assert threshold > 0.5e6, "The threshold value is too low."

		# Initialisation of the clashes calculation
		dataset_clashes = pd.DataFrame()

		# Generation of the dataset for each ROACHs
		for idx in toneslist.index:

			# Initialisation of the clashes identification
			sub_toneslist = toneslist.loc[idx]
			res_id_sweep = sub_toneslist.res_id_sweep
			f_res_sweep = sub_toneslist.f_res_sweep
			pow_res_sweep = sub_toneslist.pow_res_sweep
			q_res_sweep = sub_toneslist.q_res_sweep
			bb_freqs = sub_toneslist.bb_freqs

			idx_rm = []
			delta_f = 0

			# Threshold testing
			for i in range(0, len(f_res_sweep[0]) - 1):
				delta_f = abs(f_res_sweep[0][i + 1] - f_res_sweep[0][i])

				if delta_f <= threshold:
					res_id_clashes = [res_id_sweep[0][i]]
					res_id_clashes.append(res_id_sweep[0][i + 1])
					f_rm_clashes = [f_res_sweep[0][i]]
					f_rm_clashes.append(f_res_sweep[0][i + 1])
					pow_rm_clashes = [pow_res_sweep[0][i]]
					pow_rm_clashes.append(pow_res_sweep[0][i + 1])
					q_rm_clashes = [q_res_sweep[0][i]]
					q_rm_clashes.append(q_res_sweep[0][i + 1])
					if not i in idx_rm:
						idx_rm.append(i)
						idx_rm.append(i + 1)

			# Generation of the dataset
			if not (not idx_rm):
				content = [(res_id_clashes, f_rm_clashes, pow_rm_clashes, q_rm_clashes)]
				col_names = ['res_id_clashes', 'f_rm_clashes', 'pow_rm_clashes', 'q_rm_clashes']
				sub_dataset_clashes = pd.DataFrame(content, columns = col_names, index = [idx])

				dataset_clashes = pd.concat([dataset_clashes, sub_dataset_clashes])

			# Optionnal removal of the clashes from the main toneslist
			if update_toneslist == True and not (not idx_rm):
				res_id_new = np.delete(res_id_sweep, idx_rm)
				freqs_new = np.delete(f_res_sweep, idx_rm)
				pow_new = np.delete(pow_res_sweep, idx_rm)
				q_new = np.delete(q_res_sweep, idx_rm)

				# LO calculation
				lo_frequency = sum(freqs_new) / len(freqs_new)

				# Baseband frequency tranformation
				bb_freqs = freqs_new - lo_frequency

				toneslist.at[idx, "res_id_sweep"] = [res_id_new]
				toneslist.at[idx, "f_res_sweep"] = [freqs_new]
				toneslist.at[idx, "pow_res_sweep"] = [pow_new]
				toneslist.at[idx, "q_res_sweep"] = [q_new]
				toneslist.at[idx, "lo_frequency"] = lo_frequency
				toneslist.at[idx, "bb_freqs"] = bb_freqs

				print("Toneslist updated for the " + idx)

		return dataset_clashes
	#

	def check_missings(self, toneslist):

		"""
			Description:
				Compare the resonators data obtained from the VNA broadband sweep to the design ones to check if resonators are missing.

			Notes:
				Will be modifyied later to incorporate a large array case, where the bandwith [-256MHz; 256MHz] is not offering enough spacing.
				Will also contain a list of the estimated missing resonators

			Parameters:
				toneslist (pandas dataframe): The main toneslist for which the missing resonators needs to be found,

			Return:
				dataset_missings (pandas dataframe): A dictionary listing, for each ROACHs:
					warning (bool): 0 if none are found, 1 if there are missing resonators
		"""

		# Parameters validation
		col = ['date', 'time', 'run', 'array', 'chip', 'temp',
										'pow_in_cryo', 'pow_out_cryo', 'res_id_design',
										'f_res_design', 'q_res_design', 'res_id_sweep',
										'f_res_sweep', 'q_res_sweep', 'pow_res_sweep', 'lo_frequency', 'bb_freqs']
		assert all(toneslist.columns == col), "The toneslist parameter is not a toneslist."

		# Initialisation of the missings calculation
		dataset_missings = pd.DataFrame()

		for idx in toneslist.index:

			# Initialisation of the clashes identification
			warning = 0
			# missings = []
			sub_toneslist = toneslist.loc[idx]
			res_id_sweep = sub_toneslist.res_id_sweep
			# f_res_sweep = sub_toneslist.f_res_sweep
			# q_res_sweep = sub_toneslist.q_res_sweep

			res_id_design = sub_toneslist.res_id_design
			# f_res_design = sub_toneslist.f_res_design
			# q_res_design = sub_toneslist.q_res_design

			if len(res_id_design[0]) != len(res_id_sweep[0]):
				warning = 1

			# for i in range(0, len(res_id_design[0])):
			# 	missings =
			#
			# if not missings:
			# 	warning = 0
			# else:
			# 	warning = 1

			# Generation of the dataset
			if warning:
				content = [(warning)]
				col_names = ['warning']
				sub_dataset_missings = pd.DataFrame(content, columns = col_names, index = [idx])

				dataset_missings = pd.concat([dataset_missings, sub_dataset_missings])

		return dataset_missings
	#
        ##

	### === Design and Sweep Toneslist generation === ###

	def compile_sd_toneslist(self, sd_data, save_sd_toneslist = False):

		"""
			Description:
				Compile sweep or design toneslist in a numpy array format, from data either in txt, csv, list or array format

			Parameters:
				sd_data (txt, csv, list or array): The toneslist data containing:
					resonators ID (list of string),
					resonnance frequency (list of floats) in Hz,
					absolute power if sweep (list of int), in dBm,
					Qs (list of int).
				save_sd_toneslist (bool): Option to save the compiled sweep / design toneslist.

			Return:
				sd_toneslist (numpy array): The compiled toneslist in the right format to be used by the compile_toneslist function

		"""

		# Parameter validation
		if sd_data.endswith('.txt') or sd_data.endswith('.csv'):

			# Reading data
			data = pd.read_csv(sd_data, delim_whitespace=True, skipinitialspace=True)

			if len(data.columns) == 4: datatype_flag = 1
			elif len(data.columns) == 3: datatype_flag = 1
			else: datatype_flag = 0

		elif type(sd_data) == list or type(sd_data) == numpy.ndarray:
			if len(sd_data) == 3 or len(sd_data) == 4: datatype_flag = 1

		else: datatype_flag = 0

		assert datatype_flag == 1, "Data format error."

		# Compilation from txt or csv
		if sd_data.endswith('.txt') or sd_data.endswith('.csv'):
			sd_data_header = data.columns
			if len(sd_data_header) == 4:
				sd_toneslist = np.array([data[sd_data_header[0]],data[sd_data_header[1]], data[sd_data_header[2]], data[sd_data_header[3]]])
			elif len(sd_data_header) == 3:
				sd_toneslist = np.array([data[sd_data_header[0]],data[sd_data_header[1]], data[sd_data_header[2]]])

		# Compilation from list
		elif type(sd_data) == list:
			sd_toneslist = np.array(sd_data)

		# Saving the compiled toneslist
		if save_sd_toneslist == True:
			if len(sd_toneslist) == 3: np.save('./last_design_toneslist.npy',sd_toneslist)
			elif len(sd_toneslist) == 4: np.save('./last_sweep_toneslist.npy',sd_toneslist)

		return sd_toneslist

### END ###
