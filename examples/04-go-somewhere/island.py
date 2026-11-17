"""Guide 4. Send the player somewhere."""
from grape import on_start, on_talk
from vine import guide_to, objective, say


@on_start
def arriving():
    # Runs once, when the player arrives.
    # objective is the line at the top of the screen. guide_to draws the arrow.
    yield objective("Find the trophies.")
    yield guide_to("trophies")


@on_talk("trophies")
def found_them():
    # They made it, so take the arrow and the line down.
    yield guide_to(None)
    yield objective(None)
    yield say("You found the trophies.")
