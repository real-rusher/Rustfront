"""
DUSTFRONT - Wesen
=================

Alles, was sich bewegt. Ein Wesen hat eine Ebene, einen Kreis als Koerper und
zwei Positionen: die aktuelle und die vom Schritt davor. Gezeichnet wird
dazwischen interpoliert, deshalb laeuft das Bild auch bei 144 Hz fluessig,
obwohl die Simulation mit festen 120 Schritten rechnet.

Waffen sind keine Klassen, sondern Eintraege in config.WAFFEN. Eine neue Waffe
ist eine Zeile Daten.
"""

from __future__ import annotations

import math
import random

import pygame

from . import config as K
from .core import naehern

RND = random.Random(20260913)


# ══════════════════════════════════════════════════════════════════
# Grundlage
# ══════════════════════════════════════════════════════════════════

class Wesen:
    fraktion = "neutral"
    # Hoehe ueber dem Boden fuer die Frage, ob eine Mauer es verdeckt
    # (K.HOEHEN, render.Renderer.verdeckt). 0: steht oder liegt am Boden
    # und wird mit den Figuren gezeichnet, vor den Mauern.
    hoehe_bild = 0.0
    schiebt = True
    trefferbar = True
    bild = None
    spur = None              # Farbe der Leuchtspur, None = keine
    radius = 8.0
    max_leben = 1.0
    schatten = True
    faellt = False           # True = kann in Loecher stuerzen
    # Wie hoch das Bild in Perspektive steht (K.FIGUREN_3D, seit 0.34.25).
    # 0: flach. Seit 0.34.34 sind alle Figuren - Spieler, Bots, Gegner -
    # wieder flach (gemeldet: "Entfern mal das 3D-Rendering bei Figuren,
    # das ist doch nicht so gut"); Hoehe haben nur noch Buggy und Beute.
    hoehe_3d = 0.0
    # Zustaende (seit 0.34.66, zustand_setzen): betaeubt (Schockstab) und
    # gefroren (Schneeball) laehmen ganz - kein Laufen, kein Schiessen,
    # kein Schlagen; fest (Nagler, Kettensaege) haelt nur am Ort.
    betaeubt_rest = 0.0
    gefroren_rest = 0.0
    fest_rest = 0.0

    # Eine laufende Nummer je Wesen. Gebraucht wird sie vom Gast: er
    # bekommt sechzigmal in der Sekunde eine Liste fliegender Dinge und
    # konnte bisher nicht sagen, welcher Punkt darin dieselbe Granate ist
    # wie im Paket davor. Also zeichnete er jedes Paket neu an die
    # gemeldete Stelle - bei 300 Bildern und 60 Paketen fuenf gleiche
    # Bilder, dann ein Sprung. Genau das sah aus wie "die Granate ist
    # woanders gelandet". Mit der Nummer laesst sich dazwischen
    # weiterzeichnen.
    _naechste_kennung = 0

    def __init__(self, pos, ebene: int = 0) -> None:
        Wesen._naechste_kennung += 1
        self.kennung = Wesen._naechste_kennung
        self.pos = pygame.Vector2(pos)
        self.vorher = pygame.Vector2(pos)
        self.tempo = pygame.Vector2(0, 0)
        self.ebene = ebene
        self.winkel = 0.0
        self.leben = self.max_leben
        self.lebt = True
        self.blitz = 0.0
        self.welt = None
        self.flug = 0.0          # Hoehe ueber dem eigenen Boden, waehrend eines Sturzes
        self.sturz_rest = 0.0
        self.sturz_dauer = 0.0
        self.sturz_hoehe = 0.0
        self.sturz_ziel = None   # freier Platz, falls es unter uns eng ist

    # ---- Ablauf ------------------------------------------------------
    def schritt(self, dt: float) -> None:
        self.vorher.update(self.pos)
        if self.blitz > 0:
            self.blitz -= dt
        if self.sturz_rest > 0:
            self.sturz_schritt(dt)
        if self.betaeubt_rest > 0.0 or self.gefroren_rest > 0.0 or self.fest_rest > 0.0:
            self.betaeubt_rest = max(0.0, self.betaeubt_rest - dt)
            self.gefroren_rest = max(0.0, self.gefroren_rest - dt)
            self.fest_rest = max(0.0, self.fest_rest - dt)

    @property
    def gelaehmt(self) -> bool:
        """Betaeubt oder gefroren: tut gar nichts (seit 0.34.66)."""
        return self.betaeubt_rest > 0.0 or self.gefroren_rest > 0.0

    @property
    def gehalten(self) -> bool:
        """Kommt nicht vom Fleck: gelaehmt oder festgenagelt."""
        return self.gelaehmt or self.fest_rest > 0.0

    # ---- Sturz --------------------------------------------------------
    def stuerzen(self) -> None:
        """Faellt bis auf die naechste Ebene, die hier wirklich Boden hat.

        Ist die Stelle auch eine Ebene tiefer noch ein Loch, geht es weiter
        nach unten. Von Ebene 2 bis auf den Boden ist das ein einziger Sturz
        und kein Zwischenaufsetzen.
        """
        w = self.welt
        ziel = w.boden_unter(self.pos, self.ebene)
        dz = max(1.0, w.hoehe(self.ebene) - w.hoehe(ziel))
        # Die Figur bleibt stehen, wo sie ist, und faellt von dort. Frueher
        # sprang sie hier sofort auf den spaeteren Landeplatz - seitlich und,
        # ueber flug, auch nach oben. Das war der Ruck beim Absprung. Wo sie
        # aufkommt, entscheidet sich jetzt erst beim Aufschlag.
        self.ebene = ziel
        self.flug = dz
        self.sturz_hoehe = dz
        # Steht unter dem Loch etwas im Weg, wird der Ausweichplatz jetzt
        # schon gesucht: die Figur rutscht waehrend des Fluges dorthin ab,
        # statt im letzten Bild dorthin gesetzt zu werden.
        self.sturz_ziel = None
        if not w.frei(self.pos, self.radius, ziel):
            frei_bei = w.landeplatz(self.pos, self.radius, ziel)
            if frei_bei.distance_to(self.pos) > 0.5:
                self.sturz_ziel = frei_bei
        # freier Fall: die Dauer folgt der Hoehe, nicht einer festen Zahl
        self.sturz_dauer = math.sqrt(2.0 * dz / K.STURZ["schwerkraft"])
        self.sturz_rest = self.sturz_dauer
        self.tempo *= 0.7

    def sturz_schritt(self, dt: float) -> None:
        self.sturz_rest -= dt
        t = max(0.0, self.sturz_dauer - self.sturz_rest)
        self.flug = max(0.0, self.sturz_hoehe
                        - 0.5 * K.STURZ["schwerkraft"] * t * t)
        if self.sturz_ziel is not None:
            if self.welt.frei(self.pos, self.radius, self.ebene):
                # Freier Grund erreicht. Ab hier gehoert die Bewegung wieder
                # dem Spieler: das Abrutschen ist schneller als die
                # Luftsteuerung und wuerde sie sonst bis zur Landung
                # ueberstimmen.
                self.sturz_ziel = None
            else:
                # Am Hindernis abrutschen. Direkt an der Position, nicht
                # ueber welt.bewegen: wer in einer Wand haengt, kaeme dort
                # nie heraus.
                self.pos.move_towards_ip(self.sturz_ziel,
                                         K.STURZ["abrutschen"] * dt)
        if self.sturz_rest <= 0:
            self.flug = 0.0
            self.sturz_ziel = None
            self.aufschlag()

    def aufschlag(self) -> None:
        """Aufsetzen: Staub, Ring, Schlag, Ton - und dann erst der Schaden.

        Ein Sturz ueber zwei Etagen war vorher fast nicht zu bemerken: ein
        bisschen Staub, ein bisschen Schaden, kein Ton. Jetzt haengt alles
        an der Fallhoehe, damit sich ein Sprung von der obersten Ebene
        anders anfuehlt als ein Schritt ueber eine Kante.
        """
        h = self.sturz_hoehe
        self.sturz_hoehe = 0.0
        # Erst jetzt zaehlt der Boden wieder. Steht an der Stelle etwas im
        # Weg, wird die naechste freie daneben genommen; vorher war der Flug
        # ungebremst, damit niemand mitten in der Luft an einer Wand haengt,
        # die eine Etage tiefer steht.
        self.pos.update(self.welt.landeplatz(self.pos, self.radius, self.ebene))
        self.vorher.update(self.pos)
        st = K.STURZ
        schaden = max(st["min_schaden"], h / 100.0 * st["schaden_je_100"])
        w = self.welt
        wucht = min(1.0, h / 240.0)
        wolke(w, self.pos, int(st["staub"] * (0.5 + 0.5 * wucht)),
              130 + 90 * wucht, 0.5, K.C_MUTED_DK, self.ebene, 1, "staub")
        w.ruckeln(st["ruckeln"] + h * 0.035, "sturz", self.pos, self.ebene,
                  self)
        w.aufschlagring(self.pos, self.ebene, wucht)
        w.klang("sturz", 0.55 + 0.45 * wucht, self.pos, self.ebene)
        if hasattr(self, "zaehlen"):
            self.zaehlen("stuerze")
        self.schaden(schaden, None, None)

    def zeichenpos(self, alpha: float) -> pygame.Vector2:
        # Fest gesetzt fuer ein Bild (seit 0.34.95): wem die Kamera folgt,
        # der steht ruhig im Bild (render.Kamera.fest_im_bild).
        fest = self.__dict__.get("_zeichen_fest")
        if fest is not None:
            return pygame.Vector2(fest)
        return self.vorher.lerp(self.pos, alpha)

    # ---- Schaden -----------------------------------------------------
    def schaden(self, menge: float, schub: pygame.Vector2 | None = None,
                von=None) -> None:
        if not self.lebt or self.leben <= 0:
            return
        stand_vorher = not getattr(self, "am_boden", False)
        # Nur der Schaden, der wirklich angekommen ist. Wer einen mit
        # 3 Leben mit einer Granate erwischt, hat 3 Schaden gemacht und
        # nicht 78 - sonst sagt die Zahl nichts.
        angekommen = min(float(menge), max(0.0, self.leben))
        self.leben -= menge
        self.blitz = K.TREFFER["blitz"]
        if schub is not None:
            self.tempo += schub
        if angekommen > 0:
            if hasattr(von, "zaehlen") and von is not self:
                von.zaehlen("schaden", angekommen)
            if hasattr(self, "zaehlen"):
                self.zaehlen("schaden_ein", angekommen)
        if self.leben <= 0:
            self.sterben(von)
        # Das Trefferzeichen des Schuetzen (seit 0.34.15). Nicht fuer sich
        # selbst und nicht fuer die eigenen Leute - eine Rueckmeldung fuer
        # den Granatwurf ins eigene Team waere eine Belohnung dafuer.
        melden = getattr(von, "treffer_melden", None)
        if (angekommen > 0 and melden is not None and von is not self
                and getattr(von, "fraktion", None) != self.fraktion):
            umgeworfen = stand_vorher and (not self.lebt
                                          or getattr(self, "am_boden", False))
            melden(self, umgeworfen)

    def sterben(self, von=None) -> None:
        self.lebt = False


# ══════════════════════════════════════════════════════════════════
# Partikel
# ══════════════════════════════════════════════════════════════════

class Partikel:
    __slots__ = ("pos", "vorher", "tempo", "leben", "dauer", "art", "farbe",
                 "groesse", "reibung", "ebene", "lebt", "dreh", "winkel")

    def __init__(self, pos, tempo, dauer, farbe, groesse=1, art="staub",
                 reibung=3.0, ebene=0) -> None:
        self.pos = pygame.Vector2(pos)
        self.vorher = pygame.Vector2(pos)
        self.tempo = pygame.Vector2(tempo)
        self.leben = self.dauer = dauer
        self.farbe = farbe
        self.groesse = groesse
        self.art = art
        self.reibung = reibung
        self.ebene = ebene
        self.lebt = True
        self.winkel = RND.uniform(0, 360)
        self.dreh = RND.uniform(-600, 600)

    def schritt(self, dt: float) -> None:
        self.vorher.update(self.pos)
        self.pos += self.tempo * dt
        self.tempo *= max(0.0, 1.0 - self.reibung * dt)
        self.winkel += self.dreh * dt
        self.leben -= dt
        if self.leben <= 0:
            self.lebt = False

    def zeichenpos(self, alpha: float) -> pygame.Vector2:
        return self.vorher.lerp(self.pos, alpha)


_WERTE_ARTEN: list = [None, None]


def _werte_arten() -> dict:
    """{Schluessel: Art} aus K.WERTE, einmal gebaut (seit 0.34.75) - die
    Anzeige fragt werte_runde jedes Bild fuer jeden Kaempfer."""
    if _WERTE_ARTEN[0] is not K.WERTE:
        _WERTE_ARTEN[0] = K.WERTE
        _WERTE_ARTEN[1] = {s: a for s, _t, a in K.WERTE}
    return _WERTE_ARTEN[1]


def wolke(welt, pos, anzahl, tempo, dauer, farbe, ebene, groesse=1,
          art="staub", streuung=360.0, richtung=0.0, reibung=3.0):
    for _ in range(anzahl):
        a = math.radians(richtung + RND.uniform(-streuung / 2, streuung / 2))
        v = RND.uniform(tempo * 0.35, tempo)
        welt.partikel.append(Partikel(
            pos, (math.cos(a) * v, math.sin(a) * v),
            dauer * RND.uniform(0.6, 1.2), farbe, groesse, art, reibung, ebene))


# ══════════════════════════════════════════════════════════════════
# Der Tod (seit 0.34.33)
# ══════════════════════════════════════════════════════════════════

def tod_blut(w) -> str:
    """Das Blut eines Wesens aus K.TOD["wesen"]: Gegner nach ihrer Art,
    alle Figuren (Spieler, Bots) als "spieler"."""
    t = K.TOD["wesen"]
    art = getattr(w, "art", None)
    if art in t:
        return t[art]
    if isinstance(w, Spieler):
        return t["spieler"]
    return t.get("laeufer", "zombie")


def tod_zeigen(w, von=None) -> None:
    """Ein Wesen ist gestorben: Fleck, Spritzer und Todeslaut (Welt.tod).
    Die Spritzer fliegen vom Toeter weg, ohne Toeter in Blickrichtung."""
    welt = w.welt
    if welt is None:
        return
    weg = None
    quelle = getattr(von, "von", von)        # bei einem Geschoss der Schuetze
    if quelle is not None and hasattr(quelle, "pos"):
        weg = w.pos - quelle.pos
    if weg is None or weg.length_squared() < 1.0:
        weg = pygame.Vector2(1, 0).rotate(w.winkel)
    welt.tod(w.pos, w.ebene, tod_blut(w), float(getattr(w, "radius", 9.0)),
             math.degrees(math.atan2(weg.y, weg.x)))


def daten_faktor(geschoss) -> float:
    """Wie viel mehr eine Waffe mit `flak` gegen Luftziele wiegt (K.FLAK luft_faktor,
    seit 0.34.118 nicht mehr gesetzt: die Flakgranate platzt, siehe fahrzeug.Flakgranate)."""
    return float(getattr(K, "FLAK", {}).get("luft_faktor", 1.0))


def abschuss_buchen(von, ziel, waffe: str, lebte: bool) -> None:
    """Hat dieser Treffer `ziel` getoetet? Dann beim Schuetzen buchen.

    Je Waffe als "abschuesse" (die Spalte gab es in der Statistik schon
    lange, gezaehlt hatte sie nie jemand), und bei Zombies und Bossen als
    eigene Zahl. Spieler zaehlt das Gefecht selbst - dort entscheidet
    erst das Ende der Bodenzeit, ob einer wirklich gefallen ist.
    """
    if not hasattr(von, "zaehlen"):
        return
    if hasattr(ziel, "toeter_waffe"):
        # Ein Kaempfer im Gefecht: er faellt erst um und stirbt spaeter.
        # Hier nur die Waffe merken, mit der er umgeworfen wurde; gebucht
        # wird beim Abrechnen (Gefecht._tote_abrechnen), einmal je Tod.
        if lebte and ziel.toeter is von and not ziel.toeter_waffe:
            ziel.toeter_waffe = waffe
        return
    if not lebte or ziel.lebt:
        return
    von.zaehlen("abschuesse", 1.0, waffe)
    if isinstance(ziel, Gegner) and not getattr(ziel, "ist_puppe", False):
        von.zaehlen("gegner_abschuesse")
        if getattr(ziel, "ist_boss", False):
            von.zaehlen("boss_abschuesse")


def schaden_an(ziel, menge, schub=None, von=None, art=None, herkunft=None,
               fahrzeug_menge=None, waffe=None) -> None:
    """Ein Treffer mit Schadensart (seit 0.34.65, K.PANZERUNG).

    Nur Fahrzeuge (`ist_fahrzeug`) fragen nach der Art und danach, woher
    der Treffer kam; alles andere bekommt `menge` wie bisher. Darum geht
    jeder Treffer, der einen Wagen treffen kann, hier durch - und die
    Wesen selbst brauchen keine neue Unterschrift. `fahrzeug_menge`
    ersetzt `menge` am Blech (Haftladung)."""
    if getattr(ziel, "ist_fahrzeug", False):
        m = menge if fahrzeug_menge is None else fahrzeug_menge
        # Die Klassen (seit 0.34.73): Pionier und Panzerjaeger treffen Blech
        # haerter; wer als Fahrer drinsitzt, schuetzt sein Fahrzeug.
        m *= getattr(von, "fahrzeug_bonus", 1.0)
        m *= getattr(getattr(ziel, "fahrer", None), "fahrzeug_schutz", 1.0)
        ziel.schaden(m, schub, von, art=art, herkunft=herkunft)
    else:
        if art == "feuer":
            menge *= getattr(ziel, "feuer_schutz", 1.0)   # Flammentrupp (0.34.73)
        if getattr(ziel, "schild", False):
            # Was durchs Schild geht (seit 0.34.86, K.SCHILD "durchschlag").
            s = K.SCHILD
            durch = float(s["durchschlag"].get(waffe or "", 0.0))
            if art == "panzerbrechend":
                durch = max(durch, s["panzerbrechend"])
            ziel.schaden(menge, schub, von, durch=durch)
            return
        ziel.schaden(menge, schub, von)


def zustand_setzen(ziel, art: str, dauer: float) -> None:
    """Betaeubt, gefroren oder fest (seit 0.34.66). Fahrzeuge kennen das
    nicht (die haben den EMP), Bosse halten nur die Haelfte aus - sonst
    waere ein Schockstab das Ende jedes Bosskampfs."""
    if getattr(ziel, "ist_fahrzeug", False) or not getattr(ziel, "lebt", False):
        return
    if getattr(ziel, "ist_boss", False):
        dauer *= K.ZUSTAENDE["boss_anteil"]
    name = art + "_rest"
    setattr(ziel, name, max(getattr(ziel, name, 0.0), float(dauer)))


def treffer_ziel_buchen(von, ziel) -> None:
    """Ein Treffer, getrennt danach, ob er einen Spieler oder einen Zombie traf."""
    if not hasattr(von, "zaehlen"):
        return
    if isinstance(ziel, Spieler):
        von.zaehlen("treffer_spieler")
    elif isinstance(ziel, Gegner) and not getattr(ziel, "ist_puppe", False):
        von.zaehlen("treffer_gegner")


# ══════════════════════════════════════════════════════════════════
# Geschoss
# ══════════════════════════════════════════════════════════════════

class Geschoss(Wesen):
    fraktion = "geschoss"
    hoehe_bild = K.HOEHEN["lauf"]   # fliegt in Laufhoehe
    schiebt = False
    trefferbar = False
    schatten = False
    bild = "geschoss"
    spur = (250, 206, 128)
    radius = 2.0
    # Das Fahrzeug, aus dem geschossen wurde (seit 0.34.59): das Ring-MG
    # des Panzerwagens schiesst ueber das eigene Dach, und die Kugel soll
    # nicht im eigenen Blech stecken bleiben.
    traeger = None

    def __init__(self, pos, richtung: float, daten: dict, ebene: int,
                 von=None, waffe: str = "") -> None:
        super().__init__(pos, ebene)
        self.winkel = richtung
        r = math.radians(richtung)
        self.tempo = pygame.Vector2(math.cos(r), math.sin(r)) * daten["tempo"]
        self.schaden_wert = daten["schaden"]
        # Gegen Blech ein anderer Wert (seit 0.34.73, die Panzerbuechse).
        self.fahrzeug_wert = daten.get("fahrzeug_schaden")
        self.rest = daten["reichweite"]
        self.von = von
        # Wer im Beiwagen eines Krads schiesst (seit 0.34.107), trifft nicht
        # das eigene Fahrzeug.
        if von is not None and self.traeger is None:
            self.traeger = getattr(von, "mitfahrt", None)
        # Auf ein Luftziel gezielt (seit 0.34.113, luft.py): die Kugel geht am
        # Boden entlang und trifft nur dieses Ziel (und Mauern).
        self.luft_ziel = getattr(von, "luft_ziel", None) if von is not None else None
        self.flak = bool(daten.get("flak"))
        # Der Stoss auf das Ziel gilt je Schuss, nicht je Kugel: vorher
        # schob jede der sieben Schrotkugeln einzeln, und aus naechster
        # Naehe flog ein Getroffener rund 240 Pixel weit (0.32).
        self.schub_anteil = 1.0 / max(1, int(daten.get("geschosse", 1)))
        # Womit geschossen wurde, muss das Geschoss selbst wissen: beim
        # Einschlag kann der Schuetze laengst die Waffe gewechselt haben,
        # und dann landete der Treffer bei der falschen.
        self.waffe = waffe
        self.quelle_fraktion = von.fraktion if von else "neutral"
        # Treffer-Rueckrechnung (seit 0.34.105): die Kugel eines Gasts trifft,
        # wo die Ziele standen, als er sie sah (Gefecht setzt `rueck`).
        self.rueck = float(getattr(von, "rueck", 0.0) or 0.0) if von is not None else 0.0
        # Was die Waffe am Geschoss besonders macht (seit 0.34.62, siehe
        # K.WAFFEN): Schadensabfall, Durchschlag, Stoss, Blech.
        self.reichweite = float(daten["reichweite"])
        self.abfall_ab = daten.get("abfall_ab")
        self.abfall_rest = float(daten.get("abfall_rest", 1.0))
        self.durch = int(daten.get("durchschlag", 0))
        self.durch_deckung = bool(daten.get("durch_deckung", False))
        # Seit 0.34.96 (Panzerbuechse): nach dem ersten Hindernis - Mauer
        # oder Panzerung - noch so viele Pixel weiter, durch alles hindurch,
        # danach ist Schluss. Getroffen wird also nur, was dicht hinter dem
        # Hindernis steht.
        self.durchdringen = float(daten.get("durchdringen", 0.0))
        self._eindringen = None
        self.gegen_fahrzeug = bool(daten.get("gegen_fahrzeug", False))
        # Der Nagler (seit 0.34.66): ein Nagel statt einer Leuchtspur, und
        # wer vor einer Wand getroffen wird, haengt fest.
        self.nagelt = bool(daten.get("nagelt", False))
        # Der Spiegellaser (seit 0.34.68): so oft prallt er noch ab.
        self.abprall = int(daten.get("abprall", 0))
        self.abprall_faktor = float(daten.get("abprall_faktor", 1.0))
        if daten.get("bild_flug"):
            self.bild = daten["bild_flug"]
            self.spur = None
        # Welche Zeile von K.PANZERUNG gilt (seit 0.34.65).
        self.schadensart = daten.get("schadensart") or (
            "panzerbrechend" if self.gegen_fahrzeug else "kugel")
        self.stoss = float(daten.get("stoss", 1.0))
        self._durch_wen: list = []

    def schaden_jetzt(self) -> float:
        """Der Schaden auf der Strecke, die das Geschoss schon flog: ab
        `abfall_ab` linear weniger, bis `abfall_rest` am Ende (die MP)."""
        if self.abfall_ab is None:
            return self.schaden_wert
        weit = self.reichweite - self.rest
        if weit <= self.abfall_ab:
            return self.schaden_wert
        f = min(1.0, (weit - self.abfall_ab) / max(1.0, self.reichweite - self.abfall_ab))
        return self.schaden_wert * (1.0 - (1.0 - self.abfall_rest) * f)

    def schritt(self, dt: float) -> None:
        self.vorher.update(self.pos)
        weg = self.tempo * dt
        strecke = weg.length()
        if strecke <= 0:
            return
        # Unterteilen, damit nichts durch Waende oder Gegner fliegt
        schritte = max(1, int(strecke / 6.0))
        teil = weg / schritte
        for _ in range(schritte):
            self.pos += teil
            self.rest -= teil.length()
            lz = self.luft_ziel
            if lz is not None:
                ziel = None            # am Boden trifft sie nichts, sie geht darueber
                if lz.lebt and self.pos.distance_to(lz.jetzt) <= lz.radius + K.LUFT_ZIELEN["treffer_extra"]:
                    self.lebt = False
                    lz.treffen(self.schaden_jetzt() * (daten_faktor(self) if self.flak else 1.0),
                               self.von)
                    return
            else:
                ziel = self.welt.treffer(self.pos, self.radius, self.ebene,
                                         self.quelle_fraktion, self.rueck)
            if self._eindringen is not None:
                self._eindringen -= teil.length()
                if self._eindringen <= 0.0:
                    # Die Kraft ist verbraucht: steckt sie in der Mauer, ist
                    # es ein Einschlag dort, sonst faellt sie einfach.
                    if self.welt.schuss_halt(self.pos, self.ebene, self.radius, True):
                        self.einschlag(None)
                    else:
                        self.lebt = False
                    return
            if (ziel is not None and ziel is not self.von and ziel is not self.traeger
                    and ziel not in self._durch_wen):
                if self.durchdringen > 0.0 and getattr(ziel, "ist_fahrzeug", False):
                    # Durch die Panzerung (seit 0.34.96): der Wagen bekommt den
                    # Treffer, und die Kugel fliegt noch ein Stueck weiter.
                    self._durch_wen.append(ziel)
                    self.treffen(ziel)
                    if self._eindringen is None:
                        self._eindringen = self.durchdringen
                    continue
                if self.durch > 0 and not getattr(ziel, "rechteckig", False):
                    # Durchschlag (seit 0.34.62): treffen und weiterfliegen.
                    # Jeden nur einmal - sonst traefe sie ihn in jedem
                    # Teilschritt, solange sie in ihm steckt.
                    self.durch -= 1
                    self._durch_wen.append(ziel)
                    self.treffen(ziel)
                    continue
                self.einschlag(ziel)
                return
            # Jede feste Kachel haelt die Kugel auf (seit 0.34.26) - die
            # Panzerbuechse nur eine Mauer (seit 0.34.62).
            if self.welt.schuss_halt(self.pos, self.ebene, self.radius,
                                     self.durch_deckung):
                if self.durchdringen > 0.0:
                    if self._eindringen is None:
                        self._eindringen = self.durchdringen
                        wolke(self.welt, self.pos, 6, 160, 0.2, (232, 196, 140), self.ebene,
                              1, "funke", 120, self.winkel + 180, 6.0)
                    continue
                self.pos -= teil
                if self.abprall > 0:
                    self._abprallen(teil)
                    return
                self.einschlag(None)
                return
            if self.rest <= 0:
                self.lebt = False
                return

    def _abprallen(self, teil) -> None:
        """An der Wand gespiegelt: welche Achse stoesst an, die kehrt um.
        Mit jedem Abprall staerker (Waffenpaket, SPIEGELLASER)."""
        w = self.welt
        x_stoesst = w.schuss_halt(self.pos + pygame.Vector2(teil.x, 0), self.ebene, self.radius)
        y_stoesst = w.schuss_halt(self.pos + pygame.Vector2(0, teil.y), self.ebene, self.radius)
        if x_stoesst or not y_stoesst:
            self.tempo.x = -self.tempo.x
        if y_stoesst or not x_stoesst:
            self.tempo.y = -self.tempo.y
        self.abprall -= 1
        self.schaden_wert *= self.abprall_faktor
        self.winkel = math.degrees(math.atan2(self.tempo.y, self.tempo.x))
        self._durch_wen = []
        wolke(w, self.pos, 6, 120, 0.2, K.ENTLADUNG["tuerkis"], self.ebene, 1, "funke")

    def einschlag(self, ziel) -> None:
        self.lebt = False
        richtung = math.degrees(math.atan2(self.tempo.y, self.tempo.x))
        if ziel is not None:
            self.treffen(ziel)
        else:
            wolke(self.welt, self.pos, 5, 190, 0.18, (232, 196, 140), self.ebene,
                  1, "funke", 130, richtung + 180, 6.0)
            if self.nagelt:
                # Der Nagel bleibt in der Wand stecken (Welt.explosion "nagel":
                # der Radius ist dort die Richtung - so geht sie beim Gast mit).
                self.welt.explosion(self.pos, self.ebene, richtung, "nagel")

    def treffen(self, ziel) -> None:
        """Was ein Treffer anrichtet - beim Einschlag und bei jedem Koerper,
        durch den ein Durchschlag geht (seit 0.34.62 eine eigene Methode)."""
        richtung = math.degrees(math.atan2(self.tempo.y, self.tempo.x))
        schub = None
        if self.tempo.length_squared() > 0.001:
            schub = (pygame.Vector2(self.tempo).normalize()
                     * K.TREFFER["rueckstoss"] * self.schub_anteil * self.stoss)
        # Ein Wagen (seit 0.34.18) ist ein Ziel, aber kein Treffer fuer
        # die Statistik - die zaehlt Spieler und Gegner.
        if hasattr(self.von, "zaehlen") and getattr(ziel, "zaehlt_treffer", True):
            self.von.zaehlen("treffer", 1.0, self.waffe)
            treffer_ziel_buchen(self.von, ziel)
        lebte = ziel.lebt
        menge = self.schaden_jetzt()
        # Am Fahrzeug zaehlt die Art (seit 0.34.65, K.PANZERUNG): eine
        # Kugel zerkratzt den Panzer nur - wer im Turm oder im Ring steht,
        # bekommt seinen Teil aber ganz ab. Die Panzerbuechse geht durchs
        # Blech. Die Herkunft ist der Weg zurueck, den sie gekommen ist.
        art = self.schadensart
        herkunft = None
        if self.tempo.length_squared() > 0.001:
            herkunft = self.pos - pygame.Vector2(self.tempo).normalize() * 40.0
        schaden_an(ziel, menge, schub, self.von, art, herkunft, self.fahrzeug_wert,
                   waffe=self.waffe)
        abschuss_buchen(self.von, ziel, self.waffe, lebte)
        if self.nagelt and ziel.lebt and self.tempo.length_squared() > 0.001:
            z = K.ZUSTAENDE
            hinter = (ziel.pos + pygame.Vector2(self.tempo).normalize()
                      * (getattr(ziel, "radius", 8.0) + z["nagel_wand"]))
            if self.welt.schuss_halt(hinter, ziel.ebene, 2.0):
                zustand_setzen(ziel, "fest", z["genagelt"])
        if getattr(ziel, "treffer_art", "") == "metall":
            wolke(self.welt, self.pos, 5, 170, 0.18, (255, 222, 150), self.ebene,
                  1, "funke", 120, richtung + 180, 5.0)
        else:
            wolke(self.welt, self.pos, 6, 150, 0.22, K.C_BLUT, self.ebene, 1,
                  "blut", 110, richtung, 5.0)
            if self.durch > 0 or self._durch_wen:
                # Der Austritt ist groesser als der Einschuss, in
                # Flugrichtung (Paket: "Einschuss klein, Austritt gross").
                wolke(self.welt, self.pos + pygame.Vector2(6, 0).rotate(richtung), 9,
                      190, 0.3, K.C_BLUT, self.ebene, 2, "blut", 70, richtung, 6.0)


# ══════════════════════════════════════════════════════════════════
# Granate
# ══════════════════════════════════════════════════════════════════

class Granate(Wesen):
    """Fliegt, prallt von Waenden ab und zuendet nach ihrer Flugzeit."""

    fraktion = "geschoss"
    ueber_wasser = True     # fliegt ueber tiefes Wasser (seit 0.34.131)
    schiebt = False
    trefferbar = False
    schatten = True
    radius = 3.0
    bild = "granate"
    # Seit 0.34.67 (Blinken, Knaller, Kuller) - als Klassenwerte, weil die
    # Werfergranate Granate.__init__ nicht durchlaeuft.
    _alter = 0.0
    knallt = 0.0
    _knall_rest = 0.0
    traeger = None
    # Wie der Spieler: Loecher sind fuer sie keine Wand. Ohne das prallte
    # eine Granate an der Kante eines Lochs ab wie an einem Mauerstueck
    # und blieb oben liegen - eine Etage ueber dem, den sie treffen sollte.
    faellt = True

    def __init__(self, pos, richtung: float, daten: dict, ebene: int, von=None,
                 weite: float | None = None) -> None:
        super().__init__(pos, ebene)
        self.daten = daten
        self.von = von
        self.winkel = richtung
        # Das Bild kommt ueber die Skin-Rolle und nicht als fester Name:
        # eine Skin soll spaeter die eigene Blendgranate austauschen
        # koennen, ohne dass hier etwas anders steht.
        if daten.get("rauch"):
            self.bild = "rauchgranate"
        elif daten.get("feuer"):
            self.bild = K.skin("molotov_flug")
        elif daten.get("blend"):
            self.bild = K.skin("blend_flug")
        elif daten.get("haftet"):
            self.bild = "haftladung_flug"
        elif daten.get("emp"):
            self.bild = "emp_flug"
        elif daten.get("bild_flug"):
            self.bild = daten["bild_flug"]       # Gas, Kuller, Knaller (seit 0.34.67)
        else:
            self.bild = "granate"
        # Blinken (seit 0.34.67): das Bild wechselt, darum sieht es auch der
        # Gast - der bekommt nur den Bildnamen.
        self._bild_aus = self.bild
        self._alter = 0.0
        self.knallt = 0.0          # Knaller: so lange macht er noch Laerm
        self._knall_rest = 0.0
        # Haftladung (seit 0.34.65): woran sie klebt, und wo darauf.
        self.traeger = None
        self._versatz = pygame.Vector2(0, 0)
        self.rest = daten["flugzeit"]
        self.dreh = RND.uniform(-700, 700)
        # Anfangstempo so waehlen, dass sie nach der Reibung genau auf der
        # gewuenschten Weite liegen bleibt. Der Weg einer gebremsten Bewegung
        # ist v0 * (1 - e^(-k*t)) / k, das loesen wir nach v0 auf.
        if weite is None:
            weite = daten["wurf_max"]
        # Die Kuller rollt weiter, als gezielt wurde (seit 0.34.87).
        weite *= float(daten.get("ueber_ziel", 1.0))
        k = daten["reibung"]
        anteil = 1.0 - math.exp(-k * self.rest)
        v0 = weite * k / max(0.05, anteil)
        self.tempo = pygame.Vector2(v0, 0).rotate(richtung)

    def schritt(self, dt: float) -> None:
        self.vorher.update(self.pos)
        self.rest -= dt
        self._alter += dt
        d = self.daten
        if d.get("blinkt"):
            self._blinken()
        if self.knallt > 0.0:
            self._knallen(dt)
            return
        if d.get("kuller") and self._alter >= d["scharf_nach"] and self._jemand_nah():
            self.zuenden()
            return
        if self.daten.get("haftet") and self._haften(dt):
            return
        self.winkel += self.dreh * dt
        if self.sturz_rest > 0:
            self.sturz_schritt(dt)
        self.tempo *= max(0.0, 1.0 - self.daten["reibung"] * dt)   # rollt aus
        stoss_x, stoss_y = self.welt.bewegen(self, self.tempo.x * dt,
                                             self.tempo.y * dt)
        if stoss_x:
            self.tempo.x = -self.tempo.x * 0.5
        if stoss_y:
            self.tempo.y = -self.tempo.y * 0.5
        # Ueber die Kante gerollt: sie faellt hinunter wie eine Figur, mit
        # derselben Rechnung. Frueher blieb sie ueber dem Loch in der Luft
        # liegen und zuendete dort, wo unten niemand stand.
        if self.sturz_rest <= 0 and self.welt.loch_unter(self):
            self.stuerzen()
        # Der Zuender wartet, bis sie liegt. Sonst kaeme der Knall auf der
        # Zielebene an, waehrend die Granate im Bild noch in der Luft ist.
        if self.rest <= 0 and self.sturz_rest <= 0:
            self.zuenden()

    def _blinken(self) -> None:
        """Immer schneller, je naeher die Zuendung (Haftladung, EMP)."""
        gesamt = max(0.1, self.daten["flugzeit"])
        rest = max(0.0, self.rest) / gesamt
        takt = 0.12 + 0.6 * rest            # Sekunden je Blinken
        an = (self._alter % takt) < takt * 0.4
        neu = self._bild_aus + "_an" if an else self._bild_aus
        if an and neu != self.bild and self.welt is not None:
            # Bei jedem Aufleuchten ein Piepen (Waffenpaket: "wer beklebt
            # wird, hoert ein Piepen"), seit 0.34.72.
            self.welt.klang("piepen", 0.3, self.pos, self.ebene)
        self.bild = neu

    def _jemand_nah(self) -> bool:
        """Der Kuller: ist jemand ausser dem Werfer und seinen Leuten nahe?"""
        r = self.daten["naehe"]
        eigene = getattr(self.von, "fraktion", None)
        for a in self.welt.nahe(self.pos, r + 30.0, self.ebene):
            if (a is self or a is self.von or not a.lebt
                    or not getattr(a, "trefferbar", False)
                    or getattr(a, "fraktion", "") in ("geschoss", eigene)):
                continue
            if a.pos.distance_to(self.pos) <= r + a.radius:
                return True
        return False

    def _knallen(self, dt: float) -> None:
        """Der Knaller: Knall um Knall, mit Blitz, und Bots hoeren hin.
        Schussknall und Laerm gehen ueber die Welt, also auch zum Gast."""
        d = self.daten
        self.knallt -= dt
        self.tempo.update(0, 0)
        if self.knallt <= 0.0:
            self.lebt = False
            return
        self._knall_rest -= dt
        if self._knall_rest > 0.0:
            return
        self._knall_rest = RND.uniform(*d["knall_takt"])
        w = self.welt
        winkel = RND.uniform(-180, 180)
        w.schussknall(self.pos + pygame.Vector2(4, 0).rotate(winkel), winkel, self.ebene,
                      "knaller", None)
        # Der Knaller huepft dabei ein wenig.
        self.pos += pygame.Vector2(RND.uniform(1.0, 3.0), 0).rotate(winkel)
        if not w.frei(self.pos, self.radius, self.ebene):
            self.pos.update(self.vorher)
        w.laerm(self.pos, self.ebene, None, d["laerm"])

    def _haften(self, dt: float) -> bool:
        """Die Haftladung: klebt sie schon, faehrt sie mit ihrem Traeger und
        zuendet nach ihrer Zeit. Sonst sucht sie, woran sie stoesst - jedes
        trefferbare Wesen ausser dem Werfer. True: der Schritt ist erledigt."""
        w = self.welt
        t = self.traeger
        if t is None:
            for a in w.nahe(self.pos, self.radius + 40.0, self.ebene):
                if (a is self or a is self.von or not a.lebt
                        or not getattr(a, "trefferbar", False)
                        or getattr(a, "fraktion", "") == "geschoss"):
                    continue
                if getattr(a, "ist_fahrzeug", False):
                    if not a.beruehrt(self.pos, self.radius):
                        continue
                elif a.pos.distance_to(self.pos) > a.radius + self.radius:
                    continue
                # Fahrer kleben am Wagen, nicht an sich selbst.
                if getattr(a, "im_fahrzeug", False) and getattr(a, "fahrzeug", None) is not None:
                    a = a.fahrzeug
                self.traeger = t = a
                rel = (self.pos - a.pos) * 0.75
                self._versatz = rel.rotate(-getattr(a, "winkel", 0.0))
                self.tempo.update(0, 0)
                w.klang("klebt", 0.7, self.pos, self.ebene)
                break
            if t is None:
                return False
        if not t.lebt or t.ebene != self.ebene and not getattr(t, "ist_fahrzeug", False):
            # Der Traeger ist weg: sie faellt, wo sie war, und zuendet dort.
            self.traeger = None
            self.tempo.update(0, 0)
            return False
        self.ebene = t.ebene
        self.pos.update(t.pos + self._versatz.rotate(getattr(t, "winkel", 0.0)))
        self.tempo.update(0, 0)
        if self.rest <= 0:
            self.zuenden()
        return True

    def stuerzen(self) -> None:
        """Ueber die Kante: sie fliegt weiter, wie sie geworfen wurde.

        Wesen.stuerzen() nimmt beim Absprung 30 Prozent des Tempos weg -
        fuer eine Figur richtig, die ueber eine Kante stolpert. Eine
        Granate stolpert nicht. Zusammen mit dem harten Abbremsen beim
        Aufsetzen hatte sie gemessen nach der Landung nur noch 25 Prozent
        des Tempos, das sie ohne Sturz gehabt haette, und legte im Flug 71
        Prozent der Strecke zurueck. Gemeldet als: sie verliert beim Fall
        das ganze Momentum.

        Jetzt folgt sie waehrend des Falls derselben Kurve wie jeder
        andere Wurf - dieselbe Reibung, kein Abzug beim Absprung, keiner
        beim Aufsetzen.
        """
        tempo = pygame.Vector2(self.tempo)
        super().stuerzen()
        self.tempo = tempo

    def aufschlag(self) -> None:
        """Aufsetzen nach einem Sturz - ohne Sturzschaden und ohne Bremse.

        Wesen.aufschlag() wuerde der Granate Fallschaden geben. Sie hat
        Leben wie jedes Wesen, waere danach tot und wuerde nie zuenden.
        Das Tempo bleibt: sie rollt weiter, wie sie gerollt waere, wenn
        dort keine Kante gewesen waere.
        """
        self.sturz_hoehe = 0.0
        self.pos.update(self.welt.landeplatz(self.pos, self.radius, self.ebene))
        self.vorher.update(self.pos)
        wolke(self.welt, self.pos, 4, 60, 0.3, K.C_MUTED_DK, self.ebene, 1,
              "staub")

    def zuenden(self) -> None:
        """Zuenden ist zweierlei: Wirkung und Auftritt.

        Die Wirkung - Schaden und Rauchwand - rechnet nur, wer die Welt
        rechnet. Der Auftritt steht in `Welt.explosion` und wird von dort
        aus auch bei jedem Gast nachgespielt; sonst verschwindet bei ihm
        nur das Bild der Granate, ohne Knall und ohne Funken.
        """
        self.lebt = False
        d = self.daten
        w = self.welt
        if d.get("rauch"):
            w.rauch.append(Rauchwolke(self.pos, self.ebene))
            w.explosion(self.pos, self.ebene, 0.0, "rauch")
            return
        if d.get("blend"):
            # Kein Schaden, kein Rueckstoss, keine Mannschaftsfrage: die
            # Blendgranate nimmt eine Sekunde, und sie nimmt sie jedem,
            # der hinsieht. Wer wie stark geblendet ist, rechnet jeder
            # Rechner fuer sich aus der Lage des Blitzes.
            # Der Werfer geht mit: seine Spielerkosmetik bestimmt, wie es
            # klingt und was im Weiss steht (spielerkosmetik.py).
            w.explosion(self.pos, self.ebene, 0.0, "blend", von=self.von)
            return
        if d.get("feuer"):
            # Kein Sprengschaden - das ist der Punkt an dieser Waffe. Die
            # Flaeche entsteht dort, wo die Flasche liegt, und auf der
            # Ebene, auf der sie liegt. Ist sie durch ein Loch gefallen,
            # ist das die untere; dann brennt es eben dort.
            w.feuer.append(Brandflaeche(self.pos, self.ebene, von=self.von))
            w.explosion(self.pos, self.ebene, 0.0, "feuer")
            return
        if d.get("knaller"):
            # Seit 0.34.67: er zuendet nicht, er faengt an zu knallen.
            self.lebt = True
            self.knallt = d["knall_dauer"]
            return
        if d.get("gas"):
            # Seit 0.34.67: eine Gaswolke, die langsam waechst.
            w.gas.append(Gaswolke(self.pos, self.ebene, von=self.von))
            w.klang("gas", 0.7, self.pos, self.ebene)
            return
        if d.get("emp"):
            # Seit 0.34.65: jedes Fahrzeug im Kreis steht still. Kein
            # Schaden, keine Mannschaftsfrage - Elektronik kennt keine.
            e = K.EMP
            for b in list(w.nahe(self.pos, e["radius"] + 80.0, self.ebene)):
                if (getattr(b, "ist_fahrzeug", False) and b.lebt
                        and b.beruehrt(self.pos, e["radius"])):
                    b.emp_treffen(e["dauer"])
                elif (getattr(b, "technik", False) and b.lebt
                      and b.pos.distance_to(self.pos) <= e["radius"] + b.radius):
                    # Geschuetz, Drohne, Horchposten (seit 0.34.69).
                    b.emp_treffen(e["dauer"])
            w.explosion(self.pos, self.ebene, e["radius"], "emp")
            return
        r = d["radius"]
        art = d.get("schadensart", "spreng")
        fz = d.get("fahrzeug_schaden")
        for ziel in list(w.nahe(self.pos, r + 30, self.ebene)):
            if not ziel.lebt or ziel is self:
                continue
            ab = ziel.pos - self.pos
            entfernung = ab.length()
            if entfernung > r + ziel.radius:
                continue
            # volle Wucht in der Mitte, am Rand ein Viertel - hinter
            # Deckung weniger (seit 0.34.26)
            anteil = 1.0 - 0.75 * min(1.0, entfernung / r)
            anteil *= w.deckung_anteil(self.pos, ziel.pos, self.ebene)
            schub = (ab.normalize() * 320 * anteil) if entfernung > 0.01 else None
            lebte = ziel.lebt
            # Klebt sie am Wagen, wirkt sie ganz - auch wenn seine Mitte
            # weiter weg liegt als ihr Kreis.
            if ziel is getattr(self, "traeger", None):
                anteil = 1.0
            schaden_an(ziel, d["schaden"] * anteil, schub, self.von, art, self.pos,
                       None if fz is None else fz * anteil)
            abschuss_buchen(self.von, ziel, getattr(self, "waffe", "granate"), lebte)
        w.explosion(self.pos, self.ebene, r, d.get("explosion", "spreng"))
        w.kurz_langsam(0.05)


class Wurfkoerper(Granate):
    """Was gerade fliegt (seit 0.34.67): Wurfmesser, Speer, Schneeball.

    Kein Bogen, kein Rollen (Waffenpaket, GRUNDREGELN 3): es fliegt mit
    festem Tempo bis zur Weite, trifft den ersten Koerper oder bleibt an
    der Wand liegen. Was `aufheben` hat, liegt danach am Boden, bis es
    jemand mit dieser Waffe aufhebt - nach `K.WURFKOERPER["zurueck"]`
    Sekunden kommt es von selbst zum Werfer zurueck, damit nichts fuer
    immer verloren ist. Der Schneeball zerfaellt."""

    def __init__(self, pos, richtung: float, daten: dict, ebene: int, von=None,
                 weite: float = 200.0, waffe: str = "") -> None:
        Wesen.__init__(self, pos, ebene)
        self.daten = daten
        self.von = von
        self.waffe = waffe
        self.winkel = richtung
        self.bild = daten.get("bild_flug", "granate")
        self._bild_aus = self.bild
        self.traeger = None
        self.knallt = 0.0
        self._alter = 0.0
        self.quelle_fraktion = von.fraktion if von is not None else "neutral"
        tempo = daten.get("wurf_tempo", 450.0)
        self.tempo = pygame.Vector2(tempo, 0).rotate(richtung)
        self.weg = float(weite)
        self.liegt = False
        self.rest = 1e9
        self.dreh = 0.0

    def schritt(self, dt: float) -> None:
        self.vorher.update(self.pos)
        self._alter += dt
        if self.liegt:
            self._liegen()
            return
        w = self.welt
        strecke = self.tempo.length() * dt
        schritte = max(1, int(strecke / 5.0))
        teil = self.tempo * dt / schritte
        for _ in range(schritte):
            self.pos += teil
            self.weg -= teil.length()
            ziel = w.treffer(self.pos, self.radius + 2.0, self.ebene, self.quelle_fraktion)
            if ziel is not None and ziel is not self.von:
                self._treffen(ziel)
                return
            if w.schuss_halt(self.pos, self.ebene, self.radius):
                self.pos -= teil
                self._hinlegen()
                return
            if self.weg <= 0.0:
                self._hinlegen()
                return

    def _treffen(self, ziel) -> None:
        d = self.daten
        menge = d.get("wurf_schaden", d.get("schaden", 0.0))
        schub = pygame.Vector2(self.tempo).normalize() * 90.0
        lebte = ziel.lebt
        if hasattr(self.von, "zaehlen") and getattr(ziel, "zaehlt_treffer", True):
            self.von.zaehlen("treffer", 1.0, self.waffe)
            treffer_ziel_buchen(self.von, ziel)
        schaden_an(ziel, menge, schub, self.von, "nahkampf", self.pos - self.tempo * 0.05)
        abschuss_buchen(self.von, ziel, self.waffe, lebte)
        if d.get("kaelte"):
            self.welt.klang("schneeball", 0.6, self.pos, self.ebene)
            # Der Schneeball: wer oft genug getroffen wird, friert ein.
            jetzt = self.welt.zeit
            if jetzt - getattr(ziel, "_kaelte_zeit", -1e9) > d["kaelte_fenster"]:
                ziel._kaelte = 0
            ziel._kaelte = getattr(ziel, "_kaelte", 0) + d["kaelte"]
            ziel._kaelte_zeit = jetzt
            if ziel._kaelte >= d["kaelte_bis"]:
                ziel._kaelte = 0
                zustand_setzen(ziel, "gefroren", d["gefroren"])
        elif getattr(ziel, "treffer_art", "") != "metall":
            wolke(self.welt, self.pos, 6, 140, 0.22, K.C_BLUT, self.ebene, 1, "blut")
        self._hinlegen()

    def _hinlegen(self) -> None:
        if not self.daten.get("aufheben"):
            # Der Schneeball zerfaellt.
            self.welt.klang("schneeball", 0.4, self.pos, self.ebene)
            wolke(self.welt, self.pos, 8, 80, 0.4, (236, 240, 248), self.ebene, 1, "staub")
            self.lebt = False
            return
        self.liegt = True
        self.tempo.update(0, 0)
        self._alter = 0.0

    def _liegen(self) -> None:
        """Wer diese Waffe traegt und darueber laeuft, hebt es auf."""
        for a in self.welt.nahe(self.pos, 24.0, self.ebene):
            if not getattr(a, "lebt", False) or (
                    self.waffe not in getattr(a, "waffen", ())
                    and getattr(a, "nahkampf_waffe", None) != self.waffe):
                continue
            if getattr(a, "am_boden", False) or a.pos.distance_to(self.pos) > 16.0:
                continue
            if self._zurueck_an(a):
                self.welt.klang("aufheben", 0.6, self.pos, self.ebene)
                return
        if self._alter >= K.WURFKOERPER["zurueck"] and self.von is not None:
            self._zurueck_an(self.von)
            self.lebt = False

    def _zurueck_an(self, wer) -> bool:
        voll = self.daten.get("magazin", 1)
        hat = wer.magazin.get(self.waffe, 0)
        if hat >= voll:
            return False
        wer.magazin[self.waffe] = hat + 1
        self.lebt = False
        return True


class Kugelblitz(Geschoss):
    """Die Energiekugel des Kugelblitzes (seit 0.34.68). Langsam, gut zu
    sehen; alle `zap_takt` Sekunden schlaegt sie Blitze in mehrere
    Richtungen bis an ihre Reichweite (auch ohne Ziel, damit man die
    Reichweite sieht) und trifft alles darin. Am Ende - Wand, Koerper oder
    Reichweite - platzt sie gross (Welt.explosion "plasma")."""

    radius = 6.0

    def __init__(self, pos, richtung: float, daten: dict, ebene: int,
                 von=None, waffe: str = "kugelblitz") -> None:
        super().__init__(pos, richtung, daten, ebene, von, waffe)
        self.daten = daten
        self.bild = daten.get("bild_flug", "kugelblitz_flug")
        self.spur = None
        self._zap_rest = 0.1
        self._dreh = RND.uniform(0, 360)

    def schritt(self, dt: float) -> None:
        self._zap_rest -= dt
        if self._zap_rest <= 0.0 and self.welt is not None:
            self._zap_rest = self.daten["zap_takt"]
            self._zappen()
        super().schritt(dt)

    def _zappen(self) -> None:
        d = self.daten
        w = self.welt
        r = d["zap_radius"]
        getroffen = 0
        for ziel in list(w.nahe(self.pos, r + 20.0, self.ebene)):
            if (ziel is self or ziel is self.von or not ziel.lebt
                    or getattr(ziel, "fraktion", "") in ("geschoss", self.quelle_fraktion)
                    or not getattr(ziel, "trefferbar", True)):
                continue
            if ziel.pos.distance_to(self.pos) > r + ziel.radius:
                continue
            if not w.sicht_frei(self.pos, ziel.pos, self.ebene):
                continue
            lebte = ziel.lebt
            schaden_an(ziel, d["schaden"], None, self.von, "kugel", self.pos)
            abschuss_buchen(self.von, ziel, self.waffe, lebte)
            w.entladung([self.pos, ziel.pos], self.ebene, "blitz")
            getroffen += 1
        # Und immer ein paar Blitze ins Leere, bis an die Reichweite.
        for i in range(max(0, d["zap_strahlen"] - getroffen)):
            self._dreh = (self._dreh + 137.0) % 360.0
            ende = w.strahl(self.pos, pygame.Vector2(1, 0).rotate(self._dreh), r, self.ebene)
            w.entladung([self.pos, ende], self.ebene, "blitz")

    def einschlag(self, ziel) -> None:
        self.lebt = False
        self._platzen()

    def _platzen(self) -> None:
        if getattr(self, "_geplatzt", False):
            return
        self._geplatzt = True
        d = self.daten
        w = self.welt
        r = d["platzen_radius"]
        for ziel in list(w.nahe(self.pos, r + 30.0, self.ebene)):
            if (ziel is self or not ziel.lebt or getattr(ziel, "fraktion", "") == "geschoss"
                    or ziel.fraktion == self.quelle_fraktion and ziel is not self.von
                    or not getattr(ziel, "trefferbar", True)):
                continue
            ab = ziel.pos - self.pos
            weit = ab.length()
            if weit > r + ziel.radius:
                continue
            anteil = (1.0 - 0.6 * min(1.0, weit / r)) * w.deckung_anteil(self.pos, ziel.pos,
                                                                          self.ebene)
            schub = ab.normalize() * 260.0 * anteil if weit > 0.01 else None
            lebte = ziel.lebt
            schaden_an(ziel, d["platzen_schaden"] * anteil, schub, self.von, "spreng", self.pos)
            abschuss_buchen(self.von, ziel, self.waffe, lebte)
        w.explosion(self.pos, self.ebene, r, "plasma", self.von)

    @property
    def lebt(self):
        return self.__dict__.get("_lebt", True)

    @lebt.setter
    def lebt(self, wert):
        # Auch am Ende der Reichweite platzt sie (Geschoss setzt dort nur
        # lebt = False).
        if not wert and self.__dict__.get("_lebt", True) and self.welt is not None:
            self.__dict__["_lebt"] = False
            self._platzen()
            return
        self.__dict__["_lebt"] = wert


class Gaswolke:
    """Die Wolke der Gasgranate (seit 0.34.67). Wie die Brandflaeche kein
    Wesen: sie liegt flach am Boden, waechst langsam und schadet, solange
    man drinsteht. Zombies atmen nicht (`K.GAS["verschont"]`), Fahrzeuge
    auch nicht - wer drinsitzt, ist geschuetzt."""

    __slots__ = ("pos", "ebene", "dauer", "alter", "lebt", "kennung", "von")
    _naechste_kennung = 0

    def __init__(self, pos, ebene: int, von=None, kennung: int | None = None,
                 alter: float = 0.0) -> None:
        self.pos = pygame.Vector2(pos)
        self.ebene = int(ebene)
        self.dauer = float(K.GAS["dauer"])
        self.alter = float(alter)
        self.lebt = True
        self.von = von
        if kennung is None:
            Gaswolke._naechste_kennung += 1
            kennung = Gaswolke._naechste_kennung
        self.kennung = int(kennung)

    @property
    def radius(self) -> float:
        g = K.GAS
        f = min(1.0, self.alter / max(0.1, g["wachsen"]))
        r = g["anfang"] + (g["radius"] - g["anfang"]) * f
        # Am Ende zieht sie sich wieder zusammen.
        rest = self.dauer - self.alter
        if rest < 2.0:
            r *= max(0.2, rest / 2.0)
        return r

    def schritt(self, dt: float, welt=None) -> None:
        self.alter += dt
        if self.alter >= self.dauer:
            self.lebt = False
            return
        if welt is None:
            return
        g = K.GAS
        r = self.radius
        for ziel in list(welt.nahe(self.pos, r + 20.0, self.ebene)):
            if (not ziel.lebt or getattr(ziel, "fraktion", "") in ("geschoss", g["verschont"])
                    or getattr(ziel, "ist_fahrzeug", False) or getattr(ziel, "im_fahrzeug", False)
                    or not getattr(ziel, "trefferbar", False)):
                continue
            if ziel.pos.distance_to(self.pos) <= r:
                ziel.schaden(g["schaden"] * dt, None, self.von)


class Werfergranate(Granate):
    """Die 40-mm-Granate des Granatwerfers (seit 0.34.62).

    Fliegt in einem Bogen bis zu der Weite, auf die gezielt wurde - die
    Hoehe sieht man nur daran, dass sie groesser wird (`flug`, gezeichnet
    wie alles in der Luft). Hoch genug geht sie ueber Kisten und Sandsaecke
    hinweg, nie ueber eine Mauer und nie eine Ebene hinauf. Trifft sie
    unterwegs tief genug einen Koerper, zuendet sie sofort; sonst landet
    sie, rollt kurz aus und zuendet nach `zuender` Sekunden wie eine
    Granate (Granate.schritt und Granate.zuenden)."""

    bild = "teil_granate40"

    def __init__(self, pos, richtung: float, daten: dict, ebene: int, von=None,
                 weite: float = 200.0, waffe: str = "granatwerfer") -> None:
        Wesen.__init__(self, pos, ebene)
        self.daten = daten
        self.von = von
        self.waffe = waffe
        self.winkel = richtung
        self.bild = "teil_granate40"
        self.quelle_fraktion = von.fraktion if von else "neutral"
        self.dauer = max(0.05, float(weite) / daten["tempo"])
        self.zeit = 0.0
        self.liegt = False
        self.rest = daten["zuender"]
        self.dreh = 0.0
        self.tempo = pygame.Vector2(daten["tempo"], 0).rotate(richtung)

    def schritt(self, dt: float) -> None:
        if self.liegt:
            super().schritt(dt)
            return
        self.vorher.update(self.pos)
        d = self.daten
        self.zeit = min(self.dauer, self.zeit + dt)
        f = self.zeit / self.dauer
        self.flug = 4.0 * d["bogen"] * f * (1.0 - f)
        weg = self.tempo * dt
        schritte = max(1, int(weg.length() / 4.0))
        teil = weg / schritte
        for _ in range(schritte):
            self.pos += teil
            if self.flug <= d["koerper_hoehe"]:
                ziel = self.welt.treffer(self.pos, self.radius, self.ebene,
                                         self.quelle_fraktion)
                if ziel is not None and ziel is not self.von:
                    self.flug = 0.0
                    self.zuenden()
                    return
            # Seit 0.34.87 haelt sie nur auf, was hoeher steht, als sie
            # gerade fliegt (K.STEHEN, Mauer 24, Fels 30) - im Bogen geht sie
            # ueber Mauern. Gemeldet: die Granaten "kollidieren oft mit
            # Mauern, obwohl die gar nicht so hoch gerendert werden".
            if (self.welt.schuss_halt(self.pos, self.ebene, self.radius)
                    and self.flug < self.welt.kachel_hoehe(self.pos, self.ebene)
                    + d["ueber_rand"]):
                self.pos -= teil
                self.flug = 0.0
                self.zuenden()
                return
        if f >= 1.0:
            # Gelandet: ab hier eine Granate, die ausrollt und zuendet.
            self.flug = 0.0
            self.liegt = True
            self.tempo *= d["ausrollen"]
            wolke(self.welt, self.pos, 4, 60, 0.3, K.C_MUTED_DK, self.ebene, 1, "staub")


class C4Ladung(Wesen):
    """Klebt nach einem kurzen Wurf und wartet auf den Zuender."""

    fraktion = "geschoss"
    schiebt = False
    trefferbar = False
    schatten = True
    radius = 4.0
    bild = "c4_brick"

    def __init__(self, pos, richtung: float, ebene: int, von=None,
                 weite: float = 0.0) -> None:
        super().__init__(pos, ebene)
        self.von = von
        self.winkel = richtung
        self.restweg = min(K.C4["wurfweite"], max(0.0, float(weite)))
        r = math.radians(richtung)
        self.richtung = pygame.Vector2(math.cos(r), math.sin(r))
        self.lade_rest = K.C4["ladezeit"]
        self.haftend = self.restweg <= 0.0
        # Woran sie klebt, wenn es etwas ist, das sich bewegt (ein Buggy,
        # seit 0.34.11), und wo genau - in dessen eigener Ausrichtung,
        # damit sie in der Kurve mitdreht und nicht ueber das Blech rutscht.
        self.traeger = None
        self._versatz = pygame.Vector2(0, 0)
        self._dreh = 0.0

    @property
    def obenauf(self) -> bool:
        """Auf einem Wagen wird sie nach ihm gezeichnet, sonst laege sie
        je nach Fahrtrichtung mal unter dem Blech."""
        return self.traeger is not None

    def schritt(self, dt: float) -> None:
        self.vorher.update(self.pos)
        if not self.haftend:
            schritt = min(self.restweg, K.C4["wurftempo"] * dt)
            vorher = pygame.Vector2(self.pos)
            stoss_x, stoss_y = self.welt.bewegen(
                self, self.richtung.x * schritt, self.richtung.y * schritt)
            self.restweg -= self.pos.distance_to(vorher)
            if self._ankleben():
                return
            if self.restweg <= 0.5 or stoss_x or stoss_y:
                self.haftend = True
        else:
            self.lade_rest = max(0.0, self.lade_rest - dt)
            t = self.traeger
            if t is not None:
                if not t.lebt:
                    self.traeger = None
                else:
                    self.pos.update(t.pos + self._versatz.rotate(t.winkel))
                    self.winkel = t.winkel + self._dreh
                    self.ebene = t.ebene

    def _ankleben(self) -> bool:
        """Im Flug an einen Wagen gestossen? Dann klebt sie dort."""
        for w in self.welt.wesen:
            if (getattr(w, "c4_haftet", False) and w.lebt
                    and w.ebene == self.ebene and w.beruehrt(self.pos, self.radius)):
                self.haftend = True
                self.traeger = w
                # Nicht mitten im Wagen, sondern dort, wo sie aufgekommen
                # ist - etwas zur Mitte gezogen, damit sie auf dem Blech liegt.
                rel = (self.pos - w.pos) * 0.7
                self._versatz = rel.rotate(-w.winkel)
                self._dreh = self.winkel - w.winkel
                self.pos.update(w.pos + rel)
                return True
        return False

    @property
    def bereit(self) -> bool:
        return self.haftend and self.lade_rest <= 0.0

    def detonieren(self) -> None:
        if not self.lebt or not self.bereit:
            return
        self.lebt = False
        w = self.welt
        radius = K.C4["radius"]
        for ziel in list(w.nahe(self.pos, radius + 30, self.ebene)):
            if not ziel.lebt or ziel is self:
                continue
            delta = ziel.pos - self.pos
            abstand = delta.length()
            if abstand > radius + ziel.radius:
                continue
            anteil = 1.0 - 0.72 * min(1.0, abstand / radius)
            anteil *= w.deckung_anteil(self.pos, ziel.pos, self.ebene)
            schub = (delta.normalize() * K.C4["schub"] * anteil
                     if abstand > 0.01 else None)
            lebte = ziel.lebt
            schaden_an(ziel, K.C4["schaden"] * anteil, schub, self.von, "hohlladung",
                       self.pos)
            abschuss_buchen(self.von, ziel, "c4", lebte)
        w.explosion(self.pos, self.ebene, radius, "c4", von=self.von)


class Rakete(Wesen):
    """Eine Rakete. Fliegt langsam, lenkt traege, zerlegt alles am Ende.

    Sie ist mit Absicht **langsam**: eine Rakete, der man nicht ausweichen
    kann, ist keine Waffe, sondern eine Ansage. Wer sie kommen sieht, hat
    eine Sekunde, und diese Sekunde ist das ganze Spiel gegen sie.

    **Lenken kann sie kaum.** `lenk_dreh` Grad je Sekunde, nicht mehr -
    an jeder Ecke verliert sie ihr Ziel, und um eine Wand herum kommt sie
    nie. Ohne das waere die Erfassung ein Todesurteil statt einer
    Entscheidung.

    **Ebenenwechsel im Flug.** Nur mit Erfassung, und nur ueber einem
    Loch: wer eine Etage tiefer erfasst wurde, bekommt sie durch den
    Abgrund, durch den man ihn gesehen hat. Ohne Erfassung fliegt sie
    darueber hinweg, wie jedes andere Geschoss auch.
    """

    fraktion = "geschoss"
    hoehe_bild = K.HOEHEN["lauf"]   # fliegt in Laufhoehe
    schiebt = False
    trefferbar = False
    schatten = True
    radius = 4.0
    bild = "flugrakete"
    faellt = False          # sie faellt nicht, sie fliegt

    def __init__(self, pos, richtung: float, daten: dict, ebene: int,
                 von=None, ziel=None, waffe: str = "rakete") -> None:
        super().__init__(pos, ebene)
        self.daten = daten
        self.von = von
        self.winkel = richtung
        self.rest = daten["flugzeit"]
        self.weg = 0.0
        # Womit sie abgeschossen wurde (seit 0.34.62: auch Einwegrohr und
        # Raketenbuendel), fuer die Statistik - und wie sie aussieht.
        self.waffe = waffe
        self.bild = daten.get("bild", "flugrakete")
        # Schlingern (das Raketenbuendel): die Richtung pendelt um die
        # Schussrichtung, jede Rakete mit eigenem Takt.
        self.grund_winkel = richtung
        self.schlinger_phase = RND.uniform(0, 2 * math.pi)
        # Wen sie sucht. None heisst: sie fliegt geradeaus.
        self.ziel = ziel
        self.quelle_fraktion = von.fraktion if von else "neutral"
        self.tempo = pygame.Vector2(daten["tempo"], 0).rotate(richtung)
        self._rauch_rest = 0.0

    def schritt(self, dt: float) -> None:
        self.vorher.update(self.pos)
        self.rest -= dt
        if self.rest <= 0:
            self.einschlag(None)
            return
        self._lenken(dt)
        self._schlingern(dt)
        self._ebene_wechseln()

        weg = self.tempo * dt
        strecke = weg.length()
        self.weg += strecke
        if self.weg > self.daten["reichweite"]:
            self.einschlag(None)
            return
        # In Stuecken, damit sie bei ihrem Tempo nichts durchfliegt.
        schritte = max(1, int(strecke / 6.0))
        teil = weg / schritte
        for _ in range(schritte):
            self.pos += teil
            getroffen = self.welt.treffer(self.pos, self.radius, self.ebene,
                                          self.quelle_fraktion)
            if getroffen is not None and getroffen is not self.von:
                self.einschlag(getroffen)
                return
            if self.welt.schuss_halt(self.pos, self.ebene, self.radius):
                self.pos -= teil
                self.einschlag(None)
                return
        self._rauchfahne(dt)

    def _lenken(self, dt: float) -> None:
        """Auf das erfasste Ziel zudrehen - langsam."""
        ziel = self.ziel
        if ziel is None or not getattr(ziel, "lebt", False):
            return
        ab = ziel.pos - self.pos
        if ab.length() < self.daten["lenk_ab"]:
            return                      # so kurz vor dem Ziel wird nicht mehr
        soll = math.degrees(math.atan2(ab.y, ab.x))
        diff = (soll - self.winkel + 180) % 360 - 180
        hoechstens = self.daten["lenk_dreh"] * dt
        self.winkel += max(-hoechstens, min(hoechstens, diff))
        self.tempo = pygame.Vector2(self.daten["tempo"], 0).rotate(self.winkel)

    def _schlingern(self, dt: float) -> None:
        """Unruhiger Flug (seit 0.34.62): die Richtung pendelt um die
        Schussrichtung - nah trifft sie, weit weg streut sie wild."""
        weite = self.daten.get("schlingern")
        if not weite or self.ziel is not None:
            return
        self.schlinger_phase += self.daten.get("schlinger_takt", 8.0) * dt
        self.winkel = self.grund_winkel + weite * math.sin(self.schlinger_phase)
        self.tempo = pygame.Vector2(self.daten["tempo"], 0).rotate(self.winkel)

    def _ebene_wechseln(self) -> None:
        """Ueber einem Loch zur erfassten Etage hinunter.

        Nur mit Erfassung und nur nach unten: eine Rakete steigt nicht.
        Und nur dort, wo wirklich ein Loch ist - sonst fliegt sie ueber
        den Boden hinweg, wie jedes Geschoss.
        """
        ziel = self.ziel
        if ziel is None or ziel.ebene >= self.ebene:
            return
        e = self.welt.ebene(self.ebene)
        if not e.loch(int(self.pos.x // K.TILE), int(self.pos.y // K.TILE)):
            return
        self.ebene -= 1

    def _rauchfahne(self, dt: float) -> None:
        self._rauch_rest -= dt
        if self._rauch_rest > 0:
            return
        self._rauch_rest = 0.022
        hinten = self.pos - pygame.Vector2(9, 0).rotate(self.winkel)
        self.welt.partikel.append(Partikel(
            hinten, (RND.uniform(-12, 12), RND.uniform(-12, 12)),
            RND.uniform(0.35, 0.7), K.C_MUTED, 1, "staub", 2.4, self.ebene))

    def einschlag(self, getroffen) -> None:
        """Sprengen. Eigenschaden ja, Mannschaftsschaden nein.

        Der Unterschied steht hier und nicht in `Wesen.schaden`: nur die
        Rakete kennt ihn, und nur sie soll ihn kennen. Alles andere in
        diesem Spiel trifft, was es trifft.
        """
        self.lebt = False
        d = self.daten
        w = self.welt
        r = d["radius"]
        schuetze = self.von
        mein_team = getattr(schuetze, "team", -2)
        for ziel in list(w.nahe(self.pos, r + 30, self.ebene)):
            if not ziel.lebt or ziel is self:
                continue
            ab = ziel.pos - self.pos
            rand = getattr(ziel, "rand_punkt", None)
            if rand is not None:
                # Ein Fahrzeug vom Blech aus gemessen (seit 0.34.95), auch
                # die Deckung. Von der Mitte aus kam am Bug eines
                # Panzerwagens nur ein Drittel an, und stand die Mitte
                # hinter einer Wandkante, fast nichts - die Panzerabwehr
                # verpuffte (gemeldet).
                hin = rand(self.pos)
                entfernung = hin.distance_to(self.pos)
                if entfernung > r:
                    continue
            else:
                hin = ziel.pos
                entfernung = ab.length()
                if entfernung > r + ziel.radius:
                    continue
            if ziel is schuetze:
                anteil = d["eigen_anteil"]
            elif (mein_team is not None and mein_team >= 0
                  and getattr(ziel, "team", -1) == mein_team):
                continue          # eigene Leute nimmt sie nicht mit
            else:
                anteil = 1.0
            anteil *= 1.0 - 0.7 * min(1.0, entfernung / r)
            anteil *= w.deckung_anteil(self.pos, hin, self.ebene)
            schub = (ab.normalize() * 420 * anteil) if ab.length_squared() > 1e-4 else None
            lebte = ziel.lebt
            fz = d.get("fahrzeug_schaden")
            schaden_an(ziel, d["schaden"] * anteil, schub, schuetze,
                       d.get("schadensart", "hohlladung"), self.pos - self.tempo * 0.1,
                       fahrzeug_menge=None if fz is None else fz * anteil)
            abschuss_buchen(schuetze, ziel, self.waffe, lebte)
        w.explosion(self.pos, self.ebene, r, d.get("explosion", "spreng"))
        w.kurz_langsam(0.06)


class Brandflaeche:
    """Brennender Boden. Die Wirkung eines Molotow.

    Wie die Rauchwolke kein Wesen: sie stoesst niemanden, ist nicht zu
    treffen und dreht sich nicht. Anders als der Rauch nimmt sie aber
    nicht die Sicht, sondern den **Ort** - wer hindurchlaeuft, brennt.

    **Sie wirkt auf genau einer Ebene.** Feuer auf Deck 2 brennt nicht
    durch den Boden auf Deck 1, und wer eine Etage tiefer steht, ist in
    Sicherheit. Das ist keine Vereinfachung, sondern die Regel: alles in
    diesem Spiel gehoert zu einer Ebene, und wer davon eine Ausnahme
    macht, bekommt spaeter jede Ebenenfrage doppelt.

    Der Schaden laeuft je Sekunde, nicht in Stufen. Wer hindurchhechtet,
    soll dafuer bezahlen und weiterleben; wer stehenbleibt, nicht.
    """

    __slots__ = ("pos", "ebene", "radius", "dauer", "alter", "lebt",
                 "kennung", "von", "verschont", "_saat", "_feld",
                 "_funkenrest", "napalm", "_rauchrest")

    _naechste_kennung = 0

    def __init__(self, pos, ebene: int, radius: float | None = None,
                 dauer: float | None = None, alter: float = 0.0,
                 kennung: int | None = None, von=None,
                 verschont: str = "", napalm: bool = False) -> None:
        f = K.FEUER
        # Napalm (seit 0.34.130): brennt laenger, sieht anders aus (K.FEUER
        # napalm_*), mehr Funken und schwarzer Rauch.
        self.napalm = bool(napalm)
        self._rauchrest = 0.0
        self.pos = pygame.Vector2(pos)
        self.ebene = int(ebene)
        self.radius = float(f["radius"] if radius is None else radius)
        self.dauer = float(f["dauer"] if dauer is None else dauer)
        self.alter = float(alter)
        self.lebt = True
        self.von = von
        # Welche Fraktion dieses Feuer nicht anfasst.
        #
        # Leer heisst: es brennt alles, und so bleibt der Molotow eines
        # Spielers auch. Gesetzt wird es nur beim Feuer, das ein Gegner
        # legt - siehe Blaeher und Brandstifter. Der Grund steht dort.
        self.verschont = str(verschont)
        if kennung is None:
            Brandflaeche._naechste_kennung += 1
            kennung = Brandflaeche._naechste_kennung
        self.kennung = int(kennung)
        # Wie beim Rauch: die Saat haengt an der Stelle. Zwei Feuer
        # nebeneinander sehen verschieden aus, dasselbe Feuer aber auf
        # jedem Rechner gleich.
        self._saat = (int(self.pos.x) * 40503677) ^ (int(self.pos.y) * 13731337)
        self._feld = None
        self._funkenrest = 0.0

    @property
    def staerke(self) -> float:
        """0 bis 1: auflodern, brennen, herunterbrennen."""
        f = K.FEUER
        if self.alter < f["aufbau"]:
            return max(0.0, self.alter / f["aufbau"])
        rest = self.dauer - self.alter
        if rest < f["abbau"]:
            return max(0.0, rest / f["abbau"])
        return 1.0

    def brennt(self, punkt, ebene: int) -> float:
        """Wie stark es an dieser Stelle brennt. 0, wenn gar nicht.

        Die Ebene wird zuerst geprueft und nicht zuletzt: eine Stelle auf
        einer anderen Etage brennt nie, egal wie nah sie in der Draufsicht
        liegt.
        """
        if int(ebene) != self.ebene or not self.lebt:
            return 0.0
        weg = pygame.Vector2(punkt).distance_to(self.pos)
        if weg > self.radius:
            return 0.0
        f = K.FEUER
        # Innen voll, aussen weniger - aber nie null, sonst waere der Rand
        # eine Linie, an der man gefahrlos stehen kann.
        aussen = weg / max(1.0, self.radius)
        return self.staerke * (1.0 - (1.0 - f["rand_anteil"]) * aussen)

    def schritt(self, dt: float, welt=None) -> None:
        self.alter += dt
        if self.alter >= self.dauer:
            self.lebt = False
            if welt is not None and K.FEUER["brandfleck"]:
                welt.brandfleck(self.pos, self.ebene, self.radius * 0.8)
            return
        if welt is None:
            return
        f = K.FEUER
        for ziel in list(welt.nahe(self.pos, self.radius + 12, self.ebene)):
            if not ziel.lebt or ziel.fraktion == "geschoss":
                continue
            if self.verschont and ziel.fraktion == self.verschont:
                continue
            anteil = self.brennt(ziel.pos, ziel.ebene)
            if anteil > 0.0:
                schaden_an(ziel, f["schaden"] * anteil * dt, None, self.von, "feuer")
        if self.napalm:
            self.qualmen(dt, welt)
        # Funken steigen auf. Sie sind das, was ein Feuer von einem
        # roten Fleck unterscheidet.
        self._funkenrest += f["napalm_funken" if self.napalm else "funken"] * self.staerke * dt
        while self._funkenrest >= 1.0:
            self._funkenrest -= 1.0
            winkel = RND.uniform(0, 360)
            weg = RND.uniform(0, self.radius * 0.85)
            stelle = self.pos + pygame.Vector2(weg, 0).rotate(winkel)
            welt.partikel.append(Partikel(
                stelle, (RND.uniform(-14, 14), RND.uniform(-46, -22)),
                RND.uniform(0.5, 1.1), f["toene"][3], 1, "funke", 1.2,
                self.ebene))

    def qualmen(self, dt: float, welt) -> None:
        """Napalm: schwarzer, oeliger Rauch steigt aus dem Feuer (seit
        0.34.130). Beim Gastgeber im Schritt, beim Gast aus dem Nachfuehren -
        es ist nur Bild."""
        from . import effekte
        self._rauchrest += K.FEUER["napalm_rauch"] * self.staerke * dt
        while self._rauchrest >= 1.0:
            self._rauchrest -= 1.0
            winkel = RND.uniform(0, 360)
            weg = RND.uniform(0, self.radius * 0.7)
            stelle = self.pos + pygame.Vector2(weg, 0).rotate(winkel)
            effekte.rauch(welt, RND, stelle.x, stelle.y, 4.0, self.ebene, "schwarz", 3,
                          RND.uniform(10, 16), RND.uniform(2.2, 3.4), vx=RND.uniform(-6, 6),
                          vz=RND.uniform(18, 34), zaeh=0.9, g=-6.0)

    def feld(self, korn: int):
        """Das Dichtefeld, einmal gerechnet und dann behalten.

        Dieselbe Ueberlegung wie beim Rauch: das Feld haengt nur an der
        Lage, nicht am Alter. Das Zuengeln entsteht spaeter daraus, dass
        die Schwelle wandert - nicht daraus, dass hier neu gewuerfelt
        wird. Ein Feuer, das jedes Bild neu gerechnet wird, flackert wie
        Rauschen und sieht nach Fehler aus, nicht nach Flamme.
        """
        if self._feld is not None and self._feld[0] == korn:
            return self._feld[1:]
        f = K.FEUER
        spanne = self.radius * 1.1
        x0 = int((self.pos.x - spanne) // korn) * korn
        y0 = int((self.pos.y - spanne) // korn) * korn
        breite = max(1, int(spanne * 2 / korn) + 1)
        werte = [0.0] * (breite * breite)
        masche = f["gitter"]
        felder_je_masche = masche / korn
        punkte = int(breite / felder_je_masche) + 2
        gitter = [[_zufall(int(math.floor(x0 / masche)) + gx,
                           int(math.floor(y0 / masche)) + gy, self._saat)
                   for gx in range(punkte + 1)]
                  for gy in range(punkte + 1)]
        versatz_x = (x0 / masche) - math.floor(x0 / masche)
        versatz_y = (y0 / masche) - math.floor(y0 / masche)
        mx = self.pos.x - x0
        my = self.pos.y - y0
        rr = max(1.0, self.radius)
        for gy in range(breite):
            fy = versatz_y + gy / felder_je_masche
            iy = int(fy)
            ty = fy - iy
            sy = ty * ty * (3.0 - 2.0 * ty)
            oben_zeile = gitter[iy]
            unten_zeile = gitter[iy + 1]
            zeile = gy * breite
            dy = (gy * korn + korn * 0.5 - my) / rr
            for gx in range(breite):
                fx = versatz_x + gx / felder_je_masche
                ix = int(fx)
                tx = fx - ix
                sx = tx * tx * (3.0 - 2.0 * tx)
                a, b = oben_zeile[ix], oben_zeile[ix + 1]
                c, d = unten_zeile[ix], unten_zeile[ix + 1]
                oben = a + (b - a) * sx
                unten = c + (d - c) * sx
                dx = (gx * korn + korn * 0.5 - mx) / rr
                u = math.sqrt(dx * dx + dy * dy)
                # Quadratischer Abfall: anders als beim Rauch soll das
                # Feuer zur Mitte hin deutlich heisser sein, nicht bis
                # zum Rand gleich dicht. Ein Feuer hat einen Kern.
                abfall = 1.0 - u * u
                werte[zeile + gx] = (0.0 if abfall <= 0.0 else
                                     abfall * (0.55 + 0.9 *
                                               (oben + (unten - oben) * sy)))
        # Auf 0 bis 1 normieren. Ohne das liegt der Hoechstwert je nach
        # Zufall irgendwo zwischen 0,6 und 1,5, und die Farbstufen im
        # Renderer laegen bei jedem Feuer anders - mal ein kleiner heller
        # Kern, mal eine Flaeche, die ganz hell ist. Genau das sah aus
        # wie eine Lampe und nicht wie Feuer.
        hoechst = max(werte) or 1.0
        for i, w in enumerate(werte):
            werte[i] = w / hoechst
        self._feld = (korn, breite, x0, y0, werte)
        return breite, x0, y0, werte


def _zufall(ix: int, iy: int, saat: int) -> float:
    """Eine feste Zahl zwischen 0 und 1 fuer einen Gitterpunkt."""
    h = (ix * 374761393) ^ (iy * 668265263) ^ (saat * 2246822519)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def _gitterwert(x: float, y: float, masche: float, saat: int) -> float:
    """Weich ueberblendetes Zufallsgitter an der Stelle (x, y).

    Der Unterschied zu einem Wuerfel je Bildpunkt ist der ganze Punkt:
    benachbarte Stellen bekommen aehnliche Werte, und daraus werden
    zusammenhaengende Ballen statt Rauschen. Zwischen den Gitterpunkten
    wird mit einer S-Kurve ueberblendet, nicht linear - sonst sieht man
    die Maschen als Rauten.
    """
    gx, gy = x / masche, y / masche
    ix, iy = math.floor(gx), math.floor(gy)
    fx, fy = gx - ix, gy - iy
    sx = fx * fx * (3.0 - 2.0 * fx)
    sy = fy * fy * (3.0 - 2.0 * fy)
    a = _zufall(ix, iy, saat)
    b = _zufall(ix + 1, iy, saat)
    c = _zufall(ix, iy + 1, saat)
    d = _zufall(ix + 1, iy + 1, saat)
    oben = a + (b - a) * sx
    unten = c + (d - c) * sx
    return oben + (unten - oben) * sy


class Nagelfeld:
    """Naegel und Kraehenfuesse hinter einem Wagen (seit 0.34.65, der
    Nagelstreuer). Wie die Brandflaeche kein Wesen: sie liegt nur da.

    Reifen gehen darin platt - der Wagen wird fuer `platt_dauer` langsam
    und nimmt etwas Schaden, einmal je Ueberfahrt. Ketten (der Panzer)
    rollen darueber. Auf Wesen wirkt es nicht: so hat es der Besitzer fuer
    die Kraehenfuesse festgelegt ("kein Effekt bei Wesen", Waffenpaket)."""

    __slots__ = ("pos", "ebene", "radius", "dauer", "alter", "lebt",
                 "kennung", "von", "saat")
    _naechste_kennung = 0

    def __init__(self, pos, ebene: int, von=None, kennung: int | None = None,
                 alter: float = 0.0) -> None:
        n = K.NAEGEL
        self.pos = pygame.Vector2(pos)
        self.ebene = int(ebene)
        self.radius = float(n["radius"])
        self.dauer = float(n["dauer"])
        self.alter = float(alter)
        self.lebt = True
        self.von = von
        if kennung is None:
            Nagelfeld._naechste_kennung += 1
            kennung = Nagelfeld._naechste_kennung
        self.kennung = int(kennung)
        # Wo die einzelnen Naegel liegen, folgt aus der Kennung - beim
        # Gast also genau so wie beim Gastgeber, ohne dass es mitgeht.
        self.saat = self.kennung * 7919

    def schritt(self, dt: float, welt=None) -> None:
        self.alter += dt
        if self.alter >= self.dauer:
            self.lebt = False
            return
        if welt is None:
            return
        n = K.NAEGEL
        for ziel in list(welt.nahe(self.pos, self.radius + 40.0, self.ebene)):
            if not ziel.lebt or getattr(ziel, "fraktion", "") == "geschoss":
                continue
            if getattr(ziel, "ist_fahrzeug", False):
                if (ziel.art in n["ketten"] or getattr(ziel, "platt_rest", 0.0) > 0.0
                        or abs(ziel.fahrt) < 25.0
                        or not ziel.beruehrt(self.pos, self.radius)):
                    continue
                ziel.platt_treffen(n["platt_dauer"])
                schaden_an(ziel, n["platt_schaden"], None, self.von)

    def stellen(self) -> list:
        """Wo die einzelnen Naegel liegen: (x, y, Winkel), immer gleich."""
        r = random.Random(self.saat)
        raus = []
        for _ in range(K.NAEGEL["anzahl"]):
            a = r.uniform(0, math.tau)
            d = self.radius * math.sqrt(r.random()) * 0.9
            raus.append((self.pos.x + math.cos(a) * d, self.pos.y + math.sin(a) * d,
                         r.uniform(0, 360)))
        return raus


class Rauchwolke:
    """Eine stehende Wand aus Rauch auf einer Ebene.

    Kein Wesen: sie stoesst niemanden, ist nicht zu treffen und dreht sich
    nicht. Sie liegt auf ihrer Ebene und nimmt die Sicht - auch die von
    oben, denn der Renderer zeichnet sie in die Ebene hinein, nachdem die
    Figuren dort stehen. Wer von Ebene 2 hinuntersieht, sieht also den
    Rauch und nicht, wer darin steht.

    Sie macht keinen Schaden. Wer hindurchschiesst, trifft weiter - nur
    sehen kann er es nicht.
    """

    __slots__ = ("pos", "ebene", "radius", "dauer", "alter", "lebt",
                 "kennung", "_saat", "_feld")

    # Fortlaufende Nummer je Wolke. Sie ist das, woran der Gast eine Wolke
    # wiedererkennt, die er schon hat - siehe Gefecht._welt_uebernehmen.
    _naechste_kennung = 0

    def __init__(self, pos, ebene: int, radius: float | None = None,
                 dauer: float | None = None, alter: float = 0.0,
                 kennung: int | None = None) -> None:
        r = K.RAUCH
        self.pos = pygame.Vector2(pos)
        self.ebene = int(ebene)
        self.radius = float(r["radius"] if radius is None else radius)
        self.dauer = float(r["dauer"] if dauer is None else dauer)
        self.alter = float(alter)
        self.lebt = True
        if kennung is None:
            Rauchwolke._naechste_kennung += 1
            kennung = Rauchwolke._naechste_kennung
        self.kennung = int(kennung)
        # Die Saat haengt an der Stelle, an der die Wolke steht: zwei
        # Wolken nebeneinander sehen dadurch verschieden aus, dieselbe
        # Wolke aber auf jedem Rechner gleich.
        self._saat = (int(self.pos.x) * 73856093) ^ (int(self.pos.y) * 19349663)
        self._feld = None          # wird beim ersten Zeichnen gebaut

    @property
    def dichte(self) -> float:
        """0 bis 1: erst aufziehen, dann stehen, zum Schluss verwehen."""
        r = K.RAUCH
        if self.alter < r["aufbau"]:
            return max(0.0, self.alter / r["aufbau"])
        rest = self.dauer - self.alter
        if rest < r["abbau"]:
            return max(0.0, rest / r["abbau"])
        return 1.0

    # ---- Das Dichtefeld -------------------------------------------------
    def feld(self, korn: int):
        """Das Dichtefeld der Wolke, einmal gerechnet und dann behalten.

        Gibt (breite, x0, y0, werte) zurueck: ein Quadrat aus Dichtewerten
        im Abstand `korn`, dazu seine linke obere Weltecke.

        **Warum einmal und nicht je Bild.** Das Feld haengt nur an der
        Lage der Wolke, nicht an ihrer Dichte - die verschiebt spaeter
        bloss die Schwelle, ab der ein Punkt ueberhaupt Rauch ist. Also
        wird es genau einmal gebaut, und alle Zeichenstufen bedienen sich
        daraus. Vorher wurde es fuenf Mal gerechnet, und jedes Mal
        sechzigtausend Mal gehasht.

        **Warum ein Gitter und kein Wuerfeln je Punkt.** Benachbarte
        Stellen sollen aehnliche Werte haben, sonst entsteht Rauschen und
        keine Wolke. Die Eckpunkte eines groben Gitters werden gewuerfelt,
        dazwischen wird mit einer S-Kurve ueberblendet. Zwei Lagen
        uebereinander: eine grobe fuer die Form, eine feinere fuer die
        Struktur.
        """
        if self._feld is not None and self._feld[0] == korn:
            return self._feld[1:]
        r = K.RAUCH
        spanne = self.radius * 1.25
        x0 = int((self.pos.x - spanne) // korn) * korn
        y0 = int((self.pos.y - spanne) // korn) * korn
        breite = max(1, int(spanne * 2 / korn) + 1)

        werte = [0.0] * (breite * breite)
        masche = r["gitter"]
        gewicht = 1.0
        ganz = 0.0
        for lage in range(r["lagen"]):
            ganz += gewicht
            # Erst die Gitterpunkte, dann dazwischen ueberblenden. So wird
            # je Lage ein paar hundert Mal gehasht statt zehntausende Male.
            felder_je_masche = masche / korn
            punkte = int(breite / felder_je_masche) + 2
            gitter = [[_zufall(int(math.floor(x0 / masche)) + gx,
                               int(math.floor(y0 / masche)) + gy,
                               self._saat + lage)
                       for gx in range(punkte + 1)]
                      for gy in range(punkte + 1)]
            versatz_x = (x0 / masche) - math.floor(x0 / masche)
            versatz_y = (y0 / masche) - math.floor(y0 / masche)
            for gy in range(breite):
                fy = versatz_y + gy / felder_je_masche
                iy = int(fy)
                ty = fy - iy
                sy = ty * ty * (3.0 - 2.0 * ty)
                oben_zeile = gitter[iy]
                unten_zeile = gitter[iy + 1]
                zeile = gy * breite
                for gx in range(breite):
                    fx = versatz_x + gx / felder_je_masche
                    ix = int(fx)
                    tx = fx - ix
                    sx = tx * tx * (3.0 - 2.0 * tx)
                    a = oben_zeile[ix]
                    b = oben_zeile[ix + 1]
                    c = unten_zeile[ix]
                    d = unten_zeile[ix + 1]
                    oben = a + (b - a) * sx
                    unten = c + (d - c) * sx
                    werte[zeile + gx] += gewicht * (oben + (unten - oben) * sy)
            masche *= 0.5
            gewicht *= 0.5

        # Grundform: voll in der Mitte, weich auslaufend zum Rand.
        mx = self.pos.x - x0
        my = self.pos.y - y0
        rr = max(1.0, self.radius)
        for gy in range(breite):
            dy = (gy * korn + korn * 0.5 - my) / rr
            zeile = gy * breite
            for gx in range(breite):
                dx = (gx * korn + korn * 0.5 - mx) / rr
                # Hoch drei statt hoch zwei: innen bleibt die Wolke
                # lange voll und faellt erst zum Rand hin schnell ab.
                # Genau dort soll das Rauschen den Umriss ausfransen -
                # im Inneren darf es keine Loecher reissen, eine
                # Sichtwand mit Loechern ist keine.
                u = math.sqrt(dx * dx + dy * dy)
                abfall = 1.0 - u * u * u
                if abfall <= 0.0:
                    werte[zeile + gx] = 0.0
                else:
                    werte[zeile + gx] = abfall * (0.62 + 1.1 * werte[zeile + gx] / ganz)
        self._feld = (korn, breite, x0, y0, werte)
        return breite, x0, y0, werte

    def dichte_bei(self, x: float, y: float) -> float:
        """Dichte an einer Weltstelle, aus dem Feld abgelesen."""
        korn = max(1, int(K.RAUCH["korn"]))
        breite, x0, y0, werte = self.feld(korn)
        gx = int((x - x0) // korn)
        gy = int((y - y0) // korn)
        if not (0 <= gx < breite and 0 <= gy < breite):
            return 0.0
        return werte[gy * breite + gx]

    def deckt(self, pos, ebene: int) -> bool:
        """Ist dieser Punkt vollstaendig verborgen?

        Nur der dichte Kern zaehlt und nur, wenn die Wolke schon steht.
        Wer im ausgefransten Rand steht, ist halb zu sehen - und wird
        darum auch nicht versteckt.
        """
        if not self.lebt or int(ebene) != self.ebene:
            return False
        if self.dichte < 0.999:
            return False
        return self.pos.distance_to(pos) <= self.radius * K.RAUCH["kern"]

    def schritt(self, dt: float) -> None:
        self.alter += dt
        if self.alter >= self.dauer:
            self.lebt = False


# ══════════════════════════════════════════════════════════════════
# Aufsammler
# ══════════════════════════════════════════════════════════════════

class Feuerball:
    """Der Einschlag der Panzerkanone (seit 0.34.59, Welt.explosion "panzer").

    Kein Kreis, der waechst - gemeldet war das "nicht geil". Mehrere
    versetzte Glutballen, die zeitversetzt aufgehen und verloeschen
    (additiv gezeichnet: weiss, gelb, orange, dunkelrot), danach dunkler
    Rauch aus rund zehn Wolken, der aufquillt und abtreibt. Die Zufallszahlen
    kommen aus dem Ort (`saat`): beim Gast sieht derselbe Einschlag genauso
    aus wie beim Gastgeber. Wie der Rauch kein Wesen - er stoesst niemanden
    und ist nicht zu treffen.

    Zeiten in Sekunden; im Paket waren es Bilder bei 60 je Sekunde.
    """

    __slots__ = ("pos", "ebene", "alter", "ballen", "wolken", "lebt", "brocken")

    def __init__(self, pos, ebene: int, saat: int, groesse: float = 1.0) -> None:
        self.pos = pygame.Vector2(pos)
        self.ebene = int(ebene)
        self.alter = 0.0
        self.lebt = True
        r = random.Random(saat)
        f = K.FEUERBALL
        self.ballen = []
        for _ in range(f["ballen"]):
            versatz = pygame.Vector2(r.uniform(0, f["ballen_streuung"] * groesse), 0) \
                .rotate(r.uniform(0, 360))
            self.ballen.append((versatz, r.uniform(*f["ballen_radius"]) * groesse,
                                r.uniform(0.0, f["ballen_start"]),
                                r.uniform(*f["ballen_dauer"])))
        wind = pygame.Vector2(r.uniform(*f["wind_x"]), r.uniform(*f["wind_y"]))
        self.wolken = []
        for _ in range(f["wolken"]):
            versatz = pygame.Vector2(r.uniform(0, f["wolken_streuung"] * groesse), 0) \
                .rotate(r.uniform(0, 360))
            self.wolken.append((versatz, r.uniform(*f["wolke_klein"]) * groesse,
                                r.uniform(*f["wolke_gross"]) * groesse,
                                r.uniform(*f["wolke_start"]), r.uniform(*f["wolke_dauer"]),
                                versatz * 0.6 + wind, r.choice(f["rauch_farben"])))
        # Brocken (seit 0.34.96): Richtung am Boden, Tempo nach oben, Groesse, Farbe.
        self.brocken = []
        for _ in range(f["brocken"]):
            seite = pygame.Vector2(r.uniform(*f["brocken_tempo"]) * groesse, 0) \
                .rotate(r.uniform(0, 360))
            self.brocken.append((seite, r.uniform(*f["brocken_hoch"]),
                                 r.choice((1, 2, 2, 3)), r.choice(f["brocken_farben"])))

    def schritt(self, dt: float) -> None:
        self.alter += dt
        if self.alter > K.FEUERBALL["dauer"]:
            self.lebt = False


class Flugleiche:
    """Wer beim Rammen stirbt, fliegt noch ein Stueck (seit 0.34.59).

    0,1 bis 0,6 Sekunden, mit Drehung, mit dem Stoss des Fahrzeugs - und
    wird dabei aus jedem Fahrzeug hinausgeschoben, das ihm im Weg ist. Wo
    sie landet, bleibt ein Spritzer in Flugrichtung. Nur Bild: niemand
    trifft sie, und gezaehlt ist der Tod schon (Welt.leichenflug).

    Ohne Blut (`blut` leer, seit 0.34.62) ist es ein Gegenstand - das leere
    Rohr des Einweg-Raketenwerfers: es rutscht aus, bleibt K.ROHR["liegen"]
    Sekunden liegen und qualmt hinten noch eine Weile."""

    __slots__ = ("pos", "vorher", "ebene", "bild", "winkel", "tempo", "rest",
                 "dreh", "blut", "radius", "lebt", "_qualm")

    def __init__(self, pos, ebene: int, bild: str, winkel: float, tempo,
                 dauer: float, dreh: float, blut: str, radius: float) -> None:
        self.pos = pygame.Vector2(pos)
        self.vorher = pygame.Vector2(pos)
        self.ebene = int(ebene)
        self.bild = str(bild)
        self.winkel = float(winkel)
        self.tempo = pygame.Vector2(tempo)
        self.rest = float(dauer)
        self.dreh = float(dreh)
        self.blut = str(blut)
        self.radius = float(radius)
        self.lebt = True
        self._qualm = 0.0

    def schritt(self, dt: float, welt) -> None:
        self.vorher.update(self.pos)
        if not self.blut and self.rest <= 0.0:
            self._liegen(dt, welt)
            return
        self.pos += self.tempo * dt
        self.tempo *= max(0.0, 1.0 - K.RAMMEN["flug_bremse"] * dt)
        self.winkel += self.dreh * dt
        # Auch fliegend nie im Fussabdruck eines Fahrzeugs (Paket,
        # Stolperfalle 1): an der Seite mit der geringsten Tiefe hinaus.
        for w in welt.wesen:
            if getattr(w, "rechteckig", False) and w.ebene == self.ebene \
                    and w.beruehrt(self.pos, self.radius):
                f = w.werte
                lok = w.lokal(self.pos)
                r = self.radius
                tiefe = {(1, 0): f["vorn"] + r - lok.x, (-1, 0): lok.x - (f["hinten"] - r),
                         (0, -1): lok.y + f["halb"] + r, (0, 1): f["halb"] + r - lok.y}
                n = min(tiefe, key=tiefe.get)
                self.pos = w.pos + (lok + pygame.Vector2(n) * tiefe[n]).rotate(w.winkel)
        self.rest -= dt
        if not self.blut:
            self._qualmen(dt, welt)
            return
        if self.rest <= 0.0:
            self.lebt = False
            richtung = math.degrees(math.atan2(self.tempo.y, self.tempo.x)) \
                if self.tempo.length_squared() > 25 else 0.0
            b = K.BLUT.get(self.blut, K.BLUT["mensch"])
            wolke(welt, self.pos, 10, 90, 0.5, b["spritzer"], self.ebene, 2, "blut",
                  80, richtung)
            variante = int(abs(self.pos.x) * 7 + abs(self.pos.y) * 13) % 8
            welt.blutfleck(self.pos + pygame.Vector2(self.radius * 0.6, 0).rotate(richtung),
                           self.ebene, self.radius * 0.9, self.blut, variante)

    def _liegen(self, dt: float, welt) -> None:
        """Ein Gegenstand liegt: er qualmt noch und ist dann weg."""
        self.rest -= dt
        if self.rest <= -K.ROHR["liegen"]:
            self.lebt = False
            return
        if self.rest > -K.ROHR["qualm"]:
            self._qualmen(dt, welt)

    def _qualmen(self, dt: float, welt) -> None:
        """Duenner Rauch aus dem hinteren, offenen Ende."""
        self._qualm -= dt
        if self._qualm > 0.0:
            return
        self._qualm = K.ROHR["qualm_takt"]
        hinten = self.pos - pygame.Vector2(K.ROHR["hinten"], 0).rotate(self.winkel)
        welt.partikel.append(Partikel(
            hinten, (RND.uniform(-8, 8), RND.uniform(-22, -10)),
            RND.uniform(0.5, 0.9), K.C_MUTED, 1, "staub", 2.2, self.ebene))

    def zeichenpos(self, alpha: float) -> pygame.Vector2:
        return self.vorher.lerp(self.pos, alpha)


class Aufsammler(Wesen):
    """Liegt herum, bis jemand darueber laeuft."""

    fraktion = "beute"
    schiebt = False
    trefferbar = False
    radius = 8.0
    hoehe_3d = K.FIGUREN_3D["beute"]

    def __init__(self, pos, art: str, ebene: int = 0) -> None:
        super().__init__(pos, ebene)
        self.art = art
        self.bild = "medkit" if art == "medkit" else None

    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        held = self.welt.held
        if held is None or not held.lebt or held.ebene != self.ebene:
            return
        if held.sturz_rest > 0:
            return
        if self.pos.distance_to(held.pos) < self.radius + held.radius + 3:
            if self.art == "medkit" and held.medkits < K.MEDKIT["hoechstens"]:
                held.medkits += 1
                self.lebt = False
                wolke(self.welt, self.pos, 8, 90, 0.4, K.C_TEAL, self.ebene, 1)
                self.welt.klang("aufheben", 0.6)


# ══════════════════════════════════════════════════════════════════
# Spieler
# ══════════════════════════════════════════════════════════════════

class Spieler(Wesen):
    fraktion = "mensch"
    # Vorgaben fuer Felder, die nur manche Figuren haben (seit 0.34.89):
    # dieselben Werte, die vorher `getattr(self, ..., Vorgabe)` lieferte -
    # so liest der Schritt sie direkt, ohne getattr je Feld und Schritt.
    am_boden = False
    zieht = None
    hilft = None
    schild = False
    klassen_tempo = 1.0
    draht_rest = 0.0
    tempo_anteil = 1.0
    sprintet = False
    # Kein fester Name: die Figur zeigt die Waffe, die sie gerade traegt.
    # Siehe die Eigenschaft bild() weiter unten.
    faellt = True

    def __init__(self, pos, ebene=0) -> None:
        self.max_leben = K.SPIELER["leben"]
        super().__init__(pos, ebene)
        self.radius = K.SPIELER["radius"]
        self.waffen = list(K.HOTBAR)
        self.waffe = 0
        self.magazin = {w: K.WAFFEN[w]["magazin"] for w in self.waffen}
        self._c4_feuert_alt = False
        self.c4_netz_rest = -1.0
        self.fokus = 0.0              # 0 = aus der Hueffte, 1 = ganz ruhig
        self.zielt = False            # rechte Maustaste
        self.medkits = 1
        self.heilt_rest = 0.0
        self.halte_zeit = 0.0         # wie lange der Abzug schon gedrueckt ist
        self.schlag_zeigen = 0.0      # Restzeit der Nahkampf-Anzeige
        self.nahkampf_rest = 0.0      # eigener Takt fuer den Schlag auf F
        self.takt = 0.0
        self.nachlade_rest = 0.0
        self.unverwundbar = 0.0
        self.weg = 0.0                 # fuer Schrittstaub
        self.ziel = pygame.Vector2(pos) + pygame.Vector2(1, 0)
        self.will = pygame.Vector2(0, 0)
        # Dash statt Sprint (K.DASH). `dash_ladungen` ist, was bereit ist;
        # `dash_laden` von 0 bis 1 der Fortschritt der naechsten. Sie
        # fuellen sich nacheinander, nicht gleichzeitig.
        self.dash_ladungen = K.DASH["ladungen"]
        self.dash_laden = 0.0
        self.dash_rest = 0.0          # so lange laeuft der Stoss noch
        self.dash_bild_rest = 0.0     # Nachbild und Ausklang, auch fuer den Gast
        self.dash_sperre = 0.0
        self.dash_richtung = pygame.Vector2(1, 0)
        self.feuert = False
        self.punkte = 0
        # Wie oft dieser Spieler getroffen und erledigt hat - als Zaehler,
        # damit der Gast es ueber das Netz bekommt, ohne dass ein Treffer
        # zwischen zwei Meldungen verloren geht (TREFFERMARKE).
        self.treffer_marken = 0
        self.toedlich_marken = 0
        self._marke_zeit = -1.0
        self.tracer = False           # Zielhilfe an oder aus
        # Die Linie laeuft standardmaessig ueber den Mauszeiger hinaus bis
        # zur naechsten Wand. So sieht man, was man wirklich treffen wuerde,
        # statt nur, wo der Zeiger steht. Mit Z umschaltbar wie bisher.
        self.tracer_weit = True
        # Was diese Figur in der Runde getan hat. Ein Woerterbuch und
        # keine zwanzig Felder: was gezaehlt wird, steht in K.WERTE, und
        # neue Zahlen sollen dort dazukommen und nicht hier.
        self.zaehler: dict[str, float] = {}
        self.waffen_zaehler: dict[str, dict] = {}
        self.serie = 0                # laufende Abschussfolge, Tod setzt zurueck
        # Betriebsart je Waffe. Leer heisst: die erste aus K.WAFFEN[..]["modi"].
        self.modi: dict[str, str] = {}
        # Anlauf wie bei einer Minigun: 0 bis 1. Steigt, solange gefeuert
        # wird, und faellt sonst. Er entscheidet ueber den Takt - darum
        # bringt Antippen bei einem MG fast nichts.
        self.anlauf = 0.0
        self.salve_rest = 0           # wie viele Schuss die Salve noch hat
        self.salve_takt = 0.0
        # Der Takt der zweiten Pistole bzw. des zweiten Laufs (seit 0.34.62,
        # K.WAFFEN "zweite_hand" und "beide_laeufe"): rechte Maustaste.
        self.takt2 = 0.0
        # Energiewaffen (seit 0.34.68): wie weit aufgeladen (0 bis 1), und
        # wann die naechste Ladung abgekuehlt ist.
        self.ladung = 0.0
        self._flamme_rest = 0.0
        # Hitze der Chor-Waffen (seit 0.34.130): je Waffe, wie lange sie noch
        # ueberhitzt ist, und wann der naechste Teil abgekuehlt ist - auch fuer
        # die, die gerade nicht in der Hand ist.
        self.ueberhitzt: dict = {}
        self._kuehl: dict = {}
        self._kuehl_liste = ((), ())
        # Raketenwerfer. `rpg` heisst: er wird getragen, und dann traegt
        # man sonst nichts. `rpg_waffen` merkt sich, was vorher da war.
        self.rpg = False
        self.rpg_waffen: list[str] = []
        # Zielerfassung: auf wen, wie weit, und steht sie schon?
        self.erfasst = None
        self.erfassung = 0.0
        self.erfassung_rest = 0.0

    # ---- Zaehlen -----------------------------------------------------
    def zaehlen(self, name: str, wert: float = 1.0, waffe: str = "") -> None:
        """Eine Zahl hochsetzen. Die einzige Stelle, die das tut.

        `waffe` zaehlt zusaetzlich getrennt je Waffe - sonst laesst sich
        nie sagen, womit jemand wirklich spielt, und genau das braucht
        die Siegtafel spaeter fuer das Zeichen der meistbenutzten Waffe.
        """
        self.zaehler[name] = self.zaehler.get(name, 0.0) + wert
        if waffe:
            je = self.waffen_zaehler.setdefault(waffe, {})
            je[name] = je.get(name, 0.0) + wert

    def zaehler_leeren(self) -> None:
        """Vor einer neuen Runde. Der Zaehlerstand gehoert einer Runde."""
        self.zaehler = {}
        self.waffen_zaehler = {}
        self.serie = 0

    def werte_runde(self) -> dict:
        """Die Zahlen dieser Runde, so wie sie ins Journal gehen."""
        art = _werte_arten()
        werte = {}
        for s, wert in self.zaehler.items():
            if s not in art:
                continue
            werte[s] = int(wert) if float(wert).is_integer() else round(wert, 2)
        werte["abschuesse"] = int(self.abschuesse) if hasattr(self, "abschuesse") \
            else int(self.zaehler.get("abschuesse", 0))
        werte["tode"] = int(getattr(self, "tode", self.zaehler.get("tode", 0)))
        werte["abschuesse_r"] = werte["abschuesse"]
        werte["serie"] = int(self.zaehler.get("serie", 0))
        return werte

    def waffen_runde(self) -> dict:
        """Dasselbe je Waffe, auf die Schluessel in K.WAFFEN_WERTE begrenzt."""
        raus = {}
        for waffe, zahlen in self.waffen_zaehler.items():
            eintrag = {s: int(zahlen.get(s, 0)) for s in K.WAFFEN_WERTE
                       if zahlen.get(s)}
            if eintrag:
                raus[waffe] = eintrag
        return raus

    @property
    def streuung_jetzt(self) -> float:
        """Streuung in Grad, wie sie dieser Schuss haette."""
        d = self.waffe_daten
        grund = d.get("streuung", 0.0)
        fokus_ziel = d.get("fokus_streuung")
        if fokus_ziel is not None:
            grund = grund + (fokus_ziel - grund) * self.fokus
        # Ein MG wird genauer, je laenger man haelt - umgekehrt zu allem
        # anderen. Der Lauf laeuft sich ein, der Schuetze findet den
        # Rueckstoss. Wer antippt, trifft nichts; wer ein paar Sekunden
        # haelt, trifft sehr genau.
        ziel = d.get("streuung_ziel")
        if ziel is not None:
            dauer = max(0.05, d.get("streuung_dauer", 2.0))
            weit = min(1.0, self.halte_zeit / dauer)
            grund = grund + (ziel - grund) * weit
        # "Laeuft" heisst: die Figur **will** laufen. Nicht: sie bewegt
        # sich. Der Unterschied ist keine Feinheit - der eigene Rueckstoss
        # schiebt einen ebenfalls, und eine Waffe, die sich selbst durch
        # ihren Rueckstoss ungenauer macht, ist eine Waffe mit einem
        # Fehler. Dasselbe gilt fuer den, der gerade weggestossen wurde:
        # dafuer kann er nichts.
        steht = (self.will.length_squared() <= 0.01
                 and self.tempo.length_squared() <= 3600)
        if not steht:
            grund += d.get("streuung_lauf", 0.0) * (1.0 - 0.6 * self.fokus)
        elif d.get("streuung_stand") is not None:
            # Im Stehen deutlich enger. Nur die Salve hat das: sie ist die
            # Betriebsart fuer den, der eine Stellung haelt.
            grund *= d["streuung_stand"]
        return grund

    def _waffe_lesen(self) -> dict:
        """Die Werte der gehaltenen Waffe nur zum Lesen (seit 0.34.75).

        Ohne Betriebsart und ausser beim C4 ist `waffe_daten` eine Kopie
        von K.WAFFEN[name] - die Kopie kostete jeden Schritt jeder Figur
        mehrfach Zeit. Wer hier liest, schreibt nie hinein; sonst gilt
        `waffe_daten`."""
        name = self.waffen[self.waffe]
        d = K.WAFFEN[name]
        if name == "c4" or d.get("modus_daten"):
            return self.waffe_daten
        return d

    @property
    def waffe_daten(self) -> dict:
        """Die Werte der gehaltenen Waffe - samt gewaehlter Betriebsart.

        Hat eine Waffe `modus_daten`, wird der gewaehlte Satz darueber
        gelegt. Damit sieht der ganze uebrige Code weiterhin nur `takt`,
        `streuung` und so weiter, und keine einzige Stelle muss wissen,
        dass es ueberhaupt Betriebsarten gibt.
        """
        name = self.waffen[self.waffe]
        d = K.WAFFEN[name]
        gemischt = dict(d)
        modi = d.get("modus_daten")
        if modi:
            gemischt.update(modi.get(self.modus_von(name), {}))
        if name == "c4" and self.c4_ladungen:
            rest = self.c4_rest
            gemischt["name"] = "DETONATOR"
            gemischt["kurz"] = "BEREIT" if self.c4_bereit else "LADEN %.1f" % rest
        elif name == "c4" and self.c4_netz_rest >= 0:
            gemischt["name"] = "DETONATOR"
            gemischt["kurz"] = ("BEREIT" if self.c4_bereit else
                                 "LADEN %.1f" % self.c4_netz_rest)
        return gemischt

    @property
    def c4_ladungen(self) -> list:
        if self.welt is None:
            return []
        return [w for w in self.welt.wesen + self.welt.neue
                if isinstance(w, C4Ladung) and w.lebt and w.von is self]

    @property
    def c4_rest(self) -> float:
        ladungen = self.c4_ladungen
        if ladungen:
            return max(l.lade_rest for l in ladungen)
        return self.c4_netz_rest

    @property
    def c4_bereit(self) -> bool:
        ladungen = self.c4_ladungen
        if ladungen:
            return all(l.bereit for l in ladungen)
        return self.c4_netz_rest == 0.0

    # ---- Raketenwerfer -------------------------------------------------
    def rpg_nehmen(self) -> bool:
        """Den Raketenwerfer aufheben. Danach traegt man nur noch ihn.

        Das Brecheisen bleibt - es liegt auf F und belegt keinen Platz.
        Ohne das waere man mit leerem Rohr voellig wehrlos, und eine
        Waffe, die einen wehrlos macht, hebt niemand auf.
        """
        if self.rpg:
            return False
        self.rpg = True
        self.rpg_waffen = list(self.waffen)
        self.waffen = ["rakete"]
        self.waffe = 0
        self.magazin["rakete"] = K.WAFFEN["rakete"]["magazin"]
        self.takt = 0.0
        self.abbrechen()
        return True

    def rpg_ablegen(self) -> None:
        """Geschossen - zurueck zu dem, was man vorher trug."""
        if not self.rpg:
            return
        self.rpg = False
        self.waffen = self.rpg_waffen or list(K.HOTBAR)
        self.rpg_waffen = []
        self.waffe = 0
        self.erfasst = None
        self.erfassung = 0.0

    def _erfassung_fuehren(self, dt: float, d: dict) -> None:
        """Rechte Maustaste halten und dabei auf jemanden zeigen.

        Erfasst wird, wer nah genug an der Zeigerichtung liegt, in Sicht
        ist und nicht zur eigenen Mannschaft gehoert. Eine Etage tiefer
        geht nur ueber einem Loch - man muss ihn ja sehen koennen.

        Laesst man los oder verliert ihn aus den Augen, haelt die
        Erfassung noch `halten` Sekunden. Ohne diese Nachfrist reisst sie
        an jedem Pfosten ab, und das waere nur aergerlich.
        """
        e = K.ERFASSUNG
        if not self.rpg or not d.get("lenk_dreh") or not self.lenkbar:
            self.erfasst = None
            self.erfassung = 0.0
            return
        kandidat = self._erfassungsziel(e) if self.zielt else None
        if kandidat is not None:
            if kandidat is not self.erfasst and self.erfassung < 1.0:
                self.erfasst = kandidat
                self.erfassung = 0.0
            self.erfasst = kandidat
            vorher = self.erfassung
            self.erfassung = min(1.0, self.erfassung + dt / max(0.05, e["dauer"]))
            if vorher < 1.0 <= self.erfassung:
                # Genau einmal, im Augenblick des Einrastens. Der Ton sagt
                # dem Schuetzen, dass er loslassen kann - danach schaut er
                # wieder auf das Ziel statt auf den Ring.
                self.welt.klang("erfasst", 0.8)
            self.erfassung_rest = e["halten"]
            return
        # Kein Ziel im Zeiger: die Nachfrist laeuft.
        self.erfassung_rest = max(0.0, self.erfassung_rest - dt)
        if self.erfassung_rest <= 0.0 or self.erfasst is None \
                or not self.erfasst.lebt:
            self.erfasst = None
            self.erfassung = 0.0
        elif self.erfassung < 1.0:
            # Noch nicht fertig und schon verloren: sie faellt zurueck.
            self.erfassung = max(0.0, self.erfassung - dt / max(0.05, e["dauer"]))

    def _erfassungsziel(self, e: dict):
        """Wen der Zeiger gerade meint. None, wenn niemanden."""
        w = self.welt
        if w is None:
            return None
        bestes, bester_winkel = None, e["winkel"]
        for ziel in w.wesen:
            if ziel is self or not getattr(ziel, "lebt", False):
                continue
            if not getattr(ziel, "trefferbar", False) or getattr(ziel, "kaputt", False):
                continue
            if ziel.fraktion == self.fraktion:
                continue
            ab = ziel.pos - self.pos
            weite = ab.length()
            if weite > e["weite"] or weite < 1.0:
                continue
            if ziel.ebene > self.ebene:
                continue            # nach oben wird nicht erfasst
            if ziel.ebene < self.ebene:
                # Nur durch ein Loch. Geprueft wird an der Stelle des
                # Ziels auf **meiner** Ebene: dort muss der Boden fehlen,
                # sonst sehe ich ihn gar nicht.
                tx, ty = int(ziel.pos.x // K.TILE), int(ziel.pos.y // K.TILE)
                if not w.ebene(self.ebene).loch(tx, ty):
                    continue
            elif not w.sicht_frei(self.pos, ziel.pos, self.ebene):
                continue
            richtung = math.degrees(math.atan2(ab.y, ab.x))
            delta = abs((richtung - self.winkel + 180) % 360 - 180)
            if delta < bester_winkel:
                bestes, bester_winkel = ziel, delta
        return bestes

    # Ob der Werfer lenken darf. Setzt die Spielszene aus den Regeln des
    # Gastgebers - ohne Lenkung fliegt die Rakete geradeaus.
    lenkbar = True

    # ---- Gewicht: was eine schwere Waffe kostet ------------------------
    @property
    def am_feuern(self) -> float:
        """0 bis 1: wie sehr die Waffe gerade am Wirken ist.

        Nicht einfach `feuert`: ein MG wiegt auch dann noch schwer, wenn
        der Abzug schon los ist und der Lauf noch dreht. Umgekehrt soll
        man nicht schon beim ersten Antippen festkleben.
        """
        d = self._waffe_lesen()
        if not d.get("gewicht_tempo") and not d.get("gewicht_drehen"):
            return 0.0
        if d.get("modus_daten") or d.get("anlauf"):
            # Mit Anlauf zaehlt die Drehzahl, nicht der Finger.
            return max(self.anlauf, 1.0 if self.salve_rest > 0 else 0.0)
        return 1.0 if self.feuert else 0.0

    @property
    def gewicht_tempo(self) -> float:
        """Faktor auf das Lauftempo. 1.0 heisst: keine Behinderung."""
        d = self._waffe_lesen()
        voll = d.get("gewicht_tempo")
        if voll is None:
            return 1.0
        return 1.0 - (1.0 - voll) * self.am_feuern

    @property
    def dreh_grenze(self) -> float:
        """Grad je Sekunde, mehr geht nicht. 0 heisst: keine Grenze."""
        d = self._waffe_lesen()
        voll = d.get("gewicht_drehen")
        if not voll:
            return 0.0
        wirkt = self.am_feuern
        if wirkt <= 0.01:
            return 0.0
        # Zwischen "gar keine Grenze" und der vollen Grenze wird nicht
        # linear ueberblendet, sondern die Grenze wird angehoben: bei
        # halber Drehzahl darf man doppelt so schnell drehen.
        return voll / max(0.05, wirkt)

    def _anlauf_fuehren(self, dt: float, d: dict) -> None:
        """Die Drehzahl einer Minigun. Steigt beim Halten, faellt sonst."""
        auf = d.get("anlauf")
        if not auf:
            self.anlauf = 0.0
            return
        if self.feuert and self.magazin.get(self.waffe_name, 0) > 0:
            self.anlauf = min(1.0, self.anlauf + dt / max(0.01, auf))
        else:
            self.anlauf = max(0.0, self.anlauf
                              - dt / max(0.01, d.get("anlauf_abbau", 1.0)))

    def _salve_fuehren(self, dt: float, d: dict) -> None:
        """Eine angefangene Salve zu Ende schiessen, Schuss fuer Schuss.

        Die Schuesse einer Salve kommen fast gleichzeitig - `salve_takt`
        ist ein Bruchteil des normalen Takts. Trotzdem sind es einzelne
        Geschosse und keine Schrotladung: sie fliegen nacheinander los,
        jedes mit eigener Streuung.
        """
        if self.salve_rest <= 0:
            return
        self.salve_takt = max(0.0, self.salve_takt - dt)
        if self.salve_takt > 0.0:
            return
        self.salve_rest -= 1
        self.salve_takt = d.get("salve_takt", 0.03)
        if d.get("art") == "rakete":
            self._rakete_abgeben(d)
        else:
            self._schuss_abgeben(d)
        if self.salve_rest <= 0:
            self._zweit_modus = ""

    # ---- Betriebsarten -------------------------------------------------
    def modus_von(self, waffe: str) -> str:
        """Welche Betriebsart fuer diese Waffe gewaehlt ist."""
        modi = K.WAFFEN.get(waffe, {}).get("modi")
        if not modi:
            return ""
        zweit = self.__dict__.get("_zweit_modus")
        if zweit and zweit in modi and waffe == self.waffen[self.waffe]:
            return zweit
        gewaehlt = self.modi.get(waffe)
        return gewaehlt if gewaehlt in modi else modi[0]

    @property
    def modus(self) -> str:
        return self.modus_von(self.waffe_name)

    def modus_wechseln(self) -> str:
        """Auf die naechste Betriebsart schalten. Gibt die neue zurueck.

        Der Anlauf faellt dabei auf null: wer mitten im Dauerfeuer auf
        Salve schaltet, soll nicht die Drehzahl mitnehmen. Und der Takt
        wird neu gesetzt, sonst kaeme die erste Salve sofort.
        """
        waffe = self.waffe_name
        modi = K.WAFFEN.get(waffe, {}).get("modi")
        if not modi or len(modi) < 2:
            return ""
        jetzt = self.modus_von(waffe)
        neu = modi[(list(modi).index(jetzt) + 1) % len(modi)]
        self.modi[waffe] = neu
        self.anlauf = 0.0
        self.salve_rest = 0
        self.takt = max(self.takt, 0.18)
        return neu

    def nahkampf(self) -> bool:
        """Schlag mit dem Brecheisen, unabhaengig von der gewaehlten Waffe.

        Jederzeit auf einer eigenen Taste. Er hat seinen eigenen Takt und
        haelt die Schusswaffe nicht auf - was ihn aufhaelt, ist der Schwung
        selbst: waehrend er laeuft, ist die Waffe verstaut (siehe `bild`),
        und wer nichts in der Hand hat, schiesst auch nicht.
        """
        name = self.nahkampf_name
        d = K.WAFFEN.get(name)
        if d is None or self.nahkampf_rest > 0 or self.schlag_zeigen > 0 or self.gelaehmt:
            return False
        if self.nachlade_rest > 0 or self.heilt_rest > 0:
            return False
        # Die Klasse (seit 0.34.99): der NAHKAEMPFER schlaegt haerter und
        # schneller zu. Faktoren 1.0 lassen das Woerterbuch unberuehrt.
        f_schaden = getattr(self, "nahkampf_faktor", 1.0)
        f_takt = getattr(self, "nahkampf_takt_faktor", 1.0)
        if f_schaden != 1.0 or f_takt != 1.0:
            d = dict(d, schaden=d.get("schaden", 0) * f_schaden)
            for schluessel in ("takt", "wurf_takt", "f_takt"):
                if schluessel in d:
                    d[schluessel] = d[schluessel] * f_takt
        if d.get("f_werfen"):
            # Messer werden auf F immer geworfen (seit 0.34.96).
            if self.magazin.get(name, d.get("magazin", 0)) <= 0:
                return False
            self.magazin.setdefault(name, d.get("magazin", 0))
            self.nahkampf_rest = d["wurf_takt"]
            alt_takt = self.takt
            self.takt = 0.0
            self._werfen(d, name)
            self.takt = alt_takt
            return True
        if d.get("saege"):
            # Die Kettensaege auf F: ein kraeftiger Schnitt je Druck.
            d = dict(d, saege=False, schaden=d["schaden"] * d.get("f_schnitt", 4.0),
                     takt=d.get("f_takt", 0.55), schwung=0.18)
        self.nahkampf_rest = d["takt"]
        self.schlag_zeigen = d.get("schwung", 0.26) + K.NAHKAMPF["nachhalten"]
        self.schlagen(d)
        return True

    @property
    def nahkampf_name(self) -> str:
        """Was auf F liegt (seit 0.34.96): das Brecheisen oder die
        Nahkampfwaffe aus dem Loadout - sie belegt keinen Waffenplatz."""
        name = self.__dict__.get("nahkampf_waffe") or K.NAHKAMPF["waffe"]
        return name if name in K.WAFFEN else K.NAHKAMPF["waffe"]

    def schnellwurf(self) -> bool:
        """G (seit 0.34.96, nur Spieler): die erste Wurfwaffe mit Ladung sofort
        werfen, ohne zu ihr zu wechseln."""
        if self.gelaehmt or self.nachlade_rest > 0 or self.heilt_rest > 0 or self.schwingt:
            return False
        for i, name in enumerate(self.waffen):
            d = K.WAFFEN.get(name, {})
            if d.get("art") != "wurf":
                continue
            if self.magazin.get(name, 0) <= 0 and getattr(self, "vorrat", {}).get(name, 0) <= 0:
                continue
            alt, alt_takt = self.waffe, self.takt
            self.waffe = i
            self.takt = 0.0
            try:
                self.feuern()
            finally:
                self.waffe = alt
                self.takt = alt_takt
            return True
        return False

    @property
    def schwingt(self) -> bool:
        """Laeuft gerade ein Schlag mit dem Brecheisen?"""
        return self.schlag_zeigen > 0 and self.nahkampf_rest > 0

    def schwung_nummer(self) -> int:
        """Welches Bild der Schwungfolge gerade dran ist (seit 0.32.8).

        Der Schwung laeuft schnell an und laeuft aus; danach haelt die
        Figur das Eisen noch am Ende des Bogens (Nachhalten).
        """
        d = K.WAFFEN[K.NAHKAMPF["waffe"]]
        dauer = d.get("schwung", 0.26)
        lauf = self.schlag_zeigen - K.NAHKAMPF["nachhalten"]
        f = 1.0 - max(0.0, min(1.0, lauf / dauer))
        weg = 1.0 - (1.0 - f) * (1.0 - f)
        return int(round(weg * (K.SCHWUNG_BILDER - 1)))

    def schwung_bild(self, vorsatz: str = "") -> str:
        """Der Name des Schwungbilds (schwung_nummer), in den Farben der
        Mannschaft, wenn es die gibt."""
        i = self.schwung_nummer()
        name = "spieler_%sschwung_%d" % (vorsatz, i)
        return name if name in K.BILD_MASS else "spieler_schwung_%d" % i

    @property
    def bild(self) -> str:
        """Die Figur mit der Waffe, die sie gerade haelt.

        Gibt es zu der Waffe keine eigene Figur, bleibt die schlichte
        uebrig - eine neue Waffe faellt dadurch hoechstens auf die Vorgabe
        zurueck, statt ein fehlendes Bild zu zeigen.
        """
        # Waehrend des Schlags ist die Waffe verstaut: man sieht die
        # blosse Gestalt und darueber die Bewegung des Eisens. Das
        # Brecheisen selbst wird nie in der Hand gezeigt.
        if self.schwingt:
            return self.schwung_bild()
        if self.heilt_rest > 0:
            return "spieler_medkit"
        name = "spieler_" + self.waffe_name
        return name if name in K.BILD_MASS else "spieler"

    @property
    def waffe_name(self) -> str:
        return self.waffen[self.waffe]

    # ---- Ablauf ------------------------------------------------------
    def rueckstoss_wert(self, d: dict) -> float:
        """Wie stark ein Schuss den Schuetzen zurueckschiebt.

        Das MG hat zwei Werte: den schwachen (Vorgabe) und den vollen, den
        der Gastgeber als erweiterte Regel einschalten kann (`mg_schub`,
        setzt das Gefecht an jeder Figur).
        """
        if getattr(self, "mg_schub", False) and "rueckstoss_voll" in d:
            return float(d["rueckstoss_voll"])
        return float(d.get("rueckstoss", 0.0))

    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        s = K.SPIELER
        # Zustaende (seit 0.34.66): gelaehmt tut er nichts, festgenagelt
        # schiesst er noch, laeuft aber nicht. Die Eingabe kommt jedes Bild
        # neu (Gefecht), darum genuegt es, sie hier zu loeschen.
        if self.gehalten:
            self.will.update(0, 0)
            self.dash_rest = 0.0
            if self.gelaehmt:
                self.feuert = False
                self.zielt = False
        v = self.unverwundbar - dt
        self.unverwundbar = v if v > 0.0 else 0.0     # = max(0.0, v), schneller (0.34.75)
        v = self.takt - dt
        self.takt = v if v > 0.0 else 0.0     # = max(0.0, v), schneller (0.34.75)
        v = self.takt2 - dt
        self.takt2 = v if v > 0.0 else 0.0     # = max(0.0, v), schneller (0.34.75)
        rest = getattr(self, "faehigkeit_rest", None)
        if rest:
            for art in list(rest):              # Faehigkeit der Klasse (0.34.73)
                rest[art] = max(0.0, rest[art] - dt)
        # Blickrichtung. Normalerweise sofort - die Figur schaut dorthin,
        # wo die Maus steht, und zwar ohne Verzoegerung. Eine schwere
        # Waffe begrenzt das: mit dem MG im Anschlag dreht man sich nicht
        # auf der Stelle um, und genau das ist ihr Preis.
        # Wer am Boden liegt, dreht sich nicht mehr. Vorher folgte die
        # liegende Figur weiter der Maus und drehte sich am Boden im Kreis.
        # Wer einen Gefallenen zieht oder ihm aufhilft, schaut zu ihm
        # (Gefecht._ziehen, _revive), nicht zur Maus (seit 0.34.43).
        if (self.ziel - self.pos).length_squared() > 1 \
                and not self.am_boden \
                and self.zieht is None \
                and self.hilft is None:
            soll = math.degrees(math.atan2(self.ziel.y - self.pos.y,
                                           self.ziel.x - self.pos.x))
            grenze = self.dreh_grenze
            if grenze <= 0.0:
                self.winkel = soll
            else:
                ab = (soll - self.winkel + 180) % 360 - 180
                hoechstens = grenze * dt
                if abs(ab) <= hoechstens:
                    self.winkel = soll
                else:
                    self.winkel += hoechstens * (1.0 if ab > 0 else -1.0)
                    self.winkel = (self.winkel + 180) % 360 - 180
            # Im Beiwagen eines Krads (seit 0.34.121): nur so weit, wie der Sitz es zulaesst.
            sitz = getattr(self, "mitfahrt", None)
            if sitz is not None and hasattr(sitz, "beifahrer_klemmen"):
                self.winkel = sitz.beifahrer_klemmen(self.winkel)

        # Bewegung: beschleunigen in Wunschrichtung, sonst bremsen. Im Sturz
        # bleibt ein Teil der Steuerung, man kann also noch zur Seite ziehen.
        # Fokus der Scharfschuetzenwaffe: haelt man die rechte Maustaste,
        # zieht sich der Streifen zusammen, laesst man los, springt er auf.
        wd = self.waffe_daten
        fd = wd.get("fokus_dauer")
        if fd and self.zielt and self.sturz_rest <= 0:
            self.fokus = min(1.0, self.fokus + dt / fd)
        else:
            self.fokus = max(0.0, self.fokus - dt / 0.28)

        if self.heilt_rest > 0:
            self.heilt_rest -= dt
            if self.heilt_rest <= 0:
                self.heilt_rest = 0.0
                if self.lebt and not self.am_boden:
                    self.leben = min(self.max_leben,
                                     self.leben + K.MEDKIT["heilt"])
                    wolke(self.welt, self.pos, 10, 60, 0.6, K.C_TEAL,
                          self.ebene, 1)

        v = self.dash_bild_rest - dt
        self.dash_bild_rest = v if v > 0.0 else 0.0     # = max(0.0, v), schneller (0.34.75)
        # Wie lange der letzte Dash her ist (Schlagring, seit 0.34.66).
        self._seit_dash = 0.0 if self.dash_rest > 0 else getattr(self, "_seit_dash", 9.0) + dt

        v = self.schlag_zeigen - dt
        self.schlag_zeigen = v if v > 0.0 else 0.0     # = max(0.0, v), schneller (0.34.75)
        v = self.nahkampf_rest - dt
        self.nahkampf_rest = v if v > 0.0 else 0.0     # = max(0.0, v), schneller (0.34.75)
        if (self.am_boden and self.tempo.length_squared() < 0.01
                and self.will.length_squared() < 0.01 and self.sturz_rest <= 0):
            # Wer still am Boden liegt, hat keine Waffe in der Hand, laeuft
            # nicht und dasht nicht: nichts davon rechnen (seit 0.34.55,
            # gemeldet: "die performance leidet noch immer unter vielen bots
            # am boden"). Gezogen wird er von aussen (Gefecht._ziehen).
            self.halte_zeit = 0.0
            return
        self.halte_zeit = self.halte_zeit + dt if self.feuert else 0.0
        self._anlauf_fuehren(dt, wd)
        self._salve_fuehren(dt, wd)
        self._erfassung_fuehren(dt, wd)

        luft = K.STURZ["luftsteuerung"] if self.sturz_rest > 0 else 1.0
        if fd:
            luft *= 1.0 - (1.0 - wd.get("fokus_tempo", 1.0)) * self.fokus
        luft *= self.gewicht_tempo
        # Eine leichte Waffe macht flinker (seit 0.34.62, die MP).
        luft *= wd.get("tempo_faktor", 1.0)
        if self.ladung > 0.0:
            luft *= wd.get("tempo_beim_laden", 1.0)    # Spule, Kettenblitz (0.34.68)
        if self.schild:
            luft *= K.SCHILD["tempo"]           # Schildtraeger (seit 0.34.71)
        luft *= self.klassen_tempo   # die Klasse (seit 0.34.73)
        if self.draht_rest > 0.0:
            # Im Stacheldraht (seit 0.34.69, ausruestung).
            self.draht_rest -= dt
            luft *= K.AUSRUESTUNG["stacheldraht"]["tempo"]
        if self.heilt_rest > 0:
            # Wer ein Medkit anlegt, hat die Haende voll und geht langsamer.
            luft *= K.MEDKIT["tempo"]
        if self.zieht is not None:
            # Wer jemanden zieht, ebenso.
            luft *= K.ZIEHEN["tempo"]
        # Wer wiederbelebt wurde, geht langsamer (seit 0.34.40, Testmodus).
        luft *= self.tempo_anteil
        if self.sprintet:
            luft *= K.SPRINT["faktor"]        # Bots sprinten (seit 0.34.50)
        if self.sturz_rest <= 0 and self.welt is not None:
            # Seichtes Wasser bremst (seit 0.34.131, K.WASSER).
            luft *= self.welt.boden_tempo(self.pos, self.ebene)
        self._dash_laden(dt)
        # Fuer die Vorhersage beim Gast (seit 0.34.103, Gefecht).
        self._luft = luft
        ziel_tempo = self.will * s["tempo"] * luft
        rate = (s["beschleunigung"] if self.will.length_squared() > 0
                else s["bremsung"]) * luft
        if self.dash_rest > 0:
            # Waehrend des Stosses zaehlt nur er.
            self.dash_rest -= dt
            self.tempo.update(self.dash_richtung * K.DASH["tempo"])
            if self.dash_rest <= 0:
                # Am Ende auf knapp Lauftempo abfangen. Ohne das bremste
                # die normale Regel ihn von 430 px/s herunter, und dieses
                # Auslaufen allein trug noch einmal 66 Pixel - gemessen
                # 136 statt der gedachten 70. Ein Rest bleibt, damit er
                # weich auslaeuft statt an einer Kante abzubrechen.
                deckel = s["tempo"] * K.DASH["auslauf"]
                if self.tempo.length() > deckel:
                    self.tempo.scale_to_length(deckel)
        else:
            self.tempo.x = naehern(self.tempo.x, ziel_tempo.x, rate * dt)
            self.tempo.y = naehern(self.tempo.y, ziel_tempo.y, rate * dt)
        vor = pygame.Vector2(self.pos)
        # Wer still am Boden liegt, bewegt sich nicht und wird nicht geschoben
        # (world.auseinander) - gezogen wird er nur auf freien Boden. Nach
        # einer grossen Schlacht lagen sonst Dutzende, und jeder kostete so
        # viel wie einer, der laeuft (seit 0.34.52, gemeldet: "die Framerate
        # geht oft runter").
        if not (self.am_boden and self.tempo.length_squared() < 0.01
                and self.will.length_squared() < 0.01):
            self.welt.bewegen(self, self.tempo.x * dt, self.tempo.y * dt)
            self.welt.auseinander(self)
            self.welt.befreien(self)

        if self.sturz_rest > 0:
            pass                         # in der Luft kein Staub, kein Loch
        elif self.welt.loch_unter(self):
            self.stuerzen()              # ueber den Rand getreten
        else:
            # Schrittstaub. Derselbe Abstand zaehlt die gelaufene
            # Strecke mit - sie steht ohnehin schon da.
            gegangen = self.pos.distance_to(vor)
            self.weg += gegangen
            self.zaehlen("strecke", gegangen)
            if self.weg > s["stiefel_abstand"]:
                self.weg = 0.0
                if getattr(self.welt, "satz", "") == "schnee":
                    seit = pygame.Vector2(-self.tempo.y, self.tempo.x)
                    if seit.length_squared() > 0:
                        seit.scale_to_length(5.0)
                    pos = self.pos - self.tempo.normalize() * 5 if self.tempo.length_squared() else self.pos
                    for seite in (-1, 1):
                        p = pos + seit * seite
                        self.welt.schneespuren.append([p.x, p.y, self.ebene, self.welt.zeit])
                    if len(self.welt.schneespuren) > 900:
                        del self.welt.schneespuren[:100]
                elif self.welt.seicht(self.pos, self.ebene):
                    # Im Wasser (seit 0.34.131): Wellenringe statt Staub.
                    from . import effekte
                    effekte.ring(self.welt, self.pos.x, self.pos.y + 3, self.ebene,
                                 3.0, 15.0, 0.7, (178, 214, 222))
                elif not (getattr(self.welt, "satz", "") == "gruen"
                          and self.welt.ebene(self.ebene).kachel(
                              int(self.pos.x // K.TILE), int(self.pos.y // K.TILE))
                          in (K.BODEN, K.GESTRUEPP)):
                    # Auf einer Wiese staubt es nicht.
                    wolke(self.welt, self.pos + pygame.Vector2(0, 4), 2, 26, 0.34,
                          K.C_MUTED_DK, self.ebene, 1, "staub", 360, 0, 6.0)

        # Nachladen und Feuern laufen immer weiter: beim Laufen, im Sturz
        # und beim Dash. Keine Handlung sperrt eine andere aus - siehe
        # abbrechen(). Mit einer Ausnahme: waehrend ein Medkit angelegt
        # wird, hat die Figur es in der Hand und nicht die Waffe, und das
        # sieht man ihr an. Was sie nicht haelt, schiesst nicht. Das
        # Nachladen laeuft dabei weiter - es ist ein Zaehler, kein Griff.
        einzeln = wd.get("nachladen_einzeln")
        if (self.nachlade_rest > 0 and einzeln and self.feuert and self.takt <= 0
                and self.heilt_rest <= 0 and self.magazin.get(self.waffe_name, 0) > 0):
            # Patrone fuer Patrone (seit 0.34.62, Unterhebel): ein Schuss
            # unterbricht das Laden, was schon drin ist, bleibt drin.
            self.nachlade_rest = 0.0
            self.feuern()
        elif self.nachlade_rest > 0:
            self.nachlade_rest -= dt
            if self.nachlade_rest <= 0:
                name = self.waffe_name
                if einzeln:
                    self.magazin[name] = min(wd["magazin"], self.magazin.get(name, 0) + 1)
                    if self.magazin[name] < wd["magazin"]:
                        self.nachlade_rest = wd["nachladen"]    # die naechste
                else:
                    self.magazin[name] = self.waffe_daten["magazin"]
        elif self.waffe_name == "c4":
            if self.feuert and not self._c4_feuert_alt and self.heilt_rest <= 0:
                self.feuern()
            self._c4_feuert_alt = self.feuert
        elif wd.get("art") in ("strahl", "kette"):
            self._laden(dt, wd)
        elif self.feuert and self.takt <= 0 and self.heilt_rest <= 0:
            self.feuern()
        if wd.get("kuehlt") and self.magazin.get(self.waffe_name, 0) <= 0 \
                and self.waffe_name not in self.ueberhitzt:
            self._ueberhitzen(self.waffe_name, wd)
        self._abkuehlen(dt)
        # Die rechte Maustaste als zweiter Abzug (seit 0.34.62): die zweite
        # Pistole der Zwillinge, beide Laeufe der Doppelflinte.
        if ((wd.get("zweite_hand") or wd.get("beide_laeufe") or wd.get("zweit"))
                and self.zielt and self.takt2 <= 0
                and self.nachlade_rest <= 0 and self.heilt_rest <= 0):
            self._zweit_feuern(wd)

    # ---- Waffe -------------------------------------------------------
    def treffer_melden(self, ziel, toedlich: bool) -> None:
        """Ein eigener Treffer ist angekommen (Wesen.schaden)."""
        jetzt = getattr(self.welt, "zeit", 0.0)
        if toedlich:
            self.toedlich_marken += 1
        elif jetzt - self._marke_zeit >= K.TREFFERMARKE["abstand"] \
                or jetzt < self._marke_zeit:
            self.treffer_marken += 1
        else:
            return
        self._marke_zeit = jetzt

    # ---- Dash -----------------------------------------------------------
    def _dash_laden(self, dt: float) -> None:
        """Die Ladungen fuellen sich nacheinander wieder auf."""
        d = K.DASH
        v = self.dash_sperre - dt
        self.dash_sperre = v if v > 0.0 else 0.0     # = max(0.0, v), schneller (0.34.75)
        if self.dash_ladungen >= d["ladungen"]:
            self.dash_laden = 0.0
            return
        self.dash_laden += dt / d["nachladen"]
        if self.dash_laden >= 1.0:
            self.dash_ladungen += 1
            self.dash_laden = 0.0 if self.dash_ladungen >= d["ladungen"] else \
                self.dash_laden - 1.0

    @property
    def kann_dashen(self) -> bool:
        return (self.lebt and not getattr(self, "am_boden", False)
                and self.dash_ladungen > 0 and self.dash_sperre <= 0
                and self.dash_rest <= 0 and self.sturz_rest <= 0
                and self.heilt_rest <= 0
                and getattr(self, "zieht", None) is None)

    def dashen(self) -> bool:
        """Ein Stoss in Laufrichtung, oder in Blickrichtung, wenn man steht.

        Nicht im Fall, nicht am Boden, nicht beim Anlegen eines Medkits
        und nicht beim Ziehen eines Gefallenen: in allen vier Faellen hat
        man sich fuer etwas anderes entschieden, und der Dash waere ein
        Ausweg, der diese Entscheidung nichts kosten laesst.
        """
        if not self.kann_dashen or self.gehalten:
            return False
        richtung = pygame.Vector2(self.will)
        if richtung.length_squared() < 0.01:
            r = math.radians(self.winkel)
            richtung = pygame.Vector2(math.cos(r), math.sin(r))
        richtung.normalize_ip()
        self.dash_richtung = richtung
        self.dash_rest = K.DASH["dauer"]
        self.dash_bild_rest = K.DASH["dauer"] + K.DASH["bild_ausklang"]
        self.dash_sperre = K.DASH["sperre"]
        self.dash_ladungen -= 1
        w = self.welt
        if w is not None:
            wolke(w, self.pos, K.DASH["staub"], 110, 0.45, K.C_MUTED_DK,
                  self.ebene, 1, "staub")
            w.klang("dash", 0.6, self.pos, self.ebene)
        return True

    def nachladen(self) -> None:
        d = self.waffe_daten
        # Was man wirft und wieder aufhebt (Wurfmesser, Speer), laedt man
        # nicht nach (seit 0.34.67).
        if not d.get("magazin") or d.get("art") in ("wurf", "c4") or d.get("aufheben"):
            return
        if d.get("kuehlt"):
            # Chor-Waffen laden nicht nach, sie kuehlen ab (seit 0.34.130).
            return
        if self.nachlade_rest <= 0 and self.magazin[self.waffe_name] < d["magazin"]:
            # Der Schuetze laedt schneller (seit 0.34.73, Klasse).
            self.nachlade_rest = d["nachladen"] * getattr(self, "nachlade_faktor", 1.0)
            if self.welt is not None:
                self.welt.klang("reload", 0.55, self.pos, self.ebene)

    def abbrechen(self) -> None:
        """Beendet, was gerade laeuft, ohne es zu Ende zu bringen.

        Die Regel im Spiel lautet: jede Handlung darf jederzeit begonnen
        werden, und was noch nicht fertig war, wird dabei verworfen. Nie
        wartet der Spieler darauf, dass eine Leiste vollgelaufen ist. Wer
        spaeter eine Handlung dazunimmt - ein Terminal, eine Tuer - traegt
        ihren Abbruch hier ein, und alle Aufrufer stimmen weiter.
        """
        self.nachlade_rest = 0.0
        self.fokus = 0.0
        self.heilt_rest = 0.0

    def waffe_waehlen(self, index: int) -> None:
        """Waffe wechseln - immer, sofort, ohne Wartezeit.

        Frueher stand hier `takt = max(takt, 0.18)`: eine Ziehzeit, in der
        die neue Waffe noch nicht schoss. Im Gefecht fuehlte sich das an,
        als haette der Wechsel nicht funktioniert. Es gilt dieselbe Regel
        wie fuer alles andere: keine Handlung sperrt eine andere, und der
        Wechsel sperrt am wenigsten.
        """
        if 0 <= index < len(self.waffen) and index != self.waffe:
            self.waffe = index
            self.abbrechen()
            # Eine angefangene Salve gehoert zur alten Waffe (seit 0.34.62:
            # sechs Raketen ueber eine halbe Sekunde liefen sonst mit der
            # neuen weiter).
            self.salve_rest = 0

    def stuerzen(self) -> None:
        # Ein Dash darf die langsamere Luftsteuerung nicht ueberstimmen.
        self.dash_rest = 0.0
        if self.dash_bild_rest > 0.0:
            self.dash_bild_rest = K.DASH["bild_ausklang"]
        super().stuerzen()

    def heilen(self) -> bool:
        """Setzt ein Medkit an. Gibt zurueck, ob es losging."""
        if (self.medkits > 0 and self.heilt_rest <= 0
                and self.leben < self.max_leben):
            self.medkits -= 1
            self.heilt_rest = K.MEDKIT["dauer"]
            self.welt.klang("medkit", 0.7)
            self.zaehlen("medkits")
            return True
        return False

    def feuern(self) -> None:
        d = self.waffe_daten
        art = d.get("art", "schuss")
        if art == "nahkampf":
            self.schlagen()
            return
        if art == "flamme":
            self.takt = d["takt"]
            self._flammen(d)
            return
        if art == "kugel" and self.magazin.get(self.waffe_name, 0) > 0:
            # Der Kugelblitz (seit 0.34.68).
            self.takt = d["takt"]
            self.magazin[self.waffe_name] -= 1
            muendung = self.pos + pygame.Vector2(16, 0).rotate(self.winkel)
            self.welt.dazu(Kugelblitz(muendung, self.winkel, d, self.ebene, self,
                                      self.waffe_name))
            self.zaehlen("schuesse", 1.0, self.waffe_name)
            self.welt.schussknall(muendung, self.winkel, self.ebene, self.waffe_name, self)
            if self.magazin[self.waffe_name] <= 0:
                self.nachladen()
            return
        if art == "c4":
            ladungen = self.c4_ladungen
            if ladungen:
                if all(l.bereit for l in ladungen):
                    for ladung in ladungen:
                        ladung.detonieren()
                    self.magazin["c4"] = 1
                    self.c4_netz_rest = -1.0
                return
            if self.magazin.get("c4", 0) <= 0:
                return
            muendung = self.pos + pygame.Vector2(8, 0).rotate(self.winkel)
            weite = min(K.C4["wurfweite"], self.pos.distance_to(self.ziel))
            self.welt.dazu(C4Ladung(muendung, self.winkel, self.ebene, self, weite))
            self.magazin["c4"] = 0
            self.welt.ruckeln(0.6, "wurf", self.pos, self.ebene, self)
            self.welt.klang("wurf", 0.5, self.pos, self.ebene)
            self.zaehlen("granaten", 1.0, "c4")
            return
        if self.magazin[self.waffe_name] <= 0:
            if art == "wurf":
                vorrat = getattr(self, "vorrat", {})
                if vorrat.get(self.waffe_name, 0) > 0:
                    self.magazin[self.waffe_name] = 1
                    vorrat[self.waffe_name] -= 1
                else:
                    return
            else:
                self.nachladen()
                return
        # Der Takt einer Waffe mit Anlauf haengt an der Drehzahl: am
        # Anfang langsam, bei voller Drehzahl schnell. Genau dadurch
        # bringt Antippen bei einem MG fast nichts - der erste Schuss
        # kostet so viel wie sonst vier.
        anlauf_takt = d.get("anlauf_takt")
        if anlauf_takt is not None:
            self.takt = anlauf_takt + (d["takt"] - anlauf_takt) * self.anlauf
        else:
            self.takt = d["takt"]

        if art == "rakete":
            # Ein Raketenbuendel (seit 0.34.62) schiesst eine Salve wie das
            # MG: die erste sofort, den Rest holt _salve_fuehren nach.
            salve = d.get("salve")
            if salve and salve > 1:
                self.salve_rest = salve - 1
                self.salve_takt = d.get("salve_takt", 0.1)
            self._rakete_abgeben(d)
            return

        if art == "werfer":
            self._werfer_abgeben(d)
            return

        if art == "wurf":
            self.magazin[self.waffe_name] -= 1
            muendung = self.pos + pygame.Vector2(14, 0).rotate(self.winkel)
            # Sie fliegt dorthin, wo man hinzeigt, nicht immer gleich weit.
            weite = min(d["wurf_max"], max(d["wurf_min"],
                                           self.pos.distance_to(self.ziel)))
            if d.get("gerade"):
                # Gerade Wuerfe (seit 0.34.67): der Schneeball fliegt wie
                # ein Geschoss, ohne Bogen und ohne zu rollen.
                gr = Wurfkoerper(muendung, self.winkel, d, self.ebene, self, weite,
                                 self.waffe_name)
            else:
                gr = Granate(muendung, self.winkel, d, self.ebene, self, weite)
            # Fuer die Statistik je Waffe (Haftladung, EMP ...).
            gr.waffe = self.waffe_name
            self.welt.dazu(gr)
            self.welt.ruckeln(1.2, "wurf", self.pos, self.ebene, self)
            self.welt.klang("wurf", 0.6, self.pos, self.ebene)
            self.zaehlen("rauchwolken" if d.get("rauch") else "granaten",
                         1.0, self.waffe_name)
            return

        # Eine Salve ist **ein** Abzug und mehrere Geschosse. Der erste
        # Schuss geht sofort, die uebrigen holt `_salve_fuehren` Bild fuer
        # Bild nach - fast gleichzeitig, aber einzeln und mit eigener
        # Streuung. Eine Schrotladung waere etwas anderes: die faechert.
        salve = d.get("salve")
        if d.get("salve_trommel"):
            # Faechern (Revolver, seit 0.34.87): die ganze restliche Trommel.
            salve = max(1, self.magazin.get(self.waffe_name, 0))
        if salve and salve > 1:
            self.salve_rest = salve - 1
            self.salve_takt = d.get("salve_takt", 0.03)
        self._schuss_abgeben(d)

    def _rakete_abgeben(self, d: dict) -> None:
        """Eine Rakete: Munition, Rakete, Rueckstoss, Abschuss. Eigene
        Methode seit 0.34.62, weil das Raketenbuendel sie je Salve
        mehrfach braucht."""
        name = self.waffe_name
        if self.magazin.get(name, 0) <= 0:
            self.salve_rest = 0
            return
        self.magazin[name] -= 1
        muendung = self.pos + pygame.Vector2(18, 0).rotate(self.winkel)
        ziel = self.erfasst if self.erfassung >= 1.0 else None
        streuung = d.get("streuung", 0.0)
        richtung = self.winkel + RND.uniform(-streuung, streuung)
        self.welt.dazu(Rakete(muendung, richtung, d, self.ebene, self,
                              ziel, name))
        self.tempo -= pygame.Vector2(d.get("rueckstoss", 0.0),
                                     0).rotate(self.winkel)
        self.welt.raketenstart(muendung, self.winkel, self.ebene, self,
                               ziel)
        self.zaehlen("granaten", 1.0, name)
        if d.get("einweg") and self.magazin.get(name, 0) <= 0:
            self._rohr_ablegen(name)
        # Rohr leer: zurueck zu dem, was man vorher trug.
        self.rpg_ablegen()

    def _rohr_ablegen(self, name: str) -> None:
        """Das leere Einwegrohr (seit 0.34.62): zur Seite abgelegt, es
        rutscht aus und qualmt hinten noch (Welt.leichenflug, so sieht es
        auch jeder Gast). Danach die naechste Waffe, die noch schiesst."""
        seite = pygame.Vector2(0, 1).rotate(self.winkel)
        self.welt.leichenflug(self.pos + seite * 10, self.ebene, "teil_rohr_leer",
                              self.winkel, seite * 110 + self.tempo * 0.5,
                              0.5, RND.uniform(-90, 90), "", 4.0)
        for i, w in enumerate(self.waffen):
            if w != name and K.WAFFEN[w].get("art") in ("schuss", "werfer", "rakete"):
                self.waffe_waehlen(i)
                return

    def _werfer_abgeben(self, d: dict) -> None:
        """Eine Granate aus dem Granatwerfer (seit 0.34.62): im Bogen bis
        zum Zeiger, zwischen wurf_min und wurf_max."""
        name = self.waffe_name
        self.magazin[name] -= 1
        muendung = self.pos + pygame.Vector2(16, 0).rotate(self.winkel)
        # Ab der Muendung gerechnet: sie soll am Zeiger landen, nicht 16
        # Pixel dahinter.
        weite = min(d["wurf_max"], max(d["wurf_min"], muendung.distance_to(self.ziel)))
        streuung = d.get("streuung", 0.0)
        richtung = self.winkel + RND.uniform(-streuung, streuung)
        self.welt.dazu(Werfergranate(muendung, richtung, d, self.ebene, self, weite, name))
        self.tempo -= pygame.Vector2(d.get("rueckstoss", 0.0), 0).rotate(self.winkel)
        self.welt.schussknall(muendung, self.winkel, self.ebene, name, self)
        self.zaehlen("granaten", 1.0, name)

    def _zweit_feuern(self, d: dict) -> None:
        """Rechte Maustaste: die zweite Pistole (Zwillinge, eigener Takt,
        aus der anderen Hand) oder beide Laeufe auf einmal (Doppelflinte)."""
        if d.get("zweit") == "bodenschlag":
            if self.takt <= 0:
                self._bodenschlag(d)
            return
        if d.get("zweit") == "werfen":
            self._werfen(d)
            return
        if d.get("zweit") in d.get("modi", ()):
            # Eine Betriebsart auf der rechten Maustaste (Revolver: FAECHERN,
            # seit 0.34.138). Sie gilt fuer diesen Abzug und seine Salve.
            if self.takt > 0 or self.salve_rest > 0:
                return
            if self.magazin.get(self.waffe_name, 0) <= 0:
                self.nachladen()
                return
            self._zweit_modus = d["zweit"]
            self.feuern()
            self.takt2 = max(self.takt, 0.2)
            if self.salve_rest <= 0:
                self._zweit_modus = ""
            return
        name = self.waffe_name
        hat = self.magazin.get(name, 0)
        if hat <= 0:
            self.nachladen()
            return
        if d.get("beide_laeufe"):
            self.takt = self.takt2 = d["takt"]
            self._schuss_abgeben(d, laeufe=min(2, hat))
            return
        self.takt2 = d["takt"]
        self._schuss_abgeben(d, seite=-d.get("hand_abstand", 4.0))

    def _schuss_abgeben(self, d: dict, seite: float = 0.0, laeufe: int = 1) -> None:
        """Ein einzelner Schuss: Munition, Geschoss, Rueckstoss, Knall.

        Eigene Methode, weil eine Salve sie mehrfach braucht - und weil
        `feuern` sonst nicht mehr zu lesen waere. `seite`: so weit neben
        der Mitte liegt die Muendung (die zwei Pistolen der Zwillinge),
        `laeufe`: so viele Laeufe auf einmal (die Doppelflinte).
        """
        if self.magazin.get(self.waffe_name, 0) <= 0:
            self.salve_rest = 0
            return
        if d.get("zweite_hand") and not seite:
            seite = d.get("hand_abstand", 4.0)       # linke Maustaste: rechte Hand
        self.magazin[self.waffe_name] -= laeufe
        muendung = (self.pos + pygame.Vector2(14, 0).rotate(self.winkel)
                    + pygame.Vector2(0, seite).rotate(self.winkel))

        # Ein Abzug ist ein Schuss, auch bei Schrot mit acht Kuegelchen:
        # sonst laesst sich die Treffergenauigkeit einer Schrotflinte nicht
        # mit der eines Gewehrs vergleichen.
        self.zaehlen("schuesse", 1.0, self.waffe_name)
        streuung = self.streuung_jetzt
        if d.get("streuung_dauerfeuer"):
            streuung += d["streuung_dauerfeuer"] * min(1.0, self.halte_zeit)
        for _ in range(d["geschosse"] * laeufe):
            a = self.winkel + RND.uniform(-streuung, streuung)
            self.welt.dazu(Geschoss(muendung, a, d, self.ebene, self,
                                    self.waffe_name))
        # Der Schuss reisst die Waffe hoch. Wie weit, hat die Waffe (seit
        # 0.34.62): das Praezisionsgewehr bleibt fast auf der Linie.
        self.fokus *= d.get("fokus_schuss", 0.25)

        # Rueckstoss auf den Schuetzen. Blitz, Funken, Knall und der Schlag
        # auf die Kamera stehen zusammen in Welt.schussknall - dort, wo sie
        # auch ein Gast nachspielen kann, der selbst nichts rechnet.
        self.tempo -= pygame.Vector2(self.rueckstoss_wert(d) * laeufe, 0).rotate(self.winkel)
        self.welt.schussknall(muendung, self.winkel, self.ebene,
                              self.waffe_name, self)
        for _ in range(d["huelsen"]):
            aus = self.winkel + 90 + RND.uniform(-20, 20)
            self.welt.partikel.append(Partikel(
                self.pos, pygame.Vector2(RND.uniform(60, 110), 0).rotate(aus),
                0.8, (176, 140, 62), 1, "huelse", 4.0, self.ebene))

    def schlagen(self, daten: dict | None = None) -> None:
        """Kurzer Schlag in einen Kegel vor dem Spieler.

        `daten` erlaubt, mit einer anderen Waffe zu schlagen als der
        gehaltenen - das braucht der Schlag mit dem Brecheisen auf einer
        eigenen Taste, der ja gerade nicht die gewaehlte Waffe benutzt.
        """
        d = daten or self.waffe_daten
        # Mit welcher Waffe: das Brecheisen auf F, sonst die gehaltene
        # (Hammer, Schockstab, Schlagring, Kettensaege - seit 0.34.66).
        name = self.nahkampf_name if daten is not None else self.waffe_name
        if daten is None:
            self.takt = d["takt"]
        if d.get("saege"):
            self._saegen(d, name)
            return
        # Schwung und Nachhalten: das Eisen bleibt danach noch einen Moment
        # in der Hand (K.NAHKAMPF["nachhalten"]).
        self.schlag_zeigen = d.get("schwung", 0.26) + K.NAHKAMPF["nachhalten"]
        self.zaehlen("schuesse", 1.0, name)
        w = self.welt
        reich = d["reichweite"]
        halb = d["winkel"] * 0.5
        getroffen = 0
        treffer_art = "organisch"
        menge = d["schaden"]
        if d.get("dash_faktor") and (self.dash_rest > 0.0 or getattr(self, "_seit_dash", 9.0)
                                     <= d.get("dash_fenster", 0.3)):
            # Der Schlagring: ein Schlag aus dem Dash trifft haerter.
            menge *= d["dash_faktor"]
        for ziel in list(w.nahe(self.pos, reich + 20, self.ebene)):
            if ziel is self or ziel.fraktion == self.fraktion or not ziel.lebt:
                continue
            ab = ziel.pos - self.pos
            if ab.length() > reich + ziel.radius:
                continue
            delta = (math.degrees(math.atan2(ab.y, ab.x)) - self.winkel + 180) % 360 - 180
            if abs(delta) > halb:
                continue
            schub = ab.normalize() * d["schub"] if ab.length_squared() > 0.01 else None
            lebte = ziel.lebt
            schaden_an(ziel, menge, schub, self, "nahkampf", self.pos)
            abschuss_buchen(self, ziel, name, lebte)
            if d.get("betaeubt"):
                zustand_setzen(ziel, "betaeubt", d["betaeubt"])
                w.klang("schock", 0.8, ziel.pos, self.ebene)
            elif d.get("dash_faktor"):
                w.klang("schlag_faust", 0.7, ziel.pos, self.ebene)
            if getattr(ziel, "ist_boss", False) or getattr(ziel, "treffer_art", "") == "metall":
                treffer_art = "metall"
            if getattr(ziel, "zaehlt_treffer", True):
                self.zaehlen("kopftreffer", 1.0, name)
            getroffen += 1
        spitze = self.pos + pygame.Vector2(reich * 0.7, 0).rotate(self.winkel)
        # Ein Schlag entschaerft eine Sprengfalle (seit 0.34.69, ausruestung).
        # Ueber alle Wesen und nicht Welt.nahe: was niemanden stoesst und
        # nicht zu treffen ist, steht nicht im Raster.
        for a in w.wesen:
            if (getattr(a, "entschaerfen", None) is not None and a.lebt
                    and a.ebene == self.ebene and a.pos.distance_to(spitze) <= reich):
                a.entschaerfen()
        w.schlagknall(spitze, self.winkel, self.ebene, bool(getroffen), self,
                      treffer_art)

    def _ziele_vorn(self, reich: float, winkel: float) -> list:
        """Wer im Kegel vor ihm steht (nicht er selbst, nicht die eigenen)."""
        raus = []
        halb = winkel * 0.5
        for ziel in list(self.welt.nahe(self.pos, reich + 20, self.ebene)):
            if (ziel is self or ziel.fraktion == self.fraktion or not ziel.lebt
                    or ziel.fraktion == "geschoss" or not getattr(ziel, "trefferbar", True)):
                continue
            ab = ziel.pos - self.pos
            if ab.length() > reich + ziel.radius:
                continue
            delta = (math.degrees(math.atan2(ab.y, ab.x)) - self.winkel + 180) % 360 - 180
            if abs(delta) <= halb:
                raus.append(ziel)
        return raus

    def _saegen(self, d: dict, name: str) -> None:
        """Die Kettensaege (seit 0.34.66): ein Zug je `takt`, solange die
        Taste gehalten wird. Wen sie beruehrt, den haelt sie fest. Sie ist
        laut - Bots hoeren sie weit (Welt.laerm)."""
        if self.magazin.get(name, 0) <= 0:
            self.nachladen()
            return
        self.magazin[name] -= 1
        w = self.welt
        spitze = self.pos + pygame.Vector2(d["reichweite"] * 0.8, 0).rotate(self.winkel)
        getroffen = False
        for ziel in self._ziele_vorn(d["reichweite"], d["winkel"]):
            lebte = ziel.lebt
            schaden_an(ziel, d["schaden"], None, self, "nahkampf", self.pos)
            abschuss_buchen(self, ziel, name, lebte)
            zustand_setzen(ziel, "fest", K.ZUSTAENDE["saege_fest"])
            getroffen = True
        farbe = K.C_BLUT if getroffen else (255, 214, 140)
        wolke(w, spitze, 3, 120, 0.18, farbe, self.ebene, 1,
              "blut" if getroffen else "funke", 60, self.winkel + 90, 6.0)
        self._saege_rest = getattr(self, "_saege_rest", 0.0) - d["takt"]
        if self._saege_rest <= 0.0:
            # Nicht jeden Zug: der Laerm und der Ton gehen dreimal je Sekunde.
            self._saege_rest = 0.33
            self.zaehlen("schuesse", 1.0, name)
            w.schlagknall(spitze, self.winkel, self.ebene, getroffen, self)
            w.klang("kettensaege", 0.8, self.pos, self.ebene)
            w.laerm(self.pos, self.ebene, self, d.get("laerm", 600.0))

    def _ueberhitzen(self, name: str, d: dict) -> None:
        """Die Hitze ist voll (wo frueher das Magazin leer war, seit 0.34.130):
        die Waffe ist gesperrt, bis sie abgekuehlt ist - laenger als ein
        Nachladen. Einmal der Kuehlton, damit man weiss: ab jetzt kuehlt sie."""
        self.ueberhitzt[name] = d.get("ueberhitzt", d["nachladen"]) * getattr(self, "kuehl_faktor", 1.0)
        self.ladung = 0.0
        if self.welt is not None:
            self.welt.klang("ueberhitzt", 0.7, self.pos, self.ebene)

    def _abkuehlen(self, dt: float) -> None:
        """Chor-Waffen werden heiss statt leer (seit 0.34.68, seit 0.34.130 so):
        jede kuehlt fuer sich, auch weggesteckt. Ueberhitzt ist sie gesperrt,
        bis die Zeit um ist - dann ist sie ganz kalt. Sonst kommt in Ruhe alle
        `abkuehlen` Sekunden ein Teil zurueck; wer mit ihr schiesst oder laedt,
        haelt das an."""
        if self._kuehl_liste[0] != self.waffen:
            # Je Waffenliste einmal ausrechnen: das laeuft fuer jeden Kaempfer
            # in jedem Schritt (verglichen wird der Inhalt - die Liste kann
            # sich an Ort und Stelle aendern).
            self._kuehl_liste = (list(self.waffen), tuple(n for n in self.waffen if K.WAFFEN[n].get("kuehlt")))
        faktor = getattr(self, "kuehl_faktor", 1.0)
        for name in self._kuehl_liste[1]:
            d = K.WAFFEN[name]
            rest = self.ueberhitzt.get(name)
            if rest is not None:
                rest -= dt
                if rest <= 0.0:
                    del self.ueberhitzt[name]
                    self.magazin[name] = d["magazin"]
                    self._kuehl[name] = d["abkuehlen"] * faktor
                else:
                    self.ueberhitzt[name] = rest
                continue
            if name == self.waffe_name and (self.feuert or self.ladung > 0.0):
                self._kuehl[name] = d["abkuehlen"] * faktor
                continue
            if self.magazin.get(name, 0) >= d["magazin"]:
                continue
            rest = self._kuehl.get(name, d["abkuehlen"] * faktor) - dt
            if rest <= 0.0:
                rest = d["abkuehlen"] * faktor
                self.magazin[name] = self.magazin.get(name, 0) + 1
            self._kuehl[name] = rest

    def _laden(self, dt: float, d: dict) -> None:
        """Spulengewehr und Kettenblitz (seit 0.34.68): halten laedt auf.
        Der Kettenblitz feuert, sobald er voll ist; das Spulengewehr beim
        Loslassen, mit dem, was geladen ist."""
        name = self.waffe_name
        bereit = (self.takt <= 0 and self.heilt_rest <= 0
                  and self.magazin.get(name, 0) > 0)
        if self.feuert and bereit:
            if self.ladung <= 0.0 and d["art"] == "strahl":
                self.welt.klang("spule_laden", 0.6, self.pos, self.ebene)
            self.ladung = min(1.0, self.ladung + dt / d["ladezeit"])
            if d["art"] == "kette" and self.ladung >= 1.0:
                self._entladen(d, 1.0)
            return
        if self.ladung > 0.0 and d["art"] == "strahl" and bereit and self.ladung >= d["mindest"]:
            self._entladen(d, self.ladung)
        self.ladung = 0.0

    def _entladen(self, d: dict, ladung: float) -> None:
        name = self.waffe_name
        self.ladung = 0.0
        self.takt = d["takt"]
        self.magazin[name] -= 1
        if self.magazin[name] <= 0:
            self.nachladen()        # ueberhitzt
        self.zaehlen("schuesse", 1.0, name)
        w = self.welt
        muendung = self.pos + pygame.Vector2(14, 0).rotate(self.winkel)
        richtung = pygame.Vector2(1, 0).rotate(self.winkel)
        if d["art"] == "strahl":
            self._spule(d, ladung, muendung, richtung)
        else:
            self._kettenblitz(d, muendung, richtung)
        self.tempo -= richtung * self.rueckstoss_wert(d) * ladung
        w.schussknall(muendung, self.winkel, self.ebene, name, self)

    def _spule(self, d: dict, ladung: float, muendung, richtung) -> None:
        """Ein Strahl ohne Flugzeit, durch Waende und durch jeden Koerper
        auf der Linie."""
        w = self.welt
        reich = d["reichweite"]
        ende = muendung + richtung * reich
        getroffen = []
        schritt = 6.0
        n = int(reich / schritt)
        # Seit 0.34.87 verliert der Strahl an jeder Mauer und jedem Koerper
        # Kraft (K.WAFFEN["spule"] wand_verlust, koerper_verlust).
        kraft = 1.0
        in_wand = False
        for i in range(1, n + 1):
            p = muendung + richtung * (i * schritt)
            wand = w.schuss_halt(p, self.ebene, 0.0, True)
            if wand and not in_wand:
                kraft *= 1.0 - d.get("wand_verlust", 0.0)
            in_wand = wand
            ziel = w.treffer(p, 4.0, self.ebene, self.fraktion)
            if ziel is not None and ziel is not self and ziel not in [z_ for z_, _k in getroffen]:
                getroffen.append((ziel, kraft))
                kraft *= 1.0 - d.get("koerper_verlust", 0.0)
            if kraft < 0.05:
                ende = p
                break
        for ziel, anteil in getroffen:
            lebte = ziel.lebt
            if hasattr(self, "zaehlen") and getattr(ziel, "zaehlt_treffer", True):
                self.zaehlen("treffer", 1.0, self.waffe_name)
                treffer_ziel_buchen(self, ziel)
            schaden_an(ziel, d["schaden"] * ladung * anteil, richtung * 160.0 * ladung * anteil,
                       self, d.get("schadensart"), muendung, waffe=self.waffe_name)
            abschuss_buchen(self, ziel, self.waffe_name, lebte)
        w.entladung([muendung, ende], self.ebene, "spule")

    def _kettenblitz(self, d: dict, muendung, richtung) -> None:
        """Der erste im Kegel vor ihm, dann von Koerper zu Koerper, jedesmal
        schwaecher. Nur mit freier Sicht."""
        w = self.welt
        punkte = [pygame.Vector2(muendung)]
        getroffen = []
        jetzt = pygame.Vector2(muendung)
        reich = d["reichweite"]
        halb = d["kegel"]
        menge = d["schaden"]
        for sprung in range(d["spruenge"] + 1):
            bestes, beste_weite = None, 1e9
            weite_max = reich if sprung == 0 else d["sprung"]
            for z in w.nahe(jetzt, weite_max + 30.0, self.ebene):
                if (z is self or not z.lebt or z in getroffen
                        or getattr(z, "fraktion", "") in ("geschoss", self.fraktion)
                        or not getattr(z, "trefferbar", True)):
                    continue
                ab = z.pos - jetzt
                weit = ab.length()
                if weit > weite_max + z.radius or weit >= beste_weite:
                    continue
                if sprung == 0:
                    delta = (math.degrees(math.atan2(ab.y, ab.x)) - self.winkel + 180) % 360 - 180
                    if abs(delta) > halb:
                        continue
                if not w.sicht_frei(jetzt, z.pos, self.ebene):
                    continue
                bestes, beste_weite = z, weit
            if bestes is None:
                break
            lebte = bestes.lebt
            if getattr(bestes, "zaehlt_treffer", True):
                self.zaehlen("treffer", 1.0, self.waffe_name)
                treffer_ziel_buchen(self, bestes)
            schaden_an(bestes, menge, None, self, d.get("schadensart"), jetzt)
            abschuss_buchen(self, bestes, self.waffe_name, lebte)
            getroffen.append(bestes)
            jetzt = pygame.Vector2(bestes.pos)
            punkte.append(jetzt)
            menge *= d["abfall"]
        if len(punkte) == 1:
            punkte.append(w.strahl(muendung, richtung, reich * 0.6, self.ebene))
        w.entladung(punkte, self.ebene, "blitz")

    def _flammen(self, d: dict) -> None:
        """Der Flammenwerfer (seit 0.34.68): ein Zug je `takt`. Schaden im
        Kegel (Feuer, mit freier Sicht), brennende Streifen am Ende der
        Flamme, Rauch in der Flamme loest sich auf."""
        name = self.waffe_name
        if self.magazin.get(name, 0) <= 0:
            self.nachladen()
            return
        self.magazin[name] -= 1
        w = self.welt
        muendung = self.pos + pygame.Vector2(14, 0).rotate(self.winkel)
        reich = d["reichweite"]
        ende = w.strahl(muendung, pygame.Vector2(1, 0).rotate(self.winkel), reich, self.ebene)
        for ziel in self._ziele_vorn(reich, d["winkel"]):
            if not w.sicht_frei(muendung, ziel.pos, self.ebene):
                continue
            lebte = ziel.lebt
            schaden_an(ziel, d["schaden"], None, self, "feuer", muendung)
            abschuss_buchen(self, ziel, name, lebte)
        self._flamme_rest -= d["takt"]
        if self._flamme_rest <= 0.0:
            self._flamme_rest = d["streifen_takt"]
            self.zaehlen("schuesse", 1.0, name)
            w.feuer.append(Brandflaeche(ende, self.ebene, radius=d["streifen_radius"],
                                        dauer=d["streifen_dauer"], von=self))
        for r in w.rauch:
            if r.ebene == self.ebene and r.pos.distance_to(ende) < r.radius:
                # Das Feuer frisst den Rauch: die Wolke loest sich auf.
                r.alter = max(r.alter, r.dauer - K.RAUCH["abbau"] * d["rauch_fressen"])
        w.schussknall(muendung, self.winkel, self.ebene, name, self)

    def tank_pruefen(self) -> None:
        """Wer mit dem Flammenwerfer faellt, dessen Tank geht vielleicht
        hoch - wenn noch genug darin ist (seit 0.34.68)."""
        d = K.WAFFEN.get(self.waffe_name, {})
        if not d.get("flamme") or self.welt is None:
            return
        if self.magazin.get(self.waffe_name, 0) < d["magazin"] * d["tank_ab"]:
            return
        self.magazin[self.waffe_name] = 0
        w = self.welt
        r = d["tank_radius"]
        for ziel in list(w.nahe(self.pos, r + 20.0, self.ebene)):
            if ziel is self or not ziel.lebt or getattr(ziel, "fraktion", "") == "geschoss":
                continue
            weit = ziel.pos.distance_to(self.pos)
            if weit <= r + ziel.radius:
                schaden_an(ziel, d["tank_schaden"] * (1.0 - 0.5 * min(1.0, weit / r)), None,
                           self, "feuer", self.pos)
        w.feuer.append(Brandflaeche(self.pos, self.ebene, radius=r * 0.7, von=self))
        w.explosion(self.pos, self.ebene, r, "feuer")

    def _werfen(self, d: dict, name: str | None = None) -> None:
        """Wurfmesser und Speer werfen (seit 0.34.67): gerade, und danach
        liegt das Ding am Boden, bis jemand es aufhebt. `name` (seit
        0.34.96): das Messer auf F, nicht die Waffe in der Hand."""
        name = name or self.waffe_name
        if self.takt > 0 or self.magazin.get(name, 0) <= 0:
            return
        self.magazin[name] -= 1
        self.takt = self.takt2 = d["wurf_takt"]
        muendung = self.pos + pygame.Vector2(12, 0).rotate(self.winkel)
        weite = min(d["wurf_weite"], max(30.0, self.pos.distance_to(self.ziel)))
        self.welt.dazu(Wurfkoerper(muendung, self.winkel, d, self.ebene, self, weite, name))
        self.zaehlen("schuesse", 1.0, name)
        self.welt.klang("wurf_leise" if d.get("lautlos") else "wurf", 0.5, self.pos, self.ebene)

    def _bodenschlag(self, d: dict) -> None:
        """Der Hammer auf den Boden (seit 0.34.66): alles ringsum fliegt
        weg, die eigenen Leute nicht."""
        self.takt = self.takt2 = d["boden_takt"]
        self.schlag_zeigen = d.get("schwung", 0.3) + K.NAHKAMPF["nachhalten"]
        w = self.welt
        mitte = self.pos + pygame.Vector2(14, 0).rotate(self.winkel)
        r = d["boden_radius"]
        self.zaehlen("schuesse", 1.0, self.waffe_name)
        for ziel in list(w.nahe(mitte, r + 20, self.ebene)):
            if (ziel is self or ziel.fraktion == self.fraktion or not ziel.lebt
                    or ziel.fraktion == "geschoss" or not getattr(ziel, "trefferbar", True)):
                continue
            ab = ziel.pos - mitte
            weit = ab.length()
            if weit > r + ziel.radius:
                continue
            anteil = 1.0 - 0.5 * min(1.0, weit / r)
            schub = ab.normalize() * d["boden_schub"] * anteil if weit > 0.01 else None
            lebte = ziel.lebt
            schaden_an(ziel, d["boden_schaden"] * anteil, schub, self, "nahkampf", mitte)
            abschuss_buchen(self, ziel, self.waffe_name, lebte)
        w.explosion(mitte, self.ebene, r, "boden", self)

    # ---- Schaden -----------------------------------------------------
    def schaden(self, menge, schub=None, von=None) -> None:
        """Ein Treffer kommt an, solange kein Einstiegsschutz laeuft.

        Frueher setzte **jeder** Treffer eine halbe Sekunde
        Unverwundbarkeit. Das war nie so gedacht und hatte zwei haessliche
        Folgen: von einer Schrotladung zaehlte genau ein Kuegelchen, und
        wer beschossen wurde, blinkte nach jedem Schuss kurz wie frisch
        eingestiegen. Unverwundbarkeit gibt es jetzt nur noch dort, wo sie
        hingehoert - nach dem Einstieg, und nur, wenn der Gastgeber sie
        eingeschaltet hat.
        """
        if self.unverwundbar > 0:
            return
        # Der Anlass "treffer" gilt dem Getroffenen, nicht dem Schuetzen:
        # das Bild soll dem zucken, der die Kugel abbekommt.
        self.welt.ruckeln(5.5, "treffer", self.pos, self.ebene, self)
        super().schaden(menge, schub, von)

    def sterben(self, von=None) -> None:
        self.tank_pruefen()
        super().sterben(von)
        tod_zeigen(self, von)


# ══════════════════════════════════════════════════════════════════
# Gegner
# ══════════════════════════════════════════════════════════════════

class Gegner(Wesen):
    fraktion = "feind"
    # Gegner fahren nur, wenn der Aufzug auf ihrem Weg liegt
    # (_treppe_ansteuern), nicht schon, weil sie hineingedraengt wurden.
    # Gemessen auf STAUBTAL: ein Brecher, im Gedraenge vor der Tuer in
    # die Kabine geschoben, fuhr hinauf und gleich wieder herunter.
    faehrt_aufzug = False

    def __init__(self, pos, art: str, ebene=0, leben: float | None = None) -> None:
        d = K.gegner_daten(art)
        self.art = art
        self.daten = d
        # Ein Boss bekommt sein Leben von aussen gesetzt: es haengt davon
        # ab, wie viele mitspielen und wie viele Bosse schon lagen.
        self.max_leben = float(d["leben"] if leben is None else leben)
        super().__init__(pos, ebene)
        self.leben = self.max_leben
        self.radius = d["radius"]
        self.bild = d["bild"]
        self.schlag_rest = 0.0
        self.letzte_sicht = None
        self.wartet = RND.uniform(0.0, 0.4)
        self.treppen_sperre = 0.0
        self.drall = RND.choice((-1, 1))      # Ausweichrichtung an Hindernissen
        # Rueckstoss in einem eigenen Topf, nicht im Lauftempo: laufen
        # tut ein Gegner nie in ein Loch, geschoben werden kann er schon
        # hinein - und faellt dann (siehe schritt).
        self.stoss = pygame.Vector2(0, 0)
        self.ausweich_winkel = 0
        self.ausweich_rest = 0
        # Fernkampf, Platzen und Faehigkeit: alles drei steht in den
        # Daten und nicht in Unterklassen. Ein neuer Gegner ist damit ein
        # Eintrag in der Tabelle und kein neuer Zweig im Code.
        self.fern = d.get("fern")
        self.platzt = d.get("platzt")
        self.faehigkeit = d.get("faehigkeit")
        self.ist_boss = K.ist_boss(art)
        self.schiebbar = not d.get("unverschiebbar", False)
        self.fern_rest = RND.uniform(0.6, 1.8) if self.fern else 0.0
        # Faehigkeit: `rest` bis zum naechsten Mal, `vorlauf` laeuft,
        # waehrend sie schon angekuendigt ist. Der Vorlauf ist der Grund,
        # warum ein Boss fair ist - man sieht, was kommt, und hat Zeit.
        self.f_rest = (self.faehigkeit or {}).get("takt", 0.0) * 0.6
        self.f_vorlauf = 0.0
        self.f_ziel = None
        self.brut = []          # was die Mutter gerufen hat, fuer das Limit
        self.weg_rest = -1      # Kacheln bis zur naechsten Treppe, -1: kein Weg
        self.weg_nr = -1        # welche Treppe gerade angesteuert wird
        self.lauf_anteil = 1.0  # so viel seines Tempos (GOAP: herumschlurfen)

    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        self.schlag_rest = max(0.0, self.schlag_rest - dt)
        if self.sturz_rest > 0:
            return          # im Fall: kein Laufen, kein Schlagen
        self.treppen_sperre = max(0.0, self.treppen_sperre - dt)
        self.weg_rest = -1
        ziel = self._wohin(dt)

        if self.wartet > 0:
            self.wartet -= dt
            ziel = None
        self._laufen(dt, ziel)

    def _wohin(self, dt: float):
        """Was er jetzt will: der Punkt, auf den er zulaeuft (oder None),
        und nebenbei Schlagen, Spucken, Faehigkeit. Seit 0.34.30 eine
        eigene Methode - die zielorientierte KI (gegner_goap.py) ersetzt
        genau diesen Teil und behaelt das Laufen."""
        d = self.daten
        held = self.welt.held

        # Sie laufen immer los. Ist das Ziel nur ueber eine Treppe zu
        # erreichen, gehen sie den Weg dorthin (wege.py); ein Boss nicht,
        # der wartet auf seiner Ebene.
        ziel = None
        wege = None
        if held is not None and held.lebt and not self.ist_boss:
            wege = self.welt.wege
            if not wege.braucht_weg(self.ebene, self.pos, held.ebene, held.pos):
                wege = None
        if held is not None and held.lebt and wege is not None:
            # Das Ziel ist nur ueber eine Treppe zu erreichen: eine andere
            # Ebene, oder dieselbe, aber ein anderes Plateau. Dann wird die
            # naechste Treppe auf dem Weg angesteuert, nicht das Ziel -
            # geradewegs aufs Ziel zu fuehrte unter ein Plateau und vor
            # eine Felswand.
            ziel = self._treppe_ansteuern(wege, held)
        elif held is not None and held.lebt:
            ziel = pygame.Vector2(held.pos)
            if held.ebene == self.ebene:
                ziel = self._umweg(ziel, held)
            if held.ebene != self.ebene and self.ist_boss:
                # Ein Boss wechselt nicht die Ebene. Er wartet - wer ihn
                # meiden will, geht hinauf; wer ihn will, kommt herunter.
                ziel = None
            elif held.ebene == self.ebene:
                abstand = self.pos.distance_to(held.pos)
                if abstand < d["reichweite"] + held.radius and self.schlag_rest <= 0:
                    self.schlagen(held)
                # Ein Speier will gar nicht heran. Er haelt Abstand und
                # spuckt - und wenn man ihn draengt, weicht er zurueck.
                if self.fern:
                    ziel = self._fern_fuehren(dt, held, abstand, ziel)
                if self.faehigkeit:
                    self._faehigkeit_fuehren(dt, held)
            elif self.treppen_sperre <= 0 and not self.ist_boss:
                wohin = self.welt.treppe_unter(self)
                naeher = (abs(wohin - held.ebene) < abs(self.ebene - held.ebene)
                          if wohin is not None else False)
                if naeher and self.welt.ebene_wechseln(self, wohin):
                    self.treppen_sperre = 1.2
        return ziel

    def _laufen(self, dt: float, ziel) -> None:
        """Auf den Punkt zu (None: stehen bleiben), mit Ausweichen,
        Rueckstoss und Auseinanderdruecken."""
        d = self.daten
        if ziel is not None:
            richtung = ziel - self.pos
            if richtung.length_squared() > 1:
                richtung.normalize_ip()
                # Auf dem Weg zu einer Treppe fuehrt das Feld schon um jede
                # Wand herum. Der Faecher wuerde es nur verbiegen - und an
                # einer schmalen Rampe genau daneben laufen lassen.
                if self.weg_rest < 0:
                    richtung = self.ausweichen(richtung)
                self.winkel = math.degrees(math.atan2(richtung.y, richtung.x))
            soll = richtung * (d["tempo"] * self.lauf_anteil)
        else:
            soll = pygame.Vector2(0, 0)

        self.tempo.x = naehern(self.tempo.x, soll.x, d["beschleunigung"] * dt)
        self.tempo.y = naehern(self.tempo.y, soll.y, d["beschleunigung"] * dt)
        stoss_x, stoss_y = self.welt.bewegen(self, self.tempo.x * dt, self.tempo.y * dt)
        if stoss_x:
            self.tempo.x = 0
        if stoss_y:
            self.tempo.y = 0
        if stoss_x and stoss_y:
            self.drall = -self.drall      # Sackgasse, andersherum versuchen
        self._geschoben(dt, d)
        self.welt.auseinander(self)
        self.welt.befreien(self)

    @property
    def geschoben(self) -> bool:
        """Wird er gerade vom Rueckstoss getragen? (world.befreien fragt das.)"""
        return self.stoss.length_squared() > 1.0

    def _geschoben(self, dt: float, d: dict) -> None:
        """Der Rueckstoss: als Einziges darf er einen Gegner ueber eine Kante tragen.

        Selbst laeuft ein Gegner nie in ein Loch - die Kacheln zaehlen fuer
        ihn wie eine Wand (Wesen.faellt). Ein Rueckstoss kennt diese Wand
        nicht. Landet der Gegner dadurch ueber einem Loch, faellt er auf die
        Ebene darunter, wie eine Figur. Gedacht als Notbremse und nicht als
        Spielzug: vorher blieb ein Gegner, den eine Salve ueber den Rand
        schob, an der unsichtbaren Kante haengen.

        Gebremst wird wie vorher, als der Stoss noch im Lauftempo steckte
        (`beschleunigung`) - ein Treffer schiebt also genauso weit wie
        bisher, nur eben auch ueber eine Kante.
        """
        if self.stoss.length_squared() < 0.01:
            return
        sx, sy = self.welt.bewegen(self, self.stoss.x * dt, self.stoss.y * dt,
                                   loch_fest=False)
        if sx:
            self.stoss.x = 0.0
        if sy:
            self.stoss.y = 0.0
        self.stoss.x = naehern(self.stoss.x, 0.0, d["beschleunigung"] * dt)
        self.stoss.y = naehern(self.stoss.y, 0.0, d["beschleunigung"] * dt)
        if self.welt.loch_unter(self):
            self.stoss *= 0.5
            self.stuerzen()

    # ---- Um Hindernisse herum ------------------------------------------
    def _umweg(self, ziel, held):
        """Geradewegs, wenn der Weg frei ist - sonst ueber das Abstandsfeld.

        Der Faecher aus dem Ausweichen reicht fuer eine Kiste. An einer
        Plateauwand oder einem Band aus Loechern haengt er fest, und dann
        stand ein Gegner vor dem Spieler und kam nicht heran. Hier wird
        erst gefragt, ob der gerade Weg frei ist; nur wenn nicht, folgt der
        Gegner dem Feld zur Kachel des Spielers.
        """
        wege = self.welt.wege
        if wege.gerade_frei(self.ebene, self.pos, held.pos, self.radius):
            return ziel
        _schl, feld = wege.feld_zu(self.ebene, held.pos)
        punkt, rest = wege.schritt_ueber(self.ebene, feld, self.pos)
        if punkt is None:
            return ziel
        self.weg_rest = rest
        self.weg_nr = -2              # "Feld zum Ziel", fuer die Wache
        return punkt

    # ---- Ueber Treppen --------------------------------------------------
    def _treppe_ansteuern(self, wege, held):
        """Zur naechsten Treppe auf dem Weg gehen - und oben weiter.

        Gibt den Punkt zurueck, auf den als naechstes zugelaufen wird. Wer
        auf der Treppe steht, wechselt. `weg_rest` ist, wie weit es noch
        bis zur Treppe ist; die Haengerwache misst daran den Fortschritt,
        denn auf dem Weg zu einer Treppe entfernt man sich oft erst vom
        Ziel - und wuerde sonst fuer einen Haenger gehalten und umgesetzt.
        """
        nr = wege.naechste_treppe(self.ebene, self.pos, held.ebene, held.pos)
        if nr is None:
            # Kein Weg (etwa auf ein Plateau ohne Rampe): wie frueher
            # geradewegs zu. Die Haengerwache faengt das auf.
            return pygame.Vector2(held.pos)
        punkt, rest = wege.schritt_zu(nr, self.pos)
        self.weg_rest = rest
        self.weg_nr = nr
        _eb, tx, ty, ziel_ebene = wege.treppen[nr]
        # Gewechselt wird nur **auf** der Treppe. Hier stand `rest == 0` -
        # aber `schritt_zu` gibt den Rest der Nachbarkachel zurueck, auf
        # die es als naechstes geht, und der ist schon eine Kachel VOR der
        # Treppe null. Die Gegner wechselten also schraeg neben der Rampe
        # die Ebene, standen oben im Nichts neben der Rampe, kamen nicht
        # mehr weg und wurden nach ein paar Sekunden von der Haengerwache
        # umgesetzt - vor den Augen der Spieler (gemeldet: "laufen nicht
        # wirklich auf die Pads", "despawnen in Sicht").
        if (wege.kachel(self.pos) == (tx, ty) and self.treppen_sperre <= 0
                and self.welt.ebene_wechseln(self, ziel_ebene, loch_fest=True)):
            self.treppen_sperre = 1.0
            self.weg_rest = -1
        return punkt

    # ---- Fernkampf ------------------------------------------------------
    def _fern_fuehren(self, dt, ziel_wesen, abstand, ziel):
        """Der Speier: auf Abstand bleiben und spucken.

        Er hat drei Zonen statt zweier. Zu weit weg geht er vor, im Band
        bleibt er stehen und spuckt, zu nah geht er rueckwaerts. Ohne die
        dritte Zone klebt er an einem, sobald man einmal herangelaufen
        ist - und dann ist er ein langsamer Laeufer und nichts weiter.
        """
        f = self.fern
        self.fern_rest = max(0.0, self.fern_rest - dt)
        sicht = self.welt.sicht_frei(self.pos, ziel_wesen.pos, self.ebene)
        if abstand <= f["reichweite"] and sicht:
            if self.fern_rest <= 0.0:
                self._speien(ziel_wesen)
                self.fern_rest = f["takt"]
            if abstand < f["halten"]:
                # Rueckwaerts: weg vom Ziel, aber weiter hingedreht.
                weg = self.pos - ziel_wesen.pos
                if weg.length_squared() > 1:
                    return self.pos + weg.normalize() * 60
                return None
            return None          # im Band: stehenbleiben und spucken
        return ziel

    def _speien(self, ziel_wesen) -> None:
        f = self.fern
        richtung = ziel_wesen.pos - self.pos
        winkel = math.degrees(math.atan2(richtung.y, richtung.x))
        winkel += RND.uniform(-f["streuung"], f["streuung"])
        self.winkel = winkel
        daten = {"tempo": f["tempo"], "schaden": self.daten["schaden"],
                 "reichweite": f["reichweite"] * 1.25}
        g = Geschoss(self.pos, winkel, daten, self.ebene, von=self,
                     waffe=self.art)
        g.bild = f.get("bild", "speichel")
        g.spur = (126, 176, 86)
        self.welt.dazu(g)
        self.welt.klang("speien", 0.55, self.pos, self.ebene)

    # ---- Faehigkeiten der Bosse ----------------------------------------
    def _faehigkeit_fuehren(self, dt, ziel_wesen) -> None:
        """Ankuendigen, dann ausloesen.

        Der Vorlauf ist das Wesentliche daran. Ein Boss, der ohne
        Vorwarnung 34 Schaden im Umkreis macht, ist kein Boss, sondern
        eine Steuer - man kann nichts dagegen tun ausser Abstand halten,
        und dann ist das Muster "immer weglaufen". Mit Vorlauf wird es
        eine Frage: reicht die Zeit noch fuer einen Schuss?
        """
        f = self.faehigkeit
        if self.f_vorlauf > 0.0:
            self.f_vorlauf -= dt
            if self.f_vorlauf <= 0.0:
                self._faehigkeit_ausloesen(f)
            return
        self.f_rest -= dt
        if self.f_rest > 0.0:
            return
        self.f_rest = f["takt"]
        self.f_vorlauf = f["vorlauf"]
        self.f_ziel = pygame.Vector2(ziel_wesen.pos)
        if f["art"] == "brand":
            # Vorhalten: dorthin, wo das Ziel gleich sein wird. Sonst
            # laeuft jeder einfach aus dem Feuer heraus, waehrend es
            # entsteht, und die Faehigkeit trifft nie.
            self.f_ziel += ziel_wesen.tempo * f.get("vorhalt", 0.0)
            weg = self.f_ziel - self.pos
            if weg.length() > f["wurfweite"]:
                self.f_ziel = self.pos + weg.normalize() * f["wurfweite"]
        self.welt.aufschrift(self.pos, self.ebene,
                             {"stampfer": "STAMPFT", "brut": "RUFT",
                              "brand": "WIRFT"}.get(f["art"], ""), K.C_RED)
        self.welt.klang("boss_ansage", 0.7, self.pos, self.ebene)

    def _faehigkeit_ausloesen(self, f) -> None:
        w = self.welt
        art = f["art"]
        if art == "stampfer":
            # Trifft im Umkreis, auch hinter Deckung - darum ist die
            # Antwort Abstand und nicht eine Ecke.
            w.explosion(self.pos, self.ebene, f["radius"], "spreng")
            w.ruckeln(f["ruckeln"], "explosion", self.pos, self.ebene, self)
            for ding in w.nahe(self.pos, f["radius"], self.ebene):
                if getattr(ding, "fraktion", "") == "feind" or ding is self:
                    continue
                if not getattr(ding, "trefferbar", False) or not ding.lebt:
                    continue
                weit = self.pos.distance_to(ding.pos)
                if weit >= f["radius"]:
                    continue         # nahe() liefert ganze Zellen, nicht den Kreis
                anteil = 1.0 - weit / f["radius"]
                schub = ding.pos - self.pos
                if schub.length_squared() > 0.01:
                    schub = schub.normalize() * 260 * anteil
                schaden_an(ding, f["schaden"] * anteil, schub, self, "spreng", self.pos)
        elif art == "brut":
            self.brut = [g for g in self.brut if g.lebt]
            if len(self.brut) >= f["hoechstens"]:
                return
            for _ in range(f["anzahl"]):
                punkt = self.pos + pygame.Vector2(
                    RND.uniform(-f["streuung"], f["streuung"]),
                    RND.uniform(-f["streuung"], f["streuung"]))
                if not w.frei(punkt, 10, self.ebene):
                    continue
                kind = self._brut_erzeugen(punkt, f["was"])
                if kind is not None:
                    self.brut.append(kind)
                    w.dazu(kind)
            wolke(w, self.pos, 12, 130, 0.5, (96, 140, 70), self.ebene, 2, "blut")
        elif art == "brand":
            ziel = self.f_ziel if self.f_ziel is not None else self.pos
            w.feuer.append(Brandflaeche(ziel, self.ebene, radius=f["radius"],
                                        von=self, verschont="feind"))
            w.explosion(ziel, self.ebene, f["radius"] * 0.5, "feuer")

    def _brut_erzeugen(self, punkt, art: str):
        """Wie ein gerufener Gegner entsteht.

        Im Einzelspieler ist das ein gewoehnlicher Gegner. Im Mehrspieler
        muss er gezaehlt und gemeldet werden, und darum ueberschreibt
        KampfGegner diese eine Zeile statt der ganzen Faehigkeit.
        """
        return Gegner(punkt, art, self.ebene)

    def ausweichen(self, richtung: pygame.Vector2) -> pygame.Vector2:
        """Sucht eine freie Richtung nahe der gewuenschten.

        Kein A-Stern, nur ein Faecher von Proben: erst geradeaus, dann in
        immer groesseren Winkeln zu beiden Seiten, bevorzugt zur eigenen
        Ausweichseite. Das reicht, um an Kisten und Mauerstuecken
        vorbeizulaufen, statt davor stehen zu bleiben.
        """
        self.ausweich_rest -= 1
        if self.ausweich_rest > 0 and self.ausweich_winkel:
            return richtung.rotate(self.ausweich_winkel)
        w = self.welt
        probe = self.radius * 2.2 + 16
        self.ausweich_rest = 12          # erst in zwoelf Schritten neu pruefen
        for winkel in (0, 24, -24, 48, -48, 72, -72, 100, -100, 130, -130):
            g = winkel * self.drall
            d = richtung.rotate(g)
            if w.frei(self.pos + d * probe, self.radius, self.ebene, True):
                self.ausweich_winkel = g
                return d
        self.ausweich_winkel = 0
        return richtung

    def _platzen(self) -> None:
        """Der Blaeher geht hoch, wenn er stirbt.

        Er trifft dabei **keine anderen Gegner**. Das ist eine bewusste
        Entscheidung und keine Vergesslichkeit: wer den Blaeher in ein
        Rudel lockt und dort erschiesst, hat einen Trick gefunden, und
        ein Trick, der eine halbe Welle loescht, ersetzt das Spiel. Was
        er trifft, sind die Leute - also ist er genau das, was er sein
        soll: ein Grund, nicht beieinanderzustehen.
        """
        p = self.platzt
        w = self.welt
        w.explosion(self.pos, self.ebene, p["radius"], "feuer")
        w.ruckeln(2.8, "explosion", self.pos, self.ebene, self)
        for ding in w.nahe(self.pos, p["radius"], self.ebene):
            if ding is self or getattr(ding, "fraktion", "") == "feind":
                continue
            if not getattr(ding, "trefferbar", False) or not ding.lebt:
                continue
            weit = self.pos.distance_to(ding.pos)
            if weit >= p["radius"]:
                continue             # nahe() liefert ganze Zellen, nicht den Kreis
            anteil = 1.0 - weit / p["radius"]
            schub = ding.pos - self.pos
            if schub.length_squared() > 0.01:
                schub = schub.normalize() * 220 * anteil
            schaden_an(ding, p["schaden"] * anteil, schub, self, "spreng", self.pos)
        if p.get("zuendet"):
            # `verschont="feind"`, und zwar nach einer Messung: ohne das
            # toetete das Feuer eines einzigen Blaehers alle fuenf
            # Laeufer, die um ihn herumstanden. Damit waere "Blaeher ins
            # Rudel locken und erschiessen" ein Trick, der eine halbe
            # Welle loescht - und wer den Trick hat, spielt ihn und
            # nicht das Spiel. Der Molotow eines Spielers brennt
            # weiterhin alles, das ist ja seine Aufgabe.
            w.feuer.append(Brandflaeche(self.pos, self.ebene,
                                        radius=p["radius"] * 0.62,
                                        dauer=K.FEUER["dauer"] * 0.55, von=self,
                                        verschont="feind"))

    def schaden(self, menge: float, schub=None, von=None) -> None:
        # Ein Boss laesst sich nicht durch die Karte schieben. Ohne das
        # traegt ein Sturmgewehr den Koloss rueckwaerts aus der Halle -
        # und dann ist seine ganze Bedrohung eine Frage des Nachladens.
        if not self.schiebbar:
            schub = None
        if schub is not None:
            self.stoss += schub     # eigener Topf, siehe _geschoben
            schub = None
        super().schaden(menge, schub, von)

    def schlagen(self, ziel) -> None:
        self.schlag_rest = self.daten["schlagtakt"]
        schub = ziel.pos - self.pos
        if schub.length_squared() > 0.01:
            schub = schub.normalize() * 150
        schaden_an(ziel, self.daten["schaden"], schub, self, "nahkampf", self.pos)
        wolke(self.welt, (self.pos + ziel.pos) / 2, 5, 150, 0.2, K.C_ORANGE,
              self.ebene, 1, "funke")

    def sterben(self, von=None) -> None:
        super().sterben(von)
        w = self.welt
        tod_zeigen(self, von)
        wolke(w, self.pos, 6, 90, 0.7, K.C_MUTED_DK, self.ebene, 1, "staub")
        w.ruckeln(3.4 if self.ist_boss else 2.2, "tod", self.pos, self.ebene, self)
        w.kurz_langsam(K.TREFFER["zeitlupe"])
        if self.platzt:
            self._platzen()
        if isinstance(von, Spieler) or (von is not None and von.fraktion == "mensch"):
            held = w.held
            if held is not None:
                held.punkte += self.daten["punkte"]
