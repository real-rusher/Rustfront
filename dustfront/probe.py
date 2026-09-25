"""
DUSTFRONT - Probelauf: der Wandler von aussen
=============================================

Eine Szene zum Hinsehen. Sie baut nichts Neues, sie zeigt nur, was
`beine.py` und `wandler.py` tun - und zwar so, dass man es beurteilen kann,
statt es glauben zu muessen.

    python -m dustfront --probe

Steuerung
---------

    W / S       Schub vor und zurueck
    A / D       Kurs
    SHIFT       Ueberlast
    H           Autopilot: der letzte Befehl bleibt stehen
    TAB         Ansicht naeher oder weiter
    1 / 2 / 3   Warhound, Reaver, Imperator
    4           ein Bein ausfallen lassen
    5           alle Beine richten
    F3          Zahlen einblenden
    ESC         zurueck

Worauf man achten soll
----------------------

Die Anzeige zeigt **befohlenes und gemessenes Tempo getrennt**. Das ist
kein Zierrat: das gemessene Tempo wird nirgends gesetzt, es ist der Weg,
den der Rumpf wirklich zurueckgelegt hat. Kommt es an das befohlene heran,
tragen die Beine; bleibt es zurueck, schaffen sie es nicht.

Mit **4** faellt ein Bein aus. Man sieht drei Dinge sofort, und keines
davon steht als Sonderfall im Code:

* Der Rumpf haengt schief - weil der Schwerpunkt der Standfuesse kippt.
* Die Schrittweite waechst - weil die Maschine nachregelt.
* Beim vorletzten Bein steht sie ganz - weil ein einziger Fuss nicht
  tragen und treten zugleich kann.
"""

from __future__ import annotations

import pygame

from . import config as K
from .core import Szene
from .font import SCHRIFT
from .render import Kamera, Renderer
from .wandler import Wandler, bauplan
from .world import karte_laden

KLASSEN = ("warhound", "reaver", "imperator")


class Probelauf(Szene):
    def __init__(self, app, klasse: str = "reaver") -> None:
        super().__init__(app)
        self.renderer = Renderer(app.bilder)
        self.boden = karte_laden(K.KARTEN["boden"])
        self.zoom = K.WANDLER_BILD["zoom"]
        self.kamera = Kamera()
        self.flaeche = None
        self.zeigen = False
        self.autopilot = False
        self.schub = 0.0
        self.lenkung = 0.0
        self.hinweis = ""
        self.hinweis_rest = 0.0
        self._setzen(klasse)

    # ---- Aufbau ---------------------------------------------------------
    def _setzen(self, klasse: str) -> None:
        self.klasse = klasse
        e = self.boden.ebene(0)
        mitte = (e.pixel_breite / 2, e.pixel_hoehe / 2)
        self.wandler = Wandler(bauplan(klasse), mitte, 0.0)
        self.schub = self.lenkung = 0.0
        self.autopilot = False
        self.kamera.pos.update(self.wandler.pos)
        self._flaeche_setzen()
        self._melden(self.wandler.plan.klassenname)

    def _flaeche_setzen(self) -> None:
        gross = (K.GAME_W * self.zoom, K.GAME_H * self.zoom)
        self.flaeche = pygame.Surface(gross)
        self.kamera.sicht.update(gross)

    def _melden(self, text: str) -> None:
        self.hinweis = text
        self.hinweis_rest = 1.8

    # ---- Eingabe ---------------------------------------------------------
    def ereignis(self, ev) -> None:
        if ev.type != pygame.KEYDOWN:
            return
        e = self.app.eingabe
        if ev.key == pygame.K_ESCAPE:
            self.app.werfen()
        elif ev.key == pygame.K_TAB:
            klein, gross = K.WANDLER_BILD["zoom_grenzen"]
            self.zoom = klein if self.zoom >= gross else self.zoom + 1
            self._flaeche_setzen()
            self._melden("ANSICHT 1 ZU %d" % self.zoom)
        elif ev.key in (pygame.K_1, pygame.K_2, pygame.K_3):
            self._setzen(KLASSEN[ev.key - pygame.K_1])
        elif ev.key == pygame.K_4:
            heil = [i for i, b in enumerate(self.wandler.beine) if b.heil]
            if heil:
                self.wandler.bein_verlieren(heil[-1])
                self.app.klaenge.spielen("rumpf_stoss")
                self.kamera.stossen(6.0)
                self._melden("BEIN AUSGEFALLEN - %d VON %d"
                             % (self.wandler.beine_heil, len(self.wandler.beine)))
        elif ev.key == pygame.K_5:
            for i in range(len(self.wandler.beine)):
                self.wandler.bein_richten(i)
            self.app.klaenge.spielen("station_an")
            self._melden("ALLE BEINE GERICHTET")
        elif ev.key == pygame.K_h:
            self.autopilot = not self.autopilot
            self.app.klaenge.spielen("station_an" if self.autopilot
                                     else "station_aus")
            self._melden("AUTOPILOT " + ("AN" if self.autopilot else "AUS"))
        elif ev.key == pygame.K_F3:
            self.zeigen = not self.zeigen

    # ---- Ablauf ----------------------------------------------------------
    def schritt(self, dt: float) -> None:
        e = self.app.eingabe
        w = K.WANDLER

        if not self.autopilot:
            soll = ((1.0 if e.gehalten("vor") else 0.0)
                    - (1.0 if e.gehalten("zurueck") else 0.0))
            lenk = ((1.0 if e.gehalten("rechts") else 0.0)
                    - (1.0 if e.gehalten("links") else 0.0))
            # Der Befehl schwillt an und ab - ein Steuerstand ist kein
            # Schalter. Was danach passiert, entscheiden die Beine.
            takt = w["schub_an"] if abs(soll) > abs(self.schub) else w["schub_ab"]
            self.schub += (soll - self.schub) * min(1.0, dt / max(0.01, takt))
            self.lenkung += (lenk - self.lenkung) * min(1.0, dt / w["dreh_an"])

        self.wandler.steuern(self.schub, self.lenkung, e.gehalten("sprint"))
        self.wandler.schritt(dt, self.boden, self.app.klaenge.spielen,
                             self.kamera.stossen)
        self.boden.schritt(dt)

        e0 = self.boden.ebene(0)
        self.kamera.schritt(dt, self.wandler.pos, self.wandler.pos,
                            (e0.pixel_breite, e0.pixel_hoehe))
        if self.hinweis_rest > 0:
            self.hinweis_rest -= dt

    # ---- Anzeige ----------------------------------------------------------
    def zeichnen(self, ziel: pygame.Surface, alpha: float) -> None:
        gross = self.flaeche
        gross.fill(K.C_VOID)
        self.renderer.welt_zeichnen(gross, self.boden, self.kamera, alpha,
                                    self.boden.hoehe(0))
        self.renderer.wandler_zeichnen(gross, self.wandler, self.kamera)
        pygame.transform.scale(gross, ziel.get_size(), ziel)
        ziel.blit(self.renderer._vignette, (0, 0))
        self._tafel(ziel)

    def _tafel(self, ziel) -> None:
        g = self.wandler.gangwerk
        p = self.wandler.plan
        hz, zyklus = g.zyklus(abs(g.schub))
        steht = len(g.stehende)
        luft = sum(1 for b in g.beine if not b.steht and b.heil)

        zeilen = [
            (p.klassenname, K.C_CREAM),
            ("BEFOHLEN  %3.0f" % (p.tempo * abs(g.schub)
                                  * (K.WANDLER["ueberlast"] if g.ueberlast else 1)),
             K.C_MUTED),
            ("GEMESSEN  %3.0f" % g.tempo_ist, K.C_TEAL),
            ("SCHRITT   %3.0f" % g._schrittweite(
                p.tempo * abs(g.schub), zyklus), K.C_MUTED),
            ("TAKT     %4.2f" % hz, K.C_MUTED),
            ("AM BODEN  %d/%d" % (steht, self.wandler.beine_heil), K.C_AMBER),
            ("IN LUFT   %d" % luft, K.C_MUTED),
        ]
        if self.wandler.beine_heil < len(g.beine):
            zeilen.append(("BEINE  %d VON %d"
                           % (self.wandler.beine_heil, len(g.beine)), K.C_RED))
        if not self.wandler.fahrbereit:
            zeilen.append(("NICHT FAHRBEREIT", K.C_RED))
        if g.ueberlast:
            zeilen.append(("UEBERLAST", K.C_ORANGE))
        if self.autopilot:
            zeilen.append(("AUTOPILOT", K.C_TEAL))

        breite = max(SCHRIFT.breite(z, 1) for z, _ in zeilen) + 10
        kasten = pygame.Surface((breite, len(zeilen) * 9 + 8), pygame.SRCALPHA)
        kasten.fill((12, 10, 8, 186))
        pygame.draw.rect(kasten, (52, 44, 34), kasten.get_rect(), 1)
        for i, (text, farbe) in enumerate(zeilen):
            kasten.blit(SCHRIFT.flaeche(text, farbe, 1), (5, 5 + i * 9))
        ziel.blit(kasten, (6, 6))

        if self.hinweis_rest > 0:
            s = SCHRIFT.flaeche(self.hinweis, K.C_CREAM, 1)
            ziel.blit(s, ((K.GAME_W - s.get_width()) // 2, 16))

        hilfe = "W/S SCHUB   A/D KURS   SHIFT UEBERLAST   H AUTOPILOT   " \
                "TAB ANSICHT   1-3 KLASSE   4 BEIN AB   5 RICHTEN"
        s = SCHRIFT.flaeche(hilfe, K.C_MUTED_DK, 1)
        ziel.blit(s, ((K.GAME_W - s.get_width()) // 2, K.GAME_H - 12))


def starten(headless: bool = False, beenden: bool = True) -> int:
    """Einstieg fuer `python -m dustfront --probe`."""
    from .core import App
    from .main import asset_ordner
    app = App("DUSTFRONT - PROBELAUF", asset_ordner(), headless=headless)
    app.schieben(Probelauf(app))
    app.laufen(beenden=beenden)
    return 0
