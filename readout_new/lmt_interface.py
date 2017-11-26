#!/usr/bin/env python

# Daemon used to communicate with LMT infrastructure
#


# Notes from meeting with Kamal Souccar at UMASS
#
# Discussed control interface with LMT
#
# Instruments that are not tightly integrated with the telescope should save their own data independently.
# The separate LMT telescope control software can send basic commands (through e.g. CORBA) to the instrument such
# as start/stop acquisition, etc - we can work with LMT folks to refine this - but it seems like we should expect a
# very simple one-way communication from telescope to instrument.
#
# Telescope pointing information is NOT easily sent in real time to the instrument and instead saved to LMT archive,
# so we would have to grab it later.  Think about whether we want to have the instrument computer query the telescope
# computer to get semi-real time pointing that can be independently plotted so that e.g. timestreams vs mount position can
# be seen on the same screen?
#
# They are upgrading to GPS for timestamping - should hopefully be easy to pipe same 1pps into ROACH.  Even if not, with
# good independent timestamps on both ROACH and telescope, should not be hard to reconstruct pointing.
#
# Kamal has prototype software (for Toltec backend) to save data off a ROACH running Sam's firmware.  If possible we'd
# like to use this too with minimal modifications, if any.
#
# AIs:
# Write down high-level block diagram of interface, plus a general sequence of events for observing
# Look into GPS timing with current firmware
# Get a copy Kamal's software running in lab at Chicago
