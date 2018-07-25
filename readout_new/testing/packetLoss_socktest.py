import socket
import numpy as np
import matplotlib.pyplot as plt

if __name__ == "__main__":
    s = socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(3))
    s.bind(("enp3s0",3))
    buf_size = 8192 + 42

    counts = []

    while True:
        p = s.recv(buf_size)
        if (len(p)!=buf_size) or (socket.inet_ntoa(np.fromstring(p[26:30],dtype="<I")) != '192.168.40.71'):
            print 'non roach packet'
            pass
        else:
            counts.append(np.fromstring(p[-9:-5],dtype = ">I")[0])


            

