"""Erzeugt die Karte STAUBTAL.

Sehr gross, sehr leer, Wueste mit Wildwest-Einschlag. Was sie ausmacht:

* **Flach.** Der Boden ist Sand, sonst nichts. Kein Gang, kein Labyrinth.
* **Plateaus statt Etagen.** Die obere Ebene besteht aus drei Tafeln, und
  unter jeder steht Fels - man kommt nicht darunter, nur hinauf.
* **Drei Kreise, die nicht gleich sind.** Einer im offenen Sand, einer in
  einer Halle, einer auf dem groessten Plateau.
* **Man findet sie.** Jeder Kreis hat ein Wahrzeichen, das von weitem zu
  sehen ist: ein Ring aus Fassern, eine Halle, ein Plateau.

Die erzeugte Datei ist danach ganz normaler Text und von Hand
weiterzubearbeiten - dieses Werkzeug setzt nur den ersten Stand.
"""
import math
from pathlib import Path

B, H = 120, 80          # Kacheln. Bei 32 Pixeln sind das 3840 x 2560.

SAND, WAND, FASS, LEER = ".", "#", "X", " "

# Plateaus: (x0, y0, x1, y1, Rampen). Eine Rampe ist (x, y) auf der
# unteren Ebene - dort steht die Treppe hinauf, und genau darueber die
# Treppe hinunter.
PLATEAUS = [
    # Das grosse in der Mitte oben: darauf liegt der dritte Kreis.
    dict(kasten=(44, 8, 76, 27), rampen=[(52, 28), (68, 28), (43, 16)]),
    # Zwei kleinere an den Flanken, als Stellungen ueber der Ebene.
    dict(kasten=(10, 44, 30, 62), rampen=[(31, 52), (20, 43)]),
    dict(kasten=(88, 40, 108, 58), rampen=[(87, 48), (98, 59)]),
]

# Gebaeude auf der Ebene: (x0, y0, x1, y1, Tueren). Eine Tuer ist ein
# Loch in der Wand, angegeben als (x, y).
GEBAEUDE = [
    # Die Halle. Gross, mit zwei weiten Toren - darin liegt Kreis zwei.
    dict(kasten=(80, 10, 108, 30),
         tueren=[(80, 19), (80, 20), (80, 21), (94, 30), (95, 30), (96, 30),
                 (108, 19), (108, 20)]),
    # Vier Buden, ueber die Karte verteilt. Sie geben Deckung, mehr nicht.
    dict(kasten=(16, 12, 26, 20), tueren=[(21, 20), (26, 16)]),
    dict(kasten=(36, 60, 48, 70), tueren=[(42, 60), (36, 65)]),
    dict(kasten=(62, 46, 72, 54), tueren=[(67, 46), (72, 50)]),
    dict(kasten=(98, 66, 110, 74), tueren=[(104, 66), (98, 70)]),
]

# Die drei Kreise. `zeichen` ist die Marke in der Karte.
KREISE = [
    # 1. Offener Sand. Erkennbar an einem Ring aus Fassern.
    dict(name="KESSEL", zeichen="A", ebene=0, mitte=(26, 33), ring=9),
    # 2. In der Halle. Erkennbar an der Halle.
    dict(name="DEPOT", zeichen="B", ebene=0, mitte=(94, 20), ring=0),
    # 3. Auf dem grossen Plateau. Erkennbar am Plateau.
    dict(name="KANZEL", zeichen="C", ebene=1, mitte=(60, 17), ring=0),
]

# Spawnstellen. Der Buchstabe Z in der Karte sagt: hier kommen Gegner
# heraus, wenn jemand in der Naehe ist.
#
# Sie sind nicht gleichmaessig verteilt, sondern dort, wo es sich
# erklaert - aus dem Dunkel unter den Plateaus, aus den Buden, aus dem
# Depot. Auf offenem Sand steht keine: mitten im Freien aus dem Nichts
# zu erscheinen sieht nach Fehler aus, hinter einer Bude hervorzukommen
# nicht. Wo keine Marke passt, sucht das Spiel selbst eine Stelle im
# Band um die Spieler (siehe K.SPAWN) - die Marken sind eine
# Bevorzugung, keine Bedingung.
SPAWNS = [
    # Am Fuss der drei Plateaus, im Schatten der Felswand.
    (42, 14, 0), (78, 22, 0), (60, 30, 0),
    (8, 46, 0), (32, 58, 0), (20, 41, 0),
    (86, 44, 0), (110, 54, 0), (98, 61, 0),
    # An den Buden.
    (14, 16, 0), (28, 22, 0), (34, 64, 0), (50, 68, 0),
    (60, 50, 0), (74, 48, 0), (96, 70, 0), (112, 68, 0),
    # Im Depot und an seinen Toren.
    (82, 26, 0), (106, 14, 0), (92, 34, 0),
    # Am Rand der Karte, wo die Mauer steht.
    (6, 8, 0), (114, 8, 0), (6, 72, 0), (114, 74, 0), (60, 76, 0),
    # Und oben auf den Plateaus - wenige, damit auch dort etwas kommt,
    # wenn dort gekaempft wird.
    (50, 12, 1), (70, 22, 1), (14, 48, 1), (26, 58, 1),
    (92, 44, 1), (104, 54, 1),
]

# Fasser und Wracks im freien Feld. Ohne sie ist eine sehr grosse,
# sehr flache Karte nur gross und flach.
STREU = [
    (34, 24, 4), (52, 38, 5), (70, 34, 3), (14, 68, 4), (56, 70, 5),
    (86, 62, 3), (30, 8, 3), (100, 36, 4), (74, 8, 3), (12, 28, 3),
    (46, 52, 4), (78, 70, 4), (110, 24, 3), (64, 62, 3), (22, 56, 3),
]


def gitter(fuell):
    return [[fuell] * B for _ in range(H)]


def rechteck(g, kasten, zeichen, nur_rand=False):
    x0, y0, x1, y1 = kasten
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if not (0 <= x < B and 0 <= y < H):
                continue
            if nur_rand and not (x in (x0, x1) or y in (y0, y1)):
                continue
            g[y][x] = zeichen


def streuen(g, cx, cy, r, zeichen=FASS, dichte=0.55):
    """Ein paar Fasser um einen Punkt. Fest gewuerfelt, damit die Karte
    auf jedem Rechner gleich aussieht - eine Karte ist eine Datei."""
    for i in range(r * 3):
        w = (i * 137) % 360
        weit = 1 + (i * 7) % max(1, r)
        x = int(cx + math.cos(math.radians(w)) * weit)
        y = int(cy + math.sin(math.radians(w)) * weit * 0.8)
        if not (1 <= x < B - 1 and 1 <= y < H - 1):
            continue
        if ((x * 73856093) ^ (y * 19349663)) % 100 < dichte * 100:
            g[y][x] = zeichen


def ring(g, cx, cy, r, zeichen=FASS):
    """Ein unterbrochener Kreis aus Fassern. Das Wahrzeichen im Sand:
    man sieht ihn von weitem und weiss sofort, was er bedeutet."""
    schritte = int(2 * math.pi * r)
    for i in range(schritte):
        w = i / schritte * 360.0
        # Vier Luecken, damit man hinein- und hinauslaufen kann.
        if (w % 90) < 26:
            continue
        x = int(round(cx + math.cos(math.radians(w)) * r))
        y = int(round(cy + math.sin(math.radians(w)) * r * 0.82))
        if 1 <= x < B - 1 and 1 <= y < H - 1:
            g[y][x] = zeichen


def bauen():
    e0 = gitter(SAND)
    e1 = gitter(LEER)

    # Rand: eine Mauer aus Fels rundum.
    rechteck(e0, (0, 0, B - 1, H - 1), WAND, nur_rand=True)

    # Plateaus. Oben Boden, unten Fels - man kommt nicht darunter.
    for p in PLATEAUS:
        rechteck(e0, p["kasten"], WAND)
        rechteck(e1, p["kasten"], SAND)
        # Eine Bruestung aus Fassern am Rand des Plateaus, damit man die
        # Kante sieht, bevor man darueber laeuft.
        x0, y0, x1, y1 = p["kasten"]
        for x in range(x0, x1 + 1, 3):
            e1[y0][x] = FASS
            e1[y1][x] = FASS
        for y in range(y0, y1 + 1, 3):
            e1[y][x0] = FASS
            e1[y][x1] = FASS

    # Rampen: unten hinauf, oben hinunter. Die Kachel darueber muss frei
    # sein, sonst steht man nach dem Wechsel in einem Fass.
    for p in PLATEAUS:
        x0, y0, x1, y1 = p["kasten"]
        for (rx, ry) in p["rampen"]:
            e0[ry][rx] = ">"
            # Die Treppe hinunter liegt **genau ueber** der Rampe, nicht
            # auf der Tafel daneben. Ein Ebenenwechsel behaelt die Stelle -
            # wer unten auf der Rampe steht, steht danach oben an derselben
            # Stelle. Bis 0.27 lag die obere Treppe eine Kachel versetzt im
            # Plateau, und ueber der Rampe war oben ein Loch: wer hinaufging,
            # fiel sofort wieder hinunter. Alle sieben Rampen, seit STAUBTAL
            # gibt - die Plateaus und damit der Kreis KANZEL waren nie zu
            # erreichen. Die obere Treppe ist jetzt ein Absatz, der eine
            # Kachel ueber die Kante ragt.
            e1[ry][rx] = "<"
            # Die Kachel am Rand, auf die man vom Absatz tritt, und ihre
            # Nachbarn frei von Fassern - sonst endet die Rampe an einem.
            zx = min(max(rx, x0), x1)
            zy = min(max(ry, y0), y1)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = zx + dx, zy + dy
                    if x0 <= nx <= x1 and y0 <= ny <= y1 and e1[ny][nx] == FASS:
                        e1[ny][nx] = SAND
            # Und unten davor freiraeumen.
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = rx + dx, ry + dy
                    if 0 < nx < B - 1 and 0 < ny < H - 1 and e0[ny][nx] == WAND:
                        if not any(x0 <= nx <= x1 and y0 <= ny <= y1
                                   for q in PLATEAUS
                                   for x0, y0, x1, y1 in (q["kasten"],)):
                            e0[ny][nx] = SAND

    # Gebaeude.
    for geb in GEBAEUDE:
        rechteck(e0, geb["kasten"], WAND, nur_rand=True)
        for (tx, ty) in geb["tueren"]:
            if 0 <= tx < B and 0 <= ty < H:
                e0[ty][tx] = SAND

    # Streugut im freien Feld.
    for (x, y, r) in STREU:
        if e0[y][x] == SAND:
            streuen(e0, x, y, r)

    # Die Kreise.
    for kr in KREISE:
        g = e0 if kr["ebene"] == 0 else e1
        cx, cy = kr["mitte"]
        if kr["ring"]:
            ring(g, cx, cy, kr["ring"])
        # Innen freiraeumen, damit man wirklich darin stehen kann.
        for y in range(cy - 3, cy + 4):
            for x in range(cx - 4, cx + 5):
                if 0 < x < B - 1 and 0 < y < H - 1 and g[y][x] == FASS:
                    g[y][x] = SAND
        g[cy][cx] = kr["zeichen"]

    # Spawnmarken. Zuletzt, damit sie nichts ueberschreibt - und nur
    # dort, wo wirklich Boden ist: eine Marke in einer Wand waere eine
    # Stelle, an der nie etwas herauskommt, und das faellt niemandem auf.
    gesetzt = 0
    for (x, y, ebene) in SPAWNS:
        g = e0 if ebene == 0 else e1
        if not (0 < x < B - 1 and 0 < y < H - 1):
            continue
        if g[y][x] != SAND:
            # Nachbarschaft absuchen, statt die Marke wegzuwerfen.
            for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1),
                             (2, 0), (-2, 0), (0, 2), (0, -2)):
                if 0 < x + dx < B - 1 and 0 < y + dy < H - 1 \
                        and g[y + dy][x + dx] == SAND:
                    x, y = x + dx, y + dy
                    break
            else:
                continue
        g[y][x] = "Z"
        gesetzt += 1
    if gesetzt < len(SPAWNS) * 0.7:
        raise SystemExit("Nur %d von %d Spawnmarken gesetzt - die Liste passt "
                         "nicht mehr zum Grundriss." % (gesetzt, len(SPAWNS)))

    return e0, e1


def schreiben(pfad):
    e0, e1 = bauen()
    kopf = [
        "# STAUBTAL - sehr gross, sehr leer, Wueste mit Wildwest-Einschlag.",
        "#",
        "# Die Ebene ist flach. Was sie gliedert, sind drei Plateaus und",
        "# eine Handvoll Buden - und unter jedem Plateau steht Fels, man",
        "# kommt also nicht darunter, nur hinauf.",
        "#",
        "# Marken: A KESSEL (offener Sand), B DEPOT (in der Halle),",
        "#         C KANZEL (auf dem grossen Plateau).",
        "#         Z ist eine Spawnstelle fuer Gegner - am Fuss der",
        "#         Plateaus, an den Buden, an der Mauer. Im offenen Sand",
        "#         steht keine: dort aus dem Nichts zu erscheinen sieht",
        "#         nach Fehler aus.",
        "",
        "name: STAUBTAL",
        "satz: wueste",
        "kreise: A B C",
        "",
    ]
    teile = ["\n".join(kopf)]
    for i, g in enumerate((e0, e1)):
        # **Nicht rstrippen.** Die Ebenen muessen gleich breit bleiben,
        # sonst ist die obere schmaler als die untere, und alles, was an
        # der Kartengroesse haengt - Kamera, Einstiegsplaetze - rechnet
        # mit zwei verschiedenen Karten.
        zeilen = ["".join(z).ljust(B) for z in g]
        teile.append("--- ebene %d ---\n" % i + "\n".join(zeilen) + "\n")
    Path(pfad).write_text("\n".join(teile), encoding="utf-8")
    return e0, e1


if __name__ == "__main__":
    import sys
    ziel = sys.argv[1] if len(sys.argv) > 1 else "karten/staubtal.txt"
    Path(ziel).parent.mkdir(parents=True, exist_ok=True)
    e0, e1 = schreiben(ziel)
    print("geschrieben:", ziel)
    print("Ebene 0: %d x %d, davon Sand %d" %
          (B, H, sum(z.count(".") for z in ("".join(r) for r in e0))))
    print("Ebene 1: Plateauflaeche %d Kacheln" %
          sum(1 for r in e1 for c in r if c != " "))
