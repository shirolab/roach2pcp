# Scripts to generate useful plots for kst monitoring
# Uses lower-level functions in ssMonitor.py

import ssMonitor

    
def plot_aux_data(df = 'latest', client=None):

    if client != None:
        ssMonitor.kill(client)

    if df == 'latest':
        df = '/home/superspec/Documents/ksk/multitone_20190419/pcp/kst/roach0_sf.txt'

    client_name = 'aux_data'

    field_list = ['packet_count','pps_timestamp','fine_timestamp',
                  'roach_checksum','packet_info_reg','gpio_reg']

    #for fn in field_list:
    client = ssMonitor.plot_dirfile_rawfield(field_list, df,
                                             client_name = client_name)
    return client


def plot_kidrange_mag(kidarray,df = 'latest',client=None): # array of numbers

    if client != None:
        ssMonitor.kill(client)

    if df == 'latest':
        df = '/home/superspec/Documents/ksk/multitone_20190419/pcp/kst/roach0_sf.txt'

    client_name = 'magnitude'

    chanlist = []
    for kk, kn in enumerate(kidarray):
        chanlist.append('K%03i' % kn)
        
    client = ssMonitor.plot_dirfile_IQequation(chanlist, df,
                                               client_name = client_name,
                                               eqnlist = ["mag"])

    return client

def plot_kidrange_phase(kidarray,df = 'latest',client=None): # array of numbers

    if client != None:
        ssMonitor.kill(client)

    if df == 'latest':
        df = '/home/superspec/Documents/ksk/multitone_20190419/pcp/kst/roach0_sf.txt'
        
    client_name = 'phase'

    chanlist = []
    for kk, kn in enumerate(kidarray):
        chanlist.append('K%03i' % kn)
        
    client = ssMonitor.plot_dirfile_IQequation(chanlist, df,
                                               client_name = client_name,
                                               eqnlist = ["phase"])

    return client

def plot_kidrange_x(kidarray, df = 'latest', client=None):

    if client != None:
        ssMonitor.kill(client)

    if df == 'latest':
        df = '/home/superspec/Documents/ksk/multitone_20190419/pcp/kst/roach0_sf.txt'
        
        
    client_name = 'x'

    chanlist = []
    for kk, kn in enumerate(kidarray):
        chanlist.append('K%03i' % kn)
        
    client = ssMonitor.plot_dirfile_IQequation(chanlist, df,
                                               client_name = client_name,
                                               eqnlist = ["x"])

    return client


def plot_roach0(df = 'latest', client=None):

    if client != None:
        ssMonitor.kill(client)

    if df == 'latest':
        df = '/home/superspec/Documents/ksk/multitone_20190419/pcp/kst/roach0_sf.txt'

    client_name = 'r0';
    
    # Plot aux_data
    field_list = ['packet_count','pps_timestamp','fine_timestamp',
                  'roach_checksum','packet_info_reg','gpio_reg']

    client = ssMonitor.plot_dirfile_rawfield(field_list, df,
                                             client_name = client_name)
    client.set_tab_text('r0_aux_data')

    client.new_tab()
    chanlist = ['K000','K001','K002','B000','B001','B002','B003','B004'];
    client = ssMonitor.plot_dirfile_IQequation(chanlist, df,
                                               client_name = client_name,
                                               eqnlist = ["x"])
    client.set_tab_text('r0_0-2, B0-4')

    client.new_tab()
    chanlist = ['K003','K004','K005','K006','K007','K008','K009','K010','K011']
    client = ssMonitor.plot_dirfile_IQequation(chanlist, df,
                                               client_name = client_name,
                                               eqnlist = ["x"])
    client.set_tab_text('r0_3-11')

    client.new_tab()
    chanlist = ['K012','K013','K014','K015','K016','K017','K018','K019','K020']
    client = ssMonitor.plot_dirfile_IQequation(chanlist, df,
                                               client_name = client_name,
                                               eqnlist = ["x"])
    client.set_tab_text('r0_12-20')

    # Tab 4
    client.new_tab()
    chanlist = ['K021','K022','K023','K024','K025','K026','K027','K028','K029']
    client = ssMonitor.plot_dirfile_IQequation(chanlist, df,
                                               client_name = client_name,
                                               eqnlist = ["x"])
    client.set_tab_text('r0_21-29')

    # Tab 5
    client.new_tab()
    chanlist = ['K030','K031','K032','K033','K034','K035','K036','K037','K038']
    client = ssMonitor.plot_dirfile_IQequation(chanlist, df,
                                               client_name = client_name,
                                               eqnlist = ["x"])
    client.set_tab_text('r0_30-38')

    # Tab 6
    client.new_tab()
    chanlist = ['K039','K040','K041','K042','K043','K044','K045','K046','K047']
    client = ssMonitor.plot_dirfile_IQequation(chanlist, df,
                                               client_name = client_name,
                                               eqnlist = ["x"])
    client.set_tab_text('r0_39-47')

    # Tab 7
    client.new_tab()
    chanlist = ['K048','K049','K050','K051','K052','K053']
    client = ssMonitor.plot_dirfile_IQequation(chanlist, df,
                                               client_name = client_name,
                                               eqnlist = ["x"])
    client.set_tab_text('r0_48-53')

    return client

def plot_roach0_sweep(sweepfile = None, client = None):

    if client != None:
        ssMonitor.kill(client)

    if sweepfile == None:
        sweepfile = ssMonitor.find_lastsweep()

    if client == None:
        client_name = 'sweep_' + sweepfile[-21:-6]

    # Tab 1: broadband
    chanlist = ['K000','K001','K002','B000','B001','B002','B003','B004']
    client = ssMonitor.plot_sweep(chanlist, sweepfile, client_name)
    client.set_tab_text('r0_0-2, B0-4')

    # Tab 2
    client.new_tab()
    chanlist = ['K003','K004','K005','K006','K007','K008','K009','K010','K011']
    client = ssMonitor.plot_sweep(chanlist, sweepfile, client_name)
    client.set_tab_text('r0_3-11')

    # Tab 3
    client.new_tab()
    chanlist = ['K012','K013','K014','K015','K016','K017','K018','K019','K020']
    client = ssMonitor.plot_sweep(chanlist, sweepfile, client_name)
    client.set_tab_text('r0_12-20')

    # Tab 4
    client.new_tab()
    chanlist = ['K021','K022','K023','K024','K025','K026','K027','K028','K029']
    client = ssMonitor.plot_sweep(chanlist, sweepfile, client_name)
    client.set_tab_text('r0_21-29')

    # Tab 5
    client.new_tab()
    chanlist = ['K030','K031','K032','K033','K034','K035','K036','K037','K038']
    client = ssMonitor.plot_sweep(chanlist, sweepfile, client_name)
    client.set_tab_text('r0_30-38')

    # Tab 6
    client.new_tab()
    chanlist = ['K039','K040','K041','K042','K043','K044','K045','K046','K047']
    client = ssMonitor.plot_sweep(chanlist, sweepfile, client_name)
    client.set_tab_text('r0_39-47')

    # Tab 7
    client.new_tab()
    chanlist = ['K048','K049','K050','K051','K052','K053']
    client = ssMonitor.plot_sweep(chanlist, sweepfile, client_name)
    client.set_tab_text('r0_48-53')

    return client
    
