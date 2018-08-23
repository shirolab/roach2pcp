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
import os, sys, time, signal, select
import multiprocessing as mp, threading
import setproctitle
import logging
from collections import deque

from .lib import lib_dirfiles, lib_datapackets, lib_network

from .configuration import ROOTDIR, filesys_config, network_config

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
        # initialise some status flags
        self.is_writing = False

        # create mp.Event and mp.Queue for controlling process
        self.ctrlevent  = mp.Event()
        self.exitevent  = mp.Event()
        self.eventqueue = mp.Queue()

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

        self.start : method
            Convenience method to multiprocessing.Process.start

        """
        self.process = mp.Process( target = self.data_logger_main,
                                    name = self.process_name,
                                    args = (function_args) )
        # for convenience, add methods to object
        self.start = self.process.start

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

        udp_dest_ip = self.network_config["udp_dest_ip"]
        udp_dest_port = self.network_config["udp_dest_port"]
        buffer_len = self.network_config["buf_size"]

        #lib_network.configure_socket_and_bind(socketinstance, bindaddress, bindport, buffer_size)
        lib_network.configure_socket_and_bind(self._sockethandle, udp_dest_ip, udp_dest_port, buffer_len)

    # create file upon start up (can do this in the main thread, and then reopen the file in the worker thread)
    def _initialise_writer_thread(self, roachid):
        self._writer_queue = deque()
        self._filewritethread = threading.Thread(name = roachid + 'writer_thread', \
                                                target = self.writer_thread_function)#, args=(dirf, dq,) )

        self._filewritethread.setDaemon(True) # setting daemon here ensures that the child thread ends with the main thread

    def _clean_up(self):
        print "cleaning up"
        self._sockethandle.close()
        if self.process.
        self.process.join()


    def pause_writing(self):
        self.ctrlevent.set()
        self.eventqueue.put( ("STOP_WRITE",0) )

    def start_writing(self):
        self.ctrlevent.set()
        self.eventqueue.put( ("START_WRITE",0) )

    def terminate(self):
        self.exitevent.set()

        self.ctrlevent.set()
        self.eventqueue.put( ("TERMINATE",0) )

        while self.process.is_alive():
            continue

        self._clean_up()

        #self.process.terminate()

    def set_active_dirfile(self, dirfile_name, filetag = ""):
        assert type(filetag) == str

        # check that dirfile write thread is not active, else return
        if self.is_writing():
            print "Warning, it appears a dirfile is currently being written. Stop and retry."
            return
        # stop the writing process by sending event. This will trigger the _process_command method
        # and it should wait until there is an item in the queue to read
        self.ctrlevent.set()
        # store last oepn filename for convenience
        self._last_closed_filename = self.current_filename
        # create new filename and open new dirfile
        #self.current_filename = time.strftime("%Y%m%d-%H%M%S") + "_" + filetag
        print self.current_filename
        # send new filename to worker process
        self.eventqueue.put( ("SET_FILE", self.current_filename) )

    def parse_packet_and_append_to_dirfile(self):
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
        sizetoread = min(len(self._writer_queue), 1000)
        # get all packets in the queue
        datatowrite = [self._writer_queue.pop() for i in range(sizetoread)]
        if len(datatowrite) > 0:
        # parse packets
            datapacket_dict = lib_datapackets.parse_datapacket_dict(datatowrite)
        # append to dirfile
            #lib_dirfiles.append_to_dirfile(self.current_dirfile, datapacket_dict)
            return 0
        else:
            #print "no packets in queue"
            #time.sleep(5)
            return -1

    def writer_thread_function(self):
        while not self.exitevent.is_set():
            print "writer paused "
            while self.is_writing:
                retcode = self.parse_packet_and_append_to_dirfile()
                if retcode < 0:
                    print "no packet in queue"
            time.sleep(5)

    def data_logger_main(self):
        # ingore signal.SIGINT and handle terminate manually (allows for clean up)
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        # start writer thread
        self._filewritethread.start()

        while not self.exitevent.is_set():
            print self.is_writing
            # inner while loop, runs when no event is set
            while not self.ctrlevent.is_set():
                print "in loop"

                # read data from socket (wrap up in a function from lib_network)
                time.sleep(2)
                rd,wr,err = select.select([self._sockethandle],[],[], 0.1)
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
            self.ctrlevent.clear()
            # process event
            self._process_command()

            # self.terminate sends signal.SIGINT (kill -15, ctrl+c) to the process to kill it
            # except KeyboardInterrupt:
            #     # this is a dirty way to kill the process, but might be worthwhile
            #     print "broke out"
            #     break
        print "cleaning up"

    def _process_command(self):
        # internal method to handle and process any event triggered by event.set()
        # note that when running, this is a copy of the memory space, and so self in this
        # method does not update self in the main process
        print "event handled"

        # try to read from queue/pipe to read
        try:
            command_to_process = self.eventqueue.get( timeout=1. )

        except mp.queues.Empty:
            print "queue empty, nothing done"
            return

        assert type(command_to_process) == tuple  \
            and len(command_to_process) == 2  \
            and type(command_to_process[0]) == str

        command, args = command_to_process

        print "Received command ", command, args

        # a bunch of if statements to handle all options
        if command == "SET_FILE":
            # this should actually be something like "GET_NEW_FILEHANDLE" as this will now
            # look to use existing dirfiles if possible - i.e. warn if this has to create the dirfile
            self._last_closed_filename = self.current_filename
            self.current_filename = args if type(args) == str else args[0] if type(args) in [tuple, list, np.array] else ""

            # close old file (need access to current file handler )
            #dirfile_lib.close_file( self.current_filename )
            #self.current_dirfile = dirfile_lib.( self.current_filename )

        elif command == "STOP_WRITE":
            self.is_writing = False
            print "stopping writing"

        elif command == "START_WRITE":
            self.is_writing = True
            print "starting writing"

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
