"""
DUSTFRONT - Splash-Sequenz
==========================

Spielt die fuenf Karten aus splash-sequenz.tsx ab. Gezeichnet wird in
splash_engine.py, hier stehen Ablauf, Zeitdehnung und Ton.

Zeitdehnung
-----------
Jede Karte laeuft in drei Abschnitten: Aufbau, Standbild, Abblende. Der Aufbau
laeuft etwas langsamer als im Original, damit nichts gehetzt wirkt, und das
Standbild steht lange genug, dass man die Marke wirklich liest. Gesamt rund
35 s. Alle Werte stehen in PHASEN, ein TEMPO von 1.3 bringt die Sequenz auf
etwa 27 s.

Ton
---
Kein Klangbaustein wird zweimal verwendet, jede Karte hat ihre eigene
Erzeugungsart:

    Siegel      modale Synthese (Glocke, Metall) plus Streicherflaeche
    Kaltwerk    Holzstaebe wie ein Marimba, dazu ein warmer Flaechenakkord
    Phosphor    Elektrik: Zeilenpfeifen, Netzbrummen, Entladung, Statik
    Papiermond  Holzpresse und echtes Papierrascheln mit koerniger Huellkurve
    Tafel       laufende Druckmaschine mit Rumpeln und regelmaessigen Schlaegen

Alles wird zur Laufzeit berechnet, keine Audiodateien noetig. Die Erzeugung
laeuft in einem Hintergrundfaden, damit der Start nicht haengt.

Einzeln ansehen:  python rustfront_splash.py
"""

from __future__ import annotations

import array
import math
import random
import threading

import pygame

from splash_engine import Engine, ORDER, LENS, clamp

# ══════════════════════════════════════════════════════════════════
# Einstellungen
# ══════════════════════════════════════════════════════════════════

TEMPO = 1.0          # >1 spielt die ganze Sequenz schneller ab
VORLAUF = 0.45       # Schwarz vor der ersten Karte
SCHEMA = "aurum"     # aurum | glacies | ignis

KARTEN_AN = {"a": True, "c": True, "t": True, "s": True, "b": True}

TEXTE = {
    "name": "DUSTFRONT",
    "motto": "THE STARS ARE THE BIRTHRIGHT OF HUMANITY",
    "sub": "EIN UNABHAENGIGES STUDIO \u00b7 MMXXVI",
    "role": "UNABHAENGIGE SPIELENTWICKLUNG",
    "pname": "KALTWERK",
    "peyebrow": "POWERED BY",
    "psub": "ECHTZEIT-RENDERING & AUDIO",
    "tname": "PHOSPHOR",
    "tsub": "RUNTIME READY",
    "sname": "PAPIERMOND",
    "ssub": "ERZAEHLUNG & KUNSTRICHTUNG",
}

# Pro Karte: (Kartenzeit bis hierhin, echte Sekunden fuer diesen Abschnitt)
# Abschnitt 1 = Aufbau, 2 = Standbild, 3 = Abblende.
PHASEN = {
    "a": [(7.40, 8.20), (9.70, 3.20), (11.0, 1.30)],
    "c": [(1.30, 1.60), (3.00, 2.20), (3.40, 0.40)],
    "t": [(2.80, 3.20), (4.18, 2.00), (4.60, 0.45)],
    "s": [(1.40, 1.80), (3.60, 2.60), (4.00, 0.40)],
    "b": [(2.80, 3.40), (5.60, 2.80), (6.60, 1.00)],
}

NAMEN = {"a": "Siegel", "c": "Kaltwerk", "t": "Phosphor",
         "s": "Papiermond", "b": "Tafel"}


def karten_dauer(key: str) -> float:
    return sum(d for _, d in PHASEN[key]) / TEMPO


def gesamtdauer() -> float:
    return VORLAUF + sum(karten_dauer(k) for k in ORDER if KARTEN_AN.get(k, True))


def karten_zeit(key: str, r: float) -> float:
    """Rechnet echte Sekunden in die Kartenzeit des Originals um."""
    r *= TEMPO
    t0, acc = 0.0, 0.0
    for (t_end, dur) in PHASEN[key]:
        if r <= acc + dur or dur <= 0:
            f = (r - acc) / dur if dur > 0 else 1.0
            return t0 + (t_end - t0) * clamp(f, 0, 1)
        acc += dur
        t0 = t_end
    return LENS[key]


# ══════════════════════════════════════════════════════════════════
# Klangsynthese
# ══════════════════════════════════════════════════════════════════

class Synth:
    """Kleine Werkstatt fuer Klaenge, die nach Material klingen sollen.

    Statt fertiger Toene werden Koerper nachgebaut: modale Synthese fuer
    Metall und Holz, resonant gefiltertes Rauschen fuer Luft und Schleifen,
    koernige Huellkurven fuer Papier.
    """

    def __init__(self, rate=44100):
        self.rate = rate
        self.rnd = random.Random(90210)

    def _n(self, dur):
        return max(1, int(self.rate * dur))

    # ---- Bausteine ------------------------------------------------
    def modal(self, modes, dur, attack=0.002, noise=0.0, noise_lp=1800,
              noise_dec=0.012):
        """Angeschlagener Koerper. modes = [(Frequenz, Abklingzeit, Anteil)].

        Ganzzahlige Verhaeltnisse klingen nach Holz, schiefe nach Metall.
        """
        n = self._n(dur)
        out = [0.0] * n
        rate = self.rate
        tp = 2 * math.pi
        for (f, dec, amp) in modes:
            d = math.exp(-1.0 / (max(0.005, dec) * rate))
            a = amp
            ph = 0.0
            inc = tp * f / rate
            for i in range(n):
                out[i] += math.sin(ph) * a
                ph += inc
                a *= d
        if noise > 0:                       # Anschlagsgeraeusch
            k = 1 - math.exp(-tp * noise_lp / rate)
            d = math.exp(-1.0 / (max(0.002, noise_dec) * rate))
            a = noise
            y = 0.0
            u = self.rnd.uniform
            for i in range(n):
                y += k * (u(-1.0, 1.0) - y)
                out[i] += y * a
                a *= d
        ar = max(1, int(rate * attack))
        for i in range(min(ar, n)):
            out[i] *= i / ar
        return out

    def svf(self, dur, f0, f1, q=2.0, mode="bp", vol=0.4, attack=0.02,
            decay=1.5, curve=1.0):
        """Resonant gefiltertes Rauschen: Luftzug, Zischen, Schleifen."""
        n = self._n(dur)
        out = [0.0] * n
        rate = self.rate
        low = band = 0.0
        u = self.rnd.uniform
        ar = max(1, int(rate * attack))
        damp = 1.0 / max(0.5, q)
        for i in range(n):
            p = (i / n) ** curve
            fc = f0 + (f1 - f0) * p
            f = 2 * math.sin(math.pi * min(0.45, fc / rate))
            x = u(-1.0, 1.0)
            high = x - low - damp * band
            band += f * high
            low += f * band
            s = band if mode == "bp" else (low if mode == "lp" else high)
            out[i] = s * (1 - i / n) ** decay * min(1.0, i / ar) * vol
        return out

    def pad(self, freqs, dur, vol=0.22, attack=0.4, decay=1.4, detune=0.004,
            lp=1700):
        """Weiche Flaeche: verstimmte Saegezaehne durch einen Tiefpass."""
        n = self._n(dur)
        raw = [0.0] * n
        rate = self.rate
        for f in freqs:
            for dt in (-detune, detune):
                ph = 0.0
                inc = (f * (1 + dt)) / rate
                for i in range(n):
                    ph = (ph + inc) % 1.0
                    raw[i] += 2 * ph - 1
        k = 1 - math.exp(-2 * math.pi * lp / rate)
        g = vol / (2.0 * len(freqs))
        ar = max(1, int(rate * attack))
        y = 0.0
        for i in range(n):
            y += k * (raw[i] * g - y)
            raw[i] = y * (1 - i / n) ** decay * min(1.0, i / ar)
        return raw

    def sub(self, f0, f1, dur, vol=0.8, attack=0.2, decay=2.0):
        """Tiefer Anschwellton, kein Schlag."""
        n = self._n(dur)
        out = [0.0] * n
        rate = self.rate
        tp = 2 * math.pi
        ph = 0.0
        ar = max(1, int(rate * attack))
        for i in range(n):
            p = i / n
            ph += tp * (f0 + (f1 - f0) * p) / rate
            out[i] = math.sin(ph) * (1 - p) ** decay * min(1.0, i / ar) * vol
        return out

    def rustle(self, dur, vol=0.3, hp=1100, grain=0.035, attack=0.12):
        """Papier: Rauschen mit unruhiger, koerniger Huellkurve."""
        n = self._n(dur)
        out = [0.0] * n
        rate = self.rate
        u = self.rnd.uniform
        k = 1 - math.exp(-2 * math.pi * hp / rate)
        step = max(1, int(grain * rate))
        ar = max(1, int(rate * attack))
        y = 0.0
        cur = nxt = abs(u(0.2, 1.0))
        for i in range(n):
            if i % step == 0:
                cur = nxt
                nxt = abs(u(0.05, 1.0))
            f = (i % step) / step
            g = cur + (nxt - cur) * f
            x = u(-1.0, 1.0)
            y += k * (x - y)
            out[i] = (x - y) * g * (1 - i / n) ** 1.3 * min(1.0, i / ar) * vol
        return out

    def hum(self, dur, freqs, vol=0.08, attack=0.4, buzz=0.35):
        """Netzbrummen: Grundton mit Oberwellen, leicht angeschmutzt."""
        n = self._n(dur)
        out = [0.0] * n
        rate = self.rate
        tp = 2 * math.pi
        for j, f in enumerate(freqs):
            amp = 1.0 / (1 + j * 1.6)
            ph = 0.0
            inc = tp * f / rate
            for i in range(n):
                s = math.sin(ph)
                out[i] += (s + buzz * s * abs(s)) * amp
                ph += inc
        ar = max(1, int(rate * attack))
        fade = max(1, int(rate * 0.3))
        for i in range(n):
            env = min(1.0, i / ar) * min(1.0, (n - i) / fade)
            out[i] *= env * vol
        return out

    def whine(self, dur, freq, vol=0.06, attack=0.35, drift=0.004):
        """Zeilenpfeifen einer Bildroehre, minimal schwebend."""
        n = self._n(dur)
        out = [0.0] * n
        rate = self.rate
        tp = 2 * math.pi
        ph = 0.0
        ar = max(1, int(rate * attack))
        fade = max(1, int(rate * 0.25))
        for i in range(n):
            f = freq * (1 + drift * math.sin(tp * 0.7 * i / rate))
            ph += tp * f / rate
            env = min(1.0, i / ar) * min(1.0, (n - i) / fade)
            out[i] = math.sin(ph) * env * vol
        return out

    def ratchet(self, dur, ticks, modes, vol=0.4, spread=0.7):
        """Einrasten: viele kleine Anschlaege desselben Koerpers."""
        n = self._n(dur)
        out = [0.0] * n
        for k in range(ticks):
            p = k / max(1, ticks - 1)
            pos = int((p ** spread) * n * 0.94)
            scale = 1.0 + p * 0.35
            tap = self.modal([(f * scale, dec, amp) for (f, dec, amp) in modes],
                             0.09, 0.0005, 0.22, 3000, 0.004)
            g = vol * (0.45 + 0.55 * p)
            for i, s in enumerate(tap):
                if pos + i < n:
                    out[pos + i] += s * g
        return out

    def machine(self, dur, interval=0.27, vol=0.5):
        """Laufende Presse: Rumpeln plus regelmaessige Schlaege."""
        out = self.svf(dur, 150, 520, 1.1, "lp", vol * 0.55, 0.30, 0.25)
        n = len(out)
        k = 0
        while k * interval < dur:
            pos = int(k * interval * self.rate)
            hit = self.modal([(58, 0.20, 0.55), (94, 0.13, 0.28),
                              (223, 0.07, 0.14)], 0.30, 0.001, 0.30, 800, 0.010)
            for i, s in enumerate(hit):
                if pos + i < n:
                    out[pos + i] += s * vol * 0.85
            k += 1
        return out

    def pause(self, dur):
        return [0.0] * self._n(dur)

    @staticmethod
    def mix(*layers):
        n = max(len(l) for l in layers)
        out = [0.0] * n
        for l in layers:
            for i, s in enumerate(l):
                out[i] += s
        return out

    def to_sound(self, samples, gain=1.0):
        init = pygame.mixer.get_init()
        if not init:
            return None
        channels = init[2]
        peak = max(1e-6, max(abs(s) for s in samples))
        norm = min(1.0, 0.92 / peak) if peak > 0.92 else 1.0
        buf = array.array("h")
        for s in samples:
            v = int(max(-1.0, min(1.0, s * norm * gain)) * 32000)
            buf.append(v)
            if channels > 1:
                buf.append(v)
        try:
            return pygame.mixer.Sound(buffer=buf.tobytes())
        except pygame.error:
            return None


# Materialien. Verhaeltnisse bestimmen, wonach ein Koerper klingt.
def _metall(f, dec=0.9, amp=0.5):
    return [(f, dec, amp), (f * 2.76, dec * 0.55, amp * 0.42),
            (f * 5.40, dec * 0.3, amp * 0.22), (f * 8.93, dec * 0.16, amp * 0.1)]


def _glocke(f, dec=2.4, amp=0.5):
    return [(f * 0.5, dec, amp * 0.55), (f, dec * 0.8, amp),
            (f * 2.0, dec * 0.55, amp * 0.45), (f * 2.97, dec * 0.4, amp * 0.28),
            (f * 4.16, dec * 0.25, amp * 0.16)]


def _holz(f, dec=0.32, amp=0.6):
    return [(f, dec, amp), (f * 3.93, dec * 0.35, amp * 0.3),
            (f * 9.5, dec * 0.14, amp * 0.12)]


def _presse(f, dec=0.5, amp=0.7):
    return [(f, dec, amp), (f * 1.58, dec * 0.6, amp * 0.4),
            (f * 2.44, dec * 0.3, amp * 0.2)]


def _baue_klaenge(sy: Synth, key: str) -> dict:
    """Klangwelt je Karte, als Bauauftraege.

    Jeder Eintrag ist eine Funktion, die den Klang erst beim Aufruf rechnet.
    So kostet der erste Einsatz nicht die ganze Karte an Rechenzeit.
    """
    s = {}

    if key == "a":
        # Siegel: Metall und Gold, weiter Raum, nichts Klickendes
        s["zuendung"] = lambda: sy.mix(
                sy.sub(38, 24, 3.2, 0.85, 0.30, 1.8),
                sy.svf(2.6, 90, 900, 1.4, "lp", 0.30, 0.35, 1.1))
        s["bahnen"] = lambda: sy.mix(
                sy.svf(2.4, 320, 3400, 3.2, "bp", 0.30, 0.70, 0.9),
                sy.modal(_glocke(1046.5, 2.2, 0.10), 2.4, 0.6))
        s["messring"] = lambda: sy.ratchet(1.30, 16, _metall(1650, 0.10, 0.34), 0.62)
        s["schwingen"] = lambda: sy.mix(
                sy.svf(1.55, 2100, 320, 1.6, "bp", 0.34, 0.18, 1.3),
                sy.sub(150, 62, 1.2, 0.18, 0.25, 2.2))
        s["stand"] = lambda: sy.modal(_metall(104, 1.35, 0.55), 1.8, 0.002, 0.28, 700, 0.02)
        s["wortmarke"] = lambda: sy.mix(
                sy.modal(_glocke(523.25, 3.0, 0.5), 3.4, 0.004, 0.10, 4200, 0.006),
                sy.pad([261.63, 392.0, 523.25], 3.2, 0.85, 0.75, 1.2))
        s["spruch"] = lambda: sy.pad([784.0, 1046.5, 1318.5], 2.6, 1.25, 0.8, 1.6,
                                 detune=0.006, lp=3200)
    elif key == "c":
        # Kaltwerk: Holzstaebe wie ein Marimba, trocken, kurz
        for i, f in enumerate((392.0, 523.25, 659.25)):
            s["stab%d" % i] = (lambda ff=f: sy.modal(_holz(ff, 0.30, 0.55),
                                                     0.55, 0.001, 0.18, 2600, 0.006))
        s["marke"] = lambda: sy.pad([261.63, 329.63, 392.0, 523.25], 1.7, 1.70,
                                0.14, 1.5, detune=0.003, lp=1500)
        s["strich"] = lambda: sy.svf(0.55, 380, 2600, 1.1, "lp", 0.95, 0.10, 1.6)
    elif key == "t":
        # Phosphor: reine Elektrik, kein Anschlag, nur Spannung
        s["einschalten"] = lambda: sy.mix(
                sy.sub(64, 41, 0.55, 0.55, 0.006, 2.6),
                sy.svf(0.40, 1400, 300, 6.0, "bp", 0.30, 0.004, 2.0))
        s["pfeifen"] = lambda: sy.mix(
                sy.whine(6.2, 7812.0, 0.075),
                sy.hum(6.2, [50.0, 100.0, 150.0], 0.075),
                sy.svf(6.2, 3000, 3400, 0.8, "hp", 0.035, 0.8, 0.05))
        s["taste"] = lambda: sy.modal([(184, 0.045, 0.4), (410, 0.02, 0.15)], 0.10,
                                  0.001, 0.18, 900, 0.007)
        s["entladung"] = lambda: sy.mix(
                sy.svf(0.45, 4600, 520, 7.5, "bp", 0.40, 0.002, 2.4),
                sy.sub(92, 48, 0.34, 0.42, 0.003, 3.0))
        s["abschalten"] = lambda: sy.mix(
                sy.svf(0.55, 6800, 220, 5.0, "bp", 0.30, 0.004, 1.6, curve=0.6),
                sy.svf(0.30, 900, 180, 1.0, "lp", 0.22, 0.004, 2.0))
    elif key == "s":
        # Papiermond: Holzpresse und Papier, tief und weich
        s["presse"] = lambda: sy.mix(
                sy.modal(_presse(84, 0.55, 0.75), 1.1, 0.001, 0.40, 420, 0.030),
                sy.sub(58, 40, 0.5, 0.35, 0.004, 3.0))
        s["nachschlag"] = lambda: sy.modal(_presse(126, 0.28, 0.45), 0.5, 0.001,
                                       0.22, 520, 0.016)
        s["papier"] = lambda: sy.rustle(1.10, 0.60, 900, 0.030, 0.16)
        s["farbe"] = lambda: sy.mix(
                sy.modal(_presse(98, 0.34, 0.5), 0.7, 0.001, 0.26, 380, 0.022),
                sy.rustle(0.55, 0.26, 700, 0.020, 0.08))
        s["marke"] = lambda: sy.modal(_holz(660, 0.16, 0.35), 0.28, 0.001, 0.10,
                                  2200, 0.004)
    elif key == "b":
        # Tafel: laufende Druckmaschine, danach Mechanik
        s["maschine"] = lambda: sy.machine(2.25, 0.27, 0.5)
        s["blende"] = lambda: sy.mix(
                sy.modal(_metall(880, 0.22, 0.4), 0.5, 0.001, 0.2, 3400, 0.005),
                sy.pause(0.075) + sy.modal(_metall(620, 0.30, 0.34), 0.6, 0.001,
                                           0.18, 2800, 0.006))
        s["glanz"] = lambda: sy.modal(_glocke(1318.5, 1.5, 0.38), 1.8, 0.003, 0.05,
                                  5200, 0.004)
        s["zeiger"] = lambda: sy.modal(_metall(1480, 0.18, 0.26), 0.3, 0.001, 0.08,
                                   4000, 0.003)
    return s


# Kartenzeit -> Klang. Deckt sich mit der Choreografie im Original.
CUES = {
    "a": [(0.30, "zuendung"), (1.00, "bahnen"), (1.85, "messring"),
          (2.55, "schwingen"), (3.35, "stand"), (3.75, "wortmarke"),
          (4.85, "spruch")],
    "c": [(0.10, "stab0"), (0.24, "stab1"), (0.38, "stab2"), (0.62, "marke"),
          (0.86, "strich")],
    "t": [(0.02, "einschalten"), (0.05, "pfeifen"), (0.45, "taste"),
          (0.62, "taste"), (0.80, "taste"), (1.08, "taste"), (1.30, "taste"),
          (1.61, "taste"), (1.85, "taste"), (2.22, "entladung"),
          (4.18, "abschalten")],
    "s": [(0.30, "presse"), (0.36, "nachschlag"), (0.52, "papier"),
          (0.78, "farbe"), (1.16, "marke")],
    "b": [(0.15, "maschine"), (1.58, "blende"), (1.70, "glanz"),
          (2.12, "zeiger")],
}


class SplashAudio:
    """Erzeugt die Klaenge im Hintergrund und spielt die Einsaetze ab."""

    def __init__(self, app=None):
        self.ok = bool(pygame.mixer.get_init())
        self.banks: dict[str, dict] = {}
        self.gain = 0.7
        if app is not None:
            try:
                self.gain = (app.settings.vol_master / 100.0) * (app.settings.vol_sfx / 100.0)
            except Exception:
                pass
        if not self.ok:
            return
        try:
            pygame.mixer.set_num_channels(24)
        except pygame.error:
            pass
        sy = Synth(pygame.mixer.get_init()[0])
        self.banks = {k: {} for k in ORDER}
        # Der erste Einsatz muss sofort sitzen, der Rest entsteht nebenher.
        self._bake_one(sy, ORDER[0], CUES[ORDER[0]][0][1])
        threading.Thread(target=self._rest, args=(sy,), daemon=True).start()

    def _bake_one(self, sy, key, name):
        try:
            bauauftrag = _baue_klaenge(sy, key).get(name)
            if bauauftrag is None:
                return
            snd = sy.to_sound(bauauftrag())
            if snd is not None:
                snd.set_volume(max(0.0, min(1.0, self.gain)))
                self.banks.setdefault(key, {})[name] = snd
        except Exception:
            pass

    def _rest(self, sy):
        for key in ORDER:
            try:
                bank = self.banks.setdefault(key, {})
                for name, bauauftrag in _baue_klaenge(sy, key).items():
                    if name in bank:
                        continue
                    snd = sy.to_sound(bauauftrag())
                    if snd is not None:
                        snd.set_volume(max(0.0, min(1.0, self.gain)))
                        bank[name] = snd
            except Exception:
                continue

    def play(self, key, name):
        if not self.ok:
            return
        snd = self.banks.get(key, {}).get(name)
        if snd is not None:
            try:
                snd.play()
            except pygame.error:
                pass

    @staticmethod
    def hush(ms=260):
        try:
            if pygame.mixer.get_init():
                pygame.mixer.fadeout(ms)
        except pygame.error:
            pass


# ══════════════════════════════════════════════════════════════════
# Ausgabe
# ══════════════════════════════════════════════════════════════════

_veil = None


def _present(app, surf, alpha):
    global _veil
    win = app.window
    win.fill((0, 0, 0))
    vp = app.viewport
    win.blit(pygame.transform.scale(surf, vp.size), vp.topleft)
    if alpha < 0.999:
        if _veil is None or _veil.get_size() != vp.size:
            _veil = pygame.Surface(vp.size, pygame.SRCALPHA)
        _veil.fill((0, 0, 0, int(255 * (1 - alpha))))
        win.blit(_veil, vp.topleft)
    pygame.display.flip()


def _black(app):
    app.window.fill((0, 0, 0))
    pygame.display.flip()


# ══════════════════════════════════════════════════════════════════
# Ablauf
# ══════════════════════════════════════════════════════════════════

def play(app, tempo: float | None = None) -> str:
    """Spielt die Sequenz. Gibt 'fertig' oder 'abbruch' zurueck."""
    global TEMPO
    if tempo is not None:
        TEMPO = tempo

    karten = [k for k in ORDER if KARTEN_AN.get(k, True)]
    if not karten:
        return "fertig"

    drone = getattr(getattr(app, "audio", None), "drone_channel", None)
    if drone is not None:
        try:
            drone.pause()
        except pygame.error:
            drone = None

    eng = Engine(scheme=SCHEMA, opts=TEXTE)
    audio = SplashAudio(app)
    clock = pygame.time.Clock()

    def ende(status):
        audio.hush(300)
        if drone is not None:
            try:
                drone.unpause()
            except pygame.error:
                pass
        pygame.event.clear()
        return status

    _black(app)
    r = 0.0
    while r < VORLAUF:
        r += min(clock.tick(60) / 1000.0, 0.05)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return ende("abbruch")
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                return ende("abbruch")

    for key in karten:
        total = karten_dauer(key)
        cues = CUES.get(key, [])
        ci = 0
        r = 0.0
        ueberspringen = False
        while r < total:
            r += min(clock.tick(60) / 1000.0, 0.05)
            tc = karten_zeit(key, r)

            while ci < len(cues) and cues[ci][0] <= tc:
                audio.play(key, cues[ci][1])
                ci += 1

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return ende("abbruch")
                if ev.type in (pygame.WINDOWSIZECHANGED, pygame.VIDEORESIZE):
                    app.handle(ev)
                    continue
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        return ende("abbruch")
                    if ev.key == pygame.K_F11:
                        app.toggle_fullscreen()
                        continue
                    ueberspringen = True
                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    ueberspringen = True
            if ueberspringen:
                break

            surf, alpha = eng.frame(key, tc)
            _present(app, surf, alpha)

        if ueberspringen:
            audio.hush(160)
            _black(app)
            pygame.time.wait(110)

    _black(app)
    return ende("fertig")


def main() -> int:
    import rustfront_menu as menu
    app = menu.build_app()
    print("Gesamtdauer: %.1f s" % gesamtdauer())
    for k in ORDER:
        if KARTEN_AN.get(k, True):
            print("  %-11s %.2f s  (Original %.1f s)" % (NAMEN[k], karten_dauer(k), LENS[k]))
    play(app)
    app.audio.shutdown()
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
