"""
DUSTFRONT - Innenleben eines Menschen im Gefecht (seit 0.34.38)
===============================================================

Gemeldet: "dass sie Panik haben, dass sie uebermuetig werden, dass sie
nicht perfekt agieren ... wenn sie in Panik sind, rennen sie nur noch weg
und ignorieren Sachen wie ihren Feuerschutz ... wenn spaeter taktisch
schlauere oder ausgebildetere Bots mit mehr Drill reinkommen, dass die
eher bei ihrem Ziel bleiben und schneller wieder ihr Ziel weitermachen."

Zwei Zahlen je Mensch, gebaut nach docs/KI.md Abschnitt 8.3 und 10:

* **Stress** (0 bis 1): was ihm gerade passiert. Ereignisse (`ereignis`)
  schieben ihn hoch - eine Kugel knapp vorbei, ein Treffer, ein Kamerad,
  der faellt, eine Granate vor den Fuessen -, mit der Zeit geht er
  zurueck, in Deckung schneller. Disziplin daempft, was ankommt.
* **Zuversicht** (fuenf Stufen): glaubt er, dass seine Seite gewinnt?
  Gerechnet wie in *Days Gone* (Karlsson) als Verhaeltnis der Staerken -
  die eigene, die der Kameraden (mal deren Zuversicht), die der Gegner
  (mal deren Zuversicht), dazu, wen die eigene Seite schon erwischt und
  wen sie verloren hat (`zuversicht_rechnen`). Ein Panischer zaehlt fuer
  die andere Seite - darum steckt Panik an.

Daraus die Zustaende, die das Gehirn als Fakten sieht: **Panik** (Stress
ueber der Schwelle, die der Mut setzt - er rennt weg, auch vor seinen
Auftraegen; mit Drill ist sie kuerzer), **Schreck** (der Stress springt:
ein Augenblick, in dem er nichts tut), **eingeschossen** (er feuert schon
eine Weile - wer so ein MG am Laufen hat, gibt die Stellung nicht gern
auf). Die Zahlen stehen in K.MORAL; was ein Zustand bewirkt, steht als
Ziel in wesen/bots.txt.
"""

from __future__ import annotations

from . import config as K


def zuversicht_rechnen(eigen: float, freunde, feinde, getoetet: float = 0.0,
                       verloren: float = 0.0) -> float:
    """Das Verhaeltnis der Staerken (Days Gone, Formel 1):

        (eigen + Summe c_f * s_f + getoetet) / (Summe c_e * s_e + verloren)

    `freunde` und `feinde` sind Paare (Staerke, Zuversichts-Faktor). Ein
    Freund mit Faktor 0 (panisch) zaehlt nicht fuer die eigene, sondern
    mit seiner Staerke fuer die andere Seite. Ohne Gegner gibt es nichts
    zu rechnen: dann None."""
    feinde = list(feinde)
    if not feinde:
        return None
    oben = float(eigen) + float(getoetet)
    unten = float(verloren)
    for s, c in freunde:
        if c <= 0.0:
            unten += s
        else:
            oben += c * s
    for s, c in feinde:
        unten += max(0.05, c) * s
    return oben / max(0.05, unten)


def stufe_von(verhaeltnis) -> int:
    """0 panisch, 1 besorgt, 2 neutral, 3 zuversichtlich, 4 heldenhaft."""
    if verhaeltnis is None:
        return 2
    stufe = 0
    for grenze in K.MORAL["zuversicht_stufen"]:
        if verhaeltnis >= grenze:
            stufe += 1
    return stufe


class Innenleben:
    """Stress, Zuversicht und was daraus folgt - fuer einen Menschen."""

    def __init__(self, merkmale: dict, rnd) -> None:
        self.merkmale = merkmale
        self.rnd = rnd
        self.stress = 0.0
        self.verhaeltnis = None       # zuletzt gerechnete Zuversicht (oder None)
        self.stufe = 2
        self.panik_rest = 0.0
        self.schreck_rest = 0.0
        self.eingeschossen = 0.0      # so lange feuert er schon ohne Pause
        self._feuer_aus = 0.0         # so lange hat er nicht mehr gefeuert
        self._sperren: dict = {}      # Ereignis -> so lange zaehlt es nicht wieder
        self.zuletzt = ""             # das letzte Ereignis (Testmodus)

    def _merkmal(self, name: str, vorgabe: float = 0.5) -> float:
        return float(self.merkmale.get(name, vorgabe))

    # ── Ereignisse ──────────────────────────────────────────────────
    def ereignis(self, art: str, anteil: float = 1.0) -> None:
        """Etwas ist passiert: Stress dazu (oder weg, wenn negativ)."""
        m = K.MORAL
        menge = m["stress"].get(art, 0.0) * anteil
        if menge == 0.0:
            return
        sperre = m["sperren"].get(art, 0.0)
        if sperre > 0.0:
            if self._sperren.get(art, 0.0) > 0.0:
                return
            self._sperren[art] = sperre
        if menge > 0.0:
            # Disziplin und Drill daempfen, was ankommt: wer es geuebt hat,
            # erschrickt weniger.
            daempfen = (m["disziplin_daempft"] * self._merkmal("disziplin")
                        + m["drill_daempft"] * self._merkmal("drill", 0.0))
            menge *= max(0.2, 1.0 - daempfen)
        vorher = self.stress
        self.stress = max(0.0, min(1.0, self.stress + menge))
        self.zuletzt = art
        if self.stress - vorher >= m["schreck_sprung"] and self.panik_rest <= 0.0:
            lo, hi = m["schreck"]
            self.schreck_rest = self.rnd.uniform(lo, hi) * (1.0 - 0.6 * self._merkmal("drill", 0.0))
        self._panik_pruefen()

    def _panik_pruefen(self) -> None:
        m = K.MORAL
        if self.panik_rest > 0.0:
            return
        schwelle = m["panik_ab"] + m["panik_mut"] * self._merkmal("mut")
        # Verzweifelt (die eigene Seite verliert klar) reicht weniger.
        if self.stufe <= 0:
            schwelle -= m["panik_verzweifelt"]
        if self.stress >= min(0.99, schwelle):
            lo, hi = m["panik_dauer"]
            dauer = self.rnd.uniform(lo, hi)
            dauer *= max(0.25, 1.0 - m["panik_drill"] * self._merkmal("drill", 0.0)
                         - 0.3 * self._merkmal("disziplin"))
            self.panik_rest = dauer
            self.schreck_rest = 0.0
            self.zuletzt = "panik"

    def panik_setzen(self, dauer: float | None = None) -> None:
        """Testmodus: sofort Panik."""
        self.stress = 1.0
        self.panik_rest = K.MORAL["panik_dauer"][1] if dauer is None else float(dauer)
        self.zuletzt = "panik"

    def beruhigen(self) -> None:
        """Testmodus: alles auf Ruhe."""
        self.stress = 0.0
        self.panik_rest = 0.0
        self.schreck_rest = 0.0

    # ── Der Schritt ─────────────────────────────────────────────────
    def schritt(self, dt: float, in_deckung: bool, feuert: bool) -> None:
        m = K.MORAL
        for art in list(self._sperren):
            self._sperren[art] -= dt
            if self._sperren[art] <= 0.0:
                del self._sperren[art]
        self.panik_rest = max(0.0, self.panik_rest - dt)
        self.schreck_rest = max(0.0, self.schreck_rest - dt)
        abbau = m["abbau_deckung"] if in_deckung else m["abbau"]
        abbau *= 1.0 + m["drill_abbau"] * self._merkmal("drill", 0.0)
        if self.panik_rest > 0.0:
            abbau *= 0.3                 # wer rennt, beruhigt sich kaum
        self.stress = max(0.0, self.stress - abbau * dt)
        if feuert:
            self.eingeschossen += dt
            self._feuer_aus = 0.0
        else:
            self._feuer_aus += dt
            if self._feuer_aus > m["eingeschossen_pause"]:
                self.eingeschossen = 0.0

    def zuversicht_setzen(self, verhaeltnis) -> None:
        self.verhaeltnis = verhaeltnis
        self.stufe = stufe_von(verhaeltnis)
        self._panik_pruefen()

    # ── Was das Gehirn sieht ────────────────────────────────────────
    @property
    def panik(self) -> bool:
        return self.panik_rest > 0.0

    @property
    def erschrocken(self) -> bool:
        return self.schreck_rest > 0.0

    @property
    def faktor(self) -> float:
        """Wie viel er fuer seine Seite zaehlt (c bei Days Gone): ein
        Panischer nichts, ein Heldenhafter mehr als einer."""
        if self.panik:
            return 0.0
        return K.MORAL["zuversicht_faktor"][self.stufe]

    def unschaerfe(self) -> float:
        """Wie unscharf er waehlt (goap.Gehirn._unscharf): mit dem Stress."""
        return max(0.0, min(1.0, self.stress * (1.0 - 0.5 * self._merkmal("drill", 0.0))))

    def stufen_name(self) -> str:
        return K.MORAL["zuversicht_namen"][self.stufe]
