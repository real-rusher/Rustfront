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
    def __init__(self, name: str, will=None, dringlich="0", info: str = "") -> None:
        self.name = name
        self.will = will if isinstance(will, dict) else bedingungen(will)
        self.dringlich = dringlich if isinstance(dringlich, Ausdruck) else Ausdruck(dringlich)
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

    def __init__(self, ziele, aktionen, merkmale: dict | None = None) -> None:
        self.ziele = list(ziele)
        self.aktionen = list(aktionen)
        self.merkmale = dict(merkmale or {})
        self.fakten: dict = {}
        self.werte: dict = {}
        self.dringlichkeiten: dict = {}
        self.ziel = None
        self.plan: list = []
        self.erzwungen = None           # Testmodus: dieses Ziel, egal wie dringlich
        self.protokoll = deque(maxlen=K.GOAP["protokoll"])
        self._sperre: dict = {}          # Aktion -> bis wann sie nicht geplant wird
        self._neu_planen_bis = 0.0
        self._jetzt = 0.0

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
        self.dringlichkeiten = {z.name: z.dringlich.wert(namen) for z in self.ziele}
        # Kandidaten: was dringlich ist und noch nicht gilt, das Dringendste
        # zuerst. Das laufende Ziel bekommt einen Vorsprung, damit es nicht
        # bei jedem Wackeln der Zahlen wechselt.
        offen = [z for z in self.ziele
                 if self.dringlichkeiten[z.name] > 0 and not erfuellt(self.fakten, z.will)]
        if self.erzwungen is not None:
            offen = [z for z in self.ziele if z.name == self.erzwungen] or offen

        def rang(z):
            d = self.dringlichkeiten[z.name]
            return d + (g["vorsprung"] if z is self.ziel else 0.0)

        offen.sort(key=rang, reverse=True)
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
