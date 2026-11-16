"""
DUSTFRONT - Die Zeichen der Fahrzeuge auf den Karten (seit 0.34.147)
====================================================================

Gewuenscht: fuer jedes Fahrzeug ein eigenes Zeichen auf der Karte und der
Minikarte, mit einer klaren Form (ein Symbol oder die Seitenansicht), hoch
aufgeloest, groesser als der Spielermarker. Der erste Entwurf (feine
Seitenansichten) war bei 10 bis 30 Pixeln nicht zu erkennen - gemeldet.

Jetzt wie die Zeichen auf Lagekarten: ein **Abzeichen** in der Farbe der
Seite (Orange oder Blau, K.TEAMS; leer: Sand), darauf ein **kraeftiges helles
Piktogramm** aus wenigen dicken Formen - Raeder, Fenster und Ketten sind
ausgestanzt, nichts ist duenner als ein Zehntel des Zeichens. Woran man es
erkennt:

* BUGGY: zwei grosse Raeder und der Ueberrollbuegel
* KRAD: zwei Raeder, Fahrer, Beiwagen
* PANZER: Kette, Turm, lange Kanone nach vorn
* JAGDPANZER: Kette, flacher Keil, Kanone aus der Front
* PANZERWAGEN: drei Raeder, kantige Wanne, kleiner Ring
* FLAKWAGEN: Laster mit zwei steilen Rohren
* TROSSWAGEN: Laster mit Kasten und Kreuz
* FUNKWAGEN: Kasten mit Mast und Querantenne
* WERFER: Laster mit schraegem Rohrbuendel
* SPULENWAGEN: Laster mit Spule und Blitz
* TRAGSCHRAUBER: Rotor, Rumpf, Leitwerk

Gemalt wird achtfach so gross und weich verkleinert - die Kanten bleiben
glatt. Die Nase zeigt dorthin, wohin der Wagen faehrt (links/rechts).
"""

from __future__ import annotations

import math

import pygame

GROSS = 8                 # so viel groesser wird gemalt
RAND = (16, 12, 10)       # dunkler Rand des Abzeichens
HELL = (250, 240, 220)    # das Piktogramm
LEER = (0, 0, 0, 0)


class _Maler:
    """Malt das Piktogramm in Einheiten 0..100 (x nach vorn = rechts, y nach
    unten). `hell` setzt Form, `loch` stanzt aus (wird zur Abzeichenfarbe)."""

    def __init__(self, n: int) -> None:
        self.n = n
        self.f = n / 100.0
        self.s = pygame.Surface((n, n), pygame.SRCALPHA)

    def _p(self, x, y):
        return (x * self.f, y * self.f)

    def poly(self, punkte, loch=False):
        pygame.draw.polygon(self.s, LEER if loch else HELL, [self._p(x, y) for x, y in punkte])

    def kreis(self, x, y, r, loch=False):
        pygame.draw.circle(self.s, LEER if loch else HELL, self._p(x, y), r * self.f)

    def rect(self, x, y, b, h, rund=0.0, loch=False):
        pygame.draw.rect(self.s, LEER if loch else HELL,
                         pygame.Rect(int(x * self.f), int(y * self.f), int(b * self.f), int(h * self.f)),
                         border_radius=int(rund * self.f))

    def balken(self, a, b, dick, loch=False):
        """Ein dicker Strich mit runden Enden."""
        ax, ay = a
        bx, by = b
        d = math.hypot(bx - ax, by - ay) or 1.0
        nx, ny = -(by - ay) / d * dick / 2, (bx - ax) / d * dick / 2
        self.poly([(ax + nx, ay + ny), (bx + nx, by + ny), (bx - nx, by - ny), (ax - nx, ay - ny)], loch)
        self.kreis(ax, ay, dick / 2, loch)
        self.kreis(bx, by, dick / 2, loch)

    def rad(self, x, y, r):
        """Rad: helle Scheibe mit ausgestanztem Ring - liest sich als Reifen."""
        self.kreis(x, y, r)
        self.kreis(x, y, r * 0.55, loch=True)
        self.kreis(x, y, r * 0.25)


# ---- Die Piktogramme -----------------------------------------------------

def _buggy(m):
    m.poly([(12, 62), (90, 62), (84, 50), (18, 48)])
    m.balken((28, 50), (38, 26), 7)
    m.balken((38, 26), (66, 26), 7)
    m.balken((66, 26), (76, 50), 7)
    m.rad(26, 70, 16)
    m.rad(78, 72, 13)


def _krad(m):
    m.rect(52, 50, 42, 16, rund=7)                    # Beiwagen
    m.rad(22, 72, 14)
    m.rad(66, 72, 14)
    m.poly([(20, 66), (36, 46), (60, 46), (68, 66)])
    m.kreis(40, 26, 9)                                # Fahrer
    m.poly([(32, 34), (48, 34), (50, 52), (30, 52)])
    m.balken((48, 38), (66, 42), 6)


def _panzer(m):
    m.rect(6, 60, 84, 22, rund=11)                    # Kette
    for x in (20, 36, 52, 68):
        m.kreis(x + 2, 71, 5, loch=True)
    m.poly([(4, 60), (92, 60), (96, 50), (8, 48)])
    m.rect(24, 30, 36, 20, rund=6)                    # Turm
    m.rect(56, 36, 42, 8, rund=3)                     # Kanone


def _jagdpanzer(m):
    m.rect(4, 60, 86, 22, rund=11)
    for x in (18, 34, 50, 66):
        m.kreis(x + 2, 71, 5, loch=True)
    m.poly([(4, 62), (92, 62), (96, 52), (66, 32), (8, 36)])
    m.rect(70, 42, 28, 8, rund=3)                     # Kanone aus der Front


def _panzerwagen(m):
    m.poly([(4, 66), (96, 66), (96, 50), (84, 34), (16, 34), (4, 48)])
    m.rect(40, 20, 22, 16, rund=4)                    # Ring
    m.rect(58, 24, 30, 6, rund=3)                     # MG
    m.kreis(80, 46, 4, loch=True)                     # Sehschlitz
    for x in (20, 50, 80):
        m.rad(x, 72, 12)


def _laster(m, kasten=True):
    """Fuehrerhaus vorn und Pritsche, drei Raeder."""
    m.poly([(66, 66), (96, 66), (96, 44), (84, 30), (66, 30)])
    m.poly([(74, 36), (84, 36), (90, 44), (74, 44)], loch=True)    # Fenster
    m.rect(4, 54, 64, 12)
    for x in (18, 44, 82):
        m.rad(x, 72, 12)


def _flakwagen(m):
    _laster(m)
    m.rect(14, 44, 32, 12, rund=4)                    # Lafette
    m.balken((24, 46), (52, 10), 8)                   # zwei steile Rohre
    m.balken((36, 48), (64, 14), 8)


def _trosswagen(m):
    _laster(m)
    m.rect(4, 22, 62, 34, rund=4)                     # Kasten
    m.rect(28, 28, 8, 22, loch=True)                  # Kreuz
    m.rect(21, 35, 22, 8, loch=True)


def _funkwagen(m):
    m.poly([(4, 66), (96, 66), (96, 44), (82, 30), (4, 30)])
    m.poly([(74, 36), (82, 36), (90, 44), (74, 44)], loch=True)
    m.balken((36, 30), (36, 10), 7)                   # Mast
    m.balken((18, 10), (54, 10), 7)                   # Querantenne
    m.rad(22, 72, 12)
    m.rad(78, 72, 12)


def _werfer(m):
    _laster(m)
    m.rect(16, 46, 22, 10, rund=3)
    for i in range(3):                                # Rohrbuendel, schraeg
        y = 44 - i * 9
        m.balken((14, y + 6), (60, y - 22), 7)


def _spulenwagen(m):
    _laster(m)
    m.rect(14, 18, 30, 38, rund=6)                    # Spule
    for y in (26, 36, 46):
        m.rect(14, y, 30, 4, loch=True)
    m.poly([(48, 6), (60, 6), (54, 18), (64, 18), (46, 38), (52, 22), (42, 22)])  # Blitz


def _tragschrauber(m):
    m.balken((8, 18), (92, 18), 7)                    # Rotor
    m.balken((54, 18), (54, 38), 7)                   # Mast
    m.poly([(28, 44), (80, 38), (98, 52), (82, 66), (32, 62)])  # Rumpf
    m.poly([(70, 44), (84, 42), (92, 52), (74, 52)], loch=True)  # Kanzel
    m.balken((8, 50), (32, 52), 7)                    # Heck
    m.poly([(2, 34), (14, 34), (16, 58), (4, 58)])    # Leitwerk
    m.rad(44, 74, 7)
    m.rad(74, 74, 7)


ZEICHNER = {"buggy": _buggy, "krad": _krad, "panzer": _panzer, "jagdpanzer": _jagdpanzer,
            "panzerwagen": _panzerwagen, "flakwagen": _flakwagen, "trosswagen": _trosswagen,
            "funkwagen": _funkwagen, "werfer": _werfer, "spulenwagen": _spulenwagen,
            "tragschrauber": _tragschrauber}

_MERK: dict = {}
_PIKTO: dict = {}


def _piktogramm(art: str):
    """Das Piktogramm gross (weiss auf durchsichtig), je Art einmal gemalt."""
    s = _PIKTO.get(art)
    if s is None:
        m = _Maler(100 * GROSS)
        ZEICHNER[art](m)
        s = _PIKTO[art] = m.s
    return s


def symbol(art: str, groesse: int, farbe, nach_links: bool = False):
    """Das Zeichen einer Fahrzeugart: ein Abzeichen `groesse` x `groesse`
    Pixel in `farbe` mit dem hellen Piktogramm. Gemerkt je Art, Groesse,
    Farbe und Richtung. None, wenn es die Art nicht gibt."""
    if art not in ZEICHNER:
        return None
    groesse = max(6, int(groesse))
    farbe = tuple(farbe[:3])
    schluessel = (art, groesse, farbe, bool(nach_links))
    s = _MERK.get(schluessel)
    if s is not None:
        return s
    n = groesse * GROSS
    gross = pygame.Surface((n, n), pygame.SRCALPHA)
    rand = max(GROSS, int(n * 0.07))
    ecke = int(n * 0.24)
    pygame.draw.rect(gross, RAND, gross.get_rect(), border_radius=ecke)
    dunkler = tuple(int(c * 0.72) for c in farbe)
    innen = gross.get_rect().inflate(-2 * rand, -2 * rand)
    pygame.draw.rect(gross, dunkler, innen, border_radius=max(1, ecke - rand))
    pygame.draw.rect(gross, farbe, innen.inflate(-rand, -rand).move(0, -rand // 3),
                     border_radius=max(1, ecke - rand))
    # Das Piktogramm, mit einem schmalen dunklen Schatten, damit es auch auf
    # hellem Orange steht.
    platz = int(innen.width * 0.86)
    pikto = pygame.transform.smoothscale(_piktogramm(art), (platz, platz))
    if nach_links:
        pikto = pygame.transform.flip(pikto, True, False)
    schatten = pygame.mask.from_surface(pikto, 60).to_surface(setcolor=RAND + (150,), unsetcolor=LEER)
    ort = pikto.get_rect(center=innen.center)
    gross.blit(schatten, ort.move(max(1, rand // 2), max(1, rand // 2)))
    gross.blit(pikto, ort)
    s = pygame.transform.smoothscale(gross, (groesse, groesse))
    if len(_MERK) > 800:
        _MERK.clear()
    _MERK[schluessel] = s
    return s


def breite_welt(b) -> float:
    """Wie breit der Wagen in der Welt ist (Innenkreis seiner Huelle, Pixel)."""
    w = getattr(b, "werte", {}) or {}
    if getattr(b, "rechteckig", False) and w.get("halb"):
        return 2.0 * float(w["halb"])
    return 2.0 * float(getattr(b, "radius", 14.0))


def zeichnen(ziel, b, mitte, px_je_welt: float, farbe, mindest: float = 12.0, blass: bool = False) -> None:
    """Das Zeichen von Wagen `b` um `mitte` auf eine Karte mit `px_je_welt`
    Kartenpixeln je Weltpixel: so gross wie der Wagen auf der Karte, aber nie
    kleiner als `mindest` (Kartenpixel) - deutlich groesser als ein Spielermarker."""
    groesse = max(mindest, breite_welt(b) * px_je_welt)
    nach_links = math.cos(math.radians(getattr(b, "winkel", 0.0))) < -0.1
    s = symbol(b.art, int(round(groesse)), farbe, nach_links)
    if s is None:
        return
    if blass:
        s = s.copy()
        s.set_alpha(130)
    ziel.blit(s, s.get_rect(center=(int(mitte[0]), int(mitte[1]))))
