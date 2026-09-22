# DUSTFRONT

Ein Top-Down-Spiel auf dem Kontinent Veld. Du steuerst einen modularen
Wandler, baust ihn aus Schrott weiter aus und bewegst dich zwischen drei
Fraktionen: der Kolonne, dem Chor und den Freien Werften. Beide Spielmodi
teilen dieselbe 90-Grad-Draufsicht, du wechselst mit Tab zwischen "an Bord"
und "Fahr-Modus".

Geschrieben in Python mit pygame-ce. Schulprojekt, in Arbeit.

**Aktuell: Version 0.13.0, PRE-ALPHA.** Was das heisst, steht weiter unten
unter [Versionsnummern](#versionsnummern).

## Mitwirkende

Nicolas, Nikolaus, Marlon, Alfred.

## Stand

| Teil | Zustand |
| --- | --- |
| Splash-Sequenz | fertig, fuenf Karten mit eigenem Ton |
| Hauptmenue | fertig, inklusive Optionen und Spielstand |
| Spielkern | steht: feste Zeitschritte, drei Ebenen, Kollision, Wellen |
| Waffen | sechs Stueck, alle im Test nachgewiesen, jede in der Hand zu erkennen |
| Hoehenebenen | drei, alle gleichzeitig sichtbar, Sturz mit Steuerung in der Luft |
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
| LAN: Runde aufmachen | `LAN-GASTGEBER.bat` | `LAN-GASTGEBER.command` |
| LAN: mitspielen | `LAN-GAST.bat` | `LAN-GAST.command` |

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

Gebraucht werden Python 3.10 bis 3.14 und pygame-ce (getestet mit 2.5.8).
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
| Shift | Sprint |
| Maus links | Schiessen oder schlagen |
| Maus rechts | Einzielen (bei der Scharfschuetzenwaffe) |
| Mausrad | Ansicht eine Ebene hoch oder runter |
| 1 bis 6 | Waffe waehlen |
| R | Nachladen |
| H | Medkit |
| E | Treppe benutzen |
| Tab | Inventar |
| T | Ziellinie an oder aus |
| Z | Ziellinie ueber den Zeiger hinaus verlaengern |
| Esc | Pause |
| F11 | Vollbild |
| F3 | Debug-Anzeige |

### Die sechs Waffen

| Waffe | Art | Eigenheit |
| --- | --- | --- |
| Repetierer | Schuss | Der Allrounder. Genau, mittleres Tempo. |
| Sturmgewehr | Schuss | Rund 700 Schuss in der Minute, streut bei Dauerfeuer auf. |
| Schrot | Schuss | Sieben Kugeln auf einmal, nur auf kurze Entfernung. |
| Scharfschuetze | Schuss | Aus der Hueffte unbrauchbar. Rechte Maustaste halten zieht den Streifen in anderthalb Sekunden bis auf Ziellinienbreite zusammen. Gemessen: auf 300 Pixel trifft sie aus der Hueffte 8 Prozent der Schuesse, eingezielt 100. |
| Granate | Wurf | Fliegt genau so weit, wie man zielt, zwischen 60 und 260 Pixeln. |
| Brecheisen | Nahkampf | Schlaegt in einem Kegel von 80 Grad und stoesst zurueck. Braucht keine Munition. |

Die Munition haengt am Namen der Waffe, nicht an ihrem Platz. Umsortieren im
Inventar kostet also keine Patrone.

## LAN-Gefecht

Ein kurzer Mehrspieler-Test: mehrere Leute auf einer Karte, **keine
Gegner**, wer trifft bekommt einen Punkt. Nach der Runde steht die Liste,
und sie wandert in eine Bestenliste im Benutzerordner.

### So spielt man es

1. Einer startet **`LAN-GASTGEBER`**, tippt seinen Namen und liest die
   Adresse ab, die im Fenster steht (etwa `192.168.1.7:50505`).
2. Alle anderen starten **`LAN-GAST`**, tippen ihren Namen und diese
   Adresse.
3. Fertig. Esc beendet.

Alle muessen im selben Netz sein - gleiches WLAN oder gleicher Switch.
Eine Windows-Firewall fragt beim ersten Mal, ob Python ins Netz darf; das
muss erlaubt werden, sonst findet niemand den Gastgeber.

Wer lieber tippt:

```
python -m dustfront --host --name MEISTER
python -m dustfront --join 192.168.1.7 --name BESUCH
python -m dustfront --bestenliste
```

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

Ehrlich aufgezaehlt, damit niemand danach sucht: keine Vorhersage beim
Gast (die eigene Figur laeuft mit der Verzoegerung des Netzes, im LAN
unsichtbar, ueber WLAN spuerbar), kein Wiederverbinden nach einem Abbruch,
keine Kartenwahl, keine Teams. Das Gefecht laeuft immer auf derselben
Testkarte.

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
| `bestenliste.py` | Abschuesse ueber alle Runden |

Daneben liegt `docs/`:

| Datei | Inhalt |
| --- | --- |
| `KARTE.md` | Der Weltenplan: Kontinent, Orte, Wandler, Front, Meilensteine |

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
assets/sfx/<name>.wav       Klang
```

**Eine hingelegte Datei ersetzt den Platzhalter, ohne dass eine Zeile Code
geaendert wird.** Kein Eintrag nachzutragen, keine Liste zu pflegen. Datei
hinlegen, Spiel starten, fertig. Bei Bildern gehen auch `.webp` und `.bmp`,
bei Klaengen auch `.ogg`; gesucht wird in dieser Reihenfolge, die erste
gefundene gewinnt.

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
  `assets/sfx/<name>.wav` hinlegen, und sie tritt an die Stelle der im Code
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
