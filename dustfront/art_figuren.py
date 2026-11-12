"""
DUSTFRONT - Figuren aus dem Figurenpaket, gezeichnet (seit 0.34.60)
===================================================================

42 Figuren, in vier Runden mit dem Besitzer abgestimmt (Paket
`dustfront_figuren`): 14 Operators und 17 Soldaten - als Aussehen fuer
Spieler und Bots -, 8 NPCs und 3 Tiere. Die Daten stehen in
K.FIGUREN und K.TIERE; hier steht, wie daraus Pixel werden.

Neu geschrieben im Stil von art._figur, nicht aus dem Paket kopiert (dort
waren es Vorschau-Skripte, die einander zur Laufzeit flickten). Gezeichnet
wird in dieser Reihenfolge, wie im Paket abgenommen:

    was unter den Schultern liegt (Packen des Haendlers, Mantelschoss)
    Schultern mit Tarnflecken, Ghillie-Zotteln
    Weste und Abzeichen
    was auf dem Ruecken liegt (Funkgeraet, Rucksack, Fallschirm ...)
    Neon-Markierung der Mannschaft (Schulterstreifen)
    Arme und was in der Hand ist (die Waffe aus art._hand_waffe)
    Kopf
    der Leuchtfleck am Hinterkopf (Mannschaft)
    dunkler Rand (art._rand)

**Die Waffe kommt aus dem Spiel.** Jede Figur haelt, was sie traegt, an
derselben Stelle wie art._figur (Hand bei x = c + 6). Darum braucht ein
Skin fuer eine neue Waffe keine eigene Zeichnung.

**Bildnamen** entstehen aus einem Muster (`skin_<id>[_<team>][_<waffe>]`,
siehe `bildname`) und werden ueber core.platzhalter_muster gezeichnet:
31 Aussehen mal Mannschaft mal Waffe waeren sonst ueber tausend Eintraege
in BILD_MASS. Eine Datei `assets/skin_ghost_rot_sturm.png` ersetzt die
eine Figur trotzdem, wie jedes andere Bild.

Die Tiere sind Pixel fuer Pixel gesetzt, wie im Paket.
"""

from __future__ import annotations

import math
import random

import pygame

from . import art
from . import config as K
from .core import platzhalter, platzhalter_muster

draw = pygame.draw

_HAUT = (196, 150, 112)
_SCHWARZ = (34, 32, 30)
_GOLD = (222, 180, 70)
_WEISS = (226, 222, 210)
_OLIV = (92, 98, 62)
_NVG = (120, 255, 140)


def _hell(f, n=34):
    return tuple(max(0, min(255, k + n)) for k in f[:3])


def _misch(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


# ──────────────────────────────── Ruecken: unter und auf dem Leib

def _ruecken_vor(s, c, d) -> None:
    """Was unter den Schultern liegt."""
    r = d.get("ruecken")
    k = d["kante"]
    if r == "umhang":
        farbe = d.get("umhang", _misch(d["rumpf"], _SCHWARZ, 0.35))
        pts = [(c - 2, c - 9), (c - 11, c - 7), (c - 13, c - 3), (c - 12, c),
               (c - 13, c + 3), (c - 11, c + 7), (c - 2, c + 9)]
        draw.polygon(s, k, pts)
        draw.polygon(s, farbe, [(x + (1 if x < c - 3 else 0), y) for x, y in pts[1:-1]]
                     + [(c - 2, c + 7), (c - 2, c - 7)])
        draw.line(s, _hell(farbe, 18), (c - 10, c - 5), (c - 11, c + 5))
    elif r == "mantel":
        farbe = d.get("mantel", d["rumpf"])
        draw.ellipse(s, k, (c - 12, c - 7, 14, 14))
        draw.ellipse(s, farbe, (c - 11, c - 6, 12, 12))
        draw.line(s, _misch(farbe, k, 0.5), (c - 10, c), (c - 4, c))
    elif r == "tanks":
        for dy in (-7, 1):
            draw.rect(s, (40, 30, 24), (c - 13, c + dy - 1, 8, 8), border_radius=3)
            draw.rect(s, d.get("tank", (134, 120, 60)), (c - 12, c + dy, 6, 6), border_radius=2)
            draw.rect(s, _hell(d.get("tank", (134, 120, 60)), 40), (c - 12, c + dy + 1, 6, 1))
    elif r == "riesen":
        # Haendler: ein Packen, groesser als er selbst, mit Topf und Stangen
        draw.rect(s, (52, 36, 22), (c - 14, c - 9, 12, 18), border_radius=3)
        draw.rect(s, (138, 104, 64), (c - 13, c - 8, 10, 16), border_radius=2)
        draw.rect(s, (164, 128, 80), (c - 13, c - 8, 10, 3))
        draw.line(s, (84, 60, 36), (c - 13, c - 2), (c - 4, c - 2))
        draw.line(s, (84, 60, 36), (c - 13, c + 3), (c - 4, c + 3))
        draw.circle(s, (70, 72, 74), (c - 10, c + 5), 3)
        draw.circle(s, (130, 132, 134), (c - 10, c + 5), 2)
        draw.line(s, (110, 80, 44), (c - 14, c - 6), (c - 4, c - 11), 1)
        draw.line(s, (110, 80, 44), (c - 14, c - 3), (c - 5, c - 12), 1)
        draw.rect(s, d.get("akzent"), (c - 8, c - 7, 3, 3))


def _ruecken_auf(s, c, d) -> None:
    """Was oben auf dem Ruecken liegt."""
    r = d.get("ruecken")
    k = d["kante"]
    if r == "sprengpack":
        # Pionier: Rucksack mit zwei Sprengladungen und Zuendschnur.
        f = d.get("pack", (82, 88, 56))
        draw.rect(s, k, (c - 11, c - 6, 8, 12), border_radius=2)
        draw.rect(s, f, (c - 10, c - 5, 6, 10), border_radius=1)
        for y in (c - 4, c + 1):
            draw.rect(s, (40, 36, 26), (c - 10, y, 5, 3))
            draw.rect(s, (182, 172, 132), (c - 9, y, 4, 2))
        draw.line(s, (30, 30, 28), (c - 7, c - 2), (c - 4, c + 1))
        draw.rect(s, (60, 64, 44), (c - 5, c + 5, 3, 2))
    elif r == "buendel":
        draw.ellipse(s, (52, 40, 30), (c - 12, c - 4, 8, 9))
        draw.ellipse(s, (120, 64, 54), (c - 11, c - 3, 6, 7))
        draw.rect(s, (176, 150, 100), (c - 9, c - 3, 1, 7))
        draw.rect(s, (60, 44, 30), (c - 6, c, 2, 1))
    elif r == "tasche":
        draw.ellipse(s, (54, 40, 26), (c - 4, c + 5, 8, 6))      # an der Seite
        draw.ellipse(s, (128, 96, 60), (c - 3, c + 6, 6, 4))
        draw.line(s, (70, 52, 34), (c - 4, c - 6), (c + 1, c + 6))
    elif r == "fernglas":
        draw.rect(s, (34, 34, 30), (c - 3, c + 5, 5, 3))         # vor der Brust
        draw.rect(s, (70, 72, 64), (c - 2, c + 5, 1, 2))
        draw.rect(s, (70, 72, 64), (c + 1, c + 5, 1, 2))
        draw.rect(s, (120, 104, 70), (c - 10, c - 5, 6, 8), border_radius=1)  # Kartentasche
        draw.rect(s, (156, 140, 98), (c - 10, c - 5, 6, 2))
        draw.line(s, (60, 50, 34), (c - 4, c - 3), (c + 2, c - 7))
    elif r == "schulterlampe":
        draw.rect(s, (30, 30, 30), (c + 1, c - 8, 3, 2))
        draw.rect(s, (255, 236, 160), (c + 4, c - 8, 1, 2))
    elif r == "sanitasche_klein":
        draw.rect(s, k, (c - 10, c - 4, 6, 8), border_radius=2)
        draw.rect(s, (208, 204, 190), (c - 9, c - 3, 4, 6))
        draw.rect(s, K.C_RED, (c - 8, c - 2, 2, 4))
        draw.rect(s, K.C_RED, (c - 9, c - 1, 4, 2))
    elif r == "rucksack":
        f = d.get("pack", _misch(d["rumpf"], _OLIV, 0.4))
        draw.rect(s, k, (c - 11, c - 5, 8, 10), border_radius=2)
        draw.rect(s, f, (c - 10, c - 4, 6, 8), border_radius=1)
        draw.rect(s, _hell(f, 26), (c - 10, c - 4, 2, 8))
        draw.rect(s, _misch(f, _SCHWARZ, 0.4), (c - 7, c - 1, 2, 2))
    elif r == "funk":
        f = (62, 70, 52)
        draw.line(s, (24, 24, 20), (c - 9, c - 3), (c - 13, c - 12))   # Antenne
        draw.rect(s, (24, 24, 20), (c - 14, c - 13, 2, 2))
        draw.rect(s, k, (c - 11, c - 5, 8, 10), border_radius=1)
        draw.rect(s, f, (c - 10, c - 4, 6, 8))
        draw.rect(s, (96, 104, 84), (c - 10, c - 4, 6, 2))
        draw.rect(s, (220, 70, 40), (c - 6, c + 1, 1, 1))
        draw.rect(s, (40, 44, 34), (c - 9, c + 1, 2, 2))
    elif r == "sani":
        draw.rect(s, k, (c - 11, c - 5, 8, 10), border_radius=2)
        draw.rect(s, (208, 204, 190), (c - 10, c - 4, 6, 8), border_radius=1)
        draw.rect(s, K.C_RED, (c - 8, c - 3, 2, 6))
        draw.rect(s, K.C_RED, (c - 10, c - 1, 6, 2))
    elif r == "rolle":
        draw.rect(s, k, (c - 10, c - 9, 5, 18), border_radius=2)
        draw.rect(s, d.get("pack", (96, 84, 58)), (c - 9, c - 8, 3, 16))
        draw.rect(s, _hell(d.get("pack", (96, 84, 58)), 30), (c - 9, c - 8, 1, 16))
        for y in (c - 5, c + 4):
            draw.line(s, (40, 30, 20), (c - 10, y), (c - 6, y))
    elif r == "fallschirm":
        f = (80, 86, 58)
        draw.rect(s, k, (c - 12, c - 6, 9, 12), border_radius=3)
        draw.rect(s, f, (c - 11, c - 5, 7, 10), border_radius=2)
        draw.line(s, _hell(f, 24), (c - 11, c), (c - 5, c))
        draw.rect(s, (210, 70, 40), (c - 5, c + 3, 2, 2))           # Reissleine
    elif r == "sack":
        draw.ellipse(s, (60, 46, 30), (c - 13, c - 6, 10, 12))
        draw.ellipse(s, (150, 128, 88), (c - 12, c - 5, 8, 10))
        draw.ellipse(s, (176, 154, 110), (c - 11, c - 4, 4, 5))
        draw.rect(s, (96, 70, 40), (c - 5, c - 1, 2, 2))
    elif r == "kanister":
        draw.rect(s, (30, 26, 20), (c - 12, c - 5, 8, 10))
        draw.rect(s, (150, 60, 36), (c - 11, c - 4, 6, 8))
        draw.line(s, (188, 90, 56), (c - 11, c - 4), (c - 6, c + 3))
        draw.line(s, (188, 90, 56), (c - 11, c + 3), (c - 6, c - 4))
        draw.rect(s, (60, 60, 60), (c - 10, c - 7, 2, 2))
    elif r == "schwert":
        # Scheide schraeg ueber den Ruecken, Griff ueber der Schulter
        draw.line(s, (24, 18, 16), (c - 11, c + 7), (c - 1, c - 8), 3)
        draw.line(s, (120, 40, 36), (c - 11, c + 7), (c - 3, c - 5), 1)
        draw.rect(s, _GOLD, (c - 3, c - 6, 2, 2))
        draw.line(s, (210, 200, 180), (c - 1, c - 8), (c + 1, c - 11), 2)
    elif r == "tanks":
        draw.lines(s, (30, 24, 20), False, [(c - 7, c + 4), (c - 1, c + 9), (c + 7, c + 6)], 1)


# ──────────────────────────────── Leib, Weste, Ghillie

def _leib(s, c, d) -> pygame.Rect:
    rumpf, kante = d["rumpf"], d["kante"]
    breit = d.get("breit", False)
    schulter = pygame.Rect(c - 7, c - (9 if breit else 8), 14, (18 if breit else 16))
    draw.ellipse(s, kante, schulter)
    draw.ellipse(s, rumpf, schulter.inflate(-3, -3))
    if d.get("tarn"):
        # GRUND fuer den Namen als Saat: jede Figur behaelt ihr Muster, auf
        # jedem Rechner dasselbe (random.Random mit Text ist festgelegt).
        rnd = random.Random(d["name"])
        innen = schulter.inflate(-4, -4)
        for _ in range(9):
            x = rnd.randint(innen.left, innen.right - 2)
            y = rnd.randint(innen.top, innen.bottom - 2)
            if innen.collidepoint(x, y):
                f = d["tarn"][rnd.randrange(len(d["tarn"]))]
                draw.rect(s, f, (x, y, rnd.choice((2, 3)), 2))
    draw.ellipse(s, _hell(rumpf), schulter.inflate(-3, -3).move(0, -2), 1)
    return schulter


def _weste(s, c, d, schulter) -> None:
    w = d.get("weste")
    v = d.get("westenfarbe", _misch(d["rumpf"], _SCHWARZ, 0.35))
    if w in ("platten", "schwer"):
        oben, unten = schulter.top + 1, schulter.bottom - 4
        for y in (oben, unten):
            draw.rect(s, d["kante"], (c - 5, y, 10, 3))
            draw.rect(s, v, (c - 4, y, 8, 3))
            for x in (c - 3, c, c + 3):                               # Taschen
                draw.rect(s, _hell(v, 22), (x, y + 1, 2, 1))
        draw.rect(s, v, (c - 6, c - 4, 3, 8))                         # Rueckenplatte
        draw.rect(s, _hell(v, 16), (c - 6, c - 4, 1, 8))
        if w == "schwer":                                             # Schulterschutz
            for y in (schulter.top - 1, schulter.bottom - 3):
                draw.ellipse(s, d["kante"], (c - 3, y, 7, 4))
                draw.ellipse(s, _hell(v, 30), (c - 2, y + 1, 5, 2))
    elif w == "bandelier":
        draw.line(s, (60, 40, 24), (c - 6, c - 6), (c + 4, c + 7), 2)
        for t in (0.1, 0.3, 0.75, 0.92):
            draw.rect(s, d.get("patronen", _GOLD), (int(c - 6 + 10 * t), int(c - 6 + 13 * t), 1, 1))
    elif w == "granaten":
        draw.line(s, (60, 40, 24), (c - 6, c - 6), (c + 4, c + 7), 2)
        for x, y in ((c - 5, c - 6), (c + 2, c + 5)):
            draw.circle(s, (70, 82, 56), (x, y), 2)
            draw.rect(s, K.C_AMBER, (x, y - 2, 1, 1))
    elif w == "kreuz":
        for a, b in (((c - 6, c - 6), (c + 3, c + 7)), ((c - 6, c + 6), (c + 3, c - 7))):
            draw.line(s, (54, 40, 26), a, b, 1)
    if d.get("rang"):
        for i in range(d["rang"]):
            draw.line(s, _GOLD, (c - 5 + i * 2, schulter.top + 1), (c - 5 + i * 2, schulter.top + 2))
            draw.line(s, _GOLD, (c - 5 + i * 2, schulter.bottom - 3),
                      (c - 5 + i * 2, schulter.bottom - 2))
    if d.get("armbinde"):
        draw.rect(s, _WEISS, (c, schulter.bottom - 3, 3, 2))
        draw.rect(s, K.C_RED, (c + 1, schulter.bottom - 3, 1, 2))
    if d.get("ausweis"):
        draw.rect(s, (230, 230, 220), (c - 2, schulter.bottom - 4, 3, 2))
        draw.rect(s, (70, 120, 170), (c - 2, schulter.bottom - 4, 1, 2))
    if d.get("offizier"):
        # Schulterklappen mit zwei hellen Sternen, hinten an der Schulter -
        # so bleibt die Mitte frei fuer die Neon-Markierung der Mannschaft.
        for y in (schulter.top + 1, schulter.bottom - 3):
            draw.rect(s, (58, 62, 38), (c - 7, y, 4, 2))
            draw.rect(s, (214, 216, 200), (c - 7, y, 1, 1))
            draw.rect(s, (214, 216, 200), (c - 5, y, 1, 1))


def _ghillie(s, c, d) -> None:
    """Zotteln rund um die Schultern - der Umriss loest sich auf."""
    rnd = random.Random(d["name"] + "g")
    farben = d.get("tarn") or [(74, 84, 46), (98, 96, 58), (62, 58, 36)]
    for i in range(30):
        a = rnd.uniform(0, 6.283)
        if abs(math.cos(a)) > 0.92 and math.cos(a) > 0:
            continue                                                 # vorn frei
        r0 = rnd.uniform(4, 7)
        r1 = r0 + rnd.uniform(2, 4)
        x0, y0 = c + math.cos(a) * r0 * 0.9, c + math.sin(a) * r0 * 1.1
        x1, y1 = c + math.cos(a) * r1 * 0.95, c + math.sin(a) * r1 * 1.15
        draw.line(s, farben[i % len(farben)], (x0, y0), (x1, y1), 1)


def _markierung(s, c, d, kern, licht) -> None:
    """Die Mannschaft: zwei Neon-Streifen auf den Schultern (der Fleck am
    Hinterkopf kommt nach dem Kopf, siehe `figur`)."""
    breit = d.get("breit", False)
    oben, unten = c - (9 if breit else 8) + 1, c + (9 if breit else 8) - 3
    for y in (oben, unten):
        draw.rect(s, kern, (c - 3, y, 5, 2))
        draw.rect(s, licht, (c - 2, y, 3, 1))
    hx = c + 1
    draw.rect(s, kern, (hx - 5, c - 1, 2, 3))
    draw.rect(s, licht, (hx - 5, c, 1, 1))


# ──────────────────────────────── Arme

def _hand(s, k, haut, x, y) -> None:
    draw.circle(s, k, (x, y), 2)
    draw.circle(s, haut, (x, y), 1)


def _aermel(s, k, farbe, a, b) -> None:
    """Ein Arm als eigener Aermel mit Rand: ein dunkler Strich allein
    verschmolz beim Hirten mit Leib und Kopftuch (Runde 4)."""
    draw.line(s, k, a, b, 4)
    draw.line(s, farbe, a, b, 2)


def _schild(s, c, d) -> None:
    """Leicht gewoelbt, drei Pixel dick: die Enden liegen weiter hinten als
    die Mitte. Zeilenweise gesetzt, damit die Kruemmung auf 28 px sauber
    bleibt (Runde 3)."""
    farbe = d.get("schildfarbe", (74, 84, 64))
    for dy in range(-12, 13):
        x = c + 11 - round(dy * dy / 36)
        draw.rect(s, _misch(farbe, _SCHWARZ, 0.35), (x - 2, c + dy, 1, 1))
        draw.rect(s, farbe, (x - 1, c + dy, 1, 1))
        draw.rect(s, _hell(farbe, 40) if abs(dy) < 9 else farbe, (x, c + dy, 1, 1))
    draw.rect(s, (24, 28, 30), (c + 9, c - 2, 2, 4))                  # Sichtfenster
    draw.rect(s, (150, 190, 200), (c + 10, c - 1, 1, 2))


@platzhalter("schild_klasse")
def _schild_klasse():
    """Das Schild der Klasse SCHILDTRAEGER (seit 0.34.138, gemeldet: "das
    Schild wird einfach nicht gerendert" - es hing bisher nur an Aussehen, die
    selbst eines tragen). Dieselbe Form, ueber die Figur gelegt; die Mitte des
    Bildes ist die Mitte der Figur."""
    f = pygame.Surface((32, 32), pygame.SRCALPHA)
    _schild(f, 16, {"schildfarbe": (78, 90, 70)})
    return f


def _arme(s, c, d, waffe, stummel: bool = True, arme_an: bool = True) -> None:
    """Arme und was in der Hand ist. `waffe`: die Waffe aus
    art._hand_waffe. Ohne Waffe und mit `stummel` der alte Gewehrstummel
    wie bei art._figur; ohne `stummel` gar nichts (ein Insasse haelt, was
    zum Fahrzeug gehoert)."""
    if not arme_an:
        return
    a = d.get("arme", "waffe")
    k = d["kante"]
    haut = d.get("handschuh", d.get("haut", _HAUT))
    if a == "waffe":
        draw.line(s, k, (c + 1, c - 5), (c + 8, c - 3), 3)
        draw.line(s, k, (c + 1, c + 5), (c + 8, c + 3), 3)
        if waffe:
            art._hand_waffe(s, c, waffe)
        elif stummel:
            draw.rect(s, (30, 25, 19), (c + 6, c - 2, 12, 4))
            draw.rect(s, (86, 72, 52), (c + 6, c - 1, 10, 2))
    elif a == "vorne":
        # Kurz: die Haende liegen direkt vor den Schulterecken - dort
        # reicht der Kopf nicht hin, sie bleiben sichtbar (Runde 4).
        draw.line(s, k, (c + 2, c - 5), (c + 5, c - 4), 3)
        draw.line(s, k, (c + 2, c + 5), (c + 5, c + 4), 3)
        _hand(s, k, haut, c + 7, c - 4)
        _hand(s, k, haut, c + 7, c + 4)
    elif a == "halb_vorne":
        # Hirte: links (oben im Bild) nach vorn, rechts haengt an der
        # Seite - beide als eigene Aermel.
        farbe = d.get("aermel", (104, 78, 52))
        _aermel(s, k, farbe, (c + 2, c - 5), (c + 6, c - 5))
        _hand(s, k, haut, c + 8, c - 5)
        _aermel(s, k, farbe, (c - 1, c + 7), (c + 2, c + 9))
        _hand(s, k, haut, c + 3, c + 10)
    elif a == "schild":
        draw.line(s, k, (c + 1, c - 5), (c + 7, c - 4), 3)
        draw.line(s, k, (c + 1, c + 5), (c + 7, c + 4), 3)
        _schild(s, c, d)
    elif a == "klemmbrett":
        # Klein, in einer Hand seitlich vorn, mit Klammer und Zeilen.
        draw.line(s, k, (c + 1, c - 5), (c + 6, c - 3), 3)
        draw.line(s, k, (c + 1, c + 5), (c + 7, c + 4), 3)
        _hand(s, k, haut, c + 7, c - 3)
        draw.rect(s, (60, 42, 26), (c + 7, c + 1, 6, 8))
        draw.rect(s, (226, 222, 208), (c + 8, c + 2, 4, 6))
        draw.rect(s, (168, 172, 176), (c + 9, c + 1, 2, 2))
        for y in (c + 4, c + 6):
            draw.line(s, (130, 128, 120), (c + 8, y), (c + 10, y))
    elif a == "pistole":
        draw.line(s, k, (c + 1, c - 5), (c + 9, c - 1), 3)
        draw.line(s, k, (c + 1, c + 5), (c + 9, c + 1), 3)
        draw.rect(s, (30, 28, 26), (c + 9, c - 1, 6, 3))
        draw.rect(s, (96, 92, 84), (c + 10, c - 1, 4, 1))
    elif a == "leer":
        for dy in (-1, 1):
            draw.circle(s, k, (c + 2, c + dy * 8), 2)
            draw.circle(s, haut, (c + 2, c + dy * 8), 1)
    elif a in ("laterne", "geigerzaehler"):
        draw.line(s, k, (c + 1, c - 5), (c + 7, c - 4), 3)
        draw.line(s, k, (c + 1, c + 5), (c + 8, c + 4), 3)
        if a == "laterne":
            draw.circle(s, (120, 76, 24), (c + 10, c + 5), 4)
            draw.circle(s, (250, 200, 90), (c + 10, c + 5), 2)
            draw.circle(s, (255, 244, 200), (c + 10, c + 5), 1)
        else:
            draw.rect(s, (200, 170, 40), (c + 7, c + 2, 5, 4))
            draw.rect(s, (60, 80, 40), (c + 8, c + 3, 2, 2))
            draw.line(s, (40, 40, 40), (c + 12, c + 4), (c + 13, c + 2))


# ──────────────────────────────── Kopf

def _kopf(s, c, d) -> None:
    t = d.get("kopf", "nackt")
    k, akz = d["kante"], d["akzent"]
    haut = d.get("haut", _HAUT)
    hx, hy = c + 1, c
    f = d.get("kopffarbe", _hell(d["rumpf"]))

    def grund(farbe, r=5):
        draw.circle(s, k, (hx, hy), r)
        draw.circle(s, farbe, (hx, hy), r - 1)

    def brille():
        if d.get("brille"):
            draw.rect(s, (20, 20, 20), (hx + 3, hy - 2, 1, 4))

    if t == "totenkopf":
        # Von oben sieht man vom Gesicht nur den vorderen Rand: der
        # Schaedel ist eine helle Sichel vorn (Runde 2), ohne den
        # einzelnen untersten Pixel (Runde 3).
        grund((30, 30, 32))
        draw.circle(s, (48, 48, 52), (hx - 1, hy - 1), 2)
        draw.arc(s, (214, 210, 196), (hx - 4, hy - 4, 9, 9), -1.05, 1.05, 2)
        for y in (hy - 2, hy + 1):                                    # Augenhoehlen
            draw.rect(s, (12, 12, 12), (hx + 3, y, 1, 2))
            draw.rect(s, akz, (hx + 3, y, 1, 1))
        draw.rect(s, (12, 12, 12), (hx + 4, hy, 1, 1))                # Nasenloch
        brille()
        draw.rect(s, (30, 30, 32), (hx + 2, hy + 3, 1, 1))
    elif t == "nvg":
        # Drei Roehren auf der Stirn, nicht auf der Waffe (Runde 2 und 3).
        grund(f)
        draw.circle(s, _hell(f, 26), (hx - 1, hy - 1), 2)
        draw.rect(s, (28, 28, 28), (hx, hy - 3, 3, 7))
        for y in (hy - 2, hy, hy + 2):
            draw.rect(s, _NVG if d.get("nvg_an") else (60, 70, 66), (hx + 3, y, 1, 1))
    elif t == "kapuze_augen":
        # Gesicht im Schatten der Kapuze, zwei gluehende Augen weit
        # auseinander - zwei Punkte am Rand lasen sich wie ein Nachtsichtgeraet.
        draw.ellipse(s, k, (hx - 7, hy - 5, 12, 10))
        draw.ellipse(s, f, (hx - 6, hy - 4, 10, 8))
        draw.ellipse(s, _hell(f, 18), (hx - 5, hy - 3, 5, 4))
        draw.ellipse(s, (12, 10, 10), (hx, hy - 3, 5, 7))
        glut = _misch(akz, (12, 10, 10), 0.55)
        for y in (hy - 2, hy + 2):
            draw.rect(s, glut, (hx + 1, y, 1, 1))
            draw.rect(s, akz, (hx + 2, y, 1, 1))
    elif t in ("feldmuetze", "feldmuetze_offizier"):
        # Weiche Feldmuetze im Oliv der Truppe, kurzer Schirm, kein Gold.
        grund(f)
        draw.circle(s, _hell(f, 20), (hx - 1, hy - 1), 2)
        draw.line(s, _misch(f, k, 0.45), (hx - 3, hy - 3), (hx - 3, hy + 3))
        draw.ellipse(s, k, (hx + 2, hy - 3, 4, 6))
        draw.ellipse(s, _misch(f, k, 0.35), (hx + 3, hy - 2, 2, 4))
        brille()
        if t == "feldmuetze_offizier":
            draw.rect(s, (206, 210, 196), (hx + 1, hy - 1, 2, 2))     # Abzeichen vorn
    elif t == "nvg2":
        grund(f)
        draw.circle(s, _hell(f, 26), (hx - 1, hy - 1), 2)
        draw.rect(s, (28, 28, 28), (hx, hy - 2, 3, 4))
        for y in (hy - 2, hy + 1):
            draw.rect(s, akz, (hx + 3, y, 1, 1))
        draw.rect(s, (30, 30, 30), (hx - 5, hy - 1, 2, 2))
        brille()
    elif t == "headset_maske":
        # Ganz verhuellt: Sturmhaube, Schneebrille, Headset - keine Haut.
        grund(f)
        draw.circle(s, _hell(f, 22), (hx - 1, hy - 1), 2)
        draw.rect(s, (24, 26, 30), (hx + 2, hy - 3, 2, 6))
        draw.rect(s, akz, (hx + 3, hy - 2, 1, 4))
        draw.line(s, (26, 26, 26), (hx - 1, hy - 5), (hx - 1, hy + 5), 1)
        for dy in (-5, 4):
            draw.rect(s, (30, 30, 30), (hx - 2, hy + dy, 3, 2))
        draw.line(s, (30, 30, 30), (hx, hy + 5), (hx + 4, hy + 4))
        brille()
    elif t == "kapuze_offen":
        # Kapuze ohne Umhang: liegt nur auf Kopf und Nacken.
        draw.ellipse(s, k, (hx - 7, hy - 5, 12, 10))
        draw.ellipse(s, f, (hx - 6, hy - 4, 10, 8))
        draw.ellipse(s, _hell(f, 18), (hx - 5, hy - 3, 5, 4))
        draw.circle(s, (14, 12, 10), (hx + 3, hy), 2)
        draw.rect(s, akz, (hx + 4, hy - 1, 1, 1))
        draw.rect(s, akz, (hx + 4, hy + 1, 1, 1))
        brille()
    else:
        _kopf_grund(s, c, d, t, f, haut, grund)


def _kopf_grund(s, c, d, t, f, haut, grund) -> None:
    """Die Koepfe, die seit der ersten Runde so geblieben sind."""
    k, akz = d["kante"], d["akzent"]
    hx, hy = c + 1, c
    if t == "nackt":
        grund(_hell(d["rumpf"]))
        draw.circle(s, akz, (c + 3, c), 2)
    elif t in ("helm", "visier", "kamera_helm"):
        grund(f)
        draw.circle(s, _hell(f, 26), (hx - 1, hy - 1), 2)
        draw.line(s, _misch(f, k, 0.5), (hx - 3, hy), (hx + 3, hy))   # Bezugnaht
        if t == "helm":
            draw.rect(s, akz, (c + 4, c - 2, 2, 4))                    # Schutzbrille
        elif t == "visier":
            draw.arc(s, (20, 22, 24), (hx - 5, hy - 5, 11, 11), -1.1, 1.1, 2)
            draw.arc(s, akz, (hx - 4, hy - 4, 9, 9), -0.9, 0.9, 1)
        else:
            draw.rect(s, akz, (c + 4, c - 2, 2, 4))
            draw.rect(s, (24, 24, 26), (hx - 1, hy - 6, 3, 2))         # Helmkamera
            draw.rect(s, (220, 60, 40), (hx + 1, hy - 6, 1, 1))
    elif t == "barett":
        grund(haut, 5)
        draw.ellipse(s, k, (hx - 6, hy - 6, 9, 11))
        draw.ellipse(s, f, (hx - 5, hy - 5, 7, 9))
        draw.rect(s, _GOLD, (hx - 3, hy - 4, 2, 2))
        draw.circle(s, akz, (c + 4, c), 1)
    elif t in ("kappe", "kappe_rueck"):
        grund(f)
        schirm = (c + 3, c - 3, 5, 6) if t == "kappe" else (hx - 7, hy - 3, 5, 6)
        draw.ellipse(s, k, schirm)
        draw.ellipse(s, _misch(f, k, 0.3), pygame.Rect(schirm).inflate(-2, -2))
        draw.rect(s, _hell(f, 30), (hx - 1, hy, 1, 1))
        if t == "kappe_rueck":
            draw.circle(s, akz, (c + 4, c), 1)
    elif t == "muetze":
        grund(f)
        draw.circle(s, _misch(f, k, 0.4), (hx, hy), 3, 1)
        draw.circle(s, _hell(f, 30), (hx - 1, hy), 1)
        draw.circle(s, akz, (c + 4, c), 1)
    elif t == "shemagh":
        grund(f)
        rnd = random.Random(d["name"] + "s")
        for _ in range(6):
            draw.rect(s, _misch(f, k, 0.45),
                      (hx - 3 + rnd.randint(0, 5), hy - 3 + rnd.randint(0, 5), 1, 1))
        draw.polygon(s, k, [(hx - 3, hy - 2), (hx - 9, hy + 1), (hx - 8, hy + 4), (hx - 3, hy + 3)])
        draw.polygon(s, f, [(hx - 3, hy - 1), (hx - 8, hy + 2), (hx - 3, hy + 2)])
        draw.rect(s, akz, (c + 4, c - 2, 2, 4))
    elif t == "haube":
        grund(f)
        for dy in (-2, 0, 2):
            draw.line(s, _misch(f, k, 0.45), (hx - 3, hy + dy), (hx + 2, hy + dy))
        for dy in (-5, 5):
            draw.circle(s, k, (hx, hy + dy), 2)
            draw.circle(s, _misch(f, k, 0.3), (hx, hy + dy), 1)
        draw.rect(s, akz, (hx + 2, hy - 3, 2, 6))
    elif t == "kopfhoerer":
        grund(f)                                                      # Haar
        draw.circle(s, haut, (hx + 3, hy), 2)
        draw.line(s, (26, 26, 26), (hx, hy - 5), (hx, hy + 5), 1)
        for dy in (-5, 4):
            draw.rect(s, (30, 30, 30), (hx - 1, hy + dy, 3, 2))
        draw.line(s, (30, 30, 30), (hx + 1, hy + 5), (hx + 4, hy + 3))
        draw.rect(s, akz, (hx + 4, hy + 2, 1, 1))
    elif t == "glatze":
        grund(haut)
        draw.circle(s, _hell(haut, 30), (hx - 1, hy - 1), 1)
        draw.rect(s, _misch(haut, k, 0.3), (hx, hy - 5, 1, 1))
        draw.rect(s, _misch(haut, k, 0.3), (hx, hy + 4, 1, 1))
    elif t in ("haar", "zopf"):
        if t == "zopf":
            draw.ellipse(s, k, (hx - 9, hy - 2, 6, 4))
            draw.ellipse(s, f, (hx - 8, hy - 1, 4, 2))
        grund(f)
        draw.circle(s, haut, (hx + 3, hy), 2)
        draw.circle(s, _hell(f, 24), (hx - 2, hy - 1), 1)
    elif t == "stirnband":
        grund(f)
        draw.circle(s, haut, (hx + 3, hy), 2)
        draw.circle(s, akz, (hx, hy), 4, 1)
        draw.line(s, akz, (hx - 4, hy), (hx - 9, hy - 2))
        draw.line(s, akz, (hx - 4, hy + 1), (hx - 9, hy + 3))
    elif t == "boonie":
        draw.circle(s, k, (hx, hy), 7)
        draw.circle(s, f, (hx, hy), 6)
        draw.circle(s, _misch(f, k, 0.35), (hx, hy), 4)
        draw.circle(s, _hell(f, 18), (hx - 1, hy - 1), 3)
        for dx, dy in ((-4, 3), (3, -4), (-2, -4)):
            draw.rect(s, _misch(f, (50, 60, 30), 0.5), (hx + dx, hy + dy, 2, 1))
    elif t == "turban":
        grund(f, 6)
        draw.arc(s, _misch(f, k, 0.35), (hx - 4, hy - 4, 9, 9), 0.6, 4.5, 1)
        draw.arc(s, _misch(f, k, 0.35), (hx - 2, hy - 2, 5, 5), 2.0, 5.5, 1)
        draw.rect(s, akz, (hx + 4, hy - 1, 2, 2))
    elif t == "pilot":
        grund(f)
        draw.circle(s, _hell(f, 30), (hx - 1, hy - 1), 2)
        draw.arc(s, (16, 18, 24), (hx - 5, hy - 5, 11, 11), -1.2, 1.2, 3)
        draw.arc(s, akz, (hx - 4, hy - 4, 9, 9), -0.6, 0.2, 1)
        draw.line(s, (30, 30, 30), (hx + 3, hy + 3), (hx - 2, hy + 7), 1)  # Schlauch
    elif t == "kopftuch":
        grund(f)
        draw.circle(s, haut, (hx + 3, hy), 2)
        for dx, dy in ((-2, -2), (0, 2), (-3, 1)):
            draw.rect(s, akz, (hx + dx, hy + dy, 1, 1))
        draw.circle(s, k, (hx - 5, hy), 2)
        draw.circle(s, f, (hx - 5, hy), 1)
    if d.get("brille"):
        draw.rect(s, (20, 20, 20), (hx + 3, hy - 2, 1, 4))
        draw.rect(s, (180, 220, 230), (hx + 4, hy - 2, 1, 1))
        draw.rect(s, (180, 220, 230), (hx + 4, hy + 1, 1, 1))


# ──────────────────────────────── Die Figur

def figur(d: dict, waffe=None, team=None, groesse=None, stummel: bool = True,
          arme_an: bool = True, schwung=None) -> pygame.Surface:
    """Eine Figur aus K.FIGUREN (`d` ist ihr Eintrag). `team` "ROT" oder
    "BLAU" legt die Neon-Markierung darauf, sonst keine. `groesse` wie bei
    art._figur: 28, mit Waffe 56. `schwung`: der Winkel des Brecheisens
    mitten im Schlag (art.schwung_arme) statt der Waffe."""
    groesse = groesse or (64 if schwung is not None else 56 if waffe else 28)
    s = pygame.Surface((groesse, groesse), pygame.SRCALPHA)
    c = groesse // 2
    _ruecken_vor(s, c, d)
    schulter = _leib(s, c, d)
    if d.get("ghillie"):
        _ghillie(s, c, d)
    _weste(s, c, d, schulter)
    _ruecken_auf(s, c, d)
    neon = K.FIGUREN_NEON.get(team) if team else None
    if neon:
        _markierung(s, c, d, *neon)
    if schwung is not None:
        art.schwung_arme(s, c, d["kante"], schwung)
    else:
        _arme(s, c, d, waffe, stummel, arme_an)
    _kopf(s, c, d)
    if neon:
        # Der Fleck am Hinterkopf soll auch ueber Helm und Kapuze leuchten.
        draw.rect(s, neon[0], (c - 4, c - 1, 1, 3))
        draw.rect(s, neon[1], (c - 4, c, 1, 1))
    return art._rand(s)


def standard(rumpf, kante, akzent) -> dict:
    """Die Standardfigur als Eintrag wie in K.FIGUREN (seit 0.34.77).

    Gemeldet: "die Standard-Skins neu, damit sie mehr zu den neueren
    passen - gleich aussehen, aber im Stil". Dieselben Farben wie die alte
    Figur (art._figur): Grundton, dunkle Kante, Akzent als Schutzbrille -
    dazu, was jeder neue Skin hat: Tarnflecken im eigenen Ton, eine
    Plattenweste, ein Helm mit Bezugnaht."""
    return {"name": "STANDARD %s" % (tuple(rumpf),), "rumpf": tuple(rumpf), "kante": tuple(kante),
            "akzent": tuple(akzent), "kopf": "helm", "kopffarbe": _hell(rumpf, 20),
            "tarn": (_misch(rumpf, kante, 0.25), _hell(rumpf, 16), _misch(rumpf, kante, 0.45)),
            "weste": "platten", "westenfarbe": _misch(rumpf, kante, 0.4)}


def standard_figur(rumpf, kante, akzent, waffe=None, team=None, groesse=None,
                   schwung=None, stummel: bool = True) -> pygame.Surface:
    """Die Standardfigur im Stil der Skins (siehe `standard`)."""
    return figur(standard(rumpf, kante, akzent), waffe, team, groesse, stummel=stummel,
                 schwung=schwung)


def mit_fester_hand(skin: str) -> bool:
    """Haelt diese Figur etwas Festes (Schild, Pistole, Klemmbrett)? Dann
    kann sie keine gewaehlte Waffe zeigen - und ist kein Aussehen fuer
    Spieler (README: "Man sieht, was man tut")."""
    return K.FIGUREN.get(skin, {}).get("arme", "waffe") != "waffe"


def waehlbar() -> list:
    """Die Aussehen fuer Spieler und Bots: Operators und Soldaten, die eine
    Waffe in der Hand halten koennen - in der Reihenfolge des Pakets."""
    return [s for g in ("OPERATOR", "SOLDAT") for s in K.FIGUREN_GRUPPEN[g]
            if not mit_fester_hand(s)]


def saeubern(wert) -> str:
    """Ein Aussehen, wie es aus dem Netz oder der Einstellung kommt: eine
    bekannte, waehlbare Kennung - sonst leer (die alte Figur). Ein Gast
    kann so nichts verlangen, was es nicht gibt oder keine Waffe zeigt."""
    if isinstance(wert, str) and wert in K.FIGUREN and not mit_fester_hand(wert):
        return wert
    return ""


def name_zeigen(skin: str) -> str:
    """Wie ein Aussehen im Menue heisst ("" ist die alte Figur)."""
    return K.FIGUREN[skin]["name"] if skin in K.FIGUREN else "STANDARD"


# ──────────────────────────────── Bildnamen

_TEAMS = tuple(kombi["name"].lower() for kombi in K.TEAMS["kombi"])


def bildname(skin: str, team_vorsatz: str = "", gehalten: str = "") -> str:
    """`skin_<id>[_<team>][_<waffe>]`, wie spieler_<team>_<waffe>, und
    `skin_<id>[_<team>]_schwung_<i>` fuer den Schlag mit dem Brecheisen.
    `team_vorsatz` ist der Vorsatz der Figur ("rot_", "blau_" oder leer)."""
    name = "skin_%s" % skin
    if team_vorsatz:
        name += "_" + team_vorsatz.rstrip("_")
    if gehalten and not mit_fester_hand(skin):
        name += "_" + gehalten
    return name


_NACH_LAENGE: list = []


def _skin_team(rest: str):
    """<id>[_<team>]<rest> -> (id, TEAM oder None, rest ohne Trenner) oder
    None. Die laengste Kennung zuerst: "schuetze" steckt in
    "scharfschuetze" nicht vorn, aber "mg_schuetze" beginnt mit "mg"."""
    # Die Reihenfolge einmal (seit 0.34.75), nicht bei jedem Aufruf neu
    # sortiert - K.FIGUREN aendert sich nach dem Laden nicht.
    if len(_NACH_LAENGE) != len(K.FIGUREN):
        _NACH_LAENGE[:] = sorted(K.FIGUREN, key=len, reverse=True)
    for skin in _NACH_LAENGE:
        if rest == skin or rest.startswith(skin + "_"):
            teile = rest[len(skin) + 1:]
            team = None
            for t in _TEAMS:
                if teile == t or teile.startswith(t + "_"):
                    team, teile = t.upper(), teile[len(t) + 1:]
                    break
            return skin, team, teile
    return None


def _zerlegen(name: str):
    """skin_<id>[_<team>][_<waffe> | _schwung_<i>] -> (id, TEAM oder None,
    waffe oder None, Schwungbild oder None). None, wenn der Name nicht
    passt."""
    teile = _skin_team(name[len("skin_"):])
    if teile is None:
        return None
    skin, team, rest = teile
    schwung = None
    if rest.startswith("schwung_"):
        try:
            schwung = int(rest[len("schwung_"):])
        except ValueError:
            return None
        if not 0 <= schwung < K.SCHWUNG_BILDER:
            return None
        rest = ""
    waffe = rest or None
    if waffe is not None and (waffe not in K.WAFFEN_HAND or mit_fester_hand(skin)):
        return None
    return skin, team, waffe, schwung


def skin_mass(name: str):
    """Das Sollmass eines Skin-Bildes (wie spieler / spieler_<waffe> /
    spieler_schwung_<i>)."""
    teile = _zerlegen(name) if name.startswith("skin_") else None
    if teile is None:
        return None
    _skin, _team, waffe, schwung = teile
    if schwung is not None:
        return K.BILD_MASS["spieler_schwung_%d" % schwung]
    return K.BILD_MASS["spieler_" + waffe] if waffe else K.BILD_MASS["spieler"]


def _skin_zeichnen(name: str):
    teile = _zerlegen(name)
    if teile is None:
        return None
    skin, team, waffe, schwung = teile
    winkel = None if schwung is None else art.schwung_winkel(schwung)
    return figur(K.FIGUREN[skin], waffe, team, skin_mass(name)[0], schwung=winkel)


platzhalter_muster("skin_", _skin_zeichnen, skin_mass)


# ──────────────────────────────── Insassen

def insasse(fahrer: dict, arme=8) -> pygame.Surface:
    """Ein Insasse im Aussehen seines Skins (art._insasse_auf): ohne Waffe,
    die Haende am Fahrzeug, ohne Arme in der Luke. `fahrer` =
    {"skin": id, "team": "ROT"/"BLAU"/None}."""
    d = K.FIGUREN[fahrer["skin"]]
    return figur(d, None, fahrer.get("team"), 28, stummel=False, arme_an=bool(arme))


# Fahrzeuge mit einem Insassen im Skin: <grund>_skin_<id>[_<team>], wie
# <grund>_<team>_fahrer. Der Grund ist das Bild mit dem neutralen Fahrer.
_INSASSEN = ("buggy", "panzer_turm", "panzerwagen_ring",
             # Seit 0.34.109 auch die neuen Fahrzeuge (art_neue_fahrzeuge): das Krad
             # leer mit Fahrer und mit Beifahrer (beide im Skin des Fahrers), die
             # Kanone des Jagdpanzers samt Kommandant.
             "krad", "krad_beiwagen", "jagdpanzer_rohr", "tragschrauber", "flak_lafette")


def insassen_bildname(grund: str, skin: str, team_vorsatz: str = "") -> str:
    name = "%s_skin_%s" % (grund, skin)
    if team_vorsatz:
        name += "_" + team_vorsatz.rstrip("_")
    return name


def fahrer_aus_name(name: str):
    """<grund>_skin_<id>[_<team>] -> {"skin", "team"} (fuer art._insasse),
    sonst None."""
    for grund in _INSASSEN:
        anfang = grund + "_skin_"
        if name.startswith(anfang):
            teile = _skin_team(name[len(anfang):])
            if teile is None or teile[2]:
                return None
            return {"skin": teile[0], "team": teile[1]}
    return None


def _insassen_zeichner(grund: str):
    def z(name: str):
        fahrer = fahrer_aus_name(name)
        if fahrer is None:
            return None
        from . import art_fahrzeuge, art_neue_fahrzeuge
        if grund == "krad":
            return art_neue_fahrzeuge.krad_zeichnen(fahrer)
        if grund == "krad_beiwagen":
            return art_neue_fahrzeuge.krad_zeichnen(fahrer, fahrer)
        if grund == "jagdpanzer_rohr":
            return art_neue_fahrzeuge.jagdpanzer_aufbau(fahrer)
        if grund == "tragschrauber":
            return art_neue_fahrzeuge.tragschrauber_zeichnen(fahrer)
        if grund == "flak_lafette":
            return art_neue_fahrzeuge.flak_lafette(fahrer)
        if grund == "buggy":
            return art._buggy_zeichnen(fahrer)
        if grund == "panzer_turm":
            return art_fahrzeuge.panzer_turm(fahrer)
        return art_fahrzeuge.panzerwagen_ring(fahrer)
    return z


def _insassen_mass(grund: str):
    def m(name: str):
        return K.BILD_MASS[grund + "_fahrer"] if fahrer_aus_name(name) else None
    return m


for _grund in _INSASSEN:
    platzhalter_muster(_grund + "_skin_", _insassen_zeichner(_grund),
                       _insassen_mass(_grund))


# ──────────────────────────────── NPCs

def _npc_name(skin: str, band: str = "") -> str:
    return "npc_%s_%s" % (skin, band) if band else "npc_%s" % skin


def _npc_zeichner(skin: str, farbe=None):
    def z():
        d = K.FIGUREN[skin]
        if farbe is not None:
            d = dict(d, akzent=farbe)
        return figur(d)
    return z


for _skin in K.FIGUREN_GRUPPEN["NPC"]:
    platzhalter(_npc_name(_skin))(_npc_zeichner(_skin))
for _band, _farbe in K.STIRNBAND_FARBEN:
    platzhalter(_npc_name("ueberlebende", K.bild_kennung(_band)))(
        _npc_zeichner("ueberlebende", _farbe))


def npc_bildnamen() -> list:
    raus = [_npc_name(s) for s in K.FIGUREN_GRUPPEN["NPC"]]
    raus += [_npc_name("ueberlebende", K.bild_kennung(b))
             for b, _f in K.STIRNBAND_FARBEN]
    return raus


# ──────────────────────────────── Tiere, Pixel fuer Pixel

def _px(s, x, y, f) -> None:
    if 0 <= x < s.get_width() and 0 <= y < s.get_height():
        s.set_at((int(x), int(y)), f)


def schaf(wolle=(230, 224, 206), gesicht=(54, 48, 46), seed=1) -> pygame.Surface:
    """Von oben: ein wolliger Leib mit buckligem Rand, Licht von links oben,
    eingerollte Locken; vorn der schmale dunkle Kopf mit seitlich
    abstehenden Ohren, an den Seiten lugen die Hufe vor."""
    s = pygame.Surface(K.TIERE["schaf"]["mass"], pygame.SRCALPHA)
    cx, cy, rx, ry = 10.0, 9.5, 8.6, 6.6
    hell_w, schatten = _hell(wolle, 18), _misch(wolle, (90, 80, 66), 0.38)
    mittel = _misch(wolle, (90, 80, 66), 0.18)
    huf = (40, 34, 30)
    for x, y in ((4, 3), (4, 16), (14, 3), (14, 16)):        # Hufe zuerst
        _px(s, x, y, huf)
        _px(s, x + 1, y, huf)
    for y in range(20):
        for x in range(26):
            dx, dy = (x + .5 - cx) / rx, (y + .5 - cy) / ry
            w = math.atan2(dy, dx)
            if dx * dx + dy * dy <= 1 + 0.10 * math.sin(8 * w + 0.6):
                licht = -(dx * 0.6 + dy * 0.8)
                f = (hell_w if licht > 0.45 else wolle if licht > -0.15
                     else mittel if licht > -0.6 else schatten)
                _px(s, x, y, f)
    rnd = random.Random(seed)                                 # Locken
    for _ in range(11):
        x, y = rnd.randint(4, 15), rnd.randint(4, 15)
        if s.get_at((x, y)).a and s.get_at((x + 1, y)).a and s.get_at((x, y + 1)).a:
            _px(s, x, y, mittel)
            _px(s, x + 1, y, mittel)
            _px(s, x, y + 1, mittel)
    _px(s, 1, 9, wolle)                                        # Schwanzstummel
    _px(s, 1, 10, mittel)
    kopf_d = _misch(gesicht, (0, 0, 0), 0.25)
    for y in range(7, 13):
        for x in range(17, 24):
            dx, dy = (x + .5 - 19.8) / 3.4, (y + .5 - 10) / 2.6
            if dx * dx + dy * dy <= 1:
                _px(s, x, y, gesicht if dx < 0.3 else _hell(gesicht, 22))
    _px(s, 23, 9, _hell(gesicht, 40))                          # Maul
    _px(s, 23, 10, _hell(gesicht, 40))
    _px(s, 20, 8, (16, 14, 14))                                # Augen seitlich
    _px(s, 20, 11, (16, 14, 14))
    for y, dyo in ((6, -1), (13, 1)):                          # Ohren schraeg nach hinten
        _px(s, 18, y, kopf_d)
        _px(s, 17, y + dyo, kopf_d)
        _px(s, 19, y, (150, 108, 100))
    _px(s, 17, 9, wolle)                                       # Stirnwolle
    _px(s, 17, 10, wolle)
    _px(s, 18, 8, hell_w)
    return art._rand(s)


def ziege(fell=(150, 108, 70), fleck=(232, 222, 202), seed=2) -> pygame.Surface:
    """Schlanker als das Schaf, kurzes Fell mit dunklem Aalstrich und
    hellen Flecken; vorn ein langer Kopf mit zwei nach hinten geschwungenen
    Hoernern und Schlappohren. Nur die Hufe lugen unter dem Leib vor -
    seitlich abgespreizte Beine sahen aus wie eine Eidechse."""
    s = pygame.Surface(K.TIERE["ziege"]["mass"], pygame.SRCALPHA)
    cx, cy, rx, ry = 11.0, 9.0, 8.4, 4.4
    dunkel, hellf = _misch(fell, (30, 20, 12), 0.35), _hell(fell, 26)
    bein = _misch(fell, (30, 20, 12), 0.5)
    for x0 in (6, 15):
        for y0 in (4, 13):
            _px(s, x0, y0, bein)
            _px(s, x0 + 1, y0, (34, 26, 20))
    for y in range(18):
        for x in range(28):
            dx, dy = (x + .5 - cx) / rx, (y + .5 - cy) / ry
            breite = 1 + 0.12 * math.cos(dx * math.pi * 1.5) * -1
            if dx * dx + (dy / breite) ** 2 <= 1:
                licht = -(dx * 0.4 + dy * 0.9)
                _px(s, x, y, hellf if licht > 0.5 else fell if licht > -0.45 else dunkel)
    random.Random(seed)                # im Paket gezogen, aber nicht gebraucht
    for (fx, fy, fw, fh) in ((7, 6, 3, 2), (13, 10, 3, 2), (5, 10, 2, 1)):  # Flecken
        for x in range(fx, fx + fw):
            for y in range(fy, fy + fh):
                if s.get_at((x, y)).a:
                    _px(s, x, y, fleck)
    for x in range(4, 18):                                     # Aalstrich
        _px(s, x, 9, dunkel)
    _px(s, 2, 8, hellf)                                        # Schwanz hoch
    _px(s, 2, 9, fleck)
    _px(s, 1, 8, fleck)
    for x in range(18, 21):                                    # Hals
        for y in range(8, 11):
            _px(s, x, y, fell)
    for y in range(6, 13):                                     # Kopf
        for x in range(20, 27):
            dx, dy = (x + .5 - 22.8) / 3.6, (y + .5 - 9.5) / 2.3
            if dx * dx + dy * dy <= 1:
                _px(s, x, y, fell if dx < 0.35 else fleck)
    _px(s, 26, 9, (60, 44, 34))                                # Nase
    _px(s, 26, 10, (60, 44, 34))
    _px(s, 23, 8, (20, 16, 14))                                # Augen
    _px(s, 23, 11, (20, 16, 14))
    horn, horn_d = (206, 196, 168), (120, 110, 90)
    for y0, r in ((8, -1), (11, 1)):                           # Hoerner nach hinten
        _px(s, 21, y0, horn)
        _px(s, 20, y0 + r, horn)
        _px(s, 19, y0 + r, horn_d)
        _px(s, 18, y0 + 2 * r, horn_d)
    for y0, r in ((7, -1), (12, 1)):                           # Schlappohren
        _px(s, 22, y0 + r, dunkel)
        _px(s, 21, y0 + 2 * r, dunkel)
    return art._rand(s)


def huhn(gefieder=(176, 98, 46), fluegel=(130, 66, 30), schwanz=(40, 52, 40)) -> pygame.Surface:
    """Klein - kaum laenger, als eine Schulter breit ist. Tropfenform,
    aufgestellter dunkler Schwanz, Fluegel als Streifen an den Seiten,
    Kamm laengs ueber den Kopf, Schnabel."""
    s = pygame.Surface(K.TIERE["huhn"]["mass"], pygame.SRCALPHA)
    cx, cy = 6.0, 5.5
    for y in range(11):
        for x in range(14):
            dx, dy = (x + .5 - cx), (y + .5 - cy)
            breite = 3.4 if dx > 0 else 3.4 + dx * 0.45
            if -4.6 <= dx <= 4.0 and abs(dy) <= breite * math.sqrt(max(0.0, 1 - (dx / 4.6) ** 2)):
                licht = -(dx * 0.2 + dy * 0.6)
                _px(s, x, y, _hell(gefieder, 24) if licht > 1.2 else gefieder)
    for y in (3, 7):                                           # Fluegel
        for x in range(4, 8):
            _px(s, x, y, fluegel)
    for x, y in ((1, 4), (0, 5), (1, 6), (2, 5)):              # Schwanz
        _px(s, x, y, schwanz)
    _px(s, 1, 5, _hell(schwanz, 40))
    for y in range(4, 8):                                      # Kopf
        for x in range(9, 12):
            if (x + .5 - 10.3) ** 2 + (y + .5 - 5.5) ** 2 <= 2.6:
                _px(s, x, y, _hell(gefieder, 14))
    _px(s, 9, 5, (214, 44, 36))                                # Kamm
    _px(s, 10, 5, (214, 44, 36))
    _px(s, 12, 5, (240, 184, 52))                              # Schnabel
    _px(s, 13, 5, (240, 184, 52))
    _px(s, 11, 4, (16, 14, 12))                                # Augen
    _px(s, 11, 6, (16, 14, 12))
    return art._rand(s)


_TIER_ZEICHNER = {"schaf": schaf, "ziege": ziege, "huhn": huhn}


def tier_bildname(art_name: str, farbe: int = 0) -> str:
    """tier_<art> (die erste Farbe) oder tier_<art>_<farbe>."""
    if farbe <= 0:
        return "tier_%s" % art_name
    name = K.TIERE[art_name]["farben"][farbe][0]
    return "tier_%s_%s" % (art_name, K.bild_kennung(name))


def _tier_zeichner(art_name: str, werte: dict):
    def z():
        return _TIER_ZEICHNER[art_name](**werte)
    return z


for _art, _t in K.TIERE.items():
    for _i, (_fn, _werte) in enumerate(_t["farben"]):
        platzhalter(tier_bildname(_art, _i))(_tier_zeichner(_art, _werte))
