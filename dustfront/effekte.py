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
* **Rauch und Feuer sind Wolken aus Pixel-Teilchen** (seit 0.34.126, wie
  die aelteren Explosionen; vorher gemalte Ballen mit buckligem Rand):
  oben links heller, Feuer mit weissem Kern und rotem Rand. Sie wachsen
  (die Teilchen ruecken auseinander), steigen, treiben und verblassen weich.
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


# Seit 0.34.126 sind Rauch und Feuer Wolken aus kleinen Pixel-Teilchen, wie
# die aelteren Explosionen (entities.Partikel) - vorher waren es gemalte
# Ballen mit buckligem Rand. Gemeldet: "nicht viele kleine, komisch geformte
# Wolken, sondern mehr eine grosse Partikelwolke". Jedes Teilchen hat in
# einer Wolke einen festen Platz (aus `variante`), nur der Abstand zur Mitte
# waechst mit dem Radius - so fliegen die Teilchen sichtbar auseinander, und
# was sich ueberlappt, wird eine einzige Wolke. Ohne Rand.
_TEILCHEN: dict = {}
TEILCHEN_HOECHSTENS = 320


def _teilchen(variante: int, feuer: bool) -> list:
    """Die festen Plaetze der Teilchen einer Wolke: (Abstand 0..1, Winkel,
    Groesse, Licht) - dichter zur Mitte."""
    schluessel = (variante, feuer)
    t = _TEILCHEN.get(schluessel)
    if t is not None:
        return t
    r = random.Random(variante * 7919 + (17 if not feuer else 29))
    t = []
    for _ in range(TEILCHEN_HOECHSTENS):
        d = r.random() ** (0.85 if not feuer else 1.1)
        w = r.uniform(0.0, 2.0 * math.pi)
        groesse = r.choice((1, 2, 2, 2, 3)) if not feuer else r.choice((1, 2, 2, 3))
        t.append((d, w, groesse, r.uniform(-0.35, 0.35)))
    _TEILCHEN[schluessel] = t
    return t


def _anzahl(radius: int) -> int:
    # Mit dem Radius mehr Teilchen, aber langsamer als die Flaeche: eine
    # wachsende Wolke wird dabei lockerer, wie Teilchen, die auseinanderfliegen.
    return min(TEILCHEN_HOECHSTENS, int(6 + 1.7 * radius ** 1.5))


def ballen(radius: int, palette: str, variante: int) -> pygame.Surface:
    """Eine Rauchwolke aus Pixel-Teilchen, oben links heller (das Licht des
    Spiels), unten rechts dunkler; ohne Rand."""
    radius = max(2, int(radius))
    schluessel = (radius, palette, variante)
    s = _BALLEN.get(schluessel)
    if s is not None:
        return s
    toene = PALETTEN[palette]
    n = radius * 2 + 4
    s = pygame.Surface((n, n), pygame.SRCALPHA)
    m = n / 2.0
    for d, w, g, rausch in _teilchen(variante, False)[:_anzahl(radius)]:
        dx, dy = math.cos(w) * d, math.sin(w) * d
        hell = -(dx * 0.62 + dy * 0.78) + rausch
        ton = 0 if hell > 0.5 else 1 if hell > 0.05 else 2 if hell > -0.45 else 3
        g = min(g, max(1, radius // 3))
        s.fill(toene[ton] + (255,), (int(m + dx * radius - g / 2.0), int(m + dy * radius - g / 2.0), g, g))
    _BALLEN[schluessel] = s
    return s


def flamme(radius: int, variante: int) -> pygame.Surface:
    """Feuer aus Pixel-Teilchen: weiss und gelb in der Mitte, nach aussen
    orange und rot."""
    radius = max(2, int(radius))
    schluessel = (radius, variante)
    s = _FLAMMEN.get(schluessel)
    if s is not None:
        return s
    n = radius * 2 + 4
    s = pygame.Surface((n, n), pygame.SRCALPHA)
    m = n / 2.0
    for d, w, g, rausch in _teilchen(variante, True)[:_anzahl(radius) + 8]:
        q = d + rausch * 0.3
        ton = 0 if q < 0.25 else 1 if q < 0.5 else 2 if q < 0.75 else 3 if q < 0.92 else 4
        g = min(g, max(1, radius // 3))
        s.fill(FEUER[ton] + (255,), (int(m + math.cos(w) * d * radius - g / 2.0),
                                     int(m + math.sin(w) * d * radius - g / 2.0), g, g))
    _FLAMMEN[schluessel] = s
    return s


_SCHATTEN: dict = {}


def _schatten(groesse: int) -> pygame.Surface:
    s = _SCHATTEN.get(groesse)
    if s is None:
        s = pygame.Surface((groesse * 2, max(2, groesse)), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (16, 12, 9, 70), s.get_rect())
        _SCHATTEN[groesse] = s
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
        if groesse <= 1:
            # So klein wird ein Vieleck mit Rand nur ein schwarzes Quadrat:
            # zwei mal zwei Pixel in der Farbe, eines hell.
            flach.fill(farben[1], pygame.Rect(n // 2 - 1, n // 2 - 1, 2, 2))
            flach.set_at((n // 2 - 1, n // 2 - 1), farben[0])
            _BROCKEN[(groesse, art, variante, None)] = flach
            s = pygame.transform.rotate(flach, winkel) if winkel else flach
            _BROCKEN[schluessel] = s
            return s
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


class Teilchen(Fx):
    """Ein einzelnes Pixel-Teilchen Rauch oder Feuer (seit 0.34.126) - wie
    die alten `entities.Partikel`: fliegt los, bremst ab, wird kleiner und
    duennt aus. Eine Wolke sind viele davon (`rauch`, `feuer`).

    Bewegt wird es nicht Schritt fuer Schritt: wo es ist, folgt geschlossen
    aus seinem Alter (Reibung `zaeh`, Auftrieb/Schwere `g`). So kosten
    hunderte davon fast nichts - `schritt` zaehlt nur die Zeit."""

    __slots__ = ("x0", "y0", "z0", "toene")

    def schritt(self, dt: float) -> bool:
        if self.verzoegert > 0.0:
            self.verzoegert -= dt
            return True
        self.alter += dt
        return self.alter < self.dauer

    def ort(self) -> tuple:
        t = self.alter
        k = self.zaeh
        d = (1.0 - math.exp(-k * t)) / k if k > 0.0 else t
        z = self.z0 + self.vz * d - 0.5 * self.g * t * t
        return self.x0 + self.vx * d, self.y0 + self.vy * d, max(0.0, z)


# ══════════════════════════════════════════════════════════════════
# Zeichnen
# ══════════════════════════════════════════════════════════════════

def _zeichne(ziel, f: Fx, ex: float, ey: float) -> None:
    if f.verzoegert > 0.0:
        return
    a = f.anteil
    if isinstance(f, Teilchen):
        # Gegen Ende duennt die Wolke aus: jedes Teilchen verschwindet zu
        # seiner Zeit (variante), statt dass alle zugleich blasser werden.
        if a > 0.5 and f.variante < (a - 0.5) * 200.0:
            return
        px, py, pz = f.ort()
        g = max(1, int(f.r0 * (0.45 + 0.55 * (1.0 - a)) + 0.5))
        if f.art == "feuer":
            farbe = FEUER[min(4, int(a * 4.2 + f.r1))]
        else:
            farbe = f.farbe
        ziel.fill(farbe, (int(px - ex - g / 2.0), int(py - ey - pz - g / 2.0), g, g))
        return
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
        if f.z > 1.0 and f.r0 >= 3:
            # Ein weicher, halb durchsichtiger Schatten - die harten schwarzen
            # Striche darunter sahen aus wie Fremdkoerper (0.34.126); kleine
            # Splitter werfen keinen.
            sch = _schatten(int(f.r0))
            ziel.blit(sch, (int(x - sch.get_width() / 2), int(f.y - ey - sch.get_height() / 2)))
        s = brocken(int(f.r0), f.palette, f.variante % 5, int(f.winkel / 30.0) * 30 % 360)
        if a > 0.8:
            # Auf einer Kopie ausblenden: das Bild ist im Zwischenspeicher, und
            # set_alpha(None) danach schaltete bei ihm die Durchsichtigkeit ganz
            # ab - dann war jeder Brocken (und jedes fx_teil) ein schwarzes Quadrat.
            s = s.copy()
            s.set_alpha(int(255 * (1.0 - a) / 0.2))
        ziel.blit(s, (int(x - s.get_width() / 2), int(y - s.get_height() / 2)))
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
    elif f.art == "leuchtspur":
        # Die Flakgranate (seit 0.34.123): ein greller Kopf, dahinter ein
        # roter Schweif - von schraeg oben gesehen steigt sie im Bild zu
        # ihrem Ziel hoch (z waechst). Am Boden ein schwacher Schatten.
        lang = 0.03
        x2, y2 = x - f.vx * lang, y - (f.vy - f.vz) * lang
        x3, y3 = x - f.vx * lang * 2.2, y - (f.vy - f.vz) * lang * 2.2
        if f.z > 4.0:
            pygame.draw.line(ziel, (22, 17, 12), (x, f.y - ey), (x2, f.y - ey - f.vy * lang), 1)
        pygame.draw.line(ziel, (120, 30, 18), (x3, y3), (x2, y2), 1)
        pygame.draw.line(ziel, (236, 84, 40), (x2, y2), (x, y), 3)
        pygame.draw.line(ziel, (255, 214, 140), (x2 * 0.4 + x * 0.6, y2 * 0.4 + y * 0.6), (x, y), 1)
        pygame.draw.circle(ziel, (255, 250, 228), (int(x), int(y)), 2)
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


def _teilchen_wolke(welt, r, art, x, y, z, ebene, r0, r1, dauer, vx, vy, vz, zaeh, g, verzoegert,
                    boden, anzahl, groesse, farbe_von, palette="grau") -> None:
    """Viele Teilchen, die aus einer Kugel vom Radius `r0` auseinanderfliegen,
    bis die Wolke etwa `r1` gross ist; dazu treibt sie mit (vx, vy, vz)."""
    k = max(0.4, zaeh)
    weite = (1.0 - math.exp(-k * dauer)) / k        # so weit traegt 1 px/s in der Zeit
    for _ in range(anzahl):
        # Richtung in der Kugel; im Bild etwas flacher (wie alles am Boden).
        w = r.uniform(0.0, 2.0 * math.pi)
        h = r.uniform(-0.8, 1.0)
        q = math.sqrt(max(0.0, 1.0 - h * h))
        ux, uy, uz = math.cos(w) * q, math.sin(w) * q * 0.8, h * 0.7
        start = r.uniform(0.0, r0)
        ziel = r.uniform(0.25, 1.0) ** 0.6 * r1
        v = max(0.0, ziel - start) / max(0.05, weite)
        f = Teilchen(art, x, y, z, ebene, dauer * r.uniform(0.55, 1.1))
        f.x0, f.y0, f.z0 = x + ux * start, y + uy * start, max(0.0, z + uz * start)
        f.vx, f.vy, f.vz = vx + ux * v, vy + uy * v, vz + uz * v
        f.zaeh, f.g = k, g
        f.verzoegert = verzoegert + r.uniform(0.0, 0.04)
        f.boden = boden
        f.variante = r.randrange(100)
        f.r0 = r.choice(groesse)
        f.farbe, f.r1 = farbe_von(ux, uy, uz)
        f.palette = palette                  # woraus sie ist (Staub, Rauch ...), fuer Abfragen
        _neu(welt, f)


def rauch(welt, r, x, y, z, ebene, palette, r0, r1, dauer, vx=0.0, vy=0.0, vz=0.0,
          zaeh=1.6, g=0.0, verzoegert=0.0, boden=False, deckung=1.0) -> None:
    """Eine Rauch- oder Staubwolke aus Pixel-Teilchen (seit 0.34.126, vorher
    ein gemalter Ballen): oben links heller, unten rechts dunkler. Wie viele
    Teilchen, folgt aus der Groesse; `deckung` macht sie lockerer."""
    toene = PALETTEN[palette]
    n = max(3, min(20, int(r1 * 1.1 * deckung)))
    groesse = (1, 2, 2) if r1 < 8 else (2, 2, 3) if r1 < 18 else (2, 3, 3, 4)

    def farbe(ux, uy, uz):
        hell = -(ux * 0.6 + uy * 0.7) + uz * 0.5 + r.uniform(-0.45, 0.45)
        return toene[0 if hell > 0.55 else 1 if hell > 0.0 else 2 if hell > -0.5 else 3], 0
    _teilchen_wolke(welt, r, "rauch", x, y, z, ebene, r0, r1, dauer * r.uniform(0.85, 1.15), vx, vy, vz,
                    zaeh, g, verzoegert, boden, n, groesse, farbe, palette)


def feuer(welt, r, x, y, z, ebene, r0, r1, dauer, vx=0.0, vy=0.0, vz=0.0, verzoegert=0.0) -> None:
    """Feuer aus Pixel-Teilchen (seit 0.34.126): weiss und gelb, im Fliegen
    orange, rot und dunkel - die aeusseren kuehlen schneller ab. Dazu ein
    weiches Gluehen, wie beim Feuerball der Panzerkanone."""
    n = max(4, min(22, int(r1 * 1.3)))
    groesse = (1, 2, 2) if r1 < 8 else (2, 2, 3)

    def farbe(ux, uy, uz):
        return FEUER[0], r.uniform(0.0, 1.2)       # r1: wie viel heisser/kuehler es beginnt
    _teilchen_wolke(welt, r, "feuer", x, y, z, ebene, r0, r1, dauer * r.uniform(0.85, 1.15), vx, vy, vz,
                    3.0, -20.0, verzoegert, False, n, groesse, farbe)
    b = blitz(welt, x, y, z, ebene, max(8, int(r1 * 1.6)), dauer * 0.7)
    b.verzoegert = verzoegert


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
              palette, groesse[0], groesse[1] * r.uniform(1.4, 2.2), dauer,
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


def flak_schuss(welt, pos, ebene: int, code: float) -> None:
    """Ein Rohr des Flak-Vierlings feuert (seit 0.34.123). `code` traegt
    Richtung, Strecke und Zielhoehe: Richtung + 360 * (Strecke + 2048 * Hoehe).
    Vorn ein kurzer, flacher Feuerstern, ein Woelkchen Pulverrauch, das
    stehen bleibt, und die Leuchtspur: sie steigt geradewegs zur Hoehe des
    Ziels und verlischt dort, wo die Granate platzt."""
    code = int(code)
    winkel = float(code % 360)
    rest = code // 360
    strecke, hoehe = float(rest % 2048), float(rest // 2048)
    r = _rnd(pos, 11 + int(winkel))
    x, y, z0 = pos[0], pos[1], 7.0
    c, s_ = math.cos(math.radians(winkel)), math.sin(math.radians(winkel))
    blitz(welt, x + c * 4, y + s_ * 4, z0, ebene, 22, 0.05)
    for i in range(3):
        feuer(welt, r, x + c * 3, y + s_ * 3, z0, ebene, 2, r.uniform(4, 6), 0.07,
              vx=c * r.uniform(60, 140) + r.uniform(-30, 30), vy=s_ * r.uniform(60, 140) + r.uniform(-30, 30))
    rauch(welt, r, x + c * 6, y + s_ * 6, z0, ebene, "grau", 2, r.uniform(6, 9), r.uniform(1.0, 1.5),
          vx=c * 40, vy=s_ * 40, vz=8.0, zaeh=3.0, deckung=0.8)
    tempo = float(K.FAHRZEUG_WAFFEN["flak_kanone"]["tempo"])
    dauer = max(0.05, strecke / tempo)
    f = Fx("leuchtspur", x, y, z0, ebene, dauer)
    f.vx, f.vy = c * tempo, s_ * tempo
    f.vz = (max(z0, hoehe) - z0) / dauer
    _neu(welt, f)


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


def raketenstart(welt, pos, ebene: int, code: float) -> None:
    """Eine Rakete verlaesst das Rohr. Vorn ein kurzer Feuerstoss; hinten der
    Rueckstrahl - wie bei einer Panzerfaust, nur viel mehr: ein Kegel aus
    weissem Druckrauch schiesst nach hinten, quillt auf und bleibt lange
    stehen, am Boden reisst er eine breite Staubwand hoch, ein flacher
    Druckring laeuft ueber den Boden. `code` = Steilheit * 1000 + Richtung
    (seit 0.34.123): das hintere Ende des Rohrs liegt tiefer und naeher,
    je steiler es steht."""
    code = int(code)
    winkel, steil = float(code % 1000), math.radians(min(85, code // 1000))
    r = _rnd(pos, 6 + int(winkel))
    x, y = pos[0], pos[1]
    vor = (math.cos(math.radians(winkel)), math.sin(math.radians(winkel)))
    hinten = winkel + 180.0
    zurueck = 36.0 * math.cos(steil)
    hx, hy = x - vor[0] * zurueck, y - vor[1] * zurueck
    zm = 8.0 + 20.0 * math.sin(steil)               # Muendung und hinteres Ende, hoch
    zh = max(2.0, 8.0 - 15.0 * math.sin(steil))
    blitz(welt, x, y, zm, ebene, 40, 0.08)
    feuer(welt, r, x, y, zm, ebene, 3, 8, 0.12, vx=vor[0] * 120 * math.cos(steil),
          vy=vor[1] * 120 * math.cos(steil), vz=120 * math.sin(steil))
    blitz(welt, hx, hy, zh, ebene, 60, 0.12)
    for i in range(5):
        feuer(welt, r, hx, hy, zh, ebene, 4, 10, 0.22,
              vx=math.cos(math.radians(hinten + r.uniform(-12, 12))) * r.uniform(200, 380),
              vy=math.sin(math.radians(hinten + r.uniform(-12, 12))) * r.uniform(200, 380), vz=0.0)
    for i in range(16):
        w = math.radians(hinten + r.uniform(-22, 22))
        v = r.uniform(250, 620)
        rauch(welt, r, hx, hy, zh, ebene, "weiss", 4, r.uniform(11, 20), r.uniform(2.6, 3.8),
              vx=math.cos(w) * v, vy=math.sin(w) * v, vz=r.uniform(4, 22), zaeh=3.2)
    for i in range(22):
        w = math.radians(hinten + r.uniform(-55, 55))
        v = r.uniform(180, 420)
        rauch(welt, r, hx + math.cos(w) * 20, hy + math.sin(w) * 20, 1, ebene, "staub", 5,
              r.uniform(10, 18), r.uniform(1.8, 2.8), vx=math.cos(w) * v, vy=math.sin(w) * v,
              vz=r.uniform(2, 12), zaeh=2.8)
    ring(welt, hx - vor[0] * 20, hy - vor[1] * 20, ebene, 6, 70, 0.45, (236, 222, 188))
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
    """Der Fahrer zuendet die Schrottbombe neben der Kanzel: die Lunte
    flammt auf, ein paar Funken, ein Hauch Rauch, der zurueckbleibt."""
    r = _rnd(pos, 9)
    x, y, z = pos[0], pos[1], max(0.0, hoehe - 4.0)
    rauch(welt, r, x, y, z, ebene, "grau", 1, 5, 0.9, vz=6.0, zaeh=3.0)
    funken(welt, r, x, y, z, ebene, 7, 70.0, 0.3, farbe=(255, 196, 96), hoch=0.3)


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

@platzhalter("flak_leer")
def _flak_leer():
    """Die Flakgranate selbst zeigt nichts - man sieht ihre Leuchtspur."""
    return pygame.Surface((2, 2), pygame.SRCALPHA)


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
    "flak_schuss": lambda w, p, e, r: flak_schuss(w, p, e, r),          # r = Richtung, Strecke, Hoehe
    "werfer_start": lambda w, p, e, r: raketenstart(w, p, e, r),       # r = Steilheit * 1000 + Richtung
    "werfer_gross": lambda w, p, e, r: werfer_explosion(w, p, e, r),   # r = Radius
    "einschlag": lambda w, p, e, r: einschlag(w, p, e, max(0.4, r)),   # r = Groesse
    "bombe": lambda w, p, e, r: bombe(w, p, e),
    "bombe_los": lambda w, p, e, r: bombe_los(w, p, e, r),            # r = Hoehe
}
