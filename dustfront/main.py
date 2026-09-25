"""
DUSTFRONT - Einstieg
====================

    python -m dustfront                Spiel starten
    python -m dustfront --vorlagen     jedes Bild als Vorlage herausschreiben
    python -m dustfront --assets       zeigen, was aus Dateien kommt
    python -m dustfront --probe        den Wandler laufen sehen und fahren

Bilder werden, falls vorhanden, aus dem Ordner `assets` neben dem Paket
geladen, Klaenge aus `assets/sfx`. Fehlt etwas, zeichnet und rechnet sich das
Spiel seine Platzhalter selbst.
"""

from __future__ import annotations

from pathlib import Path

from . import config as K
from .core import App
from .pfade import spielordner
from .play import Spiel


def asset_ordner() -> Path | None:
    p = spielordner() / K.ASSETS["ordner"]
    return p if p.is_dir() else None


def starten(headless: bool = False, beenden: bool = True,
            auftrag: dict | None = None) -> int:
    """Startet das Spiel.

    beenden=False laesst pygame stehen, wenn das Spiel endet - so ruft das
    Hauptmenue uns auf und macht danach weiter.

    auftrag ist das, was das Menue ausgewaehlt hat (Region, Schwierigkeit,
    Rufzeichen). Das Spiel legt es ab, ohne es heute schon auszuwerten:
    daran haengen spaeter die Sektoren, siehe docs/KARTE.md, M5 und M7.
    """
    app = App("DUSTFRONT", asset_ordner(), headless=headless)
    app.auftrag = dict(auftrag) if auftrag else {}
    app.schieben(Spiel(app))
    app.laufen(beenden=beenden)
    return 0


def aus_menue(auftrag: dict | None = None) -> int:
    """Einstieg fuer das Hauptmenue: spielen und danach zurueckkehren."""
    return starten(headless=False, beenden=False, auftrag=auftrag)


def aus_argumenten(argumente: list[str]) -> int:
    """Wertet die Kommandozeile aus. Ohne Schalter startet das Spiel."""
    if "--vorlagen" in argumente:
        from .vorlagen import schreiben
        schreiben()
        return 0
    if "--assets" in argumente:
        from .vorlagen import bestand
        return bestand()
    if "--probe" in argumente:
        from .probe import starten as probe_starten
        return probe_starten()
    return starten()
