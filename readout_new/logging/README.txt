Logging README file

Logging is potentially complicated by the requirement for multiple processes wanting to write to the same log file concurrently. This has been well documented and can be handled in a number of ways with the stdlib logging module. Here we try two such methods:

1. Set up a ThreadedTCPServer that listens on a port and handles entries sent from different clients. There is a ready-made cook-book example in the docs, so I’ve started here. In addition, this might be more flexible, as this should be capable of handling entries from multiple machines (i.e. the LMT interface, housekeeping computers).

2. Set up a multiprocessing.Queue to achieve the same thing. I believe this is implemented in Python 3.2, but not 2.7. However, it shouldn’t be hard to configure. 

Eater way, this code should run in a separate, possibly daemon, process. 

20180101 
	- implemented first version of daemon logging program using rationale 1 as described above. 
	- critical point was to add files_preserve argument to preserve logging handles alive when daemonising the process!




