#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Script to get df and some useful plots

import numpy as _np
import os as _os
import time as _time

import calculate_funcs as _calculate_funcs
from data_cardiff_lab import homodyne_cardiff_lab as _data_cf_lab

import pygetdata as _gd
from .. import color_logs as CL

import matplotlib.pyplot as plt
plt.ion()

from scipy import signal
from scipy.signal import savgol_filter


def get_KID_data(kids, channel, current_channel=True, sample_rate=512e6/2**20, filter_cos_ray=True, all_kids=False, dB=True, stopidx=None, up_lim=110, down_lim=80, verbose=False,nfft=None):
	"""
	Get all the parameters of a set of kids: S21, df, PSD noise, f0 ...
		If current channel is True, channel has to be an object, otherwise channel is an array : [sweep_folder, stream_folder]
		sample_rate		:	DAC rate / buffer_lengh
		filter_cos_ray	:	apply a cosmic ray filter to the data
		all_kids		:	ignore kids and get parameters for all the KIDs
		dB 				:	results in dB units
		stopidx			:	upper limit to cut the data
		down_lm - up_lim : 	Limits of the area where average will be taken
		verbose			:	print some results during the execution time
	"""

	if current_channel:
		sweep_folder = channel.sweep.dirfile.name
		stream_folder = channel.current_dirfile.name
	else:
		sweep_folder = channel[0]
		stream_folder = channel[1]

	# To get the sweep as function of frequency -> S21(f)
	# ------------------------- S21 ----------------------------
	freqs, sweep_data = _calculate_funcs.get_sweep_data(sweep_folder)

	# To get the time stream
	time, time_stream = _calculate_funcs.get_stream_data(stream_folder)

	# To get the keys
	if all_kids:
		knames = freqs.keys()
	else:
		knames = kids

	KID = dict.fromkeys(knames)

	for kid in knames:
		fields = {}

		# To get the resonance frequency
		argF0 = int(_np.ceil(len(freqs[kid])/2.))

		fields['f0'] = freqs[kid][argF0]

		# Get didf, dqdf
		didf, sm_i = _calculate_funcs.get_dxdf(freqs[kid], sweep_data[kid].real)
		dqdf, sm_q = _calculate_funcs.get_dxdf(freqs[kid], sweep_data[kid].imag)

		fields['didf'] = didf
		fields['dqdf'] = dqdf

		# Get df
		df = _calculate_funcs.get_df(time_stream[kid+'_I'], time_stream[kid+'_Q'], sweep_data[kid].real, sweep_data[kid].imag, didf, dqdf, argF0)
		if filter_cos_ray:
			df = remove_cos_ray(df)

		freq, psd = signal.periodogram(df[:stopidx], sample_rate,nfft=nfft)

		# PSD level
		psd_level = _np.mean(psd[_np.where(freq>down_lim)[0][0]:_np.where(freq<up_lim)[0][-1]])

		if dB:
			psd = 10*_np.log10(psd)
			psd_level = 10*_np.log10(psd_level)

		fields['df'] = df[:stopidx]
		fields['freq'] = freq
		fields['psd'] = psd
		fields['psd_level'] = psd_level

		fields['s21'] = sweep_data[kid]
		fields['f_s21'] = freqs[kid]

		fields['I'] = time_stream[kid+'_I']
		fields['Q'] = time_stream[kid+'_Q']

		KID[kid] = fields

		if verbose:
			print CL.OKGREEN + "***" + kid + "***" + CL.ENDC
			print CL.OKBLUE + "f0 : " + CL.ENDC + str(fields['f0']) + "Hz"
			print CL.OKBLUE + "didf(f0) : " + CL.ENDC + str(fields['didf'][argF0])
			print CL.OKBLUE + "dqdf(f0) : " + CL.ENDC + str(fields['dqdf'][argF0])
			print CL.OKBLUE + "noise level : "+ CL.ENDC + str(fields['psd_level'])

	time = time - time[0]
	KID['time'] = time[:stopidx]

	return KID


def plots_s21(KIDs, **kwargs):
	"""
	Plot S_21(f), Speed and IQ circles of a KIDs dictionary
	"""
    # parse the keyword arguments
	verbose 		= 	kwargs.pop("verbose", False)
	leg				= 	kwargs.pop("leg", True)
	fig_per_plot	=	kwargs.pop("fig_per_plot", False)

	n_kids = KIDs.keys()

	cmap = plt.get_cmap('jet')
	colors = [cmap(i) for i in _np.linspace(0, 1, len(n_kids))]

	cnt = 0
	for kid in n_kids:

		if kid == "time":
			continue

		if fig_per_plot:
			# Plot S21 and IQ circles
			plt.figure('Sweep S21 ' + kid)

			plt.subplot(2,2,1)
			plt.title('Sweep magnitude')
			plt.axvline(KIDs[kid]['f0'], color='r')
			plt.plot(KIDs[kid]['f_s21'], 20*_np.log10(_np.abs(KIDs[kid]['s21'])), color=colors[cnt])
			plt.ylabel('dB')
			plt.xlabel('frequency[Hz]')
			plt.grid(True)

			plt.subplot(2,2,3)
			plt.axvline(KIDs[kid]['f0'], color='r')
			fs, speed = _calculate_funcs.get_speed(KIDs[kid]['f_s21'], KIDs[kid]['s21'])
			plt.plot(fs, speed, color=colors[cnt])
			plt.ylabel('Speed')
			plt.xlabel('frequency[Hz]')
			plt.grid(True)

			plt.subplot(1,2,2)
			plt.plot(KIDs[kid]['s21'].real, KIDs[kid]['s21'].imag, color=colors[i], label=kid)
			plt.plot(KIDs[kid]['I'], KIDs[kid]['Q'], 'm,')
			plt.gca().set_aspect('equal', adjustable='box')
			plt.grid(True)

			if leg:
				plt.legend()

		else:
			if cnt == 0:
				plt.figure('Sweep S21')

				plt.subplot(2,2,1)
				plt.title('Sweep magnitude')
				plt.ylabel('dB')
				plt.xlabel('frequency[Hz]')
				plt.grid(True)

				plt.subplot(2,2,3)
				plt.ylabel('Speed')
				plt.xlabel('frequency[Hz]')
				plt.grid(True)

				plt.subplot(1,2,2)
				plt.gca().set_aspect('equal', adjustable='box')
				plt.grid(True)

			plt.subplot(2,2,1)
			plt.axvline(KIDs[kid]['f0'], color='r')
			plt.plot(KIDs[kid]['f_s21'], 20*_np.log10(_np.abs(KIDs[kid]['s21'])), color=colors[cnt])

			plt.subplot(2,2,3)
			plt.axvline(KIDs[kid]['f0'], color='r')
			fs, speed = _calculate_funcs.get_speed(KIDs[kid]['f_s21'], KIDs[kid]['s21'])
			plt.plot(fs, speed, color=colors[cnt])

			plt.subplot(1,2,2)
			plt.plot(KIDs[kid]['s21'].real, KIDs[kid]['s21'].imag, color=colors[cnt], label=kid)
			plt.plot(KIDs[kid]['I'], KIDs[kid]['Q'], 'm,')

		cnt += 1

	if leg:
		if not fig_per_plot:
			plt.legend()


def plots_streams(KIDs, **kwargs):
	"""
	Plot df and PSD from the KIDs dictionary
	"""
    # parse the keyword arguments
	verbose 		= 	kwargs.pop("verbose", False)
	leg				= 	kwargs.pop("leg", True)
	fig_per_plot	=	kwargs.pop("fig_per_plot", True)

	n_kids = KIDs.keys()

	cmap = plt.get_cmap('jet')
	colors = [cmap(i) for i in _np.linspace(0, 1, len(n_kids))]

	cnt = 0
	for kid in n_kids:

		if kid == "time":
			continue

		if fig_per_plot:
			plt.figure("Noise. " + kid)

			plt.subplot(2,1,1)
			plt.plot(KIDs['time'], KIDs[kid]['df']/KIDs[kid]['f0']*1e6, color=colors[cnt])
			plt.xlabel('time[s]')
			plt.ylabel('ffs [ppm]')
			plt.grid(True)

			plt.subplot(2,1,2)
			plt.loglog(KIDs[kid]['freq'][1:], 10**((KIDs[kid]['psd'][1:]-20*_np.log10(KIDs[kid]['f0']))/10.), color=colors[cnt], label=kid)
			plt.xlabel('frequency[Hz]')
			plt.ylabel('PSD(ffs[1/Hz])')
			plt.grid(True, which="both", ls="-")

			if leg:
				plt.legend()

		else:
			if cnt == 0:
				plt.figure("Noise")

				plt.subplot(2,1,1)
				plt.xlabel('time[s]')
				plt.ylabel('ffs [Hz/Hz]')
				plt.grid(True)

				plt.subplot(2,1,2)
				plt.xlabel('frequency[Hz]')
				plt.ylabel('PSD(ffs[1/Hz])')
				plt.grid(True, which="both", ls="-")

			plt.subplot(2,1,1)
			plt.plot(KIDs['time'], KIDs[kid]['df'], color=colors[cnt])

			plt.subplot(2,1,2)
			plt.semilogx(KIDs[kid]['freq'][1:], KIDs[kid]['psd'][1:], color=colors[cnt], label=kid)

		cnt += 1

	if leg:
		if not fig_per_plot:
			plt.legend()


def plot_psd(kids, sweep_folders, stream_folders, **kwargs):
	"""
	Plot the df and PSD(df) of n kids and n folders in a subplot format
		kids			:	kids to plot
		sweep_folders	:	list of sweep folders
		stream_folders	:	list of stream folders
		sweep_folders and stream folders have the same length
	"""
    # parse the keyword arguments
	cosmic_ray	=	kwargs.pop("cosmic_ray", True)
	sample_rate =	_np.float32( kwargs.pop("sample_rate", 512e6/2**20) )
	all_kids 	= 	kwargs.pop("all_kids", False)
	stopidx		=	_np.int32(kwargs.pop("stopidx", -1))

	verbose 	= 	kwargs.pop("verbose", False)
	dB 			= 	kwargs.pop("dB", True)
	leg			= 	kwargs.pop("leg", True)
	mode		=	kwargs.pop("mode", "semi_separated")

	if not len(sweep_folders) == len(stream_folders):
		print CL.FAIL + "Sweep and stream list have to have the same length" + CL.ENDC
		return

	if mode == "all_in":
		plt.figure("All KIDs")
		plt.grid(True,which="both",ls="-")
		plt.xlabel('frequency[Hz]')
		if dB:
			ylabel = 'PSD (df) [dB]'
		else:
			ylabel = 'PSD(df) [Hz/Hz]'
		plt.ylabel(ylabel)
		plt.title("All KIDs")

	for f in range(len(stream_folders)):
		KID = get_KID_data(kids, [sweep_folders[f], stream_folders[f]], current_channel=False, sample_rate=sample_rate, filter_cos_ray=cosmic_ray, all_kids=all_kids, dB=dB, stopidx=stopidx, verbose=verbose)

		kid_to_plot = KID.keys()
		n_kids = len(kid_to_plot)

		cmap = plt.get_cmap('jet')
		colors = [cmap(i) for i in _np.linspace(0, 1, n_kids)]

		if mode == "separated":
			for kid in kid_to_plot:
				if kid == "time":
					continue
				plt.figure(stream_folders[f] + "_" + kid)
				if dB:
					ylabel = 'PSD (df) [dB]'
					plt.semilogx(KID[kid]['freq'][1:], KID[kid]['psd'][1:], label=kid)
				else:
					ylabel = 'PSD(df) [Hz/Hz]'
					plt.loglog(KID[kid]['freq'][1:], KID[kid]['psd'][1:], label=kid)

				plt.grid(True,which="both",ls="-")
				plt.xlabel('frequency[Hz]')
				plt.ylabel(ylabel)
				plt.title(stream_folders[f] + "_" + kid)
				if leg:
					plt.legend()

		elif mode == "semi_separated":

			plt.figure(stream_folders[f])
			for i, kid in enumerate(kid_to_plot):
				if kid == "time":
					continue
				if dB:
					plt.semilogx(KID[kid]['freq'][1:], KID[kid]['psd'][1:], color=colors[i], label=kid)
				else:
					plt.loglog(KID[kid]['freq'][1:], KID[kid]['psd'][1:], color=colors[i], label=kid)

			plt.grid(True,which="both",ls="-")
			plt.xlabel('frequency[Hz]')
			if dB:
				ylabel = 'PSD (df) [dB]'
			else:
				ylabel = 'PSD(df) [Hz/Hz]'
			plt.ylabel(ylabel)
			plt.title(stream_folders[f])
			if leg:
				plt.legend()

		elif mode == "all_in":

			for i, kid in enumerate(kid_to_plot):
				if kid == "time":
					continue
				if dB:
					plt.semilogx(KID[kid]['freq'][1:], KID[kid]['psd'][1:], color=colors[i], label=kid)
				else:
					plt.loglog(KID[kid]['freq'][1:], KID[kid]['psd'][1:], color=colors[i], label=kid)

	if leg and mode == "all_in":
		plt.legend()


def on_off_res(kids, sweep_folder, on_stream_folder, off_stream_folder, **kwargs):
	"""
	Get ON/OFF resonance data
	"""
	# parse the keyword arguments
	cosmic_ray	=	kwargs.pop("cosmic_ray", True)
	sample_rate 	=	_np.float32( kwargs.pop("sample_rate", 512e6/2**20) )
	all_kids 	= 	kwargs.pop("all_kids", False)
	stopidx		=	_np.int32(kwargs.pop("stopidx", -1))
	current_channel = 	kwargs.pop("current_chn", False)

	verbose 	= 	kwargs.pop("verbose", False)
	plot_result = 	kwargs.pop("plot_result", False)
	dB 			= 	kwargs.pop("dB", True)
	leg			= 	kwargs.pop("leg", True)

	# ON Resonance
	ON = get_KID_data(kids, [sweep_folder, on_stream_folder], current_channel=current_channel, sample_rate=sample_rate, filter_cos_ray=cosmic_ray, all_kids=all_kids, dB=dB, stopidx=None, verbose=verbose)

	didf = {}
	dqdf = {}
	for k in ON.keys():
		if k == "time":
			continue
		didf[k] = ON[k]['didf']
		dqdf[k] = ON[k]['dqdf']

	# OFF Resonance
	OFF = get_KID_data(kids, [sweep_folder, off_stream_folder], current_channel=current_channel, sample_rate=sample_rate, filter_cos_ray=cosmic_ray, all_kids=all_kids, dB=dB, stopidx=None, verbose=verbose)

	if plot_result:
		plt.figure("Comparison ON/OFF resonance")

		# ON resonance
		kid_to_plot = ON.keys()
		n_kids = len(kid_to_plot)

		cmap = plt.get_cmap('jet')
		colors = [cmap(i) for i in _np.linspace(0, 1, n_kids)]

		for i, kid in enumerate(kid_to_plot):
			if kid == "time":
				continue
			if dB:
				plt.semilogx(ON[kid]['freq'][1:], ON[kid]['psd'][1:], color=colors[i], label=kid)
				plt.semilogx(OFF[kid]['freq'][1:], OFF[kid]['psd'][1:], color=colors[i], alpha=0.5)
			else:
				plt.loglog(ON[kid]['freq'][1:], ON[kid]['psd'][1:], color=colors[i], label=kid)
				plt.loglog(OFF[kid]['freq'][1:], OFF[kid]['psd'][1:], color=colors[i], alpha=0.5)

		plt.grid(True,which="both",ls="-")
		plt.xlabel('frequency[Hz]')
		if dB:
			ylabel = 'PSD (df) [dB]'
		else:
			ylabel = 'PSD(df) [Hz/Hz]'
		plt.ylabel(ylabel)
		plt.title('Comparison ON/OFF resonance')
		if leg:
			plt.legend()

	return ON, OFF

def get_CFLAB_data(sweep_homodyne_folder, psd_homodyne_folder, **kwargs):
	"""
	Get all the parameter from Homodyne Cardiff lab system
	"""
	cosmic_ray	=	kwargs.pop("cosmic_ray", True)
	dB 			= 	kwargs.pop("dB", True)
	up_lim		=	_np.float32(kwargs.pop("up_lim", 110))
	down_lim	=	_np.float32(kwargs.pop("down_lm", 80))

	#+++++++++++++++++++++++++		Homodyne		++++++++++++++++++++++++++++
	# Class to reduce the data

	#sweep_path = '/home/marcial/Downloads/Data_20193004/20190304_md_c_b/20190401_Dark_Data_Prelim/KID_K000/Set_Temperature_000_K/Set_Attenuation_48dB/Sweep.fits'
	#psd_path = '/home/marcial/Downloads/Data_20193004/20190304_md_c_b/20190401_Dark_Data_Prelim/KID_K000/Set_Temperature_000_K/Set_Attenuation_48dB/TS_2000_Hz_ON_RES_x010.fits'

	data_PSD = _data_cf_lab()

	freq, sweep_i, sweep_q = data_PSD.get_vna_sweep(sweep_homodyne_folder)
	f0_fits, actual_temp, kid_number, input_att = data_PSD.get_params_from_header(sweep_homodyne_folder)
	I0, Q0, didf, dqdf, check = data_PSD.get_vna_sweep_parameters(freq, sweep_i, sweep_q, f0_fits)

	psd_ON = data_PSD.get_homodyne_psd(psd_homodyne_folder, didf, dqdf, check, 5, cosmic_ray, False)

	psd = psd_ON[2][1:]
	freq_psd = psd_ON[0][1:]

	psd_linear = 10**(psd/10)
	psd_level = _np.mean(psd_linear[_np.where(freq_psd>down_lim)[0][0]:_np.where(freq_psd<up_lim)[0][-1]])

	if dB:
		psd_level = 10*_np.log10(psd_level)
	else:
		psd = psd_linear

	# compress the data in dict format
	KID = {}
	kid_params = {}

	kid_params['f0'] = f0_fits
	kid_params['didf'] = didf
	kid_params['dqdf'] = dqdf

	kid_params['df'] = psd_ON[6]
	kid_params['freq'] = freq_psd
	kid_params['psd'] = psd

	kid_params['psd_level'] = psd_level

	kid_params['s21'] = sweep_i + 1j*sweep_q
	kid_params['f_s21'] = freq

	kid_params['I'] = psd_ON[10]
	kid_params['Q'] = psd_ON[11]

	KID[str(kid_number)] = kid_params
	KID["time"] = psd_ON[3]

	return KID


def remove_cos_ray(raw_df, npoints=51, order=3, offset_up=5, offset_down=5):
	"""
	Remove the cosmic rays with +/-5 sigmas or more
	"""
	df = _np.copy(raw_df)
	if len(df) < 2*npoints:
		print CL.FAIL + "Npoints is higher than the length of the array, select a lower value" + CL.ENDC
		return False

	sm_df = savgol_filter(df, npoints, order)
	baseline_df = df - sm_df

	std_dev = _np.std(baseline_df)

	up_thresh = sm_df + offset_up*std_dev
	down_thresh = sm_df - offset_down*std_dev

	mask = [t<up_thresh[i] and t>down_thresh[i]	for i, t in enumerate(df)]

	mu = _np.mean(baseline_df)
	for i, flag in enumerate(mask):
		if not flag:
			df[i] = sm_df[i] + _np.random.normal(mu, std_dev, 1)

	return df


def _get_shortest_folder(folders):
	"""
	Get the shortest folder from a list of folders
	"""
	size_folder = []
	for folder in folders:
		total_size = 0
		for dirpath, dirnames, filenames in _os.walk(folder):
			for f in filenames:
				fp = _os.path.join(dirpath, f)
				if not _os.path.islink(fp):
					total_size += _os.path.getsize(fp)
		size_folder.append(total_size)
	return folders[_np.argmin(size_folder)]


def psd_avg_per_kid(kids, sweep_folder, folders, **kwargs):
	"""
	Average the psd of a set of stream folders.
	If the size of the folders is different, take the smallest one, or if stopidx is different
	to -1 this parameter define the size of the array
	"""

	cosmic_ray	=	kwargs.pop("cosmic_ray", True)
	sample_rate =	_np.float32( kwargs.pop("sample_rate", 512e6/2**20) )
	all_kids 	= 	kwargs.pop("all_kids", False)
	stopidx		=	_np.int32(kwargs.pop("stopidx", -1))

	dB 			= 	kwargs.pop("dB", True)
	verbose 	= 	kwargs.pop("verbose", False)

	# get the min time stream
	f_min = _get_shortest_folder(folders)

	print CL.WARNING + "In order to average plots, they have to be of the same length." + CL.ENDC
	print CL.WARNING + "Automatically this script adjust the data to the minimum folder: " + f_min + CL.ENDC

	m_time = len(_calculate_funcs.get_stream_data(f_min)[0])

	psd_per_kid = {}
	psd_mean_kid = {}

	psd_level_per_kid = {}
	psd_level_mean = {}

	cnt = 0
	for folder in folders:

		# get the PSD of each folder
		if stopidx == -1:
			trim = m_time
		else:
			trim = stopidx

		KID = get_KID_data(kids, [sweep_folder, folder], current_channel=False, sample_rate=sample_rate, filter_cos_ray=cosmic_ray, all_kids=all_kids, dB=False, stopidx=trim, verbose=verbose)

		post_kids = KID.keys()
		n_kids = len(post_kids)

		for kid in post_kids:
			if kid == "time":
				continue
			k_nm = kid
			if cnt == 0:
				psd_per_kid[kid] = KID[kid]['psd']
				psd_level_per_kid[kid] = KID[kid]['psd_level']
			else:
				psd_per_kid[kid] += KID[kid]['psd']
				psd_level_per_kid[kid] += KID[kid]['psd_level']

			if cnt == len(folders) - 1:
				psd_mean_kid[kid] = psd_per_kid[kid]/len(folders)
				psd_level_mean[kid] = psd_level_per_kid[kid]/len(folders)

				if dB:
					psd_mean_kid[kid] = 10*_np.log10(psd_mean_kid[kid])
					psd_level_mean[kid] = 10*_np.log10(psd_level_mean[kid])

				KID[k_nm]['psd_level'] = psd_level_mean[kid]
				KID[k_nm]['psd'] = psd_mean_kid[kid]

				KID[k_nm]['I'] = None
				KID[k_nm]['Q'] = None
				KID[k_nm]['df'] = None

		cnt += 1

	return KID


def save_current_figs():
	"""
	Save figures open with the suptitle name
	"""

	figs = [plt.figure(n) for n in plt.get_fignums()]
	for fig in figs:
		fig.set_size_inches(19, 10)
		fig.savefig(fig._suptitle.get_text()+'.png', format='png')
		plt.close(fig)
		print fig._suptitle.get_text()

	print "Done"


def main():
	print CL.OKGREEN + "Functions to noise plotting loaded!" + CL.ENDC
	#names = ['ch1','ch2','ch3','ch4','ch5','ch6']

	# ON resonance
	# phantom
	on_file_name = '/home/marcial/data_readout/phantom/20190905_153407'
	# clones
	#file_name = '/home/marcial/data_readout/clones/20190905_155646'
	# empire
	#file_name = '/home/marcial/data_readout/sith/20190905_140043'
	# hope
	#file_name = '/home/marcial/data_readout/hope/20190905_162201'
	# empire
	#file_name = '/home/marcial/data_readout/empire/20190905_164942'
	# jedi
	#file_name = '/home/marcial/data_readout/jedi/20190905_171826'

	# OFF Resonance
	#off_file_name = '/home/marcial/data_readout/sith/20190905_125739'
	off_file_name = '/home/marcial/data_readout/clones/20190905_155646'
