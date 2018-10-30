#!/usr/bin/env python
"""
Set of class definitions that attempt to provide a normalised set of synthesiser defintions to be used in
pcp. A high-level class defintion inherits from a base class provided by the manufacturer. This allows pcp users to
add new hardware by only writing a minimal amount of code.

Class naming convention is to prepend pcp_ to the factory defined class name. For a synthesiszer object to be available to this
package, a standard set of methods are required to ensure robust class polymorphism. The following methods should be
defined/renamed and point to the appropriate method of the base class;

    - test_connection():
        Method to test to see if the hardware connection is alive. Return True or False

    - frequency():
        Getter/setter to both get and set the frequency of the synthesizer. See the dummy_synth code for example code.

    - output_power():
        Getter/setter to both get and set the RF power level of the synthesizer. See the dummy_synth code for example code

    - reference():
        Getter/setter to both get and set the reference of the synthesizer. Used to set whether the synth uses its internal osicallator
        as a reference, or whether an external refrence should be used. See the dummy_synth code for a example code

Each class defintion should include a VENDOR string and MODELNUMS list that will determine which make and model the code will
work for. These strings will also be defined in the configuration files and will be used to match the correct synth object to the
correct roach. Checks are done to ensure that code exists for any hardware defined in the configuration files.

Upon initialisation of this submodule, a dictionary of objects with keys VENDOR_MODELNUM for each MODELNUM in MODELNUMS is provided. The
same object can be passed for multiple MODELNUMS. This dictionary is used by lib_hardware to generate the working set of hardware references
required as per the configuration file. Hopefully, the user should not have to worry about this code, unless adding new hardware.

Unit conventions:
    Frequency == Hz
    Power     == dBm

Currently supported models (as of 2nd Sep 2018):
    - Dummy (for testing purposes)
    -x Valon 5008, 5009
    -x APSIN 20G
    -x Rhode and Schwartz, SGS100a, SMA100a
    -x Windfreak Tech. SynthHD

    "x denotes that the required code hasn't been implemented and tested in this script yet"

TODO:
    - add "fast" frequency functionality to increase speed when sweeping
"""

# canonical module imports
import time as _time, pprint as _pprint

# ===========================================================================================
# === Dummy synthesiser object (for testing purposes) =======================================
# ===========================================================================================
import dummy_synth as _dummy_synth # hide the base class from the user by prepending "_"

class pcp_dummySynth(_dummy_synth.dummySynth):

    VENDOR = _dummy_synth.VENDOR
    MODELNUMS = _dummy_synth.MODELNUMS

    def __init__(self):
        # instantiate class to get all of the factory provided methods
        super(pcp_dummySynth, self).__init__()

    # make sure all methods are defined in the same way, and return the same item

    # only show example here, as the base class for dummySynth was written in this way
    @property
    def frequency(self):
        """Get or set the frequency of the synthesizer. Units should all be in Hz."""
        return self._frequency

    @frequency.setter
    def frequency(self, frequency):
        self._frequency = frequency
        _time.sleep(0.001) # emulate time to switch frequency
        print "frequency set to {f}".format(f=frequency)

    # add a print status method for convenience
    def print_status(self):
        _pprint.pprint(vars(self), width=1)


# ===========================================================================================
# === APSIN (20G) ===========================================================================
# ===========================================================================================

import apsin as _apsin # hide the base class from the user by prepending "_"

class pcp_apsin(_apsin.apsinSynth):

    # pass vendor and model nums as class attributes for checking
    VENDOR = _apsin.VENDOR
    MODELNUMS = _apsin.MODELNUMS

    def __init__(self):
        # instantiate class to get all of the factory provided methods
        super(pcp_apsin, self).__init__()

    # make sure all methods are defined in the same way, and return the same item

    # only show example here, as the base class for dummySynth was written in this way
    @property
    def frequency(self):
        """Get or set the frequency of the synthesizer. Units should all be in Hz."""
        return self._frequency
    @frequency.setter
    def frequency(self, frequency):
        self._frequency = frequency
        _time.sleep(0.001) # emulate time to switch frequency

    # add a print status method for convenience
    def print_status(self):
        _pprint.pprint(vars(self), width=1)
