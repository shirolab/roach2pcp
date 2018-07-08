"""

Place where the main class definitions that are used as containers

"""


from collections import namedtuple
import pprint

# dummy object - this will be defined in katcp
class fpga(object):
    def __init__(self, id):
        self.x = 1
        self.name = id

fpgaids = ['roach{0}'.format(i) for i in range(3)] # will be read from configuration files
#FPGAlist = namedtuple('FPGAlist', fpgaids) # container to hold multiple instances will eventually be imported from .core

class FPGAlist( namedtuple('FPGAlist', fpgaids) ):
    def show(self):
        pprint.pprint(self._fields)

class Containerlist( object ):
    def __init__(self, listname, listitems):
        for item in listitems:
            setattr(self, item, item)

    def show(self):
        pprint.pprint(self._fields)


# class SYNTHlist( namedtuple('SYNTHlist', synthids) ):
#     def show(self):
#         pprint.pprint(self._fields)
#
#

fpgas = FPGAlist( *[fpga(id) for id in fpgaids] )

def plusone(fpgalist):
    assert type(fpgalist) == FPGAlist
    for item in fpgalist:
        item.x+=1
