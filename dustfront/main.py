"""
DUSTFRONT - Einstieg
====================

    python -m dustfront

Bilder werden, falls vorhanden, aus dem Ordner `assets` neben dem Paket
geladen. Fehlt der Ordner, zeichnet sich das Spiel seine Platzhalter selbst.
"""

from __future__ import annotations

from pathlib import Path

from .core import App
from .play import Spiel


def asset_ordner() -> Path | None:
    p = Path(__file__).resolve().parent.parent / "assets"
    return p if p.is_dir() else None


def starten(headless: bool = False) -> int:
    app = App("DUSTFRONT", asset_ordner(), headless=headless)
    app.schieben(Spiel(app))
    app.laufen()
    return 0
