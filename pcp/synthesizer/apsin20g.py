# command set for the APSIN20G microwave synthesizer
# PB - 2018

# programming reference - https://goo.gl/7d5ci4
# attempt to standardise the commands between the different synth models in this directory
# provides a class object to hold all of the information and methods to control the synth
# required functionality
    # - initalise connection, probe any relevant information
    # - get_freq, set_freq
    # - reference_set, reference_get, islocked
    # - power_set, power_get

#

import pyvisa
