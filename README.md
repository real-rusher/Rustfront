# DUSTFRONT

Ein Top-Down-Actionspiel mit Einzelspieler und Mehrspieler. Erkunde
mehrstufige Karten, kämpfe gegen Gegner oder andere Spieler und passe
Ausrüstung, Steuerung und Darstellung an.

Geschrieben in Python mit pygame-ce. Schulprojekt, in Arbeit.

**Aktuell: Version 0.33.0, PRE-ALPHA.** Was das heisst, steht weiter unten
unter [Versionsnummern](#versionsnummern).

## Mitwirkende

Nicolas, Nikolaus, Marlon, Alfred.

## Stand

| Teil | Zustand |
| --- | --- |
| Splash-Sequenz | fertig, fünf Karten mit eigenem Ton |
| Hauptmenü | fertig, inklusive Optionen und Spielstand |
| Spielkern | feste Zeitschritte, Kollision, Gegner-KI, Bosse und Wellen |
| Waffen | Schuss-, Wurf- und Nahkampfwaffen, darunter MG, Raketenwerfer und C4 |
| Karten | mehrstufige Karten mit Treppen, Luken und Aufzügen |
| Sturz | ohne Ruck: die Figur bleibt stehen, die Welt wächst unter ihr heran |
| Inventar und Hotbar | fertig, Plätze per Maus oder Tastatur umsortierbar |
| Pause und Einstellungen | Anzeige, Ton, Steuerung und Mitwirkende |
| Grafik-Einstellungen | Vignette, Wackeln, Partikel, Zoom und Ebenenansicht |
| Mehrspieler | LAN und Internet, Lobby, Rundenplan, Statistik und Bestenliste |
| Konto | lokale Konten oder Supabase, Profile, Loadouts und Rundenstatistik |
| Anpassung | Steuerung, Anzeige, Audio, eigene Spielerkosmetik und ersetzbare Assets |

Der Spielkern gilt als tragfähig: was jetzt noch dazukommt, hängt sich als
weitere Szene, weiteres Wesen oder weitere Zeile in `config.py` an, statt
Bestehendes umzubauen.

## Wohin es geht

[`docs/KARTE.md`](docs/KARTE.md) beschreibt den langfristigen Weltenplan
und trennt geplante Systeme von dem, was im aktuellen Spiel bereits
eingebaut ist.

## Starten

**Ohne Kommandozeile, einfach doppelklicken:**

| Was | Windows | macOS, Linux |
| --- | --- | --- |
| Das ganze Spiel, mit Menü und Intro | `DUSTFRONT.bat` | `DUSTFRONT.command` |

Die Datei sucht sich Python selbst, installiert pygame-ce beim ersten Mal
nach und startet dann. Geht etwas schief, bleibt das Fenster offen und sagt
warum, statt kommentarlos zu verschwinden.

**`DUSTFRONT`** ist der einzige Spielstarter: Intro, Hauptmenü und von dort
direkt in Einzelspieler oder Mehrspieler. Beim Mehrspieler kann man eine
Lobby erstellen oder einer vorhandenen beitreten. Optionen, Steuerung und
Mitwirkende liegen ebenfalls im Hauptmenü. Mit *AUFGEBEN* im Pausemenü
kommt man zurück ins Hauptmenü.

Unter macOS beim allerersten Mal Rechtsklick auf die Datei und dann
*Öffnen* wählen - danach reicht der Doppelklick.

**Verknüpfung auf den Desktop** (Windows): Rechtsklick auf
`DUSTFRONT.bat`, dann *Senden an* und *Desktop (Verknüpfung erstellen)*.
Wer das Intro überspringen will, hängt in den Eigenschaften der
Verknüpfung hinter das Ziel ein Leerzeichen und `--nosplash`; die
Startdatei reicht Argumente durch.

**Wer lieber tippt:**

```
pip install pygame-ce
python rustfront_menu.py
```

Ohne Intro:

```
python rustfront_menu.py --nosplash
```

Nur die Splash-Sequenz ansehen:

```
python rustfront_splash.py
```

Nur das Spiel, ohne Menü und ohne Intro:

```
python -m dustfront
```

Vorlagen zum Übermalen herausschreiben, und nachsehen, was gerade aus
Dateien kommt:

```
python -m dustfront --vorlagen
python -m dustfront --assets
```

Testlauf ohne Fenster, legt Bilder zum Anschauen ab:

```
python tests/test_spiel.py
python tests/test_menues.py
python -m dustfront --kontoseite && python tests/test_konto.py
```

Beide bauen ihre Welt mit einem festen Seed auf und laufen deshalb jedes
Mal gleich ab. Das Spiel selbst würfelt weiter frei - den Seed gibt nur
der Test mit (`Spiel(app, seed=...)`). Eine Prüfung, die mal grün und mal
rot ist, sagt nichts, und man gewöhnt sich an, sie zu übersehen.

Gebraucht werden Python 3.8 bis 3.14 und pygame-ce (getestet mit 2.5.2 und
2.5.8). Die Tests wurden unter Python 3.8 und 3.11 ausgeführt;
`tests/test_konto.py` prüft ausserdem die Python-3.8-Syntax.
Schrift und fehlende Grafik entstehen zur Laufzeit. Mitgelieferte und eigene
Assets können die Platzhalter ersetzen. Wie das geht, steht
unter [Texturen und Klänge](#texturen-und-klänge).

## Steuerung im Menü

| Taste | Wirkung |
| --- | --- |
| Pfeile oder W/S | Auswahl |
| Links / Rechts | Wert ändern |
| Enter oder Leertaste | Bestätigen |
| Esc | Zurück, im Hauptmenü Beenden-Abfrage |
| F11 | Vollbild |
| Maus | Hovern, Klicken, Regler ziehen, Rad zum Blättern |

Während des Intros springt jede Taste zur nächsten Karte, Esc überspringt
die ganze Sequenz.

## Steuerung im Spiel

Alles bis auf die Maustasten und Esc lässt sich im Menü unter STEUERUNG
umlegen. Eine Taste gehört immer nur einer Aktion: legt man sie neu, wird sie
der alten weggenommen.

| Taste | Wirkung |
| --- | --- |
| W A S D | Laufen, auch während eines Sturzes (dort mit 55 Prozent Tempo) |
| Shift | Dash (drei Ladungen, laden nacheinander nach, je 2,7 s) |
| Maus links | Schiessen oder schlagen |
| Maus rechts | Einzielen (bei der Scharfschützenwaffe) |
| Mausrad | Im Gefecht: Sichtweite (weiter weg oder näher; ausserhalb des normalen Bildes Nebel). Im Einzelspiel: Ansicht eine Ebene hoch oder runter |
| Strg + Mausrad, Bild hoch / Bild runter | Ansicht eine Ebene hoch oder runter (Gefecht) |
| 1 bis 9, 0 | Waffe auf Platz 1 bis 10 wählen |
| F | Brecheisen |
| R | Nachladen |
| V | Feuerart wechseln (beim MG: Dauerfeuer oder Salve) |
| H | Medkit |
| E | Treppe benutzen, aufhelfen; am Boden: rufen |
| G | Gefallenen Mitspieler ziehen (Gefecht) |
| Q | Obere Ebenen ein- oder ausblenden (Gefecht) |
| P | Runden einstellen, in der Lobby (Gefecht) |
| Tab | Inventar |
| T | Ziellinie an oder aus |
| Z | Ziellinie über den Zeiger hinaus verlängern |
| Esc | Pausenmenü (im LAN-Gefecht läuft die Runde darunter weiter) |
| F11 | Vollbild |
| F3 | Debug-Anzeige |

## Schnee-Gelaendetest

Die eigenstaendige, vom Hauptspiel getrennte Schnee-Karte startet mit
`python schnee_test.py`. Das ist eine normale Einzelspielerpartie mit der
ueblichen Steuerung, Waffen, Gegnern, Kollision, Ebenenwechseln und HUD. Die
Karte hat drei Hoehenebenen, Schneefels-Plateaus und Schneerinnen. Laufspuren
druecken sich sichtbar in den Schnee und verblassen nach und nach. Mit Esc
oeffnet sich wie im Hauptspiel das Pausenmenue.

### Waffen

| Waffe | Art | Eigenheit |
| --- | --- | --- |
| Repetierer | Schuss | Der Allrounder. Genau, mittleres Tempo. |
| Sturmgewehr | Schuss | Rund 700 Schuss in der Minute, streut bei Dauerfeuer auf. |
| Schrot | Schuss | Sieben Kugeln auf einmal. Enger gebündelt und weiter reichend als früher, aber nah immer noch deutlich härter. |
| Scharfschütze | Schuss | Reicht weiter, als das Bild breit ist: ein Schuss endet an einer Wand, nicht an seiner Reichweite. Aus der Hüfte unbrauchbar. Rechte Maustaste halten zieht den Streifen in anderthalb Sekunden bis auf Ziellinienbreite zusammen. Gemessen: auf 300 Pixel trifft sie aus der Hüfte 8 Prozent der Schüsse, eingezielt 100. |
| MG | Schuss | Dauerfeuer oder Salven; beim Halten wird es genauer. |
| Granate | Wurf | Fliegt genau so weit, wie man zielt, zwischen 60 und 260 Pixeln. Rollt sie über eine Kante, fällt sie auf die Ebene darunter und zündet erst dort. |
| Rauchgranate | Wurf | Macht keinen Schaden, sondern eine Wand aus Rauch, und fliegt dafür kürzer als die Sprenggranate. Vierzehn Sekunden lang ist darin **nichts** zu sehen - keine Figur und kein Name, auch nicht von der Ebene darüber. |
| Molotow | Wurf | Entzündet beim Aufprall einen Bereich; das Feuer versperrt den Weg. |
| Blendgranate | Wurf | Blendet nahe Spieler; eigene Spielerkosmetik kann Ton und Bild ersetzen. |
| C4 | Sprengsatz | Kann platziert und per Fernzündung gezündet werden. |
| Raketenwerfer | Schuss | Einmalige Kartenwaffe; der Gastgeber kann die Lenkung erlauben. |
| Brecheisen | Nahkampf | Zwei Treffer töten. Schlägt in einem Kegel von 80 Grad und stösst zurück. Braucht keine Munition. |

Die Munition hängt am Namen der Waffe, nicht an ihrem Platz. Umsortieren im
Inventar kostet also keine Patrone.

## Gefecht im LAN und über das Internet

Mehrspieler wird direkt aus dem Hauptmenü gestartet. Gastgeber und Gäste
müssen dieselbe Spielversion verwenden. Details zu Lobby, Protokoll,
Spielarten und Versionsgeschichte stehen in
[`docs/MEHRSPIELER.md`](docs/MEHRSPIELER.md).

Mehrere Leute auf einer Karte, in sechs Spielarten. Nach der Runde steht
die Liste, und sie wandert in eine Bestenliste im Benutzerordner.

**Alles im Einzelnen steht in
[`docs/MEHRSPIELER.md`](docs/MEHRSPIELER.md):** Aufbau, Protokoll Feld für
Feld, Versionsgeschichte und Regeln für gemeinsames Spielen.

| Spielart | Was passiert | Wie es endet |
| --- | --- | --- |
| **PVP** | Jeder gegen jeden, keine Gegner | nach Zeit oder Abschüssen, der Gastgeber wählt |
| **PVE** | Alle zusammen gegen Wellen | wenn alle am Boden liegen |
| **PVPVE** | Wellen, und dabei jeder gegen jeden | wie PVP |
| **TEAM** | Zwei Mannschaften, Abschüsse zählen für die Mannschaft | nach Zeit oder 30 Teamabschüssen |
| **VERSUS** | Zwei Mannschaften, ein Leben je Runde, Aufhelfen durch die eigenen Leute | nach drei Rundensiegen |
| **HÜGEL** | Zwei Mannschaften, ein sichtbarer Kreis in der Kartenmitte | wenn eine Mannschaft den Kreis vollgeladen hat |

Die Einzelspieler-Systeme sind auch im Gefecht verfügbar: Waffen,
mehrstufige Karten, Treppen und Stürze, Ziellinie, Streukegel,
Nahkampfbogen und Medkits. Welche davon in einer Runde aktiv sind, hängt
von Spielart und Gastgeberregeln ab.

### Koop: am Boden und wieder auf

In **PVE** stirbt niemand sofort. Wer fällt, liegt am Boden, kann noch
kriechen und hält 45 Sekunden durch. Ein Mitspieler stellt sich daneben
und hält **E** - nach drei Sekunden steht man wieder, mit angeschlagenem
Leben. Zwei Helfer sind doppelt so schnell.

**Nach jeder Welle steht ohnehin wieder jeder.** Das ist der Ausgleich
dafür, dass eine Runde sonst mit dem ersten Fehler kippt. Vorbei ist es
erst, wenn niemand mehr steht.

In PVP, PVPVE und TEAM gibt es kein Aufhelfen: dort steigt man nach drei
Sekunden neu ein.

### Mannschaften: TEAM, VERSUS, HÜGEL

Drei Spielarten mit zwei Mannschaften, **ROT** und **BLAU**. Wer dazukommt,
geht in die kleinere - nicht abwechselnd, denn wer geht, hinterliesse sonst
eine Lücke, die nie wieder gefüllt wird. Die eigene Mannschaft trägt die
helle Farbe, die fremde die dunkle, und den Nebenmann kann man nicht
treffen. Ein kurzer Strich über dem Namen zeigt, welche Figur die eigene
ist.

**TEAM** ist Deathmatch: jeder Abschuss zählt zweimal, für den Schützen
und für die Mannschaft.

**VERSUS** gibt jedem **ein Leben je Runde**. Wer fällt, liegt am Boden -
und nur die **eigenen** Leute können aufhelfen, dafür brauchen sie vier
Sekunden statt drei. Wer die zwanzig Sekunden am Boden ausreizt, ist für
die Runde raus. Eine Runde ist zu Ende, wenn eine Mannschaft niemanden mehr
auf den Beinen hat; drei Rundensiege entscheiden. Solange eine Mannschaft
leer ist, fängt keine Runde an.

**HÜGEL** ist die Hot Zone: ein **sichtbarer Kreis in der Mitte der
Karte**, unten auf Ebene 0. Wer dort die **Mehrheit** hat, lädt für seine
Mannschaft; bei Gleichstand lädt **niemand**, und der Stand verfällt
langsam. Genau das macht den Kreis zu dem Ort, an dem man sich trifft,
statt ihn abwechselnd leerzuräumen. Der Kreis wird in den Boden gezeichnet
und nicht darüber: die Figuren stehen sichtbar darauf, und von einer
höheren Ebene aus sieht man ihn unten liegen, klein und im Dunst.

### Gegner, die mit mehreren Spielern zurechtkommen

Der Gegner aus dem Einzelspieler läuft immer auf den einen Spieler zu,
den es dort gibt. Zu viert wäre das ein Rudel, das geschlossen auf
denselben Mann zuläuft, während die anderen drei in Ruhe zielen.

Im Gefecht wählt jeder Gegner selbst, nach drei Regeln: **Nähe zählt**,
**Gedränge schreckt ab** (jeder Gegner, der schon an einem Ziel hängt,
macht es unattraktiver), und **wer entschieden hat, bleibt ein paar
Sekunden dabei** - sonst zappelt er zwischen zwei gleich weit entfernten
Spielern. Wer am Boden liegt, zieht kaum noch Gegner an, damit sie die
Helfer angreifen statt um einen Gefallenen herumzustehen.

Die Wellen wachsen mit der Spielerzahl. Dieselbe Welle wäre zu viert
sonst ein Spaziergang.

### Knappe Munition

Der Gastgeber kann Munition begrenzen. Dann hat jede Waffe einen Vorrat
ausserhalb des Magazins, der unter der Munitionsanzeige steht, und
Nachladen kostet daraus. Ist der Vorrat leer, läuft gar kein Nachladen
mehr an. **Munitionskisten** erscheinen alle 18 Sekunden neu und füllen
alles ein Stück auf.

### So spielt man es

1. Jeder startet **`MEHRSPIELER`** (oder im Hauptmenü *MEHRSPIELER*).
   Es wird nichts gefragt: jeder landet in seiner **eigenen Lobby**. Oben
   links steht ihre Adresse (etwa `192.168.1.7:50505`).
2. Wer zu jemand anderem will: **Esc -> ANDERER LOBBY BEITRETEN**. Dort
   stehen alle Lobbys im selben Netz von selbst in einer Liste - anklicken
   genügt. Eine Adresse von Hand geht darunter, ebenso ein Kennwort und,
   ohne Konto, der eigene Name. Wer eine fremde Lobby oder Runde verlässt
   (Esc -> *GEFECHT VERLASSEN*), aus ihr abgewiesen wird oder dessen
   Gastgeber aufhört, landet wieder in **seiner eigenen** Lobby.
3. In der Lobby: links die Arena (PVP), in der Mitte der Schiessstand,
   rechts das Gehege mit Zombies. Auf dem Platz dazwischen tut niemandem
   etwas weh. Der Gastgeber stellt mit **P** die nächste Runde ein -
   Spielart, Karte, Schwierigkeit, Ausrüstung und alles andere - und
   startet sie. Wer mehrere Runden hintereinander will, klappt den
   Rundenplan auf. Nach der Runde geht es weiter oder zurück in die
   Lobby. **Die Regeln bestimmt allein der Gastgeber**; die anderen sehen
   die Tafel, können aber nichts ändern.
   Hat jemand **Spielerkosmetik** (siehe unten), startet der Gastgeber
   **mit** oder **ohne** - mit erst, wenn sie bei allen angekommen ist.
4. Fertig. Esc öffnet das Menü; *SPIEL BEENDEN* macht zu (vom
   Hauptmenü aus gestartet: zurück ins Hauptmenü).

### Spielerkosmetik: der eigene Knall

Ein eigener Ton und ein eigenes Bild für die Blendgranate. In der
Kontoseite (`KONTO.html`, Reiter **KOSMETIK**) eine MP3 laden und
zuschneiden, Bass und Lautstärke hochdrehen, auf Wunsch den Knall und das
Pfeifen aus dem Spiel dazumischen; ein Bild laden und mit Filtern
bearbeiten. Wer dann eine Blendgranate wirft, klingt nach seinem Ton, und
im Weiss steht sein Bild - bei allen, wenn der Gastgeber mit Kosmetik
startet. Der Ton dauert 1 bis 4 Sekunden und **wird immer leiser**; das
prüft das Spiel selbst, bei jedem Paket. Auf dem Server braucht es dafür
einmal die Tabelle aus [`docs/KONTO.md`](docs/KONTO.md), Abschnitt 5.6.
Wie es verteilt wird: [`docs/MEHRSPIELER.md`](docs/MEHRSPIELER.md), 12c.

Für eine LAN-Runde müssen alle im selben Netz sein - gleiches WLAN oder
gleicher Switch. Eine Firewall fragt beim ersten Mal, ob Python ins Netz
darf. Beim Gastgeber muss das erlaubt sein (TCP 50505, für die Lobbysuche
UDP 50504), sonst findet ihn niemand; wer nur beitritt, braucht es nicht.
Welche Ports das Spiel seit wann benutzt: [`docs/MEHRSPIELER.md`](docs/MEHRSPIELER.md),
12g, "Was im Netz wann dazukam".

### Über das Internet

Seit 0.32 gibt es dafür keine eigene Startdatei mehr; das Internet geht
über die Kommandozeile: `python -m dustfront --host --online --passwort
GEHEIM`. Das Spiel versucht dann, den Port im Router selbst freizugeben
(UPnP), und sagt die Adresse an, die die anderen in der Lobbysuche unter
*ADRESSE* eintippen.

Drei Dinge dazu, ehrlich:

* **Es hängt am Router.** Viele Heimrouter können UPnP und haben es an,
  dann geht es von allein. Manche können es nicht, und hinter einem
  Mobilfunkanschluss oder in einem Wohnheim hilft es gar nichts. Klappt es
  nicht, schreibt das Spiel genau hin, was von Hand einzutragen ist:
  Protokoll TCP, Port, Zieladresse.
* **Es wird ruckeliger als im LAN.** Der Gastgeber rechnet alles; ein Gast
  sieht seine eigene Figur erst nach einem Hin- und Rückweg. Im LAN sind
  das zwei Millisekunden, über das Internet eher dreissig bis hundert.
  Zielen folgt trotzdem sofort, das rechnet jeder bei sich.
* **Ein offener Port ist ein offener Port.** Wer die Adresse kennt, kann
  mitspielen. Darum gehört `--passwort` dazu. Ohne eines
  kommt jeder herein, der die Adresse hat.

Wer lieber tippt:

```
python -m dustfront --lobby
python -m dustfront --host --name MEISTER --modus pve --knapp
python -m dustfront --host --name MEISTER --modus pvp --ende abschuesse --wert 20
python -m dustfront --host --name MEISTER --modus huegel --ende zeit --wert 600
python -m dustfront --host --name MEISTER --modus pvp --loadouts
python -m dustfront --join 192.168.1.7 --name BESUCH
python -m dustfront --bestenliste
python -m dustfront --konto liste
python -m dustfront --karten
python -m dustfront --host --name MEISTER --modus huegel --karte staubtal
python -m dustfront --kosmetik
python -m dustfront --kontoseite
```

`--kosmetik` schreibt die Vorschaubilder für Kisten, Skins und die
zweite Siegtafel nach `kosmetik_vorschau/`. **Eingebaut ist davon nichts**
- es sind Bilder, über die sich entscheiden lässt, ob es so aussehen
soll. Warum, und was ein Einbau kosten würde, steht in
[`docs/KOSMETIK.md`](docs/KOSMETIK.md).

Was auf der Kommandozeile steht, wird die erste geplante Runde in der
Lobby; `--sofort` überspringt die Lobby und fängt gleich an.
`--team rot|blau|auto` wählt die Mannschaft, `--runden N` die Zahl der
gespielten Runden in VERSUS. `--online` versucht, den Port im Router freizugeben,
`--passwort WORT` setzt ein Kennwort - beides zusammen ist der Weg über
das Internet.
`--loadouts` lässt jeden sein eigenes Loadout tragen - zwei Waffen und
eine Wurfwaffe statt der vollständigen Hotbar; ohne den Schalter hat jeder
alles. Konten, Statistik und Loadouts stehen in
[`docs/KONTO.md`](docs/KONTO.md).
`--modus` ist `pvp`, `pve`, `pvpve`, `team`, `versus` oder `huegel`;
`--ende` ist `zeit` oder `abschuesse`, `--wert` die Sekunden
beziehungsweise Abschüsse. Bei `versus` und `huegel` ist die Zeit nur die
Notbremse - beide enden von selbst.

### Wie es aufgebaut ist

**Ein Rechner rechnet, alle anderen schauen zu.** Der Gastgeber simuliert
die ganze Welt. Gäste schicken nur, was sie drücken, und bekommen
zurück, wo alles steht. Damit gibt es keinen Streit darüber, wer
getroffen hat, und niemand kann durch eine geänderte Datei schummeln.
Der Preis ist ein Hin- und Rückweg Verzögerung, im LAN unter zwei
Millisekunden.

**Keine Threads.** Die Verbindungen stehen auf nicht-blockierend, einmal
je Bild wird nachgesehen, was angekommen ist. Eine zweite Schleife wäre
nur eine Quelle für Fehler, die man nicht nachstellen kann.

**Jeder Spieler hat eine eigene Fraktion.** Die Trefferabfrage
überspringt alles, was zur selben Fraktion gehört - alle Spieler tragen
sonst "mensch" und könnten sich nie treffen. So bleibt der Spielkern
unverändert.

Nicht übers Netz gehen Partikel, Hülsen und Blutflecken. Die entstehen
bei jedem selbst und sind reine Kosmetik.

| Datei | Inhalt |
| --- | --- |
| `netz.py` | Verbindungen, Protokoll aus JSON-Zeilen, Gastgeber und Gast |
| `mehrspieler.py` | Die Gefechtsszene, Punkte, Wiedereinstieg, Rundenende |
| `bestenliste.py` | MVP-Punkte und Auszeichnungen über alle Runden, im Benutzerordner |

## Wie sich das Spiel anfühlen soll

Drei Regeln, die über einzelnen Funktionen stehen. Wer etwas Neues
einbaut, hält sich daran, sonst fällt es auf.

**Keine Handlung sperrt eine andere.** Man darf jederzeit die Waffe
wechseln, nachladen, ein Medkit ansetzen, die Ebene wechseln oder die
Ansicht verschieben - auch mitten in einer anderen Handlung und auch im
Sturz. Was dabei noch nicht fertig war, wird verworfen, nicht abgewartet.
Ein Waffenwechsel bricht also das Nachladen ab, statt darauf zu warten. Im
Code sammelt `Spieler.abbrechen()` diese Abbrüche an einer Stelle; eine
neue Handlung trägt sich dort ein.

**Nichts springt.** Jede Bewegung, die man sieht, entsteht Bild für Bild.
Besonders der Sturz: die Figur bleibt im Bild stehen und die Welt wächst
unter ihr heran, statt dass sie an ihren späteren Landeplatz gesetzt wird.
Steht unten etwas im Weg, rutscht sie während des Fluges zur Seite - aber
nur so lange, bis sie freien Grund unter sich hat, danach gehört die
Bewegung wieder dem Spieler. `tests/test_spiel.py` misst das nach: nicht
den Zustand, sondern die Bildposition von Schritt zu Schritt.

**Man bleibt am Steuer.** Auch im Sturz lässt sich die Figur lenken, mit
55 Prozent des normalen Tempos (`luftsteuerung` in `config.py`). Gemessen
sind das rund 25 Pixel quer auf einen Sturz über zwei Etagen - genug, um
ein Loch noch zu treffen oder daneben zu landen.

**Man sieht, was man tut.** Die Figur trägt die Waffe, die gewählt ist,
sichtbar in der Hand. Zielhilfen gehören zu der Ebene, auf der man steht,
und verschwinden, sobald man mit dem Mausrad woanders hinschaut.

## Dateien

Aussen liegt das Menü, innen das Spiel. Beides läuft auch einzeln.

| Datei | Inhalt |
| --- | --- |
| `DUSTFRONT.bat` | Startdatei zum Doppelklicken, Windows |
| `DUSTFRONT.command` | Startdatei zum Doppelklicken, macOS und Linux |
| `SPIELTEST.command` | Direkt ins Spiel, macOS und Linux |
| `rustfront_menu.py` | Hauptmenü, Kaltstart, Optionen, Spielstand, Einstiegspunkt |
| `rustfront_splash.py` | Ablauf, Zeitdehnung und Klangsynthese der Splash-Sequenz |
| `splash_engine.py` | Zeichenwerk der Splash-Sequenz, portiert aus der Web-Fassung |

Das Spiel selbst liegt im Paket `dustfront/`:

| Datei | Inhalt |
| --- | --- |
| `config.py` | Zentrale Spielwerte, Waffen, Gegner, Karten- und Netzregeln |
| `core.py` | Anwendung, Szenenstapel, feste Zeitschritte, Eingabe, Bildablage |
| `world.py` | Ebenen, Kacheln, Kollision, Sichtlinien, Treppen, Abgründe |
| `entities.py` | Spieler, Gegner, Geschosse, Granaten, Aufsammler |
| `render.py` | Kamera, Tiefenwirkung, Schatten, Ziellinie, HUD |
| `play.py` | Die Spielregel: Wellen, Tod, Neustart |
| `menues.py` | Pause, Einstellungen, Steuerung, Mitwirkende |
| `inventar.py` | Ausrüstung, Waffenraster, Tasche, Hotbar |
| `ui.py` | Bedienelemente: Kästen, Knöpfe, Reiter, Regler, Schalter |
| `einstellungen.py` | Einstellungen und Tastenbelegung, lesen und schreiben |
| `pfade.py` | Wo diese Dateien liegen, je nach Betriebssystem |
| `art.py`, `audio.py`, `font.py` | Grafik, Klang und Schrift, alles zur Laufzeit erzeugt |
| `vorlagen.py` | Die beiden Werkzeuge `--vorlagen` und `--assets` |
| `netz.py` | LAN-Verbindungen und Protokoll |
| `mehrspieler.py` | LAN- und Internetgefechte |
| `lobby.py` | Die Lobby und der Rundenplan |
| `regeln.py` | Die Regeln eines Gefechts, an einer Stelle |
| `anzeige.py` | Die Anzeige im Gefecht |
| `minikarte.py` | Die Minikarte oben links |
| `windows_tls.py` | Unter Windows: Zertifikate von Windows prüfen lassen |
| `spielerkosmetik.py` | Eigener Ton und eigenes Bild für die Blendgranate: prüfen, verteilen, zeigen |
| `bestenliste.py` | MVP-Punkte und Auszeichnungen über alle Runden |
| `konto.py` | Anmeldung, Profil, Loadouts, das Journal der Runden |
| `ablage.py` | Wo Konten und Zahlen liegen: Datei oder Server |

Und `karten/` daneben: jede Karte eine Textdatei, ein Zeichen eine
Kachel, die Ebenen hintereinander. `~` steht für ein Loch auf einer
höheren Ebene, `^` und `v` verbinden die Aufzüge. `werkzeug_staubtal.py`
erzeugt STAUBTAL neu, falls man am Grundriss etwas ändern will - danach
ist die Datei ganz normaler Text und von Hand weiterzubearbeiten.

Daneben liegt `docs/`:

| Datei | Inhalt |
| --- | --- |
| `KARTE.md` | Der Weltenplan: Kontinent, Orte, Wandler, Front, Meilensteine |
| `MEHRSPIELER.md` | Der LAN-Mehrspieler vollständig: Aufbau, Protokoll, alle sechs Spielarten, jede Zahl, jeder aufgetretene Fehler, Bauanleitung zum Wiedereinbau |
| `KONTO.md` | Konto, Statistik und Loadouts: warum Supabase, warum die Zahlen nicht auseinanderlaufen können, und wie man es in zehn Minuten aufsetzt |
| `KOSMETIK.md` | Entwurf und Umfang der geplanten Kisten, Skins, Musikkits und Siegtafel; Spielerkosmetik für Blendgranaten ist separat eingebaut |

### Wo die Einstellungen liegen

**Nicht im Spielordner.** Wer das Spiel neu herunterlädt, den Ordner löscht
oder `git clean` laufen lässt, soll seine Tastenbelegung behalten. Deshalb
liegen `einstellungen.json` und `tasten.json` dort, wo das System seine
Benutzerdaten ablegt:

| System | Ordner |
| --- | --- |
| Windows | `%APPDATA%\\Dustfront`, also `C:\\Users\\<name>\\AppData\\Roaming\\Dustfront` |
| macOS | `~/Library/Application Support/Dustfront` |
| Linux | `$XDG_CONFIG_HOME/dustfront`, sonst `~/.config/dustfront` |

Der Pfad steht auch unten in den Einstellungen, man muss also nicht suchen.

**Tragbarer Betrieb.** Liegt eine Datei `portable.txt` neben dem Paket, wird
stattdessen der Unterordner `daten` im Spielordner benutzt. Praktisch für
einen USB-Stick oder einen Schulrechner, auf dem man nichts im Benutzerprofil
ablegen darf.

Tasten stehen als lesbare Namen in der Datei, also `"w"` und `"left shift"`,
nicht `119` und `1073742049`. Das kann man notfalls mit einem Texteditor
reparieren. Kaputte oder unbekannte Einträge werden verworfen und durch die
Vorgabe ersetzt; eine beschädigte Datei kostet höchstens die eine
Einstellung, die kaputt ist, nie den Start.

Das alte Menü legt daneben weiter `rustfront_settings.json` und
`rustfront_save.json` im Spielordner ab. Beide stehen in der `.gitignore`.

## Texturen und Klänge

Alles, was das Spiel zeigt und hört, hat einen Namen. Zu jedem Namen sucht
es zuerst eine Datei und zeichnet oder rechnet nur dann selbst, wenn keine da
ist:

```
assets/<name>.png           Bild
assets/sfx/<klangname>/aufnahme.wav   Klang
```

**Eine hingelegte Datei ersetzt den Platzhalter, ohne dass eine Zeile Code
geändert wird.** Kein Eintrag nachzutragen, keine Liste zu pflegen. Datei
hinlegen, Spiel starten, fertig. Bei Bildern gehen auch `.webp` und `.bmp`,
bei Klängen `.ogg` und `.mp3`; gesucht wird in dieser Reihenfolge, die erste
gefundene gewinnt. Klangaufnahmen liegen in `assets/sfx/<klangname>/`; WAV,
OGG und MP3 sind erlaubt, und der Dateiname darin ist frei. Bisherige flache Dateien
wie `assets/sfx/medkit.wav` bleiben als Rückfall unterstützt.

### Der Weg von der leeren Datei ins Spiel

```
python -m dustfront --vorlagen
```

schreibt jedes Bild, das das Spiel kennt, nach `assets_vorlage/` — in der
richtigen Grösse, unter dem richtigen Dateinamen, dazu eine
Übersichtstafel `_uebersicht.png` mit allen Bildern nebeneinander.
Übermalen, nach `assets/` kopieren, fertig. Umbenennen entfällt.

```
python -m dustfront --assets
```

sagt umgekehrt zu jedem Namen, ob er gerade aus einer Datei oder aus dem Code
kommt, und nennt jede Datei, die sich nicht lesen liess. Damit prüft man,
ob eine neue Textur wirklich angenommen wurde.

### Grösse

Jedes Bild hat ein Sollmass. Wer genau darin malt, bekommt die Datei Pixel
für Pixel so ins Spiel, wie sie ist. Wer grösser malt, darf das: die Datei
wird beim Laden hart auf das Sollmass gerechnet, ohne Weichzeichnen. Ein
sauberes Vielfaches — doppelt, dreifach, vierfach — rechnet exakt herunter
und sieht am besten aus.

Wer dauerhaft ein anderes Mass will, ändert die Zahl in `BILD_MASS` in
`dustfront/config.py`. Das ist die eine Stelle dafür, und ein Test wacht
darüber, dass Tabelle und gezeichnete Platzhalter sich decken.

Die vollständige Namens- und Grössentabelle ist `BILD_MASS` in
`dustfront/config.py`; sie enthält auch team- und waffenspezifische Figuren,
Schwungbilder, Effekte und HUD-Symbole. `--vorlagen` schreibt aus dieser
Tabelle aktuelle Vorlagen mit den passenden Abmessungen.

Die Klangnamen stehen als `KLANG_NAMEN` in `config.py` und in
`assets/sfx/LIESMICH.md`, mit der Regel, wann welcher spielt.

### Worauf beim Malen zu achten ist

* **Kacheln** sind 32x32 und müssen randlos aneinanderpassen.
* **Figuren** sitzen mittig auf einer quadratischen Fläche und schauen nach
  rechts, also auf 0 Grad. Das Spiel dreht sie von dort aus. Wer nach oben
  malt, dessen Figur läuft seitwärts.
* **Durchsichtigkeit** benutzen, wo nichts ist. Die Übersichtstafel legt
  Durchsichtiges auf ein Schachbrett, damit man den Rand sieht.
* **Waffensymbole** sind winzig. Dort zählt nur die Silhouette: Länge des
  Laufs, Dicke des Gehäuses, was oben und unten heraussteht.

### Wenn etwas schiefgeht

Eine Datei, die sich nicht lesen lässt, kostet nichts: das Spiel nimmt den
Platzhalter und läuft weiter. Den Grund zeigt `--assets`. Ein grelles Pink
im Spiel heisst dagegen, dass weder Datei noch Code diesen Namen kennen —
dann stimmt der Name nicht.

Dass ein Dauerfeuer nicht aus einer einzigen Kopie klingt, regeln
Nummern-Fassungen: `schuss_sturm_1.wav` bis `_8` daneben legen, und das
Spiel wählt bei jedem Schuss zufällig eine davon.

## Versionsnummern

Die Nummer steht an **genau einer Stelle**: `VERSION` und `PHASE` ganz oben in
`rustfront_menu.py`. Die Splash-Sequenz und die Fusszeile im Menü holen sie
sich von dort. Wer die Nummer ändert, ändert nur diese zwei Zeilen.

### Aufbau

```
0 . 4 . 0     PRE-ALPHA
│   │   │     └── Phase, siehe Tabelle unten
│   │   └── PATCH
│   └── MINOR
└── MAJOR
```

### Welche Ziffer wird hochgezählt?

Geh die drei Fragen **von oben nach unten** durch und nimm die erste, die mit
ja beantwortet wird. Es gibt immer genau eine Antwort.

| # | Frage | Was passiert |
| --- | --- | --- |
| 1 | Ist das Spiel ab jetzt zum ersten Mal von vorn bis hinten spielbar? | `1.0.0` |
| 2 | Gibt es etwas, das es vorher **gar nicht** gab? | MINOR +1, PATCH auf 0 |
| 3 | Wurde nur etwas **Bestehendes** repariert, justiert oder umgeschrieben? | PATCH +1 |

Ab 1.0.0 kommt eine vierte Frage dazu: MAJOR +1, wenn alte Spielstände nicht
mehr laden oder das Spiel grundlegend anders funktioniert.

### Feste Regeln

* Die Nummer geht **nur hoch**, nie runter, und keine Nummer wird zweimal
  vergeben.
* Keine Ziffer überspringen: nach `0.4.0` kommt `0.5.0`, nicht `0.6.0`.
* Wird MINOR erhöht, fällt PATCH auf 0 zurück. Wird MAJOR erhöht, fallen
  MINOR und PATCH auf 0.
* Im Zweifel PATCH. Zu vorsichtig zählen ist nie falsch.
* Die Nummer wird **vor** dem Push geändert, und die Commit-Nachricht nennt
  sie. Dann sieht man in der Historie sofort, welcher Commit welche Version
  ist.
* Neue Version = neue Zeile in der Tabelle unten.

### Phasen

Die Phase hängt nur davon ab, wie weit das Spiel ist, nicht von der Nummer.

| Phase | Bedeutung |
| --- | --- |
| `PRE-ALPHA` | Einzelne Teile laufen, eine durchgehende Spielschleife fehlt. |
| `ALPHA` | Man kann Runden von Anfang bis Ende spielen; Inhalte und Feinschliff fehlen noch. Hier steht das Projekt. |
| `BETA` | Alle Inhalte sind drin, es geht nur noch um Fehler und Balance. |
| `RELEASE` | Ab `1.0.0`. |

### Bisher

| Version | Was dazukam |
| --- | --- |
| 0.33.0 | Neue spielbare Schnee-Karte `schnee_test.py` mit drei Höhenebenen, Schneefels-Plateaus im regulären 3D-Klippenrenderer und sichtbaren Laufspuren. Das Sand-Kachelmuster ist entfernt, der Schrotknall setzt ohne Anfangsstille ein, und die Aufzüge liegen am Plateau-Rand. Gastgeber und Gäste brauchen dieselbe Version und Kartendatei; kein Protokollwechsel. |
| 0.32.30 | Erste separate Schnee-Skizze; in 0.33.0 als vollständige, normal spielbare Einzelspielerkarte neu umgesetzt. |
| 0.32.29 | STAUBTAL stark vergrößert und am Lageplan ausgerichtet: 300 × 240 Kacheln mit drei nummerierten Hotzones, drei Plateauformen und acht geschützten Aufzügen. Hotzone 3 liegt in einem befestigten Hof. Gastgeber und Gast müssen dieselbe Version und Karte haben; kein Protokollwechsel. |
| 0.32.28 | Inventar-Statistik verträgt Waffen ohne Schadenswert wie C4; der Import des Spiels bricht dadurch nicht mehr ab. Gastgeber und Gast brauchen dieselbe Version; kein Netzprotokoll und keine Karten geändert. |
| 0.32.27 | Brecher vergrössert; LMG-, Pumpgun- und Rauchgranatentöne erneuert; C4 mit Fernzündung, Admin-Konsole, Wurfgranaten ohne Nachladepause und Direktstart ohne Intro ergänzt. Gastgeber und Gast brauchen dieselbe Version für C4-Zustand, Admin-Befehle und den vergrösserten Brecher; Karten unverändert. |
| 0.32.26 | **Mehrspieler-Einstieg und Brecher**: Im Hauptmenü wählt man beim Mehrspieler zwischen Lobby erstellen und beitreten. Der Brecher hat 95 Leben und sieht wie ein dunklerer Zombie ohne Bruststreifen aus. Gastgeber und Gäste brauchen dieselbe Version, damit Gegnerwerte übereinstimmen; kein Protokoll und keine Karten geändert. |
| 0.32.25 | **Ein gemeinsames Hauptmenü**: Einzelspieler, Mehrspieler, Optionen, Steuerung und Mitwirkende sind vom selben Start aus erreichbar. Nach einer Runde kehrt das Spiel ins Menü zurück. Kein Netzprotokoll und keine Karten geändert. |
| 0.32.24 | **RPG verstärkt**: Der Raketenschaden steigt auf 150, der Explosionsradius auf 104 Weltpixel. Gastgeber und Gast müssen dieselbe Version nutzen, damit der Gefechtsschaden übereinstimmt. Kein Drahtprotokoll und keine Karten geändert. |
| 0.32.23 | **Runden-MVP und Music Kit**: MVP-Punkte werten Abschüsse, Gegner und Bosse, Schaden, Trefferquote, Hilfen, Zielzeit, Medkits und Tode; Rundentafel und Bestenliste zeigen Punkte und Auszeichnungen. Eigener Kontoton wird für Sieg und Niederlage abgespielt; die Kontoseite benötigt die neue `music_kit`-Spalte und RPC-Fassung aus `docs/KONTO.md`. Das Endpaket enthält die MVP-Wertung; Gastgeber und Gäste brauchen dieselbe Version. Keine Karten geändert. |
| 0.32.22 | **LMG-Klang entfernt**: Das LMG spielt den Sturmgewehrklang; der eigene LMG-Klang und die Soundboard-Proben dafür sind entfernt. Kein Netz- oder Kartenverhalten geändert. |
| 0.32.21 | **Klänge angepasst**: Der MG-Schuss nutzt wieder den alten kurzen Ausschnitt; die Nahkampf-Schwing- und Trefferklänge laufen vollständiger aus. Rundenstart, Sieg und Niederlage sind im Soundboard direkt prüfbar. Kein Netz- oder Kartenverhalten geändert. |
| 0.32.20 | **Soundboard-Pfad korrigiert**: Das separate Soundboard sucht Aufnahmen nun in `assets/sfx` statt neben dem Projektordner. Es kennzeichnet pro Klang, ob eine Audiodatei oder ein Code-Platzhalter abgespielt wird. Kein Netz- oder Kartenverhalten geändert. |
| 0.32.19 | **Klangkorrekturen und separates Soundboard**: Nahkampf spielt nur noch den passenden Schwung-/Trefferklang; Rauch, MG, Scharfschütze und Molotow erhalten passende Ausschnitte. `python tools/soundboard.py` startet unabhängig vom Spiel und bietet Einzelklang, MG-Dauerfeuer, MG-Salve und Sturmgewehr bei Spieltempo. Mehrspieler: kein Protokollwechsel; Gastgeber und Gast verwenden denselben Klangstand. |
| 0.32.18 | **Neue Spielklänge eingebaut**: MP3-Aufnahmen werden geladen und Schussserien zu einzelnen Schüssen zugeschnitten. Neu zu hören: Nachladen, Zu-Boden-Gehen, Rauchgranate, Brecheisen-Schwung und Treffer, Rundenstart sowie Match-Sieg oder -Niederlage. Das Mehrspieler-Protokoll teilt die neuen Klangereignisse und Trefferart mit; Gastgeber und Gast brauchen dieselbe Version. |
| 0.32.17 | **Aufnahmeordner für alle 24 Klänge**: Lege WAV-, OGG- oder MP3-Dateien mit beliebigem Namen in `assets/sfx/<klangname>/`; mehrere Dateien pro Ordner dienen als zufällige Fassungen. Bestehende flache Dateien bleiben als Rückfall erhalten. Kein Netz- oder Kartenverhalten geändert. |
| 0.32.16 | **Dash und Schussbild**: die drei Windlinien bauen sich nacheinander auf; das Mündungsfeuer sitzt vor der Laufspitze. Der Lichtkern bleibt erhalten. Rein visuell, keine Netz- oder Kartenänderung. |
| 0.32.15 | **Dash und Medkit**: Der Dash zeichnet drei kleine, grauweisse Windlinien hinter der Figur. Am Medkit in der Hand wurden die losen weissen Pixel am Rand entfernt. Rein visuell, keine Netz- oder Kartenänderung. |
| 0.32.14 | **Dash-Animation neu gestaltet**: sofort sichtbarer Impulsring und Richtungs-Chevron an der Figur, nahe teamfarbene Nachbilder und gebrochene Staubschlieren. Rein visuell, keine Netz- oder Kartenänderung. |
| 0.32.13 | **Dash-Animation**: ein pixeliger Türkis- oder Teamfarben-Stoss mit zwei gefärbten Nachbildern, gebrochenen Bewegungslinien, sichtbarem Absprung und kurzem Ausklang. Der Gast bekommt denselben Animationstakt vom Gastgeber; das Weltpaket hat dafür ein neues Feld. Gastgeber und Gast müssen dieselbe Version nutzen. |
| 0.32.12 | **Gameplay-Randfehler behoben**: Medkits heilen weder Tote noch Spieler am Boden und werden bei Waffenwechsel abgebrochen; ein Sturz beendet den Dash. Geschosse mit Nulltempo schlagen sicher ein, Kartenränder gelten nicht als Löcher und Raketen wechseln dort nicht die Ebene. Lange Menü- und UI-Texte werden innerhalb ihrer Felder gekürzt. Mehrspieler: gleiches Verhalten für Gastgeber und Gast, keine Protokolländerung; Gastgeber und Gast müssen dieselbe Version nutzen. |
| 0.1.0 | Hauptmenü |
| 0.2.0 | Splash-Sequenz |
| 0.2.1 | Vollbild und Rufzeichen-Eingabe repariert |
| 0.3.0 | Projekt ins Repo, README |
| 0.4.0 | Klänge auf materialbasierte Synthese umgestellt, zweiteiliger Spruch auf der letzten Karte, Versionsanzeige |
| 0.5.0 | Das Spiel selbst: Welt, Wesen, Darstellung, Wellen, feste Zeitschritte |
| 0.6.0 | Höhenebenen mit echtem Abstand, Löcher zum Durchfallen und Durchschiessen, Sturz mit Steuerung in der Luft |
| 0.7.0 | Sechs Waffen, Medkits, Hotbar, Ziellinie; Einstellungen und Tastenbelegung im Benutzerordner |
| 0.8.0 | Pausenmenü, Einstellungen, umlegbare Steuerung, Abspann, Inventar |
| 0.9.0 | Texturen und Klänge aus Dateien: `assets/` nimmt jede Auflösung an, Vorlagen-Werkzeug, Bestandsliste |
| 0.10.0 | Schatten, Blut, Brandfleck, Wandschatten und Vignette ebenfalls ersetzbar; Blutfleck richtet sich nach der Grösse des Wesens |
| 0.11.0 | Sturz ohne Ruck, Waffe in der Hand sichtbar, durchgehend rote Ziellinie, keine Handlung sperrt mehr eine andere |
| 0.11.1 | Steuerung in der Luft im Test nachgewiesen und gegen das Abrutschen abgesichert; Testläufe mit festem Seed reproduzierbar |
| 0.11.2 | Startdateien zum Doppelklicken für Windows und macOS; Weltenplan in `docs/KARTE.md` |
| 0.12.0 | Das Hauptmenü startet das echte Spiel statt einer Platzhalter-Szene; Startdatei für den direkten Spieltest |
| 0.13.0 | LAN-Gefecht: mehrere Spieler auf einer Karte, keine Gegner, Namen, Punkte und eine Bestenliste im Benutzerordner |
| 0.13.1 | Im Gefecht gingen einzelne Tastendrücke verloren; dazu fehlten Zielhilfen, Mausrad, Medkits, Munitionsanzeige und sichtbare Granaten |
| 0.14.0 | Mehrspieler fertiggestellt: drei Spielarten, Aufhelfen, Wellen mit mehrspielertauglicher Gegner-KI, knappe Munition mit Nachschubkisten. Letzter Stand dieses Zweigs |
| 0.16.0 | Mannschaften im Gefecht: TEAM, VERSUS mit einem Leben je Runde und Aufhelfen durch die eigenen Leute, HÜGEL mit sichtbarem Kreis in der Kartenmitte. Alles in `docs/MEHRSPIELER.md` beschrieben. Nur auf `multiplayer-test`; 0.15.0 gehört dem Hauptzweig ohne Mehrspieler |
| 0.17.0 | Rauchgranate als siebte Waffe; Granaten fallen über Kanten auf die Ebene darunter; Einstiegsschutz, Startmedkits und Medkit-Nachschub als Schalter beim Aufmachen. Dazu vier gemeldete Fehler behoben: kein Ton im Gefecht, Ziellinie des Gastes am Einstiegspunkt, Versetzung nach einem Sturztod, Granaten prallten an Löchern ab. Brecheisen tötet in zwei Treffern, Schrot reicht weiter und streut enger, Scharfschütze weiter als das Bild breit ist |
| 0.32.11 | **Aufzug auf STAUBTAL (Versuch)**: die Westrampe der KANZEL (grosses Plateau) ist jetzt eine Tür unten im Fels mit dem Schachtkopf genau darüber. Hineinlaufen genügt, ohne Taste; man kommt eine Kachel weiter auf der anderen Ebene heraus, in die Richtung, in die man lief, und die Kamera geht den Schritt mit - die Figur bleibt im Bild stehen (gemessen höchstens 3 px), nur die Umgebung blendet über. Zurück genauso: oben in den Schacht laufen, unten vor der Tür heraus. Gegner nehmen ihn, wenn er auf ihrem Weg liegt (gemessen: keine Umsetzungen, alle ausser den Speiern kommen an), aber nicht, wenn sie nur hineingedrängt werden; Bosse nie. Die anderen Plateaus haben weiter Rampen, zum Vergleichen. Netz: kein neuer Port und keine neue Nachricht, der Wechsel kommt wie jeder Ebenenwechsel über die gewohnte Meldung. Aber die Karte hat zwei neue Kachelarten: Gastgeber und Gast brauchen dieselbe Version (wird beim Beitreten geprüft) |
| 0.32.10 | **Ebenenwechsel ohne Aussetzer**: nach Treppe oder Luke war man bis jetzt eine halbe Sekunde unsichtbar (nur der Laser blieb), und die Helligkeit zog nach. Grund: die Ansicht glitt langsam zur neuen Höhe, und solange galt die eigene Etage als "darüber" (ausgeblendet) oder "darunter" (abgedunkelt). Jetzt springt die Ansicht sofort, und das letzte Bild der alten Ebene blendet in 0,22 s aus. Stürze sinken weiter mit der Figur. Netz: keine Änderung, nur Darstellung beim eigenen Rechner |
| 0.32.9 | **Brecheisen-Schwung**: die Figur hält beim Schlag jetzt wirklich das alte Brecheisen aus der Schnellleiste mit beiden Händen, die Arme schwingen mit (9 Bilder über den Schwungbogen); die Waffe verschwindet für den Schwung ganz und das Eisen bleibt danach noch 0,14 s in der Hand, damit man es sieht. Die alte rostige Linie und der helle Block sind weg, nur eine schwache Punktspur der Spitze bleibt. Netz: keine Änderung (das vorhandene Schlagfeld wird genutzt) |
| 0.32.8 | **Knall der Blendgranate**: deutlich leiser mit Abstand (bei 300 Pixeln rund zwei Drittel, ab 500 Pixeln knapp die Hälfte der gewöhnlichen Dämpfung) und noch einmal halb so laut, wer wegschaut; ganz nah (2 Kacheln) voll; nie leiser als hörbar. Gilt für den Standardknall und für den Ton aus der Spielerkosmetik. **Barrierefreiheit**: neue Zeile BLENDGRANATE TON (wie vom Werfer / nur Standard), getrennt vom Bild - das eine betrifft das Auge, das andere das Ohr |
| 0.32.7 | **Kamera ruhig**: Beim Zoomen wechselte das Seitenverhältnis der Zeichenfläche in jedem Bild um Bruchteile (gerundete Breite und Höhe passten nicht zueinander) - das Bild wackelte zur Seite und nach oben. Gezoomt wird jetzt in Stufen von 1/40, bei denen es genau 16:9 bleibt. Der kleine Vorlauf zur Maus richtet sich nach dem Abstand der Maus von der Bildmitte statt nach dem Weltpunkt unter ihr; der wanderte mit der Kamera mit, und das Bild zog sich nach. Die Kamera folgt straffer (15 statt 11) und schleicht den letzten halben Pixel nicht mehr aus. **BLICK VORAUS**: Vorgabe 70 statt 110 Pixel, unter Barrierefreiheit einstellbar von 40 bis 150 |
| 0.32.6 | **Zombies und Treppen**: Gegner wechselten die Ebene schon eine Kachel *vor* der Rampe (der Rest der nächsten Kachel wurde für "steht drauf" gehalten). Sie kamen oben schräg neben der Rampe im Nichts an, steckten fest und wurden nach ein paar Sekunden umgesetzt - das war das "Verschwinden in Sicht". Jetzt wechseln sie nur auf der Rampe selbst und nur auf festen Boden; gemessen mit 15 gemischten Zombies auf STAUBTAL: vorher 7 bis 11 Umsetzungen in 90 s, jetzt keine. Und umgesetzt wird nur noch, wer seit 5 Sekunden in niemandes Bild war. Der zweite Zombie-Arm ist das Spiegelbild des ersten und kommt jetzt auch von der Seite |
| 0.32.5 | **Menüs aufgeräumt**: Ä, Ö und Ü haben in beiden Pixelschriften volle Buchstabenhöhe, die Punkte sitzen über der Zeile (vorher waren sie zwei Pixel kleiner). Die **Steuerung im Hauptmenü** zeigt die echte Belegung des Spiels statt der alten Entwurfstasten (Bauen, Fahr-Modus, Autopilot). Die **Optionen im Hauptmenü** teilen sich Vollbild, Pixelraster, Bildrate und Lautstärken mit dem Spiel; CRT-Filter, Intro und Reaktorbrummen gibt es nur im Hauptmenü. Im **Inventar** passen alle neun Hotbar-Plätze, und die Hinweise liegen nicht mehr über der dritten Waffenreihe. Nichts davon betrifft das Netz |
| 0.32.4 | **Umlaute**: Was im Spiel, in den Menüs und in `KONTO.html` zu lesen ist, schreibt Ä, Ö und Ü statt der Umschriften AE, OE und UE (143 Texte im Spiel, rund 75 in der Kontoseite). Bewusst nicht angefasst: Wörter, in denen AE/OE/UE keine Umlaute darstellen (FEUER, NEUE, STEUERUNG, DAUER ...), Schlüssel und Namen, die gespeichert oder verglichen werden, Meldungen des Servers, Ausgaben im Terminal und SS in Grossbuchstaben (GROSS ist dort richtig) |
| 0.32.3 | **Einstellungen vollständig**: Reiter VIDEO, AUDIO, GRAFIK, STEUERUNG (die Tastenbelegung ist jetzt ein Reiter derselben Tafel, Q/E blättern) und **BARRIEREFREIHEIT**. Dort: die Blendgranate WIE VOM WERFER, NUR WEISS oder NUR SCHWARZ (nur bei dir, ohne fremdes Bild), das Bildwackeln und, experimentell und aus, **BLICK VORAUS**: die Bildmitte ist ein unsichtbarer Punkt 110 Pixel vor der Waffe. Was es noch nicht gibt (Musik, VSync, Helligkeit, Partikel, Licht, Wetter, Textursatz, Farbenblind, Untertitel, Schriftgrösse), steht grau mit NICHT VERFÜGBAR da und ist nicht anklickbar - Musik und Partikel hatten vorher Regler ohne Wirkung. Die Vignette hängt jetzt wirklich an ihrem Schalter. Die Tastenbelegung überlappte sich mit ihrem Hinweiskasten |
| 0.32.2 | **Rundentafel für Neue**: zuerst die einfache Ansicht (Spielart, Karte, Dauer, Ausrüstung), alles andere unter ERWEITERT - die Wahl merkt sich das Spiel. Ist dort etwas verstellt, sagt die einfache Ansicht es. Eine **Standardrunde** (TEAM, STAUBTAL, 10 Minuten, jeder hat alles) ist in jeder frischen Lobby vorgeplant; der Knopf STANDARDRUNDE stellt sie wieder her |
| 0.32.1 | **Pausenmenü nach Helldivers 2**: eine Spalte links, die Einträge klappen nacheinander auf, rechts eine Tafel mit dieser und der nächsten Runde und was der gewählte Eintrag tut - im Gefecht und im Einzelspieler. **Mit der Maus** bedienbar (Rechtsklick = zurück); solange es offen ist, geht keine Eingabe ans Spiel, auch das Zielen nicht, und der Klick auf WEITER löst keinen Schuss mehr aus. Statt der Regelzeilen gibt es NÄCHSTE RUNDE EINSTELLEN (die Rundentafel), dazu EINSTELLUNGEN |
| 0.32.0 | **Von Lobby zu Lobby**: LAN-GAST und LAN-GASTGEBER sind weg. `MEHRSPIELER` (oder *MEHRSPIELER* im Hauptmenü) führt ohne Fragen in die eigene Lobby; Lobbys im selben Netz finden sich von selbst (UDP-Suche auf Port 50504, `lan.py`), beitreten per Klick. Wer eine fremde Runde verlässt, abgewiesen wird oder den Gastgeber verliert, landet in seiner eigenen Lobby (`sitzung.py`). **Blendgranate**: ganz nah wirkt sie immer voll, auch weggedreht; ihre Reichweite ist viel kleiner, und hinter einer Wand bekommt man nichts mehr ab (exakte Sichtlinie statt Halbkachel-Schritten). **Zielpuppen** zeigen je Treffer eine Zahl und lassen sich nicht mehr schieben. **Waffenbalance**: das MG schiebt den Schützen nicht mehr (Regel *MG-RÜCKSTOSS SCHIEBT* für die alte Bewegungstechnik), reicht 1000 statt 1450; der Repetierer reicht 560 statt 430; der Schrot-Stoss gilt je Schuss statt je Kugel. Grosses Eszett in der Pixelschrift. Unter Windows nimmt ein zweites Spiel nicht mehr denselben Port; `SPIELTEST.bat` fand unter Windows Python nicht (`>/dev/null` statt `>nul`) |
| 0.31.4 | **Zombie-Arme, endgültig unscheinbar**: kurz wie beim Bewaffneten (bis c + 8), nur leicht zur Mitte, und etwas heller als der Kopfrand. Der Rand des Kopfes lag früher unter der Waffe; ohne sie wuchs er mit gleichfarbigen Armen zu einem dunklen Klotz zusammen |
| 0.31.3 | **Zombie-Arme ruhiger**: Läufer, Brecher und Speier strecken die Arme jetzt parallel nach vorn, etwas länger und leicht ungleich - ohne die Klauenfinger und Fäuste aus 0.31.1, die in 28 Pixeln unruhig wirkten. `_figur` hat dafür `bewaffnet=False` |
| 0.31.2 | **Absturz unter Python 3.8** (gemeldet beim Gastgeber, Python 3.8.8): stand auf dem Server ein neuerer Profilstand - etwa nachdem der ADMIN das Profil geändert hatte -, führte das Spiel beide mit `dict | dict` zusammen, und das gibt es erst ab Python 3.9. Jetzt mit `{**a, **b}`. Der Zweig war nie getestet; jetzt schon, und alle Testsuiten laufen auch unter Python 3.8 mit pygame-ce 2.5.2 |
| 0.31.1 | **Plateaus sind Felsblöcke**: auf STAUBTAL hing ein Plateau, von unten mit eingeblendeter oberer Ebene, versetzt und blass neben seinem Felssockel, dazwischen Boden wie Luft. Die obere Ebene wird vergrössert gezeichnet (sie ist näher am Auge) und war über dem Fels zu 79 Prozent durchsichtig. Jetzt ist der Deckel deckend, und zwischen ihm und dem Sockel steht eine Felswand aus Gesteinsbändern, mit derselben Perspektive gerechnet wie die Ebenen; was vom Auge abgewandt ist, liegt unter dem Deckel. Gilt für jede Etage, die auf Wand steht, also auch in der Arena. Was über Spielfläche liegt, blendet weiter aus. **Zombies tragen keine Gewehre mehr**: Läufer und Speier greifen mit Klauen, der Brecher mit Fäusten - sie hatten den Waffenstummel der Spielerfigur geerbt |
| 0.31.0 | **Mehr Statistik**: wen man wie oft erledigt hat (nach Konto, also auch nach einer Umbenennung derselbe), Schüsse und Treffer getrennt nach PVP und PVE, Treffer auf Spieler und auf Zombies, Zombie- und Bossabschüsse (im Mehrspieler bisher gar nicht gezählt), Abschüsse je Waffe (bisher nie gezählt). **Abgebrochene Runden** - Fenster zu, Verbindung weg, der Gastgeber beendet - werden trotzdem gebucht, aber als `abgebrochen` getrennt von den regulären, damit Abschüsse je Runde stimmen; der Gastgeber schickt dafür alle 2 s jedem Gast seinen Zwischenstand. **Jede Runde trägt die Version**, nach der sich die Statistik filtern lässt. Die Kontoseite rechnet ÜBERSICHT und WERTE jetzt aus den Runden (bis 0.30 las sie die Einstellungen im Profil und zeigte Nullen), mit Filtern für Version, Art und Abbrüche, und einem Reiter ERLEDIGT. **ADMIN-Konto**: Anmeldung auf der Kontoseite als `admin` (erst `123`, sofort zu ändern), sieht alle Profile und die Statistik aller, bearbeitet Loadouts und Kosmetik anderer, ändert Namen und Kennwörter, löscht Konten; nach Fehlversuchen gesperrt (1, 5, 15, 30 Minuten, dann doppelt), alles im Server. SQL in `docs/KONTO.md` 5.7 und 5.8, geprüft gegen ein lokales PostgreSQL (`tests/test_admin_sql.py`). Dazu: Granaten, Molotows, Blendgranaten und Raketen sind beim Gast im Flug wieder zu sehen; **Dash mit drei Ladungen**, je 2,7 s. Neue Netzmeldungen, darum neue Version |
| 0.30.0 | **Sichtweite mit Nebel**: im Gefecht stellt das Mausrad ein, wie viel Welt ins Bild passt (0,75 bis 2). Alles ausserhalb des normalen Bildes liegt im Nebel - Gelände gedämpft, aber keine Gegner, Mitspieler oder Granaten, sie werden dort gar nicht gezeichnet. Die Ebenenansicht liegt im Gefecht jetzt auf Strg + Mausrad und Bild hoch/runter. **Blendgranate**: weit weg oder weggedreht kein Weiss mehr, nur eine weisse Explosion mit Glitzer und Druckring, ohne Splitter und Brandfleck. **Kosmetikbild** füllt jetzt den ganzen Schirm; in der Kontoseite lässt es sich auf dem Weiss verschieben und in der Grösse einstellen (die Lage steht im PNG). **Minikarte** oben links, mit den Zombies in PVE. **Gegner fallen**, wenn ein Rückstoss sie über eine Kante schiebt - selbst laufen sie nie hinunter. Behoben: die Munitionsanzeige flackerte in der Lobby bei jedem Schuss; in KONTO.html sprang eine gewählte Waffe im Loadout sofort zurück |
| 0.29.0 | **Minikarte** oben rechts, ein Versuch: der Grundriss der eigenen Ebene, man selbst mit Blickrichtung, die eigenen Leute, der Bildausschnitt und in HÜGEL der Kreis - Gegner nicht, sonst wäre es ein Wandhack (`dustfront/minikarte.py`). **Anmeldung im Kliniknetz, zweiter Anlauf**: nach 0.28.1 kam ZERTIFIKAT UNGÜLTIG. Unter Windows fragt das Spiel jetzt, wenn Python ablehnt, Windows selbst - wie Edge und Chrome (`dustfront/windows_tls.py`); jeder Fehler dabei heisst nein. Die Anmeldetafel zeigt Grund und Aussteller, auch ohne Eingabeaufforderung. **Blendgranate** jetzt ganz weiss und deckend, solange sie voll wirkt; erst beim Abklingen scheint die Welt durch. **Unendlich Munition in der Lobby.** **MG deutlich schwächer**: 17 statt 25 je Schuss, Salve zu drei statt vier (51 statt 100 auf einen Klick - vorher mehr als ein Scharfschuss), Dauerfeuer langsamer, unter dem Sturmgewehr |
| 0.28.1 | **Anmeldung scheiterte am Zertifikat** (gemeldet aus einem Kliniknetz: `CERTIFICATE_VERIFY_FAILED`, während Firefox die Seite öffnete). Die Prüfung bleibt an; stattdessen liegen die üblichen Wurzelzertifikate dem Spiel bei, die strenge Prüfung von Python 3.13 ist zurückgenommen, und eine `zertifikate.pem` im Benutzerordner wird mitgeladen - für Netze, die HTTPS mitlesen. Die Meldung sagt jetzt ZERTIFIKAT UNBEKANNT und verweist auf [`docs/KONTO.md`](docs/KONTO.md), Abschnitt 9; der Selbsttest nennt, wer das Zertifikat ausgestellt hat. Runde Klammern erscheinen nicht mehr als Fragezeichen |
| 0.28.0 | **Spielerkosmetik, ein erster Versuch**: ein eigener Ton und ein eigenes Bild für die Blendgranate. Gemacht in der Kontoseite (Reiter KOSMETIK: MP3 zuschneiden, Bass, lauter, mit Knall und Pfeifen aus dem Spiel mischen; Bild ausschneiden und filtern, mit Vorschau in Spielgrösse), abgelegt im Konto (neue Tabelle, `docs/KONTO.md` 5.6), in der Lobby an alle verteilt. Der Gastgeber startet mit oder ohne Kosmetik - mit erst, wenn alle alles haben. Wer wirft, klingt nach seinem Ton, und im Weiss steht sein Bild. Der Ton dauert 1 bis 4 Sekunden und wird immer leiser; das prüft das Spiel bei jedem Paket selbst. Neue Netzmeldungen, darum neue Version. Neuer Browsertest `tests/kontoseite_browser.py` |
| 0.27.1 | **Nur noch gleiche Versionen spielen zusammen.** Ein Gast mit einer anderen Version als der Gastgeber wird abgewiesen und bekommt eine Tafel FALSCHE VERSION mit beiden Nummern und wer aktualisieren muss; umgekehrt verlässt ein Gast einen älteren Gastgeber. Gäste von vor 0.27.1 schicken keine Version und werden ebenfalls abgewiesen, mit "VERSION 0.27.1 NÖTIG". Anlass war die **Treppe beim Gast**: ein einmaliger Druck auf E führte zu hoch, runter, hoch, wenn das Loslassen verloren ging. Die Treppe hängt jetzt am Druck statt am Halten, beim Fokusverlust werden alle Tasten losgelassen. Wichtig: wer am Netzcode etwas ändert, zählt ab jetzt die Version hoch - sonst greift die Prüfung nicht |
| 0.27.0 | Neunzehn Punkte auf einmal, alles in [`docs/MEHRSPIELER.md`](docs/MEHRSPIELER.md), Abschnitt 12b. **Lobby**: wer aufmacht, landet zuerst auf einem Platz mit Arena (PVP), Schiessstand (Puppen, die den Schaden zeigen) und Gehege (Zombies); der Gastgeber stellt die Runden im Spiel ein (P) statt im Terminal, auf Wunsch als **Rundenplan** mit mehreren Runden, Schleife und Kopieren. **Regeln an einer Stelle** (`regeln.py`), neu: Schwierigkeit und Bosse an/aus für alles mit Wellen, ein Loadout für alle, Haltezeit und Verfall beim Hügel, gespielte Runden mit Matchpoint bei Versus. **Neue Anzeige** mit festen Orten und Modi (grosse Hotbar mit Loadout, kleine ohne; Vorrat nur bei knapper Munition; Bossbalken). **Dash** statt Sprint, alles etwas langsamer (Treffer auf weite Distanz 13 -> 23 Prozent). **Am Boden**: nicht mehr schiebbar, Mitspieler können ziehen (G), Rufen mit E, Randpfeile; Versus endet, sobald niemand mehr aufhelfen kann. **Ebenen**: obere über Spielfläche ausgeblendet (Q, als Kontovorliebe), Granaten behalten beim Fall ihren Schwung, Gegner gehen über Treppen und Rampen (`wege.py`). Medkit in der Hand beim Anlegen, Mutter und Brandstifter neu gezeichnet. Dabei gefunden: alle sieben Rampen auf STAUBTAL führten seit 0.23 ins Loch, der Gast sah weder seine Gesamtmunition noch sein Loadout in der Hotbar, Klänge des Gastgebers kamen nie an, Tastendrücke fielen bei voller Leitung weg |
| 0.26.0 | Die Wellen ausgebaut, und dabei zwei Fehler gefunden, die eine Runde stillstehen liessen. **Wo Gegner herkommen** war eine Zeile: eine gewürfelte Stelle irgendwo auf der Karte. Auf STAUBTAL gemessen hiess das 1477 Pixel im Mittel - zwanzig Sekunden Fussmarsch, bevor überhaupt etwas passierte -, und vier von sechs standen auf einem Plateau, auf das nur Rampen führen. Jetzt wird die Stelle gesucht: im Ring um einen Spieler, zwischen 260 und 620 Pixeln, möglichst ausser Sicht, fast immer auf seiner Ebene (jetzt 446 Pixel, sechs Sekunden). Dazu Marken in der Karte - `Z` ist eine Spawnstelle, so wie `A B C` Kreise sind: 31 auf STAUBTAL am Fuss der Plateaus und an den Buden, 21 auf der Testkarte, und keine im offenen Sand. Der zweite Fehler fiel erst beim Nachmessen auf: ein Läufer stand 120 Sekunden an einer Plateauwand, auf **derselben** Ebene wie die Spieler - und weil eine Welle erst endet, wenn alle liegen, wurde in 300 Sekunden Welle 2 nicht fertig. Wer sieben Sekunden nicht näher kommt, wird jetzt umgesetzt; danach fünf Wellen statt zwei. **Drei neue Gegner**, jeder mit einer anderen Frage: RENNER (138 px/s gegen 132 beim Spieler - Stehenbleiben ist keine Stellung mehr), SPEIER (hält 150 bis 230 Pixel Abstand und spuckt, will gar nicht heran) und BLÄHER (platzt beim Sterben - Zusammenstehen wird teuer). **Drei Bosse**, jede fünfte Welle, reihum: KOLOSS mit einem Stampfer, der auch hinter Deckung trifft (zwingt weg von ihm), MUTTER, die laufend Renner ruft (zwingt zu ihr hin), BRANDSTIFTER, der Feuer dorthin wirft, wo man gleich sein wird (zwingt in Bewegung). Jede Fähigkeit wird angekündigt - ein Ring in der Grösse der Wirkung, ein Wort, ein Ton -, denn ohne Vorwarnung ist ein Boss keine Frage, sondern eine Steuer. **Wellen** kommen in Schüben statt auf einmal, höchstens 22 zugleich, und bringen höchstens eine neue Gegnerart je Welle; keine fällt mit einer Bosswelle zusammen. Nebenbei: das Feuer eines Gegners verschont Gegner - gemessen tötete ein Bläher sonst alle fünf Läufer um sich herum, und dann spielt man den Trick statt des Spiels; der Molotow eines Spielers brennt weiter alles. Gegner tragen im Netz jetzt eine Kennung und ruckeln dadurch nicht mehr beim Gast (Stillstand 2,2 statt rund 50 Prozent), und der **Gastgeber** zeichnet endlich auch Lebensbalken - bisher tat das nur der Gast |
| 0.25.0 | **KONTO.html** - die Kontoseite zum Doppelklicken. Anmelden mit demselben Konto wie im Spiel, dann: jeder einzelne Zähler mit seinem Namen in der Datenbank daneben, jede gespielte Runde einzeln, Schüsse und Treffer je Waffe mit dem Symbol aus dem Spiel, die drei Loadouts ändern und tragen, Anzeigename und Kennwort. Dazu ein Knopf, der **alles** als JSON herunterlädt - wer wissen will, was über ihn gespeichert ist, soll es anklicken können statt erfragen zu müssen. Was die Seite **nicht** kann, mit Absicht: Zahlen ändern (geschrieben werden nur Anzeigename und Loadouts - selbst setzbare Werte wären keine Statistik mehr), Konten löschen (dafür bräuchte es den geheimen Schlüssel, und der darf in keiner herunterladbaren Datei stehen) und fremde Zeilen sehen (das entscheidet der Zeilenschutz auf dem Server, nicht die Seite). Sie wird **erzeugt**, nicht getippt: `werkzeug_kontoseite.py` schiebt Waffen, Wertnamen, Loadout-Regeln, Farben, Bilder und die Pixelschrift des Spiels an einer einzigen Stelle in `kontoseite_vorlage.html`, damit nichts zweimal gepflegt werden muss - und ein Test prüft, dass die eingecheckte Datei noch zu `config.py` passt. Alles in einer Datei, weil eine Seite unter `file://` keine Nachbardateien laden darf; Bilder gehen als data-URI mit. Ein neuer Reiter ist ein Eintrag in `SEITEN`. Gefahren und angesehen wurde sie im Browser gegen den echten Server, nicht nur gelesen - dabei fielen die Spielarten auf, die als `[object Object]` dastanden |
| 0.24.0 | Kosmetik, **vorgezeichnet und nicht eingebaut**. `python -m dustfront --kosmetik` schreibt fünf Bilder nach `kosmetik_vorschau/`: das laufende Band einer Kiste nach dem Vorbild von CS, das Ergebnis, die Maske zum Wählen von Figur, Waffen, Wurfwaffen, Klang und Musikkit, und eine zweite Siegtafel - je drei je Mannschaft in ihren Farben, darunter eine Bühne mit Siegerpodest, auf der die drei Besten ihre Animation machen und das Musikstück des MVP läuft. Jedes Bild trägt die Zeile `VORSCHAU - NOCH NICHT EINGEBAUT`, und das ist wörtlich zu nehmen: kein Spielmodul importiert `kosmetik.py`, `K.SKIN_WAHL` ist leer, und ein Test prüft beides. Zwei Dinge daran stehen wirklich im Code und wurden dabei geprüft - die 38 **Rollen** in `K.SKIN_ROLLEN`, hinter denen jeder Bild- und Klangname steht statt fest im Quelltext, und die fünf **Stufen** in `K.SELTENHEIT`; die Prozente auf dem Kistenbild sind nicht gemalt, sie kommen aus dieser Tabelle. Begründung, Aufbau und der ehrliche Überschlag, was ein Einbau kosten würde - Besitz und Übertragung sind die Arbeit, die Kistenanimation ist der kleinste Teil daran -, stehen in `docs/KOSMETIK.md` |
| 0.23.0 | **STAUBTAL**, die erste Karte aus einer Datei: 120 mal 80 Kacheln, also 3840 mal 2560 Pixel, und zu drei Vierteln offener Sand. Die obere Ebene ist kein Gangnetz, sondern drei Plateaus - und unter jedem steht Fels, man kommt nicht darunter, nur über eine der sieben Rampen hinauf. Dazu ein eigener Kachelsatz: Sand mit Windriffeln statt Blechplatten, Fels statt Wand, Fasser statt Frachtkästen. Drei Kreise, die nicht gleich sind - einer im offenen Sand mit einem Ring aus Fassern als Wahrzeichen, einer in einer Halle, einer auf dem grössten Plateau -, und weil drei Kreise zugleich aus einer grossen Karte drei kleine machen würden, **wandert** der Kreis von einem zum nächsten. Karten sind jetzt Textdateien in `karten/` mit Kopf und Ebenenblöcken; Grossbuchstaben darin sind Marken, also steht in der Karte selbst, wo die Kreise liegen. Wählbar im Gastgebermenü und mit `--karte` |
| 0.22.0 | Vier neue Waffen. **Molotow**: brennender Boden, kein Sprengschaden, genau auf einer Ebene - sie tötet niemanden im Wurf, sie nimmt einen Ort weg. **Blendgranate**: kein Schaden, aber eine Sekunde, und sie unterscheidet keine Mannschaften; wie stark sie trifft, rechnet jeder Rechner selbst aus der Lage des Blitzes, also kann nichts auseinanderlaufen. Bild und Klang hängen dabei an einer **Rolle** statt an einem Dateinamen - die Vorbereitung für Skins. **MG**: die schwerste Waffe im Spiel, Lauftempo auf 28 %, 56 Grad Drehung je Sekunde, dafür von 7,5 auf 0,9 Grad Streuung beim Halten; zwei Betriebsarten auf einer eigenen Taste, Dauerfeuer mit Minigun-Anlauf (45 Schuss beim Halten gegen 8 beim Antippen) und Salve zu vier Schuss fast gleichzeitig. **Raketenwerfer**: vom Gastgeber einzuschalten, liegt einmal auf der Karte, wer ihn trägt trägt sonst nichts ausser dem Brecheisen auf F, Eigenschaden ja und Mannschaftsschaden nein; mit Zielerfassung über die rechte Maustaste - ein Kreis zieht sich zu und rastet ein, die Rakete lenkt dann mit höchstens 120 Grad je Sekunde und kommt um keine Ecke. Nach unten wird nur über einem Loch erfasst, und die Rakete wechselt dort im Flug die Ebene; ohne Erfassung fliegt sie darüber hinweg. Wer erfasst wird, sieht es - und sieht es anders, sobald geschossen wurde |
| 0.21.0 | Was man spürt, statt es abzulesen. **Befinden**: ein roter Rand, der sich mit sinkendem Leben färbt, bei einem Treffer aufschlägt und unter 38 % stehenbleibt und pulst - mit einem Herzschlag im Ohr, in drei Klassen statt stufenlos, weil man eine Beschleunigung nicht merkt und drei Zustände sehr wohl. Dazu wird alles andere **wirklich dumpf**: jeder Klang bekommt eine tiefpassgefilterte Fassung (echt gefiltert, nicht nur leiser - ohne numpy, mit `array`), und zwischen klar und dumpf wird überblendet statt umgeschaltet. Gebaut wird nur, was schon zu hören war, einer je Bild: 5 ms im Mittel statt 521 ms für alles auf einmal. Das **Medkit** ist der Gegenschlag: ein kalter Blitz, dann ist die Welt eine Sekunde lang sehr klar und sehr kalt (Kontrast über `2*in - g`, Drehpunkt bei 44 statt 128, weil die Welt hier gemessen bei Helligkeit 36 liegt und sonst schwarz würde), und danach drei Sekunden Ruhe. **Munitionsanzeige**: rechts nur noch das Magazin, in der Hotbar der Vorrat bei der Waffe, zu der er gehört, und der Platz der gewählten Waffe sieht anders aus, wenn ihr Magazin leer ist. **Siegtafel** nach dem Vorbild von CS und Valorant: Mannschaften links und rechts in ihren Farben, je Zeile Platz, Name, das Zeichen der meistbenutzten Waffe, Abschüsse, Tode, das Verhältnis der Runde und der am öftesten Erledigte |
| 0.20.1 | Die Masken dazu: KONTO mit Name und Kennwort - das erste Bedienelement im Spiel, in das getippt wird - und AUSRÜSTUNG mit Satz, zwei Waffen und einer Wurfwaffe, beide aus Pause und Gefechtsmenü erreichbar. Gefragt wird jeweils genau einmal: wer ohne Konto spielen will, wird nicht wieder gefragt, und wer sich ein Loadout zusammengestellt hat, auch nicht. Ein geändertes Loadout gilt ab dem nächsten Leben, nicht sofort - sonst wäre es ein kostenloser Waffenwechsel mitten im Gefecht. Dafür neu: eine Szene kann `weiterlaufen` setzen und rechnet dann weiter, während ein Menü über ihr liegt. Genau eine Art Szene braucht das - eine, die an einer Leitung hängt: ein LAN-Gefecht, das stillsteht, während jemand sein Loadout ändert, wird nach acht Sekunden als stumm hinausgeworfen |
| 0.20.0 | Konten, Statistik und Loadouts. Alle harmlosen Spielwerte laufen mit - Abschüsse, Schaden, Schüsse und Treffer je Waffe, gelaufene Strecke, Zeit im Kreis, beste Abschussfolge, und zwanzig weitere, alle in `WERTE` an einer Stelle. Als Ablage **Supabase**, aus vier Gründen in `docs/KONTO.md` begründet; der wichtigste: es spricht nur HTTPS und JSON, also reicht die Standardbibliothek, und sein öffentlicher Schlüssel darf im Quelltext stehen - damit geht die Anmeldung auf einem frisch heruntergeladenen Spiel sofort. Ohne eingetragenen Server läuft alles lokal weiter, mit scrypt-gehashten Kennwörtern und `--konto neu` im Terminal für LAN-Runden ohne Internet. Gegen auseinanderlaufende Zahlen drei Regeln: der Gastgeber vergibt die Partiekennung und rechnet die Werte, ein eindeutiger Index lässt dieselbe Runde genau einmal zu, und was gespielt wurde, liegt sofort im Journal auf der Platte und wird erst nach Bestätigung abgehakt - ein Netzaussetzer nach dem Schreiben kann damit weder etwas verlieren noch verdoppeln, nachgestellt in `tests/test_konto.py`. Loadouts: drei Sätze aus zwei Waffen und einer Wurfwaffe, im Profil und damit auf jedem Rechner, mit `--loadouts` als Regel der Runde |
| 0.19.3 | Zwei gemeldete Fehler, beide gemessen statt geraten. **Das Bild des Gastgebers zitterte ohne Pause**, das der Gäste gar nicht: `Welt.ruckeln` war eine Meldung ohne Absender und ohne Ort, und weil der Gastgeber die Welt aller Spieler rechnet, lief jeder Schuss der ganzen Runde auf seiner Kamera zusammen - 2,09 Pixel in 100 % der Bilder gegen 0,00 beim Gast. Jetzt entscheidet der Zuschauer: andere Ebene oder zu weit weg ruckelt gar nicht, zwischen zwei Schlägen liegt eine Sperre, und der eigene Gewehrschuss reisst nichts mehr. Der Regler im Menü wirkt endlich und gehört zum Konto. **Granaten waren bei Gästen unsichtbar** und schienen zu springen: ein Gast bekam von einer Explosion nichts (0 Partikel, kein Ton, kein Brandfleck) und zeichnete fliegende Dinge stur an die letzte Meldung - 80 % Stillstand, Sprünge bis 7 Pixel. Wirkungen gehen jetzt als eigene Meldung an alle und werden mit demselben Code nachgespielt, fliegende Dinge tragen eine Kennung und werden zwischen zwei Meldungen weitergezeichnet (2 % Stillstand, höchstens 1,4 Pixel). Dazu die Leitung: `sendall` auf einer nicht-blockierenden Steckdose zerriss Nachrichten, jetzt wird gepuffert und ein Rückstand gekürzt |
| 0.19.2 | Mannschaftsfarben, Brecheisen auf F und fünf gemeldete Fehler |
| 0.19.1 | Knappe Munition war keine: jeder Wiedereinstieg füllte alle Magazine am Vorrat vorbei, der Vorrat sank nie, und darum liess sich auch keine Munitionskiste aufheben. Wiedereinstieg zahlt jetzt aus dem Vorrat, die Vorräte sind halbiert, und der Vorrat steht je Waffe in der Hotbar |
| 0.19.0 | Runden über das Internet: der Gastgeber lässt den Router den Port per UPnP selbst freigeben, mit Kennwort und ehrlicher Anleitung, falls es nicht klappt. Rauch neu gezeichnet - glattes Dichtefeld statt gewürfelter Klötze, Helligkeit nach Dicke, Licht von oben links. Treppen sperren nach einem Wechsel 1.5 Sekunden |
| 0.18.0 | Pausenmenü im Gefecht, mit Regeln, Mannschaftseinteilung und Rundenstart für den Gastgeber; Rauch komplett neu als deckende Blockwand, die auch Namen verbirgt; Unverwundbarkeit nach einem Treffer entfernt, Schutz gibt es nur noch beim Einstieg; Sturz mit Ring, Staub und Ton; Rückmeldung beim Aufsammeln; am Boden liegt man wirklich; wer aufhilft, steht still; Waffenwechsel ohne Verzögerung; Schwung für das Brecheisen; neun neue Treppen; nach oben ist nur noch eine Ebene sichtbar; die verschobene Ansicht kommt von selbst zurück |

## Anpassen

Alle Stellschrauben stehen oben in der jeweiligen Datei.

* **Spielname**: `SPIEL_TITEL` in `rustfront_menu.py`, `TEXTE["name"]` in
  `rustfront_splash.py`.
* **Version und Phase**: `VERSION` und `PHASE` in `rustfront_menu.py`.
  `dustfront/config.py` liest die Zeile von dort aus, statt das Menü zu
  importieren - das Spiel soll auch ohne Menü starten.
* **Waffenwerte**: `WAFFEN` in `dustfront/config.py`. Schaden, Takt, Magazin,
  Streuung, alles an einer Stelle. Wer eine siebte Waffe will, trägt sie dort
  ein, hängt ihren Namen an `HOTBAR` und zeichnet ein Symbol
  `waffe_<name>` in `art.py`. Sonst ist nichts zu tun.
* **Höhen der Ebenen**: `EBENEN_HOEHE` in `config.py`, in Welt-Pixeln.
  Der Abstand zwischen zwei Zahlen ist der, den man beim Herunterschauen
  sieht und beim Herunterfallen spürt.
* **Vorgaben für Einstellungen und Tasten**: `VORGABE` und `TASTEN_VORGABE`
  in `dustfront/einstellungen.py`.
* **Texturen und Klänge ersetzen**: eine Datei `assets/<name>.png` oder
  `assets/sfx/<name>/<aufnahme>.mp3` hinlegen, und sie tritt an die Stelle der im Code
  gezeichneten Fassung. Es ist kein Code zu ändern. Namen, Masse und die
  beiden Werkzeuge dazu stehen oben unter
  [Texturen und Klänge](#texturen-und-klänge).
* **Dauer des Intros**: `PHASEN` in `rustfront_splash.py`. Jede Karte hat drei
  Abschnitte (Aufbau, Standbild, Abblende) mit jeweils der echten Dauer in
  Sekunden. `TEMPO` skaliert alles auf einmal, 1.3 bringt die Sequenz von rund
  36 auf etwa 28 Sekunden.
* **Einzelne Karten abschalten**: `KARTEN_AN`.
* **Namen, Sprüche und Untertitel**: `TEXTE`.
* **Farbschema**: `SCHEMA`, möglich sind `aurum`, `glacies` und `ignis`.

## Technik

**Platzhalter und Assets.** Pixel-Schrift, Splash-Grafik und fehlende
Spielgrafik werden im Code erzeugt. Vorhandene Bilder und Klänge unter
`assets/` beziehungsweise `assets/sfx/` ersetzen die passenden
Platzhalter; eigene Dateien können dort ergänzt werden.

**Auflösung.** Das Menü rendert auf 480x270, die Splash-Sequenz auf 320x180.
Beides wird auf das Fenster hochskaliert, wahlweise füllend oder nur in
ganzen Pixelvielfachen. Jedes Fensterverhältnis funktioniert, von 320x180 bis
Ultrawide.

**Splash-Engine.** Portierung einer eigenen Web-Fassung: gleiche Paletten,
gleiches 8x8-Bayer-Dithering statt Alphamischung, gleicher Zufallsgenerator
(mulberry32), damit Sterne, Druckkorn und Strahlen exakt dort sitzen wie im
Original. 1,4 bis 4,8 ms pro Bild.

**Ton.** Jede Splash-Karte hat eine eigene Erzeugungsart, damit die Marken
nicht nach demselben Baukasten klingen: modale Synthese für Glocke und Metall
(Siegel), Holzstäbe wie ein Marimba (Kaltwerk), Zeilenpfeifen mit Netzbrummen
(Phosphor), Holzpresse und körniges Papierrascheln (Papiermond), eine
laufende Druckmaschine (Tafel). Berechnet wird im Hintergrund, damit der Start
nicht hängt.

## Musik im Hauptmenü

Noch nicht eingebaut. Wenn es soweit ist, gehört der Titel hier in eine
Tabelle mit Quelle und Lizenz, sonst weiss später niemand mehr, woher er kam.

| Datei | Titel | Urheber | Lizenz | Quelle |
| --- | --- | --- | --- | --- |
| noch leer | | | | |

### Worauf achten

"Royalty-free" heisst nur, dass keine Gebühr pro Abspielen fällig wird, es
heisst nicht "ohne Bedingungen". Drei Fälle:

* **CC0** ist der einfachste: gemeinfrei, keine Namensnennung nötig, auch bei
  einem verkauften Spiel. Trotzdem nennen ist höflich.
* **CC-BY** verlangt eine feste Credit-Zeile im Spiel. Vergisst man sie, ist
  die Nutzung nicht gedeckt.
* **NonCommercial (NC)** meiden, sobald ihr auch nur theoretisch Geld nehmen
  wollt. Das fällt später auf die Füße.

### Brauchbare Quellen

| Quelle | Lizenz | Anmerkung |
| --- | --- | --- |
| kenney.nl | CC0 | Saubere, einheitliche Packs, keine Namensnennung nötig |
| opengameart.org (Filter auf CC0) | CC0 und andere | Direkt für Spiele gemacht, viele nahtlose Loops |
| pixabay.com/music | Pixabay-Lizenz | Kommerziell nutzbar, keine Namensnennung |
| incompetech.com (Kevin MacLeod) | CC-BY 4.0 | Über 2000 Stücke, feste Credit-Zeile nötig |
| freemusicarchive.org | gemischt | Pro Titel prüfen |

Gesucht ist für das Menü ein langsamer, dunkler Industrial- oder
Ambient-Loop ohne Gesang, zwei bis vier Minuten, nahtlos schleifbar. Auf
OpenGameArt hilft die Stichwortsuche nach "dark ambient loop" oder
"industrial".

### Einbauen

Datei nach `assets/music/` legen, als OGG (kleiner als WAV, pygame kann es
direkt). Dann im Menü:

```python
pygame.mixer.music.load("assets/music/menue.ogg")
pygame.mixer.music.set_volume(app.settings.vol_ambient / 100.0)
pygame.mixer.music.play(-1)          # -1 = endlos wiederholen
```

Der vorhandene Regler REAKTORBRUMM in den Optionen steuert dann auch die
Musik, dafür muss `Audio.apply_volumes` die Lautstärke mitsetzen.

## Einbinden ins Spiel

```python
from rustfront_menu import run_menu

ergebnis = run_menu()
# {"action": "new_game" | "continue" | "quit",
#  "region": ..., "difficulty": ..., "callsign": ...}
```

Seit 0.12.0 ist das eingebaut: `spiel_scene()` in `rustfront_menu.py` ruft
`dustfront.main.aus_menue()` auf und holt danach den Anzeigemodus des
Menüs zurück. Fehlt das Paket `dustfront`, bleibt es bei der
Platzhalter-Szene - das Menü läuft weiterhin auch allein.
