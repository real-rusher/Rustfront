"""
DUSTFRONT - Gefecht im LAN
==========================

Mehrspieler im LAN, in sechs Spielarten. **Dieser Zweig wird nicht mehr
weiterentwickelt** - er war ein Test und ist als solcher fertiggestellt.
Der Hauptzweig geht ohne Mehrspieler weiter, siehe docs/KARTE.md und
docs/MEHRSPIELER.md.

    pvp     Jeder gegen jeden. Endet nach Zeit oder nach Abschuessen,
            der Gastgeber waehlt.
    pve     Alle zusammen gegen Wellen. Endet, wenn alle am Boden liegen.
            Wer faellt, liegt am Boden und kann aufgeholfen bekommen;
            nach jeder Welle steht ohnehin wieder jeder.
    pvpve   Wellen, und dabei jeder gegen jeden. Endet wie pvp.
    team    Zwei Mannschaften, Abschuesse zaehlen fuer die Mannschaft.
            Endet nach Zeit oder nach Teamabschuessen.
    versus  Zwei Mannschaften, ein Leben je Runde. Wer faellt, liegt am
            Boden und kann von der eigenen Mannschaft aufgeholfen werden -
            danach ist er fuer diese Runde raus. Wer zuerst genug Runden
            gewonnen hat, gewinnt.
    huegel  Zwei Mannschaften und ein sichtbarer Kreis in der Kartenmitte.
            Wer dort die Mehrheit hat, laedt fuer seine Mannschaft.

**Mannschaften.** Nur drei Dinge unterscheiden sie vom Rest: die Fraktion
haengt am Team statt am Spieler (deshalb trifft man den Nebenmann nicht),
der Einstieg sucht einen Platz weit weg von den Fremden und nahe bei den
eigenen, und gezaehlt wird auf ein gemeinsames Konto. Neue Mitspieler gehen
in die kleinere Mannschaft, nicht abwechselnd - wer geht, hinterlaesst
sonst eine Luecke, die nie wieder gefuellt wird.

**Der Gastgeber rechnet alles.** Er hat die einzige echte Welt. Gaeste
schicken nur, was sie druecken, und bekommen zurueck, wo alles steht. Ein
Gast simuliert nichts - seine Figuren sind Attrappen, die an die Stellen
gesetzt werden, die der Gastgeber durchgibt.

**Warum eine eigene Fraktion je Spieler.** Die Trefferabfrage in world.py
ueberspringt alles, was zur selben Fraktion gehoert. Alle Spieler tragen
von Haus aus "mensch", koennten sich also nie treffen. In pvp bekommt hier
jeder seine eigene Fraktion; in pve teilen sich alle eine, damit man die
eigenen Leute nicht abschiesst. Am Spielkern aendert das keine Zeile.

**Was nicht synchronisiert wird:** Partikel, Huelsen, Blutflecken,
Staubwolken. Die entstehen bei jedem selbst und sind reine Kosmetik. Wer
sie mitschicken wollte, haette den zehnfachen Netzverkehr fuer nichts.
"""

from __future__ import annotations

import math
import random

import pygame

from . import bestenliste
from . import config as K
from . import netz
from .core import Szene
from .entities import Aufsammler, Gegner, Rauchwolke, Spieler, wolke
from .font import SCHRIFT
from .render import Kamera, Renderer
from .world import Welt, freier_punkt, testkarte


# ══════════════════════════════════════════════════════════════════
# Wesen
# ══════════════════════════════════════════════════════════════════

class Kaempfer(Spieler):
    """Ein Spieler im Gefecht.

    Kann drei Dinge mehr als der gewoehnliche Spieler: er gehoert einer
    Seite an, er kann am Boden liegen statt zu sterben, und er hat einen
    Munitionsvorrat ausserhalb des Magazins.
    """

    def __init__(self, pos, ebene: int, nummer: int, name: str,
                 fraktion: str, knapp: bool = False, team: int = -1) -> None:
        super().__init__(pos, ebene)
        self.fraktion = fraktion
        self.nummer = nummer
        self.name = name
        self.team = team             # -1 = keine Mannschaft, sonst 0 oder 1
        self.raus = False            # in versus: diese Runde erledigt
        self.abschuesse = 0
        self.tode = 0
        self.wieder_in = 0.0
        self.toeter = None           # wertet das Gefecht aus und raeumt weg
        self.abgerechnet = False     # ist dieser Tod schon verbucht?
        self.treppe_rest = 0.0       # Sperre nach einem Ebenenwechsel
        # Am Boden. Die beiden Zeiten stehen am Kaempfer und nicht fest im
        # Code, weil versus andere braucht als pve: dort soll eine Runde
        # laufen, hier soll eine Welle zu schaffen sein.
        self.revive_an = False
        self.boden_zeit = K.REVIVE["boden_zeit"]
        self.revive_dauer = K.REVIVE["dauer"]
        self.am_boden = False
        self.boden_rest = 0.0
        self.revive_stand = 0.0      # 0 bis 1, wie weit das Aufhelfen ist
        # Wem gerade geholfen wird - None, wenn niemandem. Bewusst nicht 0:
        # der Gastgeber ist Spieler 0, und eine 0 ist in Python falsch.
        # Genau daran haette niemand je dem Gastgeber aufhelfen koennen.
        self.hilft = None
        # Munitionsvorrat
        self.knapp = knapp
        self.vorrat = {w: K.MUNITION["vorrat"].get(w, 0) for w in self.waffen}

    @property
    def bild(self) -> str:
        """Am Boden eine eigene Figur, sonst die mit der Waffe.

        Ohne das unterschied sich ein Liegender nur durch die Farbe seines
        Namens von einem Stehenden - im Gefecht viel zu wenig. Ein Gegner
        muss auf einen Blick erkennen, wer unten ist: das ist der Mann,
        den er liegen lassen kann, und die Stelle, an der gleich jemand
        zum Helfen stehen bleibt.
        """
        if self.am_boden:
            return "spieler_boden"
        return super().bild

    # ---- Am Boden statt tot -------------------------------------------
    def sterben(self, von=None) -> None:
        if self.revive_an and not self.am_boden:
            # Nicht tot, nur unten. lebt bleibt True, damit die Figur
            # weiter gezeichnet wird und ansprechbar bleibt.
            self.am_boden = True
            self.leben = K.REVIVE["boden_leben"]
            self.boden_rest = self.boden_zeit
            self.revive_stand = 0.0
            self.feuert = False
            self.toeter = von
            return
        super().sterben(von)
        self.toeter = von

    def aufhelfen(self) -> None:
        """Wieder auf die Beine, mit angeschlagenem Leben."""
        self.am_boden = False
        self.boden_rest = 0.0
        self.revive_stand = 0.0
        self.leben = K.REVIVE["danach_leben"]
        self.unverwundbar = K.REVIVE["schutz"]

    # ---- Munition ------------------------------------------------------
    def nachladen(self) -> None:
        """Wie sonst, aber bei knapper Munition nur mit Vorrat."""
        if self.knapp and self.vorrat.get(self.waffe_name, 0) <= 0:
            return
        super().nachladen()

    def schritt(self, dt: float) -> None:
        self.treppe_rest = max(0.0, self.treppe_rest - dt)
        vorher = self.magazin.get(self.waffe_name, 0)
        war_am_laden = self.nachlade_rest > 0
        super().schritt(dt)
        if not (self.knapp and war_am_laden and self.nachlade_rest <= 0):
            return
        # Der Spielkern hat das Magazin eben randvoll gemacht. Bei knapper
        # Munition wird das nachtraeglich bezahlt: nur so viel, wie der
        # Vorrat hergibt. Das nachher zu verrechnen ist einfacher, als in
        # entities.py einzugreifen - und dieser Zweig soll den Kern nicht
        # anfassen.
        name = self.waffe_name
        gebraucht = K.WAFFEN[name]["magazin"] - vorher
        hat = self.vorrat.get(name, 0)
        gibt = max(0, min(gebraucht, hat))
        self.magazin[name] = vorher + gibt
        self.vorrat[name] = hat - gibt

    def auffuellen(self, anteil: float) -> bool:
        """Munitionskiste aufgesammelt. False, wenn schon alles voll ist."""
        genommen = False
        for name in self.waffen:
            voll = K.MUNITION["vorrat"].get(name, 0)
            if voll <= 0:
                continue
            hat = self.vorrat.get(name, 0)
            if hat >= voll:
                continue
            self.vorrat[name] = min(voll, hat + int(voll * anteil) + 1)
            genommen = True
        return genommen


class KampfBeute(Aufsammler):
    """Etwas zum Aufheben, das jeder Kaempfer nehmen kann.

    Der gewoehnliche Aufsammler schaut nur auf welt.held - im Einzelspieler
    gibt es ja nur einen. Im Gefecht waere das der Gastgeber, und kein Gast
    koennte je etwas aufheben.
    """

    def __init__(self, pos, art: str, ebene: int, kaempfer: dict) -> None:
        super().__init__(pos, art, ebene)
        self.bild = "munikiste" if art == "munition" else "medkit"
        self._kaempfer = kaempfer

    def schritt(self, dt: float) -> None:
        for k in list(self._kaempfer.values()):
            if not k.lebt or k.am_boden or k.ebene != self.ebene:
                continue
            if self.pos.distance_to(k.pos) > self.radius + k.radius + 3:
                continue
            genommen = False
            if self.art == "medkit" and k.medkits < K.MEDKIT["hoechstens"]:
                k.medkits += 1
                genommen = True
            elif self.art == "munition":
                genommen = k.auffuellen(K.MUNITION["kiste_gibt"])
            if genommen:
                self.lebt = False
                self.welt.beute_genommen(self.pos, self.ebene, self.art,
                                         k.nummer)
                return


class KampfGegner(Gegner):
    """Ein Gegner, der mit mehreren Spielern zurechtkommt.

    Der Gegner aus dem Einzelspieler laeuft immer auf `welt.held` zu - den
    einen Spieler, den es dort gibt. Zu viert waere das ein Rudel, das
    geschlossen auf denselben Mann zulaeuft, waehrend die anderen drei in
    Ruhe zielen. Das ist weder gefaehrlich noch interessant.

    Hier waehlt jeder Gegner selbst, und zwar nach drei Regeln:

    1. **Naehe zaehlt.** Der naechste ist der wahrscheinlichste.
    2. **Gedraenge schreckt ab.** Jeder Gegner, der schon an einem Ziel
       haengt, macht es unattraktiver. So verteilt sich das Rudel von
       selbst, ohne dass jemand die Verteilung ausrechnet.
    3. **Wer entschieden hat, bleibt dabei.** Ein Ziel wird ein paar
       Sekunden gehalten. Ohne das wechselt ein Gegner bei jedem Schritt
       und zappelt auf der Stelle, sobald zwei Spieler gleich weit weg
       sind.

    Wer am Boden liegt, zieht kaum noch Gegner an - sonst stehen alle um
    einen Gefallenen herum, statt die Helfer anzugreifen.
    """

    def __init__(self, pos, art: str, ebene: int, gefecht) -> None:
        super().__init__(pos, art, ebene)
        self._gefecht = gefecht
        self._ziel = None
        self._ziel_rest = 0.0

    def _ziel_waehlen(self, dt: float):
        self._ziel_rest -= dt
        if (self._ziel is not None and self._ziel.lebt
                and not self._ziel.am_boden and self._ziel_rest > 0):
            return self._ziel
        g = K.GEGNER_MP
        last = self._gefecht.gegnerlast
        bestes, bester_wert = None, 1e18
        for k in self._gefecht.kaempfer.values():
            if not k.lebt:
                continue
            wert = self.pos.distance_to(k.pos)
            if k.ebene != self.ebene:
                wert += g["ebenen_strafe"]
            if k.am_boden:
                wert += g["boden_strafe"]
            wert *= 1.0 + last.get(k.nummer, 0) * g["gedraenge"]
            if wert < bester_wert:
                bestes, bester_wert = k, wert
        self._ziel = bestes
        self._ziel_rest = g["ziel_haltezeit"]
        if bestes is not None:
            # Die eigene Wahl sofort mitzaehlen, damit der naechste Gegner
            # sie schon sieht. Ohne das waehlen alle im selben Schritt
            # dasselbe Ziel: beim ersten Mal ist die Last ueberall null,
            # und eine frische Welle liefe geschlossen auf einen Mann zu.
            last[bestes.nummer] = last.get(bestes.nummer, 0) + 1
        return bestes

    def schritt(self, dt: float) -> None:
        # Gegner.schritt() liest welt.held. Statt entities.py anzufassen,
        # wird der Held fuer die Dauer des Schritts auf das eigene Ziel
        # gesetzt und danach zurueckgegeben. Der Spielkern bleibt dadurch
        # unveraendert, und dieser ganze Zweig laesst sich spaeter in einem
        # Stueck entfernen.
        vorher = self.welt.held
        self.welt.held = self._ziel_waehlen(dt)
        try:
            super().schritt(dt)
        finally:
            self.welt.held = vorher


# ══════════════════════════════════════════════════════════════════
# Die Szene
# ══════════════════════════════════════════════════════════════════

class Gefecht(Szene):
    """Die Spielszene fuer den LAN-Test, beim Gastgeber wie beim Gast."""

    def __init__(self, app, name: str, gastgeber=None, gast=None,
                 modus: str = K.MODUS_VORGABE, ende_art: str = "zeit",
                 ende_wert: float = 0.0, knapp: bool = False,
                 schutz: bool | None = None, medkits: int | None = None,
                 medkit_spawn: bool | None = None, runden: int | None = None,
                 team: int | None = None, passwort: str = "",
                 seed: int | None = None) -> None:
        super().__init__(app)
        self.name = netz.name_saeubern(name)
        self.gastgeber = gastgeber
        self.gast = gast
        self.modus = modus if modus in K.MODI else K.MODUS_VORGABE
        self.regeln = K.MODI[self.modus]
        self.ende_art = ende_art if ende_art in K.ENDE_ARTEN else "zeit"
        self.knapp = bool(knapp)
        # Drei Schalter, die der Gastgeber beim Aufmachen stellt. Der Gast
        # bekommt sie mit dem Willkommen und stellt nichts selbst.
        self.schutz_an = (K.GEFECHT["schutz_an"] if schutz is None
                          else bool(schutz))
        self.start_medkits = max(0, min(
            K.GEFECHT["start_medkits_hoechstens"],
            K.GEFECHT["start_medkits"] if medkits is None else int(medkits)))
        self.medkits_spawnen = (K.GEFECHT["medkits_spawnen"]
                                if medkit_spawn is None else bool(medkit_spawn))
        g = K.VERSUS["runden_grenzen"]
        self.runden_bis = max(g[0], min(g[1], int(
            K.VERSUS["runden_bis"] if runden is None else runden)))
        # In welche Mannschaft man will: -1 heisst "such mir eine aus".
        self.team_wunsch = int(-1 if team is None else team)
        # Kennwort. Im eigenen Netz meist leer; ueber das Internet ist es
        # das Einzige, was zwischen der Runde und jedem steht, der die
        # Adresse kennt.
        self.passwort = netz.passwort_saeubern(passwort)
        self.abgewiesen = ""         # Grund, falls der Gastgeber absagt
        # Ohne Vorgabe des Gastgebers: Zeit wie immer, Abschuesse aber je
        # nachdem, ob ein Konto oder sechs gefuellt werden muessen.
        if self.ende_art == "zeit":
            vorgabe = K.GEFECHT["rundenzeit"]
        elif self.regeln["teams"]:
            vorgabe = K.GEFECHT["team_abschuesse"]
        else:
            vorgabe = K.GEFECHT["abschuesse_ziel"]
        self.ende_wert = float(ende_wert) or float(vorgabe)

        # Im Spiel ohne Seed, damit jede Runde anders ausfaellt. Die Tests
        # geben einen festen mit - ohne ihn haengt jede Pruefung daran, wo
        # der Gastgeber zufaellig eingestiegen ist, und eine Pruefung, die
        # mal gruen und mal rot ist, sagt nichts.
        self.rnd = random.Random(seed)
        self.renderer = Renderer(app.bilder)
        self.welt = testkarte()
        self.kamera = Kamera()
        self.kaempfer: dict[int, Kaempfer] = {}
        self.gegnerlast: dict[int, int] = {}
        self.teampunkte = [0] * len(K.TEAMS["namen"])
        self.zone_stand = [0.0] * len(K.TEAMS["namen"])
        self.zone_mitte = pygame.Vector2(0, 0)
        self.zone_halter = -1        # wer den Kreis gerade haelt, -1 = niemand
        self.runde = 0               # in versus: welche Runde laeuft
        self.runden_pause = 0.0
        self.sieger_team = -1
        self.rest = self.ende_wert if self.ende_art == "zeit" else 0.0
        self.welle = 0
        self.pause_rest = K.WELLEN_MP["pause"]
        self.gegner_offen: list = []
        self.vorbei = False
        self.gewonnen = False
        self.liste: list[dict] = []
        self.hinweis = ""
        self.blick = 0
        self.blick_hoehe = 0.0
        self.blick_rest = 0.0     # so lange bleibt die Ansicht verschoben
        self.ich = None
        self.meine_nummer = 0

        self._seit_senden = 0.0
        self._fremde_schuesse: list[tuple] = []
        self._fremde_beute: list[tuple] = []
        self._fremde_gegner: list[tuple] = []
        self._knoepfe: set[str] = set()
        self._waffe_wunsch = -1
        self._rad = 0
        self._seit_medkit = 0.0
        self._seit_muni = 0.0
        self._letzte_ebene = 0
        self._flughoehen: dict[int, float] = {}
        # Pausenmenue: None = zu, sonst die gewaehlte Zeile.
        self.menue = None
        self.menue_teams = False
        self.menue_zeile = 0
        self._zeit = 0.0             # laeuft mit, treibt den Puls des Kreises

        # Der Kreis liegt in der Mitte der Karte. Eine feste Stelle, die
        # alle kennen - das ist der Punkt an dieser Spielart.
        ebene_zone = self.welt.ebene(min(K.ZONE["ebene"],
                                         len(self.welt.ebenen) - 1))
        self.zone_mitte.update(ebene_zone.pixel_breite / 2,
                               ebene_zone.pixel_hoehe / 2)

        self._welt_verdrahten()
        self.wunsch = self._wunsch_lesen()

        if self.ist_gastgeber:
            self.ich = self._dazu(0, self.name, self.team_wunsch)
        else:
            self.gast.senden({"t": "hallo", "name": self.name,
                              "team": self.team_wunsch,
                              "wort": self.passwort})

    def _welt_verdrahten(self) -> None:
        """Die Rueckmeldungen der Welt anschliessen: Ton, Ruckeln, Flecken.

        Genau das hat hier lange gefehlt. Welt.klang und die anderen sind
        von Haus aus leere Methoden; der Einzelspieler haengt sich in
        play.py daran. Das Gefecht tat es nicht - und darum war im ganzen
        Mehrspieler kein Ton zu hoeren, kein Schuss zu spueren und kein
        Blutfleck zu sehen, bei Gastgeber und Gast gleichermassen.

        Eines bleibt bewusst weg: kurz_langsam. Die Zeitlupe beim Toeten
        wuerde beim Gastgeber die ganze Welt verlangsamen, also auch fuer
        alle Gaeste. Ein Abschuss darf nicht die Runde der anderen bremsen.
        """
        self.welt.ruckeln = self.kamera.stossen
        self.welt.klang = self.app.klaenge.spielen
        self.welt.blutfleck = self._blutfleck
        self.welt.brandfleck = self._brandfleck

    def _blutfleck(self, pos, ebene: int, radius: float) -> None:
        self.welt.ebene(ebene).dekal(self.renderer.blutfleck(radius),
                                     pos.x, pos.y)

    def _brandfleck(self, pos, ebene: int, radius: float) -> None:
        self.welt.ebene(ebene).dekal(self.renderer.brandfleck(radius),
                                     pos.x, pos.y)

    # ---- Grundsaetzliches --------------------------------------------
    @property
    def ist_gastgeber(self) -> bool:
        return self.gastgeber is not None

    @property
    def mit_gegnern(self) -> bool:
        return self.regeln["gegner"]

    @property
    def mit_teams(self) -> bool:
        return self.regeln["teams"]

    @property
    def schutz_zeit(self) -> float:
        """Sekunden Unverwundbarkeit nach dem Einstieg, 0 wenn abgeschaltet.

        Gegen Spawnkilling: wer gerade erst eingestiegen ist, soll nicht
        von jemandem erledigt werden, der schon zielt. Abschaltbar, weil
        man den Schutz bei zweien auf einer kleinen Karte auch ausnutzen
        kann - man laeuft geschuetzt ins Gefecht.
        """
        return K.GEFECHT["schutz"] if self.schutz_an else 0.0

    def _team_fuer(self, wunsch: int = -1) -> int:
        """In welche Mannschaft ein Neuer kommt.

        Wer sich beim Starten eine ausgesucht hat, bekommt sie - aber nur,
        solange sie dadurch nicht groesser wird als die andere. Sonst
        stehen am Ende vier gegen einen, weil sich alle dieselbe Seite
        gewuenscht haben, und das Gefecht ist vorbei, bevor es anfaengt.

        Ohne Wunsch geht es in die kleinere Mannschaft. Ausgleichend statt
        abwechselnd: wer geht, hinterlaesst sonst eine Luecke, die nie
        wieder gefuellt wird.
        """
        if not self.mit_teams:
            return -1
        groessen = [0] * len(K.TEAMS["namen"])
        for k in self.kaempfer.values():
            if 0 <= k.team < len(groessen):
                groessen[k.team] += 1
        if 0 <= wunsch < len(groessen) and groessen[wunsch] <= min(groessen):
            return wunsch
        return groessen.index(min(groessen))

    def _fraktion_fuer(self, nummer: int, team: int = -1) -> str:
        """Wer wen treffen kann.

        In pvp und pvpve ist jeder sein eigener Feind. In pve teilen sich
        alle eine Fraktion, damit man die eigenen Leute nicht abschiesst.
        Mit Mannschaften gehoert die Fraktion dem Team - so trifft man den
        Nebenmann nicht, den Gegner aber schon.
        """
        if self.mit_teams and team >= 0:
            return "team%d" % team
        if self.regeln["beute"]:
            return "kaempfer%d" % nummer
        return "mannschaft"

    def _dazu(self, nummer: int, name: str, wunsch: int = -1) -> Kaempfer:
        team = self._team_fuer(wunsch)
        pos = self._einstiegsort(team)
        k = Kaempfer(pos, 0, nummer, netz.name_saeubern(name),
                     self._fraktion_fuer(nummer, team), knapp=self.knapp,
                     team=team)
        self._regeln_anlegen(k)
        k.unverwundbar = self.schutz_zeit
        k.medkits = self.start_medkits
        self.kaempfer[nummer] = k
        self.welt.dazu(k)
        return k

    def _regeln_anlegen(self, k: Kaempfer) -> None:
        """Was die Spielart am einzelnen Kaempfer aendert."""
        k.revive_an = self.regeln["revive"]
        if self.regeln["runden"]:
            k.boden_zeit = K.VERSUS["boden_zeit"]
            k.revive_dauer = K.VERSUS["revive_dauer"]

    def _einstiegsort(self, team: int = -1) -> pygame.Vector2:
        """Ein freier Platz. Mit Mannschaften nahe bei den eigenen Leuten
        und weit weg von den fremden - sonst faengt jede Runde mit einem
        Gefecht an der Einstiegsstelle an."""
        eigene = [k.pos for k in self.kaempfer.values()
                  if k.lebt and team >= 0 and k.team == team]
        fremde = [k.pos for k in self.kaempfer.values()
                  if k.lebt and (team < 0 or k.team != team)]
        bester, bester_wert = None, -1e18
        for _ in range(K.NETZ["hoechstens"] * 6):
            p = freier_punkt(self.welt, 0, self.rnd)
            zu_fremd = min((p.distance_to(q) for q in fremde), default=9999.0)
            if not self.mit_teams:
                if zu_fremd > K.GEFECHT["abstand"]:
                    return p
                continue
            zu_eigen = min((p.distance_to(q) for q in eigene), default=0.0)
            # Weit weg von den Gegnern zaehlt, nahe bei den eigenen hilft.
            wert = zu_fremd - zu_eigen * 0.5
            if wert > bester_wert:
                bester, bester_wert = p, wert
        return bester if bester is not None else freier_punkt(self.welt, 0, self.rnd)

    # ---- Eingabe ------------------------------------------------------
    def knoepfe_sammeln(self) -> None:
        """Einmalige Tastendruecke aufheben, bis das naechste Paket rausgeht.

        Notwendig, keine Feinheit: gedrueckt() ist genau ein Bild lang wahr,
        das Spiel rechnet 120 Mal in der Sekunde, gesendet wird nur ein paar
        Dutzend Mal. Wer direkt beim Senden abfragt, verliert die meisten
        Druecke.
        """
        e = self.app.eingabe
        for name in ("nachladen", "heilen", "tracer", "tracer_weit"):
            if e.gedrueckt(name):
                self._knoepfe.add(name)
        for nr in range(1, 8):
            if e.gedrueckt("waffe%d" % nr):
                self._waffe_wunsch = nr - 1
        if e.rad:
            self._rad += e.rad

    def _meine_eingabe(self) -> dict:
        e = self.app.eingabe
        ziel = self.kamera.zu_welt(e.maus)
        offen = self.menue is not None
        meldung = {
            "t": "ein",
            "will": [0.0, 0.0] if offen else [round(v, 2) for v in e.richtung()],
            "ziel": [round(ziel.x, 1), round(ziel.y, 1)],
            "feuert": False if offen else e.gehalten("feuer"),
            "zielt": False if offen else e.gehalten("zweit"),
            "sprint": False if offen else e.gehalten("sprint"),
            # Nutzen wird gehalten, nicht gedrueckt: Treppe und Aufhelfen
            # haengen beide daran, und Aufhelfen braucht Zeit.
            "nutzen": False if offen else e.gehalten("nutzen"),
            "waffe": self._waffe_wunsch,
            "knoepfe": sorted(self._knoepfe),
        }
        self._knoepfe.clear()
        self._waffe_wunsch = -1
        return meldung

    def _anwenden(self, k: Kaempfer, ein: dict) -> None:
        """Eine Eingabemeldung auf einen Kaempfer legen. Nur beim Gastgeber.

        Alles wird geprueft und begrenzt: die Meldung kommt von einem
        fremden Rechner und ist erst einmal nur ein Vorschlag.
        """
        if not k.lebt:
            return
        try:
            will = pygame.Vector2(float(ein["will"][0]), float(ein["will"][1]))
            if will.length_squared() > 1.0:
                will.normalize_ip()
            k.ziel = pygame.Vector2(float(ein["ziel"][0]), float(ein["ziel"][1]))
        except (KeyError, TypeError, ValueError, IndexError):
            return

        if k.am_boden:
            # Am Boden liegt man. Kein Kriechen mehr: wer getroffen wurde,
            # soll an der Stelle liegen bleiben, an der es passiert ist -
            # sonst zieht er sich aus jeder Gefahr heraus, und die
            # Entscheidung, ob jemand zu ihm vorlaeuft, kostet nichts.
            k.will.update(0, 0)
            k.tempo.update(0, 0)
            k.feuert = False
            k.zielt = False
            k.sprint = False
            k.hilft = None
            return

        waffe = ein.get("waffe", -1)
        if isinstance(waffe, int) and 0 <= waffe < len(k.waffen):
            # Vor allem anderen und durch nichts zu sperren: die Waffe
            # laesst sich immer wechseln, auch beim Helfen.
            k.waffe_waehlen(waffe)

        k.will = will
        k.feuert = bool(ein.get("feuert"))
        k.zielt = bool(ein.get("zielt"))
        k.sprint = bool(ein.get("sprint"))

        knoepfe = ein.get("knoepfe") or []
        if isinstance(knoepfe, list):
            if "nachladen" in knoepfe:
                k.nachladen()
            if "heilen" in knoepfe:
                k.heilen()
            if "tracer" in knoepfe:
                k.tracer = not k.tracer
            if "tracer_weit" in knoepfe:
                k.tracer_weit = not k.tracer_weit

        # Nutzen: erst jemandem aufhelfen, sonst die Treppe nehmen.
        k.hilft = None
        if not ein.get("nutzen"):
            return
        opfer = self._wem_helfen(k)
        if opfer is not None:
            k.hilft = opfer.nummer
            # Wer aufhilft, hat die Haende voll: er steht still und
            # schiesst nicht. Das ist der Preis des Aufhelfens - und der
            # Grund, warum ein Gefallener die Gegenseite wirklich etwas
            # kostet, statt nur eine Taste zu erfordern. Die Waffe
            # umhaengen darf er trotzdem, das ist weiter oben erledigt.
            k.will.update(0, 0)
            k.tempo *= 0.2
            k.feuert = False
            k.zielt = False
            k.sprint = False
            return
        # Treppe nehmen - aber nicht jedes Bild wieder.
        #
        # "nutzen" wird gehalten, nicht gedrueckt; das braucht das
        # Aufhelfen. Ohne Sperre versuchte darum jedes Bild einen Wechsel:
        # hoch, und weil auf der Zielkachel die Treppe zurueck nach unten
        # liegt, sofort wieder hinunter. Man stand blinkend zwischen zwei
        # Etagen. Die Sperre gilt fuer den Kaempfer, nicht fuer die
        # Kachel - sie haelt also auch, wenn er nach dem Wechsel gleich
        # auf der naechsten Treppe steht.
        if k.treppe_rest > 0:
            return
        ziel_ebene = self.welt.treppe_unter(k)
        if ziel_ebene is not None and self.welt.ebene_wechseln(k, ziel_ebene):
            k.treppe_rest = K.GEFECHT["treppe_takt"]
            wolke(self.welt, k.pos, 10, 90, 0.4, K.C_MUTED_DK, k.ebene, 1,
                  "staub")
            self.welt.klang("aufheben", 0.4)

    def _darf_helfen(self, helfer, liegender) -> bool:
        """Mit Mannschaften hilft man nur den eigenen Leuten.

        Ohne diese Zeile koennte man in versus den Gegner aufheben, den man
        gerade umgelegt hat - und die Runde nie beenden.
        """
        if helfer is None or liegender is None:
            return False
        if not self.mit_teams:
            return True
        return helfer.team == liegender.team

    def _wem_helfen(self, k: Kaempfer):
        """Der naechste Gefallene in Reichweite, oder None."""
        if not self.regeln["revive"]:
            return None
        naechster, beste = None, K.REVIVE["reichweite"]
        for anderer in self.kaempfer.values():
            if anderer is k or not anderer.am_boden or not anderer.lebt:
                continue
            if anderer.ebene != k.ebene or not self._darf_helfen(k, anderer):
                continue
            d = k.pos.distance_to(anderer.pos)
            if d <= beste:
                naechster, beste = anderer, d
        return naechster

    # ---- Schritt: Gastgeber -------------------------------------------
    def _schritt_gastgeber(self, dt: float) -> None:
        self.hinweis = ""
        self.gastgeber.annehmen()

        for nummer, nachricht in self.gastgeber.holen():
            art = nachricht.get("t")
            if art == "hallo":
                if self.passwort and (netz.passwort_saeubern(
                        str(nachricht.get("wort", ""))) != self.passwort):
                    # Falsches Kennwort: hoeflich absagen und auflegen.
                    # Der Platz wird nicht belegt, der Name nicht
                    # uebernommen, und die Runde merkt nichts davon.
                    self.gastgeber.an_einen(nummer, {"t": "abgelehnt",
                                                     "grund": "KENNWORT FALSCH"})
                    leitung = self.gastgeber.leitungen.get(nummer)
                    if leitung is not None:
                        leitung.schliessen("Kennwort falsch")
                    continue
                if nummer not in self.kaempfer:
                    try:
                        wunsch = int(nachricht.get("team", -1))
                    except (TypeError, ValueError):
                        wunsch = -1
                    k = self._dazu(nummer, nachricht.get("name", "GAST"),
                                   wunsch)
                    self.gastgeber.an_einen(nummer, self._willkommen(nummer, k))
            elif art == "ein":
                k = self.kaempfer.get(nummer)
                if k is not None:
                    self._anwenden(k, nachricht)

        for nummer in self.gastgeber.gegangen():
            k = self.kaempfer.pop(nummer, None)
            if k is not None:
                k.lebt = False

        if self.ich is not None:
            self._anwenden(self.ich, self._meine_eingabe())

        if not self.vorbei:
            self._beute_nachlegen(dt)
            self._wellen(dt)
            self._zone(dt)
            self._runden(dt)
        self._gegnerlast_zaehlen()
        self.welt.schritt(dt)
        self._revive(dt)
        self._tote_abrechnen(dt)
        self._ende_pruefen(dt)

        self._seit_senden += dt
        if self._seit_senden >= K.NETZ["takt"]:
            self._seit_senden = 0.0
            self.gastgeber.an_alle(self._weltmeldung())

    def _willkommen(self, nummer: int, k: Kaempfer | None) -> dict:
        """Alle Regeln der Runde in einer Nachricht.

        Dieselbe Nachricht geht zweimal hinaus: beim Verbinden an einen
        Gast, und als "neustart" an alle, wenn der Gastgeber im Menue
        etwas geaendert hat. Sie darf darum keinen Gast voraussetzen -
        mit nummer = -1 gilt sie fuer alle.
        """
        return {"t": "willkommen", "id": nummer,
                "name": k.name if k is not None else "",
                "modus": self.modus, "ende_art": self.ende_art,
                "ende_wert": self.ende_wert, "knapp": self.knapp,
                "schutz": self.schutz_an, "medkits": self.start_medkits,
                "medkit_spawn": self.medkits_spawnen,
                "runden_bis": self.runden_bis}

    def _gegnerlast_zaehlen(self) -> None:
        """Wie viele Gegner gerade an welchem Spieler haengen.

        Einmal je Schritt gezaehlt statt von jedem Gegner einzeln - sonst
        rechnet jeder Gegner dieselbe Summe nochmal aus.
        """
        self.gegnerlast = {}
        for w in self.welt.wesen:
            if isinstance(w, KampfGegner) and w.lebt and w._ziel is not None:
                nr = w._ziel.nummer
                self.gegnerlast[nr] = self.gegnerlast.get(nr, 0) + 1

    # ---- Wellen -------------------------------------------------------
    def _wellen(self, dt: float) -> None:
        if not self.mit_gegnern:
            return
        self.gegner_offen = [g for g in self.gegner_offen if g.lebt]
        if self.gegner_offen:
            return
        self.pause_rest -= dt
        if self.pause_rest > 0:
            if self.welle > 0:
                self.hinweis = "NAECHSTE WELLE IN %d" % max(1, int(self.pause_rest) + 1)
            return
        self._welle_starten()

    def _welle_starten(self) -> None:
        w = K.WELLEN_MP
        self.welle += 1
        self.pause_rest = w["pause"]
        # Nach jeder Welle steht wieder jeder auf. Das ist der Ausgleich
        # dafuer, dass eine Runde sonst mit dem ersten Fehler kippt.
        for k in self.kaempfer.values():
            if k.am_boden:
                k.aufhelfen()
        lebende = max(1, sum(1 for k in self.kaempfer.values() if k.lebt))
        anzahl = int(w["grund"]
                     * (1.0 + w["je_welle"] * (self.welle - 1))
                     * (1.0 + w["je_spieler"] * (lebende - 1)))
        anzahl = max(1, min(w["hoechstens"], anzahl))
        brecher = 0
        if self.welle >= w["brecher_ab"]:
            brecher = int(anzahl * w["brecher_anteil"])
        for i in range(anzahl):
            art = "brecher" if i < brecher else "laeufer"
            ebene = self.rnd.randrange(len(self.welt.ebenen))
            pos = freier_punkt(self.welt, ebene, self.rnd)
            g = KampfGegner(pos, art, ebene, self)
            self.gegner_offen.append(g)
            self.welt.dazu(g)

    # ---- Der Kreis in der Mitte -----------------------------------------
    def in_der_zone(self, k) -> bool:
        """Steht dieser Kaempfer im Kreis? Nur auf der richtigen Ebene."""
        if not k.lebt or k.am_boden:
            return False
        if k.ebene != K.ZONE["ebene"]:
            return False
        return k.pos.distance_to(self.zone_mitte) <= K.ZONE["radius"]

    def _zone(self, dt: float) -> None:
        """Wer die Mehrheit im Kreis hat, laedt fuer sein Team.

        Bei Gleichstand passiert nichts - auch nicht, wenn beide viele
        Leute drin haben. Das macht den Kreis zum Ort, an dem man sich
        trifft, statt ihn abwechselnd leerzuraeumen: wer allein hineinlaeuft
        laedt schnell, wer auf Widerstand trifft muss ihn erst wegraeumen.
        """
        if not self.regeln["zone"]:
            return
        z = K.ZONE
        drin = [0] * len(self.teampunkte)
        for k in self.kaempfer.values():
            if 0 <= k.team < len(drin) and self.in_der_zone(k):
                drin[k.team] += 1

        hoechste = max(drin)
        if hoechste == 0 or drin.count(hoechste) > 1:
            # Niemand drin, oder Gleichstand: der Stand verfaellt langsam.
            self.zone_halter = -1
            for i in range(len(self.zone_stand)):
                self.zone_stand[i] = max(0.0, self.zone_stand[i]
                                         - z["verfall"] * dt)
            return

        halter = drin.index(hoechste)
        self.zone_halter = halter
        mehrheit = hoechste - max(
            [d for i, d in enumerate(drin) if i != halter] or [0])
        tempo = min(z["hoechstens"],
                    z["je_sekunde"] + z["je_kopf"] * (mehrheit - 1))
        self.zone_stand[halter] = min(z["bis"],
                                      self.zone_stand[halter] + tempo * dt)
        for i in range(len(self.zone_stand)):
            if i != halter:
                self.zone_stand[i] = max(0.0, self.zone_stand[i]
                                         - z["verfall"] * dt)
        if self.zone_stand[halter] >= z["bis"]:
            self.sieger_team = halter
            self._runde_beenden(gewonnen=True)

    # ---- Runden (versus) -------------------------------------------------
    def _runden(self, dt: float) -> None:
        """Ein Leben je Runde. Wer zuerst genug Runden hat, gewinnt.

        Eine Runde ist zu Ende, wenn eine Mannschaft niemanden mehr auf den
        Beinen hat. Am Boden zaehlt noch als lebendig - solange jemand
        aufhelfen kann, ist die Runde nicht entschieden.
        """
        if not self.regeln["runden"]:
            return
        if not self._beide_besetzt():
            # Solange eine Mannschaft leer ist, waere jede Runde in dem
            # Augenblick entschieden, in dem sie anfaengt. Also wartet sie.
            self.runden_pause = K.VERSUS["pause"]
            return
        if self.runden_pause > 0:
            self.runden_pause -= dt
            if self.runden_pause <= 0:
                self._runde_aufbauen()
            return
        if self.runde == 0:
            self._runde_aufbauen()
            return

        steht = [0] * len(self.teampunkte)
        for k in self.kaempfer.values():
            if 0 <= k.team < len(steht) and k.lebt and not k.raus:
                steht[k.team] += 1
        leer = [i for i, n in enumerate(steht) if n == 0]
        if not leer or len(leer) == len(steht):
            if len(leer) == len(steht) and steht:
                # Alle gleichzeitig hin: niemand bekommt den Punkt.
                self.runden_pause = K.VERSUS["pause"]
            return
        sieger = [i for i in range(len(steht)) if i not in leer]
        if len(sieger) != 1:
            return
        self.teampunkte[sieger[0]] += 1
        self.runden_pause = K.VERSUS["pause"]
        if self.teampunkte[sieger[0]] >= self.runden_bis:
            self.sieger_team = sieger[0]
            self._runde_beenden(gewonnen=True)

    def _beide_besetzt(self) -> bool:
        """Hat jede Mannschaft mindestens einen Mitspieler?"""
        besetzt = [0] * len(self.teampunkte)
        for k in self.kaempfer.values():
            if 0 <= k.team < len(besetzt):
                besetzt[k.team] += 1
        return all(besetzt)

    def _runde_aufbauen(self) -> None:
        """Alle wieder auf die Beine, neue Plaetze, volle Magazine."""
        self.runde += 1
        self.runden_pause = 0.0
        for k in list(self.kaempfer.values()):
            k.raus = False
            self._wieder_einsteigen(k)

    # ---- Beute ---------------------------------------------------------
    def _beute_nachlegen(self, dt: float) -> None:
        # Medkits auf der Karte sind abschaltbar - dieselbe Idee wie bei
        # den Munitionskisten: ohne sie zaehlt, was man beim Einstieg
        # dabei hat, und ein Treffer wiegt schwerer.
        if self.medkits_spawnen:
            self._seit_medkit += dt
            if self._seit_medkit >= K.GEFECHT["medkit_takt"]:
                self._seit_medkit = 0.0
                self._beute_legen("medkit", K.GEFECHT["medkit_hoechstens"])
        if not self.knapp:
            return
        self._seit_muni += dt
        if self._seit_muni >= K.MUNITION["kiste_takt"]:
            self._seit_muni = 0.0
            self._beute_legen("munition", K.MUNITION["kiste_hoechstens"])

    def _beute_legen(self, art: str, hoechstens: int) -> None:
        liegen = sum(1 for w in self.welt.wesen
                     if isinstance(w, KampfBeute) and w.lebt and w.art == art)
        if liegen >= hoechstens:
            return
        ebene = self.rnd.randrange(len(self.welt.ebenen))
        self.welt.dazu(KampfBeute(freier_punkt(self.welt, ebene, self.rnd),
                                  art, ebene, self.kaempfer))

    # ---- Am Boden und wieder auf ---------------------------------------
    def _revive(self, dt: float) -> None:
        if not self.regeln["revive"]:
            return
        # Wer hilft wem? Erst sammeln, dann anwenden - sonst haengt das
        # Ergebnis an der Reihenfolge im Woerterbuch.
        hilfe: dict[int, int] = {}
        for k in self.kaempfer.values():
            if k.lebt and not k.am_boden and k.hilft is not None:
                hilfe[k.hilft] = hilfe.get(k.hilft, 0) + 1
        for k in self.kaempfer.values():
            if not (k.lebt and k.am_boden):
                continue
            helfer = hilfe.get(k.nummer, 0)
            if helfer:
                # Zwei Helfer sind doppelt so schnell. Das belohnt, wenn
                # sich die Mannschaft sammelt.
                k.revive_stand += dt * helfer / k.revive_dauer
                if k.revive_stand >= 1.0:
                    k.aufhelfen()
                    wolke(self.welt, k.pos, 10, 70, 0.5, K.C_TEAL, k.ebene, 1)
                    self.welt.klang("medkit", 0.7)
            else:
                k.revive_stand = max(0.0, k.revive_stand - dt / k.revive_dauer)
                k.boden_rest -= dt
                if k.boden_rest <= 0:
                    k.am_boden = False
                    Spieler.sterben(k, k.toeter)

    def _tote_abrechnen(self, dt: float) -> None:
        for k in list(self.kaempfer.values()):
            if k.lebt:
                continue
            if not k.abgerechnet:
                # Jeder Tod wird genau einmal abgerechnet, auch der ohne
                # Toeter. Frueher hing das alles an "wenn es einen Toeter
                # gibt" - und ein Sturz toetet ohne Toeter. Die Folge war
                # ein wieder_in, das nie gesetzt wurde, also schon im
                # naechsten Bild abgelaufen war: wer sich zu Tode fiel,
                # stand ohne Todesbild sofort irgendwo anders auf der
                # Karte. Genau das sah aus wie ein Teleport beim
                # Hinunterspringen.
                k.abgerechnet = True
                toeter = getattr(k.toeter, "von", k.toeter)
                if isinstance(toeter, Kaempfer) and toeter is not k:
                    toeter.abschuesse += K.GEFECHT["punkt_abschuss"]
                    if self.mit_teams and 0 <= toeter.team < len(self.teampunkte):
                        # In "team" zaehlt der Abschuss fuer die Mannschaft.
                        # In "versus" nicht: dort zaehlen nur Rundensiege.
                        if not self.regeln["runden"]:
                            self.teampunkte[toeter.team] += 1
                elif toeter is k or toeter is None:
                    # Selbst erledigt oder gestuerzt: beides kostet Punkte.
                    k.abschuesse += K.GEFECHT["punkt_selbst"]
                k.toeter = None
                k.tode += 1
                k.wieder_in = K.GEFECHT["wieder_nach"]
            if self.regeln["runden"]:
                k.raus = True     # in versus bleibt man bis zur naechsten Runde
                continue
            if self.regeln["revive"]:
                continue          # in pve steigt niemand von selbst wieder ein
            k.wieder_in -= dt
            if k.wieder_in <= 0 and not self.vorbei:
                self._wieder_einsteigen(k)

    def _wieder_einsteigen(self, k: Kaempfer) -> None:
        k.pos.update(self._einstiegsort(k.team))
        k.vorher.update(k.pos)
        k.tempo.update(0, 0)
        k.leben = k.max_leben
        k.ebene = 0
        k.flug = 0.0
        k.sturz_rest = 0.0
        k.lebt = True
        k.abgerechnet = False
        k.toeter = None
        k.wieder_in = 0.0
        k.am_boden = False
        k.raus = False
        k.boden_rest = 0.0
        k.revive_stand = 0.0
        k.unverwundbar = self.schutz_zeit
        k.medkits = max(k.medkits, self.start_medkits)
        k.magazin = {w: K.WAFFEN[w]["magazin"] for w in k.waffen}
        if k not in self.welt.wesen and k not in self.welt.neue:
            self.welt.dazu(k)

    # ---- Ende ----------------------------------------------------------
    def _ende_pruefen(self, dt: float) -> None:
        if self.vorbei or not self.kaempfer:
            return
        # Zone und Runden beenden sich selbst, sobald ein Team am Ziel ist.
        if self.regeln["zone"] or self.regeln["runden"]:
            if self.ende_art == "zeit" and self.ende_wert > 0:
                self.rest = max(0.0, self.rest - dt)
                if self.rest <= 0:
                    self.sieger_team = self._bestes_team()
                    self._runde_beenden(gewonnen=True)
            return
        if self.regeln["revive"]:
            # pve: vorbei, wenn niemand mehr steht
            steht_noch = any(k.lebt and not k.am_boden
                             for k in self.kaempfer.values())
            if not steht_noch:
                self._runde_beenden(gewonnen=False)
            return
        if self.ende_art == "zeit":
            self.rest = max(0.0, self.rest - dt)
            if self.rest <= 0:
                self.sieger_team = self._bestes_team()
                self._runde_beenden(gewonnen=True)
            return
        # Nach Abschuessen: mit Mannschaften zaehlt die Mannschaft
        if self.mit_teams:
            ziel = self.ende_wert or K.GEFECHT["team_abschuesse"]
            for i, punkte in enumerate(self.teampunkte):
                if punkte >= ziel:
                    self.sieger_team = i
                    self._runde_beenden(gewonnen=True)
                    return
            return
        if any(k.abschuesse >= self.ende_wert for k in self.kaempfer.values()):
            self._runde_beenden(gewonnen=True)

    def _bestes_team(self) -> int:
        """Wer vorne liegt, wenn die Zeit ablaeuft. -1 bei Gleichstand."""
        if not self.mit_teams:
            return -1
        stand = (self.zone_stand if self.regeln["zone"] else self.teampunkte)
        hoechster = max(stand)
        return stand.index(hoechster) if stand.count(hoechster) == 1 else -1

    def _runde_beenden(self, gewonnen: bool) -> None:
        self.vorbei = True
        self.gewonnen = gewonnen
        self.liste = self._endstand()
        bestenliste.eintragen(self.liste)
        if self.ist_gastgeber:
            self.gastgeber.an_alle({"t": "ende", "liste": self.liste,
                                    "gewonnen": gewonnen, "welle": self.welle,
                                    "sieger": self.sieger_team,
                                    "teampunkte": list(self.teampunkte)})

    def _endstand(self) -> list[dict]:
        return bestenliste.sortiert(
            [{"name": k.name, "abschuesse": k.abschuesse, "tode": k.tode}
             for k in self.kaempfer.values()])

    # ---- Weltmeldung ----------------------------------------------------
    def _weltmeldung(self) -> dict:
        spieler = []
        for k in self.kaempfer.values():
            spieler.append({
                "i": k.nummer, "n": k.name,
                "p": [round(k.pos.x, 1), round(k.pos.y, 1)],
                "w": round(k.winkel, 1), "e": k.ebene,
                "f": round(k.flug, 1),
                "l": round(max(0.0, k.leben), 1),
                "b": k.waffe_name, "a": k.abschuesse, "d": k.tode,
                "v": k.lebt,
                "m": k.magazin.get(k.waffe_name, 0),
                "vo": k.vorrat.get(k.waffe_name, 0),
                "nl": round(k.nachlade_rest, 2),
                "fo": round(k.fokus, 2), "zi": k.zielt,
                "tr": k.tracer, "tw": k.tracer_weit,
                "mk": k.medkits, "hr": round(k.heilt_rest, 2),
                "sz": round(k.schlag_zeigen, 2),
                "wi": round(k.wieder_in, 1),
                "ab": k.am_boden, "br": round(k.boden_rest, 1),
                "rs": round(k.revive_stand, 2),
                "tm": k.team, "ra": k.raus,
                # Wem gerade aufgeholfen wird: der Gast braucht es fuer
                # den blauen Schein am Rand, sonst weiss er nicht, warum
                # seine Figur festhaengt.
                "hf": -1 if k.hilft is None else k.hilft,
            })
        flug = []
        gegner = []
        beute = []
        for w in self.welt.wesen:
            if not w.lebt:
                continue
            if isinstance(w, KampfGegner):
                gegner.append([round(w.pos.x, 1), round(w.pos.y, 1),
                               round(w.winkel, 1), w.ebene, w.art,
                               round(max(0.0, w.leben) / w.max_leben, 2)])
                continue
            if isinstance(w, KampfBeute):
                beute.append([round(w.pos.x, 1), round(w.pos.y, 1),
                              w.ebene, w.bild])
                continue
            name = getattr(w, "bild", None)
            if name in ("geschoss", "granate", "rauchgranate"):
                # Die Flughoehe muss mit: eine Granate, die eine Ebene
                # tiefer faellt, haengt beim Gast sonst in der Luft.
                flug.append([round(w.pos.x, 1), round(w.pos.y, 1),
                             round(w.winkel, 1), w.ebene, name,
                             round(getattr(w, "flug", 0.0), 1)])
        qualm = [[round(r.pos.x, 1), round(r.pos.y, 1), r.ebene,
                  round(r.radius, 1), round(r.alter, 2)]
                 for r in self.welt.rauch if r.lebt]
        return {"t": "welt", "rest": round(self.rest, 1), "rauch": qualm,
                "spieler": spieler, "schuesse": flug, "beute": beute,
                "gegner": gegner, "welle": self.welle,
                "pause": round(self.pause_rest, 1),
                "offen": len(self.gegner_offen), "aus": self.vorbei,
                # Mannschaften, Kreis und Runden. Der Gast rechnet nichts
                # davon selbst nach - er zeigt nur an, was hier steht.
                "tp": list(self.teampunkte),
                "zs": [round(s, 1) for s in self.zone_stand],
                "zh": self.zone_halter,
                "rn": self.runde, "rp": round(self.runden_pause, 1),
                "st": self.sieger_team}

    # ---- Schritt: Gast -------------------------------------------------
    def _schritt_gast(self, dt: float) -> None:
        self.hinweis = ""
        if self.abgewiesen:
            self.hinweis = "ABGEWIESEN: %s  [ESC]" % self.abgewiesen
            return
        if not self.gast.offen:
            self.hinweis = "VERBINDUNG VERLOREN  [ESC]"
            return

        for nachricht in self.gast.holen():
            art = nachricht.get("t")
            if art in ("willkommen", "neustart"):
                self._willkommen_lesen(nachricht)
                if art == "neustart":
                    # Der Gastgeber hat die Regeln gewechselt. Alles, was
                    # von der alten Runde noch herumliegt, kommt weg.
                    self.vorbei = False
                    self.liste = []
                    self.welt.rauch = []
                    self._fremde_beute = []
                    self._fremde_gegner = []
                    self.hinweis = "NEUE RUNDE: %s" % K.MODI[self.modus]["name"]
            elif art == "welt":
                self._welt_uebernehmen(nachricht)
            elif art == "abgelehnt":
                # Gemerkt und nicht nur angezeigt: der Gastgeber legt
                # gleich darauf auf, und im naechsten Bild wuerde sonst
                # "Verbindung verloren" daraus - die Meldung, die am
                # wenigsten erklaert.
                self.abgewiesen = str(nachricht.get("grund", ""))[:24]
                self.gast.schliessen()
                return
            elif art == "ende":
                self.vorbei = True
                self.gewonnen = bool(nachricht.get("gewonnen", False))
                self.liste = [e for e in nachricht.get("liste", [])
                              if isinstance(e, dict)]
                self.sieger_team = int(nachricht.get("sieger", -1))
                self._liste_uebernehmen(self.teampunkte,
                                        nachricht.get("teampunkte"), int)
                bestenliste.eintragen(self.liste)

        # Der Gast simuliert nichts, seine Rueckmeldungen muessen aber
        # trotzdem laufen: Staubringe und Aufschriften altern hier.
        self.welt.effekte_schritt(dt)
        self._aufsetzen_erkennen()

        self._seit_senden += dt
        eilig = bool(self._knoepfe) or self._waffe_wunsch >= 0
        if eilig or self._seit_senden >= K.NETZ["eingabe_takt"]:
            self._seit_senden = 0.0
            self.gast.senden(self._meine_eingabe())

    def _willkommen_lesen(self, nachricht: dict) -> None:
        """Der Gastgeber bestimmt die Spielart, nicht der Gast.

        Dieselbe Auswertung gilt fuer das Willkommen beim Verbinden und
        fuer den Neustart mitten im Gefecht. Beim Neustart steht -1 in
        der Nummer: die eigene bleibt dann, wie sie war.
        """
        nummer = int(nachricht.get("id", 0))
        if nummer >= 0:
            self.meine_nummer = nummer
        modus = nachricht.get("modus")
        if modus in K.MODI:
            self.modus = modus
            self.regeln = K.MODI[modus]
        art = nachricht.get("ende_art")
        if art in K.ENDE_ARTEN:
            self.ende_art = art
        try:
            self.ende_wert = float(nachricht.get("ende_wert", self.ende_wert))
        except (TypeError, ValueError):
            pass
        self.knapp = bool(nachricht.get("knapp", False))
        self.schutz_an = bool(nachricht.get("schutz", self.schutz_an))
        g = K.VERSUS["runden_grenzen"]
        try:
            self.runden_bis = max(g[0], min(g[1], int(
                nachricht.get("runden_bis", self.runden_bis))))
        except (TypeError, ValueError):
            pass
        self.medkits_spawnen = bool(nachricht.get("medkit_spawn",
                                                  self.medkits_spawnen))
        try:
            self.start_medkits = max(0, min(
                K.GEFECHT["start_medkits_hoechstens"],
                int(nachricht.get("medkits", self.start_medkits))))
        except (TypeError, ValueError):
            pass

    @staticmethod
    def _liste_uebernehmen(ziel: list, werte, art) -> None:
        """Zahlenliste aus dem Netz uebernehmen, ohne ihre Laenge zu aendern.

        Was von aussen kommt, darf hier nichts kaputt machen: eine zu kurze
        oder falsch gefuellte Liste laesst den Rest einfach stehen.
        """
        if not isinstance(werte, (list, tuple)):
            return
        for i in range(min(len(ziel), len(werte))):
            try:
                ziel[i] = art(werte[i])
            except (TypeError, ValueError):
                pass

    def _welt_uebernehmen(self, meldung: dict) -> None:
        self.rest = float(meldung.get("rest", self.rest))
        self.vorbei = bool(meldung.get("aus", False))
        self.welle = int(meldung.get("welle", 0))
        self.pause_rest = float(meldung.get("pause", 0.0))
        self._liste_uebernehmen(self.teampunkte, meldung.get("tp"), int)
        self._liste_uebernehmen(self.zone_stand, meldung.get("zs"), float)
        self.zone_halter = int(meldung.get("zh", -1))
        self.runde = int(meldung.get("rn", 0))
        self.runden_pause = float(meldung.get("rp", 0.0))
        self.sieger_team = int(meldung.get("st", -1))
        gesehen = set()
        for eintrag in meldung.get("spieler", []):
            try:
                nummer = int(eintrag["i"])
                x, y = float(eintrag["p"][0]), float(eintrag["p"][1])
            except (KeyError, TypeError, ValueError, IndexError):
                continue
            gesehen.add(nummer)
            k = self.kaempfer.get(nummer)
            team = int(eintrag.get("tm", -1))
            if k is None:
                k = Kaempfer(pygame.Vector2(x, y), 0, nummer,
                             str(eintrag.get("n", "GAST")),
                             self._fraktion_fuer(nummer, team),
                             knapp=self.knapp, team=team)
                self._regeln_anlegen(k)
                self.kaempfer[nummer] = k
                if nummer == self.meine_nummer:
                    self.ich = k
            k.team = team
            k.raus = bool(eintrag.get("ra", False))
            k.vorher.update(k.pos)
            k.pos.update(x, y)
            k.winkel = float(eintrag.get("w", k.winkel))
            k.ebene = int(eintrag.get("e", 0))
            k.flug = float(eintrag.get("f", 0.0))
            k.leben = float(eintrag.get("l", 0.0))
            k.abschuesse = int(eintrag.get("a", 0))
            k.tode = int(eintrag.get("d", 0))
            k.lebt = bool(eintrag.get("v", True))
            waffe = eintrag.get("b")
            if waffe in k.waffen:
                k.waffe = k.waffen.index(waffe)
            k.magazin[k.waffe_name] = int(eintrag.get("m", 0))
            k.vorrat[k.waffe_name] = int(eintrag.get("vo", 0))
            k.nachlade_rest = float(eintrag.get("nl", 0.0))
            k.fokus = float(eintrag.get("fo", 0.0))
            k.zielt = bool(eintrag.get("zi", False))
            k.tracer = bool(eintrag.get("tr", False))
            k.tracer_weit = bool(eintrag.get("tw", False))
            k.medkits = int(eintrag.get("mk", 0))
            k.heilt_rest = float(eintrag.get("hr", 0.0))
            k.schlag_zeigen = float(eintrag.get("sz", 0.0))
            k.wieder_in = float(eintrag.get("wi", 0.0))
            k.am_boden = bool(eintrag.get("ab", False))
            k.boden_rest = float(eintrag.get("br", 0.0))
            k.revive_stand = float(eintrag.get("rs", 0.0))
            hilft = int(eintrag.get("hf", -1))
            k.hilft = None if hilft < 0 else hilft
        for nummer in list(self.kaempfer):
            if nummer not in gesehen:
                self.kaempfer.pop(nummer, None)
        # Der Renderer laeuft ueber welt.wesen: beim Gast wird die Liste
        # gesetzt statt simuliert.
        self.welt.wesen = [k for k in self.kaempfer.values() if k.lebt]
        self.welt.neue = []
        if self.ich is not None:
            self.welt.held = self.ich
        vorige_beute = self._fremde_beute
        self._fremde_schuesse = [tuple(s) for s in meldung.get("schuesse", [])
                                 if isinstance(s, (list, tuple)) and len(s) == 6]
        # Rauch wird nicht mitsimuliert, sondern jedes Mal neu gesetzt. Er
        # hat kein Gedaechtnis ausser seinem Alter, und das kommt mit.
        self.welt.rauch = []
        for eintrag in meldung.get("rauch", []):
            if not isinstance(eintrag, (list, tuple)) or len(eintrag) != 5:
                continue
            try:
                self.welt.rauch.append(Rauchwolke(
                    pygame.Vector2(float(eintrag[0]), float(eintrag[1])),
                    int(eintrag[2]), float(eintrag[3]), alter=float(eintrag[4])))
            except (TypeError, ValueError):
                continue
        self._fremde_beute = [tuple(b) for b in meldung.get("beute", [])
                              if isinstance(b, (list, tuple)) and len(b) == 4]
        self._fremde_gegner = [tuple(g) for g in meldung.get("gegner", [])
                               if isinstance(g, (list, tuple)) and len(g) == 6]
        self._aufgehoben_erkennen(vorige_beute)

    def _aufgehoben_erkennen(self, vorher: list) -> None:
        """Beim Gast: was aus der Beuteliste verschwindet, wurde aufgehoben.

        Kein eigener Kanal im Protokoll, weil keiner noetig ist: eine
        Kiste verschwindet ausschliesslich dann, wenn jemand sie nimmt.
        Der Gast vergleicht also zwei aufeinanderfolgende Listen und macht
        an der frei gewordenen Stelle dieselbe Rueckmeldung, die der
        Gastgeber bei sich macht - Funken, Aufschrift, Ton.
        """
        if not vorher:
            return
        jetzt = {(round(x), round(y), e) for (x, y, e, _b) in self._fremde_beute}
        for (x, y, ebene, bild) in vorher:
            if (round(x), round(y), ebene) in jetzt:
                continue
            art = "munition" if bild == "munikiste" else "medkit"
            Welt.beute_genommen(self.welt, pygame.Vector2(x, y), ebene, art)

    def _aufsetzen_erkennen(self) -> None:
        """Beim Gast: wessen Flughoehe auf null faellt, der ist gelandet.

        Auch das steht schon in der Weltmeldung, es muss nur gelesen
        werden. Den Kameraschlag bekommt nur, wer selbst aufgesetzt ist -
        der Sturz eines anderen soll einem nicht das Bild verreissen.
        """
        for k in self.kaempfer.values():
            vorher = self._flughoehen.get(k.nummer, 0.0)
            if vorher > 1.0 and k.flug <= 0.01 and k.lebt:
                wucht = min(1.0, vorher / 240.0)
                self.welt.aufschlagring(k.pos, k.ebene, wucht)
                wolke(self.welt, k.pos, int(K.STURZ["staub"] * 0.6),
                      140, 0.5, K.C_MUTED_DK, k.ebene, 1, "staub")
                self.welt.klang("sturz", 0.55 + 0.45 * wucht)
                if k is self.ich:
                    self.kamera.stossen(min(K.KAMERA["ruckeln_max"],
                                            K.STURZ["ruckeln"] + vorher * 0.035))
            self._flughoehen[k.nummer] = k.flug

    # ---- Szene ---------------------------------------------------------
    def schritt(self, dt: float) -> None:
        self._zeit += dt
        if self.menue is None:
            self.knoepfe_sammeln()
        else:
            # Im Menue wird nicht gelaufen und nicht geschossen. Die Welt
            # laeuft trotzdem weiter - beim Gastgeber haengen alle Gaeste
            # daran, und auch der Gast will nicht einfrieren, nur weil er
            # kurz nachsieht, wie die Runde endet.
            self._knoepfe.clear()
            self._waffe_wunsch = -1
            self._rad = 0
        if self.ist_gastgeber:
            self._schritt_gastgeber(dt)
        else:
            self._schritt_gast(dt)

        if self.ich is None:
            return
        if not self.ist_gastgeber:
            self._eigenes_zielen()
        if self.ich.ebene != self._letzte_ebene:
            self._letzte_ebene = self.ich.ebene
            self.blick = self.ich.ebene
            self.blick_rest = 0.0
        if self._rad:
            self.blick = max(0, min(len(self.welt.ebenen) - 1,
                                    self.blick + (1 if self._rad > 0 else -1)))
            self._rad = 0
            self.blick_rest = K.GEFECHT["blick_zurueck"]
        elif self.blick != self.ich.ebene:
            # Die verschobene Ansicht kommt von selbst zurueck.
            #
            # Genau hier verschwand die Ziellinie und kam nicht wieder:
            # Zielhilfen gehoeren zu der Ebene, auf der die Figur steht,
            # und werden darum nur gezeichnet, solange man diese auch
            # anschaut. Wer einmal am Mausrad gedreht hat - oft
            # versehentlich - schaute fuer den Rest der Runde eine Etage
            # daneben. Nichts holte ihn zurueck, und der Hinweis dazu
            # konnte von einem anderen Hinweis verdraengt werden.
            self.blick_rest = max(0.0, self.blick_rest - dt)
            if self.blick_rest <= 0:
                self.blick = self.ich.ebene
        ziel_h = float(self.welt.hoehe(self.blick))
        if self.ich.flug > 0 and self.blick == self.ich.ebene:
            self.blick_hoehe = self.welt.hoehe(self.ich.ebene) + self.ich.flug
        else:
            self.blick_hoehe += (ziel_h - self.blick_hoehe) * min(1.0, 9.0 * dt)
        if self.blick != self.ich.ebene:
            # Hat Vorrang vor jedem anderen Hinweis: solange die Ansicht
            # verschoben ist, fehlen die Zielhilfen, und das muss man
            # wissen.
            self.hinweis = ("ANSICHT EBENE %d - ZURUECK IN %.0f"
                            % (self.blick, self.blick_rest + 0.9))
        ebene = self.welt.ebene(self.ich.ebene)
        self.kamera.schritt(dt, self.ich.pos, self.ich.ziel,
                            (ebene.pixel_breite, ebene.pixel_hoehe))

    def _eigenes_zielen(self) -> None:
        """Beim Gast: die eigene Figur sofort dorthin ausrichten, wo die
        Maus steht.

        Ein Gast simuliert nichts, er setzt seine Figuren dorthin, wo der
        Gastgeber sie meldet. Das Zielen war davon mitbetroffen: `ziel`
        steht in keiner Weltmeldung, also blieb es auf dem Wert aus dem
        Baukasten stehen - dem Einstiegspunkt. Die Ziellinie zeigte darum
        beim Gast sein Leben lang auf die Stelle, an der er eingestiegen
        ist, egal wohin er die Maus hielt.

        Hier wird es einmal je Bild aus der eigenen Maus gesetzt, nicht
        aus dem Netz. Das ist zugleich das Richtigere: Zielen soll ohne
        einen Hin- und Rueckweg Verzoegerung folgen. Geschossen wird
        weiterhin nur dort, wo der Gastgeber es ausrechnet - die Linie ist
        Anzeige, keine Entscheidung.
        """
        ziel = self.kamera.zu_welt(self.app.eingabe.maus)
        self.ich.ziel = ziel
        ab = ziel - self.ich.pos
        if ab.length_squared() > 1:
            self.ich.winkel = math.degrees(math.atan2(ab.y, ab.x))

    # ---- Pausenmenue ----------------------------------------------------
    #
    # Bewusst ein Deckel **in** dieser Szene und keine eigene Szene darueber.
    # Eine geschobene Szene wuerde das Gefecht anhalten - beim Gastgeber
    # heisst das: jeder Gast friert ein, solange einer ins Menue schaut.
    # Hier laeuft die Welt weiter, nur die eigene Eingabe ist stillgelegt.

    def _menue_baut(self) -> list:
        """Die Eintraege, wie sie gerade gelten. Je nach Rolle und Spielart."""
        eintraege = [("weiter", "WEITER", "")]
        if self.ist_gastgeber:
            w = self.wunsch
            eintraege.append(("modus", "SPIELART", K.MODI[w["modus"]]["name"]))
            regeln = K.MODI[w["modus"]]
            if regeln["runden"]:
                eintraege.append(("runden", "RUNDEN BIS SIEG",
                                  str(w["runden_bis"])))
            elif not regeln["zone"] and not regeln["revive"]:
                eintraege.append(("ende", "RUNDE ENDET NACH",
                                  "ZEIT" if w["ende_art"] == "zeit"
                                  else "ABSCHUESSEN"))
                eintraege.append(("wert", "  UND ZWAR BEI",
                                  ("%d MIN" % round(w["ende_wert"] / 60)
                                   if w["ende_art"] == "zeit"
                                   else "%d" % int(w["ende_wert"]))))
            eintraege.append(("schutz", "EINSTIEGSSCHUTZ",
                              "AN" if w["schutz"] else "AUS"))
            eintraege.append(("medkits", "MEDKITS BEIM EINSTIEG",
                              str(w["medkits"])))
            eintraege.append(("medspawn", "MEDKITS AUF DER KARTE",
                              "AN" if w["medkit_spawn"] else "AUS"))
            eintraege.append(("knapp", "MUNITION KNAPP",
                              "AN" if w["knapp"] else "AUS"))
            if regeln["teams"]:
                eintraege.append(("teams", "MANNSCHAFTEN EINTEILEN", ""))
            eintraege.append(("neu", "NEUE RUNDE MIT DIESEN REGELN", ""))
        eintraege.append(("raus", "GEFECHT VERLASSEN", ""))
        return eintraege

    def _menue_auf(self) -> None:
        self.menue = 0
        self.menue_teams = False
        self.menue_zeile = 0
        # Nichts soll weiterlaufen, was man vor dem Aufmachen gedrueckt hat.
        self._knoepfe.clear()
        self._waffe_wunsch = -1

    def _menue_zu(self) -> None:
        self.menue = None
        self.menue_teams = False

    def ereignis(self, ev) -> None:
        if ev.type != pygame.KEYDOWN:
            return
        if ev.key in self.app.opt.codes("pause"):
            # Esc beendete frueher das ganze Spiel. Jetzt macht es auf und
            # wieder zu, und hinaus geht es nur ueber den Eintrag dafuer.
            if self.menue is None:
                self._menue_auf()
            elif self.menue_teams:
                self.menue_teams = False
            else:
                self._menue_zu()
            return
        if self.menue is None:
            return
        self._menue_taste(ev.key)

    def _menue_taste(self, taste) -> None:
        codes = self.app.opt.codes
        hoch = taste in codes("vor") or taste == pygame.K_UP
        runter = taste in codes("zurueck") or taste == pygame.K_DOWN
        links = taste in codes("links") or taste == pygame.K_LEFT
        rechts = taste in codes("rechts") or taste == pygame.K_RIGHT
        waehlen = taste in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)

        if self.menue_teams:
            self._menue_teams_taste(hoch, runter, links, rechts, waehlen)
            return

        eintraege = self._menue_baut()
        if hoch or runter:
            self.menue = (self.menue + (1 if runter else -1)) % len(eintraege)
            self.app.klaenge.spielen("menue", 0.4)
            return
        if not (links or rechts or waehlen):
            return
        schluessel = eintraege[max(0, min(len(eintraege) - 1, self.menue))][0]
        self._menue_wirken(schluessel, rechts or waehlen, waehlen)

    # Eintraege, die etwas *tun*, statt einen Wert zu verstellen. Sie
    # reagieren nur auf Enter. Auf einen Pfeil zu hoeren waere hier
    # gefaehrlich: ein Druck daneben haette das Gefecht beendet.
    TATEN = ("weiter", "raus", "teams", "neu")

    def _menue_wirken(self, schluessel: str, vor: bool, waehlen: bool) -> None:
        if schluessel in self.TATEN and not waehlen:
            return
        self.app.klaenge.spielen("menue_ok" if waehlen else "menue", 0.5)
        if schluessel == "weiter":
            self._menue_zu()
            return
        if schluessel == "raus":
            self.app.laeuft = False
            return
        if not self.ist_gastgeber:
            return
        w = self.wunsch
        if schluessel == "modus":
            namen = list(K.MODI)
            i = (namen.index(w["modus"]) + (1 if vor else -1)) % len(namen)
            w["modus"] = namen[i]
            # Eine Spielart ohne Mannschaften hat kein Rundenziel und
            # umgekehrt - die Anzeige baut sich beim naechsten Bild neu.
            self.menue = min(self.menue, len(self._menue_baut()) - 1)
        elif schluessel == "runden":
            g = K.VERSUS["runden_grenzen"]
            w["runden_bis"] = max(g[0], min(g[1],
                                            w["runden_bis"] + (1 if vor else -1)))
        elif schluessel == "ende":
            w["ende_art"] = "abschuesse" if w["ende_art"] == "zeit" else "zeit"
            w["ende_wert"] = (K.GEFECHT["rundenzeit"] if w["ende_art"] == "zeit"
                              else K.GEFECHT["abschuesse_ziel"])
        elif schluessel == "wert":
            if w["ende_art"] == "zeit":
                w["ende_wert"] = max(60.0, min(1800.0,
                                               w["ende_wert"] + (60 if vor else -60)))
            else:
                w["ende_wert"] = max(1, min(200, w["ende_wert"] + (5 if vor else -5)))
        elif schluessel == "schutz":
            w["schutz"] = not w["schutz"]
        elif schluessel == "medkits":
            w["medkits"] = max(0, min(K.GEFECHT["start_medkits_hoechstens"],
                                      w["medkits"] + (1 if vor else -1)))
        elif schluessel == "medspawn":
            w["medkit_spawn"] = not w["medkit_spawn"]
        elif schluessel == "knapp":
            w["knapp"] = not w["knapp"]
        elif schluessel == "teams":
            self.menue_teams = True
            self.menue_zeile = 0
        elif schluessel == "neu":
            self._runde_neu()
            self._menue_zu()

    def _menue_teams_taste(self, hoch, runter, links, rechts, waehlen) -> None:
        leute = sorted(self.kaempfer.values(), key=lambda k: k.nummer)
        if not leute:
            self.menue_teams = False
            return
        if hoch or runter:
            self.menue_zeile = (self.menue_zeile
                                + (1 if runter else -1)) % len(leute)
            self.app.klaenge.spielen("menue", 0.4)
            return
        if links or rechts or waehlen:
            k = leute[max(0, min(len(leute) - 1, self.menue_zeile))]
            self._team_setzen(k, (k.team + 1) % len(K.TEAMS["namen"]))
            self.app.klaenge.spielen("menue_ok", 0.5)

    def _team_setzen(self, k, team: int) -> None:
        """Einen Mitspieler in die andere Mannschaft stecken.

        Sofort, nicht erst zur naechsten Runde: der Gastgeber macht das,
        weil es gerade ungleich steht, und dann soll es auch gerade
        gerade werden. Die Fraktion muss mit, sonst schiesst der Mann
        weiter auf seine neuen Leute.
        """
        if not self.mit_teams:
            return
        k.team = max(0, min(len(K.TEAMS["namen"]) - 1, int(team)))
        k.fraktion = self._fraktion_fuer(k.nummer, k.team)
        k.pos.update(self._einstiegsort(k.team))
        k.vorher.update(k.pos)
        k.unverwundbar = self.schutz_zeit

    def _runde_neu(self) -> None:
        """Alles zuruecksetzen und mit den gewuenschten Regeln neu anfangen.

        Der Gastgeber allein entscheidet das, und die Gaeste bekommen die
        neuen Regeln geschickt wie beim Verbinden. Ohne diese Nachricht
        spielten sie die Runde mit den alten weiter.
        """
        w = self.wunsch
        self.modus = w["modus"] if w["modus"] in K.MODI else K.MODUS_VORGABE
        self.regeln = K.MODI[self.modus]
        self.ende_art = w["ende_art"] if w["ende_art"] in K.ENDE_ARTEN else "zeit"
        self.ende_wert = float(w["ende_wert"])
        self.runden_bis = int(w["runden_bis"])
        self.knapp = bool(w["knapp"])
        self.schutz_an = bool(w["schutz"])
        self.start_medkits = int(w["medkits"])
        self.medkits_spawnen = bool(w["medkit_spawn"])

        self.teampunkte = [0] * len(K.TEAMS["namen"])
        self.zone_stand = [0.0] * len(self.teampunkte)
        self.zone_halter = -1
        self.runde = 0
        self.runden_pause = 0.0
        self.sieger_team = -1
        self.welle = 0
        self.pause_rest = K.WELLEN_MP["pause"]
        self.vorbei = False
        self.gewonnen = False
        self.liste = []
        self.rest = self.ende_wert if self.ende_art == "zeit" else 0.0

        # Alles, was herumliegt oder herumlaeuft, kommt weg: eine neue
        # Runde faengt nicht mit den Granaten der alten an.
        for g in self.gegner_offen:
            g.lebt = False
        self.gegner_offen = []
        for x in list(self.welt.wesen) + list(self.welt.neue):
            if not isinstance(x, Kaempfer):
                x.lebt = False
        self.welt.rauch = []

        for k in self.kaempfer.values():
            k.abschuesse = 0
            k.tode = 0
            k.knapp = self.knapp
            k.vorrat = {v: K.MUNITION["vorrat"].get(v, 0) for v in k.waffen}
            k.team = self._team_fuer() if self.mit_teams else -1
            k.fraktion = self._fraktion_fuer(k.nummer, k.team)
            self._regeln_anlegen(k)
            k.lebt = True
            self._wieder_einsteigen(k)

        if self.ist_gastgeber:
            self.gastgeber.an_alle(dict(self._willkommen(-1, None),
                                        t="neustart"))

    def _wunsch_lesen(self) -> dict:
        """Die Regeln, die gerade gelten, als Ausgangspunkt fuers Menue."""
        return dict(modus=self.modus, ende_art=self.ende_art,
                    ende_wert=self.ende_wert, runden_bis=self.runden_bis,
                    knapp=self.knapp, schutz=self.schutz_an,
                    medkits=self.start_medkits,
                    medkit_spawn=self.medkits_spawnen)


    # ---- Bild ----------------------------------------------------------
    def zeichnen(self, ziel, alpha: float) -> None:
        self.renderer.welt_zeichnen(ziel, self.welt, self.kamera, alpha,
                                    self.blick_hoehe, blick=self.blick,
                                    boden=self._kreis_zeichnen)
        if not self.ist_gastgeber:
            self._fremdes_zeichnen(ziel)
        if (self.ich is not None and self.ich.lebt and not self.ich.am_boden
                and self.blick == self.ich.ebene):
            self.renderer.zielhilfen(ziel, self.welt, self.kamera, self.ich)
            self.renderer.tracer(ziel, self.welt, self.kamera, self.ich)
        self._namen_zeichnen(ziel)
        if self.ich is not None and self.ich.hilft is not None:
            # Blauer Schein am Rand, solange man jemanden aufhilft. Er
            # sagt, warum die Figur gerade nicht laeuft und nicht
            # schiesst - ohne ihn haelt man es fuer einen Haenger.
            opfer = self.kaempfer.get(self.ich.hilft)
            stand = opfer.revive_stand if opfer is not None else 0.0
            self.renderer.randglut(ziel, K.C_TEAL, 0.45 + 0.55 * stand)
        self._anzeige(ziel)
        if self.vorbei:
            self._endtafel(ziel)
        if self.menue is not None:
            self._menue_zeichnen(ziel)

    def _kreis_zeichnen(self, flaeche, ebene: int, ecke) -> None:
        """Der Kreis in der Kartenmitte, auf den Boden seiner Ebene.

        Wird vom Renderer je Ebene aufgerufen, noch bevor die Figuren
        darauf stehen. Auf den verkleinerten Tiefenflaechen stimmt er
        dadurch von selbst: dort ist die Flaeche groesser und wird
        hinterher als Ganzes verkleinert.

        Die Farbe gehoert dem, der gerade haelt. Haelt niemand, bleibt sie
        neutral - man soll auf einen Blick sehen, ob der Kreis umkaempft
        ist oder laeuft.
        """
        if not self.regeln["zone"] or ebene != K.ZONE["ebene"]:
            return
        z = K.ZONE
        halter = self.zone_halter
        if 0 <= halter < len(K.TEAMS["farben"]):
            farbe = K.TEAMS["farben"][halter]
            anteil = self.zone_stand[halter] / z["bis"]
        else:
            farbe = K.C_CREAM
            anteil = max(self.zone_stand) / z["bis"] if self.zone_stand else 0.0
        self.renderer.kreis_zone(flaeche, self.zone_mitte - ecke, z["radius"],
                                 farbe, anteil, self._zeit / z["puls"],
                                 z["ring"], z["fuellung"])

    def _fremdes_zeichnen(self, ziel) -> None:
        """Beim Gast gibt es keine echten Wesen dafuer, nur gemeldete Punkte.

        Gegner, Beute, Geschosse und geworfene Granaten. Ohne das fliegt
        einem eine Granate ins Gesicht, die man nie gesehen hat, und die
        Wellen sind unsichtbar.
        """
        ecke = self.kamera.ecke
        for (x, y, ebene, bild) in self._fremde_beute:
            if ebene != self.blick:
                continue
            s = self.renderer.bilder.bild(bild)
            ziel.blit(s, (x - ecke.x - s.get_width() / 2,
                          y - ecke.y - s.get_height() / 2))
        for (x, y, winkel, ebene, art, anteil) in self._fremde_gegner:
            if ebene != self.blick:
                continue
            name = K.GEGNER.get(art, {}).get("bild", "gegner_laeufer")
            s = self.renderer.bilder.gedreht(name, winkel)
            p = pygame.Vector2(x - ecke.x, y - ecke.y)
            sch = self.renderer.schatten(K.GEGNER.get(art, {}).get("radius", 9))
            ziel.blit(sch, (p.x - sch.get_width() / 2 + 1,
                            p.y - sch.get_height() / 2 + 3))
            ziel.blit(s, (p.x - s.get_width() / 2, p.y - s.get_height() / 2))
            if anteil < 0.999:
                breite = 20
                pygame.draw.rect(ziel, (16, 11, 8),
                                 (int(p.x) - breite // 2, int(p.y) - 20, breite, 2))
                pygame.draw.rect(ziel, K.C_RED,
                                 (int(p.x) - breite // 2, int(p.y) - 20,
                                  int(breite * anteil), 2))
        for (x, y, winkel, ebene, name, hoehe) in self._fremde_schuesse:
            if hoehe > 0:
                # Faellt gerade eine Ebene tiefer: mit dem Massstab ihrer
                # eigenen Hoehe zeichnen, wie es der Gastgeber auch tut.
                self.renderer.fliegendes(ziel, self.welt, self.kamera,
                                         self.blick_hoehe,
                                         pygame.Vector2(x, y), winkel, ebene,
                                         hoehe, name)
                continue
            if ebene != self.blick:
                continue
            s = self.renderer.bilder.gedreht(name, winkel)
            ziel.blit(s, (x - ecke.x - s.get_width() / 2,
                          y - ecke.y - s.get_height() / 2))

    def _farbe_fuer(self, k, eigen: bool = False):
        """In welcher Farbe ein Mitspieler auftaucht.

        Mit Mannschaften zaehlt die Mannschaft, nicht die eigene Figur: wer
        im Gefecht ueberlegen muss, ob der da drueben zu ihm gehoert, hat
        schon verloren. Die eigene Mannschaft bekommt die helle Farbe, die
        fremde die dunkle.
        """
        if k.am_boden:
            return K.C_RED
        if self.mit_teams and 0 <= k.team < len(K.TEAMS["farben"]):
            eigenes_team = (self.ich is not None and k.team == self.ich.team)
            paar = K.TEAMS["farben"] if eigenes_team else K.TEAMS["dunkel"]
            return paar[k.team]
        if eigen:
            return K.C_TEAL
        if self.regeln["beute"]:
            return K.C_AMBER
        return K.C_HULL                   # eigene Mannschaft, kein Ziel

    def _namen_zeichnen(self, ziel) -> None:
        """Ueber jedem Mitspieler sein Name, sein Leben und sein Schutz.

        Wer im dichten Rauch steht, bekommt nichts davon - sonst waere
        eine Rauchwand wertlos: man saehe zwar die Gestalt nicht mehr,
        aber ihr Name schwebte weiter ueber der Wolke und zeigte genau,
        wo sie steht. Gefragt wird nach der Ebene des Verborgenen, nicht
        nach der des Zuschauers: auch von oben sieht man in eine
        Rauchwand nicht hinein.
        """
        ecke = self.kamera.ecke
        for k in self.kaempfer.values():
            if not k.lebt or k.ebene != self.blick:
                continue
            if k is not self.ich and self.welt.verdeckt(k.pos, k.ebene):
                continue
            p = k.pos - ecke
            if not (0 <= p.x <= K.GAME_W and 0 <= p.y <= K.GAME_H):
                continue
            eigen = (k is self.ich)
            farbe = self._farbe_fuer(k, eigen)
            SCHRIFT.zeichnen(ziel, k.name, int(p.x), int(p.y) - 26, farbe, 1,
                             ausrichtung="mitte")
            if self.schutz_an and k.unverwundbar > 0 and not k.am_boden:
                # Eine Leiste, solange der Einstiegsschutz haelt, und ein
                # Ring um die Figur. Ohne beides sieht man nur, dass
                # Treffer nichts tun, und haelt es fuer einen Fehler.
                anteil = max(0.0, min(1.0, k.unverwundbar / K.GEFECHT["schutz"]))
                breit = 24
                pygame.draw.rect(ziel, (16, 11, 8),
                                 (int(p.x) - breit // 2, int(p.y) - 34, breit, 3))
                pygame.draw.rect(ziel, K.C_TEAL,
                                 (int(p.x) - breit // 2, int(p.y) - 34,
                                  int(breit * anteil), 3))
                pygame.draw.circle(ziel, K.C_TEAL, (int(p.x), int(p.y)),
                                   int(13 + 5 * anteil), 1)
            if eigen and self.mit_teams:
                # Mit Mannschaften traegt auch die eigene Figur die
                # Mannschaftsfarbe. Der Strich darueber sagt: das bist du.
                pygame.draw.rect(ziel, K.C_CREAM,
                                 (int(p.x) - 3, int(p.y) - 31, 7, 1))
            breite = 24
            if k.am_boden:
                # Am Boden zeigt der Balken, wie weit das Aufhelfen ist -
                # wichtiger als das Leben, das ohnehin null ist.
                pygame.draw.rect(ziel, (16, 11, 8),
                                 (int(p.x) - breite // 2, int(p.y) - 18, breite, 3))
                pygame.draw.rect(ziel, K.C_TEAL,
                                 (int(p.x) - breite // 2, int(p.y) - 18,
                                  int(breite * k.revive_stand), 3))
                if not eigen and self._darf_helfen(self.ich, k):
                    SCHRIFT.zeichnen(ziel, "[E]", int(p.x), int(p.y) + 14,
                                     K.C_TEAL, 1, ausrichtung="mitte")
                continue
            anteil = max(0.0, min(1.0, k.leben / k.max_leben))
            pygame.draw.rect(ziel, (16, 11, 8),
                             (int(p.x) - breite // 2, int(p.y) - 18, breite, 3))
            pygame.draw.rect(ziel, farbe,
                             (int(p.x) - breite // 2, int(p.y) - 18,
                              int(breite * anteil), 3))

    def _teamkopf(self, ziel, y: int) -> int:
        """Mannschaftsstand oben in der Mitte, je nach Spielart.

        Drei Spielarten, eine Anzeige: was zaehlt, steht in der Mitte
        zwischen den beiden Mannschaftsnamen - Abschuesse, Rundensiege oder
        der Ladestand des Kreises. Der Kreis bekommt zusaetzlich zwei
        Balken, weil man dort auf ein Zehntel genau sehen will, wie knapp
        es ist.
        """
        f = SCHRIFT
        namen = K.TEAMS["namen"]
        farben = K.TEAMS["farben"]
        if self.regeln["zone"]:
            werte = [int(s) for s in self.zone_stand]
        else:
            werte = list(self.teampunkte)
        mitte = K.GAME_W // 2
        f.zeichnen(ziel, "%s %d" % (namen[0], werte[0]), mitte - 8, y,
                   farben[0], 1, ausrichtung="rechts")
        f.zeichnen(ziel, ":", mitte, y, K.C_MUTED_DK, 1, ausrichtung="mitte")
        f.zeichnen(ziel, "%d %s" % (werte[1], namen[1]), mitte + 8, y,
                   farben[1], 1)
        y += 10

        if self.regeln["zone"]:
            breite, hoehe = 60, 4
            for i, stand in enumerate(self.zone_stand[:2]):
                anteil = max(0.0, min(1.0, stand / K.ZONE["bis"]))
                links = mitte - breite - 6 if i == 0 else mitte + 6
                pygame.draw.rect(ziel, (16, 11, 8), (links, y, breite, hoehe))
                fuellung = int(breite * anteil)
                if i == 0:
                    pygame.draw.rect(ziel, farben[0], (links, y, fuellung, hoehe))
                else:
                    # Der rechte Balken waechst nach rechts los, damit beide
                    # von der Mitte aus laufen.
                    pygame.draw.rect(ziel, farben[1], (links, y, fuellung, hoehe))
            y += hoehe + 4
            if self.zone_halter >= 0:
                f.zeichnen(ziel, "%s HAELT DEN KREIS" % namen[self.zone_halter],
                           mitte, y, farben[self.zone_halter], 1,
                           ausrichtung="mitte")
            elif self.ich is not None and self.in_der_zone(self.ich):
                f.zeichnen(ziel, "UMKAEMPFT", mitte, y, K.C_CREAM, 1,
                           ausrichtung="mitte")
            y += 10
            return y

        if self.regeln["runden"]:
            if not self._beide_besetzt():
                f.zeichnen(ziel, "WARTET AUF MITSPIELER", mitte, y,
                           K.C_MUTED, 1, ausrichtung="mitte")
            elif self.runden_pause > 0:
                f.zeichnen(ziel, "NAECHSTE RUNDE IN %d"
                           % max(1, int(self.runden_pause + 0.99)), mitte, y,
                           K.C_AMBER, 1, ausrichtung="mitte")
            else:
                f.zeichnen(ziel, "RUNDE %d  BIS %d SIEGEN"
                           % (max(1, self.runde), self.runden_bis),
                           mitte, y, K.C_MUTED, 1, ausrichtung="mitte")
            y += 10
        return y

    def _anzeige(self, ziel) -> None:
        f = SCHRIFT
        # Kopfzeile: Spielart, und was die Runde beendet
        f.zeichnen(ziel, K.MODI[self.modus]["name"], 12, 12, K.C_AMBER, 1)
        rolle = "GASTGEBER" if self.ist_gastgeber else "GAST"
        f.zeichnen(ziel, rolle, 12, 22, K.C_MUTED_DK, 1)
        if self.ist_gastgeber:
            f.zeichnen(ziel, self.gastgeber.adresse, 12, 32, K.C_MUTED_DK, 1)

        if self.mit_gegnern:
            f.zeichnen(ziel, "WELLE %d" % max(1, self.welle), K.GAME_W // 2, 10,
                       K.C_CREAM, 2, ausrichtung="mitte")
        # Die Uhr laeuft ueberall ausser in pve: dort endet die Runde, wenn
        # alle liegen, und eine Uhr waere eine Zahl ohne Bedeutung.
        mit_uhr = self.mit_teams or not self.regeln["revive"]
        y_kopf = 28 if self.mit_gegnern else 10
        if self.ende_art == "zeit" and mit_uhr:
            minuten, sekunden = divmod(int(max(0.0, self.rest)), 60)
            f.zeichnen(ziel, "%d:%02d" % (minuten, sekunden), K.GAME_W // 2,
                       y_kopf, K.C_CREAM, 1 if self.mit_gegnern else 2,
                       ausrichtung="mitte")
            y_kopf += 16 if not self.mit_gegnern else 10
        elif mit_uhr and not self.regeln["zone"] and not self.regeln["runden"]:
            text = ("BIS %d TEAMABSCHUESSE" if self.mit_teams
                    else "BIS %d ABSCHUESSE")
            f.zeichnen(ziel, text % int(self.ende_wert or
                                        K.GEFECHT["team_abschuesse"]),
                       K.GAME_W // 2, y_kopf + 2, K.C_MUTED, 1,
                       ausrichtung="mitte")
            y_kopf += 12
        if self.mit_teams:
            self._teamkopf(ziel, y_kopf)

        # Punktestand rechts, unterhalb der Ebenenanzeige
        y = K.GEFECHT["tafel_oben"]
        for eintrag in bestenliste.sortiert(
                [{"name": k.name, "abschuesse": k.abschuesse, "tode": k.tode,
                  "k": k} for k in self.kaempfer.values()]):
            wer = eintrag["k"]
            if self.mit_teams:
                farbe = self._farbe_fuer(wer, wer is self.ich)
            elif wer is self.ich:
                farbe = K.C_TEAL
            elif wer.am_boden:
                farbe = K.C_RED
            else:
                farbe = K.C_MUTED
            marke = ">" if wer is self.ich else " "
            f.zeichnen(ziel, "%s%-10s %2d/%2d" % (marke, eintrag["name"],
                                                  eintrag["abschuesse"],
                                                  eintrag["tode"]),
                       K.GAME_W - 12, y, farbe, 1, ausrichtung="rechts")
            y += 9

        if self.ich is None:
            return
        if self.ich.am_boden:
            f.zeichnen(ziel, "AM BODEN", K.GAME_W // 2, K.GAME_H // 2 - 10,
                       K.C_RED, 2, ausrichtung="mitte")
            f.zeichnen(ziel, "NOCH %d SEKUNDEN" % max(0, int(self.ich.boden_rest)),
                       K.GAME_W // 2, K.GAME_H // 2 + 8, K.C_MUTED, 1,
                       ausrichtung="mitte")
        elif not self.ich.lebt and not self.vorbei:
            f.zeichnen(ziel, "GEFALLEN", K.GAME_W // 2, K.GAME_H // 2 - 10,
                       K.C_RED, 2, ausrichtung="mitte")
            if self.regeln["runden"]:
                f.zeichnen(ziel, "RAUS BIS ZUR NAECHSTEN RUNDE", K.GAME_W // 2,
                           K.GAME_H // 2 + 8, K.C_MUTED, 1,
                           ausrichtung="mitte")
            elif not self.regeln["revive"]:
                f.zeichnen(ziel, "WIEDER IN %.0f" % max(0.0, self.ich.wieder_in),
                           K.GAME_W // 2, K.GAME_H // 2 + 8, K.C_MUTED, 1,
                           ausrichtung="mitte")
        else:
            self.renderer.hud(ziel, self.welt, self.ich, "",
                              self.ich.abschuesse, self.blick, kopf=False)
            if self.knapp:
                # Bei knapper Munition steht der Vorrat unter dem Magazin.
                # Ohne ihn weiss man nicht, ob sich Nachladen noch lohnt.
                vorrat = self.ich.vorrat.get(self.ich.waffe_name, 0)
                f.zeichnen(ziel, "VORRAT %d" % vorrat, K.GAME_W - 12,
                           K.GAME_H - 38, K.C_MUTED if vorrat else K.C_RED, 1,
                           ausrichtung="rechts")
        if self.hinweis:
            self.renderer.hinweis(ziel, self.hinweis)

    def _menue_zeichnen(self, ziel) -> None:
        """Der Deckel ueber dem laufenden Gefecht.

        Halb durchsichtig, damit man sieht, dass es weitergeht - das ist
        keine Kosmetik, sondern eine Warnung: wer hier steht, steht auch
        in der Welt herum und kann erschossen werden.
        """
        f = SCHRIFT
        deckel = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
        deckel.fill((9, 6, 5, 190))
        ziel.blit(deckel, (0, 0))

        if self.menue_teams:
            self._menue_teams_zeichnen(ziel)
            return

        f.zeichnen(ziel, "PAUSE", K.GAME_W // 2, 34, K.C_AMBER, 3,
                   ausrichtung="mitte")
        f.zeichnen(ziel, "DAS GEFECHT LAEUFT WEITER", K.GAME_W // 2, 58,
                   K.C_RED, 1, ausrichtung="mitte")
        if self.ist_gastgeber:
            f.zeichnen(ziel, "AENDERUNGEN GELTEN AB DER NAECHSTEN RUNDE",
                       K.GAME_W // 2, 70, K.C_MUTED_DK, 1, ausrichtung="mitte")

        eintraege = self._menue_baut()
        self.menue = max(0, min(len(eintraege) - 1, self.menue))
        y = 92
        for i, (_schluessel, text, wert) in enumerate(eintraege):
            aktiv = (i == self.menue)
            farbe = K.C_CREAM if aktiv else K.C_MUTED
            if aktiv:
                pygame.draw.rect(ziel, (24, 17, 12), (110, y - 3, 420, 13))
                pygame.draw.rect(ziel, K.C_AMBER, (110, y - 3, 3, 13))
            f.zeichnen(ziel, text, 124, y, farbe, 1)
            if wert:
                f.zeichnen(ziel, "< %s >" % wert if aktiv else wert, 520, y,
                           K.C_AMBER if aktiv else K.C_MUTED_DK, 1,
                           ausrichtung="rechts")
            y += 15

        f.zeichnen(ziel, "PFEILE WAEHLEN   ENTER BESTAETIGT   [ESC] ZURUECK",
                   K.GAME_W // 2, K.GAME_H - 22, K.C_MUTED_DK, 1,
                   ausrichtung="mitte")

    def _menue_teams_zeichnen(self, ziel) -> None:
        f = SCHRIFT
        f.zeichnen(ziel, "MANNSCHAFTEN", K.GAME_W // 2, 34, K.C_AMBER, 3,
                   ausrichtung="mitte")
        f.zeichnen(ziel, "ENTER ODER PFEILE VERSCHIEBEN - SOFORT",
                   K.GAME_W // 2, 58, K.C_MUTED_DK, 1, ausrichtung="mitte")
        leute = sorted(self.kaempfer.values(), key=lambda k: k.nummer)
        if leute:
            self.menue_zeile = max(0, min(len(leute) - 1, self.menue_zeile))
        y = 86
        for i, k in enumerate(leute):
            aktiv = (i == self.menue_zeile)
            if aktiv:
                pygame.draw.rect(ziel, (24, 17, 12), (140, y - 3, 360, 13))
                pygame.draw.rect(ziel, K.C_AMBER, (140, y - 3, 3, 13))
            f.zeichnen(ziel, k.name, 154, y,
                       K.C_CREAM if aktiv else K.C_MUTED, 1)
            if 0 <= k.team < len(K.TEAMS["namen"]):
                f.zeichnen(ziel, K.TEAMS["namen"][k.team], 490, y,
                           K.TEAMS["farben"][k.team], 1, ausrichtung="rechts")
            y += 15
        # Wie es gerade steht, damit man sieht, ob man gerade ausgleicht
        groessen = [0] * len(K.TEAMS["namen"])
        for k in leute:
            if 0 <= k.team < len(groessen):
                groessen[k.team] += 1
        f.zeichnen(ziel, "  ".join("%s %d" % (n, g)
                                   for n, g in zip(K.TEAMS["namen"], groessen)),
                   K.GAME_W // 2, y + 10, K.C_MUTED, 1, ausrichtung="mitte")
        f.zeichnen(ziel, "[ESC] ZURUECK", K.GAME_W // 2, K.GAME_H - 22,
                   K.C_MUTED_DK, 1, ausrichtung="mitte")

    def _endtafel(self, ziel) -> None:
        deckel = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
        deckel.fill((9, 6, 5, 220))
        ziel.blit(deckel, (0, 0))
        f = SCHRIFT
        farbe_kopf = K.C_AMBER
        if self.mit_teams:
            if 0 <= self.sieger_team < len(K.TEAMS["namen"]):
                kopf = "%s GEWINNT" % K.TEAMS["namen"][self.sieger_team]
                farbe_kopf = K.TEAMS["farben"][self.sieger_team]
            else:
                kopf = "UNENTSCHIEDEN"
            if self.regeln["zone"]:
                unter = "%d : %d IM KREIS" % (int(self.zone_stand[0]),
                                              int(self.zone_stand[1]))
            else:
                unter = "%s %d : %d %s" % (K.TEAMS["namen"][0],
                                           self.teampunkte[0],
                                           self.teampunkte[1],
                                           K.TEAMS["namen"][1])
        elif self.regeln["revive"]:
            kopf = "ALLE GEFALLEN"
            unter = "WELLE %d ERREICHT" % max(1, self.welle)
        else:
            kopf = "RUNDE VORBEI"
            unter = "WELLE %d" % self.welle if self.mit_gegnern else ""
        f.zeichnen(ziel, kopf, K.GAME_W // 2, 40, farbe_kopf, 3,
                   ausrichtung="mitte")
        if unter:
            f.zeichnen(ziel, unter, K.GAME_W // 2, 66, K.C_MUTED, 1,
                       ausrichtung="mitte")
        y = 92
        for platz, e in enumerate(self.liste, 1):
            farbe = K.C_CREAM if platz == 1 else K.C_MUTED
            f.zeichnen(ziel, "%d." % platz, 180, y, farbe, 1)
            f.zeichnen(ziel, str(e.get("name", "?")), 206, y, farbe, 1)
            f.zeichnen(ziel, "%d ABSCHUESSE  %d TODE"
                       % (e.get("abschuesse", 0), e.get("tode", 0)),
                       K.GAME_W - 180, y, farbe, 1, ausrichtung="rechts")
            y += 12
        f.zeichnen(ziel, "[ESC] BEENDEN", K.GAME_W // 2, K.GAME_H - 30,
                   K.C_MUTED_DK, 1, ausrichtung="mitte")

    def verlassen(self) -> None:
        if self.ist_gastgeber:
            self.gastgeber.schliessen()
        elif self.gast is not None:
            self.gast.schliessen()
