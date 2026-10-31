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
from .core import naehern
from .entities import RND, Geschoss, Partikel, Wesen, abschuss_buchen, tod_blut, wolke


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
        fahrer = self.fahrer is not None and not self.kaputt
        self._physik(dt, self.gas if fahrer else 0.0,
                     self.lenk if fahrer else 0.0,
                     bool(self.handbremse) and fahrer)
        self._drehen(dt)
        self._fahren(dt)
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

    def _physik(self, dt: float, gas: float, lenk: float, handbremse: bool) -> None:
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
# * **Panzerung.** Kugeln kommen nur zum Teil an (`kugel_anteil`), was
#   explodiert, voll.
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
            ziel.schaden(d["schaden"], schub, self.von)
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
            a.schaden(d["flaeche"] * anteil, schub, self.von)
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
    def kugel_anteil(self) -> float:
        """So viel einer Kugel kommt am Blech an (Geschoss.einschlag)."""
        return float(self.werte["kugel_anteil"])

    @property
    def bild(self) -> str:
        return "%s_wrack" % self.art if self.kaputt else self.art

    def schaden(self, menge, schub=None, von=None, kugel: bool = False) -> None:
        """Wie beim Buggy: der Insasse bekommt seinen Teil (Kaempfer.schaden
        nimmt `fahrer_anteil`), die eigenen Leute verletzen ihn nicht. Neu:
        eine Kugel (`kugel`) zerkratzt das Blech nur - am Fahrzeug kommt
        `kugel_anteil` an, beim Insassen sein voller Teil. So hat auch
        jemand mit Sturmgewehr gegen einen Panzer eine Antwort: auf die
        Luke halten."""
        if self.kaputt or self.nur_bild or not self.lebt:
            return
        menge = float(menge)
        if menge <= 0.0:
            return
        k = self.fahrer
        if (k is not None and k.lebt and von is not k
                and (von is None or getattr(von, "fraktion", None) != k.fraktion)):
            k.schaden(menge, None, von)
        self.leben -= menge * (self.kugel_anteil if kugel else 1.0)
        self.blitz = K.TREFFER["blitz"]
        if self.leben <= 0.0:
            self._zerstoeren(von)

    def aufbau_bild_name(self) -> str:
        """Turm bzw. Ring: leer, mit Insasse, in den Farben seiner Mannschaft."""
        if self.fahrer is not None:
            besetzt, team = True, getattr(self.fahrer, "team", -1)
        else:
            besetzt, team = self.besetzt, self.team
        if not besetzt:
            return self.aufbau_name
        if 0 <= team < len(K.TEAMS["kombi"]):
            name = "%s_%s_fahrer" % (self.aufbau_name, K.TEAMS["kombi"][team]["name"].lower())
            if name in K.BILD_MASS:
                return name
        return self.aufbau_name + "_fahrer"

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
        """Mauern, Kisten, Faesser und Loecher (als Wand) gegen das Rechteck."""
        w = self.welt
        e = w.ebene(self.ebene)
        ecken = self.ecken(pos, winkel)
        x0 = int(min(c.x for c in ecken) // K.TILE)
        x1 = int(max(c.x for c in ecken) // K.TILE)
        y0 = int(min(c.y for c in ecken) // K.TILE)
        y1 = int(max(c.y for c in ecken) // K.TILE)
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

    def passt(self, pos, winkel=None) -> bool:
        """Kann er hier stehen? Mauern, Loecher, andere Wagen und alles
        Unverschiebbare (Zielpuppe, Koloss) halten ihn auf. Menschen und
        gewoehnliche Gegner nicht - die rammt er (`_beiseite_schieben`)."""
        w = self.welt
        if w is None:
            return True
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
        self._aufbau_fuehren(dt)
        for k in list(self.takt):
            self.takt[k] = max(0.0, self.takt[k] - dt)
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
                a.schaden((vn - f["ramm_schwelle"]) * f["ramm_je_px"], stoss, k)
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
        d = K.FAHRZEUG_WAFFEN["kanone"]
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


# Welche Art zu welcher Klasse und zu welchem Buchstaben in der Karte.
ARTEN = {"buggy": Buggy, "panzer": Panzer, "panzerwagen": Panzerwagen}


def marken() -> list:
    """(Buchstabe, Art) fuer jede Fahrzeugart, die eine Karte setzen kann."""
    return [(ARTEN[a].werte["marke"], a) for a in ("buggy", "panzer", "panzerwagen")]


def neu(art: str, pos, ebene: int = 0, winkel: float = 0.0, nur_bild: bool = False):
    """Ein Fahrzeug dieser Art. Unbekannt heisst Buggy - eine Meldung aus
    dem Netz soll nichts kaputt machen koennen."""
    return ARTEN.get(art, Buggy)(pygame.Vector2(pos), ebene, winkel, nur_bild)
