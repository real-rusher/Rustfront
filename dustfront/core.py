"""
DUSTFRONT - Kern
================

Fenster, Zeit, Eingabe, Bilder. Alles, was nichts mit dem Spiel selbst zu tun
hat, aber unter allem liegt.

Vier Entscheidungen, die hier festgezurrt sind und spaeter nicht mehr
angefasst werden muessen:

1. **Fester Zeitschritt.** Die Simulation laeuft immer in Schritten von
   1/120 s, unabhaengig von der Bildrate. Gezeichnet wird dazwischen
   interpoliert. Ohne das haengt spaeter jede Physik an der Bildrate, und das
   nachtraeglich einzubauen heisst, jede Bewegung neu zu schreiben.

2. **Alles rendert auf eine feste Flaeche.** 640x360, danach einmal
   hochskaliert. Pixel bleiben Pixel, jedes Fensterverhaeltnis geht.

3. **Eingabe laeuft ueber Aktionen, nicht ueber Tasten.** Der Spielcode fragt
   "wird VOR gedrueckt", nicht "ist W unten". Tastenbelegung aendern heisst
   dann ein Eintrag in TASTEN.

4. **Bilder kommen aus der Registratur.** Gibt es assets/<name>.png, wird die
   Datei benutzt, sonst ein im Code erzeugter Platzhalter. Beim Austausch
   gegen echte Pixel-Art aendert sich am Spielcode nichts.
"""

from __future__ import annotations

import math
from pathlib import Path

import pygame

from . import config as K

# ══════════════════════════════════════════════════════════════════
# Eingabe
# ══════════════════════════════════════════════════════════════════

TASTEN = {
    "vor":      [pygame.K_w, pygame.K_UP],
    "zurueck":  [pygame.K_s, pygame.K_DOWN],
    "links":    [pygame.K_a, pygame.K_LEFT],
    "rechts":   [pygame.K_d, pygame.K_RIGHT],
    "sprint":   [pygame.K_LSHIFT, pygame.K_RSHIFT],
    "nutzen":   [pygame.K_e],
    "nachladen": [pygame.K_r],
    "waffe1":   [pygame.K_1],
    "waffe2":   [pygame.K_2],
    "pause":    [pygame.K_ESCAPE],
    "debug":    [pygame.K_F3],
    "vollbild": [pygame.K_F11],
}
MAUSTASTEN = {"feuer": 1, "zweit": 3}


class Eingabe:
    """Uebersetzt Tasten und Maus in benannte Aktionen."""

    def __init__(self) -> None:
        self._gehalten: set[str] = set()
        self._gedrueckt: set[str] = set()
        self._losgelassen: set[str] = set()
        self.maus = pygame.Vector2(0, 0)      # in Spielkoordinaten der Flaeche
        self.rad = 0

    def neues_bild(self) -> None:
        self._gedrueckt.clear()
        self._losgelassen.clear()
        self.rad = 0

    def ereignis(self, ev) -> None:
        if ev.type == pygame.KEYDOWN:
            for name, tasten in TASTEN.items():
                if ev.key in tasten:
                    self._gehalten.add(name)
                    self._gedrueckt.add(name)
        elif ev.type == pygame.KEYUP:
            for name, tasten in TASTEN.items():
                if ev.key in tasten:
                    self._gehalten.discard(name)
                    self._losgelassen.add(name)
        elif ev.type == pygame.MOUSEBUTTONDOWN:
            for name, knopf in MAUSTASTEN.items():
                if ev.button == knopf:
                    self._gehalten.add(name)
                    self._gedrueckt.add(name)
        elif ev.type == pygame.MOUSEBUTTONUP:
            for name, knopf in MAUSTASTEN.items():
                if ev.button == knopf:
                    self._gehalten.discard(name)
                    self._losgelassen.add(name)
        elif ev.type == pygame.MOUSEWHEEL:
            self.rad += ev.y

    def gehalten(self, name: str) -> bool:
        return name in self._gehalten

    def gedrueckt(self, name: str) -> bool:
        return name in self._gedrueckt

    def losgelassen(self, name: str) -> bool:
        return name in self._losgelassen

    def richtung(self) -> pygame.Vector2:
        """Bewegungswunsch als Vektor der Laenge 0 oder 1."""
        v = pygame.Vector2(
            (1 if self.gehalten("rechts") else 0) - (1 if self.gehalten("links") else 0),
            (1 if self.gehalten("zurueck") else 0) - (1 if self.gehalten("vor") else 0))
        if v.length_squared() > 1e-6:
            v.normalize_ip()
        return v

    def alles_loslassen(self) -> None:
        self._gehalten.clear()
        self._gedrueckt.clear()
        self._losgelassen.clear()


# ══════════════════════════════════════════════════════════════════
# Bilder
# ══════════════════════════════════════════════════════════════════

_PLATZHALTER = {}


def platzhalter(name):
    """Registriert einen Zeichner fuer ein Bild, das es noch nicht gibt."""
    def deko(fn):
        _PLATZHALTER[name] = fn
        return fn
    return deko


class Bilder:
    """Registratur fuer Sprites.

    bild("wand") liefert assets/wand.png, falls vorhanden, sonst den im Code
    erzeugten Platzhalter. Gedrehte Fassungen werden zwischengespeichert,
    damit pro Bild nicht neu rotiert wird.
    """

    DREH_SCHRITT = 3        # Grad

    def __init__(self, ordner: Path | None = None) -> None:
        self.ordner = ordner
        self._cache: dict[str, pygame.Surface] = {}
        self._dreh: dict[tuple, pygame.Surface] = {}
        self.aus_datei: set[str] = set()

    def bild(self, name: str) -> pygame.Surface:
        hit = self._cache.get(name)
        if hit is not None:
            return hit
        surf = None
        if self.ordner is not None:
            pfad = self.ordner / (name + ".png")
            if pfad.is_file():
                try:
                    surf = pygame.image.load(str(pfad)).convert_alpha()
                    self.aus_datei.add(name)
                except pygame.error:
                    surf = None
        if surf is None:
            zeichner = _PLATZHALTER.get(name)
            if zeichner is None:
                surf = pygame.Surface((K.TILE, K.TILE), pygame.SRCALPHA)
                surf.fill((255, 0, 220, 180))          # auffaellig fehlend
            else:
                surf = zeichner()
        self._cache[name] = surf
        return surf

    def gedreht(self, name: str, winkel: float) -> pygame.Surface:
        k = int(round(winkel / self.DREH_SCHRITT)) * self.DREH_SCHRITT % 360
        key = (name, k)
        hit = self._dreh.get(key)
        if hit is None:
            hit = pygame.transform.rotate(self.bild(name), -k)
            self._dreh[key] = hit
        return hit


# ══════════════════════════════════════════════════════════════════
# Szenen
# ══════════════════════════════════════════════════════════════════

class Szene:
    """Ein Zustand des Spiels. Die App haelt einen Stapel davon."""

    deckt_zu = True          # False = darunterliegende Szene wird mitgezeichnet

    def __init__(self, app: "App") -> None:
        self.app = app

    def betreten(self) -> None:
        pass

    def verlassen(self) -> None:
        pass

    def ereignis(self, ev) -> None:
        pass

    def schritt(self, dt: float) -> None:
        """Fester Simulationsschritt. dt ist immer K.FIXED_DT."""

    def zeichnen(self, ziel: pygame.Surface, alpha: float) -> None:
        """alpha = 0..1 zwischen vorletztem und letztem Schritt."""


# ══════════════════════════════════════════════════════════════════
# Anwendung
# ══════════════════════════════════════════════════════════════════

class App:
    def __init__(self, titel="DUSTFRONT", asset_ordner: Path | None = None,
                 headless=False) -> None:
        self.headless = headless
        pygame.init()
        self.flaeche = pygame.Surface((K.GAME_W, K.GAME_H))
        self.fenster_groesse = tuple(K.START_FENSTER)
        self.vollbild = False
        self.anzeige_setzen()
        pygame.display.set_caption(titel)
        self.flaeche = self.flaeche.convert()

        self.bilder = Bilder(asset_ordner)
        self.eingabe = Eingabe()
        self.uhr = pygame.time.Clock()
        self.stapel: list[Szene] = []
        self.laeuft = True
        self.fps_grenze = K.ZIEL_FPS
        self.debug = False
        self.zeitlupe = 0.0            # Restsekunden kurzer Verlangsamung
        self._rest = 0.0
        self.fps = 0.0

    # ---- Anzeige ----------------------------------------------------
    def anzeige_setzen(self) -> None:
        if self.headless:
            self.fenster = pygame.display.set_mode(K.START_FENSTER)
            self.viewport_rechnen()
            return
        if self.vollbild:
            try:
                groesse = pygame.display.get_desktop_sizes()[0]
            except (pygame.error, AttributeError, IndexError):
                info = pygame.display.Info()
                groesse = (info.current_w, info.current_h)
            versuche = [(groesse, pygame.FULLSCREEN), ((0, 0), pygame.FULLSCREEN)]
        else:
            versuche = [(self.fenster_groesse, pygame.RESIZABLE)]
        for groesse, flags in versuche:
            try:
                self.fenster = pygame.display.set_mode(groesse, flags)
                self.viewport_rechnen()
                return
            except pygame.error:
                continue
        self.vollbild = False
        self.fenster = pygame.display.set_mode(self.fenster_groesse, pygame.RESIZABLE)
        self.viewport_rechnen()

    def viewport_rechnen(self) -> None:
        fw, fh = self.fenster.get_size()
        self.skala = max(0.25, min(fw / K.GAME_W, fh / K.GAME_H))
        w, h = int(K.GAME_W * self.skala), int(K.GAME_H * self.skala)
        self.viewport = pygame.Rect((fw - w) // 2, (fh - h) // 2, w, h)

    def vollbild_wechseln(self) -> None:
        self.vollbild = not self.vollbild
        self.anzeige_setzen()

    def zu_spiel(self, pos) -> pygame.Vector2:
        """Fensterkoordinate in Koordinate der Spielflaeche."""
        return pygame.Vector2((pos[0] - self.viewport.x) / self.skala,
                              (pos[1] - self.viewport.y) / self.skala)

    # ---- Szenenstapel -----------------------------------------------
    def schieben(self, szene: Szene) -> None:
        self.stapel.append(szene)
        szene.betreten()

    def werfen(self) -> None:
        if self.stapel:
            self.stapel.pop().verlassen()

    def ersetzen(self, szene: Szene) -> None:
        while self.stapel:
            self.werfen()
        self.schieben(szene)

    @property
    def oben(self) -> Szene | None:
        return self.stapel[-1] if self.stapel else None

    # ---- Schleife ---------------------------------------------------
    def ereignisse(self) -> None:
        self.eingabe.neues_bild()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.laeuft = False
                return
            if ev.type in (pygame.WINDOWSIZECHANGED, pygame.VIDEORESIZE):
                surf = pygame.display.get_surface()
                if surf is not None:
                    self.fenster = surf
                    if not self.vollbild and not self.headless:
                        self.fenster_groesse = surf.get_size()
                self.viewport_rechnen()
                continue
            if ev.type == pygame.KEYDOWN:
                if ev.key in TASTEN["vollbild"]:
                    self.vollbild_wechseln()
                    continue
                if ev.key in TASTEN["debug"]:
                    self.debug = not self.debug
                    continue
            self.eingabe.ereignis(ev)
            if self.oben is not None:
                self.oben.ereignis(ev)
        self.eingabe.maus = self.zu_spiel(pygame.mouse.get_pos())

    def laufen(self) -> None:
        while self.laeuft and self.stapel:
            echt = self.uhr.tick(self.fps_grenze) / 1000.0
            self.fps = self.uhr.get_fps()
            echt = min(echt, 0.25)
            if self.zeitlupe > 0.0:
                self.zeitlupe -= echt
                echt *= 0.25

            self.ereignisse()
            if not self.laeuft or not self.stapel:
                break

            self._rest += echt
            schritte = 0
            while self._rest >= K.FIXED_DT and schritte < K.MAX_SCHRITTE:
                for szene in self._aktive():
                    szene.schritt(K.FIXED_DT)
                self._rest -= K.FIXED_DT
                schritte += 1
            if schritte == K.MAX_SCHRITTE:
                self._rest = 0.0          # aufgelaufene Zeit verwerfen

            alpha = self._rest / K.FIXED_DT
            self.flaeche.fill(K.C_VOID)
            for szene in self._sichtbar():
                szene.zeichnen(self.flaeche, alpha)
            self.ausgeben()
        pygame.quit()

    def _aktive(self) -> list[Szene]:
        """Nur die oberste Szene rechnet, darunter steht alles still."""
        return self.stapel[-1:]

    def _sichtbar(self) -> list[Szene]:
        i = len(self.stapel) - 1
        while i > 0 and not self.stapel[i].deckt_zu:
            i -= 1
        return self.stapel[i:]

    def ausgeben(self) -> None:
        self.fenster.fill(K.C_VOID)
        self.fenster.blit(pygame.transform.scale(self.flaeche, self.viewport.size),
                          self.viewport.topleft)
        pygame.display.flip()


# ══════════════════════════════════════════════════════════════════
# Kleine Helfer
# ══════════════════════════════════════════════════════════════════

def mische(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def naehern(wert: float, ziel: float, schritt: float) -> float:
    """Bewegt wert um hoechstens schritt in Richtung ziel."""
    if wert < ziel:
        return min(ziel, wert + schritt)
    return max(ziel, wert - schritt)


def winkel_zu(von: pygame.Vector2, nach: pygame.Vector2) -> float:
    return math.degrees(math.atan2(nach.y - von.y, nach.x - von.x))
