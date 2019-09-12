"""
rudat_6000_30_usb.py
Sam Rowe, Cardiff University, 2016

Provides a class with a property 'att' to get/set the attenuation levels

*****************************************************************************
Requires pyusb:
$ pip install pyusb

Also requires a udev rule for permission to write to usb without sudo e.g:
$ echo 'SUBSYSTEMS=="usb", ATTRS{product}=="Mini-Circuits", GROUP="plugdev"' 
> /etc/udev/rules.d/10-local.rules
$ udevadm trigger
*****************************************************************************

TBD: measure frequency response and power levels as functions of attenuation

"""

import usb.core

VENDOR      = "minicircuits" #Mini-Circuits
MODELNUMS = ["rudat6000"]   #Programmable Attenuator

#USB HID codes
VEND_ID      = 0x20ce #Mini-Circuits
PROD_ID = [0x23]   #Programmable Attenuator

#Command Codes (see the device manual)
GET_DEVICE_MODEL_NAME     = 40
GET_DEVICE_SERIAL_NUMBER  = 41
GET_FIRMWARE              = 99
SET_ATTENUATION           = 19
READ_ATTENUATION          = 18

#Other globals
NULL        = 0
TX_BUF_SIZE = 64 #bytes [B0,B1,B2...BN]
RX_BUF_SIZE = 64 #bytes [B0,B1,B2...BN]
ATT_MAX     = 60.0
ATT_MIN     = 0.0
RESOLUTION  = 0.25

class rudat6000Device(object):
	
	def __init__(self,dev):

		self.vendor = VENDOR
		self.modelnum = MODELNUMS[0]

		self._device = dev
		self._endpoint_in  = self._device[0][(0,0)][0]
		self._endpoint_out = self._device[0][(0,0)][1]
		self.model_name    = self._get_device_model_name()
		self.serial_number = self._get_device_serial_number()
		self.firmware      = self._get_firmware()

	def _get_device_model_name(self):
		arr    = [chr(GET_DEVICE_MODEL_NAME)] + [chr(NULL)]*(TX_BUF_SIZE-1) 
		tx_arr = usb.core.array.array('c',arr)
		self._device.write(self._endpoint_out, tx_arr)
		
		rx_arr       = self._device.read(self._endpoint_in, RX_BUF_SIZE)
		model_number = rx_arr[1:rx_arr.index(NULL)].tostring()
		return model_number

	def _get_device_serial_number(self):
		arr    = [chr(GET_DEVICE_SERIAL_NUMBER)] + [chr(NULL)]*(TX_BUF_SIZE-1) 
		tx_arr = usb.core.array.array('c',arr)
		self._device.write(self._endpoint_out, tx_arr)
		
		rx_arr        = self._device.read(self._endpoint_in, RX_BUF_SIZE)
		serial_number = rx_arr[1:rx_arr.index(NULL)].tostring()
		return serial_number

	def _get_firmware(self):
		arr    = [chr(GET_FIRMWARE)] + [chr(NULL)]*(TX_BUF_SIZE-1) 
		tx_arr = usb.core.array.array('c',arr)
		self._device.write(self._endpoint_out, tx_arr)
		
		rx_arr   = self._device.read(self._endpoint_in, RX_BUF_SIZE)
		firmware = rx_arr[3:rx_arr.index(NULL)].tostring()
		return firmware
	
	def get_model(self):
		return self.model_name
	
	def get_serial(self):
		return self.serial_number
	
	def get_status(self):
		try:
			ret=self.get_model()
			return 'Connected.'
		except:
			return 'Not Connected.'

class rudat6000Source(object):

	def __init__(self, rudat6000Device, sourceNumber):

		self.rudat6000Device = rudat6000Device
		self.sourceNumber = sourceNumber

		self._device = self.rudat6000Device._device
		self._endpoint_in  = self._device[0][(0,0)][0]
		self._endpoint_out = self._device[0][(0,0)][1]
		self._att          = None

	@property
	def att(self):
		arr              = [chr(READ_ATTENUATION)] + [chr(NULL)]*(TX_BUF_SIZE-1) 
		tx_arr           = usb.core.array.array('c',arr)
		self._device.write(self._endpoint_out, tx_arr)
		
		rx_arr           = self._device.read(self._endpoint_in, RX_BUF_SIZE)
		integer_value    = float(rx_arr[1])
		fractional_value = float(rx_arr[2])/4.
		attenuation      = integer_value + fractional_value
		
		self._att        = attenuation
		return self._att

	@att.setter
	def att(self,value):
		assert value <= ATT_MAX, 'Attenuation over range!'
		assert value >= ATT_MIN, 'Attenuation under range!'
		assert (value/RESOLUTION)%1==0, 'Resolution is %f dB!'%RESOLUTION
		integer_value    = int(value)
		fractional_value = int((value - integer_value)/RESOLUTION)
		arr              = [chr(SET_ATTENUATION)] + [chr(integer_value)] + \
				[chr(fractional_value)] + [chr(NULL)]*(TX_BUF_SIZE-3) 
		tx_arr           = usb.core.array.array('c',arr)
		self._device.write(self._endpoint_out, tx_arr)
		
		rx_arr     = self._device.read(self._endpoint_in, RX_BUF_SIZE)
		self._att  = value
		print 'RUDAT with serial #%s set to %.2f dB'%(self.rudat6000Device.serial_number,self.att)
		
	def get_atten(self):
		return self.att
	
	def set_atten(self,atten):
		self.att = atten

def get_attenuators():
	"""
	Returns a dict of all connected Mini-Circuits RUDAT attenuators.
	"""
	found = usb.core.find(idVendor=VEND_ID, idProduct=PROD_ID[0], find_all=True)

	assert found is not None, 'No devices found!'

	if isinstance(found, usb.core.Device):
		devs = [found]
	else:
		devs = list(found)

	for dev in devs:
		dev.reset() #releases any previous instances of the device
		for config in dev:
			for i in range(config.bNumInterfaces):
					if dev.is_kernel_driver_active(i):
						dev.detach_kernel_driver(i)
	
	atts = [rudat6000Device(d) for d in devs]
	names = [int(att.serial_number) for att in atts]
	
	return dict(zip(names,devs))

