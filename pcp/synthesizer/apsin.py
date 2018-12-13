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
import pyvisa, time as _time, serial as _serial

# requires py-visa-py
try:
    _resouce_manager = pyvisa.ResourceManager("@py")
except:
    print "pyvisa and pyvisa-py are not operating correcly. Check that these packages are installed and try again."
# metadata that will be used to determine when this class should be used

# make of synthesizer (same key as used in the config file)
VENDOR = 'anapico'
# model numbers for which the following code will work
MODELNUMS = ["apsin20g", "3000"]


class apsinSynthDevice(object):
    def __init__(self):

        self.resource_string = "TCPIP{boardnum}::{ipaddress}::INSTR".format(boardnum = 0, ipaddress = "192.168.40.93")

        try:
            self.instrument = self._connect(self.resource_string)
        except Exception as exc:
            # 9 appears to be instrument in use
            # no link appears to be wrong ipaddress
            print "Error!", exc
            return
        
        self.vendor   = "dummy"
        self.modelnum = "0"
        
        self.src = apsinSynthSource(self,0)

    
    def _connect(self, resource_string):
        return _resouce_manager.open_resource(resource_string)

    def test_connection(self):
        """Simple method to test to see if the hardware connection is alive. Returns True or False"""
        # checks that the VISA resource name read from the instrument matches the software value
        return self.instrument.resource_name == self.resource_string

    def close(self):
        self.instrument.close()


class apsinSynthSource(object):
    """
    Dummy synthesizer class for testing. Includes only basic synthesizer functionality, which will be the minimum
    required a synth object in this package. Other functionality can be used interactively and in custom scripts, but the
    code will not rely on additional functionality to operate.

    """
    def __init__(self,device,source):
        self.device = device
        self.sourceNumber = source
        
        # initialise parameters
        self.frequency = 1e6 # in Hz
        self.output_power = 0 # in dBm
        self.reference = "int" # ext, int
        self.islocked  = False
        
    
    @property
    def rf_output(self):
        """Get or set the frequency of the synthesizer. Units should all be in Hz."""
        print "queried instrument"
        return bool(int(self.device.instrument.query( "output?" ).rstrip()))

    @rf_output.setter
    def rf_output(self, output_bool):
        self._output = output_bool
        self.device.instrument.write( 'output {output:d}'.format(output = output_bool) ) # emulate time to switch frequency

    @property
    def frequency(self):
        """Get or set the frequency of the synthesizer. Units should all be in Hz."""
        print "queried instrument"
        return float(self.device.instrument.query( 'freq?' ))

    @frequency.setter
    def frequency(self, frequency):
        self._frequency = frequency
        self.device.instrument.write( 'freq {freq:.2f}'.format(freq = frequency) ) # emulate time to switch frequency

    @property
    def output_power(self):
        """Get or set the output power of the synthesizer. Units should be all in dBm."""
        print "queried instrument"
        return float( self.device.instrument.query("pow:level?") )

    @output_power.setter
    def output_power(self, output_power):
        self._output_power = output_power
        self.device.instrument.write("pow:level {power:.1f} dbm".format(power = output_power))

    @property
    def reference(self):
        """Get or set the reference of the synthesizer. Should be either 'int' for internal
        reference, or 'ext' for an external reference.

        # TODO: allow external reference to pass numeric arguement to pass different frequency references
        """
        return bool(int(self.device.instrument.query( "roscillator:locked?" ).rstrip()))
    @reference.setter
    def reference(self, which="int"):
        assert which in ["int", "ext"], "reference not recognised"
        self._reference = which

        self.islocked = True if which == 'ext' else False # emulated the reference locked state
