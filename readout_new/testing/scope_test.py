
# To both handle the relative import correctly for use in the module and test the script, you can do one of the following:

#   1. from the command line, use python -m readout_new.testing.scope_test. In this case, __name__ == "__main__".
#   2. Alternatively, from ipython, you can from readout_new.testing import scope_test. In this case __name__ == "readout_new.testing.scope_test"


from ..configuration import filesys_config

print filesys_config.config.items()

testvar = 'this is defined outside the class'

class testClass(object):
    def __init__(self, x):
        print "class instatiated with x={0}\n".format(x)
        print testvar
if __name__ == "__main__":
    testClass(2)
