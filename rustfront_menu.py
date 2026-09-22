"""
RUSTFRONT - Hauptmenue
======================

Vollstaendiges, spielfertiges Hauptmenue für pygame-ce (getestet mit 2.5.8,
Python 3.10 - 3.14). Keine externen Dateien noetig: Schrift, Grafik und Ton
werden zur Laufzeit erzeugt.

Start:
    pip install pygame-ce
    python rustfront_menu.py            # mit Splash-Sequenz
    python rustfront_menu.py --nosplash  # ohne

Dateien:
    rustfront_menu.py     dieses Menue
    rustfront_splash.py   Ablauf und Ton der Splash-Sequenz
    splash_engine.py      Zeichenwerk der Splash-Sequenz

Liegen die beiden Splash-Dateien daneben, laeuft die Sequenz automatisch vor
dem Menue. Fehlen sie, startet das Menue einfach direkt.

Einbinden ins Spiel:
    from rustfront_menu import run_menu
    ergebnis = run_menu()      # {"action": "new_game"/"continue"/"quit", ...}

Steuerung:
    Pfeile / W S      Auswahl
    Links / Rechts    Wert ändern
    Enter / Leer      Bestaetigen
    Esc               Zurück
    F11               Vollbild
    Maus              Hovern, Klicken, Schieberegler ziehen, Rad scrollen

Dateien, die das Menue anlegt (neben dieser .py-Datei):
    rustfront_settings.json   Einstellungen
    rustfront_save.json       Demo-Spielstand (aktiviert FORTSETZEN)
"""

from __future__ import annotations

import array
import json
import math
import os
import random
import sys
import time
from pathlib import Path

import pygame

# --------------------------------------------------------------------------
# Grundwerte
# --------------------------------------------------------------------------

SPIEL_TITEL = "DUSTFRONT"         # <- hier den Spielnamen ändern
# Versionsnummer nach dem Schema in der README: MAJOR.MINOR.PATCH
#   MINOR +1  etwas Neues kam dazu      PATCH +1  nur repariert oder justiert
#   1.0.0     erstmals von vorn bis hinten spielbar
VERSION = "0.19.1"
PHASE = "PRE-ALPHA"        # PRE-ALPHA | ALPHA | BETA | RELEASE

VW, VH = 480, 270                  # virtuelle Aufloesung (alles wird hochskaliert)
START_FENSTER = (1152, 648)

try:
    BASE_DIR = Path(__file__).resolve().parent
except NameError:                  # interaktiv gestartet
    BASE_DIR = Path.cwd()
SETTINGS_PATH = BASE_DIR / "rustfront_settings.json"
SAVE_PATH = BASE_DIR / "rustfront_save.json"

# --------------------------------------------------------------------------
# Palette (uebernommen aus den Mockups V2)
# --------------------------------------------------------------------------

C_VOID = (9, 6, 5)
C_GROUND = (33, 23, 16)
C_GROUND_DK = (23, 15, 11)
C_GROUND_LT = (46, 33, 23)
C_PANEL = (14, 10, 8)
C_LINE = (74, 52, 34)
C_LINE_DK = (46, 32, 21)
C_AMBER = (232, 163, 61)
C_AMBER_LT = (250, 208, 133)
C_ORANGE = (226, 98, 47)
C_RUST = (150, 60, 30)
C_TEAL = (63, 210, 192)
C_TEAL_DK = (28, 96, 90)
C_CREAM = (238, 226, 203)
C_MUTED = (131, 108, 82)
C_MUTED_DK = (84, 66, 49)
C_RED = (203, 62, 42)
C_HULL = (170, 152, 112)
C_HULL_DK = (108, 94, 66)
C_HULL_SH = (58, 47, 32)

FRAKTIONSFARBE = {"KOLONNE": C_ORANGE, "CHOR": C_TEAL, "WERFTEN": C_AMBER}

# --------------------------------------------------------------------------
# Bitmap-Schrift 5x7, komplett im Code
# --------------------------------------------------------------------------

_GLYPHS = {
    "A": "01110/10001/10001/11111/10001/10001/10001",
    "B": "11110/10001/10001/11110/10001/10001/11110",
    "C": "01110/10001/10000/10000/10000/10001/01110",
    "D": "11110/10001/10001/10001/10001/10001/11110",
    "E": "11111/10000/10000/11110/10000/10000/11111",
    "F": "11111/10000/10000/11110/10000/10000/10000",
    "G": "01110/10001/10000/10111/10001/10001/01111",
    "H": "10001/10001/10001/11111/10001/10001/10001",
    "I": "11111/00100/00100/00100/00100/00100/11111",
    "J": "00111/00010/00010/00010/00010/10010/01100",
    "K": "10001/10010/10100/11000/10100/10010/10001",
    "L": "10000/10000/10000/10000/10000/10000/11111",
    "M": "10001/11011/10101/10001/10001/10001/10001",
    "N": "10001/11001/10101/10011/10001/10001/10001",
    "O": "01110/10001/10001/10001/10001/10001/01110",
    "P": "11110/10001/10001/11110/10000/10000/10000",
    "Q": "01110/10001/10001/10001/10101/10010/01101",
    "R": "11110/10001/10001/11110/10100/10010/10001",
    "S": "01111/10000/10000/01110/00001/00001/11110",
    "T": "11111/00100/00100/00100/00100/00100/00100",
    "U": "10001/10001/10001/10001/10001/10001/01110",
    "V": "10001/10001/10001/10001/10001/01010/00100",
    "W": "10001/10001/10001/10001/10101/11011/10001",
    "X": "10001/10001/01010/00100/01010/10001/10001",
    "Y": "10001/10001/01010/00100/00100/00100/00100",
    "Z": "11111/00001/00010/00100/01000/10000/11111",
    "0": "01110/10001/10011/10101/11001/10001/01110",
    "1": "00100/01100/00100/00100/00100/00100/01110",
    "2": "01110/10001/00001/00010/00100/01000/11111",
    "3": "11110/00001/00001/01110/00001/00001/11110",
    "4": "00010/00110/01010/10010/11111/00010/00010",
    "5": "11111/10000/11110/00001/00001/10001/01110",
    "6": "00110/01000/10000/11110/10001/10001/01110",
    "7": "11111/00001/00010/00100/01000/01000/01000",
    "8": "01110/10001/10001/01110/10001/10001/01110",
    "9": "01110/10001/10001/01111/00001/00010/01100",
    " ": "00000/00000/00000/00000/00000/00000/00000",
    ".": "00000/00000/00000/00000/00000/01100/01100",
    ",": "00000/00000/00000/00000/01100/01100/01000",
    ":": "00000/01100/01100/00000/01100/01100/00000",
    ";": "00000/01100/01100/00000/01100/00100/01000",
    "!": "00100/00100/00100/00100/00100/00000/00100",
    "?": "01110/10001/00001/00010/00100/00000/00100",
    "-": "00000/00000/00000/11111/00000/00000/00000",
    "_": "00000/00000/00000/00000/00000/00000/11111",
    "/": "00001/00001/00010/00100/01000/10000/10000",
    "\\": "10000/10000/01000/00100/00010/00001/00001",
    "(": "00110/01000/01000/01000/01000/01000/00110",
    ")": "01100/00010/00010/00010/00010/00010/01100",
    "[": "01110/01000/01000/01000/01000/01000/01110",
    "]": "01110/00010/00010/00010/00010/00010/01110",
    "<": "00010/00100/01000/10000/01000/00100/00010",
    ">": "01000/00100/00010/00001/00010/00100/01000",
    "+": "00000/00100/00100/11111/00100/00100/00000",
    "=": "00000/00000/11111/00000/11111/00000/00000",
    "%": "11001/11010/00010/00100/01000/01011/10011",
    "'": "00100/00100/00000/00000/00000/00000/00000",
    '"': "01010/01010/00000/00000/00000/00000/00000",
    "*": "00000/00100/10101/01110/10101/00100/00000",
    "|": "00100/00100/00100/00100/00100/00100/00100",
    "&": "01100/10010/10100/01000/10101/10010/01101",
    "\u00b0": "01100/10010/01100/00000/00000/00000/00000",
    "\u00c4": "01010/00000/01110/10001/11111/10001/10001",
    "\u00d6": "01010/00000/01110/10001/10001/10001/01110",
    "\u00dc": "01010/00000/10001/10001/10001/10001/01110",
    "\u25b2": "00100/00100/01110/01110/11111/11111/00000",
    "\u25bc": "00000/11111/11111/01110/01110/00100/00100",
    "\u25ba": "01000/01100/01110/01111/01110/01100/01000",
    "\u25c4": "00010/00110/01110/11110/01110/00110/00010",
    "\u2022": "00000/00000/01110/01110/01110/00000/00000",
}

GW, GH = 5, 7
UP, DOWN, RIGHT, LEFT, DOT = "\u25b2", "\u25bc", "\u25ba", "\u25c4", "\u2022"

_TRANS = {"\u00df": "SS", "\u00e4": "\u00c4", "\u00f6": "\u00d6", "\u00fc": "\u00dc"}


class PixelFont:
    """Rendert die eingebaute 5x7-Schrift, mit Cache."""

    def __init__(self) -> None:
        self._rows = {k: v.split("/") for k, v in _GLYPHS.items()}
        self._cache: dict[tuple, pygame.Surface] = {}

    @staticmethod
    def prepare(text: str) -> str:
        out = []
        for ch in text:
            out.append(_TRANS.get(ch, ch.upper() if ch.isalpha() else ch))
        return "".join(out)

    def width(self, text: str, scale: int = 1, spacing: int = 1) -> int:
        n = len(self.prepare(text))
        if n == 0:
            return 0
        return n * (GW + spacing) * scale - spacing * scale

    def height(self, scale: int = 1) -> int:
        return GH * scale

    def render(self, text: str, color, scale: int = 1, spacing: int = 1) -> pygame.Surface:
        key = (text, color, scale, spacing)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        txt = self.prepare(text)
        w = max(1, self.width(text, scale, spacing))
        surf = pygame.Surface((w, GH * scale), pygame.SRCALPHA)
        step = (GW + spacing) * scale
        for i, ch in enumerate(txt):
            rows = self._rows.get(ch)
            if rows is None:
                rows = self._rows["?"]
            ox = i * step
            for ry, row in enumerate(rows):
                run = 0
                for rx in range(GW + 1):
                    on = rx < GW and row[rx] == "1"
                    if on:
                        run += 1
                    elif run:
                        pygame.draw.rect(
                            surf, color,
                            (ox + (rx - run) * scale, ry * scale, run * scale, scale))
                        run = 0
        if len(self._cache) > 900:
            self._cache.clear()
        self._cache[key] = surf
        return surf

    def draw(self, target, text, x, y, color, scale=1, spacing=1,
             align="left", shadow=None):
        surf = self.render(text, color, scale, spacing)
        if align == "right":
            x -= surf.get_width()
        elif align == "center":
            x -= surf.get_width() // 2
        if shadow is not None:
            target.blit(self.render(text, shadow, scale, spacing), (x + scale, y + scale))
        target.blit(surf, (x, y))
        return surf.get_width()


FONT = PixelFont()


def fit(text: str, max_px: int, scale: int, spacing: int = 1) -> str:
    """Kuerzt Text hart auf die verfuegbare Breite."""
    while text and FONT.width(text, scale, spacing) > max_px:
        text = text[:-1]
    return text


def wrap(text: str, max_chars: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        probe = w if not cur else cur + " " + w
        if len(probe) <= max_chars:
            cur = probe
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# --------------------------------------------------------------------------
# Einstellungen
# --------------------------------------------------------------------------

SKALIER_MODI = ["GEFÜLLT", "GANZZAHLIG"]
BILDRATEN = [60, 120, 0]
SCHWIERIGKEITEN = ["LEICHT", "NORMAL", "SCHWER", "EISERN"]


class Settings:
    defaults = {
        "fullscreen": False,
        "scale_mode": 0,
        "fps_index": 0,
        "vol_master": 70,
        "vol_ambient": 45,
        "vol_sfx": 75,
        "crt": True,
        "splash": True,
        "callsign": "PILOT",
        "difficulty": 1,
        "region": 0,
    }

    def __init__(self) -> None:
        self.data = dict(self.defaults)
        self.load()

    def __getattr__(self, name):
        data = self.__dict__.get("data", {})
        if name in data:
            return data[name]
        raise AttributeError(name)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def load(self):
        try:
            raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            for k, v in raw.items():
                if k in self.defaults and isinstance(v, type(self.defaults[k])):
                    self.data[k] = v
        except Exception:
            pass

    def save(self):
        try:
            SETTINGS_PATH.write_text(
                json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


# --------------------------------------------------------------------------
# Ton (komplett synthetisch, ohne Dateien)
# --------------------------------------------------------------------------

MIX_RATE = 44100


class Audio:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.ok = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.drone_channel = None
        try:
            pygame.mixer.init(frequency=MIX_RATE, size=-16, channels=2, buffer=512)
            self.ok = pygame.mixer.get_init() is not None
        except pygame.error:
            self.ok = False
        if not self.ok:
            return
        try:
            self.sounds["move"] = self._tone(660, 45, 0.22, "square", sweep=0.25)
            self.sounds["enter"] = self._chord([(330, 55), (495, 90)], 0.28)
            self.sounds["back"] = self._tone(220, 90, 0.24, "square", sweep=-0.4)
            self.sounds["deny"] = self._tone(110, 130, 0.26, "saw", sweep=-0.15)
            self.sounds["tick"] = self._tone(880, 25, 0.14, "square")
            self.sounds["boot"] = self._tone(140, 220, 0.20, "saw", sweep=1.6)
            self.drone = self._drone(4.0)
        except Exception:
            self.ok = False
            return
        self.apply_volumes()
        self.start_drone()

    # -- Synthese ---------------------------------------------------------
    @staticmethod
    def _wave(kind, phase):
        if kind == "square":
            return 1.0 if phase < 0.5 else -1.0
        if kind == "saw":
            return 2.0 * phase - 1.0
        if kind == "noise":
            return random.uniform(-1.0, 1.0)
        return math.sin(2.0 * math.pi * phase)

    def _tone(self, freq, ms, vol, kind="square", sweep=0.0):
        n = max(1, int(MIX_RATE * ms / 1000.0))
        buf = array.array("h")
        phase = 0.0
        attack = max(1, int(MIX_RATE * 0.003))
        for i in range(n):
            f = freq * (1.0 + sweep * (i / n))
            phase = (phase + f / MIX_RATE) % 1.0
            env = (1.0 - i / n) ** 1.5
            env *= min(1.0, i / attack)
            s = int(max(-1.0, min(1.0, self._wave(kind, phase) * env * vol)) * 32000)
            buf.append(s)
            buf.append(s)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def _chord(self, parts, vol):
        total = sum(p[1] for p in parts)
        n = max(1, int(MIX_RATE * total / 1000.0))
        buf = array.array("h")
        idx, acc, phase = 0, 0, 0.0
        for i in range(n):
            while idx < len(parts) - 1 and i > acc + MIX_RATE * parts[idx][1] / 1000.0:
                acc += MIX_RATE * parts[idx][1] / 1000.0
                idx += 1
            phase = (phase + parts[idx][0] / MIX_RATE) % 1.0
            env = min(1.0, (1.0 - i / n) * 2.2) * min(1.0, i / 200.0)
            s = int(max(-1.0, min(1.0, self._wave("square", phase) * env * vol)) * 32000)
            buf.append(s)
            buf.append(s)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def _drone(self, seconds):
        """Nahtlos schleifbarer Reaktorbrumm (nur ganzzahlige Perioden)."""
        n = int(MIX_RATE * seconds)
        buf = array.array("h")
        f1, f2, f3 = 55.0, 55.25, 82.5
        tp = 2.0 * math.pi
        for i in range(n):
            t = i / MIX_RATE
            swell = 0.62 + 0.38 * math.sin(tp * (0.25 * t))
            s = (math.sin(tp * f1 * t) * 0.55
                 + math.sin(tp * f2 * t) * 0.35
                 + math.sin(tp * f3 * t) * 0.18 * swell)
            v = int(max(-1.0, min(1.0, s * 0.30 * swell)) * 32000)
            buf.append(v)
            buf.append(v)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    # -- Steuerung --------------------------------------------------------
    def apply_volumes(self):
        if not self.ok:
            return
        m = self.settings.vol_master / 100.0
        for s in self.sounds.values():
            s.set_volume(m * self.settings.vol_sfx / 100.0 * 0.9)
        if self.drone_channel is not None:
            self.drone_channel.set_volume(m * self.settings.vol_ambient / 100.0 * 0.8)

    def start_drone(self):
        if not self.ok:
            return
        try:
            self.drone_channel = self.drone.play(loops=-1, fade_ms=1200)
            self.apply_volumes()
        except pygame.error:
            self.drone_channel = None

    def play(self, name):
        if not self.ok:
            return
        snd = self.sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except pygame.error:
                pass

    def shutdown(self):
        if self.ok:
            try:
                pygame.mixer.fadeout(400)
            except pygame.error:
                pass


# --------------------------------------------------------------------------
# Zeichen-Hilfen
# --------------------------------------------------------------------------

def cut_points(rect: pygame.Rect, cut: int = 5):
    x, y, w, h = rect
    return [
        (x + cut, y), (x + w - 1 - cut, y), (x + w - 1, y + cut),
        (x + w - 1, y + h - 1 - cut), (x + w - 1 - cut, y + h - 1),
        (x + cut, y + h - 1), (x, y + h - 1 - cut), (x, y + cut),
    ]


def panel(surface, rect, border=C_LINE, fill=(0, 0, 0, 208), cut=5,
          brackets=C_AMBER, bracket_len=7):
    rect = pygame.Rect(rect)
    pts = cut_points(rect, cut)
    body = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.polygon(body, fill, [(px - rect.x, py - rect.y) for px, py in pts])
    surface.blit(body, rect.topleft)
    pygame.draw.polygon(surface, border, pts, 1)
    if brackets:
        L = bracket_len
        x, y, w, h = rect
        segs = [
            ((x + cut, y), (x + cut + L, y)), ((x, y + cut), (x, y + cut + L)),
            ((x + w - 1 - cut, y), (x + w - 1 - cut - L, y)),
            ((x + w - 1, y + cut), (x + w - 1, y + cut + L)),
            ((x + cut, y + h - 1), (x + cut + L, y + h - 1)),
            ((x, y + h - 1 - cut), (x, y + h - 1 - cut - L)),
            ((x + w - 1 - cut, y + h - 1), (x + w - 1 - cut - L, y + h - 1)),
            ((x + w - 1, y + h - 1 - cut), (x + w - 1, y + h - 1 - cut - L)),
        ]
        for a, b in segs:
            pygame.draw.line(surface, brackets, a, b, 1)


def panel_tab(surface, rect, text, color=C_AMBER, bg=C_PANEL):
    """Beschriftungs-Lasche, die auf der oberen Kante sitzt."""
    rect = pygame.Rect(rect)
    tw = FONT.width(text, 1) + 12
    tab = pygame.Rect(rect.x + 12, rect.y - 4, tw, 9)
    pygame.draw.rect(surface, bg, tab)
    pygame.draw.rect(surface, color, tab, 1)
    FONT.draw(surface, text, tab.x + 6, tab.y + 1, color, 1)


def seg_bar(surface, x, y, w, h, value, color, back=C_LINE_DK, segments=0, gap=1):
    """Segmentierter Balken wie in den HUD-Mockups (value 0..1)."""
    value = max(0.0, min(1.0, value))
    if segments <= 0:
        segments = max(4, w // 4)
    seg_w = max(1, (w - (segments - 1) * gap) // segments)
    filled = int(round(value * segments))
    for i in range(segments):
        rx = x + i * (seg_w + gap)
        pygame.draw.rect(surface, color if i < filled else back, (rx, y, seg_w, h))


def dotted_circle(surface, center, radius, color, step=14, offset=0.0):
    w, h = surface.get_size()
    for a in range(0, 360, step):
        r = math.radians(a + offset)
        px = int(center[0] + math.cos(r) * radius)
        py = int(center[1] + math.sin(r) * radius)
        if 0 <= px < w and 0 <= py < h:
            surface.set_at((px, py), color)


_GLOW_CACHE: dict[tuple, pygame.Surface] = {}


def glow(surface, center, radius, color, strength=90):
    """Weicher additiver Lichtschein, pro Groesse zwischengespeichert."""
    radius = max(2, int(radius))
    key = (radius, color, int(strength) // 6)
    g = _GLOW_CACHE.get(key)
    if g is None:
        d = radius * 2
        g = pygame.Surface((d, d), pygame.SRCALPHA)
        steps = max(3, radius // 2)
        for i in range(steps, 0, -1):
            f = i / steps
            a = int(strength * (1.0 - f) ** 2)
            pygame.draw.circle(g, (*color, a), (radius, radius), int(radius * f))
        if len(_GLOW_CACHE) > 400:
            _GLOW_CACHE.clear()
        _GLOW_CACHE[key] = g
    surface.blit(g, (center[0] - radius, center[1] - radius),
                 special_flags=pygame.BLEND_RGB_ADD)


_DUST_CACHE: dict[tuple, pygame.Surface] = {}


def dust_pixel(alpha, size):
    key = (alpha // 8, size)
    s = _DUST_CACHE.get(key)
    if s is None:
        s = pygame.Surface((size, 1), pygame.SRCALPHA)
        s.fill((*C_MUTED, alpha))
        _DUST_CACHE[key] = s
    return s


# --------------------------------------------------------------------------
# Walker-Sprite (Dachansicht, aus Modulen zusammengesetzt)
# --------------------------------------------------------------------------

WALKER_SIZE = 78


def build_hull() -> pygame.Surface:
    s = pygame.Surface((WALKER_SIZE, WALKER_SIZE), pygame.SRCALPHA)
    c = WALKER_SIZE // 2

    # Beine als Saeulen, diagonal nach aussen
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        inner = (c + sx * 12, c + sy * 12)
        outer = (c + sx * 33, c + sy * 31)
        pygame.draw.line(s, C_HULL_SH, inner, outer, 7)
        pygame.draw.line(s, C_HULL_DK, inner, outer, 5)
        pygame.draw.rect(s, C_HULL_SH, (outer[0] - 4, outer[1] - 4, 8, 8))
        pygame.draw.rect(s, C_HULL_DK, (outer[0] - 3, outer[1] - 3, 6, 6))

    # Rumpf
    hull = pygame.Rect(13, 11, 52, 56)
    pygame.draw.polygon(s, C_HULL, cut_points(hull, 8))
    pygame.draw.polygon(s, C_HULL_SH, cut_points(hull, 8), 1)

    # Plattenfugen
    pygame.draw.line(s, C_HULL_DK, (18, 32), (60, 32))
    pygame.draw.line(s, C_HULL_DK, (18, 50), (60, 50))
    pygame.draw.line(s, C_HULL_DK, (39, 12), (39, 31))

    # Cockpit-Slit (Bug oben)
    pygame.draw.rect(s, C_HULL_SH, (29, 14, 20, 6))
    pygame.draw.rect(s, C_CREAM, (31, 16, 16, 2))

    # Reaktorluefter
    pygame.draw.circle(s, C_HULL_SH, (25, 42), 8)
    pygame.draw.circle(s, (70, 30, 16), (25, 42), 6)
    pygame.draw.circle(s, C_RUST, (25, 42), 4)
    pygame.draw.circle(s, C_ORANGE, (25, 42), 2)

    # Kuehlerlamellen
    for i in range(4):
        pygame.draw.rect(s, C_TEAL_DK, (45 + i * 4, 36, 3, 13))
    pygame.draw.rect(s, C_HULL_SH, (44, 35, 19, 15), 1)

    # Dachluke
    pygame.draw.rect(s, C_HULL_DK, (32, 54, 12, 10))
    pygame.draw.rect(s, C_HULL_SH, (32, 54, 12, 10), 1)
    pygame.draw.line(s, C_HULL_SH, (32, 59), (43, 59))

    # Turmring
    pygame.draw.circle(s, C_HULL_SH, (39, 36), 12, 1)
    return s


def build_turret() -> pygame.Surface:
    s = pygame.Surface((34, 34), pygame.SRCALPHA)
    base = pygame.Rect(9, 9, 16, 16)
    pygame.draw.polygon(s, C_HULL_DK, cut_points(base, 4))
    pygame.draw.polygon(s, C_HULL_SH, cut_points(base, 4), 1)
    pygame.draw.rect(s, C_HULL_SH, (15, 0, 4, 12))
    pygame.draw.rect(s, C_HULL_DK, (16, 1, 2, 10))
    pygame.draw.rect(s, C_HULL_SH, (13, 12, 8, 3))
    return s


def build_shadow() -> pygame.Surface:
    s = pygame.Surface((WALKER_SIZE, WALKER_SIZE), pygame.SRCALPHA)
    hull = pygame.Rect(11, 9, 56, 60)
    pygame.draw.polygon(s, (0, 0, 0, 120), cut_points(hull, 10))
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        c = WALKER_SIZE // 2
        pygame.draw.line(s, (0, 0, 0, 120),
                         (c + sx * 12, c + sy * 12), (c + sx * 33, c + sy * 31), 7)
    return s


class RotCache:
    """Dreh-Cache, damit pro Bild nicht neu rotiert wird."""

    def __init__(self, surface: pygame.Surface, step: int = 2) -> None:
        self.src = surface
        self.step = step
        self.cache: dict[int, pygame.Surface] = {}

    def get(self, angle: float) -> pygame.Surface:
        key = int(round(angle / self.step)) * self.step % 360
        hit = self.cache.get(key)
        if hit is None:
            hit = pygame.transform.rotate(self.src, -key)
            self.cache[key] = hit
        return hit


# --------------------------------------------------------------------------
# Hintergrundszene: Draufsicht auf den Aschewald
# --------------------------------------------------------------------------

class Scene:
    def __init__(self) -> None:
        self.rnd = random.Random(4711)
        self.terrain = self._build_terrain()
        self.embers = [(self.rnd.randrange(20, VW - 20), self.rnd.randrange(20, VH - 20),
                        self.rnd.randrange(3, 7), self.rnd.random() * 6.0)
                       for _ in range(7)]
        self.dust = [{"x": self.rnd.uniform(0, VW), "y": self.rnd.uniform(0, VH),
                      "v": self.rnd.uniform(4, 16), "a": self.rnd.randrange(40, 130),
                      "s": 1 if self.rnd.random() < 0.8 else 2}
                     for _ in range(90)]
        self.hull = RotCache(build_hull())
        self.turret = RotCache(build_turret())
        self.shadow = RotCache(build_shadow())
        self.walker_pos = (386, 150)
        self.t = 0.0
        self.vignette = self._build_vignette()
        self.scan = self._build_scanlines()

    # -- Aufbau -----------------------------------------------------------
    def _build_terrain(self) -> pygame.Surface:
        r = self.rnd
        s = pygame.Surface((VW, VH))
        s.fill(C_GROUND)

        # Diagonaler Aschegraben
        pygame.draw.polygon(s, C_GROUND_LT,
                            [(-40, 210), (200, 60), (250, 78), (30, 250)])
        pygame.draw.polygon(s, C_GROUND_LT,
                            [(180, 44), (420, -30), (450, 10), (215, 72)])

        # Krater
        for _ in range(46):
            x, y = r.randrange(-10, VW + 10), r.randrange(-10, VH + 10)
            rw, rh = r.randrange(10, 46), r.randrange(7, 30)
            pygame.draw.ellipse(s, C_GROUND_DK, (x, y, rw, rh))
            if r.random() < 0.4:
                pygame.draw.ellipse(s, (52, 36, 24), (x, y, rw, rh), 1)

        # Trittspuren eines Walkers
        for lane in range(2):
            px, py = r.randrange(0, 120), r.randrange(160, 250)
            ang = math.radians(r.uniform(-34, -18))
            for i in range(24):
                px += math.cos(ang) * 19
                py += math.sin(ang) * 19
                off = 7 if i % 2 == 0 else -7
                ox = px + math.cos(ang + math.pi / 2) * off
                oy = py + math.sin(ang + math.pi / 2) * off
                pygame.draw.rect(s, (44, 31, 21), (int(ox), int(oy), 6, 4))
            _ = lane

        # Schrott
        for _ in range(230):
            x, y = r.randrange(VW), r.randrange(VH)
            col = r.choice([(48, 34, 23), (58, 42, 28), (40, 28, 19), (66, 48, 30)])
            s.set_at((x, y), col)
        for _ in range(26):
            x, y = r.randrange(VW), r.randrange(VH)
            w, h = r.randrange(3, 9), r.randrange(1, 3)
            pygame.draw.rect(s, (55, 40, 26), (x, y, w, h))
        return s

    def _build_vignette(self) -> pygame.Surface:
        v = pygame.Surface((VW, VH), pygame.SRCALPHA)
        # Links abdunkeln, damit die Menuespalte lesbar bleibt
        for x in range(VW):
            a = int(max(0, 196 - x * 0.62))
            if a > 0:
                pygame.draw.line(v, (0, 0, 0, a), (x, 0), (x, VH))
        for y in range(34):
            a = int(150 * (1 - y / 34))
            pygame.draw.line(v, (0, 0, 0, a), (0, y), (VW, y))
            pygame.draw.line(v, (0, 0, 0, a), (0, VH - 1 - y), (VW, VH - 1 - y))
        for x in range(40):
            a = int(120 * (1 - x / 40))
            pygame.draw.line(v, (0, 0, 0, a), (VW - 1 - x, 0), (VW - 1 - x, VH))
        return v

    def _build_scanlines(self) -> pygame.Surface:
        s = pygame.Surface((VW, VH), pygame.SRCALPHA)
        for y in range(0, VH, 2):
            pygame.draw.line(s, (0, 0, 0, 46), (0, y), (VW, y))
        return s

    # -- Ablauf -----------------------------------------------------------
    def update(self, dt: float) -> None:
        self.t += dt
        for d in self.dust:
            d["x"] -= d["v"] * dt
            d["y"] += d["v"] * 0.22 * dt
            if d["x"] < -2:
                d["x"] = VW + 2
                d["y"] = random.uniform(0, VH)
            if d["y"] > VH + 2:
                d["y"] = -2

    def draw(self, c: pygame.Surface, crt: bool) -> None:
        c.blit(self.terrain, (0, 0))

        for (x, y, r, ph) in self.embers:
            puls = 0.55 + 0.45 * math.sin(self.t * 1.7 + ph)
            glow(c, (x, y), r * 2 + 5, (120, 50, 18), int(30 * puls))
            pygame.draw.circle(c, (96, 44, 22), (x, y), max(1, r // 2))
            pygame.draw.circle(c, (164, 76, 32), (x, y), max(1, r // 3))

        self._draw_walker(c)

        for d in self.dust:
            c.blit(dust_pixel(d["a"], d["s"]), (int(d["x"]), int(d["y"])))

        c.blit(self.vignette, (0, 0))
        if crt:
            c.blit(self.scan, (0, 0))

    def _draw_walker(self, c: pygame.Surface) -> None:
        cx, cy = self.walker_pos
        hull_angle = 24 + math.sin(self.t * 0.22) * 3.5
        turret_angle = hull_angle + math.sin(self.t * 0.42) * 52

        sh = self.shadow.get(hull_angle)
        c.blit(sh, sh.get_rect(center=(cx + 7, cy + 9)))

        hl = self.hull.get(hull_angle)
        c.blit(hl, hl.get_rect(center=(cx, cy)))

        # Reaktorschein an der mitrotierenden Luefterposition
        off = pygame.math.Vector2(25 - WALKER_SIZE / 2, 42 - WALKER_SIZE / 2)
        off = off.rotate(hull_angle)
        flick = 0.62 + 0.38 * math.sin(self.t * 6.1) * math.sin(self.t * 2.3)
        glow(c, (int(cx + off.x), int(cy + off.y)), 11, (200, 88, 26), int(78 * flick))

        tu = self.turret.get(turret_angle)
        ring = pygame.math.Vector2(39 - WALKER_SIZE / 2, 36 - WALKER_SIZE / 2).rotate(hull_angle)
        c.blit(tu, tu.get_rect(center=(int(cx + ring.x), int(cy + ring.y))))

        dotted_circle(c, (cx, cy), 52, (86, 62, 40), 12, self.t * 9)
        dotted_circle(c, (cx, cy), 53, (70, 50, 32), 12, self.t * 9 + 6)


# --------------------------------------------------------------------------
# Menue-Eintraege
# --------------------------------------------------------------------------

class Item:
    selectable = True

    def __init__(self, label, hint="", enabled=True):
        self.label = label
        self.hint = hint
        self.enabled = enabled

    def value_text(self):
        return ""

    def activate(self, app):
        return None

    def adjust(self, app, d):
        return False

    def draw_value(self, c, row: pygame.Rect, selected, color):
        vt = self.value_text()
        if vt:
            FONT.draw(c, vt, row.right - 6, row.y + 3, color, 2, align="right")


class Action(Item):
    def __init__(self, label, callback, hint="", enabled=True, accent=None):
        super().__init__(label, hint, enabled)
        self.callback = callback
        self.accent = accent

    def activate(self, app):
        return self.callback(app)


class Toggle(Item):
    def __init__(self, label, key, hint=""):
        super().__init__(label, hint)
        self.key = key

    def value_text(self):
        return "AN" if _APP.settings.data[self.key] else "AUS"

    def activate(self, app):
        self.adjust(app, 1)
        return None

    def adjust(self, app, d):
        app.settings.set(self.key, not app.settings.data[self.key])
        app.on_setting_changed(self.key)
        return True


class Cycle(Item):
    def __init__(self, label, key, options, hint="", hints=None):
        super().__init__(label, hint)
        self.key = key
        self.options = options
        self.hints = hints

    def value_text(self):
        i = _APP.settings.data[self.key] % len(self.options)
        return str(self.options[i])

    @property
    def current_hint(self):
        if self.hints:
            return self.hints[_APP.settings.data[self.key] % len(self.hints)]
        return self.hint

    def activate(self, app):
        self.adjust(app, 1)
        return None

    def adjust(self, app, d):
        i = (app.settings.data[self.key] + d) % len(self.options)
        app.settings.set(self.key, i)
        app.on_setting_changed(self.key)
        return True


class Slider(Item):
    def __init__(self, label, key, hint="", step=5):
        super().__init__(label, hint)
        self.key = key
        self.step = step
        self.track = pygame.Rect(0, 0, 0, 0)

    def value_text(self):
        return f"{_APP.settings.data[self.key]:3d}"

    def adjust(self, app, d):
        v = max(0, min(100, app.settings.data[self.key] + d * self.step))
        if v != app.settings.data[self.key]:
            app.settings.set(self.key, v)
            app.on_setting_changed(self.key)
            return True
        return False

    def set_from_x(self, app, x):
        if self.track.width <= 0:
            return
        span = max(1, self.track.width - 1)
        v = int(round((x - self.track.x) / span * 20)) * 5
        v = max(0, min(100, v))
        if v != app.settings.data[self.key]:
            app.settings.set(self.key, v)
            app.on_setting_changed(self.key)
            app.audio.play("tick")

    def draw_value(self, c, row, selected, color):
        val = _APP.settings.data[self.key]
        w = 76
        self.track = pygame.Rect(row.right - 6 - w - 26, row.y + 4, w, 7)
        seg_bar(c, self.track.x, self.track.y, self.track.width, self.track.height,
                val / 100.0, color, C_LINE_DK, segments=10, gap=2)
        FONT.draw(c, f"{val}", row.right - 6, row.y + 3, color, 2, align="right")


VERBOTENE_ZEICHEN = "\u25b2\u25bc\u25ba\u25c4\u2022"


class TextInput(Item):
    BOX_W = 132

    def __init__(self, label, key, hint="", maxlen=10, fallback="PILOT"):
        super().__init__(label, hint)
        self.key = key
        self.maxlen = maxlen
        self.fallback = fallback
        self.editing = False

    def value_text(self):
        return _APP.settings.data[self.key]

    def activate(self, app):
        if self.editing:
            self.end_edit(app)
        else:
            self.editing = True
            app.text_target = self
        return None

    def end_edit(self, app):
        """Eingabe abschliessen: leeres Feld auffuellen, einmal speichern."""
        if not self.editing:
            return
        self.editing = False
        if app.text_target is self:
            app.text_target = None
        if not app.settings.data[self.key].strip():
            app.settings.data[self.key] = self.fallback
        app.settings.save()

    def feed(self, app, event):
        val = app.settings.data[self.key]
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE,
                         pygame.K_TAB, pygame.K_UP, pygame.K_DOWN):
            self.end_edit(app)
            app.audio.play("enter")
            return
        if event.key == pygame.K_BACKSPACE:
            if val:
                app.settings.data[self.key] = val[:-1]
                app.audio.play("tick")
            return
        if event.key == pygame.K_DELETE:
            if val:
                app.settings.data[self.key] = ""
                app.audio.play("tick")
            return
        ch = PixelFont.prepare(event.unicode or "")
        if not ch or not ch.strip() and ch != " ":
            return
        if any(c not in _GLYPHS or c in VERBOTENE_ZEICHEN for c in ch):
            app.audio.play("deny")
            return
        if len(val) + len(ch) > self.maxlen:
            app.audio.play("deny")
            return
        app.settings.data[self.key] = val + ch
        app.audio.play("tick")

    def draw_value(self, c, row, selected, color):
        val = _APP.settings.data[self.key]
        box = pygame.Rect(row.right - 6 - self.BOX_W, row.y + 1,
                          self.BOX_W, row.height - 2)
        fill = pygame.Surface(box.size, pygame.SRCALPHA)
        fill.fill((6, 4, 3, 235))
        c.blit(fill, box.topleft)
        pygame.draw.rect(c, C_TEAL if self.editing else C_LINE, box, 1)

        txt = fit(val, self.BOX_W - 16, 2)
        w = FONT.draw(c, txt, box.x + 5, box.y + 3,
                      C_TEAL if self.editing else color, 2)
        if self.editing and int(time.monotonic() * 2.4) % 2 == 0:
            pygame.draw.rect(c, C_TEAL, (box.x + 6 + w, box.y + 3, 5, 10))


class Spacer(Item):
    selectable = False

    def __init__(self, height=6):
        super().__init__("")
        self.height = height


# --------------------------------------------------------------------------
# Seiten
# --------------------------------------------------------------------------

_MAP_CACHE: dict[int, pygame.Surface] = {}


def sector_preview(index: int, size=(104, 46)) -> pygame.Surface:
    """Kleine, pro Region feste Sektorkarte (wie Szene 04 der Mockups)."""
    hit = _MAP_CACHE.get(index)
    if hit is not None:
        return hit
    rnd = random.Random(900 + index)
    s = pygame.Surface(size, pygame.SRCALPHA)
    disp = REGIONEN[index][2]
    facs = list(disp.items())
    nodes = []
    for _ in range(8):
        nodes.append((rnd.randrange(7, size[0] - 7), rnd.randrange(11, size[1] - 6)))
    nodes.sort()
    for a, b in zip(nodes, nodes[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        steps = max(2, int(math.hypot(dx, dy) / 3))
        for i in range(steps):
            if i % 2:
                continue
            s.set_at((int(a[0] + dx * i / steps), int(a[1] + dy * i / steps)),
                     (*C_LINE, 190))
    for (nx, ny) in nodes:
        roll = rnd.random() * sum(v for _, v in facs)
        col = C_MUTED
        for name, val in facs:
            roll -= val
            if roll <= 0:
                col = FRAKTIONSFARBE[name]
                break
        pygame.draw.rect(s, (*col, 255), (nx - 1, ny - 1, 3, 3))
    FONT.draw(s, "SEKTORKARTE", 2, 2, C_MUTED_DK, 1)
    _MAP_CACHE[index] = s
    return s


REGIONEN = [
    ("ASCHEWALD", "sektor 12. viel schrott, wenige patrouillen. der ruhige einstieg.",
     {"KOLONNE": 0.3, "CHOR": 0.15, "WERFTEN": 0.7}),
    ("TRICHTERFELD", "dichte kolonne-verbände, dafür schwere module im wrackfeld.",
     {"KOLONNE": 0.85, "CHOR": 0.25, "WERFTEN": 0.35}),
    ("CHORWERK-RUINE", "der chor sendet noch. beste technik, kaum überlebende.",
     {"KOLONNE": 0.2, "CHOR": 0.9, "WERFTEN": 0.2}),
]

STEUERUNG = [
    ("LAUFEN", "W A S D"), ("INTERAGIEREN", "E"),
    ("BAUEN", "B"), ("WERKZEUG", "Q"),
    ("MODUS WECHSELN", "TAB"), ("ANSICHT / ZOOM", "MAUSRAD"),
    ("DREHEN (FAHRT)", "A / D"), ("FAHRT", "W / S"),
    ("BOOST", "SHIFT"), ("ZIELEN", "MAUS"),
    ("AUTOPILOT", "H"), ("MENÜ", "ESC"),
]


class Page:
    key = "page"
    tab = ""
    px, py, pw = 26, 126, 214
    row_h = 17
    body_h = 0
    cut = 6

    def __init__(self, app):
        self.app = app
        self.items: list[Item] = []
        self.index = 0
        self.build()
        self.select_first()

    def build(self):
        pass

    # -- Navigation -------------------------------------------------------
    def select_first(self):
        for i, it in enumerate(self.items):
            if it.selectable and it.enabled:
                self.index = i
                return
        self.index = 0

    def move(self, d):
        if not self.items:
            return
        i = self.index
        for _ in range(len(self.items)):
            i = (i + d) % len(self.items)
            if self.items[i].selectable and self.items[i].enabled:
                if i != self.index:
                    self.index = i
                    self.app.audio.play("move")
                    self.app.select_anim = 0.0
                return

    @property
    def current(self):
        if 0 <= self.index < len(self.items):
            return self.items[self.index]
        return None

    # -- Geometrie --------------------------------------------------------
    def rect(self) -> pygame.Rect:
        h = 12 + self.body_h + sum(
            it.height if isinstance(it, Spacer) else self.row_h for it in self.items) + 10
        return pygame.Rect(self.px, self.py, self.pw, h)

    def row_rect(self, idx) -> pygame.Rect:
        r = self.rect()
        y = r.y + 12 + self.body_h
        for i, it in enumerate(self.items):
            h = it.height if isinstance(it, Spacer) else self.row_h
            if i == idx:
                return pygame.Rect(r.x + 7, y, r.width - 14, h)
            y += h
        return pygame.Rect(0, 0, 0, 0)

    # -- Zeichnen ---------------------------------------------------------
    def draw(self, c):
        r = self.rect()
        panel(c, r, C_LINE, (6, 4, 3, 214), self.cut)
        if self.tab:
            panel_tab(c, r, self.tab)
        if self.body_h:
            self.draw_body(c, pygame.Rect(r.x + 8, r.y + 10, r.width - 16, self.body_h))
        for i, it in enumerate(self.items):
            if isinstance(it, Spacer):
                continue
            self.draw_row(c, i, it)
        self.draw_hint(c, r)

    def draw_row(self, c, i, it: Item):
        row = self.row_rect(i)
        selected = (i == self.index)
        if not it.enabled:
            col = C_MUTED_DK
        elif selected:
            col = (18, 12, 8)
        else:
            col = C_CREAM if isinstance(it, Action) else C_MUTED

        if selected:
            a = self.app.select_anim
            bar = row.copy()
            bar.width = int(row.width * min(1.0, a * 5.0))
            pygame.draw.polygon(c, C_AMBER, cut_points(bar, 4))
            pygame.draw.rect(c, C_ORANGE, (row.x, row.y, 2, row.height))
            FONT.draw(c, RIGHT, row.x + 6, row.y + 3, (18, 12, 8), 2)
        elif it.enabled and isinstance(it, Action) and it.accent:
            pygame.draw.rect(c, it.accent, (row.x, row.y + 2, 2, row.height - 4))

        lx = row.x + (20 if selected else 9)
        label = fit(it.label, row.width - 24 - self.value_width(it), 2)
        lw = FONT.draw(c, label, lx, row.y + 3, col, 2)

        if not selected and it.enabled and self.value_width(it):
            for dx in range(lx + lw + 6, row.right - 8 - self.value_width(it), 4):
                c.set_at((dx, row.y + 9), C_LINE)

        it.draw_value(c, row, selected, col if selected else
                      (C_AMBER if it.enabled else C_MUTED_DK))

    @staticmethod
    def value_width(it: Item) -> int:
        if isinstance(it, Slider):
            return 108
        if isinstance(it, TextInput):
            return it.BOX_W + 8
        vt = it.value_text()
        return FONT.width(vt, 2) + 4 if vt else 0

    def draw_hint(self, c, r):
        it = self.current
        if it is None:
            return
        text = getattr(it, "current_hint", it.hint)
        if not text:
            return
        y = r.bottom + 8
        pygame.draw.line(c, C_LINE_DK, (r.x, y - 4), (r.x + 60, y - 4))
        for line in wrap(text, 46)[:2]:
            FONT.draw(c, line, r.x + 1, y, C_MUTED, 1)
            y += 8

    def draw_body(self, c, r):
        pass

    def handle_key(self, event):
        return False


class MainPage(Page):
    key, tab = "main", "HAUPTMENÜ"
    py = 112

    def build(self):
        app = self.app
        has_save = app.save_info is not None
        info = app.save_info or {}
        self.items = [
            Action("FORTSETZEN", lambda a: a.start_game("continue"),
                   hint=(f"letzter stand: {info.get('label', '')}" if has_save
                         else "kein spielstand gefunden. starte einen neuen auftrag."),
                   enabled=has_save, accent=C_TEAL),
            Action("NEUER AUFTRAG", lambda a: a.goto("newgame"),
                   "neue kampagne. region, schwierigkeit und rufzeichen wählen."),
            Action("OPTIONEN", lambda a: a.goto("options"),
                   "bild, ton und darstellung anpassen."),
            Action("STEUERUNG", lambda a: a.goto("controls"),
                   "belegung für charakter- und fahr-modus."),
            Action("BEENDEN", lambda a: a.goto("quit"),
                   "wandler abschalten und zurück zum schreibtisch."),
        ]


class NewGamePage(Page):
    key, tab = "newgame", "NEUER AUFTRAG"
    px, py, pw = 26, 48, 322
    row_h = 17
    body_h = 58

    def build(self):
        self.items = [
            Cycle("REGION", "region", [r[0] for r in REGIONEN],
                  hints=[r[1] for r in REGIONEN]),
            Cycle("SCHWIERIGKEIT", "difficulty", SCHWIERIGKEITEN,
                  hints=["mehr schrott, weniger hitze, gegner zielen langsamer.",
                         "die ausbalancierte fassung. so ist es gedacht.",
                         "hitze steigt schneller, patrouillen jagen in gruppen.",
                         "ein wandler, ein leben. kein laden nach dem verlust."]),
            TextInput("RUFZEICHEN", "callsign",
                      "enter zum tippen, enter zum \u00fcbernehmen. bis zu 10 zeichen."),
            Spacer(4),
            Action("KAMPAGNE STARTEN", lambda a: a.start_game("new_game"),
                   "legt einen neuen spielstand an und startet im gewählten sektor.",
                   accent=C_ORANGE),
            Action("ZURÜCK", lambda a: a.goto("main"), ""),
        ]

    def draw_body(self, c, r):
        idx = self.app.settings.region % len(REGIONEN)
        name, _desc, disp = REGIONEN[idx]
        FONT.draw(c, "PRÄSENZ IM SEKTOR", r.x, r.y, C_AMBER, 1)
        FONT.draw(c, name, r.x, r.y + 12, C_CREAM, 2)
        y = r.y + 28
        for i, (fac, val) in enumerate(disp.items()):
            FONT.draw(c, fac, r.x, y + i * 10, C_MUTED, 1)
            seg_bar(c, r.x + 52, y + i * 10, 84, 5, val, FRAKTIONSFARBE[fac],
                    C_LINE_DK, segments=12, gap=2)
            FONT.draw(c, f"{int(val * 100)}", r.x + 156, y + i * 10,
                      FRAKTIONSFARBE[fac], 1, align="right")
        prev = sector_preview(idx)
        box = pygame.Rect(r.right - prev.get_width() - 3, r.y - 2,
                          prev.get_width() + 2, prev.get_height() + 2)
        pygame.draw.rect(c, (8, 6, 5), box)
        pygame.draw.rect(c, C_LINE_DK, box, 1)
        c.blit(prev, (box.x + 1, box.y + 1))


class OptionsPage(Page):
    key, tab = "options", "OPTIONEN"
    px, py, pw = 26, 46, 322
    row_h = 16

    def build(self):
        self.items = [
            Toggle("VOLLBILD", "fullscreen", "f11 tut dasselbe, jederzeit."),
            Cycle("PIXELRASTER", "scale_mode", SKALIER_MODI,
                  hints=["das bild füllt das fenster, seitenverhältnis bleibt.",
                         "nur ganze pixelvielfache. saubere kanten, schmalerer rand."]),
            Cycle("BILDRATE", "fps_index", ["60", "120", "FREI"],
                  hint="obergrenze für bilder pro sekunde."),
            Toggle("CRT-FILTER", "crt", "scanlinien und leichtes flimmern."),
            Toggle("INTRO ZEIGEN", "splash",
                   "die splash-sequenz beim start. esc \u00fcberspringt sie immer."),
            Slider("GESAMT", "vol_master", "hauptlautstärke."),
            Slider("REAKTORBRUMM", "vol_ambient", "der hintergrundton des wandlers."),
            Slider("EFFEKTE", "vol_sfx", "klicks und bestätigungen."),
            Spacer(6),
            Action("ZURÜCK", lambda a: a.goto("main"), ""),
        ]


class ControlsPage(Page):
    key, tab = "controls", "STEUERUNG"
    px, py, pw = 26, 52, 322
    body_h = 118

    def build(self):
        self.items = [Action("ZURÜCK", lambda a: a.goto("main"), "")]

    def draw_body(self, c, r):
        half = r.width // 2
        FONT.draw(c, "AN BORD", r.x, r.y, C_TEAL, 1)
        FONT.draw(c, "IM FAHR-MODUS", r.x + half, r.y, C_ORANGE, 1)
        pygame.draw.line(c, C_LINE_DK, (r.x, r.y + 9), (r.x + half - 12, r.y + 9))
        pygame.draw.line(c, C_LINE_DK, (r.x + half, r.y + 9), (r.right - 4, r.y + 9))
        for i, (label, keys) in enumerate(STEUERUNG):
            col = 0 if i < 6 else 1
            row = i % 6
            x = r.x + col * half
            y = r.y + 15 + row * 12
            FONT.draw(c, label, x, y, C_MUTED, 1)
            FONT.draw(c, keys, x + half - 16, y, C_CREAM, 1, align="right")
        y2 = r.y + 94
        pygame.draw.line(c, C_LINE_DK, (r.x, y2 - 5), (r.right - 4, y2 - 5))
        FONT.draw(c, "TAB WECHSELT ZWISCHEN BEIDEN MODI, VON ÜBERALL AN BORD.",
                  r.x, y2, C_AMBER, 1)
        FONT.draw(c, "SCROLLEN BEWEGT NUR DIE ANSICHT, NIE DIE FIGUR.",
                  r.x, y2 + 9, C_MUTED, 1)


class QuitPage(Page):
    key, tab = "quit", ""
    px, py, pw = 26, 152, 214

    def build(self):
        self.items = [
            Action("WEITERSPIELEN", lambda a: a.goto("main"), "zurück ins menü."),
            Action("ABSCHALTEN", lambda a: a.quit_now(),
                   "beendet das spiel. einstellungen sind gespeichert.",
                   accent=C_RED),
        ]

    def draw(self, c):
        r = self.rect()
        FONT.draw(c, "WIRKLICH ABSCHALTEN?", r.x + 2, r.y - 20, C_RED, 2)
        super().draw(c)


PAGES = {p.key: p for p in (MainPage, NewGamePage, OptionsPage, ControlsPage, QuitPage)}


# --------------------------------------------------------------------------
# Anwendung
# --------------------------------------------------------------------------

_APP = None  # wird in App.__init__ gesetzt, damit Items an die Settings kommen


class App:
    def __init__(self, headless=False):
        global _APP
        _APP = self
        self.settings = Settings()
        self.canvas = pygame.Surface((VW, VH))
        self.audio = Audio(self.settings)
        self.scene = Scene()
        self.save_info = self.read_save()
        self.pages: dict[str, Page] = {}
        self.page: Page = self.get_page("main")
        self.select_anim = 1.0
        self.text_target = None
        self.result = {"action": "quit"}
        self.running = True
        self.boot_t = 0.0
        self.boot_done = False
        self.fade = 1.0            # 1 = schwarz, 0 = klar
        self.fade_dir = -1
        self.pending = None
        self.t = 0.0
        self.hover_index = None
        self.drag_slider = None
        self.headless = headless
        self.windowed_size = tuple(START_FENSTER)

    # -- Spielstand -------------------------------------------------------
    @staticmethod
    def read_save():
        try:
            data = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "label" in data:
                return data
        except Exception:
            return None
        return None

    def write_save(self):
        data = {
            "label": time.strftime("%d.%m.%Y %H:%M"),
            "region": REGIONEN[self.settings.region % len(REGIONEN)][0],
            "difficulty": SCHWIERIGKEITEN[self.settings.difficulty % len(SCHWIERIGKEITEN)],
            "callsign": self.settings.callsign,
        }
        try:
            SAVE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                                 encoding="utf-8")
        except OSError:
            pass
        self.save_info = data
        self.pages.pop("main", None)

    # -- Seiten -----------------------------------------------------------
    def get_page(self, key) -> Page:
        page = self.pages.get(key)
        if page is None:
            page = PAGES[key](self)
            self.pages[key] = page
        return page

    def goto(self, key):
        if self.text_target is not None:
            self.text_target.end_edit(self)
        self.audio.play("enter" if key != "main" else "back")
        self.page = self.get_page(key)
        self.page.select_first()
        self.select_anim = 0.0

    def back(self):
        if self.page.key == "main":
            self.goto("quit")
        else:
            self.goto("main")

    def quit_now(self):
        self.result = {"action": "quit"}
        self.fade_dir = 1
        self.pending = "exit"

    def start_game(self, action):
        self.result = {
            "action": action,
            "region": REGIONEN[self.settings.region % len(REGIONEN)][0],
            "difficulty": SCHWIERIGKEITEN[self.settings.difficulty % len(SCHWIERIGKEITEN)],
            "callsign": self.settings.callsign,
        }
        self.audio.play("boot")
        self.fade_dir = 1
        self.pending = "play"

    def on_setting_changed(self, key):
        if key in ("vol_master", "vol_ambient", "vol_sfx"):
            self.audio.apply_volumes()
        elif key == "fullscreen":
            self.apply_display()
        elif key == "splash":
            pass
        elif key == "scale_mode":
            self.compute_viewport()

    # -- Anzeige ----------------------------------------------------------
    def apply_display(self):
        """Setzt den Anzeigemodus. Mehrere Rueckfallebenen, weil Vollbild je
        nach Treiber unterschiedlich zickt."""
        if self.headless:
            self.window = pygame.display.set_mode(START_FENSTER)
            self.compute_viewport()
            return

        if self.settings.fullscreen:
            desk = self.desktop_size()
            # Kein pygame.SCALED: das mischt sich schlecht mit dem eigenen
            # Hochskalieren und mit spaeteren Fenstermodi.
            versuche = [(desk, pygame.FULLSCREEN),
                        ((0, 0), pygame.FULLSCREEN),
                        (desk, pygame.NOFRAME)]
        else:
            size = self.windowed_size
            versuche = [(size, pygame.RESIZABLE)]

        # Bewusst ohne vsync=1: das verlangt einen Renderer, den nicht jeder
        # Treiber hat. Die Bildrate begrenzt ohnehin clock.tick().
        letzter = None
        for size, flags in versuche:
            try:
                self.window = pygame.display.set_mode(size, flags)
                self.compute_viewport()
                return
            except pygame.error as err:
                letzter = err
        # Nichts hat geklappt: zurueck ins Fenster, damit das Spiel weiterlaeuft
        print("Anzeigemodus nicht verfuegbar:", letzter)
        self.settings.set("fullscreen", False)
        self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self.compute_viewport()

    @staticmethod
    def desktop_size():
        try:
            sizes = pygame.display.get_desktop_sizes()
            if sizes:
                return sizes[0]
        except (pygame.error, AttributeError):
            pass
        info = pygame.display.Info()
        if info.current_w > 0 and info.current_h > 0:
            return (info.current_w, info.current_h)
        return START_FENSTER

    def toggle_fullscreen(self):
        self.settings.set("fullscreen", not self.settings.fullscreen)
        self.apply_display()

    def compute_viewport(self):
        sw, sh = self.window.get_size()
        raw = min(sw / VW, sh / VH)
        if SKALIER_MODI[self.settings.scale_mode % 2] == "GANZZAHLIG":
            scale = max(1.0, float(int(raw)))
        else:
            scale = max(0.25, raw)
        self.scale = scale
        w, h = int(VW * scale), int(VH * scale)
        self.viewport = pygame.Rect((sw - w) // 2, (sh - h) // 2, w, h)

    def to_virtual(self, pos):
        x = (pos[0] - self.viewport.x) / max(0.001, self.scale)
        y = (pos[1] - self.viewport.y) / max(0.001, self.scale)
        return x, y

    # -- Eingabe ----------------------------------------------------------
    def handle(self, event):
        if event.type == pygame.QUIT:
            self.result = {"action": "quit"}
            self.running = False
            return
        if event.type in (pygame.WINDOWSIZECHANGED, pygame.VIDEORESIZE):
            surf = pygame.display.get_surface()
            if surf is not None:
                self.window = surf
            if not self.settings.fullscreen and not self.headless:
                self.windowed_size = self.window.get_size()
            self.compute_viewport()
            return

        if self.pending:
            return

        if event.type == pygame.KEYDOWN:
            self.on_key(event)
        elif event.type == pygame.MOUSEMOTION:
            self.on_motion(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.on_click(event)
        elif event.type == pygame.MOUSEBUTTONUP:
            self.drag_slider = None
        elif event.type == pygame.MOUSEWHEEL:
            if not self.text_target:
                self.page.move(-1 if event.y > 0 else 1)

    def on_key(self, event):
        if not self.boot_done:
            self.skip_boot()
            return
        if event.key == pygame.K_F11 or (
                event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT):
            self.toggle_fullscreen()
            return
        if self.text_target is not None:
            self.text_target.feed(self, event)
            return

        page = self.page
        if event.key in (pygame.K_UP, pygame.K_w):
            page.move(-1)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            page.move(1)
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self._adjust(-1)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._adjust(1)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._activate()
        elif event.key == pygame.K_ESCAPE:
            self.back()
        elif event.key == pygame.K_HOME:
            page.select_first()

    def _adjust(self, d):
        it = self.page.current
        if it is None or not it.enabled:
            return
        if it.adjust(self, d):
            self.audio.play("tick")

    def _activate(self):
        it = self.page.current
        if it is None:
            return
        if not it.enabled:
            self.audio.play("deny")
            return
        if isinstance(it, Action):
            self.audio.play("enter")
        it.activate(self)

    def on_motion(self, event):
        if not self.boot_done:
            return
        mx, my = self.to_virtual(event.pos)
        if self.drag_slider is not None:
            self.drag_slider.set_from_x(self, mx)
            return
        for i, it in enumerate(self.page.items):
            if not it.selectable or not it.enabled:
                continue
            if self.page.row_rect(i).collidepoint(mx, my):
                if i != self.page.index:
                    self.page.index = i
                    self.select_anim = 0.0
                    self.audio.play("move")
                self.hover_index = i
                return
        self.hover_index = None

    def on_click(self, event):
        if not self.boot_done:
            self.skip_boot()
            return
        if event.button != 1:
            if event.button == 3:
                self.back()
            return
        mx, my = self.to_virtual(event.pos)
        if self.text_target is not None:
            ziel = self.page.row_rect(self.page.items.index(self.text_target))
            if not ziel.collidepoint(mx, my):
                self.text_target.end_edit(self)
        for i, it in enumerate(self.page.items):
            if not it.selectable:
                continue
            if self.page.row_rect(i).collidepoint(mx, my):
                if not it.enabled:
                    self.audio.play("deny")
                    return
                self.page.index = i
                if isinstance(it, Slider) and it.track.collidepoint(mx, my):
                    self.drag_slider = it
                    it.set_from_x(self, mx)
                    return
                self._activate()
                return

    def skip_boot(self):
        if not self.boot_done:
            self.boot_done = True
            self.boot_t = 99.0
            self.audio.play("enter")

    # -- Ablauf -----------------------------------------------------------
    def update(self, dt):
        self.t += dt
        self.scene.update(dt)
        if self.text_target is not None and self.page.current is not self.text_target:
            self.text_target.end_edit(self)
        self.select_anim = min(1.0, self.select_anim + dt * 4.0)
        if not self.boot_done:
            self.boot_t += dt
            if self.boot_t > 3.4:
                self.boot_done = True
        if self.fade_dir < 0:
            self.fade = max(0.0, self.fade - dt * 1.8)
        elif self.fade_dir > 0:
            self.fade = min(1.0, self.fade + dt * 2.6)
            if self.fade >= 1.0 and self.pending:
                self.running = False

    # -- Zeichnen ---------------------------------------------------------
    def draw(self):
        c = self.canvas
        crt = bool(self.settings.crt)
        self.scene.draw(c, crt)

        if self.boot_done:
            self.draw_topbar(c)
            self.draw_title(c)
            self.page.draw(c)
            self.draw_footer(c)
        else:
            self.draw_boot(c)

        if crt:
            flick = 0.5 + 0.5 * math.sin(self.t * 31.0)
            if flick > 0.86:
                tint = pygame.Surface((VW, VH), pygame.SRCALPHA)
                tint.fill((255, 220, 170, 8))
                c.blit(tint, (0, 0))

        if self.fade > 0.001:
            veil = pygame.Surface((VW, VH), pygame.SRCALPHA)
            veil.fill((0, 0, 0, int(255 * self.fade)))
            c.blit(veil, (0, 0))

    BOOT_LINES = [
        ("REAKTORKERN", "ONLINE", C_TEAL),
        ("HYDRAULIK", "DRUCK OK", C_TEAL),
        ("KÜHLKREIS", "41 GRAD", C_TEAL),
        ("SENSORMAST", "AUSGEFAHREN", C_TEAL),
        ("WAFFENBUS", "GESPERRT", C_AMBER),
    ]

    def draw_boot(self, c):
        x, y = 34, 86
        FONT.draw(c, "KALTSTART", x, y - 16, C_MUTED, 1)
        pygame.draw.line(c, C_LINE_DK, (x, y - 6), (x + 296, y - 6))
        for i, (label, state, col) in enumerate(self.BOOT_LINES):
            t0 = 0.25 + i * 0.4
            if self.boot_t < t0:
                break
            ry = y + i * 17
            FONT.draw(c, label, x, ry, C_MUTED, 2)
            if self.boot_t > t0 + 0.18:
                FONT.draw(c, state, x + 296, ry, col, 2, align="right")
            else:
                FONT.draw(c, "...", x + 296, ry, C_MUTED_DK, 2, align="right")
        if self.boot_t > 2.45:
            blink = int(self.boot_t * 3) % 2 == 0
            FONT.draw(c, "WILLKOMMEN ZURÜCK, " + self.settings.callsign,
                      x, y + 96, C_CREAM if blink else C_AMBER, 2)
        prog = max(0.0, min(1.0, self.boot_t / 3.4))
        seg_bar(c, x, VH - 34, 296, 4, prog, C_RUST, C_LINE_DK, segments=32, gap=2)
        FONT.draw(c, "[BELIEBIGE TASTE] ÜBERSPRINGEN", x, VH - 22, C_MUTED_DK, 1)

    def draw_topbar(self, c):
        y = 9
        FONT.draw(c, "VELD", 26, y, C_AMBER, 1)
        FONT.draw(c, "SEKTOR 12", 56, y, C_MUTED, 1)
        FONT.draw(c, "ASCHEWALD", 118, y, C_MUTED, 1)
        FONT.draw(c, "WINDSTÄRKE 4", 182, y, C_MUTED, 1)
        right = VW - 26
        w = FONT.draw(c, "STABIL", right, y, C_ORANGE, 1, align="right")
        puls = int(self.t * 2) % 2 == 0
        pygame.draw.rect(c, C_ORANGE if puls else C_RUST, (right - w - 8, y, 4, 5))
        FONT.draw(c, "REAKTOR", right - w - 13, y, C_MUTED, 1, align="right")
        pygame.draw.line(c, C_LINE_DK, (26, y + 11), (right, y + 11))

    def draw_title(self, c):
        x = 26
        if self.page.key == "main" or self.page.key == "quit":
            y = 34
            FONT.draw(c, SPIEL_TITEL, x, y, C_CREAM, 5, spacing=2, shadow=(62, 26, 12))
            w = FONT.width(SPIEL_TITEL, 5, 2)
            pygame.draw.rect(c, C_ORANGE, (x, y + 40, w, 2))
            pygame.draw.rect(c, C_AMBER, (x, y + 40, 44, 2))
            FONT.draw(c, "WANDLER BAUEN. LAND NEHMEN. AM LEBEN BLEIBEN.",
                      x + 1, y + 48, C_MUTED, 1)
        else:
            y = 24
            w = FONT.draw(c, SPIEL_TITEL, x, y, C_MUTED, 2, spacing=2)
            pygame.draw.rect(c, C_RUST, (x, y + 16, w, 1))

    def draw_footer(self, c):
        y = VH - 16
        pygame.draw.line(c, C_LINE_DK, (26, y - 5), (VW - 26, y - 5))
        hint = f"[{UP}{DOWN}] WÄHLEN   [{LEFT}{RIGHT}] ÄNDERN   [ENTER] OK   [ESC] ZURÜCK"
        FONT.draw(c, hint, 26, y, C_MUTED, 1)
        FONT.draw(c, "V%s  %s" % (VERSION, PHASE), VW - 26, y, C_MUTED_DK, 1,
                  align="right")

    def present(self):
        self.window.fill(C_VOID)
        self.window.blit(pygame.transform.scale(self.canvas, self.viewport.size),
                         self.viewport.topleft)
        pygame.display.flip()

    # -- Hauptschleife ----------------------------------------------------
    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            fps = BILDRATEN[self.settings.fps_index % len(BILDRATEN)]
            dt = clock.tick(fps if fps else 0) / 1000.0
            dt = min(dt, 0.05)
            for event in pygame.event.get():
                self.handle(event)
            self.update(dt)
            self.draw()
            self.present()
        return self.result


# --------------------------------------------------------------------------
# Platzhalter-Szene, damit das Menue vollstaendig testbar ist
# --------------------------------------------------------------------------

def spiel_scene(window, app: App, result: dict) -> None:
    """Uebergibt an das eigentliche Spiel und nimmt danach wieder auf.

    Liegt das Paket `dustfront` nicht daneben, bleibt es beim Platzhalter -
    das Menue soll auch allein lauffaehig bleiben, so wie es im README
    steht.

    Nach dem Spiel muss der Anzeigemodus zurueckgeholt werden: das Spiel
    rendert auf 640x360 und setzt sich sein eigenes Fenster, das Menue
    rechnet mit 480x270.
    """
    try:
        from dustfront.main import aus_menue
    except ImportError:
        placeholder_scene(window, app, result)
        return

    app.write_save()
    try:
        aus_menue(result)
    finally:
        # Auch wenn das Spiel mit einem Fehler aussteigt, soll das Menue
        # wieder erscheinen statt in einem toten Fenster zu enden.
        app.apply_display()
        pygame.event.clear()
        pygame.key.set_repeat()


def placeholder_scene(window, app: App, result: dict) -> None:
    """Rueckfall, falls das Paket dustfront fehlt. Esc kehrt zurück."""
    canvas = pygame.Surface((VW, VH))
    clock = pygame.time.Clock()
    t = 0.0
    running = True
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        t += dt
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type in (pygame.WINDOWSIZECHANGED, pygame.VIDEORESIZE):
                app.compute_viewport()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
        canvas.fill((16, 11, 8))
        app.scene.update(dt)
        app.scene.draw(canvas, bool(app.settings.crt))
        veil = pygame.Surface((VW, VH), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        canvas.blit(veil, (0, 0))
        FONT.draw(canvas, "HIER ÜBERNIMMT DAS SPIEL", VW // 2, 112, C_CREAM, 3,
                  align="center")
        info = (f"{result['action'].upper()}   {result.get('region', '')}   "
                f"{result.get('difficulty', '')}   {result.get('callsign', '')}")
        FONT.draw(canvas, info, VW // 2, 140, C_AMBER, 1, align="center")
        FONT.draw(canvas, "[ESC] SPEICHERN UND ZURÜCK INS MENÜ", VW // 2, 160,
                  C_MUTED, 1, align="center")
        window.fill(C_VOID)
        window.blit(pygame.transform.scale(canvas, app.viewport.size),
                    app.viewport.topleft)
        pygame.display.flip()
    app.write_save()


# --------------------------------------------------------------------------
# Einstieg
# --------------------------------------------------------------------------

def run_menu(app: App | None = None) -> dict:
    """Zeigt das Menue und liefert die Auswahl als dict zurück."""
    own = app is None
    if own:
        app = build_app()
    else:
        app.running = True
        app.fade, app.fade_dir, app.pending = 1.0, -1, None
        app.boot_done = True
        app.goto("main")
    return app.run()


def build_app() -> App:
    pygame.init()
    app = App()
    app.canvas = pygame.Surface((VW, VH))
    app.apply_display()
    app.canvas = app.canvas.convert()
    pygame.display.set_caption(SPIEL_TITEL)
    icon = pygame.transform.scale(build_hull(), (64, 64))
    pygame.display.set_icon(icon)
    pygame.key.set_repeat(320, 55)
    return app


def run_splash(app) -> str:
    """Spielt die Splash-Sequenz, falls das Modul daneben liegt."""
    if not app.settings.splash or "--nosplash" in sys.argv:
        return "aus"
    try:
        import rustfront_splash
    except Exception as err:        # Modul fehlt oder ist kaputt: einfach weiter
        print("Splash-Sequenz nicht geladen:", err)
        return "fehler"
    return rustfront_splash.play(app)


def main() -> int:
    app = build_app()
    run_splash(app)
    pygame.event.clear()
    while True:
        result = app.run()
        if result["action"] == "quit":
            break
        spiel_scene(app.window, app, result)
        app.running = True
        app.fade, app.fade_dir, app.pending = 1.0, -1, None
        app.pages.pop("main", None)
        app.goto("main")
        app.audio.play("back")
    app.audio.shutdown()
    pygame.quit()
    print("Menue-Ergebnis:", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
