#!/usr/bin/env python
# -*- coding: utf-8 -*-
# The homodyne system for AIG lab
#
# Copyright (C) November, 2018  Becerril, Marcial <mbecerrilt@inaoep.mx>
# Author: Becerril, Marcial <mbecerrilt@inaoep.mx> based in the codes of
# Sam Gordon <sbgordo1@asu.edu>, Sam Rowe and Thomas Gascard.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

#********************************************************************
#*                         CONFIGURATION FILE                       *
#*                           INAOE - MUSCAT                         *
#*                             index.py                             *
#*                        Programa principal                        *
#*                      Marcial Becerril Tapia                      *
#*                   2/octubre/2018 NO SE OLVIDA!                   *
#********************************************************************

import sys
import numpy as np
import yaml

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import *

from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit, QFileDialog
from PyQt5.QtGui import QIcon

# Main Window class
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)

        # Load of main window GUI
        # The GUI was developed in QT Designer
        self.ui = uic.loadUi("./main_config.ui")

        self.gen_cfg = yaml.load(open('./configuration/general_config.cfg','r'))
        self.hdw_cfg = yaml.load(open('./configuration/hardware_config.cfg','r'))
        self.fsy_cfg = yaml.load(open('./configuration/filesys_config.cfg','r'))
        self.lgg_cfg = yaml.load(open('./configuration/logging_config.cfg','r'))
        self.net_cfg = yaml.load(open('./configuration/network_config.cfg','r'))
        self.rch_cfg = yaml.load(open('./configuration/roach_config.cfg','r'))
        self.reg_cfg = yaml.load(open('./configuration/firmware_registers.cfg','r'))

        # General
        self.ui.firmFileEdit.setText(self.gen_cfg["FIRMWARE_FILE"])
        self.ui.ddsEdit.setText(str(self.gen_cfg["dds_shift"]))
        self.ui.centFreqEdit.setText(str(self.gen_cfg["center_freq"]))
        self.ui.loSweepEdit.setText(str(self.gen_cfg["lo_step"]))
        self.ui.nFreqEdit.setText(str(self.gen_cfg["Nfreq"]))
        
        self.ui.maxPosEdit.setText(str(self.gen_cfg["max_pos_freq"]))
        self.ui.minPosEdit.setText(str(self.gen_cfg["min_pos_freq"]))
        self.ui.maxNegEdit.setText(str(self.gen_cfg["max_neg_freq"]))
        self.ui.minNegEdit.setText(str(self.gen_cfg["min_neg_freq"]))
        
        self.ui.offsetEdit.setText(str(self.gen_cfg["symm_offset"]))
        self.ui.testEdit.setText(str(self.gen_cfg["test_freq"]))

        self.ui.bufferEdit.setText(str(self.gen_cfg["buf_size"]))
        self.ui.headerEdit.setText(str(self.gen_cfg["header_len"]))

        # ROACH
        self.ui.maxChanEdit.setText(str(self.rch_cfg["MAXCHANNELS"]))
        self.ui.totLenEdit.setText(str(self.rch_cfg["totallen"]))
        
        self.ui.headStartEdit.setText(str(self.rch_cfg["headerstart"]))
        self.ui.headerLenEdit.setText(str(self.rch_cfg["headerlen"]))
        
        self.ui.dataLenEdit.setText(str(self.rch_cfg["datalen"]))
        self.ui.dataTypeEdit.setText(str(self.rch_cfg["datatype"]))
        self.ui.timTypeEdit.setText(str(self.rch_cfg["timingtype"]))
        self.ui.timEndEdit.setText(str(self.rch_cfg["timingendian"]))
        
        self.ui.packCountEdit.setText(str(self.rch_cfg["PACKETSTRUCT"]["packetcount"]))
        self.ui.fineTimeEdit.setText(str(self.rch_cfg["PACKETSTRUCT"]["coarsetimestamp"]))
        self.ui.packInfoEdit.setText(str(self.rch_cfg["PACKETSTRUCT"]["finetimestamp"]))
        self.ui.coarseTimeEdit.setText(str(self.rch_cfg["PACKETSTRUCT"]["checksum"]))
        self.ui.checksumEdit.setText(str(self.rch_cfg["PACKETSTRUCT"]["packetinfo"]))

        # Logging
        self.ui.lggRootEdit.setText(str(self.lgg_cfg["logrootname"]))

        if self.lgg_cfg["disable_existing_loggers"]:
            self.ui.lggBtn.setText('True')
        else:
            self.ui.lggBtn.setText('False')

        self.ui.lggFileEdit.setText(str(self.lgg_cfg["logfilename"]))
        self.ui.lggformatEdit.setText(str(self.lgg_cfg["formatters"]["simple"]["format"]))

        self.ui.lggRotEdit.setText(str(self.lgg_cfg["logrotatetime"]))
        self.ui.lgghostEdit.setText(str(self.lgg_cfg["serverconfig"]["host"]))
        self.ui.lggPortEdit.setText(str(self.lgg_cfg["serverconfig"]["port"]))

        # Hardware
        self.ui.synthHWEdit.setText(str(self.hdw_cfg["synth1"]["synthmake"]))
        self.ui.synthPortEdit.setText(str(self.hdw_cfg["synth1"]["synthport"]))
        self.ui.synthCommEdit.setText(str(self.hdw_cfg["synth1"]["synth_comm_port"]))        

        # Network
        self.ui.maxChanNwEdit.setText(str(self.net_cfg["MAXCHANNELS"]))
        self.ui.totLenNwEdit.setText(str(self.net_cfg["totallen"]))
        
        self.ui.headStartNwEdit.setText(str(self.net_cfg["headerstart"]))
        self.ui.headerLenNwEdit.setText(str(self.net_cfg["headerlen"]))
        
        self.ui.dataLenNwEdit.setText(str(self.net_cfg["datalen"]))
        self.ui.dataTypeNwEdit.setText(str(self.net_cfg["datatype"]))
        self.ui.timTypeNwEdit.setText(str(self.net_cfg["timingtype"]))
        self.ui.timEndNwEdit.setText(str(self.net_cfg["timingendian"]))
        
        self.ui.packCountNwEdit.setText(str(self.net_cfg["PACKETSTRUCT"]["packetcount"]))
        self.ui.fineTimeNwEdit.setText(str(self.net_cfg["PACKETSTRUCT"]["coarsetimestamp"]))
        self.ui.packInfoNwEdit.setText(str(self.net_cfg["PACKETSTRUCT"]["finetimestamp"]))
        self.ui.coarseTimeNwEdit.setText(str(self.net_cfg["PACKETSTRUCT"]["checksum"]))
        self.ui.checksumNwEdit.setText(str(self.net_cfg["PACKETSTRUCT"]["packetinfo"]))

        # Directories
        self.ui.rootDiryEdit.setText(str(self.fsy_cfg["rootdir"]))
        self.ui.lggFilesEdit.setText(str(self.fsy_cfg["logfiledir"]))
        self.ui.diryPIDEdit.setText(str(self.fsy_cfg["pidfiledir"]))
        self.ui.dirySaveEdit.setText(str(self.fsy_cfg["savedatadir"]))
        self.ui.diryToneListEdit.setText(str(self.fsy_cfg["tonelistdir"]))
        self.ui.diryRamDiskEdit.setText(str(self.fsy_cfg["livefiledir"]))

        # Botones
        self.ui.firmBtn.mousePressEvent = self.chooseFirmPath
        self.ui.rootDiryBtn.mousePressEvent = self.chooseRootPath
        self.ui.logDiryBtn.mousePressEvent = self.chooseLogPath
        self.ui.pidBtn.mousePressEvent = self.choosePIDPath
        self.ui.mainDiryBtn.mousePressEvent = self.chooseMainPath
        self.ui.toneDiryBtn.mousePressEvent = self.chooseTonesPath
        self.ui.RAMDiryBtn.mousePressEvent = self.chooseRAMPath

        self.ui.lggBtn.mousePressEvent = self.is_loggers

        self.ui.gralBtn.mousePressEvent = self.gralFile
        self.ui.roachBtn.mousePressEvent = self.roachFile
        self.ui.logBtn.mousePressEvent = self.logFile
        self.ui.hdwBtn.mousePressEvent = self.hdwFile
        self.ui.netBtn.mousePressEvent = self.netFile
        self.ui.theDiryBtn.mousePressEvent = self.diryFile

        self.ui.numRoachEdit.valueChanged.connect(self.updateNumRoach)
        self.ui.numRoachNwEdit.valueChanged.connect(self.updateNumNwRoach)


        # TODO. Load number of roaches and their parameters
        self.nRoach = 1
        self.numRoach(self.nRoach)

        self.ui.show()

    def updateNumRoach(self, event):
        self.nRoach = self.ui.numRoachEdit.value()
        self.ui.numRoachNwEdit.setValue(self.nRoach)
        self.numRoach(self.nRoach)

    def updateNumNwRoach(self, event):
        self.nRoach = self.ui.numRoachNwEdit.value()
        self.ui.numRoachEdit.setValue(self.nRoach)
        self.numRoach(self.nRoach)

    def disableRoachTabs(self):
        self.ui.roach1.setEnabled(False)  
        self.ui.roach2.setEnabled(False)
        self.ui.roach3.setEnabled(False)
        self.ui.roach4.setEnabled(False)
        self.ui.roach5.setEnabled(False)
        self.ui.roach6.setEnabled(False)

        self.ui.roachN1.setEnabled(False)  
        self.ui.roachN2.setEnabled(False)
        self.ui.roachN3.setEnabled(False)
        self.ui.roachN4.setEnabled(False)
        self.ui.roachN5.setEnabled(False)
        self.ui.roachN6.setEnabled(False)

    def numRoach(self, numRoach):
        
        self.disableRoachTabs()

        for i in range(numRoach):
            if i == 0:
                self.ui.roach1.setEnabled(True)
                self.ui.roachN1.setEnabled(True)
            elif i == 1:
                self.ui.roach2.setEnabled(True)
                self.ui.roachN2.setEnabled(True)
            elif i == 2:
                self.ui.roach3.setEnabled(True)
                self.ui.roachN3.setEnabled(True)
            elif i == 3:
                self.ui.roach4.setEnabled(True)
                self.ui.roachN4.setEnabled(True)
            elif i == 4:
                self.ui.roach5.setEnabled(True)
                self.ui.roachN5.setEnabled(True)
            elif i == 5:
                self.ui.roach6.setEnabled(True)
                self.ui.roachN6.setEnabled(True)

    def gralFile(self, event):
        # General
        self.gen_cfg["FIRMWARE_FILE"] = self.ui.firmFileEdit.text()
        self.gen_cfg["dds_shift"] = self.ui.ddsEdit.text()
        self.gen_cfg["center_freq"] = self.ui.centFreqEdit.text()
        self.gen_cfg["lo_step"] = self.ui.loSweepEdit.text()
        self.gen_cfg["Nfreq"] = self.ui.nFreqEdit.text()
        
        self.gen_cfg["max_pos_freq"] = self.ui.maxPosEdit.text()
        self.gen_cfg["min_pos_freq"] = self.ui.minPosEdit.text()
        self.gen_cfg["max_neg_freq"] = self.ui.maxNegEdit.text()
        self.gen_cfg["min_neg_freq"] = self.ui.minNegEdit.text()
        
        self.gen_cfg["symm_offset"] = self.ui.offsetEdit.text()
        self.gen_cfg["test_freq"] = self.ui.testEdit.text()

        self.gen_cfg["buf_size"] = self.ui.bufferEdit.text()
        self.gen_cfg["header_len"] = self.ui.headerEdit.text()

        with open('general_config.cfg', 'w') as outfile:
            yaml.dump(self.gen_cfg, outfile, default_flow_style=False)

    def roachFile(self, event):
        # ROACH

        self.rch_cfg["MAXCHANNELS"] = self.ui.maxChanEdit.text()
        self.rch_cfg["totallen"] = self.ui.totLenEdit.text()
        
        self.rch_cfg["headerstart"] = self.ui.headStartEdit.text()
        self.rch_cfg["headerlen"] = self.ui.headerLenEdit.text()
        
        self.rch_cfg["datalen"] = self.ui.dataLenEdit.text()
        self.rch_cfg["datatype"] = self.ui.dataTypeEdit.text()
        self.rch_cfg["timingtype"] = self.ui.timTypeEdit.text()
        self.rch_cfg["timingendian"] = self.ui.timEndEdit.text()
        
        self.rch_cfg["PACKETSTRUCT"]["packetcount"] = self.ui.packCountEdit.text()
        self.rch_cfg["PACKETSTRUCT"]["coarsetimestamp"] = self.ui.fineTimeEdit.text()
        self.rch_cfg["PACKETSTRUCT"]["finetimestamp"] = self.ui.packInfoEdit.text()
        self.rch_cfg["PACKETSTRUCT"]["checksum"] = self.ui.coarseTimeEdit.text()
        self.rch_cfg["PACKETSTRUCT"]["packetinfo"] = self.ui.checksumEdit.text()

        with open('roach_config.cfg', 'w') as outfile:
            yaml.dump(self.rch_cfg, outfile, default_flow_style=False)

    def logFile(self, event):
        # Logging
        self.lgg_cfg["logrootname"] = self.ui.lggRootEdit.text()

        self.lgg_cfg["logfilename"] = self.ui.lggFileEdit.text()
        self.lgg_cfg["formatters"]["simple"]["format"] = self.ui.lggformatEdit.text()

        self.lgg_cfg["logrotatetime"] = self.ui.lggRotEdit.text()
        self.lgg_cfg["serverconfig"]["host"] = self.ui.lgghostEdit.text()
        self.lgg_cfg["serverconfig"]["port"] = self.ui.lggPortEdit.text()

        with open('logging_config.cfg', 'w') as outfile:
            yaml.dump(self.lgg_cfg, outfile, default_flow_style=False)

    def hdwFile(self, event):
        # Hardware
        self.hdw_cfg["synth1"]["synthmake"] = self.ui.synthHWEdit.text()
        self.hdw_cfg["synth1"]["synthport"] = self.ui.synthPortEdit.text()
        self.hdw_cfg["synth1"]["synth_comm_port"] = self.ui.synthCommEdit.text()        

        with open('hardware_config.cfg', 'w') as outfile:
            yaml.dump(self.hdw_cfg, outfile, default_flow_style=False)

    def netFile(self, event):
        # Network
        self.net_cfg["MAXCHANNELS"] = self.ui.maxChanNwEdit.text()
        self.net_cfg["totallen"] = self.ui.totLenNwEdit.text()
        
        self.net_cfg["headerstart"] = self.ui.headStartNwEdit.text()
        self.net_cfg["headerlen"] = self.ui.headerLenNwEdit.text()
        
        self.net_cfg["datalen"] = self.ui.dataLenNwEdit.text()
        self.net_cfg["datatype"] = self.ui.dataTypeNwEdit.text()
        self.net_cfg["timingtype"] = self.ui.timTypeNwEdit.text()
        self.net_cfg["timingendian"] = self.ui.timEndNwEdit.text()
        
        self.net_cfg["PACKETSTRUCT"]["packetcount"] = self.ui.packCountNwEdit.text()
        self.net_cfg["PACKETSTRUCT"]["coarsetimestamp"] = self.ui.fineTimeNwEdit.text()
        self.net_cfg["PACKETSTRUCT"]["finetimestamp"] = self.ui.packInfoNwEdit.text()
        self.net_cfg["PACKETSTRUCT"]["checksum"] = self.ui.coarseTimeNwEdit.text()
        self.net_cfg["PACKETSTRUCT"]["packetinfo"] = self.ui.checksumNwEdit.text()

        with open('network_config.cfg', 'w') as outfile:
            yaml.dump(self.net_cfg, outfile, default_flow_style=False)

    def diryFile(self, event):
        # Directory
        self.fsy_cfg["rootdir"] = self.ui.rootDiryEdit.text()
        self.fsy_cfg["logfiledir"] = self.ui.lggFilesEdit.text()
        self.fsy_cfg["pidfiledir"] = self.ui.diryPIDEdit.text()
        self.fsy_cfg["savedatadir"] = self.ui.dirySaveEdit.text()
        self.fsy_cfg["tonelistdir"] = self.ui.diryToneListEdit.text()
        self.fsy_cfg["livefiledir"] = self.ui.diryRamDiskEdit.text()

        with open('filesys_config.cfg', 'w') as outfile:
            yaml.dump(self.fsy_cfg, outfile, default_flow_style=False)

    def is_loggers(self, event):
        if self.ui.lggBtn.isChecked():
            self.ui.lggBtn.setText('False')
            self.lgg_cfg["disable_existing_loggers"] = False 
            self.ui.lggBtn.setChecked(False)
        else:
            self.ui.lggBtn.setText('True')
            self.lgg_cfg["disable_existing_loggers"] = True 
            self.ui.lggBtn.setChecked(True)

    def choosePath(self,flag):
        w = QWidget()
        w.resize(320, 240)
        w.setWindowTitle("Select file")

        if flag == "firm":
            self.firmware = QFileDialog.getOpenFileName(self, "Select File")
            self.ui.firmFileEdit.setText(self.firmware[0])
        elif flag == "root":
            self.root = QFileDialog.getExistingDirectory(self, "Select File")
            self.ui.rootDiryEdit.setText(self.root)
        elif flag == "logg":
            self.logg = QFileDialog.getExistingDirectory(self, "Select File")
            self.ui.lggFilesEdit.setText(self.logg)
        elif flag == "pid":
            self.pid = QFileDialog.getExistingDirectory(self, "Select File")
            self.ui.diryPIDEdit.setText(self.pid)
        elif flag == "main":
            self.mainDiry = QFileDialog.getExistingDirectory(self, "Select File")
            self.ui.dirySaveEdit.setText(self.mainDiry)
        elif flag == "tonelist":
            self.tones = QFileDialog.getExistingDirectory(self, "Select File")
            self.ui.diryToneListEdit.setText(self.tones)
        elif flag == "ram":
            self.ram = QFileDialog.getExistingDirectory(self, "Select File")
            self.ui.diryRamDiskEdit.setText(self.ram)

    def chooseFirmPath(self,event):
        self.choosePath("firm")

    def chooseRootPath(self,event):
        self.choosePath("root")

    def chooseLogPath(self,event):
        self.choosePath("logg")

    def choosePIDPath(self,event):
        self.choosePath("pid")

    def chooseMainPath(self,event):
        self.choosePath("main")

    def chooseTonesPath(self,event):
        self.choosePath("tonelist")

    def chooseRAMPath(self,event):
        self.choosePath("ram")

app = QtWidgets.QApplication(sys.argv)
MyWindow = MainWindow()
sys.exit(app.exec_())
