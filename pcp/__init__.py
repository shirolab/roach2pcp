#!/usr/bin/env python

# any code to initialse the module (c)should be placed here

# import logfile control for scripts

import os, sys, pkgutil, time

# Define top level root directory, and alert loudly if it don't already exist

print ( \
"""
Welcome to the Python Control Program for readout of kinetic inductance detectors
using Roach2 control boards.

Loading submodules...

"""
)

#import sub-libraries
import configuration, lib, kid, synthesizer, unittests
import logfile, roach_interface, datalog_mp, toneslist


# lists of important information defined at the top level for convenience (i.e. pcp.ROACH_LIST)
# will show the list of roaches defined in the confiruation files

ROACH_LIST = configuration.roach_config['roach_params'].keys()
SYNTH_LIST = configuration.hardware_config['synth_config'].keys()
ATTEN_LIST = configuration.hardware_config['atten_config'].keys()








# MOVE OUT OF INIT - maybe create file called funcs_convenience
def reload_all_packages():
    """Helper function to reload all submodules interactively. Useful for debugging, and
    reloading configuration files. Currently, only reloads top level packages.
     """

    current_module = sys.modules[__name__]

    print "Reloading submodules..."
    for importer, modname, ispkg in pkgutil.iter_modules(current_module.__path__):
        if ispkg:
            time.sleep(0.1)
            print "Reloaded", current_module.__name__, modname
            reload( sys.modules[getattr(current_module, modname).__name__] )
    print "Done."
    reload(sys.modules[__name__])


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
