import numpy as np
import sys, os
import matplotlib.pyplot as plt
import scipy.ndimage

#bb_freqs = np.load(os.path.join(path,'bb_freqs.npy'))
#lo_freqs = np.load(os.path.join(path,'sweep_freqs.npy'))
accum_len = 2**19
def openStored(path):
	files = sorted(os.listdir(path))
	I_list = [os.path.join(path, filename) for filename in files if filename.startswith('I')]
	Q_list = [os.path.join(path, filename) for filename in files if filename.startswith('Q')]
	chan_I = np.array([np.load(filename) for filename in I_list])
	chan_Q = np.array([np.load(filename) for filename in Q_list])
	return chan_I, chan_Q

def compute_dI_and_dQ(I,Q,freq=None,filterstr='SG',do_deriv=True):
	#Given I,Q,freq arrays
	#input filterstr = 'SG' for sav-gol filter with builtin gradient, 'SGgrad' savgol then apply gradient to filtered
	#do_deriv: if want to look at filtered non differentiated data
	if freq==None:
		df=1.0
	else:
    	df = freq[1]-freq[0]
    dI=filtered_differential(I, df,filtertype=filterstr,do_deriv=do_deriv)
    dQ=filtered_differential(Q, df,filtertype=filterstr,do_deriv=do_deriv)
    return dI,dQ
   
def filtered_differential(data,df,filtertype=None,do_deriv=True):
    '''take 1d array data with spacing df. return filtered version of data depending on filterrype'''
    if filtertype==None:
        out = np.gradient(data,df)
    #plotting dI/df and dQ/df unfiltered
    window=13; n=3
    if filtertype=='SG':
        if do_deriv==True:  
            out = savgol_filter(data, window, n, deriv=1, delta=df)
        else:
            out = savgol_filter(data, window, n, deriv=0, delta=df)
    if filtertype=='SGgrad':    
        tobegrad = savgol_filter(data, window, n)
        out = np.gradient(tobegrad,df)
    return out

def filter_trace(path, bb_freqs, lo_freqs):
	chan_I, chan_Q = openStored(path)
	channels = np.arange(np.shape(chan_I)[1])
	mag = np.zeros((len(channels),len(lo_freqs)))
	chan_freqs = np.zeros((len(channels),len(lo_freqs)))
	for chan in channels:
		mag[chan] = (np.sqrt(chan_I[:,chan]**2 + chan_Q[:,chan]**2)) 
		chan_freqs[chan] = (lo_freqs + bb_freqs[chan])/1.0e6
	mag = np.concatenate((mag[len(mag)/2:], mag[:len(mag)/2]))
	mags = np.hstack(mag)
	mags /= (2**17 - 1)
	mags /= (accum_len/ 512)
	mags = 20*np.log10(mags)
	chan_freqs = np.hstack(chan_freqs)
	chan_freqs = np.concatenate((chan_freqs[len(chan_freqs)/2:],chan_freqs[:len(chan_freqs)/2]))
	return chan_freqs, mags

def lowpass_cosine( y, tau, f_3db, width, padd_data=True):
        # padd_data = True means we are going to symmetric copies of the data to the start and stop
	# to reduce/eliminate the discontinuities at the start and stop of a dataset due to filtering
	#
	# False means we're going to have transients at the start and stop of the data

	# kill the last data point if y has an odd length
	if np.mod(len(y),2):
		y = y[0:-1]

	# add the weird padd
	# so, make a backwards copy of the data, then the data, then another backwards copy of the data
	if padd_data:
		y = np.append( np.append(np.flipud(y),y) , np.flipud(y) )

	# take the FFT
        import scipy
        import scipy.fftpack
	ffty=scipy.fftpack.fft(y)
	ffty=scipy.fftpack.fftshift(ffty)

	# make the companion frequency array
	delta = 1.0/(len(y)*tau)
	nyquist = 1.0/(2.0*tau)
	freq = np.arange(-nyquist,nyquist,delta)
	# turn this into a positive frequency array
	pos_freq = freq[(len(ffty)/2):]

	# make the transfer function for the first half of the data
	i_f_3db = min( np.where(pos_freq >= f_3db)[0] )
	f_min = f_3db - (width/2.0)
	i_f_min = min( np.where(pos_freq >= f_min)[0] )
	f_max = f_3db + (width/2);
	i_f_max = min( np.where(pos_freq >= f_max)[0] )

	transfer_function = np.zeros(len(y)/2)
	transfer_function[0:i_f_min] = 1
	transfer_function[i_f_min:i_f_max] = (1 + np.sin(-np.pi * ((freq[i_f_min:i_f_max] - freq[i_f_3db])/width)))/2.0
	transfer_function[i_f_max:(len(freq)/2)] = 0

	# symmetrize this to be [0 0 0 ... .8 .9 1 1 1 1 1 1 1 1 .9 .8 ... 0 0 0] to match the FFT
	transfer_function = np.append(np.flipud(transfer_function),transfer_function)

	# apply the filter, undo the fft shift, and invert the fft
	filtered=np.real(scipy.fftpack.ifft(scipy.fftpack.ifftshift(ffty*transfer_function)))

	# remove the padd, if we applied it
	if padd_data:
		filtered = filtered[(len(y)/3):(2*(len(y)/3))]

	# return the filtered data
        return filtered
	
def main(path):
	bb_freqs = np.load(os.path.join(path,'bb_freqs.npy'))
	lo_freqs = np.load(os.path.join(path,'sweep_freqs.npy'))
	
	sweep_step = 2.5 # kHz
	smoothing_scale = 10000.0 # kHz
	peak_threshold = 2. # mag units
	spacing_threshold = 1000.0 # kHz
	
	chan_freqs,mags = filter_trace(path, bb_freqs, lo_freqs)
	filtermags = lowpass_cosine( mags, sweep_step, 1./smoothing_scale, 0.1 * (1.0/smoothing_scale))
	plt.ion()
	plt.figure(1)
	plt.clf()
	plt.plot(chan_freqs,mags,'b',label='#nofilter')
	plt.plot(chan_freqs,filtermags,'g',label='Filtered')
	plt.xlabel('frequency (MHz)')
	plt.ylabel('dB')
	plt.legend()

	plt.figure(2)
	plt.clf()
	plt.plot(chan_freqs,mags-filtermags,'b')
	ilo = np.where( (mags-filtermags) < -1.0*peak_threshold)[0]
	plt.plot(chan_freqs[ilo],mags[ilo]-filtermags[ilo],'r*')
	plt.xlabel('frequency (MHz)')

	iup = np.where( (mags-filtermags) > -1.0*peak_threshold)[0]
	new_mags = mags - filtermags
	new_mags[iup] = 0
	labeled_image, num_objects = scipy.ndimage.label(new_mags)
	indices = scipy.ndimage.measurements.minimum_position(new_mags,labeled_image,np.arange(num_objects)+1)
	kid_idx = np.array(indices, dtype = 'int')
	
	
	#region1 = kid_idx[(chan_freqs[kid_idx] > 590.)]
	#region2 = kid_idx[(chan_freqs[kid_idx] < 751.)]
	#region3 = kid_idx[(chan_freqs[kid_idx] > 779.)]
	#region4 = kid_idx[(chan_freqs[kid_idx] < 1035.)]

	#print len(kid_idx)
	#new_kid_idx = []
	#for i in range(len(kid_idx)):
	#	if (kid_idx[i] in region1) & (kid_idx[i] in region2):
	#		new_kid_idx.append(kid_idx[i])
	#	if (kid_idx[i] in region3) & (kid_idx[i] in region4):
	#		new_kid_idx.append(kid_idx[i])

	#kid_idx = np.array(new_kid_idx)
	print len(kid_idx)
	print kid_idx
	del_idx = []
	for i in range(len(kid_idx) - 1):
		spacing = (chan_freqs[kid_idx[i + 1]] - chan_freqs[kid_idx[i]]) * 1.0e3
		if (spacing < spacing_threshold):
			print spacing, spacing_threshold
			print "Spacing conflict"
			if (new_mags[kid_idx[i + 1]] < new_mags[kid_idx[i]]):
				del_idx.append(i)
			else: 
				del_idx.append(i + 1)

	del_idx = np.array(del_idx) 
	print "Removing " + str(len(del_idx)) + " KIDs"
	print
	kid_idx = np.delete(kid_idx, del_idx)

	del_again = []
	for i in range(len(kid_idx) - 1):
		spacing = (chan_freqs[kid_idx[i + 1]] - chan_freqs[kid_idx[i]]) * 1.0e3
		if (spacing < spacing_threshold):
			print "Spacing conflict"
			print spacing, spacing_threshold
			if (new_mags[kid_idx[i + 1]] < new_mags[kid_idx[i]]):
				del_again.append(i)
			else: 
				del_again.append(i + 1)

	del_again = np.array(del_again) 
	print "Removing " + str(len(del_again)) + " KIDs"
	print
	kid_idx = np.delete(kid_idx, del_again)

	
	plt.figure(4)
	plt.clf()
	plt.plot(chan_freqs, mags,'b')
	plt.plot(chan_freqs[kid_idx], mags[kid_idx], 'r*')
	plt.xlabel('frequency (MHz)')
	plt.ylabel('dB')
	# list of kid frequencies
	target_freqs = chan_freqs[kid_idx]
	print len(target_freqs), "pixels found"
	print "Freqs =", chan_freqs[kid_idx]
	prompt = raw_input('Save target freqs in ' + path + ' (y/n) (may overwrite) ? ')
	if prompt == 'y':
		np.save(path + '/target_freqs.npy', chan_freqs[kid_idx])
	return

def read_tonelist(fname,lofreq = 0):
	"""Reads in the .txt tonelist generated by the Labview program and 
	returns the RF frequencies. First pass only extracts F0s and discards all other information.
	Optional argument lofreq; if 0, returns the RF frequencies, otherwise returns (rffreqs - lofreqs)"""
	return np.genfromtxt(fname, delimiter='\t', unpack=True)[1] - lofreq


# read in files
def importIQsweep(sweepdir):
	# read in corresponding sweeps
	sweepfs = [os.path.join(sweepdir, f) for f in os.listdir(sweepdir) if 'I' in f or 'Q' in f]
	
	# each sweep data file contain numtones points, each being an average of N packets taken at single LO frequency
	swpdata = np.load(sweepfs[0])
	
	iidx = np.arange(len(swpdata)/2)
	qidx = np.arange(len(swpdata)/2) + len(swpdata)/2
	
	ifs = sweepfs[::2]
	qfs = sweepfs[1::2]
	print 'There are {nres} resonators each with {npoint} points in the sweep'.format(npoint=len(ifs), nres=len(swpdata))
	
	# read in each file, append to list, create array and transpose
	iswp = np.array([np.load(f) for f in ifs]).T
	qswp = np.array([np.load(f) for f in qfs]).T
	zswp = iswp+1j*qswp
# 	
# 	plt.plot(zswp.T.real, zswp.T.imag)
# 	plt.plot(zdata[:,::100].T.real, zdata[:,::100].T.imag) # plot every 100 points so as not to break the graphics
	return iswp,qswp


