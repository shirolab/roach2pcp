import random
import time
import struct
import pygetdata as gd

def write_ascii(filename = 'test_timestream'):
    try:
        while True:
            f = open(str(filename + '1.txt'),'a')
            f.write(str(time.time()) + ', '
                    + str(random.randint(0,9)) + ', '
                    + str(random.gauss(0,1)))
            f.write('\n')
            time.sleep(0.1)
            f.close()
            
            f = open(str(filename + '2.txt'),'a')
            f.write(str(time.time()) + ', '
                    + str(random.randint(10,19)) + ', '
                    + str(random.gauss(3,1)))
            f.write('\n')
            time.sleep(0.1)
            f.close()
            
    except KeyboardInterrupt:
        pass

# Jankily taken from Sam Gordon (roachInterface.py)
def write_dirfile(filename = 'test_dirfile',nchannel = 3, ntime = 100):
    channels = range(nchannel)
    # Create dirfile
    d = gd.dirfile(filename,gd.CREAT|gd.RDWR|gd.UNENCODED)
    # Write format file
    fields = []
    for chan in range(nchannel):
        fields.append('chP_' + str(chan))
        d.add_spec('chP_' + str(chan) + ' RAW FLOAT64 1')
    d.add_spec('time RAW FLOAT64 1')
    d.close()
    
    # Open it again to start writing
    d = gd.dirfile(filename,gd.RDWR|gd.UNENCODED)
    nfo_phase = map(lambda z: filename + "/chP_" + str(z),
                    range(nchannel))
    # "ab" = 'append','binary'
    fo_phase = map(lambda z: open(z, "ab"), nfo_phase)
    fo_time = open(filename + "/time", "ab")

    count = 0
    while count < ntime:
        for chan in channels:
            ts = time.time()
            fo_phase[chan].write(struct.pack('d',random.gauss(3,1)))
            fo_phase[chan].flush()
        count += 1
        fo_time.write(struct.pack('d',ts))
        fo_time.flush()
        time.sleep(0.1)
    for chan in channels:
        fo_phase[chan].close()
    fo_time.close()
    d.close()

    return

    

    
        
