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
from . import ablage
from . import konto as konto_modul
from . import netz
from . import ui
from . import world as welt_modul
from .core import Szene
from .entities import (Aufsammler, Brandflaeche, Gegner, Rakete,
                       Rauchwolke, Spieler, wolke)
from .font import SCHRIFT
from .render import Befinden, Kamera, Renderer
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
                 fraktion: str, knapp: bool = False, team: int = -1,
                 loadout=None) -> None:
        super().__init__(pos, ebene)
        # Ein Loadout, wenn die Runde danach gespielt wird. Gesetzt wird es
        # **vor** allem anderen, weil Magazin und Vorrat je Waffe angelegt
        # werden: nachtraeglich haette die Figur Munition fuer Waffen, die
        # sie nicht traegt, und keine fuer die, die sie traegt.
        if loadout:
            plaetze = konto_modul.hotbar_aus_loadout(loadout)
            if plaetze:
                self.waffen = plaetze
                self.waffe = 0
                self.magazin = {w: K.WAFFEN[w]["magazin"] for w in self.waffen}
        self.loadout = dict(loadout) if loadout else None
        self.fraktion = fraktion
        self.nummer = nummer
        self.name = name
        self.team = team             # -1 = keine Mannschaft, sonst 0 oder 1
        self.raus = False            # in versus: diese Runde erledigt
        self.abschuesse = 0
        self.tode = 0
        # Wen dieser Kaempfer wie oft erwischt hat. Gebraucht fuer die
        # Zeile "am oeftesten erledigt" auf der Siegtafel - die Zahl, die
        # nach der Runde am meisten erzaehlt, weil sie sagt, wer gegen wen
        # gespielt hat und nicht nur wie gut.
        self.opfer: dict[int, int] = {}
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
        # Wen er gerade zieht (Nummer oder None), und von wem er gezogen
        # wird. Beides getrennt, weil beide Seiten es wissen muessen: der
        # Ziehende, um langsamer zu gehen, der Gezogene, um nicht zu
        # zweit an ihm zu zerren.
        self.zieht = None
        self.gezogen_von = None
        # Rufen am Boden: Sperre bis zum naechsten Ruf, und wie lange der
        # letzte noch zu sehen ist.
        self.ruf_sperre = 0.0
        self.ruf_zeigen = 0.0
        # Munitionsvorrat
        self.knapp = knapp
        self.vorrat = {w: K.MUNITION["vorrat"].get(w, 0) for w in self.waffen}

    @property
    def team_vorsatz(self) -> str:
        """`rot_`, `blau_` oder leer - je nach Mannschaft.

        Leer heisst: keine Mannschaften im Spiel, also traegt niemand eine
        Farbe. In einem Jeder-gegen-jeden waere sie auch sinnlos.
        """
        if 0 <= self.team < len(K.TEAMS["kombi"]):
            return K.TEAMS["kombi"][self.team]["name"].lower() + "_"
        return ""

    @property
    def bild(self) -> str:
        """Am Boden eine eigene Figur, sonst die mit der Waffe - und beides
        in den Farben der Mannschaft.

        Zwei Dinge muss man einer Gestalt auf einen Blick ansehen, ohne
        Namen und ohne Balken:

        **Wer unten liegt.** Ohne das unterschied sich ein Liegender nur
        durch die Farbe seines Namens von einem Stehenden - im Gefecht viel
        zu wenig. Ein Gegner muss sofort erkennen, wen er liegen lassen
        kann und wo gleich jemand zum Helfen stehen bleibt.

        **Zu wem er gehoert.** Namen verschwinden im Rauch, auf Entfernung
        und eine Ebene tiefer. Die Farbe der Figur bleibt. Deshalb traegt
        sie die Mannschaftsfarbe und nicht nur die Schrift darueber.
        """
        vorsatz = self.team_vorsatz
        if self.am_boden:
            name = "spieler_%sboden" % vorsatz
            return name if name in K.BILD_MASS else "spieler_boden"
        if self.schwingt:
            # Waffe verstaut, nur die Gestalt - darueber zeichnet der
            # Renderer die Bewegung des Eisens.
            name = "spieler_%s" % vorsatz.rstrip("_") if vorsatz else "spieler"
            return name if name in K.BILD_MASS else "spieler"
        name = "spieler_%s%s" % (vorsatz, self.waffe_name)
        return name if name in K.BILD_MASS else super().bild

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

    def schaden(self, menge, schub=None, von=None) -> None:
        # Am Boden gibt es keinen Rueckstoss. Wer liegt, liegt - sonst
        # schoebe jede Salve, jede Granate und jeder Stampfer einen
        # Gefallenen ein Stueck weiter, und am Ende laege er ganz woanders
        # als dort, wo sein Team ihn zuletzt gesehen hat.
        if self.am_boden:
            schub = None
        super().schaden(menge, schub, von)

    def zeichenpos(self, alpha: float) -> pygame.Vector2:
        """Wo die Figur gezeichnet wird. Beim Ruf zuckt sie kurz.

        Nur das Bild bewegt sich, nicht die Figur - sonst verschoebe jeder
        Ruf den Gefallenen, und genau das soll am Boden nicht mehr gehen.
        """
        p = super().zeichenpos(alpha)
        if self.am_boden and self.ruf_zeigen > 0.0:
            frisch = self.ruf_zeigen - (K.RUFEN["zeigen"] - 0.45)
            if frisch > 0.0:
                t = self.ruf_zeigen * 58.0
                weit = K.RUFEN["zucken"] * min(1.0, frisch / 0.45)
                p = p + pygame.Vector2(math.sin(t) * weit,
                                       math.cos(t * 1.3) * weit * 0.6)
        return p

    def aufhelfen(self) -> None:
        """Wieder auf die Beine, mit angeschlagenem Leben."""
        self.am_boden = False
        self.boden_rest = 0.0
        self.revive_stand = 0.0
        self.gezogen_von = None
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
        self.ruf_sperre = max(0.0, self.ruf_sperre - dt)
        self.ruf_zeigen = max(0.0, self.ruf_zeigen - dt)
        if not self.am_boden:
            self.ruf_zeigen = 0.0
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

    BILDER = {"munition": "munikiste", "medkit": "medkit",
              "rakete": "rpg_kiste"}

    def __init__(self, pos, art: str, ebene: int, kaempfer: dict) -> None:
        super().__init__(pos, art, ebene)
        self.bild = self.BILDER.get(art, "medkit")
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
            elif self.art == "rakete":
                # Wer schon einen traegt, laesst ihn liegen. Sonst waere
                # der Werfer einmal in der Runde eben doch zweimal da.
                genommen = k.rpg_nehmen()
            if genommen:
                self.lebt = False
                k.zaehlen("beute")
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

    def __init__(self, pos, art: str, ebene: int, gefecht,
                 leben: float | None = None) -> None:
        super().__init__(pos, art, ebene, leben=leben)
        self._gefecht = gefecht
        self._ziel = None
        self._ziel_rest = 0.0
        # Haengerwache: bestes bisher erreichtes Naeherkommen und wie
        # lange es sich nicht gebessert hat.
        self._bestes = 1e18
        self._stockt = 0.0
        self._pruef_rest = K.GEGNER_MP["stockt_pruefung"]

    def _haenger_pruefen(self, dt: float) -> None:
        """Wer nicht naeher kommt, wird umgesetzt.

        Ohne das steht eine Runde still, sobald ein einziger Gegner
        haengt: eine Welle endet erst, wenn alle liegen. Gemessen auf
        STAUBTAL blieb ein Laeufer 120 Sekunden lang 323 Pixel entfernt
        an einer Plateauwand haengen, auf derselben Ebene wie die
        Spieler - in 300 Sekunden wurde Welle 2 nicht fertig.

        Umgesetzt statt getoetet: ein Gegner, der sich in Luft aufloest,
        ist ein Fehler, den man sieht. Einer, der aus einer anderen
        Richtung kommt, ist keiner - und er ist ausser Sicht, wenn es
        passiert, weil die Spawnstelle genau darauf geprueft wird.

        Ein Boss wird nie umgesetzt. Ihn zu suchen ist Teil der Aufgabe,
        und ein Boss, der hinter dem Ruecken neu auftaucht, ist unfair.
        """
        if self.ist_boss:
            return
        self._pruef_rest -= dt
        if self._pruef_rest > 0.0:
            return
        g = K.GEGNER_MP
        self._pruef_rest = g["stockt_pruefung"]
        ziel = self._ziel
        if ziel is None or not ziel.lebt:
            self._bestes = 1e18
            self._stockt = 0.0
            return
        weit = self.pos.distance_to(ziel.pos)
        if ziel.ebene != self.ebene:
            weit += g["ebenen_strafe"]
        if weit < self._bestes - g["stockt_schritt"]:
            self._bestes = weit
            self._stockt = 0.0
            return
        self._stockt += g["stockt_pruefung"]
        if self._stockt < g["stockt_ab"]:
            return
        ebene, pos = self._gefecht._spawnstelle()
        self.pos.update(pos)
        self.vorher.update(pos)
        self.ebene = ebene
        self.tempo.update(0, 0)
        self._bestes = 1e18
        self._stockt = 0.0
        self._ziel = None          # am neuen Ort neu entscheiden

    def _brut_erzeugen(self, punkt, art: str):
        """Was die Mutter ruft, ist ein KampfGegner und wird mitgezaehlt.

        Ohne das Mitzaehlen laeuft die Welle weiter, sobald die
        urspruenglichen Gegner liegen - die Brut stuende dann noch auf
        der Karte, waehrend schon die naechste Welle anfaengt. Und ohne
        KampfGegner suchte sie sich kein Ziel unter mehreren Spielern.
        """
        kind = KampfGegner(punkt, art, self.ebene, self._gefecht)
        self._gefecht.gegner_offen.append(kind)
        return kind

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
        self._haenger_pruefen(dt)


# ══════════════════════════════════════════════════════════════════
# Die Szene
# ══════════════════════════════════════════════════════════════════

class Gefecht(Szene):
    """Die Spielszene fuer den LAN-Test, beim Gastgeber wie beim Gast."""

    # Das Gefecht haelt eine Leitung offen und darf darum nie anhalten,
    # auch nicht, wenn ein Menue darueber liegt: der Gastgeber wirft
    # einen Gast nach K.NETZ["stumm_nach"] Sekunden ohne Lebenszeichen
    # hinaus. Gesteuert wird trotzdem nichts - siehe `pausiert`.
    weiterlaufen = True

    def __init__(self, app, name: str, gastgeber=None, gast=None,
                 modus: str = K.MODUS_VORGABE, ende_art: str = "zeit",
                 ende_wert: float = 0.0, knapp: bool = False,
                 schutz: bool | None = None, medkits: int | None = None,
                 medkit_spawn: bool | None = None, runden: int | None = None,
                 team: int | None = None, passwort: str = "",
                 loadouts: str | None = None, rpg: bool | None = None,
                 rpg_lenkung: bool | None = None, karte: str = "",
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
        self.runden_anzahl = max(g[0], min(g[1], int(
            K.VERSUS["runden"] if runden is None else runden)))
        # Gespielte Runden, Unentschieden mitgezaehlt. Die Siege stehen in
        # teampunkte; aus ihnen allein laesst sich nicht ablesen, ob alle
        # Runden durch sind.
        self.runden_gespielt = 0
        # Gelten Loadouts? "eigenes" heisst: jeder traegt seine zwei
        # Waffen und seine Wurfwaffe. "alles" heisst: jeder hat alles, wie
        # bisher. Der Gastgeber entscheidet es, ein Gast bekommt es mit dem
        # Willkommen - zwei Leute mit verschiedenen Regeln auf derselben
        # Karte waeren kein Gefecht, sondern ein Missverstaendnis.
        self.loadout_regel = (loadouts if loadouts in K.GEFECHT["loadout_arten"]
                              else K.GEFECHT["loadouts"])
        # Der Raketenwerfer. Aus, wenn der Gastgeber ihn nicht will: er
        # veraendert eine Runde, und das soll eine Entscheidung sein.
        self.rpg_an = (K.GEFECHT["rpg"] if rpg is None else bool(rpg))
        self.rpg_lenkung = (K.GEFECHT["rpg_lenkung"] if rpg_lenkung is None
                            else bool(rpg_lenkung))
        self._rpg_takt = K.GEFECHT["rpg_takt"] * 0.4
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
        # Die Karte. Ohne Namen die eingebaute Testkarte; sonst eine
        # Datei aus `karten/`. Faellt sie aus, laeuft die Runde trotzdem -
        # eine fehlende Kartendatei darf kein Gefecht verhindern.
        self.karte = ""
        self.karte_kopf: dict = {}
        self.welt = None
        if karte:
            gelesen, kopf = welt_modul.karte_lesen(karte)
            if gelesen is not None:
                self.welt, self.karte, self.karte_kopf = gelesen, karte, kopf
        if self.welt is None:
            self.welt = testkarte()
        # Feste Einstiegsseite je Mannschaft. Wird vor dem ersten Einstieg
        # gewaehlt und gilt die ganze Runde (siehe _einstiegszonen_waehlen).
        self.einstiegszonen: list = []
        self.kamera = Kamera()
        self.kaempfer: dict[int, Kaempfer] = {}
        self.gegnerlast: dict[int, int] = {}
        self.teampunkte = [0] * len(K.TEAMS["namen"])
        self.zone_stand = [0.0] * len(K.TEAMS["namen"])
        self.zone_mitte = pygame.Vector2(0, 0)
        self.zone_ebene = K.ZONE["ebene"]
        self.zone_name = ""
        self.zone_halter = -1        # wer den Kreis gerade haelt, -1 = niemand
        self.runde = 0               # in versus: welche Runde laeuft
        self.runde_sieger = -1       # wer die letzte Runde geholt hat
        self.runden_pause = 0.0
        self.sieger_team = -1
        self.rest = self.ende_wert if self.ende_art == "zeit" else 0.0
        self.welle = 0
        self.pause_rest = K.WELLEN_MP["pause"]
        self.gegner_offen: list = []
        # Was von der laufenden Welle noch nicht losgeschickt ist, und
        # wann der naechste Schub darf. Eine Welle steht nicht mehr auf
        # einmal da, sie kommt nach.
        self.welle_rest: list[str] = []
        self.schub_rest = 0.0
        self.boss_welle = False
        self.boss = None            # der Boss dieser Welle, solange er lebt
        self.vorbei = False
        self.gewonnen = False
        self.liste: list[dict] = []
        self.hinweis = ""
        self.blick = 0
        self.blick_hoehe = 0.0
        self.blick_rest = 0.0     # so lange bleibt die Ansicht verschoben
        self.ich = None
        self.meine_nummer = 0

        # Kennung der laufenden Partie. Der Gastgeber vergibt sie am
        # Rundenende und schickt sie mit; sie ist der Schluessel, unter
        # dem alle Rechner dieselbe Runde ablegen.
        self.partie = ""
        self._gebucht = ""
        self._rundenzeit = 0.0
        self._masken_durch = False
        # Die Zahlen, aus denen die Siegtafel gebaut wird. Beim Gastgeber
        # gerechnet, beim Gast aus der Endmeldung - beide Male dieselben.
        self.endwerte: dict = {}

        self._seit_senden = 0.0
        # Was seit der letzten Meldung an Wirkung entstanden ist. Wird mit
        # der Weltmeldung verschickt und dabei geleert.
        self._wirkung: list[list] = []
        self._fremde_schuesse: list[tuple] = []
        # Uhr fuer die Zwischenlagen beim Gast. Der Gastgeber meldet
        # sechzigmal in der Sekunde, gezeichnet wird bis zu dreihundertmal
        # - dazwischen muss weitergezeichnet werden, sonst steht das Bild
        # fuenf Bilder still und springt dann. Gemessen wird der Abstand
        # zweier Meldungen, nicht angenommen: eine ueberlastete Leitung
        # meldet eben seltener, und dann soll auch langsamer ueberblendet
        # werden statt frueh anzuhalten.
        self._seit_paket = 0.0
        self._paket_takt = float(K.NETZ["takt"])
        # Roter Rand, Herzschlag, dumpfe Welt - und das Medkit dagegen.
        # Gelesen wird nur das eigene Leben; beim Gast steht es genauso in
        # der Weltmeldung wie beim Gastgeber in seiner eigenen Figur.
        self.befinden = Befinden()
        self._leben_vorher = 0.0
        self._heilte = 0.0
        self._fremde_beute: list[tuple] = []
        self._fremde_gegner: list[tuple] = []
        self._in_wirkung = False      # siehe NETZKLAENGE
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
        self.kreise = self._kreise_lesen()
        # Spawnmarken der Karte, einmal gelesen. Sie stehen dort als
        # Buchstaben, genau wie die Kreise.
        self._spawnmarken = self._spawnmarken_lesen()
        self.kreis_nr = 0
        self.kreis_rest = K.ZONE["wechsel"]
        self._kreis_setzen(0)

        self._welt_verdrahten()
        self.wunsch = self._wunsch_lesen()

        if self.ist_gastgeber:
            # Erst die Seiten festlegen, dann einsteigen - sonst hat der
            # Gastgeber keine Zone und landet irgendwo.
            self._einstiegszonen_waehlen()
            self.ich = self._dazu(0, self.name, self.team_wunsch,
                                  self.mein_loadout())
        else:
            self.gast.senden({"t": "hallo", "name": self.name,
                              "team": self.team_wunsch,
                              "wort": self.passwort,
                              # Das Loadout geht mit der Anmeldung mit. Der
                              # Gastgeber legt die Figur an, also muss er zu
                              # diesem Zeitpunkt wissen, was sie traegt.
                              "lo": self.mein_loadout()})

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

        Ruckeln und Klang haengen **nicht mehr stur** an Kamera und
        Tonausgabe. Genau das war der gemeldete Fehler: der Gastgeber
        rechnet die Welt aller Spieler, also lief bei ihm jeder Schuss
        der ganzen Runde auf seiner eigenen Kamera zusammen - gemessen
        2,09 Pixel Dauerzittern in 100 % der Bilder, waehrend der Gast
        bei 0,00 sass. Dazwischen liegt jetzt eine Rechnung, die fragt,
        ob die Meldung diesen Zuschauer ueberhaupt angeht.
        """
        self.welt.ruckeln = self._ruckeln
        self.welt.klang = self._klang
        self.welt.blutfleck = self._blutfleck
        self.welt.brandfleck = self._brandfleck
        self.welt.blitz = self._blitz
        if self.ist_gastgeber:
            # Nur beim Gastgeber: was in der Welt an Wirkung entsteht,
            # wird zusaetzlich mitgeschrieben und geht als Meldung an die
            # Gaeste, die selbst nichts rechnen. Siehe _wirkung_melden.
            self.welt.explosion = self._explosion_melden
            self.welt.schussknall = self._schussknall_melden
            self.welt.schlagknall = self._schlagknall_melden
            self.welt.raketenstart = self._raketenstart_melden

    def _blutfleck(self, pos, ebene: int, radius: float) -> None:
        self.welt.ebene(ebene).dekal(self.renderer.blutfleck(radius),
                                     pos.x, pos.y)

    def _brandfleck(self, pos, ebene: int, radius: float) -> None:
        self.welt.ebene(ebene).dekal(self.renderer.brandfleck(radius),
                                     pos.x, pos.y)

    def _blitz(self, pos, ebene: int) -> None:
        """Eine Blendgranate ist gezuendet. Blendet sie **mich**?

        Gerechnet wird hier und nicht beim Gastgeber: es ist eine Frage
        des Bildes, nicht des Spiels, und gleiche Lage ergibt auf jedem
        Rechner dieselbe Antwort. Uebertragen werden muss dafuer nichts.
        """
        staerke = welt_modul.blend_wert(pos, ebene, self.ich, self.welt)
        if staerke > 0.0:
            self.befinden.blenden(staerke)
            self.app.klaenge.spielen(K.skin("blend_pfeifen"), 0.35 + 0.5 * staerke)

    def _ruckeln(self, kraft: float, anlass: str = "", pos=None,
                 ebene: int = 0, quelle=None) -> None:
        self.kamera.stossen(welt_modul.ruckel_wert(kraft, anlass, pos, ebene,
                                                   quelle, self.ich))

    # Klaenge, die der Gastgeber an die Gaeste weiterreicht.
    #
    # Nicht alle: was in Explosion, Schuss oder Schlag steckt, kommt mit
    # deren eigener Meldung, und den Sturz baut der Gast aus der Flughoehe
    # selbst nach. Weitergereicht wird nur, was beim Gast sonst **fehlt** -
    # und das war mehr, als man denkt: die Ansage eines Bosses und den
    # Spuck des Speiers hat seit 0.26 kein Gast je gehoert.
    NETZKLAENGE = ("speien", "boss_ansage", "dash", "wurf", "medkit", "ruf")

    def _klang(self, name: str, lautstaerke: float = 1.0, pos=None,
               ebene: int | None = None) -> None:
        laut = welt_modul.klang_wert(lautstaerke, pos, ebene or 0, self.ich)
        if laut > 0.0:
            self.app.klaenge.spielen(name, laut)
        if (self.ist_gastgeber and name in self.NETZKLAENGE
                and not self._in_wirkung):
            if pos is None:
                x = y = -99999.0          # ohne Ort: ueberall gleich laut
            else:
                x, y = round(pos.x, 1), round(pos.y, 1)
            self._wirkung.append(["k", x, y, int(ebene or 0),
                                  round(float(lautstaerke), 2), str(name)])

    # ---- Wirkung, die an die Gaeste weitergeht -------------------------
    #
    # Ein Gast simuliert nichts. Bisher hiess das: er sah das Bild einer
    # Granate fliegen, und dann war es weg - kein Knall, keine Funken,
    # kein Brandfleck. Gemessen an einer Runde ueber echte Steckdosen:
    # Gastgeber 5 Partikel und ein Ton, Gast 0 und keiner. Auch am Lauf
    # blitzte bei ihm nie etwas, und im ganzen Mehrspieler war ausser dem
    # eigenen Nachladen kein Schuss zu hoeren.
    #
    # Es fehlte schlicht der Kanal. Jetzt schreibt der Gastgeber jede
    # Wirkung mit, schickt sie mit der Weltmeldung und der Gast ruft
    # damit **dieselbe** Funktion in seiner eigenen Welt auf. Damit kann
    # das Ergebnis gar nicht auseinanderlaufen: es ist derselbe Code.

    def _explosion_melden(self, pos, ebene: int, radius: float,
                          art: str = "spreng") -> None:
        self._in_wirkung = True
        try:
            Welt.explosion(self.welt, pos, ebene, radius, art)
        finally:
            self._in_wirkung = False
        self._wirkung.append(["x", round(pos.x, 1), round(pos.y, 1),
                              int(ebene), round(radius, 1), str(art)])

    def _schussknall_melden(self, pos, winkel: float, ebene: int, waffe: str,
                            quelle=None) -> None:
        self._in_wirkung = True
        try:
            Welt.schussknall(self.welt, pos, winkel, ebene, waffe, quelle)
        finally:
            self._in_wirkung = False
        self._wirkung.append(["s", round(pos.x, 1), round(pos.y, 1),
                              int(ebene), round(winkel, 1), waffe])

    def _schlagknall_melden(self, pos, winkel: float, ebene: int,
                            getroffen: bool = False, quelle=None) -> None:
        self._in_wirkung = True
        try:
            Welt.schlagknall(self.welt, pos, winkel, ebene, getroffen, quelle)
        finally:
            self._in_wirkung = False
        self._wirkung.append(["n", round(pos.x, 1), round(pos.y, 1),
                              int(ebene), round(winkel, 1),
                              1 if getroffen else 0])

    def _raketenstart_melden(self, pos, winkel: float, ebene: int,
                             quelle=None, ziel=None) -> None:
        self._in_wirkung = True
        try:
            Welt.raketenstart(self.welt, pos, winkel, ebene, quelle, ziel)
        finally:
            self._in_wirkung = False
        self._wirkung.append(["r", round(pos.x, 1), round(pos.y, 1),
                              int(ebene), round(winkel, 1), 0])

    def _wirkung_nachspielen(self, eintraege) -> None:
        """Beim Gast: die gemeldeten Wirkungen in der eigenen Welt ausloesen.

        Der Absender ist bewusst None. Damit gilt fuer den Gast alles als
        fremd, was nicht seine eigene Figur betrifft - und die Rechnung in
        `ruckel_wert` entscheidet nach Ebene und Entfernung, ob es ihn
        angeht. Der Schuss eines Mitspielers am anderen Ende der Karte ist
        dann zu hoeren, aber ruckelt nicht.
        """
        for e in eintraege:
            if not isinstance(e, (list, tuple)) or len(e) != 6:
                continue
            try:
                art = str(e[0])
                pos = pygame.Vector2(float(e[1]), float(e[2]))
                ebene = int(e[3])
            except (TypeError, ValueError):
                continue
            if art == "x":
                try:
                    radius = float(e[4])
                except (TypeError, ValueError):
                    continue
                # Aeltere Gastgeber schicken hier noch 0 oder 1 statt
                # eines Namens. Beides soll ankommen.
                wirkung = e[5]
                if not isinstance(wirkung, str):
                    wirkung = "rauch" if wirkung else "spreng"
                self.welt.explosion(pos, ebene, radius, wirkung)
            elif art == "s":
                try:
                    winkel = float(e[4])
                except (TypeError, ValueError):
                    continue
                waffe = str(e[5])
                if waffe in K.WAFFEN:
                    self.welt.schussknall(pos, winkel, ebene, waffe)
            elif art == "n":
                try:
                    winkel = float(e[4])
                except (TypeError, ValueError):
                    continue
                self.welt.schlagknall(pos, winkel, ebene, bool(e[5]))
            elif art == "k":
                try:
                    laut = float(e[4])
                except (TypeError, ValueError):
                    continue
                name = str(e[5])
                if name not in self.NETZKLAENGE:
                    continue       # nur, was auch geschickt werden darf
                ort = None if pos.x < -9e4 else pos
                self.welt.klang(name, laut, ort, ebene)
            elif art == "r":
                try:
                    winkel = float(e[4])
                except (TypeError, ValueError):
                    continue
                self.welt.raketenstart(pos, winkel, ebene)

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
    def pausiert(self) -> bool:
        """Wird gerade nicht gespielt, obwohl die Welt weiterlaeuft?

        Zwei Faelle: das eigene Menue ist auf, oder eine andere Szene
        liegt darueber - Ausruestung, Konto. In beiden darf die Figur
        nicht laufen und nicht schiessen, sonst steht man im Menue und
        wird nebenbei erschossen, waehrend der Finger noch auf der Taste
        liegt.
        """
        if self.menue is not None:
            return True
        # Gefragt wird nach dem Stapel und nicht nach `app.oben`: in den
        # Pruefungen laeuft ein Gefecht auch mal ganz ohne Stapel, und
        # das darf es nicht laehmen.
        stapel = getattr(self.app, "stapel", [])
        return self in stapel and stapel[-1] is not self

    @property
    def mit_rpg(self) -> bool:
        return bool(self.rpg_an)

    @property
    def mit_loadouts(self) -> bool:
        return self.loadout_regel == "eigenes"

    def mein_loadout(self) -> dict | None:
        """Das eigene Loadout, oder None, wenn es keines gibt.

        Ohne Konto gibt es trotzdem eines: die Vorlagen stehen auch dem
        offen, der sich nie angemeldet hat. Ein Spiel, das ohne Anmeldung
        nur mit halber Ausruestung laeuft, waere eine Zumutung.
        """
        konto = getattr(self.app, "konto", None)
        if konto is None:
            return None
        return konto.loadout

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

    def _teams_ausgleichen(self) -> None:
        """Bringt die Mannschaften ins Gleichgewicht, ohne sie zu wuerfeln.

        **Hier lag ein Fehler, der bei vier Leuten drei in dieselbe
        Mannschaft steckte.** Der alte Weg setzte beim Rundenstart fuer
        jeden einzeln `k.team = self._team_fuer()` - und `_team_fuer`
        zaehlt die Mannschaftsgroessen aus den Werten, die *gerade* an den
        Kaempfern stehen. Waehrend der Schleife sind das teils die alten,
        teils die neuen. Aus [0,0,1,1] wurde dadurch [0,0,0,1]:

            k0: Groessen [2,2] -> kleinste ist 0 -> bleibt 0
            k1: Groessen [2,2] -> kleinste ist 0 -> bleibt 0
            k2: Groessen [2,2] -> kleinste ist 0 -> **wechselt zu 0**
            k3: Groessen [3,1] -> kleinste ist 1 -> bleibt 1

        Je nach Ausgangslage ging es gut oder nicht - genau deshalb trat
        es "manchmal" auf.

        Jetzt bleibt jede Einteilung erhalten, die der Gastgeber vorgenommen
        hat, und ausgeglichen wird nur, wenn eine Mannschaft wirklich zu
        gross ist. Verschoben werden dann die zuletzt Hinzugekommenen -
        wer schon laenger dabei ist, behaelt seine Seite.
        """
        if not self.mit_teams:
            return
        anzahl = len(K.TEAMS["namen"])
        leute = sorted(self.kaempfer.values(), key=lambda k: k.nummer)
        for k in leute:
            if not 0 <= k.team < anzahl:
                k.team = 0
        # So lange den Groessten verkleinern, bis der Unterschied hoechstens
        # eins ist. Das endet immer, weil jeder Schritt ihn verringert.
        for _ in range(len(leute) + 1):
            gruppen = [[k for k in leute if k.team == i] for i in range(anzahl)]
            groesste = max(range(anzahl), key=lambda i: len(gruppen[i]))
            kleinste = min(range(anzahl), key=lambda i: len(gruppen[i]))
            if len(gruppen[groesste]) - len(gruppen[kleinste]) <= 1:
                break
            gruppen[groesste][-1].team = kleinste

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

    def _dazu(self, nummer: int, name: str, wunsch: int = -1,
              loadout=None) -> Kaempfer:
        team = self._team_fuer(wunsch)
        pos = self._einstiegsort(team)
        k = Kaempfer(pos, 0, nummer, netz.name_saeubern(name),
                     self._fraktion_fuer(nummer, team), knapp=self.knapp,
                     team=team,
                     loadout=loadout if self.mit_loadouts else None)
        self._regeln_anlegen(k)
        k.unverwundbar = self.schutz_zeit
        k.medkits = self.start_medkits
        self.kaempfer[nummer] = k
        self.welt.dazu(k)
        return k

    def _rpg_regeln(self) -> None:
        """Jedem Kaempfer sagen, ob sein Werfer lenken darf.

        Der Gastgeber entscheidet das, nicht die Figur - sonst haette ein
        Gast mit geaenderter Datei eine Lenkung, die in dieser Runde gar
        nicht gilt.
        """
        for k in self.kaempfer.values():
            k.lenkbar = self.rpg_lenkung

    def _loadout_anlegen(self, k: Kaempfer) -> None:
        """Dem Kaempfer die Waffen geben, die gerade fuer ihn gelten.

        Ohne Loadout-Regel bekommt jeder alles zurueck - auch dann, wenn
        die Runde vorher mit Loadouts lief. Sonst liefe jemand nach einem
        Regelwechsel mit drei Plaetzen herum, waehrend alle anderen sechs
        haben.
        """
        if self.mit_loadouts:
            # Der Gastgeber kennt das Loadout jedes Gastes von dessen
            # Anmeldung; sein eigenes holt er sich frisch, damit eine
            # Aenderung im Menue ankommt.
            lo = self.mein_loadout() if k is self.ich else k.loadout
            plaetze = konto_modul.hotbar_aus_loadout(lo) if lo else []
        else:
            plaetze = list(K.HOTBAR)
        if not plaetze or plaetze == k.waffen:
            return
        k.loadout = dict(lo) if self.mit_loadouts and lo else None
        k.waffen = plaetze
        k.waffe = 0
        k.magazin = {w: K.WAFFEN[w]["magazin"] for w in plaetze}
        k.vorrat = {w: K.MUNITION["vorrat"].get(w, 0) for w in plaetze}

    def _regeln_anlegen(self, k: Kaempfer) -> None:
        """Was die Spielart am einzelnen Kaempfer aendert."""
        k.revive_an = self.regeln["revive"]
        if self.regeln["runden"]:
            k.boden_zeit = K.VERSUS["boden_zeit"]
            k.revive_dauer = K.VERSUS["revive_dauer"]

    def _einstiegszonen_waehlen(self) -> None:
        """Legt fuer jede Mannschaft **eine** Seite der Karte fest.

        Vorher suchte jeder Einstieg neu nach "weit weg von den Gegnern,
        nahe bei den eigenen". Das ergab von Runde zu Runde andere Seiten,
        und mitten in der Runde wanderten die Mannschaften ueber die Karte,
        weil sich die Lage der Lebenden staendig aendert.

        Jetzt werden einmal je Runde zwei Ankerpunkte gesucht, die so weit
        wie moeglich auseinanderliegen, und jede Mannschaft bekommt einen.
        Der gilt die ganze Runde. Man weiss dadurch, wo die eigenen Leute
        einsteigen und aus welcher Richtung die anderen kommen - und genau
        das macht eine Karte lesbar.
        """
        anzahl = len(K.TEAMS["namen"])
        self.einstiegszonen = []
        if not self.mit_teams:
            return
        # Kandidaten sammeln und das Paar mit dem groessten Abstand nehmen.
        punkte = [freier_punkt(self.welt, 0, self.rnd)
                  for _ in range(K.GEFECHT["zonen_proben"])]
        beste, bester_wert = None, -1.0
        for i, a in enumerate(punkte):
            for b in punkte[i + 1:]:
                d = a.distance_squared_to(b)
                if d > bester_wert:
                    beste, bester_wert = (a, b), d
        if beste is None:
            beste = (freier_punkt(self.welt, 0, self.rnd),
                     freier_punkt(self.welt, 0, self.rnd))
        for i in range(anzahl):
            self.einstiegszonen.append(pygame.Vector2(beste[i % 2]))

    def _einstiegsort(self, team: int = -1, ausser=None) -> pygame.Vector2:
        """Ein freier Platz zum Einsteigen.

        `ausser` ist der Kaempfer, der gerade eingesetzt wird. Er muss
        heraus, und das war ein echter Fehler: beim Rundenstart wird
        `lebt` gesetzt, *bevor* der Platz gesucht wird. Der Gastgeber zaehlte
        sich dadurch selbst zu den "eigenen Leuten", in deren Naehe man
        einsteigen soll - und stand prompt wieder da, wo er in der Runde
        davor gestanden hatte.

        Mit Mannschaften wird in der Zone der eigenen Mannschaft gesucht
        (siehe `_einstiegszonen_waehlen`), sonst einfach weit weg von allen
        anderen.
        """
        eigene = [k.pos for k in self.kaempfer.values()
                  if k.lebt and k is not ausser and team >= 0 and k.team == team]
        fremde = [k.pos for k in self.kaempfer.values()
                  if k.lebt and k is not ausser and (team < 0 or k.team != team)]
        anker = None
        if self.mit_teams and 0 <= team < len(self.einstiegszonen):
            anker = self.einstiegszonen[team]

        bester, bester_wert = None, -1e18
        for _ in range(K.NETZ["hoechstens"] * 6):
            p = freier_punkt(self.welt, 0, self.rnd)
            zu_fremd = min((p.distance_to(q) for q in fremde), default=9999.0)
            if not self.mit_teams:
                if zu_fremd > K.GEFECHT["abstand"]:
                    return p
                continue
            zu_eigen = min((p.distance_to(q) for q in eigene), default=0.0)
            # Die eigene Zone zaehlt am meisten - sie haelt die Seite fest.
            # Abstand zu den Gegnern und Naehe zu den eigenen Leuten
            # entscheiden nur noch darueber, wo *innerhalb* der Zone.
            zur_zone = p.distance_to(anker) if anker is not None else 0.0
            wert = (-zur_zone * K.GEFECHT["zonen_zug"]
                    + zu_fremd * 0.35 - zu_eigen * 0.2)
            if wert > bester_wert:
                bester, bester_wert = p, wert
        return bester if bester is not None else freier_punkt(self.welt, 0, self.rnd)

    # ---- Eingabe ------------------------------------------------------
    # Einmalige Tastendruecke - Nachladen, Medkit, Zielhilfe, Waffenwahl -
    # werden **beim Ereignis** aufgehoben und nicht im Zeitschritt.
    #
    # Das ist kein Stil, das behebt einen Fehler. Die Ereignisschleife
    # laeuft je Bild und loescht dabei alles, was "gerade gedrueckt" ist.
    # Der Zeitschritt laeuft aber nur, wenn genug Zeit aufgelaufen ist -
    # bei 120 Schritten je Sekunde und unbegrenzter Bildrate gibt es reihum
    # Bilder ganz ohne Schritt. Wer in einem solchen Bild eine Taste
    # drueckt, dessen Druck sieht der Zeitschritt nie.
    #
    # Gemessen, mit der Schleife aus core.laufen:
    #
    #      60 Bilder/s    0 Prozent der Bilder ohne Schritt
    #     144 Bilder/s   17 Prozent
    #     300 Bilder/s   60 Prozent
    #
    # Und die Bildrate ist am Anfang einer Runde am hoechsten, weil noch
    # wenig auf der Karte steht. Genau deshalb ging Z "bei den ersten paar
    # Klicks" nicht - und Nachladen und Waffenwechsel ebenso, nur faellt es
    # dort weniger auf, weil man es sofort noch einmal drueckt.

    # Tasten, die als einzelner Druck zum Gastgeber gehen. An einer
    # Stelle, weil es sie zweimal braucht (Ereignis und Rueckfallebene) -
    # und eine Taste, die in der einen Liste steht und in der anderen
    # fehlt, geht genau dann nicht, wenn es darauf ankommt.
    DRUECKE = ("nachladen", "heilen", "tracer", "tracer_weit",
               "nahkampf", "feuermodus", "dash")

    def _knopf_merken(self, taste) -> None:
        """Einen Tastendruck aufheben, bis das naechste Paket rausgeht."""
        tabelle = self.app.eingabe.tabelle
        for name in self.DRUECKE:
            if taste in tabelle.get(name, ()):
                self._knoepfe.add(name)
        # Am Boden ist "benutzen" ein Ruf. Als Druck geschickt, nicht als
        # gehaltener Zustand: ein Ruf ist ein Ereignis, und der Gastgeber
        # entscheidet, ob er gerade zaehlt.
        if taste in tabelle.get("nutzen", ()):
            self._knoepfe.add("rufen")
        for nr in range(1, K.HOTBAR_PLAETZE + 1):
            if taste in tabelle.get("waffe%d" % nr, ()):
                self._waffe_wunsch = nr - 1

    def knoepfe_sammeln(self) -> None:
        """Bleibt als Rueckfallebene fuer Tasten, die kein Ereignis erzeugen.

        Die Maustasten kommen weiterhin ueber `gehalten()` und brauchen das
        hier nicht; was hier steht, faengt nur den Fall ab, dass eine
        Belegung ohne Tastencode auskommt.
        """
        e = self.app.eingabe
        for name in self.DRUECKE:
            if e.gedrueckt(name):
                self._knoepfe.add(name)
        if e.gedrueckt("nutzen"):
            self._knoepfe.add("rufen")
        for nr in range(1, K.HOTBAR_PLAETZE + 1):
            if e.gedrueckt("waffe%d" % nr):
                self._waffe_wunsch = nr - 1

    def _meine_eingabe(self) -> dict:
        e = self.app.eingabe
        ziel = self.kamera.zu_welt(e.maus)
        offen = self.pausiert
        meldung = {
            "t": "ein",
            "will": [0.0, 0.0] if offen else [round(v, 2) for v in e.richtung()],
            "ziel": [round(ziel.x, 1), round(ziel.y, 1)],
            "feuert": False if offen else e.gehalten("feuer"),
            "zielt": False if offen else e.gehalten("zweit"),
            # Nutzen wird gehalten, nicht gedrueckt: Treppe und Aufhelfen
            # haengen beide daran, und Aufhelfen braucht Zeit.
            "nutzen": False if offen else e.gehalten("nutzen"),
            "ziehen": False if offen else e.gehalten("ziehen"),
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
            k.hilft = None
            k.zieht = None
            # Das Einzige, was man am Boden noch tun kann: rufen.
            knoepfe = ein.get("knoepfe") or []
            if isinstance(knoepfe, list) and "rufen" in knoepfe:
                self._rufen(k)
            return

        waffe = ein.get("waffe", -1)
        if isinstance(waffe, int) and 0 <= waffe < len(k.waffen):
            # Vor allem anderen und durch nichts zu sperren: die Waffe
            # laesst sich immer wechseln, auch beim Helfen.
            k.waffe_waehlen(waffe)

        k.will = will
        # Waehrend des Schwungs ist die Waffe verstaut - dann wird auch
        # nicht geschossen. Sonst schluege man mit dem Eisen und feuerte
        # zugleich eine Waffe ab, die man gar nicht in der Hand hat.
        k.feuert = bool(ein.get("feuert")) and not (
            K.NAHKAMPF["sperrt_feuer"] and k.schwingt)
        k.zielt = bool(ein.get("zielt"))

        knoepfe = ein.get("knoepfe") or []
        if isinstance(knoepfe, list):
            if "nachladen" in knoepfe:
                k.nachladen()
            if "dash" in knoepfe:
                k.dashen()
            if "heilen" in knoepfe:
                k.heilen()
            if "tracer" in knoepfe:
                k.tracer = not k.tracer
            if "tracer_weit" in knoepfe:
                k.tracer_weit = not k.tracer_weit
            if "feuermodus" in knoepfe:
                # Die Betriebsart gehoert zur Figur und damit zum
                # Gastgeber - sonst schoesse der Gast im Dauerfeuer,
                # waehrend der Gastgeber eine Salve rechnet.
                k.modus_wechseln()
            if "nahkampf" in knoepfe:
                # Das Brecheisen liegt auf einer eigenen Taste und braucht
                # keinen Waffenwechsel. Es schlaegt mit seinen eigenen
                # Werten, egal was gerade in der Hand ist.
                if k.nahkampf():
                    self.welt.klang("nahkampf", 0.9)

        # Ziehen: gehalten, und solange es laeuft, gibt es nichts anderes.
        # Kein Schiessen und kein Aufhelfen - wer beide Haende an einem
        # Gefallenen hat, hat keine frei. Das ist der Preis dafuer, ihn aus
        # der Schusslinie holen zu koennen.
        k.hilft = None
        if ein.get("ziehen"):
            opfer = (self.kaempfer.get(k.zieht) if k.zieht is not None
                     else self._wen_ziehen(k))
            if opfer is not None and self._ziehen_moeglich(k, opfer):
                k.zieht = opfer.nummer
                opfer.gezogen_von = k.nummer
                k.feuert = False
                k.zielt = False
                return
        self._loslassen(k)

        # Nutzen: erst jemandem aufhelfen, sonst die Treppe nehmen.
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
        # Wer selbst liegt, hilft niemandem auf. Die Pruefung fehlte hier,
        # und darum stand bei einem Gefallenen neben einem anderen
        # Gefallenen "[E]" - als koenne er ihn aufheben. Die Handlung selbst
        # war woanders schon gesperrt, der Hinweis nicht; jetzt sagen beide
        # dasselbe, weil beide hier fragen.
        if not helfer.lebt or getattr(helfer, "am_boden", False):
            return False
        if helfer is liegender:
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

    # ---- Ziehen ---------------------------------------------------------
    def _wen_ziehen(self, k: Kaempfer):
        """Wer sich ziehen laesst: dieselben Regeln wie beim Aufhelfen.

        Aus demselben Grund: wer einen Gefallenen aufheben duerfte, darf
        ihn auch aus der Schusslinie holen - und den Gegner, den man
        gerade umgelegt hat, darf man in beiden Faellen nicht anfassen.
        Wer schon gezogen wird, faellt raus: zu zweit an einem zu zerren,
        ergaebe einen Koerper, der zwischen zwei Leuten zittert.
        """
        if not self.regeln["revive"]:
            return None
        naechster, beste = None, K.REVIVE["reichweite"]
        for anderer in self.kaempfer.values():
            if not self._ziehen_moeglich(k, anderer):
                continue
            if anderer.gezogen_von not in (None, k.nummer):
                continue
            d = k.pos.distance_to(anderer.pos)
            if d <= beste:
                naechster, beste = anderer, d
        return naechster

    def _ziehen_moeglich(self, k, opfer) -> bool:
        if opfer is None or opfer is k:
            return False
        if not (opfer.lebt and opfer.am_boden):
            return False
        if opfer.ebene != k.ebene or not self._darf_helfen(k, opfer):
            return False
        return k.pos.distance_to(opfer.pos) <= K.ZIEHEN["reisst"]

    def _loslassen(self, k: Kaempfer) -> None:
        if k.zieht is None:
            return
        opfer = self.kaempfer.get(k.zieht)
        if opfer is not None and opfer.gezogen_von == k.nummer:
            opfer.gezogen_von = None
        k.zieht = None

    def _ziehen(self, dt: float) -> None:
        """Gezogene folgen an einer kurzen Leine hinter dem Ziehenden.

        Die Figur wird verschoben, nicht gedreht - sie liegt, wie sie
        gefallen ist. Und sie wird nur dorthin gesetzt, wo Boden ist: ein
        Gefallener, den man ueber eine Kante zieht, soll nicht in die
        Tiefe fallen, sondern am Rand haengen bleiben.
        """
        for k in self.kaempfer.values():
            if k.zieht is None:
                continue
            opfer = self.kaempfer.get(k.zieht)
            if (opfer is None or not k.lebt or k.am_boden
                    or not self._ziehen_moeglich(k, opfer)):
                self._loslassen(k)
                continue
            weg = opfer.pos - k.pos
            if weg.length_squared() < 0.01:
                weg = pygame.Vector2(-1, 0)
            ziel = k.pos + weg.normalize() * K.ZIEHEN["leine"]
            schritt = ziel - opfer.pos
            if schritt.length_squared() < 0.04:
                continue
            neu = opfer.pos + schritt
            if self.welt.frei(neu, opfer.radius * 0.8, opfer.ebene, True):
                opfer.vorher.update(opfer.pos)
                opfer.pos.update(neu)

    # ---- Rufen am Boden ---------------------------------------------------
    def _rufen(self, k: Kaempfer) -> None:
        """Ein Gefallener macht auf sich aufmerksam. Hoechstens alle 1,5 s."""
        if not k.am_boden or k.ruf_sperre > 0.0:
            return
        k.ruf_sperre = K.RUFEN["sperre"]
        k.ruf_zeigen = K.RUFEN["zeigen"]
        self.welt.klang("ruf", 0.8, k.pos, k.ebene)

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
                                   wunsch,
                                   konto_modul.loadout_saeubern(
                                       nachricht.get("lo")))
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
        self._rpg_regeln()
        self.welt.schritt(dt)
        self._ziehen(dt)
        self._revive(dt)
        self._tote_abrechnen(dt)
        self._ende_pruefen(dt)

        self._seit_senden += dt
        if self._seit_senden >= K.NETZ["takt"]:
            # Abgezogen, nicht auf null gesetzt: sonst geht bei jedem
            # Senden der Rest verloren, und der tatsaechliche Takt haengt
            # davon ab, wie das Bildmass zum Netztakt passt. Bei 1/120 zu
            # 1/60 ginge es gerade auf, bei jedem anderen Verhaeltnis
            # schleicht sich ein Fehler ein, der die Meldungen ungleich
            # verteilt - und ungleich verteilte Meldungen sehen aus wie
            # springende Granaten.
            self._seit_senden -= K.NETZ["takt"]
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
                "runden": self.runden_anzahl,
                "loadouts": self.loadout_regel,
                "rpg": self.rpg_an, "rpg_lenkung": self.rpg_lenkung,
                "karte": self.karte}

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
        if self.boss is not None and not self.boss.lebt:
            self.boss = None
        # Erst nachschieben, was von der Welle noch aussteht.
        if self.welle_rest:
            self._nachschub(dt)
            return
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

        self.boss_welle = (self.welle >= w["boss_ab"]
                           and self.welle % w["boss_alle"] == 0)
        if self.boss_welle:
            # In einer Bosswelle kommt weniger Fussvolk. Der Boss ist die
            # Aufgabe; ein volles Rudel daneben macht ihn nicht schwerer,
            # sondern nur unuebersichtlich.
            anzahl = max(1, int(anzahl * w["boss_begleitung"]))
            self._boss_setzen(lebende)

        # Der Bauplan der Welle, einmal gezogen und dann abgearbeitet.
        # Vorher gezogen und nicht Stueck fuer Stueck, damit die Mischung
        # stimmt: wer je Gegner wuerfelt, bekommt bei sechs Gegnern mit
        # etwas Pech sechsmal dasselbe.
        self.welle_rest = self._welle_bauen(anzahl)
        self.schub_rest = 0.0
        self._nachschub(0.0)

    def _welle_bauen(self, anzahl: int) -> list[str]:
        """Woraus die Welle besteht - als Liste von Gegnerarten.

        Gezogen wird nach Gewichten aus `K.MISCHUNG`, die sich mit der
        Wellennummer verschieben. Der Laeufer hat ein fallendes Gewicht:
        er verschwindet nicht, aber er macht Platz. Ohne die Untergrenze
        `mindestens` waere er ab Welle 15 ganz weg, und dann besteht eine
        Welle nur noch aus Sonderfaellen - was ermuedet, weil nichts mehr
        gewoehnlich ist.
        """
        offen = []
        for e in K.MISCHUNG:
            if self.welle < e["ab"]:
                continue
            g = e["gewicht"] + e.get("steigt", 0.0) * (self.welle - e["ab"])
            g = max(e.get("mindestens", 0.0), g)
            if g > 0:
                offen.append((e["art"], g))
        if not offen:
            offen = [("laeufer", 1.0)]
        summe = sum(g for _a, g in offen)
        raus = []
        for _ in range(anzahl):
            wurf = self.rnd.uniform(0.0, summe)
            for art, g in offen:
                wurf -= g
                if wurf <= 0:
                    raus.append(art)
                    break
            else:
                raus.append(offen[0][0])
        return raus

    def _boss_setzen(self, lebende: int) -> None:
        """Den Boss dieser Welle aufstellen.

        Sein Leben waechst mit der Zahl der Spieler und mit der Zahl der
        Bosse, die schon lagen. Beides ist noetig: zu viert faellt ein
        fester Boss in Sekunden, und der dritte Koloss darf nicht
        derselbe sein wie der erste.
        """
        w = K.WELLEN_MP
        nummer = self.welle // w["boss_alle"]          # 1, 2, 3, ...
        art = K.BOSS_FOLGE[(nummer - 1) % len(K.BOSS_FOLGE)]
        leben = (K.BOSSE[art]["leben"]
                 * (1.0 + w["boss_leben_je_spieler"] * (lebende - 1))
                 * (1.0 + w["boss_leben_je_runde"] * (nummer - 1)))
        ebene, pos = self._spawnstelle(boss=True)
        g = KampfGegner(pos, art, ebene, self, leben=leben)
        self.gegner_offen.append(g)
        self.welt.dazu(g)
        self.boss = g
        self.hinweis = "%s" % K.BOSSE[art]["name"]
        self.welt.klang("boss_ansage", 1.0)

    def _nachschub(self, dt: float) -> None:
        """Den naechsten Schub losschicken, wenn Platz und Zeit da sind.

        Zwei Bremsen: `gleichzeitig` haelt die Zahl der Gegner auf der
        Karte im Rahmen (sonst faellt die Bildrate, und eine Welle, die
        ruckelt, ist keine Herausforderung, sondern ein Aergernis), und
        `schub_pause` gibt dem Rudel Zeit anzukommen, bevor das naechste
        losgeht. Kleine Wellen kommen weiter auf einmal - bei sechs
        Gegnern ist ein Nachschub nur eine Verzoegerung.
        """
        if not self.welle_rest:
            return
        w = K.WELLEN_MP
        self.schub_rest = max(0.0, self.schub_rest - dt)
        lebende = sum(1 for g in self.gegner_offen if g.lebt)
        auf_einmal = len(self.welle_rest) + lebende < w["schub_ab"]
        if not auf_einmal:
            if self.schub_rest > 0.0 or lebende >= w["gleichzeitig"]:
                return
        wie_viele = len(self.welle_rest) if auf_einmal else min(
            w["schub"], len(self.welle_rest), w["gleichzeitig"] - lebende)
        for _ in range(max(0, wie_viele)):
            art = self.welle_rest.pop()
            ebene, pos = self._spawnstelle()
            g = KampfGegner(pos, art, ebene, self)
            self.gegner_offen.append(g)
            self.welt.dazu(g)
        self.schub_rest = w["schub_pause"]

    # ---- Wo Gegner auftauchen -------------------------------------------
    def _spawnstelle(self, boss: bool = False):
        """Eine Stelle im Band um die Spieler. Gibt (Ebene, Punkt).

        Vier Regeln, in dieser Reihenfolge:

        1. **Bei jemandem.** Gewuerfelt wird um einen lebenden Spieler
           herum, nicht ueber der Karte. Auf STAUBTAL war der Unterschied
           gemessen 1477 gegen jetzt rund 400 Pixel - also zwanzig
           Sekunden Fussmarsch gegen fuenf.
        2. **Nicht zu nah und nicht zu weit.** Zwischen `nah` und `weit`.
           Naeher waere ein Gegner, der aus dem Nichts im Ruecken steht;
           weiter waere wieder Fussmarsch.
        3. **Moeglichst ausser Sicht.** Es soll niemand vor den Augen
           entstehen. Geht das nicht - auf offenem Sand geht es oft
           nicht -, dann eben im Blickfeld; das ist besser als gar kein
           Gegner oder einer am anderen Ende der Karte.
        4. **Auf der Ebene des Spielers**, fast immer. Auf STAUBTAL sind
           die oberen Ebenen Plateaus, auf die nur Rampen fuehren - wer
           dort oben entsteht, waehrend unten gekaempft wird, kommt nie
           an. Frueher landeten dort vier von sechs.

        Findet sich gar nichts, bleibt es beim alten Verfahren. Lieber
        ein Gegner an einer maessigen Stelle als keiner.
        """
        s = K.SPAWN
        anker = [k for k in self.kaempfer.values() if k.lebt]
        if not anker:
            ebene = self.rnd.randrange(len(self.welt.ebenen))
            return ebene, freier_punkt(self.welt, ebene, self.rnd)
        wer = self.rnd.choice(anker)
        weit = s["weit_boss"] if boss else s["weit"]

        # Kartenmarken zuerst: wer eine Karte baut, soll sagen duerfen,
        # wo die Dinger herkommen. Sie gelten aber nur, wenn sie auch in
        # der Naehe liegen - sonst waere es wieder ein Fussmarsch.
        marke = self._spawnmarke(wer, weit * s["marke_band"], anker)
        if marke is not None and self.rnd.random() < s["marke_anteil"]:
            return marke

        ebene = wer.ebene
        if self.rnd.random() > s["eigene_ebene"] and len(self.welt.ebenen) > 1:
            ebene = self.rnd.randrange(len(self.welt.ebenen))
        bester = None
        for versuch in range(s["versuche"]):
            winkel = self.rnd.uniform(0.0, 360.0)
            abstand = self.rnd.uniform(s["nah"], weit)
            p = wer.pos + pygame.Vector2(abstand, 0).rotate(winkel)
            e = self.welt.ebene(ebene)
            if not (8 < p.x < e.pixel_breite - 8 and 8 < p.y < e.pixel_hoehe - 8):
                continue
            if not self.welt.frei(p, 14, ebene):
                continue
            # Der Abstand gilt gegen **jeden** Spieler, nicht nur gegen
            # den gewuerfelten. Stand hier einmal nur `wer`, und prompt
            # entstand auf der kleinen Testkarte ein Gegner 137 Pixel
            # neben dem zweiten Mann - die Spieler stehen dort naeher
            # beieinander als das Band breit ist.
            if self._zu_nah(p, ebene, anker):
                continue
            if bester is None:
                bester = p
            # Ausser Sicht ist besser, aber nur so lange gesucht, wie es
            # sich lohnt - danach zaehlt die erste brauchbare Stelle.
            if versuch < s["verdeckt_versuche"]:
                if ebene == wer.ebene and self.welt.sicht_frei(p, wer.pos, ebene):
                    continue
            return ebene, p
        if bester is not None:
            return ebene, bester
        # Nichts gefunden: dann wenigstens irgendwo mit Abstand. Die
        # kleine Testkarte ist klein genug, dass das vorkommt.
        for _ in range(20):
            p = freier_punkt(self.welt, ebene, self.rnd)
            if not self._zu_nah(p, ebene, anker):
                return ebene, p
        return ebene, freier_punkt(self.welt, ebene, self.rnd)

    def _zu_nah(self, punkt, ebene: int, anker) -> bool:
        """Steht diese Stelle jemandem im Gesicht? Auf seiner Ebene."""
        nah = K.SPAWN["nah"]
        return any(k.ebene == ebene and punkt.distance_to(k.pos) < nah
                   for k in anker)

    def _spawnmarke(self, wer, hoechstens: float, anker):
        """Eine Spawnmarke aus der Karte, die nah genug liegt.

        Die Marken stehen als Buchstaben in der Kartendatei, genau wie
        die Kreise - wer eine Karte baut, setzt ein Z hin und ist fertig.
        """
        if not self._spawnmarken:
            return None
        # Dieselbe Untergrenze wie beim Ring. Stand hier einmal die
        # Haelfte davon, und prompt entstand auf der Testkarte ein
        # Gegner 105 Pixel neben einem Spieler - eine Marke darf naeher
        # liegen als der Ring wuerfelt, aber nicht im Gesicht.
        nah = K.SPAWN["nah"]
        passend = [(e, p) for (e, p) in self._spawnmarken
                   if e == wer.ebene
                   and nah < p.distance_to(wer.pos) <= hoechstens
                   and not self._zu_nah(p, e, anker)]
        if not passend:
            return None
        ebene, punkt = self.rnd.choice(passend)
        # Etwas streuen, damit nicht alle auf demselben Pixel stehen.
        for _ in range(8):
            p = punkt + pygame.Vector2(self.rnd.uniform(-34, 34),
                                       self.rnd.uniform(-34, 34))
            if self._zu_nah(p, ebene, anker):
                continue          # die Streuung darf die Grenze nicht reissen
            if self.welt.frei(p, 14, ebene):
                return ebene, p
        return ebene, punkt

    def _spawnmarken_lesen(self) -> list:
        """Alle Spawnmarken der Karte: [(Ebene, Punkt), ...]."""
        raus = []
        for buchstabe in str(K.SPAWN["marken"]):
            for i, e in enumerate(self.welt.ebenen):
                for punkt in e.marken.get(buchstabe, ()):
                    raus.append((i, pygame.Vector2(punkt)))
        return raus

    # ---- Der Kreis in der Mitte -----------------------------------------
    def in_der_zone(self, k) -> bool:
        """Steht dieser Kaempfer im Kreis? Nur auf der richtigen Ebene."""
        if not k.lebt or k.am_boden:
            return False
        # Die Ebene kommt aus der Karte und nicht mehr fest aus der
        # Tabelle: auf STAUBTAL liegt einer der Kreise auf einem Plateau.
        if k.ebene != self.zone_ebene:
            return False
        return k.pos.distance_to(self.zone_mitte) <= K.ZONE["radius"]

    def _kreise_lesen(self) -> list[tuple]:
        """Wo die Kreise dieser Karte liegen: [(Ebene, Punkt, Name), ...].

        Sie stehen als Marken **in der Kartendatei**, nicht in einer
        Tabelle daneben: wer eine Karte baut, setzt dort ein A, ein B und
        ein C hin und ist fertig. Der Kopf sagt nur, welche Buchstaben
        Kreise sind und wie sie heissen.

        Hat eine Karte keine Marken, bleibt es bei der Mitte - so wie
        bisher und wie bei der Testkarte.
        """
        namen = str(self.karte_kopf.get("kreise", "")).split()
        raus = []
        for buchstabe in namen:
            for i, e in enumerate(self.welt.ebenen):
                for punkt in e.marken.get(buchstabe, ()):
                    raus.append((i, pygame.Vector2(punkt), buchstabe))
        if raus:
            return raus
        e = self.welt.ebene(min(K.ZONE["ebene"], len(self.welt.ebenen) - 1))
        return [(e.index, pygame.Vector2(e.pixel_breite / 2,
                                         e.pixel_hoehe / 2), "")]

    def _kreis_setzen(self, nr: int) -> None:
        nr = nr % max(1, len(self.kreise))
        self.kreis_nr = nr
        ebene, punkt, name = self.kreise[nr]
        self.zone_ebene = ebene
        self.zone_mitte.update(punkt)
        self.zone_name = name

    def _kreis_wandern(self, dt: float) -> None:
        """Bei mehreren Kreisen wandert er weiter.

        Eine sehr grosse Karte mit drei Kreisen zugleich ist keine grosse
        Karte, sondern drei kleine: die Mannschaften teilen sich auf und
        treffen sich nie. Ein Kreis, der weiterzieht, haelt sie beisammen
        und macht die Groesse trotzdem nutzbar - man muss den Weg gehen.
        """
        if len(self.kreise) < 2:
            return
        self.kreis_rest -= dt
        if self.kreis_rest > 0:
            return
        self.kreis_rest = K.ZONE["wechsel"]
        self._kreis_setzen(self.kreis_nr + 1)
        self.hinweis = "DER KREIS ZIEHT WEITER"
        self.welt.klang("erfasst", 0.5)

    def _zone(self, dt: float) -> None:
        """Wer die Mehrheit im Kreis hat, laedt fuer sein Team.

        Bei Gleichstand passiert nichts - auch nicht, wenn beide viele
        Leute drin haben. Das macht den Kreis zum Ort, an dem man sich
        trifft, statt ihn abwechselnd leerzuraeumen: wer allein hineinlaeuft
        laedt schnell, wer auf Widerstand trifft muss ihn erst wegraeumen.
        """
        if not self.regeln["zone"]:
            return
        self._kreis_wandern(dt)
        z = K.ZONE
        drin = [0] * len(self.teampunkte)
        for k in self.kaempfer.values():
            if 0 <= k.team < len(drin) and self.in_der_zone(k):
                drin[k.team] += 1
                # Die Zeit im Kreis zaehlt fuer jeden, der drin steht -
                # auch dann, wenn seine Mannschaft gerade nichts laedt.
                # Dagestanden hat er trotzdem.
                k.zaehlen("zonenzeit", dt)

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

        # Wer zaehlt als "steht noch"? Nur, wer auf den Beinen ist.
        #
        # Bis 0.26 zaehlte auch, wer am Boden lag - "solange jemand
        # aufhelfen kann, ist die Runde nicht entschieden". Nur konnte, wer
        # am Boden lag, selbst niemandem aufhelfen. Lagen alle einer
        # Mannschaft, war die Runde also laengst entschieden, aber sie
        # lief weiter, bis der Bodentimer jedes einzelnen abgelaufen war:
        # zwanzig Sekunden Warten auf einen Sieg, der schon feststand.
        # Gemeldet als "man gewinnt erst, wenn man die Timer abwartet".
        steht = [0] * len(self.teampunkte)
        for k in self.kaempfer.values():
            if (0 <= k.team < len(steht) and k.lebt and not k.raus
                    and not k.am_boden):
                steht[k.team] += 1
        leer = [i for i, n in enumerate(steht) if n == 0]
        if not leer:
            return
        self.runden_gespielt += 1
        self.runden_pause = K.VERSUS["pause"]
        if len(leer) < len(steht):
            sieger = [i for i in range(len(steht)) if i not in leer]
            if len(sieger) == 1:
                self.teampunkte[sieger[0]] += 1
                self.runde_sieger = sieger[0]
        else:
            # Alle gleichzeitig hin: niemand bekommt den Punkt, aber die
            # Runde ist gespielt.
            self.runde_sieger = -1
        entschieden = self._match_sieger()
        if entschieden >= 0:
            self.sieger_team = entschieden
            self._runde_beenden(gewonnen=True)

    def _match_sieger(self) -> int:
        """Wer das Match gewonnen hat, oder -1, wenn es weitergeht.

        Zwei Wege zum Sieg: nicht mehr einzuholen sein, oder nach allen
        Runden vorne liegen. Steht es danach gleich, geht es weiter - jede
        weitere Runde ist dann Matchpoint.
        """
        punkte = self.teampunkte
        if len(punkte) < 2:
            return -1
        rest = max(0, self.runden_anzahl - self.runden_gespielt)
        for i, p in enumerate(punkte):
            andere = max(q for j, q in enumerate(punkte) if j != i)
            if p > andere + rest:
                return i
        return -1

    @property
    def matchpoint(self) -> bool:
        """Alle Runden gespielt und Gleichstand: die naechste entscheidet."""
        return (self.regeln["runden"]
                and self.runden_gespielt >= self.runden_anzahl
                and len(set(self.teampunkte)) == 1)

    def runden_text(self) -> str:
        if self.matchpoint:
            return "MATCHPOINT  %s" % ":".join(str(p) for p in self.teampunkte)
        runde = min(self.runden_gespielt + 1, self.runden_anzahl)
        return "RUNDE %d VON %d" % (runde, self.runden_anzahl)

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
        # Neue Runde, neue Seiten - aber innerhalb der Runde bleiben sie.
        self._einstiegszonen_waehlen()
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
        if self.mit_rpg:
            # Vor der Munition und nicht danach: der Zweig darunter steigt
            # bei nicht-knapper Munition sofort aus, und dann laege nie
            # ein Werfer auf der Karte.
            self._rpg_takt -= dt
            if self._rpg_takt <= 0.0:
                self._rpg_takt = K.GEFECHT["rpg_takt"]
                # **Einer**. Weder liegen zwei herum, noch bekommt einer
                # den zweiten, waehrend er den ersten noch traegt.
                traegt = any(getattr(k, "rpg", False)
                             for k in self.kaempfer.values())
                if not traegt:
                    self._beute_legen("rakete", 1)
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
                    self.welt.klang("medkit", 0.7, k.pos, k.ebene)
                    # Aufhelfen zaehlt bei denen, die geholfen haben, nicht
                    # bei dem, dem geholfen wurde.
                    for helfer_k in self.kaempfer.values():
                        if helfer_k.hilft == k.nummer:
                            helfer_k.zaehlen("hilfen")
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
                    toeter.opfer[k.nummer] = toeter.opfer.get(k.nummer, 0) + 1
                    toeter.serie += 1
                    toeter.zaehler["serie"] = max(
                        toeter.zaehler.get("serie", 0), toeter.serie)
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
                k.serie = 0          # der eigene Tod beendet die Folge
                k.wieder_in = K.GEFECHT["wieder_nach"]
            if self.regeln["runden"]:
                k.raus = True     # in versus bleibt man bis zur naechsten Runde
                continue
            if self.regeln["revive"]:
                continue          # in pve steigt niemand von selbst wieder ein
            k.wieder_in -= dt
            if k.wieder_in <= 0 and not self.vorbei:
                self._wieder_einsteigen(k)

    def _magazine_fuellen(self, k: Kaempfer) -> None:
        """Magazine beim Einstieg auffuellen.

        Ohne knappe Munition wie immer: alles randvoll, umsonst.

        **Mit knapper Munition kostet es Vorrat**, genau wie ein
        Nachladen. Genau hier lief die Begrenzung frueher ins Leere: jeder
        Wiedereinstieg schenkte alle Magazine neu - in einem Deathmatch
        also alle paar Sekunden sechzig Schuss, am Vorrat vorbei. Man kam
        nie in die Lage, aus dem Vorrat nachladen zu muessen; der blieb
        voll, und weil er voll blieb, liess sich auch keine
        Munitionskiste aufheben. Zwei gemeldete Fehler, eine Ursache.
        """
        if not self.knapp:
            k.magazin = {w: K.WAFFEN[w]["magazin"] for w in k.waffen}
            return
        for w in k.waffen:
            voll = K.WAFFEN[w]["magazin"]
            if not voll:
                continue
            fehlt = voll - k.magazin.get(w, 0)
            hat = k.vorrat.get(w, 0)
            gibt = max(0, min(fehlt, hat))
            k.magazin[w] = k.magazin.get(w, 0) + gibt
            k.vorrat[w] = hat - gibt

    def _wieder_einsteigen(self, k: Kaempfer) -> None:
        # Ein im Menue geaendertes Loadout gilt ab dem naechsten Leben.
        # Sofort waere ein kostenloser Waffenwechsel mitten im Gefecht -
        # man wuerde die Ausruestung nach dem Gegner aussuchen, den man
        # gerade vor sich hat, und die Entscheidung waere keine mehr.
        self._loadout_anlegen(k)
        k.pos.update(self._einstiegsort(k.team, ausser=k))
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
        self._magazine_fuellen(k)
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
            # Die Partiekennung vergibt **nur** der Gastgeber, und sie geht
            # an alle. Das ist der ganze Trick gegen auseinanderlaufende
            # Zahlen: jeder Rechner traegt dieselbe Runde unter derselben
            # Kennung ein, und die Tabelle laesst sie genau einmal zu. Ob
            # ein Gast die Meldung zweimal bekommt oder sein Abgleich
            # dreimal losgeht, ist damit gleichgueltig.
            self.partie = self.partie or ablage.kennung()
            self.endwerte = self._werte_aller()
            self.gastgeber.an_alle({"t": "ende", "liste": self.liste,
                                    "gewonnen": gewonnen, "welle": self.welle,
                                    "sieger": self.sieger_team,
                                    "teampunkte": list(self.teampunkte),
                                    "partie": self.partie,
                                    "werte": self.endwerte})
        self._runde_buchen()

    def _werte_aller(self) -> dict:
        """Die Zahlen jedes Spielers, nach Spielernummer.

        Gerechnet hat sie der Gastgeber - er ist der einzige, der die
        Welt simuliert und damit der einzige, der sie ueberhaupt kennen
        kann. Ein Gast bekommt seine eigenen zugeschickt und traegt nur
        die ein; so kann niemand seine eigene Statistik erfinden, und
        zwei Rechner koennen fuer dieselbe Runde keine zwei verschiedenen
        Zahlen ablegen.
        """
        raus = {}
        for k in self.kaempfer.values():
            raus[str(k.nummer)] = {"werte": k.werte_runde(),
                                   "waffen": k.waffen_runde(),
                                   "team": k.team, "name": k.name,
                                   "opfer": {str(n): z for n, z
                                             in k.opfer.items() if z}}
        return raus

    def _runde_buchen(self, werte=None) -> None:
        """Die eigene Runde ins Journal des Kontos schreiben.

        Genau einmal je Runde, und nur die eigene Figur. `partie` kommt
        vom Gastgeber; ohne sie wird nicht gebucht, denn eine Runde ohne
        gemeinsame Kennung waere die eine, die doppelt zaehlen koennte.
        """
        konto = getattr(self.app, "konto", None)
        if konto is None or self.ich is None or not self.partie:
            return
        if self.partie == self._gebucht:
            return
        self._gebucht = self.partie
        if werte is None:
            werte = {"werte": self.ich.werte_runde(),
                     "waffen": self.ich.waffen_runde(),
                     "team": self.ich.team}
        zahlen = dict(werte.get("werte") or {})
        zahlen["runden"] = 1
        zahlen["spielzeit"] = round(self._rundenzeit, 1)
        sieger = self.sieger_team
        gewonnen = (self.gewonnen if not self.mit_teams
                    else (sieger >= 0 and sieger == werte.get("team", -1)))
        zahlen["siege"] = 1 if gewonnen else 0
        konto.runde_eintragen({
            "partie": self.partie, "modus": self.modus,
            "gastgeber": self.ist_gastgeber, "gewonnen": bool(gewonnen),
            "team": int(werte.get("team", -1)),
            "werte": zahlen, "waffen": dict(werte.get("waffen") or {}),
        })

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
                # Magazin und Vorrat **jeder** Waffe, nicht nur der
                # gehaltenen. Stand hier einmal nur die gehaltene, und der
                # Gast sah in der Hotbar fuer jede andere Waffe den Stand
                # vom Rundenbeginn - gemessen 30/90 fuers Sturmgewehr,
                # waehrend es in Wahrheit 1/60 hatte. Die Waffenliste geht
                # mit, damit beide Listen sicher zueinander gehoeren.
                # Dash: wie viele bereit, wie weit die naechste ist, und
                # ob gerade einer laeuft (fuer die Spur hinter der Figur).
                "dl": k.dash_ladungen, "dp": round(k.dash_laden, 2),
                "dr": round(k.dash_rest, 2),
                "wl": list(k.waffen),
                "ml": [k.magazin.get(n, 0) for n in k.waffen],
                "vl": [k.vorrat.get(n, 0) for n in k.waffen],
                "nl": round(k.nachlade_rest, 2),
                "fo": round(k.fokus, 2), "zi": k.zielt,
                "tr": k.tracer, "tw": k.tracer_weit,
                "mk": k.medkits, "hr": round(k.heilt_rest, 2),
                "sz": round(k.schlag_zeigen, 2),
                "wi": round(k.wieder_in, 1),
                "ab": k.am_boden, "br": round(k.boden_rest, 1),
                "rs": round(k.revive_stand, 2),
                "tm": k.team, "ra": k.raus,
                # Raketenwerfer und Zielerfassung. Der Gast zeichnet
                # daraus den Ring um sein Ziel und die Warnung, wenn er
                # selbst erfasst wird.
                "rp": k.rpg,
                "ef": -1 if k.erfasst is None else getattr(k.erfasst,
                                                           "nummer", -1),
                "es": round(k.erfassung, 2),
                # Wem gerade aufgeholfen wird: der Gast braucht es fuer
                # den blauen Schein am Rand, sonst weiss er nicht, warum
                # seine Figur festhaengt.
                "hf": -1 if k.hilft is None else k.hilft,
                # Ziehen und Rufen: wen er zieht, und wie lange sein Ruf
                # noch nachleuchtet.
                "zg": -1 if k.zieht is None else k.zieht,
                "rz": round(k.ruf_zeigen, 2),
            })
        flug = []
        gegner = []
        beute = []
        for w in self.welt.wesen:
            if not w.lebt:
                continue
            if isinstance(w, KampfGegner):
                # Die Kennung ist neu und der Grund, warum Gegner beim
                # Gast nicht mehr ruckeln - siehe _gegner_uebernehmen.
                # Der Vorlauf sagt, ob gerade eine Faehigkeit anliegt:
                # ohne ihn saehe der Gast den Stampfer erst am Schaden.
                gegner.append([round(w.pos.x, 1), round(w.pos.y, 1),
                               round(w.winkel, 1), w.ebene, w.art,
                               round(max(0.0, w.leben) / w.max_leben, 2),
                               w.kennung, round(w.f_vorlauf, 2)])
                continue
            if isinstance(w, KampfBeute):
                beute.append([round(w.pos.x, 1), round(w.pos.y, 1),
                              w.ebene, w.bild])
                continue
            name = getattr(w, "bild", None)
            if name in ("geschoss", "granate", "rauchgranate"):
                # Die Flughoehe muss mit: eine Granate, die eine Ebene
                # tiefer faellt, haengt beim Gast sonst in der Luft. Und
                # die Kennung, damit der Gast dieselbe Granate von einem
                # Paket zum naechsten wiedererkennt und zwischen den
                # Paketen weiterzeichnen kann, statt sie springen zu
                # lassen.
                flug.append([round(w.pos.x, 1), round(w.pos.y, 1),
                             round(w.winkel, 1), w.ebene, name,
                             round(getattr(w, "flug", 0.0), 1), w.kennung])
        # Die Kennung muss mit. Ohne sie kann der Gast eine Wolke, die er
        # schon hat, nicht von einer neuen unterscheiden - und baut sie
        # deshalb bei jedem Paket neu (siehe _welt_uebernehmen).
        qualm = [[round(r.pos.x, 1), round(r.pos.y, 1), r.ebene,
                  round(r.radius, 1), round(r.alter, 2), r.kennung]
                 for r in self.welt.rauch if r.lebt]
        # Die Wirkungen gehen genau einmal hinaus. Was hier mitgeht, ist
        # geleert, bevor der naechste Schritt neue erzeugt - sonst
        # explodierte bei den Gaesten jede Granate wieder und wieder.
        wirkung, self._wirkung = self._wirkung, []
        # Brandflaechen wie der Rauch: mit Kennung, damit der Gast sie
        # wiedererkennt und nicht bei jedem Paket neu anlegt. Das war beim
        # Rauch der teure Fehler, und ein Feuerfeld kostet genauso viel.
        brand = [[round(b.pos.x, 1), round(b.pos.y, 1), b.ebene,
                  round(b.radius, 1), round(b.alter, 2), b.kennung]
                 for b in self.welt.feuer if b.lebt]
        return {"t": "welt", "rest": round(self.rest, 1), "rauch": qualm,
                "feuer": brand,
                "wirkung": wirkung,
                "spieler": spieler, "schuesse": flug, "beute": beute,
                "gegner": gegner, "welle": self.welle,
                "pause": round(self.pause_rest, 1),
                "offen": len(self.gegner_offen), "aus": self.vorbei,
                # Mannschaften, Kreis und Runden. Der Gast rechnet nichts
                # davon selbst nach - er zeigt nur an, was hier steht.
                "tp": list(self.teampunkte),
                "zs": [round(s, 1) for s in self.zone_stand],
                "zh": self.zone_halter,
                "zk": self.kreis_nr,
                "rn": self.runde, "rp": round(self.runden_pause, 1),
                "rg": self.runden_gespielt, "rs": self.runde_sieger,
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

        # Vor dem Lesen der Post hochgezaehlt, nicht danach: eine
        # Meldung setzt die Uhr auf null, und dann soll die Ueberblendung
        # bei null anfangen und nicht schon bei der Haelfte stehen.
        self._seit_paket += dt

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
                    self.welt.feuer = []
                    self._fremde_beute = []
                    self._fremde_gegner = []
                    self._fremde_schuesse = []
                    self.welt.partikel = []
                    self.welt.muendungen = []
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
                # Die Zahlen rechnet der Gastgeber, der Gast traegt nur
                # seine eigenen ein - unter der Kennung, die von dort
                # kommt. Damit legen beide dieselbe Runde ab, und die
                # Tabelle laesst sie genau einmal zu.
                self.partie = str(nachricht.get("partie") or "")
                alle = nachricht.get("werte")
                meine = None
                if isinstance(alle, dict):
                    self.endwerte = alle
                    meine = alle.get(str(self.meine_nummer))
                self._runde_buchen(meine if isinstance(meine, dict) else None)

        # Der Gast simuliert nichts, seine Rueckmeldungen muessen aber
        # trotzdem laufen: Staubringe und Aufschriften altern hier.
        self.welt.effekte_schritt(dt)
        self._aufsetzen_erkennen()

        self._seit_senden += dt
        eilig = bool(self._knoepfe) or self._waffe_wunsch >= 0
        if eilig or self._seit_senden >= K.NETZ["eingabe_takt"]:
            # Bei einer eiligen Meldung faengt der Takt neu an, sonst wird
            # nur der Takt abgezogen - siehe die Begruendung beim
            # Gastgeber.
            self._seit_senden = (0.0 if eilig
                                 else self._seit_senden - K.NETZ["eingabe_takt"])
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
            self.runden_anzahl = max(g[0], min(g[1], int(
                nachricht.get("runden", self.runden_anzahl))))
        except (TypeError, ValueError):
            pass
        self.medkits_spawnen = bool(nachricht.get("medkit_spawn",
                                                  self.medkits_spawnen))
        regel = nachricht.get("loadouts")
        if regel in K.GEFECHT["loadout_arten"]:
            self.loadout_regel = regel
        self.rpg_an = bool(nachricht.get("rpg", self.rpg_an))
        self.rpg_lenkung = bool(nachricht.get("rpg_lenkung", self.rpg_lenkung))
        karte = str(nachricht.get("karte", ""))
        if karte and karte != self.karte:
            # Der Gastgeber bestimmt die Karte. Wer sie nicht hat, bleibt
            # auf der Testkarte - dann stimmt zwar nichts mehr, aber er
            # fliegt wenigstens nicht heraus, und der Hinweis sagt es.
            gelesen, kopf = welt_modul.karte_lesen(karte)
            if gelesen is not None:
                self.welt = gelesen
                self.karte, self.karte_kopf = karte, kopf
                self._welt_verdrahten()
                self.kreise = self._kreise_lesen()
                self._kreis_setzen(0)
            else:
                self.hinweis = "KARTE %s FEHLT" % karte.upper()
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

    def misch(self, alpha: float = 0.0) -> float:
        """Wie weit zwischen der vorletzten und der letzten Meldung.

        0 heisst: die letzte Meldung ist gerade angekommen, 1 heisst: die
        naechste ist faellig. Beim Gastgeber gibt es nichts zu mischen,
        der rechnet ja selbst - dort zaehlt der Bildanteil des Schrittes.

        `alpha` ist genau dieser Bildanteil und gehoert dazu: gerechnet
        wird nur alle 1/120 s, gezeichnet bis zu 300-mal in der Sekunde.
        Ohne ihn haette die Ueberblendung nur so viele Stufen, wie es
        Rechenschritte gibt, und zwei bis drei Bilder hintereinander
        zeigten dasselbe - gemessen stand die Granate dann in 61 % der
        Bilder still. Mit ihm laeuft sie in jedem Bild weiter.
        """
        vergangen = self._seit_paket + max(0.0, min(1.0, alpha)) * K.FIXED_DT
        return max(0.0, min(1.0, vergangen / max(1e-4, self._paket_takt)))

    def _welt_uebernehmen(self, meldung: dict) -> None:
        # Den Meldungsabstand messen und weich mitfuehren. Ein einzelnes
        # spaetes Paket soll die Ueberblendung nicht gleich umwerfen.
        if self._seit_paket > 0.0:
            self._paket_takt += (self._seit_paket - self._paket_takt) * 0.25
            self._paket_takt = max(K.NETZ["takt"] * 0.5,
                                   min(0.5, self._paket_takt))
        self._seit_paket = 0.0
        self.rest = float(meldung.get("rest", self.rest))
        self.vorbei = bool(meldung.get("aus", False))
        self.welle = int(meldung.get("welle", 0))
        self.pause_rest = float(meldung.get("pause", 0.0))
        self._liste_uebernehmen(self.teampunkte, meldung.get("tp"), int)
        self._liste_uebernehmen(self.zone_stand, meldung.get("zs"), float)
        self.zone_halter = int(meldung.get("zh", -1))
        kreis = int(meldung.get("zk", 0))
        if self.kreise and kreis != self.kreis_nr:
            self._kreis_setzen(kreis)
        self.runde = int(meldung.get("rn", 0))
        self.runden_pause = float(meldung.get("rp", 0.0))
        self.runden_gespielt = int(meldung.get("rg", 0))
        self.runde_sieger = int(meldung.get("rs", -1))
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
            namen, mags, vorr = (eintrag.get("wl"), eintrag.get("ml"),
                                 eintrag.get("vl"))
            if (isinstance(namen, list) and isinstance(mags, list)
                    and isinstance(vorr, list)
                    and len(namen) == len(mags) == len(vorr)):
                for n, m, v in zip(namen, mags, vorr):
                    try:
                        k.magazin[str(n)] = int(m)
                        k.vorrat[str(n)] = int(v)
                    except (TypeError, ValueError):
                        continue
            k.nachlade_rest = float(eintrag.get("nl", 0.0))
            k.dash_ladungen = int(eintrag.get("dl", K.DASH["ladungen"]))
            k.dash_laden = float(eintrag.get("dp", 0.0))
            k.dash_rest = float(eintrag.get("dr", 0.0))
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
            zieht = int(eintrag.get("zg", -1))
            k.zieht = None if zieht < 0 else zieht
            k.ruf_zeigen = float(eintrag.get("rz", 0.0))
            k.rpg = bool(eintrag.get("rp", False))
            if k.rpg and k.waffen != ["rakete"]:
                # Beim Gast wird nichts simuliert: die Waffe muss aus der
                # Meldung folgen, sonst traegt seine Figur im Bild
                # weiterhin das Gewehr, waehrend sie in Wahrheit ein Rohr
                # auf der Schulter hat.
                k.rpg_waffen = list(k.waffen)
                k.waffen = ["rakete"]
                k.waffe = 0
                k.magazin.setdefault("rakete", 1)
            elif not k.rpg and k.waffen == ["rakete"]:
                k.waffen = k.rpg_waffen or list(K.HOTBAR)
                k.waffe = 0
            k.erfassung = float(eintrag.get("es", 0.0))
            k._erfasst_nummer = int(eintrag.get("ef", -1))
        for nummer in list(self.kaempfer):
            if nummer not in gesehen:
                self.kaempfer.pop(nummer, None)
        # Erst jetzt, wo alle da sind, die Erfassung verknuepfen.
        for k in self.kaempfer.values():
            nr = getattr(k, "_erfasst_nummer", -1)
            k.erfasst = self.kaempfer.get(nr) if nr >= 0 else None
        # Der Renderer laeuft ueber welt.wesen: beim Gast wird die Liste
        # gesetzt statt simuliert.
        self.welt.wesen = [k for k in self.kaempfer.values() if k.lebt]
        self.welt.neue = []
        if self.ich is not None:
            self.welt.held = self.ich
        vorige_beute = self._fremde_beute
        self._fliegendes_uebernehmen(meldung.get("schuesse", []))
        self._rauch_uebernehmen(meldung.get("rauch", []))
        self._feuer_uebernehmen(meldung.get("feuer", []))
        self._wirkung_nachspielen(meldung.get("wirkung", []))
        self._fremde_beute = [tuple(b) for b in meldung.get("beute", [])
                              if isinstance(b, (list, tuple)) and len(b) == 4]
        self._gegner_uebernehmen(meldung.get("gegner", []))
        self._aufgehoben_erkennen(vorige_beute)

    def _gegner_uebernehmen(self, eintraege) -> None:
        """Gegner beim Gast nachfuehren, mit Zwischenlage.

        Genau dieselbe Ueberlegung wie bei den Geschossen, und genau
        derselbe Fehler: die Liste wurde bei jedem Paket weggeworfen und
        gezeichnet wurde die zuletzt gemeldete Stelle. Bei sechzig
        Paketen und 120 Bildern heisst das, dass jeder Gegner die Haelfte
        der Zeit stillsteht und dann springt. Bei einem Laeufer faellt
        das gerade noch durch; bei einem Koloss, der 58 Pixel breit ist
        und sich langsam bewegt, sieht man jeden Sprung.
        """
        vorher = {e[6]: e for e in self._fremde_gegner if len(e) > 6}
        raus = []
        for e in eintraege:
            if not isinstance(e, (list, tuple)) or len(e) < 6:
                continue
            try:
                x, y = float(e[0]), float(e[1])
                winkel, ebene = float(e[2]), int(e[3])
                art, anteil = str(e[4]), float(e[5])
                # Aeltere Gastgeber schicken beides nicht. Dann gibt es
                # keine Zwischenlage und keine Ankuendigung, aber der
                # Gegner steht trotzdem da.
                kennung = int(e[6]) if len(e) > 6 else 0
                vorlauf = float(e[7]) if len(e) > 7 else 0.0
            except (TypeError, ValueError):
                continue
            alt = vorher.get(kennung) if kennung else None
            vx, vy = (alt[0], alt[1]) if alt is not None else (x, y)
            raus.append((x, y, winkel, ebene, art, anteil, kennung, vorlauf,
                         vx, vy))
        self._fremde_gegner = raus

    def _fliegendes_uebernehmen(self, eintraege) -> None:
        """Geschosse und Granaten beim Gast nachfuehren, mit Zwischenlage.

        Der zweite Teil des gemeldeten Granatenfehlers steckte hier. Die
        Liste wurde bei jedem Paket weggeworfen und neu gesetzt, und
        gezeichnet wurde stur die zuletzt gemeldete Stelle. Bei sechzig
        Paketen und dreihundert Bildern in der Sekunde heisst das: fuenf
        Bilder lang steht die Granate still, dann springt sie um ihren
        ganzen Weg weiter - waehrend jeder Mitspieler daneben sauber
        zwischen zwei Meldungen laeuft, weil Kaempfer ein `vorher` haben.
        Eine Granate sprang also sichtbar und landete gefuehlt woanders,
        als sie geflogen war.

        Jetzt traegt jedes fliegende Ding seine Kennung. Was schon da
        war, behaelt seine letzte Lage als `vorher`, und gezeichnet wird
        dazwischen - genau wie bei den Figuren.
        """
        vorher = {e[6]: e for e in self._fremde_schuesse if len(e) > 6}
        raus = []
        for e in eintraege:
            if not isinstance(e, (list, tuple)) or len(e) < 6:
                continue
            try:
                x, y = float(e[0]), float(e[1])
                winkel, ebene = float(e[2]), int(e[3])
                name, hoehe = str(e[4]), float(e[5])
                # Aeltere Gastgeber schicken keine Kennung. Dann gibt es
                # eben keine Zwischenlage, aber alles andere geht weiter.
                kennung = int(e[6]) if len(e) > 6 else 0
            except (TypeError, ValueError):
                continue
            alt = vorher.get(kennung) if kennung else None
            # Die bisher gemeldete Lage wird zur Ausgangslage. Zwischen
            # ihr und der neuen wird gezeichnet.
            vx, vy = (alt[0], alt[1]) if alt is not None else (x, y)
            raus.append((x, y, winkel, ebene, name, hoehe, kennung, vx, vy))
        self._fremde_schuesse = raus

    def _feuer_uebernehmen(self, eintraege) -> None:
        """Brandflaechen beim Gast nachfuehren, ohne sie neu zu bauen.

        Wortwoertlich dieselbe Ueberlegung wie beim Rauch: eine Flaeche
        rechnet beim Anlegen ihr Dichtefeld, und das bei sechzig Paketen
        in der Sekunde neu zu tun kostet mehr als die halbe Rechenzeit.
        Die Kennung sagt, was schon da ist.

        Schaden macht hier nichts: der Gast rechnet die Welt nicht, und
        `Welt.schritt` laeuft bei ihm gar nicht erst. Die Flaechen altern
        nur mit, damit sie zuengeln und ausgehen.
        """
        vorhanden = {b.kennung: b for b in self.welt.feuer}
        behalten = []
        for eintrag in eintraege:
            if not isinstance(eintrag, (list, tuple)) or len(eintrag) < 6:
                continue
            try:
                x, y = float(eintrag[0]), float(eintrag[1])
                ebene, radius = int(eintrag[2]), float(eintrag[3])
                alter = float(eintrag[4])
                kennung = int(eintrag[5])
            except (TypeError, ValueError):
                continue
            alt = vorhanden.get(kennung)
            if alt is not None:
                alt.alter = alter
                alt.lebt = True
                behalten.append(alt)
                continue
            behalten.append(Brandflaeche(pygame.Vector2(x, y), ebene, radius,
                                         alter=alter, kennung=kennung))
        self.welt.feuer = behalten

    def _rauch_uebernehmen(self, eintraege) -> None:
        """Rauchwolken beim Gast nachfuehren - **ohne sie neu zu bauen**.

        Hier lag der Fehler, der sich als "Desync" gezeigt hat. Vorher warf
        der Gast bei *jedem* Netzpaket alle Wolken weg und legte sie neu an.
        Eine Wolke rechnet beim Anlegen ihr Dichtefeld, und das kostet:
        gemessen **9 Millisekunden fuer zwei Wolken**. Bei sechzig Paketen
        je Sekunde sind das 550 Millisekunden Rechenzeit je Sekunde - mehr
        als die Haelfte des Rechners, nur fuer Rauch.

        Das Bild des Gastes brach dadurch ein, sobald Rauch stand. Was man
        sah, waren ruckelnde Mitspieler und Granaten, die zu springen
        schienen - also genau das, was nach Desync aussieht, in Wahrheit
        aber eine ueberlastete Anzeige war.

        Jede Wolke traegt jetzt eine Kennung. Was der Gast schon hat,
        bekommt nur sein neues Alter; neu ist nur, was wirklich neu ist,
        und weg ist, was der Gastgeber nicht mehr meldet.
        """
        vorhanden = {r.kennung: r for r in self.welt.rauch}
        behalten = []
        for eintrag in eintraege:
            if not isinstance(eintrag, (list, tuple)) or len(eintrag) < 5:
                continue
            try:
                x, y = float(eintrag[0]), float(eintrag[1])
                ebene, radius = int(eintrag[2]), float(eintrag[3])
                alter = float(eintrag[4])
                # Aeltere Gastgeber senden keine Kennung. Dann dient die
                # Lage als Ersatz: eine Wolke bewegt sich nicht.
                kennung = int(eintrag[5]) if len(eintrag) > 5 else \
                    hash((round(x), round(y), ebene)) & 0x7FFFFFFF
            except (TypeError, ValueError):
                continue
            alt = vorhanden.get(kennung)
            if alt is not None:
                alt.alter = alter
                alt.lebt = True
                behalten.append(alt)
                continue
            behalten.append(Rauchwolke(pygame.Vector2(x, y), ebene, radius,
                                       alter=alter, kennung=kennung))
        self.welt.rauch = behalten

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
                self.welt.klang("sturz", 0.55 + 0.45 * wucht, k.pos, k.ebene)
                # Dieselbe Rechnung wie ueberall, mit `quelle=k`: der eigene
                # Aufschlag zaehlt voll, der eines anderen nach Ebene und
                # Entfernung.
                self.welt.ruckeln(K.STURZ["ruckeln"] + vorher * 0.035, "sturz",
                                  k.pos, k.ebene, k)
            self._flughoehen[k.nummer] = k.flug

    # ---- Szene ---------------------------------------------------------
    def schritt(self, dt: float) -> None:
        self._zeit += dt
        if not self.vorbei:
            self._rundenzeit += dt
        self._start_masken()
        if not self.pausiert:
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
        self._befinden_fuehren(dt)
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
        # Die Einstellung greift bei jedem Bild neu: wer das Wackeln
        # im Pausenmenue abschaltet, sieht es sofort stehen.
        self.kamera.anteil = self.app.opt.ruckel_anteil()
        self.kamera.schritt(dt, self.ich.pos, self.ich.ziel,
                            (ebene.pixel_breite, ebene.pixel_hoehe))

    def _befinden_fuehren(self, dt: float) -> None:
        """Den roten Rand und den Herzschlag nachfuehren.

        Gelesen wird ausschliesslich das eigene Leben - beim Gast steht es
        in der Weltmeldung, beim Gastgeber in seiner Figur, und beide
        Wege fuehren hier zusammen. Ein Treffer wird am Unterschied
        erkannt und nicht gemeldet: dann gilt dieselbe Rechnung fuer
        Kugeln, Granaten, Stuerze und alles, was noch kommt.
        """
        ich = self.ich
        if ich is None:
            return
        leben = max(0.0, ich.leben) if ich.lebt else 0.0
        if leben < self._leben_vorher - 0.01:
            self.befinden.treffer((self._leben_vorher - leben) / 40.0)
        elif leben > self._leben_vorher + 20.0:
            # Deutlich mehr Leben als eben: Wiedereinstieg oder
            # Aufgeholfen. Dann faengt alles von vorn an.
            self.befinden.zuruecksetzen()
        self._leben_vorher = leben
        if ich.heilt_rest <= 0 < self._heilte:
            self.befinden.medkit()
        self._heilte = ich.heilt_rest
        self.befinden.schritt(dt, leben / max(1.0, ich.max_leben), self._klang)
        self.app.klaenge.daempfung_setzen(self.befinden.dumpf)
        if self.befinden.dumpf > 0.0:
            self.app.klaenge.dumpf_nachziehen()

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
        konto = getattr(self.app, "konto", None)
        eintraege.append(("ausruestung", "MEINE AUSRUESTUNG",
                          konto.loadout["name"] if konto else ""))
        eintraege.append(("konto", "KONTO",
                          konto.name.upper() if konto and konto.angemeldet
                          else "NICHT ANGEMELDET"))
        if self.ist_gastgeber:
            w = self.wunsch
            eintraege.append(("modus", "SPIELART", K.MODI[w["modus"]]["name"]))
            eintraege.append(("karte", "KARTE",
                              (w["karte"] or "TESTKARTE").upper()))
            regeln = K.MODI[w["modus"]]
            if regeln["runden"]:
                eintraege.append(("runden", "GESPIELTE RUNDEN",
                                  str(w["runden"])))
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
            eintraege.append(("loadouts", "AUSRUESTUNG",
                              "EIGENES LOADOUT" if w["loadouts"] == "eigenes"
                              else "JEDER HAT ALLES"))
            eintraege.append(("rpg", "RAKETENWERFER",
                              "AN" if w["rpg"] else "AUS"))
            if w["rpg"]:
                eintraege.append(("rpg_lenkung", "  MIT ZIELERFASSUNG",
                                  "AN" if w["rpg_lenkung"] else "AUS"))
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
        if ev.type == pygame.MOUSEWHEEL and self.menue is None:
            self._rad += ev.y
            return
        if ev.type != pygame.KEYDOWN:
            return
        if self.menue is None:
            self._knopf_merken(ev.key)
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
    TATEN = ("weiter", "raus", "teams", "neu", "ausruestung", "konto")

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
        if schluessel in ("ausruestung", "konto"):
            # Als eigene Szene und nicht als Unterseite: die beiden
            # Masken gehoeren dem Konto, nicht dem Gefecht, und der
            # Einzelspieler oeffnet genau dieselben. Das Gefecht laeuft
            # darunter weiter (Szene.weiterlaufen), sonst faellt die
            # Leitung tot.
            from .menues import Anmeldung, Ausruestung
            self._menue_zu()
            self.app.schieben(Ausruestung(self.app)
                              if schluessel == "ausruestung"
                              else Anmeldung(self.app))
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
            w["runden"] = max(g[0], min(g[1], w["runden"] + (1 if vor else -1)))
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
        elif schluessel == "loadouts":
            w["loadouts"] = ("alles" if w["loadouts"] == "eigenes"
                             else "eigenes")
        elif schluessel == "karte":
            # Alle Karten aus dem Ordner, dazu die eingebaute Testkarte
            # als leerer Name. Wer keine Datei hat, blaettert eben nur
            # durch eine Auswahl von einer.
            auswahl = [""] + welt_modul.karten_liste()
            jetzt = w["karte"] if w["karte"] in auswahl else ""
            i = (auswahl.index(jetzt) + (1 if vor else -1)) % len(auswahl)
            w["karte"] = auswahl[i]
        elif schluessel == "rpg":
            w["rpg"] = not w["rpg"]
            self.menue = min(self.menue, len(self._menue_baut()) - 1)
        elif schluessel == "rpg_lenkung":
            w["rpg_lenkung"] = not w["rpg_lenkung"]
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
        k.pos.update(self._einstiegsort(k.team, ausser=k))
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
        self.runden_anzahl = int(w["runden"])
        self.knapp = bool(w["knapp"])
        self.schutz_an = bool(w["schutz"])
        self.start_medkits = int(w["medkits"])
        self.medkits_spawnen = bool(w["medkit_spawn"])
        if w.get("loadouts") in K.GEFECHT["loadout_arten"]:
            self.loadout_regel = w["loadouts"]
        self.rpg_an = bool(w.get("rpg", self.rpg_an))
        self.rpg_lenkung = bool(w.get("rpg_lenkung", self.rpg_lenkung))
        gewaehlt = str(w.get("karte", ""))
        if gewaehlt != self.karte:
            gelesen, kopf = (welt_modul.karte_lesen(gewaehlt) if gewaehlt
                             else (testkarte(), {}))
            if gelesen is not None:
                self.welt = gelesen
                self.karte, self.karte_kopf = gewaehlt, kopf
                self._welt_verdrahten()
                self.kreise = self._kreise_lesen()
                self._kreis_setzen(0)
                # Alles, was auf der alten Karte stand, gehoert nicht auf
                # die neue - auch nicht die Kaempfer.
                for k in self.kaempfer.values():
                    self.welt.dazu(k)

        self.teampunkte = [0] * len(K.TEAMS["namen"])
        self.zone_stand = [0.0] * len(self.teampunkte)
        self.zone_halter = -1
        self.runde = 0
        self.runden_gespielt = 0
        self.runde_sieger = -1
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
        self.welt.feuer = []
        # Auch die Wirkungen, die noch nicht hinaus sind: sonst knallt
        # bei den Gaesten im ersten Bild der neuen Runde noch die letzte
        # Granate der alten.
        self._wirkung = []
        self.welt.partikel = []
        self.welt.muendungen = []
        # Eine neue Partie faengt bei null an - auch beim Zaehlen.
        self.partie = ""
        self._rundenzeit = 0.0
        self.endwerte = {}
        for k in self.kaempfer.values():
            k.zaehler_leeren()
            k.opfer = {}
            k.rpg_ablegen()
            self._loadout_anlegen(k)

        self._teams_ausgleichen()
        self._einstiegszonen_waehlen()
        for k in self.kaempfer.values():
            k.abschuesse = 0
            k.tode = 0
            k.knapp = self.knapp
            k.vorrat = {v: K.MUNITION["vorrat"].get(v, 0) for v in k.waffen}
            if not self.mit_teams:
                k.team = -1
            k.fraktion = self._fraktion_fuer(k.nummer, k.team)
            self._regeln_anlegen(k)
            k.lebt = True
            self._wieder_einsteigen(k)

        if self.ist_gastgeber:
            self.gastgeber.an_alle(dict(self._willkommen(-1, None),
                                        t="neustart"))

    def _start_masken(self) -> None:
        """Einmal beim Betreten: anmelden, und wenn noetig ausruesten.

        Beides **einmal** und beides wegdrueckbar. Wer "OHNE KONTO
        SPIELEN" waehlt, wird nicht wieder gefragt; wer sich ein Loadout
        zusammengestellt hat, auch nicht. Eine Maske, die bei jedem Start
        wieder auftaucht, lernt man wegzuklicken, ohne sie zu lesen - und
        dann haette sie auch gleich wegbleiben koennen.
        """
        if self._masken_durch:
            return
        stapel = getattr(self.app, "stapel", [])
        if self not in stapel or stapel[-1] is not self:
            return
        self._masken_durch = True
        konto = getattr(self.app, "konto", None)
        if konto is None:
            return
        from .menues import Anmeldung, Ausruestung

        def ausruesten(_szene=None):
            if self.mit_loadouts and not konto.loadout_gewaehlt_je:
                self.app.schieben(Ausruestung(self.app))

        if not konto.angemeldet and not konto.werte.get("anmeldung_gefragt"):
            konto.werte["anmeldung_gefragt"] = True
            konto.profil_sichern()
            self.app.schieben(Anmeldung(self.app, danach=ausruesten))
            return
        ausruesten()

    def _wunsch_lesen(self) -> dict:
        """Die Regeln, die gerade gelten, als Ausgangspunkt fuers Menue."""
        return dict(modus=self.modus, karte=self.karte,
                    ende_art=self.ende_art,
                    ende_wert=self.ende_wert, runden=self.runden_anzahl,
                    knapp=self.knapp, schutz=self.schutz_an,
                    medkits=self.start_medkits,
                    medkit_spawn=self.medkits_spawnen,
                    loadouts=self.loadout_regel,
                    rpg=self.rpg_an, rpg_lenkung=self.rpg_lenkung)


    # ---- Bild ----------------------------------------------------------
    def zeichnen(self, ziel, alpha: float) -> None:
        # Beim Gast wird nicht zwischen zwei Rechenschritten ueberblendet,
        # sondern zwischen zwei Meldungen. `vorher` und `pos` eines
        # Mitspielers stehen bei ihm eine Sechzigstelsekunde auseinander,
        # nicht eine Hundertzwanzigstel - mit dem Bildanteil waere die
        # Bewegung nach der halben Zeit fertig und stuende dann still.
        # Genau das sah man als Ruckeln der Mitspieler.
        misch = alpha if self.ist_gastgeber else self.misch(alpha)
        self.renderer.welt_zeichnen(ziel, self.welt, self.kamera, misch,
                                    self.blick_hoehe, blick=self.blick,
                                    boden=self._kreis_zeichnen)
        if not self.ist_gastgeber:
            self._fremdes_zeichnen(ziel, misch)
        if (self.ich is not None and self.ich.lebt and not self.ich.am_boden
                and self.blick == self.ich.ebene):
            self.renderer.zielhilfen(ziel, self.welt, self.kamera, self.ich)
            self.renderer.tracer(ziel, self.welt, self.kamera, self.ich)
        self._namen_zeichnen(ziel)
        self._randpfeile(ziel)
        self._erfassung_zeichnen(ziel)
        # Der rote Rand liegt ueber der Welt, aber unter der Anzeige: die
        # Zahlen sollen lesbar bleiben, auch wenn es einem schlecht geht.
        self.befinden.zeichnen(ziel)
        if self.ich is not None and self.ich.hilft is not None:
            # Blauer Schein am Rand, solange man jemanden aufhilft. Er
            # sagt, warum die Figur gerade nicht laeuft und nicht
            # schiesst - ohne ihn haelt man es fuer einen Haenger.
            opfer = self.kaempfer.get(self.ich.hilft)
            stand = opfer.revive_stand if opfer is not None else 0.0
            self.renderer.randglut(ziel, K.C_TEAL, 0.45 + 0.55 * stand)
        # Die Anzeige bleibt weg, sobald die Runde vorbei ist: Lebensbalken
        # und Hotbar sagen dann nichts mehr, und sie standen quer durch die
        # Siegtafel.
        if not self.vorbei:
            self._anzeige(ziel)
        else:
            self._endtafel(ziel)
        if self.menue is not None:
            self._menue_zeichnen(ziel)
        # Zuletzt und ueber allem: das Weiss einer Blendgranate. Es liegt
        # auch ueber der Anzeige - geblendet ist geblendet.
        self.befinden.blendung_zeichnen(ziel)

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
        if not self.regeln["zone"] or ebene != self.zone_ebene:
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

    def _ankuendigung_zeichnen(self, ziel, p, daten, vorlauf) -> None:
        """Was ein Boss gleich tut, bevor er es tut.

        Ein Ring, der sich zuzieht - dieselbe Sprache wie die
        Zielerfassung des Raketenwerfers, damit man sie nicht neu lernen
        muss. Beim Stampfer hat er die Groesse des Schadens: man sieht
        also nicht nur **dass** etwas kommt, sondern auch **wohin** es
        reicht, und kann entscheiden statt zu raten.
        """
        f = daten.get("faehigkeit") or {}
        gesamt = max(0.01, f.get("vorlauf", 0.5))
        anteil = max(0.0, min(1.0, vorlauf / gesamt))
        radius = float(f.get("radius", daten.get("radius", 12)) or 12)
        if f.get("art") == "brut":
            radius = daten.get("radius", 16) * 2.2
        # Aussen der volle Umfang, innen der zulaufende Ring.
        pygame.draw.circle(ziel, (78, 30, 22), (int(p.x), int(p.y)),
                           int(radius), 1)
        jetzt = int(radius * (0.25 + 0.75 * anteil))
        pygame.draw.circle(ziel, K.C_RED, (int(p.x), int(p.y)), max(2, jetzt), 2)

    def _fremdes_zeichnen(self, ziel, misch: float = 1.0) -> None:
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
        for (x, y, winkel, ebene, art, anteil, _kn, vorlauf,
             vx, vy) in self._fremde_gegner:
            if ebene != self.blick:
                continue
            # Zwischen der vorletzten und der letzten Meldung, wie bei
            # den Geschossen. Ohne das steht jeder Gegner die halbe Zeit.
            x = vx + (x - vx) * misch
            y = vy + (y - vy) * misch
            d = K.gegner_daten(art)
            s = self.renderer.bilder.gedreht(d.get("bild", "gegner_laeufer"), winkel)
            p = pygame.Vector2(x - ecke.x, y - ecke.y)
            sch = self.renderer.schatten(d.get("radius", 9))
            ziel.blit(sch, (p.x - sch.get_width() / 2 + 1,
                            p.y - sch.get_height() / 2 + 3))
            if vorlauf > 0.0:
                self._ankuendigung_zeichnen(ziel, p, d, vorlauf)
            ziel.blit(s, (p.x - s.get_width() / 2, p.y - s.get_height() / 2))
            if anteil < 0.999:
                boss = K.ist_boss(art)
                breite = 34 if boss else 20
                hoch = int(d.get("radius", 9)) + 11
                pygame.draw.rect(ziel, (16, 11, 8),
                                 (int(p.x) - breite // 2, int(p.y) - hoch,
                                  breite, 3 if boss else 2))
                pygame.draw.rect(ziel, K.C_AMBER if boss else K.C_RED,
                                 (int(p.x) - breite // 2, int(p.y) - hoch,
                                  int(breite * anteil), 3 if boss else 2))
        for (x, y, winkel, ebene, name, hoehe, _kn, vx, vy) in self._fremde_schuesse:
            # Zwischen der vorletzten und der letzten Meldung. Ohne das
            # steht eine Granate fuenf Bilder still und springt dann.
            x = vx + (x - vx) * misch
            y = vy + (y - vy) * misch
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

    def _erfassung_zeichnen(self, ziel) -> None:
        """Der Ring um das erfasste Ziel - und die Warnung, wenn man es ist.

        Zwei Sachen in einer Methode, weil sie zusammengehoeren: derselbe
        Vorgang, einmal von der Seite des Schuetzen und einmal von der des
        Getroffenen. Wer erfasst wird, **muss** es merken; eine Waffe, die
        ohne Vorwarnung um die Ecke kommt, ist keine Entscheidung mehr.
        """
        ich = self.ich
        if ich is None:
            return
        e = K.ERFASSUNG
        ecke = self.kamera.ecke

        # 1. Was ich selbst gerade erfasse.
        opfer = getattr(ich, "erfasst", None)
        stand = getattr(ich, "erfassung", 0.0)
        if opfer is not None and stand > 0.0 and opfer.lebt:
            fest = stand >= 1.0
            farbe = e["farbe_fest"] if fest else e["farbe"]
            # Der Kreis zieht sich zusammen, waehrend die Erfassung laeuft.
            r = int(e["ring_gross"]
                    + (e["ring_klein"] - e["ring_gross"]) * min(1.0, stand))
            p = opfer.pos - ecke
            if 0 <= p.x <= K.GAME_W and 0 <= p.y <= K.GAME_H:
                pygame.draw.circle(ziel, farbe, (int(p.x), int(p.y)), r, 1)
                if fest:
                    # Steht sie, kommt ein zweiter Ring dazu und vier
                    # Ecken - man soll es nicht uebersehen koennen.
                    pygame.draw.circle(ziel, farbe, (int(p.x), int(p.y)),
                                       r + 3, 1)
                    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                        ex, ey = int(p.x) + dx * (r + 3), int(p.y) + dy * (r + 3)
                        pygame.draw.line(ziel, farbe, (ex, ey),
                                         (ex - dx * 4, ey), 1)
                        pygame.draw.line(ziel, farbe, (ex, ey),
                                         (ex, ey - dy * 4), 1)

        # 2. Ob mich jemand erfasst - und ob schon geschossen wurde.
        erfasst_mich = 0.0
        for k in self.kaempfer.values():
            if k is ich:
                continue
            if getattr(k, "erfasst", None) is ich:
                erfasst_mich = max(erfasst_mich, getattr(k, "erfassung", 0.0))
        fliegt = any(getattr(r, "ziel", None) is ich
                     for r in self.welt.wesen if isinstance(r, Rakete))
        if fliegt:
            # Die Rakete ist unterwegs. Anderer Ton, und er pulst.
            puls = 0.55 + 0.45 * abs(math.sin(self._zeit * 9.0))
            self.renderer.randglut(ziel, K.ERFASSUNG["warnung_scharf"], puls)
        elif erfasst_mich > 0.0:
            self.renderer.randglut(ziel, K.ERFASSUNG["warnung"],
                                   0.25 + 0.45 * erfasst_mich)

    def _farbe_fuer(self, k, eigen: bool = False):
        """In welcher Farbe ein Mitspieler auftaucht.

        Mit Mannschaften zaehlt die Mannschaft, nicht die eigene Figur: wer
        im Gefecht ueberlegen muss, ob der da drueben zu ihm gehoert, hat
        schon verloren. Die eigene Mannschaft bekommt die helle Farbe, die
        fremde die dunkle.
        """
        if k.am_boden:
            return K.C_RED
        if self.mit_teams and 0 <= k.team < len(K.TEAMS["kombi"]):
            # Dieselbe Farbkombination wie die Figur selbst, damit Schrift
            # und Gestalt zusammengehoeren. Die eigene Mannschaft kraeftig,
            # die fremde gedaempft - so bleibt der Blick bei den eigenen
            # Leuten haengen und nicht bei jedem Namen im Bild.
            kombi = K.TEAMS["kombi"][k.team]
            eigenes_team = (self.ich is not None and k.team == self.ich.team)
            return kombi["hud"] if eigenes_team else kombi["hud_dunkel"]
        if eigen:
            return K.C_TEAL
        if self.regeln["beute"]:
            return K.C_AMBER
        return K.C_HULL                   # eigene Mannschaft, kein Ziel

    def _tastenname(self, aktion: str) -> str:
        """Die erste Taste einer Aktion, so wie der Spieler sie belegt hat."""
        tasten = getattr(getattr(self.app, "opt", None), "tasten", {}) or {}
        namen = tasten.get(aktion) or []
        return (namen[0] if namen else aktion).upper()[:6]

    def _verbuendet(self, k) -> bool:
        """Gehoert er zu mir - so, dass ich ihm aufhelfen koennte?"""
        if self.ich is None or k is self.ich or not self.regeln["revive"]:
            return False
        return (not self.mit_teams) or k.team == self.ich.team

    def _ruf_marke(self, ziel, p, k) -> None:
        """Ueber einem Rufenden: ein Zeichen, das blinkt.

        Fuer den, der ihn im Bild hat. Das Blinken ist schnell und kurz -
        es soll den Blick ziehen, nicht nerven.
        """
        an = int(k.ruf_zeigen * 9.0) % 2 == 0
        farbe = K.C_AMBER if an else K.C_CREAM
        x, y = int(p.x), int(p.y) - 40
        pygame.draw.polygon(ziel, (16, 11, 8), [(x, y - 7), (x + 7, y),
                                                (x, y + 7), (x - 7, y)])
        pygame.draw.polygon(ziel, farbe, [(x, y - 6), (x + 6, y),
                                          (x, y + 6), (x - 6, y)], 1)
        SCHRIFT.zeichnen(ziel, "!", x, y - 3, farbe, 1, ausrichtung="mitte")

    def _randpfeile(self, ziel) -> None:
        """Wo ein Gefallener aus dem eigenen Team liegt, den man nicht sieht.

        Ein Pfeil am Bildrand, der auf ihn zeigt, mit den Sekunden, die er
        noch hat. Ruft er, leuchtet der Pfeil auf und wird groesser.
        Gezeigt wird er, sobald der Gefallene nicht im Bild ist - oder auf
        einer anderen Ebene liegt, denn dann sieht man ihn ja auch nicht.
        """
        if self.ich is None or self.vorbei:
            return
        rand = 16
        mitte = pygame.Vector2(K.GAME_W / 2, K.GAME_H / 2)
        ecke = self.kamera.ecke
        for k in self.kaempfer.values():
            if not (k.lebt and k.am_boden and self._verbuendet(k)):
                continue
            p = k.pos - ecke
            im_bild = (rand <= p.x <= K.GAME_W - rand
                       and rand <= p.y <= K.GAME_H - rand)
            if im_bild and k.ebene == self.blick:
                continue
            richtung = p - mitte
            if richtung.length_squared() < 1.0:
                richtung = pygame.Vector2(0, -1)
            # Schnitt mit dem Rechteck, eingerueckt um den Rand.
            halb = pygame.Vector2(K.GAME_W / 2 - rand, K.GAME_H / 2 - rand)
            teiler = max(abs(richtung.x) / halb.x, abs(richtung.y) / halb.y)
            stelle = mitte + richtung / teiler
            winkel = math.degrees(math.atan2(richtung.y, richtung.x))
            ruft = k.ruf_zeigen > 0.0
            puls = 1.0
            if ruft:
                puls = 1.0 + 0.45 * abs(math.sin(k.ruf_zeigen * 11.0))
            groesse = 7.0 * puls
            farbe = (K.C_AMBER if (ruft and int(k.ruf_zeigen * 9) % 2 == 0)
                     else self._farbe_fuer(k, False))
            spitze = stelle + pygame.Vector2(groesse, 0).rotate(winkel)
            links = stelle + pygame.Vector2(-groesse * 0.7, groesse * 0.75).rotate(winkel)
            rechts = stelle + pygame.Vector2(-groesse * 0.7, -groesse * 0.75).rotate(winkel)
            pygame.draw.polygon(ziel, (16, 11, 8),
                                [spitze + (1, 1), links + (1, 1), rechts + (1, 1)])
            pygame.draw.polygon(ziel, farbe, [spitze, links, rechts])
            # Die Zeit, die er noch hat, und ob er eine Ebene woanders liegt.
            text = "%d" % max(0, int(k.boden_rest + 0.99))
            if k.ebene != self.blick:
                text += " E%d" % k.ebene
            hinten = stelle - pygame.Vector2(groesse + 9, 0).rotate(winkel)
            SCHRIFT.zeichnen(ziel, text, int(hinten.x), int(hinten.y) - 3,
                             farbe, 1, ausrichtung="mitte")

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
                if (not eigen and self._darf_helfen(self.ich, k)
                        and self.ich.pos.distance_to(k.pos)
                        <= K.REVIVE["reichweite"] * 2.5):
                    # In Reichweite: was geht. Das Ziehen steht dabei, weil
                    # man es sonst nie entdeckt - es ist die eine Taste,
                    # die man nur in dieser Lage braucht.
                    taste_e = self._tastenname("nutzen")
                    taste_g = self._tastenname("ziehen")
                    SCHRIFT.zeichnen(ziel, "[%s] AUF  [%s] ZIEHEN"
                                     % (taste_e, taste_g),
                                     int(p.x), int(p.y) + 14, K.C_TEAL, 1,
                                     ausrichtung="mitte")
                if k.ruf_zeigen > 0.0:
                    self._ruf_marke(ziel, p, k)
                continue
            anteil = max(0.0, min(1.0, k.leben / k.max_leben))
            pygame.draw.rect(ziel, (16, 11, 8),
                             (int(p.x) - breite // 2, int(p.y) - 18, breite, 3))
            pygame.draw.rect(ziel, farbe,
                             (int(p.x) - breite // 2, int(p.y) - 18,
                              int(breite * anteil), 3))

    @staticmethod
    def _teamzeichen(ziel, x: int, y: int, kombi: dict) -> None:
        """Das Farbzeichen einer Mannschaft: Rumpffarbe mit Akzentpunkt.

        Dieselben beiden Farben, die auch die Figur traegt. Sie stehen hier
        nicht zur Zierde: wer sie einmal neben dem Mannschaftsnamen gesehen
        hat, erkennt die Gestalt auf der anderen Seite des Raums wieder,
        ohne ihren Namen lesen zu muessen.
        """
        pygame.draw.rect(ziel, (14, 10, 7), (x - 1, y - 1, 9, 9))
        pygame.draw.rect(ziel, kombi["kante"], (x, y, 7, 7))
        pygame.draw.rect(ziel, kombi["rumpf"], (x + 1, y + 1, 5, 5))
        pygame.draw.rect(ziel, kombi["akzent"], (x + 2, y + 2, 3, 3))

    def _teamkopf(self, ziel, y: int) -> int:
        """Mannschaftsstand oben in der Mitte, je nach Spielart.

        Drei Spielarten, eine Anzeige: was zaehlt, steht in der Mitte
        zwischen den beiden Mannschaftsnamen - Abschuesse, Rundensiege oder
        der Ladestand des Kreises. Der Kreis bekommt zusaetzlich zwei
        Balken, weil man dort auf ein Zehntel genau sehen will, wie knapp
        es ist.
        """
        f = SCHRIFT
        kombis = K.TEAMS["kombi"]
        namen = [k["name"] for k in kombis]
        farben = [k["hud"] for k in kombis]
        if self.regeln["zone"]:
            werte = [int(s) for s in self.zone_stand]
        else:
            werte = list(self.teampunkte)
        mitte = K.GAME_W // 2
        links_text = "%s %d" % (namen[0], werte[0])
        rechts_text = "%d %s" % (werte[1], namen[1])
        f.zeichnen(ziel, links_text, mitte - 8, y, farben[0], 1,
                   ausrichtung="rechts")
        f.zeichnen(ziel, ":", mitte, y, K.C_MUTED_DK, 1, ausrichtung="mitte")
        f.zeichnen(ziel, rechts_text, mitte + 8, y, farben[1], 1)
        # Neben jedem Namen das Farbzeichen der Mannschaft - dieselbe
        # Kombination, die auch die Figuren tragen. Damit lernt man die
        # Zuordnung beilaeufig, statt sie im Gefecht raten zu muessen.
        self._teamzeichen(ziel, mitte - 12 - f.breite(links_text, 1) - 9,
                          y - 1, kombis[0])
        self._teamzeichen(ziel, mitte + 12 + f.breite(rechts_text, 1) + 2,
                          y - 1, kombis[1])
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
                f.zeichnen(ziel, self.runden_text(), mitte, y, K.C_MUTED, 1,
                           ausrichtung="mitte")
            y += 10
        return y

    def _anzeige(self, ziel) -> None:
        f = SCHRIFT
        # Kopfzeile: Spielart, und was die Runde beendet
        f.zeichnen(ziel, K.MODI[self.modus]["name"], 12, 12, K.C_AMBER, 1)
        rolle = "GASTGEBER" if self.ist_gastgeber else "GAST"
        if self.karte:
            rolle = "%s - %s" % (rolle, (self.karte_kopf.get("name")
                                         or self.karte).upper())
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
                # Der Vorrat steht in der Hotbar, bei der Waffe, zu der er
                # gehoert - hier bleibt nur die Warnung, wenn gar nichts
                # mehr da ist.
                vorrat = self.ich.vorrat.get(self.ich.waffe_name, 0)
                if not vorrat and not self.ich.magazin.get(
                        self.ich.waffe_name, 0):
                    # Sonst drueckt man ratlos auf R und nichts passiert.
                    f.zeichnen(ziel, "KEIN VORRAT - WAFFE WECHSELN ODER KISTE",
                               K.GAME_W // 2, K.GAME_H - 46, K.C_RED, 1,
                               ausrichtung="mitte")
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

    # ── Siegtafel ────────────────────────────────────────────────────
    #
    # Gebaut wie in den Spielen, die das seit Jahren machen: die beiden
    # Mannschaften nebeneinander, jede in ihrer Farbe, innerhalb der
    # Mannschaft sortiert. Der Sinn ist nicht Zierde - man soll nach einer
    # Runde in drei Sekunden sehen, wie sie gelaufen ist, und dafuer
    # muessen die eigenen Leute beieinander stehen und nicht zwischen den
    # Gegnern verteilt.
    #
    # Je Zeile: Platz, Name, das **Zeichen** der meistbenutzten Waffe
    # (kein Name - auf zwanzig Pixel passt keiner, und ein Zeichen liest
    # sich schneller), Abschuesse, Tode, das Verhaeltnis der Runde und
    # der, den man am oeftesten erwischt hat.

    def _tafel_zeilen(self) -> list[dict]:
        """Was auf der Siegtafel steht, je Spieler eine Zeile.

        Die Zahlen kommen aus `endwerte` - beim Gastgeber gerechnet, beim
        Gast aus der Endmeldung. Faellt das aus (eine aeltere Gegenstelle
        zum Beispiel), wird aus den Kaempfern gebaut, was noch da ist:
        lieber eine magere Tafel als gar keine.
        """
        zeilen = []
        for nummer, eintrag in sorted((self.endwerte or {}).items(),
                                      key=lambda p: int(p[0])):
            if not isinstance(eintrag, dict):
                continue
            werte = eintrag.get("werte") or {}
            zeilen.append({
                "nummer": int(nummer),
                "name": str(eintrag.get("name")
                            or getattr(self.kaempfer.get(int(nummer)),
                                       "name", "?")),
                "team": int(eintrag.get("team", -1)),
                "abschuesse": int(werte.get("abschuesse", 0)),
                "tode": int(werte.get("tode", 0)),
                "waffe": self._lieblingswaffe(eintrag.get("waffen")),
                "opfer": self._haeufigstes_opfer(eintrag.get("opfer")),
            })
        if not zeilen:
            for k in self.kaempfer.values():
                zeilen.append({"nummer": k.nummer, "name": k.name,
                               "team": k.team, "abschuesse": k.abschuesse,
                               "tode": k.tode, "waffe": "", "opfer": ""})
        zeilen.sort(key=lambda z: (-z["abschuesse"], z["tode"], z["name"]))
        return zeilen

    @staticmethod
    def _lieblingswaffe(waffen) -> str:
        """Womit am meisten geschossen wurde. Leer, wenn mit nichts.

        Gezaehlt wird nach Schuessen und nicht nach Abschuessen: gefragt
        ist, was jemand **benutzt** hat, und wer eine Runde lang mit dem
        Scharfschuetzen danebenhaelt, hat trotzdem mit ihm gespielt.
        """
        if not isinstance(waffen, dict) or not waffen:
            return ""
        bestes, meiste = "", 0
        for name, zahlen in waffen.items():
            if not isinstance(zahlen, dict) or name not in K.WAFFEN:
                continue
            wieviel = int(zahlen.get("schuesse", 0) or 0)
            if wieviel > meiste:
                bestes, meiste = name, wieviel
        return bestes

    def _haeufigstes_opfer(self, opfer) -> str:
        """Wen dieser Spieler am oeftesten erwischt hat."""
        if not isinstance(opfer, dict) or not opfer:
            return ""
        bester, meiste = "", 0
        for nummer, zahl in opfer.items():
            try:
                zahl = int(zahl)
                nummer = int(nummer)
            except (TypeError, ValueError):
                continue
            if zahl <= meiste:
                continue
            eintrag = (self.endwerte or {}).get(str(nummer)) or {}
            name = eintrag.get("name") or getattr(
                self.kaempfer.get(nummer), "name", "")
            if name:
                bester, meiste = str(name), zahl
        return bester

    def _endtafel(self, ziel) -> None:
        # Fast blickdicht. Vorher schimmerten Namen und die ganze Anzeige
        # durch die Tafel, und beides stand quer durch die Zahlen, die man
        # eigentlich lesen wollte.
        deckel = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
        deckel.fill((9, 6, 5, 246))
        ziel.blit(deckel, (0, 0))
        f = SCHRIFT
        farbe_kopf = K.C_AMBER
        if self.mit_teams:
            if 0 <= self.sieger_team < len(K.TEAMS["namen"]):
                kopf = "%s GEWINNT" % K.TEAMS["namen"][self.sieger_team]
                farbe_kopf = K.TEAMS["kombi"][self.sieger_team]["hud"]
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
        f.zeichnen(ziel, kopf, K.GAME_W // 2, 22, farbe_kopf, 3,
                   ausrichtung="mitte")
        if unter:
            f.zeichnen(ziel, unter, K.GAME_W // 2, 48, K.C_MUTED, 1,
                       ausrichtung="mitte")

        zeilen = self._tafel_zeilen()
        if self.mit_teams:
            breite = 300
            hoch = self._tafel_hoehe(max(
                len([z for z in zeilen if z["team"] == 0]),
                len([z for z in zeilen if z["team"] == 1])))
            oben = max(72, (K.GAME_H - hoch) // 2)
            for seite in range(2):
                x = 10 + seite * (K.GAME_W - 2 * 10 - breite)
                self._tafel_spalte(ziel, x, oben, breite,
                                   [z for z in zeilen if z["team"] == seite],
                                   seite)
            ohne = [z for z in zeilen if not 0 <= z["team"] < 2]
            if ohne:
                self._tafel_spalte(ziel, (K.GAME_W - breite) // 2,
                                   oben + hoch + 8, breite, ohne, -1)
        else:
            breite = 360
            oben = max(72, (K.GAME_H - self._tafel_hoehe(len(zeilen))) // 2)
            self._tafel_spalte(ziel, (K.GAME_W - breite) // 2, oben, breite,
                               zeilen, -1)
        f.zeichnen(ziel, "[ESC] BEENDEN", K.GAME_W // 2, K.GAME_H - 20,
                   K.C_MUTED_DK, 1, ausrichtung="mitte")

    @staticmethod
    def _tafel_hoehe(zeilen: int) -> int:
        return 16 + 11 * max(1, zeilen) + 14

    def _tafel_spalte(self, ziel, x: int, y: int, breite: int, zeilen: list,
                      team: int) -> None:
        """Eine Mannschaft als Block: Kopf, Spaltentitel, Zeilen."""
        f = SCHRIFT
        if 0 <= team < len(K.TEAMS["kombi"]):
            kombi = K.TEAMS["kombi"][team]
            hell, dunkel = kombi["hud"], kombi["hud_dunkel"]
            name = kombi["name"]
        else:
            hell, dunkel, name = K.C_CREAM, K.C_MUTED_DK, "ALLE"
        rand = pygame.Rect(x, y, breite, self._tafel_hoehe(len(zeilen)))
        pygame.draw.rect(ziel, (14, 10, 8), rand)
        pygame.draw.rect(ziel, dunkel, rand, 1)
        # Ein voller Balken in der Mannschaftsfarbe ueber dem Block: die
        # Farbe muss man sehen, bevor man einen Namen liest.
        pygame.draw.rect(ziel, hell, (x, y, breite, 2))
        if 0 <= team < len(K.TEAMS["kombi"]):
            self._teamzeichen(ziel, x + 5, y + 6, K.TEAMS["kombi"][team])
        f.zeichnen(ziel, name, x + (16 if team >= 0 else 5), y + 6, hell, 1)

        # Spaltentitel. "K/D" steht fuer die Runde, nicht fuer die
        # Bestenliste - deshalb "RUNDE" darunter und nicht mehr.
        sx = self._tafel_spalten(x, breite)
        kopfzeile = y + 6
        f.zeichnen(ziel, "A", sx["abschuesse"], kopfzeile, dunkel, 1, 1, "rechts")
        f.zeichnen(ziel, "T", sx["tode"], kopfzeile, dunkel, 1, 1, "rechts")
        f.zeichnen(ziel, "K/D", sx["kd"], kopfzeile, dunkel, 1, 1, "rechts")
        f.zeichnen(ziel, "ERLEDIGT", sx["opfer"], kopfzeile, dunkel, 1)

        zy = y + 18
        for platz, z in enumerate(zeilen, 1):
            eigen = (self.ich is not None and z["nummer"] == self.ich.nummer)
            if eigen:
                pygame.draw.rect(ziel, (30, 22, 16), (x + 2, zy - 2,
                                                      breite - 4, 11))
            farbe = hell if eigen else (K.C_CREAM if platz == 1 else K.C_MUTED)
            f.zeichnen(ziel, "%d" % platz, x + 6, zy, dunkel, 1)
            f.zeichnen(ziel, ui.kuerzen(z["name"], sx["waffe"] - x - 20),
                       x + 16, zy, farbe, 1)
            # Nur das Zeichen der Waffe. Ein Name passt nicht, und ein
            # abgeschnittener Name sagt weniger als ein Umriss.
            if z["waffe"]:
                bild = self.renderer.bilder.bild("waffe_" + z["waffe"])
                ziel.blit(bild, (sx["waffe"], zy + 3 - bild.get_height() // 2))
            f.zeichnen(ziel, "%d" % z["abschuesse"], sx["abschuesse"], zy,
                       farbe, 1, 1, "rechts")
            f.zeichnen(ziel, "%d" % z["tode"], sx["tode"], zy, K.C_MUTED, 1,
                       1, "rechts")
            f.zeichnen(ziel, self._kd_text(z), sx["kd"], zy,
                       K.C_MUTED if z["tode"] else K.C_TEAL, 1, 1, "rechts")
            if z["opfer"]:
                f.zeichnen(ziel, ui.kuerzen(z["opfer"], x + breite - 6
                                            - sx["opfer"]),
                           sx["opfer"], zy, K.C_MUTED_DK, 1)
            zy += 11

    @staticmethod
    def _tafel_spalten(x: int, breite: int) -> dict:
        """Wo die Spalten liegen. Einmal gerechnet, zweimal benutzt -
        Kopfzeile und Zeilen muessen uebereinanderstehen."""
        rechts = x + breite - 6
        return {"waffe": rechts - 158, "abschuesse": rechts - 116,
                "tode": rechts - 96, "kd": rechts - 68, "opfer": rechts - 58}

    @staticmethod
    def _kd_text(z: dict) -> str:
        """Abschuesse je Tod. Ohne Tod steht die Zahl allein da."""
        if not z["tode"]:
            return "%d" % z["abschuesse"] if z["abschuesse"] else "-"
        return "%.1f" % (z["abschuesse"] / z["tode"])

    def verlassen(self) -> None:
        if self.ist_gastgeber:
            self.gastgeber.schliessen()
        elif self.gast is not None:
            self.gast.schliessen()
