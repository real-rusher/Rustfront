"""
DUSTFRONT - Pausenmenue, Einstellungen, Steuerung, Mitwirkende
==============================================================

Vier Szenen, die alle dasselbe Muster haben:

    Tafel mit Eckwinkeln  ->  Kopfzeile  ->  Liste von Elementen  ->  Fusszeile

Alle liegen als Szene **ueber** dem Spiel, nicht statt ihm. `deckt_zu = False`
heisst: das Spiel wird weiter gezeichnet, nur eingefroren und abgedunkelt. Man
sieht also die Welle, in der man steckt, waehrend man am Ton dreht.

Bedient wird alles zweifach, mit Maus und mit Tastatur. Wer im Gefecht Escape
drueckt, will nicht erst die Maus suchen muessen; wer im Menue ist, will
klicken. Pfeiltasten waehlen, Enter bestaetigt, Links und Rechts aendern den
Wert der gewaehlten Zeile, Escape geht eine Ebene zurueck.

Gespeichert wird sofort bei jeder Aenderung, nicht erst beim Verlassen. Ein
Absturz oder ein hartes Beenden kostet damit keine Einstellung.
"""

from __future__ import annotations

import math

import pygame

from . import config as K
from . import einstellungen as E
from . import pfade
from . import ui
from .core import Szene
from .font import SCHRIFT

# ══════════════════════════════════════════════════ Masse

TAFEL_GROSS = pygame.Rect(64, 30, 512, 300)
ZEILE_H = 16
ZEILE_ABSTAND = 4


def _mitte(breite: int, hoehe: int) -> pygame.Rect:
    return pygame.Rect((K.GAME_W - breite) // 2, (K.GAME_H - hoehe) // 2,
                       breite, hoehe)


class Menue(Szene):
    """Gemeinsames Verhalten: Tastaturauswahl, Maus, Klang, Zurueck.

    Die Unterklassen bauen nur ihre Elementliste in `aufbauen()` und
    beantworten in `ausloesen(el)`, was ein Druck auf ein Element bedeutet.
    """

    deckt_zu = False
    titel = ""
    unterzeile = ""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.elemente: list[ui.Element] = []
        self.wahl = 0
        self.zeit = 0.0
        self.meldung = ""
        self.meldung_rest = 0.0
        self.aufbauen()

    # ---- Von den Unterklassen zu fuellen -----------------------------
    def aufbauen(self) -> None:
        pass

    def ausloesen(self, el: ui.Element) -> None:
        pass

    def geaendert(self, el: ui.Element) -> None:
        """Ein Regler, Schalter oder eine Wahl hat einen neuen Wert."""

    def inhalt_zeichnen(self, ziel) -> None:
        pass

    # ---- Hilfen ------------------------------------------------------
    def klang(self, name: str, laut: float = 0.7) -> None:
        self.app.klaenge.spielen(name, laut)

    def sagen(self, text: str, dauer: float = 2.6) -> None:
        self.meldung = text
        self.meldung_rest = dauer

    @property
    def waehlbar(self) -> list[ui.Element]:
        return [e for e in self.elemente if not e.gesperrt]

    def wahl_schieben(self, d: int) -> None:
        w = self.waehlbar
        if not w:
            return
        jetzt = self.elemente[self.wahl] if 0 <= self.wahl < len(self.elemente) else None
        i = w.index(jetzt) if jetzt in w else 0
        neu = w[(i + d) % len(w)]
        self.wahl = self.elemente.index(neu)
        self.klang("menue", 0.35)

    def gewaehlt(self) -> ui.Element | None:
        if 0 <= self.wahl < len(self.elemente):
            return self.elemente[self.wahl]
        return None

    def zurueck(self) -> None:
        self.app.werfen()

    # ---- Ablauf ------------------------------------------------------
    def betreten(self) -> None:
        self.app.eingabe.alles_loslassen()
        w = self.waehlbar
        if w and self.elemente[self.wahl].gesperrt:
            self.wahl = self.elemente.index(w[0])

    def verlassen(self) -> None:
        self.app.eingabe.alles_loslassen()

    def schritt(self, dt: float) -> None:
        self.zeit += dt
        self.meldung_rest = max(0.0, self.meldung_rest - dt)
        if self.meldung_rest <= 0:
            self.meldung = ""
        maus = self.app.zu_spiel(pygame.mouse.get_pos())
        for i, el in enumerate(self.elemente):
            if el.maus(maus):
                self.wahl = i
            if isinstance(el, ui.Regler) and el.zieht:
                alt = el.wert
                el.wert = el.aus_x(int(maus.x))
                if el.wert != alt:
                    self.geaendert(el)

    def ereignis(self, ev) -> None:
        if ev.type == pygame.KEYDOWN:
            self.taste(ev)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.maus_druck(self.app.zu_spiel(ev.pos))
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            for el in self.elemente:
                if isinstance(el, ui.Regler) and el.zieht:
                    el.zieht = False
                    self.geaendert(el)
                el.gedrueckt = False
        elif ev.type == pygame.MOUSEWHEEL:
            el = self.gewaehlt()
            if isinstance(el, (ui.Regler,)):
                el.aendern(1 if ev.y > 0 else -1)
                self.geaendert(el)
            elif isinstance(el, ui.Wahl):
                el.blaettern(1 if ev.y > 0 else -1)
                self.geaendert(el)
            else:
                self.wahl_schieben(-1 if ev.y > 0 else 1)

    def taste(self, ev) -> None:
        if ev.key == pygame.K_ESCAPE:
            self.klang("menue", 0.4)
            self.zurueck()
            return
        if ev.key in (pygame.K_UP, pygame.K_w):
            self.wahl_schieben(-1)
        elif ev.key in (pygame.K_DOWN, pygame.K_s):
            self.wahl_schieben(1)
        elif ev.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            d = -1 if ev.key in (pygame.K_LEFT, pygame.K_a) else 1
            el = self.gewaehlt()
            if isinstance(el, ui.Regler):
                el.aendern(d)
                self.geaendert(el)
            elif isinstance(el, ui.Wahl):
                el.blaettern(d)
                self.geaendert(el)
            elif isinstance(el, ui.Schalter):
                el.an = not el.an
                self.geaendert(el)
            elif isinstance(el, ui.Reiter):
                self.reiter_blaettern(d)
        elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            el = self.gewaehlt()
            if el is not None and not el.gesperrt:
                self.klang("menue_ok", 0.6)
                if isinstance(el, ui.Schalter):
                    el.an = not el.an
                    self.geaendert(el)
                elif isinstance(el, ui.Wahl):
                    el.blaettern(1)
                    self.geaendert(el)
                else:
                    self.ausloesen(el)

    def reiter_blaettern(self, d: int) -> None:
        pass

    def maus_druck(self, pos) -> None:
        for el in self.elemente:
            if el.gesperrt:
                continue
            if isinstance(el, ui.Regler):
                if el.rect.collidepoint(pos):
                    el.zieht = True
                    el.wert = el.aus_x(int(pos.x))
                    self.geaendert(el)
                    self.klang("menue", 0.3)
                    return
            elif isinstance(el, ui.Wahl):
                if el.klick(pos):
                    self.geaendert(el)
                    self.klang("menue", 0.4)
                    return
            elif isinstance(el, ui.Schalter):
                if el.rect.collidepoint(pos):
                    el.an = not el.an
                    self.geaendert(el)
                    self.klang("menue_ok", 0.5)
                    return
            elif el.klick(pos):
                el.gedrueckt = True
                self.klang("menue_ok", 0.6)
                self.ausloesen(el)
                return

    # ---- Bild --------------------------------------------------------
    @property
    def oben_auf(self) -> bool:
        """Liegt noch ein Menue darueber, zeichnet dieses hier gar nichts.

        Sonst staffelten sich zwei Schleier und zwei Tafeln uebereinander,
        und das Bild wuerde mit jeder Ebene dunkler und unruhiger.
        """
        return self.app.oben is self

    def zeichnen(self, ziel, alpha: float) -> None:
        if not self.oben_auf:
            return
        ui.schleier(ziel, 178)
        self.rahmen_zeichnen(ziel)
        for i, el in enumerate(self.elemente):
            el.ueber = (i == self.wahl) and not el.gesperrt
            el.zeichnen(ziel)
        self.inhalt_zeichnen(ziel)
        self.fuss_zeichnen(ziel)

    def rahmen_zeichnen(self, ziel) -> None:
        r = getattr(self, "tafel", TAFEL_GROSS)
        ui.tafel(ziel, r)
        if self.titel:
            SCHRIFT.zeichnen(ziel, self.titel, r.centerx, r.y + 8, K.C_AMBER, 2,
                             2, "mitte")
            pygame.draw.line(ziel, K.C_MUTED_DK, (r.x + 18, r.y + 24),
                             (r.right - 19, r.y + 24))
        if self.unterzeile:
            SCHRIFT.zeichnen(ziel, self.unterzeile, r.centerx, r.y + 28,
                             K.C_MUTED, 1, 1, "mitte")

    def fuss_zeichnen(self, ziel) -> None:
        r = getattr(self, "tafel", TAFEL_GROSS)
        if self.meldung:
            SCHRIFT.zeichnen(ziel, self.meldung, r.centerx, r.bottom - 13,
                             K.C_TEAL, 1, 1, "mitte")
            return
        hinweis = self.fusstext()
        if hinweis:
            SCHRIFT.zeichnen(ziel, hinweis, r.centerx, r.bottom - 13,
                             K.C_MUTED_DK, 1, 1, "mitte")

    def fusstext(self) -> str:
        return "[PFEILE] WAEHLEN   [ENTER] OEFFNEN   [ESC] ZURUECK"


# ══════════════════════════════════════════════════════════════════
# Pause
# ══════════════════════════════════════════════════════════════════

class Pause(Menue):
    """Was man sieht, wenn man mitten im Gefecht Escape drueckt."""

    titel = "PAUSE"

    def __init__(self, app, spiel) -> None:
        self.spiel = spiel
        self.tafel = _mitte(232, 246)
        super().__init__(app)

    def aufbauen(self) -> None:
        r = self.tafel
        eintraege = [
            ("FORTSETZEN", "weiter"),
            ("EINSTELLUNGEN", "opt"),
            ("STEUERUNG", "tasten"),
            ("MITWIRKENDE", "credits"),
            ("AUFGEBEN", "raus"),
        ]
        bx, bw, bh = r.x + 24, r.width - 48, 22
        by = r.y + 44
        self.elemente = [
            ui.Knopf((bx, by + i * (bh + 6), bw, bh), text, name)
            for i, (text, name) in enumerate(eintraege)
        ]

    def ausloesen(self, el) -> None:
        if el.name == "weiter":
            self.zurueck()
        elif el.name == "opt":
            self.app.schieben(Einstellungen(self.app))
        elif el.name == "tasten":
            self.app.schieben(Steuerung(self.app))
        elif el.name == "credits":
            self.app.schieben(Mitwirkende(self.app))
        elif el.name == "raus":
            self.app.laeuft = False

    def inhalt_zeichnen(self, ziel) -> None:
        r = self.tafel
        s = self.spiel
        y = r.bottom - 42
        pygame.draw.line(ziel, K.C_MUTED_DK, (r.x + 18, y - 6), (r.right - 19, y - 6))
        SCHRIFT.zeichnen(ziel, "WELLE %d" % s.welle, r.x + 24, y, K.C_MUTED, 1)
        SCHRIFT.zeichnen(ziel, "SCHROTT %d" % s.held.punkte, r.right - 24, y,
                         K.C_AMBER, 1, 1, "rechts")
        SCHRIFT.zeichnen(ziel, "EBENE %d" % s.held.ebene, r.x + 24, y + 10,
                         K.C_MUTED, 1)
        SCHRIFT.zeichnen(ziel, "%s %s" % (K.PHASE, K.VERSION), r.right - 24,
                         y + 10, K.C_MUTED_DK, 1, 1, "rechts")

    def fusstext(self) -> str:
        return "[ESC] WEITERSPIELEN"


# ══════════════════════════════════════════════════════════════════
# Einstellungen
# ══════════════════════════════════════════════════════════════════

# Was die gewaehlte Zeile bewirkt, in zwei bis drei kurzen Saetzen. Steht
# hier und nicht im Elementnamen, damit die Erklaerung wachsen kann, ohne
# dass das Menue umgebaut werden muss.
HILFE = {
    "_": ["ZEILE WAEHLEN, UM MEHR ZU ERFAHREN."],
    "fenstermodus": [
        "FENSTER LAESST SICH VERSCHIEBEN UND IN DER GROESSE ZIEHEN.",
        "RANDLOS FUELLT DEN BILDSCHIRM, ALT+TAB BLEIBT SCHNELL.",
        "VOLLBILD UEBERNIMMT DEN BILDSCHIRM GANZ ALLEIN.",
    ],
    "aufloesung": [
        "GROESSE DES FENSTERS. IM VOLLBILD GILT DER BILDSCHIRM.",
        "GERECHNET WIRD IMMER MIT 640 MAL 360 UND DANN VERGROESSERT.",
    ],
    "bildrate": [
        "OBERGRENZE DER BILDER JE SEKUNDE.",
        "UNBEGRENZT IST FLUESSIGER, BEGRENZT SCHONT AKKU UND LUEFTER.",
        "DIE SPIELREGEL LAEUFT IMMER MIT 120 SCHRITTEN, UNABHAENGIG DAVON.",
    ],
    "pixelraster": [
        "FUELLT DAS FENSTER NUTZT JEDEN PIXEL, KANN ABER LEICHT WISCHEN.",
        "GANZE PIXEL VERGROESSERT NUR UM 2X, 3X, 4X - GESTOCHEN SCHARF,",
        "DAFUER BLEIBT AUSSEN EIN SCHWARZER RAND STEHEN.",
    ],
    "ton_gesamt": ["REGELT ALLES ZUSAMMEN, AUCH SPAETERE MUSIK."],
    "ton_effekte": [
        "SCHUESSE, SCHRITTE, EINSCHLAEGE.",
        "WIRD MIT GESAMT MULTIPLIZIERT, NICHT ERSETZT.",
    ],
    "ton_musik": [
        "LAUTSTAERKE DER MUSIK.",
        "NOCH OHNE WIRKUNG - ES GIBT BISHER KEINE STUECKE.",
    ],
    "probe": ["SPIELT EINEN SCHUSS, DAMIT MAN DIE LAUTSTAERKE HOERT."],
    "vignette": ["DUNKLE ECKEN. ZIEHT DEN BLICK ZUR MITTE."],
    "bildschirm_ruckeln": [
        "WIE STARK DAS BILD BEI SCHUESSEN UND TREFFERN WACKELT.",
        "AUF 0 STEHT ES VOLLKOMMEN STILL.",
    ],
    "partikel": ["MENGE AN STAUB, FUNKEN UND HUELSEN."],
    "spaeter0": ["RICHTUNGSLICHT UND ECHTE SCHATTEN. SPAETER."],
    "spaeter1": ["STAUBWEHEN UND WETTER UEBER DER KARTE. SPAETER."],
    "spaeter2": ["UMSCHALTEN ZWISCHEN TEXTURSAETZEN. SPAETER."],
    "reset": ["SETZT ALLE WERTE DIESER SEITEN AUF DIE VORGABE ZURUECK."],
    "zurueck": ["ZURUECK ZUM PAUSENMENUE. GESPEICHERT IST SCHON ALLES."],
    "reiter_anzeige": ["FENSTER, AUFLOESUNG, BILDRATE."],
    "reiter_ton": ["LAUTSTAERKEN."],
    "reiter_grafik": ["EFFEKTE UND WAS SPAETER DAZUKOMMT."],
}


class Einstellungen(Menue):
    """Drei Seiten hinter Reitern: Anzeige, Ton, Grafik."""

    titel = "EINSTELLUNGEN"
    SEITEN = [("ANZEIGE", "anzeige"), ("TON", "ton"), ("GRAFIK", "grafik")]

    def __init__(self, app, seite: int = 0) -> None:
        self.seite = seite
        self.tafel = TAFEL_GROSS.copy()
        super().__init__(app)
        # Beim Oeffnen steht die Auswahl auf der ersten echten Zeile, nicht
        # auf dem Reiter. Sonst erklaert der Kasten unten den Reiter.
        self.wahl = len(self.reiter)

    # ---- Aufbau ------------------------------------------------------
    def aufbauen(self) -> None:
        r = self.tafel
        self.elemente = []
        # Reiter
        bw = 108
        bx = r.centerx - (len(self.SEITEN) * (bw + 4) - 4) // 2
        self.reiter = []
        for i, (text, name) in enumerate(self.SEITEN):
            t = ui.Reiter((bx + i * (bw + 4), r.y + 30, bw, 15), text, "reiter_" + name)
            t.aktiv = (i == self.seite)
            self.reiter.append(t)
            self.elemente.append(t)

        zx, zw = r.x + 26, r.width - 52
        zy = r.y + 58
        baue = (self._seite_anzeige, self._seite_ton, self._seite_grafik)[self.seite]
        baue(zx, zy, zw)

        # Fussknoepfe
        fy = r.bottom - 40
        self.elemente.append(ui.Knopf((r.x + 26, fy, 120, 18), "ZURUECKSETZEN",
                                      "reset"))
        self.elemente.append(ui.Knopf((r.right - 26 - 96, fy, 96, 18), "ZURUECK",
                                      "zurueck"))

    def _reihe(self, zx, zy, zw, i):
        return (zx, zy + i * (ZEILE_H + ZEILE_ABSTAND), zw, ZEILE_H)

    def _seite_anzeige(self, zx, zy, zw) -> None:
        o = self.app.opt
        self.elemente += [
            ui.Wahl(self._reihe(zx, zy, zw, 0), "FENSTERMODUS", "fenstermodus",
                    E.FENSTERMODI, self._index(E.FENSTERMODI, o["fenstermodus"]),
                    E.BESCHRIFTUNG["fenstermodus"]),
            ui.Wahl(self._reihe(zx, zy, zw, 1), "AUFLOESUNG", "aufloesung",
                    E.AUFLOESUNGEN, self._index(E.AUFLOESUNGEN, o["aufloesung"])),
            ui.Wahl(self._reihe(zx, zy, zw, 2), "BILDRATE", "bildrate",
                    E.BILDRATEN, self._index(E.BILDRATEN, o["bildrate"]),
                    E.BESCHRIFTUNG["bildrate"]),
            ui.Wahl(self._reihe(zx, zy, zw, 3), "PIXELRASTER", "pixelraster",
                    E.RASTER, self._index(E.RASTER, o["pixelraster"]),
                    E.BESCHRIFTUNG["pixelraster"]),
        ]

    def _seite_ton(self, zx, zy, zw) -> None:
        o = self.app.opt
        self.elemente += [
            ui.Regler(self._reihe(zx, zy, zw, 0), "GESAMT", "ton_gesamt",
                      o["ton_gesamt"]),
            ui.Regler(self._reihe(zx, zy, zw, 1), "EFFEKTE", "ton_effekte",
                      o["ton_effekte"]),
            ui.Regler(self._reihe(zx, zy, zw, 2), "MUSIK", "ton_musik",
                      o["ton_musik"]),
        ]
        self.elemente.append(ui.Knopf(self._reihe(zx, zy, 128, 4), "PROBE HOEREN",
                                      "probe"))

    def _seite_grafik(self, zx, zy, zw) -> None:
        o = self.app.opt
        self.elemente += [
            ui.Schalter(self._reihe(zx, zy, zw, 0), "VIGNETTE", "vignette",
                        o["vignette"]),
            ui.Regler(self._reihe(zx, zy, zw, 1), "BILDWACKELN",
                      "bildschirm_ruckeln", o["bildschirm_ruckeln"]),
            ui.Wahl(self._reihe(zx, zy, zw, 2), "PARTIKEL", "partikel",
                    E.PARTIKEL, self._index(E.PARTIKEL, o["partikel"]),
                    E.BESCHRIFTUNG["partikel"]),
        ]
        # Was spaeter kommt, steht schon da, aber grau. So sieht man, wohin
        # es geht, ohne dass etwas ins Leere klickt.
        for i, text in enumerate(("LICHT UND SCHATTEN", "WETTER UND STAUB",
                                  "TEXTURSATZ")):
            self.elemente.append(
                ui.Knopf(self._reihe(zx, zy, zw, 3 + i), text, "spaeter%d" % i,
                         gesperrt=True))

    @staticmethod
    def _index(liste, wert) -> int:
        try:
            return liste.index(wert)
        except ValueError:
            return 0

    # ---- Reaktion ----------------------------------------------------
    def reiter_blaettern(self, d: int) -> None:
        self.seite_wechseln((self.seite + d) % len(self.SEITEN))

    def seite_wechseln(self, nr: int) -> None:
        if nr == self.seite:
            return
        self.seite = nr
        merk = self.wahl
        self.aufbauen()
        # Kam die Auswahl aus einem Reiter, bleibt sie dort. Kam sie aus dem
        # Inhalt, landet sie auf der ersten Zeile der neuen Seite.
        self.wahl = merk if merk < len(self.reiter) else len(self.reiter)
        self.klang("menue", 0.45)

    def ausloesen(self, el) -> None:
        if el.name.startswith("reiter_"):
            self.seite_wechseln([n for _, n in self.SEITEN].index(el.name[7:]))
        elif el.name == "probe":
            self.klang("schuss_sturm", 0.9)
        elif el.name == "reset":
            self.app.opt.zuruecksetzen_werte()
            self.app.anzeige_uebernehmen()
            self.aufbauen()
            self.sagen("EINSTELLUNGEN AUF VORGABE ZURUECKGESETZT")
        elif el.name == "zurueck":
            self.zurueck()

    def geaendert(self, el) -> None:
        o = self.app.opt
        if isinstance(el, ui.Wahl):
            o[el.name] = el.wert
        elif isinstance(el, ui.Regler):
            o[el.name] = el.wert
        elif isinstance(el, ui.Schalter):
            o[el.name] = el.an
        o.speichern()
        if el.name in ("fenstermodus", "aufloesung", "bildrate", "pixelraster"):
            self.app.anzeige_uebernehmen()
            self.aufbauen()
        elif el.name in ("ton_gesamt", "ton_effekte"):
            self.app.klaenge.lautstaerke_setzen(o["ton_gesamt"] / 100.0,
                                                o["ton_effekte"] / 100.0)
            if not getattr(el, "zieht", False):
                self.klang("menue_ok", 0.8)

    # ---- Bild --------------------------------------------------------
    def inhalt_zeichnen(self, ziel) -> None:
        r = self.tafel
        # Erklaerkasten: sagt zur gerade gewaehlten Zeile, was sie bewirkt.
        # So muss niemand raten, was "PIXELRASTER" bedeutet.
        kasten_r = pygame.Rect(r.x + 26, r.bottom - 100, r.width - 52, 50)
        ui.kasten(ziel, kasten_r, (40, 31, 23), (10, 7, 6), 4)
        el = self.gewaehlt()
        zeilen = HILFE.get(getattr(el, "name", ""), HILFE["_"])
        SCHRIFT.zeichnen(ziel, getattr(el, "text", "") or "EINSTELLUNGEN",
                         kasten_r.x + 8, kasten_r.y + 7, K.C_AMBER, 1)
        for i, z in enumerate(zeilen[:3]):
            SCHRIFT.zeichnen(ziel, z, kasten_r.x + 8, kasten_r.y + 20 + i * 10,
                             K.C_MUTED, 1)
        SCHRIFT.zeichnen(ziel, "ABLAGE  " + pfade.beschreibung(), r.x + 26,
                         r.bottom - 112, K.C_MUTED_DK, 1)

    def fusstext(self) -> str:
        return "[LINKS/RECHTS] AENDERN   [ESC] ZURUECK"


# ══════════════════════════════════════════════════════════════════
# Steuerung
# ══════════════════════════════════════════════════════════════════

class Steuerung(Menue):
    """Tastenbelegung. Zeile anklicken, neue Taste druecken, fertig."""

    titel = "STEUERUNG"
    unterzeile = "ZEILE WAEHLEN, DANN NEUE TASTE DRUECKEN"

    def __init__(self, app) -> None:
        self.tafel = TAFEL_GROSS.copy()
        self.wartet_auf: str | None = None
        super().__init__(app)

    def aufbauen(self) -> None:
        r = self.tafel
        o = self.app.opt
        self.elemente = []
        spalten = 2
        je_spalte = math.ceil(len(E.TASTEN_VORGABE) / spalten)
        sw = (r.width - 52 - 16) // spalten
        for i, (name, label, _) in enumerate(E.TASTEN_VORGABE):
            sp, zi = divmod(i, je_spalte)
            x = r.x + 26 + sp * (sw + 16)
            y = r.y + 44 + zi * 15
            self.elemente.append(
                ui.Zeile((x, y, sw, 13), label, name,
                         E.belegung_text(o.tasten.get(name, [])),
                         gesperrt=(name in E.FEST), label_breite=112))
        fy = r.bottom - 40
        self.elemente.append(ui.Knopf((r.x + 26, fy, 120, 18), "ZURUECKSETZEN",
                                      "reset"))
        self.elemente.append(ui.Knopf((r.right - 26 - 96, fy, 96, 18), "ZURUECK",
                                      "zurueck"))

    def ausloesen(self, el) -> None:
        if el.name == "reset":
            self.app.opt.zuruecksetzen_tasten()
            self.app.eingabe.tabelle_setzen(self.app.opt.tastentabelle())
            self.aufbauen()
            self.sagen("BELEGUNG AUF VORGABE ZURUECKGESETZT")
        elif el.name == "zurueck":
            self.zurueck()
        elif isinstance(el, ui.Zeile):
            self.warten(el)

    def warten(self, zeile: ui.Zeile) -> None:
        for el in self.elemente:
            if isinstance(el, ui.Zeile):
                el.wartet = False
        zeile.wartet = True
        self.wartet_auf = zeile.name
        self.sagen("NEUE TASTE FUER %s   [ESC] ABBRECHEN" % zeile.text, 30.0)

    def abbrechen(self) -> None:
        self.wartet_auf = None
        for el in self.elemente:
            if isinstance(el, ui.Zeile):
                el.wartet = False
        self.meldung, self.meldung_rest = "", 0.0

    # Solange eine Zeile wartet, faengt sie jeden Tastendruck ab.
    def taste(self, ev) -> None:
        if self.wartet_auf is None:
            super().taste(ev)
            return
        if ev.key == pygame.K_ESCAPE:
            self.klang("menue", 0.4)
            self.abbrechen()
            return
        aktion = self.wartet_auf
        verdraengt = self.app.opt.belegen(aktion, ev.key)
        self.app.eingabe.tabelle_setzen(self.app.opt.tastentabelle())
        merk = self.wahl
        self.abbrechen()
        self.aufbauen()
        self.wahl = merk
        self.klang("menue_ok", 0.7)
        name = E.taste_kurz(E.taste_name(ev.key))
        if verdraengt:
            label = dict((n, l) for n, l, _ in E.TASTEN_VORGABE).get(verdraengt,
                                                                    verdraengt)
            self.sagen("%s BELEGT - %s IST JETZT FREI" % (name, label))
        else:
            self.sagen("%s BELEGT" % name)

    def maus_druck(self, pos) -> None:
        if self.wartet_auf is not None:
            self.abbrechen()
            return
        super().maus_druck(pos)

    def inhalt_zeichnen(self, ziel) -> None:
        r = self.tafel
        kasten_r = pygame.Rect(r.x + 26, r.bottom - 88, r.width - 52, 38)
        ui.kasten(ziel, kasten_r, (40, 31, 23), (10, 7, 6), 4)
        for i, z in enumerate((
                "MAUS LINKS SCHIESST, MAUS RECHTS ZIELT - FEST VERDRAHTET.",
                "PAUSE LAESST SICH NICHT UMLEGEN, SONST SPERRT MAN SICH AUS.",
                "EINE TASTE GEHOERT IMMER NUR EINER AKTION.")):
            SCHRIFT.zeichnen(ziel, z, kasten_r.x + 8, kasten_r.y + 6 + i * 10,
                             K.C_MUTED, 1)

    def fusstext(self) -> str:
        return "[ENTER] UMLEGEN   [ESC] ZURUECK"


# ══════════════════════════════════════════════════════════════════
# Mitwirkende
# ══════════════════════════════════════════════════════════════════

# Aufbau: ("art", "text"). Die Arten bestimmen Groesse und Farbe.
#   kopf   grosse Ueberschrift
#   teil   Abschnittstitel
#   name   eine Zeile mit Namen
#   rolle  was diese Person gemacht hat, unter dem Namen
#   text   normale Zeile
#   luft   Abstand
MITWIRKENDE = [
    ("luft", ""),
    ("kopf", "DUSTFRONT"),
    ("text", "%s %s" % (K.PHASE, K.VERSION)),
    ("luft", ""),
    ("luft", ""),
    ("teil", "ENTWURF UND UMSETZUNG"),
    ("name", "NICOLAS"),
    ("name", "NIKOLAUS"),
    ("name", "MARLON"),
    ("name", "ALFRED"),
    ("luft", ""),
    ("teil", "WELT"),
    ("rolle", "KARTEN, EBENEN UND DER WEG DAZWISCHEN"),
    ("rolle", "DREI ETAGEN, EIN ABGRUND, KEINE SACKGASSE"),
    ("luft", ""),
    ("teil", "GESTALTUNG"),
    ("rolle", "ALLES IM CODE GEZEICHNET, 640 MAL 360"),
    ("rolle", "GEKAPPTE ECKEN, EIN PIXEL LINIE, BERNSTEIN AUF RUSS"),
    ("luft", ""),
    ("teil", "TON"),
    ("rolle", "JEDER KLANG WIRD GERECHNET, KEINER IST GESAMPELT"),
    ("rolle", "MODALE SYNTHESE FUER HOLZ UND METALL"),
    ("rolle", "GEFILTERTES RAUSCHEN FUER ALLES, WAS STAUBT"),
    ("luft", ""),
    ("teil", "WERKZEUG"),
    ("text", "PYTHON UND PYGAME-CE"),
    ("text", "GESCHRIEBEN OHNE SPIEL-BAUKASTEN"),
    ("luft", ""),
    ("teil", "DANK"),
    ("text", "AN ALLE, DIE EINE FRUEHE FASSUNG ERTRAGEN HABEN"),
    ("text", "UND TROTZDEM GESAGT HABEN, WAS NICHT STIMMT"),
    ("luft", ""),
    ("luft", ""),
    ("text", "IN THE GRIM DARKNESS OF THE FAR FUTURE,"),
    ("text", "THERE IS ONLY WAR"),
    ("luft", ""),
    ("luft", ""),
]

STIL = {
    "kopf":  (3, K.C_AMBER, 22),
    "teil":  (1, K.C_ORANGE, 14),
    "name":  (2, K.C_CREAM, 16),
    "rolle": (1, K.C_MUTED, 10),
    "text":  (1, K.C_MUTED, 10),
    "luft":  (1, K.C_MUTED, 9),
}


class Mitwirkende(Menue):
    """Ein Abspann, der von selbst laeuft und den man anhalten kann."""

    titel = ""
    TEMPO = 17.0          # Pixel je Sekunde

    def __init__(self, app) -> None:
        self.tafel = TAFEL_GROSS.copy()
        self.versatz = 0.0
        self.laeuft = True
        super().__init__(app)
        self.hoehe = sum(STIL[art][2] for art, _ in MITWIRKENDE)

    def aufbauen(self) -> None:
        r = self.tafel
        self.elemente = [ui.Knopf((r.centerx - 48, r.bottom - 44, 96, 18),
                                  "ZURUECK", "zurueck")]

    def ausloesen(self, el) -> None:
        self.zurueck()

    @property
    def sicht(self) -> pygame.Rect:
        r = self.tafel
        return pygame.Rect(r.x + 14, r.y + 14, r.width - 28, r.height - 66)

    # Farbe der Tafelfuellung. Der Abspann laeuft nach oben und unten in
    # genau diesen Ton aus, nicht nach Schwarz - sonst saehe man dort zwei
    # dunkle Balken stehen statt eines weichen Uebergangs.
    GRUND = (9, 6, 5)

    @classmethod
    def _verlauf(cls, breite: int, hoehe: int, unten: bool) -> pygame.Surface:
        """Streifen in Tafelfarbe, der nach innen durchsichtig wird.

        Wird auf die fertige Flaeche geblittet, nicht in das Band gezeichnet:
        eine Linie mit Alpha wuerde die Pixel darunter ersetzen statt sie zu
        mischen, und der Abspann bekaeme einen harten Rand.
        """
        s = pygame.Surface((breite, hoehe), pygame.SRCALPHA)
        for i in range(hoehe):
            a = int(255 * (1.0 - i / float(hoehe)) ** 1.6)
            y = (hoehe - 1 - i) if unten else i
            pygame.draw.line(s, cls.GRUND + (a,), (0, y), (breite, y))
        return s

    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        if self.laeuft:
            self.versatz += self.TEMPO * dt
            # Am Ende von vorn, damit man nie auf eine leere Tafel schaut
            if self.versatz > self.hoehe:
                self.versatz = -self.sicht.height * 0.4

    def taste(self, ev) -> None:
        if ev.key == pygame.K_SPACE:
            self.laeuft = not self.laeuft
            self.klang("menue", 0.4)
            return
        if ev.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
            self.laeuft = False
            self.versatz += -12 if ev.key in (pygame.K_UP, pygame.K_w) else 12
            return
        super().taste(ev)

    def ereignis(self, ev) -> None:
        if ev.type == pygame.MOUSEWHEEL:
            self.laeuft = False
            self.versatz -= ev.y * 14
            return
        super().ereignis(ev)

    def zeichnen(self, ziel, alpha: float) -> None:
        if not self.oben_auf:
            return
        ui.schleier(ziel, 200)
        r = self.tafel
        ui.tafel(ziel, r)

        s = self.sicht
        band = pygame.Surface(s.size, pygame.SRCALPHA)
        y = -self.versatz + s.height * 0.32
        for art, text in MITWIRKENDE:
            skala, farbe, schritt = STIL[art]
            if text and -20 < y < s.height + 20:
                SCHRIFT.zeichnen(band, text, s.width // 2, int(y), farbe, skala,
                                 2 if skala > 1 else 1, "mitte")
            y += schritt
        ziel.blit(band, s.topleft)
        # Oben und unten weich auslaufen lassen, damit nichts hart abschneidet
        ziel.blit(self._verlauf(s.width, 26, False), s.topleft)
        ziel.blit(self._verlauf(s.width, 26, True), (s.x, s.bottom - 26))

        for i, el in enumerate(self.elemente):
            el.ueber = (i == self.wahl)
            el.zeichnen(ziel)
        SCHRIFT.zeichnen(ziel, "[LEERTASTE] ANHALTEN   [ESC] ZURUECK", r.centerx,
                         r.bottom - 15, K.C_MUTED_DK, 1, 1, "mitte")
