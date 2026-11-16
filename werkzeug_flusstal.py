# -*- coding: utf-8 -*-
"""
Erzeugt karten/flusstal.txt - FLUSSTAL (seit 0.34.131).

Gewuenscht: zwei neue Karten fuer die SCHLACHT, "im Stil und der Location
deutlich anders" als STAUBTAL, alle Fahrzeuge gut nutzbar, mit seichtem
Wasser, mehreren Basen je Seite, Eroberungspunkten und Wegen, auf denen
die Bots in kleinen Gruppen vorgehen und flankieren - und es soll sich wie
eine Front anfuehlen, ohne leichten Weg hinten herum.

FLUSSTAL: ein gruenes Tal, durch die Mitte fliesst ein Fluss, zu tief zum
Durchwaten. Hinueber geht es nur an fuenf Stellen: zwei steinerne Bruecken
(NORDBRUECKE, SUEDBRUECKE), zwei Furten dazwischen und die breite Furt um
die MUEHLE auf der Insel in der Mitte. Jede Uebergangsstelle liegt an einem
Eroberungspunkt - wer hinueber will, muss durch einen Kampf.

Neun Punkte im Raster 3 x 3, eine Zeile je Bahn:

    KAPELLE   - NORDBRUECKE - GUTSHOF        (Nordbahn)
    WESTDORF  - MUEHLE      - OSTDORF        (Mitte)
    GEHOEFT   - SUEDBRUECKE - KLAUSE         (Suedbahn)

Je Seite drei Basen am Kartenrand (Nord, Haupt, Sued) mit Mauerring,
Toren, Bunker und eigenen Fahrzeugen: die Hauptlager mit schwerem Geraet,
das Nordlager der Roten (Suedlager der Blauen) mit dem Tragschrauber.
Zwischen den Bahnen Wald (nur zu Fuss), Hecken mit Durchlaessen (Bocage),
Felsruecken und Bachlaeufe mit seichtem Wasser.

Die Karte ist punktgespiegelt (werkzeug_schlachtkarte.Leinwand): was ROT
im Westen hat, hat BLAU im Osten. Die Datei ist genau die Ausgabe dieses
Werkzeugs - wer die Karte aendern will, aendert hier (tests/test_pruefung.py
prueft das).

    python werkzeug_flusstal.py
"""
from __future__ import annotations

import math
from pathlib import Path

from werkzeug_schlachtkarte import Leinwand, glatt, zufall

BREITE, HOEHE = 340, 210
SAAT = 13101

KOPF = [
    "# FLUSSTAL - gruenes Tal mit Fluss, Bruecken und Furten (seit 0.34.131).",
    "# Erzeugt mit werkzeug_flusstal.py (nicht von Hand aendern - neu erzeugen).",
    "# 340 x 210 Kacheln, eine Ebene, punktgespiegelt. Satz gruen:",
    "#   . Wiese  : Feldweg  ; Kiesufer  \" hohe Wiese  _ Platten  = Dielen  | Bruecke",
    "#   # Feldsteinmauer  r Granit  b Findling  s Sandsack  h Holzkiste",
    "#   X Fass  k Baum  w Schrott  + seichtes Wasser  % tiefes Wasser",
    "#   Z Spawnstelle  F Buggy  P Panzer  L Panzerwagen  E Eroberungspunkt",
    "#   R Basis Rot  B Basis Blau",
    "",
    "name: FLUSSTAL",
    "satz: gruen",
    "kreise: E",
    "je_seite: 24",
    "je_seite_bis: 150",
    "fahrer: 7",
]

MITTE_X, MITTE_Y = (BREITE - 1) / 2.0, (HOEHE - 1) / 2.0


def fluss_x(y: float) -> float:
    """Wo die Mitte des Flusses in Zeile y liegt - eine Welle, die um die
    Kartenmitte punktsymmetrisch ist."""
    return MITTE_X + 15.0 * math.sin((y - MITTE_Y) * math.tau / 160.0) \
        + 3.0 * math.sin((y - MITTE_Y) * math.tau / 47.0)


def bauen() -> Leinwand:
    r = zufall(SAAT)
    lw = Leinwand(BREITE, HOEHE, ".")

    # ── Boden: hohe Wiese und Kiesflecken ───────────────────────────────
    for _ in range(140):
        cx, cy = r.randrange(BREITE), r.randrange(HOEHE)
        lw.kreis(cx, cy, r.randint(2, 6), '"', rnd=r, dichte=0.65)
    for _ in range(30):
        cx, cy = r.randrange(BREITE), r.randrange(HOEHE)
        lw.kreis(cx, cy, r.randint(1, 3), ";", rnd=r, dichte=0.5)

    # ── Waelder: nur zu Fuss, mit Lichtungen ─────────────────────────────
    def wald(cx, cy, rx, ry, dichte=0.42):
        for y in range(int(cy - ry), int(cy + ry) + 1):
            for x in range(int(cx - rx), int(cx + rx) + 1):
                d = ((x - cx) / float(rx)) ** 2 + ((y - cy) / float(ry)) ** 2
                rand = 1.0 + 0.25 * math.sin(x * 0.7) * math.cos(y * 0.5)
                if d <= rand:
                    if r.random() < dichte * (1.0 - 0.35 * d):
                        lw.setze(x, y, "k")
                    elif r.random() < 0.35:
                        lw.setze(x, y, '"')
    wald(72, 72, 22, 11)            # Nordwald, zwischen Nord- und Mittelbahn
    wald(270, 66, 20, 10)           # Ostwald (gespiegelt: Suedwestwald)
    wald(132, 8, 22, 6, 0.5)        # Waldrand am Nordrand
    wald(36, 138, 12, 9, 0.38)      # Waeldchen hinter den roten Linien
    # Ufergehoelz: einzelne Baeume den Fluss entlang
    for y in range(0, HOEHE):
        for seite in (-1, 1):
            if r.random() < 0.07:
                x = int(fluss_x(y) + seite * r.uniform(9, 15))
                lw.setze(x, y, "k", nur=set('.";'))

    # ── Felsruecken ─────────────────────────────────────────────────────
    def fels(cx, cy, rad, quer=1.4):
        lw.kreis(cx, cy, rad, "r", quer=quer)
        lw.kreis(cx, cy, rad + 1.5, "b", rnd=r, dichte=0.25, nur=set('.";'), quer=quer)
    fels(140, 20, 4)                # Felsnase am Nordufer
    fels(88, 46, 3, 2.0)            # Ruecken zwischen Kapelle und Nordwald
    fels(60, 96, 3, 1.2)
    fels(200, 74, 3.5, 1.6)         # am Ostufer zwischen Furt und Gutshof
    fels(124, 136, 3, 1.8)
    fels(230, 128, 2.5, 1.3)

    # ── Hecken (Bocage) zwischen Westdorf und Fluss ──────────────────────
    # Felder mit Heckenrand; jede Hecke hat einen Durchlass, breit genug
    # fuer einen Panzer - wer faehrt, muss ihn finden.
    for fx0, fy0 in ((112, 82), (132, 82), (112, 128), (132, 124), (198, 116), (198, 96)):
        b, h = 18, 14
        for x in range(fx0, fx0 + b + 1):
            for y in (fy0, fy0 + h):
                if not (fx0 + 6 <= x <= fx0 + 11):
                    lw.setze(x, y, r.choice("kk\"b"), nur=set('.";'))
        for y in range(fy0, fy0 + h + 1):
            for x in (fx0, fx0 + b):
                if not (fy0 + 4 <= y <= fy0 + 9):
                    lw.setze(x, y, r.choice("kk\""), nur=set('.";'))

    # ── Deckung auf den Wiesen ──────────────────────────────────────────
    # Einzelne Baeume und Buschgruppen: offen genug fuer Panzer, aber zu
    # Fuss kommt man von Deckung zu Deckung.
    # Seit 0.34.135 weniger Kram (gewuenscht: "freier", "uebersichtlicher"):
    # Baeume 170 -> 90, Heuballen 26 -> 14, Feldmauern 22 -> 11, Trichter 18 -> 10.
    for _ in range(90):
        x, y = r.randrange(8, BREITE - 8), r.randrange(8, HOEHE - 8)
        if lw.get(x, y) in '."':
            lw.setze(x, y, "k")
            if r.random() < 0.5:
                lw.kreis(x + r.choice((-1, 1)), y + r.choice((-1, 1)), 1.4, '"', nur=set("."))
    # Heuballen in Reihen auf den Feldern.
    for _ in range(14):
        x, y = r.randrange(50, 150), r.randrange(10, HOEHE - 10)
        quer = r.random() < 0.5
        for i in range(r.randint(2, 4)):
            xx, yy = (x + i * 2, y) if quer else (x, y + i * 2)
            lw.setze(xx, yy, "h", nur=set('.";'))
    # Feldmauern: kurze Zuege aus Feldsteinen mit Luecken.
    for _ in range(11):
        x, y = r.randrange(48, 150), r.randrange(10, HOEHE - 10)
        quer = r.random() < 0.5
        for i in range(r.randint(5, 11)):
            if r.random() < 0.8:
                xx, yy = (x + i, y) if quer else (x, y + i)
                lw.setze(xx, yy, "#", nur=set('.";'))
    # Granattrichter: Kies im Kreis, ein paar Brocken am Rand.
    for _ in range(10):
        x, y = r.randrange(110, 160), r.randrange(10, HOEHE - 10)
        rad = r.uniform(1.6, 2.8)
        lw.kreis(x, y, rad, ";", nur=set('."k'))
        lw.kreis(x, y, rad + 1.2, "b", rnd=r, dichte=0.18, nur=set('."'))
    # Kleine Ruinen: ein Mauereck, drinnen Kram.
    for (rx, ry) in ((70, 20), (140, 92), (62, 150), (128, 58), (86, 190)):
        lw.haus(rx, ry, 7, 6, r, tueren=(("s", 2, 3), ("o", 2, 2)), boden=";", kaputt=0.3)
        lw.setze(rx + 3, ry + 2, r.choice("hXw"))

    # ── Der Fluss ───────────────────────────────────────────────────────
    for y in range(-2, HOEHE + 2):
        x = fluss_x(y)
        breit = 4.6 + 0.8 * math.sin(y * 0.21)
        for xx in range(int(x - breit - 4), int(x + breit + 5)):
            d = abs(xx + 0.5 - x)
            if d <= breit:
                lw.setze(xx, y, "%")
            elif d <= breit + 1.6:
                lw.setze(xx, y, "+")
            elif d <= breit + 2.8 and r.random() < 0.55:
                lw.setze(xx, y, ";")
    # Furten: das tiefe Wasser wird seicht, das Ufer flach.
    def furt(y0, y1):
        for y in range(y0, y1 + 1):
            x = fluss_x(y)
            for xx in range(int(x - 8), int(x + 9)):
                if lw.get(xx, y) == "%":
                    lw.setze(xx, y, "+")
                elif lw.get(xx, y) in "k":
                    lw.setze(xx, y, ";")
    furt(66, 74)                    # Nordfurt (gespiegelt: Suedfurt)
    furt(91, 118)                   # die breite Furt um die Muehle
    # Die Muehleninsel in der breiten Furt.
    lw.kreis(MITTE_X, MITTE_Y, 7.5, ";", quer=1.25)
    lw.kreis(MITTE_X, MITTE_Y, 6.2, ".", quer=1.25)
    # Bachlaeufe: seicht, mit tiefen Kolken - sie gliedern die Ufer.
    bach = glatt([(54, 0), (60, 18), (82, 30), (96, 58), (120, 66), (150, 70), (fluss_x(70), 70)])
    lw.linie(bach, 2.6, "+", nur=set('.";kb'))
    for i in range(6, len(bach) - 4, 9):
        lw.kreis(bach[i][0], bach[i][1], 1.6, "%")
    bach2 = glatt([(150, 209), (142, 186), (134, 166), (120, 150), (98, 146), (80, 150), (58, 160)])
    lw.linie(bach2, 2.2, "+", nur=set('.";kb'))
    for i in range(5, len(bach2) - 3, 11):
        lw.kreis(bach2[i][0], bach2[i][1], 1.4, "%")

    # ── Strassen (Feldwege) ─────────────────────────────────────────────
    def strasse(punkte, breit=3.6):
        lw.linie(glatt(punkte), breit, ":", nicht=set("%+#=|"))
    # Nordbahn: Nordlager - Kapelle - Nordbruecke - Gutshof - (blaues Suedlager)
    bruecke_n = (int(round(fluss_x(38))), 38)
    strasse([(34, 38), (60, 42), (96, 40), (118, 42), (bruecke_n[0] - 12, 39), (bruecke_n[0] - 6, 38)])
    strasse([(bruecke_n[0] + 6, 38), (bruecke_n[0] + 14, 37), (200, 34), (231, 36), (262, 30),
             (290, 34), (305, 37)])
    # Mitte: Hauptlager - Westdorf - Muehlenfurt
    strasse([(33, 104), (60, 106), (84, 112), (100, 113), (124, 110), (146, 106),
             (MITTE_X - 12, 105), (MITTE_X - 7, 104.5)])
    # Hinter der Front: die Nachschubstrasse von Lager zu Lager.
    strasse([(40, 38), (44, 60), (42, 82), (40, 104)], 3.2)
    strasse([(40, 104), (44, 126), (42, 150), (40, 172)], 3.2)
    # Querwege zwischen den Bahnen (zu den Furten).
    strasse([(100, 113), (106, 90), (112, 62), (114, 44)], 3.2)
    strasse([(150, 70), (int(fluss_x(70)) - 9, 70)], 3.2)
    strasse([(int(fluss_x(70)) + 9, 70), (214, 66), (244, 90)], 3.2)
    # Durch das Mittelfeld: Westdorf - Furt (Suedfurt) - Klause
    strasse([(100, 113), (116, 124), (140, 136), (int(fluss_x(139)) - 9, 139)], 3.2)

    # Die Furten der Strassen sind Kiesbaenke: dort wird nichts tief.
    for y0, y1 in ((66, 74),):
        for y in range(y0, y1 + 1):
            x = fluss_x(y)
            for xx in range(int(x - 4), int(x + 5)):
                if lw.get(xx, y) == "%":
                    lw.setze(xx, y, "+")

    # ── Stellungen am Ufer: Sandsackreihen mit Luecken ──────────────────
    # Die Front: an jedem Ufer liegen Stellungen, aus denen man den Fluss
    # und die andere Seite haelt.
    for y in range(8, HOEHE - 8, 9):
        x = int(fluss_x(y) - 12 - r.randrange(0, 4))
        if lw.get(x, y) in '.";' and r.random() < 0.7:
            for i in range(r.randint(3, 5)):
                lw.setze(x, y + i, "s", nur=set('.";'))

    # ── Bruecken ─────────────────────────────────────────────────────────
    bx, by = bruecke_n
    for y in range(by - 3, by + 4):
        for x in range(bx - 9, bx + 10):
            lw.setze(x, y, "|")
    for x in range(bx - 8, bx + 9):
        lw.setze(x, by - 4, "#")
        lw.setze(x, by + 4, "#")
    for x in (bx - 9, bx + 9):        # Pfeiler an den Enden, die Bruecke bleibt offen
        lw.setze(x, by - 4, "#")
        lw.setze(x, by + 4, "#")
    # Sandsackstellungen an beiden Brueckenkoepfen.
    for seite in (-1, 1):
        for i in range(4):
            lw.setze(bx + seite * 13, by - 8 + i, "s")
            lw.setze(bx + seite * 13, by + 5 + i, "s")
    lw.punkt(bx, by, "NORDBRÜCKE", "SÜDBRÜCKE")

    # ── Die Muehle auf der Insel (Punkt in der Mitte) ────────────────────
    lw.spiegeln = True
    # Genau um die Kartenmitte, sonst laege ihr Spiegelbild versetzt darueber.
    lw.haus(166, 100, 8, 10, r, tueren=(("w", 4, 2), ("o", 4, 2)), fenster=0.15)
    lw.setze(int(MITTE_X) - 7, int(MITTE_Y) - 5, "h")
    lw.setze(int(MITTE_X) - 7, int(MITTE_Y) - 6, "h")
    lw.spiegeln = False
    lw.punkt(int(MITTE_X), int(MITTE_Y) - 6, "MÜHLE")
    lw.spiegeln = True

    # ── Kapelle auf dem Huegel (Nordwest) ────────────────────────────────
    kx, ky = 112, 24
    lw.kreis(kx, ky, 11, "r", quer=1.3)
    lw.kreis(kx, ky, 8.5, ".", quer=1.3)
    for weg in ((kx, ky + 7, kx + 2, ky + 14), (kx - 12, ky - 2, kx - 17, ky + 1),
                (kx + 11, ky - 3, kx + 16, ky - 5)):
        lw.linie([(weg[0], weg[1]), (weg[2], weg[3])], 4.2, ";")
    lw.haus(kx - 4, ky - 6, 9, 11, r, tueren=(("s", 3, 3), ("o", 4, 2)), fenster=0.2, kaputt=0.08)
    for gy in range(ky - 5, ky + 6, 3):               # Friedhof: Grabsteine
        for gx in (kx - 9, kx - 7, kx + 7, kx + 9):
            lw.setze(gx, gy, "b", nur=set('.";'))
    lw.punkt(kx, ky + 8, "KAPELLE", "KLAUSE")

    # ── Westdorf (gespiegelt: Ostdorf) ──────────────────────────────────
    dx, dy = 100, 112
    lw.rechteck(dx - 7, dy - 5, dx + 7, dy + 5, "_")
    lw.setze(dx, dy - 3, "X")                         # der Brunnen
    haeuser = ((dx - 22, dy - 16, 10, 8, (("s", 4, 2),)),
               (dx - 8, dy - 18, 9, 8, (("s", 3, 2), ("w", 3, 2))),
               (dx + 6, dy - 17, 11, 9, (("s", 4, 3),)),
               (dx + 15, dy - 15, 8, 8, (("s", 3, 2), ("w", 3, 2))),
               (dx + 6, dy + 9, 10, 8, (("n", 4, 2), ("o", 3, 2))),
               (dx - 9, dy + 10, 8, 9, (("n", 3, 2),)),
               (dx - 22, dy + 6, 9, 8, (("o", 3, 2), ("n", 3, 2))))
    for (hx, hy, hb, hh, tueren) in haeuser:
        lw.haus(hx, hy, hb, hh, r, tueren=tueren, fenster=0.18, kaputt=0.1,
                innen=hb // 2 if hb >= 10 else None)
    for i in range(6):                                 # Gartenzaeune
        lw.setze(dx - 20 + i * 2, dy + 20, "s", nur=set('.";'))
    lw.punkt(dx, dy, "WESTDORF", "OSTDORF")

    # ── Gutshof (Nordost; gespiegelt: Gehoeft im Suedwesten) ─────────────
    gx, gy = 231, 34
    lw.rechteck(gx - 12, gy - 14, gx + 12, gy + 10, ";", nur=set('.";k'))
    lw.haus(gx - 11, gy - 13, 13, 8, r, tueren=(("s", 5, 3),), fenster=0.15, innen=6)    # Wohnhaus
    lw.haus(gx + 3, gy - 14, 9, 11, r, tueren=(("w", 4, 3), ("s", 3, 3)), kaputt=0.12)  # Scheune
    for i in range(0, 8, 2):                                                           # Heuballen
        lw.setze(gx - 8 + i, gy + 5, "h")
        lw.setze(gx - 8 + i, gy + 6, "h")
    lw.setze(gx + 9, gy + 7, "w")
    for x in range(gx - 13, gx + 14):                                                  # Hofmauer, offen
        if not (gx - 3 <= x <= gx + 3):
            lw.setze(x, gy + 11, "s", nur=set('.";:'))
    lw.punkt(gx, gy + 1, "GUTSHOF", "GEHÖFT")

    # ── Basen ───────────────────────────────────────────────────────────
    lw.basis(0, 19, 38, "NORDLAGER", "buggy 1 0, krad 1 0, funkwagen 1 1, tragschrauber 1 2", r,
             tore=("o", "s"), gegen_name="SÜDLAGER")
    lw.basis(0, 18, 104, "HAUPTLAGER",
             "buggy 1 0, panzerwagen 1 0, trosswagen 1 0, flakwagen 1 1, panzer 1 2, werfer 1 3", r,
             tore=("o", "n", "s"), gegen_name="HAUPTLAGER")
    # Direkt bei BLAU gebaut (Tore aus seiner Sicht: Westen ist vorn);
    # gespiegelt ergibt es das Suedlager von ROT.
    lw.basis(1, 320, 37, "NORDLAGER", "buggy 1 0, krad 1 0, trosswagen 1 1, jagdpanzer 1 2, spulenwagen 1 2", r,
             tore=("w", "s"), gegen_name="SÜDLAGER")
    # Fahrzeuge fuer die anderen Spielarten (dort stehen sie fest).
    for (fx, fy, z) in ((34, 100, "F"), (34, 108, "F"), (36, 44, "L"), (36, 112, "P")):
        lw.setze(fx, fy, z)

    # ── Wege fuer die Bots ──────────────────────────────────────────────
    # Von jeder Basis zu den Punkten, entlang der Bahnen, durch Wald und
    # Furten - die Front waehlt daraus, wer welchen Weg nimmt.
    nb = (bruecke_n[0], bruecke_n[1])
    lw.weg([(34, 38), (60, 42), (96, 40), (112, 38), (nb[0] - 14, 39), nb,
            (nb[0] + 16, 37), (200, 34), (231, 35), (262, 30), (305, 37)])          # Nordbahn
    lw.weg([(33, 104), (60, 106), (84, 112), (100, 112), (124, 110), (146, 106),
            (160, 103), (169, 97), (179, 98), (193, 104), (215, 99), (239, 97), (306, 105)])  # Mitte
    lw.weg([(40, 38), (42, 60), (42, 82), (40, 104), (42, 126), (42, 150), (40, 172)])   # hinten
    lw.weg([(100, 112), (106, 90), (112, 62), (112, 38)])                             # Dorf - Kapelle
    lw.weg([(112, 38), (96, 58), (84, 72), (62, 84), (40, 104)])                      # durch den Nordwald
    lw.weg([(100, 112), (124, 96), (144, 76), (int(fluss_x(70)), 70), (214, 66),
            (231, 35)])                                                               # Nordfurt
    lw.weg([(int(fluss_x(70)), 70), (214, 66), (244, 90), (239, 97)])                 # Nordfurt - Ostdorf
    lw.weg([(112, 38), (140, 52), (nb[0] - 14, 39)])                                  # Kapelle - Bruecke
    lw.weg([(146, 106), (150, 90), (int(fluss_x(70)) - 6, 72)])                       # Ufer entlang
    return lw


def als_text(lw: Leinwand) -> str:
    return lw.als_text(KOPF)


def fertig() -> Leinwand:
    lw = bauen()
    r = zufall(SAAT + 1)
    # Der Rand: Granit, davor Baeume - gewuerfelt fuer die eine Haelfte,
    # gesetzt gespiegelt (die Leinwand spiegelt jede Aenderung).
    lw.spiegeln = True
    for y in range(HOEHE):
        for x in range(BREITE):
            gx, gy = lw.gegen(x, y)
            if (y, x) > (gy, gx):
                continue
            tief = min(x, y, BREITE - 1 - x, HOEHE - 1 - y)
            if tief < 3 or (tief < 6 and r.random() < 0.3 * (6 - tief) / 3):
                lw.setze(x, y, "r")
            elif tief <= 7 and lw.k[y][x] in '."' and r.random() < 0.16 * (8 - tief) / 4:
                lw.setze(x, y, "k")
    lw.wege_freilegen()
    lw.erreichbar_machen((40, 104))
    lw.pruefen()
    return lw


if __name__ == "__main__":
    ziel = Path("karten/flusstal.txt")
    ziel.write_text(als_text(fertig()), encoding="utf-8")
    print("geschrieben:", ziel)
