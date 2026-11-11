# Balancing der Fahrzeuge in SCHLACHT (seit 0.34.129)

Gilt fuer die SCHLACHT: dort kaufen Spieler mit Punkten Nachschub, der am
Fallschirm landet (`K.SCHLACHT["belohnungen"]`). In den anderen Spielarten
stehen nur Buggy, Panzer und Panzerwagen fest auf der Karte - daran aendert
sich nichts. Alle Zahlen stehen in `dustfront/config.py` (`SCHLACHT`), die
Logik in `dustfront/schlacht.py` (Abschnitt "Freischalten und Balancing").

## Grundsaetze

* **Preis folgt Wirkung** - wie viel es zerstoert, wie weit es wirkt, wie
  schwer es zu kontern ist. Insgesamt eher guenstig: kaufen koennen nur
  Menschen, und davon gibt es in einer Runde nicht viele.
* **Der Konter ist billiger als das, was er kontert** (Flak 5 < Tragschrauber 9).
* **Schweres kommt nach und nach** - nicht nach festen Minuten, sondern nach
  dem Spielverlauf (FREISCHALTEN, siehe unten).
* **Hoechstens so viele je Seite** fuer alles, was gehaeuft das Spiel kippt -
  seit 0.34.130 nur mit der Regel HÖCHSTENS JE SEITE (erweiterte Ansicht,
  Vorgabe aus: beliebig viele).
* **Unterstuetzer nur in der eigenen Haelfte**: Funkwagen, Werfer und
  Tragschrauber wirken auf Entfernung und gehoeren nach hinten.
* **Ein zerstoertes Fahrzeug bringt den halben Kaufpreis** (mindestens 2),
  nicht kaufbare (Trosswagen) 3 - vorher pauschal 5, ein Krad brachte damit
  mehr, als es kostete.

## Preise, Stufen, Grenzen

| Was | Preis (vorher) | Stufe | hoechstens je Seite | Abwurf |
| --- | --- | --- | --- | --- |
| Munition | 2 (3) | 0 | - | ueberall ausser nahe der feindlichen Basis |
| Sanitaetsabwurf | 2 (3) | 0 | - | ueberall |
| Krad | 2 (3) | 0 | - | ueberall |
| Buggy | 3 (5) | 0 | - | ueberall |
| Aufklaerungsdrohne | 4 (6) | 0 | - | ueberall |
| Panzerwagen | 6 (8) | 1 | 3 | ueberall |
| Flakwagen | 5 (9) | 1 | 2 | ueberall |
| Funkwagen | 6 (7) | 1 | 1 | **eigene Haelfte** |
| Fallschirmjaeger | 6 (8) | 1 | - | nicht in der eigenen Basis |
| Napalm-Angriff | 7 (10) | 1 | - | Bahn nicht in die feindliche Basis |
| Jagdpanzer | 8 (10) | 2 | 2 | ueberall |
| Spulenwagen | 8 (10) | 2 | 1 | ueberall |
| Panzer | 9 (12) | 2 | 2 | ueberall |
| Tragschrauber | 9 (9) | 2 | 1 | **eigene Haelfte** |
| Werfer | 10 (9) | 3 | 1 | **eigene Haelfte** |

"Hoechstens je Seite" zaehlt, was die Seite gekauft hat und was noch lebt
oder unterwegs ist (angemeldete Zone, am Schirm, gelandet und heil). Die
Fahrzeuge der Basis zaehlen nicht mit.

## FREISCHALTEN (Regel der Runde)

Einstellbar in RUNDE EINSTELLEN (auch in der einfachen Ansicht):
**AUS - ALLES SOFORT**, **SCHNELL**, **NORMAL** (Vorgabe), **LANGSAM**.

**Der Spielverlauf** ist der Anteil der Rundenzeit, der schon um ist. Bei
einer Runde nach Abschuessen der groessere von: Abschuesse der fuehrenden
Seite am Ziel, Laufzeit an 15 Minuten. Eine Stufe gilt, sobald der Verlauf
ihren Anteil erreicht - **oder spaetestens** nach ihrer Hoechstzeit, damit
lange Runden nicht ewig warten.

| Einstellung | Stufe 1 | Stufe 2 | Stufe 3 |
| --- | --- | --- | --- |
| SCHNELL | 5 % / spaetestens 1:00 | 12 % / 2:30 | 22 % / 4:30 |
| NORMAL | 10 % / 2:00 | 22 % / 4:30 | 35 % / 7:30 |
| LANGSAM | 15 % / 3:00 | 32 % / 7:00 | 50 % / 11:00 |

Beispiele mit NORMAL: eine **5-Minuten-Runde** hat Stufe 1 nach 0:30, Stufe 2
nach 1:06, Stufe 3 nach 1:45 - es bleibt reichlich Zeit fuer alles. Eine
**30-Minuten-Runde** hat Stufe 1 nach 2:00, Stufe 2 nach 4:30, Stufe 3 nach
7:30 (die Hoechstzeiten greifen). In der Kaufliste steht bei Gesperrtem,
wann es kommt ("IN 0:20").

## Die Basis im Lauf der Runde

Auch was an der Basis steht, kommt mit den Stufen (mit FREISCHALTEN AUS
steht alles von Anfang an da, wie vorher):

| Stufe | an jeder Basis |
| --- | --- |
| 0 (Start) | 2 Buggys, 1 Krad, 1 Panzerwagen, 1 Trosswagen |
| 1 | + 1 Flakwagen (mit Bot), + 1 Trosswagen |
| 2 | + 1 Panzer |

Neue Fahrzeuge der Basis fallen mit Rueckzaehlung an ihren Zonen, wie zu
Rundenbeginn. Was zerstoert wird, kommt nach seiner Wartezeit (`neu_nach`)
wieder.

## Ideen fuer weitere Karten (noch nicht gebaut)

Die Basis-Ausstattung haengt bisher nur an `K.SCHLACHT["fahrzeuge"]`. Fuer
neue Karten waere der naechste Schritt, dass eine Karte das ueberschreiben
kann - im Kopf der Kartendatei, wie die Kartenzeichen:

* **Ausstattung je Karte**: `# basis: buggy 2 0, krad 1 0, panzer 1 2` (Art,
  Anzahl, Stufe). Eine enge Stadtkarte bekaeme keine Panzer an die Basis und
  mehr Kraeder, eine offene Wueste mehr schwere Wagen.
* **Sperren je Karte**: `# ohne: tragschrauber, werfer` - eine Karte mit
  vielen Plateaus und Mauern ist fuer Werfer und Flieger zu unuebersichtlich.
* **Feste Stellplaetze**: Zeichen auf der Karte fuer die Basis-Zonen, statt
  sie im Umkreis der Basis zu suchen.
* **Eroberbare Punkte**: ein Punkt in der Mitte, dessen Besitzer eine Stufe
  frueher bekommt oder einen Rabatt - dann lohnt es, um ihn zu kaempfen.
* **Ungleiche Karten**: wenn eine Seite es schwerer hat (bergauf), bekommt sie
  eine Stufe Vorsprung bei der Basis.
