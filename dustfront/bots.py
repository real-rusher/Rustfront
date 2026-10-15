"""
DUSTFRONT - Bots (seit 0.34.18)
===============================

Gemeldet: "bau optionale schwache bots ein, die man bei allen pvp runden
aktivieren kann die dann gleichmaessig die teams auffuellen und objectives
machen und versuchen gegner zu eliminieren. Stell sicher das deren ai gut
ist, aber das sie keinen aimbot bzw unfaire Vorteile haben. Wenn ihnen alle
Munition ausgeht sollen sie zu melee switchen, und ihr loadout soll random
sein. C4 sollen sie nicht haben koennen. Sie sollen keine autos fahren
koennen."

**Fair, weil es dieselbe Eingabe ist.** Ein Bot ist ein Kaempfer wie jeder
andere. Er bekommt keine Sonderrechte am Spielkern vorbei: sein Hirn
(`BotHirn`) baut je Schritt genau die Eingabemeldung, die ein Gast schicken
wuerde - Laufrichtung, Mauszeiger, Feuertaste, Tastendruecke -, und der
Gastgeber legt sie mit `Gefecht._anwenden` an, wie die jedes Gastes.
Geschossen, gestreut, nachgeladen und getroffen wird also nach denselben
Regeln.

**Was er weiss.** Nur, was ein Mensch an seiner Stelle wissen koennte:

* Er **sieht** Gegner auf seiner Ebene in Sichtweite (`sicht`, etwa eine
  halbe Bildbreite), nicht durch Waende (`Welt.sicht_frei`, dieselbe
  Rechnung wie fuer die Blendgranate) und nicht durch dichten Rauch.
* Er **hoert** Schuesse in der Naehe und sieht dort nach - ungefaehr, nicht
  genau.
* Wird er getroffen, dreht er sich in die Richtung, aus der es kam.
* Wo die Kreise liegen und wo die eigenen Leute sind, weiss jeder Spieler
  (Minikarte) - also auch er. Wo die Gegner sind, weiss er nur, wenn die
  Regel "Gegner auf der Minikarte" an ist - wie alle anderen auch.

**Wie er zielt.** Wie ein mittelmaessiger Spieler mit Maus:

* Bis zum ersten Schuss auf ein neues Ziel vergeht eine Reaktionszeit
  (`reaktion`), laenger, wenn es von hinten kommt.
* Das Fadenkreuz schwenkt hoechstens `dreh` Grad je Sekunde - kein
  Schnappen auf den Kopf.
* Er zielt auf die Stelle, an der der Gegner **jetzt** steht, mit einem
  Fehler, der beim ersten Sehen gross ist und erst mit der Zeit kleiner
  wird. Vorgehalten wird nicht: wer quer laeuft, wird oft verfehlt.
* Er schiesst in Feuerstoessen mit Pausen und bleibt dabei oft stehen.

**Was er tut.** Er kaempft, wenn er jemanden sieht, haelt dabei einen zur
Waffe passenden Abstand und weicht seitlich aus. Sonst arbeitet er an der
Aufgabe der Spielart: in HUEGEL geht er in den Kreis und bleibt dort, in
VERSUS hilft er gefallenen Mitspielern auf, sonst sucht er Gegner - dort,
wo er zuletzt einen sah oder hoerte, oder auf der Karte. Er nimmt Treppen
und Aufzuege (dasselbe Wegenetz wie die Zombies), legt ein Medkit an, wenn
es ruhig ist, wirft ab und zu, was er dabeihat, und laedt nach. Ist alle
Munition weg (nur mit knapper Munition moeglich), geht er mit dem
Brecheisen auf den naechsten los.

**Was er nicht darf.** Kein C4 (auch nicht, wenn der Gastgeber eines fuer
alle vorgibt), keinen Raketenwerfer aufheben, nicht in einen Buggy steigen.
Sein Loadout wird zu jedem Leben neu gewuerfelt: zwei Waffen und eine
Wurfwaffe - ausser bei "eines fuer alle", dann traegt er das wie jeder.

**Wer rechnet.** Nur der Gastgeber. Beim Gast ist ein Bot ein Spieler wie
jeder andere in der Weltmeldung (mit `bo` gekennzeichnet). Gebucht wird
fuer einen Bot nichts, und in die Bestenliste kommt er nicht.
"""

from __future__ import annotations

import math
import random

import pygame

from . import config as K
from . import konto as konto_modul


def _winkel_zu(von, nach) -> float:
    d = nach - von
    return math.degrees(math.atan2(d.y, d.x))


def _winkel_diff(a: float, b: float) -> float:
    """b - a, auf -180 bis 180."""
    return (b - a + 180.0) % 360.0 - 180.0


def bot_loadout(rnd, fest=None) -> dict:
    """Ein Loadout fuer einen Bot: zwei Waffen und eine Wurfwaffe, zufaellig
    - oder das vorgegebene ("eines fuer alle"). C4 nie."""
    lo = K.LOADOUT
    wuerfe = [w for w in lo["auswahl_wuerfe"] if w != "c4"]
    if fest:
        raus = konto_modul.loadout_saeubern(fest) or {}
        raus = dict(raus)
        raus["wuerfe"] = [w for w in raus.get("wuerfe", []) if w != "c4"]
        if not raus["wuerfe"]:
            raus["wuerfe"] = [rnd.choice(wuerfe)]
        return raus
    waffen = rnd.sample(list(lo["auswahl_waffen"]), lo["waffen"])
    return {"name": "BOT", "waffen": waffen,
            "wuerfe": [rnd.choice(wuerfe) for _ in range(lo["wuerfe"])]}


class BotHirn:
    """Was ein Bot denkt. Liefert je Schritt eine Eingabemeldung."""

    def __init__(self, gefecht, k, rnd) -> None:
        self.g = gefecht
        self.k = k
        self.rnd = rnd
        self.neues_leben()

    def neues_leben(self) -> None:
        k = self.k
        self.ziel = None              # wen er bekaempft
        self.gesehen = {}             # Wesen -> (Ort, Ebene, Zeit)
        self.verdacht = None          # (Ort, Ebene, bis wann)
        self.reaktion_rest = 0.0
        self.fehler = pygame.Vector2(0, 0)
        self.fehler_zeit = 0.0        # so lange verfolgt er das Ziel schon
        self.blick = float(k.winkel)  # wohin sein Fadenkreuz zeigt
        self.stoss_rest = 0.0         # Feuerstoss laeuft noch
        self.pause_rest = 0.0         # Feuerpause laeuft noch
        self.still = False            # bleibt er in diesem Stoss stehen?
        self.seite = self.rnd.choice((-1.0, 1.0))
        self.seite_rest = 0.0
        self.denk_rest = self.rnd.uniform(0.0, K.BOTS["takt"])
        self.wurf_rest = self.rnd.uniform(*K.BOTS["wurf_pause"]) * 0.5
        self.wurf_phase = 0.0         # > 0: zielt gerade zum Wurf
        self.wurf_platz = -1
        self.dash_rest = 0.0
        self.waffen_rest = 0.0        # Sperre zwischen zwei Waffenwechseln
        self.wegpunkt = None          # Zwischenziel auf dem Weg
        self.weg_ziel = None          # (Ort, Ebene) des Weges
        self.weg_rest = 0.0
        self.streifzug = None         # wohin er geht, wenn nichts los ist
        self.streif_rest = 0.0
        self.stockt_ort = pygame.Vector2(k.pos)
        self.stockt_rest = K.BOTS["stockt_nach"]
        self.ausweich_rest = 0.0
        self.ausweich = pygame.Vector2(0, 0)
        self.ruhe = 0.0               # so lange niemanden gesehen
        self.leben_vorher = k.leben
        self.ruf_rest = 0.0
        self.geblendet = 0.0          # so lange sieht er nichts (Blendgranate)

    def blenden(self, dauer: float) -> None:
        """Eine Blendgranate hat ihn erwischt: er sieht nichts, verliert
        sein Ziel und muss danach neu reagieren."""
        self.geblendet = max(self.geblendet, dauer)
        self.ziel = None
        self.stoss_rest = 0.0

    # ══════════════════════════════════════════════════════════════
    # Der Schritt
    # ══════════════════════════════════════════════════════════════
    def eingabe(self, dt: float) -> dict:
        k = self.k
        g = self.g
        ein = {"t": "ein", "will": [0.0, 0.0],
               "ziel": [round(k.ziel.x, 1), round(k.ziel.y, 1)],
               "feuert": False, "zielt": False, "nutzen": False,
               "ziehen": False, "hb": False, "waffe": -1, "knoepfe": [],
               "admin": ""}
        if not k.lebt:
            return ein
        if k.am_boden:
            # Am Boden bleibt nur das Rufen - wie bei einem Menschen.
            self.ruf_rest -= dt
            if self.ruf_rest <= 0.0:
                self.ruf_rest = 5.0
                ein["knoepfe"].append("nutzen")
            return ein
        self._zeiten(dt)
        self.denk_rest -= dt
        if self.denk_rest <= 0.0:
            self.denk_rest = K.BOTS["takt"]
            self._wahrnehmen()

        will = pygame.Vector2(0, 0)
        ziel_punkt = None            # wohin das Fadenkreuz will
        feuern = False
        zielt = False

        # Getroffen worden: dorthin schauen, woher es kam.
        if k.leben < self.leben_vorher - 0.5:
            self._getroffen()
        self.leben_vorher = k.leben

        # Medkit, wenn es ruhig ist.
        b = K.BOTS
        if (k.leben < b["heilen_unter"] and k.medkits > 0 and k.heilt_rest <= 0
                and self.ruhe >= b["heilen_ruhe"]):
            ein["knoepfe"].append("heilen")

        helfen = self._wem_helfen()
        if self.ziel is not None and self.ziel_ok(self.ziel):
            will, ziel_punkt, feuern, zielt = self._kaempfen(dt, ein)
        elif helfen is not None:
            will, ziel_punkt = self._helfen(helfen, ein)
        else:
            will, ziel_punkt = self._unterwegs(dt, ein)

        will = self._sicher(will)
        will = self._nicht_stecken(dt, will)

        # Fadenkreuz: schwenkt, springt nicht.
        if ziel_punkt is None:
            ziel_punkt = k.pos + (will * 120 if will.length_squared() > 0.01
                                  else pygame.Vector2(1, 0).rotate(self.blick) * 120)
        soll = _winkel_zu(k.pos, ziel_punkt)
        ab = _winkel_diff(self.blick, soll)
        schritt = K.BOTS["dreh"] * dt
        self.blick += max(-schritt, min(schritt, ab))
        weit = max(40.0, k.pos.distance_to(ziel_punkt))
        maus = k.pos + pygame.Vector2(1, 0).rotate(self.blick) * weit
        ein["ziel"] = [round(maus.x, 1), round(maus.y, 1)]
        ein["will"] = [round(will.x, 2), round(will.y, 2)]
        ein["feuert"] = bool(feuern)
        ein["zielt"] = bool(zielt)
        return ein

    def _zeiten(self, dt: float) -> None:
        for name in ("reaktion_rest", "stoss_rest", "pause_rest", "seite_rest",
                     "wurf_rest", "dash_rest", "waffen_rest", "weg_rest",
                     "streif_rest", "ausweich_rest", "geblendet"):
            setattr(self, name, max(0.0, getattr(self, name) - dt))
        if self.ziel is None:
            self.ruhe += dt
        else:
            self.ruhe = 0.0
            self.fehler_zeit += dt

    # ══════════════════════════════════════════════════════════════
    # Wahrnehmen
    # ══════════════════════════════════════════════════════════════
    def ist_feind(self, w) -> bool:
        k = self.k
        if w is k or not getattr(w, "lebt", False):
            return False
        if getattr(w, "fraktion", "") == k.fraktion:
            return False
        if getattr(w, "raus", False) or getattr(w, "ist_puppe", False):
            return False
        return hasattr(w, "nummer") or getattr(w, "fraktion", "") == "feind"

    def ziel_ok(self, w) -> bool:
        return self.ist_feind(w) and w.ebene == self.k.ebene

    def _kandidaten(self) -> list:
        g = self.g
        raus = [w for w in g.kaempfer.values() if self.ist_feind(w)]
        if g.mit_gegnern:
            from .mehrspieler import KampfGegner
            raus += [w for w in g.welt.wesen
                     if isinstance(w, KampfGegner) and self.ist_feind(w)]
        return raus

    def sieht(self, w) -> bool:
        """Sieht er `w`? Ebene, Weite, Wand, Rauch - wie ein Mensch."""
        k = self.k
        if self.geblendet > 0.0:
            return False
        if w.ebene != k.ebene or getattr(w, "flug", 0.0) > 0:
            return False
        if k.pos.distance_to(w.pos) > K.BOTS["sicht"]:
            return False
        welt = self.g.welt
        if not welt.sicht_frei(k.pos, w.pos, k.ebene):
            return False
        mitte = (k.pos + w.pos) / 2
        for r in welt.rauch:
            if r.ebene == k.ebene and (r.deckt(w.pos, k.ebene) or r.deckt(mitte, k.ebene)):
                return False
        return True

    def _wahrnehmen(self) -> None:
        k = self.k
        jetzt = self.g.welt.zeit
        sichtbar = []
        for w in self._kandidaten():
            if self.sieht(w):
                sichtbar.append(w)
                self.gesehen[w] = (pygame.Vector2(w.pos), w.ebene, jetzt)
        # Vergessen, was zu lange her ist.
        for w in list(self.gesehen):
            if jetzt - self.gesehen[w][2] > K.BOTS["gedaechtnis"] or not w.lebt:
                del self.gesehen[w]
        if self.ziel is not None and self.ziel in sichtbar:
            return                            # er bleibt dran
        alt = self.ziel
        self.ziel = None
        if sichtbar:
            def wert(w):
                d = k.pos.distance_to(w.pos)
                if getattr(w, "am_boden", False):
                    d += 260.0                # erst, wer noch steht
                return d
            neu = min(sichtbar, key=wert)
            self._neues_ziel(neu, neu is alt)
            return
        # Niemand zu sehen: wo er zuletzt jemanden sah, sonst was er hoerte.
        if alt is not None and alt in self.gesehen:
            ort, ebene, _t = self.gesehen[alt]
            self.verdacht = (ort, ebene, jetzt + K.BOTS["gedaechtnis"])
        geraeusch = self._hoeren()
        if geraeusch is not None and (self.verdacht is None or self.verdacht[2] < jetzt):
            self.verdacht = geraeusch

    def _neues_ziel(self, w, gleiches: bool) -> None:
        b = K.BOTS
        self.ziel = w
        if gleiches:
            return                            # kurz verdeckt, wieder da
        self.reaktion_rest = self.rnd.uniform(*b["reaktion"])
        if abs(_winkel_diff(self.blick, _winkel_zu(self.k.pos, w.pos))) > 100:
            self.reaktion_rest += b["reaktion_hinten"]
        self.fehler.from_polar((1.0, self.rnd.uniform(0, 360)))
        self.fehler_zeit = 0.0
        self.verdacht = None
        self.pause_rest = self.reaktion_rest

    def _hoeren(self):
        """Der naechste Schuss eines Gegners in Hoerweite, als ungefaehrer
        Ort - oder None."""
        k = self.k
        jetzt = self.g.welt.zeit
        bestes, beste = None, K.BOTS["gehoer"]
        for (ort, ebene, zeit, fraktion) in getattr(self.g, "_bot_geraeusche", ()):
            if jetzt - zeit > 1.5 or fraktion == k.fraktion:
                continue
            d = k.pos.distance_to(ort)
            if d < beste:
                bestes, beste = (ort, ebene), d
        if bestes is None:
            return None
        ungefaehr = pygame.Vector2(bestes[0]) + pygame.Vector2(
            self.rnd.uniform(-60, 60), self.rnd.uniform(-60, 60))
        return (ungefaehr, bestes[1], jetzt + 3.0)

    def _getroffen(self) -> None:
        """Woher kam es? Ungefaehr dorthin schauen und nachsehen."""
        von = getattr(self.k, "zuletzt_von", None)
        von = getattr(von, "von", von)       # Granate, Feuer -> Werfer
        if von is None or not hasattr(von, "pos") or von is self.k:
            return
        if self.ziel is None:
            ort = pygame.Vector2(von.pos) + pygame.Vector2(
                self.rnd.uniform(-50, 50), self.rnd.uniform(-50, 50))
            # Kein Herumreissen des Fadenkreuzes: er schaut dorthin, mit
            # derselben Drehgeschwindigkeit wie sonst auch.
            self.verdacht = (ort, getattr(von, "ebene", self.k.ebene),
                             self.g.welt.zeit + 3.0)
            self.denk_rest = 0.0

    # ══════════════════════════════════════════════════════════════
    # Kaempfen
    # ══════════════════════════════════════════════════════════════
    def _waffen_mit_munition(self) -> list:
        k = self.k
        raus = []
        for i, name in enumerate(k.waffen):
            d = K.WAFFEN[name]
            if d.get("art") != "schuss":
                continue
            if k.magazin.get(name, 0) > 0 or not k.knapp or k.vorrat.get(name, 0) > 0:
                raus.append((i, name))
        return raus

    def _beste_waffe(self, abstand: float):
        """Die Waffe, die zu diesem Abstand passt und Munition hat."""
        liste = self._waffen_mit_munition()
        if not liste:
            return None
        wunsch = K.BOTS["wunschabstand"]
        return min(liste, key=lambda p: abs(wunsch.get(p[1], 220.0) - abstand)
                   + (0 if self.k.magazin.get(p[1], 0) > 0 else 60))

    def _kaempfen(self, dt: float, ein: dict):
        k = self.k
        b = K.BOTS
        z = self.ziel
        abstand = k.pos.distance_to(z.pos)
        sichtbar = z in self.gesehen and self.gesehen[z][2] >= self.g.welt.zeit - 0.15

        # Zielfehler: gross beim ersten Sehen, wird kleiner, wackelt etwas.
        massstab = max(0.5, min(2.0, abstand / 250.0))
        fehler = max(b["fehler_min"], b["fehler_start"]
                     * math.exp(-self.fehler_zeit / b["fehler_abbau"]))
        self.fehler.rotate_ip(self.rnd.uniform(-40, 40) * dt * 3)
        ziel_punkt = z.pos + self.fehler * (fehler * massstab)

        # Wurf: ab und zu, wenn es passt.
        if self.wurf_phase > 0.0:
            return self._werfen(dt, ein, z)
        waffe = self._beste_waffe(abstand)
        if waffe is None:
            return self._nahkampf(ein, z, abstand)
        if self._wurf_moeglich(abstand) and sichtbar:
            self.wurf_phase = 0.45
            self.wurf_rest = self.rnd.uniform(*b["wurf_pause"])
            return self._werfen(dt, ein, z)
        nr, name = waffe
        if nr != k.waffe and self.waffen_rest <= 0.0 and k.nachlade_rest <= 0:
            ein["waffe"] = nr
            self.waffen_rest = 1.2
        if k.magazin.get(k.waffe_name, 0) <= 0 and k.nachlade_rest <= 0:
            ein["knoepfe"].append("nachladen")

        # Bewegen: Abstand halten, seitlich ausweichen.
        will = self._kampfbewegung(abstand, z)

        # Schiessen: nach der Reaktion, wenn das Fadenkreuz in der Naehe
        # ist, in Stoessen.
        feuern = False
        zielt = False
        name = k.waffe_name
        reich = b["reichweite"].get(name, 300.0)
        winkel_fehler = abs(_winkel_diff(self.blick, _winkel_zu(k.pos, ziel_punkt)))
        erlaubt = math.degrees(math.atan2(getattr(z, "radius", 9.0) + 8.0,
                                          max(1.0, abstand))) + 3.0
        bereit = (sichtbar and self.reaktion_rest <= 0.0 and abstand <= reich
                  and k.nachlade_rest <= 0)
        if name == "scharf" and sichtbar and abstand > 90:
            zielt = True
            bereit = bereit and k.fokus >= 0.8
        if bereit and winkel_fehler <= erlaubt:
            if self.stoss_rest <= 0.0 and self.pause_rest <= 0.0:
                self.stoss_rest = self.rnd.uniform(*b["feuerstoss"])
                self.still = self.rnd.random() < b["still_beim_schiessen"]
            if self.stoss_rest > 0.0:
                feuern = True
                if self.stoss_rest <= dt:
                    self.pause_rest = self.rnd.uniform(*b["feuerpause"])
        if feuern and self.still:
            will = pygame.Vector2(0, 0)
        return will, ziel_punkt, feuern, zielt

    def _kampfbewegung(self, abstand: float, z):
        k = self.k
        g = self.g
        if self.seite_rest <= 0.0:
            self.seite_rest = self.rnd.uniform(0.7, 1.6)
            if self.rnd.random() < 0.55:
                self.seite = -self.seite
        wunsch = K.BOTS["wunschabstand"].get(k.waffe_name, 220.0)
        hin = z.pos - k.pos
        if hin.length_squared() < 1.0:
            hin = pygame.Vector2(1, 0)
        hin = hin.normalize()
        quer = pygame.Vector2(-hin.y, hin.x) * self.seite
        if abstand > wunsch + 40:
            # Heran - um Waende herum, wenn noetig.
            weg = self._weg_richtung(z.pos, z.ebene)
            will = weg * 0.9 + quer * 0.25
        elif abstand < wunsch - 40:
            will = -hin * 0.8 + quer * 0.45
        else:
            will = quer * 0.85 + hin * 0.1
        # HUEGEL: im Kreis bleiben, auch im Kampf.
        if g.regeln.get("zone") and k.ebene == g.zone_ebene:
            zum_kreis = g.zone_mitte - k.pos
            if zum_kreis.length() > K.ZONE["radius"] * 0.8:
                will = will * 0.4 + zum_kreis.normalize() * 0.8
        if will.length_squared() > 1.0:
            will = will.normalize()
        return will

    def _nahkampf(self, ein: dict, z, abstand: float):
        """Keine Munition mehr: mit dem Brecheisen hin und zuschlagen."""
        k = self.k
        b = K.BOTS
        will = self._weg_richtung(z.pos, z.ebene)
        if abstand <= b["nahkampf_ab"] + getattr(z, "radius", 9.0):
            if self.reaktion_rest <= 0.0:
                ein["knoepfe"].append("nahkampf")
            will = will * 0.3
        elif 70.0 < abstand < 160.0 and self.dash_rest <= 0.0 and self.rnd.random() < 0.02:
            ein["knoepfe"].append("dash")
            self.dash_rest = b["dash_pause"]
        return will, pygame.Vector2(z.pos), False, False

    def _wurf_platz(self) -> int:
        k = self.k
        for i, name in enumerate(k.waffen):
            d = K.WAFFEN[name]
            if d.get("art") != "wurf" or name == "c4":
                continue
            if k.magazin.get(name, 0) > 0 or k.vorrat.get(name, 0) > 0:
                return i
        return -1

    def _wurf_moeglich(self, abstand: float) -> bool:
        if self.wurf_rest > 0.0 or self.reaktion_rest > 0.0:
            return False
        nah, weit = K.BOTS["wurf_weite"]
        if not (nah <= abstand <= weit):
            return False
        self.wurf_platz = self._wurf_platz()
        if self.wurf_platz < 0:
            return False
        name = self.k.waffen[self.wurf_platz]
        if name == "rauch":
            # Rauch nur, wenn es eng wird: als Deckung zum Rueckzug.
            return self.k.leben < 45.0
        return self.rnd.random() < 0.5

    def _werfen(self, dt: float, ein: dict, z):
        """Wurfwaffe nehmen, kurz zielen, werfen, zurueck zur Waffe."""
        k = self.k
        self.wurf_phase -= dt
        nr = self.wurf_platz
        if nr < 0 or nr >= len(k.waffen):
            self.wurf_phase = 0.0
            return pygame.Vector2(0, 0), pygame.Vector2(z.pos), False, False
        if k.waffe != nr:
            ein["waffe"] = nr
        ziel = pygame.Vector2(z.pos)
        if k.waffen[nr] == "rauch":
            ziel = k.pos + (z.pos - k.pos) * 0.4
        werfen = self.wurf_phase <= 0.0 and k.waffe == nr
        if werfen:
            self.wurf_phase = 0.0
            self.waffen_rest = 0.0
        return pygame.Vector2(0, 0), ziel, werfen, False

    # ══════════════════════════════════════════════════════════════
    # Helfen (VERSUS)
    # ══════════════════════════════════════════════════════════════
    def _wem_helfen(self):
        g = self.g
        k = self.k
        if not g.regeln.get("revive") or not g.mit_teams:
            return None
        bester, weite = None, 700.0
        for x in g.kaempfer.values():
            if x is k or not x.lebt or not x.am_boden or x.team != k.team:
                continue
            d = k.pos.distance_to(x.pos) + (300.0 if x.ebene != k.ebene else 0.0)
            if d < weite:
                bester, weite = x, d
        return bester

    def _helfen(self, x, ein: dict):
        k = self.k
        if x.ebene == k.ebene and k.pos.distance_to(x.pos) <= K.REVIVE["reichweite"] - 4:
            ein["nutzen"] = True
            return pygame.Vector2(0, 0), pygame.Vector2(x.pos)
        return self._weg_richtung(x.pos, x.ebene), None

    # ══════════════════════════════════════════════════════════════
    # Unterwegs: Aufgabe, Verdacht, Streifzug
    # ══════════════════════════════════════════════════════════════
    def _unterwegs(self, dt: float, ein: dict):
        k = self.k
        g = self.g
        self.stoss_rest = 0.0
        # Nachladen, wenn es ruhig ist und das Magazin nicht voll.
        d = k.waffe_daten
        if (d.get("art") == "schuss" and k.nachlade_rest <= 0
                and k.magazin.get(k.waffe_name, 0) < d.get("magazin", 0) * 0.6):
            ein["knoepfe"].append("nachladen")
        jetzt = g.welt.zeit
        ziel = None
        # HUEGEL: der Kreis ist die Aufgabe.
        if g.regeln.get("zone"):
            mitte, ebene = g.zone_mitte, g.zone_ebene
            if k.ebene != ebene or k.pos.distance_to(mitte) > K.ZONE["radius"] * 0.7:
                ziel = (pygame.Vector2(mitte), ebene)
            else:
                if self.streif_rest <= 0.0 or self.streifzug is None:
                    p = pygame.Vector2(mitte) + pygame.Vector2(
                        self.rnd.uniform(-1, 1), self.rnd.uniform(-1, 1)) \
                        * K.ZONE["radius"] * 0.5
                    self.streifzug = (p, ebene)
                    self.streif_rest = self.rnd.uniform(1.5, 3.0)
                ziel = self.streifzug
        if ziel is None:
            beute = self._beute_ziel()
            if beute is not None:
                ziel = beute
        if ziel is None and self.verdacht is not None and self.verdacht[2] >= jetzt:
            ort, ebene, _bis = self.verdacht
            if k.ebene == ebene and k.pos.distance_to(ort) < 30:
                self.verdacht = None
            else:
                ziel = (ort, ebene)
        if ziel is None:
            if (self.streifzug is None or self.streif_rest <= 0.0
                    or (k.ebene == self.streifzug[1]
                        and k.pos.distance_to(self.streifzug[0]) < 40)):
                self.streifzug = self._streifziel()
                self.streif_rest = self.rnd.uniform(12.0, 25.0)
            ziel = self.streifzug
        will = self._weg_richtung(ziel[0], ziel[1], ein)
        blick = None
        if self.verdacht is not None and self.verdacht[2] >= jetzt:
            blick = pygame.Vector2(self.verdacht[0])
        return will, blick

    def _beute_ziel(self):
        """Ein Medkit oder eine Munitionskiste in Sicht, wenn er sie braucht."""
        k = self.k
        from .mehrspieler import KampfBeute
        braucht = set()
        if k.medkits <= 0 and k.leben < 70:
            braucht.add("medkit")
        if k.knapp and len(self._waffen_mit_munition()) < 2:
            braucht.add("munition")
        if not braucht:
            return None
        bestes, beste = None, K.BOTS["sicht"]
        for w in self.g.welt.wesen:
            if (isinstance(w, KampfBeute) and w.lebt and w.art in braucht
                    and w.ebene == k.ebene):
                d = k.pos.distance_to(w.pos)
                if d < beste and self.g.welt.sicht_frei(k.pos, w.pos, k.ebene):
                    bestes, beste = (pygame.Vector2(w.pos), w.ebene), d
        return bestes

    def _streifziel(self):
        """Irgendwohin, wo Gegner sein koennten: die Kreise und Spawnstellen
        der Karte (kennt jeder), die Seite der anderen Mannschaft (auch),
        oder einfach eine freie Stelle."""
        g = self.g
        k = self.k
        wahl = []
        for ebene, punkt, _name in getattr(g, "kreise", ()):
            wahl.append((pygame.Vector2(punkt), ebene))
        if g.mit_teams and getattr(g, "einstiegszonen", None):
            for i, p in enumerate(g.einstiegszonen):
                if i != k.team:
                    wahl += [(pygame.Vector2(p), 0)] * 2
        # Was die Minikarte jedem zeigt, darf er auch wissen.
        if g.regelwerk.get("gegner_karte"):
            feinde = [w for w in g.kaempfer.values() if self.ist_feind(w)]
            if feinde:
                w = self.rnd.choice(feinde)
                wahl += [(pygame.Vector2(w.pos), w.ebene)] * 3
        if not wahl or self.rnd.random() < 0.35:
            from .world import freier_punkt
            ebene = 0 if self.rnd.random() < 0.75 else self.rnd.randrange(len(g.welt.ebenen))
            wahl.append((freier_punkt(g.welt, ebene, self.rnd), ebene))
            return wahl[-1]
        return self.rnd.choice(wahl)

    # ══════════════════════════════════════════════════════════════
    # Wege
    # ══════════════════════════════════════════════════════════════
    def _weg_richtung(self, ort, ebene: int, ein: dict | None = None):
        """Richtung zum naechsten Wegpunkt nach `ort` auf `ebene` - um Waende
        herum und ueber Treppen. Gerechnet wird nur ab und zu (`weg_rest`)."""
        k = self.k
        welt = self.g.welt
        ort = pygame.Vector2(ort)
        if (self.wegpunkt is None or self.weg_rest <= 0.0 or self.weg_ziel is None
                or self.weg_ziel[1] != ebene or self.weg_ziel[0].distance_to(ort) > 24
                or k.pos.distance_to(self.wegpunkt) < 10):
            self.wegpunkt = self._wegpunkt(ort, ebene, ein)
            self.weg_ziel = (ort, ebene)
            self.weg_rest = 0.35
        elif ein is not None:
            self._treppe_nehmen(ebene, ein)
        d = self.wegpunkt - k.pos
        if d.length_squared() < 4.0:
            return pygame.Vector2(0, 0)
        return d.normalize()

    def _wegpunkt(self, ort, ebene: int, ein):
        k = self.k
        welt = self.g.welt
        wege = welt.wege
        if k.ebene != ebene or wege.braucht_weg(k.ebene, k.pos, ebene, ort):
            nr = wege.naechste_treppe(k.ebene, k.pos, ebene, ort)
            if nr is None:
                return pygame.Vector2(ort)
            punkt, _rest = wege.schritt_zu(nr, k.pos)
            if ein is not None:
                self._treppe_nehmen(ebene, ein, nr)
            return punkt if punkt is not None else pygame.Vector2(ort)
        if wege.gerade_frei(k.ebene, k.pos, ort, k.radius + 2):
            return pygame.Vector2(ort)
        _schl, feld = wege.feld_zu(k.ebene, ort)
        punkt, _rest = wege.schritt_ueber(k.ebene, feld, k.pos)
        return punkt if punkt is not None else pygame.Vector2(ort)

    def _treppe_nehmen(self, ebene: int, ein: dict, nr: int | None = None) -> None:
        """Steht er auf der Treppe (dem Aufzug), die er nehmen will: E."""
        k = self.k
        if k.ebene == ebene or k.treppe_rest > 0:
            return
        welt = self.g.welt
        wohin = welt.treppe_unter(k)
        if wohin is None:
            return
        if abs(wohin - ebene) < abs(k.ebene - ebene):
            if "nutzen" not in ein["knoepfe"]:
                ein["knoepfe"].append("nutzen")

    def _sicher(self, will):
        """Nicht in ein Loch und nicht gegen die Wand: die Richtung so weit
        drehen, bis vor ihm Boden ist."""
        if will.length_squared() < 0.01:
            return will
        k = self.k
        welt = self.g.welt
        e = welt.ebene(k.ebene)
        for dreh in (0, 30, -30, 60, -60, 100, -100, 150, -150):
            r = will.rotate(dreh)
            p = k.pos + r.normalize() * 16.0
            tx, ty = int(p.x // K.TILE), int(p.y // K.TILE)
            if k.ebene > 0 and e.loch(tx, ty):
                continue
            if welt.frei(p, k.radius, k.ebene, True):
                return r
        return pygame.Vector2(0, 0)

    def _nicht_stecken(self, dt: float, will):
        """Kommt er nicht vom Fleck, obwohl er will: kurz anders herum."""
        k = self.k
        if self.ausweich_rest > 0.0:
            return self.ausweich
        if will.length_squared() < 0.01:
            self.stockt_ort.update(k.pos)
            self.stockt_rest = K.BOTS["stockt_nach"]
            return will
        if self.stockt_rest <= 0.0:
            if k.pos.distance_to(self.stockt_ort) < 10.0:
                self.ausweich = will.rotate(self.rnd.choice((-1, 1)) * self.rnd.uniform(70, 150))
                self.ausweich_rest = self.rnd.uniform(0.4, 0.8)
                self.wegpunkt = None
                self.streif_rest = 0.0 if self.rnd.random() < 0.5 else self.streif_rest
            self.stockt_ort.update(k.pos)
            self.stockt_rest = K.BOTS["stockt_nach"]
        else:
            self.stockt_rest -= dt
        return will


class BotTeil:
    """Was das Gefecht fuer die Bots tut: aufstellen, wegnehmen, steuern.
    Wie LobbyTeil und KosmetikTeil ein Anteil des Gefechts."""

    def _bots_anlegen(self) -> None:
        self._bot_rnd = random.Random(getattr(self, "_bot_seed", None))
        self._bots_rest = 0.0
        # Schuesse, die die Bots hoeren: (Ort, Ebene, Zeit, Fraktion).
        self._bot_geraeusche: list = []

    def _ist_bot(self, nummer) -> bool:
        try:
            return int(nummer) >= K.BOTS["nummer_ab"]
        except (TypeError, ValueError):
            return False

    @property
    def bots_soll(self) -> int:
        """Wie viele Spieler es mit Bots insgesamt sein sollen, 0 = keine."""
        if self.in_lobby or not self.regeln.get("beute"):
            return 0
        return int(self.regelwerk.get("bots", 0) or 0)

    def _bots(self) -> list:
        return [k for k in self.kaempfer.values() if getattr(k, "ist_bot", False)]

    def _bot_fehlen(self) -> list:
        """Je Mannschaft (oder ohne: -1), wie viele Bots dazu sollen -
        negativ: so viele zu viel."""
        soll = self.bots_soll
        menschen = [k for k in self.kaempfer.values() if not getattr(k, "ist_bot", False)]
        bots = self._bots()
        if not self.mit_teams:
            return [(-1, max(0, soll - len(menschen)) - len(bots))]
        anzahl = len(K.TEAMS["namen"])
        je_team = [sum(1 for k in menschen if k.team == i) for i in range(anzahl)]
        ziel = max([-(-soll // anzahl)] + je_team) if soll else 0
        raus = []
        for i in range(anzahl):
            da = sum(1 for k in bots if k.team == i)
            raus.append((i, (ziel - je_team[i]) - da if soll else -da))
        return raus

    def _bots_fuehren(self, dt: float, sofort: bool = False) -> None:
        """Nachzaehlen: Bots dazu, wo welche fehlen, weg, wo zu viele sind.
        Einer nach dem anderen und jedes Mal neu gezaehlt - so kann keine
        Mannschaft dabei ueberlaufen."""
        if not self.ist_gastgeber:
            return
        self._bots_rest -= dt
        if not sofort and self._bots_rest > 0.0:
            return
        self._bots_rest = K.BOTS["verwalten_takt"]
        for _ in range(4 * len(K.BOTS["auffuellen"]) + 8):
            plan = self._bot_fehlen()
            fehlt = [t for t, n in plan if n > 0]
            zu_viel = [t for t, n in plan if n < 0]
            if fehlt:
                self._bot_dazu(fehlt[0])
            elif zu_viel:
                team = zu_viel[0]
                kandidaten = [k for k in self._bots() if team < 0 or k.team == team]
                if not kandidaten:
                    break
                # Wer tot ist oder gerade nicht kaempft, geht zuerst.
                k = max(kandidaten, key=lambda x: (not x.lebt,
                                                   getattr(x.hirn, "ziel", None) is None,
                                                   x.nummer))
                self._bot_weg(k)
            else:
                break

    def _bot_dazu(self, team: int):
        """Ein Bot in genau diese Mannschaft - nicht ueber _team_fuer, das
        jeden in die kleinere steckt und dabei das Auffuellen durcheinander
        braechte."""
        from .mehrspieler import Kaempfer
        nummer = K.BOTS["nummer_ab"]
        while nummer in self.kaempfer:
            nummer += 1
        vergeben = {k.name for k in self.kaempfer.values()}
        namen = [n for n in K.BOTS["namen"] if "BOT-" + n not in vergeben]
        name = "BOT-" + (self._bot_rnd.choice(namen) if namen else str(nummer - 99))
        k = Kaempfer(self._einstiegsort(team), 0, nummer, name,
                     self._fraktion_fuer(nummer, team), knapp=self.knapp,
                     team=team)
        k.ist_bot = True
        k.angemeldet = None
        k.team_wunsch = team
        k.konto = ""
        self._regeln_anlegen(k)
        k.unverwundbar = self.schutz_zeit
        k.medkits = self.start_medkits
        self.kaempfer[nummer] = k
        self.welt.dazu(k)
        self._namen_merken(k)
        k.hirn = BotHirn(self, k, self._bot_rnd)
        self._loadout_anlegen(k)
        self._magazine_fuellen(k)
        return k

    def _bot_weg(self, k) -> None:
        self._fahrzeug_loesen(k)
        k.lebt = False
        self.kaempfer.pop(k.nummer, None)

    def _bots_alle_weg(self) -> None:
        for k in self._bots():
            self._bot_weg(k)

    def _bot_loadout_anlegen(self, k) -> None:
        """Zu jedem Leben ein neues, zufaelliges Loadout - ohne C4."""
        fest = self._fest_loadout() if self.loadout_regel == "gleich" else None
        lo = bot_loadout(self._bot_rnd, fest)
        plaetze = konto_modul.hotbar_aus_loadout(lo)
        k.loadout = lo
        k.waffen = plaetze
        k.waffe = 0
        k.magazin = {w: K.WAFFEN[w]["magazin"] for w in plaetze}
        k.vorrat = {w: K.MUNITION["vorrat"].get(w, 0) for w in plaetze}

    def _bots_steuern(self, dt: float) -> None:
        """Jeder Bot schickt seine Eingabe, wie ein Gast."""
        jetzt = self.welt.zeit
        self._bot_geraeusche = [g for g in self._bot_geraeusche if jetzt - g[2] < 2.0]
        for k in self._bots():
            hirn = getattr(k, "hirn", None)
            if hirn is None:
                continue
            self._anwenden(k, hirn.eingabe(dt))

    def _bot_hoert(self, pos, ebene: int, quelle) -> None:
        """Ein Schuss oder Knall - fuer die Ohren der Bots."""
        if not self._bots():
            return
        fraktion = getattr(getattr(quelle, "von", quelle), "fraktion", "")
        self._bot_geraeusche.append((pygame.Vector2(pos), int(ebene),
                                     self.welt.zeit, fraktion))
        if len(self._bot_geraeusche) > 40:
            del self._bot_geraeusche[:10]
