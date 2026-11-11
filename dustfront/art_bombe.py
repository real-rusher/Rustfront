"""
DUSTFRONT - Die Bomben des Tragschraubers (seit 0.34.123)
=========================================================

Neu gebaut (gewuenscht: "das mit den Bomben komplett neu machen und
designen"). Die Bomben sind ein echtes 3D-Modell (drei_d.py): Rumpf, Nase,
gelbes Band, Heck mit vier Leitflaechen, oben ein Traeger.

* **Am Tragschrauber** haengen sie fest im Bild: `tsb<N>_<Bildname>` ist das
  Bild des Tragschraubers mit N Bomben an den Traegern links und rechts
  unter dem Rahmen - ein einziges Bild, das sich mit ihm dreht und hebt. Sie
  koennen nicht neben ihm schweben oder verrutschen. Der Schatten
  (`tss<N>`) ist der Umriss genau dieses Bildes.
* **Im Fall** wird die Bombe aus dem Modell gemalt, in der Richtung, in der
  der Tragschrauber flog, und kippt dabei mit der Nase nach unten
  (`bombe_fallend`).
"""

from __future__ import annotations

import pygame

from . import core
from . import drei_d as D
from .core import platzhalter_muster

RUMPF = (96, 104, 70)
NASE = (58, 54, 48)
BAND = (214, 182, 76)
LEIT = (74, 80, 56)
TRAEGER = (62, 60, 56)

# Wo die Bomben am Tragschrauber haengen (Spielpixel, +x vorn, +y rechts), die
# erste rechts: sie faellt zuerst.
PLAETZE = ((4.0, 12.0), (4.0, -12.0))


def bombe_netz(traeger: int = 0) -> list:
    """Die Bombe, Nase nach +x, 13 Pixel lang. `traeger`: +1 Traeger nach
    links (die rechte Bombe haengt rechts am Rahmen), -1 nach rechts, 0 ohne."""
    f = []
    f += D.stumpf(-4.0, 3.6, 2.1, 2.1, RUMPF, 12, kappe0=False, kappe1=False, glanz=True)
    f += D.stumpf(0.6, 1.6, 2.2, 2.2, BAND, 12, kappe0=False, kappe1=False)
    f += D.stumpf(3.6, 6.4, 2.1, 0.5, NASE, 12, kappe0=False, kappe1=True)
    f += D.stumpf(-6.6, -4.0, 1.0, 2.1, RUMPF, 12, kappe0=True, kappe1=False)
    for y, z in ((3.4, 0.0), (-3.4, 0.0), (0.0, 3.4), (0.0, -3.4)):
        ny, nz = (0.0, 1.0) if y == 0.0 else (1.0, 0.0)
        f += D.platte([(-7.2, 0, 0), (-4.4, 0, 0), (-5.0, y * 0.8, z * 0.8), (-7.4, y, z)], (0, nz, ny), LEIT)
    if traeger:
        s = -traeger
        f += D.quader(-2.0, 2.4, min(0, s * 5.0), max(0, s * 5.0), 1.6, 2.6, TRAEGER)
    return f


_FALL: dict = {}


def bombe_fallend(gieren: float, kippen: float, rollen: float = 0.0) -> pygame.Surface:
    """Die fallende Bombe, 40 x 40, gerundet auf 10 Grad (gieren), 8 Grad
    (kippen) und 30 Grad (rollen)."""
    g = int(round(gieren / 10.0)) * 10 % 360
    k = max(0, min(88, int(round(kippen / 8.0)) * 8))
    r = int(round(rollen / 30.0)) * 30 % 360
    s = _FALL.get((g, k, r))
    if s is None:
        s = D.malen(D.bewegen(bombe_netz(), gieren=g, kippen=k, rollen=r), 40)
        _FALL[(g, k, r)] = s
    return s


def _basis(name: str):
    """Ein Bild aus den Zeichnern des Spiels (ohne Datei), fuer die Bilder mit Bomben."""
    z = core._PLATZHALTER.get(name)
    if z is not None:
        return z()
    for anfang, muster in core._MUSTER:
        if anfang in ("tsb", "tss"):
            continue
        if name.startswith(anfang):
            s = muster(name)
            if s is not None:
                return s
    return None


def _mit_bomben(basis: pygame.Surface, anzahl: int) -> pygame.Surface:
    s = pygame.Surface(basis.get_size(), pygame.SRCALPHA)
    m = (basis.get_width() / 2.0, basis.get_height() / 2.0)
    for i in range(max(0, min(2, anzahl))):
        x, y = PLAETZE[i]
        b = D.malen(bombe_netz(1 if y > 0 else -1), 40)
        s.blit(b, b.get_rect(center=(int(round(m[0] + x)), int(round(m[1] + y)))))
    s.blit(basis, (0, 0))         # der Rahmen liegt ueber den Traegern
    return s


def _tsb(name: str):
    """`tsb<N>_<Bildname>`: der Tragschrauber mit N Bomben."""
    try:
        kopf, basisname = name.split("_", 1)
        anzahl = int(kopf[3:])
    except (ValueError, IndexError):
        return None
    basis = _basis(basisname)
    return None if basis is None else _mit_bomben(basis, anzahl)


def _tss(name: str):
    """`tss<N>`: der Schatten des leeren Tragschraubers mit N Bomben."""
    try:
        anzahl = int(name[3:])
    except ValueError:
        return None
    basis = _basis("tragschrauber")
    if basis is None:
        return None
    bild = _mit_bomben(basis, anzahl)
    return pygame.mask.from_surface(bild, 40).to_surface(setcolor=(0, 0, 0, 112), unsetcolor=(0, 0, 0, 0))


platzhalter_muster("tsb", _tsb, lambda name: (160, 160) if name.startswith("tsb") else None)
platzhalter_muster("tss", _tss, lambda name: (160, 160) if name[3:].isdigit() else None)
