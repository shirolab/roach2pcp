# World's simplest python daemon to write current ctime to ROACH
# register, based on https://stackoverflow.com/a/8375012
# Run with $ python timedaemon.py
# Need to make this interface with a config file to choose the
# right ROACH when there is more than one

# import daemon
# import time
# import kidPy
#
# def write_ctime(fpga):
#     while True:
#         fpga.write_int('GbE_ctime',time.time())
#
# def run():
#     with daemon.DaemonContext():
#         fpga = kidPy.getFPGA()
#         write_ctime(fpga)
#
# if __name__ == "__main__":
#     run()
#
#
#
