"""
DUSTFRONT - Karten aus Dateien
==============================

Bis hierher gab es genau eine Karte, und sie stand als Liste von Zeichenketten
im Code. Ab jetzt ist eine Karte eine **Textdatei** in `karten/`. Damit ist ein
neuer Ort - oder ein neuer Wandler - kein Programmieren mehr, sondern Tippen.

Das Format
----------

Ein Kopf aus `schluessel: wert`, dann je Ebene ein Block. Ebene 0 steht
zuerst, und das ist die unterste.

    name: Probehalle
    grund: boden

    --- ebene 0 ---
    ##########
    #...S....#
    ##########

    --- ebene 1 ---
    ##########
    #   ..   #
    ##########

**Leerzeichen sind Loecher**, keine Luft: sie duerfen am Zeilenende stehen und
werden nicht wegoptimiert. Deshalb wird beim Lesen nur der Zeilenumbruch
abgeschnitten, sonst nichts.

Im Kopf ist `#` ein Kommentar, in den Ebenenbloecken eine Wand. Die beiden
koennen sich nicht in die Quere kommen, weil der erste Trenner sie sauber
scheidet.

Marken
------

Grossbuchstaben und Ziffern sind **Marken**. Sie werden zu einer Kachel *und*
legen ihre Position unter einem Namen ab:

    S  start          R  rampe          T  steuerstand    G  geschuetz
    E  reaktor        W  werkbank       K  kartentisch    F  funk
    M  modulschacht   A  antrieb        Y  werkstatt      L  lager
    B  koje           1-9 punkt1 bis punkt9

Damit muss kein Code mehr wissen, wo der Start liegt oder wo der Steuerstand
steht - es steht in der Karte. Welche Marke welche Kachel setzt, steht in
`K.MARKEN`; wer eine neue erfindet, aendert eine Tabelle, keine Funktion.

Untergrund
----------

`grund: boden` benutzt Wasteland-Kacheln, `grund: deck` die Rumpffamilie.
Die Zeichen sind in beiden Faellen dieselben - ein Deck tippt sich wie ein
Stueck Boden, es sieht nur anders aus.
"""

from __future__ import annotations

from pathlib import Path

from . import config as K
from .pfade import spielordner


class KartenFehler(Exception):
    """Eine Kartendatei laesst sich nicht lesen.

    Fliegt mit einer Meldung, die sagt *welche Datei*, *welche Zeile* und
    *was erwartet wurde*. Eine Karte ist Text, den Menschen tippen, also ist
    eine brauchbare Fehlermeldung hier kein Luxus.
    """


# ──────────────────────────────── Fundstellen

def kartenordner() -> Path:
    return spielordner() / K.KARTEN["ordner"]


def pfad(name: str) -> Path:
    """Vollstaendiger Pfad zu einer Karte, mit oder ohne Endung benannt.

    Ein Name darf einen Unterordner enthalten (`wandler/warhound`), damit
    Ruempfe und Orte sich nicht mischen.
    """
    p = Path(name)
    if not p.suffix:
        p = p.with_suffix(K.KARTEN["endung"])
    return kartenordner() / p


def alle(unterordner: str = "") -> list[str]:
    """Alle Kartennamen, sortiert. Ohne Endung, mit Unterordner."""
    wurzel = kartenordner()
    if unterordner:
        wurzel = wurzel / unterordner
    if not wurzel.is_dir():
        return []
    gefunden = []
    for p in sorted(wurzel.rglob("*" + K.KARTEN["endung"])):
        gefunden.append(p.relative_to(kartenordner()).with_suffix("").as_posix())
    return gefunden


# ──────────────────────────────── Lesen

class Karte:
    """Was in einer Kartendatei steht, noch ohne pygame.

    Absichtlich eine reine Datenklasse: sie laesst sich ohne Bildschirm
    pruefen, und genau das tut der Testlauf.
    """

    def __init__(self, name: str, kopf: dict, bloecke: list[list[str]]) -> None:
        self.name = name
        self.kopf = kopf
        self.bloecke = bloecke

    # ---- Kopf bequem abfragen -----------------------------------------
    def text(self, schluessel: str, ersatz: str = "") -> str:
        wert = self.kopf.get(schluessel, ersatz)
        return wert[0] if isinstance(wert, list) else wert

    def zahl(self, schluessel: str, ersatz: float) -> float:
        roh = self.text(schluessel, "")
        if not roh:
            return ersatz
        try:
            return float(roh)
        except ValueError:
            raise KartenFehler("%s: %r ist keine Zahl bei %s"
                               % (self.name, roh, schluessel))

    def liste(self, schluessel: str) -> list[str]:
        """Alle Zeilen eines mehrfach vorkommenden Schluessels, etwa `bein:`."""
        wert = self.kopf.get(schluessel)
        if wert is None:
            return []
        return list(wert) if isinstance(wert, list) else [wert]

    @property
    def grund(self) -> str:
        return self.text("grund", K.KARTEN["grund_voreinstellung"])

    @property
    def zeichen(self) -> dict:
        return K.ZEICHEN_DECK if self.grund == "deck" else K.ZEICHEN_BODEN

    def __repr__(self) -> str:
        masse = ["%dx%d" % (max(len(z) for z in b), len(b)) for b in self.bloecke]
        return "<Karte %s %s [%s]>" % (self.name, self.grund, " ".join(masse))


def lesen(name: str) -> Karte:
    """Liest eine Kartendatei und gibt ihren Inhalt zurueck."""
    p = pfad(name)
    try:
        roh = p.read_text(encoding="utf-8")
    except OSError as fehler:
        raise KartenFehler("%s: laesst sich nicht lesen (%s)" % (p, fehler))
    return aus_text(roh, name)


def aus_text(roh: str, name: str = "<text>") -> Karte:
    """Dasselbe aus einer Zeichenkette. Getrennt, damit der Test ohne
    Dateien auskommt."""
    kopf: dict = {}
    bloecke: list[list[str]] = []
    laufend: list[str] | None = None
    trenner = K.KARTEN["trenner"]
    kommentar = K.KARTEN["kommentar"]

    for nummer, zeile in enumerate(roh.splitlines(), start=1):
        if zeile.startswith(trenner):
            laufend = []
            bloecke.append(laufend)
            continue
        if laufend is None:                        # noch im Kopf
            blank = zeile.strip()
            if not blank or blank.startswith(kommentar):
                continue
            if ":" not in blank:
                raise KartenFehler(
                    "%s, Zeile %d: %r - im Kopf steht 'schluessel: wert'"
                    % (name, nummer, zeile))
            schluessel, wert = blank.split(":", 1)
            schluessel, wert = schluessel.strip().lower(), wert.strip()
            if schluessel in kopf:                 # mehrfach erlaubt, etwa bein:
                if not isinstance(kopf[schluessel], list):
                    kopf[schluessel] = [kopf[schluessel]]
                kopf[schluessel].append(wert)
            else:
                kopf[schluessel] = wert
            continue
        # In einem Block: die Zeile ist Karte. Nichts abschneiden - ein
        # Leerzeichen am Zeilenende ist ein Loch und kein Versehen.
        laufend.append(zeile.rstrip("\r"))

    # Aufraeumen - und hier liegt eine Falle, in die ich einmal getappt bin:
    #
    # Eine Zeile aus lauter Leerzeichen ist **keine** Leerzeile. Sie ist eine
    # Kartenzeile aus lauter Loechern, und genau daraus besteht die Spitze
    # eines Rumpfes. Wirft man sie weg, verrutscht die halbe Karte.
    #
    # Weg darf nur, was wirklich nichts ist: eine Zeile der Laenge null.
    bloecke = [[z for z in b if len(z) > 0] for b in bloecke]
    bloecke = [b for b in bloecke if b]

    if not bloecke:
        raise KartenFehler("%s: keine einzige Ebene - fehlt der Trenner %r?"
                           % (name, trenner))
    return Karte(name, kopf, bloecke)


# ──────────────────────────────── Pruefen

def pruefen(karte: Karte) -> list[str]:
    """Sucht Fehler, die man einer Karte ansieht, ohne sie zu spielen.

    Gibt eine Liste von Klartextmeldungen zurueck, leer heisst in Ordnung.
    Das ist die Grundlage des Kartentests: er laedt jede Datei im Ordner und
    verlangt, dass hier nichts herauskommt.
    """
    fehler = []
    if karte.grund not in ("boden", "deck"):
        fehler.append("grund: %r - erlaubt sind 'boden' und 'deck'"
                      % karte.grund)
    if len(karte.bloecke) > K.HOEHEN["decks_hoechstens"] + 1:
        fehler.append("%d Ebenen - hoechstens %d"
                      % (len(karte.bloecke), K.HOEHEN["decks_hoechstens"] + 1))

    bekannt = set(karte.zeichen) | set(K.MARKEN)
    for idx, block in enumerate(karte.bloecke):
        if not block:
            fehler.append("Ebene %d ist leer" % idx)
            continue
        unbekannt = sorted({z for zeile in block for z in zeile} - bekannt)
        if unbekannt:
            fehler.append("Ebene %d: unbekannte Zeichen %s"
                          % (idx, " ".join(repr(z) for z in unbekannt)))
    return fehler


def pruefen_welt(welt) -> list[str]:
    """Baulicher Pruefer: stimmt die Karte, wenn man sie wirklich begeht?

    Drei Fragen, und alle drei sind schon einmal falsch beantwortet worden,
    als Karten noch von Hand gezaehlt wurden:

    1. **Fluchten die Treppen?** Eine Treppe nach oben ist wertlos, wenn auf
       der Zielebene an derselben Stelle eine Wand oder ein Loch steht - man
       laeuft hin, drueckt E, und nichts passiert.
    2. **Kommt man ueberall hin?** Von der Startmarke aus muss jede Ebene
       erreichbar sein, sonst hat jemand ein Deck gebaut, das niemand
       betritt.
    3. **Steht der Start im Freien?** Eine Startmarke in einer Wand ist ein
       Spiel, das im Dunkeln beginnt.

    Zurueck kommen Klartextmeldungen, leer heisst in Ordnung.
    """
    fehler = []
    for e in welt.ebenen:
        if not any(e.begehbar(tx, ty)
                   for ty in range(e.hoehe) for tx in range(e.breite)):
            fehler.append("Ebene %d hat keine begehbare Kachel" % e.index)

    # 1. Treppen
    for e in welt.ebenen:
        for ty in range(e.hoehe):
            for tx in range(e.breite):
                rel = e.daten(tx, ty).get("treppe")
                if rel is None:
                    continue
                ziel = e.index + rel
                if not 0 <= ziel < len(welt.ebenen):
                    fehler.append("Ebene %d (%d,%d): Treppe nach %d, die es "
                                  "nicht gibt" % (e.index, tx, ty, ziel))
                    continue
                if not welt.ebene(ziel).begehbar(tx, ty):
                    fehler.append("Ebene %d (%d,%d): Treppe nach %d, aber dort "
                                  "ist kein Boden" % (e.index, tx, ty, ziel))

    # 2. und 3. Erreichbarkeit ab der Startmarke
    eb, pos = welt.startpunkt()
    sx, sy = int(pos.x // K.TILE), int(pos.y // K.TILE)
    if not welt.ebene(eb).begehbar(sx, sy):
        fehler.append("Startmarke auf Ebene %d (%d,%d) ist nicht begehbar"
                      % (eb, sx, sy))
        return fehler

    gesehen = {(eb, sx, sy)}
    stapel = [(eb, sx, sy)]
    while stapel:
        idx, tx, ty = stapel.pop()
        e = welt.ebene(idx)
        nachbarn = [(idx, tx + 1, ty), (idx, tx - 1, ty),
                    (idx, tx, ty + 1), (idx, tx, ty - 1)]
        rel = e.daten(tx, ty).get("treppe")
        if rel is not None and 0 <= idx + rel < len(welt.ebenen):
            nachbarn.append((idx + rel, tx, ty))
        # Ein Loch ist kein Weg, aber man faellt hindurch - also zaehlt die
        # Ebene darunter als erreichbar.
        if e.loch(tx, ty) and idx > 0:
            nachbarn.append((idx - 1, tx, ty))
        for n in nachbarn:
            if n in gesehen:
                continue
            ni, nx, ny = n
            if not welt.ebene(ni).begehbar(nx, ny):
                continue
            gesehen.add(n)
            stapel.append(n)

    erreicht = {i for i, _, _ in gesehen}
    for e in welt.ebenen:
        if e.index not in erreicht:
            fehler.append("Ebene %d ist vom Start aus nicht erreichbar"
                          % e.index)
    return fehler
