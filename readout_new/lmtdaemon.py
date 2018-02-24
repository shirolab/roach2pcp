# World's simplest python daemon to listen on some port for
# TCP text commands from LMT TCS
# based on https://stackoverflow.com/a/8375012 and
# https://wiki.python.org/moin/TcpCommunication
#
# Run with $ python lmtdaemon.py
#
# To write e.g. an integer to the GbE_packet_info register
# over TCP, in another Python window...
# import socket
# TCP_IP = '127.0.0.1'
# TCP_PORT = 5005
# BUFFER_SIZE = 1024
# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# s.connect((TCP_IP, TCP_PORT))
# s.send('1001') # the integer I want to write
# s.close()
#
# Need to have this interface with config file for external
# (i.e. LMT) IPs, exit gracefully...

import daemon
import kidPy
import socket

def write_packetinfo(fpga,thingtowrite):
    fpga.write_int('GbE_packet_info',int(thingtowrite))

def run():
    with daemon.DaemonContext():
        fpga = kidPy.getFPGA()
        TCP_IP = '127.0.0.1'
        TCP_PORT = 5005
        BUFFER_SIZE = 20
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((TCP_IP, TCP_PORT))
        s.listen(1)
        
        conn, addr = s.accept()
        while 1:
            thingtowrite = conn.recv(BUFFER_SIZE)
            if not thingtowrite: break
            write_packetinfo(fpga,thingtowrite)

if __name__ == "__main__":
    run()

