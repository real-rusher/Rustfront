"""
RUSTFRONT - Hauptmenue
======================

Das Hauptmenue des Spiels fuer pygame-ce. Gezeichnet wird mit den
Bausteinen des Spiels (dustfront: Schrift, Farben, Tafeln, Einstellungen,
Toene) - bis 0.34.150 hatte das Menue von alldem eine eigene Kopie, aus
der Zeit, als es noch allein laufen sollte. Seit 0.34.151 gibt es jedes
davon nur einmal.

Start:
    pip install pygame-ce
    python rustfront_menu.py            # mit Splash-Sequenz
    python rustfront_menu.py --nosplash  # ohne

Dateien:
    rustfront_menu.py     dieses Menue
    rustfront_splash.py   Ablauf und Ton der Splash-Sequenz
    splash_engine.py      Zeichenwerk der Splash-Sequenz

Steuerung:
    Pfeile / W S      Auswahl
    Enter / Leer      Bestaetigen
    Esc               Zurück
    F11               Vollbild
    Maus              Hovern, Klicken, Rad scrollen

Einstellungen liegen dort, wo das Spiel sie ablegt (dustfront/einstellungen.py).
"""

from __future__ import annotations

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
VERSION = "0.34.156"
PHASE = "PRE-ALPHA"        # PRE-ALPHA | ALPHA | BETA | RELEASE

VW, VH = 480, 270                  # virtuelle Aufloesung (alles wird hochskaliert)
START_FENSTER = (1152, 648)

# Auf iOS (seit 0.34.20) gibt es die Bildschirmtastatur und nur Vollbild.
# Geladen wird plattform.py hier nur auf iOS oder mit DUSTFRONT_TOUCH.
_plattform = None
if sys.platform == "ios" or os.environ.get("DUSTFRONT_TOUCH", "") not in ("", "0"):
    try:
        from dustfront import plattform as _plattform
    except ImportError:
        _plattform = None

# --------------------------------------------------------------------------
# Farben, Schrift, Tafeln, Einstellungen, Toene: aus dem Spiel (seit 0.34.151)
# --------------------------------------------------------------------------

from dustfront import ui  # noqa: E402
from dustfront.audio import MenueTon  # noqa: E402
from dustfront.config import (  # noqa: E402
    C_AMBER, C_CREAM, C_GROUND, C_GROUND_DK, C_GROUND_LT, C_HULL, C_HULL_DK, C_HULL_SH,
    C_LINE, C_LINE_DK, C_MUTED, C_MUTED_DK, C_ORANGE, C_PANEL, C_RED, C_RUST, C_TEAL,
    C_TEAL_DK, C_VOID)
from dustfront.einstellungen import Einstellungen  # noqa: E402
from dustfront.font import MENUE_SCHRIFT as FONT, HOCH, RECHTS, RUNTER  # noqa: E402


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
# Zeichen-Hilfen
# --------------------------------------------------------------------------

def panel(surface, rect, border=C_LINE, fill=(0, 0, 0, 208), cut=5,
          brackets=C_AMBER, bracket_len=7):
    """Tafel mit gekappten Ecken und Eckwinkeln - die aus ui.py."""
    ui.kasten(surface, rect, border, fill, cut)
    if brackets:
        ui.eckwinkel(surface, rect, brackets, bracket_len, cut)


def panel_tab(surface, rect, text, color=C_AMBER, bg=C_PANEL):
    """Beschriftungs-Lasche, die auf der oberen Kante sitzt."""
    rect = pygame.Rect(rect)
    tw = FONT.breite(text, 1) + 12
    tab = pygame.Rect(rect.x + 12, rect.y - 4, tw, 9)
    pygame.draw.rect(surface, bg, tab)
    pygame.draw.rect(surface, color, tab, 1)
    FONT.zeichnen(surface, text, tab.x + 6, tab.y + 1, color, 1)


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
    pygame.draw.polygon(s, C_HULL, ui.ecken(hull, 8))
    pygame.draw.polygon(s, C_HULL_SH, ui.ecken(hull, 8), 1)

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
    pygame.draw.polygon(s, C_HULL_DK, ui.ecken(base, 4))
    pygame.draw.polygon(s, C_HULL_SH, ui.ecken(base, 4), 1)
    pygame.draw.rect(s, C_HULL_SH, (15, 0, 4, 12))
    pygame.draw.rect(s, C_HULL_DK, (16, 1, 2, 10))
    pygame.draw.rect(s, C_HULL_SH, (13, 12, 8, 3))
    return s


def build_shadow() -> pygame.Surface:
    s = pygame.Surface((WALKER_SIZE, WALKER_SIZE), pygame.SRCALPHA)
    hull = pygame.Rect(11, 9, 56, 60)
    pygame.draw.polygon(s, (0, 0, 0, 120), ui.ecken(hull, 10))
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

    def activate(self, app):
        return None


class Action(Item):
    def __init__(self, label, callback, hint="", enabled=True, accent=None,
                 info=(), titel=""):
        super().__init__(label, hint, enabled)
        self.callback = callback
        self.accent = accent
        # Fuer die Erklaerkarte rechts (seit 0.34.79): Ueberschrift und
        # Absaetze. Wer neu ist, soll lesen koennen, was hinter einem
        # Punkt steckt, bevor er ihn anklickt.
        self.titel = titel or label
        self.info = tuple(info)

    def activate(self, app):
        return self.callback(app)


class Spacer(Item):
    selectable = False

    def __init__(self, height=6):
        super().__init__("")
        self.height = height


# --------------------------------------------------------------------------
# Seiten
# --------------------------------------------------------------------------

# Die Steuerung, wie sie im Spiel wirklich ist (seit 0.32). Vorher stand
# hier eine Liste aus den ersten Entwuerfen - Bauen, Werkzeug, Fahr-Modus,
# Autopilot -, die mit dem Spiel nichts mehr zu tun hatte. Jetzt werden
# die Tasten aus der Belegung des Spiels gelesen; wer sie dort umlegt,
# sieht sie hier umgelegt.
#   (Beschriftung, Aktionen in der Belegung, fester Text ohne Belegung)
STEUERUNG = [
    ("LAUFEN", ("vor", "links", "zurueck", "rechts"), ""),
    ("DASH", ("dash",), ""),
    ("BENUTZEN / RUFEN", ("nutzen",), ""),
    ("NACHLADEN", ("nachladen",), ""),
    ("MEDKIT", ("heilen",), ""),
    ("BRECHEISEN", ("nahkampf",), ""),
    ("FEUERART", ("feuermodus",), ""),
    ("FÄHIGKEIT / WERKZEUG", ("faehigkeit",), ""),
    ("WERKZEUG WECHSELN", ("werkzeug",), ""),
    ("INVENTAR", ("inventar",), ""),
    ("SCHIESSEN", (), "MAUS LINKS"),
    ("ZIELEN", (), "MAUS RECHTS"),
    ("WAFFE WÄHLEN", (), "1 - 9"),
    ("SICHTWEITE", (), "MAUSRAD"),
    ("RUNDEN (MEHRSP.)", ("planen",), ""),
    ("PAUSE", ("pause",), ""),
]


def steuerung_zeilen() -> list[tuple[str, str]]:
    """(Beschriftung, Tasten) - aus der Belegung des Spiels, wenn es da ist."""
    from dustfront import einstellungen as E
    opt = Einstellungen()
    raus = []
    for text, aktionen, fest in STEUERUNG:
        if fest:
            raus.append((text, fest or "-"))
            continue
        try:
            if len(aktionen) == 4:
                # WASD in einer Zeile statt vier: jeweils die erste Taste.
                tasten = " ".join(E.taste_kurz(opt.tasten.get(a, ["?"])[0])
                                  for a in aktionen)
            else:
                tasten = E.belegung_text(opt.tasten.get(aktionen[0], []))
        except Exception:
            tasten = "-"
        raus.append((text, tasten))
    return raus



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
                    self.app.audio.spielen("move")
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
        if self.karte:
            self.draw_card(c, r)
        else:
            self.draw_hint(c, r)

    # Seit 0.34.79: rechts neben der Liste eine Karte, die den gewaehlten
    # Punkt erklaert. Vorher stand darunter eine Zeile in Kleinschrift, die
    # bei grossen Fenstern mit der Fusszeile zusammenstiess und fuer
    # jemanden, der das Spiel nicht kennt, zu wenig sagte.
    karte = False

    def card_rect(self, r) -> pygame.Rect:
        x = r.right + 10
        return pygame.Rect(x, r.y, VW - 26 - x, r.height)

    def draw_card(self, c, r):
        box = self.card_rect(r)
        panel(c, box, C_LINE_DK, (6, 4, 3, 196), self.cut)
        it = self.current
        if it is None:
            return
        titel = getattr(it, "titel", "") or it.label
        FONT.zeichnen(c, ui.kuerzen(titel, box.width - 16, 2), box.x + 8, box.y + 9,
                      C_AMBER, 2)
        pygame.draw.line(c, C_LINE_DK, (box.x + 8, box.y + 25),
                         (box.right - 8, box.y + 25))
        absaetze = getattr(it, "info", ()) or ((it.hint,) if it.hint else ())
        zeichen = max(10, (box.width - 16) // 6)
        y = box.y + 32
        for n, absatz in enumerate(absaetze):
            # Ein Absatz, der mit "> " beginnt, ist ein Tipp: andere Farbe.
            tipp = absatz.startswith("> ")
            text = absatz[2:] if tipp else absatz
            for zeile in wrap(text, zeichen):
                if y + 7 > box.bottom - 6:
                    return
                FONT.zeichnen(c, zeile, box.x + 8, y,
                              C_TEAL if tipp else (C_CREAM if n == 0 else C_MUTED), 1)
                y += 9
            y += 5

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
            pygame.draw.polygon(c, C_AMBER, ui.ecken(bar, 4))
            pygame.draw.rect(c, C_ORANGE, (row.x, row.y, 2, row.height))
            FONT.zeichnen(c, RECHTS, row.x + 6, row.y + 3, (18, 12, 8), 2)
        elif it.enabled and isinstance(it, Action) and it.accent:
            pygame.draw.rect(c, it.accent, (row.x, row.y + 2, 2, row.height - 4))

        lx = row.x + (20 if selected else 9)
        FONT.zeichnen(c, ui.kuerzen(it.label, row.width - 24, 2), lx, row.y + 3, col, 2)

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
            if y + 7 >= VH - 20:
                break
            FONT.zeichnen(c, line, r.x + 1, y, C_MUTED, 1)
            y += 8

    def draw_body(self, c, r):
        pass


class MainPage(Page):
    """Das Hauptmenue (seit 0.34.79 neu geordnet).

    Gemeldet: "raeum mal alle Menues auf ... damit neue Spieler das alles
    verstehen". Darum: erst SPIELEN (drei Arten), dann VORBEREITEN
    (Ausruestung, Konto, Einstellungen), dann Hilfe und Beenden - und zu
    jedem Punkt rechts eine Karte, die sagt, was einen erwartet.
    FORTSETZEN und die Seite mit Region und Schwierigkeit sind weg: beides
    wertete das Spiel nie aus, und ein Knopf, der nichts tut, verwirrt
    gerade die, fuer die er gedacht war.
    """
    key, tab = "main", "HAUPTMENÜ"
    px, py, pw = 26, 72, 196
    karte = True

    def build(self):
        self.items = [
            Action("EINZELSPIELER", lambda a: a.start_game("new_game"),
                   info=("ALLEIN GEGEN WELLEN VON GEGNERN.",
                         "JEDE WELLE WIRD HÄRTER. SAMMLE SCHROTT, HEILE DICH "
                         "MIT MEDKITS UND HALTE SO LANGE DURCH, WIE DU KANNST.",
                         "> GUT FÜR DEN ANFANG: HIER LERNST DU STEUERUNG UND "
                         "WAFFEN IN RUHE."),
                   accent=C_ORANGE),
            Action("MEHRSPIELER", lambda a: a.goto("multiplayer"),
                   info=("MIT ANDEREN ÜBER DAS INTERNET ODER IM LAN.",
                         "DU LANDEST ZUERST IN DER LOBBY: ARENA, SCHIESSSTAND "
                         "UND ZOMBIE-GEHEGE. DORT TRÄGST DU DEINE KLASSE UND "
                         "DEINE WAFFEN UND KANNST ALLES AUSPROBIEREN.",
                         "> DER GASTGEBER STELLT DIE RUNDEN EIN UND STARTET SIE."),
                   accent=C_ORANGE),
            Action("TESTMODUS", lambda a: a.start_game("testmodus"),
                   info=("DIE SPIELWIESE.",
                         "DU SCHWEBST ALS BEOBACHTER ÜBER DER KARTE UND "
                         "SETZT GEGNER, BOTS, WAFFEN, FAHRZEUGE UND FALLEN, "
                         "WO DU WILLST. ALLE KLASSEN-FÄHIGKEITEN WIRKEN.",
                         "> DER ZIFFERNBLOCK (ODER ANTIPPEN) SIND DIE WERKZEUGE. "
                         "F2: SIEHT AUS WIE EINE NORMALE RUNDE."),
                   accent=C_TEAL),
            Spacer(5),
            Action("AUSRÜSTUNG", lambda a: a.start_game("ausruestung"),
                   titel="KLASSE & WAFFEN",
                   info=("WÄHLE DEINE KLASSE, ZWEI WAFFEN, EINE WURFWAFFE "
                         "UND DEIN AUSSEHEN.",
                         "DIE KLASSE GIBT VORTEILE (LEBEN, TEMPO, NACHLADEN ...) "
                         "UND EINE FÄHIGKEIT AUF TASTE C, ETWA EINE "
                         "MUNITIONSKISTE ODER EIN GESCHÜTZ.",
                         "> IN DER LOBBY GILT EINE ÄNDERUNG SOFORT, IN EINER "
                         "RUNDE AB DEM NÄCHSTEN EINSTIEG.")),
            Action("KONTO", lambda a: a.start_game("konto"),
                   info=("ANMELDEN ODER EIN KONTO ANLEGEN.",
                         "DAS KONTO ZÄHLT ABSCHÜSSE, SIEGE UND DEINE "
                         "BESTENLISTE UND NIMMT AUSRÜSTUNG UND EINSTELLUNGEN "
                         "AN JEDEN RECHNER MIT.",
                         "> OHNE KONTO KANNST DU GENAUSO SPIELEN.")),
            Action("EINSTELLUNGEN", lambda a: a.start_game("einstellungen"),
                   info=("BILD, TON, GRAFIK, TASTEN, BARRIEREFREIHEIT, NETZ.",
                         "ALLES AN EINEM ORT - ES GILT IM MENÜ UND IM SPIEL "
                         "GLEICHERMASSEN.",
                         "> F11 SCHALTET JEDERZEIT ZWISCHEN FENSTER UND "
                         "VOLLBILD.")),
            Spacer(5),
            Action("SO SPIELST DU", lambda a: a.goto("controls"),
                   info=("DIE WICHTIGSTEN TASTEN UND DIE ERSTEN SCHRITTE.",
                         "LIES DAS EINMAL, BEVOR DU DIE ERSTE RUNDE STARTEST. "
                         "DORT STEHEN AUCH DIE MITWIRKENDEN.")),
            Action("BEENDEN", lambda a: a.goto("quit"),
                   info=("DAS SPIEL SCHLIESSEN.",
                         "EINSTELLUNGEN UND AUSRÜSTUNG SIND SCHON GESPEICHERT.")),
        ]


class MultiplayerPage(Page):
    key, tab = "multiplayer", "MEHRSPIELER"
    px, py, pw = 26, 72, 196
    karte = True

    def build(self):
        self.items = [
            Action("LOBBY ERSTELLEN", lambda a: a.start_game("mehrspieler"),
                   info=("DU BIST GASTGEBER.",
                         "DEINE LOBBY BEKOMMT EINEN CODE AUS VIER WÖRTERN. "
                         "GIB IHN DEINEN FREUNDEN - DAMIT KOMMEN SIE ÜBER DAS "
                         "INTERNET HEREIN, OHNE ROUTER-EINSTELLUNGEN.",
                         "> IN DER LOBBY: P ODER ESC - RUNDE EINSTELLEN, "
                         "DANN STARTEN."),
                   accent=C_ORANGE),
            Action("LOBBY BEITRETEN", lambda a: a.start_game("mehrspieler_beitreten"),
                   info=("BEI JEMANDEM MITSPIELEN.",
                         "ZEIGT DIE LOBBYS IN DEINEM NETZ. FÜR EINE LOBBY IM "
                         "INTERNET GIBST DU DEN CODE EIN, DEN DIR DER "
                         "GASTGEBER GESAGT HAT.",
                         "> GASTGEBER UND GAST BRAUCHEN DIESELBE VERSION."),
                   accent=C_ORANGE),
            Spacer(5),
            Action("ZURÜCK", lambda a: a.goto("main"),
                   info=("ZURÜCK INS HAUPTMENÜ.",)),
        ]


# Was "SO SPIELST DU" neben den Tasten erklaert. Kurz, und in der
# Reihenfolge, in der man es beim ersten Spielen braucht.
ERSTE_SCHRITTE = [
    "MIT DER MAUS ZIELEN, LINKS SCHIESSEN.",
    "1-9 WECHSELN DIE WAFFE. DAS BRECHEISEN IST IMMER DA.",
    "DER DASH WEICHT AUS UND LÄDT SICH VON SELBST AUF.",
    "AM BODEN HILFT DIR EIN MITSPIELER WIEDER AUF.",
    "DIE FÄHIGKEIT DEINER KLASSE: MENÜ AUSRÜSTUNG.",
]


class ControlsPage(Page):
    """SO SPIELST DU (seit 0.34.79, vorher nur STEUERUNG): links die
    Tasten, so wie sie gerade belegt sind, rechts die ersten Schritte."""
    key, tab = "controls", "SO SPIELST DU"
    px, py, pw = 26, 50, 428
    body_h = 146

    def build(self):
        self.items = [Action("MITWIRKENDE", lambda a: a.goto("credits"), ""),
                      Action("ZURÜCK", lambda a: a.goto("main"), "")]

    def draw_body(self, c, r):
        links = 206
        FONT.zeichnen(c, "TASTEN", r.x, r.y, C_TEAL, 1)
        FONT.zeichnen(c, "ERSTE SCHRITTE", r.x + links + 12, r.y, C_ORANGE, 1)
        pygame.draw.line(c, C_LINE_DK, (r.x, r.y + 9), (r.x + links, r.y + 9))
        pygame.draw.line(c, C_LINE_DK, (r.x + links + 12, r.y + 9),
                         (r.right - 2, r.y + 9))
        for i, (label, keys) in enumerate(steuerung_zeilen()):
            y = r.y + 14 + i * 8
            if y + 7 > r.bottom:
                break
            FONT.zeichnen(c, label, r.x, y, C_MUTED, 1)
            FONT.zeichnen(c, ui.kuerzen(keys, links - FONT.breite(label) - 10, 1),
                          r.x + links, y, C_CREAM, 1, ausrichtung="rechts")
        y = r.y + 14
        x = r.x + links + 12
        zeichen = (r.right - x) // 6
        for satz in ERSTE_SCHRITTE:
            for n, zeile in enumerate(wrap(satz, zeichen - 2)):
                if n == 0:
                    pygame.draw.rect(c, C_AMBER, (x, y + 2, 3, 3))
                FONT.zeichnen(c, zeile, x + 7, y, C_CREAM if n == 0 else C_MUTED, 1)
                y += 9
            y += 3
        FONT.zeichnen(c, "UMLEGEN: EINSTELLUNGEN, STEUERUNG",
                      x, r.bottom - 8, C_AMBER, 1)


class CreditsPage(Page):
    key, tab = "credits", "MITWIRKENDE"
    px, py, pw = 26, 72, 300
    body_h = 76

    def build(self):
        self.items = [Action("ZURÜCK", lambda a: a.goto("controls"), "")]

    def draw_body(self, c, r):
        FONT.zeichnen(c, "DUSTFRONT", r.x, r.y, C_AMBER, 2)
        FONT.zeichnen(c, "EIN SPIEL VON", r.x, r.y + 22, C_MUTED, 1)
        FONT.zeichnen(c, "NICOLAS, NIKOLAUS, MARLON", r.x, r.y + 34, C_CREAM, 1)
        FONT.zeichnen(c, "UND ALFRED", r.x, r.y + 44, C_CREAM, 1)
        FONT.zeichnen(c, "PYTHON + PYGAME-CE", r.x, r.y + 62, C_TEAL, 1)


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
        FONT.zeichnen(c, "WIRKLICH ABSCHALTEN?", r.x + 2, r.y - 20, C_RED, 2)
        super().draw(c)


PAGES = {p.key: p for p in (MainPage, MultiplayerPage, CreditsPage,
                            ControlsPage, QuitPage)}


# --------------------------------------------------------------------------
# Anwendung
# --------------------------------------------------------------------------

class App:
    def __init__(self, headless=False):
        # Die Einstellungen des Spiels - es gibt nur diese (seit 0.34.151;
        # vorher hielt das Menue eine eigene Datei und glich ab).
        self.opt = Einstellungen()
        self.canvas = pygame.Surface((VW, VH))
        self.audio = MenueTon(self.opt)
        self.scene = Scene()
        self.pages: dict[str, Page] = {}
        self.page: Page = self.get_page("main")
        self.select_anim = 1.0
        self.result = {"action": "quit"}
        self.running = True
        self.boot_t = 0.0
        self.boot_done = False
        self.fade = 1.0            # 1 = schwarz, 0 = klar
        self.fade_dir = -1
        self.pending = None
        self.t = 0.0
        self.hover_index = None
        self.headless = headless
        self.windowed_size = tuple(START_FENSTER)

    # -- Seiten -----------------------------------------------------------
    def get_page(self, key) -> Page:
        page = self.pages.get(key)
        if page is None:
            page = PAGES[key](self)
            self.pages[key] = page
        return page

    def goto(self, key):
        self.audio.spielen("enter" if key != "main" else "back")
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
        self.result = {"action": action}
        self.audio.spielen("boot")
        self.fade_dir = 1
        self.pending = "play"

    # -- Anzeige ----------------------------------------------------------
    def apply_display(self):
        """Setzt den Anzeigemodus. Mehrere Rueckfallebenen, weil Vollbild je
        nach Treiber unterschiedlich zickt."""
        if self.headless:
            self.window = pygame.display.set_mode(START_FENSTER)
            self.compute_viewport()
            return

        if _plattform is not None and _plattform.nur_vollbild():
            versuche = [((0, 0), pygame.FULLSCREEN)]
        elif self.vollbild:
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
        self.opt["fenstermodus"] = "fenster"
        self.opt.speichern()
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

    @property
    def vollbild(self) -> bool:
        """Vollbild oder randlos - dann im Menue Vollbild."""
        return self.opt["fenstermodus"] != "fenster"

    def toggle_fullscreen(self):
        self.opt["fenstermodus"] = "fenster" if self.vollbild else "vollbild"
        self.opt.speichern()
        self.apply_display()

    def compute_viewport(self):
        sw, sh = self.window.get_size()
        raw = min(sw / VW, sh / VH)
        if self.opt["pixelraster"] == "ganzzahlig":
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
            if not self.vollbild and not self.headless:
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
        elif event.type == pygame.MOUSEWHEEL:
            self.page.move(-1 if event.y > 0 else 1)

    def on_key(self, event):
        if not self.boot_done:
            self.skip_boot()
            return
        if event.key == pygame.K_F11 or (
                event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT):
            self.toggle_fullscreen()
            return

        page = self.page
        if event.key in (pygame.K_UP, pygame.K_w):
            page.move(-1)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            page.move(1)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._activate()
        elif event.key == pygame.K_ESCAPE:
            self.back()
        elif event.key == pygame.K_HOME:
            page.select_first()

    def _activate(self):
        it = self.page.current
        if it is None:
            return
        if not it.enabled:
            self.audio.spielen("deny")
            return
        if isinstance(it, Action):
            self.audio.spielen("enter")
        it.activate(self)

    def on_motion(self, event):
        if not self.boot_done:
            return
        mx, my = self.to_virtual(event.pos)
        for i, it in enumerate(self.page.items):
            if not it.selectable or not it.enabled:
                continue
            if self.page.row_rect(i).collidepoint(mx, my):
                if i != self.page.index:
                    self.page.index = i
                    self.select_anim = 0.0
                    self.audio.spielen("move")
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
        for i, it in enumerate(self.page.items):
            if not it.selectable:
                continue
            if self.page.row_rect(i).collidepoint(mx, my):
                if not it.enabled:
                    self.audio.spielen("deny")
                    return
                self.page.index = i
                self._activate()
                return

    def skip_boot(self):
        if not self.boot_done:
            self.boot_done = True
            self.boot_t = 99.0
            self.audio.spielen("enter")

    # -- Ablauf -----------------------------------------------------------
    def update(self, dt):
        self.t += dt
        self.scene.update(dt)
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
        crt = bool(self.opt["menue_crt"])
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
        FONT.zeichnen(c, "KALTSTART", x, y - 16, C_MUTED, 1)
        pygame.draw.line(c, C_LINE_DK, (x, y - 6), (x + 296, y - 6))
        for i, (label, state, col) in enumerate(self.BOOT_LINES):
            t0 = 0.25 + i * 0.4
            if self.boot_t < t0:
                break
            ry = y + i * 17
            FONT.zeichnen(c, label, x, ry, C_MUTED, 2)
            if self.boot_t > t0 + 0.18:
                FONT.zeichnen(c, state, x + 296, ry, col, 2, ausrichtung="rechts")
            else:
                FONT.zeichnen(c, "...", x + 296, ry, C_MUTED_DK, 2, ausrichtung="rechts")
        if self.boot_t > 2.45:
            blink = int(self.boot_t * 3) % 2 == 0
            # Mit dem Namen aus dem Spiel (seit 0.34.151; vorher stand hier
            # immer PILOT - einstellen liess er sich seit 0.34.79 nicht mehr).
            name = str(self.opt["spielername"] or "").strip()
            FONT.zeichnen(c, "WILLKOMMEN ZURÜCK" + (", " + name if name else ""),
                          x, y + 96, C_CREAM if blink else C_AMBER, 2)
        prog = max(0.0, min(1.0, self.boot_t / 3.4))
        seg_bar(c, x, VH - 34, 296, 4, prog, C_RUST, C_LINE_DK, segments=32, gap=2)
        FONT.zeichnen(c, "[BELIEBIGE TASTE] ÜBERSPRINGEN", x, VH - 22, C_MUTED_DK, 1)

    def draw_topbar(self, c):
        y = 9
        FONT.zeichnen(c, "VELD", 26, y, C_AMBER, 1)
        FONT.zeichnen(c, "SEKTOR 12", 56, y, C_MUTED, 1)
        FONT.zeichnen(c, "ASCHEWALD", 118, y, C_MUTED, 1)
        FONT.zeichnen(c, "WINDSTÄRKE 4", 182, y, C_MUTED, 1)
        right = VW - 26
        w = FONT.zeichnen(c, "STABIL", right, y, C_ORANGE, 1, ausrichtung="rechts")
        puls = int(self.t * 2) % 2 == 0
        pygame.draw.rect(c, C_ORANGE if puls else C_RUST, (right - w - 8, y, 4, 5))
        FONT.zeichnen(c, "REAKTOR", right - w - 13, y, C_MUTED, 1, ausrichtung="rechts")
        pygame.draw.line(c, C_LINE_DK, (26, y + 11), (right, y + 11))

    def draw_title(self, c):
        x = 26
        if self.page.key in ("main", "quit", "multiplayer"):
            # Seit 0.34.79 eine Stufe kleiner: in 5 lief die Schrift in
            # den Reiter der Tafel darunter.
            y = 24
            FONT.zeichnen(c, SPIEL_TITEL, x, y, C_CREAM, 4, abstand=2, schatten=(62, 26, 12))
            w = FONT.breite(SPIEL_TITEL, 4, 2)
            pygame.draw.rect(c, C_ORANGE, (x, y + 33, w, 2))
            pygame.draw.rect(c, C_AMBER, (x, y + 33, 44, 2))
            FONT.zeichnen(c, "GEFECHTE IM STAUB", x + w + 10, y + 26,
                          C_MUTED, 1)
        else:
            y = 24
            w = FONT.zeichnen(c, SPIEL_TITEL, x, y, C_MUTED, 2, abstand=2)
            pygame.draw.rect(c, C_RUST, (x, y + 16, w, 1))

    def draw_footer(self, c):
        y = VH - 16
        pygame.draw.line(c, C_LINE_DK, (26, y - 5), (VW - 26, y - 5))
        # Ohne [<>] AENDERN (seit 0.34.79): im Hauptmenue gibt es nichts
        # mehr zu verstellen, und die Zeile lief in die Versionsnummer.
        hint = f"[{HOCH}{RUNTER}] WÄHLEN   [ENTER] OK   [ESC] ZURÜCK"
        FONT.zeichnen(c, hint, 26, y, C_MUTED, 1)
        FONT.zeichnen(c, "V%s  %s" % (VERSION, PHASE), VW - 26, y, C_MUTED_DK, 1,
                      ausrichtung="rechts")

    def present(self):
        self.window.fill(C_VOID)
        self.window.blit(pygame.transform.scale(self.canvas, self.viewport.size),
                         self.viewport.topleft)
        pygame.display.flip()

    # -- Hauptschleife ----------------------------------------------------
    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            fps = int(self.opt["bildrate"] or 0)
            dt = clock.tick(fps if fps else 0) / 1000.0
            dt = min(dt, 0.05)
            ereignisse = pygame.event.get()
            if _plattform is not None:
                # Bildschirmtastatur auf iOS: Zeichen kommen als TEXTINPUT.
                ereignisse = _plattform.text_umsetzen(ereignisse)
            for event in ereignisse:
                self.handle(event)
            self.update(dt)
            self.draw()
            self.present()
            if _plattform is not None:
                _plattform.tastatur_abgleichen()
        return self.result


# --------------------------------------------------------------------------
# Platzhalter-Szene, damit das Menue vollstaendig testbar ist
# --------------------------------------------------------------------------

# Was das Hauptmenue im Spiel oeffnet, ohne zu spielen (seit 0.34.79):
# die Menues des Spiels selbst, damit es jede Einstellung nur einmal gibt.
NUR_MENUE = ("einstellungen", "ausruestung", "konto")


def spiel_scene(window, app: App, result: dict) -> None:
    """Uebergibt an das eigentliche Spiel und nimmt danach wieder auf.

    Nach dem Spiel muss der Anzeigemodus zurueckgeholt werden: das Spiel
    rendert auf 640x360 und setzt sich sein eigenes Fenster, das Menue
    rechnet mit 480x270.
    """
    # Nicht schwarz, solange geladen wird (seit 0.34.137).
    uebersetzer_abwarten(app)
    ladebild(app)
    from dustfront.main import aus_menue
    try:
        aus_menue(result)
    finally:
        # Auch wenn das Spiel mit einem Fehler aussteigt, soll das Menue
        # wieder erscheinen statt in einem toten Fenster zu enden.
        # Was im Spiel eingestellt wurde (Bildrate, Ton ...), gilt jetzt
        # auch hier: frisch lesen, bevor das Fenster neu aufgebaut wird.
        app.opt = app.audio.opt = Einstellungen()
        app.audio.lautstaerke_setzen()
        app.apply_display()
        pygame.event.clear()
        pygame.key.set_repeat()


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
    if not app.opt["intro"] or "--nosplash" in sys.argv:
        return "aus"
    try:
        import rustfront_splash
    except Exception as err:        # Modul fehlt oder ist kaputt: einfach weiter
        print("Splash-Sequenz nicht geladen:", err)
        return "fehler"
    return rustfront_splash.play(app)


# ── Vorab uebersetzen (seit 0.34.137) ───────────────────────────────────
# Gemeldet: auf sehr schwachen Rechnern beim ersten Start jeder neuen Version
# ein langer schwarzer Schirm beim ersten Gang in die Runde (und ein kuerzerer
# bis zum Hauptmenue). Grund: Python uebersetzt jede geaenderte .py-Datei beim
# ersten Import in Bytecode (__pycache__) - 75 000 Zeilen, gemessen 0,64 s auf
# einem schnellen Rechner, auf einem langsamen ein Vielfaches. Das Menue
# braucht nur wenige Dateien; den grossen Rest (mehrspieler.py allein 9000
# Zeilen) holte erst der Klick auf SPIELEN.
# Darum uebersetzt jetzt ein eigener Prozess das ganze Paket, waehrend man im
# Menue steht. Ein Prozess und kein Faden: ein Faden hielte die GIL und
# braechte den Ton zum Haengen (siehe 0.34.136).
_UEBERSETZER = None


def _veraltet(ordner: Path) -> list:
    """Die .py-Dateien im Ordner, deren Bytecode fehlt oder aelter ist."""
    import importlib.util
    raus = []
    for py in sorted(ordner.glob("*.py")):
        try:
            pyc = Path(importlib.util.cache_from_source(str(py)))
            if not pyc.is_file() or pyc.stat().st_mtime < py.stat().st_mtime:
                raus.append(py)
        except (OSError, NotImplementedError, ValueError):
            continue
    return raus


def vorab_uebersetzen(ordner: Path | None = None):
    """Startet den Uebersetzer-Prozess, wenn etwas veraltet ist. Gibt ihn
    zurueck, oder None (nichts zu tun, oder es geht hier nicht)."""
    global _UEBERSETZER
    if getattr(sys, "frozen", False) or not sys.executable or sys.dont_write_bytecode:
        return None
    # Wie plattform.prozesse_erlaubt, aber ohne das Paket zu laden: dessen
    # __init__ zoege das ganze Spiel nach (und uebersetzte es hier vorn).
    if sys.platform == "ios":
        return None
    ordner = ordner or (Path(__file__).resolve().parent / "dustfront")
    if not ordner.is_dir() or not _veraltet(ordner):
        return None
    import subprocess
    extra = {}
    if os.name == "nt":
        # Unter normaler Prioritaet und ohne Konsolenfenster.
        extra["creationflags"] = 0x00004000 | 0x08000000   # BELOW_NORMAL | CREATE_NO_WINDOW
    try:
        _UEBERSETZER = subprocess.Popen(
            [sys.executable, "-m", "compileall", "-q", "-l", str(ordner)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL, **extra)
    except (OSError, ValueError):
        _UEBERSETZER = None
    return _UEBERSETZER


def uebersetzer_abwarten(app=None, hoechstens: float = 120.0) -> None:
    """Vor dem Spiel: laeuft der Uebersetzer noch, auf ihn warten - mit
    LAEDT im Bild statt schwarz. Doppelt uebersetzen kostete nur mehr."""
    proc = _UEBERSETZER
    if proc is None or proc.poll() is not None:
        return
    ende = time.time() + hoechstens
    while proc.poll() is None and time.time() < ende:
        for _ in pygame.event.get(pygame.QUIT):
            pass
        if app is not None:
            ladebild(app, "LÄDT DIE NEUE VERSION ...")
        time.sleep(0.05)


def ladebild(app, text: str = "LÄDT ...") -> None:
    """Ein Bild mit LAEDT, damit der Schirm beim Uebergang nicht schwarz ist."""
    try:
        c = app.canvas
        c.fill(C_VOID)
        punkte = "." * (1 + int(time.time() * 2.5) % 3)
        FONT.zeichnen(c, text.rstrip(". ") + " " + punkte, VW // 2, VH // 2 - 4, C_AMBER, 1,
                      ausrichtung="mitte")
        app.present()
    except Exception:               # noqa: BLE001  nur ein Hinweis, nie ein Absturz
        pass


def _klaenge_vorbauen() -> None:
    """Die Klaenge des Spiels schon im Menue bauen lassen (seit 0.34.58).

    Bis dahin legte das Spiel jeden Klang beim ersten Abspielen an, und der
    erste Schuss jeder Waffe hielt es bis zu 380 ms an. Erst nach dem
    Splash, damit dessen Bild ruhig laeuft; das Spiel bekommt dieselbe
    Werkstatt mit allem, was bis dahin fertig ist."""
    try:
        from dustfront.audio import im_hintergrund_bauen
        im_hintergrund_bauen()
    except Exception as err:        # ohne Spiel daneben: dann eben nicht
        print("Klaenge nicht vorgebaut:", err)


def _startauftrag() -> dict | None:
    """Gleich in den Testmodus statt ins Hauptmenue (seit 0.34.63), wenn
    DUSTFRONT_START=testmodus gesetzt ist - so startet ios/aufspielen.sh
    --testmodus die App auf dem iPhone oder iPad. Danach geht es wie
    sonst ins Hauptmenue."""
    if os.environ.get("DUSTFRONT_START", "").strip().lower() == "testmodus":
        return {"action": "testmodus",
                "karte": os.environ.get("DUSTFRONT_KARTE", "").strip().lower() or "staubtal"}
    return None


def main() -> int:
    vorab_uebersetzen()
    app = build_app()
    run_splash(app)
    pygame.event.clear()
    _klaenge_vorbauen()
    auftrag = _startauftrag()
    if auftrag is not None:
        spiel_scene(app.window, app, auftrag)
        app.running = True
        app.fade, app.fade_dir, app.pending = 1.0, -1, None
        app.pages.pop("main", None)
        app.goto("main")
    while True:
        result = app.run()
        if result["action"] == "quit":
            break
        # Wohin es zurueckgeht: aus EINSTELLUNGEN, KONTO und AUSRUESTUNG
        # auf genau diese Zeile, aus einem Spiel an den Anfang.
        seite, zeile = app.page.key, app.page.index
        spiel_scene(app.window, app, result)
        app.running = True
        app.fade, app.fade_dir, app.pending = 1.0, -1, None
        app.pages.pop("main", None)
        app.goto("main")
        if result["action"] in NUR_MENUE and seite == "main":
            app.page.index = zeile
            app.fade = 0.35
        app.audio.spielen("back")
    app.audio.ausklingen()
    try:
        from dustfront.audio import alle_anhalten
        alle_anhalten()
    except Exception:               # noqa: BLE001
        pass
    pygame.quit()
    print("Menue-Ergebnis:", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
