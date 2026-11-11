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
    tm.welt._wege = None                  # neu rechnen, siehe setzen
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


def flaeche(tm, rnd, breite: int, hoehe: int):
    """Eine freie Flaeche auf Ebene 0, in Kacheln (links oben), fuer eine
    gebaute Szene mitten in der Karte - und eine Hilfe, die eine Kachel
    darin in einen Weltpunkt (ihre Mitte) umrechnet."""
    T = K.TILE
    e = tm.welt.ebene(0)
    for _ in range(20000):
        tx = rnd.randrange(2, e.breite - breite - 2)
        ty = rnd.randrange(2, e.hoehe - hoehe - 2)
        mitten = [pygame.Vector2((tx + x + 0.5) * T, (ty + y + 0.5) * T)
                  for x in range(0, breite, 2) for y in range(0, hoehe, 2)]
        if all(tm.welt.frei(p, 12, 0, True) for p in mitten):
            return tx, ty, (lambda x, y: pygame.Vector2((tx + x + 0.5) * T, (ty + y + 0.5) * T))
    raise RuntimeError("Keine freie Flaeche gefunden")


def setzen(tm, tx, ty, punkte, art):
    """Kacheln setzen (Mauer, Kiste) - `punkte` in Kacheln der Flaeche."""
    e = tm.welt.ebene(0)
    for x, y in punkte:
        e.setzen(tx + x, ty + y, art)
    # Das Wegenetz rechnet die Welt nur einmal (Welt.wege) - ohne das liefen
    # die Bots geradewegs gegen die neue Mauer (gesehen in der Aufnahme).
    tm.welt._wege = None


def kennen(eigene, andere, tm):
    """Beide Seiten wissen voneinander - sonst ziehen sie suchend
    auseinander, und die Kamera haengt zwischen ihnen im Leeren."""
    for b in eigene:
        for x in andere:
            b.hirn.gesehen[x] = (pygame.Vector2(x.pos), 0, tm.welt.zeit)


def szene_mauer(tm, rnd):
    """Seit 0.34.48: volle Deckung zuerst. Rot hat eine Mauer vor sich und
    einzelne Kisten daneben - sie gehen an die Mauerenden, dicht heran, und
    lehnen sich von dort heraus, statt hinter die Kisten oder weit hinter
    die Mauer."""
    tx, ty, v = flaeche(tm, rnd, 20, 11)
    setzen(tm, tx, ty, [(11, y) for y in range(3, 8)], K.WAND)
    setzen(tm, tx, ty, [(14, 1), (14, 9), (7, 2), (7, 8)], K.KISTE)
    rot = [tm.bot_setzen(v(17, 4 + i), 0, {"team": 0, "hirn": "goap", "leben": 2.0}) for i in range(3)]
    for b in rot:
        b.hirn.merkmale["mut"] = min(b.hirn.merkmale.get("mut", 0.5), 0.45)
    blau = [tm.bot_setzen(v(1, 4 + i), 0, {"team": 1, "hirn": "goap", "leben": 2.0}) for i in range(3)]
    kennen(rot, blau, tm)
    kennen(blau, rot, tm)
    return ("Volle Deckung: an die Mauerenden, dicht heran (rot)",
            rot + blau, alle_weg(rot, blau), 40, 1.5)


def szene_panik(tm, rnd):
    """Seit 0.34.48: drei hinter Kisten, eine Mauer weiter hinten. Nach vier
    Sekunden bekommen alle drei Panik - gesund bleibt einer und verkriecht
    sich, angeschlagen wechseln sie hinter die Mauer, schwer getroffen
    rennt einer, wenn es keine bessere Deckung gibt."""
    tx, ty, v = flaeche(tm, rnd, 20, 11)
    setzen(tm, tx, ty, [(8, y) for y in (2, 3, 5, 6, 8, 9)], K.KISTE)
    setzen(tm, tx, ty, [(15, y) for y in range(3, 9)], K.WAND)
    tm.verwundete_setzen(True)
    anteile = (1.0, 0.45, 0.15)
    # Dreifaches Leben fuer Rot: sonst lagen zwei schon, bevor die Panik kam.
    rot = [tm.bot_setzen(v(9, 2 + 3 * i), 0, {"team": 0, "hirn": "goap", "leben": 3.0}) for i in range(3)]
    blau = [tm.bot_setzen(v(2, 3 + 2 * i), 0, {"team": 1, "hirn": "goap", "leben": 1.5}) for i in range(3)]
    kennen(rot, blau, tm)
    kennen(blau, rot, tm)
    uhr = {"t": 0.0}

    def jedes_bild():
        uhr["t"] += 1.0 / BILDER_JE_SEKUNDE
        if uhr["t"] >= 3.0 and not uhr.get("panik"):
            uhr["panik"] = True
            for b, anteil in zip(rot, anteile):
                if b.lebt and not getattr(b, "am_boden", False):
                    b.leben = b.max_leben * anteil
                    b.hirn.innen.panik_setzen(6.0)

    return ("Panik: je nach Lage bleiben, Deckung wechseln oder fliehen",
            rot + blau, alle_weg(rot, blau), 30, 1.5, jedes_bild)


def szene_bergen_mauer(tm, rnd):
    """Seit 0.34.48: einer faellt im Freien. Rauch auf ihn, dann ziehen sie
    ihn hinter die Mauer - erst dort helfen sie ihm auf (Arme, Verband,
    Ring), die anderen decken."""
    tx, ty, v = flaeche(tm, rnd, 20, 11)
    setzen(tm, tx, ty, [(12, y) for y in range(2, 9)], K.WAND)
    tm.verwundete_setzen(True)
    trupp = tm.trupp_setzen(v(15, 5), 0, {"groesse": 4, "team": 0, "fuehrer": "funk",
                                          "mischung": "gemischt", "leben": 2.0})
    opfer = next(m for m in trupp.mitglieder if m is not trupp.fuehrer)
    opfer.pos.update(v(8, 5))
    opfer.vorher.update(opfer.pos)
    feinde = [tm.puppe_setzen(v(1, 4 + 2 * i), 0, {"team": 1, "leben": 10.0}) for i in range(2)]
    kennen(trupp.mitglieder, feinde, tm)
    uhr = {"t": 0.0}

    def jedes_bild():
        uhr["t"] += 1.0 / BILDER_JE_SEKUNDE
        if uhr["t"] >= 1.0 and not uhr.get("gefallen"):
            uhr["gefallen"] = True
            tm.toeten(opfer)

    return ("Bergen: Rauch auf ihn, hinter die Mauer ziehen, dort aufhelfen",
            trupp.mitglieder, lambda: uhr.get("gefallen") and opfer.lebt and not opfer.am_boden
            and uhr["t"] > 16.0 or all(not f.lebt for f in feinde), 45, 1.75, jedes_bild)


def szene_ueberfall(tm, rnd):
    """Seit 0.34.48: ein Trupp wird aus der Naehe ueberrascht. Der Anfuehrer
    will um Hilfe funken, aber wer ihn trifft oder dicht vor ihm steht,
    bricht den Spruch ab - der zweite Trupp erfaehrt nichts."""
    a, b = stelle(tm, rnd, 170, "")
    for _ in range(4000):
        c, _d = stelle(tm, rnd, 220, "")
        if 600 < c.distance_to(a) < 950:
            break
    alpha = tm.trupp_setzen(a, 0, {"groesse": 4, "team": 0, "fuehrer": "funk", "mischung": "gemischt",
                                   "leben": 2.0})
    bravo = tm.trupp_setzen(c, 0, {"groesse": 3, "team": 0, "fuehrer": "funk"})
    feinde = [tm.bot_setzen(p, 0, {"team": 1, "hirn": "goap", "leben": 2.0}) for p in kreis(b, 6, 30)]
    return ("Ueberfall: zu nah dran - der Hilferuf kommt nicht durch",
            alpha.mitglieder + feinde, alle_weg(alpha.mitglieder, feinde), 40, 1.75)


def szene_zange(tm, rnd):
    """Seit 0.34.50: ein Trupp wird von zwei Seiten angegriffen. Die Front
    knickt - ein Teil schaut zu jeder Gruppe -, und wer von der Seite
    beschossen wird, nimmt den Schuetzen, statt weiter nach vorn zu
    schiessen."""
    tx, ty, v = flaeche(tm, rnd, 20, 12)
    setzen(tm, tx, ty, [(6, 5), (6, 6), (10, 2), (11, 2), (13, 7)], K.KISTE)
    rot = tm.trupp_setzen(v(10, 6), 0, {"groesse": 5, "team": 0, "fuehrer": "funk",
                                         "mischung": "gemischt", "leben": 2.0})
    west = [tm.bot_setzen(v(0, 5 + i), 0, {"team": 1, "hirn": "goap", "leben": 1.5}) for i in range(2)]
    nord = [tm.bot_setzen(v(9 + 2 * i, 0), 0, {"team": 1, "hirn": "goap", "leben": 1.5}) for i in range(2)]
    blau = west + nord
    kennen(rot.mitglieder, blau, tm)
    kennen(blau, rot.mitglieder, tm)
    return ("Zange: Gegner von zwei Seiten - die Front knickt",
            rot.mitglieder + blau, alle_weg(rot.mitglieder, blau), 40, 1.75)


def szene_zuruf(tm, rnd):
    """Seit 0.34.50: zwei Bots, einer sucht ein Stueck abseits. Der andere
    sieht den Gegner und ruft es ihm zu (Sprechblase) - der Suchende hoert
    auf und hilft."""
    tx, ty, v = flaeche(tm, rnd, 20, 11)
    setzen(tm, tx, ty, [(7, 3), (7, 4)], K.KISTE)
    rot = [tm.bot_setzen(v(9, 4), 0, {"team": 0, "hirn": "goap"}),
           tm.bot_setzen(v(15, 9), 0, {"team": 0, "hirn": "goap"})]
    blau = [tm.bot_setzen(v(1, 3), 0, {"team": 1, "hirn": "goap", "leben": 2.0})]
    return ("Zuruf: einer sieht ihn, sagt es - der andere hoert auf zu suchen",
            rot + blau, alle_weg(rot, blau), 30, 1.5)


def szene_bergen_puppen(tm, rnd):
    """Seit 0.34.50, wie im Test des Besitzers: ein Trupp, zwei Puppen, einer
    faellt. Rauch auf ihn, einer zieht ihn hinter die Mauer, die anderen
    geben aus der Deckung Feuerschutz, dort helfen sie ihm auf."""
    tx, ty, v = flaeche(tm, rnd, 20, 11)
    setzen(tm, tx, ty, [(13, y) for y in range(2, 9)], K.WAND)
    setzen(tm, tx, ty, [(15, 1), (15, 9)], K.KISTE)
    tm.verwundete_setzen(True)
    trupp = tm.trupp_setzen(v(15, 5), 0, {"groesse": 4, "team": 0, "fuehrer": "funk",
                                          "mischung": "gemischt"})
    feinde = [tm.puppe_setzen(v(2, 4 + 2 * i), 0, {"team": 1, "leben": 10.0}) for i in range(2)]
    opfer = next(m for m in trupp.mitglieder if m is not trupp.fuehrer)
    opfer.pos.update(v(9, 5))
    opfer.vorher.update(opfer.pos)
    kennen(trupp.mitglieder, feinde, tm)
    uhr = {"t": 0.0}

    def jedes_bild():
        uhr["t"] += 1.0 / BILDER_JE_SEKUNDE
        if uhr["t"] >= 1.0 and not uhr.get("gefallen"):
            uhr["gefallen"] = True
            tm.toeten(opfer)

    return ("Bergen gegen Puppen: Rauch, hinter die Mauer, Feuerschutz aus Deckung",
            trupp.mitglieder, lambda: uhr.get("gefallen") and opfer.lebt and not opfer.am_boden
            and uhr["t"] > 20.0, 45, 1.75, jedes_bild)


def szene_abschnitte(tm, rnd):
    """Seit 0.34.51, ruhiger als `zange`: der Trupp haelt eine wichtige
    Stellung (kein Rueckzug), die Gegner sind Puppen aus zwei Richtungen
    (keiner schiesst zurueck, keine Panik). Die Front knickt: ein Teil
    schaut nach Westen, einer nach Norden; zu sehen mit der Trupp-Anzeige
    (Front, Stellungen, kurze Striche fuer die Blickrichtung)."""
    tx, ty, v = flaeche(tm, rnd, 20, 12)
    setzen(tm, tx, ty, [(7, 5), (7, 7), (11, 3), (13, 3)], K.KISTE)
    tm.sauber_trupps = True
    trupp = tm.trupp_setzen(v(11, 7), 0, {"groesse": 6, "team": 0, "fuehrer": "funk",
                                          "mischung": "gemischt"})
    tm.trupp_auftrag("halten", v(11, 7), 0, {"team": 0, "wichtig": True})
    west = [tm.puppe_setzen(v(1, 5 + 2 * i), 0, {"team": 1, "leben": 10.0}) for i in range(3)]
    nord = [tm.puppe_setzen(v(9 + 2 * i, 0), 0, {"team": 1, "leben": 10.0}) for i in range(3)]
    for p in west + nord:
        p.unverwundbar = 1e9
    kennen(trupp.mitglieder, west + nord, tm)
    return ("Geknickte Front: ein Teil nach Westen, einer nach Norden",
            trupp.mitglieder, lambda: False, 25, 1.5)


# Name -> (Dateiname, Szene). Die Nummer im Dateinamen ist die Reihenfolge.
def _feld_ganz_frei(tm, rnd, breite: int, hoehe: int):
    """Wie `flaeche`, aber jede Kachel frei - ein Panzer braucht Platz, und
    zwischen zwei Stichproben passt eine ganze Mauer (seit 0.34.59)."""
    T = K.TILE
    e = tm.welt.ebene(0)
    for _ in range(40000):
        tx = rnd.randrange(2, e.breite - breite - 2)
        ty = rnd.randrange(2, e.hoehe - hoehe - 2)
        if all(not K.KACHELN[e.kachel(tx + x, ty + y)]["fest"] and not e.loch(tx + x, ty + y)
               for x in range(breite) for y in range(hoehe)):
            return tx, ty, (lambda x, y: pygame.Vector2((tx + x + 0.5) * T, (ty + y + 0.5) * T))
    raise RuntimeError("Keine ganz freie Flaeche gefunden")


def _fahrer_in(tm, art: str, pos, winkel: float):
    """Ein Fahrzeug und darin eine Figur, die nichts selbst tut - die Szene
    gibt ihr die Eingabe (seit 0.34.59)."""
    b = tm.fahrzeug_setzen(art, pos, 0, {"winkel": winkel})
    k = tm.puppe_setzen(b.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="FAHRER")
    tm._einsteigen(k, b)
    return b, k


def _steuern(tm, k, will, ziel, feuert=False, zielt=False):
    tm._anwenden(k, {"will": list(will), "ziel": [ziel.x, ziel.y], "knoepfe": [],
                     "feuert": feuert, "zielt": zielt})


def szene_panzer(tm, rnd):
    """Seit 0.34.59: der Panzer. Der Turm dreht zu einer Gruppe Laeufer,
    die Kanone schlaegt ein (Feuerball, Rauch, Krater), dann haelt das
    Bug-MG, und er faehrt langsam in den Rest hinein - vorn geschoben und
    angeschlagen, seitlich nur beiseite."""
    tx, ty, zelle = _feld_ganz_frei(tm, rnd, 26, 12)
    start = zelle(4, 6)
    b, k = _fahrer_in(tm, "panzer", start, 0.0)
    gruppe = [tm.gegner_setzen("laeufer", zelle(16 + (i % 3) * 2, 3 + (i // 3) * 3), 0,
                               {"ki": False}) for i in range(9)]
    uhr = {"t": 0.0}

    def jedes_bild():
        uhr["t"] += 1.0 / BILDER_JE_SEKUNDE
        t = uhr["t"]
        lebende = [g for g in gruppe if g.lebt]
        ziel = lebende[0].pos if lebende else b.pos + b.vorn * 200
        if t < 3.0:
            _steuern(tm, k, (0, 0), zelle(16, 6), feuert=t > 2.2)
        elif t < 5.0:
            _steuern(tm, k, (0, 0), ziel, zielt=True)
        else:
            _steuern(tm, k, (0, -1), b.pos + b.vorn * 200, zielt=(t % 0.9) < 0.5)
        if t > 5.0:
            for g in lebende:
                g.ki_aus = False

    return ("Panzer: Turm, Kanone mit Feuerball und Krater, Bug-MG, Rammen",
            [b], lambda: uhr["t"] > 16.0, 18, 1.5, jedes_bild)


def szene_panzerwagen(tm, rnd):
    """Seit 0.34.59: der Panzerwagen zieht zaeh an, wird sehr schnell und
    rammt eine Gruppe; danach haelt der Schuetze mit dem Ring-MG drauf."""
    tx, ty, zelle = _feld_ganz_frei(tm, rnd, 44, 10)
    b, k = _fahrer_in(tm, "panzerwagen", zelle(3, 5), 0.0)
    gruppe = [tm.gegner_setzen("laeufer", zelle(30 + (i % 3) * 2, 3 + (i // 3) * 2), 0,
                               {"ki": False}) for i in range(7)]
    uhr = {"t": 0.0}

    def jedes_bild():
        uhr["t"] += 1.0 / BILDER_JE_SEKUNDE
        t = uhr["t"]
        lebende = [g for g in gruppe if g.lebt]
        if t < 6.0:
            _steuern(tm, k, (0, -1), b.pos + b.vorn * 300)
        else:
            ziel = lebende[0].pos if lebende else b.pos + b.vorn * 200
            _steuern(tm, k, (0, 1) if b.fahrt > 5 else (0, 0), ziel,
                     feuert=(t % 0.8) < 0.55)
            for g in lebende:
                g.ki_aus = False

    return ("Panzerwagen: zaeh, schnell, rammt - dann das Ring-MG",
            [b], lambda: uhr["t"] > 13.0, 15, 1.5, jedes_bild)


# ── Die Nacharbeit an den Fahrzeugen (seit 0.34.124, docs/UEBERGABE.md) ──
# Der Besitzer wollte am Ende alles "praesentiert": Videos und Bilder. Die
# Kamera folgt hier oft einem Blickpunkt statt Figuren - eine Rakete fliegt
# weiter, als das Bild breit ist.

class _Blick:
    """Ein Punkt, dem die Kamera folgt (wie eine Figur: pos, lebt, ebene)."""

    lebt = True
    ebene = 0

    def __init__(self, pos) -> None:
        self.pos = pygame.Vector2(pos)


def szene_funkwagen(tm, rnd):
    """Der Mast des Funkwagens als 3D-Modell: er liegt auf dem Dach, richtet
    sich auf, faehrt aus, der Kopf klappt auf, die Seile laufen aus; dann
    dreht sich der Kopf, und der Abbau laeuft rueckwaerts."""
    tx, ty, zelle = _feld_ganz_frei(tm, rnd, 12, 10)
    b, k = _fahrer_in(tm, "funkwagen", zelle(6, 5), 25.0)
    uhr = {"t": 0.0}

    def jedes_bild():
        uhr["t"] += 1.0 / BILDER_JE_SEKUNDE
        t = uhr["t"]
        # Rechte Maustaste kurz: bei 1 s aufbauen, bei 9 s wieder abbauen.
        _steuern(tm, k, (0, 0), b.pos + b.vorn * 100, zielt=(1.0 <= t < 1.05 or 9.0 <= t < 9.05))

    return ("Funkwagen: der Mast richtet sich auf, faehrt aus, Kopf klappt auf und dreht sich",
            [_Blick(b.mast_mitte() + pygame.Vector2(0, -14))], lambda: uhr["t"] > 13.0, 15, 1.0, jedes_bild)


def _werfer_mit_ziel(tm, rnd, abstand: float):
    """Ein Werfer mit Fahrer, vor ihm in `abstand` eine Gruppe Gegner und ein
    Kamerad, der sie sieht (sonst gilt das Ziel nicht, Gefecht.werfer_pruefen)."""
    tx, ty, zelle = _feld_ganz_frei(tm, rnd, 8, 8)
    b, k = _fahrer_in(tm, "werfer", zelle(4, 4), 0.0)
    ziel = b.pos + pygame.Vector2(abstand, 60)
    gruppe = [tm.puppe_setzen(ziel + pygame.Vector2((i % 3) * 22 - 22, (i // 3) * 22 - 11), 0,
                              {"team": 1, "leben": 5.0}, name="ZIEL") for i in range(6)]
    kamerad = tm.puppe_setzen(ziel + pygame.Vector2(-120, 30), 0, {"team": 0}, name="KAMERAD")
    tm.welt._raster_bauen()
    return b, k, ziel, gruppe, kamerad


def szene_werfer(tm, rnd):
    """Der Werfer: Stuetzen raus, das Gestell hebt sich und dreht zum
    Ziel, die Rohre stellen sich nach der Entfernung (erst nah und steil,
    dann weit und flacher). Die Salve: Rakete fuer Rakete aus ihrem Rohr,
    Rueckstrahl hinten, im Bogen ins Ziel; die Rohre laden einzeln nach."""
    b, k, ziel, gruppe, kamerad = _werfer_mit_ziel(tm, rnd, 820.0)
    nah = b.pos + pygame.Vector2(260, -330)
    blick = _Blick(b.pos)
    uhr = {"t": 0.0}

    def jedes_bild():
        uhr["t"] += 1.0 / BILDER_JE_SEKUNDE
        t = uhr["t"]
        zeiger = nah if t < 5.0 else ziel
        _steuern(tm, k, (0, 0), zeiger, zielt=(0.5 <= t < 0.55), feuert=(8.0 <= t < 8.3))
        # Die Kamera bleibt beim Werfer, bis die letzte Rakete draussen ist,
        # dann faehrt sie zum Ziel und sieht die Einschlaege.
        if t > 11.5:
            blick.pos.update(ziel)
        else:
            blick.pos.update(b.pos + pygame.Vector2(40, -20))

    return ("Werfer: Gestell hebt sich nach der Entfernung, Raketen im Bogen aus ihren Rohren",
            [blick], lambda: uhr["t"] > 19.0, 21, 1.0, jedes_bild)


def szene_werfer_explosion(tm, rnd):
    """Der Werfer geht hoch: die groesste Explosion des Spiels, kein Wrack."""
    b, k, ziel, gruppe, kamerad = _werfer_mit_ziel(tm, rnd, 820.0)
    for i in range(5):
        tm.puppe_setzen(b.pos + pygame.Vector2(math.cos(i * 1.3) * 150, math.sin(i * 1.3) * 110), 0,
                        {"team": 1}, name="DANEBEN")
    uhr = {"t": 0.0}

    def jedes_bild():
        uhr["t"] += 1.0 / BILDER_JE_SEKUNDE
        t = uhr["t"]
        _steuern(tm, k, (0, 0), ziel, zielt=(0.3 <= t < 0.35))
        if 5.0 <= t < 5.05 and not b.kaputt:
            b._zerstoeren(None)

    return ("Werfer: getroffen - die groesste Explosion, nur Einzelteile bleiben",
            [_Blick(b.pos)], lambda: uhr["t"] > 11.0, 13, 1.2, jedes_bild)


def szene_schrottbombe(tm, rnd):
    """Der Tragschrauber wirft seine zwei Schrottbomben (Dose mit Lunte) auf
    eine Gruppe: am Heli sieht man nichts, sie faellt neben der Kanzel,
    ueberschlaegt sich, die Lunte glimmt."""
    tx, ty, zelle = _feld_ganz_frei(tm, rnd, 30, 8)
    b, k = _fahrer_in(tm, "tragschrauber", zelle(3, 4), 0.0)
    gruppen = []
    for gx in (33, 44):
        gruppen.append([tm.gegner_setzen("laeufer", zelle(gx + (i % 2) * 1.2, 3.4 + (i // 2) * 1.2), 0,
                                         {"ki": False}) for i in range(4)])
    blick = _Blick(b.pos)
    uhr = {"t": 0.0}
    abgeworfen = []

    def jedes_bild():
        uhr["t"] += 1.0 / BILDER_JE_SEKUNDE
        feuer = False
        for i, g in enumerate(gruppen):
            mitte = sum((x.pos for x in g), pygame.Vector2()) / len(g)
            if i not in abgeworfen and b.hoch_oben and b.pos.x >= mitte.x - 16:
                feuer = True
                abgeworfen.append(i)
        _steuern(tm, k, (0, -1), b.pos + b.vorn * 200, feuert=feuer)
        blick.pos.update(b.pos + pygame.Vector2(0, -max(0.0, b.hoehe) * 0.5))

    return ("Tragschrauber: zwei Schrottbomben auf zwei Gruppen",
            [blick], lambda: uhr["t"] > 16.0 or len(abgeworfen) == 2 and not b.bomben_fall and uhr["t"] > 6,
            18, 1.0, jedes_bild)


def szene_flak(tm, rnd):
    """Der Flakwagen mit Bot gegen einen Tragschrauber: sichtbar ist die
    Leuchtspur, die zur Hoehe des Fliegers steigt, dazu das Muendungsfeuer;
    die Wolken platzen in seiner Hoehe."""
    tx, ty, zelle = _feld_ganz_frei(tm, rnd, 24, 10)
    ts = tm.fahrzeug_setzen("tragschrauber", zelle(2, 3), 0, {"winkel": 0})
    pilot = tm.puppe_setzen(ts.ausstiegsorte(9.0)[0], 0, {"team": 1}, name="PILOT")
    tm._einsteigen(pilot, ts)
    fl = tm.fahrzeug_setzen("flakwagen", zelle(16, 8), 0, {"winkel": -90})
    fahrer = tm.fahrer_setzen(fl.pos, 0, {"team": 0, "fahrzeug": "flakwagen"}, mit_fahrzeug=False)
    tm._einsteigen(fahrer, fl)
    tm.welt._raster_bauen()
    blick = _Blick(fl.pos)
    uhr = {"t": 0.0}

    def jedes_bild():
        uhr["t"] += 1.0 / BILDER_JE_SEKUNDE
        _steuern(tm, pilot, (0, -1), ts.pos + ts.vorn * 200)
        if ts.lebt and not ts.kaputt:
            blick.pos.update((fl.pos + ts.pos) / 2)

    return ("Flak: Leuchtspur zur Hoehe des Ziels, Wolken in seiner Hoehe",
            [blick], lambda: uhr["t"] > 16.0 or ts.kaputt and uhr["t"] > 8.0, 18, 1.1, jedes_bild)


def szene_krad(tm, rnd):
    """Das Krad faehrt einen Bogen, der Beifahrer im Beiwagen haelt seine
    Waffe auf einen Punkt - nur so weit, wie sein Sitz es erlaubt."""
    tx, ty, zelle = _feld_ganz_frei(tm, rnd, 24, 16)
    b, k = _fahrer_in(tm, "krad", zelle(4, 12), -20.0)
    bei = tm.puppe_setzen(b.pos + pygame.Vector2(20, 14), 0, {"team": 0, "waffe_figur": "sturm"}, name="BEI")
    tm._anwenden(bei, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
    punkt = zelle(14, 4)
    uhr = {"t": 0.0}

    def jedes_bild():
        uhr["t"] += 1.0 / BILDER_JE_SEKUNDE
        t = uhr["t"]
        _steuern(tm, k, (0.55 if t > 1.0 else 0.0, -0.55), b.pos + b.vorn * 100)
        tm._anwenden(bei, {"will": [0, 0], "ziel": [punkt.x, punkt.y], "knoepfe": []})

    return ("Krad: der Beifahrer zielt im Beiwagen, nur in seinem Bogen",
            [b], lambda: uhr["t"] > 11.0, 13, 1.0, jedes_bild)


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
    "mauer": ("13_volle_deckung_mauer", szene_mauer),
    "panik": ("14_panik_entscheidet", szene_panik),
    "bergen_mauer": ("15_bergen_hinter_die_mauer", szene_bergen_mauer),
    "ueberfall": ("16_ueberfall_ohne_funk", szene_ueberfall),
    "zange": ("17_zange_front_knickt", szene_zange),
    "zuruf": ("18_zuruf_statt_suchen", szene_zuruf),
    "bergen_puppen": ("19_bergen_gegen_puppen", szene_bergen_puppen),
    "abschnitte": ("20_geknickte_front", szene_abschnitte),
    "panzer": ("21_panzer", szene_panzer),
    "panzerwagen": ("22_panzerwagen", szene_panzerwagen),
    "funkwagen": ("23_funkwagen_mast", szene_funkwagen),
    "werfer": ("24_werfer_salve", szene_werfer),
    "werfer_explosion": ("25_werfer_explosion", szene_werfer_explosion),
    "schrottbombe": ("26_schrottbombe", szene_schrottbombe),
    "flak": ("27_flak_leuchtspur", szene_flak),
    "krad": ("28_krad_beifahrer", szene_krad),
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
    # Auch der Zufall der Bots (Merkmale, Namen, Aufstellung) steht fest
    # (seit 0.34.52): dieselbe Szene ist jedes Mal dieselbe Aufnahme.
    tm._bot_rnd.seed(seed if seed is not None else sum(map(ord, name)))
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
