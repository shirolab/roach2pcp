#!/usr/bin/env python

# holds the code for the Roach interface class.

# Each ri will have the following data
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

class roachInterface(object):
    def __init__(self, roachid):

        self.roachid  = roachid

        self.fpga     = None
        self.tonelist = None
        self.daemon   = None
        self.synth    = None





# This script is the first code to be run after all hardware in connected and switched on


# We could write a small helper script to check things are connected would be useful for initial configuration testing
#    - check dnsmasq is running
#   - check roach(s) are connected
#


# the goal of this is to read information from a set of configuration files that contain all the
# neccessary information regarding Roaches/synths/ip addresses/ports...etc.

# Read from YAML/JSON for configuration file handling http://camel.readthedocs.io/en/latest/yamlref.html

# - instantiate a roach interface class (similar to SG original code) for each available Roach board.
# Each roach interface class should have the following information:
#   - upon init: roach fpga ip, roach ppc ip, local port ip, fpga instance, individual roach parameters( dds_shift, sample rate, accum_len)
# synthesiser handle (which should be a sub-class), attenuators (again, subclass)
#   - configuration of logging files. Have log file for each Roach independently, or all in one? (doesn't really matter,
# we can pass the log file handle to each roach instance)
#  - spawn a datalog.py instance for each Roach
# - This should then return a list of the roach interface objects, with everything initalised and running, to be used
# for subsequent tasks (e.g. biasing, streaming...etc)


# logging
