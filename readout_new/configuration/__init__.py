"""
Read the config files and return the object for importing by other modules. This script is called
when the "configuration" submodule is imported, and will load all the configuration files. Different
parts of the application can call individual configurations as required by using
'from configuration import <NAME>_config.'
"""

# TODO
# is there a method to reload this on demand? e.g. when config files are changed? Dynamic reloading of the submodule
# where required should work.
# Log messages (but handle the configuration of the logger correctly (i.e. we can't log if it hasn't been configured!) )

import os as _os, sys as _sys, yaml as _yaml
config_dir = _os.path.dirname(__file__) # returns this directory, regardless of the cwd

def load_config_file(config_file):
    with open(config_file, "r") as f:
        return _yaml.safe_load(f)

def reload_all():
   """Function to reload all configuration files. The easiest way to this is to
   reload the module."""

   reload(_sys.modules[__name__])
   print "Module reloaded"

############# General configuration #############
general_config_file = _os.path.join(config_dir, 'general_config.cfg')

assert _os.path.exists(general_config_file)
#general_config = roachConfig(general_config_file)
general_config = load_config_file(general_config_file)

############# Hardware configuration #############
hardware_config_file = _os.path.join(config_dir, 'hardware_config.cfg')

assert _os.path.exists(hardware_config_file)
hardware_config = load_config_file(hardware_config_file)

############# Filesystem configuration #############
filesys_config_file = _os.path.join(config_dir, 'filesys_config.cfg')

assert _os.path.exists(filesys_config_file)
filesys_config = load_config_file(filesys_config_file)

############# Logging configuration #############
logging_config_file = _os.path.join(config_dir, 'logging_config.cfg')

assert _os.path.exists(logging_config_file)
logging_config = load_config_file(logging_config_file)

############# Network configuration #############
network_config_file = _os.path.join(config_dir, 'network_config.cfg')

assert _os.path.exists(network_config_file)
network_config = load_config_file(network_config_file)

############## Roach configuration ##############
roach_config_file = _os.path.join(config_dir, 'roach_config.cfg')

assert _os.path.exists(roach_config_file)
roach_config = load_config_file(roach_config_file)


# class roachConfig(object):
#     """Simple container to load in a configuration file. Functionality can, and probably will, be
#     extended at a later date.
#     """
#
#     def __init__(self, config_file):
#         #self.config_file = config_file
#         self._reload_config_file(config_file)
#
#     def _reload_config_file(self, config_file):
#         with open(config_file, "r") as f:
#             self.config = _yaml.safe_load(f)
