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
    - Valon 5008, 5009
    - APSIN 20G
    - Rhode and Schwartz, SGS100a, SMA100a
    - Windfreak Tech. SynthHD

TODO:
    - add "fast" frequency functionality to increase speed when sweeping
"""

# canonical module imports
import time as _time, pprint as _pprint

# ===========================================================================================
# === Dummy synthesiser object (for testing purposes) =======================================
# ===========================================================================================
import dummy_synth as _dummy_synth # hide the base class from the user by prepending "_"

class pcp_dummySynthDevice(_dummy_synth.dummySynthDevice):

    VENDOR = _dummy_synth.VENDOR
    MODELNUMS = _dummy_synth.MODELNUMS

    def __init__(self):
        # instantiate class to get all of the factory provided methods
        super(pcp_dummySynthDevice, self).__init__()
    # make sure all methods are defined in the same way, and return the same item
    def getSourceObj(self,channel):
        return pcp_dummySynthSource(self,channel)

class pcp_dummySynthSource(_dummy_synth.dummySynthSource):

    def __init__(self,device,source):
        # instantiate class to get all of the factory provided methods
        super(pcp_dummySynthSource, self).__init__(device,source)

    # make sure all methods are defined in the same way, and return the same item

    # only show example here, as the base class for dummySynth was written in this way
    @property
    def frequency(self):
        """Get or set the frequency of the synthesizer. Units should all be in Hz."""
        return self._frequency

    @frequency.setter
    def frequency(self, frequency):
        self._frequency = frequency
        print ("frequency set to {f}".format(f=frequency))

    # Power getter
    @property
    def power(self):
        return self._power

    # Power getter
    @power.setter
    def power(self, power):
        self._power = power
        _time.sleep(0.001)
        print ("power set to {p}".format(p=power))

    # add a print status method for convenience
    def print_status(self):
        _pprint.pprint(vars(self), width=1)

# ===========================================================================================
# === r+s (sgs100a) ===========================================================================
# ===========================================================================================

import rs_sgs100a as _rs_sgs100a # hide the base class from the user by prepending "_"

class pcp_rssgsDevice(_rs_sgs100a.sgsSynthDevice):
    # pass vendor and model nums as class attributes for checking
    VENDOR = _rs_sgs100a.VENDOR
    MODELNUMS = _rs_sgs100a.MODELNUMS

    def __init__(self):
        # instantiate class to get all of the factory provided methods
        super(pcp_rssgsDevice, self).__init__()
    def getSourceObj(self,channel):
        return pcp_rssgsSource(self,channel)

class pcp_rssgsSource(_rs_sgs100a.sgsSynthSource):

    def __init__(self,device,source):
        # instantiate class to get all of the factory provided methods

        # as the methods are defined correctly in the drivers (as we wrote them!), nothing else is needed
        super(pcp_rssgsSource, self).__init__(device,source)

    # add a print status method for convenience
    def print_status(self):
        _pprint.pprint(vars(self), width=1)

# ===========================================================================================
# === APSIN (20G) ===========================================================================
# ===========================================================================================

import apsin as _apsin # hide the base class from the user by prepending "_"

class pcp_apsinDevice(_apsin.apsinSynthDevice):
    # pass vendor and model nums as class attributes for checking
    VENDOR = _apsin.VENDOR
    MODELNUMS = _apsin.MODELNUMS

    def __init__(self):
        # instantiate class to get all of the factory provided methods
        super(pcp_apsinDevice, self).__init__()
    def getSourceObj(self,channel):
        return pcp_apsinSource(self,channel)

class pcp_apsinSource(_apsin.apsinSynthSource):

    def __init__(self,device,source):
        # instantiate class to get all of the factory provided methods

        # as the methods are defined correctly in the drivers (as we wrote them!), nothing else is needed
        super(pcp_apsinSource, self).__init__(device,source)


    # add a print status method for convenience
    def print_status(self):
        _pprint.pprint(vars(self), width=1)

    # # only show example here, as the base class for dummySynth was written in this way
    # @property
    # def frequency(self):
    #     """Get or set the frequency of the synthesizer. Units should all be in Hz."""
    #     self._frequency = self.frequency
    #     return self._frequency
    #
    # @frequency.setter
    # def frequency(self, frequency):
    #     self.frequency = frequency
    #     self._frequency = frequency
    #     print ("frequency set to {f}".format(f=frequency))
    #
    # # Power getter
    # @property
    # def power(self):
    #     self._power = self.output_power
    #     return self._power
    #
    # # Power getter
    # @power.setter
    # def power(self, power):
    #     self.output_power = power
    #     self._power = power
    #     print ("power set to {p}".format(p=power))

# ===========================================================================================
# === WINDFREAK =============================================================================
# ===========================================================================================

import windfreaksynth_v2 as _windfreaksynth # hide the base class from the user by prepending "_"

class pcp_windfreaksynthDevice(_windfreaksynth.SynthHDDevice):
    # pass vendor and model nums as class attributes for checking when creating SYNTH_HW_DICT
    VENDOR = _windfreaksynth.VENDOR
    MODELNUMS = _windfreaksynth.MODELNUMS

    def __init__(self,serial):
        # instantiate class to get all of the factory provided methods
        super(pcp_windfreaksynthDevice, self).__init__(serial)

    def getSourceObj(self,channel):
        return pcp_windfreaksynthSource(self,channel)


class pcp_windfreaksynthSource(_windfreaksynth.SynthHDSource):

    def __init__(self,device,source):
        # instantiate class to get all of the factory provided methods
        super(pcp_windfreaksynthSource, self).__init__(device,source)

        #set all settings as required for muscat

        #keep track of which source is being controlled
        #really needs to link to config file.
        #self.clk_or_lo='clk'

    # make sure all methods are defined in the same way, and return the same item

    # only show example here, as the base class for dummySynth was written in this way
    # frequency getter
    @property
    def frequency(self): # getter
        #clk_or_lo='lo'
        """Get or set the frequency of the synthesizer. Units should all be in Hz."""
        self._frequency = self.getFrequency()
        return self._frequency

    # frequency setter
    @frequency.setter
    def frequency(self, frequency):
        self.setFrequencyFast(frequency)
        self._frequency=frequency
        #print ("frequency set to {f}".format(f=frequency))

    # power getter
    @property
    def power(self):
        self._power = self.getPower()
        return self._power

    # power setter
    @power.setter
    def power(self, power):
        self.setPower(power)
        self._power = power
        print ("power set to {p}".format(p=power))

    # add a print status method for convenience
    def print_status(self):
        _pprint.pprint(vars(self), width=1)

# ===========================================================================================
# === Valon 5009 ============================================================================
# ===========================================================================================

# Valon 5009

import valon5009 as _synth_valon5009 # hide the base class from the user by prepending "_"

class pcp_valon5009synthDevice(_synth_valon5009.ValonDevice):
    # pass vendor and model nums as class attributes for checking when creating SYNTH_HW_DICT
    VENDOR = _synth_valon5009.VENDOR
    MODELNUMS = _synth_valon5009.MODELNUMS

    def __init__(self, serial):
        # instantiate class to get all of the factory provided methods
        super(pcp_valon5009synthDevice, self).__init__(serial)

    def getSourceObj(self,channel):
        return pcp_valon5009synthSource(self,channel)

class pcp_valon5009synthSource(_synth_valon5009.ValonSource):

    def __init__(self,device,source):
        # instantiate class to get all of the factory provided methods
        super(pcp_valon5009synthSource, self).__init__(device,source)
        self.source = source

    # frequency getter
    @property
    def frequency(self): # getter
        """Get or set the frequency of the synthesizer. Units should all be in Hz."""
        self._frequency = self.Frequency
        return self._frequency

    # frequency setter
    @frequency.setter
    def frequency(self, frequency):
        self.Frequency = frequency
        self._frequency = frequency
        print ("frequency set to {f}".format(f=frequency))

    # power getter
    @property
    def power(self):
        self._power = self.powerLevel
        return self._power

    # power setter
    @power.setter
    def power(self, power):
        self.powerLevel = power
        self._power = power
        print ("power set to {p}".format(p=power))

    # add a print status method for convenience
    def print_status(self):
        _pprint.pprint(vars(self), width=1)


# ===========================================================================================
# === Synthesizer ADF4355====================================================================
# ===========================================================================================

# Alternative version for MUSCAT channels

import synth_ADF4355 as _synth_ADF4355 # hide the base class from the user by prepending "_"

class pcp_adf4355synthDevice(_synth_ADF4355.ADF4355synthDevice):
    # pass vendor and model nums as class attributes for checking when creating SYNTH_HW_DICT
    VENDOR = _synth_ADF4355.VENDOR
    MODELNUMS = _synth_ADF4355.MODELNUMS

    def __init__(self):
        # instantiate class to get all of the factory provided methods
        super(pcp_adf4355synthDevice, self).__init__()

    def getSourceObj(self,channel):
        return pcp_adf4355synthSource(self,channel)

class pcp_adf4355synthSource(_synth_ADF4355.ADF4355synthSource):

    def __init__(self,device,source):
        # instantiate class to get all of the factory provided methods
        super(pcp_adf4355synthSource, self).__init__(device,source)

    @property
    def frequency(self): # getter
        """Get or set the frequency of the synthesizer. Units should all be in Hz."""
        self._frequency = self.getFrequency()
        return self._frequency

    @frequency.setter
    def frequency(self, frequency):
        self.setFrequency(frequency)
        self._frequency=frequency

    # add a print status method for convenience
    def print_status(self):
        _pprint.pprint(vars(self), width=1)
