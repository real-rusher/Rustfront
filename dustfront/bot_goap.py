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

**Ein Mensch, kein Rechner (seit 0.34.38).** Gemeldet: "Dadurch, dass die
Gegner immer das Optimale ueberlegen, gehen sie aus der Deckung raus,
geben dir ein paar Schuesse ab, werden beschossen ... selbst wenn der
Gegner quasi tot ist, gehen sie dann eher in Deckung ... Ein Mensch
entscheidet nicht die ganze Zeit und fuehrt es sofort aus." Darum:

* **Innenleben** (innenleben.py): Stress und Zuversicht. Ereignisse -
  Kugeln, Treffer, ein Kamerad faellt, eine Granate - aendern sie; daraus
  Panik, Schreck, Uebermut. Wann er in Deckung geht, entscheidet der
  Stress, nicht jede einzelne Kugel.
* **Bindung**: ein Ziel haelt er eine Weile (goap.Ziel `bindung`), nur
  ein hoeherer Rang (Granate, Panik) reisst ihn sofort heraus.
* **Bedenkzeit**: wechselt er das Ziel, macht er noch kurz weiter, was er
  tat, bevor er das Neue angeht.
* **Hoeren** (`lagebild`): Schuesse, Explosionen und die Schritte eines
  Gegners in der Naehe, auch hinter einer Wand. Er schaut dorthin und
  sucht sich keine Deckung mitten zwischen Gegnern, die er kennt.
* **Umschauen**: ab und zu schaut er weg vom Ziel; unter Stress seltener -
  dann wirkt eine Flanke.
* **Granaten**: liegt eine neben ihm, rennt er weg - vor allem anderen.

Welche KI ein Bot hat, sagt die Regel BOT-KI (KLASSISCH / GOAP), im
Testmodus der Spawner. Was er gerade denkt, zeigt der Testmodus (Taste 8,
zweimal: Gedanken). Was spaeter noch kommt: docs/KI.md.
"""

from __future__ import annotations

import math

import pygame

from . import config as K
from . import wesen_daten
from .bots import BotHirn
from .bottaktik import braucht_schutz, rolle_frei
from .entities import Granate
from .innenleben import Innenleben, zuversicht_rechnen
from .trupp import richtung_wort, sieht_durch_rauch


def _nichts(status: str):
    """Stehen, nichts tun - jedes Mal ein neuer Vektor, weil der Aufrufer
    die Laufrichtung weiterrechnet."""
    return pygame.Vector2(0, 0), None, False, False, status


def _abstand_zur_strecke(p, a, b) -> float:
    ab = b - a
    lang = ab.length_squared()
    if lang < 1.0:
        return p.distance_to(a)
    t = max(0.0, min(1.0, (p - a).dot(ab) / lang))
    return p.distance_to(a + ab * t)


def staerke(w) -> float:
    """Wie viel einer im Gefecht zaehlt (s bei Days Gone): Leben, Waffe,
    niedergehalten. Ein Zombie zaehlt nach seinem Leben, weniger als ein
    Mensch mit Gewehr."""
    m = K.MORAL
    if not getattr(w, "lebt", False) or getattr(w, "am_boden", False):
        return 0.0
    if not hasattr(w, "nummer"):
        return min(3.0, 0.25 + getattr(w, "max_leben", 60.0) / 260.0)
    anteil = max(0.15, w.leben / max(1.0, w.max_leben))
    s = anteil * m["staerke_waffe"].get(getattr(w, "waffe_name", ""), 1.0)
    hirn = getattr(w, "hirn", None)
    if hirn is not None and getattr(hirn, "unterdrueckt", 0.0) > 0.0:
        s *= m["staerke_unterdrueckt"]
    return s


def faktor_von(w) -> float:
    """Wie zuversichtlich einer wirkt: ein GOAP-Bot nach seinem
    Innenleben, jeder andere neutral."""
    innen = getattr(getattr(w, "hirn", None), "innen", None)
    return innen.faktor if innen is not None else 1.0


class GoapHirn(BotHirn):
    """Ein Bot, der plant, statt einer festen Reihenfolge zu folgen."""

    ist_goap = True

    def __init__(self, gefecht, k, rnd, spezies: str = "mp_bot") -> None:
        self.spezies = spezies
        self.merkmale = None
        self.gehirn = None
        # Sein Trupp (seit 0.34.39, trupp.py) - gehoert zum Bot, nicht zum
        # Leben, wie die Merkmale.
        self.trupp = None
        super().__init__(gefecht, k, rnd)

    def liegt(self) -> None:
        """Am Boden: das Gehirn hat kein Ziel und keinen Plan mehr - er
        stirbt, er flankiert nicht (seit 0.34.46, gemeldet: "da steht dann
        immer noch, ich flankiere")."""
        super().liegt()
        if self.gehirn is not None and (self.gehirn.plan or self.gehirn.ziel is not None):
            self.gehirn.log("AM BODEN")
            self.gehirn.plan = []
            self.gehirn.ziel = None
        self._aktion_lief = None
        self._vorige = None
        self._bedenk_rest = 0.0
        self._lehnen = None
        self._ecke = None
        self._flucht = None
        self._wechsel = None
        self.funk_laeuft = None
        self.wurf_phase = 0.0

    def neues_leben(self) -> None:
        super().neues_leben()
        self.gehirn_neu()
        self._deckung_platz = None    # wo er in Deckung gegangen ist
        self.innen = Innenleben(self.merkmale or {}, self.rnd)
        self.lagebild = []            # gehoerte Orte: [Ort, Ebene, Zeit, Art]
        self._kameraden_da = {}       # Nummer -> Kaempfer, der eben noch stand
        self._feinde_da = {}          # Wesen -> zuletzt gesehen, solange es lebt
        self._abschuesse = []         # (Zeit, Staerke) der eigenen Seite in der Naehe
        self._verluste = []
        self._zuversicht_rest = 0.0
        self._umschau_rest = self.rnd.uniform(*K.MORAL["umschau"])
        self._umschau_bis = 0.0
        self._umschau_punkt = None
        self._bedenk_rest = 0.0
        self._vorige = None           # die Aktion vor dem Wechsel (Bedenkzeit)
        self._rang_vorher = 0.0
        self._feuerte = False
        self._flucht = None           # (Ort, bis wann)
        self._panik_vorher = False
        self._abwarten = 0.0          # so lange wartet er schon in der Deckung
        self._lehnen = None           # aus der Deckung schiessen: dict(phase, platz, punkt, bis)
        self._ecke = None             # Panik in Deckung: wohin er sich verkriecht
        self._wechsel = None          # Panik: die bessere Deckung, zu der er laeuft (0.34.48)
        self.funk_laeuft = None       # dict(art, bis, text): er spricht gerade in sein Funkgeraet
        self._rede_rest = self.rnd.uniform(3.0, 6.0)   # bis er beim Suchen etwas sagt

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
        self.gehirn = d.gehirn(self.spezies, self.merkmale, self.rnd) if sp else None
        if self.gehirn is not None:
            self.gehirn.erzwungen = erzwungen
        self.goap_rest = 0.0
        self._aktion_lief = None
        self._druck_lief = False

    # ── Ereignisse fuer das Innenleben ────────────────────────────
    def kugel_vorbei(self) -> None:
        self.innen.ereignis("vorbei")

    def _getroffen(self) -> None:
        super()._getroffen()
        k = self.k
        self.innen.ereignis("getroffen")
        if k.leben < K.BOTS["deckung_leben"]:
            self.innen.ereignis("angeschlagen")
        von = getattr(k, "zuletzt_von", None)
        von = getattr(von, "von", von)
        if von is not None and hasattr(von, "pos"):
            richtung = math.degrees(math.atan2(von.pos.y - k.pos.y, von.pos.x - k.pos.x))
            ab = (richtung - self.blick + 180.0) % 360.0 - 180.0
            if abs(ab) > 70.0:
                self.innen.ereignis("seite")

    def fehler_faktor(self) -> float:
        """Unter Stress zittert die Hand, in Panik schiesst er fast blind -
        und wer eben wiederbelebt wurde, zielt schlechter (0.34.40)."""
        f = 1.0 + 0.8 * self.innen.stress
        if self.innen.panik:
            f *= 2.5
        if self.geschwaecht:
            f *= K.VERWUNDET["danach_fehler"]
        return f

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
        if p is None:
            return False
        # Wer gerade aus der Deckung heraus schiesst (tun_aus_deckung), steht
        # ein Stueck daneben - und ist trotzdem in seiner Deckung.
        lehnt = self._lehnen is not None and self._lehnen["platz"] == p
        # Wer sich in Panik verkriecht (tun_verkriechen), geht nur einen Weg,
        # der ganz gedeckt ist - auch der zaehlt noch als seine Deckung, sonst
        # plante er mitten darin die Flucht.
        kriecht = self._ecke is not None
        weite = 20.0
        if lehnt:
            weite = K.BOTS["lehnen_weite"]
        elif kriecht:
            weite = K.BOTS["ecke_radien"][-1] + 20.0
        if self.k.pos.distance_to(p) > weite:
            return False
        gefahr = self._gefahr()
        if lehnt or kriecht or gefahr is None:
            return True
        return self.dicht_gedeckt(self.k.pos, gefahr[0])

    def dicht_gedeckt(self, p, gegen) -> bool:
        """Steht die Deckung zwischen ihm und `gegen` dicht vor ihm? Weit
        hinter einer Kiste, die nur irgendwo dazwischen steht, ist er nicht
        in Deckung (seit 0.34.48, gemeldet: "dass sie trotzdem denken, dass
        sie in Deckung sind, wenn sie recht weit hinter der Deckung stehen
        ... sie sollen schon an die Deckung rangehen")."""
        welt = self.g.welt
        k = self.k
        gegen = pygame.Vector2(gegen)
        hin = gegen - p
        if hin.length_squared() < 1.0:
            return False
        nah = p + hin.normalize() * min(hin.length(), K.BOTS["deckung_dicht"])
        return welt.deckung(gegen, p, k.ebene) != "" and welt.deckung(nah, p, k.ebene) != ""

    def fest_gedeckt(self, pos, ebene) -> bool:
        """Dicht gedeckt vor jedem Gegner, den er kennt - ohne Rauch: dorthin
        zieht er einen Verwundeten, bevor er ihm aufhilft (seit 0.34.48)."""
        for o in self.feind_orte():
            if o.distance_to(pos) <= K.BOTS["sicht"] and not self.dicht_gedeckt(pos, o):
                return False
        return True

    def feind_orte(self, ohne=None) -> list:
        """Alle Orte auf seiner Ebene, an denen er Gegner weiss: gesehen
        (frisch), gehoert und - im Trupp - gesagt bekommen. `ohne`: diesen
        Ort nicht."""
        k = self.k
        jetzt = self.g.welt.zeit
        raus = []
        for w, (ort, ebene, zeit) in self.gesehen.items():
            if w.lebt and ebene == k.ebene and jetzt - zeit <= K.BOTS["gedaechtnis"]:
                raus.append(pygame.Vector2(w.pos if jetzt - zeit < 0.2 else ort))
        if self.trupp is not None:
            for ort, ebene, w in self.trupp.feinde(k.ebene):
                if not any(ort.distance_to(o) < 40.0 for o in raus):
                    raus.append(ort)
        for ort, ebene, zeit, _art in self.lagebild:
            if ebene == k.ebene and not any(ort.distance_to(o) < 60.0 for o in raus):
                raus.append(pygame.Vector2(ort))
        if ohne is not None:
            raus = [o for o in raus if o.distance_to(ohne) > 30.0]
        return raus

    def _lagebild_auffrischen(self) -> None:
        """Was er hoert: Schuesse und Knalle der anderen Seite, und die
        Schritte eines Gegners in der Naehe - durch eine Wand nur naeher.
        Alles nur ungefaehr, wie ein Mensch es hoert."""
        k = self.k
        b = K.BOTS
        g = self.g
        jetzt = g.welt.zeit
        neu = []
        for (ort, ebene, zeit, fraktion, weite) in getattr(g, "_bot_geraeusche", ()):
            if jetzt - zeit > 0.25 or fraktion == k.fraktion:
                continue
            if k.pos.distance_to(ort) <= weite:
                neu.append((ort, ebene, "schuss", 55.0))
        if self.geblendet <= 0.0:
            for w in self._kandidaten():
                if w in self.gesehen and jetzt - self.gesehen[w][2] < 0.2:
                    continue
                tempo = getattr(w, "tempo", None)
                v = tempo.length() if tempo is not None else 0.0
                if v >= b["schritte_tempo"][0]:
                    weite = b["schritte"][0]
                elif v >= b["schritte_tempo"][1]:
                    weite = b["schritte"][1]
                else:
                    continue
                if w.ebene != k.ebene:
                    continue
                if not g.welt.sicht_frei(k.pos, w.pos, k.ebene):
                    weite *= b["schritte_wand"]
                if k.pos.distance_to(w.pos) <= weite:
                    neu.append((w.pos, w.ebene, "schritte", 25.0))
        for ort, ebene, art, unscharf in neu:
            p = pygame.Vector2(ort) + pygame.Vector2(self.rnd.uniform(-unscharf, unscharf),
                                                     self.rnd.uniform(-unscharf, unscharf))
            for eintrag in self.lagebild:
                if eintrag[1] == ebene and eintrag[0].distance_to(p) < 70.0:
                    eintrag[0] = (eintrag[0] + p) / 2
                    eintrag[2] = jetzt
                    eintrag[3] = art
                    break
            else:
                self.lagebild.append([p, int(ebene), jetzt, art])
                if not self._erklaert(p, ebene):
                    self.innen.ereignis("gehoert")
                    self._umschau_rest = 0.0       # gleich hinsehen
        self.lagebild = [e for e in self.lagebild if jetzt - e[2] <= b["lagebild"]][-12:]

    def _erklaert(self, ort, ebene) -> bool:
        """Sieht er dort schon einen Gegner? Dann ist das Geraeusch nichts Neues."""
        jetzt = self.g.welt.zeit
        for w, (o, e, zeit) in self.gesehen.items():
            if e == ebene and jetzt - zeit < 0.5 and w.pos.distance_to(ort) < 90.0:
                return True
        return False

    def unerklaert(self):
        """Das frischeste Geraeusch, zu dem er keinen Gegner sieht - oder None."""
        jetzt = self.g.welt.zeit
        for ort, ebene, zeit, _art in reversed(self.lagebild):
            if ebene == self.k.ebene and jetzt - zeit < 3.0 and not self._erklaert(ort, ebene):
                return ort
        return None

    def granate_nah(self):
        """Eine scharfe Granate (oder ein Molotow im Flug), die er sieht und
        deren Wirkungskreis ihn erreicht: (Ort, Radius) - oder None."""
        k = self.k
        welt = self.g.welt
        b = K.BOTS
        if self.geblendet > 0.0:
            return None
        beste = None
        for w in welt.wesen:
            if not isinstance(w, Granate) or not w.lebt or w.ebene != k.ebene:
                continue
            d = w.daten
            if d.get("rauch") or d.get("blend"):
                continue
            r = d.get("radius", 0.0) or (40.0 if d.get("feuer") else 0.0)
            if r <= 0.0:
                continue
            ab = k.pos.distance_to(w.pos)
            if ab > b["granate_sieht"] or ab > r + b["granate_abstand"]:
                continue
            if not welt.sicht_frei(k.pos, w.pos, k.ebene):
                continue
            if beste is None or ab < beste[2]:
                beste = (pygame.Vector2(w.pos), r, ab)
        return None if beste is None else beste[:2]

    def _zuversicht_rechnen(self) -> None:
        """Days Gone: eigene Seite gegen andere Seite, was er weiss."""
        k = self.k
        m = K.MORAL
        jetzt = self.g.welt.zeit
        weite = m["zuversicht_weite"]
        freunde = [(staerke(x), faktor_von(x)) for x in self.kameraden()
                   if x.ebene == k.ebene and x.pos.distance_to(k.pos) <= weite]
        feinde = []
        for w, (ort, ebene, zeit) in self.gesehen.items():
            if not w.lebt or jetzt - zeit > K.BOTS["gedaechtnis"]:
                continue
            c = faktor_von(w)
            # Wer auf ihn zustuermt, macht Eindruck (Days Gone: wer den
            # Spieler angreifen laesst, belohnt ihn fuer Mut).
            tempo = getattr(w, "tempo", None)
            if tempo is not None and tempo.length() > 60.0 * K.BEWEGUNG["lauf"]:
                hin = k.pos - w.pos
                if hin.length_squared() > 1.0 and tempo.normalize().dot(hin.normalize()) > 0.6:
                    c *= 1.3
            feinde.append((staerke(w), c))
        for ort, ebene, zeit, _art in self.lagebild:
            if ebene == k.ebene and not self._erklaert(ort, ebene):
                feinde.append((0.6, 1.0))     # gehoert, nicht gesehen: halb so schwer
        abbau = m["verlust_abbau"]
        getoetet = sum(s * math.exp(-(jetzt - t) / abbau) for t, s in self._abschuesse)
        verloren = sum(s * math.exp(-(jetzt - t) / abbau) for t, s in self._verluste)
        self.innen.zuversicht_setzen(zuversicht_rechnen(staerke(k), freunde, feinde,
                                                        getoetet, verloren))

    def _verluste_zaehlen(self) -> None:
        """Wer von der eigenen Seite eben fiel, und wen sie erwischt hat."""
        k = self.k
        jetzt = self.g.welt.zeit
        weite = K.MORAL["zuversicht_weite"]
        da = {}
        for x in self.kameraden():
            if not getattr(x, "am_boden", False):
                da[x.nummer] = x
        for nummer, x in self._kameraden_da.items():
            if nummer in da:
                continue
            if x.ebene == k.ebene and x.pos.distance_to(k.pos) <= weite * 1.4:
                self._verluste.append((jetzt, max(0.5, staerke(x) or 1.0)))
                self.innen.ereignis("kamerad")
        self._kameraden_da = da
        for w in list(self._feinde_da):
            if not w.lebt or getattr(w, "am_boden", False):
                ort = self._feinde_da.pop(w)
                if ort.distance_to(k.pos) <= weite * 1.4:
                    self._abschuesse.append((jetzt, 1.0))
                    self.innen.ereignis("abschuss")
        for w, (ort, ebene, zeit) in self.gesehen.items():
            if w.lebt and jetzt - zeit < 1.0:
                self._feinde_da[w] = pygame.Vector2(ort)
        self._abschuesse = self._abschuesse[-10:]
        self._verluste = self._verluste[-10:]

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
        innen = self.innen
        waffe = k.waffe_name
        ziel_leben = (z.leben / max(1.0, getattr(z, "max_leben", 100.0))) if sichtbar else 1.0
        fakten = dict(
            feind_sichtbar=sichtbar,
            linie_frei=sichtbar and self.linie != "hindernis",
            feind_bekannt=gefahr is not None,
            feind_gehoert=self.unerklaert() is not None,
            munition_da=bool(self._waffen_mit_munition()),
            magazin_leer=magazin_leer,
            granate_da=self._wurf_platz() >= 0
            and K.WAFFEN[k.waffen[self._wurf_platz()]].get("radius", 0.0) > 0.0,
            angeschlagen=k.leben < K.BOTS["deckung_leben"],
            getroffen=self.getroffen_rest > 0.0,
            unterdrueckt=self.unterdrueckt > 0.0,
            in_deckung=self._in_deckung(),
            beruhigt=innen.stress < 0.3,
            kamerad_liegt=self._wem_helfen() is not None,
            kamerad_braucht_schutz=any(braucht_schutz(x) for x in self.kameraden()),
            kamerad_flankiert=gegen is not None and not rolle_frei(g, gegen, "flanke", k),
            flanke_frei=(gegen is not None and self.flanke_pause <= 0.0
                         and rolle_frei(g, gegen, "flanke", k)),
            zone_aktiv=zone is not None,
            im_kreis=im_kreis,
            sturm_plan=self.sturm is not None,
            granate_nah=self.granate_nah() is not None,
            panik=innen.panik,
            eingeschossen=innen.eingeschossen >= K.MORAL["eingeschossen_ab"],
            waffe_mg=waffe == "lmg",
            waffe_auto=waffe in K.BOTS["feuer"],
            feinde_gruppe=sichtbar and len(self.gruppe_um(z)) >= 2,
            ziel_fast_tot=sichtbar and ziel_leben < 0.3,
        )
        fakten.update(self._trupp_fakten())
        fakten.update(self._bergung_fakten())
        fakten["geschwaecht"] = self.geschwaecht
        werte = dict(leben=k.leben / max(1.0, k.max_leben),
                     abstand=k.pos.distance_to(gefahr[0]) if gefahr else 9999.0,
                     stress=round(innen.stress, 3),
                     zuversicht=innen.stufe / 4.0,
                     unschaerfe=innen.unschaerfe())
        return fakten, werte

    # ── Im Trupp (seit 0.34.39) ───────────────────────────────────
    def _trupp_fakten(self) -> dict:
        """Was er ueber seinen Trupp weiss. Ohne Trupp - oder als Letzter
        uebrig - ist alles falsch, und er ist ein Bot wie jeder andere."""
        t = self.trupp
        k = self.k
        leer = dict(im_trupp=False, ist_fuehrer=False, hat_funk=False, allein=False,
                    in_formation=True, trupp_rueckzug=False, trupp_druck=False,
                    trupp_halten=False, welle_dran=False, flanke_rolle=False,
                    trupp_unterlegen=False, hilfe_gerufen=False, lage_neu=False,
                    antwort_offen=False, hilfe_zugesagt=False, rauch_da=False,
                    trupp_igel=False, trupp_engstelle=False)
        rauch = self._rauch_platz() >= 0
        if t is None or len(t.lebende()) < 2 or k not in t.lebende():
            leer["rauch_da"] = rauch
            return leer
        fuehrer = t.fuehrt(k)
        funk = bool(getattr(k, "funkgeraet", False))
        p = t.stellung(k)
        return dict(
            im_trupp=True,
            ist_fuehrer=fuehrer,
            hat_funk=funk,
            allein=not t.in_kontakt(k),
            in_formation=p is None or k.pos.distance_to(p) <= K.TRUPP["stellung_weite"],
            trupp_rueckzug=t.zustand == "rueckzug",
            trupp_druck=t.zustand == "druck",
            trupp_halten=t.zustand == "halten",
            welle_dran=k.nummer in t.welle,
            flanke_rolle=k.nummer in t.flanker,
            trupp_unterlegen=t.unterlegen(),
            hilfe_gerufen=t.hilfe_gerufen(),
            lage_neu=fuehrer and funk and t.lage_neu(),
            antwort_offen=fuehrer and funk and t.antwort_offen(),
            hilfe_zugesagt=t.hilfe is not None and bool(t.hilfe.get("zugesagt")),
            rauch_da=rauch,
            trupp_igel=t.zustand == "igel",
            trupp_engstelle=t.zustand == "engstelle",
        )

    # ── Bergen (seit 0.34.40) ─────────────────────────────────────
    def _opfer(self):
        """Wen er bergen soll: im Trupp den, den der Trupp birgt; sonst den
        naechsten Gefallenen seiner Mannschaft."""
        t = self.trupp
        if t is not None and t.bergung is not None:
            x = t.bergung["opfer"]
            if x.lebt and getattr(x, "am_boden", False):
                return x
        return self._wem_helfen()

    def bedrohung(self, x) -> int:
        """Wie viele Gegner, von denen er weiss, den Liegenden sehen - nah
        genug und ohne Rauch dazwischen."""
        welt = self.g.welt
        n = 0
        for o in self.feind_orte():
            if o.distance_to(x.pos) > K.VERWUNDET["bedrohung"]:
                continue
            if sieht_durch_rauch(welt, o, x.pos, x.ebene):
                n += 1
        return n

    def _im_rauch(self, pos, ebene) -> bool:
        return any(r.ebene == ebene and r.deckt(pos, ebene) for r in self.g.welt.rauch)

    def gedeckt(self, pos, ebene) -> bool:
        """Liegt diese Stelle vor jedem Gegner, den er kennt, in Deckung
        (oder im Rauch)?"""
        if self._im_rauch(pos, ebene):
            return True
        welt = self.g.welt
        for o in self.feind_orte():
            if o.distance_to(pos) <= K.VERWUNDET["bedrohung"] * 1.5 \
                    and welt.deckung(o, pos, ebene) == "" and sieht_durch_rauch(welt, o, pos, ebene):
                return False
        return True

    def _bergung_fakten(self) -> dict:
        k = self.k
        x = self._opfer()
        if x is None:
            return dict(bei_kamerad=False, kamerad_gedeckt=False, ich_berge=False,
                        bergen_sicher=False, bergung_laeuft=False)
        t = self.trupp
        if t is not None and t.bergung is not None and t.bergung["opfer"] is x:
            ich = k.nummer in t.bergung["retter"]
            sicher = t.bergung["sicher"]
        else:
            # Ohne Trupp: die zwei, die am naechsten sind, und nur, wenn ihn
            # keiner sieht - ausser er ist sich seiner Sache sehr sicher.
            naechste = sorted((m for m in self.kameraden() + [k]
                               if not getattr(m, "am_boden", False) and m.ebene == x.ebene),
                              key=lambda m: m.pos.distance_to(x.pos))
            ich = k in naechste[:K.VERWUNDET["retter"]]
            sicher = self.bedrohung(x) == 0 or self.innen.stufe >= 3
        laeuft = any(getattr(m, "zieht", None) == x.nummer or getattr(m, "hilft", None) == x.nummer
                     for m in self.kameraden() + [k])
        return dict(bei_kamerad=x.ebene == k.ebene
                    and k.pos.distance_to(x.pos) <= K.REVIVE["reichweite"] - 4,
                    # Fest gedeckt, nicht nur im Rauch: erst dorthin ziehen, dann
                    # aufhelfen (seit 0.34.48, gemeldet: "die Teammates immer
                    # erst hinter eine gute und sichere Deckung bergen").
                    kamerad_gedeckt=self.fest_gedeckt(x.pos, x.ebene),
                    ich_berge=ich, bergen_sicher=sicher, bergung_laeuft=laeuft)

    def bergeplatz(self, x):
        """Wohin er den Liegenden zieht: die naechste Stelle um ihn, die vor
        jedem bekannten Gegner gedeckt ist und die er geradewegs erreicht."""
        k = self.k
        welt = self.g.welt
        bestes, beste = None, 1e9
        for r in K.VERWUNDET["deckung_radien"]:
            for i in range(12):
                p = x.pos + pygame.Vector2(r, 0).rotate(i * 30.0)
                if not welt.frei(p, k.radius + 2, x.ebene, True):
                    continue
                if not self.fest_gedeckt(p, x.ebene):
                    continue
                if not welt.wege.gerade_frei(x.ebene, x.pos, p, k.radius + 1):
                    continue
                wert = p.distance_to(x.pos) + 0.5 * p.distance_to(k.pos)
                orte = self.feind_orte()
                if orte and welt.deckung(sum(orte, pygame.Vector2(0, 0)) / len(orte), p, x.ebene) == "wand":
                    wert -= K.BOTS["deckung_wand"]    # hinter eine Mauer, lieber als hinter ein Fass
                if wert < beste:
                    bestes, beste = p, wert
            if bestes is not None:
                return bestes
        return None

    def _rauch_platz(self) -> int:
        k = self.k
        for i, name in enumerate(k.waffen):
            if K.WAFFEN[name].get("rauch") and (k.magazin.get(name, 0) > 0
                                                or k.vorrat.get(name, 0) > 0):
                return i
        return -1

    def _stellung(self):
        t = self.trupp
        if t is None or len(t.lebende()) < 2:
            return None
        return t.stellung(self.k)

    def letzter_feind(self):
        """Wen er zuletzt gesehen hat - oder, im Trupp, wen ihm einer
        gesagt hat (die Lage des Trupps)."""
        eigen = super().letzter_feind()
        if eigen is not None or self.trupp is None:
            return eigen
        k = self.k
        bester = None
        for ort, ebene, w in self.trupp.feinde(k.ebene):
            d = k.pos.distance_to(ort)
            if bester is None or d < bester[0]:
                bester = (d, (ort, ebene, w))
        return None if bester is None else bester[1]

    def _ziel_bonus(self, w) -> float:
        """Im Trupp: wer dem Anfuehrer zu nahe kommt, zuerst - und lieber
        der, auf den schon ein Kamerad schiesst (Feuer buendeln, Killzone)."""
        t = self.trupp
        if t is None:
            return 0.0
        bonus = 0.0
        f = t.fuehrer
        if (f is not None and f is not self.k and f.lebt and f.ebene == w.ebene
                and f.pos.distance_to(w.pos) < K.TRUPP["fuehrer_schutz"]):
            bonus += K.TRUPP["fuehrer_bonus"]
        if any(getattr(m.hirn, "ziel", None) is w for m in t.lebende() if m is not self.k):
            bonus += K.TRUPP["buendeln_bonus"]
        return bonus

    def _kampfbewegung(self, abstand: float, z, ein=None):
        """Im Trupp kaempft er von seiner Stellung aus (seiner Bahn), statt
        frei hin und her zu laufen - so stehen sie nebeneinander und nicht
        in einer Reihe."""
        p = self._stellung()
        if p is None:
            return super()._kampfbewegung(abstand, z, ein)
        k = self.k
        if k.pos.distance_to(p) > K.TRUPP["stellung_weite"]:
            return self._weg_richtung(p, k.ebene, ein)
        if self.seite_rest <= 0.0:
            self.seite_rest = self.rnd.uniform(0.7, 1.6)
            self.seite = -self.seite
        hin = z.pos - k.pos
        if hin.length_squared() < 1.0:
            return pygame.Vector2(0, 0)
        hin = hin.normalize()
        return pygame.Vector2(-hin.y, hin.x) * self.seite * 0.35

    def _unterwegs(self, dt: float, ein: dict):
        """Ohne Kontakt im Trupp: die anderen gehen in breiter Linie neben
        dem Anfuehrer und schauen nach aussen; der Anfuehrer geht vor und
        wartet, wenn einer zurueckfaellt. Ab und zu sagt einer, was er
        sieht - oder dass nichts ist."""
        t = self.trupp
        k = self.k
        if t is None or len(t.lebende()) < 2 or k not in t.lebende():
            return super()._unterwegs(dt, ein)
        self.stoss_rest = 0.0
        if k is t.fuehrer:
            ziel = t.ziel_ort()
            if ziel is not None:
                will = self._weg_richtung(ziel, t.auftrag.get("ebene", k.ebene), ein)
                if k.pos.distance_to(ziel) < 40.0:
                    will = pygame.Vector2(0, 0)
                blick = None
            else:
                will, blick = super()._unterwegs(dt, ein)
            weit = K.TRUPP["linie_abstand"] * K.TRUPP["linie_warten"]
            for m in t.lebende():
                q = t.stellung(m)
                if m is not k and q is not None and m.pos.distance_to(q) > weit:
                    will = will * 0.2          # warten, bis sie aufschliessen
                    break
            return will, blick
        p = t.stellung(k)
        if p is None:
            return super()._unterwegs(dt, ein)
        will = pygame.Vector2(0, 0)
        if k.pos.distance_to(p) > 10.0:
            will = self._weg_richtung(p, k.ebene, ein)
        # Nach aussen schauen: zur Seite, auf der er in der Linie steht.
        f = t.fuehrer
        blick = None
        if f is not None and f.lebt:
            aussen = k.pos - f.pos
            if aussen.length_squared() > 1.0:
                vor = pygame.Vector2(1, 0).rotate(f.hirn.blick)
                blick = k.pos + (aussen.normalize() + vor).normalize() * 120.0
        self._rede_rest -= dt
        if self._rede_rest <= 0.0:
            self._rede_rest = self.rnd.uniform(5.0, 9.0)
            seite = "LINKS" if f is not None and (k.pos - f.pos).cross(
                pygame.Vector2(1, 0).rotate(f.hirn.blick)) > 0 else "RECHTS"
            ort = self.unerklaert()
            if ort is not None:
                self.sagen("DA WAR WAS, %s!" % richtung_wort(k.pos, ort))
            else:
                self.sagen(self.rnd.choice(("%s FREI." % seite, "NICHTS ZU SEHEN.",
                                            "%s SAUBER." % seite)))
        return will, blick

    # ── Entscheiden ───────────────────────────────────────────────
    def _entscheiden(self, dt: float, ein: dict):
        if self.gehirn is None:
            return super()._entscheiden(dt, ein)
        innen = self.innen
        innen.schritt(dt, self._in_deckung(), self._feuerte)
        self._zuversicht_rest -= dt
        self.goap_rest -= dt
        if self.goap_rest <= 0.0 or self.gehirn.aktion is None:
            self.goap_rest = K.GOAP["takt"]
            self._lagebild_auffrischen()
            self._verluste_zaehlen()
            if self._zuversicht_rest <= 0.0:
                self._zuversicht_rest = 0.5
                self._zuversicht_rechnen()
            if self.granate_nah() is not None:
                innen.ereignis("granate")
            fakten, werte = self.fuehlen()
            vorher = self._aktion_lief
            self.gehirn.denken(self.g.welt.zeit, fakten, werte)
            rang = self.gehirn.raenge.get(self.gehirn.ziel.name, 0.0) if self.gehirn.ziel else 0.0
            if (self.gehirn.gewechselt and vorher is not None and rang <= self._rang_vorher
                    and rang < 2):
                # Bedenkzeit: kurz macht er weiter, was er tat - ein Mensch
                # schaltet nicht im selben Augenblick um.
                lo, hi = K.MORAL["bedenkzeit"]
                drill = float(self.merkmale.get("drill", 0.0)) if self.merkmale else 0.0
                self._bedenk_rest = (self.rnd.uniform(lo, hi) * (1.0 + innen.stress)
                                     * (1.0 - 0.5 * drill))
                self._vorige = vorher
            elif rang >= 2:
                self._bedenk_rest = 0.0
            self._rang_vorher = rang
        if innen.panik and not self._panik_vorher:
            self.funken("panik", wichtig=True)
        self._panik_vorher = innen.panik
        # Schreck: einen Augenblick tut er gar nichts. Nur eine Granate
        # vor den Fuessen und die Panik sind staerker.
        if innen.erschrocken and not innen.panik and not self.gehirn.fakten.get("granate_nah"):
            self._feuerte = False
            gefahr = self._gefahr()
            return pygame.Vector2(0, 0), (gefahr[0] if gefahr else None), False, False
        will, punkt, feuern, zielt = self._handeln(dt, ein)
        will, punkt, feuern = self._umschauen(dt, will, punkt, feuern)
        if feuern and punkt is not None and self.vorn_zu(punkt):
            # Die eigene Deckung steht davor: nicht hineinschiessen, keine
            # Granate dagegen. Ein Wurf, der so nicht geht, faellt aus.
            feuern = False
            if self.wurf_phase > 0.0:
                self.wurf_phase = 0.0
        self._feuerte = bool(feuern)
        return will, punkt, feuern, zielt

    def _handeln(self, dt: float, ein: dict):
        a = self.gehirn.aktion
        if self._bedenk_rest > 0.0:
            self._bedenk_rest -= dt
            alt = self._vorige
            tun = TUN.get(alt.tut) if alt is not None else None
            if tun is not None:
                will, punkt, feuern, zielt, status = tun(self, dt, ein)
                if status == "laeuft":
                    return will, punkt, feuern, zielt
            self._vorige = None
            gefahr = self._gefahr()
            return pygame.Vector2(0, 0), (gefahr[0] if gefahr else None), False, False
        if a is None:
            # Nichts zu tun: herumgehen und suchen, wie die klassische KI.
            will, punkt = self._unterwegs(dt, ein)
            ort = self.unerklaert()
            if ort is not None:
                punkt = pygame.Vector2(ort)
            return will, punkt, False, False
        if a is not self._aktion_lief:
            self._aktion_lief = a
            self._druck_lief = False
            self._abwarten = 0.0
            if a.tut != "aus_deckung":
                self._lehnen = None           # sonst zaehlte der Lehnpunkt weiter als Deckung
            if a.tut != "verkriechen":
                self._ecke = None
            if a.tut != "deckung_wechseln":
                self._wechsel = None
            if not a.tut.startswith("funk"):
                self.funk_laeuft = None       # unterbrochen: der Spruch ist nicht raus
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

    def _umschauen(self, dt: float, will, punkt, feuern):
        """Ab und zu weg vom Ziel schauen - zu dem, was er hoert, oder zur
        Seite. Nie mitten im Feuerstoss, nie in Panik; unter Stress seltener
        (Tunnelblick). Waehrend er wegschaut, schiesst er nicht, und danach
        muss er sich wieder einzielen."""
        m = K.MORAL
        jetzt = self.g.welt.zeit
        if jetzt < self._umschau_bis and self._umschau_punkt is not None:
            return will, pygame.Vector2(self._umschau_punkt), False
        self._umschau_rest -= dt
        if (self._umschau_rest > 0.0 or feuern or self.stoss_rest > 0.0 or self.innen.panik
                or self.wurf_phase > 0.0):
            return will, punkt, feuern
        self._umschau_rest = self.rnd.uniform(*m["umschau"]) * (1.0 + 2.0 * self.innen.stress)
        k = self.k
        ort = self.unerklaert()
        if ort is None:
            gefahr = self._gefahr()
            if gefahr is None:
                return will, punkt, feuern
            # Zur Seite: dorthin, wo keiner ist, von dem er weiss.
            hin = gefahr[0] - k.pos
            if hin.length_squared() < 1.0:
                return will, punkt, feuern
            ort = k.pos + hin.normalize().rotate(self.rnd.choice((-1, 1))
                                                 * self.rnd.uniform(80.0, 150.0)) * 120.0
        self._umschau_punkt = pygame.Vector2(ort)
        self._umschau_bis = jetzt + self.rnd.uniform(*m["umschau_dauer"])
        self.fehler_zeit *= 0.5
        return will, pygame.Vector2(ort), False

    # ── Deckung mit Ueberblick ────────────────────────────────────
    deckung_weiter = 1                # bots._deckung_suchen: einen Ring weiter
    def _deckung_wert(self, p, gefahr, zone):
        """Wie bei der klassischen KI, dazu jeder andere Gegner, den er
        kennt: keine Deckung mitten zwischen ihnen, keine, die zu einem
        anderen offen ist, und kein Weg dorthin an ihnen vorbei. In Panik
        sieht er nur den einen, vor dem er wegrennt (Tunnelblick)."""
        wert = super()._deckung_wert(p, gefahr, zone)
        if wert is None or self.innen.panik:
            return wert
        k = self.k
        welt = self.g.welt
        for o in self.feind_orte(ohne=gefahr):
            d = p.distance_to(o)
            if d < 110.0 and d < k.pos.distance_to(o):
                return None                   # mitten hinein: nein
            if _abstand_zur_strecke(o, k.pos, p) < 70.0:
                wert += 260.0                 # der Weg fuehrt an ihm vorbei
            if welt.deckung(o, p, k.ebene) == "":
                wert += 90.0                  # gegen ihn deckt sie nicht
        return wert + self._deckung_guete(p, gefahr)

    def _deckung_guete(self, p, gefahr) -> float:
        """Volle Deckung vor halber (seit 0.34.46). Gemeldet: "sie sollen
        eher volle Deckung wie Mauern priorisieren und sich dann an den
        Endpunkten der Mauern splitten ... nicht jeder hinter einen Barrel."
        Eine Mauer (sichtdicht) zaehlt mehr als ein Fass; eine Stelle, die
        schon ein leicht flankierender Gegner trifft, weniger; eine, von der
        aus er sich herauslehnen kann (Mauerende), mehr; und eine, an der
        schon ein Kamerad sitzt, weniger."""
        b = K.BOTS
        k = self.k
        welt = self.g.welt
        gefahr = pygame.Vector2(gefahr)
        if not self.dicht_gedeckt(p, gefahr):
            return 1e6                        # nur hinter, nicht weit hinter einer Deckung
        wert = 0.0
        # Zu nah am Gegner fuer seine Waffe: lieber eine weiter hinten.
        nah = K.BOTS["wunschabstand"].get(k.waffe_name, 220.0) * b["deckung_mindest"]
        d = p.distance_to(gefahr)
        if d < nah:
            wert += (nah - d) * b["deckung_zu_nah"]
        if welt.deckung(gefahr, p, k.ebene) == "wand":
            wert -= b["deckung_wand"]
        hin = gefahr - p
        for w in (-b["deckung_flanke_winkel"], b["deckung_flanke_winkel"]):
            if welt.deckung(p + hin.rotate(w), p, k.ebene) == "":
                wert += b["deckung_flanke"]
        if self.lehnpunkt(p, gefahr) is not None:
            wert -= b["deckung_ecke"]
        for x in self.kameraden():
            if x.ebene != k.ebene:
                continue
            platz = getattr(getattr(x, "hirn", None), "deckung_ort", None)
            if platz is None:
                platz = x.pos
            if pygame.Vector2(platz).distance_to(p) < b["deckung_belegt"]:
                wert += b["deckung_belegt_strafe"]
        return wert

    # ── Was die Aktionen tun ──────────────────────────────────────
    # Jede gibt (Laufrichtung, Zielpunkt, feuern, zielen, Zustand) zurueck;
    # Zustand ist "laeuft", "fertig" oder "gescheitert".

    def tun_kaempfen(self, dt, ein):
        z = self.ziel
        if z is None or not self.ziel_ok(z):
            return _nichts("fertig")
        return self._kaempfen(dt, ein, mit_deckung=False) + ("laeuft",)

    def tun_dauerfeuer(self, dt, ein):
        """Auf eine Gruppe halten: stehen bleiben, lange Stoesse, ueber die
        ganze Gruppe schwenken (das Schwenken macht _kaempfen). Ohne Gruppe
        ist es vorbei."""
        z = self.ziel
        if z is None or not self.ziel_ok(z):
            return _nichts("fertig")
        if len(self.gruppe_um(z)) < 2:
            return _nichts("fertig")
        will, punkt, feuern, zielt = self._kaempfen(dt, ein, mit_deckung=False)
        if self.wurf_phase <= 0.0:
            will = pygame.Vector2(0, 0)
        return will, punkt, feuern, zielt, "laeuft"

    def tun_werfen(self, dt, ein):
        """Die Granate in eine Gruppe (in ihre Mitte, bots._werfen)."""
        z = self.ziel
        if self.wurf_phase <= 0.0:
            if z is None or not self.ziel_ok(z):
                return _nichts("gescheitert")
            self.wurf_platz = self._wurf_platz()
            nah, weit = K.BOTS["wurf_weite"]
            if self.wurf_platz < 0 or not (nah <= self.k.pos.distance_to(z.pos) <= weit * 1.1):
                return _nichts("gescheitert")
            if self.vorn_zu(z.pos):
                return _nichts("gescheitert")     # erst aus der Deckung heraus
            self.wurf_phase = 0.45
            self.wurf_rest = self.rnd.uniform(*K.BOTS["wurf_pause"])
            self.funken("granate", wichtig=True)
        ziel = z if (z is not None and z.lebt) else None
        if ziel is None:
            self.wurf_phase = 0.0
            return _nichts("gescheitert")
        will, punkt, werfen, zielt = self._werfen(dt, ein, ziel)
        return will, punkt, werfen, zielt, ("fertig" if werfen else "laeuft")

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

    def tun_abwarten(self, dt, ein):
        """In der Deckung bleiben, bis er sich gefangen hat - nachladen,
        wenn es sich lohnt, und dorthin schauen, wo der Gegner war. Laenger
        als `abwarten` haelt es keiner aus."""
        k = self.k
        if not self._in_deckung():
            return _nichts("gescheitert")
        if self.innen.stress < 0.3:
            return _nichts("fertig")
        self._abwarten += dt
        if self._abwarten > 4.0:
            self._abwarten = 0.0
            return _nichts("fertig")
        d = k.waffe_daten
        if (d.get("art") == "schuss" and k.nachlade_rest <= 0
                and k.magazin.get(k.waffe_name, 0) < d.get("magazin", 0) * 0.5
                and (not k.knapp or k.vorrat.get(k.waffe_name, 0) > 0)):
            ein["knoepfe"].append("nachladen")
        gefahr = self._gefahr()
        return pygame.Vector2(0, 0), (gefahr[0] if gefahr else None), False, False, "laeuft"

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

    def tun_ausweichen(self, dt, ein):
        """Weg von der Granate - geradewegs, so schnell es geht. Wohin, ist
        egal, solange es weg ist; nur nicht in eine Wand."""
        k = self.k
        gr = self.granate_nah()
        if gr is None:
            return _nichts("fertig")
        ort, _r = gr
        weg = k.pos - ort
        if weg.length_squared() < 1.0:
            weg = pygame.Vector2(1, 0).rotate(self.rnd.uniform(0, 360))
        self.funken("granate_weg", wichtig=True)
        self.stoss_rest = 0.0
        return weg.normalize(), None, False, False, "laeuft"

    # ── Aus der Deckung (seit 0.34.43) ───────────────────────────
    def lehnpunkt(self, platz, gefahr):
        """Eine Stelle dicht neben der Deckung, von der aus nichts zwischen
        ihm und dem Gegner steht - dort lehnt er sich heraus."""
        k = self.k
        welt = self.g.welt
        hin = gefahr - platz
        if hin.length_squared() < 1.0:
            return None
        hin = hin.normalize()
        quer = pygame.Vector2(-hin.y, hin.x)
        for d in K.BOTS["lehnen_versatz"]:
            for seite in (self.seite, -self.seite):
                p = platz + quer * (seite * d) + hin * 4.0
                if not welt.frei(p, k.radius + 1, k.ebene, True):
                    continue
                if not welt.wege.gerade_frei(k.ebene, platz, p, k.radius):
                    continue
                if welt.deckung(p, gefahr, k.ebene) == "":
                    return p
        return None

    def tun_aus_deckung(self, dt, ein):
        """Aus der Deckung kaempfen, wie man es tut: drin warten, sich zur
        Seite herauslehnen, ein Feuerstoss, zurueck - und wieder. Gemeldet:
        "Bots blieben teils immer noch im Freien stehen und gruppierten
        sich dort. Sie sollen schon priorisieren, in Deckung zu gehen."
        Sieht er den Gegner vom Lehnpunkt aus nicht mehr, haelt er dorthin
        nieder, wo er war."""
        k = self.k
        b = K.BOTS
        jetzt = self.g.welt.zeit
        gefahr = self._gefahr()
        platz = self._deckung_platz
        if gefahr is None:
            self._lehnen = None
            return _nichts("fertig")
        if platz is None:
            return _nichts("gescheitert")
        st = self._lehnen
        if st is None or st["platz"] != platz:
            st = self._lehnen = dict(phase="drin", platz=pygame.Vector2(platz), punkt=None,
                                     bis=jetzt + self.rnd.uniform(*b["lehnen_warten"]) * 0.5,
                                     geschossen=False)
        ort = pygame.Vector2(gefahr[0])
        if st["phase"] == "drin":
            if k.pos.distance_to(platz) > 4.0:
                return self._weg_richtung(platz, k.ebene, ein), ort, False, False, "laeuft"
            if jetzt >= st["bis"]:
                punkt = self.lehnpunkt(platz, ort)
                if punkt is None:
                    self._lehnen = None
                    return _nichts("gescheitert")
                st.update(phase="raus", punkt=punkt, bis=jetzt + b["lehnen_raus"], geschossen=False)
            return pygame.Vector2(0, 0), ort, False, False, "laeuft"
        if st["phase"] == "raus":
            if k.pos.distance_to(st["punkt"]) > 4.0 and not st["geschossen"]:
                return self._weg_richtung(st["punkt"], k.ebene, ein), ort, False, False, "laeuft"
            z = self.ziel
            if z is not None and self.ziel_ok(z) and self.linie == "":
                _w, punkt, feuern, zielt = self._kaempfen(dt, ein, mit_deckung=False)
                if feuern:
                    st["geschossen"] = True
                fertig = st["geschossen"] and self.stoss_rest <= 0.0
                will = pygame.Vector2(0, 0)
            else:
                punkt = self.druckpunkt(ort, gefahr[1])
                feuern = self._munition_reicht() and self._abdruecken(dt, punkt, ein)
                if feuern:
                    st["geschossen"] = True
                fertig = st["geschossen"] and self.stoss_rest <= 0.0
                zielt = False
                will = pygame.Vector2(0, 0)
            if fertig or jetzt >= st["bis"]:
                st["phase"] = "zurueck"
            return will, punkt, feuern, zielt, "laeuft"
        # zurueck
        if k.pos.distance_to(platz) > 4.0:
            return self._weg_richtung(platz, k.ebene, ein), ort, False, False, "laeuft"
        lo, hi = b["lehnen_warten"]
        st.update(phase="drin", bis=jetzt + self.rnd.uniform(lo, hi) * (1.0 + self.innen.stress))
        return pygame.Vector2(0, 0), ort, False, False, "laeuft"

    def ecke(self):
        """Panik in der Deckung: die beste Stelle in der Naehe, die er
        erreicht, ohne die Deckung zu verlassen - dort, wo am meisten um ihn
        herum steht (in einem Haus die Ecke) und er vor jedem bekannten
        Gegner gedeckt ist. Gemeldet: "nicht probieren, am Gegner
        vorbeizurennen, sondern sich an die krasseste Deckung begeben, die
        sie erreichen koennen, ohne ihre bisherige Deckung zu verlassen." """
        from .trupp import deckung_ringsum
        k = self.k
        welt = self.g.welt
        orte = self.feind_orte()
        bestes, beste = None, 1e9
        for r in K.BOTS["ecke_radien"]:
            for i in range(12):
                p = k.pos + pygame.Vector2(r, 0).rotate(i * 30.0)
                if not welt.frei(p, k.radius + 1, k.ebene, True):
                    continue
                if not welt.wege.gerade_frei(k.ebene, k.pos, p, k.radius):
                    continue
                # Auf dem ganzen Weg gedeckt: sonst verliesse er die Deckung.
                if not (self.gedeckt(p, k.ebene) and self.gedeckt((k.pos + p) / 2, k.ebene)):
                    continue
                wert = -45.0 * deckung_ringsum(welt, p, k.ebene) + 0.4 * r
                if orte:
                    wert -= 0.3 * min(o.distance_to(p) for o in orte)
                if wert < beste:
                    bestes, beste = p, wert
        return bestes

    def tun_verkriechen(self, dt, ein):
        """Panik, aber schon in Deckung: in die beste Ecke, und dort bleiben,
        bis die Panik vorbei ist. Kommt einer zu nahe, ein Stoss blind."""
        k = self.k
        if not self.innen.panik:
            self._ecke = None
            return _nichts("fertig")
        if self._ecke is None:
            ecke = self.ecke()
            # Keine bessere Ecke: zurueck an seine Deckung, nicht stehen
            # bleiben, wo er sich gerade herauslehnt.
            platz = self._deckung_platz if self._deckung_platz is not None else k.pos
            self._ecke = ecke if ecke is not None else pygame.Vector2(platz)
        will = pygame.Vector2(0, 0)
        if k.pos.distance_to(self._ecke) > 4.0:
            will = self._weg_richtung(self._ecke, k.ebene, ein)
        else:
            self._deckung_platz = pygame.Vector2(self._ecke)
        z = self.ziel
        feuern = False
        punkt = None
        if z is not None and self.ziel_ok(z) and k.pos.distance_to(z.pos) < 120.0:
            punkt = pygame.Vector2(z.pos)
            feuern = self.rnd.random() < 0.5 and k.magazin.get(k.waffe_name, 0) > 0
        return will, punkt, feuern, False, "laeuft"

    def bessere_deckung(self):
        """Panik: eine Deckung weiter weg von jedem Gegner, den er kennt,
        dicht gedeckt vor allen, erreichbar auf geradem Weg, der an keinem
        vorbeifuehrt - lieber eine Mauer (seit 0.34.48)."""
        k = self.k
        welt = self.g.welt
        orte = self.feind_orte()
        if not orte:
            return None
        mitte = sum(orte, pygame.Vector2(0, 0)) / len(orte)
        jetzt_weit = min(o.distance_to(k.pos) for o in orte)
        bestes, beste = None, 1e9
        for r in K.BOTS["wechsel_radien"]:
            for i in range(12):
                p = k.pos + pygame.Vector2(r, 0).rotate(i * 30.0)
                if not welt.frei(p, k.radius + 2, k.ebene, True):
                    continue
                weit = min(o.distance_to(p) for o in orte)
                if weit < jetzt_weit + K.BOTS["wechsel_weiter"]:
                    continue
                if any(_abstand_zur_strecke(o, k.pos, p) < 90.0 for o in orte):
                    continue                  # nicht am Gegner vorbei
                if not welt.wege.gerade_frei(k.ebene, k.pos, p, k.radius + 1):
                    continue
                if not all(self.dicht_gedeckt(p, o) for o in orte):
                    continue
                wert = 0.5 * r - 0.4 * weit
                if welt.deckung(mitte, p, k.ebene) == "wand":
                    wert -= K.BOTS["deckung_wand"]
                if wert < beste:
                    bestes, beste = p, wert
        return bestes

    def tun_deckung_wechseln(self, dt, ein):
        """Panik: hinueber in eine bessere Deckung, dann ist er dort sicher
        (und verkriecht sich, wenn die Panik bleibt). Gibt es keine, ist es
        gescheitert - dann bleibt er oder rennt."""
        k = self.k
        if not self.innen.panik:
            self._wechsel = None
            return _nichts("fertig")
        if getattr(self, "_wechsel", None) is None:
            self._wechsel = self.bessere_deckung()
            if self._wechsel is None:
                return _nichts("gescheitert")
        if k.pos.distance_to(self._wechsel) < 5.0:
            self._deckung_platz = pygame.Vector2(self._wechsel)
            self._wechsel = None
            return _nichts("fertig")
        gefahr = self._gefahr()
        return (self._weg_richtung(self._wechsel, k.ebene, ein),
                (gefahr[0] if gefahr else None), False, False, "laeuft")

    def tun_fliehen(self, dt, ein):
        """Panik: weg vom Gegner, zu den eigenen Leuten, wenn welche da
        sind, die weiter weg vom Gegner stehen. Wer ihm zu nahe kommt,
        bekommt einen Stoss blind hinterher. Auftraege, Feuerschutz, der
        Kreis - alles egal, bis die Panik vorbei ist."""
        k = self.k
        if not self.innen.panik:
            self._flucht = None
            return _nichts("fertig")
        jetzt = self.g.welt.zeit
        orte = self.feind_orte()
        if self._flucht is None or jetzt > self._flucht[1]:
            if orte:
                mitte = sum(orte, pygame.Vector2(0, 0)) / len(orte)
                weg = k.pos - mitte
                if weg.length_squared() < 1.0:
                    weg = pygame.Vector2(1, 0)
                ziel = k.pos + weg.normalize() * 220.0
                for x in self.kameraden():
                    if x.ebene == k.ebene and x.pos.distance_to(mitte) > k.pos.distance_to(mitte):
                        ziel = (ziel + x.pos) / 2
                        break
            else:
                ziel = k.pos + pygame.Vector2(200, 0).rotate(self.rnd.uniform(0, 360))
            self._flucht = (ziel, jetzt + 1.0)
        will = self._weg_richtung(self._flucht[0], k.ebene, ein)
        z = self.ziel
        feuern = False
        punkt = None
        if z is not None and self.ziel_ok(z) and k.pos.distance_to(z.pos) < 140.0:
            punkt = pygame.Vector2(z.pos)
            feuern = self.rnd.random() < 0.5 and k.magazin.get(k.waffe_name, 0) > 0
        return will, punkt, feuern, False, "laeuft"

    def tun_nachsetzen(self, dt, ein):
        """Uebermut: dorthin, wo er den Gegner zuletzt sah - geradewegs,
        ohne Deckung, ohne auf die anderen zu warten."""
        k = self.k
        z = self.ziel
        if z is not None and self.ziel_ok(z):
            return _nichts("fertig")
        gefahr = self.letzter_feind()
        if gefahr is None:
            return _nichts("gescheitert")
        ort, ebene, _w = gefahr
        if k.pos.distance_to(ort) < 24.0:
            return _nichts("fertig")
        return self._weg_richtung(ort, ebene, ein), pygame.Vector2(ort), False, False, "laeuft"

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
            return self._kaempfen(dt, ein, mit_deckung=False) + ("laeuft",)
        return self._weg_richtung(zone[0], zone[1], ein), None, False, False, "laeuft"

    def tun_helfen(self, dt, ein):
        x = self._opfer()
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
            if self.linie == "":
                return _nichts("fertig")
            # Er sieht ihn, aber eine Kiste steht dazwischen. "Fertig" hiesse
            # hier: angreifen geht nicht (keine freie Linie), also wieder
            # suchen, wieder fertig - und er stand dabei still im Feuer
            # (gesehen in der Aufnahme, 0.34.31). Die Kampfbewegung geht
            # zur Seite, bis die Bahn frei ist.
            return self._kaempfen(dt, ein, mit_deckung=False) + ("laeuft",)
        # Gehoert, aber nicht gesehen: dorthin, wo es war.
        ort = self.unerklaert()
        if ort is not None and self.verdacht is None:
            self.verdacht = (pygame.Vector2(ort), self.k.ebene, self.g.welt.zeit + 3.0)
        will, punkt = self._unterwegs(dt, ein)
        return will, punkt, False, False, "laeuft"


    # ── Bergen (seit 0.34.40) ─────────────────────────────────────
    def tun_zum_kameraden(self, dt, ein):
        """Hin zu dem, der liegt."""
        k = self.k
        x = self._opfer()
        if x is None:
            return _nichts("fertig")
        if x.ebene == k.ebene and k.pos.distance_to(x.pos) <= K.REVIVE["reichweite"] - 6:
            return _nichts("fertig")
        will = self._weg_richtung(x.pos, x.ebene, ein)
        gefahr = self._gefahr()
        return will, (gefahr[0] if gefahr else None), False, False, "laeuft"

    def tun_ziehen(self, dt, ein):
        """Den Liegenden an eine gedeckte Stelle ziehen. Er haengt an einer
        kurzen Leine hinter ihm (Gefecht._ziehen), also geht er ein Stueck
        ueber die Stelle hinaus. Beide Haende am Kameraden: kein Schuss."""
        k = self.k
        x = self._opfer()
        if x is None:
            self._berge_ort = None
            return _nichts("fertig")
        if self.fest_gedeckt(x.pos, x.ebene):
            self._berge_ort = None
            return _nichts("fertig")
        ort = getattr(self, "_berge_ort", None)
        if ort is None or not self.fest_gedeckt(ort, x.ebene):
            ort = self._berge_ort = self.bergeplatz(x)
        if ort is None:
            return _nichts("gescheitert")
        if k.pos.distance_to(x.pos) > K.REVIVE["reichweite"] - 2 and k.zieht is None:
            return self._weg_richtung(x.pos, x.ebene, ein), None, False, False, "laeuft"
        ein["ziehen"] = True
        weg = ort - x.pos
        if weg.length() < 8.0:
            self._berge_ort = None
            return _nichts("fertig")
        hin = ort + weg.normalize() * K.ZIEHEN["leine"]
        will = self._weg_richtung(hin, x.ebene, ein)
        gefahr = self._gefahr()
        return will, (gefahr[0] if gefahr else None), False, False, "laeuft"

    # ── Aktionen im Trupp (seit 0.34.39) ─────────────────────────
    def _hin_und_kaempfen(self, dt, ein, p, ebene=None):
        """Zu einem Ort - und wenn er dabei einen Gegner frei vor sich hat,
        schiesst er im Gehen."""
        k = self.k
        will = self._weg_richtung(p, k.ebene if ebene is None else ebene, ein)
        z = self.ziel
        if z is not None and self.ziel_ok(z) and self.linie == "":
            _w, punkt, feuern, zielt = self._kaempfen(dt, ein, mit_deckung=False)
            return will, punkt, feuern, zielt
        gefahr = self._gefahr()
        return will, (gefahr[0] if gefahr else None), False, False

    def tun_zur_stelle(self, dt, ein):
        """An seine Stellung im Trupp (seine Bahn, seinen Platz in der Linie)."""
        p = self._stellung()
        if p is None or self.k.pos.distance_to(p) <= K.TRUPP["stellung_weite"] * 0.6:
            return _nichts("fertig")
        return self._hin_und_kaempfen(dt, ein, p) + ("laeuft",)

    def tun_welle(self, dt, ein):
        """Rueckzug oder Druck in Wellen: wer dran ist, zieht an seine neue
        Stellung (und schiesst dabei, wenn er kann); wer nicht dran ist,
        deckt - kaempft von da, wo er steht, oder haelt nieder."""
        t = self.trupp
        if t is None or t.zustand not in ("rueckzug", "druck"):
            return _nichts("fertig")
        k = self.k
        p = t.stellung(k)
        if (k.nummer in t.welle or k.nummer in t.flanker) and p is not None \
                and k.pos.distance_to(p) > K.TRUPP["stellung_weite"] * 0.6:
            return self._hin_und_kaempfen(dt, ein, p) + ("laeuft",)
        z = self.ziel
        if z is not None and self.ziel_ok(z) and self.linie == "":
            _w, punkt, feuern, zielt = self._kaempfen(dt, ein, mit_deckung=False)
            return pygame.Vector2(0, 0), punkt, feuern, zielt, "laeuft"
        gefahr = self._gefahr()
        if gefahr is not None and self._munition_reicht():
            punkt = self.druckpunkt(gefahr[0], gefahr[1])
            return pygame.Vector2(0, 0), punkt, self._abdruecken(dt, punkt, ein), False, "laeuft"
        return _nichts("laeuft")

    def tun_sektor(self, dt, ein):
        """Igel und Engstelle: an seine Stellung im Ring (oder im Bogen),
        dann dort bleiben und in seinen Sektor schauen. Wer dort auftaucht,
        ist fuer angreifen - das Ziel kommt von selbst, sobald er ihn sieht."""
        t = self.trupp
        if t is None or t.zustand not in ("igel", "engstelle"):
            return _nichts("fertig")
        k = self.k
        p = t.stellung(k)
        if p is not None and k.pos.distance_to(p) > K.TRUPP["stellung_weite"] * 0.6:
            return self._hin_und_kaempfen(dt, ein, p) + ("laeuft",)
        blick = t.blick_fuer(k)
        ort = self.unerklaert()
        if ort is not None and blick is not None and (ort - k.pos).dot(blick - k.pos) > 0:
            blick = ort                       # etwas in seinem Sektor: dorthin
        return pygame.Vector2(0, 0), (pygame.Vector2(blick) if blick else None), False, False, "laeuft"

    def tun_verlegen(self, dt, ein):
        """Zu einem anderen Trupp, der um Hilfe gerufen hat: der Anfuehrer
        geht vor, die anderen in ihrer Linie hinterher (_unterwegs)."""
        t = self.trupp
        if t is None or t.hilfe is None:
            return _nichts("fertig")
        z = self.ziel
        if z is not None and self.ziel_ok(z):
            return _nichts("fertig")              # unterwegs Kontakt: erst der
        will, punkt = self._unterwegs(dt, ein)
        return will, punkt, False, False, "laeuft"

    def funkplatz(self):
        """Wo er in Ruhe funken kann: wenigstens `funk_abstand` von jedem
        Gegner weg, den er kennt - lieber dort, wo er auch gedeckt ist -, auf
        geradem Weg, der nicht an ihnen vorbeifuehrt. None: wo er steht, geht
        es schon, oder es gibt keinen solchen Platz."""
        k = self.k
        welt = self.g.welt
        t = K.TRUPP
        orte = self.feind_orte()

        def weit_genug(p):
            return all(o.distance_to(p) >= t["funk_abstand"] for o in orte)

        if not orte or weit_genug(k.pos):
            return None
        bestes, beste = None, 1e9
        for r in t["funk_weg_radien"]:
            for i in range(12):
                p = k.pos + pygame.Vector2(r, 0).rotate(i * 30.0)
                if not welt.frei(p, k.radius + 2, k.ebene, True) or not weit_genug(p):
                    continue
                if any(_abstand_zur_strecke(o, k.pos, p) < 110.0 for o in orte):
                    continue
                if not welt.wege.gerade_frei(k.ebene, k.pos, p, k.radius + 1):
                    continue
                wert = r - 0.3 * min(o.distance_to(p) for o in orte)
                if all(self.dicht_gedeckt(p, o) for o in orte):
                    wert -= K.BOTS["deckung_wand"]    # dort auch gedeckt: besser
                if wert < beste:
                    bestes, beste = p, wert
            if bestes is not None:
                return bestes
        return None

    def _funken_tun(self, art: str):
        """Ein Spruch ins Funkgeraet (seit 0.34.48 in zwei Teilen): erst
        zieht er sich zurueck, an einen gedeckten Platz weit genug weg vom
        Gegner (`funkplatz`), dann spricht er, bis er durch ist
        (K.TRUPP["funk_dauer"]) - erst dann haben ihn die anderen. Trifft
        ihn dabei eine Kugel oder sieht er einen Gegner dicht vor sich, ist
        der Spruch nicht raus: wer einen Trupp ueberrascht, laesst ihn nicht
        funken."""
        t = self.trupp
        k = self.k
        if t is None or not getattr(k, "funkgeraet", False):
            return _nichts("gescheitert")
        T = K.TRUPP
        jetzt = self.g.welt.zeit
        laeuft = self.funk_laeuft
        gefahr = self._gefahr()
        blick = gefahr[0] if gefahr else None
        if laeuft is None or laeuft["art"] != art:
            dauer = T["funk_dauer"] * (0.5 if art == "zusage" else 1.0)
            self.funk_laeuft = laeuft = dict(art=art, dauer=dauer, phase="weg", ort=self.funkplatz(),
                                             weg_bis=jetzt + T["funk_weg_zeit"],
                                             text=t.funk_text(art, (t.hilfe or {}).get("fuer")),
                                             anfang=jetzt, bis=jetzt + dauer, leben=k.leben)
        if laeuft["phase"] == "weg":
            ort = laeuft["ort"]
            if ort is not None and k.pos.distance_to(ort) > 6.0 and jetzt < laeuft["weg_bis"]:
                return self._weg_richtung(ort, k.ebene, ein=None), blick, False, False, "laeuft"
            laeuft.update(phase="senden", anfang=jetzt, bis=jetzt + laeuft["dauer"], leben=k.leben)
        z = self.ziel
        nah = (z is not None and self.ziel_ok(z) and z in self.gesehen
               and self.gesehen[z][2] >= jetzt - 0.3 and k.pos.distance_to(z.pos) < T["funk_stoer"])
        if k.leben < laeuft["leben"] - 0.5 or nah:
            self.funk_laeuft = None
            self.gehirn.log("FUNK ABGEBROCHEN")
            return _nichts("gescheitert")
        if jetzt >= laeuft["bis"]:
            t.funk_senden(art)
            self.funk_laeuft = None
            return _nichts("fertig")
        return pygame.Vector2(0, 0), blick, False, False, "laeuft"

    def tun_funk_hilfe(self, dt, ein):
        return self._funken_tun("hilfe")

    def tun_funk_lage(self, dt, ein):
        return self._funken_tun("lage")

    def tun_funk_zusage(self, dt, ein):
        return self._funken_tun("zusage")

    def tun_rauch(self, dt, ein):
        """Rauch genau dorthin, wo er gebraucht wird (seit 0.34.46): auf den
        Liegenden - in den Rauch hinein sieht keiner, und die Retter sind
        darin auch verborgen -, beim Rueckzug auf den Trupp selbst. Vorher
        lag er zwischen dem Trupp und dem Gegner; gemeldet: "nicht einfach
        nur zwischen Gegner und den Kameraden, das bringt ja nichts. Man
        kann ja darueber hinwegschauen." Ist der Ort weiter als der Wurf,
        geht er erst naeher heran. Geworfen wird wie jede Wurfwaffe."""
        k = self.k
        gefahr = self._gefahr()
        if gefahr is None:
            return _nichts("gescheitert")
        soll = self.rauch_ort(gefahr[0])
        if self.wurf_phase <= 0.0:
            self.wurf_platz = self._rauch_platz()
            if self.wurf_platz < 0:
                return _nichts("gescheitert")
            weit = K.WAFFEN[k.waffen[self.wurf_platz]]["wurf_max"] * 0.9
            if k.pos.distance_to(soll) > weit:
                return self._weg_richtung(soll, k.ebene, ein), pygame.Vector2(gefahr[0]), False, False, "laeuft"
            self.wurf_phase = 0.45
            self.sagen("RAUCH!", wichtig=True)
        ziel = _Stelle(soll, k.ebene)
        ziel.genau = True                 # nicht auf 40 Prozent des Weges (bots._werfen)
        will, punkt, werfen, zielt = self._werfen(dt, ein, ziel)
        return will, punkt, werfen, zielt, ("fertig" if werfen else "laeuft")

    def rauch_ort(self, gefahr):
        """Wohin der Rauch gehoert: auf den Liegenden, ein Stueck zum Gegner
        hin (dort laufen die Retter hinein); sonst auf die Mitte des
        Trupps."""
        k = self.k
        x = self._opfer()
        if x is not None and self.gehirn.fakten.get("kamerad_liegt"):
            mitte = pygame.Vector2(x.pos)
        else:
            leute = self.trupp.lebende() if self.trupp is not None else [k]
            leute = [m for m in leute if m.ebene == k.ebene] or [k]
            mitte = sum((pygame.Vector2(m.pos) for m in leute), pygame.Vector2(0, 0)) / len(leute)
        hin = pygame.Vector2(gefahr) - mitte
        if hin.length_squared() > 1.0:
            mitte += hin.normalize() * K.BOTS["rauch_vor"]
        return mitte


class _Stelle:
    """Ein Ort, auf den sich zielen laesst wie auf ein Wesen (pos, ebene)."""

    radius = 9.0
    genau = False                     # True: Rauch genau hierhin (tun_rauch)

    def __init__(self, pos, ebene: int) -> None:
        self.pos = pygame.Vector2(pos)
        self.ebene = int(ebene)


# Was `tut:` in wesen/bots.txt heissen darf, und was es dann tut.
TUN = {name[4:]: getattr(GoapHirn, name) for name in dir(GoapHirn)
       if name.startswith("tun_")}
