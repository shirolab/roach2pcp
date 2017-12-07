# Quick-look live-monitoring software for SuperSpec
# This is a one-way street: data are saved to the control computer and
# this simply plots it - no commands are sent to the ROACH,
# housekeeping, or telescope computers!
#
# Requires pykst
#

import pykst as kst
import netCDF4 as nc

def plot_mount(client_name="Mount Position"):
    mount = kst.Client(client_name)
    # mount datafile should be passed in here...
    datafile = './test_timestream.txt'
    T = mount.new_data_vector(datafile,
                              field="Column 1",
                              start=-1,num_frames=1000)
    V1 = mount.new_data_vector(datafile,
                               field="Column 2",
                               start=-1,num_frames=1000)
    V2 = mount.new_data_vector(datafile,
                               field="Column 3",
                               start=-1,num_frames=1000)
    c1 = mount.new_curve(T,V1)
    c2 = mount.new_curve(T,V2)
    p1 = mount.new_plot(font_size = 12)
    p2 = mount.new_plot(font_size = 12)
    p1.add(c1)
    p2.add(c2)
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

if __name__ == '__main__':
    plot_mount()
