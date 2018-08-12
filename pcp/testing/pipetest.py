import sys, time


while True:
    time.sleep(1)
    try:
        sys.stdout.write("testing")
    except KeyboardInterrupt:
        break
