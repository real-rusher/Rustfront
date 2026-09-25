# DUSTFRONT - Der Weltenplan

**Was das hier ist.** Der vollstaendige Entwurf, wie DUSTFRONT am Ende
aufgebaut sein soll: vom Kontinent ueber das Gefecht zweier Wandler bis zur
einzelnen Kachel an Bord. Nichts davon ist gebaut. Dieses Dokument sagt,
*was* gebaut wird, *warum* es so und nicht anders, und *in welcher
Reihenfolge*.

**Fuer wen.** Fuer Der Meister, und fuer jede Claude-Instanz, die spaeter
gesagt bekommt "mach mit dem Kartenplan weiter". Wer hier anfaengt, liest
zuerst Abschnitt 0, 1 und 2, dann Abschnitt 5 ganz, dann den Meilenstein,
der dran ist.

**Stand beim Schreiben:** Hauptzweig 0.15.0, PRE-ALPHA, naechste freie
Nummer **0.20.0**. Der Spielkern steht (feste Zeitschritte, drei Ebenen,
sechs Waffen, Inventar, Menues, Texturen aus Dateien). Es gibt genau eine
Karte: `testkarte()` in `world.py`. Zwischendurch ist ein Mehrspieler
entstanden, der als Test abgeschlossen auf `multiplayer-test` liegt und die
Nummern 0.16.0 bis 0.19.1 verbraucht hat.

> ### Achtung: Diese Fassung ist eine Korrektur
>
> Die erste Fassung dieses Dokuments hat das Spiel **falsch verstanden**.
> Sie beschrieb einen Einzelspieler, der von Ort zu Ort faehrt, dort zu
> Fuss kaempft, und dazwischen in seinem Wandler wohnt - der Wandler war
> darin ein Zuhause unter mehreren Schauplaetzen, und das Fahren war ein
> Kostenposten, den man am besten streicht.
>
> **Das ist es nicht.** DUSTFRONT ist ein **Mech-Kampfspiel**. Der riesige
> Wandler *ist* die Basis, und er ist gleichzeitig das, womit gekaempft
> wird. Abschnitt 1 zaehlt auf, was daraus folgt, und was von der alten
> Fassung uebrig bleibt.

> ### Die Rangfolge, festgelegt von Der Meister
>
> **Zuerst die Grundmechanik, und jedes System einzeln funktionsfaehig.**
> Front, Fraktionen mit eigenen Prioritaeten, Missionen, eine konkrete
> Karte und eine Geschichte mit verschiedenen Enden sind *ambitioniert und
> nicht die Prioritaet* - sie kommen, wenn alles andere laeuft.
>
> Begruendung von ihm, und sie ist richtig: ob der eigene Wandler gegen
> einen KI-Wandler oder gegen den eines anderen Spielers faehrt, ist
> hinterher **umbaubar**. Eine Geschichte laesst sich auf ein
> funktionierendes Gefecht aufsetzen; ein Gefecht laesst sich nicht auf
> eine Geschichte aufsetzen.
>
> Was von der Front jetzt schon gebraucht wird, ist **nicht der Bau,
> sondern der Nachweis, dass sie spaeter ohne Umbau hineinpasst.** Der
> steht in Abschnitt 9.4 als Liste von Bedingungen, die die Meilensteine
> M1 bis M8 einhalten muessen.
>
> Die Abschnitte 9 bis 11 (Veld, Front, Fraktionen, Regionen,
> Progression, Erzaehlung) bleiben deshalb im Dokument, sind aber
> **Fernziel**, nicht Arbeitsauftrag. Sie stehen da, damit niemand die
> Grundmechanik so baut, dass sie spaeter im Weg steht.

---

## 0. Wie dieses Dokument zu benutzen ist

Es geht **von grob nach fein**. Wer nur einen Ueberblick braucht, liest 1
bis 4. Wer baut, liest 5 ganz und springt dann zu Abschnitt 13
(Meilensteine).

Vier Arten von Aussagen, immer unterscheidbar:

| Zeichen | Bedeutung |
| --- | --- |
| **FEST** | Steht schon im Code oder folgt zwingend daraus. Nicht verhandelbar, ohne Bestehendes umzubauen. |
| **ENTWURF** | So ist es gedacht. Begruendet, durchgerechnet, aber aenderbar. |
| **OFFEN** | Bewusst nicht entschieden. Steht in Abschnitt 14, Der Meister entscheidet. |
| **KORREKTUR** | Stand in der ersten Fassung anders. Hier steht, was falsch war. |

**Abschnitt 14 ist der wichtigste fuer Der Meister.** Er trennt vollstaendig,
was von ihm kommt (14.1) von dem, was Claude vorgeschlagen hat, und sortiert
Letzteres danach, **was es kostet, es spaeter zu aendern**: sechs
Entscheidungen, die jetzt zaehlen (Topf A), zehn, die am Meilenstein
gemessen werden (Topf B), Kosmetik, die niemand vorab entscheiden muss
(Topf C), und das geparkte Fernziel (Topf D).

**Die eiserne Regel dieses Plans:** Nichts in diesem Dokument darf
erzwingen, dass der Spielkern umgebaut wird. Wo ein Entwurf das verlangen
wuerde, steht ausdruecklich dabei, was genau sich aendern muss und warum es
sich lohnt. Jede solche Stelle ist in Abschnitt 12 aufgelistet.

---

## 1. Was falsch verstanden war

**KORREKTUR.** Fuenf Punkte, vom groessten abwaerts. Jeder zieht einen Teil
des alten Plans mit sich.

### 1.1 Der Wandler ist die Basis, nicht ein Ort unter vielen

Alt: drei Massstaebe - Kontinent, Ort, Wandler - und der Wandler war der
dritte, das Zuhause zwischen den Einsaetzen.

Richtig: **Der Wandler ist der Mittelpunkt.** Er ist Basis, Fahrzeug,
Waffenplattform und Lager in einem Stueck. Alles andere ordnet sich ihm
unter: der Boden ist das, worueber er laeuft, Veld ist das, wohin er laeuft,
und der Gegner ist in erster Linie **ein zweiter Wandler**.

### 1.2 Die Ebenen sind die Etagen des Wandlers

Alt: Ebenen waren Stockwerke von Ruinen, Kraterwaende, Turmgeschosse.

Richtig: **Die Hoehenebenen gibt es, weil der Wandler Etagen hat.** Unten
der Boden, darueber die Decks. Das war von Anfang an der Zweck der
teuersten Mechanik im Spiel, und der alte Plan hat sie fuer Kulisse
ausgegeben. Wie viele Decks ein Rumpf hat, entscheidet seine Bauklasse -
vom Warhound bis zum Emperor-Titan (Abschnitt 5.4).

### 1.3 Steuern ist der Hauptmodus, nicht der teuerste Fehler

Alt, Abschnitt 10.4 der ersten Fassung: *"Ein zweites vollwertiges
Bewegungssystem ist der teuerste Posten im ganzen Plan, und er bringt
spielerisch am wenigsten."* Es folgte der Vorschlag, den Fahr-Modus
vielleicht nie zu bauen und die Zeilen `FAHRT`, `DREHEN`, `BOOST`,
`AUTOPILOT` aus dem Menue zu entfernen.

Richtig: **Man steuert primaer den Wandler.** Diese Zeilen im Menue sind
kein Altlast-Versprechen, sie sind die Beschreibung des Spiels. Sie stehen
seit 0.1.0 da und waren die ganze Zeit der deutlichste Hinweis im Repo.

Und: es braucht *kein* zweites Bewegungssystem. Siehe Abschnitt 6.1 - der
Trick ist, dass der Spieler nie aufhoert, eine laufende Figur zu sein.

### 1.4 Der Kampf hat zwei Massstaebe gleichzeitig

Alt: Kampf war Kampf zu Fuss, Gegner waren Wellen von Laeufern.

Richtig: Zwei Wandler beschiessen sich, **waehrend** ihre Besatzungen zu
Fuss auf den Decks stehen. Man stellt den Kurs auf Autopilot, legt die
Waffensysteme auf den anderen Wandler fest, und geht dann selbst nach
unten, um eine **Enterung** abzuwehren - oder um den anderen Wandler zu
entern. Das Gefecht zu Fuss, das der Spielkern heute schon kann, findet
*auf* den Maschinen statt, nicht neben ihnen.

### 1.5 Absteigen ist eine Entscheidung, keine Reise

Alt: Man faehrt zu einem Ort, parkt, steigt aus, der Ort ist die Mission.

Richtig: Man steigt ab, **waehrend der Wandler weiterlaeuft oder wartet** -
um Gebaeude im Wasteland zu pluendern. Das ist ein Risiko, kein
Ortswechsel: unten ist man allein, oben laeuft die Maschine ohne Fuehrer,
und man muss zurueck, bevor etwas passiert.

### 1.6 Was von der alten Fassung bleibt

Nicht alles war falsch. Diese Teile sind uebernommen, teils umgebaut:

| Bleibt | Wie es jetzt steht |
| --- | --- |
| Karten sind Text, Marken in der Karte | unveraendert, Abschnitt 5.6 - jetzt noch wichtiger, weil auch Wandler Textkarten sind |
| Keine beweglichen Kacheln | unveraendert, Abschnitt 5.2 - der Grund ist jetzt ein anderer |
| Module als begehbarer Fortschritt | Abschnitt 6.5, praktisch unveraendert. Die staerkste Idee der alten Fassung. |
| Veld als Knotengraph | Abschnitt 9, gekuerzt. Die Fahrt dazwischen ist jetzt Spiel, nicht Transport. |
| Die vorrueckende Front | Abschnitt 9.2, unveraendert und jetzt besser begruendet |
| Drei Fraktionen, drei Regionen | Abschnitt 10, auf Wandler umgestellt |
| Erzaehlen ohne Dialogsystem | Abschnitt 11.4, unveraendert |

| Faellt weg | Warum |
| --- | --- |
| "Der Wandler wird in den Ort gestempelt" als Grundlage | Der Wandler steht nicht in einer fremden Karte, er *ist* die Karte. Das Stempeln bleibt als Sonderfall fuers Andocken, Abschnitt 5.2. |
| "Drei Massstaebe" in der alten Reihenfolge | ersetzt durch Abschnitt 4 |
| Ortstypen als Hauptinhalt (Chorturm, Trichter, Silo) | verschoben. Erst der Wandler, dann die Orte. Abschnitt 13. |
| Der Vorschlag, den Fahr-Modus zu streichen | falsch, siehe 1.3 |

---

## 2. Das Vorbild: SAND: Raiders of Sophie

Der Meister hat es als Inspiration genannt. Hier steht, was es ist, damit
niemand raten muss - **und vor allem, was DUSTFRONT anders macht.**

### 2.1 Was SAND ist

Ein Dieselpunk-Extraction-Shooter von Hologryph und TowerHaus, Ego-Sicht,
seit Juni 2026 im Early Access. Spielort ist der ausgetrocknete Planet
**Sophie** in einem alternativen 1910. Man baut, ruestet und steuert eine
riesige Laufmaschine, den **Trampler**, entworfen nach Baufahrzeugen der
1870er mit angesetzten Klappbeinen.

Was daran zaehlt, in Stichpunkten:

* Der Trampler ist **nicht ein Fahrzeug, sondern die Festung**: Transport,
  Lager, Schutz und Waffenplattform zugleich.
* Er wird aus **Bauteilen** zusammengesetzt - Motoren, Reaktoren, Lager,
  Einstiegspunkte, Waffen - und als Bauplan gespeichert, um ihn nach einem
  Verlust neu zu bauen. Es gibt Gewichtsklassen: leicht und schnell,
  schwer und gepanzert.
* Eine Besatzung von bis zu fuenf Spielern teilt sich die Arbeit: *"einer
  kuemmert sich um den Motor, einer steuert, einer repariert, die beiden
  anderen bedienen die Kanonen."* Allein zu spielen ist moeglich, aber
  ueberfordernd.
* **Kritische Bauteile:** Reaktor, Beine, Schwungrad, Kapitaenskajuete.
  Das Schwungrad macht die Lenkung - ist es hin, verliert man die
  Richtungskontrolle. Beine werden im Stehen repariert.
* **Entern:** Wer die Tuer sprengt und an Bord kommt, uebernimmt die
  Maschine.
* Man steigt ab, um **Ruinen, Staedte, Schiffswracks** zu pluendern, und
  faehrt mit der Beute zu einem Funkturm, um sich ausfliegen zu lassen.
  Das Aktivieren warnt alle in der Naehe.
* Gegner sind KI-Kreaturen (**Upiors**), rivalisierende Besatzungen und
  Sandstuerme.

*Nicht verlaesslich gefunden:* wie der Innenraum in Etagen aufgeteilt ist,
ob es einen Autopiloten gibt und wie genau die Waffen festgelegt werden.
Die Fundstellen schweigen dazu. Wo dieser Plan solche Dinge festlegt, ist
es eigene Erfindung und als ENTWURF markiert, nicht als Nachbau.

### 2.2 Was DUSTFRONT uebernimmt

1. **Die Maschine ist die Basis.** Der eine Satz, um den sich alles dreht.
2. **Kritische Bauteile statt eines Lebensbalkens.** Ein Treffer nimmt dir
   nicht Zahlen weg, sondern eine Faehigkeit - die Lenkung, ein Geschuetz,
   das Licht. Das ist unendlich viel besser lesbar als ein Balken, und es
   kostet im Kachelspiel fast nichts (Abschnitt 6.6).
3. **Entern.** Der Moment, in dem Maschinenkampf und Fusskampf dasselbe
   Gefecht werden.
4. **Absteigen als Risiko.**
5. **Arbeitsteilung als Spannungsquelle** - siehe naechster Punkt, aber
   mit umgekehrtem Vorzeichen.

### 2.3 Was DUSTFRONT ausdruecklich anders macht

**"Das moechte ich quasi in 2D mit einem radikal anderen Vibe nachbauen."**
Also, Punkt fuer Punkt:

| SAND | DUSTFRONT |
| --- | --- |
| Ego-Sicht, 3D | **90-Grad-Draufsicht, 2D, Kachelwelt.** Man sieht den ganzen Wandler auf einmal - das ist keine Einschraenkung, das ist ein anderes Spiel. Man sieht die Enterer kommen. |
| Besatzung aus fuenf Spielern | **Ein Spieler.** Allein sein ist nicht das Problem, sondern das Thema - siehe 6.3. |
| PvPvE, Extraction, andere Spieler als Hauptgefahr | **Einzelspieler.** Der zweite Wandler ist KI. Der Mehrspieler liegt abgeschlossen auf `multiplayer-test` und kommt hier nicht vor. |
| Alternatives 1910, Dieselpunk, Sandplanet | **Veld, Staub und Schrott, drei Fraktionen.** Kein Dieselpunk-Messing, sondern Rost, Blech und Asche. Das steht schon im README und aendert sich nicht. |
| Offene Welt, prozedurale Duenen | **Knotengraph mit vorrueckender Front.** Entscheidung statt Weite, Abschnitt 9. |
| Verlieren heisst Beute weg | **Verlieren heisst der Wandler weg** - bei EISERN endgueltig. Das Menue sagt das schon: *"ein wandler, ein leben."* |

**Der wichtigste Unterschied ist der Blickwinkel.** In SAND weiss man nie
genau, was auf dem eigenen Deck los ist. In DUSTFRONT sieht man es -
und kommt trotzdem nicht rechtzeitig hin. Das ist eine andere Art von
Druck, und sie passt zu einem Spiel, dessen Kernversprechen *"nichts
springt, nichts sperrt"* ist.

---

## 3. Was schon feststeht

Geerntet aus dem, was im Repo liegt. Das ist kein Vorschlag, das ist
Bestandsaufnahme - der Plan muss dazu passen, nicht umgekehrt.

### 3.1 Aus dem README

* Kontinent **Veld**. Top-Down-Ansicht, 90 Grad von oben.
* Der Spieler steuert einen **modularen Wandler** und **baut ihn aus
  Schrott weiter aus**.
* Drei Fraktionen: **die Kolonne**, **der Chor**, **die Freien Werften**.
* **Zwei Spielmodi**, die sich dieselbe Ansicht teilen: *an Bord* und
  *Fahr-Modus*, gewechselt mit Tab.

Der letzte Punkt ist die Kurzfassung des ganzen Spiels und stand die ganze
Zeit im ersten Absatz.

### 3.2 Aus `rustfront_menu.py`

Das Hauptmenue weiss schon mehr ueber das Spiel als das Spiel selbst.
Diese Zeilen sind bindend, weil sie dem Spieler bereits etwas versprechen:

```python
REGIONEN = [
    ("ASCHEWALD",      "sektor 12. viel schrott, wenige patrouillen. der ruhige einstieg.",
     {"KOLONNE": 0.3,  "CHOR": 0.15, "WERFTEN": 0.7}),
    ("TRICHTERFELD",   "dichte kolonne-verbaende, dafuer schwere module im wrackfeld.",
     {"KOLONNE": 0.85, "CHOR": 0.25, "WERFTEN": 0.35}),
    ("CHORWERK-RUINE", "der chor sendet noch. beste technik, kaum ueberlebende.",
     {"KOLONNE": 0.2,  "CHOR": 0.9,  "WERFTEN": 0.2}),
]
```

Die Steuerungstabelle im Menue nennt Aktionen, die es im Spiel noch nicht
gibt. **Sie sind damit als Absicht dokumentiert, und sie beschreiben genau
das Spiel aus Abschnitt 1:**

| Taste | Aktion | Gibt es? | Was es bedeutet |
| --- | --- | --- | --- |
| TAB | MODUS WECHSELN | nein (Tab ist heute Inventar) | zwischen "an Bord" und "Fahrt" |
| W / S | FAHRT | nein | Schub am Steuerstand |
| A / D | DREHEN (FAHRT) | nein | Kurs am Steuerstand |
| SHIFT | BOOST | teilweise (Sprint) | Ueberlast, Abschnitt 6.2 |
| H | AUTOPILOT | nein (H ist heute Medkit) | **der Schluessel zum ganzen Spiel**, Abschnitt 6.3 |
| B | BAUEN | nein | Module und Reparatur |
| Q | WERKZEUG | nein | Schweissgeraet, Abschnitt 6.6 |

Ausserdem: `sector_preview()` zeichnet bereits eine **Sektorkarte aus acht
Knoten**, verbunden durch gestrichelte Linien, jeder Knoten in einer
Fraktionsfarbe. Der Spielstand kennt `region`, `difficulty`, `callsign`.
Die Schwierigkeit **EISERN** ist beschrieben als *"ein wandler, ein leben.
kein laden nach dem verlust."* - und das ergibt erst jetzt seinen vollen
Sinn.

### 3.3 Aus dem Spielkern

* **FEST:** Eine `Welt` ist eine Liste von `Ebene`n. Eine `Ebene` ist ein
  Kachelgitter mit einem Index. Jedes Wesen gehoert zu genau einer Ebene.
* **FEST:** Karten sind **Text**. Ein Zeichen ist eine Kachel
  (`ZEICHEN` in `world.py`). `Ebene.aus_text()` baut daraus ein Gitter.
* **FEST:** `EBENEN_HOEHE = [0, 118, 182, 238, 288]` - fuenf Hoehen sind
  vorgesehen, drei werden benutzt. Der Abstand entscheidet ueber Sturzdauer,
  Fallschaden und wie klein die untere Ebene gezeichnet wird. Gelesen wird
  die Tabelle an **genau einer** Stelle, in `Welt.hoehe()`; alles andere
  ruft diese Methode. Deshalb kann jeder Rumpf spaeter seine eigene
  Hoehenstaffel bekommen, ohne dass etwas umgebaut wird (5.4).
* **FEST:** Ein Sturz laeuft ohne Ruck: die Figur bleibt stehen, die Welt
  waechst unter ihr heran, und man kann in der Luft noch steuern.
* **FEST:** Alle Zahlen in `config.py`. Jedes Bild durch eine Datei
  ersetzbar. Jeder Klang auch.
* **FEST:** Das HUD zeigt bereits **SCHROTT** als Zaehler.

### 3.4 Was der Name sagt

**DUSTFRONT.** Eine *Front* aus Staub. Kein Ort, sondern eine Linie, die
sich bewegt - und jetzt auch: zwei Maschinen, die sich an dieser Linie
begegnen. Der Motor der Karte ist die vorrueckende Front (Abschnitt 9.2).

---

## 4. Die Massstaebe

```
    VELD              Der Kontinent. Knotengraph, keine Kacheln.
    (Strategie)       Zeitskala: Etappen. Hier entscheidet man WOHIN.
        |             Die Front rueckt nach.
        |
        v
    DIE FAHRT         Der Wandler laeuft. Man ist an Bord, an einer Station,
    (Hauptmodus)      oder unterwegs zwischen den Decks.
        |             Zeitskala: Minuten. Hier passiert das Gefecht.
        |
        +-----------------+--------------------+
        |                 |                    |
        v                 v                    v
    DAS DUELL         DIE ENTERUNG          DER BODEN
    (Wandler          (Fussgefecht          (absteigen, Gebaeude
     gegen Wandler)    auf den Decks)        pluendern, Abschnitt 8)
```

**Der Unterschied zur alten Fassung:** Die Fahrt ist nicht mehr der
langweilige Strich zwischen zwei Schauplaetzen, sondern der Ort, an dem
alles passiert. Veld sagt nur noch, *in welche Richtung* gelaufen wird und
wie viel Zeit bleibt.

**Das Versprechen an den Spieler**, in einem Satz je Massstab:

* *Veld:* "Ich komme nicht ueberall hin. Ich muss waehlen."
* *Die Fahrt:* "Ich kann nicht an zwei Stellen gleichzeitig sein."
* *Der Wandler:* "Das hier ist meins, und es wird besser."
* *Der Boden:* "Wenn ich zu lange brauche, ist sie weg."

---

## 5. Die eine technische Grundlage

Dieser Abschnitt ist der wichtigste des Dokuments. Wer ihn ueberspringt,
baut spaeter dreimal dasselbe - oder baut sich den Kern kaputt.

### 5.1 Jeder Rumpf ist eine eigene `Welt`

**ENTWURF, und zwar der harte, an dem alles haengt:**

> Der eigene Wandler ist eine `Welt`. Der gegnerische Wandler ist eine
> `Welt`. Der Boden ist eine `Welt`. Alle drei benutzen denselben
> Renderer, dieselbe Kollision, dieselben Treppen, dieselben Stuerze.
> Ein Wesen gehoert zu genau einer Welt und darin zu genau einer Ebene.

**Warum das der entscheidende Griff ist.** Die naheliegende Frage lautet:
"Wie bewege ich eine Maschine aus Kacheln durch eine Kachelwelt?" Darauf
gibt es keine billige Antwort (siehe 5.2). Die richtige Frage lautet:

> **Wer auf dem Deck steht, fuer den bewegt sich das Deck nicht.**

Alle Koordinaten an Bord sind **relativ zum Rumpf**. Der Wandler bewegt
sich nicht *in* einer Welt - er *ist* eine, und was sich bewegt, ist eine
einzige Zahl: seine Position auf Veld. Diese Zahl wird gebraucht fuer

* den Hintergrund, der unter den Beinen durchzieht (Parallaxe, reine
  Anzeige),
* den Abstand zum anderen Wandler (entscheidet ueber Waffenreichweiten),
* die Frage, ob die Rampe unten ankommt und ob geentert werden kann.

**Was daraus folgt:** `frei()`, `strahl()`, `bewegen()`, `ebene_zeichnen()`
und `Welt.schritt()` bleiben **unveraendert**. Kein einziger Aufruf im
Spielkern muss wissen, dass die Maschine laeuft. Das ist der Grund, warum
ein Mech-Kampfspiel in diesem Kern ueberhaupt machbar ist.

### 5.2 Die drei Wege, und warum es Weg A wird

**Weg A - jeder Rumpf eine eigene Welt, verbunden durch Uebergaenge.**
Empfohlen. Kosten: eine Liste von Welten statt einer, ein Versatz je Welt
beim Zeichnen, und eine Handvoll Uebergaenge (5.3). Der Kern bleibt, wie er
ist.

**Weg B - der Wandler faehrt als bewegliches Kachelfeld durch eine grosse
Bodenwelt.** *Kosten: sehr hoch.* Bewegliche Kacheln bedeuten, dass
Kollision, Sichtlinien und das Kachelraster nicht mehr an ganzen
Kachelkoordinaten haengen duerfen. *Preis:* Monate, und ein Kern, der nicht
mehr einfach ist. **Nein.** (Das war in der alten Fassung schon die
Antwort, aus demselben Grund.)

**Weg C - der Wandler wird beim Ankommen in eine Ortskarte gestempelt.**
Das war die Empfehlung der alten Fassung. Sie setzt voraus, dass der
Wandler **steht**, und faellt damit als Grundlage aus - ein Wandler, der
nur im Parken begehbar ist, ist kein Mech-Kampfspiel.

**Aber:** Weg C bleibt als **Sonderfall** nuetzlich, naemlich ueberall dort,
wo der Wandler wirklich haelt - beim Andocken an eine Freie Werft, bei
einer Reparaturpause, am Sektorausgang. Dann wird der Rumpf an einer Marke
in die Bodenkarte gestempelt und man laeuft nahtlos hinaus. Eine Funktion
`stempeln(welt, bauplan, tx, ty)`, mehr nicht. **Spaeter, nicht zuerst.**

### 5.3 Uebergaenge: derselbe Griff wie eine Treppe

Ein **Uebergang** verbindet zwei Welten, genau so wie eine Treppe zwei
Ebenen verbindet. Der Code dafuer existiert bereits im Prinzip - ein
Ebenenwechsel setzt Ebene und Position neu, ein Weltwechsel setzt Welt und
Position neu. Ein Feld mehr.

| Uebergang | Von | Nach | Bedingung |
| --- | --- | --- | --- |
| **Rampe** | eigenes Unterdeck | Boden | Wandler steht oder geht Schritttempo |
| **Enterbruecke** | eigenes Deck | fremdes Deck | Abstand unter `ENTERN["weite"]`, Bruecke ausgefahren |
| **Enterhaken** | fremdes Deck | eigenes Deck | dasselbe, von der Gegenseite |
| **Sturz** | jedes Deck | Boden | Fehltritt ueber die Kante - kein Uebergang, sondern ein Sturz |

Der letzte ist der wichtigste und kostet **null neuen Code**: Wer ueber die
Kante des Oberdecks geht, faellt. Der Sturz mit Steuerung in der Luft steht
seit 0.11.0. Was neu dazukommt, ist die Pointe - **unten ist der Boden, und
der Wandler laeuft weiter.** Man landet hinter der eigenen Maschine und
sieht sie davonlaufen. Das ist ein ganzer Spielmoment fuer den Preis einer
Zeile.

**Sichtlinien zwischen Welten:** Ein Uebergang ist nur begehbar, wenn beide
Seiten nah genug sind. Sichtlinien und Schuesse gehen ueber 5.5.

#### Die Probe aufs Exempel (A1)

Der Meister hat genau die richtige Frage gestellt: *"Waere sowas wie zwei
Mechs nebeneinander parken und von einem zum anderen springen, oder
zumindest Einschlaege von Waffen auf anderen Mechs plus Kills von Entities
auf anderen Mechs sehen, dann moeglich?"*

Das ist der Test, ob 5.1 taugt. **Antwort: ja, beides - und das Zweite ist
fast geschenkt.**

**Sehen, was auf dem anderen Rumpf passiert.** Jede Welt wird mit ihrem
eigenen Bildversatz gezeichnet (`Versatz = Rumpfposition - Kamera`). Was auf
dem fremden Deck steht, faellt, blutet, explodiert oder stirbt, sind
schlicht die `wesen` und `partikel` jener Welt - gezeichnet an ihrem
Versatz, mit derselben Perspektive wie alles andere. **Man sieht einen
Enterer druben fallen, genau wie man ihn auf dem eigenen Deck fallen
sieht.** Es braucht dafuer keine Zeile Sonderlogik, nur die Schleife ueber
mehrere Welten statt ueber eine.

**Von Rumpf zu Rumpf springen.** Auch ja, und der Mechanismus dafuer ist
schon gebaut. Es gibt zwei Faelle:

* **Hinuebergehen** ueber Bruecke oder Steg: ein Uebergang wie oben. Eine
  Kachel betreten, Welt und Position wechseln. Trivial.
* **Wirklich springen**, also eine Luecke ueberwinden und dabei in der Luft
  sein: Genau das kann der Kern seit 0.11.0. Ein fliegendes Wesen (`w.flug`)
  wird **ausserhalb der Ebenenstruktur** gezeichnet, mit der Perspektive
  seiner eigenen Hoehe (`fliegende_zeichnen`, `_bildpunkt`), und man kann
  waehrend des Fluges noch steuern.

Der Sprung von Rumpf zu Rumpf ist also: beim Absprung wird die Figur ein
fliegendes Wesen mit **absoluter** Position (Bezugsrahmen ist die Bodenwelt,
die ohnehin der ruhende Rahmen ist). Beim Aufsetzen wird geprueft, welcher
Rumpf unter ihr steht, und sie wird in dessen Welt uebernommen - Position
zurueckgerechnet auf dessen Versatz. **Ein Rahmenwechsel beim Absprung und
einer beim Aufsetzen, sonst nichts.**

**Und das ergibt die beste Stelle im ganzen Entwurf**, ohne dass jemand sie
erfinden musste: Wenn sich die beiden Maschinen waehrend des Sprungs
gegeneinander bewegen, muss man **vorhalten**. Zieht der andere Rumpf weg,
waehrend man in der Luft ist, greift man ins Leere und faellt auf den Boden
- der Sturz mit Steuerung in der Luft, der schon da ist, mit einem Ausgang,
der schon da ist (8.2: die Maschinen laufen ohne einen weiter).

**Die eine Bedingung, die das erzwingt:** Der Versatz eines Rumpfes ist eine
**Kommazahl, keine Kachelkoordinate.** Er wird nur beim Zeichnen und beim
Umrechnen benutzt; kein Gitter verschiebt sich je gegen sein eigenes Raster.
Wesenpositionen sind ohnehin schon Kommazahlen, nur die Kacheln sind ganze
Zahlen - es aendert sich also nichts, was heute gilt.

### 5.4 Die Hoehenlage: beliebig viele Decks, ohne Umbau

**ENTSCHIEDEN von Der Meister (A4):** Es soll **grosse und kleine Wandler**
geben, orientiert an den Titanen aus Warhammer 40k - vom Warhound bis zur
Emperor-Klasse, jeder mit eigenen Vor- und Nachteilen, eigenem Spielgefuehl
und eigener Bedeutung in der Geschichte. Eine feste Obergrenze von vier
Decks ist damit hinfaellig.

**Das geht, und es ist billiger, als es klingt.** Der Nachweis, nachgesehen
im Code:

#### Warum es nur eine Stelle betrifft

`EBENEN_HOEHE` wird im ganzen Spiel an **genau einer** Stelle gelesen:

```python
# world.py
def hoehe(self, index: int) -> float:
    """Hoehe einer Ebene in Welt-Pixeln, aus der Tabelle in config."""
    i = max(0, min(len(K.EBENEN_HOEHE) - 1, index))
    return K.EBENEN_HOEHE[i]
```

Alles andere - `render.py` (Ebenenschleife und `fliegende_zeichnen`),
`entities.py` (Sturz), `play.py` (Blickhoehe) - ruft **`welt.hoehe(idx)`**
auf, nie die Tabelle direkt. Das ist schon heute eine Methode *an der Welt*.

**Daraus folgt:** Gibt jeder Rumpf sich seine eigene Hoehentabelle, folgen
Perspektive, Sturz, Blickhoehe und Zeichenreihenfolge automatisch. Das ist
ein Methodenkoerper, keine Umstellung. Weil ohnehin jeder Rumpf eine eigene
`Welt` ist (5.1), liegt die Tabelle genau dort, wo sie hingehoert.

#### Die Tabelle ist keine Liste, sondern eine Regel

Die fuenf Zahlen `[0, 118, 182, 238, 288]` sehen willkuerlich aus. Sind sie
nicht. Die Perspektive rechnet

```
    k = brennweite / (brennweite + dz)        brennweite = 430
    dz = Hoehe der Ansicht - Hoehe der Ebene
```

Steht man oben und misst, wie gross jede Ebene darunter erscheint:

| Ebene | Hoehe | k | Verhaeltnis zur Ebene darueber |
| --- | --- | --- | --- |
| 4 | 288 | 1.0000 | - |
| 3 | 238 | 0.8958 | 1.1163 |
| 2 | 182 | 0.8022 | 1.1167 |
| 1 | 118 | 0.7167 | 1.1194 |
| 0 | 0 | 0.5989 | **1.1967** |

**Die Decks stehen in einem konstanten Schritt von 0.895** - jedes Deck
erscheint genau 89,5 Prozent so gross wie das darueber. Der Boden faellt
bewusst aus der Reihe (1.1967 statt 1.116) und sitzt tiefer, damit er sich
deutlich von den Decks absetzt.

Damit laesst sich die Tabelle fuer **jede** Deckzahl erzeugen:

```
    deck_hoehe(n) = brennweite * (schritt**-n - 1)      schritt = 0.895
    n = wie viele Decks unter dem obersten

    n=0 ->    0      n=3 ->  170      n=6 ->  407
    n=1 ->   50      n=4 ->  240      n=8 ->  614
    n=2 ->  107      n=5 ->  319      n=9 ->  737
```

Die ersten Werte sind auf den Pixel die heutigen. **Ein Warhound mit drei
Decks und ein Emperor-Titan mit zehn sehen beide richtig aus**, ohne dass
jemand Zahlen von Hand sucht. `SCHRITT` und `BODEN_ABSTAND` kommen nach
`config.py`, die Tabelle wird je Rumpf daraus gerechnet.

#### Was gross und klein wirklich bedeutet

Drei Dinge folgen aus der Deckzahl von selbst, ohne eine Sonderregel:

1. **Lesbarkeit bleibt gleich.** `welt_zeichnen(..., blick=...)` zeigt
   hoechstens **eine** Ebene ueber der eigenen (gelernt im Mehrspieler). Man
   sieht also immer zwei Decks, egal ob der Rumpf drei oder zwoelf hat. Ein
   Emperor-Titan wird nicht unuebersichtlicher, er wird **unuebersehbar** -
   man kennt immer nur seine Umgebung.
2. **Der Sturz wird toedlich.** Vom obersten Deck eines Zehn-Deck-Titanen
   sind es rund 740 Pixel bis zum Boden, gut 1,2 Sekunden Fall. Fallschaden
   haengt schon heute an der Hoehendifferenz. Wer von einem Emperor-Titan
   faellt, stirbt - und das ist richtig.
3. **Und der wichtigste: Groesse kostet Anwesenheit.** Mehr Decks heisst
   laengere Wege zwischen den Stationen, und damit wiegt der Autopilot-Abzug
   aus 6.3 schwerer. **Genau das ist der Klassenunterschied, und er faellt
   umsonst an:**

| Klasse | Decks | Geschuetze | Spielgefuehl |
| --- | --- | --- | --- |
| **Warhound** | 2-3 | 1-2 | schnell, man schafft jede Station rechtzeitig. Wenig Platz, jeder Treffer sitzt. |
| **Reaver / Warlord** | 4-6 | 3-4 | der Standard. Man muss waehlen, wo man ist. |
| **Emperor-Klasse** | 8-12 | 8+ | eine laufende Festung, die man **nie ganz bedienen kann**. Ohne gute Autopilot-Module ist sie ein Riese mit verbundenen Augen. Entern ist hier die eigentliche Gefahr, nicht der Beschuss. |

Ein kleiner Wandler wird also **nicht** durch schlechtere Zahlen
ausgeglichen, sondern dadurch, dass man ihn ganz beherrscht. Das ist der
Unterschied in Spielgefuehl und Rolle, den Der Meister wollte, und er
entsteht aus zwei bereits getroffenen Entscheidungen statt aus einer neuen
Mechanik.

*Faellig:* in **M2**. Nachtraeglich waere es teuer, weil dann jede Karte und
jeder Bauplan auf fuenf feste Hoehen gebaut waere.

### 5.5 Schuesse zwischen Ruempfen

Ein Schuss, der eine Welt verlaesst, wird um den Versatz zwischen den
beiden Ruempfen verschoben und in der Zielwelt fortgesetzt. **Eine
Koordinatenverschiebung, keine neue Physik.**

```
    Weltversatz = Position(Rumpf B) - Position(Rumpf A)

    Treffer in B  <->  welt_B.treffer(punkt - versatz, radius, ebene, feind_von)
```

`Welt.treffer()` kennt bereits Fraktionen und ueberspringt die eigene Seite
- das stammt aus dem Mehrspieler und passt hier unveraendert.

#### Geschosse treffen beides (KORREKTUR, A5)

**ENTSCHIEDEN von Der Meister:** *"es soll sich ja so anfuehlen wie SAND,
also sollen Geschosse auf Mech- und Player-Ebene einschlagen."*

Eine fruehere Fassung dieses Abschnitts trennte die Massstaebe: Geschuetze
sollten nur Rumpfteile treffen, Handwaffen nur Figuren. **Das ist
gestrichen.** Ein Geschuetztreffer schlaegt ein - er beschaedigt das
Bauteil, das er trifft, *und* alles, was dort steht.

*Die Sorge dahinter war:* wenn Geschuetze Leute toeten, gewinnt man jedes
Duell aus der Ferne, und Entern passiert nie.

*Warum sie unbegruendet war:* Der Grund zu entern ist nicht, dass Geschuetze
keine Leute toeten koennen - **der Grund ist die Beute**, und die liegt an
Bord (7.1). Wer den fremden Rumpf leerschiesst, hat einen Gegner ohne
Besatzung und steht immer noch vor einer Maschine, in die er hineinmuss. Die
Regel, die das Entern traegt, stand also schon da; die Trennung war
ueberfluessig und haette das Spiel unglaubwuerdiger gemacht.

**Was stattdessen die Balance traegt - drei Regeln, alle physisch statt
willkuerlich:**

1. **Decks sind Deckung, das Oberdeck ist es nicht.** Wer unter einem Deck
   steht, ist vor Beschuss von oben und von der Seite geschuetzt. Das
   Oberdeck hat den besten Schussbereich und **keinen** Schutz. Damit ist
   die Wahl des Decks eine echte Abwaegung, und die offenen Kanten aus 6.4
   bekommen einen zweiten Zweck.
2. **Geschuetze sind Flaechenwaffen mit Flugzeit.** Sie treffen eine
   Gegend, nicht einen Kopf. Eine Besatzung gezielt wegzuschiessen ist
   moeglich, aber teuer und langsam - man zerlegt dabei genau die Bauteile,
   die man erbeuten wollte (7.5). **Wer nur schiesst, gewinnt arm.**
3. **Die eigene Maschine steht im Weg.** Wer vom Oberdeck schiesst, hat
   freie Bahn; wer vom Hauptdeck schiesst, schiesst in die eigene
   Aussenwand. Das deckt `strahl()` schon heute ab.

**Technisch ist das die einfachere Loesung**, nicht die aufwendigere: ein
Einschlag ruft einmal den Bauteilschaden (6.6) und einmal das bestehende
`welt.treffer()` auf. Zwei Zeilen, statt zweier getrennter Trefferwege.

### 5.6 Karten, Marken und Baustellen

Unveraendert aus der alten Fassung uebernommen, weil es dort richtig war
und jetzt noch mehr traegt: **ein Wandler ist auch nur eine Textkarte.**

```
ZEICHEN erweitern um Markierungszeichen, die beim Einlesen zu BODEN werden
und ihre Position in ebene.marken ablegen:

    "S"  ->  BODEN, marke "start"
    "R"  ->  BODEN, marke "rampe"
    "T"  ->  BODEN, marke "steuerstand"
    "G"  ->  BODEN, marke "geschuetz"
    "W"  ->  BODEN, marke "werkbank"
    "E"  ->  BODEN, marke "reaktor"
    "M"  ->  BODEN, marke "modulschacht"
    "1".."9" -> BODEN, marke "punkt1".."punkt9"
```

| Neu | Wofuer | Aufwand |
| --- | --- | --- |
| `Ebene.marken` | benannte Punkte aus der Karte | klein |
| `Welt.aus_datei(name)` | Welt aus Textdateien statt aus Konstanten | klein |
| `Welt.versatz` | wo dieser Rumpf gerade steht | klein |
| `Ebene.stempeln(zeilen, tx, ty)` | Sonderfall Andocken, 5.2 | klein |

Damit kann ein Kartenbauer - Mensch oder spaeter ein Generator - einen
Wandler **oder** einen Ort vollstaendig in Text beschreiben, ohne eine
Zeile Python. Das ist der Grund, warum das der erste Meilenstein bleibt.

### 5.7 Groessen, durchgerechnet

Bei 640x360 Bildpunkten und 32er Kacheln sieht man **20 x 11,25 Kacheln**
gleichzeitig.

| Was | Kacheln je Ebene | Bildschirme | Begruendung |
| --- | --- | --- | --- |
| Wandler, leicht | 14 x 9 | 0,7 x 0,8 | passt auf einen Bildschirm - man sieht alles |
| Wandler, mittel | 18 x 12 | 0,9 x 1,1 | knapp ein Bildschirm |
| Wandler, schwer | 24 x 14 | 1,2 x 1,2 | man muss laufen, um hinzusehen |
| Bodenausschnitt | 60 x 40 | 3 x 3,6 | so viel Wasteland, wie unter den Fuessen liegt |
| Obergrenze | 120 x 70 | 6 x 6 | nur mit Wegmarken sinnvoll |

**Die Wandlergroesse ist bewusst klein.** Ein Rumpf, der auf einen
Bildschirm passt, ist genau das, was der Top-Down-Blick hergibt: man sieht
den Enterer an der Bruecke, waehrend man unten am Reaktor steht, und weiss
sofort, dass man es nicht rechtzeitig schafft. Ein groesserer Rumpf gibt
diesen Blick auf, ohne etwas dafuer zu bekommen.

**Aufwand:** Messwert heute 3,9 ms pro Bild bei 51 Wesen auf 44x24x3. Drei
Welten gleichzeitig (eigener Rumpf, fremder Rumpf, Boden) mit zusammen rund
5 000 Kacheln je Ebene liegen darunter, weil der Zeichenaufwand am
Ausschnitt haengt und nicht an der Kartengroesse. **Machbar, mit Reserve.**

---

## 6. Der Wandler von innen

Hier entscheidet sich, ob das Spiel eine Seele hat.

### 6.1 Stationen statt Fahr-Modus

**ENTWURF, und die zweite tragende Entscheidung nach 5.1:**

> Der Spieler hoert nie auf, eine laufende Figur zu sein. Der Wandler wird
> **an Stationen** bedient. Eine Station ist eine Kachel mit einer Marke.
> Man stellt sich hin, drueckt E, und die Tasten bedeuten etwas anderes,
> solange man dort steht.

Damit gibt es **kein zweites Bewegungssystem, keine zweite Kollision,
keinen zweiten Kameramodus** - genau die drei Posten, die die alte Fassung
zu Recht als teuer ausgerechnet hat. Man loest sie, indem man sie nicht
baut.

`Spieler.nutzen` und `Spieler.abbrechen()` gibt es bereits. Eine Station
ist eine Zustandsvariable am Spieler und ein anderer Satz Tastenbelegungen
- weniger Code als eine einzige Waffe.

Und **TAB "MODUS WECHSELN"** bekommt dadurch eine billige, ehrliche
Bedeutung: die Ansicht springt zwischen "an Bord" (Kamera folgt der Figur)
und "Fahrt" (Kamera zeigt beide Wandler und den Boden). Eine Kameraoption,
kein Spielmodus.

### 6.2 Die Stationen

**ENTWURF.** Jede Station hat genau eine Aufgabe und liegt auf genau einem
Deck, damit man nie sucht.

| Station | Deck | Taste dort | Was sie tut | Was man dabei nicht kann |
| --- | --- | --- | --- | --- |
| **Steuerstand** | Bruecke | W/S Schub, A/D Kurs, SHIFT Ueberlast | Kurs und Tempo | schiessen, reparieren |
| **Geschuetz** | Oberdeck | Maus zielen, Klick feuern | Rumpfteile des Gegners zerlegen | irgendwo anders sein |
| **Maschine** | Unterdeck | W/S Leistung verteilen | Energie auf Antrieb, Waffen, Schild | sehen, was oben los ist |
| **Kartentisch** | Bruecke | Karte oeffnen | Ziel auf Veld waehlen | alles andere |
| **Funk** | Bruecke | - | deckt Knoten auf, faengt Bruchstuecke | - |
| **Werkbank** | Hauptdeck | B bauen | Module einbauen, Waffen verbessern | fahren |

**SHIFT ist Ueberlast, nicht Boost.** Mehr Tempo, dafuer steigt die
Belastung eines kritischen Bauteils (6.6). Das ist dieselbe Taste wie der
Sprint zu Fuss und dieselbe Idee: schneller, aber es kostet.

### 6.3 Der Autopilot - der Kern des ganzen Spiels

**ENTWURF, und der wichtigste Absatz im Dokument.**

Der Meister hat es in einem Satz gesagt: *"man steuert primaer den mech,
aber teils eben auf autopilot stellt und die waffensysteme auf den anderen
mech fixiert, und dann eben zu fuss auf dem mech eine enterung abwehrt."*

Daraus folgt die Mechanik, um die sich alles dreht:

> **Man ist ein Mensch und hat vier Stationen. Der Autopilot ist der Preis
> dafuer, woanders zu sein.**

SAND loest das mit fuenf Spielern. DUSTFRONT hat einen - und macht daraus
nicht einen Mangel, sondern das Thema.

#### Die Leiter der Entfernung (A2, nach Der Meister)

Der Meister hat den Fortschritt so gedacht: *"dass man an verschiedenen
Punkten in der Progression erst immer zum Steuerpult gehen kann, und dass es
spaeter quasi ueber Ingame-Bluetooth von ueberall geht, mit Upgrades die
zum Beispiel entscheiden, ob man den Mech steuern kann, wenn man nicht drauf
ist."*

**Das ist besser als der urspruengliche Entwurf und ersetzt ihn.** Aus drei
Zustaenden wird eine **Leiter**, und die Sprosse haengt daran, *wie weit weg
man ist* - genau die Groesse, um die es in diesem Abschnitt ohnehin geht:

| Sprosse | Leistung | Wo man ist |
| --- | --- | --- |
| **besetzt** | voll | man steht an der Station |
| **in Reichweite** | leichter Abzug | irgendwo auf demselben Deck |
| **fern bedient** | deutlicher Abzug, waechst mit der Entfernung | irgendwo auf dem Rumpf ("Bluetooth") |
| **festgelegt** | fester Abzug, keine Reaktion auf Neues | Autopilot, man ist vom Rumpf herunter |
| **unbesetzt** | nichts | niemand hat sich darum gekuemmert |

**Und der Fortschritt ist, diese Leiter hinaufzukaufen.** Ein Modul hebt
nicht "Schaden", sondern **auf welcher Sprosse man noch brauchbar ist**. Die
beste Stufe des Kursrechners ist die, mit der man den Wandler noch steuern
kann, waehrend man unten in einer Ruine steht (8.2). Damit ist die
Progression keine Zahlenreihe, sondern eine Antwort auf die Frage *"wie weit
darf ich mich entfernen?"* - und das ist genau die Frage, aus der dieses
Spiel besteht.

**ENTWURF, was die Abzuege jeweils betreffen** - die Zahlen kommen nach
`config.py` unter `AUTOPILOT` und werden gemessen, nicht geraten:

| System | Besetzt | Fern bedient | Festgelegt |
| --- | --- | --- | --- |
| Steuerstand | voller Kurs und Schub | traege Lenkung | haelt den letzten Kurs, weicht nichts aus |
| Geschuetz | freies Zielen, volle Feuerrate | zielt langsamer nach | feuert auf den festgelegten Rumpfteil, trifft schlechter |
| Maschine | Leistung frei verteilbar | Umverteilung dauert | eingefrorene Verteilung, kein Ausgleich bei Schaden |

**Warum das traegt, in vier Punkten:**

1. **Jede Entscheidung ist ein Verzicht, kein Menuepunkt.** Nach unten zu
   gehen, um die Enterer aufzuhalten, heisst: die Geschuetze treffen jetzt
   schlechter. Echte Spannung ohne einen einzigen neuen Gegnertyp.
2. **Es begruendet die Ebenen** - und mit 5.4 auch die Baugroesse. Der Weg
   vom Reaktor zum Oberdeck sind bei einem Emperor-Titan acht Treppen, und
   diese Sekunden sind das Spiel.
3. **Es begruendet Module**, siehe oben: sie kaufen Entfernung.
4. **Es macht den Fortschritt spuerbar statt ablesbar.** Der Moment, in dem
   man zum ersten Mal aus einer Ruine heraus den eigenen Wandler herumzieht,
   ist ein Ereignis. "+8% Zielgenauigkeit" ist keines.

**H ist die Taste dafuer**, wie das Menue seit 0.1.0 sagt.

#### Die eine Bedingung an den Code

Der Meister hat gefragt, ob das fuers Programmieren wichtig ist oder sich
spaeter aendern laesst. **Es laesst sich spaeter aendern - wenn eine Sache
von Anfang an stimmt:**

> Wer eine Station bedient, steht **an der Station**, nicht am Spieler.
> Also `wandler.stationen["steuerstand"].bedient_von`, nicht
> `spieler.modus == "steuern"`.

Steht es an der Station, ist "aus der Ferne bedienen" nur eine gelockerte
Abstandspruefung - eine Zeile, jederzeit nachruestbar, und die ganze Leiter
oben ist eine Zahl je Sprosse. Steht es am Spieler, muss spaeter jede
Station angefasst werden.

**Derselbe Griff loest nebenbei A3** (mehrere Spieler): eine Station, die
weiss, *wer* sie bedient, kann auch von einem zweiten Menschen bedient
werden. Fuer den Mehrspieler spaeter faellt damit nichts an, was nicht
ohnehin da waere.

*Faellig:* in **M3**. Die Leiter selbst nicht - nur diese eine
Entwurfsentscheidung, und die kostet zehn Minuten.

### 6.4 Grundriss

**ENTWURF, mittlere Klasse, 18 x 12 je Deck.** Im Format, das
`Ebene.aus_text()` schon versteht:

```
E1 UNTERDECK              E2 HAUPTDECK              E3 BRUECKE          E4 OBERDECK
##################        ##################        ##################   ##...####...##
#....#RRRR#......#        #......#....#....#        #................#   #.G........G.#
#.WW.#....#..EE..#        #.SS...#.MM.#.LL.#        #....#......#....#   #............#
#.WW.......<.....#        #.SS........<....#        #.KK.>......#.FF.#   #.....<......#
#....#....#......#        #......#....#....#        #................#   #............#
#....o....#..>...#        #..MM..o....>....#        #....#..TT..#....#   #.G........G.#
#.AA.#....#......#        #..MM..#....#....#        #................#   ##...####...##
##################        ##################        ##################

  R = Rampe                 S = Schlafkoje            K = Kartentisch     G = Geschuetz
  W = Werkstatt             M = Modulschacht          T = Steuerstand
  A = Antrieb               L = Lager                 F = Funk            > = Treppe hoch
  E = Reaktor               o = Luke nach unten                           < = Treppe runter
```

**Was fest sein soll**, auch wenn der Grundriss sich noch aendert:

* Rampe unten aussen, Steuerstand ganz oben. Wer los will, geht hoch; wer
  raus will, geht runter. Der Weg selbst erzaehlt den Ablauf.
* Treppen durchgehend an derselben Stelle, damit man blind hoch und runter
  findet - im Gefecht zaehlt jede Sekunde auf dieser Strecke.
* Geschuetze auf dem Oberdeck, also am weitesten weg von allem anderen.
  Das ist die Entscheidung aus 6.3 in Kachelform.
* Das Oberdeck hat **offene Kanten**. Man kann herunterfallen. Absicht.

### 6.5 Module: der Fortschritt zum Anfassen

**Aus der alten Fassung uebernommen, weil es dort schon richtig war.**

Es gibt keinen abstrakten Faehigkeitsbaum in einem Menue - man **laeuft
durch seinen eigenen Fortschritt**. Ein neues Modul ist ein neuer Raum, den
es vorher nicht gab. Ein Modul belegt einen **Schacht**, ein 2x2-Feld auf
einem Deck. Ein leerer Schacht ist sichtbar leer: offene Verankerung, lose
Kabel.

| Modul | Deck | Was es tut | Warum man es will |
| --- | --- | --- | --- |
| **Reaktor** | Unterdeck | liefert Energie, Stufe 1-3 | jedes andere Modul zieht davon |
| **Antrieb** | Unterdeck | Reichweite und Tempo | der Front davonlaufen |
| **Werkstatt** | Unterdeck | Reparatur unterwegs | ohne sie faehrt man Schaden mit |
| **Zielrechner** | Oberdeck | hebt den **festgelegten** Zustand der Geschuetze | kauft dir, woanders zu sein (6.3) |
| **Kursrechner** | Bruecke | Autopilot weicht Hindernissen aus | dasselbe fuer die Lenkung |
| **Werkbank** | Hauptdeck | Waffen verbessern | die sechs Waffen bekommen Stufen |
| **Lager** | Hauptdeck | wie viel Schrott mitgeht | ohne Lager laesst man Beute liegen |
| **Kojen** | Hauptdeck | Leben zwischen Etappen auffuellen | sonst zaehlt jeder Treffer dauerhaft |
| **Labor** | Hauptdeck | Chor-Technik auswerten | der einzige Weg an die besten Teile |
| **Funk** | Bruecke | deckt Sektorknoten auf | man laeuft nicht mehr blind |
| **Schotten** | alle | Tueren, die Enterer aufhalten | Zeit, um hinzukommen |
| **Panzerung** | alle | schuetzt kritische Bauteile | ueberlebt das Duell |

**Energie als Knappheit.** Der Reaktor liefert eine Zahl. Jedes Modul zieht
eine Zahl. Man kann mehr einbauen, als man betreiben kann - dann muss man
abschalten, an der Station **Maschine**, im Gefecht, waehrend geschossen
wird. Das erzeugt echte Entscheidungen, ohne eine einzige neue Mechanik: es
ist Addition.

### 6.6 Kritische Bauteile statt eines Lebensbalkens

**ENTWURF, uebernommen von SAND, und der beste Einzelgriff daraus.**

Ein Wandler hat keinen Huellenbalken, der von 100 auf 0 faellt. Er hat
**Bauteile, und jedes hat eigene Punkte**. Ein Geschosstreffer trifft ein
bestimmtes Feld, und was dort steht, geht kaputt.

| Bauteil | Kaputt heisst | Notbehelf |
| --- | --- | --- |
| **Reaktor** | keine Energie, alle Module aus | Handbetrieb, ein System zur Zeit |
| **Beine** | Tempo weg, kein Ausweichen | nur im Stehen zu reparieren |
| **Schwungrad** | keine Lenkung, der Kurs bleibt | - |
| **Geschuetz** | das eine Geschuetz schweigt | das andere benutzen |
| **Schotte** | Enterer kommen durch | mit dem Ruecken davorstellen |
| **Rampe** | man kommt nicht runter | springen (5.3) |

**Warum das so viel besser ist als ein Balken:**

* **Es ist lesbar.** Man sieht am Bildschirm, *was* kaputt ist - es steht
  ja als Kachel da und qualmt.
* **Es erzeugt Geschichten.** "Die Lenkung war weg und ich bin mit
  festgefahrenem Kurs in den Gegner gelaufen" ist ein Erlebnis. "Ich hatte
  noch 12 Prozent" ist keines.
* **Es kostet fast nichts.** Eine Kachel mit Punkten und einem Zustand.
  Der Kern kennt Kacheln mit Eigenschaften bereits.
* **Es begruendet das Werkzeug (Q).** Reparieren heisst: hingehen, davor
  stehen, Q halten, waehrend woanders gekaempft wird. Wieder dieselbe
  Klammer wie 6.3.

**Wann ist ein Wandler verloren?** **ENTWURF:** Wenn der Reaktor
durchgeht, oder wenn die Beine brechen und die Front aufschliesst. Nicht
bei null Punkten - es gibt keine.

### 6.7 Der Wandler als Gegenstand der Story

**ENTWURF, aus der alten Fassung uebernommen.** Der Wandler ist nicht neu.
Er hat **Spuren von Vorbesitzern** - ein zugeschweisster Schacht, ein Name
unter der Farbe, eine Koje zu viel. Wer genau hinsieht, findet sie. Das
erzaehlt Geschichte ohne einen einzigen Dialog und kostet nur Textur- und
Marken-Arbeit.

Bei **EISERN** (*"ein wandler, ein leben"*) bekommt das Gewicht: der
Wandler, den man verliert, ist der, in dem man zwanzig Stunden gelebt hat.

---

## 7. Das Duell

Wie ein Kampf zwischen zwei Wandlern tatsaechlich ablaeuft.

### 7.1 Die vier Phasen

**ENTWURF.** Der Ablauf ergibt sich aus den Reichweiten, nicht aus
Skripten:

```
   1. SICHTEN     Der andere Rumpf am Rand. Man entscheidet:
                  ausweichen oder stellen. Der Funk sagt, was er ist.

   2. BESCHIESSEN Geschuetze auf grosse Distanz. Rumpfteile gehen
                  kaputt (6.6). Man rennt zwischen Geschuetz,
                  Maschine und Werkstatt hin und her.

   3. ANNAEHERN   Wer den Gegner lahmgelegt hat, kann heran.
                  Handwaffen tragen. Jetzt sieht man Figuren auf dem
                  anderen Deck stehen.

   4. ENTERN      Bruecke raus oder Haken rueber. Fussgefecht auf den
                  Decks - der Spielkern, wie er heute schon laeuft.
```

Man muss nicht bis 4 gehen. Wer nur den Antrieb zerschiesst und
weiterlaeuft, hat gewonnen, aber nichts geholt. **Die Beute ist an Bord,
und an Bord kommt man nur zu Fuss.** Das ist der Grund, warum Entern kein
Sonderfall ist, sondern das Ziel.

### 7.2 Warum Entern der Kern ist

Weil es der eine Moment ist, in dem die beiden Massstaebe **dasselbe
Gefecht** werden: Die Geschuetze feuern weiter, waehrend man auf einem
fremden Hauptdeck mit dem Brecheisen um eine Ecke geht. Der Boden zieht
unten durch. Die eigene Maschine laeuft auf Autopilot, mit niemandem am
Steuer.

Und es ist **kaum neuer Code**: Fussgefecht, Kollision, Waffen, Sturz,
Treppen - alles steht. Was dazukommt, sind ein Uebergang (5.3) und eine
Gegner-KI, die Treppen benutzen kann.

### 7.3 Eine Enterung abwehren

Die Gegenrichtung, und die haerteste Lage im Spiel. **ENTWURF:**

* Enterer kommen an **einer** Stelle an Bord - dort, wo die Bruecke
  aufsetzt. Man sieht es (Draufsicht!) und ist trotzdem drei Decks weg.
* **Schotten** kaufen Sekunden. Sie sind das einzige Modul, dessen Nutzen
  man nur merkt, wenn man es hat.
* Wer alle Enterer erledigt, kann die Bruecke kappen - und der Rest der
  fremden Besatzung ist drueben.
* Wer verliert, verliert den Wandler. Nicht sofort das Spiel: man kann
  noch springen (5.3) und unten weiterlaufen. Was man dann hat, ist eine
  Figur im Wasteland und keine Basis mehr. **OFFEN:** ob das eine
  Ueberlebenschance ist oder das Ende des Laufs, steht in Abschnitt 14.

### 7.4 Die fremde Besatzung

**ENTWURF.** Gegner sind keine Wellen von Laeufern mehr, sondern eine
**Besatzung mit Stationen** - dieselbe Logik wie beim Spieler, gespiegelt.
Das gibt lesbares Verhalten ohne eine einzige neue KI-Idee:

* Jeder fremde Kaempfer hat eine Station, die er besetzen will.
* Wird sein Geschuetz zerstoert, geht er zur Werkstatt.
* Kommen Enterer, verlassen zwei Mann ihre Station und gehen hin.
* Sind zu wenige uebrig, laeuft ihre Maschine auf Autopilot - genau wie
  die eigene, mit denselben Nachteilen.

Damit zahlt sich jeder Abschuss doppelt aus: ein Mann weniger heisst eine
Station weniger. Das ist eine Schadensmechanik, die man sieht statt
abzulesen.

### 7.5 Was man gewinnt

**ENTWURF:** Den fremden Rumpf pluendert man nach Bauteilen - genau die
Module aus 6.5, die dort eingebaut sind. Wer ein Labor will, holt sich das
Labor aus einem Chor-Wandler. Damit kommt der Fortschritt aus dem Kampf
und nicht aus einer Beutetabelle.

**OFFEN:** Ob man einen erbeuteten Wandler behalten und den eigenen
aufgeben kann. Das waere ein starkes Stueck, kostet aber Spielstand-Arbeit.
Abschnitt 14.

---

## 8. Der Boden

### 8.1 Absteigen

**ENTWURF.** Man geht aufs Unterdeck, oeffnet die Rampe, laeuft hinunter.
Der Wandler bleibt stehen - oder eben nicht, wenn man ihn auf Autopilot
gestellt hat.

Was unten ist: **Gebaeude im Wasteland.** Ruinen, Silos, umgekippte
Transporter, Vorposten. Jedes ist eine kleine Kachelwelt mit ein bis drei
Ebenen und einer Hauptbeute, nach den Regeln aus 8.3.

### 8.2 Warum das aufregend ist, und nicht nur ein zweiter Schauplatz

Drei Gruende, alle aus der Grundstruktur, keiner aus einem Skript:

1. **Oben laeuft die Maschine ohne dich.** Jede Sekunde unten ist eine
   Sekunde, in der niemand am Steuer sitzt, niemand am Geschuetz und
   niemand an der Werkstatt.
2. **Die Front rueckt nach** (9.2). Unten zu sein kostet Etappenzeit.
3. **Man ist zu Fuss und klein.** Ebene 0, kleinster Massstab, weiteste
   Sicht - und der eigene Wandler steht als riesiges Ding am Rand des
   Bildes. Das ist ein Bild, das man nur in dieser Ansicht bekommt.

**Der schlimmste Fall, und den muss es geben:** Man kommt aus einer Ruine,
und der eigene Wandler ist nicht mehr da, weil der Autopilot den Kurs
gehalten hat. Dann laeuft man zu Fuss hinterher.

### 8.3 Die Beute-Regel

**ENTWURF, aus der alten Fassung uebernommen.** Jedes Gebaeude hat genau
**eine Hauptbeute** und **verstreuten Schrott**. Die Hauptbeute liegt nie
am Eingang und nie hinter einer einzelnen Tuer - sie liegt so, dass man
**mindestens eine Ebene wechseln** muss. Jede Kammer hat **mindestens zwei
Zugaenge** (eine Treppe zaehlt), damit sie keine Falle ist und der Schrot
nicht unbesiegbar wird.

### 8.4 Wie Gebaeude entstehen

**ENTWURF, dreistufig - die Reihenfolge ist wichtig:**

1. **Handgetippte Karten** unter `karten/boden/<typ>_<nummer>.txt`. Vier
   bis sechs je Typ. Handgebaut ist besser als generiert, solange man noch
   nicht weiss, was gut ist.
2. **Bausteine** von 8x8 oder 16x16 Kacheln, die an den Raendern
   zusammenpassen.
3. **Echte Erzeugung** nur, wenn Stufe 2 sich erschoepft anfuehlt.

**Pflicht ab Stufe 2:** Ein Pruefwerkzeug in `tests/`, das jede Karte
testet: Hauptbeute erreichbar? Jede Kammer zwei Zugaenge? Kann man sich
festfahren?

---

## 9. Veld und die Front

Gekuerzt gegenueber der alten Fassung - das meiste stimmt weiter, ist aber
nicht mehr der Mittelpunkt.

### 9.1 Der Knotengraph

**ENTWURF:** Ein Sektor ist ein Graph von **14 bis 20 Knoten**, gerichtet
von links (Start) nach rechts (Ausgang), in **6 bis 8 Spalten**. Von einem
Knoten fuehren 1 bis 3 Kanten in die naechste Spalte.

```
   Spalte  1     2     3     4     5     6     7
           o-----o-----o     o-----o-----o           o  Knoten
            \   / \   / \   /       \   /            -  Laufstrecke
             \ /   \ /   \ /         \ /             #  Ausgang
   START -----o-----o-----o-----o-----o----- #
             / \   / \   /       \   / \
            o-----o     o-----o-----o     o
```

Bei 16 Knoten und 7 Spalten besucht man etwa 7 - **weniger als die
Haelfte**. Ein zweiter Durchlauf sieht anders aus.

**Was an einem Knoten sein kann:** ein feindlicher Wandler, ein
Gebaeudefeld zum Pluendern, eine Freie Werft (Reparatur und Handel, kein
Kampf), ein Sendemast (Vorwissen), ein Wrackfeld (viel Schrott, wenig
Gefahr).

**Die Vorschau gibt es schon:** `sector_preview()` zeichnet acht Knoten mit
Verbindungen und Fraktionsfarben. Der Plan macht daraus die echte Karte.

### 9.2 Die Front - der Motor

**ENTWURF, unveraendert aus der alten Fassung, weil es dort richtig war.**

Hinter dem Spieler rueckt eine Linie nach: die Staubfront der Kolonne. Sie
bewegt sich pro **Etappe** eine feste Strecke nach rechts. Jeder besuchte
Knoten kostet eine Etappe. Zurueckgehen auch.

Was das bewirkt:

1. **Es gibt kein Ausruhen.** Man kann nicht jeden Knoten mitnehmen. Gier
   wird bestraft, ohne dass eine Uhr tickt, die man anstarrt.
2. **Der Name stimmt.** DUSTFRONT ist die Front.
3. **Spannung ohne Gegner.** Der Druck kommt aus der Karte.
4. **Es macht das Absteigen teuer** (8.2) - und damit zu einer
   Entscheidung.
5. **Eine Verlustbedingung, die kein Tod ist.**

**Zahlen, ENTWURF:** Front rueckt 1 Spalte je 2 Etappen, Sektor hat 7
Spalten, also rund 14 Etappen fuer 7 noetige Schritte. Feinjustage in
`config.py` unter `FRONT`.

### 9.3 Die Fahrt zwischen den Knoten (KORREKTUR der alten Fassung)

**KORREKTUR.** Die alte Fassung nannte das *"Transport, und Transport ist
selten das, wofuer man ein Spiel startet"*, und wollte es zu einer
animierten Karte abkuerzen.

Richtig: **Die Fahrt ist das Spiel.** Zwischen zwei Knoten laeuft der
Wandler, man ist an Bord, und hier passiert alles aus Abschnitt 7 und 8.
Der Knoten ist nur die Ankunft - die Strecke ist der Inhalt.

### 9.4 Warum die Front spaeter passt, ohne sie jetzt zu bauen

Der Meister hat es so gesetzt: *"Das mit der Front muessen wir wissen, dass
das theoretisch geht."* Also - der Nachweis, und zwar als Liste von
**Bedingungen an M1 bis M8**, nicht als Bauauftrag.

**Was die Front technisch ist:** eine Zahl. Eine Spaltenposition auf einem
Graphen, die nach jeder Etappe um einen Betrag steigt. Sie zeichnet einen
Balken auf der Sektorkarte und vergleicht sich mit der eigenen Position.
Das ist keine Mechanik, das ist eine Variable mit einer Anzeige.

**Warum sie trotzdem umbauen kann, wenn man nicht aufpasst:** nicht weil
sie kompliziert ist, sondern weil sie voraussetzt, dass es *einen Lauf gibt,
der aus mehreren Gefechten besteht*. Wenn M1 bis M8 ein einzelnes Gefecht
bauen, das beim Start alles frisch anlegt und beim Ende alles wegwirft, dann
ist die Front spaeter ein Umbau. Wenn sie es nicht tun, ist sie eine neue
Szene und eine Zahl.

**Fuenf Bedingungen. Wer M1 bis M8 baut, haelt sie ein:**

| # | Bedingung | Warum |
| --- | --- | --- |
| 1 | **Das Gefecht kennt seinen Ausgang.** Wenn ein Gefecht endet, hinterlaesst es ein Ergebnis - Wandler-Zustand, Beute, verbrauchte Zeit - statt nur zum Menue zurueckzuspringen. | Eine Etappe muss etwas an die naechste weitergeben koennen. Das ist der einzige Punkt, der spaeter wirklich weh taete. |
| 2 | **Der Wandler-Zustand liegt nicht in der Szene.** Decks, Module, kaputte Bauteile, Inventar gehoeren in ein Objekt, das das Gefecht *bekommt*, nicht in eines, das es *anlegt*. | Sonst kann kein Schaden ueber eine Etappe hinaus bestehen bleiben, und ohne das hat die Front nichts, womit sie drohen koennte. |
| 3 | **Ein Gefecht wird mit einem Auftrag gestartet** (welche Karte, welcher Gegner, welche Regeln) - so wie `Spiel(app, seed=...)` und `Gefecht(app, ..., seed=...)` es heute schon tun. | Die Sektorkarte wird spaeter genau dieser Auftraggeber. Wer das einhaelt, muss fuer M8 nichts anfassen. |
| 4 | **Zeit wird gezaehlt, auch wenn sie noch nichts kostet.** Ein Zaehler "Etappen verbraucht" laeuft mit und wird angezeigt, ohne Folgen. | Die Front haengt daran. Ein Zaehler, den es schon gibt, bekommt spaeter nur eine Konsequenz. Das ist eine Zeile. |
| 5 | **Kein Zahlenwert steht im Code.** Wie immer: `config.py`. Ein spaeterer Abschnitt `FRONT` steht dann neben `WANDLER` und `AUTOPILOT`, statt sie zu durchkreuzen. | Steht ohnehin als Hausregel fest. |

**Was ausdruecklich *nicht* eingehalten werden muss:** es braucht jetzt
keinen Graphen, keine Knoten, keine Sektorkarte, keine Etappenkosten und
keine Ueberrollt-Bedingung. Bedingung 1 bis 4 sind zusammen vielleicht ein
halber Tag Arbeit, verteilt ueber M2 bis M7, und sie sind auch ohne Front
sinnvoll - ein Wandler, dessen Schaden nach dem Gefecht verschwindet, ist
auch fuer sich genommen kein Wandler.

**Damit ist die Frage beantwortet: ja, es geht.** Die Front ist spaeter
eine neue Datei (`sektor.py`), eine neue Szene und eine Zahl - vorausgesetzt,
die fuenf Zeilen oben stehen. Sie steht deshalb als Pruefpunkt in jedem
Meilenstein, der sie beruehrt.

---

## 10. Die drei Fraktionen und die drei Regionen

Namen und Fraktionsverteilung stehen bereits im Menue und sind damit
**FEST**. Was fehlt, ist ihr Charakter - und der haengt jetzt daran, *was
fuer Wandler* sie fahren.

### 10.1 Die Fraktionen als Maschinen

**ENTWURF:**

| Fraktion | Ihre Wandler | Wie man gegen sie kaempft |
| --- | --- | --- |
| **Die Kolonne** | schwer, gepanzert, viele Geschuetze, grosse Besatzung | nicht im Beschuss gewinnen. Beine lahmlegen, entern, drinnen ist es eng und sie sind viele. |
| **Der Chor** | unbemannt. Keine Besatzung, alles auf Autopilot, tadellos gewartet. | Beschuss wirkt, Entern ist leicht - nur ist drinnen niemand, den man umstimmen koennte, und die Maschine stoppt nicht. |
| **Die Freien Werften** | zusammengeflickt, jeder anders, meist friedlich | gar nicht. Hier repariert und handelt man. |

**Der Chor ist der interessante Fall:** eine Anlage, die weiterlaeuft. Ein
Chor-Wandler greift nicht an, er *faehrt seine Route* und behandelt einen
als Stoerung. Das erlaubt Begegnungen, die man auch weglaufen kann - und
macht Schleichen moeglich, ohne ein Schleichsystem zu bauen.

### 10.2 Die drei Regionen

> **ASCHEWALD** - *"viel schrott, wenige patrouillen. der ruhige einstieg."*
> Kolonne 0.3 · Chor 0.15 · Werften 0.7

Verbrannter Wald aus Stahlmasten, Asche knoecheltief. Weite Sicht, wenig
Deckung. **Lehrsektor**, und er lehrt durch Aufbau, nicht durch Textkaesten:
der erste Gegner ist ein einzelner Werften-Wandler mit halber Besatzung,
der erste Abstieg ist in eine Ruine in Sichtweite, und die erste Enterung
geht von einem selbst aus.

> **TRICHTERFELD** - *"dichte kolonne-verbaende, dafuer schwere module im
> wrackfeld."* Kolonne 0.85 · Chor 0.25 · Werften 0.35

Einschlagkrater, dazwischen Daemme aus gepresstem Schrott. Hier lernt man
Beschuss: Kolonne-Wandler in Verbaenden, und **Verbaende ziehen durch**.
Wer sich Zeit laesst, trifft auf mehr. Das koppelt direkt an die Front.
Die schweren Module liegen in den Trichtern - man muss absteigen, waehrend
oben etwas vorbeizieht.

> **CHORWERK-RUINE** - *"der chor sendet noch. beste technik, kaum
> ueberlebende."* Kolonne 0.2 · Chor 0.9 · Werften 0.2

Tuerme aus weissem Beton, die immer noch Strom haben. Kein Rost, kein
Staub. Hier sind die besten Bauteile, und sie stecken in Maschinen, die
niemand fuehrt.

### 10.3 Wie die Regionen zusammenhaengen

**ENTWURF:** Drei Abschnitte einer Reise, keine drei Schwierigkeitsgrade.
Das Menue laesst einen waehlen, wo man **anfaengt** - wer spaeter anfaengt,
faengt haerter an.

```
   ASCHEWALD  --->  TRICHTERFELD  --->  CHORWERK-RUINE
   lernen           verdienen           riskieren
```

**Der Wandler ist das, was zwischen den Regionen bleibt** - und damit das,
was den Fortschritt traegt.

---

## 11. Progression

### 11.1 Die vier Faeden

| Faden | Waehrung | Wo man ihn spuert | Weg beim Verlust? |
| --- | --- | --- | --- |
| **Wandler** | Module, Schrott, erbeutete Bauteile | an Bord, sichtbar als Raum | ja (bei EISERN endgueltig) |
| **Waffen** | Schrott an der Werkbank | im Fussgefecht | ja |
| **Wissen** | Blaupausen, Funkdaten | Sektorkarte, Bauliste | **nein** |
| **Spieler** | Panzerung, Medkits | Leben im HUD | ja |

**Der dritte Faden ist der wichtige.** Wissen bleibt. Wer einmal eine
Blaupause gefunden hat, kann sie im naechsten Lauf bauen, wenn er das
Material hat. Damit hat auch ein verlorener Lauf etwas gebracht, ohne dass
die Schwierigkeit sinkt.

### 11.2 Die Kopplung an die Karte

| Braucht man | Laeuft man zu | Kostet |
| --- | --- | --- |
| Schrott (Menge) | Wrackfeld | Zeit, wenig Risiko |
| Ein bestimmtes Modul | einen Wandler, der es eingebaut hat | ein Duell und eine Enterung |
| Schweres Bauteil | Trichter, Vorposten am Boden | absteigen, waehrend oben niemand steht |
| Reparatur, Handel | Freie Werft | Schrott |
| Vorwissen | Sendemast | eine Etappe |

### 11.3 Die Waffen bekommen Stufen

Die sechs Waffen stehen und sind ausbalanciert (im Test nachgewiesen). Sie
werden **nicht** ersetzt - man findet keine "bessere Schrotflinte".
Stattdessen hat jede Waffe an der Werkbank drei Stufen, die je **eine Zahl
in `K.WAFFEN`** anheben. Das ist mit Absicht langweilig gebaut: es gibt
bereits einen Test, der die Balance jeder Waffe misst, und Stufen, die nur
Zahlen anheben, lassen sich damit pruefen.

| Waffe | Stufe hebt | Damit wird sie |
| --- | --- | --- |
| Repetierer | `magazin` | der verlaessliche Dauerlaeufer |
| Sturmgewehr | `streuung_dauerfeuer` runter | im Dauerfeuer beherrschbar |
| Schrot | `geschosse` | auf kurze Distanz vernichtend - die Enterwaffe |
| Scharfschuetze | `fokus_dauer` runter | schneller einsatzbereit |
| Granate | `radius` | Flaechenwaffe statt Punktwaffe |
| Brecheisen | `schub` | ein Werkzeug, um Platz zu schaffen |

Geschuetze sind **keine** Waffen aus `K.WAFFEN` - sie gehoeren zur Maschine
und stehen unter `GESCHUETZE` in `config.py`. Das haelt die
Waffenbalance-Tests sauber.

### 11.4 Wie erzaehlt wird

**ENTWURF - vier Mittel, alle billig, keines braucht ein Dialogsystem:**

1. **Der Ort selbst.** Eine Werft mit gedeckten Tischen und niemandem
   darin. Ein Chor-Wandler, der seit Jahren dieselbe Runde laeuft.
2. **Terminals.** Kurze Texte an festen Stellen, mit E zu lesen.
3. **Der Funk.** Bruchstuecke, die beim Laufen eingeblendet werden. Ein
   Satz, kein Absatz.
4. **Der Wandler.** Spuren der Vorbesitzer (6.7).

**Was ausdruecklich nicht:** Gespraeche mit Auswahlmoeglichkeiten,
Auftragsgeber, Textkaesten, die den Ablauf anhalten.

---

## 12. Machbarkeit: was neuen Code braucht

Ehrliche Aufstellung.

### 12.1 Geht heute schon, ohne eine Zeile

* Mehr Ebenen (fuenf stehen in `EBENEN_HOEHE`, mehr braucht 5.4)
* Groessere und kleinere Karten
* Neue Kacheltypen (ein Eintrag in `KACHELN` und `ZEICHEN`)
* Neue Gegnertypen (ein Eintrag in `GEGNER` plus ein Bild)
* Stuerzen von einem Deck, mit Steuerung in der Luft
* Jede Textur und jeder Klang dafuer

### 12.2 Kleine Ergaenzungen, additiv

| Was | Wo | Aufwand |
| --- | --- | --- |
| Marken in Karten | `world.py`, `ZEICHEN` | klein |
| `Welt.aus_datei()` | `world.py` | klein |
| `Welt.versatz` (wo der Rumpf steht) | `world.py` | klein |
| Stationen (Zustand am Spieler, andere Tasten) | `entities.py`, `play.py` | klein |
| Kacheln mit Punkten und Zustand (6.6) | `world.py` | klein |
| Waffenstufen | `config.py`, `inventar.py` | klein |
| `Ebene.stempeln()` (Sonderfall Andocken) | `world.py` | klein |

### 12.3 Neue Bausteine, aber ohne Umbau am Kern

| Was | Neue Datei | Aufwand |
| --- | --- | --- |
| Mehrere Welten gleichzeitig zeichnen, mit Versatz | `render.py` | **mittel, und der erste echte Posten** |
| Hoehenstaffel je Rumpf statt global (5.4) | `world.py` | klein - ein Methodenkoerper |
| Sprung von Rumpf zu Rumpf (5.3) | `entities.py` | klein - der Sturz kann es schon |
| Der Wandler: Bauplan, Decks, Stationen, Module | `wandler.py` | mittel |
| Schuesse zwischen Ruempfen (5.5) | `world.py` | mittel |
| Uebergaenge zwischen Welten (5.3) | `world.py`, `play.py` | mittel |
| Besatzungs-KI mit Stationen (7.4) | `entities.py` | mittel |
| Gegner, die Treppen benutzen | `entities.py` | mittel |
| Sektorgraph und Sektorkarte | `sektor.py` | mittel |
| Lauf-Spielstand | `spielstand.py` | mittel |
| Kartenpruefung | `tests/` | mittel |

### 12.4 Was wirklich teuer ist

| Was | Warum teuer | Empfehlung |
| --- | --- | --- |
| **Bewegliche Kacheln (Weg B)** | bricht das Kachelraster ueberall | nein, nie |
| **Beinanimation des Wandlers von aussen** | der Rumpf wird von innen gezeigt, aussen sieht man ihn nur auf der Sektorkarte | als Bild, nicht als Simulation |
| **Echte Kartenerzeugung** | Qualitaet schwer zu sichern | Stufe 3, nur wenn noetig |
| **Erbeuteten Wandler uebernehmen** | Spielstand, Bauplaene, Umzug des Inventars | OFFEN, Abschnitt 14 |

**Der Unterschied zur alten Fassung:** Dort stand der Fahr-Modus als
teuerster Posten. Er ist es nicht mehr, weil er nicht als zweites
Bewegungssystem gebaut wird (6.1). Der teuerste Posten ist jetzt, mehrere
Welten gleichzeitig zu zeichnen - und das sind ein paar Versatzrechnungen
in `render.py`, kein Umbau.

---

## 13. Reihenfolge der Umsetzung

Jeder Meilenstein ist **fuer sich spielbar und fuer sich testbar**. Nach
jedem laeuft das Spiel, beide Testlaeufe sind gruen, und es gibt etwas
Neues zu sehen.

Versionsnummern nach dem Schema im README. Die Nummern sind **Richtwerte,
keine Zusagen** - zwischen zwei Meilensteinen kommen Reparaturen dazu, die
auch hochzaehlen. Sie fangen bei 0.20.0 an, weil 0.12.0 bis 0.19.1 vergeben
sind, groesstenteils an den abgespaltenen Mehrspieler. Keine Nummer wird
zweimal benutzt, auch nicht ueber Zweige hinweg.

**Die Reihenfolge folgt der Rangfolge vom Anfang des Dokuments:** erst
jedes System einzeln funktionsfaehig, dann die Welt drumherum. M1 bis M8
sind die Grundmechanik und ergeben zusammen ein fertiges Spiel ohne
Sektoren, ohne Front und ohne Geschichte. M9 und M10 sind Fernziel.

**Die Trennlinie liegt hinter M8.** Nach M8 kann man DUSTFRONT spielen:
eigener Wandler gegen fremden Wandler, Geschuetze, Entern, Absteigen,
Module, und ein Grund weiterzumachen. Das ist der Punkt, an dem entschieden
wird, ob eine Geschichte darauf kommt oder Mitspieler - und beides ist von
dort aus ein Aufsatz, kein Umbau.

**Jeder Meilenstein bis M8 nennt am Ende seine Front-Pruefpunkte** aus
Abschnitt 9.4. Das sind die einzigen Zugestaendnisse an das Fernziel, und
sie sind auch ohne Fernziel richtig.

### M1 - Karten kommen aus Dateien (0.20.0)

*Ziel:* `testkarte()` ist nicht mehr die einzige Karte.

* `karten/` mit Textdateien, eine Datei je Welt mit Trennzeilen je Ebene
* `Welt.aus_datei(name)`
* Marken (`S`, `R`, `T`, `G`, `W`, `E`, `M`, `1`-`9`) mit `ebene.marken`
* Der Spieler startet auf der Marke `S`
* Test: jede Karte im Ordner laedt, hat eine Startmarke, jede Ebene ist
  von dort erreichbar

*Warum weiter zuerst:* Ein Wandler ist auch nur eine Textkarte. Ohne
diesen Schritt ist jeder weitere eine Codeaenderung.

*Front-Pruefpunkt:* keiner. M1 beruehrt nichts aus 9.4.

### M2 - Der Wandler als begehbarer Rumpf (0.21.0)

* `wandler.py`: Bauplan aus Text, **beliebig viele Decks** (5.4)
* Der Wandler ist eine eigene `Welt` (5.1), er steht noch still
* **Die Hoehenstaffel gehoert an den Rumpf, nicht in `config.py`:**
  `Welt.hoehe()` rechnet sie aus Deckzahl und `SCHRITT`, statt die globale
  Tabelle zu lesen. Eine Methode, und der Emperor-Titan ist moeglich.
* Zwei Baugroessen zum Vergleich anlegen, klein und gross - damit sich
  zeigt, ob lange Wege sich gut oder nur laestig anfuehlen
* Man laeuft hinein, hoch, runter, ueber die Rampe hinaus auf einen Boden
* Treppen zwischen den Decks, offene Kanten am Oberdeck, Sturz auf den Boden

*Sichtbar:* Man hat ein Zuhause, und es ist wirklich begehbar.

*Hier faellt A4 an.* Nachtraeglich waere es teuer, weil dann jede Karte und
jeder Bauplan auf fuenf feste Hoehen gebaut waere.

*Front-Pruefpunkt (9.4, Bedingung 2):* Der Wandler-Zustand gehoert in ein
eigenes Objekt, das die Szene **bekommt**, nicht anlegt. Das ist hier eine
Entwurfsentscheidung von zehn Minuten und spaeter ein Umbau von Tagen.

### M3 - Stationen und die Fahrt (0.22.0)

* Stationen als Marken plus Tastenbelegung (6.1, 6.2)
* **Die Belegung gehoert an die Station, nicht an den Spieler** (6.3, Ende).
  Zehn Minuten jetzt; spart spaeter, fuer Fernbedienung (A2) und
  Mitspieler (A3) jede Station anzufassen.
* Steuerstand: der Rumpf bekommt eine Position, der Boden zieht durch
* TAB schaltet die Ansicht zwischen "an Bord" und "Fahrt"
* **Autopilot (H)**, zunaechst nur "besetzt" und "festgelegt" - die volle
  Leiter aus 6.3 kommt mit den Modulen in M7
* `AUTOPILOT` und `WANDLER` in `config.py`

*Sichtbar:* **Es ist ein Mech-Spiel.** Der Meilenstein, der alles aendert.

*Front-Pruefpunkt (9.4, Bedingung 4):* Die gelaufene Strecke wird gezaehlt
und angezeigt, ohne Folgen. Der spaetere Etappenzaehler ist dann schon da.

### M4 - Geschuetze und der zweite Rumpf (0.23.0)

* Zweite Welt: ein feindlicher Wandler mit Versatz (5.5). Der Versatz ist
  eine **Kommazahl**, kein Kachelmass (5.3).
* Geschuetzstationen, Schuesse zwischen Ruempfen
* **Ein Einschlag trifft Bauteil und Besatzung** (A5) - ein Aufruf fuer den
  Bauteilschaden, einer fuer das bestehende `welt.treffer()`
* Decks als Deckung, das Oberdeck ohne (5.5)
* Kritische Bauteile mit Punkten und Zustand (6.6)
* Reparieren mit Q an der Werkstatt

*Sichtbar:* Das Duell. Phasen 1 bis 3 aus 7.1. Und: man sieht Leute auf dem
fremden Deck sterben - das ist die Probe aus 5.3, und sie faellt hier an.

*Front-Pruefpunkt (9.4, Bedingung 3):* Das Gefecht wird mit einem Auftrag
gestartet - welche Karte, welcher Gegner, welche Regeln - so wie
`Spiel(app, seed=...)` es heute schon tut. Wer das einhaelt, muss fuer die
Sektorkarte spaeter nichts anfassen.

### M5 - Entern (0.24.0)

* Uebergaenge zwischen Welten (5.3): Enterbruecke und Haken
* **Springen von Rumpf zu Rumpf** (5.3): beim Absprung fliegendes Wesen mit
  absoluter Position, beim Aufsetzen in den Rumpf darunter uebernommen.
  Zieht der andere weg, faellt man auf den Boden.
* Besatzungs-KI mit Stationen (7.4)
* Gegner, die Treppen benutzen
* Schotten als Modul

*Sichtbar:* Phase 4. Maschinenkampf und Fusskampf sind dasselbe Gefecht.

### M6 - Absteigen und pluendern (0.25.0)

* Der Boden als eigene Welt mit Gebaeuden
* Rampe runter, Gebaeude betreten, Hauptbeute nach 8.3
* Der eigene Wandler laeuft weiter, wenn man ihn so eingestellt hat
* Drei bis vier handgetippte Gebaeudetypen

*Sichtbar:* Der schlimmste Fall aus 8.2 kann passieren.

### M7 - Module, Schaechte, Energie (0.26.0)

* Modulliste in `config.py`, leere Schaechte sichtbar leer
* Bauen mit B an der Werkbank
* Energie als Budget, Verteilung an der Station Maschine
* Erbeutete Module aus fremden Ruempfen (7.5)

*Sichtbar:* Schrott hat zum ersten Mal einen Zweck, und man laeuft durch
seinen eigenen Fortschritt.

### M8 - Das Spiel ist rund (0.27.0)

**Der wichtigste Meilenstein, und der, an dem die Rangfolge haengt.** Kein
neues System, sondern der Schritt, der aus sieben Systemen ein Spiel macht.

* Ein Gefecht hat einen Anfang und ein Ende und hinterlaesst ein Ergebnis
  (9.4, Bedingung 1): Wandler-Zustand, Beute, verbrauchte Strecke
* Man kann mehrere Gefechte hintereinander spielen, und der Wandler nimmt
  Schaden und Module mit
* Verlieren heisst etwas, Gewinnen heisst etwas
* Die Balance wird gemessen: Geschuetze gegen Panzerung, Enterung gegen
  Schotten, Autopilot-Abzuege (6.3) gegen Laufzeit zwischen den Decks
* Jedes System einzeln im Test nachgewiesen, so wie die sechs Waffen es sind

*Sichtbar:* **Man kann DUSTFRONT spielen.** Kein Sektor, keine Front, keine
Geschichte - und es funktioniert trotzdem als Spiel.

*Hier wird entschieden*, was darauf kommt: eine Geschichte (M9/M10), oder
Mitspieler (der Mehrspieler von `multiplayer-test` liegt bereit und ist
dokumentiert). Beides ist von hier ein Aufsatz, kein Umbau. Deshalb ist
diese Entscheidung erst hier faellig und nicht vorher.

---

**Ab hier Fernziel.** Nicht anfangen, solange M1 bis M8 nicht stehen und
jedes System einzeln funktioniert.

### M9 - Veld: Sektorkarte und Front (0.28.0) - FERNZIEL

* `sektor.py`: Graph, 14-20 Knoten, 6-8 Spalten
* Sektorkarte als Szene, aufgerufen vom Kartentisch
* `FRONT` in `config.py`, die Front rueckt je Etappe
* Ueberrollt werden beendet den Lauf
* Lauf-Spielstand: was bleibt (Wissen), was nicht (Wandler)

*Sichtbar:* Aus einzelnen Gefechten wird eine Reise mit Druck. Der Titel
erklaert sich.

*Wenn 9.4 eingehalten wurde,* ist das eine neue Datei, eine neue Szene und
eine Zahl. Wenn nicht, ist es ein Umbau - deshalb steht 9.4 da.

### M10 - Fraktionen, Missionen, Erzaehlung - FERNZIEL

Der ambitionierte Teil, und der, den Der Meister ausdruecklich nach hinten
gestellt hat. Er braucht praktisch alles aus M1 bis M9 als Unterlage:

* Fraktionen mit eigenen Prioritaeten, die sich auch untereinander verhalten
* Missionen oder Auftraege, mit denen man die Lage beeinflusst
* Regionen mit eigenem Charakter (Abschnitt 10.2)
* Erzaehlung: Terminals, Funkbruchstuecke, Spuren im Wandler (11.4)
* Verschiedene Enden

**Warum das ganz hinten steht:** Fraktionen mit eigenen Prioritaeten sind
kein Inhalt, sondern ein System - und zwar ein grosses, das sich nur
sinnvoll bauen laesst, wenn alles darunter steht und gemessen ist. Eine
Geschichte laesst sich auf ein funktionierendes Gefecht aufsetzen. Ein
Gefecht laesst sich nicht auf eine Geschichte aufsetzen.

**Nach M10 ist das Spiel von vorn bis hinten spielbar.** Damit stellt sich
die erste Frage aus dem Versionsschema, und es wird `1.0.0`.

---

## 14. Was noch nicht entschieden ist

Der Meister hat gefragt: *"was denn theoretisch noch zu entscheiden waere
oder welche Entscheidung ich noch umaendern koennte, was davor getroffen
wurde, was also jetzt in dem Plan steht, was ich noch nicht explizit
bestaetigt habe."*

Dieser Abschnitt ist die Antwort, und er ist vollstaendig. **Alles, was in
diesem Dokument steht und nicht in 14.1 aufgezaehlt ist, kommt von Claude
und ist damit Vorschlag, nicht Beschluss.**

Sortiert ist nach **Kosten der Aenderung**, nicht nach Wichtigkeit. Das ist
der einzige Sortierschluessel, der praktisch hilft: was spaeter teuer wird,
gehoert jetzt entschieden; was jederzeit billig bleibt, gehoert jetzt
ignoriert.

| Topf | Bedeutung | Wann faellig |
| --- | --- | --- |
| **A - Fundament** | Aenderung nachher heisst Umbau. 6 Stueck. | **alle sechs entschieden** (14.2) |
| **B - Spielgefuehl** | Aenderung nachher heisst Zahlen und ein paar Stunden. 10 Stueck. | am Meilenstein selbst, gern nach dem Ausprobieren |
| **C - Kosmetik** | Aenderung nachher kostet nichts. | nie vorab. Einfach machen. |
| **D - Fernziel** | Betrifft nur M9 und M10. | nach M8, nicht vorher |

---

### 14.1 Was von Der Meister kommt

Zur Kontrolle, nicht zur Debatte. Wenn hier etwas falsch wiedergegeben ist,
ist das der wichtigste Fehler im Dokument.

**Aus dieser Sitzung, woertlich bestaetigt:**

* Rustfront ist ein **Mech-Kampfspiel**, der riesige Mech ist auch die Basis
* Die **Ebenen** sind die verschiedenen Etagen des Mechs und der Boden
* Man steuert **primaer den Mech**
* Man stellt ihn **teils auf Autopilot** und **fixiert die Waffensysteme**
  auf den anderen Mech
* Dann **zu Fuss auf dem eigenen Mech eine Enterung abwehren**
* Oder **den anderen Mech entern**
* Oder **absteigen, um Gebaeude im Wasteland zu looten**
* Vorbild **SAND: Raiders of Sophie**, in 2D, mit einem **radikal anderen
  Vibe**
* **Rangfolge:** erst die Grundmechanik und jedes System einzeln
  funktionsfaehig. Front, Fraktionen mit eigenen Prioritaeten, Missionen,
  konkrete Karte, Geschichte mit verschiedenen Enden sind nicht die
  Prioritaet und kommen danach.
* **Begruendung dafuer, von ihm:** ob man gegen einen KI-Mech oder gegen
  andere Spieler kaempft, ist hinterher umbaubar - "das kann man dann ja
  eben einfach umbauen zu einer Story".
* Von der Front wird jetzt nur gebraucht, **dass sie theoretisch geht**
  (Abschnitt 9.4).

**Aus dem Repo, von ihm gebaut oder abgenommen** - also bestaetigt, aber
aelter als die Korrektur:

* Kontinent **Veld**, 90-Grad-Draufsicht
* **Modularer Wandler**, aus Schrott weiter ausgebaut
* Drei Fraktionen: **Kolonne, Chor, Freie Werften**
* Drei Regionen im Menue: **ASCHEWALD, TRICHTERFELD, CHORWERK-RUINE** mit
  ihren Fraktionsanteilen
* **Tab** wechselt zwischen "an Bord" und "Fahr-Modus"
* Die Steuerungstabelle im Menue: **B BAUEN, Q WERKZEUG, W/S FAHRT, A/D
  DREHEN, SHIFT BOOST, H AUTOPILOT**
* **EISERN:** "ein wandler, ein leben. kein laden nach dem verlust."
* **SCHROTT** als Waehrung im HUD
* Hausregeln: alle Zahlen in `config.py`, deutsche Bezeichner und
  Kommentare, keine Umlaute im Code, beide Testlaeufe gruen, Version vor
  dem Push hoch, keine Nummer zweimal

Alles andere unten ist Claude.

---

### 14.2 Topf A - Fundament: entschieden

**Alle sechs sind beantwortet.** Der Meister hat sie in einem Zug erledigt;
was hier steht, ist das Ergebnis und die Begruendung, nicht mehr eine Frage.
Zwei davon haben den Plan geaendert (A4 und A5), eine hat ihn verbessert
(A2).

| | Entscheidung | Ergebnis | Wirkt in |
| --- | --- | --- | --- |
| **A1** | Jeder Rumpf eine eigene `Welt` | **bleibt**, mit Nachweis (5.3) | M2 |
| **A2** | Stationen statt Fahr-Modus | **bleibt**, Fernbedienung als Fortschritt ergaenzt (6.3) | M3 |
| **A3** | Wie viele Spieler | **Einzelspieler**, spaeter je ein Spieler pro Wandler | M3 / nach M8 |
| **A4** | Wie viele Decks | **beliebig viele**, Titanklassen (5.4) - *geaendert* | M2 |
| **A5** | Was Geschosse treffen | **beides, Mech und Figuren** (5.5) - *umgedreht* | M4 |
| **A6** | Kritische Bauteile | **bleibt** | M4 |

#### A1 - Jeder Rumpf ist eine eigene `Welt` (5.1) - BLEIBT

*Entschieden:* bleibt, nachdem Der Meister die entscheidende Probe verlangt
hat - zwei Wandler nebeneinander, von einem zum anderen springen, Einschlaege
und Tote auf dem fremden Rumpf sehen.

**Beides geht.** Der Nachweis steht in **5.3, "Die Probe aufs Exempel"**:
Sehen ist eine Zeichenschleife ueber mehrere Welten mit je eigenem Versatz;
Springen ist der Sturzmechanismus aus 0.11.0, mit einem Rahmenwechsel beim
Absprung und einem beim Aufsetzen.

*Die Bedingung, die das erzwingt:* der Versatz eines Rumpfes ist eine
Kommazahl, keine Kachelkoordinate. Aendert nichts an heute geltenden Regeln.

*Warum nicht der andere Weg:* Weg B (beweglich Kacheln) verlangt, dass
Kollision, Sichtlinien und Kachelraster nicht mehr an ganzen Koordinaten
haengen - also `frei()`, `strahl()`, `bewegen()`, `ebene_zeichnen()` neu.

#### A2 - Stationen statt Fahr-Modus (6.1) - BLEIBT, ERWEITERT

*Entschieden:* bleibt. Der Meister hat gefragt, ob das fuers Programmieren
wichtig ist oder sich spaeter aendern laesst - **es laesst sich spaeter
aendern**, und sein eigener Entwurf ist dabei besser als der
urspruengliche.

*Sein Entwurf:* erst muss man zum Steuerpult gehen, spaeter geht es "ueber
Ingame-Bluetooth von ueberall", mit Upgrades, die entscheiden, ob man den
Wandler noch steuern kann, wenn man nicht drauf ist.

*Was daraus wurde:* die **Leiter der Entfernung** in 6.3. Aus drei
Zustaenden werden fuenf Sprossen, von "besetzt" bis "unbesetzt", und der
Fortschritt ist, diese Leiter hinaufzukaufen. Module heben nicht Schaden,
sondern **wie weit man sich entfernen darf**. Das ist die bessere
Fortschrittsachse, und sie stammt von ihm.

*Die eine Bedingung:* Stationsbelegung gehoert **an die Station**
(`wandler.stationen[...].bedient_von`), nicht als Zustand an den Spieler.
Dann ist Fernbedienung eine gelockerte Abstandspruefung. Kostet in M3 zehn
Minuten und spart spaeter, jede Station anzufassen.

*Sein zweiter Punkt, auch richtig:* Perspektive loest sich ueber die Ebenen
billig. Bestaetigt im Code - die Perspektive ist ein einziger projektiver
Faktor, der an `welt.hoehe()` haengt (Rechnung in 5.4).

*Der Zweifel bleibt stehen:* ob sich "am Steuer stehen und W halten"
unmittelbar genug anfuehlt, zeigt erst M3. Die Rettung waere klein - die
Kamera loest sich im Fahr-Blick von der Figur.

#### A3 - Wie viele Spieler (2.3) - EINZELSPIELER, SPAETER PvP

*Entschieden:* **erst Einzelspieler.** Spaeter ein Spieler pro Wandler;
zwei Spieler auf demselben Wandler bleiben als Nischenoption denkbar, nicht
als Entwurfsziel.

*Was das heisst:* Die Mechanik aus 6.3 bleibt unangetastet, denn sie wird
nur durch *zwei Menschen auf einem Rumpf* entwertet - und genau das ist zur
Nische erklaert. Ein Spieler pro Wandler laesst sie voll in Kraft: jeder
sitzt im selben Dilemma.

*Wann das faellig wird:* nach M8, und dort steht es auch. Ab M4 gibt es
ohnehin zwei Ruempfe; aus dem zweiten einen Menschen zu machen, ist dann
kein Umbau. Das Netz liegt fertig und dokumentiert auf `multiplayer-test`.

*Was jetzt schon dafuer getan wird:* nichts Eigenes - die Bedingung aus A2
(Belegung an der Station) genuegt bereits, weil eine Station, die weiss
*wer* sie bedient, auch einen zweiten Menschen kennt.

#### A4 - Wie viele Decks (5.4) - GEAENDERT: beliebig viele

*Entschieden:* **Die Obergrenze von vier Decks faellt.** Der Meister will
grosse und kleine Wandler nach dem Vorbild der Titanen aus Warhammer 40k -
vom Warhound bis zur Emperor-Klasse, je mit eigenen Vor- und Nachteilen,
eigenem Spielgefuehl und eigener Bedeutung in der Geschichte.

*Warum das billig ist:* `EBENEN_HOEHE` wird im ganzen Spiel an **genau
einer** Stelle gelesen, und das ist bereits eine Methode an der `Welt`.
Alles andere ruft `welt.hoehe(idx)`. Gibt jeder Rumpf sich seine eigene
Tabelle, folgen Perspektive, Sturz und Blickhoehe von selbst.

*Und die Tabelle ist eine Regel, keine Liste:* die heutigen fuenf Zahlen
kodieren einen konstanten Wahrnehmungsschritt von 0.895 je Deck (Rechnung
in 5.4). Daraus laesst sich jede Deckzahl erzeugen, und die ersten Werte
sind auf den Pixel die heutigen.

*Der Gewinn, der dabei umsonst anfaellt:* Groesse kostet Anwesenheit. Mehr
Decks heisst laengere Wege und damit schwerere Autopilot-Abzuege (6.3). Ein
Warhound beherrscht man ganz; einen Emperor-Titan nie. **Das ist der
Klassenunterschied, den Der Meister wollte, und er entsteht aus zwei
bereits getroffenen Entscheidungen statt aus einer neuen Mechanik.**

*Faellig:* M2. Nachtraeglich teuer, weil dann jede Karte auf fuenf feste
Hoehen gebaut waere.

#### A5 - Was Geschosse treffen (5.5) - UMGEDREHT

*Entschieden:* **Geschosse schlagen auf Mech- und Spielerebene ein**, so wie
in SAND. Die urspruengliche Trennung - Geschuetze nur gegen Rumpfteile,
Handwaffen nur gegen Figuren - ist gestrichen.

*Warum die Sorge dahinter unbegruendet war:* Der Grund zu entern ist nicht,
dass Geschuetze keine Leute toeten koennen - **der Grund ist die Beute**,
und die liegt an Bord (7.1). Wer den fremden Rumpf leerschiesst, steht
immer noch vor einer Maschine, in die er hineinmuss. Die Regel, die das
Entern traegt, stand schon da.

*Was die Balance stattdessen traegt* (ausgefuehrt in 5.5): Decks sind
Deckung und das Oberdeck ist keine; Geschuetze sind Flaechenwaffen mit
Flugzeit und zerlegen beim Leerschiessen genau die Bauteile, die man
erbeuten wollte; die eigene Maschine steht im Weg.

*Nebenbei:* technisch ist das die **einfachere** Loesung. Ein Einschlag ruft
einmal den Bauteilschaden und einmal das bestehende `welt.treffer()` auf,
statt zweier getrennter Trefferwege.

#### A6 - Kritische Bauteile statt Huellenbalken (6.6) - BLEIBT

*Entschieden:* bleibt, ohne Einwand.

Ein Wandler hat keinen Lebensbalken, sondern Bauteile mit eigenen Punkten -
Reaktor, Beine, Schwungrad, Geschuetze, Schotten, Rampe. Ein Treffer nimmt
eine Faehigkeit, nicht eine Zahl. Es ist lesbar, es erzeugt Geschichten
statt Prozenten, und es begruendet Q und die Werkstatt.

*Passt jetzt noch besser*, weil nach A5 derselbe Einschlag Bauteil und
Besatzung trifft - Schaden ist dadurch an einem Ort sichtbar statt in zwei
Balken.

### 14.3 Topf B - Spielgefuehl: zehn Entscheidungen, die warten koennen

Alle zehn sind am jeweiligen Meilenstein faellig, und bei allen ist
*ausprobieren* besser als *vorher entscheiden*. Sie stehen hier, damit sie
nicht vergessen werden, nicht damit sie jetzt beantwortet werden.

| # | Entscheidung | Im Plan steht | Alternative | Faellig |
| --- | --- | --- | --- | --- |
| **B1** | **Wie viel Maschine, wie viel Fuss?** | ausgewogen: Beschuss bis Phase 3, Entern als Hoehepunkt (7.1). Mit A5 ist die *Richtung* gesetzt - Beschuss ist toedlich, aber die Beute zwingt an Bord. Offen bleibt das Verhaeltnis. | Maschinenspiel mit Fussgefecht als Seltenheit, oder Fussspiel mit Maschine als Buehne | M4, durch Messen |
| **B2** | **Autopilot: wie schlecht ist "festgelegt"?** | eingeschraenkt, Zahlen offen (6.3) | gar nicht schlechter (dann ist es Komfort, keine Mechanik), oder viel schlechter | M3, durch Messen |
| **B3** | **Grundflaeche je Deck?** | 18x12, passt fast auf einen Bildschirm (5.7). Die *Hoehe* ist mit A4 entschieden, die Flaeche nicht. | deutlich groesser - man sieht nicht alles und muss suchen | M2 |
| **B4** | **Welche Decks, mit welchem Inhalt?** | Unterdeck/Hauptdeck/Bruecke/Oberdeck mit festen Aufgaben (5.4, 6.4) | frei belegbar, oder andere Aufteilung | M2 |
| **B5** | **Welche Titanklassen genau?** | drei Stufen als Anhalt: Warhound 2-3 Decks, Reaver/Warlord 4-6, Emperor 8-12 (5.4). Dass es sie gibt, ist mit A4 entschieden - die Zahlen nicht. | mehr oder weniger Stufen, andere Deckzahlen | M2, dann M7 |
| **B6** | **Wo kommen Enterer an Bord?** | an einer Stelle, wo die Bruecke aufsetzt (7.3) | mehrere Stellen gleichzeitig - deutlich haerter | M5 |
| **B7** | **Spiegelt die fremde Besatzung meine Stationen?** | ja, gleiche Logik gespiegelt (7.4) | eigene KI-Regeln, oder nur Waechter ohne Stationen | M5 |
| **B8** | **Was erbeutet man?** | Module aus dem fremden Rumpf (7.5) | Schrott und Blaupausen, keine Bauteile | M7 |
| **B9** | **Waffenstufen: je eine Zahl** | drei Stufen, je eine Zahl in `K.WAFFEN` (11.3) | Waffen mit neuen Faehigkeiten - macht die Balancetests wertlos | M7 |
| **B10** | **Wird der Wandler entworfen oder waechst er?** | er waechst Deck fuer Deck und Schacht fuer Schacht (6.5) | ein Bauplan-Editor wie in SAND - viel groesser | M7 |

**Zwei davon sind mehr als Feinheiten:**

**B1** entscheidet, was fuer ein Spiel das ist. Er ist absichtlich als
Messung in M4 eingeplant und nicht als Entscheidung jetzt - denn die
ehrliche Antwort bekommt man, indem man es spielt, nicht indem man darueber
nachdenkt. Falls Der Meister eine Vorliebe hat, aendert das die
Startreichweiten in `config.py` und sonst nichts.

**B2** ist die Zahl, an der 6.3 haengt. Ist "festgelegt" nicht schlechter
als "besetzt", gibt es keinen Grund, jemals an einer Station zu stehen, und
die ganze Mechanik fehlt. Ist es zu schlecht, verlaesst man die Bruecke
nie, und dann fehlt sie auch. Der richtige Wert liegt dazwischen und wird
gemessen.

---

### 14.4 Topf C - Kosmetik: jetzt ignorieren

Vollstaendigkeit halber, damit klar ist, worueber man **nicht** nachdenken
muss. Alles hier ist eine Zeile in `config.py` oder ein Zeichen in einer
Textdatei:

* Der Grundriss in 6.4, jede einzelne Kachel darin
* Welche Kachelzeichen fuer welche Marke stehen (5.6)
* Die Namen der Stationen und Module
* Jede Zahl, die im Dokument als Beispiel steht
* Welche Bilder und Klaenge es gibt
* Ob SHIFT "Ueberlast" oder "Boost" heisst

**Regel dafuer:** Wer baut, entscheidet das selbst und fragt nicht. Wenn es
falsch ist, sieht man es beim Spielen und aendert es.

---

### 14.5 Topf D - Fernziel: geparkt bis nach M8

Der Meister hat diesen Bereich ausdruecklich nach hinten gestellt. Die
Fragen stehen hier, damit sie nicht verloren gehen - **sie sind jetzt nicht
zu beantworten.**

1. **Bleibt Veld ein Knotengraph?** (9.1) Ungeprueft aus der alten Fassung
   uebernommen.
2. **Die Front-Zahlen:** 1 Spalte je 2 Etappen, 7 Spalten (9.2). Reine
   Erfindung.
3. **Sind die drei Fraktionen so?** Kolonne schwer und viele, Chor
   unbemannt und gleichgueltig, Werften friedlich (10.1). Die
   Fraktionsanteile stehen im Menue; ihr Charakter als Maschinen ist neu
   erfunden.
4. **Ist der Chor feindlich** oder gleichgueltig, solange man nicht stoert?
   Die zweite Antwort ist interessanter und billiger.
5. **Verliert man mit dem Wandler den Lauf** (7.3), oder laeuft man zu Fuss
   weiter und erbeutet sich einen neuen? Die zweite Antwort ist dramatischer
   und teurer.
6. **Kann man einen erbeuteten Wandler uebernehmen?** (7.5)
7. **Roguelite oder Kampagne?** Das Menue kennt "fortsetzen", EISERN kennt
   "ein leben". Beides ist moeglich, es sollte eines sein.
8. **Wie viel Tod zu Fuss?** Heute 100 Leben, Laeufer macht 9. Das ist
   zaeh. Passt das, wenn Enterer auf dem eigenen Deck stehen?
9. **Bleibt Wissen ueber einen Verlust hinaus?** (11.1)
10. **Was steht am Ende?** Und wie viele Enden gibt es?

**Punkt 8 ist der einzige, der frueher stoert:** Er betrifft M5 (Entern),
nicht M9. Falls sich das Fussgefecht auf den Decks zu zaeh anfuehlt, ist es
eine Zahl in `SPIELER` - aber sie sollte in M5 bewusst angesehen werden.

---

### 14.6 Und die Frage, die von letztem Mal offen ist

Der Meister schrieb *"da gibt es leider viele punkte, die bei dem plan
vollkommen falsch verstanden wurden"* und nannte den groessten. Diese
Sitzung hat einen zweiten geklaert: die Rangfolge - Story, Fraktionen und
Karte sind nicht die Prioritaet.

**Offen bleibt, ob das alle waren.** Was in 14.1 unter "Aus dem Repo" steht,
ist bestaetigt, aber aelter als die Korrektur, und was in Topf D steht, ist
grossteils ungeprueft aus der alten Fassung uebernommen. Beides ist jetzt
unkritisch, weil es Fernziel ist - **die Grundmechanik in M1 bis M8 haengt
an keinem Punkt daraus.** Es genuegt also, das nach M8 zu klaeren, oder wann
immer es ihm einfaellt.

---

## 15. Was dieses Dokument bewusst nicht tut

* Es legt keine Kachelzeichen fest, die noch nicht gebraucht werden.
* Es schreibt keine Dialoge.
* Es nennt keine Balancewerte ausser als Beispiel - die gehoeren in
  `config.py`, und zwar erst, wenn sie gemessen sind.
* Es behauptet nichts ueber SAND, was nicht belegt ist. Was dort nicht
  auffindbar war, steht in 2.1 als nicht auffindbar.
* Es entscheidet nichts aus Topf A oder D in Abschnitt 14.
* Es faengt nicht mit dem Fernziel an. Abschnitt 9 bis 11 stehen da, damit
  die Grundmechanik sie spaeter nicht ausschliesst - nicht als Auftrag.

**Wer hier weitermacht:**

1. Lies Abschnitt 1, 2 und 5 ganz, und Abschnitt 14.1 (was von Der Meister
   kommt und was Vorschlag ist).
2. Nimm den naechsten Meilenstein aus Abschnitt 13. Bis M8 ist das
   Grundmechanik - **M9 und M10 nicht anfangen**, solange M1 bis M8 nicht
   stehen und jedes System einzeln gemessen ist.
3. Halte die Front-Pruefpunkte des Meilensteins ein (Abschnitt 9.4). Sie
   sind billig und verhindern den einzigen Umbau, der sonst spaeter droht.
4. Halte dich an die drei Regeln aus dem README ("Wie sich das Spiel
   anfuehlen soll").
5. Verlangt ein Meilenstein etwas aus **Topf A** (14.2), frag nach. Etwas
   aus **Topf B** (14.3): bau es, miss es, und leg die Zahl danach fest.
   Etwas aus **Topf C** (14.4): entscheide selbst und frag nicht.

---

### Quellen zu Abschnitt 2

* [SAND: Raiders of Sophie auf Steam](https://store.steampowered.com/app/1431300/SAND_Raiders_of_Sophie/)
* [Besprechung bei KeenGamer](https://www.keengamer.com/articles/reviews/pc-reviews/sand-raiders-of-sophie-review-desert-pirates/)
* [Trampler-Ueberlebensleitfaden bei BlogAndGuide](https://www.blogandguide.com/sand-raiders-of-sophie-walker-trampler-survival-guide/)
* [Ueberblick im SAND-Wiki](https://www.sandraidersofsophie.xyz/guides/what-is-sand-raiders-of-sophie)
