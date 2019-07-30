#!/usr/bin/env python
# 20171230 - PB

# Code to be run as a python-daemon in the background and be used to collect UDP packets
# and save to disk. Philosophy is to keep this simple as possible!

# function to run for logging daemon

# top level
#     - should return a single object that can communicate easily with the process

# simple producer/cosumer thread
#     - producer reads packet from the socket
        # - valid socket will passed in to this function
        # - needs to be able to reset the socket upon error?
#     - consumer saves file to disk
        # - create new file


# other functionality
    # - ability to stop and start data saving on demand
    # - create new dirfile on demand
    #    - ensure that files can't be overwritten accidently
    #    - get format for filename from configuration file
    #    - allow tag to be appended to filename

# commands
#    - send a tuple (str, any_required_data)

"""
Datalogger.

Usage:
    dl = pcp.datalog_mp.dataLogger(roachid)
        - upon instantiation, initialises both daemon process, the writer thread, and a socket instance
    dl.start_daemon()
        - starts daemon process. When started, the writer thread is initially paused.

Useful notes:
    - dl.network_config will display the current loaded configuration parameters
    - dl.isrunning() and dl.process.is_alive()

    - testing individual parallel functions
        -

    dirfile methods
        - set active dirfile
        - get active dirfile


"""

#from memory_profiler import profile

# test of multiprocessing
import os, sys, time, signal, select, threading, ctypes
from collections import deque
import numpy as np

import multiprocessing as mp; from multiprocessing.managers import SyncManager as _syncmanager
_syncmanager.register('deque', deque, exposed = [d for d in dir(deque) if not d.startswith("__") or d == "__len__"] )

_deque_manager = _syncmanager(); #_deque_manager.start(signal.signal, (signal.SIGINT, signal.SIG_IGN) )

import setproctitle
import logging as _logging
_logger = _logging.getLogger(__name__)
import pygetdata as _gd

from .lib import lib_dirfiles, lib_datapackets, lib_network

from .configuration import ROOTDIR, filesys_config, network_config, roach_config

# globally define filesystem
DIRFILE_SAVEDIR = os.path.join(ROOTDIR, filesys_config['savedatadir'])

# paranoia - this should all have been handled in the setup of the configuration parameters
if not os.path.exists(DIRFILE_SAVEDIR): os.mkdir(DIRFILE_SAVEDIR)

#BaseManager.register('dataLogger', dataLogger)
#manager = BaseManager()

class dataLogger(object):
    """
    Create a datalogger object.

    Parameters
    ----------
    roachid : str
        String used as an index the configuration files, as well as identify the datalogger daemon. Therefore, "roachid"
        should be an entry in the configuration files. In addition, the same string is used to name the logger.

    Returns
    -------
    out : dataLogger instance
        Fully initialised datalogger instance ready to start the daemon process, with dataLogger.start()

    Provides
    --------

    Notes
    -----
    Due to the parallel process nature, this class is a little complicated, and requires some care when programming. Within the class
    we define functions that are designed to be run in an independant process. When the daemon process is created, Python creates a copy
    of the main memory-space. What this means is that references to "self" will not point to the same object in both the main (ipython)
    process, and the parallel daemon process. Therefore, if self.attribute is set to a new value in the daemon, it will NOT update in ipython.
    This just means that to access attributes in the daemon, we will need to pass data via a multiprocessing.Queue. In addition, when
    care must be take to remain cognisant of which process the function will run in, and therefore which set of vairables you have access
    to.

    There are three Events used to maintain synchronisation between the main and daemon processes, and a Queue (_eventqueue) to pass data
    between processes;
        1. _ctrlevent
        2. _cmdevent
        3. _exitevent

    Communication between processes follows a simple producer - consumer design;
        - the main process puts a command into the
        - the main process sets _ctrlevent which breaks out of the inner loop in the daemon process (_data_logger_main) and allows
        the daemon to read the queue and parse the command (_process_command)
        - in the case of functions that expect a response, _read_response_from_eventqueue is used
        - _read_response_from_eventqueue waits for a _cmdevent to be set before reading the event queue


    # TODO:
    -x implement a check to see whether packets are being collected
    -x add flush/empty data queue function
    - move socket initialisation into daemon process (remove duplicate socket defs)
    - implement a close dirfile option
    - implement a more robust method to check if _eventqueue has been read
    """

    def __init__(self, roachid):

        # get logger instance
        self.logger = _logging.getLogger("logging.daemon.{name}".format(name = roachid))
        self.roachid = roachid

        # make sure roachid is a string
        assert isinstance(roachid, str), "identifier is not a string, but {0}".format(type(roachid))
        self.process_name = roachid

        # container for datapacket_dict. Used by the writer process to parse and save packet data
        self._datapacket_dict = None
        #self._toneslist       = None

        # setup up attribute for dirfiles
        self.DIRFILE_SAVEDIR  = os.path.join(DIRFILE_SAVEDIR, roachid) # <- (this might not be needed )
        self.current_filename = None
        self.current_dirfile  = None

        # moved to muxChannel
        #self._last_closed_dirfile  = None
        #self._last_closed_filename = None

        # setup up network handles
        self._sockethandle = None

        #self._writer_queue = deque(maxlen = roach_config[roachid]["max_queue_len"])
        self._writer_queue = _deque_manager.deque(maxlen = roach_config[roachid]["max_queue_len"])

        # check that the roachid is in the configuration files
        try:
            # get the network configuration file and store it
            self.network_config = network_config[roachid]
            # initialise the multiprocessing.Process
            self._initialise_data_logger_process( roachid )#, self._datapipe_in )
            # initialise the socket
            self._initialise_network_config( roachid )
            # initialise packet writer thread
            self._initialise_writer_thread ( roachid ) #, self._datapipe_out )
            #self._filewritethread = None

        except KeyError:
            raise

        #self._filesys_config = filesys_config

        # create mp.Event and mp.Queue for controlling process
        self._ctrlevent  = mp.Event()
        self._exitevent  = mp.Event()
        self._cmdevent   = mp.Event()
        self._eventqueue = mp.Queue()
        self._datapipe_out, self._datapipe_in = mp.Pipe(duplex=False)

        # initialise status flag(s). Upon starting, the writer is initially paused.
        self.is_writing = mp.Value(ctypes.c_bool, False)
        #self.is_writing = False

    # -----------------------------------------------------------------------------

    def _initialise_data_logger_process(self, process_name):#, datapipe_in):
        """
        Function to inialise multiprocessing.Process. Called during instantiation to initialse
        the daemon process.

        Parameters
        ----------
        process_name : str
            String used to as the name of the process daemon.
        *function_args
            Any arguments to be passed to the function to be run as the daemon.

        Created Class Attributes
        -------
        self.process : multiprocessing.Process
            Handle to the newly initialised multiprocessing.Process object. Used to control and
            communicate with the process.

        self.start_daemon : method
            Convenience method to multiprocessing.Process.start

        self.is_daemon_running : bool
            Convenience check to see if daemon process is running

        """
        self.process = mp.Process( target = self._data_logger_main,
                                    name = self.process_name) #,
                                    #args = (datapipe_in,)
                                    #)
        self.process.daemon = False
        # for convenience, add handle to process start method
        #self.start_daemon      = self.process.start
        self.is_daemon_running = self.process.is_alive

    def _initialise_network_config(self, roachid):
        """
        Function to inialise socket configuration. Creates and binds to a socket, according to parameters network
        configuration file.

        Parameters
        ----------
        roachid : str
            String that is used to index the network configuration file.

        Created Class Attributes
        -------
        self._sockethandle : socket.socket
            Handle to the newly initialised multiprocessing.Process object. Used to control and
            communicate with the process.

        """
        self._sockethandle = lib_network.generate_socket(self.network_config["socket_type"])

        udp_dest_ip   = self.network_config["udp_dest_ip"]
        udp_dest_port = self.network_config["udp_dest_port"]
        buffer_len    = self.network_config["buf_size"]

        lib_network.configure_socket_and_bind(self._sockethandle, udp_dest_ip, udp_dest_port, buffer_len)

    def _initialise_writer_thread(self, roachid): #, datapipe_out):

        # set maximum queue length from configuration file (default = 1000 = 8 MB)
        # self._writer_queue = deque(maxlen = roach_config[roachid]["max_queue_len"])
        # self._filewritethread = threading.Thread(name = roachid + 'writer_thread', \
        #                                         target = self._writer_thread_function)#, args=(dirf, dq,) )

        self._filewritethread = mp.Process( target = self._writer_thread_function,
                                            name = roachid + 'writer_thread' )#,
                                            #args = (datapipe_out, )
                                            #)
        #self._filewritethread.setDaemon(True) # setting daemon here ensures that the child thread ends with the main thread
        self._filewritethread.daemon = True

    def _data_logger_main(self ):#, datapipe_in ):
        # ingore signal.SIGINT and handle terminate manually (allows for clean up)
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        # try to decrease niceness to prioritize packet reading (needs root privileges..etc)
        #if os.getuid() > 0:
        #    _logger.warning("increasing priority requires root permissions. Nothing done.")
        #else:
        #    os.nice(-10)

        # run basic config to initialise logging for the new process
        #_logging.basicConfig(level=10)

        # start writer thread. Initially the writer is paused
        #self._filewritethread.start()
        #print "current process daemon", mp.current_process().daemon
        _logger.info( "current process daemon {0}".format( mp.current_process().daemon ) )
        #mp.current_process().daemon = False

        #self._initialise_writer_thread(self.roachid)
        #self._filewritethread.start()

        # check file write process is running before continuing
        # tstart = time.time()
        # while not self._filewritethread.is_alive():
        #     if (time.time() - tstart) > 2.:
        #         print "timeout, filewrite process not started, nothing done"
        #         return

        # outer 'exit' loop - once this exit event is set, the function completes and the daemon terminates
        while not self._exitevent.is_set():
            _logger.debug( "in main loop daemon; is writing = {0}".format( self.is_writing ) )
            c = 0
            # inner while loop, runs when no event is set
            while not self._ctrlevent.is_set():
                #print "in main loop"

                # read data from socket (wrap up in a function from lib_network)
                #time.sleep(2)

                rd,wr,err = select.select([self._sockethandle],[],[], 0.1)
                if rd:
                    #print rd[0]
                    packet = self._sockethandle.recv(9000)
                    count = np.frombuffer(packet[-9:-5],">u4")
                    if count - c > 1:
                        print self.roachid," -> PACKET LOST, HELP", c, "  ", count - c - 1, "Packets lost"

                    c = count
                    # append (packet, time.time()) to queue which passes to packet to _writer_thread_function
                    self._writer_queue.appendleft( ( packet, time.time() ) )

                    #print "sending packet to pipe", packet[:10]
                    #datapipe_in.send( ( packet, time.time() ) )
                    # if len(self._writer_queue) > 100:
                    #     datainqueue = [self._writer_queue.pop() for i in range(len(self._writer_queue))]
                    #     if any( np.diff( np.array([np.frombuffer(x[0][-9:-5],">u4") for x in datainqueue]).T)[0] > 1):
                    #         print "packet count = {0}".format(np.array([np.frombuffer(x[0][-9:-5],">u4") for x in datainqueue]).T )
                continue

            # event has been set, broken out of main loop
            _logger.debug("control event triggered - processing command")
            self._process_command() # process event

            self._ctrlevent.clear() # clear control event and continue

            # self.terminate sends signal.SIGINT (kill -15, ctrl+c) to the process to kill it
            # except KeyboardInterrupt:
            #     # this is a dirty way to kill the process, but might be worthwhile
            #     print "broke out"
            #     break
        _logger.debug ( "left main writer loop - cleaning up" )

    #@profile
    def _parse_packet_and_append_to_dirfile(self, datatowrite):
        """
        Function to act as the worker thread for parsing packets and writing data to a dirfile.

        Handles both a single packet or a list of packets.

        Parameters
        ----------
        datatowrite : str, or list of strs

            List of raw packet data to be parsed. The raw packet is read from the socket and will
            be a raw binary string.

        Notes
        -----

        """

        self._datapacket_dict = lib_datapackets.parse_datapacket_dict(datatowrite, self._datapacket_dict)

        #print '\n\n\n\n\n\n*****************'
        #print [len(i) for i in self._datapacket_dict.iteritems()]
        #print self._datapacket_dict.keys()

        #print "size of datapacket_dict", len(self._datapacket_dict["packet_count"][-1])
        #print "bytes size of datapacket_dict", sum([sys.getsizeof(v) for v in self._datapacket_dict.values()])

        packet_counts = np.array(self._datapacket_dict['packet_count'][-1]).T.flatten()
        packet_check, = np.where( np.diff( packet_counts > 1 ))


        if packet_check.size > 0:
            _logger.warning ( "PACKET LOST IN WRITER THREAD = {0}".format( packet_counts[packet_check]  ) )

        # append to data to dirfile
        lib_dirfiles.append_to_dirfile(self.current_dirfile, self._datapacket_dict)

        return 0

    #@profile
    def _writer_thread_function( self ):#, datapipe_out):#, data_queue):
        """
        Function to run as the writer thread spawned in the daemon process. Runs self.parse_packet_and_append_to_dirfile()
        continuously until both is_writing is set to False and _exitevent is set. Note that this means that to terminate
        gracefully the writer should be stopped before the _exitevent is set. That said, if the daemon_process is terminated,
        as setDaemon is True by default, this thread will die at the same time, possibly not gracefully.

        Inner while loop is set by is_writing flag, and allows the writer to be paused by the user. From the main thread, use
        self.pause_writing() and self.start_writing().

        TODO:

        Scope : thread spawned in daemon_process

        """
        # ignore ctrl+c signals from main thread
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        i = 0 # loop iteration index, used for debugging

        # set niceness of this process

        os.nice(15)

        #assert isinstance(self._writer_queue, deque), "queue object doesn't appear to be correct"
        # check that a dirfile exists before starting wirter loop
        if not type(self.current_dirfile) == _gd.dirfile:
            print "no dirfile set"

        #print datapipe_out.__repr__
        datatowrite = []

        # BUFFER SIZE REQUIRED BEFORE WRITING TO DISK (# TODO: be able to change on the fly?)
        sizetowrite = roach_config[self.roachid]["buffer_len_to_write"]

        while not self._exitevent.is_set():

            # POLL PIPE TO CHECK FOR UPDATES TO DATAPACKET_DICT or CURRENT DIRFILE
            if self._datapipe_out.poll():
                pipedata = self._datapipe_out.recv()

                if not isinstance(pipedata, tuple) and len(pipedata)==2:
                    _logger.debug("data on pipe not of correct format. Found {0}".format(pipedata))
                    pass
                else:
                    command, data = pipedata
                    _logger.debug("command, data on pipe: {0},{1}".format(command, data))
                    #
                    if   command == "SET_DATAPACKET_DICT": self._datapacket_dict = data
                    elif command == "SET_FILE":            self.current_dirfile = _gd.dirfile(str(data), _gd.RDWR)
                    else :
                        _logger.warning("command not recognised {0}. nothing done.".format(command))

            c = 0
            # MAIN DATA WRITING LOOP #
            while self.is_writing.value:

                _logger.debug( "in writing loop; {0},{1}".format (len(self._writer_queue), sizetowrite) )

                # WRITE TO DISK WHEN BUFFER_LEN IS REACHED

                if (len(self._writer_queue) >= sizetowrite) or not self.is_writing.value: # not self is_writing catches last loop iteration

                    #print "len queue inside: ",len(self._writer_queue)

                    datatowrite = [self._writer_queue.pop() for i in range(len(self._writer_queue))] # get all data currently in queue
                    _logger.debug("length of datatowrite {0}".format(len(datatowrite)))

                    for packet in datatowrite:
                        count = np.frombuffer(packet[0][-9:-5],">u4")
                        if count - c > 1:
                            print self.roachid," -> Writer thread: ", c, "  ", count - c - 1, "Packets lost"
                        c = count

                    retcode = self._parse_packet_and_append_to_dirfile(datatowrite) # parse the packet using the datapacket_dict and append ot the dirfile

                    #del datatowrite
                    datatowrite = []


                else:
                    time.sleep(sizetowrite/488*0.5)

            if datatowrite:
                _logger.warning( "{0} packets didn't get saved!!".format( len(datatowrite) ) ) # just in case some data is left in the buffer
                datatowrite = []
            time.sleep(0.1)

    ########################### Queue functions ###########################

    def _add_to_queue_and_wait(self, command_to_send, timeout = 2.):

        if self.is_daemon_running():

            self._ctrlevent.set()
            _logger.debug ( "(command, value) put into queue: {0}".format(command_to_send) )
            self._eventqueue.put( command_to_send )

            # wait for the command to processes and the _ctrlevent to be reset by the daemon process (see _data_logger_main)
            timestart = time.time()
            while not self._ctrlevent.is_set():
                if (time.time() - timestart) > timeout:
                    _logger.warning ( "control event loop timeout - not set." )
                    break

                time.sleep(1e-3) # cpu saver

        else:
            _logger.debug ( " data logging daemon doesn't appear to running." )

    def _read_response_from_eventqueue(self, initial_command):
        # check if write status is the same as the command we sent. How to properly handle it if so? It most likely is due to the main daemon process being terminated
        #self.writer_alive = writer_status if writer_status != command_to_send else self.writer_alive
        #return self.writer_alive

        _logger.debug("waiting for queue to empty\r")
        while not self._cmdevent.is_set():
            sys.stdout.write("waiting for queue to empty\r")
            time.sleep(0.1)
            continue

        #sys.stdout.write("\ncommand queue empty - moving on.")
        _logger.debug("\ncommand queue empty - moving on.")
        self._cmdevent.clear()

        try:
            value_from_queue = self._eventqueue.get( timeout=.1 )
            return value_from_queue if value_from_queue != initial_command else "error"

        except mp.queues.Empty:
            _logger.warning ( "queue empty, no data returned." )
            return 'error'

    def _check_dirfile_and_datapacket_dict_match(self):
        """Function to check that the field names of the current dirfile match the fields in the datapacket_dict"""

        # get field lists while removing any field_suffix (separated by '__')
        field_list = [ fn.split('__', 1)[0] for fn in self.current_dirfile.field_list( _gd.RAW_ENTRY ) ]

        field_name_set = set( field_list )
        return len( field_name_set.difference( self._datapacket_dict.keys() ) ) == 0

    def start_daemon(self):
        # check process isn't already running
        assert not self.process.is_alive(), "writer daemon appears to be already running"

        # clear all the events before starting the process.
        #self._ctrlevent.clear()
        #self._exitevent.clear()
        #self._cmdevent.clear()

        self.process.start()
        self._filewritethread.start()

        return

    def initialise_datapacket_dict(self, tones):
        """
        (Re)initialise the datapacket dictionary according to the given list of tones. Passes new datapacket_dict
        to writer process.

        Parameters
        ----------
        tones : toneslist.Toneslist

            A pcp.tonelist.Toneslist object that is used to generate the correct field names that will be
            used to parse datapackets and write to disk.
        """

        if self.is_writing.value:
            _logger.warning (" it appears a dirfile is currently being written. Stop and retry." )
            return

        self._datapacket_dict = lib_datapackets.generate_datapacket_dict( self.roachid, tones )

        command_to_send = ("SET_DATAPACKET_DICT", self._datapacket_dict)
        self._add_to_queue_and_wait( command_to_send )

    def is_writer_thread_running(self):
        """
        Function to check whether the writer thread is running. This is a little complicated as the threading
        instance is not accessible to the main thread. Instead, send a command to the daemon_process and return the
        result from there.

        Returns a two-element bool tuple (is_writer_alive, is_writing)

        ( there is a )

        """
        # command_to_send = ("STATUS_WRITER",0)
        # # set the event to read the command
        # #self._ctrlevent.set()
        # self._add_to_queue_and_wait( command_to_send ) # need to be careful that we don't have race conditions?
        #
        # return self._read_response_from_eventqueue( command_to_send )
        return self._filewritethread.is_alive()

        # Read queue to get values returned
        # try:
        #     writer_status = self._eventqueue.get( timeout=.1 )
        #     # check if write status is the same as the command we sent. How to properly handle it if so? It most likely is due to the main daemon process being terminated
        #     #self.writer_alive = writer_status if writer_status != command_to_send else self.writer_alive
        #     #return self.writer_alive
        #     return writer_status if writer_status != command_to_send else False
        #
        # except mp.queues.Empty:
        #     print "queue empty, no data returned."
        #     return False

    def _clean_up(self):
        _logger.info( "cleaning up" )
        self._sockethandle.close()

        # join main process (assuming that it has been started)
        if self.process._popen:
            self.process.join()
        # join writer process (assuming that it has been started)
        if self._filewritethread._popen:
            self._filewritethread.join()

        # by design, writer thread will die after the daemon process is temrinated
        self.is_writing.value = False
        # close the current dirfile so as not to leave dangling file references
        if self.current_dirfile is not None:
            self.current_dirfile.close()

    def start_writing(self):
        """
        Sets the "is_writing" flag to True to being wirting to a dirfile.

        Checks that a valid dirfile is set, otherwise prints warning, returns and does nothing.

        """
        # check that a dirfile exists and is valid
        if not lib_dirfiles.is_dirfile_valid( self.current_dirfile ):
            _logger.error( "dirfile invalid - returning" )
            return

        # check that the datapacket_dict looks like it should
        if type( self._datapacket_dict ) != dict:
            _logger.error( "datapacket_dict does not appear to be valid." )
            return

        # check that fields of dirfile and dtapacket dict match - important!
        if not self._check_dirfile_and_datapacket_dict_match():
            _logger.error( "dirfile fields and datapacket dicts don't match!" )
            return

        command_to_send = ("START_WRITE", 0)
        self._add_to_queue_and_wait( command_to_send ) # need to be careful that we don't have race conditions?
        #self.is_writing.value = self._read_response_from_eventqueue( command_to_send )

    def pause_writing(self):
        command_to_send = ("STOP_WRITE", 0)
        self._add_to_queue_and_wait( command_to_send )
        self._read_response_from_eventqueue( command_to_send )

    def terminate(self):
        # setting the exitevent allows the functions to exit the main while loops in the daemon and writer thread
        self._exitevent.set()
        _logger.debug("terminating writer daemon - set exit event")
        # setting the _ctrl event is required to exit the inner loop of the daemon process
        self._ctrlevent.set()
        _logger.debug("terminating writer daemon - set control event")
        # currently, this doesn't do anything, but we could add entry in self._process_command if required
        self._eventqueue.put( ("TERMINATE",0) )

        # wait for process to finish
        while self.process.is_alive():
            continue

        # run clean up script
        self._clean_up()

    def set_active_dirfile(self, new_dirfile):#{}, field_names = [],  datatag = ""):
        """

        Function to set the current dirfile that will be used to write data.

        Scope : mainthread

        Parameters
        ----------
        new_dirfile : pygetdata.dirfile
            An existing dirfile

        Provides
        --------
        - handles input argument, appropriately setting class attributes.
        - sets the control event, and passes the dirfile object to be handled by the worker thread

        TODO:
            - allow the user to close the current dirfile?
        """

        # check that dirfile write thread is not active, else return
        if self.is_writing.value:
            _logger.warning( "it appears a dirfile is currently being written. Stop and retry." )
            return

        # check new_dirfile is valid - required to access dirfile.name to pass the filename between processes
        if not lib_dirfiles.is_dirfile_valid ( new_dirfile ):
            _logger.warning( "dirfile {0} not valid".format(new_dirfile) )
            return

        _logger.debug( "new dirfile filename".format( new_dirfile.name ) )

        command_to_send = ("SET_FILE", new_dirfile.name)
        self._add_to_queue_and_wait ( command_to_send )

        self.current_filename = self._read_response_from_eventqueue(command_to_send)
        self.current_dirfile = new_dirfile if self.current_filename == new_dirfile.name else None

    def print_status(self):
        """
        Helper function to quickly check the status of the daemon writer. Checks status of the daemon process
        as well as the writer thread, as well as printing the current dirfile name.

        """

        print "Daemon process pid={pid} is running = {daemon_running} \
                ".format(pid=self.process.pid, daemon_running=self.is_daemon_running())

        # this will get current status of the writer thread
        #self.is_writer_thread_running()

        print "Writer thread is alive = {writer_alive} and running = {writer_running} \
                ".format(writer_alive=self.is_writer_thread_running(), writer_running=self.is_writing.value)

        if isinstance(self.current_dirfile, _gd.dirfile):
            try:
                print "Current dirfile filename = {dirfname} ".format(dirfname = self.current_dirfile.name)
            except _gd.BadDirfileError:
                print "Current dirfile is closed/invalid in writer daemon. Use self.set_active_dirfile() to create new file, or pass existing dirfile to use."
        else:
            print "No dirfile set"

    def get_active_dirfile(self):
        """

        Diagnositic function to check the currently loaded dirfile

        """
        command_to_send = ("GET_FILE", 0)
        self._add_to_queue_and_wait(command_to_send)
        self.current_filename = self._read_response_from_eventqueue(command_to_send)
        _logger.info( "active dirfile {0}".format(self.current_filename) )

    def check_packets_received(self, num_packets= 101):
        """

        Diagnositic function to determine if packets are being received and collected.

        Scope : mainthread

        """
        # check that the file writer is not running
        command_to_send = ("CHECK_PACKET", num_packets)
        if not self.is_writing.value:
            self._add_to_queue_and_wait(command_to_send)
        else:
            _logger.error( "currently saving data. Stop and retry" )

        return self._read_response_from_eventqueue(command_to_send)

    def check_packet_data(self):
        """

        Diagnositic function to determine if packets are being received and collected.

        Scope : mainthread

        """
        # check that the file writer is not running
        command_to_send = ("CHECK_PACKET_DATA", None)
        if not self.is_writing.value:
            self._add_to_queue_and_wait(command_to_send)
        else:
            _logger.error( "currently saving data. Stop and retry" )

        return self._read_response_from_eventqueue(command_to_send)

        #try:
        #    packet_check = self._eventqueue.get( timeout=.1 )
        #    return packet_check if packet_check != command_to_send else False

        #except mp.queues.Empty:
        #    print "queue empty, no data returned."
        #    return False

    def clear_queue(self):
        """

        Function used to flush the queue.

        Scope : mainthread
        """
        command_to_send = ("CLEAR_QUEUE", 0)
        # check that the file writer is not running
        if not self.is_writing.value:
            self._add_to_queue_and_wait(command_to_send)

    def _process_command(self):
        """
        Internal method to handle and process any event triggered by event.set(). Note that when running,
        this is a copy of the main memory space and has direct access to the daemon process memory space,
        Also, self in this method does not update self in the main process.

        """

        def send_response_to_eventqueue( data_to_send ):
            if self._eventqueue.empty():
                self._cmdevent.set()
                _logger.debug( "putting data to send on eventqueue, {0}".format( data_to_send ) )
                self._eventqueue.put( data_to_send )
            else:
                _logger.error( "queue not empty - something bad has happened - nothing done" )

        try:
            command_to_process = self._eventqueue.get( timeout=1. )

        except mp.queues.Empty:
            _logger.error( "queue empty, nothing done" )
            return

        # make sure that the command conforms to some simple requirements
        assert  type(command_to_process) == tuple \
            and len(command_to_process) == 2 \
            and type(command_to_process[0]) == str, " item on queue not in expected format {0} ".format(command_to_process)

        command, args = command_to_process

        _logger.debug( "\nReceived command ({0}, {1})\n".format( command, args ) )
        #print  "\nReceived command ({0}, {1})\n".format( command, args )

        #  a set of if statements to handle all available options.
        if command == "SET_DATAPACKET_DICT":
            # reinitialise datapacket_dict
            self._datapacket_dict = args if isinstance(args, dict) else None
            self._datapipe_in.send( (command, self._datapacket_dict) )

        elif command == "SET_FILE":

            # don't proceed if the writer is currently saving data. Return the current dirfile name
            if self.is_writing.value:
                _logger.error( "writer is currently saving data. Stop and try again." )
                send_response_to_eventqueue( self.current_filename )
                return

            # close the current dirfile - this will probably be done in the main thread too
            lib_dirfiles.close_dirfile( self.current_dirfile )

            # extract new dirfile path from queue arguments
            new_filename = args if isinstance(args, str) else args[0] if isinstance(args, tuple) else None

            # open dirfile (note that for some reason we can't pass an open dirfilehandle between proceses)
            self.current_dirfile  = _gd.dirfile(new_filename, _gd.RDWR)

            try:
                _logger.debug( "current dirfile is {0}".format(self.current_dirfile.name) )
                self.current_filename = self.current_dirfile.name

            except:
                _logger.error( "Bad dirfile. Possibly the dirfile is closed?" )
                self.current_filename = None
                return

            # send new dirfile filename to main process
            self._datapipe_in.send( (command, self.current_filename) )
            send_response_to_eventqueue( self.current_filename )

        elif command == "GET_FILE":
            send_response_to_eventqueue( self.current_filename )

        elif command == "START_WRITE":

            # clear all packets currently in data queue
            self._writer_queue.clear()
            _logger.debug( "starting writing" )
            print "Starting writing"

            # sets the writing flag to True (see inner loop of _writer_thread_function)
            self.is_writing.value = True

            # set cmd event to indicate that the main thread can read the queue
            #send_response_to_eventqueue( self.is_writing.value )

        elif command == "STOP_WRITE":
            self.is_writing.value = False
            _logger.info( "pausing writer" )

            send_response_to_eventqueue( self.is_writing.value )

        elif command == "STATUS_WRITER":
            send_response_to_eventqueue( self._filewritethread.is_alive() )

        elif command == "CHECK_PACKET":
            # select on the socket to see if there packets are being received. Doesn't do anything with
            # the packet, and so this could be triggered by stray packets if using SOCK_RAW

            rd,wr,err = select.select([self._sockethandle],[],[], 1.)
            send_response_to_eventqueue( bool(rd) )

        elif command == "CHECK_PACKET_DATA":
            # select on the socket to see if there packets are being received. Doesn't do anything with
            # the packet, and so this could be triggered by stray packets if using SOCK_RAW

            rd,wr,err = select.select([self._sockethandle],[],[], 1.)
            send_response_to_eventqueue( self._sockethandle.recv(9000) )

        elif command == "CLEAR_QUEUE":
            print "Clearing queue with {0} packets".format(len(self._writer_queue))
            self._writer_queue.clear()
            print "Queue cleared"


        elif command == "TERMINATE":
            print "Terminating datalogger. Goodbye."

        else:
            print "command not recognised - nothing done "




# ----- graveyard ----

#         - If an empty string is given (default), then a new file path is generated in the "DIRFILE_SAVEDIR + roachid" directory,
#         with the filename given by the format in the general_config file.
#         - If a file path is given, a new dirfile will be created at the given path. If a dirfile already exists at that path, a warning
#         is printed to screen, and the existing dirfile is returned.
#         - If a dirfile object is given, a check to determine if the dirfile is valid is made and will be returned.
#
# field_names : array-like or int
#     Either a list of field names (i.e. names given in the tonelist), or a int to use the default [K000, ...K(N)]. If an empty array
#     is given (default), then roach_config["max_ntones"] is used as a default fallback.
#     Checks are carried out in lib.lib_dirfiles to make sure the correct types are given.
#
# datatag : str (optional)
#     Allows the user to provide a string that will be appended to the dirfile. Note that if data is to be appended to an existing dirfile,
#     then care should be taken to ensure that the dirfile paths are the same. If not, a new dirfile will be created.
