"""
DUSTFRONT - Wasser und die Kachelsaetze gruen und stadt (seit 0.34.131)
======================================================================

Fuer FLUSSTAL (Satz "gruen") und KANALSTADT (Satz "stadt"): dieselben
Kachelarten wie in der Wueste, aber anders gemalt (K.KARTENSAETZE) - eine
Piste ist dort ein Feldweg oder eine Strasse, ein Kaktus ein Baum, der Fels
bemooster Granit oder Betontruemmer. Dazu Wasser, seicht und tief.

Wie in art.py: Bodenbilder halten Abstand zum Rand (was bis an die Kante
laeuft, setzt sich beim Nachbarn fort und wird zur Linie), stehende Kacheln
fuellen ihr Seitenbild mit dem Stoff selbst (der Renderer nimmt daraus die
Farbe der Seiten), was man von oben sieht, ist "<name>_oben".
"""

from __future__ import annotations

import math
import random

import pygame

from . import config as K
from .core import platzhalter

T = K.TILE


def _flaeche(w, h) -> pygame.Surface:
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _koerner(s, farbe, menge, seed) -> None:
    r = random.Random(seed)
    w, h = s.get_size()
    for _ in range(menge):
        s.set_at((r.randrange(w), r.randrange(h)), farbe)


def _ton(farbe, um) -> tuple:
    return tuple(max(0, min(255, c + um)) for c in farbe)


def _reihe(name: str, zeichner, saaten) -> None:
    """Registriert name, name_2 ... mit je einer Saat."""
    for i, saat in enumerate(saaten):
        n = name if i == 0 else "%s_%d" % (name, i + 1)
        platzhalter(n)(lambda saat=saat: zeichner(saat))


# ──────────────────────────────── Wasser

def _wasser_basis(seed, grund, hell, dunkel, glanz) -> pygame.Surface:
    """Tiefes Wasser: dunkler Grund, kurze Wellenkaemme in zwei Toenen,
    hier und da ein Lichtpunkt. Kurz und weg vom Rand - sonst zoege sich
    ein Kamm ueber den ganzen Fluss."""
    r = random.Random(seed)
    s = _flaeche(T, T)
    s.fill(grund)
    for _ in range(r.randrange(3, 6)):                 # dunkle Mulden
        x, y = r.randrange(1, T - 12), r.randrange(1, T - 8)
        pygame.draw.ellipse(s, dunkel, (x, y, r.randrange(8, 14), r.randrange(4, 7)))
    for _ in range(r.randrange(4, 7)):                 # Wellenkaemme
        x, y = r.randrange(3, T - 12), r.randrange(3, T - 4)
        laenge = r.randrange(4, 9)
        pygame.draw.arc(s, hell, (x, y, laenge, 4), 0.3, math.pi - 0.3, 1)
    for _ in range(r.randrange(1, 4)):                 # Glanz
        x, y = r.randrange(4, T - 5), r.randrange(4, T - 5)
        pygame.draw.line(s, glanz, (x, y), (x + r.randrange(1, 3), y))
    _koerner(s, _ton(grund, 10), 12, seed + 1)
    return s


def _seicht_basis(seed, grund, kiesel, hell) -> pygame.Surface:
    """Seichtes Wasser: heller, der Grund schimmert durch - Kiesel und
    Sandflecken unter einer leichten Kraeuselung."""
    r = random.Random(seed)
    s = _flaeche(T, T)
    s.fill(grund)
    for _ in range(r.randrange(2, 4)):                 # Sand am Grund
        x, y = r.randrange(1, T - 12), r.randrange(1, T - 9)
        pygame.draw.ellipse(s, _ton(grund, 12), (x, y, r.randrange(8, 13), r.randrange(5, 9)))
    for _ in range(r.randrange(5, 9)):                 # Kiesel
        x, y = r.randrange(2, T - 4), r.randrange(2, T - 4)
        b = r.randrange(2, 4)
        pygame.draw.ellipse(s, r.choice(kiesel), (x, y, b, max(2, b - 1)))
    for _ in range(r.randrange(3, 6)):                 # Kraeuselung
        x, y = r.randrange(3, T - 10), r.randrange(3, T - 4)
        pygame.draw.arc(s, hell, (x, y, r.randrange(4, 8), 3), 0.4, math.pi - 0.4, 1)
    _koerner(s, _ton(grund, 16), 10, seed + 2)
    return s


_reihe("wasser", lambda saat: _wasser_basis(saat, (36, 74, 100), (70, 116, 140),
                                            (28, 60, 84), (168, 206, 214)), (1301, 1307, 1319))
_reihe("seicht", lambda saat: _seicht_basis(saat, (76, 118, 124),
                                            ((92, 110, 100), (66, 90, 88), (110, 124, 110)),
                                            (150, 194, 196)), (1321, 1327, 1331))
# Der Kanal der Stadt: dunkler, gruenlicher, mit oeligem Schimmer.
_reihe("kanal", lambda saat: _wasser_basis(saat, (34, 60, 66), (62, 94, 96),
                                           (26, 46, 52), (136, 150, 132)), (1361, 1367, 1373))


# ──────────────────────────────── Satz gruen (FLUSSTAL)

def _gras_basis(seed, grund=(68, 98, 48), bunt=0.35) -> pygame.Surface:
    """Wiese, kurz: Halme als kurze Striche in drei Gruentoenen, selten
    eine Bluete. Keine Flecken mit harter Kante - die wuerden sich ueber
    die Flaeche wiederholen."""
    r = random.Random(seed)
    s = _flaeche(T, T)
    s.fill(grund)
    # Weiche Flecken, etwas dunkler und heller - weg vom Rand, sonst
    # zoegen sie sich als Muster ueber die Wiese.
    for _ in range(r.randrange(1, 3)):
        x, y = r.randrange(3, T - 15), r.randrange(3, T - 11)
        pygame.draw.ellipse(s, _ton(grund, r.choice((-6, 5))), (x, y, r.randrange(8, 13), r.randrange(5, 8)))
    toene = (_ton(grund, -14), _ton(grund, 14), (84, 116, 54), (58, 86, 42))
    for _ in range(r.randrange(26, 36)):
        x, y = r.randrange(1, T - 1), r.randrange(3, T - 1)
        pygame.draw.line(s, r.choice(toene), (x, y), (x + r.choice((-1, 0, 0, 1)), y - r.randrange(2, 4)))
    if r.random() < bunt:
        for _ in range(r.randrange(1, 3)):
            x, y = r.randrange(3, T - 3), r.randrange(3, T - 3)
            s.set_at((x, y), r.choice(((236, 220, 120), (240, 240, 236), (210, 120, 160))))
    _koerner(s, _ton(grund, -20), 14, seed + 1)
    _koerner(s, _ton(grund, 20), 10, seed + 2)
    return s


def _wiese_basis(seed) -> pygame.Surface:
    """Hohe Wiese: Grasbueschel und Blumen auf dem kurzen Gras."""
    r = random.Random(seed)
    s = _gras_basis(seed, (72, 102, 50), 0.0)
    for _ in range(r.randrange(3, 5)):
        cx, cy = r.randrange(5, T - 5), r.randrange(7, T - 3)
        for _i in range(r.randrange(6, 10)):
            dx = r.randrange(-4, 5)
            pygame.draw.line(s, r.choice(((50, 82, 36), (96, 130, 58), (110, 138, 64))),
                             (cx, cy), (cx + dx, cy - r.randrange(4, 7)))
    for _ in range(r.randrange(2, 5)):
        x, y = r.randrange(3, T - 3), r.randrange(3, T - 3)
        farbe = r.choice(((240, 214, 92), (236, 236, 230), (196, 112, 170), (226, 96, 70)))
        s.set_at((x, y), farbe)
        s.set_at((x + 1, y), _ton(farbe, -40))
    return s


def _feldweg_basis(seed) -> pygame.Surface:
    """Festgetretene Erde: braun, mit Steinchen und feuchten Flecken."""
    r = random.Random(seed)
    s = _flaeche(T, T)
    grund = (112, 90, 62)
    s.fill(grund)
    for _ in range(r.randrange(3, 6)):
        x, y = r.randrange(2, T - 12), r.randrange(2, T - 9)
        pygame.draw.ellipse(s, r.choice(((104, 82, 56), (120, 98, 68))),
                            (x, y, r.randrange(7, 13), r.randrange(4, 8)))
    if r.random() < 0.4:                                # Pfuetze
        x, y = r.randrange(4, T - 14), r.randrange(4, T - 10)
        pygame.draw.ellipse(s, (82, 70, 54), (x, y, 10, 6))
        pygame.draw.ellipse(s, (104, 118, 120), (x + 2, y + 1, 6, 3))
    for _ in range(r.randrange(2, 5)):
        x, y = r.randrange(3, T - 4), r.randrange(3, T - 4)
        pygame.draw.rect(s, (82, 66, 48), (x, y + 1, 2, 1))
        pygame.draw.rect(s, (150, 132, 102), (x, y, 2, 1))
    _koerner(s, (130, 108, 78), 16, seed + 3)
    _koerner(s, (90, 72, 50), 14, seed + 5)
    return s


def _ufer_basis(seed) -> pygame.Surface:
    """Kiesbank am Fluss: graue, runde Kiesel auf feuchtem Sand."""
    r = random.Random(seed)
    s = _flaeche(T, T)
    s.fill((108, 100, 84))
    _koerner(s, (92, 86, 72), 40, seed + 1)
    for _ in range(r.randrange(14, 20)):
        x, y = r.randrange(2, T - 5), r.randrange(2, T - 4)
        b = r.randrange(2, 5)
        ton = r.choice(((140, 136, 126), (124, 120, 112), (150, 144, 130), (112, 110, 104)))
        pygame.draw.ellipse(s, (70, 66, 58), (x, y + 1, b, max(2, b - 1)))
        pygame.draw.ellipse(s, ton, (x, y, b, max(2, b - 1)))
    return s


def _steg_basis(seed) -> pygame.Surface:
    """Bohlen einer Bruecke, laengs gelegt, mit Fugen, durch die man das
    Wasser sieht - so liest man: darunter ist Fluss."""
    r = random.Random(seed)
    s = _flaeche(T, T)
    s.fill((40, 66, 84))
    for x in range(0, T, 16):
        ton = r.choice(((126, 94, 62), (116, 86, 56), (132, 100, 66), (110, 82, 54)))
        pygame.draw.rect(s, ton, (x + 1, 0, 14, T))
        pygame.draw.line(s, _ton(ton, 14), (x + 1, 0), (x + 1, T - 1))
        for _ in range(2):                              # Maserung
            mx = x + r.randrange(3, 12)
            pygame.draw.line(s, _ton(ton, -12), (mx, r.randrange(2, 10)), (mx, r.randrange(16, T - 2)))
        stoss = r.randrange(6, T - 6)
        pygame.draw.line(s, (78, 56, 36), (x + 1, stoss), (x + 14, stoss))
        s.set_at((x + 4, stoss - 2), (170, 162, 140))
        s.set_at((x + 11, stoss + 2), (170, 162, 140))
    _koerner(s, (148, 116, 80), 10, seed + 1)
    return s


def _feldstein_seite() -> pygame.Surface:
    """Feldsteinmauer von der Seite: runde graue Steine in Moertel, Moos
    in den Fugen."""
    r = random.Random(1401)
    s = _flaeche(T, T)
    s.fill((96, 94, 84))
    for gy in range(0, T, 8):
        x = -r.randrange(0, 6)
        while x < T:
            b = r.randrange(7, 12)
            ton = r.choice(((150, 146, 132), (134, 132, 120), (160, 154, 138), (122, 120, 112)))
            pygame.draw.ellipse(s, ton, (x, gy + 1, b, 7))
            pygame.draw.line(s, _ton(ton, 22), (x + 2, gy + 2), (x + b - 3, gy + 2))
            x += b + 1
    _koerner(s, (76, 104, 52), 18, 1402)
    return s


@platzhalter("feldstein")
def _feldstein():
    return _feldstein_seite()


@platzhalter("feldstein_oben")
def _feldstein_oben():
    """Mauerkrone aus Feldsteinen, mit Moos."""
    r = random.Random(1411)
    s = _flaeche(T, T)
    s.fill((92, 92, 82))
    for _ in range(14):
        x, y = r.randrange(-2, T - 6), r.randrange(-2, T - 6)
        b = r.randrange(7, 12)
        ton = r.choice(((158, 154, 140), (140, 138, 126), (168, 162, 146)))
        pygame.draw.ellipse(s, (70, 70, 62), (x, y + 1, b, b - 2))
        pygame.draw.ellipse(s, ton, (x, y, b, b - 2))
    for _ in range(4):
        x, y = r.randrange(1, T - 6), r.randrange(1, T - 5)
        pygame.draw.ellipse(s, (82, 112, 56), (x, y, r.randrange(3, 7), r.randrange(2, 4)))
    return s


def _moosfels_seite(seed) -> pygame.Surface:
    """Granit von der Seite: grau, Risse, Moos in Streifen."""
    r = random.Random(seed)
    s = _flaeche(T, T)
    s.fill((112, 114, 108))
    y = r.randrange(1, 5)
    while y < T:
        dick = r.randrange(4, 8)
        pygame.draw.rect(s, r.choice(((120, 122, 116), (104, 106, 100), (126, 126, 118))), (0, y, T, dick))
        y += dick + r.randrange(1, 3)
    for _ in range(4):
        x, y = r.randrange(2, T - 8), r.randrange(3, T - 3)
        pygame.draw.line(s, (70, 72, 68), (x, y), (x + r.randrange(3, 8), y + r.randrange(-2, 3)))
    for _ in range(3):
        x, y = r.randrange(0, T - 8), r.randrange(0, T - 4)
        pygame.draw.ellipse(s, (78, 108, 54), (x, y, r.randrange(5, 10), r.randrange(2, 4)))
    _koerner(s, (150, 150, 142), 16, seed + 1)
    return s


def _moosfels_oben_basis(seed) -> pygame.Surface:
    """Granit von oben: Platten, Risse, Moospolster und Flechten."""
    r = random.Random(seed)
    s = _flaeche(T, T)
    s.fill((128, 130, 122))
    for _ in range(r.randrange(4, 7)):
        x, y = r.randrange(-6, T - 6), r.randrange(-6, T - 6)
        pygame.draw.ellipse(s, r.choice(((138, 140, 132), (118, 120, 112), (144, 144, 136))),
                            (x, y, r.randrange(10, 20), r.randrange(8, 16)))
    for _ in range(r.randrange(2, 4)):
        x, y = r.randrange(2, T - 2), r.randrange(2, T - 2)
        for _i in range(r.randrange(2, 5)):
            nx = max(1, min(T - 2, x + r.randrange(-6, 7)))
            ny = max(1, min(T - 2, y + r.randrange(-6, 7)))
            pygame.draw.line(s, (84, 86, 80), (x, y), (nx, ny))
            x, y = nx, ny
    for _ in range(r.randrange(2, 5)):                 # Moospolster
        x, y = r.randrange(0, T - 9), r.randrange(0, T - 7)
        b, h = r.randrange(5, 11), r.randrange(4, 8)
        pygame.draw.ellipse(s, (60, 88, 44), (x, y + 1, b, h))
        pygame.draw.ellipse(s, (86, 120, 58), (x, y, b - 1, h - 1))
    for _ in range(r.randrange(1, 4)):
        x, y = r.randrange(2, T - 4), r.randrange(2, T - 4)
        pygame.draw.circle(s, (184, 180, 120), (x, y), 1)
    _koerner(s, (160, 160, 150), 12, seed + 1)
    return s


_reihe("moosfels", _moosfels_seite, (1421, 1427, 1433))
for _i, _saat in enumerate((1441, 1447, 1451)):
    platzhalter("moosfels_oben" if _i == 0 else "moosfels_%d_oben" % (_i + 1))(
        lambda saat=_saat: _moosfels_oben_basis(saat))


@platzhalter("baum")
def _baum():
    """Der Baum von der Seite: Laub, dazwischen Rinde - die Seite der
    stehenden Krone ist dunkelgruen."""
    s = _flaeche(T, T)
    s.fill((48, 78, 38))
    r = random.Random(1461)
    for _ in range(26):
        x, y = r.randrange(0, T - 4), r.randrange(0, T - 3)
        pygame.draw.ellipse(s, r.choice(((40, 66, 32), (62, 96, 46), (54, 86, 40))), (x, y, 5, 4))
    pygame.draw.rect(s, (84, 62, 42), (T // 2 - 2, T - 10, 4, 10))
    return s


@platzhalter("baum_oben")
def _baum_oben():
    """Eine Baumkrone von oben: dunkler Rand, Laubballen, Licht oben links."""
    b = 22
    s = _flaeche(b, b)
    m = b / 2.0
    r = random.Random(1471)
    pygame.draw.circle(s, (30, 52, 26), (b // 2, b // 2), b // 2)
    for _ in range(16):
        w = r.uniform(0, math.tau)
        d = r.uniform(0, m - 4)
        x, y = m + math.cos(w) * d, m + math.sin(w) * d
        rr = r.randrange(3, 5)
        pygame.draw.circle(s, r.choice(((48, 82, 38), (56, 92, 42), (44, 76, 34))), (round(x), round(y)), rr)
    for _ in range(8):
        w = r.uniform(math.pi * 0.9, math.pi * 1.6)
        d = r.uniform(2, m - 4)
        pygame.draw.circle(s, (86, 128, 60), (round(m + math.cos(w) * d), round(m + math.sin(w) * d)), 2)
    _koerner(s, (104, 146, 72), 0, 1)
    return s


_reihe("gras", _gras_basis, (1501, 1509, 1511, 1523))
_reihe("wiese", _wiese_basis, (1531, 1537, 1543, 1549))
_reihe("feldweg", _feldweg_basis, (1553, 1559, 1567, 1571))
_reihe("ufer", _ufer_basis, (1579, 1583, 1597, 1601))
_reihe("steg", _steg_basis, (1607, 1609))


# ──────────────────────────────── Satz stadt (KANALSTADT)

def _asphalt_basis(seed, grund=(68, 68, 72), risse=True) -> pygame.Surface:
    """Asphalt: feines Korn, ein paar Risse, mal ein Oelfleck."""
    r = random.Random(seed)
    s = _flaeche(T, T)
    s.fill(grund)
    _koerner(s, _ton(grund, 14), 34, seed + 1)
    _koerner(s, _ton(grund, -12), 30, seed + 2)
    if risse:
        for _ in range(r.randrange(0, 3)):
            x, y = r.randrange(4, T - 10), r.randrange(4, T - 6)
            for _i in range(r.randrange(2, 4)):
                nx, ny = x + r.randrange(2, 6), y + r.randrange(-3, 4)
                pygame.draw.line(s, _ton(grund, -26), (x, y), (nx, ny))
                x, y = nx, ny
    if r.random() < 0.25:
        x, y = r.randrange(4, T - 14), r.randrange(4, T - 10)
        pygame.draw.ellipse(s, _ton(grund, -14), (x, y, r.randrange(7, 12), r.randrange(5, 8)))
    return s


def _strasse_basis(seed) -> pygame.Surface:
    """Fahrbahn: dunkler als der Platz, Flickstellen, ab und zu ein
    Gullydeckel. Keine Mittellinie - dieselbe Kachel liegt in jeder
    Richtung."""
    r = random.Random(seed)
    s = _asphalt_basis(seed, (54, 54, 58))
    if r.random() < 0.4:
        x, y = r.randrange(3, T - 14), r.randrange(3, T - 12)
        pygame.draw.rect(s, (62, 62, 66), (x, y, r.randrange(8, 12), r.randrange(6, 10)))
    if r.random() < 0.18:
        x, y = r.randrange(6, T - 12), r.randrange(6, T - 12)
        pygame.draw.circle(s, (40, 40, 42), (x + 4, y + 4), 4)
        pygame.draw.circle(s, (78, 76, 74), (x + 4, y + 4), 4, 1)
        pygame.draw.line(s, (40, 40, 42), (x + 1, y + 4), (x + 7, y + 4))
    return s


def _gehweg_basis(seed) -> pygame.Surface:
    """Gehwegplatten: hellgrau, je Kachel vier Platten, eine mal gesprungen."""
    r = random.Random(seed)
    s = _flaeche(T, T)
    s.fill((112, 110, 106))
    for gx in (0, T // 2):
        for gy in (0, T // 2):
            ton = r.choice(((128, 126, 122), (122, 120, 116), (134, 132, 126)))
            pygame.draw.rect(s, ton, (gx + 1, gy + 1, T // 2 - 1, T // 2 - 1))
            pygame.draw.line(s, _ton(ton, 12), (gx + 1, gy + 1), (gx + T // 2 - 2, gy + 1))
    if r.random() < 0.5:
        x, y = r.randrange(3, T - 8), r.randrange(3, T - 8)
        pygame.draw.line(s, (92, 90, 88), (x, y), (x + r.randrange(3, 7), y + r.randrange(2, 6)))
    _koerner(s, (98, 96, 92), 14, seed + 1)
    return s


def _schutt_basis(seed) -> pygame.Surface:
    """Schutt: Staub, Ziegelbrocken, Betonstuecke, ein Draht."""
    r = random.Random(seed)
    s = _asphalt_basis(seed, (92, 88, 84), risse=False)
    for _ in range(r.randrange(8, 13)):
        x, y = r.randrange(1, T - 6), r.randrange(1, T - 5)
        b, h = r.randrange(2, 6), r.randrange(2, 4)
        ton = r.choice(((150, 86, 66), (132, 128, 120), (160, 156, 146), (118, 72, 56)))
        pygame.draw.rect(s, _ton(ton, -40), (x, y + 1, b, h))
        pygame.draw.rect(s, ton, (x, y, b, h))
    if r.random() < 0.35:
        x, y = r.randrange(3, T - 12), r.randrange(3, T - 6)
        pygame.draw.line(s, (60, 46, 40), (x, y), (x + 10, y + r.randrange(-3, 4)))
    return s


def _rasen_basis(seed) -> pygame.Surface:
    """Park: gepflegter Rasen, etwas heller, mit Maehstreifen."""
    s = _gras_basis(seed, (74, 104, 52), 0.15)
    for y in range(4, T - 4, 8):
        pygame.draw.line(s, (80, 112, 56), (3, y), (T - 4, y))
    return s


def _fliesen_basis(seed) -> pygame.Surface:
    """Fliesen im Haus: hell und dunkel im Wechsel, Staub darauf."""
    r = random.Random(seed)
    s = _flaeche(T, T)
    for gx in range(4):
        for gy in range(4):
            ton = (128, 122, 112) if (gx + gy) % 2 else (106, 100, 92)
            pygame.draw.rect(s, ton, (gx * 8, gy * 8, 8, 8))
    for _ in range(2):
        x, y = r.randrange(2, T - 8), r.randrange(2, T - 8)
        pygame.draw.line(s, (70, 66, 62), (x, y), (x + r.randrange(2, 6), y + r.randrange(2, 6)))
    _koerner(s, (128, 120, 110), 20, seed + 1)
    return s


@platzhalter("ziegel")
def _ziegel():
    """Ziegelmauer von der Seite: rote Steine im Verband, heller Moertel."""
    s = _flaeche(T, T)
    s.fill((148, 140, 128))
    r = random.Random(1701)
    for reihe, y in enumerate(range(0, T, 5)):
        versatz = 0 if reihe % 2 == 0 else 5
        for x in range(versatz - 10, T, 10):
            ton = r.choice(((150, 78, 58), (138, 70, 52), (162, 88, 64), (128, 64, 50)))
            pygame.draw.rect(s, ton, (x + 1, y + 1, 9, 4))
    _koerner(s, (176, 108, 84), 10, 1702)
    return s


@platzhalter("ziegel_oben")
def _ziegel_oben():
    """Das Dach von oben: Teerpappe mit Kies, Bahnen und Flicken. Ein Haus
    aus vielen Kacheln ist so ein Dach, keine Mauer aus lauter Steinen."""
    r = random.Random(1711)
    s = _flaeche(T, T)
    s.fill((70, 66, 64))
    _koerner(s, (96, 92, 88), 40, 1712)
    _koerner(s, (52, 50, 48), 30, 1713)
    if r.random() < 0.5:
        x, y = r.randrange(2, T - 12), r.randrange(2, T - 10)
        pygame.draw.rect(s, (80, 76, 72), (x, y, r.randrange(7, 11), r.randrange(5, 9)))
    return s


def _beton_seite(seed) -> pygame.Surface:
    """Beton von der Seite: grau, Schalbretter-Fugen, Rostfahnen."""
    r = random.Random(seed)
    s = _flaeche(T, T)
    s.fill((140, 140, 136))
    for y in range(6, T, 8):
        pygame.draw.line(s, (122, 122, 118), (0, y), (T - 1, y))
    for _ in range(r.randrange(1, 3)):
        x = r.randrange(2, T - 3)
        pygame.draw.line(s, (128, 92, 70), (x, r.randrange(0, 8)), (x, r.randrange(12, T)))
    _koerner(s, (160, 160, 154), 16, seed + 1)
    _koerner(s, (104, 104, 100), 16, seed + 2)
    return s


def _beton_oben_basis(seed) -> pygame.Surface:
    """Eine geborstene Betondecke von oben: Bruchkanten, Eisen, Staub."""
    r = random.Random(seed)
    s = _flaeche(T, T)
    s.fill((150, 150, 144))
    for _ in range(r.randrange(2, 4)):
        x, y = r.randrange(2, T - 2), r.randrange(2, T - 2)
        for _i in range(r.randrange(2, 5)):
            nx = max(1, min(T - 2, x + r.randrange(-7, 8)))
            ny = max(1, min(T - 2, y + r.randrange(-7, 8)))
            pygame.draw.line(s, (96, 96, 92), (x, y), (nx, ny))
            pygame.draw.line(s, (176, 176, 170), (x + 1, y), (nx + 1, ny))
            x, y = nx, ny
    for _ in range(r.randrange(1, 3)):                    # Bewehrung
        x, y = r.randrange(3, T - 10), r.randrange(3, T - 3)
        pygame.draw.line(s, (110, 70, 48), (x, y), (x + r.randrange(5, 10), y + r.randrange(-2, 3)))
    _koerner(s, (172, 170, 164), 14, seed + 1)
    _koerner(s, (118, 118, 112), 14, seed + 2)
    return s


_reihe("beton", _beton_seite, (1721, 1723, 1733))
for _i, _saat in enumerate((1741, 1747, 1753)):
    platzhalter("beton_oben" if _i == 0 else "beton_%d_oben" % (_i + 1))(
        lambda saat=_saat: _beton_oben_basis(saat))


def _truemmer_seite(seed) -> pygame.Surface:
    s = _beton_seite(seed)
    _koerner(s, (150, 86, 66), 14, seed + 5)
    return s


def _truemmer_oben_basis(seed, form) -> pygame.Surface:
    """Ein Truemmerbrocken von oben: kantiges Betonstueck, Licht oben links."""
    r = random.Random(seed)
    b = 26
    s = _flaeche(b, b)
    if form == 0:
        punkte = [(2, 6), (10, 1), (22, 3), (25, 14), (18, 24), (5, 22)]
    elif form == 1:
        punkte = [(1, 10), (8, 2), (24, 6), (23, 20), (11, 25), (2, 19)]
    else:
        punkte = [(4, 3), (20, 1), (25, 11), (21, 23), (6, 25), (1, 13)]
    pygame.draw.polygon(s, (88, 88, 84), punkte)
    innen = [(x + (13 - x) * 0.12, y + (13 - y) * 0.12) for x, y in punkte]
    pygame.draw.polygon(s, (148, 148, 142), innen)
    licht = [(x + (13 - x) * 0.45 - 2, y + (13 - y) * 0.45 - 2) for x, y in punkte]
    pygame.draw.polygon(s, (170, 170, 164), licht)
    x = r.randrange(6, 16)
    pygame.draw.line(s, (112, 72, 50), (x, 6), (x + r.randrange(-3, 4), 18))
    _koerner(s, (120, 120, 114), 0, 1)
    return s


_reihe("truemmer", _truemmer_seite, (1761, 1763, 1767))
for _i, _saat in enumerate((1771, 1777, 1783)):
    platzhalter("truemmer_oben" if _i == 0 else "truemmer_%d_oben" % (_i + 1))(
        lambda saat=_saat, form=_i: _truemmer_oben_basis(saat, form))


_WRACK_LACK = ((132, 52, 44), (70, 86, 100), (98, 104, 66))


def _wrack_seite(seed) -> pygame.Surface:
    """Ein ausgebranntes Auto von der Seite: Lack, Rost, Russ."""
    r = random.Random(seed)
    lack = _WRACK_LACK[seed % 3]
    s = _flaeche(T, T)
    s.fill(lack)
    for _ in range(5):
        x, y = r.randrange(0, T - 10), r.randrange(0, T - 6)
        pygame.draw.rect(s, r.choice(((112, 64, 40), (54, 46, 42), _ton(lack, -20))),
                         (x, y, r.randrange(5, 12), r.randrange(3, 7)))
    _koerner(s, (40, 34, 30), 18, seed + 1)
    return s


def _wrack_oben_basis(seed) -> pygame.Surface:
    """Das Autowrack von oben: Karosserie mit Haube, eingeschlagener
    Scheibe und Dach, Lack, Rost und Russ - drei Farben, damit ein Stau
    aus Wracks nicht aussieht wie eine Reihe gleicher Kaesten."""
    r = random.Random(seed)
    lack = _WRACK_LACK[seed % 3]
    b, h = 24, 30
    s = _flaeche(b, h)
    pygame.draw.rect(s, (30, 26, 24), s.get_rect(), border_radius=5)
    pygame.draw.rect(s, lack, (1, 1, b - 2, h - 2), border_radius=5)
    pygame.draw.line(s, _ton(lack, 24), (3, 2), (b - 4, 2))
    pygame.draw.rect(s, (44, 52, 60), (4, 8, b - 8, 5))                 # Frontscheibe
    pygame.draw.line(s, (150, 170, 176), (5, 9), (10, 12))
    pygame.draw.rect(s, _ton(lack, -18), (4, 13, b - 8, 10))            # Dach
    pygame.draw.rect(s, (44, 52, 60), (4, 23, b - 8, 3))                # Heckscheibe
    for _ in range(5):                                                  # Rost und Russ
        x, y = r.randrange(1, b - 6), r.randrange(1, h - 5)
        pygame.draw.ellipse(s, r.choice(((112, 64, 40), (40, 34, 30))), (x, y, 5, 3))
    return s


_reihe("wrack", _wrack_seite, (1801, 1802, 1803))
for _i, _saat in enumerate((1811, 1812, 1813)):
    platzhalter("wrack_oben" if _i == 0 else "wrack_%d_oben" % (_i + 1))(
        lambda saat=_saat: _wrack_oben_basis(saat))

_reihe("asphalt", _asphalt_basis, (1821, 1823, 1831, 1847))
_reihe("strasse", _strasse_basis, (1851, 1861, 1867, 1871))
_reihe("gehweg", _gehweg_basis, (1873, 1877, 1879))
_reihe("schutt", _schutt_basis, (1889, 1901, 1907, 1913))
_reihe("rasen", _rasen_basis, (1931, 1933, 1949, 1951))
_reihe("fliesen", _fliesen_basis, (1973, 1979))


def _platz_basis(seed) -> pygame.Surface:
    """Der Kasernenhof (Gitter im Satz stadt): grosse Betonplatten mit
    Dehnfugen am Rand, Reifenspuren, hier und da Oel."""
    r = random.Random(seed)
    s = _flaeche(T, T)
    grund = (104, 108, 100)
    s.fill(grund)
    pygame.draw.line(s, (78, 80, 74), (0, 0), (T - 1, 0))
    pygame.draw.line(s, (78, 80, 74), (0, 0), (0, T - 1))
    pygame.draw.line(s, (122, 126, 118), (1, 1), (T - 2, 1))
    _koerner(s, (118, 122, 114), 26, seed + 1)
    _koerner(s, (88, 90, 84), 22, seed + 2)
    if r.random() < 0.4:
        y = r.randrange(6, T - 8)
        pygame.draw.line(s, (88, 90, 86), (3, y), (T - 4, y + r.randrange(-2, 3)))
    if r.random() < 0.2:
        x, y = r.randrange(4, T - 12), r.randrange(4, T - 10)
        pygame.draw.ellipse(s, (82, 84, 80), (x, y, 9, 6))
    return s


_reihe("kasernenplatz", _platz_basis, (1991, 1993, 1997))
# Seichtes Wasser im Kanal: trueb, mit Schlick und Truemmersplittern.
_reihe("kanal_seicht", lambda saat: _seicht_basis(saat, (54, 82, 84),
                                                  ((86, 86, 80), (70, 72, 68), (110, 70, 56)),
                                                  (110, 136, 132)), (2003, 2011, 2017))
