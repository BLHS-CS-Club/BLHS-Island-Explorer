"""Example 1: make someone talk."""
from grape import on_talk
from vine import say


@on_talk("host")
def talk():
    # every say is one line in the box, and the player clicks to get the next one
    yield say("Hey. Welcome to the CS Club.", who="host")
    yield say("Everything I say is one line of Python.", who="host")
    yield say("Change my lines, save, and talk to me again.", who="host")
