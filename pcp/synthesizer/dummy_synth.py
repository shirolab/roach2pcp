# command set for a dummy synthesizer that will be used for testing
# PB - 2018

VENDOR = 'dummy'
MODELNUMS = ['dummy']

import time as _time

class dummySynth(object):
    """
    Dummy synthesizer class for testing. Includes only basic synthesizer functionality, which will be the minimum
    required a synth object in this package. Other functionality can be used interactively and in custom scripts, but the
    code will not rely on additional functionality to operate.

    """
    def __init__(self):
        # initialise parameters
        self.frequency = 1e6 # in Hz
        self.power    = 0 # in dBm
        self.reference = "int" # ext, int
        self.islocked  = False
        self.vendor   = "dummy"
        self.modelnum = "dummy"

    def test_connection(self):
        """Simple method to test to see if the hardware connection is alive. Returns True or False"""

        # for dummy synth, assume it is always connected
        return True

    @property
    def frequency(self):
        """Get or set the frequency of the synthesizer. Units should all be in Hz."""
        return self._frequency
    @frequency.setter
    def frequency(self, frequency):
        self._frequency = frequency
        _time.sleep(0.001) # emulate time to switch frequency

    @property
    def output_power(self):
        """Get or set the output power of the synthesizer. Units should be all in dBm."""
        return self._power
    @output_power.setter
    def power(self, output_power):
        self._power = output_power

    @property
    def reference(self):
        """Get or set the reference of the synthesizer. Should be either 'int' for internal
        reference, or 'ext' for an external reference.

        # TODO: allow external reference to pass numeric arguement to pass different frequency references
        """
        return self._reference
    @reference.setter
    def reference(self, which="int"):
        assert which in ["int", "ext"], "reference not recognised"
        self._reference = which
        self.islocked = True if which == 'ext' else False # emulated the reference locked state
