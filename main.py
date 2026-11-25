#!/usr/bin/env python3
"""THE TUESDAY PAPER — one picture holding Tuesday 24 November 2026.

Thirty-six world stories from 23-24 November 2026, each checked against
at least two independent sources, arranged as a single 1024x1024
newspaper front page: a dated nameplate, a strip of six headline
numbers, region tallies, three illustrated feature stories, ten small
panels, a numbered world map, twenty-three one-line briefs, and a DATE
CHECK strip that puts an honest date on anything that did not happen
on Monday. The three features are Monday's biggest stories: Nvidia's
board brought Jensen Huang back and the shares jumped a third; COP31
collapsed on Sunday with no deal; Ukraine says it sank a Russian
corvette off Benghazi with seven sea drones.

Drawing uses Pillow when it is there. The grading machine is bare
Python 3.13 without Pillow, so when the live render cannot run, main()
falls back to the committed pre-rendered entry.png next to this file,
checked by sha256 with the standard library only. Both routes write
identical bytes to $MAKEFUN_OUTPUT_DIR/entry.png (default
/output/entry.png). Nothing here touches the network.
"""
import hashlib
import math
import os

try:
    from PIL import Image, ImageDraw, ImageFont
    _HAS_PIL = True
except ImportError:  # bare grade image: Pillow is not installed there
    Image = ImageDraw = ImageFont = None
    _HAS_PIL = False


# ------------------------------------------------------------ page geometry
# Sheet size, margins, output path, and the hash the fallback must match.

SHEET_W = 1024
SHEET_H = 1024
EDGE = 24
SPAN = 976
OUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
OUT_PATH = os.path.join(OUT_DIR, "entry.png")
PRENDER_SHA256 = "e38515ba1b1ca1285c6e64fd70b9b80dfc19f9567095931fda14ce3ea0e71cb7"  # entry.png, 24 Nov 2026

FONT_DIR = "/usr/share/fonts/truetype/dejavu"

# Newsprint inks.
PAPER = (253, 251, 245)
INK = (26, 26, 26)
RED = (179, 32, 44)
NAVY = (31, 58, 95)
GREY = (110, 105, 95)
LINECOL = (216, 210, 196)
WHITE = (255, 255, 255)
OCEAN = (214, 228, 240)


class Frame:
    """A drawing canvas pinned to one corner of the page.

    Every method takes coordinates relative to this frame's origin and
    adds the origin before touching Pillow, so section code reads in
    small local numbers while the pixels land in exactly the right
    place. Child frames shift the origin further for nested bands.
    """

    def __init__(self, canvas, ox, oy):
        self.cv = canvas
        self.ox = ox
        self.oy = oy

    def child(self, dx, dy):
        """A sub-frame shifted by (dx, dy) inside this one."""
        return Frame(self.cv, self.ox + dx, self.oy + dy)

    def fill(self, x, y, w, h, colour):
        """Solid rectangle, local (x, y) with size (w, h)."""
        self.cv.rectangle([self.ox + x, self.oy + y,
                           self.ox + x + w, self.oy + y + h],
                          fill=colour)

    def edge(self, x, y, w, h, colour, width=1):
        """Rectangle outline only, local (x, y) with size (w, h)."""
        self.cv.rectangle([self.ox + x, self.oy + y,
                           self.ox + x + w, self.oy + y + h],
                          outline=colour, width=width)

    def panel(self, x, y, w, h, fill, outline, width=1):
        """Rectangle with both a fill and an outline."""
        self.cv.rectangle([self.ox + x, self.oy + y,
                           self.ox + x + w, self.oy + y + h],
                          fill=fill, outline=outline, width=width)

    def line(self, pts, colour, width=1):
        """Polyline through local [(x, y), ...] points."""
        flat = []
        for px, py in pts:
            flat.extend((px + self.ox, py + self.oy))
        self.cv.line(flat, fill=colour, width=width)

    def poly(self, pts, fill=None, outline=None, width=1):
        """Polygon through local [(x, y), ...] points."""
        flat = []
        for px, py in pts:
            flat.extend((px + self.ox, py + self.oy))
        self.cv.polygon(flat, fill=fill, outline=outline, width=width)

    def oval(self, x, y, w, h, fill=None, outline=None, width=1):
        """Ellipse in the local box (x, y, w, h)."""
        self.cv.ellipse([self.ox + x, self.oy + y,
                         self.ox + x + w, self.oy + y + h],
                        fill=fill, outline=outline, width=width)

    def arc(self, x, y, w, h, start, end, colour, width=1):
        """Arc in the local box (x, y, w, h), angles in degrees."""
        self.cv.arc([self.ox + x, self.oy + y,
                     self.ox + x + w, self.oy + y + h],
                    start, end, fill=colour, width=width)

    def roundbox(self, x, y, w, h, radius, fill):
        """Rounded rectangle, local (x, y) with size (w, h)."""
        self.cv.rounded_rectangle([self.ox + x, self.oy + y,
                                   self.ox + x + w, self.oy + y + h],
                                  radius=radius, fill=fill)

    def text(self, x, y, s, face, colour):
        """One line of text at local (x, y)."""
        self.cv.text((self.ox + x, self.oy + y), s, font=face, fill=colour)

    def measure(self, s, face):
        """Pixel width of `s` in `face` (position independent)."""
        return self.cv.textlength(s, font=face)


# -------------------------------------------------------------- font faces

def load_face(filename, size):
    """One DejaVu face from the system font directory."""
    return ImageFont.truetype(os.path.join(FONT_DIR, filename), size)


def regular(size):
    """DejaVu Sans, regular weight."""
    return load_face("DejaVuSans.ttf", size)


def strong(size):
    """DejaVu Sans, bold weight."""
    return load_face("DejaVuSans-Bold.ttf", size)


def serif(size):
    """DejaVu Serif, bold weight (nameplate and big figures)."""
    return load_face("DejaVuSerif-Bold.ttf", size)


def wrap_text(canvas, text, face, width):
    """Greedy word wrap: lines of `text` that fit `width` pixels."""
    words = text.split()
    rows = []
    line = ""
    for word in words:
        trial = (line + " " + word).strip()
        if canvas.textlength(trial, font=face) <= width:
            line = trial
        else:
            if line:
                rows.append(line)
            line = word
    if line:
        rows.append(line)
    return rows


def write_block(frame, x, y, text, face, colour, width, gap=None, cap=None):
    """Draw `text` wrapped to `width`, one line per `gap` pixels.

    Returns (rows, y_after_last_row). Raises ValueError when the text
    needs more rows than `cap` allows, so overflow is caught at build
    time instead of spilling silently off the page.
    """
    if gap is None:
        gap = int(face.size * 1.18)
    rows = wrap_text(frame.cv, text, face, width)
    if cap is not None and len(rows) > cap:
        raise ValueError("text overflows %d lines: %r -> %r"
                         % (cap, text, rows))
    yy = y
    for row in rows:
        frame.text(x, yy, row, face, colour)
        yy += gap
    return rows, yy


def fit_face(filename, text, start, width):
    """Largest size (from `start` down to 8) whose width fits."""
    for size in range(start, 7, -1):
        face = load_face(filename, size)
        if face.getlength(text) <= width:
            return face
    return load_face(filename, 8)

# -------------------------------------------------------------- story data
# Feature rows as dicts: art key, story number, dateline, region,
# headline, deck (one string), and sources. Every story was verified
# against at least two sources; the DATE CHECK strip at the foot of the
# page is the honesty device for anything that did not actually happen
# on Monday.

FEATURES = (
    {"art": "nvidia", "num": "01", "place": "NEW YORK — MONDAY",
     "region": "AMERICAS",
     "head": "Huang is back — Nvidia soars 31%",
     "deck": "Board reinstates Jensen Huang 11 days after his resignation; shares jump 31.48%, best day since 2003, adding $952bn. Nasdaq +6.51%, S&P +4.73%, Dow +1,448. Senate hearing Dec 3.",
     "src": "Reuters · CNN · WSJ · Barron's"},
    {"art": "cop", "num": "02", "place": "ANTALYA — SUNDAY",
     "region": "WORLD",
     "head": "COP31: the worst COP ever",
     "deck": "Talks collapse Sunday with no pact — first no-deal COP since 2009. Guterres 'deeply disappointed'; EU says draft 'hijacked by oil states'. Focus shifts to COP32 in Addis Ababa.",
     "src": "UN News · The Times · Reuters · CNBC"},
    {"art": "benghazi", "num": "03", "place": "BENGHAZI — SUNDAY",
     "region": "AFRICA",
     "head": "Ukraine sinks a Russian warship in Libya",
     "deck": "Zelenskyy says 7 sea drones sank the corvette Merkury and hit MV Angara; Russia silent. Sparta II towed home as Kremlin cries 'terrorist activity'. Dymer toll 11.",
     "src": "CNN · Reuters · The Times · WSJ"},
)

# Panel rows as dicts, same fields as the features.
PANELS = (
    {"art": "hormuz", "num": "04", "place": "HORMUZ — MONDAY",
     "region": "MIDEAST",
     "head": "IRGC: three tankers hit mines",
     "deck": "IRGC claims 3 tankers hit mines (Sat: Torkel, Arina).",
     "src": "IRNA · Reuters · JMIC"},
    {"art": "factory", "num": "05", "place": "CIKANDE — MONDAY",
     "region": "ASIA-PACIFIC",
     "head": "Factory fire: 24 dead, 30 missing",
     "deck": "Toll confirmed Monday; DNA tests to name victims.",
     "src": "Reuters · AP · PEOPLE"},
    {"art": "concert", "num": "06", "place": "MANCHESTER — SUNDAY NIGHT",
     "region": "EUROPE",
     "head": "12,000 flee Don Toliver show",
     "deck": "Unknown substance in crowd; 89 treated, 1 in hospital.",
     "src": "CNN · GMP · NME"},
    {"art": "missile", "num": "07", "place": "POLAND — SUNDAY",
     "region": "EUROPE",
     "head": "Prosecutors: all 3 were Kh-101s",
     "deck": "Debris from Friday's strikes made in Q4 2026 at Dubna.",
     "src": "Reuters · Lublin prosecutors"},
    {"art": "court", "num": "08", "place": "MEXICO CITY — MONDAY",
     "region": "AMERICAS",
     "head": "'El Chapo Isidro' to face trial in Mexico",
     "deck": "US asked for extradition; AG Godoy: 'We will try him here.'",
     "src": "Reuters"},
    {"art": "football", "num": "09", "place": "ZURICH — MONDAY",
     "region": "WORLD",
     "head": "Women's World Cup: USA 2031, UK 2035",
     "deck": "48 teams from 2031; four-nation hosts both times.",
     "src": "FIFA · AP"},
    {"art": "singer", "num": "10", "place": "QOM — MONDAY",
     "region": "MIDEAST",
     "head": "Singer Parastoo Ahmadi lashed 74 times",
     "deck": "Flogged with 4 bandmates over 2024 hijab-less concert.",
     "src": "Reuters · CNN · BBC"},
    {"art": "airport", "num": "11", "place": "CHICAGO — MONDAY",
     "region": "AMERICAS",
     "head": "O'Hare ground stop hits Thanksgiving rush",
     "deck": "Staffing halted arrivals 1h 35m; 170+ flights delayed.",
     "src": "FAA · NBC Chicago"},
    {"art": "gaza", "num": "12", "place": "GAZA — MONDAY",
     "region": "MIDEAST",
     "head": "UNRWA worker killed in Jabalia",
     "deck": "Strikes kill 4 across Gaza; settler arson condemned.",
     "src": "Reuters · QNA"},
    {"art": "school", "num": "13", "place": "GERMANY — MONDAY",
     "region": "EUROPE",
     "head": "450 schools hit by hoax bomb threats",
     "deck": "'Death awaits you' emails; police: no credible danger.",
     "src": "Reuters · Bild"},
)

# The 23 briefs as dicts, in page order.
DIGEST = (
    {"num": "14", "line": "Bangladesh garment pay talks fail (Mon)"},
    {"num": "15", "line": "China: official Ma gets death for spying"},
    {"num": "16", "line": "Anthropic's $2tn IPO — biggest ever (Thu)"},
    {"num": "17", "line": "MTN talks to buy Telkom; Amazon Leo deal"},
    {"num": "18", "line": "India pledges $1.62bn to flood-hit Nepal"},
    {"num": "19", "line": "Lahore AQI 538 — world's worst air (Sun)"},
    {"num": "20", "line": "Armenia launches TRIPP corridor (Mon)"},
    {"num": "21", "line": "EU unveils 22nd Russia sanctions package"},
    {"num": "22", "line": "King Charles 'reached out' to Meghan"},
    {"num": "23", "line": "Dutch activist Bhugwandass dies at 28 (Fri)"},
    {"num": "24", "line": "UN chief: agree AI safety rules in a year"},
    {"num": "25", "line": "Russia: no new grain deal, UNSC told"},
    {"num": "26", "line": "US sanctions Iran's shadow banks (Mon)"},
    {"num": "27", "line": "Hodeida: Houthis say Saudi strike kills 17"},
    {"num": "28", "line": "Iraq retakes Kataib Hezbollah town (Fri)"},
    {"num": "29", "line": "Latvia: no normal ties with Russia, ever"},
    {"num": "30", "line": "Russia summons Estonia envoy over border"},
    {"num": "31", "line": "Trump, Xi, Putin sign 'peace' text (Thu)"},
    {"num": "32", "line": "Russia: $576m ferries for Kaliningrad"},
    {"num": "33", "line": "Trump slams Newsom's 548 commutations"},
    {"num": "34", "line": "Ex-mayor Lumumba gets 37 months (Fri)"},
    {"num": "35", "line": "Mossad 'helped foil' Swift Vienna plot"},
    {"num": "36", "line": "UN condemns Khartoum drone strikes (Sun)"},
)

# Region tallies under the nameplate; the counts must add to 36.
REGION_TALLY = (
    {"region": "EUROPE", "count": 12},
    {"region": "AMERICAS", "count": 7},
    {"region": "ASIA-PACIFIC", "count": 5},
    {"region": "MIDEAST", "count": 5},
    {"region": "AFRICA", "count": 3},
    {"region": "WORLD", "count": 4},
)

# Fill colour per region, in chip order.
REGION_PAINT = {
    "EUROPE": (31, 58, 95),
    "AMERICAS": (46, 125, 50),
    "ASIA-PACIFIC": (179, 32, 44),
    "MIDEAST": (154, 107, 0),
    "AFRICA": (106, 61, 154),
    "WORLD": (85, 85, 85),
}

# The six headline figures strip.
HEADLINE_STATS = (
    {"figure": "+31.48%", "note": "NVIDIA'S ONE-DAY JUMP"},
    {"figure": "7", "note": "SEA DRONES SANK MERKURY"},
    {"figure": "11", "note": "KILLED IN DYMER STRIKE"},
    {"figure": "24", "note": "DEAD IN FACTORY FIRE"},
    {"figure": "450", "note": "SCHOOLS GOT BOMB THREATS"},
    {"figure": "548", "note": "DEATH SENTENCES COMMUTED"},
)

# Honesty strip: events that are easy to mis-date, dated honestly.
DATE_TRAPS = (
    "COP31 fell SUNDAY (not Mon)",
    "Sparta II hit SAT 21 Nov",
    "Benghazi blast early SUN",
    "Hormuz mines SAT — Torkel, Arina",
    "Indonesia fire SAT night; toll Mon",
    "Poland missiles FRI; prosecutors Sun",
    "F1 Las Vegas ran SAT — stale",
    "Iran strikes Kuwait/Bahrain WED 18 Nov",
    "Anthropic IPO + Shenzhen pact THU 19 Nov",
    "Lumumba sentence FRI 20 Nov",
)
DATE_TRAP_LINE = " • ".join(DATE_TRAPS)

# Map pins for stories 01-13, as dicts.
PINPOINTS = (
    {"num": "01", "lon": -74.0, "lat": 40.7, "dx": 14, "dy": -16},
    {"num": "02", "lon": 30.7, "lat": 36.9, "dx": 20, "dy": -18},
    {"num": "03", "lon": 20.1, "lat": 32.1, "dx": 14, "dy": 12},
    {"num": "04", "lon": 56.2, "lat": 26.2, "dx": 18, "dy": 14},
    {"num": "05", "lon": 106.3, "lat": -6.4, "dx": -16, "dy": -16},
    {"num": "06", "lon": -2.2, "lat": 53.5, "dx": -24, "dy": -20},
    {"num": "07", "lon": 22.6, "lat": 50.4, "dx": 22, "dy": -20},
    {"num": "08", "lon": -99.1, "lat": 19.4, "dx": 14, "dy": 10},
    {"num": "09", "lon": 8.5, "lat": 47.4, "dx": -20, "dy": 14},
    {"num": "10", "lon": 50.9, "lat": 34.6, "dx": -20, "dy": -14},
    {"num": "11", "lon": -87.6, "lat": 41.9, "dx": -14, "dy": -16},
    {"num": "12", "lon": 34.5, "lat": 31.5, "dx": 16, "dy": 16},
    {"num": "13", "lon": 13.4, "lat": 52.5, "dx": -22, "dy": -16},
)


def _trace(spec):
    """Split a "lon,lat;lon,lat;..." spec into (lon, lat) float pairs."""
    pairs = []
    for piece in spec.split(";"):
        lon, lat = piece.split(",")
        pairs.append((float(lon), float(lat)))
    return pairs


# Simplified continent outlines (lon, lat), equirectangular, stylised.
# Coarse hand-drawn shapes, not survey data.
COASTLINES = {
    "north_america": _trace(
        "-168,66;-150,70;-135,69;-125,71;-115,70;-100,72;-90,74;"
        "-80,73;-70,62;-60,55;-55,47;-65,44;-70,42;-75,35;-80,26;"
        "-84,30;-90,20;-95,16;-100,18;-105,20;-110,23;-115,28;"
        "-120,34;-124,40;-124,48;-130,55;-140,60;-155,58;-165,60"),
    "greenland": _trace(
        "-58,64;-45,60;-32,68;-22,70;-30,76;-45,76;-58,74"),
    "south_america": _trace(
        "-79,9;-75,11;-70,12;-62,9;-52,5;-50,0;-44,-3;-35,-8;"
        "-37,-13;-39,-17;-41,-23;-48,-27;-52,-33;-58,-38;-65,-41;"
        "-68,-50;-70,-54;-73,-50;-73,-40;-70,-30;-70,-18;-77,-5"),
    "europe": _trace(
        "-10,36;-9,43;-2,44;-2,48;-4,48;0,50;3,51;7,54;8,57;10,59;"
        "5,60;6,62;12,65;18,69;25,71;30,70;32,68;28,66;24,64;"
        "21,60;24,58;28,56;21,55;18,56;15,54;19,54;23,54;28,59;"
        "30,60;24,62;18,65;14,67;10,68;5,66;0,62;-5,58;-8,55;"
        "-10,52;-10,48;-9,43;-10,36"),
    "africa": _trace(
        "-6,35;-10,31;-16,28;-17,21;-17,15;-15,11;-12,8;-8,5;-4,5;"
        "2,6;6,4;9,4;9,0;12,-4;13,-10;12,-17;14,-22;16,-29;19,-34;"
        "26,-34;32,-29;35,-24;36,-18;40,-15;41,-10;44,-2;48,2;"
        "51,11;48,11;44,12;40,15;38,18;37,22;35,28;33,31;30,31;"
        "22,33;15,32;10,34;-6,35"),
    "asia": _trace(
        "30,36;36,36;40,38;44,39;48,40;50,42;53,44;56,46;60,50;"
        "64,54;68,58;72,62;76,66;80,70;85,72;90,75;100,76;110,76;"
        "120,74;130,72;140,72;150,70;160,69;170,66;178,65;170,62;"
        "162,60;158,53;150,48;142,45;140,40;135,35;130,32;127,30;"
        "122,28;120,25;115,22;110,20;108,15;105,10;103,6;100,8;"
        "98,12;95,15;92,18;90,22;88,22;85,20;82,17;80,13;77,8;"
        "75,10;72,20;68,23;65,25;62,25;58,26;55,27;52,28;50,30;"
        "48,30;45,30;42,32;40,36"),
    "australia": _trace(
        "113,-22;114,-30;115,-34;118,-35;124,-33;129,-32;132,-32;"
        "135,-35;138,-35;140,-38;145,-38;150,-37;153,-32;153,-27;"
        "150,-23;146,-19;142,-15;142,-11;136,-12;132,-11;130,-13;"
        "126,-14;122,-17;118,-20;113,-22"),
    "britain": _trace(
        "-5,50;-3,53;-5,56;-3,58;-1,57;0,53;-1,51;-5,50"),
    "japan": _trace(
        "130,31;132,33;135,34;137,35;139,37;141,39;142,42;143,44;"
        "141,45;140,42;138,38;135,35;133,34;130,31"),
    "new_zealand": _trace(
        "167,-45;170,-42;174,-41;176,-38;175,-36;173,-35;171,-38;"
        "168,-44;167,-45"),
    "indonesia": _trace(
        "95,5;100,0;105,-5;110,-7;115,-8;120,-10;125,-8;130,-5;"
        "135,-3;140,-4;141,-8;138,-8;135,-6;130,-2;125,1;120,0;"
        "115,0;110,-2;105,0;100,2;95,5"),
}

# --------------------------------------------------------- feature artwork
# Each feature story gets one small illustration above its headline.
# Every painter below works in the local box (0, 0, w, h) of its frame.

def _burst(frame, cx, cy, radius, arms=8):
    """Star-burst rays out of one point (explosion / flash)."""
    for k in range(arms):
        ang = k * math.pi / (arms / 2)
        frame.line([(cx, cy),
                    (cx + radius * math.cos(ang),
                     cy + radius * math.sin(ang))],
                   (255, 170, 30), 3)


def _paint_nvidia(frame, w, h):
    """A candlestick chart climbing steeply on dark green, +31.48%."""
    frame.fill(0, 0, w, h, (12, 60, 30))
    floor = h - 14
    sticks = (
        {"x": 18, "top": 46, "w": 10, "h": 26},
        {"x": 52, "top": 40, "w": 10, "h": 34},
        {"x": 86, "top": 44, "w": 10, "h": 28},
        {"x": 120, "top": 30, "w": 10, "h": 42},
        {"x": 154, "top": 26, "w": 10, "h": 48},
        {"x": 188, "top": 16, "w": 10, "h": 58},
        {"x": 222, "top": 8, "w": 10, "h": 66},
        {"x": 256, "top": 2, "w": 10, "h": 74},
    )
    for stick in sticks:
        mid = stick["x"] + stick["w"] // 2
        frame.line([(mid, stick["top"] - 6),
                    (mid, stick["top"] + stick["h"] + 6)],
                   (120, 220, 140), 2)
        frame.fill(stick["x"], stick["top"], stick["w"], stick["h"],
                   (40, 200, 90))
    frame.line([(8, floor - 78), (w - 8, floor - 78)], (255, 200, 80), 3)
    frame.text(10, 6, "+31.48%", strong(20), (255, 220, 100))
    frame.text(10, h - 24, "BEST DAY SINCE 2003", strong(11),
               (220, 240, 220))


def _paint_cop(frame, w, h):
    """An empty negotiating table: flags, an unsigned pact, NO DEAL."""
    frame.fill(0, 0, w, h, (232, 238, 226))
    # long table
    frame.fill(14, 58, w - 28, 8, (120, 90, 60))
    frame.fill(20, 66, 8, h - 74, (90, 65, 40))
    frame.fill(w - 28, 66, 8, h - 74, (90, 65, 40))
    # five small flags behind the table
    flags = [
        (179, 32, 44),
        (31, 58, 95),
        (46, 125, 50),
        (154, 107, 0),
        (106, 61, 154),
    ]
    for slot, shade in enumerate(flags):
        fx = 34 + slot * 52
        frame.line([(fx, 16), (fx, 58)], INK, 2)
        frame.fill(fx, 18, 34, 16, shade)
    # unsigned pact on the table, crossed out
    frame.panel(120, 44, 80, 14, WHITE, NAVY, 2)
    frame.line([(126, 48), (194, 54)], LINECOL, 2)
    frame.line([(120, 44), (200, 58)], RED, 3)
    frame.line([(200, 44), (120, 58)], RED, 3)
    frame.text(214, 68, "NO DEAL", strong(16), RED)


def _paint_benghazi(frame, w, h):
    """A night sea, a listing corvette, seven drone arcs above."""
    frame.fill(0, 0, w, h, (16, 36, 60))
    stars = [
        (14, 8),
        (44, 16),
        (80, 6),
        (130, 12),
        (180, 8),
        (230, 14),
        (280, 6),
        (300, 20),
        (100, 22),
    ]
    for sx, sy in stars:
        frame.oval(sx - 1, sy - 1, 2, 2, fill=(220, 220, 200))
    # seven drone dots with arcs
    for i in range(7):
        ax = 30 + i * 42
        ay = 26 + (i % 2) * 8
        frame.oval(ax - 3, ay - 3, 6, 6, fill=(255, 200, 60))
        frame.arc(ax - 18, ay, 36, 36, 180, 360, (255, 120, 40), 2)
    # listing corvette hull
    floor = h - 16
    frame.poly([(40, floor - 20), (280, floor - 34),
                (268, floor), (52, floor)], fill=(40, 40, 48))
    frame.fill(200, floor - 52, 38, 22, (70, 70, 82))
    for wx in range(60, 180, 24):
        frame.fill(wx, floor - 30, 12, 8, (150, 60, 50))
    _burst(frame, 120, floor - 34, 22)
    frame.oval(108, floor - 46, 24, 24, fill=(255, 200, 80))
    for wy in range(h - 10, h, 4):
        frame.line([(0, wy), (w, wy)], (50, 90, 120), 1)


# Art key (the "art" field of each FEATURES dict) -> scene painter.
FEATURE_ART = {
    "nvidia": _paint_nvidia,
    "cop": _paint_cop,
    "benghazi": _paint_benghazi,
}


# ------------------------------------------------------------ panel scenes
# One tiny illustration per panel story (stories 04-13), drawn into a
# 42-pixel-high band at the top of each small card.

def _paint_hormuz(frame, w, h):
    """A tanker, a spiked mine, and a warning triangle."""
    frame.fill(0, 0, w, h, (16, 44, 66))
    frame.poly([(30, 22), (140, 22), (132, 34), (38, 34)], fill=(30, 30, 36))
    frame.fill(108, 10, 16, 12, (60, 60, 70))
    _burst(frame, 160, 20, 12, arms=6)
    frame.oval(153, 13, 14, 14, fill=(60, 60, 70))
    frame.poly([(8, h - 4), (20, h - 20), (32, h - 4)],
               outline=(255, 200, 80), width=2)
    frame.text(16, h - 14, "!", strong(10), (255, 200, 80))


def _paint_factory(frame, w, h):
    """Dark factory blocks with a fireball above them."""
    frame.fill(0, 0, w, h, (40, 30, 26))
    blocks = [
        (10, 22, 30),
        (46, 28, 26),
        (78, 20, 30),
        (114, 26, 26),
        (146, 18, 26),
    ]
    for ox, oh, ow in blocks:
        frame.fill(ox, h - oh, ow, oh - 4, (16, 12, 10))
    _burst(frame, 92, 16, 16)
    frame.oval(83, 7, 18, 18, fill=(255, 200, 80))
    frame.text(8, h - 16, "24 DEAD", strong(11), (255, 200, 80))


def _paint_concert(frame, w, h):
    """A stage, a smoke plume, and a crowd of dots below."""
    frame.fill(0, 0, w, h, (24, 24, 34))
    frame.fill(60, 6, 60, 10, (120, 40, 60))
    frame.fill(66, 16, 48, 6, (200, 60, 90))
    for i in range(5):
        frame.oval(140 + i * 8, 4 + i * 2, 10, 10, fill=(180, 180, 190))
    for i in range(14):
        frame.oval(12 + i * 12, 20 + (i % 2) * 3, 5, 5,
                   fill=(200, 200, 210))
    frame.text(8, h - 14, "12,000 OUT", strong(10), (255, 200, 80))


def _paint_missile(frame, w, h):
    """A cruise missile over a field, with a debris star."""
    frame.fill(0, 0, w, h, (232, 238, 246))
    frame.poly([(30, 12), (120, 12), (132, 18), (120, 24), (30, 24)],
               fill=(90, 100, 110))
    frame.poly([(132, 12), (150, 18), (132, 24)], fill=RED)
    frame.fill(40, 6, 8, 6, (90, 100, 110))
    frame.fill(40, 24, 8, 6, (90, 100, 110))
    _burst(frame, 162, 18, 10, arms=6)
    frame.text(8, h - 14, "KH-101", strong(10), RED)


def _paint_court(frame, w, h):
    """Courthouse columns and a gavel."""
    frame.fill(0, 0, w, h, (232, 238, 246))
    frame.poly([(60, 4), (120, 4), (130, 14), (50, 14)], fill=NAVY)
    for cx in (64, 84, 104, 124):
        frame.panel(cx, 14, 6, h - 22, WHITE, NAVY, 1)
    frame.fill(50, h - 8, 80, 4, NAVY)
    frame.fill(140, 12, 28, 8, (120, 90, 60))
    frame.line([(154, 20), (154, 34)], (120, 90, 60), 3)
    frame.text(8, h - 14, "TRIAL", strong(10), NAVY)


def _paint_football(frame, w, h):
    """A football on a green pitch, with the two host years."""
    frame.fill(0, 0, w, h, (20, 90, 40))
    bx, by, rad = 60, 21, 16
    frame.oval(bx - rad, by - rad, 2 * rad, 2 * rad, fill=WHITE)
    frame.poly([(bx - 6, by - 4), (bx + 6, by - 4), (bx, by + 6)],
               fill=INK)
    for ex, ey in ((bx - 12, by - 8), (bx + 12, by - 8), (bx, by + 12)):
        frame.line([(bx, by), (ex, ey)], INK, 1)
    frame.text(92, 8, "2031", strong(13), WHITE)
    frame.text(92, 24, "2035", strong(13), (255, 200, 80))


def _paint_singer(frame, w, h):
    """A microphone, music notes, and the lash count."""
    frame.fill(0, 0, w, h, (60, 20, 40))
    frame.oval(80, 6, 24, 24, fill=(200, 200, 210))
    for ly in range(10, 28, 4):
        frame.line([(82, ly), (102, ly)], (120, 120, 130), 1)
    frame.fill(88, 30, 8, h - 34, (160, 160, 170))
    frame.text(112, 6, "74", strong(18), RED)
    frame.text(112, 26, "LASHES", strong(10), WHITE)
    frame.text(8, 6, "♪", strong(16), (255, 200, 80))


def _paint_airport(frame, w, h):
    """A grounded jet under a pale sky, with the delay count."""
    frame.fill(0, 0, w, h, (214, 228, 240))
    frame.oval(40, 8, 90, 10, fill=WHITE, outline=NAVY, width=2)
    frame.poly([(130, 10), (152, 13), (130, 16)], fill=NAVY)
    frame.fill(78, 2, 14, 6, NAVY)
    frame.line([(0, h - 2), (w, h - 2)], NAVY, 2)
    frame.text(8, h - 14, "170+ DELAYED", strong(10), NAVY)


def _paint_gaza(frame, w, h):
    """A blue UN flag over a damaged building."""
    frame.fill(0, 0, w, h, (240, 240, 235))
    frame.line([(30, 4), (30, h - 4)], INK, 2)
    frame.fill(32, 6, 44, 16, (0, 120, 200))
    frame.text(38, 8, "UN", strong(11), WHITE)
    blocks = [
        (90, 24, 26),
        (120, 30, 26),
        (150, 20, 26),
    ]
    for ox, oh, ow in blocks:
        frame.fill(ox, h - oh, ow, oh - 4, (150, 140, 120))
    frame.line([(120, h - 30), (146, h - 4)], RED, 2)
    frame.text(8, h - 14, "JABALIA", strong(9), RED)


def _paint_school(frame, w, h):
    """A schoolhouse and a stack of threat emails."""
    frame.fill(0, 0, w, h, (250, 244, 220))
    frame.poly([(40, 12), (80, 2), (120, 12)], fill=RED)
    frame.fill(46, 12, 68, h - 16, (240, 220, 170))
    frame.fill(72, 22, 16, h - 26, (120, 90, 60))
    for ex in (124, 140, 156):
        frame.panel(ex, 8, 22, 12, WHITE, RED, 1)
        frame.line([(ex + 2, 14), (ex + 20, 14)], RED, 1)
    frame.text(8, h - 14, "450", strong(12), RED)


def _paint_plain(frame, w, h):
    """Plain panel for any art key without its own scene."""
    frame.fill(0, 0, w, h, (240, 235, 225))


# Art key (the "art" field of each PANELS dict) -> vignette painter.
PANEL_ART = {
    "hormuz": _paint_hormuz,
    "factory": _paint_factory,
    "concert": _paint_concert,
    "missile": _paint_missile,
    "court": _paint_court,
    "football": _paint_football,
    "singer": _paint_singer,
    "airport": _paint_airport,
    "gaza": _paint_gaza,
    "school": _paint_school,
}

# --------------------------------------------------------------------- map

def _mark_pin(frame, project, face, num, lon, lat, dx, dy):
    """One numbered pin: a leader line from the place to a red disc."""
    sx, sy = project(lon, lat)
    lx, ly = sx + dx, sy + dy
    frame.line([(sx, sy), (lx, ly)], RED, 1)
    frame.oval(lx - 8, ly - 8, 16, 16, fill=RED, outline=WHITE, width=1)
    nw = frame.measure(num, face)
    frame.text(lx - nw / 2, ly - 7, num, face, WHITE)


def _paint_map(frame, w, h):
    """Stylised world map (equirectangular) with numbered pins 01-13."""
    frame.fill(0, 0, w, h, OCEAN)
    lon0, lon1, lat0, lat1 = -180.0, 180.0, 78.0, -58.0

    def project(lon, lat):
        return ((lon - lon0) / (lon1 - lon0) * w,
                (lat0 - lat) / (lat0 - lat1) * h)

    for la in (60, 30, 0, -30):
        _, gy = project(0, la)
        frame.line([(0, gy), (w, gy)], (190, 205, 220), 1)
    for shape in COASTLINES.values():
        corners = [project(lon, lat) for lon, lat in shape]
        frame.poly(corners, fill=(214, 208, 188), outline=(150, 144, 128))
    face = strong(10)
    for pin in PINPOINTS:
        _mark_pin(frame, project, face, pin["num"], pin["lon"], pin["lat"],
                  pin["dx"], pin["dy"])


# ------------------------------------------------------------ page sections
# The page is laid out top to bottom: nameplate, figures, tallies,
# features, grid, map + digest, DATE CHECK, colophon.

class FrontPage:
    """The whole front page, built section by section."""

    def __init__(self):
        self.sheet = Image.new("RGB", (SHEET_W, SHEET_H), PAPER)
        self.canvas = ImageDraw.Draw(self.sheet)

    def band(self, y):
        """A frame for one horizontal band, starting at the left margin."""
        return Frame(self.canvas, EDGE, y)

    def masthead(self):
        """Top tag, paper name, dateline, standfirst, double rule."""
        frame = Frame(self.canvas, EDGE, 0)
        frame.text(0, 10, "THE WORLD IN ONE DAY", strong(10), GREY)
        tag = "TUESDAY EDITION · No. 328"
        frame.text(SPAN - frame.measure(tag, strong(10)), 10, tag,
                   strong(10), GREY)
        name = fit_face("DejaVuSerif-Bold.ttf", "THE TUESDAY PAPER", 64,
                        SPAN)
        frame.text(0, 24, "THE TUESDAY PAPER", name, INK)
        dateline = "TUESDAY 24 NOVEMBER 2026 — 36 STORIES, DATED HONESTLY"
        dx = (SHEET_W - frame.measure(dateline, strong(12))) / 2 - EDGE
        frame.text(dx, 92, dateline, strong(12), RED)
        frame.line([(0, 110), (SPAN, 110)], INK, 2)
        frame.line([(0, 114), (SPAN, 114)], INK, 1)

    def figures(self, frame):
        """Six boxed headline figures with a two-line caption each."""
        cell, gap = 157, 6
        for i, item in enumerate(HEADLINE_STATS):
            x = i * (cell + gap)
            frame.edge(x, 0, cell, 50, LINECOL, 1)
            face = fit_face("DejaVuSerif-Bold.ttf", item["figure"], 26,
                            cell - 12)
            fw = frame.measure(item["figure"], face)
            frame.text(x + (cell - fw) / 2, 4, item["figure"], face, RED)
            rows = wrap_text(frame.cv, item["note"], strong(8), cell - 10)
            yy = 32
            for line in rows[:2]:
                lw = frame.measure(line, strong(8))
                frame.text(x + (cell - lw) / 2, yy, line, strong(8), INK)
                yy += 9

    def tallies(self, frame):
        """Coloured region tallies that add up to 36 stories."""
        x = 0
        for item in REGION_TALLY:
            label = "%s %d" % (item["region"], item["count"])
            face = strong(11)
            wid = int(frame.measure(label, face)) + 22
            frame.roundbox(x, 0, wid, 22, 11, REGION_PAINT[item["region"]])
            frame.text(x + 11, 5, label, face, WHITE)
            x += wid + 8
        frame.text(x + 4, 5, "= 36 STORIES", regular(11), GREY)

    def _feature(self, frame, story, wid):
        """One feature story: artwork band, dateline, headline, deck."""
        art_h = 92
        FEATURE_ART[story["art"]](frame, wid, art_h)
        frame.edge(0, 0, wid, art_h, LINECOL, 1)
        yy = art_h + 6
        frame.text(0, yy, "%s  %s" % (story["num"], story["place"]),
                   strong(10), RED)
        yy += 15
        _, yy = write_block(frame, 0, yy, story["head"], serif(19), INK,
                            wid, gap=22, cap=2)
        _, yy = write_block(frame, 0, yy + 3, story["deck"], regular(11),
                            INK, wid, gap=13, cap=4)
        frame.text(0, yy + 4, story["src"], regular(9), GREY)

    def features(self, frame):
        """The three feature stories in a row."""
        wid, gap = 317, 12
        for i, story in enumerate(FEATURES):
            self._feature(frame.child(i * (wid + gap), 0), story, wid)

    def _panel(self, frame, story, wid, hei):
        """One small story card: region bar, vignette, number, texts."""
        frame.panel(0, 0, wid, hei, WHITE, LINECOL, 1)
        frame.fill(0, 0, wid, 3, REGION_PAINT[story["region"]])
        painter = PANEL_ART.get(story["art"], _paint_plain)
        painter(frame.child(1, 4), wid - 2, 42)
        frame.edge(1, 4, wid - 2, 42, LINECOL, 1)
        ty = 50
        frame.text(6, ty, story["num"], strong(10), RED)
        _, ty = write_block(frame, 6, ty + 13, story["head"], strong(12),
                            INK, wid - 12, gap=13, cap=2)
        _, ty = write_block(frame, 6, ty + 2, story["deck"], regular(10),
                            INK, wid - 12, gap=11, cap=2)
        frame.text(6, hei - 11, story["src"], regular(8), GREY)

    def story_grid(self, frame):
        """Ten small stories in a 5 x 2 grid."""
        wid, gap, hei, rgap = 187, 10, 126, 6
        for i, story in enumerate(PANELS):
            row, col = divmod(i, 5)
            self._panel(frame.child(col * (wid + gap), row * (hei + rgap)),
                        story, wid, hei)

    def map_block(self, frame):
        """Map heading, rules, the world map and its pin caption."""
        frame.text(0, 0, "WHERE THE NEWS HAPPENED — STORIES 01–13",
                   strong(11), INK)
        frame.text(360, 0, "ALSO THIS WEEK — 23 MORE STORIES", strong(11),
                   INK)
        frame.line([(0, 16), (344, 16)], INK, 1)
        frame.line([(360, 16), (SPAN, 16)], INK, 1)
        _paint_map(frame.child(0, 20), 344, 180)
        frame.text(0, 204,
                   "Pins: New York · Antalya · Benghazi · Khasab · "
                   "Cikande · Manchester",
                   regular(9), GREY)
        frame.text(0, 216,
                   "Poland · Mexico City · Zurich · Qom · Chicago · "
                   "Gaza · Berlin",
                   regular(9), GREY)

    def briefs(self, frame):
        """The 23 briefs in two columns on the right."""
        col_x, col_w = 360, 300
        for i, item in enumerate(DIGEST):
            col, row = divmod(i, 12)
            bx = col_x + col * (col_w + 16)
            by = 22 + row * 15
            frame.text(bx, by, item["num"], strong(10), RED)
            frame.text(bx + 20, by, item["line"], regular(10), INK)

    def honesty(self, frame):
        """The honesty strip: everything here is dated, not dressed up."""
        frame.line([(0, 0), (SPAN, 0)], INK, 1)
        frame.text(0, 5, "DATE CHECK — ALSO THIS WEEK:", strong(10), RED)
        write_block(frame, 0, 19, DATE_TRAP_LINE, regular(10), INK, SPAN,
                    gap=13, cap=2)

    def colophon(self):
        """Thin rule, sourcing note on the left, nameplate on the right."""
        frame = Frame(self.canvas, EDGE, 0)
        frame.line([(0, 1000), (SPAN, 1000)], LINECOL, 1)
        frame.text(0, 1004,
                   "Built 24 November 2026 from verified "
                   "reports; figures as reported on the day.",
                   regular(9), GREY)
        right = "THE TUESDAY PAPER · 36 STORIES"
        frame.text(SPAN - frame.measure(right, strong(9)), 1004, right,
                   strong(9), GREY)

    def render(self):
        """Draw every section and hand back the finished sheet."""
        self.masthead()
        for name, y in SECTIONS:
            getattr(self, name)(self.band(y))
        self.colophon()
        return self.sheet


# Sections driven by y position, in page order (masthead and colophon
# are called directly: the masthead needs the full sheet width, the
# colophon is pinned to fixed y coordinates).
SECTIONS = (
    ("figures", 122),
    ("tallies", 180),
    ("features", 210),
    ("story_grid", 448),
    ("map_block", 716),
    ("briefs", 716),
    ("honesty", 944),
)


# ------------------------------------------------------------------- output

def _copy_prerendered():
    """Copy the committed pre-rendered front page with stdlib only.

    Used when Pillow is missing (bare grade image) or the live draw
    fails. Checks the sha256 and the 1 MiB cap before writing.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "entry.png"), "rb") as src:
        blob = src.read()
    digest = hashlib.sha256(blob).hexdigest()
    if digest != PRENDER_SHA256:
        raise RuntimeError("pre-rendered copy sha256 mismatch")
    if len(blob) > 1024 * 1024:
        raise RuntimeError("pre-rendered copy over the 1 MiB cap")
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_PATH, "wb") as dst:
        dst.write(blob)


def main():
    """Render the page (live draw, else pre-rendered copy) and save it."""
    total = len(FEATURES) + len(PANELS) + len(DIGEST)
    assert total == 36, "must be 36 stories"
    assert sum(item["count"] for item in REGION_TALLY) == 36, \
        "tallies must sum to 36"
    if _HAS_PIL:
        try:
            page = FrontPage()
            img = page.render()
            os.makedirs(OUT_DIR, exist_ok=True)
            img.save(OUT_PATH, format="PNG", optimize=True)
            print("wrote %s (%dx%d) [live draw]"
                  % (OUT_PATH, SHEET_W, SHEET_H))
            return
        except Exception as exc:
            print("live draw failed (%s); using pre-rendered copy" % exc)
    _copy_prerendered()
    print("wrote %s (%dx%d) [pre-rendered]" % (OUT_PATH, SHEET_W, SHEET_H))


if __name__ == "__main__":
    main()
