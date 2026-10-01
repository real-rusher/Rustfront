"""Erzeugt die Karte LOBBY.

Der Ort, an dem man beim Aufmachen landet und nach jeder Runde wieder.
Er soll drei Dinge koennen, nebeneinander und ohne sich zu stoeren:

* **Herumstehen.** Der Platz in der Mitte. Hier tut niemandem etwas weh,
  hier wartet man, waehrend der Gastgeber die Runde einstellt.
* **Ueben.** Oben am Platz der Schiessstand: Puppen, die Treffer zaehlen
  und nicht umfallen. Man probiert eine Waffe aus, ohne jemanden zu
  stoeren.
* **Sich schon mal aufwaermen.** Links die Arena fuer PVP, rechts das
  Gehege mit Zombies fuer PVE. Beide durch eine Mauer mit zwei Toren vom
  Platz getrennt - man geht bewusst hinein.

Die Bereiche stehen als Rechtecke im Kopf der Datei (bereich_pvp,
bereich_stand, bereich_pve), in Kacheln und einschliesslich. Das Spiel
liest sie von dort und malt sie auf den Boden - wer die Karte von Hand
aendert, aendert auch die Bereiche an derselben Stelle.

Marken: S Einstiegsplatz (auf dem Platz), D Zielpuppe, Z Spawnstelle im
Gehege.

Die erzeugte Datei ist danach ganz normaler Text und von Hand
weiterzubearbeiten - dieses Werkzeug setzt nur den ersten Stand.
"""
from pathlib import Path

B, H = 60, 34           # Kacheln. Bei 32 Pixeln sind das 1920 x 1088.

BODEN, WAND, KISTE = ".", "#", "X"

# Die drei Bereiche, (x0, y0, x1, y1) einschliesslich. Die Trennmauern
# stehen bei x = 21 und x = 38, der Platz liegt dazwischen.
PVP = (1, 1, 20, 32)
STAND = (22, 1, 37, 9)
PVE = (39, 1, 58, 32)
MAUERN = (21, 38)
TORE = ((7, 9), (24, 26))       # je Mauer zwei, von y bis y


def gitter():
    return [[BODEN] * B for _ in range(H)]


def rechteck(g, kasten, zeichen, nur_rand=False):
    x0, y0, x1, y1 = kasten
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if not (0 <= x < B and 0 <= y < H):
                continue
            if nur_rand and not (x in (x0, x1) or y in (y0, y1)):
                continue
            g[y][x] = zeichen


def spiegeln(g, punkte, zeichen, mitte_x):
    """Deckung links und rechts gleich: eine Arena, in der eine Seite
    besser ist, ist keine."""
    for (x, y) in punkte:
        g[y][x] = zeichen
        g[y][int(2 * mitte_x - x)] = zeichen


def bauen():
    g = gitter()
    rechteck(g, (0, 0, B - 1, H - 1), WAND, nur_rand=True)

    # Die beiden Trennmauern, jede mit zwei Toren.
    for mx in MAUERN:
        for y in range(1, H - 1):
            if any(a <= y <= b for (a, b) in TORE):
                continue
            g[y][mx] = WAND

    # PVP: Deckung, gespiegelt um die Mitte der Arena. Ein Riegel in der
    # Mitte, vier Kistengruppen, zwei Mauerwinkel an den Enden.
    mitte = (PVP[0] + PVP[2]) / 2.0
    spiegeln(g, [(4, 6), (5, 6), (4, 7),
                 (4, 26), (5, 26), (4, 25),
                 (7, 14), (7, 15), (7, 18), (7, 19)], KISTE, mitte)
    for x in range(8, 14):
        g[16][x] = WAND
    spiegeln(g, [(3, 12), (3, 13), (3, 20), (3, 21)], WAND, mitte)

    # Der Schiessstand: vier Puppen in einer Reihe, dahinter die Mauer.
    # Zwei Kisten an den Seiten fassen ihn ein, damit man sieht, wo er
    # aufhoert und der Platz anfaengt.
    for x in (25, 28, 31, 34):
        g[3][x] = "D"
    for y in (2, 3, 4):
        g[y][22] = KISTE
        g[y][37] = KISTE

    # Der Platz: acht Einstiegsplaetze um die Mitte, ein paar Kisten
    # an den Raendern zum Anlehnen.
    for (x, y) in ((26, 18), (29, 17), (33, 18), (25, 22), (34, 22),
                   (27, 26), (30, 27), (33, 26)):
        g[y][x] = "S"
    for (x, y) in ((23, 30), (24, 30), (36, 30), (35, 30), (23, 14),
                   (36, 14)):
        g[y][x] = KISTE

    # Das Gehege: Pfeiler zum Umlaufen und Spawnstellen am hinteren Ende.
    for (x, y) in ((44, 8), (44, 9), (53, 8), (53, 9),
                   (44, 24), (44, 25), (53, 24), (53, 25)):
        g[y][x] = WAND
    for (x, y) in ((48, 15), (49, 15), (48, 18), (49, 18)):
        g[y][x] = KISTE
    for (x, y) in ((57, 4), (57, 16), (57, 29), (51, 3), (51, 30)):
        g[y][x] = "Z"
    return g


def schreiben(pfad):
    g = bauen()
    kopf = [
        "# LOBBY - der Ort vor und zwischen den Runden.",
        "#",
        "# Links die Arena (PVP), in der Mitte der Platz mit dem",
        "# Schiessstand, rechts das Gehege mit Zombies (PVE). Ausserhalb",
        "# der Arena und des Geheges tut niemandem etwas weh.",
        "#",
        "# Bereiche: x0 y0 x1 y1 in Kacheln, einschliesslich.",
        "# Marken: S Einstieg, D Zielpuppe, Z Spawnstelle im Gehege.",
        "",
        "name: LOBBY",
        "bereich_pvp: %d %d %d %d" % PVP,
        "bereich_stand: %d %d %d %d" % STAND,
        "bereich_pve: %d %d %d %d" % PVE,
        "",
    ]
    zeilen = ["".join(z) for z in g]
    teile = ["\n".join(kopf), "--- ebene 0 ---\n" + "\n".join(zeilen) + "\n"]
    Path(pfad).write_text("\n".join(teile), encoding="utf-8")
    return g


if __name__ == "__main__":
    import sys
    ziel = sys.argv[1] if len(sys.argv) > 1 else "karten/lobby.txt"
    Path(ziel).parent.mkdir(parents=True, exist_ok=True)
    g = schreiben(ziel)
    print("geschrieben:", ziel)
    print("%d x %d Kacheln, %d Puppen, %d Einstiege, %d Spawnstellen" % (
        B, H, sum(r.count("D") for r in g), sum(r.count("S") for r in g),
        sum(r.count("Z") for r in g)))
