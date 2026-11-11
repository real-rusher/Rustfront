"""
DUSTFRONT - Das Raketengestell des Werfers und seine Raketen (seit 0.34.123)
===========================================================================

Komplett neu gebaut, als echtes 3D-Modell (drei_d.py), und aus Schrott wie
alles in RUSTFRONT: sechs alte Rohre verschiedener Herkunft (verzinkt,
rostig, olivgruen), nicht ganz gleich lang, mit zwei Bandeisen und einem
Winkeleisen-Rahmen zusammengeschweisst. Das Buendel liegt auf einer Achse
zwischen zwei Lagerboecken aus Blechresten, die auf einer alten Radfelge
stehen (dem Drehteller). Eine Spindel vorn hebt es an.

* **Drehen und Heben.** Das Bild wird fuer jede Richtung neu gerechnet
  (`gestell(gieren, erhebung, maske)`), nicht als flaches Bild gedreht: beim
  Schwenken sieht man je nach Richtung die Seite, die Oberseite oder die
  Muendungen der Rohre, das Licht wandert ueber die Flaechen. Je steiler die
  Rohre stehen, desto hoeher ragen die Muendungen im Bild, und die Spindel
  faehrt aus.
* **Raketen.** In jedem geladenen Rohr schaut vorn die rote Spitze heraus,
  hinten das Leitwerk aus Blech. Leere Rohre sind schwarze Loecher.
* **Im Flug** (`rakete(gieren, kippen)`) dasselbe Modell klein: Rumpf aus
  Rohr, rote Spitze, vier Blechflossen - es zeigt immer in Flugrichtung.

`muendung3d` und `hinten3d` sagen, wo ein Rohr vorn und hinten endet: von
dort startet die Rakete, dort tritt der Rueckstrahl aus.
"""

from __future__ import annotations

import math

import pygame

from . import drei_d as D

STUFEN = 8                          # Aufbau in so vielen Stufen (Fahrzeug.stufe)
GROESSE_BILD = 112                  # Bildgroesse des Gestells (Spielpixel)
ACHSE_Z = 8.0                       # so hoch liegt die Achse des Buendels ueber dem Drehteller

# Die sechs Rohre: (quer, hoch, hinten, vorn, Farbe). Unten drei, oben drei.
# Absichtlich ungleich: Schrott aus verschiedenen Quellen.
ROHRE = (
    (-5.2, -1.6, -15.0, 18.0, (150, 144, 128)),   # verzinkt, stumpf
    (0.0, -1.6, -14.0, 19.5, (156, 92, 52)),      # rostig
    (5.2, -1.6, -15.5, 18.5, (116, 124, 86)),      # olivgruen
    (-5.2, 3.0, -14.5, 19.0, (162, 100, 56)),
    (0.0, 3.0, -15.0, 18.0, (110, 118, 84)),
    (5.2, 3.0, -14.0, 19.5, (144, 138, 124)),
)
ROHR_R = 2.3
SPITZE = (168, 60, 38)
SPITZE_BAND = (204, 176, 86)
BLECH = (150, 146, 134)
DUNKEL = (22, 18, 15)
BAND = (70, 64, 56)
WINKEL = (126, 84, 54)
BOCK_L = (112, 74, 46)              # die Lagerboecke: einer rostig ...
BOCK_R = (98, 100, 74)              # ... einer aus olivem Blech
FELGE = (104, 98, 88)
NABE = (128, 122, 110)
RAKETE_RUMPF = (150, 146, 130)


def _punkt_im_buendel(p, gieren: float, erhebung: float) -> tuple:
    """Ein Punkt im Buendel (zur Achse) in Spielpixeln vom Drehteller."""
    x, y, z = p
    e = math.radians(erhebung)
    x, z = x * math.cos(e) - z * math.sin(e), x * math.sin(e) + z * math.cos(e)
    z += ACHSE_Z
    g = math.radians(gieren)
    return (x * math.cos(g) - y * math.sin(g), x * math.sin(g) + y * math.cos(g), z)


def muendung3d(index: int, gieren: float, erhebung: float) -> tuple:
    """Die Muendung von Rohr `index`: (x, y, hoch) vom Drehteller aus."""
    q, h, _x0, x1, _f = ROHRE[index]
    return _punkt_im_buendel((x1 + 1.0, q, h), gieren, erhebung)


def hinten3d(index: int, gieren: float, erhebung: float) -> tuple:
    """Das hintere offene Ende von Rohr `index` - dort tritt der Rueckstrahl aus."""
    q, h, x0, _x1, _f = ROHRE[index]
    return _punkt_im_buendel((x0 - 1.0, q, h), gieren, erhebung)


def _scheibe(x, y, z, r, normale_x, farbe, n=10) -> D.Flaeche:
    return D.Flaeche([(x, y + math.cos(2 * math.pi * i / n) * r, z + math.sin(2 * math.pi * i / n) * r)
                      for i in range(n)], (normale_x, 0, 0), farbe)


def _flossen(x0, x1, y, z, r, farbe) -> list:
    f = []
    for dy, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nrm = (0, 0, 1) if dy else (0, 1, 0)
        f += D.platte([(x1, y + dy * r * 0.7, z + dz * r * 0.7), (x0 + 0.6, y + dy * r * 0.7, z + dz * r * 0.7),
                       (x0, y + dy * (r + 1.6), z + dz * (r + 1.6)), (x1 - 0.8, y + dy * (r + 1.4), z + dz * (r + 1.4))],
                      nrm, farbe)
    return f


def _buendel(maske: int) -> list:
    """Das Rohrbuendel um seine Achse (0, 0, 0), Muendungen nach +x."""
    f = []
    # Winkeleisen-Rahmen links und rechts unter den Rohren (in Stuecken, damit
    # die Reihenfolge beim Malen stimmt - siehe drei_d.malen).
    for s in (-1, 1):
        for a in range(-13, 16, 5):
            f += D.quader(a, min(16.0, a + 5.0), min(s * 7.4, s * 8.4), max(s * 7.4, s * 8.4), -4.4, -0.6, WINKEL)
    for i, (q, h, x0, x1, farbe) in enumerate(ROHRE):
        a = x0
        while a < x1 - 0.01:
            e = min(x1, a + 4.5)
            f += D.stumpf(a, e, ROHR_R, ROHR_R, farbe, 10, kappe0=False, kappe1=False, y=q, z=h, glanz=True)
            a = e
        for x in (-8.0, 9.0):                         # Bandeisen um jedes Rohr
            f += D.stumpf(x - 0.7, x + 0.7, ROHR_R + 0.4, ROHR_R + 0.4, BAND, 10, kappe0=True, kappe1=True,
                          y=q, z=h)
        # Wulst an der Muendung, wie ein abgesaegtes Rohr mit Muffe.
        f += D.stumpf(x1 - 1.4, x1, ROHR_R + 0.35, ROHR_R + 0.35, tuple(int(c * 0.8) for c in farbe), 10,
                      kappe0=False, kappe1=True, y=q, z=h)
        if maske & (1 << i):
            f += D.stumpf(x1, x1 + 1.2, ROHR_R * 0.82, ROHR_R * 0.82, SPITZE_BAND, 8, kappe0=False, kappe1=False,
                          y=q, z=h)
            f += D.stumpf(x1 + 1.2, x1 + 4.6, ROHR_R * 0.82, 0.35, SPITZE, 8, kappe0=False, kappe1=False,
                          y=q, z=h, glanz=True)
            f += _flossen(x0 - 2.8, x0 + 0.2, q, h, 1.2, BLECH)
        else:
            f.append(_scheibe(x1 + 0.05, q, h, ROHR_R * 0.92, 1, DUNKEL))
        f.append(_scheibe(x0 - 0.05, q, h, ROHR_R * 0.92, -1, DUNKEL))
    # Ein Haltegriff aus Rundeisen hinten links, zum Nachrichten von Hand.
    f += D.stab((-12.0, -8.4, 1.0), (-16.0, -10.8, 1.6), 0.55, NABE)
    return f


def _sockel() -> list:
    """Drehteller (alte Felge) mit den zwei Lagerboecken und der Achse."""
    f = []
    felge = D.stumpf(0.0, 1.8, 11.0, 11.0, FELGE, 16, kappe0=False, kappe1=True)
    nabe = D.stumpf(1.8, 2.6, 4.6, 4.6, NABE, 12, kappe0=False, kappe1=True)
    f += D.bewegen(felge + nabe, kippen=-90.0)
    f += D.quader(-3.4, 3.4, 9.4, 11.4, 1.8, ACHSE_Z + 1.6, BOCK_L)
    f += D.quader(-3.0, 3.0, -11.4, -9.4, 1.8, ACHSE_Z + 1.4, BOCK_R)
    f += D.stab((0.0, -12.2, ACHSE_Z), (0.0, 12.2, ACHSE_Z), 1.1, NABE, 8)
    return f


def _spindel(erhebung: float) -> list:
    """Die Hubspindel vorn: vom Drehteller schraeg zum Buendel."""
    unten = (8.0, 0.0, 2.0)
    e = math.radians(erhebung)
    x, z = 9.0, -4.6
    oben = (x * math.cos(e) - z * math.sin(e), 0.0, x * math.sin(e) + z * math.cos(e) + ACHSE_Z)
    mitte = tuple(unten[k] + (oben[k] - unten[k]) * 0.45 for k in range(3))
    return D.stab(unten, mitte, 1.5, (70, 66, 58), 6) + D.stab(mitte, oben, 0.9, (176, 170, 156), 6, glanz=True)


_GESTELL: dict = {}


def gestell(gieren: float, erhebung: float, maske: int) -> tuple:
    """(Bild, Schatten) des Gestells. Gerundet auf 5 Grad (gieren) und 2 Grad
    (erhebung), jedes Bild wird einmal gerechnet und behalten."""
    g = int(round(gieren / 5.0)) * 5 % 360
    e = max(0, min(80, int(round(erhebung / 2.0)) * 2))
    m = int(maske) & 63
    s = _GESTELL.get((g, e, m))
    if s is not None:
        return s
    if len(_GESTELL) > 700:
        _GESTELL.clear()
    teile = _sockel() + _spindel(e) + D.bewegen(_buendel(m), kippen=-e, dz=ACHSE_Z)
    teile = D.bewegen(teile, gieren=g)
    bild = D.malen(teile, GROESSE_BILD)
    flach = D.malen(D.flach(teile, 0.42, 0.34), GROESSE_BILD, rand=False)
    schatten = pygame.mask.from_surface(flach, 30).to_surface(setcolor=(0, 0, 0, 86), unsetcolor=(0, 0, 0, 0))
    s = _GESTELL[(g, e, m)] = (bild, schatten)
    return s


def _rakete_netz() -> list:
    f = []
    f += D.stumpf(-5.0, 2.6, 1.5, 1.5, RAKETE_RUMPF, 8, kappe0=True, kappe1=False, glanz=True)
    f += D.stumpf(2.6, 3.6, 1.5, 1.5, SPITZE_BAND, 8, kappe0=False, kappe1=False)
    f += D.stumpf(3.6, 7.0, 1.5, 0.3, SPITZE, 8, kappe0=False, kappe1=False, glanz=True)
    f += _flossen(-6.2, -3.0, 0.0, 0.0, 1.0, BLECH)
    return f


_RAKETE: dict = {}


def rakete(gieren: float, kippen: float) -> pygame.Surface:
    """Eine Rakete im Flug, 28 x 28, Nase in Flugrichtung (`kippen` negativ:
    Nase nach oben). Gerundet auf 10 Grad."""
    g = int(round(gieren / 10.0)) * 10 % 360
    k = max(-90, min(90, int(round(kippen / 10.0)) * 10))
    s = _RAKETE.get((g, k))
    if s is None:
        s = _RAKETE[(g, k)] = D.malen(D.bewegen(_rakete_netz(), gieren=g, kippen=k), 28)
    return s


def rakete_heck(gieren: float, kippen: float) -> tuple:
    """Wo das Heck (die Flamme) liegt, relativ zur Mitte: (x, y - z) im Bild."""
    g, k = math.radians(gieren), math.radians(kippen)
    x, z = -6.4 * math.cos(k), 6.4 * math.sin(k)
    return (x * math.cos(g), x * math.sin(g) - z)
