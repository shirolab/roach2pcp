import valon_synth
import valon_synth9
import utils

#python class to hand switch between different sources ie
#valon 5008, 5009 windfreak source and Anritsu source
#currently only works for valon 5008 and 5009

class frequency_source:
	def __init__(self, clock_or_lo):
		config = utils.read_config()
		if clock_or_lo == "clock":
			self.source_type = config['clock_source']
			self.port = int(config['clock_source_port'])
			self.usb_port = config['clock_source_usb']
		elif clock_or_lo == "lo":
			self.source_type = config['lo_source']
			self.port = int(config['lo_source_port'])
			self.usb_port = config['clock_source_usb']
		else:
			print("Please specify clock or lo as str when intializing a frequency source")

		if self.source_type == "valon5009":
			self.source = valon_synth9.Synthesizer('/dev/ttyUSB4')
		elif self.source_type == "valon5008":
			self.source = valon_synth9.Synthesizer('/dev/ttyUSB4')
		else:
			print "unkown frequency source"

	def set_frequency(self,freq):
		#sets the frequency in MHz
		if self.source_type == "valon5009":
			self.source.set_frequency(self.port,freq)
		elif self.source_type == "valon5008":
			self.source.set_frequency(self.port,freq,0.01)


	def get_frequency(self):
		#sets the frequency in MHz
		if self.source_type == "valon5009":
			val = self.source.get_frequency(self.port)
		elif self.source_type == "valon5008":
			val = self.source.get_frequency(self.port)
		return val
		
			
