"""
SakuraHub asset generator.
Run:  python3 _source/build_assets.py          (offline: uses the small fallback data below)
      python3 _source/build_assets.py --live   (pulls EVERYTHING real from GitHub: repos, descriptions,
                                                commit counts, stats, contribution graph, latest commits)
The workflow in .github/ runs --live every few hours. It rewrites ./assets/*.svg AND ./README.md.
Nothing here is invented: if a number is not known, it is simply not shown.
"""
import random, math, os, sys, json, glob, html, datetime, urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
os.makedirs(OUT, exist_ok=True)

# ---------- palette ----------
BG0, BG1 = "#0c0f1d", "#171a31"      # night navy
CARD0, CARD1 = "#161a2e", "#1d2040"  # card gradient
LINE = "#3b3566"
CREAM, SILVER = "#f3e9dc", "#b9bccf"
SAKURA, BLUSH, DUSTY = "#e8a3c0", "#f6cfdc", "#c47a9b"
LAV, PURPLE, BLUE = "#b9a4e6", "#7d6bb3", "#a9c4ec"
BARK = "#4a3358"

HAND = "'Segoe Print','Bradley Hand','Chalkboard SE','Marker Felt','Comic Sans MS','Comic Neue',cursive"
SOFT = "'Segoe UI','Helvetica Neue',Helvetica,Arial,sans-serif"

# ---------- config ----------
PROFILE_LOGIN = os.environ.get("PROFILE_LOGIN", "mehroofsaba")
MAIN_PROJECT = "Oneiric"          # gets the big spotlight card

# Static personality (these are YOUR choices, so they are not pulled from GitHub)
TOOLS = ["Java", "Spring Boot", "JavaScript", "React", "HTML", "CSS", "C++", "Tauri", "Node.js"]
POKING = ["Linux", "Open Source", "Game Dev", "AI + ML", "Better UI/UX", "Rust"]

# Hand-written notes used ONLY when a repo has no description on GitHub yet.
# Once you fill in a repo's "About" description on GitHub, that live text wins automatically.
CURATED = {
  "Oneiric":       {"desc": "A dark, dreamy personal space for journaling, wrapped in cherry blossoms. Still being built.", "tech": ["Java", "Spring Boot", "HTML"], "fallback_badge": "main project"},
  "Wobble":        {"desc": "A little desktop companion with a tray menu. Drag it anywhere and it remembers where you left it.", "tech": "Tauri 2 · JavaScript", "art": "wobble", "fallback_badge": "in progress"},
  "CyberDefuse":   {"desc": "A 10×10 grid virus puzzle with a hacker-console look. One HTML file so far.", "tech": "HTML", "art": "cyberdefuse", "fallback_badge": "just started"},
  "Hacktoberfest": {"display": "BugBite", "link": "Hacktoberfest repo  →", "desc": "Paste code, pick a language, get a plain explanation of what's wrong and how to fix it.", "tech": "Node · Express · Gemma", "art": "bugbite", "fallback_badge": "open source"},
  "Portfolio":     {"desc": "My little corner of the web. The repo exists, the site isn't live yet. Still cooking.", "tech": "HTML · CSS", "art": "portfolio", "always_badge": "still cooking"},
  "Calculator":    {"desc": "A Hello Kitty themed calculator with scientific functions, tip calculation, unit conversion and the basics.", "tech": "Java", "art": "calculator"},
  "ChessMaster":   {"desc": "A Java chess game with move validation, check and checkmate detection, and a nice UI. AI and multiplayer are planned, not built yet.", "tech": "Java", "art": "chessmaster"},
}

# Used only before the first live sync (everything below was read from your real GitHub)
FALLBACK_REPOS = ["Oneiric", "Wobble", "CyberDefuse", "Hacktoberfest", "Portfolio", "Calculator", "ChessMaster"]
FALLBACK_STATS = [("public repositories", "12"), ("followers", "2"), ("following", "2")]
FALLBACK_DIARY = [("oneiric", "Still the main thing."),
                  ("wobble", "Lives in the tray with open, hide, mute, settings and quit."),
                  ("bugbite", "Paste code, pick a language, get a plain explanation."),
                  ("cyberdefuse", "Started as a single file, nodezero.html. Big idea, tiny start.")]

# ---------- little drawing helpers ----------
def svg(w, h, body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img">\n<defs>\n{GRADS}{defs}</defs>\n{body}\n</svg>\n')

GRADS = f'''<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>
<linearGradient id="card" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{CARD0}"/><stop offset="1" stop-color="{CARD1}"/></linearGradient>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1b1745"/><stop offset="0.6" stop-color="#4a2f6e"/><stop offset="1" stop-color="#8a4f85"/></linearGradient>
<radialGradient id="warm"><stop offset="0" stop-color="#ffd9a8" stop-opacity=".55"/><stop offset="1" stop-color="#ffd9a8" stop-opacity="0"/></radialGradient>
<radialGradient id="pinkglow"><stop offset="0" stop-color="{SAKURA}" stop-opacity=".35"/><stop offset="1" stop-color="{SAKURA}" stop-opacity="0"/></radialGradient>
<radialGradient id="lavglow"><stop offset="0" stop-color="{LAV}" stop-opacity=".35"/><stop offset="1" stop-color="{LAV}" stop-opacity="0"/></radialGradient>
<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="1.2"/></filter>
<filter id="shadow" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="6" stdDeviation="8" flood-color="#000" flood-opacity=".35"/></filter>
'''

def petal(x, y, s=8, rot=0, c=SAKURA, op=.9):
    return (f'<path transform="translate({x:.1f} {y:.1f}) rotate({rot:.0f}) scale({s/8:.2f})" '
            f'd="M0 -6 C5 -6 7 -1 0 7 C-7 -1 -5 -6 0 -6Z" fill="{c}" opacity="{op}"/>')

def flower(x, y, r=12, rot=0, c=SAKURA, op=.95):
    ps = ""
    for i in range(5):
        ps += (f'<path transform="rotate({i*72})" d="M0 0 C{-r*.62:.1f} {-r*.4:.1f} {-r*.55:.1f} {-r*1.05:.1f} 0 {-r:.1f} '
               f'C{r*.55:.1f} {-r*1.05:.1f} {r*.62:.1f} {-r*.4:.1f} 0 0Z" fill="{c}" opacity="{op}" stroke="{BLUSH}" stroke-opacity=".35" stroke-width=".6"/>')
    dots = "".join(f'<circle cx="{math.cos(a)*r*.28:.1f}" cy="{math.sin(a)*r*.28:.1f}" r="{r*.07:.1f}" fill="#fff1b8"/>' for a in [0, 1.3, 2.6, 3.9, 5.2])
    return f'<g transform="translate({x:.1f} {y:.1f}) rotate({rot:.0f})">{ps}<circle r="{r*.16:.1f}" fill="#d96a98"/>{dots}</g>'

def sparkle(x, y, s=6, c=CREAM, op=.9):
    return (f'<path transform="translate({x:.1f} {y:.1f}) scale({s/6:.2f})" d="M0 -6 Q0 0 6 0 Q0 0 0 6 Q0 0 -6 0 Q0 0 0 -6Z" fill="{c}" opacity="{op}"/>')

def star(x, y, r=1.4, c=CREAM, op=.8):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{c}" opacity="{op}"/>'

def heart(x, y, s=8, c=SAKURA):
    return (f'<path transform="translate({x} {y}) scale({s/10})" d="M0 8 C-12 -2 -6 -10 0 -4 C6 -10 12 -2 0 8Z" fill="none" stroke="{c}" stroke-width="1.6" stroke-linejoin="round"/>')

def text(x, y, s, size=16, fill=CREAM, font=HAND, anchor="start", extra=""):
    s = html.escape(s, quote=False)
    return f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" {extra}>{s}</text>'

def branch(pts, width=5, flowers=True, seed=1, density=.5, c=BARK, fr=11):
    """pts: list of (x,y). Smooth path + flowers/buds/petals sitting on it."""
    rnd = random.Random(seed)
    d = f"M{pts[0][0]} {pts[0][1]}"
    for i in range(1, len(pts) - 1):
        mx, my = (pts[i][0] + pts[i+1][0]) / 2, (pts[i][1] + pts[i+1][1]) / 2
        d += f" Q{pts[i][0]} {pts[i][1]} {mx:.1f} {my:.1f}"
    d += f" L{pts[-1][0]} {pts[-1][1]}"
    out = f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{width}" stroke-linecap="round"/>'
    out += f'<path d="{d}" fill="none" stroke="{DUSTY}" stroke-opacity=".25" stroke-width="{max(1,width-3)}" stroke-linecap="round" transform="translate(-.8 -.8)"/>'
    if flowers:
        for i in range(len(pts)):
            for k in range(2 if rnd.random() < density else 1):
                x = pts[i][0] + rnd.uniform(-22, 22); y = pts[i][1] + rnd.uniform(-22, 22)
                out += flower(x, y, rnd.uniform(fr*.7, fr*1.25), rnd.uniform(0, 72), rnd.choice([SAKURA, SAKURA, BLUSH, DUSTY]))
            if rnd.random() < .6:
                out += petal(pts[i][0] + rnd.uniform(-30, 30), pts[i][1] + rnd.uniform(-28, 28), rnd.uniform(3, 5), rnd.uniform(0, 360), DUSTY, .8)
    return out

def falling(w, h, n, seed, avoid=None, cols=(SAKURA, BLUSH, DUSTY, LAV)):
    rnd = random.Random(seed); out = ""; k = 0
    while k < n:
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        if avoid and avoid[0] < x < avoid[2] and avoid[1] < y < avoid[3]:
            continue
        out += petal(x, y, rnd.uniform(3, 7), rnd.uniform(0, 360), rnd.choice(cols), rnd.uniform(.35, .85)); k += 1
    return out

def stars(w, h, n, seed, avoid=None):
    rnd = random.Random(seed); out = ""; k = 0
    while k < n:
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        if avoid and avoid[0] < x < avoid[2] and avoid[1] < y < avoid[3]:
            continue
        out += star(x, y, rnd.choice([.8, 1, 1.4, 1.8]), CREAM, rnd.uniform(.25, .8))
        if rnd.random() < .12: out += sparkle(x, y, rnd.uniform(4, 7), CREAM, .8)
        k += 1
    return out

def squiggle(x, y, w, c=SAKURA, amp=3):
    d = f"M{x} {y}"
    n = int(w // 14)
    for i in range(n):
        d += f" q7 {-amp*2 if i%2==0 else amp*2} 14 0"
    return f'<path d="{d}" fill="none" stroke="{c}" stroke-width="1.6" stroke-linecap="round" opacity=".85"/>'

def cat_sleep(x, y, s=1.0, c="#cfc6e8", ear="#e8a3c0"):
    return (f'<g transform="translate({x} {y}) scale({s})">'
            f'<ellipse cx="0" cy="0" rx="46" ry="20" fill="{c}"/>'
            f'<circle cx="-34" cy="-6" r="17" fill="{c}"/>'
            f'<path d="M-48 -18 L-44 -34 L-33 -21Z M-30 -21 L-22 -34 L-18 -16Z" fill="{c}"/>'
            f'<path d="M-45 -20 L-43 -29 L-37 -22Z M-28 -22 L-23 -29 L-21 -18Z" fill="{ear}" opacity=".8"/>'
            f'<path d="M-42 -6 q3 3 6 0 M-30 -6 q3 3 6 0" stroke="#4a3358" stroke-width="1.5" fill="none" stroke-linecap="round"/>'
            f'<circle cx="-36" cy="1" r="1.3" fill="{ear}"/>'
            f'<path d="M40 8 q22 -2 24 -20 q0 -10 -8 -8" fill="none" stroke="{c}" stroke-width="8" stroke-linecap="round"/>'
            f'</g>')

def cat_face(x, y, s=1.0, c="#fbf3ea"):
    return (f'<g transform="translate({x} {y}) scale({s})">'
            f'<path d="M-30 -14 L-26 -38 L-8 -24Z M30 -14 L26 -38 L8 -24Z" fill="{c}"/>'
            f'<path d="M-26 -17 L-24 -31 L-14 -23Z M26 -17 L24 -31 L14 -23Z" fill="{BLUSH}"/>'
            f'<ellipse cx="0" cy="0" rx="34" ry="28" fill="{c}"/>'
            f'<ellipse cx="-14" cy="-2" rx="3" ry="4" fill="#3a2b4d"/><ellipse cx="14" cy="-2" rx="3" ry="4" fill="#3a2b4d"/>'
            f'<circle cx="-13" cy="-3.5" r="1.1" fill="#fff"/><circle cx="15" cy="-3.5" r="1.1" fill="#fff"/>'
            f'<ellipse cx="-22" cy="8" rx="6" ry="3.5" fill="{SAKURA}" opacity=".55"/><ellipse cx="22" cy="8" rx="6" ry="3.5" fill="{SAKURA}" opacity=".55"/>'
            f'<path d="M-3 6 Q0 9 3 6 M0 9 Q-4 14 -7 11 M0 9 Q4 14 7 11" stroke="#3a2b4d" stroke-width="1.5" fill="none" stroke-linecap="round"/>'
            f'</g>')

def card_frame(w, h, r=22, glow=None):
    g = ""
    if glow:
        g = (f'<clipPath id="cc"><rect x="1.5" y="1.5" width="{w-3}" height="{h-3}" rx="{r}"/></clipPath>'
             f'<circle clip-path="url(#cc)" cx="{glow[0]}" cy="{glow[1]}" r="{glow[2]}" fill="url(#{glow[3]})"/>')
    return (f'<rect x="1.5" y="1.5" width="{w-3}" height="{h-3}" rx="{r}" fill="url(#card)" stroke="{LINE}" stroke-width="1.4"/>'
            f'<rect x="3" y="3" width="{w-6}" height="{h-6}" rx="{r-2}" fill="none" stroke="{BLUSH}" stroke-opacity=".06"/>' + g)

def tl_attr(s, size):
    return f'textLength="{len(s)*size*0.5:.0f}" lengthAdjust="spacingAndGlyphs"'

def hand(x, y, s, size=16, fill=CREAM, anchor="start", extra=""):
    """handwriting text with a FIXED width, so it looks the same whatever font the viewer's device has."""
    return text(x, y, s, size, fill, HAND, anchor, tl_attr(s, size) + " " + extra), len(s) * size * 0.5

def title_end(t, size=24, x=26):
    return x + 32 + len(t) * size * 0.5

def card_title(t, x=26, y=44, size=24):
    return flower(x + 10, y - 8, 11, 10) + text(x + 32, y, t, size, CREAM, HAND, extra='font-weight="600" ' + tl_attr(t, size))

def pill(x, y, label, c=SAKURA, size=13, h=28):
    w = len(label) * (size * .6) + 26
    return (f'<rect x="{x}" y="{y}" width="{w:.0f}" height="{h}" rx="{h/2}" fill="{c}" fill-opacity=".14" stroke="{c}" stroke-opacity=".55"/>'
            + text(f"{x + w/2:.0f}", y + h/2 + size*.35, label, size, CREAM, SOFT, "middle")), w

def pill_flow(labels, x0, y0, maxw, gap=10, rowh=40, cols=(SAKURA, LAV, BLUSH, BLUE, DUSTY)):
    out = ""; x = x0; y = y0
    for i, l in enumerate(labels):
        w = len(l) * 7.8 + 26
        if x + w > x0 + maxw:
            x = x0; y += rowh
        p, w = pill(x, y, l, cols[i % len(cols)])
        out += p; x += w + gap
    return out, y + 28

def save(name, content):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(content)

# ======================================================================
# HERO  1000 x 380
# ======================================================================
def hero():
    W, H = 1000, 380
    b = f'<rect width="{W}" height="{H}" fill="url(#bg)"/>'
    b += f'<ellipse cx="270" cy="150" rx="260" ry="190" fill="url(#warm)"/>'
    b += f'<ellipse cx="860" cy="120" rx="220" ry="170" fill="url(#lavglow)"/>'
    b += f'<ellipse cx="520" cy="200" rx="260" ry="110" fill="url(#pinkglow)" opacity=".6"/>'
    b += stars(W, H, 70, 7, avoid=(300, 70, 740, 250))
    # back branches
    b += branch([(-10, 40), (60, 30), (140, 60), (230, 40), (300, 70)], 6, seed=3, density=.8, fr=13)
    b += branch([(1010, 20), (940, 40), (850, 20), (770, 45), (700, 30)], 6, seed=4, density=.8, fr=13)
    b += branch([(-10, 330), (70, 345), (150, 320), (230, 340)], 6, seed=5, density=.7)
    b += branch([(1010, 350), (930, 330), (850, 352), (770, 335)], 6, seed=6, density=.7)
    # corkboard note (left)
    b += (f'<g transform="rotate(-5 80 130)"><rect x="28" y="84" width="104" height="80" rx="6" fill="#3a2b4d" stroke="{LINE}"/>'
          f'<rect x="36" y="92" width="88" height="64" rx="3" fill="#f3e2d3" opacity=".92"/>'
          + text(80, 114, "small ideas.", 12, "#5b3d63", anchor="middle") + text(80, 130, "big chaos.", 12, "#5b3d63", anchor="middle")
          + heart(80, 144, 8, DUSTY) + '</g>')
    # lamp
    b += (f'<g><path d="M262 100 L292 62 L318 78 L290 112Z" fill="#f0d4b0"/><ellipse cx="280" cy="108" rx="24" ry="5" fill="#ffe9c4" opacity=".9"/>'
          f'<path d="M270 112 L252 170 L270 210" stroke="#cdbfd8" stroke-width="3" fill="none"/>'
          f'<ellipse cx="268" cy="214" rx="26" ry="5" fill="#cdbfd8"/>'
          f'<ellipse cx="282" cy="150" rx="70" ry="85" fill="url(#warm)" opacity=".5"/></g>')
    # laptop
    b += (f'<g filter="url(#shadow)"><path d="M48 238 L66 176 L212 176 L230 238Z" fill="#232749" stroke="{LAV}" stroke-opacity=".5"/>'
          f'<rect x="76" y="184" width="126" height="46" rx="3" fill="#161a33"/>'
          + "".join(f'<rect x="{84}" y="{192+i*9}" width="{[60,86,44,70][i]}" height="3" rx="1.5" fill="{[SAKURA,LAV,BLUE,BLUSH][i]}" opacity=".7"/>' for i in range(4))
          + f'<rect x="38" y="238" width="202" height="9" rx="4" fill="#2b2f58"/></g>')
    b += cat_face(168, 211, .26, "#cfc6e8")
    # books + mug (bottom left center)
    books = [("#7d6bb3", 90, 18), ("#c47a9b", 80, 16), ("#5d6aa0", 96, 17), ("#8f78c4", 72, 15)]
    yy = 296
    for i, (c, w, h) in enumerate(books):
        yy -= h
        b += f'<rect x="{262+(i%2)*6}" y="{yy+78}" width="{w}" height="{h}" rx="3" fill="{c}" stroke="{BG0}" stroke-opacity=".4"/><rect x="{270+(i%2)*6}" y="{yy+78+h/2-1}" width="{w-16}" height="2" fill="{CREAM}" opacity=".35"/>'
    b += (f'<g transform="translate(372 270)"><path d="M0 0 H34 V30 Q34 40 24 40 H10 Q0 40 0 30Z" fill="#e9ddef"/><path d="M34 8 q14 2 8 16 q-2 4 -8 4" fill="none" stroke="#e9ddef" stroke-width="4"/>'
          f'<ellipse cx="17" cy="2" rx="17" ry="3" fill="#8a5a6e"/>'
          f'<path d="M9 -8 q-4 -8 2 -14 M20 -8 q-4 -8 2 -14" stroke="{CREAM}" stroke-opacity=".4" fill="none" stroke-linecap="round"/></g>')
    # window with moon + skyline (right)
    b += (f'<g filter="url(#shadow)"><rect x="770" y="44" width="190" height="170" rx="10" fill="url(#sky)" stroke="{LAV}" stroke-opacity=".5" stroke-width="3"/>'
          f'<circle cx="905" cy="84" r="20" fill="#f3e9dc"/><circle cx="913" cy="78" r="18" fill="#2a2150"/>'
          + "".join(f'<rect x="{x}" y="{214-h}" width="{w}" height="{h}" fill="#1a1238"/>' for x, w, h in [(776,14,40),(792,10,66),(804,18,50),(824,12,78),(838,16,44),(856,10,58),(868,20,36),(890,12,72),(904,16,48),(922,12,60),(936,18,40)])
          + "".join(f'<rect x="{x}" y="{y}" width="2" height="2" fill="#ffe9a8"/>' for x, y in [(796,170),(828,150),(842,180),(893,160),(926,172),(860,188)])
          + stars(190, 120, 14, 11).replace('<circle', '<circle transform="translate(770 44)"') +
          f'<line x1="865" y1="44" x2="865" y2="214" stroke="{LAV}" stroke-opacity=".5" stroke-width="3"/><line x1="770" y1="130" x2="960" y2="130" stroke="{LAV}" stroke-opacity=".5" stroke-width="3"/></g>')
    # curtain
    b += f'<path d="M762 40 Q780 120 752 230 L792 230 Q800 120 790 40Z" fill="#6b4a8a" opacity=".8"/><path d="M968 40 Q950 120 978 230 L940 230 Q935 120 944 40Z" fill="#6b4a8a" opacity=".8"/>'
    # sill + sleeping cat
    b += f'<rect x="750" y="214" width="230" height="14" rx="5" fill="#2b2352" stroke="{LINE}"/>'
    b += cat_sleep(880, 204, .95)
    b += sparkle(842, 170, 5) + text(842, 160, "z", 11, LAV) + text(852, 148, "z", 9, LAV)
    # plant on right ledge
    b += (f'<g transform="translate(738 262)"><path d="M-14 0 H14 L10 28 H-10Z" fill="#8a5a8e"/><path d="M0 0 Q-20 -22 -18 -38 Q-4 -30 0 0 M0 0 Q22 -26 20 -42 Q4 -32 0 0 M0 0 Q0 -30 6 -48" fill="#6a8a8f" opacity=".85"/></g>')
    # centre text
    b += text(520, 150, "I should probably stop", 44, CREAM, HAND, "middle", f'textLength="420" lengthAdjust="spacingAndGlyphs" font-weight="700"')
    b += text(538, 204, "making things.", 44, SAKURA, HAND, "middle", f'textLength="330" lengthAdjust="spacingAndGlyphs" font-weight="700"')
    b += squiggle(420, 222, 210, DUSTY)
    b += text(520, 256, "Anyway, here's what I'm building.", 20, SILVER, SOFT, "middle", f'textLength="390" lengthAdjust="spacingAndGlyphs" font-style="italic" letter-spacing=".4"')
    b += heart(520, 276, 10, SAKURA)
    # crown doodle + sparkles
    b += '<path d="M498 86 l6 -14 l8 9 l8 -11 l8 11 l8 -9 l6 14Z" fill="none" stroke="%s" stroke-width="1.6" stroke-linejoin="round"/>' % CREAM
    b += sparkle(360, 100, 7) + sparkle(722, 170, 8, SAKURA) + sparkle(430, 66, 4, LAV)
    # annotation top-right with arrow
    b += text(640, 62, "do not ask how many", 13, CREAM, HAND, extra='transform="rotate(-6 640 62)"')
    b += text(645, 80, "tabs are open.", 13, CREAM, HAND, extra='transform="rotate(-6 645 80)"')
    b += f'<path d="M644 90 q-16 2 -20 14" stroke="{CREAM}" stroke-width="1.4" fill="none" stroke-linecap="round"/><path d="M620 98 l4 8 l8 -6" stroke="{CREAM}" stroke-width="1.4" fill="none" stroke-linecap="round"/>'
    # bottom-left annotation
    b += text(42, 290, "currently making", 12, BLUSH, HAND, extra='transform="rotate(-4 42 290)"')
    b += text(42, 306, "questionable decisions.", 12, BLUSH, HAND, extra='transform="rotate(-4 42 306)"')
    # foreground petals
    b += falling(W, H, 46, 21, avoid=(300, 110, 740, 290))
    # soft vignette
    b += f'<rect width="{W}" height="{H}" fill="none" stroke="{BG0}" stroke-width="0"/>'
    save("hero.svg", svg(W, H, b))

# ======================================================================
# DIVIDERS (each hides a tiny note)
# ======================================================================
def divider(name, note, seed):
    W, H = 1000, 56
    t, tl = hand(500, 33, note, 14, SILVER, "middle", 'font-style="italic" opacity=".9"')
    gl, gr = 500 - tl / 2 - 20, 500 + tl / 2 + 20
    b = f'<line x1="40" y1="28" x2="{gl:.0f}" y2="28" stroke="{LINE}" stroke-width="1.4" stroke-linecap="round"/>'
    b += f'<line x1="{gr:.0f}" y1="28" x2="960" y2="28" stroke="{LINE}" stroke-width="1.4" stroke-linecap="round"/>' + t
    b += flower(40, 28, 7, 10, SAKURA) + flower(960, 28, 7, 40, LAV)
    rnd = random.Random(seed)
    for _ in range(6):
        b += petal(rnd.choice([rnd.uniform(70, 280), rnd.uniform(720, 930)]), rnd.uniform(8, 48), rnd.uniform(3, 5), rnd.uniform(0, 360), rnd.choice([SAKURA, BLUSH, DUSTY]), .7)
    b += sparkle(rnd.uniform(110, 200), 14, 4) + sparkle(rnd.uniform(780, 900), 42, 4, SAKURA)
    save(name, svg(W, H, b))

# ======================================================================
# small utilities
# ======================================================================
def wrap(s, n):
    lines, cur = [], ""
    for wd in s.split():
        if len(cur) + len(wd) + 1 > n:
            lines.append(cur); cur = wd
        else:
            cur = (cur + " " + wd).strip()
    lines.append(cur)
    return lines

def clip(s, n):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n - 1].rsplit(" ", 1)[0] + "…"

def rel(iso):
    if not iso: return None
    try:
        t = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    d = (datetime.datetime.now(datetime.timezone.utc) - t).days
    if d < 1: return "today"
    if d < 14: return f"{d}d ago"
    if d < 60: return f"{d // 7}w ago"
    return f"{d // 30}mo ago"

def esc(s): return html.escape(s, quote=True)

# ======================================================================
# LIVE DATA  (GitHub GraphQL; every number on the page comes from here)
# ======================================================================
Q1 = """query($login:String!){user(login:$login){
 id name bio
 followers{totalCount} following{totalCount}
 allRepos: repositories(privacy:PUBLIC, ownerAffiliations:OWNER){totalCount}
 pinnedItems(first:6, types:REPOSITORY){nodes{... on Repository{name}}}
 repositories(first:100, privacy:PUBLIC, ownerAffiliations:OWNER, isFork:false, orderBy:{field:PUSHED_AT, direction:DESC}){
  nodes{name description url stargazerCount pushedAt isArchived primaryLanguage{name}
        defaultBranchRef{target{... on Commit{history{totalCount}}}}}}
 contributionsCollection{totalCommitContributions totalPullRequestContributions totalIssueContributions
  contributionCalendar{totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""

def gql(query, variables, tok):
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": "bearer " + tok, "Content-Type": "application/json", "User-Agent": "sakurahub"})
    with urllib.request.urlopen(req, timeout=40) as r:
        d = json.load(r)
    if d.get("errors"):
        raise RuntimeError(d["errors"][0].get("message", "graphql error"))
    return d["data"]

def norm_repo(n):
    h = (((n.get("defaultBranchRef") or {}).get("target")) or {}).get("history") or {}
    return dict(name=n["name"], url=n["url"], desc=(n.get("description") or "").strip() or None,
                lang=(n.get("primaryLanguage") or {}).get("name"), stars=n.get("stargazerCount"),
                commits=h.get("totalCount"), pushed=n.get("pushedAt"))

def fetch_live(tok=None):
    tok = tok or os.environ.get("GITHUB_TOKEN")
    if not tok:
        print("no GITHUB_TOKEN: using fallback data"); return None
    try:
        u = gql(Q1, {"login": PROFILE_LOGIN}, tok)["user"]
        repos = [norm_repo(n) for n in u["repositories"]["nodes"] if not n["isArchived"]]
        cc = u["contributionsCollection"]
        live = dict(
            repos=repos,
            pinned=[n["name"] for n in u["pinnedItems"]["nodes"] if n],
            stats=[("public repositories", str(u["allRepos"]["totalCount"])),
                   ("stars earned", str(sum(n["stargazerCount"] for n in u["repositories"]["nodes"]))),
                   ("commits this year", str(cc["totalCommitContributions"])),
                   ("pull requests this year", str(cc["totalPullRequestContributions"])),
                   ("followers", str(u["followers"]["totalCount"])),
                   ("following", str(u["following"]["totalCount"]))],
            calendar=cc["contributionCalendar"], commits=[])
        # latest real commits from the 5 most recently pushed repos
        recent = [r["name"] for r in repos if r["name"].lower() != PROFILE_LOGIN.lower()][:5]
        if recent:
            parts = "".join(f'r{i}: repository(owner:$login, name:"{n}"){{name defaultBranchRef{{target{{... on Commit{{'
                            f'history(first:4, author:{{id:$id}}){{nodes{{messageHeadline committedDate}}}}}}}}}}}}\n' for i, n in enumerate(recent))
            try:
                d2 = gql("query($login:String!,$id:ID!){" + parts + "}", {"login": PROFILE_LOGIN, "id": u["id"]}, tok)
                for v in d2.values():
                    if not v: continue
                    for c in (((v.get("defaultBranchRef") or {}).get("target")) or {}).get("history", {}).get("nodes", []):
                        live["commits"].append((v["name"], c["messageHeadline"], c["committedDate"]))
                live["commits"].sort(key=lambda x: x[2], reverse=True)
            except Exception as e:
                print("commit feed failed:", e)
        return live
    except Exception as e:
        print("live fetch failed, using fallback data:", e); return None

def fallback_repos():
    return [dict(name=n, url=f"https://github.com/{PROFILE_LOGIN}/{n}", desc=None, lang=None, stars=None, commits=None, pushed=None)
            for n in FALLBACK_REPOS]

def select(repos, pinned):
    pool = [r for r in repos if r["name"].lower() != PROFILE_LOGIN.lower()]
    main = next((r for r in pool if r["name"] == MAIN_PROJECT), None)
    rest = [r for r in pool if r is not main]
    order = {n: i for i, n in enumerate(pinned)}
    rest.sort(key=lambda r: (0, order[r["name"]]) if r["name"] in order else (1, 0))   # pinned first, then most recently pushed
    return main, rest[:4], rest[4:6], pool

def info(r):
    cur = CURATED.get(r["name"], {})
    updated = rel(r["pushed"])
    badge = cur.get("always_badge") or (f"updated {updated}" if updated else None) or cur.get("fallback_badge")
    parts = []
    if r["commits"]: parts.append(f'{r["commits"]} commits')
    if r["stars"]: parts.append(f'★ {r["stars"]}')
    return dict(name=cur.get("display", r["name"]), repo=r["name"], url=r["url"],
                desc=r["desc"] or cur.get("desc") or "No description on GitHub yet.",
                tech=cur.get("tech") or r["lang"] or "see repo", art=cur.get("art"),
                link=cur.get("link", "View repo  →"), badge=badge, meta=" · ".join(parts), updated=updated)

# ======================================================================
# ABOUT
# ======================================================================
def about():
    W, H = 1000, 340
    b = card_frame(W, H, glow=(900, 40, 220, "pinkglow"))
    t = "so... who am i?"
    b += card_title(t) + squiggle(title_end(t) + 14, 36, 70, SAKURA, 2.5)
    lines = ["Hey! I'm Mehroof. I like turning random ideas into things I can",
             "actually click, break, rebuild, and occasionally finish.",
             "",
             "Right now most of that energy goes into Oneiric, a dark, dreamy",
             "personal space I'm building with Spring Boot, plus a few smaller",
             "experiments: a desktop companion, a puzzle game, a debugging helper.",
             "",
             "My GitHub bio says \"The Bugs Fixes Me!!\" and honestly, fair."]
    y = 92
    for l in lines:
        if l == "":
            y += 14; continue
        b += text(40, y, l, 17, CREAM, SOFT, extra='letter-spacing=".15"'); y += 27
    sg, w = hand(40, y + 22, "same brain, different day.", 19, SAKURA, extra='font-style="italic"')
    b += sg + heart(40 + w + 22, y + 15, 10)
    b += cat_face(870, 235, 1.25)
    b += f'<path d="M830 292 q40 14 80 0" stroke="{LAV}" stroke-opacity=".5" stroke-width="2" fill="none" stroke-linecap="round"/>'
    b += branch([(760, 316), (820, 326), (900, 318), (990, 304)], 4, seed=8, density=.6, fr=9)
    n1, _ = hand(700, 70, "(yes, that's a cat.", 12, SILVER, extra='transform="rotate(-3 700 70)" opacity=".8"')
    n2, _ = hand(706, 87, "no, i won't explain.)", 12, SILVER, extra='transform="rotate(-3 706 87)" opacity=".8"')
    b += n1 + n2 + stars(W, H, 18, 31, avoid=(0, 60, 700, 340)) + sparkle(955, 40, 6, CREAM)
    save("about.svg", svg(W, H, b))

def tools():
    W, H = 490, 240
    b = card_frame(W, H, glow=(60, 30, 160, "pinkglow")) + card_title("things i keep reaching for", size=21)
    p, _ = pill_flow(TOOLS, 28, 76, W - 56); b += p
    sg, w = hand(28, H - 30, "and a little bit of chaos.", 16, SAKURA, extra='font-style="italic"')
    b += sg + heart(28 + w + 18, H - 35, 9) + text(W - 30, 38, "✦", 14, CREAM, SOFT, "end", 'opacity=".7"')
    b += branch([(330, 240), (400, 230), (470, 236)], 3, seed=12, density=.3, fr=7)
    save("tools.svg", svg(W, H, b))

def poking():
    W, H = 490, 240
    b = card_frame(W, H, glow=(430, 30, 160, "lavglow")) + card_title("currently poking at", size=21)
    p, _ = pill_flow(POKING, 28, 76, W - 56); b += p
    sg, w = hand(28, H - 30, "slowly... but surely.", 16, LAV, extra='font-style="italic"')
    n, _ = hand(W - 150, H - 18, "(ask me about tabs)", 11, SILVER, extra='opacity=".6"')
    b += sg + heart(28 + w + 18, H - 35, 9, LAV) + n + sparkle(W - 34, 36, 6) + sparkle(W - 70, 200, 4, SAKURA)
    save("poking.svg", svg(W, H, b))

def section_header(name, title, sub=None, seed=1):
    W, H = 1000, 84
    b = flower(36, 40, 15, 12) + text(66, 50, title, 30, CREAM, HAND, extra='font-weight="700" ' + tl_attr(title, 30))
    b += squiggle(66 + len(title) * 15 + 14, 44, 80, SAKURA, 3)
    if sub: b += text(66, 74, sub, 14, SILVER, SOFT, extra='font-style="italic"')
    b += falling(W, H, 8, seed) + sparkle(960, 30, 6) + sparkle(900, 60, 4, SAKURA)
    save(name, svg(W, H, b))

# ======================================================================
# PROJECT ART  (picked by repo, generic sakura scene for any new repo)
# ======================================================================
def project_art(key, w, h, seed=0):
    a = ""
    if key == "wobble":
        a += f'<rect width="{w}" height="{h}" fill="url(#sky)"/><circle cx="{w-40}" cy="28" r="14" fill="{CREAM}" opacity=".9"/><circle cx="{w-35}" cy="24" r="12" fill="#3a2a62"/>'
        a += stars(w, h, 14, 5) + cat_face(w/2, h/2 + 10, 1.35) + f'<ellipse cx="{w/2}" cy="{h-10}" rx="46" ry="6" fill="#000" opacity=".25"/>'
        a += petal(40, 40, 6, 20) + petal(30, 90, 5, 70, BLUSH) + petal(w-30, 100, 6, 130, LAV)
    elif key == "cyberdefuse":
        a += f'<rect width="{w}" height="{h}" fill="#0f1a2c"/><circle cx="{w/2}" cy="{h/2}" r="80" fill="#7fd6c8" opacity=".08"/>'
        gx, gy, cs = w/2 - 60, h/2 - 60, 12
        for i in range(11):
            a += f'<line x1="{gx}" y1="{gy+i*cs}" x2="{gx+10*cs}" y2="{gy+i*cs}" stroke="#7fd6c8" stroke-opacity=".28"/><line x1="{gx+i*cs}" y1="{gy}" x2="{gx+i*cs}" y2="{gy+10*cs}" stroke="#7fd6c8" stroke-opacity=".28"/>'
        for (i, j) in [(2, 3), (6, 2), (4, 6), (7, 7), (1, 8)]:
            cx, cy = gx + i*cs + cs/2, gy + j*cs + cs/2
            a += f'<circle cx="{cx}" cy="{cy}" r="4.2" fill="{SAKURA}" opacity=".85"/>' + "".join(f'<line x1="{cx+math.cos(t)*4.5:.1f}" y1="{cy+math.sin(t)*4.5:.1f}" x2="{cx+math.cos(t)*7:.1f}" y2="{cy+math.sin(t)*7:.1f}" stroke="{SAKURA}" stroke-width="1.2" opacity=".85"/>' for t in [0, 1.05, 2.1, 3.14, 4.2, 5.25])
        a += f'<rect x="{gx+4*cs}" y="{gy+4*cs}" width="{cs}" height="{cs}" fill="#7fd6c8" opacity=".6"/>' + sparkle(34, 34, 5, "#7fd6c8") + sparkle(w-30, h-30, 4, CREAM)
    elif key == "bugbite":
        a += f'<rect width="{w}" height="{h}" fill="#141836"/><circle cx="{w/2}" cy="{h/2}" r="90" fill="url(#lavglow)"/>' + stars(w, h, 14, 8)
        a += f'<rect x="16" y="20" width="{w-32}" height="96" rx="10" fill="#0e1128" stroke="{LAV}" stroke-opacity=".6"/>'
        a += "".join(f'<circle cx="{30+i*12}" cy="32" r="3" fill="{c}"/>' for i, c in enumerate([SAKURA, LAV, BLUE]))
        for k, (x, ww, c) in enumerate([(30, 70, SAKURA), (44, 90, LAV), (44, 54, BLUE), (30, 40, BLUSH), (44, 76, LAV)]):
            a += f'<rect x="{x}" y="{46+k*13}" width="{ww}" height="4" rx="2" fill="{c}" opacity=".75"/>'
        bx, by = w - 52, h - 36
        a += f'<g transform="translate({bx} {by})">' + "".join(f'<line x1="0" y1="{y}" x2="{s*16}" y2="{y+dy}" stroke="{DUSTY}" stroke-width="2" stroke-linecap="round"/>' for s in (-1, 1) for y, dy in ((-4, -6), (2, 0), (8, 6)))
        a += (f'<ellipse cx="0" cy="3" rx="12" ry="14" fill="{SAKURA}"/><circle cx="0" cy="-13" r="8" fill="{BLUSH}"/>'
              f'<circle cx="-3" cy="-14" r="1.6" fill="#3a2b4d"/><circle cx="3" cy="-14" r="1.6" fill="#3a2b4d"/>'
              f'<path d="M-6 -20 q-4 -8 -8 -8 M6 -20 q4 -8 8 -8" stroke="{DUSTY}" stroke-width="1.5" fill="none" stroke-linecap="round"/>'
              f'<circle cx="-4" cy="0" r="2" fill="{DUSTY}"/><circle cx="4" cy="6" r="2" fill="{DUSTY}"/></g>')
        a += sparkle(36, h - 22, 6) + sparkle(w - 22, 20, 4, SAKURA)
    else:  # portfolio + generic sakura scene (seed varies it per repo)
        a += f'<rect width="{w}" height="{h}" fill="url(#sky)"/><ellipse cx="{w/2}" cy="{h/2}" rx="90" ry="60" fill="url(#pinkglow)"/>' + stars(w, h, 14, 9 + seed)
        if seed % 2: a += f'<circle cx="{w-44}" cy="34" r="14" fill="{CREAM}" opacity=".9"/>'
        a += f'<path d="M{w/2-6} {h} Q{w/2-10} {h/2+30} {w/2+20} {h/2-10} M{w/2+20} {h/2-10} Q{w/2+50} {h/2-30} {w/2+80} {h/2-24} M{w/2+8} {h/2+14} Q{w/2-30} {h/2} {w/2-70} {h/2-14}" stroke="{BARK}" stroke-width="6" fill="none" stroke-linecap="round"/>'
        rnd = random.Random(14 + seed)
        for _ in range(16):
            a += flower(w/2 + rnd.uniform(-80, 90), h/2 + rnd.uniform(-48, 36), rnd.uniform(7, 12), rnd.uniform(0, 72), rnd.choice([SAKURA, BLUSH, DUSTY]))
        a += falling(w, h, 10, 17 + seed)
    return a

ACCENTS = [SAKURA, LAV, BLUE, "#7fd6c8", BLUSH]

def project_card(i, d, accent):
    W, H = 235, 350
    art_h = 140
    cp = f'<clipPath id="art{i}"><rect x="12" y="12" width="{W-24}" height="{art_h}" rx="14"/></clipPath>'
    b = card_frame(W, H, 20)
    b += f'<g clip-path="url(#art{i})"><g transform="translate(12 12)">{project_art(d["art"] or "generic", W-24, art_h, i)}</g></g>'
    b += f'<rect x="12" y="12" width="{W-24}" height="{art_h}" rx="14" fill="none" stroke="{accent}" stroke-opacity=".35"/>'
    if d["badge"]:
        sp, sw = pill(20, 20, d["badge"], accent, 10, 22)
        b += f'<rect x="20" y="20" width="{sw:.0f}" height="22" rx="11" fill="#0c0f1d" fill-opacity=".72"/>' + sp
    b += text(20, 186, clip(d["name"], 16), 20, CREAM, HAND, extra='font-weight="700"')
    for k, l in enumerate(wrap(d["desc"], 30)[:4]):
        b += text(20, 210 + k * 18, l, 12.5, SILVER, SOFT)
    if d["meta"]: b += text(20, 284, d["meta"], 11.5, SILVER, SOFT, extra='font-style="italic" opacity=".85"')
    p, _ = pill(20, 292, clip(d["tech"], 24), accent, 11, 26); b += p
    b += text(20, 338, d["link"], 13, accent, HAND, extra='font-weight="600"')
    save(f"project-{i+1}.svg", svg(W, H, b, cp))

def mini_card(i, d, accent):
    W, H = 490, 166
    b = card_frame(W, H, 20)
    b += f'<rect x="16" y="16" width="86" height="134" rx="14" fill="#10132a" stroke="{accent}" stroke-opacity=".45"/>'
    art = d["art"]
    if art == "calculator":
        b += f'<rect x="28" y="28" width="62" height="24" rx="6" fill="#0e1128" stroke="{accent}" stroke-opacity=".5"/>' + text(84, 46, "0.", 14, CREAM, SOFT, "end")
        for r in range(4):
            for c in range(3):
                col = [SAKURA, LAV, BLUSH][(r + c) % 3]
                b += f'<rect x="{28+c*21}" y="{60+r*20}" width="18" height="16" rx="5" fill="{col}" fill-opacity=".35" stroke="{col}" stroke-opacity=".6"/>'
    elif art == "chessmaster":
        for r in range(6):
            for c in range(4):
                if (r + c) % 2 == 0: b += f'<rect x="{28+c*15}" y="{34+r*15}" width="15" height="15" fill="{accent}" fill-opacity=".38"/>'
        b += f'<rect x="28" y="34" width="60" height="90" fill="none" stroke="{accent}" stroke-opacity=".6"/>' + flower(58, 79, 9, 0, SAKURA, .95)
    else:
        b += flower(59, 60, 14, 0, SAKURA) + flower(40, 98, 10, 20, BLUSH) + flower(78, 104, 11, 50, LAV) + petal(36, 40, 5, 30) + petal(84, 36, 5, 90, BLUSH)
    b += text(122, 46, clip(d["name"], 22), 20, CREAM, HAND, extra='font-weight="700"')
    for k, l in enumerate(wrap(d["desc"], 50)[:3]):
        b += text(122, 70 + k * 18, l, 12.5, SILVER, SOFT)
    p, w = pill(122, 126, clip(d["tech"], 20), accent, 11, 24); b += p
    if d["meta"]: b += text(122 + w + 12, 142, d["meta"], 11, SILVER, SOFT, extra='font-style="italic" opacity=".85"')
    b += text(W - 20, 143, d["link"], 13, accent, HAND, "end", 'font-weight="600"')
    save(f"mini-{i+1}.svg", svg(W, H, b))

def oneiric_spotlight(d):
    W, H = 1000, 340
    aw, ah = 380, 304
    cp = f'<clipPath id="oa"><rect x="18" y="18" width="{aw}" height="{ah}" rx="18"/></clipPath>'
    art = f'<rect width="{aw}" height="{ah}" fill="url(#sky)"/>'
    art += f'<circle cx="290" cy="76" r="86" fill="url(#lavglow)"/><circle cx="290" cy="76" r="28" fill="{CREAM}"/>'
    art += f'<circle cx="281" cy="70" r="5" fill="#e3d6c8" opacity=".7"/><circle cx="298" cy="84" r="3.5" fill="#e3d6c8" opacity=".7"/>'
    art += stars(aw, ah, 46, 3, avoid=(250, 30, 335, 125))
    art += branch([(20, 310), (60, 258), (120, 200), (200, 164), (290, 144), (372, 162)], 10, seed=31, density=1.0, fr=15)
    art += branch([(120, 200), (110, 144), (150, 98), (200, 76)], 6, seed=32, density=.9, fr=13)
    art += branch([(200, 164), (236, 118), (264, 100)], 5, seed=33, density=.9, fr=12)
    art += f'<ellipse cx="205" cy="270" rx="110" ry="40" fill="url(#warm)"/>'
    art += (f'<g transform="translate(205 266)"><path d="M-70 -18 L0 -28 L70 -18 L70 24 L0 34 L-70 24Z" fill="#2a2a5a" stroke="{LAV}" stroke-opacity=".7"/>'
            f'<path d="M0 -28 V34" stroke="{LAV}" stroke-opacity=".7"/>'
            + "".join(f'<rect x="{x}" y="{y}" width="{w}" height="3" rx="1.5" fill="{c}" opacity=".75"/>' for x, y, w, c in
                      [(-60,-8,44,SAKURA),(-60,2,36,LAV),(-60,12,42,BLUE),(10,-8,42,BLUSH),(10,2,34,LAV),(10,12,44,SAKURA)]) + '</g>')
    art += cat_sleep(76, 288, .55) + falling(aw, ah, 20, 5, cols=(SAKURA, BLUSH, DUSTY))
    b = card_frame(W, H, 24, glow=(800, 60, 280, "pinkglow"))
    b += f'<g clip-path="url(#oa)"><g transform="translate(18 18)">{art}</g></g>'
    b += f'<rect x="18" y="18" width="{aw}" height="{ah}" rx="18" fill="none" stroke="{SAKURA}" stroke-opacity=".4"/>'
    nm = clip(d["name"], 14)
    b += text(430, 82, nm, 48, CREAM, HAND, extra='font-weight="700" ' + tl_attr(nm, 48))
    px = 430 + len(nm) * 24 + 26
    p, w = pill(px, 52, "main project", SAKURA, 13, 28); b += p
    if d["updated"]:
        p, w2 = pill(px + w + 10, 52, f'updated {d["updated"]}', LAV, 13, 28); b += p
    for i, l in enumerate(wrap(d["desc"], 56)[:3]):
        b += text(430, 124 + i * 26, l, 17, CREAM, SOFT)
    n, _ = hand(430, 216, "features land as i build them, not before.", 17, SAKURA, extra='font-style="italic"'); b += n
    tech = d["tech"] if isinstance(d["tech"], list) else [d["tech"]]
    p, _ = pill_flow(tech, 430, 238, 520); b += p
    if d["meta"]: b += text(430, 292, d["meta"], 13, SILVER, SOFT, extra='font-style="italic"')
    lk, lw = hand(430, 322, "View Oneiric on GitHub  →".replace("Oneiric", d["name"]), 19, SAKURA, extra='font-weight="700"')
    b += lk + squiggle(430, 330, min(lw, 330), DUSTY, 2)
    b += sparkle(960, 40, 7) + sparkle(930, 300, 5, LAV) + heart(940, 70, 10)
    save("project-main.svg", svg(W, H, b, cp))

def building(rows):
    W = 1000
    H = 82 + len(rows) * 56 + 12
    b = card_frame(W, H, glow=(900, 30, 200, "pinkglow"))
    t = "anyway, here's what i'm building."
    b += flower(38, 42, 12, 0) + text(62, 52, t, 24, CREAM, HAND, extra='font-weight="600" ' + tl_attr(t, 24))
    for i, (n, dsc, s) in enumerate(rows):
        c = ACCENTS[i % 5]
        y = 74 + i * 56
        b += f'<rect x="24" y="{y}" width="952" height="46" rx="14" fill="#10132a" stroke="{LINE}"/>'
        b += f'<circle cx="52" cy="{y+23}" r="14" fill="{c}" fill-opacity=".18" stroke="{c}" stroke-opacity=".6"/>' + sparkle(52, y+23, 6, c)
        b += text(78, y + 21, clip(n, 22), 16, CREAM, HAND, extra='font-weight="700"') + text(78, y + 38, clip(dsc, 96), 12, SILVER, SOFT)
        if s:
            p, _ = pill(940 - (len(s)*6.8+22) + 10, y + 11, s, c, 11, 24); b += p
    b += stars(W, H, 10, 44, avoid=(0, 60, 1000, H))
    save("building.svg", svg(W, H, b))

# ======================================================================
# STATS
# ======================================================================
def stats(items, live):
    n = len(items)
    cols_n = 3
    rows_n = (n + cols_n - 1) // cols_n
    W, H = 1000, 110 + rows_n * 90 + 40
    b = card_frame(W, H, glow=(100, 20, 220, "lavglow"))
    t = "tiny numbers from the chaos."
    b += card_title(t, y=46, size=26) + squiggle(title_end(t, 26) + 14, 38, 60, LAV, 2.5)
    cols = [SAKURA, LAV, BLUSH, BLUE, DUSTY, LAV]
    gap = 16; cw = (W - 56 - (cols_n - 1) * gap) / cols_n
    for i, (lab, val) in enumerate(items):
        cx, cy, c = 28 + (i % cols_n) * (cw + gap), 80 + (i // cols_n) * 90, cols[i % 6]
        b += f'<rect x="{cx:.0f}" y="{cy}" width="{cw:.0f}" height="78" rx="18" fill="#10132a" stroke="{c}" stroke-opacity=".4"/>'
        b += f'<rect x="{cx:.0f}" y="{cy+16}" width="4" height="46" rx="2" fill="{c}" opacity=".8"/>'
        b += text(f"{cx+24:.0f}", cy + 33, lab, 14, SILVER, SOFT) + text(f"{cx+24:.0f}", cy + 64, val, 30, CREAM, HAND, extra='font-weight="700"')
        b += flower(cx + cw - 38, cy + 39, 11, i * 20, c, .8)
    sg, _ = hand(30, H - 18, "the numbers are real. the chaos is worse.", 17, SAKURA, extra='font-style="italic"')
    nt, _ = hand(W - 30, H - 16, "refreshed automatically from github" if live else "fallback numbers until the first sync", 11, SILVER, "end", 'opacity=".55"')
    b += sg + nt + cat_sleep(880, 50, .55)
    save("stats.svg", svg(W, H, b))

# ======================================================================
# CONTRIBUTION GARDEN (your real calendar, pink paint)
# ======================================================================
LEVELS = {"NONE": "#1f2342", "FIRST_QUARTILE": "#5b3f86", "SECOND_QUARTILE": "#9a6bb5",
          "THIRD_QUARTILE": "#d27ba3", "FOURTH_QUARTILE": "#ffa8cf"}

def contributions(cal):
    W, H = 1000, 270
    b = card_frame(W, H, glow=(880, 40, 240, "pinkglow"))
    b += card_title("planting little bits of me here...", y=46, size=24)
    cs, step, x0, y0 = 14, 17, 58, 100
    if cal:
        weeks = cal["weeks"]
        h1, _ = hand(W - 30, 46, f'{cal["totalContributions"]} contributions in the last year', 18, CREAM, "end", 'font-weight="600"')
        b += h1
        last_m = None
        for wi, wk in enumerate(weeks):
            days = wk["contributionDays"]
            if not days: continue
            m = days[0]["date"][5:7]
            if m != last_m and wi < len(weeks) - 2:
                b += text(x0 + wi * step, 90, ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"][int(m) - 1], 11, SILVER, SOFT)
            last_m = m
            for d in days:
                dow = datetime.date.fromisoformat(d["date"]).isoweekday() % 7   # sunday = 0
                b += (f'<rect x="{x0+wi*step}" y="{y0+dow*step}" width="{cs}" height="{cs}" rx="4" '
                      f'fill="{LEVELS.get(d["contributionLevel"], LEVELS["NONE"])}"><title>{d["contributionCount"]} on {d["date"]}</title></rect>')
        for lab, r in (("mon", 1), ("wed", 3), ("fri", 5)):
            b += text(28, y0 + r * step + 11, lab, 10, SILVER, SOFT, "middle")
    else:
        for wi in range(53):
            for r in range(7):
                b += f'<rect x="{x0+wi*step}" y="{y0+r*step}" width="{cs}" height="{cs}" rx="4" fill="{LEVELS["NONE"]}" opacity=".55"/>'
        b += f'<rect x="250" y="130" width="500" height="56" rx="18" fill="#0c0f1d" fill-opacity=".9" stroke="{LINE}"/>'
        b += text(500, 154, "the garden is waiting for its first sync.", 17, CREAM, HAND, "middle", tl_attr("the garden is waiting for its first sync.", 17))
        b += text(500, 174, "your real activity appears after the workflow runs once. nothing here is made up.", 12, SILVER, SOFT, "middle")
    lx = W - 30 - (5 * step + 90)
    b += text(lx, 244, "less", 11, SILVER, SOFT)
    for i, k in enumerate(["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]):
        b += f'<rect x="{lx+32+i*step}" y="233" width="{cs}" height="{cs}" rx="4" fill="{LEVELS[k]}"/>'
    b += text(lx + 32 + 5 * step + 6, 244, "more", 11, SILVER, SOFT)
    nt, _ = hand(190, 246, "the data is real. only the paint is mine.", 12, SILVER, extra='opacity=".7"')
    b += nt + branch([(-10, 268), (70, 258), (150, 270)], 3, seed=41, density=.4, fr=7) + sparkle(960, 78, 5) + sparkle(30, 70, 4, SAKURA)
    save("contributions.svg", svg(W, H, b))

# ======================================================================
# DIARY  (live: your latest real commits)
# ======================================================================
def diary(commits):
    items = [(r, m, rel(d)) for r, m, d in commits[:6]] if commits else [(t, x, None) for t, x in FALLBACK_DIARY]
    n = len(items)
    W, H = 1000, 84 + n * 52 + 40
    b = card_frame(W, H, glow=(900, H - 30, 220, "pinkglow"))
    t = "developer diary"
    b += card_title(t, y=46, size=26)
    sub = "straight from my latest commits. nothing staged." if commits else "notes until the first live sync."
    st, _ = hand(title_end(t, 26) + 22, 46, sub, 13, SILVER, extra='font-style="italic"')
    b += st
    for i, (tag, msg, when) in enumerate(items):
        y = 84 + i * 52
        b += f'<rect x="26" y="{y}" width="948" height="42" rx="14" fill="#10132a" stroke="{LINE}"/>'
        p, w = pill(40, y + 8, clip(tag, 16), ACCENTS[i % 5], 12, 26); b += p
        ax = 40 + w + 14
        b += f'<path d="M{ax:.0f} {y+21} h22 m-6 -5 l6 5 l-6 5" stroke="{LAV}" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        b += text(f"{ax+36:.0f}", y + 27, clip(msg, 78), 15, CREAM, SOFT)
        if when: b += text(952, y + 26, when, 12, SILVER, SOFT, "end")
    ft, _ = hand(30, H - 16, "pulled from my real commit history. i just write the commits." if commits else "this fills itself from real commits once the workflow runs.", 12, SILVER, extra='opacity=".7"')
    b += ft + branch([(800, H), (880, H - 14), (960, H - 8), (1010, H - 24)], 4, seed=15, density=.5, fr=8) + sparkle(950, 40, 6)
    save("diary.svg", svg(W, H, b))

# ======================================================================
# CONTACT, BUTTONS, FOOTER
# ======================================================================
def contact():
    W, H = 1000, 200
    b = card_frame(W, H, glow=(100, 170, 220, "pinkglow"))
    b += card_title("wanna cook something weird?", y=48, size=26)
    b += text(40, 94, "Let's talk about projects, ideas, collaborations, open source,", 17, CREAM, SOFT)
    b += text(40, 120, "or just interesting things to build.", 17, CREAM, SOFT)
    b += text(40, 154, "Easiest way to reach me for now: say hi on GitHub, or open an issue on any repo.", 15, SILVER, SOFT)
    nt, _ = hand(40, 183, "buttons are right below, they don't bite.", 13, SILVER, extra='opacity=".7"')
    b += nt + cat_face(900, 124, 1.0) + heart(840, 68, 10) + sparkle(960, 40, 6)
    save("contact.svg", svg(W, H, b))

def button(name, label, c, glyph, W=138):
    H = 40
    b = f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="20" fill="#141730" stroke="{c}" stroke-opacity=".6"/>'
    b += glyph(c) + text(60, 25, label, 14, CREAM, SOFT)
    save(name, svg(W, H, b))

def g_gh(c): return f'<circle cx="32" cy="20" r="10" fill="none" stroke="{c}" stroke-width="1.6"/>' + flower(32, 20, 5, 0, c, .9)
def g_repo(c): return (f'<rect x="24" y="11" width="16" height="19" rx="3" fill="none" stroke="{c}" stroke-width="1.6"/>'
                       f'<path d="M28 16 h8 M28 21 h8" stroke="{c}" stroke-width="1.4" stroke-linecap="round"/>')

def footer():
    W, H = 1000, 150
    msg = "okay bye, go look at my stuffs."
    t, tl = hand(500, 66, msg, 22, CREAM, "middle", 'font-weight="600"')
    b = f'<line x1="60" y1="60" x2="{500-tl/2-24:.0f}" y2="60" stroke="{LINE}" stroke-width="1.4" stroke-linecap="round"/><line x1="{500+tl/2+24:.0f}" y1="60" x2="940" y2="60" stroke="{LINE}" stroke-width="1.4" stroke-linecap="round"/>'
    n, _ = hand(500, 118, "thanks for scrolling this far. the tabs are still open.", 12, SILVER, "middle", 'opacity=".7"')
    b += flower(500, 38, 10, 5) + t + heart(500, 86, 12) + n
    b += branch([(-10, 140), (80, 128), (170, 144), (250, 130)], 4, seed=22, density=.7, fr=9)
    b += branch([(1010, 140), (920, 126), (830, 144), (750, 132)], 4, seed=23, density=.7, fr=9)
    b += falling(W, H, 14, 33) + stars(W, H, 14, 34, avoid=(300, 30, 700, 130))
    save("footer.svg", svg(W, H, b))

# ======================================================================
# README (generated, so links always match the cards)
# ======================================================================
def write_readme(main, featured, minis, mode):
    L = []
    A = lambda s: L.append(s)
    A("<!--\n  SAKURAHUB: generated by _source/build_assets.py (the workflow in .github/ re-runs it every few hours).\n"
      "  To change wording or layout, edit _source/build_assets.py, not this file: this file is rewritten.\n  data source: " + mode + "\n-->\n")
    A('<div align="center">\n  <img src="assets/hero.svg" alt="I should probably stop making things. Anyway, here\'s what I\'m building." width="100%">\n</div>\n')
    def img(n, alt="", w="100%"): return f'<img src="assets/{n}" alt="{esc(alt)}" width="{w}">'
    A(img("divider-1.svg") + "\n"); A(img("about.svg", "so... who am i?") + "\n"); A(img("divider-2.svg") + "\n")
    A('<table>\n  <tr>\n    <td width="50%" valign="top">' + img("tools.svg", "things i keep reaching for: " + ", ".join(TOOLS)) + '</td>\n'
      '    <td width="50%" valign="top">' + img("poking.svg", "currently poking at: " + ", ".join(POKING)) + '</td>\n  </tr>\n</table>\n')
    A(img("divider-3.svg") + "\n"); A(img("header-projects.svg", "look what i made.") + "\n")
    if main:
        d = info(main)
        A(f'<a href="{d["url"]}">' + img("project-main.svg", f'{d["name"]}: {d["desc"]}') + "</a>\n")
    if featured:
        w = 100 // len(featured)
        A("<table>\n  <tr>")
        for i, r in enumerate(featured):
            d = info(r)
            A(f'    <td width="{w}%" valign="top"><a href="{d["url"]}">' + img(f"project-{i+1}.svg", f'{d["name"]}: {d["desc"]}') + "</a></td>")
        A("  </tr>\n</table>\n")
    if minis:
        A(img("header-more.svg", "also in the pile.") + "\n")
        w = 100 // len(minis)
        A("<table>\n  <tr>")
        for i, r in enumerate(minis):
            d = info(r)
            A(f'    <td width="{w}%" valign="top"><a href="{d["url"]}">' + img(f"mini-{i+1}.svg", f'{d["name"]}: {d["desc"]}') + "</a></td>")
        A("  </tr>\n</table>\n")
    A(img("building.svg", "anyway, here's what i'm building") + "\n"); A(img("divider-4.svg") + "\n")
    A(img("stats.svg", "tiny numbers from the chaos") + "\n")
    A(img("contributions.svg", "planting little bits of me here: my real GitHub contributions over the last year") + "\n")
    A(img("divider-5.svg") + "\n"); A(img("diary.svg", "developer diary: my latest real commits") + "\n")
    A(img("contact.svg", "wanna cook something weird?") + "\n")
    A(f'<div align="center">\n  <a href="https://github.com/{PROFILE_LOGIN}">' + img("btn-github.svg", "github", None).replace(' width="None"', ' height="40"') + '</a>\n'
      f'  <a href="https://github.com/{PROFILE_LOGIN}?tab=repositories">' + img("btn-repos.svg", "repositories", None).replace(' width="None"', ' height="40"') + '</a>\n</div>\n')
    A(img("footer.svg", "okay bye, go look at my stuffs.") + "\n")
    with open(os.path.join(OUT, "..", "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))

# ======================================================================
def build(live):
    for old in glob.glob(os.path.join(OUT, "*.svg")):
        os.remove(old)
    repos = live["repos"] if live else fallback_repos()
    pinned = live["pinned"] if live else []
    main, featured, minis, pool = select(repos, pinned)
    hero()
    divider("divider-1.svg", "psst. you're still here? good.", 1)
    divider("divider-2.svg", "petals included. no refunds.", 2)
    divider("divider-3.svg", "tab count: classified.", 3)
    divider("divider-4.svg", "status: the pro of procrastinate.", 4)
    divider("divider-5.svg", "small ideas. big chaos.", 5)
    about(); tools(); poking()
    section_header("header-projects.svg", "look what i made.", "pulled live from my real repos. every card links to the real thing.", 2)
    if main: oneiric_spotlight(info(main))
    for i, r in enumerate(featured): project_card(i, info(r), ACCENTS[i % 5])
    if minis: section_header("header-more.svg", "also in the pile.", "smaller builds that still count.", 5)
    for i, r in enumerate(minis): mini_card(i, info(r), ACCENTS[i % 2])
    # "building": main project first, then whatever I pushed to most recently
    recent = sorted([r for r in pool if r is not main], key=lambda r: r["pushed"] or "", reverse=True) if live else [r for r in pool if r is not main]
    rows = []
    for r in ([main] if main else []) + recent[:2]:
        d = info(r)
        rows.append((d["name"], d["desc"], "main project" if r is main else (f'pushed {d["updated"]}' if d["updated"] else d["badge"])))
    building(rows)
    stats(live["stats"] if live else FALLBACK_STATS, bool(live))
    contributions(live["calendar"] if live else None)
    diary(live["commits"] if live else [])
    contact(); footer()
    button("btn-github.svg", "github", LAV, g_gh)
    button("btn-repos.svg", "repositories", SAKURA, g_repo, 170)
    write_readme(main, featured, minis, "live from GitHub" if live else "offline fallback (no token)")
    print("live data:", "yes" if live else "no (fallback)", "|", len(os.listdir(OUT)), "svgs | readme written")

if __name__ == "__main__":
    build(fetch_live() if "--live" in sys.argv else None)
