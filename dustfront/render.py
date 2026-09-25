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

import random

import math

import pygame

from . import art  # noqa: F401  registriert die Platzhalter-Bilder
from . import config as K
from .beine import knie_punkt
from .font import SCHRIFT

RND = random.Random(4711)


class Kamera:
    def __init__(self, ziel=(0, 0), sicht=None) -> None:
        self.pos = pygame.Vector2(ziel)
        self.ruckeln = 0.0
        self.versatz = pygame.Vector2(0, 0)
        # Wie gross der Ausschnitt ist, den diese Kamera zeigt. Voreingestellt
        # die Bildgroesse - die Aussenansicht eines Wandlers setzt hier mehr
        # ein und zeichnet auf eine groessere Flaeche, die danach verkleinert
        # wird. Ohne das haengt jede Kamera an GAME_W und GAME_H fest.
        self.sicht = pygame.Vector2(sicht or (K.GAME_W, K.GAME_H))
        # Auf welches Vielfache die Bildecke einrastet.
        #
        # Das ist keine Feinheit, sondern der Unterschied zwischen ruhig und
        # unbrauchbar. Wird eine grosse Flaeche hinterher verkleinert, tastet
        # das Verkleinern ein festes Raster ab. Wandert die Ecke um einen
        # einzelnen Weltpixel, verschiebt sich dieses Raster gegen die
        # Textur - und dann flimmert **das ganze Bild**, nicht nur ein Rand.
        #
        # Gemessen: bei 1 zu 2 und drei Weltpixeln Versatz wechselten 29,5
        # Prozent aller Bildpunkte ihre Farbe, ohne dass sich etwas bewegt
        # haette. Rastet die Ecke auf dem Verkleinerungsfaktor ein, sind es
        # null.
        self.raster = 1

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
        halb_w, halb_h = self.sicht.x / 2, self.sicht.y / 2
        bw, bh = grenze
        if bw > self.sicht.x:
            self.pos.x = max(halb_w, min(bw - halb_w, self.pos.x))
        else:
            self.pos.x = bw / 2
        if bh > self.sicht.y:
            self.pos.y = max(halb_h, min(bh - halb_h, self.pos.y))
        else:
            self.pos.y = bh / 2

    @property
    def ecke(self) -> pygame.Vector2:
        r = max(1, int(self.raster))
        x = self.pos.x - self.sicht.x / 2 + self.versatz.x
        y = self.pos.y - self.sicht.y / 2 + self.versatz.y
        return pygame.Vector2(round(x / r) * r, round(y / r) * r)

    def zu_welt(self, bildpunkt) -> pygame.Vector2:
        return pygame.Vector2(bildpunkt) + self.ecke


class Renderer:
    def __init__(self, bilder) -> None:
        self.bilder = bilder
        self._dunkel: dict[tuple, pygame.Surface] = {}
        self._schatten_cache: dict[tuple, pygame.Surface] = {}
        self._tiefen: dict[int, pygame.Surface] = {}
        self._dunst = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
        self._linie = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
        self._brand: dict[int, pygame.Surface] = {}
        self._fleck_cache: dict[tuple, pygame.Surface] = {}
        # Auch Schatten, Vignette und die Dekale kommen aus der Registratur:
        # eine Datei assets/vignette.png ersetzt sie genauso wie eine Kachel.
        # Gehalten werden sie hier, damit die Zeichenschleife nicht bei jedem
        # Bild nachschlaegt.
        self._vignette = bilder.bild("vignette")
        self._blut = bilder.bild("blut")
        self._wandschatten = bilder.bild("wandschatten")
        self._boden_namen = ("boden", "boden_2", "boden_3", "boden_4")
        self._deck_namen = ("deck", "deck_2", "deck_3", "deck_4")
        # Beinglieder und Rumpfumrisse: einmal auf Mass gebracht, dann nur
        # noch gedreht. Ein Wandler zeichnet je Bild bis zu zwoelf Glieder,
        # und jedes davon neu zu skalieren waere die teuerste Zeile im
        # ganzen Renderer.
        self._glieder: dict[tuple, pygame.Surface] = {}
        self._gedrehte: dict[tuple, pygame.Surface] = {}
        self._umrisse: dict[tuple, pygame.Surface] = {}
        self._schleier_cache: dict[tuple, pygame.Surface] = {}
        self._vignetten: dict[tuple, pygame.Surface] = {}

    # ---- Vorgefertigtes -------------------------------------------
    def _passend(self, cache: dict, name: str, groesse, deckkraft: float = 1.0):
        """Ein Bild aus der Registratur auf eine Groesse gebracht, gemerkt.

        Schatten, Blut und Brandfleck haben keine feste Groesse: sie richten
        sich nach dem, was sie wirft. Gemalt sind sie einmal in ihrem
        Basismass, hier werden sie darauf umgerechnet. Das gilt fuer den
        Platzhalter wie fuer eine hingelegte Datei - beide sind an dieser
        Stelle nur noch eine Form.
        """
        w = max(1, int(groesse[0]))
        h = max(1, int(groesse[1]))
        deckung = max(0, min(255, int(round(255 * deckkraft))))
        key = (w, h, deckung)
        hit = cache.get(key)
        if hit is not None:
            return hit
        # Hart skalieren, genau wie die Registratur es mit einer Datei macht.
        # Weichzeichnen wuerde aus einem Blutfleck einen Farbnebel machen.
        hit = pygame.transform.scale(self.bilder.bild(name), (w, h))
        if deckung < 255:
            hit = hit.copy()
            hit.fill((255, 255, 255, deckung), special_flags=pygame.BLEND_RGBA_MULT)
        if len(cache) > 200:
            cache.clear()
        cache[key] = hit
        return hit

    def schatten(self, radius: float, f: float = 1.0) -> pygame.Surface:
        """Schatten passend zum Koerperkreis des Wesens.

        Frueher war das ein festes Oval fuer alle, das weder zur Groesse noch
        zur Fusslinie passte. Jetzt richtet sich das Oval nach dem Radius,
        und f schrumpft und lichtet es, wenn das Wesen in der Luft haengt.
        """
        d = K.DEKAL
        r = max(3.0, float(radius))
        return self._passend(self._schatten_cache, "schatten",
                             (r * d["schatten_breite"] * f + 4,
                              r * d["schatten_hoehe"] * f + 4), f)

    def blutfleck(self, radius: float) -> pygame.Surface:
        """Was liegen bleibt, wo ein Wesen gestorben ist. Ein Brecher
        hinterlaesst mehr als ein Laeufer, darum haengt es am Radius."""
        basis = K.BILD_MASS["blut"]
        k = max(0.4, float(radius) / K.DEKAL["blut_radius"])
        return self._passend(self._fleck_cache, "blut",
                             (basis[0] * k, basis[1] * k))

    def brandfleck(self, radius: float) -> pygame.Surface:
        """Russfleck, den eine Granate hinterlaesst."""
        k = max(0.2, float(radius) / K.DEKAL["brand_radius"])
        basis = K.BILD_MASS["brandfleck"]
        return self._passend(self._brand, "brandfleck",
                             (basis[0] * k, basis[1] * k))

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
        # Der Ausschnitt richtet sich nach der Zielflaeche, nicht nach der
        # Bildgroesse: die Tiefenflaeche fuer untere Ebenen ist groesser.
        zw, zh = ziel.get_size()
        t0x = max(0, int(ecke.x // K.TILE))
        t0y = max(0, int(ecke.y // K.TILE))
        t1x = min(e.breite - 1, int((ecke.x + zw) // K.TILE))
        t1y = min(e.hoehe - 1, int((ecke.y + zh) // K.TILE))
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
        # Dekale liegen auf dem Boden - falls es ueberhaupt welche gibt.
        d = e.dekale
        if d is None:
            return
        if dunkel is None:
            ziel.blit(d, (-ecke.x, -ecke.y))
        else:
            ziel.blit(self.dunkel(d, dunkel), (-ecke.x, -ecke.y))

    def wesen_zeichnen(self, ziel, welt, index, ecke, alpha, dunkel=None) -> None:
        liste = [w for w in welt.wesen if w.ebene == index and w.lebt]
        liste.sort(key=lambda w: w.pos.y)
        for w in liste:
            p = boden = w.zeichenpos(alpha) - ecke  # Stelle, auf der es steht
            if w.schatten:
                f = (1.0 if w.flug <= 0
                     else max(K.DEKAL["schatten_luft"], 1.0 - w.flug / 240.0))
                sch = self.schatten(w.radius, f)
                ziel.blit(sch, (boden.x - sch.get_width() / 2 + 1,
                                boden.y - sch.get_height() / 2 + 3))
            if w.flug > 0:
                # Der Schatten gehoert auf diesen Boden, das Wesen selbst
                # nicht: es haengt zwischen den Ebenen und wird nach allen
                # Ebenen gezeichnet, mit dem Massstab seiner eigenen Hoehe.
                continue
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

    def _bildpunkt(self, weltpos, kamera, k: float) -> pygame.Vector2:
        """Wo ein Weltpunkt im Bild liegt, wenn er mit k verkleinert wird.

        Dieselbe Rechnung, die auch hinter der Tiefenflaeche steckt: gleiche
        Weltmitte, kleinerer Massstab.
        """
        mitte = kamera.pos + kamera.versatz
        return pygame.Vector2(
            K.GAME_W / 2 + (weltpos.x - mitte.x) * k,
            K.GAME_H / 2 + (weltpos.y - mitte.y) * k)

    def fliegende_zeichnen(self, ziel, welt, kamera, alpha, blick_hoehe) -> None:
        """Wesen im Sturz, nach allen Ebenen und mit eigenem Massstab.

        Ein fallendes Wesen gehoert zu keiner Ebene, es haengt zwischen
        ihnen. Wurde es mit seiner Zielebene gezeichnet, trug es auch deren
        Massstab - beim Absprung also den einer Ebene, die noch weit unter
        ihm lag. Es schrumpfte dadurch schlagartig zusammen und sass
        gleichzeitig um die volle Fallhoehe zu hoch im Bild.

        Hier bekommt es den Massstab seiner eigenen Hoehe. Sinkt die Ansicht
        mit ihm - das tut sie bei der eigenen Figur - bleibt es stehen und
        die Welt waechst unter ihm heran. Genau das soll sich anfuehlen wie
        ein Blick von oben in echte Tiefe.
        """
        p = K.PERSPEKTIVE
        fliegende = [w for w in welt.wesen
                     if w.lebt and w.flug > 0 and w.bild is not None]
        if not fliegende:
            return
        # Das hoechste zuletzt, damit es ueber den tieferen liegt.
        fliegende.sort(key=lambda w: welt.hoehe(w.ebene) + w.flug)
        for w in fliegende:
            dz = blick_hoehe - (welt.hoehe(w.ebene) + w.flug)
            if dz < -p["ausblenden"]:
                continue                      # zu weit ueber der Ansicht
            k = p["brennweite"] / max(60.0, p["brennweite"] + dz)
            s = self.bilder.gedreht(w.bild, w.winkel)
            if abs(k - 1.0) > p["massstab_schwelle"]:
                s = pygame.transform.scale(
                    s, (max(1, int(round(s.get_width() * k))),
                        max(1, int(round(s.get_height() * k)))))
            if w.blitz > 0:
                s = s.copy()
                s.fill((210, 210, 210), special_flags=pygame.BLEND_RGB_ADD)
            b = self._bildpunkt(w.zeichenpos(alpha), kamera, k)
            ziel.blit(s, (b.x - s.get_width() / 2, b.y - s.get_height() / 2))

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

    def _tiefenflaeche(self, k: float, groesse) -> pygame.Surface:
        """Hilfsflaeche fuer eine tiefer liegende Ebene.

        Sie zeigt einen groesseren Weltausschnitt und wird danach auf die
        Zielgroesse verkleinert. Genau das laesst die untere Ebene weiter weg
        wirken: gleiche Weltmitte, kleinerer Massstab.

        **Die Groesse kommt vom Ziel, nicht von GAME_W.** Die Aussenansicht
        eines Wandlers zeichnet auf eine groessere Flaeche; stand hier die
        Bildgroesse fest, wurde nur ihr linkes oberes Viertel gefuellt - und
        genau das sah man als harte Helligkeitskante mitten im Bild.
        """
        zw, zh = int(groesse[0]), int(groesse[1])
        schluessel = (int(k * 100), zw, zh)
        hit = self._tiefen.get(schluessel)
        if hit is None:
            hit = pygame.Surface((int(zw / k) + 2, int(zh / k) + 2),
                                 pygame.SRCALPHA)
            if len(self._tiefen) > 48:
                self._tiefen.clear()
            self._tiefen[schluessel] = hit
        return hit

    def _schleier(self, groesse) -> pygame.Surface:
        """Dunstflaeche in Zielgroesse, gehalten je Groesse."""
        zw, zh = int(groesse[0]), int(groesse[1])
        hit = self._schleier_cache.get((zw, zh))
        if hit is None:
            hit = pygame.Surface((zw, zh), pygame.SRCALPHA)
            self._schleier_cache[(zw, zh)] = hit
        return hit

    def vignette(self, groesse) -> pygame.Surface:
        """Die Vignette auf Zielgroesse gebracht, gehalten je Groesse."""
        zw, zh = int(groesse[0]), int(groesse[1])
        if (zw, zh) == self._vignette.get_size():
            return self._vignette
        hit = self._vignetten.get((zw, zh))
        if hit is None:
            hit = pygame.transform.scale(self._vignette, (zw, zh))
            self._vignetten[(zw, zh)] = hit
        return hit

    def welt_zeichnen(self, ziel, welt, kamera, alpha, blick_hoehe=None) -> None:
        """Zeichnet alle Ebenen relativ zu einer Ansichtshoehe.

        Die Ansicht haengt bewusst nicht an der Ebene der Figur, sondern an
        einer Hoehe in Welt-Pixeln. Dadurch faellt beim Sturz nicht die
        Darstellung um eine Stufe, sondern die Ansicht sinkt mit: die untere
        Ebene waechst heran, die verlassene rutscht darueber weg. Dieselbe
        Zahl treibt spaeter das freie Scrollen durch die Etagen.

        dz = blick_hoehe - Ebenenhoehe.
            dz > 0   liegt unter der Ansicht: verkleinert, dunkler, im Dunst
            dz = 0   die angeschaute Ebene: unveraendert
            dz < 0   liegt darueber: vergroessert und ausgeblendet
        """
        ecke = kamera.ecke
        held = welt.held
        p = K.PERSPEKTIVE
        ziel_gross = ziel.get_size()
        if blick_hoehe is None:
            blick_hoehe = welt.hoehe(held.ebene if held else 0)

        for idx in range(len(welt.ebenen)):
            dz = blick_hoehe - welt.hoehe(idx)
            if dz < -p["ausblenden"] or dz > p["brennweite"] * p["tiefe_sichtbar"]:
                continue
            sicht = 1.0 if dz >= 0 else max(0.0, 1.0 + dz / p["ausblenden"])
            if sicht <= 0.01:
                continue
            k = p["brennweite"] / max(60.0, p["brennweite"] + dz)

            if abs(dz) < 1.0:                      # die angeschaute Ebene
                self.ebene_zeichnen(ziel, welt, idx, ecke, None)
                self.wesen_zeichnen(ziel, welt, idx, ecke, alpha)
                self.partikel_zeichnen(ziel, welt, idx, ecke, alpha)
                self.muendungsfeuer(ziel, welt, ecke, idx)
                continue

            dunkel = max(48, int(p["dunkel"] * k)) if dz > 0 else None
            flaeche = self._tiefenflaeche(k, ziel_gross)
            flaeche.fill((0, 0, 0, 0))
            mitte = kamera.pos + kamera.versatz
            u_ecke = pygame.Vector2(round(mitte.x - flaeche.get_width() / 2),
                                    round(mitte.y - flaeche.get_height() / 2))
            self.ebene_zeichnen(flaeche, welt, idx, u_ecke, dunkel)
            self.wesen_zeichnen(flaeche, welt, idx, u_ecke, alpha, dunkel)
            self.partikel_zeichnen(flaeche, welt, idx, u_ecke, alpha)
            self.muendungsfeuer(flaeche, welt, u_ecke, idx)
            skaliert = pygame.transform.scale(flaeche, ziel_gross)
            if sicht < 0.999:
                skaliert.set_alpha(int(255 * sicht))
            ziel.blit(skaliert, (0, 0))
            if dz > 0:
                a = int(255 * p["dunst_staerke"] * (1.0 - k))
                if a > 0:
                    schleier = self._schleier(ziel_gross)
                    schleier.fill((*p["dunst"], min(255, a)))
                    ziel.blit(schleier, (0, 0))

        self.fliegende_zeichnen(ziel, welt, kamera, alpha, blick_hoehe)
        ziel.blit(self.vignette(ziel_gross), (0, 0))

    def tracer(self, ziel, welt, kamera, spieler) -> None:
        """Zielhilfe: eine duenne Linie von der Waffe zum Mauszeiger.

        Mit tracer_weit laeuft sie darueber hinaus weiter, bis etwas im Weg
        steht. Beides sind Schalter am Spieler, T und Z.
        """
        if not spieler.tracer or not spieler.lebt:
            return
        t = K.TRACER
        ecke = kamera.ecke
        muendung = spieler.pos + pygame.Vector2(14, 0).rotate(spieler.winkel)
        ende = pygame.Vector2(spieler.ziel)
        richtung = ende - muendung
        if richtung.length_squared() < 4:
            return
        if spieler.tracer_weit:
            ende = welt.strahl(muendung, richtung.normalize(), t["weite"],
                               spieler.ebene)
        a = muendung - ecke
        b = ende - ecke
        linie = self._linie
        linie.fill((0, 0, 0, 0))
        # Durchgehend rot. Frueher lag auf den ersten Prozenten ein heller
        # Kern; weil er am Anteil der Strecke hing, wuchs er mit, sobald man
        # die Linie mit Z verlaengert hat, und sah aus wie ein Fehler.
        pygame.draw.line(linie, (*t["farbe"], t["staerke"]), a, b, 1)
        ziel.blit(linie, (0, 0))
        pygame.draw.rect(ziel, t["punkt"], (int(b.x) - 1, int(b.y) - 1, 3, 3))

    def zielhilfen(self, ziel, welt, kamera, spieler) -> None:
        """Streukegel der Scharfschuetzenwaffe und der Nahkampfbogen."""
        if not spieler.lebt:
            return
        ecke = kamera.ecke
        d = spieler.waffe_daten
        p = spieler.pos - ecke

        if d.get("fokus_dauer"):
            halb = spieler.streuung_jetzt
            weite = min(d["reichweite"], 340.0)
            muendung = spieler.pos + pygame.Vector2(14, 0).rotate(spieler.winkel)
            a = muendung - ecke
            linie = self._linie
            linie.fill((0, 0, 0, 0))
            deck = int(40 + 90 * spieler.fokus)
            for vz in (-1, 1):
                b = a + pygame.Vector2(weite, 0).rotate(spieler.winkel + halb * vz)
                pygame.draw.line(linie, (*K.C_AMBER, deck), a, b, 1)
            if spieler.fokus > 0.55:      # ruhig genug fuer die Mittellinie
                b = a + pygame.Vector2(weite, 0).rotate(spieler.winkel)
                pygame.draw.line(linie, (*K.C_CREAM, int(60 + 120 * spieler.fokus)),
                                 a, b, 1)
            ziel.blit(linie, (0, 0))

        if spieler.schlag_zeigen > 0 and d.get("art") == "nahkampf":
            f = spieler.schlag_zeigen / 0.16
            reich = d["reichweite"] * (0.6 + 0.4 * (1.0 - f))
            halb = d["winkel"] * 0.5
            linie = self._linie
            linie.fill((0, 0, 0, 0))
            punkte = [p]
            schritte = 9
            for i in range(schritte + 1):
                g = spieler.winkel - halb + (2 * halb) * i / schritte
                punkte.append(p + pygame.Vector2(reich, 0).rotate(g))
            pygame.draw.polygon(linie, (*K.C_CREAM, int(70 * f)), punkte)
            ziel.blit(linie, (0, 0))

    # ---- HUD -------------------------------------------------------
    def hud(self, ziel, welt, spieler, wellen_text, punkte, blick=None) -> None:
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
        if blick is None:
            blick = spieler.ebene
        for i in range(len(welt.ebenen) - 1, -1, -1):
            ey = 16 + (len(welt.ebenen) - 1 - i) * 14
            angeschaut = (i == blick)
            r = pygame.Rect(ex, ey, 18, 11)
            pygame.draw.rect(ziel, K.C_AMBER if angeschaut else (18, 12, 9), r)
            pygame.draw.rect(ziel, K.C_AMBER if angeschaut else K.C_MUTED_DK, r, 1)
            f.zeichnen(ziel, "E%d" % i, r.centerx, ey + 2,
                       (18, 12, 8) if angeschaut else K.C_MUTED, 1, ausrichtung="mitte")
            if i == spieler.ebene:          # wo die Figur wirklich steht
                pygame.draw.rect(ziel, K.C_TEAL, (ex - 5, ey + 3, 3, 5))

        # Hotbar unten in der Mitte
        n = len(spieler.waffen)
        bw, bh, luecke = 34, 18, 3
        gesamt = n * bw + (n - 1) * luecke
        hx = (K.GAME_W - gesamt) // 2
        hy = K.GAME_H - 22
        for i, name in enumerate(spieler.waffen):
            r = pygame.Rect(hx + i * (bw + luecke), hy, bw, bh)
            aktiv = (i == spieler.waffe)
            pygame.draw.rect(ziel, (10, 7, 5), r)
            pygame.draw.rect(ziel, K.C_AMBER if aktiv else K.C_MUTED_DK, r, 1)
            wd = K.WAFFEN[name]
            # Symbol statt abgeschnittenem Namen: auf 34 Pixel Breite passen
            # nur vier Buchstaben, und "SCHA" sagt niemandem etwas.
            sym = self.bilder.bild("waffe_" + name)
            ziel.blit(sym, (r.centerx - sym.get_width() // 2,
                            r.centery - sym.get_height() // 2))
            f.zeichnen(ziel, "%d" % (i + 1), r.x + 2, r.y + 2,
                       K.C_AMBER if aktiv else K.C_MUTED_DK, 1)
            f.zeichnen(ziel, "%d" % spieler.magazin[name] if wd.get("magazin")
                       else "--", r.right - 2, r.bottom - 9,
                       K.C_AMBER if aktiv else K.C_MUTED_DK, 1,
                       ausrichtung="rechts")

        # Medkits links neben der Hotbar
        mx = hx - 40
        f.zeichnen(ziel, "[H]", mx, hy + 1, K.C_MUTED_DK, 1)
        for i in range(K.MEDKIT["hoechstens"]):
            r = pygame.Rect(mx + i * 9, hy + 9, 7, 7)
            pygame.draw.rect(ziel, K.C_TEAL if i < spieler.medkits else (24, 18, 13), r)
            pygame.draw.rect(ziel, K.C_TEAL_DK, r, 1)
        if spieler.heilt_rest > 0:
            anteil = 1.0 - spieler.heilt_rest / K.MEDKIT["dauer"]
            pygame.draw.rect(ziel, K.C_TEAL, (mx, hy - 4, int(30 * anteil), 2))

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


# ══════════════════════════════════════════════════════════════════
# Der Wandler
# ══════════════════════════════════════════════════════════════════
#
# Von aussen ist ein Wandler zweierlei: ein Rumpf, der sich dreht, und
# Beine, die sich bewegen. Beides wird aus Bildern gebaut, die sich
# austauschen lassen - der Rumpf aus seinen eigenen Deckkacheln, die Beine
# aus vier Gliedbildern.
#
# Der Rumpf dreht sich, das Kachelraster darf das aber nie. Beides zugleich
# geht, weil der Umriss **einmal** in ein Bild gezeichnet und danach nur
# noch gedreht wird: die Kacheln bleiben in ihrem eigenen Raster, und was
# sich dreht, ist eine fertige Flaeche. Wer an Bord laeuft, sieht wieder
# das ungedrehte Raster - dort ist der Rumpf der ruhende Bezugsrahmen.

def _erweitern(cls):
    """Haengt die folgenden Methoden an den Renderer.

    Getrennt geschrieben, damit der Wandler nicht mitten in die bestehende
    Zeichenschleife einbricht: was oben steht, hat sich bewaehrt und bleibt
    unangetastet.
    """
    def deko(fn):
        setattr(cls, fn.__name__, fn)
        return fn
    return deko


@_erweitern(Renderer)
def glied(self, name: str, laenge: float, dicke: float,
          winkel: float) -> pygame.Surface:
    """Ein Beinglied auf Mass und im richtigen Winkel.

    Das Bild in `BILD_MASS` ist ein Grundmass; eine Bauklasse mit anderen
    Beinlaengen bekommt es hart umgerechnet, Pixel fuer Pixel, ohne
    Weichzeichnen. Deshalb bleibt es auch beim Imperator scharf.
    """
    lang = max(1, int(round(laenge)))
    dick = max(1, int(round(dicke)))
    key = (name, lang, dick)
    basis = self._glieder.get(key)
    if basis is None:
        roh = self.bilder.bild(name)
        basis = (roh if roh.get_size() == (lang, dick)
                 else pygame.transform.scale(roh, (lang, dick)))
        self._glieder[key] = basis
    stufe = int(round(winkel / self.bilder.DREH_SCHRITT)) * self.bilder.DREH_SCHRITT
    stufe %= 360
    dkey = (name, lang, dick, stufe)
    fertig = self._gedrehte.get(dkey)
    if fertig is None:
        fertig = pygame.transform.rotate(basis, -stufe)
        self._gedrehte[dkey] = fertig
    return fertig


@_erweitern(Renderer)
def _strecke(self, ziel, name, von, nach, dicke, ecke, tonung=None) -> None:
    """Zeichnet ein Glied von einem Punkt zum anderen."""
    d = nach - von
    laenge = d.length()
    if laenge < 1.0:
        return
    winkel = math.degrees(math.atan2(d.y, d.x))
    s = self.glied(name, laenge, dicke, winkel)
    if tonung is not None:
        s = s.copy()
        s.fill(tonung, special_flags=pygame.BLEND_RGB_ADD)
    mitte = (von + nach) * 0.5 - ecke
    ziel.blit(s, (mitte.x - s.get_width() / 2, mitte.y - s.get_height() / 2))


@_erweitern(Renderer)
def _punktbild(self, ziel, name, punkt, mass, winkel, ecke, tonung=None) -> None:
    lang = max(1, int(round(mass)))
    s = self.glied(name, lang, lang, winkel)
    if tonung is not None:
        s = s.copy()
        s.fill(tonung, special_flags=pygame.BLEND_RGB_ADD)
    p = punkt - ecke
    ziel.blit(s, (p.x - s.get_width() / 2, p.y - s.get_height() / 2))


@_erweitern(Renderer)
def beine_zeichnen(self, ziel, wandler, ecke, schatten=True) -> None:
    """Alle Beine einer Maschine.

    Zwei Durchgaenge, und die Reihenfolge ist der Grund, warum man einen
    angehobenen Fuss ueberhaupt als angehoben sieht:

    1. **Schatten**, alle auf Bodenhoehe, ohne Hub. Sie bleiben unten.
    2. **Glieder**, mit Hub nach oben versetzt und im Schwung eine Spur
       heller und groesser.

    Erst die Luecke zwischen Schatten und Bein liest sich als Hoehe. Ohne
    den Schatten schiebt sich ein Bein bloss nach oben, und niemand sieht,
    dass es abhebt.
    """
    m = wandler.plan.bein_masse
    mitte, kurs = wandler.pos, wandler.kurs

    if schatten:
        versatz = pygame.Vector2(K.BEIN["schatten_versatz"],
                                 K.BEIN["schatten_versatz"])
        schicht = pygame.Surface(ziel.get_size(), pygame.SRCALPHA)
        for b in wandler.beine:
            h = b.huefte_welt(mitte, kurs) + versatz
            f = pygame.Vector2(b.fuss) + versatz          # ohne Hub: am Boden
            k = knie_punkt(h, f, b.ober, b.unter, b.seite)
            self._strecke(schicht, "bein_ober", h, k, m["dicke_ober"], ecke)
            self._strecke(schicht, "bein_unter", k, f, m["dicke_unter"], ecke)
            self._punktbild(schicht, "bein_fuss", f, m["fuss"], kurs, ecke)
        schicht.fill((0, 0, 0, int(255 * K.BEIN["schatten"])),
                     special_flags=pygame.BLEND_RGBA_MULT)
        ziel.blit(schicht, (0, 0))

    for b in wandler.beine:
        h, k, f = b.glieder(mitte, kurs)
        if not b.heil:
            ton = None
            self._strecke(ziel, "bein_ober", h, k, m["dicke_ober"] * 0.9, ecke)
            continue
        hell = int(b.hub * K.BEIN["hub_hell"] / max(1.0, self._hub_bezug(wandler)))
        ton = (hell, hell, hell) if hell > 1 else None
        wuchs = 1.0 + b.hub * K.BEIN["hub_massstab"]
        self._strecke(ziel, "bein_ober", h, k, m["dicke_ober"] * wuchs, ecke, ton)
        self._strecke(ziel, "bein_unter", k, f, m["dicke_unter"] * wuchs, ecke, ton)
        self._punktbild(ziel, "bein_fuss", f, m["fuss"] * wuchs,
                        kurs, ecke, ton)


@_erweitern(Renderer)
def _hub_bezug(self, wandler) -> float:
    return max(1.0, wandler.gangwerk.reichweite * K.GANG["hub_voll_anteil"])


@_erweitern(Renderer)
def rumpf_umriss(self, wandler) -> pygame.Surface:
    """Der Rumpf **von aussen**: ein gestufter Panzeraufbau, kein Grundriss.

    Der erste Anlauf zeichnete hier einfach das oberste Deck. Das war
    sichtbar falsch: von aussen sieht man nicht den Fussboden der Bruecke,
    sondern das Blech darueber, und eine Maschine sah dadurch aus wie ein
    aufgeklappter Bauplan.

    Gebaut wird stattdessen aus dem, was ohnehin dasteht - **jedes Deck
    einzeln, von unten nach oben**:

    1. Das unterste Deck ist das groesste und dunkelste. Darueber legt sich
       jedes weitere, kleiner und eine Spur heller.
    2. Jedes bekommt ringsum eine Lichtkante. Erst die Staffelung dieser
       Kanten macht aus einer Flaeche einen Aufbau - man sieht der Maschine
       an, dass sie Etagen hat, ohne eine davon zu betreten.
    3. Der Bug wird heller abgesetzt und bekommt Warnwinkel. Ohne das sieht
       man einem Umriss nicht an, wohin er laeuft, und das ist die
       wichtigste Auskunft, die eine Laufmaschine geben muss.
    4. Aufbauten kommen an die Marken des obersten Decks: Geschuetze, wo
       `G` steht, die Kanzel, wo `T` steht. Wer die Karte aendert, aendert
       damit auch das Aussehen von aussen - ohne eine Zeile Code.

    Wird einmal gebaut und behalten. Der Rumpf aendert sich nicht, waehrend
    er laeuft; was sich aendert, ist allein der Winkel.
    """
    key = (id(wandler), "aussen")
    fertig = self._umrisse.get(key)
    if fertig is not None:
        return fertig

    kb = K.WANDLER_BILD
    ebenen = wandler.welt.ebenen
    breite = max(e.breite for e in ebenen)
    hoehe = max(e.hoehe for e in ebenen)
    s = pygame.Surface((breite * K.TILE, hoehe * K.TILE), pygame.SRCALPHA)
    bild = self.bilder.bild

    def belegung(e):
        """Belegte Kacheln und der Bereich, den sie einnehmen."""
        b = [[e.kachel(tx, ty) != K.LEER for tx in range(e.breite)]
             for ty in range(e.hoehe)]
        punkte = [(tx, ty) for ty in range(e.hoehe) for tx in range(e.breite)
                  if b[ty][tx]]
        if not punkte:
            return b, None
        xs = [x for x, _ in punkte]
        ys = [y for _, y in punkte]
        return b, (min(xs), min(ys), max(xs), max(ys))

    # Ausgerichtet wird an dem, was wirklich belegt ist, nicht an der
    # Arraygroesse. Beim Schreiben einer Karte fallen Leerzeichen am
    # Zeilenende weg - ein Deck mit mehr Loechern rechts kaeme sonst
    # schmaler heraus und der ganze Aufbau saesse schief.
    _, grund_feld = belegung(ebenen[0])
    grund_mitte = (((grund_feld[0] + grund_feld[2]) / 2.0,
                    (grund_feld[1] + grund_feld[3]) / 2.0)
                   if grund_feld else (breite / 2.0, hoehe / 2.0))

    for idx, e in enumerate(ebenen):
        belegt, feld = belegung(e)
        if feld is None:
            continue
        ox = int(round(grund_mitte[0] - (feld[0] + feld[2]) / 2.0))
        oy = int(round(grund_mitte[1] - (feld[1] + feld[3]) / 2.0))
        hell = min(255, kb["panzer_dunkel"] + idx * kb["stufe_hell"])
        bug = max(tx for ty in range(e.hoehe) for tx in range(e.breite)
                  if belegt[ty][tx])

        for ty in range(e.hoehe):
            for tx in range(e.breite):
                if not belegt[ty][tx]:
                    continue
                name = self._deck_namen[((tx * 73856093) ^ (ty * 19349663)) % 4]
                s.blit(self.dunkel(bild(name), hell),
                       ((tx + ox) * K.TILE, (ty + oy) * K.TILE))

        # Plattenstoesse nur auf dem untersten Deck: darueber wuerden sie
        # mit den Stufenkanten um Aufmerksamkeit streiten.
        if idx == 0:
            for tx in range(0, e.breite, kb["plattenstoss"]):
                x = (tx + ox) * K.TILE
                pygame.draw.line(s, (26, 24, 20), (x, 0), (x, hoehe * K.TILE))
            for ty in range(0, e.hoehe, kb["plattenstoss"]):
                y = (ty + oy) * K.TILE
                pygame.draw.line(s, (26, 24, 20), (0, y), (breite * K.TILE, y))

        for ty in range(e.hoehe):
            for tx in range(e.breite):
                if not belegt[ty][tx]:
                    continue
                x, y = (tx + ox) * K.TILE, (ty + oy) * K.TILE
                vorn = tx >= bug - kb["bug_tiefe"] + 1
                kante = (126, 118, 102) if vorn else (88, 82, 71)
                if ty == 0 or not belegt[ty - 1][tx]:
                    pygame.draw.rect(s, kante, (x, y, K.TILE, 2))
                    pygame.draw.rect(s, (22, 20, 17), (x, y + 2, K.TILE, 1))
                if ty == e.hoehe - 1 or not belegt[ty + 1][tx]:
                    pygame.draw.rect(s, (28, 25, 21), (x, y + K.TILE - 3, K.TILE, 3))
                    pygame.draw.rect(s, (62, 58, 50), (x, y + K.TILE - 3, K.TILE, 1))
                if tx == 0 or not belegt[ty][tx - 1]:
                    pygame.draw.rect(s, (36, 33, 28), (x, y, 3, K.TILE))
                    pygame.draw.rect(s, (72, 67, 58), (x, y, 1, K.TILE))
                if tx == e.breite - 1 or not belegt[ty][tx + 1]:
                    pygame.draw.rect(s, kante, (x + K.TILE - 3, y, 3, K.TILE))
                    pygame.draw.rect(s, (22, 20, 17), (x + K.TILE - 4, y, 1, K.TILE))

    # Warnwinkel am Bug, zuletzt und ueber allen Decks - sonst deckt ihn der
    # Aufbau zu, und die Maschine verliert ihre Richtung.
    oben = ebenen[-1]
    _, feld_o = belegung(oben)
    if feld_o is None:
        feld_o = (0, 0, oben.breite - 1, oben.hoehe - 1)
    ox_o = int(round(grund_mitte[0] - (feld_o[0] + feld_o[2]) / 2.0))
    oy_o = int(round(grund_mitte[1] - (feld_o[1] + feld_o[3]) / 2.0))
    bug_o = feld_o[2]
    mitte_y = (oy_o + oben.hoehe / 2) * K.TILE
    spitze = (bug_o + ox_o + 1) * K.TILE
    winkel = pygame.Surface((breite * K.TILE, hoehe * K.TILE), pygame.SRCALPHA)
    for i in range(kb["winkel"]):
        weit = K.TILE * (1.0 + i * 0.8)
        pygame.draw.lines(winkel, K.C_WARN, False,
                          [(spitze - weit, mitte_y - weit * 0.66),
                           (spitze - weit + K.TILE * 0.66, mitte_y),
                           (spitze - weit, mitte_y + weit * 0.66)], 3)
    winkel.set_alpha(kb["winkel_deckkraft"])
    s.blit(winkel, (0, 0))

    # Aufbauten an den Marken des obersten Decks.
    ox, oy = ox_o, oy_o
    for ty in range(oben.hoehe):
        for tx in range(oben.breite):
            st = oben.daten(tx, ty).get("station")
            x, y = (tx + ox) * K.TILE, (ty + oy) * K.TILE
            if st == "geschuetz":
                s.blit(bild("st_geschuetz"), (x, y))
                pygame.draw.circle(s, (20, 18, 15),
                                   (x + K.TILE // 2, y + K.TILE // 2), 8, 2)
            elif st == "steuerstand":
                kanzel = pygame.Rect(x + 3, y + 3, K.TILE - 6, K.TILE - 6)
                pygame.draw.rect(s, (20, 27, 29), kanzel)
                pygame.draw.rect(s, K.C_STAHL_DUNKEL, kanzel, 2)
                pygame.draw.line(s, K.C_TEAL_DK, (kanzel.left + 2, kanzel.top + 3),
                                 (kanzel.right - 3, kanzel.top + 3))
                pygame.draw.line(s, K.C_TEAL, (kanzel.left + 3, kanzel.top + 2),
                                 (kanzel.left + 9, kanzel.top + 2))

    self._umrisse[key] = s
    return s


@_erweitern(Renderer)
def rumpf_zeichnen(self, ziel, wandler, ecke) -> None:
    """Der Rumpf von aussen: das Panzerdach, gedreht, mit Schlagschatten."""
    bild = self.rumpf_umriss(wandler)
    stufe = int(round(wandler.kurs / self.bilder.DREH_SCHRITT))
    stufe = stufe * self.bilder.DREH_SCHRITT % 360
    key = ("rumpf", id(wandler), stufe)
    gedreht = self._gedrehte.get(key)
    if gedreht is None:
        gedreht = pygame.transform.rotate(bild, -stufe)
        self._gedrehte[key] = gedreht

    mitte = wandler.pos - ecke
    mitte.y -= wandler.gangwerk.atem            # das Heben und Senken im Gang
    b, h = gedreht.get_size()
    schatten = pygame.Surface((b, h), pygame.SRCALPHA)
    schatten.blit(gedreht, (0, 0))
    schatten.fill((0, 0, 0, 150), special_flags=pygame.BLEND_RGBA_MULT)
    v = K.DEKAL["wand_versatz"]
    ziel.blit(schatten, (mitte.x - b / 2 + v, mitte.y - h / 2 + v))
    ziel.blit(gedreht, (mitte.x - b / 2, mitte.y - h / 2))


@_erweitern(Renderer)
def wandler_zeichnen(self, ziel, wandler, kamera) -> None:
    """Die ganze Maschine von aussen, in der richtigen Reihenfolge:
    Beinschatten, Beine, Rumpf. Die Beine liegen unter dem Rumpf, weil sie
    unter ihm haengen - wer sie darueber zeichnet, bekommt eine Maschine,
    die auf Stelzen sitzt."""
    ecke = kamera.ecke
    self.beine_zeichnen(ziel, wandler, ecke)
    self.rumpf_zeichnen(ziel, wandler, ecke)
