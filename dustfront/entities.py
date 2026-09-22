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
    schiebt = True
    trefferbar = True
    bild = None
    spur = None              # Farbe der Leuchtspur, None = keine
    radius = 8.0
    max_leben = 1.0
    schatten = True
    faellt = False           # True = kann in Loecher stuerzen

    def __init__(self, pos, ebene: int = 0) -> None:
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
        w.ruckeln(min(K.KAMERA["ruckeln_max"], st["ruckeln"] + h * 0.035))
        w.aufschlagring(self.pos, self.ebene, wucht)
        w.klang("sturz", 0.55 + 0.45 * wucht)
        self.schaden(schaden, None, None)

    def zeichenpos(self, alpha: float) -> pygame.Vector2:
        return self.vorher.lerp(self.pos, alpha)

    # ---- Schaden -----------------------------------------------------
    def schaden(self, menge: float, schub: pygame.Vector2 | None = None,
                von=None) -> None:
        if not self.lebt or self.leben <= 0:
            return
        self.leben -= menge
        self.blitz = K.TREFFER["blitz"]
        if schub is not None:
            self.tempo += schub
        if self.leben <= 0:
            self.sterben(von)

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


def wolke(welt, pos, anzahl, tempo, dauer, farbe, ebene, groesse=1,
          art="staub", streuung=360.0, richtung=0.0, reibung=3.0):
    for _ in range(anzahl):
        a = math.radians(richtung + RND.uniform(-streuung / 2, streuung / 2))
        v = RND.uniform(tempo * 0.35, tempo)
        welt.partikel.append(Partikel(
            pos, (math.cos(a) * v, math.sin(a) * v),
            dauer * RND.uniform(0.6, 1.2), farbe, groesse, art, reibung, ebene))


# ══════════════════════════════════════════════════════════════════
# Geschoss
# ══════════════════════════════════════════════════════════════════

class Geschoss(Wesen):
    fraktion = "geschoss"
    schiebt = False
    trefferbar = False
    schatten = False
    bild = "geschoss"
    spur = (250, 206, 128)
    radius = 2.0

    def __init__(self, pos, richtung: float, daten: dict, ebene: int,
                 von=None) -> None:
        super().__init__(pos, ebene)
        self.winkel = richtung
        r = math.radians(richtung)
        self.tempo = pygame.Vector2(math.cos(r), math.sin(r)) * daten["tempo"]
        self.schaden_wert = daten["schaden"]
        self.rest = daten["reichweite"]
        self.von = von
        self.quelle_fraktion = von.fraktion if von else "neutral"

    def schritt(self, dt: float) -> None:
        self.vorher.update(self.pos)
        weg = self.tempo * dt
        strecke = weg.length()
        if strecke <= 0:
            return
        # Unterteilen, damit nichts durch Waende oder Gegner fliegt
        schritte = max(1, int(strecke / 6.0))
        teil = weg / schritte
        e = self.welt.ebene(self.ebene)
        for _ in range(schritte):
            self.pos += teil
            self.rest -= teil.length()
            ziel = self.welt.treffer(self.pos, self.radius, self.ebene,
                                     self.quelle_fraktion)
            if ziel is not None and ziel is not self.von:
                self.einschlag(ziel)
                return
            if e.sichtdicht(int(self.pos.x // K.TILE), int(self.pos.y // K.TILE)):
                self.pos -= teil
                self.einschlag(None)
                return
            if self.rest <= 0:
                self.lebt = False
                return

    def einschlag(self, ziel) -> None:
        self.lebt = False
        richtung = math.degrees(math.atan2(self.tempo.y, self.tempo.x))
        if ziel is not None:
            schub = pygame.Vector2(self.tempo).normalize() * K.TREFFER["rueckstoss"]
            ziel.schaden(self.schaden_wert, schub, self.von)
            wolke(self.welt, self.pos, 6, 150, 0.22, K.C_BLUT, self.ebene, 1,
                  "blut", 110, richtung, 5.0)
        else:
            wolke(self.welt, self.pos, 5, 190, 0.18, (232, 196, 140), self.ebene,
                  1, "funke", 130, richtung + 180, 6.0)


# ══════════════════════════════════════════════════════════════════
# Granate
# ══════════════════════════════════════════════════════════════════

class Granate(Wesen):
    """Fliegt, prallt von Waenden ab und zuendet nach ihrer Flugzeit."""

    fraktion = "geschoss"
    schiebt = False
    trefferbar = False
    schatten = True
    radius = 3.0
    bild = "granate"
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
        self.bild = "rauchgranate" if daten.get("rauch") else "granate"
        self.rest = daten["flugzeit"]
        self.dreh = RND.uniform(-700, 700)
        # Anfangstempo so waehlen, dass sie nach der Reibung genau auf der
        # gewuenschten Weite liegen bleibt. Der Weg einer gebremsten Bewegung
        # ist v0 * (1 - e^(-k*t)) / k, das loesen wir nach v0 auf.
        if weite is None:
            weite = daten["wurf_max"]
        k = daten["reibung"]
        anteil = 1.0 - math.exp(-k * self.rest)
        v0 = weite * k / max(0.05, anteil)
        self.tempo = pygame.Vector2(v0, 0).rotate(richtung)

    def schritt(self, dt: float) -> None:
        self.vorher.update(self.pos)
        self.rest -= dt
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

    def aufschlag(self) -> None:
        """Aufsetzen nach einem Sturz - ohne Sturzschaden.

        Wesen.aufschlag() wuerde der Granate Fallschaden geben. Sie hat
        Leben wie jedes Wesen, waere danach tot und wuerde nie zuenden.
        """
        self.sturz_hoehe = 0.0
        self.pos.update(self.welt.landeplatz(self.pos, self.radius, self.ebene))
        self.vorher.update(self.pos)
        self.tempo *= 0.35
        wolke(self.welt, self.pos, 4, 60, 0.3, K.C_MUTED_DK, self.ebene, 1,
              "staub")

    def zuenden(self) -> None:
        self.lebt = False
        d = self.daten
        w = self.welt
        if d.get("rauch"):
            w.rauch.append(Rauchwolke(self.pos, self.ebene))
            wolke(w, self.pos, 12, 90, 0.6, K.RAUCH["toene"][0], self.ebene, 2)
            w.ruckeln(d["kamera"])
            w.klang("wurf", 0.8)
            return
        r = d["radius"]
        for ziel in list(w.nahe(self.pos, r + 30, self.ebene)):
            if not ziel.lebt or ziel is self:
                continue
            ab = ziel.pos - self.pos
            entfernung = ab.length()
            if entfernung > r + ziel.radius:
                continue
            # volle Wucht in der Mitte, am Rand ein Viertel
            anteil = 1.0 - 0.75 * min(1.0, entfernung / r)
            schub = (ab.normalize() * 320 * anteil) if entfernung > 0.01 else None
            ziel.schaden(d["schaden"] * anteil, schub, self.von)
        wolke(w, self.pos, 26, 340, 0.5, (255, 212, 140), self.ebene, 2, "funke")
        wolke(w, self.pos, 18, 150, 0.9, K.C_MUTED_DK, self.ebene, 2, "staub")
        w.brandfleck(self.pos, self.ebene, r)
        w.ruckeln(d["kamera"])
        w.kurz_langsam(0.05)
        w.klang("granate", 1.0)


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

    __slots__ = ("pos", "ebene", "radius", "dauer", "alter", "lebt", "_saat", "_feld")

    def __init__(self, pos, ebene: int, radius: float | None = None,
                 dauer: float | None = None, alter: float = 0.0) -> None:
        r = K.RAUCH
        self.pos = pygame.Vector2(pos)
        self.ebene = int(ebene)
        self.radius = float(r["radius"] if radius is None else radius)
        self.dauer = float(r["dauer"] if dauer is None else dauer)
        self.alter = float(alter)
        self.lebt = True
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

class Aufsammler(Wesen):
    """Liegt herum, bis jemand darueber laeuft."""

    fraktion = "beute"
    schiebt = False
    trefferbar = False
    radius = 8.0

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
        self.fokus = 0.0              # 0 = aus der Hueffte, 1 = ganz ruhig
        self.zielt = False            # rechte Maustaste
        self.medkits = 1
        self.heilt_rest = 0.0
        self.halte_zeit = 0.0         # wie lange der Abzug schon gedrueckt ist
        self.schlag_zeigen = 0.0      # Restzeit der Nahkampf-Anzeige
        self.takt = 0.0
        self.nachlade_rest = 0.0
        self.unverwundbar = 0.0
        self.weg = 0.0                 # fuer Schrittstaub
        self.ziel = pygame.Vector2(pos) + pygame.Vector2(1, 0)
        self.will = pygame.Vector2(0, 0)
        self.sprint = False
        self.feuert = False
        self.punkte = 0
        self.tracer = False           # Zielhilfe an oder aus
        self.tracer_weit = False      # laeuft sie ueber den Mauszeiger hinaus

    @property
    def streuung_jetzt(self) -> float:
        """Streuung in Grad, wie sie dieser Schuss haette."""
        d = self.waffe_daten
        grund = d.get("streuung", 0.0)
        fokus_ziel = d.get("fokus_streuung")
        if fokus_ziel is not None:
            grund = grund + (fokus_ziel - grund) * self.fokus
        if self.tempo.length_squared() > 400:
            grund += d.get("streuung_lauf", 0.0) * (1.0 - 0.6 * self.fokus)
        return grund

    @property
    def waffe_daten(self) -> dict:
        return K.WAFFEN[self.waffen[self.waffe]]

    @property
    def bild(self) -> str:
        """Die Figur mit der Waffe, die sie gerade haelt.

        Gibt es zu der Waffe keine eigene Figur, bleibt die schlichte
        uebrig - eine neue Waffe faellt dadurch hoechstens auf die Vorgabe
        zurueck, statt ein fehlendes Bild zu zeigen.
        """
        name = "spieler_" + self.waffe_name
        return name if name in K.BILD_MASS else "spieler"

    @property
    def waffe_name(self) -> str:
        return self.waffen[self.waffe]

    # ---- Ablauf ------------------------------------------------------
    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        s = K.SPIELER
        self.unverwundbar = max(0.0, self.unverwundbar - dt)
        self.takt = max(0.0, self.takt - dt)
        # Blickrichtung
        if (self.ziel - self.pos).length_squared() > 1:
            self.winkel = math.degrees(math.atan2(self.ziel.y - self.pos.y,
                                                  self.ziel.x - self.pos.x))

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
                self.leben = min(self.max_leben, self.leben + K.MEDKIT["heilt"])
                wolke(self.welt, self.pos, 10, 60, 0.6, K.C_TEAL, self.ebene, 1)

        self.schlag_zeigen = max(0.0, self.schlag_zeigen - dt)
        self.halte_zeit = self.halte_zeit + dt if self.feuert else 0.0

        luft = K.STURZ["luftsteuerung"] if self.sturz_rest > 0 else 1.0
        if fd:
            luft *= 1.0 - (1.0 - wd.get("fokus_tempo", 1.0)) * self.fokus
        ziel_tempo = self.will * s["tempo"] * (s["sprint"] if self.sprint else 1.0) * luft
        rate = (s["beschleunigung"] if self.will.length_squared() > 0
                else s["bremsung"]) * luft
        self.tempo.x = naehern(self.tempo.x, ziel_tempo.x, rate * dt)
        self.tempo.y = naehern(self.tempo.y, ziel_tempo.y, rate * dt)
        vor = pygame.Vector2(self.pos)
        self.welt.bewegen(self, self.tempo.x * dt, self.tempo.y * dt)
        self.welt.auseinander(self)
        self.welt.befreien(self)

        if self.sturz_rest > 0:
            pass                         # in der Luft kein Staub, kein Loch
        elif self.welt.loch_unter(self):
            self.stuerzen()              # ueber den Rand getreten
        else:
            # Schrittstaub
            self.weg += self.pos.distance_to(vor)
            if self.weg > s["stiefel_abstand"]:
                self.weg = 0.0
                wolke(self.welt, self.pos + pygame.Vector2(0, 4), 2, 26, 0.34,
                      K.C_MUTED_DK, self.ebene, 1, "staub", 360, 0, 6.0)

        # Nachladen und Feuern laufen immer weiter: beim Rennen, im Sturz,
        # und waehrend ein Medkit angelegt wird. Keine Handlung sperrt eine
        # andere aus - siehe abbrechen().
        if self.nachlade_rest > 0:
            self.nachlade_rest -= dt
            if self.nachlade_rest <= 0:
                self.magazin[self.waffe_name] = self.waffe_daten["magazin"]
        elif self.feuert and self.takt <= 0:
            self.feuern()

    # ---- Waffe -------------------------------------------------------
    def nachladen(self) -> None:
        d = self.waffe_daten
        if not d.get("magazin"):
            return
        if self.nachlade_rest <= 0 and self.magazin[self.waffe_name] < d["magazin"]:
            self.nachlade_rest = d["nachladen"]

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

    def heilen(self) -> bool:
        """Setzt ein Medkit an. Gibt zurueck, ob es losging."""
        if (self.medkits > 0 and self.heilt_rest <= 0
                and self.leben < self.max_leben):
            self.medkits -= 1
            self.heilt_rest = K.MEDKIT["dauer"]
            self.welt.klang("medkit", 0.7)
            return True
        return False

    def feuern(self) -> None:
        d = self.waffe_daten
        art = d.get("art", "schuss")
        if art == "nahkampf":
            self.schlagen()
            return
        if self.magazin[self.waffe_name] <= 0:
            self.nachladen()
            return
        self.magazin[self.waffe_name] -= 1
        self.takt = d["takt"]
        muendung = self.pos + pygame.Vector2(14, 0).rotate(self.winkel)

        if art == "wurf":
            # Sie fliegt dorthin, wo man hinzeigt, nicht immer gleich weit.
            weite = min(d["wurf_max"], max(d["wurf_min"],
                                           self.pos.distance_to(self.ziel)))
            self.welt.dazu(Granate(muendung, self.winkel, d, self.ebene, self,
                                   weite))
            self.welt.ruckeln(1.2)
            self.welt.klang("wurf", 0.6)
            return

        streuung = self.streuung_jetzt
        if d.get("streuung_dauerfeuer"):
            streuung += d["streuung_dauerfeuer"] * min(1.0, self.halte_zeit)
        for _ in range(d["geschosse"]):
            a = self.winkel + RND.uniform(-streuung, streuung)
            self.welt.dazu(Geschoss(muendung, a, d, self.ebene, self))
        self.fokus *= 0.25            # der Schuss reisst die Waffe hoch

        # Rueckstoss auf den Schuetzen und auf die Kamera
        self.tempo -= pygame.Vector2(d.get("rueckstoss", 0.0), 0).rotate(self.winkel)
        self.welt.ruckeln(d["kamera"])
        self.welt.klang("schuss_" + self.waffe_name, K.AUDIO["schuss"])
        self.welt.muendung(muendung, self.winkel, self.ebene)
        wolke(self.welt, muendung, 3, 120, 0.12, (255, 226, 160), self.ebene, 1,
              "funke", 34, self.winkel, 8.0)
        for _ in range(d["huelsen"]):
            aus = self.winkel + 90 + RND.uniform(-20, 20)
            self.welt.partikel.append(Partikel(
                self.pos, pygame.Vector2(RND.uniform(60, 110), 0).rotate(aus),
                0.8, (176, 140, 62), 1, "huelse", 4.0, self.ebene))

    def schlagen(self) -> None:
        """Kurzer Schlag in einen Kegel vor dem Spieler."""
        d = self.waffe_daten
        self.takt = d["takt"]
        self.schlag_zeigen = d.get("schwung", 0.26)
        w = self.welt
        reich = d["reichweite"]
        halb = d["winkel"] * 0.5
        getroffen = 0
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
            ziel.schaden(d["schaden"], schub, self)
            getroffen += 1
        spitze = self.pos + pygame.Vector2(reich * 0.7, 0).rotate(self.winkel)
        wolke(w, spitze, 6 if getroffen else 3, 160, 0.18,
              K.C_CREAM if getroffen else K.C_MUTED, self.ebene, 1, "funke",
              d["winkel"], self.winkel, 7.0)
        w.ruckeln(d["kamera"] if getroffen else 0.8)
        w.klang("nahkampf", 0.7)

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
        self.welt.ruckeln(5.5)
        super().schaden(menge, schub, von)

    def sterben(self, von=None) -> None:
        super().sterben(von)
        wolke(self.welt, self.pos, 22, 210, 0.8, K.C_BLUT, self.ebene, 2, "blut")


# ══════════════════════════════════════════════════════════════════
# Gegner
# ══════════════════════════════════════════════════════════════════

class Gegner(Wesen):
    fraktion = "feind"

    def __init__(self, pos, art: str, ebene=0) -> None:
        d = K.GEGNER[art]
        self.art = art
        self.daten = d
        self.max_leben = d["leben"]
        super().__init__(pos, ebene)
        self.radius = d["radius"]
        self.bild = d["bild"]
        self.schlag_rest = 0.0
        self.letzte_sicht = None
        self.wartet = RND.uniform(0.0, 0.4)
        self.treppen_sperre = 0.0
        self.drall = RND.choice((-1, 1))      # Ausweichrichtung an Hindernissen
        self.ausweich_winkel = 0
        self.ausweich_rest = 0

    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        d = self.daten
        self.schlag_rest = max(0.0, self.schlag_rest - dt)
        held = self.welt.held

        # Sie laufen immer los. Auf einer anderen Ebene gehen sie zur Stelle
        # unter oder ueber dem Spieler und nehmen die naechste Treppe.
        ziel = None
        self.treppen_sperre = max(0.0, self.treppen_sperre - dt)
        if held is not None and held.lebt:
            ziel = pygame.Vector2(held.pos)
            if held.ebene == self.ebene:
                abstand = self.pos.distance_to(held.pos)
                if abstand < d["reichweite"] + held.radius and self.schlag_rest <= 0:
                    self.schlagen(held)
            elif self.treppen_sperre <= 0:
                wohin = self.welt.treppe_unter(self)
                naeher = (abs(wohin - held.ebene) < abs(self.ebene - held.ebene)
                          if wohin is not None else False)
                if naeher and self.welt.ebene_wechseln(self, wohin):
                    self.treppen_sperre = 1.2

        if self.wartet > 0:
            self.wartet -= dt
            ziel = None

        if ziel is not None:
            richtung = ziel - self.pos
            if richtung.length_squared() > 1:
                richtung.normalize_ip()
                richtung = self.ausweichen(richtung)
                self.winkel = math.degrees(math.atan2(richtung.y, richtung.x))
            soll = richtung * d["tempo"]
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
        self.welt.auseinander(self)
        self.welt.befreien(self)

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

    def schlagen(self, ziel) -> None:
        self.schlag_rest = self.daten["schlagtakt"]
        schub = ziel.pos - self.pos
        if schub.length_squared() > 0.01:
            schub = schub.normalize() * 150
        ziel.schaden(self.daten["schaden"], schub, self)
        wolke(self.welt, (self.pos + ziel.pos) / 2, 5, 150, 0.2, K.C_ORANGE,
              self.ebene, 1, "funke")

    def sterben(self, von=None) -> None:
        super().sterben(von)
        w = self.welt
        wolke(w, self.pos, 14, 190, 0.55, K.C_BLUT, self.ebene, 2, "blut")
        wolke(w, self.pos, 6, 90, 0.7, K.C_MUTED_DK, self.ebene, 1, "staub")
        w.blutfleck(self.pos, self.ebene, self.radius)
        w.ruckeln(2.2)
        w.kurz_langsam(K.TREFFER["zeitlupe"])
        if isinstance(von, Spieler) or (von is not None and von.fraktion == "mensch"):
            held = w.held
            if held is not None:
                held.punkte += self.daten["punkte"]
