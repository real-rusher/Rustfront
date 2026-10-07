"""Erzeugt STAUBTAL aus dem grossen Grundriss und festen Landmarken.

ACHTUNG: karten/staubtal.txt wurde nach dem Erzeugen von Hand
nachgearbeitet (0.34.0 Aufzug-Vorfelder, 0.34.1 Gaenge zu den Aufzuegen
im Fels, Fels statt einzelner Tuerfelder). Neu erzeugen ueberschreibt das;
danach `python tests/test_pruefung.py` laufen lassen.

Bekannt (0.34.1): die Haeuser von Hotzone 2 und zwei weitere Haeuser
werden hier auf Ebene 0 gezeichnet, liegen aber unter einem Plateau -
im Fels sind sie unsichtbar. Gemeint war vermutlich Ebene 1 bzw. 2.
"""
from pathlib import Path

B, H = 300, 240
SAND, WAND, DECKUNG, LOCH = ".", "#", "X", "~"

# Die Rechtecke folgen dem WhatsApp-Grundriss: ein langes oberes Plateau,
# zwei kleinere Plateaus unten und das hohe Plateau im Nordosten.
PLATEAUS_1 = ((5, 5, 294, 83), (8, 161, 51, 232),
              (214, 168, 263, 207))
PLATEAU_2 = (220, 5, 286, 143)

# Aufzuege aus dem Plan: sechs vom Sand auf Hoehe 1, zwei von Hoehe 1 auf 2.
AUFZUEGE_01 = ((18, 82), (90, 82), (192, 82), (46, 190),
               (210, 176), (273, 193))
AUFZUEGE_12 = ((224, 29), (240, 137))

KREISE = (("A", 0, 150, 137), ("B", 1, 150, 48),
          ("C", 0, 150, 197))


def gitter(fuellung):
    return [[fuellung] * B for _ in range(H)]


def in_bounds(x, y):
    return 0 <= x < B and 0 <= y < H


def rechteck(g, x0, y0, x1, y1, zeichen, rand=False):
    for y in range(max(0, y0), min(H, y1 + 1)):
        for x in range(max(0, x0), min(B, x1 + 1)):
            if not rand or x in (x0, x1) or y in (y0, y1):
                g[y][x] = zeichen


def haus(g, box, deuren=(), fuellung=SAND):
    x0, y0, x1, y1 = box
    rechteck(g, x0, y0, x1, y1, WAND, rand=True)
    for x, y in deuren:
        if in_bounds(x, y):
            g[y][x] = fuellung


def deckungsgruppe(g, cx, cy, ausdehnung=2):
    """Zwei versetzte, sichtblockende Seitenbunker mit freiem Mittelgang."""
    for seite in (-1, 1):
        x = cx + seite * ausdehnung
        for dy in (-2, -1, 1, 2):
            if in_bounds(x, cy + dy):
                g[cy + dy][x] = WAND
        if in_bounds(cx + seite * (ausdehnung + 1), cy):
            g[cy][cx + seite * (ausdehnung + 1)] = WAND
        # Fassbarrikaden lassen eine zweite Deckungslinie hinter den Mauern.
        for dx in (ausdehnung + 2, ausdehnung + 3):
            if in_bounds(cx + seite * dx, cy - 1):
                g[cy - 1][cx + seite * dx] = DECKUNG
            if in_bounds(cx + seite * dx, cy + 1):
                g[cy + 1][cx + seite * dx] = DECKUNG


def plattform(g, box, fuellung=SAND):
    x0, y0, x1, y1 = box
    rechteck(g, x0, y0, x1, y1, fuellung)
    # Gestaffelte Fasserbruestung, mit offenen Passagen an den Ecken.
    for x in range(x0 + 2, x1 - 1, 4):
        g[y0][x] = DECKUNG
        g[y1][x] = DECKUNG
    for y in range(y0 + 2, y1 - 1, 4):
        g[y][x0] = DECKUNG
        g[y][x1] = DECKUNG


def bauen():
    e0, e1, e2 = gitter(SAND), gitter(LOCH), gitter(LOCH)
    rechteck(e0, 0, 0, B - 1, H - 1, WAND, rand=True)

    # Hoehe 1 und 2 haben jeweils einen passenden Felsunterbau darunter.
    for box in PLATEAUS_1:
        plattform(e1, box)
        rechteck(e0, *box, WAND)
    plattform(e2, PLATEAU_2)
    rechteck(e1, *PLATEAU_2, WAND)
    rechteck(e0, *PLATEAU_2, WAND)

    # Die drei Aufzuege suedlich und oestlich der Plateaus bekommen
    # begehbare Verbindungsstege auf Hoehe 1, wie im Plan eingezeichnet.
    for box in ((206, 172, 218, 180), (259, 189, 276, 197),
                (237, 137, 243, 168), (209, 27, 225, 31)):
        rechteck(e1, *box, SAND)
        rechteck(e0, *box, WAND)

    # Weite, gut lesbare Truemmerfelder. Die Mitte bleibt offen, damit die
    # Groesse sichtbar und die drei Hotzones aus der Ferne auffindbar sind.
    for box in (
        (38, 108, 56, 111), (73, 116, 76, 136), (223, 98, 244, 101),
        (30, 151, 47, 154), (69, 180, 72, 197), (229, 220, 249, 223),
        (253, 113, 256, 129), (83, 214, 101, 217), (195, 111, 211, 114),
    ):
        rechteck(e0, *box, DECKUNG)

    # Hotzone 2: Aussenposten und Gassen, aber ein freier Platz um den Kreis.
    haus(e0, (118, 28, 137, 39), ((127, 28), (118, 34)))
    haus(e0, (163, 30, 182, 42), ((173, 42), (163, 35)))
    rechteck(e0, 139, 25, 143, 35, DECKUNG)
    rechteck(e0, 157, 42, 161, 55, DECKUNG)
    rechteck(e0, 130, 59, 139, 61, WAND)
    rechteck(e0, 162, 58, 171, 60, WAND)

    # Hotzone 1 bleibt ein offenes Sandfeld mit einzelnen Deckungsinseln.
    for box in ((130, 126, 133, 132), (167, 143, 170, 149),
                (137, 158, 143, 160), (157, 119, 162, 121)):
        rechteck(e0, *box, DECKUNG)

    # Hotzone 3 liegt in einem befestigten Aussenposten. Vier Gebaeude
    # umschliessen einen begehbaren Hof; Tore und versetzte Barrikaden halten
    # mehrere Wege offen. Die Zone selbst bleibt frei begehbar.
    rechteck(e0, 95, 166, 205, 229, WAND, rand=True)
    for x, y in ((148, 166), (152, 166), (95, 194), (95, 199),
                 (205, 188), (205, 193), (145, 229), (155, 229)):
        e0[y][x] = SAND
    haus(e0, (105, 173, 130, 188), ((117, 188), (130, 180)))
    haus(e0, (170, 172, 195, 187), ((182, 187), (170, 179)))
    haus(e0, (104, 207, 130, 222), ((116, 207), (130, 216)))
    haus(e0, (171, 207, 196, 222), ((183, 207), (171, 216)))
    # Seitenwaende staffeln die Schusslinien in den Hof, ohne ihn zu sperren.
    for box in ((134, 179, 136, 188), (164, 180, 166, 189),
                (134, 207, 136, 217), (164, 206, 166, 217)):
        rechteck(e0, *box, WAND)
    for x, y in ((142, 190), (158, 190), (142, 204), (158, 204),
                 (139, 197), (161, 197)):
        e0[y][x] = DECKUNG

    # Gebaeude, Schuetzengraeben und Schrottinseln verteilen sich ueber das
    # riesige Spielfeld, mit mehreren breiten Routen zwischen den Punkten.
    for box, doors in (
        ((25, 101, 42, 116), ((33, 101), (42, 109))),
        ((92, 100, 107, 116), ((99, 116), (107, 108))),
        ((257, 96, 278, 113), ((266, 96), (257, 106))),
        ((31, 132, 47, 145), ((39, 145), (47, 137))),
        ((254, 145, 276, 160), ((264, 145), (254, 153))),
        ((61, 205, 78, 220), ((69, 205), (78, 213))),
        ((222, 51, 236, 64), ((229, 64), (236, 57))),
    ):
        haus(e0, box, doors)
    for box in (
        (15, 121, 22, 123), (53, 91, 62, 93), (81, 153, 90, 155),
        (214, 112, 222, 114), (282, 151, 285, 161), (25, 188, 33, 190),
        (74, 225, 84, 227), (215, 151, 218, 160), (282, 216, 285, 226),
        (122, 94, 129, 96), (183, 151, 191, 153), (267, 70, 277, 72),
    ):
        rechteck(e0, *box, DECKUNG)

    # Auf der oberen Etage setzen direkte Flankenbunker die Ausgaenge in
    # Deckung: nach dem Hochfahren ist sofort ein Weg nach links oder rechts
    # und dahinter jeweils ein Sichtschutz erreichbar.
    for x, y in AUFZUEGE_01:
        deckungsgruppe(e1, x, y, 2)
    # Die hohen Plattformen haben dieselbe geschuetzte Ausstiegssituation.
    for x, y in AUFZUEGE_12:
        deckungsgruppe(e2, x, y, 2)

    # Im Sand eine kleine Deckungskrone um jeden unteren Aufzugseingang.
    for x, y in AUFZUEGE_01:
        deckungsgruppe(e0, x, y, 3)

    # Aufzugskacheln zuletzt setzen, damit keine Mauer ihre Verbindung kappt.
    for x, y in AUFZUEGE_01:
        e0[y][x] = "^"
        e1[y][x] = "v"
    for x, y in AUFZUEGE_12:
        e1[y][x] = "^"
        e2[y][x] = "v"

    # Kreis A, B und C stehen in der Kartenreihenfolge. C sitzt im Hof.
    for zeichen, ebene, x, y in KREISE:
        (e0 if ebene == 0 else e1)[y][x] = zeichen

    # Gegner erscheinen an festen Deckungs- und Gebaeudekanten, nie mitten
    # auf offenem Sand. Oberhalb gibt es weitere Marken fuer Plateaukaempfe.
    spawnpunkte = []
    for x, y in ((12, 102), (48, 115), (83, 105), (110, 133), (190, 108),
                 (245, 105), (281, 125), (57, 159), (88, 202), (215, 128),
                 (278, 179), (38, 222), (88, 235), (214, 226), (280, 230),
                 (108, 195), (191, 195), (126, 169), (174, 229)):
        spawnpunkte.append((e0, x, y))
    for x, y in ((14, 18), (80, 68), (131, 74), (180, 67), (205, 32),
                 (279, 60), (20, 214), (40, 179), (235, 177), (255, 197)):
        spawnpunkte.append((e1, x, y))
    for x, y in ((230, 17), (275, 90), (229, 126)):
        spawnpunkte.append((e2, x, y))
    for g, x, y in spawnpunkte:
        if g[y][x] == SAND:
            g[y][x] = "Z"

    return e0, e1, e2


def schreiben(pfad):
    ebenen = bauen()
    kopf = [
        "# STAUBTAL - Wuestenkarte nach dem markierten Lageplan.",
        "# 300 x 240 Kacheln; ein Rasterfeld entspricht einer Spielkachel.",
        "# A, B und C sind Hotzones 1 bis 3; C liegt im befestigten Hof.",
        "# ^ und v sind Aufzuege. Nach oben fuehrt der Ausgang in seitliche",
        "# Deckung. X sind Fass-/Schrottbarrikaden, # sind sichtdichte Waende.",
        "",
        "name: STAUBTAL",
        "satz: wueste",
        "kreise: A B C",
        "",
    ]
    teile = ["\n".join(kopf)]
    for i, g in enumerate(ebenen):
        zeilen = ["".join(z) for z in g]
        teile.append("--- ebene %d ---\n" % i + "\n".join(zeilen) + "\n")
    Path(pfad).write_text("\n".join(teile).rstrip("\n") + "\n",
                          encoding="utf-8")
    return ebenen


if __name__ == "__main__":
    import sys
    ziel = sys.argv[1] if len(sys.argv) > 1 else "karten/staubtal.txt"
    Path(ziel).parent.mkdir(parents=True, exist_ok=True)
    ebenen = schreiben(ziel)
    print("geschrieben:", ziel)
    print("Masse je Ebene: %d x %d Kacheln (%d x %d Pixel)" %
          (B, H, B * 32, H * 32))
    print("Hotzones: A, B, C; Aufzuege: %d" %
          (len(AUFZUEGE_01) + len(AUFZUEGE_12)))
