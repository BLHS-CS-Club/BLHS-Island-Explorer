"""Build everything that goes in the club's Google Drive.

    python tools/kit.py

It reads the guides in learn/ and the meeting plans in meetings/meetings.json
and writes Word and PowerPoint files into out/drive. Drive turns those into
Google Docs and Google Slides when they are uploaded.

    out/drive/Start here.docx
    out/drive/Calendar 2026-27.docx
    out/drive/Library/Guide 01 - Make someone talk.docx   (one per guide)
    out/drive/Meetings/11-18 Make someone talk/Slides.pptx
    out/drive/Meetings/11-18 Make someone talk/Run sheet.docx

To add a meeting, add it to meetings.json and run this again.
"""
import datetime
import json
import os
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches as DInches, Pt as DPt, RGBColor as DRGB
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from tools import site  # noqa: E402  (needs the path line above)

OUT = os.path.join(REPO, "out", "drive")
LOGO = os.path.join(REPO, "meetings", "art", "csc-logo.png")

# The two fonts. Both are in Google Docs and Google Slides.
FACE = "Poppins"
MONO = "Roboto Mono"

# The club's colors, taken from the slides the club already uses.
TEAL_DARK = "0D3640"
TEAL = "17515F"
TEAL_LINK = "1F7A8C"
SOFT = "8FB9C2"
INK = "1F2A2E"
GRAY = "5E6B70"
CODE_BG = "F1EFE7"


def meetings():
    with open(os.path.join(REPO, "meetings", "meetings.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    # The Classroom join code is kept out of the public repo. It lives in
    # meetings/local.json on the laptop that builds the kit: {"join": "the code"}
    local = os.path.join(REPO, "meetings", "local.json")
    cfg["club"]["join"] = ""
    if os.path.isfile(local):
        with open(local, encoding="utf-8") as f:
            cfg["club"]["join"] = json.load(f).get("join", "")
    return cfg


def join_line(club):
    """The line that shows the Classroom code, or nothing when there isn't one here."""
    return "JOIN : %s" % club["join"] if club.get("join") else ""


def plain(text):
    """The text with the <code> and <b> marks taken out, for a slide."""
    return re.sub(r"</?(code|b)>", "", text)


def pieces(text):
    """Split marked-up text into (kind, words) pairs: plain, code or bold."""
    out = []
    for part in re.split(r"(<code>.*?</code>|<b>.*?</b>)", text):
        if not part:
            continue
        if part.startswith("<code>"):
            out.append(("code", part[6:-7]))
        elif part.startswith("<b>"):
            out.append(("bold", part[3:-4]))
        else:
            out.append(("plain", part))
    return out


def long_date(iso):
    d = datetime.date.fromisoformat(iso)
    return "%s, %s %d" % (d.strftime("%A"), d.strftime("%B"), d.day)


def try_link(cfg, guide_id=None):
    url = cfg["try_url"].rstrip("/") + "/club/try/"
    return url + ("?g=" + guide_id if guide_id else "")


# ---- Word documents ----------------------------------------------------------

def new_doc():
    doc = Document()
    for section in doc.sections:
        section.left_margin = section.right_margin = DInches(0.9)
        section.top_margin = DInches(0.8)
        section.bottom_margin = DInches(0.8)
    normal = doc.styles["Normal"]
    normal.font.name = FACE
    normal.font.size = DPt(11)
    normal.font.color.rgb = DRGB.from_string(INK)
    normal.paragraph_format.space_after = DPt(6)
    normal.paragraph_format.line_spacing = 1.25
    return doc


def run_of(paragraph, text, size=None, bold=False, color=None, mono=False, italic=False):
    run = paragraph.add_run(text)
    run.font.name = MONO if mono else FACE
    run._element.rPr.rFonts.set(qn("w:eastAsia"), MONO if mono else FACE)
    if size:
        run.font.size = DPt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = DRGB.from_string(color)
    return run


def rich(paragraph, text, size=None, color=None):
    """Add marked-up text to a paragraph, with code in the code font."""
    for kind, words in pieces(text):
        if kind == "code":
            run_of(paragraph, words, size=(size or 11) - 1, mono=True, color="0B5563")
        else:
            run_of(paragraph, words, size=size, bold=(kind == "bold"), color=color)


def link(paragraph, text, url, size=None, bold=True):
    """A clickable link. python-docx has no call for one, so this builds it by hand."""
    rel = paragraph.part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    hyper = OxmlElement("w:hyperlink")
    hyper.set(qn("r:id"), rel)
    run = OxmlElement("w:r")
    props = OxmlElement("w:rPr")
    fonts = OxmlElement("w:rFonts")
    for key in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(key), FACE)
    props.append(fonts)
    if bold:
        props.append(OxmlElement("w:b"))
    color = OxmlElement("w:color")
    color.set(qn("w:val"), TEAL_LINK)
    props.append(color)
    if size:
        for key in ("w:sz", "w:szCs"):
            sz = OxmlElement(key)
            sz.set(qn("w:val"), str(int(size * 2)))
            props.append(sz)
    # Word wants these in a fixed order, and the underline comes after the size.
    under = OxmlElement("w:u")
    under.set(qn("w:val"), "single")
    props.append(under)
    run.append(props)
    words = OxmlElement("w:t")
    words.text = text
    words.set(qn("xml:space"), "preserve")
    run.append(words)
    hyper.append(run)
    paragraph._p.append(hyper)


def shade(cell, fill):
    props = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    # Shading goes before these, if the cell has them.
    for later in ("w:noWrap", "w:tcMar", "w:textDirection", "w:tcFitText", "w:vAlign", "w:hideMark"):
        found = props.find(qn(later))
        if found is not None:
            found.addprevious(shd)
            return
    props.append(shd)


def borders(table, color="C9C4B4"):
    props = table._element.tblPr
    box = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        box.append(el)
    # A little room between the words and the lines around them.
    room = OxmlElement("w:tblCellMar")
    for edge, twips in (("top", "70"), ("left", "110"), ("bottom", "70"), ("right", "110")):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:w"), twips)
        el.set(qn("w:type"), "dxa")
        room.append(el)
    # Word wants these two in a fixed place: after the alignment, before the look.
    look = props.find(qn("w:tblLook"))
    if look is not None:
        look.addprevious(box)
        look.addprevious(room)
    else:
        props.append(box)
        props.append(room)


def kicker(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = DPt(0)
    run_of(p, text.upper(), size=9, bold=True, color=TEAL_LINK)
    return p


def title(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = DPt(2)
    p.paragraph_format.line_spacing = 1.05
    run_of(p, text, size=26, bold=True, color=TEAL_DARK)
    return p


def lead(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = DPt(10)
    rich(p, text, size=13, color=GRAY)
    return p


def heading(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = DPt(14)
    p.paragraph_format.space_after = DPt(4)
    p.paragraph_format.keep_with_next = True
    run_of(p, text, size=14, bold=True, color=TEAL_DARK)
    return p


def para(doc, text, size=None):
    p = doc.add_paragraph()
    rich(p, text, size=size)
    return p


def numbered(doc, items):
    for i, item in enumerate(items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = DInches(0.3)
        p.paragraph_format.first_line_indent = DInches(-0.3)
        run_of(p, "%d.  " % i, bold=True, color=TEAL_LINK)
        rich(p, item)


def bullets(doc, items):
    for item in items:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = DInches(0.3)
        p.paragraph_format.first_line_indent = DInches(-0.2)
        run_of(p, "•  ", bold=True, color=TEAL_LINK)
        rich(p, item)


def code_block(doc, code):
    """Code in a shaded box, one paragraph per line so it copies out cleanly."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    borders(table, "D8D3C2")
    cell = table.rows[0].cells[0]
    shade(cell, CODE_BG)
    lines = code.rstrip("\n").split("\n")
    for i, line in enumerate(lines):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        p.paragraph_format.space_after = DPt(0)
        p.paragraph_format.line_spacing = 1.15
        run_of(p, line if line else " ", size=9.5, mono=True, color="1B2B2E")
    doc.add_paragraph().paragraph_format.space_after = DPt(0)
    return table


def grid(doc, head, rows, widths, link_cells=None):
    """A table with a teal header row. A cell can be text or (text, url)."""
    table = doc.add_table(rows=1, cols=len(head))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    borders(table)
    for i, words in enumerate(head):
        cell = table.rows[0].cells[i]
        shade(cell, TEAL)
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = DPt(0)
        run_of(p, words, size=10, bold=True, color="FFFFFF")
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = DPt(0)
            p.paragraph_format.line_spacing = 1.15
            if isinstance(value, tuple):
                link(p, value[0], value[1], size=10)
            else:
                rich(p, value, size=10)
    # Without this Word and Google Docs both ignore the widths and space the columns evenly.
    table.autofit = False
    for row in table.rows:
        for i, width in enumerate(widths):
            row.cells[i].width = DInches(width)
    doc.add_paragraph().paragraph_format.space_after = DPt(0)
    return table


def footer(doc, cfg):
    club = cfg["club"]
    p = doc.add_paragraph()
    p.paragraph_format.space_before = DPt(16)
    run_of(p, "BLHS CS Club  ·  %s, %s  ·  %s" % (club["day"], club["time"], club["room"]),
           size=9, color=GRAY)


def save(doc, *where):
    path = os.path.join(OUT, *where)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc.save(path)
    return path


def guide_name(n, guide):
    return "Guide %02d - %s" % (n, guide["title"])


def guide_doc(n, guide, cfg):
    doc = new_doc()
    kicker(doc, "CS Club  ·  Guide %d" % n)
    title(doc, guide["title"])
    lead(doc, guide.get("blurb", ""))

    p = doc.add_paragraph()
    if guide.get("video"):
        link(p, "Watch the video (half a minute)", guide["video"], size=12)
        run_of(p, "      ")
    link(p, "Open it in the Try page", try_link(cfg, guide["id"]), size=12)

    heading(doc, "The code")
    para(doc, "This is the whole island. The Try page opens with it already typed in.", size=10)
    code_block(doc, guide["files"].get("island.py", ""))

    heading(doc, "How it works")
    for text in guide.get("how", []):
        para(doc, text)

    heading(doc, "Try this")
    numbered(doc, guide.get("try", []))

    heading(doc, "If it breaks")
    para(doc, "The Try page shows a red box when something is wrong, and it names the line.", size=10)
    grid(doc, ["What you see", "What to do"], [list(row) for row in guide.get("breaks", [])], [2.4, 4.3])

    heading(doc, "Hand it in")
    para(doc, "Press <b>Copy my link</b> at the top of the Try page and paste it in Google Classroom. "
              "The link has your whole island in it.")
    footer(doc, cfg)
    return save(doc, "Library", guide_name(n, guide) + ".docx")


def start_here_doc(guides, cfg):
    club = cfg["club"]
    doc = new_doc()
    kicker(doc, "CS Club")
    title(doc, "Start here")
    lead(doc, "We build islands for BLHS Island Explorer, the game that shows freshmen what Bonney Lake "
              "High School has. You don't need to know how to code yet.")

    heading(doc, "The one link you need")
    p = doc.add_paragraph()
    link(p, try_link(cfg), try_link(cfg), size=13)
    para(doc, "It opens the real game next to a box of code. Change a line, press <b>Run</b>, and the game "
              "changes. There is no account to make and nothing to install.")

    heading(doc, "How a meeting goes")
    numbered(doc, [
        "A quick warm-up on the screen while people come in.",
        "A half-minute video of the thing you're about to make.",
        "You make it, in the Try page, alone or with one other person.",
        "A few people put theirs on the big screen.",
    ])

    heading(doc, "The guides")
    para(doc, "Each one is a single small idea. They build on each other, but you can jump in anywhere.")
    rows = []
    for i, g in enumerate(guides, 1):
        rows.append([
            str(i),
            (g["title"], g["doc"]) if g.get("doc") else g["title"],
            ("Watch", g["video"]) if g.get("video") else "",
            ("Open it", try_link(cfg, g["id"])),
        ])
    grid(doc, ["", "Guide", "Video", "Try page"], rows, [0.4, 3.9, 1.0, 1.4])

    heading(doc, "Keeping your work")
    para(doc, "Your code stays in the browser on the computer you used. To keep it or move it, press "
              "<b>Copy my link</b>. That link has your whole island in it and opens on any computer. "
              "Paste it in Classroom before you leave.")

    heading(doc, "What happens to your island")
    para(doc, "Islands that get turned in are added to the club's own copy of the game, where everyone can "
              "play them. The best ones go into the real game that freshmen play.")

    heading(doc, "Missed a meeting?")
    para(doc, "Open the next guide and go. Nothing depends on having been there.")

    heading(doc, "When and where")
    where = "%s, %s, %s." % (club["day"], club["time"], club["room"])
    if club.get("join"):
        where += " Google Classroom code: <b>%s</b>" % club["join"]
    para(doc, where)
    return save(doc, "Start here.docx")


KINDS = {"game": "Game", "other": "Something else", "off": "No club", "check": "Check"}


def calendar_doc(cfg):
    doc = new_doc()
    kicker(doc, "CS Club  ·  2026-27")
    title(doc, "Every meeting this year")
    lead(doc, "A draft. The meetings through December 16 are ready to run, with slides and a run sheet in "
              "the Meetings folder. Everything after winter break is a sketch to change.")
    ready = {m["date"] for m in cfg["meetings"]}
    rows = []
    for date, kind, what, note in cfg["calendar"]:
        d = datetime.date.fromisoformat(date)
        when = "%s %d" % (d.strftime("%b"), d.day)
        rows.append([
            "<b>%s</b>" % when if date in ready else when,
            KINDS.get(kind, kind),
            "<b>%s</b>" % what if date in ready else what,
            note,
            "Ready" if date in ready else "",
        ])
    grid(doc, ["Date", "Kind", "What we do", "Notes", ""], rows, [0.8, 1.2, 2.3, 2.0, 0.6])

    heading(doc, "How the year is meant to go")
    bullets(doc, [
        "<b>Now to winter break.</b> Everyone learns the basics in the CS Club room on the Try page and "
        "ends with a small island of their own. The last meeting is a show day.",
        "<b>January and February.</b> Each member picks one real thing at BLHS and builds its island, "
        "with true facts and, later, their own map.",
        "<b>March and April.</b> Playtesting and fixing. The best islands go into the real game.",
        "<b>May and June.</b> A game jam, and handing the club to next year's leads.",
    ])
    heading(doc, "The pattern")
    para(doc, "About three game meetings, then one that is something else: a show day, competition "
              "practice, or swapping islands to break them. The same thing every week gets old.")
    footer(doc, cfg)
    return save(doc, "Calendar 2026-27.docx")


def classroom_post(meeting, by_id, cfg):
    """The words to paste into Google Classroom for one meeting."""
    lines = ["Today: %s" % meeting["title"].lower(), ""]
    got = [by_id[g] for g in meeting["guides"]]
    if not got:
        lines += ["Open your island: %s" % try_link(cfg),
                  "", "Before you leave, press Copy my link and paste it here."]
        return "\n".join(lines)
    for i, g in enumerate(got):
        if i:
            lines += ["", "Done with that one? Next:"]
        if g.get("video"):
            lines.append("%sWatch (half a minute): %s" % ("1. " if not i else "", g["video"]))
        lines.append("%sOpen it: %s" % ("2. " if not i else "", try_link(cfg, g["id"])))
        if not i:
            lines.append("3. Do the three things in the Try this box on that page.")
    docs = [g["doc"] for g in got if g.get("doc")]
    if docs:
        lines += ["", "Stuck? Every line is explained here: " + "  ".join(docs)]
    lines += ["", "Before you leave, press Copy my link at the top of the Try page and paste it here."]
    return "\n".join(lines)


def run_sheet_doc(meeting, by_id, cfg):
    club = cfg["club"]
    doc = new_doc()
    kicker(doc, "CS Club  ·  Run sheet")
    title(doc, "%s: %s" % (long_date(meeting["date"]), meeting["title"]))
    lead(doc, "By 3:30 everyone has: " + meeting["leave_with"][0].lower() + meeting["leave_with"][1:])

    heading(doc, "Before people walk in")
    bullets(doc, [
        "Open the slides. They're in this folder.",
        "Open the Try page on the projector computer and press Run once, so you know it loads: "
        + try_link(cfg),
        "Have Google Classroom open in another tab, ready to post.",
    ])

    heading(doc, "The plan")
    grid(doc, ["Time", "Min", "What happens", "On screen"],
         [[row[0], row[1], row[2], row[3]] for row in meeting["plan"]], [0.7, 0.5, 4.2, 1.3])

    if meeting.get("say"):
        heading(doc, "Lines worth saying")
        bullets(doc, meeting["say"])

    if meeting.get("riddle"):
        heading(doc, "The riddle's answer")
        para(doc, meeting["riddle"]["a"])

    heading(doc, "Post this in Classroom")
    para(doc, "Post it when you reach the slide that says Open the Try page. Copy everything in the box.",
         size=10)
    code_block(doc, classroom_post(meeting, by_id, cfg))

    heading(doc, "If something goes wrong")
    bullets(doc, [
        "<b>The Try page won't open on school computers.</b> Run it on your laptop on the projector and "
        "have people call out what to change. It's still a good meeting.",
        "<b>Somebody's game is stuck loading.</b> Reload the page. Their code is still there.",
        "<b>Somebody changed computers.</b> Their code is on the old one. Copy my link moves it.",
        "<b>A red box nobody understands.</b> Take a picture of it and keep going.",
    ])

    heading(doc, "After")
    para(doc, "For every link that got turned in, run this in the islands folder on your laptop. It checks "
              "the island and adds it to the club's copy of the game.")
    code_block(doc, 'python tools/add.py "the link" their-name')
    footer(doc, cfg)
    return save(doc, "Meetings", "%s %s" % (meeting["short"], meeting["title"]), "Run sheet.docx")


# ---- slides ------------------------------------------------------------------

W = 13.333
H = 7.5
PANEL = 3.75


def rgb(value):
    return RGBColor.from_string(value)


def box(slide, x, y, w, h, fill):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(fill)
    shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def words(slide, x, y, w, h, lines, size=22, color="FFFFFF", bold=False, face=FACE, gap=6, url=None):
    """A text box. `lines` is a string or a list of strings, one paragraph each."""
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = shape.text_frame
    frame.word_wrap = True
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(frame, side, 0)
    if isinstance(lines, str):
        lines = [lines]
    for i, line in enumerate(lines):
        p = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        p.space_after = Pt(gap)
        run = p.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.name = face
        run.font.color.rgb = rgb(color)
        if url:
            run.hyperlink.address = url
            run.font.underline = True
    return shape


def button(slide, x, y, text, url, w=3.6):
    """A light button that opens a link. Link text on its own turns dark blue, which can't be read here."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(0.72))
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb("7FE0F0")
    shape.line.fill.background()
    shape.shadow.inherit = False
    shape.click_action.hyperlink.address = url
    frame = shape.text_frame
    frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    run = frame.paragraphs[0].add_run()
    run.text = text
    run.font.size = Pt(22)
    run.font.bold = True
    run.font.name = FACE
    run.font.color.rgb = rgb(TEAL_DARK)
    return shape


def chrome(slide, number):
    """What every slide has: the dark page, the lighter panel, the logo and the number."""
    box(slide, 0, 0, W, H, TEAL_DARK)
    box(slide, W - PANEL, 0, PANEL, H, TEAL)
    if os.path.isfile(LOGO):
        size = 2.55
        slide.shapes.add_picture(LOGO, Inches(W - PANEL + (PANEL - size) / 2), Inches((H - size) / 2),
                                 width=Inches(size))
    words(slide, W - 1.2, 0.38, 0.8, 0.3, "%02d" % number, size=11, color=SOFT)


def headline(slide, light, heavy, y=2.3, size=54):
    """The two-line title the club's slides use: a light line over a bold one."""
    words(slide, 0.95, y, W - PANEL - 1.5, 1.0, light, size=size, color="FFFFFF")
    words(slide, 0.95, y + size / 72 * 1.18, W - PANEL - 1.5, 2.2, heavy, size=size, color="FFFFFF",
          bold=True)


def code_on(slide, code, y, size=24):
    lines = code.split("\n")
    height = 0.42 * len(lines) + 0.5
    box(slide, 0.95, y, W - PANEL - 1.9, height, "092A32")
    words(slide, 1.2, y + 0.24, W - PANEL - 2.4, height, lines, size=size, color="E8F3F5", face=MONO, gap=2)
    return y + height


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def deck(meeting, by_id, cfg):
    club = cfg["club"]
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    blank = prs.slide_layouts[6]
    count = [0]
    plan = "\n".join("%s  %s" % (row[0], row[2]) for row in meeting["plan"])

    def new(note=""):
        slide = prs.slides.add_slide(blank)
        count[0] += 1
        chrome(slide, count[0])
        if note:
            notes(slide, note)
        return slide

    left = W - PANEL - 1.9
    got = [by_id[g] for g in meeting["guides"]]
    say = "\n".join(meeting.get("say", []))

    if not got:
        # A show day has no guide, so its slides are written out here.
        s = new(plan)
        headline(s, "SHOW DAY", "OPEN YOUR ISLAND", y=1.9)
        words(s, 0.95, 4.5, left, 0.6, "Fix one last thing. You have ten minutes.", size=24, color=SOFT)
        button(s, 0.95, 5.3, "Open the Try page", try_link(cfg), w=4.2)
        s = new(say)
        headline(s, "PASTE YOUR LINK", "SOMEBODY ELSE PLAYS IT", y=2.0, size=46)
        words(s, 0.95, 4.6, left, 1.2, "Watching someone else play is how you find out what's confusing.",
              size=24, color=SOFT)
        s = new()
        headline(s, "VOTE", "ON PAPER", y=2.0)
        words(s, 0.95, 4.5, left, 1.4, ["Funniest island.", "Best made island."], size=28)
        s = new(say)
        headline(s, "WHAT HAPPENS", "NEXT", y=1.5)
        words(s, 0.95, 3.9, left, 2.4, [
            "Over break, these islands go into the club's copy of the game.",
            "In January you pick one real thing at BLHS and build its island.",
        ], size=24, gap=14)
        s = new()
        headline(s, "SEE YOU", meeting["next"]["when"].upper(), y=1.9)
        words(s, 0.95, 4.6, left, 1.6, [line for line in (meeting["next"]["note"],
                                        "%s, %s" % (club["time"], club["room"]), join_line(club)) if line],
              size=24, color=SOFT)
        path = os.path.join(OUT, "Meetings", "%s %s" % (meeting["short"], meeting["title"]), "Slides.pptx")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        prs.save(path)
        return path

    warm = meeting["warmup"]
    riddle = meeting["riddle"]

    s = new(plan)
    words(s, 0.95, 0.75, left, 0.8, "WELCOME TO", size=40)
    words(s, 0.95, 1.4, left, 0.9, club["name"].upper(), size=40, bold=True)
    end = code_on(s, warm["code"], 2.75)
    words(s, 0.95, end + 0.25, left, 0.5, "What shows up?", size=24, color=SOFT)
    if join_line(club):
        words(s, 0.95, 6.5, left, 0.5, join_line(club), size=22)

    s = new(warm["why"])
    headline(s, "IT PRINTS", warm["answer"].upper(), y=1.7)
    words(s, 0.95, 4.4, left, 1.6, warm["why"], size=24, color=SOFT)

    s = new("The answer is on the next slide, and on the run sheet.")
    words(s, 0.95, 0.9, left, 0.6, "RIDDLE", size=28, bold=True, color=SOFT)
    words(s, 0.95, 1.9, left, 4.2, riddle["q"], size=30, gap=10)

    s = new()
    words(s, 0.95, 0.9, left, 0.6, "THE ANSWER", size=28, bold=True, color=SOFT)
    words(s, 0.95, 1.9, left, 4.2, riddle["a"], size=26, gap=10)

    s = new(say)
    headline(s, "TODAY", meeting["title"].upper(), y=1.6, size=50)
    words(s, 0.95, 4.5, left, 1.8, meeting["leave_with"], size=24, color=SOFT)

    def watch(g):
        slide = new("Click the link to play it. It opens in a new tab.")
        headline(slide, "WATCH THIS", "HALF A MINUTE", y=1.6)
        words(slide, 0.95, 4.35, left, 0.6, g["title"], size=26, color=SOFT)
        if g.get("video"):
            button(slide, 0.95, 5.15, "Play the video", g["video"])

    def tasks(g):
        slide = new("Walk around. People who finish early start the next guide.")
        words(slide, 0.95, 0.75, left, 0.6, "TRY THIS", size=28, bold=True, color=SOFT)
        words(slide, 0.95, 1.35, left, 0.8, g["title"].upper(), size=34, bold=True)
        steps = ["%d.  %s" % (i, plain(t)) for i, t in enumerate(g.get("try", []), 1)]
        words(slide, 0.95, 2.55, left, 3.6, steps, size=20, gap=14)
        words(slide, 0.95, 6.55, left, 0.5, "Stuck? Read the red box first. It names the line.", size=18,
              color=SOFT)

    watch(got[0])

    s = new("Post the Classroom post now. The words are on the run sheet.")
    headline(s, "OPEN", "THE TRY PAGE", y=1.4)
    words(s, 0.95, 3.9, left, 0.6, "The link is in Google Classroom.", size=26)
    words(s, 0.95, 4.55, left, 0.6, "No account. Nothing to install.", size=22, color=SOFT)
    button(s, 0.95, 5.4, "Open the Try page", try_link(cfg, got[0]["id"]), w=4.2)

    tasks(got[0])
    for g in got[1:]:
        watch(g)
        tasks(g)

    s = new("Free time. Nobody's island should still look like the example.")
    headline(s, "MAKE IT", "YOURS", y=1.7)
    words(s, 0.95, 4.4, left, 1.8, ["Open My island from the menu at the top.",
                                    "Your words. Your question. Your joke."], size=24, color=SOFT, gap=10)

    s = new("Two or three people. Somebody else plays it, not the person who wrote it.")
    headline(s, "SHOW IT", "THEN HAND IT IN", y=1.3, size=48)
    words(s, 0.95, 3.8, left, 2.6, [
        "1.  Press Copy my link.",
        "2.  Paste it on the projector computer. Somebody else plays it.",
        "3.  Turn the link in on Classroom before you leave.",
    ], size=22, gap=12)

    s = new()
    headline(s, "SEE YOU", meeting["next"]["when"].upper(), y=1.6)
    tail = [meeting["next"]["note"]] if meeting["next"]["note"] else []
    last = tail + ["%s, %s" % (club["time"], club["room"])] + ([join_line(club)] if join_line(club) else [])
    words(s, 0.95, 4.35, left, 2.0, last, size=24, color=SOFT, gap=8)

    path = os.path.join(OUT, "Meetings", "%s %s" % (meeting["short"], meeting["title"]), "Slides.pptx")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    prs.save(path)
    return path


def main():
    cfg = meetings()
    guides = site.guides()
    by_id = {g["id"]: g for g in guides}
    made = []
    for n, guide in enumerate(guides, 1):
        made.append(guide_doc(n, guide, cfg))
    made.append(start_here_doc(guides, cfg))
    made.append(calendar_doc(cfg))
    for meeting in cfg["meetings"]:
        made.append(run_sheet_doc(meeting, by_id, cfg))
        made.append(deck(meeting, by_id, cfg))
    for path in made:
        print(os.path.relpath(path, REPO))


if __name__ == "__main__":
    main()
