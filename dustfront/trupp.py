"""
DUSTFRONT - Trupps mit Anfuehrer, Sprechen und Funk (seit 0.34.39)
==================================================================

Gemeldet: "dass die Teams verschiedene Squad-Leader haben, die miteinander
ueber Funk kommunizieren ... wenn das eine Team sagt, wir sind in der
Unterzahl, wir halten aber eine wichtige Position, dann sollen sie nach
Hilfe rufen. Das andere Team soll entscheiden, okay, bei uns sind nur ein
paar Gegner, dann toeten wir die und kommen dann sofort zur Hilfe ... Die
Squad-Leader sollen eher hinten bleiben, in der Mitte der Formation, und
die anderen sollen priorisieren, ihnen zu helfen ... Sie sollen sprechen
koennen, mit einer bestimmten Reichweite, und in Sprechreichweite bleiben
... Wichtig ist, dass das mit dem GOAP weiter beibehalten wird: die Bots
sind am Ende immer noch nur Menschen, und durch ihre Moeglichkeiten und
Ziele entsteht alles."

Ein `Trupp` entscheidet darum **nichts fuer seine Leute**. Er ist das, was
alle im Trupp gemeinsam wissen und sehen - wie in *Days Gone* (Karlsson):

* **Lage**: wen einer gesehen hat und in Sprechweite gesagt hat. Wer zu
  weit weg ist, dessen Wissen kommt nicht an - und er erfaehrt nichts.
* **Zuversicht des Trupps**: der Schnitt der Leute, zur Mitte gerundet.
  Daraus der **Zustand**: Feuerkampf, Rueckzug in Wellen (besorgt), Druck
  mit Flanke (zuversichtlich), Halten (eine Stellung, die wichtig ist),
  Suchen in breiter Linie (kein Kontakt).
* **Frontlinie und Bahnen**: Richtung von der eigenen Mitte zur
  Gegnermitte, ein Niemandsland davor, jeder bekommt eine Bahn - damit
  sie nicht "wie Ameisen in einer Reihe" laufen (Killzone 2). Der
  Anfuehrer steht in der Mitte und tiefer.
* **Wellen**: beim Rueckzug geht die Haelfte vorn zurueck, die andere
  deckt; beim Druck ruecken die Hinteren auf.

Was einer davon tut, entscheidet sein eigenes Gehirn: der Zustand kommt
bei ihm als Fakt an (`trupp_rueckzug` ...), die Ziele dazu stehen in
`wesen/bots.txt` - und Panik oder eine Granate gehen weiter vor.

**Funk** (nur im Testmodus, wo es Trupps gibt): der Anfuehrer mit
Funkgeraet (`k.funkgeraet`) meldet die Lage und ruft um Hilfe. Ein Spruch
dauert (`K.TRUPP["funk_dauer"]`), dann haben ihn alle Anfuehrer seiner
Seite mit Funk. Ob sie helfen, entscheidet jeder Trupp nach seiner
eigenen Lage (`hilfe_pruefen`): wer selbst kaum Gegner hat, sagt zu,
macht seine erst fertig und kommt dann.
"""

from __future__ import annotations

import math

import pygame

from . import config as K


def trupp_von(k):
    """Der Trupp eines Kaempfers, oder None."""
    return getattr(getattr(k, "hirn", None), "trupp", None)


def richtung_wort(von, nach) -> str:
    """Grob die Himmelsrichtung, fuer Sprueche wie "ZWEI IM NORDEN"."""
    d = pygame.Vector2(nach) - pygame.Vector2(von)
    if d.length_squared() < 1.0:
        return "HIER"
    winkel = math.degrees(math.atan2(d.y, d.x)) % 360.0
    worte = ("OSTEN", "SÜDOSTEN", "SÜDEN", "SÜDWESTEN", "WESTEN", "NORDWESTEN",
             "NORDEN", "NORDOSTEN")
    return worte[int((winkel + 22.5) // 45.0) % 8]


ZAHLWORTE = ("KEINER", "EINER", "ZWEI", "DREI", "VIER", "FÜNF", "SECHS")


def zahl_wort(n: int) -> str:
    return ZAHLWORTE[n] if 0 <= n < len(ZAHLWORTE) else "VIELE"


class Funkspruch:
    """Ein Spruch ueber Funk: wer, an wen (alle Anfuehrer der Seite), was."""

    def __init__(self, trupp, art: str, text: str, zeit: float, lage: dict) -> None:
        self.trupp = trupp
        self.art = art               # "lage", "hilfe", "zusage", "frei"
        self.text = text
        self.zeit = zeit
        self.lage = lage             # staerke, feinde, zuversicht, ort, ebene, wichtig
        self.an = None               # bei "zusage": an welchen Trupp


class Trupp:
    """Was ein Trupp gemeinsam weiss. Siehe oben."""

    def __init__(self, g, team: int, name: str) -> None:
        self.g = g
        self.team = team
        self.name = name
        self.mitglieder: list = []
        self.fuehrer = None
        # Der Auftrag: "frei" (selbst suchen), "halten" (eine Stellung),
        # "angriff" (dorthin). `wichtig`: dort gibt man nicht nach.
        self.auftrag = dict(art="frei", ort=None, ebene=0, wichtig=False)
        self.lage: dict = {}          # Wesen -> [Ort, Ebene, Zeit]
        self.zustand = "ruhe"
        self._zustand_seit = -1e9
        self.zuversicht = 2
        self.front = None             # dict(freund, feind, richtung, quer, linie, breite)
        self.stellungen: dict = {}    # Nummer -> Ort, an dem er stehen soll
        self.welle: set = set()       # Nummern, die in dieser Welle ziehen
        self._welle_ziel: dict = {}   # ... und wohin
        self._welle_rest = 0.0
        self.flanker: set = set()     # Nummern mit der Rolle Flanke (Druck)
        self.geister: dict = {}       # Nummer -> Ort, wo ein Flankierer war (Days Gone)
        self.suche_ort = None         # wohin der Trupp ohne Kontakt geht
        self.hilfe = None             # dict(fuer, ort, ebene, zugesagt, geantwortet)
        self.bergung = None           # dict(opfer, retter, sicher, bedrohung) - seit 0.34.40
        self.gerufen_bis = -1e9       # so lange gilt unser eigener Hilferuf
        self.gemeldet = None          # was wir zuletzt gemeldet haben
        self.gemeldet_zeit = -1e9
        self.funk_lage: dict = {}     # Name eines anderen Trupps -> letzte Meldung
        self._takt = 0.0

    # ── Wer ───────────────────────────────────────────────────────
    def lebende(self) -> list:
        g = self.g
        return [m for m in self.mitglieder
                if m.lebt and not getattr(m, "am_boden", False)
                and g.kaempfer.get(m.nummer) is m and getattr(m, "hirn", None) is not None]

    def fuehrt(self, k) -> bool:
        """Fuehrt `k` gerade jemanden? Wer allein uebrig ist, fuehrt keinen."""
        return k is self.fuehrer and len(self.lebende()) >= 2 and k in self.lebende()

    def sprechweite(self) -> float:
        return K.TRUPP["sprech_weite"]

    def hoert(self, a, b) -> bool:
        """Hoeren sich zwei, wenn sie sprechen? Gleiche Ebene, nah genug."""
        return (a.ebene == b.ebene
                and a.pos.distance_to(b.pos) <= self.sprechweite())

    def in_kontakt(self, k) -> bool:
        """Hat er Sprechkontakt zu jemandem im Trupp (oder ist er allein)?"""
        andere = [m for m in self.lebende() if m is not k]
        return not andere or any(self.hoert(k, m) for m in andere)

    # ── Der Schritt ───────────────────────────────────────────────
    def schritt(self, dt: float) -> None:
        self._welle_rest -= dt
        self._takt -= dt
        if self._takt > 0.0:
            return
        self._takt = K.TRUPP["takt"]
        leute = self.lebende()
        if self.fuehrer is not None and self.fuehrer not in leute and leute:
            # Faellt der Anfuehrer, fuehrt der Naechste - ohne Funkgeraet,
            # das hatte nur er.
            self.fuehrer = max(leute, key=lambda m: m.hirn.merkmale.get("disziplin", 0.5))
        self._lage_sammeln(leute)
        self._zuversicht(leute)
        self._zustand_waehlen(leute)
        self._front_rechnen(leute)
        self._stellungen(leute)
        self._hilfe_auswerten()
        self._bergung_planen(leute)

    def _lage_sammeln(self, leute) -> None:
        """Wer einen Gegner sieht und jemanden im Trupp in Sprechweite hat,
        sagt es - dann wissen es alle. Neue Gegner werden angesagt."""
        jetzt = self.g.welt.zeit
        neu_je = {}
        for m in leute:
            if not self.in_kontakt(m):
                continue
            for w, (ort, ebene, zeit) in m.hirn.gesehen.items():
                if not w.lebt or jetzt - zeit > 0.4:
                    continue
                if w not in self.lage:
                    neu_je.setdefault(m, []).append(w)
                self.lage[w] = [pygame.Vector2(w.pos), w.ebene, jetzt]
        for w in list(self.lage):
            if not w.lebt or getattr(w, "am_boden", False) \
                    or jetzt - self.lage[w][2] > K.TRUPP["gedaechtnis"]:
                del self.lage[w]
        for m, neue in neu_je.items():
            m.hirn.sagen("%s IM %s!" % (zahl_wort(len(neue)),
                                       richtung_wort(m.pos, neue[0].pos)))

    def feinde(self, ebene=None) -> list:
        """(Ort, Ebene, Wesen) aller Gegner, die der Trupp kennt."""
        return [(pygame.Vector2(o), e, w) for w, (o, e, _z) in self.lage.items()
                if ebene is None or e == ebene]

    def _zuversicht(self, leute) -> None:
        """Days Gone: der Schnitt, zur Mitte (neutral) hin gerundet."""
        stufen = [m.hirn.innen.stufe for m in leute if getattr(m.hirn, "innen", None)]
        if not stufen:
            self.zuversicht = 2
            return
        schnitt = sum(stufen) / len(stufen)
        self.zuversicht = int(math.floor(schnitt)) if schnitt > 2 else int(math.ceil(schnitt))

    def unterlegen(self) -> bool:
        """Sind wir in der Unterzahl? Deutlich mehr Gegner als Leute - oder
        mehr Gegner als Leute, und der Trupp ist besorgt. Besorgt allein
        reicht nicht: vier gegen einen ruft keiner um Hilfe."""
        n = len(self.lebende())
        feinde = len(self.lage)
        if not feinde:
            return False
        return (feinde >= max(2, n) * K.TRUPP["unterzahl"]
                or (feinde > n and self.zuversicht <= 1)
                or self.zuversicht <= 0)

    def _zustand_waehlen(self, leute) -> None:
        jetzt = self.g.welt.zeit
        t = K.TRUPP
        if not leute:
            self.zustand = "ruhe"
            return
        halten = self.auftrag["art"] == "halten" and self.auftrag["ort"] is not None
        if not self.lage:
            neu = "halten" if halten else "suchen"
        elif halten and self.auftrag.get("wichtig"):
            neu = "halten"          # eine wichtige Stellung gibt man nicht auf
        elif self.zuversicht <= 1:
            neu = "rueckzug"
        elif self.zuversicht >= 3:
            neu = "druck"
        else:
            neu = "halten" if halten else "feuerkampf"
        if neu != self.zustand and jetzt - self._zustand_seit >= t["zustand_halten"]:
            self.zustand = neu
            self._zustand_seit = jetzt
            self.welle = set()
            self._welle_rest = 0.0
            self.flanker = set()
            self.geister = {}

    def _front_rechnen(self, leute) -> None:
        """Die Frontlinie (Days Gone): Richtung, Linie, Breite. Bewegt sich
        nur ueber einer Schwelle - sonst muesste jeder bei jedem Schritt
        des Gegners seine Stellung wechseln."""
        t = K.TRUPP
        if not leute or not self.lage:
            self.front = None
            return
        ebene = leute[0].ebene
        feinde = [o for o, e, _w in self.feinde(ebene)]
        if not feinde:
            self.front = None
            return
        punkte = []
        for m in leute:
            if m.nummer in self.flanker and m.nummer in self.geister:
                punkte.append(self.geister[m.nummer])
            elif m.ebene == ebene:
                punkte.append(pygame.Vector2(m.pos))
        if not punkte:
            self.front = None
            return
        freund = sum(punkte, pygame.Vector2(0, 0)) / len(punkte)
        if self.auftrag["art"] == "halten" and self.auftrag["ort"] is not None \
                and freund.distance_to(self.auftrag["ort"]) < t["halten_weite"]:
            # Die Stellung im Ruecken (Days Gone, Home Area).
            freund = pygame.Vector2(self.auftrag["ort"])
        feind = sum(feinde, pygame.Vector2(0, 0)) / len(feinde)
        hin = feind - freund
        if hin.length_squared() < 1.0:
            hin = pygame.Vector2(1, 0)
        richtung = hin.normalize()
        quer = pygame.Vector2(-richtung.y, richtung.x)
        naechster = min((o - freund).dot(richtung) for o in feinde)
        spanne = [(o - freund).dot(quer) for o in feinde]
        breite = max(max(spanne) - min(spanne) + 2 * t["rand"], len(leute) * t["bahn_min"])
        linie = freund + richtung * max(0.0, naechster - t["niemandsland"])
        alt = self.front
        if alt is not None:
            winkel = abs((alt["richtung"].angle_to(richtung) + 180.0) % 360.0 - 180.0)
            wackelt = (alt["linie"].distance_to(linie) < t["front_schwelle"]
                       and winkel < t["front_winkel"])
            if wackelt:
                return
            # Gleitend hin, schneller, je groesser der Sprung.
            anteil = min(1.0, 0.35 + alt["linie"].distance_to(linie) / 400.0)
            linie = alt["linie"] + (linie - alt["linie"]) * anteil
        self.front = dict(freund=freund, feind=feind, richtung=richtung, quer=quer,
                          linie=linie, breite=breite, ebene=ebene)

    def _stellungen(self, leute) -> None:
        """Wo jeder stehen soll. Mit Kontakt: seine Bahn hinter der Linie,
        so weit zurueck, wie seine Waffe es will; der Anfuehrer in der
        Mitte und tiefer. Ohne Kontakt: eine breite Linie um den
        Anfuehrer, nicht hintereinander."""
        t = K.TRUPP
        self.stellungen = {}
        if not leute:
            return
        f = self.front
        if f is None:
            self._linie_ohne_kontakt(leute)
            return
        andere = [m for m in leute if m is not self.fuehrer]
        # Bahnen von links nach rechts, nach der Lage quer zur Richtung
        # vergeben - so laeuft keiner quer durch die anderen.
        andere.sort(key=lambda m: (m.pos - f["freund"]).dot(f["quer"]))
        reihe = list(andere)
        if self.fuehrer in leute:
            reihe.insert(len(reihe) // 2, self.fuehrer)
        n = len(reihe)
        for i, m in enumerate(reihe):
            seitlich = (i - (n - 1) / 2.0) * (f["breite"] / max(1, n))
            wunsch = K.BOTS["wunschabstand"].get(m.waffe_name, 220.0)
            tiefe = max(0.0, wunsch - t["niemandsland"]) * 0.6
            if m is self.fuehrer:
                tiefe += t["fuehrer_tiefe"]
            if getattr(m.hirn, "geschwaecht", False):
                tiefe += t["geschwaecht_tiefe"]
            p = f["linie"] + f["quer"] * seitlich - f["richtung"] * tiefe
            if m.nummer in self.flanker:
                p = self._flankenpunkt(m)
            self.stellungen[m.nummer] = self._frei(p, m)
        self._wellen(leute)

    def _linie_ohne_kontakt(self, leute) -> None:
        t = K.TRUPP
        fuehrer = self.fuehrer if self.fuehrer in leute else leute[0]
        ziel = self.ziel_ort()
        richtung = None
        if ziel is not None:
            hin = pygame.Vector2(ziel) - fuehrer.pos
            if hin.length_squared() > 100.0:
                richtung = hin.normalize()
        if richtung is None:
            richtung = pygame.Vector2(1, 0).rotate(fuehrer.hirn.blick)
        quer = pygame.Vector2(-richtung.y, richtung.x)
        andere = [m for m in leute if m is not fuehrer]
        andere.sort(key=lambda m: (m.pos - fuehrer.pos).dot(quer))
        n = len(andere)
        for i, m in enumerate(andere):
            seitlich = (i - (n - 1) / 2.0) * t["linie_abstand"]
            if n == 1:
                seitlich = t["linie_abstand"] * 0.7
            p = fuehrer.pos + quer * seitlich + richtung * t["linie_vor"]
            self.stellungen[m.nummer] = self._frei(p, m)
        self.stellungen[fuehrer.nummer] = pygame.Vector2(fuehrer.pos)

    def _frei(self, p, m):
        welt = self.g.welt
        if welt.frei(p, m.radius + 2, m.ebene, True):
            return pygame.Vector2(p)
        return pygame.Vector2(welt.landeplatz(p, m.radius + 2, m.ebene))

    def _flankenpunkt(self, m):
        """Seitlich des Gegners (Days Gone): auf der Seite, die ihm naeher
        ist - hinten bleibt eine Luecke zum Rueckzug."""
        f = self.front
        seite = 1.0 if (m.pos - f["freund"]).dot(f["quer"]) >= 0 else -1.0
        return (f["feind"] + f["quer"] * seite * (f["breite"] / 2 + K.TRUPP["rand"])
                - f["richtung"] * K.TRUPP["flanke_vor"])

    def _wellen(self, leute) -> None:
        """Rueckzug und Druck in Wellen: die Haelfte zieht, die andere
        deckt, dann umgekehrt. Beim Rueckzug ziehen die vorn zuerst, beim
        Druck die hinten. Wer zieht, bekommt eine neue Stellung."""
        t = K.TRUPP
        f = self.front
        if self.zustand not in ("rueckzug", "druck") or f is None:
            self.welle = set()
            return
        if self._welle_rest > 0.0 and self.welle:
            for m in leute:
                if m.nummer in self.welle and m.nummer in self._welle_ziel:
                    self.stellungen[m.nummer] = self._welle_ziel[m.nummer]
            return
        self._welle_rest = t["welle_zeit"]
        vorn = sorted(leute, key=lambda m: -(m.pos - f["freund"]).dot(f["richtung"]))
        haelfte = max(1, len(leute) // 2)
        if self.zustand == "rueckzug":
            ziehen = vorn[:haelfte]
            schritt = -t["welle_weite"]
        else:
            ziehen = vorn[-haelfte:]
            schritt = t["welle_weite"]
            # Nahe genug dran: die Aeusseren flankieren.
            nah = all((m.pos - f["linie"]).dot(f["richtung"]) > -t["flanke_ab"] for m in leute)
            if nah and len(leute) >= 3 and not self.flanker:
                aussen = sorted(leute, key=lambda m: -abs((m.pos - f["freund"]).dot(f["quer"])))
                for m in aussen[:1]:
                    if m is not self.fuehrer:
                        self.flanker.add(m.nummer)
                        self.geister[m.nummer] = pygame.Vector2(m.pos)
        self.welle = {m.nummer for m in ziehen if m.nummer not in self.flanker}
        self._welle_ziel = {}
        for m in ziehen:
            p = m.pos + f["richtung"] * schritt
            if schritt > 0:
                # Nie ins Niemandsland.
                ueber = (p - f["linie"]).dot(f["richtung"])
                if ueber > 0:
                    p -= f["richtung"] * ueber
            self._welle_ziel[m.nummer] = self._frei(p, m)
            self.stellungen[m.nummer] = self._welle_ziel[m.nummer]

    def ziel_ort(self):
        """Wohin der Trupp ohne Kontakt geht: zur Hilfe, zum Auftrag, zu dem,
        was zuletzt einer gehoert hat, sonst den Weg seines Anfuehrers."""
        if self.hilfe is not None and self.hilfe.get("zugesagt"):
            return pygame.Vector2(self.hilfe["ort"])
        if self.auftrag["ort"] is not None:
            return pygame.Vector2(self.auftrag["ort"])
        return None

    # ── Funk ──────────────────────────────────────────────────────
    def lage_jetzt(self) -> dict:
        leute = self.lebende()
        f = self.front
        mitte = (sum((pygame.Vector2(m.pos) for m in leute), pygame.Vector2(0, 0)) / len(leute)
                 if leute else pygame.Vector2(0, 0))
        return dict(staerke=len(leute), feinde=len(self.lage), zuversicht=self.zuversicht,
                    ort=pygame.Vector2(f["freund"] if f else mitte),
                    ebene=leute[0].ebene if leute else 0,
                    wichtig=bool(self.auftrag.get("wichtig")) and self.auftrag["art"] == "halten",
                    zustand=self.zustand)

    def lage_neu(self) -> bool:
        """Hat sich so viel geaendert, dass der Anfuehrer es melden sollte?"""
        jetzt = self.g.welt.zeit
        if jetzt - self.gemeldet_zeit < K.TRUPP["melden_pause"]:
            return False
        jetzt_lage = self.lage_jetzt()
        alt = self.gemeldet
        if alt is None:
            return bool(self.lage)
        return (abs(jetzt_lage["feinde"] - alt["feinde"]) >= 2
                or jetzt_lage["staerke"] < alt["staerke"]
                or jetzt_lage["zuversicht"] != alt["zuversicht"]
                or (alt["feinde"] > 0) != (jetzt_lage["feinde"] > 0))

    def hilfe_gerufen(self) -> bool:
        return self.g.welt.zeit < self.gerufen_bis

    def antwort_offen(self) -> bool:
        return self.hilfe is not None and self.hilfe.get("zugesagt") \
            and not self.hilfe.get("geantwortet")

    def funk_text(self, art: str, an=None) -> str:
        lage = self.lage_jetzt()
        if art == "hilfe":
            teil = "HALTEN STELLUNG" if lage["wichtig"] else "UNTER DRUCK"
            return "%s: %s, %d GEGEN %d - BRAUCHEN HILFE!" % (
                self.name, teil, lage["staerke"], lage["feinde"])
        if art == "zusage":
            return "%s AN %s: VERSTANDEN, KOMMEN!" % (self.name, an.name if an else "ALLE")
        if art == "frei":
            return "%s: LAGE RUHIG, KEIN KONTAKT." % self.name
        zustand = {"rueckzug": "ZIEHEN UNS ZURÜCK", "druck": "DRÜCKEN NACH VORN",
                   "halten": "HALTEN", "feuerkampf": "IM FEUERKAMPF"}.get(lage["zustand"], "")
        return "%s: %d GEGNER, %d MANN, %s." % (self.name, lage["feinde"], lage["staerke"],
                                                zustand or "IN BEWEGUNG")

    def funk_senden(self, art: str) -> Funkspruch:
        """Der Spruch ist zu Ende gesprochen: alle Anfuehrer der Seite mit
        Funk haben ihn jetzt."""
        g = self.g
        jetzt = g.welt.zeit
        an = self.hilfe["fuer"] if art == "zusage" and self.hilfe else None
        spruch = Funkspruch(self, art, self.funk_text(art, an), jetzt, self.lage_jetzt())
        spruch.an = an
        netz = g.__dict__.setdefault("_funknetz", [])
        netz.append(spruch)
        del netz[:-K.TRUPP["funk_gedaechtnis"]]
        self.gemeldet = spruch.lage
        self.gemeldet_zeit = jetzt
        if art == "hilfe":
            self.gerufen_bis = jetzt + K.TRUPP["hilferuf_gilt"]
        if art == "zusage" and self.hilfe is not None:
            self.hilfe["geantwortet"] = True
        for anderer in trupps(g):
            if anderer is self or anderer.team != self.team:
                continue
            fuehrer = anderer.fuehrer
            if fuehrer is None or not fuehrer.lebt or not getattr(fuehrer, "funkgeraet", False):
                continue
            anderer.empfangen(spruch)
        return spruch

    def empfangen(self, spruch) -> None:
        self.funk_lage[spruch.trupp.name] = spruch
        if spruch.art == "hilfe":
            self.hilfe_pruefen(spruch)
        elif self.hilfe is not None and self.hilfe["fuer"] is spruch.trupp:
            # Es geht ihnen wieder besser: nicht mehr hin.
            lage = spruch.lage
            if spruch.art == "frei" or lage["zuversicht"] >= 3 or lage["feinde"] == 0:
                self.hilfe = None

    def hilfe_pruefen(self, spruch) -> bool:
        """Lohnt es sich zu helfen? Wer selbst in der Unterzahl ist, nicht.
        Wer nur wenige Gegner hat, sagt zu - und macht die erst fertig."""
        t = K.TRUPP
        if self.hilfe is not None or not self.lebende():
            return False
        eigene = len(self.lage)
        if self.unterlegen() or eigene > t["helfen_bis_feinde"]:
            return False
        if self.auftrag["art"] == "halten" and self.auftrag.get("wichtig") and eigene > 0:
            return False
        weg = spruch.lage["ort"].distance_to(self.lebende()[0].pos)
        if weg > t["helfen_weite"]:
            return False
        self.hilfe = dict(fuer=spruch.trupp, ort=pygame.Vector2(spruch.lage["ort"]),
                          ebene=spruch.lage["ebene"], zugesagt=True, geantwortet=False,
                          zeit=self.g.welt.zeit)
        return True

    def _hilfe_auswerten(self) -> None:
        """Angekommen, oder zu lange her: die Hilfe ist vorbei."""
        h = self.hilfe
        if h is None:
            return
        leute = self.lebende()
        if not leute or self.g.welt.zeit - h["zeit"] > K.TRUPP["hilfe_hoechstens"]:
            self.hilfe = None
            return
        mitte = sum((pygame.Vector2(m.pos) for m in leute), pygame.Vector2(0, 0)) / len(leute)
        if mitte.distance_to(h["ort"]) < K.TRUPP["angekommen"]:
            # Angekommen: jetzt hoert man die anderen - was sie wissen, wissen
            # wir auch, und gekaempft wird, wo sie kaempfen.
            for w, eintrag in h["fuer"].lage.items():
                self.lage.setdefault(w, list(eintrag))
            self.hilfe = None

    def stellung(self, k):
        return self.stellungen.get(k.nummer)

    # ── Bergen (seit 0.34.40) ─────────────────────────────────────
    def _bergung_planen(self, leute) -> None:
        """Liegt einer, sucht der Trupp ein, zwei Retter aus - die naechsten,
        nicht den Anfuehrer, keinen Geschwaechten -, die anderen decken. Ob
        es sicher genug ist, sagt die Lage: sieht ihn kein Gegner (oder
        liegt Rauch auf ihm), oder ist der Trupp zuversichtlich genug, um
        es gegen die durchzuziehen, die ihn sehen. Gemeldet: "nur, wenn es
        recht sicher erscheint oder die Bots sich sicher sind, dass sie in
        der Lage sind, das als Team durchzuziehen." """
        g = self.g
        v = K.VERWUNDET
        liegen = [m for m in self.mitglieder
                  if m.lebt and getattr(m, "am_boden", False) and g.kaempfer.get(m.nummer) is m]
        b = self.bergung
        if b is not None and b["opfer"] not in liegen:
            self.bergung = b = None
        if not liegen or not leute:
            self.bergung = None
            return
        if b is None:
            mitte = sum((pygame.Vector2(m.pos) for m in leute), pygame.Vector2(0, 0)) / len(leute)
            opfer = min(liegen, key=lambda m: m.pos.distance_to(mitte))
            b = self.bergung = dict(opfer=opfer, retter=set(), sicher=False, bedrohung=0)
        opfer = b["opfer"]
        welt = g.welt
        n = 0
        for o, e, _w in self.feinde(opfer.ebene):
            if (o.distance_to(opfer.pos) <= v["bedrohung"]
                    and sieht_durch_rauch(welt, o, opfer.pos, e)):
                n += 1
        b["bedrohung"] = n
        b["sicher"] = (n == 0 or self.zuversicht >= 4
                       or (self.zuversicht >= 2 and n <= max(0, len(leute) - 2)))
        da = {m.nummer for m in leute}
        retter = {r for r in b["retter"] if r in da}
        soll = min(v["retter"], max(1, len(leute) - 1))
        frei = sorted((m for m in leute if m.nummer not in retter),
                      key=lambda m: (m is self.fuehrer and len(leute) > 1,
                                     bool(getattr(m.hirn, "geschwaecht", False)),
                                     m.pos.distance_to(opfer.pos)))
        while len(retter) < soll and frei:
            retter.add(frei.pop(0).nummer)
        b["retter"] = retter


def sieht_durch_rauch(welt, a, b, ebene) -> bool:
    """Freie Sicht von a nach b - ohne Mauer und ohne Rauch auf der Linie
    (seit 0.34.40: Rauch zwischen einem Liegenden und dem Gegner macht das
    Bergen sicher)."""
    if not welt.sicht_frei(a, b, ebene):
        return False
    a = pygame.Vector2(a)
    b = pygame.Vector2(b)
    for t in (0.25, 0.5, 0.75, 1.0):
        p = a + (b - a) * t
        if any(r.ebene == ebene and r.deckt(p, ebene) for r in welt.rauch):
            return False
    return True


def trupps(g) -> list:
    return g.__dict__.setdefault("_trupps", [])


def trupps_fuehren(g, dt: float) -> None:
    """Beim Gastgeber, einmal je Schritt: jeder Trupp frischt auf, was er
    weiss. Leere Trupps fallen weg."""
    liste = trupps(g)
    for t in list(liste):
        if not any(m.lebt and g.kaempfer.get(m.nummer) is m for m in t.mitglieder):
            liste.remove(t)
            continue
        t.schritt(dt)
