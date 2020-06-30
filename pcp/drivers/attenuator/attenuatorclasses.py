#!/usr/bin/env python
"""
Set of class definitions that attempt to provide a normalised set of attenuator defintions to be used in
pcp. A high-level class defintion inherits from a base class provided by the manufacturer. This allows pcp users to
add new hardware by only writing a minimal amount of code.

Class naming convention is to prepend pcp_ to the factory defined class name. For a attenuator object to be available to this
package, a standard set of methods are required to ensure robust class polymorphism. The following methods should be
defined/renamed and point to the appropriate method of the base class;

    - test_connection():
        Method to test to see if the hardware connection is alive. Return True or False

    - frequency():
        Getter/setter to both get and set the attenuation.

Each class defintion should include a VENDOR string and MODELNUMS list that will determine which make and model the code will
work for. These strings will also be defined in the configuration files and will be used to match the correct synth object to the
correct roach. Checks are done to ensure that code exists for any hardware defined in the configuration files.

Upon initialisation of this submodule, a dictionary of objects with keys VENDOR_MODELNUM for each MODELNUM in MODELNUMS is provided. The
same object can be passed for multiple MODELNUMS. This dictionary is used by lib_hardware to generate the working set of hardware references
required as per the configuration file. Hopefully, the user should not have to worry about this code, unless adding new hardware.

Unit conventions:
    Attenuation == dB

Currently supported models (02/18/2019):
    - Dummy (for testing purposes)
    - Minicircuits RUDAT 6000-30

"""

# canonical module imports
import time as _time, pprint as _pprint

# ===========================================================================================
# ================== Dummy synthesiser object (for testing purposes) ========================
# ===========================================================================================
import dummy_atten as _dummy_atten # hide the base class from the user by prepending "_"

class pcp_dummyAttenDevice(_dummy_atten.dummyAttenDevice):

    VENDOR = _dummy_atten.VENDOR
    MODELNUMS = _dummy_atten.MODELNUMS

    def __init__(self):
        # instantiate class to get all of the factory provided methods
        super(pcp_dummyAttenDevice, self).__init__()
    # make sure all methods are defined in the same way, and return the same item
    def getSourceObj(self,channel):
        return pcp_dummyAttenSource(self,channel)


class pcp_dummyAttenSource(_dummy_atten.dummyAttenSource):

    def __init__(self,device,source):
        # instantiate class to get all of the factory provided methods
        super(pcp_dummyAttenSource, self).__init__(device,source)

    # make sure all methods are defined in the same way, and return the same item

    # only show example here, as the base class for dummySynth was written in this way
    @property
    def attenuation(self):
        """
        Get or set the attenuation. Units should all be in dB.
        """
        return self._attenuation

    @attenuation.setter
    def attenuation(self, attenuation):
        self._attenuation = attenuation
        _time.sleep(1e-6) # emulate time to switch attenuation
        print ("attenuation set to {a}".format(a=attenuation))

    # add a print status method for convenience
    def print_status(self):
        _pprint.pprint(vars(self), width=1)


# ===========================================================================================
# ================================== RUDAT 6000-XX ==========================================
# ===========================================================================================

import rudat6000usb as _rudat6000usb
RUDATS_CONNECTED = _rudat6000usb.get_attenuators()

class pcp_rudat6000Device(_rudat6000usb.rudat6000Device):
    # pass vendor and model nums as class attributes for checking
    VENDOR = _rudat6000usb.VENDOR
    MODELNUMS = _rudat6000usb.MODELNUMS

    def __init__(self,serial,attmax=60.0,attmin=0.0,attres=0.25):
        #Get usb device handle from initial usb scan
        #perform initial scan to find usb device handles for connected rudats
        dev = RUDATS_CONNECTED[int(serial)]

        # instantiate class to get all of the factory provided methods
        super(pcp_rudat6000Device, self).__init__(dev,attmax,attmin,attres)

    def getSourceObj(self,channel):
        return pcp_rudat6000Source(self,channel)

class pcp_rudat6000Source(_rudat6000usb.rudat6000Source):

    def __init__(self,device,source):
        # instantiate class to get all of the factory provided methods
        super(pcp_rudat6000Source, self).__init__(device,source)

    @property
    def attenuation(self):
        """Get or set the attenuation of the attenuator. Units should all be in dB."""
        self._attenuation = self.get_atten()
        return self._attenuation
    @attenuation.setter
    def attenuation(self, attenuation):
        self.set_atten(attenuation)
        self._attenuation = attenuation

    # add a print status method for convenience
    def print_status(self):
        _pprint.pprint(vars(self), width=1)
