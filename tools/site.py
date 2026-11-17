"""Build the club website into site/, ready to put online.

    python tools/site.py

The site is the pages in club/ plus a copy of every island in this repo. The
game itself is not copied. The site passes every other request on to the real
game, so the club site is always the real game running the islands from here.
"""
import json
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The real game. Everything the club site doesn't have is fetched from here.
GAME = "https://blhs-island-explorer.vercel.app"

# Folders that hold islands, in the order play.py looks through them.
ROOTS = ("islands", "practice", "learn")


def _read(path):
    # utf-8-sig, because Windows editors like to add a byte order mark
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def island_files(folder):
    """The files an island is made of, as {name: text}."""
    return {name: _read(os.path.join(folder, name))
            for name in sorted(os.listdir(folder))
            if name.endswith(".py") or name == "island.json"}


def guides():
    """Every guide in learn/, in order, with its example island's files."""
    out = []
    base = os.path.join(REPO, "learn")
    if not os.path.isdir(base):
        return out
    for name in sorted(os.listdir(base)):
        path = os.path.join(base, name, "guide.json")
        if not os.path.isfile(path):
            continue
        try:
            guide = json.loads(_read(path))
        except ValueError as e:
            guide = {"title": name, "blurb": "guide.json is not valid JSON: %s" % e}
        guide["id"] = name
        guide["files"] = island_files(os.path.join(base, name))
        out.append(guide)
    return out


def roster():
    """The islands that are in the game, from islands.json."""
    path = os.path.join(REPO, "islands.json")
    if not os.path.isfile(path):
        return []
    try:
        return json.loads(_read(path)).get("islands", [])
    except ValueError:
        return []


def practice():
    """Every practice island except the starter, as rows for the club page."""
    out = []
    base = os.path.join(REPO, "practice")
    if not os.path.isdir(base):
        return out
    for name in sorted(os.listdir(base)):
        path = os.path.join(base, name, "island.json")
        if name == "starter" or not os.path.isfile(path):
            continue
        try:
            m = json.loads(_read(path))
        except ValueError:
            continue
        out.append({"folder": name, "name": m.get("title") or name,
                    "map": m.get("map"), "owner": m.get("owner")})
    return out


def club_data():
    """Everything the club pages read: the guides, the starter and the islands."""
    starter = os.path.join(REPO, "practice", "starter")
    return {
        "guides": guides(),
        "starter": island_files(starter) if os.path.isdir(starter) else {},
        "islands": roster(),
        "practice": practice(),
    }


def vercel_config():
    """How the site answers. Its own files first, then the real game for the rest."""
    return {
        "$schema": "https://openapi.vercel.sh/vercel.json",
        "redirects": [
            # The bare address opens the club page. With ?scene= it is the game.
            {"source": "/", "missing": [{"type": "query", "key": "scene"}],
             "destination": "/club/", "permanent": False},
        ],
        "rewrites": [
            # Practice never lands in the real game's records.
            {"source": "/api/:path*", "destination": "/club/lib/nothing.txt"},
            {"source": "/club/try/game/:path*", "destination": GAME + "/index.html"},
            {"source": "/((?!club/).*)", "destination": GAME + "/$1"},
        ],
        "headers": [
            {"source": "/club/(.*)",
             "headers": [{"key": "Cache-Control", "value": "no-cache"}]},
            {"source": "/grapes/(.*)",
             "headers": [{"key": "Cache-Control", "value": "no-store"}]},
        ],
    }


def build(out=None):
    """Write the whole site into `out`. Returns how many islands went in."""
    out = out or os.path.join(REPO, "site")
    os.makedirs(out, exist_ok=True)
    # Clear the last build, but keep .vercel. It remembers which Vercel project this is.
    for name in os.listdir(out):
        if name == ".vercel":
            continue
        path = os.path.join(out, name)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

    shutil.copytree(os.path.join(REPO, "club"), os.path.join(out, "club"))
    # The Play page only works next to play.py on your own machine, so it stays home.
    shutil.rmtree(os.path.join(out, "club", "play"), ignore_errors=True)
    os.makedirs(os.path.join(out, "club", "data"), exist_ok=True)
    with open(os.path.join(out, "club", "data", "guides.json"), "w", encoding="utf-8") as f:
        json.dump(club_data(), f)
    with open(os.path.join(out, "club", "lib", "nothing.txt"), "w", encoding="utf-8") as f:
        f.write("")

    count = 0
    for root in ROOTS:
        base = os.path.join(REPO, root)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            folder = os.path.join(base, name)
            target = os.path.join(out, "grapes", name)
            if not os.path.isfile(os.path.join(folder, "island.json")) or os.path.isdir(target):
                continue
            os.makedirs(target)
            for part, text in island_files(folder).items():
                with open(os.path.join(target, part), "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
            count += 1

    with open(os.path.join(out, "vercel.json"), "w", encoding="utf-8") as f:
        json.dump(vercel_config(), f, indent=2)
    return count


if __name__ == "__main__":
    where = sys.argv[1] if len(sys.argv) > 1 else None
    n = build(where)
    print("site/ is built: the club pages and %d islands." % n)
