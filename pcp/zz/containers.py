"""

Place where the main class definitions that are used as containers

"""


from collections import namedtuple
import pprint

import casperfpga as _casperfpga

from configuration import filesys_config, general_config, roach_config, hardware_config, network_config

class roachobj(object):
    def __init__(self, roachid):
        """
        Main container object for the roach, which will contain all of the HW information for a single
        Roach. It will contain the following items:
            - fpga instance (allows direct communiation with the fpga)

        """
        # make some assertions to catch basic errors
        assert type(roachid) is str, "roachid is not a string"
        assert roachid in network_config.keys()                # check that roachid matches one of the configuration file entries

        self.roachid = roachid
        # read configuration files, which should all be based on roachid
        
        #
        self.fpga =

    def _initialise_fpga(self):
        try:
            self.fpga = _casperfpga.katcp_fpga.KatcpFpga(ppc_ipaddr, timeout = 120);

        except RuntimeError:
            print "No connection to ROACH."
            return None

#
# # dummy object - this will be defined in katcp
# class fpga(object):
#     def __init__(self, id):
#         self.x = 1
#         self.name = id
#
# fpgaids = ['roach{0}'.format(i) for i in range(3)] # will be read from configuration files
#FPGAlist = namedtuple('FPGAlist', fpgaids) # container to hold multiple instances will eventually be imported from .core

# class FPGAlist( namedtuple('FPGAlist', fpgaids) ):
#     def show(self):
#         pprint.pprint(self._fields)
#
# class Containerlist( object ):
#     def __init__(self, listname, listitems):
#         for item in listitems:
#             setattr(self, item, item)
#
#     def show(self):
#         pprint.pprint(self._fields)


# class SYNTHlist( namedtuple('SYNTHlist', synthids) ):
#     def show(self):
#         pprint.pprint(self._fields)
#
#
#
# fpgas = FPGAlist( *[fpga(id) for id in fpgaids] )
#
# def plusone(fpgalist):
#     assert type(fpgalist) == FPGAlist
#     for item in fpgalist:
#         item.x+=1
