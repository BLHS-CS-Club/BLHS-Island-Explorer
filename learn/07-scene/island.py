"""Guide 7. Direct a scene the player watches."""
from grape import on_talk
from vine import as_a_cutscene, look_at, say, walk_to


def the_tour():
    yield say("Let me show you around.", who="host")
    # look_at moves the camera. The number is how long it takes, in milliseconds.
    yield look_at("trophies", ms=1500)
    yield say("Those are our trophies.", who="host")
    yield look_at("the_desk", ms=1500)
    yield say("And that computer is where the game gets made.", who="host")
    # look_at(None) gives the camera back. walk_to walks the player over.
    yield look_at(None)
    yield walk_to("the_desk")


@on_talk("host")
def talk():
    # as_a_cutscene puts the black bars up and takes them down at the end.
    yield from as_a_cutscene(the_tour())
