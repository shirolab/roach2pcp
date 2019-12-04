# command set for a dummy attenuator that will be used for testing

VENDOR = 'dummy'
MODELNUMS = ['dummy']

import time as _time

class dummyAttenDevice(object):
    def __init__(self):
        self.vendor   = "dummy"
        self.modelnum = "dummy"
        self.src     = dummyAttenSource(self,0)

    def test_connection(self):
        """Simple method to test to see if the hardware connection is alive. Returns True or False"""

        # for dummy atten, assume it is always connected
        return True


class dummyAttenSource(object):
    """
    Dummy attenuator class for testing. Includes only basic attenuator functionality.
    """
    def __init__(self,device,source):

        self.device = device
        self.sourceNumber = source
        # initialise parameters
        self._attenuation = 10 # in dB

    @property
    def attenuation(self):
        """Get or set the attenuation of the attenuator. Units should all be in dB."""
        return self._attenuation
    @attenuation.setter
    def attenuation(self, frequency):
        self._attenuation = attenuation
        _time.sleep(1e-6) # emulate time to switch attenuation
