# Entfernter Code, der noch einmal nützlich sein könnte

Seit 0.34.150 ist toter Code aus dem Spiel entfernt (gewünscht: „Toten Code
gerne entfernen, wenn er noch mal nützlich sein könnte, dann Teile davon
dokumentieren"). Gefunden mit `vulture` und von Hand nachgeprüft: nichts
davon wurde irgendwo aufgerufen, auch nicht über Namen in `wesen/*.txt`
oder Dekoratoren. Was nur eine Zeile war oder nichts Eigenes konnte
(`core.mische`, `core.winkel_zu`, `world.fest_an`, `trupp.trupp_von`,
`klassen.faehigkeiten_schritt`, `schlacht._welt_zu_karte`,
`render.rueckmeldung_zeichnen`, die Properties `kanone_rest`,
`kugel_anteil` und `konto.beschaeftigt`), steht hier nicht - die alten
Fassungen findet man mit `git log -S name`.

Was hier steht, war fertig und getestet, wurde nur nicht mehr gebraucht.

## Weiches Zufallsgitter (Value Noise) – war `entities._gitterwert`

Benachbarte Stellen bekommen ähnliche Werte, daraus werden
zusammenhängende Ballen statt Rauschen. Zwischen den Gitterpunkten mit
einer S-Kurve überblendet, nicht linear - sonst sieht man die Maschen als
Rauten. Der Rauch rechnet dasselbe inzwischen inline und schneller
(`entities.py`, `_zufall` steht noch da). Brauchbar für Geländeflecken,
Wolkenschatten, Verteilungen auf Karten.

```python
def _gitterwert(x: float, y: float, masche: float, saat: int) -> float:
    gx, gy = x / masche, y / masche
    ix, iy = math.floor(gx), math.floor(gy)
    fx, fy = gx - ix, gy - iy
    sx = fx * fx * (3.0 - 2.0 * fx)
    sy = fy * fy * (3.0 - 2.0 * fy)
    a = _zufall(ix, iy, saat)
    b = _zufall(ix + 1, iy, saat)
    c = _zufall(ix, iy + 1, saat)
    d = _zufall(ix + 1, iy + 1, saat)
    oben = a + (b - a) * sx
    unten = c + (d - c) * sx
    return oben + (unten - oben) * sy
```

## Dichte des Rauchs an einer Weltstelle – war `Rauch.dichte_bei`

Liest das Dichtefeld einer Rauchwolke an einem Punkt ab. Gedacht dafür,
dass Bots oder Treffer „wie dicht ist es hier" fragen statt nur „deckt der
Rauch". Wer das baut: `feld(korn)` liefert das Raster.

```python
def dichte_bei(self, x: float, y: float) -> float:
    korn = max(1, int(K.RAUCH["korn"]))
    breite, x0, y0, werte = self.feld(korn)
    gx = int((x - x0) // korn)
    gy = int((y - y0) // korn)
    if not (0 <= gx < breite and 0 <= gy < breite):
        return 0.0
    return werte[gy * breite + gx]
```

## Kamera-Ecke ohne Ruckeln – war `Renderer.ecke_ruhig`

Der Gedanke ist wichtiger als die eine Zeile: Eingaben (Zielpunkt, damit
Schusswinkel und Wurfweite) werden über die Ecke **ohne** Bildwackeln
umgerechnet - sonst ändert sich das Ziel mit jedem Zittern des Bildes, und
ein Wurf geht woandershin, obwohl man stillhält. Das Ruckeln gehört ins
Bild, nicht in die Hand. Heute geschieht das an der Stelle, die umrechnet.

```python
@property
def ecke_ruhig(self) -> pygame.Vector2:
    return self._ecke_bei(0.0, 0.0)
```

## Trifft ein Punkt eine stehende Kachel? – war `Renderer._stehend_an`

Die Maße einer stehenden Kachel (Mauer, Fels, Baum) am Weltpunkt, wenn er
in ihrer Grundfläche liegt; bei runden Kacheln im Kreis. Wurde durch eine
schnellere Abtastung ohne Nachschlagen ersetzt (`render.py`, „Dieselbe
Abtastung wie mit _stehend_an").

```python
def _stehend_an(self, welt, e, x: float, y: float):
    T = K.TILE
    tx, ty = int(x // T), int(y // T)
    daten = K.KACHELN[e.kachel(tx, ty)]
    if not daten["fest"]:
        return None
    satz = self.SAETZE.get(getattr(welt, "satz", ""), {})
    st = self._stehend(satz.get(daten["bild"], daten["bild"]), daten)
    if st is None:
        return None
    rx, ry, rb, rh = st["rahmen"]
    lx, ly = x - tx * T - rx, y - ty * T - ry
    if not (0 <= lx < rb and 0 <= ly < rh):
        return None
    if st["form"] == "rund":
        mx, my = rb / 2.0, rh / 2.0
        if (lx - mx) ** 2 + (ly - my) ** 2 > mx * mx:
            return None
    return st
```

## 3D-Zeichner: Kegelstumpf und Skalieren – war `drei_d.stumpf`, `drei_d.skalieren`

`drei_d.py` kann weiter Platte, Quader und Zylinder. Der Kegelstumpf
(Rohre, die sich verjüngen: Mündungen, Raketen, Schornsteine) und das
Skalieren eines ganzen Körpers wurden nirgends benutzt.

```python
def stumpf(x0, x1, r0, r1, farbe, n=12, kappe0=True, kappe1=True, y=0.0, z=0.0, glanz=False) -> list:
    """Ein Kegelstumpf entlang x: Radius r0 bei x0, r1 bei x1 (gleich: Zylinder)."""
    raus = []
    neigung = (r0 - r1) / max(1e-6, (x1 - x0))
    for i in range(n):
        a0 = 2 * math.pi * i / n
        a1 = 2 * math.pi * (i + 1) / n
        am = (a0 + a1) / 2
        p = [(x0, y + math.cos(a0) * r0, z + math.sin(a0) * r0),
             (x1, y + math.cos(a0) * r1, z + math.sin(a0) * r1),
             (x1, y + math.cos(a1) * r1, z + math.sin(a1) * r1),
             (x0, y + math.cos(a1) * r0, z + math.sin(a1) * r0)]
        nx = neigung
        ny, nz = math.cos(am), math.sin(am)
        lang = math.sqrt(nx * nx + ny * ny + nz * nz)
        raus.append(Flaeche(p, (nx / lang, ny / lang, nz / lang), farbe, glanz=glanz))
    if kappe0 and r0 > 0.01:
        raus.append(Flaeche([(x0, y + math.cos(2 * math.pi * i / n) * r0, z + math.sin(2 * math.pi * i / n) * r0)
                             for i in range(n)], (-1, 0, 0), farbe))
    if kappe1 and r1 > 0.01:
        raus.append(Flaeche([(x1, y + math.cos(2 * math.pi * i / n) * r1, z + math.sin(2 * math.pi * i / n) * r1)
                             for i in range(n)], (1, 0, 0), farbe))
    return raus


def skalieren(flaechen, f: float) -> list:
    return [Flaeche([(p[0] * f, p[1] * f, p[2] * f) for p in x.punkte], x.normale, x.farbe,
                    x.beidseitig, x.glanz, x.ton) for x in flaechen]
```

## SCHLACHT: Fahrzeuge an die Basis – war `Gefecht._basis_fahrzeuge_aufstellen`

Stellte zu Beginn jeder Seite die Fahrzeuge aus `K.basis_wagen` an die
Basis. Heute kommen sie über die Dropzonen (`schlacht.py`). Wer wieder
feste Startfahrzeuge will:

```python
def _basis_fahrzeuge_aufstellen(self) -> None:
    for team in range(2):
        for art, anzahl in K.basis_wagen(min(3, self.freischalt_stufe())):
            for _ in range(anzahl):
                self._basis_fahrzeug(art, team)
```

## Eigener Wagen beim Gast über den Ort – war die erste Fassung von `Gefecht._mein_wagen`

`_mein_wagen` stand zweimal in `Gefecht`; gegolten hat immer nur die
zweite (über `fahrer_nummer`). Die erste suchte beim Gast den Wagen, der
genau an der eigenen Stelle steht - falls die Meldung einmal keine
Fahrernummer hat:

```python
for b in self.fahrzeuge:
    if b.ebene == ich.ebene and b.pos.distance_squared_to(ich.pos) < 9.0:
        return b
```
