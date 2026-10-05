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
    if welt is not None and not welt.sicht_frei(ich.pos, pos, int(ebene)):
        return 0.0
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
    wert = max(0.0, min(1.0, naehe * hin))
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
        return e

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
        return K.KACHELN[self.kachel(tx, ty)].get("loch", False)

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


class Welt:
    """Haelt die Ebenen und alle Wesen."""

    ZELLE = 48          # Rastergroesse der Nachbarschaftssuche

    def __init__(self, ebenen: list[Ebene], satz: str = "") -> None:
        self.ebenen = ebenen
        # Welcher Kachelsatz gilt. Leer ist der Standard; "wueste" tauscht
        # Boden, Wand und Kiste gegen Sand, Fels und Fass. Steht als
        # `satz:` im Kopf der Kartendatei.
        self.satz = satz
        self.wesen: list = []
        self.neue: list = []
        self.partikel: list = []
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
        # Reine Rueckmeldung: Staubringe beim Aufsetzen und kurze
        # Aufschriften ueber aufgesammelter Beute. Beides entscheidet
        # nichts, es sagt nur, dass etwas passiert ist.
        self.ringe: list = []
        self.aufschriften: list = []

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

    def blutfleck(self, pos, ebene: int, radius: float) -> None:
        pass

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

    def schussknall(self, pos, winkel: float, ebene: int, waffe: str,
                    quelle=None) -> None:
        """Muendungsblitz, Funken und Knall eines Schusses.

        Auch das sah ein Gast bisher nicht: der Gastgeber schickt die
        Geschosse, aber nicht das, was am Lauf passiert. Es blitzte
        nirgends, und zu hoeren war im ganzen Mehrspieler kein einziger
        Schuss ausser dem eigenen.
        """
        from .entities import wolke
        pos = pygame.Vector2(pos)
        self.muendung(pos, winkel, ebene)
        wolke(self, pos, 3, 120, 0.12, (255, 226, 160), ebene, 1, "funke",
              34, winkel, 8.0)
        daten = K.WAFFEN.get(waffe, {})
        self.ruckeln(daten.get("kamera", 1.0), "schuss", pos, ebene, quelle)
        if waffe == "lmg":
            klang = ("lmg_salve" if getattr(quelle, "modus", "dauer") == "salve"
                     else "lmg_dauer")
        else:
            klang = "schuss_schrot" if waffe == "schrot" else "schuss_" + waffe
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
        # Beim Gast altert das Feuer hier mit, ohne Welt: er bekommt die
        # Flaechen gemeldet und soll sie zuengeln sehen, aber niemandem
        # Schaden machen - das rechnet der Gastgeber.
        if self.feuer and not self._rechnet:
            for b in self.feuer:
                b.schritt(dt, None)
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

    def muendung(self, pos, winkel: float, ebene: int) -> None:
        self.muendungen.append([pygame.Vector2(pos), winkel, ebene, 0.055])

    # ---- Bestand -----------------------------------------------------
    def dazu(self, w):
        self.neue.append(w)
        w.welt = self
        return w

    def ebene(self, index: int) -> Ebene:
        return self.ebenen[max(0, min(len(self.ebenen) - 1, index))]

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
                if w.lebt:
                    self.aufzug_pruefen(w)
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
        if any(not w.lebt for w in self.wesen):
            self.wesen = [w for w in self.wesen if w.lebt]

    # ---- Nachbarschaft ------------------------------------------------
    def _raster_bauen(self) -> None:
        self._raster.clear()
        for w in self.wesen:
            if not w.lebt or w.radius <= 0 or not w.trefferbar:
                continue
            k = (int(w.pos.x // self.ZELLE), int(w.pos.y // self.ZELLE), w.ebene)
            self._raster.setdefault(k, []).append(w)

    def nahe(self, pos: pygame.Vector2, radius: float, ebene: int):
        """Alle Wesen der Ebene, deren Zelle den Kreis beruehrt."""
        r = int(radius // self.ZELLE) + 1
        cx, cy = int(pos.x // self.ZELLE), int(pos.y // self.ZELLE)
        for gy in range(cy - r, cy + r + 1):
            for gx in range(cx - r, cx + r + 1):
                for w in self._raster.get((gx, gy, ebene), ()):
                    yield w

    def treffer(self, pos: pygame.Vector2, radius: float, ebene: int, feind_von: str):
        """Naechstes lebendes Ziel einer anderen Fraktion im Kreis."""
        bestes, beste_d = None, 1e18
        for w in self.nahe(pos, radius + 24, ebene):
            if not w.lebt or w.fraktion == feind_von or w.leben <= 0:
                continue
            d = pos.distance_squared_to(w.pos)
            grenze = (radius + w.radius) ** 2
            if d < grenze and d < beste_d:
                bestes, beste_d = w, d
        return bestes

    # ---- Kollision ----------------------------------------------------
    def frei(self, pos: pygame.Vector2, radius: float, ebene: int,
             loch_fest: bool = False) -> bool:
        """loch_fest: Loecher zaehlen als Wand. Fuer alles, was nicht fallen soll."""
        e = self.ebene(ebene)
        t0x = int((pos.x - radius) // K.TILE)
        t1x = int((pos.x + radius) // K.TILE)
        t0y = int((pos.y - radius) // K.TILE)
        t1y = int((pos.y + radius) // K.TILE)
        for ty in range(t0y, t1y + 1):
            for tx in range(t0x, t1x + 1):
                if not (e.fest(tx, ty) or (loch_fest and e.loch(tx, ty))):
                    continue
                nx = max(tx * K.TILE, min(pos.x, tx * K.TILE + K.TILE))
                ny = max(ty * K.TILE, min(pos.y, ty * K.TILE + K.TILE))
                if (pos.x - nx) ** 2 + (pos.y - ny) ** 2 < radius * radius:
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
        fest_w = not getattr(wesen, "schiebbar", True)
        for a in self.nahe(wesen.pos, wesen.radius * 2, wesen.ebene):
            if a is wesen or not a.schiebt or getattr(a, "am_boden", False):
                continue
            fest_a = not getattr(a, "schiebbar", True)
            if fest_w and fest_a:
                continue
            d = wesen.pos - a.pos
            abstand = d.length()
            mindest = wesen.radius + a.radius
            if 0.0001 < abstand < mindest:
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
        """Erster Punkt auf der Linie, an dem etwas im Weg steht."""
        e = self.ebene(ebene)
        schritte = max(1, int(laenge / (K.TILE * 0.4)))
        for i in range(1, schritte + 1):
            p = von + richtung * (laenge * i / schritte)
            if e.sichtdicht(int(p.x // K.TILE), int(p.y // K.TILE)):
                return von + richtung * (laenge * (i - 1) / schritte)
        return von + richtung * laenge

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
        e = self.ebene(ebene)
        T = float(K.TILE)
        x0, y0 = von.x / T, von.y / T
        x1, y1 = nach.x / T, nach.y / T
        dx, dy = x1 - x0, y1 - y0
        if dx * dx + dy * dy < (1.0 / T) ** 2:
            return True
        tx, ty = int(math.floor(x0)), int(math.floor(y0))
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
        while min(tmx, tmy) <= 1.0:
            if abs(tmx - tmy) < 1e-9:
                if e.sichtdicht(tx + sx, ty) or e.sichtdicht(tx, ty + sy):
                    return False
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
            if e.sichtdicht(tx, ty):
                return False
        return True

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

    def ebene_wechseln(self, wesen, ziel: int, loch_fest: bool = False) -> bool:
        """Wechselt die Ebene, wenn der Platz dort frei ist.

        loch_fest: auch Loecher zaehlen als belegt. Fuer Gegner - sie laufen
        nie in ein Loch; wer oben halb ueber dem Nichts ankaeme, kaeme
        dort nicht mehr weg. Ein Gegner, dem es noch nicht passt, geht
        weiter zur Mitte der Treppe und versucht es dort.
        """
        if self.aufzug_unter(wesen) is not None:
            raus = self.aufzug_ausgang(wesen, ziel)
            if raus is None:
                return False
            wesen.ebene = ziel
            wesen.pos.update(raus)
            wesen.vorher.update(raus)
            return True
        alt = wesen.ebene
        wesen.ebene = ziel
        if self.frei(wesen.pos, wesen.radius, ziel, loch_fest):
            wesen.vorher.update(wesen.pos)
            return True
        wesen.ebene = alt
        return False

    # ---- Aufzug (seit 0.32.11) ------------------------------------------
    def aufzug_unter(self, wesen) -> int | None:
        """Zielebene, wenn das Wesen in einer Aufzugkachel steht."""
        e = self.ebene(wesen.ebene)
        rel = e.daten(int(wesen.pos.x // K.TILE),
                      int(wesen.pos.y // K.TILE)).get("aufzug")
        if rel is None:
            return None
        ziel = wesen.ebene + rel
        return ziel if 0 <= ziel < len(self.ebenen) else None

    def aufzug_ausgang(self, wesen, ziel: int):
        """Wo man nach dem Aufzug steht, oder None.

        Eine Kachel weiter, in die Richtung, in die man lief - und zwar
        als Verschiebung, nicht auf die Kachelmitte: wer am oberen Rand
        der Tuer hineinging, kommt am oberen Rand heraus. Zusammen mit
        der Ueberblendung (render.Ueberblendung) und der mitgeschobenen
        Kamera sieht das aus wie ein Schritt durch die Tuer.

        In Frage kommen nur die vier Nachbarn der Gegenstelle, die Boden
        sind - kein Loch, keine Wand und kein Aufzug, sonst fuehre man
        sofort zurueck. Gibt es keinen, bleibt man, wo man ist.
        """
        e = self.ebene(ziel)
        tx, ty = int(wesen.pos.x // K.TILE), int(wesen.pos.y // K.TILE)
        lauf = pygame.Vector2(getattr(wesen, "tempo", (0, 0)))
        if lauf.length_squared() < 1.0:
            lauf = pygame.Vector2(1, 0).rotate(getattr(wesen, "winkel", 0.0))
        bester, beste_guete = None, -9.0
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = tx + dx, ty + dy
            if (not e.begehbar(nx, ny) or e.loch(nx, ny)
                    or e.daten(nx, ny).get("aufzug") is not None):
                continue
            richtung = pygame.Vector2(dx, dy)
            for p in (wesen.pos + richtung * K.TILE,
                      pygame.Vector2((nx + 0.5) * K.TILE, (ny + 0.5) * K.TILE)):
                if (int(p.x // K.TILE), int(p.y // K.TILE)) != (nx, ny):
                    continue
                if self.frei(p, wesen.radius, ziel, loch_fest=True):
                    guete = richtung.dot(lauf.normalize())
                    if guete > beste_guete:
                        bester, beste_guete = pygame.Vector2(p), guete
                    break
        return bester

    def aufzug_pruefen(self, wesen) -> bool:
        """Wer in einen Aufzug hineinlaeuft, faehrt - ohne Taste.

        Nur, wer selbst laeuft: kein Sturz, kein Liegender, kein Boss.
        Gegner fahren gar nicht von hier aus (`faehrt_aufzug` False):
        sie nehmen den Aufzug wie eine Treppe in `_treppe_ansteuern`,
        wenn er auf ihrem Weg liegt.
        """
        if (not getattr(wesen, "faehrt_aufzug", False) or wesen.flug > 0
                or getattr(wesen, "am_boden", False)
                or getattr(wesen, "ist_boss", False)):
            return False
        ziel = self.aufzug_unter(wesen)
        if ziel is None:
            return False
        return self.ebene_wechseln(wesen, ziel, loch_fest=True)


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
