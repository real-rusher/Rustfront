"""
DUSTFRONT - Das Raketengestell des Werfers und seine Raketen (seit 0.34.126)
===========================================================================

Gemalt wie die anderen Fahrzeuge (klassisch, von oben, mit dunklem Rand und
wenigen flachen Toenen) - aber fuer jede Richtung und jede Steilheit ein
eigenes Bild, damit man Drehung und Aufrichtung sieht. Bis 0.34.125 war es
ein schattiertes 3D-Modell (drei_d.py); gemeldet: "nicht wirklich 3D, es soll
nach 3D aussehen, aber das ist zu krass, der Artstyle zu unterschiedlich -
klassischer".

Wie es entsteht: die Lage jedes Teils wird raeumlich gerechnet (dieselbe
Rechnung wie fuer Muendung und Rueckstrahl, `muendung3d`, `hinten3d`), die
Bildpunkte sind dann (x, y - Hoehe) wie bei allem, was im Spiel in der Luft
ist. Gemalt wird jedes Teil aber flach im Pixelstil der Fahrzeuge
(art_fahrzeuge._Blatt): Rohre mit dunkler Kante, hellem Kern und einer
Glanzlinie, Bandeisen, Lagerboecke mit hellem Deckel und dunkler Seite. Je
steiler die Rohre, desto hoeher ragen die Muendungen im Bild und desto
kuerzer werden die Rohre, wenn sie zum Betrachter oder von ihm weg zeigen.

Aus Schrott wie alles in RUSTFRONT: sechs alte Rohre verschiedener Herkunft
(verzinkt, rostig, olivgruen), nicht ganz gleich lang, zwei Bandeisen, auf
einer Achse zwischen zwei Lagerboecken auf einer alten Felge; eine Spindel
vorn hebt das Buendel. Geladene Rohre zeigen vorn die rote Spitze und hinten
das Leitwerk, leere Rohre sind dunkle Loecher.

Bilder: `gestell(gieren, erhebung, maske)` (auf 5 und 2 Grad gerundet, jedes
einmal gerechnet und behalten) und `rakete(gieren, kippen)` fuer die Rakete
im Flug.
"""

from __future__ import annotations

import math

import pygame

STUFEN = 8                          # Aufbau in so vielen Stufen (Fahrzeug.stufe)
GROESSE_BILD = 112                  # Bildgroesse des Gestells (Spielpixel)
ACHSE_Z = 8.0                       # so hoch liegt die Achse des Buendels ueber dem Drehteller

# Die sechs Rohre: (quer, hoch, hinten, vorn, Farbe). Unten drei, oben drei.
# Absichtlich ungleich: Schrott aus verschiedenen Quellen.
ROHRE = (
    (-5.2, -1.6, -15.0, 18.0, (150, 144, 128)),   # verzinkt, stumpf
    (0.0, -1.6, -14.0, 19.5, (156, 92, 52)),      # rostig
    (5.2, -1.6, -15.5, 18.5, (116, 124, 86)),      # olivgruen
    (-5.2, 3.0, -14.5, 19.0, (162, 100, 56)),
    (0.0, 3.0, -15.0, 18.0, (110, 118, 84)),
    (5.2, 3.0, -14.0, 19.5, (144, 138, 124)),
)
ROHR_R = 2.3
SPITZE = (176, 62, 40)
SPITZE_DK = (92, 26, 18)
SPITZE_BAND = (204, 176, 86)
BLECH = (150, 146, 134)
DUNKEL = (24, 20, 17)
BAND = (64, 58, 50)
BOCK_L = (112, 74, 46)              # die Lagerboecke: einer rostig ...
BOCK_R = (98, 100, 74)              # ... einer aus olivem Blech
FELGE = (104, 98, 88)
NABE = (128, 122, 110)
RAKETE_RUMPF = (150, 146, 130)


def _mal(farbe, f: float) -> tuple:
    return tuple(max(0, min(255, int(c * f))) for c in farbe)


def _punkt_im_buendel(p, gieren: float, erhebung: float) -> tuple:
    """Ein Punkt im Buendel (zur Achse) in Spielpixeln vom Drehteller."""
    x, y, z = p
    e = math.radians(erhebung)
    x, z = x * math.cos(e) - z * math.sin(e), x * math.sin(e) + z * math.cos(e)
    z += ACHSE_Z
    g = math.radians(gieren)
    return (x * math.cos(g) - y * math.sin(g), x * math.sin(g) + y * math.cos(g), z)


def _punkt_am_teller(p, gieren: float) -> tuple:
    """Ein Punkt am Drehteller (dreht nur mit, hebt sich nicht)."""
    x, y, z = p
    g = math.radians(gieren)
    return (x * math.cos(g) - y * math.sin(g), x * math.sin(g) + y * math.cos(g), z)


def muendung3d(index: int, gieren: float, erhebung: float) -> tuple:
    """Die Muendung von Rohr `index`: (x, y, hoch) vom Drehteller aus."""
    q, h, _x0, x1, _f = ROHRE[index]
    return _punkt_im_buendel((x1 + 1.0, q, h), gieren, erhebung)


def hinten3d(index: int, gieren: float, erhebung: float) -> tuple:
    """Das hintere offene Ende von Rohr `index` - dort tritt der Rueckstrahl aus."""
    q, h, x0, _x1, _f = ROHRE[index]
    return _punkt_im_buendel((x0 - 1.0, q, h), gieren, erhebung)


# ══════════════════════════════════════════════════════════════════
# Malen
# ══════════════════════════════════════════════════════════════════

def _bild(p) -> tuple:
    """Raumpunkt -> Bildpunkt (wie alles in der Luft: um die Hoehe nach oben)."""
    return (p[0], p[1] - p[2])


def _tiefe(*punkte) -> float:
    """Was naeher am Betrachter ist (groesseres y + Hoehe), kommt spaeter."""
    return sum(p[1] + p[2] for p in punkte) / len(punkte)


def _rohr_malen(b, a, e, dicke: float, farbe) -> None:
    """Ein Rohr im Stil der Fahrzeuge: dunkle Kante, Kern, Glanzlinie oben
    links (das Licht des Spiels)."""
    pa, pe = _bild(a), _bild(e)
    b.rohr(pa, pe, dicke, farbe, _mal(farbe, 0.42))
    dx, dy = pe[0] - pa[0], pe[1] - pa[1]
    lang = math.hypot(dx, dy)
    if lang < 1.5:
        return
    nx, ny = -dy / lang, dx / lang
    if nx + ny > 0.0:                       # zur Lichtseite (oben links)
        nx, ny = -nx, -ny
    v = dicke * 0.22
    k = 0.18 * lang
    hell = _mal(farbe, 1.32)
    b.linie(hell, (pa[0] + nx * v + dx / lang * k * 0.3, pa[1] + ny * v + dy / lang * k * 0.3),
            (pe[0] + nx * v - dx / lang * k * 0.3, pe[1] + ny * v - dy / lang * k * 0.3),
            max(0.5, dicke * 0.18))


def _ring_malen(b, a, e, breite: float, farbe, achse_a, achse_e) -> None:
    """Ein Band um ein Rohr (Bandeisen, Muffe) als flacher Streifen quer
    ueber das Rohr - mit runden Enden wuerde aus so einem kurzen Stueck eine
    dunkle Scheibe. `achse_a`/`achse_e`: die Enden des Rohrs, fuer die
    Richtung (auch wenn das Band selbst im Bild fast keine Laenge hat)."""
    pa, pe = _bild(achse_a), _bild(achse_e)
    dx, dy = pe[0] - pa[0], pe[1] - pa[1]
    lang = math.hypot(dx, dy)
    if lang < 0.5:
        b.kreis(farbe, _bild(a), breite / 2.0)
        return
    nx, ny = -dy / lang * breite / 2.0, dx / lang * breite / 2.0
    qa, qe = _bild(a), _bild(e)
    if math.hypot(qe[0] - qa[0], qe[1] - qa[1]) < 0.6:          # mindestens ein Streifen
        ux, uy = dx / lang * 0.3, dy / lang * 0.3
        qa, qe = (qa[0] - ux, qa[1] - uy), (qe[0] + ux, qe[1] + uy)
    b.poly(_mal(farbe, 0.55), [(qa[0] + nx * 1.12, qa[1] + ny * 1.12), (qe[0] + nx * 1.12, qe[1] + ny * 1.12),
                               (qe[0] - nx * 1.12, qe[1] - ny * 1.12), (qa[0] - nx * 1.12, qa[1] - ny * 1.12)])
    b.poly(farbe, [(qa[0] + nx, qa[1] + ny), (qe[0] + nx, qe[1] + ny),
                   (qe[0] - nx, qe[1] - ny), (qa[0] - nx, qa[1] - ny)])


def _quader_malen(b, ecken_von, x0, x1, y0, y1, z0, z1, farbe) -> None:
    """Ein Block (Lagerbock): sichtbare Seiten dunkel, Deckel hell - drei
    flache Toene, wie die Kaesten auf den Fahrzeugen."""
    p = {(i, j, k): ecken_von((x, y, z)) for i, x in enumerate((x0, x1))
         for j, y in enumerate((y0, y1)) for k, z in enumerate((z0, z1))}
    seiten = []
    for achse, wert in ((0, 0), (0, 1), (1, 0), (1, 1)):
        ecken = [(i, j) for i in (0, 1) for j in (0, 1) if (i, j)[achse] == wert]
        ecken = sorted(ecken, key=lambda q: q[1 - achse])
        vier = [p[ecken[0] + (0,)], p[ecken[1] + (0,)], p[ecken[1] + (1,)], p[ecken[0] + (1,)]]
        mitte = (sum(q[0] for q in vier) / 4, sum(q[1] for q in vier) / 4)
        innen = (sum(q[0] for q in p.values()) / 8, sum(q[1] for q in p.values()) / 8)
        if mitte[1] - innen[1] > 0.05:          # zeigt zum Betrachter
            licht = (mitte[0] - innen[0]) < 0.0
            seiten.append((mitte[1], vier, _mal(farbe, 0.78 if licht else 0.6)))
    for _t, vier, f in sorted(seiten, key=lambda s: s[0]):
        b.poly(f, [_bild(q) for q in vier])
    deckel = [p[(0, 0, 1)], p[(1, 0, 1)], p[(1, 1, 1)], p[(0, 1, 1)]]
    b.poly(_mal(farbe, 1.12), [_bild(q) for q in deckel])


def _teile(gieren: float, erhebung: float, maske: int) -> list:
    """Was zu malen ist, je (Tiefe, Zeichner(b))."""
    teile = []
    im = lambda p: _punkt_im_buendel(p, gieren, erhebung)      # noqa: E731
    am = lambda p: _punkt_am_teller(p, gieren)                  # noqa: E731
    # Die Lagerboecke links und rechts, dazwischen die Achse.
    for y0, y1, farbe in ((9.4, 11.4, BOCK_L), (-11.4, -9.4, BOCK_R)):
        m = am((0.0, (y0 + y1) / 2, 4.0))
        teile.append((_tiefe(m), lambda b, y0=y0, y1=y1, farbe=farbe:
                      _quader_malen(b, am, -3.2, 3.2, y0, y1, 1.6, ACHSE_Z + 1.4, farbe)))
    a, e = am((0.0, -12.0, ACHSE_Z)), am((0.0, 12.0, ACHSE_Z))
    teile.append((_tiefe(a, e) - 0.5, lambda b, a=a, e=e: _rohr_malen(b, a, e, 2.0, NABE)))
    # Die Hubspindel vorn, vom Teller schraeg unter das Buendel.
    unten = am((8.0, 0.0, 2.0))
    oben = im((9.0, 0.0, -4.6))
    mitte = tuple(unten[k] + (oben[k] - unten[k]) * 0.45 for k in range(3))
    teile.append((_tiefe(unten, oben) - 1.0, lambda b: (_rohr_malen(b, unten, mitte, 2.8, (78, 74, 64)),
                                                        _rohr_malen(b, mitte, oben, 1.8, (176, 170, 156)))))
    # Die sechs Rohre, jedes mit Bandeisen, Muffe, Spitze oder Loch.
    for i, (q, h, x0, x1, farbe) in enumerate(ROHRE):
        hinten, vorn = im((x0, q, h)), im((x1, q, h))
        geladen = bool(maske & (1 << i))

        def rohr(b, i=i, q=q, h=h, x0=x0, x1=x1, farbe=farbe, hinten=hinten, vorn=vorn, geladen=geladen):
            if geladen:                                           # Leitwerk aus Blech
                for dq in (-1.0, 1.0):
                    b.linie(_mal(BLECH, 0.8), _bild(im((x0 - 0.4, q + dq * 1.2, h))),
                            _bild(im((x0 - 2.8, q + dq * 3.4, h))), 0.9)
            _rohr_malen(b, hinten, vorn, ROHR_R * 2.0, farbe)
            for x in (-8.0, 9.0):                                 # zwei Bandeisen
                _ring_malen(b, im((x - 0.6, q, h)), im((x + 0.6, q, h)), ROHR_R * 2.0 + 0.6, BAND,
                            hinten, vorn)
            _ring_malen(b, im((x1 - 1.2, q, h)), vorn, ROHR_R * 2.0 + 0.6, _mal(farbe, 0.82),
                        hinten, vorn)                             # Muffe vorn
            b.kreis(DUNKEL, _bild(hinten), ROHR_R * 0.8)
            if geladen:
                band = im((x1 + 1.0, q, h))
                nase = im((x1 + 4.4, q, h))
                b.rohr(_bild(vorn), _bild(band), ROHR_R * 1.6, SPITZE_BAND, _mal(SPITZE_BAND, 0.45))
                b.rohr(_bild(band), _bild(nase), ROHR_R * 1.3, SPITZE, SPITZE_DK)
                b.kreis(_mal(SPITZE, 1.3), _bild(im((x1 + 2.6, q - 0.4, h + 0.5))), 0.5)
            else:
                b.kreis(DUNKEL, _bild(vorn), ROHR_R * 0.85)
        teile.append((_tiefe(hinten, vorn) + 2.0, rohr))
    # Ein Haltegriff aus Rundeisen hinten links, zum Nachrichten von Hand.
    g0, g1 = im((-12.0, -8.4, 1.0)), im((-16.0, -10.8, 1.6))
    teile.append((_tiefe(g0, g1), lambda b: _rohr_malen(b, g0, g1, 1.2, NABE)))
    return sorted(teile, key=lambda t: t[0])


def _felge_malen(b) -> None:
    """Der Drehteller: eine alte Radfelge, rund - sie sieht in jeder
    Richtung gleich aus."""
    b.kreis(_mal(FELGE, 0.4), (0, -1.0), 10.6)
    b.kreis(FELGE, (0, -1.0), 9.8)
    b.kreis(_mal(FELGE, 0.7), (0, -1.0), 7.4)
    b.kreis(_mal(NABE, 0.5), (0, -1.6), 4.2)
    b.kreis(NABE, (0, -1.6), 3.5)
    b.linie(_mal(FELGE, 1.3), (-7.4, -4.6), (-2.8, -8.6), 0.8)


_GESTELL: dict = {}
GESTELL_HOECHSTENS = 600              # so viele Bilder bleiben gemerkt (je ~12 KB zugeschnitten)


def zuschneiden(s: pygame.Surface) -> tuple:
    """Nur der belegte Teil eines Bildes und wo er liegt, von der Bildmitte
    aus (seit 0.34.127): die gemerkten Bilder sind meist zu drei Vierteln
    leer, zugeschnitten brauchen sie einen Bruchteil des Speichers."""
    r = s.get_bounding_rect(1)
    if r.width == 0 or r.height == 0:
        r = pygame.Rect(0, 0, 1, 1)
    return s.subsurface(r).copy(), (r.x - s.get_width() / 2.0, r.y - s.get_height() / 2.0)


def gestell_zugeschnitten(gieren: float, erhebung: float, maske: int) -> tuple:
    """(Bild, Versatz, Schatten, Versatz) - so zeichnet es das Spiel: den
    Versatz zur Mitte des Drehtellers addieren. Gerundet auf 5 Grad (gieren)
    und 2 Grad (erhebung), jedes Bild wird einmal gerechnet und behalten."""
    g = int(round(gieren / 5.0)) * 5 % 360
    e = max(0, min(80, int(round(erhebung / 2.0)) * 2))
    m = int(maske) & 63
    s = _GESTELL.get((g, e, m))
    if s is not None:
        return s
    if len(_GESTELL) > GESTELL_HOECHSTENS:
        _GESTELL.clear()
    bild, schatten = _gestell_malen(g, e, m)
    s = _GESTELL[(g, e, m)] = zuschneiden(bild) + zuschneiden(schatten)
    return s


def gestell(gieren: float, erhebung: float, maske: int) -> tuple:
    """(Bild, Schatten) des Gestells in voller Groesse (GROESSE_BILD), Mitte
    = Drehteller - fuer Werkzeuge und Pruefungen; das Spiel nimmt die
    zugeschnittenen (gestell_zugeschnitten)."""
    b, bv, s, sv = gestell_zugeschnitten(gieren, erhebung, maske)
    halb = GROESSE_BILD / 2.0
    raus = []
    for teil, (vx, vy) in ((b, bv), (s, sv)):
        voll = pygame.Surface((GROESSE_BILD, GROESSE_BILD), pygame.SRCALPHA)
        voll.blit(teil, (int(round(halb + vx)), int(round(halb + vy))))
        raus.append(voll)
    return tuple(raus)


def _gestell_malen(g: int, e: int, m: int) -> tuple:
    from .art_fahrzeuge import _Blatt
    teile = _teile(float(g), float(e), m)
    b = _Blatt(GROESSE_BILD, 1.0)
    _felge_malen(b)
    for _t, malen in teile:
        malen(b)
    bild = b.fertig()
    # Der Schatten: dasselbe in Schwarz, auf den Boden gedrueckt und schraeg
    # nach rechts unten verschoben (je hoeher, desto weiter).
    sb = _Blatt(GROESSE_BILD, 1.0)
    for i, (q, h, x0, x1, _f) in enumerate(ROHRE):
        a = _punkt_im_buendel((x0, q, h), float(g), float(e))
        z = _punkt_im_buendel((x1 + (4.4 if m & (1 << i) else 0.0), q, h), float(g), float(e))
        sb.rohr((a[0] + a[2] * 0.42, a[1] + a[2] * 0.34), (z[0] + z[2] * 0.42, z[1] + z[2] * 0.34),
                ROHR_R * 2.0, (0, 0, 0), (0, 0, 0))
    sb.kreis((0, 0, 0), (0, 0), 10.0)
    flach = sb.fertig(rand=False)
    schatten = pygame.mask.from_surface(flach, 30).to_surface(setcolor=(0, 0, 0, 86), unsetcolor=(0, 0, 0, 0))
    return bild, schatten


_RAKETE: dict = {}


def _rakete_richtung(gieren: float, kippen: float) -> tuple:
    """Die Flugrichtung im Raum (`kippen` negativ: Nase nach oben)."""
    g, k = math.radians(gieren), math.radians(kippen)
    return (math.cos(k) * math.cos(g), math.cos(k) * math.sin(g), -math.sin(k))


def rakete(gieren: float, kippen: float) -> pygame.Surface:
    """Eine Rakete im Flug, 28 x 28, Nase in Flugrichtung - gemalt wie das
    Gestell: Rumpf aus Rohr, rote Spitze, Leitwerk. Gerundet auf 10 Grad."""
    from .art_fahrzeuge import _Blatt
    g = int(round(gieren / 10.0)) * 10 % 360
    k = max(-90, min(90, int(round(kippen / 10.0)) * 10))
    s = _RAKETE.get((g, k))
    if s is not None:
        return s
    d = _rakete_richtung(g, k)
    an = lambda t: (d[0] * t, d[1] * t, d[2] * t)               # noqa: E731
    b = _Blatt(28, 1.0)
    quer = (-math.sin(math.radians(g)), math.cos(math.radians(g)), 0.0)
    for s_ in (-1.0, 1.0):                                        # Leitwerk
        a0 = an(-4.6)
        a1 = tuple(an(-6.6)[i] + quer[i] * 2.6 * s_ for i in range(3))
        b.linie(_mal(BLECH, 0.75), _bild(a0), _bild(a1), 0.9)
    _rohr_malen(b, an(-6.0), an(2.6), 3.0, RAKETE_RUMPF)
    b.rohr(_bild(an(2.6)), _bild(an(3.6)), 3.0, SPITZE_BAND, _mal(SPITZE_BAND, 0.45))
    b.rohr(_bild(an(3.6)), _bild(an(6.4)), 2.4, SPITZE, SPITZE_DK)
    s = _RAKETE[(g, k)] = b.fertig()
    return s


def rakete_heck(gieren: float, kippen: float) -> tuple:
    """Wo das Heck (die Flamme) liegt, relativ zur Mitte: (x, y - z) im Bild."""
    g, k = math.radians(gieren), math.radians(kippen)
    x, z = -6.4 * math.cos(k), 6.4 * math.sin(k)
    return (x * math.cos(g), x * math.sin(g) - z)
