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

import os, yaml
config_dir = os.path.dirname(__file__) # returns this directory, regardless of the cwd

class roachConfig(object):
    """Simple container to load in a configuration file. Functionality can, and probably will, be
    extended at a later date.
    """

    def __init__(self, config_file):
        self.config_file = config_file
        self._reload_config_file()

    def _reload_config_file(self):
        with open(self.config_file, "r") as f:
            self.config = yaml.safe_load(f)

#def reload_all():
#    """Function to reload all configuration files. The easiest way to this is to
#    reload the module. How to do that?"""

############# Hardware configuration #############

general_config_file = os.path.join(config_dir, 'general_config.yml')

assert os.path.exists(general_config_file)
general_config = roachConfig(general_config_file)

############# Hardware configuration #############

hardware_config_file = os.path.join(config_dir, 'hardware_config.yml')

assert os.path.exists(hardware_config_file)
hardware_config = roachConfig(hardware_config_file)

############# Filesystem configuration #############

filesys_config_file = os.path.join(config_dir, 'filesys_config.yml')

assert os.path.exists(filesys_config_file)
filesys_config = roachConfig(filesys_config_file)

############# Logging configuration #############

logging_config_file = os.path.join(config_dir, 'logging_config.yml')

assert os.path.exists(logging_config_file)
logging_config = roachConfig(logging_config_file)

############# Network configuration #############

network_config_file = os.path.join(config_dir, 'network_config.yml')

assert os.path.exists(network_config_file)
network_config = roachConfig(network_config_file)

############## Roach configuration ##############

roach_config_file = os.path.join(config_dir, 'roach_config.yml')
assert os.path.exists(roach_config_file)
roach_config = roachConfig(roach_config_file)
