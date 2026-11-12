"""
DUSTFRONT - Das Kartenbild (seit 0.34.100)
=========================================

Gewuenscht: "deutlich hoehere Resolution fuer die Minimap, generell was
schoener und lesbarer machen." Bis 0.34.99 war der Grundriss eine Flaeche
mit einem Pixel je Kachel, die dann ohne Glaettung verkleinert wurde - auf
STAUBTAL (300 Kacheln breit) fiel dabei jede zweite Kachel heraus, und die
Karte flimmerte zu Rauschen.

Hier entsteht der Grundriss einer Ebene einmal **gross** (mehrere Pixel je
Kachel, K.KARTENBILD), mit

* Boden je nach Art (Sand, Piste, Kies, Gestruepp, Pflaster, Dielen) und
  einem leisen Rauschen je Kachel, damit Flaechen nicht tot wirken,
* hohen Mauern und Fels hell, mit Lichtkante oben links und Schatten unten
  rechts auf dem Boden - so liest man sofort, wo es nicht weitergeht,
* niedriger Deckung (Sandsack, Kiste, Brocken ...) als kleineres Quadrat,
* Treppen, Luken und Aufzuegen tuerkis.

Wer es kleiner braucht (runde Karte, Nachschubkarte), holt es mit
`in_groesse` - weich verkleinert und je Groesse gemerkt.
"""

from __future__ import annotations

import pygame

from . import config as K

B = K.KARTENBILD

_TREPPEN = (K.TREPPE_HOCH, K.TREPPE_RUNTER, K.LUKE, K.AUFZUG_HOCH, K.AUFZUG_RUNTER)

# Je Kachelart, welche Farbe aus K.KARTENBILD der Boden hat.
_BODEN_SCHLUESSEL = {
    K.BODEN: "sand",
    K.PISTE: "piste",
    K.KIES: "kies",
    K.GESTRUEPP: "gestruepp",
    K.PFLASTER: "pflaster",
    K.DIELEN: "dielen",
    K.GITTER: "gitter",
    K.WASSER_SEICHT: "seicht",
    K.WASSER_TIEF: "wasser",
    K.BRUECKE: "dielen",
}


def _farben(ebene) -> dict:
    """Die Farben fuer den Kachelsatz der Ebene (seit 0.34.131): eine Wiese
    ist gruen, Asphalt grau - nicht alles sandbraun wie in der Wueste."""
    f = dict(B)
    f.update(B["saetze"].get(getattr(ebene, "satz", ""), {}))
    return f

# Gemerkt: je Ebene (Objekt) das grosse Bild, je (Ebene, Groesse) das kleine.
_gross: dict = {}
_klein: dict = {}


def _rauschen(tx: int, ty: int) -> int:
    """Ein fester Wert -1..1 je Kachel (immer derselbe, kein Zufall)."""
    h = (tx * 73856093) ^ (ty * 19349663)
    return (h >> 5) % 3 - 1


def _hell(farbe, um: int) -> tuple:
    return tuple(max(0, min(255, c + um)) for c in farbe)


def pixel_je_kachel(ebene) -> int:
    """So viele Pixel bekommt eine Kachel: grosse Karten weniger."""
    laengste = max(1, max(ebene.breite, ebene.hoehe))
    return max(B["mindest"], min(B["hoechstens"], int(B["ziel_pixel"] // laengste)))


def bild(ebene) -> pygame.Surface:
    """Der grosse Grundriss dieser Ebene (einmal gemalt, dann gemerkt)."""
    fertig = _gross.get(id(ebene))
    if fertig is not None and fertig[0] is ebene:
        return fertig[1]
    p = pixel_je_kachel(ebene)
    br, ho = ebene.breite, ebene.hoehe
    s = pygame.Surface((br * p, ho * p), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    kachel = ebene.kachel
    daten = K.KACHELN
    F = _farben(ebene)
    boden_farbe = {k: F[n] for k, n in _BODEN_SCHLUESSEL.items()}
    leer = K.LEER

    def art(tx, ty):
        return kachel(tx, ty)

    def hoch(tx, ty):
        a = art(tx, ty)
        return daten[a]["fest"] and daten[a]["sicht"]

    # 1. Boden ueberall, wo kein Loch ist.
    for ty in range(ho):
        for tx in range(br):
            a = art(tx, ty)
            if a == leer:
                continue
            grund = boden_farbe.get(a, F["sand"])
            if daten[a]["fest"]:
                grund = F["sand"]
            s.fill(_hell(grund, _rauschen(tx, ty) * B["rauschen"]), (tx * p, ty * p, p, p))
    # 2. Schatten der hohen Waende nach unten rechts auf den Boden.
    schatten = max(1, p // 3)
    for ty in range(ho):
        for tx in range(br):
            if not hoch(tx, ty):
                continue
            if tx + 1 < br and not hoch(tx + 1, ty) and art(tx + 1, ty) != leer:
                s.fill(F["schatten"], ((tx + 1) * p, ty * p + schatten, schatten, p))
            if ty + 1 < ho and not hoch(tx, ty + 1) and art(tx, ty + 1) != leer:
                s.fill(F["schatten"], (tx * p + schatten, (ty + 1) * p, p, schatten))
    # 3. Hohe Waende, niedrige Deckung, Treppen.
    kante = max(1, p // 4)
    for ty in range(ho):
        for tx in range(br):
            a = art(tx, ty)
            x, y = tx * p, ty * p
            if a in _TREPPEN:
                s.fill(B["treppe"], (x, y, p, p))
                continue
            if not daten[a]["fest"]:
                continue
            if daten[a]["sicht"]:
                # Gewachsener Fels etwas dunkler als gebaute Mauern: so liest
                # man auf STAUBTAL Haeuser vor dem Gebirge.
                farbe = F["fels"] if a == K.FELS else F["wand"]
                s.fill(_hell(farbe, _rauschen(ty, tx) * B["rauschen"]), (x, y, p, p))
                # Lichtkante oben und links, wo die Nachbarkachel nicht hoch ist.
                if ty == 0 or not hoch(tx, ty - 1):
                    s.fill(F["wand_licht"], (x, y, p, kante))
                if tx == 0 or not hoch(tx - 1, ty):
                    s.fill(F["wand_licht"], (x, y, kante, p))
                if ty + 1 >= ho or not hoch(tx, ty + 1):
                    s.fill(F["wand_dunkel"], (x, y + p - kante, p, kante))
                if tx + 1 >= br or not hoch(tx + 1, ty):
                    s.fill(F["wand_dunkel"], (x + p - kante, y, kante, p))
            elif a == K.KAKTUS and "baum" in F:
                # Ein Baum: eine runde, dunkelgruene Krone.
                pygame.draw.circle(s, F["baum"], (x + p // 2, y + p // 2), max(1, p // 2))
            else:
                rand = max(1, p // 5) if p >= 4 else 0
                s.fill(F["deckung_rand"], (x + rand, y + rand, p - 2 * rand, p - 2 * rand))
                innen = rand + max(1, p // 6) if p >= 4 else 0
                if p - 2 * innen > 0:
                    s.fill(F["deckung"], (x + innen, y + innen, p - 2 * innen, p - 2 * innen))
    if len(_gross) > 8:
        _gross.clear()
        _klein.clear()
    _gross[id(ebene)] = (ebene, s)
    return s


def in_groesse(ebene, groesse) -> pygame.Surface:
    """Der Grundriss, weich auf `groesse` gebracht (je Groesse gemerkt)."""
    groesse = (max(1, int(groesse[0])), max(1, int(groesse[1])))
    schluessel = (id(ebene), groesse)
    fertig = _klein.get(schluessel)
    if fertig is not None and fertig[0] is ebene:
        return fertig[1]
    gross = bild(ebene)
    klein = gross if gross.get_size() == groesse else pygame.transform.smoothscale(gross, groesse)
    if len(_klein) > 24:
        _klein.clear()
    _klein[schluessel] = (ebene, klein)
    return klein
