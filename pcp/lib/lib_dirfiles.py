#

# pcp dirfile standards
# maindirfile
#   - sweepdirfile
#- calfrag constants from sweep fragment (di/df, dq/df, i0, q0 )
#- K### x Ntones (timestreams)
#- S### x Ntones (sweeps)
#- TONES -> derived fields to constant can easily be configured
# timing info x 7?

# create a new dirfile, and populate with correct fieldnames
import os, sys, time, shutil, functools, numpy as np, pandas as _pd, logging as _logging, multiprocessing as _mp
_logger = _logging.getLogger(__name__)
import pygetdata as _gd
from ..configuration import filesys_config, roach_config, general_config, lib_config, firmware_registers
from .. import toneslist
from . import lib_datapackets

# maps made using pygetdata 0.10.0 - hopefully this won't change in future version of pygetdata...
_GDDATAMAP = { "_gd.UINT8":1, "_gd.UINT16":2, "_gd.UINT32":4, "_gd.UINT64":8,
               "_gd.INT":36, "_gd.INT8":33, "_gd.INT16":34, "_gd.INT32":36, "_gd.INT64":40,
               "_gd.FLOAT":136, "_gd.FLOAT32":132, "_gd.FLOAT64":136,
               "_gd.STRING":520, "_gd.NULL":0 }

_GDENTRYMAP = { "_gd.NO_ENTRY":0, "_gd.BIT_ENTRY":4, "_gd.CARRAY_ENTRY":18, "_gd.CONST_ENTRY":16, "_gd.DIVIDE_ENTRY":10,
                "_gd.LINCOM_ENTRY":2, "_gd.LINTERP_ENTRY":3, "_gd.MPLEX_ENTRY":13, "_gd.MULTIPLY_ENTRY":5, "_gd.PHASE_ENTRY":6,
                "_gd.POLYNOM_ENTRY":8, "_gd.RAW_ENTRY":1, "_gd.RECIP_ENTRY":11, "_gd.SBIT_ENTRY":9, "_gd.STRING_ENTRY":17,
                "_gd.WINDOW_ENTRY":12, "_gd.INDEX_ENTRY":7 }

# class pcp_dirfile(_gd.dirfile):
#     def __init__(self):
#         super(pcp_dirfile, self).__init__()
#
#     def pcp_putdata(*args, **kwargs) :
#         field_code, data = args
#         type         = kwargs.pop("type", None)
#         first_frame  = kwargs.pop("first_frame", None),
#         first_sample = kwargs.pop("first_sample", None)
#
#         return self.putdata(field_code, data, type, first_frame, first_sample)

def is_path_a_dirfile(path_to_check):
    """
    Simple function to check if a path is a vlaid dirfile.
    Firstly, checks if there is a "format" file, then checks that the first line
    is as expected for the dirfile standard.

    """
    # ensure that the path exists
    if not os.path.exists(path_to_check):
        _logger.warning( "Path doesn't exist." )
        return False

    # ensure that the path is a directory
    if not os.path.isdir(path_to_check):
        _logger.warning( "Path is not a directory" )
        return False

    # check if directory contains a 'format' file
    if not 'format' in os.listdir(path_to_check):
        _logger.warning( "no format file found in directory." )
        return False

    # open and read the first line of the format file (which should read # "This is a dirfile format file."")
    format_file_to_check = os.path.join(path_to_check, 'format')

    assert os.path.exists(format_file_to_check) # this is probably not necessary

    # read first line of the format file
    with open(format_file_to_check) as fin:
        first_line = fin.readline()

    # check that the first line contains "dirfile format file"
    if "dirfile format file" in first_line:
        return True
    else:
        _logger.warning( "{0} doesn't look like a valid dirfile".format(path_to_check) )
        return False

def is_dirfile_valid(dirfile):

    """
    Function to check if a given dirfile is open/valid and ready to be written to.

    Parameters
    ----------
    dirfile : pygetdata.dirfile
        Input dirfile to check. Must be a pygetdata dirfile.

    Returns
    -------
    isvalid : bool
        True or False depending on whether the dirfile is open.

    """
    assert type(dirfile) == _gd.dirfile, "'{0}' doesn't appear to be a dirfile ".format(dirfile)

    try:
        return dirfile.name != "" # calling dirfile.name checks if the dirfile is valid
    except _gd.BadDirfileError:
        return False

def check_valid_sweep_dirfile(dirfile):
    """
    Function to check if a given dirfile appears to be a valid pcp sweep file, by checking for the metadata.type
    field.

    Parameters
    ----------
    dirfile : pygetdata.dirfile
        Input dirfile to check. Must be a pygetdata dirfile.

    Returns
    -------
    isvalid_sweep : bool
        True or False depending on whether the dirfile looks like a pcp sweep dirfile.

    """
    assert is_dirfile_valid(dirfile), "{0} doesn't appear to be a valid dirfile. Ensure the dirfile is open and try again.".format(dirfile)

    try:
        return dirfile.get_string("metadata.type") == 'sweep'
    except _gd.BadCodeError:
        print "metadata fragment doesn't appear to exist"
        return False

def list_fragments_in_dirfile(dirfile):
    return [os.path.basename(dirfile.fragment(i).name) for i in range(dirfile.nfragments)]

def check_fragment_valid(dirfile, frag_name):
    """
    Function to check if a given fragment name is included in dirfile.

    Parameters
    ----------
    dirfile : pygetdata.dirfile
        Input dirfile to check. Must be a pygetdata dirfile.

    fragname : str
        Fragment name to check. Assumes a string input.

    Returns
    -------
    (frag_exists, frag_idx) : (bool, int)
        Tuple returning True/False and the corresponding index. If False, index will be None.

    """
    assert is_dirfile_valid(dirfile), "{0} doesn't appear to be a valid dirfile. Ensure the dirfile is open and try again.".format(dirfile)
    assert isinstance(frag_name, str), "{0} is not a string."
    # check if metadata fragment exists, and create if not
    try:
        return True, list_fragments_in_dirfile(dirfile).index(frag_name)
    except ValueError:
        return False, None

def create_pcp_dirfile(roachid, dirfilename="", dirfile_type = "stream", tones=21, *dirfile_creation_flags, **kwargs):
    """
    High level function to create a new dirfile according to the pcp standards. This creates a format file with a number of tones
    (to be standardised), and other packet information, read from roach_config (to be implmented).

    If no dirfilename is given, or if dirfilename is a path and not a valid dirfile, then a new dirfile will be created using
    the default filename format.

    If a valid dirfile is given, a warning will be given and it will be passed through.

    Valid kwargs:
        - datatag; string to add to file path prepended by a leading underscore. Only applies to new filenames. Default is empty string.
    """
    # check that the input is a string
    assert type(dirfilename) == str

    assert dirfile_type in ["stream", "sweep"]

    # handle kwargs
    filename_suffix = kwargs.pop("filename_suffix", "") # str to add to file path (only applies to new filenames)
    filename_suffix = "_"  + filename_suffix if filename_suffix else ""

    array_size = kwargs.pop("array_size", 101) # default size used for sweep file creation

    inc_derived_fields = kwargs.pop("inc_derived_fields", False) # option to include derived fields to dirfile

    if kwargs:
        raise NameError("Unknown kwarg(s) given {0}".format(kwargs.keys()))

    # parse user specified set of dirfile flags, else use defaults (note _gd.EXCL prevents accidental overwriting)
    dirfileflagint = np.bitwise_or.reduce(dirfileflags) if dirfile_creation_flags \
                                                        else _gd.CREAT|_gd.RDWR|_gd.UNENCODED|_gd.EXCL
    # check if the file path is a valid dirfile
    if is_path_a_dirfile(dirfilename):
        _logger.info( "It looks like {0} is a valid dirfile. Opening and returning dirfile.".format(dirfilename) )
        return _gd.dirfile(dirfilename, _gd.RDWR|_gd.UNENCODED)

    # check if path exists - join new filename to existing path. Or if no path is given, create file in cwd
    elif os.path.exists(dirfilename) or dirfilename == "":
        dirfilename = os.path.join( dirfilename, time.strftime(general_config['default_datafilename_format']) + filename_suffix )

    # assume that the path given is the intended path of the new dirfile
    else:
        pass # not required, but better to be explicit than implicit :)

    # create the new dirfile
    dirfile = _gd.dirfile(dirfilename, dirfileflagint)
    _logger.info( "new dirfile created; {0}".format(dirfile.name) )
    # add main fields according to the type required

    if dirfile_type == "stream":
        dirfile = generate_main_rawfields(dirfile, roachid, tones, fragnum = 0)#, field_suffix = field_suffix)
        if inc_derived_fields:
            # add derived fields
            pass

    elif dirfile_type == "sweep":
        dirfile = generate_sweep_fields(dirfile, tones, array_size = array_size)#, field_suffix = field_suffix)

    return dirfile

def open_dirfile(dirfilename, **dirfile_flags):

    if is_path_a_dirfile(dirfilename):
        return _gd.dirfile(dirfilename, dirfileflags)
    else:
        _logger.warning("can't open dirfile {0}".format(dirfilename))

def close_dirfile(dirfilename):

    # allow dirfile instance to be passed
    if type( dirfilename ) == _gd.dirfile:
        # check if dirfile is valid ?
        dirfilename.close()

    elif type( dirfilename ) == str:
    # check if file exists
        if os.path.exists(dirfilename):
            _gd.dirfile(dirfilename).close()
            return
        else:
            return
    else:
        return

def generate_main_rawfields(dirfile, roachid, tones, fragnum=0 ):#, field_suffix = ""):
    # function to generate a standard set of dirfile entries for the roach readout
    # will be used for both timestreams and raw sweep files

    if type(dirfile) != _gd.dirfile:
        print "given dirfile is of type {0}, and not a valid dirfile. Nothing done.".format(type(dirfile))
        return
    elif roachid not in roach_config.keys():
        print "Unrecognised roachid = {0}".format(roachid)
        return

    # add metadata fragment and add "type" field
    add_metadata_to_dirfile(dirfile, {"type": "stream"})

    # get the appropriate namespace for the fragment to add to the fields
    namespace = dirfile.fragment(fragnum).namespace

    # read in auxillary fields as defined in the configuration file and create getdata entries
    firmware_dict = lib_config.get_firmware_register_dict( firmware_registers, roach_config[roachid]["firmware_file"] )
    aux_fields = firmware_dict["packet_structure"]["aux_field_cfg"]

    aux_entries_to_write = []

    for field_name, (entry_type, field_datatype, __, __, __, __) in aux_fields.items():
        #print eval(entry_type), eval(field_datatype)
        #print _GDENTRYMAP[entry_type], _GDDATAMAP[field_datatype]
        aux_entries_to_write.append( _gd.entry( _GDENTRYMAP[entry_type], namespace + field_name, \
                                                fragnum, \
                                                (_GDDATAMAP[field_datatype], 1) ) )
                                                 # field_type, name, fragment_idx, (data_type, sample_rate)
    # generate the field names for tones
    kid_fields_I, kid_fields_Q = toneslist.gen_tone_iq_fields(tones, namespace=namespace) #, field_suffix = field_suffix)

    kid_entries_to_write = [ _gd.entry(_gd.RAW_ENTRY, field_name, fragnum, (_gd.FLOAT64, 1)) for field_name in kid_fields_I ] \
                         + [ _gd.entry(_gd.RAW_ENTRY, field_name, fragnum, (_gd.FLOAT64, 1)) for field_name in kid_fields_Q ]

    # add derived fields

    # constants for each resonator - can we use an array? need i0, q0, di0, dq0, di0**2 + dq0**2, di0*i0, dq0*q0


    # add all entries into format file
    for entry in aux_entries_to_write + kid_entries_to_write:
        dirfile.add(entry)

    dirfile.sync()
    return dirfile

def generate_sweep_fields(dirfile, tones, array_size = 501 ):#, field_suffix=""):
    """Generate fragment file for the derived sweep file """

    # add metadata fragment and add "type" field
    add_metadata_to_dirfile(dirfile, {"type": "sweep"})

    swp_fields = toneslist.get_tone_fields( tones )
    #swp_fields = ["K{kidnum:04d}".format(kidnum=i) for i in range(tones)]
    _logger.debug("size of carray for sweep data = {0}".format(array_size) )

    # Parameters
    sweep_entry_freq       = [ _gd.entry(_gd.CARRAY_ENTRY, "sweep." + "lo_freqs", 0, (_gd.FLOAT64,   array_size)) ]
    sweep_entry_bb         = [ _gd.entry(_gd.CARRAY_ENTRY, "sweep." + "bb_freqs", 0, (_gd.FLOAT64,   len(tones))) ]
    sweep_entries_to_write = [ _gd.entry(_gd.CARRAY_ENTRY, "sweep." + field_name, 0, (_gd.COMPLEX64, array_size)) for field_name in swp_fields ]

    _logger.debug("generating new sweep fields: {0}".format(sweep_entries_to_write) )

    map(dirfile.add, sweep_entry_freq + sweep_entry_bb + sweep_entries_to_write)

    # --- add calibration fragment ---

    # constants for F0s, i0, q0, didf0, dqdf0, didq0
    cal_data_fields = ["f0s", "i0", "q0", "didf0", "dqdf0", "didq2"]
    # arrays for cal data
    # constants for centres and rotation for phase (just start with df)

    cal_fragment = dirfile.include("calibration", flags = _gd.CREAT|_gd.EXCL)

    # add calibration fields to the dirfile
    cal_param_entries        = [ _gd.entry(_gd.CARRAY_ENTRY, "cal."     + field_name, cal_fragment, (_gd.FLOAT64, len(tones)) )  for field_name in cal_data_fields]
    caldata_entries_to_write = [ _gd.entry(_gd.CARRAY_ENTRY, "caldata." + field_name, cal_fragment, (_gd.COMPLEX64, array_size)) for field_name in swp_fields ]

    _logger.debug("generating new sweep cal fields: {0}".format(cal_param_entries + caldata_entries_to_write) )

    map(dirfile.add, cal_param_entries + caldata_entries_to_write)

    dirfile.sync()

    return dirfile

def generate_sweep_fragment(dirfile, tones, array_size = 501, datatag=""):
    """Generate fragment file for the derived sweep file """

    namespace = "sweep"

    sweep_frag = dirfile.include("sweep_frag", namespace = namespace, flags = _gd.CREAT|_gd.EXCL)

    sep = "_" if datatag else ""; datatag = sep + datatag # str to add to file path (only applies to new filenames)

    swp_fields = check_tones_type(tones)
    # old - to delete -
    #swp_fields = ["K{kidnum:04d}{datatag}".format(kidnum=i, datatag=datatag) for i in range(ntones)]

    sweep_entry_freq       = [ _gd.entry(_gd.CARRAY_ENTRY, ".".join((namespace, "lo_freqs")), sweep_frag, (_gd.FLOAT64, array_size)) ]
    sweep_entries_to_write = [ _gd.entry(_gd.CARRAY_ENTRY, ".".join((namespace, field_name)), sweep_frag, (_gd.COMPLEX64, array_size)) for field_name in swp_fields ]

    #return sweep_entries_to_write
    for entry in sweep_entry_freq + sweep_entries_to_write:
        dirfile.add(entry)

    dirfile.sync()

    return dirfile

def generate_main_derivedfields(dirfile):
    pass

def check_dirfile_is_empty(dirfile):
    """Returns True if dirfile is empty (len(INDEX) == 0), otherwise, False"""
    # get the size of the INDEX field
    return len( dirfile.getdata("INDEX") ) == 0

def add_subdirfile_to_existing_dirfile(subdirfile, dirfile, namespace = "", overwrite=False):
    """
    Function to add a subdirfile to an existing dirfile and include the subdirfile as a new fragment
    of the main dirfile - i.e. all of the fields of the subdirfile will be avaialble to the main dirfile.

    Will check to see if one already exists, and if empty, replace with the new one. If not,
    rename existing file and add this.

    Mainly used to add multiple sweep dirfiles to a main dirfile.

    """
    # check both files exist and are open (i.e. dirfile.name is a valid path)
    try:
        subdfname = subdirfile.name
        dfname    = dirfile.name
    except _gd.BadDirfileError:
        print "Invlaid dirfile. Make sure the dirfile is open and exists. Nothing done. Returning. "
        return
    except AttributeError:
        print "inputs do not appear to be dirfiles"

    # check that the destination doesn't exist and ask the user for permission to overwrite -maybe this should be removed
    new_subdirfile_path = os.path.join(dirfile.name, os.path.basename(subdirfile.name))
    if os.path.exists(new_subdirfile_path):
        if overwrite:
            # delete old path and continue
            print "warning: path to new subdir already exists. Overwriting"
            shutil.rmtree(new_subdirfile_path)
        else:
            print "Not overwriting. Returning."
            return

    # copy the subdirfile into the existing dirfile
    try:
        # copy the subdirfile to the maindirfile using the same base name
        shutil.copytree(subdirfile.name, new_subdirfile_path)

    except OSError as err:
        print "Copy unsuccesful - nothing done; error:", err
        return

    # add a the subdrifile as a new fragment
    ## TODO: this should probably be in a try - except statement
    newfrag = dirfile.include(os.path.join(os.path.basename(subdirfile.name), "format"), namespace = namespace, flags = _gd.EXCL|_gd.RDWR)
    # could change above to df.fragment(0).name

    # flush the changes and update the format file
    dirfile.flush()

def write_sweep_cal_params(dirfile, cal_params, cal_data_dict):

    assert is_dirfile_valid(dirfile)

    assert isinstance(cal_data_dict, dict), "cal data is required to be in a dictionary with tonename: caldata as key: value"
    # cal params = (sweep_f[idxs], sweep_i[idxs], sweep_q[idxs], didf[idxs], dqdf[idxs])
    # cal_data  = (didf, dqdf, didq2)

    # check that sweep cal_fragment is available
    is_frag_valid, calfrag = check_fragment_valid(dirfile, "calibration")
    if not is_frag_valid:
        _logger.warning("there doesn't appear to be a claibration fragment. Calibration parameters not written.")
        return

    cal_param_fields = ["f0s", "i0", "q0", "didf0", "dqdf0", "didq2"]
    cal_data_fields  = ["didf", "dqdf", "didf2"] # dictionaries

    for cal_param_field, cal_param in zip(cal_param_fields, cal_params):
        dirfile.put_carray("cal." + cal_param_field, cal_param)

    for tone_name, cal_data in cal_data_dict.items():
        dirfile.put_carray("caldata." + tone_name, cal_data)

    dirfile.flush()

def add_sweep_to_dirfile(dirfile):
    """

    High level function to add a sweep dirfile to another dirfile. This function adds the sweep file as a subdirfile
    to a dirfile, and adds an auxillary sweep format file to create the derived products that can be calculated from
    raw I and Q data when a sweep is present.

    """
    # checks that the dirfile is valid
    # check that the number of fields is sensible?

    #
    pass

def get_calibration_data_from_sweep(sweep_dirfile, which = "di"):
    pass
    # checks that the sweep dirfile is valid
    # return the di/df dq/df, i0, q0... etc
    # also can return phase parameters?

def create_sweep_derived_fields(dirfile, f_tone):

    calfrag = dirfile.include("calibration", flags = _gd.EXCL|_gd.RDWR )

    for chan in channels:
        dirfile.add( _gd.entry( _gd.CONST_ENTRY,'_cal_tone_freq_%04d'%chan,calfrag,(_gd.FLOAT64,) ) )
        dirfile.put_constant('_cal_tone_freq_%04d'%chan, f_tone[chan])

        #i-i0 q-q0
        dirfile.add(_gd.entry(_gd.LINCOM_ENTRY, '_cal_i_sub_i0_%04d'%chan, calfrag, (("I%04d"%chan,),(1,),(-1*i_tone,))))
        dirfile.add(_gd.entry(_gd.LINCOM_ENTRY, '_cal_q_sub_q0_%04d'%chan, calfrag, (("Q%04d"%chan,),(1,),(-1*q_tone,))))

        #Complex values
        dirfile.add(_gd.entry(_gd.LINCOM_ENTRY,'_cal_complex_%04d'%chan,calfrag, (("I%04d"%chan,"Q%04d"%chan),(1,1j),(0,0))))

        #Amplitude
        dirfile.add(_gd.entry(_gd.PHASE_ENTRY,'amplitude_%04d'%chan,calfrag, (('_cal_complex_%04d.m'%chan),0)))

        #Phase
        dirfile.add(_gd.entry(_gd.LINCOM_ENTRY,'phase_raw_%04d'%chan,calfrag,
        (('_cal_complex_%04d.a'%chan,),(1,1j),(0,))))

        #Complex_centered:
        dirfile.add(_gd.entry(_gd.LINCOM_ENTRY,'_cal_centred_%04d'%chan,calfrag,
        (("_cal_complex_%04d"%chan,),(1,),(-c[0]-1j*c[1],))))

        #Complex_rotated
        dirfile.add(_gd.entry(_gd.LINCOM_ENTRY,'_cal_rotated_%04d'%chan,calfrag,
        (("_cal_centred_%04d"%chan,),(np.exp(-1j*phi_tone),),(0,))))

        #Phase
        dirfile.add(_gd.entry(_gd.LINCOM_ENTRY,'phase_rotated_%04d'%chan,calfrag,
        (('_cal_rotated_%04d.a'%chan,),(1,),(0,))))

        #df = ((i[0]-i)(di/df) + (q[0]-q)(dq/df) ) / ((di/df)**2 + (dq/df)**2)
        dirfile.add(_gd.entry(_gd.CONST_ENTRY,'_cal_didf_mult_%04d'%chan,calfrag,(_gd.FLOAT64,)))
        dirfile.add(_gd.entry(_gd.CONST_ENTRY,'_cal_dqdf_mult_%04d'%chan,calfrag,(_gd.FLOAT64,)))
        dirfile.put_constant('_cal_didf_mult_%04d'%chan,didf_tone/(didf_tone**2+dqdf_tone**2))
        dirfile.put_constant('_cal_dqdf_mult_%04d'%chan,dqdf_tone/(didf_tone**2+dqdf_tone**2))
        dirfile.add(_gd.entry(_gd.LINCOM_ENTRY,'_cal_i0_sub_i_%04d'%chan,calfrag,
        (("I%04d"%chan,),(-1,),(i_tone,))))
        dirfile.add(_gd.entry(_gd.LINCOM_ENTRY,'_cal_q0_sub_q_%04d'%chan,calfrag,
        (("Q%04d"%chan,),(-1,),(q_tone,))))
        dirfile.add(_gd.entry(_gd.LINCOM_ENTRY, 'delta_f_%04d'%chan, calfrag,
        (("_cal_i0_sub_i_%04d"%chan,"_cal_q0_sub_q_%04d"%chan),
        ("_cal_didf_mult_%04d"%chan,"_cal_dqdf_mult_%04d"%chan),
        (0,0))))

        #x = df/f0
        dirfile.add(_gd.entry(_gd.LINCOM_ENTRY,'x_%04d'%chan,calfrag,
        (('delta_f_%04d'%chan,),(1./f_tone[chan],),(0,))))


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


def get_auxdata_from_datapacket_dict(datapacket_dict, field_name):
    # assert field_name in datapacket_dict.keys()
    # assert all([type(x) == np.ndarray for x in datapacket_dict[field_name][-1]]) # adds 1 us to loop time for each field, may be unnecessary
    data = datapacket_dict[field_name][-1]
    return np.ascontiguousarray( [data.pop(0) for i in range(len(data))] ).flatten() # pop to remove data from the data list

def append_to_dirfile(dirfile, datapacket_dict): #, datatag=""):
    """Function to act as the consumer, that takes the datapacket_dict with
    data from multiple packets, and write that data to disk.
    """

    #print dirfile.nentries(type  = _gd.RAW_ENTRY), datatowrite.shape[-1]
    #assert dirfile.nentries(type = _gd.RAW_ENTRY) == datatowrite.shape[-1]
    # check that the number of fields in the dirfile (index field is not RAW_ENTRY) is less than or equal to the
    # number that are in the packet, otherwise, this function will fail

    field_list = dirfile.field_list(_gd.RAW_ENTRY)

    #assert len(field_list) <= len(datapacket_dict)

    currentsize = dirfile.nframes
    _logger.debug("current size and index of first sample of data chunk to write = {0}".format( currentsize ) )

    # write raw packet to disk
    #print datapacket_dict['raw_packet'][-1]
    #dirfile.putdata('raw_packet', datapacket_dict['raw_packet'][-1]  )

    # write the data
    for field_name in field_list:

        if field_name in datapacket_dict['aux_fields'].keys() + ['python_timestamp']:
            dirfile.putdata(field_name, get_auxdata_from_datapacket_dict(datapacket_dict['aux_fields'], field_name), first_sample = currentsize ) #+ 1)

        elif field_name in datapacket_dict['tone_fields'].keys():
            toneidx = datapacket_dict['tone_fields'][field_name][-1]
            #print toneidx, field_name
            dirfile.putdata( field_name, datapacket_dict['tone_data'][toneidx], first_sample = currentsize )

        else:
            raise TypeError, "warning, unknown field name {0}".format(field_name)

    dirfile.flush()

def generate_sweep_dirfile( roachid, dirfilename, lo_frequencies, bb_frequencies, complex_sweep_data_dict ):#, field_suffix = "" ):
    """
    Generate a sweep dirfile from arrays of F, I, Q. In addition, add constants from
    di/df, dq/df vs freq, di/df ^2, dq/df ^2, centred + rotated IQ circle + anything else you can get from the sweep!

    input is an array of lo frequencies and a dictionary of complex I + 1j*Q for each tone vs lo freq.

    """
    tone_names       = complex_sweep_data_dict.keys()#len(complex_sweep_data_dict)
    num_sweep_points = len(lo_frequencies)
    _logger.debug( "tone names used for sweep fields: {0}".format( tone_names ) )
    _logger.debug( "number of sweep points {0}".format( num_sweep_points ) )

    # create new dirfile for derived sweep
    sweep_dirfile = create_pcp_dirfile(roachid, dirfilename, dirfile_type = "sweep", tones = tone_names, array_size = num_sweep_points, filename_suffix = "sweep")

    sweep_dirfile.put_carray("sweep." + "bb_freqs", bb_frequencies)
    sweep_dirfile.put_carray("sweep." + "lo_freqs", lo_frequencies)

    for field_name, sweep_data in complex_sweep_data_dict.items():
        sweep_dirfile.put_carray("sweep." + field_name, sweep_data)

    sweep_dirfile.flush()
    return sweep_dirfile

######################################################################################################
######################################################################################################
def add_metadata_to_dirfile(dirfile, metadata_dict):
    """

    Function to add metadata to a dirfile as a new fragment.

    Currently all data is written as a string for simplicity.

    """
    # check if metadata fragment exists, and create if not
    is_frag_valid, metadata_frag = check_fragment_valid(dirfile, "metadata")

    if not is_frag_valid:
        metadata_frag = dirfile.include("metadata", flags = _gd.CREAT|_gd.EXCL)

    # add new entries to the dirfile
    map(dirfile.add, [ _gd.entry(_gd.STRING_ENTRY, ".".join(("metadata", field_name)), metadata_frag) for field_name in metadata_dict.keys() ] )

    # write metadata to file
    for field_name, metadata in metadata_dict.items():
        dirfile.put_string(".".join(("metadata", field_name)), str(metadata))

    dirfile.flush()

######################################################################################################
######################################################################################################
def read_sweep_dirfile(sweep_dirfile):
    """

    Read data from a sweep dirfile. Returns a tuple contain a dictionary with the sweep data, and any metadata

    """

    assert is_dirfile_valid(sweep_dirfile)

    # check that the dirfile looks like a sweep dirfile
    assert "sweep" in os.path.basename(sweep_dirfile.name)

    return dict( sweep_dirfile.carrays( _gd.COMPLEX, as_list=False) ), dict( sweep_dirfile.strings() )


def append_dirfile_to_sourcefile(srcfile, dirfilename, timespan = 120.):
    """
    Function to append a dirfile to a source file list for easy reading in KST. Time span, in minutes, is the
    length of time for which the dirfiles remain in the sourcefile
    """

    assert not srcfile.closed, "source file appears to be closed - check again"

    # read sourcefile contents
    srcfile.seek(0)
    dirfilelist = np.array( [f.strip() for f in srcfile.readlines()] )

    # get last modified timestamps for current files
    modtimes = np.array( [os.path.getmtime(df) for df in dirfilelist] )

    # choose only where last modified times are greater than timespan
    dirfilelist = dirfilelist[ modtimes > time.time() - timespan * 60. ]
    # append new file to the list
    print dirfilelist
    dirfilelist = np.append( dirfilelist, dirfilename )
    print dirfilelist

    # write to file (adding newlines)
    srcfile.seek(0)
    srcfile.writelines( np.char.add( dirfilelist, '\n' ) )
    srcfile.truncate()
    srcfile.flush()

######################################################################################################
################################################# Graveyard #####################################################

# def create_pcp_dirfile(dirfilename, ntones, *dirfileflags):
#     """
#     High level function to create a new dirfile according to the pcp standards. This creates a format file with a number of tones
#     (to be standardised), and other packet information, read from roach_config (to be implmented).
#
#     It then creates a new dirfile, that contains an empty sweep sweep dirfile (which has an identical format file). This sweep dirfile
#     will be used to store the raw data from a sweep, and will then be used to store a reduced version by the sweep function.
#
#
#     """
#     #
#     # parse user specified set of dirfile flags, else use defaults (note _gd.EXCL prevents accidental overwriting)
#     dirfileflagint = np.bitwise_or.reduce(dirfileflags) if dirfileflags \
#                                                         else _gd.CREAT|_gd.RDWR|_gd.UNENCODED|_gd.EXCL
#     # create dirfile
#     maindirfile = _gd.dirfile(dirfilename, dirfileflagint)
#     # add main fields
#     maindirfile = generate_main_rawfields(maindirfile, ntones)
#
#     # create sweep subdirfile
#     sweepdirfilename = os.path.join(maindirfile.name, "sweep")
#     sweepdirfile = _gd.dirfile(sweepdirfilename, dirfileflagint)
#
#     sweepdirfile = generate_main_rawfields(sweepdirfile, ntones, fragnum = 0, datatag = "_swp")
#
#     swpfragment = maindirfile.include("sweep_data", flags = _gd.CREAT|_gd.EXCL)
#
#     #raw_sweep_frag = maindirfile.include(os.path.join( os.path.basename(sweepdirfilename), "format"), flags = _gd.RDWR|_gd.CREAT)
#
#     # add sweep files that will be saved later ()
#
#     # include sweep format file to maindir. Note that adds a fragment_index = 1 for the sweep
#     #maindirfile.include("sweep_data", flags = _gd.CREAT|_gd.EXCL|_gd.RDWR)
#
#
#     # set up sweep fields in main directory - can we calculate from derived fields?
#     #maindirfile.add(gd.entry( _gd.RAW_ENTRY, K000_LO, 0,(_gd.FLOAT64, 1) ))
#     return maindirfile, sweepdirfile
    # derived fields
    # calbration fragment



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
