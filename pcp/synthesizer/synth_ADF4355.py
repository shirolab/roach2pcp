"""
synth_ADF4355.py
Jose Miguel Garcia & Marcial Becerril INAOE february 2019.

This class provides methods to set and get the fequency of 
the synthesizer ADF4355
"""

import serial
import serial.tools.list_ports
import time as _time

#Serial Parameters
BAUDRATE = 115200
NBITS = serial.EIGHTBITS
PARITY = serial.PARITY_NONE
STOP = serial.STOPBITS_ONE

#Synthesizer parameters
SYNTH_FREQ_MAX = 3.4e9
SYNTH_FREQ_MIN  = 54.e6
RESOLUTION  = 1

VENDOR = 'inaoe'
MODELNUMS = ['adf4355']
SERIALNUMBER = '001'

class ADF4355synthDevice(object):
	
	def __init__(self, serialNumber=SERIALNUMBER):

		self.vendor   = VENDOR
		self.modelnum = MODELNUMS[0]
		self.serialNumber = serialNumber

		print 'Connecting to ADF4355 Synthesizer...'

		self.device = serial.Serial(None, timeout=0.01)
		self.device.baudrate = BAUDRATE
		self.device.bytesize = NBITS
		self.device.parity = PARITY
		self.device.stopbits = STOP

		# Look for the device
		status = self._findSerialPort(serialNumber)

		if not status:
			print 'Error, device not found'	
			return 
		
	def _findSerialPort(self,serialNumber):
		statusConnect = False
		comports = serial.tools.list_ports.comports()
		for port, desc, hwid in comports:
			self.device.port = port
			if self.device.isOpen() == False:
				try:
					self._openConnection()
					model = self.get_device_serial_number()
					if model == "SN:" + serialNumber + "\r\n":
						statusConnect = True
						print "Device connected :)"
						return statusConnect
					else:
						self._closeConnection()
				except Exception as e: 
					print e
					self._closeConnection()
	
		return statusConnect

	def get_device_serial_number(self):
		self.device.reset_input_buffer()
		cnt_try = 0
		while self.device.in_waiting == 0 and cnt_try < 20:
			self.device.write("S\n")
			_time.sleep(0.1)
			cnt_try += 1
		model = self.device.readlines()[0]
		return model

	def _openConnection(self):
		self.device.open()

	def _closeConnection(self):
		self.device.close()

	def get_status(self):
		if self.device.is_open:
			return 'Connected.'
		else:
			return 'Not Connected.'

class ADF4355synthSource(object):
  
	def __init__(self, ADF4355synthDevice, sourceNumber=0):
	
		self.ADF4355SynthDevice = ADF4355synthDevice
		self.sourceNumber = sourceNumber

	def getFrequency(self):
		self.ADF4355SynthDevice.device.reset_input_buffer()
		while self.ADF4355SynthDevice.device.in_waiting == 0:
			self.ADF4355SynthDevice.device.write("R\n")
			_time.sleep(0.1)
		freq_value = int(self.ADF4355SynthDevice.device.readlines()[0][1:-2])
		self._freq = freq_value
		return self._freq
	
	def setFrequency(self,value):
		assert value <= SYNTH_FREQ_MAX, 'Frequency over range!'
		assert value >= SYNTH_FREQ_MIN, 'Frequency under range!'
		assert (value/RESOLUTION)%1==0, 'Resolution is %.2f dB!'%RESOLUTION
		
		freq_value = str(int(value))

		self.ADF4355SynthDevice.device.write("F" + freq_value + "\n")
		self._freq = value
		
		print 'Frequency set to %.2f Hz'%(self._freq)
