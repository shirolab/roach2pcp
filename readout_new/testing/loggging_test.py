import logging
import os, sys

import yaml
# attempt to debug the behviour of the logging configuration that I don't understand

filename = os.path.join('/Users/PeteBarry/Documents/AnalysisCode/multitone/readout_new/testing/run/example.log')

logging.basicConfig( \
                filename = os.path.abspath(filename), \
                format = "%(relativeCreated)5d %(name)-15s %(levelname)-8s %(message)s",\
                level=logging.INFO)

logger = logging.getLogger('') # gets the root logger
logging.info('Jackdaws love my big sphinx of quartz.')


with open("readout_new/configuration/network_config.yml") as x:
    y = yaml.safe_load(x)
    logging.warning('File opened')
