"""Checks the starter, everyone's practice islands, the examples, and what play.py says about mistakes."""
import inspect
import os
import shutil
import tempfile
import unittest

import play
from tests import pump

# every practice island and example runs in the CS Club room, so these are the spots that exist
ROOM_SPOTS = ["host", "the_desk", "trophies", "the_lab"]


def folders(root):
    if not os.path.isdir(root):
        return []
    return [name for name in sorted(os.listdir(root))
            if os.path.isfile(os.path.join(root, name, "island.json"))]


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
                self.assertEqual(play.check(os.path.join(root, name), ROOM_SPOTS), [])

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


if __name__ == "__main__":
    unittest.main()
