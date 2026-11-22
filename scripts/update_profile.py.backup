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
  Everything is drawn as vector outlines using the Jost Light and Regular fonts
  committed in the repository under fonts/.

Only the blocks between the marker comments in README.md are rewritten, so the Hero and
About sections are never touched. Output is deterministic (no timestamps), so the
workflow commits only when something really changed.
"""
import base64
import datetime as dt
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

MAX_REPOS = 6
COMMITS_SHOWN = 6
REPOS_SCANNED_FOR_COMMITS = 15
DISPLAY_STROKE = 0   # Set to 0 to disable outline strokes.
EXCLUDE = {
    x.strip().lower()
    for x in os.environ.get("EXCLUDE_REPOS", "").split(",")
    if x.strip()
}

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


JOST_L = Face(TTFont(str(FONTS / "Jost-Light.ttf")))
JOST_R = Face(TTFont(str(FONTS / "Jost-Regular.ttf")))

DISPLAY = [JOST_L]
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
    def __init__(self, w, h, label, transparent=False):
        self.w, self.h, self.label = w, h, label
        self.transparent = transparent
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
        background = "" if self.transparent else f'<rect width="{self.w}" height="{self.h}" fill="{BG}"/>'
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" role="img" '
            f'aria-label="{attr(self.label)}"><defs>{"".join(self.defs)}'
            f'<linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="{LINE}" stop-opacity="0"/>'
            f'<stop offset=".5" stop-color="{LINE}"/><stop offset="1" stop-color="{LINE}" stop-opacity="0"/></linearGradient>'
            f'</defs>{background}{"".join(self.body)}</svg>\n'
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
        url = (
            f"https://api.github.com/users/{USER}/repos"
            f"?type=owner&sort=pushed&per_page=100&page={page}"
        )
        batch = request(url)
        repos.extend(batch)

        if len(batch) < 100:
            break

        page += 1

    keep = []

    for r in repos:
        if r.get("private") or r.get("fork"):
            continue

        if r["name"].lower() in EXCLUDE:
            continue

        if r["name"].lower() == USER.lower():
            continue

        stamp = r.get("pushed_at") or r.get("updated_at")

        if not stamp:
            continue

        r["_active"] = parse_dt(stamp)
        keep.append(r)

    keep.sort(
        key=lambda r: r["_active"],
        reverse=True
    )

    return keep


def get_commits(repos):
    found = []

    for r in repos[:REPOS_SCANNED_FOR_COMMITS]:
        try:
            url = (
                f"https://api.github.com/repos/{USER}/{r['name']}"
                f"/commits?author={USER}&per_page=5"
            )
            items = request(url)

        except urllib.error.HTTPError:
            continue

        for c in items:
            commit = c["commit"]
            author = commit.get("author") or {}
            committer = commit.get("committer") or {}
            commit_date = author.get("date") or committer.get("date")

            if not commit_date:
                continue

            found.append({
                "repo": r["name"],
                "message": commit["message"].split("\n")[0],
                "date": parse_dt(commit_date),
                "sha": c["sha"][:7],
                "url": c["html_url"],
            })

    found.sort(
        key=lambda c: c["date"],
        reverse=True
    )

    # First pass: one recent commit per repository.
    selected = []
    seen = set()

    for commit in found:
        repo_name = commit["repo"].lower()

        if repo_name not in seen:
            selected.append(commit)
            seen.add(repo_name)

        if len(selected) >= COMMITS_SHOWN:
            break

    return selected


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


def divider(doc, y):
    doc.raw(
        f'<rect x="40" y="{y}" width="720" '
        f'height="1" fill="{BORDER}"/>'
    )


def header(
    label=None,
    heading="",
    tagline="",
    tagline_sparkle=False
):
    has_tagline = bool(tagline and tagline.strip())

    doc = Doc(
        800,
        220 if has_tagline else 190,
        f"{heading} {tagline}".strip()
    )

    size = fit(heading, 58, DISPLAY, 760)

    doc.text(
        400, 88, heading, size, HEAD, DISPLAY,
        anchor="middle"
    )

    if has_tagline:
        doc.text(
            400, 128, tagline, 18, BODY, BODYF,
            anchor="middle"
        )

    divider(doc, 165 if has_tagline else 145)

    return doc


def subhead(title, size=27, h=58):
    doc = Doc(800, h, title)

    doc.text(
        400, h - 18, title, size, HEAD, DISPLAY,
        anchor="middle"
    )

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
    doc = Doc(800, 174, "Contribution heatmap")

    left, top, pitch, size = 40, 43, 13.5, 10.5

    doc.raw(
        f'<rect x="1" y="1" width="798" height="172" '
        f'rx="14" fill="{CARD}" stroke="{BORDER}"/>'
    )

    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        doc.text(
            left - 9,
            top + row * pitch + 9,
            name, 11, MUTED, LABEL,
            anchor="end"
        )

   
    previous_month = None

    for col, week in enumerate(weeks):
        for day in week:
            date = day["date"]

            # Label each month only once, including the first partial month.
            month_key = (date.year, date.month)
            if month_key != previous_month:
                doc.text(
                    left + col * pitch,
                    28,
                    date.strftime("%b"),
                    11, BODY, LABEL
                )
                previous_month = month_key

            x = left + col * pitch
            y = top + day["weekday"] * pitch

            doc.raw(
                f'<rect x="{x:.1f}" y="{y:.1f}" '
                f'width="{size}" height="{size}" '
                f'rx="2" fill="{HEAT[level(day["count"])]}"/>'
            )

    doc.text(735, 155, "More", 12, MUTED, BODYF)

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

    # Skip today only if it has no contributions yet.
    if (
        i >= 0
       and days[i]["date"] == dt.date.today()
        and days[i]["count"] == 0
    ):
        i -= 1

    current = 0

    while i >= 0 and days[i]["count"] > 0:
        current += 1
        i -= 1

    return current, longest


# ---- section 04 ------------------------------------------------------------
LANGUAGES = [("Java", "java"), ("Python", "python"), ("C", "c"), ("C++", "cplusplus"), ("JavaScript", "javascript")]
FRAMEWORKS = [("Spring Boot", "spring"), ("React", "react"), ("Vite", "vitejs"), ("HTML", "html5"), ("CSS", "css3")]
DATABASES = [
    ("MySQL", "mysql"),
    ("Neon", "neon"),
    ("PostgreSQL", "postgresql"),
]
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
    doc = Doc(256, 64, f"{name}: {handle}", transparent=True)
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
    all_repos = get_repos()
    commits = get_commits(all_repos)
    repos = all_repos[:MAX_REPOS]

    try:
        cal = get_calendar()
    except Exception as e:
        print(
            f"WARNING: contribution heatmap not updated ({e}).",
            file=sys.stderr
        )
        cal = None

    def emit(name, doc):
        write(name, doc)
        written.add(name)

    # Page heading and section headings
    emit(
        "header-projects.svg",
        header(None, "Things I’ve been building.", "", False)
    )
    emit("head-repositories.svg", subhead("Repositories"))
    emit("head-activity.svg", subhead("Recent Activity"))
    emit("head-contributions.svg", subhead("Contribution Activity"))

    parts = [
        img(
            G + "header-projects.svg",
            "Things I’ve been building.",
            "100%"
        ),
        "",
        img(G + "head-repositories.svg", "Repositories", "100%"),
        "",
        '<p align="center">'
    ]

    # Six latest eligible public repositories
    for i, r in enumerate(repos, 1):
        name = f"project-{i:02d}.svg"
        emit(name, project_card(i, r))

        alt = r["name"] + (
            f' — {r["description"]}'
            if r.get("description") else ""
        )

        parts.append(
            f'<a href="{attr(r["html_url"])}">'
            f'{img(G + name, alt, 392)}</a>'
        )

    parts += ["</p>", ""]

    # Recent commits across different repositories
    if commits:
        parts += [
            img(G + "head-activity.svg", "Recent Activity", "100%"),
            "",
            '<p align="center">'
        ]

        for i, c in enumerate(commits, 1):
            name = f"commit-{i:02d}.svg"
            emit(name, commit_card(c))

            parts.append(
                f'<a href="{attr(c["url"])}">'
                f'{img(G + name, c["repo"] + ": " + c["message"], 392)}'
                f'</a>'
            )

        parts += ["</p>", ""]

    # One continuous contribution heatmap
    heat_files = [
        "heatmap.svg",
        "stat-1.svg",
        "stat-2.svg",
        "stat-3.svg",
        "stat-4.svg"
    ]

    if cal:
        days = cal["days"]

        period = (
            f'{fmt_date(days[0]["date"])} – '
            f'{fmt_date(days[-1]["date"])}'
        )

        level = levels(days)

        emit(
            "heatmap.svg",
            heat_panel(cal["weeks"], level, "legend", period)
        )

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

    # Keep previously generated genuine data if GitHub fetch fails
    if cal or all((OUT / f).exists() for f in heat_files):
        written.update(heat_files)

        parts += [
            img(
                G + "head-contributions.svg",
                "Contribution Activity",
                "100%"
            ),
            "",
            '<p align="center">',
            img(
                G + "heatmap.svg",
                "Continuous contribution heatmap",
                800
            ),
            "</p>",
            '<p align="center">'
        ]

        for n, lab in enumerate(
            [
                "contributions",
                "current streak",
                "longest streak",
                "active days"
            ],
            1
        ):
            parts.append(img(f"{G}stat-{n}.svg", lab, 190))

        parts += ["</p>", ""]

    print(
        f"{len(repos)} repositories, {len(commits)} commits, "
        f"heatmap: {'updated' if cal else 'kept or omitted'}"
    )

    return "\n".join(parts)

def build_tech(written):
    def emit(name, doc):
        write(name, doc)
        written.add(name)

    # Clean, centered page heading
    emit(
        "header-tech.svg",
        header(None, "Tech Stack & Connect", TAGLINE_4)
    )

    emit(
        "head-languages.svg",
        subhead("Languages", 25, 52)
    )

    emit(
        "head-frameworks.svg",
        subhead("Frameworks & Technologies", 25, 52)
    )

    emit(
    "head-databases.svg",
    subhead("Databases", 25, 52)
)

    emit(
        "head-connect.svg",
        subhead("Find me around the internet", 25, 58)
    )

    emit("signoff.svg", signoff())

    parts = [
        img(
            G + "header-tech.svg",
            "Tech Stack & Connect",
            "100%"
        ),
        "",
        img(G + "head-languages.svg", "Languages", "100%"),
        "",
        '<p align="center">'
    ]

    # Languages
    for name, icon in LANGUAGES:
        fn = f"tile-{icon}.svg"
        emit(fn, tile(name, icon))
        parts.append(img(G + fn, name, 100))

    parts += [
        "</p>",
        "",
        img(
            G + "head-frameworks.svg",
            "Frameworks & Technologies",
            "100%"
        ),
        "",
        '<p align="center">'
    ]

    # Frameworks and technologies
    for name, icon in FRAMEWORKS:
        fn = f"tile-{icon}.svg"
        emit(fn, tile(name, icon))
        parts.append(img(G + fn, name, 100))

    parts += [
        "</p>",
        "",
        img(
            G + "head-databases.svg",
            "Databases",
            "100%"
        ),
        "",
        '<p align="center">'
    ]

    # Databases
    for name, icon in DATABASES:
        fn = f"tile-{icon}.svg"
        emit(fn, tile(name, icon))
        parts.append(img(G + fn, name, 100))

    parts += [
        "</p>",
        "",
        img(
            G + "head-connect.svg",
            "Find me around the internet",
            "100%"
        ),
        "",
        '<p align="center">'
    ]

    # Social links
    for name, handle, icon, url in SOCIALS:
        fn = f"pill-{icon}.svg"
        emit(fn, pill(name, handle, icon))

        parts.append(
            f'<a href="{attr(url)}">'
            f'{img(G + fn, f"{name}: {handle}", 256)}'
            f'</a>'
        )

    parts += [
        "</p>",
        "",
        img(G + "signoff.svg", SIGNOFF, "100%")
    ]

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
