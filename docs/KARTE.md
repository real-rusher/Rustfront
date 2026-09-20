# DUSTFRONT - Der Weltenplan

**Was das hier ist.** Der vollstaendige Entwurf, wie die Karte von DUSTFRONT
am Ende aufgebaut sein soll: vom Kontinent bis zur einzelnen Kachel. Nichts
davon ist gebaut. Dieses Dokument sagt, *was* gebaut wird, *warum* es so und
nicht anders, und *in welcher Reihenfolge*.

**Fuer wen.** Fuer Der Meister, und fuer jede Claude-Instanz, die spaeter
gesagt bekommt "mach mit dem Kartenplan weiter". Wer hier anfaengt, liest
zuerst Abschnitt 0 und 1, dann den Meilenstein, der dran ist.

**Stand beim Schreiben:** Version 0.11.1, PRE-ALPHA. Der Spielkern steht
(feste Zeitschritte, drei Ebenen, sechs Waffen, Inventar, Menues, Texturen
aus Dateien). Es gibt genau eine Karte: `testkarte()` in `world.py`, drei
handgetippte Textebenen. Alles Folgende haengt an dieser einen Struktur.

---

## 0. Wie dieses Dokument zu benutzen ist

Es geht **von grob nach fein**. Wer nur einen Ueberblick braucht, liest 1
bis 3. Wer baut, springt zu Abschnitt 11 (Meilensteine) und liest von dort
zurueck.

Drei Arten von Aussagen, immer unterscheidbar:

| Zeichen | Bedeutung |
| --- | --- |
| **FEST** | Steht schon im Code oder folgt zwingend daraus. Nicht verhandelbar, ohne Bestehendes umzubauen. |
| **ENTWURF** | So ist es gedacht. Begruendet, durchgerechnet, aber aenderbar. |
| **OFFEN** | Bewusst nicht entschieden. Steht in Abschnitt 12, Der Meister entscheidet. |

**Die eiserne Regel dieses Plans:** Nichts in diesem Dokument darf
erzwingen, dass der Spielkern umgebaut wird. Wo ein Entwurf das verlangen
wuerde, steht ausdruecklich dabei, was genau sich aendern muss und warum es
sich lohnt. Jede solche Stelle ist in Abschnitt 10 aufgelistet.

---

## 1. Was schon feststeht

Geerntet aus dem, was im Repo liegt. Das ist kein Vorschlag, das ist
Bestandsaufnahme - der Plan muss dazu passen, nicht umgekehrt.

### 1.1 Aus dem README

* Kontinent **Veld**. Top-Down-Ansicht, 90 Grad von oben.
* Der Spieler steuert einen **modularen Wandler** und **baut ihn aus
  Schrott weiter aus**.
* Drei Fraktionen: **die Kolonne**, **der Chor**, **die Freien Werften**.
* **Zwei Spielmodi**, die sich dieselbe Ansicht teilen: *an Bord* und
  *Fahr-Modus*, gewechselt mit Tab.

### 1.2 Aus `rustfront_menu.py`

Das Hauptmenue weiss schon mehr ueber das Spiel als das Spiel selbst. Diese
Zeilen sind bindend, weil sie dem Spieler bereits etwas versprechen:

```python
REGIONEN = [
    ("ASCHEWALD",      "sektor 12. viel schrott, wenige patrouillen. der ruhige einstieg.",
     {"KOLONNE": 0.3,  "CHOR": 0.15, "WERFTEN": 0.7}),
    ("TRICHTERFELD",   "dichte kolonne-verbaende, dafuer schwere module im wrackfeld.",
     {"KOLONNE": 0.85, "CHOR": 0.25, "WERFTEN": 0.35}),
    ("CHORWERK-RUINE", "der chor sendet noch. beste technik, kaum ueberlebende.",
     {"KOLONNE": 0.2,  "CHOR": 0.9,  "WERFTEN": 0.2}),
]
FRAKTIONSFARBE = {"KOLONNE": C_ORANGE, "CHOR": C_TEAL, "WERFTEN": C_AMBER}
```

Die Steuerungstabelle im Menue nennt Aktionen, die es im Spiel noch nicht
gibt - sie sind damit als Absicht dokumentiert:

| Taste | Aktion | Gibt es? |
| --- | --- | --- |
| B | BAUEN | nein |
| Q | WERKZEUG | nein |
| TAB | MODUS WECHSELN | nein (Tab ist heute Inventar) |
| A / D | DREHEN (FAHRT) | nein |
| W / S | FAHRT | nein |
| SHIFT | BOOST | teilweise (Sprint) |
| H | AUTOPILOT | nein (H ist heute Medkit) |

Ausserdem: `sector_preview()` zeichnet bereits eine **Sektorkarte aus acht
Knoten**, verbunden durch gestrichelte Linien, jeder Knoten in einer
Fraktionsfarbe. Der Spielstand kennt `region`, `difficulty`, `callsign`.
Die Schwierigkeit **EISERN** ist beschrieben als *"ein wandler, ein leben.
kein laden nach dem verlust."*

### 1.3 Aus dem Spielkern

* **FEST:** Eine `Welt` ist eine Liste von `Ebene`n. Eine `Ebene` ist ein
  Kachelgitter mit einem Index. Jedes Wesen gehoert zu genau einer Ebene.
* **FEST:** Karten sind **Text**. Ein Zeichen ist eine Kachel
  (`ZEICHEN` in `world.py`). `Ebene.aus_text()` baut daraus ein Gitter.
* **FEST:** `EBENEN_HOEHE = [0, 118, 182, 238, 288]` - fuenf Hoehen sind
  vorgesehen, drei werden benutzt. Der Abstand entscheidet ueber Sturzdauer,
  Fallschaden und wie klein die untere Ebene gezeichnet wird.
* **FEST:** Alle Zahlen in `config.py`. Jedes Bild durch eine Datei
  ersetzbar. Jeder Klang auch.
* **FEST:** Das HUD zeigt bereits **SCHROTT** als Zaehler. Schrott ist also
  die Waehrung, und das steht schon auf dem Bildschirm.

### 1.4 Was der Name sagt

**DUSTFRONT.** Eine *Front* aus Staub. Kein Ort, sondern eine Linie, die
sich bewegt. Das ist der wichtigste Hinweis im ganzen Projekt, und der Plan
baut darauf auf: **Die Karte hat einen Motor, und der Motor ist die
vorrueckende Front.** Siehe Abschnitt 5.3.

---

## 2. Die drei Massstaebe

Der Fehler, den man hier machen kann, ist "eine riesige Karte" woertlich zu
nehmen und eine gigantische Kachelflaeche zu bauen. Das waere technisch
machbar und spielerisch tot: leere Wege, kein Rhythmus, keine Spannung, und
`ebene_zeichnen()` wuerde bei 500x500 Kacheln pro Bild durch eine Million
Felder laufen.

Stattdessen hat DUSTFRONT **drei Massstaebe**, die ineinandergreifen. Jeder
hat eine eigene Aufgabe, eine eigene Zeitskala und ein eigenes Gefuehl.

```
    VELD            Der Kontinent. Ein Knotengraph, keine Kacheln.
    (Strategie)     Zeitskala: Tage. Hier entscheidet man WOHIN.
        |           Die Front rueckt nach. Treibstoff ist knapp.
        |
        |  ankommen / abfahren
        v
    DER ORT         Ein Knoten von innen. Kachelwelt, 3-5 Ebenen.
    (Taktik)        Zeitskala: Minuten. Hier entscheidet man WIE.
        |           Das ist der Spielkern, wie er heute schon laeuft.
        |
        |  Rampe / Luke
        v
    DER WANDLER     Das fahrende Zuhause. Kachelwelt, 3 Etagen.
    (Ruhe, Bau)     Zeitskala: solange man will. Hier entscheidet man WOMIT.
                    Kein Gegner an Bord (ausser bei Ueberfaellen).
```

**Warum drei und nicht zwei.** Ohne den Wandler waere das Spiel eine Folge
von Missionen ohne Zuhause - man haette nichts, wofuer man sammelt. Ohne
Veld waere es eine Levelliste ohne Entscheidung. Ohne den Ort waere es ein
Menuespiel. Alle drei tragen.

**Das Versprechen an den Spieler**, in einem Satz je Massstab:

* *Veld:* "Ich komme nicht ueberall hin. Ich muss waehlen."
* *Ort:* "Ich weiss nicht, was hinter der naechsten Wand ist."
* *Wandler:* "Das hier ist meins, und es wird besser."

---

## 3. Die eine technische Grundlage

Dieser Abschnitt ist der wichtigste des Dokuments. Wer ihn ueberspringt,
baut spaeter dreimal dasselbe.

### 3.1 Alles Begehbare ist eine `Welt`

**ENTWURF, und zwar ein harter:** Der Ort und der Wandler sind **dieselbe
Datenstruktur**. Beide sind eine `Welt` aus `Ebene`n, beide werden vom
selben Renderer gezeichnet, beide benutzen dieselbe Kollision, dieselben
Treppen, dieselben Stuerze.

Das ist kein Sparzwang, das ist die Bedingung dafuer, dass sich der Wandler
wie ein Ort anfuehlt und nicht wie ein Menue mit Hintergrundbild. Man laeuft
an Bord genauso wie draussen, faellt genauso durch eine offene Luke, und
schiesst durch dieselben Loecher.

**Was daraus folgt:** Es darf keinen Code geben, der "Wandler" von "Ort"
unterscheidet, ausser bei den Regeln (Gegner, Beute, Zeitdruck). Die
Darstellung unterscheidet gar nichts.

### 3.2 Der Wandler wird in den Ort gestempelt

Das ist die Kernentscheidung, und sie hat drei denkbare Antworten. Alle drei
wurden durchgerechnet.

**Weg A - zwei getrennte Welten, Blende dazwischen.**
Man steht an der Rampe, drueckt E, kurze Schwarzblende, man ist an Bord.
*Kosten:* niedrig, geht fast ohne neuen Code. *Preis:* der Wandler steht
nicht wirklich in der Welt. Man kann nicht vom Oberdeck auf das Wrackfeld
schiessen, nicht von draussen sehen, dass die Rampe offen ist. Der Uebergang
ist ein Schnitt, und Schnitte kosten genau das Gefuehl, das in 0.11.0
teuer erkauft wurde ("nichts springt").

**Weg B - der Wandler faehrt als bewegliches Kachelfeld durch die Ortswelt.**
*Kosten:* sehr hoch. Bewegliche Kacheln bedeuten, dass Kollision,
Sichtlinien und das Kachelraster nicht mehr an ganzen Kachelkoordinaten
haengen duerfen. `frei()`, `strahl()`, `bewegen()`, `ebene_zeichnen()`
muessten alle umgeschrieben werden. *Preis:* Monate, und ein Kern, der nicht
mehr einfach ist.

**Weg C - der Wandler wird beim Ankommen in die Ortswelt gestempelt.**
Empfohlen. Der Wandler ist ein **Bauplan**: ein Satz Textebenen plus eine
Liste von Einbauten. Beim Ankommen an einem Knoten wird dieser Bauplan an
einer festgelegten Andockstelle in die Ebenen der Ortswelt kopiert -
Kachel fuer Kachel, einmal, beim Aufbau der Karte.

```
    Ortskarte E1:  ..........................
                   ....####..................
                   ..........................

    Wandler E1:    +------+
                   |..>...|
                   |.X..X.|
                   +------+

    Ergebnis E1:   ..........................
                   ....####..+------+........
                   ..........|..>...|........
                   ..........|.X..X.|........
                   ..........+------+........
```

*Kosten:* gering. Eine Funktion `stempeln(welt, bauplan, tx, ty)`, die
Kacheln kopiert. Mehr nicht - danach ist es eine ganz normale Welt.
*Gewinn:* alles von Weg B, solange der Wandler steht. Man laeuft nahtlos
hinaus, schiesst vom Oberdeck, sieht die Rampe. Kein Ladebildschirm, kein
Schnitt.
*Grenze:* der Wandler kann sich waehrend eines Ortsbesuchs nicht bewegen.
Das ist kein Verlust, sondern richtig: **man parkt, man steigt aus, man
arbeitet.** Die Fahrt ist ein eigener Massstab (Abschnitt 5).

**Entscheidung: Weg C.** Der Rest des Dokuments setzt ihn voraus.

### 3.3 Was `Ebene` dafuer koennen muss

Heute kommt eine Ebene aus einer Liste gleich langer Zeilen. Fuer den
Stempel braucht es drei kleine Faehigkeiten. Alle drei sind additiv - kein
bestehender Aufruf aendert sich.

| Neu | Wofuer | Aufwand |
| --- | --- | --- |
| `Ebene.stempeln(zeilen, tx, ty)` | Bauplan an Position kopieren, Leerzeichen als "nichts aendern" | klein |
| `Ebene.marken` | benannte Punkte aus der Karte (`@rampe`, `@werkbank`) | klein |
| `Welt.aus_plan(plan)` | eine Welt aus einer Beschreibung bauen statt aus drei festen Listen | mittel |

**Marken sind wichtiger, als sie aussehen.** Ohne sie muss jeder Ort im Code
wissen, wo seine Rampe ist. Mit ihnen steht es in der Karte:

```
ZEICHEN erweitern um Markierungszeichen, die beim Einlesen zu BODEN werden
und ihre Position in ebene.marken ablegen:

    "R"  ->  BODEN, marke "rampe"
    "W"  ->  BODEN, marke "werkbank"
    "S"  ->  BODEN, marke "start"
    "1".."9" -> BODEN, marke "punkt1".."punkt9"  (Gegnerwellen, Beute)
```

Damit kann ein Kartenbauer - Mensch oder spaeter ein Generator - einen Ort
vollstaendig in Text beschreiben, ohne eine Zeile Python.

### 3.4 Groessen, durchgerechnet

Die Zahlen sind nicht geraten. `ebene_zeichnen()` laeuft nur ueber den
sichtbaren Ausschnitt, aber `Welt.schritt()` und das Nachbarschaftsraster
laufen ueber alles.

Bei 640x360 Bildpunkten und 32er Kacheln sieht man **20 x 11,25 Kacheln**
gleichzeitig. Daraus folgen sinnvolle Ortsgroessen:

| Ort | Kacheln | Bildschirme | Gefuehl |
| --- | --- | --- | --- |
| eng (Bunker, Silo) | 30 x 20 | 1,5 x 1,8 | man kennt ihn nach einem Besuch |
| mittel (heutige Testkarte) | 44 x 24 | 2,2 x 2,1 | gut ueberschaubar |
| gross (Wrackfeld, Trichter) | 80 x 50 | 4 x 4,4 | man braucht die Ebenenanzeige |
| sehr gross (Obergrenze) | 120 x 70 | 6 x 6 | nur mit Wegmarken sinnvoll |

**Obergrenze 120 x 70 je Ebene, fuenf Ebenen.** Das sind 42 000 Kacheln.
Messwert heute: 3,9 ms pro Bild bei 51 Wesen auf 44x24x3. Der Zeichenaufwand
haengt am Ausschnitt, nicht an der Kartengroesse, also bleibt er gleich. Was
waechst, ist das einmalige Aufbauen und der Speicher (42 000 Ganzzahlen sind
nichts). **Machbar, mit Reserve.**

Was *nicht* machbar ist: eine zusammenhaengende Flaeche ueber ganz Veld.
Deshalb der Knotengraph.

### 3.5 Die fuenfte Ebene, und warum nach unten

`EBENEN_HOEHE` hat fuenf Eintraege, benutzt werden drei. Der Plan nutzt alle
fuenf, aber nicht so, wie man zuerst denkt.

**ENTWURF:** Ebene 0 ist nicht immer der Boden. Bei einem **Trichter** ist
Ebene 0 die Kraterwand oben und man steigt nach unten - dann sind die
tieferen Ebenen negativ gedacht. Technisch bleibt es bei aufsteigenden
Indizes; was sich aendert, ist nur, wo der Spieler startet und wohin die
Treppen zeigen.

Das kostet **null Code**: ein Ort mit fuenf Ebenen, Start auf Ebene 4,
Treppen nach unten. Und es fuehlt sich voellig anders an als ein Turm, weil
man beim Abstieg immer weiter ins Dunkle kommt und der Rueckweg nach oben
der gefaehrliche ist.

---

## 4. Der Wandler

Das fahrende Zuhause. Hier entscheidet sich, ob das Spiel eine Seele hat.

### 4.1 Die Grundidee

**ENTWURF:** Der Wandler ist gleichzeitig Fahrzeug, Basis und
**Fortschrittsanzeige**. Es gibt keinen abstrakten Faehigkeitsbaum in einem
Menue - man **laeuft durch seinen eigenen Fortschritt**. Ein neues Modul ist
ein neuer Raum, den es vorher nicht gab. Wer nach zehn Stunden an Bord geht,
sieht auf einen Blick, was er erreicht hat.

Das ist die staerkste Idee in diesem Plan, und alles andere ordnet sich ihr
unter. Begruendung: Ein Skill-Tree im Menue ist eine Tabelle. Ein Deck, das
sich fuellt, ist ein Ort. Orte erinnert man, Tabellen nicht.

### 4.2 Die drei Decks

Der Wandler hat **drei Etagen**, genau wie der Spielkern sie schon kann.
Jedes Deck hat eine klare Aufgabe, damit man nie sucht.

```
   E2  BRUECKE          Steuerstand, Kartentisch, Funk, Kanzel
       ------------     "Wohin fahre ich?"
   E1  HAUPTDECK        Werkbank, Modulschaechte, Kojen, Lager
       ------------     "Womit fahre ich?"
   E0  UNTERDECK        Reaktor, Antrieb, Werkstatt, RAMPE nach draussen
       ------------     "Faehrt es ueberhaupt noch?"
```

**Warum diese Reihenfolge.** Wer von draussen hereinkommt, betritt das
Unterdeck - dreckig, laut, hier wird repariert. Nach oben wird es ruhiger
und heller, bis zur Bruecke mit Aussicht. Das ist eine Stimmungskurve, die
man beim Hochsteigen spuert, und sie belohnt das Heimkommen.

Ausserdem praktisch: die Rampe liegt unten, der Kartentisch oben. Wer los
will, geht hoch (Ziel waehlen) und dann runter (losfahren). Der Weg selbst
erzaehlt den Ablauf.

### 4.3 Groesse und Grundriss

**ENTWURF:** Der Wandler misst **18 x 12 Kacheln** je Deck. Das sind knapp
zwei Bildschirmbreiten - gross genug, dass es sich nach Raum anfuehlt, klein
genug, dass man in wenigen Sekunden vom Reaktor zur Rampe kommt.

Ein erster Grundriss, im Format, das `Ebene.aus_text()` schon versteht:

```
E0 UNTERDECK (18 x 12)          E1 HAUPTDECK                E2 BRUECKE
##################              ##################          ##################
#....#RRRR#......#              #......#....#....#          #................#
#.WW.#....#..RE..#              #.SS...#.MM.#.LL.#          #....#......#....#
#.WW.......<.....#              #.SS........<....#          #....#.KK...#....#
#....#....#......#              #......#....#....#          #.....>..........#
#....o....#..>...#              #..MM..o....>....#          #....#......#....#
#.AA.#....#......#              #..MM..#....#....#          #....#..TT..#....#
#.AA.#....#......#              #......#....#....#          #................#
##################              ##################          ##################

  R = Rampe (Marke)               S = Schlafkoje              K = Kartentisch
  W = Werkstatt                   M = Modulschacht            T = Steuerstand
  A = Antrieb                     L = Lager                   > = Treppe hoch
  E = Reaktor                     o = Luke nach unten         < = Treppe runter
```

Das ist **ENTWURF, nicht fest** - der endgueltige Grundriss entsteht beim
Bauen. Was fest sein soll: Rampe unten aussen, Treppen durchgehend an
derselben Stelle (damit man blind hoch und runter findet), Modulschaechte
gebuendelt auf E1.

### 4.4 Module: der Fortschritt zum Anfassen

**ENTWURF:** Ein Modul belegt einen **Schacht** - ein 2x2-Feld auf einem
Deck. Ein leerer Schacht ist sichtbar leer (offene Verankerung, lose Kabel).
Ein belegter Schacht zeigt das Modul und laesst sich benutzen.

| Modul | Deck | Was es tut | Warum man es will |
| --- | --- | --- | --- |
| **Reaktor** | E0 | liefert Energie, Stufe 1-3 | jedes andere Modul zieht davon |
| **Antrieb** | E0 | Reichweite je Etappe | weiter kommen, bevor die Front nachrueckt |
| **Werkstatt** | E0 | Reparatur zwischen Orten | ohne sie faehrt man Schaden mit |
| **Greifer** | E0 | bergt schwere Beute | manche Module liegen sonst unerreichbar |
| **Werkbank** | E1 | Waffen verbessern | die sechs Waffen bekommen Stufen |
| **Lager** | E1 | wie viel Schrott mitgeht | ohne Lager laesst man Beute liegen |
| **Kojen** | E1 | Leben zwischen Orten auffuellen | sonst zaehlt jeder Treffer dauerhaft |
| **Labor** | E1 | Chor-Technik auswerten | der einzige Weg an die besten Teile |
| **Funk** | E2 | deckt Sektorknoten auf | man faehrt nicht mehr blind |
| **Kanzel** | E2 | Geschuetz gegen Ueberfaelle | sonst ist ein Ueberfall reiner Verlust |
| **Panzerung** | alle | Huellenpunkte | ueberlebt den Ueberfall |

**Energie als Knappheit.** Der Reaktor liefert eine Zahl. Jedes Modul zieht
eine Zahl. Man kann mehr einbauen, als man betreiben kann - dann muss man
abschalten. Das erzeugt echte Entscheidungen, ohne eine einzige neue
Mechanik: es ist Addition.

**Warum das Spass macht:** Jeder Fund draussen hat einen sichtbaren Platz
drinnen. Man traegt kein abstraktes "+3 Angriff" nach Hause, sondern eine
Kiste, die in einem bestimmten Schacht landet und danach *da ist*.

### 4.5 Der Wandler als Gegenstand der Story

**ENTWURF:** Der Wandler ist nicht neu. Er hat **Spuren von Vorbesitzern** -
ein zugeschweisster Schacht, ein Name unter der Farbe, eine Koje zu viel.
Wer genau hinsieht, findet sie. Das erzaehlt Geschichte ohne einen einzigen
Dialog, passt zur Fraktion der Freien Werften (Weiterverwertung) und kostet
nur Textur- und Marken-Arbeit.

Bei **EISERN** ("ein wandler, ein leben") bekommt das Gewicht: der Wandler,
den man verliert, ist der, in dem man zwanzig Stunden gelebt hat.

---

## 5. Veld: die Sektorkarte

### 5.1 Warum ein Graph und keine Flaeche

Ein durchgehender Kontinent waere leer. Ein Graph gibt jedem Weg eine
Bedeutung: man sieht drei moegliche naechste Knoten, kennt von jedem etwas,
und muss einen waehlen. Das ist eine Entscheidung pro Etappe statt einer
Fahrt durch Nichts.

Ausserdem: **die Vorschau gibt es schon.** `sector_preview()` zeichnet acht
Knoten mit Verbindungen und Fraktionsfarben. Der Plan macht daraus die echte
Karte, statt etwas Neues danebenzustellen.

### 5.2 Aufbau eines Sektors

**ENTWURF:** Ein Sektor ist ein Graph von **14 bis 20 Knoten**, gerichtet von
links (Start) nach rechts (Ausgang), in **6 bis 8 Spalten**. Pro Spalte 2 bis
4 Knoten. Von einem Knoten fuehren 1 bis 3 Kanten in die naechste Spalte.

```
   Spalte  1     2     3     4     5     6     7
                                                     Legende
           o-----o-----o     o-----o-----o           o  Knoten
            \   / \   / \   /       \   /            -  Fahrtstrecke
             \ /   \ /   \ /         \ /             #  Ausgang
   START -----o-----o-----o-----o-----o----- #
             / \   / \   /       \   / \
            /   \ /   \ /         \ /   \
           o-----o     o-----o-----o     o
```

Man kann also nie alles sehen. Bei 16 Knoten und 7 Spalten besucht man etwa
7 - **weniger als die Haelfte**. Das ist der Punkt: ein zweiter Durchlauf
sieht anders aus, und jede Entscheidung kostet etwas anderes.

### 5.3 Die Front - der Motor der ganzen Karte

**ENTWURF, und der wichtigste im Dokument.**

Hinter dem Spieler rueckt eine Linie nach: die Staubfront der Kolonne. Sie
bewegt sich pro **Etappe** eine feste Strecke nach rechts. Wer einen Knoten
besucht, verbraucht eine Etappe. Wer zurueckfaehrt, auch.

```
   ////|                                            //// bereits ueberrollt
   ////|  o-----o-----o     o-----o-----o           |    die Front
   ////|   \   / \   / \   /       \   /            X    hier steht der Spieler
   ////|----X-----o-----o-----o-----o----- #
   ////|   / \   / \   /       \   / \
   ////|  o-----o     o-----o-----o     o
```

Was das bewirkt, alles auf einmal:

1. **Es gibt kein Ausruhen.** Man kann nicht jeden Knoten mitnehmen. Gier
   wird bestraft, ohne dass eine Uhr tickt, die man anstarrt.
2. **Der Name stimmt.** DUSTFRONT ist die Front. Der Titel erklaert sich
   beim ersten Blick auf die Karte.
3. **Spannung ohne Gegner.** Der Druck kommt aus der Karte, nicht aus mehr
   Feinden. Das haelt die Gefechte lesbar.
4. **Rueckkehr kostet echt etwas.** Ein Knoten hinter einem ist nicht
   "gratis nochmal", sondern eine Etappe naeher an der Front.
5. **Eine Verlustbedingung, die kein Tod ist.** Wird man ueberrollt, ist der
   Lauf vorbei - aber anders als beim Sterben, und das macht den zweiten
   Durchlauf anders.

**Zahlen, ENTWURF:** Front rueckt 1 Spalte je 2 Etappen. Sektor hat 7
Spalten. Man hat also rund 14 Etappen fuer 7 noetige Schritte - Luft fuer
etwa 7 Umwege, wenn man nie zurueckfaehrt. Feinjustage gehoert in
`config.py` unter `FRONT`.

### 5.4 Was man auf der Karte sieht

**ENTWURF:** Ein Knoten zeigt vor dem Anfahren:

* **Fraktionsfarbe** - wem der Ort gehoert (gibt es schon)
* **Typ-Zeichen** - Wrack, Vorposten, Turm, Werft, Trichter (Abschnitt 6)
* **eine Zeile Vorwissen**, wenn Funk eingebaut ist: *"schwer befestigt"*,
  *"kaum bewacht"*, *"chor sendet"*

Ohne Funk sieht man nur Farbe und Typ. **Das Funkmodul kauft Information**,
und Information ist in einem Spiel mit knappen Etappen bares Geld. Damit hat
ein unscheinbares Modul echtes Gewicht.

---

## 6. Der Ort: wie ein Knoten von innen aussieht

Hier lebt das Spiel. Der Spielkern kann das heute schon - was fehlt, ist
Vielfalt und eine Regel, warum jeder Ort sich anders anfuehlt.

### 6.1 Die Regel: jeder Ortstyp nutzt die Hoehe anders

Das ist der Pruefstein fuer jeden Entwurf in diesem Abschnitt. Drei Ebenen
sind teuer erkauft; ein Ort, der sie nicht braucht, verschwendet sie.

| Typ | Ebenen | Wie die Hoehe benutzt wird | Gefuehl |
| --- | --- | --- | --- |
| **Wrackfeld** | 2 | flach, wenige Aufbauten zum Draufsteigen | offen, ruhig, Sammeln |
| **Vorposten** | 3 | Wachtuerme oben, Hof unten, Feuer von oben | Deckung suchen |
| **Chorturm** | 5 | ein Turm, man steigt **hoch**, eng | Aufstieg, Klaustrophobie |
| **Trichter** | 5 | ein Krater, man steigt **runter** | Abstieg, Rueckweg ist die Gefahr |
| **Freie Werft** | 3 | kein Kampf, Ebenen als Stadtviertel | Ruhe, Handel |
| **Silo** | 4 | senkrechte Schaechte, Stuerze als Abkuerzung | Tempo, Risiko |
| **Konvoi** | 2 | flach, dafuer Zeitdruck | Hetze |

**Wrackfeld mit 2 Ebenen ist Absicht.** Nicht jeder Ort muss alles koennen.
Ein flacher, offener Ort nach einem engen Turm ist Erholung, und Erholung
macht den naechsten Turm wieder eng.

### 6.2 Zonen statt Raeume

**ENTWURF:** Ein Ort besteht aus **Zonen**, nicht aus einem gleichmaessigen
Gewirr. Drei Sorten, und jeder Ort mischt sie anders:

1. **Ankunft** - wo der Wandler parkt. Immer sicher, immer am Rand, immer
   wiedererkennbar. Von hier sieht man in mindestens zwei Richtungen.
2. **Durchgang** - Wege, Deckung, Treppen. Hier passiert der Kampf.
3. **Kammer** - wo etwas ist, das man will. Beute, ein Modul, ein Terminal.
   Eine Kammer hat **immer mindestens zwei Zugaenge** (eine Treppe zaehlt),
   damit sie keine Falle ist.

Die Regel mit den zwei Zugaengen ist nicht kosmetisch: mit nur einem Zugang
wird jede Kammer zum Rueckzugspunkt, in dem man alles einzeln abarbeitet.
Das ist langweilig und macht den Schrot unbesiegbar.

### 6.3 Die Beute-Regel

**ENTWURF:** Jeder Ort hat genau **eine Hauptbeute** (ein Modul, eine
Blaupause, ein Fass Treibstoff) und **verstreuten Schrott**. Die Hauptbeute
liegt nie am Anfang und nie hinter einer einzelnen Tuer - sie liegt so, dass
man **mindestens eine Ebene wechseln** muss, um sie zu holen.

Warum: Der Ebenenwechsel ist die teuerste und beste Mechanik des Spiels.
Wenn Beute ihn erzwingt, wird er benutzt, statt eine Kuriositaet zu bleiben.

### 6.4 Wie Orte entstehen

**ENTWURF, dreistufig - und die Reihenfolge ist wichtig:**

**Stufe 1 (zuerst): Handgetippte Karten.** Wie heute, in Textdateien unter
`karten/<typ>_<nummer>.txt`. Vier bis sechs je Typ. Handgebaut ist besser
als generiert, solange man noch nicht weiss, was gut ist.

**Stufe 2: Bausteine.** Ein Ort wird aus handgetippten **Stuecken** von
8x8 oder 16x16 Kacheln zusammengesetzt, die an den Raendern zusammenpassen.
Das gibt Abwechslung mit handgemachter Qualitaet. Diese Technik traegt
auch grosse Karten.

**Stufe 3 (nur wenn noetig): echte Erzeugung.** Erst wenn Stufe 2 sich
erschoepft anfuehlt.

**Warum diese Reihenfolge:** Ein Generator, der gebaut wird, bevor man weiss,
was einen guten Ort ausmacht, erzeugt gleichmaessigen Brei. Der Weg ueber
Bausteine zwingt dazu, erst gute Stuecke zu haben.

**Pflicht ab Stufe 2:** Ein Pruefwerkzeug, das jede erzeugte Karte testet:
Ist die Hauptbeute erreichbar? Hat jede Kammer zwei Zugaenge? Ist jede Ebene
von der Ankunft aus erreichbar? Gibt es eine Stelle, wo man sich
festfahren kann? Das gehoert in `tests/test_karten.py` und laeuft als
dritter Testlauf - oder haengt sich an `test_spiel.py`, damit es bei den
zwei gewohnten Laeufen bleibt.

---

## 7. Die drei Regionen

Die Namen und die Fraktionsverteilung stehen bereits im Menue und sind damit
**FEST**. Was fehlt, ist ihr Charakter: eine Region muss sich anders
*anfuehlen*, nicht nur andere Zahlen haben.

### 7.1 ASCHEWALD - Sektor 12

> *"viel schrott, wenige patrouillen. der ruhige einstieg."*
> Kolonne 0.3 · Chor 0.15 · Werften 0.7

**Bild:** Verbrannter Wald aus Stahlmasten. Asche liegt knoecheltief, jeder
Schritt staubt. Weite Sicht, wenig Deckung.

**Was hier gelehrt wird.** Aschewald ist der Lehrsektor, und er lehrt durch
Aufbau, nicht durch Textkaesten:

| Was der Spieler lernen soll | Wie die Karte es beibringt |
| --- | --- |
| Ebenen wechseln | Die erste Hauptbeute liegt auf einem Mast, nur ueber eine Treppe erreichbar. |
| Stuerzen ist erlaubt | Der Rueckweg vom Mast ist ein Sprung. Fallschaden ist klein genug. |
| Durch Loecher schiessen | Ein Gegner steht unter einem Gitterrost, bevor er einen bemerkt. |
| Schrott ist Waehrung | Der erste Knoten hat mehr Schrott, als das Lager fasst. |

**Ortsmischung:** viele Wrackfelder, zwei bis drei Freie Werften, wenige
Vorposten, **kein** Chorturm. Werftenanteil 0.7 heisst: hier gibt es
Menschen, hier kann man handeln.

### 7.2 TRICHTERFELD

> *"dichte kolonne-verbaende, dafuer schwere module im wrackfeld."*
> Kolonne 0.85 · Chor 0.25 · Werften 0.35

**Bild:** Einschlagkrater, einer neben dem anderen, randvoll mit dem, was
die Kolonne liegengelassen hat. Zwischen den Trichtern Daemme aus
gepresstem Schrott. Man ist entweder oben und sichtbar oder unten und blind.

**Was hier anders ist.** Das ist der Sektor, in dem **Tiefe nach unten**
zum ersten Mal wehtut. Trichter haben fuenf Ebenen, und Ebene 0 ist der
Kraterboden - dunkel, eng, voll. Man steigt hinunter, weil die schweren
Module unten liegen, und der Rueckweg ist der gefaehrliche, weil man nicht
mehr fallen kann, sondern klettern muss.

**Der Kolonne-Anteil von 0.85 muss man spueren:** Patrouillen sind hier
nicht Gegner, die warten, sondern Verbaende, die **durchziehen**. Wer sich
Zeit laesst, trifft auf mehr. Das koppelt direkt an die Front.

**Ortsmischung:** Trichter, Vorposten, Konvoi-Hinterhalte. Werften selten
und wertvoll.

### 7.3 CHORWERK-RUINE

> *"der chor sendet noch. beste technik, kaum ueberlebende."*
> Kolonne 0.2 · Chor 0.9 · Werften 0.2

**Bild:** Tuerme aus weissem Beton, die immer noch Strom haben. Kein Rost,
kein Staub - der Chor haelt sauber. Licht, das von selbst angeht.

**Was hier anders ist.** Der Chor ist keine Armee, sondern eine **Anlage,
die weiterlaeuft**. Seine Gegner sind keine Soldaten, sondern Wartung, die
einen als Stoerung einordnet. Das erlaubt Gegnertypen, die nicht auf den
Spieler zulaufen, sondern Routen abgehen und nur reagieren, wenn man auf
ihrer Route steht - und das macht Schleichen moeglich, ohne ein
Schleichsystem zu bauen.

**Chortuerme sind der Gegenentwurf zum Trichter:** man steigt **hoch**, eng,
in einem Turm ohne Aussenlicht. Oben ist die beste Beute und der einzige
Weg zurueck ist derselbe enge Schacht - ausser man wirft sich in den
Lichtschacht und faellt fuenf Ebenen. Das ist der Moment, in dem der Sturz
mit Steuerung in der Luft, der in 0.11.0 gebaut wurde, seinen Auftritt hat.

**Ortsmischung:** Chortuerme, Silos, Sendemasten. Fast keine Werften -
hier ist man allein.

### 7.4 Wie die Regionen zusammenhaengen

**ENTWURF:** Die drei Regionen sind **nicht** drei Schwierigkeitsgrade zur
Auswahl, sondern drei Abschnitte einer Reise. Das Menue laesst einen
waehlen, wo man **anfaengt** - wer spaeter anfaengt, faengt haerter an.

```
   ASCHEWALD  --->  TRICHTERFELD  --->  CHORWERK-RUINE
   lernen           verdienen           riskieren
   (Sektor 12)      (die Front holt      (der Grund, warum
                     hier zum ersten      man ueberhaupt
                     Mal wirklich auf)    gefahren ist)
```

Jede Region ist ein eigener Sektorgraph mit eigenem Ausgang. Wer den Ausgang
erreicht, faehrt in die naechste - mit dem Wandler, den er hat. **Der
Wandler ist das, was zwischen den Regionen bleibt**, und damit ist er auch
das, was den Fortschritt traegt.

---

## 8. Progression: was waechst womit

Damit nichts doppelt oder gar nicht waechst, hier alles an einer Stelle.

### 8.1 Die vier Faeden

| Faden | Waehrung | Wo man ihn spuert | Verliert man ihn beim Tod? |
| --- | --- | --- | --- |
| **Wandler** | Module, Schrott | an Bord, sichtbar als Raum | ja (bei EISERN endgueltig) |
| **Waffen** | Schrott an der Werkbank | im Gefecht | ja |
| **Wissen** | Blaupausen, Funkdaten | Sektorkarte, Bauliste | **nein** |
| **Spieler** | Panzerung, Medkits | Leben im HUD | ja |

**Der dritte Faden ist der wichtige.** Wissen bleibt. Wer einmal eine
Blaupause gefunden hat, kann sie im naechsten Lauf bauen, wenn er das
Material hat. Damit hat auch ein verlorener Lauf etwas gebracht, ohne dass
die Schwierigkeit sinkt. Das ist der Unterschied zwischen "nochmal von vorn"
und "nochmal, aber ich weiss jetzt mehr".

### 8.2 Die Kopplung an die Karte

Jeder Faden haengt an einem Ortstyp - so weiss man, wohin man fahren muss,
wenn man etwas Bestimmtes braucht. Das macht die Sektorkarte zu einer echten
Entscheidung statt zu einer Reihenfolge.

| Braucht man | Faehrt man zu | Kostet |
| --- | --- | --- |
| Schrott (Menge) | Wrackfeld | Zeit, wenig Risiko |
| Schweres Modul | Trichter, Vorposten | viel Risiko |
| Chor-Technik | Chorturm, Silo | sehr viel Risiko |
| Reparatur, Handel | Freie Werft | Schrott |
| Vorwissen | Sendemast | eine Etappe |

### 8.3 Die Waffen bekommen Stufen

Die sechs Waffen stehen und sind ausbalanciert (im Test nachgewiesen). Sie
sollen **nicht** ersetzt werden - man findet keine "bessere Schrotflinte".
Stattdessen hat jede Waffe an der Werkbank drei Stufen, die je **eine Zahl
in `K.WAFFEN`** anheben.

Das ist mit Absicht langweilig gebaut: Es gibt bereits einen Test, der die
Balance jeder Waffe misst. Stufen, die nur Zahlen anheben, lassen sich mit
demselben Test pruefen. Waffen mit neuen Faehigkeiten wuerden das kaputt
machen.

**ENTWURF fuer die Stufen** - je Waffe genau eine Eigenheit, die ihren
Charakter schaerft, statt sie rundum besser zu machen:

| Waffe | Stufe hebt | Damit wird sie |
| --- | --- | --- |
| Repetierer | `magazin` | der verlaessliche Dauerlaeufer |
| Sturmgewehr | `streuung_dauerfeuer` runter | im Dauerfeuer beherrschbar |
| Schrot | `geschosse` | auf kurze Distanz vernichtend |
| Scharfschuetze | `fokus_dauer` runter | schneller einsatzbereit |
| Granate | `radius` | Flaechenwaffe statt Punktwaffe |
| Brecheisen | `schub` | ein Werkzeug, um Platz zu schaffen |

---

## 9. Story: ein Geruest, keine Geschichte

**OFFEN, zur Entscheidung.** Was hier steht, ist ein Vorschlag, der zu
allem oben passt. Der Meister entscheidet, ob es so erzaehlt wird.

### 9.1 Die Ausgangslage

Die **Kolonne** rueckt ueber Veld vor - keine Armee mit Zielen, sondern
etwas, das sich ausbreitet und alles einebnet, was es ueberrollt. Sie ist
die Front, und sie ist im Ruecken des Spielers.

Der **Chor** war vor der Kolonne da und ist praktisch verschwunden. Seine
Anlagen laufen weiter, ohne dass jemand sie bedient. Sie senden - und
niemand weiss, an wen.

Die **Freien Werften** sind, was von den Menschen uebrig ist: Handel,
Reparatur, Weiterverwertung. Kein Widerstand, nur Ausweichen. Der Spieler
ist einer von ihnen.

### 9.2 Der Bogen

**ENTWURF:** Kein Heldenbogen, sondern ein Frachtauftrag, der sich als
etwas anderes herausstellt.

1. **Aschewald.** Man faehrt einen gewoehnlichen Bergungsauftrag. Die Front
   ist weit weg, ein Geruecht. Am Ende des Sektors ueberholt sie einen zum
   ersten Mal - eine Werft, bei der man war, ist beim Zurueckkommen nicht
   mehr da.
2. **Trichterfeld.** Man faehrt nicht mehr zu etwas hin, sondern vor etwas
   davon. Zwischen den Trichtern findet man Chor-Technik, die nicht dorthin
   gehoert - jemand hat sie dort vergraben.
3. **Chorwerk-Ruine.** Man faehrt hin, weil die Sendungen eine Richtung
   haben, und die Richtung ist vor der Front, nicht hinter ihr. Was am Ende
   steht, entscheidet Der Meister.

**Warum das traegt:** Der Bogen braucht keinen einzigen Dialog. Er besteht
aus drei Sektoren und einer Front, die naeher kommt. Alles, was erzaehlt
wird, wird durch Orte erzaehlt - und Orte sind das, was dieser Plan ohnehin
baut.

### 9.3 Wie erzaehlt wird

**ENTWURF - vier Mittel, alle billig, keines braucht ein Dialogsystem:**

1. **Der Ort selbst.** Eine Werft mit gedeckten Tischen und niemandem darin.
2. **Terminals.** Kurze Texte an festen Stellen, mit E zu lesen. Genau das,
   wofuer `Spieler.abbrechen()` schon vorbereitet ist.
3. **Der Funk.** Das Funkmodul faengt Bruchstuecke auf, die beim Fahren
   eingeblendet werden. Ein Satz, kein Absatz.
4. **Der Wandler.** Spuren der Vorbesitzer, die man nach Stunden erst
   bemerkt.

**Was ausdruecklich nicht:** Gespraeche mit Auswahlmoeglichkeiten,
Auftragsgeber, Textkaesten, die den Ablauf anhalten. Nichts davon passt zu
einem Spiel, dessen Kernversprechen "nichts springt, nichts sperrt" ist.

---

## 10. Machbarkeit: was neuen Code braucht

Ehrliche Aufstellung. Alles, was dieser Plan verlangt, in vier Toepfen.

### 10.1 Geht heute schon, ohne eine Zeile

* Mehr Ebenen je Ort (bis fuenf, `EBENEN_HOEHE` hat sie)
* Groessere Karten (nur laengere Textlisten)
* Orte, bei denen man nach unten statt nach oben steigt
* Neue Kacheltypen (ein Eintrag in `KACHELN` und `ZEICHEN`)
* Neue Gegnertypen (ein Eintrag in `GEGNER` plus ein Bild)
* Jede Textur und jeder Klang dafuer

### 10.2 Kleine Ergaenzungen, additiv

| Was | Wo | Aufwand |
| --- | --- | --- |
| Marken in Karten (`@rampe`) | `world.py`, `ZEICHEN` | klein |
| `Ebene.stempeln()` | `world.py` | klein |
| Karten aus Dateien statt aus Konstanten | `world.py` | klein |
| Terminal-Kachel zum Lesen | `world.py`, `play.py` | klein |
| Waffenstufen | `config.py`, `inventar.py` | klein |

### 10.3 Neue Bausteine, aber ohne Umbau am Kern

| Was | Neue Datei | Aufwand |
| --- | --- | --- |
| Sektorgraph, Knoten, Kanten | `sektor.py` | mittel |
| Sektorkarte als Szene | `sektor_szene.py` | mittel |
| Der Wandler als Bauplan + Module | `wandler.py` | mittel |
| Modulschacht-Benutzung | `wandler.py` | mittel |
| Lauf-Spielstand (was bleibt, was nicht) | `spielstand.py` | mittel |
| Kartenpruefung | `tests/` | mittel |

### 10.4 Was wirklich teuer ist - und die Empfehlung dazu

| Was | Warum teuer | Empfehlung |
| --- | --- | --- |
| **Fahr-Modus mit echter Physik** | zweites Bewegungssystem, zweite Kollision, zweiter Kameramodus | **Erst spaeter, und vielleicht nie.** Siehe unten. |
| Bewegliche Kacheln (Weg B) | bricht das Kachelraster ueberall | nein |
| Gegner, die Ebenen wechseln | Wegfindung ueber Treppen | machbar, aber nach hinten |
| Echte Kartenerzeugung | Qualitaet schwer zu sichern | Stufe 3, nur wenn noetig |

**Zum Fahr-Modus, ehrlich:** Das Menue verspricht ihn (`FAHRT`, `DREHEN`,
`BOOST`, `AUTOPILOT`). Ein zweites vollwertiges Bewegungssystem ist aber der
teuerste Posten im ganzen Plan, und er bringt spielerisch am wenigsten -
Fahren zwischen Knoten ist Transport, und Transport ist selten das, wofuer
man ein Spiel startet.

**Vorschlag:** Die Fahrt ist zunaechst **die Sektorkarte in Bewegung** - man
waehlt ein Ziel, der Wandler zieht sichtbar ueber die Karte, unterwegs
koennen Ereignisse kommen (Ueberfall, Fund, Funkspruch). Man ist dabei **an
Bord und darf herumlaufen**: auf die Bruecke zum Kartentisch, nach unten zur
Werkstatt. Das nutzt alles, was schon da ist, und gibt der Fahrt trotzdem
Gegenwart.

Ein echter Fahr-Modus mit Lenkung kann spaeter darauf gesetzt werden, ohne
dass etwas umgebaut werden muss - oder er faellt weg, und niemand vermisst
ihn. Wenn er wegfaellt, gehoeren die Zeilen aus der Menue-Steuerungstabelle
entfernt, damit das Menue nichts verspricht, was es nicht gibt.

---

## 11. Reihenfolge der Umsetzung

Jeder Meilenstein ist **fuer sich spielbar und fuer sich testbar**. Nach
jedem laeuft das Spiel, beide Testlaeufe sind gruen, und es gibt etwas Neues
zu sehen. Kein Meilenstein laesst das Spiel in einem halben Zustand.

Versionsnummern nach dem Schema im README (neue Sache = MINOR hoch).

### M1 - Karten kommen aus Dateien (0.12.0)

*Ziel:* `testkarte()` ist nicht mehr die einzige Karte.

* `karten/` mit Textdateien, eine Datei je Ebene oder eine mit Trennzeilen
* `Welt.aus_datei(name)`
* Marken (`R`, `S`, `W`, `1`-`9`) mit `ebene.marken`
* Der Spieler startet auf der Marke `S` statt auf einem Zufallspunkt
* Test: jede Karte im Ordner laedt, hat eine Startmarke, jede Ebene ist
  von dort erreichbar

*Warum zuerst:* Ohne das ist jeder weitere Schritt eine Code-Aenderung.
Danach ist ein neuer Ort eine Textdatei.

### M2 - Mehrere Orte, ein Ortstyp mehr (0.13.0)

* Drei bis vier handgetippte Wrackfelder
* Ein Vorposten mit Wachtuermen
* Beim Start wird zufaellig einer gewaehlt
* Hauptbeute als Marke, erzwingt einen Ebenenwechsel

*Sichtbar:* Es ist nicht mehr jedes Mal dieselbe Karte.

### M3 - Der Wandler als Ort (0.14.0)

* `wandler.py`: Bauplan aus Text, drei Decks
* `Ebene.stempeln()`
* Der Wandler wird an der Marke `R` in die Ortskarte gestempelt
* Man kann hinein, hoch, runter, wieder hinaus - nahtlos
* Noch keine Module, nur Raeume

*Sichtbar:* Man hat ein Zuhause, und es steht wirklich in der Welt.
*Das ist der Meilenstein, der das Spiel veraendert.*

### M4 - Module und Schaechte (0.15.0)

* Modulliste in `config.py`
* Leere Schaechte auf E1, sichtbar leer
* Zwei bis drei Module einbaubar (Lager, Kojen, Werkbank)
* Energie als Budget
* Bauen mit B an einem Schacht

*Sichtbar:* Schrott hat zum ersten Mal einen Zweck.

### M5 - Die Sektorkarte (0.16.0)

* `sektor.py`: Graph, 14-20 Knoten, 6-8 Spalten
* Sektorkarte als Szene, aufgerufen vom Kartentisch auf E2
* Ein Knoten waehlen, hinfahren, dort ist der Ort
* Noch keine Front

*Sichtbar:* Aus einzelnen Orten wird eine Reise.

### M6 - Die Front (0.17.0)

* `FRONT` in `config.py`
* Die Front rueckt je Etappe
* Ueberrollt werden beendet den Lauf
* Anzeige auf der Sektorkarte

*Sichtbar:* Das Spiel hat einen Motor. Der Titel erklaert sich.

### M7 - Der Lauf als Ganzes (0.18.0)

* Lauf-Spielstand: was bleibt (Wissen), was nicht (Wandler)
* Sektorausgang, dann naechste Region
* EISERN wird das, was es verspricht

### M8 - Ortsvielfalt (0.19.0)

* Chorturm (5 Ebenen, hoch), Trichter (5 Ebenen, runter), Freie Werft
* Bausteine statt ganzer Karten
* Kartenpruefung im Test

### M9 - Erzaehlung (0.20.0)

* Terminals
* Funkbruchstuecke
* Spuren im Wandler

**Nach M9 ist das Spiel von vorn bis hinten spielbar.** Damit stellt sich
die erste Frage aus dem Versionsschema, und es wird `1.0.0`.

---

## 12. Offene Fragen - hier entscheidet Der Meister

Bewusst nicht entschieden. Jede Antwort aendert Teile des Plans.

1. **Fahr-Modus:** Reicht "Fahrt als Sektorkarte in Bewegung, man laeuft an
   Bord herum" (Abschnitt 10.4)? Oder soll es echtes Lenken geben? *Das ist
   die teuerste Frage im Dokument.*

2. **Roguelite oder Kampagne:** Beginnt man nach einem Verlust von vorn (mit
   bleibendem Wissen), oder gibt es Speicherstaende? Das Menue kennt
   "fortsetzen" und EISERN kennt "ein leben" - beides ist moeglich, aber es
   sollte eines sein.

3. **Wie viel Tod:** Ist der Spieler zerbrechlich (drei Treffer) oder zaeh?
   Heute: 100 Leben, Laeufer macht 9. Das ist zaeh. Passt das zum Ton?

4. **Gegner auf anderen Ebenen:** Sollen Gegner Treppen benutzen und einen
   verfolgen? Das macht Ebenen gefaehrlicher, aber auch anstrengender.

5. **Ist der Chor feindlich?** Oder gleichgueltig, solange man nicht stoert?
   Die zweite Antwort ist interessanter und billiger zu bauen.

6. **Ende:** Was steht am Ende der Chorwerk-Ruine? Ohne Antwort bleibt der
   Bogen ein Rahmen.

---

## 13. Was dieses Dokument bewusst nicht tut

* Es legt keine Kachelzeichen fest, die noch nicht gebraucht werden.
* Es schreibt keine Dialoge.
* Es nennt keine Balancewerte ausser als Beispiel - die gehoeren in
  `config.py`, und zwar erst, wenn sie gemessen sind.
* Es entscheidet nichts, was in Abschnitt 12 steht.

**Wer hier weitermacht:** Nimm den naechsten Meilenstein aus Abschnitt 11.
Lies vorher Abschnitt 3 ganz. Halte dich an die drei Regeln aus dem README
("Wie sich das Spiel anfuehlen soll"). Wenn ein Meilenstein etwas verlangt,
was Abschnitt 12 offen laesst, frag nach, statt zu raten.
