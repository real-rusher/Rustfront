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
            self.fliegendes(ziel, welt, kamera, blick_hoehe,
                            w.zeichenpos(alpha), w.winkel, w.ebene, w.flug,
                            w.bild, w.blitz > 0)

    def fliegendes(self, ziel, welt, kamera, blick_hoehe, pos, winkel,
                   ebene: int, flug: float, bild: str,
                   blitzt: bool = False) -> None:
        """Ein einzelnes Ding in der Luft, mit dem Massstab seiner Hoehe.

        Eigene Methode, weil nicht nur eigene Wesen fallen: beim Gast im
        Gefecht kommen fallende Granaten als blosse Zahlen aus dem Netz und
        muessen mit derselben Rechnung ins Bild, sonst haengen sie in der
        Luft, wo die Figur daneben schon faellt.
        """
        p = K.PERSPEKTIVE
        dz = blick_hoehe - (welt.hoehe(ebene) + flug)
        if dz < -p["ausblenden"]:
            return                            # zu weit ueber der Ansicht
        k = p["brennweite"] / max(60.0, p["brennweite"] + dz)
        s = self.bilder.gedreht(bild, winkel)
        if abs(k - 1.0) > p["massstab_schwelle"]:
            s = pygame.transform.scale(
                s, (max(1, int(round(s.get_width() * k))),
                    max(1, int(round(s.get_height() * k)))))
        if blitzt:
            s = s.copy()
            s.fill((210, 210, 210), special_flags=pygame.BLEND_RGB_ADD)
        b = self._bildpunkt(pos, kamera, k)
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

    def _tiefenflaeche(self, k: float) -> pygame.Surface:
        """Hilfsflaeche fuer eine tiefer liegende Ebene.

        Sie zeigt einen groesseren Weltausschnitt und wird danach auf die
        Bildgroesse verkleinert. Genau das laesst die untere Ebene weiter weg
        wirken: gleiche Weltmitte, kleinerer Massstab.
        """
        schluessel = int(k * 100)
        hit = self._tiefen.get(schluessel)
        if hit is None:
            w = int(K.GAME_W / k) + 2
            h = int(K.GAME_H / k) + 2
            hit = pygame.Surface((w, h), pygame.SRCALPHA)
            if len(self._tiefen) > 64:
                self._tiefen.clear()
            self._tiefen[schluessel] = hit
        return hit

    def welt_zeichnen(self, ziel, welt, kamera, alpha, blick_hoehe=None,
                      boden=None) -> None:
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

        boden ist ein Aufruf (flaeche, ebene, ecke) direkt nach dem Boden
        und vor den Wesen. Damit zeichnet der Mehrspieler seinen Kreis in
        die Karte, statt darueber: er bekommt Verkleinerung, Abdunklung und
        Dunst der jeweiligen Ebene geschenkt, und die Figuren stehen
        sichtbar darauf.
        """
        ecke = kamera.ecke
        held = welt.held
        p = K.PERSPEKTIVE
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
                if boden is not None:
                    boden(ziel, idx, ecke)
                self.wesen_zeichnen(ziel, welt, idx, ecke, alpha)
                self.partikel_zeichnen(ziel, welt, idx, ecke, alpha)
                self.muendungsfeuer(ziel, welt, ecke, idx)
                self.rauch_zeichnen(ziel, welt, idx, ecke)
                continue

            dunkel = max(48, int(p["dunkel"] * k)) if dz > 0 else None
            flaeche = self._tiefenflaeche(k)
            flaeche.fill((0, 0, 0, 0))
            mitte = kamera.pos + kamera.versatz
            u_ecke = pygame.Vector2(round(mitte.x - flaeche.get_width() / 2),
                                    round(mitte.y - flaeche.get_height() / 2))
            self.ebene_zeichnen(flaeche, welt, idx, u_ecke, dunkel)
            if boden is not None:
                boden(flaeche, idx, u_ecke)
            self.wesen_zeichnen(flaeche, welt, idx, u_ecke, alpha, dunkel)
            self.partikel_zeichnen(flaeche, welt, idx, u_ecke, alpha)
            self.muendungsfeuer(flaeche, welt, u_ecke, idx)
            self.rauch_zeichnen(flaeche, welt, idx, u_ecke)
            skaliert = pygame.transform.scale(flaeche, (K.GAME_W, K.GAME_H))
            if sicht < 0.999:
                skaliert.set_alpha(int(255 * sicht))
            ziel.blit(skaliert, (0, 0))
            if dz > 0:
                a = int(255 * p["dunst_staerke"] * (1.0 - k))
                if a > 0:
                    self._dunst.fill((*p["dunst"], min(255, a)))
                    ziel.blit(self._dunst, (0, 0))

        self.fliegende_zeichnen(ziel, welt, kamera, alpha, blick_hoehe)
        ziel.blit(self._vignette, (0, 0))

    def rauch_zeichnen(self, ziel, welt, index: int, ecke) -> None:
        """Rauchwolken der Ebene, ueber allem, was auf ihr steht.

        Bewusst nach den Figuren und nach den Partikeln: Rauch nimmt die
        Sicht, er liegt nicht am Boden. Weil er in die Ebene selbst
        gezeichnet wird, verdeckt er auch dann, wenn man von weiter oben
        auf diese Ebene hinuntersieht - genau das ist der Sinn.

        Gezeichnet aus mehreren Ballen statt als eine Scheibe: ein Kreis
        sieht nach Zielscheibe aus, mehrere ineinander nach Rauch. Sie
        wallen langsam, damit die Wand lebt.
        """
        if not welt.rauch:
            return
        r = K.RAUCH
        for wolke_ in welt.rauch:
            if wolke_.ebene != index or not wolke_.lebt:
                continue
            dichte = wolke_.dichte
            if dichte <= 0.01:
                continue
            m = wolke_.pos - ecke
            gross = wolke_.radius * (0.55 + 0.45 * dichte)
            flaeche = pygame.Surface((int(gross * 2.4), int(gross * 2.4)),
                                     pygame.SRCALPHA)
            mitte = flaeche.get_width() / 2
            deckung = int(r["deckkraft"] * dichte)
            for i in range(r["flocken"]):
                a = math.tau * i / r["flocken"] + wolke_.alter * r["wallen_takt"]
                weg = gross * r["flocken_streuung"] * (0.45 + 0.55 * ((i * 7) % 5) / 4)
                wall = r["wallen"] * math.sin(wolke_.alter * 1.7 + i)
                p = (mitte + math.cos(a) * weg,
                     mitte + math.sin(a) * weg + wall * 0.3)
                pygame.draw.circle(flaeche, (*r["farbe"], deckung), p,
                                   gross * 0.62)
            pygame.draw.circle(flaeche, (*r["farbe"], deckung), (mitte, mitte),
                               gross * 0.7)
            ziel.blit(flaeche, (m.x - mitte, m.y - mitte))

    def kreis_zone(self, ziel, mitte, radius: float, farbe, anteil: float = 0.0,
                   puls: float = 0.0, ring: int = 3, fuellung: int = 34) -> None:
        """Der Kreis in der Kartenmitte, wie ihn der Mehrspieler braucht.

        Absichtlich ohne Kamera und ohne Ebene: der Aufrufer uebergibt den
        Mittelpunkt bereits in der Flaeche, in die gezeichnet wird. So
        stimmt der Kreis auch auf den verkleinerten Tiefenflaechen, ohne
        dass hier irgendetwas von Perspektive wissen muesste.

        anteil zeichnet den Ladestand als Bogen, oben beginnend und im
        Uhrzeigersinn - das liest man schneller als eine Zahl.
        """
        r = int(round(radius))
        if r < 2:
            return
        m = pygame.Vector2(mitte)
        rand = max(ring + 2, 4)
        flaeche = pygame.Surface((2 * (r + rand), 2 * (r + rand)),
                                 pygame.SRCALPHA)
        mp = (r + rand, r + rand)
        pygame.draw.circle(flaeche, (*farbe, fuellung), mp, r)
        # Der Ring pulst leicht. Ein ruhiger Kreis verschwindet im Boden,
        # ein pulsender sagt: hier geht es um etwas.
        schlag = 0.5 + 0.5 * math.sin(puls * math.tau)
        pygame.draw.circle(flaeche, (*farbe, int(120 + 90 * schlag)), mp, r,
                           max(1, ring))
        if anteil > 0.001:
            kasten = pygame.Rect(rand, rand, 2 * r, 2 * r)
            bogen = math.tau * max(0.0, min(1.0, anteil))
            pygame.draw.arc(flaeche, (*farbe, 255), kasten,
                            math.pi / 2 - bogen, math.pi / 2,
                            max(2, ring + 1))
        ziel.blit(flaeche, (m.x - r - rand, m.y - r - rand))

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
    def hud(self, ziel, welt, spieler, wellen_text, punkte, blick=None,
            kopf: bool = True) -> None:
        """kopf=False laesst die Kopfzeile weg. Im Gefecht gibt es weder
        Wellen noch Schrott, und "SCHROTT 3" fuer drei Abschuesse waere
        schlicht gelogen."""
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
        if kopf:
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
