# The words

Everything your island can ask the game to do. There are 36.

Put `yield` in front of a word and it happens. Without the `yield` nothing
happens, and no error tells you so.

Every place is the name of a spot somebody marked on the map in MAPVIS. A name
the map does not have stops your island with an error that points at your line.

Hover over a word in VS Code to see what goes in its brackets and a line you can
copy. This page is made by `python tools/vocabulary.py`, so do not edit it by hand.

## talking

| word | how you write it | what it does |
|---|---|---|
| `say` | `say(text, who=None, portrait=None)` | Shows one line in the talk box and waits for the player to click. |
| `choose` | `choose(options, prompt=None)` | Shows buttons for the player to pick from, and gives back which one they picked. |

## showing him where to go

| word | how you write it | what it does |
|---|---|---|
| `guide_to` | `guide_to(anchor)` | Puts an arrow and a trail on the map pointing to a spot, and your next line runs straight away without waiting for the player to get there. |
| `highlight` | `highlight(anchor, on=True)` | Lights up one thing on the map where it stands, with no arrow and no trail. |
| `walk_to` | `walk_to(anchor, off=None)` | Takes over the controls and walks the player to a spot, and your next line runs once they get there. |
| `look_at` | `look_at(anchor, ms=None)` | Moves the camera over to a spot for a short time, then lets it go back to following the player. |

## his own body

| word | how you write it | what it does |
|---|---|---|
| `pose` | `pose(name=None, facing=None)` | Makes the player sit, lie down or stand, or turns them to face a direction, without walking. |

## driving somebody else

| word | how you write it | what it does |
|---|---|---|
| `actor_move` | `actor_move(actor, to, off=None, facing=None, pace=None)` | Walks another character over to a spot, and your next line runs once they get there. |
| `lead_to` | `lead_to(actor, to, off=None, pace=None)` | Has a character walk ahead to a spot while the player follows behind, like a guided tour. |
| `place` | `place(actor, at, off=None, facing=None)` | Puts a character at a spot straight away with no walking, to set up a scene before it starts. |
| `actor_face` | `actor_face(actor, facing)` | Turns a character, or the player, to face something without moving them. |
| `actor_look` | `actor_look(actor, look)` | Swaps the picture a character is showing for another picture drawn for it in MAPVIS. |
| `actor_release` | `actor_release(actor=None)` | Lets a character you have been moving go back to doing its own thing. |

## paths and the camera

| word | how you write it | what it does |
|---|---|---|
| `route` | `route(path, who=None, backwards=False)` | Sends the player, a character or the ship along a path drawn in MAPVIS, and your next line runs at the end. |
| `framing` | `framing(shot, ms=None)` | Moves the camera to a shot somebody set up in MAPVIS, and your next line runs once it gets there. |
| `view` | `view(shot, ms=None)` | Moves the camera to one of five ready-made shots, and your next line runs once it gets there. |

## time and sound

| word | how you write it | what it does |
|---|---|---|
| `wait` | `wait(ms)` | Pauses your island for a while before the next line runs. |
| `wait_for` | `wait_for(anchor, ms=None)` | Waits until the player walks into a spot, and gives back True if they did. |
| `sound` | `sound(name, gain=None)` | Plays one sound effect once, and your next line runs straight away. |

## what is on the screen

| word | how you write it | what it does |
|---|---|---|
| `movie` | `movie(on=True)` | Puts black bars on the screen and takes the controls away, for a part the player only watches. |
| `objective` | `objective(text=None)` | Sets the one line at the top of the screen that tells the player what to do next. |
| `island_tasks` | `island_tasks(tasks)` | Sets your island's to-do list, which the player opens by clicking the line at the top of the screen. |
| `task_done` | `task_done(id)` | Ticks one task off your island's to-do list. |

## boats and panels

| word | how you write it | what it does |
|---|---|---|
| `ashore` | `ashore()` | Moves the player off a boat tied up at the dock and onto the dock. |
| `open` | `open(ui, wait=False)` | Opens one of the game's panels, like the planner, on top of the map. |

## something that gets a score

| word | how you write it | what it does |
|---|---|---|
| `play` | `play(beat, as_plain=None, title=None, place=None, items=None)` | Runs a scored activity, like a quiz question, and gives back the player's score. |

## the world showing the run

| word | how you write it | what it does |
|---|---|---|
| `show` | `show(anchor, visible=True)` | Makes the thing at a spot appear or disappear. |
| `fx` | `fx(name, anchor=None, data=None)` | Plays a short visual effect, like a spark, and your next line runs when it has finished. |

## going somewhere else

| word | how you write it | what it does |
|---|---|---|
| `enter` | `enter(map, at=None, cover=None)` | Takes the player to another map, the same way walking through a door does. |
| `sail_to` | `sail_to(map)` | Sails the player to another island, and the game does the whole trip for them. |
| `cutscene` | `cutscene(script)` | Always stops with an error, because the game has no stored cutscenes left to play. |
| `end_run` | `end_run()` | Ends the game and goes back to the title screen. |

## the run

| word | how you write it | what it does |
|---|---|---|
| `get` | `get(path)` | Gives back one fact about the player's game so far, like which school year they are in. |
| `set_flag` | `set_flag(flag)` | Writes down a flag, which is a note about the player that your island can read back later. |
| `award` | `award(programme=None, grade=None, tags=None, fact=None, sticker=None, badge=None)` | Puts your island's grade on the player's transcript, and shows a card telling them. |
| `log` | `log(event, data=None)` | Writes one line to the game's records for the people who run it, and the player sees nothing. |

## what you may pass

These are closed lists. Anything else is refused.

- `view(shot)`: `island`, `walk`, `close`, `ship`, `sail`
- `actor_move(pace=) and lead_to(pace=)`: `stroll`, `walk`, `run`
- `enter(cover=)`: `ceremony`, `passing`
- `open(ui)`: `planner`, `handbook`, `cords`, `chart`, `wardrobe`, `settings`, `wall`, `yearbook`, `tour`
- `get(path)`: `year`, `gpa`, `tokens`, `cords`, `flags`, `islands`, `handle`, `mode`, `graduated`, `cord_board`, `trophies`, `phase`, `picks`, `advisory`, `planned`, `rank`
