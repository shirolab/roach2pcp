import numpy as np

import time,sys
import netCDF4 as nc

# packets coming from the Roach will contain a bunch of info (possibly will be changed
# in future firmaware updates). but will contain at least packet_count, time, I and Q data for 1024 channels

# to test whether netcdf4 file is viable, write fake data to a file continuously at ~ 500 Hz,
# and see if it handles it. Additionally, try to open the file while wiriting. Lastly, try to open in KST

# genrate fake data with noisy sine waves with random phases

def gen_fake_roach_packet():
    # want time, packet count, data
    return time.time(), np.random.randint(1000, size=1024)


# now to read while writing?
# testing appending in real time
# filename = 'simple.nc'
#
# rootgrp = nc.Dataset(filename, "w", format="NETCDF4")
# rootgrp.createDimension("time", None)
# times = rootgrp.createVariable("times", "f8", dimensions = ("time",))
# rootgrp.description = "example script"
# rootgrp.history = "Created " + time.ctime(time.time())
#
# rootgrp.close()


#https://docs.scipy.org/doc/scipy-0.15.1/reference/generated/scipy.io.netcdf.netcdf_file.html
from scipy.io import netcdf
import signal
# f = netcdf.netcdf_file('simple.nc', 'w', version=2)
#
# f.history = 'Created for a test'
# f.createDimension('time', None)
# tnow = f.createVariable('time', 'f', ('time',))
# tnow.units = 'days since 2008-01-01'
# tnow[:] = np.arange(10)
# f.close()



if __name__ == '__main__':

    try:
        with nc.Dataset('simple.nc', 'a') as f:
        #with open('simple.txt', 'a') as f:
            print f.isopen()
            cnt = 0
            chunksize = 25
            tnow = f.variables['times']

            while True:

                time.sleep(0.1)

                print cnt, gen_fake_roach_packet()

                tnow[cnt] = gen_fake_roach_packet()[0]

                if np.mod(cnt, chunksize)==0:
                    print "syncing"
                    f.sync()

                #f.write("%.3f\n"%gen_fake_roach_packet()[0]); f.flush()
                cnt=cnt+1

    except KeyboardInterrupt:

        print 'closing'
        sys.exit(0)
