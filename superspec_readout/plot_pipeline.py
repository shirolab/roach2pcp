# This software provides a console interface to use the functions found in pipeline.py
#
# Copyright (C) 2016  Gordon, Sam <sbgordo1@asu.edu>
# Author: Gordon, Sam <sbgordo1@asu.edu>
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
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import numpy as np
import matplotlib.pyplot as plt
import sys
from build_menu import Console_interface
from blast_pipeline import pipeline
ci = Console_interface()
p = pipeline()

main_prompt = '\n\t\033[35mBLAST-TNG Readout Analysis\033[0m\n\t\033[33mChoose a number from the list and press Enter:\033[0m'                
plot_opts= ['Plot target sweep', 'IQ Loops', 'Multiplot', 'Plot PSD from saved binary data', 'Plot PSD 2', 'Plot on off', 'Plot on off avg all', 'Exit']

while True:
	opt = ci.mk_menu(main_prompt,plot_opts)
	if opt == 0:
		try:
			p.plot_targ(p.targ_path)		
		except KeyboardInterrupt:
			pass
	if opt == 1:
		try:
			chan = input('Channel = ? ')
			p.plot_loop_centered(chan)		
		except KeyboardInterrupt:
			pass
	if opt == 2:
		try:
			chan = input('Channel = ? ')
			p.multiplot(chan)
		except KeyboardInterrupt:
			pass
	if opt == 3:
		try:
			chan = input('Channel = ? ')
			time_interval = input('Time interval (s) ? ')
			p.plotPSD(chan, time_interval)
		except KeyboardInterrupt:
			pass
	if opt == 4:
		try:
			time_interval = input('Time interval (s) ? ')
			p.plotPSD_all_chan(time_interval)
		except KeyboardInterrupt:
			pass
	if opt == 5:
		try:
			chan = input('Channel = ? ')
			p.plot_on_off(chan)
		except KeyboardInterrupt:
			pass
	if opt == 6:
		try:
			p.plot_on_off_avg()
		except KeyboardInterrupt:
			pass
	if opt == 7:
		sys.exit()
