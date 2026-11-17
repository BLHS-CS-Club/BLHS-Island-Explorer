"""Example 3: remember what the player did."""
from grape import on_talk
from vine import get, say, set_flag


@on_talk("host")
def talk():
    # flags is the list of things this island has written down so far
    flags = yield get("flags")
    if "met" in flags:
        yield say("Oh hey, you're back, good to see you.", who="host")
        return

    yield say("First time here? I'm the president, by the way.", who="host")
    # write it down, so next time the lines at the top run instead
    yield set_flag("met")
