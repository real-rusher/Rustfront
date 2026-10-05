"""
DUSTFRONT - Spielszene
======================

Verdrahtet Welt, Wesen, Kamera und Anzeige. Hier steht die Spielregel, sonst
nichts: Wellen von Gegnern, Treppen zwischen den Etagen, Pause, Tod.

Der Ablauf einer Runde ist absichtlich duenn gehalten. Was spaeter dazukommt
(Auftraege, Bauen, der Wandler als zweiter Modus) haengt sich als weitere
Szene oder als weiteres Wesen an, nicht als Aenderung an dieser Datei.
"""

from __future__ import annotations

import math
import random

import pygame

from . import config as K
from . import world as welt_modul
from .core import Szene
from .entities import Aufsammler, Gegner, Spieler, wolke
from .font import SCHRIFT
from .inventar import Inventar
from .menues import Pause
from .render import Befinden, Kamera, Renderer, Ueberblendung
from .world import freier_punkt, testkarte


class Spiel(Szene):
    def __init__(self, app, seed=None, karte=None) -> None:
        super().__init__(app)
        self.renderer = Renderer(app.bilder)
        self.karte = karte
        # Im Spiel ohne Seed, damit jede Runde anders ausfaellt. Die Tests
        # geben einen festen mit: eine Pruefung, die mal gruen und mal rot
        # ist, sagt nichts, und man gewoehnt sich an, sie zu uebersehen.
        self.rnd = random.Random(seed)
        self.neu_aufbauen()

    # ---- Aufbau ------------------------------------------------------
    def neu_aufbauen(self) -> None:
        kopf = {}
        if self.karte:
            self.welt, kopf = welt_modul.karte_lesen(self.karte)
        else:
            self.welt = testkarte()
        if self.welt is None:
            self.welt = testkarte()
        self.kamera = Kamera()
        start_text = kopf.get("start", "").replace(",", " ").split()
        if len(start_text) == 2:
            start = pygame.Vector2((int(start_text[0]) + 0.5) * K.TILE,
                                   (int(start_text[1]) + 0.5) * K.TILE)
        else:
            start = freier_punkt(self.welt, 0, self.rnd)
        self.held = Spieler(start, 0)
        self.welt.dazu(self.held)
        self.welt.held = self.held

        # Die Welt meldet sich bei uns, wenn es wackeln oder spritzen soll
        self.welt.ruckeln = self._ruckeln
        self.welt.kurz_langsam = self._zeitlupe
        self.welt.blutfleck = self._blutfleck
        self.welt.klang = self._klang
        self.welt.brandfleck = self._brandfleck
        self.welt.blitz = self._blitz

        # Ansicht: welche Ebene die Kamera anschaut, und die geglaettete
        # Hoehe dazu. Beides haengt bewusst nicht an der Figur, damit man
        # spaeter frei durch die Etagen scrollen kann.
        self.blick = self.held.ebene
        self.blick_hoehe = float(self.welt.hoehe(self.blick))
        self._letzte_ebene = self.held.ebene
        self._ueberblendung = Ueberblendung()
        self._held_zuletzt = pygame.Vector2(self.held.pos)

        self.welle = 0
        self.pause_rest = 2.0
        self.offen: list = []
        self.schaden_blende = 0.0
        self.befinden = Befinden()
        self.tot_seit = 0.0
        self.hinweis = ""
        self.admin_zeile = None
        self._heilte = 0.0
        self.befinden.zuruecksetzen()
        self.kamera.pos.update(self.held.pos)

    def _zeitlupe(self, sekunden: float) -> None:
        self.app.zeitlupe = max(self.app.zeitlupe, sekunden)

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
        staerke = welt_modul.blend_wert(pos, ebene, self.held, self.welt)
        if staerke > 0.0:
            self.befinden.blenden(staerke)
            self.app.klaenge.spielen(K.skin("blend_pfeifen"), 0.35 + 0.5 * staerke)
        # Der Knall: leiser mit Abstand und Wegschauen (blend_ton_wert).
        laut = welt_modul.blend_ton_wert(pos, ebene, self.held)
        if laut > 0.0:
            self.app.klaenge.spielen(K.skin("blend_knall"), laut)
        return True

    def _ruckeln(self, kraft: float, anlass: str = "", pos=None,
                 ebene: int = 0, quelle=None) -> None:
        self.kamera.stossen(welt_modul.ruckel_wert(kraft, anlass, pos, ebene,
                                             quelle, self.held))

    def _klang(self, name: str, lautstaerke: float = 1.0, pos=None,
               ebene: int | None = None) -> None:
        laut = welt_modul.klang_wert(lautstaerke, pos, ebene or 0, self.held)
        if laut > 0.0:
            self.app.klaenge.spielen(name, laut)

    # ---- Wellen -------------------------------------------------------
    def welle_starten(self) -> None:
        self.welle += 1
        self.offen = [g for g in self.offen if g.lebt]
        if self.welle <= len(K.WELLEN):
            plan = K.WELLEN[self.welle - 1]
        else:
            ueber = self.welle - len(K.WELLEN)
            faktor = 1.0 + K.WELLE_WACHSTUM * ueber
            plan = [(max(1, int(n * faktor)), art) for n, art in K.WELLEN[-1]]
        for anzahl, art in plan:
            for _ in range(anzahl):
                ebene = self.rnd.choice([0, 1]) if self.welle > 2 else self.held.ebene
                pos = freier_punkt(self.welt, ebene, self.rnd,
                                   weg_von=self.held.pos if ebene == self.held.ebene else None,
                                   mindest=210)
                g = self.welt.dazu(Gegner(pos, art, ebene))
                wolke(self.welt, pos, 8, 80, 0.45, K.C_MUTED_DK, ebene, 1, "staub")
                self.offen.append(g)
        # Nachschub: ein paar Medkits, verteilt auf die Ebenen
        for _ in range(K.MEDKIT["je_welle"]):
            eb = self.rnd.randrange(len(self.welt.ebenen))
            self.welt.dazu(Aufsammler(freier_punkt(self.welt, eb, self.rnd),
                                      "medkit", eb))

    @property
    def gegner_uebrig(self) -> int:
        return sum(1 for g in self.offen if g.lebt)

    # ---- Ablauf -------------------------------------------------------
    def ereignis(self, ev) -> None:
        if self.admin_zeile is not None:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    self.admin_zeile = None
                elif ev.key == pygame.K_RETURN:
                    self._admin_befehl()
                elif ev.key == pygame.K_BACKSPACE:
                    self.admin_zeile = self.admin_zeile[:-1]
                elif ev.unicode and ev.unicode.isprintable() and len(self.admin_zeile) < 100:
                    self.admin_zeile += ev.unicode
            return
        if ev.type != pygame.KEYDOWN:
            return
        konto = getattr(self.app, "_konto", None)
        if ev.key == pygame.K_t and konto is not None and konto.angemeldet \
                and konto.name.strip().lower() == "admin":
            self.admin_zeile = ""
            return
        # Beide Schirme sind Szenen ueber dieser hier. Das Spiel rechnet
        # solange nicht weiter, bleibt aber sichtbar.
        if ev.key in self.app.opt.codes("pause"):
            if self.held.lebt:
                self.app.schieben(Pause(self.app, self))
        elif ev.key in self.app.opt.codes("inventar"):
            if self.held.lebt:
                self.app.schieben(Inventar(self.app, self))

    def _admin_befehl(self) -> None:
        """Lokale Moderationsbefehle mit einfachen @-Zielgruppen."""
        teile = self.admin_zeile.strip().split()
        self.admin_zeile = None
        if not teile:
            return
        befehl = teile[0].lower().lstrip("/")
        zielwahl = teile[1].lower() if len(teile) > 1 else "@s"
        try:
            wert = float(teile[2]) if len(teile) > 2 else 100.0
        except ValueError:
            self.hinweis = "ADMIN: ZAHL UNGUELTIG"
            return
        spieler = [w for w in self.welt.wesen if getattr(w, "fraktion", "") == "mensch"]
        alle = list(self.welt.wesen)
        if zielwahl == "@e":
            ziele = alle
        elif zielwahl == "@a":
            ziele = spieler
        elif zielwahl == "@g":
            mein_team = getattr(self.held, "team", -1)
            ziele = ([w for w in spieler if getattr(w, "team", -1) != mein_team]
                     if mein_team >= 0 else
                     [w for w in alle if getattr(w, "fraktion", "") == "feind"])
        elif zielwahl == "@t":
            mein_team = getattr(self.held, "team", -1)
            ziele = ([w for w in spieler if getattr(w, "team", -2) == mein_team]
                     if mein_team >= 0 else [self.held])
        elif zielwahl == "@s":
            ziele = [self.held]
        else:
            ziele = [w for w in spieler if getattr(w, "name", "").lower() == zielwahl]
        ziele = [w for w in ziele if w.lebt]
        if befehl in ("heal", "heilen"):
            for w in ziele:
                w.leben = min(w.max_leben, w.leben + wert)
        elif befehl in ("damage", "schaden"):
            for w in ziele:
                w.schaden(wert, None, self.held)
        elif befehl in ("kill", "toeten", "töten"):
            for w in ziele:
                w.schaden(w.leben + 1, None, self.held)
        elif befehl in ("speed", "tempo"):
            for w in ziele:
                w.tempo *= max(0.0, min(5.0, wert))
        elif befehl in ("ammo", "munition"):
            for w in ziele:
                if hasattr(w, "magazin"):
                    for name in w.magazin:
                        w.magazin[name] = int(max(0, min(999, wert)))
        else:
            self.hinweis = "ADMIN: heal|damage|kill|speed|ammo @ziel [wert]"
            return
        self.hinweis = "ADMIN: %s (%d)" % (befehl.upper(), len(ziele))

    def schritt(self, dt: float) -> None:
        e = self.app.eingabe
        held = self.held
        self.schaden_blende = max(0.0, self.schaden_blende - dt * 2.2)
        self.hinweis = ""
        if self.admin_zeile is not None:
            held.feuert = False
            return

        if held.lebt:
            held.will = e.richtung()
            if e.gedrueckt("dash"):
                held.dashen()
            held.ziel = self.kamera.zu_welt(e.maus)
            held.feuert = e.gehalten("feuer")
            if e.gedrueckt("nachladen"):
                held.nachladen()
            if e.gedrueckt("tracer"):
                held.tracer = not held.tracer
            if e.gedrueckt("tracer_weit"):
                held.tracer_weit = not held.tracer_weit
            if e.gedrueckt("feuermodus"):
                neu_modus = held.modus_wechseln()
                if neu_modus:
                    self.hinweis = "%s: %s" % (
                        held.waffe_daten["name"],
                        K.WAFFEN[held.waffe_name]["modus_daten"][neu_modus]["kurz"])
            for nr in range(1, K.HOTBAR_PLAETZE + 1):
                if ((nr == 10 and e.gedrueckt("waffe10"))
                        or (nr < 10 and e.gedrueckt("waffe%d" % nr))):
                    held.waffe_waehlen(nr - 1)
            if e.gedrueckt("heilen"):
                held.heilen()
            held.zielt = e.gehalten("zweit")
            if e.rad:                      # scrollen bewegt nur die Ansicht
                self.blick = max(0, min(len(self.welt.ebenen) - 1,
                                        self.blick + (1 if e.rad > 0 else -1)))

            ziel_ebene = self.welt.treppe_unter(held)
            if ziel_ebene is not None:
                self.hinweis = "[E] EBENE %d" % ziel_ebene
                if e.gedrueckt("nutzen"):
                    if self.welt.ebene_wechseln(held, ziel_ebene):
                        wolke(self.welt, held.pos, 10, 90, 0.4, K.C_MUTED_DK,
                              held.ebene, 1, "staub")
                        self.kamera.stossen(0.8)
            vorher_leben = held.leben
        else:
            held.will.update(0, 0)
            held.feuert = False
            vorher_leben = held.leben
            self.tot_seit += dt
            if self.tot_seit > 1.2 and (e.gedrueckt("nutzen") or e.gedrueckt("feuer")):
                self.neu_aufbauen()
                return

        self.welt.schritt(dt)
        if held.leben < vorher_leben:
            self.schaden_blende = 1.0
            self.befinden.treffer((vorher_leben - held.leben) / 40.0)
        if held.heilt_rest <= 0 < self._heilte:
            self.befinden.medkit()
        self._heilte = held.heilt_rest
        self.befinden.schritt(dt, held.leben / held.max_leben if held.lebt else 0.0,
                              self._klang)
        self.app.klaenge.daempfung_setzen(self.befinden.dumpf)
        if self.befinden.dumpf > 0.0:
            self.app.klaenge.dumpf_nachziehen()

        # Wellen nachschieben
        if held.lebt:
            if self.gegner_uebrig == 0:
                self.pause_rest -= dt
                if self.pause_rest <= 0:
                    self.welle_starten()
                    self.pause_rest = K.WELLE_PAUSE

        # Wechselt die Figur die Ebene, folgt die Ansicht ihr nach
        self._ueberblendung.schritt(dt)
        if held.ebene != self._letzte_ebene:
            self._letzte_ebene = held.ebene
            self.blick = held.ebene
            if held.flug <= 0:
                # Treppe oder Luke: sofort dort, das alte Bild blendet aus
                # (K.EBENENWECHSEL). Ein Sturz sinkt weiter mit.
                self.blick_hoehe = float(self.welt.hoehe(held.ebene))
                self._ueberblendung.starten()
                # Aufzug: die Kamera geht den Schritt beim Aussteigen mit.
                sprung = held.pos - self._held_zuletzt
                if sprung.length_squared() <= (2 * K.TILE) ** 2:
                    self.kamera.pos += sprung
        self._held_zuletzt.update(held.pos)
        if self.blick != held.ebene:
            self.hinweis = "ANSICHT EBENE %d  [MAUSRAD]" % self.blick

        # Waehrend eines Sturzes sinkt die Ansicht genau mit der Figur, sonst
        # zieht sie weich zur angeschauten Ebene.
        if held.flug > 0 and self.blick == held.ebene:
            self.blick_hoehe = self.welt.hoehe(held.ebene) + held.flug
        else:
            ziel_h = float(self.welt.hoehe(self.blick))
            self.blick_hoehe += (ziel_h - self.blick_hoehe) * min(1.0, 9.0 * dt)

        ebene = self.welt.ebene(held.ebene)
        # Die Einstellung greift bei jedem Bild neu: wer das Wackeln
        # im Pausenmenue abschaltet, sieht es sofort stehen.
        self.kamera.anteil = self.app.opt.ruckel_anteil()
        self.kamera.vorausschau = self.app.opt.blick_weite()
        self.kamera.schritt(dt, held.pos, held.ziel,
                            (ebene.pixel_breite, ebene.pixel_hoehe),
                            versatz=(self.app.eingabe.maus
                                     - pygame.Vector2(K.GAME_W / 2, K.GAME_H / 2))
                                    * self.kamera.zoom)

    # ---- Bild ---------------------------------------------------------
    def zeichnen(self, ziel, alpha: float) -> None:
        # Seit 0.32 haengt die Vignette am Schalter in GRAFIK.
        self.renderer.vignette_an = bool(self.app.opt["vignette"])
        self.renderer.welt_zeichnen(ziel, self.welt, self.kamera, alpha,
                                    self.blick_hoehe, blick=self.blick)
        self._ueberblendung.zeichnen(ziel)
        self._ueberblendung.merken(ziel)
        # Ziellinie, Streukegel und Nahkampfbogen gehoeren zu der Ebene, auf
        # der die Figur steht. Schaut man mit dem Mausrad eine Etage hoeher
        # oder tiefer, haben sie dort nichts zu suchen - sie zeigten sonst
        # ueber einen Boden, auf dem man gar nicht ist.
        if self.blick == self.held.ebene and self.held.heilt_rest <= 0:
            self.renderer.zielhilfen(ziel, self.welt, self.kamera, self.held)
            self.renderer.tracer(ziel, self.welt, self.kamera, self.held)
        self.renderer.schaden_blende(ziel, self.schaden_blende)
        self.befinden.zeichnen(ziel)

        if self.gegner_uebrig == 0 and self.held.lebt:
            text = "NÄCHSTE WELLE IN %d" % math.ceil(max(0.0, self.pause_rest))
        else:
            text = "WELLE %d  %d ÜBRIG" % (self.welle, self.gegner_uebrig)
        self.renderer.hud(ziel, self.welt, self.held, text, self.held.punkte,
                          self.blick)
        if self.hinweis:
            self.renderer.hinweis(ziel, self.hinweis)
        if self.admin_zeile is not None:
            pygame.draw.rect(ziel, (12, 10, 9), (16, 12, K.GAME_W - 32, 28))
            pygame.draw.rect(ziel, K.C_AMBER, (16, 12, K.GAME_W - 32, 28), 1)
            SCHRIFT.zeichnen(ziel, "> " + self.admin_zeile, 24, 21, K.C_CREAM, 1)
        self.befinden.blendung_zeichnen(
            ziel, (0, 0, 0) if self.app.opt["blendung"] == "schwarz"
            else (255, 255, 255))
        if not self.held.lebt:
            self.tod_schirm(ziel)
        if self.app.debug:
            self.renderer.debug(ziel, self.app, self.welt)

    def tod_schirm(self, ziel) -> None:
        s = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
        s.fill((0, 0, 0, min(190, int(self.tot_seit * 260))))
        ziel.blit(s, (0, 0))
        SCHRIFT.zeichnen(ziel, "VERLOREN", K.GAME_W // 2, K.GAME_H // 2 - 24,
                         K.C_RED, 4, 2, "mitte")
        SCHRIFT.zeichnen(ziel, "WELLE %d  SCHROTT %d" % (self.welle, self.held.punkte),
                         K.GAME_W // 2, K.GAME_H // 2 + 6, K.C_CREAM, 1, 2, "mitte")
        if self.tot_seit > 1.2:
            SCHRIFT.zeichnen(ziel, "[E] NEUE RUNDE", K.GAME_W // 2,
                             K.GAME_H // 2 + 26, K.C_AMBER, 1, 2, "mitte")


# Das frueher hier stehende PauseSchirm ist nach menues.Pause gewandert.
# Es gibt weiter einen Namen darauf, damit aelterer Code nicht bricht.
PauseSchirm = Pause
