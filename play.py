"""Run the real game on your island.

    python play.py            plays your own island, or the starter if you don't have one yet
    python play.py atc        plays the island in that folder
    python play.py --new      makes you an island of your own and a branch to keep it on

Leave it running, because the game reloads every time you save a file, and if
something is wrong it shows on top of the game and here in the terminal.

You don't need the engine, Node or a build for any of this, since play.py gets
the game from the website and swaps in the island files from this folder.
"""
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO = os.path.dirname(os.path.abspath(__file__))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from tools import manifest  # noqa: E402  (needs the path line above)

# where the game itself comes from (set BLHS_GAME_URL to point at a different copy)
GAME = os.environ.get("BLHS_GAME_URL", "https://blhs-island-explorer.vercel.app").rstrip("/")

# maps that are published in MAPVIS but not built into the game yet get read from here
MAPVIS = "https://mapvis-atc.vercel.app"

# the folders that hold islands: practice/ is where your own starts out, islands/ has
# the finished ones, and examples/ has small ones to copy from
ROOTS = ("practice", "islands", "examples")

# the map an island runs on when its own map hasn't been painted yet (the CS Club room)
ROOM = "atc-1"

PORT = 5290
HOOK = '<script src="/_play/hook.js"></script>'
PASS_ALONG = ("Cache-Control", "Content-Encoding", "Content-Range", "Accept-Ranges", "ETag",
              "Last-Modified")

# one hint for each mistake that comes up a lot, matched against the error text
HINTS = (
    (r"no anchor named|not an anchor|no spot called",
     "check the spelling against the spots listed above"),
    (r"IndentationError|unexpected indent|unindent",
     "the spaces at the start of that line don't line up with the lines around it"),
    (r"SyntaxError|invalid syntax|unterminated|was never closed",
     "usually a missing quote, bracket or colon, on that line or the one above it"),
    (r"NameError|isn't defined|is not defined",
     "python doesn't know that name, so check the spelling and the import line at the top"),
    (r"ImportError|no module named|can't import|cannot import",
     "the import line asks for a word that doesn't exist, and docs/VOCABULARY.md has the real ones"),
    (r"no yield|not a generator",
     "a game word only does something with yield in front of it"),
    (r"TypeError",
     "a word got the wrong kind of value, like a number where it wanted text"),
)


def hint_for(text):
    for pattern, hint in HINTS:
        if re.search(pattern, text, re.I):
            return hint
    return ""


def find_islands():
    """Every island folder here, as {name: folder path}, where the name is the folder's own name."""
    found = {}
    for root in ROOTS:
        base = os.path.join(REPO, root)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            folder = os.path.join(base, name)
            if os.path.isfile(os.path.join(folder, "island.json")) and name not in found:
                found[name] = folder
    return found


def stamp(folder):
    """A number that changes whenever a file in the island is saved."""
    return max([os.path.getmtime(os.path.join(folder, n)) for n in os.listdir(folder)
                if n.endswith((".py", ".json"))] or [0.0])


def rel(folder, name=""):
    """The path from the repo's top folder, with forward slashes, so VS Code can link to it."""
    return os.path.relpath(os.path.join(folder, name), REPO).replace(os.sep, "/").rstrip("/")


_maps = {}


def spots_on(map_id):
    """The names of the spots on a map that is built into the game, or None if it isn't."""
    if map_id not in _maps:
        _maps[map_id] = None
        for base in ("maps-vendored", "maps-painted"):
            try:
                with urllib.request.urlopen("%s/%s/%s/map.json" % (GAME, base, map_id), timeout=15) as got:
                    data = json.loads(got.read().decode("utf-8"))
                _maps[map_id] = [a["name"] for a in data.get("anchors", [])]
                break
            except Exception:
                continue
    return _maps[map_id]


def on_mapvis(map_id):
    try:
        with urllib.request.urlopen("%s/api/v1/maps/%s" % (MAPVIS, map_id), timeout=15) as got:
            return got.status == 200
    except Exception:
        return False


def talks_in(folder):
    """Every @on_talk("name") in the island, as (name, file, line number)."""
    out = []
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(folder, name), encoding="utf-8-sig") as f:
            for number, line in enumerate(f, 1):
                found = re.match(r"""\s*@on_talk\(\s*["']([^"']+)["']""", line)
                if found:
                    out.append((found.group(1), name, number))
    return out


def find_line(text, folder):
    """Some errors name the thing that's wrong but not its line, so this looks the name up."""
    names = []
    found = re.search(r"(\w+)\(\) has no yield", text)
    if found:
        names.append("def " + found.group(1))
    names += re.findall(r"'([A-Za-z_]\w*)'", text)
    found = re.search(r"import name (\w+)", text)
    if found:
        names.append(found.group(1))
    for wanted in names:
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(folder, name), encoding="utf-8-sig") as f:
                for number, line in enumerate(f, 1):
                    if line.lstrip().startswith("#"):
                        continue
                    if re.search(r"(?<!\w)%s(?!\w)" % re.escape(wanted), line):
                        return name, number
    return None


def error(title, folder, name=None, line=None, detail="", hint=None):
    """Builds one error the way the terminal and the box over the game both show it."""
    where = link = ""
    if name:
        where = "%s, line %s" % (name, line) if line else name
        link = "%s:%s" % (rel(folder, name), line) if line else rel(folder, name)
    return {"title": title, "where": where, "link": link, "detail": detail,
            "hint": hint if hint is not None else hint_for(title + " " + detail)}


def check(folder, spots):
    """What is wrong with the island before the game even runs it, as a list of errors."""
    out = []
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".py"):
            continue
        try:
            with open(os.path.join(folder, name), encoding="utf-8-sig") as f:
                compile(f.read(), name, "exec")
        except SyntaxError as e:
            out.append(error("python can't read this line", folder, name, e.lineno,
                             "%s\n%s" % (e.msg, (e.text or "").rstrip())))
    try:
        for fault in manifest.faults(folder):
            out.append(error("island.json has a problem", folder, "island.json", None, fault, hint=""))
    except Exception:
        pass
    if spots is not None and not out:
        for spot, name, number in talks_in(folder):
            if spot not in spots:
                out.append(error('there is no spot called "%s" on this map' % spot, folder, name, number,
                                 "the spots on this map are %s" % ", ".join(spots)))
    return out


def lines_in(text):
    """The island's own files named in a Python traceback, as (file, line number)."""
    found = re.findall(r'File "[^"]*?([a-z_]+\.py)", line (\d+)', text)
    return [(name, int(line)) for name, line in found if name not in ("vine.py", "grape.py", "driver.py")]


def explain(text, folder):
    """Turn one line the game printed into an error a member can act on, or None."""
    def with_line(title, detail):
        hit = (lines_in(detail) or [None])[-1] or find_line(detail, folder)
        name, line = hit if hit else (None, None)
        return error(title, folder, name, line, detail.strip())

    found = re.match(r"\[pmap\] [\w-]+: island did not load: (.*)", text, re.S)
    if found:
        return with_line("the island didn't load", found.group(1))
    found = re.match(r"\[pmap\] [\w-]+: this island claims (.+?), which (?:is|are) not (?:an anchor|anchors) "
                     r"on this map\. It has: (.*)", text, re.S)
    if found:
        return error("there is no spot called %s on this map" % found.group(1), folder, None, None,
                     "the spots on this map are %s" % found.group(2))
    found = re.match(r"\[pmap\] [\w-]+: the island's opening stopped: (.*)", text, re.S)
    if found:
        return with_line("@on_start crashed", found.group(1))
    found = re.match(r"\[pmap\] [\w-]+: the island's opening was refused: (.*)", text, re.S)
    if found:
        return error("the game refused something in @on_start", folder, None, None,
                     found.group(1).replace(" · ", "\n"))
    found = re.match(r"\[pmap\] station ([\w-]+): (.*)", text, re.S)
    if found:
        return with_line('talking to "%s" crashed' % found.group(1), found.group(2))
    return None


def say(text):
    print(text, flush=True)


class Show:
    """Keeps track of which island the game is showing, where the player starts and what's wrong."""

    def __init__(self, island, at=None):
        self.lock = threading.Lock()
        self.at_asked = at
        self.switch(island)

    def switch(self, island):
        self.island = island
        self.folder = find_islands()[island]
        self.checked = []
        self.runtime = []
        self.printed = set()
        self.seen = None
        self.said_map = False
        self.map, self.platform, self.at = ROOM, False, None

    def plan(self):
        """Work out the map, where the player starts, and anything that is already wrong."""
        try:
            with open(os.path.join(self.folder, "island.json"), encoding="utf-8-sig") as f:
                wanted = json.load(f).get("map") or ROOM
        except (OSError, ValueError):
            wanted = ROOM
        spots = spots_on(wanted)
        self.map, self.platform = wanted, False
        if spots is None:
            if on_mapvis(wanted):
                self.platform = True
            else:
                self.map, spots = ROOM, spots_on(ROOM)
                if not self.said_map:
                    say("  %s's own map (%s) isn't painted yet, so it runs in the CS Club room for now"
                        % (self.island, wanted))
                    self.said_map = True
        self.checked = check(self.folder, spots)
        # start the player next to the first thing they can talk to, so pressing E works right away
        talks = [t[0] for t in talks_in(self.folder) if spots is None or t[0] in spots]
        self.at = self.at_asked or (talks[0] if talks else None)
        if self.at == "door":
            self.at = None

    def state(self, fresh=False):
        with self.lock:
            now = stamp(self.folder)
            if now != self.seen:
                self.seen = now
                self.printed = set()
                self.runtime = []
                self.plan()
                self.tell(self.checked)
            elif fresh:
                self.runtime = []
            return {"island": self.island, "stamp": "%s:%s" % (self.island, now),
                    "errors": self.checked + self.runtime}

    def url(self):
        self.state()
        q = [("scene", "pmap"), ("map", self.map), ("deep", "1")]
        if self.at:
            q.append(("at", self.at))
        q.append(("grape", "/grapes/%s/" % self.island))
        if self.platform:
            q.append(("src", "platform"))
        return "/?" + urllib.parse.urlencode(q, safe="/")

    def heard(self, text):
        """When the game prints something about the island, keep it and say it in the terminal."""
        with self.lock:
            if text.startswith("[print] "):
                say(text[8:])
            elif text.startswith("Traceback (most recent call last)"):
                # the traceback comes right after its error and it's where the line number is
                found = lines_in(text)
                if found and self.runtime and ":" not in self.runtime[-1]["link"]:
                    last = self.runtime[-1]
                    self.runtime[-1] = error(last["title"], self.folder, found[-1][0], found[-1][1], last["detail"])
                    self.tell([self.runtime[-1]])
            else:
                got = explain(text, self.folder)
                # if python already couldn't read the file, don't also say the game didn't load it
                if got and self.checked and "didn't load" in got["title"]:
                    got = None
                if got and got not in self.runtime:
                    self.runtime.append(got)
                    self.tell([got])
            return self.checked + self.runtime

    def tell(self, errors):
        for e in errors:
            key = (e["link"], e["title"], e["detail"])
            if key in self.printed:
                continue
            self.printed.add(key)
            say("")
            say("%s  %s" % (e["link"], e["title"]) if e["link"] else e["title"])
            for line in e["detail"].split("\n"):
                if line.strip():
                    say("    " + line)
            if e["hint"]:
                say("  " + e["hint"])


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    show = None

    def answer(self, status, body, ctype, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        headers = {"Cache-Control": "no-store"}
        headers.update(extra or {})
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def answer_json(self, value):
        self.answer(200, json.dumps(value).encode("utf-8"), "application/json")

    def do_GET(self):
        path, _, query = self.path.partition("?")
        asked = urllib.parse.parse_qs(query)

        # the bare address goes to the game on whichever island is being played
        if path == "/" and "scene" not in asked:
            self.send_response(302)
            self.send_header("Location", self.show.url())
            self.send_header("Content-Length", "0")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return None
        if path == "/_play/state":
            return self.answer_json(self.show.state(fresh="fresh" in asked))
        if path == "/_play/switch":
            island = (asked.get("island") or [""])[0]
            if island in find_islands():
                with self.show.lock:
                    self.show.at_asked = (asked.get("at") or [None])[0]
                    self.show.switch(island)
                say("  playing   %s" % rel(find_islands()[island]))
            return self.answer_json({"island": self.show.island})
        if path == "/_play/hook.js":
            with open(os.path.join(REPO, "tools", "play_hook.js"), "rb") as f:
                return self.answer(200, f.read(), "text/javascript; charset=utf-8")
        if path.startswith("/grapes/"):
            mine = self.island_file(path)
            if mine:
                kind = "application/json" if mine.endswith(".json") else "text/x-python"
                with open(mine, "rb") as f:
                    return self.answer(200, f.read(), kind + "; charset=utf-8")
        # nothing you do while playing gets written to the game's real records
        if path.startswith("/api/"):
            return self.answer(204, b"", "text/plain")
        return self.from_the_game()

    do_HEAD = do_GET

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        if self.path.startswith("/_play/log"):
            try:
                text = json.loads(body.decode("utf-8")).get("text", "")
            except ValueError:
                text = ""
            return self.answer_json({"errors": self.show.heard(text)})
        return self.answer(204, b"", "text/plain")

    def island_file(self, path):
        """The file in this folder for /grapes/<island>/<file>, if there is one."""
        parts = [p for p in path.split("/") if p]
        if len(parts) < 2 or len(parts) > 3:
            return None
        folder = find_islands().get(parts[1])
        if not folder:
            return None
        name = parts[2] if len(parts) == 3 else "island.json"
        if not name.endswith((".py", ".json")) or "\\" in name:
            return None
        full = os.path.join(folder, name)
        return full if os.path.isfile(full) else None

    def from_the_game(self):
        """Get anything else from the website and pass it straight through."""
        ask = urllib.request.Request(GAME + self.path, method=self.command, headers={
            "Accept-Encoding": "gzip", "User-Agent": "blhs-play"})
        if self.headers.get("Range"):
            ask.add_header("Range", self.headers["Range"])
        try:
            with urllib.request.urlopen(ask, timeout=30) as got:
                status, headers, body = got.status, got.headers, got.read()
        except urllib.error.HTTPError as e:
            status, headers, body = e.code, e.headers, e.read()
        except Exception as e:
            page = ("<h1>Can't reach the game</h1><p>play.py gets the game from %s and it didn't "
                    "answer, so check that you're online and reload the page.</p><p><small>%s</small></p>" % (GAME, e))
            return self.answer(502, page.encode("utf-8"), "text/html; charset=utf-8")

        ctype = headers.get("Content-Type", "application/octet-stream")
        extra = {k: headers[k] for k in PASS_ALONG if headers.get(k)}
        if "text/html" in ctype:
            # the only change to the game is one extra script tag in its page
            if headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            text = body.decode("utf-8", "replace")
            text = text.replace("<head>", "<head>" + HOOK, 1) if "<head>" in text else HOOK + text
            body, extra = text.encode("utf-8"), {"Cache-Control": "no-store"}
        return self.answer(status, body, ctype, extra)

    def log_message(self, fmt, *args):
        pass


class Server(ThreadingHTTPServer):
    # left off because with it on, windows lets a second copy share the port and both break
    allow_reuse_address = False
    daemon_threads = True


def git(*args):
    """Run a git command here and give back what it printed, or None if it didn't work."""
    try:
        got = subprocess.run(("git",) + args, cwd=REPO, capture_output=True, text=True)
    except OSError:
        return None
    return got.stdout.strip() if got.returncode == 0 else None


def mine():
    """The island named after the branch you're on, which is the one that's yours."""
    branch = git("branch", "--show-current")
    return branch if branch and branch in find_islands() else None


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")


def new_island(name=None):
    """Copy the starter into practice/<name> and switch to a branch with the same name."""
    name = name or os.environ.get("GITHUB_USER") or ""
    if not name and sys.stdin and sys.stdin.isatty():
        name = input("Pick a short name for your island, like maya: ")
    name = slug(name)
    if not manifest.SLUG.fullmatch(name) or name == "starter":
        raise SystemExit("that name won't work, use lower case letters and digits like maya or team-two")

    if name not in find_islands():
        starter = os.path.join(REPO, "practice", "starter")
        folder = os.path.join(REPO, "practice", name)
        os.makedirs(folder)
        for part in os.listdir(starter):
            if part.endswith(".py"):
                shutil.copyfile(os.path.join(starter, part), os.path.join(folder, part))
        with open(os.path.join(starter, "island.json"), encoding="utf-8") as f:
            info = json.load(f)
        info["programme"] = name if name != info["map"] else name + "-island"
        info["title"] = "%s's Island" % name.replace("-", " ").title()
        info["owner"] = name
        with open(os.path.join(folder, "island.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(info, f, indent=2)
            f.write("\n")
        say("  made practice/%s, which is yours" % name)

    if git("branch", "--show-current") in ("main", "master"):
        if git("switch", name) is not None or git("switch", "-c", name) is not None:
            say("  and you're on your own branch now, called %s" % name)
    return name


def already_running(island, at):
    """If play.py is already running, ask it to show this island instead of starting again."""
    q = urllib.parse.urlencode([(k, v) for k, v in (("island", island), ("at", at)) if v])
    try:
        with urllib.request.urlopen("http://localhost:%d/_play/switch?%s" % (PORT, q), timeout=2) as got:
            showing = json.loads(got.read().decode("utf-8")).get("island")
    except Exception:
        return False
    if showing != island:
        raise SystemExit("a play.py from a different folder is already using port %d, so stop that one first" % PORT)
    say("  the game is already open, so it switched to %s" % island)
    return True


def main(argv):
    argv = list(argv)

    def value_of(flag):
        if flag not in argv:
            return None
        at = argv.index(flag)
        value = argv[at + 1] if at + 1 < len(argv) else None
        del argv[at:at + 2]
        return value

    at = value_of("--at")
    file = value_of("--file")
    flags = [a for a in argv if a.startswith("--")]
    words = [a for a in argv if not a.startswith("--")]

    wanted = words[0] if words else None
    if "--new" in flags:
        wanted = new_island(wanted)
        if "--only" in flags:
            return
    islands = find_islands()
    if file:
        # F5 in VS Code passes the file that's open, so play the island that file is in
        folder = os.path.normcase(os.path.dirname(os.path.abspath(file)))
        wanted = next((n for n, f in islands.items() if os.path.normcase(f) == folder), wanted)
    if wanted and wanted not in islands:
        raise SystemExit("there's no island called %r here, the ones that exist are %s"
                         % (wanted, ", ".join(sorted(islands))))
    island = wanted or mine() or "starter"

    if already_running(island, at):
        return
    try:
        server = Server(("127.0.0.1", PORT), Handler)
    except OSError as e:
        raise SystemExit("port %d is busy and it isn't play.py using it (%s)" % (PORT, e))
    Handler.show = Show(island, at)

    url = "http://localhost:%d/" % PORT
    say("  playing   %s" % rel(islands[island]))
    say("  game      %s" % url)
    say("  the game reloads when you save, and errors show up here (ctrl+c to stop)")
    if island == "starter" and not mine():
        say("  this is the starter, so run  python play.py --new  to get an island of your own")
    Handler.show.state()

    if os.environ.get("CODESPACES"):
        # in a codespace the game opens in its own tab, so open the island's code next to it
        code = shutil.which("code")
        if code:
            subprocess.run([code, "-r", os.path.join(islands[island], "island.py")])
    elif "--no-open" not in flags:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        say("\n  stopped")


if __name__ == "__main__":
    main(sys.argv[1:])
