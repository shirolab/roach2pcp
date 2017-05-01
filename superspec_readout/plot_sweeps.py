import os
import numpy as np
import matplotlib.pyplot as plt

def open_stored(save_path = None):
	files = sorted(os.listdir(save_path))
	sweep_freqs = np.array([np.float(filename[1:-4]) for filename in files if (filename.startswith('I'))])
	I_list = [os.path.join(save_path, filename) for filename in files if filename.startswith('I')]
	Q_list = [os.path.join(save_path, filename) for filename in files if filename.startswith('Q')]
	Is = np.array([np.load(filename) for filename in I_list])
	Qs = np.array([np.load(filename) for filename in Q_list])
	return sweep_freqs, Is, Qs

def plot_vnas(paths):
# paths = a list of tuples: [ (path1, temp1), (path2, temp2) ....
	plt.ion()
	figure = plt.figure(5, figsize = (20,12))
	ax = figure.add_subplot(1,1,1)
	plt.tick_params(labelsize=25)
	#ax.tick_params(axis='x', labelsize=25, which = 'both', width = 2)
	#ax.tick_params(axis='y', labelsize=25, which = 'both', width = 2)
	plt.clf()
	for entry in paths:
		path = entry[0]
		lab = entry[1]
		c = entry[2]
		sweep_freqs, Is, Qs = open_stored(path)
		sweep_freqs = np.load(path + '/sweep_freqs.npy')
		bb_freqs = np.load(path + '/bb_freqs.npy')
		rf_freqs = np.zeros((len(bb_freqs),len(sweep_freqs)))
		for chan in range(len(bb_freqs)):
			rf_freqs[chan] = (sweep_freqs + bb_freqs[chan])/1.0e6
		Q = np.reshape(np.transpose(Qs),(len(Qs[0])*len(sweep_freqs)))
		I = np.reshape(np.transpose(Is),(len(Is[0])*len(sweep_freqs)))
		mag = np.sqrt(I**2 + Q**2)
		mag /= (2**17 - 1)
		mag /= ((2**19) / (512))
		mag = 20*np.log10(mag)
		mag = np.concatenate((mag[len(mag)/2:],mag[:len(mag)/2]))
		rf_freqs = np.hstack(rf_freqs)
		rf_freqs = np.concatenate((rf_freqs[len(rf_freqs)/2:],rf_freqs[:len(rf_freqs)/2]))
		plt.xlim(591, 1000)
		plt.ylim(-92, -52)
		plt.plot(rf_freqs, mag, alpha = 0.7, label = lab, color = c)
	plt.legend(loc = 'upper right', fontsize = 28)
	plt.xlabel('frequency (MHz)', fontsize = 28)
	plt.ylabel('dBm', fontsize = 18)
	plt.tight_layout()
	plt.savefig('./two_temp.png', bbox_inches = 'tight', dpi = 200)
	return


