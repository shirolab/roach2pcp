# Author = Sam Gordon
# This script uploads a .bof file to the ROACHI
# First argument is the absolute path to the bitstream
# Edit IP address accordingly

import casperfpga
import sys
bitstream = sys.argv[1] # absolute path to bitstream
fpga = casperfpga.katcp_fpga.KatcpFpga('192.168.40.64')
fpga.upload_bof(bitstream,7147, 200)
