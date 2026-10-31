"""
DUSTFRONT - Die Waffen aus dem Waffenpaket, gezeichnet (seit 0.34.61)
====================================================================

58 Eintraege, in sechs Runden mit dem Besitzer abgestimmt (Paket
`dustfront_waffen`). Hier steht, wie sie aussehen - in der Hand (Draufsicht,
ab der Hand bei x = c + 6 nach rechts, wie art._hand_waffe) und als Zeichen
in der Hotbar (26 x 11, Seitenansicht, wie art._waffe_*). Was davon schon
spielbar ist, steht in K.WAFFEN; alle anderen haben bisher nur ihr Bild.

Die Zeichnungen sind die aus dem Paket (`code/zeichnungen/entwurf.py`), mit
den Ueberarbeitungen aus `entwurf_neu.py` - wo es fuer eine Waffe beides
gibt, gilt die neue Fassung, und sie steht hier weiter unten und
ueberschreibt die alte. GRUND fuer die Uebernahme fast Zeile fuer Zeile:
jede Zeichnung ist Pixel fuer Pixel abgenommen. tests/test_spiel.py
vergleicht nicht mit dem Paket, aber jede Aenderung hier ist eine
Aenderung an einem abgenommenen Bild.

Registriert wird:

    H[id](s, c)      die Waffe an der Hand (art.HAND_ZEICHNER)
    SY[id]()         das Hotbar-Zeichen -> Bild "waffe_<id>"
    T[name]()        Teile, die fliegen oder liegen -> Bild "teil_<name>"
"""

from __future__ import annotations

import pygame

from . import art
from . import config as K
from .core import platzhalter

D = pygame.draw
F = art._flaeche
RAND = art._rand

STAHL, STAHL_H = (92, 82, 64), (146, 132, 104)
DUNKEL, SCHWARZ = (56, 52, 44), (30, 28, 24)
HOLZ, HOLZ_H = art._W_HOLZ, art._W_HOLZ_H
WST, WST_H = art._W_ST, art._W_ST_H
KUNST, KUNST_H = (64, 60, 52), (104, 98, 84)
OLIV, OLIV_H, OLIV_DK = (74, 80, 58), (112, 120, 86), (48, 52, 38)
KER, KER_H, KER_DK = (176, 186, 180), (222, 230, 224), (84, 94, 92)
TEAL, TEAL_H, TEAL_DK = K.C_TEAL, (170, 250, 236), K.C_TEAL_DK
ROST, ROST_H = K.C_RUST, (188, 82, 44)
HULL, HULL_DK, HULL_SH = K.C_HULL, K.C_HULL_DK, K.C_HULL_SH
GELB, WARN = (214, 170, 52), (36, 30, 22)
MESSING, MESSING_DK = (206, 168, 82), (146, 112, 46)
GOLD, GOLD_H, GOLD_DK = (222, 176, 64), (255, 228, 140), (150, 108, 30)
ORANGE, AMBER, ROT, CREAM = K.C_ORANGE, K.C_AMBER, K.C_RED, K.C_CREAM
KLINGE, KLINGE_H = (176, 180, 182), (226, 230, 232)


def r(s, f, x, y, w, h):
    D.rect(s, f, (x, y, w, h))


def lauf(s, f, fh, x, y, w, h):
    """Ein Teil mit hellem Grat oben, wie alles in art.py."""
    r(s, f, x, y, w, h)
    r(s, fh, x, y, w, 1)


CHROM, CHROM_H, CHROM_DK = (168, 172, 174), (222, 226, 228), (96, 100, 102)
SAND, SAND_H, SAND_DK = (150, 132, 90), (186, 166, 118), (102, 88, 58)
KARBON, KARBON_H = (40, 42, 44), (78, 82, 84)

# ══════════════════════════════════════ In der Hand (Draufsicht)
# Alle beginnen bei hand = c + 6 und bleiben innerhalb von 56 Pixeln.

H = {}


def hand(name):
    def reg(f):
        H[name] = f
        return f
    return reg


def gewehr(s, c, laenge, dicke, schaft, s_dicke, sf, sfh, f=STAHL, fh=STAHL_H):
    h = c + 6
    lauf(s, sf, sfh, h - schaft, c - s_dicke // 2, schaft + 3, s_dicke)
    lauf(s, f, fh, h, c - dicke // 2, laenge, dicke)


@hand("revolver")
def _(s, c):
    h = c + 6
    lauf(s, HOLZ, HOLZ_H, h - 4, c - 2, 6, 4)
    lauf(s, DUNKEL, STAHL_H, h + 1, c - 3, 5, 6)          # Trommel, breiter als der Lauf
    r(s, SCHWARZ, h + 2, c - 1, 1, 1)
    r(s, SCHWARZ, h + 4, c + 1, 1, 1)
    lauf(s, STAHL, STAHL_H, h + 6, c - 1, 7, 3)


@hand("zwillinge")
def _(s, c):
    h = c + 6
    for y in (c - 3, c + 3):                               # je Hand eine
        lauf(s, DUNKEL, STAHL_H, h + 1, y - 1, 9, 3)
        r(s, SCHWARZ, h + 9, y - 1, 1, 3)


@hand("mp")
def _(s, c):
    h = c + 6
    r(s, STAHL, h - 8, c - 3, 7, 1)                        # Drahtschaft
    r(s, STAHL, h - 8, c + 2, 7, 1)
    lauf(s, DUNKEL, STAHL_H, h - 2, c - 2, 9, 5)
    lauf(s, STAHL, STAHL_H, h + 7, c - 1, 6, 2)
    r(s, (60, 52, 40), h + 2, c + 3, 3, 6)                # langes Magazin
    r(s, AMBER, h + 2, c + 8, 3, 1)


@hand("bolzer")
def _(s, c):
    h = c + 6
    D.line(s, SCHWARZ, (h - 1, c + 3), (h - 5, c + 6))    # Luftschlauch
    D.line(s, SCHWARZ, (h - 5, c + 6), (h - 9, c + 5))
    lauf(s, HULL_DK, HULL, h - 1, c - 3, 8, 6)
    r(s, GELB, h + 2, c - 3, 1, 6)
    r(s, WARN, h + 3, c - 3, 1, 6)
    lauf(s, ROST, ROST_H, h + 7, c - 4, 2, 8)              # Andruckplatte
    r(s, STAHL_H, h + 9, c - 1, 2, 2)                      # Bolzenspitze


@hand("praezision")
def _(s, c):
    h = c + 6
    gewehr(s, c, 19, 3, 9, 4, KUNST, KUNST_H)
    r(s, (60, 52, 40), h - 2, c + 2, 4, 3)
    lauf(s, (52, 46, 38), (120, 110, 92), h - 1, c - 4, 8, 3)  # kurzes Zielfernrohr
    r(s, TEAL, h + 6, c - 3, 1, 1)
    r(s, SCHWARZ, h + 17, c - 2, 2, 4)


@hand("unterhebel")
def _(s, c):
    h = c + 6
    gewehr(s, c, 16, 3, 9, 4, HOLZ, HOLZ_H)
    r(s, MESSING_DK, h + 2, c + 2, 11, 1)                  # Roehrenmagazin
    lauf(s, HOLZ, HOLZ_H, h + 3, c - 2, 6, 5)              # Vorderschaft
    D.rect(s, STAHL_H, (h - 3, c + 2, 4, 4), 1)            # Hebel als Schlaufe


@hand("nagler")
def _(s, c):
    h = c + 6
    lauf(s, HULL_DK, HULL, h - 2, c - 3, 10, 6)
    for i in range(3):
        r(s, GELB if i % 2 == 0 else WARN, h + 5 + i, c - 3, 1, 6)
    lauf(s, STAHL, STAHL_H, h + 8, c - 1, 5, 3)
    for i in range(4):                                     # Naegelstreifen schraeg
        r(s, MESSING, h + i * 2, c + 3 + i, 1, 2)


@hand("doppelflinte")
def _(s, c):
    h = c + 6
    lauf(s, HOLZ, HOLZ_H, h - 9, c - 3, 12, 6)
    lauf(s, STAHL, STAHL_H, h, c - 3, 12, 2)               # zwei Laeufe nebeneinander
    lauf(s, STAHL, STAHL_H, h, c + 1, 12, 2)
    r(s, SCHWARZ, h, c - 1, 12, 2)
    r(s, STAHL_H, h - 1, c - 4, 1, 1)                      # Haehne
    r(s, STAHL_H, h - 1, c + 3, 1, 1)


@hand("autoschrot")
def _(s, c):
    h = c + 6
    gewehr(s, c, 13, 4, 8, 5, KUNST, KUNST_H)
    D.circle(s, (44, 40, 34), (h + 2, c + 4), 4)           # Trommel
    D.circle(s, (78, 72, 60), (h + 2, c + 4), 2)
    r(s, AMBER, h + 1, c + 7, 3, 1)
    r(s, SCHWARZ, h + 12, c - 2, 2, 4)


@hand("panzerbuechse")
def _(s, c):
    h = c + 6
    lauf(s, OLIV_DK, OLIV, h - 10, c - 2, 13, 5)
    lauf(s, OLIV, OLIV_H, h, c - 2, 8, 5)
    r(s, ORANGE, h + 5, c - 2, 1, 5)
    lauf(s, STAHL, STAHL_H, h + 8, c - 1, 12, 3)
    r(s, SCHWARZ, h + 18, c - 3, 3, 7)                     # Muendungsbremse
    r(s, DUNKEL, h + 19, c - 3, 1, 7)
    r(s, ROT, h + 6, c + 3, 2, 1)                          # Ziellaser


@hand("minigun")
def _(s, c):
    h = c + 6
    for i in range(3):                                     # Gurt
        r(s, MESSING, h - 1 - i * 2, c + 5 + i, 2, 2)
    lauf(s, DUNKEL, STAHL_H, h - 4, c - 4, 9, 9)           # Motor
    r(s, STAHL, h - 3, c - 2, 7, 5)
    r(s, SCHWARZ, h + 1, c - 6, 4, 2)                      # Griff
    lauf(s, STAHL, STAHL_H, h + 5, c - 3, 13, 6)           # Laufbuendel
    r(s, SCHWARZ, h + 5, c - 1, 13, 1)
    r(s, SCHWARZ, h + 5, c + 1, 13, 1)
    r(s, DUNKEL, h + 9, c - 4, 2, 8)
    r(s, DUNKEL, h + 16, c - 4, 2, 8)


@hand("granatwerfer")
def _(s, c):
    h = c + 6
    lauf(s, OLIV_DK, OLIV, h - 8, c - 2, 10, 4)
    lauf(s, OLIV_DK, OLIV_H, h, c - 4, 7, 9)               # Trommel
    r(s, OLIV, h + 1, c - 3, 5, 7)
    r(s, OLIV_DK, h + 1, c - 1, 5, 1)
    r(s, OLIV_DK, h + 1, c + 2, 5, 1)
    lauf(s, STAHL, STAHL_H, h + 7, c - 3, 8, 6)            # dicker kurzer Lauf
    r(s, AMBER, h + 7, c - 3, 1, 6)
    r(s, SCHWARZ, h + 14, c - 2, 1, 4)


@hand("moerser")
def _(s, c):
    h = c + 6
    r(s, DUNKEL, h - 7, c - 5, 5, 10)                      # Bodenplatte hinten
    lauf(s, OLIV_DK, OLIV_H, h - 2, c - 3, 16, 6)
    r(s, OLIV, h - 1, c - 2, 14, 3)
    r(s, ORANGE, h + 9, c - 3, 1, 6)
    r(s, SCHWARZ, h + 3, c + 3, 8, 1)                      # Zweibein, eingeklappt
    r(s, SCHWARZ, h + 13, c - 2, 1, 4)


@hand("einwegwerfer")
def _(s, c):
    h = c + 6
    lauf(s, OLIV_DK, OLIV_H, h - 6, c - 3, 26, 6)
    r(s, OLIV, h - 5, c - 2, 24, 3)
    r(s, SCHWARZ, h - 6, c - 3, 1, 6)                      # Kappen hinten und vorn
    r(s, SCHWARZ, h + 19, c - 3, 1, 6)
    r(s, GELB, h + 15, c - 3, 2, 6)
    r(s, STAHL_H, h + 2, c - 5, 2, 2)                      # Klappvisier


@hand("raketenbuendel")
def _(s, c):
    h = c + 6
    for i, y in enumerate((c - 4, c - 1, c + 2)):
        f, fh = (ROST, ROST_H) if i % 2 else (HULL_DK, HULL)
        lauf(s, f, fh, h - 2, y, 15, 3)
        r(s, (214, 96, 56), h + 12, y + 1, 2, 1)           # Spitzen
    r(s, STAHL_H, h + 3, c - 4, 1, 9)                      # Schweissbaender
    r(s, STAHL_H, h + 9, c - 4, 1, 9)
    r(s, SCHWARZ, h - 2, c - 4, 1, 9)


@hand("spule")
def _(s, c):
    h = c + 6
    lauf(s, KER_DK, KER_H, h - 6, c - 3, 10, 6)
    r(s, KER, h - 5, c - 2, 8, 4)
    r(s, TEAL, h - 3, c - 1, 4, 1)
    lauf(s, KER_DK, KER, h + 4, c - 2, 17, 4)
    r(s, (40, 48, 46), h + 4, c - 1, 17, 2)
    for x in range(h + 5, h + 20, 3):
        r(s, TEAL, x, c - 2, 1, 4)
    r(s, KER_H, h + 20, c - 2, 1, 4)


@hand("kettenblitz")
def _(s, c):
    h = c + 6
    lauf(s, KER_DK, KER_H, h - 2, c - 3, 9, 6)
    r(s, KER, h - 1, c - 2, 7, 4)
    D.circle(s, TEAL_DK, (h + 8, c), 3)
    D.circle(s, TEAL, (h + 8, c), 2)
    r(s, TEAL_H, h + 7, c - 1, 1, 1)
    r(s, KER_H, h + 10, c - 3, 5, 1)                       # zwei Zinken
    r(s, KER_H, h + 10, c + 2, 5, 1)
    r(s, TEAL_H, h + 13, c - 1, 1, 1)
    r(s, TEAL, h + 14, c, 1, 1)


@hand("spiegellaser")
def _(s, c):
    h = c + 6
    lauf(s, KER_DK, KER_H, h - 2, c - 2, 14, 4)
    r(s, KER, h - 1, c - 1, 12, 2)
    D.polygon(s, TEAL_DK, [(h + 12, c), (h + 15, c - 3), (h + 18, c), (h + 15, c + 3)])
    D.polygon(s, TEAL, [(h + 13, c), (h + 15, c - 2), (h + 17, c), (h + 15, c + 2)])
    r(s, TEAL_H, h + 15, c - 1, 1, 1)


@hand("kugelblitz")
def _(s, c):
    h = c + 6
    lauf(s, KER_DK, KER_H, h - 3, c - 3, 9, 6)
    r(s, KER, h - 2, c - 2, 7, 4)
    r(s, KER_DK, h + 6, c - 1, 2, 3)
    D.circle(s, TEAL_DK, (h + 12, c), 5)
    D.circle(s, TEAL, (h + 12, c), 4)
    D.circle(s, TEAL_H, (h + 11, c - 1), 2)
    D.circle(s, KER_DK, (h + 12, c), 5, 1)


@hand("flammenwerfer")
def _(s, c):
    h = c + 6
    D.line(s, SCHWARZ, (h - 3, c + 2), (h - 6, c + 6), 2)  # Schlauch zum Tank
    D.line(s, SCHWARZ, (h - 6, c + 6), (h - 11, c + 7), 2)
    lauf(s, OLIV_DK, OLIV_H, h - 3, c - 2, 8, 5)
    r(s, OLIV, h - 2, c - 1, 6, 3)
    lauf(s, STAHL, STAHL_H, h + 5, c - 1, 10, 3)
    r(s, ORANGE, h + 9, c - 1, 1, 3)
    r(s, DUNKEL, h + 15, c - 2, 3, 5)                      # Duese
    r(s, (236, 150, 44), h + 18, c, 1, 1)                  # Zuendflamme
    r(s, (252, 214, 120), h + 18, c - 1, 1, 1)


def druckluft(s, c, chor=False):
    h = c + 6
    koerper, koerper_h = (KER_DK, KER_H) if chor else (HULL_DK, HULL)
    tank, tank_h = (KER_DK, TEAL) if chor else (ROST, ROST_H)
    lauf(s, koerper, koerper_h, h - 3, c - 3, 9, 6)
    lauf(s, tank, tank_h, h - 1, c + 3, 8, 3)
    r(s, TEAL_H if chor else CREAM, h + 3, c + 4, 1, 1)
    lauf(s, KER if chor else STAHL, KER_H if chor else STAHL_H, h + 6, c - 2, 5, 4)
    D.polygon(s, KER if chor else STAHL, [(h + 11, c - 2), (h + 17, c - 5), (h + 17, c + 5), (h + 11, c + 2)])
    D.polygon(s, TEAL_DK if chor else SCHWARZ, [(h + 12, c - 1), (h + 16, c - 3), (h + 16, c + 3), (h + 12, c + 1)])
    if chor:
        r(s, TEAL, h + 14, c - 2, 1, 5)
    r(s, TEAL if chor else GELB, h + 4, c - 3, 1, 6)


hand("druckluft")(lambda s, c: druckluft(s, c))
hand("chorstimme")(lambda s, c: druckluft(s, c, chor=True))


def wurfkoerper(s, c, name):
    h = c + 6
    x = h + 4
    if name == "gas":
        lauf(s, OLIV_DK, OLIV_H, h + 1, c - 4, 7, 9)
        r(s, OLIV, h + 2, c - 3, 5, 7)
        r(s, (150, 200, 60), h + 1, c, 7, 2)
        r(s, SCHWARZ, h + 3, c - 7, 3, 3)
        r(s, AMBER, h + 4, c - 6, 1, 1)
    elif name == "kuller":
        D.circle(s, DUNKEL, (x, c), 5)
        D.circle(s, (84, 78, 66), (x - 1, c - 1), 3)
        r(s, GELB, x - 5, c - 1, 11, 2)
        r(s, WARN, x - 2, c - 1, 1, 2)
        r(s, WARN, x + 2, c - 1, 1, 2)
        r(s, ROT, x, c - 4, 1, 1)
    elif name == "haftladung":
        D.circle(s, (126, 168, 80), (x, c), 5)
        D.circle(s, (40, 44, 40), (x, c), 4)
        D.circle(s, (70, 76, 68), (x - 1, c - 1), 2)
        r(s, ROT, x, c, 1, 1)
    elif name == "emp":
        D.circle(s, KER_DK, (x, c), 5)
        D.circle(s, KER, (x, c), 4)
        D.circle(s, TEAL, (x, c), 2)
        r(s, TEAL_H, x, c - 1, 1, 1)
        for dx, dy in ((0, -4), (0, 3), (-4, 0), (3, 0)):
            r(s, KER_DK, x + dx, c + dy, 1, 1)
    elif name == "knaller":
        for y in (c - 3, c, c + 3):
            lauf(s, (150, 40, 30), (210, 70, 50), h + 1, y - 1, 8, 2)
        r(s, CREAM, h + 4, c - 4, 1, 8)
        D.line(s, SCHWARZ, (h + 9, c), (h + 11, c - 2))
        r(s, AMBER, h + 11, c - 3, 1, 1)
    elif name == "wurfmesser":
        r(s, SCHWARZ, h, c - 1, 4, 2)
        r(s, STAHL, h + 4, c - 2, 1, 4)
        D.polygon(s, KLINGE, [(h + 5, c - 1), (h + 12, c - 1), (h + 14, c), (h + 5, c + 1)])
        r(s, KLINGE_H, h + 5, c - 1, 7, 1)
    elif name == "schneeball":
        D.circle(s, (196, 202, 212), (x, c), 4)
        D.circle(s, (240, 244, 250), (x - 1, c - 1), 3)
    elif name == "versetzer":
        D.polygon(s, KER_DK, [(x - 4, c + 4), (x, c - 5), (x + 4, c + 4)])
        D.polygon(s, KER, [(x - 3, c + 3), (x, c - 3), (x + 3, c + 3)])
        r(s, TEAL, x, c, 1, 2)
        r(s, TEAL_H, x, c, 1, 1)


for _n in ("gas", "kuller", "haftladung", "emp", "knaller", "wurfmesser", "schneeball", "versetzer"):
    hand(_n)(lambda s, c, n=_n: wurfkoerper(s, c, n))


@hand("hammer")
def _(s, c):
    h = c + 6
    lauf(s, HOLZ, HOLZ_H, h - 5, c - 1, 19, 2)
    lauf(s, DUNKEL, STAHL_H, h + 13, c - 4, 5, 9)
    r(s, STAHL, h + 14, c - 3, 3, 7)


@hand("speer")
def _(s, c):
    h = c + 6
    lauf(s, HOLZ, HOLZ_H, h - 8, c - 1, 24, 2)
    r(s, (180, 160, 120), h + 13, c - 1, 2, 2)             # Wicklung
    D.polygon(s, STAHL_H, [(h + 15, c - 2), (h + 21, c), (h + 15, c + 2)])
    r(s, KLINGE_H, h + 16, c - 1, 3, 1)


@hand("kettensaege")
def _(s, c):
    h = c + 6
    lauf(s, DUNKEL, (248, 196, 90), h - 3, c - 4, 9, 8)
    r(s, (198, 150, 52), h - 2, c - 3, 7, 6)
    r(s, SCHWARZ, h - 1, c - 5, 1, 10)                     # Buegelgriff
    lauf(s, STAHL, STAHL_H, h + 6, c - 2, 13, 4)
    for x in range(h + 6, h + 19, 2):
        r(s, SCHWARZ, x, c - 3, 1, 1)
        r(s, SCHWARZ, x + 1, c + 2, 1, 1)
    r(s, STAHL, h + 19, c - 1, 1, 2)


@hand("schockstab")
def _(s, c):
    h = c + 6
    r(s, SCHWARZ, h - 3, c - 1, 6, 3)
    lauf(s, KER_DK, KER, h + 3, c - 1, 12, 3)
    r(s, TEAL, h + 15, c - 2, 2, 1)
    r(s, TEAL, h + 15, c + 1, 2, 1)
    r(s, TEAL_H, h + 16, c, 1, 1)


@hand("schlagring")
def _(s, c):
    h = c + 6
    for y in (c - 5, c + 2):                               # an beiden Faeusten
        r(s, MESSING_DK, h + 3, y, 2, 4)
        r(s, MESSING, h + 3, y, 1, 4)


@hand("sprengfalle")
def _(s, c):
    h = c + 6
    lauf(s, OLIV_DK, OLIV_H, h + 1, c - 4, 8, 8)
    r(s, OLIV, h + 2, c - 3, 6, 6)
    D.circle(s, DUNKEL, (h + 5, c), 2)
    r(s, ROT, h + 5, c, 1, 1)
    D.circle(s, STAHL_H, (h + 9, c + 4), 2, 1)              # Drahtrolle


@hand("kraehenfuss")
def _(s, c):
    h = c + 6
    D.ellipse(s, (96, 82, 56), (h + 1, c - 4, 9, 9))       # Beutel
    D.ellipse(s, (130, 112, 78), (h + 2, c - 3, 6, 6))
    for dx, dy in ((3, -5), (6, -4), (9, -2)):
        r(s, STAHL_H, h + dx, c + dy, 1, 1)


@hand("geschuetz")
def _(s, c):
    h = c + 6
    lauf(s, OLIV_DK, OLIV_H, h + 1, c - 4, 11, 8)          # zusammengeklappt im Kasten
    r(s, OLIV, h + 2, c - 3, 9, 6)
    r(s, ORANGE, h + 2, c, 9, 1)
    r(s, SCHWARZ, h + 4, c - 6, 4, 2)


@hand("kanister")
def _(s, c):
    h = c + 6
    lauf(s, (110, 30, 22), (196, 64, 44), h + 1, c - 5, 9, 10)
    D.line(s, (110, 30, 22), (h + 2, c - 3), (h + 8, c + 3))
    D.line(s, (110, 30, 22), (h + 8, c - 3), (h + 2, c + 3))
    r(s, SCHWARZ, h + 2, c - 7, 4, 2)
    r(s, GELB, h + 7, c - 6, 2, 1)


@hand("sandsack")
def _(s, c):
    h = c + 6
    D.ellipse(s, (98, 84, 56), (h, c - 5, 11, 10))
    D.ellipse(s, (152, 132, 92), (h + 1, c - 4, 9, 8))
    D.ellipse(s, (180, 160, 116), (h + 2, c - 4, 5, 4))
    r(s, (98, 84, 56), h + 9, c - 1, 2, 2)


@hand("stacheldraht")
def _(s, c):
    h = c + 6
    D.circle(s, (88, 88, 84), (h + 5, c), 5, 1)
    D.circle(s, (150, 150, 146), (h + 5, c), 3, 1)
    for dx, dy in ((5, -5), (10, 0), (5, 5), (0, 0)):
        r(s, (196, 196, 190), h + dx, c + dy, 1, 1)


@hand("fernglas")
def _(s, c):
    h = c + 6
    lauf(s, SCHWARZ, DUNKEL, h - 1, c - 4, 7, 3)
    lauf(s, SCHWARZ, DUNKEL, h - 1, c + 1, 7, 3)
    r(s, DUNKEL, h + 1, c - 1, 2, 2)
    r(s, TEAL_DK, h + 5, c - 3, 1, 1)
    r(s, TEAL_DK, h + 5, c + 2, 1, 1)


@hand("spaehdrohne")
def _(s, c):
    h = c + 6
    lauf(s, KER_DK, KER_H, h + 1, c - 4, 8, 8)             # Steuerung
    r(s, (20, 50, 46), h + 2, c - 2, 6, 4)
    r(s, TEAL, h + 3, c - 1, 2, 1)
    r(s, KER_H, h + 9, c - 3, 2, 1)                        # Antenne


@hand("horcher")
def _(s, c):
    h = c + 6
    lauf(s, KER_DK, KER, h, c - 1, 11, 3)                  # Spiess
    D.circle(s, KER_DK, (h + 12, c), 3)
    D.circle(s, TEAL, (h + 12, c), 2)
    r(s, TEAL_H, h + 12, c - 1, 1, 1)


@hand("leuchtfeuer")
def _(s, c):
    h = c + 6
    lauf(s, (170, 70, 30), (246, 146, 70), h, c - 2, 9, 5)
    r(s, (210, 96, 40), h + 1, c - 1, 7, 3)
    r(s, SCHWARZ, h + 8, c - 1, 1, 3)
    r(s, (255, 120, 110), h + 6, c + 3, 3, 1)              # Fackel am Guertel


@hand("enterhaken")
def _(s, c):
    h = c + 6
    D.circle(s, (150, 120, 80), (h + 2, c + 5), 2, 1)       # Seilrolle
    lauf(s, DUNKEL, STAHL_H, h - 1, c - 2, 9, 4)
    for ende in ((h + 12, c - 3), (h + 13, c), (h + 12, c + 3)):
        D.line(s, STAHL_H, (h + 8, c), ende)


@hand("sanitasche")
def _(s, c):
    h = c + 6
    lauf(s, (68, 74, 50), (110, 118, 82), h, c - 5, 10, 10)
    r(s, (88, 96, 64), h + 1, c - 4, 8, 8)
    r(s, (214, 210, 196), h + 3, c - 2, 4, 4)
    r(s, ROT, h + 4, c - 2, 2, 4)
    r(s, ROT, h + 3, c - 1, 4, 2)


@hand("munbeutel")
def _(s, c):
    h = c + 6
    lauf(s, (80, 64, 40), (124, 102, 66), h, c - 4, 9, 8)
    r(s, (96, 80, 48), h + 1, c - 3, 7, 6)
    for y in (c - 3, c - 1, c + 1, c + 3):
        r(s, MESSING, h + 8, y, 2, 1)


@hand("goldene")
def _(s, c):
    h = c + 6
    lauf(s, (96, 70, 40), (140, 104, 60), h - 4, c - 2, 6, 4)
    lauf(s, GOLD_DK, GOLD_H, h + 1, c - 3, 5, 6)
    r(s, GOLD_DK, h + 2, c - 1, 1, 1)
    r(s, GOLD_DK, h + 4, c + 1, 1, 1)
    lauf(s, GOLD, GOLD_H, h + 6, c - 1, 7, 3)


# Aufsaetze sitzen auf dem Sturmgewehr, so wie es heute aussieht.
def aufsatz(name):
    def z(s, c):
        art._hand_waffe(s, c, "sturm")
        h = c + 6
        if name == "auf_daempfer":
            lauf(s, SCHWARZ, DUNKEL, h + 14, c - 2, 7, 4)
        elif name == "auf_fernrohr":
            lauf(s, (52, 46, 38), (120, 110, 92), h - 3, c - 4, 10, 3)
            r(s, AMBER, h + 1, c - 4, 1, 3)
            r(s, TEAL, h + 6, c - 3, 1, 1)
        elif name == "auf_trommel":
            D.circle(s, (44, 40, 34), (h - 1, c + 5), 4)
            D.circle(s, (78, 72, 60), (h - 1, c + 5), 2)
            r(s, AMBER, h - 2, c + 8, 3, 1)
        elif name == "auf_zweibein":
            D.line(s, (40, 38, 32), (h + 10, c - 2), (h + 13, c - 6))
            D.line(s, (40, 38, 32), (h + 10, c + 2), (h + 13, c + 6))
        elif name == "auf_laser":
            r(s, SCHWARZ, h + 6, c + 2, 4, 2)
            r(s, ROT, h + 10, c + 2, 1, 1)
        elif name == "auf_unterlauf":
            lauf(s, DUNKEL, STAHL, h + 3, c + 2, 8, 4)
            r(s, SCHWARZ, h + 10, c + 3, 1, 2)
    return z


for _n in ("auf_daempfer", "auf_fernrohr", "auf_trommel", "auf_zweibein", "auf_laser", "auf_unterlauf"):
    H[_n] = aufsatz(_n)


def fraktions_gewehr(art_):
    def z(s, c):
        h = c + 6
        if art_ == "K":
            lauf(s, OLIV_DK, OLIV, h - 8, c - 2, 11, 5)
            lauf(s, OLIV, OLIV_H, h, c - 2, 8, 5)
            r(s, ORANGE, h + 5, c - 2, 1, 5)
            lauf(s, STAHL, STAHL_H, h + 8, c - 1, 8, 3)
            r(s, SCHWARZ, h + 15, c - 2, 2, 5)
        elif art_ == "C":
            lauf(s, KER_DK, KER_H, h - 8, c - 2, 11, 5)
            lauf(s, KER_DK, KER_H, h, c - 3, 10, 6)
            r(s, KER, h + 1, c - 2, 8, 4)
            r(s, TEAL, h + 2, c, 6, 1)
            lauf(s, KER_DK, KER, h + 10, c - 1, 6, 3)
            r(s, TEAL_H, h + 15, c - 1, 1, 3)
        else:
            lauf(s, ROST, ROST_H, h - 8, c - 2, 11, 5)
            lauf(s, HULL_DK, HULL, h, c - 2, 9, 5)
            r(s, ROST, h + 3, c - 3, 3, 2)                 # aufgeschweisstes Blech
            r(s, GELB, h + 7, c - 2, 1, 5)
            r(s, WARN, h + 8, c - 2, 1, 5)
            lauf(s, STAHL, STAHL_H, h + 9, c - 1, 8, 3)
            r(s, MESSING_DK, h + 2, c + 3, 3, 3)
    return z


for _f in "KCW":
    H["fraktion_" + _f] = fraktions_gewehr(_f)


# ══════════════════════════════════════ Hotbar-Symbole (26 x 11, Seitenansicht)

SY = {}


def symbol(name):
    def reg(f):
        SY[name] = f
        return f
    return reg


def neu():
    return F(26, 11)


@symbol("revolver")
def _():
    s = neu()
    D.polygon(s, HOLZ, [(3, 5), (7, 5), (6, 10), (2, 10)])
    r(s, HOLZ_H, 3, 5, 4, 1)
    lauf(s, WST, WST_H, 6, 3, 4, 4)
    lauf(s, WST, WST_H, 9, 2, 5, 5)
    r(s, (30, 26, 20), 10, 4, 3, 1)
    lauf(s, WST, WST_H, 14, 3, 10, 2)
    r(s, WST, 6, 1, 2, 2)
    D.rect(s, WST, (8, 7, 3, 3), 1)
    return s


@symbol("zwillinge")
def _():
    s = neu()
    for dx, dy, f in ((1, 0, WST), (9, 4, (60, 52, 42))):
        lauf(s, f, WST_H, dx + 3, dy + 1, 11, 3)
        D.polygon(s, f, [(dx + 3, dy + 4), (dx + 7, dy + 4), (dx + 6, dy + 7), (dx + 3, dy + 7)])
    return s


@symbol("mp")
def _():
    s = neu()
    r(s, WST, 1, 4, 5, 1)
    r(s, WST, 1, 6, 5, 1)
    r(s, WST, 1, 4, 1, 3)
    lauf(s, WST, WST_H, 6, 3, 10, 4)
    lauf(s, WST, WST_H, 16, 4, 7, 2)
    r(s, (60, 52, 40), 12, 7, 2, 4)
    r(s, K.C_AMBER, 12, 10, 2, 1)
    r(s, WST, 8, 7, 2, 3)
    return s


@symbol("bolzer")
def _():
    s = neu()
    D.line(s, SCHWARZ, (5, 6), (2, 9))
    D.line(s, SCHWARZ, (2, 9), (1, 7))
    lauf(s, HULL_SH, HULL_DK, 5, 3, 12, 5)
    r(s, GELB, 13, 3, 1, 5)
    r(s, WARN, 14, 3, 1, 5)
    lauf(s, ROST, ROST_H, 17, 2, 2, 7)
    r(s, WST_H, 19, 5, 3, 1)
    r(s, WST, 7, 8, 3, 3)
    return s


@symbol("praezision")
def _():
    s = neu()
    lauf(s, KUNST, KUNST_H, 1, 5, 8, 3)
    r(s, KUNST, 1, 4, 3, 1)
    lauf(s, WST, WST_H, 9, 4, 6, 3)
    lauf(s, WST, WST_H, 15, 5, 10, 2)
    lauf(s, (30, 26, 20), (70, 62, 50), 10, 1, 7, 2)
    r(s, K.C_TEAL_DK, 16, 1, 1, 2)
    r(s, (60, 52, 40), 11, 7, 3, 3)
    r(s, WST, 9, 7, 1, 3)
    return s


@symbol("unterhebel")
def _():
    s = neu()
    lauf(s, HOLZ, HOLZ_H, 1, 5, 8, 4)
    lauf(s, WST, WST_H, 9, 4, 5, 3)
    lauf(s, WST, WST_H, 14, 4, 11, 2)
    r(s, MESSING_DK, 14, 6, 9, 1)
    lauf(s, HOLZ, HOLZ_H, 15, 6, 6, 2)
    D.rect(s, WST, (9, 7, 4, 3), 1)
    return s


@symbol("nagler")
def _():
    s = neu()
    lauf(s, HULL_SH, HULL_DK, 5, 2, 12, 5)
    r(s, GELB, 15, 2, 1, 5)
    r(s, WARN, 16, 2, 1, 5)
    lauf(s, WST, WST_H, 17, 3, 6, 3)
    r(s, WST, 7, 7, 3, 4)
    for i in range(4):
        r(s, MESSING, 11 + i, 7 + i, 1, 1)
    return s


@symbol("doppelflinte")
def _():
    s = neu()
    D.polygon(s, HOLZ, [(1, 6), (9, 5), (9, 8), (1, 10)])
    r(s, HOLZ_H, 1, 6, 8, 1)
    lauf(s, WST, WST_H, 9, 4, 4, 4)
    lauf(s, WST, WST_H, 13, 3, 12, 2)
    lauf(s, WST, WST_H, 13, 5, 12, 2)
    r(s, (18, 16, 12), 24, 3, 1, 4)
    r(s, WST, 10, 2, 1, 2)
    r(s, WST, 12, 2, 1, 2)
    r(s, WST, 10, 8, 2, 2)
    return s


@symbol("autoschrot")
def _():
    s = neu()
    lauf(s, KUNST, KUNST_H, 1, 4, 7, 3)
    lauf(s, WST, WST_H, 8, 3, 9, 4)
    lauf(s, WST, WST_H, 17, 3, 8, 2)
    r(s, (66, 56, 44), 17, 5, 6, 2)
    D.circle(s, (44, 40, 34), (12, 8), 3)
    D.circle(s, (78, 72, 60), (12, 8), 1)
    return s


@symbol("panzerbuechse")
def _():
    s = neu()
    lauf(s, OLIV_DK, OLIV, 0, 4, 7, 4)
    lauf(s, OLIV, OLIV_H, 7, 3, 7, 4)
    r(s, ORANGE, 12, 3, 1, 4)
    lauf(s, WST, WST_H, 14, 4, 9, 2)
    r(s, (24, 22, 18), 22, 3, 3, 4)
    D.line(s, WST, (18, 6), (16, 10))
    D.line(s, WST, (18, 6), (20, 10))
    r(s, ROT, 9, 7, 2, 1)
    r(s, OLIV_DK, 9, 7, 1, 3)
    return s


@symbol("minigun")
def _():
    s = neu()
    lauf(s, (36, 34, 30), (80, 74, 62), 1, 3, 8, 6)
    lauf(s, WST, WST_H, 9, 3, 13, 5)
    r(s, (24, 22, 18), 9, 5, 13, 1)
    r(s, (60, 54, 44), 14, 2, 2, 7)
    r(s, (60, 54, 44), 20, 2, 2, 7)
    r(s, SCHWARZ, 3, 1, 5, 2)
    lauf(s, OLIV_DK, OLIV, 2, 8, 5, 3)
    return s


@symbol("granatwerfer")
def _():
    s = neu()
    lauf(s, OLIV_DK, OLIV, 1, 4, 6, 3)
    lauf(s, OLIV_DK, OLIV_H, 7, 2, 8, 7)
    r(s, OLIV, 8, 3, 6, 5)
    r(s, OLIV_DK, 8, 5, 6, 1)
    lauf(s, WST, WST_H, 15, 3, 9, 4)
    r(s, K.C_AMBER, 15, 3, 1, 4)
    r(s, OLIV_DK, 8, 9, 2, 2)
    return s


@symbol("moerser")
def _():
    s = neu()
    r(s, DUNKEL, 1, 9, 9, 2)
    D.line(s, OLIV_DK, (5, 9), (21, 2), 4)
    D.line(s, OLIV_H, (5, 8), (21, 1), 1)
    r(s, ORANGE, 15, 3, 1, 3)
    D.line(s, SCHWARZ, (16, 4), (13, 10))
    D.line(s, SCHWARZ, (16, 4), (19, 10))
    return s


@symbol("einwegwerfer")
def _():
    s = neu()
    lauf(s, OLIV_DK, OLIV_H, 1, 3, 24, 5)
    r(s, OLIV, 2, 4, 22, 2)
    r(s, SCHWARZ, 1, 3, 1, 5)
    r(s, SCHWARZ, 24, 3, 1, 5)
    r(s, GELB, 19, 3, 2, 5)
    r(s, WST_H, 8, 1, 2, 2)
    r(s, OLIV_DK, 10, 8, 2, 3)
    return s


@symbol("raketenbuendel")
def _():
    s = neu()
    for i, y in enumerate((1, 4, 7)):
        f, fh = (ROST, ROST_H) if i % 2 else (HULL_DK, HULL)
        lauf(s, f, fh, 3, y, 18, 3)
        r(s, (214, 96, 56), 21, y + 1, 2, 1)
    r(s, WST_H, 8, 1, 1, 9)
    r(s, WST_H, 15, 1, 1, 9)
    r(s, SCHWARZ, 3, 1, 1, 9)
    return s


@symbol("spule")
def _():
    s = neu()
    lauf(s, KER_DK, KER_H, 1, 3, 9, 5)
    r(s, TEAL, 3, 5, 4, 1)
    lauf(s, KER_DK, KER, 10, 4, 15, 3)
    for x in range(11, 25, 3):
        r(s, K.C_TEAL, x, 3, 1, 5)
    r(s, KER_DK, 4, 8, 2, 3)
    return s


@symbol("kettenblitz")
def _():
    s = neu()
    lauf(s, KER_DK, KER_H, 2, 3, 10, 5)
    D.circle(s, TEAL_DK, (14, 5), 3)
    D.circle(s, TEAL, (14, 5), 2)
    r(s, KER_H, 17, 3, 6, 1)
    r(s, KER_H, 17, 7, 6, 1)
    r(s, TEAL_H, 21, 5, 1, 1)
    r(s, KER_DK, 5, 8, 2, 3)
    return s


@symbol("spiegellaser")
def _():
    s = neu()
    lauf(s, KER_DK, KER_H, 2, 4, 15, 3)
    r(s, KER_DK, 6, 7, 2, 3)
    D.polygon(s, TEAL_DK, [(17, 5), (20, 2), (23, 5), (20, 8)])
    D.polygon(s, TEAL, [(18, 5), (20, 3), (22, 5), (20, 7)])
    return s


@symbol("kugelblitz")
def _():
    s = neu()
    lauf(s, KER_DK, KER_H, 1, 3, 10, 5)
    r(s, KER_DK, 11, 4, 2, 3)
    D.circle(s, TEAL_DK, (18, 5), 5)
    D.circle(s, TEAL, (18, 5), 4)
    D.circle(s, TEAL_H, (17, 4), 2)
    r(s, KER_DK, 4, 8, 2, 3)
    return s


@symbol("flammenwerfer")
def _():
    s = neu()
    lauf(s, OLIV_DK, OLIV_H, 1, 2, 6, 7)
    r(s, ORANGE, 1, 5, 6, 1)
    D.line(s, SCHWARZ, (4, 9), (10, 7))
    lauf(s, WST, WST_H, 9, 4, 13, 2)
    r(s, (60, 54, 44), 22, 3, 3, 4)
    r(s, OLIV_DK, 10, 6, 2, 3)
    r(s, (236, 150, 44), 25, 5, 1, 1)
    return s


def symbol_druckluft(chor=False):
    s = neu()
    lauf(s, KER_DK if chor else HULL_SH, KER_H if chor else HULL_DK, 4, 3, 9, 5)
    lauf(s, KER_DK if chor else ROST, TEAL if chor else ROST_H, 4, 8, 9, 3)
    lauf(s, KER if chor else WST, KER_H if chor else WST_H, 13, 4, 5, 3)
    D.polygon(s, KER if chor else WST_H, [(18, 4), (24, 1), (24, 9), (18, 7)])
    D.polygon(s, TEAL_DK if chor else SCHWARZ, [(19, 5), (23, 3), (23, 7), (19, 6)])
    r(s, TEAL_H if chor else CREAM, 7, 9, 1, 1)
    return s


symbol("druckluft")(lambda: symbol_druckluft())
symbol("chorstimme")(lambda: symbol_druckluft(True))


@symbol("gas")
def _():
    s = neu()
    lauf(s, OLIV_DK, OLIV_H, 8, 2, 9, 8)
    r(s, (150, 200, 60), 8, 5, 9, 2)
    r(s, SCHWARZ, 11, 0, 3, 2)
    r(s, (92, 80, 60), 14, 1, 4, 1)
    return s


@symbol("kuller")
def _():
    s = neu()
    D.circle(s, DUNKEL, (13, 5), 5)
    D.circle(s, (84, 78, 66), (12, 4), 3)
    r(s, GELB, 8, 5, 11, 2)
    r(s, WARN, 11, 5, 1, 2)
    r(s, WARN, 15, 5, 1, 2)
    r(s, ROT, 13, 1, 1, 1)
    return s


@symbol("haftladung")
def _():
    s = neu()
    D.ellipse(s, (40, 44, 40), (7, 3, 12, 6))
    D.ellipse(s, (70, 76, 68), (9, 3, 7, 3))
    r(s, (126, 168, 80), 7, 8, 12, 1)
    r(s, (126, 168, 80), 9, 9, 2, 1)
    r(s, (126, 168, 80), 15, 9, 1, 2)
    r(s, ROT, 13, 2, 1, 1)
    return s


@symbol("emp")
def _():
    s = neu()
    D.ellipse(s, KER_DK, (7, 2, 12, 7))
    D.ellipse(s, KER, (8, 3, 10, 4))
    r(s, TEAL, 11, 4, 4, 2)
    r(s, KER_DK, 12, 0, 1, 2)
    r(s, TEAL_H, 12, 0, 1, 1)
    return s


@symbol("knaller")
def _():
    s = neu()
    for y in (2, 5, 8):
        lauf(s, (150, 40, 30), (210, 70, 50), 6, y, 12, 2)
    r(s, CREAM, 11, 1, 1, 10)
    D.line(s, SCHWARZ, (18, 5), (22, 2))
    r(s, AMBER, 22, 1, 1, 1)
    return s


@symbol("wurfmesser")
def _():
    s = neu()
    r(s, SCHWARZ, 2, 4, 6, 3)
    r(s, WST, 8, 3, 1, 5)
    D.polygon(s, KLINGE, [(9, 4), (22, 4), (24, 5), (9, 6)])
    r(s, KLINGE_H, 9, 4, 13, 1)
    return s


@symbol("schneeball")
def _():
    s = neu()
    D.circle(s, (196, 202, 212), (13, 5), 4)
    D.circle(s, (240, 244, 250), (12, 4), 3)
    return s


@symbol("hammer")
def _():
    s = neu()
    for x in range(2, 19):
        r(s, HOLZ, x, 8 - (x - 2) * 5 // 16, 1, 2)
    lauf(s, DUNKEL, STAHL_H, 18, 0, 6, 7)
    r(s, STAHL, 19, 1, 4, 5)
    return s


@symbol("speer")
def _():
    s = neu()
    lauf(s, HOLZ, HOLZ_H, 0, 5, 20, 2)
    r(s, (180, 160, 120), 17, 4, 2, 3)
    D.polygon(s, STAHL_H, [(19, 3), (25, 5), (25, 6), (19, 8)])
    return s


@symbol("kettensaege")
def _():
    s = neu()
    lauf(s, (198, 150, 52), (248, 196, 90), 1, 2, 10, 7)
    D.rect(s, SCHWARZ, (3, 0, 6, 3), 1)
    lauf(s, WST, WST_H, 11, 4, 13, 3)
    for x in range(11, 24, 2):
        r(s, SCHWARZ, x, 3, 1, 1)
        r(s, SCHWARZ, x + 1, 7, 1, 1)
    return s


@symbol("schockstab")
def _():
    s = neu()
    r(s, SCHWARZ, 1, 4, 6, 3)
    lauf(s, KER_DK, KER, 7, 4, 13, 3)
    r(s, TEAL, 20, 3, 3, 1)
    r(s, TEAL, 20, 7, 3, 1)
    r(s, TEAL_H, 22, 5, 1, 1)
    return s


@symbol("schlagring")
def _():
    s = neu()
    lauf(s, MESSING_DK, MESSING, 6, 2, 14, 5)
    for x in (8, 11, 14, 17):
        r(s, (60, 44, 20), x, 3, 2, 3)
    r(s, MESSING_DK, 8, 7, 10, 2)
    return s


@symbol("sprengfalle")
def _():
    s = neu()
    D.ellipse(s, OLIV_DK, (3, 4, 14, 6))
    D.ellipse(s, OLIV, (4, 4, 12, 4))
    r(s, DUNKEL, 9, 2, 2, 3)
    r(s, ROT, 9, 2, 2, 1)
    D.circle(s, WST_H, (21, 6), 3, 1)
    D.line(s, WST_H, (17, 7), (19, 7))
    return s


@symbol("kraehenfuss")
def _():
    s = neu()
    for x in (5, 13, 20):
        D.line(s, WST_H, (x - 3, 9), (x, 4))
        D.line(s, WST_H, (x + 3, 9), (x, 4))
        D.line(s, WST, (x, 4), (x, 1))
    return s


@symbol("geschuetz")
def _():
    s = neu()
    lauf(s, WST, WST_H, 6, 2, 17, 3)
    r(s, (24, 22, 18), 22, 1, 2, 5)
    lauf(s, OLIV_DK, OLIV, 8, 4, 5, 3)
    for x in (6, 16):
        D.line(s, WST, (11, 6), (x, 10))
    D.line(s, WST, (11, 6), (11, 10))
    return s


@symbol("kanister")
def _():
    s = neu()
    lauf(s, (110, 30, 22), (196, 64, 44), 7, 2, 12, 9)
    D.line(s, (110, 30, 22), (8, 3), (17, 9))
    D.line(s, (110, 30, 22), (17, 3), (8, 9))
    D.rect(s, SCHWARZ, (8, 0, 5, 3), 1)
    r(s, GELB, 16, 0, 2, 2)
    return s


@symbol("sandsack")
def _():
    s = neu()
    for x, y in ((4, 5), (13, 5), (8, 1)):
        D.ellipse(s, (98, 84, 56), (x, y, 10, 6))
        D.ellipse(s, (152, 132, 92), (x + 1, y + 1, 8, 4))
    return s


@symbol("stacheldraht")
def _():
    s = neu()
    r(s, HOLZ, 1, 2, 2, 9)
    r(s, HOLZ, 23, 2, 2, 9)
    for x in range(3, 23, 4):
        D.ellipse(s, (150, 150, 146), (x, 2, 6, 8), 1)
    for x in range(4, 23, 3):
        r(s, (210, 210, 204), x, 6, 1, 1)
    return s


@symbol("fernglas")
def _():
    s = neu()
    lauf(s, SCHWARZ, DUNKEL, 6, 2, 13, 3)
    lauf(s, SCHWARZ, DUNKEL, 6, 6, 13, 3)
    r(s, (60, 54, 46), 10, 5, 4, 1)
    r(s, TEAL_DK, 19, 2, 1, 3)
    r(s, TEAL_DK, 19, 6, 1, 3)
    return s


@symbol("spaehdrohne")
def _():
    s = neu()
    lauf(s, KER_DK, KER_H, 9, 4, 8, 3)
    r(s, TEAL, 15, 5, 1, 1)
    D.line(s, KER_DK, (9, 5), (6, 3))
    D.line(s, KER_DK, (17, 5), (20, 3))
    r(s, SCHWARZ, 3, 2, 7, 1)
    r(s, SCHWARZ, 17, 2, 7, 1)
    r(s, KER_DK, 11, 7, 1, 2)
    r(s, KER_DK, 15, 7, 1, 2)
    return s


@symbol("horcher")
def _():
    s = neu()
    r(s, KER_DK, 12, 3, 2, 7)
    D.line(s, KER_DK, (12, 9), (8, 10))
    D.line(s, KER_DK, (13, 9), (17, 10))
    D.polygon(s, KER, [(8, 1), (18, 1), (16, 4), (10, 4)])
    r(s, TEAL, 12, 2, 2, 1)
    return s


@symbol("leuchtfeuer")
def _():
    s = neu()
    lauf(s, (170, 70, 30), (246, 146, 70), 9, 3, 14, 4)
    r(s, SCHWARZ, 22, 4, 1, 2)
    D.polygon(s, (150, 60, 28), [(8, 5), (12, 5), (11, 10), (7, 10)])
    lauf(s, (180, 40, 36), (255, 120, 110), 1, 8, 6, 2)
    return s


@symbol("enterhaken")
def _():
    s = neu()
    lauf(s, WST, WST_H, 3, 4, 12, 4)
    r(s, WST, 6, 8, 2, 3)
    D.circle(s, (150, 120, 80), (4, 2), 2, 1)
    for y in (1, 5, 9):
        D.line(s, STAHL_H, (16, 5), (22, y))
    r(s, STAHL_H, 15, 5, 2, 1)
    return s


@symbol("versetzer")
def _():
    s = neu()
    D.polygon(s, KER_DK, [(8, 10), (13, 0), (18, 10)])
    D.polygon(s, KER, [(9, 9), (13, 2), (17, 9)])
    r(s, TEAL, 12, 6, 2, 2)
    r(s, TEAL_H, 12, 6, 1, 1)
    return s


@symbol("sanitasche")
def _():
    s = neu()
    lauf(s, (68, 74, 50), (110, 118, 82), 6, 2, 14, 9)
    r(s, (214, 210, 196), 10, 4, 6, 5)
    r(s, ROT, 12, 4, 2, 5)
    r(s, ROT, 10, 6, 6, 1)
    D.line(s, (52, 56, 40), (6, 3), (3, 0))
    return s


@symbol("munbeutel")
def _():
    s = neu()
    lauf(s, (80, 64, 40), (124, 102, 66), 7, 4, 12, 7)
    for x in (9, 12, 15):
        r(s, MESSING, x, 1, 2, 3)
        r(s, (120, 74, 28), x, 1, 2, 1)
    return s


@symbol("goldene")
def _():
    s = neu()
    D.polygon(s, (96, 70, 40), [(3, 5), (7, 5), (6, 10), (2, 10)])
    lauf(s, GOLD_DK, GOLD, 6, 3, 4, 4)
    lauf(s, GOLD_DK, GOLD_H, 9, 2, 5, 5)
    lauf(s, GOLD, GOLD_H, 14, 3, 10, 2)
    r(s, GOLD_DK, 6, 1, 2, 2)
    D.rect(s, GOLD_DK, (8, 7, 3, 3), 1)
    return s


def symbol_aufsatz(name):
    s = art._waffe_sturm()
    if name == "auf_daempfer":
        lauf(s, SCHWARZ, (70, 64, 52), 20, 3, 6, 4)
    elif name == "auf_fernrohr":
        lauf(s, (30, 26, 20), (70, 62, 50), 8, 0, 9, 3)
        r(s, AMBER, 11, 0, 1, 3)
        r(s, K.C_TEAL_DK, 16, 1, 1, 1)
    elif name == "auf_trommel":
        r(s, (0, 0, 0, 0), 10, 8, 4, 3)
        D.circle(s, (44, 40, 34), (12, 8), 3)
        D.circle(s, (78, 72, 60), (12, 8), 1)
    elif name == "auf_zweibein":
        D.line(s, WST, (21, 6), (19, 10))
        D.line(s, WST, (21, 6), (24, 10))
    elif name == "auf_laser":
        r(s, SCHWARZ, 17, 6, 4, 2)
        r(s, ROT, 21, 6, 1, 1)
    elif name == "auf_unterlauf":
        lauf(s, (36, 34, 30), (80, 74, 62), 16, 6, 8, 3)
        r(s, SCHWARZ, 23, 7, 1, 1)
    return s


for _n in ("auf_daempfer", "auf_fernrohr", "auf_trommel", "auf_zweibein", "auf_laser", "auf_unterlauf"):
    SY[_n] = (lambda n=_n: symbol_aufsatz(n))


def symbol_patrone(spitze, hohl=False):
    s = neu()
    lauf(s, MESSING_DK, MESSING, 4, 3, 12, 5)              # Huelse
    r(s, MESSING_DK, 3, 3, 1, 5)
    D.polygon(s, spitze, [(16, 3), (21, 4), (23, 5), (23, 6), (21, 7), (16, 7)])
    r(s, tuple(min(255, k + 50) for k in spitze), 16, 3, 5, 1)
    if hohl:
        r(s, (40, 24, 10), 22, 5, 1, 1)
    return s


SY["mun_panzer"] = lambda: symbol_patrone((34, 34, 36))
SY["mun_brand"] = lambda: symbol_patrone((196, 52, 36))
SY["mun_hohl"] = lambda: symbol_patrone((150, 96, 44), hohl=True)
SY["mun_leucht"] = lambda: symbol_patrone((190, 220, 80))
SY["mun_unterschall"] = lambda: symbol_patrone((96, 92, 168))


@symbol("hecknebel")
def _():
    s = neu()
    for x in (4, 10):
        lauf(s, (72, 76, 72), (132, 138, 132), x, 3, 5, 7)
        r(s, SCHWARZ, x + 1, 1, 3, 2)
    for x in (17, 20, 23):
        r(s, (168, 166, 160), x, 3 + x % 3, 1, 2)
    return s


@symbol("nagelstreuer")
def _():
    s = neu()
    D.polygon(s, ROST, [(4, 1), (18, 1), (15, 7), (7, 7)])
    r(s, ROST_H, 4, 1, 14, 1)
    r(s, SCHWARZ, 9, 7, 4, 2)
    for x in (8, 12, 16, 20):
        r(s, WST_H, x, 10, 1, 1)
    return s


@symbol("kartenwaffen")
def _():
    s = neu()
    lauf(s, (44, 48, 40), (72, 78, 64), 2, 4, 22, 7)
    for x in range(4, 23, 4):
        r(s, AMBER, x, 7, 2, 1)
    lauf(s, WST, WST_H, 6, 1, 13, 3)
    r(s, AMBER, 21, 1, 2, 2)
    return s


SY["fraktion_K"] = lambda: symbol_fraktion("K")
SY["fraktion_C"] = lambda: symbol_fraktion("C")
SY["fraktion_W"] = lambda: symbol_fraktion("W")


def symbol_fraktion(a):
    s = neu()
    if a == "K":
        lauf(s, OLIV_DK, OLIV, 1, 4, 7, 3)
        lauf(s, OLIV, OLIV_H, 8, 3, 9, 4)
        r(s, ORANGE, 14, 3, 1, 4)
        lauf(s, WST, WST_H, 17, 4, 8, 2)
        r(s, OLIV_DK, 10, 7, 3, 3)
    elif a == "C":
        lauf(s, KER_DK, KER_H, 1, 4, 7, 3)
        lauf(s, KER_DK, KER_H, 8, 2, 11, 6)
        r(s, TEAL, 10, 4, 7, 1)
        lauf(s, KER_DK, KER, 19, 4, 6, 2)
        r(s, KER_DK, 11, 8, 2, 3)
    else:
        lauf(s, ROST, ROST_H, 1, 4, 7, 3)
        lauf(s, HULL_DK, HULL, 8, 3, 10, 4)
        r(s, ROST, 10, 2, 3, 2)
        r(s, GELB, 16, 3, 1, 4)
        r(s, WARN, 17, 3, 1, 4)
        lauf(s, WST, WST_H, 18, 4, 7, 2)
        r(s, MESSING_DK, 11, 7, 3, 3)
    return s


# ══════════════════════════════════════ Teile, die fliegen oder liegen

T = {}


def teil(name):
    def reg(f):
        T[name] = f
        return f
    return reg


@teil("minirakete")
def _():
    s = F(9, 5)
    r(s, HULL_DK, 2, 1, 5, 3)
    r(s, HULL, 2, 1, 5, 1)
    D.polygon(s, (170, 70, 44), [(7, 1), (9, 2), (7, 3)])
    r(s, (252, 208, 120), 0, 2, 2, 1)
    return s


# ══════════════════════════════════════ Ueberarbeitungen (Runden 4 bis 6)
# Aus entwurf_neu.py. Sie ersetzen die Eintraege oben mit demselben Namen.

# ── Bolzenschussgeraet: blanker Viehschussapparat statt Werften-Zylinder ──
@hand("bolzer")
def _(s, c):
    h = c + 6
    lauf(s, CHROM_DK, CHROM_H, h - 3, c - 2, 14, 5)         # blanker Zylinder
    r(s, CHROM, h - 2, c - 1, 12, 3)
    for x in (h - 3, h - 1, h + 1):                          # geriffelter Griff
        r(s, CHROM_DK, x, c - 2, 1, 5)
    r(s, MESSING, h + 4, c - 2, 1, 5)                        # Ausloeserring
    lauf(s, SCHWARZ, DUNKEL, h + 11, c - 3, 2, 7)            # breite Kappe vorn
    r(s, CHROM_H, h + 13, c - 1, 1, 2)                       # Bolzenspitze


@symbol("bolzer")
def _():
    s = neu()
    lauf(s, CHROM_DK, CHROM_H, 3, 3, 15, 4)
    r(s, CHROM, 4, 4, 13, 2)
    for x in (4, 6, 8):
        r(s, CHROM_DK, x, 3, 1, 4)
    r(s, MESSING, 12, 3, 1, 4)
    lauf(s, SCHWARZ, DUNKEL, 18, 2, 2, 6)
    r(s, CHROM_H, 20, 4, 2, 2)
    D.polygon(s, SCHWARZ, [(7, 7), (10, 7), (9, 10), (6, 10)])  # Griff
    return s


# ── Einweg-Raketenwerfer: zweiteiliges Teleskoprohr ──
@hand("einwegwerfer")
def _(s, c):
    h = c + 6
    D.polygon(s, OLIV_DK, [(h - 9, c - 4), (h - 5, c - 3), (h - 5, c + 3), (h - 9, c + 4)])  # Trichter hinten
    r(s, SCHWARZ, h - 9, c - 2, 1, 5)
    lauf(s, OLIV_DK, OLIV, h - 5, c - 2, 12, 5)              # hinteres, duenneres Rohr
    lauf(s, OLIV_DK, OLIV_H, h + 7, c - 3, 13, 6)            # vorderes, dickeres Rohr
    r(s, OLIV, h + 8, c - 2, 11, 3)
    r(s, SAND, h + 14, c - 3, 2, 6)                          # Sandband
    r(s, SCHWARZ, h + 19, c - 3, 1, 6)                       # Kappe vorn
    lauf(s, SCHWARZ, DUNKEL, h + 1, c - 5, 4, 2)             # Ausloesekasten oben
    r(s, STAHL_H, h + 9, c - 5, 1, 2)                        # Klappvisier


@symbol("einwegwerfer")
def _():
    s = neu()
    D.polygon(s, OLIV_DK, [(0, 2), (3, 3), (3, 8), (0, 9)])
    lauf(s, OLIV_DK, OLIV, 3, 4, 11, 4)
    lauf(s, OLIV_DK, OLIV_H, 13, 3, 12, 6)
    r(s, SAND, 19, 3, 2, 6)
    r(s, SCHWARZ, 24, 3, 1, 6)
    lauf(s, SCHWARZ, DUNKEL, 8, 1, 4, 3)
    r(s, STAHL_H, 15, 1, 1, 2)
    r(s, OLIV_DK, 9, 8, 2, 3)
    return s


@teil("rohr_leer")
def _():
    s = F(30, 9)
    D.polygon(s, OLIV_DK, [(0, 0), (4, 1), (4, 7), (0, 8)])
    r(s, SCHWARZ, 0, 2, 1, 5)
    lauf(s, OLIV_DK, OLIV, 4, 2, 12, 5)
    lauf(s, OLIV_DK, OLIV_H, 16, 1, 13, 7)
    r(s, SAND, 23, 1, 2, 7)
    r(s, SCHWARZ, 28, 2, 1, 5)                               # vorn offen
    return RAND(s, (16, 12, 8))


# ── Granatwerfer: einschuessig, Holzschaft, dicker Lauf, Leitervisier ──
@hand("granatwerfer")
def _(s, c):
    h = c + 6
    lauf(s, HOLZ, HOLZ_H, h - 9, c - 2, 12, 5)
    lauf(s, DUNKEL, STAHL_H, h + 1, c - 3, 4, 6)             # Verschluss
    lauf(s, STAHL, STAHL_H, h + 4, c - 3, 11, 7)             # dicker Lauf
    r(s, (70, 62, 50), h + 5, c - 2, 9, 5)
    r(s, SCHWARZ, h + 14, c - 2, 1, 5)                       # Muendung
    lauf(s, HOLZ, HOLZ_H, h + 6, c - 4, 5, 1)                # Vorderschaft-Kante
    D.rect(s, STAHL_H, (h + 2, c - 6, 3, 3), 1)              # Leitervisier hochgeklappt


@symbol("granatwerfer")
def _():
    s = neu()
    D.polygon(s, HOLZ, [(1, 5), (9, 4), (9, 8), (1, 10)])
    r(s, HOLZ_H, 1, 5, 8, 1)
    lauf(s, WST, WST_H, 9, 3, 4, 5)
    lauf(s, WST, WST_H, 13, 2, 11, 6)
    r(s, (24, 22, 18), 23, 3, 1, 4)
    lauf(s, HOLZ, HOLZ_H, 14, 7, 6, 2)
    D.rect(s, WST_H, (10, 0, 3, 3), 1)
    return s


@teil("granate40")
def _():
    s = F(7, 7)
    D.circle(s, OLIV_DK, (3, 3), 3)
    D.circle(s, OLIV, (3, 3), 2)
    r(s, MESSING, 3, 1, 1, 1)
    return RAND(s, (16, 12, 8))


# ── Horchposten: Mikrofon-Gitterkopf auf Spiess, neue Form in der Hand ──
@hand("horcher")
def _(s, c):
    h = c + 6
    lauf(s, KER_DK, KER, h, c - 1, 7, 3)                     # kurzer Spiess
    D.circle(s, KER_DK, (h + 10, c), 4)                      # runder Gitterkopf
    D.circle(s, KER, (h + 10, c), 3)
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1), (0, 0)):
        r(s, KER_DK, h + 10 + dx, c + dy, 1, 1)
    r(s, TEAL_H, h + 5, c - 2, 1, 1)                         # Leuchte
    D.line(s, KER_DK, (h + 2, c + 2), (h - 1, c + 5))       # eingeklappte Beine
    D.line(s, KER_DK, (h + 4, c + 2), (h + 4, c + 5))


@symbol("horcher")
def _():
    s = neu()
    r(s, KER_DK, 12, 4, 2, 6)
    D.line(s, KER_DK, (12, 9), (8, 10))
    D.line(s, KER_DK, (13, 9), (17, 10))
    D.circle(s, KER_DK, (13, 3), 3)
    D.circle(s, KER, (13, 3), 2)
    r(s, KER_DK, 13, 3, 1, 1)
    r(s, TEAL_H, 15, 6, 1, 1)
    return s


@teil("horcher_k")
def _():
    s = F(16, 16)
    for ende in ((2, 3), (2, 13), (14, 8)):
        D.line(s, KER_DK, (8, 8), ende)
    D.circle(s, KER_DK, (8, 8), 4)
    D.circle(s, KER, (8, 8), 3)
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1), (0, 0)):
        r(s, KER_DK, 8 + dx, 8 + dy, 1, 1)
    return RAND(s, (16, 12, 8))


# ── Kettenblitz: schwerer, mit Kondensatorbank und dicken Zinken ──
@hand("kettenblitz")
def _(s, c):
    h = c + 6
    for y in (c + 3, c + 5):                                 # Kondensatoren seitlich
        lauf(s, KER_DK, TEAL, h - 3, y, 8, 2)
    lauf(s, KER_DK, KER_H, h - 4, c - 4, 13, 8)              # schweres Gehaeuse
    r(s, KER, h - 3, c - 3, 11, 6)
    r(s, TEAL, h - 1, c - 1, 7, 1)
    D.circle(s, TEAL_DK, (h + 11, c), 4)                     # Spule
    D.circle(s, TEAL, (h + 11, c), 3)
    r(s, TEAL_H, h + 10, c - 1, 2, 1)
    lauf(s, KER_DK, KER_H, h + 13, c - 4, 6, 2)              # dicke Zinken
    lauf(s, KER_DK, KER_H, h + 13, c + 2, 6, 2)


@symbol("kettenblitz")
def _():
    s = neu()
    lauf(s, KER_DK, KER_H, 1, 2, 12, 7)
    r(s, TEAL, 3, 5, 8, 1)
    for x in (3, 7):
        lauf(s, KER_DK, TEAL, x, 9, 3, 2)
    D.circle(s, TEAL_DK, (15, 5), 3)
    D.circle(s, TEAL, (15, 5), 2)
    lauf(s, KER_DK, KER_H, 18, 2, 6, 2)
    lauf(s, KER_DK, KER_H, 18, 7, 6, 2)
    r(s, TEAL_H, 23, 5, 1, 1)
    return s


# ── Knaller: verbeulte Blechdose mit Loechern statt roter Stangen ──
BLECH, BLECH_H, BLECH_DK = (142, 144, 136), (196, 198, 188), (78, 80, 74)


def dose(s, x, y):
    D.circle(s, BLECH_DK, (x, y), 4)
    D.circle(s, BLECH, (x, y), 3)
    D.circle(s, BLECH_H, (x - 1, y - 1), 1)
    for dx, dy in ((1, -2), (2, 1), (-1, 2), (0, 0)):
        r(s, (40, 38, 34), x + dx, y + dy, 1, 1)
    r(s, GELB, x - 4, y + 1, 2, 1)                           # Rest eines Etiketts


@hand("knaller")
def _(s, c):
    dose(s, c + 6 + 4, c)
    r(s, SCHWARZ, c + 6 + 8, c - 1, 2, 1)                    # Zuendschnur
    r(s, AMBER, c + 6 + 10, c - 1, 1, 1)


@symbol("knaller")
def _():
    s = neu()
    lauf(s, BLECH_DK, BLECH_H, 8, 2, 9, 9)
    r(s, BLECH, 9, 3, 7, 7)
    for x, y in ((10, 4), (13, 5), (11, 7), (14, 8)):
        r(s, (40, 38, 34), x, y, 1, 1)
    r(s, GELB, 9, 6, 7, 1)
    D.line(s, SCHWARZ, (17, 3), (20, 1))
    r(s, AMBER, 21, 0, 1, 1)
    return s


@teil("knaller_wurf")
def _():
    s = F(12, 12)
    dose(s, 6, 6)
    return RAND(s, (16, 12, 8))


# ── Kuller: kleine, unscheinbare Stahlkugel ──
@hand("kuller")
def _(s, c):
    x = c + 6 + 4
    D.circle(s, (62, 62, 58), (x, c), 3)
    D.circle(s, (96, 96, 90), (x - 1, c - 1), 1)


@symbol("kuller")
def _():
    s = neu()
    D.circle(s, (62, 62, 58), (13, 6), 3)
    D.circle(s, (96, 96, 90), (12, 5), 1)
    return s


@teil("kuller_wurf")
def _():
    s = F(8, 8)
    D.circle(s, (62, 62, 58), (4, 4), 3)
    D.circle(s, (104, 104, 98), (3, 3), 1)
    return RAND(s, (16, 12, 8))


# ── MP: seitliches Stangenmagazin, Lochmantel, Drahtschaft ──
@hand("mp")
def _(s, c):
    h = c + 6
    D.rect(s, STAHL, (h - 9, c - 2, 7, 5), 1)                # Drahtschaft als Schlaufe
    lauf(s, DUNKEL, STAHL_H, h - 3, c - 1, 9, 3)             # duennes Rohrgehaeuse
    lauf(s, STAHL, STAHL_H, h + 6, c - 2, 7, 4)              # Lochmantel
    for x in range(h + 7, h + 13, 2):
        r(s, SCHWARZ, x, c - 1, 1, 2)
    r(s, STAHL_H, h + 13, c - 1, 2, 2)
    lauf(s, (60, 52, 40), (96, 84, 62), h + 2, c - 10, 3, 9)  # Magazin zur Seite
    r(s, AMBER, h + 2, c - 10, 3, 1)


@symbol("mp")
def _():
    s = neu()
    D.polygon(s, WST, [(1, 3), (6, 4), (6, 6), (1, 8)], 1)
    lauf(s, WST, WST_H, 6, 4, 9, 3)
    lauf(s, WST, WST_H, 15, 3, 8, 4)
    for x in range(16, 22, 2):
        r(s, (20, 18, 14), x, 4, 1, 2)
    r(s, WST_H, 23, 4, 2, 2)
    lauf(s, (60, 52, 40), (96, 84, 62), 10, 2, 3, 6)         # Magazin, von der Seite gesehen
    r(s, AMBER, 10, 2, 3, 1)
    r(s, WST, 8, 7, 2, 3)
    return s


# ── Munitionskiste statt Beutel, wie die Kisten im Spiel ──
@hand("munbeutel")
def _(s, c):
    h = c + 6
    lauf(s, (28, 22, 16), (28, 22, 16), h, c - 5, 12, 10)
    lauf(s, (122, 96, 44), (168, 136, 66), h + 1, c - 4, 10, 8)
    r(s, (60, 46, 24), h + 1, c + 2, 10, 2)
    for x in range(h + 2, h + 10, 3):
        r(s, (206, 168, 82), x, c - 2, 2, 3)
    r(s, (60, 50, 38), h + 4, c - 7, 4, 2)                   # Griff


@symbol("munbeutel")
def _():
    s = neu()
    w, hh = 16, 10
    x0 = 5
    lauf(s, (28, 22, 16), (28, 22, 16), x0, 1, w, hh)
    lauf(s, (122, 96, 44), (168, 136, 66), x0 + 1, 2, w - 2, hh - 2)
    r(s, (60, 46, 24), x0 + 1, 8, w - 2, 2)
    for x in range(x0 + 3, x0 + w - 2, 3):
        r(s, (206, 168, 82), x, 4, 2, 3)
    r(s, (60, 50, 38), x0 + 5, 0, 6, 2)
    return s


T["beutel_wurf"] = art._munikiste


# ── Raketenbuendel: kantige Kapsel mit Rohrmuendungen statt Wurst ──
@hand("raketenbuendel")
def _(s, c):
    h = c + 6
    lauf(s, HULL_SH, HULL_DK, h - 3, c - 5, 14, 11)          # Kapsel aus Blech
    r(s, HULL_DK, h - 2, c - 4, 12, 9)
    for i in range(0, 12, 4):                                # Warnstreifen schraeg
        D.line(s, GELB, (h - 2 + i, c + 4), (h + i, c + 2))
    for x, y in ((h - 1, c - 3), (h + 8, c - 3), (h - 1, c + 3), (h + 8, c + 3)):
        r(s, STAHL_H, x, y, 1, 1)                            # Nieten
    for y in (c - 4, c - 1, c + 2):                          # drei Rohrmuendungen vorn
        r(s, SCHWARZ, h + 11, y, 2, 2)
        r(s, (214, 96, 56), h + 12, y, 1, 1)
    r(s, SCHWARZ, h + 1, c - 7, 5, 2)                        # Tragegriff


@symbol("raketenbuendel")
def _():
    s = neu()
    lauf(s, HULL_SH, HULL_DK, 3, 1, 18, 8)
    r(s, HULL_DK, 4, 2, 16, 6)
    for i in range(4, 18, 4):
        D.line(s, GELB, (i, 7), (i + 2, 5))
    for y in (2, 5):
        lauf(s, SCHWARZ, DUNKEL, 21, y, 3, 3)
        r(s, (214, 96, 56), 23, y + 1, 1, 1)
    r(s, SCHWARZ, 9, 9, 3, 2)
    return s


# ── Sandsaecke: gefaltete Saecke in der Hand, neue Sackwand ──
@hand("sandsack")
def _(s, c):
    h = c + 6
    for i, y in enumerate((c - 4, c - 1, c + 2)):            # drei flache Saecke
        lauf(s, SAND_DK, SAND_H, h + 1 + (i % 2), y, 10, 3)
        r(s, SAND, h + 2 + (i % 2), y + 1, 8, 1)
    r(s, (96, 72, 40), h + 5, c - 5, 1, 9)                   # Gurt


@symbol("sandsack")
def _():
    s = neu()
    for i, y in enumerate((7, 4, 1)):
        lauf(s, SAND_DK, SAND_H, 6 + (i % 2) * 2, y, 13, 3)
    r(s, (96, 72, 40), 12, 1, 1, 9)
    return s


def sack(s, x, y, w=9, h=5):
    D.rect(s, (70, 60, 40), (x, y, w, h), border_radius=2)
    D.rect(s, SAND, (x + 1, y + 1, w - 2, h - 2), border_radius=1)
    r(s, SAND_H, x + 2, y + 1, w - 4, 1)
    r(s, (112, 96, 64), x + w // 2, y + 1, 1, h - 2)        # Naht


@teil("sackwand")
def _():
    s = F(14, 34)
    for i, y in enumerate(range(1, 30, 4)):                  # versetzte Reihen
        sack(s, 1 + (i % 2) * 3, y)
    return RAND(s, (16, 12, 8))


# ── Schlagring: an einer Faust, mit Ringen und Dornen; die andere bandagiert ──
@hand("schlagring")
def _(s, c):
    h = c + 6
    lauf(s, MESSING_DK, MESSING, h + 3, c + 1, 3, 6)         # Ring an der rechten Faust
    for y in (c + 2, c + 4):
        r(s, (60, 44, 20), h + 4, y, 1, 1)
    for y in (c + 1, c + 3, c + 5):
        r(s, CHROM_H, h + 6, y, 1, 1)                        # Dornen
    r(s, (214, 206, 180), h + 2, c - 5, 2, 3)                # Bandage links


@symbol("schlagring")
def _():
    s = neu()
    lauf(s, MESSING_DK, MESSING, 6, 4, 14, 4)
    for x in (7, 10, 13, 16):
        D.circle(s, MESSING, (x + 1, 2), 2, 1)               # Fingerringe
    for x in (8, 11, 14, 17):
        r(s, CHROM_H, x, 8, 1, 2)                            # Dornen unten
    r(s, MESSING_DK, 8, 8, 10, 1)
    return s


# ── Spaehdrohne: Vierrotor mit Rotorschutz, Kamera, Positionslichtern ──
def drohne_neu(phase):
    s = F(22, 22)
    m = 11
    for (x, y) in ((4, 4), (17, 4), (4, 17), (17, 17)):
        D.line(s, KARBON, (m, m), (x, y), 2)
        D.circle(s, KARBON_H, (x, y), 4, 1)                  # Rotorschutz
        a = phase * 45 + (x + y)
        v = pygame.Vector2(3, 0).rotate(a)
        D.line(s, (150, 154, 156), (x - v.x, y - v.y), (x + v.x, y + v.y))  # Blatt
        r(s, KARBON, x, y, 1, 1)
    D.ellipse(s, KARBON, (m - 4, m - 3, 9, 7))               # Rumpf
    D.ellipse(s, KER, (m - 3, m - 2, 7, 5))
    D.circle(s, SCHWARZ, (m + 4, m), 2)                      # Kamera vorn
    r(s, TEAL, m + 5, m, 1, 1)
    r(s, (220, 60, 50), m - 4, m - 4, 1, 1)                  # Positionslichter
    r(s, (90, 220, 110), m - 4, m + 4, 1, 1)
    return RAND(s, (16, 12, 8))


T["drohne_a"] = lambda: drohne_neu(0)
T["drohne_b"] = lambda: drohne_neu(1)


@hand("spaehdrohne")
def _(s, c):
    h = c + 6
    lauf(s, KARBON, KARBON_H, h, c - 5, 10, 10)             # Steuerung
    r(s, (20, 50, 46), h + 2, c - 3, 6, 3)                   # Bildschirm
    r(s, TEAL, h + 3, c - 2, 2, 1)
    D.circle(s, SCHWARZ, (h + 2, c + 3), 1)                  # zwei Knueppel
    D.circle(s, SCHWARZ, (h + 7, c + 3), 1)
    r(s, KER_H, h + 10, c - 4, 2, 1)                         # Antenne


@symbol("spaehdrohne")
def _():
    s = neu()
    lauf(s, KARBON, KARBON_H, 8, 4, 10, 3)
    D.ellipse(s, KER, (10, 4, 6, 3))
    r(s, SCHWARZ, 17, 6, 2, 2)
    for x in (2, 18):
        r(s, KARBON, x + 1, 3, 5, 1)
        r(s, (150, 154, 156), x, 2, 7, 1)
    D.line(s, KARBON, (8, 5), (5, 3))
    D.line(s, KARBON, (17, 5), (20, 3))
    r(s, KARBON, 10, 7, 1, 2)
    r(s, KARBON, 15, 7, 1, 2)
    return s


# Leuchtspur in mehreren Farben: die Spitze hat die Farbe der Spur
SY["mun_leucht_rot"] = lambda: symbol_patrone((214, 58, 40))
SY["mun_leucht_gruen"] = lambda: symbol_patrone((84, 196, 84))
SY["mun_leucht_gelb"] = lambda: symbol_patrone((236, 200, 64))


# ══════════════════════════════════════ Anmelden

# Die Hand zeichnet art._hand_waffe (aufbau "paket" in K.WAFFEN_HAND), die
# Figur je Waffe und Mannschaft entsteht dort wie bei jeder anderen Waffe.
# Klein geschrieben, wie alle Bildnamen (das Paket schrieb "fraktion_K").
art.HAND_ZEICHNER.update({n.lower(): z for n, z in H.items()
                          if n.lower() in K.PAKET_HAND})
_SY_KLEIN = {n.lower(): z for n, z in SY.items()}


def _symbol_zeichner(name):
    return lambda: _SY_KLEIN[name]()


def _teil_zeichner(name):
    return lambda: T[name]()


for _name in K.PAKET_SYMBOLE:
    platzhalter("waffe_" + _name)(_symbol_zeichner(_name))
for _name in K.PAKET_TEILE:
    platzhalter("teil_" + _name)(_teil_zeichner(_name))
