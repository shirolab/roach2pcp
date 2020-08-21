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

import pcp
pcp.scripts.init_pcp() #ok
name = ['phantom','clones','sith','hope','empire','jedi']
mclist = pcp.mux_channel.muxChannelList(name)
#Ok
mc=mclist.phantom
mc.ri.initialise_fpga(force_reupload=True)
#Shitloads of firmware warnings about Meta fields are seperated by spaces, should be tabs
#Error due to unexpected timeout parameter in upload_to_fpga_and_program
#Error in upload_firmware_file due to upload_to_ram_and_program now returning True, not None
#Error in fpga.write_int, udp_dest_mac value requires unsigned but casper is now returning signed values, fixed with cast to _np.int32 in write_to_fpga_register
#Tested: OK
#COMMIT: casperfpga==0.1.1 broke lib_fpga: more fixes in lib_fpga

mc.write_freqs_to_fpga()
Write new tones to qdr? [y/n]y
File "pcp/lib/lib_fpga.py", line 424, in gen_waveform_from_freqs
    spec[fft_bin_index] = amps * _np.exp( 1j * phases )
ValueError: operands could not be broadcast together with shapes (215,) (197,)

mc.toneslist.amps = mc.toneslist.amps[:197]
mc.write_freqs_to_fpga()
2020-08-20 15:24:27,204 - pcp.mux_channel - INFO - It looks like this set of tones has already been uploaded. Nothing done.

#This is a bug, the tones were not uploaded, possibly the progress bar thread not forwarding on exceptions, which allowed the write_freqs_to_qdr to continue even though it failed 
#Fixed in lib_fpga.progress_bar
#Commit: lib_fpga.progress_bar handle exceptions correctly in tqdm progress bar
#Commit: lib_fpga.progress_bar handle keyboard interrupt correctly

#Also, random USB disconnect again. Restarting.





