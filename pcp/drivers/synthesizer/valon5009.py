#Valon 5009 python controller
#Sam Rowe, Cardiff University, 2017

import serial
import serial.tools.list_ports
import time,sys
from numpy import linspace as _linspace

import os
VENDOR = 'valon'
MODELNUMS = ["5009"]

#FTDI chip ID for the valon 5009  found by inspecting output of serial.tools.list_ports.comports()
#hwid_snrs = ['A59JJN5']
#dev_snrs = ['A9040DX6']

#Valon power output
#Default settings:
#	level = 3 which is the highest out of [0,1,2,3].
#	atten = 15dB
#	measured power on Source 1 = +1.27dBm at 512MHz
#	measured power on Source 2 = +1.25dBm at 512MHz

#TBD measure phase noise as a function of power level and attenuation
#    measure flatness versus frequency
#    measure attenuation accuracy
#    figure out reference div/dbl params for optimal phase noise/freq step size

class ValonListMode:
	"""TBD"""
	pass


class ValonDevice(object):

	def __init__(self,device_serial_number,open_connection=True,baud=115200):
		print 'Connecting to Valon 5009 Synthesiser...'
		self.bauds_available = [9600,19200, 38400, 57600, 115200, 230400, 460800, 921600]
		if baud not in self.bauds_available:
			raise StandardError, 'Requested baud rate invalid'
		self.FREQMIN= 23e6
		self.FREQMAX= 6e9
		self.hwid_serial_number   = device_serial_number
		self.serialPort           = self._findSerialPort()
		self.baud_requested       = baud
		self.conn                 = serial.Serial(None, baudrate=baud,timeout=0.1)
		self.conn.port 			  = self.serialPort

		self.status=u''
		self.s1=None
		self.s2=None
		if open_connection:
			self.open_connection()
		print 'OK :)'


	def _findSerialPort(self):
		comports = serial.tools.list_ports.comports()
		for port, desc, hwid in comports:
			if hwid.find(self.hwid_serial_number)>0:
				return port
		return None

	def set_local_baud_auto(self):
		for baud in self.bauds_available:
			print 'trying %d baud...'%baud, ;sys.stdout.flush()
			self.conn.baudrate = baud
			try:
				self.get_status()
				print 'found connection at %d baud.'%baud
				return baud
			except (IOError,StandardError):
				continue

	def open_connection(self):
		self.conn.open()
		try:
			self.clearSerialBuffer()
			self.get_status()
		except (IOError,StandardError):
			self.set_local_baud_auto()
			self.clearSerialBuffer()
			self.conn.write('baud %d \r'%self.baud_requested)
			dump = self.conn.readlines()
			self.conn.baudrate = self.baud_requested
			print 'Now using %d baud'%self.conn.baudrate
			self.clearSerialBuffer()

		self.activeSource       = None
		self.s1 = ValonSource(self,1)
		self.s2 = ValonSource(self,2)
		self._referenceSource   = None
		self._referenceTrim     = None

	def clearSerialBuffer(self):
		self.conn.write('\r')
		readlines = self.conn.readlines()
		if len(readlines) == 0:
			raise IOError, 'Is it switched on?'
		#if readlines[-1] != '\r-1->':
			#raise StandardError

	def get_status(self):
		self.status = unicode(self.sendCommand('status'),encoding='latin-1')
		return self.status

	def sendCommand(self,command):
		self.clearSerialBuffer()
		self.conn.write(command+'\r')
		readlines = self.conn.readlines()
		#print unicode(''.join(readlines),encoding='latin-1')

		messageFound = False
		for line in readlines:
			if line.strip().find(command)>=0:
				messageFound=True
				readlines.pop(readlines.index(line))
				break
		if not messageFound:
			raise StandardError, 'received invalid message'

		prompt  = readlines.pop(-1).strip()
		if prompt.find('1')>=0:
			self.activeSource = 1
		elif prompt.find('2')>=0:
			self.activeSource = 2
		else:
			raise StandardError, 'received invalid prompt message'

		if len(readlines)==0:
			return
		elif len(readlines)==1:
			return readlines[0].strip()
		else:
			message = ''
			for i in readlines:
				message += i.strip()+'\n'
			return message

	def sendCommandFast(self,command):
		self.conn.write(command+'\r')

	def recallFlash(self):
		self.sendCommand('RCL')

	def saveFlash(self):
		self.sendCommand('SAV')

	def factoryReset(self):
		self.sendCommand('RST')

	def displayAllParameters(self):
		self.sendCommand('DALL')

	def displayLockState(self):
		self.sendCommand('LOCK')

	def displayDeviceID(self):
		self.sendCommand('ID')

	def displayHelp(self):
		self.sendCommand('HELP')

	@property
	def referenceTrim(self):
		self._referenceTrim = self.sendCommand('refTrim?')
		return self._referenceTrim
	@referenceTrim.setter
	def referenceTrim(self,value):
		assert value in range(256)
		self.sendCommand('reftrim %s'%value)

	@property
	def referenceSource(self):
		self._referenceSource = self.sendCommand('refs?')
		return self._referenceSource
	@referenceSource.setter
	def referenceSource(self,value):
		"""value = 0 for internal, or 1 for external source \n if using internal source, ext port should be open, i.e. no termination or dc coupled connection"""
		assert value in [0,1]
		self.sendCommand('refs %s'%value)



class ValonSource(object):
	def __init__(self,valonDevice,sourceNumber):
		if sourceNumber not in [1,2]:
			raise ValueError, 'Must select source 1 or 2'
		self.valonDevice          = valonDevice
		self.sourceNumber         = sourceNumber
		self.sourceName           = 'S'+str(sourceNumber)
		self._lock                = None
		self._mode                = None
		self._frequency           = None
		self._frequencyOffset     = None
		self._frequencyIncDecStep = None
		self._sweepStart          = None
		self._sweepStop           = None
		self._sweepStep           = None
		self._sweepRate           = None
		self._sweepTriggerMode    = None
		self._attenuator          = None
		self._powerLevel          = None
		self._powerOutputEnable   = None
		self._powerDown           = None
		self._AMFrequency         = None
		self._AMDepth             = None
		self._PFD                 = None
		self._referenceDoubler    = None
		self._referenceDivider    = None
		self._chargePumpCurrent   = None
		#self._dividerFeedback     = None
		self._SDN                 = None
		self._intFracMode         = None

	def _switchSourcePrompt(self):
		if self.valonDevice.activeSource != self.sourceNumber:
			print 'activating source %d'%self.sourceNumber
			self.valonDevice.sendCommand('source %d'%self.sourceNumber)

	@property
	def lock(self):
		self._lock = self.valonDevice.sendCommand('lock%d?'%self.sourceNumber)
		return self._lock

	def get_locked(self):
		lock = self.lock
		if lock.lower() == 's%d locked'%self.sourceNumber:
			self.locked = True
		else:
			self.locked=False
		return self.locked

	@property
	def mode(self):
		self._mode = self.valonDevice.sendCommand('s%d; mode?'%self.sourceNumber)
		return self._mode
	@mode.setter
	def mode(self,value):
		assert value.upper in ['CW','SWEEP','LIST']
		self.valonDevice.sendCommand('s%d; mode %s'%(self.sourceNumber,value))
		self._mode  = self.mode

	@property
	def Frequency(self):
		self._frequency = self.valonDevice.sendCommand('s%d; frequency?'%self.sourceNumber)
		return self._frequency

	@Frequency.setter
	def Frequency(self,value):
		if value < self.valonDevice.FREQMAX/1.e6:
			value*=1e6

		assert (value > self.valonDevice.FREQMIN) and (value < self.valonDevice.FREQMAX)

		ret = self.valonDevice.sendCommand('s%d; frequency %s'%(self.sourceNumber,value))
		self._frequency  = value
		self.frequencyActual = float(ret.split()[-2])
		if ret[-1] == 'GHz':
			self.frequencyActual*=1e9
		elif ret[-1] == 'MHz':
			self.frequencyActual*=1e6
		elif ret[-1] == 'kHz':
			self.frequencyActual*=1e3

	def get_frequency(self):
		try:
			return self.frequencyActual
		except NameError:
			f = self.Frequency
			return self.frequencyActual

	@property
	def frequencyOffset(self):
		self._frequencyOffset = self.valonDevice.sendCommand('s%d; offset?'%self.sourceNumber)
		return self._frequencyOffset
	@frequencyOffset.setter
	def frequencyOffset(self,value):
		assert value<6e9
		self.valonDevice.sendCommand('s%d; offset %s'%(self.sourceNumber,value))
		self._frequencyOffset  = self.frequencyOffset

	@property
	def frequencyIncDecStep(self):
		self._frequencyIncDecStep = self.valonDevice.sendCommand('s%d; FrequencyStep?'%self.sourceNumber)
		return self._frequencyIncDecStep
	@frequencyIncDecStep.setter
	def frequencyIncDecStep(self,value):
		assert (value>1e3) and (value <100e6)
		self.valonDevice.sendCommand('s%d; frequencyStep %s'%(self.sourceNumber,value))
		self._frequencyIncDecStep  = self.frequencyIncDecStep

	def frequencyIncrement(self):
		self.valonDevice.sendCommand('s%d; frequencyIncrement'%self.sourceNumber)

	def frequencyDecrement(self):
		self.valonDevice.sendCommand('s%d; frequencyDecrement'%self.sourceNumber)

	@property
	def sweepStart(self):
		self._sweepStart = self.valonDevice.sendCommand('s%d; start?'%self.sourceNumber)
		return self._sweepStart
	@sweepStart.setter
	def sweepStart(self,value):
		assert (value > 23e6) and (value <6e9)
		self.valonDevice.sendCommand('s%d; start %s'%(self.sourceNumber,value))
		self._frequencyStart  = self.frequencyStart

	@property
	def sweepStop(self):
		self._sweepStop = self.valonDevice.sendCommand('s%d; stop?'%self.sourceNumber)
		return self._sweepStop
	@sweepStop.setter
	def sweepStop(self,value):
		assert (value > 23e6) and (value <6e9)
		self.valonDevice.sendCommand('s%d; stop %s'%(self.sourceNumber,value))
		self._sweepStop  = self.sweepStop

	@property
	def sweepStep(self):
		self._sweepStep = self.valonDevice.sendCommand('s%d; step?'%self.sourceNumber)
		return self._sweepStep
	@sweepStep.setter
	def sweepStep(self,value):
		assert (value < (self.sweepStop-self.sweepStart))
		self.valonDevice.sendCommand('s%d; step %s'%(self.sourceNumber,value))
		self._sweepStep  = self.sweepStep

	@property
	def sweepRate(self):
		self._sweepRate = self.valonDevice.sendCommand('s%d; rate?'%self.sourceNumber)
		return self._sweepRate
	@sweepRate.setter
	def sweepRate(self,value):
		assert (value>10) and (value<1000)
		self.valonDevice.sendCommand('s%d; rate %s'%(self.sourceNumber,value))
		self._sweepRate = self.sweepRate

	@property
	def sweepTriggerMode(self):
		self._sweepTriggerMode = self.valonDevice.sendCommand('s%d; TMode?'%self.sourceNumber)
		return self._sweepTriggerMode
	@sweepTriggerMode.setter
	def sweepTriggerMode(self,value):
		assert value.lower() in ['auto','manual','man','ext','external']
		value=value[:3]
		self.valonDevice.sendCommand('s%d; TMode %s'%(self.sourceNumber,value))
		self._sweepTriggerMode = self.sweepTriggerMode

	def sweepManualTrigger(self):
		"""manually trigger a full sweep if in manual trigger mode"""
		self.valonDevice.sendCommand('TRGR')

	def sweepRun(self,source=None):
		"""start sweeping"""
		if source is None:
			source = self.sourceNumber
		assert source in [0,1,2,3]
		if source in [0,self.sourceNumber]:
				self.valonDevice.sendCommand('s%d; Run 0'%self.sourceNumber)
		else:
			self.valonDevice.sendCommand('s%d; Run %d'%(self.sourceNumber,value))

	def sweepHalt(self,source=None):
		"""start sweeping"""
		if source is None:
			source = self.sourceNumber
		assert source in [0,1,2,3]
		if source in [0,self.sourceNumber]:
				self.valonDevice.sendCommand('s%d; Halt 0'%self.sourceNumber)
		else:
			self.valonDevice.sendCommand('s%d; Halt %d'%(self.sourceNumber,source))

	@property
	def attenuator(self):
		self._attenuator = self.valonDevice.sendCommand('s%d; attenuator?'%self.sourceNumber)
		return self._attenuator
	@attenuator.setter
	def attenuator(self,value):
		assert value in _linspace(0,31.5,64)
		self.valonDevice.sendCommand('s%d; att %s'%(self.sourceNumber,value))
		self._attenuator = self.attenuator

	@property
	def powerLevel(self):
		self._powerLevel = self.valonDevice.sendCommand('s%d; plevel?'%self.sourceNumber)
		return self._powerLevel

	@powerLevel.setter
	def powerLevel(self,value):
		assert value in [0,1,2,3]
		self.valonDevice.sendCommand('s%d; plevel %s'%(self.sourceNumber,value))
		self._powerLevel = self.powerLevel

	@property
	def powerOutputEnable(self):
		"""Source Amplifier On/Off"""
		self._powerOutputEnable = self.valonDevice.sendCommand('s%d; oen?'%self.sourceNumber)
		return self._powerOutputEnable
	@powerOutputEnable.setter
	def powerOutputEnable(self,value):
		assert value in [0,1,'ON','on','On','OFF','off','Off']
		self.valonDevice.sendCommand('s%d; oen %s'%(self.sourceNumber,value))
		self._powerOutputEnable = self.powerOutputEnable

	@property
	def powerDown(self):
		"""Complete Source Power On/Off"""
		self._powerDown = self.valonDevice.sendCommand('s%d; pdn?'%self.sourceNumber)
		return self._powerDown
	@powerDown.setter
	def powerDown(self,value):
		assert value in [0,1,'ON','on','On','OFF','off','Off']
		self.valonDevice.sendCommand('s%d; pdn %s'%(self.sourceNumber,value))
		self._powerDown = self.powerDown

	@property
	def AMFrequency(self):
		self._AMFrequency = self.valonDevice.sendCommand('s%d; AMF?'%self.sourceNumber)
		return self._AMFrequency
	@AMFrequency.setter
	def AMFrequency(self,value):
		assert (value > 0.5) and (value <= 10e3)
		self.valonDevice.sendCommand('s%d; AMF %s'%(self.sourceNumber,value))
		self._AMFrequency = self.AMFrequency

	@property
	def AMDepth(self):
		self._AMDepth = self.valonDevice.sendCommand('s%d; AMD?'%self.sourceNumber)
		return self._AMDepth
	@AMDepth.setter
	def AMDepth(self,value):
		assert value in _linspace(0,31.5,64)
		self.valonDevice.sendCommand('s%d; AMD %s'%(self.sourceNumber,value))
		self._AMDepth = self.AMDepth


	@property
	def PFD(self):
		self._PFD = self.valonDevice.sendCommand('s%d; pfd ?'%self.sourceNumber)
		return self._PFD
	@PFD.setter
	def PFD(self,value):
		assert (value >= 1e6) and (value<140e6)
		self.valonDevice.sendCommand('s%d; pfd %s'%(self.sourceNumber,value))
		self._PFD = self.PFD

	@property
	def referenceDoubler(self):
		self._referenceDoubler = self.valonDevice.sendCommand('s%d; refdb ?'%self.sourceNumber)
		return self._referenceDoubler
	@referenceDoubler.setter
	def referenceDoubler(self,value):
		assert value in [0,1]
		self.valonDevice.sendCommand('s%d; refdb %s'%(self.sourceNumber,value))
		self._referenceDoubler = self.referenceDoubler

	@property
	def referenceDivider(self):
		self._referenceDivider = self.valonDevice.sendCommand('s%d; refdiv ?'%self.sourceNumber)
		return self._referenceDivider
	@referenceDivider.setter
	def referenceDivider(self,value):
		assert value in [0,1]
		self.valonDevice.sendCommand('s%d; refdiv %s'%(self.sourceNumber,value))
		self._referenceDivider = self.referenceDivider

	@property
	def chargePumpCurrent(self):
		self._chargePumpCurrent = self.valonDevice.sendCommand('s%d; cp ?'%self.sourceNumber)
		return self._chargePumpCurrent
	@chargePumpCurrent.setter
	def chargePumpCurrent(self,value):
		assert value in range(16)
		self.valonDevice.sendCommand('s%d; cp %s'%(self.sourceNumber,value))
		self._chargePumpCurrent = self.chargePumpCurrent

	#@property
	#def dividerFeedback(self):
		#self._dividerFeedback = self.valonDevice.sendCommand('divfb ?')
		#return self._dividerFeedback
	#@dividerFeedback.setter
	#def dividerFeedback(self,value):
		#assert value in ['VCO','Divider']
		#self.valonDevice.sendCommand('divfb %s'%value)
		#self._dividerFeedback = self.dividerFeedback

	@property
	def SDN(self):
		"""spur mitigation mode...
		0:=low noise mode, 2:=low spur mode 1, 3:=low spur mode 2"""
		self._SDN = self.valonDevice.sendCommand('s%d; sdn ?'%self.sourceNumber)
		return self._SDN
	@SDN.setter
	def SDN(self,value):
		"""spur mitigation mode...
		0:=low noise mode, 2:=low spur mode 1, 3:=low spur mode 2"""
		assert value in [0,2,3]
		self.valonDevice.sendCommand('s%d; sdn %s'%(self.sourceNumber,value))
		self._SDN = self.SDN

	@property
	def intFracMode(self):
		"""intfrac mode... 0:=fractional mode, 1:=integer mode, 2:=auto"""
		self._intFracMode = self.valonDevice.sendCommand('s%d; intfrac ?'%self.sourceNumber)
		return self._intFracMode
	@intFracMode.setter
	def intFracMode(self,value):
		"""intfrac mode... 0:=fractional mode, 1:=integer mode, 2:=auto"""
		assert value in [0,1,2]
		self.valonDevice.sendCommand('s%d; intfrac %s'%(self.sourceNumber,value))
		self._intFracMode = self.intFracMode

	@property
	def sName(self):
		self._sName = self.valonDevice.sendCommand('s%d; name ?'%self.sourceNumber)
		return self._sName
	@sName.setter
	def sName(self,value):
		assert value in [0,1,2]
		self.valonDevice.sendCommand('s%d; name %s'%(self.sourceNumber,value))
		self._sName = self.sName

	def set_frequency(self,source,frequency,fast=False):
		if fast:
			if source==0:
				source=1
			if source==8:
				source=2
			assert frequency > self.valonDevice.FREQMIN and frequency < self.valonDevice.FREQMAX
			self.valonDevice.sendCommandFast('s%d; frequency %s'%(source,frequency))
			return 1
		else:
			self.Frequency = frequency
			return 1
	def get_frequency(self):
		return self.Frequency
