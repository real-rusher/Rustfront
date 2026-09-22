"""
DUSTFRONT - Einstieg
====================

    python -m dustfront                Spiel starten
    python -m dustfront --host ...     LAN-Runde aufmachen, siehe README
    python -m dustfront --join WOHIN   einer LAN-Runde beitreten
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
            port: int = 0, headless: bool = False,
            modus: str = K.MODUS_VORGABE, ende_art: str = "zeit",
            ende_wert: float = 0.0, knapp: bool = False,
            schutz: bool | None = None, medkits: int | None = None,
            medkit_spawn: bool | None = None, runden: int | None = None,
            team: int | None = None, online: bool = False,
            passwort: str = "") -> int:
    """LAN-Test: als Gastgeber aufmachen oder als Gast verbinden.

    Die Spielart bestimmt allein der Gastgeber. Ein Gast bekommt sie mit
    dem Willkommen zugeschickt - sonst spielen zwei Leute mit verschiedenen
    Regeln auf derselben Karte.
    """
    from . import netz
    from .mehrspieler import Gefecht

    app = App("DUSTFRONT - GEFECHT", asset_ordner(), headless=headless)
    wirt = gast = None
    try:
        if gastgeber:
            wirt = netz.Gastgeber(port or None, online=online)
            regeln = K.MODI.get(modus, K.MODI[K.MODUS_VORGABE])
            print("Gastgeber laeuft: %s - %s" % (regeln["name"], regeln["hinweis"]))
            if regeln["teams"]:
                print("Mannschaften: %s gegen %s, neue Leute gehen in die "
                      "kleinere." % K.TEAMS["namen"])
            if regeln["zone"]:
                print("Der Kreis liegt in der Kartenmitte, Ebene %d. Wer dort "
                      "die Mehrheit hat, laedt bis %d."
                      % (K.ZONE["ebene"], int(K.ZONE["bis"])))
            elif regeln["runden"]:
                print("Ein Leben je Runde, %d Rundensiege entscheiden. "
                      "Aufhelfen geht nur in der eigenen Mannschaft."
                      % (K.VERSUS["runden_bis"] if runden is None else runden))
            elif not regeln["revive"]:
                print("Endet nach %s" % ("Zeit" if ende_art == "zeit"
                                         else "Abschuessen"))
            if knapp:
                print("Munition ist knapp, es gibt Nachschubkisten.")
            print("Einstiegsschutz: %s"
                  % ("%.0f Sekunden" % K.GEFECHT["schutz"]
                     if (K.GEFECHT["schutz_an"] if schutz is None else schutz)
                     else "aus"))
            wieviele = (K.GEFECHT["start_medkits"] if medkits is None
                        else medkits)
            print("Medkits beim Einstieg: %d" % wieviele)
            print("Medkits auf der Karte: %s"
                  % ("alle %.0f Sekunden" % K.GEFECHT["medkit_takt"]
                     if (K.GEFECHT["medkits_spawnen"] if medkit_spawn is None
                         else medkit_spawn) else "keine"))
            if passwort:
                print("Kennwort: %s" % netz.passwort_saeubern(passwort))
            print("Im eigenen Netz verbinden sich Mitspieler mit:")
            print("   %s" % wirt.adresse)
            if online and wirt.freigabe is not None:
                print()
                for zeile in wirt.freigabe.bericht():
                    print(zeile)
                print()
                print("Ueber das Internet ist die Verzoegerung so gross wie")
                print("die Leitung: der Gastgeber rechnet alles, ein Gast")
                print("sieht seine Figur erst nach einem Hin- und Rueckweg.")
                if not passwort:
                    print("Ohne Kennwort (--passwort) kann jeder mitspielen,")
                    print("der die Adresse kennt.")
        else:
            gast = netz.Gast(wohin)
            if not gast.offen:
                print("Keine Verbindung zu %s: %s" % (wohin, gast.fehler))
                return 1
            print("Verbunden mit %s" % wohin)
    except OSError as grund:
        print("Konnte nicht aufmachen: %s" % grund)
        return 1

    app.schieben(Gefecht(app, name or "GAST", gastgeber=wirt, gast=gast,
                         modus=modus, ende_art=ende_art,
                         ende_wert=ende_wert, knapp=knapp, schutz=schutz,
                         medkits=medkits, medkit_spawn=medkit_spawn,
                         runden=runden, team=team, passwort=passwort))
    app.laufen()
    return 0


def team_lesen(text: str) -> int | None:
    """"rot", "blau" oder "auto" in eine Mannschaftsnummer uebersetzen."""
    text = (text or "").strip().lower()
    if not text or text in ("auto", "egal", "-"):
        return None
    for i, name in enumerate(K.TEAMS["namen"]):
        if text == name.lower() or text == str(i + 1):
            return i
    return None


def aus_argumenten(argumente: list[str]) -> int:
    """Wertet die Kommandozeile aus. Ohne Schalter startet das Spiel."""
    def wert(schalter, vorgabe=""):
        if schalter in argumente:
            i = argumente.index(schalter)
            if i + 1 < len(argumente):
                return argumente[i + 1]
        return vorgabe

    if "--host" in argumente:
        modus = wert("--modus", K.MODUS_VORGABE).strip().lower()
        if modus not in K.MODI:
            print("Unbekannte Spielart %r. Moeglich: %s"
                  % (modus, ", ".join(K.MODI)))
            return 1
        ende_art = wert("--ende", "zeit").strip().lower()
        if ende_art not in K.ENDE_ARTEN:
            print("Unbekanntes Ende %r. Moeglich: %s"
                  % (ende_art, ", ".join(K.ENDE_ARTEN)))
            return 1
        try:
            ende_wert = float(wert("--wert", "0") or 0)
        except ValueError:
            print("--wert braucht eine Zahl.")
            return 1
        try:
            medkits = int(wert("--medkits", str(K.GEFECHT["start_medkits"])))
        except ValueError:
            print("--medkits braucht eine ganze Zahl.")
            return 1
        try:
            runden = int(wert("--runden", str(K.VERSUS["runden_bis"])))
        except ValueError:
            print("--runden braucht eine ganze Zahl.")
            return 1
        return gefecht(True, name=wert("--name", "GASTGEBER"),
                       port=int(wert("--port", "0") or 0),
                       modus=modus, ende_art=ende_art, ende_wert=ende_wert,
                       knapp="--knapp" in argumente,
                       schutz="--kein-schutz" not in argumente,
                       medkits=medkits, runden=runden,
                       team=team_lesen(wert("--team", "")),
                       online="--online" in argumente,
                       passwort=wert("--passwort", ""),
                       medkit_spawn="--keine-medkits" not in argumente)
    if "--join" in argumente:
        return gefecht(False, wohin=wert("--join"),
                       name=wert("--name", "GAST"),
                       passwort=wert("--passwort", ""),
                       team=team_lesen(wert("--team", "")))
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
