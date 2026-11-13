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
from .bottaktik import Taktik, braucht_schutz, kampffaehig, stuerme_fuehren, unterdrueckung_pruefen


def _winkel_zu(von, nach) -> float:
    d = nach - von
    return math.degrees(math.atan2(d.y, d.x))


# Welches Fahrzeug ein Bot lieber nimmt (seit 0.34.131), in Pixeln Umweg:
# was selten ist und viel bewirkt, zuerst - und damit eine Seite ihre Basis
# nutzt, steigen Fahrer dort ein, wo so etwas frei steht (front._fahrer_basis).
FAHRZEUG_VORZUG = {"tragschrauber": 520.0, "werfer": 480.0, "panzer": 420.0, "jagdpanzer": 400.0,
                   "spulenwagen": 340.0, "funkwagen": 320.0, "panzerwagen": 280.0, "flakwagen": 260.0,
                   "trosswagen": 220.0, "buggy": 60.0, "krad": 40.0}


def _winkel_diff(a: float, b: float) -> float:
    """b - a, auf -180 bis 180."""
    return (b - a + 180.0) % 360.0 - 180.0


def bot_aussehen(name: str) -> str:
    """Ein Bot traegt das Aussehen eines Soldaten (seit 0.34.60) - immer
    dasselbe zu seinem Namen. GRUND fuer einen eigenen Zufall aus dem
    Namen statt _bot_rnd: der Zufall der Bots entscheidet ueber ihr
    Verhalten, und ein Bild soll keinen Wurf davon verbrauchen
    (tests/test_verhalten.py laeuft mit festen Seeds)."""
    from .art_figuren import waehlbar
    soldaten = [s for s in waehlbar() if s in K.FIGUREN_GRUPPEN["SOLDAT"]]
    return random.Random(name).choice(soldaten) if soldaten else ""


def bot_waffen_gewichten(waffen: list, rnd) -> list:
    """Eine Waffe mit Gewicht unter 1 (K.BOTS waffen_gewicht: das MG) bleibt
    nur mit dieser Wahrscheinlichkeit, sonst kommt eine andere aus
    K.BOTS["waffen"], die er noch nicht hat.

    Gewuerfelt wird mit einem eigenen Zufall, der aus dem Stand von `rnd`
    abgeleitet ist, ohne ihn weiterzudrehen (seit 0.34.94): der Zufall der
    Bots (Merkmale, Namen, Aufstellung) bleibt so genau, wie er war, und
    dieselbe Szene ergibt dieselben Waffen - egal, was vorher lief."""
    gewicht = K.BOTS["waffen_gewicht"]
    zufall = random.Random(hash(rnd.getstate()[1][:24]))
    raus = list(waffen)
    for i, w in enumerate(raus):
        if zufall.random() < float(gewicht.get(w, 1.0)):
            continue
        andere = [x for x in K.BOTS["waffen"] if x not in raus
                  and float(gewicht.get(x, 1.0)) >= 1.0]
        if andere:
            raus[i] = andere[zufall.randrange(len(andere))]
    return raus


def bot_waffen_vielfalt(waffen: list, rnd) -> list:
    """Mehr Vielfalt (seit 0.34.95, K.BOTS vielfalt/varianten): eine
    gezogene Waffe wird manchmal gegen eine verwandte getauscht - statt des
    Sturmgewehrs eine MP, statt der Schrotflinte die Doppelflinte. Wie beim
    Gewichten mit eigenem Zufall aus dem Stand von `rnd`, ohne ihn
    weiterzudrehen."""
    b = K.BOTS
    zufall = random.Random(hash(rnd.getstate()[1][24:48]))
    raus = list(waffen)
    for i, w in enumerate(raus):
        andere = [x for x in b["varianten"].get(w, ()) if x in K.WAFFEN and x not in raus]
        if andere and zufall.random() < b["vielfalt"]:
            raus[i] = andere[zufall.randrange(len(andere))]
    return raus


def panzerjaeger_waffen(nummer: int, normal: str = "sturm") -> list:
    """Was ein Panzerjaeger traegt (seit 0.34.96, K.BOTS panzerjaeger): eine
    Panzerabwehrwaffe - nach Nummer meist Raketen, selten die
    Panzerbuechse - und eine gewoehnliche Waffe."""
    p = K.BOTS["panzerjaeger"]
    pa = p["waffen"][nummer % len(p["waffen"])]
    if normal == pa or normal not in K.WAFFEN:
        normal = "sturm"
    return [pa, normal]


def bot_loadout(rnd, fest=None, vielfalt: bool = False) -> dict:
    """Ein Loadout fuer einen Bot: zwei verschiedene Waffen und eine
    Granate (K.BOTS["wurf_arten"]) - oder das vorgegebene ("eines fuer
    alle"), dann aber auch nur mit einer Wurfwaffe. C4 nie. Die Waffen
    kommen aus K.BOTS["waffen"], nicht aus der Auswahl der Spieler."""
    wuerfe = [w for w in K.BOTS["wurf_arten"] if w != "c4"]
    if fest:
        raus = konto_modul.loadout_saeubern(fest) or {}
        raus = dict(raus)
        raus["wuerfe"] = [w for w in raus.get("wuerfe", []) if w != "c4"][:1]
        if not raus["wuerfe"]:
            raus["wuerfe"] = [rnd.choice(wuerfe)]
        return raus
    # Bots tragen weiter zwei aus ihren fuenf (auch nach 0.34.91, Haupt- und
    # Seitenwaffe gelten fuer die Saetze der Spieler): mit der Pistole als
    # zweiter Waffe hielten sie im Feuerschutz messbar schlechter nieder -
    # ihre KI ist auf zwei Hauptwaffen abgestimmt (tests/test_verhalten.py).
    waffen = bot_waffen_gewichten(rnd.sample(list(K.BOTS["waffen"]), 2), rnd)
    if vielfalt:
        waffen = bot_waffen_vielfalt(waffen, rnd)
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
        # Wo verschwundene Gegner zuletzt waren (seit 0.34.80): [Ort, Ebene,
        # bis wann]. Er prueft sie vorsichtig, bevor er sie vergisst.
        self.spuren = []
        self.reaktion_rest = 0.0
        self.fehler = pygame.Vector2(0, 0)
        self.fehler_zeit = 0.0        # so lange verfolgt er das Ziel schon
        self.blick = float(k.winkel)  # wohin sein Fadenkreuz zeigt
        self._drall = 0.0             # wie weit er sich zuletzt in eine Richtung drehte (Grad, klingt ab)
        self._kehrt = 0.0             # in einer Kehrtwende: in welche Richtung er sich dreht (+1, -1)
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
        self.streif_ort = None        # wohin er faehrt, wenn er niemanden sieht (0.34.71)
        # Gefahren (seit 0.34.70): Feuer, Gas, Fallen, Wuerfe.
        self._gefahren = []
        self._flaechen = []           # davon, was liegt: Feuer, Gas, Draht, Fallen (0.34.80)
        self.gefahr_rest = 0.0
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
        if getattr(k, "mitfahrt", None) is not None:
            # Hinten auf dem Panzerwagen (seit 0.34.96): der Fahrer setzt ab.
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
        if schwebt(k):
            # Fallschirmjaeger in der Luft (seit 0.34.100): er sieht schon, wer
            # unten steht (und merkt ihn sich), tut aber nichts, bis er landet.
            if self.ziel is not None:
                ein["ziel"] = [round(self.ziel.pos.x, 1), round(self.ziel.pos.y, 1)]
            return ein
        # Am Steuer (seit 0.34.71) - und wer fahren darf, aber keinen Wagen
        # hat, geht zum naechsten freien.
        if k.fahrzeug is not None:
            return self._am_steuer(dt, ein)
        if getattr(k, "darf_fahren", False):
            hin = self._zum_fahrzeug(ein)
            if hin is not None:
                return hin
        elif getattr(g, "schlacht", False):
            hin = self._aufsitzen_wollen(ein)
            if hin is not None:
                return hin

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

        springer = self._springer_reaktion(dt)
        if springer is not None:
            will, ziel_punkt, feuern, zielt = springer
        else:
            will, ziel_punkt, feuern, zielt = self._entscheiden(dt, ein)
            ziel_punkt, feuern = self._luft_abwehr(dt, ziel_punkt, feuern)
        feuern, zielt = self._abzug(feuern, zielt)
        # Seit 0.34.70: steht er in Feuer, Gas oder am Rand einer Falle,
        # geht er zuerst dort heraus - schiessen darf er dabei weiter.
        self.gefahr_rest -= dt
        if self.gefahr_rest <= 0.0:
            self.gefahr_rest = K.BOTS["gefahr_takt"]
            self._gefahren = self._gefahren_sammeln()
        raus = self._gefahr_raus()
        if raus is not None:
            will = raus

        will = self._sicher(will)
        will = self._nicht_stecken(dt, will)

        # Fadenkreuz: schwenkt, springt nicht.
        if ziel_punkt is None:
            ziel_punkt = self._blick_ohne_ziel(will)
        soll = _winkel_zu(k.pos, ziel_punkt)
        ab = _winkel_diff(self.blick, soll)
        z = self.ziel
        if abs(ab) > K.BOTS["kehrt_winkel"] and not (z is not None and self.ziel_ok(z)):
            # Fast eine halbe Drehung: zurueck, wie er gekommen ist (seit
            # 0.34.58). Bei einer halben Drehung ist die Richtung sonst Zufall,
            # und zwei Kehrtwenden hintereinander wurden eine ganze Drehung um
            # sich selbst. Die Richtung gilt, bis die Wende fast durch ist -
            # sonst pendelte er bei einem Ziel genau hinter ihm hin und her.
            # Auf einen Gegner schwenkt er weiter den kuerzesten Weg: dort
            # zaehlt jede Zehntelsekunde (gemessen beim Feuerschutz).
            if not self._kehrt:
                self._kehrt = (-math.copysign(1.0, self._drall) if abs(self._drall) > 1.0
                               else math.copysign(1.0, ab))
            if self._kehrt * ab < 0.0:
                ab += math.copysign(360.0, self._kehrt)
        else:
            self._kehrt = 0.0
        schritt = K.BOTS["dreh"] * dt
        dreh = max(-schritt, min(schritt, ab))
        if (dreh * self._drall > 0.0 and abs(self._drall) >= K.BOTS["drall_bremse"]
                and not (z is not None and self.ziel_ok(z))):
            # Drehbremse (seit 0.34.91): ohne Gegner im Blick nicht noch
            # weiter in dieselbe Richtung, wer sich eben schon fast ganz
            # herum gedreht hat. Beim Suchen lagen die Blickpunkte sonst
            # nacheinander je gut 120 Grad weiter - zusammen eine ganze
            # Drehung ohne Sinn (gesehen, als die Gefechte laenger dauerten).
            dreh = 0.0
        self.blick += dreh
        self._drall = self._drall * max(0.0, 1.0 - dt / K.BOTS["drall_zeit"]) + dreh
        weit = max(40.0, k.pos.distance_to(ziel_punkt))
        maus = k.pos + pygame.Vector2(1, 0).rotate(self.blick) * weit
        if feuern and k._waffe_lesen().get("art") == "schuss" and self.kamerad_im_weg(weit):
            feuern = False
        ein["ziel"] = [round(maus.x, 1), round(maus.y, 1)]
        if (feuern and k._waffe_lesen().get("art") == "schuss"
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

    def _luft_abwehr(self, dt: float, ziel_punkt, feuern):
        """Auf einen Tragschrauber oder eine Drohne schiessen (seit 0.34.138,
        gemeldet: "die Bots kriegen es nicht hin, Ziele in der Luft zu
        treffen"). Nur ohne Gegner am Boden im Blick, mit einer Schusswaffe,
        in Reichweite; erst nach der Reaktionszeit und in Stoessen. Getroffen
        wird ueber das Einrasten wie beim Menschen (luft.luft_zielen) - dort
        bekommt ein Bot seinen Zielfehler (K.BOTS luft_fehler)."""
        k, g = self.k, self.g
        if (feuern or (self.ziel is not None and self.ziel_ok(self.ziel))
                or k.ebene != 0 or not hasattr(g, "luft_ziele")
                or k._waffe_lesen().get("art") != "schuss"):
            self._luft_lz = None
            return ziel_punkt, feuern
        b = K.BOTS
        self._luft_such = getattr(self, "_luft_such", 0.0) - dt
        if self._luft_such <= 0.0:
            self._luft_such = b["luft_takt"]
            reich = min(b["reichweite"].get(k.waffe_name, 300.0), b["luft_weite"])
            beste, best_d = None, reich
            for lz in g.luft_ziele():
                if lz.nur_flak or not lz.lebt or not lz.fraktion or lz.fraktion == k.fraktion:
                    continue
                d = k.pos.distance_to(lz.bild_pos)
                if d < best_d:
                    beste, best_d = lz, d
            if beste is not getattr(self, "_luft_lz", None):
                self._luft_lz = beste
                self._luft_seit = 0.0
                self._luft_reaktion = self.rnd.uniform(*b["reaktion"]) + b["luft_reaktion"]
        lz = getattr(self, "_luft_lz", None)
        if lz is None or not lz.lebt:
            return ziel_punkt, feuern
        self._luft_seit = getattr(self, "_luft_seit", 0.0) + dt
        if self._luft_seit < getattr(self, "_luft_reaktion", 1.0):
            return pygame.Vector2(lz.bild_pos), False
        stoss, pause = b["luft_stoss"]
        im_stoss = ((self._luft_seit - self._luft_reaktion) % (stoss + pause)) < stoss
        return pygame.Vector2(lz.bild_pos), bool(im_stoss and k.magazin.get(k.waffe_name, 0) > 0)

    def _blick_ohne_ziel(self, will):
        """Wohin er schaut, wenn er nichts anvisiert: wohin er geht - aber
        erst, wenn er eine Weile in dieselbe Richtung geht -, sonst
        geradeaus weiter. Vorher folgte der Blick jedem Trippelschritt zur
        Stellung hin, und wer viermal in vier Richtungen trat, drehte sich
        dabei fast auf der Stelle einmal ganz um sich selbst (seit 0.34.55,
        gemeldet: "teils drehen sich bots in verschiedensten Situationen um
        360 grad")."""
        k = self.k
        # "Geradeaus" erst, wenn es gebraucht wird (seit 0.34.75) - dieselbe
        # Rechnung, nur nicht in jedem Schritt umsonst.
        if will.length_squared() <= 0.01:
            self._lauf_richtung = None
            return k.pos + pygame.Vector2(1, 0).rotate(self.blick) * 120
        jetzt = self.g.welt.zeit
        alt = getattr(self, "_lauf_richtung", None)
        if alt is None or abs(_winkel_diff(alt.as_polar()[1], will.as_polar()[1])) > K.BOTS["lauf_blick_winkel"]:
            self._lauf_richtung = pygame.Vector2(will)
            self._lauf_seit = jetzt
        if jetzt - getattr(self, "_lauf_seit", jetzt) < K.BOTS["lauf_blick_ruhe"]:
            return k.pos + pygame.Vector2(1, 0).rotate(self.blick) * 120
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
        # Ausgeschrieben statt setattr/getattr in einer Schleife (seit
        # 0.34.75): jeder Bot jeden Schritt, gemessen ein Zehntel seiner
        # Zeit. `v if v > 0.0 else 0.0` ist genau max(0.0, v).
        v = self.reaktion_rest - dt
        self.reaktion_rest = v if v > 0.0 else 0.0
        v = self.stoss_rest - dt
        self.stoss_rest = v if v > 0.0 else 0.0
        v = self.pause_rest - dt
        self.pause_rest = v if v > 0.0 else 0.0
        v = self.seite_rest - dt
        self.seite_rest = v if v > 0.0 else 0.0
        v = self.wurf_rest - dt
        self.wurf_rest = v if v > 0.0 else 0.0
        v = self.waffen_rest - dt
        self.waffen_rest = v if v > 0.0 else 0.0
        v = self.weg_rest - dt
        self.weg_rest = v if v > 0.0 else 0.0
        v = self.streif_rest - dt
        self.streif_rest = v if v > 0.0 else 0.0
        v = self.ausweich_rest - dt
        self.ausweich_rest = v if v > 0.0 else 0.0
        v = self.geblendet - dt
        self.geblendet = v if v > 0.0 else 0.0
        v = self.getroffen_rest - dt
        self.getroffen_rest = v if v > 0.0 else 0.0
        v = self.deckung_rest - dt
        self.deckung_rest = v if v > 0.0 else 0.0
        v = self.deckung_pause - dt
        self.deckung_pause = v if v > 0.0 else 0.0
        v = self.deckung_suche - dt
        self.deckung_suche = v if v > 0.0 else 0.0
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
        # Wer noch am Schirm haengt, ist auch kein Ziel (seit 0.34.100) - erst
        # wenn er gelandet ist.
        return (self.ist_feind(w) and w.ebene == self.k.ebene and not getattr(w, "am_boden", False)
                and not schwebt(w))

    def _kandidaten(self) -> list:
        """Wer fuer ihn ein Gegner sein kann (ist_feind), in derselben
        Reihenfolge wie immer.

        Seit 0.34.89 je Durchgang von _bots_steuern, Seite und Besetzung
        nur einmal gesucht: alles, was ist_feind ausser "lebt" fragt
        (Seite, raus, Puppe, unsichtbar, Nummer), aendert sich darin nicht.
        "Lebt" kann sich aendern (ein Schlag eines Bots vor ihm im selben
        Schritt) und wird darum bei jedem Aufruf neu gefragt."""
        g = self.g
        k = self.k
        welt = g.welt
        lauf = g.__dict__.get("_kandidaten_lauf")
        if lauf is None:
            # Ausserhalb von _bots_steuern wie immer, ohne Merken.
            return [w for w in self._roh_kandidaten() if w is not k and getattr(w, "lebt", False)]
        # Gemerkt nur innerhalb eines Durchgangs von _bots_steuern - und
        # wer da ist, ueber die Identitaet jedes Einzelnen.
        schluessel = (lauf, id(welt), tuple(map(id, g.kaempfer.values())),
                      tuple(map(id, welt.wesen)) if g.mit_gegnern else (), g.mit_gegnern)
        merk = g.__dict__.setdefault("_kandidaten_merk", {})
        hit = merk.get(k.fraktion)
        if hit is None or hit[0] != schluessel:
            hit = merk[k.fraktion] = (schluessel, self._roh_kandidaten())
        return [w for w in hit[1] if w is not k and getattr(w, "lebt", False)]

    def _roh_kandidaten(self) -> list:
        g = self.g
        roh = [w for w in g.kaempfer.values() if self._feind_fest(w)]
        if g.mit_gegnern:
            from .mehrspieler import KampfGegner
            roh += [w for w in g.welt.wesen
                    if isinstance(w, KampfGegner) and self._feind_fest(w)]
        return roh

    def _feind_fest(self, w) -> bool:
        """ist_feind ohne "lebt" und ohne "ist es er selbst" - was sich
        innerhalb eines Schritts nicht aendert."""
        k = self.k
        if getattr(w, "fraktion", "") == k.fraktion:
            return False
        if getattr(w, "raus", False) or getattr(w, "ist_puppe", False):
            return False
        if getattr(w, "ki_unsichtbar", False):
            return False
        return hasattr(w, "nummer") or getattr(w, "fraktion", "") == "feind"

    def sieht(self, w) -> bool:
        """Sieht er `w`? Ebene, Weite, Wand, Rauch - wie ein Mensch."""
        k = self.k
        if self.geblendet > 0.0:
            return False
        if w.ebene != k.ebene or getattr(w, "flug", 0.0) > 0:
            return False
        weite = K.BOTS["sicht"]
        if k.fahrzeug is not None:
            weite = K.BOTS["fahren"]["sicht"].get(k.fahrzeug.art, weite)
        if k.pos.distance_to(w.pos) > weite:
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
        melden = getattr(self.g, "lage_melden", None)
        for w in self._kandidaten():
            # Wer liegt, ist keine Gefahr mehr (bottaktik.kampffaehig): nicht
            # hinsehen spart je Liegendem eine Sichtlinie (seit 0.34.52).
            if getattr(w, "am_boden", False):
                continue
            if self.sieht(w):
                if schwebt(w):
                    # Ein Fallschirmjaeger im Anflug (seit 0.34.100): gesehen
                    # und gemerkt, aber noch kein Ziel - in Stellung gehen.
                    self.springer_gesehen = (pygame.Vector2(w.pos), jetzt)
                    self.gesehen[w] = (pygame.Vector2(w.pos), w.ebene, jetzt)
                    if melden is not None:
                        melden(k, w)
                    continue
                sichtbar.append(w)
                if melden is not None:
                    melden(k, w)
                self.gesehen[w] = (pygame.Vector2(w.pos), w.ebene, jetzt)
                if self.spuren:
                    self._spur_weg(w.pos, w.ebene, alle=False)
        # Vergessen, was zu lange her ist - und wer liegt. Wer nur aus dem
        # Blick ist, hinterlaesst eine Spur (seit 0.34.80): dort sieht er
        # vorsichtig nach, bevor er ihn ganz vergisst.
        for w in list(self.gesehen):
            if not w.lebt or getattr(w, "am_boden", False):
                del self.gesehen[w]
            elif jetzt - self.gesehen[w][2] > K.BOTS["gedaechtnis"]:
                ort, ebene, _z = self.gesehen.pop(w)
                self.spur_dazu(ort, ebene)
        # Wer am Boden liegt, ist kein Ziel mehr (seit 0.34.46, gemeldet:
        # "sie feuern immer sehr lange auf Gegner, die schon am Boden sind").
        # Seit 0.34.52 endet auch der Stoss, der lief: ein Dauerfeuer hielt
        # sonst vier Sekunden auf den Liegenden.
        liegt = self.ziel is not None and getattr(self.ziel, "am_boden", False)
        if liegt:
            self.stoss_rest = 0.0
        # Der Panzer nimmt zuerst gepanzerte Ziele (seit 0.34.96): sieht er
        # ein Fahrzeug, laesst er den Fussgaenger.
        panzer = getattr(k.fahrzeug, "art", "") == "panzer"
        blech_da = panzer and any(getattr(w, "im_fahrzeug", False) for w in sichtbar)
        if (self.ziel is not None and self.ziel in sichtbar and not liegt
                and not schwebt(self.ziel)
                and self._ziel_erlaubt(self.ziel)
                and not (blech_da and not getattr(self.ziel, "im_fahrzeug", False))):
            # Er bleibt dran - ausser ein anderer, den er sieht, hat ihn eben
            # getroffen (seit 0.34.38). Wer von der Seite beschossen wird,
            # dreht sich zu dem, der schiesst, statt stur auf den ersten zu
            # halten. Mitten im Feuerstoss nicht: den bringt er zu Ende.
            von = getattr(k, "zuletzt_von", None)
            von = getattr(von, "von", von)
            # Im Fahrzeug nicht (seit 0.34.84): jeder Wechsel heisst, den
            # Turm neu zu drehen - im Gefecht wechselte er so dauernd das
            # Ziel und kam kaum zum Schuss (gemeldet).
            if (von is not None and von is not self.ziel and von in sichtbar
                    and self.getroffen_rest > 1.6 and self.stoss_rest <= 0.0
                    and k.fahrzeug is None):
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
            fz = k.fahrzeug if getattr(k.fahrzeug, "rechteckig", False) else None

            def wert(w):
                d = k.pos.distance_to(w.pos)
                if fz is not None:
                    # Lieber einen, auf den der Turm schon fast zeigt.
                    d += abs(_winkel_diff(fz.aufbau, self._turm_soll(fz, w.pos))) \
                        * K.BOTS["fahren"]["dreh_kosten"]
                d -= self.schutz_bonus(w, schuetzlinge)[0]
                d -= self._ziel_bonus(w)
                if panzer and getattr(w, "im_fahrzeug", False):
                    d -= K.BOTS["fahren"]["panzer_blech_vorzug"]
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

    def _springer_reaktion(self, dt: float):
        """Gegner kommen am Schirm herunter (seit 0.34.100, gewuenscht: "Bots
        sollen die abspringenden Fallschirmjaeger wahrnehmen, aber nicht auf
        sie schiessen, bis sie gelandet sind, und erstmal in Position oder in
        Deckung gehen"). Ohne eigenes Ziel geht er in Deckung gegen die
        Landestelle - findet er keine, bleibt er stehen - und schaut hin.
        Gibt (will, Blickpunkt, feuern, zielt) zurueck oder None."""
        k = self.k
        z = self.ziel
        if (z is not None and self.ziel_ok(z)) or k.fahrzeug is not None:
            return None
        gesehen = getattr(self, "springer_gesehen", None)
        jetzt = self.g.welt.zeit
        if gesehen is None or jetzt - gesehen[1] > K.BOTS["springer_merken"]:
            self.springer_deckung = None
            return None
        ort = gesehen[0]
        suche = getattr(self, "springer_suche", 0.0) - dt
        self.springer_suche = suche
        if getattr(self, "springer_deckung", None) is None and suche <= 0.0:
            self.springer_suche = 1.0
            self.springer_deckung = self._deckung_suchen(ort) or pygame.Vector2(k.pos)
        hin = (getattr(self, "springer_deckung", None) or k.pos) - k.pos
        will = hin.normalize() if hin.length() > 4.0 else pygame.Vector2(0, 0)
        return will, pygame.Vector2(ort), False, False

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
            # Seit 0.34.70 alles, womit man kaempft (K.BOTS["kampf_arten"]):
            # Werfer, Raketen, Chor-Waffen, Flammenwerfer, Nahkampf.
            if d.get("art", "schuss") not in K.BOTS["kampf_arten"]:
                continue
            if d.get("art") == "nahkampf" and (not d.get("magazin") or d.get("aufheben")):
                raus.append((i, name))           # ein Schlag braucht keine Munition
                continue
            if d.get("kuehlt"):
                # Chor-Waffen (seit 0.34.130): solange sie ueberhitzt ist, nimmt
                # er eine andere - so wie ein Mensch.
                if name not in getattr(k, "ueberhitzt", {}) and k.magazin.get(name, 0) > 0:
                    raus.append((i, name))
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
        # Gegen ein Fahrzeug die Panzerabwehr, sonst die Einwegrakete
        # sparen (seit 0.34.95, Panzerjaeger).
        z = getattr(self, "ziel", None)
        gegen_blech = (z is not None and (getattr(z, "im_fahrzeug", False)
                                          or getattr(z, "ist_fahrzeug", False)))
        pa = K.BOTS["panzerabwehr"]

        def blech(name):
            d = K.WAFFEN[name]
            stark = d.get("fahrzeug_schaden") is not None or d.get("gegen_fahrzeug")
            if gegen_blech:
                return -pa["vorzug"] if stark else 0.0
            return pa["einweg_sparen"] if d.get("einweg") else 0.0
        return min(liste, key=lambda p: abs(wunsch.get(p[1], 220.0) - abstand)
                   - vorzug.get(p[1], 0.0) + blech(p[1])
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
        if k.ladung > 0.0 and k._waffe_lesen().get("art") == "strahl":
            # Wer die Spule laedt, zielt in Ruhe (seit 0.34.91): ein einzelner
            # Schuss, der alles entscheidet. Mit dem gewoehnlichen Wackeln
            # ging er an einer Figur meist vorbei (gemessen: 7 von 12 Laeufen).
            fehler *= b["spule_fehler"]
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
        wd = K.WAFFEN[k.waffe_name]
        if (k.magazin.get(k.waffe_name, 0) <= 0 and k.nachlade_rest <= 0
                and nr == k.waffe and wd.get("art", "schuss") in ("schuss", "werfer", "flamme",
                                                                  "kugel", "strahl", "kette")
                and wd.get("magazin") and not wd.get("aufheben")):
            ein["knoepfe"].append("nachladen")
        if wd.get("art") == "nahkampf" and nr == k.waffe:
            # Eine Nahkampfwaffe in der Hand (seit 0.34.70): hin und
            # zuschlagen - Abstand halten oder Deckung suchen hiesse hier,
            # nie zu treffen.
            will = self._weg_richtung(z.pos, z.ebene)
            nah = abstand <= wd.get("reichweite", 30.0) + getattr(z, "radius", 9.0)
            if nah:
                will = will * 0.3
            return (will, pygame.Vector2(z.pos), nah and sichtbar and self.reaktion_rest <= 0.0,
                    False)

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
        d = k._waffe_lesen()
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
        # Der Verdacht ist die frische Verfolgung - im normalen Tempo. Erst
        # was danach als Spur bleibt, prueft er vorsichtig (unten).
        gruppe = getattr(g, "front_an", False) and g.front_gruppe(k) is not None
        if ziel is None and self.verdacht is not None and self.verdacht[2] >= jetzt \
                and not (gruppe and k.pos.distance_to(self.verdacht[0]) > K.FRONT["verdacht_weite"]):
            # In einer Gruppe der Front (seit 0.34.133) geht er nur nahen
            # Geraeuschen nach - fernen Schuessen schaut er nur entgegen.
            ort, ebene, _bis = self.verdacht
            if k.ebene == ebene and k.pos.distance_to(ort) < 30:
                self.verdacht = None
                self._spur_weg(ort, ebene)
            else:
                ziel = (ort, ebene)
        if ziel is None:
            spur = self.spur_offen()
            # In einer Gruppe der Front (seit 0.34.131) prueft er nur Spuren
            # in der Naehe - sonst zoege jede Spur einen aus der Formation.
            if spur is not None and gruppe and k.pos.distance_to(spur[0]) > K.FRONT["kampf_weite"] * 0.6:
                spur = None
            if spur is not None:
                if self._spur_gesehen(spur):
                    self._spur_weg(spur[0], spur[1])
                    self.sagen_wenn_trupp("HIER IST KEINER MEHR.")
                else:
                    will = self._weg_richtung(spur[0], spur[1], ein) * self._vorsicht_tempo()
                    return will, pygame.Vector2(spur[0])
        if ziel is None and self.__dict__.get("_flucht_bis", 0.0) > jetzt:
            # Aus einem Wrack geflohen (seit 0.34.135): weg von ihm, zur eigenen Seite.
            basis = g.schlacht_basis(k.team) if hasattr(g, "schlacht_basis") else None
            if basis is not None and k.pos.distance_to(basis) > 200.0:
                return self._weg_richtung(basis, 0, ein), None
        if ziel is None and getattr(g, "front_an", False):
            # Die Front: mit seiner Gruppe auf ihrem Weg, in Formation.
            auftrag = g.front_auftrag(k)
            if auftrag is not None:
                ort, tempo, blick = auftrag
                if self.verdacht is not None and self.verdacht[2] >= jetzt:
                    blick = pygame.Vector2(self.verdacht[0])     # dorthin schauen, nicht gehen
                if tempo <= 0.0 or k.pos.distance_to(ort) < 8.0:
                    return pygame.Vector2(0, 0), blick
                return self._weg_richtung(ort, 0, ein) * tempo, blick
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

    # ── Spuren (seit 0.34.80) ─────────────────────────────────────
    # Gemeldet: "Bots vergessen Gegner sehr sehr schnell ... wenn die Bots
    # entscheiden, dass der Gegner weg ist, sollten sie wenigstens erst
    # vorsichtig seine letzten Spots pruefen." Eine Spur ist die letzte
    # Stelle eines Gegners, den er aus dem Blick verloren hat. Er geht
    # langsam hin, den Blick darauf, bis er sie sieht - dann ist sie fuer
    # ihn und die Kameraden in der Naehe erledigt.
    def _vorsicht_tempo(self) -> float:
        """Wie schnell er nachsehen geht: K.BOTS["spur_tempo"] fuer den
        ganz Vorsichtigen, schneller mit mehr Mut (Merkmal mut, GOAP), und
        ein Draufgaenger (ab K.BOTS["spur_draufgaenger"]) bremst gar nicht -
        er jagt dem Verschwundenen nach."""
        mut = max(0.0, min(1.0, float(getattr(self, "merkmale", {}).get("mut", 0.5))))
        if mut >= K.BOTS["spur_draufgaenger"]:
            return 1.0
        t = K.BOTS["spur_tempo"]
        return t + (1.0 - t) * mut

    def spur_dazu(self, ort, ebene) -> None:
        b = K.BOTS
        jetzt = self.g.welt.zeit
        for s in self.spuren:
            if s[1] == ebene and s[0].distance_to(ort) <= b["spur_zusammen"]:
                s[0] = pygame.Vector2(ort)
                s[2] = jetzt + b["spur_dauer"]
                return
        self.spuren.append([pygame.Vector2(ort), ebene, jetzt + b["spur_dauer"]])
        del self.spuren[:-b["spur_hoechstens"]]
        # Im Trupp entscheidet der Anfuehrer, wohin es geht: er bekommt die
        # Spur auch, sonst zoege er weiter auf Streife.
        t = getattr(self, "trupp", None)
        f = getattr(t, "fuehrer", None) if t is not None else None
        if f is not None and f is not self.k and f.lebt and getattr(f, "hirn", None) is not None:
            f.hirn.spur_dazu(ort, ebene)

    def spur_offen(self):
        """Die naechste offene Spur auf seiner Ebene, oder None. Nur, wenn
        gerade nichts anderes los ist: waehrend im Trupp einer geborgen
        wird oder er einen Gegner kennt, geht keiner Spuren nachsehen -
        sonst lief beim Bergen einer vom Feuerschutz weg."""
        jetzt = self.g.welt.zeit
        self.spuren = [s for s in self.spuren if s[2] >= jetzt]
        if not self.spuren:
            return None
        t = getattr(self, "trupp", None)
        if t is not None and getattr(t, "bergung", None) is not None:
            return None
        # Solange er einen Gegner noch kennt (gesehen, innerhalb des
        # Gedaechtnisses), kaempft er - Spuren sind fuer danach.
        if self.ziel is not None or self.gesehen:
            return None
        k = self.k
        hier = [s for s in self.spuren if s[1] == k.ebene]
        if not hier:
            return None
        return min(hier, key=lambda s: k.pos.distance_squared_to(s[0]))

    def _spur_gesehen(self, spur) -> bool:
        k = self.k
        b = K.BOTS
        d = k.pos.distance_to(spur[0])
        if d <= b["spur_nah"]:
            return True
        return (d <= b["spur_blick"] and self.geblendet <= 0.0
                and self.g.welt.sicht_frei(k.pos, spur[0], k.ebene))

    def _spur_weg(self, ort, ebene, alle: bool = True) -> None:
        """Die Spur bei `ort` ist erledigt - bei ihm und (alle) bei den
        Kameraden, die dieselbe Stelle pruefen wollten."""
        weit = K.BOTS["spur_zusammen"]
        hirne = [self]
        if alle:
            hirne += [x.hirn for x in self.kameraden() if getattr(x, "hirn", None) is not None]
        for h in hirne:
            spuren = getattr(h, "spuren", None)
            if spuren:
                h.spuren = [s for s in spuren
                            if s[1] != ebene or s[0].distance_to(ort) > weit]

    def sagen_wenn_trupp(self, text: str) -> None:
        """Ein Funkspruch, wenn er das kann (GOAP im Trupp); sonst nichts."""
        sagen = getattr(self, "sagen", None)
        if sagen is not None and getattr(self, "trupp", None) is not None:
            sagen(text)

    def _streifziel(self):
        """Irgendwohin, wo Gegner sein koennten: die Kreise und Spawnstellen
        der Karte (kennt jeder), die Seite der anderen Mannschaft (auch),
        oder einfach eine freie Stelle."""
        g = self.g
        k = self.k
        # SCHLACHT (seit 0.34.95): zur Mitte, dann zur Basis der anderen.
        vorstoss = getattr(g, "vorstoss_ziel", None)
        if vorstoss is not None:
            ziel = vorstoss(k, self.rnd)
            if ziel is not None:
                return ziel
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
        if getattr(self, "_flaechen", None) and k.ebene == ebene:
            return self._um_gefahr(d.normalize(), ort)
        return d.normalize()

    def _um_gefahr(self, richtung, ort):
        """Liegt eine Gefahr (Brandflaeche, Gas ...) vor ihm auf dem Weg:
        aussen herum (seit 0.34.80). Gemeldet: "Bots laufen noch oefters in
        Molotovs rein, also kurz und dann wieder rueckwaerts raus." Bis
        dahin merkte er das Feuer erst 26 Pixel vorher, drehte ab, und der
        Weg zog ihn gleich wieder hinein. Jetzt schaut er weiter voraus und
        bleibt eine Weile bei der Seite, die er gewaehlt hat. Ist auf
        keiner Seite Platz, wartet er davor; liegt das Ziel selbst darin,
        bleibt er am Rand stehen."""
        k = self.k
        b = K.BOTS
        if self._gefahr_bei(k.pos):
            return richtung              # schon drin: _gefahr_raus fuehrt hinaus
        jetzt = self.g.welt.zeit
        weite = min(b["gefahr_umweg_vor"], k.pos.distance_to(ort))
        erste = None
        for mitte, r in self._flaechen:
            rel = mitte - k.pos
            t = rel.dot(richtung)
            if t < 0.0 or t > weite + r:
                continue
            quer = abs(rel.x * richtung.y - rel.y * richtung.x)
            if quer >= r + k.radius:
                continue
            if erste is None or t < erste[2]:
                erste = (mitte, r, t)
        if erste is None:
            return richtung
        mitte, r, _t = erste
        if mitte.distance_to(ort) <= r:
            # Das Ziel liegt im Feuer: davor warten.
            return pygame.Vector2(0, 0) if k.pos.distance_to(mitte) <= r + k.radius + 14.0 \
                else richtung
        n = richtung.rotate(90)
        alt = getattr(self, "_umweg", None)
        if alt is None or alt[0].distance_to(mitte) > 30.0 or alt[2] < jetzt:
            welt = self.g.welt
            zuerst = -1 if (mitte - k.pos).dot(n) > 0 else 1
            seite, weit = 0, 0.0
            # Erst eng am Rand vorbei, dann weiter aussen - in einem Gang ist
            # oft nur dicht am Feuer Platz.
            for s in (zuerst, -zuerst):
                for extra in (2.0, 8.0, 14.0):
                    p = mitte + n * s * (r + k.radius + extra)
                    if welt.frei(p, k.radius, k.ebene, True) and not self._gefahr_bei(p):
                        seite, weit = s, r + k.radius + extra
                        break
                if seite:
                    break
            self._umweg = (pygame.Vector2(mitte), seite, jetzt + b["gefahr_umweg_seite"], weit)
        seite = self._umweg[1]
        if seite == 0:
            # Kein Platz daneben: wie bisher, Schritt fuer Schritt (_sicher).
            return richtung
        p = mitte + n * seite * self._umweg[3]
        hin = p - k.pos
        if hin.length_squared() < 16.0:
            return richtung
        return hin.normalize()

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

    # ---- Fahren (seit 0.34.71) ------------------------------------------
    def _zum_fahrzeug(self, ein: dict):
        """Ein Fahrer ohne Fahrzeug: zum naechsten freien und einsteigen.

        Seit 0.34.84 auch, wenn er einen Gegner sieht - solange der Wagen
        nah ist und der Gegner nicht dicht vor ihm steht (gemeldet: "Bots
        gehen oft nicht in Fahrzeuge"). Und er geht an die **Seite**: beim
        Panzerwagen reicht die Front weiter, als man zum Einsteigen an die
        Mitte heran muss - wer vorn oder hinten stand, kam nie hinein und
        blieb dort stehen."""
        k = self.k
        f = K.BOTS["fahren"]
        if self.g.welt.zeit < getattr(self, "_fz_pause_bis", -1.0):
            return None                 # eben aus einem Buggy gestiegen, um zu kaempfen
        bester, weite, wert = None, f["suchen"], 1e18
        for b in getattr(self.g, "fahrzeuge", ()):
            if b.fahrer is not None or b.kaputt or b.nur_bild or b.ebene != k.ebene:
                continue
            if b.werte.get("nur_mensch"):
                continue                # (seit 0.34.131 keiner mehr)
            if self.g.welt.zeit - getattr(b, "_abgestellt", -999.0) < 60.0:
                continue                # ein abgestellter Trosswagen ist Nachschub, kein Taxi
            if b.leben < b.max_leben * f["wrack_meiden"] or "_aufgegeben" in b.__dict__:
                continue                # kurz vor dem Hochgehen oder schon aufgegeben (seit 0.34.135)
            d = b.pos.distance_to(k.pos)
            # Das wertvollere Fahrzeug zuerst (seit 0.34.131): sonst stieg jeder
            # in den naechsten Buggy, und Werfer und Tragschrauber blieben stehen.
            w = d - FAHRZEUG_VORZUG.get(b.art, 0.0)
            if d < f["suchen"] and w < wert:
                bester, weite, wert = b, d, w
        if bester is None:
            return None
        if self.ziel is not None and self.ziel_ok(self.ziel):
            if (weite > f["einstieg_trotz_feind"]
                    or k.pos.distance_to(self.ziel.pos) < f["einstieg_feind_nah"]):
                return None
        if weite <= bester.werte["einsteigen"] - 3.0:
            ein["knoepfe"].append("nutzen")
            return ein
        will = self._sicher(self._weg_richtung(self._einstiegspunkt(bester), bester.ebene, ein))
        ein["will"] = [round(will.x, 2), round(will.y, 2)]
        ein["ziel"] = [round(bester.pos.x, 1), round(bester.pos.y, 1)]
        return ein

    def _aufsitzen_wollen(self, ein: dict):
        """SCHLACHT (seit 0.34.96): wer nichts zu tun hat und neben einem
        Panzerwagen der eigenen Seite steht, den ein Bot faehrt und der noch
        weit fahren will, sitzt auf - der Fahrer setzt ihn vor dem Kampf ab."""
        k = self.k
        g = self.g
        if self.ziel is not None and self.ziel_ok(self.ziel):
            return None
        s = K.SCHLACHT
        for b in getattr(g, "fahrzeuge", ()):
            if (b.art != "panzerwagen" or b.fahrer is None or b.kaputt or b.ebene != k.ebene
                    or not getattr(b.fahrer, "ist_bot", False)
                    or b.fahrer.team != k.team
                    or len(b.mitfahrer) >= b.werte["plaetze"]
                    or getattr(b, "abgesetzt", False)):
                continue
            weit = b.pos.distance_to(k.pos)
            if weit > s["aufsitzen_weite"]:
                continue
            h = b.fahrer.hirn
            if h is None or (h.ziel is not None and h.ziel_ok(h.ziel)):
                continue
            if weit <= b.werte["einsteigen"] - 4.0:
                if k.treppe_rest <= 0.0:
                    ein["knoepfe"].append("nutzen")
                return ein
            will = self._sicher(self._weg_richtung(self._einstiegspunkt(b), b.ebene, ein))
            ein["will"] = [round(will.x, 2), round(will.y, 2)]
            ein["ziel"] = [round(b.pos.x, 1), round(b.pos.y, 1)]
            return ein
        return None

    def _absetzen_pruefen(self, b, z) -> None:
        """Am Steuer mit Leuten hinten drauf: vor einem Kampf absetzen - wenn
        er Gegner sieht oder ein gemeldeter Kampf nahe ist -, danach langsam
        mit ihnen vorruecken (K.SCHLACHT)."""
        liste = b.__dict__.get("_mitfahrer")
        if not liste:
            return
        s = K.SCHLACHT
        nah = z is not None and z.pos.distance_to(b.pos) < s["absetzen_vor"] * 1.6
        lage = getattr(self.g, "lage_nahe", None)
        if not nah and lage is not None:
            nah = lage(self.k.team, b.pos, s["absetzen_vor"]) is not None
        punkte = getattr(self.g, "_schlacht_punkte", None)
        if not nah and punkte is not None:
            # Vor der Mitte und vor der Basis der anderen: dort wird gekaempft.
            basis_l, basis_r, mitte = punkte()
            feind = basis_r if self.k.team == 0 else basis_l
            nah = (b.pos.distance_to(mitte) < s["mitte_nah"] + s["absetzen_vor"]
                   or b.pos.distance_to(feind) < s["absetzen_vor"] * 1.5)
        if nah:
            self.funken("absetzen", wichtig=True)
            self.g.alle_absetzen(b)
            b.abgesetzt = True

    def _einstiegspunkt(self, b):
        """Wohin er zum Einsteigen geht: neben die Wanne, auf die Seite, die
        ihm naeher ist - beim Buggy reicht die Mitte."""
        if not getattr(b, "rechteckig", False):
            return pygame.Vector2(b.pos)
        k = self.k
        quer = pygame.Vector2(-b.vorn.y, b.vorn.x)
        seite = 1.0 if (k.pos - b.pos).dot(quer) >= 0 else -1.0
        weit = min(b.werte.get("halb", 16.0) + k.radius + K.BOTS["fahren"]["einstieg_seite"],
                   b.werte["einsteigen"] - 6.0)
        return b.pos + quer * seite * weit

    def _lenken(self, b, hin, halten: bool = False, weit=None):
        """(Gas, Lenkung) zu einem Punkt (seit 0.34.84). Der Stick
        (stick_steuern) faehrt rueckwaerts, sobald das Ziel hinter dem Wagen
        liegt - fuer einen Menschen mit Daumen auf dem Stick richtig, fuer
        einen Bot hiess es, lange Strecken rueckwaerts zu fahren (gemeldet).
        Hier: weit weg und hinten - vorwaerts wenden; der Panzer dreht auf
        der Stelle, wenn er sehr schief steht. `halten`: nicht fahren, nur
        die Wanne dorthin drehen (Bug-MG)."""
        f = K.BOTS["fahren"]
        weg = pygame.Vector2(hin) - b.pos
        dist = weg.length()
        if dist < 4.0:
            return 0.0, 0.0
        # Wie weit es bis zum eigentlichen Ziel ist, nicht bis zum naechsten
        # Wegpunkt - der liegt immer nah, und dann galt jede Strecke als kurz.
        gesamt = dist if weit is None else max(dist, weit)
        if dist < f["nah_rueckwaerts"] and getattr(self, "_fahr_versuch", None) is not None:
            # Ein naher Wegpunkt hinter ihm, nachdem er schon feststeckte
            # (seit 0.34.96): rueckwaerts hin statt vorwaerts zu wenden -
            # beim Wenden drehte sich ein Panzerwagen in einer Sackgasse fest.
            gesamt = dist
        soll = math.degrees(math.atan2(weg.y, weg.x))
        gas_mal = 1.0
        if not halten and dist > f["ausweichen_ab"]:
            # Vorausschauend ausweichen (seit 0.34.139, gewuenscht: "Bots sollen
            # nirgendwo gegenfahren") - um Mauern, leere Wagen, Wracks und die
            # eigenen Leute, nicht erst, wenn er feststeckt.
            soll, gas_mal = self._frei_richtung(b, soll)
        elif not halten:
            self._an_der_wand(b, soll)
        ab = _winkel_diff(b.winkel, soll)
        voll = b.werte.get("stick_voll_lenken", 40.0)
        lenk = max(-1.0, min(1.0, ab / voll))
        if halten:
            return 0.0, (lenk if abs(ab) > 3.0 else 0.0)
        jetzt = self.g.welt.zeit
        rueck_bis = b.__dict__.get("_rueck_bis", -1.0)
        rueck_ab = b.__dict__.get("_rueck_ab")
        if (rueck_ab is not None and rueck_bis <= jetzt < rueck_bis + 0.05
                and jetzt - rueck_ab < f["wand_rueck_max"]
                and not self._spur_frei(b, b.winkel, f["ausweichen_nah"] * 1.5)):
            # An der Wand noch kein Platz vor der Nase (schwere Wagen kommen im
            # Rueckwaertsgang langsam in Fahrt): laenger zurueck.
            b._rueck_bis = rueck_bis = jetzt + 0.04
        if jetzt < rueck_bis:
            # Direkt vor der Nase steht etwas: kurz zurueck und die Nase dabei
            # zur freien Richtung drehen (rueckwaerts lenkt es andersherum).
            return -f["ausweichen_rueck_gas"], (-1.0 if ab > 0 else 1.0) if abs(ab) > 5.0 else 0.0
        if gas_mal < 1.0 and abs(ab) < b.werte.get("stick_wenden", 110.0):
            return gas_mal, lenk
        if b.art == "panzer":
            if abs(ab) > f["panzer_drehen_ab"]:
                # Drehen und dabei langsam rollen: in einer engen Ecke haengt
                # eine Wanne, die nur auf der Stelle dreht, an der Wand.
                return f["panzer_drehen_gas"], (1.0 if ab > 0 else -1.0)
            return 1.0, lenk
        if abs(ab) >= b.werte.get("stick_zurueck", 150.0) and gesamt <= f["wenden_ab"]:
            return b.stick_steuern(weg.normalize())   # kurz: rueckwaerts ist richtig
        if abs(ab) >= b.werte.get("stick_wenden", 110.0):
            return 0.7, (1.0 if ab > 0 else -1.0)      # wenden, vorwaerts
        return 1.0, lenk

    def _kolonne(self, b, soll: float, weite: float, laenge: float):
        """Faehrt ein besetzter Wagen vor ihm auf seiner Spur? ("folgen",
        Gasanteil): in gleicher Richtung - dahinter bleiben, mit Abstand; steht
        der Vordermann, warten, aber hoechstens `kolonne_warten` s, dann wird
        er umfahren. ("rechts", Grad): er kommt entgegen - beide halten sich
        rechts. None: niemand."""
        f = K.BOTS["fahren"]
        richtung = pygame.Vector2(1, 0).rotate(soll)
        quer = pygame.Vector2(-richtung.y, richtung.x)
        halb = float(b.werte.get("halb", b.werte.get("kreis", 16.0)))
        bester = None
        for o in getattr(self.g, "fahrzeuge", ()):
            if (o is b or o.fahrer is None or o.kaputt or o.ebene != b.ebene
                    or getattr(o, "in_der_luft", False) or getattr(o, "nur_bild", False)):
                continue
            rel = o.pos - b.pos
            vor = rel.dot(richtung)
            o_halb = float(o.werte.get("halb", o.werte.get("kreis", 16.0)))
            o_laenge = float(o.werte.get("vorn", o.werte.get("achse", 0.0) + o.werte.get("kreis", 16.0)))
            if not (0.0 < vor < weite + o_laenge + f["kolonne_abstand"]):
                continue
            if abs(rel.dot(quer)) > halb + o_halb + f["kolonne_seite"]:
                continue
            if bester is None or vor < bester[0]:
                bester = (vor, o, o_laenge)
        if bester is None:
            b.__dict__.pop("_kolonne_seit", None)
            return None
        vor, o, o_laenge = bester
        b._kolonne_info = ("folgen", o, self.g.welt.zeit)     # fuer die INFO-Ansicht (Testmodus)
        # Nach der Nase des anderen, nicht nach seinem Tempo: zwei, die Nase an
        # Nase stehen, hielten sonst einander fuer den Vordermann und warteten.
        gleich = o.vorn.dot(richtung)
        if gleich < -f["kolonne_gleich"] or o.geschw.dot(richtung) < -f["kolonne_gegen"]:
            b._kolonne_info = ("rechts", o, self.g.welt.zeit)
            return ("rechts", f["kolonne_rechts"])
        if gleich < f["kolonne_gleich"]:
            b.__dict__.pop("_kolonne_info", None)
            return None                     # er faehrt quer: ausweichen wie sonst
        jetzt = self.g.welt.zeit
        if o.geschw.length() < f["kolonne_steht"]:
            # Ein geparkter Wagen (kein Gas, wartet selbst in keiner Kolonne):
            # kein Vordermann, sondern ein Hindernis - gleich vorbei.
            seine = o.__dict__.get("_kolonne_info")
            wartet = seine is not None and seine[0] == "folgen" and jetzt - seine[2] < 0.5
            if abs(getattr(o, "gas", 0.0)) < 0.05 and not wartet:
                b.__dict__.pop("_kolonne_info", None)
                return None
            seit = b.__dict__.setdefault("_kolonne_seit", jetzt)
            if jetzt - seit > f["kolonne_warten"]:
                b.__dict__.pop("_kolonne_info", None)
                return None                 # er kommt nicht weiter: vorbei
        else:
            b.__dict__.pop("_kolonne_seit", None)
        # `laenge` und `o_laenge` reichen schon von der Mitte bis zur Nase.
        o_hinten = abs(float(o.werte.get("hinten", -o_laenge)))
        luecke = vor - laenge - o_hinten
        # Wer schneller ist als der Vordermann, braucht mehr Abstand - und
        # bremst (Gas los hiess nur rollen, und der Buggy fuhr auf).
        eigen = b.geschw.dot(richtung)
        schliesst = max(0.0, eigen - o.geschw.dot(richtung))
        noetig = f["kolonne_abstand"] + schliesst * f["kolonne_bremsweg"]
        if luecke < noetig:
            return ("folgen", -1.0 if eigen > f["kolonne_steht"] else 0.0)
        return ("folgen", max(0.0, min(1.0, (luecke - noetig) / f["kolonne_auflauf"])))

    def _spur_frei(self, b, winkel: float, weite: float) -> bool:
        """Kann der Wagen in Richtung `winkel` die naechsten `weite` px fahren,
        ohne an etwas zu stossen (Mauer, Wagen, Wrack, eigene Leute)?"""
        vorn = pygame.Vector2(1, 0).rotate(winkel)
        kreis = float(b.werte.get("halb", b.werte.get("kreis", 16.0)))
        eigen = [k for k in self.g.kaempfer.values()
                 if k is not self.k and k.lebt and k.team == self.k.team and k.fahrzeug is None
                 and getattr(k, "mitfahrt", None) is None and k.ebene == b.ebene
                 and k.pos.distance_squared_to(b.pos) < (weite + 80.0) ** 2]
        for anteil in (0.35, 0.7, 1.0):
            q = b.pos + vorn * (weite * anteil)
            if not b.passt(q, winkel):
                return False
            for k in eigen:
                if k.pos.distance_squared_to(q) < (kreis + k.radius + 6.0) ** 2:
                    return False
        return True

    def _frei_richtung(self, b, soll: float):
        """(Richtung, Gasanteil): `soll`, wenn die Spur frei ist; sonst die
        naechste freie Richtung daneben (zuerst zur Seite, zu der er ohnehin
        dreht); ist keine frei, langsam weiter - das Feststecken (_am_steuer)
        setzt dann wie bisher zurueck. Gemerkt je Wagen fuer `ausweichen_takt` s."""
        f = K.BOTS["fahren"]
        jetzt = self.g.welt.zeit
        merk = b.__dict__.get("_ausweich")
        if merk is not None and jetzt - merk[0] < f["ausweichen_takt"] and abs(_winkel_diff(merk[1], soll)) < 25.0:
            return (soll + merk[2]) % 360.0, merk[3]
        tempo = abs(getattr(b, "fahrt", 0.0)) if hasattr(b, "fahrt") else b.geschw.length()
        weite = max(f["ausweichen_min"], min(f["ausweichen_max"], tempo * f["ausweichen_zeit"]))
        laenge = float(b.werte.get("vorn", b.werte.get("achse", 0.0) + b.werte.get("kreis", 16.0)))
        weite += laenge * 0.5
        versatz, gas = 0.0, 1.0
        kolonne = self._kolonne(b, soll, weite, laenge)
        if kolonne is not None and kolonne[0] == "folgen":
            # Hinter einem eigenen Wagen anstellen statt vorbeidraengeln (seit
            # 0.34.140, gemeldet mit Bild: fuenf Wagen verkeilt an einer
            # Engstelle). Der Vordermann faehrt den Weg, den man selbst will.
            b._ausweich = (jetzt, soll, 0.0, kolonne[1])
            return soll % 360.0, kolonne[1]
        if kolonne is not None:
            versatz = kolonne[1]           # Gegenverkehr: rechts halten
        if not self._spur_frei(b, (soll + versatz) % 360.0, weite):
            versatz = 0.0
            # Die Seite von eben behalten - sonst pendelt er zwischen links und rechts.
            alt = b.__dict__.get("_ausweich_seite")
            if alt is not None and jetzt - alt[1] < f["ausweichen_seite_halten"]:
                zuerst = alt[0]
            else:
                zuerst = 1.0 if _winkel_diff(b.winkel, soll) >= 0 else -1.0
            gefunden = False
            for w in f["ausweichen_winkel"]:
                for seite in (zuerst, -zuerst):
                    if self._spur_frei(b, soll + seite * w, weite * 0.8):
                        versatz, gefunden = seite * w, True
                        b._ausweich_seite = (seite, jetzt)
                        break
                if gefunden:
                    break
            if not gefunden:
                gas = f["ausweichen_gas"]
            # Steht direkt vor der Nase etwas und geht es auch in die neue
            # Richtung nicht gleich weiter, hilft kein Lenken mehr: kurz zurueck.
            if (jetzt >= b.__dict__.get("_rueck_bis", -1.0) and tempo < f["ausweichen_rueck_tempo"]
                    and not self._spur_frei(b, b.winkel, f["ausweichen_nah"])
                    and not self._spur_frei(b, soll + versatz, f["ausweichen_nah"])):
                b._rueck_bis = jetzt + f["ausweichen_rueck_zeit"]
                b._rueck_ab = None
        b._ausweich = (jetzt, soll, versatz, gas)
        return (soll + versatz) % 360.0, gas

    def _an_der_wand(self, b, soll: float) -> None:
        """Der naechste Wegpunkt liegt dicht neben ihm, quer zur Nase, und die
        Nase steht an einer Wand: vorwaerts mit vollem Einschlag kommt ein
        Wagen mit Raedern nicht hin (gesehen beim Flakwagen: 10 s auf der
        Stelle). Steht er so eine Weile, ohne sich zu drehen, setzt er zurueck,
        bis vor der Nase Platz ist."""
        f = K.BOTS["fahren"]
        jetzt = self.g.welt.zeit
        tempo = abs(getattr(b, "fahrt", 0.0)) if hasattr(b, "fahrt") else b.geschw.length()
        if (jetzt < b.__dict__.get("_rueck_bis", -1.0) or tempo >= f["wand_tempo"]
                or abs(_winkel_diff(b.winkel, soll)) <= f["wand_rueck_winkel"]
                or self._spur_frei(b, b.winkel, f["ausweichen_nah"])):
            b._wand_seit = None
            return
        seit = b.__dict__.get("_wand_seit")
        if seit is None or abs(_winkel_diff(seit[1], b.winkel)) > f["wand_drehung"]:
            b._wand_seit = (jetzt, b.winkel)
        elif jetzt - seit[0] >= f["wand_zeit"]:
            b._rueck_bis = jetzt + f["ausweichen_rueck_zeit"]
            b._rueck_ab = jetzt
            b._wand_seit = None

    def _schutz_ort(self, b):
        """Ein Kamerad liegt, und ein Gegner ist bekannt: der Platz zwischen
        beiden (seit 0.34.84, nicht im Buggy) - dort deckt der Wagen ihn,
        bis ihm einer aufhilft. None, wenn es nichts zu decken gibt oder es
        zu weit oder zu gefaehrlich ist."""
        f = K.BOTS["fahren"]
        k = self.k
        if b.art in ("buggy", "krad") or b.leben < b.max_leben * f["schutz_leben"]:
            return None
        feind = self.ziel if self.ziel is not None and self.ziel_ok(self.ziel) else None
        if feind is None:
            alt = self.letzter_feind()
            feind_pos = alt[0] if alt is not None else None
            if feind_pos is None:
                # Aus dem Blick, aber nicht vergessen: seine Spur (0.34.80).
                jetzt = self.g.welt.zeit
                spuren = [s_ for s_ in self.spuren if s_[1] == b.ebene and s_[2] >= jetzt]
                if spuren:
                    feind_pos = pygame.Vector2(min(spuren, key=lambda s_: s_[0].distance_to(b.pos))[0])
        else:
            feind_pos = pygame.Vector2(feind.pos)
        if feind_pos is None:
            return None
        welt = self.g.welt
        bester = None
        for x in self.kameraden():
            if not getattr(x, "am_boden", False) or x.ebene != b.ebene:
                continue
            d = x.pos.distance_to(b.pos)
            if d > f["schutz_weite"]:
                continue
            hin = feind_pos - x.pos
            if hin.length_squared() < 1.0:
                continue
            hin = hin.normalize()
            ort = None
            # Erst genau davor, sonst etwas weiter oder leicht versetzt - steht
            # dort eine Kiste, deckt ihn der Wagen daneben fast genauso.
            for vor in (f["schutz_vor"], f["schutz_vor"] * 1.4, f["schutz_vor"] * 0.8):
                for dreh in (0.0, 20.0, -20.0):
                    p = x.pos + hin.rotate(dreh) * vor
                    # "Wenn das ohne grosse Probleme geht" (gemeldet): nur
                    # dorthin, wo der Wagen geradewegs hinkommt - um eine
                    # Mauer herum ist er zu spaet und steht nur im Weg.
                    # Nicht jeder Wagen hat "halb" (Spulenwagen, seit 0.34.131 mit Bot).
                    halb = b.werte.get("halb", b.werte.get("kreis", 16.0))
                    if (welt.frei(p, halb, b.ebene, True)
                            and welt.wege.gerade_frei(b.ebene, b.pos, p, halb * 0.8)):
                        ort = p
                        break
                if ort is not None:
                    break
            if ort is None:
                continue
            if bester is None or d < bester[0]:
                bester = (d, ort, x)
        return None if bester is None else bester[1:]

    def _turm_soll(self, b, ort) -> float:
        mitte = b.aufbau_mitte()
        weg = pygame.Vector2(ort) - mitte
        return math.degrees(math.atan2(weg.y, weg.x))

    def _am_steuer(self, dt: float, ein: dict) -> dict:
        """Fahren und schiessen im Fahrzeug (seit 0.34.71, seit 0.34.84 neu
        gelenkt, siehe _lenken). Turm bzw. Ring folgen dem Zeiger."""
        k = self.k
        b = k.fahrzeug
        f = K.BOTS["fahren"]
        ein["rl"] = True
        if b.kaputt:
            ein["knoepfe"].append("nutzen")
            return ein
        if b.leben < b.max_leben * f["raus_unter"]:
            # Kurz vor dem Hochgehen (seit 0.34.135, gemeldet: Bots stiegen aus
            # und sofort wieder ein, immer weiter): er entscheidet sich einmal -
            # drinbleiben bis zum Schluss, raus und weglaufen, oder raus und in
            # Stellung. Den Wagen nimmt danach kein Bot mehr (_zum_fahrzeug).
            wahl = self.__dict__.get("_wrack_wahl")
            if wahl is None or wahl[0] is not b:
                t = self.rnd.random()
                art = "bleiben" if t < f["wrack_bleiben"] else (
                    "fliehen" if t < f["wrack_bleiben"] + f["wrack_fliehen"] else "stellung")
                self._wrack_wahl = wahl = (b, art)
            if wahl[1] != "bleiben":
                b._aufgegeben = self.g.welt.zeit
                ein["knoepfe"].append("nutzen")          # raus, bevor er hochgeht
                if wahl[1] == "fliehen":
                    self._flucht_bis = self.g.welt.zeit + f["wrack_flucht_zeit"]
                return ein
        z = self.ziel if self.ziel is not None and self.ziel_ok(self.ziel) else None
        # Funk aus dem Fahrzeug (seit 0.34.96): wenn etwas passiert - ein
        # neuer Gegner, ein Treffer am Blech. Nur dann funkt das Geraet.
        if z is not None and z is not getattr(self, "_fz_gemeldet", None):
            self._fz_gemeldet = z
            self.funken("fahrzeug_kontakt")
        leben_alt = getattr(self, "_fz_leben", b.leben)
        if b.leben < leben_alt - 1.0:
            self.funken("fahrzeug_getroffen")
        self._fz_leben = b.leben
        # Ein Gegner, der eben noch zu sehen war: fuer die Kanone (explosiv)
        # und um den Turm schon dorthin zu drehen.
        verdeckt = None
        if z is None and getattr(b, "rechteckig", False):
            jetzt = self.g.welt.zeit
            frisch = [(ort, w) for w, (ort, ebene, zeit) in self.gesehen.items()
                      if ebene == b.ebene and jetzt - zeit <= f["verdeckt_merken"]
                      and kampffaehig(w)]
            if frisch:
                verdeckt = min(frisch, key=lambda o: o[0].distance_to(b.pos))[0]
        if getattr(self.g, "schlacht", False):
            self._absetzen_pruefen(b, z)
        if b.art == "tragschrauber":
            # Fliegen (seit 0.34.131): eigene Steuerung, siehe _schrauber_steuern.
            return self._schrauber_steuern(b, ein, dt)
        # Nachschub, Funk und Werfer jagen keinen (seit 0.34.131): sie fahren
        # in ihre Stellung hinter der Front und tun dort ihre Arbeit.
        stellung = b.art in ("trosswagen", "funkwagen", "werfer")
        ziel_ort = (pygame.Vector2(z.pos) if z is not None
                    else (pygame.Vector2(verdeckt) if verdeckt is not None else None))
        if stellung:
            ziel_ort = None
        unbewaffnet = not (getattr(b, "rechteckig", False) or getattr(b, "schiesst", False)
                           or getattr(b, "flak", False) or b.art == "tragschrauber")
        if unbewaffnet and not stellung:
            # Seit 0.34.138 (gemeldet: "Bots in Buggies versuchen die ganze Zeit
            # einen anzufahren und umkreisen einen, obwohl sie keinen Schaden
            # machen"): wer nicht schiessen kann, jagt keinen. Ist ein Gegner
            # nah, steigt er aus und kaempft zu Fuss - und sucht eine Weile
            # keinen Wagen (bots._zum_fahrzeug).
            if z is not None and b.pos.distance_to(z.pos) <= f["unbewaffnet_aussteigen"]:
                self._fz_pause_bis = self.g.welt.zeit + f["unbewaffnet_pause"]
                ein["knoepfe"].append("nutzen")
                return ein
            ziel_ort = None
        gas, lenk = 0.0, 0.0
        will = pygame.Vector2(0, 0)
        schutz = None if stellung else self._schutz_ort(b)
        if getattr(b, "flak", False):
            # Flakwagen (seit 0.34.117): fahren nur im Gefolge anderer Fahrzeuge.
            gas, lenk, will, ziel = self._konvoi_fahren(b, ziel_ort)
        elif schutz is not None:
            schutz, liegt = schutz
            if b.pos.distance_to(schutz) > 18.0:
                wp = self._wegpunkt_fuer(b, schutz)
                # Nicht ueber ihn hinweg: liegt er auf dem Weg, aussen herum.
                bahn = wp - b.pos
                rel = liegt.pos - b.pos
                t = rel.dot(bahn.normalize()) if bahn.length_squared() > 1.0 else -1.0
                frei_halb = b.werte.get("halb", b.werte.get("kreis", 16.0)) + 26.0
                if 0.0 < t < bahn.length() and abs(rel.x * bahn.normalize().y
                                                  - rel.y * bahn.normalize().x) < frei_halb:
                    quer = pygame.Vector2(-bahn.y, bahn.x).normalize()
                    seite = -1.0 if rel.dot(quer) > 0 else 1.0
                    wp = liegt.pos + quer * seite * (frei_halb + 12.0)
                gas, lenk = self._lenken(b, wp)
                will = wp - b.pos
            ziel = ziel_ort if ziel_ort is not None else b.pos + b.vorn * 200.0
        elif ziel_ort is not None:
            abstand = b.pos.distance_to(ziel_ort)
            if abstand > f["abstand"].get(b.art, 200.0):
                wp = self._wegpunkt_fuer(b, ziel_ort)
                gas, lenk = self._lenken(b, wp, weit=abstand)
                will = wp - b.pos
            elif b.art == "panzer" and f["mg_ausrichten"] and z is not None:
                # Er haelt: die Wanne zum Gegner, damit das Bug-MG mitschiesst.
                gas, lenk = self._lenken(b, z.pos, halten=True)
            elif b.art == "jagdpanzer":
                # Die Kanone schwenkt nur ein paar Grad (seit 0.34.131 faehrt
                # ihn ein Bot): er dreht die ganze Wanne zum Gegner.
                gas, lenk = self._lenken(b, ziel_ort, halten=True)
            # Die Kanone zielt ohne Handfehler (sie ist ein Geschuetz, kein
            # Gewehr aus der Hand) - mit Fehler flog jede zweite Granate im
            # Freien vorbei und zuendete erst 900 px weiter.
            fehler = (self.fehler * f["fehler"] if z is not None and b.art != "panzer"
                      else pygame.Vector2(0, 0))
            ziel = ziel_ort + fehler
        elif stellung:
            gas, lenk, will = self._stellung_steuern(b, ein, dt)
            ziel = b.pos + b.vorn * 200.0
            if b.art == "werfer":
                ziel = self._werfer_zielen(b, ein, ziel)
        else:
            if self.streif_ort is None or b.pos.distance_to(self.streif_ort[0]) < 80.0:
                self.streif_ort = self._streifziel()
            wp = self._wegpunkt_fuer(b, self.streif_ort[0])
            gas, lenk = self._lenken(b, wp, weit=b.pos.distance_to(self.streif_ort[0]))
            if getattr(b, "abgesetzt", False) and abs(b.fahrt) > K.SCHLACHT["nach_absetzen_tempo"]:
                # Nach dem Absetzen langsam mit den Leuten vor (seit 0.34.96):
                # das Tempo begrenzt, nicht das Gas - mit halbem Gas kam er
                # aus keiner Kurve mehr heraus.
                gas = 0.0
            will = wp - b.pos
            ziel = b.pos + b.vorn * 200.0
        # Steckt er fest: Gas, aber er kommt nicht vom Fleck - gemessen am
        # Weg, nicht am Tempo (seit 0.34.84): ein Panzerwagen, der langsam
        # anfaehrt und dabei wendet, war sonst schon "fest" und setzte immer
        # wieder zurueck.
        self._fahr_steckt = getattr(self, "_fahr_steckt", 0.0)
        self._fahr_zurueck = max(0.0, getattr(self, "_fahr_zurueck", 0.0) - dt)
        # Auch wer nur dreht (Panzer auf der Stelle) und dabei mit der Wanne
        # an einer Wand haengt, steckt fest.
        anker = getattr(self, "_fahr_anker", None)
        if abs(gas) > 0.1 or abs(lenk) > 0.3:
            if (anker is None or b.pos.distance_to(anker[0]) > 12.0
                    or abs(_winkel_diff(anker[1], b.winkel)) > 6.0):
                self._fahr_anker = (pygame.Vector2(b.pos), b.winkel)
                self._fahr_steckt = 0.0
            else:
                self._fahr_steckt += dt
        else:
            self._fahr_anker = None
            self._fahr_steckt = 0.0
        # Seit 0.34.96 merkt er, wie oft er an derselben Stelle feststeckt:
        # jedes Mal etwas laenger zurueck und abwechselnd zur anderen Seite
        # eingeschlagen (gemessen in SCHLACHT: ein Panzerwagen setzte eine
        # Minute lang gleich vor und zurueck). Steckt er immer wieder, setzt
        # er seine Leute ab.
        versuch = getattr(self, "_fahr_versuch", None)
        if versuch is not None and b.pos.distance_to(versuch[0]) > 90.0:
            self._fahr_versuch = versuch = None
        if self._fahr_steckt > f["steckt_nach"] * 2.0:
            self._fahr_steckt = 0.0
            self._fahr_anker = None
            n = 0 if versuch is None else versuch[1] + 1
            self._fahr_versuch = (pygame.Vector2(b.pos) if versuch is None else versuch[0], n)
            # Die ersten beiden Male wie bisher eine Sekunde, erst dann laenger.
            self._fahr_zurueck = min(2.6, f["zurueck"] * (1.0 + 0.4 * max(0, n - 1)))
            self._fahr_seite = 1.0 if n % 2 == 0 else -1.0
            if n >= 3 and getattr(self.g, "schlacht", False) and b.__dict__.get("_mitfahrer"):
                self.g.alle_absetzen(b)
                b.abgesetzt = True
            if n >= 2:
                # Seit 0.34.135 schon beim zweiten Mal (vorher vierten).
                # Immer wieder an derselben Stelle (seit 0.34.131, gemessen auf
                # FLUSSTAL: ein Werfer hing 40 s zwischen Findlingen): ein
                # Umweg zu einer freien Stelle des Fahrwegenetzes daneben.
                netz = self.g.welt.fahrwege
                rnd = self.rnd
                for _ in range(20):
                    q = b.pos + pygame.Vector2(rnd.uniform(160.0, 320.0), 0).rotate(rnd.uniform(0, 360))
                    nah = netz.naechste_frei(b.ebene, q)
                    if nah is not None and self.g.welt.frei(nah, 30.0, b.ebene, True):
                        self._fahr_umweg = (pygame.Vector2(nah), self.g.welt.zeit + 5.0)
                        break
        if self._fahr_zurueck > 0.0:
            n = 0 if getattr(self, "_fahr_versuch", None) is None else self._fahr_versuch[1]
            if n == 0:
                gas, lenk = -0.8, -lenk if abs(lenk) > 0.05 else 0.0
            elif abs(lenk) > 0.3:
                # Wie beim Wenden in drei Zuegen (seit 0.34.140): rueckwaerts
                # gegen die Seite lenken, zu der er will - die Nase schwenkt so
                # zum Ziel. Abwechselnd (wie bisher) machte jeder zweite Versuch
                # den vorigen zunichte; gemessen hing ein Panzerwagen 88 s.
                gas, lenk = -0.8, (-1.0 if lenk > 0 else 1.0)
            else:
                gas, lenk = -0.8, getattr(self, "_fahr_seite", 1.0)
        ein["gl"] = [round(gas, 2), round(lenk, 2)]
        if will.length_squared() > 1.0:
            will = will.normalize()
        ein["will"] = [round(will.x, 2), round(will.y, 2)]
        ein["ziel"] = [round(ziel.x, 1), round(ziel.y, 1)]
        if ziel_ort is not None and getattr(b, "rechteckig", False) and self.reaktion_rest <= 0.0:
            self._fahrzeug_feuern(b, z, ziel_ort, ein)
        if getattr(b, "flak", False):
            self._flak_feuern(b, ein)
        if b.art == "spulenwagen":
            self._spule_feuern(b, z, ein, dt)
        return ein

    # ---- Fahrzeuge mit eigener Aufgabe (seit 0.34.131) --------------------------
    # Gewuenscht: "Stell sicher, dass die Bots alle Fahrzeuge richtig nutzen."
    # Bis 0.34.130 liessen Bots den Jagdpanzer, den Trosswagen, den
    # Spulenwagen, den Funkwagen, den Werfer und den Tragschrauber stehen
    # (K.<ART> nur_mensch). Jetzt hat jeder seine Aufgabe.
    def _druecken(self, ein: dict, dt: float) -> None:
        """Rechte Maustaste einmal druecken (der Wagen reagiert auf die
        Flanke): hoechstens alle 0,6 Sekunden."""
        if self.__dict__.get("_druck_rest", 0.0) <= 0.0:
            ein["zielt"] = True
            self._druck_rest = 0.25

    def _stellung_ort(self, b):
        """Wo ein Nachschub-, Funk- oder Werferwagen stehen soll: mit Front
        hinter dem eigenen Punkt, der den Zielen am naechsten ist; sonst auf
        dem Weg von der eigenen Basis zur Mitte (der Werfer weiter hinten)."""
        g = self.g
        ort = g.front_fahrziel(self.k) if getattr(g, "front_an", False) else None
        if ort is None:
            punkte = getattr(g, "_schlacht_punkte", None)
            basis = g.schlacht_basis(self.k.team) if hasattr(g, "schlacht_basis") else None
            if basis is None or punkte is None:
                return None
            mitte = punkte()[2]
            anteil = {"trosswagen": 0.55, "funkwagen": 0.45, "werfer": 0.22}.get(b.art, 0.4)
            ort = basis + (mitte - basis) * anteil
        return pygame.Vector2(ort)

    def _stellung_steuern(self, b, ein: dict, dt: float):
        """(Gas, Lenkung, Richtung) fuer die Stellung: hinfahren, anhalten,
        aufbauen (Funk, Werfer) oder - der Trosswagen - abstellen und
        aussteigen: dort holen sich die Leute Munition."""
        k = self.k
        jetzt = self.g.welt.zeit
        self._druck_rest = self.__dict__.get("_druck_rest", 0.0) - dt
        st = self.__dict__.get("_fz_stellung")
        if st is None or st[2] is not b or jetzt >= st[1]:
            ort = self._stellung_ort(b)
            if ort is None:
                return 0.0, 0.0, pygame.Vector2(0, 0)
            # Nur umziehen, wenn sich die Front wirklich verschoben hat - ein
            # Aufbau kostet Sekunden, und jeder Umzug macht ihn wehrlos.
            if st is not None and st[2] is b and st[0].distance_to(ort) < 900.0:
                self._fz_stellung = st = (st[0], jetzt + 30.0, b)
            else:
                platz = None
                if hasattr(self.g, "_fahrzeug_platz_bei"):
                    platz = self.g._fahrzeug_platz_bei(b.art, ort, 320.0)
                ort = pygame.Vector2(platz[0]) if platz is not None else ort
                self._fz_stellung = st = (ort, jetzt + 30.0, b)
        ort = st[0]
        d = b.pos.distance_to(ort)
        aufbauen = b.art in ("funkwagen", "werfer")
        # Angekommen ist er auf gut drei Kacheln: kurz vor dem Ziel nimmt
        # _lenken das Gas weg, er rollt nicht genau auf den Punkt.
        if d > 130.0:
            if aufbauen and getattr(b, "phase", 0) in (1, 2):
                # Die Stellung ist weitergezogen: erst einpacken.
                if getattr(b, "aufgebaut", False) or b.phase == 1:
                    self._druecken(ein, dt)
                return 0.0, 0.0, pygame.Vector2(0, 0)
            if aufbauen and getattr(b, "fortschritt", 0.0) > 0.0:
                return 0.0, 0.0, pygame.Vector2(0, 0)          # packt noch ein
            wp = self._wegpunkt_fuer(b, ort)
            gas, lenk = self._lenken(b, wp, weit=d)
            return gas, lenk, wp - b.pos
        ein["hb"] = True
        if aufbauen:
            # Der Wagen nimmt den Druck nur im Stand an (stillstand): mit Abstand
            # darunter druecken, die Handbremse zittert noch ein wenig.
            if b.phase == 0 and b.geschw.length() <= b.werte["stillstand"] * 0.6:
                self._druecken(ein, dt)
            if b.art == "funkwagen" and getattr(b, "aufgebaut", False):
                # Stoeren, sobald Gegner nahe sind, sonst peilen (R wechselt).
                nah = any(x.lebt and x.team != k.team and 0 <= x.team < 2
                          and x.pos.distance_to(b.pos) <= b.werte["stoeren"]
                          for x in self.g.kaempfer.values())
                if b.modus != (1 if nah else 0) and self._druck_rest <= 0.0:
                    ein["knoepfe"].append("nachladen")
                    self._druck_rest = 1.0
        elif b.art == "trosswagen":
            # Abgestellt: aussteigen und mitkaempfen - der Wagen bleibt als
            # Nachschub stehen (keiner faehrt ihn gleich wieder weg).
            if b.geschw.length() < 8.0:
                b._abgestellt = jetzt
                ein["knoepfe"].append("nutzen")
        return 0.0, 0.0, pygame.Vector2(0, 0)

    def _werfer_zielen(self, b, ein: dict, ziel):
        """Aufgebaut: das Ziel der Seite mit den meisten Gegnern darum, in
        Reichweite - dorthin der Zeiger, und feuern, wenn er bereit ist."""
        if not getattr(b, "aufgebaut", False):
            return ziel
        w = K.WERFER["salve"]
        team = self.k.team
        mitte = b.rohr_mitte()
        orte = [o for o, _r in self.g.werfer_ziele(team)
                if w["nah"] + 20.0 <= o.distance_to(mitte) <= self.g.werfer_weite() - 20.0] \
            if hasattr(self.g, "werfer_ziele") and 0 <= team < 2 else []
        if not orte:
            return ziel
        # Nie dorthin, wo eigene Leute stehen.
        eigen = [x.pos for x in self.g.kaempfer.values()
                 if x.lebt and x.team == team and x is not self.k]
        orte = [o for o in orte if all(o.distance_to(q) > w["streu"] + w["radius"] + 30.0 for q in eigen)]
        if not orte:
            return ziel
        bestes = max(orte, key=lambda o: sum(1 for q in orte if q.distance_to(o) < w["streu"] * 1.5))
        ein["feuert"] = bool(getattr(b, "bereit", False))
        return pygame.Vector2(bestes)

    def _landeplatz_suchen(self, b, basis) -> pygame.Vector2:
        """Eine freie, offene Stelle bei der Basis, gross genug, dass ein
        Tragschrauber dort ohne Absturz aufsetzt (Buggy.passt und Abstand)."""
        welt = self.g.welt
        rnd = self.rnd
        beste = pygame.Vector2(basis)
        for versuch in range(80):
            weit = 120.0 + versuch * 8.0
            p = pygame.Vector2(basis) + pygame.Vector2(weit, 0).rotate(rnd.uniform(0, 360))
            if welt.frei(p, 70.0, b.ebene, True):
                return p
        return beste

    def _spule_feuern(self, b, z, ein: dict, dt: float) -> None:
        """Spulenwagen: der Kettenblitz auf einen Gegner in Reichweite, das
        EMP-Feld, wenn fremde Fahrzeuge nah sind (er haelt dafuer an)."""
        self._druck_rest = self.__dict__.get("_druck_rest", 0.0) - dt
        welt = self.g.welt
        blitz = b.werte["blitz"]
        if z is not None and z.pos.distance_to(b.pos) <= blitz["reichweite"] \
                and welt.sicht_frei(b.pos, z.pos, b.ebene):
            ein["feuert"] = True
            ein["ziel"] = [round(z.pos.x, 1), round(z.pos.y, 1)]
        feld = b.werte["feld"]
        from .fahrzeug import seite_von
        eigen = seite_von(b)
        fremde = [x for x in getattr(self.g, "fahrzeuge", ())
                  if x is not b and not x.kaputt and not x.nur_bild and x.fahrer is not None
                  and seite_von(x) != eigen and x.pos.distance_to(b.pos) <= feld["radius"] * 0.85]
        if fremde and b.phase == 0:
            ein["gl"] = [0.0, 0.0]
            ein["hb"] = True
            if b.geschw.length() <= feld["stillstand"]:
                self._druecken(ein, dt)

    def _schrauber_steuern(self, b, ein: dict, dt: float) -> dict:
        """Der Tragschrauber (seit 0.34.131 auch mit Bot): am Boden Gas, bis
        er abhebt; in der Luft zum Ziel der Front und dort im Kreis, Bomben
        auf Gegner unter ihm. Ohne Bomben zurueck zur eigenen Basis, landen,
        nachladen, wieder los."""
        k = self.k
        g = self.g
        f = b.werte
        jetzt = g.welt.zeit
        basis = g.schlacht_basis(k.team) if hasattr(g, "schlacht_basis") else None
        heim = b.bomben <= 0 or b.leben < b.max_leben * 0.35
        if not b.luft:
            self.__dict__.pop("_landeplatz", None)
            if b.bomben < f["bomben"] and basis is not None and b.pos.distance_to(basis) < 900.0:
                ein["gl"] = [0.0, 0.0]          # nachladen: stehen
                ein["hb"] = True
                ein["will"] = [0.0, 0.0]
                return ein
            # Anlauf: geradeaus, wo frei ist, bis er abhebt.
            frei = g.welt.frei(b.pos + b.vorn * 90.0, 18.0, b.ebene, True)
            ein["gl"] = [1.0, 0.0 if frei else 1.0]
            ein["will"] = [round(b.vorn.x, 2), round(b.vorn.y, 2)]
            ein["ziel"] = [round(b.pos.x + b.vorn.x * 200, 1), round(b.pos.y + b.vorn.y * 200, 1)]
            return ein
        if heim and basis is not None:
            # Heim zum Nachladen: ein freier Landeplatz bei der Basis, gemerkt.
            # Er setzt zur Landung an, wenn er gerade darauf zufliegt und noch
            # so weit weg ist, wie er beim Sinken gleitet - dann setzt er dort auf.
            platz = self.__dict__.get("_landeplatz")
            if platz is None or platz[1] != id(b):
                ort = self._landeplatz_suchen(b, basis)
                platz = self._landeplatz = (ort, id(b))
            ziel = pygame.Vector2(platz[0])
            weg = ziel - b.pos
            gleiten = f["landen_tempo"] * f["hoehe"] / max(1.0, f["sinken"]) + 30.0
            if not b.landen and weg.length() < gleiten + 50.0:
                diff_l = abs(_winkel_diff(b.winkel, math.degrees(math.atan2(weg.y, weg.x))))
                if diff_l < 25.0 and weg.length() > gleiten - 40.0:
                    ein["knoepfe"].append("nutzen")       # E: zur Landung ansetzen
                elif weg.length() < gleiten - 40.0:
                    # Zu nah fuer den Anflug: eine Schleife und noch einmal.
                    ziel = ziel + (b.pos - ziel).normalize() * 500.0 if weg.length() > 1.0 else ziel
        else:
            ziel = self.__dict__.get("_flug_ziel")
            if ziel is None or jetzt >= self.__dict__.get("_flug_neu", 0.0):
                ort = g.front_fahrziel(k) if getattr(g, "front_an", False) else None
                if ort is None:
                    punkte = getattr(g, "_schlacht_punkte", None)
                    ort = punkte()[2] if punkte is not None else b.pos
                self._flug_ziel = ziel = pygame.Vector2(ort)
                self._flug_neu = jetzt + 20.0
            # Ueber dem Ziel kreisen: der Punkt wandert auf einem Kreis darum.
            kreis = pygame.Vector2(260.0, 0).rotate(jetzt * 30.0 + k.nummer * 47.0)
            if b.pos.distance_to(ziel) < 420.0:
                ziel = ziel + kreis
        weg = ziel - b.pos
        soll = math.degrees(math.atan2(weg.y, weg.x))
        diff = _winkel_diff(b.winkel, soll)
        lenk = max(-1.0, min(1.0, diff / 25.0))
        gas = 1.0 if weg.length() > 600.0 else 0.0
        ein["gl"] = [round(gas, 2), round(lenk, 2)]
        ein["will"] = [round(b.vorn.x, 2), round(b.vorn.y, 2)]
        # Bomben: ein Gegner (oder fremdes Fahrzeug) dort, wo sie aufschlaegt.
        bo = f["bombe"]
        abwurf = b.pos + pygame.Vector2(bo["abwurf"]).rotate(b.winkel) + b.vorn * (b.flug_v * bo["fall"] * bo["schwung"])
        treffer = [x.pos for x in g.kaempfer.values()
                   if x.lebt and 0 <= x.team < 2 and x.team != k.team and int(x.ebene) == 0
                   and x.pos.distance_to(abwurf) <= bo["radius"] * 0.8]
        from .fahrzeug import seite_von
        eigen = seite_von(b)
        treffer += [x.pos for x in getattr(g, "fahrzeuge", ())
                    if x is not b and not x.kaputt and not x.nur_bild and x.fahrer is not None
                    and seite_von(x) != eigen and x.pos.distance_to(abwurf) <= bo["radius"]]
        freunde = any(x.lebt and x.team == k.team and x is not k
                      and x.pos.distance_to(abwurf) <= bo["radius"] * 1.2 for x in g.kaempfer.values())
        ein["feuert"] = bool(treffer) and not freunde and b.bomben > 0 and not heim
        ziel_bild = treffer[0] if treffer else b.pos + b.vorn * 200.0
        ein["ziel"] = [round(ziel_bild.x, 1), round(ziel_bild.y, 1)]
        return ein

    def _konvoi_fuehrer(self, b):
        """Das Fahrzeug der eigenen Seite, hinter dem der Flakwagen herfaehrt
        (seit 0.34.117) - oder None: dann wartet er. Erst wenn eines mit
        Fahrer mehr als K.FLAK["konvoi_los"] von seinem Startort weg ist, geht
        es los; danach gilt jedes eigene Fahrzeug mit Fahrer."""
        f = K.FLAK
        team = self.k.team
        los = self.__dict__.get("_konvoi_los", False)
        bester = None
        for x in getattr(self.g, "fahrzeuge", ()):
            if (x is b or x.art == "flakwagen" or x.nur_bild or x.kaputt or x.fahrer is None
                    or x.ebene != b.ebene or getattr(x.fahrer, "team", -1) != team):
                continue
            start = getattr(x, "start", None)
            if not los and start is not None and x.pos.distance_to(start[0]) < f["konvoi_los"]:
                continue
            d = x.pos.distance_to(b.pos)
            if bester is None or d < bester[0]:
                bester = (d, x)
        self._konvoi_los = bester is not None
        return None if bester is None else bester[1]

    def _konvoi_fahren(self, b, ziel_ort):
        """Gas, Lenken, Richtung und Zielpunkt des Flakwagens: hinter dem
        Fuehrer her oder stehen. Geschossen wird wie immer."""
        f = K.FLAK
        ziel = pygame.Vector2(ziel_ort) if ziel_ort is not None else b.pos + b.vorn * 200.0
        fuehrer = self._konvoi_fuehrer(b)
        if fuehrer is None:
            # Ohne Konvoi nicht stehen bleiben (seit 0.34.138, gemeldet: "die
            # Fahrer im Flakwagen fahren oft einfach nicht los"): wie die
            # anderen Fahrzeuge zu den Zielen der Seite.
            if self.streif_ort is None or b.pos.distance_to(self.streif_ort[0]) < 80.0:
                self.streif_ort = self._streifziel()
            wp = self._wegpunkt_fuer(b, self.streif_ort[0])
            gas, lenk = self._lenken(b, wp, weit=b.pos.distance_to(self.streif_ort[0]))
            return gas, lenk, wp - b.pos, ziel
        abstand = b.pos.distance_to(fuehrer.pos)
        if abstand <= f["konvoi_abstand"]:
            return 0.0, 0.0, pygame.Vector2(0, 0), ziel
        wp = self._wegpunkt_fuer(b, fuehrer.pos)
        gas, lenk = self._lenken(b, wp, weit=abstand)
        return gas, lenk, wp - b.pos, ziel

    def _flak_feuern(self, b, ein: dict) -> None:
        """Am Flak-Vierling (seit 0.34.114): ein Luftziel der Gegner in
        Reichweite geht vor jedem Bodenziel. Der Bot legt den Zeiger auf das
        *Bild* des Fliegers - die Zielregel (luft.py) rastet dann ein und
        haelt vor - und feuert, sobald die Lafette nah genug dran ist. Mauern
        zwischen Rohr und Boden unter ihm halten die Kugeln auf."""
        f = K.FLAK
        welt = self.g.welt
        mitte = b.aufbau_mitte()
        bester, weite = None, f["bot_reichweite"]
        for lz in self.g.luft_ziele():
            if (lz.fraktion and lz.fraktion == self.k.fraktion) or lz.objekt is b:
                continue
            d = lz.pos.distance_to(mitte)
            if d < weite and welt.sicht_frei(mitte, lz.pos, b.ebene):
                bester, weite = lz, d
        self.flak_ziel = bester          # fuer die INFO-Ansicht des Testmodus
        if bester is None:
            return
        ein["ziel"] = [round(bester.bild_pos.x, 1), round(bester.bild_pos.y, 1)]
        ort = self.g._vorhalten(self.k, bester)
        weg = ort - mitte
        soll = math.degrees(math.atan2(weg.y, weg.x))
        ein["feuert"] = abs(_winkel_diff(b.aufbau, soll)) <= f["bot_winkel"]

    def _wegpunkt_fuer(self, b, ort):
        """Der naechste Wegpunkt zu `ort` fuer den Wagen. Seit 0.34.95 aus
        dem Wegenetz der Fahrzeuge (wege.Fahrwegenetz): durch Luecken, durch
        die nur ein Mensch passt, schickt es ihn nicht mehr. Er zielt so
        weit voraus, wie die Strecke gerade frei ist."""
        f = K.BOTS["fahren"]
        netz = self.g.welt.fahrwege
        ort = pygame.Vector2(ort)
        umweg = self.__dict__.get("_fahr_umweg")
        if umweg is not None:
            if self.g.welt.zeit < umweg[1] and b.pos.distance_to(umweg[0]) > K.TILE * 1.5:
                ort = umweg[0]
            else:
                self._fahr_umweg = None
        if b.pos.distance_to(ort) < K.TILE * 1.5:
            return ort
        ziel = netz.naechste_frei(b.ebene, ort)
        if ziel is None:
            return ort
        _schl, feld = netz.feld_zu(b.ebene, ziel)
        punkt, _rest = netz.schritt_ueber(b.ebene, feld, b.pos)
        if punkt is None:
            # Er steht neben dem Netz (an einer Wand): erst zurueck darauf.
            nah = netz.naechste_frei(b.ebene, b.pos)
            if nah is not None and nah.distance_to(b.pos) > 4.0 and _rest != 0:
                return nah
            return ort
        breit = b.werte.get("halb", 12.0)
        for _ in range(f["weg_voraus"]):
            weiter, _r = netz.schritt_ueber(b.ebene, feld, punkt)
            if weiter is None or not netz.gerade_frei(b.ebene, b.pos, weiter, breit):
                break
            punkt = weiter
        return punkt

    def _fahrzeug_feuern(self, b, z, ziel_ort, ein: dict) -> None:
        """Kanone, Ring-MG und Bug-MG (seit 0.34.84). Die Kanone ist
        explosiv: sie feuert, sobald der Einschlag nah genug am Ziel liegt
        (statt auf 5 Grad genau), und auch auf einen, der gerade hinter
        Deckung steht, wenn die Granate bis dicht an ihn herankommt."""
        f = K.BOTS["fahren"]
        welt = self.g.welt
        mitte = b.aufbau_mitte()
        weg = ziel_ort - mitte
        dist = weg.length()
        if dist < 1.0:
            return
        soll = math.degrees(math.atan2(weg.y, weg.x))
        fehl = abs(_winkel_diff(b.aufbau, soll))
        if b.art == "jagdpanzer":
            # Die Jagdkanone (seit 0.34.131 mit Bot): weit und genau - sie
            # feuert, wenn das Rohr auf ihn zeigt und nichts dazwischen ist.
            w = K.FAHRZEUG_WAFFEN.get(b.werte.get("kanone", "kanone"), K.FAHRZEUG_WAFFEN["kanone"])
            treffer = (getattr(z, "radius", 9.0) if z is not None else 9.0) + 6.0
            vorbei = dist * math.sin(math.radians(min(fehl, 89.0)))
            ein["feuert"] = (dist <= w["reichweite"] and vorbei <= treffer
                             and welt.sicht_frei(mitte, ziel_ort, b.ebene))
            return
        if b.art == "panzer":
            w = K.FAHRZEUG_WAFFEN["kanone"]
            if dist <= w["reichweite"]:
                # Die Granate zuendet erst beim Aufschlag. Im Freien muss sie
                # also treffen; steht aber Deckung direkt bei ihm (davor oder
                # dahinter), schlaegt sie dort ein, und dann reicht "nah dran".
                richtung = weg.normalize()
                frei = welt.sicht_frei(mitte, ziel_ort, b.ebene)
                dahinter = ziel_ort + richtung * (w["radius"] * 0.8)
                deckung_nah = not welt.sicht_frei(ziel_ort, dahinter, b.ebene)
                vorbei = dist * math.sin(math.radians(min(fehl, 89.0)))
                if frei:
                    treffer = (getattr(z, "radius", 9.0) if z is not None else 9.0) + 5.0
                    ein["feuert"] = vorbei <= treffer or (
                        deckung_nah and vorbei <= w["radius"] * f["splash_anteil"])
                else:
                    # Verdeckt: reicht die Bahn bis dicht vor ihn?
                    vor = ziel_ort - richtung * (w["radius"] * 0.7)
                    ein["feuert"] = (vorbei <= w["radius"] * f["splash_anteil"]
                                     and welt.sicht_frei(mitte, vor, b.ebene))
            if z is not None:
                vorn = math.degrees(math.atan2(b.vorn.y, b.vorn.x))
                mg = K.FAHRZEUG_WAFFEN["bug_mg"]
                ein["zielt"] = (abs(_winkel_diff(vorn, soll)) <= f["mg_winkel"]
                                and dist <= mg["reichweite"]
                                and welt.sicht_frei(mitte, z.pos, b.ebene))
        elif z is not None:
            mg = K.FAHRZEUG_WAFFEN["ring_mg"]
            ein["feuert"] = (fehl <= f["mg_winkel"] and dist <= mg["reichweite"]
                             and welt.sicht_frei(mitte, z.pos, b.ebene))

    def _sicher(self, will):
        """Nicht in ein Loch und nicht gegen die Wand: die Richtung so weit
        drehen, bis vor ihm Boden ist. Seit 0.34.70 auch nicht in Feuer,
        Gas, eine Falle, die er sieht, oder in Stacheldraht - lieber geht
        er herum; nur wenn es gar keinen anderen Weg gibt, hinein."""
        if will.length_squared() < 0.01:
            return will
        k = self.k
        welt = self.g.welt
        e = welt.ebene(k.ebene)
        notfall = None
        for dreh in (0, 30, -30, 60, -60, 100, -100, 150, -150):
            r = will.rotate(dreh)
            p = k.pos + r.normalize() * 16.0
            tx, ty = int(p.x // K.TILE), int(p.y // K.TILE)
            if k.ebene > 0 and e.loch(tx, ty):
                continue
            if welt.frei(p, k.radius, k.ebene, True):
                # Ohne bekannte Gefahr gibt es nichts zu pruefen (seit 0.34.75).
                if (self._gefahren and self._gefahr_bei(k.pos + r.normalize() * 26.0)
                        and not self._gefahr_bei(k.pos)):
                    if notfall is None:
                        notfall = r
                    continue
                return r
        return notfall if notfall is not None else pygame.Vector2(0, 0)

    # ---- Gefahren (seit 0.34.70) ---------------------------------------
    def _gefahren_sammeln(self) -> list:
        """Was auf seiner Ebene gefaehrlich ist: (Ort, Radius) - Feuer, Gas,
        Fallen, die er sieht, Stacheldraht und scharfe Wuerfe, die er sieht.
        Gefragt wird die Welt, nie der Beobachter (AGENTS.md)."""
        k = self.k
        welt = self.g.welt
        rand = K.BOTS["gefahr_rand"]
        raus = []
        for b in welt.feuer:
            if b.lebt and b.ebene == k.ebene and b.staerke > 0.15:
                raus.append((pygame.Vector2(b.pos), b.radius + rand))
        for g in getattr(welt, "gas", ()):
            if g.lebt and g.ebene == k.ebene:
                raus.append((pygame.Vector2(g.pos), g.radius + rand))
        if self.geblendet > 0.0:
            self._flaechen = list(raus)
            return raus                  # was fliegt und liegt, sieht er nicht
        sicht = K.BOTS["granate_sieht"]
        fliegt = set()
        for w in welt.wesen:
            if not w.lebt or w.ebene != k.ebene or w is k:
                continue
            art = getattr(w, "art", "")
            if getattr(w, "ist_ausruestung", False):
                if art == "stacheldraht":
                    raus.append((pygame.Vector2(w.pos), K.AUSRUESTUNG["stacheldraht"]["laenge"] / 2))
                elif art == "sprengfalle" and getattr(w, "fraktion", "") != k.fraktion \
                        and (w.bild is not None or w.zuendet >= 0.0):
                    raus.append((pygame.Vector2(w.pos), K.AUSRUESTUNG["sprengfalle"]["spreng_radius"]
                                 if w.zuendet >= 0.0 else K.AUSRUESTUNG["sprengfalle"]["radius"] + rand))
                continue
            d = getattr(w, "daten", None)
            if not isinstance(d, dict) or not hasattr(w, "zuenden"):
                continue
            if d.get("rauch") or d.get("blend") or d.get("knaller") or d.get("gerade"):
                continue
            r = d.get("radius", 0.0) or (40.0 if d.get("feuer") or d.get("gas") else 0.0)
            if r <= 0.0 or k.pos.distance_to(w.pos) > sicht:
                continue
            raus.append((pygame.Vector2(w.pos), r + rand))
            fliegt.add(len(raus) - 1)
        # Was liegt und brennt (Feuer, Gas, Draht, Fallen) - nur darum geht
        # der Umweg (_um_gefahr). Einer geworfenen Granate weicht er auf
        # seine eigene Art aus (granate_ausweichen).
        self._flaechen = [g_ for i_, g_ in enumerate(raus) if i_ not in fliegt]
        return raus

    def _gefahr_bei(self, punkt) -> bool:
        for ort, r in self._gefahren:
            if ort.distance_squared_to(punkt) <= r * r:
                return True
        return False

    def _gefahr_raus(self):
        """Steht er in einer Gefahr: die Richtung hinaus (weg von allen,
        in denen er steht). Sonst None."""
        if not self._gefahren:
            return None                   # wie unten: keine Gefahr, kein Weg hinaus
        k = self.k
        weg = pygame.Vector2(0, 0)
        for ort, r in self._gefahren:
            ab = k.pos - ort
            if ab.length_squared() <= r * r:
                weg += ab.normalize() if ab.length_squared() > 0.01 else pygame.Vector2(1, 0).rotate(
                    self.rnd.uniform(0, 360))
        if weg.length_squared() < 0.01:
            return None
        return weg.normalize()

    def _abzug(self, feuern: bool, zielt: bool):
        """Wie die Waffe in der Hand bedient wird (seit 0.34.70): mit dem
        Nahkampf erst, wenn er nah genug ist; die Spule wird gehalten und
        losgelassen, wenn sie voll ist; die Flamme nur in Reichweite."""
        k = self.k
        d = k._waffe_lesen()
        art = d.get("art", "schuss")
        z = self.ziel
        abstand = k.pos.distance_to(z.pos) if z is not None else 9999.0
        if art == "nahkampf":
            feuern = feuern and abstand <= d.get("reichweite", 30.0) + getattr(z, "radius", 9.0)
            zielt = False
        elif art == "flamme":
            feuern = feuern and abstand <= d["reichweite"]
        elif art == "strahl":
            # Einmal angefangen, haelt er, bis sie voll ist - dann ein Bild
            # loslassen, das feuert. Feuerstoesse wie beim Gewehr luden sie
            # nie ganz.
            if k.ladung >= K.BOTS["spule_loslassen"]:
                feuern = False
            elif k.ladung > 0.0 and z is not None and z.lebt:
                feuern = True
        elif art == "kette":
            # Ebenso: halten, bis der Blitz von selbst springt.
            if k.ladung > 0.0 and z is not None and z.lebt:
                feuern = True
        return feuern, zielt

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


def schwebt(w) -> bool:
    """Haengt `w` noch am Fallschirm (seit 0.34.100)?"""
    return getattr(w, "schirm_hoehe", 0.0) > 0.0


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
        """Wie viele Spieler es mit Bots insgesamt sein sollen, 0 = keine.
        In SCHLACHT (seit 0.34.95) immer beide Seiten voll."""
        if not self.bots_aktiv:
            return 0
        if getattr(self, "schlacht", False):
            return self.schlacht_seite * len(K.TEAMS["namen"])
        return int(self.regelwerk.get("bots", 0) or 0)

    def bots_fest(self, team: int) -> int:
        """Wie viele Bots fest in dieser Mannschaft spielen (-1: ohne
        Mannschaften), unabhaengig von den Menschen (seit 0.34.26)."""
        if not self.bots_aktiv or getattr(self, "schlacht", False):
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
        # Fallschirmjaeger (seit 0.34.100) kommen dazu, sie zaehlen nicht mit:
        # sonst nahm das Auffuellen gleich fuenf andere Bots weg.
        bots = [k for k in self._bots() if not getattr(k, "verstaerkung", False)]
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
                       + K.BOTS["je_team_hoechstens"] * (len(K.TEAMS["namen"]) + 1) + 8
                       + max(K.SCHLACHT["groessen"]) * len(K.TEAMS["namen"])):
            plan = self._bot_fehlen()
            fehlt = [t for t, n in plan if n > 0]
            zu_viel = [t for t, n in plan if n < 0]
            if fehlt:
                self._bot_dazu(fehlt[0])
            elif zu_viel:
                team = zu_viel[0]
                kandidaten = [k for k in self._bots() if (team < 0 or k.team == team)
                              and not getattr(k, "verstaerkung", False)]
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
        # SCHLACHT (seit 0.34.95): so viele Bots je Seite duerfen fahren,
        # wie die Basis Fahrzeuge hat - sonst fahren Bots nicht.
        if getattr(self, "schlacht", False) and 0 <= team:
            fahrer = sum(1 for x in self._bots() if x.team == team
                         and getattr(x, "darf_fahren", False))
            # Auf einer Karte mit Front sagt der Kopf, wie viele (seit 0.34.131).
            plan = getattr(self, "schlachtplan", None)
            hoechstens = plan.fahrer if plan is not None else K.SCHLACHT["fahrer_je_seite"]
            # Seit 0.34.138 mit der Seitenstaerke mehr (gemeldet: "die Bots sollen
            # alle Fahrzeuge bewusster einsetzen, den Funkwagen sehe ich nie") -
            # hoechstens so viele, wie die Basen Wagen haben.
            seite = int(getattr(self, "schlacht_seite", 0) or 0)
            if seite > 0:
                # Ein Anteil der Seite - bei 8 je Seite 3, bei 24 je Seite 10.
                hoechstens = max(1, int(round(seite * K.SCHLACHT["fahrer_anteil"])))
            if hasattr(self, "basis_ausstattung"):
                try:
                    wagen = sum(n for _a, n, _b in self.basis_ausstattung(team, -1, 3))
                except Exception:          # noqa: BLE001  ohne Plan: wie bisher
                    wagen = hoechstens
                if wagen > 0:
                    hoechstens = min(hoechstens, wagen)
            k.darf_fahren = fahrer < hoechstens
        k.konto = ""
        k.skin = bot_aussehen(name)
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
        if getattr(self, "schlacht", False) and getattr(self, "front_an", False) and 0 <= team < 2:
            # Front (seit 0.34.131): gleich dort einsteigen, wo ihn sein Ziel
            # hinschickt. Nur in SCHLACHT - im Testmodus steht ein Bot dort,
            # wo man ihn hinsetzt.
            k.pos.update(self.front_einstiegsort(k))
            k.vorher.update(k.pos)
            self.front_eingestiegen(k)
        return k

    def _bot_weg(self, k) -> None:
        self._fahrzeug_loesen(k)
        k.lebt = False
        self.kaempfer.pop(k.nummer, None)

    def _bots_alle_weg(self) -> None:
        for k in self._bots():
            self._bot_weg(k)

    def _bot_vielfalt(self) -> bool:
        """Mehr verschiedene Waffen bei den Bots (seit 0.34.95). In echten
        Runden immer; der Testmodus schaltet es selbst."""
        return True

    def _panzerjaeger_an(self) -> bool:
        """Gibt es in dieser Runde Panzerjaeger? Nur, wenn Fahrzeuge da sind."""
        # In SCHLACHT immer: dort kommen die Fahrzeuge erst nach den Bots
        # an Fallschirmen (seit 0.34.96).
        return bool(getattr(self, "fahrzeuge", ())) or bool(getattr(self, "schlacht", False))

    def _panzerjaeger_noetig(self, k) -> bool:
        """Soll `k` in diesem Leben Panzerjaeger sein? So viele je
        Mannschaft wie K.BOTS panzerjaeger je_team (in SCHLACHT
        K.SCHLACHT panzerjaeger_je_seite) - gezaehlt, nicht gewuerfelt."""
        if not self._panzerjaeger_an():
            return False
        hoechstens = (K.SCHLACHT["panzerjaeger_je_seite"] if getattr(self, "schlacht", False)
                      else K.BOTS["panzerjaeger"]["je_team"])
        # Einer je `je_bots` Bots der Mannschaft: in einer kleinen Runde
        # waeren sonst gleich alle Bots Panzerjaeger.
        team = [x for x in self._bots() if x.team == k.team]
        soll = min(hoechstens, len(team) // K.BOTS["panzerjaeger"]["je_bots"])
        da = sum(1 for x in team if x is not k and getattr(x, "panzerjaeger", False))
        return da < soll

    def _bot_loadout_anlegen(self, k) -> None:
        """Zu jedem Leben ein neues, zufaelliges Loadout - ohne C4."""
        fest = self._fest_loadout() if self.loadout_regel == "gleich" else None
        lo = bot_loadout(self._bot_rnd, fest, vielfalt=fest is None and self._bot_vielfalt())
        k.panzerjaeger = fest is None and self._panzerjaeger_noetig(k)
        if k.panzerjaeger:
            lo = dict(lo, waffen=panzerjaeger_waffen(k.nummer, lo["waffen"][0]))
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
        # Ein Durchgang: so lange gilt das Merken in BotHirn._kandidaten.
        self._kandidaten_lauf = self.__dict__.get("_kandidaten_zaehler", 0) + 1
        self._kandidaten_zaehler = self._kandidaten_lauf
        bots = self._bots()
        jede = 1
        for ab, n in K.BOTS["staffel"]:
            if len(bots) >= ab:
                jede = n
        lauf = self.__dict__.get("_staffel_lauf", 0) + 1
        self._staffel_lauf = lauf
        # Fern vom Geschehen (seit 0.34.142): wer weiter als `fern_ab` px von
        # jedem Menschen weg ist, denkt nur jeden `fern_jede`. Schritt - ihn
        # sieht keiner, und gekaempft wird trotzdem (gemessen in SCHLACHT:
        # die meisten Bots stehen weit weg vom Spieler). Ohne Menschen (der
        # Testmodus, die Verhaltens-Szenen) gilt das nicht.
        fern_ab, fern_jede = K.BOTS["fern_ab"], K.BOTS["fern_jede"]
        menschen = [(m.pos, m.ebene) for m in self.kaempfer.values() if not m.ist_bot] \
            if len(bots) >= K.BOTS["fern_ab_bots"] else []
        fern_q = fern_ab * fern_ab
        try:
            for k in bots:
                hirn = getattr(k, "hirn", None)
                if hirn is None:
                    continue
                jetzt_jede = jede
                if menschen and fern_jede > jede and all(
                        k.pos.distance_squared_to(p_) > fern_q for p_, _e in menschen):
                    jetzt_jede = fern_jede
                if jetzt_jede > 1:
                    # Versetzt: in jedem Schritt denkt ein Teil der Bots.
                    hirn._staffel_dt = getattr(hirn, "_staffel_dt", 0.0) + dt
                    if (lauf + k.nummer) % jetzt_jede:
                        continue
                    schritt, hirn._staffel_dt = hirn._staffel_dt, 0.0
                    self._anwenden(k, hirn.eingabe(schritt))
                    continue
                hirn._staffel_dt = 0.0
                self._anwenden(k, hirn.eingabe(dt))
        finally:
            self._kandidaten_lauf = None
            self.__dict__.pop("_kandidaten_merk", None)

    def _bot_hoert(self, pos, ebene: int, quelle, weite: float | None = None) -> None:
        """Ein Schuss oder Knall - fuer die Ohren der Bots. `weite`: so weit
        ist er zu hoeren (Vorgabe: ein Schuss)."""
        # any statt der ganzen Liste (seit 0.34.89): dieselbe Frage, ob es
        # ueberhaupt einen Bot gibt - bei jedem Schuss gestellt.
        if not any(getattr(k, "ist_bot", False) for k in self.kaempfer.values()):
            return
        fraktion = getattr(getattr(quelle, "von", quelle), "fraktion", "")
        self._bot_geraeusche.append((pygame.Vector2(pos), int(ebene),
                                     self.welt.zeit, fraktion,
                                     K.BOTS["gehoer"] if weite is None else float(weite)))
        if len(self._bot_geraeusche) > 40:
            del self._bot_geraeusche[:10]
