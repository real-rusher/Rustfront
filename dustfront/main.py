"""
DUSTFRONT - Einstieg
====================

    python -m dustfront                Spiel starten
    python -m dustfront --vorlagen     jedes Bild als Vorlage herausschreiben
    python -m dustfront --assets       zeigen, was aus Dateien kommt

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


def gefecht(gastgeber: bool, wohin: str = "", name: str = "",
            port: int = 0, headless: bool = False) -> int:
    """LAN-Test: als Gastgeber aufmachen oder als Gast verbinden."""
    from . import netz
    from .mehrspieler import Gefecht

    app = App("DUSTFRONT - GEFECHT", asset_ordner(), headless=headless)
    wirt = gast = None
    try:
        if gastgeber:
            wirt = netz.Gastgeber(port or None)
            print("Gastgeber laeuft. Mitspieler verbinden sich mit:")
            print("   %s" % wirt.adresse)
        else:
            gast = netz.Gast(wohin)
            if not gast.offen:
                print("Keine Verbindung zu %s: %s" % (wohin, gast.fehler))
                return 1
            print("Verbunden mit %s" % wohin)
    except OSError as grund:
        print("Konnte nicht aufmachen: %s" % grund)
        return 1

    app.schieben(Gefecht(app, name or "GAST", gastgeber=wirt, gast=gast))
    app.laufen()
    return 0


def aus_argumenten(argumente: list[str]) -> int:
    """Wertet die Kommandozeile aus. Ohne Schalter startet das Spiel."""
    def wert(schalter, vorgabe=""):
        if schalter in argumente:
            i = argumente.index(schalter)
            if i + 1 < len(argumente):
                return argumente[i + 1]
        return vorgabe

    if "--host" in argumente:
        return gefecht(True, name=wert("--name", "GASTGEBER"),
                       port=int(wert("--port", "0") or 0))
    if "--join" in argumente:
        return gefecht(False, wohin=wert("--join"),
                       name=wert("--name", "GAST"))
    if "--bestenliste" in argumente:
        from . import bestenliste
        daten = bestenliste.laden()
        print("Bestenliste: %s" % bestenliste.beschreibung())
        if not daten["eintraege"]:
            print("  noch leer")
        for platz, e in enumerate(daten["eintraege"], 1):
            print("  %2d. %-12s %4d Abschuesse  %4d Tode  %3d Runden"
                  % (platz, e["name"], e["abschuesse"], e["tode"], e["runden"]))
        return 0
    if "--vorlagen" in argumente:
        from .vorlagen import schreiben
        schreiben()
        return 0
    if "--assets" in argumente:
        from .vorlagen import bestand
        return bestand()
    return starten()
