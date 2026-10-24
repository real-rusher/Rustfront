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
Aufgabe der Spielart: in HUEGEL geht er in den Kreis und bleibt dort - der
Kreis geht vor, auch im Kampf (er schiesst auf dem Weg dorthin) -, in
VERSUS hilft er gefallenen Mitspielern auf, sonst sucht er Gegner - dort,
wo er zuletzt einen sah oder hoerte, oder auf der Karte. Er nimmt Treppen
und Aufzuege (dasselbe Wegenetz wie die Zombies), wechselt zwischen seinen
beiden Waffen je nach Abstand und laedt nach.

**Deckung (seit 0.34.26).** Zum Nachladen und wenn er angeschlagen ist und
getroffen wird, geht er hinter die naechste Mauer oder Kiste, die ihn vom
Gegner trennt (`_deckung`). Steht eine Kiste in seiner Schusslinie, schiesst
er nicht hinein, sondern geht zur Seite, bis er freie Bahn hat.

**Funk und Taktik (seit 0.34.27).** Er sagt an, was er vorhat, flankiert,
haelt nieder, gibt Feuerschutz und stuermt mit anderen Bots - siehe
bottaktik.py.

**Was er hat (seit 0.34.26).** Gemeldet: "Die Bots sollen jeweils zwei
verschiedene Waffen haben ... auch eine Granate haben, aber jeweils nur in
ihrem Leben eine werfen koennen ... keine Medkits oder Munition einsammeln,
sondern wenn ihre Munition und Granaten aufgebraucht sind, einfach in den
Nahkampf gehen." Also: zwei verschiedene Waffen, eine Granate, die
gewoehnliche Reserve und kein Medkit - immer mit knapper Munition, egal was
die Runde sagt. Aufgehoben wird nichts. Ist alles weg, geht er mit dem
Brecheisen auf den naechsten los. Sein Leben ist das eines Spielers.

**Was er nicht darf.** Kein C4 (auch nicht, wenn der Gastgeber eines fuer
alle vorgibt), keinen Raketenwerfer aufheben, nicht in einen Buggy steigen.
Sein Loadout wird zu jedem Leben neu gewuerfelt - ausser bei "eines fuer
alle", dann traegt er das wie jeder (mit hoechstens einer Wurfwaffe).

**Wie viele.** Zwei Regeln, es gilt die groessere Zahl: AUFFUELLEN BIS
macht die Mannschaften gleich gross, BOTS IN ROT / BLAU (ohne Mannschaften:
BOTS DAZU) stellt so viele fest dazu. Beides stellt der Gastgeber im
Team-Manager ein (Pausenmenue, TEAMS UND BOTS), vor der Runde oder mitten
darin.

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
from .bottaktik import Taktik, braucht_schutz, stuerme_fuehren, unterdrueckung_pruefen


def _winkel_zu(von, nach) -> float:
    d = nach - von
    return math.degrees(math.atan2(d.y, d.x))


def _winkel_diff(a: float, b: float) -> float:
    """b - a, auf -180 bis 180."""
    return (b - a + 180.0) % 360.0 - 180.0


def bot_loadout(rnd, fest=None) -> dict:
    """Ein Loadout fuer einen Bot: zwei verschiedene Waffen und eine
    Granate (K.BOTS["wurf_arten"]) - oder das vorgegebene ("eines fuer
    alle"), dann aber auch nur mit einer Wurfwaffe. C4 nie."""
    lo = K.LOADOUT
    wuerfe = [w for w in K.BOTS["wurf_arten"] if w != "c4"]
    if fest:
        raus = konto_modul.loadout_saeubern(fest) or {}
        raus = dict(raus)
        raus["wuerfe"] = [w for w in raus.get("wuerfe", []) if w != "c4"][:1]
        if not raus["wuerfe"]:
            raus["wuerfe"] = [rnd.choice(wuerfe)]
        return raus
    waffen = rnd.sample(list(lo["auswahl_waffen"]), 2)
    return {"name": "BOT", "waffen": waffen, "wuerfe": [rnd.choice(wuerfe)]}


class BotHirn(Taktik):
    """Was ein Bot denkt. Liefert je Schritt eine Eingabemeldung. Funk und
    Taktik (flankieren, niederhalten, stuermen) stehen in bottaktik.py."""

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
        self._pause_naechste = 0.3    # so lange die Pause nach diesem Stoss
        self.seite = self.rnd.choice((-1.0, 1.0))
        self.seite_rest = 0.0
        self.denk_rest = self.rnd.uniform(0.0, K.BOTS["takt"])
        self.wurf_rest = self.rnd.uniform(*K.BOTS["wurf_pause"]) * 0.5
        self.wurf_phase = 0.0         # > 0: zielt gerade zum Wurf
        self.wurf_platz = -1
        self._wurf_warten = 0.0       # so lange wartet er schon, bis er zum Ziel schaut
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
        self.getroffen_rest = 0.0     # so lange ist der letzte Treffer her
        self.deckung_ort = None       # wo er sich gerade versteckt
        self.deckung_rest = 0.0       # so lange bleibt er noch dort
        self.deckung_pause = 0.0      # so lange keine neue Deckung (angeschlagen)
        self.deckung_suche = 0.0      # so lange gilt der gefundene Ort
        self.linie = ""               # was zwischen ihm und dem Ziel steht
        # Wiederbelebt und geschwaecht (seit 0.34.40, Testmodus): er haelt
        # mehr Abstand - Aufgaben auf Distanz.
        self.geschwaecht = False
        self.abstand_mehr = 0.0
        self.taktik_anlegen()

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
            # Am Boden bleibt nur das Rufen - wie bei einem Menschen. Was er
            # vorhatte, ist vorbei (seit 0.34.46: in der Anzeige stand
            # weiter FLANKIEREN).
            self.liegt()
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

        # Getroffen worden: dorthin schauen, woher es kam.
        if k.leben < self.leben_vorher - 0.5:
            self.getroffen_rest = 2.0
            self._getroffen()
        self.leben_vorher = k.leben
        # Nachladen ansagen - dann wissen die anderen, dass sie ihn decken
        # muessen (bottaktik.braucht_schutz).
        laedt = k.nachlade_rest > 0.0
        if laedt and not self.laden_vorher and self.ziel is not None:
            self.funken("nachladen")
        self.laden_vorher = laedt

        will, ziel_punkt, feuern, zielt = self._entscheiden(dt, ein)

        will = self._sicher(will)
        will = self._nicht_stecken(dt, will)

        # Fadenkreuz: schwenkt, springt nicht.
        if ziel_punkt is None:
            ziel_punkt = self._blick_ohne_ziel(will)
        soll = _winkel_zu(k.pos, ziel_punkt)
        ab = _winkel_diff(self.blick, soll)
        schritt = K.BOTS["dreh"] * dt
        self.blick += max(-schritt, min(schritt, ab))
        weit = max(40.0, k.pos.distance_to(ziel_punkt))
        maus = k.pos + pygame.Vector2(1, 0).rotate(self.blick) * weit
        if feuern and k.waffe_daten.get("art") == "schuss" and self.kamerad_im_weg(weit):
            feuern = False
        ein["ziel"] = [round(maus.x, 1), round(maus.y, 1)]
        if (feuern and k.waffe_daten.get("art") == "schuss"
                and self.g.welt.deckung(k.pos, pygame.Vector2(ein["ziel"]), k.ebene) == "wand"):
            # Nie in eine Mauer (seit 0.34.54, gemeldet: "Bots versuchen oft
            # durch Mauern zu schiessen") - sie haelt jede Kugel auf, und
            # dahinter sieht er nichts. In eine Kiste ("hindernis") darf er
            # weiter: so haelt er den nieder, der dahinter sitzt. Gefragt mit
            # dem Punkt, der an die Figur geht (gerundet).
            feuern = False
        ein["will"] = [round(will.x, 2), round(will.y, 2)]
        ein["feuert"] = bool(feuern)
        ein["zielt"] = bool(zielt)
        return ein

    def _blick_ohne_ziel(self, will):
        """Wohin er schaut, wenn er nichts anvisiert: wohin er geht - aber
        erst, wenn er eine Weile in dieselbe Richtung geht -, sonst
        geradeaus weiter. Vorher folgte der Blick jedem Trippelschritt zur
        Stellung hin, und wer viermal in vier Richtungen trat, drehte sich
        dabei fast auf der Stelle einmal ganz um sich selbst (seit 0.34.55,
        gemeldet: "teils drehen sich bots in verschiedensten Situationen um
        360 grad")."""
        k = self.k
        geradeaus = k.pos + pygame.Vector2(1, 0).rotate(self.blick) * 120
        if will.length_squared() <= 0.01:
            self._lauf_richtung = None
            return geradeaus
        jetzt = self.g.welt.zeit
        alt = getattr(self, "_lauf_richtung", None)
        if alt is None or abs(_winkel_diff(alt.as_polar()[1], will.as_polar()[1])) > K.BOTS["lauf_blick_winkel"]:
            self._lauf_richtung = pygame.Vector2(will)
            self._lauf_seit = jetzt
        if jetzt - getattr(self, "_lauf_seit", jetzt) < K.BOTS["lauf_blick_ruhe"]:
            return geradeaus
        return k.pos + will * 120

    def _entscheiden(self, dt: float, ein: dict):
        """Was er jetzt tut: (Laufrichtung, Zielpunkt, feuern, zielen).

        Die klassische Entscheidung als feste Reihenfolge. Seit 0.34.29
        eine eigene Methode: die zielorientierte KI (bot_goap.GoapHirn)
        ersetzt genau diesen Teil und behaelt alles andere - Sehen,
        Zielen, Feuerstoesse, Wege."""
        k = self.k
        will = pygame.Vector2(0, 0)
        ziel_punkt = None            # wohin das Fadenkreuz will
        feuern = False
        zielt = False
        helfen = self._wem_helfen()
        kaempft = self.ziel is not None and self.ziel_ok(self.ziel)
        # Aufhelfen ist in VERSUS die Aufgabe: liegt einer nah und ist der
        # Gegner nicht gerade dicht dran, geht das vor.
        if (kaempft and helfen is not None
                and k.pos.distance_to(helfen.pos) < 160.0
                and k.pos.distance_to(self.ziel.pos) > 260.0):
            kaempft = False
        if kaempft:
            will, ziel_punkt, feuern, zielt = self._kaempfen(dt, ein)
        elif helfen is not None:
            will, ziel_punkt = self._helfen(helfen, ein)
        else:
            # Ohne Gegner im Blick: der Sturm der Mannschaft, dann der eben
            # verschwundene Gegner (niederhalten, flankieren), dann der
            # gewoehnliche Weg. In HUEGEL geht ausserhalb des Kreises der
            # Kreis vor - hinterherlaufen kann man spaeter.
            plan = self.taktik_sturm(dt, ein)
            zone = self._zone()
            draussen = zone is not None and (k.ebene != zone[1] or k.pos.distance_to(zone[0])
                                             > K.ZONE["radius"])
            ohne = None if plan is not None or draussen else self.taktik_ohne_sicht(dt, ein)
            if plan is not None:
                will, ziel_punkt, feuern = plan
            elif ohne is not None:
                will, ziel_punkt, feuern = ohne
            else:
                will, ziel_punkt = self._unterwegs(dt, ein)
        return will, ziel_punkt, feuern, zielt

    def _zeiten(self, dt: float) -> None:
        for name in ("reaktion_rest", "stoss_rest", "pause_rest", "seite_rest",
                     "wurf_rest", "waffen_rest", "weg_rest",
                     "streif_rest", "ausweich_rest", "geblendet",
                     "getroffen_rest", "deckung_rest", "deckung_pause",
                     "deckung_suche"):
            setattr(self, name, max(0.0, getattr(self, name) - dt))
        self.taktik_zeiten(dt)
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
        if getattr(w, "ki_unsichtbar", False):
            return False                  # Gottmodus UNSICHTBAR (testmodus.py)
        return hasattr(w, "nummer") or getattr(w, "fraktion", "") == "feind"

    def ziel_ok(self, w) -> bool:
        # Wer liegt, ist kein Ziel (seit 0.34.52): sonst hielten Aktionen und
        # Gefahr (bot_goap._gefahr) ihn fest, und das Niederhalten schoss
        # Stoss um Stoss auf die Stelle, an der er lag.
        return self.ist_feind(w) and w.ebene == self.k.ebene and not getattr(w, "am_boden", False)

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
            # Wer liegt, ist keine Gefahr mehr (bottaktik.kampffaehig): nicht
            # hinsehen spart je Liegendem eine Sichtlinie (seit 0.34.52).
            if getattr(w, "am_boden", False):
                continue
            if self.sieht(w):
                sichtbar.append(w)
                self.gesehen[w] = (pygame.Vector2(w.pos), w.ebene, jetzt)
        # Vergessen, was zu lange her ist - und wer liegt.
        for w in list(self.gesehen):
            if (jetzt - self.gesehen[w][2] > K.BOTS["gedaechtnis"] or not w.lebt
                    or getattr(w, "am_boden", False)):
                del self.gesehen[w]
        # Wer am Boden liegt, ist kein Ziel mehr (seit 0.34.46, gemeldet:
        # "sie feuern immer sehr lange auf Gegner, die schon am Boden sind").
        # Seit 0.34.52 endet auch der Stoss, der lief: ein Dauerfeuer hielt
        # sonst vier Sekunden auf den Liegenden.
        liegt = self.ziel is not None and getattr(self.ziel, "am_boden", False)
        if liegt:
            self.stoss_rest = 0.0
        if (self.ziel is not None and self.ziel in sichtbar and not liegt
                and self._ziel_erlaubt(self.ziel)):
            # Er bleibt dran - ausser ein anderer, den er sieht, hat ihn eben
            # getroffen (seit 0.34.38). Wer von der Seite beschossen wird,
            # dreht sich zu dem, der schiesst, statt stur auf den ersten zu
            # halten. Mitten im Feuerstoss nicht: den bringt er zu Ende.
            von = getattr(k, "zuletzt_von", None)
            von = getattr(von, "von", von)
            if (von is not None and von is not self.ziel and von in sichtbar
                    and self.getroffen_rest > 1.6 and self.stoss_rest <= 0.0):
                self.feuerschutz_fuer = None
                self._neues_ziel(von, False)
                self.linie = self.g.welt.deckung(k.pos, von.pos, k.ebene)
                return
            self.linie = self.g.welt.deckung(k.pos, self.ziel.pos, k.ebene)
            return
        alt = self.ziel
        self.ziel = None
        sichtbar = [w for w in sichtbar
                    if not getattr(w, "am_boden", False) and self._ziel_erlaubt(w)]
        if sichtbar:
            zone = self._zone()
            # Feuerschutz: wer einem Kameraden zu nahe kommt, der gerade
            # nachlaedt, liegt oder flankiert, ist zuerst dran.
            schuetzlinge = [x for x in self.kameraden() if braucht_schutz(x)]
            def wert(w):
                d = k.pos.distance_to(w.pos)
                d -= self.schutz_bonus(w, schuetzlinge)[0]
                d -= self._ziel_bonus(w)
                # HUEGEL: wer im Kreis steht, nimmt ihn uns weg.
                if zone is not None and w.ebene == zone[1] \
                        and w.pos.distance_to(zone[0]) <= K.ZONE["radius"]:
                    d -= 150.0
                return d
            neu = min(sichtbar, key=wert)
            self.feuerschutz_fuer = self.schutz_bonus(neu, schuetzlinge)[1]
            self._neues_ziel(neu, neu is alt)
            self.linie = self.g.welt.deckung(k.pos, neu.pos, k.ebene)
            return
        # Niemand zu sehen: wo er zuletzt jemanden sah, sonst was er hoerte.
        if alt is not None and alt in self.gesehen and not getattr(alt, "am_boden", False):
            ort, ebene, _t = self.gesehen[alt]
            self.verdacht = (ort, ebene, jetzt + K.BOTS["gedaechtnis"])
        geraeusch = self._hoeren()
        if geraeusch is not None and (self.verdacht is None or self.verdacht[2] < jetzt):
            self.verdacht = geraeusch

    def liegt(self) -> None:
        """Er ist zu Boden gegangen: kein Ziel, keine Taktik, kein Sturm."""
        self.ziel = None
        self.verdacht = None
        self.taktik = None
        self.deckung_ort = None
        self.stoss_rest = 0.0

    def _ziel_erlaubt(self, w) -> bool:
        """Darf er auf diesen sichtbaren Gegner schiessen? Hier jeden - im
        Trupp mit geknickter Front nur den in seinem Abschnitt (bot_goap.py)."""
        return True

    def _ziel_bonus(self, w) -> float:
        """So viel lieber nimmt er diesen Gegner (in Pixeln Abstand) - hier
        nichts; im Trupp der, der den Anfuehrer bedroht (bot_goap.py)."""
        return 0.0

    def _neues_ziel(self, w, gleiches: bool) -> None:
        b = K.BOTS
        self.ziel = w
        if gleiches:
            return                            # kurz verdeckt, wieder da
        self.funken("feuerschutz" if self.feuerschutz_fuer is not None else "kontakt")
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
        bestes, beste = None, 1e9
        for (ort, ebene, zeit, fraktion, weite) in getattr(self.g, "_bot_geraeusche", ()):
            if jetzt - zeit > 1.5 or fraktion == k.fraktion:
                continue
            d = k.pos.distance_to(ort)
            if d < weite and d < beste:
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
        vorzug = K.BOTS["waffe_vorzug"]
        return min(liste, key=lambda p: abs(wunsch.get(p[1], 220.0) - abstand)
                   - vorzug.get(p[1], 0.0)
                   + (0 if self.k.magazin.get(p[1], 0) > 0 else 60))

    def _stoss(self):
        """(Stoss, Pause, still?) fuer die Waffe in der Hand - je Waffe aus
        K.BOTS["feuer"], sonst die gewoehnlichen Werte."""
        b = K.BOTS
        eigen = b["feuer"].get(self.k.waffe_name)
        if eigen is None:
            return (self.rnd.uniform(*b["feuerstoss"]), self.rnd.uniform(*b["feuerpause"]),
                    self.rnd.random() < b["still_beim_schiessen"])
        stoss, pause, still = eigen
        return (self.rnd.uniform(*stoss), self.rnd.uniform(*pause),
                self.rnd.random() < still)

    def fehler_faktor(self) -> float:
        """x Zielfehler aus dem Zustand des Schuetzen - hier immer 1, das
        GOAP-Hirn rechnet den Stress dazu (bot_goap.py)."""
        return 1.0

    def gruppe_um(self, z):
        """Die Gegner, die mit `z` eine Gruppe bilden (er selbst dabei),
        soweit er sie sieht oder eben sah - fuer Granate und Flaechenfeuer."""
        weite = K.BOTS["flaeche_weite"]
        jetzt = self.g.welt.zeit
        raus = [z]
        for w, (ort, ebene, zeit) in self.gesehen.items():
            if w is z or not w.lebt or ebene != z.ebene or jetzt - zeit > 1.0:
                continue
            if getattr(w, "am_boden", False):
                continue
            if ort.distance_to(z.pos) <= weite:
                raus.append(w)
        return raus

    def _kaempfen(self, dt: float, ein: dict, mit_deckung: bool = True):
        """`mit_deckung` False (seit 0.34.38): wann er in Deckung geht,
        entscheidet ein anderer (das GOAP-Gehirn) - nicht jede Kugel, die
        vorbeipfeift."""
        k = self.k
        b = K.BOTS
        z = self.ziel
        abstand = k.pos.distance_to(z.pos)
        sichtbar = z in self.gesehen and self.gesehen[z][2] >= self.g.welt.zeit - 0.15

        # Zielfehler: gross beim ersten Sehen, wird kleiner, wackelt etwas.
        massstab = max(0.5, min(2.0, abstand / 250.0))
        fehler = max(b["fehler_min"], b["fehler_start"]
                     * math.exp(-self.fehler_zeit / b["fehler_abbau"]))
        if self.unterdrueckt > 0.0:
            fehler *= b["unterdrueckt_fehler"]   # Kugeln um die Ohren
        fehler *= self.fehler_faktor()
        self.fehler.rotate_ip(self.rnd.uniform(-40, 40) * dt * 3)
        ziel_punkt = z.pos + self.fehler * (fehler * massstab)
        # Mehrere dicht beieinander: ungefaehr in die Richtung, hin und her
        # ueber die Gruppe statt genau auf einen (seit 0.34.38).
        gruppe = self.gruppe_um(z) if k.waffe_name in b["feuer"] else [z]
        if len(gruppe) >= 2:
            mitte = sum((pygame.Vector2(w.pos) for w in gruppe), pygame.Vector2(0, 0)) / len(gruppe)
            breite = max(w.pos.distance_to(mitte) for w in gruppe) + 10.0
            hin = mitte - k.pos
            if hin.length_squared() > 1.0:
                quer = pygame.Vector2(-hin.y, hin.x).normalize()
                schwenk = math.sin(self.g.welt.zeit * b["flaeche_schwenk"] * math.tau)
                ziel_punkt = mitte + quer * (schwenk * breite) + self.fehler * (fehler * 0.5)

        # Wurf: ab und zu, wenn es passt.
        if self.wurf_phase > 0.0:
            return self._werfen(dt, ein, z)
        waffe = self._beste_waffe(abstand)
        # Erst die Granate, dann - wenn auch die weg ist - das Brecheisen.
        if self._wurf_moeglich(abstand, waffe is None, len(self.gruppe_um(z))) and sichtbar:
            self.wurf_phase = 0.45
            self.wurf_rest = self.rnd.uniform(*b["wurf_pause"])
            self.funken("granate", wichtig=True)
            return self._werfen(dt, ein, z)
        if waffe is None:
            return self._nahkampf(ein, z, abstand)
        nr, name = waffe
        if nr != k.waffe and self.waffen_rest <= 0.0 and k.nachlade_rest <= 0:
            ein["waffe"] = nr
            self.waffen_rest = 1.2
        # Nur eine Schusswaffe laedt man nach. Mit der eben geworfenen
        # Granate noch in der Hand hiess das sonst: 3,2 Sekunden Granate
        # nachladen, statt die Waffe zu nehmen (gefunden 0.34.38).
        if (k.magazin.get(k.waffe_name, 0) <= 0 and k.nachlade_rest <= 0
                and nr == k.waffe and K.WAFFEN[k.waffe_name].get("art") == "schuss"):
            ein["knoepfe"].append("nachladen")

        # Bewegen: Abstand halten, seitlich ausweichen - oder in Deckung.
        will = self._kampfbewegung(abstand, z, ein)
        versteckt = self._deckung(z, ein) if mit_deckung else None
        taktik = None
        druck = False
        if versteckt is not None:
            will = versteckt
        else:
            # Flankieren oder niederhalten (bottaktik.py).
            taktik = self.taktik_im_kampf(z, sichtbar, ein)
            if taktik is not None:
                will, punkt, druck = taktik
                if punkt is not None:
                    ziel_punkt = punkt

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
        if druck:
            # Niederhalten: auf die Stelle neben seiner Deckung, auch ohne
            # ihn zu treffen. Das Fadenkreuz muss genau dort sein.
            bereit = (self.reaktion_rest <= 0.0 and abstand <= reich
                      and k.nachlade_rest <= 0)
            erlaubt = 6.0
        elif self.linie == "hindernis":
            # Eine Kiste in der Schusslinie haelt jede Kugel auf (seit
            # 0.34.26). Hineinschiessen waere Munition verschenken: er
            # geht zur Seite, bis er freie Bahn hat.
            bereit = False
            if versteckt is None and taktik is None:
                hin = z.pos - k.pos
                if hin.length_squared() > 1.0:
                    hin = hin.normalize()
                    will = pygame.Vector2(-hin.y, hin.x) * self.seite * 0.9 + hin * 0.3
        if name == "scharf" and sichtbar and abstand > 90:
            zielt = True
            bereit = bereit and k.fokus >= 0.8
        if len(gruppe) >= 2 and not druck:
            # Flaechenfeuer: das Fadenkreuz soll ueber der Gruppe liegen,
            # nicht genau auf einem.
            erlaubt = max(erlaubt, math.degrees(math.atan2(K.BOTS["flaeche_weite"],
                                                           max(1.0, abstand))))
        if self.stoss_rest > 0.0 and k.waffe_name in b["feuer"]:
            # Laeuft der Stoss schon, haelt er drauf und fuehrt die Garbe
            # nach, statt bei jedem Wackeln loszulassen - so schiesst man
            # ein MG (seit 0.34.38), das sich ja nur langsam drehen laesst.
            erlaubt *= 3.0
        if getattr(z, "am_boden", False):
            # Liegt er, kein neuer Stoss mehr: sonst begann jeder neue, bevor
            # das Ziel beim naechsten Hinsehen (_wahrnehmen, alle `takt`) wegfiel.
            self.stoss_rest = 0.0
            bereit = False
        if bereit and winkel_fehler <= erlaubt:
            if self.stoss_rest <= 0.0 and self.pause_rest <= 0.0:
                stoss, self._pause_naechste, self.still = self._stoss()
                if len(gruppe) >= 2:
                    stoss *= b["dauerfeuer"]
                self.stoss_rest = stoss
            if self.stoss_rest > 0.0:
                feuern = True
                if self.stoss_rest <= dt:
                    self.pause_rest = self._pause_naechste
        if feuern and self.still and versteckt is None:
            will = pygame.Vector2(0, 0)
        return will, ziel_punkt, feuern, zielt

    def _kampfbewegung(self, abstand: float, z, ein: dict | None = None):
        k = self.k
        if self.seite_rest <= 0.0:
            self.seite_rest = self.rnd.uniform(0.7, 1.6)
            if self.rnd.random() < 0.55:
                self.seite = -self.seite
        wunsch = K.BOTS["wunschabstand"].get(k.waffe_name, 220.0) + self.abstand_mehr
        hin = z.pos - k.pos
        if hin.length_squared() < 1.0:
            hin = pygame.Vector2(1, 0)
        hin = hin.normalize()
        quer = pygame.Vector2(-hin.y, hin.x) * self.seite
        # HUEGEL: der Kreis geht vor. Wer draussen ist, kaempft auf dem Weg
        # dorthin - auch ueber die Treppe -, statt dem Gegner nachzulaufen
        # (seit 0.34.26; vorher zog es ihn nur auf derselben Ebene hin).
        zone = self._zone()
        if zone is not None and (k.ebene != zone[1] or k.pos.distance_to(zone[0])
                                 > K.ZONE["radius"] * 0.75):
            self.funken("kreis")
            will = self._weg_richtung(zone[0], zone[1], ein) * 0.85 + quer * 0.2
        elif abstand > wunsch + 40:
            # Heran - um Waende herum, wenn noetig.
            weg = self._weg_richtung(z.pos, z.ebene)
            will = weg * 0.9 + quer * 0.25
        elif abstand < wunsch - 40:
            will = -hin * 0.8 + quer * 0.45
        else:
            will = quer * 0.85 + hin * 0.1
        if will.length_squared() > 1.0:
            will = will.normalize()
        return will

    def _zone(self):
        """(Mitte, Ebene) des Kreises, wenn HUEGEL gespielt wird."""
        g = self.g
        if not g.regeln.get("zone"):
            return None
        return pygame.Vector2(g.zone_mitte), g.zone_ebene

    def _deckung(self, z, ein: dict):
        """In Deckung gehen (seit 0.34.26): zum Nachladen, und wenn er
        angeschlagen ist und gerade getroffen wird. Gibt die Laufrichtung
        dorthin zurueck - oder None, wenn er nicht in Deckung will oder
        keine findet.

        Deckung ist eine Stelle in der Naehe, zwischen der und dem Gegner
        eine Mauer oder ein Hindernis steht (Welt.deckung) - dieselbe
        Rechnung, mit der eine Kugel dort haengen bleibt. Gesucht wird in
        Ringen um ihn herum, der naechste Ring zuerst, und nur, wo er
        geradewegs hinkommt. Angeschlagen versteckt er sich nur kurz und
        danach eine Weile nicht wieder: Medkits hat er keine, und wer sich
        dauerhaft versteckt, verliert den Kreis."""
        k = self.k
        b = K.BOTS
        laedt = k.nachlade_rest > 0
        if (not laedt and self.deckung_pause <= 0.0 and self.getroffen_rest > 0.0
                and k.leben < b["deckung_leben"]):
            self.deckung_rest = b["deckung_zeit"]
            self.deckung_pause = b["deckung_pause"]
            self.funken("getroffen")
        # Niedergehalten (Kugeln knapp vorbei, seit 0.34.27): unten bleiben,
        # solange es pfeift. Genau das will, wer niederhaelt.
        if self.unterdrueckt > 0.0:
            self.deckung_rest = max(self.deckung_rest, self.unterdrueckt)
        if not laedt and self.deckung_rest <= 0.0:
            self.deckung_ort = None
            return None
        if self.deckung_ort is None or self.deckung_suche <= 0.0:
            self.deckung_ort = self._deckung_suchen(pygame.Vector2(z.pos))
            self.deckung_suche = 0.6
        if self.deckung_ort is None:
            return None
        d = self.deckung_ort - k.pos
        if d.length() < 4.0:
            return pygame.Vector2(0, 0)
        return d.normalize()

    def _deckung_suchen(self, gefahr):
        k = self.k
        welt = self.g.welt
        zone = self._zone()
        hin = gefahr - k.pos
        quer = (pygame.Vector2(-hin.y, hin.x).normalize() * (k.radius - 2)
                if hin.length_squared() > 1.0 else pygame.Vector2(0, 0))
        start = self.rnd.uniform(0.0, 30.0)
        bestes, beste = None, 1e9
        noch = None                   # so viele Ringe schaut er noch weiter
        for r in K.BOTS["deckung_radien"]:
            for i in range(12):
                p = k.pos + pygame.Vector2(r, 0).rotate(start + i * 30.0)
                if not welt.frei(p, k.radius + 2, k.ebene, True):
                    continue
                # Ganz verdeckt: Mitte und beide Seiten der Figur.
                if any(welt.deckung(gefahr, q, k.ebene) == ""
                       for q in (p, p + quer, p - quer)):
                    continue
                if not welt.wege.gerade_frei(k.ebene, k.pos, p, k.radius + 1):
                    continue
                wert = self._deckung_wert(p, gefahr, zone)
                if wert is not None and wert < 1e5 and wert < beste:
                    bestes, beste = p, wert
            if bestes is not None:
                # Das GOAP-Hirn schaut einen Ring weiter: eine Mauer etwas
                # dahinter ist besser als das Fass daneben (seit 0.34.46).
                noch = self.deckung_weiter if noch is None else noch - 1
                if noch <= 0:
                    return bestes
        return bestes

    deckung_weiter = 0                # Ringe, die er nach der ersten Deckung noch absucht

    def vorn_zu(self, punkt) -> bool:
        """Steht dicht vor ihm, Richtung `punkt`, etwas, das Kugeln aufhaelt
        - meist seine eigene Deckung? Dann schiesst und wirft er nicht
        (seit 0.34.46, gemeldet: "dass sie dann gegen ihre Deckung schiessen
        oder eine Granate gegen ihre Deckung werfen")."""
        k = self.k
        d = pygame.Vector2(punkt) - k.pos
        laenge = d.length()
        if laenge < 1.0:
            return False
        nah = k.pos + d * (min(laenge, K.BOTS["vorn_frei"]) / laenge)
        return self.g.welt.deckung(k.pos, nah, k.ebene) != ""

    def kamerad_im_weg(self, weite: float) -> bool:
        """Steht ein Kamerad dort, wohin der Lauf gerade zeigt, naeher als
        `weite`? Dann schiesst er nicht (seit 0.34.52, gemeldet: sie
        schossen "manchmal auf Teammates"). Wer liegt, ist unter der Bahn."""
        k = self.k
        hin = pygame.Vector2(1, 0).rotate(self.blick)
        luecke = K.BOTS["kamerad_linie"]
        for x in self.kameraden():
            if x.ebene != k.ebene or getattr(x, "am_boden", False):
                continue
            d = x.pos - k.pos
            vor = d.dot(hin)
            if vor <= 0.0 or vor > weite + luecke:
                continue
            if abs(d.cross(hin)) < luecke + getattr(x, "radius", 9.0) * 0.5:
                return True
        return False

    def _deckung_wert(self, p, gefahr, zone):
        """Wie gut diese Deckung ist (kleiner ist besser), oder None, wenn
        sie nicht in Frage kommt. Das GOAP-Hirn rechnet hier alle Gegner
        dazu, die es kennt (bot_goap.py)."""
        k = self.k
        wert = p.distance_to(k.pos) - 0.3 * p.distance_to(gefahr)
        if zone is not None and k.ebene == zone[1] \
                and p.distance_to(zone[0]) > K.ZONE["radius"]:
            wert += 200.0             # lieber im Kreis bleiben
        return wert

    def _nahkampf(self, ein: dict, z, abstand: float):
        """Keine Munition mehr: mit dem Brecheisen hin und zuschlagen."""
        k = self.k
        b = K.BOTS
        self.funken("leer")
        will = self._weg_richtung(z.pos, z.ebene)
        if abstand <= b["nahkampf_ab"] + getattr(z, "radius", 9.0):
            if self.reaktion_rest <= 0.0:
                ein["knoepfe"].append("nahkampf")
            will = will * 0.3
        # Kein Dash mehr (seit 0.34.38, gemeldet: "Dashes sollen sie nicht
        # haben") - auch nicht auf dem Weg zum Schlag.
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

    def _wurf_moeglich(self, abstand: float, leer: bool = False, gruppe: int = 1) -> bool:
        """`leer`: keine Munition mehr - dann wirft er, was er noch hat,
        ohne die Pause zwischen zwei Wuerfen abzuwarten. `gruppe`: so viele
        Gegner stehen dort beieinander - seine eine Granate hebt er sich
        fuer so etwas auf (seit 0.34.38)."""
        if (self.wurf_rest > 0.0 and not leer) or self.reaktion_rest > 0.0:
            return False
        nah, weit = K.BOTS["wurf_weite"]
        if not (nah <= abstand <= weit):
            return False
        self.wurf_platz = self._wurf_platz()
        if self.wurf_platz < 0:
            return False
        if self.ziel is not None and self.vorn_zu(self.ziel.pos):
            return False
        name = self.k.waffen[self.wurf_platz]
        if name == "rauch":
            # Rauch nur, wenn es eng wird: als Deckung zum Rueckzug.
            return self.k.leben < 45.0 or leer
        if gruppe >= 2:
            return True
        return leer or self.rnd.random() < 0.3

    def _werfen(self, dt: float, ein: dict, z):
        """Wurfwaffe nehmen, kurz zielen, werfen, zurueck zur Waffe."""
        k = self.k
        self.wurf_phase -= dt
        if self.wurf_phase > 1e-3:
            self._wurf_warten = 0.0           # ein neuer Wurf: noch nicht gewartet
        nr = self.wurf_platz
        if nr < 0 or nr >= len(k.waffen):
            self.wurf_phase = 0.0
            return pygame.Vector2(0, 0), pygame.Vector2(z.pos), False, False
        if k.waffe != nr:
            ein["waffe"] = nr
        ziel = pygame.Vector2(z.pos)
        gruppe = self.gruppe_um(z) if hasattr(z, "lebt") else [z]
        if len(gruppe) >= 2:
            # In die Mitte der Gruppe - so trifft sie die meisten.
            ziel = sum((pygame.Vector2(w.pos) for w in gruppe), pygame.Vector2(0, 0)) / len(gruppe)
        if k.waffen[nr] == "rauch" and not getattr(z, "genau", False):
            ziel = k.pos + (z.pos - k.pos) * 0.4
        werfen = self.wurf_phase <= 0.0 and k.waffe == nr
        if (werfen and self._wurf_warten < K.BOTS["wurf_warten"]
                and abs(_winkel_diff(self.blick, _winkel_zu(k.pos, ziel))) > K.BOTS["wurf_winkel"]):
            # Geworfen wird dorthin, wohin er schaut (seit 0.34.52): wer sich
            # erst umdrehen muss, wartet - sonst flog der Rauch fuer den
            # Verwundeten drei Kacheln an ihm vorbei (gemessen).
            self._wurf_warten += dt
            self.wurf_phase = 1e-4            # der Wurf laeuft noch: kein Umschauen
            werfen = False
        if werfen:
            self.wurf_phase = 0.0
            self.waffen_rest = 0.0
            self._wurf_warten = 0.0
        return pygame.Vector2(0, 0), ziel, werfen, False

    # ══════════════════════════════════════════════════════════════
    # Helfen (VERSUS)
    # ══════════════════════════════════════════════════════════════
    def _wem_helfen(self):
        g = self.g
        k = self.k
        bergen = g.bergen_an() if hasattr(g, "bergen_an") else g.regeln.get("revive")
        if not bergen or not g.mit_teams:
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
        self.funken("helfen")
        # Wer schon hilft, hilft ueber die Reichweite hinaus weiter, bis an
        # die Haltezone des Gefechts (seit 0.34.55): zwei Helfer schoben
        # einander genau auf die Grenze, und jeder fiel bei jedem Schubs
        # heraus und fing neu an.
        weite = K.REVIVE["reichweite"] + (K.REVIVE["halten"] - 1 if k.hilft == x.nummer else -4)
        if x.ebene == k.ebene and k.pos.distance_to(x.pos) <= weite:
            ein["nutzen"] = True
            ein["wen"] = x.nummer        # ihm, nicht dem, der zufaellig naeher liegt
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
                if k.ebene != ebene or k.pos.distance_to(mitte) > K.ZONE["radius"] * 2.0:
                    self.funken("kreis")
            else:
                if self.streif_rest <= 0.0 or self.streifzug is None:
                    p = pygame.Vector2(mitte) + pygame.Vector2(
                        self.rnd.uniform(-1, 1), self.rnd.uniform(-1, 1)) \
                        * K.ZONE["radius"] * 0.5
                    self.streifzug = (p, ebene)
                    self.streif_rest = self.rnd.uniform(1.5, 3.0)
                ziel = self.streifzug
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
        # Absprachen der Mannschaften (bottaktik.py): wer flankiert, wer
        # haelt nieder, wer stuermt gerade mit wem.
        self._bot_rollen = {}
        self._stuerme = []
        self._sturm_pause = {}
        # Schuesse, die die Bots hoeren: (Ort, Ebene, Zeit, Fraktion).
        self._bot_geraeusche: list = []

    def _ist_bot(self, nummer) -> bool:
        try:
            return int(nummer) >= K.BOTS["nummer_ab"]
        except (TypeError, ValueError):
            return False

    @property
    def bots_aktiv(self) -> bool:
        """Bots gibt es nur in Runden mit Gegnern aus Fleisch und Blut
        (pvp, team, versus, huegel) - nicht in der Lobby, nicht in pve."""
        return not self.in_lobby and bool(self.regeln.get("beute"))

    @property
    def bots_soll(self) -> int:
        """Wie viele Spieler es mit Bots insgesamt sein sollen, 0 = keine."""
        if not self.bots_aktiv:
            return 0
        return int(self.regelwerk.get("bots", 0) or 0)

    def bots_fest(self, team: int) -> int:
        """Wie viele Bots fest in dieser Mannschaft spielen (-1: ohne
        Mannschaften), unabhaengig von den Menschen (seit 0.34.26)."""
        if not self.bots_aktiv:
            return 0
        schluessel = "bots_dazu" if team < 0 else "bots_t%d" % team
        try:
            return max(0, int(self.regelwerk.get(schluessel, 0) or 0))
        except (TypeError, ValueError):
            return 0

    def _bots(self) -> list:
        return [k for k in self.kaempfer.values() if getattr(k, "ist_bot", False)]

    def _bot_fehlen(self) -> list:
        """Je Mannschaft (oder ohne: -1), wie viele Bots dazu sollen -
        negativ: so viele zu viel.

        Zwei Regeln, und es gilt die groessere Zahl: AUFFUELLEN BIS
        (`bots`) macht die Mannschaften gleich gross, BOTS IN ROT/BLAU
        (`bots_t0` ...) stellt so viele Bots fest in eine Mannschaft."""
        soll = self.bots_soll
        menschen = [k for k in self.kaempfer.values() if not getattr(k, "ist_bot", False)]
        bots = self._bots()
        if not self.mit_teams:
            braucht = max(max(0, soll - len(menschen)) if soll else 0,
                          self.bots_fest(-1))
            return [(-1, braucht - len(bots))]
        anzahl = len(K.TEAMS["namen"])
        je_team = [sum(1 for k in menschen if k.team == i) for i in range(anzahl)]
        ziel = max([-(-soll // anzahl)] + je_team) if soll else 0
        raus = []
        for i in range(anzahl):
            da = sum(1 for k in bots if k.team == i)
            braucht = max((ziel - je_team[i]) if soll else 0, self.bots_fest(i))
            raus.append((i, braucht - da))
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
        for _ in range(4 * len(K.BOTS["auffuellen"])
                       + K.BOTS["je_team_hoechstens"] * (len(K.TEAMS["namen"]) + 1) + 8):
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

    def _bot_dazu(self, team: int, hirn: str | None = None):
        """Ein Bot in genau diese Mannschaft - nicht ueber _team_fuer, das
        jeden in die kleinere steckt und dabei das Auffuellen durcheinander
        braechte. `hirn` ("klassisch"/"goap") geht vor der Regel BOT-KI -
        der Testmodus stellt beide nebeneinander."""
        from .mehrspieler import Kaempfer
        nummer = K.BOTS["nummer_ab"]
        while nummer in self.kaempfer:
            nummer += 1
        vergeben = {k.name for k in self.kaempfer.values()}
        namen = [n for n in K.BOTS["namen"] if "BOT-" + n not in vergeben]
        name = "BOT-" + (self._bot_rnd.choice(namen) if namen else str(nummer - 99))
        k = Kaempfer(self._einstiegsort(team), 0, nummer, name,
                     self._fraktion_fuer(nummer, team), knapp=True,
                     team=team)
        k.ist_bot = True
        k.angemeldet = None
        k.team_wunsch = team
        k.konto = ""
        self._regeln_anlegen(k)
        k.unverwundbar = self.schutz_zeit
        k.medkits = 0
        self.kaempfer[nummer] = k
        self.welt.dazu(k)
        self._namen_merken(k)
        if hirn is None:
            hirn = self.regelwerk.get("bot_ki", "klassisch")
        if hirn == "goap":
            from .bot_goap import GoapHirn
            k.hirn = GoapHirn(self, k, self._bot_rnd, K.GOAP["spezies_bot"])
        else:
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
        self._bot_munition(k)

    def _bot_munition(self, k) -> None:
        """Was ein Bot zu Beginn eines Lebens dabeihat (seit 0.34.26).

        Gemeldet: "Die sollen auch eine Granate haben, aber jeweils nur in
        ihrem Leben eine werfen koennen ... die sollen keine Medkits oder
        Munition einsammeln, sondern wenn ihre Munition und Granaten
        aufgebraucht sind, sollen sie einfach in den Nahkampf gehen."
        Darum immer knapp, egal was die Runde sagt: volle Magazine und ein
        Vorrat (`vorrat_anteil` des gewoehnlichen), eine Wurfwaffe ohne
        Nachschub, kein Medkit. Mit unbegrenzter Munition kaeme der
        Nahkampf nie."""
        b = K.BOTS
        k.knapp = True
        k.medkits = 0
        k.magazin = {}
        k.vorrat = {}
        for w in k.waffen:
            d = K.WAFFEN[w]
            if d.get("art") == "wurf":
                k.magazin[w] = b["wuerfe_je_leben"]
                k.vorrat[w] = 0
            else:
                k.magazin[w] = d["magazin"]
                k.vorrat[w] = int(round(K.MUNITION["vorrat"].get(w, 0)
                                        * b["vorrat_anteil"]))

    def _bots_steuern(self, dt: float) -> None:
        """Jeder Bot schickt seine Eingabe, wie ein Gast."""
        jetzt = self.welt.zeit
        self._bot_geraeusche = [g for g in self._bot_geraeusche if jetzt - g[2] < 2.0]
        if self._bots():
            unterdrueckung_pruefen(self)
            stuerme_fuehren(self, dt)
            if getattr(self, "_trupps", None):
                from .trupp import trupps_fuehren
                trupps_fuehren(self, dt)
        for k in self._bots():
            hirn = getattr(k, "hirn", None)
            if hirn is None:
                continue
            self._anwenden(k, hirn.eingabe(dt))

    def _bot_hoert(self, pos, ebene: int, quelle, weite: float | None = None) -> None:
        """Ein Schuss oder Knall - fuer die Ohren der Bots. `weite`: so weit
        ist er zu hoeren (Vorgabe: ein Schuss)."""
        if not self._bots():
            return
        fraktion = getattr(getattr(quelle, "von", quelle), "fraktion", "")
        self._bot_geraeusche.append((pygame.Vector2(pos), int(ebene),
                                     self.welt.zeit, fraktion,
                                     K.BOTS["gehoer"] if weite is None else float(weite)))
        if len(self._bot_geraeusche) > 40:
            del self._bot_geraeusche[:10]
