"""
DUSTFRONT - Krad und Jagdpanzer, gezeichnet (seit 0.34.107)
===========================================================

Die Bilder der ersten beiden Fahrzeuge aus dem Konzept fuer grosse Karten.
Gezeichnet wie art_fahrzeuge.py: auf derselben Zeichenflaeche (`_Blatt`,
vierfach gross, weich verkleinert, dunkler Rand), Licht von oben links,
Staub und Rost; beide schauen nach +x.

**Krad.** Eine Abwandlung des Buggys, ein Motorrad mit Beiwagen. Es gibt es
leer, mit Fahrer und mit Fahrer und Beifahrer (der Beiwagen sitzt rechts,
+y), je neutral und je Mannschaft.

**Jagdpanzer.** Wanne mit Kasematte und Ketten (`jagdpanzer_wanne`), dazu
der drehende Teil (`jagdpanzer_aufbau`): Blende, langes Rohr mit
Muendungsbremse und die Luke des Kommandanten. Er dreht nur um wenige Grad
um die Mitte der Wanne; die Kanone ist ja fest im Bug.

Keine Insassen im Skin (art_figuren): ein Skin faellt hier auf die Farben
der Mannschaft zurueck.
"""

from __future__ import annotations

import math
import random

import pygame

from . import art
from . import config as K
from .art_fahrzeuge import (GROESSE, LW_DK, _ROST, _SS, _Blatt, _kette, _kombi_fahrer, _reifen,
                            _schatten, _staub, _wrack)
from .core import platzhalter

G = GROESSE
_NEUTRAL = (K.C_HULL, K.C_HULL_SH, K.C_TEAL)

# ──────────────────────────────── kleine Helfer


def _platte(b, umriss, dk, lack, fx=0.94, fy=0.9, dx=0.0):
    """Ein Blech als Vieleck: dunkler Rand, Lack innen."""
    b.poly(dk, umriss)
    cx = sum(p[0] for p in umriss) / len(umriss)
    cy = sum(p[1] for p in umriss) / len(umriss)
    b.poly(lack, [(cx + (x - cx) * fx + dx, cy + (y - cy) * fy) for x, y in umriss])


def _nieten(b, punkte, farbe, r=0.42):
    for p in punkte:
        b.kreis(farbe, p, r)


def _scheinwerfer(b, c, r=1.0):
    b.kreis((40, 34, 28), c, r + 0.5)
    b.kreis((255, 236, 170), (c[0] + 0.2, c[1]), r)
    b.kreis((255, 255, 236), (c[0] - 0.1, c[1] - 0.2), r * 0.4)


def _kanister(b, x, y, w=4.5, h=3.4):
    b.rect((40, 50, 34), x, y, w, h, 0.5)
    b.rect((86, 104, 62), x + 0.4, y + 0.4, w - 0.8, h - 0.8, 0.4)
    b.linie((40, 50, 34), (x + w * 0.5, y + 0.6), (x + w * 0.5, y + h - 0.6), 0.35)


def _rost(b, rnd, n, x0, x1, y0, y1):
    for _ in range(n):
        b.kreis(rnd.choice(_ROST), (rnd.uniform(x0, x1), rnd.uniform(y0, y1)),
                rnd.uniform(0.3, 0.9))


def _insasse(b, fahrer, x, y, arme=8):
    """Die Spielerfigur, Mitte (x, y) in Zeichenmass des Blatts."""
    art._insasse_auf(b.s, _SS, b.n // 2, fahrer, x * b.g, y * b.g, arme=arme)


def _schatten_bild(n: int, lang: int, breit: int, rund: int) -> pygame.Surface:
    s = pygame.Surface((n, n), pygame.SRCALPHA)
    pygame.draw.rect(s, (0, 0, 0, 120), (n // 2 - lang // 2, n // 2 - breit // 2, lang, breit),
                     border_radius=rund)
    for _ in range(2):
        s = pygame.transform.smoothscale(pygame.transform.smoothscale(s, (24, 24)), (n, n))
    return s


# ──────────────────────────────── Krad

KR_LACK = (120, 118, 86)
KR_DK = (58, 56, 40)
KR_HELL = (164, 160, 120)
_STAUB = [(150, 140, 96), (120, 110, 72), (176, 166, 126), (110, 96, 64)]


def krad_zeichnen(fahrer=None, beifahrer=None) -> pygame.Surface:
    """Das Krad von oben, 96 x 96. `fahrer` und `beifahrer` sind (rumpf,
    kante, akzent) ihrer Mannschaft oder None."""
    b = _Blatt(96, 1.3)
    rnd = random.Random(7101)
    my = -6.0                                   # Laengsachse des Motorrads
    by = 8.6                                    # Laengsachse des Beiwagens
    for x in (-8, 5):                           # Streben zum Beiwagen, unter allem
        b.rohr((x, my + 1), (x + 1, by - 5), 1.5, (96, 92, 86))
    b.rohr((-3, by + 5), (-3, by + 8.4), 1.6, (96, 92, 86))
    _reifen(b, 14.5, my, 10, 3.6, 0.0)
    _reifen(b, -13.5, my, 11, 4.2, 0.0)
    _reifen(b, -3, by + 9.0, 10, 3.6, 0.0)
    for sy in (-1, 1):                          # Gabel
        b.rohr((8, my + sy * 1.6), (15, my + sy * 2.3), 1.0, (150, 146, 138))
    b.rect(KR_DK, 11.5, my - 2.0, 6.5, 4.0, 1.8)
    b.rect(KR_LACK, 12, my - 1.5, 5.5, 3.0, 1.4)
    b.rect((30, 28, 26), -4, my - 4.8, 6, 9.6, 0.8)          # Motorblock, Boxer
    b.rect((96, 92, 86), -3.5, my - 4.4, 5, 8.8, 0.6)
    for i in range(4):
        b.linie((52, 50, 46), (-3.2 + i * 1.3, my - 4.4), (-3.2 + i * 1.3, my + 4.4), 0.4)
    b.rohr((-3, my - 4.6), (-18, my - 4.2), 1.5, (170, 164, 152), (52, 48, 44))
    b.kreis((20, 18, 16), (-18.2, my - 4.2), 0.55)
    tank = [(8.6, my - 1.2), (6.4, my - 3.2), (0, my - 3.4), (-2, my - 2.4), (-2, my + 2.4),
            (0, my + 3.4), (6.4, my + 3.2), (8.6, my + 1.2)]
    _platte(b, tank, KR_DK, KR_LACK, fx=0.86, fy=0.8)
    b.linie(KR_HELL, (0.4, my - 2.3), (6.4, my - 2.1), 0.6)
    b.kreis((40, 36, 30), (3.8, my), 0.9)
    b.kreis((150, 146, 138), (3.8, my), 0.5)
    b.rect((30, 22, 16), -13, my - 2.5, 11.5, 5.0, 1.6)      # Sitzbank
    b.rect((98, 66, 44), -12.5, my - 2.0, 10.5, 4.0, 1.3)
    b.linie((70, 46, 30), (-7.5, my - 1.9), (-7.5, my + 1.9), 0.4)
    b.rect(KR_DK, -18.6, my - 2.2, 5.4, 4.4, 1.6)            # Schutzblech hinten, Packtasche
    b.rect(KR_LACK, -18.2, my - 1.8, 4.6, 3.6, 1.3)
    b.rect((44, 34, 24), -16.5, my - 6.2, 5.6, 2.8, 0.5)
    b.rect((122, 92, 58), -16.1, my - 5.8, 4.8, 2.0, 0.4)
    b.rohr((7.6, my - 6.8), (7.6, my + 6.8), 1.1, (150, 146, 138))   # Lenker
    for sy in (-1, 1):
        b.rect((22, 19, 17), 6.8, my + sy * 7.0 - 0.9, 1.7, 1.8, 0.4)
    _scheinwerfer(b, (10.8, my), 1.4)
    boot = [(17.5, by - 0.8), (13, by - 6.0), (-10, by - 6.8), (-13.5, by - 4.6),
            (-13.5, by + 4.6), (-10, by + 6.8), (13, by + 6.0), (17.5, by + 0.8)]
    _platte(b, boot, KR_DK, KR_LACK, fx=0.94, fy=0.88)       # Beiwagen: ein Boot aus Blech
    b.linien(KR_HELL, [(12.4, by - 5.0), (-9.6, by - 5.7), (-12.2, by - 4.0)], 0.7)
    b.linien((90, 88, 62), [(12.4, by + 5.0), (-9.6, by + 5.7), (-12.2, by + 4.0)], 0.7)
    b.rect((22, 18, 16), -10.6, by - 5.6, 15.6, 11.2, 3.0)   # Sitzmulde, gross genug fuer die Figur
    b.rect((44, 38, 34), -10.1, by - 5.1, 14.6, 10.2, 2.6)
    if beifahrer is None:
        b.rect((30, 22, 16), -9.4, by - 3.6, 6.4, 7.2, 1.6)
        b.rect((92, 62, 44), -9.0, by - 3.2, 5.6, 6.4, 1.3)
    b.kreis((22, 19, 17), (11.4, by), 3.2)                   # Reserverad auf der Nase
    b.kreis((46, 41, 37), (11.4, by), 2.5)
    b.kreis((120, 118, 86), (11.4, by), 1.1)
    _kanister(b, -13.2, by - 2.2, 2.6, 4.4)
    b.rohr((6.2, by - 4.4), (6.2, by + 4.4), 0.9, (150, 146, 138))   # Haltegriff
    _staub(b, rnd, 30, -12, 15, by - 5, by + 5, _STAUB)
    _rost(b, rnd, 9, -12, 14, by - 6, by + 6)
    if fahrer is not None:
        _insasse(b, fahrer, -2.5, my, arme=8)
    if beifahrer is not None:
        _insasse(b, beifahrer, -3.0, by, arme=8)
        # Er haelt seine eigene Waffe ueber den Bug.
        b.rect((26, 24, 22), 3.5, by - 0.4, 13, 1.5, 0.4)
        b.rect((90, 88, 82), 3.9, by - 0.1, 12, 0.8, 0.3)
        b.rect((92, 62, 44), 1.8, by - 0.6, 3.4, 1.9, 0.4)
    return b.fertig()


@platzhalter("krad")
def _krad():
    return krad_zeichnen()


@platzhalter("krad_beiwagen")
def _krad_beiwagen():
    return krad_zeichnen()


@platzhalter("krad_fahrer")
def _krad_fahrer():
    return krad_zeichnen(_NEUTRAL)


@platzhalter("krad_beiwagen_fahrer")
def _krad_beiwagen_fahrer():
    return krad_zeichnen(_NEUTRAL, _NEUTRAL)


@platzhalter("krad_wrack")
def _krad_wrack():
    return _wrack(krad_zeichnen(), 7180)


@platzhalter("krad_schatten")
def _krad_schatten():
    return _schatten_bild(96, 48, 30, 8)


def _krad_team(kombi, zwei: bool):
    def z():
        f = _kombi_fahrer(kombi)
        return krad_zeichnen(f, f if zwei else None)
    return z


for _kombi in K.TEAMS["kombi"]:
    _kurz = _kombi["name"].lower()
    platzhalter("krad_%s_fahrer" % _kurz)(_krad_team(_kombi, False))
    platzhalter("krad_beiwagen_%s_fahrer" % _kurz)(_krad_team(_kombi, True))


# ──────────────────────────────── Jagdpanzer

JP_LACK = (156, 138, 88)          # dunkelgelb
JP_DK = (76, 64, 38)
JP_HELL = (196, 178, 124)
JP_SCHATTEN = (118, 102, 62)
_KUPPEL = (-5, -3.6)              # Luke des Kommandanten, Entwurfspixel
_STAUB_JP = [(166, 150, 104), (130, 116, 76), (190, 174, 130), (116, 100, 66)]


def jagdpanzer_wanne(ph_links: float = 0.0, ph_rechts: float = 0.0) -> pygame.Surface:
    """Wanne mit Ketten, Schuerzen, Bugplatte und der flachen Kasematte.
    Das Rohr und die Luke gehoeren zum drehenden Teil."""
    b = _Blatt()
    rnd = random.Random(7201)
    _kette(b, -31, 30, -16.5, 8.2, ph_links)
    _kette(b, -31, 30, 16.5, 8.2, ph_rechts)
    umriss = [(32, -6), (27, -13.4), (-26, -13.4), (-31, -10), (-31, 10), (-26, 13.4),
              (27, 13.4), (32, 6)]
    b.poly(JP_DK, umriss)
    b.poly(JP_LACK, [(x * 0.95 - 0.2, y * 0.9) for x, y in umriss])
    b.poly(JP_HELL, [(31.2, -5.6), (26.4, -12), (15, -12), (15, 12), (26.4, 12), (31.2, 5.6)])
    for sy in (-1, 1):                          # Schuerzen ueber den Ketten, eine fehlt
        for i, x in enumerate((-24, -13, -2, 9)):
            if sy == 1 and i == 1:
                continue
            b.rect(JP_DK, x, sy * 19.4 - 2.0, 10, 4.0, 0.3)
            b.rect(JP_SCHATTEN if sy > 0 else JP_LACK, x + 0.4, sy * 19.4 - 1.6, 9.2, 3.2, 0.2)
            b.kreis(JP_DK, (x + 1.4, sy * 19.4), 0.4)
            b.kreis(JP_DK, (x + 8.6, sy * 19.4), 0.4)
    kas = [(19, -9), (9, -12.4), (-13, -12.4), (-18, -9), (-18, 9), (-13, 12.4),
           (9, 12.4), (19, 9)]
    b.poly((40, 34, 20), [(x * 1.04, y * 1.05) for x, y in kas])
    b.poly(JP_DK, kas)
    dach = [(13, -6.4), (6, -9), (-11, -9), (-14, -6.6), (-14, 6.6), (-11, 9), (6, 9), (13, 6.4)]
    b.poly(JP_HELL, [kas[1], kas[2], kas[3], dach[3], dach[2], dach[1]])
    b.poly(JP_SCHATTEN, [kas[6], kas[5], kas[4], dach[4], dach[5], dach[6]])
    b.poly(JP_LACK, [kas[0], kas[1], dach[1], dach[0], dach[7], dach[6], kas[6], kas[7]])
    b.poly((132, 116, 72), [kas[3], kas[4], dach[4], dach[3]])
    b.poly(JP_LACK, dach)
    b.linien(JP_DK, dach + [dach[0]], 0.5)
    # Tarnflecken, beschnitten auf die Wanne
    schicht = pygame.Surface(b.s.get_size(), pygame.SRCALPHA)
    alt, b.s = b.s, schicht
    for _ in range(16):
        cx, cy = rnd.uniform(-30, 30), rnd.uniform(-13, 13)
        f = rnd.choice([(104, 68, 40), (86, 96, 58), (104, 68, 40)])
        for _ in range(5):
            b.kreis(f, (cx + rnd.uniform(-2.6, 2.6), cy + rnd.uniform(-1.8, 1.8)),
                    rnd.uniform(1.2, 2.8))
    maske = pygame.Surface(schicht.get_size(), pygame.SRCALPHA)
    b.s = maske
    b.poly((255, 255, 255, 255), umriss)
    b.s = alt
    schicht.blit(maske, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    b.s.blit(schicht, (0, 0))
    b.rect(JP_DK, -11, 3.4, 7, 4.6, 0.8)        # Ladeluke
    b.rect(JP_SCHATTEN, -10.6, 3.8, 6.2, 3.8, 0.6)
    b.linie(JP_DK, (-7.5, 3.8), (-7.5, 7.6), 0.4)
    b.rect((30, 30, 30), 5.5, -7.2, 3.6, 2.2, 0.5)     # Winkelspiegel
    b.rect((60, 92, 110), 8.2, -6.8, 0.8, 1.4, 0.2)
    b.rect((30, 30, 30), 3, 5.2, 4.4, 2.4, 0.5)
    b.rect((60, 92, 110), 6.4, 5.6, 0.9, 1.6, 0.2)
    b.rect((40, 38, 34), -29.4, -8, 10, 16, 1.0)       # Motordeck, Auspuffe
    b.rect((84, 78, 62), -29, -7.6, 9.2, 15.2, 0.8)
    for i in range(6):
        y = -6.2 + i * 2.5
        b.linie((34, 32, 28), (-28.4, y), (-20.4, y), 0.9)
    for sy in (-1, 1):
        b.rect((44, 40, 36), -32.6, sy * 9.6 - 1.5, 3.6, 3.0, 0.8)
        b.kreis((18, 16, 14), (-32.6, sy * 9.6), 0.8)
    b.rect((40, 28, 18), -16, -15.6, 26, 3.2, 1.5)     # Baumstamm, Schleppseil
    b.rect((122, 88, 54), -15.6, -15.2, 25.2, 2.4, 1.2)
    for x in (-10, -2, 6):
        b.linie((70, 48, 30), (x, -15.2), (x + 1.2, -12.9), 0.35)
    b.linien((52, 50, 46), [(-14, 13.9), (-4, 14.6), (8, 13.9), (16, 12.6)], 0.8)
    _scheinwerfer(b, (27.6, -9.4), 0.9)
    _nieten(b, [(x, sy * 11.6) for x in range(-24, 14, 5) for sy in (-1, 1)], JP_DK)
    _staub(b, rnd, 70, -30, 30, -12.5, 12.5, _STAUB_JP)
    for _ in range(12):
        b.kreis(rnd.choice(_ROST), (rnd.uniform(-29, 27), rnd.choice((-1, 1)) * rnd.uniform(11, 13)),
                rnd.uniform(0.3, 0.8))
    return b.fertig()


def jagdpanzer_aufbau(fahrer=None, rueckstoss: float = 0.0) -> pygame.Surface:
    """Der drehende Teil, 160 x 160, Drehpunkt in der Mitte: die Blende mit
    dem langen Rohr und der Muendungsbremse, dazu die Luke. Mit `fahrer`
    steht der Kommandant darin. `rueckstoss`: so viele Pixel faehrt das
    Rohr zurueck."""
    b = _Blatt(160, G)
    r = -rueckstoss / G
    gy = 0.0
    b.rect((30, 28, 24), 6 + r, gy - 2.1, 46, 4.2, 1.2)
    b.rect((104, 98, 80), 6.6 + r, gy - 1.4, 45, 2.8, 1.0)
    b.linie((150, 144, 122), (7 + r, gy - 0.8), (50 + r, gy - 0.8), 0.5)
    b.rect((26, 24, 20), 46 + r, gy - 3.3, 6, 6.6, 1.0)
    b.rect((92, 88, 76), 46.6 + r, gy - 2.7, 4.8, 5.4, 0.8)
    b.linie((26, 24, 20), (49 + r, gy - 2.7), (49 + r, gy + 2.7), 0.9)
    blende = [(24 + r * 0.3, gy - 2.4), (20, gy - 5.4), (14, gy - 6), (14, gy + 6),
              (20, gy + 5.4), (24 + r * 0.3, gy + 2.4)]
    b.poly(JP_DK, blende)
    b.poly(JP_HELL, [(x * 0.97 + 0.5, gy + (y - gy) * 0.82) for x, y in blende])
    b.linie(JP_SCHATTEN, (15, gy + 4.2), (22, gy + 2.2), 0.8)
    kl = _KUPPEL
    rr = 5.2
    b.kreis(JP_DK, kl, rr)
    b.kreis(JP_SCHATTEN, kl, rr - 0.7)
    for i in range(6):
        a = i * math.pi / 3 + 0.3
        b.rect((40, 58, 70), kl[0] + math.cos(a) * 4.2 - 0.5, kl[1] + math.sin(a) * 4.2 - 0.5,
               1.0, 1.0, 0.3)
    if fahrer is None:
        b.kreis(JP_DK, kl, 3.4)
        b.kreis(JP_LACK, kl, 2.8)
        b.kreis(JP_HELL, (kl[0] - 1.0, kl[1] - 1.0), 1.1)
    else:
        b.kreis((18, 16, 14), kl, 3.6)
        art._insasse_auf(b.s, _SS, b.n // 2, fahrer, kl[0] * G, kl[1] * G, arme=None)
        b.segment(JP_DK, 6.4 / G, rr, -180, 180, kl[0], kl[1])
        b.segment(JP_SCHATTEN, 6.9 / G, rr - 0.5, -180, 180, kl[0], kl[1])
    return b.fertig(rand=True)


def _jagdpanzer_ganz(fahrer=None) -> pygame.Surface:
    s = pygame.Surface((160, 160), pygame.SRCALPHA)
    w = jagdpanzer_wanne()
    s.blit(w, w.get_rect(center=(80, 80)))
    t = jagdpanzer_aufbau(fahrer)
    s.blit(t, t.get_rect(center=(80, 80)))
    return pygame.transform.smoothscale(s.subsurface(pygame.Rect(16, 16, 128, 128)), (128, 128))


@platzhalter("jagdpanzer")
def _jagdpanzer():
    return jagdpanzer_wanne()


@platzhalter("jagdpanzer_rohr")
def _jagdpanzer_rohr():
    return jagdpanzer_aufbau()


@platzhalter("jagdpanzer_rohr_fahrer")
def _jagdpanzer_rohr_fahrer():
    return jagdpanzer_aufbau(_NEUTRAL)


@platzhalter("jagdpanzer_wrack")
def _jagdpanzer_wrack():
    return _wrack(_jagdpanzer_ganz(), 7280)


@platzhalter("jagdpanzer_schatten")
def _jagdpanzer_schatten():
    return _schatten(int(66 * G), int(44 * G), 14)


def _rohr_team(kombi):
    def z():
        return jagdpanzer_aufbau(_kombi_fahrer(kombi))
    return z


for _kombi in K.TEAMS["kombi"]:
    platzhalter("jagdpanzer_rohr_%s_fahrer" % _kombi["name"].lower())(_rohr_team(_kombi))


# ──────────────────────────────── Trosswagen (seit 0.34.108)

HK_LACK = (126, 120, 92)
HK_DK = (60, 56, 40)
HK_HELL = (168, 160, 126)
HK_SCHATTEN = (96, 90, 66)
HOLZ = (128, 96, 62)
HOLZ_DK = (74, 52, 34)
PLANE = (164, 146, 108)
PLANE_DK = (112, 96, 68)
PLANE_HELL = (196, 180, 140)
GLAS_DK = (24, 30, 36)
_STAUB_TW = [(150, 142, 110), (118, 110, 84), (176, 166, 132), (104, 96, 70)]


def _munkiste(b, x, y, w, h, streifen=(214, 178, 72)):
    b.rect((40, 50, 34), x, y, w, h, 0.4)
    b.rect((86, 104, 62), x + 0.4, y + 0.4, w - 0.8, h - 0.8, 0.3)
    b.rect(streifen, x + 0.4, y + h * 0.42, w - 0.8, h * 0.16)
    b.linie((40, 50, 34), (x + w * 0.3, y + 0.4), (x + w * 0.3, y + h - 0.4), 0.3)
    b.linie((40, 50, 34), (x + w * 0.7, y + 0.4), (x + w * 0.7, y + h - 0.4), 0.3)


def _fass(b, c, r, farbe, dk):
    b.kreis(dk, c, r)
    b.kreis(farbe, c, r - 0.5)
    b.kreis(dk, c, r * 0.55)
    b.kreis(farbe, c, r * 0.55 - 0.35)
    b.kreis(tuple(min(255, v + 46) for v in farbe), (c[0] - r * 0.3, c[1] - r * 0.3), r * 0.22)


def trosswagen_zeichnen() -> pygame.Surface:
    """Halbkette mit Pritsche, Plane, Kisten, Faessern und Kranarm. Vorn
    gelenkte Raeder, hinten Ketten; Platz fuer den Fahrer unter dem Verdeck
    (er ist nicht zu sehen). Hinten steht, wer sich Nachschub holt."""
    b = _Blatt()
    rnd = random.Random(7301)
    b.rohr((21, -10), (21, 10), 1.8, (96, 92, 86))
    _reifen(b, 21, -13.2, 10.5, 5.6, 0.0)
    _reifen(b, 21, 13.2, 10.5, 5.6, 0.0)
    _kette(b, -29, 7, -14.2, 7.4, 0.0)
    _kette(b, -29, 7, 14.2, 7.4, 0.0)
    b.rect((30, 28, 24), 31.4, -10.5, 2.6, 21, 0.6)          # Stossstange mit Seilwinde
    b.rect((104, 98, 88), 31.8, -10.1, 1.8, 20.2, 0.4)
    b.rect((40, 36, 30), 29.4, -2.6, 2.6, 5.2, 0.5)
    for i in range(4):
        b.linie((120, 114, 100), (29.8, -2 + i * 1.3), (31.6, -2 + i * 1.3), 0.35)
    for sy in (-1, 1):
        _scheinwerfer(b, (29.6, sy * 7.6), 1.2)
        b.rect(HK_DK, 15.4, sy * 13.4 - 3.8, 11.6, 7.6, 2.4)     # Kotfluegel
        b.rect(HK_LACK if sy < 0 else HK_SCHATTEN, 15.9, sy * 13.4 - 3.3, 10.6, 6.6, 2.0)
    haube = [(30, -5.6), (28, -8.4), (13.5, -9.6), (13.5, 9.6), (28, 8.4), (30, 5.6)]
    b.poly(HK_DK, haube)
    b.poly(HK_LACK, [(x * 0.97 + 0.3, y * 0.88) for x, y in haube])
    b.linie(HK_HELL, (15, -7.4), (27.4, -6.6), 0.8)
    b.linie(HK_DK, (14.5, 0), (29, 0), 0.5)
    for i in range(5):
        y = -5.6 + i * 1.5
        b.linie(HK_DK, (18, y), (24, y), 0.5)
        b.linie(HK_DK, (18, -y), (24, -y), 0.5)
    b.rect(HK_DK, 1, -12, 12.5, 24, 1.4)                      # Fuehrerhaus mit Stoffdach
    b.rect(PLANE_DK, 1.5, -11.5, 11.5, 23, 1.2)
    b.rect(PLANE, 2.2, -10.8, 9.6, 21.6, 1.0)
    for y in (-5.4, 0, 5.4):
        b.linie(PLANE_DK, (2.4, y), (11.6, y), 0.5)
    b.linie(PLANE_HELL, (2.6, -10.2), (11.2, -10.2), 0.7)
    b.rect(GLAS_DK, 12.2, -9.6, 1.5, 19.2, 0.3)
    b.rect((70, 96, 112), 12.5, -8.8, 0.7, 7.6, 0.2)
    b.rect((70, 96, 112), 12.5, 1.2, 0.7, 7.6, 0.2)
    for sy in (-1, 1):
        b.rohr((11, sy * 12), (13.4, sy * 15.6), 0.8)
        b.rect((30, 30, 32), 12.6, sy * 15.6 - 1.1, 1.6, 2.2, 0.4)
    b.rect(HK_DK, -31, -13, 32, 26, 0.8)                      # Pritsche aus Holz
    b.rect(HOLZ_DK, -30.3, -12.3, 30.6, 24.6, 0.5)
    for i in range(8):
        b.rect(HOLZ if i % 2 else (116, 86, 54), -30, -11.8 + i * 3.05, 30, 2.7, 0.2)
    for x in (-22, -12, -3):
        b.linie(HOLZ_DK, (x, -12), (x, 12), 0.35)
    b.linien(HK_HELL, [(-30.4, -12.5), (0.4, -12.5)], 0.9)
    b.linien(HK_SCHATTEN, [(-30.4, 12.5), (0.4, 12.5)], 0.9)
    _munkiste(b, -8.5, -11, 7.5, 5)                           # Ladung
    _munkiste(b, -8.5, -5.4, 7.5, 5)
    _munkiste(b, -16.8, -11, 7.5, 5, (196, 72, 52))
    b.rect((70, 66, 60), -8.6, 2.6, 7.6, 7.6, 0.5)            # Sanitaetskiste mit Kreuz
    b.rect((226, 220, 204), -8.1, 3.1, 6.6, 6.6, 0.4)
    b.rect((196, 52, 44), -5.6, 4.2, 1.6, 4.4)
    b.rect((196, 52, 44), -7.0, 5.6, 4.4, 1.6)
    _fass(b, (-13.4, 7.6), 3.0, (150, 62, 44), (62, 26, 20))
    _fass(b, (-13.4, 1.4), 3.0, (70, 110, 112), (30, 48, 50))
    _fass(b, (-19.8, 7.8), 3.0, (150, 62, 44), (62, 26, 20))
    b.rect((44, 40, 36), -16.6, -4.6, 6.4, 4.2, 0.4)          # Werkzeugkiste
    b.rect((150, 60, 44), -16.2, -4.2, 5.6, 3.4, 0.3)
    b.linie((226, 220, 204), (-15.6, -2.5), (-11.2, -2.5), 0.45)
    plane = [(-18, -12.4), (-30.6, -12.4), (-30.6, 2), (-24, 4), (-19, -3)]
    b.poly(PLANE_DK, plane)                                   # Plane ueber dem Heck
    b.poly(PLANE, [(x * 0.985 - 0.3, y * 0.95 - 0.2) for x, y in plane])
    b.linien(PLANE_HELL, [(-30, -11.6), (-19, -11.6)], 0.7)
    b.linien(PLANE_DK, [(-29, -8), (-24, -6.4), (-20.6, -8.4)], 0.5)
    b.linien(PLANE_DK, [(-29.6, -2.4), (-25, -1.2), (-21.4, -4.4)], 0.5)
    b.rohr((-24, 9.6), (-34.5, 3.4), 1.5, (150, 146, 138))    # Kranarm am Heck
    b.rohr((-24, -1.2), (-34.5, 3.4), 1.5, (150, 146, 138))
    b.kreis((30, 28, 26), (-34.8, 3.4), 1.7)
    b.kreis((150, 146, 138), (-34.8, 3.4), 0.9)
    b.linie((52, 50, 46), (-34.8, 3.4), (-38, 3.4), 0.6)
    b.kreis((22, 19, 17), (-26.4, 8.6), 3.2)                  # Reserverad
    b.kreis((46, 41, 37), (-26.4, 8.6), 2.5)
    b.kreis((96, 92, 86), (-26.4, 8.6), 1.0)
    _staub(b, rnd, 60, -30, 30, -12, 12, _STAUB_TW)
    _rost(b, rnd, 14, 14, 30, -9, 9)
    return b.fertig()


@platzhalter("trosswagen")
def _trosswagen():
    return trosswagen_zeichnen()


@platzhalter("trosswagen_wrack")
def _trosswagen_wrack():
    return _wrack(trosswagen_zeichnen(), 7380)


@platzhalter("trosswagen_schatten")
def _trosswagen_schatten():
    return _schatten(int(64 * G), int(34 * G), 11)


# ──────────────────────────────── Spulenwagen (seit 0.34.110)

KUPFER = (184, 112, 62)
KUPFER_HELL = (232, 164, 96)
TEAL = (110, 226, 208)
TEAL_HELL = (214, 255, 246)
CHOR = (226, 222, 208)
CHOR_DK = (120, 118, 110)
CHOR_SCHATTEN = (176, 172, 160)
CHOR_HELL = (250, 248, 238)
_STAUB_SP = [(176, 160, 124), (150, 134, 100), (196, 182, 150)]


def _halb_durch(b, zeichnen):
    """Etwas halb durchsichtig auflegen: auf eigener Flaeche, dann blitten."""
    s = pygame.Surface(b.s.get_size(), pygame.SRCALPHA)
    alt, b.s = b.s, s
    try:
        zeichnen()
    finally:
        b.s = alt
    b.s.blit(s, (0, 0))


def spulenwagen_zeichnen(glut: float = 0.3) -> pygame.Surface:
    """Das erbeutete Sechsrad des Chors: helle Keramikplatten, nachgeruestet
    mit Rost, Platte und Kanistern; hinten die Spule mit Kupferwicklung und
    einem Kern, der mit `glut` (0 bis 1) leuchtet. Der Fahrer sitzt hinter
    dem Glasband."""
    b = _Blatt()
    rnd = random.Random(8001)
    for ax in (20, -2, -22):
        for sy in (-1, 1):
            _reifen(b, ax, sy * 15.2, 10.5, 5.4, 0.0)
            b.rect(CHOR_DK, ax - 6.6, sy * 12.6 - 3.4, 13.2, 6.8, 2.8)
            b.rect(CHOR if sy < 0 else CHOR_SCHATTEN, ax - 6.1, sy * 12.6 - 2.9, 12.2, 5.8, 2.4)
    rumpf = [(33, 0), (27, -9.4), (-27, -11.6), (-32, -7), (-32, 7), (-27, 11.6), (27, 9.4)]
    b.poly(CHOR_DK, rumpf)
    b.poly(CHOR, [(x * 0.965, y * 0.92) for x, y in rumpf])
    b.linien(CHOR_HELL, [(26, -8.2), (-26.4, -10.2), (-30.4, -6.4)], 1.0)
    b.linien(CHOR_SCHATTEN, [(26, 8.2), (-26.4, 10.2), (-30.4, 6.4)], 1.2)
    for x in (16, 6, -6, -18):
        b.linie((168, 164, 152), (x, -10), (x, 10), 0.4)
    b.linie((168, 164, 152), (-26, 0), (16, 0), 0.35)
    kanzel = [(31, 0), (26.6, -6.8), (18, -7.6), (18, 7.6), (26.6, 6.8)]
    b.poly(CHOR_DK, kanzel)
    b.poly((28, 44, 50), [(30, 0), (26, -6), (19, -6.8), (19, 6.8), (26, 6)])
    b.poly((70, 124, 130), [(29.2, -0.8), (25.6, -5.4), (20, -6.0), (20, -1.4)])
    b.linie((150, 214, 210), (21, -5.2), (25.2, -4.8), 0.5)
    for sy in (-1, 1):
        b.kreis((28, 44, 50), (29.6, sy * 4.8), 0.9)
        b.kreis(TEAL, (29.6, sy * 4.8), 0.55)
    b.rect((60, 40, 26), 6.6, 2.4, 9.4, 6.6, 0.4)             # nachgeruestete Platte
    b.rect((132, 80, 46), 7.0, 2.8, 8.6, 5.8, 0.3)
    _nieten(b, [(7.8, 3.6), (14.8, 3.6), (7.8, 7.8), (14.8, 7.8)], (60, 40, 26), 0.4)
    b.rohr((7, -8.4), (16, -8.0), 0.8, (120, 110, 96))
    b.rohr((7, -4.2), (16, -4.0), 0.8, (120, 110, 96))
    _kanister(b, 8.6, -8.0, 4.6, 3.4)
    b.rect(PLANE_DK, 12.6, -7.6, 3.4, 3.2, 0.8)
    b.rect(PLANE, 13.0, -7.2, 2.6, 2.4, 0.6)
    for sy in (-1, 1):                                        # Kondensatoren am Heck
        for i in range(3):
            c = (-29.2 + i * 4.4, sy * 7.2)
            b.kreis((40, 44, 46), c, 2.1)
            b.kreis((104, 124, 126), c, 1.6)
            b.kreis((196, 226, 222), (c[0] - 0.5, c[1] - 0.5), 0.55)
            b.linie((30, 28, 26), c, (-13.5 + i * 1.5, sy * 4.2), 0.45)
    b.rect((40, 44, 46), -32.6, -4.4, 3.0, 8.8, 0.4)          # Kuehlrippen
    for i in range(6):
        b.linie((150, 160, 158), (-32.3, -3.6 + i * 1.44), (-29.9, -3.6 + i * 1.44), 0.4)
    c = (-9, 0)
    if glut > 0:
        _halb_durch(b, lambda: b.kreis(TEAL + (int(40 + 60 * glut),), c, 12.6))
    b.kreis((36, 34, 32), c, 10.4)                            # die Spule
    for i in range(10):
        a = i * math.pi / 5 + 0.2
        p = (c[0] + math.cos(a) * 9.0, c[1] + math.sin(a) * 9.0)
        b.kreis((70, 66, 60), p, 1.5)
        b.kreis((232, 226, 210), p, 1.1)
        b.kreis((176, 170, 156), p, 0.5)
    b.kreis((70, 40, 22), c, 7.6)
    for i, rr in enumerate((7.2, 6.4, 5.6)):
        b.kreis(KUPFER if i % 2 == 0 else KUPFER_HELL, c, rr)
        b.kreis((110, 62, 34), c, rr - 0.42)
    b.kreis(KUPFER, c, 5.0)
    b.segment(KUPFER_HELL, 5.0, 7.3, -160, -100, c[0], c[1])
    b.kreis((52, 54, 56), c, 4.7)
    b.kreis((188, 192, 190), c, 4.2)
    b.segment((236, 240, 238), 2.6, 4.0, -170, -80, c[0], c[1])
    b.segment((120, 124, 124), 2.6, 4.0, 10, 100, c[0], c[1])
    b.kreis((30, 44, 46), c, 2.5)
    b.kreis(tuple(int(v * (0.45 + 0.55 * glut)) for v in TEAL), c, 2.0)
    if glut > 0.3:
        b.kreis(TEAL_HELL, c, 1.0)
    _staub(b, rnd, 50, -30, 30, 6, 10.6, _STAUB_SP)
    _staub(b, rnd, 24, -30, 30, -10.6, -7, _STAUB_SP[:2])
    _rost(b, rnd, 8, -28, 26, 8, 10.4)
    return b.fertig()


@platzhalter("spulenwagen")
def _spulenwagen():
    return spulenwagen_zeichnen(0.3)


@platzhalter("spulenwagen_aktiv")
def _spulenwagen_aktiv():
    return spulenwagen_zeichnen(1.0)


@platzhalter("spulenwagen_wrack")
def _spulenwagen_wrack():
    return _wrack(spulenwagen_zeichnen(0.0), 7480)


@platzhalter("spulenwagen_schatten")
def _spulenwagen_schatten():
    return _schatten(int(66 * G), int(36 * G), 12)
