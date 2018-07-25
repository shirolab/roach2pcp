import serial
import serial.tools.list_ports
from time import sleep

dev_snrs    = ['001102']
hwid_snrs = ['0403:6015']
#hwid_snrs = ['FTDIBUS\\VID_0403+PID_6015+6&14CF9D57&0&3\\0000']

class atlantech_asg3000u(object):
    def __init__(self, dev_snr=dev_snrs[0], open_connection=True, baud=115200):
        print 'Connecting to ASG-3000-U Synthesiser...'
        self.bauds_available = [9600,19200,38400,57600,115200]
        if baud not in self.bauds_available:
            raise StandardError, 'Requested baud rate not supported'
        self.serialNumber = dev_snr
        self.FREQMIN    = 25e6
        self.FREQMAX    = 3e9
        self.POWMIN     = -27.0
        self.POWMAX     = +13.0
        self.REFMIN     = 10e6
        self.REFMAX     = 75e9
        self.statRFON   = None
        self.statPWRCMD = None
        self.statLOCK   = None
        self.statREFOUT = None
        self.statFREQ   = None
        self.statPOW    = None
        self.serialPort           = self._findSerialPort()
        self.baud_requested       = baud
        self.conn                 = serial.Serial(None, baudrate=baud,timeout=0.1)
        self.conn.setPort(self.serialPort)
        if open_connection:
            self.conn.open()
        self.status=u''
        print 'OK :)'
        
    def _findSerialPort(self):
        comports = serial.tools.list_ports.comports()
        for port, desc, hwid in comports:
            print  port, desc, hwid
            if hwid.find(hwid_snrs[dev_snrs.index(self.serialNumber)])>=0:
                return port
        raise ValueError, "Not found"
        return None    
    
    
    def set_local_baud_auto(self):
        for baud in self.bauds_available:
            print 'trying %d baud...'%baud, ;sys.stdout.flush()
            self.conn.setBaudrate(baud)
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
            self.conn.setBaudrate(self.baud_requested)
            print 'Now using %d baud'%self.conn.getBaudrate()
            self.clearSerialBuffer()
        self.s1 = ASGSource()
    
    def close_connection(self):
        self.conn.close()
        
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
    
    def sendCommand(self,command,clearbuf=True):
        if clearbuf: self.clearSerialBuffer()
        self.conn.write(command+'\r')
        readlines = self.conn.readlines()
        print unicode(''.join(readlines),encoding='latin-1')
        
        messageFound = False
        for line in readlines:
            if line.strip().find(command)>=0:
                messageFound=True
                readlines.pop(readlines.index(line))
                break
        if not messageFound:
            raise StandardError, 'received invalid message'
        prompt  = readlines.pop(-1)
                
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
    
    def getBaud(self,qflag=False):
        cmd='baud'
        if qflag:
            cmd+=' /q'
        return self.sendCommand(cmd)
    
    def setBaud(self,baud,qflag=False):
        assert baud in self.bauds_available
        cmd='baud'
        if qflag:
            cmd+=' /q'
        cmd+=' %s'%baud
        return self.sendCommand(cmd)
    
    def getFrequency(self,qflag=False,lflag=False):
        cmd='fr'
        if qflag:
            cmd+=' /q'
        if lflag:
            cmd+=' /l'
        return self.sendCommand(cmd)
        
    def setFrequency(self,freq,qflag=False,nflag=False):
        assert freq>=self.FREQMIN, 'Freq too low'
        assert freq<=self.FREQMAX, 'Freq too high'
        cmd='fr'
        if qflag:
            cmd+=' /q'
        if nflag:
            cmd+=' /n'
        cmd+=' %.6f'%(freq/1e6)
        return self.sendCommand(cmd)
    
    def setFrequencyFastest(self,freq,dwell=0.05):
        assert freq>=self.FREQMIN, 'Freq too low'
        assert freq<=self.FREQMAX, 'Freq too high'
        self.conn.write('fr /n /q %.6f \r'%(freq/1e6))
        sleep(dwell)
        
    def setFrequencyFaster(self,freq,dwell=0.05):
        assert freq>=self.FREQMIN, 'Freq too low'
        assert freq<=self.FREQMAX, 'Freq too high'
        self.conn.write('fr /n %.6f \r'%(freq/1e6))
        sleep(dwell)
        
    def setFrequencyFast(self,freq,dwell=0.05):
        assert freq>=self.FREQMIN, 'Freq too low'
        assert freq<=self.FREQMAX, 'Freq too high'
        self.conn.write('fr %.6f \r'%(freq/1e6))
        sleep(dwell)
        
    def getHelp(self,qflag=False):
        cmd='help'
        if qflag:
            cmd+=' /q'
        return self.sendCommand(cmd)

    def identify(self):
        return self.sendCommand('id')
        
    def getName(self,qflag=False):
        cmd='name'
        if qflag:
            cmd+=' /q'
        return self.sendCommand(cmd)
    
    def setName(self,name,qflag=False):
        assert (len(name)>=1) and (len(name)<=32)
        cmd='name'
        if qflag:
            cmd+=' /q'
        cmd+=' %s'%name
        return self.sendCommand(cmd)
    
    def getOutput(self,output,qflag=False):
        cmd='output'
        if qflag:
            cmd+=' /q'
        return self.sendCommand(cmd)
    
    def setOutput(self,output,qflag=False,nflag=False):
        assert output in ['on','off','trig']
        cmd='output'
        if qflag:
            cmd+=' /q'
        if nflag:
            cmd+=' /n'
        cmd+=' '+output
        return self.sendCommand(cmd)
    
    def getPower(self,qflag=False,lflag=False):
        cmd='power'
        if qflag:
            cmd+=' /q'
        if lflag:
            cmd+=' /l'
        return self.sendCommand(cmd)
    
    def setPower(self,power,qflag=False,nflag=False):
        assert power>=self.POWMIN, 'power too low'
        assert power<=self.POWMAX, 'power too high'
        cmd = 'power'
        if qflag:
            cmd+=' /q'
        if nflag:
            cmd+=' /n'
        cmd+=' %+.1f'%(power)
        return self.sendCommand(cmd)
    
    def getReference(self,qflag=False,lflag=False):
        cmd='reference'
        if qflag:
            cmd+=' /q'
        if lflag:
            cmd+=' /l'        
        return float(self.sendCommand(cmd).split(",")[1][:-1])
        # int(self.sendCommand('refs?').split()[1][:-1])
    
    def setReference(self,int_ext,reffreq=40e6,qflag=False):
        if int_ext == 0:
            src = 'ext'
        else:
            src = 'int'
        assert src in ['int','ext']
        assert (reffreq > self.REFMIN) and (reffreq < self.REFMAX)
        if (src == 'int'):
            assert reffreq==40e6
        cmd='reference'
        if qflag:
            cmd+=' /q'
        cmd+= ' %s'%src
        cmd+= ' %.6f'%(reffreq/1e6)
        return self.sendCommand(cmd)
    
    def getSerial(self,qflag=False):
        cmd='serial'
        if qflag:
            cmd+=' /q'
        ret = self.sendCommand(cmd)
        self.serial=ret
        return ret

    def getStatus(self,qflag=False):
        cmd='status'
        if qflag:
            cmd+=' /q'
        statRFON,statPWRCMD,statLOCK,statREFOUT,statFREQ,statPOW = self.sendCommand(cmd).split(',')
        self.statRFON   = True if statRFON   == 'H' else False
        self.statPWRCMD = True if statPWRCMD == 'H' else False
        self.statLOCK   = True if statLOCK   == 'H' else False
        self.statREFOUT = True if statREFOUT == 'H' else False
        self.statFREQ   = float(statFREQ)*1e6
        self.statPOW    = float(statPOW)
        return     self.statRFON,self.statPWRCMD,self.statLOCK,self.statREFOUT,self.statFREQ,self.statPOW
    def setSweep(self):
        pass

    def getVersion(self,qflag=False):
        cmd='version'
        if qflag:
            cmd+=' /q'
        ret = self.sendCommand(cmd)
        self.firmwareVersion = ret
        return ret

    def getVoltage(self,qflag=False):
        cmd='voltage'
        if qflag:
            cmd+=' /q'
        ret = self.sendCommand(cmd)
        self.voltage = float(ret)
        return ret
        
        
        
        
        
        
    
    

    