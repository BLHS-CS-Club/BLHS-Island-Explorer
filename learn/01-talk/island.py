"""Guide 1. Make someone talk."""
from grape import on_talk
from vine import say


@on_talk("host")
def talk():
    # Each say is one line in the box. The player clicks to get the next one.
    yield say("Hey. Welcome to the CS Club.", who="host")
    yield say("Everything I say is one line of Python.", who="host")
    yield say("Change my lines, press Run, and talk to me again.", who="host")
