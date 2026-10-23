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
        self.stellungen_vorher: dict = {}
        self.abschnitte = 1           # in so viele Richtungen schaut die Front (seit 0.34.50)
        self.abschnitt_linien: list = []
        self.welle: set = set()       # Nummern, die in dieser Welle ziehen
        self._welle_ziel: dict = {}   # ... und wohin
        self._welle_rest = 0.0
        self.flanker: set = set()     # Nummern mit der Rolle Flanke (Druck)
        self.geister: dict = {}       # Nummer -> Ort, wo ein Flankierer war (Days Gone)
        self.suche_ort = None         # wohin der Trupp ohne Kontakt geht
        self.hilfe = None             # dict(fuer, ort, ebene, zugesagt, geantwortet)
        self.bergung = None           # dict(opfer, retter, sicher, bedrohung) - seit 0.34.40
        # Seit 0.34.41: Rundumverteidigung und Engstellen.
        self.igel = None              # dict(ort, ebene, bis): wo sich der Trupp einigelt
        self.enge = None              # dict(ort, halte, achse, breite, ebene, bis): die Engstelle
        self.blicke: dict = {}        # Nummer -> Ort, wohin er schauen soll (sein Sektor)
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
        self._bergung_deckung(leute)

    def _lage_sammeln(self, leute) -> None:
        """Wer einen Gegner sieht und jemanden im Trupp in Sprechweite hat,
        haelt die anderen auf dem Laufenden. Neue Gegner kommen seit 0.34.50
        nicht mehr sofort dazu: er ruft sie zu (GoapHirn._ansagen), und erst
        wenn der Satz durch ist, weiss es der Trupp."""
        jetzt = self.g.welt.zeit
        for m in leute:
            if not self.in_kontakt(m):
                continue
            for w, (ort, ebene, zeit) in m.hirn.gesehen.items():
                if not w.lebt or getattr(w, "am_boden", False) or jetzt - zeit > 0.4:
                    continue
                if w in self.lage or not hasattr(m.hirn, "zuruf_starten"):
                    self.lage[w] = [pygame.Vector2(w.pos), w.ebene, jetzt]
        for w in list(self.lage):
            if not w.lebt or getattr(w, "am_boden", False) \
                    or jetzt - self.lage[w][2] > K.TRUPP["gedaechtnis"]:
                del self.lage[w]

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
        if self.auftrag["art"] == "igel" and self.auftrag["ort"] is not None:
            # Testmodus TRUPP: IGEL HIER - einigeln, wo es befohlen ist.
            self.igel = dict(ort=pygame.Vector2(self.auftrag["ort"]),
                             ebene=self.auftrag.get("ebene", leute[0].ebene), bis=jetzt + 1e9)
            neu = "igel"
        elif self.lage and self.umzingelt(leute):
            # Von allen Seiten: einigeln - lieber an einem Platz mit Deckung
            # ringsum, jeder schaut in seine Richtung.
            neu = "igel"
            if self.igel is None or jetzt > self.igel["bis"]:
                self.igel = self._igel_platz(leute)
        elif self.lage and self._horde(leute):
            # Eine Horde Nahkaempfer (Zombies): an einer Engstelle halten,
            # wenn es eine gibt - sonst wie immer.
            if self.enge is None or jetzt > self.enge["bis"]:
                self.enge = self._engstelle_suchen(leute)
            neu = "engstelle" if self.enge is not None else ("halten" if halten else "feuerkampf")
        elif not self.lage:
            neu = "halten" if halten else "suchen"
        elif halten and self.auftrag.get("wichtig"):
            neu = "halten"          # eine wichtige Stellung gibt man nicht auf
        elif self.zuversicht <= 1:
            neu = "rueckzug"
        elif self.zuversicht >= 3:
            neu = "druck"
        else:
            neu = "halten" if halten else "feuerkampf"
        if neu != self.zustand and (jetzt - self._zustand_seit >= t["zustand_halten"]
                                    or neu == "igel"):
            if neu != "igel" and self.auftrag["art"] != "igel":
                self.igel = None
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
        self.stellungen_vorher = self.stellungen
        self.stellungen = {}
        self.abschnitte = 1
        self.abschnitt_linien = []
        if not leute:
            return
        self._blicke_vorher = self.blicke
        self.blicke = {}
        if self.zustand == "igel" and self.igel is not None:
            self._ring(leute)
            return
        if self.zustand == "engstelle" and self.enge is not None:
            self._bogen(leute)
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
            else:
                p = self._deckung_nah(p, m, f["feind"])
            self.stellungen[m.nummer] = self._frei(p, m)
        if self.zustand not in ("rueckzug", "druck"):
            self._abschnitte(leute)
        self._wellen(leute)

    def gruppen_nach_richtung(self, mitte, ebene) -> list:
        """Die bekannten Gegner, nach ihrer Richtung von `mitte` aus in
        Gruppen geteilt: wo zwischen zwei Richtungen mehr als
        `abschnitt_luecke` Grad frei sind, beginnt eine neue. Je Gruppe
        (Richtung als Einheitsvektor, Mitte, Zahl)."""
        feinde = [o for o, e, _w in self.feinde(ebene) if o.distance_to(mitte) > 1.0]
        if not feinde:
            return []
        paare = sorted(((math.degrees(math.atan2(o.y - mitte.y, o.x - mitte.x)) % 360.0, o)
                        for o in feinde), key=lambda x: x[0])
        luecke = K.TRUPP["abschnitt_luecke"]
        gruppen = [[paare[0]]]
        for vor, nach in zip(paare, paare[1:]):
            if nach[0] - vor[0] > luecke:
                gruppen.append([nach])
            else:
                gruppen[-1].append(nach)
        # Ueber 360 Grad hinweg: die letzte gehoert zur ersten, wenn die
        # Luecke dort klein ist.
        if len(gruppen) > 1 and paare[0][0] + 360.0 - paare[-1][0] <= luecke:
            gruppen[0] = gruppen.pop() + gruppen[0]
        raus = []
        for gr in gruppen:
            m = sum((o for _w, o in gr), pygame.Vector2(0, 0)) / len(gr)
            hin = m - mitte
            raus.append((hin.normalize() if hin.length_squared() > 1.0 else pygame.Vector2(1, 0),
                         m, len(gr)))
        return raus

    def _abschnitte(self, leute) -> None:
        """Gegner aus mehreren Richtungen (seit 0.34.50): die Front knickt -
        ein Teil des Trupps schaut zu jeder Gruppe, in einer kurzen Linie
        quer zu ihr, an Deckung gerueckt; der Anfuehrer bleibt in der Mitte
        dahinter. Gemeldet: "dass sich die Frontlinie stark anpasst ... wo
        immer ein Teil der Front quasi zu jedem Gegner schaut". Die Leute
        werden nach ihrer Richtung verteilt, damit keiner quer laeuft."""
        t = K.TRUPP
        f = self.front
        ebene = f["ebene"]
        mitte = pygame.Vector2(f["freund"])
        gruppen = self.gruppen_nach_richtung(mitte, ebene)
        andere = [m for m in leute if m is not self.fuehrer and m.nummer not in self.flanker]
        if len(gruppen) < 2 or len(andere) < 2:
            return
        gruppen.sort(key=lambda g: math.atan2(g[0].y, g[0].x))
        gruppen = gruppen[:len(andere)]
        # Je Gruppe wenigstens einer, der Rest nach der Zahl der Gegner.
        anteile = [1] * len(gruppen)
        rest = len(andere) - len(gruppen)
        gesamt = sum(g[2] for g in gruppen)
        while rest > 0:
            i = max(range(len(gruppen)), key=lambda j: gruppen[j][2] / gesamt - anteile[j] / len(andere))
            anteile[i] += 1
            rest -= 1
        teile = self._abschnitt_leute(andere, gruppen, anteile, mitte)
        hinten = pygame.Vector2(0, 0)
        self.abschnitt_linien = []
        for (richtung, gmitte, _n), anzahl, teil in zip(gruppen, anteile, teile):
            quer = pygame.Vector2(-richtung.y, richtung.x)
            hinten -= richtung
            # Fuer die Anzeige (Testmodus): jeder Abschnitt eine kurze Linie.
            self.abschnitt_linien.append(dict(mitte=mitte + richtung * t["abschnitt_vor"], quer=quer,
                                              richtung=richtung,
                                              breite=max(40.0, anzahl * t["bahn_min"])))
            # Bahnen quer zur Gruppe nach der Lage: so laeuft keiner quer.
            teil.sort(key=lambda m: (m.pos - mitte).dot(quer))
            for j, m in enumerate(teil):
                seitlich = (j - (anzahl - 1) / 2.0) * t["bahn_min"]
                p = mitte + richtung * t["abschnitt_vor"] + quer * seitlich
                p = self._deckung_nah(p, m, gmitte)
                self.stellungen[m.nummer] = self._frei(p, m)
                self.blicke[m.nummer] = pygame.Vector2(gmitte)
        if self.fuehrer in leute:
            weg = hinten.normalize() if hinten.length_squared() > 0.01 else pygame.Vector2(0, 0)
            self.stellungen[self.fuehrer.nummer] = self._frei(mitte + weg * t["fuehrer_tiefe"], self.fuehrer)
        self.abschnitte = len(gruppen)

    def _abschnitt_leute(self, andere, gruppen, anteile, mitte) -> list:
        """Wer in welchen Abschnitt kommt: je Gruppe eine Liste. Wer schon
        einen hatte, bleibt dort (seit 0.34.52) - vorher wurde jeden Takt nach
        dem Winkel neu verteilt, und wer dabei die Gruppe wechselte, lief
        quer durch die Stellung zur anderen Seite. Zu viele in einem
        Abschnitt: die, deren Richtung am wenigsten passt, gehen."""
        def abweichung(m, j):
            a = m.pos - mitte
            if a.length_squared() < 1.0:
                return 0.0
            return abs((a.angle_to(gruppen[j][0]) + 180.0) % 360.0 - 180.0)

        vorher = getattr(self, "_blicke_vorher", {})
        teile = [[] for _g in gruppen]
        offen = []
        for m in andere:
            alt = vorher.get(m.nummer)
            if alt is None:
                offen.append(m)
                continue
            j = min(range(len(gruppen)), key=lambda i: gruppen[i][1].distance_to(alt))
            teile[j].append(m)
        for j, teil in enumerate(teile):
            teil.sort(key=lambda m: abweichung(m, j))
            while len(teil) > anteile[j]:
                offen.append(teil.pop())
        # Die Uebrigen dorthin, wo noch Platz ist und die Richtung am besten
        # passt - wer am eindeutigsten zu einer Gruppe gehoert, zuerst.
        offen.sort(key=lambda m: min(abweichung(m, j) for j in range(len(gruppen))))
        for m in offen:
            frei = [j for j in range(len(gruppen)) if len(teile[j]) < anteile[j]]
            j = min(frei, key=lambda i: abweichung(m, i))
            teile[j].append(m)
        return teile

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

    def gedeckt_hier(self, p, ebene, feind) -> bool:
        """Steht dicht vor dieser Stelle etwas zwischen ihr und dem Gegner?
        Nur eine ferne Wand dazwischen zaehlt nicht - an die kann er sich
        nicht anlehnen."""
        welt = self.g.welt
        hin = pygame.Vector2(feind) - p
        if hin.length_squared() < 1.0:
            return False
        nah = p + hin.normalize() * K.TRUPP["deckung_nah"]
        return welt.deckung(feind, p, ebene) != "" and welt.deckung(nah, p, ebene) != ""

    def _deckung_nah(self, p, m, feind, halten: bool = True):
        """Die Stellung an die naechste Deckung ruecken: wer eine Kiste in
        der Naehe hat, stellt sich dahinter, nicht daneben ins Freie. Die
        vorige Stellung bleibt, solange sie noch deckt - sonst rueckten sie
        bei jedem Takt hin und her."""
        welt = self.g.welt
        p = pygame.Vector2(p)
        # Wer in einer Welle zieht, soll wirklich weiter - nicht dort bleiben.
        alt = self.stellungen_vorher.get(m.nummer) if halten else None
        weit = K.TRUPP["deckung_ringe"][-1]
        if (alt is not None and alt.distance_to(p) <= weit
                and self.gedeckt_hier(alt, m.ebene, feind)):
            return pygame.Vector2(alt)
        if self.gedeckt_hier(p, m.ebene, feind):
            return an_deckung(welt, p, m.radius, m.ebene, feind)
        belegt = [q for n, q in self.stellungen.items() if n != m.nummer]
        for r in K.TRUPP["deckung_ringe"]:
            for i in range(8):
                q = p + pygame.Vector2(r, 0).rotate(i * 45.0)
                if not welt.frei(q, m.radius + 2, m.ebene, True):
                    continue
                if any(q.distance_to(b) < K.TRUPP["bahn_min"] * 0.5 for b in belegt):
                    continue
                if self.gedeckt_hier(q, m.ebene, feind):
                    return an_deckung(welt, q, m.radius, m.ebene, feind)
        return p

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
            self._welle_ziel[m.nummer] = self._frei(self._deckung_nah(p, m, f["feind"], halten=False), m)
            self.stellungen[m.nummer] = self._welle_ziel[m.nummer]

    # ── Igel und Engstelle (seit 0.34.41) ───────────────────────────
    def umzingelt(self, leute) -> bool:
        """Kommen die Gegner von (fast) allen Seiten? Die groesste Luecke
        zwischen ihren Richtungen ist kleiner als `igel_luecke` Grad - wer
        sich schon eingeigelt hat, bleibt es bis `igel_luecke_raus`: sonst
        loeste er den Ring, sobald einer kurz aus dem Blick ist."""
        grenze = K.TRUPP["igel_luecke_raus" if self.zustand == "igel" else "igel_luecke"]
        return self.luecke(leute) < grenze

    def luecke(self, leute) -> float:
        """Die groesste Luecke zwischen den Richtungen, aus denen Gegner
        kommen (Grad); 360, wenn es zu wenige sind."""
        if not leute:
            return 360.0
        ebene = leute[0].ebene
        mitte = sum((pygame.Vector2(m.pos) for m in leute), pygame.Vector2(0, 0)) / len(leute)
        feinde = [o for o, e, _w in self.feinde(ebene)
                  if o.distance_to(mitte) <= K.TRUPP["igel_weite"]]
        if len(feinde) < K.TRUPP["igel_ab"]:
            return 360.0
        winkel = sorted(math.degrees(math.atan2(o.y - mitte.y, o.x - mitte.x)) % 360.0
                        for o in feinde)
        luecken = [b - a for a, b in zip(winkel, winkel[1:])] + [winkel[0] + 360.0 - winkel[-1]]
        return max(luecken)

    def _horde(self, leute) -> bool:
        """Viele, die nur im Nahkampf gefaehrlich sind (Zombies ohne Fernangriff)."""
        nah = [w for w in self.lage if not hasattr(w, "nummer") and not getattr(w, "fern", None)]
        return len(nah) >= max(K.TRUPP["horde_ab"], 2 * len(leute))

    def _igel_platz(self, leute) -> dict:
        """Wo sich der Trupp einigelt: in der Naehe ein Platz, um den herum
        moeglichst viel Deckung steht (ein Hof, eine Ecke zwischen Kisten),
        nicht dicht an einem Gegner. Gemeldet: "wenn es ein Gebiet gibt, was
        von Deckung umgeben ist, dass sie sich da drinnen quasi zurueckziehen
        und eine Art kleine Position aufbauen." """
        t = K.TRUPP
        welt = self.g.welt
        ebene = leute[0].ebene
        mitte = sum((pygame.Vector2(m.pos) for m in leute), pygame.Vector2(0, 0)) / len(leute)
        feinde = [o for o, e, _w in self.feinde(ebene)]
        bestes, beste = pygame.Vector2(mitte), 1e9
        schritt = t["igel_raster"]
        n = int(t["igel_suche"] // schritt)
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                p = mitte + pygame.Vector2(i * schritt, j * schritt)
                if p.distance_to(mitte) > t["igel_suche"]:
                    continue
                if not welt.frei(p, t["igel_platz_frei"], ebene, True):
                    continue
                wert = 0.4 * p.distance_to(mitte) - 55.0 * deckung_ringsum(welt, p, ebene)
                if feinde:
                    nah = min(o.distance_to(p) for o in feinde)
                    if nah < t["igel_feind_abstand"]:
                        wert += 400.0
                if wert < beste:
                    bestes, beste = p, wert
        return dict(ort=bestes, ebene=ebene, bis=self.g.welt.zeit + t["platz_gilt"])

    def _ring(self, leute) -> None:
        """Im Ring um den Platz, jeder schaut nach aussen; der Anfuehrer in
        der Mitte. Die Plaetze nach dem Winkel vergeben, den jeder schon
        hat - so laeuft keiner quer durch den Ring."""
        t = K.TRUPP
        ort = self.igel["ort"]
        andere = [m for m in leute if m is not self.fuehrer]
        if self.fuehrer in leute:
            self.stellungen[self.fuehrer.nummer] = self._frei(ort, self.fuehrer)
        if not andere:
            return
        andere.sort(key=lambda m: math.atan2(m.pos.y - ort.y, m.pos.x - ort.x))
        radius = t["igel_ring"] + t["igel_ring_je"] * len(andere)
        start = math.degrees(math.atan2(andere[0].pos.y - ort.y, andere[0].pos.x - ort.x))
        welt = self.g.welt
        for i, m in enumerate(andere):
            richtung = pygame.Vector2(1, 0).rotate(start + i * 360.0 / len(andere))
            # Steht dort Deckung (darum wurde der Platz ja gewaehlt), naeher
            # zur Mitte in derselben Richtung - nicht irgendwohin daneben,
            # sonst stuenden zwei auf derselben Seite.
            p = None
            # Erst in seiner Richtung, dann ein paar Grad daneben (seit
            # 0.34.50) - sonst schob der Notbehelf ihn irgendwohin, und zwei
            # standen auf derselben Seite. Bis 40 Grad (seit 0.34.52): stand
            # ein Fels genau dort, landete er sonst 70 Grad daneben.
            for drehung in (0.0, 10.0, -10.0, 20.0, -20.0, 30.0, -30.0, 40.0, -40.0):
                for anteil in (1.0, 0.75, 0.5, 0.3):
                    q = ort + richtung.rotate(drehung) * (radius * anteil)
                    if welt.frei(q, m.radius + 2, self.igel["ebene"], True):
                        p = q
                        break
                if p is not None:
                    break
            self.stellungen[m.nummer] = p if p is not None else self._frei(ort + richtung * radius, m)
            self.blicke[m.nummer] = ort + richtung * (radius + 200.0)

    def _engstelle_suchen(self, leute):
        """Eine Engstelle zwischen dem Trupp und der Horde: ein schmaler Durchgang
        (`breite_an`), den sie herkommen muessen. Gehalten wird ein Stueck
        dahinter, auf der eigenen Seite. None, wenn es keine gibt."""
        t = K.TRUPP
        welt = self.g.welt
        ebene = leute[0].ebene
        mitte = sum((pygame.Vector2(m.pos) for m in leute), pygame.Vector2(0, 0)) / len(leute)
        feinde = [o for o, e, w in self.feinde(ebene)]
        if not feinde:
            return None
        feind = sum(feinde, pygame.Vector2(0, 0)) / len(feinde)
        hin = feind - mitte
        if hin.length_squared() < 1.0:
            return None
        richtung = hin.normalize()
        bestes, beste = None, 1e9
        schritt = t["enge_raster"]
        n = int(t["enge_suche"] // schritt)
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                p = mitte + pygame.Vector2(i * schritt, j * schritt)
                vor = (p - mitte).dot(richtung)
                if vor < 0 or p.distance_to(mitte) > t["enge_suche"]:
                    continue
                if (feind - p).dot(richtung) < 0:
                    continue          # hinter den Zombies hilft keine Engstelle
                if not welt.frei(p, 8.0, ebene, True):
                    continue
                breite, achse = breite_an(welt, p, ebene)
                if breite > t["enge_breite"]:
                    continue
                wert = breite + 0.35 * p.distance_to(mitte)
                if wert < beste:
                    bestes, beste = (p, breite, achse), wert
        if bestes is None:
            return None
        p, breite, achse = bestes
        if achse.dot(mitte - p) < 0:
            achse = -achse            # die Achse zeigt zum Trupp
        halte = p + achse * t["enge_abstand"]
        return dict(ort=p, halte=pygame.Vector2(halte), achse=achse, breite=breite,
                    ebene=ebene, bis=self.g.welt.zeit + t["platz_gilt"])

    def _bogen(self, leute) -> None:
        """Hinter der Engstelle im Bogen, alle schauen in den Durchgang -
        so muessen die Zombies einzeln hindurch."""
        t = K.TRUPP
        e = self.enge
        quer = pygame.Vector2(-e["achse"].y, e["achse"].x)
        andere = [m for m in leute if m is not self.fuehrer]
        andere.sort(key=lambda m: (m.pos - e["halte"]).dot(quer))
        n = len(andere)
        for i, m in enumerate(andere):
            seitlich = (i - (n - 1) / 2.0) * t["enge_abstand_quer"]
            # Die Aeusseren etwas weiter vor: ein Bogen um den Durchgang.
            vor = -abs(seitlich) * 0.25
            p = e["halte"] + quer * seitlich + e["achse"] * (-vor)
            self.stellungen[m.nummer] = self._frei(p, m)
            self.blicke[m.nummer] = pygame.Vector2(e["ort"])
        if self.fuehrer in leute:
            self.stellungen[self.fuehrer.nummer] = self._frei(
                e["halte"] + e["achse"] * t["fuehrer_tiefe"] * 0.6, self.fuehrer)
            self.blicke[self.fuehrer.nummer] = pygame.Vector2(e["ort"])

    def blick_fuer(self, k):
        return self.blicke.get(k.nummer)

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
                    # Wer wo ist (seit 0.34.50): das sagt der, der den Spruch
                    # bekommt, seinem Trupp weiter.
                    feinde_orte=[(w, pygame.Vector2(o), e) for w, (o, e, _z) in self.lage.items()],
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
        self.empfangen_zeit = self.g.welt.zeit      # fuer die Anzeige (Testmodus)
        # Der Anfuehrer sagt seinem Trupp, was er ueber Funk gehoert hat -
        # auch das dauert (seit 0.34.50, gemeldet: "Anfuehrer sollen dabei
        # auch Informationen, die sie erhalten haben, an ihren Trupp erstmal
        # weitergeben ueber das Sprechen").
        f = self.fuehrer
        if f is not None and f.lebt and hasattr(f.hirn, "zuruf_starten"):
            feinde = [(w, o, e) for w, o, e in spruch.lage.get("feinde_orte", ()) if w.lebt]
            worte = {"hilfe": "%s BRAUCHT HILFE!", "zusage": "%s KOMMT!", "lage": "FUNK VON %s."}
            f.hirn.zuruf_starten(feinde, worte.get(spruch.art, "FUNK VON %s.") % spruch.trupp.name, funk=True)
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
        jetzt = welt.zeit
        # Auch wen die Leute nur noch erinnern (seit 0.34.50): hinter dem
        # Rauch vergass der Trupp die Gegner nach sechs Sekunden, und dann
        # war es "sicher", bis sie wieder auftauchten.
        orte = [o for o, e, _w in self.feinde(opfer.ebene)]
        for m in leute:
            for w, (o, e, _z) in getattr(m.hirn, "erinnerung", {}).items():
                if e == opfer.ebene and not any(o.distance_to(q) < 40.0 for q in orte):
                    orte.append(pygame.Vector2(o))
        b["orte"] = orte
        n = 0
        for o in orte:
            if (o.distance_to(opfer.pos) <= v["bedrohung"]
                    and sieht_durch_rauch(welt, o, opfer.pos, opfer.ebene)):
                n += 1
        b["bedrohung"] = n
        sicher = (n == 0 or self.zuversicht >= 4
                  or (self.zuversicht >= 2 and n <= max(0, len(leute) - 2)))
        if sicher and not b["sicher"]:
            b["sicher_seit"] = jetzt
            # Warum: weil keiner hinsah (ruhig) - oder nur aus Mut. Zu Ende
            # gebracht wird nur, was ruhig begann; wer es aus Mut anfing,
            # hoert auf, wenn der Mut weg ist.
            b["ruhig"] = n == 0
        # Wer angefangen hat, bringt es zu Ende (seit 0.34.50): vorher brach
        # die Bergung ab, sobald einer hinsah, und die Retter standen neben
        # dem Liegenden im Freien. Nur eine deutlich groessere Bedrohung
        # bricht sie ab.
        # Angefangen ist sie erst, wenn einer zieht oder aufhilft - nicht
        # schon, weil einer neben dem steht, der eben neben ihm fiel.
        laeuft = any(getattr(m, "zieht", None) == opfer.nummer or getattr(m, "hilft", None) == opfer.nummer
                     for m in leute if m.nummer in b["retter"])
        if (not sicher and b["sicher"] and b.get("ruhig") and laeuft and n <= len(leute)
                and jetzt - b.get("sicher_seit", jetzt) < v["dranbleiben"]):
            sicher = True
        b["sicher"] = sicher
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


    def _bergung_deckung(self, leute) -> None:
        """Waehrend einer geborgen wird, bleiben alle anderen in Deckung (seit
        0.34.52): wer gedeckt steht, bleibt dort; wer im Freien steht - etwa
        nach dem Rauchwurf -, geht zur naechsten Deckung. Gemeldet: "alle
        Bots haben ihre Deckung verlassen, um zu bergen ... so viele wie
        moeglich sollen eigentlich in Deckung bleiben." Der Retter selbst
        laeuft los (bot_goap: kamerad_bergen)."""
        b = self.bergung
        if b is None or not b.get("orte"):
            return
        welt = self.g.welt
        v = K.VERWUNDET
        for m in leute:
            if m.nummer in b["retter"] or m.ebene != b["opfer"].ebene:
                continue
            orte = [o for o in b["orte"] if o.distance_to(m.pos) <= v["bedrohung"] * 1.5]
            if not orte:
                continue
            mitte = sum(orte, pygame.Vector2(0, 0)) / len(orte)

            def gedeckt(p):
                return all(welt.deckung(o, p, m.ebene) != "" for o in orte) \
                    and self.gedeckt_hier(p, m.ebene, mitte)

            # Wohin er Feuerschutz gibt (seit 0.34.54): auf den, der dem
            # Liegenden am naechsten ist - der bedroht die Bergung am meisten.
            schuetze = min(orte, key=lambda o: o.distance_to(b["opfer"].pos))
            reicht = K.BOTS["reichweite"].get(m.waffe_name, 300.0)
            lehnen = getattr(m.hirn, "lehnpunkt", None)

            def schiesst(p):
                # Von hier aus kann er sich herauslehnen und trifft ihn auch.
                return (p.distance_to(schuetze) <= reicht and lehnen is not None
                        and lehnen(p, schuetze) is not None)

            def wert(p):
                w = p.distance_to(m.pos)
                if not schiesst(p):
                    w += v["schutz_ohne_schuss"]
                return w

            # Wer gedeckt steht und von dort schiessen kann, bleibt - jeder
            # Schritt waere einer zu viel. Sonst die naechste gedeckte Stelle,
            # lieber eine, von der aus er Feuerschutz geben kann: gemeldet
            # (0.34.54), hinter der langen Mauer sassen sie sicher, konnten
            # aber nicht schiessen, und der Retter wurde abgeschossen.
            kandidaten = []
            if gedeckt(m.pos):
                if schiesst(m.pos):
                    self.stellungen[m.nummer] = pygame.Vector2(m.pos)
                    continue
                kandidaten.append(pygame.Vector2(m.pos))
            alt = self.stellungen_vorher.get(m.nummer)
            if alt is not None and alt.distance_to(m.pos) <= v["halten_radien"][-1] and gedeckt(alt):
                kandidaten.append(pygame.Vector2(alt))
            n = v["halten_richtungen"]
            for r in v["halten_radien"]:
                for i in range(n):
                    p = m.pos + pygame.Vector2(r, 0).rotate(i * 360.0 / n)
                    if not welt.frei(p, m.radius + 2, m.ebene, True):
                        continue
                    p = an_deckung(welt, p, m.radius, m.ebene, mitte)
                    if gedeckt(p):
                        kandidaten.append(p)
            if kandidaten:
                # Die vorige Stelle ein wenig lieber - sonst rueckten sie jeden Takt.
                bestes = min(kandidaten, key=lambda p: wert(p) - (v["schutz_halten"] if alt is not None
                                                                   and p.distance_to(alt) < 1.0 else 0.0))
                self.stellungen[m.nummer] = bestes

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


def an_deckung(welt, p, radius: float, ebene: int, feind):
    """Von einer gedeckten Stelle aus zum Gegner hin bis an das Hindernis:
    so weit, wie die Figur noch frei steht und weiter ganz gedeckt ist (seit
    0.34.52). Wer 30 px hinter einer Kiste steht, ist zwar gedeckt - aber
    er sieht nicht so aus, und von der Seite trifft man ihn eher."""
    p = pygame.Vector2(p)
    hin = pygame.Vector2(feind) - p
    if hin.length_squared() < 1.0:
        return p
    hin = hin.normalize()
    quer = pygame.Vector2(-hin.y, hin.x) * (radius - 2.0)
    schritt = K.TRUPP["anruecken_schritt"]
    for _ in range(int(K.TRUPP["deckung_nah"] * 2 / schritt)):
        q = p + hin * schritt
        if not welt.frei(q, radius + 2.0, ebene, True):     # wie Trupp._frei
            break
        if any(welt.deckung(feind, x, ebene) == "" for x in (q, q + quer, q - quer)):
            break
        p = q
    return p


def deckung_ringsum(welt, p, ebene) -> int:
    """In wie vielen von acht Richtungen steht nah um `p` etwas, das Kugeln
    aufhaelt - ein Mass dafuer, wie gut man sich dort einigeln kann."""
    n = 0
    for i in range(8):
        d = pygame.Vector2(1, 0).rotate(i * 45.0)
        if any(welt.schuss_halt(p + d * r, ebene) for r in K.TRUPP["igel_deckung"]):
            n += 1
    return n


def breite_an(welt, p, ebene):
    """Wie breit ist es an `p`? (schmalste Breite, Achse des Durchgangs).
    Gemessen in vier Richtungen bis zur naechsten Wand oder Kiste; die
    Achse steht quer zur schmalsten Richtung. Ein Durchgang muss in
    Richtung seiner Achse weit offen sein - sonst ist es eine Sackgasse."""
    schritt = 6.0
    weit = K.TRUPP["enge_offen"]

    def frei_bis(d):
        s = 0.0
        while s < weit:
            if not welt.frei(p + d * (s + schritt), 6.0, ebene, True):
                return s
            s += schritt
        return weit

    beste, achse = 1e9, pygame.Vector2(1, 0)
    for winkel in (0.0, 45.0, 90.0, 135.0):
        d = pygame.Vector2(1, 0).rotate(winkel)
        breite = frei_bis(d) + frei_bis(-d)
        if breite < beste:
            beste, achse = breite, pygame.Vector2(-d.y, d.x)
    if frei_bis(achse) + frei_bis(-achse) < 2 * weit - 2 * schritt:
        return 1e9, achse              # kein Durchgang, eine Sackgasse
    return beste, achse


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
