
def check_sweep_lo_steps(dirfile,kidnum,startidx=10,stopidx=20):
    import pygetdata as gd
    from matplotlib.pyplot import *
    
    df = gd.dirfile(dirfile,gd.RDONLY)
    z  = df.getdata('K%03d_z'%kidnum)
    lotimes = df.getdata( "lostep_times" )
    ptimes  = df.getdata( "python_timestamp" ) # way to get the python_timestamp fie
ld with knowing any field suffix
    lofreqs = df.getdata( "lo_freqs" )

    # align LO steps with python timestreams
    idxs = np.searchsorted(ptimes, lotimes) # miss out the first point (should a
lways be 0)
    figure()
    plot(abs(z))
    [axvline(i,color='k') for i in idxs]
    [axvline(i+startidx,color='g') for i in idxs]
    [axvline(i+stopidx,color='r') for i in idxs]
    title(dirfile + ': K%03d_z'%kidnum)
    show()
    
    
#NoTES:
#ch1 synth fails if autocall is OFF, also is slowest to change
#ch2 timelines have a weird bump sometimes after switching LO, independent of autocall setting
#PLL mute till LD causes dips between steps, but avoids random switching between steps
#Feedback select = 0 (divided) seems to remove bump in ch2
#charage pump current:was 3, tried 1 and 6, no discernable difference

