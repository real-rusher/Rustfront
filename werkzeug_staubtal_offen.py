# -*- coding: utf-8 -*-
"""
Erzeugt karten/staubtal_offen.txt - STAUBTAL - OFFEN (seit 0.34.96).

Gewuenscht: eine zweite Staubtal-Karte "mit viel mehr freien Flaechen,
sodass Fahrzeuge nutzbarer sind". Eine Ebene, offene Wueste mit Pisten,
dazwischen nur leichte Deckung: Felsnasen, kleine Ruinen mit breiten
Toren, Sandsackstellungen, Faesser und Kakteen. Links die Basis von ROT,
rechts die von BLAU, je mit Spawnstellen und Fahrzeugen.

Wie bei STAUBTAL: die Datei ist genau die Ausgabe dieses Werkzeugs - wer
die Karte aendern will, aendert hier (tests/test_pruefung.py prueft das).

    python werkzeug_staubtal_offen.py
"""
from __future__ import annotations

import random
from collections import deque
from pathlib import Path

BREITE, HOEHE = 300, 200
SAAT = 9601

KOPF = [
    "# STAUBTAL - OFFEN - die grosse Wueste fuer Fahrzeuge (seit 0.34.96).",
    "# Erzeugt mit werkzeug_staubtal_offen.py (nicht von Hand aendern - neu",
    "# erzeugen). 300 x 200 Kacheln, eine Ebene, viel freie Flaeche.",
    "# Zeichen wie STAUBTAL: . Sand  : Piste  ; Kies  \" Gestruepp",
    "#   # Mauer  r Fels  b Brocken  s Sandsack  h Holzkiste  X Fass",
    "#   k Kaktus  w Schrott  Z Spawnstelle  F Buggy  P Panzer  L Panzerwagen",
    "",
    "name: STAUBTAL - OFFEN",
    "satz: wueste",
    "kreise: A",
    "",
]

FEST = set("#rbshXkw")


def _frei(k, x, y, rand=0):
    return all(0 <= x + dx < BREITE and 0 <= y + dy < HOEHE and k[y + dy][x + dx] not in FEST
               for dx in range(-rand, rand + 1) for dy in range(-rand, rand + 1))


def bauen() -> list:
    r = random.Random(SAAT)
    k = [["."] * BREITE for _ in range(HOEHE)]
    # Boden: Flecken aus Kies und Gestruepp.
    for _ in range(260):
        cx, cy = r.randrange(BREITE), r.randrange(HOEHE)
        art = r.choice((";", ";", '"'))
        rad = r.randint(2, 6)
        for y in range(cy - rad, cy + rad + 1):
            for x in range(cx - rad, cx + rad + 1):
                if 0 <= x < BREITE and 0 <= y < HOEHE and (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad \
                        and r.random() < 0.7:
                    k[y][x] = art
    # Pisten: eine lange von West nach Ost, zwei schraeg, eine Nord-Sued.
    def piste(punkte, breit=3):
        for (x0, y0), (x1, y1) in zip(punkte, punkte[1:]):
            n = max(abs(x1 - x0), abs(y1 - y0))
            for i in range(n + 1):
                x = round(x0 + (x1 - x0) * i / n)
                y = round(y0 + (y1 - y0) * i / n)
                for dy in range(-breit // 2, breit // 2 + 1):
                    for dx in range(-breit // 2, breit // 2 + 1):
                        if 0 <= x + dx < BREITE and 0 <= y + dy < HOEHE:
                            k[y + dy][x + dx] = ":"
    piste([(8, 100), (70, 96), (150, 102), (230, 98), (292, 100)], 4)
    piste([(20, 40), (90, 60), (150, 100), (210, 140), (280, 160)])
    piste([(20, 160), (90, 140), (150, 100), (210, 60), (280, 40)])
    piste([(150, 10), (146, 60), (150, 100), (154, 150), (150, 190)])

    basis_links, basis_rechts, mitte = (24, 100), (276, 100), (150, 100)

    def weit_weg(x, y, rand):
        return all(abs(x - bx) > rand or abs(y - by) > rand
                   for bx, by in (basis_links, basis_rechts, mitte))

    # Felsnasen: einzelne Blobs, nie auf der Hauptpiste.
    for _ in range(46):
        cx, cy = r.randrange(30, BREITE - 30), r.randrange(12, HOEHE - 12)
        if not weit_weg(cx, cy, 22) or abs(cy - 100) < 6:
            continue
        rad = r.randint(2, 5)
        for y in range(cy - rad, cy + rad + 1):
            for x in range(cx - rad - 1, cx + rad + 2):
                if (x - cx) ** 2 * 0.7 + (y - cy) ** 2 <= rad * rad + r.random() * 3:
                    k[y][x] = "r"
    # Kleine Ruinen: offene Mauerecken mit breiten Luecken.
    for _ in range(26):
        x0, y0 = r.randrange(36, BREITE - 46), r.randrange(14, HOEHE - 24)
        if not weit_weg(x0 + 4, y0 + 4, 20) or abs(y0 + 4 - 100) < 10:
            continue
        b, h = r.randint(6, 10), r.randint(5, 8)
        for x in range(x0, x0 + b):
            for y in (y0, y0 + h):
                if r.random() < 0.6 and not (b // 2 - 2 <= x - x0 <= b // 2 + 1):
                    k[y][x] = "#"
        for y in range(y0, y0 + h + 1):
            for x in (x0, x0 + b - 1):
                if r.random() < 0.55 and not (h // 2 - 1 <= y - y0 <= h // 2 + 1):
                    k[y][x] = "#"
        k[y0 + h // 2][x0 + b // 2] = r.choice("hXw")
    # Sandsackstellungen, kurze Reihen.
    for _ in range(40):
        x, y = r.randrange(30, BREITE - 30), r.randrange(10, HOEHE - 10)
        if not weit_weg(x, y, 10):
            continue
        quer = r.random() < 0.5
        for i in range(r.randint(3, 6)):
            xx, yy = (x + i, y) if quer else (x, y + i)
            if 0 < xx < BREITE - 1 and 0 < yy < HOEHE - 1:
                k[yy][xx] = "s"
    # Kleinkram, einzeln.
    for _ in range(320):
        x, y = r.randrange(6, BREITE - 6), r.randrange(6, HOEHE - 6)
        if weit_weg(x, y, 8) and k[y][x] not in ":":
            k[y][x] = r.choice("kkbbXw")
    # Rand: Fels, unregelmaessig.
    for y in range(HOEHE):
        for x in range(BREITE):
            tief = min(x, y, BREITE - 1 - x, HOEHE - 1 - y)
            if tief < 3 or (tief < 6 and r.random() < 0.35 * (6 - tief) / 3):
                k[y][x] = "r"

    # Basen und Mitte: frei raeumen, Spawnstellen und Fahrzeuge.
    def raeumen(cx, cy, rad):
        for y in range(cy - rad, cy + rad + 1):
            for x in range(cx - rad, cx + rad + 1):
                if 4 <= x < BREITE - 4 and 4 <= y < HOEHE - 4 and k[y][x] in FEST:
                    k[y][x] = "."
    for c in (basis_links, basis_rechts, mitte):
        raeumen(c[0], c[1], 14)
    for seite, (bx, by) in ((1, basis_links), (-1, basis_rechts)):
        for i, dy in enumerate((-18, -10, -3, 4, 11, 18, -24, 24)):
            k[by + dy][bx + seite * (2 + (i % 3) * 3)] = "Z"
        k[by - 7][bx + seite * 12] = "P"
        k[by + 7][bx + seite * 12] = "L"
        k[by - 2][bx + seite * 14] = "F"
        k[by + 2][bx + seite * 14] = "F"
        # Sandsaecke als kleine Basismauer, mit breiten Durchfahrten.
        for dy in range(-20, 21):
            if abs(dy) > 6 and dy % 7 not in (0, 1, 2):
                k[by + dy][bx + seite * 20] = "s"
    k[mitte[1]][mitte[0]] = "A"

    # Alles, was man vom Start aus nicht erreicht, wird Fels.
    start = basis_links
    da = [[False] * BREITE for _ in range(HOEHE)]
    offen = deque([start])
    da[start[1]][start[0]] = True
    while offen:
        x, y = offen.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < BREITE and 0 <= ny < HOEHE and not da[ny][nx] and k[ny][nx] not in FEST:
                da[ny][nx] = True
                offen.append((nx, ny))
    for y in range(HOEHE):
        for x in range(BREITE):
            if k[y][x] not in FEST and not da[y][x]:
                k[y][x] = "r"
    return k


def als_text(k) -> str:
    zeilen = ["".join(z) for z in k]
    return "\n".join(KOPF) + "\n--- ebene 0 ---\n" + "\n".join(zeilen) + "\n"


if __name__ == "__main__":
    ziel = Path("karten/staubtal_offen.txt")
    ziel.write_text(als_text(bauen()), encoding="utf-8")
    print("geschrieben:", ziel)
