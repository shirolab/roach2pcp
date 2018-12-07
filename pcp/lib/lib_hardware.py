#

from ..configuration import hardware_config, roach_config

from ..synthesizer import SYNTH_HW_DICT as _SYNTH_HW_DICT
#from ..synthesizer import synth_class_dict

from collections import namedtuple as _namedtuple
_synthObj = _namedtuple("synthObj", ["config", "synthobj"])

def initialise_connected_synths():
    """
    Function to initialise and return a set of synthesiser objects according to
    parameters given in the configuration file.

    Returns
    -------
    synth_dict : dict
        Dictionary containing all the synthesizer objects that are defined and active in the
        hardware configuration file

    Notes
    -----
    Does a number of checks to ensure that the synths are initialised correctly, and are working

    """

    # read in synth configuration (make copies here to not alter the live configuration dict, may not be a bad thing?)
    synth_config = hardware_config["synth_config"].copy()
    roach_params = roach_config["roach_params"].copy()
    
    # for each entry, return the key, if active is true
    for key, cfg in synth_config.items():
        if cfg["active"] is not True:
            del synth_config[key]

    # should only be left with active - check that its not empty, and is the number
    # defined in roach_config

    # get the unique synthids defined in the roach_config for both lo and clocks (clocks can be None, and will be discarded)
    synthids = set([roach[key] for roach in roach_params.values() \
                                for key in roach.keys() if key.startswith("synthid") if roach[key] is not None])	
    print '\n\n synthids',synthids
    # compare and check that all synthids are in the active synth_config dict
    synth_check = synthids.difference(synth_config.keys()) # should be empty

    if len(synth_check) > 0:
        raise RuntimeError,\
        "synthids = {synthids} are not present/active in the configuration files. Please check that each roach has an active synth \
entry in the configuration files and try again.".format(synthids=list(synth_check))
        return

    # return a dictionary with initilased synth objects

    synth_object_dict = dict.fromkeys(synth_config, None)
    print '\n\n _SYNTH_HW_DICT',_SYNTH_HW_DICT
    
    for synthid, synthcfg in synth_config.items():
        # replace None with instantiated synthesiser object

        # need dictionary of synth objects from synthesier
        synth_dict_key = "_".join((synthcfg['vendor'], str(synthcfg['modelnum']))).lower()
        print '\n',synthid,synthcfg,synth_dict_key
    
        synth_object_dict[synthid] = _synthObj(config = synthcfg, synthobj = _SYNTH_HW_DICT[synth_dict_key] )
        #synth_object_dict[synthid] = (synthcfg, _SYNTH_HW_DICT[synth_dict_key])# initialise_synth(synth_config[synthid])

        # need initialise_synth function!
    return synth_object_dict

# create synth object dict that is initialised and can be used by everything else

# have simple reload() function to reinitialise hardware on demand
