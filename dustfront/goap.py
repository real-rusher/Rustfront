"""
DUSTFRONT - Zielorientierte KI, der Kern (seit 0.34.29)
=======================================================

GOAP: "goal-oriented action planning". Ein Wesen hat keine feste
Reihenfolge, was es tut, sondern

* **Fakten** ueber seine Lage - Wahrheitswerte wie `feind_sichtbar` oder
  `in_deckung`, und Zahlen wie `leben` (0 bis 1);
* **Ziele** mit einer **Dringlichkeit**, die aus Fakten, Zahlen und seinen
  **Merkmalen** (Mut, Disziplin ...) gerechnet wird, und einem Zustand,
  den es erreichen will (`will`);
* **Aktionen** mit Vorbedingungen (`braucht`), Wirkung (`macht`) und
  Kosten.

Der **Planer** sucht die billigste Folge von Aktionen, die vom jetzigen
Zustand zum Zustand des dringendsten Ziels fuehrt (A*-Suche ueber die
Wahrheitswerte, begrenzt in Tiefe und Knoten). Neue Faehigkeiten sind
damit nur eine neue Aktion: Kombinationen ("erst in Deckung, dann
nachladen") findet der Planer selbst.

Dieses Modul kennt das Spiel nicht. Was die Fakten sind und was eine
Aktion **tut**, sagt der, der es benutzt (bot_goap.py fuer die Bots).
Ziele, Aktionen und Spezies stehen als Daten in `wesen/` (wesen_daten.py).
Die ganze Planung, auch was spaeter kommen soll, steht in docs/KI.md.
"""

from __future__ import annotations

import ast
import heapq
from collections import deque

from . import config as K


# ══════════════════════════════════════════════════════════════════
# Ausdruecke
# ══════════════════════════════════════════════════════════════════

_ERLAUBT = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare,
            ast.Name, ast.Load, ast.Call, ast.IfExp,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd, ast.Not,
            ast.And, ast.Or, ast.Lt, ast.Gt, ast.LtE, ast.GtE, ast.Eq, ast.NotEq)
# Zahlen: ast.Constant ab 3.8; ast.Num gibt es bis 3.11 noch, danach nicht.
_ZAHL = tuple(t for t in (getattr(ast, "Constant", None), getattr(ast, "Num", None)) if t)
_FUNKTIONEN = {"min": min, "max": max, "abs": abs}


class _Namen(dict):
    """Unbekannte Namen sind 0: ein Fakt, den keiner gesetzt hat, gilt
    nicht, und ein Merkmal, das eine Spezies nicht hat, ist null."""

    def __missing__(self, schluessel):
        return 0


class Ausdruck:
    """Eine kleine Rechnung aus den Daten, etwa
    `80 * magazin_leer * munition_da` oder `3 - mut`.

    Erlaubt sind Zahlen, Namen, + - * /, Vergleiche, and/or/not,
    `a if b else c` und min, max, abs - sonst nichts. Geprueft wird beim
    Laden; ein Fehler in einer Datendatei kann so nie Code ausfuehren."""

    def __init__(self, text) -> None:
        self.text = str(text).strip()
        baum = ast.parse(self.text, mode="eval")
        for knoten in ast.walk(baum):
            if isinstance(knoten, _ZAHL):
                wert = getattr(knoten, "value", getattr(knoten, "n", None))
                if isinstance(wert, bool) or not isinstance(wert, (int, float)):
                    raise ValueError("nur Zahlen: %r" % (wert,))
                continue
            if not isinstance(knoten, _ERLAUBT):
                raise ValueError("nicht erlaubt: %s" % type(knoten).__name__)
            if isinstance(knoten, ast.Call):
                if not (isinstance(knoten.func, ast.Name)
                        and knoten.func.id in _FUNKTIONEN) or knoten.keywords:
                    raise ValueError("unbekannte Funktion")
        self.namen = sorted({k.id for k in ast.walk(baum) if isinstance(k, ast.Name)}
                            - set(_FUNKTIONEN))
        self._code = compile(baum, "<wesen>", "eval")

    def wert(self, namen: dict) -> float:
        n = _Namen(namen)
        n.update(_FUNKTIONEN)
        try:
            return float(eval(self._code, {"__builtins__": {}}, n))
        except ZeroDivisionError:
            return 0.0


# ══════════════════════════════════════════════════════════════════
# Ziele und Aktionen
# ══════════════════════════════════════════════════════════════════

def bedingungen(text) -> dict:
    """`a, !b` -> {"a": True, "b": False}."""
    raus = {}
    for teil in str(text or "").split(","):
        teil = teil.strip()
        if not teil:
            continue
        if teil.startswith("!"):
            raus[teil[1:].strip()] = False
        else:
            raus[teil] = True
    return raus


def erfuellt(fakten: dict, bed: dict) -> bool:
    return all(bool(fakten.get(n, False)) == v for n, v in bed.items())


class Aktion:
    def __init__(self, name: str, braucht=None, macht=None, kosten="1", tut="",
                 funk: str = "", info: str = "") -> None:
        self.name = name
        self.braucht = braucht if isinstance(braucht, dict) else bedingungen(braucht)
        self.macht = macht if isinstance(macht, dict) else bedingungen(macht)
        self.kosten = kosten if isinstance(kosten, Ausdruck) else Ausdruck(kosten)
        self.tut = tut or name
        self.funk = funk
        self.info = info

    def __repr__(self) -> str:
        return "Aktion(%s)" % self.name


class Ziel:
    """`rang` und `bindung` seit 0.34.38 (Dual Utility nach Dill, docs/KI.md
    Abschnitt 10): ein Ziel mit hoeherem Rang unterbricht jederzeit; eines
    mit gleichem Rang muss warten, bis das laufende `bindung` Sekunden lang
    verfolgt wurde. So bleibt ein Mensch bei dem, was er angefangen hat,
    statt bei jedem Wackeln der Lage umzuschwenken - nur eine Granate vor
    den Fuessen reisst ihn sofort heraus."""

    def __init__(self, name: str, will=None, dringlich="0", info: str = "",
                 rang="0", bindung="0") -> None:
        self.name = name
        self.will = will if isinstance(will, dict) else bedingungen(will)
        self.dringlich = dringlich if isinstance(dringlich, Ausdruck) else Ausdruck(dringlich)
        self.rang = rang if isinstance(rang, Ausdruck) else Ausdruck(rang)
        self.bindung = bindung if isinstance(bindung, Ausdruck) else Ausdruck(bindung)
        self.info = info

    def __repr__(self) -> str:
        return "Ziel(%s)" % self.name


# ══════════════════════════════════════════════════════════════════
# Der Planer
# ══════════════════════════════════════════════════════════════════

def planen(fakten: dict, will: dict, aktionen, namen: dict | None = None,
           tiefe: int | None = None, knoten: int | None = None):
    """Die billigste Folge von Aktionen von `fakten` nach `will`.

    Gibt eine Liste zurueck (leer, wenn `will` schon gilt) oder None,
    wenn es keinen Weg gibt. Gesucht wird vorwaerts (A*): der Zustand ist
    die Menge der wahren Fakten, die Schaetzung die Zahl der noch
    falschen Zielfakten. `tiefe` und `knoten` begrenzen die Suche, damit
    ein Plan auch mit vielen Aktionen nie ein Bild kostet."""
    g = K.GOAP
    tiefe = g["tiefe"] if tiefe is None else tiefe
    knoten = g["knoten"] if knoten is None else knoten
    namen = namen or {}
    start = frozenset(n for n, v in fakten.items() if v)

    def gilt(zustand, bed):
        return all((n in zustand) == v for n, v in bed.items())

    def schaetzung(zustand):
        return sum(1 for n, v in will.items() if (n in zustand) != v)

    if gilt(start, will):
        return []
    kosten = {a.name: max(0.01, a.kosten.wert(namen)) for a in aktionen}
    offen = [(schaetzung(start), 0, 0.0, start, ())]
    besucht = {start: 0.0}
    nr = 0
    while offen and nr < knoten:
        _f, _n, g_wert, zustand, weg = heapq.heappop(offen)
        if gilt(zustand, will):
            return list(weg)
        if len(weg) >= tiefe:
            continue
        for a in aktionen:
            if not gilt(zustand, a.braucht):
                continue
            neu = set(zustand)
            for n, v in a.macht.items():
                if v:
                    neu.add(n)
                else:
                    neu.discard(n)
            neu = frozenset(neu)
            if neu == zustand:
                continue
            g_neu = g_wert + kosten[a.name]
            if g_neu >= besucht.get(neu, float("inf")):
                continue
            besucht[neu] = g_neu
            nr += 1
            heapq.heappush(offen, (g_neu + schaetzung(neu), nr, g_neu, neu, weg + (a,)))
    return None


# ══════════════════════════════════════════════════════════════════
# Das Gehirn
# ══════════════════════════════════════════════════════════════════

class Gehirn:
    """Ziele waehlen, planen, den Plan abarbeiten, neu planen, wenn er
    nicht mehr passt - und mitschreiben, warum (fuer den Testmodus).

    Wer es benutzt, ruft je Denkschritt `denken` mit den Fakten und Zahlen
    und fuehrt die zurueckgegebene Aktion aus; ist sie fertig oder geht
    sie nicht, sagt er es mit `melden`."""

    def __init__(self, ziele, aktionen, merkmale: dict | None = None, rnd=None) -> None:
        self.ziele = list(ziele)
        self.aktionen = list(aktionen)
        self.merkmale = dict(merkmale or {})
        # Ohne Zufall waehlt es immer das Dringendste. Mit Zufall und dem
        # Wert `unschaerfe` (0 bis 1) waehlt es unter den guten Zielen des
        # hoechsten Rangs nach Gewicht - aber nie eines, das weit unter dem
        # besten liegt (Dual Utility, docs/KI.md 10.2).
        self.rnd = rnd
        self.fakten: dict = {}
        self.werte: dict = {}
        self.dringlichkeiten: dict = {}
        self.raenge: dict = {}
        self.ziel = None
        self.plan: list = []
        self.erzwungen = None           # Testmodus: dieses Ziel, egal wie dringlich
        self.protokoll = deque(maxlen=K.GOAP["protokoll"])
        self._sperre: dict = {}          # Aktion -> bis wann sie nicht geplant wird
        self._neu_planen_bis = 0.0
        self._gebunden_bis = 0.0         # vorher wechselt er nur fuer einen hoeheren Rang
        self.gewechselt = False          # hat der letzte Denkschritt das Ziel gewechselt?
        self._jetzt = 0.0

    @property
    def gebunden(self) -> float:
        """So lange haelt er sein Ziel noch gegen gleichrangige (s)."""
        return max(0.0, self._gebunden_bis - self._jetzt)

    @property
    def aktion(self):
        return self.plan[0] if self.plan else None

    def log(self, text: str) -> None:
        if self.protokoll and self.protokoll[-1][1] == text:
            return
        self.protokoll.append((round(self._jetzt, 2), text))

    def _namen(self) -> dict:
        n = dict(self.merkmale)
        n.update(self.werte)
        n.update({k: (1 if v else 0) for k, v in self.fakten.items()})
        return n

    def denken(self, jetzt: float, fakten: dict, werte: dict | None = None):
        """Ein Denkschritt. Gibt die Aktion zurueck, die jetzt dran ist,
        oder None, wenn es nichts zu tun gibt."""
        g = K.GOAP
        self._jetzt = jetzt
        self.fakten = dict(fakten)
        self.werte = dict(werte or {})
        namen = self._namen()
        self.gewechselt = False
        self.dringlichkeiten = {z.name: z.dringlich.wert(namen) for z in self.ziele}
        self.raenge = {z.name: z.rang.wert(namen) for z in self.ziele}
        # Kandidaten: was dringlich ist und noch nicht gilt - der hoechste
        # Rang zuerst, darin das Dringendste. Das laufende Ziel bekommt
        # einen Vorsprung, damit es nicht bei jedem Wackeln der Zahlen
        # wechselt.
        offen = [z for z in self.ziele
                 if self.dringlichkeiten[z.name] > 0 and not erfuellt(self.fakten, z.will)]
        if self.erzwungen is not None:
            offen = [z for z in self.ziele if z.name == self.erzwungen] or offen

        def wert(z):
            d = self.dringlichkeiten[z.name]
            return (self.raenge[z.name], d + (g["vorsprung"] if z is self.ziel else 0.0))

        offen.sort(key=wert, reverse=True)
        laufend = self.ziel if self.ziel in offen else None
        if laufend is not None and jetzt < self._gebunden_bis and self.erzwungen is None:
            # Gebunden: nur ein hoeherer Rang kommt vor das laufende Ziel.
            # Hat das laufende keinen Plan mehr, geht es mit dem Rest weiter.
            r = self.raenge[laufend.name]
            hoeher = [z for z in offen if self.raenge[z.name] > r]
            offen = hoeher + [laufend] + [z for z in offen if z not in hoeher and z is not laufend]
        elif (laufend is None and self.rnd is not None and self.erzwungen is None
              and len(offen) > 1):
            # Gewuerfelt wird nur bei einer neuen Wahl - sonst wuerfelte er
            # jeden Denkschritt neu und sprang zwischen zwei Zielen hin und her.
            offen = self._unscharf(offen)
        # Was vom Plan schon erledigt ist, faellt weg.
        while self.plan and self.plan[0].macht and erfuellt(self.fakten, self.plan[0].macht):
            self.log("FERTIG: %s" % self.plan[0].name)
            self.plan.pop(0)
        for z in offen:
            if z is self.ziel and self.plan and erfuellt(self.fakten, self.plan[0].braucht) \
                    and jetzt < self._neu_planen_bis:
                return self.plan[0]
            plan = self._planen(z, namen)
            if plan:
                if z is not self.ziel:
                    self.log("ZIEL: %s (%d)" % (z.name, round(self.dringlichkeiten[z.name])))
                    self.gewechselt = self.ziel is not None
                    self._gebunden_bis = jetzt + max(0.0, z.bindung.wert(namen))
                if [a.name for a in plan] != [a.name for a in self.plan]:
                    self.log("PLAN: %s" % " > ".join(a.name for a in plan))
                self.ziel = z
                self.plan = plan
                self._neu_planen_bis = jetzt + g["neu_planen"]
                return self.plan[0]
            self.log("KEIN PLAN FUER %s" % z.name)
        if self.ziel is not None:
            self.log("NICHTS ZU TUN")
        self.ziel = None
        self.plan = []
        return None

    def _unscharf(self, offen: list) -> list:
        """Dual Utility: im hoechsten Rang nur, was nah am Besten liegt,
        und darunter nach Gewicht gewuerfelt. Je groesser die Unschaerfe
        (Stress), desto weiter darf es vom Besten weg sein - er macht unter
        Druck Fehler, aber keine voellig dummen."""
        u = max(0.0, min(1.0, float(self.werte.get("unschaerfe", 0.0))))
        if u <= 0.0:
            return offen
        oben = self.raenge[offen[0].name]
        gruppe = [z for z in offen if self.raenge[z.name] == oben]
        bestes = max(self.dringlichkeiten[z.name] for z in gruppe)
        grenze = bestes * (1.0 - K.GOAP["unschaerfe_weite"] * u)
        gute = [z for z in gruppe if self.dringlichkeiten[z.name] >= grenze]
        if len(gute) < 2:
            return offen
        summe = sum(self.dringlichkeiten[z.name] for z in gute)
        wurf = self.rnd.uniform(0.0, summe)
        wahl = gute[-1]
        for z in gute:
            wurf -= self.dringlichkeiten[z.name]
            if wurf <= 0.0:
                wahl = z
                break
        return [wahl] + [z for z in offen if z is not wahl]

    def _planen(self, ziel, namen: dict):
        jetzt = self._jetzt
        moeglich = [a for a in self.aktionen if self._sperre.get(a.name, -1.0) <= jetzt]
        return planen(self.fakten, ziel.will, moeglich, namen)

    def melden(self, status: str) -> None:
        """Die laufende Aktion ist "fertig" oder "gescheitert". Gescheitert
        heisst: eine Weile nicht wieder einplanen und neu planen."""
        a = self.aktion
        if a is None or status == "laeuft":
            return
        if status == "fertig":
            self.log("FERTIG: %s" % a.name)
            self.plan.pop(0)
        else:
            self.log("GESCHEITERT: %s" % a.name)
            self._sperre[a.name] = self._jetzt + K.GOAP["sperre"]
            self.plan = []
        self._neu_planen_bis = 0.0
