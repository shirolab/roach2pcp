import random
import time

try:
    while True:
        f = open('./test_timestream.txt','a')
        f.write(str(time.time()) + ', ' + str(random.randint(0,9)) + ', ' + str(random.gauss(0,1)))
        f.write('\n')
        time.sleep(0.1)
        f.close()
except KeyboardInterrupt:
    pass

        