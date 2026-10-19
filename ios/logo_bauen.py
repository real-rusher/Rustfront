"""
DUSTFRONT auf iOS - App-Symbol und Startbild
============================================

Seit 0.34.23. Die Vorlage von pygame-ios bringt das Logo von pygame-ce mit,
als App-Symbol und auf dem Bild, das beim Start der App kurz zu sehen
ist. Hier entsteht stattdessen ein eigenes Zeichen: der Stern mit seinen
drei Umlaufbahnen aus dem Intro - nur er, ohne Uhr und Fluegel drumherum
(die fanden wir nicht schoen). Gezeichnet wird mit denselben Pinseln wie
im Intro (splash_engine.py: Farbrampen, gerasterte Uebergaenge), nur gut
doppelt so gross, damit das Symbol auf dem Homescreen nicht aus wenigen
Klotzpixeln besteht:

    ios/bilder/AppIcon.png     1024 x 1024: das Zeichen
    ios/bilder/Startbild.png   das Zeichen mit dem Schriftzug darunter,
                               in der Schrift des Hauptmenues

ios/bauen.sh setzt beide in das Xcode-Projekt ein. Neu erzeugen:

    python ios/logo_bauen.py
"""

import math
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HIER))

import pygame  # noqa: E402

GROESSE = 128          # Leinwand des Zeichens; x 8 = 1024 fuer das Symbol
MASSSTAB = 1.85        # so viel groesser als im Intro; die Bahnen bleiben
                       # weg vom Rand, den iOS rund abschneidet
HIMMEL = (8, 13, 21)
# Die Bahnen wie im Intro (splash_engine.RINGS), angehalten in einem
# Augenblick, in dem sich keine zwei Lichtpunkte verdecken.
ZEIT = 9.0


def _zeichen():
    """Das Zeichen auf einer GROESSE x GROESSE grossen Flaeche."""
    import splash_engine as se
    # Die Pinsel des Intros rechnen mit der Groesse ihrer Leinwand aus dem
    # Modul. Fuer das Zeichen gilt kurz eine eigene - danach wie vorher.
    alt = (se.W, se.H, se.CX, se.CY, se.RINGS)
    try:
        se.W = se.H = GROESSE
        se.CX = se.CY = GROESSE / 2
        se.RINGS = [(r * MASSSTAB,) + tuple(rest) for (r, *rest) in alt[4]]
        eng = se.Engine(scheme="aurum")
        eng.fill(bytes(HIMMEL))
        _glimmen(eng, se)
        _sterne(eng, se)
        eng.draw_orbits(ZEIT)
        _stern(eng, se, MASSSTAB)
        bild = pygame.image.frombuffer(bytes(eng.buf), (GROESSE, GROESSE), "RGB").copy()
    finally:
        se.W, se.H, se.CX, se.CY, se.RINGS = alt
    return bild


def _glimmen(eng, se):
    """Ein schwacher Schein hinter dem Stern, damit er nicht im Leeren haengt."""
    r = GROESSE * 0.46
    for y in range(GROESSE):
        for x in range(GROESSE):
            d = math.hypot(x - se.CX, y - se.CY) / r
            if d < 1:
                eng.plot(x, y, eng.ENG, 0.2 + 0.7 * (1 - d), (1 - d) ** 2.8 * 0.4)


def _sterne(eng, se):
    """Ein paar ferne Sterne, fest gesaet - jedes Mal dieselben."""
    zufall = random.Random(1979)
    for _ in range(26):
        x, y = zufall.randrange(GROESSE), zufall.randrange(GROESSE)
        if math.hypot(x - se.CX, y - se.CY) < 40:
            continue
        eng.plot(x, y, eng.ENG, zufall.uniform(1.5, 4.5), 1.0)


def _stern(eng, se, s):
    """Der Stern wie in splash_engine.Engine.draw_star, um `s` vergroessert."""
    CX, CY, ENG = se.CX, se.CY, eng.ENG
    R = 17 * s
    for y in range(math.floor(CY - R), math.floor(CY + R) + 1):
        for x in range(math.floor(CX - R), math.floor(CX + R) + 1):
            dd = math.hypot(x - CX, y - CY)
            if dd <= R:
                v = 1 - dd / R
                eng.plot(x, y, ENG, 0.4 + v * 3.4, (v ** 2.1) * 0.95)
    L = 16 * s
    for ux, uy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        i = 1
        while i <= L:
            v = 1 - i / L
            th = round(2.5 * s * (v ** 1.5))
            for j in range(-th, th + 1):
                eng.plot(CX + ux * i - uy * j, CY + uy * i + ux * j, ENG,
                         3.4 + 4.6 * v * (1 - abs(j) / (th + 1.4)), v ** 0.85)
            i += 1
    L2 = 7.5 * s
    for ux, uy in ((0.707, 0.707), (-0.707, 0.707), (0.707, -0.707), (-0.707, -0.707)):
        i = 1
        while i <= L2:
            v = 1 - i / L2
            for j in (-0.5, 0, 0.5):
                eng.plot(CX + ux * i - uy * j, CY + uy * i + ux * j, ENG,
                         3 + 4.5 * v, (v ** 0.9) * 0.8)
            i += 1
    eng.disc(CX, CY, 3.3 * s, ENG, lambda dd: 8.4 - dd * 1.15 / s, 1)


def bauen(ziel_ordner=None) -> list:
    pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((8, 8))
    ordner = ziel_ordner or os.path.join(HIER, "bilder")
    os.makedirs(ordner, exist_ok=True)
    zeichen = _zeichen()

    # App-Symbol: x 8, ohne Weichzeichnen - die Pixel bleiben Pixel. iOS
    # rundet die Ecken selbst ab und will keine Durchsichtigkeit.
    symbol = pygame.transform.scale(zeichen, (GROESSE * 8, GROESSE * 8))
    pfad_symbol = os.path.join(ordner, "AppIcon.png")
    pygame.image.save(symbol, pfad_symbol)

    # Startbild: das Zeichen, darunter der Name in der Schrift des
    # Hauptmenues, mit dessen Unterstrich.
    import rustfront_menu as rm
    breite, hoehe = 240, 176
    start = pygame.Surface((breite, hoehe))
    start.fill(HIMMEL)
    start.blit(zeichen, ((breite - GROESSE) // 2, 0))
    skala = 3
    w = rm.FONT.width(rm.SPIEL_TITEL, skala, 2)
    x, y = (breite - w) // 2, GROESSE + 8
    rm.FONT.draw(start, rm.SPIEL_TITEL, x, y, rm.C_CREAM, skala, spacing=2,
                 shadow=(62, 26, 12))
    unten = y + 8 * skala
    pygame.draw.rect(start, rm.C_ORANGE, (x, unten, w, 2))
    pygame.draw.rect(start, rm.C_AMBER, (x, unten, 30, 2))
    start = pygame.transform.scale(start, (breite * 4, hoehe * 4))
    pfad_start = os.path.join(ordner, "Startbild.png")
    pygame.image.save(start, pfad_start)
    return [pfad_symbol, pfad_start]


if __name__ == "__main__":
    for p in bauen():
        print("geschrieben:", p)
