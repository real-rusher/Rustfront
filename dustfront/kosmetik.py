"""
DUSTFRONT - Kosmetik, vorgezeichnet
===================================

**Hier wird nichts eingebaut.** Dieses Modul zeichnet Bilder davon, wie
Kisten, Skins und die zweite Siegtafel aussehen wuerden, und sonst
nichts. Kein Spielcode ruft es auf, keine Runde haengt daran, kein Konto
bekommt dadurch ein Inventar.

    python -m dustfront --kosmetik

schreibt die Bilder nach `kosmetik_vorschau/`. Daran laesst sich
entscheiden, ob es so aussehen soll - und erst danach lohnt es sich,
darueber zu reden, wo die Gegenstaende herkommen und wem sie gehoeren.

Warum ueberhaupt schon jetzt: weil man an einem Bild in drei Sekunden
sieht, was in drei Absaetzen Text untergeht. Und weil zwei Sachen, die
dafuer noetig sind, ohnehin schon gebaut wurden und damit gleich
gepruefft werden - die **Rollen** in `K.SKIN_ROLLEN` (ein Bildname steht
nirgends fest im Code, er steht hinter einer Rolle) und die
**Seltenheitsstufen** in `K.SELTENHEIT`.

Was noch fehlt und bewusst fehlt:

* Woher ein Gegenstand kommt. Kisten? Spielzeit? Beides waere eine
  Entscheidung ueber das Spiel und nicht ueber die Anzeige.
* Wo er liegt. Das Konto kann es (Profil, Fassungszaehler, siehe
  docs/KONTO.md), aber solange es nichts zu speichern gibt, wird nichts
  gespeichert.
* Handel, Preise, alles in der Richtung. Steht nicht zur Debatte.
"""

from __future__ import annotations

import math
from pathlib import Path

import pygame

from . import config as K
from . import ui
from .font import SCHRIFT

ORDNER = "kosmetik_vorschau"

# Beispielgegenstaende. Erfunden, nur zum Ansehen - die Namen sind
# Platzhalter und sollen zeigen, wie lang ein Name sein darf.
BEISPIELE = [
    ("STURMGEWEHR", "sturm", "ROSTNARBE", 0),
    ("SCHROT", "schrot", "STAUBFÄNGER", 0),
    ("SCHARFSCHÜTZE", "scharf", "LANGER BLICK", 1),
    ("MG", "lmg", "KESSELFLICKEN", 1),
    ("REPETIERER", "repetierer", "ALTES EISEN", 0),
    ("BLENDGRANATE", "blend", "WEISSE NACHT", 2),
    ("MOLOTOW", "molotov", "LETZTE RUNDE", 2),
    ("RAKETENWERFER", "rakete", "ABSCHIED", 3),
    ("BRECHEISEN", "brecheisen", "TÜRGRUSS", 4),
]


def _flaeche():
    f = pygame.Surface((K.GAME_W, K.GAME_H))
    f.fill((14, 10, 8))
    return f


def _hinweis(f, text="VORSCHAU - NOCH NICHT EINGEBAUT"):
    """Auf jedem Bild dieselbe Zeile. Sie soll jeden Zweifel nehmen."""
    SCHRIFT.zeichnen(f, text, K.GAME_W // 2, K.GAME_H - 11, (92, 74, 56), 1,
                     ausrichtung="mitte")


def _passend(bild, rect, rand=8, hoechstens=6):
    """Ein Symbol so weit vergroessern, wie es in einen Kasten passt.

    Nur ganzzahlig. Alles andere verschmiert die Pixel, und ein Symbol,
    das man im Spiel scharf sieht, darf im Menue nicht weich werden.
    """
    b, h = bild.get_size()
    faktor = max(1, min(hoechstens, (rect.width - rand * 2) // max(1, b),
                        (rect.height - rand * 2) // max(1, h)))
    if faktor == 1:
        return bild
    return pygame.transform.scale(bild, (b * faktor, h * faktor))


def _gegenstand(f, bilder, rect, eintrag, beschriftet=True):
    """Ein Gegenstand in seiner Seltenheitsfarbe.

    Der farbige Streifen liegt **unten** und nicht als Rahmen rundum:
    ein Rahmen konkurriert mit dem Bild darin, ein Streifen nicht. So
    machen es die Spiele, die davon leben, und sie haben recht.
    """
    _, waffe, skin, stufe = eintrag
    s = K.SELTENHEIT[min(stufe, len(K.SELTENHEIT) - 1)]
    ui.kasten(f, rect, (52, 44, 34), (24, 18, 13), 3)
    # Das Bild bekommt nur die obere Haelfte: darunter stehen Name und
    # Streifen, und ein Symbol, das darauf laeuft, sieht nach Fehler aus.
    feld = pygame.Rect(rect.x, rect.y + 2, rect.width,
                       rect.height - (16 if beschriftet else 8))
    sym = _passend(bilder.bild(K.skin("%s_symbol" % waffe)), feld, 5, 3)
    f.blit(sym, (feld.centerx - sym.get_width() // 2,
                 feld.centery - sym.get_height() // 2))
    pygame.draw.rect(f, s["farbe"], (rect.x + 2, rect.bottom - 4,
                                     rect.width - 4, 2))
    if beschriftet:
        SCHRIFT.zeichnen(f, ui.kuerzen(skin, rect.width - 6),
                         rect.centerx, rect.bottom - 13, (156, 140, 114), 1,
                         ausrichtung="mitte")
    return s


# ══════════════════════════════════════════════════ 1. Die Kiste

def kiste_lauf(bilder, stand: float = 0.62):
    """Der laufende Streifen, wie man ihn aus CS kennt.

    Der Aufbau ist immer derselbe und aus gutem Grund: ein Band, das von
    rechts nach links laeuft, ein fester Zeiger in der Mitte, und eine
    Verzoegerung, die gegen Ende sehr lang wird. Man sieht die Ergebnisse
    vorbeiziehen, die man **nicht** bekommen hat - daran haengt die ganze
    Spannung, und ohne das ist es eine Ziehung mit einem Knopf davor.
    """
    f = _flaeche()
    SCHRIFT.zeichnen(f, "LIEFERUNG", K.GAME_W // 2, 24, K.C_AMBER, 3,
                     ausrichtung="mitte")
    SCHRIFT.zeichnen(f, "STAUBTAL-KISTE 01", K.GAME_W // 2, 50, K.C_MUTED, 1,
                     ausrichtung="mitte")

    band = pygame.Rect(0, 100, K.GAME_W, 96)
    pygame.draw.rect(f, (20, 15, 11), band)
    pygame.draw.line(f, (52, 44, 34), (0, band.y), (K.GAME_W, band.y))
    pygame.draw.line(f, (52, 44, 34), (0, band.bottom), (K.GAME_W, band.bottom))

    breite, luft = 84, 6
    versatz = int(stand * (breite + luft) * len(BEISPIELE)) % (breite + luft)
    x = -versatz - (breite + luft) * 2
    i = int(stand * 7)
    while x < K.GAME_W + breite:
        eintrag = BEISPIELE[i % len(BEISPIELE)]
        _gegenstand(f, bilder, pygame.Rect(x, band.y + 8, breite,
                                           band.height - 16), eintrag)
        x += breite + luft
        i += 1

    # Die Raender verlaufen ins Dunkle: das Band hat keinen Anfang und
    # kein Ende, es zieht durch. 110 Pixel, nicht 70 - bei 70 steht der
    # vorletzte Gegenstand noch fast voll im Licht, und dann sieht das
    # Band abgeschnitten aus statt endlos.
    tiefe = 110
    schleier = pygame.Surface((tiefe, band.height - 1), pygame.SRCALPHA)
    for i in range(tiefe):
        a = int(255 * (1.0 - i / float(tiefe)) ** 1.5)
        pygame.draw.line(schleier, (14, 10, 8, a), (i, 0), (i, band.height))
    f.blit(schleier, (0, band.y + 1))
    f.blit(pygame.transform.flip(schleier, True, False),
           (K.GAME_W - tiefe, band.y + 1))

    # Der Zeiger. Oben und unten ein Dreieck, dazwischen eine Linie.
    mitte = K.GAME_W // 2
    pygame.draw.line(f, K.C_AMBER, (mitte, band.y + 2), (mitte, band.bottom - 2))
    for oben in (True, False):
        y = band.y + 2 if oben else band.bottom - 2
        r = -1 if oben else 1
        for i in range(6):
            pygame.draw.line(f, K.C_AMBER, (mitte - 5 + i, y + r * i),
                             (mitte + 5 - i, y + r * i))
    SCHRIFT.zeichnen(f, "[LEERTASTE] ÜBERSPRINGEN", K.GAME_W // 2,
                     band.bottom + 12, (108, 92, 70), 1, ausrichtung="mitte")

    # Die Stufen mit ihren Anteilen. Sie stehen hier, weil sie hierhin
    # gehoeren: wer zieht, soll vorher sehen, worauf er zieht. Die Zahlen
    # kommen aus K.SELTENHEIT und sind damit nicht gemalt, sondern wahr.
    SCHRIFT.zeichnen(f, "WAS DRIN IST", K.GAME_W // 2, 238, K.C_MUTED, 1,
                     ausrichtung="mitte")
    zellen, zluft = 112, 6
    gesamt = len(K.SELTENHEIT) * zellen + (len(K.SELTENHEIT) - 1) * zluft
    zx = (K.GAME_W - gesamt) // 2
    for j, s in enumerate(K.SELTENHEIT):
        r = pygame.Rect(zx + j * (zellen + zluft), 254, zellen, 30)
        ui.kasten(f, r, (52, 44, 34), (20, 15, 11), 3)
        pygame.draw.rect(f, s["farbe"], (r.x + 2, r.y + 2, r.width - 4, 2))
        SCHRIFT.zeichnen(f, s["name"], r.centerx, r.y + 8, s["farbe"], 1,
                         ausrichtung="mitte")
        SCHRIFT.zeichnen(f, "%.1f%%" % (s["anteil"] * 100.0), r.centerx,
                         r.y + 19, (128, 114, 92), 1, ausrichtung="mitte")
    _hinweis(f)
    return f


def _schein(f, mitte, farbe, breite=420, hoehe=230, staerke=0.34, schaerfe=1.6):
    """Ein weicher Schein in der Seltenheitsfarbe.

    Zwei Sachen daran sind nicht selbstverstaendlich:

    * **Erst klein rechnen, dann glatt vergroessern.** Ein gestapelter
      Haufen Rechtecke oder Kreise gibt sichtbare Stufen, und Stufen sehen
      nach Kasten aus und nicht nach Licht. Ein 64x40-Feld, mit
      `smoothscale` hochgezogen, hat keine.
    * **Die Helligkeit steht im Pixel, nicht im Alpha.** `BLEND_RGB_ADD`
      rechnet die Farbkanaele zusammen und sieht das Alpha gar nicht an -
      wer die Abstufung ins Alpha legt, bekommt eine volle Flaeche.
    """
    kb, kh = 64, 40
    klein = pygame.Surface((kb, kh))
    klein.fill((0, 0, 0))
    for y in range(kh):
        dy = (y + 0.5) / kh * 2.0 - 1.0
        for x in range(kb):
            dx = (x + 0.5) / kb * 2.0 - 1.0
            d = math.hypot(dx, dy)
            if d >= 1.0:
                continue
            v = staerke * (1.0 - d) ** schaerfe
            klein.set_at((x, y), (min(255, int(farbe[0] * v)),
                                  min(255, int(farbe[1] * v)),
                                  min(255, int(farbe[2] * v))))
    schein = pygame.transform.smoothscale(klein, (int(breite), int(hoehe)))
    f.blit(schein, (mitte[0] - breite // 2, mitte[1] - hoehe // 2),
           special_flags=pygame.BLEND_RGB_ADD)


def kiste_ergebnis(bilder):
    """Was am Ende stehenbleibt.

    Ein Bild, ein Name, eine Farbe - mehr nicht. Die Versuchung ist gross,
    hier noch Zahlen hinzuschreiben (Fassungszaehler, Wert, Datum); genau
    das nimmt dem Moment aber alles. Das kommt auf die naechste Seite.
    """
    f = _flaeche()
    eintrag = ("BRECHEISEN", "brecheisen", "TÜRGRUSS", 4)
    s = K.SELTENHEIT[eintrag[3]]
    mitte = (K.GAME_W // 2, 174)
    # Gross und kraeftig: der Kasten deckt die Mitte ohnehin ab, zu sehen
    # ist nur der Saum darum - und der ist es, der den Fund traegt.
    _schein(f, mitte, s["farbe"], 560, 300, 0.90, 1.6)

    SCHRIFT.zeichnen(f, s["name"], K.GAME_W // 2, 42, s["farbe"], 3,
                     ausrichtung="mitte")

    kasten = pygame.Rect(0, 0, 300, 132)
    kasten.center = mitte
    ui.kasten(f, kasten, s["farbe"], (22, 16, 12), 5)
    sym = _passend(bilder.bild(K.skin("%s_symbol" % eintrag[1])), kasten, 16, 8)
    f.blit(sym, (kasten.centerx - sym.get_width() // 2,
                 kasten.centery - sym.get_height() // 2))
    # Der Streifen sitzt auf der Unterkante des Kastens, die Namen
    # darunter im Freien - sonst draengt sich beides auf denselben Pixeln.
    pygame.draw.rect(f, s["farbe"], (kasten.x + 4, kasten.bottom - 5,
                                     kasten.width - 8, 3))
    SCHRIFT.zeichnen(f, eintrag[2], K.GAME_W // 2, kasten.bottom + 14,
                     K.C_CREAM, 2, ausrichtung="mitte")
    SCHRIFT.zeichnen(f, eintrag[0], K.GAME_W // 2, kasten.bottom + 32,
                     (140, 124, 100), 1, ausrichtung="mitte")

    SCHRIFT.zeichnen(f, "AUS DER STAUBTAL-KISTE 01", K.GAME_W // 2, 300,
                     (108, 92, 70), 1, ausrichtung="mitte")
    SCHRIFT.zeichnen(f, "[ENTER] WEITER", K.GAME_W // 2, 320, K.C_MUTED, 1,
                     ausrichtung="mitte")
    _hinweis(f)
    return f


# ══════════════════════════════════════════════════ 2. Skins waehlen

def skinauswahl(bilder):
    """Die Maske, in der man auswaehlt, was man traegt.

    Links die Figur, rechts das, was sie tragen kann. Die Vorschau ist
    gross und links, weil man sie anschaut, waehrend man rechts
    blaettert - umgekehrt muesste der Blick staendig springen.
    """
    f = _flaeche()
    tafel = pygame.Rect(16, 14, K.GAME_W - 32, K.GAME_H - 50)
    ui.tafel(f, tafel)
    SCHRIFT.zeichnen(f, "AUSSEHEN", tafel.centerx, tafel.y + 8, K.C_AMBER, 2,
                     2, "mitte")
    pygame.draw.line(f, K.C_MUTED_DK, (tafel.x + 18, tafel.y + 24),
                     (tafel.right - 19, tafel.y + 24))

    # Links: die Figur, gross - und darunter, was sonst noch an ihr haengt.
    # Der Klang steht bewusst mit dabei: ein Blendgranaten-Skin ist zur
    # Haelfte ein Geraeusch, und wer das erst im Gefecht merkt, waehlt blind.
    vor = pygame.Rect(tafel.x + 14, tafel.y + 32, 164, 176)
    ui.kasten(f, vor, (52, 44, 34), (20, 15, 11), 4)
    figur = bilder.bild(K.skin("figur"))
    gross = pygame.transform.scale(figur, (figur.get_width() * 4,
                                           figur.get_height() * 4))
    f.blit(gross, (vor.centerx - gross.get_width() // 2, vor.y + 16))
    pygame.draw.rect(f, K.SELTENHEIT[1]["farbe"],
                     (vor.x + 4, vor.bottom - 5, vor.width - 8, 3))
    SCHRIFT.zeichnen(f, "STAUBLÄUFER", vor.centerx, vor.bottom - 32,
                     K.C_CREAM, 1, ausrichtung="mitte")
    SCHRIFT.zeichnen(f, K.SELTENHEIT[1]["name"], vor.centerx, vor.bottom - 20,
                     K.SELTENHEIT[1]["farbe"], 1, ausrichtung="mitte")
    def beilage(y, titel, wert, stufe, pegel=False):
        r = pygame.Rect(vor.x, y, vor.width, 34)
        ui.kasten(f, r, (52, 44, 34), (20, 15, 11), 3)
        SCHRIFT.zeichnen(f, titel, r.x + 8, r.y + 6, K.C_MUTED, 1)
        SCHRIFT.zeichnen(f, wert, r.x + 8, r.y + 18,
                         K.SELTENHEIT[stufe]["farbe"], 1)
        if pegel:
            for i in range(7):               # Zeichen fuer "das hoert man"
                h = 2 + int(9 * abs(math.sin(i * 1.3 + 0.4)))
                pygame.draw.rect(f, (72, 60, 44),
                                 (r.right - 14 - i * 4, r.centery + 6 - h, 2, h))
        return r

    beilage(vor.bottom + 8, "KLANG", "WEISSE NACHT", 2, True)
    beilage(vor.bottom + 50, "MUSIKKIT", "STAUBWIND", 3, True)

    # Rechts: das Raster. Vier Spalten zu 90 Pixeln - schmaler wuerde
    # jeden zweiten Namen abschneiden, und ein Skin ohne lesbaren Namen
    # ist nur ein Bildchen.
    rx, rw, luft = vor.right + 14, 90, 8

    def reihe(titel, y, eintraege, hoehe, zeichner):
        SCHRIFT.zeichnen(f, titel, rx, y - 11, K.C_MUTED, 1)
        for i, e in enumerate(eintraege):
            r = pygame.Rect(rx + (i % 4) * (rw + luft),
                            y + (i // 4) * (hoehe + 10), rw, hoehe)
            zeichner(r, i, e)
        return y + ((len(eintraege) + 3) // 4) * (hoehe + 10)

    figuren = [("STAUBLÄUFER", 1), ("ROSTGRAU", 0), ("NACHTZUG", 2),
               ("SANDKÖNIG", 3)]
    figur_zwei = pygame.transform.scale(figur, (figur.get_width() * 2,
                                                figur.get_height() * 2))

    def figur_zelle(r, i, e):
        name, stufe = e
        gewaehlt = (i == 0)
        ui.kasten(f, r, K.C_AMBER if gewaehlt else (52, 44, 34),
                  (32, 24, 16) if gewaehlt else (20, 15, 11), 3)
        f.blit(figur_zwei, (r.centerx - figur_zwei.get_width() // 2, r.y + 2))
        pygame.draw.rect(f, K.SELTENHEIT[stufe]["farbe"],
                         (r.x + 2, r.bottom - 4, r.width - 4, 2))
        SCHRIFT.zeichnen(f, ui.kuerzen(name, r.width - 6), r.centerx,
                         r.bottom - 13, K.C_CREAM if gewaehlt else
                         (156, 140, 114), 1, ausrichtung="mitte")

    y = reihe("FIGUREN", tafel.y + 40, figuren, 56, figur_zelle)
    waffen = [e for e in BEISPIELE if e[1] not in ("blend", "molotov")]
    y = reihe("WAFFEN", y + 16, waffen[:8], 48,
              lambda r, i, e: _gegenstand(f, bilder, r, e))
    wuerfe = [("BLENDGRANATE", "blend", "WEISSE NACHT", 2),
              ("MOLOTOW", "molotov", "LETZTE RUNDE", 2),
              ("GRANATE", "granate", "HANDGELD", 0),
              ("RAUCH", "rauch", "GRAUER MORGEN", 1)]
    reihe("WURF", y + 16, wuerfe, 48,
          lambda r, i, e: _gegenstand(f, bilder, r, e))

    SCHRIFT.zeichnen(f, "[PFEILE] WÄHLEN   [ESC] ZURÜCK", K.GAME_W // 2,
                     K.GAME_H - 24, (108, 92, 70), 1, ausrichtung="mitte")
    _hinweis(f)
    return f


# ══════════════════════════════════════════════════ 3. Zweite Siegtafel

def siegtafel_zwei(bilder):
    """Die Tafel nach der Tafel: drei je Mannschaft, und eine Buehne.

    Die erste Siegtafel sagt, wie die Runde ausging - Zahlen, alle
    Spieler, nuechtern. Diese hier sagt, wem sie gehoerte. Darum nur
    drei je Seite, gross, mit Namen und einem Satz dazu; und darum eine
    Buehne, auf der die Figuren etwas tun.

    Der MVP steht in der Mitte, sein Musikstueck laeuft, und die drei
    machen ihre Animation. Was genau, waehlt jeder selbst - das ist der
    Punkt an der Sache: es ist die eine Stelle im Spiel, an der man
    zeigt, was man hat, und alle schauen hin.
    """
    f = _flaeche()
    SCHRIFT.zeichnen(f, "ROT GEWINNT", K.GAME_W // 2, 12, K.TEAMS["kombi"][0]["hud"],
                     3, ausrichtung="mitte")

    # (Mannschaft, Name, Abschuesse, Tode, Lieblingswaffe)
    beste = [
        (0, "MEISTER", 18, 4, "scharf"),
        (0, "RUSHER", 12, 7, "schrot"),
        (0, "NOVA", 9, 8, "sturm"),
        (1, "TAMM", 14, 9, "lmg"),
        (1, "KOLJA", 11, 10, "sturm"),
        (1, "BESUCH", 6, 12, "repetierer"),
    ]
    for seite in range(2):
        kombi = K.TEAMS["kombi"][seite]
        x = 14 + seite * (K.GAME_W - 28 - 178)
        block = pygame.Rect(x, 40, 178, 104)
        pygame.draw.rect(f, (18, 13, 10), block)
        pygame.draw.rect(f, kombi["hud_dunkel"], block, 1)
        pygame.draw.rect(f, kombi["hud"], (block.x, block.y, block.width, 2))
        SCHRIFT.zeichnen(f, kombi["name"], block.x + 7, block.y + 8,
                         kombi["hud"], 1)
        SCHRIFT.zeichnen(f, "A / T", block.right - 7, block.y + 8,
                         K.C_MUTED_DK, 1, ausrichtung="rechts")
        y = block.y + 24
        for platz, (_, name, a, t, waffe) in enumerate(
                [b for b in beste if b[0] == seite], 1):
            farbe = K.C_CREAM if platz == 1 else K.C_MUTED
            SCHRIFT.zeichnen(f, "%d" % platz, block.x + 7, y + 6,
                             kombi["hud"] if platz == 1 else kombi["hud_dunkel"], 1)
            SCHRIFT.zeichnen(f, name, block.x + 18, y + 6, farbe, 1)
            # Die meistbenutzte Waffe als Symbol, nicht als Wort - genau
            # wie auf der ersten Tafel, damit beide dieselbe Sprache reden.
            sym = bilder.bild(K.skin("%s_symbol" % waffe))
            f.blit(sym, (block.right - 42 - sym.get_width(), y + 4))
            SCHRIFT.zeichnen(f, "%d/%d" % (a, t), block.right - 7, y + 6,
                             K.C_MUTED, 1, ausrichtung="rechts")
            y += 22

    # Die Mitte zwischen den beiden Bloecken: Karte, Stand, Musikstueck.
    # Ohne sie klafft oben ein Loch, und das Musikkit haette sonst nur
    # Platz auf der Buehne - wo es den Figuren im Weg steht.
    SCHRIFT.zeichnen(f, "STAUBTAL", K.GAME_W // 2, 46, K.C_MUTED, 2,
                     ausrichtung="mitte")
    SCHRIFT.zeichnen(f, "13", K.GAME_W // 2 - 14, 68, K.TEAMS["kombi"][0]["hud"],
                     3, ausrichtung="rechts")
    SCHRIFT.zeichnen(f, ":", K.GAME_W // 2, 68, K.C_MUTED_DK, 3,
                     ausrichtung="mitte")
    SCHRIFT.zeichnen(f, "9", K.GAME_W // 2 + 14, 68, K.TEAMS["kombi"][1]["hud"], 3)
    # Breit genug fuer den laengsten Namen, den K.LOADOUT zulaesst -
    # sonst laeuft die Schrift aus dem Kasten.
    kit = pygame.Rect(0, 0, 168, 18)
    kit.center = (K.GAME_W // 2, 116)
    ui.kasten(f, kit, K.SELTENHEIT[3]["farbe"], (28, 20, 26), 3)
    for i in range(5):                       # Pegel
        h = 3 + int(8 * abs(math.sin(i * 1.7)))
        pygame.draw.rect(f, K.SELTENHEIT[3]["farbe"],
                         (kit.x + 7 + i * 4, kit.centery + 5 - h, 2, h))
    SCHRIFT.zeichnen(f, "MUSIKKIT: STAUBWIND", kit.x + 32, kit.centery - 3,
                     K.C_CREAM, 1)

    # Die Buehne.
    buehne = pygame.Rect(14, 152, K.GAME_W - 28, 154)
    pygame.draw.rect(f, (20, 15, 11), buehne)
    pygame.draw.rect(f, (52, 44, 34), buehne, 1)
    boden = buehne.bottom - 26
    pygame.draw.line(f, (46, 38, 29), (buehne.x + 6, boden),
                     (buehne.right - 7, boden))
    figur = bilder.bild(K.skin("figur"))
    gross = pygame.transform.scale(figur, (figur.get_width() * 3,
                                           figur.get_height() * 3))
    # Reihenfolge wie auf jedem Siegerpodest: zwei links, eins in der
    # Mitte und oben, drei rechts. Das liest man ohne Beschriftung.
    for (dx, hoch, platz, name) in ((-150, 24, 2, "RUSHER"), (0, 40, 1, "MEISTER"),
                                    (150, 12, 3, "NOVA")):
        x = buehne.centerx + dx
        sockel = pygame.Rect(x - 36, boden - hoch, 72, hoch + 8)
        pygame.draw.rect(f, (34, 26, 19), sockel)
        pygame.draw.rect(f, (58, 48, 36), sockel, 1)
        SCHRIFT.zeichnen(f, "%d" % platz, x, sockel.y + 3,
                         K.C_AMBER if platz == 1 else (78, 66, 50), 2,
                         ausrichtung="mitte")
        # +16: die Figur ist von oben gezeichnet und hat unten Luft im
        # Bild. Ohne den Versatz schwebt sie ueber ihrem Podest.
        f.blit(gross, (x - gross.get_width() // 2,
                       sockel.y - gross.get_height() + 16))
        SCHRIFT.zeichnen(f, name, x, boden + 11,
                         K.C_CREAM if platz == 1 else K.C_MUTED, 1,
                         ausrichtung="mitte")
        # Andeutung einer Bewegung: ein paar Striche **neben** der Figur,
        # nicht darauf. Sie stehen fuer die Animation, die hier liefe.
        kopf = sockel.y - gross.get_height()
        for j in range(3):
            w = 5 + j * 4
            yy = kopf + 18 + j * 9
            pygame.draw.line(f, (72, 60, 44), (x + 48, yy), (x + 48 + w, yy))
            pygame.draw.line(f, (72, 60, 44), (x - 48, yy), (x - 48 - w, yy))

    SCHRIFT.zeichnen(f, "DIE DREI BESTEN MACHEN IHRE ANIMATION",
                     K.GAME_W // 2, buehne.bottom + 8, (92, 78, 58), 1,
                     ausrichtung="mitte")
    SCHRIFT.zeichnen(f, "[LEERTASTE] TAFEL   [ESC] BEENDEN", K.GAME_W // 2,
                     buehne.bottom + 22, (108, 92, 70), 1, ausrichtung="mitte")
    _hinweis(f)
    return f


# ══════════════════════════════════════════════════ Herausschreiben

def schreiben(bilder, ordner: Path | None = None, lupe: int = 2) -> list[str]:
    ziel = Path(ordner) if ordner else Path(ORDNER)
    ziel.mkdir(parents=True, exist_ok=True)
    bilderliste = [
        ("kiste_1_lauf", kiste_lauf(bilder, 0.62)),
        ("kiste_2_langsam", kiste_lauf(bilder, 0.955)),
        ("kiste_3_ergebnis", kiste_ergebnis(bilder)),
        ("skinauswahl", skinauswahl(bilder)),
        ("siegtafel_zwei", siegtafel_zwei(bilder)),
    ]
    raus = []
    for name, f in bilderliste:
        gross = pygame.transform.scale(f, (K.GAME_W * lupe, K.GAME_H * lupe))
        pfad = ziel / ("%s.png" % name)
        pygame.image.save(gross, str(pfad))
        raus.append(str(pfad))
    return raus
