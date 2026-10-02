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


# ──────────────────────────────── Wueste
#
# Derselbe Aufbau, anderer Untergrund. Sand hat **keine Fugen** und keine
# Nieten - er hat Korn, Riffel und hier und da einen Stein. Wer die
# Plattenkachel bloss einfaerbt, bekommt eine gelbe Werkhalle und keine
# Wueste; der Unterschied liegt darin, was fehlt.

def _sand_basis(seed):
    r = random.Random(seed)
    ton = tuple(max(0, min(255, c + r.randrange(-3, 4))) for c in K.C_SAND)
    s = _flaeche(T, T)
    s.fill(ton)
    # Riffel: flache Wellen, wie der Wind sie zieht.
    #
    # **Kurz und mit Abstand zum Rand.** Es gibt nur vier Bodenbilder, und
    # die wiederholen sich alle paar Kacheln; ein Riffel, der bis an die
    # Kachelkante laeuft, setzt sich beim Nachbarn fort und ergibt eine
    # durchgehende Linie ueber die halbe Karte. Das sah aus wie Dielen,
    # nicht wie Sand. Innerhalb der Kachel kann nichts zusammenwachsen.
    for _ in range(r.randrange(3, 6)):
        y = r.randrange(3, T - 4)
        laenge = r.randrange(T // 5, T // 2)
        x = r.randrange(3, T - laenge - 3)
        pygame.draw.line(s, K.C_SAND_DUNKEL, (x, y), (x + laenge, y))
        pygame.draw.line(s, K.C_SAND_KORN, (x + 1, y - 1), (x + laenge - 1, y - 1))
    _koerner(s, K.C_SAND_KORN, 26, seed + 3)
    _koerner(s, K.C_SAND_DUNKEL, 16, seed + 7)
    if r.random() < 0.45:                     # ein Stein
        x, y = r.randrange(3, T - 6), r.randrange(3, T - 6)
        b, h = r.randrange(2, 4), r.randrange(2, 3)
        pygame.draw.rect(s, (86, 72, 52), (x, y + 1, b, h))
        pygame.draw.rect(s, (132, 114, 84), (x, y, b, 1))
    return s


@platzhalter("sand")
def _sand():
    return _sand_basis(101)


@platzhalter("sand_2")
def _sand2():
    return _sand_basis(137)


@platzhalter("sand_3")
def _sand3():
    return _sand_basis(211)


@platzhalter("sand_4")
def _sand4():
    return _sand_basis(307)


@platzhalter("sand_wand")
def _sand_wand():
    """Lehm und Fels. Heller als die Blechwand und mit rauem Kopf."""
    s = _flaeche(T, T)
    s.fill(K.C_FELS)
    pygame.draw.rect(s, K.C_FELS_OBEN, (0, 0, T, 6))
    pygame.draw.rect(s, K.C_FELS_KANTE, (0, T - 3, T, 3))
    # Unregelmaessige Lagen statt gerader Bleche: Fels bricht, er wird
    # nicht geschweisst.
    # Auch hier mit Abstand zum Rand: eine Fuge, die bis an die Kante
    # laeuft, zieht sich sonst ueber die ganze Felswand durch.
    r = random.Random(55)
    for y in range(7, T - 4, 5):
        x = r.randrange(2, 8)
        pygame.draw.line(s, K.C_FELS_KANTE, (x, y),
                         (T - 3 - r.randrange(0, 6), y))
    for _ in range(3):
        x, y = r.randrange(1, T - 4), r.randrange(7, T - 6)
        pygame.draw.rect(s, (92, 76, 54), (x, y, r.randrange(2, 5), 2))
    _koerner(s, (84, 68, 48), 26, 23)
    _koerner(s, (162, 140, 104), 12, 24)
    return s


@platzhalter("sand_kiste")
def _sand_kiste():
    """Ein Fass. Im Sand steht kein Frachtkasten, da steht ein Fass -
    und ein Ring aus Fassern ist das Wahrzeichen des offenen Kreises."""
    s = _sand_basis(163)
    pygame.draw.ellipse(s, (20, 15, 10), (4, T - 13, T - 8, 11))   # Schatten
    pygame.draw.rect(s, (74, 62, 44), (5, 4, T - 10, T - 10))
    pygame.draw.rect(s, (118, 96, 60), (6, 5, T - 12, T - 12))
    pygame.draw.rect(s, (156, 128, 82), (7, 6, T - 14, 2))
    for y in (10, 16, 22):
        pygame.draw.line(s, (62, 50, 34), (6, y), (T - 7, y))
    pygame.draw.rect(s, (24, 18, 12), (5, 4, T - 10, T - 10), 1)
    return s


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


def _aufzug_pfeile(s, hoch: bool):
    """Das Zeichen fuer einen Aufzug: zwei Pfeile, der der Fahrtrichtung
    leuchtet. Tuerkis hinauf, Bernstein hinab - wie bei den Treppen,
    damit niemand lernen muss, was die Farbe hier heisst."""
    m = T // 2
    an = K.C_TEAL if hoch else K.C_AMBER
    aus = (70, 62, 52)
    pygame.draw.polygon(s, an if hoch else aus,
                        [(m, m - 9), (m - 5, m - 3), (m + 5, m - 3)])
    pygame.draw.polygon(s, aus if hoch else an,
                        [(m, m + 9), (m - 5, m + 3), (m + 5, m + 3)])


@platzhalter("aufzug_tuer")
def _aufzug_tuer():
    """Unten: die Kabine, in die man aus dem Sand hineinlaeuft.

    Dunkler Riffelblechboden zwischen zwei Stahlpfosten, damit sie sich
    klar vom Fels daneben abhebt - wer sie sucht, muss sie von weitem
    als Oeffnung erkennen, nicht als weiteren Felsbrocken.
    """
    s = _flaeche(T, T)
    s.fill((34, 30, 27))
    for y in range(3, T, 6):
        for x in range(2 + (y // 6) % 2 * 3, T - 2, 6):
            pygame.draw.line(s, (52, 46, 40), (x, y), (x + 2, y + 1))
    # Pfosten oben und unten, mit Nieten
    for y in (0, T - 3):
        pygame.draw.rect(s, (88, 80, 70), (0, y, T, 3))
        for x in range(3, T, 8):
            s.set_at((x, y + 1), (150, 138, 116))
    _aufzug_pfeile(s, True)
    return s


@platzhalter("aufzug_schacht")
def _aufzug_schacht():
    """Oben: der Schachtkopf auf dem Plateau, mit Warnstreifen am Rand."""
    s = _flaeche(T, T)
    s.fill((46, 40, 34))
    # Gitter ueber dem Schacht
    for i in range(5, T - 4, 5):
        pygame.draw.line(s, (24, 20, 16), (i, 4), (i, T - 5))
        pygame.draw.line(s, (70, 62, 52), (4, i), (T - 5, i))
    # Warnstreifen, schraeg, als Rahmen
    rahmen = _flaeche(T, T)
    for i in range(-T, T * 2, 6):
        pygame.draw.line(rahmen, K.C_AMBER, (i, 0), (i + T, T), 3)
    innen = pygame.Rect(4, 4, T - 8, T - 8)
    rahmen.fill((0, 0, 0, 0), innen)
    s.blit(rahmen, (0, 0))
    pygame.draw.rect(s, (24, 18, 12), innen, 1)
    pygame.draw.rect(s, (24, 18, 12), s.get_rect(), 1)
    _aufzug_pfeile(s, False)
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

    if d["aufbau"] == "buechse":                  # Rauchgranate: Blechdose
        # Bewusst eckig und hell. Als Kugel sah sie aus wie die
        # Sprenggranate, und im Gefecht muss man der Hand ansehen, was
        # gleich fliegt.
        pygame.draw.rect(s, (72, 76, 72), (hand + 1, c - 4, 7, 9))
        pygame.draw.rect(s, (128, 134, 128), (hand + 2, c - 3, 5, 7))
        pygame.draw.rect(s, (168, 172, 168), (hand + 2, c - 3, 5, 2))
        pygame.draw.rect(s, (44, 46, 44), (hand + 3, c - 7, 3, 3))
        pygame.draw.rect(s, K.C_CREAM, (hand + 4, c - 6, 1, 1))
        return

    if d["aufbau"] == "rohr":                     # Raketenwerfer: dickes Rohr
        # Die unverwechselbarste Silhouette im Spiel, und das soll sie
        # sein: wer eine Rakete traegt, ist von weitem zu erkennen. Ein
        # sehr dickes Rohr, vorn der Sprengkopf, hinten offen.
        laenge, dick = d["lauf"], d["dicke"]
        pygame.draw.rect(s, (62, 58, 48), (hand - d["schaft"], c - dick // 2,
                                           d["schaft"] + laenge, dick))
        pygame.draw.rect(s, (104, 96, 78), (hand - d["schaft"] + 1, c - dick // 2 + 1,
                                            d["schaft"] + laenge - 2, 2))
        # Sprengkopf
        pygame.draw.polygon(s, (150, 62, 40),
                            [(hand + laenge - 3, c - dick // 2 - 1),
                             (hand + laenge + 4, c),
                             (hand + laenge - 3, c + dick // 2 + 1)])
        pygame.draw.rect(s, (214, 96, 56), (hand + laenge - 3, c - 1, 4, 2))
        # Hinten offen: das Rohr ist dort dunkel
        pygame.draw.rect(s, (18, 16, 14), (hand - d["schaft"], c - dick // 2 + 1,
                                           2, dick - 2))
        return

    if d["aufbau"] == "zweibein":                 # MG: dick, mit Zweibein
        # In der Draufsicht ist ein MG vor allem eines: breit. Dazu ein
        # Kastenmagazin unter dem Lauf und ein Zweibein vorn, das nach
        # beiden Seiten absteht - daran erkennt man es auf einen Blick,
        # auch wenn Lauf und Laenge dem Scharfschuetzen aehneln.
        laenge, dick = d["lauf"], d["dicke"]
        pygame.draw.rect(s, (56, 52, 44), (hand - d["schaft"], c - d["s_dicke"] // 2,
                                           d["schaft"] + 3, d["s_dicke"]))
        pygame.draw.rect(s, stahl, (hand, c - dick // 2, laenge, dick))
        pygame.draw.rect(s, stahl_h, (hand, c - dick // 2, laenge, 1))
        # Kastenmagazin
        pygame.draw.rect(s, (44, 48, 44), (hand + 2, c + dick // 2, 7, 5))
        pygame.draw.rect(s, (78, 84, 76), (hand + 3, c + dick // 2 + 1, 5, 3))
        # Zweibein, nach beiden Seiten
        pygame.draw.line(s, (40, 38, 32), (hand + laenge - 5, c - dick // 2),
                         (hand + laenge - 1, c - dick // 2 - 4))
        pygame.draw.line(s, (40, 38, 32), (hand + laenge - 5, c + dick // 2),
                         (hand + laenge - 1, c + dick // 2 + 4))
        # Muendungsbremse
        pygame.draw.rect(s, (30, 28, 24), (hand + laenge - 2, c - dick // 2 - 1,
                                           3, dick + 2))
        return

    if d["aufbau"] == "koffer":                   # Medkit beim Anlegen
        # Mit beiden Haenden vor der Brust, aufgeklappt: weiss, mit dem
        # roten Kreuz, und ein Streifen Verband haengt heraus. Muss sich
        # auf den ersten Blick von jeder Waffe unterscheiden - wer das
        # sieht, weiss: der schiesst gerade nicht.
        pygame.draw.rect(s, (28, 22, 16), (hand - 1, c - 7, 11, 14))
        pygame.draw.rect(s, (214, 210, 196), (hand, c - 6, 9, 12))
        pygame.draw.rect(s, (168, 162, 148), (hand, c + 3, 9, 3))
        pygame.draw.rect(s, K.C_RED, (hand + 3, c - 4, 3, 7))
        pygame.draw.rect(s, K.C_RED, (hand + 1, c - 2, 7, 3))
        pygame.draw.rect(s, (236, 232, 220), (hand + 9, c + 1, 4, 2))
        pygame.draw.rect(s, (236, 232, 220), (hand + 12, c + 2, 2, 3))
        return

    if d["aufbau"] == "walze":                    # Blendgranate: glatte Walze
        # Glatt und hell, ohne Riffel und ohne Lappen: in der Hand muss
        # man ihr ansehen, dass sie nicht splittert und nicht brennt.
        pygame.draw.rect(s, (126, 128, 132), (hand + 2, c - 4, 5, 9))
        pygame.draw.rect(s, (188, 192, 196), (hand + 3, c - 3, 3, 7))
        pygame.draw.rect(s, (236, 240, 244), (hand + 3, c - 3, 1, 7))
        pygame.draw.rect(s, (52, 54, 58), (hand + 3, c - 6, 3, 2))
        pygame.draw.rect(s, (236, 232, 200), (hand + 4, c - 7, 1, 2))
        return

    if d["aufbau"] == "flasche":                  # Molotow: Flasche mit Lappen
        # Schmal und hoch, mit einem hellen Lappen obendrauf. Von oben
        # sieht man von einer Flasche wenig; was sie unterscheidbar
        # macht, ist die Schulter und der brennende Docht.
        pygame.draw.rect(s, (46, 66, 44), (hand + 2, c - 3, 5, 8))
        pygame.draw.rect(s, (84, 116, 78), (hand + 3, c - 2, 3, 6))
        pygame.draw.rect(s, (132, 168, 120), (hand + 3, c - 2, 1, 6))
        pygame.draw.rect(s, (38, 52, 38), (hand + 3, c - 6, 3, 3))   # Hals
        pygame.draw.rect(s, K.C_CREAM, (hand + 3, c - 8, 3, 2))      # Lappen
        pygame.draw.rect(s, (236, 150, 44), (hand + 4, c - 9, 1, 1))
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


# Wie weit die Arme eines Zombies vom dunklen Ton zum Rumpfton aufgehellt
# sind (0 = so dunkel wie der Kopfrand, 1 = Rumpffarbe). Siehe _figur.
ZOMBIE_ARMTON = 0.30


def _figur(groesse, rumpf, rumpf_dk, akzent, breit=False, waffe=None,
           bewaffnet=True):
    """Draufsicht: Schultern quer, Kopf mittig, Waffe nach rechts.

    `bewaffnet=False`: ein Zombie. Bis 0.31 hielten die Gegner denselben
    Gewehrstummel wie der Spieler - sie benutzten dieselbe Figur, und
    deren Vorgabe war eine Waffe. Ohne Waffe bleiben die Arme kurz, so
    lang wie beim Bewaffneten, laufen aber nur noch einen Pixel zur Mitte
    statt zwei: sie halten ja nichts. Und sie sind etwas heller als der
    Kopfrand (ZOMBIE_ARMTON). Der dunkle Rand des Kopfes lag vorher unter
    der Waffe; ohne sie liegt er genau zwischen den Armen, und in
    derselben Farbe wuchs alles zu einem dunklen Klotz zusammen.

    Laengere Arme, gespreizte, parallele, mit Klauen oder Faeusten sind
    in 0.31.1 bis 0.31.3 ausprobiert worden - in 28 Pixeln sah keine
    davon besser aus als diese unscheinbare.
    """
    s = _flaeche(groesse, groesse)
    c = groesse // 2
    hell = tuple(min(255, k + 34) for k in rumpf)
    schulter = pygame.Rect(c - 7, c - (9 if breit else 8), 14, (18 if breit else 16))
    pygame.draw.ellipse(s, rumpf_dk, schulter)
    pygame.draw.ellipse(s, rumpf, schulter.inflate(-3, -3))
    pygame.draw.ellipse(s, hell, schulter.inflate(-3, -3).move(0, -2), 1)
    if bewaffnet or waffe is not None:
        # Arme nach vorn, zur Waffe hin
        pygame.draw.line(s, rumpf_dk, (c + 1, c - 5), (c + 8, c - 3), 3)
        pygame.draw.line(s, rumpf_dk, (c + 1, c + 5), (c + 8, c + 3), 3)
    else:
        arm = tuple(int(d + (r - d) * ZOMBIE_ARMTON) for d, r in zip(rumpf_dk, rumpf))
        # Ein Arm wird gezeichnet, der andere ist sein Spiegelbild (seit
        # 0.32.6). Zwei Linien mit pygame.draw.line und Breite 3 werden
        # nicht symmetrisch gezeichnet: der obere Arm lag eine Zeile weiter
        # innen als der untere und sah aus, als wuechse er aus der Mitte
        # (gemeldet). Gespiegelt wird um die Mitte der Schultern - die
        # Ellipse reicht von c - 8 bis c + 7, gespiegelt wird also Zeile y
        # auf 2c - 1 - y, und genau das tut ein Umklappen der ganzen
        # Flaeche.
        einer = _flaeche(groesse, groesse)
        pygame.draw.line(einer, arm, (c + 1, c + 5), (c + 8, c + 4), 3)
        s.blit(einer, (0, 0))
        s.blit(pygame.transform.flip(einer, False, True), (0, 0))
    # Waffe: entweder die benannte aus der Tabelle oder der alte Stummel
    if waffe is not None:
        _hand_waffe(s, c, waffe)
    elif bewaffnet:
        pygame.draw.rect(s, (30, 25, 19), (c + 6, c - 2, 12, 4))
        pygame.draw.rect(s, (86, 72, 52), (c + 6, c - 1, 10, 2))
    # Kopf
    pygame.draw.circle(s, rumpf_dk, (c + 1, c), 5)
    pygame.draw.circle(s, hell, (c + 1, c), 4)
    pygame.draw.circle(s, akzent, (c + 3, c), 2)
    return _rand(s)


def _figur_schwung(rumpf, rumpf_dk, akzent, rel: float):
    """Die Gestalt mitten im Schlag mit dem Brecheisen (seit 0.32.8).

    Gemeldet: der Schwung sah billig aus (eine Linie mit einem Klotz), und
    die Figur sah dabei aus, als haette sie die Waffe noch - die schlichte
    Gestalt hatte noch den alten Gewehrstummel. Jetzt: keine Waffe, beide
    Arme gehen zu einer Hand vorn, und in der liegt das Brecheisen aus der
    alten Hotbar (`waffe_brecheisen`), um `rel` Grad gegen die Blickrichtung
    gedreht. Die Arme laufen mit, der Kopf liegt obendrauf.
    """
    groesse = 64
    s = _flaeche(groesse, groesse)
    c = groesse // 2
    hell = tuple(min(255, k + 34) for k in rumpf)
    schulter = pygame.Rect(c - 7, c - 8, 14, 16)
    pygame.draw.ellipse(s, rumpf_dk, schulter)
    pygame.draw.ellipse(s, rumpf, schulter.inflate(-3, -3))
    pygame.draw.ellipse(s, hell, schulter.inflate(-3, -3).move(0, -2), 1)
    hand = pygame.Vector2(c + 1, c) + pygame.Vector2(12, 0).rotate(rel)
    # Erst das Eisen, dann die Arme darueber: die Haende umfassen den Griff.
    eisen = _waffe_brecheisen()
    gedreht = pygame.transform.rotate(eisen, -rel)
    # Gedreht wird um den Griff (5, 7.5 im Bild), nicht um die Bildmitte.
    griff = pygame.Vector2(5 - eisen.get_width() / 2, 7.5 - eisen.get_height() / 2)
    mitte = hand - griff.rotate(rel)
    s.blit(gedreht, gedreht.get_rect(center=(round(mitte.x), round(mitte.y))))
    for seite in (-5, 5):
        pygame.draw.line(s, rumpf_dk, (c + 1, c + seite), hand, 3)
    pygame.draw.circle(s, rumpf_dk, (round(hand.x), round(hand.y)), 2)
    # Kopf
    pygame.draw.circle(s, rumpf_dk, (c + 1, c), 5)
    pygame.draw.circle(s, hell, (c + 1, c), 4)
    pygame.draw.circle(s, akzent, (c + 3, c), 2)
    return _rand(s)


def schwung_winkel(i: int) -> float:
    """Der Winkel des Eisens im Bild `i` (von K.SCHWUNG_BILDER)."""
    halb = K.WAFFEN[K.NAHKAMPF["waffe"]]["winkel"] * 0.5
    return -halb + 2 * halb * i / max(1, K.SCHWUNG_BILDER - 1)


def _schwung_bild(i, kombi=None):
    def zeichner():
        if kombi is None:
            return _figur_schwung(K.C_HULL, K.C_HULL_SH, K.C_TEAL, schwung_winkel(i))
        return _figur_schwung(kombi["rumpf"], kombi["kante"], kombi["akzent"],
                              schwung_winkel(i))
    return zeichner


for _i in range(K.SCHWUNG_BILDER):
    platzhalter("spieler_schwung_%d" % _i)(_schwung_bild(_i))
    for _kombi in K.TEAMS["kombi"]:
        platzhalter("spieler_%s_schwung_%d" % (_kombi["name"].lower(), _i))(
            _schwung_bild(_i, _kombi))


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


# ── Mannschaftsfarben ─────────────────────────────────────────────
#
# Jede Mannschaft bekommt jede Spielerfigur noch einmal, in ihren eigenen
# Farben. Das ist der Punkt, an dem man im Gefecht auf einen Blick sieht,
# wer zu wem gehoert - ohne Namen, ohne Balken, auch quer ueber den Raum
# und auch eine Ebene tiefer, wo eine Gestalt nur noch ein Fleck ist.
#
# Registriert wird ueber eine Schleife: eine dritte Mannschaft in
# K.TEAMS["kombi"] bekommt ihre Figuren dadurch von selbst, und jede davon
# ist einzeln durch eine Datei ersetzbar.

def _spieler_team(kombi, waffe=None):
    def zeichner():
        if waffe is None:
            return _figur(K.BILD_MASS["spieler"][0], kombi["rumpf"],
                          kombi["kante"], kombi["akzent"])
        gross = K.BILD_MASS["spieler_" + waffe][0]
        return _figur(gross, kombi["rumpf"], kombi["kante"], kombi["akzent"],
                      waffe=waffe)
    return zeichner


def _boden_team(kombi):
    def zeichner():
        return _figur_boden(kombi["rumpf"], kombi["kante"])
    return zeichner


for _kombi in K.TEAMS["kombi"]:
    _kurz = _kombi["name"].lower()
    platzhalter("spieler_" + _kurz)(_spieler_team(_kombi))
    platzhalter("spieler_%s_boden" % _kurz)(_boden_team(_kombi))
    for _waffe in K.WAFFEN_HAND:
        platzhalter("spieler_%s_%s" % (_kurz, _waffe))(
            _spieler_team(_kombi, _waffe))


@platzhalter("gegner_laeufer")
def _gegner_laeufer():
    return _figur(28, (128, 84, 58), (58, 36, 24), K.C_ORANGE, bewaffnet=False)


@platzhalter("gegner_brecher")
def _gegner_brecher():
    s = _figur(36, (112, 70, 48), (48, 30, 20), K.C_RED, breit=True,
               bewaffnet=False)
    c = 18
    pygame.draw.rect(s, (74, 48, 32), (c - 9, c - 12, 18, 4))
    pygame.draw.rect(s, K.C_RUST, (c - 8, c - 11, 16, 2))
    return s


# ── Die drei neuen Gegner
#
# Jeder muss sich auf einen Blick von den anderen unterscheiden, und zwar
# an **Form und Farbe zugleich**. Nur an der Farbe geht es nicht: im
# Rauch, im Feuerschein und auf dem Sand von STAUBTAL sieht alles
# orangebraun aus. Also hat der Renner eine schmale Silhouette, der
# Blaeher eine runde, der Speier eine mit Auswuchs.

@platzhalter("gegner_renner")
def _gegner_renner():
    """Der Schnelle. Muss sich vom Laeufer auf einen Blick unterscheiden.

    Der erste Versuch war ein kleinerer, hellerer Laeufer - und genau das
    reichte nicht: im Bild nebeneinander sah man den Unterschied, im
    Gefecht nicht. Er ist deshalb nicht dieselbe Gestalt in klein,
    sondern eine andere Form: laenglich statt rund, knochenhell statt
    erdbraun, und nach vorn gebeugt mit Schleppe dahinter.
    """
    s = _flaeche(24, 24)
    c = 12
    # Laenglicher Leib, nach vorn geneigt: die Silhouette allein sagt
    # schon "der ist schnell".
    pygame.draw.ellipse(s, (58, 50, 42), (c - 9, c - 5, 20, 10))
    pygame.draw.ellipse(s, (196, 182, 156), (c - 8, c - 4, 18, 8))
    pygame.draw.ellipse(s, (232, 222, 198), (c - 6, c - 4, 12, 5))
    # Die Arme weit vorgestreckt.
    pygame.draw.line(s, (58, 50, 42), (c + 2, c - 4), (c + 10, c - 6), 2)
    pygame.draw.line(s, (58, 50, 42), (c + 2, c + 4), (c + 10, c + 6), 2)
    # Schleppe nach hinten: drei Striche, die schmaler werden.
    for i, dy in enumerate((-3, 0, 3)):
        laenge = 6 - abs(dy)
        pygame.draw.line(s, (128, 116, 96), (c - 9, c + dy),
                         (c - 9 - laenge, c + dy), 1)
    pygame.draw.circle(s, (46, 40, 34), (c + 5, c), 4)
    pygame.draw.circle(s, (238, 232, 214), (c + 5, c), 3)
    pygame.draw.circle(s, (226, 62, 42), (c + 7, c), 2)
    return _rand(s)


@platzhalter("gegner_speier")
def _gegner_speier():
    s = _figur(30, (92, 106, 62), (42, 52, 28), (168, 226, 96), bewaffnet=False)
    c = 15
    # Der Kropf vorn: daher kommt der Spuck, und man sieht, wohin er zielt.
    pygame.draw.circle(s, (54, 68, 34), (c + 8, c), 5)
    pygame.draw.circle(s, (110, 140, 70), (c + 8, c), 4)
    pygame.draw.circle(s, (176, 232, 108), (c + 10, c), 2)
    return _rand(s)


@platzhalter("gegner_blaeher")
def _gegner_blaeher():
    # Rund und aufgedunsen, mit hellen Blasen. Die Form sagt "platzt".
    s = _flaeche(34, 34)
    c = 17
    pygame.draw.circle(s, (58, 44, 26), (c, c), 13)
    pygame.draw.circle(s, (126, 96, 52), (c, c), 12)
    pygame.draw.circle(s, (158, 126, 70), (c - 2, c - 3), 9)
    for (bx, by, br) in ((-5, 4, 3), (5, 5, 2), (3, -6, 3), (-6, -4, 2)):
        pygame.draw.circle(s, (196, 178, 96), (c + bx, c + by), br)
        pygame.draw.circle(s, (232, 220, 150), (c + bx - 1, c + by - 1), max(1, br - 2))
    pygame.draw.circle(s, (46, 34, 20), (c + 9, c), 4)      # der kleine Kopf
    pygame.draw.circle(s, K.C_ORANGE, (c + 10, c), 2)
    return _rand(s)


# ── Die Bosse
#
# Gross, und jeder mit einem Merkmal, das seine Faehigkeit ankuendigt:
# der Koloss hat Platten (er stampft), die Mutter einen Sack voller
# Renner (sie ruft), der Brandstifter Tanks und eine brennende Flasche
# (er wirft Feuer). Und jeder mit eigenem Umriss - rund ist schon der
# Blaeher, und ein grosser Blaeher ist kein Boss.

@platzhalter("boss_koloss")
def _boss_koloss():
    s = _flaeche(58, 58)
    c = 29
    pygame.draw.circle(s, (34, 30, 26), (c, c), 24)
    pygame.draw.circle(s, (96, 88, 78), (c, c), 22)
    pygame.draw.circle(s, (128, 118, 102), (c - 2, c - 3), 18)
    # Panzerplatten quer. Sie geben ihm die Schwere, die er im Spiel hat.
    for i, dy in enumerate((-12, -4, 4, 12)):
        breit = 30 - abs(dy)
        pygame.draw.rect(s, (58, 52, 44), (c - breit // 2, c + dy - 2, breit, 4))
        pygame.draw.rect(s, (150, 138, 118), (c - breit // 2, c + dy - 2, breit, 1))
    # Zwei Faeuste vorn - womit er stampft.
    for dy in (-11, 11):
        pygame.draw.circle(s, (44, 38, 32), (c + 15, c + dy), 7)
        pygame.draw.circle(s, (112, 100, 86), (c + 15, c + dy), 6)
        pygame.draw.circle(s, K.C_RUST, (c + 17, c + dy), 2)
    pygame.draw.circle(s, (22, 18, 15), (c + 6, c), 6)
    pygame.draw.circle(s, K.C_RED, (c + 8, c), 3)
    return _rand(s)


@platzhalter("boss_mutter")
def _boss_mutter():
    """Die Mutter. Ein riesiger Brutsack hinten, vorn ein kleiner Leib mit
    langen, spinnigen Armen.

    Die erste Fassung war ein gruenes Ei mit hellen Punkten - so gruen
    wie der Speier und so rund wie der Blaeher, und im Gefecht hielt man
    sie fuer einen grossen Speier. Jetzt ist sie birnenfoermig statt rund
    und fleischig-violett statt gruen. Was im Sack liegt, sind Renner:
    knochenhell, eingerollt, mit dem roten Auge - man sieht ihr also an,
    **was** sie gleich ruft.
    """
    s = _flaeche(48, 48)
    c = 24
    kante, leib, hell = (44, 22, 32), (128, 74, 92), (168, 108, 122)
    # Nachschleppende Straenge hinter dem Sack.
    for dy, lang in ((-8, 6), (0, 8), (8, 6)):
        pygame.draw.line(s, (70, 38, 50), (c - 20, c + dy),
                         (c - 20 - lang, c + dy + (dy // 4)), 2)
    # Der Sack: gross, prall, hinten.
    sack = pygame.Rect(c - 22, c - 16, 30, 32)
    pygame.draw.ellipse(s, kante, sack)
    pygame.draw.ellipse(s, leib, sack.inflate(-3, -3))
    pygame.draw.ellipse(s, hell, sack.inflate(-12, -14).move(-2, -4))
    # Adern ueber den Sack.
    for (a, b) in (((c - 16, c - 9), (c - 6, c - 12)),
                   ((c - 18, c + 4), (c - 8, c + 11)),
                   ((c - 12, c - 2), (c - 3, c + 1))):
        pygame.draw.line(s, (88, 44, 62), a, b, 1)
    # Die Brut im Sack: eingerollte Renner, knochenhell mit rotem Auge.
    for (bx, by) in ((-15, -6), (-9, 4), (-13, 9), (-5, -8), (-3, 5)):
        pygame.draw.ellipse(s, (70, 50, 52), (c + bx - 3, c + by - 2, 8, 6))
        pygame.draw.ellipse(s, (214, 200, 176), (c + bx - 2, c + by - 2, 6, 4))
        pygame.draw.rect(s, (226, 62, 42), (c + bx + 2, c + by - 1, 1, 1))
    # Der Leib vorn: klein gegen den Sack.
    pygame.draw.ellipse(s, kante, (c + 2, c - 8, 14, 16))
    pygame.draw.ellipse(s, (104, 62, 74), (c + 3, c - 7, 12, 14))
    pygame.draw.ellipse(s, (146, 94, 106), (c + 4, c - 6, 7, 6))
    # Vier lange Arme, nach vorn gespreizt, mit Klauen.
    for (x0, y0, x1, y1) in ((c + 8, c - 6, c + 18, c - 15),
                             (c + 8, c + 6, c + 18, c + 15),
                             (c + 5, c - 7, c + 8, c - 19),
                             (c + 5, c + 7, c + 8, c + 19)):
        pygame.draw.line(s, kante, (x0, y0), (x1, y1), 3)
        pygame.draw.line(s, (150, 104, 110), (x0, y0), (x1, y1), 1)
        pygame.draw.rect(s, (226, 214, 190), (x1, y1 - 1, 2, 2))
    # Kopf mit drei Augen.
    pygame.draw.circle(s, (34, 18, 24), (c + 17, c), 5)
    pygame.draw.circle(s, (88, 50, 62), (c + 17, c), 4)
    for (ax, ay) in ((c + 19, c - 2), (c + 20, c), (c + 19, c + 2)):
        pygame.draw.rect(s, (236, 70, 48), (ax, ay, 1, 1))
    return _rand(s)


@platzhalter("boss_brandstifter")
def _boss_brandstifter():
    """Der Brandstifter. Ein Mann in verkohltem Schutzanzug, zwei
    Brennstofftanks auf dem Ruecken, vorn eine brennende Flasche.

    Die erste Fassung war eine glimmende Kugel - so rund wie der Blaeher
    und in derselben Farbe, und man wusste nicht, ob gleich etwas platzt
    oder brennt. Jetzt ist er die einzige Gestalt mit breiten Schultern
    und Tanks, fast schwarz statt orange, und das Feuer sitzt genau dort,
    wo es herkommt: in der Hand, die wirft.
    """
    s = _flaeche(46, 46)
    c = 23
    # Die Tanks auf dem Ruecken, rostrot mit Messingkappen.
    for dy in (-11, 2):
        pygame.draw.rect(s, (40, 18, 12), (c - 19, c + dy - 1, 12, 11),
                         border_radius=3)
        pygame.draw.rect(s, (146, 54, 34), (c - 18, c + dy, 10, 9),
                         border_radius=3)
        pygame.draw.rect(s, (200, 92, 56), (c - 18, c + dy + 1, 10, 2))
        pygame.draw.rect(s, (224, 172, 72), (c - 20, c + dy + 3, 2, 3))
    # Schultern: breit, verkohlt.
    schulter = pygame.Rect(c - 11, c - 14, 22, 28)
    pygame.draw.ellipse(s, (18, 14, 12), schulter)
    pygame.draw.ellipse(s, (74, 62, 52), schulter.inflate(-3, -3))
    pygame.draw.ellipse(s, (106, 90, 74), schulter.inflate(-10, -14).move(-2, -4))
    # Glut in den Rissen des Anzugs - hell genug, dass er auch auf
    # dunklem Boden nicht nur ein Loch ist.
    for (a, b) in (((c - 7, c - 9), (c - 2, c - 5)),
                   ((c - 8, c + 6), (c - 2, c + 9)),
                   ((c + 1, c - 12), (c + 4, c - 8))):
        pygame.draw.line(s, (214, 92, 34), a, b, 2)
        pygame.draw.line(s, (255, 196, 96), a, b, 1)
    # Der Schlauch vom Tank nach vorn.
    pygame.draw.lines(s, (30, 24, 20), False,
                      [(c - 9, c + 7), (c - 2, c + 12), (c + 8, c + 11)], 2)
    # Arme nach vorn: der untere haelt die Flasche.
    pygame.draw.line(s, (26, 20, 18), (c + 2, c - 8), (c + 11, c - 6), 4)
    pygame.draw.line(s, (26, 20, 18), (c + 2, c + 8), (c + 12, c + 7), 4)
    # Die Flasche mit brennendem Lappen. Die Flamme ist sein Zeichen und
    # darf deshalb gross sein: sie sagt, womit er gleich wirft.
    pygame.draw.rect(s, (46, 66, 44), (c + 12, c + 5, 5, 5))
    pygame.draw.rect(s, (104, 140, 92), (c + 13, c + 6, 2, 3))
    pygame.draw.polygon(s, (196, 54, 28), [(c + 16, c + 4), (c + 20, c + 1),
                                           (c + 22, c + 5), (c + 21, c + 11),
                                           (c + 16, c + 10)])
    pygame.draw.polygon(s, (246, 140, 44), [(c + 17, c + 5), (c + 20, c + 3),
                                            (c + 21, c + 6), (c + 20, c + 9),
                                            (c + 17, c + 9)])
    pygame.draw.rect(s, (255, 226, 132), (c + 17, c + 6, 3, 2))
    # Kopf: Gasmaske mit zwei gluehenden Glaesern und dem Filter vorn.
    pygame.draw.circle(s, (14, 12, 10), (c + 4, c - 1), 6)
    pygame.draw.circle(s, (48, 42, 38), (c + 4, c - 1), 5)
    pygame.draw.rect(s, (255, 196, 88), (c + 6, c - 4, 2, 2))
    pygame.draw.rect(s, (255, 196, 88), (c + 6, c + 1, 2, 2))
    pygame.draw.rect(s, (96, 90, 82), (c + 9, c - 2, 3, 3))
    return _rand(s)


@platzhalter("puppe")
def _puppe():
    """Die Zielpuppe im Schiessstand der Lobby.

    Von oben: ein Sandsack auf einem Pfahl, mit einem Querholz als Arme
    und einer aufgemalten Scheibe. Bewusst hell und rund, nichts daran
    sieht aus wie ein Zombie - im Schiessstand soll niemand zoegern, und
    im Gehege daneben soll niemand eine Puppe fuer einen Gegner halten.
    """
    s = _flaeche(28, 28)
    c = 14
    # Das Querholz, unter dem Sack.
    pygame.draw.rect(s, (54, 38, 24), (c - 2, c - 12, 5, 24))
    pygame.draw.rect(s, (112, 80, 48), (c - 1, c - 12, 3, 24))
    # Der Sack.
    pygame.draw.circle(s, (70, 58, 40), (c, c), 9)
    pygame.draw.circle(s, (176, 154, 110), (c, c), 8)
    pygame.draw.circle(s, (206, 186, 140), (c - 2, c - 2), 5)
    # Die Scheibe: rot, weiss, rot.
    pygame.draw.circle(s, (196, 58, 40), (c, c), 6, 2)
    pygame.draw.circle(s, (236, 230, 214), (c, c), 3)
    pygame.draw.circle(s, (196, 58, 40), (c, c), 1)
    # Die Naht, an der er zugebunden ist.
    pygame.draw.line(s, (96, 80, 56), (c + 6, c - 3), (c + 8, c - 5))
    return _rand(s)


@platzhalter("speichel")
def _speichel():
    # Der Spuck des Speiers. Gruen, damit man ihn nicht mit dem eigenen
    # Geschoss verwechselt - im Getuemmel ist das der ganze Unterschied.
    s = _flaeche(10, 6)
    pygame.draw.ellipse(s, (58, 88, 36), (0, 1, 10, 4))
    pygame.draw.ellipse(s, (126, 176, 86), (1, 1, 7, 4))
    pygame.draw.circle(s, (206, 240, 160), (7, 3), 2)
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


@platzhalter("munikiste")
def _munikiste():
    """Munitionskiste. Bewusst dem Medkit aehnlich im Umriss, aber in
    Messing statt Weiss - man soll auf einen Blick sehen, was da liegt."""
    w, h = K.BILD_MASS["munikiste"]
    s = _flaeche(w, h)
    pygame.draw.rect(s, (28, 22, 16), (0, 2, w, h - 2))
    pygame.draw.rect(s, (122, 96, 44), (1, 3, w - 2, h - 4))
    pygame.draw.rect(s, (168, 136, 66), (1, 3, w - 2, 2))
    pygame.draw.rect(s, (60, 46, 24), (1, h - 4, w - 2, 2))
    for x in range(4, w - 3, 4):            # angedeutete Patronen
        pygame.draw.rect(s, (206, 168, 82), (x, 6, 2, 4))
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


def _figur_boden(rumpf=None, kante=None):
    """Die liegende Gestalt, in den Farben einer Mannschaft.

    Auch am Boden muss man sehen, zu wem jemand gehoert - sonst rennt man
    quer ueber die Karte, um einem Gegner aufzuhelfen.
    """
    rumpf = rumpf or K.C_HULL_DK
    kante = kante or K.C_HULL_SH
    s = _flaeche(28, 28)
    c = 14
    pygame.draw.ellipse(s, (58, 22, 18), (4, 9, 20, 11))          # Lache
    pygame.draw.ellipse(s, (74, 28, 22), (7, 11, 14, 7))
    koerper = pygame.Rect(c - 9, c - 4, 18, 9)
    pygame.draw.ellipse(s, kante, koerper)
    pygame.draw.ellipse(s, rumpf, koerper.inflate(-3, -3))
    pygame.draw.circle(s, rumpf, (c - 8, c + 1), 4)
    pygame.draw.circle(s, kante, (c - 8, c + 1), 4, 1)
    pygame.draw.line(s, kante, (c - 1, c - 3), (c + 6, c - 7), 3)
    pygame.draw.line(s, kante, (c - 1, c + 4), (c + 7, c + 6), 3)
    return _rand(s, (16, 11, 8))


@platzhalter("spieler_boden")
def _spieler_boden():
    """Wer am Boden liegt. Muss sich auf einen Blick von einem Stehenden
    unterscheiden, auch fuer den Gegner auf der anderen Seite des Raums.

    Drei Unterschiede, die schon einzeln reichen wuerden: die Gestalt
    liegt quer statt aufrecht, sie hat keine Waffe in der Hand, und unter
    ihr steht eine dunkle Blutlache. Dazu ist sie merklich kleiner - eine
    liegende Gestalt nimmt von oben weniger Flaeche ein."""
    return _figur_boden()


@platzhalter("waffe_rauch")
def _waffe_rauch():
    s = _waffe()
    # Buechse statt Kugel, damit man sie in der Hotbar nicht mit der
    # Sprenggranate verwechselt. Heller Kopf, graue Schwaden.
    pygame.draw.rect(s, (96, 100, 96), (9, 2, 9, 8))
    pygame.draw.rect(s, (132, 138, 132), (10, 3, 3, 6))
    pygame.draw.rect(s, (40, 34, 24), (12, 0, 3, 3))     # Zuender
    pygame.draw.rect(s, K.C_CREAM, (12, 1, 2, 1))
    for x in (19, 21, 23):                               # Schwaden
        pygame.draw.rect(s, (168, 166, 160), (x, 3 + (x % 3), 1, 2))
    return s


@platzhalter("rauchgranate")
def _rauchgranate():
    s = _flaeche(10, 10)
    pygame.draw.ellipse(s, (92, 96, 92), (1, 1, 8, 8))
    pygame.draw.ellipse(s, (146, 150, 146), (2, 2, 5, 5))
    pygame.draw.rect(s, (40, 34, 24), (4, 0, 3, 3))
    pygame.draw.rect(s, K.C_CREAM, (4, 1, 2, 1))
    return _rand(s, (16, 12, 8))


@platzhalter("waffe_molotov")
def _waffe_molotov():
    s = _waffe()
    # Eine Flasche in der Seitenansicht: Bauch, Schulter, Hals, Lappen.
    # In der Hotbar muss man sie von der Buechse der Rauchgranate
    # unterscheiden koennen, und das schafft die Form des Halses.
    pygame.draw.rect(s, (46, 66, 44), (8, 3, 9, 7))
    pygame.draw.rect(s, (84, 116, 78), (9, 4, 7, 5))
    pygame.draw.rect(s, (132, 168, 120), (9, 4, 7, 1))     # Glanz oben
    pygame.draw.rect(s, (46, 66, 44), (17, 4, 3, 5))       # Schulter
    pygame.draw.rect(s, (38, 52, 38), (20, 5, 4, 3))       # Hals
    pygame.draw.rect(s, K.C_CREAM, (24, 4, 2, 4))          # Lappen
    pygame.draw.rect(s, (236, 150, 44), (25, 3, 1, 2))     # Flamme
    pygame.draw.rect(s, (252, 214, 120), (25, 3, 1, 1))
    return s


@platzhalter("molotov")
def _molotov():
    s = _flaeche(10, 10)
    pygame.draw.ellipse(s, (52, 74, 48), (1, 2, 8, 6))
    pygame.draw.ellipse(s, (96, 130, 88), (2, 3, 5, 3))
    pygame.draw.rect(s, (38, 52, 38), (4, 0, 3, 3))        # Hals mit Lappen
    pygame.draw.rect(s, K.C_CREAM, (4, 0, 3, 1))
    pygame.draw.rect(s, (240, 164, 56), (5, 0, 1, 1))
    return _rand(s, (16, 12, 8))


@platzhalter("waffe_rakete")
def _waffe_rakete():
    s = _waffe()
    pygame.draw.rect(s, (62, 58, 48), (2, 3, 19, 6))       # Rohr
    pygame.draw.rect(s, (104, 96, 78), (3, 4, 17, 2))
    pygame.draw.rect(s, (18, 16, 14), (2, 4, 2, 4))        # hinten offen
    pygame.draw.polygon(s, (150, 62, 40), [(20, 2), (25, 5), (25, 6), (20, 9)])
    pygame.draw.rect(s, (214, 96, 56), (21, 5, 3, 2))      # Sprengkopf
    pygame.draw.rect(s, (48, 44, 38), (8, 9, 4, 2))        # Griff
    return s


@platzhalter("flugrakete")
def _flugrakete():
    s = _flaeche(16, 8)
    pygame.draw.rect(s, (86, 80, 66), (3, 2, 9, 4))        # Koerper
    pygame.draw.rect(s, (140, 130, 106), (3, 2, 9, 1))
    pygame.draw.polygon(s, (170, 70, 44), [(12, 1), (15, 4), (12, 6)])
    pygame.draw.polygon(s, (52, 48, 40), [(3, 1), (0, 0), (0, 7), (3, 6)])
    pygame.draw.rect(s, (252, 208, 120), (0, 3, 2, 2))     # Strahl hinten
    return _rand(s, (16, 12, 8))


@platzhalter("rpg_kiste")
def _rpg_kiste():
    s = _flaeche(18, 14)
    pygame.draw.rect(s, (44, 48, 40), (0, 2, 18, 10))
    pygame.draw.rect(s, (72, 78, 64), (1, 3, 16, 8))
    pygame.draw.rect(s, (34, 36, 30), (1, 6, 16, 1))
    # Das Rohr obendrauf, damit man sie nicht mit einer Munikiste
    # verwechselt - eine Rakete liegt einmal in der Runde.
    pygame.draw.rect(s, (86, 80, 66), (2, 0, 12, 3))
    pygame.draw.polygon(s, (170, 70, 44), [(14, 0), (17, 1), (14, 3)])
    return _rand(s, (16, 12, 8))


@platzhalter("waffe_lmg")
def _waffe_lmg():
    s = _waffe()
    # Gross und schwer: langer dicker Lauf, Kastenmagazin darunter,
    # Zweibein vorn, breiter Schaft hinten. In der Hotbar muss man es
    # vom Scharfschuetzen unterscheiden koennen, und das schafft die
    # Dicke, nicht die Laenge.
    pygame.draw.rect(s, (48, 44, 38), (1, 3, 8, 5))        # Schaft
    pygame.draw.rect(s, (84, 78, 66), (2, 4, 6, 2))
    pygame.draw.rect(s, (92, 86, 70), (7, 3, 15, 5))       # Gehaeuse und Lauf
    pygame.draw.rect(s, (146, 136, 110), (7, 3, 15, 1))
    pygame.draw.rect(s, (44, 48, 44), (9, 8, 6, 3))        # Kastenmagazin
    pygame.draw.rect(s, (30, 28, 24), (22, 2, 3, 7))       # Muendungsbremse
    pygame.draw.line(s, (40, 38, 32), (18, 3), (21, 0))    # Zweibein
    pygame.draw.line(s, (40, 38, 32), (18, 8), (21, 10))
    return s


@platzhalter("waffe_blend")
def _waffe_blend():
    s = _waffe()
    # Eine glatte helle Walze mit Buegel. In der Hotbar muss sie sich von
    # der Buechse der Rauchgranate und der Flasche unterscheiden - das
    # macht hier die durchgehend helle Flaeche ohne Aufsatz.
    pygame.draw.rect(s, (110, 114, 118), (7, 3, 13, 6))
    pygame.draw.rect(s, (176, 182, 188), (8, 4, 11, 4))
    pygame.draw.rect(s, (232, 238, 244), (8, 4, 11, 1))
    pygame.draw.rect(s, (54, 56, 60), (20, 4, 3, 4))       # Kopf
    pygame.draw.rect(s, (236, 232, 200), (23, 5, 2, 2))    # Zuender
    pygame.draw.rect(s, (54, 56, 60), (10, 1, 7, 2))       # Buegel
    return s


@platzhalter("blendgranate")
def _blendgranate():
    s = _flaeche(10, 10)
    pygame.draw.ellipse(s, (108, 112, 116), (1, 2, 8, 6))
    pygame.draw.ellipse(s, (182, 188, 194), (2, 3, 5, 3))
    pygame.draw.rect(s, (52, 54, 58), (4, 0, 3, 3))
    pygame.draw.rect(s, (240, 238, 210), (4, 0, 2, 1))
    return _rand(s, (16, 12, 8))


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
