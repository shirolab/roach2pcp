#

# Functions used to handle dirfile data saving

def gen_dirfilehandle(self, *dirfileflags):
    """ Function to generate new dirfile with name , and return a handle to the new file.
    """
    # check to see if current handle is a valid open file, and close as appropriate
    # TODO read from stdin to get a filename ID to add to
    # test encodings to see if the data size can be reduced significantly

    # create new file as appropriate, with file name format as YYYYMMDD_HHMMSS_OBS (can be redefined if required)

    dirfilename = os.path.join(SAVEDATADIR, time.strftime("%Y%m%d-%H%M%S") + "OBS" )

    dirfileflagint = np.bitwise_or.reduce(dirfileflags) if dirfileflags \
                                                        else gd.CREAT|gd.RDWR|gd.UNENCODED|gd.EXCL
    try:
        dirfilehandle = gd.dirfile( dirfilename, dirfileflagint )
        return dirfilehandle

    except gd.ExistsError:
        print "Dirfile exists somehow. We can deal with this later. For now returning None."
        return None

def gen_formatfile(self):
    """ create a dirfile and populate the format file """

    #TODO  include dervied fields, constants, sweeps, metadata...etc
    dirfilehandle = self.dirfilehandle if hasattr(self.dirfilehandle, "name") else self.gen_dirfilehandle()

    dirfilehandle.add_spec('ctime' +  ' RAW FLOAT64 1')     # add fields (can use either add_spec or add)

    kidlist = ["KID{kidnum:04d} RAW COMPLEX128 1".format(kidnum=i) for i in range(NTONES)]
    l = map(dirf.add_spec, kidlist)
