# -*- coding: utf-8 -*-
"""
Erzeugt karten/kanalstadt.txt - KANALSTADT (seit 0.34.131).

Die zweite neue Schlachtkarte (siehe werkzeug_flusstal.py fuer den Wunsch).
Wo FLUSSTAL offen und gruen ist, ist KANALSTADT eng und grau: eine
zerschossene Stadt, durch deren Mitte ein Kanal laeuft. Gekaempft wird in
Strassenschluchten, Hinterhoefen und offenen Haeusern; Fahrzeuge haben die
Strassen und die Bruecken, zu Fuss geht es durch die Hoefe und Ruinen.

Ueber den Kanal fuehren vier Strassenbruecken und in der Mitte die
eingestuerzte ALTE BRUECKE - deren Truemmer liegen im seichten Wasser, zu
Fuss kommt man hinueber, ein Wagen nur langsam auf einer Spur.

Neun Punkte, eine Zeile je Bahn:

    BAHNHOF  - EISENBRUECKE - KRAFTWERK      (Nord)
    RATHAUS  - ALTE BRUECKE - MARKTHALLE     (Mitte, die Allee)
    GASWERK  - STEINBRUECKE - GUETERBAHNHOF  (Sued)

Je Seite drei Basen am Rand, Kasernen aus Beton mit Gitterboden. Wie
FLUSSTAL punktgespiegelt; die Datei ist genau die Ausgabe dieses Werkzeugs.

    python werkzeug_kanalstadt.py
"""
from __future__ import annotations

import math
from pathlib import Path

from werkzeug_schlachtkarte import Leinwand, zufall

BREITE, HOEHE = 320, 224
SAAT = 13161

KOPF = [
    "# KANALSTADT - zerschossene Stadt mit Kanal (seit 0.34.131).",
    "# Erzeugt mit werkzeug_kanalstadt.py (nicht von Hand aendern - neu erzeugen).",
    "# 320 x 224 Kacheln, eine Ebene, punktgespiegelt. Satz stadt:",
    "#   . Hof (Kopfstein)  : Fahrbahn  _ Gehweg  ; Schutt  \" Rasen  = Fliesen  , Gitter",
    "#   # Ziegel  r Beton  b Truemmer  w Autowrack  s Sandsack  h Kiste  X Fass",
    "#   k Baum  + seichtes Wasser  % Kanal",
    "#   Z Spawnstelle  F Buggy  P Panzer  L Panzerwagen  E Eroberungspunkt",
    "#   R Basis Rot  B Basis Blau",
    "",
    "name: KANALSTADT",
    "satz: stadt",
    "kreise: E",
    "je_seite: 24",
    "je_seite_bis: 150",
    "fahrer: 6",
]

MITTE_X, MITTE_Y = (BREITE - 1) / 2.0, (HOEHE - 1) / 2.0
# Strassen: Ost-West in diesen Zeilen, Nord-Sued in diesen Spalten (die
# westliche Haelfte; gespiegelt die oestliche).
STRASSEN_Y = (40, 76, 112, 147, 183)   # je um die Mitte gespiegelt
STRASSEN_X = (44, 76, 110, 142)


def kanal_x(y: float) -> float:
    return MITTE_X + 6.0 * math.sin((y - MITTE_Y) * math.tau / 224.0)


def bauen() -> Leinwand:
    r = zufall(SAAT)
    lw = Leinwand(BREITE, HOEHE, ".")

    # ── Boden: Schutt und Risse ─────────────────────────────────────────
    # Seit 0.34.135 weniger (160 -> 60, gewuenscht: "uebersichtlicher").
    for _ in range(60):
        cx, cy = r.randrange(BREITE), r.randrange(HOEHE)
        lw.kreis(cx, cy, r.uniform(1.2, 3.0), ";", rnd=r, dichte=0.45)

    # ── Haeuserbloecke ───────────────────────────────────────────────────
    def haus_oder_dach(x0, y0, b, h, kaputt=0.1):
        """Ein Haus: entweder ein Dach (ganz Mauer) oder offen mit Raeumen."""
        if b < 5 or h < 5:
            lw.rechteck(x0, y0, x0 + b - 1, y0 + h - 1, "#")
            return
        if r.random() < 0.4:
            lw.rechteck(x0, y0, x0 + b - 1, y0 + h - 1, "#")
            # eingestuerzte Ecke
            if r.random() < kaputt * 3:
                lw.kreis(x0 + r.choice((1, b - 2)), y0 + r.choice((1, h - 2)), 2.2, ";")
            return
        tueren = []
        for seite in "nswo":
            if r.random() < 0.6:
                lang = b if seite in "ns" else h
                tueren.append((seite, r.randrange(1, max(2, lang - 3)), 2))
        if not tueren:
            tueren = [("s", 1, 2)]
        lw.haus(x0, y0, b, h, r, wand="#", boden="=", tueren=tueren, fenster=0.12,
                kaputt=kaputt, innen=b // 2 if b >= 9 else None)
        if r.random() < 0.5:
            lw.setze(x0 + r.randrange(1, b - 1), y0 + r.randrange(1, h - 1), r.choice("hhXb"), nur=set("="))

    def block_wohnen(x0, y0, x1, y1, kaputt=0.12):
        """Blockrand: Haeuser rundherum, Hof in der Mitte, Durchgaenge."""
        tief = 6
        x = x0
        while x < x1 - 3:                                  # Nord- und Suedseite
            b = min(r.randint(6, 11), x1 - x + 1)
            if r.random() < 0.18:
                x += 3                                     # Durchgang
                continue
            haus_oder_dach(x, y0, b, tief, kaputt)
            haus_oder_dach(x, y1 - tief + 1, b, tief, kaputt)
            x += b + (1 if r.random() < 0.3 else 0)
        y = y0 + tief
        while y < y1 - tief - 2:                            # West- und Ostseite
            h = min(r.randint(5, 8), y1 - tief - y)
            if r.random() < 0.25:
                y += 3
                continue
            haus_oder_dach(x0, y, tief, h, kaputt)
            haus_oder_dach(x1 - tief + 1, y, tief, h, kaputt)
            y += h
        # Hof: Rasen oder Asphalt, ein Baum, Kram
        hx0, hy0, hx1, hy1 = x0 + tief + 1, y0 + tief + 1, x1 - tief - 1, y1 - tief - 1
        if hx1 > hx0 + 2 and hy1 > hy0 + 2:
            if r.random() < 0.4:
                lw.rechteck(hx0, hy0, hx1, hy1, '"')
            for _ in range(r.randint(0, 2)):
                lw.setze(r.randint(hx0, hx1), r.randint(hy0, hy1), r.choice("khwbX"))

    def block_ruine(x0, y0, x1, y1):
        block_wohnen(x0, y0, x1, y1, kaputt=0.45)
        for _ in range(r.randint(2, 4)):
            lw.kreis(r.randint(x0, x1), r.randint(y0, y1), r.uniform(1.5, 3.2), ";", nur=set("#=."))
        for _ in range(r.randint(2, 5)):
            lw.setze(r.randint(x0, x1), r.randint(y0, y1), "b", nur=set(";."))

    def block_truemmerfeld(x0, y0, x1, y1):
        """Ein eingeebneter Block: Schutt, Mauerreste, Bombentrichter - offen
        und weit einsehbar, Deckung nur hinter Brocken und Stummeln."""
        lw.rechteck(x0, y0, x1, y1, ";")
        for _ in range(5):
            x, y = r.randint(x0 + 1, x1 - 4), r.randint(y0 + 1, y1 - 2)
            quer = r.random() < 0.5
            for i in range(r.randint(2, 5)):
                lw.setze(x + (i if quer else 0), y + (0 if quer else i), "#")
        for _ in range(int((x1 - x0) * (y1 - y0) * 0.02)):
            lw.setze(r.randint(x0, x1), r.randint(y0, y1), r.choice("bbbrw"))
        for _ in range(3):
            lw.kreis(r.randint(x0 + 3, x1 - 3), r.randint(y0 + 3, y1 - 3), r.uniform(2.0, 3.0), ".")

    def block_park(x0, y0, x1, y1, teich=True):
        lw.rechteck(x0, y0, x1, y1, '"')
        mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        lw.linie([(x0, my), (x1, my)], 2, "_")
        lw.linie([(mx, y0), (mx, y1)], 2, "_")
        if teich:
            lw.kreis(mx + (x1 - x0) * 0.22, my - (y1 - y0) * 0.22, 3.2, "+", quer=1.5)
        for _ in range(int((x1 - x0) * (y1 - y0) * 0.06)):
            x, y = r.randint(x0, x1), r.randint(y0, y1)
            lw.setze(x, y, "k", nur=set('"'))
        for i in range(x0 + 2, x1 - 1, 5):                  # Baenke an den Wegen
            lw.setze(i, int(my) + 2, "h", nur=set('"'))

    def block_platz(x0, y0, x1, y1):
        lw.rechteck(x0, y0, x1, y1, "_")
        mx, my = int((x0 + x1) / 2), int((y0 + y1) / 2)
        lw.kreis(mx, my, 2.2, "+")                          # Brunnen
        lw.setze(mx, my, "r")
        for x in range(x0 + 1, x1, 4):
            lw.setze(x, y0 + 1, "k")
            lw.setze(x, y1 - 1, "k")

    def block_industrie(x0, y0, x1, y1):
        """Hallen aus Beton mit Toren fuer Wagen, Kisten, Schornsteine."""
        lw.rechteck(x0, y0, x1, y1, ".")
        mx = (x0 + x1) // 2
        hb = mx - x0 - 1
        lw.haus(x0, y0, hb, y1 - y0 - 6, r, wand="r", boden=",",
                tueren=(("s", 2, 5), ("o", 3, 4)), fenster=0.05, kaputt=0.1)
        lw.kreis(x1 - 4, y0 + 4, 2.3, "r")                  # Schornstein
        lw.kreis(x1 - 10, y0 + 4, 2.3, "r")
        for y in range(y1 - 4, y1 + 1, 2):                  # Containerreihen
            for x in range(mx + 1, x1 - 1):
                if (x - mx) % 6 < 4:
                    lw.setze(x, y, "h")
        for i in range(x0 + 2, mx, 3):                      # Rohrleitung
            lw.setze(i, y1 - 2, "b")

    # Die Bloecke der westlichen Haelfte (gespiegelt die oestliche).
    xs = (4,) + STRASSEN_X
    ys = (3,) + STRASSEN_Y + (HOEHE - 4,)
    besondere = {}
    for bi in range(len(xs) - 1):
        for bj in range(len(ys) - 1):
            x0, x1 = xs[bi] + 3, xs[bi + 1] - 3
            # An der Allee (y 112) ist die Strasse breiter.
            y0 = ys[bj] + (7 if ys[bj] == 112 else 3)
            y1 = ys[bj + 1] - (7 if ys[bj + 1] == 112 else 3)
            if bi == 0:
                continue                                    # hinter den Linien: Basen und Nachschubstrasse
            besondere[(bi, bj)] = (x0, y0, x1, y1)
            if (bi, bj) in ((2, 0), (2, 2), (2, 4), (3, 4)):
                continue                                    # Bahnhof, Rathaus, Gaswerk, Hafen: unten von Hand
            if (bi, bj) == (1, 1):
                block_park(x0, y0, x1, y1)
            elif (bi, bj) == (1, 3):
                block_platz(x0, y0, x1, y1)
            elif (bi, bj) == (3, 2):
                block_truemmerfeld(x0, y0, x1, y1)          # offen vor der Alten Bruecke
            elif bi == 3:
                block_ruine(x0, y0, x1, y1)                 # am Kanal ist alles zerschossen
            else:
                block_wohnen(x0, y0, x1, y1)

    # ── Strassen ────────────────────────────────────────────────────────
    def strasse_quer(y, x0, x1, breit=4):
        lw.rechteck(x0, y - breit // 2 - 1, x1, y + breit // 2, "_")
        lw.rechteck(x0, y - breit // 2, x1, y + breit // 2 - 1, ":")

    def strasse_laengs(x, y0, y1, breit=4):
        lw.rechteck(x - breit // 2 - 1, y0, x + breit // 2, y1, "_", nicht=set(":"))
        lw.rechteck(x - breit // 2, y0, x + breit // 2 - 1, y1, ":")

    kanal_links = int(min(kanal_x(y) for y in range(HOEHE))) - 8
    for y in STRASSEN_Y:
        if y == 112:
            continue
        strasse_quer(y, 4, int(MITTE_X) + 1)
    for x in STRASSEN_X:
        strasse_laengs(x, 3, HOEHE - 4)
    # Die Allee: breit, mit Baeumen im Mittelstreifen.
    lw.rechteck(4, 106, int(MITTE_X) + 1, 117, "_")
    lw.rechteck(4, 107, int(MITTE_X) + 1, 110, ":")
    lw.rechteck(4, 113, int(MITTE_X) + 1, 116, ":")
    for x in range(48, int(MITTE_X) - 12, 4):
        lw.setze(x, 111, "k")
        lw.setze(x, 112, '"')
        lw.setze(x + 2, 111, '"')
    # Die Nachschubstrasse hinter den Linien.
    strasse_laengs(40, 3, HOEHE - 4)

    # ── Der Kanal ────────────────────────────────────────────────────────
    for y in range(-1, HOEHE + 1):
        x = kanal_x(y)
        for xx in range(int(x - 9), int(x + 10)):
            d = abs(xx + 0.5 - x)
            if d <= 3.6:
                lw.setze(xx, y, "%")
            elif d <= 5.6:
                lw.setze(xx, y, "_")                        # Kai
    # Hafenbecken: ein Arm des Kanals nach Westen (gespiegelt: nach Osten),
    # suedlich davon Lagerhallen am Kai.
    hx0, hy0, hx1, hy1 = besondere[(3, 4)]
    lw.rechteck(hx0, hy0, hx1, hy1, ".")
    for i, hx in enumerate(range(hx0, hx1 - 8, 14)):
        lw.haus(hx, 172, 12, hy1 - 171, r, wand="#", boden=",",
                tueren=(("n", 3, 5), ("w", 2, 2)), fenster=0.06, kaputt=0.12)
    lw.rechteck(114, 156, int(kanal_x(162)), 168, "%")
    lw.rechteck(112, 154, int(kanal_x(162)), 155, "_")
    lw.rechteck(112, 169, int(kanal_x(162)), 170, "_")
    for x in range(116, int(kanal_x(162)) - 4, 7):          # Poller, Kisten am Kai
        lw.setze(x, 153, "h")
        lw.setze(x + 1, 153, "h")
        lw.setze(x + 3, 171, "w")
    lw.kreis(118, 151, 1.6, "r")                            # Kranfuss

    # ── Bruecken ─────────────────────────────────────────────────────────
    def bruecke(y, breit=4, punkt=None, gegen=None):
        x = kanal_x(y)
        for xx in range(int(x - 7), int(x + 8)):
            for yy in range(y - breit // 2, y + breit // 2):
                lw.setze(xx, yy, ":")
            lw.setze(xx, y - breit // 2 - 1, "_")
            lw.setze(xx, y + breit // 2, "_")
        for xx in range(int(x - 4), int(x + 5)):
            lw.setze(xx, y - breit // 2 - 2, "b")          # Bruestung
            lw.setze(xx, y + breit // 2 + 1, "b")
        if punkt:
            lw.punkt(int(round(x)), y, punkt, gegen)
    bruecke(40, 6, "EISENBRÜCKE", "STEINBRÜCKE")
    bruecke(76, 4)
    # Die ALTE BRUECKE: eingestuerzt, Truemmer im seichten Wasser.
    for y in range(103, 121):
        x = kanal_x(y)
        for xx in range(int(x - 5), int(x + 6)):
            if lw.get(xx, y) == "%":
                lw.setze(xx, y, "+")
    for _ in range(26):
        y = r.randint(104, 119)
        x = kanal_x(y) + r.uniform(-4.5, 4.5)
        if not (109 <= y <= 113):                           # eine Spur bleibt frei
            lw.setze(int(x), y, r.choice("bbr"))
    lw.spiegeln = False
    lw.punkt(int(MITTE_X), int(MITTE_Y) - 3, "ALTE BRÜCKE")
    lw.spiegeln = True

    # ── Bahnhof (Nordwest) ───────────────────────────────────────────────
    x0, y0, x1, y1 = besondere[(2, 0)]
    lw.rechteck(x0, y0, x1, y1, ".")
    lw.haus(x0, y0, x1 - x0 + 1, 12, r, wand="#", boden="=",
            tueren=(("s", 4, 4), ("s", (x1 - x0) - 8, 4), ("w", 4, 3), ("o", 4, 3)),
            fenster=0.1, kaputt=0.08, innen=(x1 - x0) // 2)
    for gy in (y0 + 15, y0 + 20, y0 + 25):                  # Gleise mit Wagen
        lw.rechteck(x0, gy, x1, gy, ";")
        for x in range(x0 + r.randint(0, 4), x1 - 6, r.randint(12, 16)):
            lw.rechteck(x, gy - 1, x + 5, gy + 1, "w")
    for gy in (y0 + 17, y0 + 22):                           # Bahnsteige
        lw.rechteck(x0 + 2, gy, x1 - 2, gy + 1, "_")
    lw.punkt((x0 + x1) // 2, y0 + 13, "BAHNHOF", "GÜTERBAHNHOF")

    # ── Rathaus (Mitte West) ─────────────────────────────────────────────
    x0, y0, x1, y1 = besondere[(2, 2)]
    lw.rechteck(x0, y0, x1, y1, "_")
    mx = (x0 + x1) // 2
    lw.haus(mx - 9, y0, 19, 12, r, wand="#", boden="=",
            tueren=(("s", 7, 5), ("w", 4, 2), ("o", 4, 2)), fenster=0.15, kaputt=0.1, innen=9)
    lw.kreis(mx, y1 - 6, 2.5, "+")                          # Brunnen
    lw.setze(mx, y1 - 6, "r")
    for x in range(x0 + 1, x1, 4):
        lw.setze(x, y1, "k")
    for dx in (-8, 8):                                       # Barrikaden
        for i in range(4):
            lw.setze(mx + dx, y1 - 10 + i, "s")
    lw.punkt(mx, y0 + 15, "RATHAUS", "MARKTHALLE")

    # ── Gaswerk (Suedwest; gespiegelt das Kraftwerk im Nordosten) ────────
    x0, y0, x1, y1 = besondere[(2, 4)]
    block_industrie(x0, y0, x1, y1)
    lw.kreis(x0 + 6, y1 - 12, 3.8, "r")                     # Gasbehaelter
    lw.punkt((x0 + x1) // 2 + 2, (y0 + y1) // 2 + 1, "GASWERK", "KRAFTWERK")

    # ── Strassenkampf: Wracks, Barrikaden, Trichter ──────────────────────
    for _ in range(30):
        if r.random() < 0.5:
            y = r.choice(STRASSEN_Y)
            x = r.randint(48, int(MITTE_X) - 10)
            y += r.choice((-1, 0, 1))
        else:
            x = r.choice(STRASSEN_X) + r.choice((-1, 0, 1))
            y = r.randint(6, HOEHE - 7)
        lw.setze(x, y, "w", nur=set(":"))
    for x in STRASSEN_X[1:]:                                 # Barrikaden an Kreuzungen
        for y in STRASSEN_Y:
            if r.random() < 0.25:
                seite = r.choice((-1, 1))
                for i in range(3):
                    lw.setze(x + seite * 4, y - 1 + i, "s", nur=set(":_."))
    for _ in range(12):                                      # Trichter
        x, y = r.randint(50, int(MITTE_X) - 12), r.randint(8, HOEHE - 8)
        lw.kreis(x, y, r.uniform(1.4, 2.6), ";", nur=set(':_."'))

    # ── Basen ───────────────────────────────────────────────────────────
    lw.basis(0, 20, 40, "NORDKASERNE", "krad 2 0, buggy 1 0, funkwagen 1 1, tragschrauber 1 2", r,
             mauer="r", hof=",", tore=("o", "s"), gegen_name="SÜDKASERNE")
    lw.basis(0, 20, 112, "HAUPTDEPOT",
             "buggy 1 0, panzerwagen 1 0, trosswagen 1 0, flakwagen 1 1, jagdpanzer 1 2, werfer 1 3", r,
             mauer="r", hof=",", tore=("o", "n", "s"), gegen_name="HAUPTDEPOT")
    lw.basis(1, 299, 40, "NORDKASERNE", "krad 1 0, buggy 1 0, trosswagen 1 1, panzer 1 2, spulenwagen 1 2", r,
             mauer="r", hof=",", tore=("w", "s"), gegen_name="SÜDKASERNE")
    for (fx, fy, z) in ((38, 108, "F"), (38, 116, "F"), (38, 46, "L"), (38, 152, "P")):
        lw.setze(fx, fy, z)

    # ── Wege fuer die Bots ──────────────────────────────────────────────
    kb_n = int(round(kanal_x(40)))
    kb_76 = int(round(kanal_x(76)))
    kb_147 = int(round(kanal_x(147)))
    lw.weg([(36, 40), (60, 40), (92, 40), (126, 40), (kb_n - 9, 40), (kb_n, 40), (kb_n + 9, 40),
            (193, 40), (227, 40), (259, 40), (283, 40)])                               # Nordbahn
    lw.weg([(36, 112), (60, 112), (92, 112), (126, 112), (150, 111), (159, 109), (169, 112),
            (193, 112), (227, 112), (259, 112), (283, 112)])                           # Allee
    lw.weg([(40, 40), (40, 76), (40, 112), (40, 147), (40, 183)])                      # hinten
    lw.weg([(92, 40), (110, 40), (110, 58), (110, 76), (110, 94), (110, 112)])         # Bahnhof - Rathaus
    lw.weg([(76, 112), (76, 94), (76, 76), (76, 58), (76, 40)])
    lw.weg([(110, 112), (110, 130), (110, 147), (110, 165), (110, 183)])               # Rathaus - Gaswerk
    lw.weg([(110, 76), (126, 76), (142, 76), (kb_76, 76), (177, 76), (209, 76), (209, 58),
            (209, 40), (227, 40)])                                                     # Nebenbruecke Nord
    lw.weg([(110, 147), (126, 147), (142, 147), (kb_147, 147), (177, 147), (209, 147),
            (209, 130), (209, 112), (227, 112)])                                       # Nebenbruecke Sued
    lw.weg([(126, 40), (142, 40), (142, 58), (142, 76), (142, 94), (142, 112)])        # am Kai
    lw.weg([(60, 76), (76, 76), (92, 76), (110, 76)])
    lw.weg([(60, 147), (76, 147), (92, 147), (110, 147)])
    return lw


def als_text(lw: Leinwand) -> str:
    return lw.als_text(KOPF)


def fertig() -> Leinwand:
    lw = bauen()
    r = zufall(SAAT + 1)
    lw.spiegeln = True
    for y in range(HOEHE):
        for x in range(BREITE):
            gx, gy = lw.gegen(x, y)
            if (y, x) > (gy, gx):
                continue
            tief = min(x, y, BREITE - 1 - x, HOEHE - 1 - y)
            if tief < 3 or (tief < 5 and r.random() < 0.35 * (5 - tief) / 2):
                lw.setze(x, y, "r")
    lw.wege_freilegen()
    lw.erreichbar_machen((40, 112))
    lw.pruefen()
    return lw


if __name__ == "__main__":
    ziel = Path("karten/kanalstadt.txt")
    ziel.write_text(als_text(fertig()), encoding="utf-8")
    print("geschrieben:", ziel)
