"""Erzeugt STAUBTAL, die grosse Wuestenkarte - seit 0.34.6 von Grund auf neu.

    python werkzeug_staubtal.py [ziel]        # Vorgabe: karten/staubtal.txt

Bis 0.34 war STAUBTAL aus Rechtecken gebaut: Plateaus als Kaesten, Deckung
als Fassreihen von zwanzig Stueck. Gemeldet: "Bereiche, wo 50 verschiedene
Faesser nebeneinander stehen" - es sollte aussehen wie von Hand gebaut,
sehr detailliert, und dabei gut spielbar bleiben.

Darum jetzt so, wie man eine Karte von Hand baut, nur dass die Hand ein
Programm ist:

* Die grosse Form ist gezeichnet. Jedes Plateau ist ein Vieleck mit von
  Hand gesetzten Ecken - Buchten, Nasen, ein Grat -, die Kanten leicht
  aufgeraut. Wo ein Plateau an den Kartenrand stoesst, geht es in die
  Schluchtwand ueber, statt einen Gang davor zu lassen.
* Die Orte sind gebaut: Westdorf, die Kreuzung um A, die Funkstation um B,
  das Fort um C, Steinbruch, Ranch, Schrottplatz, ein Flugzeugwrack auf der
  Tafel. Haeuser haben Dielen, Tueren, Kisten an der Wand, manche sind
  eingefallen.
* Dazwischen waechst Natur, aber nicht gleichmaessig: Felsnasen mit
  Brocken und Geroell davor, Kakteen, Gestruepp, Geroell am Fuss der
  Waende, ein trockenes Bachbett. Pisten verbinden die Orte.
* Faesser nur in kleinen Gruppen, dort, wo jemand sie abgestellt hat.
* Alles ist fest gesaet (SAAT): jedes Mal kommt dieselbe Datei heraus.

Am Ende prueft der Generator selbst, was die Tests pruefen (alles
erreichbar, nichts unter den Plateaus, Aufzuege frei, die Kreise frei),
und repariert Kleinigkeiten, statt eine kaputte Karte zu schreiben.
Danach trotzdem `python tests/test_pruefung.py` laufen lassen.

Kein Kartenwissen im Spiel haengt an diesem Werkzeug: es schreibt nur die
Textdatei. Gastgeber und Gast brauchen dieselbe Datei (dieselbe Version).
"""
from __future__ import annotations

import math
import random
from collections import deque
from functools import lru_cache
from pathlib import Path

B, H = 300, 240
SAAT = 35

# Zeichen der Kartendatei (dustfront/world.py, ZEICHEN).
LOCH, SAND, WAND, FASS = "~", ".", "#", "X"
FELS, BROCKEN, SACK, KISTE, KAKTUS, SCHROTT = "r", "b", "s", "h", "k", "w"
PISTE, KIES, PFLASTER, BUSCH, DIELEN = ":", ";", "_", '"', "="
HOCH, RUNTER = "^", "v"

FEST = frozenset(WAND + FASS + FELS + BROCKEN + SACK + KISTE + KAKTUS + SCHROTT)
TREPPEN = frozenset(HOCH + RUNTER)
# Worauf Natur und Kleinkram gestellt werden duerfen. Auf Piste, Pflaster
# und Dielen nicht - ein Weg, auf dem ein Kaktus steht, ist kein Weg.
NATURBODEN = frozenset(SAND + KIES + BUSCH)
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))

# Die drei Kreise (HUEGEL): Name, Ebene, Mitte.
KREISE = (("A", 0, 150, 137), ("B", 1, 150, 48), ("C", 0, 150, 197))


# ══════════════════════════════════════════════════ Formen

@lru_cache(maxsize=None)
def _wert(saat: int, i: int) -> float:
    return random.Random(saat * 1000003 + i).uniform(-1.0, 1.0)


def rauschen(saat: int, t: float) -> float:
    """Glattes Rauschen in [-1, 1]: Zufallswerte an ganzen Stellen,
    dazwischen weich uebergeblendet. Fuer Kanten, Breiten, Dicken."""
    i = math.floor(t)
    f = t - i
    w = (1 - math.cos(f * math.pi)) / 2
    return _wert(saat, i) * (1 - w) + _wert(saat, i + 1) * w


def rauschen2(saat: int, x: float, y: float) -> float:
    """Glattes Rauschen in [-1, 1] ueber die Flaeche. Damit wird Natur in
    Gruppen gesetzt: hier ein Felsfeld, dort eine Kakteenflur, dazwischen
    leerer Sand - wie gewachsen, nicht wie gestreut."""
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    wx = fx * fx * (3 - 2 * fx)
    wy = fy * fy * (3 - 2 * fy)

    def w(a, b):
        return _wert(saat, a * 7919 + b * 104729)

    oben = w(ix, iy) * (1 - wx) + w(ix + 1, iy) * wx
    unten = w(ix, iy + 1) * (1 - wx) + w(ix + 1, iy + 1) * wx
    return oben * (1 - wy) + unten * wy


def dichte(saat: int, x: float, y: float, groesse=22.0) -> float:
    """0 bis 1: wie dicht etwas an dieser Stelle waechst (zwei Lagen
    Rauschen, die grobe bestimmt die Gebiete)."""
    v = (rauschen2(saat, x / groesse, y / groesse) * 0.75
         + rauschen2(saat + 1, x / (groesse / 3), y / (groesse / 3)) * 0.25)
    return max(0.0, min(1.0, (v + 0.15) * 1.6))


def aufrauen(punkte, saat, staerke=1.3, abstand=3.0):
    """Zwischen die gesetzten Ecken Punkte legen und quer zur Kante leicht
    verschieben. Die gesetzten Ecken bleiben, wo sie sind - sie sind die
    Zeichnung, das Rauschen ist nur die Felsstruktur dazwischen."""
    raus = []
    t = 0.0
    n = len(punkte)
    for k in range(n):
        (x1, y1), (x2, y2) = punkte[k], punkte[(k + 1) % n]
        laenge = math.hypot(x2 - x1, y2 - y1)
        schritte = max(1, int(laenge / abstand))
        nx, ny = (y2 - y1) / max(laenge, 1e-6), -(x2 - x1) / max(laenge, 1e-6)
        for s in range(schritte):
            f = s / schritte
            v = 0.0 if s == 0 else rauschen(saat, t * 0.4) * staerke
            raus.append((x1 + (x2 - x1) * f + nx * v, y1 + (y2 - y1) * f + ny * v))
            t += 1
    return raus


def vieleck(punkte) -> set:
    """Alle Kacheln, deren Mitte im Vieleck liegt (Zeilen abtasten)."""
    menge = set()
    ys = [p[1] for p in punkte]
    n = len(punkte)
    for y in range(max(0, int(math.floor(min(ys)))), min(H, int(math.ceil(max(ys))) + 1)):
        cy = y + 0.5
        schnitte = []
        for k in range(n):
            (x1, y1), (x2, y2) = punkte[k], punkte[(k + 1) % n]
            if (y1 <= cy < y2) or (y2 <= cy < y1):
                schnitte.append(x1 + (cy - y1) * (x2 - x1) / (y2 - y1))
        schnitte.sort()
        for a, b in zip(schnitte[0::2], schnitte[1::2]):
            for x in range(max(0, int(math.ceil(a - 0.5))),
                           min(B - 1, int(math.floor(b - 0.5))) + 1):
                menge.add((x, y))
    return menge


def glaetten(menge: set, runden: int = 2) -> set:
    """Einzelne Zacken und Kerben weg. Eine Klippe, die jede Kachel vor-
    und zurueckspringt, sieht aus wie ein Fehler, nicht wie Fels."""
    for _ in range(runden):
        pruefen = set(menge)
        for (x, y) in menge:
            for dx, dy in N4:
                pruefen.add((x + dx, y + dy))
        neu = set(menge)
        for (x, y) in pruefen:
            if not (0 <= x < B and 0 <= y < H):
                continue
            n = sum((x + dx, y + dy) in menge for dx, dy in N4)
            if (x, y) in menge and n <= 1:
                neu.discard((x, y))
            elif (x, y) not in menge and n >= 3:
                neu.add((x, y))
        menge = neu
    return menge


def klumpen(cx, cy, r, rnd, rauh=0.28) -> set:
    """Eine unregelmaessig runde Form: Felsnase, Gestruepp, Kiesfleck.
    Gestreckt und gedreht - nicht jede Felsnase ist ein Kreis."""
    wellen = [(k, rnd.uniform(0, rauh) / k ** 0.5, rnd.uniform(0, math.tau))
              for k in (2, 3, 5)]
    streck = rnd.uniform(0.75, 1.35)
    dreh = rnd.uniform(0, math.pi)
    c, s = math.cos(dreh), math.sin(dreh)
    menge = set()
    weit = int(r * 1.9) + 2
    for y in range(int(cy) - weit, int(cy) + weit + 1):
        for x in range(int(cx) - weit, int(cx) + weit + 1):
            if not (0 <= x < B and 0 <= y < H):
                continue
            dx, dy = x - cx, y - cy
            u = (dx * c + dy * s) / streck
            v = -dx * s + dy * c
            w = math.atan2(v, u)
            grenze = r * (1 + sum(a * math.sin(k * w + p) for k, a, p in wellen))
            if math.hypot(u, v) <= grenze:
                menge.add((x, y))
    return menge


def kurve(punkte, dichte=3.0):
    """Catmull-Rom durch die Punkte: Wege biegen, sie knicken nicht."""
    p = [punkte[0]] + list(punkte) + [punkte[-1]]
    raus = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        n = max(1, int(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) * dichte))
        for s in range(n):
            t = s / n
            t2, t3 = t * t, t * t * t
            raus.append(tuple(
                0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t
                       + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                       + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3)
                for j in (0, 1)))
    raus.append(tuple(punkte[-1]))
    return raus


def band(punkte, breite, saat, schwanken=0.5) -> set:
    """Ein Weg oder Bachbett als Kachelmenge: Scheiben entlang der Kurve,
    die Breite schwankt ein wenig. Punkte sind Kachelmitten."""
    menge = set()
    for n, (x, y) in enumerate(kurve(punkte)):
        x, y = x + 0.5, y + 0.5
        r = max(0.8, breite / 2 + rauschen(saat, n * 0.04) * schwanken)
        weit = int(r) + 1
        for ty in range(int(y) - weit, int(y) + weit + 1):
            for tx in range(int(x) - weit, int(x) + weit + 1):
                if (0 <= tx < B and 0 <= ty < H
                        and (tx + .5 - x) ** 2 + (ty + .5 - y) ** 2 <= r * r):
                    menge.add((tx, ty))
    return menge


def scheibe(cx, cy, r) -> set:
    return {(x, y) for y in range(int(cy - r) - 1, int(cy + r) + 2)
            for x in range(int(cx - r) - 1, int(cx + r) + 2)
            if 0 <= x < B and 0 <= y < H and (x - cx) ** 2 + (y - cy) ** 2 <= r * r}


def rechteck(x0, y0, x1, y1) -> set:
    return {(x, y) for y in range(max(0, y0), min(H, y1 + 1))
            for x in range(max(0, x0), min(B, x1 + 1))}


def dehnen(menge: set, r: int) -> set:
    raus = set(menge)
    for (x, y) in menge:
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                raus.add((x + dx, y + dy))
    return raus


# ══════════════════════════════════════════════════ Die Karte

class Karte:
    def __init__(self):
        self.e = [[[SAND] * B for _ in range(H)],
                  [[LOCH] * B for _ in range(H)],
                  [[LOCH] * B for _ in range(H)]]
        # Hier kommt nichts Festes hin: Aufzugvorplaetze, Tueren, Tore,
        # die Kreise. Und hier waechst keine Natur: was gebaut ist.
        self.frei = [set(), set(), set()]
        self.bebaut = [set(), set(), set()]
        self.rnd = random.Random(SAAT)
        self.aufzuege = []          # (ebene unten, x, y, seite)
        self.tafel1 = set()
        self.tafel2 = set()

    def an(self, i, x, y):
        if 0 <= x < B and 0 <= y < H:
            return self.e[i][y][x]
        return None

    def setzen(self, i, x, y, z, nur=None) -> bool:
        if 0 <= x < B and 0 <= y < H and (nur is None or self.e[i][y][x] in nur):
            self.e[i][y][x] = z
            return True
        return False

    def malen(self, i, menge, z, nur=None) -> None:
        for (x, y) in menge:
            self.setzen(i, x, y, z, nur)

    def stellen(self, i, x, y, z, auf=NATURBODEN) -> bool:
        """Ein Hindernis hinstellen - nur auf Naturboden und nicht dort,
        wo etwas freigehalten wird."""
        if (x, y) in self.frei[i]:
            return False
        return self.setzen(i, x, y, z, auf)

    def begehbar(self, i, x, y) -> bool:
        z = self.an(i, x, y)
        return z is not None and z != LOCH and z not in FEST

    def bauen_auf(self, i, menge, rand=3) -> None:
        self.bebaut[i] |= dehnen(menge, rand)


# ══════════════════════════════════════════════════ 1. Gelaende

# Die Tafeln, von Hand gezeichnet (Kachelkoordinaten, im Uhrzeigersinn).
# Punkte ausserhalb der Karte: dort geht die Tafel in die Schluchtwand ueber.

# Die lange Tafel im Norden (Ebene 1). Ihr Suedrand ist die Front zum
# Tal: Buchten, Nasen, eine Rinne bei x 120, aus der das Bachbett kommt.
TAFEL_NORD = (
    (-6, -6), (224, -6), (224, 96),
    (214, 95), (208, 90), (201, 87), (194, 86), (186, 86), (180, 83), (172, 80),
    (165, 83), (158, 87), (151, 89), (144, 87), (138, 83), (131, 79), (125, 79),
    (121, 83), (117, 80), (112, 82), (105, 85), (97, 86), (90, 86), (83, 86),
    (76, 88), (69, 90), (62, 87), (56, 84), (50, 80), (44, 79), (38, 81),
    (32, 85), (27, 88), (20, 88), (14, 88), (8, 90), (2, 93), (-6, 95),
)
# Die hohe Tafel im Nordosten (Ebene 2), ueber ihrem eigenen Sockel.
TAFEL_HOCH = (
    (214, -6), (306, -6), (306, 118), (299, 126), (292, 134), (283, 140),
    (272, 144), (262, 146), (252, 146), (240, 146), (231, 143), (225, 136),
    (220, 126), (217, 113), (218, 101), (216, 90), (214, 78), (215, 64),
    (217, 52), (216, 40), (216, 28), (216, 16), (214, 6),
)
# Die Tafel im Suedwesten, an Schluchtwand West und Sued gelehnt.
TAFEL_SUEDWEST = (
    (-6, 146), (6, 148), (14, 150), (22, 150), (30, 150), (38, 150), (45, 153),
    (50, 159), (53, 167), (55, 176), (54, 186), (52, 195), (55, 204), (56, 213),
    (53, 222), (48, 230), (42, 236), (38, 246), (-6, 246),
)
# Die kleine Tafel im Suedosten, frei im Tal.
TAFEL_SUEDOST = (
    (212, 170), (218, 166), (226, 165), (234, 166), (248, 165), (256, 165),
    (264, 166), (269, 171), (270, 180), (268, 190), (266, 200), (260, 207),
    (250, 210), (240, 211), (232, 211), (222, 211), (216, 207), (212, 198),
    (210, 188), (211, 178),
)
# Der Grat von der Suedost-Tafel hinauf an den Fuss der hohen Tafel.
GRAT = (
    (236, 138), (246, 138), (246, 147), (244, 154), (246, 161), (247, 168),
    (235, 168), (236, 161), (234, 154), (236, 147),
)

# Aufzuege: (Tafel, Seite, ungefaehre Stelle). Die Seite ist die Kante, in
# der die Tuer liegt. Vom Sand hinauf nur an Nord- und Suedkanten: oben
# muss links und rechts der Kabine Boden sein (Test "freier Ausstieg").
AUFZUEGE = (
    ("nord", "sued", 22),      # E1 Westdorf
    ("nord", "sued", 90),      # E2 an der Rinne
    ("nord", "sued", 192),     # E3 Ost
    ("suedwest", "nord", 30),  # E4 Westdorf Sued
    ("suedost", "sued", 226),  # E5 am Fort
    ("suedost", "nord", 258),  # E6 Ranch
    ("hoch", "west", 30),      # U1 von der langen Tafel hinauf
    ("hoch", "sued", 240),     # U2 vom Grat hinauf
)


def _kante_glaetten(f: set, seite: str, wo: int, breite: int = 4):
    """Um einen Aufzug herum die Kante gerade ziehen. Gibt (x, y) der
    Kantenkachel zurueck, in der die Tuer liegt."""
    if seite in ("sued", "nord"):
        x = wo
        spalte = sorted(y for (a, y) in f if a == x)
        if seite == "sued":
            # die suedlichste Kachel des zusammenhaengenden Stuecks
            yk = spalte[-1]
            for c in range(x - breite, x + breite + 1):
                for y in range(yk - 10, yk + 1):
                    f.add((c, y))
                for y in range(yk + 1, yk + 12):
                    f.discard((c, y))
        else:
            yk = spalte[0]
            for c in range(x - breite, x + breite + 1):
                for y in range(yk, yk + 11):
                    f.add((c, y))
                for y in range(yk - 11, yk):
                    f.discard((c, y))
        return x, yk
    y = wo
    zeile = sorted(x for (x, b) in f if b == y)
    xk = zeile[0]
    for r in range(y - breite, y + breite + 1):
        for x in range(xk, xk + 11):
            f.add((x, r))
        for x in range(xk - 11, xk):
            f.discard((x, r))
    return xk, y


def gelaende(k: Karte) -> None:
    nord = glaetten(vieleck(aufrauen(TAFEL_NORD, 11)))
    hoch = glaetten(vieleck(aufrauen(TAFEL_HOCH, 12)))
    suedwest = glaetten(vieleck(aufrauen(TAFEL_SUEDWEST, 13)))
    suedost = glaetten(vieleck(aufrauen(TAFEL_SUEDOST, 14)))
    grat = glaetten(vieleck(aufrauen(GRAT, 15, staerke=0.8)), 1)
    tafeln = {"nord": nord, "hoch": hoch, "suedwest": suedwest, "suedost": suedost}

    for name, seite, wo in AUFZUEGE:
        x, y = _kante_glaetten(tafeln[name], seite, wo)
        k.aufzuege.append((1 if name == "hoch" else 0, x, y, seite))

    k.tafel2 = hoch
    k.tafel1 = nord | suedwest | suedost | grat | hoch

    # Schluchtwand: so dick, wie das Rauschen will, mit ein paar Felsnasen.
    def dicke(saat, t, lo, hi):
        f = 0.5 + 0.5 * rauschen(saat, t * 0.06) + 0.25 * rauschen(saat + 7, t * 0.22)
        return lo + (hi - lo) * max(0.0, min(1.0, f))

    rand0 = set()
    for y in range(H):
        for x in range(B):
            if (x < dicke(21, y, 1.5, 7.5) or B - 1 - x < dicke(22, y, 1.5, 7.5)
                    or y < dicke(23, x, 1.5, 6.5) or H - 1 - y < dicke(24, x, 1.5, 7.5)):
                rand0.add((x, y))
    for cx, cy, r in ((0, 120, 7), (2, 104, 4), (60, 239, 5), (128, 239, 4),
                      (176, 239, 3.5), (205, 239, 6), (299, 172, 7),
                      (299, 196, 4), (299, 222, 5.5), (246, 239, 4)):
        rand0 |= klumpen(cx, cy, r, k.rnd)

    rand1 = set()
    rand2 = set()
    for y in range(H):
        for x in range(B):
            d1 = min(x, y, H - 1 - y)
            if d1 < dicke(31, x + y, 1.5, 4.5):
                rand1.add((x, y))
            d2 = min(y, B - 1 - x)
            if d2 < dicke(32, x + y, 1.5, 4.0):
                rand2.add((x, y))

    for y in range(H):
        for x in range(B):
            p = (x, y)
            if p in k.tafel1 or p in rand0:
                k.e[0][y][x] = FELS
            if p in hoch:
                k.e[1][y][x] = FELS
                k.e[2][y][x] = FELS if p in rand2 else SAND
            elif p in k.tafel1:
                k.e[1][y][x] = FELS if p in rand1 else SAND


# ══════════════════════════════════════════════════ 2. Aufzuege

def aufzuege(k: Karte) -> None:
    """Tuer und Kabine setzen, Vorplatz und Ausstieg freihalten.

    Unten: ein Vorplatz von fuenf auf vier Kacheln vor der Tuer. Oben: die
    Kanten links und rechts der Kabine und eine Gasse sieben Kacheln weit
    hinein - aus der kommt man gerade heraus, Gegner wie Spieler."""
    for (unten, x, y, seite) in k.aufzuege:
        oben = unten + 1
        k.e[unten][y][x] = HOCH
        k.e[oben][y][x] = RUNTER
        if seite == "west":
            vor, hinein = (-1, 0), (1, 0)
        elif seite == "sued":
            vor, hinein = (0, 1), (0, -1)
        else:
            vor, hinein = (0, -1), (0, 1)
        qx, qy = abs(vor[1]), abs(vor[0])       # quer zur Laufrichtung
        for t in range(1, 6):
            for q in range(-2, 3):
                k.frei[unten].add((x + vor[0] * t + qx * q, y + vor[1] * t + qy * q))
        for t in range(0, 9):
            for q in range(-2 if t <= 2 else -1, 3 if t <= 2 else 2):
                k.frei[oben].add((x + hinein[0] * t + qx * q, y + hinein[1] * t + qy * q))
        k.bauen_auf(oben, {(x + hinein[0] * t, y + hinein[1] * t) for t in range(8)}, 2)
        k.bauen_auf(unten, {(x + vor[0] * t, y + vor[1] * t) for t in range(5)}, 2)


def landeplatz(k: Karte, unten, x, y, seite) -> None:
    """Oben neben dem Ausstieg: ein Sandsacknest auf jeder Seite, etwas
    zurueckgesetzt. Man kommt heraus und hat sofort Deckung, links oder
    rechts - frueher standen dort zwei gleiche Mauerstuecke."""
    oben = unten + 1
    if seite == "west":
        hinein, quer = (1, 0), (0, 1)
    elif seite == "sued":
        hinein, quer = (0, -1), (1, 0)
    else:
        hinein, quer = (0, 1), (1, 0)
    for s in (-1, 1):
        # Ein Haken aus Sandsaecken: drei quer, zwei nach vorn
        for t, q in ((4, 3), (4, 4), (4, 5), (3, 5), (2, 5)):
            px = x + hinein[0] * t + quer[0] * q * s
            py = y + hinein[1] * t + quer[1] * q * s
            k.stellen(oben, px, py, SACK)
    # Eine Kiste und ein Fass am Rand des Platzes, nicht in der Gasse
    s = 1 if (x + y) % 2 else -1
    for t, q, z in ((6, 4, KISTE), (7, 4, KISTE), (7, 5, FASS)):
        k.stellen(oben, x + hinein[0] * t + quer[0] * q * s,
                  y + hinein[1] * t + quer[1] * q * s, z)
    # Unten: zwei Sandsaecke als Windfang neben der Tuer, ein Pfosten.
    vor = (-hinein[0], -hinein[1])
    for s in (-1, 1):
        k.stellen(unten, x + vor[0] * 1 + quer[0] * 3 * s, y + vor[1] * 1 + quer[1] * 3 * s,
                  SACK, auf=NATURBODEN | {PISTE})
        k.stellen(unten, x + vor[0] * 2 + quer[0] * 3 * s, y + vor[1] * 2 + quer[1] * 3 * s,
                  SACK, auf=NATURBODEN | {PISTE})


# ══════════════════════════════════════════════════ 3. Boden

# Pisten im Tal (Kachelmitten). Die Hauptpiste kommt aus Westdorf ueber
# die Kreuzung A und biegt um die Suedost-Tafel zum Osttor des Forts.
PISTEN_TAL = (
    ((14, 116), (30, 116), (56, 120), (80, 126), (108, 132), (132, 137),
     (150, 138), (170, 139), (190, 143), (205, 151), (211, 163), (207, 178),
     (205, 192)),
    ((90, 88), (91, 98), (96, 110), (104, 123), (110, 131)),               # E2
    ((192, 88), (190, 99), (183, 112), (171, 126), (158, 134), (151, 137)),  # E3
    ((150, 139), (150, 152), (150, 166)),                                  # A -> Fort Nord
    ((22, 91), (24, 102), (26, 116), (27, 132), (29, 146), (30, 148)),      # Westdorf
    ((96, 197), (84, 196), (72, 190), (64, 176), (68, 158), (64, 140), (58, 122)),
    ((150, 229), (148, 232), (130, 233), (110, 232), (98, 230), (91, 227)),  # Sued West
    ((150, 229), (154, 232), (180, 233), (205, 230), (216, 222), (226, 214)),
    ((226, 214), (240, 220), (256, 223), (276, 220), (286, 210), (287, 196),
     (283, 184), (276, 172), (268, 160), (258, 160), (258, 164)),
)
# Fahrspuren auf den Tafeln, schmaler.
PISTEN_TAFEL1 = (
    ((22, 82), (26, 70), (40, 60), (66, 55), (100, 52), (126, 49), (150, 49)),
    ((90, 80), (94, 68), (104, 58), (116, 52)),
    ((192, 80), (190, 70), (180, 58), (168, 51), (150, 49)),
    ((150, 49), (170, 44), (190, 38), (205, 31), (209, 30)),
    ((30, 156), (30, 168), (26, 182), (20, 194), (20, 196)),               # Suedwest
    ((226, 205), (230, 196), (238, 190)),                                  # Suedost
    ((258, 171), (252, 180), (244, 186)),
    ((240, 168), (241, 160), (240, 154)),
)
PISTEN_TAFEL2 = (
    ((223, 30), (236, 34), (250, 46), (262, 66), (262, 86)),
    ((262, 86), (256, 106), (246, 124), (240, 136)),
)
# Das Bachbett: aus der Rinne in der Nordtafel durchs Tal nach Osten, wo
# es in einer flachen Senke unter dem Grat endet. Und ein kurzes zweites
# vom Suedwest-Plateau in den Steinbruch.
BACHBETTEN = (
    ((120, 86), (117, 96), (112, 106), (116, 118), (124, 128), (130, 141),
     (133, 151), (141, 157), (152, 159), (166, 157), (180, 153), (194, 153),
     (207, 158), (218, 154), (227, 152)),
    ((56, 190), (64, 197), (74, 206), (84, 214)),
)


def boden(k: Karte) -> None:
    rnd = random.Random(SAAT + 1)
    # Gestruepp: in Flecken, und die Flecken in Gebieten - es gibt
    # Buschland und kahlen Sand, nicht ueberall ein bisschen.
    for i, anzahl in ((0, 300), (1, 190), (2, 100)):
        gesetzt = versuche = 0
        while gesetzt < anzahl and versuche < anzahl * 12:
            versuche += 1
            x, y = rnd.randrange(3, B - 3), rnd.randrange(3, H - 3)
            d = dichte(401 + i, x, y, 26.0)
            if k.an(i, x, y) != SAND or rnd.random() > d * d:
                continue
            k.malen(i, klumpen(x, y, rnd.uniform(1.0, 1.6 + 2.6 * d), rnd), BUSCH, nur={SAND})
            gesetzt += 1
    # Kiesflecken, seltener.
    for i, anzahl in ((0, 40), (1, 25), (2, 10)):
        for _ in range(anzahl):
            x, y = rnd.randrange(3, B - 3), rnd.randrange(3, H - 3)
            if k.an(i, x, y) not in (SAND, BUSCH):
                continue
            k.malen(i, klumpen(x, y, rnd.uniform(1.2, 2.8), rnd), KIES, nur={SAND, BUSCH})
    # Geroell am Fuss jeder Wand: ein Band aus Kies, mal breit, mal keins.
    for i, unten_von in ((0, k.tafel1), (1, k.tafel2)):
        for (x, y) in list(unten_von):
            for dx, dy in N4:
                for t in range(1, 4):
                    px, py = x + dx * t, y + dy * t
                    if (px, py) in unten_von:
                        break
                    if rauschen(41 + i, (px * 0.13 + py * 0.11)) > 0.15 * t:
                        k.setzen(i, px, py, KIES, nur={SAND, BUSCH})
    # Bachbetten
    for n, punkte in enumerate(BACHBETTEN):
        bett = band(punkte, 3.6 if n == 0 else 2.6, 51 + n, schwanken=1.1)
        k.malen(0, bett, KIES, nur={SAND, BUSCH})
        # Ufer: Gestruepp waechst, wo es Wasser gab
        for (x, y) in dehnen(bett, 2) - bett:
            if rnd.random() < 0.35:
                k.setzen(0, x, y, BUSCH, nur={SAND})
    # Senke am Ende des Bachbetts
    k.malen(0, klumpen(229, 152, 4.0, rnd), KIES, nur={SAND, BUSCH})
    # Pisten zuletzt: sie liegen ueber allem.
    for n, punkte in enumerate(PISTEN_TAL):
        k.malen(0, band(punkte, 3.0, 61 + n, schwanken=0.45), PISTE,
                nur={SAND, BUSCH, KIES})
    for n, punkte in enumerate(PISTEN_TAFEL1):
        k.malen(1, band(punkte, 2.2, 81 + n, schwanken=0.3), PISTE,
                nur={SAND, BUSCH, KIES})
    for n, punkte in enumerate(PISTEN_TAFEL2):
        k.malen(2, band(punkte, 2.2, 91 + n, schwanken=0.3), PISTE,
                nur={SAND, BUSCH, KIES})


# ══════════════════════════════════════════════════ 4. Gebaeude

def haus(k: Karte, i, x0, y0, x1, y1, tueren, trenn=(), kaputt=0.0,
         kisten=2, innen=DIELEN, offen=None):
    """Ein Haus: Lehmmauern, Dielen, Tueren. `trenn`: Innenwaende als
    ("x", spalte, tuer_y) oder ("y", zeile, tuer_x). `kaputt`: so viel der
    Mauer ist eingefallen (Luecke oder Schutt). `offen`: eine Seite ohne
    Mauer ("n", "s", "w", "o") - Schuppen, Stall."""
    rnd = k.rnd
    flaeche = rechteck(x0, y0, x1, y1)
    for (x, y) in flaeche:
        rand = x in (x0, x1) or y in (y0, y1)
        seite_offen = offen and ((offen == "n" and y == y0) or (offen == "s" and y == y1)
                                 or (offen == "w" and x == x0) or (offen == "o" and x == x1))
        if rand and not seite_offen:
            ecke = x in (x0, x1) and y in (y0, y1)
            if not ecke and kaputt and rnd.random() < kaputt:
                k.setzen(i, x, y, BROCKEN if rnd.random() < 0.45 else KIES)
            else:
                k.setzen(i, x, y, WAND)
        else:
            k.setzen(i, x, y, innen)
    if kaputt:
        # In einer Ruine hat der Wind Sand hereingeweht - in Verwehungen,
        # nicht Kachel fuer Kachel (das sah aus wie ein Schachbrett).
        innenflaeche = rechteck(x0 + 1, y0 + 1, x1 - 1, y1 - 1)
        for _ in range(max(1, len(innenflaeche) // 30)):
            cx, cy = rnd.randrange(x0 + 1, x1), rnd.randrange(y0 + 1, y1)
            verweht = klumpen(cx, cy, rnd.uniform(1.6, 3.2), rnd) & innenflaeche
            k.malen(i, verweht, SAND, nur={innen})
            k.malen(i, klumpen(cx, cy, 1.0, rnd) & verweht, KIES, nur={SAND})
    for art, wo, tuer in trenn:
        if art == "x":
            for y in range(y0 + 1, y1):
                k.setzen(i, wo, y, innen if abs(y - tuer) <= 0 else WAND)
            k.frei[i] |= {(wo - 1, tuer), (wo + 1, tuer), (wo, tuer)}
        else:
            for x in range(x0 + 1, x1):
                k.setzen(i, x, wo, innen if abs(x - tuer) <= 0 else WAND)
            k.frei[i] |= {(tuer, wo - 1), (tuer, wo + 1), (tuer, wo)}
    for (x, y) in tueren:
        k.setzen(i, x, y, innen)
        k.frei[i].add((x, y))
        for dx, dy in N4:
            k.frei[i].add((x + dx, y + dy))
            k.frei[i].add((x + 2 * dx, y + 2 * dy))
    # Kisten innen an die Wand, nie vor eine Tuer
    platz = [(x, y) for (x, y) in flaeche
             if x0 < x < x1 and y0 < y < y1 and k.an(i, x, y) == innen
             and (x, y) not in k.frei[i]
             and any(k.an(i, x + dx, y + dy) == WAND for dx, dy in N4)]
    rnd.shuffle(platz)
    gestellt = 0
    for (x, y) in platz:
        if gestellt >= kisten:
            break
        # nicht in eine Ecke einsperren: hoechstens eine Kiste je Nachbarschaft
        if any(k.an(i, x + dx, y + dy) in (KISTE, FASS) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
            continue
        k.setzen(i, x, y, KISTE if rnd.random() < 0.75 else FASS)
        gestellt += 1
    k.bauen_auf(i, flaeche, 2)


def faesser(k: Karte, i, x, y, anzahl, z=FASS):
    """Eine kleine Gruppe Faesser (2 bis 4), eng beieinander, wie man sie
    abstellt: nebeneinander, eins schraeg dahinter."""
    muster = ((0, 0), (1, 0), (0, 1), (1, 1))[:anzahl]
    for dx, dy in muster:
        k.stellen(i, x + dx, y + dy, z, auf=NATURBODEN | {PISTE, PFLASTER, DIELEN})


def wrack(k: Karte, i, x, y, laenge=3, quer=False, auf=NATURBODEN, breite=2) -> bool:
    """Ein Autowrack: zwei Kacheln breit, `laenge` lang. Ganz oder gar
    nicht - ein Wrack, das eine Piste halbiert, waere zwei halbe Wracks."""
    teile = [((x + a, y + b) if quer else (x + b, y + a))
             for a in range(laenge) for b in range(breite)]
    if any((px, py) in k.frei[i] or k.an(i, px, py) not in auf for (px, py) in teile):
        return False
    for (px, py) in teile:
        k.setzen(i, px, py, SCHROTT)
    k.bauen_auf(i, set(teile), 1)
    return True


def bogen(k: Karte, i, cx, cy, r, von, bis, z=SACK, auf=NATURBODEN):
    """Kacheln auf einem Kreisbogen (Grad; 0 = Osten, 90 = Sueden)."""
    gesetzt = set()
    schritte = max(4, int(abs(bis - von) / 360 * math.tau * r * 2))
    for s in range(schritte + 1):
        w = math.radians(von + (bis - von) * s / schritte)
        p = (int(round(cx + math.cos(w) * r)), int(round(cy + math.sin(w) * r)))
        if p not in gesetzt:
            gesetzt.add(p)
            k.stellen(i, p[0], p[1], z, auf=auf)
    return gesetzt


def platz(k: Karte, i, cx, cy, r):
    """Ein gepflasterter Platz, dessen Rand ausfranst: aussen fehlen
    Steine, Sand liegt darueber. Eine gestochen runde Scheibe aus
    Kacheln waere eine Treppe im Kreis."""
    for (x, y) in scheibe(cx, cy, r + 1.5):
        d = math.hypot(x - cx, y - cy)
        if d <= r - 1 or k.rnd.random() < max(0.0, (r + 1.5 - d) / 2.5):
            k.setzen(i, x, y, PFLASTER, nur=NATURBODEN | {PISTE})


def pfad(k: Karte, i, punkte, breite=1.7):
    """Ein Trampelpfad: eine schmale Piste von einer Tuer zum Weg. Wo
    Leute wohnen, laufen sie immer denselben Weg - das sieht man."""
    k.malen(i, band(punkte, breite, 7 + int(punkte[0][0]), schwanken=0.25), PISTE,
            nur=NATURBODEN)


def westdorf(k: Karte):
    """Ein Dorf an der Piste, Bretterstege vor den Haeusern."""
    haus(k, 0, 33, 95, 45, 107, [(33, 101), (39, 107)], trenn=[("x", 40, 100)], kisten=3)
    k.malen(0, rechteck(31, 95, 32, 107), DIELEN, nur={SAND, BUSCH, KIES, PISTE})   # Steg
    haus(k, 0, 13, 95, 22, 105, [(22, 100)], kisten=3)                               # Laden
    k.malen(0, rechteck(23, 96, 23, 104), DIELEN, nur={SAND, BUSCH, KIES})
    haus(k, 0, 34, 121, 43, 130, [(34, 126)], trenn=[("y", 125, 39)], kisten=2)      # Sheriff
    k.malen(0, rechteck(32, 121, 33, 130), DIELEN, nur={SAND, BUSCH, KIES, PISTE})
    haus(k, 0, 12, 123, 21, 136, [(17, 123)], kaputt=0.22, kisten=0)                 # Kapelle
    haus(k, 0, 36, 137, 43, 143, [], offen="w", kisten=1)                            # Schmiede
    faesser(k, 0, 40, 135, 2)
    faesser(k, 0, 24, 107, 2)
    for x, y in ((48, 110), (51, 110), (48, 113), (51, 113)):                        # Wasserturm
        k.setzen(0, x, y, WAND)
    k.malen(0, {(49, 111), (50, 112), (52, 114)}, SCHROTT)
    k.bauen_auf(0, rechteck(47, 109, 53, 115), 2)
    wrack(k, 0, 15, 139, 3)                                                          # Wagen
    faesser(k, 0, 19, 142, 2)
    for x, y in ((45, 117), (46, 117), (12, 117)):
        k.stellen(0, x, y, KISTE)


def kreuzung_a(k: Karte):
    """Hotzone 1 (A): die Kreuzung im offenen Feld. Frei um den Kreis,
    Deckung in 15 bis 25 Kacheln: Tankstelle, Buswrack, Felsnase,
    Wasserturm, zwei Kontrollposten aus Sandsaecken."""
    ax, ay = 150, 137
    k.malen(0, scheibe(ax, ay, 4.5), PISTE, nur={SAND, BUSCH, KIES})
    k.frei[0] |= scheibe(ax, ay, 6)
    # Am Rand des Platzes Kleinigkeiten, damit er nicht leer gefegt wirkt:
    # ein Wegweiser (Kiste mit Pfahl), zwei Brocken, ein Kaktus.
    for x, y, z in ((156, 132, KISTE), (143, 131, BROCKEN), (144, 130, BROCKEN),
                    (157, 144, KAKTUS), (142, 145, BROCKEN)):
        k.setzen(0, x, y, z, nur=NATURBODEN)
    # Tankstelle im Nordosten
    haus(k, 0, 157, 119, 165, 125, [(161, 125)], kisten=2)
    k.malen(0, rechteck(155, 126, 168, 131), PFLASTER)
    for x, y in ((157, 129), (166, 129)):
        k.setzen(0, x, y, WAND)                              # Pfeiler des Dachs
    k.malen(0, {(160, 129), (163, 129)}, SCHROTT)            # Zapfsaeulen
    faesser(k, 0, 166, 120, 3)
    wrack(k, 0, 172, 121, 3)
    # Buswrack im Suedwesten
    wrack(k, 0, 131, 144, laenge=8, breite=3)
    faesser(k, 0, 135, 145, 3)
    k.stellen(0, 130, 153, KISTE)
    k.stellen(0, 131, 154, KISTE)
    # Felsnase im Nordwesten
    fels = klumpen(133, 124, 3.0, k.rnd)
    k.malen(0, fels, FELS, nur=NATURBODEN)
    k.malen(0, klumpen(136, 128, 2.2, k.rnd) - fels, KIES, nur={SAND, BUSCH})
    for x, y in ((137, 126), (130, 129), (138, 122)):
        k.stellen(0, x, y, BROCKEN)
    k.stellen(0, 129, 120, KAKTUS)
    k.bauen_auf(0, dehnen(fels, 2), 0)
    # Wasserturm im Suedosten, eingestuerzt
    for x, y in ((162, 148), (165, 148), (162, 151), (165, 151)):
        k.setzen(0, x, y, WAND)
    k.malen(0, {(166, 152), (167, 152), (167, 153), (168, 154)}, SCHROTT, nur=NATURBODEN)
    faesser(k, 0, 159, 153, 3)
    k.bauen_auf(0, rechteck(158, 147, 169, 155), 1)
    # Kontrollposten Ost und West: eine Sandsackreihe quer zur Piste, auf
    # beiden Seiten, die Piste selbst bleibt offen (`stellen` setzt nichts
    # auf Piste). Ein Haken am Ende, zwei Faesser dahinter.
    for sx, haken, fx in ((171, 1, 173), (129, -1, 126)):
        reihe = [y for y in range(131, 147) if k.stellen(0, sx, y, SACK)]
        for y in (reihe[:1] + reihe[-1:]):
            k.stellen(0, sx + haken, y, SACK)
        faesser(k, 0, fx, 133, 2)
    k.bauen_auf(0, rechteck(120, 132, 179, 142) - scheibe(ax, ay, 12), 0)


def fort_c(k: Karte):
    """Hotzone 3 (C): ein Fort aus Lehm. Mauer mit vier Toren, vier
    Ecktuermen und drei Breschen, darin Kantine, Stall, Lager und
    Kommandantur um einen gepflasterten Platz."""
    x0, y0, x1, y1 = 96, 167, 204, 228
    for x in range(x0, x1 + 1):
        k.setzen(0, x, y0, WAND)
        k.setzen(0, x, y1, WAND)
    for y in range(y0, y1 + 1):
        k.setzen(0, x0, y, WAND)
        k.setzen(0, x1, y, WAND)
    innen = rechteck(x0 + 1, y0 + 1, x1 - 1, y1 - 1)
    for (x, y) in innen:
        if k.an(0, x, y) in FEST:
            k.setzen(0, x, y, SAND)
    # Ecktuerme
    for cx, cy in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        k.malen(0, rechteck(cx - 2, cy - 2, cx + 2, cy + 2), WAND)
    # Tore mit Pfosten
    tore = (("n", 150, y0), ("s", 150, y1), ("w", x0, 197), ("o", x1, 192))
    for seite, x, y in tore:
        if seite in ("n", "s"):
            for d in range(-3, 4):
                k.setzen(0, x + d, y, PISTE)
                k.frei[0] |= {(x + d, y + t) for t in range(-3, 4)}
            for d in (-5, -4, 4, 5):
                for t in (-1, 0, 1):
                    k.setzen(0, x + d, y + t, WAND)
        else:
            for d in range(-3, 4):
                k.setzen(0, x, y + d, PISTE)
                k.frei[0] |= {(x + t, y + d) for t in range(-3, 4)}
            for d in (-5, -4, 4, 5):
                for t in (-1, 0, 1):
                    k.setzen(0, x + t, y + d, WAND)
    # Breschen: Mauer eingefallen, Schutt davor und dahinter
    for (bx, by, waagrecht) in ((117, y0, True), (x1, 215, False), (182, y1, True)):
        for d in range(-2, 2):
            px, py = (bx + d, by) if waagrecht else (bx, by + d)
            k.setzen(0, px, py, SAND)
        for d, t in ((-3, 0), (2, 0), (-2, -1), (1, 1), (0, -2), (-1, 2)):
            px, py = (bx + d, by + t) if waagrecht else (bx + t, by + d)
            if k.an(0, px, py) != WAND:
                k.stellen(0, px, py, BROCKEN)
            else:
                k.setzen(0, px, py, BROCKEN)
        k.malen(0, klumpen(bx, by, 2.5, k.rnd), KIES, nur={SAND, BUSCH})
        k.frei[0] |= {(bx + d, by) if waagrecht else (bx, by + d) for d in range(-1, 1)}
    # Platz um C
    cx, cy = 150, 197
    platz(k, 0, cx, cy, 6.5)
    k.frei[0] |= scheibe(cx, cy, 5)
    for punkte in (((150, 168), (150, 188)), ((150, 206), (150, 227)),
                   ((97, 197), (141, 197)), ((159, 194), (203, 192))):
        k.malen(0, band(punkte, 3.0, 71), PISTE, nur={SAND, BUSCH, KIES})
    # Gebaeude
    haus(k, 0, 106, 174, 130, 188, [(113, 188), (130, 181)], trenn=[("x", 119, 181)],
         kisten=4)                                                      # Kantine
    haus(k, 0, 170, 173, 196, 187, [(183, 187), (170, 180)], kisten=2)  # Stall
    for sx in (176, 182, 188):                                          # Boxen
        for y in range(174, 178):
            k.setzen(0, sx, y, WAND)
    for x, y in ((173, 174), (185, 174), (191, 175)):                   # Futterkisten
        k.setzen(0, x, y, KISTE)
    haus(k, 0, 104, 207, 130, 221, [(117, 207), (130, 214)], kisten=0)  # Lager
    for ry in (210, 213, 217):
        for rx in list(range(107, 112)) + list(range(121, 127)):
            if (rx, ry) not in k.frei[0] and k.rnd.random() < 0.8:
                k.setzen(0, rx, ry, KISTE)
    haus(k, 0, 171, 207, 196, 221, [(183, 207), (171, 214)], trenn=[("y", 214, 186)],
         kisten=3)                                                      # Kommandantur
    # Deckung auf dem Hof: kurze Mauern schraeg vor den Gebaeuden,
    # Sandsaecke an den Toren - kein Ring aus Faessern.
    for (mx, my) in ((140, 189), (158, 189), (140, 205), (158, 205)):
        for d in range(3):
            k.stellen(0, mx + d, my, WAND, auf=NATURBODEN | {PISTE, PFLASTER})
    bogen(k, 0, 150, 175, 3.0, 20, 160)
    bogen(k, 0, 150, 220, 3.0, 200, 340)
    bogen(k, 0, 106, 197, 3.0, -70, 70)
    bogen(k, 0, 194, 192, 3.0, 110, 250)
    faesser(k, 0, 132, 170, 2)
    faesser(k, 0, 198, 222, 3)
    faesser(k, 0, 101, 223, 2)
    for x, y in ((198, 171), (199, 171), (199, 172), (102, 171)):
        k.stellen(0, x, y, KISTE)
    k.setzen(0, 146, 186, WAND)                                         # Fahnenmast
    # Pfeiler an der Innenseite der Mauer, alle neun Kacheln
    for x in range(x0 + 6, x1 - 4, 9):
        for y in (y0 + 1, y1 - 1):
            k.stellen(0, x, y, WAND)
    for y in range(y0 + 6, y1 - 4, 9):
        for x in (x0 + 1, x1 - 1):
            k.stellen(0, x, y, WAND)
    # Trampelpfade von den Tueren zu den Wegen auf dem Hof
    for punkte in (((113, 189), (113, 195)), ((131, 181), (138, 184), (147, 188)),
                   ((183, 188), (183, 192)), ((117, 206), (117, 199)),
                   ((183, 206), (183, 195)), ((131, 214), (140, 210), (147, 204))):
        pfad(k, 0, punkte)
    # Marktstaende am Westweg: Bretterboden, Kisten darauf
    for (mx, my) in ((121, 192), (129, 192), (121, 201), (129, 201)):
        k.malen(0, rechteck(mx, my, mx + 3, my + 1), DIELEN, nur=NATURBODEN)
        k.stellen(0, mx + k.rnd.randrange(0, 4), my, KISTE, auf={DIELEN})
    # Vorraete vor dem Lager, ein Wagen am Stall, ein Schiessstand
    for x, y in ((113, 204), (114, 204), (113, 203), (121, 204)):
        k.stellen(0, x, y, KISTE)
    wrack(k, 0, 166, 189, 3, quer=True)
    for x in range(163, 168):
        k.stellen(0, x, 211, SACK)
    for x in (164, 166):
        k.stellen(0, x, 216, KISTE)                                     # Zielscheiben
    k.bauen_auf(0, rechteck(x0 - 3, y0 - 3, x1 + 3, y1 + 3), 0)


def steinbruch(k: Karte):
    """Zwischen Suedwest-Tafel und Fort: eine Grube mit Kies und
    Felsstufen, Huetten, Kisten, ein Stollen in die Schluchtwand."""
    rnd = k.rnd
    grube = klumpen(76, 200, 9.0, rnd, rauh=0.2)
    k.malen(0, grube, KIES, nur={SAND, BUSCH, PISTE})
    for cx, cy, r in ((64, 198, 3.2), (70, 212, 2.6), (84, 213, 2.2), (79, 189, 1.8)):
        k.malen(0, klumpen(cx, cy, r, rnd), FELS, nur={SAND, BUSCH, KIES})
    for x, y in ((72, 199), (78, 203), (75, 194), (82, 206), (68, 205)):
        k.stellen(0, x, y, BROCKEN)
    haus(k, 0, 80, 170, 87, 176, [(80, 173)], kisten=2)
    haus(k, 0, 61, 223, 68, 229, [(64, 223)], kisten=1)
    pfad(k, 0, ((79, 173), (74, 178), (70, 186)))
    pfad(k, 0, ((64, 222), (66, 216), (72, 211)))
    for x, y in ((72, 178), (73, 178), (72, 179)):
        k.stellen(0, x, y, KISTE)
    faesser(k, 0, 84, 179, 2)
    for x in (88, 91, 94):                                   # Lorenreihe
        k.stellen(0, x, 205, SCHROTT)
    # Stollen in die Schluchtwand im Sueden
    for y in range(229, 238):
        for x in range(88, 93):
            k.setzen(0, x, y, FELS)
    for y in range(230, 237):
        k.setzen(0, 89, y, WAND)
        k.setzen(0, 91, y, WAND)
        k.setzen(0, 90, y, DIELEN)
    k.setzen(0, 90, 229, DIELEN)
    k.frei[0] |= {(90, 228), (90, 229), (90, 227)}
    k.bauen_auf(0, rechteck(58, 186, 95, 232), 0)


def ranch(k: Karte):
    """Im Becken zwischen hoher Tafel, Grat und Suedost-Tafel."""
    haus(k, 0, 270, 149, 284, 158, [(276, 158), (277, 158), (270, 153)], kisten=4)  # Scheune
    haus(k, 0, 279, 167, 289, 176, [(279, 172)], trenn=[("x", 284, 170)], kisten=3)
    k.malen(0, rechteck(277, 167, 278, 176), DIELEN, nur={SAND, BUSCH, KIES, PISTE})
    for x, y in ((261, 151), (264, 151), (261, 154), (264, 154)):              # Windrad
        k.setzen(0, x, y, WAND)
    k.malen(0, {(266, 156), (267, 156)}, SCHROTT, nur=NATURBODEN)
    wrack(k, 0, 289, 185, 3)                                                   # Traktor
    faesser(k, 0, 268, 159, 2)
    for x, y in ((252, 152), (254, 155), (250, 156), (256, 151), (251, 159)):
        k.stellen(0, x, y, KAKTUS)
    k.bauen_auf(0, rechteck(248, 147, 292, 190), 0)


def schrottplatz(k: Karte):
    """Suedostecke: Wrackreihen mit Gassen, Reifen, ein umgestuerzter Kran."""
    rnd = k.rnd
    # Drei Reihen, dicht an dicht, die Piste laeuft dazwischen durch
    # (sie liegt bei y 220 bis 224 - eine Reihe darueber, zwei darunter).
    for reihe, (y, x0, x1) in enumerate(((214, 238, 272), (227, 234, 292), (231, 238, 290))):
        x = x0 + (reihe % 2) * 2
        while x < x1:
            if rnd.random() < 0.9:
                wrack(k, 0, x, y, rnd.choice((3, 3, 4)), quer=True)
            x += rnd.randrange(5, 7)
    # Reifenstapel und lose Teile zwischen den Reihen
    for _ in range(18):
        x, y = rnd.randrange(236, 292), rnd.choice((212, 217, 218, 226, 230, 234))
        k.stellen(0, x, y, SCHROTT)
    k.malen(0, rechteck(262, 211, 263, 212), WAND)                      # Kranfuss
    for x in range(264, 271):
        k.stellen(0, x, 211 + (x - 264) // 3, SCHROTT)
    haus(k, 0, 278, 228, 285, 234, [(281, 228)], kisten=1)
    faesser(k, 0, 274, 233, 3)
    k.bauen_auf(0, rechteck(240, 210, 294, 237), 0)


def kleinkram_tal(k: Karte):
    """Was sonst im Tal steht: ein abgebrannter Hof, ein Windrad, Wracks
    an der Piste."""
    haus(k, 0, 168, 99, 177, 107, [(172, 107)], kaputt=0.3, kisten=0)
    k.malen(0, klumpen(172, 103, 3.0, k.rnd), KIES, nur={DIELEN})        # Asche
    for x, y in ((78, 141), (81, 141), (78, 144), (81, 144)):            # Windrad
        k.setzen(0, x, y, WAND)
    k.malen(0, {(82, 145), (83, 146)}, SCHROTT, nur=NATURBODEN)
    k.bauen_auf(0, rechteck(76, 139, 84, 147), 1)
    for x, y, quer in ((66, 127, True), (105, 113, False), (196, 136, True),
                       (203, 166, False), (58, 150, False), (238, 158, True)):
        wrack(k, 0, x, y, 3, quer=quer)
    faesser(k, 0, 69, 130, 2)
    faesser(k, 0, 199, 139, 2)


# ══════════════════════════════════════════════════ 5. Auf den Tafeln

def funkstation_b(k: Karte):
    """Hotzone 2 (B): eine Funkstation auf der langen Tafel. Funkhaus,
    Baracke, Mast, zwei Wachtuerme, eine lockere Mauer im Bogen um den
    Platz und Sandsacknester. Der Landeplatz in der Mitte bleibt frei."""
    i, bx, by = 1, 150, 48
    platz(k, i, bx, by, 4.0)
    k.frei[i] |= scheibe(bx, by, 5.5)
    haus(k, i, 129, 29, 141, 38, [(135, 38)], trenn=[("x", 136, 34)], kisten=3)  # Funkhaus
    haus(k, i, 159, 30, 173, 39, [(159, 35), (166, 39)], kisten=0)               # Baracke
    for x in range(161, 172, 2):
        k.setzen(i, x, 31, KISTE)                                                # Pritschen
    k.malen(i, rechteck(149, 31, 150, 32), WAND)                                 # Mast
    for x, y in ((145, 28), (154, 28), (149, 25)):
        k.stellen(i, x, y, BROCKEN)                                              # Anker
    # Hofmauer: gerade Stuecke, im Sueden ein Tor, Wachtuerme an den
    # Ecken. Ein Bogen aus Mauerkacheln (erster Versuch) war eine Treppe.
    # Die Fahrspuren schneiden ihre Tore selbst: `stellen` setzt nichts
    # auf Piste.
    for x in range(127, 174):
        if not 145 <= x <= 155 and not (134 <= x <= 136):               # Tor, Bresche
            k.stellen(i, x, 66, WAND)
    for y in range(42, 66):
        if not 51 <= y <= 53:
            k.stellen(i, 126, y, WAND)
        if not 58 <= y <= 60:
            k.stellen(i, 174, y, WAND)
    for x in range(142, 158):                                                    # hinter dem Mast
        if x not in (149, 150):
            k.stellen(i, x, 26, WAND)
    for (tx, ty) in ((125, 65), (173, 65), (125, 41), (173, 41)):               # Wachtuerme
        k.malen(i, rechteck(tx, ty, tx + 1, ty + 1), WAND)
    for x, y in ((134, 67), (136, 65), (135, 68)):                               # Schutt
        k.stellen(i, x, y, BROCKEN)
    # Sandsacknester: gerade Stuecke mit einem Haken, wie man sie stapelt.
    # (Ein Bogen aus Sandsaecken wurde zur Treppe - Kacheln sind eckig.)
    for (sx, sy, waagrecht, haken) in ((141, 41, True, 1), (156, 41, True, 1),
                                       (141, 55, True, -1), (156, 55, True, -1),
                                       (140, 46, False, 1), (160, 48, False, -1)):
        for d in range(4 if waagrecht else 3):
            k.stellen(i, sx + d if waagrecht else sx, sy if waagrecht else sy + d, SACK)
        if waagrecht:
            k.stellen(i, sx, sy + haken, SACK)
    k.malen(i, rechteck(130, 46, 131, 47), SCHROTT)                              # Tank
    faesser(k, i, 142, 31, 2)
    faesser(k, i, 174, 37, 3)
    faesser(k, i, 156, 56, 2)
    for x, y in ((128, 40), (129, 41), (171, 42)):
        k.stellen(i, x, y, KISTE)
    k.bauen_auf(i, scheibe(bx, by, 24), 0)


def flugzeug(k: Karte):
    """Auf der Westseite der langen Tafel: ein abgestuerztes Flugzeug,
    Rumpf, Fluegel, Leitwerk, Truemmer und eine Brandspur."""
    i = 1
    k.malen(i, band(((40, 46), (52, 42), (62, 40)), 3.0, 99), KIES, nur={SAND, BUSCH})
    for x in range(56, 71):
        for y in (40, 41):
            k.stellen(i, x, y, SCHROTT)
    for y in range(33, 49):
        if y not in (40, 41):
            k.stellen(i, 64, y, SCHROTT)
    for y in range(37, 45):
        if y not in (40, 41):
            k.stellen(i, 57, y, SCHROTT)
    for x, y in ((51, 43), (48, 46), (74, 38), (61, 49), (68, 33)):
        k.stellen(i, x, y, SCHROTT)
    faesser(k, i, 72, 44, 2)
    k.bauen_auf(i, rechteck(46, 31, 76, 51), 1)


def landepiste(k: Karte):
    """Eine Landepiste auf der langen Tafel, daneben ein Hangar - das
    Flugzeug suedlich davon hat sie nicht mehr erreicht."""
    i = 1
    for x in range(28, 112):
        for y in range(19, 23):
            rand = y in (19, 22)
            if not rand or k.rnd.random() < 0.8:
                k.setzen(i, x, y, PISTE, nur=NATURBODEN)
        if x % 10 == 0:                                   # Markierungssteine
            k.stellen(i, x, 17, BROCKEN)
            k.stellen(i, x, 24, BROCKEN)
    haus(k, i, 14, 9, 25, 17, [], offen="s", kisten=3)     # Hangar
    k.malen(i, rechteck(15, 10, 24, 17), PFLASTER, nur={DIELEN})
    k.malen(i, rechteck(27, 11, 28, 12), SCHROTT)          # Tank
    faesser(k, i, 27, 14, 3)
    k.stellen(i, 30, 15, KISTE)
    k.bauen_auf(i, rechteck(14, 9, 112, 24), 1)


def tafeln_bebauen(k: Karte):
    funkstation_b(k)
    landepiste(k)
    flugzeug(k)
    # Depot vor dem Aufstieg auf die hohe Tafel
    for x, y in ((205, 24), (206, 24), (205, 25), (203, 36), (204, 36)):
        k.stellen(1, x, y, KISTE)
    faesser(k, 1, 207, 37, 2)
    # Huette auf der Suedwest-Tafel
    haus(k, 1, 15, 193, 23, 199, [(19, 193)], kisten=2)
    faesser(k, 1, 24, 200, 2)
    # Missionsruine auf der Suedost-Tafel
    haus(k, 1, 236, 177, 250, 190, [(243, 177), (243, 190)], kaputt=0.3, kisten=0)
    k.malen(1, rechteck(248, 177, 250, 179), WAND)                       # Glockenturm
    # Hohe Tafel: Aussichtsturm, ein verlassenes Lager, ein umgestuerzter
    # Funkmast und Scharfschuetzennester an den Kanten.
    haus(k, 2, 257, 84, 264, 91, [(260, 91)], kaputt=0.25, kisten=1)
    for cx, cy, von, bis in ((262, 139, 30, 150), (284, 128, 0, 120),
                             (222, 72, 100, 260), (226, 112, 100, 240)):
        bogen(k, 2, cx, cy, 2.4, von, bis)
    faesser(k, 2, 268, 130, 2)
    haus(k, 2, 276, 30, 283, 35, [(279, 35)], kisten=2)                  # Huette
    k.malen(2, rechteck(275, 36, 284, 37), DIELEN, nur=NATURBODEN)        # Steg
    for x, y in ((272, 40), (273, 40), (272, 41)):
        k.stellen(2, x, y, KISTE)
    faesser(k, 2, 286, 38, 2)
    for t in range(9):                                                   # Mast, gefallen
        k.stellen(2, 240 + t, 58 + t // 2, SCHROTT)
    k.malen(2, rechteck(238, 56, 239, 57), WAND)
    k.bauen_auf(2, rechteck(236, 55, 250, 64), 1)
    k.malen(2, band(((228, 96), (238, 100), (246, 98)), 2.0, 97), KIES, nur={SAND, BUSCH})


# ══════════════════════════════════════════════════ 6. Natur

def natur(k: Karte):
    """Felsnasen, Brockengruppen, Kakteen - verteilt, aber nicht
    gleichmaessig: Pfeil um Pfeil geworfen und behalten, was weit genug
    von allem anderen liegt (und nicht im Weg)."""
    rnd = random.Random(SAAT + 2)

    def platz_ok(i, menge, abstand=2):
        for (x, y) in dehnen(menge, abstand):
            if (x, y) in k.frei[i] or (x, y) in k.bebaut[i]:
                return False
            z = k.an(i, x, y)
            if z is None or z in TREPPEN or z == PISTE:
                return False
            if i > 0 and z == LOCH:
                return False             # nicht an die Abbruchkante
        return all(k.an(i, x, y) in NATURBODEN for (x, y) in menge)

    mitten = {0: [], 1: [], 2: []}

    def weit_genug(i, x, y, d):
        return all((x - a) ** 2 + (y - b) ** 2 >= d * d for a, b in mitten[i])

    def fels_nah(i, x, y, r=4):
        return any(k.an(i, x + dx, y + dy) == FELS
                   for dy in range(-r, r + 1) for dx in range(-r, r + 1))

    # Felsnasen - dort, wo das Felsrauschen hoch ist: Felsfelder mit
    # mehreren Nasen, dazwischen weite leere Flaechen.
    for i, anzahl, d in ((0, 58, 12), (1, 24, 13), (2, 12, 12)):
        versuche = 0
        gesetzt = 0
        while gesetzt < anzahl and versuche < anzahl * 120:
            versuche += 1
            x, y = rnd.randrange(4, B - 4), rnd.randrange(4, H - 4)
            if rnd.random() > dichte(201 + i, x, y) ** 1.5:
                continue
            if not weit_genug(i, x, y, d):
                continue
            r = rnd.uniform(1.3, 3.4) if i == 0 else rnd.uniform(1.2, 2.6)
            fels = klumpen(x, y, r, rnd)
            if len(fels) < 3 or not platz_ok(i, fels, 3):
                continue
            k.malen(i, fels, FELS)
            mitten[i].append((x, y))
            gesetzt += 1
            # Geroell auf einer Seite, wohin es gerollt ist
            w = rnd.uniform(0, math.tau)
            gx, gy = x + math.cos(w) * (r + 1.5), y + math.sin(w) * (r + 1.5)
            k.malen(i, klumpen(gx, gy, rnd.uniform(1.6, 3.0), rnd) - fels, KIES,
                    nur={SAND, BUSCH})
            for _ in range(rnd.randrange(1, 4)):
                bw = w + rnd.uniform(-0.9, 0.9)
                bd = r + rnd.uniform(1.4, 3.2)
                bx, by_ = int(round(x + math.cos(bw) * bd)), int(round(y + math.sin(bw) * bd))
                if platz_ok(i, {(bx, by_)}, 1):
                    k.stellen(i, bx, by_, BROCKEN)
            if rnd.random() < 0.4:
                kw = rnd.uniform(0, math.tau)
                kx, ky = int(round(x + math.cos(kw) * (r + 3))), int(round(y + math.sin(kw) * (r + 3)))
                if platz_ok(i, {(kx, ky)}, 1):
                    k.stellen(i, kx, ky, KAKTUS)
            k.bebaut[i] |= dehnen(fels, 1)

    # Brockengruppen und Kakteen, auch in Gebieten: Brocken liegen, wo
    # Fels ist (Felsfeld, Hangfuss), Kakteen haben ihr eigenes Rauschen
    # und wachsen gern im Schutz von Fels.
    for i, gruppen, kakteen in ((0, 80, 95), (1, 36, 30), (2, 20, 15)):
        for art, anzahl in ((BROCKEN, gruppen), (KAKTUS, kakteen)):
            gesetzt = versuche = 0
            while gesetzt < anzahl and versuche < anzahl * 150:
                versuche += 1
                x, y = rnd.randrange(4, B - 4), rnd.randrange(4, H - 4)
                if art == BROCKEN:
                    p = max(dichte(201 + i, x, y) ** 1.5, 0.6 if fels_nah(i, x, y) else 0.0)
                else:
                    p = dichte(301 + i, x, y, 18.0) ** 1.6 + (0.15 if fels_nah(i, x, y, 3) else 0.0)
                if rnd.random() > p:
                    continue
                if not weit_genug(i, x, y, 4):
                    continue
                n = rnd.choice((1, 2, 2, 3)) if art == BROCKEN else rnd.choice((1, 1, 2, 3))
                stellen = [(x, y)]
                for _ in range(n - 1):
                    a, b = stellen[-1]
                    if art == BROCKEN:
                        stellen.append((a + rnd.choice((-1, 1)), b + rnd.choice((-1, 0, 1))))
                    else:
                        stellen.append((a + rnd.choice((-3, -2, 2, 3)), b + rnd.choice((-2, 0, 2))))
                if not platz_ok(i, set(stellen), 2):
                    continue
                for (a, b) in stellen:
                    k.stellen(i, a, b, art)
                mitten[i].append((x, y))
                gesetzt += 1
    # Am Fuss der Wand: herabgefallene Brocken, mal einer, mal zwei
    for (x, y) in sorted(k.tafel1):
        if rnd.random() > 0.035:
            continue
        for dx, dy in N4:
            px, py = x + dx * 2, y + dy * 2
            if (px, py) not in k.tafel1 and platz_ok(0, {(px, py)}, 1):
                k.stellen(0, px, py, BROCKEN)
                break


# ══════════════════════════════════════════════════ 7. Marken

SPAWN = {
    0: ((12, 112), (47, 140), (60, 97), (140, 96), (206, 100), (75, 152),
        (100, 160), (190, 124), (127, 128), (174, 152), (68, 186), (78, 228),
        (110, 196), (190, 199), (150, 176), (150, 220), (122, 234), (214, 232),
        (254, 160), (292, 162), (258, 226), (292, 232), (279, 199), (226, 160)),
    1: ((14, 20), (50, 62), (92, 28), (126, 70), (180, 68), (200, 18), (110, 14),
        (22, 180), (40, 224), (222, 192), (262, 196)),
    2: ((232, 18), (276, 60), (250, 120), (290, 100)),
}


def marken(k: Karte, erreicht):
    for zeichen, i, x, y in KREISE:
        if not k.begehbar(i, x, y):
            raise SystemExit("Kreis %s liegt nicht auf Boden (%d, %d)" % (zeichen, x, y))
        k.e[i][y][x] = zeichen
    for i, liste in SPAWN.items():
        for (sx, sy) in liste:
            bestes = None
            for r in range(0, 8):
                for dy in range(-r, r + 1):
                    for dx in range(-r, r + 1):
                        if max(abs(dx), abs(dy)) != r:
                            continue
                        x, y = sx + dx, sy + dy
                        if (k.an(i, x, y) in (SAND, BUSCH, KIES) and (i, x, y) in erreicht
                                and (x, y) not in k.frei[i]
                                and all(k.an(i, x + a, y + b) not in FEST and k.an(i, x + a, y + b) != LOCH
                                        for a, b in N4)):
                            bestes = (x, y)
                            break
                    if bestes:
                        break
                if bestes:
                    break
            if bestes is None:
                raise SystemExit("Keine Spawnstelle bei %s auf Ebene %d" % ((sx, sy), i))
            k.e[i][bestes[1]][bestes[0]] = "Z"


# ══════════════════════════════════════════════════ 8. Pruefen und reparieren

def stapeln(k: Karte):
    """Unter jeder Tafel ist Fels. Was gebaut wurde, darf daran nichts
    aendern - ausser die Tueren der Aufzuege."""
    for y in range(H):
        for x in range(B):
            if k.e[1][y][x] != LOCH and k.e[0][y][x] not in FEST and k.e[0][y][x] != HOCH:
                k.e[0][y][x] = FELS
            if k.e[2][y][x] != LOCH and k.e[1][y][x] not in FEST and k.e[1][y][x] != HOCH:
                k.e[1][y][x] = FELS


def erreichbar(k: Karte, start):
    gesehen = {start}
    offen = deque([start])
    while offen:
        i, x, y = offen.popleft()
        nachbarn = [(i, x + dx, y + dy) for dx, dy in N4]
        z = k.e[i][y][x]
        if z == HOCH and i < 2:
            nachbarn.append((i + 1, x, y))
        elif z == RUNTER and i > 0:
            nachbarn.append((i - 1, x, y))
        for n in nachbarn:
            if n not in gesehen and k.begehbar(*n):
                gesehen.add(n)
                offen.append(n)
    return gesehen


def reparieren(k: Karte):
    """Was nicht erreichbar ist: klein -> zuschuetten, gross -> einen Weg
    freimachen. So lange, bis alles erreichbar ist."""
    start = (0, KREISE[0][2], KREISE[0][3])
    for _runde in range(60):
        da = erreichbar(k, start)
        fehlt = [(i, x, y) for i in range(3) for y in range(H) for x in range(B)
                 if k.begehbar(i, x, y) and (i, x, y) not in da]
        if not fehlt:
            return da
        rest = set(fehlt)
        stuecke = []
        while rest:
            s = rest.pop()
            stueck = {s}
            offen = deque([s])
            while offen:
                i, x, y = offen.popleft()
                for dx, dy in N4:
                    n = (i, x + dx, y + dy)
                    if n in rest:
                        rest.discard(n)
                        stueck.add(n)
                        offen.append(n)
            stuecke.append(stueck)
        for stueck in stuecke:
            i = next(iter(stueck))[0]
            if len(stueck) <= 6:
                for (_i, x, y) in stueck:
                    um = [k.an(i, x + dx, y + dy) for dx, dy in N4]
                    fest = [z for z in um if z in FEST]
                    k.e[i][y][x] = max(sorted(set(fest)), key=fest.count) if fest else BROCKEN
                continue
            # Kuerzester Weg durch Hindernisse (nicht durch Fels) zum Rest
            vorher = {}
            offen = deque()
            for p in stueck:
                vorher[p] = None
                offen.append(p)
            ziel = None
            while offen and ziel is None:
                p = offen.popleft()
                _i, x, y = p
                for dx, dy in N4:
                    n = (i, x + dx, y + dy)
                    if n in vorher:
                        continue
                    z = k.an(i, n[1], n[2])
                    if z is None or z == LOCH or z == FELS:
                        continue
                    vorher[n] = p
                    if n in da:
                        ziel = n
                        break
                    offen.append(n)
            if ziel is None:
                for (_i, x, y) in stueck:
                    k.e[i][y][x] = BROCKEN if len(stueck) < 30 else k.e[i][y][x]
                continue
            p = vorher[ziel]
            while p is not None and p not in stueck:
                _i, x, y = p
                if k.e[i][y][x] in FEST:
                    k.e[i][y][x] = DIELEN if DIELEN in [k.an(i, x + dx, y + dy) for dx, dy in N4] else SAND
                p = vorher[p]
    raise SystemExit("Karte laesst sich nicht ganz verbinden")


def einzelne_fuellen(k: Karte):
    """Kein einzelnes Bodenfeld, um das herum alles fest ist."""
    for i in range(3):
        for y in range(H):
            for x in range(B):
                if not k.begehbar(i, x, y) or k.e[i][y][x] in TREPPEN:
                    continue
                if not any(k.begehbar(i, x + dx, y + dy) for dx, dy in N4):
                    um = [k.an(i, x + dx, y + dy) for dx, dy in N4]
                    fest = [z for z in um if z in FEST]
                    k.e[i][y][x] = max(sorted(set(fest)), key=fest.count) if fest else BROCKEN


def aufzuege_pruefen(k: Karte):
    for (unten, x, y, seite) in k.aufzuege:
        oben = unten + 1
        if unten == 0:
            assert k.begehbar(1, x - 1, y) and k.begehbar(1, x + 1, y), \
                "Aufzug %s: oben kein Ausstieg links/rechts" % ((x, y),)
        for i in (unten, oben):
            assert k.e[i][y][x] in TREPPEN, "Aufzug %s ueberbaut" % ((x, y),)


def kennzahlen(k: Karte):
    """Was die Tests messen - vorab, damit man es beim Bauen sieht."""
    zahlen = {}
    for i in range(3):
        for y in range(H):
            for x in range(B):
                z = k.e[i][y][x]
                zahlen[(i, z)] = zahlen.get((i, z), 0) + 1
    himmel = [(x, y) for y in range(H) for x in range(B) if k.e[1][y][x] == LOCH]
    frei = sum(1 for (x, y) in himmel if k.begehbar(0, x, y))
    oben = [(x, y) for y in range(H) for x in range(B) if k.begehbar(1, x, y)]
    innen = sum(1 for (x, y) in oben if all(k.begehbar(1, x + dx, y + dy) for dx, dy in N4))
    ax, ay = KREISE[0][2], KREISE[0][3]
    fass_a = [math.hypot(x - ax, y - ay) * 32 for y in range(H) for x in range(B)
              if k.e[0][y][x] == FASS]
    bx, by = KREISE[1][2], KREISE[1][3]
    um_b = [math.hypot(x - bx, y - by) for y in range(H) for x in range(B)
            if k.e[1][y][x] in (WAND, FASS) and math.hypot(x - bx, y - by) < 40]
    return {
        "himmel_frei": frei / max(1, len(himmel)),
        "oben": len(oben), "innen_anteil": innen / max(1, len(oben)),
        "faesser_a": (sum(1 for d in fass_a if 150 <= d < 800), sum(1 for d in fass_a if d < 150)),
        "um_b": (len(um_b), sum(1 for d in um_b if d * 32 < 96 + 32)),
        "faesser": sum(v for (i, z), v in zahlen.items() if z == FASS),
        "zahlen": zahlen,
    }


# ══════════════════════════════════════════════════ Ablauf

def bauen() -> Karte:
    k = Karte()
    gelaende(k)
    aufzuege(k)
    boden(k)
    westdorf(k)
    kreuzung_a(k)
    fort_c(k)
    steinbruch(k)
    ranch(k)
    schrottplatz(k)
    kleinkram_tal(k)
    tafeln_bebauen(k)
    for (unten, x, y, seite) in k.aufzuege:
        landeplatz(k, unten, x, y, seite)
    natur(k)
    stapeln(k)
    # Gassen und Vorplaetze der Aufzuege: zuletzt frei raeumen, falls doch
    # etwas hineingeraten ist (eine Hauswand, eine Bresche).
    # Fels bleibt: die Kanten links und rechts der Tuer sind die Wand.
    for (unten, x, y, seite) in k.aufzuege:
        for i in (unten, unten + 1):
            for (px, py) in k.frei[i]:
                if abs(px - x) <= 2 and abs(py - y) <= 9 or abs(py - y) <= 2 and abs(px - x) <= 9:
                    if k.an(i, px, py) in FEST - {FELS}:
                        k.e[i][py][px] = SAND
    einzelne_fuellen(k)
    da = reparieren(k)
    einzelne_fuellen(k)
    da = reparieren(k)
    aufzuege_pruefen(k)
    marken(k, da)
    return k


KOPF = (
    "# STAUBTAL - die grosse Wuestenkarte. Seit 0.34.6 von Hand gezeichnet und",
    "# erzeugt mit werkzeug_staubtal.py (nicht von Hand aendern - neu erzeugen).",
    "# 300 x 240 Kacheln, drei Ebenen: das Tal, die Tafeln, die hohe Tafel.",
    "# A Kreuzung im Tal, B Funkstation auf der langen Tafel, C das Fort.",
    "# Zeichen: . Sand  : Piste  ; Kies  \" Gestruepp  _ Pflaster  = Dielen",
    "#          # Mauer  r Fels  X Fass  b Brocken  s Sandsack  h Holzkiste",
    "#          k Kaktus  w Schrott  ^ v Aufzug (E)  ~ Luft  Z Spawnstelle",
    "",
    "name: STAUBTAL",
    "satz: wueste",
    "kreise: A B C",
    "",
)


def als_text(k: Karte) -> str:
    teile = ["\n".join(KOPF)]
    for i in range(3):
        zeilen = ["".join(z) for z in k.e[i]]
        teile.append("--- ebene %d ---\n" % i + "\n".join(zeilen) + "\n")
    return "\n".join(teile).rstrip("\n") + "\n"


def schreiben(pfad, k: Karte | None = None):
    k = k or bauen()
    Path(pfad).write_text(als_text(k), encoding="utf-8")
    return k


if __name__ == "__main__":
    import sys
    ziel = sys.argv[1] if len(sys.argv) > 1 else "karten/staubtal.txt"
    Path(ziel).parent.mkdir(parents=True, exist_ok=True)
    karte = schreiben(ziel)
    z = kennzahlen(karte)
    print("geschrieben:", ziel)
    print("unter freiem Himmel begehbar: %.0f %%" % (100 * z["himmel_frei"]))
    print("Tafeln oben: %d Kacheln, %.1f %% innen" % (z["oben"], 100 * z["innen_anteil"]))
    print("Faesser um A (150-800 px / naeher): %d / %d" % z["faesser_a"])
    print("Mauer+Fass um B (40 Kacheln / im Kreis): %d / %d" % z["um_b"])
    print("Faesser insgesamt:", z["faesser"])
    print("Aufzuege:", [(u, x, y) for (u, x, y, _s) in karte.aufzuege])
