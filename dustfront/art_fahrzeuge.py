"""
DUSTFRONT - Panzer und Panzerwagen, gezeichnet (seit 0.34.59)
=============================================================

Die Bilder der beiden schweren Fahrzeuge. Entwurf und Abnahme kamen als
Paket (`rustfront_fahrzeuge`, README_IMMEDIATELY.md): Grafik, Groesse und
Insassen hat der Besitzer Runde fuer Runde gesehen und freigegeben. Hier
steht derselbe Zeichner, neu im Stil von art.py geschrieben.

Wie der Buggy (art._buggy_zeichnen): vierfach gross gezeichnet und weich
verkleinert, Licht von oben links, dunkler Rand ueber art._rand, Staub und
Rost. Beide schauen nach +x.

**Masse.** Gezeichnet wird in "Entwurfspixeln" mal K.FAHRZEUG_BILD
["groesse"] (abgenommen: 1,4 - gezeigt wurden 1,0, 1,2 und 1,4, und bei
1,4 haben die Insassen Spielergroesse). Ausnahmen stehen in Spielpixeln
und sind so markiert: Kommandantenkuppel, MG-Ring und Insasse haengen an
der Spielerfigur und duerfen **nicht** mitwachsen, wenn jemand die Groesse
aendert.

**Was sich bewegt, ist ein eigenes Bild.** Der Turm und der MG-Ring
drehen unabhaengig von der Wanne; ihr Drehpunkt ist die Bildmitte. Die
Ketten laufen (eine Phase je Seite, `panzer_wanne`), die Reifen auch, und
ab einem Tempo sind sie verwischt (`panzerwagen_wanne`, unscharf) - sonst
laufen sie scheinbar rueckwaerts wie Speichen im Film.

**Registriert** sind die Fassungen, die man durch eine Datei ersetzen kann
(`panzer`, `panzer_turm`, ...). Die Zwischenstufen der Ketten und des
Rohrruecklaufs kommen aus `wanne_bild` und `aufbau_bild` mit eigenem
Zwischenspeicher: 12 x 12 Kettenphasen mal 120 Winkel waeren ueber 17 000
Flaechen. Liegt eine Datei da, gilt sie, und die Kette steht still.
"""

from __future__ import annotations

import math
import random
from collections import OrderedDict

import pygame

from . import art
from . import config as K
from .core import platzhalter

_SS = 4                                   # Ueberabtastung wie beim Buggy
_FB = K.FAHRZEUG_BILD
GROESSE = _FB["groesse"]
N = _FB["flaeche"]                        # Bildmass von Wanne und Turm
TG = GROESSE / 1.2                        # der Turm waechst mit, die Kuppel nicht


class _Blatt:
    """Zeichenflaeche n x n Bildpixel, Mitte (0, 0), vierfach gross.

    Alle Masse in Entwurfspixeln, mal `g` skaliert. Dasselbe wie
    art._bp / art._bp_rect, nur mit Groesse und Bildmass als Werte statt
    fester 64 Pixel."""

    def __init__(self, n=N, g=GROESSE) -> None:
        self.n, self.g = n, g
        self.s = pygame.Surface((n * _SS, n * _SS), pygame.SRCALPHA)

    def p(self, x, y):
        m = self.n / 2 * _SS
        return (m + x * _SS * self.g, m + y * _SS * self.g)

    def d(self, v):
        return v * _SS * self.g

    def r(self, x, y, w, h):
        a = self.p(x, y)
        return pygame.Rect(round(a[0]), round(a[1]), round(self.d(w)), round(self.d(h)))

    def poly(self, f, punkte):
        pygame.draw.polygon(self.s, f, [self.p(*q) for q in punkte])

    def linie(self, f, a, b, dick):
        pygame.draw.line(self.s, f, self.p(*a), self.p(*b), max(1, round(self.d(dick))))

    def linien(self, f, punkte, dick):
        pygame.draw.lines(self.s, f, False, [self.p(*q) for q in punkte],
                          max(1, round(self.d(dick))))

    def kreis(self, f, c, rad):
        pygame.draw.circle(self.s, f, self.p(*c), self.d(rad))

    def rect(self, f, x, y, w, h, rund=0.0):
        pygame.draw.rect(self.s, f, self.r(x, y, w, h), border_radius=round(self.d(rund)))

    def ellipse(self, f, x, y, w, h):
        pygame.draw.ellipse(self.s, f, self.r(x, y, w, h))

    def rohr(self, a, b, dicke=1.6, farbe=art.BUGGY_ROHR, kante=art.BUGGY_ROHR_DK):
        """Ein Rohr von oben: dunkler Rand, heller Kern, runde Enden."""
        for f, dd in ((kante, dicke), (farbe, dicke * 0.55)):
            breite = max(1, round(self.d(dd)))
            pygame.draw.line(self.s, f, self.p(*a), self.p(*b), breite)
            for q in (a, b):
                pygame.draw.circle(self.s, f, self.p(*q), breite / 2)

    def segment(self, f, r0, r1, a0, a1, cx=0.0, cy=0.0):
        """Ein Stueck Kreisring als Vieleck (Winkel in Grad, y nach unten).

        GRUND: pygame.draw.arc mit grosser Breite fuellt bei kleinen Radien
        den Innenraum - der Lukenrand war dann eine Scheibe. Nicht auf arc
        zurueckbauen."""
        n = 16
        au = [math.radians(a0 + (a1 - a0) * i / n) for i in range(n + 1)]
        punkte = [(cx + math.cos(a) * r1, cy + math.sin(a) * r1) for a in au]
        punkte += [(cx + math.cos(a) * r0, cy + math.sin(a) * r0) for a in reversed(au)]
        self.poly(f, punkte)

    def fertig(self, rand=True) -> pygame.Surface:
        klein = pygame.transform.smoothscale(self.s, (self.n, self.n))
        return art._rand(klein) if rand else klein


def _schrumpfen(punkte, fx, fy, dx=0.0):
    return [(x * fx + dx, y * fy) for x, y in punkte]


def _staub(b, rnd, n, x0, x1, y0, y1, farben):
    for _ in range(n):
        b.kreis(rnd.choice(farben), (rnd.uniform(x0, x1), rnd.uniform(y0, y1)),
                rnd.uniform(0.25, 0.6))


_ROST = [(128, 70, 38), (104, 58, 34), (150, 92, 50)]

# ──────────────────────────────── Ketten und Reifen

_GLIED = (66, 62, 56)
_GLIED_HELL = (118, 112, 100)
_GLIED_DK = (40, 37, 33)
_FUGE = (14, 12, 11)


def _kette(b, x0, x1, y, breit, phase) -> None:
    """Eine Kette von oben. `phase` 0 bis 1 je Glied: das obere Trum laeuft
    beim Vorwaertsfahren nach vorn. An den Enden laeuft sie in die Tiefe
    weg - dort werden die Glieder kuerzer und dunkler."""
    b.rect(_FUGE, x0, y - breit / 2, x1 - x0, breit, 2.4)
    b.s.set_clip(b.r(x0 + 0.3, y - breit / 2 + 0.3, x1 - x0 - 0.6, breit - 0.6))
    t = _FB["kette_teilung"]
    versatz = (phase % 1.0) * t
    rund = 3.2                         # so lang ist die Rundung an jedem Ende
    i = -1
    while True:
        gx = x0 - t + versatz + i * t
        i += 1
        if gx > x1 + t:
            break
        mitte = gx + t / 2
        rest = min(mitte - x0, x1 - mitte)
        tiefe = max(0.0, min(1.0, 1 - rest / rund))     # 0 oben, 1 ganz unten
        laenge = (t - 0.55) * (1 - 0.55 * tiefe)
        dunkel = 1 - 0.6 * tiefe

        def f(c, d=dunkel):
            return tuple(int(k * d) for k in c)

        gy0, gh = y - breit / 2 + 0.55, breit - 1.1
        b.rect(f(_GLIED), gx, gy0, laenge, gh, 0.35)
        # Greifersteg quer, Licht von oben links: helle Kante vorn
        b.linie(f(_GLIED_HELL), (gx + laenge * 0.45, gy0 + 0.4),
                (gx + laenge * 0.45, gy0 + gh - 0.4), 0.7)
        b.linie(f(_GLIED_DK), (gx + laenge * 0.45 + 0.6, gy0 + 0.4),
                (gx + laenge * 0.45 + 0.6, gy0 + gh - 0.4), 0.45)
        for sy in (-1, 1):                               # Bolzen an den Enden
            b.kreis(f((140, 134, 120)), (gx + 0.35, y + sy * (gh / 2 - 0.7)), 0.3)
        b.rect(f((150, 144, 130)), gx + laenge * 0.2, y - 0.55, 0.9, 1.1, 0.2)  # Zahn
    b.s.set_clip(None)
    # Schatten ueber die Rundung, damit die Kette nicht abgeschnitten wirkt
    for ex, vz in ((x0, 1), (x1, -1)):
        for k in range(4):
            x = ex + k * 0.8 if vz > 0 else ex - (k + 1) * 0.8
            b.rect((0, 0, 0, 90 - k * 22), x, y - breit / 2, 0.8, breit, 0)


def _reifen(b, x, y, lang, breit, phase, unscharf=False) -> None:
    """Stollenreifen von oben; die Stollen wandern mit der Phase. Schnell
    gefahren (`unscharf`) ist die Lauffläche verwischt."""
    b.rect((22, 19, 17), x - lang / 2, y - breit / 2, lang, breit, 2.2)
    b.rect((46, 41, 37), x - lang / 2 + 0.25, y - breit / 2 + 0.25,
           lang - 0.5, breit - 0.5, 1.8)
    b.s.set_clip(b.r(x - lang / 2 + 0.8, y - breit / 2, lang - 1.6, breit))
    t = 2.15
    versatz = (phase % 1.0) * t
    if unscharf:
        for k in range(int(lang * 2)):
            sx = x - lang / 2 + k * 0.5
            rel = abs(sx - x) / (lang / 2)
            hell = max(0.35, 1 - rel * rel * 0.65)
            b.linie(tuple(int(v * hell) for v in (72, 66, 59)),
                    (sx, y - breit / 2 + 1), (sx, y + breit / 2 - 1), 0.6)
    else:
        for i in range(-1, int(lang / t) + 2):
            sx = x - lang / 2 + versatz + i * t
            # zur Mitte hin hell, zu den Enden dunkel - der Reifen ist rund
            rel = abs(sx - x) / (lang / 2)
            hell = max(0.35, 1 - rel * rel * 0.65)
            o = 0.6 if i % 2 else -0.6
            b.linie(tuple(int(k * hell) for k in (104, 96, 86)),
                    (sx, y - breit / 2 + 1 + max(0, o)),
                    (sx, y + breit / 2 - 1 + min(0, o)), 0.9)
    b.s.set_clip(None)
    b.linie((96, 88, 80), (x - lang / 2 + 1.5, y - breit / 2 + 0.6),
            (x + lang / 2 - 1.5, y - breit / 2 + 0.6), 0.5)


# ──────────────────────────────── Panzer

PZ_LACK = (138, 128, 86)          # ausgeblichenes Oliv-Khaki
PZ_DK = (74, 68, 44)
PZ_HELL = (176, 166, 118)
PZ_SCHATTEN = (108, 99, 64)
_BUG_MG = (33.5, 5.0)             # Muendung des Bug-MGs, Entwurfspixel


def panzer_wanne(ph_links: float = 0.0, ph_rechts: float = 0.0) -> pygame.Surface:
    """Die Wanne mit Ketten, Bugplatte, Fahrerluke, Scheinwerfern,
    Motordeck, Auspuffen, Ersatzgliedern, Kanister und dem festen Bug-MG.
    Links ist -y (beim Blick nach +x)."""
    b = _Blatt()
    rnd = random.Random(5101)
    _kette(b, -31.5, 31.5, -17, 8.4, ph_links)
    _kette(b, -31.5, 31.5, 17, 8.4, ph_rechts)
    umriss = [(29, -8), (26, -14), (-26, -14), (-30, -11), (-30, 11),
              (-26, 14), (26, 14), (29, 8)]
    b.poly(PZ_DK, umriss)
    b.poly(PZ_LACK, _schrumpfen(umriss, 0.95, 0.9, -0.2))
    glacis = [(28.4, -7.6), (25.6, -12.4), (17, -12.4), (17, 12.4), (25.6, 12.4),
              (28.4, 7.6)]
    b.poly(PZ_HELL, glacis)
    b.linie(PZ_DK, (17, -12.4), (17, 12.4), 0.7)
    b.linien(PZ_HELL, [(25, -12.8), (-25, -12.8), (-28.4, -10.2)], 0.9)
    b.linien(PZ_SCHATTEN, [(25, 12.8), (-25, 12.8), (-28.4, 10.2)], 0.9)
    # Fahrerluke mit Winkelspiegeln
    b.kreis(PZ_DK, (20.5, -6.5), 3.0)
    b.kreis(PZ_SCHATTEN, (20.5, -6.5), 2.4)
    b.kreis(PZ_HELL, (19.9, -7.1), 0.9)
    for dy in (-1.6, 0, 1.6):
        b.rect((32, 40, 46), 23.2, -6.5 + dy - 0.4, 1.2, 0.8, 0.2)
    for sy in (-1, 1):                                   # Scheinwerfer mit Buegel
        b.kreis((40, 34, 28), (26.4, sy * 10.6), 1.5)
        b.kreis((255, 236, 170), (26.6, sy * 10.6), 1.0)
        b.rohr((25, sy * 12.4), (28.6, sy * 11.6), 0.9)
    b.kreis((40, 36, 30), (29.6, -4.5), 1.1)
    b.kreis((96, 92, 86), (29.6, -4.5), 0.55)
    # Bug-MG, fest: schiesst nur in Fahrtrichtung. Kugelblende und Lauf.
    b.rohr((27.5, _BUG_MG[1]), (_BUG_MG[0] - 0.6, _BUG_MG[1]), 1.3, (90, 88, 82), (28, 26, 24))
    b.rect((28, 26, 24), _BUG_MG[0] - 1.6, _BUG_MG[1] - 0.9, 1.8, 1.8, 0.4)
    b.kreis((40, 36, 30), (26.2, _BUG_MG[1]), 2.3)
    b.kreis(PZ_SCHATTEN, (26.2, _BUG_MG[1]), 1.8)
    b.kreis(PZ_HELL, (25.7, _BUG_MG[1] - 0.5), 0.7)
    # Motordeck mit Gitter, Auspuffe, Ersatzglieder, Kanister
    pygame.draw.rect(b.s, (40, 38, 34), b.r(-27, -9, 13, 18), border_radius=round(b.d(1.2)))
    b.rect((70, 66, 56), -26.7, -8.7, 12.4, 17.4, 1.0)
    for i in range(7):
        y = -7.4 + i * 2.45
        b.linie((34, 32, 28), (-26, y), (-15, y), 0.9)
    for sy in (-1, 1):
        b.rect((44, 40, 36), -31.2, sy * 11 - 1.6, 4, 3.2, 0.8)
        b.kreis((18, 16, 14), (-31.2, sy * 11), 0.9)
    for i in range(3):
        b.rect((36, 33, 30), -13 + i * 2.6, 9.6, 2.2, 3.2, 0.3)
    b.rect((40, 50, 34), -13, -12.8, 6.2, 3.2, 0.6)
    b.rect((86, 104, 62), -12.6, -12.4, 5.4, 2.4, 0.5)
    for x in range(-22, 16, 4):                          # Nieten am Rand
        for sy in (-1, 1):
            b.kreis(PZ_DK, (x, sy * 11.4), 0.45)
    _staub(b, rnd, 60, -29, 28, -12.5, 12.5,
           [(150, 140, 96), (120, 110, 72), (176, 166, 126), (110, 96, 64)])
    for _ in range(14):
        b.kreis(rnd.choice(_ROST), (rnd.uniform(-28, 26),
                                    rnd.choice((-1, 1)) * rnd.uniform(11, 13)),
                rnd.uniform(0.3, 0.8))
    return b.fertig()


_KUPPEL = (-4, -4)                # Mitte der Kommandantenkuppel (Turm-Entwurfspixel)
_KUPPEL_R = 10.0                  # Spielpixel: passt genau um die Spielerfigur
# Spielpixel: so weit liegt der Lukenrand ueber dem Schulterrand. Groesser
# heisst: mehr Schulter sichtbar.
_LUKE_INNEN = 6.4


def panzer_turm(fahrer=None, rueckstoss: float = 0.0) -> pygame.Surface:
    """Der Turm, eigenes Bild: Drehpunkt in der Bildmitte, schaut nach +x.
    Rohr mit Rauchabsauger und Muendungsbremse, Staukorb, Ladeschuetzenluke
    und die grosse Kommandantenkuppel. Mit `fahrer` steht der Kommandant in
    der Luke (ohne Arme), der Deckel ist dahinter hochgeklappt; ohne ist die
    Luke zu. `rueckstoss`: so viele Pixel faehrt das Rohr nach dem Schuss
    zurueck."""
    b = _Blatt(N, TG)
    rnd = random.Random(5102)
    r = -rueckstoss / TG
    rr = _KUPPEL_R / TG
    # Rohr
    b.rect((30, 28, 24), 10 + r, -2.2, 31, 4.4, 1.2)
    b.rect((96, 92, 78), 10.6 + r, -1.4, 30, 2.8, 1.0)
    b.linie((142, 136, 116), (11 + r, -0.8), (40 + r, -0.8), 0.5)
    b.rect((30, 28, 24), 21 + r, -3.1, 6, 6.2, 2.0)          # Rauchabsauger
    b.rect((104, 98, 80), 21.6 + r, -2.5, 4.8, 5.0, 1.6)
    b.rect((26, 24, 20), 38 + r, -3.6, 6, 7.2, 1.0)          # Muendungsbremse
    b.rect((88, 84, 74), 38.6 + r, -3.0, 4.8, 6.0, 0.8)
    b.linie((26, 24, 20), (41 + r, -3.0), (41 + r, 3.0), 1.0)
    # Staukorb hinten
    korb = [(-13, -10), (-20, -10), (-22, -7.5), (-22, 7.5), (-20, 10), (-13, 10)]
    b.poly((30, 28, 24), korb)
    for x in (-21, -18.6, -16.2, -13.8):
        b.linie((84, 80, 70), (x, -9.2), (x, 9.2), 0.6)
    b.rect((112, 92, 60), -20.6, 1.5, 5.5, 7.0, 0.8)
    b.rect((70, 84, 52), -19.8, -8.4, 4.6, 5.6, 0.6)
    # Turm
    umriss = [(11, -5), (7, -13.5), (-7, -16), (-14, -12.5), (-14, 12.5), (-7, 16),
              (7, 13.5), (11, 5)]
    b.poly((40, 36, 22), [(x * 1.05, y * 1.06) for x, y in umriss])
    b.poly(PZ_DK, umriss)
    b.poly(PZ_LACK, _schrumpfen(umriss, 0.93, 0.91, -0.2))
    b.linien(PZ_HELL, [(9.6, -5.6), (6.4, -12.2), (-6.6, -14.5), (-12.6, -11.6)], 1.0)
    b.linien(PZ_SCHATTEN, [(9.6, 5.6), (6.4, 12.2), (-6.6, 14.5), (-12.6, 11.6)], 1.0)
    # Blende - sie geht ein Stueck mit dem Rohr zurueck
    b.rect(PZ_DK, 7.6 + r * 0.3, -5.6, 5.0, 11.2, 1.4)
    b.rect(PZ_HELL, 8.1 + r * 0.3, -4.9, 3.8, 9.8, 1.2)
    # Zieloptik, Ladeschuetzenluke, Antennenfuss
    b.rect((30, 30, 30), 2, 7, 4.6, 2.8, 0.6)
    b.rect((60, 92, 110), 5.4, 7.5, 1.0, 1.8, 0.3)
    b.kreis(PZ_DK, (-5, 9.5), 3.6)
    b.kreis(PZ_SCHATTEN, (-5, 9.5), 2.9)
    b.linie(PZ_DK, (-7, 9.5), (-3, 9.5), 0.6)
    b.kreis((28, 26, 24), (-12, 12.4), 0.8)
    _staub(b, rnd, 40, -12, 9, -12, 12,
           [(150, 140, 96), (120, 110, 72), (176, 166, 126), (110, 96, 64)])
    # Kuppel: Ring mit Winkelspiegeln
    c = _KUPPEL
    b.kreis(PZ_DK, c, rr)
    b.kreis(PZ_SCHATTEN, c, rr - 0.8)
    for i in range(8):
        a = i * math.pi / 4 + 0.4
        b.rect((40, 58, 70), c[0] + math.cos(a) * (rr - 0.9) - 0.6,
               c[1] + math.sin(a) * (rr - 0.9) - 0.6, 1.2, 1.2, 0.3)
    if fahrer is None:
        b.kreis(PZ_DK, c, rr - 1.8)
        b.kreis(PZ_LACK, c, rr - 2.4)
        b.kreis(PZ_HELL, (c[0] - 2, c[1] - 2), 2.4)
        b.rect(PZ_DK, c[0] - rr + 1.4, c[1] - 1, 3, 2, 0.4)    # Scharnier hinten
    else:
        b.kreis((18, 16, 14), c, rr - 1.8)
        b.ellipse(PZ_DK, c[0] - rr - 4.4, c[1] - 7, 5, 14)      # Deckel hochgeklappt
        b.ellipse(PZ_HELL, c[0] - rr - 3.9, c[1] - 6.3, 3.8, 12.6)
        art._insasse_auf(b.s, _SS, N // 2, fahrer, c[0] * TG, c[1] * TG, arme=None)
        # Der Lukenrand liegt ueber den Schultern: er steht IN der Luke.
        innen = _LUKE_INNEN / TG
        b.segment(PZ_DK, innen, rr, -180, 180, c[0], c[1])
        b.segment(PZ_SCHATTEN, innen + 0.5 / TG, rr - 0.7 / TG, -180, 180, c[0], c[1])
        b.segment(PZ_HELL, innen + 0.6 / TG, innen + 1.4 / TG, -170, -100, c[0], c[1])
        for i in range(8):
            a = i * math.pi / 4 + 0.4
            b.rect((40, 58, 70), c[0] + math.cos(a) * (rr - 1.4 / TG) - 0.5,
                   c[1] + math.sin(a) * (rr - 1.4 / TG) - 0.5, 1.0, 1.0, 0.3)
    return b.fertig()


# ──────────────────────────────── Panzerwagen

LW_LACK = (124, 112, 94)          # verwittertes Stahlgrau-Braun
LW_DK = (62, 54, 44)
LW_HELL = (164, 150, 126)
LW_SCHATTEN = (96, 86, 70)
_RING = (-12.5, 0)                # Mitte des Drehrings, Entwurfspixel


def panzerwagen_wanne(ph_links: float = 0.0, ph_rechts: float = 0.0,
                      unscharf: bool = False) -> pygame.Surface:
    """Drei Achsen, Keilramme, Fuehrerhaus mit Sehschlitzen,
    Mannschaftsraum mit Nieten, Dachluke, Ersatzrad und der Sockel des
    Drehrings. Der drehende Teil des Rings ist ein eigenes Bild."""
    b = _Blatt()
    rnd = random.Random(5201)
    for ax in (18, -8, -19):
        b.rohr((ax, -9), (ax, 9), 1.8, (96, 92, 86))
    for ax, br in ((18, 6.2), (-8, 7), (-19, 7)):
        _reifen(b, ax, -14.0, 11, br, ph_links, unscharf)
        _reifen(b, ax, 14.0, 11, br, ph_rechts, unscharf)
    ramme = [(34, 0), (30, -12), (27.5, -12), (27.5, 12), (30, 12)]
    b.poly((34, 30, 26), ramme)
    b.poly((112, 106, 96), _schrumpfen(ramme, 0.96, 0.88, 0.6))
    b.linie((64, 60, 54), (28.5, -10), (32.6, 0), 0.6)
    b.linie((64, 60, 54), (28.5, 10), (32.6, 0), 0.6)
    for sy in (-1, 1):
        b.rohr((25, sy * 7), (28.5, sy * 7), 1.4)
    haube = [(27, -7.5), (25, -10), (12, -11), (12, 11), (25, 10), (27, 7.5)]
    b.poly(LW_DK, haube)
    b.poly(LW_LACK, _schrumpfen(haube, 0.95, 0.88, 0.4))
    for i in range(5):
        y = -4 + i * 2
        b.linie(LW_DK, (19, y), (25, y), 0.7)
    kabine = [(12, -11.5), (3, -11.5), (3, 11.5), (12, 11.5)]
    b.poly(LW_DK, kabine)
    b.poly(LW_SCHATTEN, _schrumpfen(kabine, 0.94, 0.9, 0.45))
    b.rect(LW_HELL, 4.2, -9.8, 7, 19.6, 1.2)
    for sy in (-1, 1):                                   # Sehschlitze
        b.rect((24, 30, 36), 11.4, sy * 5 - 2.6, 1.4, 5.2, 0.4)
        b.rect((70, 96, 112), 11.6, sy * 5 - 2.0, 0.6, 2.0, 0.2)
    b.kreis(LW_DK, (7.5, -4.5), 2.3)
    b.kreis(LW_LACK, (7.5, -4.5), 1.7)
    for sy in (-1, 1):                                   # Spiegel
        b.rohr((10, sy * 11), (12, sy * 14.5), 0.8)
        b.rect((30, 30, 32), 11.2, sy * 14.5 - 1.1, 1.6, 2.2, 0.4)
    kasten = [(2, -12.5), (-28, -12.5), (-29.5, -11), (-29.5, 11), (-28, 12.5), (2, 12.5)]
    b.poly(LW_DK, kasten)
    b.poly(LW_LACK, _schrumpfen(kasten, 0.95, 0.9, -0.3))
    b.linien(LW_HELL, [(1, -11.2), (-27.4, -11.2), (-28.4, -10)], 0.9)
    b.linien(LW_SCHATTEN, [(1, 11.2), (-27.4, 11.2), (-28.4, 10)], 0.9)
    for x in (-8, -18):
        b.linie(LW_DK, (x, -11.2), (x, 11.2), 0.6)
    for x in (0, -6, -10, -16, -20, -26):               # Nieten
        for sy in (-1, 1):
            b.kreis(LW_DK, (x, sy * 10.2), 0.45)
    b.rect(LW_DK, -28.6, -3.5, 4.4, 7, 0.8)             # Dachluke hinten
    b.rect(LW_SCHATTEN, -28.2, -3.0, 3.6, 6, 0.6)
    b.linie(LW_HELL, (-27.8, -2.6), (-24.8, -2.6), 0.4)
    b.kreis((22, 19, 17), (-30.6, -6.5), 3.0)            # Ersatzrad
    b.kreis((46, 41, 37), (-30.6, -6.5), 2.3)
    b.kreis((96, 92, 86), (-30.6, -6.5), 1.0)
    b.rect((40, 50, 34), -15, 9.2, 4.5, 3.4, 0.5)
    b.rect((86, 104, 62), -14.6, 9.6, 3.7, 2.6, 0.4)
    _staub(b, rnd, 60, -28, 26, -11, 11,
           [(144, 132, 112), (112, 100, 82), (172, 158, 132), (104, 90, 70)])
    for _ in range(18):
        b.kreis(rnd.choice(_ROST), (rnd.uniform(-28, 26), rnd.uniform(-11.5, 11.5)),
                rnd.uniform(0.3, 0.9))
    # Sockel des Drehrings (der drehende Teil ist ein eigenes Bild)
    c = _RING
    k = 1.2 / GROESSE
    b.kreis((34, 30, 26), c, 9.6 * k)
    b.kreis((88, 84, 76), c, 9.0 * k)
    b.kreis((60, 56, 50), c, 8.2 * k)
    for i in range(12):
        a = i * math.pi / 6
        b.kreis((40, 36, 32), (c[0] + math.cos(a) * 8.6 * k, c[1] + math.sin(a) * 8.6 * k), 0.35)
    return b.fertig()


def panzerwagen_ring(fahrer=None, rueckstoss: float = 0.0) -> pygame.Surface:
    """Der drehende Teil des MG-Rings: Schild, MG mit Kuehlmantel,
    Gurtkasten, Schuetze. In Spielpixeln, Drehpunkt in der Bildmitte. Der
    Ringrand liegt ueber den Schultern, MG und Schild darueber - man sieht
    nur Kopf, Schultern und Haende. Leer: ein offenes Loch."""
    n = _FB["ring_flaeche"]
    b = _Blatt(n, 1.0)
    r = -rueckstoss
    b.kreis((16, 14, 12), (0, 0), 9.4)                      # Oeffnung
    if fahrer is not None:
        art._insasse_auf(b.s, _SS, n // 2, fahrer, -1, 0, arme=7)
    b.segment((34, 30, 26), 6.8, 9.6, -180, 180)            # Ringrand
    b.segment((88, 84, 76), 7.3, 9.0, -180, 180)
    b.segment(LW_HELL, 7.4, 8.0, -170, -100)
    # MG: Gehaeuse, Kuehlmantel mit Loechern, Feuerdaempfer, Gurtkasten
    b.rect((26, 24, 22), 5 + r, -2.2, 8, 4.4, 0.8)
    b.rect((78, 76, 70), 5.5 + r, -1.6, 7, 3.2, 0.6)
    b.rect((26, 24, 22), 12 + r, -1.6, 14, 3.2, 1.0)
    b.rect((90, 88, 82), 12.4 + r, -1.0, 13.2, 2.0, 0.6)
    for x in range(14, 25, 2):
        b.kreis((30, 28, 26), (x + r, 0), 0.45)
    b.rect((26, 24, 22), 25.5 + r, -1.4, 3.2, 2.8, 0.6)
    b.rect((40, 50, 34), 6, 2.6, 4.4, 4.4, 0.6)
    b.rect((86, 104, 62), 6.4, 3.0, 3.6, 3.6, 0.5)
    # Schild vorn, ein gebogenes Panzerblech
    b.segment((34, 30, 26), 8.6, 12.0, -62, 62)
    b.segment(LW_HELL, 9.4, 11.2, -56, -3)
    b.segment(LW_SCHATTEN, 9.4, 11.2, 3, 56)
    b.rect((26, 24, 22), 8.4 + r, -1.8, 4, 3.6, 0.6)        # Laufdurchfuehrung
    b.rect((90, 88, 82), 8.6 + r, -1.0, 3.6, 2.0, 0.4)
    return b.fertig()


# ──────────────────────────────── Wracks und Schatten

def _wrack(bild: pygame.Surface, seed: int) -> pygame.Surface:
    """Verkohlt: alles dunkler, Flecken nur dort, wo Fahrzeug ist (die
    eigene Deckkraft als Maske), dazu Glutpunkte. Wie art._buggy_wrack."""
    s = bild.copy()
    s.fill((70, 62, 58, 255), special_flags=pygame.BLEND_RGBA_MULT)
    n = s.get_width()
    schicht = pygame.Surface((n, n), pygame.SRCALPHA)
    rnd = random.Random(seed)
    for _ in range(70):
        x, y = rnd.uniform(-34, 34), rnd.uniform(-16, 16)
        f = rnd.choice([(18, 16, 14), (34, 30, 28), (52, 44, 38)] * 3 + [(120, 60, 30)])
        pygame.draw.circle(schicht, f + (255,), (n // 2 + int(x), n // 2 + int(y)),
                           rnd.randint(1, 3))
    for gx, gy in ((-24, -4), (-7, 6)):
        pygame.draw.circle(schicht, (200, 90, 30, 255), (n // 2 + gx, n // 2 + gy), 3)
        pygame.draw.circle(schicht, (255, 170, 60, 255), (n // 2 + gx, n // 2 + gy), 1)
    maske = bild.copy()
    maske.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
    schicht.blit(maske, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(schicht, (0, 0))
    return s


def _schatten(lang: int, breit: int, rund: int) -> pygame.Surface:
    """Laenglich, weich; der Zeichner dreht ihn mit und legt ihn nach unten
    rechts, wie den des Buggys."""
    s = pygame.Surface((N, N), pygame.SRCALPHA)
    pygame.draw.rect(s, (0, 0, 0, 120), (N // 2 - lang // 2, N // 2 - breit // 2, lang, breit),
                     border_radius=rund)
    for _ in range(2):
        s = pygame.transform.smoothscale(pygame.transform.smoothscale(s, (32, 32)), (N, N))
    return s


def _panzer_ganz(fahrer=None) -> pygame.Surface:
    """Wanne und Turm in einem Bild, Turm nach vorn - fuer das Wrack."""
    s = panzer_wanne().copy()
    t = panzer_turm(fahrer)
    s.blit(t, t.get_rect(center=(N / 2 + K.PANZER["turm_vor"], N / 2)))
    return s


def _panzerwagen_ganz(fahrer=None) -> pygame.Surface:
    s = panzerwagen_wanne().copy()
    t = panzerwagen_ring(fahrer)
    rx, ry = K.PANZERWAGEN["ring"]
    s.blit(t, t.get_rect(center=(N / 2 + rx, N / 2 + ry)))
    return s


# ──────────────────────────────── Registratur
#
# Was durch eine Datei ersetzbar ist. Insassen in den Farben jeder
# Mannschaft ueber eine Schleife, wie beim Buggy: eine dritte Mannschaft
# bekommt ihre Bilder von selbst.

def _kombi_fahrer(kombi) -> tuple:
    return (kombi["rumpf"], kombi["kante"], kombi["akzent"])


_NEUTRAL = (K.C_HULL, K.C_HULL_SH, K.C_TEAL)


@platzhalter("panzer")
def _panzer():
    return panzer_wanne()


@platzhalter("panzer_turm")
def _panzer_turm():
    return panzer_turm()


@platzhalter("panzer_turm_fahrer")
def _panzer_turm_fahrer():
    return panzer_turm(_NEUTRAL)


@platzhalter("panzer_wrack")
def _panzer_wrack():
    return _wrack(_panzer_ganz(), 5180)


@platzhalter("panzer_schatten")
def _panzer_schatten():
    return _schatten(int(66 * GROESSE), int(42 * GROESSE), 14)


@platzhalter("panzerwagen")
def _panzerwagen():
    return panzerwagen_wanne()


@platzhalter("panzerwagen_ring")
def _panzerwagen_ring():
    return panzerwagen_ring()


@platzhalter("panzerwagen_ring_fahrer")
def _panzerwagen_ring_fahrer():
    return panzerwagen_ring(_NEUTRAL)


@platzhalter("panzerwagen_wrack")
def _panzerwagen_wrack():
    return _wrack(_panzerwagen_ganz(), 5280)


@platzhalter("panzerwagen_schatten")
def _panzerwagen_schatten():
    return _schatten(int(64 * GROESSE), int(30 * GROESSE), 11)


def _aufbau_team(zeichner, kombi):
    def z():
        return zeichner(_kombi_fahrer(kombi))
    return z


for _kombi in K.TEAMS["kombi"]:
    _kurz = _kombi["name"].lower()
    platzhalter("panzer_turm_%s_fahrer" % _kurz)(_aufbau_team(panzer_turm, _kombi))
    platzhalter("panzerwagen_ring_%s_fahrer" % _kurz)(_aufbau_team(panzerwagen_ring, _kombi))


# ──────────────────────────────── Bewegte Fassungen
#
# Stolperfalle aus dem Paket: `Bilder.gedreht` merkt sich jede Fassung je
# (Name, Winkel). Mit 12 x 12 Kettenphasen und 120 Winkeln waeren das ueber
# 17 000 Flaechen. Darum hier: ungedrehte Wannen je Phasenpaar (hoechstens
# 144 zu je 64 KB) und die gedrehten nur in einem kleinen Speicher, der
# das am laengsten Ungenutzte vergisst. Im Stand aendert sich die Phase
# nicht, dann trifft er immer.

_WANNEN: dict = {}
_GEDREHT: "OrderedDict[tuple, pygame.Surface]" = OrderedDict()


def _stufe(phase: float) -> int:
    q = _FB["phasen"]
    return int(round((phase % 1.0) * q)) % q


def _merken(schluessel, bauen):
    hit = _GEDREHT.get(schluessel)
    if hit is not None:
        _GEDREHT.move_to_end(schluessel)
        return hit
    hit = bauen()
    _GEDREHT[schluessel] = hit
    while len(_GEDREHT) > _FB["gedreht_speicher"]:
        _GEDREHT.popitem(last=False)
    return hit


def _raster(winkel: float) -> int:
    schritt = 3                        # wie Bilder.DREH_SCHRITT
    return int(round(winkel / schritt)) * schritt % 360


def wanne_bild(bilder, art_name: str, winkel: float, ph_links: float,
               ph_rechts: float, unscharf: bool = False) -> pygame.Surface:
    """Die gedrehte Wanne mit laufender Kette oder laufenden Reifen.

    Liegt `assets/<art>.png` da, gilt die Datei - dann steht die Kette."""
    bilder.bild(art_name)
    if art_name in bilder.aus_datei:
        return bilder.gedreht(art_name, winkel)
    if art_name == "panzer":
        schluessel = (art_name, _stufe(ph_links), _stufe(ph_rechts), False)
    else:
        # Der Panzerwagen hat keine Kette: alle Reifen laufen gleich, und
        # verwischt gibt es keine Phase mehr.
        st = 0 if unscharf else _stufe(ph_links)
        schluessel = (art_name, st, st, bool(unscharf))
    if schluessel == (art_name, 0, 0, False):
        return bilder.gedreht(art_name, winkel)
    roh = _WANNEN.get(schluessel)
    if roh is None:
        q = float(_FB["phasen"])
        if art_name == "panzer":
            roh = panzer_wanne(schluessel[1] / q, schluessel[2] / q)
        else:
            roh = panzerwagen_wanne(schluessel[1] / q, schluessel[2] / q, unscharf)
        _WANNEN[schluessel] = roh
    k = _raster(winkel)
    return _merken(schluessel + (k,), lambda: pygame.transform.rotate(roh, -k))


# Wer im Aufbau sitzt: Name des Bildes -> Farben.
def _fahrer_zu(name: str):
    if "_skin_" in name:
        from . import art_figuren
        return art_figuren.fahrer_aus_name(name)
    if name.endswith("_fahrer"):
        for kombi in K.TEAMS["kombi"]:
            if "_%s_fahrer" % kombi["name"].lower() in name:
                return _kombi_fahrer(kombi)
        return _NEUTRAL
    return None


def aufbau_bild(bilder, name: str, winkel: float, rueckstoss: float) -> pygame.Surface:
    """Turm oder MG-Ring, gedreht, mit Rohr- bzw. Laufruecklauf in halben
    Pixeln. Ohne Ruecklauf (und bei einer Datei) wie jedes andere Bild."""
    rk = round(max(0.0, rueckstoss) * 2) / 2
    bilder.bild(name)
    if rk <= 0.0 or name in bilder.aus_datei:
        return bilder.gedreht(name, winkel)
    k = _raster(winkel)

    def bauen():
        zeichner = panzer_turm if name.startswith("panzer_turm") else panzerwagen_ring
        roh = _WANNEN.get((name, rk))
        if roh is None:
            roh = zeichner(_fahrer_zu(name), rk)
            _WANNEN[(name, rk)] = roh
        return pygame.transform.rotate(roh, -k)
    return _merken((name, rk, k), bauen)
