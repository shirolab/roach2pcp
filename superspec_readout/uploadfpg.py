import numpy as np
import casperfpga
import sys 
import time 
import utils

bitstream = sys.argv[1]
config = utils.read_config()
#ip = "192.168.40.64"
ip = config['roach_ip']

def openClient():
	print 'Connecting...'
	katcp_port=7147
	roach = casperfpga.katcp_fpga.KatcpFpga(ip,timeout=120.)
	
	t1 = time.time()
	timeout = 10
	while not roach.is_connected():
	    if (time.time()-t1) > timeout:
		raise Exception("Connection timeout to roach")
	time.sleep(0.1)
	if (roach.is_connected() == True):
	    print 'Connected to the FPGA '
	    roach.upload_to_ram_and_program(str(bitstream))
	else:
	    print 'Not connected to the FPGA'
	time.sleep(2)
	print 'Connection established to', ip
	print 'Uploaded',bitstream

openClient()
