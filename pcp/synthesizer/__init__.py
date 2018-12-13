#!/usr/bin/env python

# Init script used to configure and make available the synthesiser modules

# Each fie
import sys as _sys, os as _os, inspect as _inspect

import synthclasses

_cwd = _os.path.dirname(__file__)

_modlist = [ _os.path.join(_cwd, _f) for _f in _os.listdir(_cwd) if _os.path.splitext(_f)[-1] == ".py" ]
__all__ = [ _os.path.basename(_f)[:-3] for _f in _modlist if _os.path.isfile(_f) and not _f.endswith('__init__.py')]

#print _modlist

# import all modules found by __all__

# create a dictionary of available synth modules that will be used by lib_hardware
# to create synth objects according to the information in the configuration files
SYNTH_HW_DICT = {}

for classname, synthobj in _inspect.getmembers(synthclasses, _inspect.isclass):
    if not hasattr(synthobj.'MODELNUMS'):
        continue
    for modelnum in getattr(synthobj, "MODELNUMS"):
        # join vendor and model numbers (all lower case)
        SYNTH_HW_DICT[ "_".join( (getattr(synthobj, "VENDOR"), str(modelnum).lower() ) )] = synthobj
#print 'synthesizer:__init__.py SYNTH_HW_DICT:', SYNTH_HW_DICT
