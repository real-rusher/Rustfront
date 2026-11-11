# Plan: Rechenleistung an die Gaeste abgeben (Client-Seite)

Stand 0.34.102. Gewuenscht: "Praesentier mir einen Plan fuer die Abgabe an
Rechenleistung an Gaeste, also der Einbau einer Client-Seite quasi."

## 1. Wo wir stehen

**Ein Rechner rechnet, alle anderen schauen zu** (netz.py). Der Gastgeber
simuliert alles: Bewegung, Schuesse, Treffer, Bots, Fahrzeuge, Feuer. Der
Gast schickt nur Tasten und zeigt, was zurueckkommt, mit einer Ueberblendung
zwischen zwei Meldungen (`Gefecht.misch`).

Seit 0.34.102 ist die **Leitung** sparsam: nur Aenderungen, 30 Meldungen je
Sekunde, Gegendruck mit Quittungen. Gemessen in SCHLACHT mit 24 Kaempfern:
rund 40 KB/s je Gast statt gut 1000. Was bleibt, ist grundsaetzlich:

| Was | Ursache | Wie es sich anfuehlt |
| --- | --- | --- |
| Eingabeverzoegerung | jeder Schritt der eigenen Figur geht hin und zurueck (Hin- und Rueckweg + Takt) | bei 150 ms Ping laeuft die eigene Figur spuerbar nach |
| Treffer nach Gefuehl | getroffen wird, wo der Gegner beim *Gastgeber* steht, nicht wo man ihn sieht | man zielt richtig und trifft trotzdem nicht |
| Last beim Gastgeber | er rechnet alle Bots (GOAP-Planer), alle Fahrzeuge, alles | mit vielen Bots und Gaesten ruckelt der Gastgeber zuerst |
| Bandbreite | jede Figur, jede Kugel, jeder Wagen in jeder Meldung | schon klein, waechst aber mit der Kartengroesse |

## 2. Grundsaetze

* **Der Gastgeber bleibt die Wahrheit.** Was zaehlt - Treffer, Tode,
  Punkte, Statistik (AGENTS.md: "Statistiken duerfen nie auseinanderlaufen")
  -, entscheidet weiter allein der Gastgeber. Der Gast rechnet *vorher*, um
  es schneller zu zeigen, und wird korrigiert, wenn er falsch lag.
* **Derselbe Code auf beiden Seiten.** Keine zweite Physik fuer den Gast:
  er ruft dieselben Funktionen (`Spieler.schritt`, `Welt.frei`, ...) auf.
  Was der Gastgeber anders macht, ist nur, dass er es auch fuer die
  anderen tut.
* **Jede Stufe einzeln abschaltbar** (`K.NETZ`), damit man bei einem Fehler
  im Spiel sofort zurueck kann, und einzeln messbar (siehe 5).
* **Alter Gast, neuer Gastgeber geht nicht** - wie bisher: dieselbe Version.

## 3. Die Stufen, in der empfohlenen Reihenfolge

### Stufe A - Die eigene Figur sofort bewegen (Vorhersage)

Der groesste Gewinn fuer das Gefuehl. Der Gast bewegt seine eigene Figur
selbst, sofort, mit demselben Code wie der Gastgeber, und schickt die
Eingabe wie bisher - jetzt mit einer laufenden Nummer.

* Der Gastgeber schreibt in jeden Spielereintrag, welche Eingabe er
  zuletzt verarbeitet hat (`"en"`).
* Der Gast haelt die Eingaben, die noch nicht bestaetigt sind. Kommt eine
  Meldung, setzt er seine Figur auf den Stand des Gastgebers und spielt die
  unbestaetigten Eingaben darauf noch einmal ab (Abgleich).
* Kleine Abweichungen werden ueber einige Bilder weich ausgeglichen, grosse
  (Stoss, Sturz, Teleport, Tod) sofort uebernommen.
* Was nicht vorhergesagt wird: Treppen, Fahrzeuge, Ziehen, Aufhelfen - dort
  bleibt es wie heute, bis Stufe A sitzt.

Aufwand: mittel (2-3 Arbeitsschritte). Risiko: Ruckeln bei Abweichungen -
darum zuerst messen, wie oft und wie weit korrigiert wird.

### Stufe B - Die anderen ruhig zeigen (Puffer statt Ueberblendung)

Heute mischt der Gast zwischen den beiden letzten Meldungen. Kommen sie
unregelmaessig (langsames Internet), springt es. Besser: die anderen etwas
in der Vergangenheit zeigen (rund zwei Meldungen, ca. 70 ms), aus einem
kleinen Puffer mit Zeitstempeln. Dann gibt es immer zwei Meldungen, zwischen
denen man liegt, und Aussetzer bis 100 ms sieht man nicht.

Aufwand: klein. Kein Protokoll ausser einem Zeitstempel je Meldung.

### Stufe C - Nur schicken, was den Gast angeht (Interessenbereich)

Der Gastgeber schickt jedem Gast nur, was in dessen Umgebung liegt
(Bildausschnitt plus Rand, eigene Mannschaft immer, Markierte immer);
Weiteres seltener (z. B. 5 je Sekunde, fuer Minikarte und Nebel). Spart auf
grossen Karten am meisten - und ist nebenbei ein Schutz gegen Wandhacks: was
man nicht sehen darf, kommt gar nicht erst an.

Aufwand: mittel. Haengt an der Regel, was die Minikarte zeigen darf.

### Stufe D - Schuss sofort zeigen, fair treffen (Treffer-Rueckrechnung)

* Der Gast zeigt Muendungsfeuer, Kugel, Rueckstoss und Ton sofort selbst.
* Der Gastgeber merkt sich die Lage aller Figuren der letzten ~0,5 s. Kommt
  ein Schuss, rechnet er den Treffer gegen die Lage, die der Schuetze
  gesehen hat (Ping + Puffer aus Stufe B), hoechstens 200 ms zurueck.
* Getroffen ist, was der Gastgeber so ausrechnet - die Statistik bleibt
  eine.

Aufwand: mittel bis gross. Am besten erst nach A und B.

### Stufe E - Vorhersagbares selbst rechnen (Ereignisse statt Zustand)

Kugeln, Granaten, Raketen, Feuer, Rauch, Fallschirme verlaufen nach dem
Start nach festen Regeln. Statt jede Kugel in jeder Meldung zu schicken,
schickt der Gastgeber nur den Start (Ort, Richtung, Waffe, Zufallssaat), und
der Gast rechnet den Flug selbst. Das Ende (Treffer, Abprall, Explosion)
meldet weiter der Gastgeber. Spart Bandbreite und gibt dem Gast fluessige
Fluege auch bei Aussetzern.

Aufwand: mittel; Voraussetzung ist, dass die Fluege nur aus Startwerten und
Welt folgen (bei den meisten heute schon so - siehe Feuerball, Rauch).

### Stufe F - Bots auf die Gaeste verteilen (echte Rechenleistung abgeben)

Die schwerste Last beim Gastgeber sind die Bots (Wahrnehmung, GOAP-Planer,
Trupps). Der Gastgeber teilt jedem Gast einige Bots zu. Der Gast rechnet
fuer sie, was sie *wollen*, und schickt es wie die Eingabe eines Spielers;
Bewegung, Treffer und Schaden rechnet weiter der Gastgeber.

* Faellt ein Gast weg oder haengt er (keine Quittungen), nimmt der
  Gastgeber seine Bots sofort zurueck.
* Ein Gast mit eigenem Bot koennte schummeln (der Bot schiesst nie auf ihn)
  - darum nur Bots der eigenen Mannschaft, und abschaltbar.
* Der Gast braucht dafuer, was die Bots wahrnehmen: in ihrer Umgebung den
  vollen Stand (passt zu Stufe C, Interessenbereich je Bot).

Aufwand: gross. Lohnt erst, wenn der Gastgeber messbar an den Bots haengt
(Testmodus: Zeit je Bild mit 40 Bots).

### Ausserdem moeglich (Transport)

* **Packen** (zlib als Strom) auf die Aenderungen: noch einmal etwa 3-5x
  weniger. Braucht einen eigenen Rahmen statt Zeilen (die gepackten Bytes
  enthalten Zeilenumbrueche) - also ein Protokollschritt.
* **UDP** fuer die Weltmeldungen: verlorene Pakete werden nicht nachgeholt,
  das Ueberholte zaehlt nicht. Lohnt erst mit Stufe A-E und bringt eigene
  Probleme (Router, Tunnel ueber Cloudflare geht nur mit TCP).

## 4. Stand

* **0.34.103: Stufe B und A eingebaut** (dustfront/gastseite.py, Tests in
  tests/test_spiel.py Abschnitt 0.34.103 mit kuenstlichem Ping, Schwankung
  und Aussetzer). Der Puffer verzoegert hoechstens 0,15 s - mehr hiesse
  bis zu Stufe D, weiter hinter Gegnern herzuzielen.
* **Gelernt dabei:** Wie lange der Gastgeber eine Eingabe anwendet, haengt
  davon ab, wann die naechste ankommt - bei Schwankung also nicht davon, wie
  lange der Gast sie gemeint hat. Der Abgleich rechnet fehlende Schritte
  nach; beim Dash bleibt trotzdem ein Versatz bis etwa 15 px, der weich
  ausgeglichen wird.
* **0.34.104: Eingabepuffer beim Gastgeber** - jede Eingabe sagt, wie
  viele Schritte die vorige beim Gast galt ("es"), und der Gastgeber wendet
  die *Bewegung* genau so lange an. Seitdem stimmt die Vorhersage auch bei
  Schwankung ohne Korrektur. Nur die Bewegung wartet (0-17 ms), Schiessen
  und alle anderen Tasten wirken sofort. Es bleiben Korrekturen, wo
  Figuren einander wegschieben (Welt.auseinander) - klein und weich.

## 5. Empfohlene Reihenfolge

1. **B** - erledigt (0.34.103).
2. **A** - erledigt (0.34.103), mit Eingabepuffer (0.34.104).
3. **D** - erledigt (0.34.105), Grenze 0,5 s. Seit 0.34.104 vorgezogen: der Gast sieht Gegner einen halben
   Ping plus Puffer zu spaet, getroffen wird aber, wo sie beim Gastgeber
   stehen. Das ist jetzt der groesste spuerbare Nachteil auf schlechtem
   Internet - und erst mit D darf der Puffer groesser werden (dann wird
   das Bild bei starker Schwankung auch ruhiger).
4. ~~**C**~~ - **kommt nicht** (Entscheidung des Besitzers, 0.34.105): alle
   Wesen sollen beim Gast immer wie bisher gezeichnet werden.
5. **E** - erledigt (0.34.106) fuer gerade Fluege (Geschoss, Panzergranate);
   Granaten, Raketen und C4 bleiben, wie sie sind (Bogen, Abprallen, Lenkung).
6. **F** - nur, wenn der Gastgeber an den Bots haengt.

## 6. Wie wir pruefen

* Eine Testreihe `tests/test_netz.py` mit einer kuenstlich langsamen
  Leitung (Bandbreite, Ping, Schwankung, Aussetzer). Fuer 0.34.102 wurde so
  von Hand gemessen (der Gast liest nur so viele Bytes je Sekunde); daraus
  wird ein festes Werkzeug.
* Je Stufe Zahlen, die nicht schlechter werden duerfen: KB/s je Gast,
  Rueckstand des Gasts, Zeit von Taste bis Bild, Zahl und Groesse der
  Korrekturen (Stufe A), Treffer, die der Schuetze sah und der Gastgeber
  nicht gab (Stufe D).
* Wie bisher: alle fuenf Testreihen gruen, je Stufe eigene Version und eine
  Zeile in docs/MEHRSPIELER.md.
