"""
DUSTFRONT - Die Schrottbombe des Tragschraubers (seit 0.34.123)
===============================================================

Gewuenscht: passend zu einem Fluggeraet aus Schrott, ohne Panzerung - also
keine Fliegerbombe, sondern was man selbst zusammenbaut: eine alte,
verrostete Blechdose, mit Draht umwickelt, ein paar Naegel unter dem Draht,
ein Streifen Klebeband, oben eine Lunte. Klein. Vor dem Abwurf sieht man
sie nicht (der Fahrer hat sie bei sich im Sitz), er zuendet sie und laesst
sie neben der Kanzel fallen.

Im Fall ueberschlaegt sie sich langsam; die Lunte glimmt und sprueht
Funken (das zeichnet luft.py). Die Bilder hier sind die Dose allein, in
12 Drehstufen, je fuer sich gemalt (nicht gedreht), damit sie auch schraeg
scharf bleibt.
"""

from __future__ import annotations

import math

import pygame

GROSS = 4               # so viel feiner wird gemalt, dann verkleinert
FELD = 16               # Bildgroesse in Spielpixeln

ROST = (122, 68, 38)
ROST_HELL = (164, 98, 52)
ROST_DK = (78, 44, 28)
FLECK = (184, 112, 50)
BLECH = (150, 138, 120)          # blanker Rand der Dose
DRAHT = (176, 172, 160)
BAND = (108, 112, 88)            # Klebeband, olivgrau
NAGEL = (190, 186, 176)
LUNTE = (104, 86, 62)

# Lage der Lunte (Spitze) in der Dose, Spielpixel: die Achse der Dose ist y,
# oben ist -y.
LUNTE_SPITZE = (1.3, -5.6)

_BILDER: dict = {}


def _punkt(x: float, y: float, w: float) -> tuple:
    c, s = math.cos(w), math.sin(w)
    return ((FELD / 2 + x * c - y * s) * GROSS, (FELD / 2 + x * s + y * c) * GROSS)


def lunte_spitze(winkel: float) -> tuple:
    """Wo die Spitze der Lunte gerade ist, relativ zur Mitte der Dose."""
    w = math.radians(winkel)
    x, y = LUNTE_SPITZE
    return (x * math.cos(w) - y * math.sin(w), x * math.sin(w) + y * math.cos(w))


def _zeichnen(winkel: float) -> pygame.Surface:
    w = math.radians(winkel)
    s = pygame.Surface((FELD * GROSS, FELD * GROSS), pygame.SRCALPHA)

    def viereck(farbe, x0, y0, x1, y1):
        pygame.draw.polygon(s, farbe, [_punkt(x0, y0, w), _punkt(x1, y0, w), _punkt(x1, y1, w), _punkt(x0, y1, w)])

    def strich(farbe, a, b, dick):
        pygame.draw.line(s, farbe, _punkt(a[0], a[1], w), _punkt(b[0], b[1], w), max(1, int(dick * GROSS)))

    def punkt(farbe, x, y, r):
        pygame.draw.circle(s, farbe, [int(v) for v in _punkt(x, y, w)], max(1, int(r * GROSS)))

    # Die Lunte zuerst - sie kommt oben aus dem Deckel und knickt ab.
    strich(LUNTE, (0.2, -3.4), (0.5, -4.8), 0.9)
    strich(LUNTE, (0.5, -4.8), LUNTE_SPITZE, 0.9)
    # Die Dose: Rost, links vom Licht heller, rechts dunkler.
    viereck(ROST, -2.4, -3.3, 2.4, 3.3)
    viereck(ROST_HELL, -2.4, -3.3, -1.2, 3.3)
    viereck(ROST_DK, 1.4, -3.3, 2.4, 3.3)
    punkt(FLECK, 0.4, 0.4, 0.7)
    punkt(FLECK, -0.9, 2.2, 0.45)
    # Der gefalzte Rand oben und unten, verbeult (unten schief).
    viereck(BLECH, -2.6, -3.6, 2.6, -2.9)
    viereck(BLECH, -2.6, 2.9, 2.3, 3.6)
    viereck(ROST_DK, 2.3, 2.9, 2.6, 3.4)
    # Klebeband quer, Draht zweimal herum, Naegel stehen raus.
    viereck(BAND, -2.5, -0.6, 2.5, 0.5)
    strich(DRAHT, (-2.6, -1.8), (2.6, -1.6), 0.35)
    strich(DRAHT, (-2.6, 1.7), (2.6, 1.9), 0.35)
    for x, y, dx in ((-2.5, -1.2, -0.9), (2.5, 1.2, 0.9), (2.5, -2.3, 0.8), (-2.5, 2.5, -0.8)):
        strich(NAGEL, (x, y), (x + dx, y), 0.35)
        punkt(NAGEL, x + dx, y, 0.3)
    klein = pygame.transform.smoothscale(s, (FELD, FELD))
    from . import art
    return art._rand(klein)


def schrottbombe(winkel: float) -> pygame.Surface:
    """Die Dose, um `winkel` Grad gedreht (gerundet auf 30 Grad)."""
    stufe = int(round(winkel / 30.0)) % 12
    s = _BILDER.get(stufe)
    if s is None:
        s = _zeichnen(stufe * 30.0)
        _BILDER[stufe] = s
    return s
