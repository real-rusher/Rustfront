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

import pygame

from . import config as K
from .entities import Wesen, wolke


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

    def __init__(self, pos, ebene: int = 0, winkel: float = 0.0,
                 nur_bild: bool = False) -> None:
        self.max_leben = K.FAHRZEUG["leben"]
        super().__init__(pos, ebene)
        f = K.FAHRZEUG
        self.radius = f["kreis"]
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
        if self.fahrer is not None:
            besetzt, team = True, getattr(self.fahrer, "team", -1)
        else:
            besetzt, team = self.besetzt, self.team
        if not besetzt:
            return "buggy"
        if 0 <= team < len(K.TEAMS["kombi"]):
            name = "buggy_%s_fahrer" % K.TEAMS["kombi"][team]["name"].lower()
            if name in K.BILD_MASS:
                return name
        return "buggy_fahrer"

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

    def schaden(self, menge, schub=None, von=None) -> None:
        """Ein Treffer am Wagen. Was drinsitzt, bekommt ihn auch - so wie
        bisher, als die Kugeln am Wagen vorbei auf den Fahrer gingen, nur
        dass jetzt auch das Blech etwas abbekommt. Die eigenen Leute treffen
        den Wagen, aber nicht den Fahrer: Freundfeuer gibt es sonst nicht.
        Weggestossen wird er nicht, `schub` bleibt ungenutzt."""
        if self.kaputt or self.nur_bild or not self.lebt:
            return
        menge = float(menge)
        if menge <= 0.0:
            return
        k = self.fahrer
        if (k is not None and k.lebt and von is not k
                and (von is None or getattr(von, "fraktion", None) != k.fraktion)):
            k.schaden(menge, None, von)
        self.leben -= menge
        self.blitz = K.TREFFER["blitz"]
        if self.leben <= 0.0:
            self._zerstoeren(von)

    def _zerstoeren(self, von) -> None:
        """Er geht hoch. Der Fahrer wird vom Gefecht herausgeholt
        (`kaputt` ist das Zeichen dafuer), alles im Umkreis bekommt
        Schaden."""
        f = K.FAHRZEUG
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
        w.explosion(self.pos, self.ebene, r, "spreng", von)
        w.klang("c4_explosion", 0.8, self.pos, self.ebene)
        for ding in list(w.nahe(self.pos, r + 30, self.ebene)):
            if (ding is self or ding is self.fahrer or not ding.lebt
                    or not getattr(ding, "trefferbar", False)):
                continue
            weit = self.pos.distance_to(ding.pos)
            if weit >= r:
                continue
            anteil = 1.0 - weit / r
            schub = ding.pos - self.pos
            if schub.length_squared() > 0.01:
                schub = schub.normalize() * 240 * anteil
            ding.schaden(f["explosion_schaden"] * anteil, schub, von)

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
        achse = pygame.Vector2(K.FAHRZEUG["achse"], 0).rotate(winkel)
        return (pos + achse, pos - achse)

    def beruehrt(self, pos, radius: float) -> bool:
        """Liegt ein Kreis an `pos` am Wagen an?"""
        grenze = (self.radius + radius) ** 2
        return any(c.distance_squared_to(pos) <= grenze for c in self.kreise())

    def passt(self, pos, winkel=None) -> bool:
        """Kann er hier stehen? Mauern, Loecher und alles Unverschiebbare
        (Zielpuppe, Koloss) halten ihn auf; Menschen und gewoehnliche
        Gegner nicht, die schiebt er beiseite."""
        w = self.welt
        if w is None:
            return True
        r = self.radius
        kreise = self.kreise(pos, winkel)
        for c in kreise:
            if not w.frei(c, r, self.ebene, True):
                return False
        for a in w.nahe(pos, K.FAHRZEUG["achse"] + r + 40, self.ebene):
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
        fahrer = self.fahrer is not None and not self.kaputt
        self._physik(dt, self.gas if fahrer else 0.0,
                     self.lenk if fahrer else 0.0,
                     bool(self.handbremse) and fahrer)
        # Drehen nur, wenn er danach noch passt - sonst klemmte er sich an
        # einer Mauer fest. Stattdessen verliert er die Drehung.
        neu = (self.winkel + math.degrees(self.gier * dt) + 180.0) % 360.0 - 180.0
        if self.passt(self.pos, neu):
            self.winkel = neu
        else:
            self.gier *= -0.2
        self._fahren(dt)
        self.tempo.update(self.geschw)
        self._beiseite_schieben()
        self._staub(dt)
        self._spuren()
        self._quietschen(dt)

    def stick_steuern(self, richtung) -> tuple:
        """(Gas, Lenkung) aus einer Richtung im Bild, fuer einen Stick.

        W/A/S/D auf einen Stick gelegt fuehlte sich falsch an (gemeldet):
        nach rechts gedrueckt lenkte er nach rechts *von sich aus*, also
        bei einem Wagen, der nach unten faehrt, im Bild nach links. Hier
        zeigt der Stick, wohin es gehen soll - wie beim Laufen. Er lenkt
        dorthin, gibt so viel Gas, wie weit der Stick gedrueckt ist, und
        wendet, wenn es hinter ihn geht. Fast genau entgegen bremst er,
        und steht er fast, faehrt er rueckwaerts."""
        f = K.FAHRZEUG
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

    def _physik(self, dt: float, gas: float, lenk: float, handbremse: bool) -> None:
        """Ein Schritt Einspurmodell: Kraefte an Vorder- und Hinterachse,
        daraus Beschleunigung und Drehung. Je Masse gerechnet."""
        f = K.FAHRZEUG
        vorn = self.vorn
        quer = pygame.Vector2(-vorn.y, vorn.x)        # rechts in Fahrtrichtung
        vx = self.geschw.dot(vorn)
        vy = self.geschw.dot(quer)
        tempo = self.geschw.length()

        # Lenkung: schnell, aber nicht sofort; bei Fahrt weniger Einschlag.
        # Dazu lenkt er einen Teil des Driftwinkels selbst gegen.
        lenk_max = math.radians(f["lenk_max"])
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
        f = K.FAHRZEUG
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
            w.klang("buggy_aufprall", 0.45 + 0.55 * staerke, self.pos, self.ebene)
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
        for a in list(w.nahe(self.pos, K.FAHRZEUG["achse"] + r + 40, self.ebene)):
            if (a is self.fahrer or a is self or not a.lebt or a.flug > 0
                    or not getattr(a, "schiebt", True)
                    or not getattr(a, "schiebbar", True)
                    or getattr(a, "am_boden", False)
                    or getattr(a, "im_fahrzeug", False)):
                continue
            for c in self.kreise():
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
        f = K.FAHRZEUG
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
        hinten = self.pos - vorn * 15
        richtung = math.degrees(math.atan2(-self.geschw.y, -self.geschw.x))
        menge = 1 + int(2 * min(1.0, tempo / f["hoechst"]))
        for seite in (-1, 1):
            wolke(self.welt, hinten + quer * (13 * seite), menge,
                  30 + 40 * tempo / f["hoechst"], 0.8, f["staub_farbe"],
                  self.ebene, f["staub_groesse"], "staub", 70, richtung, 2.5)

    def staub_gast(self, dt: float) -> None:
        """Beim Gast: derselbe Staub, dieselben Spuren - aus dem gemeldeten
        Tempo und Rutschen. Gequietscht wird beim Gastgeber (NETZKLAENGE)."""
        self._staub(dt)
        self._spuren()
        self.wrack_qualm(dt)

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
        f = K.FAHRZEUG
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
        f = K.FAHRZEUG
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

    def ausstiegsorte(self, radius: float) -> list:
        """Wo man aussteigen kann, der Reihe nach: links, rechts, hinten,
        vorn. Links zuerst, weil dort der Fahrer sitzt - wie im Auto."""
        vorn = self.vorn
        quer = pygame.Vector2(vorn.y, -vorn.x)       # links in Fahrtrichtung
        seite = self.radius + radius + 3.0
        laenge = K.FAHRZEUG["achse"] + self.radius + radius + 3.0
        return [self.pos + quer * seite, self.pos - quer * seite,
                self.pos - vorn * laenge, self.pos + vorn * laenge,
                self.pos + quer * seite - vorn * 14, self.pos - quer * seite - vorn * 14,
                self.pos + quer * seite + vorn * 14, self.pos - quer * seite + vorn * 14]
