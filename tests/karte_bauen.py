# -*- coding: utf-8 -*-
"""Erzeugt die beiden Etagen und prueft sie, bevor sie in world.py wandern."""
from collections import deque

B, H = 44, 24

def leer(fuellung="."):
    return [[fuellung] * B for _ in range(H)]

def rahmen(g):
    for x in range(B):
        g[0][x] = g[H-1][x] = "#"
    for y in range(H):
        g[y][0] = g[y][B-1] = "#"

def rect(g, x0, y0, w, h, z):
    for y in range(y0, y0+h):
        for x in range(x0, x0+w):
            if 0 <= x < B and 0 <= y < H:
                g[y][x] = z

# ───────────────────────── Ebene 0: Halle mit Saeulen und Deckung
e0 = leer(".")
rahmen(e0)
# Saeulen, 2x2, in lockerem Raster. Sie stehen frei, versperren nichts.
for (px, py) in [(6,4),(14,4),(30,4),(38,4),(6,12),(14,19),(30,19),(38,12),
                 (22,4),(22,19),(6,19),(38,19)]:
    rect(e0, px, py, 2, 2, "#")
# Kurze Mauerstuecke als Sichtbrecher, alle offen an beiden Enden
rect(e0, 10, 8, 7, 1, "#")
rect(e0, 27, 8, 7, 1, "#")
rect(e0, 10, 15, 7, 1, "#")
rect(e0, 27, 15, 7, 1, "#")
rect(e0, 21, 7, 1, 4, "#")
rect(e0, 21, 13, 1, 4, "#")
# Gitterboden als Deko
rect(e0, 3, 9, 5, 6, ",")
rect(e0, 36, 9, 5, 6, ",")
rect(e0, 18, 2, 8, 2, ",")
# Kisten als Deckung, immer frei stehend
for (px, py) in [(9,6),(34,6),(9,17),(34,17),(18,11),(25,12),(12,12),(31,11)]:
    e0[py][px] = "X"
# Treppe nach oben, mitten in der Halle, rundum frei
e0[12][22] = ">"

# ───────────────────────── Ebene 1: Laufstege ueber der Halle
e1 = leer(" ")          # Leerzeichen = Loch, dadurch sieht man Ebene 0
rahmen(e1)
rect(e1, 1, 1, B-2, 3, ".")          # Ring oben
rect(e1, 1, H-4, B-2, 3, ".")        # Ring unten
rect(e1, 1, 1, 3, H-2, ".")          # Ring links
rect(e1, B-4, 1, 3, H-2, ".")        # Ring rechts
rect(e1, 1, 11, B-2, 2, ".")         # Quersteg
rect(e1, 20, 1, 4, H-2, ".")         # Laengssteg
rect(e1, 18, 9, 8, 6, ".")           # Plattform um die Treppe
rect(e1, 19, 10, 6, 4, ",")          # Gitterboden darauf
e1[12][22] = "<"                     # genau ueber der Treppe von Ebene 0
e1[2][40] = "o"                      # Bodenluke, faellt auf Ebene 0
for (px, py) in [(6,2),(37,2),(6,21),(37,21),(2,6),(41,17),(22,5),(22,18)]:
    e1[py][px] = "X"

# ───────────────────────── Pruefung
def begehbar(z):
    return z in (".", ",", "<", ">", "o", "X") and z != "X"

def flut(g, start):
    gesehen = {start}
    q = deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            n = (x+dx, y+dy)
            if n in gesehen: continue
            if 0 <= n[0] < B and 0 <= n[1] < H and begehbar(g[n[1]][n[0]]):
                gesehen.add(n); q.append(n)
    return gesehen

fehler = []
for name, g, treppen in (("E0", e0, [(22,12)]), ("E1", e1, [(22,12),(40,2)])):
    boden = {(x,y) for y in range(H) for x in range(B) if begehbar(g[y][x])}
    start = treppen[0]
    erreicht = flut(g, start)
    fehlend = boden - erreicht
    print("%s: %d begehbare Kacheln, davon %d von der Treppe aus erreichbar"
          % (name, len(boden), len(erreicht)))
    if fehlend:
        fehler.append("%s: %d abgeschnittene Kacheln, z.B. %s"
                      % (name, len(fehlend), sorted(fehlend)[:6]))
    for t in treppen:
        if t not in erreicht:
            fehler.append("%s: Treppe %s nicht erreichbar" % (name, t))
# Landepunkte pruefen
for (x, y), quelle, ziel in (((22,12), e0, e1), ((22,12), e1, e0), ((40,2), e1, e0)):
    if not begehbar(ziel[y][x]):
        fehler.append("Landepunkt (%d,%d) auf der Zielebene ist nicht begehbar" % (x, y))
print("FEHLER:", fehler or "keine")

for name, g in (("KARTE_E0", e0), ("KARTE_E1", e1)):
    print("\n%s = [" % name)
    for zeile in g:
        print('    "%s",' % "".join(zeile))
    print("]")
