"""
DUSTFRONT - Gefecht im LAN
==========================

Ein kurzer Mehrspieler-Test: mehrere Leute auf einer Karte, keine Gegner,
wer trifft bekommt einen Punkt. Am Rundenende steht die Liste, und sie
wandert in die Bestenliste im Benutzerordner.

**Der Gastgeber rechnet alles.** Er hat die einzige echte Welt. Gaeste
schicken nur, was sie druecken, und bekommen zurueck, wo alles steht. Ein
Gast simuliert nichts - seine Figuren sind Attrappen, die an die Stellen
gesetzt werden, die der Gastgeber durchgibt.

**Warum eine eigene Fraktion je Spieler.** Die Trefferabfrage in world.py
ueberspringt alles, was zur selben Fraktion gehoert. Alle Spieler tragen
von Haus aus "mensch", koennten sich also nie treffen. Statt die
Trefferabfrage umzubauen, bekommt hier jeder seine eigene Fraktion - damit
ist jeder fuer jeden ein Feind, und am bestehenden Spielkern aendert sich
keine Zeile.

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
from .entities import Aufsammler, Spieler, wolke
from .font import SCHRIFT
from .render import Kamera, Renderer
from .world import freier_punkt, testkarte


class Kaempfer(Spieler):
    """Ein Spieler im Gefecht.

    Traegt eine eigene Fraktion, damit ihn die Geschosse aller anderen als
    Ziel sehen, und merkt sich beim Sterben, wer ihn erwischt hat.
    """

    def __init__(self, pos, ebene: int, nummer: int, name: str) -> None:
        super().__init__(pos, ebene)
        self.fraktion = "kaempfer%d" % nummer
        self.nummer = nummer
        self.name = name
        self.abschuesse = 0
        self.tode = 0
        self.wieder_in = 0.0
        self.toeter = None           # wertet das Gefecht aus und raeumt weg

    def sterben(self, von=None) -> None:
        super().sterben(von)
        self.toeter = von


class KampfBeute(Aufsammler):
    """Ein Medkit, das jeder Kaempfer aufheben kann.

    Der gewoehnliche Aufsammler schaut nur auf welt.held - im Einzelspieler
    gibt es ja nur einen. Im Gefecht waere das der Gastgeber, und kein Gast
    koennte je ein Medkit nehmen.
    """

    def __init__(self, pos, art: str, ebene: int, kaempfer: dict) -> None:
        super().__init__(pos, art, ebene)
        self._kaempfer = kaempfer

    def schritt(self, dt: float) -> None:
        for k in list(self._kaempfer.values()):
            if not k.lebt or k.ebene != self.ebene:
                continue
            if self.pos.distance_to(k.pos) > self.radius + k.radius + 3:
                continue
            if self.art == "medkit" and k.medkits < K.MEDKIT["hoechstens"]:
                k.medkits += 1
                self.lebt = False
                wolke(self.welt, self.pos, 8, 90, 0.4, K.C_TEAL, self.ebene, 1)
                self.welt.klang("aufheben", 0.6)
                return


class Gefecht(Szene):
    """Die Spielszene fuer den LAN-Test, beim Gastgeber wie beim Gast."""

    def __init__(self, app, name: str, gastgeber=None, gast=None) -> None:
        super().__init__(app)
        self.name = netz.name_saeubern(name)
        self.gastgeber = gastgeber
        self.gast = gast
        self.rnd = random.Random()
        self.renderer = Renderer(app.bilder)
        self.welt = testkarte()
        self.kamera = Kamera()
        self.kaempfer: dict[int, Kaempfer] = {}
        self.rest = K.GEFECHT["rundenzeit"]
        self.vorbei = False
        self.liste: list[dict] = []          # Endstand, wenn die Runde aus ist
        self.hinweis = ""
        self.blick = 0
        self.blick_hoehe = 0.0
        self._seit_senden = 0.0
        self._fremde_schuesse: list[tuple] = []
        self._fremde_beute: list[tuple] = []
        self._knoepfe: set[str] = set()     # gesammelte Einmal-Druecke
        self._waffe_wunsch = -1
        self._rad = 0                       # Mausrad, noch nicht verrechnet
        self._seit_medkit = 0.0
        self._letzte_ebene = 0
        self.meine_nummer = 0        # beim Gast: kommt mit "willkommen"

        if self.ist_gastgeber:
            self.ich = self._dazu(0, self.name)
        else:
            self.ich = None                  # kommt mit der ersten Weltmeldung
            self.gast.senden({"t": "hallo", "name": self.name})

    # ---- Grundsaetzliches --------------------------------------------
    @property
    def ist_gastgeber(self) -> bool:
        return self.gastgeber is not None

    def _dazu(self, nummer: int, name: str) -> Kaempfer:
        """Einen Kaempfer in die Welt setzen, weg von den anderen."""
        pos = self._einstiegsort()
        k = Kaempfer(pos, 0, nummer, netz.name_saeubern(name))
        k.unverwundbar = K.GEFECHT["schutz"]
        self.kaempfer[nummer] = k
        self.welt.dazu(k)
        return k

    def _einstiegsort(self) -> pygame.Vector2:
        """Ein freier Platz mit Abstand zu allen, die schon da sind."""
        lebende = [k.pos for k in self.kaempfer.values() if k.lebt]
        for _ in range(K.NETZ["hoechstens"] * 4):
            p = freier_punkt(self.welt, 0, self.rnd)
            if all(p.distance_to(q) > K.GEFECHT["abstand"] for q in lebende):
                return p
        return freier_punkt(self.welt, 0, self.rnd)

    # ---- Eingabe ------------------------------------------------------
    def knoepfe_sammeln(self) -> None:
        """Einmalige Tastendruecke aufheben, bis das naechste Paket rausgeht.

        Das ist keine Feinheit, sondern notwendig: gedrueckt() ist genau ein
        Bild lang wahr, das Spiel rechnet 120 Mal in der Sekunde, gesendet
        wird aber nur ein paar Dutzend Mal. Wer direkt beim Senden abfragt,
        verliert die meisten Druecke - Nachladen, Treppe und Waffenwechsel
        kamen deshalb fast nie an. Gesammelt geht keiner mehr verloren.

        Laeuft bei Gastgeber und Gast gleichermassen; der Gastgeber legt die
        Sammlung gleich auf seine eigene Figur.
        """
        e = self.app.eingabe
        for name in ("nachladen", "nutzen", "heilen", "tracer", "tracer_weit"):
            if e.gedrueckt(name):
                self._knoepfe.add(name)
        for nr in range(1, 7):
            if e.gedrueckt("waffe%d" % nr):
                self._waffe_wunsch = nr - 1
        if e.rad:
            self._rad += e.rad

    def _meine_eingabe(self) -> dict:
        e = self.app.eingabe
        ziel = self.kamera.zu_welt(e.maus)
        meldung = {
            "t": "ein",
            "will": [round(v, 2) for v in e.richtung()],
            "ziel": [round(ziel.x, 1), round(ziel.y, 1)],
            "feuert": e.gehalten("feuer"),
            "zielt": e.gehalten("zweit"),
            "sprint": e.gehalten("sprint"),
            "waffe": self._waffe_wunsch,
            "knoepfe": sorted(self._knoepfe),
        }
        self._knoepfe.clear()
        self._waffe_wunsch = -1
        return meldung

    def _anwenden(self, k: Kaempfer, ein: dict) -> None:
        """Eine Eingabemeldung auf einen Kaempfer legen. Nur beim Gastgeber.

        Alles wird auf verlaessliche Werte gebracht: die Meldung kommt von
        einem anderen Rechner, und was von dort kommt, ist erst einmal nur
        ein Vorschlag.
        """
        if not k.lebt:
            return
        try:
            will = pygame.Vector2(float(ein["will"][0]), float(ein["will"][1]))
            if will.length_squared() > 1.0:
                will.normalize_ip()
            k.will = will
            k.ziel = pygame.Vector2(float(ein["ziel"][0]), float(ein["ziel"][1]))
        except (KeyError, TypeError, ValueError, IndexError):
            return
        k.feuert = bool(ein.get("feuert"))
        k.zielt = bool(ein.get("zielt"))
        k.sprint = bool(ein.get("sprint"))
        waffe = ein.get("waffe", -1)
        if isinstance(waffe, int) and 0 <= waffe < len(k.waffen):
            k.waffe_waehlen(waffe)
        knoepfe = ein.get("knoepfe") or []
        if not isinstance(knoepfe, list):
            return
        if "nachladen" in knoepfe:
            k.nachladen()
        if "heilen" in knoepfe:
            k.heilen()
        if "tracer" in knoepfe:
            k.tracer = not k.tracer
        if "tracer_weit" in knoepfe:
            k.tracer_weit = not k.tracer_weit
        if "nutzen" in knoepfe:
            ziel_ebene = self.welt.treppe_unter(k)
            if ziel_ebene is not None:
                self.welt.ebene_wechseln(k, ziel_ebene)

    # ---- Schritt: Gastgeber -------------------------------------------
    def _schritt_gastgeber(self, dt: float) -> None:
        self.hinweis = ""
        for nummer in self.gastgeber.annehmen():
            pass                      # Kaempfer entsteht erst beim "hallo"

        for nummer, nachricht in self.gastgeber.holen():
            art = nachricht.get("t")
            if art == "hallo":
                if nummer not in self.kaempfer:
                    k = self._dazu(nummer, nachricht.get("name", "GAST"))
                    self.gastgeber.an_einen(nummer, {
                        "t": "willkommen", "id": nummer,
                        "name": k.name, "runde": self.rest})
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

        self._medkits_nachlegen(dt)
        self.welt.schritt(dt)
        self._tote_abrechnen(dt)

        self.rest = max(0.0, self.rest - dt)
        if self.rest <= 0 and not self.vorbei:
            self._runde_beenden()

        self._seit_senden += dt
        if self._seit_senden >= K.NETZ["takt"]:
            self._seit_senden = 0.0
            self.gastgeber.an_alle(self._weltmeldung())

    def _medkits_nachlegen(self, dt: float) -> None:
        """Alle paar Sekunden ein Medkit, solange nicht zu viele liegen.

        Im Einzelspieler kommen Medkits mit jeder Welle. Hier gibt es keine
        Wellen, also braucht es einen eigenen Takt - ohne ihn bleibt ein
        Treffer fuer den Rest der Runde stehen.
        """
        self._seit_medkit += dt
        if self._seit_medkit < K.GEFECHT["medkit_takt"]:
            return
        self._seit_medkit = 0.0
        liegen = sum(1 for w in self.welt.wesen
                     if isinstance(w, KampfBeute) and w.lebt)
        if liegen >= K.GEFECHT["medkit_hoechstens"]:
            return
        ebene = self.rnd.randrange(len(self.welt.ebenen))
        self.welt.dazu(KampfBeute(freier_punkt(self.welt, ebene, self.rnd),
                                  "medkit", ebene, self.kaempfer))

    def _tote_abrechnen(self, dt: float) -> None:
        """Punkte vergeben und Gefallene wieder einsteigen lassen."""
        for k in list(self.kaempfer.values()):
            if k.lebt:
                continue
            if k.toeter is not None:
                # Wer war es? Ein Geschoss meldet seinen Urheber weiter, im
                # Nahkampf steht der Schlaeger selbst da.
                toeter = getattr(k.toeter, "von", k.toeter)
                if isinstance(toeter, Kaempfer) and toeter is not k:
                    toeter.abschuesse += K.GEFECHT["punkt_abschuss"]
                elif toeter is k:
                    k.abschuesse += K.GEFECHT["punkt_selbst"]
                k.toeter = None
                k.tode += 1
                k.wieder_in = K.GEFECHT["wieder_nach"]
            k.wieder_in -= dt
            if k.wieder_in <= 0 and not self.vorbei:
                self._wieder_einsteigen(k)

    def _wieder_einsteigen(self, k: Kaempfer) -> None:
        k.pos.update(self._einstiegsort())
        k.vorher.update(k.pos)
        k.tempo.update(0, 0)
        k.leben = k.max_leben
        k.ebene = 0
        k.flug = 0.0
        k.sturz_rest = 0.0
        k.lebt = True
        k.unverwundbar = K.GEFECHT["schutz"]
        k.magazin = {w: K.WAFFEN[w]["magazin"] for w in k.waffen}
        if k not in self.welt.wesen and k not in self.welt.neue:
            self.welt.dazu(k)

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
                # Alles Weitere braucht der Gast, um sein eigenes HUD und
                # seine Zielhilfen zu zeichnen. Ohne das steht dort die
                # Munition der Vorgabe und der Nachladebalken fehlt ganz.
                "m": k.magazin.get(k.waffe_name, 0),
                "nl": round(k.nachlade_rest, 2),
                "fo": round(k.fokus, 2),
                "zi": k.zielt,
                "tr": k.tracer, "tw": k.tracer_weit,
                "mk": k.medkits, "hr": round(k.heilt_rest, 2),
                "sz": round(k.schlag_zeigen, 2),
                "wi": round(k.wieder_in, 1),
            })
        # Alles, was fliegt: Geschosse und geworfene Granaten. Beides sieht
        # der Gast sonst gar nicht - eine Granate, die man nicht kommen
        # sieht, ist kein Spiel, sondern Pech.
        flug = []
        for w in self.welt.wesen:
            name = getattr(w, "bild", None)
            if name in ("geschoss", "granate") and w.lebt:
                flug.append([round(w.pos.x, 1), round(w.pos.y, 1),
                             round(w.winkel, 1), w.ebene, name])
        beute = [[round(w.pos.x, 1), round(w.pos.y, 1), w.ebene,
                  getattr(w, "art", "medkit")]
                 for w in self.welt.wesen
                 if isinstance(w, KampfBeute) and w.lebt]
        return {"t": "welt", "rest": round(self.rest, 1),
                "spieler": spieler, "schuesse": flug, "beute": beute,
                "aus": self.vorbei}

    def _runde_beenden(self) -> None:
        self.vorbei = True
        self.liste = self._endstand()
        bestenliste.eintragen(self.liste)
        if self.ist_gastgeber:
            self.gastgeber.an_alle({"t": "ende", "liste": self.liste})

    def _endstand(self) -> list[dict]:
        return bestenliste.sortiert(
            [{"name": k.name, "abschuesse": k.abschuesse, "tode": k.tode}
             for k in self.kaempfer.values()])

    # ---- Schritt: Gast -------------------------------------------------
    def _schritt_gast(self, dt: float) -> None:
        self.hinweis = ""
        if not self.gast.offen:
            self.hinweis = "VERBINDUNG VERLOREN  [ESC]"
            return

        for nachricht in self.gast.holen():
            art = nachricht.get("t")
            if art == "willkommen":
                self.meine_nummer = int(nachricht.get("id", 0))
            elif art == "welt":
                self._welt_uebernehmen(nachricht)
            elif art == "ende":
                self.vorbei = True
                self.liste = [e for e in nachricht.get("liste", [])
                              if isinstance(e, dict)]
                bestenliste.eintragen(self.liste)

        # Warten Einmal-Druecke, geht das Paket sofort raus. Sonst haengt
        # ein Nachladen oder ein Waffenwechsel bis zum naechsten Takt, und
        # das spuert man deutlicher als jede Verzoegerung der Bewegung.
        self._seit_senden += dt
        eilig = bool(self._knoepfe) or self._waffe_wunsch >= 0
        if eilig or self._seit_senden >= K.NETZ["eingabe_takt"]:
            self._seit_senden = 0.0
            self.gast.senden(self._meine_eingabe())

    def _welt_uebernehmen(self, meldung: dict) -> None:
        """Die Attrappen an die Stellen setzen, die der Gastgeber durchgibt."""
        self.rest = float(meldung.get("rest", self.rest))
        self.vorbei = bool(meldung.get("aus", False))
        gesehen = set()
        for eintrag in meldung.get("spieler", []):
            try:
                nummer = int(eintrag["i"])
                x, y = float(eintrag["p"][0]), float(eintrag["p"][1])
            except (KeyError, TypeError, ValueError, IndexError):
                continue
            gesehen.add(nummer)
            k = self.kaempfer.get(nummer)
            if k is None:
                k = Kaempfer(pygame.Vector2(x, y), 0, nummer,
                             str(eintrag.get("n", "GAST")))
                self.kaempfer[nummer] = k
                if nummer == self.meine_nummer:
                    self.ich = k
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
            k.nachlade_rest = float(eintrag.get("nl", 0.0))
            k.fokus = float(eintrag.get("fo", 0.0))
            k.zielt = bool(eintrag.get("zi", False))
            k.tracer = bool(eintrag.get("tr", False))
            k.tracer_weit = bool(eintrag.get("tw", False))
            k.medkits = int(eintrag.get("mk", 0))
            k.heilt_rest = float(eintrag.get("hr", 0.0))
            k.schlag_zeigen = float(eintrag.get("sz", 0.0))
            k.wieder_in = float(eintrag.get("wi", 0.0))
        for nummer in list(self.kaempfer):
            if nummer not in gesehen:
                self.kaempfer.pop(nummer, None)
        # Der Renderer laeuft ueber welt.wesen: beim Gast wird die Liste
        # gesetzt statt simuliert.
        self.welt.wesen = [k for k in self.kaempfer.values() if k.lebt]
        self.welt.neue = []
        if self.ich is not None:
            self.welt.held = self.ich
        self._fremde_schuesse = [tuple(s) for s in meldung.get("schuesse", [])
                                 if isinstance(s, (list, tuple)) and len(s) == 5]
        self._fremde_beute = [tuple(b) for b in meldung.get("beute", [])
                              if isinstance(b, (list, tuple)) and len(b) == 4]

    # ---- Szene ---------------------------------------------------------
    def schritt(self, dt: float) -> None:
        # Vor allem anderen: Einmal-Druecke aufheben, sonst gehen sie
        # zwischen zwei Paketen verloren.
        self.knoepfe_sammeln()

        if self.ist_gastgeber:
            self._schritt_gastgeber(dt)
        else:
            self._schritt_gast(dt)

        if self.ich is not None:
            # Das Mausrad verschiebt nur die Ansicht, nicht die Figur - wie
            # im Einzelspieler. Wechselt die Figur die Ebene, folgt die
            # Ansicht ihr wieder nach.
            if self.ich.ebene != self._letzte_ebene:
                self._letzte_ebene = self.ich.ebene
                self.blick = self.ich.ebene
            if self._rad:
                self.blick = max(0, min(len(self.welt.ebenen) - 1,
                                        self.blick + (1 if self._rad > 0 else -1)))
                self._rad = 0
            ziel_h = float(self.welt.hoehe(self.blick))
            if self.ich.flug > 0 and self.blick == self.ich.ebene:
                self.blick_hoehe = self.welt.hoehe(self.ich.ebene) + self.ich.flug
            else:
                self.blick_hoehe += (ziel_h - self.blick_hoehe) * min(1.0, 9.0 * dt)
            if self.blick != self.ich.ebene:
                self.hinweis = "ANSICHT EBENE %d  [MAUSRAD]" % self.blick
            ebene = self.welt.ebene(self.ich.ebene)
            self.kamera.schritt(dt, self.ich.pos, self.ich.ziel,
                                (ebene.pixel_breite, ebene.pixel_hoehe))

    def ereignis(self, ev) -> None:
        if ev.type == pygame.KEYDOWN and ev.key in self.app.opt.codes("pause"):
            self.app.laeuft = False

    def zeichnen(self, ziel, alpha: float) -> None:
        self.renderer.welt_zeichnen(ziel, self.welt, self.kamera, alpha,
                                    self.blick_hoehe)
        if not self.ist_gastgeber:
            self._schuesse_zeichnen(ziel)
        # Zielhilfen und Ziellinie gehoeren zu der Ebene, auf der man steht.
        if (self.ich is not None and self.ich.lebt
                and self.blick == self.ich.ebene):
            self.renderer.zielhilfen(ziel, self.welt, self.kamera, self.ich)
            self.renderer.tracer(ziel, self.welt, self.kamera, self.ich)
        self._namen_zeichnen(ziel)
        self._anzeige(ziel)
        if self.vorbei:
            self._endtafel(ziel)

    def _schuesse_zeichnen(self, ziel) -> None:
        """Beim Gast gibt es keine echten Wesen dafuer, nur gemeldete Punkte.

        Gezeichnet werden Geschosse, geworfene Granaten und alles, was am
        Boden liegt. Ohne das fliegt einem eine Granate ins Gesicht, die man
        nie gesehen hat, und die Medkits sind unsichtbar.
        """
        ecke = self.kamera.ecke
        for (x, y, ebene, art) in self._fremde_beute:
            if ebene != self.blick:
                continue
            s = self.renderer.bilder.bild(art)
            ziel.blit(s, (x - ecke.x - s.get_width() / 2,
                          y - ecke.y - s.get_height() / 2))
        for (x, y, winkel, ebene, name) in self._fremde_schuesse:
            if ebene != self.blick:
                continue
            s = self.renderer.bilder.gedreht(name, winkel)
            ziel.blit(s, (x - ecke.x - s.get_width() / 2,
                          y - ecke.y - s.get_height() / 2))

    def _namen_zeichnen(self, ziel) -> None:
        """Ueber jedem Mitspieler sein Name. Ohne das weiss man im Gefecht
        nicht, auf wen man schiesst."""
        ecke = self.kamera.ecke
        for k in self.kaempfer.values():
            if not k.lebt or k.ebene != self.blick:
                continue
            p = k.pos - ecke
            if not (0 <= p.x <= K.GAME_W and 0 <= p.y <= K.GAME_H):
                continue
            eigen = (k is self.ich)
            farbe = K.C_TEAL if eigen else K.C_AMBER
            SCHRIFT.zeichnen(ziel, k.name, int(p.x), int(p.y) - 26, farbe, 1,
                             ausrichtung="mitte")
            # Lebensbalken, damit man sieht, wen man fast hat
            breite = 24
            anteil = max(0.0, min(1.0, k.leben / k.max_leben))
            pygame.draw.rect(ziel, (16, 11, 8),
                             (int(p.x) - breite // 2, int(p.y) - 18, breite, 3))
            pygame.draw.rect(ziel, farbe,
                             (int(p.x) - breite // 2, int(p.y) - 18,
                              int(breite * anteil), 3))

    def _anzeige(self, ziel) -> None:
        f = SCHRIFT
        minuten, sekunden = divmod(int(max(0.0, self.rest)), 60)
        f.zeichnen(ziel, "%d:%02d" % (minuten, sekunden), K.GAME_W // 2, 10,
                   K.C_CREAM, 2, ausrichtung="mitte")
        rolle = "GASTGEBER" if self.ist_gastgeber else "GAST"
        f.zeichnen(ziel, rolle, 12, 12, K.C_MUTED, 1)
        if self.ist_gastgeber:
            f.zeichnen(ziel, self.gastgeber.adresse, 12, 22, K.C_MUTED_DK, 1)

        # Punktestand rechts, unterhalb der Ebenenanzeige. Weiter oben
        # laegen beide uebereinander.
        y = K.GEFECHT["tafel_oben"]
        for k in bestenliste.sortiert(
                [{"name": k.name, "abschuesse": k.abschuesse, "tode": k.tode,
                  "k": k} for k in self.kaempfer.values()]):
            wer = k["k"]
            farbe = K.C_TEAL if wer is self.ich else K.C_MUTED
            f.zeichnen(ziel, "%-10s %2d/%2d" % (k["name"], k["abschuesse"],
                                                k["tode"]),
                       K.GAME_W - 12, y, farbe, 1, ausrichtung="rechts")
            y += 9

        if self.ich is not None and not self.ich.lebt and not self.vorbei:
            f.zeichnen(ziel, "GEFALLEN", K.GAME_W // 2, K.GAME_H // 2 - 10,
                       K.C_RED, 2, ausrichtung="mitte")
            f.zeichnen(ziel, "WIEDER IN %.0f" % max(0.0, self.ich.wieder_in),
                       K.GAME_W // 2, K.GAME_H // 2 + 8, K.C_MUTED, 1,
                       ausrichtung="mitte")
        elif self.ich is not None:
            self.renderer.hud(ziel, self.welt, self.ich, "", self.ich.abschuesse,
                              self.blick, kopf=False)
        if self.hinweis:
            self.renderer.hinweis(ziel, self.hinweis)

    def _endtafel(self, ziel) -> None:
        deckel = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
        deckel.fill((9, 6, 5, 220))
        ziel.blit(deckel, (0, 0))
        f = SCHRIFT
        f.zeichnen(ziel, "RUNDE VORBEI", K.GAME_W // 2, 46, K.C_AMBER, 3,
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
