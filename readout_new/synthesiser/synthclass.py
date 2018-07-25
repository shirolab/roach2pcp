# Copyright (C) 2018 Cardiff University, Physics department, AIG
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# Developers: Dr Samuel Rowe, Mr Thomas Gascard
# Cardiff University, School of Physics and Astrophysics, AIG
# Version 0.4, 29.03.2018

# Objective: This is a library of embed functions to set up a variety of synthesizer's parameters.
# 
# Context: This set of programs are set in the context of the MUSCAT experiment (http://muscat.astro.cf.ac.uk/).
# During the readout prototyping process, it appeared useful to perform a compared analysis on the following synthesizers:
# R&S SMA100A, R&S SGS100A, Valon 5008, Valon 5009, Windfreak SyntHD, AtlanTech ASG3000u.
# The R&S SMA 100A being a high quality system, it has been chosen as a reference to which the other systems are to be compared.
#
# ________________________________________________________________________________________________


# == PREREQUISITE ==
# -- Python and third part modules -- 
import rns_sma100a, rns_sgs100a, valon5008, valon5009, windfreak_synthd, atlantech_asg3000u

# - Parameters dictionaries -
rns_sma100a_dict = dict(zip(['CLASSDEF', 'NAME', 'ADDR', 'freqMin', 'freqMax', 'powMin', 'powMax'], [rns_sma100a.rns_sma100a, 'R&S SMA100A', '10.73.4.13', 9e3, 3e9, -145, +18]))

rns_sgs100a_dict = dict(zip(['CLASSDEF', 'NAME', 'ADDR', 'freqMin', 'freqMax', 'powMin', 'powMax'], [rns_sgs100a.rns_sgs100a, 'R&S SGS100A', 'TCPIP::10.73.4.13', 1e6, 12e9, -120, +25]))
rns_sgs100a_usb_dict = dict(zip(['CLASSDEF', 'NAME', 'ADDR', 'freqMin', 'freqMax', 'powMin', 'powMax'], [rns_sgs100a.rns_sgs100a, 'R&S SGS100A','USB0::0x0AAD::0x0088::103424::INSTR', 1e6, 12e9, -120, +25]))

valon5008ch1_dict = dict(zip(['CLASSDEF', 'NAME', 'hwid_snrs', 'dev_snrs'], [valon5008.valon5008, 'Valon 5008 (channel 1)', 'AM01H05BA', 'whaterver']))
valon5008ch2_dict = dict(zip(['CLASSDEF', 'NAME', 'hwid_snrs', 'dev_snrs'], [valon5008.valon5008, 'Valon 5008 (channel 2)', 'AM01H05BA', 'whaterver']))

valon5009ch1_dict = dict(zip(['CLASSDEF', 'NAME', 'hwid_snrs', 'dev_snrs'], [valon5009.valon5009, 'Valon 5009 (channel 1)', 'A59JJN5', 'A9040DX6']))
valon5009ch2_dict = dict(zip(['CLASSDEF', 'NAME', 'hwid_snrs', 'dev_snrs'], [valon5009.valon5009, 'Valon 5009 (channel 2)', 'A59JJN5', 'A9040DX6']))

windfreak_synthd_dict = dict(zip(['CLASSDEF', 'NAME', 'hwid_snrs', 'dev_snrs'], [windfreak_synthd.windfreak_synthd, 'Windfreak SyntHD', '4294967295', '656']))

atlantech_asg3000u_dict = dict(zip(['CLASSDEF', 'NAME', 'hwid_snrs', 'dev_snrs'], [atlantech_asg3000u.atlantech_asg3000u, 'AtlanTech ASG3000u', '0403:6015', '001102']))

# -- Synthesizer switch dictionary --
# Dictionary definition
synth_dict = {"SMA100A" : rns_sma100a_dict,
              "SGS100A" : rns_sgs100a_dict, 
              "VALON5008ch1" : valon5008ch1_dict, 
              "VALON5008ch2" : valon5008ch2_dict, 
              "VALON5009ch1" : valon5009ch1_dict, 
              "VALON5009ch2" : valon5009ch2_dict, 
              "WINDFREAK" : windfreak_synthd_dict, 
              "ASG3000U" : atlantech_asg3000u_dict}
              
# == SYNTHESIZER CLASS DEFINITION ==
class Synthesizer(object):

    # -- Synthesizer Initialisation functiuon --
    def __init__(self, synth_name):
        if synth_name not in(synth_dict.keys()):
            print "Synthesizer name is unknown: ", synth_name
            return None
        self.sd = synth_dict[synth_name] 
        
        if self.sd['NAME'] == 'R&S SMA100A' : self.synth = self.sd['CLASSDEF']()
        elif self.sd['NAME'] == 'R&S SGS100A' : self.synth = self.sd['CLASSDEF'](self.sd)
        elif self.sd['NAME'] == 'Valon 5008 (channel 1)' or self.sd['NAME'] == 'Valon 5008 (channel 2)' : self.synth = self.sd['CLASSDEF'](self.sd['dev_snrs'])
        elif self.sd['NAME'] == 'Valon 5009 (channel 1)' or self.sd['NAME'] == 'Valon 5009 (channel 2)' : self.synth = self.sd['CLASSDEF'](self.sd['dev_snrs'])
        elif self.sd['NAME'] == 'Windfreak SyntHD' : self.synth = self.sd['CLASSDEF'](self.sd['dev_snrs'])
        elif self.sd['NAME'] == 'AtlanTech ASG3000u' : self.synth = self.sd['CLASSDEF'](self.sd['dev_snrs'])
    
    # -- Reference related functions --
    def getReferenceFreq(self):
        if self.sd['NAME'] == 'R&S SMA100A' : return self.synth.getReferenceOscillatorExtFreq()
        elif self.sd['NAME'] == 'R&S SGS100A' : return self.synth.getReferenceOscillatorExtFreq()
        elif self.sd['NAME'] == 'Valon 5008 (channel 1)' or self.sd['NAME'] == 'Valon 5008 (channel 2)' : return self.synth.get_reference()
        elif self.sd['NAME'] == 'Valon 5009 (channel 1)' or self.sd['NAME'] == 'Valon 5009 (channel 2)' : return self.synth.referenceFrequency
        elif self.sd['NAME'] == 'Windfreak SyntHD' : return self.synth.getPLLReferenceFrequency()
        elif self.sd['NAME'] == 'AtlanTech ASG3000u' : return self.synth.getReference()
        
    def setReferenceFreq(self, freq):
        if self.sd['NAME'] == 'R&S SMA100A' : self.synth.setReferenceOscillatorExtFreq(freq)
        elif self.sd['NAME'] == 'R&S SGS100A' : self.synth.setReferenceOscillatorExtFreq(freq)
        elif self.sd['NAME'] == 'Valon 5008 (channel 1)' or self.sd['NAME'] == 'Valon 5008 (channel 2)' : self.synth.set_reference(freq/1e6) # This function need freq in MHz
        elif self.sd['NAME'] == 'Valon 5009 (channel 1)' or self.sd['NAME'] == 'Valon 5009 (channel 2)' : self.synth.referenceFrequency = freq
        elif self.sd['NAME'] == 'Windfreak SyntHD' : self.synth.setPLLReferenceFrequency(freq)
        elif self.sd['NAME'] == 'AtlanTech ASG3000u' : 
            self.synth.setReference()
            print "Internal reference is fixed at 40 MHz."
            
    def getReferenceSelect(self):
        if self.sd['NAME'] == 'R&S SMA100A' : return self.synth.getReferenceOscillator()
        elif self.sd['NAME'] == 'R&S SGS100A' : return self.synth.getReferenceOscillator()
        elif self.sd['NAME'] == 'Valon 5008 (channel 1)' or self.sd['NAME'] == 'Valon 5008 (channel 2)' : return self.synth.get_ref_select()
        elif self.sd['NAME'] == 'Valon 5009 (channel 1)' or self.sd['NAME'] == 'Valon 5009 (channel 2)' : return self.synth.referenceSource
        elif self.sd['NAME'] == 'Windfreak SyntHD' : return self.synth.getReferenceSelect()
        elif self.sd['NAME'] == 'AtlanTech ASG3000u' : return self.synth.getReference()
        
    def setReferenceSelect(self, source):
        print("Source is defined as follow:\n"
            "0 - External\n"
            "1 - Internal")
        if self.sd['NAME'] == 'R&S SMA100A' : self.synth.setReferenceOscillator(source)
        elif self.sd['NAME'] == 'R&S SGS100A' : self.synth.setReferenceOscillator(source)
        elif self.sd['NAME'] == 'Valon 5008 (channel 1)' or self.sd['NAME'] == 'Valon 5008 (channel 2)' : self.synth.set_ref_select(source)
        elif self.sd['NAME'] == 'Valon 5009 (channel 1)' or self.sd['NAME'] == 'Valon 5009 (channel 2)' : self.synth.referenceSource = source
        elif self.sd['NAME'] == 'Windfreak SyntHD' : 
            print("0 - External \n"
                    "Internal source can be:\n"
                    "1 - 27MHz\n"
                    "2 - 10MHz")
            self.synth.setReferenceSelect(source)
        elif self.sd['NAME'] == 'AtlanTech ASG3000u' : self.synth.setReference(source)
        
    # -- Source(s) functions --
    def getFrequency(self):
        if self.sd['NAME'] == 'R&S SMA100A' : return self.synth.getFrequency()
        elif self.sd['NAME'] == 'R&S SGS100A' : return self.synth.getFrequency()
        elif self.sd['NAME'] == 'Valon 5008 (channel 1)' : return self.synth.get_frequency_a()
        elif self.sd['NAME'] == 'Valon 5008 (channel 2)' : return self.synth.get_frequency_b()
        elif self.sd['NAME'] == 'Valon 5009 (channel 1)' : return self.synth.s1.frequency
        elif self.sd['NAME'] == 'Valon 5009 (channel 2)' : return self.synth.s2.frequency
        elif self.sd['NAME'] == 'Windfreak SyntHD' : return self.synth.getFrequency()
        elif self.sd['NAME'] == 'AtlanTech ASG3000u' : return self.synth.getFrequency()
    
    def setFrequency(self, freq):
        if self.sd['NAME'] == 'R&S SMA100A' : self.synth.setFrequency(freq)
        elif self.sd['NAME'] == 'R&S SGS100A' : self.synth.setFrequency(freq)
        elif self.sd['NAME'] == 'Valon 5008 (channel 1)' : self.synth.set_frequency_a(freq)
        elif self.sd['NAME'] == 'Valon 5008 (channel 2)' : self.synth.set_frequency_b(freq)
        elif self.sd['NAME'] == 'Valon 5009 (channel 1)' : self.synth.s1.frequency = freq
        elif self.sd['NAME'] == 'Valon 5009 (channel 2)' : self.synth.s2.frequency = freq
        elif self.sd['NAME'] == 'Windfreak SyntHD' : self.synth.setFrequency(freq)
        elif self.sd['NAME'] == 'AtlanTech ASG3000u' : self.synth.setFrequency(freq)
            
    # -- Power related functions --        
    def getPower(self):
        if self.sd['NAME'] == 'R&S SMA100A' : return self.synth.getPower()
        elif self.sd['NAME'] == 'R&S SGS100A' : return self.synth.getPower()
        elif self.sd['NAME'] == 'Valon 5008 (channel 1)' : return self.synth.get_rf_level_a()
        elif self.sd['NAME'] == 'Valon 5008 (channel 2)' : return self.synth.get_rf_level_b()
        elif self.sd['NAME'] == 'Valon 5009 (channel 1)' : return self.synth.s1.powerLevel
        elif self.sd['NAME'] == 'Valon 5009 (channel 2)' : return self.synth.s2.powerLevel
        elif self.sd['NAME'] == 'Windfreak SyntHD' : return self.synth.getPower()
        elif self.sd['NAME'] == 'AtlanTech ASG3000u' : return self.synth.getPLLPower()
        
    def setPower(self, power):
        if self.sd['NAME'] == 'R&S SMA100A' : self.synth.setPower(power)
        elif self.sd['NAME'] == 'R&S SGS100A' : self.synth.setPower(power)
        elif self.sd['NAME'] == 'Valon 5008 (channel 1)' : self.synth.set_rf_level_a(power)
        elif self.sd['NAME'] == 'Valon 5008 (channel 2)' : self.synth.set_rf_level_b(power)
        elif self.sd['NAME'] == 'Valon 5009 (channel 1)' : self.synth.s1.powerLevel = power
        elif self.sd['NAME'] == 'Valon 5009 (channel 2)' : self.synth.s2.powerLevel = power
        elif self.sd['NAME'] == 'Windfreak SyntHD' : self.synth.setPower(power)
        elif self.sd['NAME'] == 'AtlanTech ASG3000u' : self.synth.setPLLPower(power)

