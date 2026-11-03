#!/usr/bin/env python3
"""
Generates the dynamic parts of the profile README.

  03 / Projects & Activity  -> repositories, recent commits, contribution heatmap
  04. Tech Stack & Connect  -> logos and links (static, but drawn in the same typography)

Data sources (public data only):
  - repositories + commits : GitHub REST API (the built-in Actions token is used only
                             to avoid rate limits; no personal token is needed)
  - contribution heatmap   : GitHub's public contributions page for the profile, no token.
                             The numbers are cross-checked against the page's own total;
                             if anything looks off the heatmap is not drawn.

Typography
  Everything is drawn as vector outlines, so it looks identical on every device.
  Headings use Berghan. Berghan is a licensed font, so it is never committed to the repo.
  Provide it in ONE of these ways (see scripts/SETUP.md):
    - env BERGHAN_FONT_B64  (GitHub Actions secret, base64 of a subset font), or
    - a local file fonts/Berghan.otf|ttf (git-ignored) when running on your own machine.
  Without it the script still works and falls back to Jost (open licence).

Only the blocks between the marker comments in README.md are rewritten, so the Hero and
About sections are never touched. Output is deterministic (no timestamps), so the
workflow commits only when something really changed.
"""
import base64
import datetime as dt
import io
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "generated"
ICONS = ROOT / "assets" / "icons"
FONTS = ROOT / "fonts"
README = ROOT / "README.md"

USER = os.environ.get("GH_USER") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "mehroofsaba"
TOKEN = os.environ.get("GH_TOKEN", "")

# ---- things you may want to edit -------------------------------------------

TAGLINE_4 = "the tools in my little universe."
SIGNOFF = "i’ll be here, probably fixing something."
LEETCODE_URL = "https://leetcode.com/u/MEHroof/"
INSTAGRAM_URL = "https://www.instagram.com/ms_37ann/"
LINKEDIN_URL = "https://www.linkedin.com/in/mehroof-saba-295484329/"

MAX_REPOS = int(os.environ.get("MAX_REPOS", "0"))  # 0 = show every repository
EXCLUDE = {x.strip().lower() for x in os.environ.get("EXCLUDE_REPOS", "").split(",") if x.strip()}
COMMITS_SHOWN = 8
REPOS_SCANNED_FOR_COMMITS = 15
DISPLAY_STROKE = 0.3  # px; Berghan is very thin, this keeps small sizes legible. Set 0 to disable.

# ---- palette (sampled from the Hero / About images) ------------------------
BG = "#000000"
CARD = "#171819"
BORDER = "#41413E"
HEAD = "#E3CDBD"    # warm blush-champagne used by the headings
BODY = "#CDBDB0"
MUTED = "#968A80"
LINE = "#6b5f56"
BLUSH = "#D9A9A3"
HEAT = ["#1f2021", "#3a3532", "#6c5f58", "#A8978C", "#E3CDBD"]

MARKERS = {
    "projects": ("<!-- PROJECTS_ACTIVITY:START -->", "<!-- PROJECTS_ACTIVITY:END -->"),
    "tech": ("<!-- TECH_CONNECT:START -->", "<!-- TECH_CONNECT:END -->"),
}


# ---- fonts -----------------------------------------------------------------
class Face:
    def __init__(self, tt):
        self.tt = tt
        self.gs = tt.getGlyphSet()
        self.cmap = tt.getBestCmap()
        self.upem = tt["head"].unitsPerEm
        self.hmtx = tt["hmtx"]

    def has(self, ch):
        return ord(ch) in self.cmap

    def advance(self, ch):
        return self.hmtx[self.cmap[ord(ch)]][0]

    def path(self, ch):
        pen = SVGPathPen(self.gs, ntos=lambda v: str(int(round(v))))
        self.gs[self.cmap[ord(ch)]].draw(pen)
        return pen.getCommands()


def load_berghan():
    b64 = os.environ.get("BERGHAN_FONT_B64", "").strip()
    try:
        if b64:
            return Face(TTFont(io.BytesIO(base64.b64decode(b64))))
        for ext in ("otf", "ttf"):
            p = FONTS / f"Berghan.{ext}"
            if p.exists():
                return Face(TTFont(str(p)))
    except Exception as e:
        print(f"WARNING: could not load Berghan ({e}).", file=sys.stderr)
    return None


BERGHAN = load_berghan()
JOST_L = Face(TTFont(str(FONTS / "Jost-Light.ttf")))
JOST_R = Face(TTFont(str(FONTS / "Jost-Regular.ttf")))
if BERGHAN is None:
    print("WARNING: Berghan not found, headings fall back to Jost. See scripts/SETUP.md.", file=sys.stderr)

DISPLAY = ([BERGHAN] if BERGHAN else []) + [JOST_R]
BODYF = [JOST_L, JOST_R]
LABEL = [JOST_R]


def _pick(faces, ch):
    return next((f for f in faces if f.has(ch)), None)


def measure(s, size, faces, spacing=0.0):
    total = 0.0
    for ch in s:
        f = _pick(faces, ch)
        total += (f.advance(ch) * size / f.upem if f else size * 0.4) + spacing
    return max(0.0, total - spacing) if s else 0.0


def fit(s, size, faces, maxw, spacing=0.0):
    w = measure(s, size, faces, spacing)
    return size if w <= maxw else size * maxw / w


def ellipsize(s, size, faces, maxw):
    if measure(s, size, faces) <= maxw:
        return s
    while s and measure(s.rstrip() + "…", size, faces) > maxw:
        s = s[:-1]
    return s.rstrip() + "…"


def wrap_px(s, size, faces, maxw, max_lines):
    lines, cur = [], ""
    for w in " ".join(str(s).split()).split(" "):
        trial = f"{cur} {w}".strip()
        if cur and measure(trial, size, faces) > maxw:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1] + " …"
    return [ellipsize(l, size, faces, maxw) for l in lines]


# ---- SVG canvas ------------------------------------------------------------
def attr(s):
    return escape(str(s), {'"': "&quot;"})


class Doc:
    def __init__(self, w, h, label):
        self.w, self.h, self.label = w, h, label
        self.defs, self.ids, self.body = [], {}, []

    def raw(self, s):
        self.body.append(s)

    def _gid(self, face, ch):
        key = (id(face), ch)
        if key not in self.ids:
            d = face.path(ch)
            if not d:
                self.ids[key] = None
            else:
                gid = f"g{len(self.ids)}"
                self.defs.append(f'<path id="{gid}" d="{d}"/>')
                self.ids[key] = gid
        return self.ids[key]

    def text(self, x, y, s, size, fill, faces, anchor="start", spacing=0.0, stroke=0.0):
        width = measure(s, size, faces, spacing)
        x0 = x if anchor == "start" else x - width / 2 if anchor == "middle" else x - width
        cx, parts = 0.0, []
        for ch in s:
            f = _pick(faces, ch)
            if f is None:
                cx += size * 0.4 + spacing
                continue
            k = size / f.upem
            gid = self._gid(f, ch)
            if gid:
                st = f' stroke="{fill}" stroke-width="{stroke / k:.0f}" stroke-linejoin="round"' if stroke else ""
                parts.append(
                    f'<use xlink:href="#{gid}" transform="translate({x0 + cx:.1f} {y}) scale({k:.5f} {-k:.5f})"{st}/>'
                )
            cx += f.advance(ch) * k + spacing
        self.body.append(f'<g fill="{fill}">' + "".join(parts) + "</g>")
        return width

    def sparkle(self, cx, cy, r, fill):
        q = r * 0.14
        self.body.append(
            f'<path fill="{fill}" d="M{cx} {cy - r} Q{cx + q} {cy - q} {cx + r} {cy} Q{cx + q} {cy + q} {cx} {cy + r} '
            f'Q{cx - q} {cy + q} {cx - r} {cy} Q{cx - q} {cy - q} {cx} {cy - r}Z"/>'
        )

    def image(self, name, x, y, size):
        uri = "data:image/svg+xml;base64," + base64.b64encode((ICONS / f"{name}.svg").read_bytes()).decode()
        self.body.append(
            f'<image x="{x}" y="{y}" width="{size}" height="{size}" href="{uri}" xlink:href="{uri}"/>'
        )

    def arrow(self, x, y, s, color, diagonal=False):
        if diagonal:  # up-right
            self.body.append(
                f'<path d="M{x} {y + s} L{x + s} {y} M{x + s * .25} {y} H{x + s} V{y + s * .75}" fill="none" '
                f'stroke="{color}" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>'
            )
        else:
            self.body.append(
                f'<path d="M{x} {y} H{x + s} M{x + s * .62} {y - s * .32} L{x + s} {y} L{x + s * .62} {y + s * .32}" '
                f'fill="none" stroke="{color}" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>'
            )

    def build(self):
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" role="img" '
            f'aria-label="{attr(self.label)}"><defs>{"".join(self.defs)}'
            f'<linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="{LINE}" stop-opacity="0"/>'
            f'<stop offset=".5" stop-color="{LINE}"/><stop offset="1" stop-color="{LINE}" stop-opacity="0"/></linearGradient>'
            f'</defs><rect width="{self.w}" height="{self.h}" fill="{BG}"/>{"".join(self.body)}</svg>\n'
        )


def write(name, doc):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(doc.build(), encoding="utf-8")


def parse_dt(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def fmt_date(d):
    return f"{d:%b} {d.day}, {d.year}"


# ---- GitHub data -----------------------------------------------------------
def request(url, payload=None):
    headers = {"User-Agent": "profile-readme-generator", "Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def request_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (profile-readme-generator)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def get_repos():
    repos, page = [], 1
    while True:
        batch = request(f"https://api.github.com/users/{USER}/repos?type=owner&sort=pushed&per_page=100&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    keep = []
    for r in repos:
        if r.get("private") or r.get("fork"):
            continue
        if r["name"].lower() in EXCLUDE or r["name"].lower() == USER.lower():
            continue
        stamp = r.get("pushed_at") or r.get("updated_at")
        if not stamp:
            continue
        r["_active"] = parse_dt(stamp)
        keep.append(r)
    keep.sort(key=lambda r: r["_active"], reverse=True)
    return keep[:MAX_REPOS] if MAX_REPOS > 0 else keep


def get_commits(repos):
    found = []
    for r in repos[:REPOS_SCANNED_FOR_COMMITS]:
        try:
            items = request(f"https://api.github.com/repos/{USER}/{r['name']}/commits?author={USER}&per_page=5")
        except urllib.error.HTTPError:
            continue  # empty repository or no access
        for c in items:
            commit = c["commit"]
            found.append(
                {
                    "repo": r["name"],
                    "message": commit["message"].split("\n")[0],
                    "date": parse_dt(commit["author"]["date"] or commit["committer"]["date"]),
                    "sha": c["sha"][:7],
                    "url": c["html_url"],
                }
            )
    found.sort(key=lambda c: c["date"], reverse=True)
    return found[:COMMITS_SHOWN]


def parse_calendar(html):
    """Parse GitHub's public contributions page. Raises if anything looks wrong."""
    dates = {}
    for tag in re.findall(r"<td\b[^>]*>", html):
        d, i = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', tag), re.search(r'\bid="([^"]+)"', tag)
        if d and i:
            dates[i.group(1)] = dt.date.fromisoformat(d.group(1))
    counts = {}
    for cid, text in re.findall(r'<tool-tip\b[^>]*\bfor="([^"]+)"[^>]*>\s*([^<]*?)\s*</tool-tip>', html):
        if cid not in dates:
            continue
        if text.startswith("No contributions"):
            counts[cid] = 0
        else:
            m = re.match(r"([\d,]+) contributions?\b", text)
            if not m:
                raise ValueError(f"unrecognised tooltip: {text!r}")
            counts[cid] = int(m.group(1).replace(",", ""))
    if len(dates) < 300 or set(dates) != set(counts):
        raise ValueError("contribution page layout not recognised")
    days = sorted(({"date": dates[k], "count": counts[k]} for k in dates), key=lambda d: d["date"])
    total = sum(d["count"] for d in days)
    m = re.search(r"([\d,]+)\s+contributions?\s+in the last year", html)
    if not m or int(m.group(1).replace(",", "")) != total:
        raise ValueError("daily counts do not add up to the page's own total")
    weeks = {}
    for d in days:
        d["weekday"] = d["date"].isoweekday() % 7  # Sunday = 0
        start = d["date"] - dt.timedelta(days=d["weekday"])
        weeks.setdefault(start, []).append(d)
    return {"total": total, "weeks": [weeks[k] for k in sorted(weeks)], "days": days}


def get_calendar():
    return parse_calendar(request_text(f"https://github.com/users/{USER}/contributions"))


# ---- shared page pieces ----------------------------------------------------
def divider(doc, y):
    doc.raw(f'<rect x="0" y="{y}" width="360" height="1" fill="url(#fade)"/>')
    doc.raw(f'<rect x="440" y="{y}" width="360" height="1" fill="url(#fade)"/>')
    doc.sparkle(400, y, 9, HEAD)


def header(label, heading, tagline, tagline_sparkle):
    doc = Doc(800, 240, f"{heading} {tagline}")
    if label:
        w = doc.text(4, 30, label, 13, BODY, LABEL, spacing=4)
        doc.raw(f'<rect x="{4 + w + 20}" y="25" width="{796 - (4 + w + 20)}" height="1" fill="{BORDER}"/>')
    size = fit(heading, 62, DISPLAY, 790)
    doc.text(2, 128, heading, size, HEAD, DISPLAY, stroke=DISPLAY_STROKE if size < 40 else 0)
    w = doc.text(4, 174, tagline, 19, BODY, BODYF, spacing=0.6)
    if tagline_sparkle:
        doc.sparkle(4 + w + 20, 167, 7, BLUSH)
    divider(doc, 216)
    return doc


def subhead(title, size=30, h=56):
    doc = Doc(800, h, title)
    w = doc.text(4, h - 18, title, size, HEAD, DISPLAY, stroke=DISPLAY_STROKE)
    x = 4 + w + 22
    doc.raw(f'<rect x="{x:.0f}" y="{h - 18 - size * 0.32:.0f}" width="{796 - x:.0f}" height="1" fill="{BORDER}"/>')
    return doc


def explore_button():
    doc = Doc(392, 56, "Explore all repositories")
    doc.raw(f'<rect x="1" y="1" width="390" height="54" rx="27" fill="none" stroke="{MUTED}"/>')
    label = "Explore all repositories"
    w = measure(label, 22, DISPLAY)
    x = (392 - (w + 34)) / 2
    doc.text(x, 36, label, 22, HEAD, DISPLAY, stroke=DISPLAY_STROKE)
    doc.arrow(x + w + 14, 29, 20, HEAD)
    return doc


# ---- section 03 cards ------------------------------------------------------
def project_card(i, r):
    doc = Doc(392, 144, f'{r["name"]}. {r.get("description") or ""} {r.get("language") or ""}'.strip())
    doc.raw(f'<rect x="1" y="1" width="390" height="142" rx="14" fill="{CARD}" stroke="{BORDER}"/>')
    doc.text(24, 33, f"{i:02d}", 12, MUTED, LABEL, spacing=2)
    doc.text(368, 33, f"updated {fmt_date(r['_active'])}", 12.5, MUTED, BODYF, anchor="end")
    size = fit(r["name"], 27, DISPLAY, 344)
    doc.text(24, 68, r["name"], size, HEAD, DISPLAY, stroke=DISPLAY_STROKE)
    if r.get("description"):
        for n, line in enumerate(wrap_px(r["description"], 13.5, BODYF, 344, 2)):
            doc.text(24, 93 + n * 17, line, 13.5, BODY, BODYF)
    if r.get("language"):
        doc.raw(f'<circle cx="28" cy="126" r="4" fill="{BODY}"/>')
        doc.text(40, 130, r["language"], 13, MUTED, BODYF)
    return doc


def commit_card(c):
    doc = Doc(392, 116, f'{c["repo"]}: {c["message"]}')
    doc.raw(f'<rect x="1" y="1" width="390" height="114" rx="14" fill="{CARD}" stroke="{BORDER}"/>')
    size = fit(c["repo"], 23, DISPLAY, 220)
    doc.text(24, 38, c["repo"], size, HEAD, DISPLAY, stroke=DISPLAY_STROKE)
    doc.text(368, 36, fmt_date(c["date"]), 12.5, MUTED, BODYF, anchor="end")
    for n, line in enumerate(wrap_px(c["message"], 13.5, BODYF, 344, 2)):
        doc.text(24, 64 + n * 17, line, 13.5, BODY, BODYF)
    doc.text(24, 102, f"commit {c['sha']}", 11.5, MUTED, LABEL, spacing=1.5)
    return doc


# ---- heatmap ---------------------------------------------------------------
def levels(days):
    nz = sorted(d["count"] for d in days if d["count"] > 0)
    if not nz:
        return lambda c: 0
    q = [nz[min(len(nz) - 1, math.ceil(len(nz) * p) - 1)] for p in (0.25, 0.5, 0.75)]
    return lambda c: 0 if c <= 0 else 1 if c <= q[0] else 2 if c <= q[1] else 3 if c <= q[2] else 4


def heat_panel(weeks, level, footer, period):
    doc = Doc(392, 162, "Contribution heatmap")
    left, top, pitch, size = 38, 40, 12.5, 10.5
    doc.raw(f'<rect x="1" y="1" width="390" height="160" rx="14" fill="{CARD}" stroke="{BORDER}"/>')
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        doc.text(left - 8, top + row * pitch + 9, name, 11, MUTED, LABEL, anchor="end")
    last, prev = -99, None
    for c, week in enumerate(weeks):
        month = week[-1]["date"].month if c == 0 else week[0]["date"].month
        if month != prev and c - last >= 3:
            doc.text(left + c * pitch, 28, f'{week[-1 if c == 0 else 0]["date"]:%b}', 12, BODY, LABEL)
            last = c
        prev = month
        for d in week:
            x, y = left + c * pitch, top + d["weekday"] * pitch
            doc.raw(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="2" fill="{HEAT[level(d["count"])]}"/>')
    if footer == "period":
        doc.text(20, 148, period, 12, MUTED, BODYF)
    else:
        doc.text(243, 148, "Less", 12, MUTED, BODYF)
        for n, col in enumerate(HEAT):
            doc.raw(f'<rect x="{275 + n * 13}" y="139" width="10" height="10" rx="2" fill="{col}"/>')
        doc.text(346, 148, "More", 12, MUTED, BODYF)
    return doc


def stat_card(number, label):
    doc = Doc(190, 88, f"{number} {label}")
    doc.raw(f'<rect x="1" y="1" width="188" height="86" rx="14" fill="{CARD}" stroke="{BORDER}"/>')
    doc.text(22, 50, number, 36, HEAD, DISPLAY, stroke=DISPLAY_STROKE)
    doc.text(22, 72, label, 14, BODY, BODYF)
    return doc


def streaks(days):
    longest = run = 0
    for d in days:
        run = run + 1 if d["count"] > 0 else 0
        longest = max(longest, run)
    i = len(days) - 1
    if i >= 0 and days[i]["count"] == 0:
        i -= 1  # today may simply not have happened yet
    current = 0
    while i >= 0 and days[i]["count"] > 0:
        current += 1
        i -= 1
    return current, longest


# ---- section 04 ------------------------------------------------------------
LANGUAGES = [("Java", "java"), ("Python", "python"), ("C", "c"), ("C++", "cplusplus"), ("JavaScript", "javascript")]
FRAMEWORKS = [("Spring Boot", "spring"), ("React", "react"), ("Vite", "vitejs"), ("HTML", "html5"), ("CSS", "css3")]
SOCIALS = [
    ("LeetCode", "MEHroof", "leetcode", LEETCODE_URL),
    ("LinkedIn", "Mehroof Saba", "linkedin", LINKEDIN_URL),
    ("Instagram", "@ms_37ann", "instagram", INSTAGRAM_URL),
]


def tile(name, icon):
    doc = Doc(100, 112, name)
    doc.image(icon, 28, 8, 44)
    doc.text(50, 90, name, 15, BODY, BODYF, anchor="middle")
    return doc


def pill(name, handle, icon):
    doc = Doc(256, 64, f"{name}: {handle}")
    doc.raw(f'<rect x="1" y="1" width="254" height="62" rx="31" fill="none" stroke="{BORDER}"/>')
    doc.image(icon, 22, 17, 30)
    doc.text(66, 30, name, 23, HEAD, DISPLAY, stroke=DISPLAY_STROKE)
    doc.text(66, 49, handle, 13, MUTED, BODYF)
    doc.arrow(222, 26, 11, MUTED, diagonal=True)
    return doc


def signoff():
    doc = Doc(800, 64, SIGNOFF)
    w = measure(SIGNOFF, 16, BODYF, 1.5)
    x0, x1 = 400 - w / 2 - 22, 400 + w / 2 + 22
    doc.raw(f'<rect x="40" y="31" width="{x0 - 40:.0f}" height="1" fill="{BORDER}"/>')
    doc.raw(f'<rect x="{x1:.0f}" y="31" width="{760 - x1:.0f}" height="1" fill="{BORDER}"/>')
    doc.text(400, 37, SIGNOFF, 16, BODY, BODYF, anchor="middle", spacing=1.5)
    return doc


# ---- build -----------------------------------------------------------------
def img(src, alt, width):
    return f'<img src="{src}" alt="{attr(alt)}" width="{width}">'


G = "assets/generated/"


def build_projects(written):
    repos = get_repos()
    commits = get_commits(repos)
    try:
        cal = get_calendar()
    except Exception as e:
        print(f"WARNING: contribution heatmap not updated ({e}).", file=sys.stderr)
        cal = None

    def emit(name, doc):
        write(name, doc)
        written.add(name)

emit("header-projects.svg", header("03 / PROJECTS & ACTIVITY", "Things I’ve been building.", "", False))
    emit("head-repositories.svg", subhead("Repositories"))
    emit("head-activity.svg", subhead("Recent Activity"))
    emit("head-contributions.svg", subhead("Contribution Activity"))
    emit("explore.svg", explore_button())

    parts = [img(G + "header-projects.svg", f"Things I’ve been building. {SUBTITLE_3}", "100%"), ""]
    parts += [img(G + "head-repositories.svg", "Repositories", "100%"), "", '<p align="center">']
    for i, r in enumerate(repos, 1):
        name = f"project-{i:02d}.svg"
        emit(name, project_card(i, r))
        alt = r["name"] + (f' — {r["description"]}' if r.get("description") else "")
        parts.append(f'<a href="{attr(r["html_url"])}">{img(G + name, alt, 392)}</a>')
    parts += ["</p>", ""]

    if commits:
        parts += [img(G + "head-activity.svg", "Recent Activity", "100%"), "", '<p align="center">']
        for i, c in enumerate(commits, 1):
            name = f"commit-{i:02d}.svg"
            emit(name, commit_card(c))
            parts.append(f'<a href="{attr(c["url"])}">{img(G + name, c["repo"] + ": " + c["message"], 392)}</a>')
        parts += ["</p>", ""]

    heat_files = ["heat-1.svg", "heat-2.svg", "stat-1.svg", "stat-2.svg", "stat-3.svg", "stat-4.svg"]
    if cal:
        days = cal["days"]
        period = f'{fmt_date(days[0]["date"])} – {fmt_date(days[-1]["date"])}'
        level = levels(days)
        half = math.ceil(len(cal["weeks"]) / 2)
        emit("heat-1.svg", heat_panel(cal["weeks"][:half], level, "period", period))
        emit("heat-2.svg", heat_panel(cal["weeks"][half:], level, "legend", period))
        current, longest = streaks(days)
        active = sum(1 for d in days if d["count"] > 0)
        stats = [
            (f'{cal["total"]:,}', "contributions"),
            (str(current), "day current streak"),
            (str(longest), "day longest streak"),
            (str(active), "active days"),
        ]
        for n, (num, lab) in enumerate(stats, 1):
            emit(f"stat-{n}.svg", stat_card(num, lab))
    if cal or all((OUT / f).exists() for f in heat_files):
        written.update(heat_files)  # on a failed fetch the last genuine heatmap is kept
        parts += [img(G + "head-contributions.svg", "Contribution Activity", "100%"), "", '<p align="center">']
        parts.append(img(G + "heat-1.svg", "Contribution heatmap, first half of the period", 392))
        parts.append(img(G + "heat-2.svg", "Contribution heatmap, second half of the period", 392))
        parts += ["</p>", '<p align="center">']
        for n, lab in enumerate(["contributions", "current streak", "longest streak", "active days"], 1):
            parts.append(img(f"{G}stat-{n}.svg", lab, 190))
        parts += ["</p>", ""]

    parts += [
        '<p align="center">',
        f'<a href="https://github.com/{USER}?tab=repositories">{img(G + "explore.svg", "Explore all repositories", 392)}</a>',
        "</p>",
    ]
    print(f"{len(repos)} repositories, {len(commits)} commits, heatmap: {'updated' if cal else 'kept or omitted'}")
    return "\n".join(parts)


def build_tech(written):
    def emit(name, doc):
        write(name, doc)
        written.add(name)

    emit("header-tech.svg", header(None, "04. Tech Stack & Connect", TAGLINE_4, True))
    emit("head-techstack.svg", subhead("Tech Stack"))
    emit("head-languages.svg", subhead("Languages", 23, 44))
    emit("head-frameworks.svg", subhead("Frameworks & Technologies", 23, 44))
    emit("head-connect.svg", subhead("Find me around the internet"))
    emit("signoff.svg", signoff())

    parts = [img(G + "header-tech.svg", f"04. Tech Stack & Connect. {TAGLINE_4}", "100%"), ""]
    parts += [img(G + "head-techstack.svg", "Tech Stack", "100%"), ""]
    for head, alt, items in (("head-languages.svg", "Languages", LANGUAGES), ("head-frameworks.svg", "Frameworks & Technologies", FRAMEWORKS)):
        parts += [img(G + head, alt, "100%"), "", '<p align="center">']
        for name, icon in items:
            fn = f"tile-{icon}.svg"
            emit(fn, tile(name, icon))
            parts.append(img(G + fn, name, 100))
        parts += ["</p>", ""]
    parts += [img(G + "head-connect.svg", "Find me around the internet", "100%"), "", '<p align="center">']
    for name, handle, icon, url in SOCIALS:
        fn = f"pill-{icon}.svg"
        emit(fn, pill(name, handle, icon))
        parts.append(f'<a href="{attr(url)}">{img(G + fn, f"{name}: {handle}", 256)}</a>')
    parts += ["</p>", "", img(G + "signoff.svg", SIGNOFF, "100%")]
    return "\n".join(parts)


def main():
    written = set()
    blocks = {"projects": build_projects(written), "tech": build_tech(written)}

    for f in OUT.glob("*.svg"):  # drop files left over from earlier runs
        if f.name not in written:
            f.unlink()

    text = README.read_text(encoding="utf-8")
    for key, (start, end) in MARKERS.items():
        pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
        if not pattern.search(text):
            sys.exit(f"README.md is missing the {start} / {end} markers.")
        text = pattern.sub(lambda _m, b=blocks[key], s=start, e=end: f"{s}\n{b}\n{e}", text)
    if text != README.read_text(encoding="utf-8"):
        README.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
