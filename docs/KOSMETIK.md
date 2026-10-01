# DUSTFRONT - Kosmetik, vorgezeichnet

**Was das hier ist.** Fuenf Bilder und die Begruendung dazu. Kisten, Skins,
Musikkits und eine zweite Siegtafel - wie sie aussehen wuerden, wenn es sie
gaebe.

> **Nicht zu verwechseln** mit der *Spielerkosmetik* seit 0.28: einem
> eigenen Ton und Bild fuer die Blendgranate, die Spieler selbst machen
> (Kontoseite, Reiter KOSMETIK). Die ist eingebaut und steht in
> `docs/MEHRSPIELER.md`, Abschnitt 12c. Hier geht es um etwas anderes:
> Dinge, die das Spiel ausgibt.

**Was das hier nicht ist.** Eine Ankuendigung. **Eingebaut ist davon
nichts.** Kein Spielcode ruft `dustfront/kosmetik.py` auf, keine Runde
haengt daran, kein Konto bekommt dadurch ein Inventar, und niemand kann
etwas ziehen, besitzen oder verlieren. Wer das Modul loescht, merkt es im
Spiel an keiner Stelle.

**Stand beim Schreiben:** Version 0.24.0, PRE-ALPHA.

---

## 0. Warum ueberhaupt schon jetzt

Weil man an einem Bild in drei Sekunden sieht, was in drei Absaetzen Text
untergeht. Ueber eine Kistenanimation laesst sich endlos reden; ueber
`kosmetik_vorschau/kiste_1_lauf.png` ist in einem Satz entschieden, ob es so
aussehen soll.

Und weil zwei Sachen, die dafuer noetig sind, ohnehin schon gebaut wurden
und hier gleich mitgeprueft werden:

* **Rollen** (`K.SKIN_ROLLEN`, 38 Stueck). Im Code steht nirgends mehr ein
  Bildname. Es steht eine Rolle da - `lmg_hand`, `blend_symbol`,
  `sturm_knall` -, und welche Datei dahinterliegt, sagt `K.skin()`. Das ist
  die einzige Aenderung, die ein Skinsystem am Spielcode ueberhaupt
  braucht, und sie ist seit 0.22.0 drin, weil die vier neuen Waffen sie
  ohnehin brauchten.
* **Stufen** (`K.SELTENHEIT`, 5 Stueck). Name, Farbe, vorgeschlagener
  Anteil. Die Prozente auf dem Kistenbild sind nicht gemalt, sie kommen aus
  dieser Tabelle - wer sie aendert, aendert das Bild.

Beides kostet das Spiel nichts und steht schon. Alles andere steht nicht.

---

## 1. Die Bilder

    python -m dustfront --kosmetik

schreibt fuenf PNG nach `kosmetik_vorschau/`, doppelt vergroessert. Jedes
traegt unten dieselbe Zeile: `VORSCHAU - NOCH NICHT EINGEBAUT`. Die steht da
nicht aus Bescheidenheit, sondern damit ein Bild, das aus dem Ordner
herausgetragen wird, sich selbst erklaert.

| Datei | Was darauf zu sehen ist |
| --- | --- |
| `kiste_1_lauf.png` | Das laufende Band, mitten im Lauf |
| `kiste_2_langsam.png` | Dasselbe Band kurz vor dem Stillstand |
| `kiste_3_ergebnis.png` | Was stehenbleibt |
| `skinauswahl.png` | Die Maske, in der man waehlt, was man traegt |
| `siegtafel_zwei.png` | Die Tafel nach der Tafel |

### 1.1 Das Band

Der Aufbau ist der aus CS, und das ist keine Bequemlichkeit: ein Band, das
von rechts nach links laeuft, ein fester Zeiger in der Mitte, und eine
Verzoegerung, die gegen Ende sehr lang wird. Der Punkt daran ist, dass man
die Ergebnisse vorbeiziehen sieht, die man **nicht** bekommen hat. Nimmt man
das weg, bleibt eine Ziehung mit einem Knopf davor.

Drei Sachen am Bild sind bewusst so und nicht anders:

* **Der farbige Streifen liegt unten, nicht als Rahmen rundum.** Ein Rahmen
  konkurriert mit dem Bild darin, ein Streifen nicht.
* **Die Raender laufen ins Dunkle, 110 Pixel tief.** Bei 70 steht der
  vorletzte Gegenstand noch fast voll im Licht, und dann sieht das Band
  abgeschnitten aus statt endlos.
* **Die Stufen mit ihren Anteilen stehen darunter.** Wer zieht, soll vorher
  sehen, worauf er zieht. Das ist keine Gestaltungsfrage.

### 1.2 Das Ergebnis

Ein Bild, ein Name, eine Farbe. Der Schein dahinter ist das, was den
Unterschied zwischen "noch eins" und "endlich" macht, und er ist technisch
die einzige Stelle im Modul, die nicht offensichtlich ist:

* Erst klein rechnen (64 mal 40), dann mit `smoothscale` hochziehen. Ein
  Stapel aus Rechtecken oder Kreisen gibt sichtbare Stufen, und Stufen sehen
  nach Kasten aus und nicht nach Licht.
* Die Helligkeit steht im Pixel, nicht im Alpha. `BLEND_RGB_ADD` rechnet die
  Farbkanaele zusammen und sieht das Alpha gar nicht an - wer die Abstufung
  ins Alpha legt, bekommt eine volle Flaeche. (Genau das ist beim ersten
  Versuch passiert: eine massive orange Ellipse ueber dem halben Bild.)

Was **nicht** darauf steht: Fassungszaehler, Wert, Datum. Die Versuchung ist
gross, und genau das nimmt dem Moment alles. Das gehoert auf die naechste
Seite.

### 1.3 Die Auswahl

Links die Figur, gross, rechts das, was sie tragen kann. In der Reihenfolge,
weil man die Vorschau anschaut, waehrend man rechts blaettert - umgekehrt
muesste der Blick staendig springen.

Vier Spalten zu 90 Pixeln. Schmaler wuerde jeden zweiten Namen abschneiden,
und ein Skin ohne lesbaren Namen ist nur ein Bildchen. 90 Pixel tragen 15
Zeichen, `K.LOADOUT["namenslaenge"]` erlaubt 12.

Links unten stehen **Klang** und **Musikkit** als eigene Kaesten, mit einem
Pegel daneben. Das ist kein Zierat: ein Blendgranaten-Skin ist zur Haelfte
ein Geraeusch, und wer das erst im Gefecht merkt, waehlt blind. Dass Bild
und Klang getrennt waehlbar sind, ist im Code schon so - die Blendgranate
allein hat fuenf Rollen: `blend_flug`, `blend_hand`, `blend_symbol`,
`blend_knall`, `blend_pfeifen`.

### 1.4 Die zweite Siegtafel

Die erste Siegtafel sagt, wie die Runde ausging: Zahlen, alle Spieler,
nuechtern. Diese hier sagt, wem sie gehoerte. Darum nur drei je Seite, gross,
mit Abschuessen, Toden und der meistbenutzten Waffe **als Symbol** - genau
wie auf der ersten Tafel, damit beide dieselbe Sprache reden.

Darunter eine Buehne: zwei links, eins in der Mitte und oben, drei rechts.
Die Reihenfolge liest man ohne Beschriftung. Der MVP steht am hoechsten,
sein Musikstueck laeuft, und die drei machen ihre Animation - was genau,
waehlt jeder selbst. Das ist der Punkt an der Sache: es ist die eine Stelle
im Spiel, an der man zeigt, was man hat, und alle schauen hin.

Das Musikkit sitzt oben in der Mitte zwischen den beiden Bloecken und nicht
auf der Buehne. Auf der Buehne stand es den Figuren im Weg, und oben klaffte
sonst ein Loch.

---

## 2. Was bewusst fehlt

| Frage | Warum hier keine Antwort steht |
| --- | --- |
| Woher ein Gegenstand kommt - Kisten? Spielzeit? Beides? | Das ist eine Entscheidung ueber das Spiel, nicht ueber die Anzeige. |
| Wo er liegt | Das Konto koennte es (Profil, Fassungszaehler, `docs/KONTO.md` Abschnitt 3), aber solange es nichts zu speichern gibt, wird nichts gespeichert. |
| Handel, Preise, Schluessel, Geld | Steht nicht zur Debatte. |
| Ob Skins ueberhaupt kommen | Offen. Dieses Dokument macht die Frage beantwortbar, es beantwortet sie nicht. |

---

## 3. Was es kosten wuerde, es wirklich einzubauen

Der ehrliche Ueberschlag, damit die Entscheidung nicht auf einem Gefuehl
beruht. In der Reihenfolge, in der es gebaut werden muesste:

1. **Besitz.** Eine Tabelle `besitz` (Konto, Rolle, Name, wann) in Supabase,
   nach demselben Muster wie die Werte: ein eindeutiger Index, damit dieselbe
   Zuteilung genau einmal zaehlt, und das Journal davor. Die Regeln aus
   `docs/KONTO.md` Abschnitt 4 gelten unveraendert - **es darf nie
   auseinanderlaufen**, und bei Besitz gilt das doppelt.
2. **Uebertragen.** Im Mehrspieler muss jeder wissen, was die anderen
   tragen. Das sind drei bis fuenf Rollen je Spieler, einmal beim Beitritt,
   nicht je Takt. Das Feld dafuer gaebe es (`Kaempfer`), die Bilder muessten
   beim Laden aufgeloest werden, nicht im Zeichnen.
3. **Bilder.** Ein Skin ist eine PNG-Datei mehr in `assets/`. Fehlt sie,
   nimmt `Bilder.bild()` den gezeichneten Platzhalter - es kann also nichts
   kaputtgehen, wenn jemand eine Datei nicht hat. Das ist der Grund, warum
   das Rollensystem ueberhaupt so gebaut ist.
4. **Klaenge.** Dasselbe, ueber `KLANG_NAMEN`. Hier ist zu bedenken, dass
   ein Skinklang laut sein kann - die Lautstaerke muss aus dem Spiel kommen
   und nicht aus der Datei, sonst gewinnt der lauteste Skin.
5. **Die Kiste selbst.** Die Animation aus 1.1 ist das kleinste Stueck an
   der ganzen Sache: eine Szene, ein Band, eine Verzoegerungskurve. Zwei
   Tage. Alles davor sind Wochen.

Punkt 1 und 2 sind die Arbeit. Wer nur Punkt 5 sieht, unterschaetzt es um
das Zehnfache.

---

## 4. Woran man sieht, dass wirklich nichts eingebaut ist

* `dustfront/kosmetik.py` wird von genau einer Stelle importiert: dem Zweig
  `--kosmetik` in `main.py`, innerhalb der Funktion. Kein Modul des Spiels
  importiert es.
* `K.SKIN_WAHL` ist leer. Solange es leer ist, gibt `K.skin()` fuer jede
  Rolle die Vorgabe zurueck, und das Spiel sieht aus wie vorher.
* `tests/test_spiel.py` prueft beides: dass ein Rollenname aufloest, dass
  `skin_setzen()` auf eine unbekannte Rolle `False` gibt, dass
  `skin_zuruecksetzen()` den Ausgangsstand wiederherstellt, und dass die
  Anteile in `K.SELTENHEIT` zusammen 1 ergeben.
