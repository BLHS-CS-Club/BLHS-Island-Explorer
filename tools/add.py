"""Add an island that somebody made on the Try page.

    python tools/add.py "their link" their-name

The link is the one the Try page copies when you press Copy my link. This
puts the island in practice/their-name and checks it. It never runs their
code. It only reads it.

Add --replace to overwrite an island that is already there.
"""
import ast
import base64
import json
import os
import re
import sys
import zlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from tools import manifest  # noqa: E402  (needs the path line above)

# The biggest one file is allowed to be. A real island is a few thousand characters.
MAX_CHARS = 64000

# An island may import these two, plus its own files. Nothing else.
GAME_MODULES = ("grape", "vine")


def unpack(link):
    """The files inside a Try page link, as {name: text}."""
    found = re.search(r"#i=([A-Za-z0-9_-]+)", link)
    if not found:
        raise ValueError("That doesn't look like a Try page link. It should have #i= in it.")
    packed = found.group(1)
    data = base64.urlsafe_b64decode(packed + "=" * (-len(packed) % 4))
    try:
        island = json.loads(zlib.decompress(data, -15).decode("utf-8"))
    except Exception:
        raise ValueError("The link is cut off or damaged. Ask them to copy it again.")
    files = island.get("files") if isinstance(island, dict) else None
    if not isinstance(files, dict) or "island.py" not in files:
        raise ValueError("The link has no island.py in it.")
    return files


def problems(files):
    """Why these files can't go in, as a list of sentences. Empty means they can."""
    out = []
    own = {name[:-3] for name in files}
    for name, text in sorted(files.items()):
        if not re.fullmatch(r"[a-z_][a-z0-9_]*\.py", name):
            out.append("%s is not a file name an island can have" % name)
            continue
        if not isinstance(text, str) or len(text) > MAX_CHARS:
            out.append("%s is too big to be an island file" % name)
            continue
        try:
            tree = ast.parse(text, name)
        except SyntaxError as e:
            out.append("%s, line %s: %s" % (name, e.lineno, e.msg))
            continue
        for node in ast.walk(tree):
            wanted = []
            if isinstance(node, ast.Import):
                wanted = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                wanted = [(node.module or "").split(".")[0]]
            for module in wanted:
                if module not in GAME_MODULES and module not in own:
                    out.append("%s, line %d: imports %s. An island only imports grape, vine "
                               "and its own files." % (name, node.lineno, module or "something"))
    return out


def add(link, name, replace=False):
    if not manifest.SLUG.fullmatch(name):
        raise ValueError("%r can't be a folder name. Use lower case letters, digits and "
                         "single hyphens, like maya or team-two." % name)
    folder = os.path.join(REPO, "practice", name)
    if os.path.isdir(folder) and not replace:
        raise ValueError("practice/%s is already there. Add --replace to overwrite it." % name)

    files = unpack(link)
    wrong = problems(files)
    if wrong:
        raise ValueError("This island can't be added yet:\n  " + "\n  ".join(wrong))

    os.makedirs(folder, exist_ok=True)
    for old in os.listdir(folder):
        if old.endswith(".py"):
            os.remove(os.path.join(folder, old))
    for part, text in files.items():
        with open(os.path.join(folder, part), "w", encoding="utf-8", newline="\n") as f:
            f.write(text if text.endswith("\n") else text + "\n")

    with open(os.path.join(REPO, "practice", "starter", "island.json"), encoding="utf-8") as f:
        info = json.load(f)
    info["programme"] = name if name != info["map"] else name + "-island"
    info["title"] = "%s's Island" % name.replace("-", " ").title()
    info["owner"] = name
    info["modules"] = ["island.py"] + sorted(n for n in files if n != "island.py")
    with open(os.path.join(folder, "island.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(info, f, indent=2)
        f.write("\n")

    left = manifest.faults(folder)
    return folder, left


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__.strip())
        return 2
    try:
        folder, left = add(args[0], args[1], replace="--replace" in argv)
    except ValueError as e:
        print(e)
        return 1
    name = os.path.basename(folder)
    print("Added practice/%s." % name)
    for line in left:
        print("  island.json: " + line)
    print("")
    print("Play it:          python play.py %s" % name)
    print("Put it in git:    git add practice/%s" % name)
    print('                  git commit -m "%s has an island"' % name)
    print("                  git push")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
