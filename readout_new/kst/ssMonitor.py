# Quick-look live-monitoring software for SuperSpec
# This is a one-way street: data are saved to the control computer and
# this simply plots it - no commands are sent to the ROACH,
# housekeeping, or telescope computers!
#
# Requires pykst
#
# Plots IQ timestreams and FFTs

import pykst as kst
import glob, os
#import netCDF4 as nc

def find_latestfile(dataloc = "/data/dirfiles/",
                    datapattern = "20??????_??????.dir"):
    list_of_files = glob.glob(dataloc + datapattern)
    latest_file = max(list_of_files, key = os.path.getctime)
    return latest_file

# Data vectors require parameters to control how many data frames are
# read and plotted...
# start: starting index of vector, -1 for count from end
# num_frames: number of frames to read, -1 for read to end
# skip: number of frames to skip, 0 to read everything
def frametype(type = "all",
              fpm = 60.*488., # frames per min
              m2r = 2., # mins to read
              skip = 0):
    if type == "all":
        frame_start = -1
        frame_num = -1
        frame_skip = skip
    if type == "lastnmins":
        frame_start = -1
        frame_num = fpm * m2r
        frame_skip = skip

    return int(frame_start), int(frame_num), int(frame_skip)

def plot_dirfile_chanIQ(client_name = find_latestfile(),
                        datafile = find_latestfile(),
                        x_axis = "INDEX",
                        chanrange = [0],
                        dofft = 0,
                        plottype = "all",
                        minstoread = 2):

    # Find plot type params
    frame_start, frame_num, frame_skip = frametype(type = plottype,
                                                   m2r = minstoread)

    client = kst.Client(client_name)
    client.hide_window()
    X = client.new_data_vector(datafile,
                               field = x_axis,
                               start = frame_start,
                               num_frames = frame_num,
                               skip = frame_skip)
    # Go through each channel and overplot I/Q
    for ii in range(len(chanrange)):
        y_axis = 'I_' + str(chanrange[ii])
        Y_I = client.new_data_vector(datafile,
                                     field = y_axis,
                                     start = frame_start,
                                     num_frames = frame_num,
                                     skip = frame_skip)
        c1 = client.new_curve(X,Y_I)
        y_axis = 'Q_' + str(chanrange[ii])
        Y_Q = client.new_data_vector(datafile,
                                     field = y_axis,
                                     start = frame_start,
                                     num_frames = frame_num,
                                     skip = frame_skip)
        c2 = client.new_curve(X,Y_Q)
            
        p1 = client.new_plot()
        L1 = client.new_legend(p1)
        p1.add(c1)
        p1.add(c2)

        if dofft == 1:
            S_I = client.new_spectrum(Y_I,
                                      sample_rate = 488,
                                      interleaved_average = True,
                                      fft_length = 9,
                                      output_type = 3)
            S_Q = client.new_spectrum(Y_Q,
                                      sample_rate = 488,
                                      interleaved_average = True,
                                      fft_length = 9,
                                      output_type = 3)
            c3 = client.new_curve(S_I.x(), S_I.y())
            c4 = client.new_curve(S_Q.x(), S_Q.y())
            p2 = client.new_plot()
            L2 = client.new_legend(p2)
            p2.add(c3)
            p2.add(c4)
            
    #p1.set_x_axis_interpretation(interp = 'ctime')
    client.show_window()
    return client

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


