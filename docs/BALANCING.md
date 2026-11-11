# Balancing der Fahrzeuge (VORSCHLAG, noch nicht eingebaut)

Stand 0.34.128. Gilt fuer die SCHLACHT, dort werden Fahrzeuge mit Punkten
gekauft und am Fallschirm abgeworfen (`K.SCHLACHT["belohnungen"]`). In den
anderen Spielarten stehen nur Buggy, Panzer und Panzerwagen fest auf der
Karte; daran aendert der Vorschlag nichts.

## Wie es heute ist

* Punkte bekommen nur Menschen: **1 je Abschuss, 5 je zerstoertem Fahrzeug,
  5 fuers Aufhelfen**.
* Alles ist **ab der ersten Sekunde** kaufbar, **ohne Obergrenze**, ueberall
  ausser nahe der feindlichen Basis.
* In jeder Basis stehen von Anfang an: Panzer, Panzerwagen, 2 Buggys, Krad,
  2 Trosswagen, Flakwagen (mit Bot).

Was dabei schief laeuft:

1. **Ein Krad kostet 3, sein Abschuss bringt 5** - wer gegnerische Kraeder
   jagt, verdient mehr, als sie kosten. Dasselbe beim Buggy (5 / 5).
2. **Der Tragschrauber kostet 9**, ist vom Boden praktisch nicht zu treffen,
   sieht alles und wirft Bomben; sein Konter, der **Flakwagen, kostet auch 9**.
3. **Der Werfer kostet 9** und schiesst ueber die halbe Karte - zwei davon
   mit einem Funkwagen dazu machen die Mitte unbetretbar.
4. Gleich zu Beginn stehen Panzer in beiden Basen und alles Schwere ist
   kaufbar - die ersten Minuten sind keine Infanterieschlacht.

## Grundsaetze

* **Preis folgt Wirkung**: wie viel es zerstoert, wie weit es wirkt, wie
  schwer es zu kontern ist.
* **Der Konter ist billiger als das, was er kontert** (Flak < Tragschrauber,
  Jagdpanzer < Panzer).
* **Freischalten nach Rundenzeit**: erst leicht, dann mittel, dann schwer.
* **Hoechstens so viele je Seite gleichzeitig** fuer alles, was gehaeuft das
  Spiel kippt.
* **Unterstuetzer nur in der eigenen Haelfte** abwerfen (Funkwagen, Werfer,
  Tragschrauber) - sie wirken auf Entfernung und gehoeren nach hinten.
* **Ein Fahrzeug abzuschiessen bringt die Haelfte seines Preises** (mindestens 2)
  statt pauschal 5.

## Vorschlag

| Was | Kosten heute | neu | frei ab Minute | hoechstens je Seite | Abwurf |
| --- | --- | --- | --- | --- | --- |
| Munition | 3 | 3 | 0 | - | ueberall (wie heute) |
| Sanitaetsabwurf | 3 | 3 | 0 | - | ueberall |
| Krad | 3 | 3 | 0 | - | ueberall |
| Buggy | 5 | **4** | 0 | - | ueberall |
| Aufklaerungsdrohne | 6 | **5** | 0 | - | ueberall |
| Panzerwagen | 8 | 8 | **2** | **3** | ueberall |
| Flakwagen | 9 | **6** | **2** | **2** | ueberall |
| Funkwagen | 7 | **8** | **2** | **1** | **eigene Haelfte** |
| Fallschirmjaeger | 8 | 8 | **3** | - | nicht in der eigenen Basis (wie heute) |
| Jagdpanzer | 10 | 10 | **4** | **2** | ueberall |
| Spulenwagen | 10 | 10 | **4** | **1** | ueberall |
| Panzer | 12 | **14** | **5** | **2** | ueberall |
| Tragschrauber | 9 | **12** | **5** | **1** | **eigene Haelfte** |
| Werfer | 9 | **13** | **5** | **1** | **eigene Haelfte** |
| Napalm-Angriff | 10 | **12** | **6** | - | ueberall (Bahn nicht in die Basis, wie heute) |

**Basis**: der Panzer der Basis kommt erst ab **Minute 4** (heute ab Start);
alles andere bleibt. Wartezeiten bis zum Ersatz (`neu_nach`) bleiben.

**Punkte**: Abschuss eines Fahrzeugs = halber Kaufpreis, mindestens 2 (Krad 2,
Buggy 2, Panzerwagen 4, Flakwagen 3, Tragschrauber 6, Werfer 7, Panzer 7). Fuer
Wagen, die man nicht kaufen kann (Trosswagen), 3. Abschuss 1 und Aufhelfen 5
bleiben.

**Spiel nach Abschuessen** statt nach Zeit: dieselben Minuten seit Rundenbeginn.

## Was beim Einbauen dazukommt

* `K.SCHLACHT`: Kosten, `freischalten` (Sekunden je Art), `hoechstens_je_seite`,
  `nur_eigene_haelfte`; `punkte["fahrzeug"]` als Anteil des Preises.
* `schlacht.belohnung_pruefen`: neue Gruende "AB MINUTE 5", "SCHON 1 IM EINSATZ",
  "NUR IN DER EIGENEN HAELFTE"; gezaehlt wird, was eine Seite gekauft hat und
  noch lebt oder unterwegs ist (Dropzone, Abwurf, Fahrzeug).
* Die Kaufliste zeigt Gesperrtes grau mit Grund und Restzeit.
* Pruefungen in `tests/test_spiel.py`, Zeile im Testmodus (ADMIN gratis
  umgeht weiterhin nur die Punkte).
* Version, README; das Netz aendert sich nur, wenn der Gast die Sperren in der
  Liste anzeigen soll (dann: Rundenzeit und Zaehler in der Schlachtmeldung).
