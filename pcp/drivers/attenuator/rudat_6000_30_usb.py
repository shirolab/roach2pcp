"""
rudat_6000_30_usb.py
Sam Rowe, Cardiff University, 2016

Provides a class with a property 'att' to get/set the attenuation levels

Provides a dict of attenuator objects named by the last three digits
of the device serial number.

>>> from rudat_6000_30_usb import *
RUDAT attenuators connected:
{161: <rudat_6000_30_usb.Attenuator object at 0x7fea2a83d910>,
 162: <rudat_6000_30_usb.Attenuator object at 0x7fea2a83dc90>}

>>> rudats
{161: <rudat_6000_30_usb.attenuator at 0x7fb403b6ded0>,
 162: <rudat_6000_30_usb.attenuator at 0x7fb403b6de90>}

>>> rudats[161].att = 15.25
RUDAT with serial #11508260161 set to 15.25 dB

>>> print rudats[161].att
15.25

To reload the list of connected rudats...
>>> rudats = get_attenuators()

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

#USB HID codes
VEND_ID      = 0x20ce #Mini-Circuits
PROD_ID      = 0x23   #Programmable Attenuator

#Command Codes (see the device manual)
GET_DEVICE_MODEL_NAME     = 40
GET_DEVICE_SERIAL_NUMBER  = 41
SET_ATTENUATION           = 19
READ_ATTENUATION          = 18
GET_FIRMWARE              = 99

#Other globals
NULL        = 0
TX_BUF_SIZE = 64 #bytes [B0,B1,B2...BN]
RX_BUF_SIZE = 64 #bytes [B0,B1,B2...BN]
ATT_MAX     = 30.0
ATT_MIN     = 0.0
RESOLUTION  = 0.25

class Attenuator(object):

	"""
	Provides an attenuator object for control/query of
	a Mini-Circuits RUDAT programmable attenuator over USB HID.

	e.g. instantiate object (where <device> is a pyusb device object.)
	>>> rudat = Attenuator(device)

	e.g. Query device serial number:
	>>> print rudat.serial_number
	'11508260161'

	e.g. Query the current attenuation level:
	>>> print rudat.att
	30.0

	e.g. Set the attenuation level
	>>> rudat.att = 12.5
	RUDAT with serial #11508260161 set to 12.50 dB

	Or, use regular get/set functions, e.g.
	>>> rudat.set_atten(12.5)
	RUDAT with serial #11508260161 set to 12.50 dB
	>>> print rudat.att
	12.5

	"""

	def __init__(self,dev):
		self._device = dev
		self._endpoint_in  = self._device[0][(0,0)][0]
		self._endpoint_out = self._device[0][(0,0)][1]
		self.model_name    = self._get_device_model_name()
		self.serial_number = self._get_device_serial_number()
		self.firmware      = self._get_firmware()
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
		assert (value/RESOLUTION)%1==0, 'Resolution is %d dB!'%RESOLUTION
		integer_value    = int(value)
		fractional_value = int((value - integer_value)/RESOLUTION)
		arr              = [chr(SET_ATTENUATION)] + [chr(integer_value)] + \
				[chr(fractional_value)] + [chr(NULL)]*(TX_BUF_SIZE-3)
		tx_arr           = usb.core.array.array('c',arr)
		self._device.write(self._endpoint_out, tx_arr)

		rx_arr     = self._device.read(self._endpoint_in, RX_BUF_SIZE)
		self._att  = value
		print 'RUDAT with serial #%s set to %.2f dB'%(self.serial_number,self.att)

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

	def get_atten(self):
		return self.att

	def set_atten(self,atten):
		self.att = atten

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


def get_attenuators():

	"""
	Returns a dict of all connected Mini-Circuits RUDAT attenuators.

	Key names are taken from the last three digits of the device serial numbers
	"""

	found = usb.core.find(idVendor=VEND_ID, idProduct=PROD_ID, find_all=True)

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

	atts = [Attenuator(d) for d in devs]
	#print atts
	names = [int(att.serial_number) for att in atts]
	#print names

	return dict(zip(names,atts))

# rudats = get_attenuators()
# print 'RUDAT attenuators connected:'
# print rudats
