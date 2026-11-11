"""
DUSTFRONT - Der Buggy (seit 0.34.9)
===================================

Ein kleiner Wuestenbuggy, der dort steht, wo die Karte ein F hat. Man
steigt mit E ein und wieder aus; gelenkt wird wie ein Auto, nicht wie die
Figur: W gibt Gas, S bremst und faehrt dann rueckwaerts, A und D lenken -
und gelenkt wird nur, solange er rollt. Shift ist die Handbremse.

**Fahren (seit 0.34.16).** Gemeldet: "natuerlicher, Driften soll sich
realistisch anfuehlen". Vorher drehte er mit festen Grad je Sekunde, und
was seitlich rutschte, klang einfach ab - ein Wagen auf Schienen mit einem
Hauch Wischen. Jetzt ein Einspurmodell, wie es Rennspiele benutzen: eine
Vorder- und eine Hinterachse, jede mit einem Reifen, der seitlich mit dem
Schraeglauf mehr Kraft aufbaut - bis zu seiner Grenze. Darueber rutscht
er und haelt weniger (`gleiten`). Hinten haelt er weniger als vorn, Gas
kostet hinten Seitengriff (Heckantrieb), die Handbremse noch mehr. Daraus
folgt das Driften von selbst: in der schnellen Kurve kommt das Heck, mit
der Handbremse kommt es sofort.

Zwei Hilfen, ohne die es sich mit Tasten nicht fahren liesse: er lenkt
einen Teil des Driftwinkels selbst gegen (`gegenlenken`), und ab einem
Driftwinkel dreht ihn eine Stuetze zurueck, statt ihn sich drehen zu
lassen. Eine Tastatur kennt nur voll oder nichts; ein Fahrer mit Lenkrad
wuerde genau das mit den Haenden tun.

Wo er rutscht, bleiben Reifenspuren im Sand, Staub fliegt, und die Reifen
quietschen - beim Gast genauso, aus dem gemeldeten `rutschen`.

**Zerstoerbar (seit 0.34.18).** Bis dahin war er unzerstoerbar und kein
Ziel. Gemeldet: "autos sollen kaputt gehen koennen und dann respawnen random
auf der map". Jetzt ist der Wagen selbst das Ziel (`trefferbar`): Kugeln,
Splitter, Feuer und Schlaege treffen ihn - und damit auch Deckung, wenn er
leer dasteht. Wer am Steuer sitzt, ist solange selbst kein Ziel; der Wagen
reicht jeden Treffer an ihn weiter, und dort kommt wie bisher nur ein Teil
an (K.FAHRZEUG["schaden_anteil"], mehrspieler.Kaempfer.schaden). Bei null
Leben geht er hoch: Explosion, Schaden im Umkreis, der Fahrer fliegt heraus
und bekommt etwas ab. Das Wrack brennt eine Weile (`wrack_zeit`), dann ist
es weg, und etwas spaeter steht irgendwo auf der Karte ein neuer Wagen -
das Gefecht sucht den Platz (Gefecht._fahrzeuge_erneuern).

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
import struct

import pygame

from . import config as K
from .core import Bilder, naehern
from .entities import (RND, Geschoss, Nagelfeld, Partikel, Rauchwolke, Wesen, abschuss_buchen,
                       schaden_an, tod_blut, wolke)


_SPURPUNKTE: dict = {}


def _spurpunkt(deck: int) -> pygame.Surface:
    """Ein Punkt Reifenspur: dunkel, halb durchsichtig, 3 x 3 Pixel. Je
    Deckkraft einmal gebaut - es sind viele, und alle gleich."""
    deck = max(0, min(255, deck // 10 * 10))
    s = _SPURPUNKTE.get(deck)
    if s is None:
        s = pygame.Surface((3, 3), pygame.SRCALPHA)
        s.fill((52, 40, 28, deck))
        s.set_at((0, 0), (0, 0, 0, 0))
        s.set_at((2, 2), (0, 0, 0, 0))
        _SPURPUNKTE[deck] = s
    return s


class Buggy(Wesen):
    fraktion = "neutral"
    # Welche Art (seit 0.34.59): geht so ans Netz und an die Karte. Und
    # die Werte, nach denen gefahren wird - der Panzerwagen faehrt mit
    # demselben Einspurmodell, nur mit einem zweiten Satz (K.PANZERWAGEN).
    art = "buggy"
    werte = K.FAHRZEUG
    # Seit 0.34.18 ein Ziel (siehe oben).
    trefferbar = True
    # Treffer am Blech zaehlen nicht als Treffer in der Statistik (die
    # zaehlt, wie oft man Spieler und Gegner trifft), und es spritzen
    # Funken statt Blut.
    zaehlt_treffer = False
    treffer_art = "metall"
    # Die weiche Abstossung der Welt kennt nur Kreise. Wer im Weg steht,
    # schiebt der Buggy selbst beiseite (_beiseite_schieben).
    schiebt = False
    # Statt des runden Schattens der Figuren ein eigener, laenglicher
    # (Renderer.wesen_zeichnen fragt nach `schatten_bild`).
    schatten = False
    schatten_bild = "buggy_schatten"
    faellt = False
    hoehe_3d = K.FIGUREN_3D["buggy"]
    # C4 bleibt an ihm kleben und faehrt mit (seit 0.34.11, siehe
    # entities.C4Ladung). Er selbst nimmt keinen Schaden davon, wer drin
    # sitzt, schon.
    c4_haftet = True
    _passt_merk = None        # siehe passt: nur innerhalb von schritt
    # Seit 0.34.65: ein Fahrzeug fragt bei jedem Treffer nach der Art
    # (K.PANZERUNG, entities.schaden_an).
    ist_fahrzeug = True
    # Wie er hochgeht: der Buggy wie eine Granate, Panzer und Panzerwagen
    # mit dem Feuerball der Kanone (Welt.explosion, seit 0.34.59).
    explosion_art = "spreng"

    def __init__(self, pos, ebene: int = 0, winkel: float = 0.0,
                 nur_bild: bool = False) -> None:
        self.max_leben = self.werte["leben"]
        super().__init__(pos, ebene)
        f = self.werte
        self.radius = f.get("kreis", self.radius)
        self.winkel = float(winkel)
        self.fahrer = None            # der Kaempfer am Steuer, beim Gastgeber
        self.gas = 0.0                # -1 bis 1, aus W und S
        self.lenk = 0.0               # -1 bis 1, aus A und D
        self.handbremse = False       # Shift
        self.geschw = pygame.Vector2(0, 0)
        self.gier = 0.0               # Drehung um sich selbst, Radiant je Sekunde
        self.lenkwinkel = 0.0         # Radeinschlag jetzt, Radiant (+ = rechts)
        # 0 bis 1: wie sehr er gerade rutscht. Treibt Spuren, Staub und
        # Quietschen, und geht so an den Gast.
        self.rutschen = 0.0
        self._spur_letzte: dict = {}
        self._quietsch_rest = 0.0
        # Wo er zu Beginn stand. Zu jeder neuen Runde kommt er dorthin
        # zurueck, sonst steht nach drei Runden jeder Buggy irgendwo.
        self.start = (pygame.Vector2(pos), int(ebene), float(winkel))
        self.nur_bild = nur_bild
        # Beim Gast: ob jemand drinsitzt und aus welcher Mannschaft. Beim
        # Gastgeber folgt beides aus `fahrer`.
        self.besetzt = False
        self.team = -1
        # Und in welchem Aussehen (seit 0.34.60, art_figuren). Leer: die
        # alte Figur in den Farben der Mannschaft.
        self.skin = ""
        # Seit 0.34.65: wie lange ein EMP ihn noch stilllegt, wie lange die
        # Reifen noch platt sind, was er hinten heraus werfen kann, und
        # was ihn zuletzt traf (fuer die INFO-Ansicht des Testmodus).
        self.emp_rest = 0.0
        self.platt_rest = 0.0
        self._emp_funken = 0.0
        self.hilfe = {}
        self.hilfe_takt = {}
        self.hilfe_auffuellen()
        self.letzter_treffer = None
        self._staub_rest = 0.0
        # Kaputt (seit 0.34.18): ein Wrack, das noch `wrack_rest` brennt.
        # `kaputt_von` hat ihn erledigt - der bekommt auch den Fahrer.
        # `anteil` ist beim Gast das gemeldete Leben (0 bis 1).
        self.kaputt = False
        self.kaputt_von = None
        self.wrack_rest = 0.0
        self.anteil = 1.0
        self._rauch_rest = 0.0

    # ---- Bild ---------------------------------------------------------
    @property
    def bild(self) -> str:
        if self.kaputt:
            return "buggy_wrack"
        return self._insassen_bild("buggy")

    def _insassen_bild(self, grund: str) -> str:
        """Das Bild mit dem, der drinsitzt: leer, im Skin des Fahrers
        (`grund`_skin_<id>[_<team>], seit 0.34.60), sonst in den Farben
        seiner Mannschaft. Beim Gastgeber vom Fahrer, beim Gast gemeldet."""
        if self.fahrer is not None:
            besetzt = True
            team = getattr(self.fahrer, "team", -1)
            skin = getattr(self.fahrer, "skin", "")
        else:
            besetzt, team, skin = self.besetzt, self.team, self.skin
        if not besetzt:
            return grund
        kurz = (K.TEAMS["kombi"][team]["name"].lower()
                if 0 <= team < len(K.TEAMS["kombi"]) else "")
        if skin:
            name = "%s_skin_%s%s" % (grund, skin, "_" + kurz if kurz else "")
            # Nur wenn es das Muster gibt (art_figuren ist geladen) -
            # ohne Zeichnung bliebe sonst ein rotes Fehlbild stehen.
            if Bilder.mass(name):
                return name
        if kurz:
            name = "%s_%s_fahrer" % (grund, kurz)
            if name in K.BILD_MASS:
                return name
        return grund + "_fahrer"

    @property
    def vorn(self) -> pygame.Vector2:
        return pygame.Vector2(1, 0).rotate(self.winkel)

    @property
    def fahrt(self) -> float:
        """Tempo in Fahrtrichtung, rueckwaerts negativ."""
        return self.geschw.dot(self.vorn)

    @property
    def leben_anteil(self) -> float:
        if self.nur_bild:
            return self.anteil
        return max(0.0, self.leben / self.max_leben)

    def seite(self, herkunft) -> str:
        """Von wo ein Treffer kommt: "vorn", "seite" oder "hinten"."""
        if herkunft is None:
            return "seite"
        d = pygame.Vector2(herkunft) - self.pos
        if d.length_squared() < 1.0:
            return "seite"
        s = K.PANZER_SEITEN
        winkel = abs(self.vorn.angle_to(d))
        winkel = min(winkel, 360.0 - winkel)
        if winkel <= s["vorn_bis"]:
            return "vorn"
        if winkel >= s["hinten_ab"]:
            return "hinten"
        return "seite"

    def panzerung(self, art, herkunft=None) -> float:
        """So viel eines Treffers dieser Art kommt am Blech an (K.PANZERUNG,
        K.PANZER_SEITEN). Ohne Art: alles."""
        if art is None:
            return 1.0
        anteil = float(K.PANZERUNG.get(self.art, {}).get(art, 1.0))
        s = K.PANZER_SEITEN
        if art not in s["ohne"]:
            # Je Art eigene Faktoren (seit 0.34.107, Jagdpanzer: dicker vorn).
            eigene = self.werte.get("seiten")
            anteil *= (eigene or s)[self.seite(herkunft)]
        return anteil

    @property
    def kugel_anteil(self) -> float:
        """So viel einer Kugel kommt von der Seite am Blech an."""
        return float(K.PANZERUNG.get(self.art, {}).get("kugel", 1.0))

    def schaden(self, menge, schub=None, von=None, kugel: bool = False,
                art=None, herkunft=None) -> None:
        """Ein Treffer am Wagen. Was drinsitzt, bekommt ihn auch (seinen
        Teil nimmt Kaempfer.schaden, `fahrer_anteil`) - die Panzerung
        schuetzt das Fahrzeug, nicht den Mann in der Luke. Die eigenen
        Leute treffen den Wagen, aber nicht den Fahrer: Freundfeuer gibt es
        sonst nicht. Weggestossen wird er nicht, `schub` bleibt ungenutzt.

        Seit 0.34.65 mit Art und Herkunft (K.PANZERUNG): eine Kugel
        zerkratzt den Panzer nur, eine Hohlladung geht durch, und hinten
        ist das Blech duenner als vorn. `kugel` ist die alte Schreibweise
        fuer art="kugel"."""
        if self.kaputt or self.nur_bild or not self.lebt:
            return
        menge = float(menge)
        if menge <= 0.0:
            return
        if art is None and kugel:
            art = "kugel"
        k = self.fahrer
        if (k is not None and k.lebt and von is not k
                and (von is None or getattr(von, "fraktion", None) != k.fraktion)):
            k.schaden(menge, None, von)
        anteil = self.panzerung(art, herkunft)
        self.leben -= menge * anteil
        self.letzter_treffer = (art or "-", self.seite(herkunft), anteil, menge * anteil)
        self.blitz = K.TREFFER["blitz"]
        if self.leben <= 0.0:
            self._zerstoeren(von)

    # ---- EMP, Reifen, Heckhilfen (seit 0.34.65) ----------------------
    def emp_treffen(self, dauer: float) -> None:
        """Ein EMP: Motor, Lenkung und Waffen fallen fuer `dauer` aus."""
        if self.kaputt or self.nur_bild:
            return
        if self.emp_rest <= 0.0 and self.welt is not None:
            self.welt.klang("emp_aus", 0.8, self.pos, self.ebene)
        self.emp_rest = max(self.emp_rest, float(dauer))

    def platt_treffen(self, dauer: float) -> None:
        if self.kaputt or self.nur_bild:
            return
        self.platt_rest = max(self.platt_rest, float(dauer))
        if self.welt is not None:
            self.welt.klang("reifen_platt", 0.8, self.pos, self.ebene)

    def hilfe_auffuellen(self) -> None:
        """Volle Ladungen fuer das, was diese Art hinten heraus werfen kann."""
        self.hilfe = {n: int(h["ladungen"]) for n, h in K.FAHRZEUG_HILFE.items()
                      if self.art in h["arten"]}
        self.hilfe_takt = {}

    def heck(self, weiter: float = 0.0) -> pygame.Vector2:
        """Ein Punkt hinter dem Wagen."""
        f = self.werte
        hinten = f.get("hinten", -(f.get("achse", 14.0) + f.get("kreis", 13.0)))
        return self.pos + self.vorn * (hinten - 6.0 - weiter)

    def hilfe_nutzen(self, name: str) -> bool:
        """Hecknebel oder Nagelstreuer ausloesen. False: geht gerade nicht
        (keine Ladung, noch im Takt, EMP, Wrack, diese Art hat es nicht)."""
        w = self.welt
        if (w is None or self.kaputt or self.nur_bild or self.emp_rest > 0.0
                or self.hilfe.get(name, 0) <= 0 or self.hilfe_takt.get(name, 0.0) > 0.0):
            return False
        h = K.FAHRZEUG_HILFE[name]
        self.hilfe[name] -= 1
        self.hilfe_takt[name] = h["takt"]
        if name == "hecknebel":
            for i in range(h["wolken"]):
                w.rauch.append(Rauchwolke(self.heck(h["abstand"] * i), self.ebene,
                                          radius=h["radius"], dauer=h["dauer"]))
            w.explosion(self.heck(), self.ebene, 0.0, "rauch")
        elif name == "nagelstreuer":
            w.naegel.append(Nagelfeld(self.heck(K.NAEGEL["radius"] * 0.6), self.ebene,
                                      von=self.fahrer))
            w.klang("aufheben", 0.7, self.pos, self.ebene)
        return True

    def _emp_funkeln(self, dt: float) -> None:
        """Blaue Funken, solange der EMP wirkt - beim Gastgeber und beim Gast."""
        if self.emp_rest <= 0.0 or self.kaputt or self.welt is None:
            return
        self._emp_funken -= dt
        if self._emp_funken > 0.0:
            return
        self._emp_funken = K.EMP["funken_takt"]
        stelle = self.pos + pygame.Vector2(RND.uniform(-14, 14), RND.uniform(-10, 10)).rotate(self.winkel)
        wolke(self.welt, stelle, 2, 70, 0.25, (150, 220, 255), self.ebene, 1, "funke")

    def _zerstoeren(self, von) -> None:
        """Er geht hoch. Der Fahrer wird vom Gefecht herausgeholt
        (`kaputt` ist das Zeichen dafuer), alles im Umkreis bekommt
        Schaden."""
        f = self.werte
        self.kaputt = True
        self.kaputt_von = von
        self.leben = 0.0
        # Im Raster bleibt er: das Wrack haelt andere Wagen auf. Kugeln
        # gehen trotzdem hindurch - Welt.treffer nimmt nur, wer noch Leben hat.
        self.wrack_rest = f["wrack_zeit"]
        self.gas = self.lenk = 0.0
        self.handbremse = False
        w = self.welt
        if w is None:
            return
        r = f["explosion_radius"]
        w.explosion(self.pos, self.ebene, r, self.explosion_art, von)
        w.klang("c4_explosion", 0.8, self.pos, self.ebene)
        for ding in list(w.nahe(self.pos, r + 30, self.ebene)):
            if (ding is self or ding is self.fahrer or not ding.lebt
                    or not getattr(ding, "trefferbar", False)):
                continue
            weit = self.pos.distance_to(ding.pos)
            if weit >= r:
                continue
            anteil = (1.0 - weit / r) * w.deckung_anteil(self.pos, ding.pos, self.ebene)
            schub = ding.pos - self.pos
            if schub.length_squared() > 0.01:
                schub = schub.normalize() * 240 * anteil
            schaden_an(ding, f["explosion_schaden"] * anteil, schub, von, "spreng", self.pos)

    def wrack_qualm(self, dt: float) -> None:
        """Das Wrack qualmt und glimmt - beim Gastgeber und beim Gast."""
        if not self.kaputt or self.welt is None:
            return
        self._rauch_rest -= dt
        if self._rauch_rest > 0.0:
            return
        self._rauch_rest = K.FAHRZEUG["rauch_takt"]
        wolke(self.welt, self.pos - self.vorn * 10, 1, 26, 1.6, (52, 48, 46),
              self.ebene, 3, "staub", 60, -90.0, 0.8)
        wolke(self.welt, self.pos - self.vorn * 14, 1, 40, 0.5, (255, 140, 50),
              self.ebene, 1, "funke", 90, -90.0, 2.0)

    # ---- Anstossen ----------------------------------------------------
    def kreise(self, pos=None, winkel=None) -> tuple:
        """Die beiden Kreise, mit denen er anstoesst: vorn und hinten."""
        pos = self.pos if pos is None else pos
        winkel = self.winkel if winkel is None else winkel
        achse = pygame.Vector2(self.werte["achse"], 0).rotate(winkel)
        return (pos + achse, pos - achse)

    def beruehrt(self, pos, radius: float) -> bool:
        """Liegt ein Kreis an `pos` am Wagen an?"""
        grenze = (self.radius + radius) ** 2
        return any(c.distance_squared_to(pos) <= grenze for c in self.kreise())

    def rand_punkt(self, pos) -> pygame.Vector2:
        """Der Punkt am Blech, der `pos` am naechsten ist (`pos` selbst,
        wenn es am Wagen oder darin liegt). Seit 0.34.95 fuer Raketen: ein
        Treffer am Bug ist ein Volltreffer, auch wenn die Mitte des Wagens
        weit weg liegt."""
        pos = pygame.Vector2(pos)
        c = min(self.kreise(), key=lambda k: k.distance_squared_to(pos))
        ab = pos - c
        if ab.length_squared() <= self.radius * self.radius:
            return pos
        return c + ab.normalize() * self.radius

    def passt(self, pos, winkel=None) -> bool:
        """Kann er hier stehen? Mauern, Loecher und alles Unverschiebbare
        (Zielpuppe, Koloss) halten ihn auf; Menschen und gewoehnliche
        Gegner nicht, die schiebt er beiseite."""
        w = self.welt
        if w is None:
            return True
        # Innerhalb des eigenen Schritts (seit 0.34.75): dieselbe Frage
        # zweimal - Drehen um null und Fahren um null, wenn er steht - hat
        # dieselbe Antwort, dazwischen bewegt sich in der Welt nichts.
        merk = self._passt_merk
        if merk is not None:
            schluessel = (pos.x, pos.y, self.winkel if winkel is None else winkel)
            if merk[0] == schluessel:
                return merk[1]
            antwort = self._passt_rechnen(w, pos, winkel)
            self._passt_merk = (schluessel, antwort)
            return antwort
        return self._passt_rechnen(w, pos, winkel)

    def _frei_gemerkt(self, w, nr: int, c, r: float) -> bool:
        """w.frei(c, r, ebene, True), je Kreis gemerkt (seit 0.34.75): ein
        stehender Wagen fragt jeden Schritt dasselbe. Die Antwort haengt nur
        an Ort und Radius und an den Kacheln unter dem Kreis - die werden
        jedesmal verglichen."""
        e = w.ebene(self.ebene)
        T = K.TILE
        x0, x1 = int((c.x - r) // T), int((c.x + r) // T)
        y0, y1 = int((c.y - r) // T), int((c.y + r) // T)
        b = e.breite
        if not (0 <= x0 and x1 < b and 0 <= y0 and y1 < e.hoehe):
            return w.frei(c, r, self.ebene, True)
        kacheln = e.kacheln
        reihen = [kacheln[ty * b + x0: ty * b + x1 + 1] for ty in range(y0, y1 + 1)]
        schluessel = (c.x, c.y, r, x0, y0)
        merk = self.__dict__.get("_frei_merk")
        if merk is None:
            merk = self._frei_merk = {}
        hit = merk.get(nr)
        if hit is not None and hit[0] == schluessel and hit[1] is e and hit[2] == reihen:
            return hit[3]
        antwort = w.frei(c, r, self.ebene, True)
        merk[nr] = (schluessel, e, reihen, antwort)
        return antwort

    def _passt_rechnen(self, w, pos, winkel) -> bool:
        r = self.radius
        kreise = self.kreise(pos, winkel)
        for nr, c in enumerate(kreise):
            if not self._frei_gemerkt(w, nr, c, r):
                return False
        for a in w.nahe(pos, self.werte["achse"] + r + 40, self.ebene):
            if getattr(a, "rechteckig", False):
                # Ein Panzer oder Panzerwagen (seit 0.34.59): Kreis an Rechteck.
                if a.lebt and any(a.beruehrt(c, r) for c in kreise):
                    return False
                continue
            if isinstance(a, Buggy) and a is not self:
                # Andere Wagen: Kreis an Kreis (seit 0.34.18 stehen sie im
                # Raster, weil man sie treffen kann - vorher hielt nur der
                # Fahrer des anderen Wagens einen auf, ein leerer gar nicht).
                if any(c.distance_squared_to(d) < (2 * r) ** 2
                       for c in kreise for d in a.kreise()):
                    return False
                continue
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
        if self.kaputt:
            self.wrack_rest = max(0.0, self.wrack_rest - dt)
            self.wrack_qualm(dt)
        for n in list(self.hilfe_takt):
            self.hilfe_takt[n] = max(0.0, self.hilfe_takt[n] - dt)
        self.platt_rest = max(0.0, self.platt_rest - dt)
        # Ein EMP legt alles still: kein Gas, keine Lenkung (seit 0.34.65).
        # Rollen und gebremst werden geht weiter - die Physik bleibt.
        stromlos = self.emp_rest > 0.0
        if stromlos:
            self.emp_rest = max(0.0, self.emp_rest - dt)
            self._emp_funkeln(dt)
        fahrer = self.fahrer is not None and not self.kaputt and not stromlos
        self._physik(dt, self.gas if fahrer else 0.0,
                     self.lenk if fahrer else 0.0,
                     bool(self.handbremse) and fahrer)
        if self.platt_rest > 0.0:
            # Platte Reifen: mehr als einen Teil des Hoechsttempos gibt es nicht.
            hoechst = self.werte["hoechst"] * K.NAEGEL["platt_tempo"]
            if self.geschw.length() > hoechst:
                self.geschw.scale_to_length(hoechst)
        self._passt_merk = ((), False)          # ab hier merken (passt)
        try:
            self._drehen(dt)
            self._fahren(dt)
        finally:
            self._passt_merk = None
        self.tempo.update(self.geschw)
        self._beiseite_schieben()
        self._staub(dt)
        self._spuren()
        self._quietschen(dt)

    def _drehen(self, dt: float) -> None:
        """Drehen nur, wenn er danach noch passt - sonst klemmte er sich an
        einer Mauer fest. Stattdessen verliert er die Drehung."""
        neu = (self.winkel + math.degrees(self.gier * dt) + 180.0) % 360.0 - 180.0
        if self.passt(self.pos, neu):
            self.winkel = neu
        else:
            self.gier *= -0.2

    def stick_steuern(self, richtung) -> tuple:
        """(Gas, Lenkung) aus einer Richtung im Bild, fuer einen Stick.

        W/A/S/D auf einen Stick gelegt fuehlte sich falsch an (gemeldet):
        nach rechts gedrueckt lenkte er nach rechts *von sich aus*, also
        bei einem Wagen, der nach unten faehrt, im Bild nach links. Hier
        zeigt der Stick, wohin es gehen soll - wie beim Laufen. Er lenkt
        dorthin, gibt so viel Gas, wie weit der Stick gedrueckt ist, und
        wendet, wenn es hinter ihn geht. Fast genau entgegen bremst er,
        und steht er fast, faehrt er rueckwaerts."""
        f = self.werte
        r = pygame.Vector2(richtung)
        staerke = min(1.0, r.length())
        if staerke < f["stick_tot"]:
            return 0.0, 0.0
        soll = math.degrees(math.atan2(r.y, r.x))
        ab = (soll - self.winkel + 180.0) % 360.0 - 180.0
        if abs(ab) >= f["stick_zurueck"]:
            if self.fahrt > f["stick_bremsen_ab"]:
                return -1.0, 0.0                       # erst bremsen
            return -staerke, 0.0                       # dann rueckwaerts
        lenk = max(-1.0, min(1.0, ab / f["stick_voll_lenken"]))
        gas = staerke if abs(ab) < f["stick_wenden"] else staerke * 0.5
        return gas, lenk

    # Merkzelle fuer _physik (seit 0.34.75): (Eingaben als Bytes, Werte,
    # Ergebnis). Ein stehender Wagen rechnet jeden Schritt dasselbe.
    _physik_merk = None
    _PHYSIK_FORM = struct.Struct("<8d?")

    def _physik(self, dt: float, gas: float, lenk: float, handbremse: bool) -> None:
        """_physik_rechnen, gemerkt. Die Rechnung haengt nur von Tempo,
        Gier, Lenkwinkel, Winkel, den Werten und den Eingaben ab; sind die
        bitgenau (auch das Vorzeichen einer Null) wie beim letzten Schritt,
        kommt genau dasselbe heraus - ohne die ganze Rechnung."""
        g = self.geschw
        schluessel = self._PHYSIK_FORM.pack(g.x, g.y, self.gier, self.lenkwinkel, self.winkel,
                                            dt, gas, lenk, bool(handbremse))
        merk = self._physik_merk
        f = self.werte
        if merk is not None and merk[0] == schluessel and merk[1] is f:
            gx, gy, self.gier, self.lenkwinkel, self.rutschen = merk[2]
            g.update(gx, gy)
            return
        self._physik_rechnen(dt, gas, lenk, handbremse)
        g = self.geschw
        self._physik_merk = (schluessel, f, (g.x, g.y, self.gier, self.lenkwinkel,
                                             self.rutschen))

    def _physik_rechnen(self, dt: float, gas: float, lenk: float, handbremse: bool) -> None:
        """Ein Schritt Einspurmodell: Kraefte an Vorder- und Hinterachse,
        daraus Beschleunigung und Drehung. Je Masse gerechnet.

        Mit dem Satz des Panzerwagens (seit 0.34.59) an zwei Stellen
        anders: der Motor zieht mit dem Tempo staerker (`motor_wachsen`),
        und der Radeinschlag folgt einem Wenderadius, der mit dem Tempo
        waechst (`wende_grund`) - zaeh, schnell, schlecht lenkbar."""
        f = self.werte
        vorn = self.vorn
        quer = pygame.Vector2(-vorn.y, vorn.x)        # rechts in Fahrtrichtung
        vx = self.geschw.dot(vorn)
        vy = self.geschw.dot(quer)
        tempo = self.geschw.length()

        # Lenkung: schnell, aber nicht sofort; bei Fahrt weniger Einschlag.
        # Dazu lenkt er einen Teil des Driftwinkels selbst gegen.
        lenk_max = math.radians(f["lenk_max"])
        if f.get("wende_grund"):
            radstand = f["achse_vorn"] + f["achse_hinten"]
            lenk_max = math.atan(radstand / (f["wende_grund"]
                                             + f["wende_je_tempo"] * abs(vx)))
            ziel = lenk * lenk_max
        else:
            ziel = lenk * lenk_max * (1.0 - f["lenk_abfall"]
                                      * min(1.0, abs(vx) / f["hoechst"]))
        if tempo > 40.0 and vx > 0.0:
            # GRUND fuer mehr ohne Lenktaste: mit Gas haelt ein Drift sich
            # sonst selbst - Heckantrieb und Gegenlenken im Gleichgewicht,
            # gemessen 31 Grad quer, endlos. Mit Lenkrad realistisch, mit
            # Tasten heisst Loslassen aber "geradeaus".
            gegen = f["gegenlenken"] if lenk else f["gegenlenken_los"]
            ziel += gegen * math.atan2(vy, vx)
            ziel = max(-lenk_max, min(lenk_max, ziel))
        schritt = math.radians(f["lenk_tempo"]) * dt
        self.lenkwinkel += max(-schritt, min(schritt, ziel - self.lenkwinkel))
        dl = self.lenkwinkel

        # Laengs: Motor, Bremse, Rollen, Luft. Angetrieben wird hinten.
        fx = 0.0
        if gas > 0.0:
            if vx < -5.0:
                fx += f["bremse"]
            elif f.get("motor_wachsen"):
                v = max(0.0, vx)
                fx += (f["motor"] + f["motor_wachsen"] * v) * gas \
                    * max(0.0, 1.0 - (v / f["hoechst"]) ** 3)
            else:
                fx += f["motor"] * gas * max(0.0, 1.0 - max(0.0, vx) / f["hoechst"])
        elif gas < 0.0:
            if vx > 5.0:
                fx -= f["bremse"]
            else:
                fx -= f["motor"] * 0.6 * max(0.0, 1.0 - max(0.0, -vx) / f["rueckwaerts"])
        else:
            fx -= math.copysign(min(f["rollen"], abs(vx) / dt), vx)
        fx -= f["luft"] * vx * abs(vx)
        antrieb = fx if gas != 0.0 else 0.0
        durch = max(0.0, abs(antrieb) - f["griff_hinten"] * f["durchdrehen"])
        if durch > 0.0:
            fx -= math.copysign(durch, antrieb) * 0.5     # was durchdreht, schiebt nicht
        if handbremse:
            fx -= math.copysign(min(f["handbremse_bremse"], abs(vx) / dt), vx)

        # Quer: Schraeglauf an beiden Achsen, Seitenkraft bis zur Grenze.
        a, b = f["achse_vorn"], f["achse_hinten"]
        vy_vorn = vy + self.gier * a
        quer_vorn = -math.sin(dl) * vx + math.cos(dl) * vy_vorn
        laengs_vorn = math.cos(dl) * vx + math.sin(dl) * vy_vorn
        a_vorn = math.atan2(quer_vorn, max(abs(laengs_vorn), f["v_min"]))
        a_hinten = math.atan2(vy - self.gier * b, max(abs(vx), f["v_min"]))
        spitze = math.radians(f["schlupf_spitze"])

        def griff(schraeg):
            ueber = max(0.0, abs(schraeg) - spitze)
            return 1.0 - (1.0 - f["gleiten"]) * min(1.0, ueber / 0.35)

        g_vorn = f["griff_vorn"] * griff(a_vorn)
        g_hinten = f["griff_hinten"] * griff(a_hinten)
        if handbremse:
            g_hinten *= f["handbremse_griff"]
        kreis = f["antrieb_kreis"] if lenk else f["antrieb_kreis_los"]
        g_hinten = math.sqrt(max(0.0, g_hinten ** 2 - min(g_hinten, abs(antrieb)) ** 2
                                 * kreis))
        if durch > 0.0:
            g_hinten *= f["gleiten"]
        k_vorn = max(-g_vorn, min(g_vorn, -f["steif"] * a_vorn))
        k_hinten = max(-g_hinten, min(g_hinten, -f["steif"] * a_hinten))

        ax = fx - math.sin(dl) * k_vorn
        ay = math.cos(dl) * k_vorn + k_hinten
        self.geschw += (vorn * ax + quer * ay) * dt
        moment = a * math.cos(dl) * k_vorn - b * k_hinten
        # Die Driftstuetze (siehe oben): dreht ihn zurueck, bevor er sich dreht.
        # Auch ueber 90 Grad hinaus - gerade dann, sonst dreht er sich ganz.
        # Rueckwaerts gefahren wird nicht gestuetzt (gas < 0, vx < 0).
        if tempo > 40.0 and not (gas < 0.0 and vx < 0.0):
            beta = math.atan2(vy, vx)
            ueber = abs(beta) - math.radians(f["drift_grenze_hb" if handbremse
                                               else "drift_grenze"])
            if ueber > 0.0:
                moment += math.copysign(1.0, beta) * f["drift_stuetze"] * ueber \
                    * min(1.0, tempo / 120.0)
        self.gier += moment / f["traegheit"] * dt
        if tempo < 8.0 and gas == 0.0:
            # Fast stehend: ausrollen lassen, nicht zittern.
            self.geschw *= 0.9
            self.gier *= 0.8

        schlupf = max(abs(vy - self.gier * b), abs(quer_vorn))
        self.rutschen = max(0.0, min(1.0, (schlupf - 25.0) / 90.0))
        if durch > 0.0 and gas > 0.0:
            # Anfahren mit durchdrehenden Raedern zeichnet auch.
            self.rutschen = max(self.rutschen, min(1.0, durch / 200.0))
        if handbremse and tempo > 30.0:
            self.rutschen = max(self.rutschen, 0.6)

    def _fahren(self, dt: float) -> None:
        """In kleinen Schritten vorwaerts. An einer Mauer gleitet er
        entlang, wenn eine Achse frei ist; sonst prallt er ab."""
        f = self.werte
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
                self.gier *= 0.3
                break
        if stoss >= f["aufprall_hart"]:
            w = self.welt
            staerke = min(1.0, stoss / f["hoechst"])
            # Kein Klang mehr beim Anprall (seit 0.34.96, gewuenscht) - nur
            # Ruckeln und Staub.
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
        kreise = None
        for a in list(w.nahe(self.pos, self.werte["achse"] + r + 40, self.ebene)):
            if (a is self.fahrer or a is self or not a.lebt or a.flug > 0
                    or not getattr(a, "schiebt", True)
                    or not getattr(a, "schiebbar", True)
                    or getattr(a, "am_boden", False)
                    or getattr(a, "im_fahrzeug", False)):
                continue
            # Die Kreise einmal (seit 0.34.75): der Wagen bewegt sich in
            # dieser Schleife nicht, nur die Geschobenen.
            if kreise is None:
                kreise = self.kreise()
            for c in kreise:
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
        f = self.werte
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
        hinten = self.pos - vorn * f.get("staub_hinten", 15)
        richtung = math.degrees(math.atan2(-self.geschw.y, -self.geschw.x))
        menge = 1 + int(2 * min(1.0, tempo / f["hoechst"]))
        for seite in (-1, 1):
            wolke(self.welt, hinten + quer * (f.get("staub_quer", 13) * seite), menge,
                  30 + 40 * tempo / f["hoechst"], 0.8, f["staub_farbe"],
                  self.ebene, f["staub_groesse"], "staub", 70, richtung, 2.5)

    def staub_gast(self, dt: float) -> None:
        """Beim Gast: derselbe Staub, dieselben Spuren - aus dem gemeldeten
        Tempo und Rutschen. Gequietscht wird beim Gastgeber (NETZKLAENGE)."""
        self._staub(dt)
        self._spuren()
        self.wrack_qualm(dt)
        if self.emp_rest > 0.0:
            self.emp_rest = max(0.0, self.emp_rest - dt)
            self._emp_funkeln(dt)

    def _radstellen(self) -> list:
        """Wo die Raeder den Boden beruehren: hinten links, hinten rechts,
        vorn links, vorn rechts."""
        vorn = self.vorn
        quer = pygame.Vector2(-vorn.y, vorn.x)
        return [self.pos - vorn * 15 - quer * 12, self.pos - vorn * 15 + quer * 12,
                self.pos + vorn * 15 - quer * 11, self.pos + vorn * 15 + quer * 11]

    def _spuren(self) -> None:
        """Reifenspuren im Sand, wo er rutscht. Sie bleiben liegen (Dekal),
        wie Blut und Brandflecken - man sieht hinterher, wo gedriftet wurde."""
        f = self.werte
        if self.welt is None or self.rutschen < f["spur_ab"]:
            self._spur_letzte.clear()
            return
        ebene = self.welt.ebene(self.ebene)
        stellen = self._radstellen()
        # Vorn nur, wenn er richtig quer steht - sonst rollen sie.
        welche = range(4) if self.rutschen > 0.7 else range(2)
        deck = int(40 + 70 * self.rutschen)
        for i in welche:
            p = stellen[i]
            letzte = self._spur_letzte.get(i)
            if letzte is None:
                self._spur_letzte[i] = pygame.Vector2(p)
                continue
            weg = p.distance_to(letzte)
            if weg < f["spur_abstand"]:
                continue
            schritte = min(12, int(weg / f["spur_abstand"]))
            for s in range(1, schritte + 1):
                q = letzte.lerp(p, s / schritte)
                ebene.dekal(_spurpunkt(deck), q.x, q.y)
            self._spur_letzte[i] = pygame.Vector2(p)

    def _quietschen(self, dt: float) -> None:
        f = self.werte
        self._quietsch_rest = max(0.0, self._quietsch_rest - dt)
        if self.rutschen >= f["quietschen_ab"] and self._quietsch_rest <= 0.0:
            self._quietsch_rest = f["quietschen_pause"]
            self.welt.klang("buggy_rutschen", 0.35 + 0.5 * self.rutschen,
                            self.pos, self.ebene)

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
        self.gier = self.lenkwinkel = self.rutschen = 0.0
        self.handbremse = False
        self._spur_letzte.clear()
        self.leben = self.max_leben
        self.kaputt = False
        self.kaputt_von = None
        self.wrack_rest = 0.0
        self.emp_rest = self.platt_rest = 0.0
        self.hilfe_auffuellen()

    def ausstiegsorte(self, radius: float) -> list:
        """Wo man aussteigen kann, der Reihe nach: links, rechts, hinten,
        vorn. Links zuerst, weil dort der Fahrer sitzt - wie im Auto."""
        vorn = self.vorn
        quer = pygame.Vector2(vorn.y, -vorn.x)       # links in Fahrtrichtung
        seite = self.radius + radius + 3.0
        laenge = self.werte["achse"] + self.radius + radius + 3.0
        return [self.pos + quer * seite, self.pos - quer * seite,
                self.pos - vorn * laenge, self.pos + vorn * laenge,
                self.pos + quer * seite - vorn * 14, self.pos - quer * seite - vorn * 14,
                self.pos + quer * seite + vorn * 14, self.pos - quer * seite + vorn * 14]


# ══════════════════════════════════════════════════════════════════
# Panzer und Panzerwagen (seit 0.34.59)
# ══════════════════════════════════════════════════════════════════
#
# Entwurf und Abnahme aus dem Paket `rustfront_fahrzeuge`. Gemeinsam ist
# beiden, was den Buggy nicht betrifft:
#
# * **Ein Rechteck statt zweier Kreise.** Der Fussabdruck steht in den
#   Werten (`vorn`, `hinten`, `halb`, lokal, +x = vorn). Damit stoesst er
#   an Mauern, Loecher und andere Wagen, und damit wird er getroffen.
# * **Rammen.** Wer im Weg steht, wird an der Seite mit der geringsten
#   Eindringtiefe hinausgeschoben - nach jedem Schritt liegt niemand mehr
#   im Fussabdruck. Schaden gibt es nur ueber die Front und erst ab einer
#   Schwelle; wer dabei stirbt, fliegt noch ein Stueck (Welt.leichenflug).
# * **Ein Aufbau, der sich dreht.** Turm bzw. MG-Ring folgen dem
#   Mauszeiger des Fahrers mit ihrem eigenen Tempo, unabhaengig von der
#   Wanne (Weltwinkel `aufbau`). Gemeldet als Entscheidung: einer steuert
#   ein Fahrzeug - er faehrt und schiesst.
# * **Panzerung.** Seit 0.34.65 je Schadensart und Seite (K.PANZERUNG,
#   Buggy.panzerung): Kugeln zerkratzen nur, Hohlladungen gehen durch.
# * **Drei Zeichenebenen.** Erst Schatten und Wanne (Ketten und Raeder sind
#   niedrig), dann die Figuren, dann Turm und Ring (render.py). Sonst lag
#   alles, was noerdlich von ihm steht, unter seinen Ketten.

_SEITEN = {"vorn": pygame.Vector2(1, 0), "hinten": pygame.Vector2(-1, 0),
           "links": pygame.Vector2(0, -1), "rechts": pygame.Vector2(0, 1)}


def _projektion(ecken, achse) -> tuple:
    werte = [e.dot(achse) for e in ecken]
    return min(werte), max(werte)


def _vielecke_ueberlappen(a, b) -> bool:
    """Trennende Achsen fuer zwei konvexe Vierecke (je vier Ecken)."""
    for ecken in (a, b):
        for i in range(4):
            kante = ecken[(i + 1) % 4] - ecken[i]
            achse = pygame.Vector2(-kante.y, kante.x)
            a0, a1 = _projektion(a, achse)
            b0, b1 = _projektion(b, achse)
            if a1 <= b0 or b1 <= a0:
                return False
    return True


class Panzergranate(Geschoss):
    """Die Granate der Kanone: fliegt wie ein Geschoss, mit dicker
    Leuchtspur, und explodiert, wo sie aufschlaegt - an einem Wesen, einer
    Mauer oder am Ende ihrer Reichweite. Der Einschlag ist eine eigene
    Explosionsart (Welt.explosion "panzer"): groesser als Granate und C4,
    mit Feuerball, Rauch und einem unregelmaessigen Krater."""

    bild = "panzergranate"
    spur = (255, 226, 160)
    spur_dick = 2
    radius = 3.0

    def __init__(self, pos, richtung: float, daten: dict, ebene: int,
                 von=None, waffe: str = "kanone", traeger=None) -> None:
        super().__init__(pos, richtung, daten, ebene, von, waffe)
        self.daten = daten
        self.traeger = traeger

    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        if self.lebt is False and self.rest <= 0 and not getattr(self, "_gezuendet", False):
            # Am Ende der Reichweite: sie zuendet in der Luft ueber dem Boden.
            self._zuenden(None)

    def einschlag(self, ziel) -> None:
        self.lebt = False
        self._zuenden(ziel)

    def _zuenden(self, ziel) -> None:
        if getattr(self, "_gezuendet", False):
            return
        self._gezuendet = True
        self.lebt = False
        d = self.daten
        w = self.welt
        if w is None:
            return
        if ziel is not None and ziel.lebt:
            schub = pygame.Vector2(self.tempo)
            if schub.length_squared() > 0.01:
                schub.scale_to_length(d["schub"])
            lebte = ziel.lebt
            if hasattr(self.von, "zaehlen") and getattr(ziel, "zaehlt_treffer", True):
                self.von.zaehlen("treffer", 1.0, self.waffe)
            herkunft = None
            if self.tempo.length_squared() > 0.01:
                herkunft = self.pos - pygame.Vector2(self.tempo).normalize() * 40.0
            schaden_an(ziel, d["schaden"], schub, self.von, "panzerbrechend", herkunft)
            abschuss_buchen(self.von, ziel, self.waffe, lebte)
        r = d["radius"]
        for a in list(w.nahe(self.pos, r + 60, self.ebene)):
            if not a.lebt or a is ziel or a is self or not getattr(a, "trefferbar", True):
                continue
            ab = a.pos - self.pos
            weit = ab.length()
            if weit > r + a.radius:
                continue
            anteil = (1.0 - 0.6 * min(1.0, weit / max(1.0, r)))
            anteil *= w.deckung_anteil(self.pos, a.pos, self.ebene)
            schub = ab.normalize() * d["schub"] * anteil if weit > 0.01 else None
            lebte = a.lebt
            schaden_an(a, d["flaeche"] * anteil, schub, self.von, "spreng", self.pos)
            abschuss_buchen(self.von, a, self.waffe, lebte)
        w.explosion(self.pos, self.ebene, r, "panzer", self.von)


class Schwer(Buggy):
    """Was Panzer und Panzerwagen gemeinsam haben (siehe oben)."""

    rechteckig = True
    werte = None
    # Gezeichnet wird er selbst, in zwei Teilen (render.wesen_zeichnen und
    # render.aufbauten_zeichnen), und vor allen Figuren.
    zeichnet_selbst = True
    schicht = 0
    hoehe_3d = 0.0
    explosion_art = "panzer"
    # Welches Bild der Aufbau hat ("panzer_turm" oder "panzerwagen_ring").
    aufbau_name = ""

    def __init__(self, pos, ebene: int = 0, winkel: float = 0.0,
                 nur_bild: bool = False) -> None:
        super().__init__(pos, ebene, winkel, nur_bild)
        f = self.werte
        self.radius = f["halb"]
        # So weit reicht er von der Mitte aus hoechstens (Welt.nahe).
        self.huelle_radius = math.hypot(max(f["vorn"], -f["hinten"]), f["halb"])
        self.aufbau = float(winkel)      # Weltwinkel von Turm bzw. Ring
        self.feuer = False               # linke Maustaste des Fahrers
        self.zweit = False               # rechte
        self.ruecklauf = 0.0             # Rohr bzw. Lauf, Pixel
        self.ruck = 0.0                  # die Wanne nach dem Kanonenschuss
        self.takt: dict = {}             # Waffe -> Sekunden bis zum naechsten Schuss
        self.ph_links = 0.0              # Ketten- bzw. Reifenphase, 0 bis 1
        self.ph_rechts = 0.0
        self._sperre: dict = {}          # id(Wesen) -> Sekunden ohne Rammschaden
        self._spur_weg = 0.0
        self._motor_rest = 0.0

    # ---- Werte -------------------------------------------------------
    @property
    def fahrer_anteil(self) -> float:
        """So viel von jedem Treffer kommt beim Fahrer an (Kaempfer.schaden)."""
        return float(self.werte["fahrer_anteil"])

    @property
    def bild(self) -> str:
        return "%s_wrack" % self.art if self.kaputt else self.art

    def aufbau_bild_name(self) -> str:
        """Turm bzw. Ring: leer, mit Insasse - in seinem Skin oder in den
        Farben seiner Mannschaft (Buggy._insassen_bild)."""
        return self._insassen_bild(self.aufbau_name)

    def aufbau_mitte(self, pos=None, winkel=None) -> pygame.Vector2:
        raise NotImplementedError

    # ---- Geometrie ---------------------------------------------------
    def lokal(self, punkt, pos=None, winkel=None) -> pygame.Vector2:
        pos = self.pos if pos is None else pos
        winkel = self.winkel if winkel is None else winkel
        return (pygame.Vector2(punkt) - pos).rotate(-winkel)

    def ecken(self, pos=None, winkel=None, rand: float = 0.0) -> list:
        """Die vier Ecken des Fussabdrucks in der Welt, im Uhrzeigersinn."""
        f = self.werte
        pos = self.pos if pos is None else pos
        winkel = self.winkel if winkel is None else winkel
        v, h, b = f["vorn"] + rand, f["hinten"] - rand, f["halb"] + rand
        return [pos + pygame.Vector2(x, y).rotate(winkel)
                for x, y in ((v, -b), (v, b), (h, b), (h, -b))]

    def beruehrt(self, pos, radius: float, eigene=None, winkel=None) -> bool:
        """Liegt ein Kreis an `pos` am Rechteck an (oder darin)?"""
        f = self.werte
        lok = self.lokal(pos, eigene, winkel)
        nx = max(f["hinten"], min(lok.x, f["vorn"]))
        ny = max(-f["halb"], min(lok.y, f["halb"]))
        return (lok.x - nx) ** 2 + (lok.y - ny) ** 2 <= radius * radius

    def rand_punkt(self, pos) -> pygame.Vector2:
        """Der naechste Punkt des Rechtecks (siehe Buggy)."""
        f = self.werte
        lok = self.lokal(pos)
        nx = max(f["hinten"], min(lok.x, f["vorn"]))
        ny = max(-f["halb"], min(lok.y, f["halb"]))
        return self.pos + pygame.Vector2(nx, ny).rotate(self.winkel)

    def kreise(self, pos=None, winkel=None) -> tuple:
        """Fuer alles, was nur Kreise kennt: drei Kreise entlang der Mitte."""
        pos = self.pos if pos is None else pos
        winkel = self.winkel if winkel is None else winkel
        f = self.werte
        mitte = (f["vorn"] + f["hinten"]) / 2.0
        schritt = (f["vorn"] - f["hinten"]) / 2.0 - f["halb"]
        return tuple(pos + pygame.Vector2(mitte + s * schritt, 0).rotate(winkel)
                     for s in (-1, 0, 1))

    def _kacheln_frei(self, pos, winkel) -> bool:
        """Mauern, Kisten, Faesser und Loecher (als Wand) gegen das Rechteck.

        Gemerkt (seit 0.34.75): ein stehender Panzer fragt jeden Schritt
        dasselbe. Die Antwort haengt nur an Ort und Winkel (bitgenau) und
        an den Kachelnummern im Rechteck darum - die werden jedesmal
        verglichen, eine zerstoerte oder gebaute Kachel faellt also auf."""
        w = self.welt
        e = w.ebene(self.ebene)
        schluessel = struct.pack("<3d", pos.x, pos.y, winkel)
        merk = self.__dict__.get("_kacheln_merk")
        if merk is not None and merk[0] == schluessel and merk[1] is e:
            x0, x1, y0, y1 = merk[2]
            b = e.breite
            kacheln = e.kacheln
            if [kacheln[ty * b + x0: ty * b + x1 + 1] for ty in range(y0, y1 + 1)] == merk[3]:
                return merk[4]
        antwort = self._kacheln_frei_rechnen(e, pos, winkel)
        bereich = self.__dict__.pop("_kacheln_bereich", None)
        if bereich is not None:
            x0, x1, y0, y1 = bereich
            if 0 <= x0 and x1 < e.breite and 0 <= y0 and y1 < e.hoehe:
                b = e.breite
                kacheln = e.kacheln
                self._kacheln_merk = (schluessel, e, bereich,
                                      [kacheln[ty * b + x0: ty * b + x1 + 1]
                                       for ty in range(y0, y1 + 1)], antwort)
        return antwort

    def _kacheln_frei_rechnen(self, e, pos, winkel) -> bool:
        w = self.welt
        ecken = self.ecken(pos, winkel)
        x0 = int(min(c.x for c in ecken) // K.TILE)
        x1 = int(max(c.x for c in ecken) // K.TILE)
        y0 = int(min(c.y for c in ecken) // K.TILE)
        y1 = int(max(c.y for c in ecken) // K.TILE)
        self._kacheln_bereich = (x0, x1, y0, y1)
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                kachel = e.kachel(tx, ty)
                if K.KACHELN[kachel]["fest"]:
                    form, rx, ry, rb, rh = w.huelle(kachel)
                elif e.loch(tx, ty):
                    form, rx, ry, rb, rh = "block", 0, 0, K.TILE, K.TILE
                else:
                    continue
                ax, ay = tx * K.TILE + rx, ty * K.TILE + ry
                if form == "rund":
                    mitte = pygame.Vector2(ax + rb / 2.0, ay + rh / 2.0)
                    if self.beruehrt(mitte, rb / 2.0, pos, winkel):
                        return False
                    continue
                block = [pygame.Vector2(ax, ay), pygame.Vector2(ax + rb, ay),
                         pygame.Vector2(ax + rb, ay + rh), pygame.Vector2(ax, ay + rh)]
                if _vielecke_ueberlappen(ecken, block):
                    return False
        return True

    def _passt_rechnen(self, w, pos, winkel) -> bool:
        """Kann er hier stehen? Mauern, Loecher, andere Wagen und alles
        Unverschiebbare (Zielpuppe, Koloss) halten ihn auf. Menschen und
        gewoehnliche Gegner nicht - die rammt er (`_beiseite_schieben`).
        Gefragt wird ueber Buggy.passt (seit 0.34.75, mit Merkzelle)."""
        winkel = self.winkel if winkel is None else winkel
        if not self._kacheln_frei(pos, winkel):
            return False
        meine = None
        for a in w.nahe(pos, self.huelle_radius + 60, self.ebene):
            if a is self or not a.lebt or a is self.fahrer:
                continue
            if getattr(a, "rechteckig", False):
                if meine is None:
                    meine = self.ecken(pos, winkel)
                if _vielecke_ueberlappen(meine, a.ecken()):
                    return False
                continue
            if isinstance(a, Buggy):
                if any(self.beruehrt(c, a.radius, pos, winkel) for c in a.kreise()):
                    return False
                continue
            if (a.flug > 0 or getattr(a, "schiebbar", True)
                    or getattr(a, "am_boden", False)):
                continue
            if self.beruehrt(a.pos, a.radius, pos, winkel):
                return False
        return True

    def ausstiegsorte(self, radius: float) -> list:
        """Links zuerst, dann rechts, hinten, vorn - knapp neben der Wanne."""
        f = self.werte
        vorn = self.vorn
        links = pygame.Vector2(vorn.y, -vorn.x)
        seite = f["halb"] + radius + 3.0
        mitte = (f["vorn"] + f["hinten"]) / 2.0
        raus = []
        for x in (mitte, f["hinten"] * 0.5, f["vorn"] * 0.5):
            raus += [self.pos + vorn * x + links * seite, self.pos + vorn * x - links * seite]
        raus += [self.pos + vorn * (f["hinten"] - radius - 3.0),
                 self.pos + vorn * (f["vorn"] + radius + 3.0)]
        return raus

    # ---- Ablauf -------------------------------------------------------
    def schritt(self, dt: float) -> None:
        if self._sperre:
            for k in list(self._sperre):
                self._sperre[k] -= dt
                if self._sperre[k] <= 0.0:
                    del self._sperre[k]
        super().schritt(dt)
        if self.nur_bild or self.welt is None:
            return
        self._abklingen(dt)
        self._ketten(dt)
        if self.kaputt:
            return
        for k in list(self.takt):
            self.takt[k] = max(0.0, self.takt[k] - dt)
        if self.emp_rest > 0.0:
            # Stromlos: der Turm steht, die Waffen schweigen (seit 0.34.65).
            return
        self._aufbau_fuehren(dt)
        if self.fahrer is not None:
            self._schiessen()
            self._motor(dt)

    def _abklingen(self, dt: float) -> None:
        f = self.werte
        self.ruecklauf = max(0.0, self.ruecklauf
                             - f.get("ruecklauf_tempo", f.get("ring_ruecklauf_tempo", 14.0)) * dt)
        self.ruck = max(0.0, self.ruck - f.get("ruck_tempo", 10.0) * dt)

    def _ketten(self, dt: float) -> None:
        """Ketten bzw. Reifen laufen mit dem Weg (Gastgeber und Gast)."""

    def _aufbau_fuehren(self, dt: float) -> None:
        """Turm bzw. Ring drehen zum Zeiger des Fahrers, mit ihrem Tempo."""
        k = self.fahrer
        ziel = getattr(k, "ziel", None) if k is not None else None
        if ziel is None:
            return
        d = pygame.Vector2(ziel) - self.aufbau_mitte()
        if d.length_squared() < 16.0:
            return
        soll = math.degrees(math.atan2(d.y, d.x))
        diff = (soll - self.aufbau + 180.0) % 360.0 - 180.0
        schritt = self.aufbau_dreh * dt
        self.aufbau = (self.aufbau + max(-schritt, min(schritt, diff)) + 180.0) % 360.0 - 180.0

    def _schiessen(self) -> None:
        """Was die Maustasten des Fahrers ausloesen."""

    def _mg(self, waffe: str, muendung, richtung: float, huelse_von) -> None:
        """Ein Schuss aus einem MG: Geschoss, Knall, Huelse zur Seite."""
        d = K.FAHRZEUG_WAFFEN[waffe]
        self.takt[waffe] = d["takt"]
        a = richtung + RND.uniform(-d["streuung"], d["streuung"])
        g = Geschoss(muendung, a, d, self.ebene, self.fahrer, waffe)
        g.traeger = self
        self.welt.dazu(g)
        self.welt.schussknall(muendung, richtung, self.ebene, waffe, self.fahrer)
        if hasattr(self.fahrer, "zaehlen"):
            self.fahrer.zaehlen("schuesse", 1.0, waffe)
        aus = richtung + 90 + RND.uniform(-20, 20)
        self.welt.partikel.append(Partikel(
            huelse_von, pygame.Vector2(RND.uniform(60, 95), 0).rotate(aus) + self.geschw,
            0.9, (176, 140, 62), 1, "huelse", 3.0, self.ebene))

    def _motor(self, dt: float) -> None:
        """Kein Motor als Schleife - ein kurzes Brummen in einem Takt, solange
        er faehrt. Wie das Quietschen des Buggys."""
        self._motor_rest -= dt
        if self._motor_rest > 0.0:
            return
        self._motor_rest = self.werte["motor_takt"]
        tempo = abs(self.fahrt)
        if tempo < 3.0 and abs(self.gier) < 0.05 and abs(self.gas) < 0.1:
            return
        anteil = min(1.0, tempo / self.werte["hoechst"])
        self.welt.klang("%s_motor" % self.art, 0.3 + 0.35 * anteil, self.pos, self.ebene)

    # ---- Rammen -------------------------------------------------------
    def _beiseite_schieben(self) -> None:
        """Wer im Fussabdruck steht, wird an der Seite mit der geringsten
        Eindringtiefe hinausgeschoben. Ueber die Front und schnell genug
        gibt es Schaden und einen Stoss, der nach aussen aus der Bahn wirft;
        seitlich und hinten wird nur geschoben (Paket, RAMMEN)."""
        w = self.welt
        f = self.werte
        r_ = K.RAMMEN
        geschw_lok = self.geschw.rotate(-self.winkel)
        for a in list(w.nahe(self.pos, self.huelle_radius + 20, self.ebene)):
            if (a is self or a is self.fahrer or not a.lebt or a.flug > 0
                    or not getattr(a, "schiebt", True)
                    or not getattr(a, "schiebbar", True)
                    or getattr(a, "im_fahrzeug", False)):
                continue
            lok = self.lokal(a.pos)
            r = a.radius
            tiefe = {"vorn": f["vorn"] + r - lok.x, "hinten": lok.x - (f["hinten"] - r),
                     "links": lok.y + f["halb"] + r, "rechts": f["halb"] + r - lok.y}
            if min(tiefe.values()) <= 0.0:
                continue
            seite = None
            for s in sorted(tiefe, key=tiefe.get):
                neu = self.pos + (lok + _SEITEN[s] * (tiefe[s] + 0.3)).rotate(self.winkel)
                if w.frei(neu, r, a.ebene, not getattr(a, "faellt", False)):
                    a.pos.update(neu)
                    seite = s
                    break
            if seite is None:
                continue                  # klemmt an der Mauer: bleibt, wo er ist
            n = _SEITEN[seite]
            # Das Tempo des Wagens an dieser Stelle, mit seiner Drehung.
            v_lok = geschw_lok + pygame.Vector2(-self.gier * lok.y, self.gier * lok.x)
            vn = v_lok.dot(n)
            if vn <= 0.0:
                continue
            nw = n.rotate(self.winkel)
            k = self.fahrer
            freund = k is not None and getattr(a, "fraktion", None) == k.fraktion
            if (seite == "vorn" and vn > f["ramm_schwelle"] and k is not None
                    and not freund and not getattr(a, "am_boden", False)
                    and self._sperre.get(id(a), 0.0) <= 0.0):
                self._sperre[id(a)] = r_["sperre"]
                if abs(lok.y) > 0.5:
                    seite_y = 1 if lok.y > 0 else -1
                else:
                    seite_y = RND.choice((-1, 1))
                quer = pygame.Vector2(0, seite_y * (0.45 + 0.6 * abs(lok.y) / f["halb"]))
                stoss = (nw + quer.rotate(self.winkel)) * (vn * f["ramm_stoss"] + f["ramm_extra"])
                lebte = a.lebt
                schaden_an(a, (vn - f["ramm_schwelle"]) * f["ramm_je_px"], stoss, k, "ramm",
                           self.pos)
                abschuss_buchen(k, a, "rammen", lebte)
                if lebte and not a.lebt and getattr(a, "bild", None):
                    dauer = min(r_["flug_lang"], r_["flug_kurz"] + stoss.length() * r_["flug_je_tempo"])
                    dreh = RND.uniform(-r_["flug_dreh"], r_["flug_dreh"]) \
                        * min(1.0, stoss.length() / 200.0)
                    w.leichenflug(a.pos, a.ebene, a.bild, a.winkel, stoss, dauer, dreh,
                                  tod_blut(a), a.radius)
                w.klang("rammen", min(1.0, 0.4 + vn / 250.0), a.pos, a.ebene)
                w.ruckeln(min(r_["wackeln"], 0.5 + vn / 80.0), "sturz", self.pos,
                          self.ebene, k)
            elif not getattr(a, "am_boden", False):
                t = getattr(a, "tempo", None)
                if t is not None and t.dot(nw) < vn:
                    t += nw * (vn - max(0.0, t.dot(nw)))

    # ---- Zeichnen -----------------------------------------------------
    def _wanne_flaeche(self, bilder):
        from .art_fahrzeuge import wanne_bild
        if self.kaputt:
            return bilder.gedreht(self.bild, self.winkel)
        return wanne_bild(bilder, self.art, self.winkel, self.ph_links, self.ph_rechts,
                          self._unscharf())

    def _unscharf(self) -> bool:
        return False

    def _mitte_bild(self, p) -> tuple:
        """Die Bildmitte auf ganzen Pixeln, samt Ruck nach dem Schuss.

        GRUND: Wanne und Aufbau werden getrennt gezeichnet. Rundet jeder
        fuer sich, zittert der Turm gegen die Wanne (Stolperfalle 2 im
        Paket). Der Aufbau setzt sich deshalb auf diese gerundete Mitte."""
        ruck = pygame.Vector2(self.ruck, 0).rotate(self.winkel)
        return (round(p.x - ruck.x), round(p.y - ruck.y))

    def zeichnen_unten(self, renderer, ziel, p, dunkel=None) -> None:
        """Schatten und Wanne - vor allen Figuren."""
        bilder = renderer.bilder
        hx, hy = self._mitte_bild(p)
        sch = bilder.gedreht("%s_schatten" % self.art, self.winkel)
        ziel.blit(sch, sch.get_rect(center=(hx + 3, hy + 4)))
        s = self._wanne_flaeche(bilder)
        if dunkel is not None:
            s = renderer.dunkel(s, dunkel)
        elif self.blitz > 0:
            s = s.copy()
            s.fill((140, 140, 140), special_flags=pygame.BLEND_RGB_ADD)
        ziel.blit(s, s.get_rect(center=(hx, hy)))

    def zeichnen_oben(self, renderer, ziel, p, dunkel=None) -> None:
        """Turm bzw. Ring - nach allen Figuren: Rohr und MG liegen ueber
        dem, der davor steht."""
        if self.kaputt:
            return
        from .art_fahrzeuge import aufbau_bild
        hx, hy = self._mitte_bild(p)
        # Der Versatz dreht mit dem Winkel, auf den auch das Bild gerastert
        # wird (3 Grad), und liegt auf ganzen Pixeln.
        raster = int(round(self.winkel / 3.0)) * 3
        versatz = self.aufbau_mitte(pygame.Vector2(0, 0), raster)
        s = aufbau_bild(renderer.bilder, self.aufbau_bild_name(), self.aufbau, self.ruecklauf)
        if dunkel is not None:
            s = renderer.dunkel(s, dunkel)
        elif self.blitz > 0:
            s = s.copy()
            s.fill((140, 140, 140), special_flags=pygame.BLEND_RGB_ADD)
        ziel.blit(s, s.get_rect(center=(hx + round(versatz.x), hy + round(versatz.y))))

    # ---- Beim Gast ------------------------------------------------------
    def staub_gast(self, dt: float) -> None:
        """Ketten, Spuren, Staub und Wrackqualm aus dem gemeldeten Tempo."""
        self._ketten(dt)
        self._abklingen(dt)
        super().staub_gast(dt)

    def zuruecksetzen(self) -> None:
        super().zuruecksetzen()
        self.aufbau = self.winkel
        self.ruecklauf = self.ruck = 0.0
        self.takt = {}
        self._sperre = {}


class Panzer(Schwer):
    """Kettenfahrzeug: dreht auf der Stelle, driftet nicht, langsam. Turm
    mit Kanone (linke Maustaste), fest eingebautes Bug-MG in Fahrtrichtung
    (rechte Maustaste)."""

    art = "panzer"
    werte = K.PANZER
    aufbau_name = "panzer_turm"

    @property
    def aufbau_dreh(self) -> float:
        return self.werte["turm_dreh"]

    def aufbau_mitte(self, pos=None, winkel=None) -> pygame.Vector2:
        pos = self.pos if pos is None else pos
        winkel = self.winkel if winkel is None else winkel
        return pos + pygame.Vector2(self.werte["turm_vor"], 0).rotate(winkel)

    @property
    def kanone_rest(self) -> float:
        return self.takt.get("kanone", 0.0)

    def _physik(self, dt: float, gas: float, lenk: float, handbremse: bool) -> None:
        """Kein Einspurmodell: Vorwaerts- und Drehtempo naehern sich dem,
        was die Tasten wollen. Seitlich rutscht nichts."""
        f = self.werte
        vorn = self.vorn
        vx = self.geschw.dot(vorn)
        if gas > 0.0:
            soll = f["hoechst"] * gas
        elif gas < 0.0:
            soll = f["rueckwaerts"] * gas
        else:
            soll = 0.0
        if soll == 0.0:
            rate = f["rollen"]
        elif soll * vx < 0.0:
            rate = f["bremse"]
        else:
            rate = f["beschleunigung"] if abs(soll) > abs(vx) else f["rollen"]
        vx = naehern(vx, soll, rate * dt)
        self.geschw = vorn * vx
        dreh = f["drehen"] * (1.0 - (1.0 - f["drehen_fahrt"])
                              * min(1.0, abs(vx) / f["hoechst"]))
        self.gier = naehern(self.gier, math.radians(lenk * dreh),
                            math.radians(f["dreh_beschl"]) * dt)
        self.lenkwinkel = 0.0
        self.rutschen = 0.0

    def _drehen(self, dt: float) -> None:
        neu = (self.winkel + math.degrees(self.gier * dt) + 180.0) % 360.0 - 180.0
        if self.passt(self.pos, neu):
            self.winkel = neu
        else:
            self.gier = 0.0

    def _ketten(self, dt: float) -> None:
        """Phase += Weg der Kettenseite / Teilung. In der Kurve laeuft die
        aeussere Kette schneller, auf der Stelle laufen beide gegeneinander."""
        f = self.werte
        vx = self.geschw.dot(self.vorn)
        quer = self.gier * f["ketten_abstand"]
        self.ph_links = (self.ph_links + (vx + quer) * dt / f["kette_teilung"]) % 1.0
        self.ph_rechts = (self.ph_rechts + (vx - quer) * dt / f["kette_teilung"]) % 1.0

    def _staub(self, dt: float) -> None:
        """Kein Fahrstaub wie beim Buggy - er ist zu langsam dafuer."""

    def _quietschen(self, dt: float) -> None:
        """Ketten quietschen nicht im Sand."""

    def _spuren(self) -> None:
        """Kettenspuren: zwei Baender im Sand, solange er sich bewegt - auch
        beim Drehen auf der Stelle."""
        f = self.werte
        if self.welt is None:
            return
        vx = self.geschw.dot(self.vorn)
        self._spur_weg += (abs(vx) + abs(self.gier) * f["ketten_abstand"]) * K.FIXED_DT
        if self._spur_weg < f["spur_abstand"]:
            return
        self._spur_weg = 0.0
        ebene = self.welt.ebene(self.ebene)
        vorn = self.vorn
        quer = pygame.Vector2(-vorn.y, vorn.x)
        punkt = _spurpunkt(f["spur_deckkraft"])
        for sy in (-1, 1):
            for x in (f["hinten"] * 0.75, f["vorn"] * 0.75):
                q = self.pos + vorn * x + quer * (sy * f["ketten_abstand"])
                ebene.dekal(punkt, q.x - 1, q.y - 1)

    def _schiessen(self) -> None:
        if self.feuer and self.takt.get("kanone", 0.0) <= 0.0:
            self._kanone()
        if self.zweit and self.takt.get("bug_mg", 0.0) <= 0.0:
            f = self.werte
            m = self.pos + pygame.Vector2(f["bug_mg"]).rotate(self.winkel)
            self._mg("bug_mg", m, self.winkel,
                     m - pygame.Vector2(8, 0).rotate(self.winkel))

    def _kanone(self) -> None:
        """Ein Schuss aus der Kanone: Granate, Rohrruecklauf, die Wanne
        ruckt zurueck, die Kamera wackelt. Der Staub am Boden vor der
        Muendung kommt mit dem Knall (Welt.schussknall) - auch beim Gast."""
        f = self.werte
        d = K.FAHRZEUG_WAFFEN[f.get("kanone", "kanone")]
        self.takt["kanone"] = d["takt"]
        mitte = self.aufbau_mitte()
        m = mitte + pygame.Vector2(f["muendung"] - self.ruecklauf, 0).rotate(self.aufbau)
        self.welt.dazu(Panzergranate(m, self.aufbau, d, self.ebene, self.fahrer,
                                     "kanone", self))
        self.ruecklauf = f["ruecklauf"]
        self.ruck = f["ruck"]
        self.welt.schussknall(m, self.aufbau, self.ebene, "kanone", self.fahrer)
        if hasattr(self.fahrer, "zaehlen"):
            self.fahrer.zaehlen("schuesse", 1.0, "kanone")


class Panzerwagen(Schwer):
    """Drei Achsen, Keilramme und ein MG-Ring auf dem Dach. Faehrt mit dem
    Einspurmodell des Buggys und seinen eigenen Werten: zieht zaeh an, wird
    sehr schnell, lenkt sehr schlecht."""

    art = "panzerwagen"
    werte = K.PANZERWAGEN
    aufbau_name = "panzerwagen_ring"

    @property
    def mitfahrer(self) -> list:
        """Wer hinten aufgesessen ist (seit 0.34.95, Truppentransporter).
        Beim Gast steht hier nichts; er kennt nur die Zahl (`besetzt_mit`)."""
        liste = self.__dict__.get("_mitfahrer")
        if liste is None:
            liste = self._mitfahrer = []
        return liste

    @property
    def aufbau_dreh(self) -> float:
        return self.werte["ring_dreh"]

    def aufbau_mitte(self, pos=None, winkel=None) -> pygame.Vector2:
        pos = self.pos if pos is None else pos
        winkel = self.winkel if winkel is None else winkel
        return pos + pygame.Vector2(self.werte["ring"]).rotate(winkel)

    def _abklingen(self, dt: float) -> None:
        self.ruecklauf = max(0.0, self.ruecklauf - self.werte["ring_ruecklauf_tempo"] * dt)

    def _ketten(self, dt: float) -> None:
        vx = self.geschw.dot(self.vorn)
        self.ph_links = (self.ph_links + vx * dt / self.werte["reifen_teilung"]) % 1.0
        self.ph_rechts = self.ph_links

    def _unscharf(self) -> bool:
        return abs(self.fahrt) > self.werte["unscharf_ab"]

    def _radstellen(self) -> list:
        f = self.werte
        vorn = self.vorn
        quer = pygame.Vector2(-vorn.y, vorn.x)
        hinten, vorne = -26.6, 25.2
        a = f["reifen_abstand"]
        return [self.pos + vorn * hinten - quer * a, self.pos + vorn * hinten + quer * a,
                self.pos + vorn * vorne - quer * a, self.pos + vorn * vorne + quer * a]

    def _schiessen(self) -> None:
        if self.feuer and self.takt.get("ring_mg", 0.0) <= 0.0:
            f = self.werte
            mitte = self.aufbau_mitte()
            m = mitte + pygame.Vector2(f["ring_muendung"] - self.ruecklauf, 0).rotate(self.aufbau)
            self._mg("ring_mg", m, self.aufbau,
                     mitte + pygame.Vector2(8, 3).rotate(self.aufbau))
            self.ruecklauf = f["ring_ruecklauf"]


class Krad(Buggy):
    """Motorrad mit Beiwagen (seit 0.34.107): faehrt wie der Buggy, nur
    leichter und schneller, und ohne jeden Schutz - was trifft, trifft auch
    die beiden, die darauf sitzen. Der Fahrer hat keine Waffe; im Beiwagen
    sitzt einer mit E auf (wie hinten auf dem Panzerwagen) und schiesst mit
    seiner eigenen Waffe. Beide verlieren das Leben, das der Wagen verliert."""

    art = "krad"
    werte = K.KRAD
    schatten_bild = "krad_schatten"
    besetzt_mit = 0                # beim Gast: wie viele im Beiwagen sitzen

    @property
    def mitfahrer(self) -> list:
        """Wer im Beiwagen sitzt. Beim Gast steht hier nichts; er kennt nur
        die Zahl (`besetzt_mit`)."""
        liste = self.__dict__.get("_mitfahrer")
        if liste is None:
            liste = self._mitfahrer = []
        return liste

    @property
    def fahrer_anteil(self) -> float:
        return float(self.werte["fahrer_anteil"])

    @property
    def bild(self) -> str:
        if self.kaputt:
            return "krad_wrack"
        zwei = bool(self.mitfahrer) if not self.nur_bild else self.besetzt_mit > 0
        return self._insassen_bild("krad_beiwagen" if zwei else "krad")

    def schaden(self, menge, schub=None, von=None, kugel: bool = False,
                art=None, herkunft=None) -> None:
        """Wie beim Buggy, und der Beifahrer bekommt es auch (der Fahrer
        wird in Buggy.schaden bedient). Die eigenen Leute verletzen einander
        nicht."""
        if not (self.kaputt or self.nur_bild or not self.lebt) and float(menge) > 0.0:
            for k in list(self.__dict__.get("_mitfahrer") or ()):
                if (k.lebt and von is not k
                        and (von is None or getattr(von, "fraktion", None) != k.fraktion)):
                    k.schaden(float(menge), None, von)
        super().schaden(menge, schub, von, kugel, art, herkunft)

    def zuruecksetzen(self) -> None:
        super().zuruecksetzen()
        self.__dict__.pop("_mitfahrer", None)


def seite_von(b):
    """Zu welcher Seite ein Fahrzeug gehoert: der Fahrer, sonst die Basis, aus
    der es kam (Nachschub und Basisfahrzeuge setzen `basis_team`). None:
    unbekannt - dann gilt es fuer jede Seite."""
    if b.fahrer is not None:
        return getattr(b.fahrer, "fraktion", None)
    team = getattr(b, "basis_team", None)
    return "team%d" % team if team is not None and team >= 0 else None


class Trosswagen(Buggy):
    """Munition, Medkits und Reparatur fuer die Front (seit 0.34.108,
    K.TROSSWAGEN). Fahren wie der Panzerwagen, nur langsamer. Aufsitzen kann
    niemand; wer HINTEN dransteht (die Zone `zone` hinter dem Wagen), holt
    sich mit E Munition und ein Medkit (`nachschub` Mal je Wagen, siehe
    Gefecht._nachschub_nehmen), und eigene Fahrzeuge in der Zone werden
    repariert, solange der Vorrat reicht - auch im Stehen. Der Fahrer sitzt
    unter dem Verdeck: das Bild zeigt ihn nicht."""

    art = "trosswagen"
    werte = K.TROSSWAGEN
    schatten_bild = "trosswagen_schatten"

    def __init__(self, pos, ebene: int = 0, winkel: float = 0.0,
                 nur_bild: bool = False) -> None:
        super().__init__(pos, ebene, winkel, nur_bild)
        self.nachschub = int(self.werte["entnahmen"])      # beim Gast: gemeldet
        self.reparatur = float(self.werte["reparatur"]["vorrat"])
        self._entnommen: dict = {}                         # Kaempfer -> Zeit der letzten Entnahme

    @property
    def bild(self) -> str:
        return "trosswagen_wrack" if self.kaputt else "trosswagen"

    def zone_mitte(self, pos=None, winkel=None) -> pygame.Vector2:
        """Die Mitte der Zone hinter dem Wagen, in der man Nachschub holt."""
        pos = self.pos if pos is None else pos
        winkel = self.winkel if winkel is None else winkel
        return pos - pygame.Vector2(self.werte["zone"]["abstand"], 0).rotate(winkel)

    def in_zone(self, punkt, radius: float = 0.0) -> bool:
        return self.zone_mitte().distance_to(punkt) <= self.werte["zone"]["radius"] + radius

    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        if self.nur_bild or self.welt is None or self.kaputt:
            return
        if self.reparatur > 0.0 and self.emp_rest <= 0.0:
            self._reparieren(dt)

    def _reparieren(self, dt: float) -> None:
        """Eigene Fahrzeuge in der Zone bekommen Leben, solange der Vorrat reicht."""
        w = self.welt
        r = self.werte["zone"]["radius"]
        mitte = self.zone_mitte()
        meine = seite_von(self)
        je = float(self.werte["reparatur"]["je_sekunde"]) * dt
        for a in w.nahe(mitte, r + 70.0, self.ebene):
            if (a is self or not getattr(a, "ist_fahrzeug", False) or not a.lebt or a.kaputt
                    or getattr(a, "nur_bild", False) or a.leben >= a.max_leben):
                continue
            if a.pos.distance_to(mitte) > r:
                continue
            seite = seite_von(a)
            if meine is not None and seite is not None and meine != seite:
                continue
            gut = min(je, a.max_leben - a.leben, self.reparatur)
            a.leben += gut
            self.reparatur -= gut
            if self.reparatur <= 0.0:
                break

    def zuruecksetzen(self) -> None:
        super().zuruecksetzen()
        self.nachschub = int(self.werte["entnahmen"])
        self.reparatur = float(self.werte["reparatur"]["vorrat"])
        self._entnommen = {}


class Spulenwagen(Buggy):
    """Erbeutete Chor-Technik (seit 0.34.110, K.SPULENWAGEN). Linke
    Maustaste: ein schwacher Kettenblitz vom Wagen zum Zeiger. Rechte: das
    EMP-Feld - der Wagen muss dafuer stehen und aufgebaut werden, dann
    pulsiert es am Ort (alle `takt` Sekunden legt ein Puls jedes fremde
    Fahrzeug im Kreis still), aber nur `dauer` Sekunden lang; danach laedt
    er. Eigene Fahrzeuge bleiben verschont.

    Phasen: 0 bereit, 1 baut auf, 2 Feld aktiv, 3 laedt. In 1 und 2 steht er."""

    art = "spulenwagen"
    werte = K.SPULENWAGEN
    schatten_bild = "spulenwagen_schatten"
    schiesst = True            # die Maustasten des Fahrers gelten (mehrspieler._fahren)

    def __init__(self, pos, ebene: int = 0, winkel: float = 0.0,
                 nur_bild: bool = False) -> None:
        super().__init__(pos, ebene, winkel, nur_bild)
        self.feuer = False
        self.zweit = False
        self.takt: dict = {}
        self.phase = 0
        self.phase_rest = 0.0      # Sekunden bis zur naechsten Phase (beim Gast gemeldet)
        self._zweit_alt = False
        self._puls_rest = 0.0

    @property
    def bild(self) -> str:
        if self.kaputt:
            return "spulenwagen_wrack"
        return "spulenwagen_aktiv" if self.phase == 2 else "spulenwagen"

    def spule_mitte(self, pos=None, winkel=None) -> pygame.Vector2:
        """Wo die Spule sitzt: von hier gehen Blitz und Puls aus."""
        pos = self.pos if pos is None else pos
        winkel = self.winkel if winkel is None else winkel
        return pos + pygame.Vector2(self.werte["spule"]).rotate(winkel)

    def schritt(self, dt: float) -> None:
        if not (self.nur_bild or self.welt is None) and self.phase in (1, 2):
            self.gas = self.lenk = 0.0          # aufgebaut steht er
            self.handbremse = True
        super().schritt(dt)
        if self.nur_bild or self.welt is None or self.kaputt:
            return
        for k in list(self.takt):
            self.takt[k] = max(0.0, self.takt[k] - dt)
        if self.emp_rest > 0.0:
            return
        self._phasen(dt)
        if self.feuer and self.fahrer is not None and self.takt.get("blitz", 0.0) <= 0.0:
            self._blitz()

    # ---- Das Feld ----------------------------------------------------
    def _phasen(self, dt: float) -> None:
        f = self.werte["feld"]
        druck = self.zweit and not self._zweit_alt
        self._zweit_alt = self.zweit
        if self.phase == 0 and druck and self.fahrer is not None \
                and self.geschw.length() <= f["stillstand"]:
            self.phase, self.phase_rest = 1, f["aufbau"]
            self.welt.klang("aufheben", 0.8, self.pos, self.ebene)
        elif self.phase == 1 and druck:
            self.phase, self.phase_rest = 0, 0.0              # abgebrochen, kostet nichts
        elif self.phase == 2 and druck:
            benutzt = 1.0 - self.phase_rest / f["dauer"]       # frueh aus: kuerzer laden
            self.phase, self.phase_rest = 3, max(4.0, f["laden"] * benutzt)
        elif self.phase == 1:
            self.phase_rest -= dt
            if self.phase_rest <= 0.0:
                self.phase, self.phase_rest, self._puls_rest = 2, f["dauer"], 0.0
        elif self.phase == 2:
            self.phase_rest -= dt
            self._puls_rest -= dt
            if self._puls_rest <= 0.0:
                self._puls_rest = f["takt"]
                self._puls()
            if self.phase_rest <= 0.0:
                self.phase, self.phase_rest = 3, f["laden"]
        elif self.phase == 3:
            self.phase_rest -= dt
            if self.phase_rest <= 0.0:
                self.phase, self.phase_rest = 0, 0.0

    def _puls(self) -> None:
        """Ein Puls: jedes fremde Fahrzeug (und jede Technik) im Kreis steht still."""
        f = self.werte["feld"]
        w = self.welt
        mitte = self.spule_mitte()
        meine = seite_von(self)
        for b in list(w.nahe(mitte, f["radius"] + 80.0, self.ebene)):
            if b is self or not b.lebt:
                continue
            if getattr(b, "ist_fahrzeug", False):
                s = seite_von(b)
                if b.kaputt or (meine is not None and s == meine):
                    continue
                if b.beruehrt(mitte, f["radius"]):
                    b.emp_treffen(f["emp"])
            elif (getattr(b, "technik", False) and getattr(b, "fraktion", None) != getattr(self.fahrer, "fraktion", "-")
                  and b.pos.distance_to(mitte) <= f["radius"] + b.radius):
                b.emp_treffen(f["emp"])
        w.explosion(mitte, self.ebene, f["radius"], "emp")

    # ---- Der Blitz ---------------------------------------------------
    def _blitz(self) -> None:
        """Der erste im Kegel zum Zeiger, dann von Koerper zu Koerper, jedes
        Mal schwaecher (wie der Kettenblitz zu Fuss, nur schwaecher)."""
        d = self.werte["blitz"]
        k = self.fahrer
        ziel = getattr(k, "ziel", None)
        if ziel is None:
            return
        mitte = self.spule_mitte()
        zu = pygame.Vector2(ziel) - mitte
        if zu.length_squared() < 4.0:
            return
        winkel = math.degrees(math.atan2(zu.y, zu.x))
        self.takt["blitz"] = d["takt"]
        w = self.welt
        meine = seite_von(self)
        punkte = [pygame.Vector2(mitte)]
        getroffen = []
        jetzt = pygame.Vector2(mitte)
        menge = d["schaden"]
        for sprung in range(d["spruenge"] + 1):
            bestes, beste_weite = None, 1e9
            weite_max = d["reichweite"] if sprung == 0 else d["sprung"]
            for z in w.nahe(jetzt, weite_max + 40.0, self.ebene):
                if (z is self or not z.lebt or z in getroffen
                        or getattr(z, "fraktion", "") in ("geschoss", k.fraktion)
                        or not getattr(z, "trefferbar", True)
                        or getattr(z, "im_fahrzeug", False)):
                    continue
                if getattr(z, "ist_fahrzeug", False) and meine is not None and seite_von(z) == meine:
                    continue
                ab = z.pos - jetzt
                weit = ab.length()
                if weit > weite_max + z.radius or weit >= beste_weite:
                    continue
                if sprung == 0:
                    delta = (math.degrees(math.atan2(ab.y, ab.x)) - winkel + 180) % 360 - 180
                    if abs(delta) > d["kegel"]:
                        continue
                if not w.sicht_frei(jetzt, z.pos, self.ebene):
                    continue
                bestes, beste_weite = z, weit
            if bestes is None:
                break
            lebte = bestes.lebt
            schaden_an(bestes, menge, None, k, d["schadensart"], jetzt)
            abschuss_buchen(k, bestes, "kettenblitz", lebte)
            getroffen.append(bestes)
            jetzt = pygame.Vector2(bestes.pos)
            punkte.append(jetzt)
            menge *= d["abfall"]
        if len(punkte) == 1:
            punkte.append(w.strahl(mitte, pygame.Vector2(1, 0).rotate(winkel),
                                   d["reichweite"] * 0.6, self.ebene))
        w.entladung(punkte, self.ebene, "blitz")

    def zuruecksetzen(self) -> None:
        super().zuruecksetzen()
        self.phase, self.phase_rest, self._puls_rest = 0, 0.0, 0.0
        self.takt = {}
        self.feuer = self.zweit = self._zweit_alt = False


class Aufbauwagen(Buggy):
    """Ein Wagen, den man aufbauen muss, bevor er wirkt (seit 0.34.111:
    Funkwagen, Werfer): die rechte Maustaste baut auf - nur im Stand, dauert
    `aufbau` Sekunden, und er steht dabei und danach. Noch einmal gedrueckt
    baut er wieder ab. Phasen: 0 faehrt, 1 baut auf, 2 aufgebaut."""

    schiesst = True            # die Maustasten des Fahrers gelten (mehrspieler._fahren)

    def __init__(self, pos, ebene: int = 0, winkel: float = 0.0,
                 nur_bild: bool = False) -> None:
        super().__init__(pos, ebene, winkel, nur_bild)
        self.feuer = False
        self.zweit = False
        self.takt: dict = {}
        self.phase = 0
        self.phase_rest = 0.0      # beim Gast gemeldet
        self._zweit_alt = False

    @property
    def aufgebaut(self) -> bool:
        return self.phase == 2 and not self.kaputt

    def schritt(self, dt: float) -> None:
        if not (self.nur_bild or self.welt is None) and self.phase in (1, 2):
            self.gas = self.lenk = 0.0
            self.handbremse = True
        super().schritt(dt)
        if self.nur_bild or self.welt is None or self.kaputt:
            return
        for k in list(self.takt):
            self.takt[k] = max(0.0, self.takt[k] - dt)
        if self.emp_rest > 0.0:
            return
        self._aufbauen(dt)

    def _aufbauen(self, dt: float) -> None:
        druck = self.zweit and not self._zweit_alt
        self._zweit_alt = self.zweit
        if self.phase == 0 and druck and self.fahrer is not None \
                and self.geschw.length() <= self.werte["stillstand"]:
            self.phase, self.phase_rest = 1, self.werte["aufbau"]
            self.welt.klang("aufheben", 0.8, self.pos, self.ebene)
        elif self.phase in (1, 2) and druck:
            self.phase, self.phase_rest = 0, 0.0
            self.welt.klang("aufheben", 0.6, self.pos, self.ebene)
        elif self.phase == 1:
            self.phase_rest -= dt
            if self.phase_rest <= 0.0:
                self.phase, self.phase_rest = 2, 0.0

    def netz_extra(self):
        """Ein Zusatzwert fuer die Fahrzeugmeldung (Feld 20): Betriebsart,
        Einschlaege ... - was die Art braucht."""
        return 0

    def netz_extra_setzen(self, wert) -> None:
        pass

    def zuruecksetzen(self) -> None:
        super().zuruecksetzen()
        self.phase, self.phase_rest = 0, 0.0
        self.takt = {}
        self.feuer = self.zweit = self._zweit_alt = False


class Funkwagen(Aufbauwagen):
    """Mast und Peilrahmen (seit 0.34.111, K.FUNKWAGEN). Betriebsart 0 PEILEN
    oder 1 STOEREN (R); was sie bewirken, rechnet das Gefecht
    (mehrspieler.Gefecht.funkwagen_schritt) - hier steht nur der Zustand."""

    art = "funkwagen"
    werte = K.FUNKWAGEN
    schatten_bild = "funkwagen_schatten"

    def __init__(self, pos, ebene: int = 0, winkel: float = 0.0,
                 nur_bild: bool = False) -> None:
        super().__init__(pos, ebene, winkel, nur_bild)
        self.modus = 0
        self._wirk_rest = 0.0

    @property
    def bild(self) -> str:
        if self.kaputt:
            return "funkwagen_wrack"
        if self.phase != 2:
            return "funkwagen"
        zeit = self.welt.zeit if self.welt is not None else 0.0
        return "funkwagen_aktiv_%d" % (int(zeit * self.werte["drehen"] * 4) % 4)

    def mast_mitte(self, pos=None, winkel=None) -> pygame.Vector2:
        pos = self.pos if pos is None else pos
        winkel = self.winkel if winkel is None else winkel
        return pos + pygame.Vector2(self.werte["mast"]).rotate(winkel)

    @property
    def radius_wirkung(self) -> float:
        return self.werte["stoeren"] if self.modus == 1 else self.werte["peilen"]

    def modus_wechseln(self) -> None:
        if not self.kaputt and self.emp_rest <= 0.0:
            self.modus = 1 - self.modus
            if self.welt is not None:
                self.welt.klang("aufheben", 0.5, self.pos, self.ebene)

    def netz_extra(self):
        """[Betriebsart, Basis-Team]: der Gast braucht auch die Seite eines
        Wagens ohne Fahrer (Abwurf), um seine Minikarte zu stoeren (0.34.115)."""
        bt = getattr(self, "basis_team", None)
        return [self.modus, bt if bt is not None and bt >= 0 else -1]

    def netz_extra_setzen(self, wert) -> None:
        try:
            if isinstance(wert, (list, tuple)):
                self.modus = 1 if int(wert[0]) == 1 else 0
                self.basis_team = int(wert[1]) if len(wert) > 1 else -1
            else:
                self.modus = 1 if int(wert) == 1 else 0
        except (TypeError, ValueError, IndexError):
            self.modus = 0

    def zuruecksetzen(self) -> None:
        super().zuruecksetzen()
        self.modus = 0
        self._wirk_rest = 0.0


class Werfer(Aufbauwagen):
    """Steilfeuer (seit 0.34.112, K.WERFER): aufgebaut schiesst die linke
    Maustaste eine Salve Raketen auf einen Punkt, an dem die eigene Seite ein
    gueltiges Ziel hat (Gefecht.werfer_pruefen). Hier steht der Zustand: die
    Raketen in der Luft (`einschlaege`: [Restzeit, x, y, gestartet]), ob eine
    Salve bereit ist, ob das Ziel unter dem Zeiger gilt (`ziel_grund`: 0 ja,
    1 zu nah, 2 zu weit, 3 kein Ziel) und wohin das Gestell zeigt. Sehr
    leicht zerstoert - dann eine grosse Explosion."""

    art = "werfer"
    werte = K.WERFER
    schatten_bild = "werfer_schatten"
    explosion_art = "c4"

    def __init__(self, pos, ebene: int = 0, winkel: float = 0.0,
                 nur_bild: bool = False) -> None:
        super().__init__(pos, ebene, winkel, nur_bild)
        self.einschlaege: list = []
        self.bereit = False
        self.ziel_grund = 3
        self.rohr_stufe = 0          # Gestell in 30-Grad-Stufen von der Fahrtrichtung weg

    @property
    def bild(self) -> str:
        if self.kaputt:
            return "werfer_wrack"
        return "werfer_aufgebaut_%d" % self.rohr_stufe if self.phase == 2 else "werfer"

    def rohr_mitte(self, pos=None, winkel=None) -> pygame.Vector2:
        pos = self.pos if pos is None else pos
        winkel = self.winkel if winkel is None else winkel
        return pos + pygame.Vector2(self.werte["rohr"]).rotate(winkel)

    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        if self.nur_bild or self.welt is None or self.kaputt:
            return
        k = self.fahrer
        ziel = getattr(k, "ziel", None) if k is not None else None
        if self.phase == 2 and ziel is not None:
            d = pygame.Vector2(ziel) - self.rohr_mitte()
            if d.length_squared() > 16.0:
                rel = math.degrees(math.atan2(d.y, d.x)) - self.winkel
                self.rohr_stufe = int(round(rel / 30.0)) % 12

    def netz_extra(self):
        return [int(self.bereit), self.ziel_grund, self.rohr_stufe,
                [[round(e[0], 1), int(e[1]), int(e[2])] for e in self.einschlaege[:12]]]

    def netz_extra_setzen(self, wert) -> None:
        try:
            self.bereit = bool(int(wert[0]))
            self.ziel_grund = max(0, min(3, int(wert[1])))
            self.rohr_stufe = int(wert[2]) % 12
            self.einschlaege = [[max(0.0, min(30.0, float(e[0]))), float(e[1]), float(e[2]),
                                 float(e[0]) <= K.WERFER["salve"]["flug"]]
                                for e in wert[3][:12]]
        except (TypeError, ValueError, IndexError):
            self.einschlaege = []

    def zuruecksetzen(self) -> None:
        super().zuruecksetzen()
        self.einschlaege = []
        self.bereit = False
        self.ziel_grund = 3


class Tragschrauber(Buggy):
    """Fliegt (seit 0.34.113, K.TRAGSCHRAUBER). Am Boden ein kleiner Wagen; ab
    `abheben` px/s hebt er ab und fliegt ueber alles - Mauern, Felsen, Loecher
    -, mit mindestens `flug_min` (stehen geht nicht). E setzt zur Landung an;
    wo er aufsetzt, muss Platz sein, sonst stuerzt er ab. In der Luft ist er
    fuer Schuesse vom Boden unerreichbar - nur wer auf sein Bild zielt (luft.py)
    und Flak treffen ihn. Linke Maustaste wirft eine Bombe, er sieht die
    Gegner unter sich (Gefecht.tragschrauber_schritt)."""

    art = "tragschrauber"
    werte = K.TRAGSCHRAUBER
    schatten_bild = "tragschrauber_schatten"
    schiesst = True

    def __init__(self, pos, ebene: int = 0, winkel: float = 0.0,
                 nur_bild: bool = False) -> None:
        super().__init__(pos, ebene, winkel, nur_bild)
        self.feuer = False
        self.zweit = False
        self.takt: dict = {}
        self.luft = False              # fliegt er (oder setzt er gerade zur Landung an)?
        self.hoehe = 0.0               # Pixel ueber seinem Schatten, im Bild
        self.landen = False
        self.flug_v = 0.0
        self.bomben = int(self.werte["bomben"])
        self.bomben_fall: list = []    # [Restzeit, x, y]
        self._bomben_rest = 0.0
        self._feuer_alt = False
        self._aufkl_rest = 0.0

    @property
    def bild(self) -> str:
        if self.kaputt:
            return "tragschrauber_wrack"
        return self._insassen_bild("tragschrauber")

    @property
    def hoch_oben(self) -> bool:
        """Gezeichnet in der Schicht ueber allem (luft.py), solange er hoch ist."""
        return self.hoehe > 2.0 and not self.kaputt

    @property
    def in_der_luft(self) -> bool:
        return self.luft and self.hoehe > 10.0 and not self.kaputt

    def passt(self, pos, winkel=None) -> bool:
        if self.luft:
            return True
        return super().passt(pos, winkel)

    def _beiseite_schieben(self) -> None:
        if not self.luft:
            super()._beiseite_schieben()

    def schritt(self, dt: float) -> None:
        if self.luft and not self.nur_bild and self.welt is not None and not self.kaputt:
            Wesen.schritt(self, dt)
            self._fliegen(dt)
            self.trefferbar = not self.in_der_luft     # Bodenfeuer geht darunter durch
            return
        super().schritt(dt)
        self.trefferbar = True
        if self.nur_bild or self.welt is None or self.kaputt:
            return
        f = self.werte
        if (self.fahrer is not None and self.emp_rest <= 0.0 and self.fahrt >= f["abheben"]
                and not self.landen):
            self.luft = True                            # abgehoben
            self.flug_v = max(self.geschw.length(), f["abheben"])
            self.welt.klang("drohne", 0.7, self.pos, self.ebene)
        elif self.geschw.length() < 5.0 and self.bomben < f["bomben"]:
            self._bomben_rest -= dt
            if self._bomben_rest <= 0.0:
                self.bomben += 1
                self._bomben_rest = f["bomben_nachladen"]

    def _fliegen(self, dt: float) -> None:
        f = self.werte
        gas = self.gas if self.fahrer is not None and self.emp_rest <= 0.0 else 0.0
        if self.emp_rest > 0.0:
            self.emp_rest = max(0.0, self.emp_rest - dt)
            self.landen = True                          # kein Motor: runter
        ziel_v = f["flug_hoechst"] if gas > 0.3 else (f["flug_min"] if gas < -0.3 else f["flug_reise"])
        if self.landen:
            ziel_v = f["landen_tempo"]
        schritt = f["flug_beschl"] * dt
        self.flug_v += max(-schritt, min(schritt, ziel_v - self.flug_v))
        lenk = self.lenk if self.fahrer is not None else 0.0
        dreh = lenk * f["drehen"] * (0.45 + 0.55 * min(1.0, self.flug_v / f["flug_hoechst"]))
        self.winkel = (self.winkel + dreh * dt + 180.0) % 360.0 - 180.0
        self.pos += self.vorn * self.flug_v * dt
        e = self.welt.ebene(self.ebene)
        self.pos.x = max(8.0, min(e.pixel_breite - 8.0, self.pos.x))
        self.pos.y = max(8.0, min(e.pixel_hoehe - 8.0, self.pos.y))
        self.geschw = self.vorn * self.flug_v
        self.tempo.update(self.geschw)
        if self.landen:
            self.hoehe = max(0.0, self.hoehe - f["sinken"] * dt)
            if self.hoehe <= 0.0:
                self._aufsetzen()
        else:
            self.hoehe += (f["hoehe"] - self.hoehe) * min(1.0, f["steigen"] * dt)

    def landen_beginnen(self) -> None:
        if self.luft and not self.landen:
            self.landen = True

    def _aufsetzen(self) -> None:
        """Unten angekommen: ist Platz, rollt er aus, sonst Absturz."""
        self.hoehe = 0.0
        self.landen = False
        if Buggy.passt(self, self.pos):
            self.luft = False
            self.geschw = self.vorn * min(self.flug_v, self.werte["hoechst"] * 0.6)
            self.flug_v = 0.0
        else:
            self.luft = False
            self.schaden(self.leben + 1.0, None, None, art="ramm")

    def _zerstoeren(self, von) -> None:
        self.luft = self.landen = False
        self.hoehe = self.flug_v = 0.0
        super()._zerstoeren(von)

    def netz_extra(self):
        return [int(self.luft), int(self.hoehe), self.bomben,
                [[round(b[0], 1), int(b[1]), int(b[2])] for b in self.bomben_fall[:4]]]

    def netz_extra_setzen(self, wert) -> None:
        try:
            self.luft = bool(int(wert[0]))
            self.hoehe = max(0.0, min(200.0, float(wert[1])))
            self.bomben = max(0, min(9, int(wert[2])))
            self.bomben_fall = [[float(b[0]), float(b[1]), float(b[2])] for b in wert[3][:4]]
        except (TypeError, ValueError, IndexError):
            self.bomben_fall = []

    def zuruecksetzen(self) -> None:
        super().zuruecksetzen()
        self.luft = self.landen = False
        self.hoehe = self.flug_v = 0.0
        self.bomben = int(self.werte["bomben"])
        self.bomben_fall = []
        self.takt = {}
        self.feuer = self.zweit = self._feuer_alt = False


class Jagdpanzer(Panzer):
    """Ein Panzer ohne Turm (seit 0.34.107): die Kanone sitzt fest im Bug und
    schwenkt nur ein paar Grad (K.JAGDPANZER "schwenk"); wer mehr will, muss
    die Wanne drehen. Dafuer reicht sie weit (1 400 statt 900 Pixel), und die
    Front ist die dickste im Spiel (K.JAGDPANZER "seiten"). Kein Bug-MG: die
    rechte Maustaste ist das Zielfernrohr. Der drehende Teil (Rohr samt
    Kommandant) schwenkt um die Mitte der Wanne."""

    art = "jagdpanzer"
    werte = K.JAGDPANZER
    aufbau_name = "jagdpanzer_rohr"

    def _aufbau_fuehren(self, dt: float) -> None:
        """Das Rohr folgt dem Zeiger, aber nur im Schwenkbereich vor der Wanne."""
        k = self.fahrer
        ziel = getattr(k, "ziel", None) if k is not None else None
        soll = self.winkel
        if ziel is not None:
            d = pygame.Vector2(ziel) - self.aufbau_mitte()
            if d.length_squared() >= 16.0:
                bis = self.werte["schwenk"]
                rel = (math.degrees(math.atan2(d.y, d.x)) - self.winkel + 180.0) % 360.0 - 180.0
                soll = self.winkel + max(-bis, min(bis, rel))
        diff = (soll - self.aufbau + 180.0) % 360.0 - 180.0
        schritt = self.aufbau_dreh * dt
        self.aufbau = (self.aufbau + max(-schritt, min(schritt, diff)) + 180.0) % 360.0 - 180.0

    def _schiessen(self) -> None:
        if self.feuer and self.takt.get("kanone", 0.0) <= 0.0:
            self._kanone()


class Flakwagen(Panzerwagen):
    """Ein Panzerwagen mit einem Flak-Vierling statt des MG-Rings (seit
    0.34.114, K.FLAKWAGEN). Nur Bots fahren ihn (`nur_bot`). Wer darin sitzt,
    rastet mit dem Zeiger auf Luftziele ein (`flak`, luft.py) - auch auf
    solche, die sonst niemand trifft: Abwuerfe am Schirm und Fallschirmjaeger.
    Die vier Rohre schiessen reihum; am Boden ist er ein schwaches MG."""

    art = "flakwagen"
    werte = K.FLAKWAGEN
    aufbau_name = "flak_lafette"
    schatten_bild = "flakwagen_schatten"
    flak = True
    # Wo die vier Rohre sitzen (quer zur Lafette, Pixel).
    _ROHRE = (-12.2, 8.0, -8.0, 12.2)

    def _schiessen(self) -> None:
        if self.feuer and self.takt.get("flak_mg", 0.0) <= 0.0:
            f = self.werte
            mitte = self.aufbau_mitte()
            rohr = self.__dict__.get("_rohr", 0)
            self._rohr = (rohr + 1) % len(self._ROHRE)
            quer = self._ROHRE[rohr]
            m = mitte + pygame.Vector2(f["ring_muendung"] - self.ruecklauf, quer).rotate(self.aufbau)
            self._mg("flak_mg", m, self.aufbau,
                     mitte + pygame.Vector2(8, quer * 0.5).rotate(self.aufbau))
            self.ruecklauf = f["ring_ruecklauf"]


# Welche Art zu welcher Klasse und zu welchem Buchstaben in der Karte.
ARTEN = {"buggy": Buggy, "panzer": Panzer, "panzerwagen": Panzerwagen,
         "krad": Krad, "jagdpanzer": Jagdpanzer, "trosswagen": Trosswagen,
         "spulenwagen": Spulenwagen, "funkwagen": Funkwagen,
         "werfer": Werfer, "tragschrauber": Tragschrauber, "flakwagen": Flakwagen}


def marken() -> list:
    """(Buchstabe, Art) fuer jede Fahrzeugart, die eine Karte setzen kann."""
    return [(ARTEN[a].werte["marke"], a) for a in ("buggy", "panzer", "panzerwagen")]


def neu(art: str, pos, ebene: int = 0, winkel: float = 0.0, nur_bild: bool = False):
    """Ein Fahrzeug dieser Art. Unbekannt heisst Buggy - eine Meldung aus
    dem Netz soll nichts kaputt machen koennen."""
    return ARTEN.get(art, Buggy)(pygame.Vector2(pos), ebene, winkel, nur_bild)
