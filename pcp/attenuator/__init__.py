#!/usr/bin/env python

# Init script used to configure and make available the attenuator modules

import sys as _sys, os as _os, inspect as _inspect

import attenuatorclasses

_cwd = _os.path.dirname(__file__)

_modlist = [ _os.path.join(_cwd, _f)    for _f in _os.listdir(_cwd) if _os.path.splitext(_f)[-1] == ".py" ]
__all__  = [ _os.path.basename(_f)[:-3] for _f in _modlist          if _os.path.isfile(_f) and not _f.endswith('__init__.py')]

# create a dictionary of available synth device modules that will be used by lib_hardware
# to create synth device and source objects according to the information in the configuration files
ATTEN_HW_DICT = {}

for classname, attenobj in _inspect.getmembers(attenuatorclasses, _inspect.isclass):
    if not hasattr(attenobj,'MODELNUMS'):
        continue
    for modelnum in getattr(attenobj, "MODELNUMS"):
        # join vendor and model numbers (all lower case)
        ATTEN_HW_DICT[ "_".join( (getattr(attenobj, "VENDOR"), str(modelnum).lower() ) )] = attenobj
