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

## Karten mit Front (seit 0.34.131)

FLUSSTAL und KANALSTADT nennen im Kopf ihre Basen - drei je Seite - und
**jede Basis hat ihre eigene Ausstattung** (`basisN: Seite x y NAME | Art
Anzahl Stufe, ...`). Sie ersetzt dort `K.SCHLACHT["fahrzeuge"]`; die Stufen
gelten wie oben (FREISCHALTEN). Die Kaufpreise bleiben dieselben.

| FLUSSTAL | Stufe 0 | Stufe 1 | Stufe 2 | Stufe 3 |
| --- | --- | --- | --- | --- |
| Nordlager (ROT) / Suedlager (BLAU) | Buggy, Krad | Funkwagen | Tragschrauber | - |
| Hauptlager | Buggy, Panzerwagen, Trosswagen | Flakwagen | Panzer | Werfer |
| Suedlager (ROT) / Nordlager (BLAU) | Buggy, Krad | Trosswagen | Jagdpanzer, Spulenwagen | - |

| KANALSTADT | Stufe 0 | Stufe 1 | Stufe 2 | Stufe 3 |
| --- | --- | --- | --- | --- |
| Nordkaserne (ROT) / Suedkaserne (BLAU) | 2 Kraeder, Buggy | Funkwagen | Tragschrauber | - |
| Hauptdepot | Buggy, Panzerwagen, Trosswagen | Flakwagen | Jagdpanzer | Werfer |
| Suedkaserne (ROT) / Nordkaserne (BLAU) | Krad, Buggy | Trosswagen | Panzer, Spulenwagen | - |

In der Stadt mehr Kraeder und der Jagdpanzer im Hauptdepot (lange Strassen,
weite Schuesse die Allee entlang), der Panzer an der Seite, wo die
Strassen breiter sind. So viele Bots je Seite fahren, wie der Kopf sagt
(`fahrer:` 7 in FLUSSTAL, 6 in KANALSTADT; sonst `K.FRONT["fahrer"]`).

**Eroberungspunkte** bringen keine Zaehler und keinen Rabatt: ganz
eingenommen und ohne Gegner in der Naehe sind sie ein Einstieg. Das ist ihr
ganzer Wert - wer die Front nach vorn schiebt, steigt naeher am Kampf ein.

## Ideen fuer weitere Karten (noch nicht gebaut)

* **Sperren je Karte**: `# ohne: tragschrauber, werfer` - eine Karte mit
  vielen Plateaus und Mauern ist fuer Werfer und Flieger zu unuebersichtlich.
* **Ungleiche Karten**: wenn eine Seite es schwerer hat (bergauf), bekommt sie
  eine Stufe Vorsprung bei der Basis.
