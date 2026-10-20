"""
DUSTFRONT - Zombies und Bosse als zielorientierte KI (seit 0.34.30)
====================================================================

Schritt 3 aus docs/KI.md. Ein `GegnerHirn` haengt an einem Gegner des
Mehrspielers (`mehrspieler.KampfGegner.hirn`) und ersetzt dort genau
eines: `Gegner._wohin`, die Entscheidung, wohin er laeuft und ob er
zuschlaegt. Laufen, Ausweichen, Rueckstoss und Sturz bleiben, wie sie
sind (`Gegner._laufen`).

Die Zombies fliegen irgendwann aus dem Spiel. Bis dahin sind sie der
Test, ob die KI auch **dumme Wesen** kann: wenige Ziele, kein Funk,
keine langen Plaene. Wen sie jagen, waehlen sie wie bisher
(`KampfGegner._ziel_waehlen`) - Wissen und Wahrnehmung kommen in
Schritt 5.

Welche Spezies ein Gegner ist, steht in `spezies_fuer`: gibt es in
`wesen/` eine Spezies mit dem Namen seiner Art (etwa `[spezies renner]`),
diese - sonst `boss`, `speier` oder `zombie` (wesen/zombies.txt). Eine
eigene Spezies fuer eine Art ist damit nur ein Block in der Datei.

Reflexe laufen neben dem Plan her und werden nicht geplant: die
Faehigkeit eines Bosses (ankuendigen, ausloesen) zaehlt ihren Takt wie
immer - ein Boss, der sie nur einsetzte, wenn ein Plan es will, waere
schwaecher als vorher. Der Plan kann sie aber vorziehen (`wueten`).
"""

from __future__ import annotations

import random

import pygame

from . import config as K
from . import wesen_daten
from .entities import Gegner


def spezies_fuer(art: str, daten=None) -> str:
    """Die Spezies einer Gegnerart (siehe oben)."""
    d = wesen_daten.daten() if daten is None else daten
    if art in d.spezies:
        return art
    g = K.gegner_daten(art)
    if K.ist_boss(art):
        return "boss"
    if g.get("fern"):
        return "speier"
    return "zombie"


class GegnerHirn:
    """Das Gehirn eines Gegners. `g` ist der Gegner selbst."""

    def __init__(self, g, spezies: str | None = None, rnd=None) -> None:
        self.g = g
        self.spezies = spezies or spezies_fuer(g.art)
        self.rnd = rnd or random.Random()
        self.merkmale = None
        self.gehirn = None
        self.rest = self.rnd.uniform(0.0, K.GOAP["takt"])
        self._aktion_lief = None
        self._streif = None           # wohin er ohne Ziel schlurft
        self._streif_rest = 0.0
        self.gehirn_neu()

    def gehirn_neu(self) -> None:
        d = wesen_daten.daten()
        sp = d.spezies.get(self.spezies)
        if self.merkmale is None:
            self.merkmale = sp.merkmale_wuerfeln(self.rnd) if sp else {}
        erzwungen = self.gehirn.erzwungen if self.gehirn is not None else None
        self.gehirn = d.gehirn(self.spezies, self.merkmale) if sp else None
        if self.gehirn is not None:
            self.gehirn.erzwungen = erzwungen
        self.rest = 0.0
        self._aktion_lief = None

    # ── Sinne ─────────────────────────────────────────────────────
    def _ziel(self):
        held = self.g.welt.held
        return held if held is not None and held.lebt else None

    def fuehlen(self):
        """(Fakten, Zahlen). Welche es gibt, steht oben in wesen/zombies.txt."""
        g = self.g
        d = g.daten
        z = self._ziel()
        gleich = z is not None and z.ebene == g.ebene
        abstand = g.pos.distance_to(z.pos) if gleich else 9999.0
        fern = g.fern
        im_band = bool(fern) and gleich and abstand <= fern["reichweite"] \
            and g.welt.sicht_frei(g.pos, z.pos, g.ebene)
        f = g.faehigkeit
        bereit = bool(f) and g.f_vorlauf <= 0.0 and g.f_rest <= f["takt"] * 0.5
        fakten = dict(
            ziel_da=z is not None,
            ziel_gleiche_ebene=gleich,
            ziel_nah=gleich and abstand < d["reichweite"] + z.radius,
            kann_spucken=bool(fern),
            im_band=im_band,
            boss=g.ist_boss,
            faehigkeit_bereit=bereit,
            angeschlagen=g.leben < g.max_leben * K.GOAP["gegner_angeschlagen"],
        )
        werte = dict(leben=g.leben / max(1.0, g.max_leben), abstand=abstand)
        return fakten, werte

    # ── Entscheiden ───────────────────────────────────────────────
    def wohin(self, dt: float):
        """Statt Gegner._wohin: der Punkt, auf den er zulaeuft, oder None."""
        g = self.g
        g.lauf_anteil = 1.0
        if self.gehirn is None:
            return Gegner._wohin(g, dt)
        z = self._ziel()
        # Reflex: die Faehigkeit zaehlt ihren Takt wie immer (siehe oben).
        if g.faehigkeit and z is not None and z.ebene == g.ebene:
            g._faehigkeit_fuehren(dt, z)
        self.rest -= dt
        if self.rest <= 0.0 or self.gehirn.aktion is None:
            self.rest = K.GOAP["takt"]
            fakten, werte = self.fuehlen()
            self.gehirn.denken(g.welt.zeit, fakten, werte)
        a = self.gehirn.aktion
        if a is None:
            return None
        if a is not self._aktion_lief:
            self._aktion_lief = a
        tun = TUN.get(a.tut)
        if tun is None:
            self.gehirn.melden("gescheitert")
            return None
        punkt, status = tun(self, dt, z)
        if status != "laeuft":
            self.gehirn.melden(status)
            self._aktion_lief = None
            self.rest = 0.0
        return punkt

    # ── Was die Aktionen tun ──────────────────────────────────────
    # Jede gibt (Punkt, Zustand) zurueck; Zustand "laeuft", "fertig" oder
    # "gescheitert".
    def _hin(self, z):
        """Der Weg zum Ziel, wie ihn die klassische KI geht: ueber Treppen,
        wenn noetig, sonst geradewegs oder um Hindernisse herum. Ein Boss
        wechselt die Ebene nicht."""
        g = self.g
        wege = g.welt.wege
        if not g.ist_boss and wege.braucht_weg(g.ebene, g.pos, z.ebene, z.pos):
            return g._treppe_ansteuern(wege, z)
        if z.ebene == g.ebene:
            return g._umweg(pygame.Vector2(z.pos), z)
        if g.ist_boss:
            return None
        if g.treppen_sperre <= 0:
            wohin = g.welt.treppe_unter(g)
            naeher = (abs(wohin - z.ebene) < abs(g.ebene - z.ebene)
                      if wohin is not None else False)
            if naeher and g.welt.ebene_wechseln(g, wohin):
                g.treppen_sperre = 1.2
        return pygame.Vector2(z.pos)

    def _schlagen_wenn_nah(self, z) -> None:
        g = self.g
        if (z.ebene == g.ebene and g.schlag_rest <= 0
                and g.pos.distance_to(z.pos) < g.daten["reichweite"] + z.radius):
            g.schlagen(z)

    def tun_hinlaufen(self, dt, z):
        if z is None:
            return None, "gescheitert"
        return self._hin(z), "laeuft"

    def tun_zuschlagen(self, dt, z):
        if z is None:
            return None, "fertig"
        self._schlagen_wenn_nah(z)
        return self._hin(z), "laeuft"

    def tun_spucken(self, dt, z):
        g = self.g
        if z is None or not g.fern:
            return None, "gescheitert"
        self._schlagen_wenn_nah(z)
        if z.ebene != g.ebene:
            return self._hin(z), "laeuft"
        abstand = g.pos.distance_to(z.pos)
        return g._fern_fuehren(dt, z, abstand, self._hin(z)), "laeuft"

    def tun_lauern(self, dt, z):
        """Ein Boss, dessen Ziel auf einer anderen Ebene ist: er wartet."""
        if z is None or z.ebene == self.g.ebene:
            return None, "fertig"
        return None, "laeuft"

    def tun_wueten(self, dt, z):
        """Die Faehigkeit vorziehen: der Takt springt auf null, der Reflex
        kuendigt sie im naechsten Schritt an - mit vollem Vorlauf."""
        g = self.g
        if not g.faehigkeit or z is None:
            return None, "gescheitert"
        if g.f_vorlauf <= 0.0:
            g.f_rest = 0.0
        return self._hin(z) if z.ebene == g.ebene else None, "fertig"

    def tun_wandern(self, dt, z):
        """Ohne Ziel: langsam in der Gegend herumschlurfen."""
        g = self.g
        if z is not None:
            return None, "fertig"
        self._streif_rest -= dt
        if (self._streif is None or self._streif_rest <= 0.0
                or g.pos.distance_to(self._streif) < 10.0):
            self._streif_rest = self.rnd.uniform(2.5, 6.0)
            self._streif = None
            for _ in range(8):
                p = g.pos + pygame.Vector2(self.rnd.uniform(40.0, K.GOAP["wandern_weite"]),
                                           0).rotate(self.rnd.uniform(0.0, 360.0))
                if g.welt.frei(p, g.radius + 2, g.ebene, True):
                    self._streif = p
                    break
        g.lauf_anteil = K.GOAP["wandern_tempo"]
        return (pygame.Vector2(self._streif) if self._streif is not None else None), "laeuft"


# Was `tut:` in wesen/zombies.txt heissen darf, und was es dann tut.
TUN = {name[4:]: getattr(GegnerHirn, name) for name in dir(GegnerHirn)
       if name.startswith("tun_")}
