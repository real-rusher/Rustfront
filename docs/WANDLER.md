# DUSTFRONT - Der Wandler und sein Gang

**Was das hier ist.** Die Bauanleitung fuer die Laufmaschine: wie sie aus
einer Textdatei entsteht, warum ihre Bewegung wirklich aus den Beinen kommt,
und wo jede Zahl steht. Wer spaeter etwas daran aendert, liest Abschnitt 2
ganz - dort steht die eine Entscheidung, an der alles haengt.

**Stand:** Version 0.20.0, Meilenstein M1 aus `docs/KARTE.md`.

**Zum Ansehen:** `PROBELAUF.bat` (Windows) oder `PROBELAUF.command` (Mac),
oder `python -m dustfront --probe`.

---

## 1. Karten kommen aus Dateien

Bis 0.15.0 gab es genau eine Karte, und sie stand als Liste von
Zeichenketten im Code. Jetzt liegt jede Karte in `karten/` als Textdatei.
Ein neuer Ort - oder ein neuer Wandler - ist damit kein Programmieren mehr,
sondern Tippen.

### 1.1 Das Format

```
name: Probehalle
grund: boden

--- ebene 0 ---
##########
#...S....#
##########

--- ebene 1 ---
##########
#   ..   #
##########
```

| Teil | Bedeutung |
| --- | --- |
| Kopf | `schluessel: wert`, bis zum ersten Trenner. `#` ist dort ein Kommentar. |
| `--- ebene N ---` | leitet einen Ebenenblock ein. Ebene 0 steht zuerst und ist die unterste. |
| Zeilen danach | die Karte. Ein Zeichen ist eine Kachel. |

**Leerzeichen sind Loecher, keine Luft.** Eine Zeile aus lauter Leerzeichen
ist eine Kartenzeile aus lauter Loechern - genau daraus besteht die Spitze
eines Rumpfes. Der Leser schneidet deshalb nur den Zeilenumbruch ab, sonst
nichts. (Das stand schon einmal falsch darin, siehe Abschnitt 6.)

### 1.2 Zeichen

Im Kopf entscheidet `grund:`, welche Kachelfamilie gilt. Die Zeichen sind in
beiden Faellen dieselben - ein Deck tippt sich wie ein Stueck Wasteland, es
sieht nur anders aus.

| Zeichen | `grund: boden` | `grund: deck` |
| --- | --- | --- |
| `.` | Boden | Deckplatte |
| `,` | Gitter | Laufrost |
| `#` | Wand | Schott |
| `X` | Frachtkasten | Frachtkasten |
| ` ` | Loch | Loch |
| `<` `>` | Treppe runter, hoch | dasselbe |
| `o` | Luke | Luke |

### 1.3 Marken

Grossbuchstaben und Ziffern werden zu einer Kachel **und** legen ihre
Position unter einem Namen ab. Damit muss kein Code mehr wissen, wo etwas
liegt - es steht in der Karte.

| | | | | | |
| --- | --- | --- | --- | --- | --- |
| `S` start | `R` rampe | `T` steuerstand | `G` geschuetz | `E` reaktor | `W` werkbank |
| `K` kartentisch | `F` funk | `M` modulschacht | `A` antrieb | `Y` werkstatt | `L` lager |
| `B` koje | `1`-`9` punkt1 bis punkt9 | | | | |

Der Spieler startet auf `S`. Vorher war es ein Zufallspunkt.

### 1.4 Der Pruefer

`karten.pruefen()` und `karten.pruefen_welt()` beantworten drei Fragen, und
alle drei sind schon einmal falsch beantwortet worden, als Karten noch von
Hand gezaehlt wurden:

1. **Fluchten die Treppen?** Eine Treppe nach oben ist wertlos, wenn auf der
   Zielebene an derselben Stelle eine Wand oder ein Loch steht.
2. **Kommt man ueberall hin?** Von der Startmarke aus muss jede Ebene
   erreichbar sein - notfalls durch ein Loch, denn hindurchfallen zaehlt.
3. **Steht der Start im Freien?**

Der Testlauf laedt jede Datei im Ordner und verlangt, dass nichts
herauskommt. Eine kaputte Karte faellt damit im Test auf und nicht beim
Spielen.

### 1.5 Wenn eine Datei fehlt

`world.karte_laden()` faellt auf die eingebaute `testkarte()` zurueck und
schreibt den Grund auf die Konsole. Ein Spiel darf an einer fehlenden Datei
nicht sterben.

---

## 2. Die Bewegung kommt aus den Beinen

**Das ist der wichtigste Abschnitt.** Wer ihn ueberspringt, baut das
Uebliche.

### 2.1 Was fast alle machen, und warum es falsch aussieht

Der Rumpf bekommt eine Geschwindigkeit und faehrt los, und die Beine
bekommen hinterher eine Animation, die ungefaehr dazu passt. Das sieht man
sofort: der Rumpf gleitet, die Fuesse schlittern ueber den Boden, und nichts
an der Bewegung hat eine Ursache.

### 2.2 Was hier stattdessen steht

> **Der Rumpf hat keine eigene Geschwindigkeit.**
> Er wird von den Fuessen getragen, die gerade am Boden stehen.

Ein stehender Fuss ist in der **Welt** verankert und bewegt sich nicht -
nicht ein Pixel, nicht ein Tausendstel. Was den Rumpf vorwaerts bringt, ist
allein der Umstand, dass ein Fuss beim Schritt **vor** seiner Ruhelage
aufsetzt. Danach zieht der Rumpf zu seinen Fuessen hin und steht ein Stueck
weiter vorn als zuvor.

### 2.3 Wie der Rumpf gerechnet wird

Jedes Bein hat eine **Ruhelage** im Rumpfkoordinatensystem: dort steht sein
Fuss, wenn die Maschine haelt. Stehen die Fuesse woanders, wird die Lage und
Drehung gesucht, die am besten dazu passt - eine Ausgleichsrechnung, in zwei
Dimensionen ein Dreizeiler:

```
    theta = atan2( Summe(r_i kreuz f_i), Summe(r_i mal f_i) )
    mitte = Mittel(f_i) - dreh(Mittel(r_i), theta)
```

`r_i` ist die um den Mittelwert bereinigte Ruhelage des Beins i, `f_i` seine
wirkliche Fussstellung. Heraus kommt **genau eine Lage und genau ein Kurs**.
Beides zieht der Rumpf weich nach (`koerper_zug`, `kurs_zug`), damit es
mechanisch wirkt statt mathematisch.

Bei nur **einem** Standbein ist die Drehung unbestimmt - dann bleibt der
Kurs, wie er ist, und nur die Lage folgt. Daraus faellt die Eigenart der
zweibeinigen Maschinen an, siehe 3.3.

### 2.4 Was daraus von selbst folgt

Keines der folgenden Verhalten steht als Sonderfall im Code. Alle sind im
Testlauf nachgewiesen.

| Verhalten | Warum es anfaellt |
| --- | --- |
| **Tempo ist ein Ergebnis, kein Sollwert.** Gemessen: 54 von 54 px/s beim Reaver. | Der Rumpf kommt je Gangzyklus eine Schrittweite voran. |
| **Ein stehender Fuss rutscht nie.** Gemessen: 0.000000000 px ueber 8 Sekunden. | Er ist der Anker, nicht das Ergebnis. |
| **Stillstand ist Stillstand.** Gemessen: 0.0000 px ueber 6 Sekunden. | Die Fuesse sind verankert, also ist der Rumpf es auch. |
| **Ein zerstoertes Bein wirkt sofort:** der Rumpf haengt schief, die Maschine wird langsamer. | Es traegt nicht mehr, also kippt der Schwerpunkt der Standfuesse. |
| **Mit einem einzigen Bein geht gar nichts.** Gemessen: 0.00 px/s. | Ein Fuss kann nicht tragen und treten zugleich. |
| **Ein Imperator vertraegt drei verlorene Beine, ein Warhound keines.** | Sechs Beine haben Reserve, zwei nicht. |

### 2.5 Die Regelung der Schrittweite

Grundgedanke: der Rumpf kommt je Zyklus rund eine Schrittweite voran, also
ist `tempo * zyklus` der richtige Ansatz. **Genau** stimmt das nicht - wie
viel ankommt, haengt daran, wie viele Fuesse gerade tragen und wie alt ihre
Standpunkte sind. Ohne Korrektur lief ein Reaver 32 Prozent zu schnell.

Deshalb misst die Maschine ihr eigenes Tempo und greift entsprechend weiter
oder kuerzer. Das ist nicht nur robuster, es ist richtiger: faellt ein Bein
aus oder zieht die Ueberlast an, regelt sie nach, ohne dass dafuer irgendwo
ein Sonderfall steht. Ein Laeufer macht es genauso.

### 2.6 Gangarten ohne Tabelle

Welches Bein in welche Gruppe gehoert, wird aus der Bauart abgeleitet: je
Seite von vorn nach hinten abwechselnd, die rechte Seite um eins versetzt.

| Beine | Ergibt | Das ist |
| --- | --- | --- |
| 2 | 0 / 1 | Wechselschritt |
| 4 | vorn links mit hinten rechts | Kreuzgang |
| 6 | vorn links, mitte rechts, hinten links | Dreifuss |

Also genau die Gangarten, die echte Laeufer benutzen - fuer jede Beinzahl,
ohne eine eigene Tabelle. Im Testlauf nachgewiesen.

### 2.7 Die harte Bedingung

**Es bleiben immer `stand_mindest` Fuesse am Boden.** Keine Ausnahme. Ohne
diese Zeile huepft eine Maschine auf ihrem letzten Bein davon - und zwar
schneller als mit vieren, weil jeder Hupfer den ganzen Rumpf mitnimmt. Das
ist im Bauen tatsaechlich passiert.

---

## 3. Der Wandler als Datei

### 3.1 Was drinsteht

Nichts an einer bestimmten Maschine steht im Code. `karten/wandler/reaver.txt`
ist der Reaver: seine Decks als Text, seine Beine als Zeilen, seine Klasse
als Wort.

```
name: Reaver
art: wandler
klasse: reaver
grund: deck

bein: -3.4 -4.6 links
bein: -3.4  4.6 rechts
bein:  3.4 -4.6 links
bein:  3.4  4.6 rechts

--- ebene 0 ---
...
```

`bein: <huefte_x> <huefte_y> <knieseite> [fuss_x fuss_y]`, in Kacheln von
der Rumpfmitte aus. Fehlt die Ruhelage des Fusses, wird sie aus der
Beinreichweite gerechnet: ueberwiegend nach aussen, ein Viertel in
Laengsrichtung. Vordere Beine spreizen dadurch nach vorn, hintere nach
hinten - eine Maschine, die steht, statt eines Tisches.

Jede Zeile aus `K.WANDLER_KLASSEN` laesst sich in der Datei ueberschreiben
(`tempo:`, `dreh:`, `takt:`, `bein_ober:` und so weiter). Die Datei gewinnt
immer.

### 3.2 Die drei Klassen

| Klasse | Beine | Decks | Tempo | Spielgefuehl |
| --- | --- | --- | --- | --- |
| **Warhound** | 2 | 3 | 78 | schnell, wendig in der Fahrt, wankt sichtbar. Ein verlorenes Bein ist das Ende. |
| **Reaver** | 4 | 4 | 54 | der Standard. Ruhig, dreht auf dem Absatz, vertraegt ein Bein. |
| **Imperator** | 6 | 6 | 33 | laufende Festung. Vertraegt drei Beine, passt nicht auf den Bildschirm, und ein Mensch bedient acht Geschuetze nicht. |

### 3.3 Der Klassenunterschied faellt umsonst an

Keine dieser Eigenschaften ist eingebaut:

* **Der Imperator ist zaeh**, weil sechs Beine Reserve haben.
* **Der Warhound ist schnell**, weil kurze Beine schneller takten.
* **Der Warhound schlurft beim Drehen auf der Stelle** (gemessen 217 px
  gegen 26 px beim Reaver), weil dann genau ein Fuss steht - und ein
  einzelner Fuss legt keine Drehung fest (2.3). Ein Warhound muss sich
  herumtreten, ein Reaver dreht auf dem Absatz.
* **Groesse kostet Anwesenheit**: mehr Decks heisst laengere Wege zwischen
  den Stationen. Das ist der Hebel fuer den Autopiloten aus `docs/KARTE.md`,
  Abschnitt 6.3 - und er steht damit schon bereit.

### 3.4 Der Rumpf ist eine ganz normale Welt

Seine Decks sind `Ebene`n, seine Kollision ist dieselbe, seine Treppen sind
dieselben. Wer an Bord laeuft, laeuft in einer gewoehnlichen Welt - dass sie
sich durch die Wueste bewegt, faellt dabei nicht auf, denn an Bord ist der
Rumpf der ruhende Bezugsrahmen.

Was sich bewegt, ist **eine Zahl**: `welt.versatz`. Sie ist eine Kommazahl,
nie ein Kachelmass, damit sich kein Gitter je gegen sein eigenes Raster
verschiebt. `wandler.nach_welt()` und `wandler.nach_rumpf()` rechnen
zwischen beiden um - zwei Funktionen, eine Drehung, eine Verschiebung. Im
Testlauf wird geprueft, dass Hin- und Rueckrechnung wieder denselben Punkt
trifft.

### 3.5 Beliebig viele Decks

`EBENEN_HOEHE` wird im ganzen Spiel an **genau einer** Stelle gelesen, in
`Welt.hoehe()`. Alles andere ruft diese Methode. Deshalb kann jeder Rumpf
seine eigene Hoehenstaffel haben, und `world.hoehen_staffel(decks)` erzeugt
sie:

```
    hoehe(n) = brennweite * (schritt**-n - 1)      schritt = 0.895
```

Die von Hand gesetzte Tabelle kodiert einen gleichbleibenden
Wahrnehmungsschritt: jedes Deck erscheint 89,5 Prozent so gross wie das
darueber, nur der Boden sitzt bewusst tiefer. Die erzeugte Staffel trifft
die alte auf 1,4 Pixel genau - im Testlauf nachgewiesen - und gilt fuer
jede Deckzahl bis zwoelf.

---

## 4. Aussehen

### 4.1 Von aussen: ein Panzeraufbau, kein Grundriss

Der erste Anlauf zeichnete von aussen einfach das oberste Deck. Das war
sichtbar falsch - man sieht nicht den Fussboden der Bruecke, sondern das
Blech darueber, und die Maschine sah aus wie ein aufgeklappter Bauplan.

Gebaut wird stattdessen **jedes Deck einzeln, von unten nach oben**: das
unterste ist das groesste und dunkelste, jedes weitere kleiner und eine Spur
heller, jedes mit eigener Lichtkante. Erst die Staffelung dieser Kanten
macht aus einer Flaeche einen Aufbau.

Dazu kommen Warnwinkel am Bug - ohne sie sieht man einem Umriss nicht an,
wohin er laeuft - und die Aufbauten an den Marken des obersten Decks:
Geschuetze, wo `G` steht, die Kanzel, wo `T` steht. **Wer die Karte aendert,
aendert damit auch das Aussehen von aussen**, ohne eine Zeile Code.

Ausgerichtet werden die Decks an dem, was wirklich belegt ist, nicht an der
Arraygroesse: beim Schreiben einer Karte fallen Leerzeichen am Zeilenende
weg, und ein Deck mit mehr Loechern rechts kaeme sonst schmaler heraus - der
ganze Aufbau saesse schief.

### 4.2 Die Beine

Vier Bilder, alle austauschbar: `bein_ober`, `bein_unter`, `bein_fuss`,
`bein_huefte`. Sie liegen nach rechts und werden um ihre Mitte gedreht,
genau wie jede Figur. Das Mass in `BILD_MASS` ist ein **Grundmass** - eine
Bauklasse mit anderen Beinlaengen bekommt es hart umgerechnet, Pixel fuer
Pixel, ohne Weichzeichnen.

Das Knie kommt aus einer Zweikreis-Schnittrechnung; `knieseite` waehlt,
welcher der beiden Schnittpunkte genommen wird, also ob das Knie nach aussen
oder innen ausbricht. Nie ganz durchgestreckt und nie ganz zusammengelegt,
sonst springt es zwischen den Loesungen hin und her.

**Der Hub liest sich nur mit Schatten.** Beine werden in zwei Durchgaengen
gezeichnet: erst alle Schatten auf Bodenhoehe, ohne Hub, dann die Glieder
mit Hub nach oben versetzt und eine Spur heller. Erst die Luecke zwischen
Schatten und Bein ergibt Hoehe - ohne den Schatten schiebt sich ein Bein
bloss nach oben, und niemand sieht, dass es abhebt.

### 4.3 Kacheln und Klaenge

Neu und alle durch eine Datei ersetzbar: `deck` bis `deck_4`,
`deck_gitter`, `rumpfwand`, `rampe`, `modulschacht`, `antrieb`, `lager`,
`koje` und sieben Stationsbilder. Dazu die Klaenge `schritt`, `servo`,
`rumpf_stoss`, `station_an`, `station_aus`.

`python -m dustfront --vorlagen` schreibt von jedem Bild eine masshaltige
Vorlage heraus - seit 0.20.0 sind das 58 statt 36.

Der **Schritt** ist der wichtigste Klang im Spiel: er macht aus einer
Bewegung einen Vorgang. Drei Lagen - ein tiefer Stoss (die Masse), kurzes
helles Scheppern (das Blech), ausklingendes Rauschen (der Staub). Ohne die
tiefe Lage klingt es nach Schritt, nicht nach Maschine; ohne die helle nach
Sack, nicht nach Stahl.

---

## 5. Wo welche Zahl steht

Alles in `dustfront/config.py`, nirgends sonst.

| Tabelle | Wofuer |
| --- | --- |
| `KARTEN` | Ordner, Trenner, welche Karte startet |
| `ZEICHEN_BODEN`, `ZEICHEN_DECK`, `MARKEN` | was ein Zeichen bedeutet |
| `KACHELN_RUMPF`, `STATIONEN` | die Rumpfkacheln und ihre Stationen |
| `WANDLER` | Fahrt, Nachziehen des Rumpfes, Wanken, Atem |
| `GANG` | Takt, Schrittweite, Hub, Regelung, Mindeststand |
| `BEIN` | Laengen, Dicken, Knie, Schatten |
| `WANDLER_KLASSEN` | was eine Bauklasse bedeutet |
| `WANDLER_BILD` | Aussenansicht: Helligkeit, Stufen, Bug, Zoom |
| `HOEHEN` | Wahrnehmungsschritt der Hoehenstaffel |

---

## 6. Fehler, die beim Bauen aufgetreten sind

Fuer den naechsten, der hier weitermacht - und fuer mich selbst, falls ich
es noch einmal baue.

**6.1 Zeilen aus lauter Loechern wurden weggeworfen.** Mein Kartenleser
warf "Leerzeilen" weg und hielt eine Zeile aus Leerzeichen dafuer. Genau
daraus besteht aber die Spitze eines Rumpfes. Ergebnis: jede geformte Karte
verrutschte um mehrere Zeilen, und die Treppen fluchteten nicht mehr. Weg
darf nur, was Laenge null hat.

**6.2 Auf einem Bein davongehuepft.** Mit einer weichen Bedingung fuer den
Mindeststand durfte das letzte Bein treten. Dann trug nichts mehr, der Rumpf
sprang beim Aufsetzen mit - und die Maschine war auf einem Bein *schneller*
als auf vieren (70 statt 54 px/s). Die Bedingung muss hart sein.

**6.3 Tempo 32 Prozent zu hoch.** Die Schrittweite `tempo * zyklus`
ausgerechnet und geglaubt. Wie viel je Zyklus wirklich ankommt, haengt aber
daran, wie alt die Standpunkte der tragenden Fuesse sind. Geregelt statt
gerechnet, siehe 2.5.

**6.4 Von aussen ein Grundriss statt einer Maschine.** Siehe 4.1.

**6.5 Der Aufbau sass schief.** Decks nach Arraygroesse zentriert, aber
beim Schreiben fallen Leerzeichen am Zeilenende weg. Nach belegtem Bereich
ausrichten.

**6.6 Beine unsichtbar unter dem Rumpf.** Die Hueften sassen nahe der
Rumpfmitte, also lagen die Beine von oben gesehen vollstaendig unter dem
Rumpf. Physisch nicht falsch, spielerisch wertlos. Hueften an den
Rumpfrand: die Fuesse stehen jetzt 50 bis 90 Pixel ausserhalb.

**6.7 Beinglieder wie Lineale.** Gleichmaessig helle Balken ohne Querschnitt
sehen aus wie Rohre. Jede Spalte einzeln schattieren, von der Lichtkante
oben zur Schattenkante unten.

**6.8 Rampe wie ein Absperrband.** Ganzflaechige Warnstreifen schreien
lauter als alles andere auf dem Bildschirm. Schmales Band am Rand, und die
Abnutzung **zuletzt** darueber - sonst leuchten die Trittleisten ueber dem
Schmutz statt darunter.

**6.9 Deckmuster als Wellen.** Lange schraege Rippen legen sich zu einem
Wellenmuster zusammen. Kleine Stollen im festen Raster statt langer Rippen,
und kein Zufallsversatz: gefertigte Flaechen sind regelmaessig, und jeder
Wackler daran sieht nach Schmutz aus statt nach Blech.

**6.10 Kamera an GAME_W festgenagelt.** Die Aussenansicht zeichnet auf eine
groessere Flaeche und verkleinert sie danach. `Kamera.ecke` rechnete aber
fest mit der Bildgroesse, also sass die Maschine in der Ecke. Die Kamera
kennt jetzt ihre Sichtflaeche.

---

## 7. Was als Naechstes ansteht

Nach `docs/KARTE.md`, Abschnitt 13:

**M2 - Der Wandler als begehbarer Rumpf (0.21.0).** Die Decks sind gebaut,
die Stationen stehen, die Hoehenstaffel ist da. Was fehlt: hineingehen. Der
Spieler muss auf dem Deck laufen, Treppen benutzen, ueber die Rampe hinaus
und ueber die Kante fallen koennen.

**Der Front-Pruefpunkt aus Abschnitt 9.4 gilt ab M2:** der Wandler-Zustand
gehoert in ein Objekt, das die Szene **bekommt**, nicht anlegt. `Wandler`
ist bereits so gebaut - er nimmt einen `Bauplan` entgegen und haelt seinen
eigenen Zustand. Das bleibt so.
