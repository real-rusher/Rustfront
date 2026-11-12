"""
DUSTFRONT - Die Front in SCHLACHT (seit 0.34.131)
================================================

Gewuenscht: "Hot Zones an verschiedenen Punkten der Map, die, wenn
eingenommen, keine Punkte bringen, sondern dafuer sorgen, dass Teammates
und Bots dort im Umkreis respawnen koennen" - mit einer Karte nach dem Tod
wie in Battlefield. Und die Bots sollen nicht mehr alle in die Mitte laufen,
sondern "sich an verschiedenen Punkten treffen", in kleinen Gruppen (auch
mal einer oder zwei), in Formationen, auf verschiedenen Wegen, flankieren -
"viel mehr wie eine Front", und so einsteigen, dass sie "von allen Seiten
angreifen" und nicht alle an einem Punkt.

Eine Karte mit Front nennt im Kopf ihre Basen, Punkte und Wege (siehe
werkzeug_schlachtkarte.py); daraus wird hier ein `Schlachtplan`. Ohne diese
Zeilen (STAUBTAL) bleibt alles wie vorher.

**Punkte**: Stand von -1 (ganz ROT) bis +1 (ganz BLAU). Wer allein (oder in
der Mehrheit) im Kreis steht, zieht den Stand zu sich; ueber 0 wird der
Punkt neutral, am Ende gehoert er der Seite. Ein Punkt bringt keine Zaehler,
nur den Einstieg - solange kein Gegner in der Naehe ist.

**Einstieg**: Menschen waehlen auf der Karte (front_karte.py), Bots bekommen
von ihrer Front ein Ziel und steigen dort ein, wo sie es gut erreichen -
mit Aufschlag fuer jeden, der schon von dort zu diesem Ziel ging. So kommt
auch einer vom weiter entfernten Einstieg, und das Ziel wird von mehreren
Seiten angegangen.

**Gruppen**: Die Front einer Seite plant alle `takt` Sekunden: welche Punkte
angegriffen, welche verteidigt, welche gehalten werden, und wie viele Bots
jeder braucht. Jede Gruppe nimmt einen Weg durch das Wegenetz der Karte; eine
Kante, die schon eine andere Gruppe zum selben Ziel nimmt, kostet mehr - so
flankieren sie. Unterwegs geht der Anfuehrer vorn, die anderen in ihrer
Formation (Keil, Linie, Reihe, Staffel, Raute); wo der Platz in der Formation
nicht frei ist (Wald, Haeuser), gehen sie auf seiner Spur. Was ein Bot tut,
wenn er einen Gegner sieht, entscheidet weiter sein eigenes Hirn.
"""

from __future__ import annotations

import heapq
import math
import random
from collections import deque

import pygame

from . import config as K

F = K.FRONT

FORMATIONEN = {
    # Plaetze hinter dem Anfuehrer: (nach vorn, nach rechts) in form_abstand.
    "paar":    ((-0.6, 1.0),),
    "keil":    ((-1.0, -1.0), (-1.0, 1.0), (-2.0, -2.0)),
    "linie":   ((0.0, -1.2), (0.0, 1.2), (0.0, -2.4)),
    "reihe":   ((-1.0, 0.0), (-2.0, 0.0), (-3.0, 0.0)),
    "staffel": ((-0.8, 1.0), (-1.6, 2.0), (-2.4, 3.0)),
    "raute":   ((-1.0, -1.0), (-1.0, 1.0), (-2.0, 0.0)),
}
FORM_WAHL = {1: ("reihe",), 2: ("paar", "reihe", "paar"), 3: ("keil", "linie", "reihe", "staffel"),
             4: ("keil", "raute", "linie", "staffel", "reihe")}
# Wohin jemand auf welchem Platz schaut, waehrend sie gehen (Grad zur Gehrichtung).
SEKTOREN = (0.0, -55.0, 55.0, 160.0)


def _pixel(tx: float, ty: float) -> pygame.Vector2:
    return pygame.Vector2(float(tx) * K.TILE + K.TILE / 2, float(ty) * K.TILE + K.TILE / 2)


class Basis:
    def __init__(self, nr: int, team: int, pos, name: str, fahrzeuge: list) -> None:
        self.nr, self.team, self.pos, self.name = nr, team, pos, name
        self.fahrzeuge = fahrzeuge          # [(Art, Anzahl, Stufe)]
        self.knoten = -1


class Punkt:
    def __init__(self, nr: int, pos, name: str) -> None:
        self.nr, self.pos, self.name = nr, pos, name
        self.stand = 0.0                    # -1 ganz ROT ... +1 ganz BLAU
        self.besitzer = -1
        self.da = [0, 0]                    # wer gerade im Kreis steht (je Seite)
        self.knoten = -1
        self.buchstabe = "?"

    def gehoert(self, team: int) -> bool:
        """Ganz eingenommen von dieser Seite?"""
        return self.besitzer == team and abs(self.stand) >= 0.999

    @property
    def anteil(self) -> float:
        return abs(self.stand)

    @property
    def zieht(self) -> int:
        """Zu welcher Seite der Stand gerade steht (-1: genau neutral)."""
        if self.stand < -1e-3:
            return 0
        if self.stand > 1e-3:
            return 1
        return -1


class Schlachtplan:
    """Was die Karte ueber ihre Front sagt: Basen, Punkte, Wegenetz."""

    def __init__(self) -> None:
        self.basen: list = []
        self.punkte: list = []
        self.knoten: list = []
        self.kanten: dict = {}
        self.fahrer = int(F["fahrer"])

    @staticmethod
    def lesen(kopf: dict):
        """Aus dem Kopf einer Kartendatei, oder None ohne Front. Nichts
        daran wirft: eine verdrehte Zeile kostet nur diese Zeile."""
        plan = Schlachtplan()
        wege = []
        for schluessel in sorted(kopf, key=_nach_nummer):
            wert = str(kopf[schluessel])
            try:
                if schluessel.startswith("basis"):
                    links, _, rechts = wert.partition("|")
                    team, tx, ty, name = links.split(None, 3)
                    fz = []
                    for teil in rechts.split(","):
                        bits = teil.split()
                        if len(bits) >= 2:
                            fz.append((bits[0], int(bits[1]), int(bits[2]) if len(bits) > 2 else 0))
                    plan.basen.append(Basis(len(plan.basen), int(team), _pixel(tx, ty),
                                            name.strip(), fz))
                elif schluessel.startswith("punkt"):
                    tx, ty, name = wert.split(None, 2)
                    plan.punkte.append(Punkt(len(plan.punkte), _pixel(tx, ty), name.strip()))
                elif schluessel.startswith("weg"):
                    wege.append([_pixel(*q.split(",")) for q in wert.split()])
            except (TypeError, ValueError):
                continue
        try:
            plan.fahrer = int(kopf.get("fahrer", F["fahrer"]))
        except (TypeError, ValueError):
            pass
        if not plan.punkte and not plan.basen:
            return None
        # Buchstaben in Lesereihenfolge: Zeile fuer Zeile (ein Drittel der
        # Kartenhoehe), darin von West nach Ost - wie A B C in Battlefield.
        if plan.punkte:
            hoch = max(p.pos.y for p in plan.punkte) + 1.0
            for i, p in enumerate(sorted(plan.punkte, key=lambda p: (int(3 * p.pos.y / hoch), p.pos.x))):
                p.buchstabe = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[i % 26]
        plan._netz_bauen(wege)
        return plan

    # ---- Wegenetz -----------------------------------------------------------
    def _knoten_fuer(self, p) -> int:
        nah = F["knoten_zusammen"]
        for i, q in enumerate(self.knoten):
            if q.distance_to(p) <= nah:
                return i
        self.knoten.append(pygame.Vector2(p))
        self.kanten[len(self.knoten) - 1] = []
        return len(self.knoten) - 1

    def _verbinden(self, a: int, b: int) -> None:
        if a == b:
            return
        d = self.knoten[a].distance_to(self.knoten[b])
        if all(j != b for j, _ in self.kanten[a]):
            self.kanten[a].append((b, d))
            self.kanten[b].append((a, d))

    def _netz_bauen(self, wege) -> None:
        for weg in wege:
            vorher = None
            for p in weg:
                i = self._knoten_fuer(p)
                if vorher is not None:
                    self._verbinden(vorher, i)
                vorher = i
        # Punkte und Basen haengen am naechsten Knoten (oder sind selbst einer).
        for ding in list(self.punkte) + list(self.basen):
            nah = min(range(len(self.knoten)), key=lambda i: self.knoten[i].distance_squared_to(ding.pos),
                      default=None)
            if nah is not None and self.knoten[nah].distance_to(ding.pos) <= F["knoten_zusammen"]:
                ding.knoten = nah
                continue
            i = len(self.knoten)
            self.knoten.append(pygame.Vector2(ding.pos))
            self.kanten[i] = []
            ding.knoten = i
            if nah is not None and self.knoten[nah].distance_to(ding.pos) <= F["punkt_anschluss"]:
                self._verbinden(i, nah)
            # Ohne Anschluss: an die zwei naechsten Knoten, damit nichts allein steht.
            if not self.kanten[i]:
                for j in sorted(range(i), key=lambda j: self.knoten[j].distance_squared_to(ding.pos))[:2]:
                    self._verbinden(i, j)

    def naechster_knoten(self, pos) -> int:
        return min(range(len(self.knoten)), key=lambda i: self.knoten[i].distance_squared_to(pos))

    def entfernungen(self, start: int) -> dict:
        """Kuerzeste Wege von einem Knoten zu allen (Dijkstra, klein)."""
        dist = {start: 0.0}
        offen = [(0.0, start)]
        while offen:
            d, i = heapq.heappop(offen)
            if d > dist.get(i, 1e18):
                continue
            for j, laenge in self.kanten.get(i, ()):
                nd = d + laenge
                if nd < dist.get(j, 1e18):
                    dist[j] = nd
                    heapq.heappush(offen, (nd, j))
        return dist

    def weg(self, von: int, nach: int, kosten=None) -> list:
        """Knotenfolge von `von` nach `nach`; `kosten(i, j, laenge)` darf
        Kanten verteuern (flankieren)."""
        dist = {von: 0.0}
        vor = {}
        offen = [(0.0, von)]
        while offen:
            d, i = heapq.heappop(offen)
            if i == nach:
                break
            if d > dist.get(i, 1e18):
                continue
            for j, laenge in self.kanten.get(i, ()):
                nd = d + (kosten(i, j, laenge) if kosten is not None else laenge)
                if nd < dist.get(j, 1e18):
                    dist[j] = nd
                    vor[j] = i
                    heapq.heappush(offen, (nd, j))
        if nach not in dist:
            return [von, nach]
        folge = [nach]
        while folge[-1] != von:
            folge.append(vor[folge[-1]])
        return folge[::-1]


def _nach_nummer(schluessel: str):
    ziffern = "".join(c for c in schluessel if c.isdigit())
    return (schluessel.rstrip("0123456789"), int(ziffern) if ziffern else 0)


class Gruppe:
    """Ein paar Bots, die zusammen gehen: Anfuehrer vorn, Formation, Weg."""

    zaehler = 0

    def __init__(self, team: int, ziel, rnd) -> None:
        Gruppe.zaehler += 1
        self.nr = Gruppe.zaehler
        self.team = team
        self.ziel = ziel                    # ("punkt", Nr) oder ("basis", Nr)
        self.mitglieder: list = []
        self.weg: list = []                 # Wegpunkte (Vector2) bis zum Ziel
        self.kanten: list = []              # (i, j) des Weges, fuer das Flankieren
        self.schritt = 0
        self.form = "keil"
        self.spur: deque = deque(maxlen=24)
        self.richtung = pygame.Vector2(1, 0)
        self.sammeln_bis = 0.0
        self.soll = 3
        self.halten_seit = -1.0
        self.halten_bis = 0.0
        self.kampf_pause = 0.0
        self.umweg = None
        self.ring_winkel = rnd.uniform(0.0, 360.0)
        self.einstieg = None                # Kennung des Einstiegs, von dem sie kam

    def lebende(self) -> list:
        return [m for m in self.mitglieder
                if m.lebt and not getattr(m, "am_boden", False) and m.fahrzeug is None]

    def fuehrer(self):
        leute = self.lebende()
        return leute[0] if leute else None

    @property
    def am_ziel(self) -> bool:
        return self.schritt >= len(self.weg)


class FrontTeil:
    """Was das Gefecht fuer die Front tut. Ein Anteil wie SchlachtTeil."""

    # ---- Plan der Karte -------------------------------------------------------
    @property
    def schlachtplan(self):
        """Der Plan der Karte (gemerkt je Welt), oder None."""
        w = self.welt
        if w is None:
            return None
        if "_schlachtplan" not in w.__dict__:
            w._schlachtplan = Schlachtplan.lesen(getattr(self, "karte_kopf", {}) or {})
        return w._schlachtplan

    @property
    def front_an(self) -> bool:
        """Gilt die Front? In SCHLACHT auf einer Karte mit Plan (oder im
        Testmodus, wenn er sie einschaltet)."""
        an = self.schlacht or bool(self.__dict__.get("front_test"))
        return an and self.schlachtplan is not None and not self.in_lobby

    def front_punkte(self) -> list:
        plan = self.schlachtplan
        return plan.punkte if plan is not None else []

    def front_basen(self, team: int = -1) -> list:
        plan = self.schlachtplan
        if plan is None:
            return []
        return [b for b in plan.basen if team < 0 or b.team == team]

    def hauptbasis(self, team: int):
        """Die Basis, an der man ohne Wahl einsteigt: die der Kartenmitte
        am naechsten (die Hauptlager)."""
        basen = self.front_basen(team)
        if not basen:
            return None
        e = self.welt.ebene(0)
        mitte_y = e.pixel_hoehe / 2.0
        return min(basen, key=lambda b: abs(b.pos.y - mitte_y))

    def front_anlegen(self) -> None:
        """Zu Rundenbeginn: alle Punkte neutral, keine Gruppen."""
        for p in self.front_punkte():
            p.stand, p.besitzer, p.da = 0.0, -1, [0, 0]
        self.__dict__.pop("_gruppen", None)
        self.front_zustand()

    def front_zustand(self) -> None:
        """Was die Front sich merkt, wenn es das noch nicht gibt - ohne die
        Punkte anzufassen (der Testmodus setzt sie vorher)."""
        if "_gruppen" in self.__dict__:
            return
        self._gruppen = []
        self._front_rest = [0.0, 0.0]
        self._front_plan = {0: {}, 1: {}}
        self._einstieg_zahl = {}
        self._front_rnd = random.Random(getattr(self, "_bot_seed", None) or 4711)

    # ---- Punkte einnehmen (Gastgeber) -------------------------------------------
    def front_schritt(self, dt: float) -> None:
        if not self.front_an or not self.ist_gastgeber:
            return
        self.front_zustand()
        # Die Kreise zehnmal je Sekunde (seit 0.34.131 gemessen: jeden Schritt
        # alle Kaempfer gegen alle Punkte war ein Zwanzigstel des Schritts).
        self._kreis_rest = self.__dict__.get("_kreis_rest", 0.0) + dt
        if self._kreis_rest >= 0.1:
            self._punkte_einnehmen(self._kreis_rest)
            self._kreis_rest = 0.0
        for team in (0, 1):
            self._front_rest[team] -= dt
            if self._front_rest[team] <= 0.0:
                self._front_rest[team] = F["takt"] + 0.1 * team
                self._front_planen(team)

    def _zaehlbar(self) -> list:
        """Wer in einem Kreis zaehlt: lebt, steht, unten; wer faehrt, auch."""
        raus = []
        for k in self.kaempfer.values():
            if not k.lebt or getattr(k, "am_boden", False) or int(k.ebene) != 0:
                continue
            if not 0 <= k.team < 2 or getattr(k, "raus", False):
                continue
            if getattr(k, "schirm_hoehe", 0.0) > 0.0:
                continue                       # am Fallschirm zaehlt er noch nicht
            raus.append(k)
        return raus

    def _im_kreis(self, p, leute=None) -> list:
        """Wer wie viele im Kreis hat: [ROT, BLAU]."""
        da = [0, 0]
        r2 = F["radius"] ** 2
        for k in (self._zaehlbar() if leute is None else leute):
            if k.pos.distance_squared_to(p.pos) <= r2:
                da[k.team] += 1
        return da

    def _punkte_einnehmen(self, dt: float) -> None:
        leute = self._zaehlbar()
        for p in self.front_punkte():
            da = self._im_kreis(p, leute)
            p.da = da
            vorher = p.besitzer
            mehr = da[1] - da[0]
            if mehr != 0:
                n = abs(mehr)
                tempo = min(F["hoechstens"], 1.0 + F["mehr"] * (n - 1)) / F["zeit"]
                p.stand = max(-1.0, min(1.0, p.stand + (tempo if mehr > 0 else -tempo) * dt))
            elif da[0] == 0 and da[1] == 0:
                # Niemand da: zurueck zum Besitzer (oder zur Mitte, wenn neutral).
                soll = 0.0 if p.besitzer < 0 else (-1.0 if p.besitzer == 0 else 1.0)
                schritt = F["zurueck"] * dt
                p.stand += max(-schritt, min(schritt, soll - p.stand))
            if p.stand <= -1.0 + 1e-6:
                p.stand, p.besitzer = -1.0, 0
            elif p.stand >= 1.0 - 1e-6:
                p.stand, p.besitzer = 1.0, 1
            elif p.besitzer == 0 and p.stand > 0.0 or p.besitzer == 1 and p.stand < 0.0:
                p.besitzer = -1
            if p.besitzer != vorher:
                self._punkt_wechsel(p, vorher)

    def _punkt_wechsel(self, p, vorher: int) -> None:
        """Ein Punkt hat den Besitzer gewechselt: Klang und Meldung."""
        if p.besitzer >= 0:
            self.welt.klang("aufheben", 0.9, p.pos, 0)
            name = K.TEAMS["namen"][p.besitzer]
            self.__dict__.setdefault("_front_meldungen", []).append(
                (self.welt.zeit, "%s NIMMT %s" % (name, p.name), p.besitzer))
        elif vorher >= 0:
            self.__dict__.setdefault("_front_meldungen", []).append(
                (self.welt.zeit, "%s VERLIERT %s" % (K.TEAMS["namen"][vorher], p.name), vorher))
        del self.__dict__["_front_meldungen"][:-4]

    def umkaempft(self, p, team: int) -> bool:
        """Steht ein Gegner von `team` nahe am Punkt?"""
        weit2 = F["umkaempft"] ** 2
        for k in self.kaempfer.values():
            if (k.lebt and 0 <= k.team < 2 and k.team != team and int(k.ebene) == 0
                    and k.pos.distance_squared_to(p.pos) <= weit2):
                return True
        return False

    # ---- Netz: Stand der Punkte -----------------------------------------------
    def front_meldung(self) -> list:
        return [[p.besitzer, int(round(p.stand * 1000)), p.da[0], p.da[1]]
                for p in self.front_punkte()]

    def front_uebernehmen(self, liste) -> None:
        """Beim Gast: der Stand der Punkte aus der Weltmeldung. Ein Wechsel
        des Besitzers klingt und steht oben - wie beim Gastgeber, nur nicht
        bei der allerersten Meldung (sonst meldete jeder Beitritt alles)."""
        punkte = self.front_punkte()
        if not isinstance(liste, list):
            return
        erste = "_front_gesehen" not in self.__dict__
        for p, eintrag in zip(punkte, liste):
            try:
                alt = p.besitzer
                p.besitzer = int(eintrag[0])
                p.stand = max(-1.0, min(1.0, int(eintrag[1]) / 1000.0))
                p.da = [int(eintrag[2]), int(eintrag[3])]
                if p.besitzer != alt and not erste:
                    self._punkt_wechsel(p, alt)
            except (TypeError, ValueError, IndexError):
                continue
        self._front_gesehen = True

    # ---- Einstiege ------------------------------------------------------------
    def einstiege(self, team: int) -> list:
        """Alle Einstiege dieser Seite: [(Kennung, Ort, Name, frei, Grund)].
        Basen sind immer frei; ein Punkt nur, wenn er ganz der Seite gehoert
        und kein Gegner nah ist."""
        raus = []
        for b in self.front_basen(team):
            raus.append(("b%d" % b.nr, b.pos, b.name, True, ""))
        for p in self.front_punkte():
            if p.besitzer != team:
                continue
            if not p.gehoert(team):
                raus.append(("p%d" % p.nr, p.pos, p.name, False, "WIRD EINGENOMMEN"))
            elif self.umkaempft(p, team):
                raus.append(("p%d" % p.nr, p.pos, p.name, False, "UMKÄMPFT"))
            else:
                raus.append(("p%d" % p.nr, p.pos, p.name, True, ""))
        return raus

    def einstieg_ort_von(self, kennung: str):
        if not kennung:
            return None
        try:
            nr = int(kennung[1:])
        except ValueError:
            return None
        plan = self.schlachtplan
        if plan is None:
            return None
        if kennung[0] == "b" and 0 <= nr < len(plan.basen):
            return plan.basen[nr].pos
        if kennung[0] == "p" and 0 <= nr < len(plan.punkte):
            return plan.punkte[nr].pos
        return None

    def einstieg_vorgabe(self, team: int) -> str:
        b = self.hauptbasis(team)
        return "b%d" % b.nr if b is not None else ""

    def front_einstiegsort(self, k) -> pygame.Vector2:
        """Wo `k` einsteigt: ein Mensch an seinem gewaehlten Einstieg (wenn
        er noch frei ist, sonst an der Hauptbasis), ein Bot dort, wo ihn
        seine Front hinschickt."""
        team = k.team
        frei = {kenn: (ort, kenn[0]) for kenn, ort, _n, ok, _g in self.einstiege(team) if ok}
        if getattr(k, "ist_bot", False):
            kennung = self._bot_einstieg(k, frei)
        else:
            kennung = str(getattr(k, "einstieg_wahl", "") or "")
            if kennung not in frei:
                kennung = self.einstieg_vorgabe(team)
        k.einstieg_zuletzt = kennung
        ort = self.einstieg_ort_von(kennung)
        if ort is None:
            basis = self.schlacht_basis(team)
            ort = basis if basis is not None else pygame.Vector2(self.welt.ebene(0).pixel_breite / 2,
                                                                    self.welt.ebene(0).pixel_hoehe / 2)
        umkreis = F["basis_umkreis"] if kennung.startswith("b") else F["einstieg_umkreis"]
        return self._platz_um(ort, umkreis, k)

    def _platz_um(self, ort, umkreis: float, k) -> pygame.Vector2:
        rnd = self.rnd
        fremde = [x.pos for x in self.kaempfer.values()
                  if x.lebt and x is not k and x.team != k.team]
        for versuch in range(60):
            weit = umkreis * (0.3 + 0.7 * min(1.0, versuch / 20.0))
            p = ort + pygame.Vector2(rnd.uniform(-1.0, 1.0), rnd.uniform(-1.0, 1.0)) * weit
            if not self.welt.frei(p, 13.0, 0, True):
                continue
            if self.welt.wege.braucht_weg(0, p, 0, ort) and versuch < 40:
                # Nicht hinter einer Mauer, von der aus der Weg zum Ort weit ist.
                if not self.welt.wege.gerade_frei(0, p, ort, 10.0):
                    continue
            if min((p.distance_to(q) for q in fremde), default=9999.0) < 140.0:
                continue
            return p
        from .world import freier_punkt
        return freier_punkt(self.welt, 0, rnd, ort, 0.0) if not self.welt.frei(ort, 13.0, 0, True) \
            else pygame.Vector2(ort)

    # ---- Die Front einer Seite planen (Gastgeber) ---------------------------------
    def _front_ziele(self, team: int) -> list:
        """Was diese Seite gerade will: [(Ziel, Gewicht)], Ziel ("punkt", Nr)
        oder ("basis", Nr)."""
        plan = self.schlachtplan
        punkte = plan.punkte
        # Wie weit jeder Knoten von den eigenen Einstiegen ist (ueber das Netz).
        eigen = [b.knoten for b in self.front_basen(team)] + \
                [p.knoten for p in punkte if p.gehoert(team)]
        nah = {}
        for start in eigen:
            for i, d in plan.entfernungen(start).items():
                if d < nah.get(i, 1e18):
                    nah[i] = d
        ziele = []
        offen = [p for p in punkte if p.besitzer != team]
        vorstoss = set()
        if offen:
            naechster = min(nah.get(p.knoten, 1e9) for p in offen)
            bots = sum(1 for k in self.kaempfer.values() if k.team == team and getattr(k, "ist_bot", False))
            for p in offen:
                d = nah.get(p.knoten, 1e9)
                if d <= naechster * F["front_faktor"] + 300.0:
                    w = F["gewicht_angriff"] * (1.25 if p.besitzer < 0 else 1.0)
                    ziele.append((("punkt", p.nr), w))
                elif bots >= F["vorstoss_ab"]:
                    # Hinter der Front: ein Vorstoss fuer einen kleinen Trupp
                    # (seit 0.34.133) - Unruhe im Ruecken des Gegners.
                    ziele.append((("punkt", p.nr), F["gewicht_vorstoss"]))
                    vorstoss.add(("punkt", p.nr))
        else:
            for b in self.front_basen(1 - team):
                ziele.append((("basis", b.nr), F["gewicht_basis"]))
        self.__dict__.setdefault("_vorstoss_ziele", {})[team] = vorstoss
        bedroht2 = F["bedroht"] ** 2
        feinde = [k.pos for k in self.kaempfer.values()
                  if k.lebt and 0 <= k.team < 2 and k.team != team and int(k.ebene) == 0]
        for p in punkte:
            if p.besitzer != team:
                continue
            if any(q.distance_squared_to(p.pos) <= bedroht2 for q in feinde) or not p.gehoert(team):
                ziele.append((("punkt", p.nr), F["gewicht_bedroht"]))
            elif any(nah.get(q.knoten, 1e9) <= nah.get(p.knoten, 0) + 2600.0 for q in offen):
                ziele.append((("punkt", p.nr), F["gewicht_halten"]))
        return ziele

    def _ziel_ort(self, ziel):
        plan = self.schlachtplan
        art, nr = ziel
        if art == "punkt" and 0 <= nr < len(plan.punkte):
            return plan.punkte[nr].pos, plan.punkte[nr].knoten
        if art == "basis" and 0 <= nr < len(plan.basen):
            return plan.basen[nr].pos, plan.basen[nr].knoten
        return None, -1

    def _front_planen(self, team: int) -> None:
        """Alle `takt` Sekunden: Gruppen aufraeumen, Ziele gewichten, wer
        keine Gruppe hat, bekommt eine, und wessen Ziel erledigt ist, ein
        neues."""
        jetzt = self.welt.zeit
        gruppen = [g for g in self._gruppen if g.team == team]
        for g in gruppen:
            g.mitglieder = [m for m in g.mitglieder if m.lebt and self.kaempfer.get(m.nummer) is m
                            and m.team == team]
            if not g.mitglieder:
                self._gruppen.remove(g)
        gruppen = [g for g in self._gruppen if g.team == team]
        ziele = self._front_ziele(team)
        self._front_plan[team] = dict(ziele)
        gueltig = {z for z, _w in ziele}
        bots = [k for k in self.kaempfer.values()
                if k.team == team and getattr(k, "ist_bot", False) and k.lebt
                and not getattr(k, "verstaerkung", False)]
        # Ein erledigtes Ziel: neues fuer die Gruppe.
        for g in gruppen:
            if g.ziel not in gueltig and jetzt >= g.sammeln_bis:
                self._gruppe_neu_planen(g, ziele)
            elif g.am_ziel and g.halten_seit >= 0.0 and jetzt >= g.halten_bis:
                art, nr = g.ziel
                if art == "punkt" and self.schlachtplan.punkte[nr].gehoert(team) \
                        and self._front_plan[team].get(g.ziel, 0.0) < F["gewicht_bedroht"]:
                    self._gruppe_neu_planen(g, ziele, ausser=g.ziel)
        # Wer zu Fuss und ohne Gruppe ist (Rundenbeginn, ausgestiegen): in
        # eine nahe Gruppe mit Platz, sonst eine neue mit den Naechsten.
        in_gruppe = {id(m) for g in self._gruppen for m in g.mitglieder}
        ohne = [k for k in bots if id(k) not in in_gruppe and k.fahrzeug is None
                and not getattr(k, "am_boden", False)]
        rnd = self._front_rnd
        while ohne:
            k = ohne.pop(0)
            beste = None
            for g in self._gruppen:
                f = g.fuehrer()
                if g.team != team or f is None or len(g.mitglieder) >= g.soll:
                    continue
                if f.pos.distance_to(k.pos) < 260.0 and (beste is None or len(g.mitglieder) < len(beste.mitglieder)):
                    beste = g
            if beste is not None:
                beste.mitglieder.append(k)
                continue
            g = self._gruppe_bilden(team, ziele, k.pos, rnd)
            g.mitglieder.append(k)
            for x in sorted(ohne, key=lambda x: x.pos.distance_squared_to(k.pos)):
                if len(g.mitglieder) >= g.soll or x.pos.distance_to(k.pos) > 320.0:
                    break
                g.mitglieder.append(x)
                ohne.remove(x)

    def _groesse(self, rnd) -> int:
        t = rnd.random()
        for n, anteil in F["gruppen"]:
            t -= anteil
            if t <= 0.0:
                return n
        return F["gruppen"][-1][0]

    def _bedarf(self, team: int, ziele, ausser=None):
        """Das Ziel, dem am meisten Bots fehlen (nach seinem Gewicht)."""
        if not ziele:
            return None
        zahl = {}
        for g in self._gruppen:
            if g.team == team:
                zahl[g.ziel] = zahl.get(g.ziel, 0) + max(1, len(g.mitglieder))
        bots = sum(1 for k in self.kaempfer.values()
                   if k.team == team and getattr(k, "ist_bot", False))
        summe = sum(w for _z, w in ziele) or 1.0
        bestes, fehlt = None, -1e9
        # Kein Ziel bekommt mehr als ziel_anteil der Bots (seit 0.34.133),
        # solange es andere gibt - sonst laufen alle zum wichtigsten.
        deckel = max(2.0, bots * F["ziel_anteil"]) if len(ziele) >= 3 else bots
        for z, w in ziele:
            if z == ausser and len(ziele) > 1:
                continue
            soll = min(deckel, bots * w / summe)
            f = soll - zahl.get(z, 0) + self._front_rnd.uniform(0.0, 0.6)
            if f > fehlt:
                bestes, fehlt = z, f
        return bestes

    def _gruppe_bilden(self, team: int, ziele, wo, rnd, einstieg=None):
        ziel = self._bedarf(team, ziele)
        if ziel is None:
            feind = self.front_basen(1 - team)
            ziel = ("basis", feind[0].nr) if feind else ("punkt", 0)
        g = Gruppe(team, ziel, rnd)
        g.soll = self._groesse(rnd)
        if ziel in self.__dict__.get("_vorstoss_ziele", {}).get(team, ()):
            g.soll = min(g.soll, 2)               # ein Stosstrupp: einer oder zwei
        g.form = rnd.choice(FORM_WAHL.get(g.soll, ("keil",)))
        g.einstieg = einstieg
        self._weg_planen(g, wo)
        self._gruppen.append(g)
        return g

    def _gruppe_neu_planen(self, g, ziele, ausser=None) -> None:
        neu = self._bedarf(g.team, ziele, ausser)
        if neu is None:
            return
        g.ziel = neu
        g.halten_seit = -1.0
        g.umweg = None
        f = g.fuehrer()
        self._weg_planen(g, f.pos if f is not None else self._ziel_ort(neu)[0])

    def _weg_planen(self, g, wo) -> None:
        """Ein Weg durch das Netz zum Ziel - Kanten, die andere Gruppen zum
        selben Ziel schon nehmen, kosten mehr (so kommen sie von mehreren
        Seiten), dazu etwas Zufall je Gruppe."""
        plan = self.schlachtplan
        ort, ziel_knoten = self._ziel_ort(g.ziel)
        if ort is None:
            g.weg, g.kanten, g.schritt = [], [], 0
            return
        start = plan.naechster_knoten(wo)
        benutzt = {}
        for x in self._gruppen:
            if x is not g and x.team == g.team and x.ziel == g.ziel:
                for kante in x.kanten:
                    benutzt[kante] = benutzt.get(kante, 0) + 1
        rnd = self._front_rnd
        zufall = {}

        def kosten(i, j, laenge):
            schl = (min(i, j), max(i, j))
            if schl not in zufall:
                zufall[schl] = rnd.uniform(0.85, 1.25)
            return laenge * zufall[schl] * (1.0 + F["weg_teilen"] * benutzt.get(schl, 0))
        folge = plan.weg(start, ziel_knoten, kosten)
        g.kanten = [(min(a, b), max(a, b)) for a, b in zip(folge, folge[1:])]
        punkte = [pygame.Vector2(plan.knoten[i]) for i in folge]
        # Der erste Knoten liegt oft hinter einem: weglassen, wenn der zweite naeher ist.
        if len(punkte) >= 2 and pygame.Vector2(wo).distance_to(punkte[1]) < punkte[0].distance_to(punkte[1]):
            punkte = punkte[1:]
        # Der letzte Wegpunkt: vor dem Ziel, aus der Richtung, aus der sie kommen.
        if len(punkte) >= 2:
            her = punkte[-2] - ort
        else:
            her = pygame.Vector2(wo) - ort
        if her.length_squared() < 1.0:
            her = pygame.Vector2(1, 0)
        her = her.normalize().rotate(rnd.uniform(-40.0, 40.0)) * rnd.uniform(*F["anflug"])
        anflug = ort + her
        if self.welt.frei(anflug, 12.0, 0, True):
            punkte = punkte[:-1] + [anflug, pygame.Vector2(ort)]
        g.weg = punkte
        g.schritt = 0

    # ---- Einstieg der Bots ---------------------------------------------------
    def _bot_einstieg(self, k, frei: dict) -> str:
        """Ziel fuer den Bot, dann der Einstieg dazu: der naechste am Ziel -
        mit Aufschlag fuer jeden, der von dort schon zu diesem Ziel ging,
        und nie einer, der viel weiter ist als der naechste. So kommen sie
        von mehreren Seiten."""
        team = k.team
        self.front_zustand()
        if getattr(k, "darf_fahren", False):
            kenn = self._fahrer_basis(k, frei)
            if kenn is not None:
                k._front_einstieg = kenn
                return kenn
        ziele = list(self._front_plan.get(team, {}).items()) or self._front_ziele(team)
        ziel = self._bedarf(team, ziele)
        if not frei:
            return self.einstieg_vorgabe(team)
        if ziel is None:
            return min(frei, key=lambda kenn: self._front_rnd.random())
        ort, _knoten = self._ziel_ort(ziel)
        plan = self.schlachtplan
        abstaende = {}
        ziel_dist = plan.entfernungen(plan.naechster_knoten(ort))
        for kenn, (pos, _art) in frei.items():
            abstaende[kenn] = ziel_dist.get(plan.naechster_knoten(pos), pos.distance_to(ort) * 1.5) + 200.0
        naechster = min(abstaende.values())
        zahl = self._einstieg_zahl.setdefault((team, ziel), {})
        beste, wert = None, 1e18
        for kenn, d in abstaende.items():
            if d > naechster * F["einstieg_weit"]:
                continue
            w = d * (1.0 + F["einstieg_last"] * zahl.get(kenn, 0)) * self._front_rnd.uniform(0.9, 1.1)
            if w < wert:
                beste, wert = kenn, w
        zahl[beste] = zahl.get(beste, 0) + 1
        # Die Zaehlung altert: nur, wer zuletzt von dort ging, zaehlt.
        if sum(zahl.values()) > 8:
            for kenn in list(zahl):
                zahl[kenn] = max(0, zahl[kenn] - 1)
        k._front_ziel = ziel
        k._front_einstieg = beste
        return beste

    def _fahrer_basis(self, k, frei: dict):
        """Fuer einen Bot, der fahren darf: die eigene Basis, an der das
        wertvollste freie Fahrzeug steht, das sich noch kein anderer Fahrer
        vorgenommen hat - oder None."""
        from .bots import FAHRZEUG_VORZUG
        jetzt = self.welt.zeit
        unterwegs = {}
        for x in self.kaempfer.values():
            if x is not k and x.team == k.team and x.lebt and getattr(x, "darf_fahren", False) \
                    and x.fahrzeug is None and jetzt - getattr(x, "_fahrer_seit", -99.0) < 25.0:
                kenn = getattr(x, "einstieg_zuletzt", "")
                unterwegs[kenn] = unterwegs.get(kenn, 0) + 1
        beste, wert = None, 0.0
        for b in self.front_basen(k.team):
            kenn = "b%d" % b.nr
            if kenn not in frei:
                continue
            werte = sorted((FAHRZEUG_VORZUG.get(f.art, 50.0) for f in getattr(self, "fahrzeuge", ())
                            if f.fahrer is None and not f.kaputt and not f.nur_bild
                            and f.pos.distance_to(b.pos) < 560.0
                            and jetzt - getattr(f, "_abgestellt", -999.0) >= 60.0), reverse=True)
            werte = werte[unterwegs.get(kenn, 0):]
            if werte and werte[0] > wert:
                beste, wert = kenn, werte[0]
        if beste is not None:
            k._fahrer_seit = jetzt
        return beste

    def front_eingestiegen(self, k) -> None:
        """Nach dem Einstieg eines Bots: in eine Gruppe, die sich dort fuer
        dasselbe Ziel sammelt - oder eine neue, die kurz auf weitere wartet."""
        if not self.front_an or not getattr(k, "ist_bot", False) or not self.ist_gastgeber:
            return
        self.front_zustand()
        for g in self._gruppen:
            if k in g.mitglieder:
                g.mitglieder.remove(k)
        ziel = k.__dict__.pop("_front_ziel", None)
        kenn = k.__dict__.pop("_front_einstieg", None)
        jetzt = self.welt.zeit
        if ziel is not None:
            for g in self._gruppen:
                if (g.team == k.team and g.ziel == ziel and g.einstieg == kenn
                        and jetzt < g.sammeln_bis and len(g.mitglieder) < g.soll):
                    g.mitglieder.append(k)
                    return
            ziele = [(ziel, 1.0)]
        else:
            ziele = list(self._front_plan.get(k.team, {}).items()) or self._front_ziele(k.team)
        g = self._gruppe_bilden(k.team, ziele, k.pos, self._front_rnd, einstieg=kenn)
        g.sammeln_bis = jetzt + (F["sammeln"] if g.soll > 1 else 0.0)
        g.mitglieder.append(k)

    # ---- Was ein Bot in seiner Gruppe tun soll -------------------------------------
    def front_gruppe(self, k):
        for g in self.__dict__.get("_gruppen", ()):
            if k in g.mitglieder:
                return g
        return None

    def front_auftrag(self, k):
        """(Ort, Tempo, Blick) fuer einen Bot ohne Gegner im Blick, oder None
        (dann wie bisher). Der Anfuehrer geht den Weg, die anderen ihre
        Plaetze in der Formation, am Ziel stehen sie im Ring um den Punkt."""
        if not self.front_an or k.fahrzeug is not None:
            return None
        g = self.front_gruppe(k)
        if g is None or not g.weg:
            return None
        leute = g.lebende()
        if k not in leute:
            return None
        f = leute[0]
        jetzt = self.welt.zeit
        if g.am_ziel:
            return self._halten(g, leute, k)
        if k is f:
            return self._fuehren(g, leute, k, jetzt)
        # Der Platz in der Formation aendert sich langsam: gemerkt fuer eine
        # Viertelsekunde (gemessen: die Wegfragen je Schritt und Mitlaeufer
        # kosteten mehr als alles andere der Front).
        merk = k.__dict__.get("_front_merk")
        if merk is not None and merk[0] > jetzt and merk[1] is g:
            return merk[2]
        auftrag = self._folgen(g, leute, k, f)
        k._front_merk = (jetzt + 0.25, g, auftrag)
        return auftrag

    def _fuehren(self, g, leute, k, jetzt):
        if jetzt < g.sammeln_bis and len(leute) < g.soll:
            return pygame.Vector2(k.pos), 0.0, k.pos + g.richtung * 120.0
        # Ein gemeldeter Kampf in der Naehe: erst dorthin (ohne Funk, wie bisher).
        # Seit 0.34.133 nur eine Gruppe je Kampf (kampf_gruppen) und nur, wenn er
        # an ihrem eigenen Weg liegt - die anderen verfolgen ihr Ziel weiter.
        if g.umweg is None and jetzt >= g.kampf_pause and hasattr(self, "kampf_zuteilen"):
            ziel = g.weg[-1] if g.weg else None
            kampf = self.kampf_zuteilen(g.team, ("g", g.nr), k.pos, F["kampf_weite"], F["kampf_gruppen"])
            if kampf is not None and (ziel is None or ziel.distance_to(k.pos) > kampf.distance_to(k.pos) + 150.0) \
                    and min([q.distance_to(kampf) for q in g.weg[g.schritt:]] + [k.pos.distance_to(kampf)]) \
                    <= F["kampf_weg"]:
                g.umweg = pygame.Vector2(kampf)
                g.kampf_pause = jetzt + F["kampf_pause"]
        if g.umweg is not None:
            if k.pos.distance_to(g.umweg) < F["wegpunkt_nah"]:
                g.umweg = None
            else:
                return self._marsch(g, leute, k, g.umweg)
        while g.schritt < len(g.weg) and k.pos.distance_to(g.weg[g.schritt]) < F["wegpunkt_nah"]:
            g.schritt += 1
        if g.am_ziel:
            g.halten_seit = jetzt
            g.halten_bis = jetzt + self._front_rnd.uniform(*F["halten_neu"])
            return self._halten(g, leute, k)
        return self._marsch(g, leute, k, g.weg[g.schritt])

    def _marsch(self, g, leute, k, ort):
        d = ort - k.pos
        if d.length_squared() > 1.0:
            neu = d.normalize()
            # Die Richtung dreht weich: ein Knick im Weg soll nicht die ganze
            # Formation um ihn herumschwenken lassen.
            g.richtung = (g.richtung * 0.85 + neu * 0.15)
            if g.richtung.length_squared() > 1e-6:
                g.richtung.normalize_ip()
        if not g.spur or g.spur[-1].distance_to(k.pos) >= F["spur_abstand"] * 0.5:
            g.spur.append(pygame.Vector2(k.pos))
        tempo = 1.0
        zurueck = max((m.pos.distance_to(k.pos) for m in leute[1:]), default=0.0)
        if zurueck > F["warten_ab"]:
            tempo = F["warten_tempo"]
        return pygame.Vector2(ort), tempo, k.pos + g.richtung * 160.0

    def form_platz(self, g, leute, k, f):
        """Der Platz von `k` in der Formation, oder None (dann auf der Spur)."""
        i = leute.index(k) - 1
        plaetze = FORMATIONEN.get(g.form, FORMATIONEN["keil"])
        vorn, rechts = plaetze[min(i, len(plaetze) - 1)]
        if i >= len(plaetze):
            vorn -= (i - len(plaetze) + 1)
        r = g.richtung
        quer = pygame.Vector2(-r.y, r.x)
        a = F["form_abstand"]
        return f.pos + r * (vorn * a) + quer * (rechts * a)

    def _folgen(self, g, leute, k, f):
        """Ein Platz in der Formation - oder auf der Spur des Anfuehrers, wo
        die Formation nicht passt. Nur Plaetze, zu denen der Weg gerade frei
        ist: ein Wegfeld zu einer Stelle, die mit dem Anfuehrer wandert,
        waere jedes Mal neu (wege.feld_zu); sonst zum Wegpunkt der Gruppe."""
        i = leute.index(k)
        welt = self.welt
        wege = welt.wege
        platz = self.form_platz(g, leute, k, f)
        if not (welt.frei(platz, 12.0, 0, True) and wege.gerade_frei(0, f.pos, platz, 10.0)):
            # Kein Platz (Wald, Gasse): hinter ihm auf seiner Spur.
            platz = None
            weit = F["spur_abstand"] * i
            gegangen = 0.0
            vorher = f.pos
            for q in reversed(g.spur):
                gegangen += q.distance_to(vorher)
                vorher = q
                if gegangen >= weit:
                    platz = pygame.Vector2(q)
                    break
            if platz is None:
                platz = pygame.Vector2(g.spur[0]) if g.spur else pygame.Vector2(f.pos)
        if not wege.gerade_frei(0, k.pos, platz, 10.0):
            # Abgeschnitten (um eine Ecke): zum Anfuehrer, wenn der Weg frei
            # ist, sonst zum Wegpunkt der Gruppe - ein fester Ort.
            if wege.gerade_frei(0, k.pos, f.pos, 10.0):
                platz = pygame.Vector2(f.pos)
            elif g.umweg is not None:
                platz = pygame.Vector2(g.umweg)
            elif g.weg:
                platz = pygame.Vector2(g.weg[min(g.schritt, len(g.weg) - 1)])
        sektor = SEKTOREN[min(i, len(SEKTOREN) - 1)]
        blick = k.pos + g.richtung.rotate(sektor) * 150.0
        d = k.pos.distance_to(platz)
        tempo = 1.0 if d > 30.0 else 0.6
        if d < 10.0:
            tempo = 0.0
        return platz, tempo, blick

    def _halten(self, g, leute, k):
        """Am Ziel: im Ring um den Punkt, nach aussen schauend - nicht alle
        auf einem Fleck. Der Platz bleibt, solange die Gruppe dort steht."""
        merk = k.__dict__.get("_halten_merk")
        if merk is not None and merk[0] is g and merk[1] == g.ziel and merk[2] == len(leute):
            platz, richtung = merk[3], merk[4]
            tempo = 0.0 if k.pos.distance_to(platz) < 14.0 else 0.8
            return platz, tempo, k.pos + richtung * 180.0
        ort, _kn = self._ziel_ort(g.ziel)
        if ort is None:
            return None
        i = leute.index(k)
        innen, aussen = F["halten_ring"]
        rad = F["radius"] * (innen + (aussen - innen) * ((i * 0.37 + g.nr * 0.21) % 1.0))
        winkel = g.ring_winkel + i * (360.0 / max(1, len(leute))) * 0.5
        richtung = pygame.Vector2(1, 0).rotate(winkel)
        platz = ort + richtung * rad
        if not self.welt.frei(platz, 12.0, 0, True):
            platz = ort + richtung * rad * 0.5
            if not self.welt.frei(platz, 12.0, 0, True):
                platz = pygame.Vector2(ort)
        k._halten_merk = (g, g.ziel, len(leute), platz, richtung)
        tempo = 0.0 if k.pos.distance_to(platz) < 14.0 else 0.8
        return platz, tempo, k.pos + richtung * 180.0

    # ---- Ziele fuer Fahrer (Fahrzeuge der Bots) ---------------------------------
    def front_fahrziel(self, k):
        """Wohin ein Bot am Steuer faehrt, wenn er keinen Gegner sieht: zum
        Ziel mit den meisten eigenen Leuten an der Front (Unterstuetzung),
        Nachschub und Funk zum eigenen Punkt dahinter."""
        if not self.front_an:
            return None
        plan = self._front_plan.get(k.team) if "_front_plan" in self.__dict__ else None
        if not plan:
            return None
        b = k.fahrzeug
        art = getattr(b, "art", "")
        rnd = self._front_rnd
        if art in ("trosswagen", "funkwagen", "werfer"):
            eigen = [p for p in self.front_punkte() if p.gehoert(k.team)]
            hinten = self.schlacht_basis(k.team)
            if eigen and hinten is not None:
                # Der eigene Punkt, der den Zielen am naechsten ist - mit Abstand dahinter.
                ziele = [self._ziel_ort(z)[0] for z in plan if self._ziel_ort(z)[0] is not None]
                if ziele:
                    p = min(eigen, key=lambda p: min(p.pos.distance_to(z) for z in ziele))
                    zur = (hinten - p.pos)
                    zurueck = 160.0 if art == "trosswagen" else (380.0 if art == "funkwagen" else 700.0)
                    if zur.length_squared() > 1.0:
                        return p.pos + zur.normalize() * zurueck
                    return pygame.Vector2(p.pos)
            return None
        gewichtet = sorted(plan.items(), key=lambda zw: -zw[1])
        zahl = {}
        for g in self.__dict__.get("_gruppen", ()):
            if g.team == k.team:
                zahl[g.ziel] = zahl.get(g.ziel, 0) + len(g.mitglieder)
        if not gewichtet:
            return None
        ziel = max(gewichtet, key=lambda zw: zw[1] * (1.0 + zahl.get(zw[0], 0)) * rnd.uniform(0.7, 1.3))[0]
        ort, _kn = self._ziel_ort(ziel)
        return pygame.Vector2(ort) if ort is not None else None
