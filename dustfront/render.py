"""
DUSTFRONT - Darstellung
=======================

Kamera und Renderer. Zwei Regeln stecken hier drin, die spaeter nicht mehr
angefasst werden muessen:

**Sichtbarkeitsregel der Hoehenebenen.** Gezeichnet wird zuerst die Ebene
unter dir, abgedunkelt, danach deine eigene. Wo deine Ebene ein Loch hat
(Kachel "leer"), scheint die darunter durch. Genau so steht es im GDD: unter
dem Rumpf eines Walkers sieht man den Boden, und wer auf Hoehe 0 steht, sieht
die Beine als Saeulen. Mehr Etagen aendern an diesem Code nichts.

**Kamera.** Sie folgt weich, laeuft ein Stueck in Blickrichtung vor und hat
ein Ruckeln mit abklingender Staerke. Der Spieler bleibt trotzdem nah an der
Mitte, wie in den Mockups vorgesehen.
"""

from __future__ import annotations

import math
import random

import pygame

from . import art  # noqa: F401  registriert die Platzhalter-Bilder
from . import config as K
from .font import SCHRIFT

RND = random.Random(4711)


class Kamera:
    def __init__(self, ziel=(0, 0)) -> None:
        self.pos = pygame.Vector2(ziel)
        self.ruckeln = 0.0
        self.versatz = pygame.Vector2(0, 0)

    def stossen(self, kraft: float) -> None:
        self.ruckeln = min(K.KAMERA["ruckeln_max"], self.ruckeln + kraft)

    def schritt(self, dt: float, ziel: pygame.Vector2, blick: pygame.Vector2,
                grenze: tuple[int, int]) -> None:
        k = K.KAMERA
        vor = (blick - ziel)
        if vor.length() > k["maus_max"]:
            vor.scale_to_length(k["maus_max"])
        wunsch = ziel + vor * k["maus_zug"]
        self.pos += (wunsch - self.pos) * min(1.0, k["nachlauf"] * dt)

        self.ruckeln = max(0.0, self.ruckeln - k["ruckeln_abbau"] * dt * max(1.0, self.ruckeln))
        r = self.ruckeln
        self.versatz.update(RND.uniform(-r, r), RND.uniform(-r, r))

        # An den Kartenrand anlegen, damit man nicht ins Nichts schaut
        halb_w, halb_h = K.GAME_W / 2, K.GAME_H / 2
        bw, bh = grenze
        if bw > K.GAME_W:
            self.pos.x = max(halb_w, min(bw - halb_w, self.pos.x))
        else:
            self.pos.x = bw / 2
        if bh > K.GAME_H:
            self.pos.y = max(halb_h, min(bh - halb_h, self.pos.y))
        else:
            self.pos.y = bh / 2

    @property
    def ecke(self) -> pygame.Vector2:
        return pygame.Vector2(round(self.pos.x - K.GAME_W / 2 + self.versatz.x),
                              round(self.pos.y - K.GAME_H / 2 + self.versatz.y))

    def zu_welt(self, bildpunkt) -> pygame.Vector2:
        return pygame.Vector2(bildpunkt) + self.ecke


class Renderer:
    def __init__(self, bilder) -> None:
        self.bilder = bilder
        self._dunkel: dict[tuple, pygame.Surface] = {}
        self._schatten = self._schatten_bauen()
        self._vignette = self._vignette_bauen()
        self._blut = self._blut_bauen()
        self._wandschatten = self._wandschatten_bauen()
        self._boden_namen = ("boden", "boden_2", "boden_3", "boden_4")

    # ---- Vorgefertigtes -------------------------------------------
    @staticmethod
    def _schatten_bauen() -> pygame.Surface:
        s = pygame.Surface((34, 18), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, 90), s.get_rect())
        pygame.draw.ellipse(s, (0, 0, 0, 60), s.get_rect().inflate(6, 3))
        return s

    @staticmethod
    def _vignette_bauen() -> pygame.Surface:
        v = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
        rand = 74
        for i in range(rand):
            a = int(88 * (1 - i / rand) ** 2)
            if a <= 0:
                continue
            pygame.draw.rect(v, (0, 0, 0, a), (i, i, K.GAME_W - 2 * i, K.GAME_H - 2 * i), 1)
        return v

    @staticmethod
    def _wandschatten_bauen() -> pygame.Surface:
        """Schlagschatten, den eine feste Kachel auf den Boden wirft.
        Licht kommt von oben links, also faellt er nach unten rechts."""
        s = pygame.Surface((K.TILE + 7, K.TILE + 7), pygame.SRCALPHA)
        for i in range(7):
            a = int(96 * (1 - i / 7) ** 1.4)
            pygame.draw.rect(s, (0, 0, 0, a), (i, i, K.TILE, K.TILE))
        return s

    @staticmethod
    def _blut_bauen() -> pygame.Surface:
        s = pygame.Surface((26, 26), pygame.SRCALPHA)
        r = random.Random(9)
        for _ in range(14):
            x, y = r.randrange(4, 22), r.randrange(4, 22)
            pygame.draw.circle(s, (*K.C_BLUT, r.randrange(70, 150)), (x, y),
                               r.randrange(1, 5))
        return s

    def dunkel(self, surf: pygame.Surface, staerke: int) -> pygame.Surface:
        key = (id(surf), staerke)
        hit = self._dunkel.get(key)
        if hit is None:
            hit = surf.copy()
            hit.fill((staerke, staerke, staerke), special_flags=pygame.BLEND_RGB_MULT)
            if len(self._dunkel) > 400:
                self._dunkel.clear()
            self._dunkel[key] = hit
        return hit

    # ---- Welt ------------------------------------------------------
    def ebene_zeichnen(self, ziel, welt, index: int, ecke, dunkel: int | None) -> None:
        e = welt.ebene(index)
        t0x = max(0, int(ecke.x // K.TILE))
        t0y = max(0, int(ecke.y // K.TILE))
        t1x = min(e.breite - 1, int((ecke.x + K.GAME_W) // K.TILE))
        t1y = min(e.hoehe - 1, int((ecke.y + K.GAME_H) // K.TILE))
        bild = self.bilder.bild
        fest = []
        # Erster Durchgang: alles Begehbare
        for ty in range(t0y, t1y + 1):
            zeile = ty * e.breite
            sy = ty * K.TILE - ecke.y
            for tx in range(t0x, t1x + 1):
                kachel = e.kacheln[zeile + tx]
                if kachel == K.LEER:
                    continue
                daten = K.KACHELN[kachel]
                if daten["fest"]:
                    fest.append((tx, ty, daten["bild"], sy))
                    continue
                name = daten["bild"]
                if kachel == K.BODEN:
                    name = self._boden_namen[e.variante[zeile + tx]]
                s = bild(name)
                if dunkel is not None:
                    s = self.dunkel(s, dunkel)
                ziel.blit(s, (tx * K.TILE - ecke.x, sy))

        # Zweiter Durchgang: Schlagschatten, dann die festen Kacheln darueber
        sch = self._wandschatten
        if dunkel is not None:
            sch = self.dunkel(sch, dunkel)
        for (tx, ty, name, sy) in fest:
            ziel.blit(sch, (tx * K.TILE - ecke.x, sy))
        for (tx, ty, name, sy) in fest:
            s = bild(name)
            if dunkel is not None:
                s = self.dunkel(s, dunkel)
            ziel.blit(s, (tx * K.TILE - ecke.x, sy))
        # Dekale liegen auf dem Boden
        d = e.dekale
        if dunkel is None:
            ziel.blit(d, (-ecke.x, -ecke.y))
        else:
            ziel.blit(self.dunkel(d, dunkel), (-ecke.x, -ecke.y))

    def wesen_zeichnen(self, ziel, welt, index, ecke, alpha, dunkel=None) -> None:
        liste = [w for w in welt.wesen if w.ebene == index and w.lebt]
        liste.sort(key=lambda w: w.pos.y)
        for w in liste:
            p = w.zeichenpos(alpha) - ecke
            if w.schatten:
                sch = self._schatten
                if dunkel is not None:
                    sch = self.dunkel(sch, dunkel)
                ziel.blit(sch, (p.x - sch.get_width() / 2, p.y - sch.get_height() / 2 + 5))
            if w.spur is not None and w.tempo.length_squared() > 1:
                r = w.tempo.normalize()
                pygame.draw.line(ziel, (128, 80, 30), p - r * 17, p - r * 5, 1)
                pygame.draw.line(ziel, w.spur, p - r * 6, p, 1)
            if w.bild is None:
                continue
            s = self.bilder.gedreht(w.bild, w.winkel)
            if dunkel is not None:
                s = self.dunkel(s, dunkel)
            elif w.blitz > 0:
                s = s.copy()
                s.fill((210, 210, 210), special_flags=pygame.BLEND_RGB_ADD)
            ziel.blit(s, (p.x - s.get_width() / 2, p.y - s.get_height() / 2))

    def partikel_zeichnen(self, ziel, welt, index, ecke, alpha) -> None:
        for p in welt.partikel:
            if p.ebene != index:
                continue
            q = p.zeichenpos(alpha) - ecke
            f = max(0.0, p.leben / p.dauer)
            if p.art == "huelse":
                s = self.bilder.gedreht("huelse", p.winkel)
                ziel.blit(s, (q.x - s.get_width() / 2, q.y - s.get_height() / 2))
                continue
            g = max(1, int(p.groesse * (0.4 + 0.6 * f)))
            farbe = p.farbe
            if p.art == "funke":
                farbe = (255, min(255, farbe[1] + 40), 160) if f > 0.55 else farbe
            pygame.draw.rect(ziel, farbe, (int(q.x), int(q.y), g, g))

    def muendungsfeuer(self, ziel, welt, ecke, index) -> None:
        for (pos, winkel, eb, rest) in welt.muendungen:
            if eb != index or rest <= 0:
                continue
            s = self.bilder.gedreht("muendung", winkel)
            p = pos - ecke
            ziel.blit(s, (p.x - s.get_width() / 2, p.y - s.get_height() / 2),
                      special_flags=pygame.BLEND_RGB_ADD)

    def welt_zeichnen(self, ziel, welt, kamera, alpha) -> None:
        ecke = kamera.ecke
        held = welt.held
        oben = held.ebene if held else 0

        if oben - 1 >= 0:                      # was unter dir durchscheint
            self.ebene_zeichnen(ziel, welt, oben - 1, ecke, 118)
            self.wesen_zeichnen(ziel, welt, oben - 1, ecke, alpha, 118)

        self.ebene_zeichnen(ziel, welt, oben, ecke, None)
        self.wesen_zeichnen(ziel, welt, oben, ecke, alpha)
        self.partikel_zeichnen(ziel, welt, oben, ecke, alpha)
        self.muendungsfeuer(ziel, welt, ecke, oben)
        ziel.blit(self._vignette, (0, 0))

    # ---- HUD -------------------------------------------------------
    def hud(self, ziel, welt, spieler, wellen_text, punkte) -> None:
        f = SCHRIFT
        # Lebensbalken
        x, y = 12, K.GAME_H - 26
        breite = 128
        anteil = max(0.0, spieler.leben / spieler.max_leben)
        pygame.draw.rect(ziel, (18, 12, 9), (x - 2, y - 2, breite + 4, 12))
        pygame.draw.rect(ziel, K.C_MUTED_DK, (x - 2, y - 2, breite + 4, 12), 1)
        farbe = K.C_TEAL if anteil > 0.35 else K.C_RED
        segmente = 16
        for i in range(segmente):
            if i / segmente < anteil:
                pygame.draw.rect(ziel, farbe, (x + i * (breite // segmente), y,
                                               breite // segmente - 2, 8))
        f.zeichnen(ziel, "PANZERUNG", x, y - 12, K.C_MUTED, 1)
        f.zeichnen(ziel, "%d" % max(0, round(spieler.leben)), x + breite + 8, y,
                   K.C_CREAM, 1)

        # Waffe und Magazin
        d = spieler.waffe_daten
        rx = K.GAME_W - 12
        f.zeichnen(ziel, d["name"], rx, y - 12, K.C_AMBER, 1, ausrichtung="rechts")
        if spieler.nachlade_rest > 0:
            p = 1.0 - spieler.nachlade_rest / d["nachladen"]
            bw = 74
            pygame.draw.rect(ziel, (18, 12, 9), (rx - bw, y, bw, 8))
            pygame.draw.rect(ziel, K.C_AMBER, (rx - bw, y, int(bw * p), 8))
            f.zeichnen(ziel, "NACHLADEN", rx - bw - 6, y, K.C_MUTED, 1,
                       ausrichtung="rechts")
        else:
            munition = spieler.magazin[spieler.waffe_name]
            f.zeichnen(ziel, "%d / %d" % (munition, d["magazin"]), rx, y,
                       K.C_CREAM if munition else K.C_RED, 2, ausrichtung="rechts")

        # Ebenenanzeige, wie die Scrollleiste in den Mockups
        ex = K.GAME_W - 26
        for i in range(len(welt.ebenen) - 1, -1, -1):
            ey = 16 + (len(welt.ebenen) - 1 - i) * 14
            aktiv = (i == spieler.ebene)
            r = pygame.Rect(ex, ey, 18, 11)
            pygame.draw.rect(ziel, K.C_AMBER if aktiv else (18, 12, 9), r)
            pygame.draw.rect(ziel, K.C_AMBER if aktiv else K.C_MUTED_DK, r, 1)
            f.zeichnen(ziel, "E%d" % i, r.centerx, ey + 2,
                       (18, 12, 8) if aktiv else K.C_MUTED, 1, ausrichtung="mitte")

        # Kopfzeile
        f.zeichnen(ziel, wellen_text, 12, 12, K.C_MUTED, 1)
        f.zeichnen(ziel, "SCHROTT %d" % punkte, 12, 22, K.C_AMBER, 1)

    def hinweis(self, ziel, text) -> None:
        w = SCHRIFT.breite(text, 1) + 14
        r = pygame.Rect((K.GAME_W - w) // 2, K.GAME_H - 58, w, 15)
        pygame.draw.rect(ziel, (14, 10, 8), r)
        pygame.draw.rect(ziel, K.C_AMBER, r, 1)
        SCHRIFT.zeichnen(ziel, text, r.centerx, r.y + 4, K.C_CREAM, 1,
                         ausrichtung="mitte")

    def schaden_blende(self, ziel, staerke: float) -> None:
        if staerke <= 0:
            return
        s = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
        s.fill((*K.C_RED, int(90 * min(1.0, staerke))))
        ziel.blit(s, (0, 0))

    def debug(self, ziel, app, welt) -> None:
        f = SCHRIFT
        zeilen = [
            "FPS %d" % round(app.fps),
            "WESEN %d" % len(welt.wesen),
            "PARTIKEL %d" % len(welt.partikel),
            "EBENE %d VON %d" % (welt.held.ebene, len(welt.ebenen)),
        ]
        for i, z in enumerate(zeilen):
            f.zeichnen(ziel, z, K.GAME_W - 12, 60 + i * 9, K.C_TEAL, 1,
                       ausrichtung="rechts")
