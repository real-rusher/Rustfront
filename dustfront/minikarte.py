"""
DUSTFRONT - Die Minikarte (ein Versuch)
=======================================

Oben links (seit 0.30; vorher oben rechts): der Grundriss der Ebene, auf
der man steht, und darauf

* man selbst (hell, mit Blickrichtung),
* die eigenen Leute - wer zur selben Fraktion gehoert,
* die Zombies und Bosse, wenn es welche gibt (PVE, PVPVE, Gehege),
* der Ausschnitt, den man gerade im Bild hat,
* in HUEGEL der Kreis - seit 0.34.10 auch, wenn er auf einer anderen
  Ebene liegt: dann blasser und mit einem kleinen Pfeil, der sagt, ob
  er darueber oder darunter liegt,
* die Buggys (seit 0.34.10), immer und auf jeder Ebene, auch wenn
  jemand faehrt - mit einem Punkt in der Farbe des Fahrers.

**Gegnerische Spieler stehen nicht darauf.** Das ist kein Vergessen: eine
Karte, die zeigt, wo der Feind hinter der Wand steht, ist ein Wandhack,
den alle haben. Bei den Zombies ist es anders - sie sind keine Mitspieler,
die sich verstecken, und in PVE spielt man gemeinsam gegen sie.

Die eine gewollte Ausnahme (seit 0.34.10): wer einen Buggy faehrt, steht
mit ihm auf der Karte, auch fuer die Gegenseite. Gewuenscht war, dass die
Wagen immer zu sehen sind; ein Buggy ist laut und schnell, wer ihn nimmt,
tauscht Deckung gegen Tempo.

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
FARBE_GEGNER = (226, 72, 52)
FARBE_BUGGY = (214, 166, 70)
FARBE_DUNKEL = (16, 11, 8)
RAHMEN = (84, 66, 48)
GRUND = (11, 8, 6, 200)


class Minikarte:
    def __init__(self) -> None:
        self._welt = None
        self._grundriss: dict[int, pygame.Surface] = {}

    def rechteck(self, welt) -> pygame.Rect:
        """Wo sie steht: oben links."""
        e = welt.ebenen[0]
        breite, hoehe = self._mass(e.breite, e.hoehe)
        return pygame.Rect(M["links"], M["oben"], breite, hoehe)

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
                if art in (K.TREPPE_HOCH, K.TREPPE_RUNTER, K.LUKE,
                           K.AUFZUG_HOCH, K.AUFZUG_RUNTER):
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

        # Der Kreis in HUEGEL, auf jeder Ebene. Liegt er auf einer anderen
        # als man selbst, ist er blasser und hat einen Pfeil nach oben oder
        # unten - sonst sucht man auf der eigenen Ebene nach ihm.
        zone_ebene = getattr(g, "zone_ebene", -1)
        if g.regeln.get("zone") and zone_ebene >= 0:
            self._kreis(ziel, g, punkt(g.zone_mitte),
                        max(M["kreis_mindest"], int(K.ZONE["radius"] * sx)),
                        zone_ebene - nr)

        # Der Ausschnitt im Bild.
        mitte = g.kamera.pos
        sicht = pygame.Rect(0, 0, max(2, int(g.kamera.breite * sx)),
                            max(2, int(g.kamera.hoehe * sy)))
        sicht.center = punkt(mitte)
        pygame.draw.rect(ziel, (150, 128, 96), sicht.clip(r), 1)

        # Zombies und Bosse - darunter, damit die eigenen Leute obenauf
        # zu sehen sind, wenn es eng wird.
        for (x, y, ebene) in g.gegner_fuer_karte():
            if ebene == nr:
                px, py = punkt(pygame.Vector2(x, y))
                pygame.draw.rect(ziel, FARBE_GEGNER, (px - 1, py - 1, 2, 2))

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

        # Die Buggys: immer, auch besetzt und auf anderen Ebenen. Wo ein
        # Wagen steht, ist eine Frage des Weges, nicht der Deckung. Zuletzt
        # gezeichnet, damit man den eigenen auch sieht, wenn man drinsitzt
        # - sonst laege das eigene Zeichen genau darauf.
        for b in getattr(g, "fahrzeuge", ()):
            self._buggy(ziel, g, b, punkt(b.pos), int(b.ebene) != nr)

        pygame.draw.rect(ziel, RAHMEN, r.inflate(4, 4), 1)
        return r

    @staticmethod
    def _blass(farbe) -> tuple:
        return tuple(int(c * 0.5 + d * 0.5) for c, d in zip(farbe[:3], FARBE_BODEN))

    def _kreis(self, ziel, g, mitte, radius: int, hoeher: int) -> None:
        """Der Kreis: in der Farbe des Teams, das ihn haelt (wie der
        Pfeil am Bildrand). `hoeher` > 0: er liegt ueber einem, < 0
        darunter, 0 auf derselben Ebene."""
        farbe = g._zonenfarbe()[0] if hasattr(g, "_zonenfarbe") else K.C_AMBER
        if hoeher:
            farbe = self._blass(farbe)
        pygame.draw.circle(ziel, FARBE_DUNKEL, mitte, radius + 1, 1)
        pygame.draw.circle(ziel, farbe, mitte, radius, 1)
        ziel.set_at(mitte, farbe)
        if not hoeher:
            return
        # Ein kleines Dreieck rechts daneben: Spitze nach oben, wenn der
        # Kreis hoeher liegt, nach unten, wenn tiefer.
        x, y = mitte[0] + radius + 3, mitte[1]
        if hoeher > 0:
            ecken = [(x, y - 2), (x - 2, y + 1), (x + 2, y + 1)]
        else:
            ecken = [(x, y + 2), (x - 2, y - 1), (x + 2, y - 1)]
        pygame.draw.polygon(ziel, FARBE_DUNKEL, ecken, 2)
        pygame.draw.polygon(ziel, g._zonenfarbe()[0] if hasattr(g, "_zonenfarbe")
                            else K.C_AMBER, ecken)

    def _buggy(self, ziel, g, b, mitte, andere_ebene: bool) -> None:
        """Ein Buggy: laenglich in Fahrtrichtung, besetzt mit einem Punkt
        in der Farbe des Fahrers."""
        vorn = pygame.Vector2(1, 0).rotate(b.winkel)
        quer = pygame.Vector2(-vorn.y, vorn.x)
        l, q = M["buggy_laenge"] / 2.0, M["buggy_breite"] / 2.0
        m = pygame.Vector2(mitte)
        ecken = [m + vorn * l + quer * q, m + vorn * l - quer * q,
                 m - vorn * l - quer * q, m - vorn * l + quer * q]
        farbe = self._blass(FARBE_BUGGY) if andere_ebene else FARBE_BUGGY
        pygame.draw.polygon(ziel, farbe, ecken)
        pygame.draw.polygon(ziel, FARBE_DUNKEL, ecken, 1)
        fahrer = getattr(b, "fahrer", None)
        ich = g.ich
        if (getattr(ich, "im_fahrzeug", False) and ich.ebene == b.ebene
                and ich.pos.distance_squared_to(b.pos) < 4.0):
            # Man sitzt selbst drin: der Punkt in der Farbe des eigenen
            # Zeichens.
            fahrerfarbe = (230, 255, 248)
        elif fahrer is not None:
            fahrerfarbe = g._farbe_fuer(fahrer) if hasattr(g, "_farbe_fuer") else K.C_CREAM
        elif getattr(b, "besetzt", False):
            team = getattr(b, "team", -1)
            fahrerfarbe = (K.TEAMS["farben"][team]
                           if 0 <= team < len(K.TEAMS["farben"]) else K.C_CREAM)
        else:
            return
        pygame.draw.rect(ziel, fahrerfarbe, (mitte[0] - 1, mitte[1] - 1, 2, 2))
