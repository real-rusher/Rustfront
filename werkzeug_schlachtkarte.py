# -*- coding: utf-8 -*-
"""
Gemeinsames Werkzeug fuer die Schlachtkarten FLUSSTAL und KANALSTADT
(seit 0.34.131): eine Leinwand aus Zeichen, die alles **punktgespiegelt**
setzt - was ROT im Westen hat, hat BLAU im Osten, um die Kartenmitte
gedreht. So ist keine Seite im Vorteil, ohne dass man jede Haelfte von Hand
gleich halten muss.

Dazu, was eine Schlachtkarte im Kopf braucht (gelesen von
dustfront/schlachtkarte.py):

    basis1: 0 14 40 NORDLAGER | buggy 2 0, krad 1 0      Seite, Kachel x y, Name | Fahrzeuge (Art, Anzahl, Stufe)
    punkt1: 115 35 KAPELLE                               Eroberungspunkt, Kachel x y, Name
    weg1: 14,40 30,38 60,36                              ein Weg fuer die Bots, Kachel x,y je Punkt

Nur die Standardbibliothek: die Generatoren laufen auch ohne pygame.
"""
from __future__ import annotations

import math
import random
from collections import deque

FEST = set("#rbshXkw")
WASSER_TIEF = "%"
WASSER_SEICHT = "+"
# Zeichen, die beim Spiegeln die Seite wechseln: Marken der Basen.
TAUSCH = {"R": "B", "B": "R"}


class Leinwand:
    """Ein Raster aus Zeichen. `spiegeln`: jede Aenderung auch am
    Gegenpunkt (um die Mitte gedreht)."""

    def __init__(self, breite: int, hoehe: int, grund: str = ".") -> None:
        self.b, self.h = breite, hoehe
        self.k = [[grund] * breite for _ in range(hoehe)]
        self.spiegeln = True
        self.basen = []          # (Seite, x, y, Name, Fahrzeuge)
        self.punkte = []         # (x, y, Name)
        self.wege = []           # [(x, y), ...]

    # ---- Grundlagen -------------------------------------------------------
    def drin(self, x: int, y: int, rand: int = 0) -> bool:
        return rand <= x < self.b - rand and rand <= y < self.h - rand

    def gegen(self, x: int, y: int) -> tuple:
        return self.b - 1 - x, self.h - 1 - y

    def get(self, x: int, y: int) -> str:
        if not self.drin(x, y):
            return "r"
        return self.k[y][x]

    def setze(self, x: int, y: int, z: str, nur=None, nicht=None) -> None:
        """Setzt z (und gespiegelt). `nur`: nur auf diese Zeichen; `nicht`:
        nie auf diese."""
        x, y = int(round(x)), int(round(y))
        stellen = [(x, y, z)]
        if self.spiegeln:
            gx, gy = self.gegen(x, y)
            stellen.append((gx, gy, TAUSCH.get(z, z)))
        for sx, sy, sz in stellen:
            if not self.drin(sx, sy):
                continue
            alt = self.k[sy][sx]
            if nur is not None and alt not in nur:
                continue
            if nicht is not None and alt in nicht:
                continue
            self.k[sy][sx] = sz

    def rechteck(self, x0, y0, x1, y1, z, nur=None, nicht=None) -> None:
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                self.setze(x, y, z, nur, nicht)

    def kreis(self, cx, cy, rad, z, rnd=None, dichte=1.0, nur=None, nicht=None,
              quer: float = 1.0) -> None:
        """Ein Kreis (mit `quer` eine Ellipse), mit `dichte` < 1 locker."""
        r = int(math.ceil(rad))
        for y in range(int(cy) - r - 1, int(cy) + r + 2):
            for x in range(int(cx) - int(r * quer) - 1, int(cx) + int(r * quer) + 2):
                if ((x - cx) / quer) ** 2 + (y - cy) ** 2 <= rad * rad:
                    if dichte >= 1.0 or (rnd is not None and rnd.random() < dichte):
                        self.setze(x, y, z, nur, nicht)

    def linie(self, punkte, breite: float, z, nur=None, nicht=None, rnd=None,
              rauh: float = 0.0) -> None:
        """Ein dicker Zug durch die Punkte. `rauh`: die Breite schwankt um
        so viele Kacheln (Ufer, Waldwege)."""
        for (x0, y0), (x1, y1) in zip(punkte, punkte[1:]):
            n = max(1, int(max(abs(x1 - x0), abs(y1 - y0)) * 2))
            for i in range(n + 1):
                t = i / n
                x = x0 + (x1 - x0) * t
                y = y0 + (y1 - y0) * t
                b = breite / 2.0
                if rauh and rnd is not None:
                    b += rnd.uniform(-rauh, rauh)
                self.kreis(x, y, max(0.5, b), z, nur=nur, nicht=nicht)

    def streuen(self, rnd, anzahl, x0, y0, x1, y1, z, nur=None, abstand=None) -> None:
        """Einzelne Zeichen zufaellig in ein Feld (nur auf `nur`)."""
        for _ in range(anzahl):
            x, y = rnd.randrange(int(x0), int(x1)), rnd.randrange(int(y0), int(y1))
            if abstand is not None and not abstand(x, y):
                continue
            self.setze(x, y, rnd.choice(z) if len(z) > 1 else z, nur=nur)

    # ---- Gebautes ------------------------------------------------------------
    def haus(self, x0, y0, b, h, rnd, wand="#", boden="=", tueren=(), fenster=0.0,
             kaputt=0.0, innen=None) -> None:
        """Ein Haus: Mauerring, Boden, Tueren als (Seite, Abstand, Breite) mit
        Seite n/s/w/o. `fenster`: Anteil Luecken in der Mauer (Schiessscharten,
        nur einzelne Kacheln). `kaputt`: Anteil eingestuerzter Mauerstuecke.
        `innen`: Zwischenwand (senkrecht bei x0 + innen) mit Durchgang."""
        x1, y1 = x0 + b - 1, y0 + h - 1
        self.rechteck(x0 + 1, y0 + 1, x1 - 1, y1 - 1, boden)
        for x in range(x0, x1 + 1):
            for y in (y0, y1):
                self.setze(x, y, wand)
        for y in range(y0, y1 + 1):
            for x in (x0, x1):
                self.setze(x, y, wand)
        if innen:
            for y in range(y0 + 1, y1):
                self.setze(x0 + innen, y, wand)
            mitte = y0 + h // 2
            self.rechteck(x0 + innen, mitte - 1, x0 + innen, mitte, boden)
        for seite, ab, breit in tueren:
            for i in range(breit):
                if seite == "n":
                    self.setze(x0 + ab + i, y0, boden)
                elif seite == "s":
                    self.setze(x0 + ab + i, y1, boden)
                elif seite == "w":
                    self.setze(x0, y0 + ab + i, boden)
                else:
                    self.setze(x1, y0 + ab + i, boden)
        # Fenster und Einsturz: nie an den Ecken, damit das Haus ein Haus bleibt.
        rand = [(x, y0) for x in range(x0 + 2, x1 - 1)] + [(x, y1) for x in range(x0 + 2, x1 - 1)] \
            + [(x0, y) for y in range(y0 + 2, y1 - 1)] + [(x1, y) for y in range(y0 + 2, y1 - 1)]
        for x, y in rand:
            if self.k[y][x] != wand:
                continue
            w = rnd.random()
            if w < kaputt:
                self.setze(x, y, rnd.choice(";;b"))
            elif w < kaputt + fenster:
                self.setze(x, y, boden)

    def punkt(self, x: int, y: int, name: str, gegen_name: str = "") -> None:
        """Ein Eroberungspunkt (Marke E) - und sein Gegenstueck, wenn er
        nicht genau in der Mitte liegt."""
        self.setze(x, y, "E")
        self.punkte.append((x, y, name))
        gx, gy = self.gegen(x, y)
        if (gx, gy) != (x, y) and self.spiegeln:
            self.punkte.append((gx, gy, gegen_name or name))

    def weg(self, punkte) -> None:
        """Ein Weg fuer die Bots, und gespiegelt."""
        punkte = [(int(round(x)), int(round(y))) for x, y in punkte]
        self.wege.append(punkte)
        if self.spiegeln:
            self.wege.append(gespiegelt(self, punkte))

    def basis(self, seite: int, cx: int, cy: int, name: str, fahrzeuge: str, rnd,
              b: int = 30, h: int = 26, mauer: str = "#", hof: str = "_",
              tore=("o",), tor_breite: int = 7, gegen_name: str = "") -> None:
        """Eine Startbasis: Mauerring mit breiten Toren, gepflasterter Hof,
        Sandsackstellungen an den Toren, ein Bunker, Stellplaetze mit
        Kistenreihen, Spawnstellen (Z) und die Marke R/B in der Mitte.
        `tore`: Seiten mit Tor (n/s/o/w aus Sicht von ROT im Westen)."""
        x0, y0 = cx - b // 2, cy - h // 2
        x1, y1 = x0 + b - 1, y0 + h - 1
        self.rechteck(x0 - 3, y0 - 3, x1 + 3, y1 + 3, ".", nur=FEST | set("+%"))
        self.rechteck(x0, y0, x1, y1, hof)
        for x in range(x0, x1 + 1):
            for y in (y0, y0 + 1, y1 - 1, y1):
                self.setze(x, y, mauer)
        for y in range(y0, y1 + 1):
            for x in (x0, x0 + 1, x1 - 1, x1):
                self.setze(x, y, mauer)
        for tor in tore:
            if tor in ("n", "s"):
                tx = cx - tor_breite // 2 + (4 if tor == "n" else -4)
                yy = (y0, y0 + 1) if tor == "n" else (y1 - 1, y1)
                for i in range(tor_breite):
                    for y in yy:
                        self.setze(tx + i, y, hof)
                # Sandsaecke vor dem Tor, zur Seite versetzt.
                vy = y0 - 3 if tor == "n" else y1 + 3
                for i in range(3):
                    self.setze(tx - 2 + i, vy, "s")
                    self.setze(tx + tor_breite - 1 + i, vy, "s")
            else:
                ty = cy - tor_breite // 2
                xx = (x1 - 1, x1) if tor == "o" else (x0, x0 + 1)
                for i in range(tor_breite):
                    for x in xx:
                        self.setze(x, ty + i, hof)
                vx = x1 + 3 if tor == "o" else x0 - 3
                for i in range(3):
                    self.setze(vx, ty - 2 + i, "s")
                    self.setze(vx, ty + tor_breite - 1 + i, "s")
        # Wachtuerme an den Ecken: ein Block aus Mauer.
        for ex, ey in ((x0, y0), (x1 - 2, y0), (x0, y1 - 2), (x1 - 2, y1 - 2)):
            self.rechteck(ex, ey, ex + 2, ey + 2, mauer)
        # Der Bunker hinten (zur Kartenkante), mit Tuer zum Hof.
        bx = x0 + 4
        self.haus(bx, cy - 4, 6, 9, rnd, wand=mauer, boden="=", tueren=(("o", 3, 3),))
        # Stellplaetze: Kistenreihen als Trennung, Platz fuer Wagen dazwischen.
        for i, dy in enumerate((-h // 2 + 5, h // 2 - 6)):
            for dx in range(6, b - 9, 7):
                self.setze(x0 + dx + 4, cy + dy, "h")
                self.setze(x0 + dx + 4, cy + dy + 1, "h")
        # Spawnstellen im Hof.
        for dy in (-6, -2, 2, 6):
            for dx in (-2, 3):
                self.setze(cx + dx, cy + dy, "Z")
        self.setze(cx + 1, cy, "R" if seite == 0 else "B")
        self.basen.append((seite, cx + 1, cy, name, fahrzeuge))
        if self.spiegeln:
            gx, gy = self.gegen(cx + 1, cy)
            self.basen.append((1 - seite, gx, gy, gegen_name or name, fahrzeuge))

    def wege_freilegen(self) -> None:
        """Jeder Wegpunkt der Bots steht frei: ein Baum, ein Brocken genau
        dort wird Boden (die Punkte liegen oft im Wald)."""
        for weg in self.wege:
            for x, y in weg:
                for yy in range(y - 1, y + 2):
                    for xx in range(x - 1, x + 2):
                        if self.get(xx, yy) in FEST and self.drin(xx, yy, 3):
                            self.setze(xx, yy, ".")

    # ---- Pruefen und Ausgabe ---------------------------------------------------
    def erreichbar_machen(self, start, sonst: str = "r") -> None:
        """Alles Begehbare, das man von `start` nicht erreicht, wird `sonst`.
        Wasser zaehlt als begehbar fuer die Flut (tiefes nicht) - ein See
        ohne Ufer bliebe sonst stehen, wo niemand hinkommt."""
        da = [[False] * self.b for _ in range(self.h)]
        offen = deque([start])
        da[start[1]][start[0]] = True
        sperrt = FEST | {WASSER_TIEF}
        while offen:
            x, y = offen.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if self.drin(nx, ny) and not da[ny][nx] and self.k[ny][nx] not in sperrt:
                    da[ny][nx] = True
                    offen.append((nx, ny))
        for y in range(self.h):
            for x in range(self.b):
                if self.k[y][x] not in sperrt and not da[y][x]:
                    self.k[y][x] = sonst

    def rand(self, rnd, dicke: int = 3, zeichen: str = "r") -> None:
        """Unregelmaessiger Rand aus `zeichen`."""
        for y in range(self.h):
            for x in range(self.b):
                tief = min(x, y, self.b - 1 - x, self.h - 1 - y)
                if tief < dicke or (tief < dicke + 3 and rnd.random() < 0.3 * (dicke + 3 - tief) / 3):
                    self.k[y][x] = zeichen

    def pruefen(self) -> None:
        """Steht alles, was der Kopf nennt, auf begehbarem Boden, und ist
        jede Marke noch da? Sonst bricht das Werkzeug ab - lieber hier als
        im Spiel, wo ein Bot dann einen Weg in den Fels suchte."""
        sperrt = FEST | {WASSER_TIEF}
        fehler = []
        for weg in self.wege:
            for x, y in weg:
                if self.get(x, y) in sperrt:
                    fehler.append("Wegpunkt %d,%d liegt auf %r" % (x, y, self.get(x, y)))
        for x, y, name in self.punkte:
            if self.get(x, y) != "E":
                fehler.append("Punkt %s bei %d,%d ist %r statt E" % (name, x, y, self.get(x, y)))
        for seite, x, y, name, _fz in self.basen:
            if self.get(x, y) != "RB"[seite]:
                fehler.append("Basis %s bei %d,%d ist %r" % (name, x, y, self.get(x, y)))
        zahl = sum(z.count("E") for z in self.k)
        if zahl != len(self.punkte):
            fehler.append("%d Marken E, aber %d Punkte" % (zahl, len(self.punkte)))
        if fehler:
            raise SystemExit("Karte fehlerhaft:\n  " + "\n  ".join(fehler))

    def kopf_zeilen(self) -> list:
        """Die Zeilen fuer den Kopf: Basen, Punkte, Wege."""
        raus = []
        for i, (seite, x, y, name, fz) in enumerate(self.basen, 1):
            raus.append("basis%d: %d %d %d %s | %s" % (i, seite, x, y, name, fz))
        for i, (x, y, name) in enumerate(self.punkte, 1):
            raus.append("punkt%d: %d %d %s" % (i, x, y, name))
        for i, weg in enumerate(self.wege, 1):
            raus.append("weg%d: %s" % (i, " ".join("%d,%d" % p for p in weg)))
        return raus

    def als_text(self, kopf: list) -> str:
        zeilen = ["".join(z) for z in self.k]
        return "\n".join(kopf + self.kopf_zeilen() + [""]) + "\n--- ebene 0 ---\n" \
            + "\n".join(zeilen) + "\n"


def gespiegelt(lw: Leinwand, punkte) -> list:
    """Die Punkte eines Weges, um die Mitte gedreht."""
    return [lw.gegen(x, y) for x, y in punkte]


def glatt(punkte, schritte: int = 6) -> list:
    """Eine Folge von Stuetzpunkten als weiche Kurve (Catmull-Rom)."""
    if len(punkte) < 3:
        return list(punkte)
    p = [punkte[0]] + list(punkte) + [punkte[-1]]
    raus = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for s in range(schritte):
            t = s / float(schritte)
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            raus.append((x, y))
    raus.append(punkte[-1])
    return raus


def zufall(saat: int) -> random.Random:
    return random.Random(saat)
