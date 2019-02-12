"""
Colors for messages. Short cuts to color the messages
"""

COLOR_SEQ = "\033[1;%dm"

HEADER    = '\033[95m'
OKBLUE    = '\033[94m'
OKGREEN   = '\033[92m'
WARNING   = '\033[93m'
FAIL      = '\033[91m'
ENDC      = '\033[0m'
BOLD      = '\033[1m'
UNDERLINE = '\033[4m'

BLACKTXT, REDTXT, GREENTXT, YELLOWTXT, BLUETXT, MAGENTATXT, CYANTXT, WHITETXT = [30 + i for i in range(8)]
LOGCOLORS = {
    'WARNING' : YELLOWTXT,
    'INFO'    : WHITETXT,
    'DEBUG'   : CYANTXT,
    'CRITICAL': BLUETXT,
    'ERROR'   : REDTXT }
