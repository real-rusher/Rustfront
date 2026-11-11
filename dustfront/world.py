"""
DUSTFRONT - Welt
================

Die Welt besteht aus **Ebenen**. Eine Ebene ist ein Kachelgitter mit einer
Hoehe (0 = Boden, 1 = erste Etage, 2 = zweite, und so weiter). Jedes Wesen
gehoert zu genau einer Ebene, kollidiert nur mit deren Kacheln und sieht nur
deren Nachbarn.

Das ist der Punkt, an dem die meisten Projekte spaeter neu anfangen muessen.
Hier ist es von Anfang an drin: es gibt keinen Code, der davon ausgeht, dass
es nur eine Ebene gibt. Eine weitere Etage ist ein weiterer Texteintrag in der
Kartenliste, sonst nichts.

Karten sind Text. Ein Zeichen ist eine Kachel. Damit kann man eine Etage in
einem Editor tippen, und spaeter kann ein Tiled-Importeur genau dieselbe
Struktur erzeugen, ohne dass der Spielcode es merkt.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from pathlib import Path

import pygame

from . import config as K

# Zeichen -> Kachel. Alles, was hier nicht steht, wird zu Boden.
ZEICHEN = {
    " ": K.LEER,
    ".": K.BODEN,
    ",": K.GITTER,
    "#": K.WAND,
    "X": K.KISTE,
    "<": K.TREPPE_RUNTER,
    ">": K.TREPPE_HOCH,
    "o": K.LUKE,
    "^": K.AUFZUG_HOCH,
    "v": K.AUFZUG_RUNTER,
    "~": K.LEER,
    # Seit 0.34.6 (STAUBTAL): Gelaende und Kleinkram. Kleinbuchstaben und
    # Satzzeichen - Grossbuchstaben sind Marken.
    "r": K.FELS,
    "b": K.BROCKEN,
    "s": K.SANDSACK,
    "h": K.HOLZKISTE,
    "k": K.KAKTUS,
    "w": K.SCHROTT,
    ":": K.PISTE,
    ";": K.KIES,
    "_": K.PFLASTER,
    '"': K.GESTRUEPP,
    "=": K.DIELEN,
}

# Dekale werden in kleinen Flaechen abgelegt. Auf einer grossen Karte waere
# eine einzige transparente Flaeche pro Ebene mehrere hundert Megabyte gross.
DEKAL_KACHELN = 16
DEKAL_PIXEL = DEKAL_KACHELN * K.TILE


# ══════════════════════════════════════════════════════════════════
# Wie sehr eine Meldung den Zuschauer angeht
# ══════════════════════════════════════════════════════════════════
#
# Zwei kleine Funktionen, die beide Spielszenen benutzen - der
# Einzelspieler genauso wie das Gefecht. Sie stehen hier und nicht in
# einer der Szenen, weil sie sonst zweimal dastuenden und beim naechsten
# Mal auseinanderliefen.

def ruckel_wert(kraft: float, anlass: str = "", pos=None, ebene: int = 0,
                quelle=None, ich=None) -> float:
    """Wie stark ein gemeldeter Schlag **diesen** Zuschauer angeht.

    Ohne diese Rechnung bekam der Gastgeber das Ruckeln der ganzen Runde
    ab, weil bei ihm die Welt aller Spieler laeuft. Jetzt zaehlt, was
    einen selbst betrifft: der eigene Sturz, der eigene Treffer, die
    Explosion in der Naehe. Was ein anderer zwei Etagen hoeher tut,
    ergibt null.
    """
    r = K.RUCKELN
    kraft = float(kraft) * r["anlass"].get(anlass, 1.0)
    if kraft <= 0.0:
        return 0.0
    if ich is None or quelle is ich:
        return kraft
    if pos is None:
        return kraft * r["fremd"]
    if int(ebene) != int(getattr(ich, "ebene", ebene)):
        kraft *= r["fremde_ebene"]
        if kraft <= 0.0:
            return 0.0
    weg = pygame.Vector2(pos).distance_to(ich.pos)
    if weg >= r["reichweite"]:
        return 0.0
    return kraft * r["fremd"] * (1.0 - weg / r["reichweite"])


def blend_wert(pos, ebene: int, ich, welt=None) -> float:
    """Wie stark ein Blitz an dieser Stelle **diesen** Zuschauer blendet.

    Drei Fragen, in dieser Reihenfolge, weil jede die naechste erspart:

    1. Dieselbe Ebene? Ein Blitz eine Etage hoeher blendet nicht. Wie
       ueberall in diesem Spiel gehoert eine Wirkung zu einer Ebene.
    2. Freie Sicht? Steht eine Wand dazwischen, passiert nichts. Das ist
       der Griff, den man im Gefecht lernt: in Deckung gehen hilft.
    3. Wie nah, und schaut man hin? Nah blendet voll; wer weggedreht
       steht, bekommt nur einen Teil ab - ausser ganz nah (`rundum`):
       dort wirkt sie in jede Richtung (seit 0.32).
    4. Reicht es ueberhaupt? Unter `schwelle` gibt es **kein** Weiss -
       nur die Explosion mit dem Glitzer in der Welt, die jeder sieht.
       Gemeldet in 0.29: weiter weg oder weggedreht soll man sie sehen,
       aber nicht geblendet werden. Wer weggedreht steht, kommt darum
       nicht mehr ueber die Schwelle (`abgewandt` liegt darunter).

    Mannschaften spielen bewusst keine Rolle. Eine Blendgranate, die nur
    Gegner trifft, ist keine Entscheidung mehr, sondern ein Knopf.
    """
    if ich is None:
        return 0.0
    b = K.BLENDEN
    pos = pygame.Vector2(pos)
    if int(ebene) != int(getattr(ich, "ebene", ebene)):
        return 0.0
    weg = pos.distance_to(ich.pos)
    if weg >= b["weite"]:
        return 0.0
    deckung = 1.0
    if welt is not None:
        hinter = welt.deckung(ich.pos, pos, int(ebene))
        if hinter == "wand":
            return 0.0
        if hinter:
            # Seit 0.34.26: eine Kiste dazwischen schwaecht den Blitz nur
            # ab - er scheint darueber und daran vorbei.
            deckung = K.DECKUNG["blend_hindernis"]
    if weg <= b["nah"]:
        naehe = 1.0
    else:
        naehe = 1.0 - (weg - b["nah"]) / max(1.0, b["weite"] - b["nah"])
    ab = pos - ich.pos
    hin = 1.0
    if weg > b["rundum"] and ab.length_squared() > 1.0:
        richtung = math.degrees(math.atan2(ab.y, ab.x))
        delta = abs((richtung - getattr(ich, "winkel", 0.0) + 180) % 360 - 180)
        if delta > b["blickwinkel"] * 0.5:
            hin = b["abgewandt"]
    wert = max(0.0, min(1.0, naehe * hin * deckung))
    return wert if wert >= b["schwelle"] else 0.0


def blend_ton_wert(pos, ebene: int, ich) -> float:
    """Wie laut der Knall einer Blendgranate bei diesem Zuschauer ist.

    Die Entfernungsdaempfung aller Toene (klang_wert), dazu leiser mit der
    Entfernung und leiser, wer wegschaut - ausser ganz nah (`rundum`),
    dort wirkt die Granate in jede Richtung und klingt auch so.
    """
    b = K.BLENDEN
    grund = klang_wert(1.0, pos, ebene, ich)
    if grund <= 0.0 or ich is None or pos is None:
        return grund
    pos = pygame.Vector2(pos)
    weg = pos.distance_to(ich.pos)
    if weg <= b["rundum"]:
        return grund
    anteil = max(0.0, min(1.0, 1.0 - (weg - b["rundum"])
                          / max(1.0, b["ton_weite"] - b["rundum"])))
    faktor = b["ton_fern"] + (1.0 - b["ton_fern"]) * anteil
    ab = pos - ich.pos
    richtung = math.degrees(math.atan2(ab.y, ab.x))
    delta = abs((richtung - getattr(ich, "winkel", 0.0) + 180) % 360 - 180)
    if delta > b["blickwinkel"] * 0.5:
        faktor *= b["ton_abgewandt"]
    return max(min(grund, b["ton_mindest"]), grund * faktor)


def klang_wert(lautstaerke: float, pos=None, ebene: int = 0, ich=None) -> float:
    """Wie laut ein Ton bei diesem Zuschauer ankommt.

    Ohne Ort ist er ein Ton der eigenen Figur und bleibt, wie er ist.
    """
    a = K.AUDIO
    lautstaerke = float(lautstaerke)
    if pos is None or ich is None or lautstaerke <= 0.0:
        return lautstaerke
    if int(ebene) != int(getattr(ich, "ebene", ebene)):
        lautstaerke *= a["fremde_ebene"]
    weg = pygame.Vector2(pos).distance_to(ich.pos)
    if weg > a["nah"]:
        spanne = max(1.0, a["weit"] - a["nah"])
        lautstaerke *= max(0.0, 1.0 - (weg - a["nah"]) / spanne)
    return lautstaerke if lautstaerke >= a["leiseste"] else 0.0


_TAFELN: list = []


def _tafeln() -> tuple:
    """Je Kachelnummer 2 (sichtdicht), 1 (fest, aber durchsichtig) oder 0,
    als Tupel - fuer die Linien, die tausendfach je Bild verfolgt werden
    (seit 0.34.57): ein Nachschlagen je Kachel statt zweier. Die
    Kachelarten stehen fest; kommt eine dazu, wird neu gebaut (geprueft
    an der Zahl, nicht am groessten Schluessel - das kostete je Linie mehr
    als die Linie selbst)."""
    if not _TAFELN or _TAFELN[0] != len(K.KACHELN):
        n = max(K.KACHELN) + 1
        leer = K.KACHELN[K.LEER]
        art = tuple(2 if d["sicht"] else (1 if d["fest"] else 0)
                    for d in (K.KACHELN.get(i, leer) for i in range(n)))
        _TAFELN[:] = [len(K.KACHELN), art]
    return _TAFELN[1]


class Ebene:
    """Ein Kachelgitter auf einer Hoehe."""

    def __init__(self, breite: int, hoehe: int, index: int) -> None:
        self.breite, self.hoehe, self.index = breite, hoehe, index
        self.kacheln = [K.LEER] * (breite * hoehe)
        self.variante = [0] * (breite * hoehe)     # fuer abwechselnde Bodenbilder
        # Nur Kacheln mit Blut oder Brandflecken bekommen eine Flaeche. Eine
        # grosse Karte belegt so Speicher an den bespielten Stellen.
        self._dekale = {}
        self._marken: dict[str, list] = {}

    # ---- Aufbau ------------------------------------------------------
    @classmethod
    def aus_text(cls, zeilen: list[str], index: int) -> "Ebene":
        hoehe = len(zeilen)
        breite = max(len(z) for z in zeilen)
        e = cls(breite, hoehe, index)
        for ty, zeile in enumerate(zeilen):
            for tx in range(breite):
                z = zeile[tx] if tx < len(zeile) else " "
                # Grossbuchstaben ausser X sind **Marken**: sie sagen der
                # Spielart, wo etwas hingehoert - ein Kreis, ein
                # Einstiegsplatz -, und werden selbst zu Boden. So steht
                # in der Kartendatei, wo die Punkte liegen, und nicht in
                # einer zweiten Datei daneben, die man vergisst.
                if z.isalpha() and z.isupper() and z not in ZEICHEN:
                    e.marken.setdefault(z, []).append(
                        pygame.Vector2(tx * K.TILE + K.TILE / 2,
                                       ty * K.TILE + K.TILE / 2))
                    z = "."
                e.setzen(tx, ty, ZEICHEN.get(z, K.BODEN))
                # gestreute Auswahl, sonst sieht man ein Muster im Boden
                e.variante[ty * breite + tx] = ((tx * 73856093) ^ (ty * 19349663)) % 4
        e._marken_boden()
        return e

    def _marken_boden(self) -> None:
        """Eine Marke liegt auf dem Boden, der um sie herum ist.

        Bis 0.34 wurde jede Marke zu Sand. Seit es Pisten und Pflaster
        gibt (0.34.6), lag dann mitten auf dem Platz um einen Kreis ein
        einzelnes Sandfeld - und auf jeder Piste mit Spawnstelle ein
        Fleck. Jetzt: die Bodenart, die unter den vier Nachbarn am
        haeufigsten ist; ohne begehbaren Nachbarn bleibt es Sand."""
        for stellen in self._marken.values():
            for p in stellen:
                tx, ty = int(p.x // K.TILE), int(p.y // K.TILE)
                zaehlen = {}
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    k = self.kachel(tx + dx, ty + dy)
                    d = K.KACHELN[k]
                    if k != K.LEER and not d["fest"] and d.get("treppe") is None:
                        zaehlen[k] = zaehlen.get(k, 0) + 1
                if zaehlen:
                    self.setzen(tx, ty, max(sorted(zaehlen), key=zaehlen.get))

    @property
    def marken(self) -> dict:
        """Benannte Stellen dieser Ebene, aus den Grossbuchstaben."""
        return self._marken

    @property
    def dekale(self):
        """Die verwendeten Kachelflaechen mit Blut- und Brandflecken.

        Leeres Dict heisst: es liegt noch keiner. Der Renderer zeichnet
        nur die kleinen Ausschnitte, die im aktuellen Bild liegen.
        """
        return self._dekale

    def setzen(self, tx: int, ty: int, kachel: int) -> None:
        if 0 <= tx < self.breite and 0 <= ty < self.hoehe:
            self.kacheln[ty * self.breite + tx] = kachel

    # ---- Abfragen ----------------------------------------------------
    def kachel(self, tx: int, ty: int) -> int:
        if 0 <= tx < self.breite and 0 <= ty < self.hoehe:
            return self.kacheln[ty * self.breite + tx]
        return K.LEER

    def daten(self, tx: int, ty: int) -> dict:
        return K.KACHELN[self.kachel(tx, ty)]

    def fest(self, tx: int, ty: int) -> bool:
        return K.KACHELN[self.kachel(tx, ty)]["fest"]

    def sichtdicht(self, tx: int, ty: int) -> bool:
        return K.KACHELN[self.kachel(tx, ty)]["sicht"]

    def fest_an(self, x: float, y: float) -> bool:
        return self.fest(int(x // K.TILE), int(y // K.TILE))

    def loch(self, tx: int, ty: int) -> bool:
        if not (0 <= tx < self.breite and 0 <= ty < self.hoehe):
            return False
        # Direkt in die Kacheln (seit 0.34.75): dieselbe Antwort ohne den
        # Umweg ueber kachel() - die Frage kommt hunderttausendfach je Minute.
        return K.KACHELN[self.kacheln[ty * self.breite + tx]].get("loch", False)

    def begehbar(self, tx: int, ty: int) -> bool:
        return not self.fest(tx, ty) and self.kachel(tx, ty) != K.LEER

    @property
    def pixel_breite(self) -> int:
        return self.breite * K.TILE

    @property
    def pixel_hoehe(self) -> int:
        return self.hoehe * K.TILE

    def dekal(self, bild: pygame.Surface, x: float, y: float) -> None:
        """Brandfleck, Blut, Einschlag. Bleibt liegen, kostet nichts."""
        links = int(x - bild.get_width() / 2)
        oben = int(y - bild.get_height() / 2)
        rechts = links + bild.get_width()
        unten = oben + bild.get_height()
        kachel_links = max(0, links // DEKAL_PIXEL)
        kachel_rechts = min(self.pixel_breite - 1, rechts - 1) // DEKAL_PIXEL
        kachel_oben = max(0, oben // DEKAL_PIXEL)
        kachel_unten = min(self.pixel_hoehe - 1, unten - 1) // DEKAL_PIXEL
        for ky in range(kachel_oben, kachel_unten + 1):
            for kx in range(kachel_links, kachel_rechts + 1):
                schluessel = (kx, ky)
                flaeche = self._dekale.get(schluessel)
                if flaeche is None:
                    flaeche = pygame.Surface((DEKAL_PIXEL, DEKAL_PIXEL),
                                             pygame.SRCALPHA)
                    self._dekale[schluessel] = flaeche
                links_kachel, oben_kachel = kx * DEKAL_PIXEL, ky * DEKAL_PIXEL
                x0, y0 = max(links, links_kachel), max(oben, oben_kachel)
                x1 = min(rechts, links_kachel + DEKAL_PIXEL)
                y1 = min(unten, oben_kachel + DEKAL_PIXEL)
                quelle = pygame.Rect(x0 - links, y0 - oben,
                                     x1 - x0, y1 - y0)
                flaeche.blit(bild, (x0 - links_kachel, y0 - oben_kachel), quelle)


_LOCH = ("loch",)          # Marke in Welt._frei_tafel: ein Loch


class Welt:
    """Haelt die Ebenen und alle Wesen."""

    ZELLE = 48          # Rastergroesse der Nachbarschaftssuche

    def __init__(self, ebenen: list[Ebene], satz: str = "") -> None:
        self.ebenen = ebenen
        # Welcher Kachelsatz gilt. Leer ist der Standard; "wueste" tauscht
        # Boden, Wand und Kiste gegen Sand, Fels und Fass. Steht als
        # `satz:` im Kopf der Kartendatei.
        self.satz = satz
        self.schneespuren: list[list[float]] = []
        self.wesen: list = []
        self.neue: list = []
        self.partikel: list = []
        # Der Flammenstrom (seit 0.34.95, K.FLAMME, flammen_ausstossen): je
        # Fleck eine Liste statt eines Objekts, es sind bei einem
        # Flammenwerfer schnell zweihundert. Mit eigener Uhr, weil `zeit`
        # beim Gast steht - die Flammen sieht er trotzdem.
        self.flammen: list = []
        self.flammen_zeit = 0.0
        self._raster: dict[tuple, list] = {}
        self.zeit = 0.0
        self.held = None                 # setzt die Spielszene
        self.muendungen: list = []       # kurze Lichtblitze am Lauf
        # Rauchwolken. Eine eigene Liste und keine Wesen: sie stossen
        # niemanden, sind nicht zu treffen und werden nicht gedreht - sie
        # liegen nur auf ihrer Ebene und nehmen die Sicht.
        self.rauch: list = []
        # Brandflaechen. Eigene Liste aus demselben Grund wie der Rauch:
        # sie sind keine Wesen, stossen niemanden und sind nicht zu
        # treffen - sie liegen auf ihrer Ebene und nehmen den Ort.
        self.feuer: list = []
        # Nagelfelder (seit 0.34.65, der Nagelstreuer): aus demselben Grund
        # eine eigene Liste.
        self.naegel: list = []
        # Gaswolken (seit 0.34.67, die Gasgranate).
        self.gas: list = []
        # Strahlen und Blitze der Chor-Waffen (seit 0.34.68): je
        # [Punkte, Ebene, Art, Rest, Dauer, Saat]. Nur Bild.
        self.entladungen: list = []
        # Reine Rueckmeldung: Staubringe beim Aufsetzen und kurze
        # Aufschriften ueber aufgesammelter Beute. Beides entscheidet
        # nichts, es sagt nur, dass etwas passiert ist.
        self.ringe: list = []
        self.aufschriften: list = []
        # Feuerbaelle der Panzerkanone und wer nach dem Rammen noch fliegt
        # (seit 0.34.59). Reine Rueckmeldung wie die Ringe: beim Gast
        # entstehen sie aus derselben Meldung (explosion, leichenflug).
        self.feuerbaelle: list = []
        self.flugleichen: list = []
        # Kurze helle Blitze bei Explosionen (seit 0.34.64): [Ort, Ebene,
        # Radius, Rest, Dauer]. Beim Gast aus derselben Explosion.
        self.lichtblitze: list = []
        # Was groesser ist als eine Zelle des Rasters (Panzer, Panzerwagen):
        # steht nicht in den Zellen, sondern hier, und `nahe` fragt es
        # einzeln - sonst fehlte ein Panzer, dessen Mitte zwei Zellen weg
        # liegt, waehrend sein Heck schon im Kreis ist.
        self._gross: list = []

    # ---- Rueckmeldungen an die Spielszene ------------------------------
    # Standardmaessig passiert nichts. Die Szene haengt sich hier ein, damit
    # Wesen Kameraruckeln oder Dekale ausloesen koennen, ohne den Renderer zu
    # kennen.
    def ruckeln(self, kraft: float, anlass: str = "", pos=None,
                ebene: int = 0, quelle=None) -> None:
        """Ein Schlag auf die Kamera - mit Anlass, Ort und Absender.

        Die drei zusaetzlichen Angaben sind der ganze Unterschied zu
        frueher. Ohne sie musste die Szene jeden Schlag nehmen, wie er
        kam; der Gastgeber rechnet aber die Welt **aller** Spieler und
        bekam deshalb jeden Schuss, jeden Treffer und jede Granate der
        ganzen Runde auf seine eigene Kamera - dauerhaft und ohne Pause,
        waehrend bei den Gaesten gar nichts ankam. Mit Anlass, Ort und
        Absender entscheidet nicht mehr der Ausloeser, sondern der
        Zuschauer: was mich nichts angeht, ruckelt bei mir auch nicht.
        """
        pass

    def kurz_langsam(self, sekunden: float) -> None:
        pass

    def blutfleck(self, pos, ebene: int, radius: float, art: str = "mensch",
                  variante: int = 0) -> None:
        """Ein Fleck in den Boden. `art` ist das Blut (K.BLUT), `variante`
        dreht und spiegelt die Form, damit nicht jeder Fleck gleich aussieht.
        Die Szene haengt sich hier ein."""
        pass

    def tod(self, pos, ebene: int, blut: str, radius: float, fall_winkel: float) -> None:
        """Ein Wesen ist gestorben (entities.tod_zeigen): Spritzer, ein Fleck
        im Blut seiner Art (K.BLUT) und der Todeslaut. Beim Gastgeber haengt
        sich das Gefecht davor und meldet es den Gaesten (Meldung "d") - die
        rufen dann genau diese Funktion in ihrer eigenen Welt auf.

        0.34.33 hatte hier noch eine Leiche, die umfiel und eine Weile lag;
        seit 0.34.34 nicht mehr (gemeldet: "Der Fleck reicht, Animation muss
        nicht sein. Ein Death Sound reicht mir.")."""
        from .entities import wolke
        b = K.BLUT.get(blut, K.BLUT["mensch"])
        if blut not in K.BLUT:
            blut = "mensch"
        t = K.TOD
        wolke(self, pos, t["spritzer"], 170, 0.6, b["spritzer"], ebene,
              2 if radius >= 12 else 1, "blut", streuung=200.0, richtung=fall_winkel)
        # Die Form aus dem Ort statt aus dem Zufall: so liegt derselbe Fleck
        # beim Gast genauso da wie beim Gastgeber.
        variante = int(abs(pos.x) * 7 + abs(pos.y) * 13) % 8
        self.blutfleck(pos, ebene, radius * b["groesse"], blut, variante)
        self.klang("tod", t["laut_gross"] if radius >= 14 else t["laut"], pos, ebene)

    def klang(self, name: str, lautstaerke: float = 1.0, pos=None,
              ebene: int | None = None) -> None:
        """Ein Ton. Mit Ort wird er nach Entfernung und Ebene abgesenkt.

        Ohne Ort ist er ein Ton der eigenen Figur und damit voll zu
        hoeren - ein Nachladen zum Beispiel. Mit Ort gehoert er in die
        Welt, und dann soll ein Schuss am anderen Ende der Karte auch so
        klingen.
        """
        pass

    def brandfleck(self, pos, ebene: int, radius: float) -> None:
        pass

    def entladung(self, punkte, ebene: int, art: str = "blitz") -> None:
        """Ein Strahl (Spule) oder Blitz (Kettenblitz, Kugelblitz) zwischen
        den Punkten, fuer einen Augenblick (seit 0.34.68). Beim Gastgeber
        haengt sich das Gefecht davor und meldet es den Gaesten."""
        dauer = K.ENTLADUNG["dauer"].get(art, 0.2)
        self.entladungen.append([[pygame.Vector2(p) for p in punkte], int(ebene), art,
                                 dauer, dauer, int(abs(punkte[0][0]) * 13 + abs(punkte[-1][1]) * 7)])

    def laerm(self, pos, ebene: int, quelle=None, weite: float = 600.0) -> None:
        """Lauter Laerm an dieser Stelle (seit 0.34.66: Kettensaege, spaeter
        der Knaller). Wer ihn hoert, entscheidet das Gefecht (Bots)."""
        pass

    def bild_dekal(self, name: str, pos, ebene: int, winkel: float = 0.0) -> None:
        """Ein kleines Bild bleibt am Boden (seit 0.34.66: Naegel in der
        Wand). Die Szene haengt sich hier ein, wie beim Brandfleck."""
        pass

    def krater(self, pos, ebene: int, radius: float, saat: int) -> None:
        """Ein unregelmaessiger Krater im Boden (seit 0.34.59, Einschlag der
        Panzerkanone). Die Szene haengt sich hier ein, wie beim Brandfleck."""
        pass

    def leichenflug(self, pos, ebene: int, bild: str, winkel: float, tempo,
                    dauer: float, dreh: float, blut: str, radius: float) -> None:
        """Wer beim Rammen stirbt, fliegt noch ein Stueck (seit 0.34.59).
        Beim Gastgeber haengt sich das Gefecht davor und meldet es den
        Gaesten - die rufen dann genau diese Funktion auf."""
        from .entities import Flugleiche
        self.flugleichen.append(Flugleiche(pos, ebene, bild, winkel, tempo,
                                           dauer, dreh, blut, radius))

    def blitz(self, pos, ebene: int, von=None):
        """Hier hat es geblitzt. Wer davon geblendet wird, entscheidet
        jeder Zuschauer fuer sich - die Szene haengt sich hier ein.

        `von` ist der Werfer. Gibt die Szene True zurueck, hat sie den Ton
        selbst gespielt (Spielerkosmetik), und der gewoehnliche Knall
        bleibt aus."""
        return False

    # ---- Wirkungen, die jeder sehen und hoeren muss ---------------------
    #
    # Was hier steht, ist bewusst **nicht** ueber die Wesen verstreut.
    # Eine Explosion ist zwei Dinge auf einmal: Schaden, den nur der
    # Gastgeber rechnen darf, und ein Auftritt samt Ton, den jeder
    # bekommen muss. Frueher lagen beide Haelften zusammen in
    # `Granate.zuenden`, und weil ein Gast keine Granate simuliert, sah
    # und hoerte er von einer Explosion **gar nichts**: das Bild der
    # Granate verschwand einfach, ohne Knall, ohne Funken, ohne
    # Brandfleck. Gemessen an einer Runde ueber echte Steckdosen -
    # Gastgeber 5 Partikel und zwei Toene, Gast 0 und keinen.
    #
    # Getrennt gehen beide Haelften ihren eigenen Weg: der Schaden bleibt
    # beim Gastgeber, und der Auftritt geht als Meldung an alle und wird
    # dort mit genau derselben Funktion nachgespielt. Auseinanderlaufen
    # kann das nicht mehr - es ist derselbe Code.

    def explosion(self, pos, ebene: int, radius: float,
                  art: str = "spreng", von=None) -> None:
        """Wie eine Wurfwaffe aussieht und klingt, wenn sie wirkt.

        `art` statt eines Wahrheitswerts: es gibt nicht mehr nur "zuendet
        oder qualmt". Mit dem Molotow kam "zerbricht und brennt" dazu, und
        der naechste Wurf kommt bestimmt.
        """
        from .entities import wolke
        pos = pygame.Vector2(pos)
        if art == "rauch":
            wolke(self, pos, 12, 90, 0.6, K.RAUCH["toene"][0], ebene, 2)
            self.klang("smoke_grenade", 0.8, pos, ebene)
            return
        if art == "blend":
            b = K.BLENDEN
            # In der Welt eine Explosion wie bei der Granate - aber weiss
            # statt Feuer, und **ohne Splitter**: kein Rauchpilz, kein
            # Brandfleck, kein Schaden. Dazu Glitzer, der langsamer fliegt
            # und laenger leuchtet. Das ist alles, was sieht, wer weit weg
            # steht oder weggedreht - das Weiss im Bild bekommt nur, wer
            # wirklich getroffen ist (blend_wert, `schwelle`). So gemeldet:
            # "weiter weg bzw. wegschauen: nur Glitzer und Funken mit einer
            # Explosion wie eher von der Granate, ohne Fragmente".
            wolke(self, pos, 24, 300, b["funke_dauer"] * 1.8, (255, 255, 248),
                  ebene, 2, "funke")
            wolke(self, pos, 16, 120, b["glitzer_dauer"], (255, 232, 160),
                  ebene, 1, "funke", reibung=1.6)
            wolke(self, pos, 12, 90, b["glitzer_dauer"] * 1.2, (196, 222, 255),
                  ebene, 1, "funke", reibung=1.4)
            wolke(self, pos, 6, 50, 0.7, K.C_MUTED, ebene, 2, "staub")
            self.aufschlagring(pos, ebene, b["ring"])
            self.ruckeln(b["kamera"], "explosion", pos, ebene)
            if not self.blitz(pos, ebene, von):
                self.klang(K.skin("blend_knall"), 1.0, pos, ebene)
            return
        if art == "feuer":
            # Kein Knall und kein Kameraschlag: eine Flasche zerbricht,
            # sie explodiert nicht. Was man hoert, ist Glas und Auflodern.
            f = K.FEUER
            wolke(self, pos, 22, 210, 0.7, f["toene"][2], ebene, 2, "funke")
            wolke(self, pos, 10, 90, 0.5, f["toene"][1], ebene, 1, "funke")
            self.klang("molotov_glass", 0.9, pos, ebene)
            self.klang("molotov_whoosh", 0.28, pos, ebene)
            return
        if art == "plasma":
            # Der Kugelblitz platzt (seit 0.34.68): tuerkis statt Feuer, ein
            # kurzer Schleier, Blitze nach aussen (Waffenpaket).
            e = K.ENTLADUNG
            wolke(self, pos, 30, 300, 0.5, e["tuerkis"], ebene, 2, "funke")
            wolke(self, pos, 16, 120, 0.9, e["kern"], ebene, 1, "funke", reibung=1.6)
            wolke(self, pos, 10, 60, 0.8, (60, 140, 150), ebene, 3, "staub")
            for i in range(6):
                ende = pos + pygame.Vector2(radius, 0).rotate(i * 60 + pos.x % 60)
                self.entladung([pos, ende], ebene, "blitz")
            self.aufschlagring(pos, ebene, 1.2)
            self.ruckeln(4.0, "explosion", pos, ebene)
            self.klang("plasma", 0.8, pos, ebene)
            return
        if art == "nagel":
            # Ein Nagel des Naglers bleibt in der Wand stecken (seit
            # 0.34.66). Hier ist `radius` die Richtung, in der er flog.
            self.bild_dekal("nagel_steckt", pos, ebene, radius)
            self.klang("nagel_wand", 0.35, pos, ebene)
            return
        if art == "boden":
            # Der Bodenschlag des Hammers (seit 0.34.66): Staub, ein Ring,
            # Risse (ein kleiner Krater) und ein dumpfer Schlag.
            wolke(self, pos, 22, 170, 0.6, K.C_MUTED_DK, ebene, 2, "staub")
            wolke(self, pos, 10, 220, 0.35, (122, 86, 46), ebene, 1, "staub",
                  reibung=2.0)
            self.aufschlagring(pos, ebene, 1.4)
            self.krater(pos, ebene, radius * 0.25, int(abs(pos.x) * 7 + abs(pos.y) * 13))
            self.ruckeln(5.0, "explosion", pos, ebene)
            self.klang("hammer_boden", 1.0, pos, ebene)
            return
        if art in ("flak", "luft_kiste", "luft_mensch", "fallschirm_riss", "absturz"):
            self._explosion_luft(pos, ebene, radius, art)
            return
        if art == "emp":
            # Die EMP-Granate (seit 0.34.65): kein Feuer, kein Krater - ein
            # blauer Kranz, der den Kreis zeigt, in dem Fahrzeuge ausfallen.
            for i in range(28):
                winkel = i * 360.0 / 28
                p = pos + pygame.Vector2(radius * 0.9, 0).rotate(winkel)
                wolke(self, p, 1, 40, 0.5, (150, 220, 255), ebene, 1, "funke")
            wolke(self, pos, 20, 260, 0.45, (200, 240, 255), ebene, 2, "funke")
            wolke(self, pos, 10, 120, 0.8, (90, 170, 230), ebene, 1, "funke")
            self.aufschlagring(pos, ebene, 1.2)
            self.klang("emp", 0.8, pos, ebene)
            return
        if art in ("panzer", "c4", "spreng", "klein", "feuer"):
            self.lichtblitz(pos, ebene, max(radius, 40.0 if art != "klein" else 20.0)
                            * (1.6 if art in ("panzer", "c4") else 1.0))
        if art == "klein":
            # Die kleinen Raketen des Raketenbuendels (seit 0.34.64): ein
            # heller Blitz, ein Kranz Funken, wenig Rauch, ein kleiner Ring -
            # sechs davon hintereinander sollen sechs Schlaege sein.
            wolke(self, pos, 18, 300, 0.4, (255, 220, 150), ebene, 2, "funke")
            wolke(self, pos, 8, 110, 0.6, K.C_MUTED_DK, ebene, 2, "staub")
            self.aufschlagring(pos, ebene, 0.7)
            self.brandfleck(pos, ebene, radius * 0.6)
            self.ruckeln(2.5, "explosion", pos, ebene)
            self.klang("granate", 0.6, pos, ebene)
            return
        if art == "panzer":
            # Der Einschlag der Panzerkanone (seit 0.34.59): groesser als
            # Granate und C4 - Feuerball aus versetzten Glutballen, danach
            # dunkler Rauch, Funken, Staub, Holzsplitter und ein Krater, der
            # nicht rund ist. Die Form kommt aus dem Ort, damit der Gast
            # dasselbe sieht.
            from .entities import Feuerball
            f = K.FEUERBALL
            saat = int(abs(pos.x) * 7 + abs(pos.y) * 13)
            self.feuerbaelle.append(Feuerball(pos, ebene, saat))
            wolke(self, pos, f["funken"], 420, 0.8, (255, 224, 164), ebene, 3, "funke")
            wolke(self, pos, 24, 200, 1.1, K.C_MUTED_DK, ebene, 2, "staub")
            wolke(self, pos, 20, 240, 1.0, (122, 86, 46), ebene, 2, "staub",
                  reibung=2.0)
            self.krater(pos, ebene, f["krater"], saat)
            self.aufschlagring(pos, ebene, 1.4)
            self.ruckeln(f["kamera"], "explosion", pos, ebene)
            self.klang("panzer_einschlag", 1.0, pos, ebene)
            return
        if art == "c4":
            wolke(self, pos, 42, 390, 0.75, (255, 224, 164), ebene, 2,
                  "funke")
            wolke(self, pos, 30, 190, 1.1, K.C_MUTED_DK, ebene, 2, "staub")
            self.aufschlagring(pos, ebene, 1.6)
            self.ruckeln(13.0, "explosion", pos, ebene)
            self.klang("c4_explosion", 1.0, pos, ebene)
            return
        wolke(self, pos, 26, 340, 0.5, (255, 212, 140), ebene, 2, "funke")
        wolke(self, pos, 18, 150, 0.9, K.C_MUTED_DK, ebene, 2, "staub")
        self.brandfleck(pos, ebene, radius)
        self.ruckeln(K.WAFFEN["granate"]["kamera"], "explosion", pos, ebene)
        self.klang("granate", 1.0, pos, ebene)

    def _explosion_luft(self, pos, ebene: int, radius: float, art: str) -> None:
        """Was in der Luft platzt oder reisst (seit 0.34.118). `pos` ist der
        Ort im Bild, nicht am Boden. Bei "fallschirm_riss" ist `radius` die
        Seite (0 oder 1), damit die Fetzen in den Farben des Schirms fliegen."""
        from .entities import wolke
        weiss = (232, 226, 210)
        kombi = K.TEAMS["kombi"][int(radius)] if art == "fallschirm_riss" and 0 <= int(radius) < 2 else None
        tuch = kombi["rumpf"] if kombi else (200, 70, 50)
        if art == "flak":
            # Eine Flakwolke wie im zweiten Weltkrieg: ein heller Kern, der
            # gleich verglueht, eine dunkle, aufquellende Rauchwolke, die eine
            # Weile stehen bleibt, und ein Kranz Splitterfunken.
            self.lichtblitz(pos, ebene, 58.0)
            wolke(self, pos, 5, 60, 0.18, (255, 238, 196), ebene, 5, "funke", reibung=3.0)
            wolke(self, pos, 14, 90, 2.6, (24, 22, 20), ebene, 10, "flakrauch", reibung=2.2)
            wolke(self, pos, 10, 46, 3.2, (62, 58, 54), ebene, 14, "flakrauch", reibung=1.7)
            wolke(self, pos, 5, 20, 3.4, (96, 90, 84), ebene, 16, "flakrauch", reibung=1.5)
            wolke(self, pos, 20, 440, 0.3, (255, 190, 110), ebene, 1, "funke", reibung=2.5)
            wolke(self, pos, 6, 190, 0.8, (255, 140, 60), ebene, 1, "funke", reibung=2.0)
            self.ruckeln(1.2, "explosion", pos, ebene)
            self.klang("flak_burst", 0.9, pos, ebene)
            return
        if art in ("luft_kiste", "luft_mensch"):
            # Was am Schirm hing, zerplatzt: Splitter bzw. Blut, Fetzen vom
            # Schirm, eine kleine dunkle Wolke.
            self.lichtblitz(pos, ebene, 40.0)
            wolke(self, pos, 5, 60, 0.15, (255, 238, 196), ebene, 4, "funke", reibung=3.0)
            if art == "luft_kiste":
                wolke(self, pos, 16, 220, 1.1, (140, 104, 64), ebene, 2, "splitter", reibung=1.5)
                wolke(self, pos, 8, 130, 1.5, (86, 104, 62), ebene, 2, "splitter", reibung=1.4)
            else:
                wolke(self, pos, 16, 200, 1.0, K.C_BLUT, ebene, 2, "blut", reibung=1.6)
            wolke(self, pos, 12, 75, 2.4, weiss, ebene, 3, "fetzen", reibung=0.9)
            wolke(self, pos, 8, 75, 2.4, tuch, ebene, 3, "fetzen", reibung=0.9)
            wolke(self, pos, 8, 50, 2.2, (40, 36, 34), ebene, 8, "flakrauch", reibung=2.0)
            self.ruckeln(1.0, "explosion", pos, ebene)
            self.klang("flak_burst", 0.6, pos, ebene)
            return
        if art == "fallschirm_riss":
            # Der Schirm reisst: Bahnen und Fetzen fliegen auseinander und
            # taumeln hinunter.
            wolke(self, pos, 14, 120, 2.6, weiss, ebene, 4, "fetzen", reibung=0.8)
            wolke(self, pos, 14, 120, 2.6, tuch, ebene, 4, "fetzen", reibung=0.8)
            wolke(self, pos, 8, 50, 1.6, (40, 36, 34), ebene, 4, "flakrauch", reibung=2.0)
            self.klang("fallschirm_riss", 0.8, pos, ebene)
            return
        # "absturz": der Aufschlag eines Fahrzeugs ohne Schirm.
        wolke(self, pos, 44, 300, 1.3, K.C_SAND_KORN, ebene, 2, "staub", reibung=2.2)
        wolke(self, pos, 16, 340, 0.7, (122, 86, 46), ebene, 3, "staub", reibung=2.0)
        wolke(self, pos, 18, 360, 0.5, (255, 214, 140), ebene, 1, "funke", reibung=2.5)
        self.aufschlagring(pos, ebene, 1.8)
        self.ruckeln(9.0, "explosion", pos, ebene)
        self.klang("absturz", 1.0, pos, ebene)

    def lichtblitz(self, pos, ebene: int, radius: float) -> None:
        """Ein kurzer heller Blitz (K.LICHTBLITZ), gezeichnet additiv
        ueber dem Boden - jede Explosion soll man auf einen Blick sehen."""
        lb = K.LICHTBLITZ
        r = max(lb["mindestens"], min(lb["hoechstens"], radius * lb["je_radius"]))
        self.lichtblitze.append([pygame.Vector2(pos), int(ebene), r, lb["dauer"], lb["dauer"]])

    def flammen_ausstossen(self, pos, winkel: float, ebene: int, daten: dict) -> None:
        """Ein Zug des Flammenwerfers: so viele Flecken, wie in einen Takt
        passen (K.FLAMME). Jeder ist schon ein Stueck des Takts unterwegs,
        sonst kaemen sie in Buendeln aus der Duese statt als Strom.

        Ein Fleck ist [x, y, ux, uy, v0, weg_max, geburt, r_max, dauer,
        ebene]. Wo er gerade ist, folgt aus seinem Alter (flamme_jetzt) -
        so muss niemand ihn je Schritt bewegen, und gezeichnet wird er
        genau zwischen zwei Schritten. Die Wand sucht er beim Ausstossen:
        dort bleibt er stehen."""
        from .entities import RND
        f = K.FLAMME
        takt = daten.get("takt", 0.06)
        reib = f["reibung"]
        mitte_dauer = (f["dauer"][0] + f["dauer"][1]) / 2.0
        # So schnell, dass ein Fleck in seiner Zeit die Reichweite schafft:
        # Weg = v / reibung * (1 - e^(-reibung * t)).
        v0 = (daten.get("reichweite", 130.0) * f["weite"] * reib
              / max(0.05, 1.0 - math.exp(-reib * mitte_dauer)))
        # Gleich viele Flecken je Pixel wie im Paket (dort 180 je Sekunde
        # bei 170 px/s): ein laengerer Strom braucht mehr davon, sonst
        # wird er duenn und dunkel.
        n = f["dichte"] * v0 * takt
        anzahl = int(n) + (1 if RND.random() < n - int(n) else 0)
        jetzt = self.flammen_zeit
        start = pygame.Vector2(pos)
        for _ in range(anzahl):
            a = winkel + RND.uniform(-f["streuung"] / 2, f["streuung"] / 2)
            u = pygame.Vector2(1, 0).rotate(a)
            v = v0 * RND.uniform(1.0 - f["tempo_streuung"], 1.0 + f["tempo_streuung"])
            weit = v / reib
            halt = self.strahl(start, u, weit, ebene)
            self.flammen.append([start.x, start.y, u.x, u.y, v, halt.distance_to(start),
                                 jetzt - RND.uniform(0.0, takt), RND.uniform(*f["r_max"]),
                                 RND.uniform(*f["dauer"]), ebene])
        if len(self.flammen) > f["hoechstens"]:
            del self.flammen[:len(self.flammen) - f["hoechstens"]]

    def flamme_jetzt(self, b: list, zeit: float):
        """(x, y, r, hitze) eines Flecks zur Zeit `zeit`, hitze <= 0: aus."""
        f = K.FLAMME
        alter = max(0.0, zeit - b[6])
        reib = f["reibung"]
        weg = min(b[5], b[4] / reib * (1.0 - math.exp(-reib * alter)))
        return (b[0] + b[2] * weg, b[1] + b[3] * weg,
                min(b[7], f["r_start"] + f["r_wachsen"] * alter), 1.0 - alter / b[8])

    def _flammen_schritt(self, dt: float) -> None:
        jetzt = self.flammen_zeit
        if any(jetzt - b[6] >= b[8] for b in self.flammen):
            self.flammen = [b for b in self.flammen if jetzt - b[6] < b[8]]

    def schussknall(self, pos, winkel: float, ebene: int, waffe: str,
                    quelle=None) -> None:
        """Muendungsblitz, Funken und Knall eines Schusses.

        Auch das sah ein Gast bisher nicht: der Gastgeber schickt die
        Geschosse, aber nicht das, was am Lauf passiert. Es blitzte
        nirgends, und zu hoeren war im ganzen Mehrspieler kein einziger
        Schuss ausser dem eigenen.
        """
        from .entities import RND, wolke
        pos = pygame.Vector2(pos)
        daten = K.WAFFEN.get(waffe) or K.FAHRZEUG_WAFFEN.get(waffe, {})
        if daten.get("flamme"):
            # Der Flammenwerfer: kein Blitz, ein Strom von Hitzeflecken, die
            # zu einer Feuerzunge verschmelzen (seit 0.34.95 wie im Paket,
            # K.FLAMME; vorher Funken).
            self.flammen_ausstossen(pos, winkel, ebene, daten)
            if RND.random() < 0.12:
                self.klang("flammenwerfer", 0.5, pos, ebene)
            return
        gross = daten.get("muendung", 1.0)
        self.muendung(pos, winkel, ebene, gross)
        wolke(self, pos, int(3 * gross), 120 * gross, 0.12 * gross, (255, 226, 160),
              ebene, 1, "funke", 34, winkel, 8.0)
        if waffe == "kanone":
            # Die Druckwelle wirbelt Sand am Boden vor der Muendung auf - und
            # der liegt unter den Fahrzeugen, nicht in ihrer Mitte (gemeldet
            # im Paket). "bodenstaub" zeichnet der Renderer vor den Wesen.
            boden = pos - pygame.Vector2(K.PANZER["muendung"] * 0.15, 0).rotate(winkel)
            wolke(self, boden, 26, 170, 0.9, K.C_SAND_KORN, ebene, 2, "bodenstaub",
                  150, winkel)
            wolke(self, boden, 10, 90, 1.1, K.C_SAND, ebene, 2, "bodenstaub",
                  300, winkel + 180)
        self.ruckeln(daten.get("kamera", 1.0), "schuss", pos, ebene, quelle)
        if waffe == "lmg":
            klang = ("lmg_salve" if getattr(quelle, "modus", "dauer") == "salve"
                     else "lmg_dauer")
            # Die Salvenaufnahme ist schon eine ganze Salve (rund eine
            # Sekunde). Je Geschoss abgespielt lagen drei davon fast
            # gleichzeitig uebereinander - also nur beim ersten Schuss.
            # Der erste ist der, nach dem noch alle uebrigen ausstehen.
            salve = K.WAFFEN["lmg"]["modus_daten"]["salve"].get("salve", 1)
            if (klang == "lmg_salve"
                    and getattr(quelle, "salve_rest", salve - 1) < salve - 1):
                return
        else:
            # Eine Waffe aus dem Waffenpaket (seit 0.34.62) sagt selbst, wie
            # sie klingt - bis es eigene Aufnahmen gibt, wie eine verwandte.
            klang = daten.get("klang") or (
                "schuss_schrot" if waffe == "schrot" else "schuss_" + waffe)
        self.klang(klang, K.AUDIO["schuss"], pos, ebene)

    def raketenstart(self, pos, winkel: float, ebene: int, quelle=None,
                     ziel=None) -> None:
        """Der Abschuss einer Rakete: Rauch, Feuerstrahl, Knall.

        Wie schussknall eine Sache der Welt und nicht des Wesens, damit
        ein Gast sie mit demselben Code nachspielen kann.
        """
        from .entities import wolke
        pos = pygame.Vector2(pos)
        self.muendung(pos, winkel, ebene)
        # Der Ruecksstrahl nach hinten: das ist es, was einen
        # Raketenwerfer von einem Gewehr unterscheidet.
        hinten = (winkel + 180) % 360
        wolke(self, pos, 16, 280, 0.45, (246, 196, 120), ebene, 2, "funke",
              44, hinten, 6.0)
        wolke(self, pos, 12, 130, 0.9, K.C_MUTED, ebene, 2, "staub",
              70, hinten, 3.0)
        self.ruckeln(K.WAFFEN["rakete"]["kamera"], "schuss", pos, ebene, quelle)
        self.klang("rakete", 1.0, pos, ebene)

    def schlagknall(self, pos, winkel: float, ebene: int,
                    getroffen: bool = False, quelle=None,
                    treffer_art: str = "organisch") -> None:
        """Der Schwung des Brecheisens: Funken in einem Kegel und ein Ton."""
        from .entities import wolke
        d = K.WAFFEN["brecheisen"]
        pos = pygame.Vector2(pos)
        wolke(self, pos, 6 if getroffen else 3, 160, 0.18,
              K.C_CREAM if getroffen else K.C_MUTED, ebene, 1, "funke",
              d["winkel"], winkel, 7.0)
        self.ruckeln(d["kamera"] if getroffen else 0.8, "nahkampf", pos,
                     ebene, quelle)
        if getroffen:
            name = ("nahkampf_treffer_metall" if treffer_art == "metall"
                    else "nahkampf_treffer_organisch")
        else:
            name = "nahkampf_schwung"
        self.klang(name, 0.7, pos, ebene)

    def aufschlagring(self, pos, ebene: int, wucht: float = 1.0) -> None:
        """Ein Staubring, der vom Aufsetzpunkt nach aussen laeuft."""
        self.ringe.append([pygame.Vector2(pos), int(ebene),
                           K.STURZ["ring_dauer"], max(0.15, float(wucht))])

    def aufschrift(self, pos, ebene: int, text: str, farbe=K.C_CREAM) -> None:
        """Kurzer Text, der ueber der Stelle aufsteigt und verblasst.

        Dafuer da, dass man merkt, dass etwas geschehen ist: eine
        Munitionskiste, die man im Vorbeilaufen mitnimmt, verschwand sonst
        einfach, und man stand da und wusste nicht, ob sie gewirkt hat.
        """
        self.aufschriften.append([pygame.Vector2(pos), int(ebene), str(text),
                                  tuple(farbe), K.BEUTE_ZEIGEN["dauer"]])

    def beute_genommen(self, pos, ebene: int, art: str, nummer: int = -1) -> None:
        """Jemand hat etwas aufgehoben: Funken, Aufschrift, Ton.

        Eine Stelle fuer alle drei, damit die Rueckmeldung ueberall gleich
        aussieht - und damit der Mehrspieler sie sich abgreifen und an
        seine Gaeste weitergeben kann, die ja nichts selbst rechnen.
        """
        from .entities import wolke
        b = K.BEUTE_ZEIGEN
        text, farbe = K.BEUTE_TEXTE.get(art, ("AUFGENOMMEN", K.C_CREAM))
        wolke(self, pos, b["funken"], 110, 0.45, farbe, ebene, 1, "funke")
        self.aufschrift(pos, ebene, text, farbe)
        self.klang("aufheben", 0.75)

    def effekte_schritt(self, dt: float) -> None:
        """Alles altern lassen, was nur Rueckmeldung ist und nichts entscheidet.

        Getrennt von schritt(), weil ein Gast die Welt nicht simuliert,
        seine Rueckmeldungen aber trotzdem laufen muessen. Partikel und
        Muendungsblitze gehoeren seit der Wirkungsmeldung dazu: der Gast
        legt sie jetzt selbst an, und was nie altert, liegt bis zum Ende
        der Runde im Bild.
        """
        for ring in self.ringe:
            ring[2] -= dt
        if any(r[2] <= 0 for r in self.ringe):
            self.ringe = [r for r in self.ringe if r[2] > 0]
        for a in self.aufschriften:
            a[4] -= dt
        if any(a[4] <= 0 for a in self.aufschriften):
            self.aufschriften = [a for a in self.aufschriften if a[4] > 0]
        for p in self.partikel:
            p.schritt(dt)
        if any(not p.lebt for p in self.partikel):
            self.partikel = [p for p in self.partikel if p.lebt]
        self.flammen_zeit += dt
        if self.flammen:
            self._flammen_schritt(dt)
        if self.lichtblitze:
            for b in self.lichtblitze:
                b[3] -= dt
            self.lichtblitze = [b for b in self.lichtblitze if b[3] > 0]
        if self.feuerbaelle:
            for f in self.feuerbaelle:
                f.schritt(dt)
            self.feuerbaelle = [f for f in self.feuerbaelle if f.lebt]
        if self.flugleichen:
            for f in self.flugleichen:
                f.schritt(dt, self)
            self.flugleichen = [f for f in self.flugleichen if f.lebt]
        # Beim Gast altert das Feuer hier mit, ohne Welt: er bekommt die
        # Flaechen gemeldet und soll sie zuengeln sehen, aber niemandem
        # Schaden machen - das rechnet der Gastgeber.
        if self.feuer and not self._rechnet:
            for b in self.feuer:
                b.schritt(dt, None)
        if self.naegel and not self._rechnet:
            for n in self.naegel:
                n.schritt(dt, None)
        if self.gas and not self._rechnet:
            for g in self.gas:
                g.schritt(dt, None)
        if self.entladungen:
            for e in self.entladungen:
                e[3] -= dt
            self.entladungen = [e for e in self.entladungen if e[3] > 0]
        if self.muendungen:
            for m in self.muendungen:
                m[3] -= dt
            self.muendungen = [m for m in self.muendungen if m[3] > 0]

    def verdeckt(self, pos, ebene: int) -> bool:
        """Steht an dieser Stelle so dichter Rauch, dass niemand sie sieht?

        Gefragt wird nach der Ebene des Verborgenen, nicht nach der des
        Zuschauers: wer von oben in eine Rauchwand hinunterschaut, sieht
        genauso wenig wie der, der daneben steht.
        """
        for r in self.rauch:
            if r.deckt(pos, ebene):
                return True
        return False

    def muendung(self, pos, winkel: float, ebene: int, groesse: float = 1.0) -> None:
        """Ein Muendungsblitz. `groesse` seit 0.34.59: die Kanone blitzt
        2,4-mal so gross und etwas laenger."""
        self.muendungen.append([pygame.Vector2(pos), winkel, ebene,
                                0.055 * (1.0 + (groesse - 1.0) * 0.5), float(groesse)])

    # ---- Bestand -----------------------------------------------------
    def dazu(self, w):
        self.neue.append(w)
        w.welt = self
        return w

    def ebene(self, index: int) -> Ebene:
        ebenen = self.ebenen
        # Der haeufige Fall zuerst (seit 0.34.75), Ergebnis wie vorher.
        if 0 <= index < len(ebenen):
            return ebenen[index]
        return ebenen[max(0, min(len(ebenen) - 1, index))]

    def hoehe(self, index: int) -> float:
        """Hoehe einer Ebene in Welt-Pixeln, aus der Tabelle in config."""
        i = max(0, min(len(K.EBENEN_HOEHE) - 1, index))
        return K.EBENEN_HOEHE[i]

    def abstand(self, oben: int, unten: int) -> float:
        return max(1.0, self.hoehe(oben) - self.hoehe(unten))

    # True, solange diese Welt wirklich gerechnet wird. Beim Gast steht
    # sie auf False: er bekommt alles gemeldet und darf nichts selbst
    # entscheiden - vor allem keinen Schaden.
    _rechnet = False

    def schritt(self, dt: float) -> None:
        # Zaehlt die Bilder. Das Wegenetz rechnet je Bild hoechstens ein
        # neues Feld und muss wissen, wann ein neues Bild anfaengt.
        self.bildnummer = getattr(self, "bildnummer", 0) + 1
        self.zeit += dt
        self._rechnet = True
        if self.neue:
            self.wesen.extend(self.neue)
            self.neue.clear()
        self._raster_bauen()
        for w in self.wesen:
            if w.lebt:
                w.schritt(dt)
        self.effekte_schritt(dt)
        for r in self.rauch:
            r.schritt(dt)
        if any(not r.lebt for r in self.rauch):
            self.rauch = [r for r in self.rauch if r.lebt]
        # Feuer bekommt die Welt mit: es macht Schaden, und Schaden rechnet
        # nur, wer die Welt rechnet.
        for b in self.feuer:
            b.schritt(dt, self)
        if any(not b.lebt for b in self.feuer):
            self.feuer = [b for b in self.feuer if b.lebt]
        for n in self.naegel:
            n.schritt(dt, self)
        if any(not n.lebt for n in self.naegel):
            self.naegel = [n for n in self.naegel if n.lebt]
        for g in self.gas:
            g.schritt(dt, self)
        if any(not g.lebt for g in self.gas):
            self.gas = [g for g in self.gas if g.lebt]
        if any(not w.lebt for w in self.wesen):
            self.wesen = [w for w in self.wesen if w.lebt]

    # ---- Nachbarschaft ------------------------------------------------
    def _raster_bauen(self) -> None:
        self._raster.clear()
        self._belegt = {}
        self._gross = []
        for w in self.wesen:
            if not w.lebt or w.radius <= 0 or not w.trefferbar:
                continue
            if getattr(w, "huelle_radius", 0.0) > self.ZELLE * 0.5:
                self._gross.append(w)
                continue
            k = (int(w.pos.x // self.ZELLE), int(w.pos.y // self.ZELLE), w.ebene)
            self._raster.setdefault(k, []).append(w)

    def nahe(self, pos: pygame.Vector2, radius: float, ebene: int):
        """Alle Wesen der Ebene, deren Zelle den Kreis beruehrt - und die
        grossen (Panzer, Panzerwagen), deren Huelle ihn beruehrt."""
        # Seit 0.34.75 eine Liste statt eines Generators: dieselben Wesen in
        # derselben Reihenfolge, aber ohne die Kosten je geliefertem Wesen.
        # Das Raster aendert sich waehrend eines Schritts nicht (gebaut wird
        # es am Anfang von schritt), eine Liste sieht also dasselbe.
        zelle = self.ZELLE
        r = int(radius // zelle) + 1
        cx, cy = int(pos.x // zelle), int(pos.y // zelle)
        raster = self._raster
        raus = []
        seite = 2 * r + 1
        belegt = self.__dict__.get("_belegt")
        if belegt is not None and seite * seite > 9:
            # Bei grossem Kreis (seit 0.34.75): statt jede Zelle zu fragen die
            # belegten Zellen der Ebene durchgehen - nach Zeile und Spalte
            # sortiert, also in derselben Reihenfolge wie die Schleife unten.
            zellen = belegt.get(ebene)
            if zellen is None:
                zellen = belegt[ebene] = sorted(
                    (k[1], k[0], v) for k, v in raster.items() if k[2] == ebene)
            if len(zellen) < seite * seite:
                y0, y1, x0, x1 = cy - r, cy + r, cx - r, cx + r
                # Erst zur ersten Zeile springen: (y0,) liegt vor jedem
                # Eintrag (y0, ...), es werden nie die Listen verglichen.
                for i in range(bisect_left(zellen, (y0,)), len(zellen)):
                    gy, gx, drin = zellen[i]
                    if gy > y1:
                        break
                    if x0 <= gx <= x1:
                        raus.extend(drin)
                zellen = None
            else:
                zellen = ()
        else:
            zellen = ()
        if zellen == ():
            for gy in range(cy - r, cy + r + 1):
                for gx in range(cx - r, cx + r + 1):
                    drin = raster.get((gx, gy, ebene))
                    if drin:
                        raus.extend(drin)
        if self._gross:
            for w in self._gross:
                if (w.ebene == ebene and w.pos.distance_squared_to(pos)
                        <= (radius + w.huelle_radius + zelle) ** 2):
                    raus.append(w)
        return raus

    def treffer(self, pos: pygame.Vector2, radius: float, ebene: int, feind_von: str,
                rueck: float = 0.0):
        """Naechstes lebendes Ziel einer anderen Fraktion im Kreis.

        Was rechteckig ist (Panzer, Panzerwagen, seit 0.34.59), wird an
        seinem Rechteck getroffen und nicht an einem Kreis darum.

        `rueck` (seit 0.34.105, Treffer-Rueckrechnung): so viele Sekunden
        zurueck wird gefragt - jedes Ziel steht dann dort, wo es damals stand
        (lagen_merken). Die Kugel eines Gasts fragt so nach dem, was der Gast
        gesehen hat. Waende fragt der Aufrufer wie immer jetzt."""
        bestes, beste_d = None, 1e18
        damals = None
        weite = radius + 24
        if rueck > 0.0 and self.__dict__.get("_lagen"):
            damals = self._lagen_um(self._lagen_zeit - rueck)
            if damals is not None:
                # So weit kann sich seitdem etwas bewegt haben (ein Dash ist
                # mit gut 400 px/s das schnellste) - nicht mehr: jeder
                # Teilschritt jeder Kugel fragt hier.
                weite += min(K.NETZ["rueck_suchweite"], rueck * K.NETZ["rueck_tempo"])
        for w in self.nahe(pos, weite, ebene):
            if not w.lebt or w.fraktion == feind_von or w.leben <= 0:
                continue
            if damals is not None:
                eintrag = damals.get(id(w))
                if eintrag is not None and eintrag[0] is w and (
                        (w.pos.x - eintrag[1][0]) ** 2 + (w.pos.y - eintrag[1][1]) ** 2
                        > (rueck * K.NETZ["rueck_tempo"] + 30.0) ** 2):
                    # Weiter, als es in der Zeit laufen kann: versetzt
                    # (Wiedereinstieg, Treppe, Teleport). Dann zaehlt, wo es
                    # jetzt ist - sonst traefe die Kugel einen Ort, an dem es
                    # nie hingelaufen ist.
                    eintrag = None
                if eintrag is not None and eintrag[0] is w:
                    # Statt das Ziel zurueckzusetzen, den Punkt der Kugel um
                    # den Weg verschieben, den es seitdem gemacht hat - dann
                    # stimmt es auch fuer Rechtecke (beruehrt) ohne Umbau.
                    p = pos + (w.pos - pygame.Vector2(eintrag[1]))
                    if getattr(w, "rechteckig", False) or getattr(w, "c4_haftet", False):
                        d = p.distance_squared_to(w.pos)
                        if w.beruehrt(p, radius) and d < beste_d:
                            bestes, beste_d = w, d
                        continue
                    d = p.distance_squared_to(w.pos)
                    if d < (radius + w.radius) ** 2 and d < beste_d:
                        bestes, beste_d = w, d
                    continue
                if pos.distance_squared_to(w.pos) > (radius + 24) ** 2:
                    continue          # ohne alte Lage: nur, was jetzt nah ist
            d = pos.distance_squared_to(w.pos)
            if getattr(w, "rechteckig", False) or getattr(w, "c4_haftet", False):
                # Auch der Buggy (seit 0.34.64) an seiner ganzen Laenge (zwei
                # Kreise), nicht nur 13 Pixel um die Mitte: ein fahrender
                # Buggy war sonst kaum zu treffen (gefunden in einer Aufnahme).
                if w.beruehrt(pos, radius) and d < beste_d:
                    bestes, beste_d = w, d
                continue
            grenze = (radius + w.radius) ** 2
            if d < grenze and d < beste_d:
                bestes, beste_d = w, d
        return bestes

    # ---- Treffer-Rueckrechnung (seit 0.34.105) -----------------------------
    def lagen_merken(self, zeit: float) -> None:
        """Wo jedes Wesen, das getroffen werden kann, gerade steht - eine
        Drittelsekunde lang gemerkt (K.NETZ rueck_lagen). Nur beim Gastgeber
        mit Gaesten (Gefecht)."""
        from collections import deque
        lagen = self.__dict__.get("_lagen")
        if lagen is None:
            lagen = self._lagen = deque()
        lagen.append((zeit, {id(w): (w, (w.pos.x, w.pos.y)) for w in self.wesen
                             if w.lebt and w.fraktion != "geschoss"}))
        self._lagen_zeit = zeit
        while len(lagen) > K.NETZ["rueck_lagen"]:
            lagen.popleft()

    def _lagen_um(self, zeit: float):
        """Die gemerkte Lage, die dem Zeitpunkt am naechsten liegt - oder
        None, wenn er vor der aeltesten liegt."""
        lagen = self.__dict__.get("_lagen")
        if not lagen or zeit < lagen[0][0] - 1e-6:
            return None
        bestes = None
        for t, lage in reversed(lagen):
            bestes = lage
            if t <= zeit + 1e-6:
                break
        return bestes

    # ---- Kollision ----------------------------------------------------
    def huelle(self, kachel: int) -> tuple:
        """Was an einer festen Kachel wirklich aufhaelt: (Form, x, y, b, h)
        in der Kachel, Form "block" oder "rund".

        Seit 0.34.19 die Grundflaeche aus K.STEHEN - dieselbe, die auch
        gezeichnet wird. Bis dahin hielt jede feste Kachel als ganzes
        Quadrat auf: an einem Kaktus von 18 Pixeln blieb man 7 Pixel vor
        seinem Rand in der Luft haengen (gemeldet). Mauern, Fels und alles
        ohne Eintrag fuellen die Kachel weiter ganz."""
        cache = self.__dict__.setdefault("_huellen", {})
        hit = cache.get(kachel)
        if hit is None:
            daten = K.KACHELN[kachel]
            satz = K.KARTENSAETZE.get(getattr(self, "satz", ""), {})
            name = satz.get(daten["bild"], daten["bild"])
            st = K.STEHEN.get(name) or K.STEHEN.get(daten.get("name", ""))
            if st is None:
                hit = ("block", 0, 0, K.TILE, K.TILE)
            else:
                hit = (st["form"],) + tuple(st["rahmen"])
            cache[kachel] = hit
        return hit

    def _frei_tafel_bauen(self):
        tafel = {}
        for kachel, daten in K.KACHELN.items():
            if daten["fest"]:
                tafel[kachel] = self.huelle(kachel)
            elif daten.get("loch", False):
                tafel[kachel] = _LOCH
            else:
                tafel[kachel] = None
        self._frei_tafel = (K.KACHELN, getattr(self, "satz", ""), tafel)
        return self._frei_tafel

    def frei(self, pos: pygame.Vector2, radius: float, ebene: int,
             loch_fest: bool = False) -> bool:
        """loch_fest: Loecher zaehlen als Wand. Fuer alles, was nicht fallen soll.

        Feste Kacheln halten mit ihrer Grundflaeche auf (`huelle`), Loecher
        mit der ganzen Kachel."""
        ebenen = self.ebenen
        e = ebenen[ebene] if 0 <= ebene < len(ebenen) else self.ebene(ebene)
        T = K.TILE
        px, py = pos.x, pos.y
        t0x = int((px - radius) // T)
        t1x = int((px + radius) // T)
        t0y = int((py - radius) // T)
        t1y = int((py + radius) // T)
        r2 = radius * radius
        # Lokal und ohne den Umweg ueber kachel()/loch() (seit 0.34.75) -
        # dieselben Fragen in derselben Reihenfolge, nur billiger.
        kacheln, breite, hoehe = e.kacheln, e.breite, e.hoehe
        # Je Kachelart fertig (seit 0.34.75): None (frei), _LOCH, oder die
        # Huelle der festen Kachel - dieselbe Unterscheidung wie mit
        # K.KACHELN[...]["fest"] / "loch" und huelle(), ohne sie jedesmal.
        tafel = self.__dict__.get("_frei_tafel")
        if tafel is None or tafel[0] is not K.KACHELN or tafel[1] != getattr(self, "satz", ""):
            tafel = self._frei_tafel_bauen()
        tafel = tafel[2]
        leer = K.LEER
        for ty in range(t0y, t1y + 1):
            innen_y = 0 <= ty < hoehe
            for tx in range(t0x, t1x + 1):
                if innen_y and 0 <= tx < breite:
                    kachel = kacheln[ty * breite + tx]
                    innen = True
                else:
                    kachel = leer
                    innen = False
                art = tafel[kachel]
                if art is None:
                    continue
                if art is _LOCH:
                    if not (loch_fest and innen):
                        continue
                    form, rx, ry, rb, rh = "block", 0, 0, T, T
                else:
                    form, rx, ry, rb, rh = art
                x0, y0 = tx * T + rx, ty * T + ry
                if form == "rund":
                    mx, my = x0 + rb / 2.0, y0 + rh / 2.0
                    grenze = radius + rb / 2.0
                    if (px - mx) ** 2 + (py - my) ** 2 < grenze * grenze:
                        return False
                    continue
                nx = max(x0, min(px, x0 + rb))
                ny = max(y0, min(py, y0 + rh))
                if (px - nx) ** 2 + (py - ny) ** 2 < r2:
                    return False
        return True

    def bewegen(self, wesen, dx: float, dy: float,
                loch_fest: bool | None = None) -> tuple[bool, bool]:
        """Achsenweise schieben. Gibt zurueck, ob an x bzw. y angestossen wurde.

        `loch_fest` ueberstimmt, ob Loecher fuer dieses Wesen Wand sind -
        gebraucht fuer den Rueckstoss eines Gegners, der selbst nie in ein
        Loch laeuft, aber hineingeschoben werden kann (Gegner._geschoben).

        Getrennt nach Achsen, damit man an einer Wand entlanggleitet statt
        kleben zu bleiben. Grosse Schritte werden unterteilt, damit nichts
        durch duenne Waende rutscht.
        """
        pos, r, eb = wesen.pos, wesen.radius, wesen.ebene
        # Auch im Sturz zaehlen die Waende der Ebene, auf die es hinuntergeht:
        # man gleitet im Flug an ihnen entlang statt hindurchzufliegen. Nur so
        # steht die Figur beim Aufsetzen schon auf freiem Grund und muss nicht
        # im letzten Bild noch zur Seite gesetzt werden.
        lf = (not getattr(wesen, "faellt", False)) if loch_fest is None else loch_fest
        stoss_x = stoss_y = False
        schritte = max(1, int(max(abs(dx), abs(dy)) / (r * 0.75)) + 1)
        sx, sy = dx / schritte, dy / schritte
        for _ in range(schritte):
            if sx:
                pos.x += sx
                if not self.frei(pos, r, eb, lf):
                    pos.x -= sx
                    stoss_x = True
                    sx = 0.0
            if sy:
                pos.y += sy
                if not self.frei(pos, r, eb, lf):
                    pos.y -= sy
                    stoss_y = True
                    sy = 0.0
            if not sx and not sy:
                break
        return stoss_x, stoss_y

    def auseinander(self, wesen) -> None:
        """Weiche Abstossung, damit Gegner sich nicht ineinander schieben.

        Geschoben wird nur, wenn das Ziel frei ist. Sonst drueckt eine Gruppe
        Gegner den Spieler in die naechste Wand.
        """
        # Wer am Boden liegt, liegt fest: er schiebt niemanden und wird von
        # niemandem geschoben. Vorher rutschte ein Gefallener unter jedem,
        # der an ihm vorbeiging, ein Stueck weiter - und wer genug Leute um
        # ihn herum hatte, schob ihn quer durch den Raum.
        if getattr(wesen, "am_boden", False):
            return
        # Wer unverschiebbar ist (Zielpuppe, Koloss), bleibt stehen, und der
        # andere weicht den ganzen Weg aus. Vorher gab jeder die Haelfte
        # nach - und eine Puppe liess sich durch Hineinlaufen quer durch
        # den Schiessstand schieben (gemeldet nach 0.31).
        # Wer einem aufhilft, kniet und haelt seinen Platz (seit 0.34.55):
        # wer an ihm vorbeiging, schob ihn aus der Reichweite, und er fing
        # neu an, waehrend der Fortschritt verfiel.
        fest_w = not getattr(wesen, "schiebbar", True) or getattr(wesen, "hilft", None) is not None
        for a in self.nahe(wesen.pos, wesen.radius * 2, wesen.ebene):
            if a is wesen:
                continue
            # Erst der Abstand (seit 0.34.75): die meisten aus dem Raster
            # sind zu weit weg, und die Fragen danach aendern nichts - sie
            # entscheiden nur mit, ob geschoben wird.
            d = wesen.pos - a.pos
            abstand = d.length()
            mindest = wesen.radius + a.radius
            if not 0.0001 < abstand < mindest:
                continue
            if not a.schiebt or getattr(a, "am_boden", False):
                continue
            fest_a = not getattr(a, "schiebbar", True) or getattr(a, "hilft", None) is not None
            if fest_w and fest_a:
                continue
            schub = d / abstand * (mindest - abstand)
            if not fest_w:
                weg = schub * (1.0 if fest_a else 0.5)
                if self.frei(wesen.pos + weg, wesen.radius, wesen.ebene,
                             not getattr(wesen, "faellt", False)):
                    wesen.pos += weg
            if not fest_a:
                weg = schub * (1.0 if fest_w else 0.5)
                if self.frei(a.pos - weg, a.radius, a.ebene,
                             not getattr(a, "faellt", False)):
                    a.pos -= weg

    def befreien(self, wesen) -> bool:
        """Holt ein Wesen aus der Wand, falls es doch einmal darin steckt.

        Passiert durch Rueckstoss, Gedraenge oder einen ungluecklichen
        Landeplatz. Gesucht wird der naechste freie Punkt in wachsenden
        Ringen, damit der Ausweg so kurz wie moeglich bleibt.
        """
        if getattr(wesen, "sturz_rest", 0.0) > 0:
            return False          # in der Luft steckt niemand in einer Wand
        # Ein Gegner, der gerade geschoben wird, darf ueber der Kante
        # haengen - sonst zoege ihn das hier in jedem Schritt zurueck, und
        # er fiele nie (Gegner._geschoben).
        lf = not getattr(wesen, "faellt", False) and not getattr(wesen, "geschoben", False)
        if self.frei(wesen.pos, wesen.radius, wesen.ebene, lf):
            return False
        for r in (3.0, 6.0, 10.0, 15.0, 21.0, 29.0, 40.0, 54.0):
            for i in range(12):
                a = math.tau * i / 12 + r * 0.7
                p = wesen.pos + pygame.Vector2(math.cos(a), math.sin(a)) * r
                if self.frei(p, wesen.radius, wesen.ebene, lf):
                    wesen.pos.update(p)
                    wesen.vorher.update(p)
                    wesen.tempo *= 0.4
                    return True
        return False

    def strahl(self, von, richtung, laenge: float, ebene: int):
        """Erster Punkt auf der Linie, an dem etwas im Weg steht - dort,
        wo auch eine Kugel haelt (`schuss_halt`)."""
        schritte = max(1, int(laenge / 4.0))
        for i in range(1, schritte + 1):
            p = von + richtung * (laenge * i / schritte)
            if self.schuss_halt(p, ebene):
                return von + richtung * (laenge * (i - 1) / schritte)
        return von + richtung * laenge

    def kachel_hoehe(self, pos, ebene: int) -> float:
        """Wie hoch steht, was an dieser Stelle steht (K.STEHEN), in
        Spielpixeln - 0 fuer flachen Boden. Seit 0.34.87 fuer den
        Granatwerfer: was hoeher fliegt, geht darueber."""
        e = self.ebene(ebene)
        kachel = e.kachel(int(pos.x // K.TILE), int(pos.y // K.TILE))
        d = K.KACHELN[kachel]
        if not d["fest"]:
            return 0.0
        st = K.STEHEN.get(d.get("name", ""))
        if st is None:
            # Ohne Eintrag (alte Kartenkacheln): eine Mauer im Zweifel.
            return K.STEHEN["wand"]["hoehe"] if d["sicht"] else K.STEHEN["kiste"]["hoehe"]
        return float(st["hoehe"])

    def schuss_halt(self, pos, ebene: int, radius: float = 0.0,
                    nur_hoch: bool = False) -> bool:
        """Haelt etwas an dieser Stelle eine Kugel auf?

        Seit 0.34.26 jede feste Kachel, mit ihrer Grundflaeche (`huelle`),
        nicht mehr nur die sichtdichten. Gemeldet: "sehr, sehr viele
        Hindernisse, auch zum Beispiel auf der Wuestenmap, lassen Schuesse
        durch. Alles, was eine Art Textur hat und etwas blocken sollte,
        sollte auch Schuesse blocken." Bis dahin flog eine Kugel durch
        Kisten, Sandsaecke, Faesser, Kakteen und Schrott - man stand
        dahinter und war doch nicht in Deckung.

        `nur_hoch` (seit 0.34.62): nur, was auch die Sicht nimmt (Mauern) -
        fuer die Panzerbuechse, die durch Kisten und Sandsaecke geht."""
        e = self.ebene(ebene)
        tx, ty = int(pos.x // K.TILE), int(pos.y // K.TILE)
        kachel = e.kachel(tx, ty)
        d = K.KACHELN[kachel]
        if d["sicht"]:
            return True
        if not d["fest"] or nur_hoch:
            return False
        form, rx, ry, rb, rh = self.huelle(kachel)
        x0, y0 = tx * K.TILE + rx, ty * K.TILE + ry
        if form == "rund":
            mx, my = x0 + rb / 2.0, y0 + rh / 2.0
            grenze = radius + rb / 2.0
            return (pos.x - mx) ** 2 + (pos.y - my) ** 2 < grenze * grenze
        return (x0 - radius <= pos.x < x0 + rb + radius
                and y0 - radius <= pos.y < y0 + rh + radius)

    def deckung(self, von, nach, ebene: int) -> str:
        """Was zwischen zwei Punkten steht: "" (nichts), "hindernis"
        (Kiste, Sandsack, Fass ...) oder "wand" (sichtdicht).

        Fuer Explosionen und Blendgranaten (seit 0.34.26): eine Kugel haelt
        jedes Hindernis auf, eine Druckwelle geht abgeschwaecht darueber
        und daran vorbei (K.DECKUNG). Abgetastet in Schritten von 4
        Pixeln; die beiden Enden zaehlen nicht - wer neben einer Kiste
        steht, steht nicht hinter ihr."""
        if self._strecke_frei(von, nach, ebene):
            return ""
        von = pygame.Vector2(von)
        nach = pygame.Vector2(nach)
        stuecke = []
        frei, _fest = self._linie(von, nach, ebene, stuecke)
        if not frei:
            return "wand"
        if not stuecke:
            # Keine feste Kachel auf der Linie: dann steht auch nichts im Weg
            # (seit 0.34.57 ohne das Abtasten - der haeufigste Fall).
            return ""
        laenge = von.distance_to(nach)
        schritte = int(laenge / 4.0)
        if schritte < 2:
            return ""
        # Abgetastet wird nur, wo die Linie eine feste Kachel kreuzt (seit
        # 0.34.57), mit einer Probe Rand zu jeder Seite - jede Probe
        # dazwischen liegt in einer freien Kachel und haelt nichts auf. Vorher
        # die ganze Linie: an einer Kiste vorbei zum fernen Gegner hundert
        # Proben fuer zwei, die zaehlen. Welche Probe zuerst trifft, ist
        # gleich - jede ergibt "hindernis".
        proben = set()
        for t0, t1 in stuecke:
            proben.update(range(max(1, int(t0 * schritte) - 1),
                                min(schritte - 1, int(t1 * schritte) + 2) + 1))
        # Dasselbe wie schuss_halt an jedem Punkt, nur ohne neuen Vektor je
        # Punkt und mit der Kachel gemerkt, solange die Linie in ihr bleibt:
        # die Bots fragen das tausendfach je Sekunde (seit 0.34.52).
        e = self.ebene(ebene)
        T = K.TILE
        tafel = K.KACHELN
        x0, y0 = von.x, von.y
        dx, dy = nach.x - x0, nach.y - y0
        vorige = None
        huelle = None
        for i in sorted(proben):
            t = i / float(schritte)
            px, py = x0 + dx * t, y0 + dy * t
            tx, ty = int(px // T), int(py // T)
            if (tx, ty) != vorige:
                vorige = (tx, ty)
                kachel = e.kachel(tx, ty)
                d = tafel[kachel]
                if d["sicht"]:
                    return "hindernis"
                if not d["fest"]:
                    huelle = None
                    continue
                form, rx, ry, rb, rh = self.huelle(kachel)
                huelle = (form, tx * T + rx, ty * T + ry, rb, rh)
            if huelle is None:
                continue
            form, hx, hy, rb, rh = huelle
            if form == "rund":
                mx, my = hx + rb / 2.0, hy + rh / 2.0
                if (px - mx) ** 2 + (py - my) ** 2 < (rb / 2.0) ** 2:
                    return "hindernis"
            elif hx <= px < hx + rb and hy <= py < hy + rh:
                return "hindernis"
        return ""

    def _strecke_frei(self, von, nach, ebene: int) -> bool:
        """Ist jede Kachel im Rechteck um die Strecke frei und in der Karte?
        Dann findet die Verfolgung in `deckung` weder Wand noch Hindernis -
        sie kommt nie aus diesem Rechteck heraus -, und die Antwort ist ""
        (seit 0.34.89). Ein Hauch Rand je Seite deckt die Nachbarn, die sie
        an einer Kachelecke mitprueft. Gefragt wird `deckung` vor allem mit
        kurzen Strecken (trupp.gedeckt_hier), meist im Freien."""
        T = float(K.TILE)
        ax, ay, bx, by = von[0] / T, von[1] / T, nach[0] / T, nach[1] / T
        if ax > bx:
            ax, bx = bx, ax
        if ay > by:
            ay, by = by, ay
        e = self.ebene(ebene)
        tx0, tx1 = int(math.floor(ax - 1e-6)), int(math.floor(bx + 1e-6))
        ty0, ty1 = int(math.floor(ay - 1e-6)), int(math.floor(by + 1e-6))
        b = e.breite
        if not (0 <= tx0 and tx1 < b and 0 <= ty0 and ty1 < e.hoehe
                and (tx1 - tx0 + 1) * (ty1 - ty0 + 1) <= 16):
            return False
        art = _tafeln()
        kacheln = e.kacheln
        for ty in range(ty0, ty1 + 1):
            zeile = ty * b
            for tx in range(tx0, tx1 + 1):
                if art[kacheln[zeile + tx]]:
                    return False
        return True

    def deckung_anteil(self, von, nach, ebene: int) -> float:
        """Wie viel einer Explosion bei `nach` ankommt (K.DECKUNG)."""
        return K.DECKUNG["explosion_" + (self.deckung(von, nach, ebene) or "frei")]

    def boden_unter(self, pos, ebene: int) -> int:
        """Erste Ebene unterhalb, die an dieser Stelle wirklich Boden hat."""
        tx, ty = int(pos.x // K.TILE), int(pos.y // K.TILE)
        ziel = ebene - 1
        while ziel > 0 and self.ebene(ziel).loch(tx, ty):
            ziel -= 1
        return max(0, ziel)

    def sicht_frei(self, von: pygame.Vector2, nach: pygame.Vector2, ebene: int) -> bool:
        """Freie Sicht von `von` nach `nach`? Jede Kachel auf der Linie zaehlt.

        Bis 0.31 wurde die Linie in Schritten einer halben Kachel abgetastet.
        Was eine Wandecke nur schraeg anschneidet, liegt dabei auf weniger
        als einer halben Kachel - und wurde oft uebersprungen. Gemessen:
        wer sich eng hinter eine Ecke stellte, galt in zwei von hundert
        Faellen trotzdem als sichtbar, und eine Blendgranate um die Ecke
        traf ihn voll (gemeldet). Jetzt wird die Linie Kachel fuer Kachel
        verfolgt (Amanatides/Woo): keine Kachel, durch die sie geht, kann
        fehlen. Geht sie genau durch eine Kachelecke, sperrt jede der beiden
        Nachbarkacheln - durch einen Spalt zwischen zwei Waenden sieht man
        nicht.

        Die Startkachel zaehlt nicht (man steht ja darin), die Zielkachel
        schon - wie vorher.
        """
        return self._linie(von, nach, ebene)[0]

    def _linie(self, von, nach, ebene: int, stuecke=None) -> tuple:
        """(frei, fest): Sicht wie `sicht_frei`, und ob dabei eine feste
        Kachel (Kiste, Fass ...) auf der Linie liegt - die Startkachel und
        bei einer Kachelecke beide Nachbarn eingeschlossen. In `stuecke`
        (eine Liste, wenn angegeben) kommt fuer jede solche Kachel, von
        wann bis wann die Linie in ihr liegt (0 bis 1 von `von` nach `nach`).

        Seit 0.34.57 eine Verfolgung fuer beides und mit Tafeln je
        Kachelart statt zweier Methodenaufrufe und eines Woerterbuchs je
        Kachel: Sicht und Deckung fragen die Bots hunderttausendfach je
        Minute, gemessen ein Drittel der ganzen Rechenzeit einer grossen
        Schlacht."""
        e = self.ebene(ebene)
        art = _tafeln()
        kacheln = e.kacheln
        b, h = e.breite, e.hoehe
        leer_sicht = art[K.LEER] == 2
        T = float(K.TILE)
        x0, y0 = von.x / T, von.y / T
        x1, y1 = nach.x / T, nach.y / T
        dx, dy = x1 - x0, y1 - y0
        tx, ty = int(math.floor(x0)), int(math.floor(y0))
        if 0 <= tx < b and 0 <= ty < h:
            fest = art[kacheln[ty * b + tx]] != 0
        else:
            fest = art[K.LEER] != 0
        if dx * dx + dy * dy < (1.0 / T) ** 2:
            if fest and stuecke is not None:
                stuecke.append((0.0, 1.0))
            return True, fest
        sx = 1 if dx > 0 else -1
        sy = 1 if dy > 0 else -1
        unendlich = float("inf")
        tdx = abs(1.0 / dx) if dx else unendlich
        tdy = abs(1.0 / dy) if dy else unendlich
        if dx > 0:
            tmx = (tx + 1 - x0) * tdx
        elif dx < 0:
            tmx = (x0 - tx) * tdx
        else:
            tmx = unendlich
        if dy > 0:
            tmy = (ty + 1 - y0) * tdy
        elif dy < 0:
            tmy = (y0 - ty) * tdy
        else:
            tmy = unendlich
        if fest and stuecke is not None:
            stuecke.append((0.0, tmx if tmx < tmy else tmy))
        while (tmx if tmx < tmy else tmy) <= 1.0:
            t_ein = tmx if tmx < tmy else tmy
            if abs(tmx - tmy) < 1e-9:
                # Genau durch eine Ecke: jede der beiden Nachbarkacheln sperrt.
                for nx, ny in ((tx + sx, ty), (tx, ty + sy)):
                    if 0 <= nx < b and 0 <= ny < h:
                        z = art[kacheln[ny * b + nx]]
                        if z:
                            if z == 2:
                                return False, fest
                            fest = True
                            if stuecke is not None:
                                stuecke.append((t_ein, t_ein))
                    elif leer_sicht:
                        return False, fest
                tx += sx
                ty += sy
                tmx += tdx
                tmy += tdy
            elif tmx < tmy:
                tx += sx
                tmx += tdx
            else:
                ty += sy
                tmy += tdy
            if 0 <= tx < b and 0 <= ty < h:
                z = art[kacheln[ty * b + tx]]
                if z:
                    if z == 2:
                        return False, fest
                    fest = True
                    if stuecke is not None:
                        stuecke.append((t_ein, tmx if tmx < tmy else tmy))
            elif leer_sicht:
                return False, fest
        return True, fest

    # ---- Ebenenwechsel --------------------------------------------------
    def loch_unter(self, wesen) -> bool:
        """Steht das Wesen ueber einem Loch, unter dem es eine Ebene gibt?"""
        if wesen.ebene <= 0:
            return False
        e = self.ebene(wesen.ebene)
        return e.loch(int(wesen.pos.x // K.TILE), int(wesen.pos.y // K.TILE))

    def landeplatz(self, pos: pygame.Vector2, radius: float, ebene: int):
        """Naechste freie Stelle auf der Zielebene, falls direkt darunter
        etwas im Weg steht."""
        if self.frei(pos, radius, ebene):
            return pygame.Vector2(pos)
        for r in (K.TILE * 0.5, K.TILE, K.TILE * 1.5):
            for i in range(12):
                a = math.tau * i / 12
                p = pos + pygame.Vector2(math.cos(a), math.sin(a)) * r
                if self.frei(p, radius, ebene):
                    return p
        return pygame.Vector2(pos)

    def treppe_unter(self, wesen) -> int | None:
        """Zielebene, wenn das Wesen auf einer Treppe oder Luke steht."""
        e = self.ebene(wesen.ebene)
        tx, ty = int(wesen.pos.x // K.TILE), int(wesen.pos.y // K.TILE)
        daten = e.daten(tx, ty)
        rel = daten.get("treppe")
        if rel is None:
            return None
        ziel = wesen.ebene + rel
        if 0 <= ziel < len(self.ebenen):
            return ziel
        return None

    @property
    def wege(self):
        """Das Wegenetz zwischen den Ebenen, beim ersten Gebrauch gerechnet.

        Die Karte aendert sich nicht, also genuegt ein Mal - gemessen rund
        20 Millisekunden auf STAUBTAL. Siehe wege.py.
        """
        netz = getattr(self, "_wege", None)
        if netz is None:
            from .wege import Wegenetz
            netz = Wegenetz(self)
            self._wege = netz
        return netz

    @property
    def fahrwege(self):
        """Das Wegenetz fuer Fahrzeuge (seit 0.34.95, wege.Fahrwegenetz),
        beim ersten Gebrauch gerechnet."""
        netz = getattr(self, "_fahrwege", None)
        if netz is None:
            from .wege import Fahrwegenetz
            netz = Fahrwegenetz(self, K.BOTS["fahren"]["weg_rand"])
            self._fahrwege = netz
        return netz

    def ebene_wechseln(self, wesen, ziel: int, loch_fest: bool = False) -> bool:
        """Wechselt die Ebene, wenn der Platz dort frei ist.

        loch_fest: auch Loecher zaehlen als belegt. Fuer Gegner - sie laufen
        nie in ein Loch; wer oben halb ueber dem Nichts ankaeme, kaeme
        dort nicht mehr weg. Ein Gegner, dem es noch nicht passt, geht
        weiter zur Mitte der Treppe und versucht es dort.
        """
        alt = wesen.ebene
        wesen.ebene = ziel
        if self.frei(wesen.pos, wesen.radius, ziel, loch_fest):
            wesen.vorher.update(wesen.pos)
            return True
        wesen.ebene = alt
        return False

# ══════════════════════════════════════════════════════════════════
# Testkarte
# ══════════════════════════════════════════════════════════════════

# Ebene 0 ist eine offene Halle: Saeulen und kurze Mauerstuecke als Deckung,
# nichts davon schliesst einen Bereich ab. Ebene 1 ist ein Ring aus Laufstegen
# mit einer Plattform in der Mitte. Die Leerzeichen sind Loecher, durch die man
# die Halle darunter sieht.
#
# Beide Etagen sind mit einer Flutfuellung geprueft: von der Treppe aus ist
# jede begehbare Kachel erreichbar, und jeder Landepunkt eines Uebergangs ist
# auf der Zielebene frei.

# Z ist eine Spawnstelle fuer Gegner (K.SPAWN). Sie stehen an den
# Raendern und hinter den Blockreihen, nicht auf der freien Mitte: wer
# mitten im Bild aus dem Nichts erscheint, sieht nach Fehler aus.
KARTE_E0 = [
    "############################################",
    "#.Z......................................Z.#",
    "#.................,,,,,,,,.................#",
    "#..>..............,,,,,,,,..............>..#",
    "#.....##......##.....>##......##......##...#",
    "#..Z..##......##......##......##......##.Z.#",
    "#........X........................X........#",
    "#....................#.....................#",
    "#.........#######....#.....#######.........#",
    "#..,,,,,.............#..............,,,,,..#",
    "#Z.,,,,,.............#..............,,,,,.Z#",
    "#..,,,,,..........X............X....,,,,,..#",
    "#..,,,,,....X.........>..X..........,,,,,..#",
    "#..,,,,,.............#..............,,,,,..#",
    "#Z.,,,,,.............#..............,,,,,.Z#",
    "#.........#######....#.....#######.........#",
    "#....................#.....................#",
    "#........X........................X........#",
    "#..........................................#",
    "#.....##......##.....>##......##......##...#",
    "#..>..##......##......##......##......##>..#",
    "#..Z..................................ZZ...#",
    "#.Z......................................Z.#",
    "############################################",
]

KARTE_E1 = [
    "############################################",
    "#..........................................#",
    "#.Z...X..............................X..o.Z#",
    "#..<....................................<..#",
    "#...                .<..                ...#",
    "#...                ..X.                ...#",
    "#.X.                .>..                ...#",
    "#...                ....                ...#",
    "#.>.                ....                ...#",
    "#...              ........              ...#",
    "#...              .,,,,,,.              ...#",
    "#..................,,,,,,........>.........#",
    "#..................,,,<,,..................#",
    "#...              .,,,,,,.              .>.#",
    "#...              ........              ...#",
    "#...                ....                ...#",
    "#...                ....                ...#",
    "#...                ....                .X.#",
    "#...                ..X.                ...#",
    "#...                .<..                ...#",
    "#..<....................................<..#",
    "#.Z...X..............................X....Z#",
    "#..........................................#",
    "############################################",
]


KARTE_E2 = [
    "############################################",
    "#                                          #",
    "#                                          #",
    "#                                          #",
    "#               ......                     #",
    "#               ......                     #",
    "# .Z....        ..X..<                     #",
    "# ......        ......                     #",
    "# <.X...        ......        ............ #",
    "# ......        ......        .,,,,,,,,,,. #",
    "# .............................,,,,,,,X,,. #",
    "# .............................,,<,,,,,,,. #",
    "# .............................,,,,,,,,,,. #",
    "# ......        ......        .,,,,X,,,,,< #",
    "# ......        ......        .,,,,,,,,,,. #",
    "# ...X..        .....Z        .Z.......... #",
    "# ......        ......                     #",
    "# ....Z.        ..X...                     #",
    "#               ......                     #",
    "#               ......                     #",
    "#                                          #",
    "#                                          #",
    "#                                          #",
    "############################################",
]


# ══════════════════════════════════════════════════════════════════
# Karten aus Dateien
# ══════════════════════════════════════════════════════════════════
#
# Eine Karte ist eine Textdatei in `karten/`. Ein Zeichen ist eine
# Kachel, und die Ebenen stehen hintereinander, getrennt durch eine
# Zeile `--- ebene N ---`. Damit laesst sich eine Karte in jedem
# Texteditor bauen, und ein spaeterer Tiled-Importeur erzeugt genau
# dieselbe Struktur, ohne dass der Spielcode es merkt.
#
# Alles vor der ersten Ebenenzeile ist Kopf: `schluessel: wert`,
# frei erweiterbar. Zeilen, die mit `#` **und einem Leerzeichen**
# beginnen, sind Kommentar - ein einzelnes `#` ist eine Wand.

def kartenordner() -> Path:
    from .pfade import spielordner
    return spielordner() / "karten"


def karten_liste() -> list[str]:
    ordner = kartenordner()
    if not ordner.is_dir():
        return []
    return sorted(p.stem for p in ordner.glob("*.txt"))


def karte_lesen(name: str):
    """Eine Karte laden. Gibt (Welt, Kopf) zurueck, oder (None, {}).

    Nichts daran wirft: eine kaputte oder fehlende Kartendatei darf
    hoechstens diese eine Karte kosten, nie den Start.
    """
    pfad = kartenordner() / ("%s.txt" % name)
    if not pfad.is_file():
        return None, {}
    try:
        roh = pfad.read_text(encoding="utf-8")
    except OSError:
        return None, {}
    return karte_aus_text(roh)


def karte_aus_text(roh: str):
    kopf: dict[str, str] = {}
    bloecke: list[list[str]] = []
    jetzt: list[str] | None = None
    for zeile in roh.splitlines():
        blank = zeile.strip()
        if blank.startswith("--- ebene"):
            jetzt = []
            bloecke.append(jetzt)
            continue
        if jetzt is None:
            if blank.startswith("# ") or not blank:
                continue
            if ":" in blank:
                schluessel, _, wert = blank.partition(":")
                kopf[schluessel.strip()] = wert.strip()
            continue
        # **Kein rstrip und kein Ueberspringen leerer Zeilen.** Eine
        # Zeile aus lauter Leerzeichen ist eine Reihe Loecher, und wer
        # sie wegwirft, verschiebt alles darunter um eine Kachel. Das
        # ist der Fehler, der eine Karte still kaputtmacht.
        jetzt.append(zeile)
    bloecke = [[z for z in b if len(z) > 0] for b in bloecke]
    bloecke = [b for b in bloecke if b]
    if not bloecke:
        return None, kopf
    welt = Welt([Ebene.aus_text(b, i) for i, b in enumerate(bloecke)],
                satz=str(kopf.get("satz", "")))
    return welt, kopf


def testkarte() -> Welt:
    return Welt([Ebene.aus_text(KARTE_E0, 0),
                 Ebene.aus_text(KARTE_E1, 1),
                 Ebene.aus_text(KARTE_E2, 2)])


def freier_punkt(welt: Welt, ebene: int, rnd, weg_von=None, mindest=0.0):
    """Sucht eine begehbare Stelle, optional mit Abstand zu einem Punkt."""
    e = welt.ebene(ebene)
    for _ in range(400):
        tx = rnd.randrange(1, e.breite - 1)
        ty = rnd.randrange(1, e.hoehe - 1)
        if not e.begehbar(tx, ty):
            continue
        p = pygame.Vector2(tx * K.TILE + K.TILE / 2, ty * K.TILE + K.TILE / 2)
        if weg_von is not None and p.distance_to(weg_von) < mindest:
            continue
        if welt.frei(p, 12, ebene):
            return p
    return pygame.Vector2(e.pixel_breite / 2, e.pixel_hoehe / 2)
