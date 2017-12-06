# Quick-look live-monitoring software for SuperSpec
# This is a one-way street: data are saved to the control computer and
# this simply plots it - no commands are sent to the ROACH,
# housekeeping, or telescope computers!
#
# Requires pykst
#

import pykst as kst

def plot_mount():
    mount = kst.Client("Mount Position")
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


if __name__ == '__main__':
    plot_mount()
