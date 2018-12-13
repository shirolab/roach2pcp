#

from ..configuration import hardware_config, roach_config
#from pcp.configuration import hardware_config, roach_config

from ..synthesizer import SYNTH_HW_DICT as _SYNTH_HW_DICT
#from pcp.synthesizer import SYNTH_HW_DICT as _SYNTH_HW_DICT

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

    #print '\n\n synthids',synthids

    # compare and check that all synthids are in the active synth_config dict
    synth_check = synthids.difference(synth_config.keys()) # should be empty

    if len(synth_check) > 0:
        raise RuntimeError,\
        "synthids = {synthids} are not present/active in the configuration files. Please check that each roach has an active synth \
entry in the configuration files and try again.".format(synthids=list(synth_check))
        return

    
    #identify physical synth devices, not repeating entries for multi-port devices
    psynth_dict = {}
    for synthid, synthcfg in synth_config.items():
        vendor = str(synthcfg['vendor']).lower()
        model = str(synthcfg['model']).lower()
        serial = str(synthcfg['serial']).lower()
        if serial in [None, 'none', '']:
            physical_id = vendor + '_' + model
        else:
            physical_id = vendor + '_' + model + '_' + serial
        psynth_dict[physical_id] = {'vendor':vendor, 'model':model, 'serial':serial}
        psynth_dict[physical_id]['class_key'] = vendor + '_' + model  
        synth_config[synthid]['physical_id'] = physical_id
    print psynth_dict
    
    #instantiate the synth base classes for each physical device
    psynth_device_instances = {}
    for psynth in psynth_dict:
        synth_dict_key = psynth_dict[psynth]['class_key']
        synth_dict_class = _SYNTH_HW_DICT[synth_dict_key]
        print psynth, synth_dict_key, synth_dict_class
        psynth_device_instances[psynth] = synth_dict_class() 
        
    
    # return a dictionary with initilased synth device objects
    synth_device_object_dict = dict.fromkeys(synth_config, None)
    synth_source_object_dict = dict.fromkeys(synth_config, None)
    #print '\n\n _SYNTH_HW_DICT',_SYNTH_HW_DICT
    #print '\n\n _synth_object_dict',synth_object_dict
    
    for synthid, synthcfg in synth_config.items():

        #get the right labels
        physical_id = synthcfg['physical_id']
        synth_dict_key = "_".join((synthcfg['vendor'], str(synthcfg['model']))).lower()
        print ('\n',synthid,synthcfg,synth_dict_key)
    
        #add the synth device object to a dict
        synth_device_object_dict[synthid] = _synthObj(config = synthcfg, synthobj = psynth_device_instances[physical_id])
        
        #add the synth source object to a dict
        synth_source_object_dict[synthid] = _synthObj(config = synthcfg, synthobj = psynth_device_instances[physical_id].getSourceObj(channel=synthcfg['channel']))

        #NOTE: the synth object is currently a device-like object, but could be source-like to match the valon/windfreak drivers.
        
        print ('\n\n synth_device_object_dict[synthid]',synth_device_object_dict[synthid])
        print ('\n\n synth_source_object_dict[synthid]',synth_source_object_dict[synthid])
        
    return synth_source_object_dict

# create synth object dict that is initialised and can be used by everything else

# have simple reload() function to reinitialise hardware on demand
