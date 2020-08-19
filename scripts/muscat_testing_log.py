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
IOError: [Errno 2] No such file or directory: '/data1/muscat/phantom/sf.txt'
#added lines to create file if not present
exit()

#############################################################################

#19/08/2020

import pcp
pcp.scripts.init_pcp()
name = ['phantom','clones','sith','hope','empire','jedi']
mc = pcp.mux_channel.muxChannelList(name) 
AssertionError: Given filename /home/muscat/multitone2020-08-13/roach2pcp/data/tonelists/MUSCAT_A.txt doesnt appear to exist.

#add toneslist files in correct directory
