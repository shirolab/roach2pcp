#!/usr/bin/env python
# -*- coding: utf-8 -*-
#************************************************************
#*                    Data Reduction                        *
#*          		 Marcial Becerril			            *
#************************************************************

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
#from dataRed import dataRed

class remCosRay():
	def savgol(self,time, x, grade):

		coeff = [[-3,12,17,12,-3],
				  [-2,3,6,7,6,3,-2],
				  [-21,14,39,54,59,54,39,14,-21],
				  [-36,9,44,69,84,89,84,69,44,9,-36],
				  [-253-138,-33,62,147,222,287,343,387,422,447,462,467,462,447,422,387,343,287,222,147,62,-33,-238,-253]]

		N = len(x)

		p = len(coeff[grade])
		y = []

		#Algoritmo Savikzky-Golay
		for i in range(int(N - p + 1)):
			aux = 0
			for j in range(p):
				aux = aux + coeff[grade][j]*x[i + j]
			y.append((1.0/sum(coeff[grade]))*aux)

		ntime = time[(p-1)/2:int(N-(p-1)/2)]

		return ntime, y

	def findCosmicRay(self,time,signal,sigma):

		# Get the STD
		median = np.median(signal)
		mean = np.mean(signal)
		std = np.std(signal)

		cond_border_pos = sigma*std + median
		cond_border_neg = -sigma*std + median

		cand = np.where((signal > cond_border_pos) | (signal < cond_border_neg))
		diff_cand = np.diff(cand)
		lim_index = np.where(diff_cand > 1)

		cand = np.array(cand)[0]

		if len(cand) > 0:

			edges = lim_index[1]
			edges = edges + 1
			edges = np.concatenate([[0],edges,[len(diff_cand[0])+1]])

			flagRmFull = False

			for i in range(len(edges)-1):
				m = cand[edges[i]:edges[i+1]]

				"""
				plt.plot(time,signal)
				plt.plot([np.min(time),np.max(time)],[sigma*std + median,sigma*std + median])
				plt.plot([np.min(time),np.max(time)],[mean,mean])
				plt.plot([np.min(time),np.max(time)],[median,median])
				plt.plot([np.min(time),np.max(time)],[-sigma*std + median,-sigma*std + median])

				plt.plot(time[m],signal[m],'r*')

				#plt.show()
				"""

				temp_cosmic_ray = time[m]
				# Backwards
				stop = m[0]
				while stop != 0:
					stop -= 1
					if signal[stop] > median + 1.1*std or signal[stop] < median - 1.1*std:
						m = np.concatenate([[stop],m])
					else:
						break
				# Forwards
				stop = m[-1]
				while stop != len(time)-1:
					stop += 1
					if signal[stop] > median + 1.1*std or signal[stop] < median - 1.1*std:
						m = np.concatenate([m,[stop]])
					else:
						break


				#plt.plot(time[m],signal[m],'r*--')

				# Remove noise area and replace with gaussian noise
				n_signal = signal
				n_signal[m] = np.random.normal(mean,std,len(m))

				#plt.plot(time,n_signal,'co--')

				#plt.show()

				if len(m) > 6:
					flagRmFull = True
					break
				else:
					flagRmFull = False

			# Number of tolerable points
			if flagRmFull == False:

				#cos_ray_time.append(time[m])
				#cos_ray_mag.append(signal[m])
				#pos.append(m)

				#print "Reparado"

				return time,n_signal,False
			else:

				"""
				plt.plot(time,signal)
				plt.plot([np.min(time),np.max(time)],[sigma*std + median,sigma*std + median])
				plt.plot([np.min(time),np.max(time)],[mean,mean])
				plt.plot([np.min(time),np.max(time)],[median,median])
				plt.plot([np.min(time),np.max(time)],[-sigma*std + median,-sigma*std + median])

				plt.plot(time[m],signal[m],'r*')

				plt.show()
				"""

				#print "Bailó Bertha!"

				return time,signal,True

		else:
			return time,signal,False

		#plt.plot(smooth_time, smooth_sig)
		plt.plot(time,signal)
		plt.plot([np.min(time),np.max(time)],[sigma*std + median,sigma*std + median])
		plt.plot([np.min(time),np.max(time)],[mean,mean])
		plt.plot([np.min(time),np.max(time)],[median,median])
		plt.show()

	def deltaResponse(self,x, A, a, f):
		return A*np.exp(-a*x)*np.sin(2*np.pi*f*x)

	def fitCurve(self,time,signal):
		time = (time - np.min(time))
		popt, pcov = curve_fit(self.deltaResponse, time, signal, bounds=([0, 0, 0], [1, 1e4, 1e3]))
		fit_signal = deltaResponse(time, *popt)

		# Plot fit curve
		plt.plot(time,fit_signal)
		plt.plot(time,signal)
		plt.plot(time,signal-fit_signal)

		plt.show()

"""
path = "/media/marcial/Windows8_OS/Users/Marcial/Documents/FASS_2_2a/FASS_2_2a/20180802_Dark_Data_Auto/KID_K052/Set_Temperature_000_mK/Set_Attenuation_44dB"
dataRedtn = dataRed()
freq, sweep_i, sweep_q, freq_hr, sweep_i_hr, sweep_q_hr,  psd, psd_low, psd_OFF, psd_low_OFF, f0_meas, f0_fits = dataRedtn.get_all_data(path)

time = psd_low_OFF[3]

for i in range(len(psd_OFF[10])):
	I = psd_OFF[10][i]
	Q = psd_OFF[11][i]

#I[0:500] = I[-501:-1]

	cr = remCosRay()
	time,n_signal,flagRm = cr.findCosmicRay(time,I,4.5)
	print flagRm

	time,n_signal,flagRm = cr.findCosmicRay(time,Q,4.5)
	print flagRm
"""
