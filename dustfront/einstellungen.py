"""
DUSTFRONT - Einstellungen und Tastenbelegung
============================================

Alles, was der Spieler einstellt, liegt in zwei JSON-Dateien im Benutzer-
ordner des Systems (siehe pfade.py), nicht im Spielordner. Damit ueberlebt
jede Einstellung ein Neuherunterladen des Spiels.

    einstellungen.json   Bild, Ton, Anzeige
    tasten.json          Tastenbelegung

Tasten werden als Namen gespeichert, nicht als Zahlen. In der Datei steht
also "w" und "left shift", nicht 119 und 1073742049. Das kann man von Hand
lesen und notfalls mit einem Texteditor reparieren.

Unbekannte Eintraege in den Dateien werden verworfen, fehlende durch die
Vorgabe ersetzt. Eine kaputte Datei kostet damit hoechstens die eine
Einstellung, die kaputt ist, nie den Start.
"""

from __future__ import annotations

import json

import pygame

from . import pfade

# ══════════════════════════════════════════════════ Vorgaben

VORGABE = {
    # Anzeige
    "fenstermodus": "fenster",     # fenster | randlos | vollbild
    "aufloesung": "1280x720",
    "bildrate": 0,                 # 0 = unbegrenzt, sonst Obergrenze
    "pixelraster": "gefuellt",     # gefuellt | ganzzahlig
    # Ton
    "ton_gesamt": 75,
    "ton_effekte": 85,
    "ton_musik": 60,
    # Grafik (noch ohne Wirkung, die Schalter stehen schon bereit)
    "vignette": True,
    "bildschirm_ruckeln": 100,     # Prozent der Staerke
    "partikel": "viel",            # wenig | normal | viel
    # Spiel
    "tracer": False,
    "tracer_weit": False,
}

AUFLOESUNGEN = ["1280x720", "1600x900", "1920x1080", "2560x1440", "960x540"]
FENSTERMODI = ["fenster", "randlos", "vollbild"]
PARTIKEL = ["wenig", "normal", "viel"]
RASTER = ["gefuellt", "ganzzahlig"]

# ══════════════════════════════════════════════════ Tastenbelegung

# Reihenfolge ist zugleich die Reihenfolge im Menue.
TASTEN_VORGABE = [
    ("vor",         "VORWAERTS",        ["w", "up"]),
    ("zurueck",     "ZURUECK",          ["s", "down"]),
    ("links",       "LINKS",            ["a", "left"]),
    ("rechts",      "RECHTS",           ["d", "right"]),
    ("sprint",      "SPRINT",           ["left shift", "right shift"]),
    ("nutzen",      "BENUTZEN",         ["e"]),
    ("nachladen",   "NACHLADEN",        ["r"]),
    ("heilen",      "MEDKIT",           ["h"]),
    ("inventar",    "INVENTAR",         ["tab"]),
    ("waffe1",      "PLATZ 1",          ["1"]),
    ("waffe2",      "PLATZ 2",          ["2"]),
    ("waffe3",      "PLATZ 3",          ["3"]),
    ("waffe4",      "PLATZ 4",          ["4"]),
    ("waffe5",      "PLATZ 5",          ["5"]),
    ("waffe6",      "PLATZ 6",          ["6"]),
    ("tracer",      "ZIELLINIE",        ["t"]),
    ("tracer_weit", "LINIE VERLAENGERN", ["z"]),
    ("pause",       "PAUSE",            ["escape"]),
    ("vollbild",    "VOLLBILD",         ["f11"]),
    ("debug",       "DEBUG-ANZEIGE",    ["f3"]),
]

# Diese Aktionen lassen sich nicht umlegen, sonst sperrt man sich aus.
FEST = {"pause"}


def taste_name(code: int) -> str:
    try:
        return pygame.key.name(code)
    except Exception:
        return "?"


def taste_code(name: str) -> int | None:
    try:
        c = pygame.key.key_code(name)
        return c if c > 0 else None
    except Exception:
        return None


# ══════════════════════════════════════════════════ Ablage

class Einstellungen:
    """Liest und schreibt beide Dateien. Faellt weich zurueck."""

    def __init__(self) -> None:
        self.werte = dict(VORGABE)
        self.tasten: dict[str, list[str]] = {
            name: list(vorgabe) for name, _, vorgabe in TASTEN_VORGABE
        }
        self.gelesen_von: str = "Vorgabe"
        self.laden()

    # ---- Zugriff -----------------------------------------------------
    def __getitem__(self, schluessel: str):
        return self.werte.get(schluessel, VORGABE.get(schluessel))

    def __setitem__(self, schluessel: str, wert) -> None:
        self.werte[schluessel] = wert

    def codes(self, aktion: str) -> list[int]:
        """Tastencodes einer Aktion, fuer den Vergleich im Spiel."""
        raus = []
        for name in self.tasten.get(aktion, ()):
            c = taste_code(name)
            if c is not None:
                raus.append(c)
        return raus

    def tastentabelle(self) -> dict[str, list[int]]:
        return {a: self.codes(a) for a in self.tasten}

    def belegen(self, aktion: str, code: int) -> str | None:
        """Legt eine Aktion auf eine Taste. Gibt die verdraengte Aktion zurueck.

        Eine Taste gehoert immer nur einer Aktion. War sie schon vergeben,
        wird sie dort entfernt, damit nichts doppelt belegt ist.
        """
        if aktion in FEST:
            return None
        name = taste_name(code)
        verdraengt = None
        for andere, liste in self.tasten.items():
            if andere == aktion or andere in FEST:
                continue
            if name in liste:
                liste.remove(name)
                verdraengt = andere
        self.tasten[aktion] = [name]
        self.speichern()
        return verdraengt

    def zuruecksetzen_tasten(self) -> None:
        self.tasten = {name: list(v) for name, _, v in TASTEN_VORGABE}
        self.speichern()

    def zuruecksetzen_werte(self) -> None:
        self.werte = dict(VORGABE)
        self.speichern()

    # ---- Datei -------------------------------------------------------
    def laden(self) -> None:
        d = pfade.datei("einstellungen.json")
        if d is not None and d.is_file():
            try:
                roh = json.loads(d.read_text(encoding="utf-8"))
                for k, v in roh.items():
                    # Nur bekannte Schluessel mit passendem Typ uebernehmen
                    if k in VORGABE and isinstance(v, type(VORGABE[k])):
                        self.werte[k] = v
                self.gelesen_von = str(d)
            except (OSError, ValueError):
                pass
        t = pfade.datei("tasten.json")
        if t is not None and t.is_file():
            try:
                roh = json.loads(t.read_text(encoding="utf-8"))
                bekannt = {name for name, _, _ in TASTEN_VORGABE}
                for k, v in roh.items():
                    if k in bekannt and isinstance(v, list):
                        namen = [str(x) for x in v if taste_code(str(x)) is not None]
                        if namen:
                            self.tasten[k] = namen
            except (OSError, ValueError):
                pass

    def speichern(self) -> bool:
        ok = True
        d = pfade.datei("einstellungen.json")
        if d is not None:
            try:
                d.write_text(json.dumps(self.werte, indent=2, ensure_ascii=False),
                             encoding="utf-8")
            except OSError:
                ok = False
        t = pfade.datei("tasten.json")
        if t is not None:
            try:
                t.write_text(json.dumps(self.tasten, indent=2, ensure_ascii=False),
                             encoding="utf-8")
            except OSError:
                ok = False
        return ok

    def aufloesung_paar(self) -> tuple[int, int]:
        try:
            b, h = str(self["aufloesung"]).lower().split("x")
            return max(320, int(b)), max(180, int(h))
        except (ValueError, AttributeError):
            return 1280, 720
