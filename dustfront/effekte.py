"""
DUSTFRONT - Effekte: Rauch, Feuer, Druck, Truemmer (seit 0.34.122)
===================================================================

Ein eigenes System fuer alles, was bei Explosionen, Abschuessen und
Abstuerzen sichtbar passiert. Es ersetzt die Effekte, die dafuer mit
0.34.112 bis 0.34.120 kamen - gewuenscht war, sie "komplett neu, ohne Bezug
auf das Bestehende" zu bauen.

**Was anders ist als bei den alten Teilchen (`entities.Partikel`):**

* Jedes Teilchen hat eine **Hoehe** `z` mit eigener Geschwindigkeit und
  Schwerkraft. Gezeichnet wird es um `z` nach oben versetzt (wie alles, was
  in diesem Spiel in der Luft ist), Brocken werfen dabei einen Schatten,
  prallen am Boden ab und bleiben liegen. Was in der Luft platzt (Flak,
  Abwurf), beginnt in der Hoehe des Ziels - Splitter und Fetzen fallen von
  dort wirklich herunter.
* **Rauch und Feuer sind gemalte Sprites**, keine Quadrate oder flachen
  Kreise: ein Ballen mit buckligem Rand, beleuchtet von oben links (vier
  Toene wie die Fahrzeuge), Feuer mit weissem Kern und rotem Rand. Sie
  wachsen, steigen, treiben und verblassen weich.
* **Funken** ziehen einen Streifen in Flugrichtung, **Stofffetzen** flattern
  (sie werden schmal und breit, waehrend sie sich drehen) und sinken langsam,
  **Druckwellen** laufen als Ring ueber den Boden, ein **Blitz** erhellt
  kurz die Umgebung.
* Am Boden bleiben eigene Brandflecken und Truemmer (`fx_brand_N`,
  `fx_teil_N`).

Ausgeloest wird alles ueber `Welt.explosion` mit einer Art (siehe
`ARTEN`); die Meldung an den Gast bleibt dieselbe, der Gast spielt den
Effekt mit seinem eigenen Zufall nach - die Form kommt aus dem Ort, damit
beide dasselbe sehen. Fuer Dinge in der Luft traegt der `radius` der
Meldung die Hoehe (und bei Fallschirmen zusaetzlich die Seite:
`hoehe * 10 + seite`).

Gezeichnet in zwei Schichten (render.Renderer.effekte_zeichnen): was am
Boden liegt vor den Figuren, alles andere nach den Mauern, ueber allem.
"""

from __future__ import annotations

import math
import random

import pygame

from . import config as K
from .core import platzhalter

# ══════════════════════════════════════════════════════════════════
# Farben
# ══════════════════════════════════════════════════════════════════

# Je vier Toene, hell (Licht von oben links) bis dunkel, dazu der Rand.
PALETTEN = {
    "schwarz": [(70, 63, 58), (48, 43, 40), (32, 29, 27), (20, 18, 17), (10, 9, 8)],
    "grau": [(178, 170, 158), (140, 132, 122), (104, 98, 91), (74, 70, 65), (44, 41, 38)],
    "weiss": [(236, 232, 222), (208, 202, 190), (172, 166, 156), (132, 128, 120), (88, 84, 78)],
    "staub": [(222, 198, 152), (194, 168, 122), (160, 134, 94), (124, 102, 70), (82, 66, 44)],
    "erde": [(156, 124, 86), (124, 96, 64), (94, 72, 48), (66, 50, 34), (40, 30, 20)],
}
FEUER = [(255, 252, 226), (255, 222, 120), (252, 162, 56), (214, 84, 32), (128, 44, 24)]

# ══════════════════════════════════════════════════════════════════
# Sprites (gemalt beim ersten Gebrauch, gemerkt)
# ══════════════════════════════════════════════════════════════════

_BALLEN: dict = {}
_FLAMMEN: dict = {}
_BROCKEN: dict = {}
_LICHT: dict = {}
_LICHT_DIR = (-0.52, -0.62, 0.58)


def _buckel(seed: int) -> list:
    """Drei Wellen, die den Rand eines Ballens bucklig machen."""
    r = random.Random(seed)
    return [(r.uniform(0.06, 0.14), r.randint(3, 7), r.uniform(0, 6.28)) for _ in range(3)]


def ballen(radius: int, palette: str, variante: int) -> pygame.Surface:
    """Ein Rauchballen: bucklige Kugel, beleuchtet, vier Toene, dunkler Rand."""
    radius = max(2, int(radius))
    schluessel = (radius, palette, variante)
    s = _BALLEN.get(schluessel)
    if s is not None:
        return s
    toene = PALETTEN[palette]
    n = radius * 2 + 3
    s = pygame.Surface((n, n), pygame.SRCALPHA)
    wellen = _buckel(variante * 7919 + 17)
    # Kleine Buckel innen: Ballen auf dem Ballen, jeder mit eigenem Licht.
    r = random.Random(variante * 104729 + radius)
    innen = [(r.uniform(-0.45, 0.45), r.uniform(-0.45, 0.45), r.uniform(0.35, 0.55)) for _ in range(4)]
    m = n / 2.0
    lx, ly, lz = _LICHT_DIR
    for py in range(n):
        for px in range(n):
            dx = (px + 0.5 - m) / radius
            dy = (py + 0.5 - m) / radius
            d = math.hypot(dx, dy)
            if d > 1.25:
                continue
            w = math.atan2(dy, dx)
            rand = 1.0 + sum(a * math.sin(k * w + p) for a, k, p in wellen)
            if d > rand:
                continue
            q = d / rand
            nz = math.sqrt(max(0.0, 1.0 - q * q))
            licht = (lx * dx / rand + ly * dy / rand + lz * nz)
            for bx, by, br in innen:
                ex, ey = dx - bx, dy - by
                e = math.hypot(ex, ey) / br
                if e < 1.0:
                    bz = math.sqrt(1.0 - e * e)
                    licht = max(licht, 0.15 + 0.85 * (lx * ex / br + ly * ey / br + lz * bz))
            if q > 0.9:
                ton = 4 if q > 0.97 else 3
            elif licht > 0.78:
                ton = 0
            elif licht > 0.5:
                ton = 1
            elif licht > 0.18:
                ton = 2
            else:
                ton = 3
            s.set_at((px, py), toene[ton] + (255,))
    _BALLEN[schluessel] = s
    return s


def flamme(radius: int, variante: int) -> pygame.Surface:
    """Ein Feuerballen: weisser Kern, gelb, orange, roter Rand, zuengelnd."""
    radius = max(2, int(radius))
    schluessel = (radius, variante)
    s = _FLAMMEN.get(schluessel)
    if s is not None:
        return s
    n = radius * 2 + 3
    s = pygame.Surface((n, n), pygame.SRCALPHA)
    wellen = _buckel(variante * 3571 + 5)
    m = n / 2.0
    for py in range(n):
        for px in range(n):
            dx = (px + 0.5 - m) / radius
            dy = (py + 0.5 - m) / radius
            d = math.hypot(dx, dy)
            w = math.atan2(dy, dx)
            rand = 1.0 + sum(a * 1.6 * math.sin(k * w + p) for a, k, p in wellen)
            if d > rand:
                continue
            q = d / rand
            ton = 0 if q < 0.3 else 1 if q < 0.55 else 2 if q < 0.78 else 3 if q < 0.93 else 4
            s.set_at((px, py), FEUER[ton] + (255,))
    _FLAMMEN[schluessel] = s
    return s


def licht(radius: int) -> pygame.Surface:
    """Ein weicher Lichtfleck zum Addieren (Blitz)."""
    radius = max(4, int(radius))
    s = _LICHT.get(radius)
    if s is not None:
        return s
    n = radius * 2
    s = pygame.Surface((n, n))
    s.fill((0, 0, 0))
    for i in range(radius, 0, -2):
        f = 1.0 - i / radius
        pygame.draw.circle(s, (int(110 * f * f), int(84 * f * f), int(42 * f * f)), (radius, radius), i)
    _LICHT[radius] = s
    return s


def brocken(groesse: int, art: str, variante: int, winkel: int) -> pygame.Surface:
    """Ein Truemmerbrocken (Metall, Holz, Erde, Stein), gedreht."""
    schluessel = (groesse, art, variante, winkel)
    s = _BROCKEN.get(schluessel)
    if s is not None:
        return s
    flach = _BROCKEN.get((groesse, art, variante, None))
    if flach is None:
        farben = {"metall": ((110, 106, 98), (64, 60, 56), (26, 24, 22)),
                  "holz": ((168, 128, 80), (120, 86, 52), (52, 36, 22)),
                  "erde": ((150, 122, 86), (106, 84, 58), (48, 38, 26)),
                  "gruen": ((112, 128, 86), (74, 88, 56), (32, 38, 24)),
                  "rot": ((214, 86, 60), (150, 52, 36), (60, 22, 16))}[art]
        r = random.Random(variante * 31 + groesse)
        n = groesse * 2 + 4
        flach = pygame.Surface((n, n), pygame.SRCALPHA)
        ecken = []
        k = r.randint(4, 6)
        for i in range(k):
            w = i * 2 * math.pi / k + r.uniform(-0.3, 0.3)
            rr = groesse * r.uniform(0.55, 1.0)
            ecken.append((n / 2 + math.cos(w) * rr, n / 2 + math.sin(w) * rr * (0.55 if art == "holz" else 1.0)))
        pygame.draw.polygon(flach, farben[2], ecken)
        innen = [(n / 2 + (x - n / 2) * 0.72 - 0.5, n / 2 + (y - n / 2) * 0.72 - 0.5) for x, y in ecken]
        pygame.draw.polygon(flach, farben[1], innen)
        hell = [(n / 2 + (x - n / 2) * 0.4 - 1, n / 2 + (y - n / 2) * 0.4 - 1) for x, y in ecken]
        pygame.draw.polygon(flach, farben[0], hell)
        _BROCKEN[(groesse, art, variante, None)] = flach
    s = pygame.transform.rotate(flach, winkel) if winkel else flach
    _BROCKEN[schluessel] = s
    return s


# ══════════════════════════════════════════════════════════════════
# Das Teilchen
# ══════════════════════════════════════════════════════════════════

class Fx:
    """Ein Teilchen eines Effekts. `art`: rauch, feuer, funke, brocken,
    fetzen, ring, blitz, glut. Ort (x, y) am Boden, `z` die Hoehe darueber."""

    __slots__ = ("art", "x", "y", "z", "vx", "vy", "vz", "g", "zaeh", "alter", "dauer",
                 "r0", "r1", "palette", "variante", "farbe", "winkel", "dreh", "ebene",
                 "boden", "prallt", "liegt", "verzoegert", "deckung")

    def __init__(self, art: str, x: float, y: float, z: float, ebene: int, dauer: float) -> None:
        self.art = art
        self.x, self.y, self.z = float(x), float(y), float(z)
        self.vx = self.vy = self.vz = 0.0
        self.g = 0.0
        self.zaeh = 0.0
        self.alter = 0.0
        self.dauer = max(0.01, float(dauer))
        self.r0 = self.r1 = 4.0
        self.palette = "grau"
        self.variante = 0
        self.farbe = (255, 255, 255)
        self.winkel = 0.0
        self.dreh = 0.0
        self.ebene = int(ebene)
        self.boden = False          # in der Bodenschicht zeichnen (vor den Figuren)
        self.prallt = False         # springt am Boden einmal ab, bleibt dann liegen
        self.liegt = 0.0            # so lange bleibt es nach der Landung liegen
        self.verzoegert = 0.0       # erst nach so vielen Sekunden sichtbar
        self.deckung = 1.0

    @property
    def anteil(self) -> float:
        return min(1.0, self.alter / self.dauer)

    def schritt(self, dt: float) -> bool:
        if self.verzoegert > 0.0:
            self.verzoegert -= dt
            return True
        self.alter += dt
        if self.alter >= self.dauer:
            return False
        if self.zaeh > 0.0:
            f = math.exp(-self.zaeh * dt)
            self.vx *= f
            self.vy *= f
            if self.art != "brocken":
                self.vz *= f
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vz -= self.g * dt
        self.z += self.vz * dt
        self.winkel += self.dreh * dt
        if self.z < 0.0:
            self.z = 0.0
            if self.prallt and self.vz < -40.0:
                self.vz = -self.vz * 0.32
                self.vx *= 0.5
                self.vy *= 0.5
                self.dreh *= 0.5
            else:
                self.vz = 0.0
                self.vx *= 0.2
                self.vy *= 0.2
                self.dreh = 0.0
                if self.art in ("brocken", "fetzen") and self.liegt > 0.0:
                    # Gelandet: liegen bleiben, dann verblassen.
                    self.dauer = min(self.dauer, self.alter + self.liegt)
                    self.liegt = 0.0
        return True


# ══════════════════════════════════════════════════════════════════
# Zeichnen
# ══════════════════════════════════════════════════════════════════

def _zeichne(ziel, f: Fx, ex: float, ey: float) -> None:
    if f.verzoegert > 0.0:
        return
    a = f.anteil
    x = f.x - ex
    y = f.y - ey - f.z
    if f.art == "rauch":
        r = f.r0 + (f.r1 - f.r0) * (1.0 - (1.0 - a) ** 2)
        s = ballen(int(r), f.palette, f.variante % 4)
        deck = int(255 * f.deckung * (1.0 - a ** 1.6))
        if deck <= 6:
            return
        s.set_alpha(deck)
        ziel.blit(s, (int(x - s.get_width() / 2), int(y - s.get_height() / 2)))
        s.set_alpha(None)
    elif f.art == "feuer":
        r = f.r0 + (f.r1 - f.r0) * min(1.0, a * 2.2)
        # Zuengeln: alle 0,06 s eine andere Gestalt.
        v = (f.variante + int(f.alter / 0.06)) % 6
        s = flamme(int(r * (1.0 - 0.45 * a)), v)
        deck = int(255 * (1.0 - a ** 2.4))
        s.set_alpha(deck)
        ziel.blit(s, (int(x - s.get_width() / 2), int(y - s.get_height() / 2)))
        s.set_alpha(None)
    elif f.art == "glut":
        # Ein brennendes Stueck, das faellt: gelb, dann rot, dann dunkel.
        farbe = FEUER[min(4, 1 + int(a * 4))]
        g = max(1, int(f.r0 * (1.0 - a * 0.5)))
        pygame.draw.rect(ziel, farbe, (int(x), int(y), g, g))
    elif f.art == "funke":
        laenge = 0.035
        x2 = x - f.vx * laenge
        y2 = y - (f.vy - f.vz) * laenge
        kopf = (255, 248, 220) if a < 0.4 else f.farbe
        schweif = tuple(int(c * (1.0 - a) * 0.8) for c in f.farbe)
        pygame.draw.line(ziel, schweif, (x2, y2), (x, y), 1)
        pygame.draw.rect(ziel, kopf, (int(x), int(y), 2 if a < 0.3 else 1, 2 if a < 0.3 else 1))
    elif f.art == "brocken":
        if f.z > 1.0:
            sch = max(2, int(f.r0))
            pygame.draw.ellipse(ziel, (16, 12, 9), (int(x - sch), int(f.y - ey - sch * 0.4), sch * 2, max(2, int(sch * 0.8))))
        s = brocken(int(f.r0), f.palette, f.variante % 5, int(f.winkel / 30.0) * 30 % 360)
        if a > 0.8:
            s.set_alpha(int(255 * (1.0 - a) / 0.2))
        ziel.blit(s, (int(x - s.get_width() / 2), int(y - s.get_height() / 2)))
        s.set_alpha(None)
    elif f.art == "fetzen":
        # Ein Stueck Stoff, das sich dreht: mal breit, mal schmal (flattern).
        breit = max(1.0, f.r0 * abs(math.cos(math.radians(f.winkel * 2.3))))
        lang = f.r0 * 1.6
        w = math.radians(f.winkel)
        cx, cy = math.cos(w), math.sin(w)
        qx, qy = -cy, cx
        pkte = [(x - cx * lang - qx * breit * 0.5, y - cy * lang - qy * breit * 0.5),
                (x + cx * lang - qx * breit * 0.3, y + cy * lang - qy * breit * 0.3),
                (x + cx * lang + qx * breit * 0.3, y + cy * lang + qy * breit * 0.3),
                (x - cx * lang + qx * breit * 0.5, y - cy * lang + qy * breit * 0.5)]
        if f.z > 2.0:
            pygame.draw.polygon(ziel, (20, 16, 12), [(px + 1, py + f.z) for px, py in pkte])
        dunkel = tuple(int(c * 0.62) for c in f.farbe)
        pygame.draw.polygon(ziel, dunkel, pkte)
        pygame.draw.polygon(ziel, f.farbe, [(px * 0.8 + x * 0.2, py * 0.8 + y * 0.2) for px, py in pkte])
    elif f.art == "ring":
        r = f.r0 + (f.r1 - f.r0) * (1.0 - (1.0 - a) ** 2.5)
        deck = int(220 * (1.0 - a) * f.deckung)
        if deck <= 8 or r < 2:
            return
        n = int(r * 2 + 8)
        flaeche = pygame.Surface((n, n), pygame.SRCALPHA)
        dick = max(1, int((1.0 - a) * 6 + 1))
        pygame.draw.circle(flaeche, f.farbe + (deck,), (n // 2, n // 2), int(r), dick)
        pygame.draw.circle(flaeche, (255, 255, 255, deck // 3), (n // 2, n // 2), max(1, int(r) - dick), 1)
        ziel.blit(flaeche, (int(x - n / 2), int(y - n / 2)))
    elif f.art == "blitz":
        r = int(f.r0 * (0.6 + 0.4 * (1.0 - a)))
        s = licht(r)
        k = 1.0 - a
        s2 = s.copy()
        s2.fill((int(255 * k), int(255 * k), int(255 * k)), special_flags=pygame.BLEND_MULT)
        ziel.blit(s2, (int(x - r), int(y - r)), special_flags=pygame.BLEND_ADD)


def zeichnen(ziel, liste, ebene: int, ecke, boden: bool) -> None:
    """Alle Teilchen der Ebene in dieser Schicht."""
    ex, ey = ecke.x, ecke.y
    breite, hoehe = ziel.get_size()
    for f in liste:
        if f.ebene != ebene or f.boden != boden:
            continue
        if not (-120 < f.x - ex < breite + 120 and -220 < f.y - ey - f.z < hoehe + 120):
            continue
        _zeichne(ziel, f, ex, ey)


# ══════════════════════════════════════════════════════════════════
# Bausteine
# ══════════════════════════════════════════════════════════════════

def _rnd(pos, kennung: int) -> random.Random:
    return random.Random(int(abs(pos[0]) * 7 + abs(pos[1]) * 13) * 31 + kennung)


def _neu(welt, f: Fx) -> Fx:
    welt.effekte.append(f)
    return f


def rauch(welt, r, x, y, z, ebene, palette, r0, r1, dauer, vx=0.0, vy=0.0, vz=0.0,
          zaeh=1.6, g=0.0, verzoegert=0.0, boden=False, deckung=1.0) -> Fx:
    f = Fx("rauch", x, y, z, ebene, dauer * r.uniform(0.85, 1.15))
    f.palette = palette
    f.variante = r.randrange(4)
    f.r0, f.r1 = r0, r1
    f.vx, f.vy, f.vz = vx, vy, vz
    f.zaeh, f.g = zaeh, g
    f.verzoegert = verzoegert
    f.boden = boden
    f.deckung = deckung
    return _neu(welt, f)


def feuer(welt, r, x, y, z, ebene, r0, r1, dauer, vx=0.0, vy=0.0, vz=0.0, verzoegert=0.0) -> Fx:
    f = Fx("feuer", x, y, z, ebene, dauer * r.uniform(0.85, 1.15))
    f.variante = r.randrange(6)
    f.r0, f.r1 = r0, r1
    f.vx, f.vy, f.vz = vx, vy, vz
    f.zaeh = 3.0
    f.verzoegert = verzoegert
    return _neu(welt, f)


def funken(welt, r, x, y, z, ebene, anzahl, tempo, dauer, farbe=(255, 196, 96), richtung=None,
           streuung=360.0, hoch=0.6) -> None:
    for _ in range(anzahl):
        w = math.radians((richtung if richtung is not None else 0.0) + r.uniform(-streuung / 2, streuung / 2))
        v = r.uniform(tempo * 0.35, tempo)
        f = Fx("funke", x, y, z, ebene, dauer * r.uniform(0.5, 1.2))
        f.vx, f.vy = math.cos(w) * v, math.sin(w) * v
        f.vz = r.uniform(-0.2, 1.0) * v * hoch
        f.g = 380.0
        f.zaeh = 2.2
        f.farbe = farbe
        _neu(welt, f)


def brockenwurf(welt, r, x, y, z, ebene, anzahl, tempo, art, groesse=(2, 4), hoch=(0.4, 1.2),
                liegen=4.0, glut=0) -> None:
    for i in range(anzahl):
        w = r.uniform(0.0, 2 * math.pi)
        v = r.uniform(tempo * 0.3, tempo)
        f = Fx("brocken", x, y, z, ebene, 12.0)
        f.vx, f.vy = math.cos(w) * v, math.sin(w) * v
        f.vz = v * r.uniform(*hoch)
        f.g = 520.0
        f.zaeh = 0.6
        f.prallt = True
        f.liegt = liegen * r.uniform(0.6, 1.3)
        f.r0 = r.randint(groesse[0], groesse[1])
        f.palette = art
        f.variante = r.randrange(5)
        f.winkel = r.uniform(0, 360)
        f.dreh = r.uniform(-720, 720)
        _neu(welt, f)
    for _ in range(glut):
        w = r.uniform(0.0, 2 * math.pi)
        v = r.uniform(tempo * 0.3, tempo * 0.8)
        f = Fx("glut", x, y, z, ebene, r.uniform(0.8, 1.8))
        f.vx, f.vy = math.cos(w) * v, math.sin(w) * v
        f.vz = v * r.uniform(0.3, 1.1)
        f.g = 420.0
        f.zaeh = 0.8
        f.r0 = r.choice((1, 2, 2, 3))
        _neu(welt, f)


def fetzen(welt, r, x, y, z, ebene, anzahl, farben, groesse=(2, 4), tempo=90.0, dauer=3.2) -> None:
    for _ in range(anzahl):
        w = r.uniform(0.0, 2 * math.pi)
        v = r.uniform(tempo * 0.3, tempo)
        f = Fx("fetzen", x, y, z, ebene, dauer * r.uniform(0.7, 1.3))
        f.vx, f.vy = math.cos(w) * v, math.sin(w) * v * 0.7
        f.vz = r.uniform(10.0, 60.0)
        f.g = 60.0                     # Stoff faellt langsam, der Wind bremst ihn
        f.zaeh = 1.8
        f.farbe = r.choice(farben)
        f.r0 = r.randint(groesse[0], groesse[1])
        f.winkel = r.uniform(0, 360)
        f.dreh = r.uniform(-260, 260)
        f.liegt = 3.0
        _neu(welt, f)


def ring(welt, x, y, ebene, r0, r1, dauer, farbe=(232, 214, 176), boden=True, z=0.0, deckung=1.0) -> Fx:
    f = Fx("ring", x, y, z, ebene, dauer)
    f.r0, f.r1 = r0, r1
    f.farbe = farbe
    f.boden = boden
    f.deckung = deckung
    return _neu(welt, f)


def blitz(welt, x, y, z, ebene, radius, dauer=0.12) -> Fx:
    f = Fx("blitz", x, y, z, ebene, dauer)
    f.r0 = radius
    return _neu(welt, f)


def staubwand(welt, r, x, y, ebene, radius, anzahl, palette="staub", tempo=260.0, groesse=(6, 12),
              dauer=1.6) -> None:
    """Staub, der von der Mitte aus ueber den Boden rollt."""
    for i in range(anzahl):
        w = i * 2 * math.pi / anzahl + r.uniform(-0.2, 0.2)
        v = tempo * r.uniform(0.6, 1.0)
        rauch(welt, r, x + math.cos(w) * radius * 0.25, y + math.sin(w) * radius * 0.25, 1.0, ebene,
              palette, groesse[0], groesse[1] * r.uniform(1.0, 1.6), dauer,
              vx=math.cos(w) * v, vy=math.sin(w) * v, vz=r.uniform(4, 18), zaeh=2.4, boden=False)


# ══════════════════════════════════════════════════════════════════
# Die Effekte
# ══════════════════════════════════════════════════════════════════

def flak(welt, pos, ebene: int, hoehe: float) -> None:
    """Eine Flakgranate platzt (am Boden `hoehe` 0, sonst in der Hoehe des
    Ziels): ein grellweisser Kern, eine schwarze Wolke, die schlagartig
    aufquillt und dann lange als dunkler Fleck stehen bleibt und langsam
    abtreibt, ein Kranz Splitter."""
    r = _rnd(pos, 1)
    x, y, z = pos[0], pos[1], hoehe
    blitz(welt, x, y, z, ebene, 46, 0.09)
    feuer(welt, r, x, y, z, ebene, 3, 9, 0.14)
    wind = r.uniform(6.0, 14.0)
    for i in range(9):
        w = r.uniform(0, 2 * math.pi)
        d = r.uniform(0.0, 7.0)
        rauch(welt, r, x + math.cos(w) * d, y + math.sin(w) * d * 0.7, z + r.uniform(-3, 3), ebene,
              "schwarz", r.uniform(3, 5), r.uniform(9, 14), r.uniform(3.2, 4.6),
              vx=math.cos(w) * r.uniform(30, 70) + wind, vy=math.sin(w) * r.uniform(20, 50),
              vz=r.uniform(-4, 10), zaeh=3.4)
    for i in range(3):
        rauch(welt, r, x + r.uniform(-5, 5), y + r.uniform(-4, 4), z, ebene, "grau",
              r.uniform(2, 3), r.uniform(6, 9), r.uniform(2.6, 3.4), vx=wind, vz=6.0,
              zaeh=2.0, verzoegert=0.15)
    funken(welt, r, x, y, z, ebene, 14, 380.0, 0.32, farbe=(255, 170, 70), hoch=0.25)
    if hoehe <= 1.0:
        brockenwurf(welt, r, x, y, 0.0, ebene, 4, 120.0, "erde", (1, 2), liegen=1.5)
        rauch(welt, r, x, y, 0.0, ebene, "staub", 4, 12, 1.4, vz=10.0, boden=True)
    welt.ruckeln(1.0, "explosion", pygame.Vector2(x, y), ebene)
    welt.klang("flak_burst", 0.9, pygame.Vector2(x, y), ebene)


def kiste_platzt(welt, pos, ebene: int, hoehe: float) -> None:
    """Eine Kiste am Schirm platzt: Bretter fliegen auseinander und fallen,
    der Inhalt (rot/gruen) streut, der Schirm reisst in Fetzen."""
    r = _rnd(pos, 2)
    x, y, z = pos[0], pos[1], hoehe
    blitz(welt, x, y, z, ebene, 36, 0.08)
    feuer(welt, r, x, y, z, ebene, 3, 7, 0.16)
    rauch(welt, r, x, y, z, ebene, "grau", 4, 11, 1.8, vz=8.0, zaeh=2.0)
    brockenwurf(welt, r, x, y, z, ebene, 9, 140.0, "holz", (2, 4), hoch=(-0.1, 0.5), liegen=5.0)
    brockenwurf(welt, r, x, y, z, ebene, 5, 110.0, "gruen", (1, 2), hoch=(0.0, 0.5), liegen=4.0)
    brockenwurf(welt, r, x, y, z, ebene, 3, 90.0, "rot", (1, 2), hoch=(0.0, 0.5), liegen=4.0)
    fetzen(welt, r, x, y, z + 18, ebene, 14, [(232, 226, 210), (200, 70, 50)], (2, 3), 70.0)
    welt.klang("flak_burst", 0.6, pygame.Vector2(x, y), ebene)


def mensch_luft(welt, pos, ebene: int, hoehe: float) -> None:
    """Ein Fallschirmjaeger wird in der Luft getroffen: eine rote Wolke,
    Tropfen, die fallen, Fetzen des Schirms."""
    r = _rnd(pos, 3)
    x, y, z = pos[0], pos[1], hoehe
    for _ in range(6):
        rauch(welt, r, x + r.uniform(-3, 3), y + r.uniform(-3, 3), z, ebene, "erde", 2, 6, 0.9,
              vx=r.uniform(-40, 40), vy=r.uniform(-30, 30), zaeh=3.0)
    for _ in range(14):
        f = Fx("funke", x, y, z, ebene, r.uniform(0.8, 1.4))       # Tropfen, die fallen
        w = r.uniform(0, 2 * math.pi)
        v = r.uniform(30, 120)
        f.vx, f.vy, f.vz = math.cos(w) * v, math.sin(w) * v * 0.7, r.uniform(-20, 40)
        f.g = 300.0
        f.farbe = (150, 20, 18)
        _neu(welt, f)
    fetzen(welt, r, x, y, z + 14, ebene, 10, [(232, 226, 210), (110, 116, 88)], (2, 3), 60.0)


def schirm_reisst(welt, pos, ebene: int, hoehe: float, seite: int) -> None:
    """Der Schirm eines Fahrzeugs reisst: drei grosse Bahnen und viele kleine
    Fetzen fliegen auseinander und taumeln langsam hinunter, die Leinen
    peitschen (helle Striche)."""
    r = _rnd(pos, 4)
    kombi = K.TEAMS["kombi"][seite] if 0 <= seite < 2 else None
    tuch = kombi["rumpf"] if kombi else (200, 70, 50)
    x, y, z = pos[0], pos[1], hoehe + 30.0
    for _ in range(3):
        f = Fx("fetzen", x + r.uniform(-8, 8), y, z, ebene, 4.5)
        w = r.uniform(-2.4, -0.7)
        f.vx, f.vy, f.vz = math.cos(w) * 50, math.sin(w) * 30, r.uniform(20, 50)
        f.g, f.zaeh = 40.0, 1.2
        f.farbe = r.choice([tuch, (232, 226, 210)])
        f.r0 = r.randint(6, 9)
        f.winkel = r.uniform(0, 360)
        f.dreh = r.uniform(-120, 120)
        f.liegt = 3.0
        _neu(welt, f)
    fetzen(welt, r, x, y, z, ebene, 18, [tuch, (232, 226, 210)], (2, 4), 110.0, 3.8)
    funken(welt, r, x, y, z - 20, ebene, 10, 220.0, 0.35, farbe=(210, 200, 180), hoch=0.4)
    rauch(welt, r, x, y, z - 26, ebene, "grau", 3, 8, 1.2, vz=4.0)
    welt.klang("fallschirm_riss", 0.8, pygame.Vector2(x, y), ebene)


def absturz(welt, pos, ebene: int) -> None:
    """Ein Wagen schlaegt ohne Schirm auf: eine Staubwand rollt nach aussen,
    eine Wolke steigt, Erdbrocken und Funken fliegen, ein Druckring."""
    r = _rnd(pos, 5)
    x, y = pos[0], pos[1]
    ring(welt, x, y, ebene, 10, 110, 0.6, (226, 206, 160))
    staubwand(welt, r, x, y, ebene, 40, 22, "staub", 300.0, (6, 11), 1.8)
    for _ in range(6):
        rauch(welt, r, x + r.uniform(-14, 14), y + r.uniform(-10, 10), 2, ebene, "staub", 8, 18, 2.4,
              vz=r.uniform(20, 50), zaeh=1.2)
    brockenwurf(welt, r, x, y, 2, ebene, 14, 220.0, "erde", (2, 4), liegen=4.0)
    brockenwurf(welt, r, x, y, 4, ebene, 5, 180.0, "metall", (2, 3), liegen=6.0)
    funken(welt, r, x, y, 4, ebene, 18, 320.0, 0.45)
    welt.ruckeln(9.0, "explosion", pygame.Vector2(x, y), ebene)
    welt.klang("absturz", 1.0, pygame.Vector2(x, y), ebene)


def raketenstart(welt, pos, ebene: int, winkel: float) -> None:
    """Eine Rakete verlaesst das Rohr. Vorn ein kurzer Feuerstoss; hinten der
    Rueckstrahl - wie bei einer Panzerfaust, nur viel mehr: ein Kegel aus
    weissem Druckrauch schiesst nach hinten, quillt auf und bleibt lange
    stehen, am Boden reisst er eine breite Staubwand hoch, ein flacher
    Druckring laeuft ueber den Boden."""
    r = _rnd(pos, 6 + int(winkel))
    x, y = pos[0], pos[1]
    vor = (math.cos(math.radians(winkel)), math.sin(math.radians(winkel)))
    hinten = winkel + 180.0
    hx, hy = x - vor[0] * 44.0, y - vor[1] * 44.0
    blitz(welt, x, y, 10, ebene, 40, 0.08)
    feuer(welt, r, x, y, 10, ebene, 3, 8, 0.12, vx=vor[0] * 120, vy=vor[1] * 120)
    blitz(welt, hx, hy, 6, ebene, 60, 0.12)
    for i in range(5):
        feuer(welt, r, hx, hy, 8, ebene, 4, 10, 0.22,
              vx=math.cos(math.radians(hinten + r.uniform(-12, 12))) * r.uniform(200, 380),
              vy=math.sin(math.radians(hinten + r.uniform(-12, 12))) * r.uniform(200, 380), vz=0.0)
    for i in range(16):
        w = math.radians(hinten + r.uniform(-22, 22))
        v = r.uniform(250, 620)
        rauch(welt, r, hx, hy, 8, ebene, "weiss", 4, r.uniform(11, 20), r.uniform(2.6, 3.8),
              vx=math.cos(w) * v, vy=math.sin(w) * v, vz=r.uniform(4, 22), zaeh=3.2)
    for i in range(22):
        w = math.radians(hinten + r.uniform(-55, 55))
        v = r.uniform(180, 420)
        rauch(welt, r, hx + math.cos(w) * 20, hy + math.sin(w) * 20, 1, ebene, "staub", 5,
              r.uniform(10, 18), r.uniform(1.8, 2.8), vx=math.cos(w) * v, vy=math.sin(w) * v,
              vz=r.uniform(2, 12), zaeh=2.8)
    ring(welt, hx - vor[0] * 20, hy - vor[1] * 20, ebene, 6, 70, 0.45, (236, 222, 188))
    brockenwurf(welt, r, hx, hy, 1, ebene, 6, 160.0, "erde", (1, 2), hoch=(0.2, 0.6), liegen=2.0)
    welt.ruckeln(4.5, "explosion", pygame.Vector2(x, y), ebene)


def rauchspur(welt, x, y, z, ebene, seed: int) -> None:
    """Ein Ballen Rauch hinter einer fliegenden Rakete (laeuft je Bild)."""
    r = random.Random(seed)
    rauch(welt, r, x, y, z, ebene, "weiss" if r.random() < 0.6 else "grau", 2, r.uniform(5, 8),
          r.uniform(1.4, 2.2), vx=r.uniform(-6, 6), vy=r.uniform(-6, 6), vz=r.uniform(2, 8), zaeh=2.0)


def einschlag(welt, pos, ebene: int, groesse: float = 1.0) -> None:
    """Eine Rakete oder Bombe schlaegt ein: Feuerball, der aufsteigt, eine
    Erdfontaene, schwarzer Rauch, ein Druckring, ein Brandfleck."""
    r = _rnd(pos, 7)
    x, y = pos[0], pos[1]
    g = groesse
    blitz(welt, x, y, 6, ebene, int(80 * g), 0.14)
    ring(welt, x, y, ebene, 8, 90 * g, 0.5, (238, 222, 186))
    for i in range(int(6 * g) + 2):
        feuer(welt, r, x + r.uniform(-10, 10) * g, y + r.uniform(-8, 8) * g, r.uniform(2, 10), ebene,
              4 * g, r.uniform(9, 15) * g, r.uniform(0.35, 0.6), vz=r.uniform(20, 70),
              verzoegert=r.uniform(0.0, 0.08))
    for i in range(int(8 * g) + 3):
        rauch(welt, r, x + r.uniform(-12, 12) * g, y + r.uniform(-10, 10) * g, r.uniform(4, 14), ebene,
              "schwarz", 5 * g, r.uniform(12, 20) * g, r.uniform(2.6, 4.0),
              vx=r.uniform(-20, 20), vy=r.uniform(-14, 14), vz=r.uniform(14, 40), zaeh=1.4,
              verzoegert=r.uniform(0.08, 0.3))
    for i in range(int(10 * g)):
        w = r.uniform(0, 2 * math.pi)
        rauch(welt, r, x, y, 2, ebene, "erde", 4, r.uniform(8, 13) * g, r.uniform(1.0, 1.6),
              vx=math.cos(w) * r.uniform(40, 120) * g, vy=math.sin(w) * r.uniform(30, 90) * g,
              vz=r.uniform(60, 160) * g, g=160.0, zaeh=1.6)
    brockenwurf(welt, r, x, y, 2, ebene, int(12 * g), 200.0 * g, "erde", (1, 3), liegen=3.0, glut=int(8 * g))
    funken(welt, r, x, y, 4, ebene, int(18 * g), 380.0 * g, 0.5)
    welt.brand_dekal(pygame.Vector2(x, y), ebene, int(min(3, g * 1.6)), r.uniform(0, 360))
    welt.ruckeln(5.0 * g, "explosion", pygame.Vector2(x, y), ebene)


def werfer_explosion(welt, pos, ebene: int, radius: float) -> None:
    """Der Werfer geht hoch - die groesste Explosion des Spiels. In Stufen:
    ein weisser Blitz ueber das ganze Bild; ein Feuerball aus vielen Ballen,
    der aufsteigt; die Raketen in den Rohren gehen nacheinander los (kleinere
    Explosionen rundherum, zwei fliegen mit Rauchspur davon); eine Druckwelle
    rollt ueber den Boden und reisst Staub mit; Metallteile fliegen in hohen
    Boegen, prallen ab und bleiben liegen; ein schwarzer Rauchpilz steigt
    und bleibt lange stehen; brennende Stuecke regnen herunter."""
    r = _rnd(pos, 8)
    x, y = pos[0], pos[1]
    blitz(welt, x, y, 10, ebene, 260, 0.3)
    ring(welt, x, y, ebene, 12, radius * 1.1, 0.8, (246, 236, 210))
    ring(welt, x, y, ebene, 8, radius * 0.7, 1.1, (214, 190, 146), deckung=0.8)
    for i in range(22):
        w = r.uniform(0, 2 * math.pi)
        d = r.uniform(0, 26)
        feuer(welt, r, x + math.cos(w) * d, y + math.sin(w) * d * 0.7, r.uniform(4, 20), ebene,
              6, r.uniform(16, 28), r.uniform(0.6, 1.1),
              vx=math.cos(w) * r.uniform(20, 90), vy=math.sin(w) * r.uniform(15, 70), vz=r.uniform(40, 120),
              verzoegert=r.uniform(0.0, 0.18))
    # Die Raketen gehen nach: kleine Explosionen im Umkreis, nacheinander.
    for i in range(5):
        w = r.uniform(0, 2 * math.pi)
        d = r.uniform(30, 90)
        px, py = x + math.cos(w) * d, y + math.sin(w) * d
        t = 0.15 + i * r.uniform(0.12, 0.25)
        blitz(welt, px, py, 10, ebene, 60, 0.1).verzoegert = t
        for _ in range(4):
            feuer(welt, r, px, py, r.uniform(6, 16), ebene, 4, r.uniform(9, 14), 0.4, vz=r.uniform(20, 60),
                  verzoegert=t)
        for _ in range(3):
            rauch(welt, r, px, py, 10, ebene, "schwarz", 5, r.uniform(12, 18), 3.0, vz=24, zaeh=1.4,
                  verzoegert=t + 0.1)
    # Zwei Raketen fliegen davon, mit einer Spur aus Rauchballen.
    for i in range(2):
        w = r.uniform(0, 2 * math.pi)
        for k in range(14):
            d = 18 + k * 16
            rauch(welt, r, x + math.cos(w) * d, y + math.sin(w) * d, 14 + k * 3, ebene, "grau", 3,
                  r.uniform(6, 9), 2.4, vz=4, zaeh=2.0, verzoegert=0.1 + k * 0.03)
        f = Fx("funke", x, y, 14, ebene, 0.6)
        f.vx, f.vy, f.vz = math.cos(w) * 520, math.sin(w) * 520, 90
        f.farbe = (255, 220, 140)
        _neu(welt, f)
    staubwand(welt, r, x, y, ebene, radius * 0.4, 34, "staub", 520.0, (10, 18), 2.6)
    staubwand(welt, r, x, y, ebene, radius * 0.25, 22, "erde", 340.0, (8, 14), 2.2)
    # Der Pilz: schwarzer Rauch, der hoch steigt und oben breit wird.
    for i in range(30):
        h = r.uniform(0.0, 1.0)
        rauch(welt, r, x + r.uniform(-24, 24) * (0.5 + h), y + r.uniform(-16, 16), 10 + h * 30, ebene,
              "schwarz", 8, r.uniform(22, 36) * (0.7 + h * 0.6), r.uniform(5.5, 8.5),
              vx=r.uniform(-14, 14) + 8, vy=r.uniform(-8, 8), vz=30 + h * 70, zaeh=0.9,
              verzoegert=0.25 + h * 0.6)
    for i in range(10):
        rauch(welt, r, x + r.uniform(-40, 40), y + r.uniform(-30, 30), 6, ebene, "grau", 10,
              r.uniform(22, 32), r.uniform(6, 9), vx=8, vz=12, zaeh=1.0, verzoegert=0.9)
    brockenwurf(welt, r, x, y, 10, ebene, 26, 420.0, "metall", (2, 5), hoch=(0.6, 1.6), liegen=9.0, glut=40)
    brockenwurf(welt, r, x, y, 4, ebene, 20, 300.0, "erde", (1, 3), liegen=4.0)
    funken(welt, r, x, y, 10, ebene, 80, 700.0, 0.9, hoch=0.8)
    # Was liegen bleibt: Brandfleck und Teile (Dekale).
    welt.brand_dekal(pygame.Vector2(x, y), ebene, 3, r.uniform(0, 360))
    for i in range(10):
        d = r.uniform(30, radius * 0.8)
        w = r.uniform(0, 2 * math.pi)
        welt.bild_dekal("fx_teil_%d" % (i % 8), pygame.Vector2(x + math.cos(w) * d, y + math.sin(w) * d),
                        ebene, r.uniform(0, 360))
    welt.ruckeln(26.0, "explosion", pygame.Vector2(x, y), ebene)
    welt.klang("werfer_explosion", 1.0, pygame.Vector2(x, y), ebene)


def bombe_los(welt, pos, ebene: int, hoehe: float) -> None:
    """Die Bombe loest sich vom Traeger: ein kurzer Ruck, ein Woelkchen und
    ein paar Funken am Haken - man sieht, dass sie faellt."""
    r = _rnd(pos, 9)
    x, y, z = pos[0], pos[1], max(0.0, hoehe - 2.0)
    rauch(welt, r, x, y, z, ebene, "grau", 2, 6, 0.7, vz=-10.0, zaeh=3.0)
    funken(welt, r, x, y, z, ebene, 5, 90.0, 0.25, farbe=(255, 214, 140), hoch=0.2)


def bombe(welt, pos, ebene: int) -> None:
    """Die Bombe schlaegt ein - schwerer als eine Rakete: eine Erdfontaene
    schiesst hoch und regnet herunter, ein Feuerball, schwarzer Rauch, ein
    grosser Druckring und ein Krater."""
    r = _rnd(pos, 10)
    x, y = pos[0], pos[1]
    einschlag(welt, pos, ebene, 1.4)
    for i in range(18):
        w = r.uniform(0, 2 * math.pi)
        v = r.uniform(20, 70)
        rauch(welt, r, x + math.cos(w) * 6, y + math.sin(w) * 4, 4, ebene, "erde", 4, r.uniform(7, 12),
              r.uniform(1.4, 2.0), vx=math.cos(w) * v, vy=math.sin(w) * v * 0.6, vz=r.uniform(160, 300),
              g=330.0, zaeh=0.8)
    brockenwurf(welt, r, x, y, 4, ebene, 18, 160.0, "erde", (1, 3), hoch=(1.2, 2.4), liegen=4.0)
    welt.brand_dekal(pygame.Vector2(x, y), ebene, 2, r.uniform(0, 360))


# ══════════════════════════════════════════════════════════════════
# Dekale am Boden
# ══════════════════════════════════════════════════════════════════

def _brand(i: int):
    def z():
        groesse = (28, 44, 64, 96)[i]
        n = groesse
        s = pygame.Surface((n, n), pygame.SRCALPHA)
        r = random.Random(5150 + i)
        m = n / 2
        for k in range(18 + i * 8):
            w = r.uniform(0, 2 * math.pi)
            d = r.uniform(0, m * 0.55)
            rr = r.uniform(m * 0.18, m * 0.42)
            pygame.draw.circle(s, (20, 16, 13, r.randint(70, 130)),
                               (int(m + math.cos(w) * d), int(m + math.sin(w) * d)), int(rr))
        for k in range(10 + i * 6):
            w = r.uniform(0, 2 * math.pi)
            d = r.uniform(m * 0.3, m * 0.9)
            pygame.draw.line(s, (26, 20, 16, 120), (m, m), (m + math.cos(w) * d, m + math.sin(w) * d),
                             r.choice((1, 2)))
        pygame.draw.circle(s, (12, 10, 9, 170), (int(m), int(m)), int(m * 0.22))
        return s
    return z


def _teil(i: int):
    def z():
        s = pygame.Surface((24, 24), pygame.SRCALPHA)
        art = ("metall", "metall", "erde", "metall", "holz", "metall", "rot", "metall")[i]
        b = brocken(4 + i % 3, art, i, (i * 47) % 360)
        s.blit(b, b.get_rect(center=(12, 12)))
        dunkel = s.copy()
        dunkel.fill((150, 140, 130, 255), special_flags=pygame.BLEND_RGBA_MULT)
        return dunkel
    return z


for _i in range(4):
    platzhalter("fx_brand_%d" % _i)(_brand(_i))
for _i in range(8):
    platzhalter("fx_teil_%d" % _i)(_teil(_i))


# ══════════════════════════════════════════════════════════════════
# Welt.explosion -> Effekt
# ══════════════════════════════════════════════════════════════════

def _seite_hoehe(radius: float) -> tuple:
    """Fallschirme: `radius` = Hoehe * 10 + Seite (0 oder 1)."""
    r = int(round(radius))
    return r // 10, r % 10


# Art -> Aufruf (welt, pos, ebene, radius). Was der Radius traegt, steht dabei.
ARTEN = {
    "flak": lambda w, p, e, r: flak(w, p, e, r),                       # r = Hoehe
    "luft_kiste": lambda w, p, e, r: kiste_platzt(w, p, e, r),         # r = Hoehe
    "luft_mensch": lambda w, p, e, r: mensch_luft(w, p, e, r),         # r = Hoehe
    "fallschirm_riss": lambda w, p, e, r: schirm_reisst(w, p, e, *_seite_hoehe(r)),
    "absturz": lambda w, p, e, r: absturz(w, p, e),
    "werfer_start": lambda w, p, e, r: raketenstart(w, p, e, r),       # r = Richtung
    "werfer_gross": lambda w, p, e, r: werfer_explosion(w, p, e, r),   # r = Radius
    "einschlag": lambda w, p, e, r: einschlag(w, p, e, max(0.4, r)),   # r = Groesse
    "bombe": lambda w, p, e, r: bombe(w, p, e),
    "bombe_los": lambda w, p, e, r: bombe_los(w, p, e, r),            # r = Hoehe
}
