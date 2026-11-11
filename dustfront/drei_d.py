"""
DUSTFRONT - Ein kleiner 3D-Zeichner fuer Pixelbilder (seit 0.34.123)
====================================================================

Fuer alles, was sich im Raum drehen und kippen soll und dabei nach echtem
3D aussehen muss: die Bomben des Tragschraubers (sie kippen im Fall mit der
Nase nach unten) und der Mast des Funkwagens. Das Raketengestell des Werfers
und seine Raketen waren bis 0.34.125 auch von hier; seit 0.34.126 sind sie
klassisch gemalt (art_werfer.py) - "zu krass", der Stil zu anders.

**Wie es zeichnet.** Koerper bestehen aus ebenen Flaechen (Zylinder,
Kegelstuempfe, Platten, Quader), jede mit Normale und Grundfarbe. Gedreht
wird um die eigene Achse (Rollen), dann gekippt (Nase nach unten), dann
gegiert (die Richtung am Boden). Die Projektion ist die des Spiels: was hoch
ist, steht im Bild um seine Hoehe weiter oben (Bild-y = y - z) - genau wie
der Tragschrauber und jeder Abwurf. Der Betrachter schaut also von Sueden
schraeg herunter; was naeher an ihm ist (groesseres y + z), wird zuletzt
gemalt, Rueckseiten fallen weg. Das Licht kommt von oben links (wie bei
allen Sprites), die Helligkeit wird in Stufen gerundet - so entstehen die
harten Tonstufen der Pixelbilder statt eines weichen Verlaufs. Gemalt wird
vierfach gross, weich verkleinert und mit dem dunklen Rand des Spiels
versehen (art._rand).
"""

from __future__ import annotations

import math

import pygame

_LICHT = (-0.46, -0.52, 0.72)
_L = math.sqrt(sum(c * c for c in _LICHT))
LICHT = tuple(c / _L for c in _LICHT)
BLICK = (0.0, 0.7071, 0.7071)       # vom Koerper zum Betrachter
STUFEN = (0.42, 0.58, 0.74, 0.9, 1.06, 1.2)
GROSS = 4                            # so viel groesser wird gemalt


class Flaeche:
    __slots__ = ("punkte", "normale", "farbe", "beidseitig", "glanz", "ton")

    def __init__(self, punkte, normale, farbe, beidseitig=False, glanz=False, ton=None) -> None:
        self.punkte = [tuple(p) for p in punkte]
        self.normale = tuple(normale)
        self.farbe = tuple(farbe)
        self.beidseitig = beidseitig
        self.glanz = glanz
        # Fester Farbton (seit 0.34.126): gesetzt, malt `malen` ihn so, statt
        # ihn aus dem Licht zu rechnen - fuer Teile, die beim Bewegen nicht die
        # Farbe wechseln sollen (der Funkmast beim Aufrichten).
        self.ton = ton


# ---- Koerper (lokal: +x ist vorn, +y rechts, +z oben) -------------------

def stumpf(x0, x1, r0, r1, farbe, n=12, kappe0=True, kappe1=True, y=0.0, z=0.0, glanz=False) -> list:
    """Ein Kegelstumpf entlang x: Radius r0 bei x0, r1 bei x1 (gleich: Zylinder)."""
    raus = []
    neigung = (r0 - r1) / max(1e-6, (x1 - x0))
    for i in range(n):
        a0 = 2 * math.pi * i / n
        a1 = 2 * math.pi * (i + 1) / n
        am = (a0 + a1) / 2
        p = [(x0, y + math.cos(a0) * r0, z + math.sin(a0) * r0),
             (x1, y + math.cos(a0) * r1, z + math.sin(a0) * r1),
             (x1, y + math.cos(a1) * r1, z + math.sin(a1) * r1),
             (x0, y + math.cos(a1) * r0, z + math.sin(a1) * r0)]
        nx = neigung
        ny, nz = math.cos(am), math.sin(am)
        lang = math.sqrt(nx * nx + ny * ny + nz * nz)
        raus.append(Flaeche(p, (nx / lang, ny / lang, nz / lang), farbe, glanz=glanz))
    if kappe0 and r0 > 0.01:
        raus.append(Flaeche([(x0, y + math.cos(2 * math.pi * i / n) * r0, z + math.sin(2 * math.pi * i / n) * r0)
                             for i in range(n)], (-1, 0, 0), farbe))
    if kappe1 and r1 > 0.01:
        raus.append(Flaeche([(x1, y + math.cos(2 * math.pi * i / n) * r1, z + math.sin(2 * math.pi * i / n) * r1)
                             for i in range(n)], (1, 0, 0), farbe))
    return raus


def platte(punkte, normale, farbe) -> list:
    return [Flaeche(punkte, normale, farbe, beidseitig=True)]


def quader(x0, x1, y0, y1, z0, z1, farbe) -> list:
    return [
        Flaeche([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1), farbe),
        Flaeche([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], (0, 0, -1), farbe),
        Flaeche([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], (0, 1, 0), farbe),
        Flaeche([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0), farbe),
        Flaeche([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], (1, 0, 0), farbe),
        Flaeche([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], (-1, 0, 0), farbe),
    ]


# ---- Bewegen --------------------------------------------------------------

def _drehe(p, cr, sr, cp, sp, cy, sy):
    x, y, z = p
    # rollen um x
    y, z = y * cr - z * sr, y * sr + z * cr
    # kippen um y (positiv: Nase nach unten)
    x, z = x * cp + z * sp, -x * sp + z * cp
    # gieren um z (wie Vector2.rotate: im Bild im Uhrzeigersinn)
    x, y = x * cy - y * sy, x * sy + y * cy
    return x, y, z


def bewegen(flaechen, gieren=0.0, kippen=0.0, rollen=0.0, dx=0.0, dy=0.0, dz=0.0) -> list:
    cr, sr = math.cos(math.radians(rollen)), math.sin(math.radians(rollen))
    cp, sp = math.cos(math.radians(kippen)), math.sin(math.radians(kippen))
    cy, sy = math.cos(math.radians(gieren)), math.sin(math.radians(gieren))
    raus = []
    for f in flaechen:
        pts = []
        for p in f.punkte:
            x, y, z = _drehe(p, cr, sr, cp, sp, cy, sy)
            pts.append((x + dx, y + dy, z + dz))
        raus.append(Flaeche(pts, _drehe(f.normale, cr, sr, cp, sp, cy, sy), f.farbe, f.beidseitig, f.glanz, f.ton))
    return raus


def skalieren(flaechen, f: float) -> list:
    return [Flaeche([(p[0] * f, p[1] * f, p[2] * f) for p in x.punkte], x.normale, x.farbe,
                    x.beidseitig, x.glanz, x.ton) for x in flaechen]


# ---- Malen ----------------------------------------------------------------

def ton_fest(flaechen, gieren=0.0, mischen=None, anteil=0.0) -> list:
    """Jeder Flaeche ihren Farbton geben, wie er jetzt (um `gieren` gedreht)
    im Licht steht - danach bleibt er beim Kippen gleich. `mischen`: eine
    Farbe, in die der Ton zu `anteil` (0 bis 1) uebergeht."""
    cy, sy = math.cos(math.radians(gieren)), math.sin(math.radians(gieren))
    raus = []
    for f in flaechen:
        n = _drehe(f.normale, 1.0, 0.0, 1.0, 0.0, cy, sy)
        if sum(a * b for a, b in zip(n, BLICK)) <= 0.0 and f.beidseitig:
            n = (-n[0], -n[1], -n[2])
        t = _ton(f.farbe, n, f.glanz)
        if mischen is not None and anteil > 0.0:
            t = tuple(int(a + (b - a) * anteil) for a, b in zip(t, mischen))
        raus.append(Flaeche(f.punkte, f.normale, f.farbe, f.beidseitig, f.glanz, t))
    return raus


def _ton(farbe, normale, glanz=False):
    nl = sum(a * b for a, b in zip(normale, LICHT))
    h = 0.34 + 0.72 * max(0.0, nl)
    stufe = min(STUFEN, key=lambda s: abs(s - h))
    if glanz and nl > 0.86:
        stufe = 1.42
    return tuple(max(0, min(255, int(c * stufe))) for c in farbe)


def malen(flaechen, groesse: int, mitte=(0.0, 0.0), rand: bool = True) -> pygame.Surface:
    """Die Flaechen in ein Bild `groesse` x `groesse` (Spielpixel), der Punkt
    `mitte` (x, y - z in Spielpixeln) liegt in der Bildmitte."""
    n = groesse * GROSS
    s = pygame.Surface((n, n), pygame.SRCALPHA)
    halb = groesse / 2.0
    sichtbar = []
    for f in flaechen:
        nrm = f.normale
        sicht = sum(a * b for a, b in zip(nrm, BLICK))
        if sicht <= 0.0:
            if not f.beidseitig:
                continue
            nrm = (-nrm[0], -nrm[1], -nrm[2])
        tiefe = sum(p[1] + p[2] for p in f.punkte) / len(f.punkte)
        sichtbar.append((tiefe, f, nrm))
    sichtbar.sort(key=lambda t: t[0])
    for _tiefe, f, nrm in sichtbar:
        pts = [((p[0] - mitte[0] + halb) * GROSS, (p[1] - p[2] - mitte[1] + halb) * GROSS) for p in f.punkte]
        if len(pts) >= 3:
            pygame.draw.polygon(s, f.ton if f.ton is not None else _ton(f.farbe, nrm, f.glanz), pts)
    klein = pygame.transform.smoothscale(s, (groesse, groesse))
    if not rand:
        return klein
    from . import art
    return art._rand(klein)


def stab(a, b, r, farbe, n=6, glanz=False) -> list:
    """Ein Rohr (Prisma mit `n` Seiten) von Punkt `a` nach Punkt `b`, ohne
    Deckel - fuer Streben, Hubspindeln und Gestaenge."""
    ax = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    lang = math.sqrt(sum(c * c for c in ax)) or 1e-6
    ax = tuple(c / lang for c in ax)
    hilf = (0.0, 0.0, 1.0) if abs(ax[2]) < 0.9 else (0.0, 1.0, 0.0)
    u = (ax[1] * hilf[2] - ax[2] * hilf[1], ax[2] * hilf[0] - ax[0] * hilf[2], ax[0] * hilf[1] - ax[1] * hilf[0])
    lu = math.sqrt(sum(c * c for c in u))
    u = tuple(c / lu for c in u)
    v = (ax[1] * u[2] - ax[2] * u[1], ax[2] * u[0] - ax[0] * u[2], ax[0] * u[1] - ax[1] * u[0])
    raus = []
    for i in range(n):
        w0, w1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        wm = (w0 + w1) / 2

        def rand(p, w):
            c, s = math.cos(w) * r, math.sin(w) * r
            return (p[0] + u[0] * c + v[0] * s, p[1] + u[1] * c + v[1] * s, p[2] + u[2] * c + v[2] * s)
        nrm = tuple(u[k] * math.cos(wm) + v[k] * math.sin(wm) for k in range(3))
        raus.append(Flaeche([rand(a, w0), rand(b, w0), rand(b, w1), rand(a, w1)], nrm, farbe, glanz=glanz))
    return raus


def flach(flaechen, dx_je_z=0.5, dy_je_z=0.3) -> list:
    """Die Flaechen auf den Boden gedrueckt (z = 0), um ihre Hoehe in
    Lichtrichtung verschoben - daraus wird ein Schatten."""
    raus = []
    for f in flaechen:
        pts = [(p[0] + p[2] * dx_je_z, p[1] + p[2] * dy_je_z, 0.0) for p in f.punkte]
        raus.append(Flaeche(pts, (0, 0, 1), (0, 0, 0), beidseitig=True))
    return raus
