import numpy as np
import matplotlib.pyplot as plt
import os
# read in files

os.chdir(os.path.dirname(os.path.abspath(__file__)))
timestreamdir = 'timestreamtest1'
fs = [os.path.join(timestreamdir, f) for f in os.listdir(timestreamdir)]

dataI = np.load(fs[0])
dataQ = np.load(fs[1])

zdata = (dataI + 1j*dataQ).T

# read in corresponding sweeps
sweepdir = 'sweeptest01'
sweepfs = np.array([os.path.join(sweepdir, f) for f in os.listdir(sweepdir) if 'I' in f or 'Q' in f])

lofreqs = np.load(os.path.join(sweepdir, 'sweep_freqs.npy'))
bb_freqs = np.load(os.path.join(sweepdir, 'bb_freqs.npy')).astype(int)

swpfreqs = bb_freqs[:,np.newaxis] + lofreqs
# each sweep data file contain numtones points, each being an average of N packets taken at single LO frequency

iidx = np.arange(len(lofreqs))
qidx = np.arange(len(lofreqs)) + len(lofreqs)

ifs = sweepfs[iidx]
qfs = sweepfs[qidx]

# read in each file, append to list, create array and transpose
iswp = np.array([np.load(f) for f in ifs]).T
qswp = np.array([np.load(f) for f in qfs]).T
zswp = iswp+1j*qswp

print 'There are {nres} resonators each with {npoint} points in the sweep'.format(npoint=len(ifs), nres=iswp.shape[0])

plt.figure()
plt.plot(zswp.T.real, zswp.T.imag)
plt.plot(zdata[:,::100].T.real, zdata[:,::100].T.imag) # plot every 100 points so as not to break the graphics

fig1, (ax11, ax12) = plt.subplots(2,1)
ax11.plot(swpfreqs.T, abs(zswp.T))
ax12.plot(swpfreqs.T[1:], abs(np.diff(zswp,axis=1)).T)

plt.show()

# calculate didq



# ----------- blind tone spacing algorithm -----------
# based on KID tones, place a user defined number of blind tones in places that wont intefere with KIDSweep
# determine bandwith of KID tones * 10% to open either side
# have multiple modes
#   - n tones in between resonators
#   - n tones maximally spaced

# place uniformly distriution of blinds and remove if too close to tones
# find median spacing of tones

tonelist = os.path.join(sweepdir, 'target_freqs.npy')
kidf0s = np.load(tonelist)
plt.figure()

[plt.axvline(k,alpha=0.5) for k in kidf0s]

bwkids = (kidf0s[-1] - kidf0s[0])
cenfreq = (kidf0s[-1] + kidf0s[0])/2

bwtones = np.around(bwkids*1.1)


nblinds = 21

blindf0s = np.linspace(cenfreq - bwtones/2., cenfreq + bwtones/2., nblinds)
[plt.axvline(k, linestyle='--') for k in blindf0s]

dkids = np.diff(kidf0s)

# remove any tones closer than average spacing between kids

b = np.min( abs(kidf0s[:,np.newaxis] - blindf0s).T , axis=1) # kidf0s - blindf0s find the mininmum

blindf0s = blindf0s[b > np.median(dkids)]

[plt.axvline(f,c='g') for f in blindf0s]
plt.show()
