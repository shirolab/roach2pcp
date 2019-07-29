# Quick-look live-monitoring software for SuperSpec
# This is a one-way street: data are saved to the control computer and
# this simply plots it - no commands are sent to the ROACH,
# housekeeping, or telescope computers!
#
# Requires pykst
#

import pykst as kst
import glob, os
import pygetdata as gd
import numpy as np

#################################################################3
# Auxiliary functions

def find_latestfile(dataloc = "/data/dirfiles/roach0/",
                    datapattern = "20??????_??????"):
    list_of_files = glob.glob(dataloc + datapattern)
    latest_file = max(list_of_files, key = os.path.getctime)
    return latest_file

def find_lastsweep(dataloc = '/data/dirfiles/roach0/',
                   datapattern = "20??????_??????_sweep"):
    list_of_files = glob.glob(dataloc + datapattern)
    latest_file = max(list_of_files, key = os.path.getctime)
    return latest_file
    
def kill(client):
    client.clear()
    client.quit()

def frametype(type = "lastnmins", f_s = 122.0, m2r = 2., ds = 1.):
    """ Data vectors require parameters to control how many data frames are
        read and plotted (see pykst documentation) - outputted in dict:
        start: starting index of vector, -1 for count from end
        num_frames: number of frames to read, -1 for read to end
        skip: number of frames to skip, 0 to read everything

        Arguments:
        type:
          'all':       Plot everything in the dirfile (not recommended)
          'lastnmins': Plot last n mins.  Frame count determined by f_s
          'firstnmins': Plot first n mins 
        fs: Sampling rate, Hz
        m2r: Minutes to read
        ds: downsampling factor (1 = none, 2 = every other frame, etc.)
    """
    skip = ds - 1
        
    if type == "all":
        start = -1
        num_frames = -1
    if type == "lastnmins":
        start = -1
        num_frames = f_s * 60 * m2r
    if type == "firstnmins":
        start = 1
        num_frames = f_s * 60 * m2r

    # Assemble everything into a dict.  Need to be ints!
    framedict = {'start'      : int(start),
                 'num_frames' : int(num_frames),
                 'skip'       : int(skip)}
    return framedict

def check_timestamp(x_axis, plothandle):
    if x_axis == "python_timestamp":
        plothandle.set_x_axis_interpretation(interp = 'ctime')
        plothandle.set_x_axis_display(display = "yyyy-MM-dd hh:mm:ss")
        plothandle.set_bottom_label(' ') # Adding another label clutters too much
    return

def process_sweep(sweepfile = None):
    """ Given a 'processed' sweep file, generate 
        I_fo, Q_fo, dIdf, dQdf and return a dict for all KIDs
    """
    if sweepfile == None:
        sweepfile = find_lastsweep()

    # Load in dirfile
    df = gd.dirfile(sweepfile, gd.RDONLY | gd.UNENCODED)
    lo = df.get_carray('sweep.lo_freqs')
    bb = df.get_carray('sweep.bb_freqs')
    
    # Get a list of KIDs...super non-robust
    kidlist = []
    for key in df.field_list():
        if (key[-4] == 'K') or (key[-4] == 'B'):
            kidlist.append(key[-4:])

    # Index for f0...probably a smarter way to do this
    ind = len(lo)/2

    # Build up sweepdict
    sweepdict = {}
    for kid in kidlist:
        thisdict = {}
        kidind = int(kid[-3:])
        thisdict['f0'] = lo[ind] + bb[kidind]
        mysweep = df.get_carray('sweep.' + kid)
        thisdict['I_f0'] = np.real(mysweep[ind])
        thisdict['Q_f0'] = np.imag(mysweep[ind])
        # Use the two points around f0 to get a slope
        thisdict['dIdf'] = (np.real(mysweep[ind+1]-mysweep[ind-1]))/ \
                           (lo[ind+1]-lo[ind-1])
        thisdict['dQdf'] = (np.imag(mysweep[ind+1]-mysweep[ind-1]))/ \
                           (lo[ind+1]-lo[ind-1])
        sweepdict[kid] = thisdict
    
    return sweepdict

def equationstring_df_x(chan, sweepdict, Ifield, Qfield):
    # ((I_f0-I)*dIdf + (Q_f0-Q)*dQdf)/(dIdf^2 + dQdf^2)
    f0 = sweepdict[chan]['f0']
    I_f0 = sweepdict[chan]['I_f0']
    Q_f0 = sweepdict[chan]['Q_f0']
    dIdf = sweepdict[chan]['dIdf'] # at f0
    dQdf = sweepdict[chan]['dQdf']

    eqnstring_df = '(((%3f-[' % (I_f0) + Ifield + '])*(%3f))'  % (dIdf) + \
                   '+((%3f-[' % (Q_f0) + Qfield + '])*(%3f)))' % (Q_f0) + \
                   '/((%3f)^2 + (%3f)^2)  '                    % (dIdf,dQdf)
    eqnstring_x = '((((%3f-[' % (I_f0) + Ifield + '])*(%3f))' % (dIdf) + \
                  '+((%3f-[' % (Q_f0) + Qfield + '])*(%3f)))' % (dQdf) + \
                  '/((%3f)^2 + (%3f)^2)) '                    % (dIdf,dQdf) + \
                  '/%3f '                                     % (f0)

    return eqnstring_df, eqnstring_x

def equationstring_IQ(eqn, Ifield, Qfield, sweepdict = None):
    """ Return a kst equation involving fields I and Q
    """
    if eqn == "mag":
        eqnstring = 'SQRT([' + Ifield + ']^2 + [' + Qfield + ']^2)'
    if eqn == "phase":
        eqnstring = 'ATAN([' + Ifield + ']/[' + Qfield + '])'
    if (eqn == "df") or (eqn == "x"):
        f0 = sweepdict['f0']
        I_f0 = sweepdict['I_f0']
        Q_f0 = sweepdict['Q_f0']
        dIdf = sweepdict['dIdf'] # at f0
        dQdf = sweepdict['dQdf']
        if eqn == "df":
            eqnstring = '(((%3f-[' % (I_f0) + Ifield + '])*(%3f))'  % (dIdf) + \
                        '+((%3f-[' % (Q_f0) + Qfield + '])*(%3f)))' % (Q_f0) + \
                        '/((%3f)^2 + (%3f)^2)  '                    % (dIdf,dQdf)
        if eqn == "x":
            eqnstring = '((((%3f-[' % (I_f0) + Ifield + '])*(%3f))' % (dIdf) + \
                        '+((%3f-[' % (Q_f0) + Qfield + '])*(%3f)))' % (dQdf) + \
                        '/((%3f)^2 + (%3f)^2)) '                    % (dIdf,dQdf) + \
                        '/%3f '                                     % (f0)
            
    return eqnstring

#################################################################3
# Plotting functions

def plot_dirfile_rawfield(myfields, datafile, client_name = None,
                          x_axis = "python_timestamp", fd = None):
    """ Plot raw fields from a dirfile
    Inputs:
       myfield: string for dirfile field, e.g. 'K000_I'
                Can be a list of strings
       datafile: dirfile or .txt sourcefile
       client_name: string for title of plot, unique handle
       x_axis: python timestamp for human-readability, 
               kst default is "INDEX" (frame count, 1 per packet)
       fd: frame dict
    """
    if type(myfields) == str:
        myfields = [myfields]

    if fd == None:
        fd = frametype()

    client = kst.Client(client_name)
    client.hide_window()
    X = client.new_data_vector(datafile,
                               field = x_axis,
                               start = fd['start'],
                               num_frames = fd['num_frames'],
                               skip = fd['skip'])

    for field in myfields:
        y_axis = field
        Y = client.new_data_vector(datafile,
                                   field = y_axis,
                                   start = fd['start'],
                                   num_frames = fd['num_frames'],
                                   skip = fd['skip'])

        c1 = client.new_curve(X,Y)
        p1 = client.new_plot()
        L1 = client.new_legend(p1)
        p1.add(c1)

        check_timestamp(x_axis, p1)

    client.show_window()
    return client

def plot_sweep(chanlist, sweepfile = None, client_name = None):
    """ Quickly plot result of the derived sweep dirfile
    Inputs:
       chanlist: list of KIDs, e.g. ['K000','K002']
                 Looks for fields 'sweep.K000' in 'entry'
       sweepfile: dirfile, default is latest matching 
                  'yyyymmdd_hhmmss_sweep'
       client_name: string for title of plot, unique handle
                    default is sweep dirfile name
    """
    if type(chanlist) == str:
        chanlist = [chanlist]

    if sweepfile == None:
        sweepfile = find_lastsweep()

    if client_name == None:
        # Client name can't start with number
        client_name = 'sweep_' + sweepfile[-21:-6] 

    # Load in dirfile and static fields
    df = gd.dirfile(sweepfile, gd.RDONLY | gd.UNENCODED)
    lo = df.get_carray('sweep.lo_freqs')/1e6 # MHz
    bb = df.get_carray('sweep.bb_freqs')/1e6 # MHz
    
    client = kst.Client(client_name)
    client.hide_window()

    for chan in chanlist:
        # Find BB freq for this chan - super janky
        ind = np.int(chan[-3:])
        
        F = client.new_editable_vector(lo + bb[ind])
        s21 = df.get_carray('sweep.' + chan)
        S21 = client.new_editable_vector(10*np.log10(np.abs(s21)))
        S21.set_name(chan)
        
        c1 = client.new_curve(F,S21)
        p1 = client.new_plot()

        p1.set_bottom_label('Frequency (MHz)')
        p1.set_left_label('10*log10(mag)')
        p1.set_top_label(chan)
        p1.add(c1)

    client.show_window()
    return client

def plot_dirfile_IQequation(chanlist, datafile, client_name = None,
                            eqnlist = ["mag"], sweepdict = None,
                            sweepfile = None,
                            x_axis = "python_timestamp", fd = None):
    """ Plot an equation involving IQ for a channel list
    Inputs:
       chanlist: list of KIDs, e.g. ['K000','K002']
                 Looks for fields 'K000_I', 'K000_Q', etc.
       datafile: dirfile or .txt sourcefile
       client_name: string for title of plot, unique handle
       eqn: list of equations or functions of (Ifield, Qfield)
            usually ["mag","phase","df","x"]
       sweepdict: dict output from process_sweep, needed for df or x
       x_axis: python timestamp for human-readability, 
               kst default is INDEX (frame count, 1 per packet)
       fd: frame dict
    """

    # If single strings for chanlist and eqnlist, turn into lists
    if type(chanlist) == str:
        chanlist = [chanlist]
    if type(eqnlist) == str:
        eqnlist = [eqnlist]
        
    if fd == None:
        fd = frametype()

    # If requested df or x and don't have sweepdict, load it
    if (("df" in eqnlist) or ("x" in eqnlist)):
        sweepdict = process_sweep(sweepfile)
        
    client = kst.Client(client_name)
    client.hide_window()
    X = client.new_data_vector(datafile,
                               field = x_axis,
                               start = fd['start'],
                               num_frames = fd['num_frames'],
                               skip = fd['skip'])
    for chan in chanlist:
        Ifield = chan + '_I'
        I = client.new_data_vector(datafile,
                                   field = Ifield,
                                   start = fd['start'],
                                   num_frames = fd['num_frames'],
                                   skip = fd['skip'])
        I.set_name(Ifield)
        Qfield = chan + '_Q'
        Q = client.new_data_vector(datafile,
                                   field = Qfield,
                                   start = fd['start'],
                                   num_frames = fd['num_frames'],
                                   skip = fd['skip'])
        Q.set_name(Qfield)

        for eqn in eqnlist:
            if (eqn == "df") or (eqn == "x"):
                eqnstring = equationstring_IQ(eqn, Ifield, Qfield, sweepdict[chan])
            else:
                eqnstring = equationstring_IQ(eqn, Ifield, Qfield)
            e1 = client.new_equation(X, eqnstring, name = chan + ' ' + eqn)
            c1 = client.new_curve(e1.x(), e1.y())
            p1 = client.new_plot()
            p1.add(c1)
            
            check_timestamp(x_axis, p1)

    client.show_window()
    return client

#################################################################3
# Old functions

"""
def add_plottoclient(client,
                     new_plot,
                     datafile = find_latestfile(),
                     x_axis = "INDEX",
                     plottype = "all",
                     minstoread = 2):

    # Find plot type params
    frame_start, frame_num, frame_skip = frametype(type = plottype,
                                                   m2r = minstoread)

    X = client.new_data_vector(datafile,
                               field = x_axis,
                               start = frame_start,
                               num_frames = frame_num,
                               skip = frame_skip)
    Y = client.new_data_vector(datafile,
                               field = new_plot,
                               start = frame_start,
                               num_frames = frame_num,
                               skip = frame_skip)
    c1 = client.new_curve(X,Y)
    p1 = client.new_plot()
    p1.add(c1)
    return client
    
def plot_mount(client_name="Mount Position"):
    mount = kst.Client(client_name)
    # mount datafile should be passed in here...
    datafile1 = './test_timestream1.txt'
    T1 = mount.new_data_vector(datafile1,
                               field = "Column 1",
                               start = -1,
                               num_frames=1000)
    V1a = mount.new_data_vector(datafile1,
                                field = "Column 2",
                                start = -1,
                                num_frames = 1000)
    V1b = mount.new_data_vector(datafile1,
                                field = "Column 3",
                                start = -1,
                                num_frames = 1000)
    datafile2 = './test_timestream2.txt'
    T2 = mount.new_data_vector(datafile2,
                               field = "Column 1",
                               start = -1,
                               num_frames = 1000)
    V2a = mount.new_data_vector(datafile2,
                                field = "Column 2",
                                start = -1,
                                num_frames = 1000)
    V2b = mount.new_data_vector(datafile2,
                                field = "Column 3",
                                start = -1,
                                num_frames = 1000)
    c1 = mount.new_curve(T1,V1a)
    c2 = mount.new_curve(T2,V2a)
    p1 = mount.new_plot()
    p2 = mount.new_plot()
    p1.add(c1)
    p1.set_x_axis_interpretation(interp='ctime')
    p2.add(c2)
    p2.set_x_axis_interpretation(interp='ctime')
    return mount

# Test netcdf file, downloaded from
# http://www.unidata.ucar.edu/software/netcdf/examples/...
# GOTEX.C130_N130AR.LRT.RF06.PNI.nc
def plot_netcdf(client_name = "Test netCDF",
                x_axis = "time_offset",
                y_axis = "INFLOW",
                frame_start = -1,
                frame_num = -1,
                frame_skip = 0):
    client = kst.Client(client_name)
    datafile = './GOTEX.C130_N130AR.LRT.RF06.PNI.nc'
    X = client.new_data_vector(datafile,
                               field = x_axis,
                               start = frame_start,
                               num_frames = frame_num,
                               skip = frame_skip)
    Y = client.new_data_vector(datafile,
                               field=y_axis,
                               start = frame_start,
                               num_frames = frame_num,
                               skip = frame_skip)
    c1 = client.new_curve(X,Y)
    p1 = client.new_plot()
    p1.add(c1)
    return client

def plot_fakeroach(client_name = "Test fakeroach",
                   datafile = "../testing/run/testdatawrite_dirfile/",
                   x_axis = "ctime",
                   y_axis = "KID0000",
                   frame_start = -1,
                   frame_num = -1,
                   frame_skip = 0):

    client = kst.Client(client_name)
    X = client.new_data_vector(datafile,
                               field = x_axis,
                               start = frame_start,
                               num_frames = frame_num,
                               skip = frame_skip)
    Y = client.new_data_vector(datafile,
                               field = y_axis,
                               start = frame_start,
                               num_frames = frame_num,
                               skip = frame_skip)
    c1 = client.new_curve(X,Y)
    p1 = client.new_plot()
    p1.add(c1)
    p1.set_x_axis_interpretation(interp = "ctime")
    p1.set_x_axis_display(display = "yyyy-MM-dd hh:mm:ss")
        
    return client

if __name__ == '__main__':
    client = plot_dirfile_chanIQ()

"""
#############
# Minimal example

"""
cd /home/superspec/Documents/ksk/multitone/pcp/kst
import ssMonitor
import pykst as kst
df = ssMonitor.find_latestfile('/data/dirfiles/roach0/','20??????_??????')

client = kst.Client('test'); client.hide_window()
V1 = client.new_data_vector(df, field = 'python_timestamp', name='V1')
V2 = client.new_data_vector(df, field = 'pps_timestamp', name='V2')
V3 = client.new_data_vector(df, field = 'fine_timestamp', name='V3')

e1 = client.new_equation(V1, "SIN([V2])+SIN([V3])", name='myequation')
c1 = client.new_curve(e1.x(), e1.y())
p1 = client.new_plot()
p1.add(c1)
client.show_window()


"""
