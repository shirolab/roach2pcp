"""
Library containing functions used to handle and manipulate configuration files
"""

# TODO
# Log messages (but handle the configuration of the logger correctly (i.e. we can't log if it hasn't been configured!) )

import os as _os, sys as _sys, yaml as _yaml

config_dir = _os.path.dirname(__file__) # returns this directory, regardless of the cwd

def load_config_file(config_file):
    with open(config_file, "r") as f:
        print( "Loaded {0}".format(config_file) )
        return _yaml.safe_load(f)

#NOTE [20180728] that this has now been superseeded by a reload function within the main directory (left for now jic, will remove later)
def reload_configfiles():
   """Function to reload all configuration files. The easiest way to this is to
   reload the module."""
   reload(_sys.modules[__name__])
   print "Module reloaded"

# functions to verify that the configuration files are consistent
# - do they contain the same number of roaches in network, roach
# - do the synthids match the ids in hardware_config
# - check that the interfaces are not duplicated, or

def verify_config_consistency():
    """
    Top level function to run tests on the current set of configuration files to ensure
    consistency. Runs the following checks:
        - ensures that the number of roachids is consistent through all config files
        - checks that the synthids defined in roach_config match those defined in hardware_config
        - checks that multiple synth instances have same lo step
    """

    # get configuration file data
    # count how many roaches are defined
    # run through tests on various config files

def _cfgcheck_roachids():
    """
    Check roach ids are consistent between all files
    """

def _cfgcheck_synthids():
    """
    Check synth ids are consistent and match
    """

def _cfgcheck_dupifaces():
    """
    Check ehterhnet interfaces are not duplicated
    """

def _cfgcheck_ifacesexist():
    """
    Check ehterhnet interfaces are present in the system
    """


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
