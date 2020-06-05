#!/usr/bin/env python

# initialisation of the "scripts" submodule.

# Each script file should contain a main() function that runs the 'script'. This function is then imported here
# and attached to the original module name. A handle to the original module is stored and hidden for debugging purposes.

# Please have the first line in each script be a log message saying the name of the script!  e.g.
#     _logger.info('SCRIPT: my_script_name')
# so that it's obvious in the log exactly when the script was started

# dynamically import the main() function from each file contained in this directory and
import sys as _sys, time as _time, pkgutil as _pkgutil, logging as _logging

import pcp

_logger = _logging.getLogger(__name__)

# get a list of all scripts, filtering out files beginning with double underscore
_allmods = [p for p in _pkgutil.iter_modules(__path__) if p[1].startswith('__') ]
del(p)

for _importer, _modname, _ispkg in _allmods:
    # imports the script as hidden variable (for debugging), and imports script.main() for convenience
    try:
        exec("import {name} as _{name}; from .{name} import main as {name}".format( name = _modname ) )
    except ImportError:
        raise ImportError, 'error importing module - {mod}'.format(mod = _modname)

def reload_scripts():
    # reload all files in this directory
    for _, _modname, _ in _allmods:
        _fullname = ".".join( (__name__,_modname) )
        reload( _sys.modules[_fullname] )
        _logger.info( "Module {0} reloaded".format(_fullname) )
   # reload this module
    reload(_sys.modules[__name__])
    _logger.info( "Module {0} reloaded".format(__name__) )
    _time.sleep(0.1)
