# Balance-Vorschlaege (Stand 0.34.147, noch nicht eingebaut)

Gesammelt fuer den Besitzer, der entscheidet, was hineinkommt. **Nichts
davon ist umgesetzt.** Wer einen Punkt einbaut, streicht ihn hier oder
schreibt die Version dazu, und traegt die neuen Werte in
`docs/BALANCING.md` ein.

Die Kuerzel (W1, F3, N1 ...) sind zum Auswaehlen gedacht. ★ heisst: zuerst
nehmen, wenn es nur wenig auf einmal sein soll.

## Messungen

Gemessen im Testmodus (STAUBTAL OFFEN), Werte aus `dustfront/config.py`.

### Infanteriewaffen gegen eine stehende Figur (100 Leben)

Sekunden ab dem ersten Abzug, bis sie liegt. Median aus 3 Laeufen, "-" =
nicht in 8 s. Zielen (rechte Maustaste) bei Scharfschuetzen-,
Praezisionsgewehr und Panzerbuechse.

| Waffe | 80 px | 200 px | 400 px | 700 px |
| --- | --- | --- | --- | --- |
| **Praezisionsgewehr** | 0,62 | 0,78 | **1,02** | **1,67** |
| **Spiegellaser** | 1,32 | 1,48 | 1,76 | **2,18** |
| Repetierer | 0,64 | 0,86 | 1,22 | - |
| Revolver | 0,89 | 1,09 | 1,43 | - |
| Sturmgewehr | 0,70 | 1,17 | **5,95** | - |
| LMG | 1,17 | 1,64 | 2,38 | 3,16 |
| Scharfschuetzengewehr | 1,30 | 1,43 | 2,88 | 3,20 |
| Unterhebel | 1,58 | 1,79 | 2,14 | - |
| Zwillinge | 1,20 | 1,41 | 1,98 | - |
| Nagler | 0,95 | 1,39 | 2,30 | - |
| Minigun | 1,71 | 2,38 | 3,79 | - |
| MP | 0,84 | 1,27 | - | - |
| Schrot | 0,78 | 1,06 | - | - |
| Autoschrot | 0,76 | 1,46 | - | - |
| Doppelflinte | 0,39 | 0,66 | - | - |
| Flammenwerfer | 1,34 | - | - | - |
| Kettenblitz | 1,88 | 1,88 | - | - |
| Kugelblitz | 2,20 | 3,17 | 4,84 | - |
| Panzerbuechse | 4,09 | 4,19 | 4,36 | 4,61 |
| **Einwegwerfer** | 0,15 | 0,48 | 1,04 | 1,88 |
| Granatwerfer | 3,54 | 3,52 | 4,12 | - |
| Raketenbuendel | 5,5 | 6,4 | 6,6 | - |

Nicht gemessen: Spule (muss geladen und losgelassen werden), Bolzer
(Reichweite 46 px).

### Fahrzeugwaffen gegen eine stehende Figur

| Fahrzeug | 300 px | 600 px | 900 px |
| --- | --- | --- | --- |
| Jagdpanzer | 0,24 | 0,57 | 0,91 |
| Panzer | 0,34 | 0,77 | 1,19 |
| Panzerwagen | 1,24 | 2,37 | - |
| Flakwagen | 2,07 | 2,44 | 2,83 |

Die MGs der Fahrzeuge (Ring-MG, Bug-MG, Flak) haben weder Magazin noch
Hitze: sie feuern ohne Ende. Ring-MG: 13 Schaden alle 0,083 s = 156 je
Sekunde, 620 px weit.

### Panzerabwehr: Treffer bis kaputt, von vorn

Gerechnet aus Leben, `PANZERUNG` und `PANZER_SEITEN` bzw. `seiten`.

| Fahrzeug | Leben | Einwegwerfer | Panzerbuechse | Raketenbuendel (Salven) | LMG (Kugeln) |
| --- | --- | --- | --- | --- | --- |
| Panzer | 950 | 4 | 7 (24 s) | 3 (10 s) | 621 |
| Jagdpanzer | 800 | **5** | **10 (36 s)** | **4 (15 s)** | 942 |
| Panzerwagen | 620 | 2 | 3 | 2 | 105 |
| Flakwagen | 520 | 2 | 2 | 1 | 62 |
| Buggy | 380 | 1 | 2 | 1 | 23 |

Ein Panzerjaeger traegt einen Einwegwerfer je Leben, 7 Schuss
Panzerbuechse und 3 Buendel-Salven. Gegen die Front des Jagdpanzers reicht
keine dieser Waffen allein.

## Vorschlaege

### Infanteriewaffen

* **W1 ★ Praezisionsgewehr abschwaechen.** Auf jeder Entfernung die
  schnellste Waffe, und nach 0,9 s Zielen ganz ohne Streuung
  (`fokus_streuung` 0). Wahlweise:
  * a) Schaden 34 -> 28 (4 statt 3 Treffer).
  * b) Die Streuung waechst nach 3 schnellen Schuessen wieder (neue Regel).
  * c) Reichweite 900 -> 650.
* **W2 Spiegellaser:** Reichweite 1300 -> 800 oder Schaden 24 -> 20. Trifft
  auf 700 px fast so schnell wie das LMG und prallt dazu ab.
* **W3 Einwegwerfer:** Schaden gegen Figuren 140 -> 90, gegen Fahrzeuge
  bleibt 300. Heute ein Sofort-Kill auf jede Entfernung mit 96 px
  Sprengradius; gedacht ist er als Panzerabwehr.
* **W4 Sturmgewehr ab 400 px staerken:** Streuung 3,0 -> 2,4. Grundwaffe der
  meisten Bots, faellt auf mittlere Entfernung weit hinter den Repetierer
  zurueck.
* **W5 Schwache Waffen etwas anheben:**
  * Unterhebel: Takt 0,48 -> 0,40 (heute ueberall langsamer als der
    Repetierer).
  * Minigun: Anlauf 1,5 -> 1,0 s (langsamer als das LMG).
  * Granatwerfer: Nachladen 2,0 -> 1,4 s.

### Fahrzeuge

* **F1 ★ Jagdpanzer:** legt Infanterie auf 1400 px mit einem Treffer, ist
  von vorn fuer einen einzelnen Panzerjaeger praktisch nicht zu knacken und
  kostet weniger (8) als der Panzer (9). Wahlweise:
  * a) Direktschaden gegen Figuren 190 -> 110 (gegen Fahrzeuge bleibt er).
  * b) Front 0,5 -> 0,65.
  * c) Preis 8 -> 10.
* **F2 Panzer:** Kanone gegen Figuren 150 -> 110 direkt. Die Sprengwirkung
  (95) bleibt: ein Volltreffer ist weiter toedlich, ein knapper nicht.
* **F3 ★ Panzerwagen:** Ring-MG mit 156 Schaden je Sekunde ohne Ende,
  Gewehre machen ihm fast nichts (gut 100 LMG-Treffer); kostet 6, Stufe 1,
  ohne HOECHSTENS JE SEITE ohne Grenze. Wahlweise:
  * a) Ring-MG Schaden 13 -> 10, Reichweite 620 -> 520.
  * b) Hitze (siehe N1).
* **F4 Flakwagen gegen Bodenziele** nur mit 50 % Schaden. Gedacht gegen
  Flieger, legt aber fuer 5 Punkte Infanterie auf 900 px in unter 3 s.
* **F5 ★ HOECHSTENS JE SEITE standardmaessig an.** Heute aus: man kann
  beliebig viele Panzerwagen kaufen.
* Tragschrauber, Werfer, Krad und Buggy erst nach ein paar Runden mit den
  neuen Werten beurteilen. Der Tragschrauber stirbt an 10 Gewehrkugeln,
  kann seit 0.34.147 aber ueber die Ebenen ausweichen.

### Luftunterstuetzung und Bots

* **U1 ★ Napalm:** die Brandbahn haelt 30-42 s, ist eine halbe Kartenhoehe
  lang und macht 34 Schaden je Sekunde, fuer 7 Punkte. Wahlweise:
  * a) Brenndauer 15-20 s.
  * b) Preis 7 -> 9.
  * c) Erst ab Stufe 2.
* **U2 Fallschirmjaeger:** hoechstens 10 gleichzeitig lebende je Seite, oder
  jeder weitere Abwurf derselben Runde kostet 2 Punkte mehr (siehe N4).
  Heute: zusaetzliche Bots ohne Grenze, die Gegenseite bekommt nichts dazu.

### Rundenablauf

* **R1 Freischalten frueh in kurzen Runden:** in einer 5-Minuten-SCHLACHT
  kommen Panzer nach etwa 66 s und der Werfer nach etwa 105 s - schwere
  Fahrzeuge bestimmen rund zwei Drittel der Runde. Vorschlag fuer "normal":
  Stufen bei 15 / 30 / 45 % statt 10 / 22 / 35 %.
* **R2 PVP, TEAM, VERSUS, HUEGEL:** dort entscheiden fast nur die
  Infanteriewaffen (jede Waffe frei waehlbar) - W1 bis W4 wirken vor allem
  dort.

### Neue Funktionen oder Funktionen weg

* **N1 ★ Hitze fuer Fahrzeug-MGs** (Ring-MG, Bug-MG, Flak), mit demselben
  System wie bei den Energiewaffen - etwa nach 4 s Dauerfeuer ueberhitzt,
  3 s Pause. Dauerfeuer ohne Ende ist der Hauptgrund, warum Panzerwagen und
  Panzer gegen Infanterie so stark sind.
* **N2 Ketten treffen:** Treffer von Panzerbuechse, Haftladung oder Raketen
  ins Heck machen den Panzer ein paar Sekunden langsam oder unbeweglich -
  ein Mittel der Infanterie gegen Panzer, ohne sie gleich zu zerstoeren.
* **N3 Splash der Jagdkanone weg:** er wird Scharfschuetzen-Geschuetz statt
  Flaechenwaffe.
* **N4 Preisstaffel statt hartem Limit:** jeder weitere Kauf derselben Art
  in einer Runde kostet 1-2 Punkte mehr (Fahrzeuge, Napalm,
  Fallschirmjaeger).

## Vorgeschlagene Reihenfolge

1. **F5 + F3 + N1** - Fahrzeuge gegen Infanterie.
2. **F1 + U1** - Jagdpanzer und Napalm.
3. **W1 + W3** - Praezisionsgewehr und Einwegwerfer.
