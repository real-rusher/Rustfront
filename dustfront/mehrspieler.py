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
from .anzeige import RAND_OBEN, RAND_UNTEN, Anzeige
from . import konto as konto_modul
from . import netz
from . import regeln as R
from . import ui
from .lobby import LobbyTeil, lobby_regeln
from .spielerkosmetik import KosmetikTeil
from . import world as welt_modul
from .core import Szene
from .entities import (Aufsammler, Brandflaeche, Gegner, Geschoss, Granate,
                       Rakete, Rauchwolke, Spieler, wolke)
from .font import SCHRIFT
from .render import Befinden, Kamera, Renderer, Ueberblendung
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
        # Die Kennung seines Kontos, wenn er angemeldet ist - damit die
        # Statistik "wen wie oft erledigt" auch dann stimmt, wenn einer
        # seinen Namen aendert. Leer ohne Konto.
        self.konto = ""
        self.wieder_in = 0.0
        self.toeter = None           # wertet das Gefecht aus und raeumt weg
        # Womit der Toeter ihn erwischt hat (seit 0.31). Ein Spieler stirbt
        # erst am Ende der Bodenzeit, lange nach dem Treffer - dann weiss
        # niemand mehr, welche Waffe es war. Gemerkt wird sie darum beim
        # Treffer (entities.abschuss_buchen) und gebucht beim Abrechnen.
        self.toeter_waffe = ""
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
            # Waffe verstaut, das Brecheisen in beiden Haenden (seit
            # 0.32.8 als Bildfolge, siehe art._figur_schwung).
            return self.schwung_bild(vorsatz)
        # Beim Anlegen eines Medkits haelt die Figur das Medkit, nicht die
        # Waffe - fuer alle sichtbar, der Gast bekommt heilt_rest mit.
        gehalten = "medkit" if self.heilt_rest > 0 else self.waffe_name
        name = "spieler_%s%s" % (vorsatz, gehalten)
        return name if name in K.BILD_MASS else super().bild

    # ---- Am Boden statt tot -------------------------------------------
    def sterben(self, von=None) -> None:
        # Ein anderer Toeter, eine andere Waffe. Derselbe (die Bodenzeit
        # ist um) behaelt die, mit der er ihn umgeworfen hat.
        if von is not self.toeter:
            self.toeter_waffe = ""
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
        # In der Lobby entscheidet das Gefecht, wo es wehtut (lobby.py).
        # Gefragt wird die Welt, weil die Figur ihr Gefecht nicht kennt.
        pruefen = getattr(self.welt, "darf_treffen", None)
        if pruefen is not None and not pruefen(self, von):
            return
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
        self.toeter = None           # wer ihn umgeworfen hatte, hat es nicht geschafft
        self.toeter_waffe = ""
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
        # Die Schwierigkeit des Gefechts. Beim Boss steckt sie schon im
        # uebergebenen Leben (siehe _boss_setzen), sonst kommt sie hier
        # dazu. Schaden und Tempo gelten fuer beide.
        stufe = getattr(gefecht, "stufe", None)
        if (stufe is not None and stufe is not K.SCHWIERIGKEIT["normal"]
                and art not in K.UEBUNG):
            self.daten = K.gegner_verstaerkt(self.daten, stufe)
            self.fern = self.daten.get("fern")
            self.platzt = self.daten.get("platzt")
            self.faehigkeit = self.daten.get("faehigkeit")
            if leben is None:
                self.max_leben *= stufe["leben"]
                self.leben = self.max_leben
        self._ziel = None
        self._ziel_rest = 0.0
        # Zielpuppe im Schiessstand: wie lange seit dem letzten Treffer,
        # und was sich an Schaden fuer die naechste Zahl gesammelt hat.
        self.ist_puppe = art in K.UEBUNG
        self._ruhe = 0.0
        self._summe = 0.0
        self._summe_rest = 0.0
        # Haengerwache: bestes bisher erreichtes Naeherkommen und wie
        # lange es sich nicht gebessert hat.
        self._bestes = 1e18
        self._stockt = 0.0
        self._pruef_rest = K.GEGNER_MP["stockt_pruefung"]
        self._ungesehen = 0.0        # so lange schon ausser jeder Sicht

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
        if self.ist_boss or getattr(self._gefecht, "in_lobby", False):
            # In der Lobby bleibt jeder im Gehege - umgesetzt wuerde er
            # irgendwohin auf den Platz, wo er nichts zu suchen hat.
            return
        if self._gefecht.sichtbar_fuer_jemanden(self.pos):
            self._ungesehen = 0.0
        else:
            self._ungesehen += dt
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
        # Wer schon am Ziel ist, haengt nicht. Das fehlte in 0.26: ein
        # Gegner, der neben seinem Ziel stand und zuschlug, kam ja nicht
        # mehr "naeher" - die Wache hielt ihn nach sieben Sekunden fuer
        # festgefahren und setzte ihn weg. Wer stillstand und kaempfte,
        # verlor so regelmaessig seine Angreifer. Dasselbe gilt fuer einen
        # Speier, der im Halteband steht: er soll dort stehen.
        if ziel.ebene == self.ebene:
            nah = self.pos.distance_to(ziel.pos)
            reicht = self.daten["reichweite"] + ziel.radius + 18.0
            if self.fern:
                reicht = max(reicht, self.fern["reichweite"] + 10.0)
            if nah <= reicht:
                self._bestes = nah
                self._stockt = 0.0
                return
        # Auf dem Weg zu einer Treppe zaehlt der Weg dorthin, nicht der
        # Abstand zum Ziel: zur Rampe geht es oft erst einmal weg vom
        # Spieler, und das ist Fortschritt, kein Haenger.
        # Der Modus schliesst die Treppe ein: nach einem Ebenenwechsel geht
        # es zur naechsten, und deren Weg ist laenger als der letzte Rest
        # zur vorigen. Ohne das hielt die Wache genau den Gegner, der gut
        # vorankam, fuer festgefahren und setzte ihn um.
        modus = ("treppe", self.weg_nr, self.ebene) if self.weg_rest >= 0 \
            else ("direkt", -1, self.ebene)
        if modus != getattr(self, "_modus", modus):
            self._bestes = 1e18
            self._stockt = 0.0
        self._modus = modus
        if modus[0] == "treppe":
            weit = float(self.weg_rest * K.TILE)
        else:
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
        if self._ungesehen < g["unsichtbar_ab"]:
            # Haengt, aber jemand sieht ihn (oder sah ihn eben noch). Dann
            # bleibt er stehen, wo er ist - ein Gegner, der sich vor den
            # Augen der Spieler in Luft aufloest, sieht nach Fehler aus.
            return
        ebene, pos = self._gefecht._spawnstelle(bei=ziel)
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
        lobby = getattr(self._gefecht, "in_lobby", False)
        for k in self._gefecht.kaempfer.values():
            if not k.lebt:
                continue
            if lobby and not self._gefecht.im_bereich(k, "pve"):
                continue       # im Gehege jagt er nur, wer drin ist
            if self.ist_boss and k.ebene != self.ebene:
                continue       # ein Boss wartet auf seiner Ebene
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
        if self.ist_puppe:
            self._puppe_schritt(dt)
            return
        vorher = self.welt.held
        self.welt.held = self._ziel_waehlen(dt)
        try:
            super().schritt(dt)
        finally:
            self.welt.held = vorher
        self._haenger_pruefen(dt)
        if getattr(self._gefecht, "in_lobby", False):
            self._gefecht._im_gehege_halten(self)

    # ---- Die Zielpuppe ---------------------------------------------------
    def _puppe_schritt(self, dt: float) -> None:
        """Eine Puppe steht. Sie heilt sich und zeigt, was sie abbekam.

        Nur das Noetigste aus Wesen.schritt: das Aufleuchten beim Treffer
        soll abklingen, bewegt wird nichts.
        """
        self.vorher.update(self.pos)
        self.blitz = max(0.0, self.blitz - dt)
        self._ruhe += dt
        if self._ruhe >= K.LOBBY["puppe_heilt"]:
            self.leben = self.max_leben
        if self._summe > 0.0:
            self._summe_rest -= dt
            if self._summe_rest <= 0.0:
                self._zahl_zeigen(self._summe)
                self._summe = 0.0

    def _zahl_zeigen(self, menge: float) -> None:
        """Eine Zahl ueber der Puppe. Mehrere kurz nacheinander (Schrot,
        Salve) stehen versetzt nebeneinander statt aufeinander."""
        self._zahl_nr = (getattr(self, "_zahl_nr", -1) + 1) % 6
        dx = (-9, 9, 0, -14, 14, 0)[self._zahl_nr]
        dy = (0, 0, -7, -7, -7, -14)[self._zahl_nr]
        self._gefecht.schadenszahl(self.pos, self.ebene, menge, dx, dy)

    def schaden(self, menge, schub=None, von=None) -> None:
        if not self.ist_puppe:
            super().schaden(menge, schub, von)
            return
        # Seit 0.32 eine Zahl je Treffer (gemeldet: "nicht pro Sekunde,
        # sondern wirklich pro Schuss"). Nur Feuer trifft in jedem Schritt
        # mit einem Bruchteil eines Punkts - 120 Zahlen in der Sekunde
        # liest niemand. Was unter einem Punkt liegt, wird darum weiter je
        # Viertelsekunde zusammengezaehlt; ein Schuss liegt immer darueber.
        if float(menge) >= 1.0:
            self._zahl_zeigen(float(menge))
        else:
            if self._summe <= 0.0:
                self._summe_rest = 0.25
            self._summe += float(menge)
        self._ruhe = 0.0
        super().schaden(menge, None, von)

    def sterben(self, von=None) -> None:
        if self.ist_puppe:
            # Eine Puppe faellt nicht um, sie fuellt sich wieder auf.
            self.leben = self.max_leben
            return
        super().sterben(von)


# ══════════════════════════════════════════════════════════════════
# Die Szene
# ══════════════════════════════════════════════════════════════════

def _version_kleiner(a: str, b: str) -> bool:
    """Ist Version a aelter als b? Unlesbares zaehlt als aelter."""
    def teile(v):
        try:
            return tuple(int(x) for x in v.split("."))
        except ValueError:
            return (-1,)
    return teile(a) < teile(b)


class Gefecht(Szene, LobbyTeil, KosmetikTeil):
    """Die Spielszene fuer den LAN-Test, beim Gastgeber wie beim Gast.

    Die Lobby und der Rundenplan stehen in lobby.py (LobbyTeil).
    """

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
                 seed: int | None = None, regeln: dict | None = None,
                 lobby: bool = False, ansagen: bool = False,
                 heimkehr: bool = False) -> None:
        super().__init__(app)
        self.name = netz.name_saeubern(name)
        self.gastgeber = gastgeber
        self.gast = gast
        # Seit 0.32 startet jeder in seiner eigenen Lobby (sitzung.py).
        # `heimkehr`: wer eine fremde Runde verlaesst oder aus ihr fliegt,
        # landet wieder in seiner eigenen Lobby statt vor dem Desktop.
        # Aus nur in den Pruefungen, die ein Gefecht von Hand bauen und
        # danach in Ruhe nachsehen wollen, was der Gast anzeigt.
        self.heimkehr = bool(heimkehr)
        self.wohin = ""              # beim Gast: wohin er verbunden ist
        # `ansagen`: die Lobby beantwortet die Suche aus lan.py. Nur beim
        # Gastgeber, und nicht in den Pruefungen - die sollen keinen
        # festen UDP-Port belegen.
        self.ansager = None
        if ansagen and gastgeber is not None:
            from . import lan
            self.ansager = lan.Ansager()
        # Die Regeln der Runde, als eine Sammlung (siehe regeln.py). Die
        # einzelnen Parameter oben bleiben fuer die Kommandozeile und die
        # Pruefungen; `regeln` ist der Weg fuer Lobby und Rundenplan, die
        # eine ganze Sammlung auf einmal haben. Was davon gesetzt ist,
        # gewinnt, und `saeubern` macht aus beidem eine gueltige Sammlung.
        # Ein Gast bekommt sie mit dem Willkommen und stellt nichts selbst.
        roh = {"modus": modus, "ende_art": ende_art, "knapp": bool(knapp),
               "karte": karte}
        if ende_wert:
            roh["ende_wert"] = float(ende_wert)
        for schluessel, wert in (("schutz", schutz), ("medkits", medkits),
                                 ("medkit_spawn", medkit_spawn),
                                 ("runden", runden), ("loadouts", loadouts),
                                 ("rpg", rpg), ("rpg_lenkung", rpg_lenkung)):
            if wert is not None:
                roh[schluessel] = wert
        if regeln:
            roh.update(regeln)
        self.regelwerk = R.saeubern(roh, self._umfeld())
        # Mit Lobby (der Normalfall beim Aufmachen seit 0.27): was eben
        # zusammengestellt wurde, ist die erste geplante Runde, und
        # angefangen wird in der Lobby. Ohne Lobby geht es sofort los, wie
        # bisher - so laufen die Pruefungen und `--sofort`.
        self._lobby_anlegen(self.regelwerk if gastgeber is not None else None)
        if lobby and gastgeber is not None:
            self.regelwerk = lobby_regeln()
        self._regeln_setzen(self.regelwerk)
        # Gespielte Runden, Unentschieden mitgezaehlt. Die Siege stehen in
        # teampunkte; aus ihnen allein laesst sich nicht ablesen, ob alle
        # Runden durch sind.
        self.runden_gespielt = 0
        self._rpg_takt = K.GEFECHT["rpg_takt"] * 0.4
        # In welche Mannschaft man will: -1 heisst "such mir eine aus".
        self.team_wunsch = int(-1 if team is None else team)
        # Kennwort. Im eigenen Netz meist leer; ueber das Internet ist es
        # das Einzige, was zwischen der Runde und jedem steht, der die
        # Adresse kennt.
        self.passwort = netz.passwort_saeubern(passwort)
        self.abgewiesen = ""         # Grund, falls der Gastgeber absagt
        # Passen die Versionen nicht zusammen: (meine, die des Gastgebers).
        # Dann gibt es kein Gefecht, sondern eine Tafel, die sagt, warum.
        self.versionsfehler: tuple[str, str] | None = None
        # Ein Hinweis, der ein paar Sekunden stehen bleibt. `hinweis` wird
        # beim Gastgeber jedes Bild neu gesetzt - fuer etwas, das einmal
        # passiert (jemand wurde abgewiesen), waere er sofort wieder weg.
        self._meldung = ""
        self._meldung_rest = 0.0

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
        karte = self.regelwerk["karte"]
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
        # Ob die Etage ueber einem gezeichnet wird, wo sie ueber
        # Spielflaeche liegt. Nur hier, nie beim Gastgeber: was einer
        # sieht, ist seine Sache. Jede Partie faengt mit der Vorliebe aus
        # dem Konto an, Q schaltet waehrenddessen um.
        self.obere_zeigen = bool(app.opt["obere_ebenen"])
        self.ich = None
        self.meine_nummer = 0

        # Kennung der laufenden Partie. Der Gastgeber vergibt sie am
        # Rundenende und schickt sie mit; sie ist der Schluessel, unter
        # dem alle Rechner dieselbe Runde ablegen.
        self.partie = ""
        self._gebucht = ""
        self._runde_gebucht = False   # ist die laufende Runde schon gebucht?
        self._zwischenstand = None    # beim Gast: seine letzten Zahlen
        self._seit_zwischenstand = 0.0
        self._spielernamen: dict[int, tuple] = {}   # Nummer -> (Name, Konto)
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
        self.hud = Anzeige(self)
        self._kosmetik_anlegen()
        self._gegner_rest = 0        # beim Gast: so meldet es der Gastgeber
        self._leben_vorher = 0.0
        self._heilte = 0.0
        self._fremde_beute: list[tuple] = []
        self._fremde_gegner: list[tuple] = []
        self._in_wirkung = False      # siehe NETZKLAENGE
        self._knoepfe: set[str] = set()
        self._waffe_wunsch = -1
        self._rad = 0
        # Sichtweite (Mausrad): wohin der Zoom will, und die Flaechen, auf
        # die mit Zoom gezeichnet wird (siehe _zoom_zeichnen).
        self.zoom_ziel = K.ZOOM["start"]
        self._zoom_weich = K.ZOOM["start"]   # der weich nachgezogene Wert
        self._kamera_versatz = pygame.Vector2(0, 0)
        self._leinwand = None
        self._nebel = None
        self._seit_medkit = 0.0
        self._seit_muni = 0.0
        self._letzte_ebene = 0
        self._ueberblendung = Ueberblendung()
        self._ich_zuletzt = pygame.Vector2(0, 0)
        self._flughoehen: dict[int, float] = {}
        # Pausenmenue: None = zu, sonst die gewaehlte Zeile.
        self.menue = None
        self.menue_teams = False
        self.menue_zeile = 0
        self._menue_seit = 0.0
        self._feuer_sperre = False   # siehe _menue_zu
        self._ziel_zuletzt = None    # wohin gezielt wurde, bevor das Menue aufging
        self._zeit = 0.0             # laeuft mit, treibt den Puls des Kreises

        # Der Kreis liegt in der Mitte der Karte. Eine feste Stelle, die
        # alle kennen - das ist der Punkt an dieser Spielart.
        self.kreise = self._kreise_lesen()
        # Spawnmarken der Karte, einmal gelesen. Sie stehen dort als
        # Buchstaben, genau wie die Kreise.
        self._spawnmarken = self._spawnmarken_lesen()
        # Das Wegenetz jetzt bauen, beim Laden, und nicht, wenn der erste
        # Gegner es braucht: auf STAUBTAL kostet es 66 ms, und mitten in
        # einer Welle waere das ein Ruckler. Der Gast rechnet keine Gegner
        # und braucht es nicht.
        if self.ist_gastgeber and self.regeln["gegner"]:
            self.welt.wege
        self.kreis_nr = 0
        self.kreis_rest = K.ZONE["wechsel"]
        self._kreis_setzen(0)

        self._welt_verdrahten()
        self._karte_geladen()
        self.wunsch = self._wunsch_lesen()

        if self.ist_gastgeber:
            # Erst die Seiten festlegen, dann einsteigen - sonst hat der
            # Gastgeber keine Zone und landet irgendwo.
            self._einstiegszonen_waehlen()
            self.ich = self._dazu(0, self.name, self.team_wunsch,
                                  self.mein_loadout())
            self.ich.konto = self._meine_kontokennung()
            self._namen_merken(self.ich)
            if self.in_lobby:
                self._lobby_bestuecken()
        else:
            self.gast.senden({"t": "hallo", "name": self.name,
                              "team": self.team_wunsch,
                              "wort": self.passwort,
                              # Gastgeber und Gast muessen genau dieselbe
                              # Version haben (siehe _version_passt).
                              "version": K.VERSION,
                              # Die Kontokennung (keine Anmeldedaten, nur die
                              # oeffentliche Nummer) - fuer "wen wie oft".
                              "kt": self._meine_kontokennung(),
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
        # Wer wem schaden darf - ausser in der Lobby immer (lobby.py).
        self.welt.darf_treffen = self._darf_treffen
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

    def _blitz(self, pos, ebene: int, von=None) -> bool:
        """Eine Blendgranate ist gezuendet. Blendet sie **mich**?

        Gerechnet wird hier und nicht beim Gastgeber: es ist eine Frage
        des Bildes, nicht des Spiels, und gleiche Lage ergibt auf jedem
        Rechner dieselbe Antwort. Uebertragen werden muss dafuer nichts.
        """
        staerke = welt_modul.blend_wert(pos, ebene, self.ich, self.welt)
        if staerke > 0.0:
            self.befinden.blenden(staerke)
        # Spielerkosmetik des Werfers: sein Ton statt Knall und Pfeifen,
        # sein Bild im Weiss. Gehoert wird der Ton wie der Knall (seit
        # 0.32.7 deutlich leiser, wer weiter weg steht oder wegschaut,
        # blend_ton_wert). Barrierefreiheit, nur bei einem selbst: das
        # fremde Bild und der fremde Ton lassen sich getrennt abschalten.
        laut = welt_modul.blend_ton_wert(pos, ebene, self.ich)
        opt = self.app.opt
        if self.kosmetik_blitz(von, staerke, laut,
                               ton=opt["blendung_ton"] != "standard",
                               bild=opt["blendung"] == "normal"):
            return True
        # Den Knall selbst spielen statt der Welt zu ueberlassen: die
        # kennt nur die gewoehnliche Entfernungsdaempfung.
        if laut > 0.0:
            self.app.klaenge.spielen(K.skin("blend_knall"), laut)
        if staerke > 0.0:
            self.app.klaenge.spielen(K.skin("blend_pfeifen"), 0.35 + 0.5 * staerke)
        return True

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
                          art: str = "spreng", von=None) -> None:
        self._in_wirkung = True
        try:
            Welt.explosion(self.welt, pos, ebene, radius, art, von)
        finally:
            self._in_wirkung = False
        # Als siebtes die Nummer des Werfers - der Gast braucht sie fuer
        # die Spielerkosmetik der Blendgranate. -1, wenn es keinen gibt.
        self._wirkung.append(["x", round(pos.x, 1), round(pos.y, 1),
                              int(ebene), round(radius, 1), str(art),
                              int(getattr(von, "nummer", -1))])

    def schadenszahl(self, pos, ebene: int, menge: float,
                     dx: float = 0.0, dy: float = 0.0) -> None:
        """Eine Zahl ueber einer Puppe: so viel hat es gerade getroffen.

        Beim Gastgeber in die eigene Welt, und als Wirkung an die Gaeste -
        die Puppen stehen bei ihnen ja nur als gemeldete Punkte. `dx`, `dy`
        versetzen sie, damit mehrere Treffer nebeneinander lesbar bleiben.
        """
        text = "%d" % max(1, round(menge))
        oben = pygame.Vector2(pos.x + dx, pos.y - 14 + dy)
        self.welt.aufschrift(oben, ebene, text, K.C_AMBER)
        if self.ist_gastgeber:
            self._wirkung.append(["t", round(oben.x, 1), round(oben.y, 1),
                                  int(ebene), 0, text])

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
            if not isinstance(e, (list, tuple)) or len(e) not in (6, 7):
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
                von = None
                if len(e) == 7 and isinstance(e[6], int) and e[6] >= 0:
                    von = e[6]          # Nummer des Werfers
                self.welt.explosion(pos, ebene, radius, wirkung, von)
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
            elif art == "t":
                # Eine Schadenszahl im Schiessstand. Nur Ziffern: was hier
                # ankommt, steht danach im Bild.
                text = str(e[5])[:6]
                if text.isdigit():
                    self.welt.aufschrift(pos, ebene, text, K.C_AMBER)

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
        """Ob Loadouts gelten - das eigene oder eines fuer alle."""
        return self.loadout_regel in ("eigenes", "gleich")

    def _umfeld(self) -> dict:
        """Was es fuer die Regeln nur hier gibt: Loadouts und Karten.

        Die Loadouts sind die des Gastgebers - aus ihnen waehlt er das eine,
        das bei "eines fuer alle" jeder traegt.
        """
        konto = getattr(self.app, "konto", None)
        return {"loadouts": list(konto.loadouts) if konto is not None else [],
                "karten": welt_modul.karten_liste()}

    def _regeln_setzen(self, d: dict) -> None:
        """Eine Regelsammlung in die Felder des Gefechts uebernehmen.

        Die Felder bleiben, weil der ganze Rest des Gefechts sie liest -
        `self.knapp` an vierzig Stellen durch `self.regelwerk["knapp"]` zu
        ersetzen, braechte nichts ausser Gelegenheiten fuer Tippfehler.
        Die Karte gehoert nicht hierher: sie zu wechseln heisst, eine Welt
        zu laden, und das macht `_karte_wechseln`.
        """
        self.regelwerk = dict(d)
        self.modus = d["modus"]
        self.regeln = K.MODI[self.modus]
        self.ende_art = d["ende_art"]
        self.ende_wert = float(d["ende_wert"])
        self.knapp = bool(d["knapp"])
        self.schutz_an = bool(d["schutz"])
        self.start_medkits = int(d["medkits"])
        self.medkits_spawnen = bool(d["medkit_spawn"])
        self.runden_anzahl = int(d["runden"])
        # Gelten Loadouts? "eigenes": jeder traegt seine zwei Waffen und
        # seine Wurfwaffe. "alles": jeder hat alles. "gleich": alle tragen
        # das eine, das der Gastgeber gewaehlt hat (loadout_nr).
        self.loadout_regel = d["loadouts"]
        self.loadout_nr = int(d["loadout_nr"])
        self.rpg_an = bool(d["rpg"])
        self.rpg_lenkung = bool(d["rpg_lenkung"])
        self.mg_schub = bool(d.get("mg_schub", False))
        for k in getattr(self, "kaempfer", {}).values():
            k.mg_schub = self.mg_schub
        self.schwierigkeit = d["schwierigkeit"]
        self.stufe = K.SCHWIERIGKEIT[self.schwierigkeit]
        self.bosse_an = bool(d["bosse"])
        self.huegel_zeit = float(d["huegel_zeit"])
        self.huegel_verfall = bool(d["huegel_verfall"])

    def _fest_loadout(self) -> dict | None:
        """Das Loadout, das bei "eines fuer alle" jeder traegt.

        Beim Gastgeber aus seinem Konto, mit der Nummer aus den Regeln.
        Gibt es die Nummer nicht mehr - er hat eines geloescht -, nimmt er
        sein gewaehltes; ohne Konto gibt es keines, und dann hat eben
        jeder alles.
        """
        konto = getattr(self.app, "konto", None)
        if konto is None or not konto.loadouts:
            return None
        if 0 <= self.loadout_nr < len(konto.loadouts):
            return dict(konto.loadouts[self.loadout_nr])
        return dict(konto.loadout)

    def _loadout_fuer(self, k, angemeldet=None) -> dict | None:
        """Was ein Kaempfer tragen soll, oder None fuer "alles".

        `angemeldet` ist das Loadout, das ein Gast beim Verbinden
        mitgeschickt hat; beim Gastgeber selbst gilt sein aktuelles.
        """
        if self.loadout_regel == "gleich":
            return self._fest_loadout()
        if self.loadout_regel == "eigenes":
            if k is not None and k is self.ich:
                return self.mein_loadout()
            return angemeldet if angemeldet is not None else getattr(
                k, "loadout", None)
        return None

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
        # Wer noch keine Mannschaft hat - etwa, weil er aus der Lobby kommt,
        # wo es keine gibt -, bekommt zuerst die, die er sich beim
        # Verbinden gewuenscht hat, und sonst die kleinere. Vorher landeten
        # alle erst in der ersten und wurden dann nach Nummer verschoben;
        # der Wunsch ging dabei verloren.
        ohne = []
        for k in leute:
            if 0 <= k.team < anzahl:
                continue
            wunsch = getattr(k, "team_wunsch", -1)
            if 0 <= wunsch < anzahl:
                k.team = wunsch
            else:
                ohne.append(k)
        for k in ohne:
            groessen = [sum(1 for x in leute if x.team == i)
                        for i in range(anzahl)]
            k.team = groessen.index(min(groessen))
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
        angemeldet = dict(loadout) if loadout else None
        if self.loadout_regel == "gleich":
            loadout = self._fest_loadout()
        k = Kaempfer(pos, 0, nummer, netz.name_saeubern(name),
                     self._fraktion_fuer(nummer, team), knapp=self.knapp,
                     team=team,
                     loadout=loadout if self.mit_loadouts else None)
        # Was er selbst mitgebracht hat, bleibt gemerkt - auch in einer
        # Runde, in der alle dasselbe tragen. Danach bekommt er es zurueck.
        k.angemeldet = angemeldet
        # Ebenso sein Mannschaftswunsch: in der Lobby gibt es keine
        # Mannschaften, der Wunsch soll aber in der ersten Teamrunde gelten.
        k.team_wunsch = int(wunsch)
        self._regeln_anlegen(k)
        k.unverwundbar = self.schutz_zeit
        k.medkits = self.start_medkits
        self.kaempfer[nummer] = k
        self.welt.dazu(k)
        self._namen_merken(k)
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
            # Aenderung im Menue ankommt. Bei "eines fuer alle" ist es fuer
            # jeden dasselbe - das eigene bleibt dabei an der Figur
            # gemerkt (`angemeldet`), damit es nach einer solchen Runde
            # wieder da ist.
            lo = self._loadout_fuer(k, getattr(k, "angemeldet", None))
            plaetze = konto_modul.hotbar_aus_loadout(lo) if lo else []
        else:
            lo = None
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
        k.mg_schub = getattr(self, "mg_schub", False)
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
        if self.in_lobby:
            platz = self._lobby_einstieg(ausser)
            if platz is not None:
                return platz
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
        # Der Druck auf E geht zusaetzlich als Ereignis mit. Daran haengen
        # Treppe und Ruf (am Boden) - beides soll genau einmal je Druck
        # passieren, und ein Ereignis geht nie verloren (siehe
        # netz._schlange_kuerzen). Gehalten wird E nur fuer das Aufhelfen.
        if taste in tabelle.get("nutzen", ()):
            self._knoepfe.add("nutzen")
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
            self._knoepfe.add("nutzen")
        for nr in range(1, K.HOTBAR_PLAETZE + 1):
            if e.gedrueckt("waffe%d" % nr):
                self._waffe_wunsch = nr - 1

    def _meine_eingabe(self) -> dict:
        e = self.app.eingabe
        offen = self.pausiert
        if offen and self._ziel_zuletzt is not None:
            # GRUND: Im Menue faehrt die Maus ueber die Eintraege. Folgte
            # die Figur ihr, drehte sie sich dabei wild im Kreis - fuer
            # alle anderen sichtbar, und das Menue sollte gerade *alle*
            # Eingaben vom Spiel fernhalten.
            ziel = self._ziel_zuletzt
        else:
            ziel = self.kamera.zu_welt(e.maus)
            self._ziel_zuletzt = pygame.Vector2(ziel)
        if self._feuer_sperre and not (e.gehalten("feuer") or e.gehalten("zweit")):
            self._feuer_sperre = False
        still = offen or self._feuer_sperre
        meldung = {
            "t": "ein",
            "will": [0.0, 0.0] if offen else [round(v, 2) for v in e.richtung()],
            "ziel": [round(ziel.x, 1), round(ziel.y, 1)],
            "feuert": False if still else e.gehalten("feuer"),
            "zielt": False if still else e.gehalten("zweit"),
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
            # Das Einzige, was man am Boden noch tun kann: rufen - mit
            # demselben Druck auf E, der sonst die Treppe nimmt.
            if self._e_gedrueckt(ein):
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
        gedrueckt = self._e_gedrueckt(ein)
        if not ein.get("nutzen") and not gedrueckt:
            return
        opfer = self._wem_helfen(k) if ein.get("nutzen") else None
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
        # Treppe nehmen: nur auf einen **Druck**, nicht solange E gehalten
        # ist.
        #
        # Bis 0.27 hing die Treppe am gehaltenen Zustand, mit 1,5 s Sperre
        # dazwischen (0.19.0, siehe docs/MEHRSPIELER.md 12.16). Das hielt,
        # solange die Taste wirklich losgelassen wurde. Beim Gast ging das
        # schief: blieb sein E als gehalten stehen - etwa weil das Fenster
        # beim Loslassen den Fokus verloren hatte und das Loslassen nie
        # ankam -, ging er alle anderthalb Sekunden hoch, runter, hoch.
        # Jetzt zaehlt nur das Ereignis "E gedrueckt", das je Druck genau
        # einmal kommt. Die kurze Sperre bleibt gegen einen Doppeldruck.
        if not gedrueckt or k.treppe_rest > 0:
            return
        ziel_ebene = self.welt.treppe_unter(k)
        if ziel_ebene is not None and self.welt.ebene_wechseln(k, ziel_ebene):
            k.treppe_rest = K.GEFECHT["treppe_takt"]
            wolke(self.welt, k.pos, 10, 90, 0.4, K.C_MUTED_DK, k.ebene, 1,
                  "staub")
            self.welt.klang("aufheben", 0.4)

    @staticmethod
    def _e_gedrueckt(ein: dict) -> bool:
        """Steht in dieser Eingabe ein Druck auf E?"""
        knoepfe = ein.get("knoepfe") or []
        return isinstance(knoepfe, list) and "nutzen" in knoepfe

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
        self._meldung_rest = max(0.0, self._meldung_rest - dt)
        if self._meldung_rest > 0:
            self.hinweis = self._meldung
        self.gastgeber.annehmen()
        if self.ansager is not None:
            self.ansager.schritt(self._ansage)

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
                if not self._version_passt(nummer, nachricht):
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
                    k.konto = str(nachricht.get("kt") or "")[:64]
                    self._namen_merken(k)
                    self.gastgeber.an_einen(nummer, self._willkommen(nummer, k))
                    # Und gleich den Plan: wer in die Lobby kommt, soll
                    # sehen, was als Naechstes gespielt wird.
                    self.gastgeber.an_einen(nummer, self._plan_meldung())
                    # Dazu die Spielerkosmetik, die schon da ist.
                    self._kos_neuer_gast(nummer)
            elif art == "ein":
                k = self.kaempfer.get(nummer)
                if k is not None:
                    self._anwenden(k, nachricht)
            elif art in ("kos", "kos_hat", "kos_weg"):
                # Spielerkosmetik - nur von dem, der schon dabei ist.
                if nummer in self.kaempfer:
                    self._kos_vom_gast(nummer, nachricht)

        for nummer in self.gastgeber.gegangen():
            k = self.kaempfer.pop(nummer, None)
            if k is not None:
                k.lebt = False

        if self.ich is not None:
            self._anwenden(self.ich, self._meine_eingabe())
        self._kosmetik_schritt()

        if self.in_lobby:
            # Keine Wellen, keine Beute, kein Ende - nur das Gehege.
            self._lobby_schritt(dt)
        elif not self.vorbei:
            self._beute_nachlegen(dt)
            self._wellen(dt)
            self._zone(dt)
            self._runden(dt)
        self._gegnerlast_zaehlen()
        self._rpg_regeln()
        self.welt.schritt(dt)
        if self.in_lobby:
            self._lobby_munition()        # nach dem Schuss, siehe dort
        self._ziehen(dt)
        self._revive(dt)
        self._tote_abrechnen(dt)
        self._ende_pruefen(dt)
        self._plan_fuehren(dt)

        self._zwischenstand_schicken(dt)
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

    def _ansage(self) -> dict:
        """Was die Lobbysuche ueber diese Runde erfaehrt (lan.py).

        Nur, was man zum Waehlen braucht. Das Kennwort selbst geht nie
        hinaus, nur ob eines gilt.
        """
        return {"name": self.name, "port": self.gastgeber.port,
                "version": K.VERSION, "spieler": len(self.kaempfer),
                # Der Gastgeber zaehlt mit: er ist einer der Spieler, aber
                # keiner der K.NETZ["hoechstens"] Gaeste.
                "hoechstens": K.NETZ["hoechstens"] + 1,
                "lobby": bool(self.in_lobby),
                "modus": K.MODI[self.modus]["name"],
                "karte": self.karte, "passwort": bool(self.passwort)}

    def melden(self, text: str, dauer: float = 4.0) -> None:
        """Ein Hinweis, der ein paar Sekunden stehen bleibt."""
        self._meldung = str(text)
        self._meldung_rest = float(dauer)
        self.hinweis = self._meldung

    def sichtbar_fuer_jemanden(self, pos) -> bool:
        """Liegt die Stelle im Bild irgendeines Spielers?

        Gerechnet mit der groessten Sichtweite und ohne Ebenen: wer auf
        einem Plateau steht, sieht auf den Sand hinunter. Lieber einmal zu
        oft "sichtbar" als ein Gegner, der vor jemandes Augen verschwindet.
        """
        bx, by = K.GEGNER_MP["sicht_halb"]
        for k in self.kaempfer.values():
            if not k.lebt:
                continue
            if abs(k.pos.x - pos.x) < bx and abs(k.pos.y - pos.y) < by:
                return True
        return False

    def _gastgeber_name(self) -> str:
        """Beim Gast: wie der Gastgeber heisst. Er hat immer die Nummer 0."""
        k = self.kaempfer.get(0)
        return k.name if k is not None else ""

    def heim(self, hinweis: str = "") -> None:
        """Zurueck in die eigene Lobby. Ohne `heimkehr`: hinaus wie frueher."""
        if not self.heimkehr:
            self.app.laeuft = False
            return
        from . import sitzung
        if sitzung.eigene_lobby(self.app, hinweis) is None:
            # Kein Port frei - sehr unwahrscheinlich, aber dann lieber
            # sauber zu als ein Fenster ohne Szene.
            print("Keine eigene Lobby moeglich: alle Ports belegt.")
            self.app.laeuft = False

    def _willkommen(self, nummer: int, k: Kaempfer | None) -> dict:
        """Alle Regeln der Runde in einer Nachricht.

        Dieselbe Nachricht geht zweimal hinaus: beim Verbinden an einen
        Gast, und als "neustart" an alle, wenn der Gastgeber im Menue
        etwas geaendert hat. Sie darf darum keinen Gast voraussetzen -
        mit nummer = -1 gilt sie fuer alle.
        """
        # Die Regeln als eine Sammlung (regeln.py) - der Gast saeubert sie
        # mit derselben Tabelle, mit der sie hier gebaut wurden. Eine neue
        # Regel kommt dadurch ohne eine Zeile hier beim Gast an.
        return {"t": "willkommen", "id": nummer,
                "name": k.name if k is not None else "",
                "version": K.VERSION,
                "regeln": dict(self.regelwerk, karte=self.karte)}

    def _version_passt(self, nummer: int, hallo: dict) -> bool:
        """Beim Gastgeber: hat der Neue genau meine Version? Sonst absagen.

        Genau dieselbe, nicht "ungefaehr": Gastgeber und Gast teilen sich
        die Arbeit (der Gast schickt Druecke, der Gastgeber rechnet), und
        ein Fehler, der in einer Version behoben ist, kommt mit der
        anderen zurueck - so war es mit der Treppe in 0.27.0. Lieber gar
        kein Gefecht als eines, in dem sich Fehler einschleichen, die
        keiner mehr nachvollziehen kann.

        Der Grund ist kurz genug fuer die Anzeige alter Gaeste, die noch
        keine eigene Tafel dafuer haben (sie zeigen 24 Zeichen). Ein Gast
        von vor 0.27.1 schickt gar keine Version - auch er wird abgewiesen.
        """
        seine = str(hallo.get("version", "") or "")[:16]
        if seine == K.VERSION:
            return True
        self.gastgeber.an_einen(nummer, {
            "t": "abgelehnt", "grund": "VERSION %s NÖTIG" % K.VERSION,
            "version": K.VERSION, "deine": seine})
        leitung = self.gastgeber.leitungen.get(nummer)
        if leitung is not None:
            leitung.schliessen("Version passt nicht")
        name = netz.name_saeubern(str(hallo.get("name", "GAST")))
        print("Abgewiesen: %s hat Version %s, hier laeuft %s."
              % (name, seine or "vor 0.27.1", K.VERSION))
        self._meldung = "%s ABGEWIESEN: VERSION %s" % (name, seine or "ALT")
        self._meldung_rest = 4.0
        self.hinweis = self._meldung
        return False

    def _version_vom_gastgeber(self, nachricht: dict) -> bool:
        """Beim Gast: hat der Gastgeber genau meine Version?

        Die andere Richtung derselben Pruefung - fuer den Fall, dass der
        Gastgeber der Aeltere ist. Ein Gastgeber von vor 0.27.1 prueft
        selbst nicht und schickt keine Version; dann sagt der Gast ab.
        """
        seine = str(nachricht.get("version", "") or "")[:16]
        if seine == K.VERSION:
            return True
        self._version_falsch(seine)
        return False

    def _version_falsch(self, beim_gastgeber: str) -> None:
        self.versionsfehler = (K.VERSION, beim_gastgeber)
        self.abgewiesen = "FALSCHE VERSION"
        print("Falsche Version: du hast %s, der Gastgeber %s. Beide brauchen "
              "denselben Stand." % (K.VERSION, beim_gastgeber or "eine aeltere"))
        self.gast.schliessen()

    def _versionsfehler_zeichnen(self, ziel) -> None:
        """Die Tafel, wenn die Versionen nicht passen.

        Vorher stand bei jeder Absage eine Zeile "ABGEWIESEN: ..." unten im
        Bild, ueber einer leeren Testkarte. Bei einer falschen Version
        reicht das nicht: man muss wissen, **wer** die andere hat und was
        jetzt zu tun ist.
        """
        meine, seine = self.versionsfehler
        f = SCHRIFT
        ui.schleier(ziel, 225)
        r = pygame.Rect(K.GAME_W // 2 - 200, K.GAME_H // 2 - 78, 400, 156)
        ui.kasten(ziel, r, K.C_RED, (14, 9, 7), 5)
        mitte = r.centerx
        f.zeichnen(ziel, "FALSCHE VERSION", mitte, r.y + 12, K.C_RED, 2,
                   ausrichtung="mitte")
        f.zeichnen(ziel, "DU HAST", mitte - 60, r.y + 44, K.C_MUTED, 1,
                   ausrichtung="mitte")
        f.zeichnen(ziel, meine, mitte - 60, r.y + 56, K.C_CREAM, 2,
                   ausrichtung="mitte")
        f.zeichnen(ziel, "DER GASTGEBER", mitte + 60, r.y + 44, K.C_MUTED, 1,
                   ausrichtung="mitte")
        f.zeichnen(ziel, seine or "ÄLTER", mitte + 60, r.y + 56, K.C_AMBER, 2,
                   ausrichtung="mitte")
        if not seine or _version_kleiner(seine, meine):
            rat = "DER GASTGEBER MUSS SEIN SPIEL AKTUALISIEREN."
        else:
            rat = "DU MUSST DEIN SPIEL AKTUALISIEREN."
        f.zeichnen(ziel, "GASTGEBER UND GAST BRAUCHEN GENAU DIESELBE VERSION.",
                   mitte, r.y + 86, K.C_CREAM, 1, ausrichtung="mitte")
        f.zeichnen(ziel, rat, mitte, r.y + 100, K.C_AMBER, 1,
                   ausrichtung="mitte")
        f.zeichnen(ziel, "NEUESTER STAND: ZWEIG MULTIPLAYER-TEST",
                   mitte, r.y + 114, K.C_MUTED, 1, ausrichtung="mitte")
        f.zeichnen(ziel, "[ESC] ZURÜCK", mitte, r.bottom - 16, K.C_MUTED_DK, 1,
                   ausrichtung="mitte")

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
                self.hinweis = "NÄCHSTE WELLE IN %d" % max(1, int(self.pause_rest) + 1)
            return
        self._welle_starten()

    def _welle_starten(self) -> None:
        w = K.WELLEN_MP
        stufe = self.stufe
        self.welle += 1
        self.pause_rest = stufe["pause"]
        # Nach jeder Welle steht wieder jeder auf. Das ist der Ausgleich
        # dafuer, dass eine Runde sonst mit dem ersten Fehler kippt.
        for k in self.kaempfer.values():
            if k.am_boden:
                k.aufhelfen()
        lebende = max(1, sum(1 for k in self.kaempfer.values() if k.lebt))
        anzahl = int(w["grund"] * stufe["anzahl"]
                     * (1.0 + w["je_welle"] * (self.welle - 1))
                     * (1.0 + w["je_spieler"] * (lebende - 1)))
        anzahl = max(1, min(w["hoechstens"], anzahl))

        # Ohne Bosse bleibt die Welle eine gewoehnliche, in voller Staerke.
        # Sie faellt nicht aus: wer Bosse abschaltet, will weiterspielen,
        # nicht eine Pause geschenkt bekommen.
        self.boss_welle = (self.bosse_an and self.welle >= w["boss_ab"]
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
        # Auf ALBTRAUM kommen neue Arten frueher, nie aber vor Welle 1.
        frueher = self.stufe.get("frueher", 0)
        for e in K.MISCHUNG:
            ab = max(1, e["ab"] - frueher)
            if self.welle < ab:
                continue
            g = e["gewicht"] + e.get("steigt", 0.0) * (self.welle - ab)
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
        leben = (K.BOSSE[art]["leben"] * self.stufe["boss"]
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
    def _spawnstelle(self, boss: bool = False, bei=None):
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
        # `bei`: um einen bestimmten Spieler, etwa den, dem ein umgesetzter
        # Gegner nachlief - sonst landete er beim anderen Ende der Karte und
        # jagte ploetzlich jemand anderen.
        wer = bei if (bei is not None and bei in anker) else self.rnd.choice(anker)
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
            # Mit Loechern als Wand: `frei()` allein haelt ein Loch fuer
            # freien Platz. Auf STAUBTAL ist die obere Ebene ausserhalb der
            # Plateaus nur Loch - und dort entstanden Gegner in der Luft,
            # die nicht fallen koennen und nie irgendwo ankamen.
            if not self.welt.frei(p, 14, ebene, True):
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
            if self.welt.frei(p, 14, ebene, True):
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

    @property
    def zone_faktor(self) -> float:
        """Wie viel schneller oder langsamer der Kreis laedt als bis 0.26.

        Die Haltezeit ist die Zeit, die einer allein ohne Gegenwehr
        braucht. Bis 0.26 waren das bis / je_sekunde = gut 14 Sekunden.
        """
        z = K.ZONE
        return (z["bis"] / z["je_sekunde"]) / max(1.0, self.huegel_zeit)

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

        # Der Verfall im selben Verhaeltnis wie das Laden (siehe
        # ZONE["haltezeit"]), und gar keiner, wenn der Gastgeber ihn
        # abgeschaltet hat: dann bleibt jeder Stand, bis er voll ist.
        verfall = (z["verfall"] * self.zone_faktor
                   if self.huegel_verfall else 0.0)
        hoechste = max(drin)
        if hoechste == 0 or drin.count(hoechste) > 1:
            # Niemand drin, oder Gleichstand: der Stand verfaellt langsam.
            self.zone_halter = -1
            for i in range(len(self.zone_stand)):
                self.zone_stand[i] = max(0.0, self.zone_stand[i]
                                         - verfall * dt)
            return

        halter = drin.index(hoechste)
        self.zone_halter = halter
        mehrheit = hoechste - max(
            [d for i, d in enumerate(drin) if i != halter] or [0])
        tempo = self.zone_faktor * min(
            z["hoechstens"], z["je_sekunde"] + z["je_kopf"] * (mehrheit - 1))
        self.zone_stand[halter] = min(z["bis"],
                                      self.zone_stand[halter] + tempo * dt)
        for i in range(len(self.zone_stand)):
            if i != halter:
                self.zone_stand[i] = max(0.0, self.zone_stand[i]
                                         - verfall * dt)
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
                    if k.toeter_waffe:
                        # Je Waffe. Die Summe "abschuesse" kommt weiter aus
                        # toeter.abschuesse (werte_runde) - dieses zaehlen
                        # aendert sie nicht, es fuellt nur die Waffenzeile.
                        toeter.zaehlen("abschuesse", 1.0, k.toeter_waffe)
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
                k.toeter_waffe = ""
                k.tode += 1
                k.serie = 0          # der eigene Tod beendet die Folge
                k.wieder_in = (K.LOBBY["wieder_nach"] if self.in_lobby
                               else K.GEFECHT["wieder_nach"])
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
        if self.vorbei or not self.kaempfer or self.in_lobby:
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
        return {str(k.nummer): self._werte_von(k) for k in self.kaempfer.values()}

    def _werte_von(self, k) -> dict:
        """Die Zahlen eines Kaempfers, so wie sie gebucht werden."""
        return {"werte": k.werte_runde(), "waffen": k.waffen_runde(),
                "team": k.team, "name": k.name, "opfer": self._opfer_liste(k)}

    def _namen_merken(self, k) -> None:
        """Name und Konto je Nummer, auch fuer die, die schon gegangen sind:
        wer einen erledigt hat, der danach geht, soll ihn trotzdem in seiner
        Statistik behalten."""
        self._spielernamen[k.nummer] = (k.name, getattr(k, "konto", ""))

    def _opfer_liste(self, k) -> list:
        """Wen er wie oft erledigt hat - mit Namen und Konto statt Nummer.
        Die Nummer gilt nur in diesem Gefecht, der Name und das Konto
        auch danach."""
        raus = []
        for nummer, anzahl in sorted(k.opfer.items()):
            if anzahl <= 0:
                continue
            name, konto = self._spielernamen.get(nummer, ("", ""))
            if not name:
                name = getattr(self.kaempfer.get(nummer), "name", "") or "?"
            raus.append({"name": name, "konto": konto, "anzahl": int(anzahl)})
        return raus[:64]

    def _meine_kontokennung(self) -> str:
        konto = getattr(self.app, "konto", None)
        if konto is not None and konto.angemeldet:
            return str(konto.kennung or "")[:64]
        return ""

    def _runde_buchen(self, werte=None, abgebrochen: bool = False,
                      partie: str = "") -> None:
        """Die eigene Runde ins Journal des Kontos schreiben.

        Genau einmal je Runde, und nur die eigene Figur. `partie` kommt
        vom Gastgeber; ohne sie wird nicht gebucht, denn eine Runde ohne
        gemeinsame Kennung waere die eine, die doppelt zaehlen koennte.

        `abgebrochen`: die Runde endete nicht regulaer - Fenster zu,
        Verbindung weg, der Gastgeber hat abgebrochen (siehe
        _abbruch_buchen). Sie wird trotzdem hochgeladen, mit allem, was
        bis dahin gezaehlt war, aber als "abgebrochen" markiert: keine
        Runde, kein Sieg, sondern ein Abbruch. So bleibt "Abschuesse je
        Runde" richtig, und wer will, kann die Abbrueche trotzdem sehen.

        Jede Zeile traegt die Version, mit der gespielt wurde: wird spaeter
        etwas ausbalanciert, lassen sich die Zahlen davor und danach
        auseinanderhalten.
        """
        konto = getattr(self.app, "konto", None)
        partie = partie or self.partie
        if konto is None or self.ich is None or not partie:
            return
        if partie == self._gebucht or self._runde_gebucht:
            return
        self._gebucht = partie
        self._runde_gebucht = True
        if werte is None:
            werte = (self._werte_von(self.ich) if self.ist_gastgeber
                     else (self._zwischenstand or self._werte_von(self.ich)))
        zahlen = dict(werte.get("werte") or {})
        art = K.MODUS_ART.get(self.modus, "")
        if art in ("pvp", "pve"):
            zahlen["schuesse_" + art] = zahlen.get("schuesse", 0)
            zahlen["treffer_" + art] = zahlen.get("treffer", 0)
        zahlen["spielzeit"] = round(self._rundenzeit, 1)
        if abgebrochen:
            gewonnen = False
            zahlen["runden"] = 0
            zahlen["siege"] = 0
            zahlen["abgebrochen"] = 1
        else:
            sieger = self.sieger_team
            gewonnen = (self.gewonnen if not self.mit_teams
                        else (sieger >= 0 and sieger == werte.get("team", -1)))
            zahlen["runden"] = 1
            zahlen["siege"] = 1 if gewonnen else 0
        opfer = werte.get("opfer")
        konto.runde_eintragen({
            "partie": partie, "modus": self.modus,
            "gastgeber": self.ist_gastgeber, "gewonnen": bool(gewonnen),
            "team": int(werte.get("team", -1)),
            "werte": zahlen, "waffen": dict(werte.get("waffen") or {}),
            "version": K.VERSION,
            "ende": "abgebrochen" if abgebrochen else "regulaer",
            "opfer": list(opfer)[:64] if isinstance(opfer, list) else [],
        })

    @property
    def runde_laeuft(self) -> bool:
        """Laeuft eine Runde, die bei einem Abbruch gebucht werden muss?"""
        return (not self.in_lobby and not self.vorbei and not self._runde_gebucht
                and self._rundenzeit >= K.GEFECHT["abbruch_ab"])

    def _abbruch_buchen(self) -> None:
        """Die laufende Runde endet vor ihrer Zeit. Trotzdem buchen.

        Beim Gastgeber fuer alle: jeder Gast bekommt seine Zahlen und eine
        gemeinsame Kennung, wie beim regulaeren Ende. Beim Gast nur fuer
        sich, mit dem letzten Zwischenstand, den der Gastgeber geschickt
        hat - er selbst rechnet ja nichts.
        """
        if not self.runde_laeuft:
            return
        partie = "abbruch-" + ablage.kennung()
        if self.ist_gastgeber:
            try:
                self.gastgeber.an_alle({"t": "abbruch", "partie": partie,
                                        "werte": self._werte_aller()})
                self.gastgeber.spuelen()
            except OSError:
                pass
        self._runde_buchen(None, abgebrochen=True, partie=partie)

    def _zwischenstand_schicken(self, dt: float) -> None:
        """Jedem Gast alle paar Sekunden seine Zahlen.

        Damit er bei einem Abbruch, den der Gastgeber nicht mehr melden
        kann - Verbindung weg, eigenes Fenster zu -, trotzdem etwas zu
        buchen hat.
        """
        if self.in_lobby or self.vorbei:
            return
        self._seit_zwischenstand += dt
        if self._seit_zwischenstand < K.GEFECHT["zwischenstand_takt"]:
            return
        self._seit_zwischenstand = 0.0
        for k in self.kaempfer.values():
            if k is not self.ich:
                self.gastgeber.an_einen(k.nummer, {"t": "stand",
                                                   "w": self._werte_von(k)})

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
            # Alles, was fliegt - erkannt an der Art und **nicht** am
            # Bildnamen. Frueher stand hier eine Liste von Namen
            # ("geschoss", "granate", "rauchgranate"), und seit Molotow,
            # Blendgranate und Rakete eigene Bilder haben (Skins), kamen
            # sie beim Gast nie an: er sah nur die Explosion (gemeldet in
            # 0.30). Der Name geht als Bild mit, wie er ist.
            if isinstance(w, (Geschoss, Granate, Rakete)):
                name = getattr(w, "bild", None) or "geschoss"
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
                "gr": self.gegner_rest,
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
        if self.versionsfehler is not None:
            self.hinweis = ""
            return
        if self.abgewiesen:
            self.hinweis = "ABGEWIESEN: %s  [ESC]" % self.abgewiesen
            if self.heimkehr:
                self.heim("ABGEWIESEN: %s" % self.abgewiesen)
            return
        if not self.gast.offen:
            self.hinweis = "VERBINDUNG VERLOREN  [ESC]"
            self._abbruch_buchen()          # mit dem letzten Zwischenstand
            if self.heimkehr:
                # Der Gastgeber hat aufgehoert oder die Leitung ist weg.
                # Zurueck in die eigene Lobby, mit dem Grund obendrauf.
                self.heim("VERBINDUNG ZU %s VERLOREN"
                          % (self._gastgeber_name() or "DER LOBBY"))
            return

        # Vor dem Lesen der Post hochgezaehlt, nicht danach: eine
        # Meldung setzt die Uhr auf null, und dann soll die Ueberblendung
        # bei null anfangen und nicht schon bei der Haelfte stehen.
        self._seit_paket += dt

        for nachricht in self.gast.holen():
            art = nachricht.get("t")
            if art in ("willkommen", "neustart"):
                if not self._version_vom_gastgeber(nachricht):
                    return
                if art == "neustart":
                    # War die alte Runde noch nicht gebucht (ein Gastgeber
                    # von vor 0.31 schickt kein "abbruch"), ist das ihr
                    # Abbruch. Vor dem Lesen der neuen Regeln: danach
                    # stuende schon der neue Modus da, und die Runde
                    # landete unter dem falschen.
                    self._abbruch_buchen()
                self._willkommen_lesen(nachricht)
                # Aufgenommen: ab jetzt darf die eigene Kosmetik hinaus.
                self._kos_zugelassen = True
                if art == "neustart":
                    # Der Gastgeber hat die Regeln gewechselt. Alles, was
                    # von der alten Runde noch herumliegt, kommt weg.
                    self._runde_gebucht = False
                    self._zwischenstand = None
                    self._rundenzeit = 0.0
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
                    self.obere_zeigen = bool(self.app.opt["obere_ebenen"])
            elif art == "welt":
                self._welt_uebernehmen(nachricht)
            elif art == "stand":
                w = nachricht.get("w")
                if isinstance(w, dict):
                    self._zwischenstand = w
            elif art == "abbruch":
                # Der Gastgeber hat die Runde vor ihrem Ende beendet. Er
                # schickt die Zahlen und eine gemeinsame Kennung mit.
                alle = nachricht.get("werte")
                meine = alle.get(str(self.meine_nummer)) if isinstance(alle, dict) else None
                if self.runde_laeuft or (not self._runde_gebucht and not self.vorbei
                                         and not self.in_lobby):
                    self._runde_buchen(meine if isinstance(meine, dict) else None,
                                       abgebrochen=True,
                                       partie=str(nachricht.get("partie") or "")[:64])
            elif art == "plan":
                self._plan_lesen(nachricht)
            elif art in ("kos", "kos_index"):
                self._kos_beim_gast(nachricht)
            elif art == "abgelehnt":
                # Gemerkt und nicht nur angezeigt: der Gastgeber legt
                # gleich darauf auf, und im naechsten Bild wuerde sonst
                # "Verbindung verloren" daraus - die Meldung, die am
                # wenigsten erklaert.
                if "version" in nachricht:
                    # Abgesagt wegen der Version: eigene Tafel statt Zeile.
                    self._version_falsch(str(nachricht.get("version", ""))[:16])
                    return
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
        if self.gast.offen:
            self._kosmetik_schritt()

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
        try:
            nummer = int(nachricht.get("id", 0))
        except (TypeError, ValueError):
            nummer = -1
        if nummer >= 0:
            self.meine_nummer = nummer
        d = R.saeubern(nachricht.get("regeln"))
        self._regeln_setzen(d)
        if not self._karte_wechseln(d["karte"]):
            # Der Gastgeber bestimmt die Karte. Wer sie nicht hat, bleibt
            # auf der alten - dann stimmt zwar nichts mehr, aber er fliegt
            # wenigstens nicht heraus, und der Hinweis sagt es.
            self.hinweis = "KARTE %s FEHLT" % d["karte"].upper()

    def _karte_wechseln(self, name: str) -> bool:
        """Auf eine andere Karte wechseln, beim Gastgeber wie beim Gast.

        Gibt zurueck, ob die Karte jetzt gilt. Stand vorher zweimal da,
        und beide Male unvollstaendig: beim Gast fehlte der Rueckweg auf
        die eingebaute Karte (ein leerer Name wurde uebergangen), und die
        Kaempfer blieben in der alten Welt - auf der neuen Karte waren
        dann alle Mitspieler unsichtbar. In der Lobby wird die Karte mit
        jeder Runde gewechselt; dort waere das sofort aufgefallen.
        """
        name = str(name or "")
        if name == self.karte and self.welt is not None:
            return True
        if name:
            gelesen, kopf = welt_modul.karte_lesen(name)
            if gelesen is None:
                return False
        else:
            gelesen, kopf = testkarte(), {}
        self.welt = gelesen
        self.karte, self.karte_kopf = name, kopf
        self._welt_verdrahten()
        self.kreise = self._kreise_lesen()
        self._kreis_setzen(0)
        # Die Spawnmarken und das Wegenetz gehoeren zur Karte. Stand hier
        # einmal nicht - und nach einem Kartenwechsel kamen die Gegner an
        # den Marken der alten Karte heraus. Das Wegenetz braucht nur, wer
        # Gegner rechnet.
        self._spawnmarken = self._spawnmarken_lesen()
        if self.ist_gastgeber and self.regeln["gegner"]:
            self.welt.wege
        # Alles, was auf der alten Karte stand, gehoert nicht auf die neue
        # - die Kaempfer aber schon.
        for k in self.kaempfer.values():
            self.welt.dazu(k)
        self._karte_geladen()
        return True

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
        self._gegner_rest = int(meldung.get("gr", 0))
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
            # Welche Waffen die Figur ueberhaupt traegt. Die Liste ging seit
            # 0.27 schon mit (fuer Magazin und Vorrat), wurde aber nie
            # uebernommen: mit eigenem Loadout zeigte die Hotbar des Gastes
            # alle neun Waffen, obwohl er nur drei hatte - und ein Druck auf
            # Platz 5 waehlte beim Gastgeber eine ganz andere. Sie enthaelt
            # auch den Raketenwerfer, wenn er getragen wird.
            namen = eintrag.get("wl")
            if (isinstance(namen, list) and namen and namen != k.waffen
                    and all(isinstance(n, str) and n in K.WAFFEN
                            for n in namen)):
                k.waffen = list(namen)
                for n in namen:
                    k.magazin.setdefault(n, 0)
                    k.vorrat.setdefault(n, 0)
                k.waffe = min(k.waffe, len(namen) - 1)
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

        if not self.ist_gastgeber and self.plan_weiter > 0:
            # Beim Gast nur Anzeige: die Zahl auf der Siegtafel soll
            # herunterzaehlen, auch wenn keine neue Meldung kommt.
            self.plan_weiter = max(0.0, self.plan_weiter - dt)
        if self.ich is None:
            return
        if not self.ist_gastgeber:
            self._eigenes_zielen()
        self._bereich_melden()
        self._befinden_fuehren(dt)
        self._ueberblendung.schritt(dt)
        if self.ich.ebene != self._letzte_ebene:
            self._letzte_ebene = self.ich.ebene
            self.blick = self.ich.ebene
            self.blick_rest = 0.0
            if self.ich.flug <= 0:
                # Treppe, Luke, Aufzug: sofort dort, das alte Bild blendet
                # aus (K.EBENENWECHSEL). Ein Sturz sinkt weiter mit.
                self.blick_hoehe = float(self.welt.hoehe(self.ich.ebene))
                self._ueberblendung.starten()
                # Der Aufzug setzt eine Kachel weiter ab. Die Kamera geht
                # den Schritt mit, damit die Figur im Bild stehen bleibt
                # und nur die Umgebung ueberblendet - sonst huepfte sie.
                sprung = self.ich.pos - self._ich_zuletzt
                if sprung.length_squared() <= (2 * K.TILE) ** 2:
                    self.kamera.pos += sprung
        self._ich_zuletzt.update(self.ich.pos)
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
            self.hinweis = ("ANSICHT EBENE %d - ZURÜCK IN %.0f"
                            % (self.blick, self.blick_rest + 0.9))
        ebene = self.welt.ebene(self.ich.ebene)
        # Die Einstellung greift bei jedem Bild neu: wer das Wackeln
        # im Pausenmenue abschaltet, sieht es sofort stehen.
        self.kamera.anteil = self.app.opt.ruckel_anteil()
        self.kamera.vorausschau = self.app.opt.blick_weite()
        # Der Zoom zieht weich nach - ein Sprung auf die doppelte Weite
        # in einem Bild verliert einen voellig.
        z = self._zoom_weich
        z += (self.zoom_ziel - z) * min(1.0, K.ZOOM["weich"] * dt)
        self._zoom_weich = self.zoom_ziel if abs(self.zoom_ziel - z) < 0.004 else z
        # Gezeichnet wird in Stufen von 1/40. GRUND: Die Leinwand ist
        # 640 x 360 mal Zoom, gerundet - und bei jedem anderen Zoom ergab
        # das Rundungen in Breite und Hoehe, die nicht zueinander passten.
        # Beim Zoomen wechselte das Seitenverhaeltnis darum in jedem Bild
        # ein wenig, und das Bild wackelte zur Seite und nach oben. Bei
        # Vielfachen von 1/40 ist die Leinwand 16 x 9 Pixel genau.
        self.kamera.zoom = round(self._zoom_weich * 40.0) / 40.0
        if not self.pausiert:
            # Im Menue faehrt die Maus ueber die Eintraege - die Kamera
            # soll ihr dabei nicht folgen.
            self._kamera_versatz = ((self.app.eingabe.maus
                                     - pygame.Vector2(K.GAME_W / 2, K.GAME_H / 2))
                                    * self.kamera.zoom)
        self.kamera.schritt(dt, self.ich.pos, self.ich.ziel,
                            (ebene.pixel_breite, ebene.pixel_hoehe),
                            versatz=self._kamera_versatz)

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
        if self.pausiert:
            return                  # im Menue zielt man nicht (_meine_eingabe)
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
        """Die Eintraege, wie sie gerade gelten. Je nach Rolle und Ort.

        Seit 0.32 nur noch Taten, keine Regelzeilen. GRUND: Bis dahin
        stand beim Gastgeber jede Regel der Runde hier (beim Huegel
        neunzehn Zeilen) - dieselben, die auch die Rundentafel (P) stellt.
        Zwei Stellen fuer dasselbe, und die laengere davon im Weg, wenn man
        nur weiterspielen will. Die naechste Runde stellt man jetzt an
        einer Stelle ein: NAECHSTE RUNDE oeffnet die Tafel.
        """
        eintraege = [("weiter", "WEITER", "")]
        konto = getattr(self.app, "konto", None)
        if self.in_lobby:
            if self.ist_gastgeber:
                if self.kos_index:
                    da, noetig = self.kosmetik_stand()
                    eintraege.append(("starten_kos", "STARTEN MIT KOSMETIK",
                                      "BEREIT" if da >= noetig
                                      else "LÄDT %d/%d" % (da, noetig)))
                    eintraege.append(("starten", "STARTEN OHNE KOSMETIK",
                                      R.kurz(self.plan[0], self._umfeld())))
                else:
                    eintraege.append(("starten", "RUNDE STARTEN",
                                      R.kurz(self.plan[0], self._umfeld())))
                eintraege.append(("planen", "RUNDE EINSTELLEN", ""))
            else:
                eintraege.append(("planen", "NÄCHSTE RUNDE ANSEHEN", ""))
        elif self.ist_gastgeber:
            eintraege.append(("planen", "NÄCHSTE RUNDE EINSTELLEN", ""))
            eintraege.append(("neu", "RUNDE NEU STARTEN", ""))
            if self.mit_teams:
                eintraege.append(("teams", "MANNSCHAFTEN", ""))
        else:
            eintraege.append(("planen", "NÄCHSTE RUNDE ANSEHEN", ""))
        eintraege.append(("ausruestung", "AUSRÜSTUNG",
                          konto.loadout["name"] if konto else ""))
        eintraege.append(("konto", "KONTO",
                          konto.name.upper() if konto and konto.angemeldet
                          else "NICHT ANGEMELDET"))
        eintraege.append(("einstellungen", "EINSTELLUNGEN", ""))
        if self.in_lobby:
            # Von Lobby zu Lobby (seit 0.32): beitreten geht aus jeder
            # Lobby, auch aus einer fremden - man steigt dann direkt um.
            eintraege.append(("suchen", "ANDERER LOBBY BEITRETEN", ""))
            if not self.ist_gastgeber:
                eintraege.append(("raus", "LOBBY VERLASSEN",
                                  "IN DEINE LOBBY" if self.heimkehr else ""))
        elif self.ist_gastgeber:
            # GRUND: Der Gastgeber ist der Server. Geht er allein, ist die
            # Runde fuer alle vorbei - "Gefecht verlassen" heisst bei ihm
            # darum: alle zusammen zurueck in die Lobby.
            eintraege.append(("lobby", "GEFECHT VERLASSEN", "ALLE IN DIE LOBBY"))
        else:
            eintraege.append(("raus", "GEFECHT VERLASSEN",
                              "IN DEINE LOBBY" if self.heimkehr else ""))
        eintraege.append(("beenden", "SPIEL BEENDEN", self._beenden_wohin()))
        return eintraege

    def _beenden_wohin(self) -> str:
        """Wohin SPIEL BEENDEN fuehrt: vom Hauptmenue gestartet dorthin."""
        return "ZUM HAUPTMENÜ" if getattr(self.app, "hauptmenue", False) else ""

    def _menue_auf(self) -> None:
        self.menue = 0
        self.menue_teams = False
        self.menue_zeile = 0
        # Ab wann die Eintraege aufklappen (siehe _menue_zeichnen).
        self._menue_seit = self._zeit
        # Nichts soll weiterlaufen, was man vor dem Aufmachen gedrueckt hat.
        self._knoepfe.clear()
        self._waffe_wunsch = -1

    def _menue_zu(self) -> None:
        self.menue = None
        self.menue_teams = False
        # GRUND: Wer WEITER anklickt, hat die linke Maustaste noch unten,
        # wenn das Menue zugeht - und die ist der Abzug. Ohne Sperre ging
        # mit dem Klick auf WEITER der erste Schuss los. Sie faellt, sobald
        # beide Maustasten einmal oben waren (_meine_eingabe).
        self._feuer_sperre = True

    def ereignis(self, ev) -> None:
        if self.menue is not None and self.versionsfehler is None and ev.type in (
                pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEWHEEL):
            # Im Menue gehoert die Maus dem Menue und nichts davon dem
            # Spiel: kein Zoom, kein Schuss, kein Zielen (siehe pausiert).
            self._menue_maus(ev)
            return
        if ev.type == pygame.MOUSEWHEEL and self.menue is None:
            # Das Rad aendert die Sichtweite; mit Strg wie frueher die
            # angeschaute Ebene.
            if pygame.key.get_mods() & pygame.KMOD_CTRL:
                self._rad += ev.y
            elif ev.y:
                self.zoom_stufe(-1 if ev.y > 0 else 1)
            return
        if ev.type != pygame.KEYDOWN:
            return
        if self.versionsfehler is not None:
            # Hier gibt es nichts mehr zu spielen: Esc fuehrt hinaus,
            # nicht ins Pausenmenue hinter der Tafel.
            if ev.key in self.app.opt.codes("pause"):
                self.heim("FALSCHE VERSION - NICHT BEIGETRETEN")
            return
        if self.menue is None:
            self._knopf_merken(ev.key)
            if ev.key in self.app.opt.codes("ebenen"):
                self.obere_umschalten()
            if ev.key in self.app.opt.codes("ansicht_hoch"):
                self._rad += 1
            if ev.key in self.app.opt.codes("ansicht_runter"):
                self._rad -= 1
            if ev.key in self.app.opt.codes("planen"):
                self.planung_oeffnen()
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

    def obere_umschalten(self) -> None:
        """Q: die Etage darueber ein- oder ausblenden.

        Geht nicht zum Gastgeber - es aendert nur, was man selbst sieht.
        Der Hinweis sagt, was jetzt gilt; ohne ihn weiss man nach einem
        Druck auf einer Karte ohne Obergeschoss nicht, ob er ankam.
        """
        self.obere_zeigen = not self.obere_zeigen
        self.hinweis = ("OBERE EBENEN SICHTBAR" if self.obere_zeigen
                        else "OBERE EBENEN AUSGEBLENDET")
        self.app.klaenge.spielen("menue", 0.3)

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
    TATEN = ("weiter", "raus", "teams", "neu", "ausruestung", "konto",
             "planen", "starten", "starten_kos", "lobby", "suchen",
             "beenden", "einstellungen")

    def _menue_wirken(self, schluessel: str, vor: bool, waehlen: bool) -> None:
        if schluessel in self.TATEN and not waehlen:
            return
        self.app.klaenge.spielen("menue_ok" if waehlen else "menue", 0.5)
        if schluessel == "weiter":
            self._menue_zu()
            return
        if schluessel == "raus":
            self._menue_zu()
            if self.ist_gastgeber:
                self.lobby_betreten()
            else:
                self.heim("")
            return
        if schluessel == "beenden":
            self.app.laeuft = False
            return
        if schluessel == "suchen":
            from .sitzung import LobbySuche
            self._menue_zu()
            self.app.schieben(LobbySuche(self.app, self))
            return
        if schluessel == "einstellungen":
            # Als Szene darueber, wie die Ausruestung: das Gefecht laeuft
            # darunter weiter und bekommt keine Eingaben (pausiert).
            from .menues import Einstellungen
            self._menue_zu()
            self.app.schieben(Einstellungen(self.app))
            return
        if schluessel == "planen":
            self._menue_zu()
            self.planung_oeffnen()
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
        if schluessel == "teams":
            self.menue_teams = True
            self.menue_zeile = 0
        elif schluessel == "neu":
            self._runde_neu()
            self._menue_zu()
        elif schluessel in ("starten", "starten_kos"):
            if self.plan_starten(0, kosmetik=(schluessel == "starten_kos")):
                self._menue_zu()
        elif schluessel == "lobby":
            self._menue_zu()
            self.lobby_betreten()

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
        # Laeuft noch eine Runde, ist das hier ihr Abbruch: neue Runde,
        # zurueck in die Lobby. Gebucht wird sie trotzdem (_abbruch_buchen).
        self._abbruch_buchen()
        self.wunsch = R.saeubern(self.wunsch, self._umfeld())
        self._regeln_setzen(self.wunsch)
        self._karte_wechseln(self.wunsch["karte"])

        self.teampunkte = [0] * len(K.TEAMS["namen"])
        self.zone_stand = [0.0] * len(self.teampunkte)
        self.zone_halter = -1
        self.runde = 0
        self.runden_gespielt = 0
        self.runde_sieger = -1
        self.runden_pause = 0.0
        self.sieger_team = -1
        self.welle = 0
        self.pause_rest = self.stufe["pause"]
        self.vorbei = False
        self.gewonnen = False
        self.liste = []
        self.rest = self.ende_wert if self.ende_art == "zeit" else 0.0
        self.obere_zeigen = bool(self.app.opt["obere_ebenen"])

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
        self._runde_gebucht = False
        self._zwischenstand = None
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

        if self.in_lobby:
            self._lobby_bestuecken()

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
            # Nur bei "eigenes": bei "eines fuer alle" waehlt der
            # Gastgeber, und die eigene Wahl aendert nichts.
            if self.loadout_regel == "eigenes" and not konto.loadout_gewaehlt_je:
                self.app.schieben(Ausruestung(self.app))

        if not konto.angemeldet and not konto.werte.get("anmeldung_gefragt"):
            konto.werte["anmeldung_gefragt"] = True
            konto.profil_sichern()
            self.app.schieben(Anmeldung(self.app, danach=ausruesten))
            return
        ausruesten()

    def _wunsch_lesen(self) -> dict:
        """Die Regeln, die gerade gelten, als Ausgangspunkt fuers Menue."""
        return dict(self.regelwerk, karte=self.karte)


    # ---- Bild ----------------------------------------------------------
    def zeichnen(self, ziel, alpha: float) -> None:
        # Beim Gast wird nicht zwischen zwei Rechenschritten ueberblendet,
        # sondern zwischen zwei Meldungen. `vorher` und `pos` eines
        # Mitspielers stehen bei ihm eine Sechzigstelsekunde auseinander,
        # nicht eine Hundertzwanzigstel - mit dem Bildanteil waere die
        # Bewegung nach der halben Zeit fertig und stuende dann still.
        # Genau das sah man als Ruckeln der Mitspieler.
        misch = alpha if self.ist_gastgeber else self.misch(alpha)
        self.renderer.vignette_an = self._vignette_an()
        if abs(self.kamera.zoom - 1.0) < 0.004:
            self._welt_bild(ziel, misch)
        else:
            self._zoom_zeichnen(ziel, misch)
        self._ueberblendung.zeichnen(ziel)
        self._ueberblendung.merken(ziel)
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
        if self.versionsfehler is not None:
            self._versionsfehler_zeichnen(ziel)
            return
        # Zuletzt und ueber allem: das Weiss einer Blendgranate. Es liegt
        # auch ueber der Anzeige - geblendet ist geblendet. Darin, wenn der
        # Werfer eines hat, sein Bild (Spielerkosmetik).
        # Barrierefreiheit (seit 0.32, nur bei einem selbst): NUR WEISS und
        # NUR SCHWARZ zeigen eine Flaeche ohne das Bild des Werfers.
        art = self.app.opt["blendung"]
        self.befinden.blendung_zeichnen(
            ziel, (0, 0, 0) if art == "schwarz" else (255, 255, 255))
        if art in ("weiss", "schwarz"):
            self.kos_zeigen = None
        else:
            self._kosmetik_bild_zeichnen(ziel)

    def _welt_bild(self, ziel, misch: float) -> None:
        """Alles, was in Weltkoordinaten liegt: die Welt, beim Gast die
        gemeldeten Wesen, Ziellinie und Streukegel."""
        self.renderer.welt_zeichnen(ziel, self.welt, self.kamera, misch,
                                    self.blick_hoehe, blick=self.blick,
                                    boden=self._kreis_zeichnen,
                                    oben_aus=not self.obere_zeigen)
        if not self.ist_gastgeber:
            self._fremdes_zeichnen(ziel, misch)
        # Ziellinie und Streukegel nicht, solange man ein Medkit anlegt:
        # dann schiesst man nicht, und eine Linie saehe aus, als ob.
        if (self.ich is not None and self.ich.lebt and not self.ich.am_boden
                and self.blick == self.ich.ebene and self.ich.heilt_rest <= 0):
            self.renderer.zielhilfen(ziel, self.welt, self.kamera, self.ich)
            self.renderer.tracer(ziel, self.welt, self.kamera, self.ich)

    # ---- Sichtweite und Nebel -------------------------------------------
    def zoom_stufe(self, schritt: int) -> None:
        """Eine Stufe weiter oder naeher (Mausrad)."""
        stufen = K.ZOOM["stufen"]
        jetzt = min(range(len(stufen)), key=lambda i: abs(stufen[i] - self.zoom_ziel))
        self.zoom_ziel = stufen[max(0, min(len(stufen) - 1, jetzt + schritt))]

    def _sicht_mitte(self) -> pygame.Vector2:
        """Wo das normale Bild (Zoom 1) jetzt stuende - dieselbe Rechnung
        wie Kamera.schritt, nur mit der normalen Groesse."""
        if self.ich is None:
            return pygame.Vector2(self.kamera.pos)
        k = K.KAMERA
        vor = pygame.Vector2(self._kamera_versatz) / (1.0 - k["maus_zug"])
        if vor.length() > k["maus_max"]:
            vor.scale_to_length(k["maus_max"])
        m = self.ich.pos + vor * k["maus_zug"]
        e = self.welt.ebene(self.ich.ebene)
        for achse, bild, karte in ((0, K.GAME_W, e.pixel_breite),
                                   (1, K.GAME_H, e.pixel_hoehe)):
            if karte > bild:
                m[achse] = max(bild / 2, min(karte - bild / 2, m[achse]))
            else:
                m[achse] = karte / 2
        return m

    def sicht_welt(self) -> pygame.Rect | None:
        """Das normale Bild in Weltpixeln - ausserhalb liegt der Nebel.
        None, wenn nichts im Nebel liegt (Zoom 1 oder naeher)."""
        if self.kamera.zoom <= 1.0 + 0.004:
            return None
        mitte = self._sicht_mitte()
        r = pygame.Rect(0, 0, K.GAME_W, K.GAME_H)
        r.center = (round(mitte.x), round(mitte.y))
        return r

    def im_licht(self, pos) -> bool:
        """Liegt der Weltpunkt ausserhalb des Nebels?"""
        r = self.sicht_welt()
        return r is None or r.collidepoint(pos.x, pos.y)

    def _zoom_zeichnen(self, ziel, misch: float) -> None:
        """Die Welt mit Zoom: groesser zeichnen, Nebel, verkleinern.

        1. Auf eine Flaeche in Zoomgroesse, mit dem Renderer auf dieser
           Groesse - die Kamera rechnet mit derselben (Kamera.zoom).
        2. Weiter weg als normal (Zoom > 1): erst nur das Gelaende ueber
           alles, darueber der Nebel, und dann das volle Bild - aber
           beschnitten auf das normale Bild (set_clip). Was draussen
           steht, wird also gar nicht erst gezeichnet; der Nebel verbirgt
           nicht nur, er ist leer.
        3. Auf 640 x 360 bringen: verkleinert weich, vergroessert hart.
           Die Vignette kommt erst danach, auf das fertige Bild.
        """
        z = self.kamera.zoom
        groesse = (max(1, int(round(K.GAME_W * z))), max(1, int(round(K.GAME_H * z))))
        if self._leinwand is None or self._leinwand.get_size() != groesse:
            self._leinwand = pygame.Surface(groesse, 0, ziel)
        lw = self._leinwand
        r = self.renderer
        r.groesse, r.vignette_an = groesse, False
        try:
            lw.fill(K.C_VOID)
            sicht = self.sicht_welt()
            if sicht is None:
                self._welt_bild(lw, misch)
            else:
                ecke = self.kamera.ecke
                bild_sicht = sicht.move(-int(ecke.x), -int(ecke.y))
                r.nur_gelaende = True
                try:
                    r.welt_zeichnen(lw, self.welt, self.kamera, misch, self.blick_hoehe,
                                    blick=self.blick, boden=self._kreis_zeichnen,
                                    oben_aus=not self.obere_zeigen)
                finally:
                    r.nur_gelaende = False
                # Der Nebel wird einmal je Groesse gefuellt und dann nur in
                # vier Streifen um das normale Bild aufgelegt - nicht jedes
                # Bild neu gefuellt und ganz aufgelegt.
                if self._nebel is None or self._nebel.get_size() != groesse:
                    self._nebel = pygame.Surface(groesse, pygame.SRCALPHA)
                    self._nebel.fill(K.ZOOM["nebel"])
                b, h = groesse
                s = bild_sicht.clip(pygame.Rect(0, 0, b, h))
                for streifen in (pygame.Rect(0, 0, b, s.top),
                                 pygame.Rect(0, s.bottom, b, h - s.bottom),
                                 pygame.Rect(0, s.top, s.left, s.height),
                                 pygame.Rect(s.right, s.top, b - s.right, s.height)):
                    if streifen.width > 0 and streifen.height > 0:
                        lw.blit(self._nebel, streifen.topleft, streifen)
                lw.set_clip(bild_sicht)
                try:
                    self._welt_bild(lw, misch)
                finally:
                    lw.set_clip(None)
                pygame.draw.rect(lw, K.ZOOM["nebel_rand"], bild_sicht.inflate(2, 2), 1)
        finally:
            r.groesse, r.vignette_an = (K.GAME_W, K.GAME_H), self._vignette_an()
        if z > 1.0:
            ziel.blit(pygame.transform.smoothscale(lw, (K.GAME_W, K.GAME_H)), (0, 0))
        else:
            ziel.blit(pygame.transform.scale(lw, (K.GAME_W, K.GAME_H)), (0, 0))
        if self._vignette_an():
            ziel.blit(r._vignette, (0, 0))

    def _vignette_an(self) -> bool:
        """Die dunklen Ecken - seit 0.32 haengen sie am Schalter in GRAFIK.

        Der Schalter stand seit 0.12 im Menue und hing an nichts; die
        Ecken wurden immer gezeichnet.
        """
        try:
            return bool(self.app.opt["vignette"])
        except (KeyError, TypeError, AttributeError):
            return True

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

        # 1. Was ich selbst gerade erfasse.
        opfer = getattr(ich, "erfasst", None)
        stand = getattr(ich, "erfassung", 0.0)
        if opfer is not None and stand > 0.0 and opfer.lebt:
            fest = stand >= 1.0
            farbe = e["farbe_fest"] if fest else e["farbe"]
            # Der Kreis zieht sich zusammen, waehrend die Erfassung laeuft.
            r = int(e["ring_gross"]
                    + (e["ring_klein"] - e["ring_gross"]) * min(1.0, stand))
            p = self.kamera.zu_bild(opfer.pos)
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

    def gegner_fuer_karte(self) -> list[tuple]:
        """Zombies und Bosse fuer die Minikarte: (x, y, ebene).

        Nur, wo es in dieser Runde Gegner gibt - und in der Lobby das
        Gehege. Die Puppen im Schiessstand sind Ziele, keine Gegner. Beim
        Gastgeber aus der Welt, beim Gast aus der letzten Weltmeldung.
        """
        if not (self.mit_gegnern or self.in_lobby):
            return []
        if self.ist_gastgeber:
            return [(w.pos.x, w.pos.y, int(w.ebene)) for w in self.welt.wesen
                    if isinstance(w, KampfGegner) and w.lebt and w.art != "puppe"]
        return [(e[0], e[1], int(e[3])) for e in self._fremde_gegner
                if e[4] != "puppe"]

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
        # Oben und unten liegt die Anzeige - die Pfeile bleiben im Streifen
        # dazwischen, sonst lagen sie unten auf der Waffe und der Panzerung.
        oben, unten = RAND_OBEN, K.GAME_H - RAND_UNTEN
        mitte = pygame.Vector2(K.GAME_W / 2, (oben + unten) / 2)
        for k in self.kaempfer.values():
            if not (k.lebt and k.am_boden and self._verbuendet(k)):
                continue
            p = self.kamera.zu_bild(k.pos)
            # Im Nebel sieht man ihn nicht - dann zeigt der Pfeil.
            im_bild = (rand <= p.x <= K.GAME_W - rand
                       and rand <= p.y <= K.GAME_H - rand and self.im_licht(k.pos))
            if im_bild and k.ebene == self.blick:
                continue
            richtung = p - mitte
            if richtung.length_squared() < 1.0:
                richtung = pygame.Vector2(0, -1)
            # Schnitt mit dem Rechteck zwischen den Anzeigestreifen.
            halb = pygame.Vector2(K.GAME_W / 2 - rand, (unten - oben) / 2)
            teiler = max(abs(richtung.x) / halb.x, abs(richtung.y) / halb.y)
            stelle = mitte + richtung / teiler
            # Oben links steht die Minikarte, darunter Spielart und Karte.
            # Ein Pfeil, der dort landete, rutscht darunter - wo der
            # Gefallene liegt, zeigt die Karte ja ohnehin.
            karte_unten = self.hud._karte_unten
            if karte_unten and stelle.y < karte_unten + 26 \
                    and stelle.x < K.MINIKARTE["links"] + K.MINIKARTE["breite"] + 10:
                stelle.y = karte_unten + 26
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
        for k in self.kaempfer.values():
            if not k.lebt or k.ebene != self.blick:
                continue
            if k is not self.ich and self.welt.verdeckt(k.pos, k.ebene):
                continue
            if not self.im_licht(k.pos):
                continue                # im Nebel steht auch kein Name
            p = self.kamera.zu_bild(k.pos)
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

    def _anzeige(self, ziel) -> None:
        """Die Anzeige steht seit 0.27 in anzeige.py."""
        self.hud.zeichnen(ziel)

    @property
    def gegner_rest(self) -> int:
        """Wie viele Gegner die laufende Welle noch hat - auch die, die noch
        nicht losgeschickt sind. Beim Gast, was der Gastgeber meldet."""
        if self.ist_gastgeber:
            return (sum(1 for g in self.gegner_offen if g.lebt)
                    + len(self.welle_rest))
        return self._gegner_rest

    def boss_stand(self):
        """(Name, Anteil Leben) des Bosses dieser Welle, oder None.

        Beim Gast aus den gemeldeten Gegnern - einen Boss gibt es je Welle
        hoechstens einmal, also ist der erste, den man findet, der richtige.
        """
        if self.ist_gastgeber:
            b = self.boss
            if b is None or not b.lebt:
                return None
            return K.BOSSE[b.art]["name"], max(0.0, b.leben) / b.max_leben
        for eintrag in self._fremde_gegner:
            art = eintrag[4]
            if K.ist_boss(art):
                return K.BOSSE[art]["name"], float(eintrag[5])
        return None

    # Das Pausenmenue seit 0.32, nach dem Vorbild von Helldivers 2: kein
    # Kasten in der Mitte, sondern eine dunkle Spalte am linken Rand, in
    # der die Eintraege nacheinander aufklappen, und rechts eine Tafel mit
    # dem, was man wissen will - welche Runde, was als Naechstes kommt,
    # und was der gewaehlte Eintrag tut. Das Gefecht bleibt rechts davon
    # sichtbar: es laeuft weiter, und das soll man sehen.
    MENUE_SPALTE = 230              # Breite der linken Spalte
    MENUE_OBEN = 76                 # erster Eintrag
    MENUE_ZEILE = 22                # Abstand der Eintraege
    MENUE_HILFE = {
        "weiter": "ZURÜCK INS SPIEL.",
        "starten": "STARTET DIE NÄCHSTE GEPLANTE RUNDE FÜR ALLE.",
        "starten_kos": "STARTET, SOBALD DIE KOSMETIK BEI ALLEN IST.",
        "planen": "SPIELART, KARTE UND REGELN DER NÄCHSTEN RUNDE (TASTE P).",
        "neu": "BRICHT DIE RUNDE AB UND FÄNGT SIE NEU AN.",
        "teams": "MITSPIELER SOFORT IN DIE ANDERE MANNSCHAFT.",
        "ausruestung": "DEINE LOADOUTS. GILT AB DEM NÄCHSTEN EINSTIEG.",
        "konto": "ANMELDEN, ABMELDEN, DEINE ZAHLEN.",
        "einstellungen": "BILD, TON, STEUERUNG, BARRIEREFREIHEIT.",
        "suchen": "LOBBYS IM SELBEN NETZ - ANKLICKEN UND UMSTEIGEN.",
        "raus": "ZURÜCK IN DEINE EIGENE LOBBY.",
        "lobby": "BEENDET DIE RUNDE. ALLE GEHEN ZURÜCK IN DIE LOBBY.",
        "beenden": "SCHLIESST DAS SPIEL.",
    }

    def _menue_flaechen(self) -> list:
        """Wo die Eintraege stehen - fuer das Bild und fuer die Maus."""
        return [pygame.Rect(16, self.MENUE_OBEN + i * self.MENUE_ZEILE,
                            self.MENUE_SPALTE - 30, 19)
                for i in range(len(self._menue_baut()))]

    def _teams_flaechen(self) -> list:
        leute = sorted(self.kaempfer.values(), key=lambda k: k.nummer)
        return [pygame.Rect(140, 83 + i * 15, 360, 13) for i in range(len(leute))]

    def _menue_maus(self, ev) -> None:
        """Die Maus im Menue: zeigen waehlt, Linksklick loest aus.

        Rechtsklick geht eine Ebene zurueck wie Esc. Das Rad blaettert.
        """
        if ev.type == pygame.MOUSEWHEEL:
            if ev.y:
                self._menue_taste(pygame.K_UP if ev.y > 0 else pygame.K_DOWN)
            return
        pos = self.app.zu_spiel(ev.pos)
        if self.menue_teams:
            for i, r in enumerate(self._teams_flaechen()):
                if r.collidepoint(pos):
                    self.menue_zeile = i
                    if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        self._menue_taste(pygame.K_RETURN)
                    break
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3:
                self.menue_teams = False
            return
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3:
            self._menue_zu()
            return
        for i, r in enumerate(self._menue_flaechen()):
            if r.collidepoint(pos):
                if self.menue != i and ev.type == pygame.MOUSEMOTION:
                    self.app.klaenge.spielen("menue", 0.25)
                self.menue = i
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    eintraege = self._menue_baut()
                    self._menue_wirken(eintraege[i][0], True, True)
                return

    def _aufklappen(self, i: int) -> float:
        """0 bis 1: wie weit Eintrag i schon aufgeklappt ist."""
        return ui.aufklappen(self._zeit - self._menue_seit, i)

    def _menue_zeichnen(self, ziel) -> None:
        """Der Deckel ueber dem laufenden Gefecht.

        Halb durchsichtig, damit man sieht, dass es weitergeht - das ist
        keine Kosmetik, sondern eine Warnung: wer hier steht, steht auch
        in der Welt herum und kann erschossen werden.
        """
        f = SCHRIFT
        deckel = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
        deckel.fill((9, 6, 5, 120))
        ziel.blit(deckel, (0, 0))

        if self.menue_teams:
            deckel.fill((9, 6, 5, 110))
            ziel.blit(deckel, (0, 0))
            self._menue_teams_zeichnen(ziel)
            return

        sp = self.MENUE_SPALTE
        spalte = pygame.Surface((sp, K.GAME_H), pygame.SRCALPHA)
        # Fast deckend: Minikarte und Lebensbalken liegen unter der Spalte
        # und sollen nicht durch die Eintraege scheinen.
        spalte.fill((9, 6, 5, 246))
        ziel.blit(spalte, (0, 0))
        pygame.draw.line(ziel, K.C_MUTED_DK, (sp, 0), (sp, K.GAME_H))

        auf = self._aufklappen(0)
        f.zeichnen(ziel, "PAUSE", 16 - int((1 - auf) * 20), 20, K.C_AMBER, 3)
        f.zeichnen(ziel, "DIE LOBBY LÄUFT WEITER" if self.in_lobby
                   else "DAS GEFECHT LÄUFT WEITER", 16, 48, K.C_RED, 1)
        pygame.draw.line(ziel, K.C_MUTED_DK, (16, 62), (sp - 14, 62))

        eintraege = self._menue_baut()
        self.menue = max(0, min(len(eintraege) - 1, self.menue))
        flaechen = self._menue_flaechen()
        for i, ((schluessel, text, wert), r) in enumerate(zip(eintraege, flaechen)):
            p = self._aufklappen(i + 1)
            if p <= 0.0:
                continue
            r = r.move(-int((1.0 - p) * 36), 0)
            ui.spalteneintrag(ziel, r, text, i == self.menue,
                              schluessel in ("beenden", "raus", "lobby"), wert)
            # Eine Trennlinie vor dem Weg hinaus: was ins Spiel fuehrt,
            # und was aus ihm heraus, soll man nicht verwechseln.
            if i + 1 < len(eintraege) and eintraege[i + 1][0] in (
                    "suchen", "raus", "lobby") and schluessel not in (
                    "suchen", "raus", "lobby"):
                pygame.draw.line(ziel, K.C_MUTED_DK, (r.x, r.bottom + 1),
                                 (r.right, r.bottom + 1))

        f.zeichnen(ziel, "MAUS ODER PFEILE, ENTER", 16, K.GAME_H - 30,
                   K.C_MUTED_DK, 1)
        f.zeichnen(ziel, "[ESC] ODER RECHTSKLICK: ZURÜCK", 16, K.GAME_H - 19,
                   K.C_MUTED_DK, 1)
        self._menue_tafel(ziel, eintraege[self.menue][0] if eintraege else "")

    def _menue_tafel(self, ziel, gewaehlt: str) -> None:
        """Rechts: diese Runde, die naechste, und was der Eintrag tut."""
        f = SCHRIFT
        p = self._aufklappen(2)
        if p <= 0.0:
            return
        breite = 226
        r = pygame.Rect(K.GAME_W - breite - 18 + int((1.0 - p) * 40), 20,
                        breite, 0)
        zeilen: list[tuple] = []        # (text, farbe, skala)
        if self.in_lobby:
            zeilen.append(("LOBBY", K.C_TEAL, 2))
        else:
            zeilen.append((K.MODI[self.modus]["name"], K.C_AMBER, 2))
        karte = (self.karte_kopf.get("name") or self.karte or "TESTKARTE")
        zeilen.append(("KARTE  %s" % str(karte).upper(), K.C_MUTED, 1))
        zeilen.append(("SPIELER  %d" % len(self.kaempfer), K.C_MUTED, 1))
        if not self.in_lobby:
            if self.regeln["runden"]:
                zeilen.append((self.runden_text(), K.C_MUTED, 1))
            elif self.ende_art == "zeit" and self.rest > 0:
                m, sek = divmod(int(self.rest), 60)
                zeilen.append(("NOCH  %d:%02d" % (m, sek), K.C_MUTED, 1))
            if self.mit_teams:
                zeilen.append(("PUNKTE  %s" % " : ".join(
                    str(x) for x in self.teampunkte), K.C_MUTED, 1))
        zeilen.append(("", K.C_MUTED, 1))
        zeilen.append(("NÄCHSTE RUNDE", K.C_AMBER, 1))
        if self.in_lobby or not self.plan_laeuft:
            naechste = R.kurz(self.plan[0], self._umfeld()) if self.plan else "-"
        else:
            naechste = self.plan_ausblick()
        zeilen.append((naechste, K.C_CREAM, 1))
        if self.ist_gastgeber:
            zeilen.append(("", K.C_MUTED, 1))
            zeilen.append(("ADRESSE  %s" % self.gastgeber.adresse,
                           K.C_MUTED_DK, 1))
        hilfe = self.MENUE_HILFE.get(gewaehlt, "")
        # Hoehe ausrechnen, dann zeichnen: Text, der sich umbricht, zaehlt
        # mehrfach.
        def umbrechen(text, skala):
            worte, raus, zeile = text.split(), [], ""
            for w in worte:
                probe = (zeile + " " + w).strip()
                if f.breite(probe, skala) > breite - 20 and zeile:
                    raus.append(zeile)
                    zeile = w
                else:
                    zeile = probe
            return raus + ([zeile] if zeile else [""])
        gesetzt = []
        for text, farbe, skala in zeilen:
            for t in umbrechen(text, skala):
                gesetzt.append((t, farbe, skala))
        hoehe = 14 + sum(18 if sk == 2 else 10 for _t, _f, sk in gesetzt)
        if hilfe:
            hilfe_zeilen = umbrechen(hilfe, 1)
            hoehe += 12 + 10 * len(hilfe_zeilen)
        r.height = hoehe
        ui.kasten(ziel, r, K.C_MUTED_DK, (12, 9, 7), 5)
        y = r.y + 8
        for text, farbe, skala in gesetzt:
            f.zeichnen(ziel, text, r.x + 10, y, farbe, skala)
            y += 18 if skala == 2 else 10
        if hilfe:
            y += 4
            pygame.draw.line(ziel, K.C_MUTED_DK, (r.x + 10, y), (r.right - 10, y))
            y += 6
            for t in hilfe_zeilen:
                f.zeichnen(ziel, t, r.x + 10, y, K.C_TEAL, 1)
                y += 10

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
        f.zeichnen(ziel, "[ESC] ZURÜCK", K.GAME_W // 2, K.GAME_H - 22,
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
        """Wen dieser Spieler am oeftesten erwischt hat.

        Seit 0.31 kommt `opfer` als Liste mit Namen (_opfer_liste) - so,
        wie es auch gebucht wird. Ein Gastgeber von davor schickte ein
        Woerterbuch nach Spielernummer; das geht weiter.
        """
        if isinstance(opfer, list):
            bester, meiste = "", 0
            for o in opfer:
                if not isinstance(o, dict):
                    continue
                try:
                    zahl = int(o.get("anzahl", 0))
                except (TypeError, ValueError):
                    continue
                if zahl > meiste and o.get("name"):
                    bester, meiste = str(o["name"])[:24], zahl
            return bester
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
        if self.plan_laeuft and self.plan_weiter >= 0:
            # Was als Naechstes kommt, und wann. Ohne das stand man vor der
            # Tafel und wusste nicht, ob noch etwas passiert.
            f.zeichnen(ziel, "WEITER IN %d:  %s" % (
                int(self.plan_weiter + 0.99), self.plan_ausblick()),
                K.GAME_W // 2, K.GAME_H - 30, K.C_AMBER, 1,
                ausrichtung="mitte")
        f.zeichnen(ziel, "[ESC] MENÜ", K.GAME_W // 2, K.GAME_H - 18,
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
        # Wer mitten in einer Runde geht - Menue, Fenster zu -, bucht sie
        # als abgebrochen; der Gastgeber auch fuer alle Gaeste.
        try:
            self._abbruch_buchen()
        except Exception:               # gehen darf daran nie scheitern
            pass
        if self.ansager is not None:
            self.ansager.schliessen()
            self.ansager = None
        if self.ist_gastgeber:
            self.gastgeber.schliessen()
        elif self.gast is not None:
            self.gast.schliessen()
