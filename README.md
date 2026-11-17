# BLHS Island Explorer

A game that shows Bonney Lake High School freshmen what the school has to offer: the clubs, the sports, the electives, the cords you can earn. You play as Thor, the school's panther, sail between islands, and every island is one real thing at the school. It runs in a browser on a school Chromebook with nothing to install.

Play it: https://blhs-island-explorer.vercel.app

![BLHS Island Explorer](docs/screenshots/title.png)

## This repository

This is where the islands live, one folder each, written in Python by BLHS CS Club members. You own a folder, nobody else edits it, and you never touch the engine. What you write runs inside the real game next to everyone else's islands.

| Repository | What it is |
| --- | --- |
| [BLHS-Island-Explorer](https://github.com/BLHS-CS-Club/BLHS-Island-Explorer) | the islands, this one |
| [BLHS-Vine](https://github.com/BLHS-CS-Club/BLHS-Vine) | the engine that runs them |
| [MAPVIS](https://github.com/ashwath-polali/MAPVIS) | the map tool the islands are painted in |

## Make your first island

You need Python and this folder, and that's all. No engine, no Node, no build.

```
python play.py
```

The game opens in your browser with the islands from this folder. Leave it running. Every time you save a file the game starts over, and if something is wrong it shows you the line.

To start your own, copy `practice/starter` to `practice/your-name` and pick it from the menu on the Play page.

There is also a Try page that does the same thing with nothing installed: the code on the left, the game on the right, and a Run button. The club's Google Classroom has the link.

## The guides

`learn/` has one tiny island for each idea, in order. Each one is the code behind a guide and a half-minute video in the club's Google Drive.

| | Guide | What you get |
| --- | --- | --- |
| 1 | Make someone talk | A character says your lines |
| 2 | Give the player a choice | A question with buttons |
| 3 | Remember what the player did | A different line the second time |
| 4 | Send the player somewhere | An arrow and a line at the top of the screen |
| 5 | Give the player a to-do list | Things tick off as they get done |
| 6 | Ask a question and score it | A real quiz question |
| 7 | Direct a scene | Black bars, a moving camera, a walk |

## The two rules

A word only happens if you yield it:

```python
yield say("You made it.")   # shows in the box and waits for the click
say("You made it.")         # nothing happens
```

Nothing calls your functions. The game does:

```python
@on_talk("host")
def meet_the_president():
    yield say("You're new here.", who="host")
```

The player walks to the spot named `host`, presses E, and the game calls that function. `@on_start` runs once when the island loads. Every word you can say is in [docs/VOCABULARY.md](docs/VOCABULARY.md).

## Where an island runs

Practice islands and the guide examples all run in the CS Club room. Its spots are `host` (the club president), `the_desk` (a computer), `trophies` and `the_lab` (the whole room).

A real island gets its own map, painted in MAPVIS, and its Python uses the spot names from that map. `islands/skeleton` is the full-size template for one, and `islands/atc` is a finished one you can read.

A real island is three files:

- `island.json` says which map it runs on and what it is
- `island.py` says what happens: who meets the player, the tasks, what each spot does when pressed
- `lines.py` is every sentence anyone says

## Getting your island into the game

1. Hand it in. Paste your Try page link in Google Classroom, or open a pull request here if you use Git.
2. The checks run. They are the same ones as `python tools/manifest.py` and `python -m unittest`.
3. Ash adds it to the club's copy of the game, where everyone can play it.

The real game that freshmen play only changes when Ash puts an island in it.

## Where things are

- `play.py` runs the game with your islands
- `practice/` where you try things. `practice/starter` is the one to copy
- `learn/` the guide examples
- `islands/` the real islands, one folder each
- `docs/VOCABULARY.md` every word, generated from the engine so it can't go out of date
- `tests/` what runs on every pull request
- `tools/` the checker, and the scripts that build the club's guides, slides and videos
- `club/` the Play page and the Try page
- `meetings/` the plan for each meeting, which the slides and run sheets are built from
- `vine.py` and `grape.py` the words and the hooks, kept identical to the engine's copy

Built by the CS Club at Bonney Lake High School. We meet Wednesdays after school, 2:15 to 3:30, in room 305.
