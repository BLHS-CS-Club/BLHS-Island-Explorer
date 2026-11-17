"""Example 2: give the player a choice."""
from grape import on_talk
from vine import choose, say


@on_talk("host")
def talk():
    yield say("Okay, quick question for you.", who="host")
    # choose shows the buttons and gives back which one got picked: 0 is the first, 1 is the second
    pick = yield choose(["Pizza", "Tacos"], prompt="Best lunch?")
    if pick == 0:
        yield say("Pizza is a solid pick.", who="host")
    else:
        yield say("Tacos, okay, I respect that.", who="host")
