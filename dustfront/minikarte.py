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

Der Grundriss kommt seit 0.34.100 aus kartenbild.py: einmal gross gemalt,
weich verkleinert und gemerkt - die Karte aendert sich im Gefecht nicht,
die Punkte darauf schon. Ein Kartenwechsel gibt eine neue Welt und damit
einen neuen Grundriss.
"""

from __future__ import annotations

import math
import random

import pygame

from . import config as K
from . import kartenbild

M = K.MINIKARTE

FARBE_BODEN = (58, 46, 34)
FARBE_WAND = (126, 104, 78)
FARBE_TREPPE = (72, 150, 140)
FARBE_GEGNER = (226, 72, 52)
FARBE_FEIND = (255, 64, 64)       # feindliche Spieler (Regel gegner_karte)
FARBE_BUGGY = (214, 166, 70)
FARBE_DUNKEL = (16, 11, 8)
FARBE_ICH = (230, 255, 248)       # man selbst
PING_FARBE = (255, 176, 40)       # der Funkwagen auf der gestoerten Karte
RAHMEN = (84, 66, 48)
GRUND = (11, 8, 6, 200)


class Minikarte:
    def __init__(self) -> None:
        self._welt = None

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

    def zeichnen(self, ziel, g, rahmen=None, rund: bool = False,
                 mass: float = 1.0) -> pygame.Rect | None:
        """Malt die Karte. Gibt ihr Rechteck zurueck, oder None.

        `rahmen` (seit 0.34.92): wohin und wie gross statt oben links - die
        runde Karte der Anzeige legt sie vergroessert um die eigene Figur.
        `rund`: ohne eigenen Grund und Rahmen, die zeichnet die Anzeige.
        `mass` (seit 0.34.100): so viel groesser als die Spielflaeche wird
        gemalt - die runde Karte kommt in Fensteraufloesung (App.hoch_auflegen),
        und Punkte, Pfeile und Striche wachsen mit."""
        ich = g.ich
        if ich is None or not g.welt.ebenen:
            return None
        nr = max(0, min(len(g.welt.ebenen) - 1, int(ich.ebene)))
        r = self.rechteck(g.welt) if rahmen is None else pygame.Rect(rahmen)
        e = g.welt.ebenen[nr]
        sx = r.width / float(e.pixel_breite)
        sy = r.height / float(e.pixel_hoehe)
        m = max(1.0, float(mass))

        def punkt(pos):
            return (int(r.x + pos.x * sx), int(r.y + pos.y * sy))

        def n(wert: float) -> int:
            return max(1, int(round(wert * m)))

        # Der durchscheinende Grund, je Groesse einmal gefuellt (seit
        # 0.34.75) - vorher jedes Bild eine neue, immer gleiche Flaeche.
        if not rund:
            groesse = r.inflate(4, 4).size
            grund = self.__dict__.get("_grund")
            if grund is None or grund.get_size() != groesse:
                grund = pygame.Surface(groesse, pygame.SRCALPHA)
                grund.fill(GRUND)
                self._grund = grund
            ziel.blit(grund, r.inflate(4, 4).topleft)
        # Der Grundriss, gross gemalt und weich verkleinert (seit 0.34.100,
        # kartenbild.py) - vorher ein Pixel je Kachel, hart verkleinert.
        ziel.blit(kartenbild.in_groesse(e, r.size), r.topleft)

        # Im Stoerkreis eines gegnerischen Funkwagens (seit 0.34.115): nur
        # Rauschen - und je Funkwagen, der einen erfasst, ein Ping an seinem Ort.
        # Sonst nichts: weder man selbst noch die eigenen Leute, nicht einmal
        # der Ausschnitt.
        stoerer = (g.funk_stoerer(ich.pos, getattr(ich, "team", -1), int(ich.ebene))
                   if hasattr(g, "funk_stoerer") else [])
        if stoerer:
            self._rauschen(ziel, r, m)
            self._pings(ziel, [punkt(b.mast_mitte()) for b in stoerer if int(b.ebene) == nr],
                        float(getattr(g.welt, "zeit", 0.0)), m)
            if not rund:
                pygame.draw.rect(ziel, RAHMEN, r.inflate(4, 4), 1)
            return r

        # Der Kreis in HUEGEL, auf jeder Ebene. Liegt er auf einer anderen
        # als man selbst, ist er blasser und hat einen Pfeil nach oben oder
        # unten - sonst sucht man auf der eigenen Ebene nach ihm.
        zone_ebene = getattr(g, "zone_ebene", -1)
        if g.regeln.get("zone") and zone_ebene >= 0:
            self._kreis(ziel, g, punkt(g.zone_mitte),
                        max(n(M["kreis_mindest"]), int(K.ZONE["radius"] * sx)),
                        zone_ebene - nr, m)

        # Der Ausschnitt im Bild.
        mitte = g.kamera.pos
        sicht = pygame.Rect(0, 0, max(2, int(g.kamera.breite * sx)),
                            max(2, int(g.kamera.hoehe * sy)))
        sicht.center = punkt(mitte)
        pygame.draw.rect(ziel, (196, 176, 140), sicht.clip(r), n(0.6))

        # Zombies und Bosse - darunter, damit die eigenen Leute obenauf
        # zu sehen sind, wenn es eng wird.
        allwissend = bool(getattr(g, "karte_allwissend", False))
        gegner = g.gegner_fuer_karte()
        if allwissend and getattr(g, "ist_gastgeber", False):
            # Allwissend (Testmodus, seit 0.34.77): jeder Zombie und Boss, auch
            # ohne Wellen, und die Tiere.
            from .mehrspieler import KampfGegner
            gegner = [(w.pos.x, w.pos.y, int(w.ebene)) for w in g.welt.wesen
                      if w.lebt and (isinstance(w, KampfGegner) or getattr(w, "tier", False))
                      and getattr(w, "art", "") != "puppe"]
        for (x, y, ebene) in gegner:
            if ebene == nr:
                self._punkt(ziel, punkt(pygame.Vector2(x, y)), FARBE_GEGNER, 1.0 * m)

        if allwissend:
            # Alle Kaempfer in den Farben ihrer Seite, mit dunklem Rand -
            # die eigenen Leute zeichnet die Schleife unten noch einmal.
            for k in g.kaempfer.values():
                if k is ich or not (k.lebt or getattr(k, "am_boden", False)):
                    continue
                if int(k.ebene) != nr or getattr(k, "raus", False):
                    continue
                self._punkt(ziel, punkt(k.pos), g._farbe_fuer(k), 1.5 * m)

        # Feindliche Spieler und Bots, wenn der Gastgeber es so eingestellt
        # hat (Regel "gegner_karte", seit 0.34.18) - unter den eigenen.
        # Seit 0.34.95 immer die, die eine eigene Drohne oder ein eigener
        # Horchposten gerade markiert hat - als rote Raute wie im Bild.
        alle_feinde = bool((getattr(g, "regelwerk", None) or {}).get("gegner_karte"))
        markiert = getattr(g, "fuer_mich_markiert", None)
        for k in g.kaempfer.values():
            if k is ich or not k.lebt or k.fraktion == ich.fraktion:
                continue
            if alle_feinde or (markiert is not None and markiert(k)):
                if int(k.ebene) != nr or getattr(k, "raus", False):
                    continue
                self._raute(ziel, punkt(k.pos), FARBE_FEIND, 2.2 * m)

        # Die eigenen Leute, dann man selbst obenauf.
        for k in g.kaempfer.values():
            if k is ich or not k.lebt and not k.am_boden:
                continue
            if int(k.ebene) != nr or k.fraktion != ich.fraktion:
                continue
            self._punkt(ziel, punkt(k.pos), g._farbe_fuer(k), 1.5 * m)

        # Man selbst: ein Pfeil in Blickrichtung (seit 0.34.100, vorher ein
        # Punkt mit Strich - auf der kleinen Karte kaum zu finden).
        self._pfeil(ziel, punkt(ich.pos), getattr(ich, "winkel", 0.0), 2.6 * m)

        # Die Buggys: immer, auch besetzt und auf anderen Ebenen. Wo ein
        # Wagen steht, ist eine Frage des Weges, nicht der Deckung. Zuletzt
        # gezeichnet, damit man den eigenen auch sieht, wenn man drinsitzt
        # - sonst laege das eigene Zeichen genau darauf.
        for b in getattr(g, "fahrzeuge", ()):
            if getattr(b, "kaputt", False):
                continue            # ein Wrack ist kein Wagen mehr (0.34.18)
            self._buggy(ziel, g, b, punkt(b.pos), int(b.ebene) != nr, m)
            if b.art == "werfer":
                # Eigenes Zeichen (seit 0.34.112): immer fuer die eigene Seite, fuer
                # die Gegner nur, solange er sich mit einer Salve verraten hat.
                seite = getattr(b.fahrer, "team", getattr(b, "team", -1)) if getattr(b, "fahrer", None) \
                    is not None else getattr(b, "team", getattr(b, "basis_team", -1))
                ich = g.ich
                if getattr(b, "markiert_rest", 0.0) > 0.0 or (ich is not None and seite == ich.team):
                    self.werfer_zeichen(ziel, punkt(b.pos), m)

        if not rund:
            pygame.draw.rect(ziel, RAHMEN, r.inflate(4, 4), 1)
        return r

    def _rauschen(self, ziel, r, mass: float) -> None:
        """Rauschen ueber der Karte (seit 0.34.115): ein paar fertige Bilder
        je Groesse, reihum, dazu ein heller Streifen, der nach unten wandert."""
        c = M["gestoert"]
        schluessel = (r.width, r.height, round(mass, 2))
        vorrat = self.__dict__.setdefault("_rausch", {})
        bilder = vorrat.get(schluessel)
        if bilder is None:
            # Fester Zufall: das Rauschen soll flackern, aber nicht von Lauf zu
            # Lauf anders aussehen (Tests, Bilder). Gemalt in Kartenpixeln und
            # grob hochgezogen, damit es auf der grossen runden Karte genauso
            # grobkoernig ist wie auf der kleinen.
            zufall = random.Random(r.width * 1000 + r.height)
            klein = (max(1, int(r.width / max(1.0, mass))), max(1, int(r.height / max(1.0, mass))))
            bilder = []
            for _ in range(int(c["bilder"])):
                f = pygame.Surface(klein, pygame.SRCALPHA)
                for y in range(klein[1]):
                    for x in range(klein[0]):
                        if zufall.random() < c["dichte"]:
                            h = zufall.randrange(70, 190)
                            f.set_at((x, y), (h, h - 6, h - 14, zufall.randrange(150, 235)))
                bilder.append(pygame.transform.scale(f, (r.width, r.height)))
            vorrat[schluessel] = bilder
        zeit = pygame.time.get_ticks() / 1000.0
        ziel.blit(bilder[int(zeit * c["takt"]) % len(bilder)], r.topleft)
        hoehe = max(2, int(r.height * c["streifen_hoehe"]))
        y = int((zeit * c["streifen_tempo"] % 1.0) * (r.height + hoehe)) - hoehe
        streifen = pygame.Surface((r.width, hoehe), pygame.SRCALPHA)
        streifen.fill((200, 190, 170, 46))
        alt = ziel.get_clip()
        ziel.set_clip(r.clip(alt))
        ziel.blit(streifen, (r.x, r.y + y))
        ziel.set_clip(alt)

    @staticmethod
    def _pings(ziel, orte: list, zeit: float, mass: float) -> None:
        """Die Orte der Funkwagen auf der gestoerten Karte: je ein Punkt und
        zwei Ringe, die nach aussen laufen und verblassen. Erst alle Ringe,
        dann alle Punkte - sonst ueberdeckt der Ring des einen den Punkt des
        anderen, wenn sich ihre Kreise decken."""
        c = M["gestoert"]
        for i, (x, y) in enumerate(orte):
            for versatz in (0.0, 0.5):
                t = ((zeit / c["ping_dauer"]) + versatz + i * 0.27) % 1.0
                rr = max(2, int(round((3.0 + t * 9.0) * mass)))
                helle = 1.0 - t
                farbe = tuple(int(a * helle + d * (1.0 - helle)) for a, d in zip(PING_FARBE, FARBE_DUNKEL))
                pygame.draw.circle(ziel, farbe, (int(x), int(y)), rr, max(1, int(round(mass))))
        for x, y in orte:
            pygame.draw.circle(ziel, FARBE_DUNKEL, (int(x), int(y)), max(2, int(round(2.4 * mass))))
            pygame.draw.circle(ziel, PING_FARBE, (int(x), int(y)), max(1, int(round(1.6 * mass))))

    @staticmethod
    def werfer_zeichen(ziel, mitte, mass: float = 1.0) -> None:
        """Das Zeichen eines Werfers (seit 0.34.112): ein Dreieck mit drei
        Punkten darueber - drei Raketen. Gebraucht auf der Minikarte und auf
        der Nachschubkarte."""
        x, y = int(mitte[0]), int(mitte[1])
        g = max(2, int(round(3 * mass)))
        dreieck = [(x, y - g), (x + g, y + g), (x - g, y + g)]
        pygame.draw.polygon(ziel, FARBE_DUNKEL, dreieck, max(2, int(round(mass * 1.6))))
        pygame.draw.polygon(ziel, (250, 208, 133), dreieck)
        for dx in (-g, 0, g):
            pygame.draw.circle(ziel, (236, 72, 52), (x + dx, y - g - max(2, int(mass * 2))),
                               max(1, int(round(mass))))

    @staticmethod
    def _punkt(ziel, mitte, farbe, radius: float) -> None:
        """Ein runder Punkt mit dunklem Rand - liest sich auf hellem Fels
        wie auf dunklem Sand."""
        rr = max(1, int(round(radius)))
        pygame.draw.circle(ziel, FARBE_DUNKEL, mitte, rr + max(1, rr // 2))
        pygame.draw.circle(ziel, farbe, mitte, rr)

    @staticmethod
    def _raute(ziel, mitte, farbe, gross: float) -> None:
        x, y = mitte
        g = max(2, int(round(gross)))
        rand = max(1, g // 2)
        aussen = [(x, y - g - rand), (x + g + rand, y), (x, y + g + rand), (x - g - rand, y)]
        innen = [(x, y - g), (x + g, y), (x, y + g), (x - g, y)]
        pygame.draw.polygon(ziel, FARBE_DUNKEL, aussen)
        pygame.draw.polygon(ziel, farbe, innen)

    @staticmethod
    def _pfeil(ziel, mitte, winkel: float, gross: float) -> None:
        vorn = pygame.Vector2(1, 0).rotate(winkel)
        quer = pygame.Vector2(-vorn.y, vorn.x)
        m = pygame.Vector2(mitte)
        spitze = m + vorn * gross * 1.4
        links = m - vorn * gross * 0.8 + quer * gross * 0.9
        rechts = m - vorn * gross * 0.8 - quer * gross * 0.9
        kerbe = m - vorn * gross * 0.35
        ecken = [spitze, links, kerbe, rechts]
        pygame.draw.polygon(ziel, FARBE_DUNKEL, ecken, max(2, int(gross * 0.6)))
        pygame.draw.polygon(ziel, FARBE_ICH, ecken)

    @staticmethod
    def _blass(farbe) -> tuple:
        return tuple(int(c * 0.5 + d * 0.5) for c, d in zip(farbe[:3], FARBE_BODEN))

    def _kreis(self, ziel, g, mitte, radius: int, hoeher: int, m: float = 1.0) -> None:
        """Der Kreis: in der Farbe des Teams, das ihn haelt (wie der
        Pfeil am Bildrand). `hoeher` > 0: er liegt ueber einem, < 0
        darunter, 0 auf derselben Ebene."""
        farbe = g._zonenfarbe()[0] if hasattr(g, "_zonenfarbe") else K.C_AMBER
        if hoeher:
            farbe = self._blass(farbe)
        dick = max(1, int(round(m)))
        pygame.draw.circle(ziel, FARBE_DUNKEL, mitte, radius + dick, dick)
        pygame.draw.circle(ziel, farbe, mitte, radius, dick)
        ziel.set_at(mitte, farbe)
        if not hoeher:
            return
        # Ein kleines Dreieck rechts daneben: Spitze nach oben, wenn der
        # Kreis hoeher liegt, nach unten, wenn tiefer.
        q = max(2, int(round(2 * m)))
        x, y = mitte[0] + radius + q + 1, mitte[1]
        if hoeher > 0:
            ecken = [(x, y - q), (x - q, y + q // 2), (x + q, y + q // 2)]
        else:
            ecken = [(x, y + q), (x - q, y - q // 2), (x + q, y - q // 2)]
        pygame.draw.polygon(ziel, FARBE_DUNKEL, ecken, 2)
        pygame.draw.polygon(ziel, g._zonenfarbe()[0] if hasattr(g, "_zonenfarbe")
                            else K.C_AMBER, ecken)

    def _buggy(self, ziel, g, b, mitte, andere_ebene: bool, mass: float = 1.0) -> None:
        """Ein Buggy: laenglich in Fahrtrichtung, besetzt mit einem Punkt
        in der Farbe des Fahrers."""
        vorn = pygame.Vector2(1, 0).rotate(b.winkel)
        quer = pygame.Vector2(-vorn.y, vorn.x)
        # Panzer und Panzerwagen (seit 0.34.59) groesser als der Buggy.
        gross = M["schwer_mass"] if getattr(b, "rechteckig", False) else 1.0
        l, q = M["buggy_laenge"] / 2.0 * gross * mass, M["buggy_breite"] / 2.0 * gross * mass
        m = pygame.Vector2(mitte)
        ecken = [m + vorn * l + quer * q, m + vorn * l - quer * q,
                 m - vorn * l - quer * q, m - vorn * l + quer * q]
        farbe = self._blass(FARBE_BUGGY) if andere_ebene else FARBE_BUGGY
        pygame.draw.polygon(ziel, farbe, ecken)
        pygame.draw.polygon(ziel, FARBE_DUNKEL, ecken, max(1, int(round(mass * 0.8))))
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
        rr = max(1, int(round(mass)))
        pygame.draw.circle(ziel, fahrerfarbe, mitte, rr)
