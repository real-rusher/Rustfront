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
   Decima es tun (Abschnitt 9). Der Truppfuehrer verteilt Rollen als
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
* Remco Verweij, *A Hierarchically-Layered Multiplayer Bot System for a
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
