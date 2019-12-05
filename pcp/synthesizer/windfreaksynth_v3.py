# Windfreaktech SynthHD python controller
# Sam Rowe, Cardiff University, 2018

# NOTE: all frequencies should be given in Hz, and powers in dBm.

import serial
import serial.tools.list_ports
import time

VENDOR = 'windfreaktech'
MODELNUMS = ["synthhd"]

def read_acm_ports():
    acm_ports = []
    com_ports = serial.tools.list_ports.comports()
    for port, desc, hwid in com_ports:
        if port.startswith("/dev/ttyACM"):
            acm_ports.append(port)
    return acm_ports

ACM_PORTS = read_acm_ports()

#serial port snrs for device identification
#hwid_snrs = ['4294967295']
#dev_snrs = ['656']

class SynthHDDevice(object):

    def __init__(self, serial_number, open_connection=True):

        self.vendor   = VENDOR
        self.modelnum = MODELNUMS[0]

        print 'Connecting to WFT SynthHD Synthesiser...'
        self.serialNumber   = serial_number
        self.FREQMIN        = 53e6
        self.FREQMAX        = 14000e6
        self.POWMIN         = -60.0
        self.POWMAX         = +20.0
        #self.serialPort     = self._findSerialPort()
 	self.serialPort     = '/dev/windfreak_synth_%s'%serial_number
        self.conn           = serial.Serial(None, timeout=0.1)
        self.conn.port      = self.serialPort
        if open_connection:
            self._openConnection()
            self.getStatus()
        print 'OK :)'
        #self.setReferenceSelect(1) #int27 TODO: this will be external when synths locked

        #keep track of which source is being controlled
        #really needs to link to config file.
        #self.src0 = SynthHDSource(self,0)
        #self.src1 = SynthHDSource(self,1)
        self.active_channel = self.getControlChannel()

    def _findSerialPort(self):
        comports = serial.tools.list_ports.comports()
        for port, desc, hwid in comports:
            if hwid.find(self.serialNumber)>0:
                return port
        print 'Error, device not found'
        return None

    def _findSerialPort_byKnownPort(self):
        ACM_PORTS = read_acm_ports()
        for port in ACM_PORTS:
            temp_conn = serial.Serial(None, timeout=0.1)
            temp_conn.port = port
            try:
                temp_conn.open()
            except (OSError, serial.SerialException):
                print "Port " + port  + " already open"

            # Clear the buffer
            try:
                temp_conn.readlines()
            except:
                pass
            # Get the Serial Number
            temp_conn.write('-')
            time.sleep(0.5)
            readlines = temp_conn.readlines()
            if len(readlines) != 0:
                snr = readlines[0].strip()
                temp_conn.close()
                if snr == self.serialNumber:
                    print "Port: " + port + "   S/N: " + snr
                    return port
        print 'Error, device not found'
        return None

    def _openConnection(self):
        self.conn.open()

    def _closeConnection(self):
        self.conn.close()

    def _clearSerialBuffer(self):
        self.conn.readlines()

    def getStatus(self):
        self.status = 'Not implemented yet'
        return self.status

    def sendCommand(self,command,clearbuf=True,getResponse=True):
        if clearbuf: self._clearSerialBuffer()
        self.conn.write(command)
        if getResponse:
            readlines = self.conn.readlines()
            if len(readlines)==0:
                return
            elif len(readlines)==1:
                return readlines[0].strip()
            else:
                message = ''
                for i in readlines:
                    message += i.strip()+'\n'
                return message


    def sendCommandFast(self,command,dwell=0.0):
        self.sendCommand(command,clearbuf=False,getResponse=False)
        #time.sleep(dwell)

    def getHelp(self):
        print self.sendCommand('?')

    def getControlChannel(self):
        try:
            return int(self.sendCommand('C?'))
        except TypeError:
            return None

    def setControlChannel(self,value):
        value = int(value)
        assert value in [0,1], 'value error'
        self.active_channel = value
        return self.sendCommand('C%d'%value)

    def getVersionFW(self):
        return self.sendCommand('v0')
    def getVersionHW(self):
        return self.sendCommand('v1')

    def _programAllSettingsToEEPROM(self):
        self.sendCommand('e')

    def getReferenceSelect(self):
        # y=0=external, y=1=internal 27MHz, y=2=internal 10MHz
        return int(self.sendCommand('x?'))
    def setReferenceSelect(self,value):
        assert value in (0,1,2)
        self.sendCommand('x%d'%(int(value)))

    def getTriggerConnectorFunctions(self):
        # 0) No Triggers
        # 1) Trigger full frequency sweep
        # 2) Trigger single frequency step
        # 3) Trigger 'stop all' which pauses sequencing through all functions of the SynthHD
        # 4) Trigger digital RF ON/OFF - Could be used for External Pulse Modulation
        # 5) Remove Interrupts (Makes modulation have less jitter - use carefully)
        # 6) Reserved
        # 7) Reserved
        # 8) External AM modulation input (requires AM Internal modulation LUT set to ramp)
        # 9) External FM modulation input (requires FM Internal modulation set to chirp)
        return int(self.sendCommand('w?'))
    def setTriggerConnectorFunctions(self,value):
        assert value in range(10)
        self.sendCommand('w%d'%(int(value)))

    def getPLLReferenceFrequency(self):
        return float(self.sendCommand('*?'))*1e6
    def setPLLReferenceFrequency(self,value):
        assert value>=10e6 and value<=100e6
        self.sendCommand('*%.3f'%(value/1e6))

    def getModelType(self):
        return self.sendCommand('+')
    def getSerialNumber(self):
        return self.sendCommand('-')

    

    def getTemperature(self):
        return float(self.sendCommand('z'))

    def getCalibrationSuccess(self):
        return bool(int(self.sendCommand('V?')))


class SynthHDSource(object):

    def __init__(self, SynthHDDevice, sourceNumber):

        self.SynthHDDevice = SynthHDDevice
        self.sourceNumber = sourceNumber

        assert self.sourceNumber in (0,1), "Source must be 0 or 1."

        """
        if self.sourceNumber == 0:
            self.SynthHDDevice.active_channel = self.sourceNumber
            self.SynthHDDevice.setControlChannel(self.sourceNumber)
        elif self.sourceNumber == 1:
            self.SynthHDDevice.active_channel = self.sourceNumber
            self.SynthHDDevice.setControlChannel(self.sourceNumber)
        """
        self.SynthHDDevice.active_channel = self.sourceNumber
        self.SynthHDDevice.setControlChannel(self.sourceNumber)

    def _checkSource(self):
        if self.SynthHDDevice.active_channel != self.sourceNumber:
            print 'WINDFREAK SYNTHHDSOURCE: changing control channel from %s to %s'%(self.SynthHDDevice.active_channel,self.sourceNumber)
            self.SynthHDDevice.setControlChannel(self.sourceNumber)
            self.SynthHDDevice.active_channel = self.SynthHDDevice.getControlChannel()

    def getPLLPowerOn(self):
        self._checkSource()
        return bool(int(self.SynthHDDevice.sendCommand('E?')))
    def setPLLPowerOn(self,value):
        assert value in (True,False)
        self._checkSource()
        self.SynthHDDevice.sendCommand('E%d'%(int(value)))

    #I) PLL output power 2, 2
    #U) PLL charge pump current 3, 3
    #d) PLL mute till LD 1, 1
    #m) Muxout function 6, 6
    #T) Autocal On(1) or Off(0) 1, 1
    #b) Feedback select Fundamental(1) or Divided(0) 0, 0
    #i) Mathematical spacing (Hz) 100.000, 100.000

    def getFrequency(self):
        self._checkSource()
        return float(self.SynthHDDevice.sendCommand('f?'))*1e6

    def setFrequency(self,value):
        assert value>=self.SynthHDDevice.FREQMIN, 'value too low'
        assert value<=self.SynthHDDevice.FREQMAX, 'value too high'
        self._checkSource()
        return self.SynthHDDevice.sendCommand('f%.8f'%(value/1e6))

    def setFrequencyFast(self,value):
        assert value>=self.SynthHDDevice.FREQMIN, 'value too low'
        assert value<=self.SynthHDDevice.FREQMAX, 'value too high'
        self._checkSource()
        self.SynthHDDevice.sendCommandFast('f%.8f'%(value/1e6))

    def getPower(self):
        self._checkSource()
        return float(self.SynthHDDevice.sendCommand('W?'))
        
    def setPower(self,value):
        assert value>=self.SynthHDDevice.POWMIN, 'value too low'
        assert value<=self.SynthHDDevice.POWMAX, 'value too high'
        self._checkSource()
        self.SynthHDDevice.sendCommand('W%.3f'%(value))

    def getTemperatureCompensationSetting(self):
        # (0=none, 1=on set, 2=1sec, 3=10sec)
        self._checkSource()
        return int(self.SynthHDDevice.sendCommand('Z?'))
    def setTemperatureCompensationSetting(self,value):
        # (0=none, 1=on set, 2=1sec, 3=10sec)
        assert value in (0,1,2,3)
        self._checkSource()
        self.SynthHDDevice.sendCommand('Z%d'%value)

    def getVGADACSetting(self):
        self._checkSource()
        return int(self.SynthHDDevice.sendCommand('a?'))
    def setVGADACSetting(self,value):
        assert value in range(0,45001)
        self._checkSource()
        self.SynthHDDevice.sendCommand('a%d'%value)

    def getPhaseStep(self):
        self._checkSource()
        return float(self.SynthHDDevice.sendCommand('~?'))
    def setPhaseStep(self,value):
        assert value>=0.0 and value<=360.0
        self._checkSource()
        self.SynthHDDevice.sendCommand('~%.4f'%value)

    def getRFMuteOff(self):
        self._checkSource()
        return bool(int(self.SynthHDDevice.sendCommand('h?')))
    def setRFMuteOff(self,value):
        assert value in (True,False)
        self._checkSource()
        self.SynthHDDevice.sendCommand('h%d'%(int(value)))

    def getRFAmpOn(self):
        self._checkSource()
        return bool(int(self.SynthHDDevice.sendCommand('r?')))
    def setRFAmpOn(self,value):
        assert value in (True,False)
        self._checkSource()
        self.SynthHDDevice.sendCommand('r%d'%(int(value)))

    def getSweepLowerFreq(self):
        self._checkSource()
        return float(self.SynthHDDevice.sendCommand('l?'))*1e6
    def setSweepLowerFreq(self,value):
        assert value>=self.SynthHDDevice.FREQMIN, 'value too low'
        assert value<=self.SynthHDDevice.FREQMAX, 'value too high'
        self._checkSource()
        self.SynthHDDevice.sendCommand('l%.8f'%(value/1e6))

    def getSweepUpperFreq(self):
        self._checkSource()
        return float(self.SynthHDDevice.sendCommand('u?'))*1e6
    def setSweepUpperFreq(self,value):
        assert value>=self.SynthHDDevice.FREQMIN, 'value too low'
        assert value<=self.SynthHDDevice.FREQMAX, 'value too high'
        self._checkSource()
        self.SynthHDDevice.sendCommand('u%.8f'%(value/1e6))

    def getSweepStepSize(self):
        self._checkSource()
        return float(self.SynthHDDevice.sendCommand('s?'))*1e6
    def setSweepStepSize(self,value):
        self._checkSource()
        self.SynthHDDevice.sendCommand('s%.8f'%(value/1e6))

    def getSweepStepTime(self):
        self._checkSource()
        return float(self.SynthHDDevice.sendCommand('t?'))*1e3
    def setSweepStepTime(self,value):
        assert value>=0.004 and value<=10.000
        self._checkSource()
        self.SynthHDDevice.sendCommand('t%.3f'%(value/1e3))

    def getSweepAmplitudeLow(self):
        self._checkSource()
        return float(self.SynthHDDevice.sendCommand('[?'))
    def setSweepAmplitudeLow(self,value):
        assert value>=-60 and value<=20
        self._checkSource()
        self.SynthHDDevice.sendCommand('[%.3f'%(value))

    def getSweepAmplitudeHigh(self):
        self._checkSource()
        return float(self.SynthHDDevice.sendCommand(']?'))
    def setSweepAmplitudeHigh(self,value):
        assert value>=-60 and value<=20
        self._checkSource()
        self.SynthHDDevice.sendCommand(']%.3f'%(value))

    def getSweepDirection(self):
        self._checkSource()
        #(up=1 / down=0)
        return int(self.SynthHDDevice.sendCommand('^?'))
    def setSweepDirection(self,value):
        #(up=1 / down=0)
        assert value in [1,0]
        self._checkSource()
        self.SynthHDDevice.sendCommand('^%d'%(value))

    def getSweepDifferentialFrequencySeparation(self):
        self._checkSource()
        return float(self.SynthHDDevice.sendCommand('k?'))*1e6
    def setSweepDifferentialFrequencySeparation(self,value):
        self._checkSource()
        self.SynthHDDevice.sendCommand('k%.8f'%(value/1e6))

    def getSweepDifferentialMethod(self):
        self._checkSource()
        #(0=off, 1=ChA-DiffFreq, 2=ChA+DiffFreq)
        return int(self.SynthHDDevice.sendCommand('n?'))
    def setSweepDifferentialMethod(self,value):
        #(0=off, 1=ChA-DiffFreq, 2=ChA+DiffFreq)
        assert value in [0,1,2]
        self._checkSource()
        self.SynthHDDevice.sendCommand('n%d'%(value))

    def getSweepType(self):
        self._checkSource()
        #(linear=0 / tabular=1)
        return int(self.SynthHDDevice.sendCommand('X?'))
    def setSweepType(self,value):
        #(linear=0 / tabular=1)
        assert value in [0,1]
        self._checkSource()
        self.SynthHDDevice.sendCommand('X%d'%value)

    def getSweepRun(self):
        self._checkSource()
        #(on=1 / off=0)
        return int(self.SynthHDDevice.sendCommand('g?'))
    def setSweepRun(self,value):
        #(on=1 / off=0)
        assert value in [0,1]
        self._checkSource()
        self.SynthHDDevice.sendCommand('g%d'%value)

    def getSweepContinuous(self):
        self._checkSource()
        #(on=1 / off=0)
        return int(self.SynthHDDevice.sendCommand('c?'))
    def setSweepContinuous(self,value):
        #(on=1 / off=0)
        assert value in [0,1]
        self._checkSource()
        self.SynthHDDevice.sendCommand('c%d'%value)

    def getAMStepTime(self):
        self._checkSource()
        return float(self.SynthHDDevice.sendCommand('F?'))/1e6
    def setAMStepTime(self,value):
        self._checkSource()
        self.SynthHDDevice.sendCommand('F%d'%(value*1e6))

    def getAMNumberRepetitions(self):
        self._checkSource()
        return int(self.SynthHDDevice.sendCommand('q?'))
    def setAMNumberRepetitions(self,value):
        self._checkSource()
        self.SynthHDDevice.sendCommand('q%d'%(value))

    def getAMRunContinuously(self):
        self._checkSource()
        #(on=1 / off=0)
        return int(self.SynthHDDevice.sendCommand('A?'))
    def setAMRunContinuously(self,value):
        #(on=1 / off=0)
        assert value in [1,0]
        self._checkSource()
        self.SynthHDDevice.sendCommand('A%d'%(value))

    def getAMLookupTable(self):
        self._checkSource()
        #always 100 samples long but samples ignored if value==-75.0
        return [float(self.SynthHDDevice.sendCommand('@%da?'%(j))) for j in range(100)]
    def setAMLookupTable(self,table):
        #always 100 samples long but samples ignored if value==-75.0
        assert len(table)==100
        self._checkSource()
        cmd = ''
        for j in range(100):
            cmd+='@%da%.2f'%(j,table[j])
        self.SynthHDDevice.sendCommand(cmd)

#     Program a Spot in the AM Lookup Table in dBm (Command @):

# Program Frequency Sweep table? and FM table?

    def getPulseOnTime(self):
        self._checkSource()
        return float(self.SynthHDDevice.sendCommand('P?'))/1e6
    def setPulseOnTime(self,value):
        assert value>=1e-6 and value<=10
        self._checkSource()
        self.SynthHDDevice.sendCommand('P%d'%(value*1e6))

    def getPulseOffTime(self):
        self._checkSource()
        return float(self.SynthHDDevice.sendCommand('O?'))/1e6
    def setPulseOffTime(self,value):
        assert value>=2e-6 and value<=10
        self._checkSource()
        self.SynthHDDevice.sendCommand('O%d'%(value*1e6))

    def getPulseNumberRepetitions(self):
        self._checkSource()
        return float(self.SynthHDDevice.sendCommand('R?'))
    def setPulseNumberRepetitions(self,value):
        assert value>=1 and value<=65500
        self._checkSource()
        self.SynthHDDevice.sendCommand('R%d'%(value))

    def setPulseRunBurst(self):
        self._checkSource()
        self.SynthHDDevice.sendCommand('G')

    def getPulseContinuous(self):
        self._checkSource()
        return int(self.SynthHDDevice.sendCommand('j?'))
    def setPulseContinuous(self,value):
        assert value in [0,1]
        self._checkSource()
        self.SynthHDDevice.sendCommand('j%d'%value)

    def getPulseDualChannelMode(self):
        self._checkSource()
        return int(self.SynthHDDevice.sendCommand('D?'))
    def setPulseDualChannelMode(self):
        assert value in [0,1]
        self._checkSource()
        self.SynthHDDevice.sendCommand('D%d'%value)

    def getFMFrequency(self):
        self._checkSource()
        return int(self.SynthHDDevice.sendCommand('<?'))
    def setFMFrequency(self,value):
        assert value>=1 and value<=5000
        self._checkSource()
        self.SynthHDDevice.sendCommand('<%d'%(value))

    def getFMDeviation(self):
        self._checkSource()
        return int(self.SynthHDDevice.sendCommand('>?'))
    def setFMDeviation(self,value):
        assert abs(value)>=10
        self._checkSource()
        current_freq = self.getFrequency()
        if   current_freq<=106.250e6: assert abs(value)<=160000
        elif current_freq<=212.500e6: assert abs(value)<=312000
        elif current_freq<=425.000e6: assert abs(value)<=625000
        elif current_freq<=850.000e6: assert abs(value)<=1250000
        elif current_freq<=1700.00e6: assert abs(value)<=2500000
        elif current_freq<=3400.00e6: assert abs(value)<=5000000
        elif current_freq<=6800.00e6: assert abs(value)<=10000000
        elif current_freq<=14000.0e6: assert abs(value)<=20000000
        self.SynthHDDevice.sendCommand('>%d'%(value))

    def getFMNumberRepetitions(self):
        self._checkSource()
        return int(self.SynthHDDevice.sendCommand(',?'))
    def setFMNumberRepetitions(self,value):
        self._checkSource()
        self.SynthHDDevice.sendCommand(',%d'%(value))

    def getFMType(self):
        self._checkSource()
        #(sinusoid=1 / chirp=0)
        return int(self.SynthHDDevice.sendCommand(';?'))
    def setFMType(self,value):
        #(sinusoid=1 / chirp=0)
        assert value in [0,1]
        self._checkSource()
        self.SynthHDDevice.sendCommand(';%d'%(value))

    def getFMContinuousMode(self):
        self._checkSource()
        return int(self.SynthHDDevice.sendCommand('/?'))
    def setFMContinuousMode(self,value):
        assert value in [0,1]
        self._checkSource()
        return int(self.SynthHDDevice.sendCommand('/%d'%value))
    
    def getPhaseLockStatus(self):
        #(lock=1 / unlock=0)
        self._checkSource()
        value = self.SynthHDDevice.sendCommand('p')
        return int(value)
