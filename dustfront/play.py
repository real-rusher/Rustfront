"""
DUSTFRONT - Spielszene
======================

Verdrahtet Welt, Wesen, Kamera und Anzeige. Hier steht die Spielregel, sonst
nichts: Wellen von Gegnern, Treppen zwischen den Etagen, Pause, Tod.

Der Ablauf einer Runde ist absichtlich duenn gehalten. Was spaeter dazukommt
(Auftraege, Bauen, der Wandler als zweiter Modus) haengt sich als weitere
Szene oder als weiteres Wesen an, nicht als Aenderung an dieser Datei.
"""

from __future__ import annotations

import math
import random

import pygame

from . import config as K
from .core import Szene
from .entities import Aufsammler, Gegner, Spieler, wolke
from .font import SCHRIFT
from .inventar import Inventar
from .menues import Pause
from .render import Kamera, Renderer
from .world import freier_punkt, testkarte


class Spiel(Szene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.renderer = Renderer(app.bilder)
        self.rnd = random.Random()
        self.neu_aufbauen()

    # ---- Aufbau ------------------------------------------------------
    def neu_aufbauen(self) -> None:
        self.welt = testkarte()
        self.kamera = Kamera()
        start = freier_punkt(self.welt, 0, self.rnd)
        self.held = Spieler(start, 0)
        self.welt.dazu(self.held)
        self.welt.held = self.held

        # Die Welt meldet sich bei uns, wenn es wackeln oder spritzen soll
        self.welt.ruckeln = self.kamera.stossen
        self.welt.kurz_langsam = self._zeitlupe
        self.welt.blutfleck = self._blutfleck
        self.welt.klang = self.app.klaenge.spielen
        self.welt.brandfleck = self._brandfleck

        # Ansicht: welche Ebene die Kamera anschaut, und die geglaettete
        # Hoehe dazu. Beides haengt bewusst nicht an der Figur, damit man
        # spaeter frei durch die Etagen scrollen kann.
        self.blick = self.held.ebene
        self.blick_hoehe = float(self.welt.hoehe(self.blick))
        self._letzte_ebene = self.held.ebene

        self.welle = 0
        self.pause_rest = 2.0
        self.offen: list = []
        self.schaden_blende = 0.0
        self.tot_seit = 0.0
        self.hinweis = ""
        self.kamera.pos.update(self.held.pos)

    def _zeitlupe(self, sekunden: float) -> None:
        self.app.zeitlupe = max(self.app.zeitlupe, sekunden)

    def _blutfleck(self, pos, ebene: int, radius: float) -> None:
        self.welt.ebene(ebene).dekal(self.renderer.blutfleck(radius),
                                     pos.x, pos.y)

    def _brandfleck(self, pos, ebene: int, radius: float) -> None:
        self.welt.ebene(ebene).dekal(self.renderer.brandfleck(radius),
                                     pos.x, pos.y)

    # ---- Wellen -------------------------------------------------------
    def welle_starten(self) -> None:
        self.welle += 1
        self.offen = [g for g in self.offen if g.lebt]
        if self.welle <= len(K.WELLEN):
            plan = K.WELLEN[self.welle - 1]
        else:
            ueber = self.welle - len(K.WELLEN)
            faktor = 1.0 + K.WELLE_WACHSTUM * ueber
            plan = [(max(1, int(n * faktor)), art) for n, art in K.WELLEN[-1]]
        for anzahl, art in plan:
            for _ in range(anzahl):
                ebene = self.rnd.choice([0, 1]) if self.welle > 2 else self.held.ebene
                pos = freier_punkt(self.welt, ebene, self.rnd,
                                   weg_von=self.held.pos if ebene == self.held.ebene else None,
                                   mindest=210)
                g = self.welt.dazu(Gegner(pos, art, ebene))
                wolke(self.welt, pos, 8, 80, 0.45, K.C_MUTED_DK, ebene, 1, "staub")
                self.offen.append(g)
        # Nachschub: ein paar Medkits, verteilt auf die Ebenen
        for _ in range(K.MEDKIT["je_welle"]):
            eb = self.rnd.randrange(len(self.welt.ebenen))
            self.welt.dazu(Aufsammler(freier_punkt(self.welt, eb, self.rnd),
                                      "medkit", eb))

    @property
    def gegner_uebrig(self) -> int:
        return sum(1 for g in self.offen if g.lebt)

    # ---- Ablauf -------------------------------------------------------
    def ereignis(self, ev) -> None:
        if ev.type != pygame.KEYDOWN:
            return
        # Beide Schirme sind Szenen ueber dieser hier. Das Spiel rechnet
        # solange nicht weiter, bleibt aber sichtbar.
        if ev.key in self.app.opt.codes("pause"):
            if self.held.lebt:
                self.app.schieben(Pause(self.app, self))
        elif ev.key in self.app.opt.codes("inventar"):
            if self.held.lebt:
                self.app.schieben(Inventar(self.app, self))

    def schritt(self, dt: float) -> None:
        e = self.app.eingabe
        held = self.held
        self.schaden_blende = max(0.0, self.schaden_blende - dt * 2.2)
        self.hinweis = ""

        if held.lebt:
            held.will = e.richtung()
            held.sprint = e.gehalten("sprint")
            held.ziel = self.kamera.zu_welt(e.maus)
            held.feuert = e.gehalten("feuer")
            if e.gedrueckt("nachladen"):
                held.nachladen()
            if e.gedrueckt("tracer"):
                held.tracer = not held.tracer
            if e.gedrueckt("tracer_weit"):
                held.tracer_weit = not held.tracer_weit
            for nr in range(1, 7):
                if e.gedrueckt("waffe%d" % nr):
                    held.waffe_waehlen(nr - 1)
            if e.gedrueckt("heilen"):
                held.heilen()
            held.zielt = e.gehalten("zweit")
            if e.rad:                      # scrollen bewegt nur die Ansicht
                self.blick = max(0, min(len(self.welt.ebenen) - 1,
                                        self.blick + (1 if e.rad > 0 else -1)))

            ziel_ebene = self.welt.treppe_unter(held)
            if ziel_ebene is not None:
                self.hinweis = "[E] EBENE %d" % ziel_ebene
                if e.gedrueckt("nutzen"):
                    if self.welt.ebene_wechseln(held, ziel_ebene):
                        wolke(self.welt, held.pos, 10, 90, 0.4, K.C_MUTED_DK,
                              held.ebene, 1, "staub")
                        self.kamera.stossen(2.0)
            vorher_leben = held.leben
        else:
            held.will.update(0, 0)
            held.feuert = False
            vorher_leben = held.leben
            self.tot_seit += dt
            if self.tot_seit > 1.2 and (e.gedrueckt("nutzen") or e.gedrueckt("feuer")):
                self.neu_aufbauen()
                return

        self.welt.schritt(dt)
        if held.leben < vorher_leben:
            self.schaden_blende = 1.0

        # Wellen nachschieben
        if held.lebt:
            if self.gegner_uebrig == 0:
                self.pause_rest -= dt
                if self.pause_rest <= 0:
                    self.welle_starten()
                    self.pause_rest = K.WELLE_PAUSE

        # Wechselt die Figur die Ebene, folgt die Ansicht ihr nach
        if held.ebene != self._letzte_ebene:
            self._letzte_ebene = held.ebene
            self.blick = held.ebene
        if self.blick != held.ebene:
            self.hinweis = "ANSICHT EBENE %d  [MAUSRAD]" % self.blick

        # Waehrend eines Sturzes sinkt die Ansicht genau mit der Figur, sonst
        # zieht sie weich zur angeschauten Ebene.
        if held.flug > 0 and self.blick == held.ebene:
            self.blick_hoehe = self.welt.hoehe(held.ebene) + held.flug
        else:
            ziel_h = float(self.welt.hoehe(self.blick))
            self.blick_hoehe += (ziel_h - self.blick_hoehe) * min(1.0, 9.0 * dt)

        ebene = self.welt.ebene(held.ebene)
        self.kamera.schritt(dt, held.pos, held.ziel,
                            (ebene.pixel_breite, ebene.pixel_hoehe))

    # ---- Bild ---------------------------------------------------------
    def zeichnen(self, ziel, alpha: float) -> None:
        self.renderer.welt_zeichnen(ziel, self.welt, self.kamera, alpha,
                                    self.blick_hoehe)
        self.renderer.zielhilfen(ziel, self.welt, self.kamera, self.held)
        self.renderer.tracer(ziel, self.welt, self.kamera, self.held)
        self.renderer.schaden_blende(ziel, self.schaden_blende)

        if self.gegner_uebrig == 0 and self.held.lebt:
            text = "NAECHSTE WELLE IN %d" % math.ceil(max(0.0, self.pause_rest))
        else:
            text = "WELLE %d  %d UEBRIG" % (self.welle, self.gegner_uebrig)
        self.renderer.hud(ziel, self.welt, self.held, text, self.held.punkte,
                          self.blick)
        if self.hinweis:
            self.renderer.hinweis(ziel, self.hinweis)
        if not self.held.lebt:
            self.tod_schirm(ziel)
        if self.app.debug:
            self.renderer.debug(ziel, self.app, self.welt)

    def tod_schirm(self, ziel) -> None:
        s = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
        s.fill((0, 0, 0, min(190, int(self.tot_seit * 260))))
        ziel.blit(s, (0, 0))
        SCHRIFT.zeichnen(ziel, "VERLOREN", K.GAME_W // 2, K.GAME_H // 2 - 24,
                         K.C_RED, 4, 2, "mitte")
        SCHRIFT.zeichnen(ziel, "WELLE %d  SCHROTT %d" % (self.welle, self.held.punkte),
                         K.GAME_W // 2, K.GAME_H // 2 + 6, K.C_CREAM, 1, 2, "mitte")
        if self.tot_seit > 1.2:
            SCHRIFT.zeichnen(ziel, "[E] NEUE RUNDE", K.GAME_W // 2,
                             K.GAME_H // 2 + 26, K.C_AMBER, 1, 2, "mitte")


# Das frueher hier stehende PauseSchirm ist nach menues.Pause gewandert.
# Es gibt weiter einen Namen darauf, damit aelterer Code nicht bricht.
PauseSchirm = Pause
