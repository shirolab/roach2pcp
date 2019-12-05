"""
Library containing functions used to handle and manipulate configuration files
"""

# TODO
# Log messages (but handle the configuration of the logger correctly (i.e. we can't log if it hasn't been configured!) )

import os as _os, sys as _sys, re as _re, yaml as _yaml, logging as _logging
import numpy as np

_logger = _logging.getLogger(__name__)

import net_ifaces as ni

config_dir = _os.path.dirname(__file__) # returns this directory, regardless of the cwd

# adds additional functionality to
pcp_yaml_loader = _yaml.SafeLoader
pcp_yaml_loader.add_implicit_resolver(  u'tag:yaml.org,2002:float', _re.compile(u'''^(?:
                                        [-+]?(?:[0-9][0-9_]*)\\.[0-9_]*(?:[eE][-+]?[0-9]+)?
                                        |[-+]?(?:[0-9][0-9_]*)(?:[eE][-+]?[0-9]+)
                                        |\\.[0-9_]+(?:[eE][-+][0-9]+)?
                                        |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\\.[0-9_]*
                                        |[-+]?\\.(?:inf|Inf|INF)
                                        |\\.(?:nan|NaN|NAN))$''', _re.X),
                                    list(u'-+0123456789.')
                                    )
def load_config_file(config_file):
    with open(config_file, "r") as f:
        msg = "Loaded {0}".format(config_file)
        # if logging hasn't been configured yet, print to screen
        if not _logger.root.handlers or _logger.manager.emittedNoHandlerWarning:
            print( msg )
        else:
            _logger.info( msg )

        return _yaml.load(f, Loader=pcp_yaml_loader)

def get_firmware_register_dict(firmware_registers, firmware_filename):
    """Given an .fpg filename, return a dictionary containing the corresponding data from firmware_registers.cfg """

    assert type(firmware_registers) == dict, "given firmware_registers dict not valid"
    # read all entries and check if fileame is present
    for key, firmware_dict in firmware_registers.iteritems():

        if firmware_filename in firmware_dict["filenames"]:
            break

    else:
        raise AttributeError("firmware file {0} not present in firmware_registers.cfg".format(firmware_filename))

    return firmware_dict

#NOTE [20180728] that this has now been superseeded by a reload function within the main directory (left for now jic, will remove later)
def reload_configfiles():
   """Function to reload all configuration files. The easiest way to this is to
   reload the module."""
   reload(_sys.modules[__name__])
   _logger.info( "Module {0} reloaded".format(__name__) )

def save_current_config():
    """
    Save the current parameters of the configuration files
    """

# Funtions to verify one by one the consistency of the configuration files
def verify_general_config(general_config):
    """
    Check coherence in the parameters of "general_config.cfg"
    """
    assert _os.path.exists(general_config["firmware_file"]), _logger.warning("Firmware file doesn't exist")
    _logger.info("Format in general_config.cfg parameters are consistent.")

def verify_filesys_config(filesys_config):
    """
    Check the file paths exists
    """
    assert _os.path.isdir(filesys_config["rootdir"]), _logger.warning(filesys_config["rootdir"] + ". Root directory doesn't exists!")
    _logger.info("Parameters in filesys_config.cfg are consistent.")

def verify_hardware_config(hardware_config):
    """
    Check the parameters in hardware config file are logical
    """
    # Synthesizers
    n_synths = _num_synths(hardware_config)

    for synth in n_synths:
        assert "modelnum" in hardware_config["synth_config"][synth] and hardware_config["synth_config"][synth]["modelnum"] != None, _logger.warning(synth +" needs a modelnum to work")

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
        _logger.warning("There is not synthesizers defined in the configuration file")
    elif not in_Att:
        _logger.warning("Input attenuators is not defined")
    elif not out_Att:
        _logger.warning("Output attenuators is not defined")
    else:
        _logger.info("Synthesizers and attenuators are defined in the configuration file")

def verify_network_config(network_config):

    n_roaches = _num_roaches(network_config)

    """
    Check if the network parameters are consistent
    """
    for n in n_roaches:
        assert _is_valid_ip(network_config[n]["roach_ppc_ip"]), _logger.warning("IP address is not valid!")
        _logger.info(n + ":" + network_config[n]["roach_ppc_ip"] + " IP address valid")

        # Check parameters of UDP Source are valid
        assert _is_valid_ip(network_config[n]["udp_source_ip"]), _logger.warning(n + ":" + network_config[n]["udp_source_ip"] + " UDP Source IP format is not valid!")
        _logger.info(n + ":" + network_config[n]["udp_source_ip"] + " UDP Source IP format is valid")

        assert _is_valid_mac(network_config[n]["udp_source_mac"]), _logger.warning(n + ":" + network_config[n]["udp_source_mac"] + " UDP Source MAC format is not valid!")
        _logger.info(n + ":" + network_config[n]["udp_source_mac"] + " UDP Source MAC format is valid")

        if _is_valid_port(network_config[n]["udp_source_port"]) == "reserved":
            _logger.warning(n + ":" + str(network_config[n]["udp_source_port"]) + " UDP Source port needs root permisions")
        else:
            assert _is_valid_port(network_config[n]["udp_source_port"]), _logger.warning(n + ":" + network_config[n]["udp_source_port"] + " UDP Source port format is not valid!")
            _logger.info(n + ":" + str(network_config[n]["udp_source_port"]) + " UDP Source port format is valid")

        # Check parameters of UDP Dest are valid
        assert _is_valid_ip(network_config[n]["udp_dest_ip"]), _logger.warning(n + ":" + network_config[n]["udp_dest_ip"] + " UDP dest IP format is not valid!")
        _logger.info(n + ":" + network_config[n]["udp_dest_ip"] + " UDP dest IP format is valid")

        assert _is_valid_mac(network_config[n]["udp_dest_mac"]), _logger.warning(n + ":" + network_config[n]["udp_dest_mac"] + " UDP dest MAC format is not valid!")
        _logger.info(n + ":" + network_config[n]["udp_dest_mac"] + " UDP dest MAC format is valid")

        if _is_valid_port(network_config[n]["udp_dest_port"]) == "reserved":
            _logger.warning(n + ":" + str(network_config[n]["udp_dest_port"]) + " UDP dest port needs root permisions")
        else:
            assert _is_valid_port(network_config[n]["udp_dest_port"]), _logger.warning(n + ":" + file[n]["udp_dest_port"] + " UDP dest port format is not valid!")
            _logger.info(n + ":" + str(network_config[n]["udp_dest_port"]) + " UDP dest port format is valid")

        # Check buffer header size
        assert network_config[n]["buf_size"] > 0 and network_config[n]["buf_size"] <= 9000, _logger.warning("The buffer size is out of range!")
        assert network_config[n]["header_len"] > 0 and network_config[n]["header_len"] <= 42, _logger.warning("The header length is out of range!")

        _logger.info(n + " buffer size and header length within range")

        # Check conflicts between source and dest network parameters
        assert network_config[n]["roach_ppc_ip"] != network_config[n]["udp_dest_ip"], _logger.warning("IP conflict. Roach PPC and Dest have the same IP address")
        assert network_config[n]["roach_ppc_ip"] != network_config[n]["udp_source_ip"], _logger.warning("IP conflict. Roach PPC and Source have the same IP address")

        assert network_config[n]["udp_source_ip"] != network_config[n]["udp_dest_ip"], _logger.warning("UDP IP conflict. Source and Dest have the same IP address")
        assert network_config[n]["udp_source_mac"] != network_config[n]["udp_dest_mac"], _logger.warning("UDP MAC conflict. Source and Dest have the same MAC address")

        _logger.info(n + " no conflicts founded between source and dest")

    _logger.info("Parameters in network_config.cfg are consistent.")

def verify_roach_config(roach_config):

    n_roaches = _num_roaches(roach_config)

    for roach in n_roaches:

        # Check buffer header size
        assert roach_config["roach_params"][roach]["buf_size"] > 0 and roach_config["roach_params"][roach]["buf_size"] <= 9000, _logger.warning("The buffer size is out of range!")
        assert roach_config["roach_params"][roach]["header_len"] > 0 and roach_config["roach_params"][roach]["header_len"] <= 42, _logger.warning("The header length is out of range!")

        assert roach_config["roach_params"][roach]["maxchannels"] > 0, _logger.warning("It should be at least 1 channel")
        assert roach_config["roach_params"][roach]["maxchannels"] <= 1012, _logger.warning("The maximum number of channels is 1012 (20 are reserved)")

    _logger.info("Parameters in roach_config.cfg are consistent.")

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

    roach_id_roach = roach_config.keys()
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
            _logger.info(roach_id + " matches in all files")
        else:
            _logger.warning(roach_id + " doesn't match in all the config files.")

    assert roach_match != 0, _logger.warning("None of the ROACH ID matches, verify that they are written correctly in the config files.")

def _cfgcheck_synthids(roach_config, hardware_config):
    """
    Check synth ids are consistent and match
    """
    n_roaches = roach_config.keys()
    synth_id_hardware = _num_synths(hardware_config)

    _is_lo = False
    _is_clk = False

    for roach in n_roaches:
        if roach_config[roach]["synthid_lo"] in synth_id_hardware:
            _is_lo = True
        if roach_config[roach]["synthid_clk"] in synth_id_hardware:
            _is_clk = True

        if _is_lo and _is_clk:
            if roach_config[roach]["synthid_lo"] == roach_config[roach]["synthid_clk"]:
                synth = hardware_config["synth_config"][roach_config[roach]["synthid_lo"]]
                if "channel" in synth:
                    if synth["channel"] < 2:
                        _logger.warning(roach_config[roach]["synthid_lo"] + " has not enough channels for lo and clk signals")
                    else:
                        _logger.info("Synthesizers parameters are consistent")
            else:
                _logger.info("Synthesizers parameters are consistent")

        elif not _is_lo:
            _logger.warning("LO synthesizer not founded")
        elif not _is_clk:
            _logger.warning("CLK synthesizer not founded")

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
            assert network_config[n_roaches[roach_1]]["roach_ppc_ip"] != network_config[n_roaches[roach_2]]["roach_ppc_ip"],  _logger.warning("There is a roach IP conflict. There are two roaches with the same IP address: " + n_roaches[roach_1] + "," + n_roaches[roach_2])

            assert network_config[n_roaches[roach_1]]["udp_source_ip"] != network_config[n_roaches[roach_2]]["udp_source_ip"],  _logger.warning("There is a UDP source IP conflict. There are two roaches with the same IP source address: " + n_roaches[roach_1] + "," + n_roaches[roach_2])
            assert network_config[n_roaches[roach_1]]["udp_source_mac"] != network_config[n_roaches[roach_2]]["udp_source_mac"],  _logger.warning("There is a UDP source MAC conflict. There are two roaches with the same MAC source address: " + n_roaches[roach_1] + "," + n_roaches[roach_2])

            #assert network_config[n_roaches[roach_1]]["udp_dest_ip"] != network_config[n_roaches[roach_2]]["udp_dest_ip"],  _logger.warning("There is a UDP dest IP conflict. There are two roaches with the same IP dest address: " + n_roaches[roach_1] + "," + n_roaches[roach_2])
            #assert network_config[n_roaches[roach_1]]["udp_dest_mac"] != network_config[n_roaches[roach_2]]["udp_dest_mac"],  _logger.warning("There is a UDP dest MAC conflict. There are two roaches with the same MAC dest address: " + n_roaches[roach_1] + "," + n_roaches[roach_2])
            #assert network_config[n_roaches[roach_1]]["udp_dest_device"] != network_config[n_roaches[roach_2]]["udp_dest_device"],  _logger.warning("There is a UDP device conflict. There are two roaches with the same UDP device address: " + n_roaches[roach_1] + "," + n_roaches[roach_2])

        start_comp += 1

    _logger.info("ROACH network parameters. No conflicts founded")

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
                _logger.info(roach + "-" + device + " is defined in network interface. IP and MAC address match")
            if not ip_flag:
                _logger.warning(roach + "-" + device + ". The IP of the device doesn't match with the configuration file.")
            if not mac_flag:
                _logger.warning(roach + "-" + device + ". MAC address of the device doesn't match with the configuration file.")
        else:
            _logger.warning(roach + "-" + device + " is not defined in network interface.")
            raise Exception(roach + "-" + device + " is not defined in network interface.")


def _num_roaches(dict_file):
    """
    Number of Roaches defined in the configuration files
    """
    return [n for n in dict_file.keys() if type(dict_file[n]) == dict]
    # return dict_file.keys()

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
    m = match(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$", ip)
    return bool(m) and all(map(lambda n: 0 <= int(n) <= 255, m.groups()))

def _is_valid_mac(mac):
    m = _re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", mac.lower())
    return bool(m)

def verify_all_config(general_config, hardware_config, filesys_config, network_config, roach_config):
    verify_general_config(general_config)
    verify_hardware_config(hardware_config)
    verify_filesys_config(filesys_config)
    verify_network_config(network_config)
    verify_config_consistency(roach_config, network_config, hardware_config)

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

############## Roach firmware registers ##############
firmware_registers = _os.path.join(config_dir, 'firmware_registers.cfg')

assert _os.path.exists(firmware_registers)
firmware_registers = load_config_file(firmware_registers)

############## e.g. to Run verification #####################
# verify_all_config(general_config, hardware_config, filesys_config, network_config, roach_config)
