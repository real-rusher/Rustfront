"""
DUSTFRONT - Ton
===============

Dieselbe Idee wie bei den Bildern: `klang("schuss_repetierer")` sucht zuerst
eine Datei, und nimmt nur dann den im Code erzeugten Platzhalter, wenn keine
da ist.

Gesucht wird in dieser Reihenfolge, im Ordner `assets/sfx`:

    schuss_repetierer.wav
    schuss_repetierer.ogg
    schuss.wav                 (allgemeiner Rueckfall ohne Waffenname)
    schuss.ogg

Wenn du also spaeter eine Aufnahme schickst, legen wir sie als
`assets/sfx/schuss_repetierer.wav` ab, und am Spielcode aendert sich nichts.

Damit ein Dauerfeuer nicht wie ein Maschinengewehr aus einer einzigen Kopie
klingt, gibt es von jedem Platzhalter drei Fassungen, aus denen zufaellig
gewaehlt wird. Bei echten Dateien passiert dasselbe, sobald
`schuss_repetierer_1.wav`, `_2` und so weiter daneben liegen.
"""

from __future__ import annotations

import array
import math
import random
from pathlib import Path

import pygame

from . import config as K

RATE = 44100
ENDUNGEN = K.ASSETS["ton_endungen"]

_PLATZHALTER = {}


def platzhalter_klang(name):
    """Registriert einen Erzeuger fuer einen Klang, den es noch nicht gibt."""
    def deko(fn):
        _PLATZHALTER[name] = fn
        return fn
    return deko


# ══════════════════════════════════════════════════════════════════
# Kleine Klangwerkstatt
# ══════════════════════════════════════════════════════════════════

def _rauschen(dur, vol, lp0, lp1, decay=2.4, seed=0, hp=False):
    """Gefiltertes Rauschen. Der Knall eines Schusses ist im Kern genau das."""
    n = max(1, int(RATE * dur))
    r = random.Random(seed)
    out = [0.0] * n
    y = prev = 0.0
    for i in range(n):
        p = i / n
        k = 1 - math.exp(-2 * math.pi * (lp0 + (lp1 - lp0) * p) / RATE)
        y += k * (r.uniform(-1.0, 1.0) - y)
        s = (y - prev) if hp else y
        prev = y
        out[i] = s * (1 - p) ** decay * vol
    return out


def _schlag(f0, f1, dur, vol, decay=3.0):
    """Tiefer Stoss mit fallender Tonhoehe, gibt dem Schuss Koerper."""
    n = max(1, int(RATE * dur))
    out = [0.0] * n
    ph = 0.0
    tp = 2 * math.pi
    for i in range(n):
        p = i / n
        ph += tp * (f0 * (1 - p) + f1 * p) / RATE
        out[i] = math.sin(ph) * (1 - p) ** decay * vol
    return out


def _mischen(*teile):
    n = max(len(t) for t in teile)
    out = [0.0] * n
    for t in teile:
        for i, s in enumerate(t):
            out[i] += s
    return out


def _zu_sound(proben, gain=1.0):
    init = pygame.mixer.get_init()
    if not init:
        return None
    kanaele = init[2]
    n = len(proben)
    aus = min(n // 3, int(0.008 * RATE))          # kurzer Ausklang, sonst knackt es
    for i in range(aus):
        proben[n - 1 - i] *= i / aus
    spitze = max(1e-6, max(abs(s) for s in proben))
    norm = min(1.0, 0.94 / spitze) if spitze > 0.94 else 1.0
    buf = array.array("h")
    for s in proben:
        v = int(max(-1.0, min(1.0, s * norm * gain)) * 31000)
        buf.append(v)
        if kanaele > 1:
            buf.append(v)
    try:
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except pygame.error:
        return None


# ══════════════════════════════════════════════════════════════════
# Platzhalter
# ══════════════════════════════════════════════════════════════════

@platzhalter_klang("schuss_repetierer")
def _schuss_repetierer(seed=0):
    """Trockener, harter Knall mit kurzem Metallnachhall."""
    return _mischen(
        _rauschen(0.16, 0.95, 7000, 900, 3.2, seed + 1),
        _rauschen(0.05, 0.55, 12000, 6000, 2.0, seed + 2, hp=True),
        _schlag(180, 62, 0.13, 0.65, 3.4),
        [0.0] * int(RATE * 0.012) + _rauschen(0.22, 0.16, 2600, 700, 2.6, seed + 3),
    )


@platzhalter_klang("schuss_schrot")
def _schuss_schrot(seed=0):
    """Tiefer, breiter Schlag, laenger im Ausklang."""
    return _mischen(
        _rauschen(0.34, 1.0, 4200, 320, 2.1, seed + 11),
        _rauschen(0.06, 0.45, 9000, 3000, 1.8, seed + 12, hp=True),
        _schlag(120, 44, 0.30, 0.85, 2.6),
        [0.0] * int(RATE * 0.02) + _rauschen(0.40, 0.22, 1400, 380, 2.2, seed + 13),
    )


@platzhalter_klang("schuss_sturm")
def _schuss_sturm(seed=0):
    """Kuerzer und haerter als der Repetierer, fuer Dauerfeuer gedacht."""
    return _mischen(
        _rauschen(0.11, 0.9, 8000, 1400, 3.6, seed + 21),
        _rauschen(0.04, 0.5, 13000, 7000, 2.2, seed + 22, hp=True),
        _schlag(210, 84, 0.09, 0.55, 3.8),
    )


@platzhalter_klang("schuss_scharf")
def _schuss_scharf(seed=0):
    """Ein einzelner, sehr lauter Knall mit langem Nachhall."""
    return _mischen(
        _rauschen(0.55, 1.0, 6500, 240, 1.8, seed + 31),
        _rauschen(0.07, 0.6, 11000, 4000, 1.6, seed + 32, hp=True),
        _schlag(150, 46, 0.34, 0.9, 2.2),
        [0.0] * int(RATE * 0.03) + _rauschen(0.7, 0.3, 1800, 300, 1.9, seed + 33),
    )


@platzhalter_klang("granate")
def _granate(seed=0):
    """Tiefer Schlag, Druckwelle, langes Grollen."""
    return _mischen(
        _schlag(90, 28, 0.9, 1.0, 1.8),
        _rauschen(0.8, 0.9, 5000, 160, 1.5, seed + 41),
        [0.0] * int(RATE * 0.04) + _rauschen(1.2, 0.45, 900, 120, 1.4, seed + 42),
    )


@platzhalter_klang("nahkampf")
def _nahkampf(seed=0):
    """Metall auf Metall, kurz und scharf."""
    return _mischen(
        _rauschen(0.10, 0.7, 9000, 2200, 3.4, seed + 51, hp=True),
        _schlag(620, 280, 0.12, 0.4, 3.0),
        _schlag(1400, 900, 0.09, 0.25, 4.0),
    )


@platzhalter_klang("wurf")
def _wurf(seed=0):
    return _rauschen(0.22, 0.4, 1800, 5200, 1.6, seed + 61, hp=True)


@platzhalter_klang("medkit")
def _medkit(seed=0):
    return _mischen(_schlag(520, 760, 0.18, 0.35, 2.0),
                    _rauschen(0.12, 0.2, 3000, 900, 2.4, seed + 71))


@platzhalter_klang("aufheben")
def _aufheben(seed=0):
    return _mischen(_schlag(880, 1180, 0.12, 0.3, 2.4),
                    _schlag(1320, 1760, 0.09, 0.18, 3.0))


@platzhalter_klang("menue")
def _menue(seed=0):
    return _schlag(660, 720, 0.05, 0.22, 3.0)


# ── Der Wandler ───────────────────────────────────────────────────
#
# Der Schritt ist der wichtigste Klang im ganzen Spiel: er ist das, was aus
# einer Bewegung einen Vorgang macht. Er besteht aus drei Lagen, und jede
# hat eine Aufgabe:
#
#   Einschlag   ein tiefer Stoss - die Masse, die aufsetzt
#   Blech       kurzes helles Scheppern - die Platte, die schwingt
#   Staub       Rauschen, das ausklingt - was aufgewirbelt wird
#
# Ohne die tiefe Lage klingt es nach Schritt, nicht nach Maschine. Ohne die
# helle nach Sack, nicht nach Stahl.

@platzhalter_klang("schritt")
def _schritt(seed=0):
    r = random.Random(seed * 17 + 3)
    f = 52 + r.uniform(-6, 6)
    return _mischen(
        _schlag(f, f * 0.42, 0.20, 0.95, 2.6),          # Masse
        _schlag(f * 5.4, f * 3.1, 0.07, 0.30, 5.0),     # Blech
        _rauschen(0.26, 0.30, 2600, 380, 2.8, seed),    # Staub
    )


@platzhalter_klang("servo")
def _servo(seed=0):
    """Ein Bein schwingt durch: Hydraulik, kein Anschlag."""
    r = random.Random(seed * 31 + 9)
    n = int(RATE * 0.17)
    out = [0.0] * n
    ph = 0.0
    grund = 210 + r.uniform(-25, 25)
    for i in range(n):
        p = i / n
        ph += 2 * math.pi * (grund * (1 + 0.55 * math.sin(math.pi * p))) / RATE
        huell = math.sin(math.pi * p) ** 1.4
        out[i] = (math.sin(ph) * 0.5 + math.sin(ph * 2.02) * 0.2) * huell * 0.34
    return _mischen(out, _rauschen(0.17, 0.10, 4200, 1400, 1.6, seed))


@platzhalter_klang("rumpf_stoss")
def _rumpf_stoss(seed=0):
    """Die ganze Maschine setzt hart auf. Tiefer und laenger als ein Schritt."""
    return _mischen(
        _schlag(38, 17, 0.42, 1.0, 2.0),
        _schlag(126, 62, 0.16, 0.34, 4.0),
        _rauschen(0.50, 0.34, 1700, 200, 2.2, seed),
    )


@platzhalter_klang("station_an")
def _station_an(seed=0):
    return _mischen(
        _schlag(300, 620, 0.09, 0.42, 3.0),
        _rauschen(0.07, 0.16, 5200, 2400, 3.0, seed),
    )


@platzhalter_klang("station_aus")
def _station_aus(seed=0):
    return _mischen(
        _schlag(560, 250, 0.10, 0.38, 3.2),
        _rauschen(0.07, 0.13, 4200, 1600, 3.0, seed),
    )


@platzhalter_klang("menue_ok")
def _menue_ok(seed=0):
    return _mischen(_schlag(430, 640, 0.10, 0.28, 2.6),
                    _schlag(880, 1180, 0.08, 0.14, 3.2))


@platzhalter_klang("schuss")
def _schuss(seed=0):
    return _schuss_repetierer(seed)


# ══════════════════════════════════════════════════════════════════
# Registratur
# ══════════════════════════════════════════════════════════════════

class Klaenge:
    FASSUNGEN = K.ASSETS["platzhalter_fassungen"]

    def __init__(self, ordner: Path | None = None) -> None:
        self.ordner = (ordner / K.ASSETS["sfx"]) if ordner is not None else None
        self.ok = False
        self.aus_datei: set[str] = set()
        self.fehler: list[str] = []
        self._cache: dict[str, list] = {}
        self.rnd = random.Random()
        self.gesamt = K.AUDIO["gesamt"]
        self.effekte = 1.0
        try:
            pygame.mixer.init(frequency=RATE, size=-16, channels=2, buffer=512)
            self.ok = pygame.mixer.get_init() is not None
        except pygame.error:
            self.ok = False
        if self.ok:
            try:
                pygame.mixer.set_num_channels(24)
            except pygame.error:
                pass

    # ---- Suchen und Bauen -------------------------------------------
    def _dateien(self, name: str) -> list[pygame.mixer.Sound]:
        """Alle passenden Dateien: name.wav, name_1.wav, name_2.ogg, ..."""
        if self.ordner is None or not self.ordner.is_dir():
            return []
        gefunden = []
        nummern = range(1, K.ASSETS["fassungen"] + 1)
        for kandidat in [name] + ["%s_%d" % (name, i) for i in nummern]:
            for endung in ENDUNGEN:
                pfad = self.ordner / (kandidat + endung)
                if pfad.is_file():
                    try:
                        gefunden.append(pygame.mixer.Sound(str(pfad)))
                        self.aus_datei.add(name)
                    except pygame.error as grund:
                        self.fehler.append("%s: %s" % (pfad.name, grund))
        return gefunden

    def _bauen(self, name: str) -> list:
        # 1. Dateien unter genau diesem Namen
        fassungen = self._dateien(name)
        if fassungen:
            return fassungen
        # 2. Dateien unter dem allgemeinen Namen vor dem Unterstrich
        wurzel = name.split("_")[0]
        if wurzel != name:
            fassungen = self._dateien(wurzel)
            if fassungen:
                return fassungen
        # 3. Platzhalter aus dem Code
        erzeuger = _PLATZHALTER.get(name) or _PLATZHALTER.get(wurzel)
        if erzeuger is None:
            return []
        fassungen = []
        for i in range(self.FASSUNGEN):
            s = _zu_sound(erzeuger(i * 37))
            if s is not None:
                fassungen.append(s)
        return fassungen

    def klang(self, name: str) -> list:
        if not self.ok:
            return []
        hit = self._cache.get(name)
        if hit is None:
            hit = self._bauen(name)
            self._cache[name] = hit
        return hit

    # ---- Abspielen ---------------------------------------------------
    def lautstaerke_setzen(self, gesamt: float, effekte: float) -> None:
        self.gesamt = max(0.0, min(1.0, gesamt))
        self.effekte = max(0.0, min(1.0, effekte))

    def spielen(self, name: str, lautstaerke: float = 1.0) -> None:
        fassungen = self.klang(name)
        if not fassungen:
            return
        s = fassungen[self.rnd.randrange(len(fassungen))]
        try:
            s.set_volume(max(0.0, min(1.0, lautstaerke * self.gesamt * self.effekte)))
            s.play()
        except pygame.error:
            pass

    def stille(self) -> None:
        if self.ok:
            try:
                pygame.mixer.stop()
            except pygame.error:
                pass
