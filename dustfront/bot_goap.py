"""
DUSTFRONT - Die Bots als zielorientierte KI (seit 0.34.29)
==========================================================

Ein `GoapHirn` ist ein `bots.BotHirn`, das nur eines anders macht: die
Entscheidung (`_entscheiden`). Statt der festen Reihenfolge der
klassischen KI ("sieht er jemanden, kaempft er, sonst ...") waehlt ein
GOAP-Gehirn (goap.py) das dringendste Ziel und plant dafuer eine Folge
von Aktionen. Ziele, Aktionen und Merkmale stehen in `wesen/bots.txt`.

Alles andere bleibt, wie es ist - und damit auch die Fairness: Sehen,
Hoeren, Zielen mit Fehler und Drehgrenze, Feuerstoesse, Wege, Treppen.
Was eine Aktion **tut**, ist meist ein Stueck der klassischen KI
(`TUN`); neu ist, wann sie es tut.

Welche KI ein Bot hat, sagt die Regel BOT-KI (KLASSISCH / GOAP), im
Testmodus der Spawner. Was er gerade denkt, zeigt der Testmodus (Taste 8,
zweimal: Gedanken). Was spaeter noch kommt: docs/KI.md.
"""

from __future__ import annotations

import pygame

from . import config as K
from . import wesen_daten
from .bots import BotHirn
from .bottaktik import braucht_schutz, rolle_frei


def _nichts(status: str):
    """Stehen, nichts tun - jedes Mal ein neuer Vektor, weil der Aufrufer
    die Laufrichtung weiterrechnet."""
    return pygame.Vector2(0, 0), None, False, False, status


class GoapHirn(BotHirn):
    """Ein Bot, der plant, statt einer festen Reihenfolge zu folgen."""

    ist_goap = True

    def __init__(self, gefecht, k, rnd, spezies: str = "mp_bot") -> None:
        self.spezies = spezies
        self.merkmale = None
        self.gehirn = None
        super().__init__(gefecht, k, rnd)

    def neues_leben(self) -> None:
        super().neues_leben()
        self.gehirn_neu()
        self._deckung_platz = None    # wo er in Deckung gegangen ist

    def gehirn_neu(self) -> None:
        """Ein frisches Gehirn aus den Daten - zu jedem Leben, und im
        Testmodus nach KI-DATEN NEU LADEN."""
        d = wesen_daten.daten()
        sp = d.spezies.get(self.spezies)
        if self.merkmale is None:
            # Merkmale gehoeren zum Bot, nicht zum Leben: wer mutig ist,
            # bleibt es auch nach dem Wiedereinstieg.
            self.merkmale = sp.merkmale_wuerfeln(self.rnd) if sp else {}
        erzwungen = self.gehirn.erzwungen if self.gehirn is not None else None
        self.gehirn = d.gehirn(self.spezies, self.merkmale) if sp else None
        if self.gehirn is not None:
            self.gehirn.erzwungen = erzwungen
        self.goap_rest = 0.0
        self._aktion_lief = None
        self._druck_lief = False

    # ── Sinne ─────────────────────────────────────────────────────
    def _gefahr(self):
        """Wo der Gegner ist, vor dem er sich in Acht nimmt: (Ort, Ebene,
        Wesen) - der, den er sieht, sonst der zuletzt gesehene."""
        z = self.ziel
        if z is not None and self.ziel_ok(z):
            return pygame.Vector2(z.pos), z.ebene, z
        return self.letzter_feind()

    def _in_deckung(self) -> bool:
        p = self._deckung_platz
        if p is None or self.k.pos.distance_to(p) > 20.0:
            return False
        gefahr = self._gefahr()
        return gefahr is None or self.g.welt.deckung(gefahr[0], self.k.pos, self.k.ebene) != ""

    def fuehlen(self):
        """(Fakten, Zahlen) - was er ueber seine Lage weiss. Welche es gibt,
        steht oben in wesen/bots.txt."""
        k = self.k
        g = self.g
        z = self.ziel
        sichtbar = z is not None and self.ziel_ok(z)
        gefahr = self._gefahr()
        zone = self._zone()
        im_kreis = (zone is not None and k.ebene == zone[1]
                    and k.pos.distance_to(zone[0]) <= K.ZONE["radius"] * 0.75)
        d = k.waffe_daten
        magazin_leer = k.nachlade_rest > 0 or (d.get("art") == "schuss"
                                               and k.magazin.get(k.waffe_name, 0) <= 0)
        gegen = gefahr[2] if gefahr is not None else None
        fakten = dict(
            feind_sichtbar=sichtbar,
            linie_frei=sichtbar and self.linie != "hindernis",
            feind_bekannt=gefahr is not None,
            munition_da=bool(self._waffen_mit_munition()),
            magazin_leer=magazin_leer,
            granate_da=self._wurf_platz() >= 0,
            angeschlagen=k.leben < K.BOTS["deckung_leben"],
            getroffen=self.getroffen_rest > 0.0,
            unterdrueckt=self.unterdrueckt > 0.0,
            in_deckung=self._in_deckung(),
            kamerad_liegt=self._wem_helfen() is not None,
            kamerad_braucht_schutz=any(braucht_schutz(x) for x in self.kameraden()),
            kamerad_flankiert=gegen is not None and not rolle_frei(g, gegen, "flanke", k),
            flanke_frei=(gegen is not None and self.flanke_pause <= 0.0
                         and rolle_frei(g, gegen, "flanke", k)),
            zone_aktiv=zone is not None,
            im_kreis=im_kreis,
            sturm_plan=self.sturm is not None,
        )
        werte = dict(leben=k.leben / max(1.0, k.max_leben),
                     abstand=k.pos.distance_to(gefahr[0]) if gefahr else 9999.0)
        return fakten, werte

    # ── Entscheiden ───────────────────────────────────────────────
    def _entscheiden(self, dt: float, ein: dict):
        if self.gehirn is None:
            return super()._entscheiden(dt, ein)
        self.goap_rest -= dt
        if self.goap_rest <= 0.0 or self.gehirn.aktion is None:
            self.goap_rest = K.GOAP["takt"]
            fakten, werte = self.fuehlen()
            self.gehirn.denken(self.g.welt.zeit, fakten, werte)
        a = self.gehirn.aktion
        if a is None:
            # Nichts zu tun: herumgehen und suchen, wie die klassische KI.
            will, punkt = self._unterwegs(dt, ein)
            return will, punkt, False, False
        if a is not self._aktion_lief:
            self._aktion_lief = a
            self._druck_lief = False
            if a.funk:
                self.funken(a.funk)
            if a.tut == "deckung" and self.k.leben < K.BOTS["deckung_leben"]:
                self.funken("getroffen")
        tun = TUN.get(a.tut)
        if tun is None:
            self.gehirn.melden("gescheitert")
            return pygame.Vector2(0, 0), None, False, False
        will, punkt, feuern, zielt, status = tun(self, dt, ein)
        if status != "laeuft":
            self.gehirn.melden(status)
            self._aktion_lief = None
            self.goap_rest = 0.0            # gleich neu denken
        return will, punkt, feuern, zielt

    # ── Was die Aktionen tun ──────────────────────────────────────
    # Jede gibt (Laufrichtung, Zielpunkt, feuern, zielen, Zustand) zurueck;
    # Zustand ist "laeuft", "fertig" oder "gescheitert".

    def tun_kaempfen(self, dt, ein):
        z = self.ziel
        if z is None or not self.ziel_ok(z):
            return _nichts("fertig")
        return self._kaempfen(dt, ein) + ("laeuft",)

    def tun_nahkampf(self, dt, ein):
        z = self.ziel
        if z is None or not self.ziel_ok(z):
            return _nichts("fertig")
        return self._nahkampf(ein, z, self.k.pos.distance_to(z.pos)) + ("laeuft",)

    def tun_flankieren(self, dt, ein):
        k = self.k
        gefahr = self._gefahr()
        if gefahr is None:
            return _nichts("gescheitert")
        ort, ebene, gegen = gefahr
        z = self.ziel
        if z is not None and self.ziel_ok(z) and self.linie == "":
            # Er hat freie Bahn: die Flanke hat ihr Ziel erreicht.
            self.taktik = None
            return _nichts("fertig")
        if self.taktik is None or self.taktik.get("gegen") is not gegen:
            if not self.flanke_starten(gegen, ort, ebene):
                return _nichts("gescheitert")
        t = self.taktik
        if self.g.welt.zeit > t["bis"] or k.pos.distance_to(t["ort"]) < 14.0:
            self.taktik = None
            self.flanke_pause = K.BOTS["flanke_pause"]
            return _nichts("fertig")
        will = self._weg_richtung(t["ort"], t["ebene"], ein)
        return will, pygame.Vector2(ort), False, False, "laeuft"

    def tun_niederhalten(self, dt, ein):
        gefahr = self._gefahr()
        if gefahr is None or not self._munition_reicht():
            return _nichts("gescheitert")
        ort, ebene, gegen = gefahr
        if self.druck_rest <= 0.0:
            if self._druck_lief:
                return _nichts("fertig")
            if not self.druck_starten(gegen):
                return _nichts("gescheitert")
            self._druck_lief = True
        punkt = self.druckpunkt(ort, ebene)
        return pygame.Vector2(0, 0), punkt, self._abdruecken(dt, punkt, ein), False, "laeuft"

    def tun_deckung(self, dt, ein):
        k = self.k
        gefahr = self._gefahr()
        if gefahr is None:
            # Vor niemandem in Deckung: wo er steht, ist er sicher genug.
            self._deckung_platz = pygame.Vector2(k.pos)
            return _nichts("fertig")
        if self.deckung_ort is None or self.deckung_suche <= 0.0:
            self.deckung_ort = self._deckung_suchen(pygame.Vector2(gefahr[0]))
            self.deckung_suche = 0.6
        if self.deckung_ort is None:
            return _nichts("gescheitert")
        d = self.deckung_ort - k.pos
        if d.length() < 5.0:
            self._deckung_platz = pygame.Vector2(k.pos)
            self.deckung_ort = None
            # Der Gegner ist inzwischen woanders und die Stelle deckt nicht
            # mehr: gescheitert, sonst plante er im selben Augenblick
            # wieder dieselbe Deckung (und so fort).
            return _nichts("fertig" if self._in_deckung() else "gescheitert")
        return d.normalize(), pygame.Vector2(gefahr[0]), False, False, "laeuft"

    def tun_nachladen(self, dt, ein):
        k = self.k
        name = k.waffe_name
        if k.nachlade_rest > 0:
            gefahr = self._gefahr()
            punkt = pygame.Vector2(gefahr[0]) if gefahr else None
            return pygame.Vector2(0, 0), punkt, False, False, "laeuft"
        if K.WAFFEN[name].get("art") == "schuss" and k.magazin.get(name, 0) > 0:
            return _nichts("fertig")
        # Lieber die andere Waffe nehmen, wenn die noch geladen ist - das
        # geht schneller als nachladen, und so macht es jeder Mensch auch.
        for i, n in enumerate(k.waffen):
            if n != name and K.WAFFEN[n].get("art") == "schuss" and k.magazin.get(n, 0) > 0:
                if self.waffen_rest <= 0.0:
                    ein["waffe"] = i
                    self.waffen_rest = 1.2
                return _nichts("laeuft")
        if k.knapp and k.vorrat.get(name, 0) <= 0:
            return _nichts("gescheitert")
        ein["knoepfe"].append("nachladen")
        return _nichts("laeuft")

    def tun_zum_kreis(self, dt, ein):
        k = self.k
        zone = self._zone()
        if zone is None:
            return _nichts("gescheitert")
        if k.ebene == zone[1] and k.pos.distance_to(zone[0]) <= K.ZONE["radius"] * 0.75:
            return _nichts("fertig")
        z = self.ziel
        if z is not None and self.ziel_ok(z):
            # Kaempfen auf dem Weg: die Kampfbewegung zieht ihn ohnehin
            # zum Kreis (bots._kampfbewegung).
            return self._kaempfen(dt, ein) + ("laeuft",)
        return self._weg_richtung(zone[0], zone[1], ein), None, False, False, "laeuft"

    def tun_helfen(self, dt, ein):
        x = self._wem_helfen()
        if x is None:
            return _nichts("fertig")
        will, punkt = self._helfen(x, ein)
        return will, punkt, False, False, "laeuft"

    def tun_sturm(self, dt, ein):
        r = self.taktik_sturm(dt, ein)
        if r is None:
            return _nichts("fertig")
        will, punkt, feuern = r
        return will, punkt, feuern, False, "laeuft"

    def tun_suchen(self, dt, ein):
        z = self.ziel
        if z is not None and self.ziel_ok(z):
            return _nichts("fertig")
        will, punkt = self._unterwegs(dt, ein)
        return will, punkt, False, False, "laeuft"


# Was `tut:` in wesen/bots.txt heissen darf, und was es dann tut.
TUN = {name[4:]: getattr(GoapHirn, name) for name in dir(GoapHirn)
       if name.startswith("tun_")}
