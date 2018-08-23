
import os, sys, time

# script to test out decoration of functions for use in the daemonTemplate to cleanly exit upon command

#
def add_message_handlers(original_function, message):

    """
        Generic function to add new messages
    """
    def wrapper(message):

        some_function(message)
        if message == 'test3':
            print "second message = {0}".format(message)
    return wrapper


def original_function(message):
    if message == "test":
        print "first message = {0}".format(message)
    elif message == "test2":
        print "second message = {0}".format(message)


#original_function = add_message_handlers(original_function)
