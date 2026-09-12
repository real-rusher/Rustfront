"""
RUSTFRONT / DUSTFRONT - Splash-Sequenz
======================================

Spielt die fuenf Karten aus splash-sequenz.tsx ab. Gezeichnet wird in
splash_engine.py, hier stehen Ablauf, Zeitdehnung und Ton.

Zeitdehnung
-----------
Das Original laeuft 29,6 s. Das ist fuer einen Spielstart zu lang, aber
einfach schneller abspielen sieht gehetzt aus. Stattdessen wird jede Karte in
zwei Abschnitte geteilt: der Aufbau laeuft fast in Originalgeschwindigkeit,
das Standbild danach wird kraeftig gekuerzt. Ergebnis: rund 19 s, ohne dass
eine Bewegung gehetzt wirkt. Werte stehen in PHASEN.

Ton
---
Jede Karte hat ihre eigene Klangwelt, weil jede zu einer anderen Firma
gehoert: Siegel orchestral-metallisch, Kaltwerk trocken und digital, Phosphor
eine Bildroehre, Papiermond eine Handpresse, Tafel eine Druckmaschine.
Alles wird zur Laufzeit synthetisiert, keine Audiodateien noetig. Die
Erzeugung laeuft in einem Hintergrundfaden, damit der Start nicht haengt.

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
VORLAUF = 0.35       # Schwarz vor der ersten Karte
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
PHASEN = {
    "a": [(7.25, 5.90), (11.0, 1.20)],   # Aufbau fast original, Standbild gekuerzt
    "c": [(1.30, 1.10), (3.40, 1.00)],
    "t": [(3.00, 2.45), (4.60, 0.90)],
    "s": [(1.50, 1.40), (4.00, 1.00)],
    "b": [(2.80, 2.50), (6.60, 1.35)],
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
    def __init__(self, rate=44100):
        self.rate = rate
        self.rnd = random.Random(90210)

    def _n(self, dur):
        return max(1, int(self.rate * dur))

    def sine(self, freqs, dur, vol=0.5, attack=0.005, decay=2.0, vib=0.0):
        n = self._n(dur)
        out = [0.0] * n
        ar = max(1, int(self.rate * attack))
        if not isinstance(freqs, (list, tuple)):
            freqs = [freqs]
        g = 1.0 / len(freqs)
        tp = 2 * math.pi
        for f in freqs:
            ph = 0.0
            for i in range(n):
                fr = f * (1 + vib * math.sin(tp * 5.5 * i / self.rate))
                ph += fr / self.rate
                out[i] += math.sin(tp * ph) * g
        for i in range(n):
            out[i] *= (1 - i / n) ** decay * min(1.0, i / ar) * vol
        return out

    def sweep(self, f0, f1, dur, vol=0.4, shape="sine", decay=1.8, attack=0.004):
        n = self._n(dur)
        out = [0.0] * n
        ar = max(1, int(self.rate * attack))
        ph = 0.0
        tp = 2 * math.pi
        for i in range(n):
            p = i / n
            ph += (f0 + (f1 - f0) * p) / self.rate
            x = ph % 1.0
            if shape == "square":
                s = 1.0 if x < 0.5 else -1.0
            elif shape == "saw":
                s = 2 * x - 1
            else:
                s = math.sin(tp * ph)
            out[i] = s * (1 - p) ** decay * min(1.0, i / ar) * vol
        return out

    def noise(self, dur, vol=0.4, lp0=4000, lp1=400, attack=0.004, decay=2.0,
              hp=False):
        """Rauschen durch ein wanderndes Einpolfilter."""
        n = self._n(dur)
        out = [0.0] * n
        ar = max(1, int(self.rate * attack))
        y = 0.0
        prev = 0.0
        rnd = self.rnd.uniform
        tp2 = 2 * math.pi / self.rate
        for i in range(n):
            p = i / n
            a = 1 - math.exp(-tp2 * (lp0 + (lp1 - lp0) * p))
            y += a * (rnd(-1.0, 1.0) - y)
            s = (y - prev) if hp else y
            prev = y
            out[i] = s * (1 - p) ** decay * min(1.0, i / ar) * vol
        return out

    def bump(self, f0, f1, dur, vol=0.7, decay=2.6):
        """Tiefer Schlag mit fallender Tonhoehe."""
        n = self._n(dur)
        out = [0.0] * n
        ph = 0.0
        tp = 2 * math.pi
        for i in range(n):
            p = i / n
            ph += (f0 * (1 - p) + f1 * p) / self.rate
            out[i] = math.sin(tp * ph) * (1 - p) ** decay * vol
        return out

    def klick(self, freq, dur=0.03, vol=0.5, shape="square"):
        return self.sweep(freq, freq * 0.8, dur, vol, shape, decay=1.2, attack=0.001)

    def ratsche(self, dur, ticks, vol=0.35, f0=2600, f1=1500):
        """Metallisches Einrasten: viele kurze Klicks, hinten dichter."""
        n = self._n(dur)
        out = [0.0] * n
        for k in range(ticks):
            p = k / ticks
            pos = int((p ** 0.72) * n)
            tick = self.klick(f0 + (f1 - f0) * p, 0.012, vol * (0.5 + 0.5 * p))
            for i, s in enumerate(tick):
                if pos + i < n:
                    out[pos + i] += s
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


def _baue_klaenge(sy: Synth, key: str) -> dict:
    """Klangwelt je Karte. Bewusst pro Firma voellig unterschiedlich."""
    s = {}
    if key == "a":
        # Siegel: weiter Raum, Metall und Gold
        s["flash"] = sy.mix(sy.bump(96, 26, 1.10, 0.9, 2.2),
                            sy.noise(0.55, 0.35, 7000, 300, 0.002, 2.4))
        s["orbit"] = sy.noise(1.15, 0.16, 260, 5200, 0.45, 1.2)
        s["bezel"] = sy.ratsche(0.95, 26, 0.30)
        s["wings"] = sy.mix(sy.noise(0.60, 0.30, 5200, 500, 0.06, 1.8),
                            sy.sweep(900, 220, 0.55, 0.10, "sine", 1.6))
        s["mount"] = sy.mix(sy.bump(150, 58, 0.34, 0.55, 3.0),
                            sy.klick(1800, 0.03, 0.22))
        s["title"] = sy.sine([523.25, 659.25, 783.99, 1046.5], 1.90, 0.46, 0.006, 2.4)
        s["quote"] = sy.sine([1567.98, 2093.0], 1.20, 0.12, 0.22, 2.0)
    elif key == "c":
        # Kaltwerk: trocken, kurz, digital. Kein Nachhall, harte Kanten.
        for i, f in enumerate((900, 760, 640)):
            s["tok%d" % i] = sy.mix(sy.klick(f, 0.035, 0.42),
                                    sy.noise(0.025, 0.22, 2600, 900, 0.001, 3.0))
        s["stab"] = sy.mix(sy.sweep(440, 440, 0.26, 0.30, "square", 0.9, 0.002),
                           sy.sweep(660, 660, 0.26, 0.20, "square", 0.9, 0.002))
        s["bar"] = sy.sweep(320, 1750, 0.26, 0.26, "saw", 1.1, 0.002)
    elif key == "t":
        # Phosphor: Bildroehre. Zeilenpfeifen, Netzbrummen, Statik.
        s["on"] = sy.mix(sy.klick(1400, 0.02, 0.40),
                         sy.noise(0.10, 0.26, 9000, 2000, 0.001, 2.6))
        s["whine"] = sy.mix(sy.sine(7812, 3.60, 0.085, 0.30, 0.15),
                            sy.sine([50, 100], 3.60, 0.075, 0.30, 0.12))
        s["key"] = sy.klick(2300, 0.014, 0.20)
        s["pop"] = sy.mix(sy.bump(130, 44, 0.20, 0.50, 3.2),
                          sy.noise(0.14, 0.34, 9500, 1200, 0.001, 2.2))
        s["off"] = sy.mix(sy.sweep(7200, 180, 0.32, 0.30, "sine", 1.1),
                          sy.klick(900, 0.02, 0.30))
    elif key == "s":
        # Papiermond: Handpresse. Holz, Papier, Farbe.
        s["stamp"] = sy.mix(sy.bump(78, 33, 0.34, 0.85, 3.4),
                            sy.noise(0.20, 0.42, 1500, 160, 0.001, 2.8))
        s["stamp2"] = sy.mix(sy.bump(120, 50, 0.16, 0.40, 3.6),
                             sy.noise(0.10, 0.22, 1800, 240, 0.001, 3.0))
        s["slide"] = sy.noise(0.34, 0.26, 3200, 900, 0.10, 1.6, hp=True)
        s["press"] = sy.mix(sy.bump(96, 42, 0.24, 0.55, 3.2),
                            sy.noise(0.14, 0.28, 1300, 200, 0.001, 2.8))
        s["tick"] = sy.klick(1500, 0.016, 0.22, "saw")
    elif key == "b":
        # Tafel: Druckmaschine. Ein langer Lauf, dann Mechanik.
        s["bar"] = sy.mix(sy.noise(1.55, 0.34, 500, 4200, 0.20, 0.6),
                          sy.sine(62, 1.55, 0.20, 0.20, 0.7),
                          sy.noise(1.55, 0.12, 3000, 700, 0.35, 0.8))
        s["shutter"] = sy.mix(sy.klick(2400, 0.026, 0.40),
                              sy.pause(0.045) + sy.klick(1750, 0.03, 0.34))
        s["shine"] = sy.mix(sy.sine([1318.5, 1975.5], 0.75, 0.28, 0.004, 2.6),
                            sy.sweep(2600, 3400, 0.30, 0.10, "sine", 2.0))
        s["tick"] = sy.klick(1900, 0.018, 0.22)
    return s


# Kartenzeit -> Klang. Deckt sich mit der Choreografie im Original.
CUES = {
    "a": [(0.38, "flash"), (1.00, "orbit"), (1.85, "bezel"), (2.60, "wings"),
          (3.35, "mount"), (3.75, "title"), (4.85, "quote")],
    "c": [(0.10, "tok0"), (0.24, "tok1"), (0.38, "tok2"), (0.62, "stab"),
          (0.86, "bar")],
    "t": [(0.02, "on"), (0.05, "whine"), (0.45, "key"), (0.62, "key"),
          (0.80, "key"), (1.08, "key"), (1.30, "key"), (1.61, "key"),
          (1.85, "key"), (2.22, "pop"), (4.18, "off")],
    "s": [(0.30, "stamp"), (0.35, "stamp2"), (0.52, "slide"), (0.78, "press"),
          (1.16, "tick")],
    "b": [(0.15, "bar"), (1.58, "shutter"), (1.70, "shine"), (2.12, "tick")],
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
        # Erste Karte sofort, damit der Einstieg sitzt. Rest nebenher.
        self._bake(sy, ORDER[0])
        threading.Thread(target=self._rest, args=(sy,), daemon=True).start()

    def _bake(self, sy, key):
        try:
            bank = {}
            for name, samples in _baue_klaenge(sy, key).items():
                snd = sy.to_sound(samples)
                if snd is not None:
                    snd.set_volume(max(0.0, min(1.0, self.gain)))
                    bank[name] = snd
            self.banks[key] = bank
        except Exception:
            self.banks[key] = {}

    def _rest(self, sy):
        for key in ORDER[1:]:
            if key not in self.banks:
                self._bake(sy, key)

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
    def hush(ms=200):
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

    # Menuebrummen waehrend des Intros pausieren
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
        audio.hush(260)
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
            audio.hush(140)
            _black(app)
            pygame.time.wait(90)

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
