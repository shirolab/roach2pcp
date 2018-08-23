#

# pcp dirfile standards
# maindirfile
#   - sweepdirfile
#- calfrag constants from sweep fragment (di/df, dq/df, i0, q0 )
#- K### x Ntones (timestreams)
#- S### x Ntones (sweeps)
#- TONES -> derived fields to constant can easily be configured
# timing info x 7?

# TODO:
# - find a neat way of reading field lists from configuration file

# create a new dirfile, and populate with correct fieldnames
import os, sys, numpy as np
import pygetdata as _gd
from ..configuration import roach_config
from . import lib_datapackets

def create_pcp_dirfile(dirfilename, ntones, *dirfileflags):
    """
    High level function to create a new dirfile according to the pcp standards. This creates a format file with a number of tones
    (to be standardised), and other packet information, read from roach_config (to be implmented).

    It then creates a new dirfile, that contains an empty sweep sweep dirfile (which has an identical format file). This sweep dirfile
    will be used to store the raw data from a sweep, and will then be used to store a reduced version by the sweep function.


    """
    #
    # parse user specified set of dirfile flags, else use defaults (note _gd.EXCL prevents accidental overwriting)
    dirfileflagint = np.bitwise_or.reduce(dirfileflags) if dirfileflags \
                                                        else _gd.CREAT|_gd.RDWR|_gd.UNENCODED|_gd.EXCL
    # create dirfile
    maindirfile = _gd.dirfile(dirfilename, dirfileflagint)
    # add main fields
    maindirfile = generate_main_rawfields(maindirfile, ntones)

    # create sweep subdirfile
    sweepdirfilename = os.path.join(maindirfile.name, "sweep")
    sweepdirfile = _gd.dirfile(sweepdirfilename, dirfileflagint)

    sweepdirfile = generate_main_rawfields(sweepdirfile, ntones, fragnum = 0, datatag = "_swp")

    swpfragment = maindirfile.include("sweep_data", flags = _gd.CREAT|_gd.EXCL|_gd.RDWR)


    #raw_sweep_frag = maindirfile.include(os.path.join( os.path.basename(sweepdirfilename), "format"), flags = _gd.RDWR|_gd.CREAT)

    # add sweep files that will be saved later ()

    # include sweep format file to maindir. Note that adds a fragment_index = 1 for the sweep
    #maindirfile.include("sweep_data", flags = _gd.CREAT|_gd.EXCL|_gd.RDWR)


    # set up sweep fields in main directory - can we calculate from derived fields?
    #maindirfile.add(gd.entry( _gd.RAW_ENTRY, K000_LO, 0,(_gd.FLOAT64, 1) ))
    return maindirfile, sweepdirfile
    # derived fields
    # calbration fragment
def create_dirfile(dirfilename, ntones, *dirfile_creation_flags):
    """
    High level function to create a new dirfile according to the pcp standards. This creates a format file with a number of tones
    (to be standardised), and other packet information, read from roach_config (to be implmented).
    """
    #
    # parse user specified set of dirfile flags, else use defaults (note _gd.EXCL prevents accidental overwriting)
    dirfileflagint = np.bitwise_or.reduce(dirfileflags) if dirfile_creation_flags \
                                                        else _gd.CREAT|_gd.RDWR|_gd.UNENCODED|_gd.EXCL
    # create dirfile
    dirfile = _gd.dirfile(dirfilename, dirfileflagint)
    # add main fields according to
    dirfile = generate_main_rawfields(maindirfile, ntones)

    return dirfile

def generate_main_rawfields(dirfile, ntones, fragnum=0, datatag=""):
    # function to generate a standard set of dirfile entries for the roach readout
    # will be used for both timestreams and raw sweep files

    # fields to save (read from config file?) # note first field will set which field is the "reference" (also from config file)
    # aux_fields = {
    #             "raw_packet" :(_gd.STRING_ENTRY, None), # save raw packets as strings (requires no type parameter)
    #             "python_timestamp" :(_gd.RAW_ENTRY, _gd.UINT32), # rough python timestamp in seconds after epoch (see kidpy )
    #             "pps_timestamp" :(_gd.RAW_ENTRY, _gd.UINT32), # seconds elapsed since 'pps_start'
    #             "fine_timestamp" :(_gd.RAW_ENTRY, _gd.UINT32), # milliseconds since PPS
    #             "packet_count" :(_gd.RAW_ENTRY, _gd.UINT32), # packet count since 'pps_start'
    #             "packet_info_reg":(_gd.RAW_ENTRY, _gd.UINT32),  # 32-bit int written to the info_register
    #             "roach_checksum" :(_gd.RAW_ENTRY, _gd.UINT32),
    #             "gpio_reg" :(_gd.RAW_ENTRY, _gd.UINT8) # hardware controlled 8-bit gpio pins
    #             }

    aux_fields = roach_config["PACKETSTRUCT"]["field_list"]
    aux_entries_to_write = []

    for field_name, (entry_type, field_datatype, __, __, __) in aux_fields.items():
        print eval(entry_type), eval(field_datatype)
        aux_entries_to_write.append( _gd.entry( eval(entry_type), field_name + datatag, fragnum, (eval(field_datatype), 1)) ) # field_type, name, fragment_idx, (data_type, sample_rate)

    # kst can't read complex numbers easily - so save as I, Q onto disk (would prefer complex data here though )
    kid_fields_I = ["K{kidnum:04d}_I{datatag}".format(kidnum=i, datatag=datatag) for i in range(ntones)]
    kid_fields_Q = ["K{kidnum:04d}_Q{datatag}".format(kidnum=i, datatag=datatag) for i in range(ntones)]

    kid_entries_to_write = [ _gd.entry(_gd.RAW_ENTRY, field_name, fragnum, (_gd.FLOAT64, 1)) for field_name in kid_fields_I ] \
                         + [ _gd.entry(_gd.RAW_ENTRY, field_name, fragnum, (_gd.FLOAT64, 1)) for field_name in kid_fields_Q ]

    # add all entries into format file
    for entry in aux_entries_to_write + kid_entries_to_write:
        dirfile.add(entry)

    dirfile.sync()
    return dirfile
    # alternative method to generate field specification (same data as above, but in different order)
    #                name  field_type data_type, sample_rate

def generate_main_derivedfields(dirfile):
    pass


def gen_sweepdirfile_fields(dirfile, ntones, fragnum=0, datatag=""):
    """Add additional fields for the sweep to the sweepdirfile """
    # can get rid of F files, as the frequency should be the same for all
    #swp_fields_F = ["SWP_F_K{kidnum:04d}{datatag}".format(kidnum=i, datatag=datatag) for i in range(ntones)]
    swp_fields_I = ["SWP_I_K{kidnum:04d}{datatag}".format(kidnum=i, datatag=datatag) for i in range(ntones)]
    swp_fields_Q = ["SWP_Q_K{kidnum:04d}{datatag}".format(kidnum=i, datatag=datatag) for i in range(ntones)]

    sweep_entry_freq       =   _gd.entry(_gd.CARRAY_ENTRY, "SWP_FREQ", fragnum, (_gd.FLOAT64, 501))

    sweep_entries_to_write = [ _gd.entry(_gd.CARRAY_ENTRY, field_name, fragnum, (_gd.FLOAT64, 501)) for field_name in swp_fields_I ] \
                            +[ _gd.entry(_gd.CARRAY_ENTRY, field_name, fragnum, (_gd.FLOAT64, 501)) for field_name in swp_fields_Q ]

    #return sweep_entries_to_write
    for entry in [sweep_entry_freq] + sweep_entries_to_write:
        dirfile.add(entry)

    return dirfile

def check_dirfile_is_empty(dirfile):
    """Returns True if dirfile is empty (len(INDEX) == 0), otherwise, False"""
    # get the size of the INDEX field
    return len( dirfile.getdata("INDEX") ) == 0

def add_subdirfile_to_existing_dirfile(dirfile, subdirfile, overwrite=False):
    """
    Function to add a subdirfile to an existing dirfile.

    Will check to see if one already exists, and if empty, replace with the new one. If not,
    rename existing file and add this.

    Mainly used to add multiple sweep dirfiles to a main dirfile.

    """
    pass



    # depends on how this is going to be written
    # if we assume that all data is going to be written, then it should look the same as the main dirfile
    #I000 - for all LO points
    #Q000 - ""
    #    - then need to extract
# Functions used to handle dirfile data saving
def gen_dirfilehandle(dirfilename, *dirfileflags):
    """

    Function to generate new dirfile with name , and return a handle to the new file.

    """
    # check to see if current handle is a valid open file, and close as appropriate
    # TODO read from stdin to get a filename ID to add to
    # test encodings to see if the data size can be reduced significantly

    # create new file as appropriate, with file name format as YYYYMMDD_HHMMSS_OBS (can be redefined if required)

    dirfileflagint = np.bitwise_or.reduce(dirfileflags) if dirfileflags \
                                                        else _gd.CREAT|gd.RDWR|gd.UNENCODED|gd.EXCL
    try:
        dirfilehandle = _gd.dirfile( dirfilename, dirfileflagint )
        return dirfilehandle

    except _gd.ExistsError:
        print "Dirfile exists somehow. We can deal with this later. For now returning None."
        return None

def append_to_dirfile(dirfile, datapacket_dict):
    """Function to act as the consumer, that will be given a 2d array of data
    comprising multiple packets, and will write the data to disk.
    """

    #print dirfile.nentries(type  = _gd.RAW_ENTRY), datatowrite.shape[-1]
    #assert dirfile.nentries(type = _gd.RAW_ENTRY) == datatowrite.shape[-1]

    dirfileindex - dirfile.getdata("INDEX")
    currentsize = dirfileindex[-1] if dirfileindex.size > 0 else 0
    print currentsize

    for field_name, (entryfaos_type, field_datatype, py_datatype, sliceobject, packet_data) in datapacket_dict.items():
        # pop out the data container
        datatowrite = [datatowrite.pop(0) for i in range(len(packet_data))]
        dirfile.putdata(field_name + datatag, np.ascontiguousarray( datatowrite ).flatten(), first_sample = currentsize)
