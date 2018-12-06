"""
Library containing functions used to handle and manipulate configuration files
"""

# TODO
# Log messages (but handle the configuration of the logger correctly (i.e. we can't log if it hasn't been configured!) )

import os as _os, sys as _sys, yaml as _yaml
import re

import numpy as np
import net_ifaces as ni

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
    assert _os.path.exists(general_config["firmware_file"]), bcolors.FAIL + "Firmware file doesn't exist" + bcolors.ENDC

    print bcolors.OKBLUE + "Format in general_config.cfg parameters are consistent." + bcolors.ENDC 

def verify_filesys_config(filesys_config):
    """
    Check the file paths exists
    """
    assert _os.path.isdir(filesys_config["rootdir"]), bcolors.FAIL + filesys_config["rootdir"] + ". Root directory doesn't exists!" + bcolors.ENDC
    print bcolors.OKBLUE + "Parameters in filesys_config.cfg are consistent." + bcolors.ENDC 

def verify_hardware_config(hardware_config):
    """
    Check the parameters in hardware config file are logical
    """
    # Synthesizers
    n_synths = _num_synths(hardware_config)

    # Attenuators
    in_Att = False
    out_Att = False
    n_attens = _num_attens(hardware_config)
    for atten in n_attens:
        if hardware_config["atten_config"][atten]["direction"] == "in":
            in_Att = True
        if hardware_config["atten_config"][atten]["direction"] == "out":
            out_Att = True 

    if len(n_synths) <= 0:
        print bcolors.WARNING + "There is not synthesizers defined in the configuration file" + bcolors.ENDC
    elif not in_Att:
        print bcolors.WARNING + "Input attenuators is not defined" + bcolors.ENDC
    elif not out_Att:
        print bcolors.WARNING + "Output attenuators is not defined" + bcolors.ENDC
    else:
        print bcolors.OKBLUE + "Synthesizers and attenuators are defined in the configuration file" + bcolors.ENDC

def verify_network_config(network_config):

    n_roaches = _num_roaches(network_config)

    """
    Check if the network parameters are consistent
    """
    for n in n_roaches:
        assert _is_valid_ip(network_config[n]["roach_ppc_ip"]), bcolors.FAIL + "IP address is not valid!" + bcolors.ENDC
        print n + ":" + network_config[n]["roach_ppc_ip"] + bcolors.OKGREEN + " IP address valid" + bcolors.ENDC

        # Check parameters of UDP Source are valid
        assert _is_valid_ip(network_config[n]["udp_source_ip"]), n + ":" + network_config[n]["udp_source_ip"] + bcolors.FAIL + " UDP Source IP format is not valid!" + bcolors.ENDC
        print n + ":" + network_config[n]["udp_source_ip"] + bcolors.OKGREEN + " UDP Source IP format is valid" + bcolors.ENDC

        assert _is_valid_mac(network_config[n]["udp_source_mac"]), n + ":" + network_config[n]["udp_source_mac"] + bcolors.FAIL + " UDP Source MAC format is not valid!" + bcolors.ENDC
        print n + ":" + network_config[n]["udp_source_mac"] + bcolors.OKGREEN + " UDP Source MAC format is valid" + bcolors.ENDC

        if _is_valid_port(network_config[n]["udp_source_port"]) == "reserved":
            print n + ":" + str(network_config[n]["udp_source_port"]) + bcolors.WARNING + " UDP Source port needs root permisions" + bcolors.ENDC
        else:
            assert _is_valid_port(network_config[n]["udp_source_port"]), n + ":" + network_config[n]["udp_source_port"] + bcolors.FAIL + " UDP Source port format is not valid!" + bcolors.ENDC
            print n + ":" + str(network_config[n]["udp_source_port"]) + bcolors.OKGREEN + " UDP Source port format is valid" + bcolors.ENDC

        # Check parameters of UDP Dest are valid
        assert _is_valid_ip(network_config[n]["udp_dest_ip"]), n + ":" + network_config[n]["udp_dest_ip"] + bcolors.FAIL + " UDP dest IP format is not valid!" + bcolors.ENDC
        print n + ":" + network_config[n]["udp_dest_ip"] + bcolors.OKGREEN + " UDP dest IP format is valid" + bcolors.ENDC

        assert _is_valid_mac(network_config[n]["udp_dest_mac"]), n + ":" + network_config[n]["udp_dest_mac"] + bcolors.FAIL + " UDP dest MAC format is not valid!" + bcolors.ENDC
        print n + ":" + network_config[n]["udp_dest_mac"] + bcolors.OKGREEN + " UDP dest MAC format is valid" + bcolors.ENDC

        if _is_valid_port(network_config[n]["udp_dest_port"]) == "reserved":
            print n + ":" + str(network_config[n]["udp_dest_port"]) + bcolors.WARNING + " UDP dest port needs root permisions" + bcolors.ENDC
        else:
            assert _is_valid_port(network_config[n]["udp_dest_port"]), n + ":" + file[n]["udp_dest_port"] + bcolors.FAIL + " UDP dest port format is not valid!" + bcolors.ENDC
            print n + ":" + str(network_config[n]["udp_dest_port"]) + bcolors.OKGREEN + " UDP dest port format is valid" + bcolors.ENDC

        # Check buffer header size 
        assert network_config[n]["buf_size"] > 0 and network_config[n]["buf_size"] <= 9000, bcolors.FAIL + "The buffer size is out of range!" + bcolors.ENDC
        assert network_config[n]["header_len"] > 0 and network_config[n]["header_len"] <= 42, bcolors.FAIL + "The header length is out of range!" + bcolors.ENDC

        print bcolors.OKBLUE + n + " buffer size and header length within range" + bcolors.ENDC

        # Check conflicts between source and dest network parameters
        assert network_config[n]["roach_ppc_ip"] != network_config[n]["udp_dest_ip"], bcolors.FAIL + "IP conflict. Roach PPC and Dest have the same IP address" + bcolors.ENDC 
        assert network_config[n]["roach_ppc_ip"] != network_config[n]["udp_source_ip"], bcolors.FAIL + "IP conflict. Roach PPC and Source have the same IP address" + bcolors.ENDC 
        
        assert network_config[n]["udp_source_ip"] != network_config[n]["udp_dest_ip"], bcolors.FAIL + "UDP IP conflict. Source and Dest have the same IP address" + bcolors.ENDC 
        assert network_config[n]["udp_source_mac"] != network_config[n]["udp_dest_mac"], bcolors.FAIL + "UDP MAC conflict. Source and Dest have the same MAC address" + bcolors.ENDC
        
        print bcolors.OKBLUE + n + " no conflicts founded between source and dest" + bcolors.ENDC

    """
    Check values of UDP packages
    """
    assert network_config["MAXCHANNELS"] > 0, bcolors.FAIL + "It should be at least 1 channel" + bcolors.ENDC
    assert network_config["MAXCHANNELS"] <= 1012, bcolors.FAIL + "The maximum number of channels is 1012 (20 are reserved)" + bcolors.ENDC 

    print bcolors.OKBLUE + "Parameters in network_config.cfg are consistent." + bcolors.ENDC 

def verify_roach_config(roach_config):

    n_roaches = _num_roaches(roach_config["roach_params"])

    for roach in n_roaches:

        # This are unreal huge limits, it depends of the synthesizer used, but they are useful for KID applications
        assert roach_config["roach_params"][roach]["center_freq"] > MIN_SYNTH_FREQ, bcolors.FAIL + "Center frequency should be higher than 0 Hz" + bcolors.ENDC 
        assert roach_config["roach_params"][roach]["center_freq"] <= MAX_SYNTH_FREQ, bcolors.FAIL + "Center frequency over range!" + bcolors.ENDC

        assert (np.float(roach_config["roach_params"][roach]["lo_step"])/MIN_STEP_SYNTH)%1==0, bcolors.FAIL + 'Resolution is %.2f dB!'%MIN_STEP_SYNTH + bcolors.ENDC

        assert roach_config["roach_params"][roach]["Nfreq"] <= MAX_NUM_FREQS, bcolors.FAIL + "Number of frequencies are over range!" + bcolors.ENDC
        assert roach_config["roach_params"][roach]["Nfreq"] >= MIN_NUM_FREQS, bcolors.FAIL + "It should be at least one tone" + bcolors.ENDC

        assert np.float(roach_config["roach_params"][roach]["max_pos_freq"]) - np.float(roach_config["roach_params"][roach]["min_pos_freq"]) > 0, bcolors.FAIL + "The positivie frequency range is wrong, minimum frequency is greater than maximum" + bcolors.ENDC 
        assert np.float(roach_config["roach_params"][roach]["min_neg_freq"]) - np.float(roach_config["roach_params"][roach]["max_neg_freq"]) < 0, bcolors.FAIL + "The negative frequency range is wrong, maximum frequency is lower than minimum" + bcolors.ENDC 

        assert np.float(roach_config["roach_params"][roach]["symm_offset"]) > 0, bcolors.FAIL + "Symm offset has to be positive!" + bcolors.ENDC

        assert np.float(roach_config["roach_params"][roach]["test_freq"]) > MIN_SYNTH_FREQ*1.0e6, bcolors.FAIL + "Test frequency should be higher than 0 Hz" + bcolors.ENDC 
        assert np.float(roach_config["roach_params"][roach]["test_freq"]) <= MAX_SYNTH_FREQ*1.0e6, bcolors.FAIL + "Test frequency over range!" + bcolors.ENDC

        # Check buffer header size 
        assert roach_config["roach_params"][roach]["buf_size"] > MIN_BUFFER and roach_config["roach_params"][roach]["buf_size"] <= MAX_BUFFER, bcolors.FAIL + "The buffer size is out of range!" + bcolors.ENDC
        assert roach_config["roach_params"][roach]["header_len"] > MIN_HEADER and roach_config["roach_params"][roach]["header_len"] <= MAX_HEADER, bcolors.FAIL + "The header length is out of range!" + bcolors.ENDC

    print bcolors.OKBLUE + "Parameters in roach_config.cfg are consistent." + bcolors.ENDC 

# functions to verify that the configuration files are consistent
# - do they contain the same number of roaches in network, roach
# - do the synthids match the ids in hardware_config
# - check that the interfaces are not duplicated, or

def verify_config_consistency(roach_config,network_config,hardware_config):
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

    _cfgcheck_roachids(roach_config, network_config)
    _cfgcheck_dupifaces(network_config)
    _cfgcheck_synthids(roach_config, hardware_config)
    _cfgcheck_ifacesexist(network_config)

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


def _cfgcheck_synthids(roach_config, hardware_config):
    """
    Check synth ids are consistent and match
    """
    n_roaches = roach_config["roach_params"].keys()
    synth_id_hardware = _num_synths(hardware_config)

    _is_lo = False
    _is_clk = False

    for roach in n_roaches:
        if roach_config["roach_params"][roach]["synthid_lo"] in synth_id_hardware:
            _is_lo = True
        if roach_config["roach_params"][roach]["synthid_clk"] in synth_id_hardware:
            _is_clk = True

        if _is_lo and _is_clk:            
            if roach_config["roach_params"][roach]["synthid_lo"] == roach_config["roach_params"][roach]["synthid_clk"]:
                synth = hardware_config["synth_config"][roach_config["roach_params"][roach]["synthid_lo"]]
                if "channel" in synth:
                    if synth["channel"] < 2:
                        print bcolors.WARNING + roach_config["roach_params"][roach]["synthid_lo"] + " has not enough channels for lo and clk signals" + bcolors.ENDC
                    else:
                       print bcolors.OKBLUE + "Synthesizers parameters are consistent" + bcolors.ENDC
            else:
                print bcolors.OKBLUE + "Synthesizers parameters are consistent" + bcolors.ENDC

        elif not _is_lo:
            print bcolors.WARNING + "LO synthesizer not founded" + bcolors.ENDC
        elif not _is_clk:
            print bcolors.WARNING + "CLK synthesizer not founded" + bcolors.ENDC

        _is_clk = False
        _is_lo = False

def _cfgcheck_dupifaces(network_config):

    n_roaches = _num_roaches(network_config)

    """
    Check ehternet interfaces are not duplicated
    """
    start_comp = 1
    for roach_1 in range(len(n_roaches)):
        for roach_2 in range(start_comp,len(n_roaches)):
            assert network_config[n_roaches[roach_1]]["roach_ppc_ip"] != network_config[n_roaches[roach_2]]["roach_ppc_ip"],  bcolors.FAIL + "There is a roach IP conflict. There are two roaches with the same IP address: " + n_roaches[roach_1] + "," + n_roaches[roach_2] + bcolors.ENDC

            assert network_config[n_roaches[roach_1]]["udp_source_ip"] != network_config[n_roaches[roach_2]]["udp_source_ip"],  bcolors.FAIL + "There is a UDP source IP conflict. There are two roaches with the same IP source address: " + n_roaches[roach_1] + "," + n_roaches[roach_2] + bcolors.ENDC
            assert network_config[n_roaches[roach_1]]["udp_source_mac"] != network_config[n_roaches[roach_2]]["udp_source_mac"],  bcolors.FAIL + "There is a UDP source IP conflict. There are two roaches with the same MAC source address: " + n_roaches[roach_1] + "," + n_roaches[roach_2] + bcolors.ENDC

            assert network_config[n_roaches[roach_1]]["udp_dest_ip"] != network_config[n_roaches[roach_2]]["udp_dest_ip"],  bcolors.FAIL + "There is a UDP dest IP conflict. There are two roaches with the same IP dest address: " + n_roaches[roach_1] + "," + n_roaches[roach_2] + bcolors.ENDC
            assert network_config[n_roaches[roach_1]]["udp_dest_mac"] != network_config[n_roaches[roach_2]]["udp_dest_mac"],  bcolors.FAIL + "There is a UDP dest IP conflict. There are two roaches with the same MAC dest address: " + n_roaches[roach_1] + "," + n_roaches[roach_2] + bcolors.ENDC

            assert network_config[n_roaches[roach_1]]["udp_dest_device"] != network_config[n_roaches[roach_2]]["udp_dest_device"],  bcolors.FAIL + "There is a UDP device conflict. There are two roaches with the same UDP device address: " + n_roaches[roach_1] + "," + n_roaches[roach_2] + bcolors.ENDC
            
        start_comp += 1

    print bcolors.OKBLUE + "ROACH network parameters. No conflicts founded" + bcolors.ENDC

def _cfgcheck_ifacesexist(network_config):
    """
    Check ehternet interfaces are present in the system
    """

    ifconfig = ni.get_ifconfig()
    ifaces = ni.get_ifaces(ifconfig)

    n_roaches = _num_roaches(network_config)
    device_flag = [False]*len(n_roaches)

    for roach in n_roaches:
        device_flag = False
        ip_flag = False
        mac_flag = False

        udp_mac = network_config[roach]["udp_dest_mac"].lower()
        n_udp_mac = ""
        for i in udp_mac:
            if i != ":":
                n_udp_mac += i

        for iface in ifaces:
            if ((network_config[roach]["udp_dest_device"] == "localhost" or network_config[roach]["udp_dest_device"] == "") and iface[0] == "lo") or (network_config[roach]["udp_dest_device"] == iface[0]):
                if network_config[roach]["udp_dest_ip"] == iface[1] or (network_config[roach]["udp_dest_ip"] == "localhost" and (iface[1] == "localhost" or iface[1] == "127.0.0.1")):
                    ip_flag = True
                if n_udp_mac == iface[3]:
                    mac_flag = True
                if (network_config[roach]["udp_dest_device"] == "localhost" or network_config[roach]["udp_dest_device"] == ""):
                    mac_flag = True

                device_flag = True

        device = network_config[roach]["udp_dest_device"]
        if network_config[roach]["udp_dest_device"] == "":
            device = "localhost"

        if device_flag:
            if ip_flag and mac_flag:
                print bcolors.OKGREEN + roach + "-" + device + " is defined in network interface. IP and MAC address match" + bcolors.ENDC
            if not ip_flag:
                print bcolors.WARNING + roach + "-" + device + ". The IP of the device doesn't match with the configuration file." + bcolors.ENDC
            if not mac_flag:
                print bcolors.WARNING + roach + "-" + device + ". MAC address of the device doesn't match with the configuration file." + bcolors.ENDC
        else:
            raise Exception(bcolors.FAIL + roach + "-" + device + " is not defined in network interface." + bcolors.ENDC)


def _num_roaches(dict_file):
    """
    Number of Roaches defined in the configuration files
    """
    return [n for n in dict_file.keys() if type(dict_file[n]) == dict and "device_id" in dict_file[n]]

def _num_synths(dict_file):
    """
    Return the synthesizers id in config file
    """
    return dict_file["synth_config"].keys()

def _num_attens(dict_file):
    """
    Return the attenuators id in config file
    """
    return dict_file["atten_config"].keys()

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

verify_hardware_config(hardware_config)

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

verify_network_config(network_config)

############## Roach configuration ##############
roach_config_file = _os.path.join(config_dir, 'roach_config.cfg')

assert _os.path.exists(roach_config_file)
roach_config = load_config_file(roach_config_file)

############## Roach firmware registers ##############
firmware_registers = _os.path.join(config_dir, 'firmware_registers.cfg')

assert _os.path.exists(firmware_registers)
firmware_registers = load_config_file(firmware_registers)

verify_config_consistency(roach_config, network_config, hardware_config)
