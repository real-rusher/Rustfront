"""
DUSTFRONT - Die Abwurfkapsel fuer gerufene Waffen (seit 0.34.155)
===============================================================

Gewuenscht: gerufene Waffen sollen "anders spawnen und deutlich schneller ...
in einem kleinen, fuer ihre Groesse passenden quasi Hellpot kommen, was dann
kurz explodiert und die Waffe zuruecklaesst. Gib dir sehr, sehr viel Muehe bei
dem genauen Aussehen der Animation."

Der Ablauf (Zahlen in K.SCHLACHT kapsel):

1. **Markierung.** Die Abwurfzone mit ihren Fackeln steht nur `vorlauf`
   Sekunden (statt 6 s fuer Kisten).
2. **Fall.** Die Kapsel kommt beinahe senkrecht aus dem Himmel, immer
   schneller (`tempo`, `beschl`) - ein halbe Sekunde vom Bildrand bis zum
   Boden. Sie gluehst an der Nase, dahinter ein Feuerschweif, der in Rauch
   uebergeht, und am Boden waechst ihr Schatten. Von schraeg oben gesehen
   (wie alles, was in diesem Spiel hoch ist) steht sie aufrecht im Bild, der
   Schweif darueber.
3. **Einschlag** (`einschlag`, ein Effekt, den auch der Gast bekommt): ein
   Blitz, eine Staubwand, die ueber den Boden rollt, ein Ring, Erdbrocken,
   Funken, ein kleiner Krater, ein Ruck der Kamera. Die Kapsel steckt jetzt
   im Boden: ein achteckiger Koerper, oben vier Klappen mit den Streifen der
   Seite, in der Mitte ein Licht, das blinkt. Sie gluehst am Fuss nach und
   dampft aus den Fugen.
4. **Aufsprengen** nach `auf_nach` Sekunden (`auf`): ein heller Knall, die
   vier Klappen fliegen schraeg nach aussen, ueberschlagen sich, springen
   einmal auf und bleiben liegen; Rauch aus dem offenen Ring. In der Mitte
   liegt die Waffe (eine KampfBeute, die der Gastgeber genau jetzt setzt).
   Ring und Klappen bleiben `liegen` Sekunden, dann verblassen sie.

Groesse: je Waffe aus `groesse` (Laenge der Kapsel in Pixeln) - eine
Panzerbuechse braucht eine laengere Kapsel als ein Spulengewehr.

Alles, was man sieht, kommt aus diesen Daten: die Fallhoehe folgt allein aus
dem Alter (`hoehe`), die Effekte tragen Groesse, Seite und Richtung in einer
Zahl (`kodieren`). So sieht der Gast genau dasselbe wie der Gastgeber.
"""

from __future__ import annotations

import math

import pygame

from . import config as K

# Farben (Metall wie die Fahrzeuge, Warnfarbe wie an den Kisten).
_RUMPF = (78, 82, 78)
_RUMPF_HELL = (112, 116, 108)
_RUMPF_DUNKEL = (48, 50, 50)
_KANTE = (26, 26, 28)
_FUGE = (30, 30, 32)
_WARN = (222, 182, 62)
_BODEN_INNEN = (132, 128, 114)      # Bodenblech: hell, damit die Waffe darauf zu sehen ist
_GLUT = ((255, 248, 220), (255, 214, 120), (250, 150, 50), (210, 80, 30))


def daten() -> dict:
    return K.SCHLACHT["kapsel"]


def ist_kapsel(art: str) -> bool:
    """Kommt diese Art in einer Kapsel? (Alle gerufenen Waffen.)"""
    return isinstance(art, str) and art.startswith("waffe_")


def groesse(art: str) -> int:
    """Laenge der Kapsel fuer diese Art (Pixel)."""
    d = daten()
    return int(d["groesse"].get(art[6:] if ist_kapsel(art) else art, d["groesse_vorgabe"]))


def fallzeit() -> float:
    """So lange faellt die Kapsel von `hoehe` bis zum Boden (s)."""
    d = daten()
    a, v, h = 0.5 * d["beschl"], d["tempo"], d["hoehe"]
    return (-v + math.sqrt(v * v + 4.0 * a * h)) / (2.0 * a)


def hoehe(alter: float) -> float:
    """Wie hoch sie nach `alter` Sekunden Fall noch ist (Pixel, >= 0)."""
    d = daten()
    t = max(0.0, float(alter))
    return max(0.0, d["hoehe"] - d["tempo"] * t - 0.5 * d["beschl"] * t * t)


def tempo(alter: float) -> float:
    d = daten()
    return d["tempo"] + d["beschl"] * max(0.0, float(alter))


def kodieren(laenge: int, team: int, winkel: float) -> float:
    """Groesse, Seite und Richtung in einer Zahl fuer Welt.explosion (die geht
    auf 0,1 gerundet an den Gast): Laenge * 1000 + (Seite + 1) * 100 + Winkel / 4."""
    w = int(round((float(winkel) % 360.0) / 4.0)) % 90
    t = max(0, min(2, int(team) + 1))
    return float(max(8, min(99, int(laenge))) * 1000 + t * 100 + w)


def dekodieren(code: float) -> tuple:
    c = int(round(float(code)))
    laenge = c // 1000
    team = (c // 100) % 10 - 1
    winkel = (c % 100) * 4.0
    return max(8, laenge), team, winkel


def teamfarbe(team: int) -> tuple:
    if 0 <= team < len(K.TEAMS["kombi"]):
        return tuple(K.TEAMS["kombi"][team]["hud"])
    return (200, 200, 190)


def _dunkler(farbe, f: float) -> tuple:
    return tuple(max(0, min(255, int(c * f))) for c in farbe)


def _achteck(mx: float, my: float, r: float, dreh: float = 22.5) -> list:
    return [(mx + r * math.cos(math.radians(dreh + 45 * i)),
             my + r * math.sin(math.radians(dreh + 45 * i))) for i in range(8)]


# ══════════════════════════════════════════════════════════════════
# Bilder (gemerkt - jede Kapsel wird je Groesse, Seite, Winkel einmal gemalt)
# ══════════════════════════════════════════════════════════════════

_MERK: dict = {}


def _merk(schluessel, bauen):
    s = _MERK.get(schluessel)
    if s is None:
        if len(_MERK) > 400:
            _MERK.clear()
        s = _MERK[schluessel] = bauen()
    return s


def _deckel(flaeche, mx: float, my: float, r: float, team: int, licht: bool, zu: bool) -> None:
    """Die Oberseite: Achteck mit vier Klappen, Streifen der Seite, Licht."""
    farbe = teamfarbe(team)
    aussen = _achteck(mx, my, r)
    # Je Flaeche des Achtecks heller oder dunkler (Licht von oben links).
    for i in range(8):
        a, b = aussen[i], aussen[(i + 1) % 8]
        mitte_w = 22.5 + 45 * i + 22.5
        hell = 0.84 + 0.22 * math.cos(math.radians(mitte_w - 225.0))
        pygame.draw.polygon(flaeche, _dunkler(_RUMPF, hell), [(mx, my), a, b])
    innen = _achteck(mx, my, r * 0.62)
    pygame.draw.polygon(flaeche, _RUMPF_HELL, innen)
    pygame.draw.polygon(flaeche, _dunkler(_RUMPF_HELL, 0.78), innen, 1)
    # Streifen der Seite: ein Band je Klappe nahe am Rand.
    for k in range(4):
        w0 = math.radians(45 + 90 * k - 26)
        w1 = math.radians(45 + 90 * k + 26)
        pkte = [(mx + r * 0.9 * math.cos(w0), my + r * 0.9 * math.sin(w0)),
                (mx + r * 0.9 * math.cos(w1), my + r * 0.9 * math.sin(w1)),
                (mx + r * 0.72 * math.cos(w1), my + r * 0.72 * math.sin(w1)),
                (mx + r * 0.72 * math.cos(w0), my + r * 0.72 * math.sin(w0))]
        pygame.draw.polygon(flaeche, farbe, pkte)
    # Warnecken (gelb) auf den Fugen.
    for k in range(4):
        w = math.radians(90 * k)
        p = (mx + r * 0.8 * math.cos(w), my + r * 0.8 * math.sin(w))
        pygame.draw.circle(flaeche, _WARN, (int(round(p[0])), int(round(p[1]))), max(1, int(r * 0.09)))
    # Die Fugen: ein Kreuz, das die vier Klappen trennt.
    if zu:
        for k in range(4):
            w = math.radians(90 * k)
            pygame.draw.line(flaeche, _FUGE, (mx + r * 0.2 * math.cos(w), my + r * 0.2 * math.sin(w)),
                             (mx + r * math.cos(w), my + r * math.sin(w)), 1)
    pygame.draw.polygon(flaeche, _KANTE, aussen, 1)
    # Die Luke in der Mitte mit dem Licht.
    rl = max(2, int(r * 0.22))
    pygame.draw.circle(flaeche, _RUMPF_DUNKEL, (int(mx), int(my)), rl)
    pygame.draw.circle(flaeche, _KANTE, (int(mx), int(my)), rl, 1)
    if licht:
        pygame.draw.circle(flaeche, (255, 255, 240), (int(mx), int(my)), max(1, rl - 2))
        pygame.draw.circle(flaeche, farbe, (int(mx), int(my)), max(1, rl - 1), 1)
    else:
        pygame.draw.circle(flaeche, _dunkler(farbe, 0.55), (int(mx), int(my)), max(1, rl - 2))


def bild_zu(laenge: int, team: int, licht: bool) -> pygame.Surface:
    """Die Kapsel steckt im Boden: ein achteckiger Koerper, von schraeg oben
    gesehen - unten die Seitenflaechen (dunkler), darueber der Deckel."""

    def bauen():
        r = laenge * 0.5
        hoch = max(4, int(laenge * 0.36))           # so weit ragt sie aus dem Boden
        n = int(laenge + 10)
        f = pygame.Surface((n, n + hoch), pygame.SRCALPHA)
        mx, my = n / 2.0, n / 2.0
        # Seitenflaechen: das untere Achteck, nach unten versetzt, dann die
        # Waende zwischen beiden. Nur die nach vorn (unten im Bild) sieht man.
        unten = _achteck(mx, my + hoch, r)
        oben = _achteck(mx, my, r)
        for i in range(8):
            a, b = oben[i], oben[(i + 1) % 8]
            c, d = unten[(i + 1) % 8], unten[i]
            if (a[1] + b[1]) / 2.0 < my - r * 0.2:
                continue
            mitte_w = 45 * i + 45
            hell = 0.62 + 0.18 * math.cos(math.radians(mitte_w - 135.0))
            pygame.draw.polygon(f, _dunkler(_RUMPF, hell), [a, b, c, d])
            pygame.draw.line(f, _KANTE, a, d, 1)
        # Rost- und Brandspuren am Fuss.
        for i in range(3, 7):
            a, b = unten[i], unten[(i + 1) % 8]
            pygame.draw.line(f, (52, 38, 28), a, b, 2)
        _deckel(f, mx, my, r, team, licht, True)
        return f

    return _merk(("zu", laenge, team, licht), bauen)


def bild_offen(laenge: int, team: int) -> pygame.Surface:
    """Was nach dem Aufsprengen am Boden bleibt: der Ring der Kapsel mit
    seinen Scharnieren, innen der verbrannte Boden."""

    def bauen():
        r = laenge * 0.5
        hoch = 3
        n = int(laenge + 10)
        f = pygame.Surface((n, n + hoch), pygame.SRCALPHA)
        mx, my = n / 2.0, n / 2.0
        unten = _achteck(mx, my + hoch, r)
        oben = _achteck(mx, my, r)
        for i in range(8):
            a, b = oben[i], oben[(i + 1) % 8]
            c, d = unten[(i + 1) % 8], unten[i]
            if (a[1] + b[1]) / 2.0 < my - r * 0.2:
                continue
            pygame.draw.polygon(f, _dunkler(_RUMPF, 0.6), [a, b, c, d])
        pygame.draw.polygon(f, _dunkler(_RUMPF, 0.92), oben)
        innen = _achteck(mx, my, r * 0.74)
        pygame.draw.polygon(f, _BODEN_INNEN, innen)
        # Riffelblech: feine Rillen, aussen Russ vom Aufsprengen.
        ri = r * 0.74
        apo, kante = ri * math.cos(math.radians(22.5)), ri * math.sin(math.radians(22.5))
        for j in range(-int(apo) + 1, int(apo), 3):
            halb = min(apo, apo + kante - abs(j)) - 1       # Breite des Achtecks in dieser Zeile
            if halb > 1:
                pygame.draw.line(f, _dunkler(_BODEN_INNEN, 0.86), (mx - halb, my + j), (mx + halb, my + j), 1)
        pygame.draw.polygon(f, (58, 52, 46), _achteck(mx, my, r * 0.74), 2)
        pygame.draw.polygon(f, _KANTE, innen, 1)
        pygame.draw.polygon(f, _KANTE, oben, 1)
        # Die Scharniere, an denen die Klappen sassen (Seitenfarbe).
        farbe = teamfarbe(team)
        for k in range(4):
            w = math.radians(45 + 90 * k)
            p = (mx + r * 0.86 * math.cos(w), my + r * 0.86 * math.sin(w))
            pygame.draw.rect(f, _RUMPF_DUNKEL, (int(p[0]) - 2, int(p[1]) - 2, 4, 4))
            pygame.draw.rect(f, farbe, (int(p[0]) - 1, int(p[1]) - 1, 2, 2))
        return f

    return _merk(("offen", laenge, team), bauen)


def klappe_punkte(laenge: int) -> list:
    """Eine der vier Klappen (ein Viertel des Deckels zwischen zwei Fugen),
    um ihre Mitte: innen am Rand der Luke, aussen zwei Ecken des Achtecks."""
    r = laenge * 0.5
    kante = r * math.cos(math.radians(22.5))       # wo die Fuge auf die Seite trifft
    luke = r * 0.22
    pk = [(luke, 0.0), (kante, 0.0),
          (r * math.cos(math.radians(22.5)), r * math.sin(math.radians(22.5))),
          (r * math.cos(math.radians(67.5)), r * math.sin(math.radians(67.5))),
          (0.0, kante), (0.0, luke)]
    mx = sum(p[0] for p in pk) / len(pk)
    my = sum(p[1] for p in pk) / len(pk)
    return [(x - mx, y - my) for x, y in pk]


# ══════════════════════════════════════════════════════════════════
# Zeichnen
# ══════════════════════════════════════════════════════════════════

def flug_zeichnen(ziel, boden, hub: float, laenge: int, team: int, alter: float, zeit: float) -> None:
    """Die fallende Kapsel: Schatten am Boden, die Kapsel `hub` Pixel darueber
    (aufrecht, Nase unten), darueber Feuerschweif und Rauch."""
    d = daten()
    anteil = 1.0 - min(1.0, hub / max(1.0, d["hoehe"] * K.SCHLACHT["abwurf"]["bild_hub"]))
    bx, by = float(boden[0]), float(boden[1])
    # Schatten: waechst und wird dunkler, je naeher sie kommt.
    sw = int(6 + laenge * 0.55 * (0.4 + 0.6 * anteil))
    sch = pygame.Surface((sw * 2, sw), pygame.SRCALPHA)
    pygame.draw.ellipse(sch, (10, 8, 6, int(40 + 150 * anteil)), sch.get_rect())
    ziel.blit(sch, (int(bx - sw), int(by - sw // 2)))
    # Ein Kreuz am Boden, das scharf wird (wohin sie faellt).
    if anteil > 0.15:
        farbe = teamfarbe(team)
        k = int(4 + 6 * (1.0 - anteil))
        a = int(120 + 135 * anteil)
        kreuz = pygame.Surface((k * 2 + 3, k * 2 + 3), pygame.SRCALPHA)
        pygame.draw.line(kreuz, farbe + (a,), (0, k + 1), (k * 2 + 2, k + 1), 1)
        pygame.draw.line(kreuz, farbe + (a,), (k + 1, 0), (k + 1, k * 2 + 2), 1)
        ziel.blit(kreuz, (int(bx - k - 1), int(by - k - 1)))
    x = bx
    unten = by - hub                     # die Nase
    breit = max(4, int(laenge * 0.5))
    lang = int(laenge * 1.15)
    oben = unten - lang
    # Der Schweif: weit oben Rauch, naeher Feuer, an der Kapsel weissgluehend.
    schweif = min(170.0, 60.0 + tempo(alter) * 0.08)
    flacker = 0.5 + 0.5 * math.sin(zeit * 47.0 + laenge)
    for i in range(9, -1, -1):
        t = i / 9.0
        y = oben - schweif * t
        r = breit * (0.5 + 1.1 * t) * (0.9 + 0.15 * flacker)
        grau = int(150 - 60 * t)
        deck = int(150 * (1.0 - t) ** 0.8)
        if deck <= 8:
            continue
        s = pygame.Surface((int(r * 2) + 2, int(r * 2) + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (grau, grau, grau - 6, deck), (int(r) + 1, int(r) + 1), int(r))
        ziel.blit(s, (int(x - r - 1 + math.sin(zeit * 9 + i) * t * 3), int(y - r - 1)))
    for i, (farbe, l, w) in enumerate(((_GLUT[3], 0.36, 0.75), (_GLUT[2], 0.26, 0.6),
                                        (_GLUT[1], 0.16, 0.42), (_GLUT[0], 0.08, 0.25))):
        ll = schweif * l * (0.85 + 0.3 * flacker)
        ww = max(1.0, breit * w)
        pkte = [(x - ww, oben + 2), (x + ww, oben + 2), (x + ww * 0.25, oben - ll), (x - ww * 0.25, oben - ll)]
        pygame.draw.polygon(ziel, farbe, pkte)
    # Der Koerper: aufrecht, Flaechen von links hell nach rechts dunkel.
    halb = breit / 2.0
    for j in range(int(breit)):
        f = 0.7 + 0.45 * math.cos(math.radians(150.0 * (j / max(1.0, breit - 1)) - 40.0))
        pygame.draw.line(ziel, _dunkler(_RUMPF, f), (x - halb + j, oben + 2), (x - halb + j, unten - breit * 0.6))
    # Streifen der Seite und Warnband.
    farbe = teamfarbe(team)
    pygame.draw.rect(ziel, farbe, (int(x - halb), int(oben + lang * 0.28), int(breit), 2))
    pygame.draw.rect(ziel, _WARN, (int(x - halb), int(oben + lang * 0.52), int(breit), 1))
    # Flossen oben.
    pygame.draw.polygon(ziel, _RUMPF_DUNKEL, [(x - halb, oben + 6), (x - halb - 3, oben + 1), (x - halb, oben + 1)])
    pygame.draw.polygon(ziel, _RUMPF_DUNKEL, [(x + halb, oben + 6), (x + halb + 3, oben + 1), (x + halb, oben + 1)])
    # Die Nase: glueht, je schneller, desto heller.
    gl = min(3, int(tempo(alter) / 500.0))
    nase = [(x - halb, unten - breit * 0.6), (x + halb, unten - breit * 0.6), (x, unten)]
    pygame.draw.polygon(ziel, _GLUT[3 - gl], nase)
    pygame.draw.polygon(ziel, _GLUT[max(0, 2 - gl)], [(x - halb * 0.5, unten - breit * 0.45),
                                                      (x + halb * 0.5, unten - breit * 0.45), (x, unten - 1)])
    pygame.draw.rect(ziel, _KANTE, (int(x - halb), int(oben + 1), int(breit), int(lang - breit * 0.6)), 1)
    # Ein schwacher Hitzeschimmer um die Nase - nur ein Hauch, die Kapsel
    # selbst soll man sehen.
    rg = max(3, int(breit * 0.7))
    s = pygame.Surface((rg * 2, rg * 2), pygame.SRCALPHA)
    pygame.draw.circle(s, (120, 60, 20, 0), (rg, rg), rg)
    pygame.draw.circle(s, (90, 46, 14, int(40 + 30 * flacker)), (rg, rg), rg)
    pygame.draw.circle(s, (140, 80, 30, int(50 + 30 * flacker)), (rg, rg), max(1, rg // 2))
    ziel.blit(s, (int(x - rg), int(unten - rg - breit * 0.2)), special_flags=pygame.BLEND_RGB_ADD)


def fx_zeichnen(ziel, f, x: float, y: float) -> None:
    """Die Teile der Kapsel im Effektsystem (effekte._zeichne)."""
    a = f.anteil
    laenge = int(f.r0)
    team = int(f.variante)
    if f.art == "kapsel_zu":
        # Das Licht blinkt, schneller, je naeher das Aufsprengen.
        takt = 5.0 + 12.0 * a
        licht = int(f.alter * takt) % 2 == 0
        s = bild_zu(laenge, team, licht)
        hoch = s.get_height() - s.get_width()
        # Beim Einschlag ein kurzes Nachfedern (sie sackt 2 px ein).
        sack = 2.0 * math.exp(-f.alter * 12.0) * math.cos(f.alter * 40.0)
        ziel.blit(s, (int(x - s.get_width() / 2), int(y - s.get_width() / 2 - hoch + sack)))
        # Am Fuss glueht sie nach (die ersten Zehntelsekunden).
        if f.alter < 0.45:
            # Ein schmaler gluehender Saum am Fuss, kein Fleck.
            g = 1.0 - f.alter / 0.45
            r = int(laenge * 0.5 + 2)
            glut = pygame.Surface((r * 2, r), pygame.SRCALPHA)
            pygame.draw.ellipse(glut, (int(150 * g), int(70 * g), int(20 * g)), glut.get_rect(), 2)
            ziel.blit(glut, (int(x - r), int(y - r // 2)), special_flags=pygame.BLEND_RGB_ADD)
    elif f.art == "kapsel_offen":
        s = bild_offen(laenge, team)
        if a > 0.82:
            s = s.copy()
            s.set_alpha(int(255 * (1.0 - a) / 0.18))
        ziel.blit(s, (int(x - s.get_width() / 2), int(y - s.get_width() / 2 - (s.get_height() - s.get_width()))))
    elif f.art == "klappe":
        pk = klappe_punkte(laenge)
        w = math.radians(f.winkel)
        cw, sw = math.cos(w), math.sin(w)
        # Ueberschlagen: eine Achse wird schmal und wieder breit.
        kipp = abs(math.cos(math.radians(f.winkel * 1.7))) if f.z > 0.5 else 1.0
        welt = []
        for px, py in pk:
            py *= max(0.15, kipp)
            welt.append((x + px * cw - py * sw, y + px * sw + py * cw))
        if f.z > 1.0:
            # Ein halb durchsichtiger Schatten (ein harter schwarzer sah aus wie ein Loch).
            sch = [(px, py + f.z) for px, py in welt]
            x0 = int(min(p[0] for p in sch)) - 1
            y0 = int(min(p[1] for p in sch)) - 1
            fl = pygame.Surface((int(max(p[0] for p in sch)) - x0 + 2, int(max(p[1] for p in sch)) - y0 + 2),
                                pygame.SRCALPHA)
            pygame.draw.polygon(fl, (10, 8, 6, 90), [(px - x0, py - y0) for px, py in sch])
            ziel.blit(fl, (x0, y0))
        hell = 0.95 + 0.4 * kipp
        farbe = _dunkler(_RUMPF, hell)
        if a > 0.82:
            deck = (1.0 - a) / 0.18
            farbe = _dunkler(farbe, 0.4 + 0.6 * deck)
        pygame.draw.polygon(ziel, farbe, welt)
        # Der Streifen der Seite auf der Klappe.
        if kipp > 0.35:
            mx = sum(p[0] for p in welt) / len(welt)
            my = sum(p[1] for p in welt) / len(welt)
            aussen = ((welt[2][0] + welt[3][0]) / 2, (welt[2][1] + welt[3][1]) / 2)
            pygame.draw.line(ziel, teamfarbe(team), aussen, ((aussen[0] * 2 + mx) / 3, (aussen[1] * 2 + my) / 3), 2)
        pygame.draw.polygon(ziel, _KANTE, welt, 1)
        if kipp > 0.5:
            # Eine helle Kante oben links (Licht).
            pygame.draw.line(ziel, _dunkler(_RUMPF_HELL, 1.25), welt[1], welt[2], 1)


# ══════════════════════════════════════════════════════════════════
# Effekte (Welt.explosion -> effekte.ARTEN, beim Gast genauso)
# ══════════════════════════════════════════════════════════════════

def einschlag(welt, pos, ebene: int, code: float) -> None:
    """Die Kapsel schlaegt ein und steckt im Boden."""
    from . import effekte as fx
    laenge, team, winkel = dekodieren(code)
    d = daten()
    x, y = float(pos[0]), float(pos[1])
    r = fx._rnd(pos, 21)
    fx.blitz(welt, x, y, 4, ebene, laenge * 1.6, 0.08)
    welt.lichtblitz(pygame.Vector2(x, y), ebene, laenge * 1.2)
    # Staub, der ueber den Boden rollt, und ein Ring.
    fx.staubwand(welt, r, x, y, ebene, laenge * 0.6, 14, "staub", tempo=230.0, groesse=(5, 10), dauer=1.4)
    fx.ring(welt, x, y, ebene, laenge * 0.4, laenge * 2.2, 0.4, (236, 220, 182))
    fx.ring(welt, x, y, ebene, laenge * 0.3, laenge * 1.3, 0.25, (255, 236, 200))
    fx.brockenwurf(welt, r, x, y, 4, ebene, 10, 170.0, "erde", (1, 3), hoch=(0.5, 1.3), liegen=3.0)
    fx.funken(welt, r, x, y, 6, ebene, 14, 260.0, 0.35, farbe=(255, 210, 140), hoch=0.5)
    fx.rauch(welt, r, x, y, 3, ebene, "staub", laenge * 0.3, laenge * 0.9, 1.6, vz=20.0, zaeh=2.0)
    welt.krater(pygame.Vector2(x, y), ebene, laenge * 0.5, int(abs(x) * 7 + abs(y) * 13))
    # Die Kapsel selbst, bis sie aufgeht.
    f = fx.Fx("kapsel_zu", x, y, 0.0, ebene, d["auf_nach"])
    f.r0 = laenge
    f.variante = team
    f.winkel = winkel
    fx._neu(welt, f)
    # Dampf aus den Fugen, nacheinander.
    for i in range(5):
        w = math.radians(90 * (i % 4) + r.uniform(-20, 20))
        fx.rauch(welt, r, x + math.cos(w) * laenge * 0.4, y + math.sin(w) * laenge * 0.4 - laenge * 0.3,
                 6, ebene, "grau", 2, r.uniform(4, 7), r.uniform(0.6, 0.9), vz=r.uniform(18, 30),
                 zaeh=2.0, verzoegert=i * d["auf_nach"] / 6.0, dicht=0.6)
    welt.ruckeln(4.5, "explosion", pygame.Vector2(x, y), ebene)
    welt.klang("einschlag", 0.75, pygame.Vector2(x, y), ebene)
    welt.klang("buggy_aufprall", 0.6, pygame.Vector2(x, y), ebene)


def auf(welt, pos, ebene: int, code: float) -> None:
    """Die Kapsel sprengt ihre Klappen ab: die Waffe liegt frei."""
    from . import effekte as fx
    laenge, team, winkel = dekodieren(code)
    d = daten()
    x, y = float(pos[0]), float(pos[1])
    r = fx._rnd(pos, 22)
    fx.blitz(welt, x, y, 8, ebene, laenge * 1.3, 0.06)
    fx.funken(welt, r, x, y, 8, ebene, 16, 220.0, 0.3, farbe=(255, 236, 180), hoch=0.7)
    fx.rauch(welt, r, x, y, 6, ebene, "grau", laenge * 0.25, laenge * 0.8, 1.2, vz=30.0, zaeh=2.2)
    fx.ring(welt, x, y, ebene, laenge * 0.3, laenge * 1.5, 0.3, (230, 230, 230))
    # Der Ring, der liegen bleibt.
    f = fx.Fx("kapsel_offen", x, y, 0.0, ebene, d["liegen"])
    f.r0 = laenge
    f.variante = team
    f.boden = True
    fx._neu(welt, f)
    # Die vier Klappen fliegen schraeg nach aussen.
    for k in range(4):
        w = math.radians(45 + 90 * k + r.uniform(-12, 12))
        v = r.uniform(70, 120) * (laenge / 30.0)
        kl = fx.Fx("klappe", x + math.cos(w) * laenge * 0.25, y + math.sin(w) * laenge * 0.25,
                   laenge * 0.3, ebene, d["liegen"])
        kl.r0 = laenge
        kl.variante = team
        kl.vx, kl.vy = math.cos(w) * v, math.sin(w) * v
        kl.vz = r.uniform(110, 160)
        kl.g = 560.0
        kl.zaeh = 1.2
        kl.winkel = 45 + 90 * k
        kl.dreh = r.choice((-1, 1)) * r.uniform(420, 720)
        kl.prallt = True
        kl.liegt = d["liegen"] - 1.0
        fx._neu(welt, kl)
    # Rauch steigt noch eine Weile aus dem offenen Ring.
    for i in range(4):
        fx.rauch(welt, r, x, y, 4, ebene, "grau", 2, r.uniform(5, 8), r.uniform(1.4, 2.0),
                 vz=r.uniform(10, 18), zaeh=1.8, verzoegert=0.3 + i * 0.6, dicht=0.5)
    welt.ruckeln(2.5, "explosion", pygame.Vector2(x, y), ebene)
    welt.klang("knaller", 0.85, pygame.Vector2(x, y), ebene)
    welt.klang("aufheben", 0.5, pygame.Vector2(x, y), ebene)
