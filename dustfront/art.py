"""
DUSTFRONT - Platzhalter-Grafik
==============================

Jedes Bild, das das Spiel braucht, wird hier im Code gezeichnet. Legt man
spaeter eine Datei `assets/<name>.png` daneben, nimmt die Registratur die
Datei und ruft den Zeichner hier gar nicht erst auf.

Damit Drehen funktioniert, schauen alle Figuren nach rechts (0 Grad) und
sitzen mittig auf einer quadratischen Flaeche.

Massstab: eine Kachel ist 32x32, eine Figur etwa 24x24.
"""

from __future__ import annotations

import random

import pygame

from . import config as K
from .core import platzhalter

T = K.TILE


def _flaeche(w, h) -> pygame.Surface:
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _koerner(surf, farbe, menge, seed):
    r = random.Random(seed)
    w, h = surf.get_size()
    for _ in range(menge):
        surf.set_at((r.randrange(w), r.randrange(h)), farbe)


# ──────────────────────────────── Kacheln

@platzhalter("leer")
def _leer():
    s = _flaeche(T, T)
    s.fill((0, 0, 0, 0))
    return s


def _boden_basis(seed, grund, fuge, platte=True):
    """Bodenplatte. Die Fuge ist bewusst schwach, sonst sieht die Karte aus
    wie Rechenpapier. Die Abwechslung kommt aus Korn und Kleinkram."""
    r = random.Random(seed)
    ton = tuple(max(0, min(255, c + r.randrange(-2, 3))) for c in grund)
    s = _flaeche(T, T)
    s.fill(ton)
    if platte:
        pygame.draw.line(s, fuge, (0, 0), (T - 1, 0))
        pygame.draw.line(s, fuge, (0, 0), (0, T - 1))
        pygame.draw.line(s, (ton[0] + 8, ton[1] + 7, ton[2] + 5), (1, 1), (T - 2, 1))
    for _ in range(r.randrange(2, 5)):
        x, y = r.randrange(2, T - 7), r.randrange(3, T - 3)
        pygame.draw.rect(s, K.C_FUGE, (x, y, r.randrange(3, 7), 1))
    if r.random() < 0.5:                      # Niete
        x, y = r.randrange(4, T - 5), r.randrange(4, T - 5)
        pygame.draw.rect(s, (ton[0] + 16, ton[1] + 13, ton[2] + 9), (x, y, 2, 2))
        pygame.draw.rect(s, K.C_FUGE, (x, y + 2, 2, 1))
    if r.random() < 0.3:                      # groesserer Fleck
        x, y = r.randrange(3, T - 12), r.randrange(3, T - 10)
        pygame.draw.ellipse(s, (ton[0] - 6, ton[1] - 5, ton[2] - 4),
                            (x, y, r.randrange(6, 11), r.randrange(4, 8)))
    _koerner(s, K.C_MUTED_DK, 22, seed)
    _koerner(s, K.C_FUGE, 26, seed + 1)
    _koerner(s, (ton[0] + 14, ton[1] + 12, ton[2] + 9), 10, seed + 2)
    return s


@platzhalter("boden")
def _boden():
    return _boden_basis(11, K.C_BODEN, K.C_FUGE)


@platzhalter("boden_2")
def _boden2():
    return _boden_basis(12, K.C_BODEN, K.C_FUGE)


@platzhalter("boden_3")
def _boden3():
    return _boden_basis(31, K.C_BODEN, K.C_FUGE)


@platzhalter("boden_4")
def _boden4():
    return _boden_basis(47, K.C_BODEN, K.C_FUGE)


@platzhalter("gitter")
def _gitter():
    s = _boden_basis(13, K.C_BODEN_2, K.C_FUGE)
    for i in range(2, T, 6):
        pygame.draw.line(s, (26, 20, 15), (i, 1), (i, T - 2))
    for i in range(2, T, 6):
        pygame.draw.line(s, (60, 48, 36), (1, i), (T - 2, i))
    return s


@platzhalter("wand")
def _wand():
    s = _flaeche(T, T)
    s.fill(K.C_WAND)
    pygame.draw.rect(s, K.C_WAND_OBEN, (0, 0, T, 5))
    pygame.draw.rect(s, K.C_WAND_KANTE, (0, T - 3, T, 3))
    for x in (0, T // 2):
        pygame.draw.line(s, K.C_WAND_KANTE, (x, 5), (x, T - 4))
    pygame.draw.line(s, (78, 64, 48), (1, 6), (T - 2, 6))
    _koerner(s, (52, 42, 31), 30, 21)
    _koerner(s, (104, 86, 64), 12, 22)
    return s


@platzhalter("kiste")
def _kiste():
    """Schwerer Frachtkasten. Steht auf dem Boden, deshalb eine Kachel gross
    mit umlaufender Kante, damit er sich klar vom Untergrund abhebt."""
    s = _boden_basis(14, K.C_BODEN, K.C_FUGE)
    k = pygame.Rect(3, 2, T - 6, T - 5)
    pygame.draw.rect(s, (22, 16, 11), k.move(0, 2))          # eigener Schatten
    pygame.draw.rect(s, K.C_HULL_DK, k)
    pygame.draw.rect(s, K.C_HULL, k.inflate(-6, -6))
    pygame.draw.rect(s, (196, 178, 136), (k.left + 3, k.top + 3, k.width - 6, 2))
    pygame.draw.rect(s, (22, 16, 11), k, 1)
    # Eckwinkel
    for ex in (k.left + 1, k.right - 4):
        for ey in (k.top + 1, k.bottom - 4):
            pygame.draw.rect(s, K.C_HULL_SH, (ex, ey, 3, 3))
    # Spannband und Kennzeichnung
    pygame.draw.rect(s, K.C_HULL_SH, (k.left + 1, k.centery - 1, k.width - 2, 3))
    pygame.draw.rect(s, (150, 132, 96), (k.left + 1, k.centery - 1, k.width - 2, 1))
    pygame.draw.rect(s, K.C_AMBER, (k.left + 4, k.top + 6, 5, 2))
    _koerner(s, K.C_HULL_SH, 14, 55)
    return s


def _treppe(pfeil_hoch: bool):
    s = _boden_basis(15, K.C_BODEN_2, K.C_FUGE)
    for i in range(4):
        y = 4 + i * 7
        pygame.draw.rect(s, (58, 46, 34), (3, y, T - 6, 5))
        pygame.draw.line(s, (92, 76, 56), (3, y), (T - 4, y))
    mitte = T // 2
    farbe = K.C_TEAL if pfeil_hoch else K.C_AMBER
    spitze = 6 if pfeil_hoch else T - 7
    fuss = T - 9 if pfeil_hoch else 8
    pygame.draw.polygon(s, farbe, [(mitte, spitze), (mitte - 5, spitze + (5 if pfeil_hoch else -5)),
                                   (mitte + 5, spitze + (5 if pfeil_hoch else -5))])
    pygame.draw.rect(s, farbe, (mitte - 1, min(spitze, fuss), 3, abs(fuss - spitze)))
    return s


@platzhalter("treppe_hoch")
def _treppe_hoch():
    return _treppe(True)


@platzhalter("treppe_runter")
def _treppe_runter():
    return _treppe(False)


@platzhalter("luke")
def _luke():
    s = _boden_basis(16, K.C_BODEN, K.C_FUGE)
    r = pygame.Rect(5, 5, T - 10, T - 10)
    pygame.draw.rect(s, (24, 18, 13), r)
    pygame.draw.rect(s, K.C_HULL_SH, r, 1)
    pygame.draw.circle(s, K.C_AMBER, (T // 2, T // 2), 3, 1)
    pygame.draw.line(s, K.C_HULL_DK, (r.left + 2, r.top + 2), (r.right - 3, r.bottom - 3))
    return s


# ──────────────────────────────── Figuren

def _rand(s, farbe=(16, 11, 8)):
    """Zieht eine dunkle Linie um alles Undurchsichtige. Ohne das versinken
    die Figuren im Boden."""
    w, h = s.get_size()
    maske = pygame.mask.from_surface(s)
    rand = _flaeche(w, h)
    for x, y in maske.outline():
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not maske.get_at((nx, ny)):
                rand.set_at((nx, ny), farbe)
    rand.blit(s, (0, 0))
    return rand


def _figur(groesse, rumpf, rumpf_dk, akzent, breit=False):
    """Draufsicht: Schultern quer, Kopf mittig, Waffe nach rechts."""
    s = _flaeche(groesse, groesse)
    c = groesse // 2
    hell = tuple(min(255, k + 34) for k in rumpf)
    schulter = pygame.Rect(c - 7, c - (9 if breit else 8), 14, (18 if breit else 16))
    pygame.draw.ellipse(s, rumpf_dk, schulter)
    pygame.draw.ellipse(s, rumpf, schulter.inflate(-3, -3))
    pygame.draw.ellipse(s, hell, schulter.inflate(-3, -3).move(0, -2), 1)
    # Arme nach vorn
    pygame.draw.line(s, rumpf_dk, (c + 1, c - 5), (c + 8, c - 3), 3)
    pygame.draw.line(s, rumpf_dk, (c + 1, c + 5), (c + 8, c + 3), 3)
    # Waffe
    pygame.draw.rect(s, (30, 25, 19), (c + 6, c - 2, 12, 4))
    pygame.draw.rect(s, (86, 72, 52), (c + 6, c - 1, 10, 2))
    # Kopf
    pygame.draw.circle(s, rumpf_dk, (c + 1, c), 5)
    pygame.draw.circle(s, hell, (c + 1, c), 4)
    pygame.draw.circle(s, akzent, (c + 3, c), 2)
    return _rand(s)


@platzhalter("spieler")
def _spieler():
    return _figur(28, K.C_HULL, K.C_HULL_SH, K.C_TEAL)


@platzhalter("gegner_laeufer")
def _gegner_laeufer():
    return _figur(28, (128, 84, 58), (58, 36, 24), K.C_ORANGE)


@platzhalter("gegner_brecher")
def _gegner_brecher():
    s = _figur(36, (112, 70, 48), (48, 30, 20), K.C_RED, breit=True)
    c = 18
    pygame.draw.rect(s, (74, 48, 32), (c - 9, c - 12, 18, 4))
    pygame.draw.rect(s, K.C_RUST, (c - 8, c - 11, 16, 2))
    return s


# ──────────────────────────────── Kleinkram

@platzhalter("geschoss")
def _geschoss():
    s = _flaeche(8, 4)
    pygame.draw.rect(s, (120, 74, 28), (0, 1, 8, 2))
    pygame.draw.rect(s, K.C_AMBER, (3, 1, 5, 2))
    pygame.draw.rect(s, (255, 238, 196), (6, 1, 2, 2))
    return s


@platzhalter("muendung")
def _muendung():
    s = _flaeche(20, 20)
    pygame.draw.polygon(s, (255, 226, 160), [(2, 10), (13, 6), (19, 10), (13, 14)])
    pygame.draw.polygon(s, K.C_AMBER, [(2, 10), (11, 7), (16, 10), (11, 13)])
    pygame.draw.circle(s, (255, 244, 214), (5, 10), 3)
    return s


@platzhalter("medkit")
def _medkit():
    s = _flaeche(16, 14)
    pygame.draw.rect(s, (28, 22, 16), (0, 2, 16, 12))
    pygame.draw.rect(s, (214, 210, 196), (1, 3, 14, 10))
    pygame.draw.rect(s, (168, 162, 148), (1, 10, 14, 3))
    pygame.draw.rect(s, K.C_RED, (6, 5, 4, 6))
    pygame.draw.rect(s, K.C_RED, (4, 7, 8, 2))
    pygame.draw.rect(s, (60, 50, 38), (5, 0, 6, 3))
    return _rand(s, (18, 13, 9))


@platzhalter("granate")
def _granate():
    s = _flaeche(10, 10)
    pygame.draw.ellipse(s, (54, 62, 44), (1, 1, 8, 8))
    pygame.draw.ellipse(s, (78, 88, 62), (2, 2, 5, 5))
    pygame.draw.rect(s, (40, 34, 24), (4, 0, 3, 3))
    pygame.draw.rect(s, K.C_AMBER, (4, 1, 2, 1))
    return _rand(s, (16, 12, 8))


@platzhalter("huelse")
def _huelse():
    s = _flaeche(4, 3)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (146, 112, 46), (0, 0, 4, 3))
    pygame.draw.rect(s, (206, 168, 82), (0, 0, 3, 1))
    return s


# ──────────────────────────────── Waffensymbole
#
# Kleine Seitenansichten fuer Hotbar und Inventar. Sie muessen auf 26 mal 11
# Pixel erkennbar sein, also zaehlt nur die Silhouette: Laenge des Laufs,
# Dicke des Gehaeuses, was oben und was unten heraussteht. Farbe traegt hier
# fast nichts, Form alles.

_W_ST = (44, 37, 29)          # Stahl dunkel
_W_ST_H = (108, 95, 74)       # Stahl hell
_W_HOLZ = (96, 62, 34)        # Schaft
_W_HOLZ_H = (134, 92, 54)


def _waffe(breite=26, hoehe=11):
    return _flaeche(breite, hoehe)


@platzhalter("waffe_repetierer")
def _waffe_repetierer():
    s = _waffe()
    pygame.draw.rect(s, _W_HOLZ, (1, 5, 9, 4))          # Schaft
    pygame.draw.rect(s, _W_HOLZ_H, (1, 5, 9, 1))
    pygame.draw.rect(s, _W_ST, (9, 4, 7, 4))            # Verschluss
    pygame.draw.rect(s, _W_ST_H, (9, 4, 7, 1))
    pygame.draw.rect(s, _W_ST, (16, 5, 9, 2))           # Lauf
    pygame.draw.rect(s, _W_ST_H, (16, 5, 9, 1))
    pygame.draw.rect(s, _W_ST, (14, 2, 2, 3))           # Kammerstengel
    pygame.draw.rect(s, _W_ST, (11, 8, 2, 3))           # Abzugsbuegel
    return s


@platzhalter("waffe_sturm")
def _waffe_sturm():
    s = _waffe()
    pygame.draw.rect(s, _W_ST, (1, 4, 6, 3))            # Schulterstuetze
    pygame.draw.rect(s, _W_ST, (7, 3, 10, 5))           # Gehaeuse
    pygame.draw.rect(s, _W_ST_H, (7, 3, 10, 1))
    pygame.draw.rect(s, _W_ST, (8, 1, 7, 2))            # Tragegriff
    pygame.draw.rect(s, _W_ST, (17, 4, 8, 2))           # Lauf
    pygame.draw.rect(s, _W_ST_H, (17, 4, 8, 1))
    pygame.draw.rect(s, (60, 52, 40), (10, 8, 4, 3))    # Magazin
    pygame.draw.rect(s, K.C_AMBER, (10, 10, 4, 1))
    pygame.draw.rect(s, _W_ST, (15, 8, 2, 2))
    return s


@platzhalter("waffe_schrot")
def _waffe_schrot():
    s = _waffe()
    pygame.draw.rect(s, _W_HOLZ, (1, 5, 8, 5))          # dicker Schaft
    pygame.draw.rect(s, _W_HOLZ_H, (1, 5, 8, 1))
    pygame.draw.rect(s, _W_ST, (9, 4, 5, 4))
    pygame.draw.rect(s, _W_ST, (14, 3, 11, 3))          # Lauf oben
    pygame.draw.rect(s, _W_ST_H, (14, 3, 11, 1))
    pygame.draw.rect(s, (66, 56, 44), (14, 6, 9, 2))    # Vorderschaft
    pygame.draw.rect(s, _W_ST, (10, 8, 2, 3))
    return s


@platzhalter("waffe_scharf")
def _waffe_scharf():
    s = _waffe()
    pygame.draw.rect(s, _W_HOLZ, (0, 5, 8, 4))
    pygame.draw.rect(s, _W_HOLZ_H, (0, 5, 8, 1))
    pygame.draw.rect(s, _W_ST, (8, 4, 6, 4))
    pygame.draw.rect(s, _W_ST, (14, 5, 12, 2))          # sehr langer Lauf
    pygame.draw.rect(s, _W_ST_H, (14, 5, 12, 1))
    pygame.draw.rect(s, (30, 26, 20), (9, 1, 9, 3))     # Zielfernrohr
    pygame.draw.rect(s, K.C_TEAL_DK, (16, 2, 2, 1))     # Linse
    pygame.draw.rect(s, _W_ST, (20, 7, 1, 4))           # Zweibein
    pygame.draw.rect(s, _W_ST, (23, 7, 1, 4))
    pygame.draw.rect(s, _W_ST, (10, 8, 2, 3))
    return s


@platzhalter("waffe_granate")
def _waffe_granate():
    s = _waffe()
    pygame.draw.ellipse(s, (54, 62, 44), (8, 2, 10, 8))
    pygame.draw.ellipse(s, (78, 88, 62), (10, 3, 5, 4))
    for y in (4, 7):                                     # Rillen
        pygame.draw.rect(s, (38, 44, 32), (9, y, 8, 1))
    pygame.draw.rect(s, (40, 34, 24), (12, 0, 3, 3))    # Zuender
    pygame.draw.rect(s, K.C_AMBER, (12, 1, 2, 1))
    pygame.draw.rect(s, (92, 80, 60), (15, 1, 4, 1))    # Buegel
    return s


@platzhalter("waffe_brecheisen")
def _waffe_brecheisen():
    s = _waffe()
    for x in range(4, 22):                               # Schaft, leicht schraeg
        pygame.draw.rect(s, K.C_RUST, (x, 7 - (x - 4) // 5, 1, 2))
    pygame.draw.rect(s, (188, 82, 44), (4, 7, 16, 1))
    pygame.draw.polygon(s, K.C_RUST, [(21, 4), (25, 2), (25, 4), (22, 6)])
    pygame.draw.rect(s, K.C_RUST, (2, 6, 3, 4))          # gebogenes Ende
    pygame.draw.rect(s, (60, 26, 14), (2, 9, 3, 1))
    return s
