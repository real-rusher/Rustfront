# DUSTFRONT

Ein Top-Down-Spiel auf dem Kontinent Veld. Du steuerst einen modularen
Wandler, baust ihn aus Schrott weiter aus und bewegst dich zwischen drei
Fraktionen: der Kolonne, dem Chor und den Freien Werften. Beide Spielmodi
teilen dieselbe 90-Grad-Draufsicht, du wechselst mit Tab zwischen "an Bord"
und "Fahr-Modus".

Geschrieben in Python mit pygame-ce. Schulprojekt, in Arbeit.

**Aktuell: Version 0.32.18, PRE-ALPHA.** Was das heisst, steht weiter unten
unter [Versionsnummern](#versionsnummern).

## Mitwirkende

Nicolas, Nikolaus, Marlon, Alfred.

## Stand

| Teil | Zustand |
| --- | --- |
| Splash-Sequenz | fertig, fuenf Karten mit eigenem Ton |
| Hauptmenue | fertig, inklusive Optionen und Spielstand |
| Spielkern | steht: feste Zeitschritte, drei Ebenen, Kollision, Wellen |
| Waffen | sieben Stueck, alle im Test nachgewiesen, jede in der Hand zu erkennen |
| Hoehenebenen | drei, eine Etage nach oben sichtbar, viele Treppen, Sturz mit Steuerung in der Luft |
| Sturz | ohne Ruck: die Figur bleibt stehen, die Welt waechst unter ihr heran |
| Inventar und Hotbar | fertig, Plaetze per Maus oder Tastatur umsortierbar |
| Pause und Einstellungen | fertig: Anzeige, Ton, Steuerung, Mitwirkende |
| Grafik-Einstellungen | Vignette, Wackeln und Partikel stehen; Licht, Wetter und Textursaetze sind vorgemerkt |
| Texturen und Klaenge | noch alle im Code erzeugt; eine Datei in `assets/` ersetzt jedes Stueck, ohne Codeaenderung |
| Ersetzbar sind | alle 36 Bilder, Kacheln und Figuren ebenso wie Schatten, Blut, Brandfleck und Vignette |

Der Spielkern gilt als tragfaehig: was jetzt noch dazukommt, haengt sich als
weitere Szene, weiteres Wesen oder weitere Zeile in `config.py` an, statt
Bestehendes umzubauen.

## Wohin es geht

**[`docs/KARTE.md`](docs/KARTE.md) ist der Weltenplan.** Dort steht
vollstaendig, wie die Karte am Ende aufgebaut sein soll: die drei
Massstaebe (Kontinent, Ort, Wandler), wie der Wandler in einen Ort
gestempelt wird, wie die Sektoren und die vorrueckende Front funktionieren,
was Fortschritt womit koppelt, und in welcher Reihenfolge das gebaut wird
(Meilensteine M1 bis M9, von 0.12.0 bis 1.0.0).

Gebaut ist davon noch nichts. Wer weitermacht, nimmt sich den naechsten
Meilenstein aus Abschnitt 11 des Plans und liest vorher Abschnitt 3 ganz -
dort steht die eine technische Entscheidung, an der alles andere haengt.

## Starten

**Ohne Kommandozeile, einfach doppelklicken:**

| Was | Windows | macOS, Linux |
| --- | --- | --- |
| Das ganze Spiel, mit Menue und Intro | `DUSTFRONT.bat` | `DUSTFRONT.command` |
| Direkt ins Spiel, zum Ausprobieren | `SPIELTEST.bat` | `SPIELTEST.command` |
| Mehrspieler: direkt in die eigene Lobby | `MEHRSPIELER.bat` | `MEHRSPIELER.command` |

Die Datei sucht sich Python selbst, installiert pygame-ce beim ersten Mal
nach und startet dann. Geht etwas schief, bleibt das Fenster offen und sagt
warum, statt kommentarlos zu verschwinden.

**`SPIELTEST`** springt ohne Menue und ohne Intro direkt in eine Runde und
schreibt die Steuerung ins Fenster. Zum schnellen Ausprobieren gedacht.
**`DUSTFRONT`** ist der normale Weg: Intro, Hauptmenue, *NEUE KAMPAGNE*,
und von dort geht es ins Spiel. Mit *AUFGEBEN* im Pausemenue kommt man
zurueck ins Hauptmenue.

Unter macOS beim allerersten Mal Rechtsklick auf die Datei und dann
*Oeffnen* waehlen - danach reicht der Doppelklick.

**Verknuepfung auf den Desktop** (Windows): Rechtsklick auf
`DUSTFRONT.bat`, dann *Senden an* und *Desktop (Verknuepfung erstellen)*.
Wer das Intro ueberspringen will, haengt in den Eigenschaften der
Verknuepfung hinter das Ziel ein Leerzeichen und `--nosplash`; die
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

Nur das Spiel, ohne Menue und ohne Intro:

```
python -m dustfront
```

Vorlagen zum Uebermalen herausschreiben, und nachsehen, was gerade aus
Dateien kommt:

```
python -m dustfront --vorlagen
python -m dustfront --assets
```

Testlauf ohne Fenster, legt Bilder zum Anschauen ab:

```
python tests/test_spiel.py
python tests/test_menues.py
```

Beide bauen ihre Welt mit einem festen Seed auf und laufen deshalb jedes
Mal gleich ab. Das Spiel selbst wuerfelt weiter frei - den Seed gibt nur
der Test mit (`Spiel(app, seed=...)`). Eine Pruefung, die mal gruen und mal
rot ist, sagt nichts, und man gewoehnt sich an, sie zu uebersehen.

Gebraucht werden Python 3.8 bis 3.14 und pygame-ce (getestet mit 2.5.2 und
2.5.8). Die Tests laufen unter 3.8 und 3.11; `tests/test_konto.py` prueft
ausserdem, dass aller Quelltext gueltiges Python 3.8 ist.
Sonst nichts: Schrift, Grafik und Ton entstehen zur Laufzeit, es liegen keine
fertigen Bilder oder Klaenge im Repo. Wie man sie durch eigene ersetzt, steht
unter [Texturen und Klaenge](#texturen-und-klaenge).

## Steuerung im Menue

| Taste | Wirkung |
| --- | --- |
| Pfeile oder W/S | Auswahl |
| Links / Rechts | Wert aendern |
| Enter oder Leertaste | Bestaetigen |
| Esc | Zurueck, im Hauptmenue Beenden-Abfrage |
| F11 | Vollbild |
| Maus | Hovern, Klicken, Regler ziehen, Rad zum Blaettern |

Waehrend des Intros springt jede Taste zur naechsten Karte, Esc ueberspringt
die ganze Sequenz.

## Steuerung im Spiel

Alles bis auf die Maustasten und Esc laesst sich im Menue unter STEUERUNG
umlegen. Eine Taste gehoert immer nur einer Aktion: legt man sie neu, wird sie
der alten weggenommen.

| Taste | Wirkung |
| --- | --- |
| W A S D | Laufen, auch waehrend eines Sturzes (dort mit 55 Prozent Tempo) |
| Shift | Dash (drei Ladungen, laden nacheinander nach, je 2,7 s) |
| Maus links | Schiessen oder schlagen |
| Maus rechts | Einzielen (bei der Scharfschuetzenwaffe) |
| Mausrad | Im Gefecht: Sichtweite (weiter weg oder naeher; ausserhalb des normalen Bildes Nebel). Im Einzelspiel: Ansicht eine Ebene hoch oder runter |
| Strg + Mausrad, Bild hoch / Bild runter | Ansicht eine Ebene hoch oder runter (Gefecht) |
| 1 bis 9 | Waffe waehlen |
| R | Nachladen |
| V | Feuerart wechseln (beim MG: Dauerfeuer oder Salve) |
| H | Medkit |
| E | Treppe benutzen, aufhelfen; am Boden: rufen |
| G | Gefallenen Mitspieler ziehen (Gefecht) |
| Q | Obere Ebenen ein- oder ausblenden (Gefecht) |
| P | Runden einstellen, in der Lobby (Gefecht) |
| Tab | Inventar |
| T | Ziellinie an oder aus |
| Z | Ziellinie ueber den Zeiger hinaus verlaengern |
| Esc | Pausenmenue (im LAN-Gefecht laeuft die Runde darunter weiter) |
| F11 | Vollbild |
| F3 | Debug-Anzeige |

### Die sieben Waffen

| Waffe | Art | Eigenheit |
| --- | --- | --- |
| Repetierer | Schuss | Der Allrounder. Genau, mittleres Tempo. |
| Sturmgewehr | Schuss | Rund 700 Schuss in der Minute, streut bei Dauerfeuer auf. |
| Schrot | Schuss | Sieben Kugeln auf einmal. Enger gebuendelt und weiter reichend als frueher, aber nah immer noch deutlich haerter. |
| Scharfschuetze | Schuss | Reicht weiter, als das Bild breit ist: ein Schuss endet an einer Wand, nicht an seiner Reichweite. Aus der Hueffte unbrauchbar. Rechte Maustaste halten zieht den Streifen in anderthalb Sekunden bis auf Ziellinienbreite zusammen. Gemessen: auf 300 Pixel trifft sie aus der Hueffte 8 Prozent der Schuesse, eingezielt 100. |
| Granate | Wurf | Fliegt genau so weit, wie man zielt, zwischen 60 und 260 Pixeln. Rollt sie ueber eine Kante, faellt sie auf die Ebene darunter und zuendet erst dort. |
| Rauchgranate | Wurf | Macht keinen Schaden, sondern eine Wand aus Rauch, und fliegt dafuer kuerzer als die Sprenggranate. Vierzehn Sekunden lang ist darin **nichts** zu sehen - keine Figur und kein Name, auch nicht von der Ebene darueber. |
| Brecheisen | Nahkampf | Zwei Treffer toeten. Schlaegt in einem Kegel von 80 Grad und stoesst zurueck. Braucht keine Munition. |

Die Munition haengt am Namen der Waffe, nicht an ihrem Platz. Umsortieren im
Inventar kostet also keine Patrone.

## Gefecht im LAN und ueber das Internet

> **Dieser Zweig ist abgeschlossen und wird nicht mehr weiterentwickelt.**
> Der Mehrspieler war ein Test. Er ist fertiggestellt und liegt auf dem
> Zweig `multiplayer-test`; der Hauptzweig geht ohne ihn weiter, dem
> Weltenplan in [`docs/KARTE.md`](docs/KARTE.md) nach.

Mehrere Leute auf einer Karte, in sechs Spielarten. Nach der Runde steht
die Liste, und sie wandert in eine Bestenliste im Benutzerordner.

**Alles im Einzelnen steht in
[`docs/MEHRSPIELER.md`](docs/MEHRSPIELER.md):** Aufbau, Protokoll Feld fuer
Feld, jede Zahl mit Begruendung, jeder Fehler, der beim Bauen aufgetreten
ist, und eine Bauanleitung in zwoelf Schritten fuer den Tag, an dem der
Mehrspieler zurueckkommen soll.

| Spielart | Was passiert | Wie es endet |
| --- | --- | --- |
| **PVP** | Jeder gegen jeden, keine Gegner | nach Zeit oder Abschuessen, der Gastgeber waehlt |
| **PVE** | Alle zusammen gegen Wellen | wenn alle am Boden liegen |
| **PVPVE** | Wellen, und dabei jeder gegen jeden | wie PVP |
| **TEAM** | Zwei Mannschaften, Abschuesse zaehlen fuer die Mannschaft | nach Zeit oder 30 Teamabschuessen |
| **VERSUS** | Zwei Mannschaften, ein Leben je Runde, Aufhelfen durch die eigenen Leute | nach drei Rundensiegen |
| **HUEGEL** | Zwei Mannschaften, ein sichtbarer Kreis in der Kartenmitte | wenn eine Mannschaft den Kreis vollgeladen hat |

Alles aus dem Einzelspieler ist dabei: die sieben Waffen, drei Ebenen mit
Treppen und Stuerzen, Ziellinie, Streukegel der Scharfschuetzenwaffe,
Nahkampfbogen. Medkits liegen alle paar Sekunden neu aus, jeder kann sie
nehmen.

### Koop: am Boden und wieder auf

In **PVE** stirbt niemand sofort. Wer faellt, liegt am Boden, kann noch
kriechen und haelt 45 Sekunden durch. Ein Mitspieler stellt sich daneben
und haelt **E** - nach drei Sekunden steht man wieder, mit angeschlagenem
Leben. Zwei Helfer sind doppelt so schnell.

**Nach jeder Welle steht ohnehin wieder jeder.** Das ist der Ausgleich
dafuer, dass eine Runde sonst mit dem ersten Fehler kippt. Vorbei ist es
erst, wenn niemand mehr steht.

In PVP, PVPVE und TEAM gibt es kein Aufhelfen: dort steigt man nach drei
Sekunden neu ein.

### Mannschaften: TEAM, VERSUS, HUEGEL

Drei Spielarten mit zwei Mannschaften, **ROT** und **BLAU**. Wer dazukommt,
geht in die kleinere - nicht abwechselnd, denn wer geht, hinterliesse sonst
eine Luecke, die nie wieder gefuellt wird. Die eigene Mannschaft traegt die
helle Farbe, die fremde die dunkle, und den Nebenmann kann man nicht
treffen. Ein kurzer Strich ueber dem Namen zeigt, welche Figur die eigene
ist.

**TEAM** ist Deathmatch: jeder Abschuss zaehlt zweimal, fuer den Schuetzen
und fuer die Mannschaft.

**VERSUS** gibt jedem **ein Leben je Runde**. Wer faellt, liegt am Boden -
und nur die **eigenen** Leute koennen aufhelfen, dafuer brauchen sie vier
Sekunden statt drei. Wer die zwanzig Sekunden am Boden ausreizt, ist fuer
die Runde raus. Eine Runde ist zu Ende, wenn eine Mannschaft niemanden mehr
auf den Beinen hat; drei Rundensiege entscheiden. Solange eine Mannschaft
leer ist, faengt keine Runde an.

**HUEGEL** ist die Hot Zone: ein **sichtbarer Kreis in der Mitte der
Karte**, unten auf Ebene 0. Wer dort die **Mehrheit** hat, laedt fuer seine
Mannschaft; bei Gleichstand laedt **niemand**, und der Stand verfaellt
langsam. Genau das macht den Kreis zu dem Ort, an dem man sich trifft,
statt ihn abwechselnd leerzuraeumen. Der Kreis wird in den Boden gezeichnet
und nicht darueber: die Figuren stehen sichtbar darauf, und von einer
hoeheren Ebene aus sieht man ihn unten liegen, klein und im Dunst.

### Gegner, die mit mehreren Spielern zurechtkommen

Der Gegner aus dem Einzelspieler laeuft immer auf den einen Spieler zu,
den es dort gibt. Zu viert waere das ein Rudel, das geschlossen auf
denselben Mann zulaeuft, waehrend die anderen drei in Ruhe zielen.

Im Gefecht waehlt jeder Gegner selbst, nach drei Regeln: **Naehe zaehlt**,
**Gedraenge schreckt ab** (jeder Gegner, der schon an einem Ziel haengt,
macht es unattraktiver), und **wer entschieden hat, bleibt ein paar
Sekunden dabei** - sonst zappelt er zwischen zwei gleich weit entfernten
Spielern. Wer am Boden liegt, zieht kaum noch Gegner an, damit sie die
Helfer angreifen statt um einen Gefallenen herumzustehen.

Die Wellen wachsen mit der Spielerzahl. Dieselbe Welle waere zu viert
sonst ein Spaziergang.

### Knappe Munition

Der Gastgeber kann Munition begrenzen. Dann hat jede Waffe einen Vorrat
ausserhalb des Magazins, der unter der Munitionsanzeige steht, und
Nachladen kostet daraus. Ist der Vorrat leer, laeuft gar kein Nachladen
mehr an. **Munitionskisten** erscheinen alle 18 Sekunden neu und fuellen
alles ein Stueck auf.

### So spielt man es

1. Jeder startet **`MEHRSPIELER`** (oder im Hauptmenue *MEHRSPIELER*).
   Es wird nichts gefragt: jeder landet in seiner **eigenen Lobby**. Oben
   links steht ihre Adresse (etwa `192.168.1.7:50505`).
2. Wer zu jemand anderem will: **Esc -> ANDERER LOBBY BEITRETEN**. Dort
   stehen alle Lobbys im selben Netz von selbst in einer Liste - anklicken
   genuegt. Eine Adresse von Hand geht darunter, ebenso ein Kennwort und,
   ohne Konto, der eigene Name. Wer eine fremde Lobby oder Runde verlaesst
   (Esc -> *GEFECHT VERLASSEN*), aus ihr abgewiesen wird oder dessen
   Gastgeber aufhoert, landet wieder in **seiner eigenen** Lobby.
3. In der Lobby: links die Arena (PVP), in der Mitte der Schiessstand,
   rechts das Gehege mit Zombies. Auf dem Platz dazwischen tut niemandem
   etwas weh. Der Gastgeber stellt mit **P** die naechste Runde ein -
   Spielart, Karte, Schwierigkeit, Ausruestung und alles andere - und
   startet sie. Wer mehrere Runden hintereinander will, klappt den
   Rundenplan auf. Nach der Runde geht es weiter oder zurueck in die
   Lobby. **Die Regeln bestimmt allein der Gastgeber**; die anderen sehen
   die Tafel, koennen aber nichts aendern.
   Hat jemand **Spielerkosmetik** (siehe unten), startet der Gastgeber
   **mit** oder **ohne** - mit erst, wenn sie bei allen angekommen ist.
4. Fertig. Esc oeffnet das Menue; *SPIEL BEENDEN* macht zu (vom
   Hauptmenue aus gestartet: zurueck ins Hauptmenue).

### Spielerkosmetik: der eigene Knall

Ein eigener Ton und ein eigenes Bild fuer die Blendgranate. In der
Kontoseite (`KONTO.html`, Reiter **KOSMETIK**) eine MP3 laden und
zuschneiden, Bass und Lautstaerke hochdrehen, auf Wunsch den Knall und das
Pfeifen aus dem Spiel dazumischen; ein Bild laden und mit Filtern
bearbeiten. Wer dann eine Blendgranate wirft, klingt nach seinem Ton, und
im Weiss steht sein Bild - bei allen, wenn der Gastgeber mit Kosmetik
startet. Der Ton dauert 1 bis 4 Sekunden und **wird immer leiser**; das
prueft das Spiel selbst, bei jedem Paket. Auf dem Server braucht es dafuer
einmal die Tabelle aus [`docs/KONTO.md`](docs/KONTO.md), Abschnitt 5.6.
Wie es verteilt wird: [`docs/MEHRSPIELER.md`](docs/MEHRSPIELER.md), 12c.

Fuer eine LAN-Runde muessen alle im selben Netz sein - gleiches WLAN oder
gleicher Switch. Eine Firewall fragt beim ersten Mal, ob Python ins Netz
darf. Beim Gastgeber muss das erlaubt sein (TCP 50505, fuer die Lobbysuche
UDP 50504), sonst findet ihn niemand; wer nur beitritt, braucht es nicht.
Welche Ports das Spiel seit wann benutzt: [`docs/MEHRSPIELER.md`](docs/MEHRSPIELER.md),
12g, "Was im Netz wann dazukam".

### Ueber das Internet

Seit 0.32 gibt es dafuer keine eigene Startdatei mehr; das Internet geht
ueber die Kommandozeile: `python -m dustfront --host --online --passwort
GEHEIM`. Das Spiel versucht dann, den Port im Router selbst freizugeben
(UPnP), und sagt die Adresse an, die die anderen in der Lobbysuche unter
*ADRESSE* eintippen.

Drei Dinge dazu, ehrlich:

* **Es haengt am Router.** Viele Heimrouter koennen UPnP und haben es an,
  dann geht es von allein. Manche koennen es nicht, und hinter einem
  Mobilfunkanschluss oder in einem Wohnheim hilft es gar nichts. Klappt es
  nicht, schreibt das Spiel genau hin, was von Hand einzutragen ist:
  Protokoll TCP, Port, Zieladresse.
* **Es wird ruckeliger als im LAN.** Der Gastgeber rechnet alles; ein Gast
  sieht seine eigene Figur erst nach einem Hin- und Rueckweg. Im LAN sind
  das zwei Millisekunden, ueber das Internet eher dreissig bis hundert.
  Zielen folgt trotzdem sofort, das rechnet jeder bei sich.
* **Ein offener Port ist ein offener Port.** Wer die Adresse kennt, kann
  mitspielen. Darum gehoert `--passwort` dazu. Ohne eines
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

`--kosmetik` schreibt die Vorschaubilder fuer Kisten, Skins und die
zweite Siegtafel nach `kosmetik_vorschau/`. **Eingebaut ist davon nichts**
- es sind Bilder, ueber die sich entscheiden laesst, ob es so aussehen
soll. Warum, und was ein Einbau kosten wuerde, steht in
[`docs/KOSMETIK.md`](docs/KOSMETIK.md).

Was auf der Kommandozeile steht, wird die erste geplante Runde in der
Lobby; `--sofort` ueberspringt die Lobby und faengt gleich an.
`--team rot|blau|auto` waehlt die Mannschaft, `--runden N` die Zahl der
gespielten Runden in VERSUS. `--online` versucht, den Port im Router freizugeben,
`--passwort WORT` setzt ein Kennwort - beides zusammen ist der Weg ueber
das Internet.
`--loadouts` laesst jeden sein eigenes Loadout tragen - zwei Waffen und
eine Wurfwaffe statt aller sechs Plaetze; ohne den Schalter hat jeder
alles. Konten, Statistik und Loadouts stehen in
[`docs/KONTO.md`](docs/KONTO.md).
`--modus` ist `pvp`, `pve`, `pvpve`, `team`, `versus` oder `huegel`;
`--ende` ist `zeit` oder `abschuesse`, `--wert` die Sekunden
beziehungsweise Abschuesse. Bei `versus` und `huegel` ist die Zeit nur die
Notbremse - beide enden von selbst.

### Wie es aufgebaut ist

**Ein Rechner rechnet, alle anderen schauen zu.** Der Gastgeber simuliert
die ganze Welt. Gaeste schicken nur, was sie druecken, und bekommen
zurueck, wo alles steht. Damit gibt es keinen Streit darueber, wer
getroffen hat, und niemand kann durch eine geaenderte Datei schummeln.
Der Preis ist ein Hin- und Rueckweg Verzoegerung, im LAN unter zwei
Millisekunden.

**Keine Threads.** Die Verbindungen stehen auf nicht-blockierend, einmal
je Bild wird nachgesehen, was angekommen ist. Eine zweite Schleife waere
nur eine Quelle fuer Fehler, die man nicht nachstellen kann.

**Jeder Spieler hat eine eigene Fraktion.** Die Trefferabfrage
ueberspringt alles, was zur selben Fraktion gehoert - alle Spieler tragen
sonst "mensch" und koennten sich nie treffen. So bleibt der Spielkern
unveraendert.

Nicht uebers Netz gehen Partikel, Huelsen und Blutflecken. Die entstehen
bei jedem selbst und sind reine Kosmetik.

| Datei | Inhalt |
| --- | --- |
| `netz.py` | Verbindungen, Protokoll aus JSON-Zeilen, Gastgeber und Gast |
| `mehrspieler.py` | Die Gefechtsszene, Punkte, Wiedereinstieg, Rundenende |
| `bestenliste.py` | Abschuesse ueber alle Runden, im Benutzerordner |

### Was der Test noch nicht kann

Ehrlich aufgezaehlt, damit niemand danach sucht.

**Keine Vorhersage beim Gast.** Die eigene Figur laeuft erst los, wenn die
Antwort des Gastgebers da ist - ein Hin- und Rueckweg. Ueber Kabel ist das
unsichtbar, ueber WLAN spuerbar. Das ist der einzige Punkt, der sich nicht
durch eine Kleinigkeit beheben laesst: dafuer muesste der Gast seine eigene
Figur mitrechnen und beim Eintreffen der Wahrheit zurechtruecken.

Ausserdem: kein Wiederverbinden nach einem Abbruch, keine Kartenwahl,
keine Teams. Das Gefecht laeuft immer auf derselben Testkarte.

## Wie sich das Spiel anfuehlen soll

Drei Regeln, die ueber einzelnen Funktionen stehen. Wer etwas Neues
einbaut, haelt sich daran, sonst faellt es auf.

**Keine Handlung sperrt eine andere.** Man darf jederzeit die Waffe
wechseln, nachladen, ein Medkit ansetzen, die Ebene wechseln oder die
Ansicht verschieben - auch mitten in einer anderen Handlung und auch im
Sturz. Was dabei noch nicht fertig war, wird verworfen, nicht abgewartet.
Ein Waffenwechsel bricht also das Nachladen ab, statt darauf zu warten. Im
Code sammelt `Spieler.abbrechen()` diese Abbrueche an einer Stelle; eine
neue Handlung traegt sich dort ein.

**Nichts springt.** Jede Bewegung, die man sieht, entsteht Bild fuer Bild.
Besonders der Sturz: die Figur bleibt im Bild stehen und die Welt waechst
unter ihr heran, statt dass sie an ihren spaeteren Landeplatz gesetzt wird.
Steht unten etwas im Weg, rutscht sie waehrend des Fluges zur Seite - aber
nur so lange, bis sie freien Grund unter sich hat, danach gehoert die
Bewegung wieder dem Spieler. `tests/test_spiel.py` misst das nach: nicht
den Zustand, sondern die Bildposition von Schritt zu Schritt.

**Man bleibt am Steuer.** Auch im Sturz laesst sich die Figur lenken, mit
55 Prozent des normalen Tempos (`luftsteuerung` in `config.py`). Gemessen
sind das rund 25 Pixel quer auf einen Sturz ueber zwei Etagen - genug, um
ein Loch noch zu treffen oder daneben zu landen.

**Man sieht, was man tut.** Die Figur traegt die Waffe, die gewaehlt ist,
sichtbar in der Hand. Zielhilfen gehoeren zu der Ebene, auf der man steht,
und verschwinden, sobald man mit dem Mausrad woanders hinschaut.

## Dateien

Aussen liegt das Menue, innen das Spiel. Beides laeuft auch einzeln.

| Datei | Inhalt |
| --- | --- |
| `DUSTFRONT.bat` | Startdatei zum Doppelklicken, Windows |
| `DUSTFRONT.command` | Startdatei zum Doppelklicken, macOS und Linux |
| `SPIELTEST.bat` | Direkt ins Spiel, Windows |
| `SPIELTEST.command` | Direkt ins Spiel, macOS und Linux |
| `rustfront_menu.py` | Hauptmenue, Kaltstart, Optionen, Spielstand, Einstiegspunkt |
| `rustfront_splash.py` | Ablauf, Zeitdehnung und Klangsynthese der Splash-Sequenz |
| `splash_engine.py` | Zeichenwerk der Splash-Sequenz, portiert aus der Web-Fassung |

Das Spiel selbst liegt im Paket `dustfront/`:

| Datei | Inhalt |
| --- | --- |
| `config.py` | Alle Zahlen und Tabellen. Sonst steht nirgends eine freie Zahl. |
| `core.py` | Anwendung, Szenenstapel, feste Zeitschritte, Eingabe, Bildablage |
| `world.py` | Ebenen, Kacheln, Kollision, Sichtlinien, Treppen, Abgruende |
| `entities.py` | Spieler, Gegner, Geschosse, Granaten, Aufsammler |
| `render.py` | Kamera, Tiefenwirkung, Schatten, Ziellinie, HUD |
| `play.py` | Die Spielregel: Wellen, Tod, Neustart |
| `menues.py` | Pause, Einstellungen, Steuerung, Mitwirkende |
| `inventar.py` | Ausruestung, Waffenraster, Tasche, Hotbar |
| `ui.py` | Bedienelemente: Kaesten, Knoepfe, Reiter, Regler, Schalter |
| `einstellungen.py` | Einstellungen und Tastenbelegung, lesen und schreiben |
| `pfade.py` | Wo diese Dateien liegen, je nach Betriebssystem |
| `art.py`, `audio.py`, `font.py` | Grafik, Klang und Schrift, alles zur Laufzeit erzeugt |
| `vorlagen.py` | Die beiden Werkzeuge `--vorlagen` und `--assets` |
| `netz.py` | LAN-Verbindungen und Protokoll |
| `mehrspieler.py` | Das LAN-Gefecht |
| `lobby.py` | Die Lobby und der Rundenplan |
| `regeln.py` | Die Regeln eines Gefechts, an einer Stelle |
| `anzeige.py` | Die Anzeige im Gefecht |
| `minikarte.py` | Die Minikarte oben links |
| `windows_tls.py` | Unter Windows: Zertifikate von Windows pruefen lassen |
| `spielerkosmetik.py` | Eigener Ton und eigenes Bild fuer die Blendgranate: pruefen, verteilen, zeigen |
| `bestenliste.py` | Abschuesse ueber alle Runden |
| `konto.py` | Anmeldung, Profil, Loadouts, das Journal der Runden |
| `ablage.py` | Wo Konten und Zahlen liegen: Datei oder Server |

Und `karten/` daneben: jede Karte eine Textdatei, ein Zeichen eine
Kachel, die Ebenen hintereinander. `werkzeug_staubtal.py` erzeugt
STAUBTAL neu, falls man am Grundriss etwas aendern will - danach ist die
Datei ganz normaler Text und von Hand weiterzubearbeiten.

Daneben liegt `docs/`:

| Datei | Inhalt |
| --- | --- |
| `KARTE.md` | Der Weltenplan: Kontinent, Orte, Wandler, Front, Meilensteine |
| `MEHRSPIELER.md` | Der LAN-Mehrspieler vollstaendig: Aufbau, Protokoll, alle sechs Spielarten, jede Zahl, jeder aufgetretene Fehler, Bauanleitung zum Wiedereinbau |
| `KONTO.md` | Konto, Statistik und Loadouts: warum Supabase, warum die Zahlen nicht auseinanderlaufen koennen, und wie man es in zehn Minuten aufsetzt |
| `KOSMETIK.md` | Kisten, Skins, Musikkits und die zweite Siegtafel - fuenf Bilder, die Begruendung dazu, und der ehrliche Ueberschlag, was ein Einbau kosten wuerde. **Eingebaut ist davon nichts.** Die Spielerkosmetik der Blendgranate (0.28) ist etwas anderes - siehe oben |

### Wo die Einstellungen liegen

**Nicht im Spielordner.** Wer das Spiel neu herunterlaedt, den Ordner loescht
oder `git clean` laufen laesst, soll seine Tastenbelegung behalten. Deshalb
liegen `einstellungen.json` und `tasten.json` dort, wo das System seine
Benutzerdaten ablegt:

| System | Ordner |
| --- | --- |
| Windows | `%APPDATA%\\Dustfront`, also `C:\\Users\\<name>\\AppData\\Roaming\\Dustfront` |
| macOS | `~/Library/Application Support/Dustfront` |
| Linux | `$XDG_CONFIG_HOME/dustfront`, sonst `~/.config/dustfront` |

Der Pfad steht auch unten in den Einstellungen, man muss also nicht suchen.

**Tragbarer Betrieb.** Liegt eine Datei `portable.txt` neben dem Paket, wird
stattdessen der Unterordner `daten` im Spielordner benutzt. Praktisch fuer
einen USB-Stick oder einen Schulrechner, auf dem man nichts im Benutzerprofil
ablegen darf.

Tasten stehen als lesbare Namen in der Datei, also `"w"` und `"left shift"`,
nicht `119` und `1073742049`. Das kann man notfalls mit einem Texteditor
reparieren. Kaputte oder unbekannte Eintraege werden verworfen und durch die
Vorgabe ersetzt; eine beschaedigte Datei kostet hoechstens die eine
Einstellung, die kaputt ist, nie den Start.

Das alte Menue legt daneben weiter `rustfront_settings.json` und
`rustfront_save.json` im Spielordner ab. Beide stehen in der `.gitignore`.

## Texturen und Klaenge

Alles, was das Spiel zeigt und hoert, hat einen Namen. Zu jedem Namen sucht
es zuerst eine Datei und zeichnet oder rechnet nur dann selbst, wenn keine da
ist:

```
assets/<name>.png           Bild
assets/sfx/<klangname>/aufnahme.wav   Klang
```

**Eine hingelegte Datei ersetzt den Platzhalter, ohne dass eine Zeile Code
geaendert wird.** Kein Eintrag nachzutragen, keine Liste zu pflegen. Datei
hinlegen, Spiel starten, fertig. Bei Bildern gehen auch `.webp` und `.bmp`,
bei Klaengen `.ogg` und `.mp3`; gesucht wird in dieser Reihenfolge, die erste
gefundene gewinnt. Klangaufnahmen liegen in `assets/sfx/<klangname>/`; WAV,
OGG und MP3 sind erlaubt, und der Dateiname darin ist frei. Bisherige flache Dateien
wie `assets/sfx/medkit.wav` bleiben als Rueckfall unterstuetzt.

### Der Weg von der leeren Datei ins Spiel

```
python -m dustfront --vorlagen
```

schreibt jedes Bild, das das Spiel kennt, nach `assets_vorlage/` — in der
richtigen Groesse, unter dem richtigen Dateinamen, dazu eine
Uebersichtstafel `_uebersicht.png` mit allen Bildern nebeneinander.
Uebermalen, nach `assets/` kopieren, fertig. Umbenennen entfaellt.

```
python -m dustfront --assets
```

sagt umgekehrt zu jedem Namen, ob er gerade aus einer Datei oder aus dem Code
kommt, und nennt jede Datei, die sich nicht lesen liess. Damit prueft man,
ob eine neue Textur wirklich angenommen wurde.

### Groesse

Jedes Bild hat ein Sollmass. Wer genau darin malt, bekommt die Datei Pixel
fuer Pixel so ins Spiel, wie sie ist. Wer groesser malt, darf das: die Datei
wird beim Laden hart auf das Sollmass gerechnet, ohne Weichzeichnen. Ein
sauberes Vielfaches — doppelt, dreifach, vierfach — rechnet exakt herunter
und sieht am besten aus.

Wer dauerhaft ein anderes Mass will, aendert die Zahl in `BILD_MASS` in
`dustfront/config.py`. Das ist die eine Stelle dafuer, und ein Test wacht
darueber, dass Tabelle und gezeichnete Platzhalter sich decken.

| Name | Mass | Was es ist |
| --- | --- | --- |
| `leer` | 32x32 | Loch in der Ebene, man sieht hindurch |
| `boden`, `boden_2`, `boden_3`, `boden_4` | 32x32 | Bodenplatten, zufaellig abgewechselt |
| `gitter` | 32x32 | Gitterrost |
| `wand` | 32x32 | feste Wand, blockiert Sicht und Schuss |
| `kiste` | 32x32 | Frachtkasten, blockiert nur Bewegung |
| `treppe_hoch`, `treppe_runter` | 32x32 | Treppen, mit E zu benutzen |
| `luke` | 32x32 | Luke nach unten |
| `aufzug_tuer`, `aufzug_schacht` | 32x32 | Aufzug: Tuer unten im Fels, Schachtkopf oben; hineinlaufen genuegt |
| `spieler` | 28x28 | die eigene Figur ohne bestimmte Waffe |
| `spieler_repetierer` … `spieler_brecheisen` | 56x56 | die Figur mit der jeweiligen Waffe in der Hand |
| `gegner_laeufer` | 28x28 | Laeufer |
| `gegner_brecher` | 36x36 | Brecher, der schwere Gegner |
| `geschoss` | 8x4 | fliegende Kugel |
| `muendung` | 20x20 | Muendungsfeuer, wird additiv gemischt |
| `medkit` | 16x14 | Medkit am Boden |
| `granate` | 10x10 | fliegende Granate |
| `huelse` | 4x3 | ausgeworfene Patronenhuelse |
| `waffe_repetierer` … `waffe_brecheisen` | 26x11 | die sechs Symbole in Hotbar und Inventar |
| `schatten` | 48x24 | Fleck unter jedem Wesen |
| `blut` | 26x26 | bleibt liegen, wo eines gestorben ist |
| `brandfleck` | 156x156 | Russ, den eine Granate hinterlaesst |
| `wandschatten` | 39x39 | was eine feste Kachel auf den Boden wirft |
| `vignette` | 640x360 | Abdunkelung zum Bildrand |

Die letzten fuenf haben kein festes Mass im Spiel: sie richten sich nach dem,
was sie wirft — der Schatten nach dem Koerper, der Blutfleck nach dem Wesen,
der Brandfleck nach dem Wirkungskreis. Das Mass in der Tabelle ist ihr
**Basismass**, und das Spiel rechnet sie von dort auf die gebrauchte Groesse
um, hart und ohne Weichzeichnen. Wer sie ersetzt, malt also eine Form, keine
feste Groesse. Fuer welchen Wert das Basismass gilt, steht in `DEKAL` in
`config.py`.

Die Klangnamen stehen als `KLANG_NAMEN` in `config.py` und in
`assets/sfx/LIESMICH.md`, mit der Regel, wann welcher spielt.

### Worauf beim Malen zu achten ist

* **Kacheln** sind 32x32 und muessen randlos aneinanderpassen.
* **Figuren** sitzen mittig auf einer quadratischen Flaeche und schauen nach
  rechts, also auf 0 Grad. Das Spiel dreht sie von dort aus. Wer nach oben
  malt, dessen Figur laeuft seitwaerts.
* **Durchsichtigkeit** benutzen, wo nichts ist. Die Uebersichtstafel legt
  Durchsichtiges auf ein Schachbrett, damit man den Rand sieht.
* **Waffensymbole** sind winzig. Dort zaehlt nur die Silhouette: Laenge des
  Laufs, Dicke des Gehaeuses, was oben und unten heraussteht.

### Wenn etwas schiefgeht

Eine Datei, die sich nicht lesen laesst, kostet nichts: das Spiel nimmt den
Platzhalter und laeuft weiter. Den Grund zeigt `--assets`. Ein grelles Pink
im Spiel heisst dagegen, dass weder Datei noch Code diesen Namen kennen —
dann stimmt der Name nicht.

Dass ein Dauerfeuer nicht aus einer einzigen Kopie klingt, regeln
Nummern-Fassungen: `schuss_sturm_1.wav` bis `_8` daneben legen, und das
Spiel waehlt bei jedem Schuss zufaellig eine davon.

## Versionsnummern

Die Nummer steht an **genau einer Stelle**: `VERSION` und `PHASE` ganz oben in
`rustfront_menu.py`. Die Splash-Sequenz und die Fusszeile im Menue holen sie
sich von dort. Wer die Nummer aendert, aendert nur diese zwei Zeilen.

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

Ab 1.0.0 kommt eine vierte Frage dazu: MAJOR +1, wenn alte Spielstaende nicht
mehr laden oder das Spiel grundlegend anders funktioniert.

### Feste Regeln

* Die Nummer geht **nur hoch**, nie runter, und keine Nummer wird zweimal
  vergeben.
* Keine Ziffer ueberspringen: nach `0.4.0` kommt `0.5.0`, nicht `0.6.0`.
* Wird MINOR erhoeht, faellt PATCH auf 0 zurueck. Wird MAJOR erhoeht, fallen
  MINOR und PATCH auf 0.
* Im Zweifel PATCH. Zu vorsichtig zaehlen ist nie falsch.
* Die Nummer wird **vor** dem Push geaendert, und die Commit-Nachricht nennt
  sie. Dann sieht man in der Historie sofort, welcher Commit welche Version
  ist.
* Neue Version = neue Zeile in der Tabelle unten.

### Phasen

Die Phase haengt nur davon ab, wie weit das Spiel ist, nicht von der Nummer.

| Phase | Bedeutung |
| --- | --- |
| `PRE-ALPHA` | Einzelne Teile laufen, es gibt noch keine durchgehende Spielschleife. Hier stehen wir. |
| `ALPHA` | Man kann eine Runde von Anfang bis Ende spielen, Inhalte fehlen noch. |
| `BETA` | Alle Inhalte sind drin, es geht nur noch um Fehler und Balance. |
| `RELEASE` | Ab `1.0.0`. |

### Bisher

| Version | Was dazukam |
| --- | --- |
| 0.32.18 | **Neue Spielklaenge eingebaut**: MP3-Aufnahmen werden geladen und Schussserien zu einzelnen Schuessen zugeschnitten. Neu zu hoeren: Nachladen, Zu-Boden-Gehen, Rauchgranate, Brecheisen-Schwung und Treffer, Rundenstart sowie Match-Sieg oder -Niederlage. Das Mehrspieler-Protokoll teilt die neuen Klangereignisse und Trefferart mit; Gastgeber und Gast brauchen dieselbe Version. |
| 0.32.17 | **Aufnahmeordner fuer alle 24 Klaenge**: Lege WAV-, OGG- oder MP3-Dateien mit beliebigem Namen in `assets/sfx/<klangname>/`; mehrere Dateien pro Ordner dienen als zufaellige Fassungen. Bestehende flache Dateien bleiben als Rueckfall erhalten. Kein Netz- oder Kartenverhalten geaendert. |
| 0.32.16 | **Dash und Schussbild**: die drei Windlinien bauen sich nacheinander auf; das Muendungsfeuer sitzt vor der Laufspitze. Der Lichtkern bleibt erhalten. Rein visuell, keine Netz- oder Kartenaenderung. |
| 0.32.15 | **Dash und Medkit**: Der Dash zeichnet drei kleine, grauweisse Windlinien hinter der Figur. Am Medkit in der Hand wurden die losen weissen Pixel am Rand entfernt. Rein visuell, keine Netz- oder Kartenaenderung. |
| 0.32.14 | **Dash-Animation neu gestaltet**: sofort sichtbarer Impulsring und Richtungs-Chevron an der Figur, nahe teamfarbene Nachbilder und gebrochene Staubschlieren. Rein visuell, keine Netz- oder Kartenaenderung. |
| 0.32.13 | **Dash-Animation**: ein pixeliger Tuerkis- oder Teamfarben-Stoss mit zwei gefaerbten Nachbildern, gebrochenen Bewegungslinien, sichtbarem Absprung und kurzem Ausklang. Der Gast bekommt denselben Animationstakt vom Gastgeber; das Weltpaket hat dafuer ein neues Feld. Gastgeber und Gast muessen dieselbe Version nutzen. |
| 0.32.12 | **Gameplay-Randfehler behoben**: Medkits heilen weder Tote noch Spieler am Boden und werden bei Waffenwechsel abgebrochen; ein Sturz beendet den Dash. Geschosse mit Nulltempo schlagen sicher ein, Kartenraender gelten nicht als Loecher und Raketen wechseln dort nicht die Ebene. Lange Menue- und UI-Texte werden innerhalb ihrer Felder gekuerzt. Mehrspieler: gleiches Verhalten fuer Gastgeber und Gast, keine Protokollaenderung; Gastgeber und Gast muessen dieselbe Version nutzen. |
| 0.1.0 | Hauptmenue |
| 0.2.0 | Splash-Sequenz |
| 0.2.1 | Vollbild und Rufzeichen-Eingabe repariert |
| 0.3.0 | Projekt ins Repo, README |
| 0.4.0 | Klaenge auf materialbasierte Synthese umgestellt, zweiteiliger Spruch auf der letzten Karte, Versionsanzeige |
| 0.5.0 | Das Spiel selbst: Welt, Wesen, Darstellung, Wellen, feste Zeitschritte |
| 0.6.0 | Hoehenebenen mit echtem Abstand, Loecher zum Durchfallen und Durchschiessen, Sturz mit Steuerung in der Luft |
| 0.7.0 | Sechs Waffen, Medkits, Hotbar, Ziellinie; Einstellungen und Tastenbelegung im Benutzerordner |
| 0.8.0 | Pausenmenue, Einstellungen, umlegbare Steuerung, Abspann, Inventar |
| 0.9.0 | Texturen und Klaenge aus Dateien: `assets/` nimmt jede Aufloesung an, Vorlagen-Werkzeug, Bestandsliste |
| 0.10.0 | Schatten, Blut, Brandfleck, Wandschatten und Vignette ebenfalls ersetzbar; Blutfleck richtet sich nach der Groesse des Wesens |
| 0.11.0 | Sturz ohne Ruck, Waffe in der Hand sichtbar, durchgehend rote Ziellinie, keine Handlung sperrt mehr eine andere |
| 0.11.1 | Steuerung in der Luft im Test nachgewiesen und gegen das Abrutschen abgesichert; Testlaeufe mit festem Seed reproduzierbar |
| 0.11.2 | Startdateien zum Doppelklicken fuer Windows und macOS; Weltenplan in `docs/KARTE.md` |
| 0.12.0 | Das Hauptmenue startet das echte Spiel statt einer Platzhalter-Szene; Startdatei fuer den direkten Spieltest |
| 0.13.0 | LAN-Gefecht: mehrere Spieler auf einer Karte, keine Gegner, Namen, Punkte und eine Bestenliste im Benutzerordner |
| 0.13.1 | Im Gefecht gingen einzelne Tastendruecke verloren; dazu fehlten Zielhilfen, Mausrad, Medkits, Munitionsanzeige und sichtbare Granaten |
| 0.14.0 | Mehrspieler fertiggestellt: drei Spielarten, Aufhelfen, Wellen mit mehrspielertauglicher Gegner-KI, knappe Munition mit Nachschubkisten. Letzter Stand dieses Zweigs |
| 0.16.0 | Mannschaften im Gefecht: TEAM, VERSUS mit einem Leben je Runde und Aufhelfen durch die eigenen Leute, HUEGEL mit sichtbarem Kreis in der Kartenmitte. Alles in `docs/MEHRSPIELER.md` beschrieben. Nur auf `multiplayer-test`; 0.15.0 gehoert dem Hauptzweig ohne Mehrspieler |
| 0.17.0 | Rauchgranate als siebte Waffe; Granaten fallen ueber Kanten auf die Ebene darunter; Einstiegsschutz, Startmedkits und Medkit-Nachschub als Schalter beim Aufmachen. Dazu vier gemeldete Fehler behoben: kein Ton im Gefecht, Ziellinie des Gastes am Einstiegspunkt, Versetzung nach einem Sturztod, Granaten prallten an Loechern ab. Brecheisen toetet in zwei Treffern, Schrot reicht weiter und streut enger, Scharfschuetze weiter als das Bild breit ist |
| 0.32.11 | **Aufzug auf STAUBTAL (Versuch)**: die Westrampe der KANZEL (grosses Plateau) ist jetzt eine Tuer unten im Fels mit dem Schachtkopf genau darueber. Hineinlaufen genuegt, ohne Taste; man kommt eine Kachel weiter auf der anderen Ebene heraus, in die Richtung, in die man lief, und die Kamera geht den Schritt mit - die Figur bleibt im Bild stehen (gemessen hoechstens 3 px), nur die Umgebung blendet ueber. Zurueck genauso: oben in den Schacht laufen, unten vor der Tuer heraus. Gegner nehmen ihn, wenn er auf ihrem Weg liegt (gemessen: keine Umsetzungen, alle ausser den Speiern kommen an), aber nicht, wenn sie nur hineingedraengt werden; Bosse nie. Die anderen Plateaus haben weiter Rampen, zum Vergleichen. Netz: kein neuer Port und keine neue Nachricht, der Wechsel kommt wie jeder Ebenenwechsel ueber die gewohnte Meldung. Aber die Karte hat zwei neue Kachelarten: Gastgeber und Gast brauchen dieselbe Version (wird beim Beitreten geprueft) |
| 0.32.10 | **Ebenenwechsel ohne Aussetzer**: nach Treppe oder Luke war man bis jetzt eine halbe Sekunde unsichtbar (nur der Laser blieb), und die Helligkeit zog nach. Grund: die Ansicht glitt langsam zur neuen Hoehe, und solange galt die eigene Etage als "darueber" (ausgeblendet) oder "darunter" (abgedunkelt). Jetzt springt die Ansicht sofort, und das letzte Bild der alten Ebene blendet in 0,22 s aus. Stuerze sinken weiter mit der Figur. Netz: keine Aenderung, nur Darstellung beim eigenen Rechner |
| 0.32.9 | **Brecheisen-Schwung**: die Figur haelt beim Schlag jetzt wirklich das alte Brecheisen aus der Schnellleiste mit beiden Haenden, die Arme schwingen mit (9 Bilder ueber den Schwungbogen); die Waffe verschwindet fuer den Schwung ganz und das Eisen bleibt danach noch 0,14 s in der Hand, damit man es sieht. Die alte rostige Linie und der helle Block sind weg, nur eine schwache Punktspur der Spitze bleibt. Netz: keine Aenderung (das vorhandene Schlagfeld wird genutzt) |
| 0.32.8 | **Knall der Blendgranate**: deutlich leiser mit Abstand (bei 300 Pixeln rund zwei Drittel, ab 500 Pixeln knapp die Haelfte der gewoehnlichen Daempfung) und noch einmal halb so laut, wer wegschaut; ganz nah (2 Kacheln) voll; nie leiser als hoerbar. Gilt fuer den Standardknall und fuer den Ton aus der Spielerkosmetik. **Barrierefreiheit**: neue Zeile BLENDGRANATE TON (wie vom Werfer / nur Standard), getrennt vom Bild - das eine betrifft das Auge, das andere das Ohr |
| 0.32.7 | **Kamera ruhig**: Beim Zoomen wechselte das Seitenverhaeltnis der Zeichenflaeche in jedem Bild um Bruchteile (gerundete Breite und Hoehe passten nicht zueinander) - das Bild wackelte zur Seite und nach oben. Gezoomt wird jetzt in Stufen von 1/40, bei denen es genau 16:9 bleibt. Der kleine Vorlauf zur Maus richtet sich nach dem Abstand der Maus von der Bildmitte statt nach dem Weltpunkt unter ihr; der wanderte mit der Kamera mit, und das Bild zog sich nach. Die Kamera folgt straffer (15 statt 11) und schleicht den letzten halben Pixel nicht mehr aus. **BLICK VORAUS**: Vorgabe 70 statt 110 Pixel, unter Barrierefreiheit einstellbar von 40 bis 150 |
| 0.32.6 | **Zombies und Treppen**: Gegner wechselten die Ebene schon eine Kachel *vor* der Rampe (der Rest der naechsten Kachel wurde fuer "steht drauf" gehalten). Sie kamen oben schraeg neben der Rampe im Nichts an, steckten fest und wurden nach ein paar Sekunden umgesetzt - das war das "Verschwinden in Sicht". Jetzt wechseln sie nur auf der Rampe selbst und nur auf festen Boden; gemessen mit 15 gemischten Zombies auf STAUBTAL: vorher 7 bis 11 Umsetzungen in 90 s, jetzt keine. Und umgesetzt wird nur noch, wer seit 5 Sekunden in niemandes Bild war. Der zweite Zombie-Arm ist das Spiegelbild des ersten und kommt jetzt auch von der Seite |
| 0.32.5 | **Menues aufgeraeumt**: Ä, Ö und Ü haben in beiden Pixelschriften volle Buchstabenhoehe, die Punkte sitzen ueber der Zeile (vorher waren sie zwei Pixel kleiner). Die **Steuerung im Hauptmenue** zeigt die echte Belegung des Spiels statt der alten Entwurfstasten (Bauen, Fahr-Modus, Autopilot). Die **Optionen im Hauptmenue** teilen sich Vollbild, Pixelraster, Bildrate und Lautstaerken mit dem Spiel; CRT-Filter, Intro und Reaktorbrummen gibt es nur im Hauptmenue. Im **Inventar** passen alle neun Hotbar-Plaetze, und die Hinweise liegen nicht mehr ueber der dritten Waffenreihe. Nichts davon betrifft das Netz |
| 0.32.4 | **Umlaute**: Was im Spiel, in den Menues und in `KONTO.html` zu lesen ist, schreibt Ä, Ö und Ü statt AE, OE und UE (143 Texte im Spiel, rund 75 in der Kontoseite). Bewusst nicht angefasst: Woerter, in denen AE/OE/UE kein Umlaut ist (FEUER, NEUE, STEUERUNG, DAUER ...), Schluessel und Namen, die gespeichert oder verglichen werden, Meldungen des Servers, Ausgaben im Terminal, und SS in Grossbuchstaben (GROSS ist dort richtig) |
| 0.32.3 | **Einstellungen vollstaendig**: Reiter VIDEO, AUDIO, GRAFIK, STEUERUNG (die Tastenbelegung ist jetzt ein Reiter derselben Tafel, Q/E blaettern) und **BARRIEREFREIHEIT**. Dort: die Blendgranate WIE VOM WERFER, NUR WEISS oder NUR SCHWARZ (nur bei dir, ohne fremdes Bild), das Bildwackeln und, experimentell und aus, **BLICK VORAUS**: die Bildmitte ist ein unsichtbarer Punkt 110 Pixel vor der Waffe. Was es noch nicht gibt (Musik, VSync, Helligkeit, Partikel, Licht, Wetter, Textursatz, Farbenblind, Untertitel, Schriftgroesse), steht grau mit NICHT VERFUEGBAR da und ist nicht anklickbar - Musik und Partikel hatten vorher Regler ohne Wirkung. Die Vignette haengt jetzt wirklich an ihrem Schalter. Die Tastenbelegung ueberlappte sich mit ihrem Hinweiskasten |
| 0.32.2 | **Rundentafel fuer Neue**: zuerst die einfache Ansicht (Spielart, Karte, Dauer, Ausruestung), alles andere unter ERWEITERT - die Wahl merkt sich das Spiel. Ist dort etwas verstellt, sagt die einfache Ansicht es. Eine **Standardrunde** (TEAM, STAUBTAL, 10 Minuten, jeder hat alles) ist in jeder frischen Lobby vorgeplant; der Knopf STANDARDRUNDE stellt sie wieder her |
| 0.32.1 | **Pausenmenue nach Helldivers 2**: eine Spalte links, die Eintraege klappen nacheinander auf, rechts eine Tafel mit dieser und der naechsten Runde und was der gewaehlte Eintrag tut - im Gefecht und im Einzelspieler. **Mit der Maus** bedienbar (Rechtsklick = zurueck); solange es offen ist, geht keine Eingabe ans Spiel, auch das Zielen nicht, und der Klick auf WEITER loest keinen Schuss mehr aus. Statt der Regelzeilen gibt es NAECHSTE RUNDE EINSTELLEN (die Rundentafel), dazu EINSTELLUNGEN |
| 0.32.0 | **Von Lobby zu Lobby**: LAN-GAST und LAN-GASTGEBER sind weg. `MEHRSPIELER` (oder *MEHRSPIELER* im Hauptmenue) fuehrt ohne Fragen in die eigene Lobby; Lobbys im selben Netz finden sich von selbst (UDP-Suche auf Port 50504, `lan.py`), beitreten per Klick. Wer eine fremde Runde verlaesst, abgewiesen wird oder den Gastgeber verliert, landet in seiner eigenen Lobby (`sitzung.py`). **Blendgranate**: ganz nah wirkt sie immer voll, auch weggedreht; ihre Reichweite ist viel kleiner, und hinter einer Wand bekommt man nichts mehr ab (exakte Sichtlinie statt Halbkachel-Schritten). **Zielpuppen** zeigen je Treffer eine Zahl und lassen sich nicht mehr schieben. **Waffenbalance**: das MG schiebt den Schuetzen nicht mehr (Regel *MG-RUECKSTOSS SCHIEBT* fuer die alte Bewegungstechnik), reicht 1000 statt 1450; der Repetierer reicht 560 statt 430; der Schrot-Stoss gilt je Schuss statt je Kugel. Grosses Eszett in der Pixelschrift. Unter Windows nimmt ein zweites Spiel nicht mehr denselben Port; `SPIELTEST.bat` fand unter Windows Python nicht (`>/dev/null` statt `>nul`) |
| 0.31.4 | **Zombie-Arme, endgueltig unscheinbar**: kurz wie beim Bewaffneten (bis c + 8), nur leicht zur Mitte, und etwas heller als der Kopfrand. Der Rand des Kopfes lag frueher unter der Waffe; ohne sie wuchs er mit gleichfarbigen Armen zu einem dunklen Klotz zusammen |
| 0.31.3 | **Zombie-Arme ruhiger**: Laeufer, Brecher und Speier strecken die Arme jetzt parallel nach vorn, etwas laenger und leicht ungleich - ohne die Klauenfinger und Faeuste aus 0.31.1, die in 28 Pixeln unruhig wirkten. `_figur` hat dafuer `bewaffnet=False` |
| 0.31.2 | **Absturz unter Python 3.8** (gemeldet beim Gastgeber, Python 3.8.8): stand auf dem Server ein neuerer Profilstand - etwa nachdem der ADMIN das Profil geaendert hatte -, fuehrte das Spiel beide mit `dict | dict` zusammen, und das gibt es erst ab Python 3.9. Jetzt mit `{**a, **b}`. Der Zweig war nie getestet; jetzt schon, und alle Testsuiten laufen auch unter Python 3.8 mit pygame-ce 2.5.2 |
| 0.31.1 | **Plateaus sind Felsbloecke**: auf STAUBTAL hing ein Plateau, von unten mit eingeblendeter oberer Ebene, versetzt und blass neben seinem Felssockel, dazwischen Boden wie Luft. Die obere Ebene wird vergroessert gezeichnet (sie ist naeher am Auge) und war ueber dem Fels zu 79 Prozent durchsichtig. Jetzt ist der Deckel deckend, und zwischen ihm und dem Sockel steht eine Felswand aus Gesteinsbaendern, mit derselben Perspektive gerechnet wie die Ebenen; was vom Auge abgewandt ist, liegt unter dem Deckel. Gilt fuer jede Etage, die auf Wand steht, also auch in der Arena. Was ueber Spielflaeche liegt, blendet weiter aus. **Zombies tragen keine Gewehre mehr**: Laeufer und Speier greifen mit Klauen, der Brecher mit Faeusten - sie hatten den Waffenstummel der Spielerfigur geerbt |
| 0.31.0 | **Mehr Statistik**: wen man wie oft erledigt hat (nach Konto, also auch nach einer Umbenennung derselbe), Schuesse und Treffer getrennt nach PVP und PVE, Treffer auf Spieler und auf Zombies, Zombie- und Bossabschuesse (im Mehrspieler bisher gar nicht gezaehlt), Abschuesse je Waffe (bisher nie gezaehlt). **Abgebrochene Runden** - Fenster zu, Verbindung weg, der Gastgeber beendet - werden trotzdem gebucht, aber als `abgebrochen` getrennt von den regulaeren, damit Abschuesse je Runde stimmen; der Gastgeber schickt dafuer alle 2 s jedem Gast seinen Zwischenstand. **Jede Runde traegt die Version**, nach der sich die Statistik filtern laesst. Die Kontoseite rechnet UEBERSICHT und WERTE jetzt aus den Runden (bis 0.30 las sie die Einstellungen im Profil und zeigte Nullen), mit Filtern fuer Version, Art und Abbrueche, und einem Reiter ERLEDIGT. **ADMIN-Konto**: Anmeldung auf der Kontoseite als `admin` (erst `123`, sofort zu aendern), sieht alle Profile und die Statistik aller, bearbeitet Loadouts und Kosmetik anderer, aendert Namen und Kennwoerter, loescht Konten; nach Fehlversuchen gesperrt (1, 5, 15, 30 Minuten, dann doppelt), alles im Server. SQL in `docs/KONTO.md` 5.7 und 5.8, geprueft gegen ein lokales PostgreSQL (`tests/test_admin_sql.py`). Dazu: Granaten, Molotows, Blendgranaten und Raketen sind beim Gast im Flug wieder zu sehen; **Dash mit drei Ladungen**, je 2,7 s. Neue Netzmeldungen, darum neue Version |
| 0.30.0 | **Sichtweite mit Nebel**: im Gefecht stellt das Mausrad ein, wie viel Welt ins Bild passt (0,75 bis 2). Alles ausserhalb des normalen Bildes liegt im Nebel - Gelaende gedaempft, aber keine Gegner, Mitspieler oder Granaten, sie werden dort gar nicht gezeichnet. Die Ebenenansicht liegt im Gefecht jetzt auf Strg + Mausrad und Bild hoch/runter. **Blendgranate**: weit weg oder weggedreht kein Weiss mehr, nur eine weisse Explosion mit Glitzer und Druckring, ohne Splitter und Brandfleck. **Kosmetikbild** fuellt jetzt den ganzen Schirm; in der Kontoseite laesst es sich auf dem Weiss verschieben und in der Groesse einstellen (die Lage steht im PNG). **Minikarte** oben links, mit den Zombies in PVE. **Gegner fallen**, wenn ein Rueckstoss sie ueber eine Kante schiebt - selbst laufen sie nie hinunter. Behoben: die Munitionsanzeige flackerte in der Lobby bei jedem Schuss; in KONTO.html sprang eine gewaehlte Waffe im Loadout sofort zurueck |
| 0.29.0 | **Minikarte** oben rechts, ein Versuch: der Grundriss der eigenen Ebene, man selbst mit Blickrichtung, die eigenen Leute, der Bildausschnitt und in HUEGEL der Kreis - Gegner nicht, sonst waere es ein Wandhack (`dustfront/minikarte.py`). **Anmeldung im Kliniknetz, zweiter Anlauf**: nach 0.28.1 kam ZERTIFIKAT UNGUELTIG. Unter Windows fragt das Spiel jetzt, wenn Python ablehnt, Windows selbst - wie Edge und Chrome (`dustfront/windows_tls.py`); jeder Fehler dabei heisst nein. Die Anmeldetafel zeigt Grund und Aussteller, auch ohne Eingabeaufforderung. **Blendgranate** jetzt ganz weiss und deckend, solange sie voll wirkt; erst beim Abklingen scheint die Welt durch. **Unendlich Munition in der Lobby.** **MG deutlich schwaecher**: 17 statt 25 je Schuss, Salve zu drei statt vier (51 statt 100 auf einen Klick - vorher mehr als ein Scharfschuss), Dauerfeuer langsamer, unter dem Sturmgewehr |
| 0.28.1 | **Anmeldung scheiterte am Zertifikat** (gemeldet aus einem Kliniknetz: `CERTIFICATE_VERIFY_FAILED`, waehrend Firefox die Seite oeffnete). Die Pruefung bleibt an; stattdessen liegen die ueblichen Wurzelzertifikate dem Spiel bei, die strenge Pruefung von Python 3.13 ist zurueckgenommen, und eine `zertifikate.pem` im Benutzerordner wird mitgeladen - fuer Netze, die HTTPS mitlesen. Die Meldung sagt jetzt ZERTIFIKAT UNBEKANNT und verweist auf [`docs/KONTO.md`](docs/KONTO.md), Abschnitt 9; der Selbsttest nennt, wer das Zertifikat ausgestellt hat. Runde Klammern erscheinen nicht mehr als Fragezeichen |
| 0.28.0 | **Spielerkosmetik, ein erster Versuch**: ein eigener Ton und ein eigenes Bild fuer die Blendgranate. Gemacht in der Kontoseite (Reiter KOSMETIK: MP3 zuschneiden, Bass, lauter, mit Knall und Pfeifen aus dem Spiel mischen; Bild ausschneiden und filtern, mit Vorschau in Spielgroesse), abgelegt im Konto (neue Tabelle, `docs/KONTO.md` 5.6), in der Lobby an alle verteilt. Der Gastgeber startet mit oder ohne Kosmetik - mit erst, wenn alle alles haben. Wer wirft, klingt nach seinem Ton, und im Weiss steht sein Bild. Der Ton dauert 1 bis 4 Sekunden und wird immer leiser; das prueft das Spiel bei jedem Paket selbst. Neue Netzmeldungen, darum neue Version. Neuer Browsertest `tests/kontoseite_browser.py` |
| 0.27.1 | **Nur noch gleiche Versionen spielen zusammen.** Ein Gast mit einer anderen Version als der Gastgeber wird abgewiesen und bekommt eine Tafel FALSCHE VERSION mit beiden Nummern und wer aktualisieren muss; umgekehrt verlaesst ein Gast einen aelteren Gastgeber. Gaeste von vor 0.27.1 schicken keine Version und werden ebenfalls abgewiesen, mit "VERSION 0.27.1 NOETIG". Anlass war die **Treppe beim Gast**: ein einmaliger Druck auf E fuehrte zu hoch, runter, hoch, wenn das Loslassen verloren ging. Die Treppe haengt jetzt am Druck statt am Halten, beim Fokusverlust werden alle Tasten losgelassen. Wichtig: wer am Netzcode etwas aendert, zaehlt ab jetzt die Version hoch - sonst greift die Pruefung nicht |
| 0.27.0 | Neunzehn Punkte auf einmal, alles in [`docs/MEHRSPIELER.md`](docs/MEHRSPIELER.md), Abschnitt 12b. **Lobby**: wer aufmacht, landet zuerst auf einem Platz mit Arena (PVP), Schiessstand (Puppen, die den Schaden zeigen) und Gehege (Zombies); der Gastgeber stellt die Runden im Spiel ein (P) statt im Terminal, auf Wunsch als **Rundenplan** mit mehreren Runden, Schleife und Kopieren. **Regeln an einer Stelle** (`regeln.py`), neu: Schwierigkeit und Bosse an/aus fuer alles mit Wellen, ein Loadout fuer alle, Haltezeit und Verfall beim Huegel, gespielte Runden mit Matchpoint bei Versus. **Neue Anzeige** mit festen Orten und Modi (grosse Hotbar mit Loadout, kleine ohne; Vorrat nur bei knapper Munition; Bossbalken). **Dash** statt Sprint, alles etwas langsamer (Treffer auf weite Distanz 13 -> 23 Prozent). **Am Boden**: nicht mehr schiebbar, Mitspieler koennen ziehen (G), Rufen mit E, Randpfeile; Versus endet, sobald niemand mehr aufhelfen kann. **Ebenen**: obere ueber Spielflaeche ausgeblendet (Q, als Kontovorliebe), Granaten behalten beim Fall ihren Schwung, Gegner gehen ueber Treppen und Rampen (`wege.py`). Medkit in der Hand beim Anlegen, Mutter und Brandstifter neu gezeichnet. Dabei gefunden: alle sieben Rampen auf STAUBTAL fuehrten seit 0.23 ins Loch, der Gast sah weder seine Gesamtmunition noch sein Loadout in der Hotbar, Klaenge des Gastgebers kamen nie an, Tastendruecke fielen bei voller Leitung weg |
| 0.26.0 | Die Wellen ausgebaut, und dabei zwei Fehler gefunden, die eine Runde stillstehen liessen. **Wo Gegner herkommen** war eine Zeile: eine gewuerfelte Stelle irgendwo auf der Karte. Auf STAUBTAL gemessen hiess das 1477 Pixel im Mittel - zwanzig Sekunden Fussmarsch, bevor ueberhaupt etwas passierte -, und vier von sechs standen auf einem Plateau, auf das nur Rampen fuehren. Jetzt wird die Stelle gesucht: im Ring um einen Spieler, zwischen 260 und 620 Pixeln, moeglichst ausser Sicht, fast immer auf seiner Ebene (jetzt 446 Pixel, sechs Sekunden). Dazu Marken in der Karte - `Z` ist eine Spawnstelle, so wie `A B C` Kreise sind: 31 auf STAUBTAL am Fuss der Plateaus und an den Buden, 21 auf der Testkarte, und keine im offenen Sand. Der zweite Fehler fiel erst beim Nachmessen auf: ein Laeufer stand 120 Sekunden an einer Plateauwand, auf **derselben** Ebene wie die Spieler - und weil eine Welle erst endet, wenn alle liegen, wurde in 300 Sekunden Welle 2 nicht fertig. Wer sieben Sekunden nicht naeher kommt, wird jetzt umgesetzt; danach fuenf Wellen statt zwei. **Drei neue Gegner**, jeder mit einer anderen Frage: RENNER (138 px/s gegen 132 beim Spieler - Stehenbleiben ist keine Stellung mehr), SPEIER (haelt 150 bis 230 Pixel Abstand und spuckt, will gar nicht heran) und BLAEHER (platzt beim Sterben - Zusammenstehen wird teuer). **Drei Bosse**, jede fuenfte Welle, reihum: KOLOSS mit einem Stampfer, der auch hinter Deckung trifft (zwingt weg von ihm), MUTTER, die laufend Renner ruft (zwingt zu ihr hin), BRANDSTIFTER, der Feuer dorthin wirft, wo man gleich sein wird (zwingt in Bewegung). Jede Faehigkeit wird angekuendigt - ein Ring in der Groesse der Wirkung, ein Wort, ein Ton -, denn ohne Vorwarnung ist ein Boss keine Frage, sondern eine Steuer. **Wellen** kommen in Schueben statt auf einmal, hoechstens 22 zugleich, und bringen hoechstens eine neue Gegnerart je Welle; keine faellt mit einer Bosswelle zusammen. Nebenbei: das Feuer eines Gegners verschont Gegner - gemessen toetete ein Blaeher sonst alle fuenf Laeufer um sich herum, und dann spielt man den Trick statt des Spiels; der Molotow eines Spielers brennt weiter alles. Gegner tragen im Netz jetzt eine Kennung und ruckeln dadurch nicht mehr beim Gast (Stillstand 2,2 statt rund 50 Prozent), und der **Gastgeber** zeichnet endlich auch Lebensbalken - bisher tat das nur der Gast |
| 0.25.0 | **KONTO.html** - die Kontoseite zum Doppelklicken. Anmelden mit demselben Konto wie im Spiel, dann: jeder einzelne Zaehler mit seinem Namen in der Datenbank daneben, jede gespielte Runde einzeln, Schuesse und Treffer je Waffe mit dem Symbol aus dem Spiel, die drei Loadouts aendern und tragen, Anzeigename und Kennwort. Dazu ein Knopf, der **alles** als JSON herunterlaedt - wer wissen will, was ueber ihn gespeichert ist, soll es anklicken koennen statt erfragen zu muessen. Was die Seite **nicht** kann, mit Absicht: Zahlen aendern (geschrieben werden nur Anzeigename und Loadouts - selbst setzbare Werte waeren keine Statistik mehr), Konten loeschen (dafuer braeuchte es den geheimen Schluessel, und der darf in keiner herunterladbaren Datei stehen) und fremde Zeilen sehen (das entscheidet der Zeilenschutz auf dem Server, nicht die Seite). Sie wird **erzeugt**, nicht getippt: `werkzeug_kontoseite.py` schiebt Waffen, Wertnamen, Loadout-Regeln, Farben, Bilder und die Pixelschrift des Spiels an einer einzigen Stelle in `kontoseite_vorlage.html`, damit nichts zweimal gepflegt werden muss - und ein Test prueft, dass die eingecheckte Datei noch zu `config.py` passt. Alles in einer Datei, weil eine Seite unter `file://` keine Nachbardateien laden darf; Bilder gehen als data-URI mit. Ein neuer Reiter ist ein Eintrag in `SEITEN`. Gefahren und angesehen wurde sie im Browser gegen den echten Server, nicht nur gelesen - dabei fielen die Spielarten auf, die als `[object Object]` dastanden |
| 0.24.0 | Kosmetik, **vorgezeichnet und nicht eingebaut**. `python -m dustfront --kosmetik` schreibt fuenf Bilder nach `kosmetik_vorschau/`: das laufende Band einer Kiste nach dem Vorbild von CS, das Ergebnis, die Maske zum Waehlen von Figur, Waffen, Wurfwaffen, Klang und Musikkit, und eine zweite Siegtafel - je drei je Mannschaft in ihren Farben, darunter eine Buehne mit Siegerpodest, auf der die drei Besten ihre Animation machen und das Musikstueck des MVP laeuft. Jedes Bild traegt die Zeile `VORSCHAU - NOCH NICHT EINGEBAUT`, und das ist woertlich zu nehmen: kein Spielmodul importiert `kosmetik.py`, `K.SKIN_WAHL` ist leer, und ein Test prueft beides. Zwei Dinge daran stehen wirklich im Code und wurden dabei geprueft - die 38 **Rollen** in `K.SKIN_ROLLEN`, hinter denen jeder Bild- und Klangname steht statt fest im Quelltext, und die fuenf **Stufen** in `K.SELTENHEIT`; die Prozente auf dem Kistenbild sind nicht gemalt, sie kommen aus dieser Tabelle. Begruendung, Aufbau und der ehrliche Ueberschlag, was ein Einbau kosten wuerde - Besitz und Uebertragung sind die Arbeit, die Kistenanimation ist der kleinste Teil daran -, stehen in `docs/KOSMETIK.md` |
| 0.23.0 | **STAUBTAL**, die erste Karte aus einer Datei: 120 mal 80 Kacheln, also 3840 mal 2560 Pixel, und zu drei Vierteln offener Sand. Die obere Ebene ist kein Gangnetz, sondern drei Plateaus - und unter jedem steht Fels, man kommt nicht darunter, nur ueber eine der sieben Rampen hinauf. Dazu ein eigener Kachelsatz: Sand mit Windriffeln statt Blechplatten, Fels statt Wand, Fasser statt Frachtkaesten. Drei Kreise, die nicht gleich sind - einer im offenen Sand mit einem Ring aus Fassern als Wahrzeichen, einer in einer Halle, einer auf dem groessten Plateau -, und weil drei Kreise zugleich aus einer grossen Karte drei kleine machen wuerden, **wandert** der Kreis von einem zum naechsten. Karten sind jetzt Textdateien in `karten/` mit Kopf und Ebenenbloecken; Grossbuchstaben darin sind Marken, also steht in der Karte selbst, wo die Kreise liegen. Waehlbar im Gastgebermenue und mit `--karte` |
| 0.22.0 | Vier neue Waffen. **Molotow**: brennender Boden, kein Sprengschaden, genau auf einer Ebene - sie toetet niemanden im Wurf, sie nimmt einen Ort weg. **Blendgranate**: kein Schaden, aber eine Sekunde, und sie unterscheidet keine Mannschaften; wie stark sie trifft, rechnet jeder Rechner selbst aus der Lage des Blitzes, also kann nichts auseinanderlaufen. Bild und Klang haengen dabei an einer **Rolle** statt an einem Dateinamen - die Vorbereitung fuer Skins. **MG**: die schwerste Waffe im Spiel, Lauftempo auf 28 %, 56 Grad Drehung je Sekunde, dafuer von 7,5 auf 0,9 Grad Streuung beim Halten; zwei Betriebsarten auf einer eigenen Taste, Dauerfeuer mit Minigun-Anlauf (45 Schuss beim Halten gegen 8 beim Antippen) und Salve zu vier Schuss fast gleichzeitig. **Raketenwerfer**: vom Gastgeber einzuschalten, liegt einmal auf der Karte, wer ihn traegt traegt sonst nichts ausser dem Brecheisen auf F, Eigenschaden ja und Mannschaftsschaden nein; mit Zielerfassung ueber die rechte Maustaste - ein Kreis zieht sich zu und rastet ein, die Rakete lenkt dann mit hoechstens 120 Grad je Sekunde und kommt um keine Ecke. Nach unten wird nur ueber einem Loch erfasst, und die Rakete wechselt dort im Flug die Ebene; ohne Erfassung fliegt sie darueber hinweg. Wer erfasst wird, sieht es - und sieht es anders, sobald geschossen wurde |
| 0.21.0 | Was man spuert, statt es abzulesen. **Befinden**: ein roter Rand, der sich mit sinkendem Leben faerbt, bei einem Treffer aufschlaegt und unter 38 % stehenbleibt und pulst - mit einem Herzschlag im Ohr, in drei Klassen statt stufenlos, weil man eine Beschleunigung nicht merkt und drei Zustaende sehr wohl. Dazu wird alles andere **wirklich dumpf**: jeder Klang bekommt eine tiefpassgefilterte Fassung (echt gefiltert, nicht nur leiser - ohne numpy, mit `array`), und zwischen klar und dumpf wird ueberblendet statt umgeschaltet. Gebaut wird nur, was schon zu hoeren war, einer je Bild: 5 ms im Mittel statt 521 ms fuer alles auf einmal. Das **Medkit** ist der Gegenschlag: ein kalter Blitz, dann ist die Welt eine Sekunde lang sehr klar und sehr kalt (Kontrast ueber `2*in - g`, Drehpunkt bei 44 statt 128, weil die Welt hier gemessen bei Helligkeit 36 liegt und sonst schwarz wuerde), und danach drei Sekunden Ruhe. **Munitionsanzeige**: rechts nur noch das Magazin, in der Hotbar der Vorrat bei der Waffe, zu der er gehoert, und der Platz der gewaehlten Waffe sieht anders aus, wenn ihr Magazin leer ist. **Siegtafel** nach dem Vorbild von CS und Valorant: Mannschaften links und rechts in ihren Farben, je Zeile Platz, Name, das Zeichen der meistbenutzten Waffe, Abschuesse, Tode, das Verhaeltnis der Runde und der am oeftesten Erledigte |
| 0.20.1 | Die Masken dazu: KONTO mit Name und Kennwort - das erste Bedienelement im Spiel, in das getippt wird - und AUSRUESTUNG mit Satz, zwei Waffen und einer Wurfwaffe, beide aus Pause und Gefechtsmenue erreichbar. Gefragt wird jeweils genau einmal: wer ohne Konto spielen will, wird nicht wieder gefragt, und wer sich ein Loadout zusammengestellt hat, auch nicht. Ein geaendertes Loadout gilt ab dem naechsten Leben, nicht sofort - sonst waere es ein kostenloser Waffenwechsel mitten im Gefecht. Dafuer neu: eine Szene kann `weiterlaufen` setzen und rechnet dann weiter, waehrend ein Menue ueber ihr liegt. Genau eine Art Szene braucht das - eine, die an einer Leitung haengt: ein LAN-Gefecht, das stillsteht, waehrend jemand sein Loadout aendert, wird nach acht Sekunden als stumm hinausgeworfen |
| 0.20.0 | Konten, Statistik und Loadouts. Alle harmlosen Spielwerte laufen mit - Abschuesse, Schaden, Schuesse und Treffer je Waffe, gelaufene Strecke, Zeit im Kreis, beste Abschussfolge, und zwanzig weitere, alle in `WERTE` an einer Stelle. Als Ablage **Supabase**, aus vier Gruenden in `docs/KONTO.md` begruendet; der wichtigste: es spricht nur HTTPS und JSON, also reicht die Standardbibliothek, und sein oeffentlicher Schluessel darf im Quelltext stehen - damit geht die Anmeldung auf einem frisch heruntergeladenen Spiel sofort. Ohne eingetragenen Server laeuft alles lokal weiter, mit scrypt-gehashten Kennwoertern und `--konto neu` im Terminal fuer LAN-Runden ohne Internet. Gegen auseinanderlaufende Zahlen drei Regeln: der Gastgeber vergibt die Partiekennung und rechnet die Werte, ein eindeutiger Index laesst dieselbe Runde genau einmal zu, und was gespielt wurde, liegt sofort im Journal auf der Platte und wird erst nach Bestaetigung abgehakt - ein Netzaussetzer nach dem Schreiben kann damit weder etwas verlieren noch verdoppeln, nachgestellt in `tests/test_konto.py`. Loadouts: drei Saetze aus zwei Waffen und einer Wurfwaffe, im Profil und damit auf jedem Rechner, mit `--loadouts` als Regel der Runde |
| 0.19.3 | Zwei gemeldete Fehler, beide gemessen statt geraten. **Das Bild des Gastgebers zitterte ohne Pause**, das der Gaeste gar nicht: `Welt.ruckeln` war eine Meldung ohne Absender und ohne Ort, und weil der Gastgeber die Welt aller Spieler rechnet, lief jeder Schuss der ganzen Runde auf seiner Kamera zusammen - 2,09 Pixel in 100 % der Bilder gegen 0,00 beim Gast. Jetzt entscheidet der Zuschauer: andere Ebene oder zu weit weg ruckelt gar nicht, zwischen zwei Schlaegen liegt eine Sperre, und der eigene Gewehrschuss reisst nichts mehr. Der Regler im Menue wirkt endlich und gehoert zum Konto. **Granaten waren bei Gaesten unsichtbar** und schienen zu springen: ein Gast bekam von einer Explosion nichts (0 Partikel, kein Ton, kein Brandfleck) und zeichnete fliegende Dinge stur an die letzte Meldung - 80 % Stillstand, Spruenge bis 7 Pixel. Wirkungen gehen jetzt als eigene Meldung an alle und werden mit demselben Code nachgespielt, fliegende Dinge tragen eine Kennung und werden zwischen zwei Meldungen weitergezeichnet (2 % Stillstand, hoechstens 1,4 Pixel). Dazu die Leitung: `sendall` auf einer nicht-blockierenden Steckdose zerriss Nachrichten, jetzt wird gepuffert und ein Rueckstand gekuerzt |
| 0.19.2 | Mannschaftsfarben, Brecheisen auf F und fuenf gemeldete Fehler |
| 0.19.1 | Knappe Munition war keine: jeder Wiedereinstieg fuellte alle Magazine am Vorrat vorbei, der Vorrat sank nie, und darum liess sich auch keine Munitionskiste aufheben. Wiedereinstieg zahlt jetzt aus dem Vorrat, die Vorraete sind halbiert, und der Vorrat steht je Waffe in der Hotbar |
| 0.19.0 | Runden ueber das Internet: der Gastgeber laesst den Router den Port per UPnP selbst freigeben, mit Kennwort und ehrlicher Anleitung, falls es nicht klappt. Rauch neu gezeichnet - glattes Dichtefeld statt gewuerfelter Kloetze, Helligkeit nach Dicke, Licht von oben links. Treppen sperren nach einem Wechsel 1.5 Sekunden |
| 0.18.0 | Pausenmenue im Gefecht, mit Regeln, Mannschaftseinteilung und Rundenstart fuer den Gastgeber; Rauch komplett neu als deckende Blockwand, die auch Namen verbirgt; Unverwundbarkeit nach einem Treffer entfernt, Schutz gibt es nur noch beim Einstieg; Sturz mit Ring, Staub und Ton; Rueckmeldung beim Aufsammeln; am Boden liegt man wirklich; wer aufhilft, steht still; Waffenwechsel ohne Verzoegerung; Schwung fuer das Brecheisen; neun neue Treppen; nach oben ist nur noch eine Ebene sichtbar; die verschobene Ansicht kommt von selbst zurueck |

## Anpassen

Alle Stellschrauben stehen oben in der jeweiligen Datei.

* **Spielname**: `SPIEL_TITEL` in `rustfront_menu.py`, `TEXTE["name"]` in
  `rustfront_splash.py`.
* **Version und Phase**: `VERSION` und `PHASE` in `rustfront_menu.py`.
  `dustfront/config.py` liest die Zeile von dort aus, statt das Menue zu
  importieren - das Spiel soll auch ohne Menue starten.
* **Waffenwerte**: `WAFFEN` in `dustfront/config.py`. Schaden, Takt, Magazin,
  Streuung, alles an einer Stelle. Wer eine siebte Waffe will, traegt sie dort
  ein, haengt ihren Namen an `HOTBAR` und zeichnet ein Symbol
  `waffe_<name>` in `art.py`. Sonst ist nichts zu tun.
* **Hoehen der Ebenen**: `EBENEN_HOEHE` in `config.py`, in Welt-Pixeln.
  Der Abstand zwischen zwei Zahlen ist der, den man beim Herunterschauen
  sieht und beim Herunterfallen spuert.
* **Vorgaben fuer Einstellungen und Tasten**: `VORGABE` und `TASTEN_VORGABE`
  in `dustfront/einstellungen.py`.
* **Texturen und Klaenge ersetzen**: eine Datei `assets/<name>.png` oder
  `assets/sfx/<name>/<aufnahme>.mp3` hinlegen, und sie tritt an die Stelle der im Code
  gezeichneten Fassung. Es ist kein Code zu aendern. Namen, Masse und die
  beiden Werkzeuge dazu stehen oben unter
  [Texturen und Klaenge](#texturen-und-klaenge).
* **Dauer des Intros**: `PHASEN` in `rustfront_splash.py`. Jede Karte hat drei
  Abschnitte (Aufbau, Standbild, Abblende) mit jeweils der echten Dauer in
  Sekunden. `TEMPO` skaliert alles auf einmal, 1.3 bringt die Sequenz von rund
  36 auf etwa 28 Sekunden.
* **Einzelne Karten abschalten**: `KARTEN_AN`.
* **Namen, Sprueche und Untertitel**: `TEXTE`.
* **Farbschema**: `SCHEMA`, moeglich sind `aurum`, `glacies` und `ignis`.

## Technik

**Keine Assets.** Die 5x7-Pixelschrift des Menues, die beiden Schriften der
Splash-Sequenz, der Wandler, das Gelaende und saemtliche Klaenge werden im
Code erzeugt. Das Repo bleibt dadurch winzig und es kann nichts fehlen.

**Aufloesung.** Das Menue rendert auf 480x270, die Splash-Sequenz auf 320x180.
Beides wird auf das Fenster hochskaliert, wahlweise fuellend oder nur in
ganzen Pixelvielfachen. Jedes Fensterverhaeltnis funktioniert, von 320x180 bis
Ultrawide.

**Splash-Engine.** Portierung einer eigenen Web-Fassung: gleiche Paletten,
gleiches 8x8-Bayer-Dithering statt Alphamischung, gleicher Zufallsgenerator
(mulberry32), damit Sterne, Druckkorn und Strahlen exakt dort sitzen wie im
Original. 1,4 bis 4,8 ms pro Bild.

**Ton.** Jede Splash-Karte hat eine eigene Erzeugungsart, damit die Marken
nicht nach demselben Baukasten klingen: modale Synthese fuer Glocke und Metall
(Siegel), Holzstaebe wie ein Marimba (Kaltwerk), Zeilenpfeifen mit Netzbrummen
(Phosphor), Holzpresse und koerniges Papierrascheln (Papiermond), eine
laufende Druckmaschine (Tafel). Berechnet wird im Hintergrund, damit der Start
nicht haengt.

## Musik im Hauptmenue

Noch nicht eingebaut. Wenn es soweit ist, gehoert der Titel hier in eine
Tabelle mit Quelle und Lizenz, sonst weiss spaeter niemand mehr, woher er kam.

| Datei | Titel | Urheber | Lizenz | Quelle |
| --- | --- | --- | --- | --- |
| noch leer | | | | |

### Worauf achten

"Royalty-free" heisst nur, dass keine Gebuehr pro Abspielen faellig wird, es
heisst nicht "ohne Bedingungen". Drei Faelle:

* **CC0** ist der einfachste: gemeinfrei, keine Namensnennung noetig, auch bei
  einem verkauften Spiel. Trotzdem nennen ist hoeflich.
* **CC-BY** verlangt eine feste Credit-Zeile im Spiel. Vergisst man sie, ist
  die Nutzung nicht gedeckt.
* **NonCommercial (NC)** meiden, sobald ihr auch nur theoretisch Geld nehmen
  wollt. Das faellt spaeter auf die Fuesse.

### Brauchbare Quellen

| Quelle | Lizenz | Anmerkung |
| --- | --- | --- |
| kenney.nl | CC0 | Saubere, einheitliche Packs, keine Namensnennung noetig |
| opengameart.org (Filter auf CC0) | CC0 und andere | Direkt fuer Spiele gemacht, viele nahtlose Loops |
| pixabay.com/music | Pixabay-Lizenz | Kommerziell nutzbar, keine Namensnennung |
| incompetech.com (Kevin MacLeod) | CC-BY 4.0 | Ueber 2000 Stuecke, feste Credit-Zeile noetig |
| freemusicarchive.org | gemischt | Pro Titel pruefen |

Gesucht ist fuer das Menue ein langsamer, dunkler Industrial- oder
Ambient-Loop ohne Gesang, zwei bis vier Minuten, nahtlos schleifbar. Auf
OpenGameArt hilft die Stichwortsuche nach "dark ambient loop" oder
"industrial".

### Einbauen

Datei nach `assets/music/` legen, als OGG (kleiner als WAV, pygame kann es
direkt). Dann im Menue:

```python
pygame.mixer.music.load("assets/music/menue.ogg")
pygame.mixer.music.set_volume(app.settings.vol_ambient / 100.0)
pygame.mixer.music.play(-1)          # -1 = endlos wiederholen
```

Der vorhandene Regler REAKTORBRUMM in den Optionen steuert dann auch die
Musik, dafuer muss `Audio.apply_volumes` die Lautstaerke mitsetzen.

## Einbinden ins Spiel

```python
from rustfront_menu import run_menu

ergebnis = run_menu()
# {"action": "new_game" | "continue" | "quit",
#  "region": ..., "difficulty": ..., "callsign": ...}
```

Seit 0.12.0 ist das eingebaut: `spiel_scene()` in `rustfront_menu.py` ruft
`dustfront.main.aus_menue()` auf und holt danach den Anzeigemodus des
Menues zurueck. Fehlt das Paket `dustfront`, bleibt es bei der
Platzhalter-Szene - das Menue laeuft weiterhin auch allein.
