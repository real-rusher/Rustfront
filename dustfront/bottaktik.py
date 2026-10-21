"""
DUSTFRONT - Taktik und Funk der Bots (seit 0.34.27)
===================================================

Gemeldet: "Lass die Bots Callouts kurz vor Aktionen geben, die als kleine
Untertitel ueber ihnen angezeigt werden. Sie sollen auch taktische Aktionen
durchfuehren, wie flankieren, suppression (also auf einen Gegner in Deckung
feuern bzw. auf den Spot direkt neben seiner Deckung, damit er in Deckung
bleibt), breaching (in Kooperation mit anderen Bots) und Feuerschutz fuer
andere Bots und Spieler des Teams."

Ein Anteil des Bot-Hirns (`Taktik`, von `bots.BotHirn` geerbt) und die
Absprache einer Mannschaft (`stuerme_fuehren`). Alles nur beim Gastgeber;
beim Gast kommt davon nur der Funkspruch an (`fk` in der Weltmeldung).
Auch hier gilt, was fuer die Bots immer gilt: sie bedienen dieselbe
Eingabe wie ein Mensch. Niederhalten heisst Fadenkreuz hinschwenken und
abdruecken, mit derselben Streuung und derselben Munition.

**Funk.** Kurz bevor er etwas tut, sagt er es an (`funken`): ein Satz aus
K.BOTS["funk"], fuer `funk_dauer` Sekunden ueber ihm. Er redet nicht
ununterbrochen - zwischen zwei Saetzen liegt `funk_abstand`, und derselbe
Anlass kommt fruehestens nach `funk_wiederholen` wieder.

**Flankieren.** Steht der Gegner hinter einer Kiste, oder ist er hinter
einer Mauer verschwunden, sucht sich einer eine Stelle seitlich von ihm,
von der aus nichts dazwischen steht (`flankenpunkt`), und geht dorthin.
Je Gegner flankiert nur einer (`rolle_nehmen`); die anderen halten ihn
derweil nieder.

**Niederhalten.** Auf die Stelle direkt neben der Deckung, an der der
Gegner herausschauen muss (`druckpunkt`) - oder, wenn es die nicht gibt,
auf die Deckung selbst. Nur, solange genug Munition bleibt. Ein Bot, an
dem Kugeln knapp vorbeifliegen, ist selbst niedergehalten
(`unterdrueckt`): er geht in Deckung und zielt schlechter.

**Feuerschutz.** Wer nachlaedt, angeschlagen ist, am Boden liegt oder
gerade flankiert, braucht Schutz - Bot wie Mensch. Gegner in seiner Naehe
nimmt ein Bot dann lieber ins Visier; ist der Gegner nicht zu sehen, haelt
er ihn nieder.

**Stuermen.** Zwei oder mehr Bots einer Mannschaft, die wissen, wo ein
Gegner steckt, aber ihn nicht sehen, sammeln sich an einer Stelle ausser
Sicht (`sammelpunkt`). Sind alle da (oder dauert es zu lange), ruft der
Erste REIN, wirft seine Granate, und alle gehen zugleich hinein.
"""

from __future__ import annotations

import pygame

from . import config as K


class _Ort:
    """Ein Punkt, der sich wie ein Ziel befragen laesst (pos, ebene) -
    fuer die Granate vor dem Sturm, die auf eine Stelle fliegt und nicht
    auf einen Gegner."""

    radius = 9.0

    def __init__(self, pos, ebene: int) -> None:
        self.pos = pygame.Vector2(pos)
        self.ebene = int(ebene)


# ══════════════════════════════════════════════════════════════════
# Rollen: wer flankiert, wer haelt nieder
# ══════════════════════════════════════════════════════════════════

def rolle_frei(g, gegner, art: str, k) -> bool:
    """Hat noch keiner aus der Mannschaft diese Aufgabe gegen diesen Gegner?"""
    eintrag = getattr(g, "_bot_rollen", {}).get((id(gegner), art))
    if eintrag is None:
        return True
    wer, bis = eintrag
    return wer is k or not wer.lebt or bis < g.welt.zeit


def rolle_nehmen(g, gegner, art: str, k, dauer: float) -> None:
    rollen = g.__dict__.setdefault("_bot_rollen", {})
    if len(rollen) > 200:
        jetzt = g.welt.zeit
        for s in [s for s, (_w, bis) in rollen.items() if bis < jetzt]:
            del rollen[s]
    rollen[(id(gegner), art)] = (k, g.welt.zeit + dauer)


def braucht_schutz(x) -> bool:
    """Braucht dieser Kamerad gerade Feuerschutz?"""
    if getattr(x, "am_boden", False) or getattr(x, "nachlade_rest", 0.0) > 0.0:
        return True
    if getattr(x, "leben", 100.0) < K.BOTS["deckung_leben"]:
        return True
    hirn = getattr(x, "hirn", None)
    if hirn is not None:
        if (getattr(hirn, "taktik", None) or {}).get("art") == "flanke":
            return True
        # Der Anfuehrer eines Trupps unter Feuer (seit 0.34.39): die
        # anderen sollen ihm zuerst helfen.
        trupp = getattr(hirn, "trupp", None)
        if (trupp is not None and trupp.fuehrer is x
                and (getattr(hirn, "getroffen_rest", 0.0) > 0.0
                     or getattr(hirn, "unterdrueckt", 0.0) > 0.0)):
            return True
        plan = getattr(hirn, "sturm", None)
        if plan is not None and plan.get("phase") == "rein":
            return True
    return False


# ══════════════════════════════════════════════════════════════════
# Das Hirn
# ══════════════════════════════════════════════════════════════════

class Taktik:
    """Funk und Taktik - ein Anteil von bots.BotHirn."""

    def taktik_anlegen(self) -> None:
        self.funk_sperre = 0.0
        self.funk_zuletzt = {}
        self.taktik = None            # laufende Flanke: dict(art, ort, ebene, gegen, bis)
        self.flanke_pause = 0.0
        self.druck_rest = 0.0         # so lange haelt er noch nieder
        self.druck_pause = 0.0
        self.druck_gegen = None
        self.unterdrueckt = 0.0       # so lange ist er selbst niedergehalten
        self.sturm = None             # der Plan seiner Mannschaft, wenn er dabei ist
        self.sturm_wurf = None        # (Ort, Ebene): dorthin wirft er vor dem Sturm
        self.feuerschutz_fuer = None
        self.laden_vorher = False

    def taktik_zeiten(self, dt: float) -> None:
        for name in ("funk_sperre", "flanke_pause", "druck_rest", "druck_pause",
                     "unterdrueckt"):
            setattr(self, name, max(0.0, getattr(self, name) - dt))

    def sagen(self, text: str, wichtig: bool = False) -> bool:
        """Etwas Eigenes sagen (seit 0.34.39, Trupps): wie `funken`, aber
        mit einem Satz, der aus der Lage entsteht ("ZWEI IM NORDEN!")."""
        b = K.BOTS
        if not text or (self.funk_sperre > 0.0 and not wichtig):
            return False
        self.k.funk = text[:b["funk_laenge"]]
        self.k.funk_rest = b["funk_dauer"]
        self.funk_sperre = b["funk_abstand"]
        return True

    def kugel_vorbei(self) -> None:
        """Eine Kugel pfeift knapp an ihm vorbei. Die klassische KI merkt
        sich das nur als `unterdrueckt`; das GOAP-Hirn bekommt Stress."""

    # ── Funk ────────────────────────────────────────────────────────
    def funken(self, anlass: str, wichtig: bool = False) -> bool:
        """Einen Satz zu diesem Anlass ansagen. `wichtig` (Granate, REIN)
        geht auch, wenn er gerade erst etwas gesagt hat."""
        b = K.BOTS
        saetze = b["funk"].get(anlass)
        if not saetze:
            return False
        jetzt = self.g.welt.zeit
        if not wichtig:
            if self.funk_sperre > 0.0:
                return False
            if jetzt - self.funk_zuletzt.get(anlass, -1e9) < b["funk_wiederholen"]:
                return False
        self.k.funk = self.rnd.choice(saetze)[:b["funk_laenge"]]
        self.k.funk_rest = b["funk_dauer"]
        self.funk_sperre = b["funk_abstand"]
        self.funk_zuletzt[anlass] = jetzt
        return True

    # ── Wer braucht Schutz ─────────────────────────────────────────
    def kameraden(self) -> list:
        k = self.k
        g = self.g
        if not g.mit_teams:
            return []
        return [x for x in g.kaempfer.values()
                if x is not k and x.lebt and x.team == k.team]

    def schutz_bonus(self, w, schuetzlinge: list):
        """(Bonus, Kamerad), wenn dieser Gegner einem Kameraden nahe ist,
        der Schutz braucht - sonst (0, None)."""
        weite = K.BOTS["feuerschutz_weite"]
        for x in schuetzlinge:
            if x.ebene == w.ebene and x.pos.distance_to(w.pos) < weite:
                return K.BOTS["feuerschutz_bonus"], x
        return 0.0, None

    def letzter_feind(self):
        """(Ort, Ebene, Wesen) des zuletzt gesehenen Gegners, wenn er frisch
        genug ist und auf derselben Ebene - sonst None."""
        k = self.k
        jetzt = self.g.welt.zeit
        bestes = None
        for w, (ort, ebene, zeit) in self.gesehen.items():
            if not w.lebt or ebene != k.ebene:
                continue
            if jetzt - zeit > K.BOTS["gedaechtnis_taktik"]:
                continue
            if bestes is None or zeit > bestes[3]:
                bestes = (pygame.Vector2(ort), ebene, w, zeit)
        return None if bestes is None else bestes[:3]

    # ── Orte ───────────────────────────────────────────────────────
    def druckpunkt(self, ort, ebene: int):
        """Wohin er schiesst, um einen in Deckung zu halten: direkt neben
        die Deckung, wo die Bahn frei ist - dort muesste er herausschauen.
        Gibt es keine solche Stelle, auf die Deckung selbst."""
        k = self.k
        welt = self.g.welt
        ort = pygame.Vector2(ort)
        hin = ort - k.pos
        if hin.length_squared() < 1.0:
            return ort
        quer = pygame.Vector2(-hin.y, hin.x).normalize()
        for d in K.BOTS["druck_versatz"]:
            for seite in (self.seite, -self.seite):
                p = ort + quer * (seite * d)
                if welt.schuss_halt(p, ebene):
                    continue
                if welt.deckung(k.pos, p, ebene) == "":
                    return p
        return ort

    def flankenpunkt(self, ort, ebene: int):
        """Eine Stelle seitlich vom Gegner, von der aus nichts zwischen ihm
        und dem Gegner steht. Weg von den Kameraden: zwei an derselben
        Stelle sind keine Flanke."""
        k = self.k
        welt = self.g.welt
        ort = pygame.Vector2(ort)
        weg = k.pos - ort
        weg = weg.normalize() if weg.length_squared() > 1.0 else pygame.Vector2(1, 0)
        andere = [x.pos for x in self.kameraden() if x.ebene == ebene]
        bestes, beste = None, 1e9
        for r in K.BOTS["flanke_radien"]:
            for winkel in (70.0, -70.0, 100.0, -100.0, 130.0, -130.0):
                p = ort + weg.rotate(winkel) * r
                if not welt.frei(p, k.radius + 3, ebene, True):
                    continue
                if welt.deckung(p, ort, ebene) != "":
                    continue
                wert = p.distance_to(k.pos)
                for a in andere:
                    if a.distance_to(p) < 90.0:
                        wert += 150.0
                if wert < beste:
                    bestes, beste = p, wert
        return bestes

    def sammelpunkt(self, ort, ebene: int):
        """Wo sich der Trupp vor dem Sturm sammelt: nah am Ziel, aber
        ausser Sicht (eine Mauer dazwischen), und auf seiner Seite."""
        k = self.k
        welt = self.g.welt
        ort = pygame.Vector2(ort)
        bestes, beste = None, 1e9
        for r in K.BOTS["sturm_sammel"]:
            for i in range(16):
                p = ort + pygame.Vector2(r, 0).rotate(i * 22.5)
                if not welt.frei(p, k.radius + 6, ebene, True):
                    continue
                if welt.sicht_frei(p, ort, ebene):
                    continue
                wert = p.distance_to(k.pos)
                if wert < beste:
                    bestes, beste = p, wert
            if bestes is not None:
                return bestes
        return None

    # ── Im Kampf ───────────────────────────────────────────────────
    def taktik_im_kampf(self, z, sichtbar: bool, ein: dict):
        """Was er statt des gewoehnlichen Kampfes tut, solange er einen
        Gegner im Blick hat: (Laufrichtung, Zielpunkt, frei_feuern) - oder
        None. `Zielpunkt` None heisst: wie immer auf den Gegner. Mit
        `frei_feuern` schiesst er auf den Zielpunkt, auch wenn er den
        Gegner nicht trifft - das ist Niederhalten."""
        k = self.k
        g = self.g
        b = K.BOTS
        jetzt = g.welt.zeit
        # Eine laufende Flanke geht weiter.
        if self.taktik is not None and self.taktik.get("gegen") is z:
            t = self.taktik
            fertig = (jetzt > t["bis"] or k.pos.distance_to(t["ort"]) < 14.0
                      or (sichtbar and self.linie == ""
                          and k.pos.distance_to(t["ort"]) < 60.0))
            if not fertig:
                return self._weg_richtung(t["ort"], t["ebene"], ein), None, False
            self.taktik = None
            self.flanke_pause = b["flanke_pause"]
        # Ein laufendes Niederhalten auch.
        if self.druck_rest > 0.0 and self.druck_gegen is z and self._munition_reicht():
            return pygame.Vector2(0, 0), self.druckpunkt(z.pos, z.ebene), True
        if not (sichtbar and self.linie == "hindernis"):
            return None
        # Er steht hinter einer Kiste. Einer flankiert, die anderen halten
        # ihn nieder - und wer allein ist, geht selbst herum.
        if self.flanke_pause <= 0.0 and rolle_frei(g, z, "flanke", k):
            if self.flanke_starten(z):
                return self._weg_richtung(self.taktik["ort"], self.taktik["ebene"],
                                          ein), None, False
        if self.druck_starten(z):
            return pygame.Vector2(0, 0), self.druckpunkt(z.pos, z.ebene), True
        return None

    def flanke_starten(self, gegen, ort=None, ebene=None) -> bool:
        k = self.k
        ort = pygame.Vector2(gegen.pos) if ort is None else pygame.Vector2(ort)
        ebene = k.ebene if ebene is None else ebene
        punkt = self.flankenpunkt(ort, ebene)
        if punkt is None:
            self.flanke_pause = 2.0     # gleich noch einmal suchen kostet nur
            return False
        self.taktik = dict(art="flanke", ort=punkt, ebene=ebene, gegen=gegen,
                           bis=self.g.welt.zeit + K.BOTS["flanke_zeit"])
        rolle_nehmen(self.g, gegen, "flanke", k, K.BOTS["flanke_zeit"])
        self.wegpunkt = None
        self.funken("flanke")
        return True

    def druck_starten(self, gegen, anlass: str = "druck") -> bool:
        if self.druck_pause > 0.0 or not self._munition_reicht():
            return False
        self.druck_rest = K.BOTS["druck_zeit"]
        self.druck_pause = K.BOTS["druck_zeit"] + K.BOTS["druck_pause"]
        self.druck_gegen = gegen
        rolle_nehmen(self.g, gegen, "druck", self.k, K.BOTS["druck_zeit"])
        self.funken(anlass)
        return True

    def _munition_reicht(self) -> bool:
        """Niederhalten frisst Munition. Nur, solange mehr als `druck_rest`
        des Gewohnten bleibt - die letzten Schuss sind fuer Treffer."""
        k = self.k
        for name in k.waffen:
            d = K.WAFFEN[name]
            if d.get("art") != "schuss":
                continue
            voll = d.get("magazin", 1) + K.MUNITION["vorrat"].get(name, 0)
            hat = k.magazin.get(name, 0) + k.vorrat.get(name, 0)
            if not k.knapp or hat > voll * K.BOTS["druck_rest"]:
                return True
        return False

    # ── Ohne Sicht ─────────────────────────────────────────────────
    def taktik_ohne_sicht(self, dt: float, ein: dict):
        """Kein Gegner im Blick, aber eben noch einer gesehen: niederhalten,
        wo er verschwunden ist, oder aussen herum gehen. Gibt (Laufrichtung,
        Zielpunkt, feuern) zurueck, oder None fuer den gewoehnlichen Weg."""
        k = self.k
        g = self.g
        b = K.BOTS
        jetzt = g.welt.zeit
        letzter = self.letzter_feind()
        # Eine laufende Flanke geht weiter, auch ohne Sicht.
        if self.taktik is not None:
            t = self.taktik
            if jetzt > t["bis"] or k.pos.distance_to(t["ort"]) < 14.0 \
                    or not getattr(t["gegen"], "lebt", False):
                self.taktik = None
                self.flanke_pause = b["flanke_pause"]
            else:
                blick = pygame.Vector2(letzter[0]) if letzter else None
                return self._weg_richtung(t["ort"], t["ebene"], ein), blick, False
        if letzter is None:
            return None
        ort, ebene, w = letzter
        if self.druck_rest > 0.0 and self.druck_gegen is w and self._munition_reicht():
            punkt = self.druckpunkt(ort, ebene)
            return pygame.Vector2(0, 0), punkt, self._abdruecken(dt, punkt, ein)
        # Ein Kamerad braucht Schutz in seiner Naehe, oder einer flankiert
        # ihn gerade: dann halten wir ihn unten.
        schutz = [x for x in self.kameraden() if braucht_schutz(x)
                  and x.ebene == ebene and x.pos.distance_to(ort) < b["feuerschutz_weite"]]
        flankiert = not rolle_frei(g, w, "flanke", k)
        if (schutz or flankiert) and rolle_frei(g, w, "druck", k):
            if self.druck_starten(w, "feuerschutz" if schutz else "druck"):
                punkt = self.druckpunkt(ort, ebene)
                return pygame.Vector2(0, 0), punkt, self._abdruecken(dt, punkt, ein)
        # Ist ein Kamerad frei in der Naehe, stuermen sie lieber zu zweit
        # (stuerme_fuehren plant das gleich) - allein herumzugehen kaeme
        # dem zuvor.
        if self.flanke_pause <= 0.0 and rolle_frei(g, w, "flanke", k) \
                and not self.sturm_moeglich():
            if self.flanke_starten(w, ort, ebene):
                return (self._weg_richtung(self.taktik["ort"], ebene, ein),
                        pygame.Vector2(ort), False)
        return None

    def sturm_moeglich(self) -> bool:
        """Koennte die Mannschaft gerade mit ihm einen Sturm planen?"""
        k = self.k
        g = self.g
        if not g.mit_teams:
            return False
        if getattr(g, "_sturm_pause", {}).get(k.team, -1e9) > g.welt.zeit:
            return False
        if any(p["team"] == k.team for p in getattr(g, "_stuerme", ())):
            return False
        for x in g._bots():
            if (x is not k and x.team == k.team and x.lebt and not x.am_boden
                    and x.ebene == k.ebene and x.hirn is not None
                    and x.hirn.sturm is None and x.hirn.ziel is None
                    and x.pos.distance_to(k.pos) < K.BOTS["sturm_weite"]):
                return True
        return False

    def _abdruecken(self, dt: float, punkt, ein: dict) -> bool:
        """Auf einen Punkt schiessen, auf den das Fadenkreuz gerade zeigt -
        in Feuerstoessen wie im Kampf, mit der Waffe, die passt."""
        k = self.k
        b = K.BOTS
        abstand = k.pos.distance_to(punkt)
        waffe = self._beste_waffe(abstand)
        if waffe is None:
            return False
        nr, _name = waffe
        if nr != k.waffe and self.waffen_rest <= 0.0 and k.nachlade_rest <= 0:
            ein["waffe"] = nr
            self.waffen_rest = 1.2
            return False
        if k.magazin.get(k.waffe_name, 0) <= 0:
            if k.nachlade_rest <= 0:
                ein["knoepfe"].append("nachladen")
            return False
        if (k.nachlade_rest > 0 or self.reaktion_rest > 0.0
                or abstand > b["reichweite"].get(k.waffe_name, 300.0)):
            return False
        from .bots import _winkel_diff, _winkel_zu
        if abs(_winkel_diff(self.blick, _winkel_zu(k.pos, punkt))) > 6.0:
            return False
        if self.stoss_rest <= 0.0 and self.pause_rest <= 0.0:
            # Je Waffe wie im Kampf (seit 0.34.38): ein MG haelt man auch
            # beim Niederhalten lange.
            self.stoss_rest, self._pause_naechste, _still = self._stoss()
        if self.stoss_rest > 0.0:
            if self.stoss_rest <= dt:
                self.pause_rest = self._pause_naechste
            return True
        return False

    # ── Sturm ──────────────────────────────────────────────────────
    def taktik_sturm(self, dt: float, ein: dict):
        """Der Plan der Mannschaft: (Laufrichtung, Blickpunkt, feuern) -
        oder None. Gefeuert wird hier nur die Granate vor dem Sturm."""
        plan = self.sturm
        if plan is None:
            return None
        k = self.k
        if plan.get("aus") or k not in plan["mitglieder"]:
            self.sturm = None
            return None
        ziel = pygame.Vector2(plan["ziel"])
        if plan["phase"] == "sammeln":
            # Jeder etwas versetzt, damit sie nicht aufeinander stehen.
            nr = plan["mitglieder"].index(k)
            ort = plan["sammel"] + (pygame.Vector2(16, 0).rotate(nr * 120.0)
                                    if nr else pygame.Vector2(0, 0))
            if k.pos.distance_to(ort) < 18.0:
                bereit = plan.setdefault("bereit", set())
                if k.nummer not in bereit:
                    bereit.add(k.nummer)
                    if nr:
                        self.funken("bereit")
                return pygame.Vector2(0, 0), ziel, False
            return self._weg_richtung(ort, plan["ebene"], ein), ziel, False
        # Hinein - der Erste wirft vorher, wenn er noch eine Granate hat.
        if self.sturm_wurf is not None and self.wurf_phase <= 0.0:
            self.wurf_platz = self._wurf_platz()
            if self.wurf_platz >= 0:
                self.wurf_phase = 0.45
                self.funken("granate", wichtig=True)
            else:
                self.sturm_wurf = None
        if self.wurf_phase > 0.0 and self.sturm_wurf is not None:
            will, punkt, werfen, _z = self._werfen(dt, ein, _Ort(*self.sturm_wurf))
            if werfen or self.wurf_phase <= 0.0:
                self.sturm_wurf = None
            return will, punkt, bool(werfen)
        return self._weg_richtung(ziel, plan["ebene"], ein), ziel, False


# ══════════════════════════════════════════════════════════════════
# Die Mannschaft: gemeinsam stuermen
# ══════════════════════════════════════════════════════════════════

def stuerme_fuehren(g, dt: float) -> None:
    """Beim Gastgeber, einmal je Schritt: laufende Stuerme weiterschalten,
    und wo zwei oder mehr Bots einer Mannschaft wissen, wo ein Gegner
    steckt, einen neuen planen. Gerechnet wird nur alle `sturm_takt`."""
    b = K.BOTS
    g._sturm_takt = getattr(g, "_sturm_takt", 0.0) - dt
    if g._sturm_takt > 0.0:
        return
    g._sturm_takt = b["sturm_takt"]
    stuerme = g.__dict__.setdefault("_stuerme", [])
    pausen = g.__dict__.setdefault("_sturm_pause", {})
    jetzt = g.welt.zeit
    for plan in list(stuerme):
        plan["mitglieder"] = [x for x in plan["mitglieder"]
                              if x.lebt and not x.am_boden
                              and g.kaempfer.get(x.nummer) is x]
        if len(plan["mitglieder"]) < 2 or jetzt > plan["bis"]:
            _sturm_ende(g, plan)
            continue
        if plan["phase"] == "sammeln":
            da = len(plan.get("bereit", ())) >= len(plan["mitglieder"])
            if da or jetzt > plan["sammeln_bis"]:
                plan["phase"] = "rein"
                plan["bis"] = jetzt + b["sturm_rein_zeit"]
                fuehrer = plan["mitglieder"][0]
                fuehrer.hirn.funken("rein", wichtig=True)
                fuehrer.hirn.sturm_wurf = (pygame.Vector2(plan["ziel"]), plan["ebene"])
        elif plan["phase"] == "rein":
            if all(x.pos.distance_to(plan["ziel"]) < 30.0 for x in plan["mitglieder"]):
                _sturm_ende(g, plan)
    if not g.mit_teams:
        return
    for team in range(len(K.TEAMS["namen"])):
        if pausen.get(team, -1e9) > jetzt or any(p["team"] == team for p in stuerme):
            continue
        # Wer in einem Trupp ist (seit 0.34.39), stuermt mit seinem Trupp,
        # nicht mit irgendwem aus der Mannschaft.
        frei = [x for x in g._bots()
                if x.team == team and x.lebt and not x.am_boden
                and x.hirn is not None and x.hirn.sturm is None
                and x.hirn.ziel is None and x.hirn.taktik is None
                and getattr(x.hirn, "trupp", None) is None]
        for a in frei:
            hinweis = a.hirn.letzter_feind()
            if hinweis is None:
                continue
            ort, ebene, _w = hinweis
            mit = [x for x in frei if x is not a and x.ebene == ebene
                   and x.pos.distance_to(a.pos) < b["sturm_weite"]]
            if not mit:
                continue
            sammel = a.hirn.sammelpunkt(ort, ebene)
            if sammel is None:
                continue
            plan = dict(team=team, mitglieder=[a] + mit[:3], ziel=pygame.Vector2(ort),
                        ebene=ebene, sammel=sammel, phase="sammeln",
                        sammeln_bis=jetzt + b["sturm_sammeln_zeit"],
                        bis=jetzt + b["sturm_sammeln_zeit"] + b["sturm_rein_zeit"] + 2.0)
            for x in plan["mitglieder"]:
                x.hirn.sturm = plan
                x.hirn.wegpunkt = None
            a.hirn.funken("sammeln", wichtig=True)
            stuerme.append(plan)
            pausen[team] = jetzt + b["sturm_pause"]
            break


def _sturm_ende(g, plan) -> None:
    plan["aus"] = True
    for x in plan["mitglieder"]:
        if getattr(x, "hirn", None) is not None and x.hirn.sturm is plan:
            x.hirn.sturm = None
            x.hirn.sturm_wurf = None
    stuerme = getattr(g, "_stuerme", [])
    if plan in stuerme:
        stuerme.remove(plan)


def unterdrueckung_pruefen(g) -> None:
    """Kugeln, die knapp an einem Bot vorbeifliegen, halten ihn unten -
    wie jeden, der weiss, was ihm da um die Ohren pfeift."""
    from .entities import Geschoss
    bots = [x for x in g._bots() if x.lebt and getattr(x, "hirn", None) is not None]
    if not bots:
        return
    weite = K.BOTS["unterdrueckt_weite"]
    for gs in g.welt.wesen:
        if not isinstance(gs, Geschoss) or not gs.lebt:
            continue
        for x in bots:
            if gs.ebene != x.ebene or gs.quelle_fraktion == x.fraktion:
                continue
            if gs.pos.distance_squared_to(x.pos) < weite * weite:
                if x.hirn.unterdrueckt <= 0.0:
                    x.hirn.funken("beschuss")
                x.hirn.unterdrueckt = K.BOTS["unterdrueckt_zeit"]
                x.hirn.kugel_vorbei()
