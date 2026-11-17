"""Checks the practice islands, the guide examples and the tools around them.

The guides in the club's Drive are built from learn/, so if an example here
breaks, a guide is wrong. These tests are what keeps the two the same.
"""
import base64
import inspect
import json
import os
import shutil
import tempfile
import unittest
import zlib

from tests import pump
from tools import add, manifest, site

REPO = pump.REPO


def folders(root):
    if not os.path.isdir(root):
        return []
    return [name for name in sorted(os.listdir(root))
            if os.path.isfile(os.path.join(root, name, "island.json"))]


def vine_words():
    """Every word vine.py has, so an example can't use one that isn't real."""
    import vine
    return {name for name, value in vars(vine).items()
            if inspect.isfunction(value) and not name.startswith("_")}


class EveryPracticeIslandAndExample(unittest.TestCase):
    ROOTS = (pump.PRACTICE, pump.LEARN)

    def each(self):
        for root in self.ROOTS:
            for name in folders(root):
                yield root, name

    def test_there_is_a_starter_and_some_guides(self):
        self.assertIn("starter", folders(pump.PRACTICE))
        self.assertTrue(folders(pump.LEARN), "learn/ has no guides in it")

    def test_each_one_follows_the_island_rules(self):
        for root, name in self.each():
            with self.subTest(island=name):
                self.assertEqual(manifest.faults(os.path.join(root, name)), [])

    def test_each_one_imports_and_gives_the_game_something_to_call(self):
        for root, name in self.each():
            with self.subTest(island=name):
                pump.load(name, root)
                self.assertTrue(pump.handlers(), "%s registered nothing" % name)

    def test_every_handler_has_a_yield_in_it(self):
        import grape
        for root, name in self.each():
            pump.load(name, root)
            for key, fn in sorted(grape._handlers.items()):
                with self.subTest(island=name, handler=key):
                    self.assertTrue(inspect.isgeneratorfunction(fn))

    def test_each_one_only_talks_to_spots_the_cs_club_room_has(self):
        # They all run in the CS Club room, so these are the only names that work.
        spots = {"host", "the_desk", "trophies", "the_lab"}
        for root, name in self.each():
            pump.load(name, root)
            for key in pump.handlers():
                if key.startswith("talk:"):
                    with self.subTest(island=name, handler=key):
                        self.assertIn(key[5:], spots)

    def test_names_that_would_collide_are_caught(self):
        # play.py finds an island by its folder name, across all three folders.
        seen = {}
        for root in (pump.ISLANDS,) + self.ROOTS:
            for name in folders(root):
                self.assertNotIn(name, seen, "%s is in two folders" % name)
                seen[name] = root

    def tearDown(self):
        pump.load("skeleton")


class TheGuides(unittest.TestCase):
    def setUp(self):
        self.guides = site.guides()

    def test_every_guide_has_what_the_pages_and_the_docs_need(self):
        for g in self.guides:
            with self.subTest(guide=g["id"]):
                for key in ("title", "blurb", "how", "try", "breaks"):
                    self.assertTrue(g.get(key), "%s is missing" % key)
                self.assertEqual(len(g["try"]), 3, "three things to try, easy to hard")
                self.assertIn("island.py", g["files"])
                for row in g["breaks"]:
                    self.assertEqual(len(row), 2)

    def test_a_guide_only_teaches_words_that_exist(self):
        real = vine_words() | {"on_talk", "on_start", "if", "else", "get"}
        for g in self.guides:
            for word in g.get("words", []):
                with self.subTest(guide=g["id"], word=word):
                    self.assertIn(word, real)

    def test_the_walkthrough_examples_run_to_the_end(self):
        # Plays every handler of every example with a pretend game that says yes to everything.
        for g in self.guides:
            pump.load(g["id"], pump.LEARN)
            for key in pump.handlers():
                with self.subTest(guide=g["id"], handler=key):
                    seen = pump.run(key, pump.answering(score=4))
                    self.assertTrue(seen, "%s did nothing" % key)

    def tearDown(self):
        pump.load("skeleton")


class AddingAnIslandFromALink(unittest.TestCase):
    def link(self, files):
        squeeze = zlib.compressobj(9, zlib.DEFLATED, -15)
        raw = squeeze.compress(json.dumps({"files": files}).encode("utf-8")) + squeeze.flush()
        return "https://example.test/club/try/#i=" + base64.urlsafe_b64encode(raw).decode().rstrip("=")

    def starter(self):
        with open(os.path.join(pump.PRACTICE, "starter", "island.py"), encoding="utf-8") as f:
            return f.read()

    def test_a_link_comes_back_as_the_same_files(self):
        files = {"island.py": self.starter(), "lines.py": 'HELLO = "hi"\n'}
        self.assertEqual(add.unpack(self.link(files)), files)

    def test_a_link_that_is_not_one_is_refused(self):
        with self.assertRaises(ValueError):
            add.unpack("https://example.test/club/try/")
        with self.assertRaises(ValueError):
            add.unpack("https://example.test/club/try/#i=not-really-a-link")

    def test_an_island_that_imports_anything_else_is_refused(self):
        wrong = add.problems({"island.py": "import os\n" + self.starter()})
        self.assertTrue(any("imports os" in line for line in wrong), wrong)

    def test_an_island_may_import_its_own_files(self):
        files = {"island.py": "from lines import HELLO\n" + self.starter(), "lines.py": 'HELLO = "hi"\n'}
        self.assertEqual(add.problems(files), [])

    def test_a_typo_is_named_with_its_line(self):
        wrong = add.problems({"island.py": 'x = "unfinished\n'})
        self.assertTrue(any("island.py, line 1" in line for line in wrong), wrong)


class TheSiteBuilds(unittest.TestCase):
    def test_it_carries_the_pages_and_every_island(self):
        out = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, out)
        count = site.build(out)
        self.assertGreater(count, 0)
        self.assertTrue(os.path.isfile(os.path.join(out, "club", "try", "index.html")))
        self.assertTrue(os.path.isfile(os.path.join(out, "grapes", "starter", "island.py")))
        with open(os.path.join(out, "club", "data", "guides.json"), encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["guides"]), len(site.guides()))
        self.assertIn("island.py", data["starter"])
        # The Play page only works next to play.py, so it must not be published.
        self.assertFalse(os.path.exists(os.path.join(out, "club", "play")))


if __name__ == "__main__":
    unittest.main()
