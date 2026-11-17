"""This is your island, so change a line, save the file and watch the game reload with it."""
from grape import on_start, on_talk
from vine import choose, guide_to, objective, say


@on_start
def arriving():
    # runs once, when the player gets here
    yield objective("Go talk to the club president.")
    yield guide_to("host")


@on_talk("host")
def the_president():
    # runs when the player walks up to the president and presses E
    yield guide_to(None)
    yield say("Hey, you made it.", who="host")
    pick = yield choose(["What is this place?", "Just looking"])
    if pick == 0:
        yield say("This is the CS Club room, where we make islands for this game.", who="host")
    else:
        yield say("Look around all you want.", who="host")
    yield objective(None)
