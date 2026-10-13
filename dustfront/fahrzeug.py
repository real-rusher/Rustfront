"""
DUSTFRONT - Der Buggy (seit 0.34.9)
===================================

Ein kleiner Wuestenbuggy, der dort steht, wo die Karte ein F hat. Man
steigt mit E ein und wieder aus; gelenkt wird wie ein Auto, nicht wie die
Figur: W gibt Gas, S bremst und faehrt dann rueckwaerts, A und D lenken -
und gelenkt wird nur, solange er rollt.

**Unzerstoerbar.** Der Wagen selbst ist kein Ziel (`trefferbar = False`):
Kugeln, Splitter und Feuer gehen an ihm vorbei auf das, was darin sitzt.
Wer am Steuer sitzt, bekommt von jedem Schaden nur einen Teil ab
(K.FAHRZEUG["schaden_anteil"]) und wird nicht weggestossen - das rechnet
der Kaempfer selbst (mehrspieler.Kaempfer.schaden).

**Wer rechnet.** Wie alles im Gefecht der Gastgeber. Beim Gast steht ein
Buggy mit `nur_bild = True`: er wird an die gemeldete Stelle gesetzt und
nur gezeichnet, Staub macht er aus dem gemeldeten Tempo selbst.

**Anstossen.** Ein laenglicher Wagen passt nicht in einen Kreis. Er stoesst
deshalb mit zwei Kreisen an, einer vorn und einer hinten (K.FAHRZEUG
"kreis" und "achse"). Loecher zaehlen als Wand: ein Buggy faellt nicht von
einer Kante, er bleibt davor stehen.
"""

from __future__ import annotations

import math

import pygame

from . import config as K
from .core import naehern
from .entities import Wesen, wolke


class Buggy(Wesen):
    fraktion = "neutral"
    # Kein Ziel fuer Kugeln: er soll nicht kaputtgehen, und eine Kugel, die
    # an einem leeren Wagen haengen bliebe, waere Deckung zum Mitnehmen.
    trefferbar = False
    # Die weiche Abstossung der Welt kennt nur Kreise. Wer im Weg steht,
    # schiebt der Buggy selbst beiseite (_beiseite_schieben).
    schiebt = False
    # Statt des runden Schattens der Figuren ein eigener, laenglicher
    # (Renderer.wesen_zeichnen fragt nach `schatten_bild`).
    schatten = False
    schatten_bild = "buggy_schatten"
    faellt = False
    # C4 bleibt an ihm kleben und faehrt mit (seit 0.34.11, siehe
    # entities.C4Ladung). Er selbst nimmt keinen Schaden davon, wer drin
    # sitzt, schon.
    c4_haftet = True

    def __init__(self, pos, ebene: int = 0, winkel: float = 0.0,
                 nur_bild: bool = False) -> None:
        super().__init__(pos, ebene)
        f = K.FAHRZEUG
        self.radius = f["kreis"]
        self.winkel = float(winkel)
        self.fahrer = None            # der Kaempfer am Steuer, beim Gastgeber
        self.gas = 0.0                # -1 bis 1, aus W und S
        self.lenk = 0.0               # -1 bis 1, aus A und D
        self.geschw = pygame.Vector2(0, 0)
        # Wo er zu Beginn stand. Zu jeder neuen Runde kommt er dorthin
        # zurueck, sonst steht nach drei Runden jeder Buggy irgendwo.
        self.start = (pygame.Vector2(pos), int(ebene), float(winkel))
        self.nur_bild = nur_bild
        # Beim Gast: ob jemand drinsitzt und aus welcher Mannschaft. Beim
        # Gastgeber folgt beides aus `fahrer`.
        self.besetzt = False
        self.team = -1
        self._staub_rest = 0.0

    # ---- Bild ---------------------------------------------------------
    @property
    def bild(self) -> str:
        if self.fahrer is not None:
            besetzt, team = True, getattr(self.fahrer, "team", -1)
        else:
            besetzt, team = self.besetzt, self.team
        if not besetzt:
            return "buggy"
        if 0 <= team < len(K.TEAMS["kombi"]):
            name = "buggy_%s_fahrer" % K.TEAMS["kombi"][team]["name"].lower()
            if name in K.BILD_MASS:
                return name
        return "buggy_fahrer"

    @property
    def vorn(self) -> pygame.Vector2:
        return pygame.Vector2(1, 0).rotate(self.winkel)

    @property
    def fahrt(self) -> float:
        """Tempo in Fahrtrichtung, rueckwaerts negativ."""
        return self.geschw.dot(self.vorn)

    def schaden(self, menge, schub=None, von=None) -> None:
        """Unzerstoerbar. Kein Ziel trifft ihn absichtlich (trefferbar),
        und sollte doch einmal etwas Schaden auf ihn rechnen, kommt nichts
        an - er bleibt stehen, so lange die Runde dauert."""
        return

    # ---- Anstossen ----------------------------------------------------
    def kreise(self, pos=None, winkel=None) -> tuple:
        """Die beiden Kreise, mit denen er anstoesst: vorn und hinten."""
        pos = self.pos if pos is None else pos
        winkel = self.winkel if winkel is None else winkel
        achse = pygame.Vector2(K.FAHRZEUG["achse"], 0).rotate(winkel)
        return (pos + achse, pos - achse)

    def beruehrt(self, pos, radius: float) -> bool:
        """Liegt ein Kreis an `pos` am Wagen an?"""
        grenze = (self.radius + radius) ** 2
        return any(c.distance_squared_to(pos) <= grenze for c in self.kreise())

    def passt(self, pos, winkel=None) -> bool:
        """Kann er hier stehen? Mauern, Loecher und alles Unverschiebbare
        (Zielpuppe, Koloss) halten ihn auf; Menschen und gewoehnliche
        Gegner nicht, die schiebt er beiseite."""
        w = self.welt
        if w is None:
            return True
        r = self.radius
        kreise = self.kreise(pos, winkel)
        for c in kreise:
            if not w.frei(c, r, self.ebene, True):
                return False
        for a in w.nahe(pos, K.FAHRZEUG["achse"] + r + 40, self.ebene):
            if (a is self.fahrer or not a.lebt or a.flug > 0
                    or getattr(a, "schiebbar", True)
                    or getattr(a, "am_boden", False)):
                continue
            for c in kreise:
                if c.distance_squared_to(a.pos) < (r + a.radius) ** 2:
                    return False
        return True

    # ---- Ablauf -------------------------------------------------------
    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        if self.nur_bild or self.welt is None:
            return
        f = K.FAHRZEUG
        fahrer = self.fahrer is not None
        gas = self.gas if fahrer else 0.0
        lenk = self.lenk if fahrer else 0.0

        # Lenken. Im Stand gar nicht, langsam nur ein wenig - ein Auto
        # dreht sich nicht auf der Stelle. Rueckwaerts andersherum, wie
        # bei jedem Wagen. Gedreht wird nur, wenn er danach noch passt;
        # sonst klemmt er sich an einer Mauer fest.
        fahrt = self.fahrt
        if lenk:
            anteil = min(1.0, abs(fahrt) / f["lenk_ab"])
            dreh = f["lenkung"] * lenk * anteil * dt * (1.0 if fahrt >= 0 else -1.0)
            neu = (self.winkel + dreh + 180.0) % 360.0 - 180.0
            if dreh and self.passt(self.pos, neu):
                self.winkel = neu

        # Das Tempo in die neue Richtung zerlegen: was quer liegt, rutscht
        # und klingt mit dem Griff der Reifen ab. Daher das kleine
        # Driften in scharfen Kurven.
        vorn = self.vorn
        quer = pygame.Vector2(-vorn.y, vorn.x)
        laengs = self.geschw.dot(vorn)
        seitlich = self.geschw.dot(quer) * math.exp(-f["griff"] * dt)
        if gas > 0.0:
            if laengs < 0.0:
                laengs = min(0.0, laengs + f["bremse"] * dt)
            elif laengs < f["hoechst"]:
                laengs = min(f["hoechst"], laengs + f["gas"] * gas * dt)
        elif gas < 0.0:
            if laengs > 0.0:
                laengs = max(0.0, laengs - f["bremse"] * dt)
            elif laengs > -f["rueckwaerts"]:
                laengs = max(-f["rueckwaerts"], laengs + f["gas"] * gas * dt)
        else:
            laengs = naehern(laengs, 0.0, f["rollen"] * dt)
        self.geschw = vorn * laengs + quer * seitlich

        self._fahren(dt)
        self.tempo.update(self.geschw)
        self._beiseite_schieben()
        self._staub(dt)

    def _fahren(self, dt: float) -> None:
        """In kleinen Schritten vorwaerts. An einer Mauer gleitet er
        entlang, wenn eine Achse frei ist; sonst prallt er ab."""
        f = K.FAHRZEUG
        weg = self.geschw * dt
        n = max(1, int(weg.length() / 4.0) + 1)
        schritt = weg / n
        stoss = 0.0
        for _ in range(n):
            neu = self.pos + schritt
            if self.passt(neu):
                self.pos.update(neu)
                continue
            nur_x = self.pos + pygame.Vector2(schritt.x, 0)
            nur_y = self.pos + pygame.Vector2(0, schritt.y)
            if schritt.x and self.passt(nur_x):
                stoss = max(stoss, abs(self.geschw.y))
                self.pos.update(nur_x)
                self.geschw.y *= -f["aufprall"]
                schritt.y = 0.0
            elif schritt.y and self.passt(nur_y):
                stoss = max(stoss, abs(self.geschw.x))
                self.pos.update(nur_y)
                self.geschw.x *= -f["aufprall"]
                schritt.x = 0.0
            else:
                stoss = max(stoss, self.geschw.length())
                self.geschw *= -f["aufprall"]
                break
        if stoss >= f["aufprall_hart"]:
            w = self.welt
            staerke = min(1.0, stoss / f["hoechst"])
            w.klang("buggy_aufprall", 0.45 + 0.55 * staerke, self.pos, self.ebene)
            w.ruckeln(2.0 + 4.0 * staerke, "sturz", self.pos, self.ebene,
                      self.fahrer)
            wolke(w, self.pos + self.vorn * 20, 8, 90, 0.45, K.C_MUTED_DK,
                  self.ebene, 1, "staub")

    def _beiseite_schieben(self) -> None:
        """Wer vor dem Wagen steht, wird zur Seite geschoben - Freund,
        Feind und Zombie. Nur wohin Platz ist; wer an der Mauer klemmt,
        bleibt eben stehen, und der Wagen mit ihm (siehe passt)."""
        w = self.welt
        r = self.radius
        for a in list(w.nahe(self.pos, K.FAHRZEUG["achse"] + r + 40, self.ebene)):
            if (a is self.fahrer or a is self or not a.lebt or a.flug > 0
                    or not getattr(a, "schiebt", True)
                    or not getattr(a, "schiebbar", True)
                    or getattr(a, "am_boden", False)
                    or getattr(a, "im_fahrzeug", False)):
                continue
            for c in self.kreise():
                d = a.pos - c
                abstand = d.length()
                mindest = r + a.radius
                if abstand >= mindest:
                    continue
                if abstand < 0.001:
                    d = pygame.Vector2(-self.vorn.y, self.vorn.x)
                    abstand = 0.0
                else:
                    d /= abstand
                weg = d * (mindest - abstand)
                if w.frei(a.pos + weg, a.radius, a.ebene,
                          not getattr(a, "faellt", False)):
                    a.pos += weg

    def _staub(self, dt: float) -> None:
        """Staub hinter den Hinterraedern, sobald er schnell genug ist."""
        f = K.FAHRZEUG
        tempo = self.geschw.length()
        if tempo < f["staub_ab"] or self.welt is None:
            self._staub_rest = 0.0
            return
        self._staub_rest -= dt
        if self._staub_rest > 0.0:
            return
        self._staub_rest = f["staub_takt"]
        vorn = self.vorn
        quer = pygame.Vector2(-vorn.y, vorn.x)
        hinten = self.pos - vorn * 15
        richtung = math.degrees(math.atan2(-self.geschw.y, -self.geschw.x))
        menge = 1 + int(2 * min(1.0, tempo / f["hoechst"]))
        for seite in (-1, 1):
            wolke(self.welt, hinten + quer * (13 * seite), menge,
                  30 + 40 * tempo / f["hoechst"], 0.8, f["staub_farbe"],
                  self.ebene, f["staub_groesse"], "staub", 70, richtung, 2.5)

    def staub_gast(self, dt: float) -> None:
        """Beim Gast: derselbe Staub, aus dem gemeldeten Tempo."""
        self._staub(dt)

    def zuruecksetzen(self) -> None:
        """Zurueck an den Platz vom Rundenbeginn, stehend und leer."""
        pos, ebene, winkel = self.start
        self.pos.update(pos)
        self.vorher.update(pos)
        self.ebene = ebene
        self.winkel = winkel
        self.geschw.update(0, 0)
        self.tempo.update(0, 0)
        self.gas = self.lenk = 0.0

    def ausstiegsorte(self, radius: float) -> list:
        """Wo man aussteigen kann, der Reihe nach: links, rechts, hinten,
        vorn. Links zuerst, weil dort der Fahrer sitzt - wie im Auto."""
        vorn = self.vorn
        quer = pygame.Vector2(vorn.y, -vorn.x)       # links in Fahrtrichtung
        seite = self.radius + radius + 3.0
        laenge = K.FAHRZEUG["achse"] + self.radius + radius + 3.0
        return [self.pos + quer * seite, self.pos - quer * seite,
                self.pos - vorn * laenge, self.pos + vorn * laenge,
                self.pos + quer * seite - vorn * 14, self.pos - quer * seite - vorn * 14,
                self.pos + quer * seite + vorn * 14, self.pos - quer * seite + vorn * 14]
