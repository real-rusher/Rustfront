"""
DUSTFRONT - Inventar
====================

Drei Felder nebeneinander und ein Band darunter:

    TRAEGER      was die Figur am Koerper hat (noch leer, kommt spaeter)
    WAFFEN       die sechs Plaetze der Hotbar, umsortierbar
    ANGABEN      Werte der gewaehlten Waffe, im Vergleich zu allen anderen
    TASCHE       Medkits und was sonst noch mitgeht

Der wichtigste Teil ist das Umsortieren. Eine Hotbar, deren Reihenfolge
feststeht, ist keine Hotbar, sondern eine Liste. Also: Waffe mit der Maus
greifen, auf einen anderen Platz ziehen, loslassen - die beiden tauschen.
Mit der Tastatur geht dasselbe, indem man eine Waffe mit Enter aufnimmt,
den Rahmen bewegt und noch einmal Enter drueckt.

Die Munition haengt am Namen der Waffe, nicht am Platz. Umsortieren kostet
also keine Patrone.

Der Balken im Feld ANGABEN vergleicht immer gegen die staerkste Waffe im
Spiel, nicht gegen einen erfundenen Hoechstwert. Ein halber Balken heisst
damit wirklich "halb so viel wie das Beste, was es gibt".
"""

from __future__ import annotations

import pygame

from . import config as K
from . import ui
from .core import Szene
from .font import SCHRIFT

# ══════════════════════════════════════════════════ Masse

TAFEL = pygame.Rect(40, 22, 560, 316)
SPALTE_Y = 54
SPALTE_H = 136
FELD_B, FELD_H = 56, 32          # ein Waffenplatz
TASCHE_SPALTEN = 8


# ══════════════════════════════════════════════════ Werte

def _wert(name: str, feld: str):
    """Ein Vergleichswert einer Waffe, oder None wenn er nicht gilt."""
    d = K.WAFFEN[name]
    if feld == "schaden":
        return d["schaden"] * d.get("geschosse", 1)
    if feld == "takt":
        return 1.0 / d["takt"] if d.get("takt") else None
    if feld == "magazin":
        return d["magazin"] or None
    if feld == "reichweite":
        return d.get("reichweite") or d.get("wurf_max")
    if feld == "streuung":
        s = d.get("streuung")
        # Weniger Streuung ist besser, also umgedreht auftragen.
        return (1.0 / max(0.2, s)) if s is not None else None
    return None


FELDER = [
    ("SCHADEN", "schaden", "%.0f"),
    ("SCHUSS/S", "takt", "%.1f"),
    ("MAGAZIN", "magazin", "%.0f"),
    ("REICHWEITE", "reichweite", "%.0f"),
    ("PRAEZISION", "streuung", None),
]

# Groesster Wert je Feld ueber alle Waffen. Einmal gerechnet, nicht je Bild.
HOECHST = {
    feld: max((v for v in (_wert(n, feld) for n in K.WAFFEN) if v), default=1.0)
    for _, feld, _ in FELDER
}


def symbol(name: str) -> str:
    return "waffe_" + name


class Inventar(Szene):
    """Liegt ueber dem Spiel, friert es ein, gibt es unveraendert zurueck."""

    deckt_zu = False

    def __init__(self, app, spiel) -> None:
        super().__init__(app)
        self.spiel = spiel
        self.held = spiel.held
        self.wahl = self.held.waffe          # Platz im Waffenraster
        self.greift: int | None = None       # aufgenommener Platz, oder None
        self.zieht = False                   # mit der Maus, nicht per Tastatur
        self.maus = pygame.Vector2(0, 0)
        self.meldung = ""
        self.meldung_rest = 0.0
        self.plaetze = self._plaetze_bauen()

    # ---- Aufbau ------------------------------------------------------
    def _plaetze_bauen(self) -> list[pygame.Rect]:
        """Die sechs Waffenplaetze, drei nebeneinander, zwei uebereinander."""
        x0 = TAFEL.x + 16 + 150 + 8 + 3
        y0 = SPALTE_Y + 18
        raus = []
        for i in range(len(K.HOTBAR)):
            zeile, spalte = divmod(i, 3)
            raus.append(pygame.Rect(x0 + spalte * (FELD_B + 4),
                                    y0 + zeile * (FELD_H + 6), FELD_B, FELD_H))
        return raus

    @property
    def hotbar_band(self) -> pygame.Rect:
        return pygame.Rect(TAFEL.x + 16, TAFEL.bottom - 58, TAFEL.width - 32, 26)

    def hotbar_feld(self, i: int) -> pygame.Rect:
        b = self.hotbar_band
        br = (b.width - 5 * 4) // 6
        return pygame.Rect(b.x + i * (br + 4), b.y, br, b.height)

    # ---- Ablauf ------------------------------------------------------
    def betreten(self) -> None:
        self.app.eingabe.alles_loslassen()

    def verlassen(self) -> None:
        self.app.eingabe.alles_loslassen()

    def sagen(self, text: str, dauer: float = 2.2) -> None:
        self.meldung, self.meldung_rest = text, dauer

    def schritt(self, dt: float) -> None:
        self.meldung_rest = max(0.0, self.meldung_rest - dt)
        if self.meldung_rest <= 0:
            self.meldung = ""
        self.maus = self.app.zu_spiel(pygame.mouse.get_pos())
        if not self.zieht:
            for i, r in enumerate(self.plaetze):
                if r.collidepoint(self.maus):
                    self.wahl = i

    def ereignis(self, ev) -> None:
        if ev.type == pygame.KEYDOWN:
            self.taste(ev)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.maus_runter(self.app.zu_spiel(ev.pos))
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self.maus_hoch(self.app.zu_spiel(ev.pos))
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3:
            self.ruesten(self.wahl)

    def taste(self, ev) -> None:
        tab = self.app.opt.codes("inventar")
        if ev.key == pygame.K_ESCAPE or ev.key in tab or ev.key == pygame.K_i:
            if self.greift is not None:
                self.loslassen()
                return
            self.app.werfen()
            return
        # Der Rahmen laeuft im Raster: links und rechts um einen Platz,
        # hoch und runter um eine ganze Zeile.
        schritt = {pygame.K_LEFT: -1, pygame.K_a: -1,
                   pygame.K_RIGHT: 1, pygame.K_d: 1,
                   pygame.K_UP: -3, pygame.K_w: -3,
                   pygame.K_DOWN: 3, pygame.K_s: 3}.get(ev.key)
        if schritt is not None:
            self.bewegen(schritt)
            return
        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            if self.greift is None:
                self.greift = self.wahl
                self.zieht = False
                self.app.klaenge.spielen("menue", 0.5)
                self.sagen("PLATZ WAEHLEN UND NOCH EINMAL ENTER")
            else:
                self.tauschen(self.greift, self.wahl)
                self.loslassen()
            return
        for nr in range(len(self.held.waffen)):
            if ev.key in self.app.opt.codes("waffe%d" % (nr + 1)):
                self.ruesten(nr)
                return
        if ev.key in self.app.opt.codes("heilen"):
            # Das Medkit braucht Zeit. Die laeuft erst, wenn das Spiel wieder
            # rechnet, also sobald man hier herausgeht.
            if self.held.heilen():
                self.sagen("MEDKIT ANGESETZT - WIRKT DRAUSSEN WEITER")
            else:
                self.sagen("KEIN MEDKIT UEBRIG")

    def bewegen(self, d: int) -> None:
        n = len(self.plaetze)
        self.wahl = (self.wahl + d) % n
        self.app.klaenge.spielen("menue", 0.3)

    def maus_runter(self, pos) -> None:
        for i, r in enumerate(self.plaetze):
            if r.collidepoint(pos):
                self.wahl = i
                self.greift = i
                self.zieht = True
                self.app.klaenge.spielen("menue", 0.5)
                return
        for i in range(len(self.held.waffen)):
            if self.hotbar_feld(i).collidepoint(pos):
                self.ruesten(i)
                return

    def maus_hoch(self, pos) -> None:
        if self.greift is None or not self.zieht:
            return
        von = self.greift
        for i, r in enumerate(self.plaetze):
            if r.collidepoint(pos):
                if i == von:
                    self.ruesten(i)          # aufnehmen und gleich wieder
                else:                        # ablegen heisst: anlegen
                    self.tauschen(von, i)
                self.loslassen()
                return
        for i in range(len(self.held.waffen)):
            if self.hotbar_feld(i).collidepoint(pos):
                self.tauschen(von, i)
                self.loslassen()
                return
        self.loslassen()

    def loslassen(self) -> None:
        self.greift = None
        self.zieht = False

    # ---- Wirkung -----------------------------------------------------
    def tauschen(self, a: int, b: int) -> None:
        if a == b:
            return
        w = self.held.waffen
        # Die angelegte Waffe soll dieselbe bleiben, auch wenn ihr Platz
        # sich aendert. Also erst merken, was angelegt ist, dann tauschen.
        angelegt = w[self.held.waffe]
        w[a], w[b] = w[b], w[a]
        self.held.waffe = w.index(angelegt)
        self.wahl = b
        self.app.klaenge.spielen("menue_ok", 0.7)
        self.sagen("%s AUF PLATZ %d" % (K.WAFFEN[w[b]]["name"], b + 1))

    def ruesten(self, i: int) -> None:
        if not (0 <= i < len(self.held.waffen)):
            return
        if self.held.waffe == i:
            return
        self.held.waffe = i
        self.held.nachlade_rest = 0.0
        self.held.fokus = 0.0
        self.wahl = i
        self.app.klaenge.spielen("menue_ok", 0.7)
        self.sagen("ANGELEGT: " + K.WAFFEN[self.held.waffen[i]]["name"])

    # ══════════════════════════════════════════════ Bild
    def zeichnen(self, ziel, alpha: float) -> None:
        if self.app.oben is not self:
            return
        ui.schleier(ziel, 184)
        ui.tafel(ziel, TAFEL)
        SCHRIFT.zeichnen(ziel, "AUSRUESTUNG", TAFEL.centerx, TAFEL.y + 8,
                         K.C_AMBER, 2, 2, "mitte")
        pygame.draw.line(ziel, K.C_MUTED_DK, (TAFEL.x + 18, TAFEL.y + 24),
                         (TAFEL.right - 19, TAFEL.y + 24))

        self._traeger(ziel)
        self._waffen(ziel)
        self._angaben(ziel)
        self._tasche(ziel)
        self._hotbar(ziel)
        self._gegriffenes(ziel)

        if self.meldung:
            SCHRIFT.zeichnen(ziel, self.meldung, TAFEL.centerx,
                             TAFEL.bottom - 24, K.C_TEAL, 1, 1, "mitte")
        SCHRIFT.zeichnen(ziel, "[ZIEHEN] UMSORTIEREN   [RECHTSKLICK] ANLEGEN   "
                               "[TAB] ZURUECK", TAFEL.centerx, TAFEL.bottom - 13,
                         K.C_MUTED_DK, 1, 1, "mitte")

    @staticmethod
    def _feldtitel(ziel, rect, text) -> None:
        ui.kasten(ziel, rect, (44, 35, 26), (8, 6, 5), 4)
        SCHRIFT.zeichnen(ziel, text, rect.x + 6, rect.y + 5, K.C_ORANGE, 1)
        pygame.draw.line(ziel, (44, 35, 26), (rect.x + 4, rect.y + 15),
                         (rect.right - 5, rect.y + 15))

    # ---- Traeger -----------------------------------------------------
    def _traeger(self, ziel) -> None:
        r = pygame.Rect(TAFEL.x + 16, SPALTE_Y, 150, SPALTE_H)
        self._feldtitel(ziel, r, "TRAEGER")

        # Figur in der Mitte, Plaetze links und rechts daneben
        # Dieselbe Figur wie im Spiel, also mit der Waffe in der Hand: man
        # soll im Inventar sehen, was man gerade traegt.
        bild = self.app.bilder.bild(self.spiel.held.bild)
        ziel.blit(bild, (r.centerx - bild.get_width() // 2,
                         r.y + 60 - bild.get_height() // 2))

        plaetze = [("KOPF", -1, 0), ("BRUST", -1, 1), ("ARME", 1, 0),
                   ("BEINE", 1, 1)]
        for text, seite, zeile in plaetze:
            x = r.centerx + seite * 60 - (11 if seite > 0 else 11)
            y = r.y + 26 + zeile * 34
            f = pygame.Rect(x, y, 22, 22)
            ui.feld(ziel, f)
            pygame.draw.line(ziel, (34, 27, 20), (f.centerx - 5, f.centery),
                             (f.centerx + 5, f.centery))
            SCHRIFT.zeichnen(ziel, text, f.centerx, f.bottom + 2, K.C_MUTED_DK,
                             1, 1, "mitte")
        SCHRIFT.zeichnen(ziel, "PANZERUNG KOMMT SPAETER", r.centerx,
                         r.bottom - 12, K.C_MUTED_DK, 1, 1, "mitte")

    # ---- Waffen ------------------------------------------------------
    def _waffen(self, ziel) -> None:
        r = pygame.Rect(TAFEL.x + 16 + 158, SPALTE_Y, 182, SPALTE_H)
        self._feldtitel(ziel, r, "WAFFEN")
        for i, feld in enumerate(self.plaetze):
            name = self.held.waffen[i]
            angelegt = (i == self.held.waffe)
            gewaehlt = (i == self.wahl)
            ui.feld(ziel, feld, gefuellt=True, gewaehlt=gewaehlt)
            if angelegt:
                ui.eckwinkel(ziel, feld, K.C_TEAL, 5, 3)
            if not (self.zieht and self.greift == i):
                self._waffe_zeichnen(ziel, feld, name)
            SCHRIFT.zeichnen(ziel, "%d" % (i + 1), feld.x + 3, feld.y + 3,
                             K.C_AMBER if angelegt else K.C_MUTED_DK, 1)
            d = K.WAFFEN[name]
            if d["magazin"]:
                SCHRIFT.zeichnen(ziel, "%d" % self.held.magazin[name],
                                 feld.right - 3, feld.bottom - 9,
                                 K.C_MUTED, 1, 1, "rechts")
        if self.greift is not None and not self.zieht:
            SCHRIFT.zeichnen(ziel, "AUFGENOMMEN", r.right - 6, r.y + 5,
                             K.C_TEAL, 1, 1, "rechts")
        for i, z in enumerate(("ZIEHEN TAUSCHT ZWEI PLAETZE.",
                               "MUNITION BLEIBT AN DER WAFFE")):
            SCHRIFT.zeichnen(ziel, ui.kuerzen(z, r.width - 12), r.x + 6,
                             r.bottom - 22 + i * 10, K.C_MUTED_DK, 1)

    def _waffe_zeichnen(self, ziel, feld, name) -> None:
        bild = self.app.bilder.bild(symbol(name))
        ziel.blit(bild, (feld.centerx - bild.get_width() // 2,
                         feld.centery - bild.get_height() // 2 + 2))

    # ---- Angaben -----------------------------------------------------
    def _angaben(self, ziel) -> None:
        r = pygame.Rect(TAFEL.x + 16 + 158 + 190, SPALTE_Y, 180, SPALTE_H)
        self._feldtitel(ziel, r, "ANGABEN")
        name = self.held.waffen[self.wahl]
        d = K.WAFFEN[name]
        SCHRIFT.zeichnen(ziel, d["name"], r.x + 6, r.y + 20, K.C_CREAM, 1)
        art = {"schuss": "SCHUSSWAFFE", "wurf": "WURFWAFFE",
               "nahkampf": "NAHKAMPF"}[d["art"]]
        SCHRIFT.zeichnen(ziel, art, r.right - 6, r.y + 20, K.C_MUTED_DK, 1,
                         1, "rechts")

        y = r.y + 34
        for beschriftung, feld, form in FELDER:
            v = _wert(name, feld)
            SCHRIFT.zeichnen(ziel, beschriftung, r.x + 6, y, K.C_MUTED, 1)
            bahn = pygame.Rect(r.x + 74, y + 1, 72, 5)
            pygame.draw.rect(ziel, (26, 20, 15), bahn)
            if v is None:
                SCHRIFT.zeichnen(ziel, "-", r.right - 6, y, K.C_MUTED_DK, 1,
                                 1, "rechts")
            else:
                anteil = max(0.03, min(1.0, v / HOECHST[feld]))
                pygame.draw.rect(ziel, K.C_AMBER,
                                 (bahn.x, bahn.y, int(bahn.width * anteil), 5))
                text = (form % v) if form else "%d%%" % round(anteil * 100)
                SCHRIFT.zeichnen(ziel, text, r.right - 6, y, K.C_CREAM, 1,
                                 1, "rechts")
            y += 11

        SCHRIFT.zeichnen(ziel, ui.kuerzen("BALKEN: ANTEIL AM BESTWERT",
                                          r.width - 12),
                         r.x + 6, y + 2, K.C_MUTED_DK, 1)
        if d["art"] == "schuss" and d.get("fokus_dauer"):
            hinweis = "MIT RECHTS ZIELT MAN EIN"
        elif d["art"] == "wurf":
            hinweis = "FLIEGT SO WEIT WIE GEZIELT"
        elif d["art"] == "nahkampf":
            hinweis = "BRAUCHT KEINE MUNITION"
        else:
            hinweis = ""
        if hinweis:
            SCHRIFT.zeichnen(ziel, ui.kuerzen(hinweis, r.width - 12), r.x + 6,
                             y + 14, K.C_TEAL_DK, 1)

    # ---- Tasche ------------------------------------------------------
    def _tasche(self, ziel) -> None:
        r = pygame.Rect(TAFEL.x + 16, SPALTE_Y + SPALTE_H + 8,
                        TAFEL.width - 32, 52)
        self._feldtitel(ziel, r, "TASCHE")
        bx, by, bs = r.x + 6, r.y + 20, 24
        luecke = (r.width - 12 - TASCHE_SPALTEN * bs) // (TASCHE_SPALTEN - 1)
        medkit = self.app.bilder.bild("medkit")
        for i in range(TASCHE_SPALTEN):
            f = pygame.Rect(bx + i * (bs + luecke), by, bs, bs)
            voll = i < self.held.medkits
            ui.feld(ziel, f, gefuellt=voll)
            if voll:
                ziel.blit(medkit, (f.centerx - medkit.get_width() // 2,
                                   f.centery - medkit.get_height() // 2))
        SCHRIFT.zeichnen(ziel, "MEDKITS %d/%d   [H] BENUTZEN"
                         % (self.held.medkits, K.MEDKIT["hoechstens"]),
                         r.right - 6, r.y + 5, K.C_MUTED, 1, 1, "rechts")

    # ---- Hotbar ------------------------------------------------------
    def _hotbar(self, ziel) -> None:
        # Zeigt genau das, was im Gefecht unten am Bildschirm steht: Zahl,
        # Symbol, Magazin. Wer hier umsortiert, sieht sofort, wie es nachher
        # aussieht.
        b = self.hotbar_band
        SCHRIFT.zeichnen(ziel, "HOTBAR", b.x, b.y - 10, K.C_ORANGE, 1)
        SCHRIFT.zeichnen(ziel, "SO SIEHT ES IM GEFECHT AUS", b.right, b.y - 10,
                         K.C_MUTED_DK, 1, 1, "rechts")
        for i, name in enumerate(self.held.waffen):
            f = self.hotbar_feld(i)
            angelegt = (i == self.held.waffe)
            ui.kasten(ziel, f, K.C_AMBER if angelegt else K.C_MUTED_DK,
                      (26, 18, 11) if angelegt else (13, 10, 7), 3)
            self._waffe_zeichnen(ziel, f, name)
            SCHRIFT.zeichnen(ziel, "%d" % (i + 1), f.x + 3, f.y + 3,
                             K.C_AMBER if angelegt else K.C_MUTED_DK, 1)
            d = K.WAFFEN[name]
            SCHRIFT.zeichnen(ziel, "%d" % self.held.magazin[name] if d["magazin"]
                             else "--", f.right - 3, f.bottom - 9,
                             K.C_AMBER if angelegt else K.C_MUTED_DK, 1,
                             1, "rechts")

    def _gegriffenes(self, ziel) -> None:
        """Was am Mauszeiger haengt, waehrend man zieht."""
        if self.greift is None or not self.zieht:
            return
        name = self.held.waffen[self.greift]
        bild = self.app.bilder.bild(symbol(name))
        ziel.blit(bild, (int(self.maus.x) - bild.get_width() // 2,
                         int(self.maus.y) - bild.get_height() // 2))
