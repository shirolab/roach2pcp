import visa
import numpy as np  
import matplotlib.pyplot as plt
#import time
import sys


SGS100A = dict(zip(['NAME',       'ADDR',        'freqMin', 'freqMax', 'powMin', 'powMax', 'refMin', 'refMax'],
                   ['R&S_SGS100A','TCPIP::10.73.4.13', 1e6,       12e9,        -120,    +25,    10e6,     1000e6]))
SGS100A_USB = dict(zip(['NAME',       'ADDR',        'freqMin', 'freqMax', 'powMin', 'powMax', 'refMin', 'refMax'],
                   ['R&S_SGS100A','USB0::0x0AAD::0x0088::103424::INSTR', 1e6,       12e9,        -120,    +25,    10e6,     1000e6]))
class rns_sgs100a(object):
    def __init__(self,dev=SGS100A_USB,preset=False):
        print "Talking to the synth..."
        self.FREQMIN      = self.SGS100A['freqMin']
        self.FREQMAX      = self.SGS100A['freqMax']
        self.POWMIN       = self.SGS100A['powMin']
        self.POWMAX       = self.SGS100A['powMax']
        self.REFMIN       = self.SGS100A['refMin']
        self.REFMAX       = self.SGS100A['refMin']
        self.dev          = dev
        self.name         = self.dev['NAME']
        self.addr           = self.dev['ADDR']
        self.rm           = visa.ResourceManager("@py")
        self.inst         = self.rm.open_resource(self.addr)
        self.inst.timeout = None
        print "*IDN? Query response from %s (%s):\n%s\n"%(self.name, self.addr, self.inst.query("*IDN?"))
        if preset:
            self.preset()
            
    def getFrequency(self):
        return self.inst.query('SOURCE:FREQ?')
    def setFrequency(self,frequency):
        if frequency<self.dev['freqMin']: frequency=self.dev['freqMin']
        if frequency>self.dev['freqMax']: frequency=self.dev['freqMax']
        self.inst.write(':FREQ %.3f'%frequency)
    
    def getPower(self):
        return self.inst.query('SOURCE:POWER?')
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
        return self.inst.query(':ROSC:EXT:FREQ?')
    def setReferenceOscillatorExtFreq(self,frequency):
        assert frequency in [10e6,13e6,100e6,1000e6]
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
