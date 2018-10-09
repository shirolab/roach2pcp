import visa
import numpy as np  
import matplotlib.pyplot as plt
#import time
import sys

SMA100A = dict(zip(['NAME', 'IP', 'freqMin', 'freqMax', 'powMin', 'powMax', 'refMin', 'refMax'],
                   ['R&S_SMA100A', '10.73.4.13', 0.1e6, 3e9, -145, +18, 10e6, 1000e6]))


class rns_sma100a(object):
    def __init__(self,dev=SMA100A,preset=False):
        print("Talking to the synth...")
        self.FREQMIN      = dev['freqMin']
        self.FREQMAX      = dev['freqMax']
        self.POWMIN       = dev['powMin']
        self.POWMAX       = dev['powMax']
        self.REFMIN       = dev['refMin']
        self.REFMAX       = dev['refMax']
        self.dev          = dev
        self.name         = dev['NAME']
        self.ip           = dev['IP']
        self.rm           = visa.ResourceManager("@py")
        self.inst         = self.rm.open_resource("TCPIP::"+self.ip)
        self.inst.timeout = None
        print "*IDN? Query response from %s (%s):\n%s\n"%(self.name, self.ip, self.inst.query("*IDN?"))
        if preset:
            self.preset()
            
    def getFrequency(self):
        return float(self.inst.query('SOURCE:FREQ?'))
    def setFrequency(self,frequency):
        if frequency<self.dev['freqMin']: frequency=self.dev['freqMin']
        if frequency>self.dev['freqMax']: frequency=self.dev['freqMax']
        self.inst.write(':FREQ %.3f'%frequency)
    
    def getPower(self):
        return float(self.inst.query('SOURCE:POWER?'))
    def setPower(self,power):
        if power<self.dev['powMin']: power=self.dev['powMin']
        if power>self.dev['powMax']: power=self.dev['powMax']
        self.inst.write(':POWER %.3f'%power)
    
    def getOutputState(self):
        return self.inst.query('OUTPUT:STATE?')
    def setOutputState(self,state):
        assert state in ['ON','OFF']
        self.inst.write('OUTPUT:STATE %s'%state)

    def setRFOn(self):
        self.inst.write('OUTPUT:STATE ON')
    def setRFOff(self):
        self.inst.write('OUTPUT:STATE OFF')
    
    def getReferenceOscillator(self):
        return self.inst.query(':ROSC:SOURCE?')
    def setReferenceOscillator(self,source):
        if source == 0:
            src = 'EXT'
        else:
            src = 'INT'
        assert src in ['INT','EXT']
        self.inst.write(':ROSC:SOURCE %s'%src)

    def getReferenceOscillatorExtFreq(self):
        return str(self.inst.query(':ROSC:EXT:FREQ?')).split()[0]
    def setReferenceOscillatorExtFreq(self,frequency):
        assert frequency in [5e6,10e6,13e6]
        self.inst.write(':ROSC:EXT:FREQ %s'%frequency)


    
    def RST(self):
        self.inst.write('*RST')
        
    def CLS(self):
        self.inst.write('*CLS')
        
    def WAI(self):
        self.inst.write('*WAI')

    def preset(self):
        self.CLS()
        self.RST()
