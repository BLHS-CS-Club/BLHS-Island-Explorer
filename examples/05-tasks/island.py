"""Example 5: give the player a to-do list."""
from grape import on_start, on_talk
from vine import island_tasks, objective, say, task_done

# one row for each thing the player has to do
# id is what you tick it off by and name is what the player reads
TASKS = [
    {"id": "president", "name": "Say hi to the president"},
    {"id": "trophies", "name": "Look at the trophies"},
]


@on_start
def arriving():
    yield island_tasks(TASKS)
    # the player clicks this line at the top of the screen to open the list
    yield objective("Finish your list.")


@on_talk("host")
def president():
    yield say("Hi, go take a look at our trophies.", who="host")
    yield task_done("president")


@on_talk("trophies")
def trophies():
    yield say("They're pretty shiny.")
    yield task_done("trophies")
