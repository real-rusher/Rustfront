"""
DUSTFRONT - Wesen als Daten (seit 0.34.29)
==========================================

Spezies, Ziele und Aktionen der zielorientierten KI (goap.py) stehen
nicht im Code, sondern in Textdateien im Ordner `wesen/` neben dem
Spiel - wie die Karten in `karten/`. Man kann sie ohne Programmieren
aendern; `tests/test_pruefung.py` prueft sie (`pruefen`).

Das Format, ein Block je Ding:

    # Kommentar
    [ziel nachladen]
    will: !magazin_leer
    dringlich: 80 * magazin_leer * munition_da
    info: Ein leeres Magazin ist das Erste, was weg muss.

    [aktion nachladen_in_deckung]
    braucht: in_deckung, magazin_leer
    macht: !magazin_leer
    kosten: 1
    tut: nachladen
    funk: nachladen

    [spezies mp_bot]
    name: BOT
    ziele: nachladen, ...
    aktionen: nachladen_in_deckung, ...
    merkmal mut: 0.3 0.9

* `will`, `braucht`, `macht`: Fakten, mit Komma getrennt, `!` davor heisst
  "nicht". Welche Fakten es gibt, sagt der, der die Spezies benutzt (fuer
  die Bots: bot_goap.py, und oben in `wesen/bots.txt`).
* `dringlich`, `kosten`: eine Rechnung (goap.Ausdruck) aus Fakten (1/0),
  Zahlen (`leben`, `abstand` ...) und Merkmalen.
* `tut`: welches Verhalten die Aktion ausfuehrt (bot_goap.TUN).
* `merkmal NAME: VON BIS`: jedes Wesen wuerfelt seinen Wert dazwischen.

Ein Name darf in mehreren Dateien nur einmal vorkommen.
"""

from __future__ import annotations

from pathlib import Path

from . import goap


class Spezies:
    def __init__(self, name: str) -> None:
        self.name = name
        self.anzeige = name.upper()
        self.ziele: list[str] = []
        self.aktionen: list[str] = []
        self.merkmale: dict[str, tuple] = {}
        self.info = ""

    def merkmale_wuerfeln(self, rnd) -> dict:
        return {n: round(rnd.uniform(lo, hi), 2) for n, (lo, hi) in self.merkmale.items()}


class Daten:
    def __init__(self) -> None:
        self.ziele: dict = {}
        self.aktionen: dict = {}
        self.spezies: dict = {}
        self.fehler: list[str] = []

    def gehirn(self, spezies: str, merkmale: dict):
        """Ein frisches Gehirn fuer ein Wesen dieser Spezies."""
        sp = self.spezies[spezies]
        return goap.Gehirn([self.ziele[z] for z in sp.ziele if z in self.ziele],
                           [self.aktionen[a] for a in sp.aktionen if a in self.aktionen],
                           merkmale)


def ordner() -> Path:
    from .pfade import spielordner
    return spielordner() / "wesen"


def aus_text(text: str, daten: Daten, datei: str = "") -> None:
    """Einen Text lesen und in `daten` eintragen. Fehler landen in
    `daten.fehler`, mit Datei und Zeile - eine kaputte Zeile kostet nur
    den einen Block, nicht das Spiel."""
    block = None

    def abschliessen():
        if block is None:
            return
        art, name, felder, zeile = block
        try:
            if art == "ziel":
                ding = goap.Ziel(name, felder.get("will", ""), felder.get("dringlich", "0"),
                                 felder.get("info", ""))
                ziel_dict = daten.ziele
            elif art == "aktion":
                ding = goap.Aktion(name, felder.get("braucht", ""), felder.get("macht", ""),
                                   felder.get("kosten", "1"), felder.get("tut", ""),
                                   felder.get("funk", ""), felder.get("info", ""))
                ziel_dict = daten.aktionen
            elif art == "spezies":
                ding = Spezies(name)
                ding.anzeige = felder.get("name", name.upper())
                ding.ziele = [x.strip() for x in felder.get("ziele", "").split(",") if x.strip()]
                ding.aktionen = [x.strip() for x in felder.get("aktionen", "").split(",") if x.strip()]
                ding.info = felder.get("info", "")
                for schluessel, wert in felder.items():
                    if schluessel.startswith("merkmal "):
                        teile = wert.split()
                        lo = float(teile[0])
                        hi = float(teile[1]) if len(teile) > 1 else lo
                        ding.merkmale[schluessel[8:].strip()] = (min(lo, hi), max(lo, hi))
                ziel_dict = daten.spezies
            else:
                daten.fehler.append("%s:%d: unbekannte Art [%s]" % (datei, zeile, art))
                return
        except (ValueError, SyntaxError, IndexError) as fehler:
            daten.fehler.append("%s:%d: [%s %s] %s" % (datei, zeile, art, name, fehler))
            return
        if name in ziel_dict:
            daten.fehler.append("%s:%d: [%s %s] gibt es schon" % (datei, zeile, art, name))
            return
        ziel_dict[name] = ding

    for nr, roh in enumerate(text.splitlines(), 1):
        zeile = roh.strip()
        if not zeile or zeile.startswith("#"):
            continue
        if zeile.startswith("[") and zeile.endswith("]"):
            abschliessen()
            teile = zeile[1:-1].split()
            if len(teile) != 2:
                daten.fehler.append("%s:%d: Kopf braucht Art und Name: %s" % (datei, nr, zeile))
                block = None
                continue
            block = (teile[0].lower(), teile[1], {}, nr)
            continue
        if block is None or ":" not in zeile:
            daten.fehler.append("%s:%d: Zeile ohne Block oder ohne ':': %s" % (datei, nr, zeile))
            continue
        schluessel, _, wert = zeile.partition(":")
        block[2][schluessel.strip().lower()] = wert.strip()
    abschliessen()


def laden(pfad: Path | None = None) -> Daten:
    """Alle Dateien aus `wesen/` (oder einem anderen Ordner)."""
    daten = Daten()
    pfad = ordner() if pfad is None else Path(pfad)
    if not pfad.is_dir():
        daten.fehler.append("Ordner fehlt: %s" % pfad)
        return daten
    for datei in sorted(pfad.glob("*.txt")):
        aus_text(datei.read_text(encoding="utf-8"), daten, datei.name)
    return daten


_GELADEN: Daten | None = None


def daten() -> Daten:
    """Die Daten des Spiels, einmal geladen."""
    global _GELADEN
    if _GELADEN is None:
        _GELADEN = laden()
    return _GELADEN


def neu_laden() -> Daten:
    """Fuer den Testmodus: Dateien geaendert, ohne das Spiel neu zu starten."""
    global _GELADEN
    _GELADEN = laden()
    return _GELADEN


def pruefen(d: Daten | None = None, tut=None) -> list[str]:
    """Was an den Daten nicht stimmt: Lesefehler, Verweise auf Ziele oder
    Aktionen, die es nicht gibt, und Verhalten (`tut`), die keiner kennt."""
    d = daten() if d is None else d
    fehler = list(d.fehler)
    for sp in d.spezies.values():
        for z in sp.ziele:
            if z not in d.ziele:
                fehler.append("spezies %s: Ziel %s gibt es nicht" % (sp.name, z))
        for a in sp.aktionen:
            if a not in d.aktionen:
                fehler.append("spezies %s: Aktion %s gibt es nicht" % (sp.name, a))
    if tut is not None:
        for a in d.aktionen.values():
            if a.tut not in tut:
                fehler.append("aktion %s: unbekanntes Verhalten '%s'" % (a.name, a.tut))
    return fehler
