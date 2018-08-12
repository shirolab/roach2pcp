# attempt at writing a logging command that can deal with wiriting a single log file from multiple processes

# use logging module (looks to be very powerful)
# Code shamlessly adapated from following cookbook example:
# https://docs.python.org/2/howto/logging-cookbook.html#sending-and-receiving-logging-events-across-a-network

# TODO
# currently this doesn't close elegantly - change that by adding appropriate exiting code
# add writing to a file, which is passed from the command line (so the same log file can be
# passed from a main control script)
# modify to suit our needs

# define a logger_server_init() funtion that runs this code in a separate process/thread
# that can be imported into the main script

import pickle
import logging, logging.handlers
import SocketServer
import struct

class LogRecordStreamHandler(SocketServer.StreamRequestHandler):
    """Handler for a streaming logging request.

    This basically logs the record using whatever logging policy is
    configured locally.
    """

    def handle(self):
        """
        Handle multiple requests - each expected to be a 4-byte length,
        followed by the LogRecord in pickle format. Logs the record
        according to whatever policy is configured locally.
        """
        while True:
            chunk = self.connection.recv(4)
            if len(chunk) < 4:
                break
            slen = struct.unpack('>L', chunk)[0]
            chunk = self.connection.recv(slen)
            while len(chunk) < slen:
                chunk = chunk + self.connection.recv(slen - len(chunk))
            obj = pickle.loads(chunk)
            logrecord = logging.makeLogRecord(obj)
            self.handleLogRecord(logrecord)

    def handleLogRecord(self, logrecord):
        # if a name is specified, we use the named logger rather than the one
        # implied by the record.
        if self.server.logname is not None:
            name = self.server.logname
        else:
            name = logrecord.name
        print "Using log name: {logname}".format(logname = name)

        logger = logging.getLogger(name)
        # N.B. EVERY record gets logged. This is because Logger.handle
        # is normally called AFTER logger-level filtering. If you want
        # to do filtering, do it at the client end.
        logger.handle(logrecord)

class LogRecordSocketReceiver(SocketServer.ThreadingTCPServer):
    """
    Simple TCP socket-based logging receiver suitable for testing.

    See here for detailed documentation:
    https://docs.python.org/2/library/socketserver.html#request-handler-objects

    This works by setting up a local asynchronous TCP server on port 9020 (i.e. threaded so that
    simultaneous requests are handled correctly) which uses the handler defined by the LogRecordStreamHandler.

    """

    allow_reuse_address = 1

    def __init__(self, host='localhost',
                 port = logging.handlers.DEFAULT_TCP_LOGGING_PORT,
                 handler = LogRecordStreamHandler):

        SocketServer.ThreadingTCPServer.__init__(self, (host, port), handler)
        self.abort = 0
        self.timeout = 1
        self.logname = None

    def serve_until_stopped(self):
        import select
        abort = 0
        while not abort:
            rd, wr, ex = select.select([self.socket.fileno()],
                                       [], [],
                                       self.timeout)
            if rd:
                self.handle_request() # is a method in ThreadingTCPServer that uses the handler to process the request
            abort = self.abort




def main():
    logging.basicConfig(
        filename = 'example.log',
        format='%(relativeCreated)5d %(name)-15s %(levelname)-8s %(message)s')
    tcpserver = LogRecordSocketReceiver()
    print('About to start TCP server...')
    tcpserver.serve_until_stopped()

if __name__ == '__main__':
    main()
