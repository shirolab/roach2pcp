# Quick-look live-monitoring software for SuperSpec
# This is a one-way street: data are saved to the control computer and
# this simply plots it - no commands are sent to the ROACH,
# housekeeping, or telescope computers!
#
# Requires pykst
#

import pykst as kst
import glob, os
#import netCDF4 as nc

def find_latestfile(dataloc = "/data/dirfiles/",
                    datapattern = "20??????_??????.dir"):
    list_of_files = glob.glob(dataloc + datapattern)
    latest_file = max(list_of_files, key = os.path.getctime)
    return latest_file

def plot_dirfile_chanIQ(client_name = find_latestfile(),
                        datafile = find_latestfile(),
                        x_axis = "INDEX",
                        chanrange = [0],
                        frame_start = -1,
                        frame_num = -1,
                        frame_skip = 0):
    client = kst.Client(client_name)
    X = client.new_data_vector(datafile,
                               field = x_axis,
                               start = frame_start,
                               num_frames = frame_num,
                               skip = frame_skip)
    # Go through each channel and overplot I/Q
    for ii in range(len(chanrange)):
        y_axis = 'I_' + str(chanrange[ii])
        Y = client.new_data_vector(datafile,
                                   field = y_axis,
                                   start = frame_start,
                                   num_frames = frame_num,
                                   skip = frame_skip)
        c1 = client.new_curve(X,Y)
        y_axis = 'Q_' + str(chanrange[ii])
        Y = client.new_data_vector(datafile,
                                   field = y_axis,
                                   start = frame_start,
                                   num_frames = frame_num,
                                   skip = frame_skip)
        c2 = client.new_curve(X,Y)
        p1 = client.new_plot()
        L1 = client.new_legend(p1)
        p1.add(c1)
        p1.add(c2)
    #p1.set_x_axis_interpretation(interp = 'ctime')
    return client

def add_plottoclient(client,
                     new_plot,
                     datafile = find_latestfile(),
                     x_axis = "INDEX",
                     frame_start = -1,
                     frame_num = -1,
                     frame_skip = 0):
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


