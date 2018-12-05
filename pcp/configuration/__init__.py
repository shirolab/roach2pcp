"""
Read the config files and return the object for importing by other modules. This script is called
when the "configuration" submodule is imported, and will load all the configuration files. Different
parts of the application can call individual configurations as required by using
'from configuration import <NAME>_config.'
"""

# TODO
# Log messages (but handle the configuration of the logger correctly (i.e. we can't log if it hasn't been configured!) )

# import configurations here (might be able to do this dynamically using importlib and inspect for variables)
import os as _os
import lib_config as _lib_config
from .lib_config import config_dir, general_config, filesys_config, logging_config, \
                        network_config, roach_config, hardware_config, firmware_registers
from .lib_config import reload_configfiles

from .lib_config import verify_config_consistency

ROOTDIR = filesys_config['rootdir']
if not _os.path.exists(ROOTDIR): _os.mkdir(ROOTDIR)
