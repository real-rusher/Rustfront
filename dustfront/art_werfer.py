"""
DUSTFRONT - Das Raketengestell des Werfers und seine Truemmer (seit 0.34.120)
=============================================================================

Das Gestell ist ein eigenes Bild, das ueber dem Wagen liegt und sich zum
Ziel dreht (luft.py `_werfer_gestelle_zeichnen`). Es steht auf dem Drehkranz,
zwei Reihen zu drei Rohren, und sieht nach 3D aus:

* **Hub.** Je hoeher es steht (Stufe 0 bis 8), desto kuerzer erscheinen die
  Rohre (von oben gesehen) und desto groesser ihre Muendungen und desto
  heller ihre Vorderseite - sie kommen dem Betrachter entgegen. Zwei
  Zylinder an der Wiege strecken sich. Das ganze Bild wird beim Zeichnen
  zusaetzlich nach oben gehoben, mit eigenem Schatten am Wagen.
* **Beladung.** Die Maske (6 Bits) sagt, welches Rohr eine Rakete traegt:
  rote Spitze in der Muendung - sonst ein dunkles, leeres Rohr.

Gezeichnet wird es nach +x, wie alle Bilder; das Spiel dreht es. Bilder
heissen `werfer_rohre_<Stufe>_<Maske>` und entstehen beim ersten Gebrauch
(`platzhalter_muster`).

Dazu `werfer_teil_0..5`: Truemmerteile, die nach der Explosion am Boden
bleiben (Rohrstueck, Rad, Blech, Rakete, Tuer, Zahnrad).
"""

from __future__ import annotations

import math
import random

import pygame

from . import config as K
from .art_fahrzeuge import GROESSE, _Blatt
from .art_neue_fahrzeuge import HK_DK, HK_HELL, HK_LACK, HK_SCHATTEN
from .core import platzhalter, platzhalter_muster

G = GROESSE
STUFEN = 8                          # Hub in so vielen Stufen
ROHR_X0 = -9.0                      # Rohre beginnen hier (Entwurfspixel vom Drehkranz)
ROHR_L = 30.0                       # ... und sind so lang (ausgefahren: Stufe 0)


def rohr_lage(index: int) -> tuple:
    """Seite (-1 links, 0 Mitte, 1 rechts) und Reihe (0 unten, 1 oben) eines Rohrs."""
    return (index % 3) - 1, index // 3


def muendung_versatz(index: int, stufe: int = 0) -> tuple:
    """Wo die Muendung von Rohr `index` liegt: (vor, quer) in Spielpixeln vom
    Drehkranz aus, nach +x gerichtet (das Spiel dreht es mit dem Gestell)."""
    spalte, _reihe = rohr_lage(index)
    laenge = ROHR_L * math.cos(math.radians(50.0 * stufe / STUFEN)) + 2.0
    return ((ROHR_X0 + laenge) * G, spalte * 5.3 * G)


def hinten_versatz(index: int) -> tuple:
    """Das offene Ende des Rohrs - dort tritt der Rueckstrahl aus."""
    spalte, _reihe = rohr_lage(index)
    return (ROHR_X0 * G, spalte * 5.3 * G)


def _rohr(b, index: int, e: float, geladen: bool) -> None:
    spalte, reihe = rohr_lage(index)
    laenge = ROHR_L * math.cos(math.radians(50.0 * e)) + 2.0
    x0, x1 = ROHR_X0, ROHR_X0 + laenge
    y = spalte * 5.3 - (2.6 + 2.8 * e if reihe else 0.0)
    r_hinten = 2.1
    r_vorn = 2.1 * (1.0 + 0.55 * e)                  # naeher am Betrachter: groesser
    kopf = [(x0, y - r_hinten), (x1, y - r_vorn), (x1, y + r_vorn), (x0, y + r_hinten)]
    if reihe:                                         # Schlagschatten auf die untere Reihe
        b.poly((20, 18, 16), [(x, py + 2.4 + 1.2 * e) for x, py in kopf])
    b.poly((24, 22, 20), kopf)
    # Wie ein Zylinder beleuchtet: Licht von oben links, also oben ein heller
    # Streifen, unten ein dunkler - Streifen entlang des Rohrs, vorn breiter.
    steigerung = 0.92 + 0.3 * e
    for f0, f1, helligkeit in ((-0.86, -0.55, 0.78), (-0.55, -0.22, 1.12), (-0.22, 0.05, 1.32),
                                (0.05, 0.42, 1.0), (0.42, 0.7, 0.78), (0.7, 0.86, 0.56)):
        farbe = tuple(min(255, int(c * helligkeit * steigerung)) for c in HK_LACK)
        b.poly(farbe, [(x0 + 0.5, y + r_hinten * f0), (x1 - 0.2, y + r_vorn * f0),
                       (x1 - 0.2, y + r_vorn * f1), (x0 + 0.5, y + r_hinten * f1)])
    b.linie((236, 232, 214), (x0 + 1.4, y - r_hinten * 0.38), (x1 - 1.2, y - r_vorn * 0.38), 0.35)
    for t in (0.28, 0.66):                            # Spannringe
        px = x0 + (x1 - x0) * t
        r = r_hinten + (r_vorn - r_hinten) * t
        b.rect((40, 36, 32), px, y - r, 1.1, 2 * r, 0.2)
    b.kreis((20, 18, 16), (x0 + 0.3, y), r_hinten * 0.82)         # offenes Ende hinten
    b.kreis((70, 66, 60), (x0 + 0.1, y), r_hinten * 0.4)
    b.kreis((30, 28, 24), (x1, y), r_vorn * 1.02)                  # Muendungsrand
    b.kreis((14, 12, 10), (x1 + 0.1, y), r_vorn * 0.78)
    if geladen:
        b.kreis((176, 66, 44), (x1 + 0.7 + 0.4 * e, y), r_vorn * 0.66)
        b.kreis((226, 120, 92), (x1 + 0.3 + 0.4 * e, y - r_vorn * 0.26), r_vorn * 0.24)
        b.linie((236, 224, 196), (x1 - 0.4, y - r_vorn * 0.7), (x1 - 0.4, y + r_vorn * 0.7), 0.3)


def werfer_gestell3d(stufe: int = 0, maske: int = 63) -> pygame.Surface:
    """Das Gestell auf dem Drehkranz: Platte, Wiege, Hubzylinder, sechs Rohre."""
    e = max(0.0, min(1.0, stufe / float(STUFEN)))
    b = _Blatt(128, G * 1.1)
    b.rect((28, 26, 24), -11.5, -10.6, 18, 21.2, 1.2)             # Wiege auf dem Drehkranz
    b.rect((96, 92, 84), -11.0, -10.1, 17, 20.2, 1.0)
    b.rect((58, 56, 50), -10.2, -9.2, 15.4, 18.4, 0.8)
    for sy in (-1, 1):                                            # Hubzylinder
        ausgefahren = 2.0 + 7.0 * e
        b.rohr((-9.5, sy * 9.2), (-9.5 + ausgefahren, sy * 9.2), 1.7, (170, 166, 156), (40, 38, 34))
        b.rohr((-9.5, sy * 9.2), (-9.5 + 2.0 + 3.0 * e, sy * 9.2), 2.3, (84, 80, 72), (30, 28, 24))
        b.kreis((30, 28, 26), (-9.5, sy * 9.2), 1.3)
    for i in (0, 1, 2):                                           # untere Reihe, dann die obere
        _rohr(b, i, e, bool(maske & (1 << i)))
    for i in (3, 4, 5):
        _rohr(b, i, e, bool(maske & (1 << i)))
    b.rect((30, 28, 26), ROHR_X0 - 3.0, -9.4, 2.4, 18.8, 0.5)     # Abgasblech hinten
    b.rect((74, 70, 62), ROHR_X0 - 2.7, -9.0, 1.7, 18.0, 0.4)
    for sy in (-1, 1):
        b.kreis((200, 170, 70), (ROHR_X0 - 1.8, sy * 7.8), 0.7)   # Warnmarken
    return b.fertig()


def _gestell_zeichner(name: str):
    """`werfer_rohre_<Stufe>_<Maske>` -> Bild; sonst None."""
    teile = name[len("werfer_rohre_"):].split("_")
    try:
        stufe, maske = int(teile[0]), int(teile[1])
    except (ValueError, IndexError):
        return None
    if not (0 <= stufe <= STUFEN and 0 <= maske <= 63):
        return None
    return werfer_gestell3d(stufe, maske)


platzhalter_muster("werfer_rohre_", _gestell_zeichner,
                   lambda name: (128, 128) if _gestell_zeichner_ok(name) else None)


def _gestell_zeichner_ok(name: str) -> bool:
    teile = name[len("werfer_rohre_"):].split("_")
    try:
        return 0 <= int(teile[0]) <= STUFEN and 0 <= int(teile[1]) <= 63
    except (ValueError, IndexError):
        return False


# ──────────────────────────────── Truemmerteile

def _angekohlt(s: pygame.Surface, seed: int) -> pygame.Surface:
    s = s.copy()
    s.fill((92, 82, 76, 255), special_flags=pygame.BLEND_RGBA_MULT)
    rnd = random.Random(seed)
    n = s.get_width()
    for _ in range(14):
        x, y = rnd.randrange(2, n - 2), rnd.randrange(2, n - 2)
        if s.get_at((x, y))[3] > 40:
            pygame.draw.circle(s, (24, 20, 18, 255), (x, y), rnd.randint(1, 2))
    return s


def _teil(index: int) -> pygame.Surface:
    b = _Blatt(32, G)
    if index == 0:                                    # ein Stueck Rohr
        b.rect((24, 22, 20), -7, -2.4, 14, 4.8, 1.2)
        b.rect(HK_LACK, -6.5, -1.9, 13, 3.8, 1.0)
        b.kreis((14, 12, 10), (6.4, 0), 1.7)
        b.rect((40, 36, 32), -2, -2.4, 1.1, 4.8, 0.2)
    elif index == 1:                                  # ein Rad
        b.kreis((22, 19, 17), (0, 0), 6.4)
        b.kreis((46, 41, 37), (0, 0), 5.0)
        b.kreis((96, 92, 86), (0, 0), 2.2)
    elif index == 2:                                  # Blech mit Nieten
        b.poly((30, 28, 24), [(-6, -4), (5, -5.4), (6.6, 3), (-2, 5.6), (-6.4, 2)])
        b.poly(HK_LACK, [(-5, -3), (4.2, -4.2), (5.6, 2.4), (-1.8, 4.6), (-5.4, 1.6)])
        for p in ((-3, -1.6), (2.4, -2.6), (3.4, 1.6), (-1.6, 2.4)):
            b.kreis((44, 42, 38), p, 0.5)
    elif index == 3:                                  # eine Rakete, verbogen
        b.rect((30, 28, 24), -7, -1.6, 12, 3.2, 1.0)
        b.rect((120, 114, 98), -6.6, -1.2, 10.8, 2.4, 0.8)
        b.kreis((176, 66, 44), (5.4, 0), 1.5)
        b.rect((30, 28, 24), -8, -2.6, 1.6, 5.2, 0.3)
    elif index == 4:                                  # eine Tuer
        b.rect((30, 28, 24), -5.5, -6.5, 11, 13, 1.0)
        b.rect(HK_LACK, -5, -6, 10, 12, 0.8)
        b.rect((24, 30, 36), -3.4, -4.4, 6.8, 3.4, 0.4)
    else:                                             # ein Zahnrad vom Drehkranz
        b.kreis((30, 28, 26), (0, 0), 6.0)
        b.kreis((96, 92, 84), (0, 0), 5.0)
        b.kreis((58, 56, 50), (0, 0), 3.4)
        for i in range(10):
            a = i * math.pi / 5
            b.kreis((30, 28, 26), (math.cos(a) * 5.8, math.sin(a) * 5.8), 0.9)
    return _angekohlt(b.fertig(), 8800 + index)


def _teil_stufe(i: int):
    def z():
        return _teil(i)
    return z


for _i in range(6):
    platzhalter("werfer_teil_%d" % _i)(_teil_stufe(_i))
