"""
DUSTFRONT - Gefechte aus dem Testmodus als Video aufnehmen (seit 0.34.32)
=========================================================================

    python werkzeug_aufnahme.py                  alle Szenen nach aufnahmen/
    python werkzeug_aufnahme.py duell boss       nur diese
    python werkzeug_aufnahme.py --liste          welche es gibt
    python werkzeug_aufnahme.py --ordner X ...   woanders hin
    python werkzeug_aufnahme.py --zeitlupe ...   dazu je eine Fassung in halbem Tempo
    python werkzeug_aufnahme.py --ohne-ton ...   ohne Tonspur

Jede Szene ist ein echtes Gefecht im Testmodus (dustfront/testmodus.py),
ohne Fenster gerechnet und Bild fuer Bild gezeichnet: 120 Rechenschritte
je Sekunde wie im Spiel, jedes vierte Bild aufgenommen (30 Bilder je
Sekunde), auf 1280 x 720 vergroessert. Gezeigt wird die SAUBERE ANSICHT
des Testmodus: nur die Welt und ueber jedem Kopf, was er gerade tut (bei
GOAP die Aktion, siehe docs/KI.md). Die Kamera folgt der Mitte aller, die
noch stehen.

Mit Ton (seit 0.34.35): ohne Fenster spielt das Spiel nichts ab, also
schreibt `Tonband` mit, welcher Klang wann wie laut gespielt wuerde - mit
derselben Entfernungsrechnung wie im Spiel, gehoert vom Beobachter aus -
und mischt daraus eine Tonspur. Die Zeitlupe ist echt: es wird doppelt so
dicht gezeichnet (60 Bilder je Spielsekunde), die normale Fassung nimmt
jedes zweite, die Zeitlupe alle, der Ton laeuft halb so schnell bei
gleicher Tonhoehe.

Braucht ffmpeg im Pfad (macOS: `brew install ffmpeg`, Linux: Paketverwaltung,
Windows: ffmpeg.org). Eine neue Szene ist eine Funktion `szene_NAME`, die
die Figuren setzt, und ein Eintrag in `SZENEN`.

Gebaut, weil der Besitzer die zielorientierte KI "in Aktion sehen" wollte,
ohne selbst zu spielen - und weil die ersten Aufnahmen gleich zwei Fehler
zeigten, die kein Test gefunden hatte (0.34.31).
"""

from __future__ import annotations

import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
import wave
from array import array

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame  # noqa: E402

from dustfront import config as K  # noqa: E402
from dustfront.world import freier_punkt  # noqa: E402

BREITE, HOEHE = 1280, 720
BILDER_JE_SEKUNDE = 30
# 120 Rechenschritte je Sekunde (K.FIXED_DT), jeder vierte wird ein Bild.
SCHRITTE_JE_BILD = max(1, int(round(1.0 / (K.FIXED_DT * BILDER_JE_SEKUNDE))))
NACHLAUF = 2.0                  # so lange laeuft das Bild nach dem Ende weiter (s)


# ══════════════════════════════════════════════════════════════════
# Hilfen fuer die Szenen
# ══════════════════════════════════════════════════════════════════

def stelle(tm, rnd, abstand: float, art: str = "", versuche: int = 20000):
    """Zwei freie Punkte auf Ebene 0 im Abstand. `art` ist, was zwischen
    ihnen steht (Welt.deckung): "" freie Sicht, "hindernis" eine Kiste."""
    for _ in range(versuche):
        a = pygame.Vector2(freier_punkt(tm.welt, 0, rnd))
        b = a + pygame.Vector2(abstand, 0).rotate(rnd.uniform(0.0, 360.0))
        if not (tm.welt.frei(a, 30, 0, True) and tm.welt.frei(b, 30, 0, True)):
            continue
        if tm.welt.deckung(a, b, 0) != art:
            continue
        return a, b
    raise RuntimeError("Keine passende Stelle auf der Karte gefunden")


def kreis(mitte, n: int, abstand: float = 26.0) -> list:
    """n Plaetze um eine Mitte, damit niemand auf dem anderen steht."""
    if n <= 1:
        return [pygame.Vector2(mitte)]
    return [mitte + pygame.Vector2(abstand, 0).rotate(i * 360.0 / n + 15.0)
            for i in range(n)]


def alle_weg(*gruppen):
    """Ende, sobald eine der Gruppen ganz liegt - tot oder am Boden (seit
    0.34.40 fallen Bots im Testmodus erst zu Boden)."""
    return lambda: any(all(not w.lebt or getattr(w, "am_boden", False) for w in g)
                       for g in gruppen)


# ══════════════════════════════════════════════════════════════════
# Die Szenen. Jede setzt ihre Figuren und gibt zurueck:
# (Titel, Teilnehmer fuer die Kamera, Ende-Bedingung, Sekunden, Zoom)
# ══════════════════════════════════════════════════════════════════

def szene_duell(tm, rnd):
    a, b = stelle(tm, rnd, 300, "hindernis")
    rot = [tm.bot_setzen(p, 0, {"team": 0, "hirn": "goap"}) for p in kreis(a, 3)]
    blau = [tm.bot_setzen(p, 0, {"team": 1, "hirn": "klassisch"}) for p in kreis(b, 3)]
    return ("GOAP-Bots (rot) gegen klassische Bots (blau), 3 gegen 3",
            rot + blau, alle_weg(rot, blau), 50, 1.5)


def szene_flanke(tm, rnd):
    a, b = stelle(tm, rnd, 230, "hindernis")
    rot = [tm.bot_setzen(p, 0, {"team": 0, "hirn": "goap"}) for p in kreis(a, 2, 30)]
    blau = [tm.bot_setzen(b, 0, {"team": 1, "hirn": "klassisch", "leben": 2.0})]
    return ("Zwei GOAP-Bots gegen einen hinter der Kiste (doppeltes Leben)",
            rot + blau, alle_weg(rot, blau), 40, 1.25)


def szene_welle(tm, rnd):
    a, b = stelle(tm, rnd, 280, "")
    c = a - (b - a)
    if not tm.welt.frei(c, 30, 0, True):
        c = pygame.Vector2(b)
    rot = [tm.bot_setzen(p, 0, {"team": 0, "hirn": "goap"}) for p in kreis(a, 3)]
    arten = ["laeufer"] * 7 + ["renner"] * 4 + ["speier"] * 2 + ["blaeher"] * 2 + ["brecher"] * 2
    zombies = []
    for seite in (b, c):
        for art in arten:
            p = seite + pygame.Vector2(rnd.uniform(-80, 80), rnd.uniform(-80, 80))
            if not tm.welt.frei(p, 16, 0, True):
                p = pygame.Vector2(seite)
            # Zombies klassisch (seit 0.34.36, Entscheidung des Besitzers: sie
            # brauchen vorerst kein GOAP).
            zombies.append(tm.gegner_setzen(art, p, 0, {"ki": True, "hirn": "klassisch"}))
    # Die Kamera folgt den Bots: 34 Zombies ziehen die Mitte sonst ins Leere.
    return ("Drei GOAP-Bots gegen 34 Zombies von zwei Seiten",
            rot, alle_weg(rot, zombies), 60, 1.75)


def szene_boss(tm, rnd):
    a, b = stelle(tm, rnd, 300, "")
    rot = [tm.bot_setzen(p, 0, {"team": 0, "hirn": "goap"}) for p in kreis(a, 4, 30)]
    boss = tm.gegner_setzen("koloss", b, 0, {"ki": True, "hirn": "klassisch", "leben": 5.0})
    return ("Vier GOAP-Bots gegen den Koloss (klassisch, fuenffaches Leben)",
            rot + [boss], alle_weg(rot, [boss]), 60, 1.5)


def szene_huegel(tm, rnd):
    a, b = stelle(tm, rnd, 720, "")
    tm.zone_setzen((a + b) / 2, 0)
    # Doppeltes Leben: im Kreis prallen alle auf einmal aufeinander, mit
    # gewoehnlichem Leben war es nach sieben Sekunden vorbei.
    rot = [tm.bot_setzen(p, 0, {"team": 0, "hirn": "goap", "leben": 2.0}) for p in kreis(a, 4, 30)]
    blau = [tm.bot_setzen(p, 0, {"team": 1, "hirn": "goap", "leben": 2.0}) for p in kreis(b, 4, 30)]
    return ("Huegel: GOAP gegen GOAP um den Kreis, 4 gegen 4 (doppeltes Leben)",
            rot + blau, alle_weg(rot, blau), 60, 1.5)


def szene_tod(tm, rnd):
    """Jede Art stirbt einmal, eine nach der anderen (seit 0.34.33): Fleck und
    Blut je Art. Steht still, damit man jeden Tod sieht."""
    arten = ["laeufer", "renner", "brecher", "speier", "blaeher",
             "koloss", "mutter", "brandstifter"]
    abstand = 50
    for _ in range(20000):
        a = pygame.Vector2(freier_punkt(tm.welt, 0, rnd))
        reihe = [a + pygame.Vector2(i * abstand, 0) for i in range(len(arten) + 2)]
        if all(tm.welt.frei(p, 34, 0, True) for p in reihe):
            break
    else:
        raise RuntimeError("Keine freie Reihe gefunden")
    tm.ki_stopp = True                 # alle stehen still, bis sie dran sind
    opfer = [tm.gegner_setzen(art, reihe[i + 2], 0, {"ki": False}) for i, art in enumerate(arten)]
    opfer = [tm.bot_setzen(reihe[0], 0, {"team": 0}),
             tm.bot_setzen(reihe[1], 0, {"team": 1})] + opfer
    # Die Kamera schaut auf die Mitte der Reihe, nicht auf die Lebenden:
    # sonst wanderte sie mit jedem Tod ein Stueck weiter.
    anker = type("Anker", (), {})()
    anker.pos, anker.ebene, anker.lebt = sum(reihe, pygame.Vector2()) / len(reihe), 0, True
    uhr = {"t": 0.0, "nr": 0}

    def jedes_bild():
        uhr["t"] += 1.0 / BILDER_JE_SEKUNDE
        if uhr["nr"] < len(opfer) and uhr["t"] >= 1.0 + 1.1 * uhr["nr"]:
            tm.toeten(opfer[uhr["nr"]])
            uhr["nr"] += 1

    return ("Jede Art stirbt einmal: Fleck und Blut je Art",
            [anker], lambda: uhr["nr"] >= len(opfer) and uhr["t"] > 1.1 * len(opfer) + 9.0,
            30, 1.0, jedes_bild)


def szene_trupp(tm, rnd):
    """Seit 0.34.39: zwei Trupps mit Anfuehrer gegeneinander - Bahnen,
    Wellen, Flanke, der Anfuehrer hinten in der Mitte."""
    a, b = stelle(tm, rnd, 420, "")
    # Doppeltes Leben: mit gewoehnlichem war es in den ersten Aufnahmen nach
    # sechs Sekunden vorbei - zu kurz, um Bahnen und Wellen zu sehen.
    rot = tm.trupp_setzen(a, 0, {"groesse": 5, "team": 0, "fuehrer": "funk", "mischung": "gemischt",
                                 "leben": 2.0})
    blau = tm.trupp_setzen(b, 0, {"groesse": 5, "team": 1, "fuehrer": "funk", "mischung": "gemischt",
                                  "leben": 2.0})
    tm.trupp_auftrag("angriff", b, 0, {"team": 0})
    tm.trupp_auftrag("angriff", a, 0, {"team": 1})
    return ("Trupp gegen Trupp, je 5 mit Anfuehrer (Funk, doppeltes Leben)",
            rot.mitglieder + blau.mitglieder, alle_weg(rot.mitglieder, blau.mitglieder), 70, 1.75)


def szene_hilferuf(tm, rnd):
    """Seit 0.34.39: ALPHA haelt eine wichtige Stellung gegen eine Uebermacht
    und funkt um Hilfe; BRAVO hat nur einen Gegner, erledigt ihn, sagt zu
    und kommt."""
    a, b = stelle(tm, rnd, 300, "")
    for _ in range(4000):
        c, d = stelle(tm, rnd, 220, "")
        if 520 < c.distance_to(a) < 900 and c.distance_to(b) > 450:
            break
    alpha = tm.trupp_setzen(a, 0, {"groesse": 4, "team": 0, "fuehrer": "funk", "mischung": "gemischt",
                                   "leben": 2.0})
    tm.trupp_auftrag("halten", a, 0, {"team": 0, "wichtig": True})
    bravo = tm.trupp_setzen(c, 0, {"groesse": 4, "team": 0, "fuehrer": "funk", "mischung": "gemischt"})
    feinde = [tm.bot_setzen(p, 0, {"team": 1, "hirn": "goap"}) for p in kreis(b, 7, 34)]
    feinde.append(tm.bot_setzen(d, 0, {"team": 1, "hirn": "goap"}))
    return ("Hilferuf: ALPHA haelt gegen 7, BRAVO kommt zu Hilfe",
            alpha.mitglieder + bravo.mitglieder, alle_weg(alpha.mitglieder + bravo.mitglieder, feinde),
            80, 2.25)


def szene_bergen(tm, rnd):
    """Seit 0.34.40: einer aus dem Trupp liegt im Blick der Gegner. Der
    Anfuehrer legt Rauch, zwei ziehen ihn in Deckung und helfen ihm auf,
    die anderen decken. Danach ist er geschwaecht."""
    a, b = stelle(tm, rnd, 280, "")
    tm.verwundete_setzen(True)
    trupp = tm.trupp_setzen(a, 0, {"groesse": 4, "team": 0, "fuehrer": "funk",
                                   "mischung": "gemischt", "leben": 2.0})
    # Zehnfaches Leben: mit vierfachem waren sie nach acht Sekunden erledigt,
    # bevor man die Bergung ganz sah.
    feinde = [tm.puppe_setzen(b + pygame.Vector2(0, 30 * i), 0, {"team": 1, "leben": 10.0})
              for i in range(2)]
    opfer = next(m for m in trupp.mitglieder if m is not trupp.fuehrer)
    uhr = {"t": 0.0}

    def jedes_bild():
        uhr["t"] += 1.0 / BILDER_JE_SEKUNDE
        if uhr["t"] >= 1.5 and not uhr.get("gefallen"):
            uhr["gefallen"] = True
            tm.toeten(opfer)

    return ("Bergen: einer faellt, Rauch, in Deckung ziehen, aufhelfen",
            trupp.mitglieder, lambda: uhr.get("gefallen") and opfer.lebt and not opfer.am_boden
            and uhr["t"] > 12.0 or all(not f.lebt for f in feinde), 45, 1.5, jedes_bild)


def szene_igel(tm, rnd):
    """Seit 0.34.41: Gegner von drei Seiten - der Trupp igelt sich ein, an
    einem Platz mit Deckung ringsum, jeder schaut nach aussen."""
    for _ in range(20000):
        a = pygame.Vector2(freier_punkt(tm.welt, 0, rnd))
        seiten = [a + pygame.Vector2(270, 0).rotate(w + rnd.uniform(0, 120)) for w in (0, 120, 240)]
        if all(tm.welt.frei(p, 30, 0, True) for p in [a] + seiten):
            break
    trupp = tm.trupp_setzen(a, 0, {"groesse": 5, "team": 0, "fuehrer": "funk", "mischung": "gemischt",
                                   "leben": 2.0})
    feinde = [tm.bot_setzen(p, 0, {"team": 1, "hirn": "goap"}) for s_ in seiten for p in kreis(s_, 2, 26)]
    return ("Von drei Seiten: der Trupp igelt sich ein (doppeltes Leben)",
            trupp.mitglieder, alle_weg(trupp.mitglieder, feinde), 60, 1.75)


def szene_engstelle(tm, rnd):
    """Seit 0.34.41: eine Zombiehorde kommt, der Trupp haelt hinter einer
    Engstelle, durch die sie einzeln muessen."""
    from dustfront.trupp import breite_an
    for _ in range(40000):
        p = pygame.Vector2(freier_punkt(tm.welt, 0, rnd))
        breite, achse = breite_an(tm.welt, p, 0)
        if breite > 70:
            continue
        a, z = p + achse * 170, p - achse * 430
        if tm.welt.frei(a, 30, 0, True) and tm.welt.frei(z, 40, 0, True):
            break
    else:
        raise RuntimeError("Keine Engstelle auf der Karte gefunden")
    trupp = tm.trupp_setzen(a, 0, {"groesse": 4, "team": 0, "fuehrer": "funk", "mischung": "gemischt"})
    zombies = []
    for art in ["laeufer"] * 14 + ["renner"] * 4 + ["brecher"] * 2:
        q = z + pygame.Vector2(rnd.uniform(-70, 70), rnd.uniform(-70, 70))
        if not tm.welt.frei(q, 16, 0, True):
            q = pygame.Vector2(z)
        zombies.append(tm.gegner_setzen(art, q, 0, {"ki": True, "hirn": "klassisch"}))
    return ("Eine Horde: der Trupp haelt hinter der Engstelle",
            trupp.mitglieder, alle_weg(trupp.mitglieder, zombies), 60, 1.75)


def szene_deckung(tm, rnd):
    """Seit 0.34.43: Rot hinter einer Kistenwand kaempft aus der Deckung
    (drin warten, herauslehnen, ein Stoss, zurueck), Blau kommt ueber das
    freie Feld. Nach acht Sekunden bekommt einer von Rot Panik und
    verkriecht sich, statt wegzurennen. Wer faellt, wird gezogen."""
    T = K.TILE
    ebene = tm.welt.ebene(0)
    for _ in range(20000):
        tx = rnd.randrange(2, ebene.breite - 22)
        ty = rnd.randrange(2, ebene.hoehe - 12)
        mitte = [pygame.Vector2((tx + x + 0.5) * T, (ty + y + 0.5) * T)
                 for x in range(0, 20, 2) for y in range(0, 9, 2)]
        if all(tm.welt.frei(p, 12, 0, True) for p in mitte):
            break
    else:
        raise RuntimeError("Keine freie Flaeche fuer die Kistenwand gefunden")
    wand_x = tx + 13
    for dy in range(1, 8):
        if dy != 4:                       # eine Luecke, durch die man sieht
            ebene.setzen(wand_x, ty + dy, K.KISTE)
    hinten = pygame.Vector2((wand_x + 1.6) * T, (ty + 4.5) * T)
    vorn = pygame.Vector2((wand_x - 6.5) * T, (ty + 4.5) * T)
    tm.verwundete_setzen(True)
    rot = [tm.bot_setzen(hinten + pygame.Vector2(0, (i - 1) * T * 2.2), 0,
                         {"team": 0, "hirn": "goap", "leben": 2.0}) for i in range(3)]
    for b in rot:
        b.hirn.merkmale["mut"] = min(b.hirn.merkmale.get("mut", 0.5), 0.45)
    blau = [tm.bot_setzen(p, 0, {"team": 1, "hirn": "goap", "leben": 3.0}) for p in kreis(vorn, 3, 34)]
    # Beide wissen voneinander: sonst zogen sie suchend auseinander, und
    # die Kamera hing zwischen ihnen im Leeren.
    for eigene, andere in ((rot, blau), (blau, rot)):
        for b in eigene:
            for x in andere:
                b.hirn.gesehen[x] = (pygame.Vector2(x.pos), 0, tm.welt.zeit)
    uhr = {"t": 0.0}

    def jedes_bild():
        uhr["t"] += 1.0 / BILDER_JE_SEKUNDE
        # Panik fuer einen, der gerade hinter den Kisten sitzt - wer im
        # Freien steht, rennt zu Recht weg, das zeigt die Szene nicht.
        if uhr["t"] >= 8.0 and not uhr.get("panik"):
            for b in rot:
                if b.lebt and not getattr(b, "am_boden", False) and b.hirn._in_deckung():
                    uhr["panik"] = True
                    b.hirn.innen.panik_setzen(5.0)
                    break

    return ("Deckung zuerst: aus der Deckung feuern, Panik = verkriechen",
            rot + blau, alle_weg(rot, blau), 35, 1.5, jedes_bild)


# Name -> (Dateiname, Szene). Die Nummer im Dateinamen ist die Reihenfolge.
SZENEN = {
    "duell": ("1_goap_gegen_klassisch", szene_duell),
    "flanke": ("2_flanke_und_niederhalten", szene_flanke),
    "welle": ("3_zombiewelle", szene_welle),
    "boss": ("4_boss_koloss", szene_boss),
    "huegel": ("5_kampf_um_den_kreis", szene_huegel),
    "tod": ("6_jeder_tod", szene_tod),
    "trupp": ("7_trupp_gegen_trupp", szene_trupp),
    "hilferuf": ("8_hilferuf_ueber_funk", szene_hilferuf),
    "bergen": ("9_bergen_und_wiederbeleben", szene_bergen),
    "igel": ("10_igel_von_drei_seiten", szene_igel),
    "engstelle": ("11_engstelle_gegen_horde", szene_engstelle),
    "deckung": ("12_deckung_zuerst", szene_deckung),
}


# ══════════════════════════════════════════════════════════════════
# Der Ton
# ══════════════════════════════════════════════════════════════════

class Tonband:
    """Haengt sich vor `Klaenge.spielen` und schreibt mit, statt abzuspielen:
    (Zeit, Klang, Lautstaerke). `wav` mischt daraus eine Tonspur.

    Gemischt wird in reinem Python (ohne numpy, wie das ganze Spiel). Eine
    Minute Gefecht mit ein paar hundert Schuessen dauert so einige
    Sekunden - fuer ein Werkzeug, das ohnehin Minuten rechnet, genug."""

    def __init__(self, klaenge, uhr) -> None:
        self.k = klaenge
        self.uhr = uhr                      # gibt die Zeit im Video zurueck (s)
        self.ereignisse: list = []
        klaenge.spielen = self.spielen      # an der Instanz, nicht an der Klasse

    def spielen(self, name: str, lautstaerke: float = 1.0) -> None:
        fassungen = self.k.klang(name)
        if not fassungen:
            return
        laut = max(0.0, min(1.0, lautstaerke * self.k.gesamt * self.k.effekte))
        if laut <= 0.0:
            return
        s = fassungen[self.k.rnd.randrange(len(fassungen))]
        self.ereignisse.append((self.uhr(), s, laut))

    def abhaengen(self) -> None:
        self.k.__dict__.pop("spielen", None)

    def wav(self, pfad: str, dauer: float) -> bool:
        """Die Tonspur schreiben. False, wenn es keinen Mixer gibt."""
        init = pygame.mixer.get_init()
        if not init or init[1] != -16:
            return False
        rate, _groesse, kanaele = init
        n = int(dauer * rate) * kanaele
        mix = array("d", bytes(8 * n))
        roh_je = {}
        for zeit, s, laut in self.ereignisse:
            roh = roh_je.get(id(s))
            if roh is None:
                roh = roh_je[id(s)] = array("h", s.get_raw())
            o = int(zeit * rate) * kanaele
            if o >= n:
                continue
            ende = min(n, o + len(roh))
            mix[o:ende] = array("d", [a + b * laut for a, b in zip(mix[o:ende], roh)])
        # Weich begrenzen statt hart abschneiden: zehn Schuesse auf einmal
        # sollen laut sein, nicht kratzen.
        voll = 32767.0
        aus = array("h", [int(voll * math.tanh(v / voll)) for v in mix])
        with wave.open(pfad, "wb") as w:
            w.setnchannels(kanaele)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(aus.tobytes())
        return True


def _video_schreiber(pfad: str):
    return subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", "%dx%d" % (BREITE, HOEHE), "-r", str(BILDER_JE_SEKUNDE), "-i", "-",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium", pfad],
        stdin=subprocess.PIPE)


def _ton_dazu(video: str, ton: str, ziel: str, tempo: float = 1.0) -> None:
    """Bild und Ton zusammen in eine Datei; mit `tempo` 0.5 halb so schnell
    bei gleicher Tonhoehe (atempo)."""
    befehl = ["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", ton,
              "-c:v", "copy", "-c:a", "aac", "-b:a", "160k"]
    if tempo != 1.0:
        befehl += ["-filter:a", "atempo=%g" % tempo]
    subprocess.run(befehl + ["-shortest", ziel], check=True)


# ══════════════════════════════════════════════════════════════════
# Aufnehmen
# ══════════════════════════════════════════════════════════════════

def testmodus_fuer_aufnahme(app, zoom: float):
    """Ein Testmodus, wie ihn eine Aufnahme braucht: saubere Ansicht,
    tote Figuren steigen nicht wieder ein, fester Zoom."""
    from dustfront import testmodus
    tm = testmodus.Testmodus(app, karte="staubtal")
    tm.sauber = True
    tm.wiedereinstieg = False
    tm.zoom_ziel = zoom
    tm._zoom_weich = zoom
    tm._geist.ebene = 0
    tm.blick = 0
    return tm


def _mitte(wesen):
    lebende = [w for w in wesen if w.lebt and w.ebene == 0]
    if not lebende:
        return None
    return sum((pygame.Vector2(w.pos) for w in lebende), pygame.Vector2()) / len(lebende)


def aufnehmen(app, name: str, ordner: str, seed: int | None = None,
              zeitlupe: bool = False, ton: bool = True) -> list:
    """Eine Szene rechnen und als MP4 schreiben (mit `zeitlupe` dazu eine
    Fassung in halbem Tempo). Gibt die Pfade zurueck."""
    datei, szene = SZENEN[name]
    rnd = random.Random(seed if seed is not None else sum(map(ord, name)))
    # Erst mit Zoom 1 aufbauen (die Szene setzt die Figuren), dann den
    # Zoom der Szene einstellen.
    tm = testmodus_fuer_aufnahme(app, 1.0)
    titel, kamera_auf, ende, sekunden, zoom, *rest = szene(tm, rnd)
    # Optional ein sechster Teil: was vor jedem Bild geschehen soll.
    jedes_bild = rest[0] if rest else None
    tm.zoom_ziel = zoom
    tm._zoom_weich = zoom
    g = tm._geist
    m = _mitte(kamera_auf)
    if m is not None:
        g.pos.update(m)
    zwischen = tempfile.mkdtemp(prefix="aufnahme_")
    normal_roh = os.path.join(zwischen, "normal.mp4")
    lupe_roh = os.path.join(zwischen, "zeitlupe.mp4")
    ff = _video_schreiber(normal_roh)
    ff_lupe = _video_schreiber(lupe_roh) if zeitlupe else None
    uhr = {"t": 0.0}
    band = Tonband(app.klaenge, lambda: uhr["t"]) if ton else None
    bild = pygame.Surface((K.GAME_W, K.GAME_H))
    gross = pygame.Surface((BREITE, HOEHE))
    schluss = None
    bilder = 0
    # Je Bild der normalen Fassung zwei Haelften: die erste nur fuer die
    # Zeitlupe, die zweite fuer beide.
    haelfte = max(1, SCHRITTE_JE_BILD // 2)
    try:
        for nr in range(int(sekunden * BILDER_JE_SEKUNDE)):
            if jedes_bild is not None:
                jedes_bild()
            for teil in (0, 1):
                if teil == 0 and ff_lupe is None:
                    schritte = SCHRITTE_JE_BILD
                else:
                    schritte = haelfte if teil == 0 else SCHRITTE_JE_BILD - haelfte
                # Die Kamera schaut ein Stueck zur Maus voraus. Ohne Fenster
                # stuende die bei (0, 0), und das Bild rutschte nach links oben.
                app.eingabe.maus = pygame.Vector2(K.GAME_W / 2, K.GAME_H / 2)
                for _ in range(schritte):
                    tm.schritt(K.FIXED_DT)
                    uhr["t"] += K.FIXED_DT
                m = _mitte(kamera_auf)
                if m is not None:
                    # Weich nachziehen: ein Sprung, wenn einer faellt, ist unruhig.
                    g.pos += (m - g.pos) * (0.06 * schritte / SCHRITTE_JE_BILD)
                    g.vorher.update(g.pos)
                    g.ziel = pygame.Vector2(g.pos)
                if teil == 0 and ff_lupe is None:
                    continue
                tm.blick = 0
                tm.zeichnen(bild, 1.0)
                pygame.transform.scale(bild, (BREITE, HOEHE), gross)
                roh = pygame.image.tobytes(gross, "RGB")
                if ff_lupe is not None:
                    ff_lupe.stdin.write(roh)
                if teil == 1:
                    ff.stdin.write(roh)
                if ff_lupe is None:
                    break
            bilder += 1
            if schluss is None and ende():
                schluss = nr + int(NACHLAUF * BILDER_JE_SEKUNDE)
            if schluss is not None and nr >= schluss:
                break
    finally:
        for f in (ff, ff_lupe):
            if f is not None:
                f.stdin.close()
                f.wait()
        if band is not None:
            band.abhaengen()
        tm.verlassen()
    pfade = [os.path.join(ordner, datei + ".mp4")]
    if zeitlupe:
        pfade.append(os.path.join(ordner, datei + "_zeitlupe.mp4"))
    tonspur = os.path.join(zwischen, "ton.wav")
    mit_ton = band is not None and band.wav(tonspur, uhr["t"])
    for roh, ziel, tempo in ((normal_roh, pfade[0], 1.0), (lupe_roh, pfade[-1], 0.5)):
        if tempo != 1.0 and not zeitlupe:
            continue
        if mit_ton:
            _ton_dazu(roh, tonspur, ziel, tempo)
        else:
            shutil.copyfile(roh, ziel)
    shutil.rmtree(zwischen, ignore_errors=True)
    print("%-8s %5.1f s  %d Klaenge  %s  (%s)"
          % (name, bilder / float(BILDER_JE_SEKUNDE),
             len(band.ereignisse) if band is not None else 0, ", ".join(pfade), titel),
          flush=True)
    return pfade


def main(argv) -> int:
    if "--liste" in argv:
        for name, (datei, szene) in SZENEN.items():
            print("%-8s %s" % (name, datei))
        return 0
    ordner = "aufnahmen"
    if "--ordner" in argv:
        i = argv.index("--ordner")
        ordner = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    zeitlupe = "--zeitlupe" in argv
    ton = "--ohne-ton" not in argv
    namen = [a for a in argv if not a.startswith("--")] or list(SZENEN)
    falsch = [n for n in namen if n not in SZENEN]
    if falsch:
        print("Unbekannte Szene: %s (--liste zeigt alle)" % ", ".join(falsch))
        return 2
    if shutil.which("ffmpeg") is None:
        print("ffmpeg fehlt - ohne es laesst sich kein Video schreiben.")
        return 2
    os.makedirs(ordner, exist_ok=True)
    from dustfront.core import App
    app = App("aufnahme", None, headless=True)
    for n in namen:
        aufnehmen(app, n, ordner, zeitlupe=zeitlupe, ton=ton)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
