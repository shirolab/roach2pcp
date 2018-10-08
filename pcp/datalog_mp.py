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



Usage: dl =
    x = pcp.datalog_mp.dataLogger(roachid)
        - upon instantiation, initialises both daemon process and socket
        - initalises everything required to start daemon process
    x.start()
        - starts daemon process

Useful notes:
    - x.network_config will display the current loaded configuration parameters
    - x.isrunning() and x.process.is_alive()

    - testing individual parallel functions
        -

    dirfile methods
        - set active dirfile
        - get active dirfile


"""

# test of multiprocessing
import os, sys, time, signal, select, threading
import multiprocessing as mp
import setproctitle
import logging
from collections import deque
import pygetdata as _gd

from .lib import lib_dirfiles, lib_datapackets, lib_network

from .configuration import ROOTDIR, filesys_config, network_config, roach_config

from multiprocessing.managers import BaseManager

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

    """

    def __init__(self, roachid):

        # get logger instance
        self.logger = logging.getLogger("logging.daemon.{name}".format(name = roachid))

        # make sure roachid is a string
        assert type(roachid) == str, "identifier is not a string"
        self.process_name = roachid

        # setup up attribute for dirfiles
        self.current_filename = None
        self.current_dirfile  = None
        self._sockethandle    = None

        # initialise some status flags
        self.is_writing   = False

        # check that the roachid is in the configuration files
        try:
            # get the network configuration file and store it
            self.network_config = network_config[roachid]
            # initialise the multiprocessing.Process
            self._initialise_data_logger_process( roachid )
            # initialise the socket
            self._initialise_network_config( roachid )
            # initialise packet writer thread
            self._initialise_writer_thread ( roachid )
        except KeyError:
            raise

        #self._filesys_config = filesys_config

        # create mp.Event and mp.Queue for controlling process
        self._ctrlevent  = mp.Event()
        self._exitevent  = mp.Event()
        self._eventqueue = mp.Queue()

    # -----------------------------------------------------------------------------

    def _initialise_data_logger_process(self, process_name, *function_args):
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
                                    name = self.process_name,
                                    args = (function_args) )

        # for convenience, add handle to process start method
        self.start_daemon      = self.process.start
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

        #lib_network.configure_socket_and_bind(socketinstance, bindaddress, bindport, buffer_size)
        lib_network.configure_socket_and_bind(self._sockethandle, udp_dest_ip, udp_dest_port, buffer_len)

    def _initialise_writer_thread(self, roachid):

        # set maximum queue length from configuration file (default = 1000 = 8 MB)
        self._writer_queue = deque(maxlen = roach_config["max_queue_len"])
        self._filewritethread = threading.Thread(name = roachid + 'writer_thread', \
                                                target = self._writer_thread_function)#, args=(dirf, dq,) )

        self._filewritethread.setDaemon(True) # setting daemon here ensures that the child thread ends with the main thread

    def _data_logger_main(self):
        # ingore signal.SIGINT and handle terminate manually (allows for clean up)
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        # start writer thread
        self._filewritethread.start()

        while not self._exitevent.is_set():
            print "in daemon; is writing", self.is_writing
            # inner while loop, runs when no event is set
            while not self._ctrlevent.is_set():
                #print "in main loop"

                # read data from socket (wrap up in a function from lib_network)
                #time.sleep(2)
                rd,wr,err = select.select([self._sockethandle],[],[], 0.5)
                if rd:
                    #print rd[0]
                    #pass to parallel thread for writing to disk
                    packet = self._sockethandle.recv(9000)
                    # check packet is real
                    self._writer_queue.appendleft( packet )

                continue

            # event has been set, broken out of main loop
                # stop or pause saving thread (should be able to stop and start )

            # clear event and continue to process event
            self._ctrlevent.clear()
            # process event
            self._process_command()

            # self.terminate sends signal.SIGINT (kill -15, ctrl+c) to the process to kill it
            # except KeyboardInterrupt:
            #     # this is a dirty way to kill the process, but might be worthwhile
            #     print "broke out"
            #     break
        print "cleaning up"

    def _parse_packet_and_append_to_dirfile(self):
        """
        Function to act as the worker thread for parsing packets and writing data to a dirfile.

        Parameters
        ----------
        dirfile : str
            Filename to an existing dirfile that will be written to. Note that in the pursuit of efficiency,
            this function does not check if the file exists, or that it is of the correct form. This will
            be done in "self.set_active_dirfile"

        queue : collections.deque
            Deque object with a list-like interface to act as the queue to pass data between concurrent threads.

        Notes
        -----


        """
        # gets passed the raw string data from the queue
        # handle empty queue?
        #while self.is_writing:
        # read current length of queue
        sizetoread = min(len(self._writer_queue), roach_config["max_queue_len"])
        # get all packets in the current queue
        datatowrite = [self._writer_queue.pop() for i in range(sizetoread)]
        if len(datatowrite) > 0:
            # parse packets into dictionary
            datapacket_dict = lib_datapackets.parse_datapacket_dict(datatowrite)
            # append to dirfile
            lib_dirfiles.append_to_dirfile(self.current_dirfile, datapacket_dict)
            return 0
        else:
            #print "no packets in queue"
            #time.sleep(5)
            return -1

    def _writer_thread_function(self):
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
        # check that a dirfile exists before starting wirter loop
        if not type(self.current_dirfile) == _gd.dirfile:
            print "no dirfile set"

        while not self._exitevent.is_set():
            print "writer paused"
            while self.is_writing:
                retcode = self._parse_packet_and_append_to_dirfile()
                if retcode < 0:
                    print "no packet in queue"
                else:
                    print "packet_received"
                time.sleep(4)
            time.sleep(5)

    def is_writer_thread_running(self):
        """
        Fucntion to check whether the writer thread is running. This is a little complicated as the threading
        instance is not accessible to the main thread. Instead, send a command to the daemon_process and return the
        result from there.

        Returns a two-element bool tuple (is_writer_alive, is_writing)
        """
        # set the event to read the command
        self._ctrlevent.set()
        # ask for the status
        command_to_send = ("STATUS_WRITER",0)
        self._eventqueue.put( command_to_send )
        # wait for that command to be processed, this could be more elegant (maybe using semaphores?),
        # but need to be careful as the parallel process will put new items in the queue. Simple delay seems to work ok for now
        time.sleep(0.25)

        # Read queue to get values returned
        try:
            writer_status = self._eventqueue.get( timeout=.1 )
            # check if write status is the same as the command we sent. How to properly handle it if so? It most likely is due to the main daemon process being terminated
            #self.writer_alive = writer_status if writer_status != command_to_send else self.writer_alive
            #return self.writer_alive
            return writer_status if writer_status != command_to_send else False

        except mp.queues.Empty:
            print "queue empty, no data returned."
            return False

    def _clean_up(self):
        print "cleaning up"
        self._sockethandle.close()

        # join main process (assuming that it has been started)
        # this will kill the thread too
        if self.process._popen:
            self.process.join()

        # by design, writer thread will die after the daemon process is temrinated
        self.is_writing   = False

    def pause_writing(self):
        self._ctrlevent.set()
        self._eventqueue.put( ("STOP_WRITE",0) )
        self.is_writing = False

    def start_writing(self):
        """
        Sets the "is_writing" flag to True to being wirting to a dirfile.

        Checks that a valid dirfile is set, otherwise prints warning, returns and does nothing.

        """
        # check that a dirfile exists and create one if neccessary
        if self.current_dirfile is None:
            print "No dirfile set. Use self.set_active_dirfile() to create and set a new dirfile and re-run"
            return

        self._ctrlevent.set()
        self._eventqueue.put( ("START_WRITE",0) )
        self.is_writing = True

    def terminate(self):
        # setting the exitevent allows the functions to exit the main while loops in the daemon and writer thread
        self._exitevent.set()
        # setting the _ctrl event is required to exit the inner loop of the daemon process
        self._ctrlevent.set()
        # currently, this doesn't do anything, but we could add entry in self._process_command if required
        self._eventqueue.put( ("TERMINATE",0) )

        # wait for process to finish
        while self.process.is_alive():
            continue

        # run clean up script
        self._clean_up()

    def set_active_dirfile(self, new_dirfile):
        """
        Function to set the current dirfile that will be written to.

        Parameters
        ----------
        new_dirfile : str or pygetdata.dirfile
            Either a filename path or an existing dirfile. If a filename, a new dirfile will be created
            at the given path. If a dirfile already exists at that path, an error is raised.
            If a dirfile object is given, a check to determine if the dirfile is valid is made, as well as
            checks on the field_list (tbd).

        Provides
        --------
        - handles input argument, appropriately setting class attributes.
        - sets the control event, and passes the dirfile object to be handled by the worker thread


        TODO:
            - handle baddirfile
        TODO:
            - when running this, we want to be able to do the following
                - continue writing to the existing dirfile
                - create new dirfile with YYYYMMDD_HHMMSS_tag file format

        """

        # check that dirfile write thread is not active, else return
        if self.is_writing:
            print "Warning, it appears a dirfile is currently being written. Stop and retry."
            return

        # check type of new_dirfile

        if type(new_dirfile) == str and not os.path.exists(new_dirfile):
            # create new dirfile with max tones assuming newdirfile is a path
            new_dirfile = lib_dirfiles.create_dirfile(new_dirfile, roach_config["packet_structure"]["ntones"])

        # store last open filename for convenience
        self._last_closed_filename = self.current_filename
        self._last_closed_dirfile  = self.current_dirfile

        # close previous dirfile
        lib_dirfiles.close_dirfile(self._last_closed_dirfile)
        # check new_dirfile is valid
        try:
        # create new filename and open new dirfile
            self.current_dirfile = new_dirfile
            self.current_filename = new_dirfile.name

        except _gd.BadDirfileError:
            print "invalid dirfile, maybe it is closed? returning  "
            return

        print "new dirfile filename", self.current_filename
        # sending event. This will trigger the _process_command method
        # and it should wait until there is an item in the queue to read
        self._ctrlevent.set()
        # send new filename to worker process
        self._eventqueue.put( ("SET_FILE", self.current_dirfile) )


    def print_status(self):
        """
        Helper function to quickly check the status of the daemon writer. Checks status of the daemon process
        as well as the writer thread, as well as printing the current dirfile name.

        """

        print "Daemon process pid={pid} is running = {daemon_running} \
                ".format(pid=self.process.pid, daemon_running=self.is_daemon_running())

        # this will get current status of the writer thread
        self.is_writer_thread_running()

        print "Writer thread is alive = {writer_alive} and running = {writer_running} \
                ".format(writer_alive=self.is_writer_thread_running(), writer_running=self.is_writing)

        if type(self.current_dirfile) == _gd.dirfile:
            print "Current dirfile filename = {dirfname} \
                ".format(dirfname = self.current_dirfile.name)
        else:
            print "No dirfile set"

    def _process_command(self):
        """
        Internal method to handle and process any event triggered by event.set(). Note that when running,
        this is a copy of the main memory space, and so self in this method does not update self in the main process.

        """

        print "event handled"

        # try to read from queue/pipe to read
        try:
            command_to_process = self._eventqueue.get( timeout=1. )

        except mp.queues.Empty:
            print "queue empty, nothing done"
            return

        # make sure that the command conforms to some simple requirements
        assert type(command_to_process) == tuple \
            and len(command_to_process) == 2 \
            and type(command_to_process[0]) == str

        command, args = command_to_process

        print "Received command ", command, args

        # a bunch of if statements to handle all options
        if command == "SET_FILE":
            # this should actually be something like "GET_NEW_FILEHANDLE" as this will now
            # look to use existing dirfiles if possible - i.e. warn if this has to create the dirfile

            # close old file (this might not work as expected)
            lib_dirfiles.close_dirfile( self.current_filename )
            print "closed old dirfile"

            # re-write last file name (note that when running, this will be run in parallel thread, and "self" will be different objects)

            self._last_closed_filename = self.current_filename

            self.current_filename = args if type(args) == str else args[0] if type(args) in [tuple, list] else ""
            print "current dirfile is ", self.current_filename
            # open new dirfile
            #self.current_dirfile = dirfile_lib.( self.current_filename )

        elif command == "STOP_WRITE":
            self.is_writing = False
            print "stopping writing"

        elif command == "START_WRITE":

            self.is_writing = True
            # clear queue of all packets
            self._writer_queue.clear()
            print "starting writing"

        elif command == "STATUS_WRITER":
            # handle the request for the status of the writer

            # make sure the event queue is empty and return the status of
            if self._eventqueue.empty():
                self._eventqueue.put( self._filewritethread.is_alive() )
            else:
                print "queue not empty - something bad has happened - nothing done"

        else:
            print "command not recognised"

# def test_function(event):
#
#     name = mp.current_process().name
#
#     assert type(event) == mp.synchronize.Event
#
#     print name
#
#     if name not in ["MainProcess"]:
#         setproctitle.setproctitle(setproctitle.getproctitle() + "- {name}".format(name = name))
#
#     i = 0
#     while True:
#         try:
#             while not event.is_set():
#
#                 print i; i+=1
#                 time.sleep(5)
#
#             handle_event()
#             event.clear()
#         except KeyboardInterrupt:
#             print "broke out"
#             break
