"""
Library containing functions used to handle and manipulate configuration files
"""

# TODO
# Log messages (but handle the configuration of the logger correctly (i.e. we can't log if it hasn't been configured!) )

import os as _os, sys as _sys, yaml as _yaml
import re

import numpy as np

MIN_BUFFER = 0
MAX_BUFFER = 9000 

MIN_HEADER = 0
MAX_HEADER = 42

MIN_SYNTH_FREQ = 0         # 0 MHz
MAX_SYNTH_FREQ = 12000     # 12 MHz
MIN_STEP_SYNTH = 0.1    # This is for Windfreak

MAX_NUM_FREQS = 1012
MIN_NUM_FREQS = 1

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

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


def save_current_config():
    """
    Save the current parameters of the configuration files
    """

# Funtions to verify one by one the consistency of the configuration files

def verify_general_config(general_config):
    """
    Check coherence in the parameters of "general_config.cfg"
    """

    print './pcp/' + general_config["firmware_file"]
    #_os.system("pwd")

    #assert _os.path.exists("." + general_config["firmware_file"]), bcolors.FAIL + "Firmware file doesn't exist" + bcolors.ENDC


    # This are unreal huge limits, it depends of the synthesizer used, but they are useful for KID applications
    assert general_config["center_freq"] > MIN_SYNTH_FREQ, bcolors.FAIL + "Center frequency should be higher than 0 Hz" + bcolors.ENDC 
    assert general_config["center_freq"] <= MAX_SYNTH_FREQ, bcolors.FAIL + "Center frequency over range!" + bcolors.ENDC

    assert (np.float(general_config["lo_step"])/MIN_STEP_SYNTH)%1==0, bcolors.FAIL + 'Resolution is %.2f dB!'%MIN_STEP_SYNTH + bcolors.ENDC

    assert general_config["Nfreq"] <= MAX_NUM_FREQS, bcolors.FAIL + "Number of frequencies are over range!" + bcolors.ENDC
    assert general_config["Nfreq"] >= MIN_NUM_FREQS, bcolors.FAIL + "It should be at least one tone" + bcolors.ENDC

    assert np.float(general_config["max_pos_freq"]) - np.float(general_config["min_pos_freq"]) > 0, bcolors.FAIL + "The positivie frequency range is wrong, minimum frequency is greater than maximum" + bcolors.ENDC 
    assert np.float(general_config["min_neg_freq"]) - np.float(general_config["max_neg_freq"]) < 0, bcolors.FAIL + "The negative frequency range is wrong, maximum frequency is lower than minimum" + bcolors.ENDC 

    assert np.float(general_config["symm_offset"]) > 0, bcolors.FAIL + "Symm offset has to be positive!" + bcolors.ENDC

    assert np.float(general_config["test_freq"]) > MIN_SYNTH_FREQ*1.0e6, bcolors.FAIL + "Test frequency should be higher than 0 Hz" + bcolors.ENDC 
    assert np.float(general_config["test_freq"]) <= MAX_SYNTH_FREQ*1.0e6, bcolors.FAIL + "Test frequency over range!" + bcolors.ENDC

    # Check buffer header size 
    assert general_config["buf_size"] > MIN_BUFFER and general_config["buf_size"] <= MAX_BUFFER, bcolors.FAIL + "The buffer size is out of range!" + bcolors.ENDC
    assert general_config["header_len"] > MIN_HEADER and general_config["header_len"] <= MAX_HEADER, bcolors.FAIL + "The header length is out of range!" + bcolors.ENDC

    print bcolors.OKBLUE + "Format in general_config.cfg parameters are consistent." + bcolors.ENDC 

def verify_filesys_config(filesys_config):

    """
    Check the file paths exists
    """
    assert _os.path.isdir(filesys_config["rootdir"]), bcolors.FAIL + filesys_config["rootdir"] + ". Root directory doesn't exists!" + bcolors.ENDC
    print bcolors.OKBLUE + "Format in filesys_config.cfg parameters are consistent." + bcolors.ENDC 


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

def _cfgcheck_roachids(roach_config, network_config):
    """
    Check roach ids are consistent between all files
    """

    roach_id_roach = roach_config["roach_params"].keys()
    roach_id_network = _num_roaches(network_config)

    if len(roach_id_roach) > len(roach_id_network):
        id_vs_comp = roach_id_roach
        id_to_comp = roach_id_network
    else:
        id_vs_comp = roach_id_network
        id_to_comp = roach_id_roach

    roach_match = 0
    for roach_id in id_vs_comp:
        if roach_id in id_to_comp:
            roach_match += 1
            print bcolors.OKGREEN + roach_id + " matches in all files" + bcolors.ENDC    
        else:
            print bcolors.WARNING + roach_id + " doesn't match in all the config files." + bcolors.ENDC    

    assert roach_match != 0, bcolors.FAIL + "None of the ROACH ID matches, verify that they are written correctly in the config files." + bcolors.ENDC    

def _cfgcheck_synthids():
    """
    Check synth ids are consistent and match
    """
    

def _cfgcheck_dupifaces(file):

    n_roaches = _num_roaches(file)

    """
    Check if the network parameters are consistent
    """
    for n in n_roaches:
        assert _is_valid_ip(file[n]["roach_ppc_ip"]), bcolors.FAIL + "IP address is not valid!" + bcolors.ENDC
        print n + ":" + file[n]["roach_ppc_ip"] + bcolors.OKGREEN + " IP address valid" + bcolors.ENDC

        # Check parameters of UDP Source are valid
        assert _is_valid_ip(file[n]["udp_source_ip"]), n + ":" + file[n]["udp_source_ip"] + bcolors.FAIL + " UDP Source IP format is not valid!" + bcolors.ENDC
        print n + ":" + file[n]["udp_source_ip"] + bcolors.OKGREEN + " UDP Source IP format is valid" + bcolors.ENDC

        assert _is_valid_mac(file[n]["udp_source_mac"]), n + ":" + file[n]["udp_source_mac"] + bcolors.FAIL + " UDP Source MAC format is not valid!" + bcolors.ENDC
        print n + ":" + file[n]["udp_source_mac"] + bcolors.OKGREEN + " UDP Source MAC format is valid" + bcolors.ENDC

        if _is_valid_port(file[n]["udp_source_port"]) == "reserved":
            print n + ":" + str(file[n]["udp_source_port"]) + bcolors.WARNING + " UDP Source port needs root permisions" + bcolors.ENDC
        else:
            assert _is_valid_port(file[n]["udp_source_port"]), n + ":" + file[n]["udp_source_port"] + bcolors.FAIL + " UDP Source port format is not valid!" + bcolors.ENDC
            print n + ":" + str(file[n]["udp_source_port"]) + bcolors.OKGREEN + " UDP Source port format is valid" + bcolors.ENDC

        # Check parameters of UDP Dest are valid
        assert _is_valid_ip(file[n]["udp_dest_ip"]), n + ":" + file[n]["udp_dest_ip"] + bcolors.FAIL + " UDP dest IP format is not valid!" + bcolors.ENDC
        print n + ":" + file[n]["udp_dest_ip"] + bcolors.OKGREEN + " UDP dest IP format is valid" + bcolors.ENDC

        assert _is_valid_mac(file[n]["udp_dest_mac"]), n + ":" + file[n]["udp_dest_mac"] + bcolors.FAIL + " UDP dest MAC format is not valid!" + bcolors.ENDC
        print n + ":" + file[n]["udp_dest_mac"] + bcolors.OKGREEN + " UDP dest MAC format is valid" + bcolors.ENDC

        if _is_valid_port(file[n]["udp_dest_port"]) == "reserved":
            print n + ":" + str(file[n]["udp_dest_port"]) + bcolors.WARNING + " UDP dest port needs root permisions" + bcolors.ENDC
        else:
            assert _is_valid_port(file[n]["udp_dest_port"]), n + ":" + file[n]["udp_dest_port"] + bcolors.FAIL + " UDP dest port format is not valid!" + bcolors.ENDC
            print n + ":" + str(file[n]["udp_dest_port"]) + bcolors.OKGREEN + " UDP dest port format is valid" + bcolors.ENDC

        # Check buffer header size 
        assert file[n]["buf_size"] > 0 and file[n]["buf_size"] <= 9000, bcolors.FAIL + "The buffer size is out of range!" + bcolors.ENDC
        assert file[n]["header_len"] > 0 and file[n]["header_len"] <= 42, bcolors.FAIL + "The header length is out of range!" + bcolors.ENDC

        print bcolors.OKBLUE + n + " buffer size and header length within range" + bcolors.ENDC

        # Check conflicts between source and dest network parameters
        assert file[n]["roach_ppc_ip"] != file[n]["udp_dest_ip"], bcolors.FAIL + "IP conflict. Roach PPC and Dest have the same IP address" + bcolors.ENDC 
        assert file[n]["roach_ppc_ip"] != file[n]["udp_source_ip"], bcolors.FAIL + "IP conflict. Roach PPC and Source have the same IP address" + bcolors.ENDC 
        
        assert file[n]["udp_source_ip"] != file[n]["udp_dest_ip"], bcolors.FAIL + "UDP IP conflict. Source and Dest have the same IP address" + bcolors.ENDC 
        assert file[n]["udp_source_mac"] != file[n]["udp_dest_mac"], bcolors.FAIL + "UDP MAC conflict. Source and Dest have the same MAC address" + bcolors.ENDC
        
        print bcolors.OKBLUE + n + " no conflicts founded between source and dest" + bcolors.ENDC

    """
    Check ehternet interfaces are not duplicated
    """
    start_comp = 1
    for roach_1 in range(len(n_roaches)):
        for roach_2 in range(start_comp,len(n_roaches)):
            assert file[n_roaches[roach_1]]["roach_ppc_ip"] != file[n_roaches[roach_2]]["roach_ppc_ip"],  bcolors.FAIL + "There is a roach IP conflict. There are two roaches with the same IP address: " + n_roaches[roach_1] + "," + n_roaches[roach_2] + bcolors.ENDC

            assert file[n_roaches[roach_1]]["udp_source_ip"] != file[n_roaches[roach_2]]["udp_source_ip"],  bcolors.FAIL + "There is a UDP source IP conflict. There are two roaches with the same IP source address: " + n_roaches[roach_1] + "," + n_roaches[roach_2] + bcolors.ENDC
            assert file[n_roaches[roach_1]]["udp_source_mac"] != file[n_roaches[roach_2]]["udp_source_mac"],  bcolors.FAIL + "There is a UDP source IP conflict. There are two roaches with the same MAC source address: " + n_roaches[roach_1] + "," + n_roaches[roach_2] + bcolors.ENDC

            assert file[n_roaches[roach_1]]["udp_dest_ip"] != file[n_roaches[roach_2]]["udp_dest_ip"],  bcolors.FAIL + "There is a UDP dest IP conflict. There are two roaches with the same IP dest address: " + n_roaches[roach_1] + "," + n_roaches[roach_2] + bcolors.ENDC
            assert file[n_roaches[roach_1]]["udp_dest_mac"] != file[n_roaches[roach_2]]["udp_dest_mac"],  bcolors.FAIL + "There is a UDP dest IP conflict. There are two roaches with the same MAC dest address: " + n_roaches[roach_1] + "," + n_roaches[roach_2] + bcolors.ENDC

            assert file[n_roaches[roach_1]]["udp_dest_device"] != file[n_roaches[roach_2]]["udp_dest_device"],  bcolors.FAIL + "There is a UDP device conflict. There are two roaches with the same UDP device address: " + n_roaches[roach_1] + "," + n_roaches[roach_2] + bcolors.ENDC
            
        start_comp += 1

    print bcolors.OKBLUE + "ROACH network parameters. No conflicts founded" + bcolors.ENDC

    """
    Check values of UDP packages
    """
    assert file["MAXCHANNELS"] > 0, bcolors.FAIL + "It should be at least 1 channel" + bcolors.ENDC
    assert file["MAXCHANNELS"] <= 1012, bcolors.FAIL + "The maximum number of channels is 1012 (20 are reserved)" + bcolors.ENDC 


def _num_roaches(dict_file):
    """
    Number of Roaches defined in the configuration files
    """
    return [n for n in dict_file.keys() if type(dict_file[n]) == dict and "device_id" in dict_file[n]]

def _is_valid_port(port):
    if port >= 0 and port <= 1023:
        return "reserved"
    return port >= 0 and port <= 65535 

def _is_valid_ip(ip):
    if ip == "localhost":
        return True
    m = re.match(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$", ip)
    return bool(m) and all(map(lambda n: 0 <= int(n) <= 255, m.groups()))

def _is_valid_mac(mac):
    m = re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", mac.lower())
    return bool(m)

def _cfgcheck_ifacesexist():
    """
    Check ehternet interfaces are present in the system
    """

    #Simon carnal, que si los dispositivos de red existen fisicamente en la compu
    #Como el device, su mac y la IP


############# General configuration #############
general_config_file = _os.path.join(config_dir, 'general_config.cfg')

assert _os.path.exists(general_config_file)
#general_config = roachConfig(general_config_file)
general_config = load_config_file(general_config_file)

verify_general_config(general_config)

############# Hardware configuration #############
hardware_config_file = _os.path.join(config_dir, 'hardware_config.cfg')

assert _os.path.exists(hardware_config_file)
hardware_config = load_config_file(hardware_config_file)

############# Filesystem configuration #############
filesys_config_file = _os.path.join(config_dir, 'filesys_config.cfg')

assert _os.path.exists(filesys_config_file)
filesys_config = load_config_file(filesys_config_file)

verify_filesys_config(filesys_config)

############# Logging configuration #############
logging_config_file = _os.path.join(config_dir, 'logging_config.cfg')

assert _os.path.exists(logging_config_file)
logging_config = load_config_file(logging_config_file)

############# Network configuration #############
network_config_file = _os.path.join(config_dir, 'network_config.cfg')

assert _os.path.exists(network_config_file)
network_config = load_config_file(network_config_file)

_cfgcheck_dupifaces(network_config)

############## Roach configuration ##############
roach_config_file = _os.path.join(config_dir, 'roach_config.cfg')

assert _os.path.exists(roach_config_file)
roach_config = load_config_file(roach_config_file)

_cfgcheck_roachids(roach_config, network_config)


############## Roach firmware registers ##############
firmware_registers = _os.path.join(config_dir, 'firmware_registers.cfg')

assert _os.path.exists(firmware_registers)
firmware_registers = load_config_file(firmware_registers)
