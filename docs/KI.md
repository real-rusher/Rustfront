# DUSTFRONT - Der KI-Plan (zielorientierte KI, GOAP)

**Was das hier ist.** Der vollstaendige Plan fuer die KI aller Wesen in
DUSTFRONT: was schon gebaut ist, was der Besitzer will und in welcher
Reihenfolge es kommt. Nichts aus den Gespraechen soll verloren gehen.
Spaeter reicht ein Satz wie **"bau jetzt Schritt 4 ein"** oder **"bau
jetzt die Moral ein"**: hier steht, was das heisst.

**Fuer wen.** Fuer den Besitzer und fuer jede KI-Instanz, die spaeter an
der KI weiterbaut. Wer anfaengt, liest Abschnitt 1 (was steht), 3 (wie es
gebaut ist) und den Schritt in Abschnitt 6, der dran ist. Abschnitt 2 ist
die Richtschnur, an der sich jeder Schritt messen lassen muss.

**Stand beim Schreiben:** Version 0.34.29. Es gibt noch keine Kampagne,
keine grosse Karte, keine Berufe, Orte, Fraktionen und keine richtigen
NPCs - und im Mehrspieler laesst sich das meiste davon nicht sinnvoll
einbauen. Darum kommt jetzt **nur der Kern** (Schritte 1 und 2), so dass
man ihn im Testmodus arbeiten sieht. Alles andere folgt mit der Kampagne.
**Detailstufen (LOD) kommen erst, wenn sie noetig werden.**

---

## 1. Was schon steht (0.34.29)

| Teil | Datei | Was es tut |
| --- | --- | --- |
| Kern | `dustfront/goap.py` | Ausdruecke (sicher, ohne Code), Ziele, Aktionen, Planer (A*), Gehirn mit Protokoll |
| Daten | `dustfront/wesen_daten.py`, `wesen/*.txt` | Spezies, Ziele, Aktionen als Text wie die Karten; Laden, Pruefen, Neuladen |
| Bots | `dustfront/bot_goap.py`, `wesen/bots.txt` | `GoapHirn`: die Mehrspieler-Bots planen, statt einer festen Reihenfolge zu folgen |
| Regel | `regeln.py`, Feld `bot_ki` | BOT-KI: KLASSISCH / GOAP (Rundentafel, ERWEITERT) |
| Testmodus | `testmodus.py` | Spawner BOT mit HIRN KLASSISCH/GOAP; Taste 8 zweimal: GEDANKEN; Testmenue: KI-DATEN NEU LADEN, ZIEL ERZWINGEN |
| Pruefung | `tests/test_pruefung.py`, `tests/test_spiel.py` | Daten lesen sich, jeder Verweis und jedes Verhalten stimmt; Planer, Gehirn, Bots, Gedanken |

**So sieht man es:** Hauptmenue, TESTMODUS. Taste 4 (Spawner), BOT, mit
Tab zu den Einstellungen, HIRN auf GOAP, ein paar in ROT und ein paar
KLASSISCH in BLAU setzen. Taste 8 zweimal: links stehen die Gedanken der
GOAP-Figur am Zeiger - Merkmale, jedes Ziel mit seiner Dringlichkeit, der
Plan, die wahren Fakten und das Protokoll ("ZIEL ... PLAN ... FERTIG ...
GESCHEITERT"). Ueber jedem Bot steht `ZIEL > AKTION`. Im Testmenue (Esc)
laesst sich der gezeigten Figur ein Ziel aufzwingen, und nach einer
Aenderung an `wesen/bots.txt` laedt KI-DATEN NEU LADEN die Dateien, ohne
das Spiel neu zu starten.

Die klassische KI (`bots.py`, `bottaktik.py`) bleibt daneben, bis die
neue in allem besser ist. Beide teilen alles ausser der Entscheidung
(`BotHirn._entscheiden`): Sehen, Hoeren, Zielen mit Fehler und
Drehgrenze, Feuerstoesse, Wege, Treppen, Funk. Damit bleibt die Fairness
dieselbe.

---

## 2. Was der Besitzer will (die Antworten, vollstaendig)

Gesammelt im Gespraech vor 0.34.29. Jeder Punkt ist ein Auftrag; in
Klammern der Schritt aus Abschnitt 6, der ihn baut.

### 2.1 Wer bekommt die KI

* **Mehrspieler-Bots** (Schritt 2, steht), **Bosse** (3), **Zombies** (3)
  und die **NPCs der Kampagne** (7, 8).
* Die Zombies fliegen irgendwann aus dem Spiel. Bis dahin sind sie der
  Test, ob die KI auch **dumme Wesen** gut kann: wenige Ziele, kein Funk,
  keine Planung ueber zwei Schritte hinaus.

### 2.2 Spezies statt fester Gegner - das Alleinstellungsmerkmal

* **Alle Wesen beruhen auf Spezies**, mit **Persoenlichkeiten** und
  **Faehigkeiten**. Es gibt **keine fest programmierten Gegner und keine
  fest programmierten freundlichen NPCs**. Wer Feind ist, ergibt sich aus
  Fraktion, Beziehung und Lage - nicht aus der Klasse im Code.
* Spezies + **Merkmale** (gewuerfelt je Wesen, Bereiche in der Datei).

### 2.3 Die Kampagne

* **Fraktionen und Zombies**; die Fraktionen bekaempfen sich auch
  untereinander.
* NPCs: **Begleiter**, **Haendler und Neutrale**, **Gefangene und
  Zivilisten** "und noch viel mehr", zum Beispiel **Roboter** - und der
  **Omnissiah: eine echte KI-Entitaet** in der Welt.

### 2.4 Ziele

* **Ueberleben / Rueckzug**, **Gebiet halten**, **Patrouille**, **Alarm und
  Verstaerkung** - "eigentlich ein ganzes Leben".
* Dazu: **Pluendern**, **Spuren verfolgen**, **Verwundete retten**,
  **Hinterhalt**.

### 2.5 Alltag (Schritt 8)

* **Beduerfnisse** (Hunger, Schlaf, Sicherheit ...).
* **Arbeit und Tagesablauf**.
* **Besitz und Wirtschaft**.
* **Beziehungen** (zu Einzelnen und zu Fraktionen).

### 2.6 Moral (Schritt 4)

* **Fliehen**, **sich ergeben**, **Panik / Zoegern**, **Wut / Rache**.

### 2.7 Umgebung

* **Tueren, Aufzuege, Leitern** benutzen.
* **Fahrzeuge** - in der Kampagne. **Die Mehrspieler-Bots bleiben ohne
  Autos.**
* **Geraete und Geschuetze** bedienen; **Deckung bauen und zerstoeren**.
* **Jemand muss die Riesenmechs steuern** - ein Mech ist ein Fahrzeug,
  das ein Wesen bedient, keine eigene KI.

### 2.8 Anfuehrer und Karriere (Schritt 6)

* **Anfuehrer und Karrieren**, aber **kein Wissen ueber das Team, das sie
  nicht haben koennen** (keine Allwissenheit der Gruppe).
* NPCs **reden miteinander**, **verraten**, **geben und nehmen Befehle**,
  **steigen im Rang auf**.

### 2.9 Wissen und Kommunikation (Schritt 5)

* Wissen kommt ueber **Funk und Sprache** - aber **nicht fuer alle gleich
  fest eingebaut**: eine Faehigkeit der Spezies.
* **Schwarm-Roboter brauchen keinen Funk** (sie teilen ihr Wissen
  unmittelbar), **primitive Barbaren haben keinen** (nur Rufen, so weit
  die Stimme reicht).

### 2.10 Anpassung an den Spieler

* **Innerhalb einer Begegnung** (wer zweimal von links kommt, wird links
  erwartet) und **ueber die Kampagne** (eine Fraktion lernt die Vorlieben
  des Spielers).

### 2.11 Fairness und Schwierigkeit

* Fairness haengt an der **Schwierigkeit**. Die Schwierigkeit veraendert:
  **was sie wissen**, **wie klug sie planen**, **Zielen und Reaktion**,
  **die Verteilung der Persoenlichkeiten**.
* **Fehler kommen aus der Persoenlichkeit** (der Ungeduldige stuermt zu
  frueh, der Aengstliche schiesst daneben), nicht aus einem Wuerfel.

### 2.12 Sichtbarkeit - was der Spieler mitbekommt

* **Funk als Untertitel** (steht seit 0.34.27).
* **Symbole und Haltung** (wer Angst hat, sieht so aus).
* **Funk abhoeren** (wer ein Funkgeraet der anderen hat, liest mit).
* **Gespraeche** zwischen NPCs.
* **Eine Ansicht im Testmodus** dafuer (steht: GEDANKEN).

### 2.13 Groesse

* **Hunderte NPCs, die Welt wird simuliert.**
* **Detailstufen erst, wenn sie noetig werden** (Schritt 9).

### 2.14 Einfuehrung, Format, Werkzeuge

* **Als Regel neben der alten KI** (steht: BOT-KI).
* **Eigenes Textformat** wie die Karten (steht: `wesen/*.txt`).
* Werkzeuge im Testmodus: **Plan- und Gedankenansicht** (steht),
  **Eingreifen** - Ziel erzwingen (steht), Werte setzen, Befehle geben
  (Schritt 5/6) -, **Protokoll und Zeitleiste** (Protokoll steht,
  Zeitleiste Schritt 5), **Aufnahme und Wiedergabe** (Schritt 5, braucht
  Determinismus).

### 2.15 Der Spieler

* Der Spieler kann **Befehle geben**, **im Rang aufsteigen**, **verraten
  werden** und **verhandeln**.
* **Er hat dieselben Moeglichkeiten wie die Bots, nur mehr in der
  Tiefe.** Rollenspielartig: **jede Rolle einnehmen und die Welt
  veraendern**.

### 2.16 Mehrspieler

* Mannschaften bleiben eine **Regel** des Spiels: **Bots sind loyal**.
  Anfuehrer und Befehle sind erlaubt, **Verrat nicht**.

### 2.17 Anfang

* **Kern und Mehrspieler-Bots zuerst** (Schritte 1 und 2, stehen).

---

## 3. Wie es gebaut ist

### 3.1 Die Schichten

Von aussen nach innen, jede nur mit der naechsten verbunden:

```
 Welt  ──>  Sinne  ──>  Wissen  ──>  Fakten/Zahlen  ──>  Gehirn  ──>  Verhalten  ──>  Eingabe
(world)    sieht()     gesehen{}    fuehlen()          goap.Gehirn    TUN[...]       _anwenden
           hoeren()    verdacht     (bot_goap)         Ziele, Plan    tun_kaempfen   wie ein Mensch
```

* **Sinne** sind fair und gehoeren zur Spezies, nicht zum Gehirn: Sicht
  durch Mauern nicht, Reaktionszeit, Blendung. Heute: `BotHirn.sieht`,
  `_hoeren`, `_wahrnehmen`.
* **Wissen** ist, was das Wesen gesehen, gehoert oder gesagt bekommen hat,
  mit Zeit und Quelle. Heute: `gesehen` (Wesen -> Ort, Ebene, Zeit) und
  `verdacht`. Schritt 5 macht daraus einen eigenen Speicher.
* **Fakten und Zahlen** sind die Sicht des Gehirns auf das Wissen:
  `feind_sichtbar`, `in_deckung`, `leben` ... Ausgerechnet von `fuehlen()`.
  Das Gehirn sieht nie die Welt selbst - nur das. Damit kann es nie mehr
  wissen, als das Wesen weiss.
* **Gehirn** (`goap.Gehirn`): rechnet die Dringlichkeit jedes Ziels,
  nimmt das dringendste, das noch nicht erfuellt ist, plant den billigsten
  Weg dorthin (A* ueber die Wahrheitswerte) und gibt die erste Aktion
  zurueck. Das laufende Ziel hat einen Vorsprung (`K.GOAP["vorsprung"]`),
  damit es nicht bei jedem Wackeln wechselt; spaetestens nach
  `neu_planen` Sekunden wird neu geplant; eine gescheiterte Aktion bleibt
  `sperre` Sekunden draussen.
* **Verhalten** (`TUN` in `bot_goap.py`): was eine Aktion tut, ein Stueck
  Code je `tut:`. Meldet "laeuft", "fertig" oder "gescheitert".
* **Eingabe**: das Verhalten liefert Laufrichtung, Zielpunkt, Feuern -
  daraus wird eine Eingabemeldung wie die eines Menschen (`eingabe`,
  `_anwenden`). Ein Bot kann nichts, was ein Spieler nicht kann.

### 3.2 Netz

Die KI rechnet **nur der Gastgeber**. Ueber das Netz geht nichts von ihr,
ausser was man sehen soll (Funk `fk`/`fr`, spaeter Symbole). Darum
braucht eine neue Aktion keine neue Netzversion - eine neue Regel oder
ein neues sichtbares Feld schon (`docs/MEHRSPIELER.md`).

### 3.3 Determinismus

Fuer Aufnahme und Wiedergabe (Schritt 5) muss ein Gefecht mit demselben
Startwert und denselben Eingaben gleich ablaufen. Heute schon: der
Planer ist deterministisch (feste Reihenfolge, Gleichstand nach
Einfuegezahl), die Bots wuerfeln mit `self._bot_rnd`. Noch nicht: einige
Stellen nehmen `random.random()` direkt, und die Weltzeit haengt am
Zeitfaktor. Bei Schritt 5 alle Zufaelle auf je einen `random.Random` je
Gefecht umstellen.

### 3.4 Was das Gehirn kostet

Ein Denkschritt je Wesen alle `K.GOAP["takt"]` Sekunden (0,1 s), nicht je
Bild. Der Planer ist begrenzt (`tiefe` 6, `knoten` 400). Fuer die Bots
(hoechstens 16) ist das nichts. Fuer Hunderte NPCs: Schritt 9.

---

## 4. Das Datenformat (`wesen/*.txt`)

Jede Datei im Ordner `wesen/` wird gelesen; ein Name darf ueber alle
Dateien nur einmal vorkommen. `#` beginnt einen Kommentar. Ein Block je
Ding:

```
[ziel nachladen]
will: !magazin_leer
dringlich: 80 * magazin_leer * munition_da
info: Ein leeres Magazin muss voll, bevor er weiterkaempft.

[aktion nachladen_in_deckung]
braucht: in_deckung, magazin_leer
macht: !magazin_leer
kosten: 1
tut: nachladen
funk: nachladen
info: ...

[spezies mp_bot]
name: BOT
ziele: ueberleben, nachladen, ...
aktionen: angreifen, flankieren, ...
merkmal mut: 0.2 0.9
merkmal disziplin: 0.3 1.0
info: ...
```

| Feld | In | Bedeutung |
| --- | --- | --- |
| `will` | ziel | Fakten, die gelten sollen. Komma trennt, `!` heisst "nicht" |
| `dringlich` | ziel | Rechnung: wie dringend (0 oder weniger: gar nicht) |
| `braucht` | aktion | Fakten, die gelten muessen, damit die Aktion geht |
| `macht` | aktion | Fakten, die danach gelten (fuer den Planer) |
| `kosten` | aktion | Rechnung: wie teuer (der Planer nimmt die billigste Folge) |
| `tut` | aktion | welches Verhalten (`bot_goap.TUN`); fehlt es, der Name |
| `funk` | aktion | Anlass in `K.BOTS["funk"]`, der beim Beginn angesagt wird |
| `ziele`, `aktionen` | spezies | was diese Spezies kennt |
| `merkmal NAME: VON BIS` | spezies | jedes Wesen wuerfelt seinen Wert dazwischen |
| `name` | spezies | Anzeige |
| `info` | alle | Erklaerung, steht im Testmodus |

**Rechnungen** (`goap.Ausdruck`): Zahlen, Namen (Fakten sind 1 oder 0,
Zahlen wie `leben`, Merkmale wie `mut`; Unbekanntes ist 0), `+ - * /`,
Vergleiche (`abstand < 260` ist 1 oder 0), `and`, `or`, `not`,
`a if b else c`, `min`, `max`, `abs`. Sonst nichts - geprueft beim Laden,
eine Datendatei kann nie Code ausfuehren.

**Ziel-Fakten**, die nie wahr werden (`feind_besiegt`), sind erlaubt: sie
benennen nur, wohin der Planer will. Die Aktion, die sie "macht", laeuft,
bis ihr Verhalten "fertig" meldet.

Fehler kosten nur ihren Block und stehen mit Datei und Zeile in
`wesen_daten.pruefen()`; `tests/test_pruefung.py` haelt das sauber.

### 4.1 Die Fakten der Mehrspieler-Bots

Stehen oben in `wesen/bots.txt` und werden in `GoapHirn.fuehlen`
ausgerechnet. Wer einen neuen Fakt braucht, traegt ihn an beiden Stellen
ein.

---

## 5. Wie man etwas dazubaut

| Was | Wo |
| --- | --- |
| Ein Ziel oder eine Aktion aus vorhandenen Fakten und Verhalten | nur `wesen/*.txt`, im Testmodus KI-DATEN NEU LADEN |
| Ein neuer Fakt | `fuehlen()` der Wesenart (heute `bot_goap.py`) + Kopf der Datendatei |
| Ein neues Verhalten | eine Methode `tun_NAME` in `bot_goap.py` (oder dem Hirn der Wesenart); `TUN` findet sie von selbst |
| Eine neue Spezies | ein `[spezies ...]`-Block; wer sie benutzt, uebergibt ihren Namen dem Hirn |
| Neue Zahlen zum Einstellen | `K.GOAP` in `config.py` |

Und immer (AGENTS.md): Eintrag im Spawner, Zeile im Testmenue oder Taste,
die INFO-Ansicht zeigt das Neue, ein Test, eine Zeile in
`docs/TESTMODUS.md`.

---

## 6. Der Fahrplan

Jeder Schritt ist eine eigene Version, jeder im Testmodus sichtbar.

| Schritt | Was | Stand |
| --- | --- | --- |
| 1 | Kern: Planer, Gehirn, Datenformat, Pruefung, Gedankenansicht | **fertig, 0.34.29** |
| 2 | Mehrspieler-Bots auf GOAP, als Regel BOT-KI neben der klassischen | **fertig, 0.34.29** |
| 3 | Zombies und Bosse auf GOAP: dumme Wesen, Spezies-Dateien | offen |
| 4 | Persoenlichkeit, Moral, Fehler aus Merkmalen, Symbole und Haltung | offen |
| 5 | Wissen und Kommunikation; Zeitleiste; Aufnahme und Wiedergabe | offen |
| 6 | Anfuehrer, Befehle, Raenge (auch fuer den Spieler) | offen |
| 7 | Kampagne: Fraktionen, Beziehungen, Verrat, Verhandeln, Ergeben | wartet auf die Kampagne |
| 8 | Alltag: Beduerfnisse, Tagesablauf, Arbeit, Besitz, Orte | wartet auf Karte und Orte |
| 9 | Weltsimulation: Hunderte NPCs, Detailstufen, Fahrzeuge, Mechs, Geschuetze, Bauen | wartet, LOD erst wenn noetig |

### Schritt 3 - Zombies und Bosse ("bau jetzt die Zombies auf GOAP")

* `KampfGegner` (und `entities.Gegner` im Einzelspieler) bekommen ein
  optionales Hirn wie die Bots: `gegner_goap.py` mit `fuehlen()` (ziel
  sichtbar, ziel nah, angeschlagen, Brut-Ziel, auf Treppe ...) und
  Verhalten (`jagen`, `schlagen`, `springen`, `brueten`, `wandern`), das
  die vorhandenen Bewegungsstuecke benutzt.
* Je Gegnerart eine `[spezies]` in `wesen/zombies.txt` und
  `wesen/bosse.txt` - Laeufer kennen zwei Ziele, ein Boss ein paar mehr.
  Was heute als Sonderfall in `KampfGegner` steht (Brueter, Springer),
  wird Aktion.
* Regel "GEGNER-KI: KLASSISCH / GOAP" (pve, gilt nur beim Gastgeber),
  Spawner: GEGNER und BOSSE bekommen die Einstellung HIRN.
* Gedankenansicht fuer jedes Wesen mit Gehirn, nicht nur Bots.
* Erfolgsmass: die Zombies spielen sich gleich (Wellen gleich schwer),
  der Boss zeigt Phasen als Ziele.

### Schritt 4 - Persoenlichkeit und Moral ("bau jetzt die Moral ein")

* Merkmale, die alle Spezies teilen koennen: `mut`, `disziplin`,
  `geduld`, `jaehzorn`, `treue`, `neugier`. Bereiche je Spezies, die
  Schwierigkeit verschiebt die Verteilung (2.11).
* Eine Zahl **Moral** (0 bis 1) je Wesen: sinkt durch Treffer, gefallene
  Kameraden, Unterzahl, Feuer, Explosionen; steigt durch Anfuehrer in der
  Naehe, Abschuesse, Ruhe. Daraus Fakten: `panik`, `zoegert`, `wuetend`.
* Ziele: `fliehen` (weg vom Gegner, zu Kameraden), `ergeben` (Waffe
  runter, Haende hoch - im Mehrspieler aus, dort Regel), `rache` (den, der
  den Freund erschoss), Panik (wegrennen, blind feuern), Zoegern (kurz
  stehen bleiben).
* **Fehler aus der Persoenlichkeit:** Kosten und Dringlichkeiten haengen
  an Merkmalen (der Ungeduldige stuermt frueh, `nachladen_offen` ist fuer
  Mutige billig - so schon in `wesen/bots.txt`), dazu Zielfehler aus
  Angst (`unterdrueckt_fehler` gibt es schon).
* **Symbole und Haltung:** ein kleines Zeichen ueber dem Kopf (Angst,
  Wut, ergibt sich) und eine Haltung der Figur; als Feld in der
  Weltmeldung (neue Netzversion).
* Testmodus: Merkmale und Moral der Figur am Zeiger **setzen** (Testmenue
  "WERT SETZEN"), Moral als Balken in der Gedankenansicht.

### Schritt 5 - Wissen und Kommunikation ("bau jetzt Wissen und Funk ein")

* Ein **Wissensspeicher** je Wesen: Eintraege (was, wo, wann, woher:
  gesehen / gehoert / gesagt), sie altern und werden unsicher. `gesehen`
  und `verdacht` der Bots gehen darin auf.
* **Kommunikation als Faehigkeit der Spezies:** `funk` (Reichweite
  unbegrenzt, nur die eigene Fraktion, abhoerbar), `stimme` (Reichweite,
  durch Mauern gedaempft, jeder in der Naehe hoert), `schwarm` (sofort,
  ohne Nachricht). Barbaren: nur `stimme`. Schwarmroboter: nur `schwarm`.
* Nachrichten sind Wissen ("Gegner bei X", "ich lade", "brauche Hilfe"),
  der Funk-Untertitel ist ihr Text. **Abhoeren**: wer ein Funkgeraet der
  anderen traegt, liest ihren Funk.
* **Gespraeche**: zwei NPCs, die beide nichts zu tun haben, tauschen
  Wissen und Saetze aus (Text ueber den Koepfen).
* Testmodus: **Zeitleiste** (je Wesen eine Leiste, Ziele als farbige
  Abschnitte, anklickbar), **Aufnahme und Wiedergabe** (Startwert +
  Eingaben aufschreiben, zurueckspulen) - dafuer 3.3.

### Schritt 6 - Anfuehrer, Befehle, Raenge ("bau jetzt Anfuehrer ein")

* Ein Wesen kann **Anfuehrer** einer Gruppe sein (Rang, Merkmal
  `fuehrung`). Er plant fuer die Gruppe (die heutigen Stuerme der
  Mannschaft in `bottaktik.stuerme_fuehren` werden sein Werkzeug) und gibt
  **Befehle**: das sind Ziele mit hoher Dringlichkeit beim Empfaenger -
  angenommen nach `disziplin` und `treue`, nicht immer.
* **Kein Teamwissen ohne Weg:** ein Befehl und jede Lagemeldung gehen ueber
  den Wissensspeicher (Schritt 5). Wer keinen Funk hat, muss rufen.
* **Raenge und Aufstieg**: Abschuesse, Rettungen, erfuellte Befehle geben
  Ansehen; der Beste wird Anfuehrer, faellt einer, rueckt einer nach.
* **Der Spieler** kann Befehle geben (Rufen-Taste, Befehlsrad), und im
  Mehrspieler fuehrt er Bots seiner Mannschaft. Bots sind dort **loyal**:
  kein Verrat, Befehle des Menschen gehen vor.
* Testmodus: Befehle an die Figur am Zeiger geben, Gruppen und Raenge in
  der INFO-Ansicht.

### Schritt 7 - Kampagne: Fraktionen ("bau jetzt die Fraktionen ein")

* **Fraktionen** mit Beziehungen untereinander (-1 Krieg bis +1 Bund),
  Fraktionen bekaempfen sich auch gegenseitig. **Feind ist, wen die
  Beziehung dazu macht**, nicht eine Klasse (2.2).
* **Beziehungen zwischen Einzelnen** (Freund, Rivale, Schuld) - Grund fuer
  Rache, Treue und **Verrat** (Ziel `verraten`, wenn die eigene Fraktion
  einem schadet und `treue` niedrig ist).
* **Verhandeln, Ergeben, Gefangene**: Ziele und Aktionen mit Gegenueber
  (der Spieler kann dieselben benutzen - 2.15).
* NPC-Arten als **Spezies, nicht als Klassen**: Begleiter, Haendler,
  Neutrale, Gefangene, Zivilisten, Roboter. Der **Omnissiah** ist eine
  eigene Spezies mit eigenem Gehirn (vielleicht spaeter mit einem echten
  Sprachmodell als Stimme - eine eigene Entscheidung).
* **Anpassung ueber die Kampagne** (2.10): eine Fraktion merkt sich, wie
  der Spieler kaempft (Waffen, Wege, Uhrzeit), und waehlt danach Ziele
  und Ausruestung.

### Schritt 8 - Alltag ("bau jetzt den Alltag ein")

* **Beduerfnisse** als Zahlen, die mit der Zeit steigen (Hunger, Schlaf,
  Sicherheit, Gesellschaft) und Ziele dringlich machen.
* **Orte als schlaue Objekte**: ein Bett, eine Werkbank, eine Wache sagt
  selbst, welche Aktionen sie anbietet (wie ein Geschuetz "bedienen"). So
  muss das Gehirn keine Orte kennen - nur das, was in der Naehe angeboten
  wird.
* **Tagesablauf und Berufe**: ein Beruf ist eine Gruppe von Zielen mit
  Uhrzeiten (Wache: Patrouille 6 bis 18 Uhr).
* **Besitz und Wirtschaft**: Dinge gehoeren jemandem; stehlen ist eine
  Aktion mit Folgen fuer Beziehungen; Haendler kaufen und verkaufen.

### Schritt 9 - Weltsimulation ("bau jetzt die Weltsimulation ein")

* **Hunderte NPCs**: Detailstufen erst jetzt. Nah: volles Gehirn je
  0,1 s. Mittel: Denken selten, Bewegung auf Wegen. Fern: nur noch
  Zustandswechsel je Minute ("ist zur Arbeit gegangen").
* **Fahrzeuge** (Kampagne; Mehrspieler-Bots bleiben ohne), **Mechs** (ein
  Wesen steuert ihn - Aktion `einsteigen`, dann Verhalten des Fahrzeugs),
  **Geschuetze und Geraete** (bedienen), **Deckung bauen und zerstoeren**,
  **Tueren, Aufzuege, Leitern** (die Wege kennen Treppen und Aufzuege
  schon).

---

## 7. Was nicht geht (und warum)

* **Kein Teamwissen ohne Weg** (2.8): das Gehirn sieht nur `fuehlen()`,
  `fuehlen()` nur das eigene Wissen. Wer eine Abkuerzung einbaut ("alle
  Bots wissen, wo der Spieler ist"), bricht die Fairness.
* **Der Beobachter des Testmodus** steht in keiner Liste, die die KI
  befragt (`welt.wesen`, `kaempfer`), und neue Wahrnehmung fragt genau
  diese Listen (AGENTS.md).
* **Keine Rechnung in den Daten, die Code ausfuehrt** (4).
