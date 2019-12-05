#!/usr/bin/env python

# initialisation of the "scripts" submodule.

# Each script file should contain a main() function that runs the 'script'. This function is then imported here
# and attached to the original module name. A handle to the original module is stored and hidden for debugging purposes.


# dynamically import the main() function from each file contained in this directory and
import pkgutil as _pkgutil

for _importer, _modname, _ispkg in _pkgutil.iter_modules(__path__):

    if _modname != "removeCR" and _modname != "data_cardiff_lab":
	    # imports the script as hidden variable (for debugging), and imports script.main() for convenience
	    exec("import {name} as _{name};\
	        from .{name} import main as {name}".format( name=_modname ) )
