#
#stdlib imports
import logging as _logging, time as _time, threading as _threading
_logger = _logging.getLogger(__name__)

from collections import namedtuple as _namedtuple
_synthObj = _namedtuple("synthObj", ["config", "synthobj"])
_attenObj = _namedtuple("attenObj", ["config", "attenobj"])

# relative pcp imports
from ..configuration import hardware_config, roach_config, color_msg as cm
#from pcp.configuration import hardware_config, roach_config

from ..synthesizer import SYNTH_HW_DICT as _SYNTH_HW_DICT
_logger.debug("synth dict : {0}".format( _SYNTH_HW_DICT ) )

from ..attenuator import ATTEN_HW_DICT as _ATTEN_HW_DICT
_logger.debug("atten dict : {0}".format( _ATTEN_HW_DICT ) )

#from pcp.synthesizer import SYNTH_HW_DICT as _SYNTH_HW_DICT
#from ..synthesizer import synth_class_dict

class usb_detector():
    ''' Monitor udev for detection of usb '''

    def __init__(self):
        ''' Initiate the object '''
        thread = _threading.Thread(target=self._work)
        thread.daemon = True
        thread.start()

    def _work(self):
        self.context = _udev.Context()
        self.monitor = _udev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem='usb')
        self.monitor.start()

        # This run in a loop
        for device in iter(self.monitor.poll, None):
            # Check how emit signal
            if device.action == 'add':
                print cm.OKGREEN + "Device connected" + cm.ENDC
            else:
                print cm.WARNING + "Device removed" + cm.ENDC

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
    #roach_params = roach_config["roach_params"].copy()
    roach_params = roach_config.copy()

    # for each entry, return the key, if active is true
    for key, cfg in synth_config.items():
        if cfg["active"] is not True:
            del synth_config[key]

    # should only be left with active - check that its not empty, and is the number
    # defined in roach_config
    _logger.debug("synth_config: {0}".format( synth_config ) )
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

    #print synth_config

    #identify physical synth devices, not repeating entries for multi-port devices
    _logger.debug("identifying physical synthesier devices..." )

    psynth_dict = {}
    for synthid, synthcfg in synth_config.items():
        vendor = str(synthcfg['vendor']).lower()
        model = str(synthcfg['model']).lower()
        serial = str(synthcfg['serial'])
        if serial in [None, 'none', '']:
            physical_id = vendor + '_' + model
        else:
            physical_id = vendor + '_' + model + '_' + serial
        psynth_dict[physical_id] = {'vendor':vendor, 'model':model, 'serial':serial}
        psynth_dict[physical_id]['class_key'] = vendor + '_' + model
        synth_config[synthid]['physical_id'] = physical_id

    _logger.debug("instantiating synth classes..." )

    #instantiate the synth base classes for each physical device
    psynth_device_instances = {}
    for psynth in psynth_dict:
        synth_dict_key = psynth_dict[psynth]['class_key']
        synth_dict_serial = psynth_dict[psynth]['serial']

        if synth_dict_serial.lower() == 'none':
            synth_dict_class = _SYNTH_HW_DICT[synth_dict_key]
            psynth_device_instances[psynth] = synth_dict_class()
        else:
            synth_dict_class = _SYNTH_HW_DICT[synth_dict_key](synth_dict_serial)
            psynth_device_instances[psynth] = synth_dict_class

    # return a dictionary with initilased synth device objects
    synth_device_object_dict = dict.fromkeys(synth_config, None)
    synth_source_object_dict = dict.fromkeys(synth_config, None)
    #print '\n\n _SYNTH_HW_DICT',_SYNTH_HW_DICT
    #print '\n\n _synth_object_dict',synth_object_dict

    _logger.debug("creating synth objects..." )

    for synthid, synthcfg in synth_config.items():

        #get the right labels
        physical_id = synthcfg['physical_id']
        synth_dict_key = "_".join((synthcfg['vendor'], str(synthcfg['model']))).lower()
        #print ('\n',synthid,synthcfg,synth_dict_key)

        #add the synth device object to a dict
        _logger.debug("adding device object {0}".format(synthid) )
        synth_device_object_dict[synthid] = _synthObj(config = synthcfg, synthobj = psynth_device_instances[physical_id])

        #add the synth source object to a dict
        _logger.debug("adding source object {0}".format(synthid) )
        synth_source_object_dict[synthid] = _synthObj(config = synthcfg, synthobj = psynth_device_instances[physical_id].getSourceObj(channel=synthcfg['channel']))

        #NOTE: the synth object is currently a device-like object, but could be source-like to match the valon/windfreak drivers.

        #print ('\n\n synth_device_object_dict[synthid]',synth_device_object_dict[synthid])
        #print ('\n\n synth_source_object_dict[synthid]',synth_source_object_dict[synthid])

    return synth_source_object_dict

# create synth object dict that is initialised and can be used by everything else

# have simple reload() function to reinitialise hardware on demand

def initialise_connected_attens():
    """
    Function to initialise and return a set of attenuator objects according to
    parameters given in the configuration file.

    Returns
    -------
    synth_dict : dict
        Dictionary containing all the attenuator objects that are defined and active in the
        hardware configuration file.

    """

    # read in attenuators configuration (make copies here to not alter the live configuration dict, may not be a bad thing?)
    atten_config = hardware_config["atten_config"].copy()
    #roach_params = roach_config["roach_params"].copy()
    roach_params = roach_config.copy()

    # for each entry, return the key, if active is true
    for key, cfg in atten_config.items():
        if cfg["active"] is not True:
            del atten_config[key]

    # should only be left with active - check that its not empty, and is the number
    # defined in roach_config

    # get the unique attenids defined in the roach_config for both in and out
    attenids = set([roach[key] for roach in roach_params.values() \
                                for key in roach.keys() if key.startswith("att_") if roach[key] is not None])

    # compare and check that all attenids are in the active atten_config dict
    atten_check = attenids.difference(atten_config.keys()) # should be empty

    if len(atten_check) > 0:
        raise RuntimeError,\
        "attenids = {attenids} are not present/active in the configuration files. Please check that each roach has an active attenuator \
entry in the configuration files and try again.".format(attenids=list(atten_check))
        return

    #identify physical synth devices, not repeating entries for multi-port devices
    patten_dict = {}
    for attenid, attencfg in atten_config.items():
        vendor = str(attencfg['vendor']).lower()
        model = str(attencfg['model']).lower()
        serial = str(attencfg['serial'])
        if serial in [None, 'none', '']:
            physical_id = vendor + '_' + model
        else:
            physical_id = vendor + '_' + model + '_' + serial
        patten_dict[physical_id] = {'vendor':vendor, 'model':model, 'serial':serial}
        patten_dict[physical_id]['class_key'] = vendor + '_' + model
        atten_config[attenid]['physical_id'] = physical_id


    #instantiate the synth base classes for each physical device
    patten_device_instances = {}

    for patten in patten_dict:
        atten_dict_key = patten_dict[patten]['class_key']
        atten_dict_serial = patten_dict[patten]['serial']

        #dummy attenuators
        if atten_dict_serial.lower() == 'none':
            atten_dict_class = _ATTEN_HW_DICT[atten_dict_key]
            patten_device_instances[patten] = atten_dict_class()
        #other attenuators
        else:
            atten_dict_class = _ATTEN_HW_DICT[atten_dict_key](atten_dict_serial)
            patten_device_instances[patten] = atten_dict_class

    atten_device_object_dict = dict.fromkeys(atten_config, None)
    atten_source_object_dict = dict.fromkeys(atten_config, None)

    for attenid, attencfg in atten_config.items():

        #get the right labels
        physical_id = attencfg['physical_id']
        atten_dict_key = "_".join((attencfg['vendor'], str(attencfg['model']))).lower()

        #add the synth device object to a dict
        atten_device_object_dict[attenid] = _attenObj(config = attencfg, attenobj = patten_device_instances[physical_id])

        #add the synth source object to a dict
        atten_source_object_dict[attenid] = _attenObj(config = attencfg, attenobj = patten_device_instances[physical_id].getSourceObj(channel=attencfg['channel']))

        #NOTE: the synth object is currently a device-like object, but could be source-like to match the valon/windfreak drivers.

        #print ('\n\n atten_device_object_dict[attenid]',atten_device_object_dict[attenid])
        #print ('\n\n atten_source_object_dict[attenid]',atten_source_object_dict[attenid])

    return atten_source_object_dict
