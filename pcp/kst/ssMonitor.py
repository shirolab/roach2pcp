# Quick-look live-monitoring software for SuperSpec
# This is a one-way street: data are saved to the control computer and
# this simply plots it - no commands are sent to the ROACH,
# housekeeping, or telescope computers!
#
# Requires pykst
#

import pykst as kst
import glob, os

#################################################################3
# Auxiliary functions

def find_latestfile(dataloc = "/data/dirfiles/roach0/",
                    datapattern = "20??????_??????"):
    list_of_files = glob.glob(dataloc + datapattern)
    latest_file = max(list_of_files, key = os.path.getctime)
    return latest_file

def kill(client):
    client.clear()
    client.quit()

def frametype(type = "lastnmins", f_s = 488.0, m2r = 2., ds = 1.):
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

def equationstring_df(chan, sweepdict, Ifield, Qfield):
    # ((I-I_f0)*dIdf + (Q-Q_f0)*dQdf)/(dIdf^2 + dQdf^2)
    f0 = sweepdict[chan]['f0']
    I_f0 = sweepdict[chan]['I_f0']
    Q_f0 = sweepdict[chan]['Q_f0']
    dIdf = sweepdict[chan]['dIdf'] # at f0
    dQdf = sweepdict[chan]['dQdf']

    eqn = '((([' + Ifield + ']-%3f)*%3f)'  % (I_f0,dIdf) + \
          '+(([' + Qfield + ']-%3f)*%3f))' % (Q_f0,dQdf) + \
          '/(%3f^2 + %3f^2)  '             % (dIdf,dQdf)

    # add division by freq?
    return eqn

def equationstring_IQ(eqn, Ifield, Qfield):
    if eqn == "mag":
        equationstring = 'SQRT([' + Ifield + ']^2 + [' + Qfield + ']^2)'
    if eqn == "phase":
        equationstring = 'ATAN([' + Ifield + ']/[' + Qfield + '])'
    return equationstring

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

def plot_dirfile_IQequation(chanlist, datafile, client_name = None,
                            eqnlist = ["mag"],
                            x_axis = "python_timestamp", fd = None):
    """ Plot an equation involving IQ for a channel list
    Inputs:
       chanlist: list of KIDs, e.g. ['K000','K002']
                 Looks for fields 'K000_I', 'K000_Q', etc.
       datafile: dirfile or .txt sourcefile
       client_name: string for title of plot, unique handle
       eqn: list of equations or functions of (Ifield, Qfield)
            usually ["mag","phase"]
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
            equationstring = equationstring_IQ(eqn, Ifield, Qfield)
            print equationstring
            e1 = client.new_equation(X, equationstring, name = chan + ' ' + eqn)
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
