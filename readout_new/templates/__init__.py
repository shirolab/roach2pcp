#!/usr/bin/env python

# any code to initialse the module (c)should be placed here

# import logfile control for scripts
from . import daemontemplate

# if True:
#     print """
#     \033[95m Welcome to Superspec deployment code
#
#     Basic commands:
#
#     Logging: access to logging scripts are imported when initalised, and are accessible via the logctrl object
#
#     """






# 1. configure logging (should be running continuously in the background)
# 2. set up roach interfaces. One ri for each roach, similar to, but a simplified version
#    of the kidPy object. Each individual ri object will be a container for the live status of each
#    and configuaion parameters of each roach.
#    There will then be a container that holds Nroach objects as a list. There will be then a set of
#    functions that will act on either single ri, or ri list
#    Each ri will have the following data
#       - fpga (as before, class defined in capserfpga)
#       - synth - generic object that will control the various synths
#            - in an attempt to handle Nroaches != Nsynths, each roach defined in network_config
#            will have a synthid entry, that matches one of the synth entries in hardware_config.
#            Upon initialisation, each synth is initialised into a synth object, which is then
#            passed to the corresponding roach interface. This way, multiple roaches can reference
#            the same synth. When multiple roaches use the same synth, care needs to be taken when
#            manipulating synths in parallel, but this should be an easy check of the ri.synth.synthid
#       - daemon tracker - associated information regarding the daemon packet receiving daemonself.
#           - this should have a live status update of whether saving is on/off...etc
