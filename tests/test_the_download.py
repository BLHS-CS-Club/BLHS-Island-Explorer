"""The download for school computers still has play.cmd and a Python of its own in it."""
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TheDownload(unittest.TestCase):
    def test_the_zip_brings_play_cmd_and_its_own_python(self):
        self.assertTrue(os.path.isfile(os.path.join(REPO, "play.cmd")),
                        "play.cmd is missing, so a computer without python can't start the game")

        # the downloaded folder has no .github in it, so there's no workflow to read there
        if not os.path.isdir(os.path.join(REPO, ".github")):
            self.skipTest("no .github folder here, so this is the download and not the repository")
        with open(os.path.join(REPO, ".github", "workflows", "download.yml"), encoding="utf-8") as f:
            workflow = f.read()

        # git archive only puts in what it's handed, and that list runs onto the next line
        archive = re.search(r"git archive((?:[^\n]*\\\n)*[^\n]*)", workflow)
        self.assertIsNotNone(archive, "download.yml doesn't make the zip with git archive any more")
        self.assertIn("play.cmd", archive.group(1).split(), "play.cmd isn't on the git archive line")

        python = re.search(r"zip -qr cs-club-islands\.zip python\b", workflow)
        self.assertIsNotNone(python, "download.yml doesn't add the python folder to the zip")
        self.assertRegex(workflow, r"python-[\d.]+-embed-amd64\.zip")
        self.assertRegex(workflow, r"[0-9a-f]{64}  \S+\" \| sha256sum -c -")
        self.assertRegex(workflow, r"unzip -q \S+ -d python\b")
        # the python folder goes in after git archive makes the zip and before it's uploaded
        self.assertLess(archive.start(), python.start())
        self.assertLess(python.start(), workflow.index("gh release upload"))


if __name__ == "__main__":
    unittest.main()
