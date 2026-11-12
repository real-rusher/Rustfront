"""
DUSTFRONT - SCHLACHT: Dropzonen, Abwuerfe und Belohnungen (seit 0.34.96)
=======================================================================

Gewuenscht nach der ersten Runde SCHLACHT:

* Statt dass Fahrzeuge einfach an der Basis erscheinen, gibt es dort
  markierte **Dropzonen** (Vorbild: die Evakuierungszone aus XCOM 2). Wird
  ein Fahrzeug fuer eine Zone faellig, zaehlt sie herunter und pulsiert,
  und dann sinkt es an einem **Fallschirm** herunter. In der Luft wirft es
  einen Schatten am Boden, der waechst, je tiefer es kommt - so sieht man,
  ob es noch faellt oder schon steht.
* Ein **Belohnungsmenue** auf TAB (die Rangliste ist dort Nebensache):
  mit Punkten kauft man einmalige Dropzonen fuer Fahrzeuge auf freiem
  Gelaende, Abwuerfe mit Munition oder Medkits und den Ueberflug einer
  grossen Aufklaerungsdrohne, die einen Teil der Karte aufdeckt und die
  Gegner dort lange markiert.
* Punkte: 1 je Abschuss, 5 je zerstoertem Fahrzeug, 5 je Kamerad, dem man
  aufhilft (K.SCHLACHT punkte).

Nur der Gastgeber entscheidet; der Gast bekommt Zonen, Abwuerfe,
Ueberfluege und seine Punkte mit der Weltmeldung ("sl") und schickt einen
Kauf als Nachricht ("belohnung").
"""

from __future__ import annotations

import math

import pygame

from . import config as K
from . import fahrzeug as fahrzeug_modul
from .font import SCHRIFT

S = K.SCHLACHT


class Dropzone:
    """Eine markierte Stelle, an der Nachschub landet."""

    _naechste = 0

    def __init__(self, pos, team: int, art: str, winkel: float,
                 einmalig: bool = False) -> None:
        Dropzone._naechste += 1
        self.kennung = Dropzone._naechste
        self.pos = pygame.Vector2(pos)
        self.team = int(team)
        self.art = art               # buggy, panzer, panzerwagen, munition, medkit
        self.winkel = float(winkel)
        self.einmalig = einmalig
        self.rest = -1.0             # Sekunden bis zum Abwurf, -1: nichts faellig
        self.fahrzeug = None         # was hier gelandet ist und noch lebt


class Abwurf:
    """Was gerade am Fallschirm herunterkommt."""

    def __init__(self, zone: Dropzone) -> None:
        self.zone = zone
        self.pos = pygame.Vector2(zone.pos)
        self.art = zone.art
        self.team = zone.team
        self.winkel = zone.winkel
        self.hoehe = S["abwurf"]["hoehe"]
        self.alter = 0.0
        self.kennung = zone.kennung
        self.ziel = None             # wohin er treibt, weil unten etwas im Weg ist
        # Der Schirm ist gerissen (seit 0.34.118, Flak): Sekunden seitdem, 0 =
        # nein. Der Wagen faellt dann beschleunigt und kommt fast kaputt an.
        self.gerissen = 0.0


class Ueberflug:
    """Die grosse Aufklaerungsdrohne: fliegt quer ueber den gewaehlten Punkt
    und markiert, was in ihrem Kreis steht."""

    def __init__(self, ziel, team: int, fraktion: str, breite: float) -> None:
        a = S["aufklaerung"]
        self.ziel = pygame.Vector2(ziel)
        self.team = team
        self.fraktion = fraktion
        richtung = pygame.Vector2(1 if team == 0 else -1, 0)
        self.start = self.ziel - richtung * a["anflug"]
        self.ende = self.ziel + richtung * a["anflug"]
        self.alter = 0.0
        self.dauer = a["dauer"]

    @property
    def pos(self) -> pygame.Vector2:
        return self.start.lerp(self.ende, min(1.0, self.alter / self.dauer))


class Luftangriff:
    """Ein Napalm-Angriff (seit 0.34.101): ein Flugzeug, das niemand sieht,
    fliegt von `start` nach `ende` und wirft unregelmaessig Napalm.

    Wo die Bomben fallen, steht beim Kauf fest (`bomben_planen`, aus dem Ort
    gewuerfelt): [(Zeit des Einschlags, Ort, Radius, Dauer), ...]. So ist
    jeder Angriff anders, aber auf jedem Rechner derselbe."""

    def __init__(self, start, ende, team: int, fraktion: str, von=None) -> None:
        self.start = pygame.Vector2(start)
        self.ende = pygame.Vector2(ende)
        self.team = int(team)
        self.fraktion = fraktion
        self.von = von
        self.alter = 0.0
        self.bomben = bomben_planen(self.start, self.ende)
        self.naechste = 0
        self.gehoert = False
        self.pfiff = 0                 # welche Bombe als naechste pfeift (seit 0.34.130)
        self._brumm_rest = 0.0         # bis zum naechsten Stueck Triebwerk

    @property
    def dauer(self) -> float:
        return (self.bomben[-1][0] if self.bomben else 0.0) + 0.5

    def flugzeug(self) -> pygame.Vector2:
        """Wo das (unsichtbare) Flugzeug gerade ist."""
        n = S["napalm"]
        weg = (self.alter - n["vorlauf"]) * n["tempo"]
        laenge = max(1.0, self.start.distance_to(self.ende))
        # Nicht lerp: das nimmt nur 0 bis 1, das Flugzeug ist aber auch vor
        # dem Start und hinter dem Ende (seit 0.34.130 hoert man es dort).
        return self.start + (self.ende - self.start) * max(-0.7, min(1.7, weg / laenge))


def bomben_planen(start, ende) -> list:
    """Die Einschlaege eines Napalm-Angriffs: unregelmaessig, mit Luecken.

    Gewuenscht: "es ist wichtig, dass es unregelmaessig ist und man mit
    etwas Navigieren trotzdem durch die Bahn durchkommt, weil nicht alles
    brennt". Darum: unregelmaessiger Abstand, seitlich versetzt, und echte
    Luecken - wenigstens `wenigstens_luecken` Stellen, an denen zwischen
    zwei Feuern ein Weg frei bleibt."""
    import random
    n = S["napalm"]
    start, ende = pygame.Vector2(start), pygame.Vector2(ende)
    laenge = start.distance_to(ende)
    if laenge < 1.0:
        return []
    vorn = (ende - start) / laenge
    quer = pygame.Vector2(-vorn.y, vorn.x)
    r = random.Random(int(start.x) * 7919 + int(start.y) * 104729 + int(ende.x) * 31 + int(ende.y))
    plan = []                   # (Weg auf der Bahn, seitlich, Radius, Dauer)
    weg = r.uniform(0.0, n["abstand"])
    luecken = 0
    while weg <= laenge:
        radius = r.uniform(*n["radius"])
        plan.append((weg, r.uniform(-n["seitlich"], n["seitlich"]), radius, r.uniform(*n["dauer"])))
        schritt = n["abstand"] * r.uniform(*n["streu"])
        if r.random() < n["luecke_chance"]:
            schritt += r.uniform(*n["luecke"])
            luecken += 1
        weg += schritt
    # Zu wenige Luecken gewuerfelt? Dann fallen zufaellige Bomben weg, bis
    # es genug freie Stellen gibt.
    while luecken < n["wenigstens_luecken"] and len(plan) > 4:
        plan.pop(r.randrange(1, len(plan) - 1))
        luecken += 1
    raus = []
    for weg, seite, radius, dauer in plan:
        zeit = n["vorlauf"] + weg / n["tempo"] + n["fall"]
        raus.append((zeit, start + vorn * weg + quer * seite, radius, dauer))
    return raus


_NAPALM_BOMBE: dict = {}


def _napalm_bombe(winkel: float) -> pygame.Surface:
    """Eine Napalmbombe (seit 0.34.130): ein olivgruener Brandkanister mit
    rotem Band und vier Blechflossen hinten, gemalt wie die Fahrzeuge; gedreht
    in Flugrichtung, auf 10 Grad gerundet."""
    from .art_fahrzeuge import _Blatt
    w = int(round(winkel / 10.0)) * 10 % 360
    s = _NAPALM_BOMBE.get(w)
    if s is not None:
        return s
    b = _Blatt(24, 1.0)
    c, s_ = math.cos(math.radians(w)), math.sin(math.radians(w))
    an = lambda t, q=0.0: (c * t - s_ * q, s_ * t + c * q)       # noqa: E731
    for q in (-1.0, 1.0):                                         # Flossen
        b.poly((70, 74, 58), [an(-5.0, q * 1.2), an(-8.4, q * 3.4), an(-8.8, q * 3.0), an(-7.6, q * 1.0)])
    b.rohr(an(-6.6), an(5.2), 3.6, (98, 106, 74), (40, 44, 30))
    b.rohr(an(-1.0), an(0.2), 3.7, (168, 52, 36), (70, 22, 16))  # rotes Band
    b.kreis((122, 130, 92), an(5.4), 1.4)                         # Nase
    b.linie((140, 148, 112), an(-5.0, -0.8), an(4.0, -0.8), 0.6)  # Glanz
    s = _NAPALM_BOMBE[w] = b.fertig()
    return s


class SchlachtTeil:
    """Was das Gefecht in SCHLACHT zusaetzlich tut. Ein Anteil wie BotTeil."""

    # ---- Aufbau ---------------------------------------------------------
    def _schlacht_anlegen(self) -> None:
        self.dropzonen: list = []
        self.abwuerfe: list = []
        self.ueberfluege: list = []
        self.luftangriffe: list = []
        self._napalm_start = None
        self.belohnung_offen = False
        self.belohnung_wahl = 0
        self._sl_meldung = ""

    def dropzonen_anlegen(self) -> None:
        """Je Basis eine Zone fuer jedes Fahrzeug aus K.SCHLACHT fahrzeuge -
        dorthin, wo es frei ist und der Weg zur Mitte offen. Zum Rundenstart
        fallen gleich alle (kurzer Vorlauf)."""
        self.dropzonen = []
        self.abwuerfe = []
        self.ueberfluege = []
        self.luftangriffe = []
        self.verstaerkung_weg()
        # Was zu Rundenbeginn schon steht (seit 0.34.129 nach FREISCHALTEN;
        # spaetere Stufen kommen mit basis_nachschub).
        self._basis_stufe = min(3, self.freischalt_stufe())
        for team in range(2):
            for art, anzahl, basis in self.basis_ausstattung(team, -1, self._basis_stufe):
                for _ in range(anzahl):
                    platz = self._fahrzeug_platz_bei(art, basis, S["fahrzeug_umkreis"],
                                                     abstand_zonen=True)
                    if platz is None:
                        continue
                    pos, winkel = platz
                    zone = Dropzone(pos, team, art, winkel)
                    zone.rest = S["abwurf"]["start"]
                    self.dropzonen.append(zone)
        # Seit 0.34.138 stehen die Wagen der Basen zum Rundenstart gleich da
        # (gemeldet: "alle laufen los, dann droppen die Fahrzeuge, und ein paar
        # Bots rennen zurueck"). Was spaeter nachkommt, faellt weiter am Schirm.
        if S["basis_sofort"]:
            for zone in list(self.dropzonen):
                if zone.fahrzeug is None and zone.art in fahrzeug_modul.ARTEN:
                    zone.rest = 0.0
                    self._abwurf_landet(Abwurf(zone))
        self._basis_fahrer_offen = True

    def basis_ausstattung(self, team: int, ab_stufe: int, bis_stufe: int) -> list:
        """Was an den Basen einer Seite steht, von (ausschliesslich) ab_stufe
        bis bis_stufe: [(Art, Anzahl, Ort der Basis)]. Auf einer Karte mit
        Front (seit 0.34.131) hat jede Basis ihre eigene Ausstattung aus dem
        Kartenkopf; sonst K.SCHLACHT fahrzeuge an der einen Basis."""
        raus = []
        basen = self.front_basen(team) if self.schlachtplan is not None else []
        if basen:
            for b in basen:
                for art, anzahl, stufe in b.fahrzeuge:
                    if ab_stufe < stufe <= bis_stufe:
                        raus.append((art, anzahl, b.pos))
            return raus
        for eintrag in S["fahrzeuge"]:
            art, anzahl = eintrag[0], eintrag[1]
            stufe = eintrag[2] if len(eintrag) > 2 else 0
            if ab_stufe < stufe <= bis_stufe:
                raus.append((art, anzahl, self.schlacht_basis(team)))
        return raus

    # ---- Ablauf (Gastgeber) ------------------------------------------------
    def basis_fahrer_setzen(self) -> int:
        """Zum Rundenstart (seit 0.34.138): in jeden Wagen der Basen setzt sich
        gleich ein freier Bot-Fahrer seiner Seite (`darf_fahren`), der naechste
        zuerst - so faehrt die Seite gemeinsam los, statt dass Bots spaeter
        zurueckrennen. Gibt die Zahl der Besetzten zurueck."""
        from .bots import FAHRZEUG_VORZUG
        n = 0
        # Die wertvollen zuerst (Werfer, Panzer, Funkwagen ...), dann Buggys.
        for b in sorted(self.fahrzeuge, key=lambda v: -FAHRZEUG_VORZUG.get(v.art, 0.0)):
            if (b.fahrer is not None or b.kaputt or b.nur_bild or not b.lebt
                    or getattr(b, "basis_team", -1) not in (0, 1) or b.werte.get("nur_mensch")):
                continue
            frei = [k for k in self.kaempfer.values()
                    if getattr(k, "ist_bot", False) and k.lebt and not k.am_boden
                    and k.team == b.basis_team and getattr(k, "darf_fahren", False)
                    and k.fahrzeug is None and getattr(k, "mitfahrt", None) is None
                    and k.pos.distance_to(b.pos) <= S["basis_fahrer_weite"]]
            if not frei:
                continue
            k = min(frei, key=lambda x: x.pos.distance_squared_to(b.pos))
            k.pos.update(b.pos)
            if hasattr(k, "vorher"):
                k.vorher.update(b.pos)
            self._einsteigen(k, b)
            n += 1
        return n

    def schlacht_schritt(self, dt: float) -> None:
        if not (self.schlacht or self.__dict__.get("nachschub_an")) or not self.ist_gastgeber:
            return
        if self.schlacht:
            self.basis_nachschub()
            if self.__dict__.get("_basis_fahrer_offen") and any(
                    getattr(k, "ist_bot", False) for k in self.kaempfer.values()):
                self._basis_fahrer_offen = False
                self.basis_fahrer_setzen()
        a = S["abwurf"]
        for zone in list(self.dropzonen):
            if zone.fahrzeug is not None:
                b = zone.fahrzeug
                if not b.lebt or b not in self.fahrzeuge:
                    zone.fahrzeug = None
                    if not zone.einmalig:
                        zone.rest = b.werte["neu_nach"]
                continue
            if zone.rest > 0.0:
                zone.rest -= dt
                if zone.rest <= 0.0:
                    zone.rest = 0.0
                    self.abwuerfe.append(Abwurf(zone))
                    self.welt.klang("anflug", 0.6, zone.pos, 0)
        for ab in list(self.abwuerfe):
            ab.alter += dt
            if ab.gerissen > 0.0:
                ab.gerissen += dt
                F = K.FLAK
                ab.hoehe -= min(F["riss_tempo"], a["sinken"] + F["riss_beschl"] * ab.gerissen) * dt
            else:
                ab.hoehe -= a["sinken"] * dt
            if ab.hoehe <= a["ausweichen_ab"]:
                self._abwurf_lenken(ab, dt)
            if ab.hoehe <= 0.0:
                self.abwuerfe.remove(ab)
                self._abwurf_landet(ab)
        self._springer_schritt(dt)
        for la in list(getattr(self, "luftangriffe", ())):
            self._luftangriff_schritt(la, dt)
            if la.alter >= la.dauer:
                self.luftangriffe.remove(la)
        for ue in list(self.ueberfluege):
            ue.alter += dt
            self._ueberflug_markieren(ue)
            if ue.alter >= ue.dauer:
                self.ueberfluege.remove(ue)

    # ---- Landen, ohne auf etwas zu fallen (seit 0.34.100) --------------------
    # Gewuenscht: "stell sicher, dass du dir eine Loesung ueberlegt hast, was
    # passiert, wenn ein Fahrzeug mit dem Airdrop auf einem Spieler oder
    # anderen Fahrzeug landet." Die Loesung in drei Stufen:
    # 1. Unter ausweichen_ab prueft der Abwurf jeden Schritt, ob seine
    #    Landestelle frei ist: kein Fels, kein Loch, kein Fahrzeug (auch kein
    #    Wrack), kein anderer Abwurf. Ist sie es nicht, sucht er die naechste
    #    freie Stelle und treibt am Schirm dorthin - sichtbar, wie bei Wind.
    # 2. Beim Aufsetzen noch einmal: ist es dann immer noch belegt (ein Wagen
    #    ist im letzten Moment hineingefahren), landet er gleich an der
    #    naechsten freien Stelle. Nie auf oder in etwas.
    # 3. Menschen und Tiere unter ihm werden nicht erschlagen, sondern aus dem
    #    Fussabdruck gestossen (stoss) und nehmen etwas Schaden (quetschen).
    #    Ab warnen_ab blinkt der Schatten rot, damit man rechtzeitig geht.
    def _probe(self, art: str):
        merk = self.__dict__.setdefault("_sl_probe", {})
        probe = merk.get(art)
        if probe is None:
            probe = merk[art] = fahrzeug_modul.neu(art, (0, 0), 0)
        probe.welt = self.welt
        return probe

    def abwurf_fuss(self, art: str) -> float:
        """Wie gross die Landestelle ist (Radius in px)."""
        if art in fahrzeug_modul.ARTEN:
            probe = self._probe(art)
            return max(20.0, float(getattr(probe, "huelle_radius", 0.0)), float(probe.radius))
        if art == "mensch":
            return 12.0
        return 26.0

    def landeplatz_frei(self, art: str, pos, winkel: float = 0.0, ohne=None) -> bool:
        """Kann hier etwas dieser Art landen, ohne auf etwas zu fallen?"""
        e = self.welt.ebene(0)
        fuss = self.abwurf_fuss(art)
        if not (fuss <= pos.x < e.pixel_breite - fuss and fuss <= pos.y < e.pixel_hoehe - fuss):
            return False
        if art in fahrzeug_modul.ARTEN:
            probe = self._probe(art)
            if not probe.passt(pygame.Vector2(pos), winkel):
                return False
            if self.welt.fahrwege.gebiet_bei(0, pos) < 0:
                return False
        elif not self.welt.frei(pygame.Vector2(pos), 12.0 if art == "mensch" else 16.0, 0):
            return False
        for b in getattr(self, "fahrzeuge", ()):
            if int(getattr(b, "ebene", 0)) != 0:
                continue
            weite = fuss + max(float(getattr(b, "huelle_radius", 0.0)), float(b.radius))
            if b.pos.distance_squared_to(pos) < weite * weite:
                return False
        for ab in self.abwuerfe:
            if ab is ohne:
                continue
            ort = ab.ziel if ab.ziel is not None else ab.pos
            weite = fuss + self.abwurf_fuss(ab.art)
            if ort.distance_squared_to(pos) < weite * weite:
                return False
        return True

    def freie_landestelle(self, art: str, nahe, winkel: float = 0.0, ohne=None):
        """Die naechste Stelle um `nahe`, an der es landen kann - oder None."""
        nahe = pygame.Vector2(nahe)
        if self.landeplatz_frei(art, nahe, winkel, ohne):
            return nahe
        schritt = 20.0
        weit = schritt
        while weit <= S["abwurf"]["suche_weit"]:
            teile = max(8, int(2 * math.pi * weit / schritt))
            for i in range(teile):
                p = nahe + pygame.Vector2(weit, 0).rotate(360.0 * i / teile)
                if self.landeplatz_frei(art, p, winkel, ohne):
                    return p
            weit += schritt
        return None

    def _abwurf_lenken(self, ab: Abwurf, dt: float) -> None:
        """Schritt 1: treiben, wenn unten belegt ist."""
        ort = ab.ziel if ab.ziel is not None else ab.pos
        if ab.ziel is None or not self.landeplatz_frei(ab.art, ort, ab.winkel, ab):
            if self.landeplatz_frei(ab.art, ab.pos, ab.winkel, ab):
                ab.ziel = None
            else:
                ab.ziel = self.freie_landestelle(ab.art, ab.pos, ab.winkel, ab)
        if ab.ziel is not None:
            weg = ab.ziel - ab.pos
            schritt = S["abwurf"]["treiben"] * dt
            if weg.length() <= schritt:
                ab.pos.update(ab.ziel)
            else:
                ab.pos += weg.normalize() * schritt

    def _abwurf_aufsetzen(self, ab: Abwurf) -> None:
        """Schritt 2 und 3: nie auf etwas, und wer drunter steht, muss weg."""
        if not self.landeplatz_frei(ab.art, ab.pos, ab.winkel, ab):
            stelle = self.freie_landestelle(ab.art, ab.pos, ab.winkel, ab)
            if stelle is not None:
                ab.pos.update(stelle)
        self.wegstossen(ab.pos, self.abwurf_fuss(ab.art))

    def wegstossen(self, mitte, fuss: float, ausser=None) -> None:
        """Alle Lebenden im Kreis `fuss` um `mitte` heraus an eine freie
        Stelle, mit einem Stoss und etwas Schaden."""
        a = S["abwurf"]
        mitte = pygame.Vector2(mitte)
        kandidaten = list(self.kaempfer.values()) + [
            w for w in self.welt.wesen if getattr(w, "lebt", False)
            and getattr(w, "schiebbar", True) and not getattr(w, "ist_ausruestung", False)
            and w not in self.kaempfer.values()]
        for k in kandidaten:
            if k is ausser or not getattr(k, "lebt", False) or int(getattr(k, "ebene", 0)) != 0:
                continue
            if getattr(k, "im_fahrzeug", False) or getattr(k, "schirm_hoehe", 0.0) > 0.0:
                continue
            if getattr(k, "fraktion", "") == "geschoss":
                continue
            r = float(getattr(k, "radius", 8.0))
            ab = k.pos - mitte
            if ab.length() >= fuss + r:
                continue
            richtung = ab.normalize() if ab.length_squared() > 1.0 else pygame.Vector2(1, 0)
            ziel = None
            for dreh in (0, 30, -30, 60, -60, 90, -90, 120, -120, 150, -150, 180):
                p = mitte + richtung.rotate(dreh) * (fuss + r + 6.0)
                if self.welt.frei(p, r, 0):
                    ziel = p
                    break
            if ziel is not None:
                k.pos.update(ziel)
                if hasattr(k, "vorher"):
                    k.vorher.update(ziel)
            if hasattr(k, "schaden"):
                k.schaden(a["quetschen"], richtung * a["stoss"])

    def _abwurf_landet(self, ab: Abwurf) -> None:
        from .entities import wolke
        w = self.welt
        self._abwurf_aufsetzen(ab)
        zone = ab.zone
        wolke(w, ab.pos, 26, 160, 0.9, K.C_SAND_KORN, 0, 2, "bodenstaub", 360, 0)
        w.ruckeln(2.5, "sturz", ab.pos, 0)
        w.klang("buggy_tuer", 0.9, ab.pos, 0)
        if ab.art in ("munition", "medkit"):
            from .mehrspieler import KampfBeute
            for i in range(S["abwurf"]["kisten"]):
                p = ab.pos + pygame.Vector2(14, 0).rotate(i * 360.0 / S["abwurf"]["kisten"])
                if not w.frei(p, 8.0, 0):
                    p = pygame.Vector2(ab.pos)     # nie in eine Mauer
                w.dazu(KampfBeute(p, ab.art, 0, self.kaempfer))
            if zone in self.dropzonen:
                self.dropzonen.remove(zone)
            return
        b = fahrzeug_modul.neu(ab.art, ab.pos, 0, ab.winkel)
        w.dazu(b)
        if hasattr(b, "aufbau"):
            b.aufbau = b.winkel
        b.start = (pygame.Vector2(ab.pos), 0, ab.winkel)
        b.basis_team = zone.team
        b.gekauft = zone.einmalig            # zaehlt fuer K.SCHLACHT hoechstens_je_seite
        b.dropzone = zone
        if ab.gerissen > 0.0:
            # Gestuerzt (seit 0.34.118): der Schirm war ab, der Wagen schlaegt hart auf
            # und hat fast nichts mehr.
            b.leben = max(1.0, b.max_leben * K.FLAK["absturz_leben"])
            w.explosion(pygame.Vector2(ab.pos), 0, 40.0, "absturz")
        self.fahrzeuge.append(b)
        zone.fahrzeug = b
        if b.werte.get("nur_bot"):
            self.bot_ans_steuer(b, zone.team)
        if zone.einmalig and zone in self.dropzonen:
            # Die gekaufte Zone gilt einmal; danach verschwindet sie.
            self.dropzonen.remove(zone)

    def _ueberflug_markieren(self, ue: Ueberflug) -> None:
        from . import ausruestung
        a = S["aufklaerung"]
        p = ue.pos
        for k in self.kaempfer.values():
            if k.lebt and k.fraktion != ue.fraktion and k.pos.distance_to(p) <= a["radius"]:
                ausruestung.markieren(k, ue.fraktion)
                k.markiert_rest = max(k.markiert_rest, a["markiert"])
        # Seit 0.34.100 auch die Fahrzeuge der anderen Seite (und herrenlose
        # an ihrer Basis): ihr Ping bewegt sich mit, auch im Nebel.
        for b in getattr(self, "fahrzeuge", ()):
            if getattr(b, "kaputt", False) or not getattr(b, "lebt", True):
                continue
            fahrer = getattr(b, "fahrer", None)
            seite = getattr(fahrer, "team", None) if fahrer is not None else getattr(b, "basis_team", -1)
            if seite == ue.team or b.pos.distance_to(p) > a["radius"]:
                continue
            b.markiert_rest = max(getattr(b, "markiert_rest", 0.0), a["markiert"])
            b.markiert_fuer = ue.fraktion

    # ---- Fallschirmjaeger (seit 0.34.100) --------------------------------------
    # Gewuenscht: "einen Fallschirmjaeger-Abwurf, also sagen wir 5 Bots, quasi
    # beliebig (wo Platz ist und nicht in Basen) gedroppt, in Formation, und
    # zwar vor dem Landen nichts machen, aber schon Gegner erkennen koennen."
    # Es sind zusaetzliche Bots der eigenen Seite (`verstaerkung`): sie
    # zaehlen beim Auffuellen nicht mit und kommen nach dem Tod nicht wieder.
    # In der Luft (`schirm_hoehe` > 0) sind sie kein Ziel und nicht zu
    # treffen; die Gegner sehen sie trotzdem und gehen in Stellung
    # (bots.BotHirn._springer_reaktion).
    def _sprung_plaetze(self, punkt, team: int) -> list:
        """Die Landestellen: ein Keil um `punkt`, die Spitze zur Gegenseite.
        Wo eine Stelle belegt ist, die naechste freie in der Naehe."""
        f = S["fallschirmjaeger"]
        punkt = pygame.Vector2(punkt)
        feind = self.schlacht_basis(1 - team) if team in (0, 1) else None
        vorn = (feind - punkt) if feind is not None else pygame.Vector2(1, 0)
        vorn = vorn.normalize() if vorn.length_squared() > 1.0 else pygame.Vector2(1, 0)
        quer = pygame.Vector2(-vorn.y, vorn.x)
        a = f["abstand"]
        muster = [(0, 0), (-1, 1), (-1, -1), (-2, 2), (-2, -2), (-3, 0), (-3, 3), (-3, -3)]
        plaetze = []
        for zurueck, seite in muster[:f["anzahl"]]:
            soll = punkt + vorn * (zurueck * a * 0.8) + quer * (seite * a * 0.6)
            stelle = None
            for weit in range(0, int(f["breite"]) + 1, 12):
                for i in range(max(1, weit // 6)):
                    q = soll + pygame.Vector2(weit, 0).rotate(360.0 * i / max(1, weit // 6))
                    if q.distance_to(punkt) > f["breite"]:
                        continue
                    if not self.landeplatz_frei("mensch", q):
                        continue
                    if any(q.distance_to(x) < 24.0 for x in plaetze):
                        continue
                    stelle = q
                    break
                if stelle is not None:
                    break
            if stelle is not None:
                plaetze.append(stelle)
        return plaetze

    def bot_ans_steuer(self, b, team: int):
        """Ein Bot dieser Seite sitzt schon im Wagen (seit 0.34.114, Flakwagen:
        Menschen duerfen ihn nicht fahren). Wie die Fallschirmjaeger ein
        zusaetzlicher Bot (`verstaerkung`): er zaehlt beim Auffuellen nicht mit
        und kommt nach dem Tod nicht wieder."""
        k = self._bot_dazu(team)
        k.verstaerkung = True
        k.darf_fahren = False        # sitzt schon; sucht nach dem Aussteigen keinen neuen Wagen
        k.pos.update(b.pos)
        if hasattr(k, "vorher"):
            k.vorher.update(b.pos)
        k.unverwundbar = 0.0
        self._einsteigen(k, b)
        return k

    def fallschirmjaeger_abwerfen(self, punkt, team: int) -> list:
        """Fuenf Bots dieser Seite am Schirm ueber `punkt` (Gastgeber)."""
        f = S["fallschirmjaeger"]
        raus = []
        for i, stelle in enumerate(self._sprung_plaetze(punkt, team)):
            k = self._bot_dazu(team)
            k.verstaerkung = True
            k.darf_fahren = False
            k.pos.update(stelle)
            if hasattr(k, "vorher"):
                k.vorher.update(stelle)
            k.sprung_ort = pygame.Vector2(stelle)
            # Leicht versetzt: sie springen nacheinander.
            k.schirm_hoehe = f["hoehe"] + i * f["hoehe"] * 0.06 * f["versatz"]
            k.trefferbar = False
            k.schiebbar = False
            k.unverwundbar = 0.0
            ziel = self.schlacht_basis(1 - team) if team in (0, 1) else None
            if ziel is not None:
                hin = ziel - k.pos
                k.winkel = math.degrees(math.atan2(hin.y, hin.x))
            raus.append(k)
        if raus:
            self.welt.klang("anflug", 0.8, pygame.Vector2(punkt), 0)
        return raus

    def _springer_schritt(self, dt: float) -> None:
        """Sinken, an der Stelle bleiben, sicher aufsetzen (Gastgeber)."""
        f = S["fallschirmjaeger"]
        for k in list(self.kaempfer.values()):
            hoch = getattr(k, "schirm_hoehe", 0.0)
            if hoch <= 0.0:
                continue
            if not k.lebt:
                k.schirm_hoehe = 0.0
                continue
            ort = getattr(k, "sprung_ort", None)
            if ort is not None:
                k.pos.update(ort)
            k.will.update(0, 0)
            k.tempo.update(0, 0)
            k.feuert = False
            k.zielt = False
            hoch -= f["sinken"] * dt
            if hoch > 0.0:
                k.schirm_hoehe = hoch
                continue
            # Gelandet. Belegt (ein Wagen ist hineingefahren)? Daneben.
            k.schirm_hoehe = 0.0
            if not self.landeplatz_frei("mensch", k.pos):
                stelle = self.freie_landestelle("mensch", k.pos)
                if stelle is not None:
                    k.pos.update(stelle)
                    if hasattr(k, "vorher"):
                        k.vorher.update(stelle)
            self.wegstossen(k.pos, 10.0, ausser=k)
            k.trefferbar = True
            k.schiebbar = True
            k.sprung_ort = None
            from .entities import wolke
            wolke(self.welt, k.pos, 8, 60, 0.6, K.C_SAND_KORN, 0, 1, "bodenstaub", 360, 0)

    def napalm_ende(self, start, richtung_punkt):
        """Wo die Bahn endet: immer gleich lang (laenge_anteil der Karten-
        hoehe), in Richtung des zweiten Punkts - auch ueber ihn hinaus."""
        start = pygame.Vector2(start)
        hin = pygame.Vector2(richtung_punkt) - start
        if hin.length_squared() < 1.0:
            return None
        laenge = self.welt.ebene(0).pixel_hoehe * S["napalm"]["laenge_anteil"]
        return start + hin.normalize() * laenge

    def _luftangriff_schritt(self, la: Luftangriff, dt: float) -> None:
        """Der Bomber kommt (man hoert ihn nur, und nur in seiner Naehe),
        die Bomben fallen pfeifend, dann brennt Napalm."""
        from .entities import Brandflaeche
        w = self.welt
        n = S["napalm"]
        # Seit 0.34.130 (gewuenscht): kein Ton fuer alle mehr, sondern ein
        # Bomber, der ueber die Bahn zieht - Stueck fuer Stueck dort gespielt,
        # wo er gerade ist. So hoert ihn, wer in der Naehe ist, unter ihm am
        # lautesten, und das Geraeusch wandert mit.
        la._brumm_rest -= dt
        laenge = max(1.0, la.start.distance_to(la.ende))
        weg = (la.alter - n["vorlauf"]) * n["tempo"] / laenge
        if la._brumm_rest <= 0.0 and n["hoeren_ab"] <= weg <= n["hoeren_bis"]:
            la._brumm_rest = n["brumm_takt"]
            w.klang("bomber", n["brumm_laut"], la.flugzeug(), 0)
        while la.pfiff < len(la.bomben) and la.bomben[la.pfiff][0] - n["fall"] <= la.alter:
            w.klang("napalm_fall", 0.7, la.bomben[la.pfiff][1], 0)
            la.pfiff += 1
        la.alter += dt
        while la.naechste < len(la.bomben) and la.bomben[la.naechste][0] <= la.alter:
            _t, ort, radius, dauer = la.bomben[la.naechste]
            la.naechste += 1
            e = w.ebene(0)
            if not (0 <= ort.x < e.pixel_breite and 0 <= ort.y < e.pixel_hoehe):
                continue
            w.feuer.append(Brandflaeche(ort, 0, radius=radius, dauer=dauer, von=la.von, napalm=True))
            w.explosion(ort, 0, 0.0, "feuer")
            w.klang("napalm", 0.9, ort, 0)
            w.laerm(ort, 0, la.von, 700.0)

    def verstaerkung_weg(self) -> None:
        """Zur neuen Runde: die Fallschirmjaeger der alten gehen."""
        for k in list(self.kaempfer.values()):
            if getattr(k, "verstaerkung", False):
                self._bot_weg(k)

    def _zeit_jetzt(self) -> float:
        return self.welt.zeit if self.ist_gastgeber else self._zeit

    # ---- Punkte -------------------------------------------------------------
    def schlacht_punkte(self, k, wie_viel: int, grund: str = "") -> None:
        if self.schlacht and k is not None and not getattr(k, "ist_bot", False):
            k.schlacht_punkte = getattr(k, "schlacht_punkte", 0) + int(wie_viel)
            if grund and int(wie_viel) > 0:
                self._punkte_melden(k, int(wie_viel), grund)

    def _punkte_melden(self, k, n: int, grund: str) -> None:
        """Fuer den Spieler selbst: wofuer es gerade Punkte gab (seit 0.34.138).
        Beim Gast kommt es als Klang-freie Meldung ueber den Stand."""
        if k is self.ich and hasattr(self, "melden"):
            self.melden("+%d %s" % (n, grund), 2.0)

    def serie_punkte(self, k, art: str) -> None:
        """Bonus fuer eine Folge (seit 0.34.138): Abschuesse oder Fahrzeuge kurz
        nacheinander bringen mehr - wer sich darauf wirft, kommt schneller voran."""
        if not self.schlacht or k is None or getattr(k, "ist_bot", False):
            return
        p = S["punkte"]
        jetzt = self.welt.zeit
        if art == "fahrzeug":
            vorher = getattr(k, "_jagd_zuletzt", -1e9)
            k._jagd_zuletzt = jetzt
            if jetzt - vorher <= p["jagd_zeit"]:
                self.schlacht_punkte(k, p["jagd"], "JAGD")
            return
        vorher = getattr(k, "_serie_zuletzt", -1e9)
        k._serie_zuletzt = jetzt
        k._serie = getattr(k, "_serie", 0) + 1 if jetzt - vorher <= p["serie_zeit"] else 1
        if k._serie > p["serie_ab"]:
            bonus = min(p["serie_hoechstens"], p["serie"] * (k._serie - p["serie_ab"]))
            self.schlacht_punkte(k, bonus, "SERIE x%d" % k._serie)

    def sold_schritt(self, dt: float) -> None:
        """Alle sold_takt Sekunden etwas fuer jeden (seit 0.34.138): wer faehrt,
        heilt oder den Werfer bedient, muss nichts aufgeben, um zu Punkten zu
        kommen. Wer mehr Eroberungspunkte haelt, bekommt mehr."""
        if not self.schlacht or self.vorbei or self.in_lobby or not self.ist_gastgeber:
            return
        p = S["punkte"]
        self._sold_rest = getattr(self, "_sold_rest", p["sold_takt"]) - dt
        if self._sold_rest > 0.0:
            return
        self._sold_rest = p["sold_takt"]
        gehalten = [0, 0]
        for q in (self.front_punkte() if hasattr(self, "front_punkte") else ()):
            if q.besitzer in (0, 1):
                gehalten[q.besitzer] += 1
        for k in self.kaempfer.values():
            if getattr(k, "ist_bot", False) or getattr(k, "team", -1) not in (0, 1):
                continue
            n = p["sold"] + (p["sold_halten"] if gehalten[k.team] > gehalten[1 - k.team] else 0)
            self.schlacht_punkte(k, n, "SOLD")

    # ---- Freischalten und Balancing (seit 0.34.129) -----------------------
    def freischalt_modus(self) -> str:
        return str(getattr(self, "regelwerk", {}).get("freischalten", "normal"))

    def spielverlauf(self) -> float:
        """Wie weit die Runde ist (0 bis 1): Anteil der Rundenzeit; bei einer
        Runde nach Abschuessen der groessere von Abschuessen der fuehrenden
        Seite am Ziel und Laufzeit an K.SCHLACHT freischalten bezug."""
        alter = float(getattr(self, "runden_alter", 0.0))
        if self.ende_art == "zeit" and self.ende_wert > 0:
            return alter / float(self.ende_wert)
        anteil = alter / float(S["freischalten"]["bezug"])
        if self.ende_wert > 0 and getattr(self, "teampunkte", None):
            anteil = max(anteil, max(self.teampunkte) / float(self.ende_wert))
        return anteil

    def freischalt_stufe(self) -> int:
        """Welche Stufe gilt: 0 am Anfang, 3 = alles. Mit FREISCHALTEN AUS
        (oder ausserhalb der SCHLACHT) gleich alles."""
        modus = self.freischalt_modus()
        if modus not in S["freischalten"] or not self.schlacht:
            return 99
        f = S["freischalten"][modus]
        anteil = self.spielverlauf()
        alter = float(getattr(self, "runden_alter", 0.0))
        return sum(1 for g, spaet in zip(f["stufen"], f["hoechstens"]) if anteil >= g or alter >= spaet)

    def freischalt_rest(self, stufe: int) -> float:
        """Sekunden, bis die Stufe kommt - None, wenn das nicht an der Zeit
        haengt (Runde nach Abschuessen: es kann auch frueher kommen)."""
        modus = self.freischalt_modus()
        if modus not in S["freischalten"] or stufe <= 0:
            return 0.0
        f = S["freischalten"][modus]
        alter = float(getattr(self, "runden_alter", 0.0))
        spaet = f["hoechstens"][stufe - 1]
        if self.ende_art == "zeit" and self.ende_wert > 0:
            spaet = min(spaet, f["stufen"][stufe - 1] * float(self.ende_wert))
        return max(0.0, spaet - alter)

    def gesperrt_bis(self, was: str) -> str:
        """Leer, wenn `was` schon freigeschaltet ist - sonst ab wann."""
        stufe = int(S["stufe"].get(was, 0))
        if stufe <= self.freischalt_stufe():
            return ""
        rest = self.freischalt_rest(stufe)
        return "IN %d:%02d" % (int(rest) // 60, int(rest) % 60) if rest > 0 else "STUFE %d" % stufe

    def gekauft_unterwegs(self, team: int, art: str) -> int:
        """Wie viele gekaufte `art` die Seite gerade hat: gelandet und heil,
        am Schirm oder noch als Zone angemeldet."""
        n = sum(1 for b in self.fahrzeuge if b.art == art and getattr(b, "gekauft", False)
                and getattr(b, "basis_team", -1) == team and not b.kaputt)
        n += sum(1 for z in self.dropzonen if z.einmalig and z.team == team and z.art == art)
        n += sum(1 for a in self.abwuerfe if a.zone.einmalig and a.team == team and a.art == art
                 and a.zone not in self.dropzonen)
        return n

    def in_eigener_haelfte(self, punkt, team: int) -> bool:
        """Liegt der Punkt auf der Seite der eigenen Basis (von der Mitte aus)?"""
        basis = self.schlacht_basis(team)
        mitte = self._schlacht_punkte()[2]
        return (punkt - mitte).dot(basis - mitte) >= 0.0

    @staticmethod
    def fahrzeug_punkte(art: str) -> int:
        """Was ein zerstoertes Fahrzeug bringt: die Haelfte seines Preises,
        mindestens `fahrzeug_min`; nicht kaufbares `fahrzeug`."""
        p = S["punkte"]
        for name, kosten, _t in S["belohnungen"]:
            if name == art:
                return max(int(p["fahrzeug_min"]), int(kosten * p["fahrzeug_anteil"] + 0.5))
        return int(p["fahrzeug"])

    def basis_nachschub(self) -> None:
        """Die Basis-Fahrzeuge einer neuen Stufe anmelden (Gastgeber): sie
        fallen mit Rueckzaehlung an der eigenen Basis wie zu Rundenbeginn."""
        stufe = min(3, self.freischalt_stufe())
        bisher = self.__dict__.get("_basis_stufe", 0)
        if stufe <= bisher:
            return
        self._basis_stufe = stufe
        for team in range(2):
            for art, anzahl, basis in self.basis_ausstattung(team, bisher, stufe):
                for _ in range(anzahl):
                    platz = self._fahrzeug_platz_bei(art, basis, S["fahrzeug_umkreis"],
                                                     abstand_zonen=True)
                    if platz is None:
                        continue
                    zone = Dropzone(platz[0], team, art, platz[1])
                    zone.rest = S["abwurf"]["vorlauf_kauf"]
                    self.dropzonen.append(zone)

    # ---- Kaufen ------------------------------------------------------------
    @staticmethod
    def belohnungen() -> list:
        return list(S["belohnungen"])

    def belohnung_pruefen(self, k, was: str, punkt, gratis: bool = False,
                          punkt2=None) -> str:
        """Leer, wenn der Kauf geht - sonst warum nicht. `gratis`: der
        ADMIN-Schalter (seit 0.34.100) - spart nur die Punkte, nicht die
        anderen Pruefungen."""
        d = dict((n, (kosten, text)) for n, kosten, text in S["belohnungen"])
        if was not in d:
            return "UNBEKANNT"
        if not gratis and getattr(k, "schlacht_punkte", 0) < d[was][0]:
            return "ZU WENIG PUNKTE"
        e = self.welt.ebene(0)
        if not (0 <= punkt.x < e.pixel_breite and 0 <= punkt.y < e.pixel_hoehe):
            return "AUSSERHALB DER KARTE"
        if not gratis and self.funk_gestoert_bei(punkt, k.team):
            return "GESTÖRT: FUNKWAGEN DER GEGNER"       # seit 0.34.111
        # Seit 0.34.129: Stufe, Hoechstzahl je Seite, eigene Haelfte.
        bis = self.gesperrt_bis(was)
        if bis:
            return "NOCH NICHT FREI (%s)" % bis
        grenze = S["hoechstens_je_seite"].get(was) if getattr(self, "regelwerk", {}).get("fahrzeug_grenze") else None
        if grenze is not None and k.team in (0, 1) and self.gekauft_unterwegs(k.team, was) >= grenze:
            return "SCHON %d IM EINSATZ" % grenze
        if was in S["nur_eigene_haelfte"] and k.team in (0, 1) and not self.in_eigener_haelfte(punkt, k.team):
            return "NUR IN DER EIGENEN HÄLFTE"
        if was == "aufklaerung":
            return ""
        feind = self.schlacht_basis(1 - k.team) if k.team in (0, 1) else None
        if feind is not None and punkt.distance_to(feind) < S["abwurf"]["sperre_basis"]:
            return "ZU NAH AN DER FEINDLICHEN BASIS"
        if was == "napalm":
            if punkt2 is None:
                return ""                     # erst der Start - die Richtung folgt
            ende = self.napalm_ende(punkt, punkt2)
            if ende is None:
                return "RICHTUNG WÄHLEN"
            # Keine Bombe in die Sperre um die feindliche Basis (Spawn).
            if feind is not None:
                laenge = punkt.distance_to(ende)
                for i in range(int(laenge // 80) + 1):
                    q = punkt.lerp(ende, min(1.0, i * 80.0 / max(1.0, laenge)))
                    if q.distance_to(feind) < S["abwurf"]["sperre_basis"]:
                        return "BAHN ZU NAH AN DER FEINDLICHEN BASIS"
            return ""
        if was == "fallschirmjaeger":
            eigen = self.schlacht_basis(k.team) if k.team in (0, 1) else None
            if eigen is not None and punkt.distance_to(eigen) < S["fallschirmjaeger"]["nicht_basis"]:
                return "NICHT IN DER EIGENEN BASIS"
            if len(self._sprung_plaetze(punkt, k.team)) < S["fallschirmjaeger"]["anzahl"]:
                return "ZU WENIG PLATZ"
            return ""
        if was in fahrzeug_modul.ARTEN:
            probe = fahrzeug_modul.neu(was, punkt, 0)
            probe.welt = self.welt
            if not probe.passt(punkt, 0.0):
                return "KEIN FREIES GELÄNDE"
            netz = self.welt.fahrwege
            if netz.gebiet_bei(0, punkt) < 0:
                return "KEIN FREIES GELÄNDE"
        elif not self.welt.frei(punkt, 14.0, 0):
            return "KEIN FREIER BODEN"
        return ""

    def belohnung_kaufen(self, k, was: str, punkt, gratis: bool = False,
                         punkt2=None) -> str:
        """Beim Gastgeber: pruefen, Punkte abziehen, ausfuehren. Gratis nur
        fuer den ADMIN (darf_gratis) - was ein anderer schickt, zaehlt nicht."""
        punkt = pygame.Vector2(punkt)
        gratis = bool(gratis) and self.darf_gratis(k)
        if was == "napalm" and punkt2 is None:
            return "RICHTUNG WÄHLEN"
        grund = self.belohnung_pruefen(k, was, punkt, gratis=gratis, punkt2=punkt2)
        if grund:
            return grund
        kosten = next(c for n, c, _t in S["belohnungen"] if n == was)
        if not gratis:
            k.schlacht_punkte -= kosten
        if was == "aufklaerung":
            self.ueberfluege.append(Ueberflug(punkt, k.team, k.fraktion,
                                              self.welt.ebene(0).pixel_breite))
            self.welt.klang("anflug", 1.0, punkt, 0)
            return ""
        if was == "fallschirmjaeger":
            self.fallschirmjaeger_abwerfen(punkt, k.team)
            return ""
        if was == "napalm":
            self.luftangriffe.append(Luftangriff(punkt, self.napalm_ende(punkt, punkt2),
                                                 k.team, k.fraktion, von=k))
            return ""
        zone = Dropzone(punkt, k.team, was, 0.0, einmalig=True)
        zone.rest = S["abwurf"]["vorlauf_kauf"]
        self.dropzonen.append(zone)
        return ""

    # ---- Netz -----------------------------------------------------------------
    def schlacht_meldung(self) -> dict:
        return {
            # Die Rueckzaehlung in halben Sekunden (seit 0.34.102): angezeigt
            # werden ganze, und jede Aenderung kostet Bandbreite.
            "dz": [[round(z.pos.x), round(z.pos.y), z.team, round(z.rest * 2.0) / 2.0, z.art,
                    1 if z.einmalig else 0, 1 if z.fahrzeug is not None else 0, z.kennung]
                   for z in self.dropzonen],
            "ab": [[round(a.pos.x), round(a.pos.y), round(a.hoehe, 1), a.art, a.team,
                    round(a.winkel), round(a.alter, 2), round(a.gerissen, 2)]
                   for a in self.abwuerfe],
            "ue": [[round(u.pos.x), round(u.pos.y), u.team] for u in self.ueberfluege],
            # Napalm-Angriffe (seit 0.34.101): Bahn und Seite, fuer die Karte.
            # Seit 0.34.130 mit dem Alter: daraus zeichnet der Gast die fallenden Bomben.
            "la": [[round(a.start.x), round(a.start.y), round(a.ende.x), round(a.ende.y), a.team,
                    round(a.alter, 2)]
                   for a in getattr(self, "luftangriffe", ())],
            # Die Eroberungspunkte der Front (seit 0.34.131).
            "fp": self.front_meldung() if self.front_an else [],
        }

    def schlacht_uebernehmen(self, m) -> None:
        """Beim Gast: Zonen und Abwuerfe nur als Bild."""
        if not isinstance(m, dict):
            return
        zonen = []
        for e in m.get("dz", []):
            try:
                z = Dropzone((float(e[0]), float(e[1])), int(e[2]), str(e[4]), 0.0,
                             bool(e[5]))
                z.rest = float(e[3])
                z.besetzt = bool(e[6])
                z.kennung = int(e[7])
                zonen.append(z)
            except (TypeError, ValueError, IndexError):
                continue
        self.dropzonen = zonen
        abw = []
        for e in m.get("ab", []):
            try:
                z = Dropzone((float(e[0]), float(e[1])), int(e[4]), str(e[3]), float(e[5]))
                a = Abwurf(z)
                a.hoehe = float(e[2])
                a.alter = float(e[6])
                a.gerissen = float(e[7]) if len(e) > 7 else 0.0
                abw.append(a)
            except (TypeError, ValueError, IndexError):
                continue
        self.abwuerfe = abw
        ue = []
        for e in m.get("ue", []):
            try:
                ue.append((pygame.Vector2(float(e[0]), float(e[1])), int(e[2])))
            except (TypeError, ValueError, IndexError):
                continue
        self._ueberfluege_gast = ue
        la = []
        alt = self.__dict__.get("_napalm_gast", {})
        neu = {}
        for e in m.get("la", []):
            try:
                la.append((pygame.Vector2(float(e[0]), float(e[1])),
                           pygame.Vector2(float(e[2]), float(e[3])), int(e[4])))
                if len(e) > 5:
                    # Derselbe Bombenplan wie beim Gastgeber (aus dem Ort), je
                    # Angriff einmal gebaut; nur das Alter kommt mit.
                    schluessel = (int(e[0]), int(e[1]), int(e[2]), int(e[3]))
                    angriff = alt.get(schluessel) or Luftangriff(la[-1][0], la[-1][1], int(e[4]), "")
                    angriff.alter = float(e[5])
                    neu[schluessel] = angriff
            except (TypeError, ValueError, IndexError):
                continue
        self._luftangriffe_gast = la
        self._napalm_gast = neu
        if m.get("fp"):
            self.front_uebernehmen(m["fp"])

    # ---- Bild: am Boden -------------------------------------------------------
    def dropzonen_zeichnen(self, flaeche, ebene: int, ecke) -> None:
        """Die Zonen auf dem Boden: ein Achteck in der Farbe der Seite mit
        Eckwinkeln, Pfeile, die nach innen laufen, und in der Mitte, was
        kommt. Steht der Abwurf kurz bevor, pulsiert sie und zaehlt."""
        if ebene != 0 or not self.dropzonen:
            return
        zeit = self.welt.zeit if self.ist_gastgeber else self._zeit
        for z in self.dropzonen:
            p = z.pos - ecke
            if not (-80 < p.x < flaeche.get_width() + 80 and -80 < p.y < flaeche.get_height() + 80):
                continue
            besetzt = z.fahrzeug is not None or getattr(z, "besetzt", False)
            self._zone_bild(flaeche, p, z, zeit, besetzt)

    # ---- Die Zone im Stil einer Evakuierungszone (seit 0.34.138) -----------
    # Gewuenscht: "wie die Extraction Zone bei XCOM 2 ... wichtig, dass diese
    # blau brennenden Fackeln, das blaue Feuer, was diesen blauen Smoke macht,
    # an den Ecken da ist", animiert, und so gross wie das Fahrzeug. Alles
    # haengt nur an der Zeit - beim Gast sieht es genauso aus.
    _FACKEL = (90, 170, 255)
    _FACKEL_KERN = (215, 240, 255)
    _RAUCH = (96, 138, 214)

    def _zone_mass(self, art: str) -> tuple:
        """(Laenge, Breite) der Zone: das Bild des Fahrzeugs plus Rand."""
        merk = self.__dict__.setdefault("_zonen_mass", {})
        if art in merk:
            return merk[art]
        d = S["dropzone"]
        if art not in fahrzeug_modul.ARTEN:
            mass = (d["kiste"], d["kiste"])
        else:
            try:
                if getattr(fahrzeug_modul.ARTEN.get(art), "rechteckig", False):
                    bild = self._fracht_ganz(art)
                else:
                    bild = self.renderer.bilder.bild(art)
                bb = bild.get_bounding_rect()
                mass = (bb.width + 2 * d["rand"], bb.height + 2 * d["rand"])
            except Exception:                  # noqa: BLE001  ohne Bild: Vorgabe
                mass = (2 * d["radius"], d["radius"])
        merk[art] = mass
        return mass

    def _zone_fest(self, z, besetzt: bool, freund: bool):
        """Was sich nicht bewegt: Grund, Raster und Hologramm, gedreht.
        Gemerkt je Art, Winkel und Zustand."""
        merk = self.__dict__.setdefault("_zonen_fest", {})
        winkel = int(round(z.winkel)) % 360
        schluessel = (z.art, winkel, besetzt, freund)
        fest = merk.get(schluessel)
        if fest is not None:
            return fest
        laenge, breite = self._zone_mass(z.art)
        rand = S["dropzone"]["rand"]
        f = pygame.Surface((laenge, breite), pygame.SRCALPHA)
        grund = (40, 90, 150) if freund else (130, 50, 46)
        f.fill(grund + (34 if besetzt else 58,))
        linie = (120, 190, 255, 46) if freund else (240, 120, 100, 46)
        for x in range(0, laenge, 8):
            pygame.draw.line(f, linie, (x, 0), (x, breite - 1))
        for y in range(0, breite, 8):
            pygame.draw.line(f, linie, (0, y), (laenge - 1, y))
        if z.art in fahrzeug_modul.ARTEN and not besetzt:
            # Das Hologramm des Fahrzeugs: wie gross es ist und wohin es schaut.
            try:
                if getattr(fahrzeug_modul.ARTEN.get(z.art), "rechteckig", False):
                    bild = self._fracht_ganz(z.art)
                else:
                    bild = self.renderer.bilder.bild(z.art)
                bild = bild.subsurface(bild.get_bounding_rect())
                holo = pygame.mask.from_surface(bild, 40).to_surface(
                    setcolor=(140, 200, 255, 70) if freund else (255, 150, 130, 70),
                    unsetcolor=(0, 0, 0, 0))
                f.blit(holo, holo.get_rect(center=(laenge // 2, breite // 2)))
            except Exception:                  # noqa: BLE001
                pass
        elif z.art not in fahrzeug_modul.ARTEN:
            zeichen = S["dropzone"]["zeichen"].get(z.art, "?")
            SCHRIFT.zeichnen(f, zeichen, laenge // 2, breite // 2 - 3,
                             (190, 225, 255) if freund else (255, 190, 170), 1, ausrichtung="mitte")
        del rand
        fest = pygame.transform.rotate(f, -winkel)
        if len(merk) > 120:
            merk.clear()
        merk[schluessel] = fest
        return fest

    def _zone_ecken(self, z, cx: float, cy: float) -> list:
        laenge, breite = self._zone_mass(z.art)
        vorn = pygame.Vector2(1, 0).rotate(z.winkel)
        quer = pygame.Vector2(-vorn.y, vorn.x)
        m = pygame.Vector2(cx, cy)
        return [m + vorn * (sx * laenge / 2) + quer * (sy * breite / 2)
                for sx, sy in ((1, 1), (1, -1), (-1, -1), (-1, 1))]

    def _hauch(self, radius: int, farbe) -> pygame.Surface:
        """Ein weicher runder Fleck (Rauch, Leuchthof), gemerkt je Groesse."""
        merk = self.__dict__.setdefault("_zonen_hauch", {})
        schluessel = (radius, farbe)
        s = merk.get(schluessel)
        if s is None:
            s = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
            for r in range(radius, 0, -1):
                a = int(255 * (1.0 - r / float(radius + 1)) ** 1.6)
                pygame.draw.circle(s, farbe + (a,), (radius + 1, radius + 1), r)
            merk[schluessel] = s
        return s

    def _leuchten(self, radius: int, farbe, staerke: float) -> pygame.Surface:
        """Ein Leuchtfleck zum Addieren (BLEND_RGB_ADD): die Farbe ist schon mit
        der Staerke verrechnet - beim Addieren wirkt set_alpha nicht."""
        merk = self.__dict__.setdefault("_zonen_licht", {})
        stufe = max(0, min(10, int(round(staerke * 10))))
        schluessel = (radius, farbe, stufe)
        s = merk.get(schluessel)
        if s is None:
            s = pygame.Surface((radius * 2 + 2, radius * 2 + 2))
            s.fill((0, 0, 0))
            for r in range(radius, 0, -1):
                k = (1.0 - r / float(radius + 1)) ** 2 * stufe / 10.0
                pygame.draw.circle(s, tuple(int(c * k) for c in farbe), (radius + 1, radius + 1), r)
            merk[schluessel] = s
        return s

    def _fackel(self, flaeche, ort, zeit: float, nr: int, stark: float) -> None:
        """Eine blau brennende Fackel mit Rauch (XCOM 2, gewuenscht)."""
        x, y = int(ort.x), int(ort.y)
        d = S["dropzone"]
        # Rauch: Wolken steigen auf, wachsen, verwehen und vergehen.
        n = d["rauch"]
        for i in range(n):
            alter = (zeit * d["rauch_tempo"] + i / float(n) + nr * 0.37) % 1.0
            wind = math.sin(zeit * 0.7 + nr * 1.9 + i) * 3.0
            px = x + wind * alter + d["wind"] * alter * 10.0
            py = y - 4 - d["steigen"] * alter
            r = int(2 + d["rauch_gross"] * alter)
            puff = self._hauch(r, self._RAUCH)
            puff.set_alpha(int(min(255, 230 * (1.0 - alter) * min(1.0, stark) * min(1.0, alter * 6.0))))
            flaeche.blit(puff, (px - r - 1, py - r - 1))
        # Der Stab und der Leuchthof.
        pygame.draw.line(flaeche, (60, 40, 34), (x, y + 2), (x, y - 2), 2)
        flacker = 0.75 + 0.25 * math.sin(zeit * 23.0 + nr * 2.1) * math.sin(zeit * 13.0 + nr)
        hof = self._leuchten(int(8 + 5 * min(1.0, stark)), self._FACKEL, 0.6 * flacker * min(1.2, stark))
        flaeche.blit(hof, (x - hof.get_width() // 2, y - 3 - hof.get_height() // 2),
                     special_flags=pygame.BLEND_RGB_ADD)
        # Die Flamme: zwei, drei zuckende Zungen.
        for k in range(3):
            h = (4 + 5 * stark) * (0.7 + 0.3 * math.sin(zeit * (17 + k * 5) + nr + k))
            dx = (k - 1) * 1.2
            pygame.draw.line(flaeche, self._FACKEL, (x + dx, y - 2), (x + dx * 0.5, y - 2 - h), 2)
        pygame.draw.circle(flaeche, self._FACKEL_KERN, (x, y - 3), 1)

    def _zone_bild(self, flaeche, p, z, zeit: float, besetzt: bool) -> None:
        ich = getattr(self, "ich", None)
        freund = ich is None or z.team not in (0, 1) or z.team == getattr(ich, "team", -1)
        bald = 0.0 <= z.rest <= S["abwurf"]["vorlauf"] and not besetzt
        cx, cy = float(p.x), float(p.y)
        fest = self._zone_fest(z, besetzt, freund)
        flaeche.blit(fest, fest.get_rect(center=(int(cx), int(cy))))
        ecken = self._zone_ecken(z, cx, cy)
        farbe = (120, 200, 255) if freund else (255, 110, 90)
        puls = 0.5 + 0.5 * math.sin(zeit * (9.0 if bald else 2.4))
        if besetzt:
            farbe = tuple(int(c * 0.45) for c in farbe)
        # Der Rand: laufende Striche, dazu Eckklammern.
        lauf = (zeit * (40.0 if bald else 14.0)) % 10.0
        for a, b in zip(ecken, ecken[1:] + ecken[:1]):
            weg = b - a
            lang = weg.length()
            if lang < 1.0:
                continue
            richtung = weg / lang
            t = -lauf
            while t < lang:
                s0, s1 = max(0.0, t), min(lang, t + 6.0)
                if s1 > s0:
                    pygame.draw.line(flaeche, farbe, a + richtung * s0, a + richtung * s1, 1)
                t += 10.0
        for i, e in enumerate(ecken):
            nach = ecken[(i + 1) % 4] - e
            vor = ecken[i - 1] - e
            for w in (nach, vor):
                if w.length_squared() > 1.0:
                    pygame.draw.line(flaeche, farbe, e, e + w.normalize() * 7, 2)
        # Ein Scanstreifen wandert ueber die Zone.
        if not besetzt:
            t = (zeit * (0.9 if bald else 0.35)) % 1.0
            a = ecken[3].lerp(ecken[0], t)
            b = ecken[2].lerp(ecken[1], t)
            hell = tuple(min(255, int(c + 60 * puls)) for c in farbe)
            pygame.draw.line(flaeche, hell, a, b, 1)
        # Die Fackeln an den Ecken.
        stark = 0.35 if besetzt else (1.0 + 0.35 * puls if bald else 0.85)
        for i, e in enumerate(ecken):
            self._fackel(flaeche, e, zeit, i + (z.kennung if isinstance(getattr(z, "kennung", 0), int) else 0),
                         stark)
        if bald:
            # Pfeile laufen nach innen, und eine Lichtsaeule steht ueber der Mitte.
            for e in ecken:
                hin = pygame.Vector2(cx, cy) - e
                if hin.length_squared() < 1.0:
                    continue
                for j in range(2):
                    t = ((zeit * 1.6) + j * 0.5) % 1.0
                    q = e + hin * (0.15 + 0.5 * t)
                    sp = hin.normalize() * 4
                    qu = pygame.Vector2(-sp.y, sp.x) * 0.8
                    pygame.draw.lines(flaeche, farbe, False, [q - sp + qu, q, q - sp - qu])
            saeule = self._leuchten(12, self._FACKEL, 0.12 + 0.12 * puls)
            for h in range(0, 60, 8):
                flaeche.blit(saeule, (int(cx) - 13, int(cy) - 13 - h), special_flags=pygame.BLEND_RGB_ADD)
            if z.rest > 0.0:
                laenge, breite = self._zone_mass(z.art)
                SCHRIFT.zeichnen(flaeche, "ABWURF %d" % int(math.ceil(z.rest)), int(cx),
                                 int(cy) - max(laenge, breite) // 2 - 14, farbe, 1, ausrichtung="mitte")

    # ---- Bild: in der Luft ---------------------------------------------------
    def napalm_bomben_zeichnen(self, ziel) -> None:
        """Die fallenden Napalmbomben (seit 0.34.130, gewuenscht): der Bomber
        bleibt unsichtbar, aber seine Bomben sieht man - sie loesen sich in
        der Hoehe, fliegen mit seinem Schwung ein Stueck mit, kippen mit der
        Nase nach unten und schlagen genau dort ein, wo das Feuer entsteht.
        Darunter waechst ihr Schatten. Beim Gastgeber und beim Gast."""
        n = S["napalm"]
        angriffe = (list(getattr(self, "luftangriffe", ())) if self.ist_gastgeber
                    else list(self.__dict__.get("_napalm_gast", {}).values()))
        if not angriffe:
            return
        ecke = self.kamera.ecke
        breite, hoehe = ziel.get_size()
        for la in angriffe:
            vorn = la.ende - la.start
            vorn = vorn.normalize() if vorn.length_squared() > 1.0 else pygame.Vector2(1, 0)
            for t_ein, ort, _r, _d in la.bomben:
                rest = t_ein - la.alter
                if not (0.0 < rest <= n["fall"]):
                    continue
                q = 1.0 - rest / n["fall"]
                hoch = n["bombe_hoehe"] * (1.0 - q * q)
                boden = ort - vorn * (n["tempo"] * n["bombe_schwung"] * rest) - ecke
                if not (-40 < boden.x < breite + 40 and -40 - hoch < boden.y < hoehe + 40):
                    continue
                sw = int(3 + 6 * q)
                sch = pygame.Surface((sw * 2, max(2, sw)), pygame.SRCALPHA)
                pygame.draw.ellipse(sch, (10, 8, 6, int(40 + 90 * q)), sch.get_rect())
                ziel.blit(sch, (boden.x - sw, boden.y - sw // 2))
                # Im Bild: vorwaerts mit dem Schwung, nach unten immer schneller.
                vx = vorn.x * n["tempo"] * n["bombe_schwung"]
                vy = vorn.y * n["tempo"] * n["bombe_schwung"] + 2.0 * n["bombe_hoehe"] * q / n["fall"]
                bild = _napalm_bombe(math.degrees(math.atan2(vy, vx)))
                ziel.blit(bild, bild.get_rect(center=(int(boden.x), int(boden.y - hoch))))

    def abwuerfe_zeichnen(self, ziel, misch: float) -> None:
        """Ueber allem: der Schatten am Boden (je tiefer, desto groesser und
        dunkler), die Last etwas hoeher und groesser, darueber der Schirm."""
        ecke = self.kamera.ecke
        r = self.renderer
        a = S["abwurf"]
        for ab in self.abwuerfe:
            boden = ab.pos - ecke
            hoch = max(0.0, ab.hoehe)
            anteil = 1.0 - min(1.0, hoch / a["hoehe"])
            # Schatten.
            sw = int(16 + 22 * anteil)
            sch = pygame.Surface((sw * 2, sw), pygame.SRCALPHA)
            pygame.draw.ellipse(sch, (12, 9, 6, int(50 + 110 * anteil)), sch.get_rect())
            ziel.blit(sch, (boden.x - sw, boden.y - sw // 2))
            # Kurz vor dem Aufsetzen: der Fussabdruck blinkt rot (seit 0.34.100)
            # - wer drin steht, wird beiseite gestossen.
            if hoch < a["warnen_ab"] and int(self._zeit_jetzt() * 6) % 2 == 0:
                fuss = int(self.abwurf_fuss(ab.art))
                pygame.draw.ellipse(ziel, K.C_RED, (int(boden.x) - fuss, int(boden.y) - int(fuss * 0.62),
                                                    fuss * 2, int(fuss * 1.24)), 1)
            # Die Last: pendelt leicht - mit gerissenem Schirm (seit 0.34.118)
            # nicht mehr, sondern dreht sich im Sturz.
            if ab.gerissen > 0.0:
                pendel = 0.0
                sturz = ab.winkel + 70.0 * ab.gerissen * (1 if ab.kennung % 2 == 0 else -1)
            else:
                pendel = math.sin(ab.alter * 2.4) * 6.0 * (1.0 - anteil * 0.5)
                sturz = ab.winkel + pendel * 0.8
            hub = hoch * a["bild_hub"]
            last = boden + pygame.Vector2(pendel, -hub)
            self._fracht_zeichnen(ziel, ab.art, last, sturz)
            # Der Schirm - ab ist er nach dem Riss.
            gross = ab.art in fahrzeug_modul.ARTEN
            if ab.gerissen <= 0.0:
                schirm = last + pygame.Vector2(pendel * 0.4, -a["schirm_ueber"] * (1.6 if gross else 1.0))
                self._schirm_zeichnen(ziel, schirm, last, ab.team,
                                      a["schirm"] if gross else a["schirm_kiste"])

        # Fallschirmjaeger: Schatten am Boden zeichnet der Renderer (wie fuer
        # jede Figur), die Figur haengt darueber am eigenen Schirm.
        for k in self.kaempfer.values():
            hoch = getattr(k, "schirm_hoehe", 0.0)
            if hoch <= 0.0 or not k.lebt or int(k.ebene) != int(getattr(self, "blick", 0)):
                continue
            boden = k.pos - ecke
            if not (-200 < boden.x < K.GAME_W + 200 and -400 < boden.y < K.GAME_H + 400):
                continue
            pendel = math.sin(self._zeit_jetzt() * 2.0 + k.nummer) * 4.0
            last = boden + pygame.Vector2(pendel, -hoch * a["bild_hub"])
            bild = k.bild
            if bild:
                s = r.bilder.gedreht(bild, k.winkel)
                ziel.blit(s, s.get_rect(center=(int(last.x), int(last.y))))
            schirm = last + pygame.Vector2(pendel * 0.3, -a["schirm_ueber"] * 0.9)
            self._schirm_zeichnen(ziel, schirm, last, k.team, S["fallschirmjaeger_schirm"])

    def _fracht_zeichnen(self, ziel, art: str, p, winkel: float) -> None:
        bilder = self.renderer.bilder
        if art in ("munition", "medkit"):
            # Seit 0.34.138 so viele Kisten, wie unten liegen, und genau dort,
            # wo sie landen (_abwurf_landet) - vorher ein grosses Paket, das
            # am Boden zu drei kleinen wurde (gemeldet).
            s = bilder.bild("munikiste" if art == "munition" else "medkit")
            n = S["abwurf"]["kisten"]
            for i in range(n):
                q = pygame.Vector2(p) + pygame.Vector2(14, 0).rotate(i * 360.0 / n)
                ziel.blit(s, s.get_rect(center=(int(q.x), int(q.y))))
            return
        if not getattr(fahrzeug_modul.ARTEN.get(art), "rechteckig", False):
            # Alles, was kein Rechteck mit Aufbau ist: das Bild der Art selbst.
            s = bilder.gedreht(art, winkel)
            ziel.blit(s, s.get_rect(center=(int(p.x), int(p.y))))
            return
        # Wanne und Turm bzw. Ring als EIN Bild (seit 0.34.117): am Schirm
        # pendelt der Wagen, und vorher drehten Wanne und Aufbau getrennt
        # (jedes mit seiner eigenen Rasterung) - die Luke und das Geschuetz
        # wanderten gegen den Rest. Jetzt wird einmal im Ruhezustand
        # zusammengesetzt und das ganze Bild gedreht.
        ganz = self._fracht_ganz(art)
        k = int(round(winkel))
        gedreht = self.__dict__.setdefault("_fracht_gedreht", {})
        s = gedreht.get((art, k))
        if s is None:
            s = gedreht[(art, k)] = pygame.transform.rotate(ganz, -k)
        ziel.blit(s, s.get_rect(center=(int(p.x), int(p.y))))

    def _fracht_ganz(self, art: str) -> pygame.Surface:
        """Der Wagen mit seinem Aufbau, nach rechts gerichtet, leer und
        ruhend - auf einer Flaeche, die fuer jede Drehung gross genug ist."""
        vorrat = self.__dict__.setdefault("_fracht_ganz_bilder", {})
        s = vorrat.get(art)
        if s is None:
            v = fahrzeug_modul.neu(art, (0, 0), 0, 0.0, nur_bild=True)
            v.winkel = 0.0
            v.aufbau = 0.0
            v.ruecklauf = v.ruck = 0.0
            w = v._wanne_flaeche(self.renderer.bilder)
            n = int(max(w.get_width(), w.get_height()) * 1.5)
            s = pygame.Surface((n, n), pygame.SRCALPHA)
            s.blit(w, w.get_rect(center=(n // 2, n // 2)))
            v.zeichnen_oben(self.renderer, s, pygame.Vector2(n // 2, n // 2))
            vorrat[art] = s
        return s

    @staticmethod
    def _schirm_zeichnen(ziel, schirm, last, team: int, groesse) -> None:
        kombi = K.TEAMS["kombi"][team] if 0 <= team < 2 else None
        hell = kombi["rumpf"] if kombi else (200, 190, 170)
        breit, hoch = groesse
        x, y = int(schirm.x), int(schirm.y)
        rect = pygame.Rect(x - breit // 2, y - hoch, breit, hoch * 2)
        # Bahnen: abwechselnd hell und weiss, als Kuppel.
        bahnen = 6
        for i in range(bahnen):
            a0 = math.pi + math.pi * i / bahnen
            a1 = math.pi + math.pi * (i + 1) / bahnen
            pts = [(x, y)]
            for t in range(5):
                a = a0 + (a1 - a0) * t / 4
                pts.append((x + math.cos(a) * breit / 2, y + math.sin(a) * hoch))
            farbe = hell if i % 2 == 0 else (232, 226, 210)
            pygame.draw.polygon(ziel, farbe, pts)
        pygame.draw.arc(ziel, (40, 32, 26), rect, 0.0, math.pi, 1)
        pygame.draw.line(ziel, (40, 32, 26), (x - breit // 2, y), (x + breit // 2, y))
        # Leinen zur Last.
        for dx in (-breit // 2, -breit // 6, breit // 6, breit // 2):
            pygame.draw.line(ziel, (70, 62, 54), (x + dx, y), (int(last.x), int(last.y) - 4))

    def ueberfluege_zeichnen(self, ziel) -> None:
        """Die grosse Aufklaerungsdrohne, hoch oben (seit 0.34.100 gewuenscht:
        "mehr wie eine realistische grosse Aufklaerungsdrohne, modernes
        Design, mehr wie eine A-10, keine Rotoren, deutlich hoeher").

        Am Boden liegt ihr Suchkreis und ihr Schatten. Die Maschine selbst
        steht weit darueber (flug_hub) und zieht schneller durchs Bild als
        der Boden (parallaxe) - so wirkt sie hoch, ohne dass man den Boden
        unter ihr aus den Augen verliert."""
        ecke = self.kamera.ecke
        a = S["aufklaerung"]
        mitte_bild = pygame.Vector2(K.GAME_W / 2.0, K.GAME_H / 2.0)
        zeit = self.welt.zeit if self.ist_gastgeber else self._zeit
        for pos, team in self._drohnen_fuer_karte():
            p = pos - ecke
            kombi = K.TEAMS["kombi"][team] if 0 <= team < 2 else None
            farbe = kombi["hud"] if kombi else K.C_TEAL
            rr = int(a["radius"])
            # Der Kreis ist 1300 Pixel gross - einmal bauen, nicht in jedem
            # Bild (seit 0.34.99).
            schluessel = (rr, tuple(farbe))
            ringe = self.__dict__.setdefault("_sl_ringe", {})
            ring = ringe.get(schluessel)
            if ring is None:
                ring = pygame.Surface((rr * 2 + 2, rr * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(ring, tuple(farbe) + (22,), (rr + 1, rr + 1), rr)
                pygame.draw.circle(ring, tuple(farbe) + (120,), (rr + 1, rr + 1), rr, 1)
                ringe[schluessel] = ring
            ziel.blit(ring, (p.x - rr - 1, p.y - rr - 1))
            winkel = 0.0 if team != 1 else 180.0
            bild, schatten = self._drohne_bilder(team, winkel)
            # Schatten: am Boden, etwas versetzt (die Sonne steht schraeg).
            ziel.blit(schatten, schatten.get_rect(center=(int(p.x + 26), int(p.y + 14))))
            flug = p + (p - mitte_bild) * a["parallaxe"] - pygame.Vector2(0, a["flug_hub"])
            ziel.blit(bild, bild.get_rect(center=(int(flug.x), int(flug.y))))
            # Positionslichter an den Fluegelspitzen, blinkend.
            if int(zeit * 2.5) % 2 == 0:
                halb = a["spannweite"] / 2.0 - 2
                quer = pygame.Vector2(0, 1).rotate(winkel)
                links, rechts = flug - quer * halb, flug + quer * halb
                pygame.draw.circle(ziel, (255, 70, 60), (int(links.x), int(links.y)), 2)
                pygame.draw.circle(ziel, (90, 255, 120), (int(rechts.x), int(rechts.y)), 2)

    @staticmethod
    def _drohne_form(u: float):
        """Die Umrisse der Drohne, Nase nach rechts, in Pixeln (Faktor u):
        [(Farbname, Punkte), ...] in der Reihenfolge des Zeichnens."""
        def pt(liste):
            return [(x * u, y * u) for x, y in liste]
        return [
            # Hoehenleitwerk hinten, mit den beiden Seitenleitwerken an den Enden.
            ("dunkel", pt([(-44, -15), (-34, -15), (-31, 15), (-44, 15)])),
            ("rumpf", pt([(-43, -14), (-35, -14), (-33, 14), (-43, 14)])),
            ("dunkel", pt([(-46, -17), (-33, -17), (-33, -13), (-46, -13)])),
            ("dunkel", pt([(-46, 13), (-33, 13), (-33, 17), (-46, 17)])),
            # Die Tragflaeche: lang und gerade, leicht verjuengt.
            ("dunkel", pt([(-2, -49), (10, -49), (14, -5), (14, 5), (10, 49), (-2, 49), (-6, 5),
                           (-6, -5)])),
            ("rumpf", pt([(-1, -48), (9, -48), (12, -5), (12, 5), (9, 48), (-1, 48), (-4, 5),
                          (-4, -5)])),
            # Rumpf: schlank, vorn der Sensorkopf.
            ("dunkel", pt([(-40, -4), (30, -5), (42, -3), (46, 0), (42, 3), (30, 5), (-40, 4)])),
            ("rumpf", pt([(-38, -3), (30, -4), (41, -2), (44, 0), (41, 2), (30, 4), (-38, 3)])),
            ("licht", pt([(-30, -1), (34, -2), (34, 0), (-30, 0)])),
            # Zwei Triebwerke hinten oben am Rumpf, wie bei der A-10.
            ("dunkel", pt([(-26, -12), (-8, -12), (-6, -9), (-6, -5), (-8, -4), (-26, -4)])),
            ("dunkel", pt([(-26, 4), (-8, 4), (-6, 5), (-6, 9), (-8, 12), (-26, 12)])),
            ("rumpf", pt([(-24, -11), (-9, -11), (-8, -9), (-8, -6), (-9, -5), (-24, -5)])),
            ("rumpf", pt([(-24, 5), (-9, 5), (-8, 6), (-8, 9), (-9, 11), (-24, 11)])),
            ("duese", pt([(-27, -10), (-24, -10), (-24, -6), (-27, -6)])),
            ("duese", pt([(-27, 6), (-24, 6), (-24, 10), (-27, 10)])),
            # Kennstreifen der Seite auf beiden Fluegeln.
            ("seite", pt([(0, -40), (8, -40), (8.4, -34), (0.4, -34)])),
            ("seite", pt([(0.4, 34), (8.4, 34), (8, 40), (0, 40)])),
            # Sensorkuppel unter der Nase.
            ("glas", pt([(34, -2.5), (40, -2), (42, 0), (40, 2), (34, 2.5)])),
        ]

    def _drohne_bilder(self, team: int, winkel: float):
        """(Bild, Schatten) der Drohne, je Seite und Richtung einmal gebaut."""
        merk = self.__dict__.setdefault("_sl_drohne", {})
        schluessel = (team, int(winkel))
        fertig = merk.get(schluessel)
        if fertig is not None:
            return fertig
        a = S["aufklaerung"]
        u = a["spannweite"] / 98.0
        kombi = K.TEAMS["kombi"][team] if 0 <= team < 2 else None
        farben = dict(rumpf=(132, 138, 140), dunkel=(70, 74, 78), licht=(168, 174, 176),
                      duese=(34, 30, 30), glas=(40, 52, 60),
                      seite=kombi["hud"] if kombi else K.C_TEAL)
        groesse = int(110 * u) * 2
        mitte = groesse / 2.0
        bild = pygame.Surface((groesse, groesse), pygame.SRCALPHA)
        schatten = pygame.Surface((groesse, groesse), pygame.SRCALPHA)
        for name, punkte in self._drohne_form(u):
            verschoben = [(mitte + x, mitte + y) for x, y in punkte]
            pygame.draw.polygon(bild, farben[name], verschoben)
            pygame.draw.polygon(schatten, (10, 8, 6, 55), verschoben)
        # Der Schatten hoch oben ist weich und kleiner als die Maschine.
        klein = (int(groesse * 0.68), int(groesse * 0.68))
        schatten = pygame.transform.smoothscale(schatten, klein)
        if winkel:
            bild = pygame.transform.rotate(bild, -winkel)
            schatten = pygame.transform.rotate(schatten, -winkel)
        merk[schluessel] = (bild, schatten)
        return bild, schatten

    def _drohne_zeichen(self, ziel, mitte, winkel: float, farbe, gross: float) -> None:
        """Das kleine Zeichen der Drohne auf der Nachschubkarte."""
        vorn = pygame.Vector2(1, 0).rotate(winkel)
        quer = pygame.Vector2(-vorn.y, vorn.x)
        m = pygame.Vector2(mitte)
        g = gross
        rumpf = [m + vorn * g * 1.6, m - vorn * g * 1.6]
        fluegel = [m + vorn * g * 0.2 + quer * g * 1.8, m + vorn * g * 0.2 - quer * g * 1.8]
        heck = [m - vorn * g * 1.4 + quer * g * 0.7, m - vorn * g * 1.4 - quer * g * 0.7]
        dick = max(1, int(round(g * 0.45)))
        for a_, b_ in (rumpf, fluegel, heck):
            pygame.draw.line(ziel, (16, 11, 8), a_, b_, dick + 2)
        for a_, b_ in (rumpf, fluegel, heck):
            pygame.draw.line(ziel, farbe, a_, b_, dick)

    # ---- Belohnungsmenue -----------------------------------------------------
    # Seit 0.34.100 in zwei Schritten (gewuenscht: "bei TAB erst die Ability und
    # dann den Spot dafuer mit der Maus auf der Karte auswaehlen"): links
    # waehlen, was kommen soll (belohnung_wahl, -1 = noch nichts), dann auf
    # der Karte, wohin. Rechtsklick oder ESC gehen einen Schritt zurueck.
    # Solange das Menue offen ist, kommt keine Eingabe ins Spiel
    # (Gefecht._meine_eingabe, Gefecht.schritt).
    def belohnung_karte_rect(self) -> pygame.Rect:
        return pygame.Rect(232, 46, 392, 262)

    def belohnung_oeffnen(self) -> None:
        self.belohnung_offen = True
        self._wahl(-1)

    def _wahl(self, i: int) -> None:
        """Was links gewaehlt ist; ein Wechsel vergisst den Startpunkt des
        Napalm-Angriffs."""
        if i != getattr(self, "belohnung_wahl", -1):
            self._napalm_start = None
        self.belohnung_wahl = i

    def belohnung_schliessen(self) -> None:
        self.belohnung_offen = False
        self._wahl(-1)
        # Die Maustaste, mit der man angefordert hat, ist vielleicht noch
        # unten: sie soll beim Schliessen keinen Schuss ausloesen.
        self._feuer_sperre = True

    def _ist_admin_lokal(self) -> bool:
        """Ist man hier mit dem Konto ADMIN angemeldet (wie die Admin-Zeile
        auf T)? Nur dann gibt es den Schalter ALLES GRATIS."""
        konto = getattr(self.app, "_konto", None)
        return bool(konto is not None and getattr(konto, "angemeldet", False)
                    and str(getattr(konto, "name", "")).strip().lower() == "admin")

    @staticmethod
    def darf_gratis(k) -> bool:
        """Beim Gastgeber: darf `k` gratis anfordern? Nur der angemeldete
        ADMIN (dieselbe Pruefung wie fuer die Admin-Befehle) - ein Gast
        kann "gratis" schicken, so viel er will."""
        return bool(k is not None and getattr(k, "konto", None)
                    and str(getattr(k, "name", "")).strip().lower() == "admin")

    @staticmethod
    def _belohnung_zeile(i: int) -> pygame.Rect:
        # Eine Zeile je Eintrag (seit 0.34.110, damit auch 14 passen; seit
        # 0.34.114 enger, damit 15 passen); was der gewaehlte tut, steht
        # darunter (`_belohnung_hilfe_rect`).
        return pygame.Rect(16, 62 + i * 15, 206, 14)

    @staticmethod
    def _belohnung_hilfe_rect() -> pygame.Rect:
        return pygame.Rect(16, 62 + len(S["belohnungen"]) * 15 + 2, 206, 12)

    def _gratis_rect(self) -> pygame.Rect:
        return pygame.Rect(16, 62 + len(S["belohnungen"]) * 15 + 16, 206, 14)

    def belohnung_ereignis(self, ev) -> bool:
        """Tasten und Maus, solange das Menue offen ist. True: verbraucht."""
        if not self.belohnung_offen:
            return False
        liste = S["belohnungen"]
        if ev.type == pygame.KEYDOWN:
            if ev.key in self.app.opt.codes("inventar"):
                self.belohnung_schliessen()
                return True
            if ev.key == pygame.K_ESCAPE:
                if self._napalm_start is not None:
                    self._napalm_start = None          # erst den Startpunkt zurueck
                elif self.belohnung_wahl >= 0:
                    self._wahl(-1)
                else:
                    self.belohnung_schliessen()
                return True
            if pygame.K_1 <= ev.key <= pygame.K_9 and ev.key - pygame.K_1 < len(liste):
                self._wahl(ev.key - pygame.K_1)
                return True
            if ev.key in (pygame.K_UP, pygame.K_w):
                self._wahl((max(0, self.belohnung_wahl) - 1) % len(liste))
                return True
            if ev.key in (pygame.K_DOWN, pygame.K_s):
                self._wahl((self.belohnung_wahl + 1) % len(liste))
                return True
            return True
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3:
            if self._napalm_start is not None:
                self._napalm_start = None
            else:
                self._wahl(-1)
            return True
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            maus = self.app.zu_spiel(ev.pos)
            for i in range(len(liste)):
                if self._belohnung_zeile(i).collidepoint(maus):
                    self._wahl(i)
                    return True
            if self._ist_admin_lokal() and self._gratis_rect().collidepoint(maus):
                self.belohnung_gratis = not getattr(self, "belohnung_gratis", False)
                return True
            karte = self.belohnung_karte_rect()
            # Ohne Wahl ist die Karte nur Karte (seit 0.34.101): ein Klick
            # tut dann nichts.
            if karte.collidepoint(maus) and self.belohnung_wahl >= 0:
                if self._belohnung_anfordern(self._karte_zu_welt(maus)):
                    self.belohnung_schliessen()
            return True
        return ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL)

    def _karte_masse(self, r=None):
        e = self.welt.ebene(0)
        r = self.belohnung_karte_rect() if r is None else r
        f = min(r.width / float(e.pixel_breite), r.height / float(e.pixel_hoehe))
        breit, hoch = e.pixel_breite * f, e.pixel_hoehe * f
        x0 = r.x + (r.width - breit) / 2
        y0 = r.y + (r.height - hoch) / 2
        return x0, y0, f

    def _karte_feld(self) -> pygame.Rect:
        """Wo die Karte in der Nachschubtafel genau liegt (ohne Rand)."""
        x0, y0, f = self._karte_masse()
        e = self.welt.ebene(0)
        return pygame.Rect(int(x0), int(y0), int(e.pixel_breite * f), int(e.pixel_hoehe * f))

    def _karte_zu_welt(self, punkt) -> pygame.Vector2:
        x0, y0, f = self._karte_masse()
        return pygame.Vector2((punkt[0] - x0) / f, (punkt[1] - y0) / f)

    def _welt_zu_karte(self, pos) -> tuple:
        x0, y0, f = self._karte_masse()
        return int(x0 + pos.x * f), int(y0 + pos.y * f)

    def _belohnung_anfordern(self, punkt) -> bool:
        """Anfordern, was gewaehlt ist, an `punkt`. True, wenn es ging."""
        if not (0 <= self.belohnung_wahl < len(S["belohnungen"])):
            return False
        was = S["belohnungen"][self.belohnung_wahl][0]
        ich = self.ich
        if ich is None:
            return False
        gratis = bool(getattr(self, "belohnung_gratis", False)) and self._ist_admin_lokal()
        punkt2 = None
        if was == "napalm":
            # Zwei Klicks (seit 0.34.101): erst der Start, dann die Richtung.
            if self._napalm_start is None:
                grund = self.belohnung_pruefen(ich, was, punkt, gratis=gratis)
                if grund:
                    self._sl_meldung = grund
                    self._sl_meldung_rest = 2.5
                    return False
                self._napalm_start = pygame.Vector2(punkt)
                self.welt.klang("aufheben", 0.4)
                return False
            punkt, punkt2 = self._napalm_start, pygame.Vector2(punkt)
        if self.ist_gastgeber:
            grund = self.belohnung_kaufen(ich, was, punkt, gratis=gratis, punkt2=punkt2)
        else:
            grund = self.belohnung_pruefen(ich, was, punkt, gratis=gratis, punkt2=punkt2)
            if not grund:
                nachricht = {"t": "belohnung", "was": was,
                             "x": round(punkt.x, 1), "y": round(punkt.y, 1)}
                if punkt2 is not None:
                    nachricht["x2"] = round(punkt2.x, 1)
                    nachricht["y2"] = round(punkt2.y, 1)
                if gratis:
                    nachricht["gratis"] = 1
                self.gast.senden(nachricht)
        if not grund:
            self._napalm_start = None
        self._sl_meldung = grund or "ANGEFORDERT"
        self._sl_meldung_rest = 2.5
        if not grund:
            self.welt.klang("aufheben", 0.7)
        return not grund

    def belohnung_zeichnen(self, ziel) -> None:
        if not self.belohnung_offen:
            return
        ich = self.ich
        schleier = self.__dict__.get("_sl_schleier")
        if schleier is None:
            schleier = self._sl_schleier = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
            schleier.fill((8, 6, 4, 215))
        ziel.blit(schleier, (0, 0))
        SCHRIFT.zeichnen(ziel, "NACHSCHUB", 16, 12, K.C_AMBER, 2)
        gratis = bool(getattr(self, "belohnung_gratis", False)) and self._ist_admin_lokal()
        punkte = getattr(ich, "schlacht_punkte", 0) if ich is not None else 0
        SCHRIFT.zeichnen(ziel, "PUNKTE: %d" % punkte + ("  (GRATIS)" if gratis else ""),
                         16, 34, K.C_TEAL if gratis else K.C_CREAM, 1)
        SCHRIFT.zeichnen(ziel, "KILL +%d  FAHRZEUG +HALBER PREIS  HELFEN +%d" % (
            S["punkte"]["abschuss"], S["punkte"]["aufhelfen"]),
            16, 46, K.C_MUTED, 1)
        for i, (name, kosten, text) in enumerate(S["belohnungen"]):
            r = self._belohnung_zeile(i)
            gewaehlt = i == self.belohnung_wahl
            bis = self.gesperrt_bis(name)            # seit 0.34.129: noch nicht frei
            leistbar = (gratis or punkte >= kosten) and not bis
            pygame.draw.rect(ziel, (40, 30, 20) if gewaehlt else (20, 15, 11), r)
            pygame.draw.rect(ziel, K.C_AMBER if gewaehlt else (70, 56, 40), r, 1)
            farbe = K.C_CREAM if leistbar else K.C_MUTED_DK
            SCHRIFT.zeichnen(ziel, "%d  %s" % (i + 1, text), r.x + 5, r.y + 4, farbe, 1)
            # Gesperrt: nur die Zeit ("0:46"), damit lange Namen Platz haben.
            SCHRIFT.zeichnen(ziel, bis.replace("IN ", "") or ("GRATIS" if gratis else "%d P" % kosten),
                             r.right - 5, r.y + 4,
                             K.C_AMBER if leistbar else K.C_MUTED_DK, 1, ausrichtung="rechts")
        wahl_ = self.belohnung_wahl
        if 0 <= wahl_ < len(S["belohnungen"]):
            SCHRIFT.zeichnen(ziel, S["belohnung_hilfe"].get(S["belohnungen"][wahl_][0], ""),
                             16, self._belohnung_hilfe_rect().y + 2, K.C_MUTED, 1)
        if self._ist_admin_lokal():
            r = self._gratis_rect()
            pygame.draw.rect(ziel, (16, 30, 28), r)
            pygame.draw.rect(ziel, K.C_TEAL if gratis else (50, 70, 66), r, 1)
            SCHRIFT.zeichnen(ziel, "ADMIN: ALLES GRATIS  [%s]" % ("AN" if gratis else "AUS"),
                             r.x + 5, r.y + 4, K.C_TEAL if gratis else K.C_MUTED, 1)
        self._belohnung_karte(ziel, ich)
        # Die Rangliste als Nebensache: der Stand der Seiten.
        if self.mit_teams and len(self.teampunkte) >= 2:
            SCHRIFT.zeichnen(ziel, "STAND  %s %d : %d %s" % (
                K.TEAMS["namen"][0], self.teampunkte[0], self.teampunkte[1],
                K.TEAMS["namen"][1]), 16, K.GAME_H - 34, K.C_MUTED, 1)
        meldung = getattr(self, "_sl_meldung", "")
        if meldung and getattr(self, "_sl_meldung_rest", 0.0) > 0.0:
            SCHRIFT.zeichnen(ziel, meldung, 428, K.GAME_H - 46, K.C_AMBER, 1, ausrichtung="mitte")
        if self.belohnung_wahl < 0:
            hilfe = "1. [1-%d] ODER KLICK LINKS: WAS ANFORDERN   [TAB] ZU" % len(S["belohnungen"])
        else:
            hilfe = "2. [KLICK AUF DIE KARTE] WOHIN   [RECHTSKLICK] ZURÜCK   [TAB] ZU"
        SCHRIFT.zeichnen(ziel, hilfe, K.GAME_W // 2, K.GAME_H - 18, K.C_MUTED, 1,
                         ausrichtung="mitte")

    def _belohnung_karte(self, ziel, ich) -> None:
        """Die Karte der Tafel: einmal auf der Spielflaeche und - wenn das
        Fenster groesser ist - noch einmal in Fensteraufloesung darueber
        (App.hoch_auflegen, seit 0.34.100)."""
        r = self.belohnung_karte_rect()
        pygame.draw.rect(ziel, (84, 66, 48), r, 1)
        feld = self._karte_feld()
        maus = self.app.zu_spiel(pygame.mouse.get_pos())
        self._karte_malen(ziel, feld, 1.0, maus, ich)
        if hasattr(self.app, "hoch_auflegen") and self.app.stapel and self.app.stapel[-1] is self:
            self.app.hoch_auflegen(feld, lambda f, mass: self._karte_malen(
                f, f.get_rect(), mass,
                ((maus[0] - feld.x) * f.get_width() / float(max(1, feld.width)),
                 (maus[1] - feld.y) * f.get_height() / float(max(1, feld.height))), ich))

    def _karte_malen(self, ziel, r, m: float, maus, ich) -> None:
        """Grundriss, Nebel, Zonen, Leute, Fahrzeuge, Drohnen und der
        Zeiger - in das Rechteck `r` von `ziel`, `m` mal so fein wie die
        Spielflaeche. `maus` in Koordinaten von `ziel`."""
        from . import kartenbild
        e = self.welt.ebene(0)
        f = r.width / float(e.pixel_breite)
        mm = max(1.0, float(m))

        def punkt(pos):
            return (int(r.x + pos.x * f), int(r.y + pos.y * f))

        def n(wert):
            return max(1, int(round(wert * mm)))

        alt_clip = ziel.get_clip()
        ziel.set_clip(r.clip(alt_clip) if alt_clip else r)
        ziel.blit(kartenbild.in_groesse(e, r.size), r.topleft)
        wahl = (S["belohnungen"][self.belohnung_wahl][0]
                if 0 <= self.belohnung_wahl < len(S["belohnungen"]) else "")
        fraktion = ich.fraktion if ich is not None else ""
        team = ich.team if ich is not None else -1

        # Der Nebel (seit 0.34.100): dunkel, ausser um die eigenen Leute und
        # im Kreis einer eigenen Aufklaerungsdrohne, solange sie fliegt.
        sicht = S["karte_sicht"] * f
        auf = S["aufklaerung"]["radius"] * f
        nebel = self.__dict__.get("_sl_nebel")
        if nebel is None or nebel.get_size() != r.size:
            nebel = self._sl_nebel = pygame.Surface(r.size, pygame.SRCALPHA)
        nebel.fill(S["karte_nebel"])
        loch = (0, 0, 0, 0)
        for k in self.kaempfer.values():
            if k.lebt and k.fraktion == fraktion and int(k.ebene) == 0:
                p = punkt(k.pos)
                pygame.draw.circle(nebel, loch, (p[0] - r.x, p[1] - r.y), int(sicht))
        drohnen = self._drohnen_fuer_karte()
        for pos, d_team in drohnen:
            if d_team == team:
                p = punkt(pos)
                pygame.draw.circle(nebel, loch, (p[0] - r.x, p[1] - r.y), int(auf))
        ziel.blit(nebel, r.topleft)

        def sichtbar(pos) -> bool:
            for k in self.kaempfer.values():
                if (k.lebt and k.fraktion == fraktion
                        and k.pos.distance_squared_to(pos) <= S["karte_sicht"] ** 2):
                    return True
            return any(d_team == team and q.distance_to(pos) <= S["aufklaerung"]["radius"]
                       for q, d_team in drohnen)

        # Gesperrt: um die Basis der anderen (nicht fuer die Aufklaerung).
        if wahl and wahl != "aufklaerung" and team in (0, 1):
            feind = self.schlacht_basis(1 - team)
            if feind is not None:
                rr = int(S["abwurf"]["sperre_basis"] * f)
                sperre = pygame.Surface((rr * 2, rr * 2), pygame.SRCALPHA)
                pygame.draw.circle(sperre, (200, 40, 30, 60), (rr, rr), rr)
                pygame.draw.circle(sperre, (220, 60, 40, 150), (rr, rr), rr, n(1))
                q = punkt(feind)
                ziel.blit(sperre, (q[0] - rr, q[1] - rr))
        # Feuer, die man sieht (seit 0.34.101): Napalm und Molotow.
        for brand in getattr(self.welt, "feuer", ()):
            if brand.lebt and brand.ebene == 0 and brand.staerke > 0.05 and sichtbar(brand.pos):
                q = punkt(brand.pos)
                rr = max(n(1.5), int(brand.radius * f))
                pygame.draw.circle(ziel, (150, 52, 18), q, rr)
                pygame.draw.circle(ziel, (236, 128, 40), q, max(1, rr // 2))
        # Laufende Napalm-Angriffe der eigenen Seite: ihre Bahn (seit 0.34.101).
        if self.ist_gastgeber:
            bahnen = [(a_.start, a_.ende, a_.team) for a_ in getattr(self, "luftangriffe", ())]
        else:
            bahnen = list(getattr(self, "_luftangriffe_gast", ()))
        for b_start, b_ende, b_team in bahnen:
            if b_team == team:
                self._bahn_malen(ziel, punkt(b_start), punkt(b_ende), (200, 90, 30),
                                 S["napalm"]["seitlich"] * f, mm)
        # Die Kreise der Drohnen am Himmel und ihr Flugzeug-Zeichen.
        for pos, d_team in drohnen:
            kombi = K.TEAMS["kombi"][d_team] if 0 <= d_team < 2 else None
            farbe = kombi["hud"] if kombi else K.C_TEAL
            q = punkt(pos)
            pygame.draw.circle(ziel, farbe, q, int(auf), n(1))
            self._drohne_zeichen(ziel, q, 0.0 if d_team == 0 else 180.0, farbe, 3.0 * mm)
        # Dropzonen.
        for z in self.dropzonen:
            if z.team != team and not sichtbar(z.pos):
                continue
            kombi = K.TEAMS["kombi"][z.team] if 0 <= z.team < 2 else None
            q = punkt(z.pos)
            gr = n(3)
            pygame.draw.rect(ziel, kombi["hud"] if kombi else K.C_AMBER,
                             (q[0] - gr, q[1] - gr, gr * 2 + 1, gr * 2 + 1), n(1))
        # Die Front (seit 0.34.131): Punkte mit Buchstaben, Basen mit Fahne.
        self.front_auf_karte(ziel, punkt, f, mm, namen=True)
        # Fallendes: wo gerade etwas am Schirm haengt.
        for ab in self.abwuerfe:
            if ab.team == team or sichtbar(ab.pos):
                q = punkt(ab.pos)
                pygame.draw.circle(ziel, (232, 226, 210), q, n(2), n(1))
        # Fahrzeuge: eigene und unbesetzte in Sicht, feindliche in Sicht
        # oder markiert (mit Raute, sie bewegt sich mit).
        for b in getattr(self, "fahrzeuge", ()):
            if getattr(b, "kaputt", False) or int(getattr(b, "ebene", 0)) != 0:
                continue
            seite = getattr(b, "team", -1)
            if getattr(b, "fahrer", None) is not None:
                seite = getattr(b.fahrer, "team", seite)
            markiert = self.fahrzeug_fuer_mich_markiert(b)
            if seite != team and not sichtbar(b.pos) and not markiert:
                continue
            q = punkt(b.pos)
            vorn = pygame.Vector2(1, 0).rotate(getattr(b, "winkel", 0.0))
            quer = pygame.Vector2(-vorn.y, vorn.x)
            gross = 1.6 if getattr(b, "rechteckig", False) else 1.0
            l, qq = 3.2 * gross * mm, 1.8 * gross * mm
            mq = pygame.Vector2(q)
            ecken = [mq + vorn * l + quer * qq, mq + vorn * l - quer * qq,
                     mq - vorn * l - quer * qq, mq - vorn * l + quer * qq]
            farbe = K.TEAMS["kombi"][seite]["hud"] if 0 <= seite < 2 else (214, 166, 70)
            pygame.draw.polygon(ziel, farbe, ecken)
            pygame.draw.polygon(ziel, (16, 11, 8), ecken, n(0.8))
            if markiert and seite != team:
                self._ping(ziel, (q[0], q[1] - int(6 * mm)), mm)
            if b.art == "werfer":
                from .minikarte import Minikarte
                Minikarte.werfer_zeichen(ziel, (q[0], q[1] - int(1 * mm)), mm)
        # Leute: eigene als Punkte, Gegner in Sicht oder markiert als Raute.
        for k in self.kaempfer.values():
            if not (k.lebt or getattr(k, "am_boden", False)) or int(k.ebene) != 0:
                continue
            if getattr(k, "im_fahrzeug", False) or getattr(k, "raus", False):
                continue
            q = punkt(k.pos)
            if k.fraktion == fraktion:
                if k is ich:
                    continue
                pygame.draw.circle(ziel, (16, 11, 8), q, n(2.2))
                pygame.draw.circle(ziel, self._farbe_fuer(k), q, n(1.5))
            elif self.fuer_mich_markiert(k) or (k.lebt and sichtbar(k.pos)):
                self._ping(ziel, q, mm)
        # Fallschirmjaeger in der Luft (seit 0.34.100).
        for k in self.kaempfer.values():
            if k.lebt and getattr(k, "schirm_hoehe", 0.0) > 0.0 and (
                    k.fraktion == fraktion or sichtbar(k.pos)):
                q = punkt(k.pos)
                pygame.draw.circle(ziel, (232, 226, 210), (q[0], q[1] - n(2)), n(2), n(1))
        if ich is not None:
            q = punkt(ich.pos)
            vorn = pygame.Vector2(1, 0).rotate(getattr(ich, "winkel", 0.0))
            quer = pygame.Vector2(-vorn.y, vorn.x)
            g = 2.6 * mm
            mq = pygame.Vector2(q)
            ecken = [mq + vorn * g * 1.4, mq - vorn * g * 0.8 + quer * g * 0.9,
                     mq - vorn * g * 0.35, mq - vorn * g * 0.8 - quer * g * 0.9]
            pygame.draw.polygon(ziel, (16, 11, 8), ecken, max(2, int(g * 0.6)))
            pygame.draw.polygon(ziel, (236, 255, 250), ecken)
        # Napalm (seit 0.34.101): nach dem ersten Klick die ganze Bahn,
        # immer gleich lang - sie reicht auch ueber den Zeiger hinaus.
        if wahl == "napalm" and ich is not None and self._napalm_start is not None:
            start = self._napalm_start
            welt = pygame.Vector2((maus[0] - r.x) / f, (maus[1] - r.y) / f)
            ende = self.napalm_ende(start, welt)
            gratis = bool(getattr(self, "belohnung_gratis", False)) and self._ist_admin_lokal()
            grund = (self.belohnung_pruefen(ich, wahl, start, gratis=gratis, punkt2=welt)
                     if ende is not None else "RICHTUNG WÄHLEN")
            self._bahn_malen(ziel, punkt(start), punkt(ende) if ende is not None else None,
                             K.C_ORANGE if not grund else K.C_RED,
                             S["napalm"]["seitlich"] * f + S["napalm"]["radius"][1] * f * 0.6, mm)
            groesse = max(1, int(round(mm)))
            q = punkt(start)
            SCHRIFT.zeichnen(ziel, grund or "RICHTUNG: KLICKEN", q[0], q[1] - n(14),
                             K.C_ORANGE if not grund else K.C_RED, groesse, ausrichtung="mitte")
        # Unter der Maus: wie gross das Ziel ist, und ob es geht.
        elif wahl and ich is not None and r.collidepoint(maus):
            welt = pygame.Vector2((maus[0] - r.x) / f, (maus[1] - r.y) / f)
            gratis = bool(getattr(self, "belohnung_gratis", False)) and self._ist_admin_lokal()
            grund = self.belohnung_pruefen(ich, wahl, welt, gratis=gratis)
            weite = (S["aufklaerung"]["radius"] if wahl == "aufklaerung"
                     else S["fallschirmjaeger"]["breite"] if wahl == "fallschirmjaeger"
                     else S["napalm"]["radius"][1] if wahl == "napalm"
                     else S["dropzone"]["radius"])
            rr = max(n(3), int(weite * f))
            farbe = K.C_TEAL if not grund else K.C_RED
            mp = (int(maus[0]), int(maus[1]))
            pygame.draw.circle(ziel, farbe, mp, rr, n(1))
            pygame.draw.line(ziel, farbe, (mp[0] - n(4), mp[1]), (mp[0] + n(4), mp[1]), n(1))
            pygame.draw.line(ziel, farbe, (mp[0], mp[1] - n(4)), (mp[0], mp[1] + n(4)), n(1))
            groesse = max(1, int(round(mm)))
            text = grund or ("STARTPUNKT DER BAHN" if wahl == "napalm" else "HIER ANFORDERN")
            SCHRIFT.zeichnen(ziel, text, mp[0], mp[1] - rr - n(10),
                             farbe, groesse, ausrichtung="mitte")
        # Ohne Wahl ist die Karte einfach die Karte (seit 0.34.101, gewuenscht:
        # "das soll auch als normale Map dienen") - kein Schleier, kein Text.
        ziel.set_clip(alt_clip)

    @staticmethod
    def _bahn_malen(ziel, a, b, farbe, breite: float, mm: float) -> None:
        """Die Bahn eines Napalm-Angriffs: Mittellinie gestrichelt, die
        Raender duenn, Pfeile in Flugrichtung."""
        n = max(1, int(round(mm)))
        pygame.draw.circle(ziel, farbe, a, max(2, int(3 * mm)), n)
        if b is None:
            return
        va, vb = pygame.Vector2(a), pygame.Vector2(b)
        laenge = va.distance_to(vb)
        if laenge < 2:
            return
        vorn = (vb - va) / laenge
        quer = pygame.Vector2(-vorn.y, vorn.x) * max(2.0, breite)
        for seite in (quer, -quer):
            pygame.draw.line(ziel, tuple(int(c * 0.6) for c in farbe), va + seite, vb + seite, n)
        strich = max(4.0, 6.0 * mm)
        t = 0.0
        while t < laenge:
            p0 = va + vorn * t
            p1 = va + vorn * min(laenge, t + strich)
            pygame.draw.line(ziel, farbe, p0, p1, n + 1)
            t += strich * 2
        pfeil = max(4.0, 5.0 * mm)
        for i in range(1, 5):
            p = va + vorn * (laenge * i / 5.0)
            pygame.draw.polygon(ziel, farbe, [p + vorn * pfeil, p - vorn * pfeil * 0.4 + quer.normalize() * pfeil * 0.8,
                                              p - vorn * pfeil * 0.4 - quer.normalize() * pfeil * 0.8])
        pygame.draw.circle(ziel, farbe, vb, max(2, int(2 * mm)))

    @staticmethod
    def _ping(ziel, mitte, mm: float) -> None:
        """Eine rote Raute ueber einem markierten Gegner."""
        x, y = mitte
        g = max(2, int(round(2.4 * mm)))
        rand = max(1, int(round(mm)))
        pygame.draw.polygon(ziel, (16, 11, 8), [(x, y - g - rand), (x + g + rand, y),
                                                 (x, y + g + rand), (x - g - rand, y)])
        pygame.draw.polygon(ziel, K.C_RED, [(x, y - g), (x + g, y), (x, y + g), (x - g, y)])

    def _drohnen_fuer_karte(self) -> list:
        """[(Ort, Team)] der Aufklaerungsdrohnen, die gerade fliegen."""
        if self.ist_gastgeber:
            return [(u.pos, u.team) for u in self.ueberfluege]
        return [(e[0], e[1]) for e in getattr(self, "_ueberfluege_gast", [])]

    def fahrzeug_fuer_mich_markiert(self, b) -> bool:
        """Hat eine eigene Drohne dieses Fahrzeug markiert (seit 0.34.100)?"""
        ich = self.ich
        return (ich is not None and getattr(b, "markiert_rest", 0.0) > 0.0
                and getattr(b, "markiert_fuer", "") == ich.fraktion)
