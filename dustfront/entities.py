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
        return self.vorher.lerp(self.pos, alpha)

    # ---- Schaden -----------------------------------------------------
    def schaden(self, menge: float, schub: pygame.Vector2 | None = None,
                von=None) -> None:
        if not self.lebt or self.leben <= 0:
            return
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
    schiebt = False
    trefferbar = False
    schatten = False
    bild = "geschoss"
    spur = (250, 206, 128)
    radius = 2.0

    def __init__(self, pos, richtung: float, daten: dict, ebene: int,
                 von=None, waffe: str = "") -> None:
        super().__init__(pos, ebene)
        self.winkel = richtung
        r = math.radians(richtung)
        self.tempo = pygame.Vector2(math.cos(r), math.sin(r)) * daten["tempo"]
        self.schaden_wert = daten["schaden"]
        self.rest = daten["reichweite"]
        self.von = von
        # Der Stoss auf das Ziel gilt je Schuss, nicht je Kugel: vorher
        # schob jede der sieben Schrotkugeln einzeln, und aus naechster
        # Naehe flog ein Getroffener rund 240 Pixel weit (0.32).
        self.schub_anteil = 1.0 / max(1, int(daten.get("geschosse", 1)))
        # Womit geschossen wurde, muss das Geschoss selbst wissen: beim
        # Einschlag kann der Schuetze laengst die Waffe gewechselt haben,
        # und dann landete der Treffer bei der falschen.
        self.waffe = waffe
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
            schub = None
            if self.tempo.length_squared() > 0.001:
                schub = (pygame.Vector2(self.tempo).normalize()
                         * K.TREFFER["rueckstoss"] * self.schub_anteil)
            if hasattr(self.von, "zaehlen"):
                self.von.zaehlen("treffer", 1.0, self.waffe)
                treffer_ziel_buchen(self.von, ziel)
            lebte = ziel.lebt
            ziel.schaden(self.schaden_wert, schub, self.von)
            abschuss_buchen(self.von, ziel, self.waffe, lebte)
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
        # Das Bild kommt ueber die Skin-Rolle und nicht als fester Name:
        # eine Skin soll spaeter die eigene Blendgranate austauschen
        # koennen, ohne dass hier etwas anders steht.
        if daten.get("rauch"):
            self.bild = "rauchgranate"
        elif daten.get("feuer"):
            self.bild = K.skin("molotov_flug")
        elif daten.get("blend"):
            self.bild = K.skin("blend_flug")
        else:
            self.bild = "granate"
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
            lebte = ziel.lebt
            ziel.schaden(d["schaden"] * anteil, schub, self.von)
            abschuss_buchen(self.von, ziel, "granate", lebte)
        w.explosion(self.pos, self.ebene, r)
        w.kurz_langsam(0.05)


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

    def schritt(self, dt: float) -> None:
        self.vorher.update(self.pos)
        if not self.haftend:
            schritt = min(self.restweg, K.C4["wurftempo"] * dt)
            vorher = pygame.Vector2(self.pos)
            stoss_x, stoss_y = self.welt.bewegen(
                self, self.richtung.x * schritt, self.richtung.y * schritt)
            self.restweg -= self.pos.distance_to(vorher)
            if self.restweg <= 0.5 or stoss_x or stoss_y:
                self.haftend = True
        else:
            self.lade_rest = max(0.0, self.lade_rest - dt)

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
            schub = (delta.normalize() * K.C4["schub"] * anteil
                     if abstand > 0.01 else None)
            lebte = ziel.lebt
            ziel.schaden(K.C4["schaden"] * anteil, schub, self.von)
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
    schiebt = False
    trefferbar = False
    schatten = True
    radius = 4.0
    bild = "flugrakete"
    faellt = False          # sie faellt nicht, sie fliegt

    def __init__(self, pos, richtung: float, daten: dict, ebene: int,
                 von=None, ziel=None) -> None:
        super().__init__(pos, ebene)
        self.daten = daten
        self.von = von
        self.winkel = richtung
        self.rest = daten["flugzeit"]
        self.weg = 0.0
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
        e = self.welt.ebene(self.ebene)
        for _ in range(schritte):
            self.pos += teil
            getroffen = self.welt.treffer(self.pos, self.radius, self.ebene,
                                          self.quelle_fraktion)
            if getroffen is not None and getroffen is not self.von:
                self.einschlag(getroffen)
                return
            if e.sichtdicht(int(self.pos.x // K.TILE), int(self.pos.y // K.TILE)):
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
            schub = (ab.normalize() * 420 * anteil) if entfernung > 0.01 else None
            lebte = ziel.lebt
            ziel.schaden(d["schaden"] * anteil, schub, schuetze)
            abschuss_buchen(schuetze, ziel, "rakete", lebte)
        w.explosion(self.pos, self.ebene, r)
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
                 "_funkenrest")

    _naechste_kennung = 0

    def __init__(self, pos, ebene: int, radius: float | None = None,
                 dauer: float | None = None, alter: float = 0.0,
                 kennung: int | None = None, von=None,
                 verschont: str = "") -> None:
        f = K.FEUER
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
                ziel.schaden(f["schaden"] * anteil * dt, None, self.von)
        # Funken steigen auf. Sie sind das, was ein Feuer von einem
        # roten Fleck unterscheidet.
        self._funkenrest += f["funken"] * self.staerke * dt
        while self._funkenrest >= 1.0:
            self._funkenrest -= 1.0
            winkel = RND.uniform(0, 360)
            weg = RND.uniform(0, self.radius * 0.85)
            stelle = self.pos + pygame.Vector2(weg, 0).rotate(winkel)
            welt.partikel.append(Partikel(
                stelle, (RND.uniform(-14, 14), RND.uniform(-46, -22)),
                RND.uniform(0.5, 1.1), f["toene"][3], 1, "funke", 1.2,
                self.ebene))

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
        art = {s: a for s, _t, a in K.WERTE}
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
            if not getattr(ziel, "trefferbar", False):
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
        d = self.waffe_daten
        if not d.get("gewicht_tempo") and not d.get("gewicht_drehen"):
            return 0.0
        if d.get("modus_daten") or d.get("anlauf"):
            # Mit Anlauf zaehlt die Drehzahl, nicht der Finger.
            return max(self.anlauf, 1.0 if self.salve_rest > 0 else 0.0)
        return 1.0 if self.feuert else 0.0

    @property
    def gewicht_tempo(self) -> float:
        """Faktor auf das Lauftempo. 1.0 heisst: keine Behinderung."""
        d = self.waffe_daten
        voll = d.get("gewicht_tempo")
        if voll is None:
            return 1.0
        return 1.0 - (1.0 - voll) * self.am_feuern

    @property
    def dreh_grenze(self) -> float:
        """Grad je Sekunde, mehr geht nicht. 0 heisst: keine Grenze."""
        d = self.waffe_daten
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
        self._schuss_abgeben(d)

    # ---- Betriebsarten -------------------------------------------------
    def modus_von(self, waffe: str) -> str:
        """Welche Betriebsart fuer diese Waffe gewaehlt ist."""
        modi = K.WAFFEN.get(waffe, {}).get("modi")
        if not modi:
            return ""
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
        d = K.WAFFEN.get(K.NAHKAMPF["waffe"])
        if d is None or self.nahkampf_rest > 0 or self.schlag_zeigen > 0:
            return False
        if self.nachlade_rest > 0 or self.heilt_rest > 0:
            return False
        self.nahkampf_rest = d["takt"]
        self.schlag_zeigen = d.get("schwung", 0.26) + K.NAHKAMPF["nachhalten"]
        self.schlagen(d)
        return True

    @property
    def schwingt(self) -> bool:
        """Laeuft gerade ein Schlag mit dem Brecheisen?"""
        return self.schlag_zeigen > 0 and self.nahkampf_rest > 0

    def schwung_bild(self, vorsatz: str = "") -> str:
        """Welches Bild der Schwungfolge gerade dran ist (seit 0.32.8).

        Der Schwung laeuft schnell an und laeuft aus; danach haelt die
        Figur das Eisen noch am Ende des Bogens (Nachhalten).
        """
        d = K.WAFFEN[K.NAHKAMPF["waffe"]]
        dauer = d.get("schwung", 0.26)
        lauf = self.schlag_zeigen - K.NAHKAMPF["nachhalten"]
        f = 1.0 - max(0.0, min(1.0, lauf / dauer))
        weg = 1.0 - (1.0 - f) * (1.0 - f)
        i = int(round(weg * (K.SCHWUNG_BILDER - 1)))
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
        self.unverwundbar = max(0.0, self.unverwundbar - dt)
        self.takt = max(0.0, self.takt - dt)
        # Blickrichtung. Normalerweise sofort - die Figur schaut dorthin,
        # wo die Maus steht, und zwar ohne Verzoegerung. Eine schwere
        # Waffe begrenzt das: mit dem MG im Anschlag dreht man sich nicht
        # auf der Stelle um, und genau das ist ihr Preis.
        # Wer am Boden liegt, dreht sich nicht mehr. Vorher folgte die
        # liegende Figur weiter der Maus und drehte sich am Boden im Kreis.
        if (self.ziel - self.pos).length_squared() > 1 \
                and not getattr(self, "am_boden", False):
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
                if self.lebt and not getattr(self, "am_boden", False):
                    self.leben = min(self.max_leben,
                                     self.leben + K.MEDKIT["heilt"])
                    wolke(self.welt, self.pos, 10, 60, 0.6, K.C_TEAL,
                          self.ebene, 1)

        self.dash_bild_rest = max(0.0, self.dash_bild_rest - dt)

        self.schlag_zeigen = max(0.0, self.schlag_zeigen - dt)
        self.nahkampf_rest = max(0.0, self.nahkampf_rest - dt)
        self.halte_zeit = self.halte_zeit + dt if self.feuert else 0.0
        self._anlauf_fuehren(dt, wd)
        self._salve_fuehren(dt, wd)
        self._erfassung_fuehren(dt, wd)

        luft = K.STURZ["luftsteuerung"] if self.sturz_rest > 0 else 1.0
        if fd:
            luft *= 1.0 - (1.0 - wd.get("fokus_tempo", 1.0)) * self.fokus
        luft *= self.gewicht_tempo
        if self.heilt_rest > 0:
            # Wer ein Medkit anlegt, hat die Haende voll und geht langsamer.
            luft *= K.MEDKIT["tempo"]
        if getattr(self, "zieht", None) is not None:
            # Wer jemanden zieht, ebenso.
            luft *= K.ZIEHEN["tempo"]
        self._dash_laden(dt)
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
                else:
                    wolke(self.welt, self.pos + pygame.Vector2(0, 4), 2, 26, 0.34,
                          K.C_MUTED_DK, self.ebene, 1, "staub", 360, 0, 6.0)

        # Nachladen und Feuern laufen immer weiter: beim Laufen, im Sturz
        # und beim Dash. Keine Handlung sperrt eine andere aus - siehe
        # abbrechen(). Mit einer Ausnahme: waehrend ein Medkit angelegt
        # wird, hat die Figur es in der Hand und nicht die Waffe, und das
        # sieht man ihr an. Was sie nicht haelt, schiesst nicht. Das
        # Nachladen laeuft dabei weiter - es ist ein Zaehler, kein Griff.
        if self.nachlade_rest > 0:
            self.nachlade_rest -= dt
            if self.nachlade_rest <= 0:
                self.magazin[self.waffe_name] = self.waffe_daten["magazin"]
        elif self.waffe_name == "c4":
            if self.feuert and not self._c4_feuert_alt and self.heilt_rest <= 0:
                self.feuern()
            self._c4_feuert_alt = self.feuert
        elif self.feuert and self.takt <= 0 and self.heilt_rest <= 0:
            self.feuern()

    # ---- Waffe -------------------------------------------------------
    # ---- Dash -----------------------------------------------------------
    def _dash_laden(self, dt: float) -> None:
        """Die Ladungen fuellen sich nacheinander wieder auf."""
        d = K.DASH
        self.dash_sperre = max(0.0, self.dash_sperre - dt)
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
        if not self.kann_dashen:
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
        if not d.get("magazin") or d.get("art") in ("wurf", "c4"):
            return
        if self.nachlade_rest <= 0 and self.magazin[self.waffe_name] < d["magazin"]:
            self.nachlade_rest = d["nachladen"]
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
            self.magazin[self.waffe_name] -= 1
            muendung = self.pos + pygame.Vector2(18, 0).rotate(self.winkel)
            ziel = self.erfasst if self.erfassung >= 1.0 else None
            streuung = d.get("streuung", 0.0)
            richtung = self.winkel + RND.uniform(-streuung, streuung)
            self.welt.dazu(Rakete(muendung, richtung, d, self.ebene, self,
                                  ziel))
            self.tempo -= pygame.Vector2(d.get("rueckstoss", 0.0),
                                         0).rotate(self.winkel)
            self.welt.raketenstart(muendung, self.winkel, self.ebene, self,
                                   ziel)
            self.zaehlen("granaten", 1.0, "rakete")
            # Rohr leer: zurueck zu dem, was man vorher trug.
            self.rpg_ablegen()
            return

        if art == "wurf":
            self.magazin[self.waffe_name] -= 1
            muendung = self.pos + pygame.Vector2(14, 0).rotate(self.winkel)
            # Sie fliegt dorthin, wo man hinzeigt, nicht immer gleich weit.
            weite = min(d["wurf_max"], max(d["wurf_min"],
                                           self.pos.distance_to(self.ziel)))
            self.welt.dazu(Granate(muendung, self.winkel, d, self.ebene, self,
                                   weite))
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
        if salve and salve > 1:
            self.salve_rest = salve - 1
            self.salve_takt = d.get("salve_takt", 0.03)
        self._schuss_abgeben(d)

    def _schuss_abgeben(self, d: dict) -> None:
        """Ein einzelner Schuss: Munition, Geschoss, Rueckstoss, Knall.

        Eigene Methode, weil eine Salve sie mehrfach braucht - und weil
        `feuern` sonst nicht mehr zu lesen waere.
        """
        if self.magazin.get(self.waffe_name, 0) <= 0:
            self.salve_rest = 0
            return
        self.magazin[self.waffe_name] -= 1
        muendung = self.pos + pygame.Vector2(14, 0).rotate(self.winkel)

        # Ein Abzug ist ein Schuss, auch bei Schrot mit acht Kuegelchen:
        # sonst laesst sich die Treffergenauigkeit einer Schrotflinte nicht
        # mit der eines Gewehrs vergleichen.
        self.zaehlen("schuesse", 1.0, self.waffe_name)
        streuung = self.streuung_jetzt
        if d.get("streuung_dauerfeuer"):
            streuung += d["streuung_dauerfeuer"] * min(1.0, self.halte_zeit)
        for _ in range(d["geschosse"]):
            a = self.winkel + RND.uniform(-streuung, streuung)
            self.welt.dazu(Geschoss(muendung, a, d, self.ebene, self,
                                    self.waffe_name))
        self.fokus *= 0.25            # der Schuss reisst die Waffe hoch

        # Rueckstoss auf den Schuetzen. Blitz, Funken, Knall und der Schlag
        # auf die Kamera stehen zusammen in Welt.schussknall - dort, wo sie
        # auch ein Gast nachspielen kann, der selbst nichts rechnet.
        self.tempo -= pygame.Vector2(self.rueckstoss_wert(d), 0).rotate(self.winkel)
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
        if daten is None:
            self.takt = d["takt"]
        # Schwung und Nachhalten: das Eisen bleibt danach noch einen Moment
        # in der Hand (K.NAHKAMPF["nachhalten"]).
        self.schlag_zeigen = d.get("schwung", 0.26) + K.NAHKAMPF["nachhalten"]
        self.zaehlen("schuesse", 1.0, K.NAHKAMPF["waffe"])
        w = self.welt
        reich = d["reichweite"]
        halb = d["winkel"] * 0.5
        getroffen = 0
        treffer_art = "organisch"
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
            if getattr(ziel, "ist_boss", False):
                treffer_art = "metall"
            self.zaehlen("kopftreffer", 1.0, K.NAHKAMPF["waffe"])
            getroffen += 1
        spitze = self.pos + pygame.Vector2(reich * 0.7, 0).rotate(self.winkel)
        w.schlagknall(spitze, self.winkel, self.ebene, bool(getroffen), self,
                      treffer_art)

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
        super().sterben(von)
        wolke(self.welt, self.pos, 22, 210, 0.8, K.C_BLUT, self.ebene, 2, "blut")


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

    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        d = self.daten
        self.schlag_rest = max(0.0, self.schlag_rest - dt)
        if self.sturz_rest > 0:
            return          # im Fall: kein Laufen, kein Schlagen
        held = self.welt.held

        # Sie laufen immer los. Ist das Ziel nur ueber eine Treppe zu
        # erreichen, gehen sie den Weg dorthin (wege.py); ein Boss nicht,
        # der wartet auf seiner Ebene.
        ziel = None
        self.treppen_sperre = max(0.0, self.treppen_sperre - dt)
        self.weg_rest = -1
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

        if self.wartet > 0:
            self.wartet -= dt
            ziel = None

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
                ding.schaden(f["schaden"] * anteil, schub, self)
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
            ding.schaden(p["schaden"] * anteil, schub, self)
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
        ziel.schaden(self.daten["schaden"], schub, self)
        wolke(self.welt, (self.pos + ziel.pos) / 2, 5, 150, 0.2, K.C_ORANGE,
              self.ebene, 1, "funke")

    def sterben(self, von=None) -> None:
        super().sterben(von)
        w = self.welt
        wolke(w, self.pos, 14, 190, 0.55, K.C_BLUT, self.ebene, 2, "blut")
        wolke(w, self.pos, 6, 90, 0.7, K.C_MUTED_DK, self.ebene, 1, "staub")
        w.blutfleck(self.pos, self.ebene, self.radius)
        w.ruckeln(3.4 if self.ist_boss else 2.2, "tod", self.pos, self.ebene, self)
        w.kurz_langsam(K.TREFFER["zeitlupe"])
        if self.platzt:
            self._platzen()
        if isinstance(von, Spieler) or (von is not None and von.fraktion == "mensch"):
            held = w.held
            if held is not None:
                held.punkte += self.daten["punkte"]
