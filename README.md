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

## Working on an island

Open this folder in VS Code and press F5, or type this in the terminal:

```
python play.py
```

A browser tab opens with the real game running your island. When you save a file the game reloads, and if your code has a mistake it shows on top of the game and in the terminal, with the file and the line. Python is the only thing you need installed, because play.py gets the game from the website and swaps your island's files into it.

The first time, run `python play.py --new`. It asks for a name, copies `practice/starter` into `practice/<name>` and puts you on a branch with that name, so your work stays apart from everybody else's.

If you can't install Python where you are (the school computers), open the repo in a Codespace from the green Code button on GitHub. That's VS Code in a browser tab with everything already set up, and the game opens beside your code.

## Getting it into the game

Commit from the Source Control tab in VS Code and press Sync, which puts your branch on GitHub. When it's ready, open a pull request. The checks that run on it are `python tools/manifest.py` and `python -m unittest`, so you can run them yourself first. Ash reviews it and merges it.

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

## Where things are

- `play.py` runs the game on your island
- `practice/` where your own island starts out. `practice/starter` is what `--new` copies
- `examples/` seven small islands that each do one thing (talk, choices, remembering, arrows, a to-do list, a scored question, a cutscene)
- `islands/` the finished islands. `islands/atc` is the CS Club's, and `islands/skeleton` is the template for one with its own map
- `docs/VOCABULARY.md` every word, generated from the engine so it can't go out of date
- `tests/` what runs on every pull request
- `vine.py` and `grape.py` the words and the hooks, kept identical to the engine's copy

Your own island and the examples run in the CS Club room, which has four spots you can use: `host` (the club president), `the_desk` (a computer), `trophies` and `the_lab` (the whole room). A finished island gets its own map from MAPVIS.

Built by the CS Club at Bonney Lake High School. We meet Wednesdays after school, 2:15 to 3:30, in room 305.
