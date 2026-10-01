"""
DUSTFRONT - Die Minikarte (ein Versuch)
=======================================

Oben rechts, neben den Ebenen: der Grundriss der Ebene, auf der man
steht, und darauf

* man selbst (hell, mit Blickrichtung),
* die eigenen Leute - wer zur selben Fraktion gehoert,
* der Ausschnitt, den man gerade im Bild hat,
* in HUEGEL der Kreis, wenn er auf dieser Ebene liegt.

**Gegner stehen nicht darauf.** Das ist kein Vergessen: eine Karte, die
zeigt, wo der Feind hinter der Wand steht, ist ein Wandhack, den alle
haben. Wer einen Gegner sehen will, muss ihn sehen.

Der Grundriss wird je Ebene einmal gemalt und gemerkt - die Karte aendert
sich im Gefecht nicht, die Punkte darauf schon. Ein Kartenwechsel gibt
eine neue Welt und damit einen neuen Grundriss.
"""

from __future__ import annotations

import math

import pygame

from . import config as K

M = K.MINIKARTE

FARBE_BODEN = (58, 46, 34)
FARBE_WAND = (126, 104, 78)
FARBE_TREPPE = (72, 150, 140)
RAHMEN = (84, 66, 48)
GRUND = (11, 8, 6, 200)


class Minikarte:
    def __init__(self) -> None:
        self._welt = None
        self._grundriss: dict[int, pygame.Surface] = {}

    def rechteck(self, welt) -> pygame.Rect:
        """Wo sie steht: oben rechts, links neben den Ebenen."""
        e = welt.ebenen[0]
        breite, hoehe = self._mass(e.breite, e.hoehe)
        rechts = K.GAME_W - M["rand_rechts"]
        return pygame.Rect(rechts - breite, M["oben"], breite, hoehe)

    @staticmethod
    def _mass(kb: int, kh: int) -> tuple[int, int]:
        """Groesse in Pixeln: hoechstens so breit und hoch, Seiten wie die Karte."""
        f = min(M["breite"] / float(kb), M["hoehe"] / float(kh))
        return max(8, int(kb * f)), max(8, int(kh * f))

    def _grundriss_fuer(self, welt, nr: int) -> pygame.Surface:
        if welt is not self._welt:
            self._welt = welt
            self._grundriss = {}
        fertig = self._grundriss.get(nr)
        if fertig is not None:
            return fertig
        e = welt.ebenen[nr]
        klein = pygame.Surface((e.breite, e.hoehe), pygame.SRCALPHA)
        klein.fill((0, 0, 0, 0))
        for ty in range(e.hoehe):
            for tx in range(e.breite):
                art = e.kachel(tx, ty)
                if art == K.LEER:
                    continue
                if art in (K.TREPPE_HOCH, K.TREPPE_RUNTER, K.LUKE):
                    farbe = FARBE_TREPPE
                elif e.fest(tx, ty):
                    farbe = FARBE_WAND
                else:
                    farbe = FARBE_BODEN
                klein.set_at((tx, ty), farbe)
        fertig = pygame.transform.scale(klein, self._mass(e.breite, e.hoehe))
        self._grundriss[nr] = fertig
        return fertig

    def zeichnen(self, ziel, g) -> pygame.Rect | None:
        """Malt die Karte. Gibt ihr Rechteck zurueck, oder None."""
        ich = g.ich
        if ich is None or not g.welt.ebenen:
            return None
        nr = max(0, min(len(g.welt.ebenen) - 1, int(ich.ebene)))
        r = self.rechteck(g.welt)
        e = g.welt.ebenen[nr]
        sx = r.width / float(e.pixel_breite)
        sy = r.height / float(e.pixel_hoehe)

        def punkt(pos):
            return (int(r.x + pos.x * sx), int(r.y + pos.y * sy))

        grund = pygame.Surface(r.inflate(4, 4).size, pygame.SRCALPHA)
        grund.fill(GRUND)
        ziel.blit(grund, r.inflate(4, 4).topleft)
        ziel.blit(self._grundriss_fuer(g.welt, nr), r.topleft)

        # Der Kreis in HUEGEL.
        if g.regeln.get("zone") and getattr(g, "zone_ebene", -1) == nr:
            pygame.draw.circle(ziel, K.C_AMBER, punkt(g.zone_mitte),
                               max(2, int(K.ZONE["radius"] * sx)), 1)

        # Der Ausschnitt im Bild.
        mitte = g.kamera.pos
        sicht = pygame.Rect(0, 0, max(2, int(K.GAME_W * sx)), max(2, int(K.GAME_H * sy)))
        sicht.center = punkt(mitte)
        pygame.draw.rect(ziel, (150, 128, 96), sicht.clip(r), 1)

        # Die eigenen Leute, dann man selbst obenauf.
        for k in g.kaempfer.values():
            if k is ich or not k.lebt and not k.am_boden:
                continue
            if int(k.ebene) != nr or k.fraktion != ich.fraktion:
                continue
            farbe = g._farbe_fuer(k)
            pygame.draw.rect(ziel, farbe, (*(p - 1 for p in punkt(k.pos)), 3, 3))
        x, y = punkt(ich.pos)
        w = math.radians(getattr(ich, "winkel", 0.0))
        pygame.draw.line(ziel, K.C_TEAL, (x, y),
                         (x + int(5 * math.cos(w)), y + int(5 * math.sin(w))))
        pygame.draw.rect(ziel, (230, 255, 248), (x - 1, y - 1, 3, 3))

        pygame.draw.rect(ziel, RAHMEN, r.inflate(4, 4), 1)
        return r
