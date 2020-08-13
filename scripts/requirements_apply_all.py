#!/usr/bin/python


"""
Runs 'pip install --user' for each item in the requirements file/

Need to be run from with the scripts directory otherwise it wont find the requirements file
"""


import os

filename = '../requirements.txt'

if not os.path.exists(filename):
    print('Error: Requirements file not found. Exiting.' )
    exit()
    
with open(filename,'r') as file:
    lines = file.readlines()
    for l in lines:
        os.system('pip install --user %s'%(l.strip()))
    print('Done. Exiting.')
exit()
