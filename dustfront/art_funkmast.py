"""
DUSTFRONT - Der Mast des Funkwagens (seit 0.34.124)
===================================================

Neu gebaut, als 3D-Modell (drei_d.py), aus Schrott wie der Werfer: ein
Teleskopmast aus zwei Rohren, oben ein Peilkopf aus Rundeisen - ein Ausleger
mit fuenf Querstaeben (wie eine selbstgebaute Richtantenne) und ein Ring aus
einer alten Felge. Gezeichnet ueber dem Wagen (luft.py `_funkmasten_zeichnen`).

Der Aufbau ist eine Bewegung im Raum (`fortschritt` 0 bis 1):

1. Der Mast liegt auf dem Dach nach hinten und **richtet sich auf**, bis er
   senkrecht steht - im Bild waechst er dabei nach oben.
2. Das obere Rohr **faehrt aus**, der Mast wird gut doppelt so hoch.
3. Der Peilkopf **klappt auf** (die Querstaebe schwenken aus dem Ausleger).
4. Vier **Abspannseile** laufen vom Mast zu den Erdnaegeln am Boden.

Aufgebaut **dreht sich der Kopf** (`drehung`). Der Abbau ist dieselbe
Bewegung rueckwaerts.
"""

from __future__ import annotations

import math

import pygame

from . import drei_d as D

GROESSE_BILD = 176
MITTE = (0.0, -26.0)                 # Bildmitte (x, y - z): der Mast ragt nach oben
UNTEN_L = 17.0                       # unteres Rohr
OBEN_L = 21.0                        # oberes Rohr, ganz ausgefahren
NAEGEL = ((42.0, -42.0), (42.0, 42.0), (-45.0, -39.0), (-45.0, 39.0))

ROHR_U = (112, 116, 92)
ROHR_O = (156, 152, 138)
EISEN = (120, 84, 56)
RING = (92, 88, 80)
SEIL = (58, 54, 48)
NAGEL = (150, 146, 136)
LAMPE = (226, 70, 50)


def _glatt(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def stellung(fortschritt: float) -> tuple:
    """(aufrichten 0..90 Grad, ausfahren 0..1, aufklappen 0..1, Seile 0..1)."""
    p = max(0.0, min(1.0, fortschritt))
    return (90.0 * _glatt(p / 0.42), _glatt((p - 0.42) / 0.24), _glatt((p - 0.6) / 0.22),
            _glatt((p - 0.72) / 0.28))


def _kopf(aufklappen: float, drehung: float) -> list:
    """Der Peilkopf, um die Mastachse (+z) gedreht, Fuss bei z = 0."""
    f = []
    f += D.stab((0.0, 0.0, 0.0), (0.0, 0.0, 3.0), 1.1, ROHR_O, 6)
    lang = 9.0
    f += D.stab((-lang, 0.0, 3.0), (lang, 0.0, 3.0), 0.55, EISEN, 6)           # Ausleger
    for i, x in enumerate((-8.0, -4.0, 0.0, 4.0, 8.0)):                       # Querstaebe
        q = (6.4 - abs(x) * 0.35) * (0.15 + 0.85 * aufklappen)
        w = math.radians(90.0 * aufklappen)
        dy, dx = q * math.sin(w), q * math.cos(w) * 0.25
        f += D.stab((x - dx, -dy, 3.0), (x + dx, dy, 3.0), 0.42, EISEN, 5)
    # Der Ring aus einer Felge, hinten am Ausleger, steht senkrecht.
    if aufklappen > 0.05:
        r = 3.4 * aufklappen
        n = 10
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            f += D.stab((-lang - 0.5, math.cos(a0) * r, 3.0 + r + math.sin(a0) * r),
                        (-lang - 0.5, math.cos(a1) * r, 3.0 + r + math.sin(a1) * r), 0.5, RING, 4)
    f += D.quader(-0.7, 0.7, -0.7, 0.7, 3.4, 4.8, LAMPE)                     # Warnlampe
    return D.bewegen(f, gieren=drehung)


def _mast(aufrichten: float, ausfahren: float, aufklappen: float, drehung: float) -> tuple:
    """Mast samt Kopf am Fuss (0, 0, 0); und wo seine Spitze ist."""
    lang = UNTEN_L + OBEN_L * ausfahren
    f = []
    f += D.stab((0.0, 0.0, 0.0), (0.0, 0.0, UNTEN_L), 1.5, ROHR_U, 6)
    f += D.stab((0.0, 0.0, UNTEN_L - 2.0), (0.0, 0.0, max(UNTEN_L, lang)), 1.0, ROHR_O, 6, glanz=True)
    for z in (5.0, 11.0, UNTEN_L - 0.6):                                       # Schellen
        f += D.stab((0.0, 0.0, z - 0.5), (0.0, 0.0, z + 0.5), 1.8, (70, 66, 58), 6)
    f += D.bewegen(_kopf(aufklappen, drehung), dz=lang)
    k = aufrichten - 90.0
    f = D.bewegen(f, kippen=k)
    w = math.radians(k)
    spitze = (lang * math.sin(w), 0.0, lang * math.cos(w))
    return f, spitze


def _fuss() -> list:
    f = D.quader(-3.0, 3.0, -3.0, 3.0, 0.0, 1.6, (84, 82, 74))
    f += D.quader(-1.2, 1.2, -2.6, 2.6, 1.6, 3.6, (70, 66, 58))              # Gelenkbock
    return f


_BILDER: dict = {}
_SCHATTEN: dict = {}


def _schluessel(gieren: float, fortschritt: float, drehung: float) -> tuple:
    return (int(round(gieren / 5.0)) * 5 % 360, int(round(max(0.0, min(1.0, fortschritt)) * 24)),
            int(round(drehung / 15.0)) * 15 % 360)


def _seile(g: int, p: int, d: int) -> list:
    """Die Abspannseile, schon gegiert: [(oben, ende), ...] in Spielpixeln
    vom Mastfuss."""
    aufrichten, ausfahren, aufklappen, seile = stellung(p / 24.0)
    if seile <= 0.0:
        return []
    _f, spitze = _mast(aufrichten, ausfahren, 0.0, 0.0)
    oben = tuple(c * 0.82 for c in spitze)
    w = math.radians(g)
    cw, sw = math.cos(w), math.sin(w)

    def gier(q):
        return (q[0] * cw - q[1] * sw, q[0] * sw + q[1] * cw, q[2])
    raus = []
    for nx, ny in NAEGEL:
        ende = (oben[0] + (nx - oben[0]) * seile, oben[1] + (ny - oben[1]) * seile,
                oben[2] + (0.0 - oben[2]) * seile)
        raus.append((gier(oben), gier(ende)))
    return raus


def _teile(g: int, p: int, d: int, seile_als_stab: bool = False) -> list:
    aufrichten, ausfahren, aufklappen, seile = stellung(p / 24.0)
    teile, spitze = _mast(aufrichten, ausfahren, aufklappen, d)
    teile += _fuss()
    if seile >= 0.98:
        for nx, ny in NAEGEL:
            teile += D.quader(nx - 1.0, nx + 1.0, ny - 1.0, ny + 1.0, 0.0, 1.4, NAGEL)
    teile = D.bewegen(teile, gieren=g)
    if seile_als_stab:
        for a, b in _seile(g, p, d):
            teile += D.stab(a, b, 0.3, SEIL, 4)
    return teile


def _ins_bild(q) -> tuple:
    halb = GROESSE_BILD / 2.0
    return (q[0] - MITTE[0] + halb, q[1] - q[2] - MITTE[1] + halb)


def funkmast(gieren: float, fortschritt: float, drehung: float = 0.0) -> pygame.Surface:
    """Der Mast im Bild, gerundet auf 5 Grad (gieren), 1/24 (fortschritt) und
    15 Grad (drehung). Bildmitte ist der Mastfuss, verschoben um MITTE."""
    k = _schluessel(gieren, fortschritt, drehung)
    s = _BILDER.get(k)
    if s is not None:
        return s
    if len(_BILDER) > 600:
        _BILDER.clear()
    mast = D.malen(_teile(*k), GROESSE_BILD, mitte=MITTE)
    # Die Seile nicht als 3D-Koerper: so duenn greift der dunkle Rand von
    # drei_d.malen nur bei manchen Lagen, und dann waren die vorderen Seile
    # dick und schwarz, die hinteren kaum zu sehen. Als glatte Linie sind
    # alle gleich - die hinteren unter dem Mast, die vorderen darueber.
    s = pygame.Surface(mast.get_size(), pygame.SRCALPHA)
    seile = _seile(*k)
    hinten = [z for z in seile if z[1][1] < 0.0]
    vorn = [z for z in seile if z[1][1] >= 0.0]
    for a, b in hinten:
        pygame.draw.aaline(s, SEIL, _ins_bild(a), _ins_bild(b))
    s.blit(mast, (0, 0))
    for a, b in vorn:
        pygame.draw.aaline(s, SEIL, _ins_bild(a), _ins_bild(b))
    _BILDER[k] = s
    return s


def schatten(gieren: float, fortschritt: float, drehung: float = 0.0) -> pygame.Surface:
    """Der Schatten des Mastes auf dem Boden, wie beim Werfer-Gestell schraeg
    nach rechts unten; dieselbe Bildmitte wie `funkmast`. Der Kopf dreht sich
    im Schatten mit, darum dieselben Stufen."""
    k = _schluessel(gieren, fortschritt, drehung)
    s = _SCHATTEN.get(k)
    if s is not None:
        return s
    if len(_SCHATTEN) > 600:
        _SCHATTEN.clear()
    flach = D.malen(D.flach(_teile(*k, seile_als_stab=True), 0.42, 0.34), GROESSE_BILD, mitte=MITTE, rand=False)
    s = _SCHATTEN[k] = pygame.mask.from_surface(flach, 30).to_surface(
        setcolor=(0, 0, 0, 70), unsetcolor=(0, 0, 0, 0))
    return s
