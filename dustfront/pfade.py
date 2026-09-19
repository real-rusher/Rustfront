"""
DUSTFRONT - Wo die Dateien liegen
=================================

Einstellungen, Tastenbelegung und Spielstaende gehoeren **nicht** in den
Spielordner. Wer das Spiel neu herunterlaedt, den Ordner loescht oder
`git clean` laufen laesst, haette sonst alles verloren.

Stattdessen benutzt jedes System seinen eigenen Platz dafuer:

    Windows   %APPDATA%\\Dustfront
              C:\\Users\\<name>\\AppData\\Roaming\\Dustfront
    macOS     ~/Library/Application Support/Dustfront
    Linux     $XDG_CONFIG_HOME/dustfront, sonst ~/.config/dustfront

**Tragbarer Betrieb.** Liegt eine Datei `portable.txt` neben dem Paket, wird
stattdessen der Unterordner `daten` im Spielordner benutzt. Praktisch fuer
einen USB-Stick oder einen Schulrechner, auf dem man nichts im Benutzerprofil
ablegen will.

Faellt beides aus, etwa weil nirgends geschrieben werden darf, laeuft das
Spiel trotzdem. Dann ist `ordner()` None, und alles, was speichert, merkt
das und laesst es bleiben.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

NAME = "Dustfront"

_gemerkt: Path | None = None
_geprueft = False


def paketordner() -> Path:
    return Path(__file__).resolve().parent


def spielordner() -> Path:
    """Der Ordner, in dem das Paket liegt, also das Projektverzeichnis."""
    return paketordner().parent


def _system_ordner() -> Path:
    if sys.platform.startswith("win"):
        wurzel = os.environ.get("APPDATA")
        if wurzel:
            return Path(wurzel) / NAME
        return Path.home() / "AppData" / "Roaming" / NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / NAME
    wurzel = os.environ.get("XDG_CONFIG_HOME")
    if wurzel:
        return Path(wurzel) / NAME.lower()
    return Path.home() / ".config" / NAME.lower()


def tragbar() -> bool:
    return (spielordner() / "portable.txt").is_file()


def ordner() -> Path | None:
    """Der Ordner fuer Einstellungen und Spielstaende, oder None.

    Wird einmal ermittelt und dann gemerkt. Das Verzeichnis wird angelegt,
    falls es noch nicht da ist.
    """
    global _gemerkt, _geprueft
    if _geprueft:
        return _gemerkt
    _geprueft = True
    ziel = (spielordner() / "daten") if tragbar() else _system_ordner()
    try:
        ziel.mkdir(parents=True, exist_ok=True)
        probe = ziel / ".schreibtest"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        _gemerkt = ziel
    except OSError:
        _gemerkt = None
    return _gemerkt


def datei(name: str) -> Path | None:
    o = ordner()
    return (o / name) if o is not None else None


def beschreibung() -> str:
    """Einzeiler fuer die Anzeige in den Einstellungen."""
    o = ordner()
    if o is None:
        return "NICHT SCHREIBBAR"
    return str(o)
