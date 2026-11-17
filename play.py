"""Run the real game with the islands in this folder.

    python play.py              opens the game on your islands
    python play.py my-island    opens straight on one of them

Leave it running. Save a file and the game reloads on its own.

You don't need the engine, Node or a build. This script fetches the game from
the website and swaps in the island files from this folder, so what you see is
the real game running your code.
"""
import gzip
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO = os.path.dirname(os.path.abspath(__file__))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from tools import manifest, site  # noqa: E402  (needs the path line above)

# Where the game itself comes from. Set BLHS_GAME_URL to use a different copy.
GAME = os.environ.get("BLHS_GAME_URL", "https://blhs-island-explorer.vercel.app").rstrip("/")

# Folders that hold islands. islands/ is the real ones, practice/ is where you
# try things, learn/ is the examples the guides use.
ROOTS = ("islands", "practice", "learn")

# The first port to try. It walks up from here when one is busy.
PORT = 5290
TRIES = 20

# The only kinds of file an island is made of.
ISLAND_FILES = (".py", ".json")

# Added to the game's page so it can tell the Play page what went wrong.
HOOK = '<script src="/club/lib/hook.js"></script>'

# Headers worth passing along from the website.
PASS_ALONG = ("Content-Type", "Cache-Control", "Content-Encoding", "Content-Range",
              "Accept-Ranges", "ETag", "Last-Modified")


def find_islands():
    """Every island folder here, as {name: (root, folder path)}.

    The name is the folder's own name. If two roots both have a folder with the
    same name, the first one in ROOTS wins.
    """
    found = {}
    for root in ROOTS:
        base = os.path.join(REPO, root)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            folder = os.path.join(base, name)
            if os.path.isfile(os.path.join(folder, "island.json")) and name not in found:
                found[name] = (root, folder)
    return found


def stamp(folder):
    """A number that changes whenever a file in the island is saved."""
    newest = 0.0
    for name in os.listdir(folder):
        if name.endswith(ISLAND_FILES):
            newest = max(newest, os.path.getmtime(os.path.join(folder, name)))
    return newest


def problems(folder):
    """What is wrong with this island before the game even runs it.

    Two checks: the island.json rules, and whether Python can read each file.
    A typo caught here gets a clear line number. The game's own message for
    the same typo is harder to read.
    """
    out = []
    try:
        out.extend("island.json: " + p for p in manifest.faults(folder))
    except Exception as e:  # a half-saved file should not take the server down
        out.append("island.json could not be checked: %s" % e)

    for name in sorted(os.listdir(folder)):
        if not name.endswith(".py"):
            continue
        try:
            with open(os.path.join(folder, name), encoding="utf-8-sig") as f:
                compile(f.read(), name, "exec")
        except SyntaxError as e:
            out.append("%s, line %s: %s" % (name, e.lineno, e.msg))
            if e.text:
                out.append("    " + e.text.strip())
        except Exception as e:
            out.append("%s could not be read: %s" % (name, e))
    return out


def describe(name, root, folder):
    """One island, the way the Play page lists it."""
    row = {"id": name, "root": root, "title": name, "map": None,
           "stamp": stamp(folder), "problems": problems(folder)}
    try:
        with open(os.path.join(folder, "island.json"), encoding="utf-8-sig") as f:
            m = json.load(f)
        row["title"] = m.get("title") or name
        row["map"] = m.get("map")
    except Exception:
        pass
    return row


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

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

    def answer_file(self, path):
        with open(path, "rb") as f:
            body = f.read()
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        if path.endswith(".py"):
            ctype = "text/x-python"
        if path.endswith((".js", ".mjs")):
            ctype = "text/javascript"
        if ctype.startswith("text/") or ctype == "application/json":
            ctype += "; charset=utf-8"
        self.answer(200, body, ctype)

    def do_GET(self):
        path = self.path.split("?")[0].split("#")[0]

        # The bare address opens the Play page. With ?scene= it is the game itself.
        if path == "/" and "scene=" not in self.path:
            self.send_response(302)
            self.send_header("Location", "/club/play/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None

        if path == "/_play/state":
            rows = [describe(n, r, f) for n, (r, f) in find_islands().items()]
            return self.answer_json({"game": GAME, "islands": rows})

        if path == "/club/data/guides.json":
            return self.answer_json(site.club_data())

        if path == "/club" or path.startswith("/club/"):
            return self.club(path)

        if path.startswith("/grapes/"):
            mine = self.island_file(path)
            if mine:
                return self.answer_file(mine)

        # Play does not send anything to the game's own record keeping.
        if path.startswith("/api/"):
            return self.answer(204, b"", "text/plain")

        return self.from_the_game()

    do_HEAD = do_GET

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        self.answer(204, b"", "text/plain")

    def club(self, path):
        """A page of the club site, read from the club/ folder here."""
        rel = path[len("/club"):].lstrip("/")
        full = os.path.normpath(os.path.join(REPO, "club", rel))
        if not full.startswith(os.path.join(REPO, "club")):
            return self.answer(404, b"not found", "text/plain")
        if os.path.isdir(full):
            if not path.endswith("/"):
                self.send_response(302)
                self.send_header("Location", path + "/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            full = os.path.join(full, "index.html")
        if not os.path.isfile(full):
            return self.answer(404, b"not found", "text/plain")
        return self.answer_file(full)

    def island_file(self, path):
        """The file on this machine for /grapes/<island>/<file>, if we have it."""
        parts = [p for p in path.split("/") if p]
        if len(parts) < 2 or len(parts) > 3:
            return None
        found = find_islands().get(parts[1])
        if not found:
            return None
        name = parts[2] if len(parts) == 3 else "island.json"
        if not name.endswith(ISLAND_FILES) or "\\" in name:
            return None
        full = os.path.join(found[1], name)
        return full if os.path.isfile(full) else None

    def from_the_game(self):
        """Fetch anything else from the website and pass it straight through."""
        ask = urllib.request.Request(GAME + self.path, method=self.command, headers={
            "Accept-Encoding": "gzip",
            "User-Agent": "blhs-play",
        })
        if self.headers.get("Range"):
            ask.add_header("Range", self.headers["Range"])
        try:
            with urllib.request.urlopen(ask, timeout=30) as got:
                status, headers, body = got.status, got.headers, got.read()
        except urllib.error.HTTPError as e:
            status, headers, body = e.code, e.headers, e.read()
        except Exception as e:
            page = ("<h1>Can't reach the game</h1><p>Play gets the game from %s and "
                    "that didn't answer. Check that you're online, then reload.</p>"
                    "<p><small>%s</small></p>" % (GAME, e))
            return self.answer(502, page.encode("utf-8"), "text/html; charset=utf-8")

        ctype = headers.get("Content-Type", "application/octet-stream")
        extra = {k: headers[k] for k in PASS_ALONG if headers.get(k) and k != "Content-Type"}

        # The game's own page gets one extra script tag, so it can report errors.
        if "text/html" in ctype:
            if headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            text = body.decode("utf-8", "replace")
            text = text.replace("<head>", "<head>" + HOOK, 1) if "<head>" in text else HOOK + text
            body = text.encode("utf-8")
            extra = {"Cache-Control": "no-store"}
        return self.answer(status, body, ctype, extra)

    def log_message(self, fmt, *args):
        # Quiet on purpose. The Play page shows what matters.
        pass


class Server(ThreadingHTTPServer):
    # Off, so a second copy fails loudly on Windows. With it on, both get the port.
    allow_reuse_address = False
    daemon_threads = True


def start():
    last = None
    for port in range(PORT, PORT + TRIES):
        try:
            return Server(("127.0.0.1", port), Handler), port
        except OSError as e:
            last = e
    raise SystemExit("Could not find a free port between %d and %d: %s"
                     % (PORT, PORT + TRIES - 1, last))


def main(argv):
    wanted = [a for a in argv if not a.startswith("-")]
    islands = find_islands()
    if wanted and wanted[0] not in islands:
        names = ", ".join(sorted(islands)) or "none yet"
        raise SystemExit("There is no island called %r here. The islands are: %s"
                         % (wanted[0], names))

    server, port = start()
    url = "http://localhost:%d/club/play/" % port
    if wanted:
        url += "?island=" + wanted[0]

    print("The game is running with your islands.", flush=True)
    print("", flush=True)
    print("  " + url, flush=True)
    print("", flush=True)
    print("Leave this window open. Save a file and the game reloads.", flush=True)
    print("Press Ctrl+C to stop.", flush=True)

    # A Codespace opens the page itself, so only open a browser on a real machine.
    if "--no-open" not in argv and not os.environ.get("CODESPACES"):
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
