#!/usr/bin/env python
# 20180510 - PB




# test this code to extract INFO to pass to stop_loggin_daemon


# def start_logging_daemon():
#     global INFO
#
#     # read startup information from logger
#     info = []
#     while True:
#         r, _, _ = _select.select([subp.stdout], [], [], 1)
#         if r:
#             info.append(r[0].readline())
#         else:
#             break
#
#     subp.poll() # kills zombie process left behind
#
#     INFO = {item.split(':')[0] : item.split(':')[1] for item in info}
#
