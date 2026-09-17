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
from .entities import Gegner, Spieler, wolke
from .font import SCHRIFT
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
        bild = self.renderer._blut
        self.welt.ebene(ebene).dekal(bild, pos.x, pos.y)

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

    @property
    def gegner_uebrig(self) -> int:
        return sum(1 for g in self.offen if g.lebt)

    # ---- Ablauf -------------------------------------------------------
    def ereignis(self, ev) -> None:
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE,):
            if self.held.lebt:
                self.app.schieben(PauseSchirm(self.app, self))

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
            if e.gedrueckt("waffe1"):
                held.waffe_waehlen(0)
            if e.gedrueckt("waffe2"):
                held.waffe_waehlen(1)
            if e.rad:
                held.waffe_waehlen((held.waffe + (1 if e.rad < 0 else -1))
                                   % len(held.waffen))

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

        ebene = self.welt.ebene(held.ebene)
        self.kamera.schritt(dt, held.pos, held.ziel,
                            (ebene.pixel_breite, ebene.pixel_hoehe))

    # ---- Bild ---------------------------------------------------------
    def zeichnen(self, ziel, alpha: float) -> None:
        self.renderer.welt_zeichnen(ziel, self.welt, self.kamera, alpha)
        self.renderer.schaden_blende(ziel, self.schaden_blende)

        if self.gegner_uebrig == 0 and self.held.lebt:
            text = "NAECHSTE WELLE IN %d" % math.ceil(max(0.0, self.pause_rest))
        else:
            text = "WELLE %d  %d UEBRIG" % (self.welle, self.gegner_uebrig)
        self.renderer.hud(ziel, self.welt, self.held, text, self.held.punkte)
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


class PauseSchirm(Szene):
    deckt_zu = False

    def __init__(self, app, spiel: Spiel) -> None:
        super().__init__(app)
        self.spiel = spiel

    def betreten(self) -> None:
        self.app.eingabe.alles_loslassen()

    def ereignis(self, ev) -> None:
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.app.werfen()
            elif ev.key == pygame.K_q:
                self.app.laeuft = False

    def zeichnen(self, ziel, alpha: float) -> None:
        s = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
        s.fill((0, 0, 0, 150))
        ziel.blit(s, (0, 0))
        SCHRIFT.zeichnen(ziel, "PAUSE", K.GAME_W // 2, K.GAME_H // 2 - 22,
                         K.C_AMBER, 3, 2, "mitte")
        SCHRIFT.zeichnen(ziel, "[ESC] WEITER    [Q] BEENDEN", K.GAME_W // 2,
                         K.GAME_H // 2 + 8, K.C_MUTED, 1, 2, "mitte")
