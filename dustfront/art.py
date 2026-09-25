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

import math
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


def _hand_waffe(s, c, name):
    """Zeichnet die getragene Waffe von oben, ab der Hand nach rechts.

    Von oben sieht man von einer Waffe fast nur den Umriss. Laenge und
    Dicke kommen deshalb aus K.WAFFEN_HAND, hier steht nur, wie daraus
    Pixel werden. Die Hand sitzt bei x = c + 6.
    """
    d = K.WAFFEN_HAND.get(name)
    if d is None:
        return
    hand = c + 6
    # Deutlich heller als der Boden (K.C_BODEN), sonst verschwindet die
    # Waffe darin - erkennen soll man sie ja auf einen Blick.
    stahl, stahl_h = (92, 82, 64), (146, 132, 104)
    if d["aufbau"] == "kugel":                    # Granate: nichts als Kugel
        pygame.draw.circle(s, (70, 82, 56), (hand + 4, c), 5)
        pygame.draw.circle(s, (104, 118, 80), (hand + 3, c - 1), 3)
        pygame.draw.rect(s, (52, 44, 32), (hand + 2, c - 7, 4, 3))
        pygame.draw.rect(s, K.C_AMBER, (hand + 3, c - 6, 2, 1))
        return

    if d["aufbau"] == "haken":                    # Brecheisen: roher Stab
        laenge, dick = d["lauf"], d["dicke"]
        pygame.draw.rect(s, K.C_RUST, (hand - d["schaft"], c - dick // 2 - 1,
                                       d["schaft"] + laenge, dick + 1))
        pygame.draw.rect(s, (188, 82, 44), (hand - d["schaft"], c - dick // 2 - 1,
                                            d["schaft"] + laenge, 1))
        pygame.draw.polygon(s, K.C_RUST, [(hand + laenge - 2, c - 3),
                                          (hand + laenge + 2, c - 5),
                                          (hand + laenge + 2, c - 2),
                                          (hand + laenge - 1, c + 1)])
        return

    # Schaft hinter der Hand
    sd = d["s_dicke"]
    schaft_farbe = _W_HOLZ if d["holz"] else stahl
    schaft_hell = _W_HOLZ_H if d["holz"] else stahl_h
    pygame.draw.rect(s, schaft_farbe, (hand - d["schaft"], c - sd // 2,
                                       d["schaft"] + 3, sd))
    pygame.draw.rect(s, schaft_hell, (hand - d["schaft"], c - sd // 2,
                                      d["schaft"] + 3, 1))
    # Lauf nach vorn
    dd = d["dicke"]
    pygame.draw.rect(s, stahl, (hand, c - dd // 2, d["lauf"], dd))
    pygame.draw.rect(s, stahl_h, (hand, c - dd // 2, d["lauf"], 1))

    if d["aufbau"] == "kammer":                   # Kammerstengel quer
        pygame.draw.rect(s, stahl_h, (hand - 1, c + 2, 3, 4))
    elif d["aufbau"] == "magazin":                # Magazin unter dem Gehaeuse
        pygame.draw.rect(s, (60, 52, 40), (hand - 3, c + 3, 5, 5))
        pygame.draw.rect(s, K.C_AMBER, (hand - 3, c + 7, 5, 1))
    elif d["aufbau"] == "doppel":                 # zweiter Lauf daneben
        pygame.draw.rect(s, stahl, (hand, c - dd // 2 - 3, d["lauf"] - 2, 2))
        pygame.draw.rect(s, stahl_h, (hand, c - dd // 2 - 3, d["lauf"] - 2, 1))
    elif d["aufbau"] == "fernrohr":               # Zielfernrohr obenauf
        pygame.draw.rect(s, (52, 46, 38), (hand - 4, c - 4, 12, 4))
        pygame.draw.rect(s, (120, 110, 92), (hand - 4, c - 4, 12, 1))
        pygame.draw.rect(s, K.C_TEAL, (hand + 7, c - 3, 1, 2))


def _figur(groesse, rumpf, rumpf_dk, akzent, breit=False, waffe=None):
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
    # Waffe: entweder die benannte aus der Tabelle oder der alte Stummel
    if waffe is not None:
        _hand_waffe(s, c, waffe)
    else:
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


# Eine Figur je Waffe. Damit sieht man der Gestalt an, was sie traegt,
# ohne in die Hotbar zu schauen. Registriert wird ueber eine Schleife: eine
# siebte Waffe in WAFFEN_HAND bekommt ihre Figur dadurch von selbst.
def _spieler_mit(waffe):
    def zeichner():
        gross = K.BILD_MASS["spieler_" + waffe][0]
        return _figur(gross, K.C_HULL, K.C_HULL_SH, K.C_TEAL, waffe=waffe)
    return zeichner


for _waffe in K.WAFFEN_HAND:
    platzhalter("spieler_" + _waffe)(_spieler_mit(_waffe))


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


# ──────────────────────────────── Schatten und Dekale
#
# Diese fuenf sitzen nicht auf einer Kachel und haben keine feste Groesse:
# das Spiel rechnet sie von ihrem Basismass auf das um, was es gerade
# braucht. Wer sie ersetzt, malt deshalb eine Form, keine feste Groesse.
# Welcher Wert zum Basismass gehoert, steht in K.DEKAL.

@platzhalter("schatten")
def _schatten():
    """Weicher Fleck unter jedem Wesen. Drei gestaffelte Ovale, damit der
    Rand ausfranst statt hart abzubrechen."""
    w, h = K.BILD_MASS["schatten"]
    s = _flaeche(w, h)
    innen = pygame.Rect(2, 2, w - 4, h - 4)
    pygame.draw.ellipse(s, (0, 0, 0, 42), innen.inflate(4, 3))
    pygame.draw.ellipse(s, (0, 0, 0, 78), innen)
    pygame.draw.ellipse(s, (0, 0, 0, 104), innen.inflate(-4, -2))
    return s


@platzhalter("blut")
def _blut():
    """Was liegen bleibt, wo ein Wesen gestorben ist."""
    w, h = K.BILD_MASS["blut"]
    s = _flaeche(w, h)
    r = random.Random(9)
    for _ in range(14):
        x, y = r.randrange(4, w - 4), r.randrange(4, h - 4)
        pygame.draw.circle(s, (*K.C_BLUT, r.randrange(70, 150)), (x, y),
                           r.randrange(1, 5))
    return s


@platzhalter("brandfleck")
def _brandfleck():
    """Russfleck, den eine Granate hinterlaesst. Dicht in der Mitte, nach
    aussen immer duenner, damit kein Kreis mit hartem Rand entsteht."""
    w, h = K.BILD_MASS["brandfleck"]
    r = w // 2
    s = _flaeche(w, h)
    rnd = random.Random(r)
    for _ in range(int(r * 1.8)):
        winkel = rnd.uniform(0, 6.283)
        ab = rnd.uniform(0, 1.0) ** 0.6 * r
        x = int(r + math.cos(winkel) * ab)
        y = int(r + math.sin(winkel) * ab)
        dunkelheit = int(150 * (1.0 - ab / r))
        pygame.draw.circle(s, (14, 10, 8, dunkelheit), (x, y),
                           rnd.randrange(2, 7))
    return s


@platzhalter("wandschatten")
def _wandschatten():
    """Schlagschatten, den eine feste Kachel auf den Boden wirft.
    Licht kommt von oben links, also faellt er nach unten rechts."""
    versatz = K.DEKAL["wand_versatz"]
    s = _flaeche(T + versatz, T + versatz)
    for i in range(versatz):
        a = int(96 * (1 - i / versatz) ** 1.4)
        pygame.draw.rect(s, (0, 0, 0, a), (i, i, T, T))
    return s


@platzhalter("vignette")
def _vignette():
    """Abdunkelung zum Bildrand hin. Liegt ueber allem, auch ueber dem HUD
    nicht - sie wird vor dem HUD gezeichnet."""
    s = _flaeche(K.GAME_W, K.GAME_H)
    rand = 74
    for i in range(rand):
        a = int(88 * (1 - i / rand) ** 2)
        if a <= 0:
            continue
        pygame.draw.rect(s, (0, 0, 0, a), (i, i, K.GAME_W - 2 * i,
                                           K.GAME_H - 2 * i), 1)
    return s


# ──────────────────────────────── Der Rumpf
#
# Ein Deck muss sich auf einen Blick von Wasteland unterscheiden, auch wenn
# beide Kacheln nebeneinander liegen - sonst weiss man beim Absteigen nicht,
# wann man die Maschine verlassen hat. Dafuer sorgen drei Dinge:
#
#   Farbe    kuehler und grauer. Draussen Staub und Rost, drinnen Stahl.
#   Muster   Traenenblech statt gestreuter Flecken: gefertigt, nicht gewachsen.
#   Kante    umlaufende Plattenfuge mit Nieten, regelmaessig statt zufaellig.
#
# Das Korn bleibt, sonst wirkt der Stahl wie Plastik. Aber es liegt duenner
# darauf als beim Boden: benutzt, nicht verfallen.

def _niete(s, x, y, hell=K.C_STAHL, dunkel=K.C_DECK_FUGE):
    """Eine Niete: zwei helle Punkte, darunter ein Schatten. Drei Pixel,
    und die Flaeche sieht verschraubt aus statt gemalt."""
    pygame.draw.rect(s, hell, (x, y, 2, 2))
    pygame.draw.rect(s, dunkel, (x, y + 2, 2, 1))
    s.set_at((x, y), tuple(min(255, k + 34) for k in hell))


def _stollen(s, x, y, hell, mitte, dunkel):
    """Ein Stollen im Riffelblech, von oben gesehen.

    Drei mal drei Pixel: oben links das Licht, unten rechts der Schatten,
    dazwischen die Flaeche. Das ist die kleinste Form, die sich wirklich
    als Erhebung liest - eine einfarbige Raute sieht aus wie ein Fleck,
    und lange schraege Rippen legen sich zu Wellen zusammen.

    Das Licht kommt von oben links, wie ueberall im Spiel (siehe
    `_wandschatten`).
    """
    w, h = s.get_size()
    def setz(px, py, farbe):
        if 0 <= px < w and 0 <= py < h:
            s.set_at((px, py), farbe)
    setz(x + 1, y, hell)
    setz(x, y + 1, hell)
    setz(x + 1, y + 1, mitte)
    setz(x + 2, y + 1, mitte)
    setz(x + 1, y + 2, mitte)
    setz(x + 2, y + 2, dunkel)
    setz(x + 2, y, dunkel)
    setz(x, y + 2, dunkel)


def _deck_basis(seed, grund=None, muster=True, nieten=True):
    """Eine Rumpfplatte. Grundlage jeder Kachel an Bord."""
    r = random.Random(seed)
    grund = grund or K.C_DECK
    ton = tuple(max(0, min(255, c + r.randrange(-2, 3))) for c in grund)
    s = _flaeche(T, T)
    s.fill(ton)

    hell = tuple(min(255, k + 20) for k in ton)
    dunkel = tuple(max(0, k - 14) for k in ton)

    if muster:                                  # Riffelblech, versetztes Raster
        # Festes Raster ohne Zufallsversatz: gefertigte Flaechen sind
        # regelmaessig, und jeder Wackler daran sieht nach Schmutz aus
        # statt nach Blech. Die Abwechslung zwischen den Kacheln kommt aus
        # der Phase, nicht aus verrutschten Stollen.
        phase = seed % 2
        st_hell = tuple(min(255, k + 24) for k in ton)
        st_mitte = tuple(min(255, k + 9) for k in ton)
        st_dunkel = tuple(max(0, k - 13) for k in ton)
        for gy in range(-1, T // 6 + 2):
            for gx in range(-1, T // 6 + 2):
                x = gx * 6 + (3 if (gy + phase) % 2 else 0)
                y = gy * 6 + 4
                _stollen(s, x, y, st_hell, st_mitte, st_dunkel)

    # Umlaufende Plattenfuge: oben und links dunkel, eine Zeile darunter hell.
    pygame.draw.line(s, K.C_DECK_FUGE, (0, 0), (T - 1, 0))
    pygame.draw.line(s, K.C_DECK_FUGE, (0, 0), (0, T - 1))
    pygame.draw.line(s, hell, (1, 1), (T - 2, 1))
    pygame.draw.line(s, tuple(max(0, k - 6) for k in ton), (0, T - 1), (T - 1, T - 1))

    if nieten:
        for nx, ny in ((2, 3), (T - 5, 3), (2, T - 6), (T - 5, T - 6)):
            _niete(s, nx, ny)

    if r.random() < 0.28:                       # Oelfleck oder Abrieb
        x, y = r.randrange(6, T - 12), r.randrange(6, T - 10)
        pygame.draw.ellipse(s, tuple(max(0, k - 9) for k in ton),
                            (x, y, r.randrange(6, 11), r.randrange(4, 7)))
    if r.random() < 0.22:                       # Schweissnaht
        y = r.randrange(9, T - 9)
        for x in range(4, T - 4, 2):
            pygame.draw.rect(s, tuple(min(255, k + 12) for k in ton), (x, y, 1, 2))

    _koerner(s, K.C_DECK_FUGE, 16, seed)
    _koerner(s, hell, 8, seed + 1)
    return s


@platzhalter("deck")
def _deck():
    return _deck_basis(101)


@platzhalter("deck_2")
def _deck2():
    return _deck_basis(102)


@platzhalter("deck_3")
def _deck3():
    return _deck_basis(103, K.C_DECK_2)


@platzhalter("deck_4")
def _deck4():
    return _deck_basis(104)


@platzhalter("deck_gitter")
def _deck_gitter():
    """Laufrost. Man sieht hindurch, also ist zwischen den Streben Dunkel
    und kein Blech."""
    s = _flaeche(T, T)
    s.fill((15, 13, 12))                        # der Blick nach unten
    strebe = (48, 45, 39)
    kante = (74, 69, 60)
    for x in range(1, T, 5):                    # Laengsstreben, hochkant
        pygame.draw.rect(s, strebe, (x, 0, 3, T))
        pygame.draw.line(s, kante, (x, 0), (x, T - 1))       # Lichtkante
        pygame.draw.line(s, (24, 22, 19), (x + 2, 0), (x + 2, T - 1))
    for y in range(4, T, 12):                   # Querbaender, tiefer liegend
        pygame.draw.rect(s, (36, 34, 29), (0, y, T, 2))
        pygame.draw.line(s, (58, 54, 47), (0, y), (T - 1, y))
    pygame.draw.line(s, K.C_DECK_FUGE, (0, 0), (T - 1, 0))
    _koerner(s, (11, 10, 9), 16, 105)
    _koerner(s, (86, 80, 70), 5, 106)
    return s


@platzhalter("rumpfwand")
def _rumpfwand():
    """Aussenhaut und Schotten. Wie die Wand draussen gebaut - obere Flaeche
    hell, untere Kante hart - aber aus Stahl statt aus Stein."""
    s = _flaeche(T, T)
    s.fill(K.C_RUMPF)
    pygame.draw.rect(s, K.C_RUMPF_OBEN, (0, 0, T, 6))
    pygame.draw.rect(s, K.C_RUMPF_KANTE, (0, T - 3, T, 3))
    pygame.draw.line(s, tuple(min(255, k + 24) for k in K.C_RUMPF_OBEN),
                     (0, 0), (T - 1, 0))
    for x in (0, T // 2):                       # senkrechte Plattenstoesse
        pygame.draw.line(s, K.C_RUMPF_KANTE, (x, 6), (x, T - 4))
        pygame.draw.line(s, tuple(min(255, k + 16) for k in K.C_RUMPF),
                         (x + 1, 6), (x + 1, T - 4))
    pygame.draw.line(s, (94, 87, 74), (1, 7), (T - 2, 7))
    for nx in (4, T - 7):                       # Verschraubung oben
        _niete(s, nx, 2, K.C_STAHL_HELL, (56, 51, 43))
    _koerner(s, (60, 55, 47), 24, 107)
    _koerner(s, (126, 117, 100), 10, 108)
    return s


@platzhalter("rampe")
def _rampe():
    """Der Weg nach draussen. Warnmarkierung, damit man sie im Gefecht
    findet, ohne zu suchen."""
    r = random.Random(110)
    s = _deck_basis(109, muster=False, nieten=False)
    # Warnmarkierung nur als schmales Band am oberen und unteren Rand, und
    # zwar abgelaufen. Eine ganzflaechig gestreifte Kachel schreit lauter
    # als alles andere auf dem Bildschirm und macht die Karte unlesbar -
    # gesucht ist ein Hinweis, kein Absperrband.
    for band_y in (1, T - 5):
        for i in range(-6, T + 6, 7):
            pygame.draw.polygon(s, K.C_WARN,
                                [(i, band_y + 4), (i + 3, band_y + 4),
                                 (i + 7, band_y), (i + 4, band_y)])
        pygame.draw.rect(s, (0, 0, 0, 0), (0, band_y, 0, 0))
    for y in range(7, T - 6, 6):                # Trittleisten quer
        pygame.draw.rect(s, (40, 37, 32), (2, y, T - 4, 3))
        pygame.draw.line(s, (86, 80, 70), (2, y), (T - 3, y))
        pygame.draw.line(s, (22, 20, 17), (2, y + 2), (T - 3, y + 2))
    # Und zuletzt die Jahre darueber: Tritt, Staub, abgelaufener Lack.
    abgelaufen = pygame.Surface((T, T), pygame.SRCALPHA)
    abgelaufen.fill((14, 12, 10, 132))
    s.blit(abgelaufen, (0, 0))
    for _ in range(30):                         # blank getretene Stellen
        x, y = r.randrange(T), r.randrange(T)
        s.set_at((x, y), tuple(min(255, k + 10) for k in K.C_DECK))
    pygame.draw.line(s, K.C_DECK_FUGE, (0, 0), (T - 1, 0))
    pygame.draw.line(s, K.C_DECK_FUGE, (0, 0), (0, T - 1))
    _koerner(s, K.C_DECK_FUGE, 20, 110)
    _koerner(s, (96, 90, 78), 6, 111)
    return s


# ──────────────────────────────── Stationen und Einbauten
#
# Von oben sieht man von einem Geraet fast nur seine Grundflaeche. Erkennbar
# wird es dadurch **nicht** ueber Einzelheiten - dafuer ist keine Flaeche da -
# sondern ueber drei Dinge:
#
#   Umriss   rund, eckig, laenglich. Das liest man als Erstes.
#   Licht    ein farbiger Punkt sagt "das laeuft" und wo man hinsieht.
#   Richtung wohin das Geraet zeigt, damit man weiss, wo man sich hinstellt.
#
# Die Lichter halten sich an die Bedeutung, die das Spiel schon benutzt:
# tuerkis heisst Anzeige und Information, bernstein heisst Kraft und Gefahr.

def _geraet(seed, rechteck, farbe=None, hell=None):
    """Grundform jedes Einbaus: eine Platte auf dem Deck, mit Schatten."""
    s = _deck_basis(seed, muster=False)
    farbe = farbe or K.C_STAHL
    hell = hell or K.C_STAHL_HELL
    r = pygame.Rect(rechteck)
    pygame.draw.rect(s, (18, 16, 14), r.move(1, 2))        # eigener Schatten
    pygame.draw.rect(s, K.C_STAHL_DUNKEL, r)
    pygame.draw.rect(s, farbe, r.inflate(-2, -2))
    pygame.draw.line(s, hell, (r.left + 1, r.top + 1), (r.right - 2, r.top + 1))
    return s, r


def _lampe(s, x, y, farbe, grell=None):
    """Ein Betriebslicht. Zwei Pixel Kern, ein Hof darum - so liest es sich
    als Leuchte und nicht als Farbfleck."""
    grell = grell or tuple(min(255, k + 70) for k in farbe)
    pygame.draw.rect(s, tuple(k // 2 for k in farbe), (x - 1, y - 1, 4, 4))
    pygame.draw.rect(s, farbe, (x, y, 2, 2))
    s.set_at((x, y), grell)


@platzhalter("st_steuerstand")
def _st_steuerstand():
    """Der Steuerstand. Laenglich quer, zwei Griffe, eine Anzeige - man
    sieht sofort, auf welcher Seite man sich hinstellt."""
    s, r = _geraet(120, (4, 9, T - 8, 13))
    pygame.draw.rect(s, (30, 27, 23), (7, 12, T - 14, 6))   # Anzeigenblende
    pygame.draw.rect(s, K.C_TEAL_DK, (8, 13, T - 16, 4))
    for x in range(9, T - 8, 3):                            # Zeilen im Schirm
        pygame.draw.rect(s, K.C_TEAL, (x, 14, 2, 1))
    for gx in (5, T - 9):                                   # die beiden Griffe
        pygame.draw.circle(s, K.C_STAHL_DUNKEL, (gx + 1, 20), 3)
        pygame.draw.circle(s, (118, 110, 95), (gx + 1, 19), 2)
    _lampe(s, T // 2 - 1, 10, K.C_TEAL)
    _koerner(s, K.C_DECK_FUGE, 10, 120)
    return s


@platzhalter("st_geschuetz")
def _st_geschuetz():
    """Geschuetzstand: der Drehkranz, in dem das Rohr sitzt. Rund, damit man
    ihn von allem anderen unterscheidet."""
    s = _deck_basis(121, muster=False)
    m = T // 2
    pygame.draw.circle(s, (20, 18, 15), (m, m + 1), 12)     # Vertiefung
    pygame.draw.circle(s, K.C_STAHL_DUNKEL, (m, m), 12)
    pygame.draw.circle(s, K.C_STAHL, (m, m), 10)
    for i in range(12):                                     # Zahnkranz
        a = math.tau * i / 12
        x = int(m + math.cos(a) * 10.5)
        y = int(m + math.sin(a) * 10.5)
        pygame.draw.rect(s, K.C_STAHL_DUNKEL, (x - 1, y - 1, 2, 2))
    pygame.draw.circle(s, (42, 39, 34), (m, m), 6)
    pygame.draw.circle(s, K.C_STAHL_HELL, (m, m - 1), 5, 1)
    pygame.draw.rect(s, K.C_STAHL_DUNKEL, (m - 2, 3, 4, 8))  # Munitionszufuhr
    pygame.draw.rect(s, K.C_WARN, (m - 2, 4, 4, 1))
    _lampe(s, m - 1, m - 1, K.C_AMBER)
    return s


@platzhalter("st_reaktor")
def _st_reaktor():
    """Der Reaktor. Das einzige Bild im Rumpf, das von selbst leuchtet -
    und deshalb das, an dem man sich unter Deck orientiert."""
    s = _deck_basis(122, muster=False)
    m = T // 2
    for i in range(-T, T, 6):                               # Warnband
        pygame.draw.polygon(s, (72, 56, 26),
                            [(i, T), (i + 3, T), (i + 3 + T, 0), (i + T, 0)])
    pygame.draw.circle(s, K.C_STAHL_DUNKEL, (m, m), 13)
    pygame.draw.circle(s, (46, 42, 36), (m, m), 11)
    for ring, farbe in ((9, (96, 54, 22)), (7, (150, 78, 28)),
                        (5, K.C_GLUT), (3, (248, 186, 96))):
        pygame.draw.circle(s, farbe, (m, m), ring)
    pygame.draw.circle(s, (255, 236, 186), (m - 1, m - 1), 1)
    for i in range(8):                                      # Kuehlrippen
        a = math.tau * i / 8 + 0.4
        x1 = int(m + math.cos(a) * 11); y1 = int(m + math.sin(a) * 11)
        x2 = int(m + math.cos(a) * 14); y2 = int(m + math.sin(a) * 14)
        pygame.draw.line(s, K.C_STAHL_DUNKEL, (x1, y1), (x2, y2), 2)
        s.set_at((x2, y2), K.C_STAHL)
    return s


@platzhalter("st_werkbank")
def _st_werkbank():
    """Werkbank: eine Platte, Werkzeug darauf, ein Schraubstock an der Kante."""
    s, r = _geraet(123, (3, 7, T - 6, 17), (86, 62, 38), (136, 100, 62))
    for x in range(5, T - 5, 4):                            # Holzfugen
        pygame.draw.line(s, (56, 40, 24), (x, 9), (x, r.bottom - 3))
    pygame.draw.rect(s, K.C_STAHL_DUNKEL, (5, 10, 9, 3))    # Werkzeug
    pygame.draw.rect(s, K.C_STAHL_HELL, (5, 10, 9, 1))
    pygame.draw.rect(s, K.C_RUST, (17, 11, 8, 2))
    pygame.draw.circle(s, K.C_STAHL, (22, 18), 3)
    pygame.draw.rect(s, K.C_STAHL_DUNKEL, (4, 16, 7, 6))    # Schraubstock
    pygame.draw.rect(s, (118, 110, 95), (5, 17, 5, 2))
    _koerner(s, (48, 34, 20), 12, 123)
    return s


@platzhalter("st_kartentisch")
def _st_kartentisch():
    """Kartentisch: der einzige Ort an Bord, an dem Veld sichtbar wird."""
    s, r = _geraet(124, (3, 5, T - 6, T - 10), (44, 40, 34), (74, 68, 58))
    innen = r.inflate(-6, -6)
    pygame.draw.rect(s, (16, 24, 26), innen)                # Leuchttisch
    pygame.draw.rect(s, K.C_TEAL_DK, innen, 1)
    rnd = random.Random(7)
    punkte = [(innen.left + 3 + rnd.randrange(innen.width - 6),
               innen.top + 2 + rnd.randrange(innen.height - 4)) for _ in range(5)]
    for a, b in zip(punkte, punkte[1:]):                    # Sektorknoten
        pygame.draw.line(s, (26, 70, 68), a, b)
    for x, y in punkte:
        s.set_at((x, y), K.C_TEAL)
    _lampe(s, innen.centerx - 1, innen.top + 1, K.C_TEAL)
    return s


@platzhalter("st_funk")
def _st_funk():
    """Funk: Gehaeuse mit Lautsprechergitter, zwei Drehknoepfe, eine Skala."""
    s, r = _geraet(125, (5, 6, T - 10, T - 12), (52, 48, 41), (92, 85, 73))
    pygame.draw.rect(s, (24, 22, 19), (8, 9, 9, 9))         # Lautsprecher
    for y in range(10, 18, 2):
        pygame.draw.line(s, (62, 57, 49), (9, y), (15, y))
    pygame.draw.rect(s, (18, 26, 27), (19, 9, 6, 4))        # Skala
    pygame.draw.rect(s, K.C_TEAL, (20 + 2, 10, 1, 2))
    for cx in (20, 24):                                      # Drehknoepfe
        pygame.draw.circle(s, K.C_STAHL_DUNKEL, (cx, 17), 2)
        s.set_at((cx, 16), K.C_STAHL_HELL)
    pygame.draw.line(s, K.C_STAHL, (T - 7, 4), (T - 5, 12))  # Antenne
    _lampe(s, 9, 20, K.C_AMBER)
    return s


@platzhalter("st_werkstatt")
def _st_werkstatt():
    """Werkstatt: Schweissgeraet und Flaschen. Hier wird repariert, also
    liegt hier das Werkzeug fuer Q."""
    s = _deck_basis(126, muster=False)
    pygame.draw.rect(s, (18, 16, 14), (5, 8, 10, 18))       # Schatten
    for i, farbe in enumerate(((62, 76, 58), (96, 62, 40))):  # zwei Flaschen
        x = 5 + i * 6
        pygame.draw.rect(s, K.C_STAHL_DUNKEL, (x, 7, 5, 18))
        pygame.draw.rect(s, farbe, (x + 1, 8, 3, 16))
        pygame.draw.rect(s, tuple(min(255, k + 40) for k in farbe), (x + 1, 8, 1, 16))
        pygame.draw.rect(s, K.C_STAHL, (x + 1, 5, 3, 3))     # Ventil
    pygame.draw.rect(s, K.C_STAHL_DUNKEL, (18, 14, 11, 9))   # Geraet
    pygame.draw.rect(s, (66, 61, 52), (19, 15, 9, 7))
    pygame.draw.rect(s, K.C_STAHL_HELL, (19, 15, 9, 1))
    for x in range(20, 28, 2):                               # Schlauch
        pygame.draw.line(s, (34, 30, 26), (x, 24), (x + 1, 26))
    _lampe(s, 26, 17, K.C_TEAL)
    s.set_at((17, 12), (255, 240, 200))                      # ein Funke
    s.set_at((16, 13), K.C_AMBER)
    return s


@platzhalter("modulschacht")
def _modulschacht():
    """Ein **leerer** Schacht, und man muss ihm ansehen, dass er leer ist.

    Der Fortschritt im Spiel ist begehbar: ein neues Modul ist ein neuer
    Raum. Damit das wirkt, muss der leere Platz vorher als Luecke lesbar
    sein - offene Verankerung, lose Kabel, blanker Rumpf darunter.
    """
    s = _deck_basis(127, muster=False, nieten=False)
    r = pygame.Rect(3, 3, T - 6, T - 6)
    pygame.draw.rect(s, (22, 20, 17), r)                     # offener Grund
    pygame.draw.rect(s, K.C_STAHL_DUNKEL, r, 2)
    for ex in (r.left + 1, r.right - 5):                     # Verankerung
        for ey in (r.top + 1, r.bottom - 5):
            pygame.draw.rect(s, K.C_STAHL, (ex, ey, 4, 4))
            pygame.draw.rect(s, (24, 22, 18), (ex + 1, ey + 1, 2, 2))
    rnd = random.Random(19)
    for farbe in ((92, 60, 30), (46, 74, 72), (70, 64, 54)):  # lose Kabel
        x0 = rnd.randrange(r.left + 4, r.right - 8)
        y0 = rnd.randrange(r.top + 4, r.bottom - 6)
        pygame.draw.lines(s, farbe, False,
                          [(x0, y0), (x0 + 3, y0 + 3), (x0 + 7, y0 + 2),
                           (x0 + 9, y0 + 5)])
    _koerner(s, (14, 12, 10), 14, 127)
    return s


@platzhalter("antrieb")
def _antrieb():
    """Antriebsblock. Fest - man geht darum herum, nicht hindurch."""
    s = _deck_basis(128, muster=False, nieten=False)
    pygame.draw.rect(s, K.C_RUMPF_KANTE, (0, T - 3, T, 3))
    pygame.draw.rect(s, (62, 57, 49), (0, 0, T, T - 3))
    pygame.draw.rect(s, (86, 80, 69), (0, 0, T, 5))
    for x in range(3, T - 4, 8):                             # Kolben
        pygame.draw.rect(s, K.C_STAHL_DUNKEL, (x, 7, 6, 15))
        pygame.draw.rect(s, K.C_STAHL, (x + 1, 8, 4, 13))
        pygame.draw.rect(s, K.C_STAHL_HELL, (x + 1, 8, 1, 13))
        pygame.draw.rect(s, (30, 27, 23), (x + 1, 14, 4, 2))
    pygame.draw.rect(s, (34, 31, 26), (0, 23, T, 2))         # Riemen
    _lampe(s, T - 6, 2, K.C_AMBER)
    _koerner(s, (44, 40, 34), 20, 128)
    return s


@platzhalter("lager")
def _lager():
    """Gestapelte Frachtkaesten. Fest, und man sieht die Beute liegen."""
    s = _deck_basis(129, muster=False, nieten=False)
    for (x, y, w, h, ton) in ((2, 4, 14, 12, K.C_HULL_DK),
                              (17, 2, 12, 15, (96, 84, 58)),
                              (5, 17, 16, 12, K.C_HULL_DK),
                              (22, 18, 8, 11, (86, 76, 52))):
        pygame.draw.rect(s, (20, 17, 13), (x + 1, y + 2, w, h))
        pygame.draw.rect(s, K.C_HULL_SH, (x, y, w, h))
        pygame.draw.rect(s, ton, (x + 1, y + 1, w - 2, h - 2))
        pygame.draw.rect(s, tuple(min(255, k + 34) for k in ton),
                         (x + 2, y + 2, w - 4, 1))
        pygame.draw.rect(s, K.C_HULL_SH, (x + 1, y + h // 2, w - 2, 2))
    pygame.draw.rect(s, K.C_WARN, (19, 5, 4, 2))
    _koerner(s, K.C_HULL_SH, 14, 129)
    return s


@platzhalter("koje")
def _koje():
    """Eine Schlafkoje. Das einzige Stueck an Bord, das niemandem nutzt und
    trotzdem dasteht - und genau deshalb erzaehlt es etwas."""
    s = _deck_basis(130, muster=False)
    r = pygame.Rect(4, 3, T - 8, T - 6)
    pygame.draw.rect(s, (18, 16, 14), r.move(1, 2))
    pygame.draw.rect(s, K.C_STAHL_DUNKEL, r)                 # Rahmen
    pygame.draw.rect(s, (58, 46, 38), r.inflate(-3, -3))     # Liegeflaeche
    pygame.draw.rect(s, (150, 140, 118), (r.left + 3, r.top + 2, r.width - 6, 7))
    pygame.draw.rect(s, (188, 178, 152), (r.left + 4, r.top + 3, r.width - 8, 3))
    pygame.draw.rect(s, (112, 104, 86), (r.left + 3, r.top + 8, r.width - 6, 1))
    pygame.draw.rect(s, (50, 44, 36), (r.left + 2, r.top + 11,
                                       r.width - 4, r.height - 13))
    for y in range(r.top + 13, r.bottom - 3, 3):             # Deckenfalten
        pygame.draw.line(s, (40, 35, 29), (r.left + 3, y), (r.right - 4, y))
    _koerner(s, (34, 30, 25), 12, 130)
    return s


# ──────────────────────────────── Beinglieder
#
# Von oben sieht man von einem Bein die Oberseite: ein gepanzertes Gehaeuse,
# darin die Hydraulik. Die Glieder liegen nach rechts und werden um ihre
# Mitte gedreht, genau wie jede Figur - das linke Ende ist das koerpernahe
# Gelenk, das rechte das koerperferne.
#
#   bein_ober    Huefte  -> Knie    das schwere Glied, traegt die Last
#   bein_unter   Knie    -> Fuss    schlanker, mit sichtbarer Kolbenstange
#   bein_fuss    die Trittplatte
#   bein_huefte  die Schulter am Rumpf
#
# Alle vier bekommen eine dunkle Randlinie. Ohne sie versinken sie im Boden,
# sobald die Maschine ueber dunklen Untergrund laeuft - dasselbe Problem,
# das die Figuren haben, und dieselbe Loesung.
#
# Das Mass in BILD_MASS ist ein **Grundmass**. Eine Bauklasse mit anderen
# Beinlaengen bekommt es hart umgerechnet, Pixel fuer Pixel. Wer die Bilder
# ersetzt, malt deshalb eine Form und keine feste Groesse.

# Farbverlauf ueber den Querschnitt eines Glieds, von der oberen Kante zur
# unteren. Licht kommt von oben links, wie ueberall im Spiel. Ohne diesen
# Verlauf sieht ein Bein von oben aus wie ein Lineal: gleichmaessig hell,
# ohne Koerper. Mit ihm liest es sich als gewoelbtes Panzerblech.
_GLIED_TON = (
    (0.00, (118, 110, 95)),     # Lichtkante oben
    (0.16, (96, 90, 78)),
    (0.42, (72, 67, 58)),
    (0.70, (52, 48, 41)),
    (0.88, (34, 31, 27)),
    (1.00, (22, 20, 17)),       # Schattenkante unten
)


def _ton(f: float) -> tuple:
    """Mischt den Querschnittston an der Stelle f (0 oben, 1 unten)."""
    f = max(0.0, min(1.0, f))
    for (a, fa), (b, fb) in zip(_GLIED_TON, _GLIED_TON[1:]):
        if f <= b:
            k = 0.0 if b == a else (f - a) / (b - a)
            return tuple(int(round(fa[i] + (fb[i] - fa[i]) * k)) for i in range(3))
    return _GLIED_TON[-1][1]


def _glied(laenge, dicke, keil=0.0, seed=0, bauch=0.0):
    """Grundform eines Beinglieds: ein gewoelbtes Gehaeuse, das sich zum
    koerperfernen Ende verjuengt.

    `keil` sagt, wie stark es sich verjuengt - 0 bleibt gleich dick, 1
    laeuft spitz zu. `bauch` woelbt es in der Mitte zusaetzlich auf, wie ein
    Muskel oder ein Gehaeuse um eine Mechanik.

    Jede Spalte wird einzeln schattiert, von der Lichtkante oben bis zur
    Schattenkante unten. Das ist der ganze Unterschied zwischen einem Rohr
    und etwas, das Kraft uebertraegt.
    """
    s = _flaeche(laenge, dicke)
    mitte = dicke / 2.0
    for x in range(laenge):
        t = x / max(1, laenge - 1)
        halb = mitte * (1.0 - keil * t) + bauch * math.sin(math.pi * t)
        y0 = int(round(mitte - halb))
        y1 = int(round(mitte + halb))
        hoehe = y1 - y0
        if hoehe <= 0:
            continue
        for i in range(hoehe):
            s.set_at((x, y0 + i), _ton(i / max(1, hoehe - 1)))
    return s


def _kolben(s, x0, x1, y, laenge_hell=True):
    """Eine Kolbenstange laengs. Blanker Stahl, deshalb der hellste Strich
    auf dem ganzen Bein - daran erkennt man von oben, dass da Hydraulik
    arbeitet und nicht bloss ein Rohr liegt."""
    pygame.draw.line(s, (26, 24, 20), (x0, y + 1), (x1, y + 1))
    pygame.draw.line(s, K.C_STAHL_HELL, (x0, y), (x1, y))
    if laenge_hell:
        pygame.draw.line(s, (198, 188, 166), (x0 + 1, y), (x0 + max(2, (x1 - x0) // 3), y))


def _bolzen(s, x, y):
    pygame.draw.rect(s, (32, 29, 25), (x, y, 3, 3))
    pygame.draw.rect(s, K.C_STAHL, (x, y, 2, 2))
    s.set_at((x, y), K.C_STAHL_HELL)


@platzhalter("bein_ober")
def _bein_ober():
    """Oberschenkel: das schwere Glied. Breite Schulter am Rumpf, schmaler
    zum Knie, ein Panzerblech obenauf."""
    laenge, dicke = K.BILD_MASS["bein_ober"]
    s = _glied(laenge, dicke, keil=0.38, seed=41, bauch=1.2)
    m = dicke // 2
    # Querrippen. Sie verjuengen sich mit dem Glied, sonst laufen sie ueber
    # die Kante hinaus und heben die Form wieder auf.
    for x in range(9, laenge - 10, 8):
        t = x / max(1, laenge - 1)
        halb = int((dicke / 2.0) * (1.0 - 0.38 * t) + 1.2 * math.sin(math.pi * t))
        pygame.draw.line(s, (40, 37, 32), (x, m - halb + 2), (x, m + halb - 2))
        pygame.draw.line(s, (108, 101, 87), (x - 1, m - halb + 2),
                         (x - 1, m + halb - 2))
    _kolben(s, 7, laenge - 9, m + 1)
    for x in (2, laenge - 7):                     # Verschraubung an den Enden
        _bolzen(s, x, m - 1)
    return _rand(s, (14, 12, 10))


@platzhalter("bein_unter")
def _bein_unter():
    """Schienbein: schlanker, mit blanker Kolbenstange am Knie und einem
    Panzerschutz zum Fuss hin."""
    laenge, dicke = K.BILD_MASS["bein_unter"]
    drittel = laenge // 3
    # Am Knie eine blanke Kolbenstange, erst danach das Panzergehaeuse. Man
    # sieht dem Bein damit an, wo es arbeitet und wo es nur traegt.
    s = _glied(laenge, dicke, keil=0.24, seed=42, bauch=0.6)
    m = dicke // 2
    stange = pygame.Rect(2, m - 2, drittel - 2, 4)
    pygame.draw.rect(s, (0, 0, 0, 0), stange)
    pygame.draw.rect(s, (30, 27, 23), stange)
    pygame.draw.line(s, K.C_STAHL_HELL, (stange.left, m - 2), (stange.right, m - 2))
    pygame.draw.line(s, (204, 194, 172), (stange.left + 1, m - 2),
                     (stange.left + stange.width // 2, m - 2))
    pygame.draw.rect(s, (46, 42, 36), (drittel - 2, m - 3, 4, 7))  # Kragen
    for x in range(drittel + 5, laenge - 9, 9):                    # Nietenreihe
        _bolzen(s, x, m - 1)
    pygame.draw.rect(s, (56, 52, 44), (laenge - 6, m - 3, 5, 6))   # Knoechel
    pygame.draw.line(s, K.C_STAHL, (laenge - 6, m - 3), (laenge - 2, m - 3))
    return _rand(s, (14, 12, 10))


@platzhalter("bein_fuss")
def _bein_fuss():
    """Die Trittplatte, von oben. Drei Zehen nach vorn, eine Ferse hinten -
    daran sieht man, wohin das Bein zeigt, auch wenn es still steht."""
    g = K.BILD_MASS["bein_fuss"][0]
    s = _flaeche(g, g)
    m = g // 2
    # Drei Klauen nach vorn, mit dunklen Spalten dazwischen. Die Spalten
    # sind das Entscheidende: ohne sie verschmelzen die Zehen zu einem
    # Klumpen, und der Fuss hat keine Richtung mehr.
    for dy, laenge in ((-4, g - 7), (0, g - 4), (4, g - 7)):
        y = m + dy
        for x in range(m - 3, laenge):
            t = (x - (m - 3)) / max(1, laenge - (m - 3) - 1)
            halb = max(0, int(round(2.4 * (1.0 - t * 0.75))))
            for i in range(-halb, halb + 1):
                if 0 <= y + i < g and 0 <= x < g:
                    s.set_at((x, y + i), _ton((i + halb) / max(1, 2 * halb)))
    pygame.draw.circle(s, (26, 24, 20), (m - 3, m), 5)           # Ballen
    pygame.draw.circle(s, (86, 80, 69), (m - 3, m - 1), 4)
    pygame.draw.circle(s, (124, 116, 100), (m - 4, m - 2), 2)
    pygame.draw.rect(s, (30, 27, 23), (0, m - 3, 4, 7))          # Ferse
    pygame.draw.rect(s, (74, 68, 58), (1, m - 2, 3, 5))
    pygame.draw.line(s, K.C_STAHL_HELL, (1, m - 2), (3, m - 2))
    return _rand(s, (13, 11, 9))


@platzhalter("bein_huefte")
def _bein_huefte():
    """Das Schultergelenk am Rumpf. Rund, weil es sich dreht - und das soll
    man ihm ansehen."""
    g = K.BILD_MASS["bein_huefte"][0]
    s = _flaeche(g, g)
    m = g // 2
    pygame.draw.circle(s, (22, 20, 17), (m, m + 1), m - 1)
    pygame.draw.circle(s, K.C_STAHL_DUNKEL, (m, m), m - 1)
    pygame.draw.circle(s, (84, 78, 67), (m, m), m - 3)
    pygame.draw.circle(s, K.C_STAHL_HELL, (m, m - 1), m - 4, 1)
    for i in range(6):                                           # Kranzbolzen
        a = math.tau * i / 6
        x = int(m + math.cos(a) * (m - 2.5)) - 1
        y = int(m + math.sin(a) * (m - 2.5)) - 1
        pygame.draw.rect(s, K.C_STAHL, (x, y, 2, 2))
        s.set_at((x, y), K.C_STAHL_HELL)
    pygame.draw.circle(s, (34, 31, 26), (m, m), 2)
    return _rand(s, (13, 11, 9))
