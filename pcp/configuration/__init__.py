"""
Read the config files and return the object for importing by other modules. This script is called
when the "configuration" submodule is imported, and will load all the configuration files. Different
parts of the application can call individual configurations as required by using
'from configuration import <NAME>_config.'
"""

# import configurations here (might be able to do this dynamically using importlib and inspect for variables)
import lib_config
# from .lib_config import config_dir, general_config, filesys_config, logging_config, \
#                         network_config, roach_config, hardware_config, firmware_registers
#
# from .lib_config import reload_configfiles, verify_config_consistency
#
# _logger = _logging.getLogger(__name__)
# # define some constants for convenience
# ROOTDIR = filesys_config['rootdir']
#
# FIRMWAREDIR = filesys_config['firmwaredir'] if _os.path.isabs(filesys_config['firmwaredir']) \
#                                             else _os.path.join(ROOTDIR, filesys_config['firmwaredir'])
# SAVEDATADIR = filesys_config['savedatadir'] if _os.path.isabs(filesys_config['savedatadir']) \
#                                             else _os.path.join(ROOTDIR, filesys_config['savedatadir'])
# TONELISTDIR = filesys_config['tonelistdir'] if _os.path.isabs(filesys_config['tonelistdir']) \
#                                             else _os.path.join(ROOTDIR, filesys_config['tonelistdir'])
# TONEHISTDIR = filesys_config['tonehistdir'] if _os.path.isabs(filesys_config['tonehistdir']) \
#                                             else _os.path.join(ROOTDIR, filesys_config['tonehistdir'])
# AMPCORRDIR  = filesys_config['ampcorrdir'] if _os.path.isabs(filesys_config['ampcorrdir']) \
#                                             else _os.path.join(ROOTDIR, filesys_config['ampcorrdir'])
# PIDFILEDIR  = filesys_config['pidfiledir'] if _os.path.isabs(filesys_config['pidfiledir']) \
#                                             else _os.path.join(ROOTDIR, filesys_config['pidfiledir'])
# LIVEFILEDIR = filesys_config['livefiledir'] if _os.path.isabs(filesys_config['livefiledir']) \
#                                             else _os.path.join(ROOTDIR, filesys_config['livefiledir'])
# LOGFILEDIR  = logging_config['logfiledir'] if _os.path.isabs(logging_config['logfiledir']) \
#                                             else _os.path.join(ROOTDIR, logging_config['logfiledir'])
#
# # set up file system according to the configuration files - no checks on permissions...
# if not _os.path.exists(ROOTDIR)    : _os.makedirs(ROOTDIR)
# if not _os.path.exists(PIDFILEDIR) : _os.makedirs(PIDFILEDIR)
# if not _os.path.exists(LOGFILEDIR) : _os.makedirs(LOGFILEDIR)
# if not _os.path.exists(SAVEDATADIR): _os.makedirs(SAVEDATADIR)
# if not _os.path.exists(TONELISTDIR): _os.makedirs(TONELISTDIR)
# if not _os.path.exists(TONEHISTDIR): _os.makedirs(TONEHISTDIR)
# if not _os.path.exists(AMPCORRDIR) : _os.makedirs(AMPCORRDIR)
# if not _os.path.exists(LIVEFILEDIR): _os.makedirs(LIVEFILEDIR)
#
# # create a dictionary that contains the firmware regsiters for each roachid
# FIRMWARE_REG_DICT = {}
# for roachid in roach_config.keys():
#     FIRMWARE_REG_DICT[roachid] = _lib_config.get_firmware_register_dict(firmware_registers, roach_config[roachid]["firmware_file"]) ["registers"]
#
# # if the firmware directory doesn't exist already, there will likely be a problem, so raise an exception
# # (this should be moved to the filesys consistency checking code )
#
# if not _os.path.exists(FIRMWAREDIR):
#     raise OSError("Firmware directory doesn't exist. Please point to a valid directory ")
# elif not any( map(lambda x: _os.path.splitext(x)[-1]=='.fpg', _os.listdir(FIRMWAREDIR) ) ):
#     raise AttributeError("Firmware directory doesn't appear to contain any .fpg files. Please point to a valid directory ")
#
#
# # set system limits on num open files, send and revice buffer lengths
# try:
#     _os.system("sysctl -w fs.file-max=100000 ")
#     _logger.info("changed max number of open files to 10k")
#     print "changed max number of open files to 10k"
# except:
#     _logger.warning("couldn't change the max number of files. ")
#     print "couldn't change the max number of files. "
#
# # set system limits udp receive buffer length (only required for raw sockets (not used any more))
# try:
#     _os.system("sysctl -w net.core.rmem_max='88104 117473 176208' ")
#     _logger.info("changed RCVBUF default to 117473")
#     print "changed RCVBUF default to 117473"
#
# except:
#     _logger.warning("couldn't change default RCVBUF")
#     print "couldn't change default RCVBUF"
#
# # set system limits send buffer lengths (required for faster tone writing )
# try:
#     _os.system("sysctl -w net.ipv4.tcp_wmem='4096 16777216 16777216'")
#     _os.system("sysctl -w net.core.wmem_max=16777216")
#
#     _logger.info("changed SNDBUF default to 2**24 = 16777216")
#     print "changed SNDBUF default to 2**24 = 16777216"
# except:
#     _logger.warning("couldn't change default RCVBUF")
#     print "couldn't change default RCVBUF"
