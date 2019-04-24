# Scripts to generate useful plots for kst monitoring
# Uses lower-level functions in ssMonitor.py

import ssMonitor

def plot_aux_data(client=None):

    if client != None:
        client.quit()
        
    df = ssMonitor.find_latestfile()
    client_name = 'aux_data'

    field_list = ['packet_count','pps_timestamp','fine_timestamp',
                  'roach_checksum','packet_info_reg']

    for fn in field_list:
        client = ssMonitor.plot_dirfile_rawfield(fn,
                                                 client_name = client_name,
                                                 datafile = df)
    return client


def plot_kidrange_mag(kidarray,df = None,client=None): # array of numbers

    if client != None:
        client.quit()

    if df == None:
        df = ssMonitor.find_latestfile()

    client_name = 'magnitude'

    chanlist = []
    for kk, kn in enumerate(kidarray):
        chanlist.append('K%03i' % kn)
        
    client = ssMonitor.plot_dirfile_IQequation(chanlist, df,
                                               client_name = client_name,
                                               eqnlist = ["mag"])

    return client

def plot_kidrange_phase(kidarray,df = None,client=None): # array of numbers

    if client != None:
        client.quit()

    if df == None:
        df = ssMonitor.find_latestfile()
        
    client_name = 'phase'

    chanlist = []
    for kk, kn in enumerate(kidarray):
        chanlist.append('K%03i' % kn)
        
    client = ssMonitor.plot_dirfile_IQequation(chanlist, df,
                                               client_name = client_name,
                                               eqnlist = ["phase"])

    return client

