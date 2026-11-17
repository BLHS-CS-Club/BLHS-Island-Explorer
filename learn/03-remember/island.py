"""Guide 3. Remember what the player did."""
from grape import on_talk
from vine import get, say, set_flag


@on_talk("host")
def talk():
    # flags is the list of things this island has remembered so far.
    flags = yield get("flags")
    if "met" in flags:
        yield say("You again. Good to see you.", who="host")
        return

    yield say("First time here? I'm the president.", who="host")
    # Remember it. Next time, the lines at the top run.
    yield set_flag("met")
