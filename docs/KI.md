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

**Stand beim Schreiben:** Version 0.34.29, Schritt 3 in 0.34.30. Es gibt noch keine Kampagne,
keine grosse Karte, keine Berufe, Orte, Fraktionen und keine richtigen
NPCs - und im Mehrspieler laesst sich das meiste davon nicht sinnvoll
einbauen. Darum kommt jetzt **nur der Kern** (Schritte 1 und 2), so dass
man ihn im Testmodus arbeiten sieht. Alles andere folgt mit der Kampagne.
**Detailstufen (LOD) kommen erst, wenn sie noetig werden.**

---

## 1. Was schon steht (0.34.29 und 0.34.30)

| Teil | Datei | Was es tut |
| --- | --- | --- |
| Kern | `dustfront/goap.py` | Ausdruecke (sicher, ohne Code), Ziele, Aktionen, Planer (A*), Gehirn mit Protokoll |
| Daten | `dustfront/wesen_daten.py`, `wesen/*.txt` | Spezies, Ziele, Aktionen als Text wie die Karten; Laden, Pruefen, Neuladen |
| Bots | `dustfront/bot_goap.py`, `wesen/bots.txt` | `GoapHirn`: die Mehrspieler-Bots planen, statt einer festen Reihenfolge zu folgen |
| Gegner (0.34.30) | `dustfront/gegner_goap.py`, `wesen/zombies.txt` | `GegnerHirn`: Zombies, Speier und Bosse des Mehrspielers; ersetzt nur `Gegner._wohin` |
| Regeln | `regeln.py`, Felder `bot_ki`, `gegner_ki` | BOT-KI und GEGNER-KI: KLASSISCH / GOAP (Rundentafel, ERWEITERT) |
| Testmodus | `testmodus.py` | Spawner BOT, GEGNER und BOSSE mit HIRN KLASSISCH/GOAP; Taste 8 zweimal: GEDANKEN; Testmenue: KI-DATEN NEU LADEN, ZIEL ERZWINGEN |
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
hirn: bot
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
| `tut` | aktion | welches Verhalten (`bot_goap.TUN`, `gegner_goap.TUN`); fehlt es, der Name |
| `funk` | aktion | Anlass in `K.BOTS["funk"]`, der beim Beginn angesagt wird |
| `ziele`, `aktionen` | spezies | was diese Spezies kennt |
| `merkmal NAME: VON BIS` | spezies | jedes Wesen wuerfelt seinen Wert dazwischen |
| `name` | spezies | Anzeige |
| `hirn` | spezies | `bot` oder `gegner`: welches Hirn, und damit welche `tut:` erlaubt sind |
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

### 4.1 Die Fakten der Mehrspieler-Bots und der Gegner

Stehen oben in `wesen/bots.txt` (ausgerechnet in `GoapHirn.fuehlen`) und
in `wesen/zombies.txt` (`GegnerHirn.fuehlen`). Wer einen neuen Fakt braucht, traegt ihn an beiden Stellen
ein.

---

## 5. Wie man etwas dazubaut

| Was | Wo |
| --- | --- |
| Ein Ziel oder eine Aktion aus vorhandenen Fakten und Verhalten | nur `wesen/*.txt`, im Testmodus KI-DATEN NEU LADEN |
| Ein neuer Fakt | `fuehlen()` der Wesenart (heute `bot_goap.py`) + Kopf der Datendatei |
| Ein neues Verhalten | eine Methode `tun_NAME` in `bot_goap.py` oder `gegner_goap.py`; `TUN` findet sie von selbst |
| Ein neues Hirn (eine neue Wesenart) | eine Klasse mit `fuehlen`, `tun_*` und `TUN`, eingetragen in `wesen_daten.hirne()` |
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
| 3 | Zombies und Bosse auf GOAP: dumme Wesen, Spezies-Dateien | **fertig, 0.34.30** (Mehrspieler; der Einzelspieler bleibt klassisch) |
| 4 | Persoenlichkeit, Moral, Fehler aus Merkmalen, Symbole und Haltung | offen |
| 5 | Wissen und Kommunikation; Zeitleiste; Aufnahme und Wiedergabe | offen |
| 6 | Anfuehrer, Befehle, Raenge (auch fuer den Spieler) | offen |
| 7 | Kampagne: Fraktionen, Beziehungen, Verrat, Verhandeln, Ergeben | wartet auf die Kampagne |
| 8 | Alltag: Beduerfnisse, Tagesablauf, Arbeit, Besitz, Orte | wartet auf Karte und Orte |
| 9 | Weltsimulation: Hunderte NPCs, Detailstufen, Fahrzeuge, Mechs, Geschuetze, Bauen | wartet, LOD erst wenn noetig |

### Schritt 3 - Zombies und Bosse ("bau jetzt die Zombies auf GOAP")

**Entscheidung des Besitzers (0.34.36): Zombies und Bosse bleiben vorerst
klassisch.** "Die brauchen erstmal kein GOAP." Der Code bleibt, Vorgabe
ist KLASSISCH (Regel GEGNER-KI, Spawner HIRN), auch in den Aufnahmen.
Weiter geht es mit den Bots und spaeter den Menschen der Kampagne
(Abschnitt 8).

**Gebaut in 0.34.30**, so:

* `Gegner.schritt` ist geteilt in `_wohin` (Entscheidung, wohin und ob
  er zuschlaegt) und `_laufen` (Bewegung). `KampfGegner.hirn`
  (`gegner_goap.GegnerHirn`) ersetzt nur `_wohin`. Wen er jagt, waehlt er
  wie bisher (`_ziel_waehlen`).
* `wesen/zombies.txt`: Spezies `zombie` (hinlaufen, zuschlagen, ohne Ziel
  herumirren), `speier` (in Spuckweite gehen, spucken), `boss` (lauern,
  wenn das Ziel auf einer anderen Ebene ist; angeschlagen die Faehigkeit
  vorziehen - zweite Phase). Gibt es eine Spezies mit dem Namen einer
  Art, gilt diese (`gegner_goap.spezies_fuer`).
* Die Faehigkeit eines Bosses ist ein **Reflex**: sie zaehlt ihren Takt
  neben dem Plan her. Ohne das waere ein GOAP-Boss schwaecher.
* Jede Spezies sagt mit `hirn: bot` oder `hirn: gegner`, welche Verhalten
  ihre Aktionen haben duerfen; `wesen_daten.pruefen` prueft das.
* Regel GEGNER-KI (Spielarten mit Gegnern), die Brut denkt wie ihre
  Mutter, die Zielpuppe nie. Spawner: HIRN bei GEGNER und BOSSE.
* Der Einzelspieler (`entities.Gegner`, `play.py`) bleibt klassisch - er
  hat keine Regeln; das kommt mit der Kampagne.

Der urspruengliche Entwurf:

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

---

## 8. Menschen im Gefecht (Entwurf, 0.34.36)

Gemeldet nach den Aufnahmen: "Ich finde das GOAP jetzt noch nicht so
ueberzeugend ... wie du das genau machen wuerdest, dass sie wirklich wie
Menschen agieren. Also nicht wie die Spieler im Spiel, sondern wie als
wuerden sie in dieser Welt leben, in normalen Combat-Situationen, auch
wenn sie keine Vorgeschichte und kein Leben haben. Dass sie Panik haben,
dass sie uebermuetig werden, dass sie nicht perfekt agieren ... mit einem
Maschinengewehr, schon voll am Feuern ... eher nicht ihre Position
verlassen, sondern eher noch niederhalten ... mit einer Shotgun eher
naeher rangehen und eher die sind, die stuermen ... eher mit ihrem Team
zusammen irgendwo reingehen, als dass sie alleine eine Rolle ausfuellen."

Das ist **Schritt 4 (Moral) plus ein Teil von Schritt 6 (Trupp)** aus dem
Fahrplan, so zugeschnitten, dass er schon im Mehrspieler geht - ohne
Welt, ohne Vorgeschichte. Auftrag spaeter: "bau jetzt Abschnitt 8A ein"
usw.

### 8.1 Warum es heute nicht ueberzeugt

* **Es ist zu richtig.** GOAP nimmt immer den billigsten Plan. Menschen
  im Gefecht nehmen den, der sich gerade richtig anfuehlt - und der
  haengt an Angst, Zuversicht und Gewohnheit, nicht an einer Rechnung.
* **Es gibt kein Innenleben.** Ein Bot hat zwei Merkmale (Mut,
  Disziplin) und sonst nur die Lage. Was eben passiert ist (der Kamerad
  neben ihm faellt), aendert nichts an ihm.
* **Jeder spielt allein.** Rollen (Flanke, Druck) werden einzeln
  vergeben; ein Trupp, der zusammen vorgeht, entsteht nur zufaellig.
* **Die Waffe sagt nichts ueber den Menschen.** Wer ein MG hat, verhaelt
  sich wie jeder andere, nur mit anderem Abstand.
* **Nichts ist traege.** Neu geplant wird alle 0,6 s; ein Mensch bleibt
  bei dem, was er angefangen hat, oft laenger als klug.

### 8.2 Aufbau: drei Ebenen

1. **Trupp** (2 bis 4 Mann, einer fuehrt): kennt wenige **Truppplaene** -
   vorruecken in Spruengen (einer bewegt sich, der andere deckt),
   Feuerkampf halten, Stellung stuermen (sammeln, Granate, Spitzenmann
   zuerst, die anderen dicht dahinter), Rueckzug unter Feuerschutz.
   Gebaut als kleine HTN (hierarchische Aufgaben), wie Killzone 2 und
   Decima es tun (Abschnitt 9) - nach dem Lesen der Quellen zuerst als
   Truppzustaende mit Bedingungen, siehe 10.4. Der Truppfuehrer verteilt Rollen als
   **Auftraege**: ein Ziel mit hoher Dringlichkeit beim Einzelnen - der es
   nach Disziplin, Stress und Zuversicht annimmt oder nicht. Wissen geht
   nur ueber Funk und Sicht (Abschnitt 7).
2. **Einzelner**: waehlt sein Ziel mit **Nutzenkurven** (Utility, wie
   Dave Marks IAUS) statt mit festen Dringlichkeiten: jede Ueberlegung
   ("wie nah ist der Gegner", "wie gestresst bin ich", "wie voll ist das
   Magazin") ist eine Kurve von 0 bis 1, das Produkt ist die
   Dringlichkeit. Ausgefuehrt wird mit GOAP wie jetzt, aber mit kurzen
   Plaenen (2 bis 4 Schritte, so lang wie bei Killzone 3 gemessen).
3. **Koerper**: Sehen, Hoeren, Zielen, Reaktion - wie heute, aber vom
   Innenleben beeinflusst (8.3, 8.6).

### 8.3 Innenleben: Stress und Zuversicht

Zwei Zahlen je Mensch, 0 bis 1, die **Ereignisse** veraendern und die
mit der Zeit zurueckgehen:

| Ereignis | Stress | Zuversicht |
| --- | --- | --- |
| Kugel knapp vorbei (Unterdrueckung, gibt es schon) | + | |
| selbst getroffen | ++ | - |
| Kamerad faellt (gesehen oder gefunkt) | ++ | -- |
| von der Seite oder hinten beschossen | ++ | - |
| Granate in der Naehe | +++ | |
| Gegner ausgeschaltet | - | ++ |
| Ueberzahl (eigene Leute in Sicht) | - | + |
| Truppfuehrer in der Naehe | - (daempft) | + |
| in Deckung, Ruhe | baut ab | |

Daraus Zustaende - Schwellen haengen an den Merkmalen (Mut, Disziplin,
Geduld, Jaehzorn), die je Mensch gewuerfelt sind:

* **Panik** (Stress ueber der Schwelle, die der Mut setzt): weg vom
  Gegner zu den eigenen Leuten oder in Deckung, blind feuern (grosse
  Streuung), zu frueh nachladen, Auftraege ignorieren. Funk: "ICH BIN
  RAUS!", "WO SEID IHR?".
* **Zoegern** (Stress springt ploetzlich): eine halbe Sekunde stehen,
  bevor er reagiert - die menschliche Schrecksekunde.
* **Uebermut** (Zuversicht hoch, Disziplin niedrig): verlaesst die
  Deckung, jagt einem Fliehenden hinterher, stuermt allein, laedt offen
  nach. Genau der Fehler, den ein Spieler bestrafen kann.
* **Wut** (Kamerad fiel durch X): X wird Ziel Nummer eins, er nimmt mehr
  Risiko.
* **Ansteckung**: Panik und Uebermut springen im Trupp ueber - wer
  sieht, dass einer wegrennt, bekommt Stress dazu.

Alle Zahlen nach `config.py` (`K.MORAL`), Schwellen und Kurven in
`wesen/*.txt`.

### 8.4 Die Waffe macht die Rolle

| Waffe | Rolle | Verhalten |
| --- | --- | --- |
| MG | Stuetzpunkt | Sucht Deckung mit Schussfeld und bleibt. Ist es **eingeschossen** (laeuft der Feuerstoss schon eine Weile), wird jede Bewegung teuer: lieber weiter niederhalten als die Stellung aufgeben. Bewegt sich nur bei Granate, Flanke oder leerem Gurt. |
| Schrotflinte | Spitzenmann | Will nah heran, geht beim Sturm vorne, wartet aber auf den Partner, statt allein loszurennen. Auf Abstand sucht er Deckung naeher am Gegner. |
| Scharfschuetzenwaffe | Ueberwachung | Bleibt weit weg, wechselt nach zwei, drei Schuessen die Stellung, meidet den Nahkampf, meldet Gegner per Funk. |
| Sturmgewehr | Allrounder | Flankiert - mit Partner -, deckt den Spitzenmann. |
| Repetierer | Schuetze | Wie das Sturmgewehr, laenger zielen, weniger Bewegung. |

In den Daten: Fakten wie `waffe_mg`, `eingeschossen`, `waffe_schrot` und
Kosten/Dringlichkeiten, die damit rechnen (`kosten: 2 + 6 * eingeschossen`
fuer `stellung_wechseln`). Kein Sonderfall im Code.

### 8.5 Lieber zusammen als allein

* **Partner**: Jeder hat einen Partner im Trupp. Flankieren und
  Vorruecken nur zu zweit - einer bewegt sich, der andere deckt.
* **Allein?** Dann zuerst Anschluss suchen ("zum Trupp"), statt eine
  Rolle allein auszufuellen - ausser im Uebermut.
* **Sturm als Trupp**: sammeln (gibt es schon), der Spitzenmann (am
  liebsten die Schrotflinte) zuerst, der Zweite wirft vorher, die
  anderen dicht dahinter, je einer schaut in eine andere Richtung.
* **Feuerschutz** (gibt es schon) wird Teil des Truppplans statt einer
  Einzelentscheidung.

### 8.6 Nicht perfekt - aber aus Gruenden

Fehler kommen aus dem Zustand, nicht aus einem Wuerfel (2.11):

* **Unscharfe Wahl**: unter Stress waehlt er nicht immer das beste Ziel,
  sondern eines der guten (Auswahl mit "Temperatur", die mit dem Stress
  steigt).
* **Tunnelblick**: unter Stress sieht er zur Seite schlechter - darum
  wirkt eine Flanke.
* **Fehleinschaetzung**: unter Stress haelt er den Gegner fuer mehr, als
  er ist (das Wissen aus Schritt 5 wird unsicherer).
* **Traegheit**: was er angefangen hat, macht er laenger, als klug ist -
  der Vorsprung des laufenden Ziels (`K.GOAP["vorsprung"]`) haengt an
  Geduld und Stress.
* **Reaktion** wird mit Stress langsamer, mit Erfahrung im Gefecht (eine
  Runde lang) schneller.

Fairness bleibt: Sehen, Zielen, Drehgrenze wie heute. Die Schwierigkeit
verschiebt nur die Verteilung der Merkmale (2.11).

### 8.7 Sichtbar machen

Funk passend zum Zustand, ein kleines Zeichen ueber dem Kopf (Angst,
Wut), im Testmodus Balken fuer Stress und Zuversicht in der
Gedankenansicht, Werte setzen und Ereignisse ausloesen ("Kamerad
faellt"), und Aufnahmen mit `werkzeug_aufnahme.py` zum Vergleichen.

### 8.8 Reihenfolge

| Teil | Was | Netz |
| --- | --- | --- |
| **8A** | Stress, Zuversicht, Ereignisse; Panik, Zoegern, Uebermut, Wut; Funk und Anzeige | Zeichen ueber dem Kopf: ein Feld in der Weltmeldung |
| **8B** | Waffenrollen: MG eingeschossen bleibt und haelt nieder, Schrot vorne, Scharfschuetze ueberwacht und wechselt | nichts |
| **8C** | Partner und Trupp: Flanke zu zweit, Spruenge, Truppsturm mit Rollen (HTN) | nichts |
| **8D** | Unvollkommenheit: unscharfe Wahl, Tunnelblick, Fehleinschaetzung, Traegheit | nichts |

Jeder Teil wird gemessen: Aufnahmen GOAP gegen klassisch, und die
Fairness-Tests (Treffen quer laufender Ziele, Reaktion) muessen bleiben.

---

## 9. Lernmaterial (gesammelt 0.34.36)

Zum Weiterlesen, sortiert nach Thema. Kostenlos, wenn nicht anders
gesagt.

**Planung, wie sie in Spielen wirklich laeuft**
* Jeff Orkin, *Three States and a Plan: The A.I. of F.E.A.R.* (GDC 2006) -
  der Ursprung von GOAP in Spielen, mit Trupp-Tricks:
  https://pages.cs.wisc.edu/~dyer/cs540/handouts/gdc2006_orkin_jeff_fear.pdf
* Tim Verweij, *A Hierarchically-Layered Multiplayer Bot System for a
  First-Person Shooter* (Killzone 2, 2007) - genau unser Fall:
  Mehrspieler-Bots mit Trupp- und Einzelebene:
  https://www.guerrilla-games.com/media/News/Files/VUA07_Verweij_Hierarchically-Layered-MP-Bot_System.pdf
* Guerrilla, *HTN Planning in Decima* (Horizon, Killzone):
  https://www.guerrilla-games.com/read/htn-planning-in-decima
* *SquadSmart* - HTN fuer ganze Trupps mit Abstimmung:
  https://ojs.aaai.org/index.php/AIIDE/article/view/18775

**Entscheiden mit Nutzenkurven (Utility)**
* Dave Mark, *Infinite Axis Utility System* (Guild Wars 2):
  https://gameai.com/iaus.php
* Dave Mark, GDC: *Embracing the Dark Art of Mathematical Modeling in AI*:
  https://gdcvault.com/play/1015421/Embracing-the-Dark-Art-of
* Buch (kostet): Dave Mark, *Behavioral Mathematics for Game AI*.

**Sammelbaende und Kanaele**
* *Game AI Pro* 1 bis 3 und Online Edition, Kapitel frei als PDF - darin
  u. a. *Squad Coordination in Days Gone* und *Choosing Effective
  Utility-Based Considerations*: https://gameaipro.com/
* Tommy Thompson, *AI and Games* (YouTube) - Fallstudien zur KI echter
  Spiele, verstaendlich erklaert:
  https://80.lv/articles/ai-and-games-a-channel-about-artificial-intelligence-in-games/
* Buch (kostet): Ian Millington, *AI for Games* - das Lehrbuch.

**Gefuehle, Stress, Moral**
* *Modelling Stress Levels in Combat NPCs* (Abertay, 2024) - Stress nach
  menschlichen Stressreaktionen, mit Spielertest:
  https://rke.abertay.ac.uk/en/publications/modelling-stress-levels-in-combat-npcs/
* Square Enix, GDC AI Summit: *Driving Emotionally Expressive NPCs*
  (Gefuehl, Stimmung, Persoenlichkeit, Zuneigung):
  https://gdcvault.com/play/1027102/AI-Summit-Driving-Emotionally-Expressive

**Weltbau und simulierte Leben (fuer Schritt 7 bis 9)**
* Tanya X. Short und Tarn Adams (Hg.), *Procedural Storytelling in Game
  Design* (kostet) - u. a. *Generating Histories* und das Kapitel zu Dwarf
  Fortress: https://www.routledge.com/Procedural-Storytelling-in-Game-Design-1st-Edition/Short-Adams/p/book/9781138595309
* Wie Dwarf Fortress gebaut ist (Interview):
  https://stackoverflow.blog/2021/12/31/700000-lines-of-code-20-years-and-one-developer-how-dwarf-fortress-is-built/
* *Shadows of Doubt* Devblogs - eine ganze Stadt mit Tagesablaeufen,
  Detailstufen nach Naehe zum Spieler:
  https://colepowered.com/?p=34142 und
  https://colepowered.itch.io/shadows/devlog/189689/shadows-of-doubt-devblog-23-generating-citizens-part-1

---

## 10. Was wir aus den Quellen nutzen (gelesen 0.34.37)

Auftrag: "diese ganzen verschiedenen Artikel und Papers lesen ... und
zusammenfassen, was wir davon nutzen koennen."

**Ganz gelesen:** Orkin (F.E.A.R.), Verweij (Killzone 2, alle Kapitel),
Karlsson (*Squad Coordination in Days Gone*), Lewis (*Choosing Effective
Utility-Based Considerations*, Guild Wars 2), Dill (*Dual-Utility
Reasoning*), Gorniak/Davis (*SquadSmart*), Dave Marks IAUS-Seite, die
Devblogs von Shadows of Doubt und das Dwarf-Fortress-Interview.
**Nur Zusammenfassung:** das Stress-Paper (Volltext gesperrt), Decima
(Folien zu gross). **Nicht erreichbar:** der Square-Enix-Vortrag (GDC
Vault in Wartung), Shadows-of-Doubt-Devblog 8 (leer). Das Buch
*Procedural Storytelling* kostet und ist nicht gelesen.

Neu im Lernmaterial (Abschnitt 9 nennt sie nur ueber gameaipro.com):
* Karlsson, *Squad Coordination in Days Gone* (Game AI Pro Online 2021):
  http://www.gameaipro.com/GameAIProOnlineEdition2021/GameAIProOnlineEdition2021_Chapter12_Squad_Coordination_in_Days_Gone.pdf
* Lewis, *Choosing Effective Utility-Based Considerations* (Game AI Pro 3):
  http://www.gameaipro.com/GameAIPro3/GameAIPro3_Chapter13_Choosing_Effective_Utility-Based_Considerations.pdf
* Dill, *Dual-Utility Reasoning* (Game AI Pro 2):
  http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter03_Dual-Utility_Reasoning.pdf

### 10.1 Die fuenf Lehren, die ueberall wiederkommen

1. **Gut aussehen schlaegt richtig sein.** Days Gone sagt es woertlich:
   das Ziel ist "good-looking combat", nicht das wirksamste Verhalten -
   die KI laesst sich eine Weile flankieren, damit die Flanke des Spielers
   sich lohnt, und Flankierer lassen hinten eine Luecke zum Rueckzug.
   Killzone 2: die Bots waren der alten KI 159 zu 14 Runden ueberlegen
   und wirkten trotzdem "robotisch". F.E.A.R.: die Spieler halten die KI
   fuer klug, weil sie *sagt*, was sie tut ("Flankiert ihn!").
2. **Ein Trupp-Gehirn ueber dem Einzelnen, und der Einzelne darf Nein
   sagen.** Bei allen dreien gleich: der Trupp vergibt Rollen, der
   Einzelne fuehrt sie aus, ausser etwas Dringenderes ist los (F.E.A.R.:
   Flucht schlaegt Befehl; Days Gone: die Rolle steckt *an einer Stelle*
   in der Rangfolge des Einzelnen, alles darueber gewinnt). Killzone 2
   zeigt den Fehler: Befehle hatten den hoechsten Rang, also liefen die
   Bots an Gegnern vorbei zum Kreis - das war die haeufigste Kritik der
   Tester ("ignorierten Gegner, nutzten keine Deckung").
3. **Eine Zahl fuer den Mut genuegt.** Days Gone steuert Angriff, Halten
   und Rueckzug mit *einer* Groesse, der Zuversicht, aus dem
   Kraefteverhaeltnis (10.2). Ansteckung (Panik reisst den Trupp mit,
   wenige Mutige reissen ihn hoch) kommt von selbst aus der Formel.
4. **Raum ordnen.** Ohne Ordnung stehen beide Seiten durcheinander,
   Deckungen werden staendig ungueltig, und der Spieler erkennt nicht,
   wer gewinnt. Days Gone loest das mit einer **Frontlinie**; Killzone
   hatte keine und bekam "wie Ameisen, alle in einer Reihe".
5. **Ruhe in die Entscheidung.** Jede Quelle hat eigene Bremsen gegen
   Hin-und-her: Schwellen, bevor sich die Frontlinie bewegt; geglaettete
   Werte; ein Bonus fuer die laufende Entscheidung; Laufzeit und
   Abklingzeit je Aktion (Lewis); die laufende Aufgabe anpassen statt neu
   planen (Killzone 2: neue Deckung, gleicher Plan). Unser
   `K.GOAP["vorsprung"]` und `sperre` sind der Anfang davon.

### 10.2 Je Quelle: was wir uebernehmen

**Days Gone (Karlsson) - die wertvollste Quelle fuer 8A und 8C.**
* **Zuversicht** in fuenf Stufen: panisch, besorgt, neutral, zuversichtlich,
  heldenhaft. Berechnet je Mensch x:
  `C(x) = (s_x + Summe c_f*s_f + Summe s_getoetet) / (Summe c_e*s_e + Summe s_verloren)`.
  s ist die Staerke (Waffe, Panzerung, verwundet, niedergehalten), c der
  Zuversichts-Faktor des anderen. Sein eigener Wert zaehlt *ohne* Faktor,
  damit er nur die Lage spiegelt. Ein **Panischer zaehlt fuer den Gegner**,
  das macht Panik ansteckend. Kills und Verluste bleiben am Trupp haengen
  und klingen langsam ab (viel laenger als ein Gefecht). Die Formel ist
  stabil und pendelt sich nach wenigen Durchlaeufen ein; die Stufen haben
  Schwellen, also gibt es kein Flattern.
* **Gegen den Spieler extra:** steht der Spieler still oder liegt in
  Deckung, *steigt* die Zuversicht der KI (sie macht Druck); stuermt er,
  greift er im Nahkampf an oder zielt er auf einen, *sinkt* sie. Wer
  angreift, wird belohnt.
* **Trupps** bilden sich von selbst: zwei Gleiche in Reichweite sind im
  selben Trupp, Trupps verschmelzen und zerfallen nach Abstand.
* **Frontlinie**: Richtung von der eigenen Mitte zur Gegnermitte; davor
  ein **Niemandsland**, das keiner betritt; Breite nach der Breite des
  Gegners, aber mindestens so, dass alle nebeneinander passen; jeder
  bekommt eine **Bahn** (Lane) und sucht sich darin seinen Platz. Die
  Linie bewegt sich erst ueber einer Schwelle und gleitet nach (schneller,
  je groesser die Aenderung). Wer in Deckung ist, zaehlt mit dem Platz der
  Deckung, nicht mit dem Schritt zur Seite beim Schiessen.
* **Vier Truppzustaende**, gewaehlt nach Zuversicht: *Formieren* (wer
  steht, schiesst, die anderen ruecken auf), *Feuerkampf* (neutral,
  Abstand halten), *Rueckzug in Wellen* (besorgt oder schlechter: die
  Haelfte, die vorn steht oder keine Deckung hat, geht kurz zurueck, die
  andere deckt, dann umgekehrt), *Druck* (zuversichtlich: die Hinteren
  ruecken auf, dann flankieren die Aeusseren zur naeheren Seite - hinten
  bleibt eine Luecke).
* **Feinheiten**: Flankierer zaehlen nicht zur Frontlinie und lassen
  einen **Geist** an ihrem alten Platz, damit die Linie nicht kippt;
  gegnerische Flankierer werden eine Zeit lang ignoriert, dann
  beachtet. Scharfschuetzen und **Stuermer** (Nahkampf, Schrot) gehoeren
  nicht in die Frontlinie - genau unsere Rollen aus 8.4. Rennt der
  Spieler, schiesst die KI und wartet mit dem Stellungswechsel, bis er
  stehen bleibt.
* **Karten-Markierungen** fuer die Kampagne (Schritt 7): Verteidigungszone
  mit weicher Grenze (draussen sinkt die Zuversicht langsam, darum
  kehren sie von selbst zurueck), Heimatbereich (Rueckzug immer dorthin,
  im Heimatbereich kein Rueckzug mehr), Befestigung (steht das Ziel in der
  Todeszone, geh in die Stellung; immer mit Richtung).

**Killzone 2 (Verweij)** - Aufbau und was schiefging.
* Drei Ebenen: **Fraktionsfuehrer** (alle 6,7 s, versetzt zwischen den
  Seiten, damit die Strategie nicht flattert), **Truppfuehrer**,
  **Einzelner**. Trupps bis 4.
* Truppablauf **sammeln -> angreifen -> halten**; Sammeln, sobald mehr als
  die Haelfte da ist, an einem Punkt mit Deckung, Zeitgrenze = Ankunft
  des Fernsten, wer allein ist, sammelt nicht; mehr als die Haelfte tot =
  verloren, Ueberlebende kaempfen weiter, Wiedereinsteiger sammeln neu.
* Abstimmung ohne Planer: **Feuer buendeln**, indem die Zielwahl den
  Abstand der Kameraden zum Ziel mitrechnet; **Ausguckpunkte aufteilen**.
* Einzelne: nie entspannt, laufen ohne Gegner mit voller Geschwindigkeit,
  zielen wie ein durchschnittlicher Spieler ("schlechter sieht dumm aus,
  besser fuehlt sich unfair an"), verteilen sich im Kreis.
* Fraktionsfuehrer fuer Zonen-Spielarten: so viele Zonen angreifen, wie
  zum Gewinnen noch fehlen (`ceil(N/2 + Rueckstand / (2 * Punkte je
  Zone))`), lieber neutrale und nahe Ziele, Ziele behalten, gleichmaessig
  teilen (4-3-1), Spaeher zu Zonen, die keiner angreift.
* **Was die Tester sagten** (unsere Warnliste): Befehl vor Gefahr wirkt
  dumm; alle laufen denselben Weg hintereinander ("Ameisen"); beim
  Sammeln stehen alle still (eine Granate und der Trupp ist weg); keine
  Ahnung von Engstellen - Menschen verteidigen die Zugaenge, nicht die
  Mitte; gut fanden alle, dass die Bots *zusammen* kamen, und sie spielten
  dadurch selbst mehr zusammen. Zielgenauigkeit fanden die einen
  menschlich, die anderen unfair - also eine Einstellung, keine Konstante.
* **Fairness durch den Aufbau**: der Planer sieht nur, was ein Daemon ihm
  als Fakt hinlegt - das zwingt zu fragen, ob ein Mensch das wissen
  koennte. Bei uns: Fakten nur aus Sicht, Gehoer und Funk (Abschnitt 7).

**F.E.A.R. (Orkin)** - kleine Bausteine, Verhalten entsteht.
* Ziele in Schichten ("seven-layer dip"): angreifen, ausweichen,
  Deckung, blind aus der Deckung feuern, wenn man in der Deckung
  getroffen wird, Hinterhalt, wenn die Deckung aufgeflogen ist. Regel:
  **die Deckung nur verlassen, wenn sie bedroht ist und es eine andere
  gibt.**
* Fehlschlaege kommen ins Gedaechtnis und verteuern den Plan beim
  naechsten Mal; Zielwahl (wen, mit welcher Waffe) geschieht *vor* dem
  Planer.
* Truppverhalten: Deckung nehmen (einer haelt nieder, die anderen gehen
  in *verschiedene* Deckungen), Vorruecken von Deckung zu Deckung, Reihe
  (jeder deckt den Vorderen, der Letzte nach hinten), Suche in Paaren.
  Ablauf: Plaetze besetzen -> Befehle senden -> der Einzelne wiegt den
  Befehl gegen eigene Ziele -> Erfolg pruefen.
* **Flanke und Zange entstehen**, wenn Deckungen rund um ein Hindernis
  vergeben werden - man muss sie nicht ausprogrammieren.
* **Funk nach der Entscheidung**: der Satz beschreibt, was gerade
  beschlossen wurde; Wechselreden zu zweit ("Status?" - "Alles ruhig");
  Untaetigkeit erklaeren ("Ich komm hier nicht weg!"); auch Gespieltes
  ("Brauche Verstaerkung!", wenn nur einer uebrig ist).

**Lewis (Guild Wars 2)** - wie man Nutzenkurven waehlt.
* Jede Ueberlegung: Eingang auf 0 bis 1 begrenzen ("Buchstuetzen"),
  durch eine Kurve, alle multiplizieren; eine 0 streicht die ganze
  Entscheidung (billige Ueberlegungen zuerst pruefen).
* **Wenige fertige Kurven** statt freier Formeln - das kann jeder lesen.
  Dazu zwei Standards gegen Wiederholung: **Laufzeit** (`1 - x^6`: nach
  einer Weile faellt die Aktion weg) und **Abklingzeit** (`x^5`: erst kurz
  vor Ablauf wieder voll).
* Bei gleichen Werten flattert die Wahl: Bonus fuer die laufende
  Entscheidung, Gewichte, Laufzeit/Abklingzeit - am besten aber **eine
  weitere Ueberlegung**, die die beiden trennt.
* Fragen wie ein Schauspieler: "warum wuerde ich das tun?" und dafuer
  einen einfachen **Stellvertreter** suchen (eine feste Zeit statt einer
  Rechnung) - Spieler erfinden die Begruendung selbst dazu.
* Beispiele, die genau zu uns passen: *Sturmangriff* nur auf mittlere
  Entfernung, nur wenn er gesund ist, nur nach vorn, und **nicht, wenn
  schon genug Kameraden am Ziel sind** - der Spieler soll nicht von drei
  Seiten ueberrannt werden.

**Dill (Dual Utility)** - Zufall ohne Dummheit.
* Jede Option hat **Rang** und **Gewicht**. Gewicht 0 = gestrichen; nur
  der hoechste Rang zaehlt; was weit unter dem besten Gewicht liegt, faellt
  weg; aus dem Rest wird **nach Gewicht gewuerfelt**. Zoo Tycoon 2:
  Beduerfnisse Rang 0, auf dem Baum Rang 5, Vorfuehrung Rang 100,
  Sterben Rang 1.000.000.

**SquadSmart (Gorniak/Davis)** - Abstimmung im Trupp.
* **Reservieren**: wer eine Deckung, ein Ziel oder einen Kameraden fuer
  eine Aufgabe nimmt, sperrt sie, damit kein zweiter Plan sie doppelt
  vergibt. **Warten auf**: "geh erst, wenn der andere fertig ist"
  (Sturm erst nach dem Wurf). Wirkungen werden *gesehen*, nicht
  angenommen - klappt etwas nicht, plant der Trupp es einfach wieder.
* Erst gute Abfolge, dann Zweige: der erste passende Zweig gewinnt
  (zu zweit festnehmen, sonst allein).

**Dave Mark (IAUS)** - bestaetigt 8.2: Entscheidung = Verhalten in
einem Zusammenhang (wen, wo), Ueberlegungen als Kurven, Produkt,
Verhaltenspakete je Spezies. Passt zu `wesen/*.txt`.

**Stress-Paper (Abertay)** - nur die Zusammenfassung: Wut, Angst, Schock
als Stressreaktionen, im Spielertest mochten die Spieler es (80 % spielten
laenger als geplant). Bestaetigt 8.3, keine neuen Zahlen.

**Weltsimulation (fuer Schritt 7 bis 9):** Shadows of Doubt hat feste
Tagesplaene verworfen (zu zerbrechlich) und auf Beduerfnisse umgestellt
(essen, trinken, schlafen) - genau unser Schritt 8 mit GOAP. Genau
gerechnet wird nur in der Naehe des Spielers, der Rest grob. Dwarf
Fortress: Eigenschaften zusammenstecken statt Klassen vererben (das tun
wir mit Spezies und Daten schon), Erreichbarkeit als vorberechnete
Bereiche statt Wegsuche fuer jede Frage.

### 10.3 Was sich am Plan aendert (Abschnitt 8)

* **8A Innenleben:** *Zuversicht* nach der Days-Gone-Formel statt nur
  aus der Ereignistabelle in 8.3, mit den fuenf Stufen und der
  Spieler-Sonderregel. *Stress* bleibt fuer das Kurzfristige
  (Unterdrueckung, Granate, getroffen) und treibt Zoegern und Panik;
  Zuversicht treibt Angriff, Halten, Rueckzug und Uebermut. Kills und
  Verluste haengen am Trupp und klingen langsam ab (im Mehrspieler: bis
  Rundenende). Alle Zahlen nach `K.MORAL`.
* **8B Waffenrollen:** als Ueberlegungen mit Kurven, nicht als
  Sonderfall. MG *eingeschossen* = Laufzeit-Kurve andersherum (je laenger
  er feuert, desto teurer der Stellungswechsel). Schrot = Stuermer, steht
  nicht in der Frontlinie; Sturm nur, wenn nicht schon genug Kameraden am
  Ziel sind (Lewis). Scharfschuetze ausserhalb der Frontlinie, wechselt
  nach Schuessen (Abklingzeit).
* **8C Trupp:** Trupps nach Abstand (Days Gone), hoechstens 4 (Killzone).
  **Frontlinie mit Bahnen** gegen die Ameisenreihe. Truppzustaende
  *formieren, Feuerkampf, Rueckzug in Wellen, Druck mit Flanke* nach der
  Zuversicht. Sammeln *in Bewegung*, nicht stehend. Befehl als Rolle mit
  festem Platz in der Rangfolge - Ueberleben und Gegner direkt vor ihm
  bleiben darueber. Reservieren von Deckung und Ziel, "warten auf" fuer
  den Sturm. Feuer buendeln ueber die Zielwahl. Fuer die Kreis-Spielart
  spaeter ein Fraktionsfuehrer (wie viele, wer, wohin).
* **8D Unvollkommenheit:** die "Temperatur" aus 8.6 wird **Dual
  Utility**: Rang trennt Wichtiges (Granate ausweichen) von Normalem,
  innerhalb des Rangs wird nach Gewicht gewuerfelt, und die Schwelle fuer
  "zu schlecht, um gewuerfelt zu werden" sinkt mit dem Stress - so macht
  er unter Druck Fehler, aber nie voellig dumme. Zielgenauigkeit als
  Einstellung je Schwierigkeit (Killzone).
* **Funk (8.7):** jeder Spruch folgt einer Entscheidung, dazu
  Wechselreden und Saetze, die Untaetigkeit erklaeren (F.E.A.R.).
* **Karten (spaeter):** Engstellen und Zugaenge je Karte in
  `karten/*.txt` markieren; Verteidiger halten die Zugaenge (Killzone),
  fuer die Kampagne Verteidigungszone, Heimatbereich, Befestigung (Days
  Gone). Das betrifft die Karten und damit das Netz.

### 10.4 Was wir bewusst *nicht* uebernehmen

* **Keinen vollen HTN-Planer fuer den Trupp.** Verweijs eigenes Fazit:
  das Truppverhalten haette es auch ohne Planer gegeben - es sind
  Zustaende mit Wechselbedingungen, die Befehle schicken. Also zuerst
  Truppzustaende in `wesen/*.txt` (Bedingung -> Zustand -> Rollen); ein
  echter HTN erst, wenn Truppplaene mit mehreren Schritten noetig sind.
* Kein Zeitscheiben-Planen und kein Uebersetzen der Daten in Code
  (SquadSmart): unsere Plaene sind kurz, das Gehirn misst seine Zeit schon
  (3.4).
* Keine feste Faktenliste wie bei F.E.A.R. - unsere Fakten sind Namen
  in den Daten, das bleibt.

### 10.5 Wie wir messen

* **Bot gegen Bot**, viele Runden ohne Bild, Ergebnis als
  `(A - B) / (A + B)` (Killzone 2: symmetrisch und zeigt, wie knapp es
  war). Seiten tauschen, weil keine Karte ganz gleich ist.
* **Spieler fragen, ohne zu lenken:** nicht "war es lustig?", sondern
  "wirkte es organisiert? klug? menschlich? wie schwer?" (Killzone 2).
* **Aufnahmen** mit `werkzeug_aufnahme.py`: neue Szenen fuer Rueckzug in
  Wellen, Flanke mit Luecke, MG haelt.

### 10.6 Empfohlene Reihenfolge

1. **8A** Zuversicht und Stress - alles andere haengt daran.
2. **8C** Frontlinie, Bahnen und die vier Truppzustaende - das bemerken
   Spieler am meisten (Killzone: fast alle sahen das Zusammenspiel).
3. **8B** Waffenrollen - danach fast nur Daten.
4. **8D** Dual Utility und Zielgenauigkeit je Schwierigkeit.

---

## 11. Gebaut: Menschen im Gefecht (ab 0.34.38)

Auftrag (gekuerzt): "Das MG feuert nie laenger als ein paar Schuesse ...
sie sollen mehr Commitment zu ihren Aufgaben zeigen ... ein Mensch
entscheidet nicht die ganze Zeit und fuehrt es sofort aus ... bei 20
Gegnern eher Granaten oder Dauerfeuer ... besser hoeren ... vor Granaten
weglaufen, und da kann die Panik ueberhand nehmen ... keine Dashes ...
nicht in eine Gruppe Gegner laufen, um in Deckung zu gehen ... alles
weiter auf dem GOAP-Framework." Dazu Trupps mit Anfuehrer und Funk,
Bergen und Wiederbeleben, Rundumverteidigung und Engstellen - in vier
Paketen (0.34.38 bis 0.34.41), jedes mit Version und Test.

### 11.1 Paket 1 (0.34.38): Innenleben, Bindung, Feuer, Hoeren

* **Rang und Bindung** (goap.Ziel, Felder `rang:` und `bindung:` in
  `wesen/*.txt`): Rang 3 Granate, 2 Panik, 1 was keinen Aufschub duldet
  (leeres Magazin, Stress ueber 0,85), 0 alles andere. Ein hoeherer Rang
  unterbricht sofort; ein gleicher erst, wenn das laufende Ziel `bindung`
  Sekunden lang verfolgt wurde - die Bindung waechst mit der Disziplin.
* **Dual Utility** (goap.Gehirn._unscharf, Dill): bei einer neuen Wahl
  und unter Stress wuerfelt er unter den Zielen des hoechsten Rangs, die
  nah am besten liegen (`K.GOAP["unschaerfe_weite"]`).
* **Innenleben** (innenleben.py, Zahlen in `K.MORAL`): Stress aus
  Ereignissen (Kugel vorbei, Treffer, von der Seite, Kamerad faellt,
  Granate, Geraeusch; ein Abschuss beruhigt), gedaempft von Disziplin und
  Drill, Abbau in Deckung schneller. Zuversicht nach Days Gone aus den
  Staerken (`bot_goap.staerke`): eigene Seite in der Naehe (mal deren
  Zuversicht) plus Abschuesse gegen gesehene und gehoerte Gegner plus
  Verluste, fuenf Stufen. Panik ab Stress 0,8 plus Mut (weniger, wenn die
  Seite verliert), Dauer kuerzer mit Drill. Schreck bei einem Sprung:
  einen Augenblick nichts tun.
* **Neues Merkmal `drill`** (0,1 bis 0,45 fuer `mp_bot`): spaetere
  Soldaten bekommen mehr - sie bleiben bei ihrem Ziel und fangen sich
  schneller. Kein Sonderfall im Code, nur ein anderer Bereich in den
  Daten.
* **Bedenkzeit**: wechselt das Ziel (ohne hoeheren Rang), macht er
  0,1 bis 0,4 s (mit Stress laenger, mit Drill kuerzer) weiter, was er tat.
* **Deckung entscheidet der Stress, nicht jede Kugel**: `_kaempfen` hat
  `mit_deckung`; das GOAP-Hirn schaltet den alten Reflex ab. Ziel
  ueberleben will `in_deckung, beruhigt` (Aktionen deckung, abwarten).
  Wer das MG am Laufen hat (`eingeschossen`) oder den Gegner gleich
  erledigt (`ziel_fast_tot`), bleibt draussen.
* **Feuer je Waffe** (`K.BOTS["feuer"]`): das MG 1,8 bis 3,4 s Stoss
  (vorher hoechstens 0,6 s - es kam nie ueber seinen Anlauf von 1,15 s),
  im Stoss fuehrt er die Garbe nach statt loszulassen, und er nimmt das
  MG auch auf mittlere Weite (`waffe_vorzug`). Gilt auch fuer die
  klassische KI.
* **Gruppen**: stehen mehrere beisammen (`gruppe_um`), schiesst er
  ungefaehr in die Richtung und schwenkt ueber sie (Flaechenfeuer), mit
  laengeren Stoessen; die Granate geht in die Mitte, und fuer einen
  einzelnen hebt er sie eher auf. GOAP-Ziel gruppe_bekaempfen mit den
  Aktionen granate_werfen und dauerfeuer.
* **Hoeren** (`lagebild`): Schuesse (460 px), Explosionen (820 px) und
  Schritte (rennend 150 px, gehend 70 px, durch eine Wand 60 Prozent
  davon), alles ungefaehr. Er schaut zum Unerklaerten (Umschauen), sucht
  dort, und die gehoerten Gegner zaehlen fuer Zuversicht und Deckung.
* **Umschauen**: alle 2,5 bis 5,5 s (unter Stress seltener -
  Tunnelblick) schaut er kurz weg vom Ziel; danach muss er sich neu
  einzielen.
* **Deckung mit Ueberblick** (`_deckung_wert`): keine Stelle naeher als
  110 px an einem anderen bekannten Gegner, Aufschlag fuer einen Weg an
  einem vorbei und fuer jeden, gegen den sie nicht deckt. In Panik nur der
  eine.
* **Getroffen von einem anderen**: er wechselt zu dem, der schiesst
  (auch klassisch), nicht mitten im Stoss.
* **Granaten**: Ziel granate_ausweichen (Rang 3), Aktion ausweichen -
  weg, geradewegs. Stress dazu, Panik kann folgen.
* **Panik**: Ziel panik (Rang 2), Aktion fliehen - weg von den Gegnern,
  zu Kameraden, die weiter weg stehen; wer ihm zu nahe kommt, bekommt
  einen Stoss blind hinterher.
* **Uebermut**: Ziel nachsetzen (zuversichtlich, wenig Disziplin) -
  dorthin, wo der Gegner verschwand, ohne Deckung. Nachladen im Offenen
  wird mit Zuversicht billiger.
* **Kein Dash** mehr, auch klassisch.
* **Testmodus**: INFO KURZ zeigt unter jedem GOAP-Bot den Stress als
  Balken, die Zuversicht als Buchstaben (P B N Z H), PANIK oder SCHRECK,
  und Kreise mit Linien zu dem, was er hoert. GEDANKEN zeigt Stress,
  Zuversicht, Panik, Schreck, eingeschossen, Bindung und Bedenkzeit.
  Testmenue INNENLEBEN: PANIK, STRESS +0,3, KAMERAD FAELLT, GRANATE NEBEN
  IHM, RUHE fuer die gezeigte Figur.

### 11.2 Paket 2 (0.34.39): Trupps, Anfuehrer, Sprechen, Funk

* **Ein Trupp entscheidet nichts fuer seine Leute** (trupp.py). Er ist,
  was alle gemeinsam wissen: die Lage (nur was einer in Sprechweite
  gesagt hat - `K.TRUPP["sprech_weite"]` 260 px), die Zuversicht (Schnitt,
  zur Mitte gerundet, Days Gone), daraus der Zustand (suchen, feuerkampf,
  rueckzug, druck, halten), die Frontlinie mit Niemandsland und Bahnen,
  die Wellen und die Flanker. Bei seinen Leuten kommt das als Fakten an
  (`im_trupp`, `ist_fuehrer`, `trupp_rueckzug`, `welle_dran` ...); was sie
  damit tun, sind Ziele in `wesen/bots.txt` - und Panik und Granaten gehen
  weiter vor.
* **Neue Ziele**: verstaerkung_rufen (Rang 1, nur wer fuehrt und Funk
  hat und unterlegen ist), funk_antworten, lage_melden, rauch_legen
  (Anfuehrer deckt den Rueckzug), rueckzug und druck (Aktion welle: wer
  dran ist, zieht an seine neue Stellung, die anderen decken), zu_hilfe
  (Aktion verlegen - erst wenn die eigenen Gegner erledigt sind),
  trupp_halten (an seiner Stellung, dringend, wenn er allein ist).
* **Der Anfuehrer ist ein Mensch wie die anderen** - mit anderen Zahlen:
  er steht in der Mitte und tiefer (`fuehrer_tiefe`), will mehr
  ueberleben, flankiert kaum, setzt nicht nach, und die anderen nehmen
  zuerst, wer ihm zu nahe kommt (`fuehrer_bonus`), und schiessen lieber
  auf den, auf den schon einer schiesst (`buendeln_bonus`). Ohne
  Funkgeraet ist Funken kein Ziel, das er erreichen kann; allein uebrig
  ist er ein Bot wie jeder andere. Faellt er, fuehrt der mit der meisten
  Disziplin - ohne Funk.
* **Sprechen**: wer einen neuen Gegner sieht und jemanden in Sprechweite
  hat, sagt es ("ZWEI IM NORDEN!"); beim Suchen sagen sie, was sie sehen
  ("LINKS FREI.", "DA WAR WAS, OSTEN!").
* **Funk** (nur der Anfuehrer, nur im Testmodus): ein Spruch dauert
  2,2 s (die Zusage halb so lang), er steht dabei. Danach haben ihn alle
  Anfuehrer der Seite mit Funk. Ein Hilferuf wird nach der eigenen Lage
  beantwortet (`Trupp.hilfe_pruefen`): wer selbst unterlegen ist oder mehr
  als zwei Gegner hat oder eine wichtige Stellung haelt, sagt nicht zu;
  sonst "VERSTANDEN, KOMMEN!" - erst die eigenen, dann hin. Angekommen
  uebernimmt er, was die anderen wissen. Meldet der andere, dass es ruhig
  ist, bleibt er weg.
* **Suchen in breiter Linie**: ohne Kontakt gehen die anderen nebeneinander
  vor dem Anfuehrer (`linie_abstand` 68 px) und schauen nach aussen, der
  Anfuehrer wartet, wenn einer zurueckfaellt.
* **Testmodus**: Spawner-Gruppe TRUPPS - TRUPP (Groesse, Team, Anfuehrer
  MIT FUNK / OHNE FUNK / KEINER, Waffen GEMISCHT / ZUFALL, Leben), TRUPP:
  HALTEN HIER (wichtig ja/nein), TRUPP: ANGRIFF HIER, TRUPP: FREI. INFO
  zeigt Frontlinie, Stellungen, Name und Zustand des Trupps und unten
  links die letzten Funksprueche; wer funkt, hat einen Kasten mit Balken
  ueber sich (auch in der sauberen Ansicht). GEDANKEN zeigt Rolle,
  Zustand, Zuversicht, Lage und Hilfe. Aufnahmen: Szenen `trupp` und
  `hilferuf`.

### 11.3 Paket 3 (0.34.40): Verwundete, Bergen, Wiederbeleben (Testmodus)

* **Testmenue VERWUNDETE BOTS** (vorgegeben AN): ein Bot faellt erst zu
  Boden - die erste Leiche, mit Lache, noch zu retten (er verblutet nach
  `K.VERWUNDET["boden_zeit"]`). Spielerfiguren und Zombies nicht. Nur
  einmal: wer wiederbelebt wurde und noch einmal faellt, ist tot und
  liegt als zweite Leiche da (anders gezeichnet - ausgestreckt, blass,
  groessere Lache; `testmodus.Leiche`), die nach sechs Sekunden weg ist.
  ENTF TOETET legt einen Bot erst hin, ein zweites ENTF toetet ihn.
* **Der Trupp plant die Bergung** (`Trupp._bergung_planen`): er bestimmt
  ein, zwei Retter (die naechsten, nicht den Anfuehrer, keinen
  Geschwaechten) und rechnet, wie viele bekannte Gegner den Liegenden
  sehen - durch Rauch nicht (`trupp.sieht_durch_rauch`). Sicher genug ist
  es, wenn ihn keiner sieht, oder der Trupp zuversichtlich genug ist, es
  gegen die durchzuziehen, die ihn sehen. Ohne Trupp: die zwei naechsten,
  nur wenn ihn keiner sieht (oder einer sehr zuversichtlich ist).
* **Ziel kamerad_bergen** (Rang 1, sobald es sicher ist - der Rauch haelt
  nicht ewig): zum_kameraden, kamerad_ziehen (an die naechste Stelle, die
  vor jedem bekannten Gegner gedeckt ist; beide Haende am Kameraden, kein
  Schuss), aufhelfen - oder aufhelfen_offen, wo keine Deckung zu finden
  ist. Die anderen decken: wer zieht oder aufhilft, braucht Schutz
  (`braucht_schutz`), also nehmen sie zuerst, wer ihm nahe ist, und
  halten nieder. Der Anfuehrer legt Rauch zwischen den Liegenden und die
  Gegner (rauch_legen, auch beim Rueckzug).
* **Geschwaecht nach dem Wiederbeleben**: 60 Prozent Leben, 75 Prozent
  Tempo, 1,4 x Zielfehler, 80 px mehr Abstand (Aufgaben auf Distanz),
  im Trupp weiter hinten, flankiert und stuermt kaum, setzt nicht nach,
  will mehr ueberleben, wird nicht Retter. Ein neues Leben macht ihn
  wieder ganz.
* **Testmodus**: INFO zeigt um den Liegenden einen Kreis (tuerkis:
  sicher, rot: zu gefaehrlich) mit der Zahl der Gegner, die ihn sehen,
  und Linien von den Rettern; GEDANKEN zeigt GESCHWAECHT. Aufnahme:
  Szene `bergen`.

### 11.4 Paket 4 (0.34.41): Igel und Engstellen

* **Igel** (Rundumverteidigung): kommen die Gegner aus Richtungen, zwischen
  denen keine Luecke groesser als 160 Grad ist (`Trupp.luecke`, wer schon
  eingeigelt ist, bleibt es bis 220 Grad), sucht der Trupp in 170 px einen
  Platz, um den herum moeglichst viel Deckung steht
  (`trupp.deckung_ringsum`, acht Richtungen) und der nicht dicht an einem
  Gegner liegt. Dort ein Ring, gleichmaessig nach den Winkeln verteilt,
  die die Leute schon haben (keiner laeuft quer hindurch); steht eine
  Stelle in der Deckung, rueckt er in seiner Richtung naeher zur Mitte. Der
  Anfuehrer steht in der Mitte, jeder schaut nach aussen in seinen Sektor.
* **Engstelle**: gegen eine Horde Nahkaempfer (mindestens vier, oder
  doppelt so viele wie der Trupp) sucht er zwischen sich und der Horde
  einen Durchgang, der schmaler als 84 px und laengs offen ist
  (`trupp.breite_an`), und haelt 120 px dahinter im Bogen, alle mit Blick
  in den Durchgang. Ohne Engstelle kaempft er wie sonst.
* **GOAP**: Fakten `trupp_igel`, `trupp_engstelle`; Ziel sektor_halten
  (Aktion sektor_halten: an den Platz, dann in den Sektor schauen, einem
  Geraeusch darin nachsehen). Flankieren wird dort teuer, Nachsetzen faellt
  weg - niemand verlaesst den Ring. Wer auftaucht, ist fuer angreifen,
  und gekaempft wird von der Stellung aus.
* **Testmodus**: TRUPP: IGEL HIER (einigeln am Zeiger, auch ohne Gegner);
  INFO zeigt den Igelplatz, die Engstelle mit ihrer Breite und kurze
  Striche fuer jede Blickrichtung. Aufnahmen: `igel`, `engstelle`.

### 11.5 Paket 5 (0.34.43): Ruhiger, Deckung zuerst, Verkriechen

Gemeldet nach den Aufnahmen: "zu schnell, nicht wirklich erkennbar ...
ein bisschen wie RimWorld", "Bots blieben teils immer noch im Freien
stehen und gruppierten sich dort", und Panik in der Deckung soll nicht am
Gegner vorbeifuehren.

* **Tempo**: `K.BEWEGUNG` - lauf 0,65 fuer alle Figuren (das Verhaeltnis
  untereinander bleibt), geschoss 0,8 (gleiche Reichweite).
* **Aus der Deckung** (Aktion aus_deckung_feuern, `tun_aus_deckung`): drin
  warten (`lehnen_warten`, laenger unter Stress), zur Seite herauslehnen
  (`lehnpunkt`: dicht neben der Deckung, freie Linie zum Gegner), einen
  Feuerstoss - oder dorthin niederhalten, wo er war -, zurueck. Wer sich
  herauslehnt, gilt noch als in Deckung (`lehnen_weite`).
* **Deckung zuerst**: angreifen kostet `1,5 + 4 (1 - mut)`, weniger mit
  laufendem MG oder fast totem Gegner. Deckung + aus_deckung_feuern kostet
  `2 + mut` - nur die Mutigen greifen offen an. feind_ausschalten bindet
  kuerzer (`0,6 + 0,8 disziplin`).
* **Gesperrt nach Rang** (goap.py): scheitert eine Aktion, bleibt sie nur
  fuer Ziele bis zu dem Rang gesperrt, fuer den sie scheiterte. Fand er
  beim Angriff keine Deckung, sucht er sie trotzdem, wenn er ueberleben
  muss.
* **Trupp-Stellungen** rucken hinter nahe Deckung (`Trupp._deckung_nah`:
  Ringe bis 64 px, ein Hindernis dicht vor ihm, die vorige Stellung bleibt,
  solange sie deckt).
* **Verkriechen** (Panik, schon in Deckung; Aktion verkriechen, kostet 0,5
  gegen fliehen 1): die Stelle in bis zu 70 px mit der meisten Deckung
  ringsum (`deckung_ringsum`, im Haus die Ecke), vor jedem bekannten
  Gegner gedeckt, auf einem gedeckten Weg. Dort bleibt er, bis die Panik
  vorbei ist; kommt einer nah, ein Stoss blind.
* **Untertitel aus** (`K.BOTS["callouts"]`): gesprochen wird weiter (der
  Trupp teilt sein Wissen), es steht nur nicht mehr ueber dem Kopf.
* **Funk im Testmodus** als Wellen vom Funker; wer empfaengt, blinkt.
* **Sturm nur in Ueberzahl** (0.34.44, `stuerme_fuehren`): mindestens
  `sturm_ueberzahl` (1,5) mal so viele wie die Gegner, die der Erste kennt -
  sonst stuermten drei gegen drei aus ihrer Deckung.

### 11.6 Paket 6 (0.34.46): Liegende, Rauch genau, volle Deckung

Gemeldet nach der Aufnahme `deckung`.

* **Liegende sind kein Ziel** (`bots._wahrnehmen`): den laufenden
  Feuerstoss bringt er zu Ende, dann nimmt er den, der noch steht; liegt
  nur noch einer, schiesst er auf keinen. Wer selbst liegt, denkt nicht
  (`liegt()`: kein Ziel, kein Plan, kein Sturm, keine Flanke).
* **Rauch genau** (`rauch_ort`, `tun_rauch`): auf den Liegenden, 18 px zum
  Gegner hin - in den Rauch hinein sieht keiner, und die Retter sind darin
  verborgen; beim Rueckzug auf die Mitte des Trupps. Ist der Ort weiter als
  der Wurf (165 px), geht der Anfuehrer erst naeher heran.
* **Volle Deckung** (`_deckung_guete`): Mauer -70, je offene Flanke bei 25
  Grad +80, Herauslehnen moeglich (Mauerende) -90, Kamerad schon dort +60.
  Gesucht wird einen Ring weiter als bis zur ersten Deckung
  (`deckung_weiter`) - die Mauer dahinter schlaegt das Fass daneben.
* **Nicht in die eigene Deckung** (`vorn_zu`): steht in 56 px vor ihm etwas,
  das Kugeln aufhaelt, kein Schuss und kein Wurf.

### 11.7 Paket 7 (0.34.48): Dicht an der Deckung, Panik waehlt, Funk dauert

* **Dicht in Deckung** (`dicht_gedeckt`): ein Hindernis muss in 40 px vor
  ihm stehen, nicht nur irgendwo zwischen ihm und dem Gegner. Eine Deckung
  naeher am Gegner als 0,6 x Wunschabstand seiner Waffe kostet 1,5 je Pixel;
  gesucht wird bis 200 px.
* **Panik waehlt** (wesen/bots.txt): verkriechen `0,5 + 1,2 (1 - leben) +
  0,6 (1 - zuversicht) + 0,8 trupp_rueckzug`, deckung_wechseln `0,9 + 0,3
  leben + 0,6 trupp_druck` (`bessere_deckung`: 40 px weiter weg von jedem
  Gegner, dicht gedeckt, nicht an ihm vorbei, lieber eine Mauer), fliehen
  `0,8 + 1,5 leben + 0,8 trupp_druck - 0,6 trupp_rueckzug`.
* **Bergen** (`fest_gedeckt`): kamerad_gedeckt heisst dicht gedeckt vor
  jedem bekannten Gegner, ohne Rauch; der Bergeplatz liegt dort, lieber
  hinter einer Mauer, bis 240 px weit.
* **Funk** (`funkplatz`, `_funken_tun`): erst an einen Platz 300 px von
  jedem bekannten Gegner (lieber gedeckt), dann 6 s sprechen; ein Treffer
  oder ein Gegner in 240 px bricht ab (FUNK ABGEBROCHEN).

### 11.8 Was noch offen ist

* Der Funk geht bisher nur zwischen Trupps im Testmodus; im Mehrspieler gibt
  es keine Trupps.
* Gelaendewissen ist gemessen, nicht markiert: Engstellen und Igelplaetze
  findet der Trupp selbst. Fuer die Kampagne (Schritt 7) waeren
  Markierungen in `karten/*.txt` genauer (Days Gone: Verteidigungszone,
  Heimatbereich, Befestigung).
* Die Fraktionsfuehrer-Ebene (Killzone: wie viele Trupps wohin) fehlt noch.
