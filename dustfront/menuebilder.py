"""Grosse Bilder fuer das Menue AUSRUESTUNG (seit 0.34.82).

Gewuenscht: "damit die Waffen im Menue cooler und anders als im Spiel selbst
aussehen". Die Bilder kommen aus einem Bildgenerator (Prompts in
docs/BILDPROMPTS.md) und liegen als assets/menue/<kennung>.jpg neben dem
Spiel. Sie gehoeren nur ins Menue: im Spiel bleibt jedes Bild das kleine
Pixelbild, und fehlt eine Datei, zeigt auch das Menue wieder das.

    bild("sturm", 140)    -> Surface 140 breit, oder None
"""
from __future__ import annotations

import pygame

from . import config as K
from .pfade import spielordner

# Kennung -> Originalbild (oder None, wenn es keines gibt). Geladen wird
# erst, wenn das Menue es braucht: 54 Bilder beim Start kosteten Zeit, die
# niemand bemerkt haette, der das Menue nie oeffnet.
_roh: dict = {}
# (Kennung, Breite) -> skaliert. Weich skaliert: es ist ein Gemaelde,
# kein Pixelbild, und harte Kanten saehen hier nach Fehler aus.
_fertig: dict = {}


def _ordner():
    return spielordner() / K.ASSETS["ordner"] / K.MENUEBILDER["ordner"]


def _laden(kennung: str):
    if kennung in _roh:
        return _roh[kennung]
    bild = None
    for endung in K.MENUEBILDER["endungen"]:
        pfad = _ordner() / (kennung + endung)
        if pfad.is_file():
            try:
                bild = pygame.image.load(str(pfad))
                if pygame.display.get_surface() is not None:
                    bild = bild.convert()
            except (pygame.error, OSError):
                bild = None       # kaputte Datei: dann eben das Pixelbild
            break
    _roh[kennung] = bild
    return bild


def bild(kennung: str, breite: int):
    """Das Menuebild von `kennung` in dieser Breite, oder None."""
    if not kennung or breite <= 0:
        return None
    schluessel = (kennung, int(breite))
    if schluessel in _fertig:
        return _fertig[schluessel]
    roh = _laden(kennung)
    s = None
    if roh is not None:
        hoch = max(1, round(roh.get_height() * breite / roh.get_width()))
        s = pygame.transform.smoothscale(roh, (int(breite), hoch))
    _fertig[schluessel] = s
    return s


def vorhanden() -> list:
    """Welche Kennungen ein Menuebild haben (fuer Tests und --assets)."""
    o = _ordner()
    if not o.is_dir():
        return []
    return sorted({p.stem for p in o.iterdir() if p.suffix in K.MENUEBILDER["endungen"]})
