"""
This is not a script intended to be run.
I have left it as a .py file for syntax highlighting reasons
"""

exit()

#############################################################################
#18/08/2020

import pcp
pcp.scripts.init_pcp()
name = ['phantom','clones','sith','hope','empire','jedi']
mc = pcp.mux_channel.muxChannelList(name) 
> IOError: [Errno 2] No such file or directory: '/data1/muscat/phantom/sf.txt'

#COMMIT: added lines to create file if not present
exit()

#############################################################################
#19/08/2020

import pcp
pcp.scripts.init_pcp()
name = ['phantom','clones','sith','hope','empire','jedi']
mc = pcp.mux_channel.muxChannelList(name) 
> AssertionError: Given filename /home/muscat/multitone2020-08-13/roach2pcp/data/tonelists/MUSCAT_A.txt doesnt appear to exist.

#COMMIT: add toneslist files in correct directory and delete top level toneslist directory

mc = pcp.mux_channel.muxChannelList(name) 
#completed without exception HOWEVER log output shows Errors connecting to all fpgas
#trying again from scratch
exit()

import pcp
pcp.scripts.init_pcp()
> SerialException: Attempting to use a port that is not open
#4 out of 6 windfreaks now disconnected. usb hardware error? reconnect and try again
exit()


import pcp
pcp.scripts.init_pcp() #ok
name = ['phantom','clones','sith','hope','empire','jedi']
mc = pcp.mux_channel.muxChannelList(name) 
#Again, no exception but failed top connect. Inspecting output:
File "pcp/lib/lib_fpga.py", line 96, in get_fpga_instance
    return _casperfpga.katcp_fpga.KatcpFpga( ipaddress, timeout = 10. )
AttributeError: 'module' object has no attribute 'katcp_fpga'
#this requires casperfpga==0.0.1 but just upgraded to 0.1.1 as per the requirements.txt and unable to downgrade as 0.0.1 is missing from pypi. 


#############################################################################
#20/08/2020

#Updated lib_fpga and mux_channel to work with casperfpga==0.1.1:
#_casperfpga.katcp_fpga.KatcpFpga -> _casperfpga.CasperFpga
#fpga._read_design_info_from_host -> fpga.transport._read_design_info_from_host
#fpga._sock is not available in 0.1.1 so commented out any uses, i.e. fast_blindwrite.
#fpga._disconnect -> fpga.disconnect, also remove 10s timeout prior to disconnect
#Tested: OK
#COMMIT: updates to lib_fpga and mux_channel required after upgrade to casperfpga==0.1.1







