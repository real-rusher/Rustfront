"""Bauen, Fallen, Aufklaerung, Sanitasche und Munitionskiste (seit 0.34.69).

Aus dem Waffenpaket (`WAFFEN.md`, Abschnitte Bauen, Fallen, Aufklaerung,
Unterstuetzung). Gemeldet: "Das Ganze, was mit Bauen zu tun hat, schon mal
soweit fertig machen und Fallen auch fertig machen, aber erstmal nur fuer
den Testmodus". Darum stehen sie nur im Spawner des Testmodus
(testmodus.eintraege, Gruppen BAUEN, FALLEN, AUFKLAERUNG, HILFE) und gehen
nicht ueber das Netz - der Testmodus hat keine Gaeste.

Alles hier ist ein Wesen in `welt.wesen`, damit Kugeln, Granaten und der
EMP es finden. Wem es gehoert, sagt die Fraktion (`team0`, `team1` ...):
die eigenen Leute loesen nichts aus und werden nicht beschossen.

Was eine Figur sieht oder hoert, markiert sie (`markiert_rest`, die
Testmodus-Anzeige zeichnet eine Raute darueber). Gefragt werden nur
`welt.wesen` und `ki_unsichtbar` - nie der Beobachter (AGENTS.md).
"""
from __future__ import annotations

import math

import pygame

from . import config as K
from .entities import (RND, Brandflaeche, Geschoss, Wesen, schaden_an, wolke)

A = K.AUSRUESTUNG

# Wer fuer Fallen, Geschuetze und Aufklaerung kein Gegner ist.
_KEINE_ZIELE = ("geschoss", "neutral", "zivil", "falle")


def ist_gegner(ding, fraktion: str) -> bool:
    """Ist `ding` fuer jemanden mit `fraktion` ein Gegner, den man sieht?"""
    return (getattr(ding, "lebt", False) and getattr(ding, "trefferbar", False)
            and getattr(ding, "fraktion", "") not in _KEINE_ZIELE + (fraktion,)
            and not getattr(ding, "ki_unsichtbar", False)
            and not getattr(ding, "am_boden", False)
            and not getattr(ding, "ist_ausruestung", False))


def markieren(ding, fuer: str = "") -> None:
    """`fuer`: die Fraktion, die es jetzt weiss (seit 0.34.95). Im Gefecht
    sieht sie den Markierten auch im Nebel und auf der Karte."""
    ding.markiert_rest = max(getattr(ding, "markiert_rest", 0.0), A["markiert"])
    if fuer:
        ding.markiert_fuer = fuer


class Ausruestung(Wesen):
    """Was gebaut oder hingestellt wird. Steht, wird nicht geschoben."""

    schiebbar = False
    schiebt = True
    zaehlt_treffer = False
    treffer_art = "metall"
    ist_ausruestung = True
    # Der EMP schaltet Technik aus (entities.Granate.zuenden).
    technik = False
    emp_rest = 0.0

    def __init__(self, pos, ebene: int, fraktion: str, art: str) -> None:
        werte = A.get(art, {})
        self.max_leben = float(werte.get("leben", 1.0))
        super().__init__(pos, ebene)
        self.fraktion = fraktion
        self.art = art
        self.radius = float(werte.get("radius", 8.0))

    def emp_treffen(self, dauer: float) -> None:
        if self.technik:
            self.emp_rest = max(self.emp_rest, float(dauer))

    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        self.tempo.update(0, 0)
        if self.emp_rest > 0.0:
            self.emp_rest = max(0.0, self.emp_rest - dt)
            if RND.random() < dt * 8:
                wolke(self.welt, self.pos, 1, 60, 0.25, (150, 220, 255), self.ebene, 1, "funke")


# ── Bauen ──────────────────────────────────────────────────────────────

class Sandsack(Ausruestung):
    """Ein Stueck Sandsackwand: haelt Kugeln auf (bis es zerfaellt),
    nicht aber, was durch niedrige Deckung geht. Mehrere nebeneinander
    sind eine Wand (sandsackwand)."""

    bild = "teil_sackwand"
    treffer_art = "organisch"

    def __init__(self, pos, ebene: int, fraktion: str, winkel: float = 0.0) -> None:
        super().__init__(pos, ebene, "neutral", "sandsack")
        self.winkel = float(winkel)

    def sterben(self, von=None) -> None:
        wolke(self.welt, self.pos, 14, 90, 0.6, K.C_SAND, self.ebene, 2, "staub")
        super().sterben(von)


def sandsackwand(pos, ebene: int, winkel: float) -> list:
    """Drei Stuecke quer zur Blickrichtung."""
    s = A["sandsack"]
    quer = pygame.Vector2(0, 1).rotate(winkel)
    mitte = (s["stuecke"] - 1) / 2.0
    return [Sandsack(pygame.Vector2(pos) + quer * (i - mitte) * s["abstand"], ebene, "neutral",
                     winkel) for i in range(s["stuecke"])]


class Stacheldraht(Ausruestung):
    """Ein Streifen Draht: wer hindurch will, kommt nur langsam voran und
    reisst sich auf. Kugeln gehen hindurch (`trefferbar` aus)."""

    bild = "stacheldraht"
    trefferbar = False
    schiebt = False

    def __init__(self, pos, ebene: int, fraktion: str, winkel: float = 0.0) -> None:
        super().__init__(pos, ebene, "neutral", "stacheldraht")
        self.winkel = float(winkel)

    def _drin(self, punkt, radius: float) -> bool:
        d = A["stacheldraht"]
        lok = (pygame.Vector2(punkt) - self.pos).rotate(-self.winkel)
        return abs(lok.x) <= d["laenge"] / 2 + radius and abs(lok.y) <= d["breite"] / 2 + radius

    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        d = A["stacheldraht"]
        for a in self.welt.nahe(self.pos, d["laenge"], self.ebene):
            if (a is self or not a.lebt or getattr(a, "ist_ausruestung", False)
                    or getattr(a, "fraktion", "") == "geschoss" or getattr(a, "ist_fahrzeug", False)
                    or getattr(a, "flug", 0.0) > 0 or not self._drin(a.pos, a.radius)):
                continue
            # Langsam (Spieler.schritt bzw. KampfGegner.schritt lesen
            # `draht_rest`), und wer sich bewegt, blutet.
            a.draht_rest = 0.1
            if a.tempo.length() > 15.0:
                a.schaden(d["schaden"] * dt, None, None)


# ── Fallen ─────────────────────────────────────────────────────────────

class Sprengfalle(Ausruestung):
    """Eine versteckte Ladung mit Ausloeser: Druckplatte im Boden oder ein
    Draht. Aus der Naehe zu sehen (`sehen`), ein Schlag mit dem Brecheisen
    entschaerft sie (Spieler.schlagen fragt `entschaerfen`). Wer den
    Ausloeser spuert, hat einen Augenblick zum Wegspringen."""

    trefferbar = False
    schiebt = False

    def __init__(self, pos, ebene: int, fraktion: str, winkel: float = 0.0,
                 ausloeser: str = "platte") -> None:
        super().__init__(pos, ebene, fraktion, "sprengfalle")
        self.winkel = float(winkel)
        self.ausloeser = ausloeser
        self._bild = "sprengfalle_draht" if ausloeser == "draht" else "sprengfalle_platte"
        self.bild = None
        self.zuendet = -1.0          # >= 0: so lange noch bis zum Knall
        self.entschaerft = False

    def draht_enden(self):
        h = pygame.Vector2(A["sprengfalle"]["draht"] / 2, 0).rotate(self.winkel + 90)
        return self.pos - h, self.pos + h

    def _beruehrt(self, a) -> bool:
        s = A["sprengfalle"]
        if self.ausloeser == "draht":
            p0, p1 = self.draht_enden()
            weg = p1 - p0
            t = max(0.0, min(1.0, (a.pos - p0).dot(weg) / max(1.0, weg.length_squared())))
            return (p0 + weg * t).distance_to(a.pos) <= a.radius + 2.0
        return a.pos.distance_to(self.pos) <= s["radius"] + a.radius

    def entschaerfen(self) -> None:
        if self.zuendet < 0.0 and not self.entschaerft:
            self.entschaerft = True
            self.lebt = False
            wolke(self.welt, self.pos, 6, 80, 0.3, (200, 200, 190), self.ebene, 1, "funke")
            self.welt.klang("aufheben", 0.6, self.pos, self.ebene)

    def gesehen(self) -> bool:
        """Steht eine Figur nahe genug, um sie zu entdecken?"""
        s = A["sprengfalle"]
        return any(hasattr(a, "medkits") and a.lebt and a.pos.distance_to(self.pos) <= s["sehen"]
                   for a in self.welt.nahe(self.pos, s["sehen"], self.ebene))

    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        s = A["sprengfalle"]
        # Versteckt: zu sehen nur aus der Naehe (und im Testmodus in INFO).
        self.bild = self._bild if self.gesehen() or self.zuendet >= 0.0 else None
        if self.zuendet >= 0.0:
            self.zuendet -= dt
            if self.zuendet <= 0.0:
                self._knall()
            return
        for a in self.welt.nahe(self.pos, s["draht"], self.ebene):
            if a is self or not ist_gegner(a, self.fraktion) or getattr(a, "flug", 0.0) > 0:
                continue
            if self._beruehrt(a):
                self.zuendet = s["verzoegerung"]
                self.welt.klang("falle_klick", 0.9, self.pos, self.ebene)
                return

    def _knall(self) -> None:
        s = A["sprengfalle"]
        w = self.welt
        self.lebt = False
        r = s["spreng_radius"]
        for ziel in list(w.nahe(self.pos, r + 30, self.ebene)):
            if not ziel.lebt or ziel is self or getattr(ziel, "fraktion", "") == "geschoss":
                continue
            ab = ziel.pos - self.pos
            weit = ab.length()
            if weit > r + ziel.radius:
                continue
            anteil = (1.0 - 0.75 * min(1.0, weit / r)) * w.deckung_anteil(self.pos, ziel.pos,
                                                                           self.ebene)
            schub = ab.normalize() * 320 * anteil if weit > 0.01 else None
            schaden_an(ziel, s["schaden"] * anteil, schub, None, "spreng", self.pos)
        w.explosion(self.pos, self.ebene, r, "spreng")


class Kanister(Ausruestung):
    """Ein Benzinkanister: ein Treffer genuegt, dann ein Feuerball und eine
    brennende Flaeche, ohne Qualm darueber (Waffenpaket)."""

    bild = "kanister"

    def __init__(self, pos, ebene: int, fraktion: str, winkel: float = 0.0) -> None:
        super().__init__(pos, ebene, "neutral", "kanister")
        self.winkel = float(winkel)

    def sterben(self, von=None) -> None:
        super().sterben(von)
        k = A["kanister"]
        w = self.welt
        r = k["brand_radius"]
        for ziel in list(w.nahe(self.pos, r + 20, self.ebene)):
            if ziel is self or not ziel.lebt or getattr(ziel, "fraktion", "") == "geschoss":
                continue
            weit = ziel.pos.distance_to(self.pos)
            if weit <= r + ziel.radius:
                schaden_an(ziel, k["schaden"] * (1.0 - 0.6 * min(1.0, weit / r)), None, von,
                           "feuer", self.pos)
        w.feuer.append(Brandflaeche(self.pos, self.ebene, radius=r, von=von))
        w.explosion(self.pos, self.ebene, r, "feuer")
        w.lichtblitz(self.pos, self.ebene, r)


class Geschuetz(Ausruestung):
    """Die Selbstschussanlage: dreht sich zum naechsten Gegner, den sie
    sieht, und schiesst. Ein EMP legt sie still, Schaden zerstoert sie."""

    bild = "geschuetz_oben"
    technik = True

    def __init__(self, pos, ebene: int, fraktion: str, winkel: float = 0.0) -> None:
        super().__init__(pos, ebene, fraktion, "geschuetz")
        self.winkel = float(winkel)
        self.takt = 0.0
        self.magazin = A["geschuetz"]["magazin"]
        self.nachlade_rest = 0.0
        self.ziel = None
        self._suche_rest = 0.0
        self._daten = dict(schaden=A["geschuetz"]["schaden"], tempo=A["geschuetz"]["tempo"],
                           reichweite=A["geschuetz"]["reichweite"], geschosse=1,
                           kamera=0.3)

    def _suchen(self) -> None:
        g = A["geschuetz"]
        bestes, weite = None, g["reichweite"]
        for a in self.welt.nahe(self.pos, g["reichweite"], self.ebene):
            if a is self or not ist_gegner(a, self.fraktion):
                continue
            d = a.pos.distance_to(self.pos)
            if d < weite and self.welt.sicht_frei(self.pos, a.pos, self.ebene):
                bestes, weite = a, d
        self.ziel = bestes

    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        g = A["geschuetz"]
        self.takt = max(0.0, self.takt - dt)
        if self.nachlade_rest > 0.0:
            self.nachlade_rest -= dt
            if self.nachlade_rest <= 0.0:
                self.magazin = g["magazin"]
        if self.emp_rest > 0.0:
            return
        self._suche_rest -= dt
        if self._suche_rest <= 0.0:
            self._suche_rest = 0.2
            self._suchen()
        z = self.ziel
        if z is None or not z.lebt:
            return
        d = z.pos - self.pos
        soll = math.degrees(math.atan2(d.y, d.x))
        ab = (soll - self.winkel + 180) % 360 - 180
        schritt = g["dreh"] * dt
        self.winkel += max(-schritt, min(schritt, ab))
        if abs(ab) <= g["kegel"] and self.takt <= 0.0 and self.nachlade_rest <= 0.0:
            self.takt = g["takt"]
            self.magazin -= 1
            if self.magazin <= 0:
                self.nachlade_rest = g["nachladen"]
            muendung = self.pos + pygame.Vector2(12, 0).rotate(self.winkel)
            a = self.winkel + RND.uniform(-g["streuung"], g["streuung"])
            geschoss = Geschoss(muendung, a, self._daten, self.ebene, self, "geschuetz")
            self.welt.dazu(geschoss)
            self.welt.schussknall(muendung, self.winkel, self.ebene, "lmg", None)


# ── Aufklaerung ────────────────────────────────────────────────────────

class Drohne(Ausruestung):
    """Die Spaehdrohne: kreist ueber einem Punkt und markiert jeden
    Gegner, den sie sieht. Ein EMP holt sie herunter."""

    technik = True
    schiebt = False

    def __init__(self, pos, ebene: int, fraktion: str, winkel: float = 0.0) -> None:
        super().__init__(pos, ebene, fraktion, "drohne")
        self.mitte = pygame.Vector2(pos)
        self.phase = math.radians(winkel)
        self.bild = "teil_drohne_a"
        self._takt = 0.0
        # Sie startet, wo sie hingestellt wird, und fliegt in einer Spirale
        # hinaus auf ihren Kreis (seit 0.34.95: der Kreis ist weit, sie
        # sprang sonst gleich 230 px weg).
        self.kreis_jetzt = 0.0

    def emp_treffen(self, dauer: float) -> None:
        # Sie faellt herunter (Waffenpaket: "die Drohne sinkt zu Boden").
        self.schaden(self.leben + 1.0, None, None)

    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        d = A["drohne"]
        self.phase += d["tempo"] * dt
        self.kreis_jetzt = min(d["kreis"], self.kreis_jetzt + d["hinaus"] * dt)
        neu = self.mitte + pygame.Vector2(self.kreis_jetzt, 0).rotate(math.degrees(self.phase))
        self.winkel = math.degrees(self.phase) + 90
        self.pos.update(neu)
        self._takt += dt
        self.bild = "teil_drohne_a" if int(self._takt * 20) % 2 else "teil_drohne_b"
        if int((self._takt - dt) / 0.5) != int(self._takt / 0.5):
            self.welt.klang("drohne", 0.25, self.pos, self.ebene)
        # Nicht in jedem Schritt (seit 0.34.95): der Blick ist weit, die
        # Markierung haelt laenger als der Takt.
        self._such_rest = getattr(self, "_such_rest", 0.0) - dt
        if self._such_rest > 0.0:
            return
        self._such_rest = d["such_takt"]
        for a in self.welt.nahe(self.pos, d["sicht"], self.ebene):
            if (a is not self and ist_gegner(a, self.fraktion)
                    and a.pos.distance_to(self.pos) <= d["sicht"]):
                markieren(a, self.fraktion)

    def sterben(self, von=None) -> None:
        wolke(self.welt, self.pos, 10, 120, 0.4, (255, 220, 150), self.ebene, 1, "funke")
        super().sterben(von)


class Horchposten(Ausruestung):
    """Hoert durch Waende: wer sich in seinem Umkreis bewegt, wird alle
    `takt` Sekunden markiert. Wer stillsteht, bleibt unentdeckt."""

    bild = "teil_horcher_k"
    technik = True

    def __init__(self, pos, ebene: int, fraktion: str, winkel: float = 0.0) -> None:
        super().__init__(pos, ebene, fraktion, "horchposten")
        self.winkel = float(winkel)
        self._takt = 0.0
        self.welle = 0.0             # fuer den Ring, der vom Posten ausgeht

    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        h = A["horchposten"]
        self.welle = max(0.0, self.welle - dt)
        if self.emp_rest > 0.0:
            return
        self._takt -= dt
        if self._takt > 0.0:
            return
        self._takt = h["takt"]
        self.welle = 0.6
        self.welt.klang("horchposten", 0.3, self.pos, self.ebene)
        for a in self.welt.nahe(self.pos, h["weite"], self.ebene):
            if (a is not self and ist_gegner(a, self.fraktion)
                    and a.pos.distance_to(self.pos) <= h["weite"]
                    and a.tempo.length() > h["bewegt"]):
                markieren(a, self.fraktion)


# ── Hilfe ──────────────────────────────────────────────────────────────

class Sanitasche(Ausruestung):
    """Eine hingeworfene Sanitasche: wer verwundet daneben steht, wird
    ueber `dauer` Sekunden um `heilt` geheilt, bis die Ladungen alle sind."""

    bild = "sanitasche"
    trefferbar = False
    schiebt = False

    def __init__(self, pos, ebene: int, fraktion: str, winkel: float = 0.0) -> None:
        super().__init__(pos, ebene, fraktion, "sanitasche")
        self.winkel = float(winkel)
        self.ladungen = A["sanitasche"]["ladungen"]
        self._heilt: dict = {}       # id(Figur) -> [Figur, Rest]

    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        s = A["sanitasche"]
        for a in self.welt.nahe(self.pos, s["radius"] + 10, self.ebene):
            if (id(a) in self._heilt or self.ladungen <= 0 or not hasattr(a, "medkits")
                    or not a.lebt or a.leben >= a.max_leben
                    or a.pos.distance_to(self.pos) > s["radius"]):
                continue
            self.ladungen -= 1
            self._heilt[id(a)] = [a, s["dauer"]]
            self.welt.klang("medkit", 0.6, self.pos, self.ebene)
        for schluessel, (a, rest) in list(self._heilt.items()):
            if not a.lebt or rest <= 0.0:
                del self._heilt[schluessel]
                continue
            a.leben = min(a.max_leben, a.leben + s["heilt"] / s["dauer"] * dt)
            self._heilt[schluessel][1] = rest - dt
        if self.ladungen <= 0 and not self._heilt:
            self.lebt = False


class Munitionskiste(Ausruestung):
    """Eine hingestellte Munitionskiste: wer daran vorbeigeht, bekommt
    seine Waffen voll - jeder hoechstens alle `pause` Sekunden, bis die
    Ladungen alle sind."""

    bild = "munikiste"

    def __init__(self, pos, ebene: int, fraktion: str, winkel: float = 0.0) -> None:
        super().__init__(pos, ebene, "neutral", "munitionskiste")
        self.winkel = float(winkel)
        self.ladungen = A["munitionskiste"]["ladungen"]
        self._zuletzt: dict = {}
        self.max_leben = self.leben = 200.0

    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        m = A["munitionskiste"]
        jetzt = self.welt.zeit
        for a in self.welt.nahe(self.pos, m["radius"] + 10, self.ebene):
            if (not hasattr(a, "magazin") or not a.lebt or a is self
                    or a.pos.distance_to(self.pos) > m["radius"]
                    or jetzt - self._zuletzt.get(id(a), -1e9) < m["pause"]):
                continue
            voll = False
            for name in getattr(a, "waffen", ()):
                d = K.WAFFEN.get(name, {})
                if d.get("magazin") and a.magazin.get(name, 0) < d["magazin"]:
                    a.magazin[name] = d["magazin"]
                    voll = True
            if voll:
                self._zuletzt[id(a)] = jetzt
                self.ladungen -= 1
                self.welt.klang("aufheben", 0.7, self.pos, self.ebene)
                self.welt.aufschrift(self.pos, self.ebene, "MUNITION")
        if self.ladungen <= 0:
            self.lebt = False


# Was der Spawner setzen kann: Name -> (Klasse, Gruppe).
ARTEN = {
    "SANDSACKWAND": (None, "BAUEN"),
    "STACHELDRAHT": (Stacheldraht, "BAUEN"),
    "SPRENGFALLE (PLATTE)": (Sprengfalle, "FALLEN"),
    "SPRENGFALLE (DRAHT)": (Sprengfalle, "FALLEN"),
    "SELBSTSCHUSSANLAGE": (Geschuetz, "FALLEN"),
    "BENZINKANISTER": (Kanister, "FALLEN"),
    "SPÄHDROHNE": (Drohne, "AUFKLÄRUNG"),
    "HORCHPOSTEN": (Horchposten, "AUFKLÄRUNG"),
    "SANITASCHE": (Sanitasche, "HILFE"),
    "MUNITIONSKISTE (STEHT)": (Munitionskiste, "HILFE"),
}


def bauen(name: str, pos, ebene: int, fraktion: str, winkel: float) -> list:
    """Die Dinge fuer einen Spawner-Eintrag."""
    if name == "SANDSACKWAND":
        return sandsackwand(pos, ebene, winkel)
    klasse = ARTEN[name][0]
    if klasse is Sprengfalle:
        return [Sprengfalle(pos, ebene, fraktion, winkel,
                            "draht" if "DRAHT" in name else "platte")]
    return [klasse(pos, ebene, fraktion, winkel)]
