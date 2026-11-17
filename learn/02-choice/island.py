"""Guide 2. Give the player a choice."""
from grape import on_talk
from vine import choose, say


@on_talk("host")
def talk():
    yield say("Quick question.", who="host")
    # choose shows the buttons. pick is 0 for the first one and 1 for the second.
    pick = yield choose(["Pizza", "Tacos"], prompt="Best lunch?")
    if pick == 0:
        yield say("Pizza. Solid.", who="host")
    else:
        yield say("Tacos. Bold.", who="host")
