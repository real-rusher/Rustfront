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
ENDUNGEN = (".wav", ".ogg")

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


@platzhalter_klang("schuss")
def _schuss(seed=0):
    return _schuss_repetierer(seed)


# ══════════════════════════════════════════════════════════════════
# Registratur
# ══════════════════════════════════════════════════════════════════

class Klaenge:
    FASSUNGEN = 3        # so viele leicht verschiedene Kopien je Platzhalter

    def __init__(self, ordner: Path | None = None) -> None:
        self.ordner = (ordner / "sfx") if ordner is not None else None
        self.ok = False
        self.aus_datei: set[str] = set()
        self._cache: dict[str, list] = {}
        self.rnd = random.Random()
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
        for kandidat in [name] + ["%s_%d" % (name, i) for i in range(1, 9)]:
            for endung in ENDUNGEN:
                pfad = self.ordner / (kandidat + endung)
                if pfad.is_file():
                    try:
                        gefunden.append(pygame.mixer.Sound(str(pfad)))
                        self.aus_datei.add(name)
                    except pygame.error:
                        pass
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
    def spielen(self, name: str, lautstaerke: float = 1.0) -> None:
        fassungen = self.klang(name)
        if not fassungen:
            return
        s = fassungen[self.rnd.randrange(len(fassungen))]
        try:
            s.set_volume(max(0.0, min(1.0, lautstaerke * K.AUDIO["gesamt"])))
            s.play()
        except pygame.error:
            pass

    def stille(self) -> None:
        if self.ok:
            try:
                pygame.mixer.stop()
            except pygame.error:
                pass
