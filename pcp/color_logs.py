"""
Colors for messages. Short cuts to color the messages
"""

HEADER    = '\033[95m'
OKBLUE    = '\033[94m'
OKGREEN   = '\033[92m'
WARNING   = '\033[93m'
FAIL      = '\033[91m'
BOLD      = '\033[1m'
ENDC      = '\033[0m'

COLOR_SEQ = "\033[1;%dm"
BLACKTXT, REDTXT, GREENTXT, YELLOWTXT, BLUETXT, MAGENTATXT, CYANTXT, WHITETXT = [30 + i for i in range(8)]
LOGCOLORS = {
    'WARNING' : YELLOWTXT,
    'INFO'    : WHITETXT,
    'DEBUG'   : CYANTXT,
    'CRITICAL': BLUETXT,
    'ERROR'   : REDTXT }
