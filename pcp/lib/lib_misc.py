
import logging as _logging
_logger = _logging.getLogger(__name__)

## MOVE THIS OUT OF INIT - maybe create file called funcs_convenience
def reload_all_packages():
    """Helper function to reload all submodules interactively. Useful for debugging, and
    reloading configuration files. Currently, only reloads top level packages.
     """

    current_module = _sys.modules[__name__]

    print "Reloading submodules..."
    for importer, modname, ispkg in _pkgutil.iter_modules(current_module.__path__):
        if ispkg:
            _time.sleep(0.1)
            print "Reloading", current_module.__name__, modname
            reload( _sys.modules[getattr(current_module, modname).__name__] )
    print "Done."
    reload(_sys.modules[__name__])


def help_screen():
    print "this is a printed message "
    _logger.info("this is a logged message ")
