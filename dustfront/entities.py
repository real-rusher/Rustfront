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
        self.sturz_hoehe = 0.0

    # ---- Ablauf ------------------------------------------------------
    def schritt(self, dt: float) -> None:
        self.vorher.update(self.pos)
        if self.blitz > 0:
            self.blitz -= dt
        if self.sturz_rest > 0:
            self.sturz_schritt(dt)

    # ---- Sturz --------------------------------------------------------
    def stuerzen(self) -> None:
        """Faellt eine Ebene tiefer. Kein Laden, kein Schnitt: das Wesen ist
        sofort unten und wird nur noch von oben eingeblendet."""
        w = self.welt
        ziel = self.ebene - 1
        dz = w.abstand(self.ebene, ziel)
        self.pos.update(w.landeplatz(self.pos, self.radius, ziel))
        self.vorher.update(self.pos)
        self.ebene = ziel
        self.flug = dz
        self.sturz_hoehe = dz
        self.sturz_rest = K.STURZ["dauer"]
        self.tempo *= 0.35

    def sturz_schritt(self, dt: float) -> None:
        self.sturz_rest -= dt
        d = K.STURZ["dauer"]
        t = max(0.0, min(1.0, 1.0 - self.sturz_rest / d))
        # freier Fall: der Weg waechst quadratisch, also faellt die Hoehe so
        self.flug = self.sturz_hoehe * (1.0 - t * t)
        if self.sturz_rest <= 0:
            self.flug = 0.0
            self.aufschlag()

    def aufschlag(self) -> None:
        h = self.sturz_hoehe
        self.sturz_hoehe = 0.0
        schaden = max(K.STURZ["min_schaden"], h / 100.0 * K.STURZ["schaden_je_100"])
        w = self.welt
        wolke(w, self.pos, 12, 130, 0.45, K.C_MUTED_DK, self.ebene, 1, "staub")
        w.ruckeln(min(6.0, 1.5 + h * 0.03))
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
# Spieler
# ══════════════════════════════════════════════════════════════════

class Spieler(Wesen):
    fraktion = "mensch"
    bild = "spieler"
    faellt = True

    def __init__(self, pos, ebene=0) -> None:
        self.max_leben = K.SPIELER["leben"]
        super().__init__(pos, ebene)
        self.radius = K.SPIELER["radius"]
        self.waffen = ["repetierer", "schrot"]
        self.waffe = 0
        self.magazin = {w: K.WAFFEN[w]["magazin"] for w in self.waffen}
        self.takt = 0.0
        self.nachlade_rest = 0.0
        self.unverwundbar = 0.0
        self.weg = 0.0                 # fuer Schrittstaub
        self.ziel = pygame.Vector2(pos) + pygame.Vector2(1, 0)
        self.will = pygame.Vector2(0, 0)
        self.sprint = False
        self.feuert = False
        self.punkte = 0

    @property
    def waffe_daten(self) -> dict:
        return K.WAFFEN[self.waffen[self.waffe]]

    @property
    def waffe_name(self) -> str:
        return self.waffen[self.waffe]

    # ---- Ablauf ------------------------------------------------------
    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        s = K.SPIELER
        self.unverwundbar = max(0.0, self.unverwundbar - dt)
        self.takt = max(0.0, self.takt - dt)
        if self.sturz_rest > 0:          # im Fall haengt man hilflos in der Luft
            self.tempo *= 0.92
            self.welt.bewegen(self, self.tempo.x * dt, self.tempo.y * dt)
            return

        # Blickrichtung
        if (self.ziel - self.pos).length_squared() > 1:
            self.winkel = math.degrees(math.atan2(self.ziel.y - self.pos.y,
                                                  self.ziel.x - self.pos.x))

        # Bewegung: beschleunigen in Wunschrichtung, sonst bremsen
        ziel_tempo = self.will * s["tempo"] * (s["sprint"] if self.sprint else 1.0)
        rate = s["beschleunigung"] if self.will.length_squared() > 0 else s["bremsung"]
        self.tempo.x = naehern(self.tempo.x, ziel_tempo.x, rate * dt)
        self.tempo.y = naehern(self.tempo.y, ziel_tempo.y, rate * dt)
        vor = pygame.Vector2(self.pos)
        self.welt.bewegen(self, self.tempo.x * dt, self.tempo.y * dt)
        self.welt.auseinander(self)

        # Ueber den Rand getreten? Dann geht es sofort abwaerts.
        if self.sturz_rest <= 0 and self.welt.loch_unter(self):
            self.stuerzen()
            return

        # Schrittstaub
        self.weg += self.pos.distance_to(vor)
        if self.weg > s["stiefel_abstand"]:
            self.weg = 0.0
            wolke(self.welt, self.pos + pygame.Vector2(0, 4), 2, 26, 0.34,
                  K.C_MUTED_DK, self.ebene, 1, "staub", 360, 0, 6.0)

        # Nachladen laeuft weiter, auch wenn man rennt
        if self.nachlade_rest > 0:
            self.nachlade_rest -= dt
            if self.nachlade_rest <= 0:
                self.magazin[self.waffe_name] = self.waffe_daten["magazin"]
        elif self.feuert and self.takt <= 0:
            self.feuern()

    # ---- Waffe -------------------------------------------------------
    def nachladen(self) -> None:
        d = self.waffe_daten
        if self.nachlade_rest <= 0 and self.magazin[self.waffe_name] < d["magazin"]:
            self.nachlade_rest = d["nachladen"]

    def waffe_waehlen(self, index: int) -> None:
        if 0 <= index < len(self.waffen) and index != self.waffe:
            self.waffe = index
            self.nachlade_rest = 0.0
            self.takt = max(self.takt, 0.18)

    def feuern(self) -> None:
        d = self.waffe_daten
        if self.magazin[self.waffe_name] <= 0:
            self.nachladen()
            return
        self.magazin[self.waffe_name] -= 1
        self.takt = d["takt"]

        streuung = d["streuung"]
        if self.tempo.length_squared() > 400:
            streuung += d["streuung_lauf"]
        muendung = self.pos + pygame.Vector2(14, 0).rotate(self.winkel)
        for _ in range(d["geschosse"]):
            a = self.winkel + RND.uniform(-streuung, streuung)
            self.welt.dazu(Geschoss(muendung, a, d, self.ebene, self))

        # Rueckstoss auf den Schuetzen und auf die Kamera
        self.tempo -= pygame.Vector2(d["rueckstoss"], 0).rotate(self.winkel)
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

    # ---- Schaden -----------------------------------------------------
    def schaden(self, menge, schub=None, von=None) -> None:
        if self.unverwundbar > 0:
            return
        self.unverwundbar = K.SPIELER["unverwundbar"]
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
                self.winkel = math.degrees(math.atan2(richtung.y, richtung.x))
            soll = richtung * d["tempo"]
        else:
            soll = pygame.Vector2(0, 0)

        self.tempo.x = naehern(self.tempo.x, soll.x, d["beschleunigung"] * dt)
        self.tempo.y = naehern(self.tempo.y, soll.y, d["beschleunigung"] * dt)
        stoss_x, stoss_y = self.welt.bewegen(self, self.tempo.x * dt, self.tempo.y * dt)
        # An einer Wand nicht stehenbleiben, sondern daran entlangschieben
        if stoss_x:
            self.tempo.x = 0
            self.tempo.y += self.drall * d["tempo"] * 0.9 * dt * 60 * dt
        if stoss_y:
            self.tempo.y = 0
            self.tempo.x += self.drall * d["tempo"] * 0.9 * dt * 60 * dt
        if stoss_x and stoss_y:
            self.drall = -self.drall
        self.welt.auseinander(self)

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
