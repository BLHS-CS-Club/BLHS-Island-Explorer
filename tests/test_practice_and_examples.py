"""Checks the starter, everyone's practice islands, the examples, and what play.py says about mistakes."""
import inspect
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import play
from tests import pump

# the starter and the examples run in the CS Club room, and these are the spots that exist there
ROOM_SPOTS = ["host", "the_desk", "trophies", "the_lab"]


def folders(root):
    if not os.path.isdir(root):
        return []
    return [name for name in sorted(os.listdir(root))
            if os.path.isfile(os.path.join(root, name, "island.json"))]


def spots_for(folder):
    """The spots to hold an island to: the club room's, or None when it names a map of its own."""
    with open(os.path.join(folder, "island.json"), encoding="utf-8") as f:
        # a member's own map lives in MAPVIS, which these tests never call, so its spot names
        # get checked by play.py when the island is played
        return ROOM_SPOTS if json.load(f).get("map") == play.ROOM else None


class PracticeIslandsAndExamples(unittest.TestCase):
    ROOTS = (pump.PRACTICE, pump.EXAMPLES)

    def each(self):
        for root in self.ROOTS:
            for name in folders(root):
                yield root, name

    def tearDown(self):
        pump.load("skeleton")

    def test_the_starter_and_the_examples_are_there(self):
        self.assertIn("starter", folders(pump.PRACTICE))
        self.assertTrue(folders(pump.EXAMPLES))

    def test_play_finds_nothing_wrong_with_any_of_them(self):
        for root, name in self.each():
            with self.subTest(island=name):
                folder = os.path.join(root, name)
                self.assertEqual(play.check(folder, spots_for(folder)), [])

    def test_each_one_imports_and_every_handler_has_a_yield(self):
        import grape
        for root, name in self.each():
            pump.load(name, root)
            self.assertTrue(pump.handlers(), "%s gives the game nothing to call" % name)
            for key, fn in sorted(grape._handlers.items()):
                with self.subTest(island=name, handler=key):
                    self.assertTrue(inspect.isgeneratorfunction(fn))

    def test_every_example_runs_to_the_end(self):
        # plays each handler with a pretend game that answers everything
        for name in folders(pump.EXAMPLES):
            pump.load(name, pump.EXAMPLES)
            for key in pump.handlers():
                with self.subTest(example=name, handler=key):
                    self.assertTrue(pump.run(key, pump.answering(score=4)))

    def test_no_two_folders_share_a_name(self):
        # play.py finds an island by its folder name, wherever it lives
        seen = set()
        for root in (pump.ISLANDS,) + self.ROOTS:
            for name in folders(root):
                self.assertNotIn(name, seen, "%s is in two places" % name)
                seen.add(name)


class WhatPlaySaysAboutMistakes(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(dir=pump.REPO)
        self.addCleanup(shutil.rmtree, self.dir)
        self.folder = os.path.join(self.dir, "mine")
        shutil.copytree(os.path.join(pump.PRACTICE, "starter"), self.folder)

    def write(self, old, new):
        path = os.path.join(self.folder, "island.py")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn(old, text)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace(old, new))

    def test_a_missing_quote_is_named_with_its_file_and_line(self):
        self.write('yield say("Hey, you made it.", who="host")', 'yield say("Hey, you made it., who="host")')
        got = play.check(self.folder, ROOM_SPOTS)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["where"], "island.py, line 17")
        self.assertTrue(got[0]["link"].endswith("mine/island.py:17"))
        self.assertTrue(got[0]["hint"])

    def test_a_spot_that_is_not_on_the_map_is_caught_before_the_game_runs(self):
        self.write('@on_talk("host")', '@on_talk("hots")')
        got = play.check(self.folder, ROOM_SPOTS)
        self.assertEqual(len(got), 1)
        self.assertIn('"hots"', got[0]["title"])
        self.assertIn("host, the_desk", got[0]["detail"])

    def test_a_crash_while_talking_gets_its_line_looked_up(self):
        self.write('yield say("Hey, you made it.", who="host")', 'yield sya("Hey.")')
        got = play.explain("[pmap] station host: NameError: name 'sya' isn't defined", self.folder)
        self.assertEqual(got["where"], "island.py, line 17")
        self.assertIn("spelling", got["hint"])

    def test_a_crash_at_the_start_takes_its_line_from_the_traceback(self):
        text = ('[pmap] atc-1: the island\'s opening stopped: RuntimeError: no anchor named "x" on atc-1\n'
                'Traceback (most recent call last):\n  File "<stdin>", line 95, in _resume\n'
                '  File "islands/mine/island.py", line 9, in arriving\nRuntimeError: no anchor named "x"')
        got = play.explain(text, self.folder)
        self.assertEqual(got["where"], "island.py, line 9")

    def test_the_game_chatting_about_other_things_is_ignored(self):
        self.assertIsNone(play.explain("[pmap] loaded \"atc-1\" 512x512", self.folder))

    def test_the_player_starts_next_to_the_first_thing_to_talk_to(self):
        self.assertEqual([t[0] for t in play.talks_in(self.folder)], ["host"])

    def test_a_name_becomes_a_folder_name(self):
        self.assertEqual(play.slug("Alex-xel"), "alex-xel")
        self.assertEqual(play.slug("  Maya R. "), "maya-r")


class AnIslandOnItsOwnMap(unittest.TestCase):
    """A member publishes a map in MAPVIS, names it in island.json, and plays their island on it."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(dir=pump.REPO)
        self.addCleanup(shutil.rmtree, self.dir)
        self.folder = os.path.join(self.dir, "mine")
        shutil.copytree(os.path.join(pump.PRACTICE, "starter"), self.folder)
        path = os.path.join(self.folder, "island.json")
        with open(path, encoding="utf-8") as f:
            info = json.load(f)
        info["programme"], info["map"] = "mine", "my-map"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(info, f)
        path = os.path.join(self.folder, "island.py")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace('"host"', '"mayor"'))

    def show(self, published):
        """Play the island with the game not knowing the map and MAPVIS answering with these spots."""
        built_in = lambda m: ROOM_SPOTS if m == play.ROOM else None
        with mock.patch.object(play, "find_islands", return_value={"mine": self.folder}), \
                mock.patch.object(play, "spots_on", side_effect=built_in), \
                mock.patch.object(play, "on_mapvis", return_value=published), \
                mock.patch.object(play, "say"):
            show = play.Show("mine")
            return show, show.state(), show.url()

    def test_it_plays_on_the_map_from_mapvis_and_starts_at_its_first_spot(self):
        show, state, url = self.show(["mayor", "well"])
        self.assertEqual(state["errors"], [])
        self.assertEqual((show.map, show.platform, show.at), ("my-map", True, "mayor"))
        self.assertIn("map=my-map", url)
        self.assertIn("src=platform", url)

    def test_a_spot_the_map_does_not_have_is_named_with_the_ones_it_does(self):
        show, state, url = self.show(["baker", "well"])
        self.assertEqual(len(state["errors"]), 1)
        self.assertIn('"mayor"', state["errors"][0]["title"])
        self.assertIn("baker, well", state["errors"][0]["detail"])

    def test_a_map_that_is_not_published_falls_back_to_the_club_room(self):
        show, state, url = self.show(None)
        self.assertEqual((show.map, show.platform), (play.ROOM, False))
        self.assertNotIn("src=platform", url)


if __name__ == "__main__":
    unittest.main()
