"""
Splash-Engine - 1:1-Portierung von splash-sequenz.tsx nach Python.

Gleiche Aufloesung (320x180), gleiche Paletten, gleiches 8x8-Bayer-Dithering,
gleiche Pixelschriften, gleicher Zufallsgenerator (mulberry32, gegen die
JS-Fassung geprueft). Gezeichnet wird in einen Bytepuffer, der pro Bild einmal
zu einer pygame-Surface wird.

Dieses Modul zeichnet nur. Ablauf, Ton und Fensterausgabe stehen in
rustfront_splash.py.
"""

from __future__ import annotations

import math

import pygame

# ═════════════ Grundmasse ═════════════
W, H, CX, CY = 320, 180, 160, 64
A_LEN, C_LEN, T_LEN, S_LEN, B_LEN = 11.0, 3.4, 4.6, 4.0, 6.6
ORDER = ("a", "c", "t", "s", "b")
LENS = {"a": A_LEN, "c": C_LEN, "t": T_LEN, "s": S_LEN, "b": B_LEN}

TL = {
    "flash": (0.38, 0.55), "star": (0.42, 0.55), "orbits": (1.0, 0.75),
    "bezel": (1.85, 0.95), "wings": (2.6, 0.5), "mount": (3.35, 0.4),
    "title": (3.75, 0.4), "rule": (4.55, 0.45), "quote": (4.85, 0.45),
    "micro": (6.55, 0.7),
}
B = {"ax": 52, "ay": 96, "aR": 22, "tx": 88, "trg": 296, "barIn": 0.15, "barDur": 1.45}
SCHOCK = 3.55        # Kartenzeit, an der der zweite Teil des Spruchs einschlaegt
C = {"my": 54, "gap": 15, "sw": 24, "sh": 12, "th": 4, "ox": 9}


# ═════════════ Paletten ═════════════
def hx(h):
    return bytes((int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)))


def RA(lst):
    return [hx(h) for h in lst]


STEEL = RA(["#0a0f16", "#131b26", "#1d2836", "#293748", "#38495d",
            "#4b5f75", "#64788e", "#8199ad", "#a6bccd", "#d4e6f2"])
GOLD = RA(["#2b1e0a", "#4a3411", "#6d4c19", "#915f1f", "#b47c2a",
           "#d19a3b", "#e6b855", "#f5d47e", "#ffeab4"])
SILVER = RA(["#101720", "#1b2531", "#2b3a49", "#3f5265", "#586e83",
             "#7590a5", "#98b2c4", "#c0d5e3", "#eaf5fd"])
CYAN = RA(["#0b2430", "#124152", "#1a6379", "#2489a5", "#35b0cc",
           "#5fd3e8", "#96eaf7", "#cdf8ff", "#ffffff"])
EMBER = RA(["#2b0d08", "#4d1a0c", "#7a2a10", "#a84318", "#d06526",
            "#e88f3e", "#f6b96a", "#ffdca6", "#ffffff"])
VOIDR = RA(["#04060a", "#06090f", "#080d15", "#0b121c", "#0f1826"])
VOIDW = RA(["#04060a", "#06090f", "#0a0e14", "#10151c", "#171e28"])
VOIDE = RA(["#06060a", "#0b080d", "#100b11", "#160f15", "#1d141a"])
SCHEMES = {
    "aurum": (GOLD, CYAN, VOIDR),
    "glacies": (SILVER, CYAN, VOIDW),
    "ignis": (GOLD, EMBER, VOIDE),
}

P_PAPER, P_INK, P_INKD = [hx("#e9e5db")], [hx("#17171c")], [hx("#0a0a0e")]
P_COB, P_COBD, P_GREY = [hx("#2b4ede")], [hx("#1a2f96")], [hx("#8b887f")]
PHOS = RA(["#050b07", "#0a1a0e", "#0f2e18", "#164a26", "#1e7036",
           "#2a9c4a", "#3fc766", "#77e598", "#c9ffd9"])
S_PAPER, S_INK, S_OX = [hx("#d8c8a2")], [hx("#201d33")], [hx("#ad3a24")]

B8 = [(v + 0.5) / 64 for v in [
    0, 32, 8, 40, 2, 34, 10, 42, 48, 16, 56, 24, 50, 18, 58, 26,
    12, 44, 4, 36, 14, 46, 6, 38, 60, 28, 52, 20, 62, 30, 54, 22,
    3, 35, 11, 43, 1, 33, 9, 41, 51, 19, 59, 27, 49, 17, 57, 25,
    15, 47, 7, 39, 13, 45, 5, 37, 63, 31, 55, 23, 61, 29, 53, 21]]

# ═════════════ Tabellen ═════════════
VANES = [(-0.345, 56, 6.4), (-0.15, 66, 5.9), (0.055, 62, 5.2),
         (0.26, 52, 4.4), (0.47, 41, 3.5)]
R_ROOT = 34
RINGS = [(26.5, 1.16, 0.34, 0.21, False, 0.0),
         (20.0, 0.58, -0.92, -0.3, False, 2.1),
         (13.5, 1.34, 0.88, 0.43, True, 4.2)]
CPTS = [(30, 47), (68, 30), (112, 42), (131, 58), (156, 25), (199, 37),
        (241, 27), (288, 45)]
CEDGE = [(0, 1), (1, 2), (2, 4), (4, 5), (5, 6), (6, 7), (2, 3)]
CBRIGHT = (1, 4, 6)

_M32 = 0xFFFFFFFF


def mulberry32(seed):
    a = seed & _M32

    def rnd():
        nonlocal a
        a = (a + 0x6D2B79F5) & _M32
        t = ((a ^ (a >> 15)) * (1 | a)) & _M32
        t = (((t + (((t ^ (t >> 7)) * (61 | t)) & _M32)) & _M32) ^ t) & _M32
        return ((t ^ (t >> 14)) & _M32) / 4294967296.0
    return rnd


def _build_stars():
    r = mulberry32(20260725)
    out = []
    for _ in range(96):
        b = r()
        out.append((int(r() * W), int(r() * H),
                    8 if b > 0.94 else 6 if b > 0.76 else 4 if b > 0.44 else 2.4,
                    r() * math.pi * 2, 0.6 + r() * 1.9, r() > 0.88))
    return out


STARS = _build_stars()
NOISE = (lambda r: [r() for _ in range(W * H)])(mulberry32(77123))
RAYS = (lambda r: [((i * math.pi) / 6 + (r() - 0.5) * 0.17, 10 + r() * 9,
                    2.1 + r() * 2.3) for i in range(12)])(mulberry32(4711))


def clamp(v, a, b):
    return a if v < a else b if v > b else v


def seg(t, s, dur):
    return clamp((t - s) / dur, 0, 1)


def eOut(p):
    return 1 - (1 - p) ** 3


def eOut2(p):
    return 1 - (1 - p) ** 2


def smooth(p):
    return p * p * (3 - 2 * p)


def jround(v):
    return math.floor(v + 0.5)


fadeA = lambda t: clamp(t / 0.7, 0, 1) * (1 - clamp((t - 9.7) / 0.9, 0, 1))
fadeB = lambda t: clamp(t / 0.22, 0, 1) * (1 - clamp((t - 5.6) / 0.8, 0, 1))
fadeC = lambda t: 1 - clamp((t - 3.0) / 0.35, 0, 1)
fadeS = lambda t: 1 - clamp((t - 3.6) / 0.4, 0, 1)

# ═════════════ Pixelschriften (aus dem Original uebernommen) ═════════════
F7G = {
    "A": ".#####.|#######|##...##|##...##|##...##|#######|#######|##...##|##...##|##...##|##...##",
    "B": "######.|#######|##...##|##...##|##..##.|######.|######.|##..##.|##...##|#######|######.",
    "C": ".#####.|#######|##...##|##.....|##.....|##.....|##.....|##.....|##...##|#######|.#####.",
    "D": "######.|#######|##...##|##...##|##...##|##...##|##...##|##...##|##...##|#######|######.",
    "E": "#######|#######|##.....|##.....|##.....|######.|######.|##.....|##.....|#######|#######",
    "F": "#######|#######|##.....|##.....|##.....|######.|######.|##.....|##.....|##.....|##.....",
    "G": ".#####.|#######|##...##|##.....|##.....|##.####|##.####|##...##|##...##|#######|.#####.",
    "H": "##...##|##...##|##...##|##...##|##...##|#######|#######|##...##|##...##|##...##|##...##",
    "I": "#######|#######|..###..|..###..|..###..|..###..|..###..|..###..|..###..|#######|#######",
    "J": "..#####|..#####|.....##|.....##|.....##|.....##|.....##|##...##|##...##|#######|.#####.",
    "K": "##...##|##..##.|##.##..|####...|###....|###....|####...|##.##..|##..##.|##...##|##...##",
    "L": "##.....|##.....|##.....|##.....|##.....|##.....|##.....|##.....|##.....|#######|#######",
    "M": "##...##|###.###|#######|#######|##.#.##|##.#.##|##...##|##...##|##...##|##...##|##...##",
    "N": "##...##|###..##|###..##|####.##|####.##|##.####|##.####|##..###|##..###|##...##|##...##",
    "O": ".#####.|#######|##...##|##...##|##...##|##...##|##...##|##...##|##...##|#######|.#####.",
    "P": "######.|#######|##...##|##...##|##...##|#######|######.|##.....|##.....|##.....|##.....",
    "Q": ".#####.|#######|##...##|##...##|##...##|##...##|##...##|##.#.##|##..###|#######|.######",
    "R": "######.|#######|##...##|##...##|##...##|#######|######.|##.##..|##..##.|##...##|##...##",
    "S": ".#####.|#######|##...##|##.....|###....|.#####.|....###|.....##|##...##|#######|.#####.",
    "T": "#######|#######|..###..|..###..|..###..|..###..|..###..|..###..|..###..|..###..|..###..",
    "U": "##...##|##...##|##...##|##...##|##...##|##...##|##...##|##...##|##...##|#######|.#####.",
    "V": "##...##|##...##|##...##|##...##|##...##|##...##|.##.##.|.##.##.|.##.##.|..###..|...#...",
    "W": "##...##|##...##|##...##|##...##|##...##|##...##|##.#.##|##.#.##|##.#.##|#######|.##.##.",
    "X": "##...##|##...##|.##.##.|.##.##.|..###..|..###..|..###..|.##.##.|.##.##.|##...##|##...##",
    "Y": "##...##|##...##|.##.##.|.##.##.|..###..|..###..|..###..|..###..|..###..|..###..|..###..",
    "Z": "#######|#######|....##.|....##.|...##..|..##...|..##...|.##....|##.....|#######|#######",
    "0": ".#####.|#######|##...##|##..###|##.####|#######|####.##|###..##|##...##|#######|.#####.",
    "1": "..###..|.####..|..###..|..###..|..###..|..###..|..###..|..###..|..###..|.#####.|.#####.",
    "2": ".#####.|#######|##...##|.....##|....##.|...##..|..##...|.##....|##.....|#######|#######",
    "3": ".#####.|#######|##...##|.....##|..####.|..####.|.....##|.....##|##...##|#######|.#####.",
    "4": "....##.|...###.|..####.|.##.##.|##..##.|#######|#######|....##.|....##.|....##.|....##.",
    "5": "#######|#######|##.....|##.....|######.|#######|.....##|.....##|##...##|#######|.#####.",
    "6": ".#####.|#######|##...##|##.....|######.|#######|##...##|##...##|##...##|#######|.#####.",
    "7": "#######|#######|.....##|....##.|...##..|...##..|..##...|..##...|.##....|.##....|.##....",
    "8": ".#####.|#######|##...##|##...##|.#####.|.#####.|##...##|##...##|##...##|#######|.#####.",
    "9": ".#####.|#######|##...##|##...##|##...##|#######|.######|.....##|##...##|#######|.#####.",
    " ": ".......|.......|.......|.......|.......|.......|.......|.......|.......|.......|.......",
    ".": ".......|.......|.......|.......|.......|.......|.......|.......|.......|..##...|..##...",
    "-": ".......|.......|.......|.......|.......|.#####.|.#####.|.......|.......|.......|.......",
    "'": "..##...|..##...|..##...|.......|.......|.......|.......|.......|.......|.......|.......",
    ":": ".......|.......|..##...|..##...|.......|.......|.......|..##...|..##...|.......|.......",
    "\u00b7": ".......|.......|.......|.......|.......|..##...|..##...|.......|.......|.......|.......",
    "/": ".....##|.....##|....##.|....##.|...##..|...##..|..##...|..##...|.##....|.##....|.##....",
}
F5G = {
    "A": ".###.|#...#|#...#|#####|#...#|#...#|#...#", "B": "####.|#...#|#...#|####.|#...#|#...#|####.",
    "C": ".###.|#...#|#....|#....|#....|#...#|.###.", "D": "####.|#...#|#...#|#...#|#...#|#...#|####.",
    "E": "#####|#....|#....|####.|#....|#....|#####", "F": "#####|#....|#....|####.|#....|#....|#....",
    "G": ".###.|#...#|#....|#.###|#...#|#...#|.###.", "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    "I": "#####|..#..|..#..|..#..|..#..|..#..|#####", "J": "..###|...#.|...#.|...#.|...#.|#..#.|.##..",
    "K": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#", "L": "#....|#....|#....|#....|#....|#....|#####",
    "M": "#...#|##.##|#.#.#|#...#|#...#|#...#|#...#", "N": "#...#|##..#|#.#.#|#..##|#...#|#...#|#...#",
    "O": ".###.|#...#|#...#|#...#|#...#|#...#|.###.", "P": "####.|#...#|#...#|####.|#....|#....|#....",
    "Q": ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#", "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    "S": ".####|#....|#....|.###.|....#|....#|####.", "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    "U": "#...#|#...#|#...#|#...#|#...#|#...#|.###.", "V": "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    "W": "#...#|#...#|#...#|#...#|#.#.#|##.##|#...#", "X": "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..", "Z": "#####|....#|...#.|..#..|.#...|#....|#####",
    "0": ".###.|#..##|#.#.#|#.#.#|##..#|#...#|.###.", "1": "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
    "2": ".###.|#...#|....#|...#.|..#..|.#...|#####", "3": "#####|...#.|..#..|...#.|....#|#...#|.###.",
    "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.", "5": "#####|#....|####.|....#|....#|#...#|.###.",
    "6": "..##.|.#...|#....|####.|#...#|#...#|.###.", "7": "#####|....#|...#.|..#..|.#...|.#...|.#...",
    "8": ".###.|#...#|#...#|.###.|#...#|#...#|.###.", "9": ".###.|#...#|#...#|.####|....#|...#.|.##..",
    " ": ".....|.....|.....|.....|.....|.....|.....", ".": ".....|.....|.....|.....|.....|.##..|.##..",
    ",": ".....|.....|.....|.....|.##..|.##..|.#...", "'": "..#..|..#..|.....|.....|.....|.....|.....",
    "-": ".....|.....|.....|.###.|.....|.....|.....", ":": ".....|.##..|.##..|.....|.##..|.##..|.....",
    "\u00b7": ".....|.....|.....|.##..|.##..|.....|.....", "/": "....#|....#|...#.|..#..|.#...|#....|#....",
    "!": "..#..|..#..|..#..|..#..|..#..|.....|..#..", "?": ".###.|#...#|....#|..##.|..#..|.....|..#..",
    "(": "...#.|..#..|.#...|.#...|.#...|..#..|...#.", ")": ".#...|..#..|...#.|...#.|...#.|..#..|.#...",
    "&": ".##..|#..#.|#.#..|.#...|#.#.#|#..#.|.##.#", "+": ".....|..#..|..#..|#####|..#..|..#..|.....",
    ">": "#....|.#...|..#..|...#.|..#..|.#...|#....", "<": "....#|...#.|..#..|.#...|..#..|...#.|....#",
    "=": ".....|.....|#####|.....|#####|.....|.....", "*": ".....|#.#.#|.###.|#####|.###.|#.#.#|.....",
    "[": ".###.|.#...|.#...|.#...|.#...|.#...|.###.", "]": ".###.|...#.|...#.|...#.|...#.|...#.|.###.",
}


class Font:
    def __init__(self, table, w, h):
        self.w, self.h = w, h
        self.g = {k: v.split("|") for k, v in table.items()}


F7, F5 = Font(F7G, 7, 11), Font(F5G, 5, 7)


def clean(s: str) -> str:
    return (s.upper().replace("\u00c4", "AE").replace("\u00d6", "OE")
            .replace("\u00dc", "UE").replace("\u00df", "SS"))


# ═════════════ Engine ═════════════
class Engine:
    def __init__(self, scheme="aurum", opts=None):
        self.buf = bytearray(W * H * 3)
        self.snap = bytearray(W * H * 3)
        self.scan = False
        self.gx = 0
        self.gy = 0
        self.last_motto_w = 200
        self.bgc = {}
        self.scheme_key = scheme
        self.ACC, self.ENG, self.BG = SCHEMES.get(scheme, SCHEMES["aurum"])
        self.opts = {
            "name": "DUSTFRONT",
            "version": "VERSION 0.0.0 \u00b7 PRE-ALPHA",
            "sub": "EIN UNABHAENGIGES STUDIO \u00b7 MMXXVI",
            "role": "UNABHAENGIGE SPIELENTWICKLUNG",
            "schlag1": "IN THE GRIM DARKNESS OF THE FAR FUTURE,",
            "schlag2": "THERE IS ONLY WAR",
            "pname": "KALTWERK", "peyebrow": "POWERED BY",
            "psub": "ECHTZEIT-RENDERING & AUDIO",
            "tname": "PHOSPHOR", "tsub": "RUNTIME READY",
            "sname": "PAPIERMOND", "ssub": "ERZAEHLUNG & KUNSTRICHTUNG",
        }
        if opts:
            self.opts.update({k: clean(v) for k, v in opts.items() if v is not None})
        self.surface = pygame.Surface((W, H))

    # ───── Grundoperationen ─────
    def plot(self, x, y, ramp, lvl, a=1.0):
        x = int(x)
        y = int(y)
        if x < 0 or y < 0 or x >= W or y >= H or a <= 0:
            return
        if self.scan and (y & 1):
            lvl -= 2.1
        if a < 1 and B8[(((y + 3) & 7) << 3) + ((x + 5) & 7)] >= a:
            return
        li = math.floor(lvl)
        f = lvl - li
        if f > 0 and B8[((y & 7) << 3) + (x & 7)] < f:
            li += 1
        if li < 0:
            li = 0
        m = len(ramp) - 1
        if li > m:
            li = m
        o = (y * W + x) * 3
        self.buf[o:o + 3] = ramp[li]

    def fill(self, color: bytes):
        self.buf[:] = color * (W * H)

    def line(self, x0, y0, x1, y1, ramp, lvl, a=1.0, clip=None, dash=0):
        x0, y0, x1, y1 = jround(x0), jround(y0), jround(x1), jround(y1)
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        n = 0
        callable_lvl = callable(lvl)
        while True:
            if (not dash or n % dash < max(1, dash - 1)) and (not clip or clip(x0, y0)):
                self.plot(x0, y0, ramp, lvl(x0, y0) if callable_lvl else lvl, a)
            if x0 == x1 and y0 == y1:
                break
            e2 = err << 1
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy
            n += 1

    def poly(self, pts, ramp, lvl, a=1.0, clip=None):
        mn = min(p[1] for p in pts)
        mx = max(p[1] for p in pts)
        y0 = max(0, math.floor(mn))
        y1 = min(H - 1, math.ceil(mx))
        callable_lvl = callable(lvl)
        n = len(pts)
        for y in range(y0, y1 + 1):
            yc = y + 0.5
            xs = []
            for i in range(n):
                p = pts[i]
                q = pts[(i + 1) % n]
                if (p[1] <= yc < q[1]) or (q[1] <= yc < p[1]):
                    xs.append(p[0] + ((yc - p[1]) / (q[1] - p[1])) * (q[0] - p[0]))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                xa = max(0, jround(xs[i]))
                xb = min(W - 1, jround(xs[i + 1]))
                for x in range(xa, xb + 1):
                    if clip and not clip(x, y):
                        continue
                    self.plot(x, y, ramp, lvl(x, y) if callable_lvl else lvl, a)

    def disc(self, cx, cy, r, ramp, lvl, a=1.0):
        callable_lvl = callable(lvl)
        for y in range(math.floor(cy - r), math.floor(cy + r) + 1):
            for x in range(math.floor(cx - r), math.floor(cx + r) + 1):
                dd = math.hypot(x - cx, y - cy)
                if dd > r:
                    continue
                self.plot(x, y, ramp, lvl(dd) if callable_lvl else lvl, a)

    @staticmethod
    def polar(cx, cy, r, a):
        return (cx + math.cos(a) * r, cy + math.sin(a) * r)

    def build_bg(self, kind):
        key = self.scheme_key + kind
        hit = self.bgc.get(key)
        if hit is not None:
            return hit
        save = self.buf
        self.buf = bytearray(W * H * 3)
        gx = B["ax"] if kind == "b" else CX
        gy = B["ay"] if kind == "b" else CY
        for y in range(H):
            for x in range(W):
                dx = x - gx
                dy = (y - gy) / 0.86
                l = 4.15 * math.exp(-(dx * dx + dy * dy) / (2 * 72 * 72))
                l += 0.55 * math.exp(-(((y - 150) / 46) ** 2))
                self.plot(x, y, self.BG, clamp(l, 0, 4), 1)
        out = bytes(self.buf)
        self.buf = save
        self.bgc[key] = out
        return out

    def shift(self, dx):
        """Ganzes Bild waagerecht versetzen, fuer kurze Einschlaege."""
        if not dx:
            return
        pad = b"\x00\x00\x00" * abs(dx)
        w3 = W * 3
        for y in range(H):
            o0 = y * w3
            row = bytes(self.buf[o0:o0 + w3])
            if dx > 0:
                self.buf[o0:o0 + w3] = pad + row[:w3 - len(pad)]
            else:
                self.buf[o0:o0 + w3] = row[len(pad):] + pad

    def draw_stars(self, t):
        plot = self.plot
        ACC, ST = self.ACC, STEEL
        for (sx, sy, sl, ph, sp, g) in STARS:
            tw = 0.78 + 0.22 * math.sin(t * sp + ph)
            plot(sx, sy, ACC if g else ST, sl * tw, 1)
            if sl > 7:
                plot(sx + 1, sy, ST, 2.5 * tw, 0.7)
                plot(sx - 1, sy, ST, 2.5 * tw, 0.7)
                plot(sx, sy + 1, ST, 2.5 * tw, 0.7)
                plot(sx, sy - 1, ST, 2.5 * tw, 0.7)

    # ───── Typografie ─────
    @staticmethod
    def text_width(f, s, tr):
        return len(s) * (f.w + 1 + tr) - (1 + tr)

    def glyph(self, f, ch, x, y, ramp, lvl, a, bevel=False, clip=None):
        g = f.g.get(ch) or f.g[" "]
        for r in range(f.h):
            row = g[r]
            for c in range(f.w):
                if row[c] != "#":
                    continue
                if clip and not clip(x + c, y + r):
                    continue
                L = lvl
                if bevel:
                    up = r > 0 and g[r - 1][c] == "#"
                    dn = r < f.h - 1 and g[r + 1][c] == "#"
                    if not up:
                        L = lvl + 2.2
                    elif not dn:
                        L = lvl - 2.6
                self.plot(x + c, y + r, ramp, L, a)

    def draw_text(self, f, s, x0, y, ramp, lvl, a, tr, per=None, bevel=False, clip=None):
        x = jround(x0)
        for i, ch in enumerate(s):
            m = per(i, ch, x) if per else None
            if not m or m[0] > 0:
                self.glyph(f, ch, x, y + (m[1] if m else 0), ramp,
                           lvl + (m[2] if m else 0), m[0] if m else a, bevel, clip)
            x += f.w + 1 + tr
        return self.text_width(f, s, tr)

    def draw_text_c(self, f, s, cc, y, ramp, lvl, a, tr, per=None, bevel=False, clip=None):
        return self.draw_text(f, s, cc - self.text_width(f, s, tr) / 2, y,
                              ramp, lvl, a, tr, per, bevel, clip)

    def fit_tracking(self, f, s, base, maxw):
        tr = base
        while tr > 0 and self.text_width(f, s, tr) > maxw:
            tr -= 1
        return tr

    # ═══════════ KARTE 1 - Siegel ═══════════
    @staticmethod
    def _outside(x, y):
        return math.hypot(x - CX, y - CY) >= 33.2

    def draw_wings(self, t):
        for s in range(2):
            sx = 1 if s == 0 else -1
            for i, (va, vL, vth) in enumerate(VANES):
                p = eOut(seg(t, TL["wings"][0] + i * 0.075, TL["wings"][1]))
                if p <= 0:
                    continue
                ext = R_ROOT + vL * (0.3 + 0.7 * p)
                ca, sa = math.cos(va), math.sin(va)
                bx, by = CX + sx * ca * R_ROOT, CY + sa * R_ROOT
                tx, ty = CX + sx * ca * ext, CY + sa * ext
                px, py, th = -sa * sx, ca, vth
                P = [(bx - px * th * 0.56, by - py * th * 0.56),
                     (tx - px * th * 0.15, ty - py * th * 0.15),
                     (tx + px * th * 0.11, ty + py * th * 0.11),
                     (bx + px * th * 0.44, by + py * th * 0.44)]
                nx, ny = -px, -py

                def lvl(x, y, bx=bx, by=by, nx=nx, ny=ny, th=th):
                    return 6.6 - 4.6 * clamp(((x - bx) * nx + (y - by) * ny) / (th * 0.95) + 0.55, 0, 1)

                self.poly(P, STEEL, lvl, p, self._outside)
                self.line(P[0][0], P[0][1], P[1][0], P[1][1], STEEL, 9, p, self._outside)
                self.line(P[3][0], P[3][1], P[2][0], P[2][1], STEEL, 1, p, self._outside)
                q = 0.94 * p
                self.line(bx - px * th * 0.1 + ca * sx * 4, by - py * th * 0.1 + sa * 4,
                          tx - px * th * 0.02 - ca * sx * 3, ty - py * th * 0.02 - sa * 3,
                          self.ACC, 5.6, q, self._outside)
                for k in range(2):
                    rr = R_ROOT + 9 + k * 11
                    if rr > ext - 4:
                        continue
                    self.plot(CX + sx * ca * rr - px * th * 0.28,
                              CY + sa * rr - py * th * 0.28, self.ACC, 7.4, q)

    def draw_bezel(self, t):
        p = eOut2(seg(t, TL["bezel"][0], TL["bezel"][1]))
        if p <= 0:
            return
        R0, R1, LIGHT, TAU = 33, 41, -2.35, math.pi * 2
        gl = ((t * 0.42) % 1) * TAU - math.pi
        plot = self.plot
        sqrt, atan2, cos, fabs = math.sqrt, math.atan2, math.cos, math.fabs
        pTAU = p * TAU
        for y in range(CY - R1 - 1, CY + R1 + 2):
            if y < 0 or y >= H:
                continue
            dy = y - CY
            for x in range(CX - R1 - 1, CX + R1 + 2):
                if x < 0 or x >= W:
                    continue
                dx = x - CX
                dd = sqrt(dx * dx + dy * dy)
                if dd < R0 - 0.5 or dd > R1 + 0.4:
                    continue
                ang = atan2(dy, dx)
                u = (ang + math.pi / 2) % TAU
                if u > pTAU:
                    continue
                ad = ((ang - gl + math.pi) % TAU) - math.pi
                sh = 0.5 + 0.5 * cos(ang - LIGHT) + max(0, 1 - fabs(ad) / 0.32) * 0.55
                if dd >= 39.0:
                    lvl = 2.4 + 5.6 * sh
                elif dd >= 37.4:
                    lvl = 0.7
                else:
                    sg = ((ang + math.pi) / TAU) * 14
                    fr = sg - math.floor(sg)
                    lvl = 0.6 if (fr < 0.055 or fr > 0.945) else 2.0 + 5.2 * sh
                    if dd < 34.3:
                        lvl = max(0.5, lvl - 3.2)
                plot(x, y, STEEL, clamp(lvl, 0, 9), 1)
        for k in range(48):
            u = k / 48
            if u > p:
                continue
            a = -math.pi / 2 + u * TAU
            ca, sa = math.cos(a), math.sin(a)
            major = (k % 6 == 0)
            fl = 1 - clamp((p - u) * 13, 0, 1)
            r0 = 26.5 if major else 29.2
            self.line(CX + ca * r0, CY + sa * r0, CX + ca * 32.2, CY + sa * 32.2,
                      self.ACC if major else STEEL,
                      6.2 + 2.4 * fl if major else 4.0 + 3.6 * fl, 1)
        if p > 0.98:
            for k in range(4):
                a = -math.pi / 2 + (k * math.pi) / 2
                self.disc(CX + math.cos(a) * 33.6, CY + math.sin(a) * 33.6, 1.7,
                          self.ACC, lambda dd: 7.4 - dd * 0.9, 1)

    @staticmethod
    def proj(R, tx, ry, a):
        x = math.cos(a) * R
        y = math.sin(a) * R
        y1 = y * math.cos(tx)
        z1 = y * math.sin(tx)
        return (x * math.cos(ry) + z1 * math.sin(ry), y1,
                ((-x * math.sin(ry) + z1 * math.cos(ry)) / R + 1) / 2)

    def draw_orbits(self, t):
        for i, (R, tx, ry, sp, e, o) in enumerate(RINGS):
            p = eOut(seg(t, TL["orbits"][0] + i * 0.17, TL["orbits"][1]))
            if p <= 0:
                continue
            ramp = self.ENG if e else self.ACC
            phase = o + t * sp
            N = math.ceil(R * 8)
            n = math.floor(N * p)
            span = len(ramp) - 3.2
            for k in range(n):
                q = self.proj(R, tx, ry, phase + (k / N) * math.pi * 2)
                self.plot(CX + q[0], CY + q[1], ramp, 1.6 + q[2] * span,
                          0.55 + 0.45 * q[2])
            if p > 0.97:
                na = phase + t * (0.9 + i * 0.25)
                for k in range(7):
                    q = self.proj(R, tx, ry, na - k * 0.055)
                    f = 1 - k / 7
                    self.plot(CX + q[0], CY + q[1], self.ENG,
                              3 + 5 * f * (0.4 + 0.6 * q[2]), f * 0.9)
                q = self.proj(R, tx, ry, na)
                self.plot(CX + q[0], CY + q[1], self.ENG, 8, 1)
                self.plot(CX + q[0] + 1, CY + q[1], self.ENG, 8, 0.85)

    def draw_star(self, t):
        p = eOut(seg(t, TL["star"][0], TL["star"][1]))
        if p <= 0:
            return
        s = p * (0.93 + 0.05 * math.sin(t * 2.3) + 0.03 * math.sin(t * 5.9))
        R = 17 * s
        ENG = self.ENG
        for y in range(math.floor(CY - R), math.floor(CY + R) + 1):
            if y < 0 or y >= H:
                continue
            for x in range(math.floor(CX - R), math.floor(CX + R) + 1):
                dd = math.hypot(x - CX, y - CY)
                if dd > R:
                    continue
                v = 1 - dd / R
                self.plot(x, y, ENG, 0.4 + v * 3.4, (v ** 2.1) * 0.95)
        L = 16 * s
        for ux, uy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            i = 1
            while i <= L:
                v = 1 - i / L
                th = jround(2.5 * (v ** 1.5))
                for j in range(-th, th + 1):
                    self.plot(CX + ux * i - uy * j, CY + uy * i + ux * j, ENG,
                              3.4 + 4.6 * v * (1 - abs(j) / (th + 1.4)), v ** 0.85)
                i += 1
        L2 = 7.5 * s
        for ux, uy in ((0.707, 0.707), (-0.707, 0.707), (0.707, -0.707), (-0.707, -0.707)):
            i = 1
            while i <= L2:
                v = 1 - i / L2
                self.plot(CX + ux * i, CY + uy * i, ENG, 3 + 4.5 * v, (v ** 0.9) * 0.8)
                i += 1
        self.disc(CX, CY, 3.3 * s, ENG, lambda dd: 8.4 - dd * 1.15, 1)

    def draw_flash(self, t):
        p = seg(t, TL["flash"][0], TL["flash"][1])
        if p <= 0 or p >= 1:
            return
        r = 2 + p * 62
        a = (1 - p) ** 2.2
        for y in range(math.floor(CY - r - 2), math.floor(CY + r + 3)):
            if y < 0 or y >= H:
                continue
            for x in range(math.floor(CX - r - 2), math.floor(CX + r + 3)):
                dd = math.hypot(x - CX, y - CY)
                if dd < r - 1.6 or dd > r + 1.2:
                    continue
                self.plot(x, y, self.ENG, 5 + 3 * a, a)

    def draw_mount(self, t):
        p = eOut(seg(t, TL["mount"][0], TL["mount"][1]))
        if p <= 0:
            return
        yTop, yBar, yBot = CY + 39, CY + 48, CY + 51
        for sx in (1, -1):
            self.poly([(CX + sx * 11.5, yTop), (CX + sx * 17.5, yTop),
                       (CX + sx * 22, yBar), (CX + sx * 17, yBar)],
                      STEEL, lambda x, y: 5.4 - (y - yTop) * 0.22, p)
        hw = jround(27 * p)
        for y in range(yBar, yBot + 1):
            l = 7.2 if y == yBar else 2.2 if y == yBot else 5.4
            for x in range(CX - hw, CX + hw + 1):
                self.plot(x, y, self.ACC, l, 1)
        if p > 0.85:
            for k in range(-2, 3):
                self.plot(CX + k * 7, yBar + 1, self.ENG, 7, 0.9 * p)

    def render_a(self, t):
        self.buf[:] = self.build_bg("a")
        self.draw_stars(t)
        self.draw_wings(t)
        self.draw_bezel(t)
        self.draw_orbits(t)
        self.draw_star(t)
        self.draw_flash(t)
        self.draw_mount(t)
        o = self.opts
        if o["name"]:
            def per(i, ch, x):
                p = eOut(seg(t, TL["title"][0] + i * 0.055, TL["title"][1]))
                return (p, jround((1 - p) * 4), (1 - p) * 1.6)
            self.draw_text_c(F7, o["name"], CX, CY + 56, self.ACC, 5.6, 1,
                             self.fit_tracking(F7, o["name"], 3, W - 24), per, True)
        rp = eOut(seg(t, TL["rule"][0], TL["rule"][1]))
        if rp > 0:
            y = CY + 74
            hw = min(self.last_motto_w / 2 + 11, 142) * rp
            for x in range(jround(CX - hw), jround(CX + hw) + 1):
                self.plot(x, y, STEEL, 1.6 + 3.4 * (1 - abs(x - CX) / (hw + 1)), 1)
            if rp > 0.9:
                for sx in (1, -1):
                    dx = CX + sx * jround(hw)
                    for a in range(-2, 3):
                        for b in range(-2, 3):
                            if abs(a) + abs(b) <= 2:
                                self.plot(dx + a, y + b, self.ACC, 6.8 - abs(a) * 0.7, 1)
        if o["version"]:
            tr = self.fit_tracking(F5, o["version"], 1, W - 20)

            def per_m(i, ch, x):
                p = seg(t, TL["quote"][0] + i * 0.02, TL["quote"][1])
                return (eOut(p), 0, (1 - p) * (0 if ch == " " else 2.4))
            self.draw_text_c(F5, o["version"], CX, CY + 80, STEEL, 8.6, 1, tr, per_m, False)
            self.last_motto_w = self.text_width(F5, o["version"], tr)
        if o["sub"]:
            p = eOut(seg(t, TL["micro"][0], TL["micro"][1]))
            if p > 0:
                self.draw_text_c(F5, o["sub"], CX, CY + 95, STEEL, 5.0, p,
                                 self.fit_tracking(F5, o["sub"], 2, W - 16), None, False)

    # ═══════════ KARTE 2 - Tafel ═══════════
    @staticmethod
    def bar_x(t):
        return smooth(seg(t, B["barIn"], B["barDur"])) * (W + 6) - 3

    def draw_plate(self):
        for x in range(10, 311):
            self.plot(x, 14, STEEL, 2.4, 1)
            self.plot(x, 170, STEEL, 2.0, 1)
        for x in range(10, 27):
            self.plot(x, 14, self.ACC, 6.4, 1)
            self.plot(x, 13, self.ACC, 3.2, 1)

    def draw_constellation(self, px):
        for (ia, ib) in CEDGE:
            a, b = CPTS[ia], CPTS[ib]
            xr = max(a[0], b[0])
            p = clamp((px - xr) / 16, 0, 1)
            if p <= 0:
                continue
            self.line(a[0], a[1], a[0] + (b[0] - a[0]) * p, a[1] + (b[1] - a[1]) * p,
                      STEEL, 3.2, 0.9, None, 3)
        for i, p in enumerate(CPTS):
            if px < p[0] + 2:
                continue
            big = i in CBRIGHT
            self.plot(p[0], p[1], self.ENG if big else self.ACC, 8 if big else 6.4, 1)
            if big:
                E = self.ENG
                self.plot(p[0] + 1, p[1], E, 4.5, 0.8)
                self.plot(p[0] - 1, p[1], E, 4.5, 0.8)
                self.plot(p[0], p[1] + 1, E, 4.5, 0.8)
                self.plot(p[0], p[1] - 1, E, 4.5, 0.8)
                self.plot(p[0] + 2, p[1], E, 2.5, 0.5)
                self.plot(p[0] - 2, p[1], E, 2.5, 0.5)

    def draw_aperture(self, t, px):
        LIGHT = -2.35
        R = B["aR"]
        Ri = R - 4.6
        ax, ay = B["ax"], B["ay"]
        open_ = eOut(clamp((px - (ax + R)) / 30, 0, 1))
        self.disc(ax, ay, Ri - 0.5, STEEL, lambda dd: 0.4, 1)
        if open_ > 0.15:
            gr = 13 * open_
            for y in range(math.floor(ay - gr), math.floor(ay + gr) + 1):
                for x in range(math.floor(ax - gr), math.floor(ax + gr) + 1):
                    dd = math.hypot(x - ax, y - ay)
                    if dd > gr:
                        continue
                    v = 1 - dd / gr
                    self.plot(x, y, self.ENG, 0.3 + v * 3.2, (v ** 2.3) * open_)
            for ux, uy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                i = 1
                while i <= 9 * open_:
                    v = 1 - i / (9 * open_)
                    self.plot(ax + ux * i, ay + uy * i, self.ENG, 3 + 4.5 * v,
                              (v ** 0.9) * open_)
                    i += 1
            self.disc(ax, ay, 2.2 * open_, self.ENG, lambda dd: 8.4 - dd * 1.2, 1)
        rTip = 1.2 + open_ * 14.6
        for i in range(6):
            phi = i * (math.pi / 3) + 0.2
            P = [self.polar(ax, ay, Ri, phi), self.polar(ax, ay, Ri, phi + 1.25),
                 self.polar(ax, ay, rTip, phi + 0.45)]
            sh = 0.5 + 0.5 * math.cos(phi + 0.6 - LIGHT)
            self.poly(P, STEEL, 1.4 + 4.2 * sh, 1)
            self.line(P[0][0], P[0][1], P[2][0], P[2][1], STEEL, 2.4 + 5.4 * sh, 1)
        for k in range(8):
            t0 = k * (math.pi / 4) + math.pi / 8
            t1 = t0 + math.pi / 4
            sh = 0.5 + 0.5 * math.cos(t0 + math.pi / 8 - LIGHT)
            self.poly([self.polar(ax, ay, R, t0), self.polar(ax, ay, R, t1),
                       self.polar(ax, ay, Ri, t1), self.polar(ax, ay, Ri, t0)],
                      STEEL, 2.0 + 5.6 * sh, 1)
            o0 = self.polar(ax, ay, R, t0)
            o1 = self.polar(ax, ay, R, t1)
            self.line(o0[0], o0[1], o1[0], o1[1], STEEL, 9 if sh > 0.55 else 1.2, 1)
            c = self.polar(ax, ay, R - 1.5, t0)
            self.plot(c[0], c[1], self.ACC, 6.8, 1)

    def draw_scale(self, t, px):
        y = 138
        for x in range(16, 297):
            if px > x:
                self.plot(x, y, STEEL, 2.2, 1)
        k = 0
        while k * 4 + 16 <= 296:
            x = 16 + k * 4
            if px >= x:
                h = 8 if k % 20 == 0 else 5 if k % 5 == 0 else 2
                ramp = self.ACC if k % 20 == 0 else STEEL
                for j in range(1, h + 1):
                    self.plot(x, y - j, ramp, 6.2 if k % 20 == 0 else 3.4 - j * 0.12, 1)
            k += 1
        cp = clamp((px - 300) / 30, 0, 1) * clamp(seg(t, 1.5, 0.6), 0, 1)
        if cp > 0:
            xc = jround(16 + 0.62 * 280 * cp + 16 * (1 - cp))
            for j in range(10):
                self.plot(xc, y - j, self.ENG, 7.4 - j * 0.35, 1)
            for j in range(3):
                self.plot(xc - 1 - j, y - 10 - j, self.ENG, 5.5, 1)
                self.plot(xc + 1 + j, y - 10 - j, self.ENG, 5.5, 1)

    def draw_word_b(self, t, px):
        o = self.opts
        if not o["name"]:
            return
        trk = self.fit_tracking(F7, o["name"], 5, B["trg"] - B["tx"])
        swp = seg(t, B["barIn"] + B["barDur"] + 0.05, 0.55)
        sx = B["tx"] - 20 + swp * (B["trg"] - B["tx"] + 46)

        def per(i, ch, x):
            dl = max(0, 1 - abs(x + 3 - sx) / 16) * 2.6 if 0 < swp < 1 else 0
            return (1, 0, dl)
        self.draw_text(F7, o["name"], B["tx"], 84, self.ACC, 5.6, 1, trk, per, True)
        for x in range(B["tx"], B["trg"] + 1):
            if px < x:
                continue
            self.plot(x, 100, STEEL, 0 if x < B["tx"] + 22 else 2.8, 1)
            if x < B["tx"] + 22:
                self.plot(x, 100, self.ACC, 6.6, 1)
        if o["role"]:
            self.draw_text(F5, o["role"], B["tx"], 105, STEEL, 6.2, 1,
                           self.fit_tracking(F5, o["role"], 1, B["trg"] - B["tx"]),
                           None, False)

    def render_b(self, t):
        self.buf[:] = self.build_bg("b")
        self.draw_stars(t + 4.3)
        self.snap[:] = self.buf
        px = self.bar_x(t)
        self.draw_plate()
        self.draw_constellation(px)
        self.draw_aperture(t, px)
        self.draw_word_b(t, px)
        self.draw_scale(t, px)
        if px < W:
            x0 = max(0, math.ceil(px))
            for y in range(H):
                o0 = (y * W + x0) * 3
                o1 = (y * W + W) * 3
                self.buf[o0:o1] = self.snap[o0:o1]
        if -2 < px < W + 2:
            xi = jround(px)
            for y in range(12, 173):
                self.plot(xi, y, self.ENG, 8, 1)
                self.plot(xi - 1, y, self.ENG, 5.5, 0.75)
                self.plot(xi - 2, y, self.ENG, 3.2, 0.45)
                self.plot(xi + 1, y, self.ENG, 2.6, 0.3)
        # Erster Teil blendet ruhig ein
        s1 = self.opts["schlag1"]
        if s1:
            p = eOut(seg(t, B["barIn"] + B["barDur"] + 0.3, 0.75))
            if p > 0:
                self.draw_text_c(F5, s1, CX, 140, STEEL, 5.4, p,
                                 self.fit_tracking(F5, s1, 1, W - 24), None, False)

        # Zweiter Teil schlaegt ohne Vorwarnung ein
        s2 = self.opts["schlag2"]
        k = t - SCHOCK
        if s2 and k >= 0:
            tr2 = self.fit_tracking(F7, s2, 3, W - 28)
            jit = 2 if (k < 0.16 and math.floor(t * 60) % 2 == 0) else 0
            lvl = 8.6 if k < 0.10 else 6.2
            self.draw_text_c(F7, s2, CX + jit, 155, self.ACC, lvl, 1, tr2, None, True)
            # Zwei Linien fahren aus der Mitte heraus
            hw = int(min(1.0, k / 0.10) * (self.text_width(F7, s2, tr2) / 2 + 8))
            for yy in (151, 169):
                for x in range(CX - hw, CX + hw + 1):
                    self.plot(x, yy, self.ACC, 7.2 if k < 0.14 else 4.4, 1)
            if k < 0.18:                     # kurzes Ruckeln, kein Stroboskop
                off = 2 if math.floor(k * 48) % 2 == 0 else -2
                self.shift(off)

    # ═══════════ KARTE III - Partnermarke ═══════════
    def slab(self, i, t):
        t0 = 0.1 + i * 0.14
        dur = 0.17
        p = seg(t, t0, dur)
        if p <= 0:
            return
        e = 1 - (1 - p) ** 4
        cx = CX + (i - 1) * C["ox"]
        cy = C["my"] + i * C["gap"] - 74 * (1 - e)
        ps = seg(t, t0 + dur, 0.11)
        k = math.sin(ps * math.pi) if 0 < ps < 1 else 0
        hw = C["sw"] * (1 + 0.1 * k)
        hh = C["sh"] * (1 - 0.2 * k)
        top = P_COB if i == 1 else P_INK
        side = P_COBD if i == 1 else P_INKD
        self.poly([(cx - hw, cy), (cx, cy + hh), (cx + hw, cy),
                   (cx + hw, cy + C["th"]), (cx, cy + hh + C["th"]),
                   (cx - hw, cy + C["th"])], side, 0, 1)
        self.poly([(cx - hw, cy), (cx, cy - hh), (cx + hw, cy), (cx, cy + hh)],
                  top, 0, 1)

    def render_c(self, t):
        self.fill(P_PAPER[0])
        for i in range(3):
            self.slab(i, t)
        o = self.opts
        if t > 0.7 and o["peyebrow"]:
            tr = 2
            w = self.text_width(F5, o["peyebrow"], tr)
            x0 = jround(CX - w / 2)
            for y in range(27, 38):
                for x in range(x0 - 6, x0 + w + 6):
                    self.plot(x, y, P_INK, 0, 1)
            self.draw_text(F5, o["peyebrow"], x0, 29, P_PAPER, 0, 1, tr, None, False)
        if o["pname"]:
            self.draw_text_c(F7, o["pname"], CX, 110, P_INK, 0, 1,
                             self.fit_tracking(F7, o["pname"], 1, W - 40),
                             lambda i, ch, x: (1 if t > 0.62 + i * 0.018 else 0, 0, 0),
                             False)
        if t > 0.8 and o["psub"]:
            self.draw_text_c(F5, o["psub"], CX, 128, P_GREY, 0, 1,
                             self.fit_tracking(F5, o["psub"], 2, W - 40), None, False)
        bw = smooth(seg(t, 0.86, 0.24)) * W
        for y in range(172, 178):
            for x in range(int(bw)):
                self.plot(x, y, P_COB, 0, 1)

    # ═══════════ KARTE IV - Phosphor ═══════════
    def warp(self, sc):
        self.snap[:] = self.buf
        self.buf[:] = b"\x00\x00\x00" * (W * H)
        yc = 90
        s = max(sc, 0.001)
        for y in range(H):
            sy = jround(yc + (y - yc) / s)
            if sy < 0 or sy >= H:
                continue
            self.buf[(y * W) * 3:((y + 1) * W) * 3] = \
                self.snap[(sy * W) * 3:((sy + 1) * W) * 3]
        if sc < 0.4:
            a = 1 - sc / 0.4
            for x in range(W):
                self.plot(x, yc, PHOS, 6 + 2.6 * a, 1)
                self.plot(x, yc - 1, PHOS, 4, 0.55 * a)
                self.plot(x, yc + 1, PHOS, 4, 0.55 * a)

    def bloom(self, f, s, cc, y, tr, base, glow):
        for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            self.draw_text_c(f, s, cc + ox, y + oy, PHOS, 2.6 + glow, 0.6, tr, None, False)
        for ox, oy in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
            self.draw_text_c(f, s, cc + ox, y + oy, PHOS, 1.8 + glow, 0.34, tr, None, False)
        self.draw_text_c(f, s, cc, y, PHOS, base, 1, tr, None, False)

    def block(self, x, y, ramp, lvl):
        for j in range(7):
            for i in range(5):
                self.plot(x + i, y + j, ramp, lvl, 1)

    def render_t(self, t):
        self.scan = True
        self.fill(PHOS[0])
        roll = ((t * 0.32) % 1) * (H + 44) - 22
        for y in range(math.floor(roll), math.floor(roll) + 16):
            if 0 <= y < H:
                for x in range(W):
                    self.plot(x, y, PHOS, 1.5, 0.45)
        nm = self.opts["tname"] or "PHOSPHOR"
        L = [(32, 0.42, "> MOUNT " + nm + ".RT"),
             (44, 1.05, "> LINK RENDER BUS ... OK"),
             (56, 1.58, "> HANDSHAKE ......... OK")]
        CPS = 30
        blink = math.floor(t * 3) % 2 == 0
        act, actN = -1, 0
        for i, (ly, t0, s) in enumerate(L):
            n = math.floor((t - t0) * CPS)
            if n <= 0:
                continue
            k = min(n, len(s))
            self.draw_text(F5, s[:k], 26, ly, PHOS, 5.4, 1, 1, None, False)
            if k < len(s) and act < 0:
                act, actN = i, k
        if act >= 0 and blink:
            self.block(26 + actN * 7, L[act][0], PHOS, 7)
        nt = 2.22
        if t > nt:
            for x in range(26, 295):
                if (x & 3) != 3:
                    self.plot(x, 72, PHOS, 3.4, 1)
            fl = max(0, 1 - (t - nt) / 0.18)
            jit = 2 if (t < nt + 0.32 and math.floor(t * 42) % 4 == 0) else 0
            self.bloom(F7, nm, CX + jit, 84, 4, 7.0 + fl * 1.9, fl * 2.8)
        if t > nt + 0.4:
            s2 = self.opts["tsub"] or "RUNTIME READY"
            w = self.text_width(F5, s2, 2)
            self.draw_text_c(F5, s2, CX, 106, PHOS, 4.6, 1, 2, None, False)
            if blink:
                self.block(jround(CX + w / 2) + 5, 106, PHOS, 6.5)
        pOn = seg(t, 0.02, 0.26)
        pOff = seg(t, T_LEN - 0.42, 0.30)
        sc = 1.0
        if pOn < 1:
            sc = pOn ** 2.4
        if pOff > 0:
            sc = min(sc, (1 - pOff) ** 1.9)
        if sc < 0.999:
            self.warp(sc)
        self.scan = False

    # ═══════════ KARTE V - Handdruck ═══════════
    @staticmethod
    def grain(dens):
        return lambda x, y: (0 <= x < W and 0 <= y < H and NOISE[y * W + x] < dens)

    def ink(self, x, y, ramp, dens):
        px = int(x + self.gx)
        py = int(y + self.gy)
        if px < 0 or py < 0 or px >= W or py >= H:
            return
        if NOISE[py * W + px] > dens:
            return
        self.plot(px, py, ramp, 0, 1)

    def plate(self, ramp):
        x0, x1, y0, y1 = 9, 310, 9, 170
        for x in range(x0, x1 + 1):
            w = jround(math.sin(x * 0.11) * 1.2 + math.sin(x * 0.27 + 2) * 0.8)
            self.ink(x, y0 + w, ramp, 0.88)
            self.ink(x, y0 + w + 1, ramp, 0.68)
            self.ink(x, y1 - w, ramp, 0.88)
            self.ink(x, y1 - w - 1, ramp, 0.68)
        for y in range(y0, y1 + 1):
            w = jround(math.sin(y * 0.13) * 1.2 + math.sin(y * 0.29 + 1) * 0.8)
            self.ink(x0 + w, y, ramp, 0.88)
            self.ink(x0 + w + 1, y, ramp, 0.68)
            self.ink(x1 - w, y, ramp, 0.88)
            self.ink(x1 - w - 1, y, ramp, 0.68)

    def eclipse(self, cx, cy, R, ramp):
        for y in range(math.floor(cy - R - 4), math.floor(cy + R + 5)):
            for x in range(math.floor(cx - R - 4), math.floor(cx + R + 5)):
                dx, dy = x - cx, y - cy
                dd = math.hypot(dx, dy)
                if dd > R + 3:
                    continue
                ang = math.atan2(dy, dx)
                rr = R + 1.5 * math.sin(ang * 7 + 1.2) + 1.0 * math.sin(ang * 11 - 0.4)
                if dd > rr:
                    continue
                if math.hypot(dx + R * 0.30, dy + R * 0.24) < R * 0.74:
                    continue
                self.ink(x, y, ramp, 0.30 + 0.64 * clamp((rr - dd) / 2.6, 0, 1))

    def rays(self, cx, cy, R, ramp):
        for (ra, rL, rw) in RAYS:
            ca, sa = math.cos(ra), math.sin(ra)
            bx, by = cx + ca * (R + 3), cy + sa * (R + 3)
            tx, ty = cx + ca * (R + 3 + rL), cy + sa * (R + 3 + rL)
            self.poly([(bx - sa * rw + self.gx, by + ca * rw + self.gy),
                       (bx + sa * rw + self.gx, by - ca * rw + self.gy),
                       (tx + self.gx, ty + self.gy)], ramp, 0, 1, self.grain(0.86))

    def wobble(self, x0, x1, y, ramp):
        for x in range(x0, x1 + 1):
            w = jround(math.sin(x * 0.09) * 1.1 + math.sin(x * 0.23 + 1) * 0.7)
            self.ink(x, y + w, ramp, 0.9)
            self.ink(x, y + w + 1, ramp, 0.72)

    def reg_mark(self, cx, cy, ramp):
        for a in range(72):
            th = (a / 72) * math.pi * 2
            self.ink(cx + math.cos(th) * 4.2, cy + math.sin(th) * 4.2, ramp, 0.92)
        for i in range(-6, 7):
            self.ink(cx + i, cy, ramp, 0.92)
            self.ink(cx, cy + i, ramp, 0.92)

    def render_s(self, t):
        self.fill(S_PAPER[0])
        rise = jround((1 - eOut(seg(t, 0, 0.24))) * 6)
        sh = 0
        if 0.30 <= t < 0.345:
            sh = 2
        elif 0.345 <= t < 0.385:
            sh = -1
        elif 0.78 <= t < 0.815:
            sh = 1
        self.gx = 0
        self.gy = rise + sh
        isc = 0 if t < 0.30 else (1.12 - ((t - 0.30) / 0.07) * 0.12) if t < 0.37 else 1
        if isc > 0:
            self.plate(S_INK)
            self.eclipse(CX, 66, 22 * isc, S_INK)
        rp = eOut(seg(t, 0.52, 0.18))
        if rp > 0:
            sgx, sgy = self.gx, self.gy
            self.gx += jround(-5 + 7 * rp)
            self.gy += jround(-3 + 4 * rp)
            self.rays(CX, 66, 22, S_OX)
            self.wobble(96, 224, 130, S_OX)
            self.gx, self.gy = sgx, sgy
        o = self.opts
        if t > 0.78 and o["sname"]:
            self.draw_text_c(F7, o["sname"], CX + self.gx, 114 + self.gy, S_INK, 0, 1,
                             self.fit_tracking(F7, o["sname"], 3, W - 50), None, False,
                             self.grain(0.91))
        if t > 1.02 and o["ssub"]:
            self.draw_text_c(F5, o["ssub"], CX + self.gx, 137 + self.gy, S_INK, 0, 1,
                             self.fit_tracking(F5, o["ssub"], 2, W - 50), None, False,
                             self.grain(0.88))
        if t > 1.16:
            self.reg_mark(292, 158, S_OX)
        self.gx = 0
        self.gy = 0

    # ───── Bild-Dispatch ─────
    def frame(self, key, t):
        self.scan = False
        if key == "a":
            self.render_a(t)
            a = fadeA(t)
        elif key == "c":
            self.render_c(t)
            a = fadeC(t)
        elif key == "t":
            self.render_t(t)
            a = 1.0
        elif key == "s":
            self.render_s(t)
            a = fadeS(t)
        else:
            self.render_b(t)
            a = fadeB(t)
        img = pygame.image.frombuffer(bytes(self.buf), (W, H), "RGB")
        self.surface.blit(img, (0, 0))
        return self.surface, clamp(a, 0, 1)
