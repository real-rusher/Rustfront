# DUSTFRONT

Ein Top-Down-Actionspiel mit Einzelspieler und Mehrspieler. Erkunde
mehrstufige Karten, kämpfe gegen Gegner oder andere Spieler und passe
Ausrüstung, Steuerung und Darstellung an.

Geschrieben in Python mit pygame-ce. Schulprojekt, in Arbeit.

**Aktuell: Version 0.34.134, PRE-ALPHA.** Was das heisst, steht weiter unten
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

[`docs/KI.md`](docs/KI.md) ist der Plan für die KI aller Wesen:
zielorientiert (GOAP), Spezies statt fester Gegner, Moral, Wissen und
Funk, Anführer, Fraktionen, Alltag. Seit 0.34.29 steht der Kern, und die
Bots des Mehrspielers können ihn schon benutzen (Regel **BOT-KI: GOAP**);
alles Weitere folgt mit der Kampagne, Schritt für Schritt.

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

**iPhone und iPad:** derselbe Code als App, mit Touch-Steuerung und
Crossplay mit Windows und Mac. Gebaut wird sie auf einem Mac mit Xcode:
`ios/aufspielen.sh` baut sie und spielt sie direkt auf das angesteckte
iPhone oder iPad (`--testmodus` startet gleich im Testmodus); `ios/bauen.sh`
öffnet stattdessen Xcode. Schritt für Schritt in [`ios/LIESMICH.md`](ios/LIESMICH.md).
Am Rechner ändert das nichts: dort startet das Spiel wie immer mit Maus
und Tastatur.

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
| E | Treppe benutzen, aufhelfen, in den Buggy ein- und aussteigen; am Boden: rufen. Buggys gehen kaputt: dann fliegt man heraus |
| W/S, A/D im Buggy | Gas und Bremse (dann rückwärts), lenken - nur solange er rollt |
| Shift im Buggy | Handbremse: das Heck bricht aus, zum Driften |
| E am Panzer oder Panzerwagen | Einsteigen (seit 0.34.59); drin fährt man mit W/S, dreht mit A/D und zielt mit der Maus: der Turm bzw. MG-Ring folgt ihr |
| Maus links / rechts im Panzer | Kanone / Bug-MG (in Fahrtrichtung) |
| Maus links im Panzerwagen | MG im Ring |
| G | Gefallenen Mitspieler ziehen (Gefecht) |
| Q | Obere Ebenen ein- oder ausblenden (Gefecht) |
| P | Runden einstellen, in der Lobby (Gefecht) |
| Tab | Inventar |
| T | Ziellinie an oder aus |
| Z | Ziellinie über den Zeiger hinaus verlängern |
| Esc | Pausenmenü (im LAN-Gefecht läuft die Runde darunter weiter) |
| F11 | Vollbild |
| F3 | Debug-Anzeige |

## Testmodus

Seit 0.34.28: im Hauptmenü **TESTMODUS** (oder `python -m dustfront
--testmodus`), zum schnellen Ausprobieren neuer Sachen – nicht auf iPhone
und iPad. Man fliegt als **Beobachter** über die Karte (W A S D, Umschalt
schneller), den **nichts** in der Welt wahrnimmt oder trifft. Alles läuft
über den **Ziffernblock**, der immer am rechten Rand steht, jede Taste mit
ihrer Wirkung, und sich auch anklicken lässt: Zeit anhalten (0), ein
Schritt (.), Zeitfaktor (+ / −), KI aus (/), alles weg (*), Ebene (7 / 9),
KI-Ansicht (8), **Spawner** (4) für Figuren, alle Gegner und Bosse,
Buggys, Hotzone, Beute und Wurfwaffen mit Anzahl und Einstellungen – auch
bei angehaltener Zeit –, nochmal spawnen (5), Gottmodus (6), Bot (1),
stehender Spieler (2), Figur übernehmen (3), löschen (Enter). Esc öffnet
das Testmenü: Karte, Zeit, KI, Gottmodi einzeln, Wiedereinstieg, Wellen,
Einstellungen. Gebucht wird nichts. Alles Weitere in
[docs/TESTMODUS.md](docs/TESTMODUS.md). **Jedes neue Feature muss dort
ausprobierbar sein** (siehe `AGENTS.md`).

Seit 0.34.29 auch die **zielorientierte KI**: im Spawner beim BOT (seit
0.34.30 auch bei Gegnern und Bossen) die Einstellung HIRN auf GOAP stellen; Taste 8 zweimal zeigt links die
**Gedanken** der GOAP-Figur am Zeiger (Merkmale, Ziele mit Dringlichkeit,
Plan, Fakten, Protokoll). Im Testmenü: ZIEL ERZWINGEN und KI-DATEN NEU
LADEN (nach einer Änderung an `wesen/*.txt`).

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
| Revolver | Schuss | Sechs schwere Schüsse, langes Nachladen. In der Betriebsart FÄCHERN (Taste für den Feuermodus) leert ein Druck die ganze Trommel, schnell und ungenau. |
| Zwillinge | Schuss | Zwei Pistolen: linke Maustaste die rechte Hand, rechte Maustaste die linke, jede mit eigenem Takt. Abwechselnd doppelt so schnell, aber nie genau. |
| Maschinenpistole | Schuss | Sehr schnell, im Laufen genau, man ist mit ihr etwas flinker. Ab 160 Pixeln wird der Schaden kleiner, am Ende der Reichweite noch 45 Prozent. |
| Präzisionsgewehr | Schuss | Halbautomat zwischen Repetierer und Scharfschütze. Rechte Maustaste schliesst den Kegel zu einer Linie (ohne Mittellinie); jeder Schuss öffnet ihn nur ein kleines Stück. |
| Unterhebelgewehr | Schuss | Patrone für Patrone geladen; ein Schuss unterbricht das Laden, was drin ist, bleibt drin. |
| Panzerbüchse | Schuss | Ein Schuss, dann lange laden. Geht durch drei Körper und durch Kisten und Sandsäcke, am Fahrzeug voller Schaden. Der rote Ziellaser ist für alle zu sehen. |
| Doppelflinte | Schuss | Linke Maustaste ein Lauf, rechte beide auf einmal; danach lange laden. |
| Autoschrot | Schuss | Halbautomatisches Schrot: schwächer je Schuss, dafür schnell, und ein Treffer drückt deutlich zurück. |
| Minigun | Schuss | Anlauf, dann Dauerfeuer; wer feuert, steht fast und dreht kaum. Ein Gurt mit 240 Schuss. |
| Granatwerfer | Werfer | Granaten im Bogen bis zum Zeiger (70 bis 430 Pixel), über Kisten und Sandsäcke hinweg, nie über eine Mauer oder eine Ebene hinauf. Die Höhe sieht man nur an der Grösse. Tief getroffen zündet ein Körper sie sofort, sonst liegt sie kurz. |
| Einweg-Raketenwerfer | Werfer | Eine ungelenkte Rakete, dann liegt das leere Rohr qualmend am Boden, und man hat die nächste Waffe in der Hand. |
| Raketenbündel | Werfer | Sechs kleine, ungelenkte Raketen auf einen Druck, die schlingern: nah verheerend, weit weg wild. |

Die zwölf Waffen unter dem Brecheisen kommen aus dem Waffenpaket (seit
0.34.62) und stehen nur im Loadout (Menü AUSRÜSTUNG), nicht in der Hotbar
ohne Loadouts. Ihre Zahlen sind ein erster Vorschlag. Bots tragen sie noch
nicht.

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

### Bots

In jeder Runde mit PVP-Anteil (PVP, PVPVE, TEAM, VERSUS, HÜGEL) kann der
Gastgeber **Bots** zuschalten: Regel **BOTS AUFFÜLLEN BIS** (aus, 2 bis 12
Spieler). Sie füllen auf die Zahl auf, mit Mannschaften gleichmässig;
kommt ein Mensch dazu, geht ein Bot. Seit 0.34.26 lassen sich Bots auch
fest in eine Mannschaft stellen (**BOTS IN ROT / BLAU**, ohne Mannschaften
**BOTS DAZU**, je 0 bis 8); mit Auffüllen zusammen gilt die grössere Zahl.
In der Lobby gibt es keine.

**Team-Manager** (seit 0.34.26): Pausenmenü → **TEAMS UND BOTS** (oder der
Knopf auf der Rundentafel, Taste P). Dort stellt der Gastgeber Auffüllen
und Bots je Mannschaft ein und setzt Spieler in eine Mannschaft. In der
Lobby gilt das für die nächste Runde, im Gefecht sofort: ein Spieler
wechselt und steigt bei der neuen Mannschaft ein, Bots kommen und gehen.

Die Bots sind bewusst **schwach und fair**. Sie spielen mit genau der
Eingabe, die ein Gast schicken würde (Laufrichtung, Mauszeiger,
Feuertaste), und haben keine Sonderrechte:

* Sie sehen nur in ihrer Sichtweite (etwa eine halbe Bildbreite), nicht
  durch Wände und nicht durch Rauch. Blendgranaten blenden sie genauso.
* Sie brauchen eine Reaktionszeit, bevor sie auf ein neues Ziel schiessen,
  und schwenken das Fadenkreuz nicht schneller als eine Hand die Maus.
* Sie zielen erst ungenau und dann besser, halten aber nie vor. Wer quer
  läuft, wird oft verfehlt.
* Sie schiessen in Feuerstössen, bleiben dabei oft stehen und hören
  Schüsse in der Nähe.

Sie erledigen die Aufgabe der Spielart: In HÜGEL gehen sie in den Kreis
(der geht vor - sie kämpfen auf dem Weg dorthin), in VERSUS helfen sie
gefallenen Mitspielern auf, sonst suchen sie Gegner. Sie nehmen Treppen
und Aufzüge und wechseln je nach Abstand zwischen ihren beiden Waffen.
Zum Nachladen und wenn sie angeschlagen getroffen werden, gehen sie in
**Deckung** hinter die nächste Mauer oder Kiste; in eine Kiste in der
Schusslinie schiessen sie nicht, sie gehen zur Seite.

Ausrüstung (seit 0.34.26): zwei verschiedene Waffen, **eine Granate pro
Leben**, die gewöhnliche Reserve und **kein Medkit**. Sie heben nichts
auf, und ihre Munition ist immer begrenzt, auch wenn die Runde etwas
anderes sagt. Ist alles verschossen und die Granate geworfen, gehen sie
mit dem Brecheisen los. Sie haben so viel Leben wie ein Spieler. Das
Loadout wird zu jedem Leben neu gewürfelt; bei EINES FÜR ALLE tragen sie
das vorgegebene (mit höchstens einer Wurfwaffe).
**Nie C4**, keinen Raketenwerfer, und **sie fahren keine Buggys**.

**Funk und Taktik** (seit 0.34.27): Bots sagen kurz vor einer Aktion an,
was sie vorhaben – als kleiner Untertitel über ihnen, mit Mannschaften nur
für die eigene. Sie flankieren einen Gegner hinter Deckung, halten ihn
derweil nieder (Feuer auf die Stelle neben seiner Deckung), geben
Kameraden Feuerschutz, die nachladen, angeschlagen sind oder flankieren,
und stürmen zu zweit oder zu dritt: sammeln außer Sicht, Granate, REIN.

Für Bots wird nichts gebucht, und sie kommen in keine Bestenliste. Wer
einen Bot erledigt, bekommt den Abschuss aber wie jeden anderen.

Ebenfalls neu als Regel: **GEGNER AUF DER MINIKARTE**. Dann stehen
feindliche Spieler und Bots als rote Punkte darauf, für alle gleich.

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

### Über das Internet: mit Code (seit 0.34.13)

Jede eigene Lobby bekommt von selbst einen **Code aus vier englischen
Wörtern**, zum Beispiel `THERMAL-UNDERLYING-PROVIDERS-TOE` (die Wörter
vergibt Cloudflare). Er steht in der Lobby oben links und im
Pausenmenü unter *ONLINE-CODE* (auswählen kopiert ihn). Wer mitspielen
will, öffnet *ANDERER LOBBY BEITRETEN*, fügt den Code mit Strg+V ein und
drückt *BEITRETEN* - von überall, auch aus einem anderen Netz.

* **Nichts einzustellen.** Kein Router, keine Portfreigabe, keine Abfrage
  der Windows-Firewall: niemand lauscht nach draussen. Gastgeber und Gast
  verbinden sich beide nur ausgehend mit Cloudflare (kostenloser "Quick
  Tunnel", ohne Konto). Das Programm dafür, `cloudflared`, liegt für
  Windows und macOS in [`tools/cloudflared`](tools/cloudflared) bei, mit
  Lizenz und Prüfsummen; das Spiel packt es beim ersten Mal selbst aus.
* **Der Code gilt, solange die Lobby offen ist.** Startet sie neu (Spiel
  neu, aus einer fremden Runde zurück), gibt es einen neuen.
* **Wer den Code hat, kommt rein.** Für Fremde gibt es das Kennwort
  (Kommandozeile `--passwort`).
* **Es ist weiter weg als im LAN.** Der Gastgeber rechnet alles; ein Gast
  sieht seine eigene Figur erst nach einem Hin- und Rückweg. Über
  Cloudflare sind das in Deutschland meist zwanzig bis fünfzig
  Millisekunden. Zielen folgt trotzdem sofort, das rechnet jeder bei sich.
* **Ohne Gewähr von Cloudflare.** Quick Tunnels haben keine
  Verfügbarkeitszusage. Fällt der Dienst aus, steht der Grund statt des
  Codes da; im selben Netz geht es dann weiter über das LAN.

Abschalten lässt sich der Code unter *EINSTELLUNGEN > NETZ > ONLINE-LOBBY*.

### Im eigenen Netz (LAN)

Seit 0.34.13 ist die Lobby im LAN nur zu sehen, wenn man es will:
*EINSTELLUNGEN > NETZ > IM LAN SICHTBAR*. Dann steht sie bei den anderen
im selben Netz in der Liste und man sieht deren Lobbys - dafür fragt die
Windows-Firewall beim ersten Mal, ob Python ins Netz darf (TCP 50505, für
die Suche UDP 50504). Ohne den Schalter lauscht die Lobby nur auf
127.0.0.1, und es fragt niemand; über den Code kommt man trotzdem herein,
auch im selben Netz. Welche Ports das Spiel seit wann benutzt:
[`docs/MEHRSPIELER.md`](docs/MEHRSPIELER.md), 12g, "Was im Netz wann
dazukam".

Der alte Weg über den Router steht weiter zur Verfügung: `python -m
dustfront --host --online --passwort GEHEIM` lässt den Router den Port per
UPnP freigeben (dann fragt auch die Firewall). Den Code braucht man dafür
nicht.

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
| `werkzeug_aufnahme.py` | Nimmt Gefechte aus dem Testmodus als Video auf (braucht ffmpeg) |
| `ios/bauen.sh` | Baut auf dem Mac die App für iPhone und iPad (Anleitung `ios/LIESMICH.md`) |
| `ios/aufspielen.sh` | Baut, signiert, spielt die App auf ein angestecktes iPhone oder iPad und startet sie, ohne Klick in Xcode |
| `ios/start.py` | Einstieg der App auf iOS |
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
| `fahrzeug.py` | Buggy, Panzer und Panzerwagen: Fahren, Anstossen, Rammen, Turm, Waffen, Kaputtgehen |
| `bots.py` | Die Bots: was sie sehen, wie sie zielen und laufen, das Auffüllen |
| `bottaktik.py` | Funk und Taktik der Bots: flankieren, niederhalten, Feuerschutz, stürmen |
| `goap.py` | Zielorientierte KI, der Kern: Ziele, Aktionen, Planer, Gehirn (docs/KI.md) |
| `wesen_daten.py` | Spezies, Ziele und Aktionen aus `wesen/*.txt` lesen und prüfen |
| `bot_goap.py` | Die Bots mit zielorientierter KI (Regel BOT-KI: GOAP) |
| `gegner_goap.py` | Zombies und Bosse mit zielorientierter KI (Regel GEGNER-KI: GOAP) |
| `testmodus.py` | Der Testmodus: Beobachter, Ziffernblock, Spawner, Gottmodi (docs/TESTMODUS.md) |
| `render.py` | Kamera, Tiefenwirkung, Schatten, Ziellinie, HUD |
| `play.py` | Die Spielregel: Wellen, Tod, Neustart |
| `menues.py` | Pause, Einstellungen, Steuerung, Mitwirkende |
| `inventar.py` | Ausrüstung, Waffenraster, Tasche, Hotbar |
| `ui.py` | Bedienelemente: Kästen, Knöpfe, Reiter, Regler, Schalter |
| `einstellungen.py` | Einstellungen und Tastenbelegung, lesen und schreiben |
| `pfade.py` | Wo diese Dateien liegen, je nach Betriebssystem |
| `art.py`, `audio.py`, `font.py` | Grafik, Klang und Schrift, alles zur Laufzeit erzeugt |
| `art_fahrzeuge.py` | Panzer und Panzerwagen gezeichnet: Wanne, Turm, MG-Ring, Ketten, Wracks |
| `art_figuren.py` | Skins (Operators, Soldaten), NPCs und Tiere aus dem Figurenpaket gezeichnet |
| `art_waffen.py` | Die 58 Eintraege des Waffenpakets gezeichnet: Waffe an der Hand, Zeichen in der Hotbar, Teile |
| `vorlagen.py` | Die beiden Werkzeuge `--vorlagen` und `--assets` |
| `netz.py` | LAN-Verbindungen und Protokoll |
| `online.py` | Über das Internet: Online-Code über Cloudflare (`tools/cloudflared`) |
| `wszugang.py` | Weg eines Gastes zum Online-Code ohne cloudflared (iOS, Linux) |
| `plattform.py` | Was auf iOS anders ist: kein zweites Programm, Touch, Bildschirmtastatur |
| `touch.py` | Touch-Steuerung: zwei Sticks und Knöpfe |
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

Und `wesen/` daneben (seit 0.34.29): Spezies, Ziele und Aktionen der
zielorientierten KI als Textdateien, ein Block je Ding. Das Format steht
in `docs/KI.md`, Abschnitt 4; `tests/test_pruefung.py` prüft die Dateien.

Und `karten/` daneben: jede Karte eine Textdatei, ein Zeichen eine
Kachel, die Ebenen hintereinander. `~` steht für ein Loch auf einer
höheren Ebene, `^` und `v` verbinden die Aufzüge. Grossbuchstaben sind
Marken (`A B C` Kreise, `Z` Spawnstellen). Seit 0.34.6 gibt es dazu
Gelände und Kleinkram:

| Zeichen | Kachel | | Zeichen | Kachel |
| --- | --- | --- | --- | --- |
| `.` | Sand / Boden | | `r` | gewachsener Fels (hoch, hält Kugeln auf) |
| `:` | Piste | | `b` | Felsbrocken |
| `;` | Kies, Geröll | | `s` | Sandsäcke |
| `"` | Gestrüpp | | `h` | Holzkiste |
| `_` | Pflaster | | `k` | Kaktus |
| `=` | Dielen | | `w` | Schrott, Wracks |
| `#` | Mauer | | `X` | Fass |

Fahrzeuge stehen auf Marken: `F` Buggy, `P` Panzer, `L` Panzerwagen
(seit 0.34.59).

Brocken, Sandsäcke, Kisten, Kakteen, Schrott und Fässer halten auf, aber
man schiesst darüber hinweg; Fels und Mauern halten auch Kugeln auf.

STAUBTAL kommt vollständig aus `werkzeug_staubtal.py`: wer die Karte
ändern will, ändert das Werkzeug und erzeugt sie neu
(`python werkzeug_staubtal.py`). `tests/test_pruefung.py` prüft, dass die
Datei genau dessen Ausgabe ist - von Hand nachgebesserte Stellen gingen
beim nächsten Erzeugen verloren, so wie bis 0.34.

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
| 0.34.134 | **SCHLACHT: 2 Punkte schon beim Umwerfen, Bots aus Fahrzeugen werfen, Werfer mit Karte.** (1) Jeder Abschuss bringt **2 Punkte** (vorher 1), gebucht **sofort beim Umwerfen** - egal, ob er danach aufgeholfen wird; beim Tod nicht noch einmal. (2) **E an einem Fahrzeug, in dem ein Bot der eigenen Seite sitzt**: der Bot steigt aus, man selbst ein (nicht beim Flakwagen, nicht im fliegenden Tragschrauber; beim Panzerwagen nur vorn an der Seite, an der Fahrertuer - an der Mitte und hinten sitzt man wie bisher auf). Steigt man aus, steigt der Bot sofort wieder ein, wenn er in der Naehe ist. (3) **Werfer aufgebaut**: eine Karte wie im Nachschub, mit Kreis der Reichweite - jetzt **ueber die halbe Kartenbreite** (mindestens wie bisher 3200 px) - und den Zielen, die die Seite sieht; Zeiger auf der Karte zielt, Klick feuert. Netz/LAN: Regelwert geaendert (Punkte), sonst wie 0.34.133; Gastgeber und Gast brauchen 0.34.134. Karten unveraendert. |
| 0.34.133 | **SCHLACHT: nicht mehr alle Bots zum selben Kampf, eigene Ziele und Vorstoesse an verschiedenen Stellen.** (1) **Zulauf begrenzt**: zu einem gemeldeten Kampf gehen hoechstens 3 Bots zugleich (ohne Front, `kampf_zulauf`) bzw. eine Gruppe (Front, `kampf_gruppen`) - die anderen verfolgen ihr eigenes Ziel; erst nach 25 s darf jemand nachruecken. Der Umkreis, aus dem ein Kampf anzieht, ist kleiner (1 100 statt 1 600 px), und eine Gruppe biegt nur ab, wenn er an ihrem eigenen Weg liegt. (2) In einer Gruppe geht ein Bot nur **nahen** Schuessen nach (330 px), fernen schaut er nur entgegen. (3) **Front**: kein Ziel bekommt mehr als gut ein Drittel der Bots einer Seite; **Stosstrupps** aus 1-2 Bots gehen zu Punkten hinter der Front. (4) **Ohne Front** (STAUBTAL, STAUBTAL - OFFEN): die Bots verteilen sich immer auf fuenf Abschnitte ueber drei Viertel der Kartenhoehe (vorher erst ab 20 Bots und in gut einem Drittel der Hoehe), die Abschnitte treffen sich in verschiedener Tiefe, und ein Viertel zieht als Stosstrupp gleich zur Basis der anderen. Behoben: wer die Mitte *seines* Abschnitts erreicht hatte, bekam dasselbe Ziel immer wieder (geprueft wurde gegen die Kartenmitte) und blieb dort stehen, statt weiter vorzustossen. Gemessen (20 je Seite, 3 Minuten): im groessten Knaeuel stand vorher auf STAUBTAL - OFFEN im Mittel 68 % einer Seite (Spitze 95 %), jetzt 47 % (Spitze 67-75 %), an 6,5 statt 4,5 Orten; auf FLUSSTAL 25 % statt 28-34 % (Spitze 45 % statt 60 %). Pruefungen in `tests/test_spiel.py` (Abschnitt 0.34.133) und `tests/test_verhalten.py` (Szene `verteilung`). Netz/LAN: unveraendert (nur der Gastgeber rechnet die Bots), Gastgeber und Gast brauchen trotzdem dieselbe Version. Karten unveraendert. |
| 0.34.132 | **JE SEITE in SCHLACHT je Karte, von sehr wenig bis sehr viel.** Gewuenscht: "die moegliche Bot-Anzahl in den Schlacht-Settings pro Karte anpassen, von sehr wenig zu unglaublich viel". Statt 12-30 gibt es jetzt die Stufen 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 30, 36, 42, 50, 60, 75, 100, 125, 150 - und jede Karte bietet so viele davon an, wie sie traegt: FLUSSTAL und KANALSTADT sagen es im Kopf (`je_seite: 24`, `je_seite_bis: 150`), andere Karten nach ihrer begehbaren Flaeche (STAUBTAL bis 150, STAUBTAL - OFFEN bis 125, SCHNEEFELD bis 5, Testkarte bis 16). Wer die Karte wechselt, bekommt hoechstens, was die neue traegt. Ab 42 je Seite steht `(VIEL!)` dabei: gemessen haelt ein gewoehnlicher Rechner bis etwa 40 je Seite die volle Geschwindigkeit, mit 100 je Seite braucht ein Schritt etwa 2,5 mal so lang (das Spiel laeuft dann langsamer). Netz: die Gegendruck-Grenze waechst mit der Groesse der Weltmeldung - mit sehr vielen Kaempfern fiel sonst schon im LAN jede zweite Meldung aus. Pruefungen in `tests/test_spiel.py` (Abschnitt 0.34.132). **Netz/LAN: geaendert** (Gegendruck beim Gastgeber, Regelwerte von JE SEITE). **Karten: geaendert** (Kopfzeilen von FLUSSTAL und KANALSTADT). Gastgeber und Gast brauchen 0.34.132. |
| 0.34.131 | **Zwei neue Schlachtkarten, eine Front mit Eroberungspunkten, Einstiegskarte nach dem Tod, Bots in Gruppen und an allen Fahrzeugen.** (1) **FLUSSTAL** (340 x 210, gruen): ein Fluss in der Mitte, nur an fuenf Stellen zu queren - zwei steinerne Bruecken, zwei Furten, die breite Furt um die Muehle; Doerfer, Gutshof, Kapelle auf dem Huegel, Waelder (nur zu Fuss), Hecken mit Durchlaessen, Bachlaeufe, Stellungen an den Ufern. **KANALSTADT** (320 x 224, Stadt): zerschossene Strassenzuege, ein Kanal mit vier Bruecken und der eingestuerzten ALTEN BRUECKE (Truemmer im seichten Wasser), Bahnhof, Rathaus, Gaswerk/Kraftwerk, Hafenbecken, Park, Truemmerfeld. Beide punktgespiegelt (keine Seite im Vorteil), **FLUSSTAL ist die neue Vorgabe fuer SCHLACHT**, in den anderen Spielarten spielbar (Kreise des HUEGEL sind die Punkte). (2) **Wasser**: seicht (`+`) bremst Menschen und Fahrzeuge, spritzt; tief (`%`) sperrt, aber Kugeln, Sicht und Wuerfe gehen darueber. Neue Kachelsaetze `gruen` und `stadt` (Wiese, Feldweg, Kiesufer, bemooster Granit, Baeume, Feldsteinmauern, Bruecken; Asphalt, Fahrbahn, Gehweg, Schutt, Rasen, Ziegeldaecher, Beton, Truemmer, Autowracks, Kasernenhof, Kanal). (3) **Front** (`front.py`): je Karte drei Basen pro Seite mit Mauerring, Toren, Bunker und **eigener Ausstattung** (z. B. Tragschrauber im Nordlager, Werfer im Hauptlager) und **neun Eroberungspunkte**. Ein Punkt bringt keine Zaehler, sondern ist, ganz eingenommen und ohne Gegner in der Naehe, ein **Einstieg**. (4) **Einstiegskarte nach dem Tod** wie in Battlefield: links alle Einstiege (1-9), rechts die Karte zum Anklicken; wenn die Zeit um ist (7 s), steigt man am gewaehlten ein. Oben eine Leiste mit allen Punkten A-I, im Kreis ein Balken, Meldungen (ROT NIMMT ...). (5) **Bots**: kein Lauf mehr zur Mitte - jede Seite plant laufend, welche Punkte sie angreift, verteidigt oder haelt; die Bots gehen **in Gruppen von 1 bis 4** auf **verschiedenen Wegen** (Kanten, die eine andere Gruppe zum selben Ziel nimmt, kosten mehr - so flankieren sie), **in Formation** (Keil, Linie, Reihe, Staffel, Raute; im Wald und in Gassen auf der Spur des Anfuehrers), stehen am Punkt im Ring und schauen nach aussen. Sie steigen dort ein, wo sie ihr Ziel gut erreichen - mit Aufschlag fuer jeden, der schon von dort kam, damit sie von mehreren Seiten angreifen. (6) **Bots fahren alle Fahrzeuge**: Jagdpanzer (dreht die Wanne), Spulenwagen (Kettenblitz, EMP-Feld gegen nahe Fahrzeuge), Trosswagen (faehrt hinter die Front, stellt ab, steigt aus), Funkwagen und Werfer (Stellung hinter dem eigenen Punkt, aufbauen; Funk stoert, wenn Gegner nah sind; der Werfer schiesst auf gesehene Gegner, nie auf eigene Leute), Tragschrauber (hebt ab, kreist ueber der Front, bombt, fliegt zum Nachladen heim und landet). Fahrer steigen an der Basis mit dem wertvollsten freien Fahrzeug ein. Pruefungen in `tests/test_spiel.py` (Abschnitt 0.34.131) und `tests/test_pruefung.py` (Karten = Ausgabe ihrer Werkzeuge). **Netz/LAN: geaendert** - Schlachtmeldung `fp` (Stand der Punkte), Gast-Nachricht `einstieg` (gewaehlter Einstieg). **Karten: neu** (`karten/flusstal.txt`, `karten/kanalstadt.txt`, Zeichen `+ % |`). Gastgeber und Gast brauchen 0.34.131. |
| 0.34.130 | **Chor-Waffen werden heiss, Kugelblitz schwaecher, Napalm-Angriff mit Bomber, Obergrenze je Seite als Regel.** (1) **Chor-Waffen (Spulengewehr, Kettenblitz, Spiegellaser, Kugelblitz) haben Hitze statt Munition**: jeder Schuss heizt; nach so vielen Schuss, wie frueher ins Magazin passten, **ueberhitzt** sie und ist gesperrt, bis sie abgekuehlt ist (5 bis 7,5 s, laenger als das alte Nachladen) - **einmal ein Kuehlton** (Klacken, herunterfahrendes Pfeifen, Dampf), **kein Nachladen** mehr (R tut nichts). In Ruhe kuehlt sie nach und nach ab, **auch weggesteckt** - man nimmt solange eine andere Waffe. Die Anzeige am Zeiger zeigt die Hitze als Balken, ueberhitzt rot mit KÜHLT. Bots wechseln, solange sie ueberhitzt ist. (2) **Kugelblitz stark abgeschwaecht** (gemeldet "viel zu OP"): Blitze 18 -> 10 Schaden, Reichweite 86 -> 58 px, 4 -> 3 Strahlen; das Platzen 70 -> 40 in 96 -> 62 px. (3) **Napalm-Angriff**: statt eines Tons fuer alle **hoert man den Bomber nur in seiner Naehe** - er zieht unsichtbar ueber die Bahn (auch davor und dahinter), unter ihm am lautesten. **Die Bomben sieht man fallen** (olivgruene Brandkanister mit rotem Band, mit Schwung, Nase nach unten, wachsender Schatten), jede pfeift. **Das Napalm brennt anders**: tiefrot mit gelbweissem Kern, schwarzem, oeligem Russ am Rand, zuengelt schneller, mehr Funken, schwarzer Rauch steigt auf - und **30 bis 42 s** statt 16 bis 24. Behoben: beim Gast ging ein Napalmfeuer mit der gewoehnlichen Dauer zu frueh aus; der Ort des Flugzeugs vor dem Start brach ab (lerp ausserhalb 0..1). (4) **HÖCHSTENS JE SEITE** ist eine Regel der SCHLACHT in der erweiterten Ansicht, **Vorgabe aus**: jede Seite kann beliebig viele vom selben Fahrzeug haben; an, gelten die Grenzen aus 0.34.129. Pruefungen in `tests/test_spiel.py` (Abschnitt 0.34.130). **Netz/LAN: geaendert** - Spielereintrag `ul` (Ueberhitzung je Waffe), Brandflaechen mit Dauer und Napalm-Kennung (Feld 7, 8), Napalm-Angriffe mit Alter (`la` Feld 6), neue Netzklaenge `ueberhitzt`, `bomber`, `napalm_fall`, neue Regel `fahrzeug_grenze`. Gastgeber und Gast brauchen 0.34.130. Karten unveraendert. |
| 0.34.129 | **RESPAWN und Aufgeben, Balancing der SCHLACHT mit FREISCHALTEN.** (1) **RESPAWN im Escape-Menue**: man stirbt und kommt neu, wie nach jedem Tod (in VERSUS bis zur naechsten Runde raus). Wer kurz davor (8 s) von einem Gegner getroffen wurde, zaehlt fuer den als Abschuss - sonst entzoege man sich so jedem Abschuss. (2) **Am Boden: R 2,5 s halten gibt auf** (Balken in der Bodenanzeige, loslassen faengt von vorn an) - zaehlt wie Verbluten fuer den, der einen umgeworfen hat. Bots geben nie auf. (3) **Balancing** (`docs/BALANCING.md`): alles billiger (z. B. Buggy 3, Panzer 9, Tragschrauber 9, Werfer 10, Flak 5 - der Konter billiger als der Flieger); **hoechstens so viele gekaufte je Seite** (Tragschrauber, Werfer, Funkwagen, Spulenwagen 1; Panzer, Jagdpanzer, Flak 2; Panzerwagen 3); **Funkwagen, Werfer, Tragschrauber nur in der eigenen Haelfte**; ein **zerstoertes Fahrzeug bringt den halben Preis** (mindestens 2, Trosswagen 3) statt pauschal 5. (4) **FREISCHALTEN** (neue Regel der SCHLACHT, auch in der einfachen Ansicht: AUS / SCHNELL / NORMAL / LANGSAM): Schweres kommt in drei Stufen **nach dem Spielverlauf** statt nach festen Minuten - bei 5 wie bei 30 Minuten spielbar (NORMAL in 5 Minuten: Stufe 1 nach 0:30, 2 nach 1:06, 3 nach 1:45; spaetestens nach 2:00 / 4:30 / 7:30). Die Kaufliste zeigt bei Gesperrtem, wann es kommt. **Auch die Basis waechst mit**: zum Start Buggys, Krad, Panzerwagen, Trosswagen; mit Stufe 1 Flak und zweiter Trosswagen, mit Stufe 2 der Panzer. AUS: alles sofort wie vorher. Testmodus: Zeile RESPAWN. Pruefungen in `tests/test_spiel.py` (Abschnitte 0.34.129; aeltere SCHLACHT-Pruefungen spielen mit FREISCHALTEN AUS). **Netz/LAN: geaendert** - Eingabe des Gasts: Taste `aufgeben` (RESPAWN) und Feld `ag` (R gehalten am Boden); Weltmeldung `rlz` (Laufzeit der Runde); neue Regel `freischalten`. Gastgeber und Gast brauchen 0.34.129. Karten unveraendert. |
| 0.34.128 | **Aufnahmen in echtem Tempo, Szene Absturz.** `werkzeug_aufnahme.py` rechnete ohne Zeitlupe je Bild 6 statt 4 Spielschritte: **jedes Video seit 0.34.35 lief 1,5-mal zu schnell**, und die Zeiten in den Szenen stimmten nicht (z. B. traf der zweite Tragschrauber Sekunden zu spaet). Jetzt sind beide Haelften zusammen genau ein Bild; eine Pruefung zaehlt die Schritte je geschriebenem Bild. Neue Szene `heli_absturz` (zwei Tragschrauber, einer prallt an eine Mauer, einer schlaegt im Freien auf) auf einem Feld, ueber dem kein Plateau liegt (`_feld_offen`). Nur das Werkzeug - **Netz/LAN: nicht geaendert**, das Spiel selbst unveraendert gegenueber 0.34.127. |
| 0.34.127 | **Tragschrauber stuerzt ab, massivere grosse Explosionen, weniger Speicher.** (1) **Wird der Tragschrauber zerstoert, sind Pilot und Mitfahrer sofort tot** (auch am Boden; vorher fielen sie heraus und bekamen 70 Schaden). (2) **In der Luft getroffen faellt er mit seinem Schwung**: ein Feuerball in seiner Hoehe (`heli_treffer`, ohne Schaden am Boden), dann fliegt das brennende Wrack in seine Richtung weiter, wird von der Luft gebremst, faellt immer schneller und dreht sich, mit Rauchspur. Erst beim Aufschlag gibt es Schaden ringsum (Art `absturz` und ein Feuerball). **Mauern und Felsen**: ist etwas hoeher als das Wrack gerade, prallt es dort ab, verliert den Schwung und rutscht an der Wand herunter; niedrigere Hindernisse ueberfliegt es. Sinkt es beim Ueberfliegen auf eine Mauer oder ueber einem Loch, rutscht es zur naeheren Seite herunter (liegt nie in einer Mauer). Werte `K.TRAGSCHRAUBER["absturz"]`. (3) **Massive Explosionen dichter** (Werfer, Bombe, Absturz): groessere und etwas mehr Teilchen (`rauch(..., dicht=)`), damit kaum Boden zwischen ihnen durchscheint; die kleinen bleiben locker. Die Grenze fuer Effekte auf einmal liegt jetzt bei 4500 (`K.EFFEKTE_HOECHSTENS`), sonst fiel bei der Werfer-Explosion ihr eigener Feuerball weg. (4) **Speicher**: Werfer-Gestell und Funkmast merken sich ihre Bilder zugeschnitten (vorher zu drei Vierteln leere Flaechen, bis ueber 100 MB). Pruefungen in `tests/test_spiel.py` (Abschnitt 0.34.127). **Netz/LAN: geaendert** - neue Explosionsart `heli_treffer` (Radius = Hoehe); das fallende Wrack kommt ueber die bisherige Fahrzeugmeldung (Leben 0, Hoehe im Zusatzwert). Gastgeber und Gast brauchen 0.34.127. Karten unveraendert. |
| 0.34.126 | **Kein Drift-Ton mehr, Explosionen als Teilchenwolken, Funkmast einheitlich, Werfer-Gestell klassisch gemalt.** (1) **Der Ton beim Driften ist weg** (`buggy_rutschen`, gemeldet: "den moechte ich nie wieder hoeren"): er kam beim Krad und beim Buggy, wenn sie rutschten, und auch bei jedem Aufprall (der setzt das Rutschen hoch). Kein Ersatz - beim Driften ist es still; Spuren und Staub bleiben. (2) **Alle neuen Explosionen sind eine grosse Teilchenwolke** wie die aelteren (Granate, Panzerkanone), statt vieler kleiner, buckliger Wolkenbilder: Rauch, Staub und Feuer bestehen aus einzelnen Pixel-Teilchen (`effekte.Teilchen`), die auseinanderfliegen, abbremsen, kleiner werden und ausduennen; Feuer glueht dazu weich. Besonders der **Rueckstrahl des Werfers** ist jetzt ein Ausstoss aus Teilchen nach hinten. Die Schatten fliegender Brocken sind weich statt schwarzer Striche. Die Lage jedes Teilchens wird aus seinem Alter gerechnet - auch die groesste Explosion kostet nur ein paar Millisekunden. (3) **Funkmast**: kein schwarzer Umriss mehr (er kam nur in manchen Lagen), Farbe und Dicke bleiben beim Aufrichten gleich (die Farben werden am aufrechten Mast gerechnet), und liegend geht er in den Lack des Dachs ueber - man sieht ihn erst, wenn er sich hebt. (4) **Werfer-Gestell und Raketen klassisch gemalt** (`art_werfer.py`, wie die anderen Fahrzeuge: Rohre mit dunkler Kante, Kern und Glanzlinie, duenne Bandeisen, rote Spitzen, Lagerboecke mit hellem Deckel) statt als schattiertes 3D-Modell - aber fuer jede Drehung (5 Grad) und jede Aufrichtung (2 Grad) ein eigenes Bild, die Muendungen ragen steiler hoeher ins Bild. Pruefungen in `tests/test_spiel.py` (Abschnitt 0.34.126). **Netz/LAN: nicht geaendert** (dieselben Meldungen; `buggy_rutschen` wird nicht mehr gesendet, weil er nicht mehr klingt). Karten unveraendert. |
| 0.34.125 | **Schwarze Quadrate bei Einschlaegen weg, Seile des Funkmasts gleichmaessig, Videos der neuen Fahrzeugteile.** (1) **Bei jedem Einschlag lagen schwarze Quadrate herum**: ein Brocken, der am Ende ausgeblendet wird, veraenderte dabei sein Bild im Zwischenspeicher (`set_alpha(None)` schaltet bei pygame-ce die Durchsichtigkeit ganz ab) - danach war jeder Brocken dieser Sorte und jedes liegende Teil `fx_teil_N` ein schwarzes Kaestchen. Jetzt wird eine Kopie ausgeblendet (`effekte._zeichne`). (2) **Funkmast**: die vier Abspannseile sind glatte duenne Linien (vorher als 3D-Koerper: die vorderen dick und schwarz, die hinteren kaum zu sehen); die hinteren liegen unter dem Mast, die vorderen darueber. (3) **Aufnahmen** (`werkzeug_aufnahme.py`): neue Szenen `funkwagen`, `werfer`, `werfer_explosion`, `schrottbombe`, `flak`, `krad` - die Nacharbeit aus 0.34.124 als Video. Pruefungen in `tests/test_spiel.py` (Abschnitt 0.34.124 ergaenzt). **Netz/LAN: nicht geaendert** (nur Zeichnen); Gastgeber und Gast sollten trotzdem dieselbe Version haben. Karten unveraendert. |
| 0.34.124 | **Nacharbeit an den Fahrzeugen: alles neu, was 0.34.117 bis 0.34.120 an Designfehlern hatte.** (0.34.121 bis 0.34.123 waren nur Zwischenstaende beim Bauen und wurden nie einzeln veroeffentlicht; Kommentare im Code nennen sie.) (1) **Neues Effektsystem** (`effekte.py`): Teilchen mit Hoehe, Schwerkraft, Abprall und Schatten, gemalter Rauch und Feuer in vier Lichtstufen, Funkenstreifen, flatternde Stofffetzen, Druckringe, Blitz, Brandflecken (`fx_brand_N`) und Teile (`fx_teil_N`) am Boden. Alle Explosionen, Rauch und Effekte laufen darueber (`Welt.explosion`, Tabelle `effekte.ARTEN`). (2) **Kleiner 3D-Zeichner** (`drei_d.py`) fuer alles, was sich im Raum drehen und kippen muss. (3) **Bombe des Tragschraubers neu**: keine Fliegerbombe mehr, sondern eine kleine rostige Schrottbombe (Blechdose mit Draht, Naegeln, Klebeband und Lunte, `art_bombe.py`); am Heli sieht man nichts, der Fahrer laesst sie neben der Kanzel fallen, sie ueberschlaegt sich, die Lunte glimmt und sprueht Funken. Neue Klaenge `bombe_ab`, `bombe_fall`. (4) **Werfer neu**: das Raketengestell ist ein 3D-Modell aus sechs ungleichen Schrottrohren auf einer alten Felge (`art_werfer.py`), dreht sich und **hebt die Rohre nach der Zielentfernung** (nah steil, weit flacher, `K.WERFER` `hub`, `hub_dreh`); die Raketen sind 3D-Modelle, fliegen im Bogen aus ihrem Rohr und ziehen Rauch, der Rueckstrahl kommt am hinteren Rohrende heraus. (5) **Flak-Schuesse neu**: sichtbar ist eine Leuchtspur, die zur Hoehe des Luftziels steigt, dazu ein eigenes Muendungsfeuer; die Granate selbst ist unsichtbar. (6) **Funkwagen: der Mast ist ein 3D-Modell** (`art_funkmast.py`): ein Teleskopmast aus Schrottrohren mit selbstgebautem Peilkopf (Ausleger mit Querstaeben, Ring aus einer Felge, Warnlampe). Eingepackt liegt er auf dem Dach; der Aufbau richtet ihn auf, faehrt das obere Rohr aus, klappt den Kopf auf, dann laufen vier Abspannseile zu den Erdnaegeln. Aufgebaut dreht sich der Kopf weich (`K.FUNKWAGEN["kopf_dreh"]`, ersetzt `drehen`), beim Abbau dreht er erst zurueck und dann laeuft alles rueckwaerts. Mit Schatten. Die alten flachen Bilder `funkwagen_aufbau_N`/`funkwagen_aktiv_N` sind weg. (7) Jagdpanzer: die Luke ist fest in die Wanne gemalt. Krad: der Beifahrer sitzt sichtbar im Beiwagen und zeigt seine Waffe, nur so weit der Sitz es erlaubt (`K.KRAD` `beifahrer_bogen`). Der Tragschrauber schiebt in der Luft keine Bodenwesen mehr (Insassen zaehlen bei `Welt.auseinander` nicht). Testmodus: wie bisher FUNKWAGEN, WERFER, TRAGSCHRAUBER, FLAKWAGEN, KRAD, JAGDPANZER; Pruefungen in `tests/test_spiel.py` (Abschnitte 0.34.111, 0.34.120 angepasst, neu 0.34.123 und 0.34.124). **Netz/LAN: geaendert** - neue Explosionsarten `einschlag`, `bombe`, `bombe_los`, `flak_schuss`; bei den Luftarten (`flak`, `luft_kiste`, `luft_mensch`, `fallschirm_riss`) steht der Ort jetzt am Boden und der Radius traegt die Hoehe; `werfer_start` traegt Steilheit*1000 + Richtung; Feld 20 des Werfers hat ein sechstes Feld (Steilheit), fallende Bomben des Tragschraubers ein viertes (Richtung). Gastgeber und Gast brauchen 0.34.124. Karten: unveraendert. |
| 0.34.120 | **Funkwagen und Werfer: Aufbau mit Animation, neues Raketengestell, groesste Explosion.** (1) **Aufbau und Abbau sind Animationen** (`Aufbauwagen.fortschritt`, 0 bis 1, weich - vorher wechselte das Bild einfach): der **Funkwagen** laesst die vier Abspannseile zu den Erdnaegeln auslaufen (die Naegel stehen erst am Ende), der Peilrahmen steigt auf dem Mast (wird groesser), klappt auf und dreht sich schneller an - 15 Zwischenstellungen `funkwagen_aufbau_1..15`, dann `funkwagen_aktiv_N`. Beim **Werfer** schwenken die vier Stuetzen aus und setzen auf (`werfer_stuetze_1..8`), dann hebt sich das Gestell in neun Stufen. Der Abbau laeuft rueckwaerts; **solange er eingepackt wird, steht der Wagen** (vorher fuhr er mit halb ausgefahrenem Mast los) und ein neuer Aufbau geht erst, wenn alles eingepackt ist. (2) **Der Raketenwerfer ist neu** (`art_werfer.py`): ein eigenes Bild ueber dem Wagen mit sechs Rohren in zwei Reihen, **wie ein Zylinder beleuchtet und mit Perspektive** (je hoeher, desto kuerzer und mit groesseren Muendungen, dazu Hubzylinder, Schatten auf der Pritsche) und **dreht sich weich zum Zeiger** (110 Grad/s, `Werfer.rohr_rel`) statt in 30-Grad-Stufen zu springen. (3) **Die Raketen fliegen sichtbar nacheinander aus ihren Rohren** (Reihenfolge 0-3-1-4-2-5, alle 0,5 s): das Rohr ist danach leer (dunkle Muendung), und **die Rohre laden nach einer Pause einzeln wieder** (die rote Spitze erscheint Rohr fuer Rohr, `K.WERFER["salve"]` `nachladen_ab`/`nachladen_je`); bereit ist er, wenn alle sechs voll sind. (4) **Beim Abfeuern entweicht viel Druck nach hinten**, wie hinten bei einer Panzerfaust, nur viel mehr: ein Feuerstrahl, grosse graue Schwaden, eine breite Staubwand und Staubringe (`Welt.explosion` Art `werfer_start`). (5) **Die Explosion ist die groesste und lauteste des Spiels** (Art `werfer_gross`, neuer Ton `werfer_explosion`): sechs Feuerbaelle nacheinander, ein Blitz ueber das ganze Bild, zwei Druckwellen, hunderte Funken, ein dicker schwarzer Rauchpilz, ein grosser Krater, Kamera-Schlag 26. **Der Fahrer stirbt sofort** (nicht nur am Boden) **und alle im Umkreis von 210 Pixeln mit ihm**, bis 330 Pixel reisst es noch Leben, Fahrzeuge bekommen 700. **Kein Wrack**: sein Bild ist leer, am Boden bleiben acht **Einzelteile** (Rohrstueck, Rad, Blech, Rakete, Tuer, Zahnrad: `werfer_teil_0..5`) liegen. Testmodus: WERFER und FUNKWAGEN wie bisher; Pruefungen in `tests/test_spiel.py` (Werfer-Abschnitt 0.34.112 angepasst, neu 0.34.120). **Netz/LAN: geaendert** - Feld 20 des Werfers ist jetzt `[bereit, Zielgrund, Gestellwinkel, Rohrmaske, [[Restzeit, x, y, Rohr], ...]]` (vorher mit Stufe), neue Explosionsarten `werfer_start` (Radius = Richtung des Gestells) und `werfer_gross`; der Gast rechnet den Fortschritt der Animation selbst aus der Phase. Gastgeber und Gast brauchen 0.34.120. Karten: unveraendert. |
| 0.34.119 | **Tragschrauber: ein Schatten, der genau passt; Bomben gross, senkrecht, eine nach der anderen.** (1) **Der doppelte Schatten ist weg**: in der Luft zeichneten zwei Stellen einen (das allgemeine Fahrzeug-Oval am Boden und der der Luftschicht). Jetzt wirft die Luftschicht allein einen **Schatten, der exakt der Silhouette des Tragschraubers entspricht** (aus seinem eigenen Bild abgeleitet: Rahmen, Kanzel, Leitwerk, Fahrwerk) **plus den Schatten der Rotorblaetter** in der jeweiligen Stellung (`rotor_schatten_0..5`); am Boden gilt dieselbe Silhouette. (2) **Bomben**: sie sind kein Teil des Fahrzeugbilds mehr, sondern **eigene, groessere Bilder** am Rahmen (`bombe_rahmen`) und fallen als grosse Bombe (`bombe_fall`, mit Leitwerk, Nase, gelbem Band, Rauchstreifen nach oben, wachsendem Schatten am Boden) **senkrecht unter ihm** - **ohne sein Tempo**: sie loesen sich vom Rahmen an der Seite, an der sie hingen, und schlagen genau dort ein, wo sie abgeworfen wurden (vorher flogen sie 0,8 s mit ihm voraus). Die Fallzeit ist 1,1 s, sie faellt beschleunigt, dazu ein Klacken beim Loesen und ein Pfeifen (`bombe_ab`, `bombe_fall`). **Nur eine Bombe auf einmal**: die naechste geht erst, wenn die erste unten ist. Testmodus: wie bisher TRAGSCHRAUBER (OBJEKTE); Pruefungen in `tests/test_spiel.py` (Abschnitt 0.34.113 angepasst, neu 0.34.119). **Netz/LAN: nicht geaendert** (die fallenden Bomben gehen wie bisher im Zusatzwert des Tragschraubers mit; der Gast zeichnet sie nach der neuen Art); Karten unveraendert; Gastgeber und Gast sollten dieselbe Version haben. |
| 0.34.118 | **Flak: langsamer, platzende Granaten, Abwuerfe am Schirm.** (1) **Der Vierling schiesst deutlich langsamer**: gut zwei Schuss je Sekunde (`FAHRZEUG_WAFFEN["flak_kanone"]`, takt 0,42 s) statt 16 MG-Kugeln; vier Rohre reihum, kraeftiger Rueckstoss. (2) **Die Granaten platzen nach einer bestimmten Strecke** (`fahrzeug.Flakgranate`, Zeitzuender): sie fliegen ueber alles hinweg, was dazwischen steht, und platzen am Zeigerpunkt, bei einem anvisierten Luftziel zusaetzlich, sobald sie ihm auf 44 px nahekommen; nur eine Mauer haelt sie auf. Optisch eine **Flakwolke wie im zweiten Weltkrieg** (`Welt.explosion` Art `flak`): heller Kern, der gleich verglueht, dunkle aufquellende Rauchwolke, die ein paar Sekunden stehen bleibt, Splitterfunken; neuer Knall (`schuss_flak_kanone`, `flak_burst`). (3) **Gegen Dinge in der Luft bleibt sie sehr stark**: platzt die Wolke nahe an einem Luftziel, trifft sie es immer (75 Schaden in der Mitte, am Rand von 64 px ein Drittel weniger; `K.FLAK`); die Granate rechnet das Vorhalten wie bisher. Am Boden ist es nur ein kleiner Splitterkreis (26 Schaden, 40 px). (4) **Kleine Abwuerfe** (Kisten, Medkits) und **Fallschirmjaeger** platzen mit einem Treffer mit eigener Animation (`luft_kiste`: Holzsplitter, Schirmfetzen, Rauch; `luft_mensch`: Blut, Fetzen; ein Fallschirmjaeger stirbt in der Luft gleich, ohne Aufhelfen). (5) **Fahrzeuge am Schirm** halten 200 Schaden aus: dann **reisst der Schirm** (Animation `fallschirm_riss`: Bahnen und Fetzen in den Farben der Seite fliegen auseinander, neuer Ton), der Wagen **faellt beschleunigt** (bis 620 px/s, dreht sich im Sturz) und kommt mit **4 % Leben** am Boden an (hartes Aufsetzen: Staub, Funken, starkes Rucken, `absturz`). Ein Wagen mit gerissenem Schirm ist kein Luftziel mehr. Testmodus: wie bisher ABWURF-Eintraege und FLAKWAGEN; Pruefungen in `tests/test_spiel.py`. **Netz/LAN: geaendert** - Abwuerfe tragen als Feld 7 die Zeit seit dem Riss (0 = Schirm ganz), und die Welt-Effekte kennen die neuen Explosionsarten `flak`, `luft_kiste`, `luft_mensch`, `fallschirm_riss`, `absturz`. Gastgeber und Gast brauchen 0.34.118. Karten: unveraendert. |
| 0.34.117 | **Abwurf, Jagdpanzer, Trosswagen, Basis-Fahrzeuge.** (1) **Am Fallschirm bewegt sich der ganze Wagen gleichmaessig**: Luke und Geschuetz (Panzer, Panzerwagen, Jagdpanzer, Flakwagen) wanderten beim Pendeln unabhaengig vom Rest, weil Wanne und Aufbau getrennt gedreht wurden. Jetzt wird der Wagen einmal als **ein Bild** zusammengesetzt und als Ganzes gedreht (`SchlachtTeil._fracht_ganz`); ab dem Boden bleibt alles wie bisher. (2) **Jagdpanzer: der Fahrer ist nicht sichtbar** - die Luke ist immer geschlossen, mit und ohne Fahrer dasselbe Bild (kein Skin mehr, die Pruefung zu den Skins wurde dafuer geaendert). (3) **Der Trosswagen ist ein Fuenftel groesser** (Bild, Schatten, Wrack, Kreise, Achsen, Einsteigreichweite, die Zone hinten). (4) **Basis: zwei Trosswagen und ein Flakwagen je Seite** (`K.SCHLACHT["fahrzeuge"]`); der Flakwagen kommt mit einem Bot am Steuer und **wartet mit dem Losfahren auf andere Fahrzeuge**: er steht, bis ein anderes Fahrzeug seiner Seite mit Fahrer mehr als 350 px von seinem Startort weg ist, faehrt dann hinter ihm her (`K.FLAK["konvoi_los"/"konvoi_abstand"]`) und steht wieder, wenn es keinen Vordermann gibt (`bots._konvoi_fahren`). **Netz/LAN: nicht geaendert** (die Basis hat mehr Fahrzeuge, die Meldungen bleiben gleich), Karten unveraendert; Gastgeber und Gast sollten dieselbe Version haben. |
| 0.34.116 | **Fehler behoben: Abwurf am Fallschirm stuerzte beim Zeichnen ab** (gefunden beim Filmen der neuen Fahrzeuge). `SchlachtTeil._fracht_zeichnen` nahm fuer jede Fahrzeugart ohne Eigenschaft `rechteckig` an, sie habe eine Wanne wie Panzer und Panzerwagen - und rief `_wanne_flaeche` auf, die nur diese haben. Betroffen waren **Buggy, Krad, Trosswagen, Spulenwagen, Funkwagen, Werfer und Tragschrauber** (seit der Verallgemeinerung in 0.34.107); der Flug des Wagens am Schirm liess das Bild abbrechen. Jetzt gilt fuer Arten ohne diese Eigenschaft das Bild der Art selbst. Neue Pruefung in `tests/test_spiel.py`: die Last am Schirm wird fuer **jede** Art in `fahrzeug.ARTEN` gezeichnet (schlug vorher bei sieben Arten fehl). **Netz/LAN: nicht geaendert** (nur Zeichnen), Karten unveraendert; Gastgeber und Gast sollten trotzdem dieselbe Version haben. |
| 0.34.115 | **Funkwagen stoert jetzt auch die Minikarte und den Trupp-Funk** (die zwei offenen Punkte aus 0.34.111). **Minikarte:** wer im Kreis eines gegnerischen Funkwagens auf STOEREN steht, sieht nur noch **Rauschen** (dichtes, flackerndes Bild mit wanderndem Streifen) - weder man selbst noch die eigenen Leute, Buggys, Kreis oder Ausschnitt. Das Einzige, was darauf steht, ist ein **Ping** (Punkt mit zwei auslaufenden Ringen, bernsteinfarben) an jedem Funkwagen, der einen erfasst: bei sich deckenden Kreisen mehrere Pings. Gilt auf der kleinen und der grossen runden Karte, fuer Gastgeber und Gast (`Gefecht.funk_stoerer`). **Trupp-Funk:** ein Anfuehrer im Stoerkreis kommt mit seinem Spruch nicht durch (abgebrochen: grauer Ring, rotes Kreuz; kein Eintrag im Funknetz; 8 s Pause, `K.TRUPP["funk_gestoert_pause"]`) und hoert Sprueche anderer Trupps nicht. Werte: `K.MINIKARTE["gestoert"]`. Testmodus: Funkwagen auf STOEREN aufbauen (wie bisher) und mit ICH in den Kreis gehen; Taste 8 (INFO) zeigt abgebrochene Sprueche wie sonst. **Netz/LAN: geaendert** - der Zusatzwert (Feld 20) des Funkwagens ist jetzt [Betriebsart, Basis-Team] statt nur der Betriebsart (alte Zahl wird noch gelesen); die Karte rechnet jeder Rechner selbst aus der Fahrzeugliste. Gastgeber und Gast brauchen 0.34.115. Karten: unveraendert. |
| 0.34.114 | **Flakwagen** (siebente Stufe des Plans, `docs/FAHRZEUGE.md`). Ein Panzerwagen mit **Flak-Vierling** statt des MG-Rings: die Lafette sitzt hinten auf der Pritsche, dreht schneller (190 Grad/s) und schiesst 16 Schuss/s (`FAHRZEUG_WAFFEN["flak_mg"]`, 9 Schaden, gegen Luftziele x1,8 - `K.FLAK`). **Nur Bots fahren ihn** (`nur_bot`, gewuenscht: ein Mensch koenne Boden- und Luftziel nicht auseinanderhalten): ein Mensch kommt nicht hinein (E bleibt ohne Wirkung), und ein Abwurf (`DROPZONE: FLAKWAGEN`, 9 Punkte) bringt einen Bot der Seite gleich am Steuer mit - eine zusaetzliche Verstaerkung, die nach dem Tod nicht nachkommt. Der Bot am Steuer sucht im Umkreis von 680 px das naechste Luftziel der Gegner (Tragschrauber, Spaehdrohnen, Abwuerfe am Schirm, Fallschirmjaeger), legt den Zeiger auf dessen *Bild*, die Zielregel aus 0.34.113 rastet ein und **haelt vor** (neu: `_vorhalten` in `luft.py`, die Kugel prueft ihren Abstand zum jetzigen Ort des Ziels) - Mauern auf dem Boden unter dem Flieger halten die Kugeln auf. Ohne Luftziel schiesst er wie ein Ring-MG auf den Boden. Wer im Flakwagen sitzt (`flak`), trifft als Einziger auch Abwuerfe am Schirm und Fallschirmjaeger. Bild: Wanne mit Fuehrerhaus, Munitionskisten und Sockel; Lafette mit vier Rohren, Schilden und Trommeln (Rueckstoss reihum), Wrack, Schatten, Mannschaftsfarben und Skins der Bots. Testmodus: Spawner FLAKWAGEN (leer), ABWURF: FLAKWAGEN, FAHRER MIT FAHRZEUG mit FAHRZEUG FLAKWAGEN; die INFO-Ansicht zeigt "> FLAK" und eine Linie zum Bild des Fliegers; Pruefungen in `tests/test_spiel.py`. **Netz/LAN: geaendert** - neue Fahrzeugart `flakwagen` (Fahrzeugliste wie beim Panzerwagen, Aufbau `flak_lafette`); das Einrasten und Vorhalten rechnet der Gastgeber. Gastgeber und Gast brauchen 0.34.114. Karten: unveraendert. |
| 0.34.113 | **Tragschrauber und die Luftziel-Regel** (sechste Stufe des Plans, `docs/FAHRZEUGE.md`). **Regel: man schiesst auf das, worauf der Mauszeiger liegt - auch in der Luft.** Was in der Luft ist, wird um seine Hoehe nach oben versetzt gezeichnet; liegt der Zeiger auf diesem *Bild* (nicht auf dem Schatten), rastet das Ziel des Schuetzen auf den Ort darunter ein, und seine Kugeln gehen auf das Luftziel (Mauern halten sie auf, Leute dazwischen nicht). Liegt der Zeiger daneben, schiesst man wie immer auf den Boden. Gilt fuer Menschen, Bots und Fahrzeuge und fuer jedes Luftziel (`luft.py`, `LuftTeil.luft_ziele`); fuer spaetere Helis und Ziele auf anderen Etagen kommt nur ein Eintrag dazu. Heute Luftziele: Tragschrauber und Spaehdrohnen (alle koennen sie treffen) sowie Abwuerfe am Schirm und Fallschirmjaeger (nur Flak - kommt mit dem naechsten Fahrzeug; ohne Flak aendert sich fuer sie nichts). **Tragschrauber:** am Boden ein kleiner Wagen, ab 100 px/s hebt er ab (140 Leben), fliegt 140 bis 260 px/s ueber Mauern und Felsen, stehen bleiben geht nicht, A/D Kurve, E setzt zur Landung an (unten muss Platz sein, sonst Absturz). In der Luft treffen ihn nur gezielte Schuesse und Flak. Er sieht die Gegner unter sich (Radius 300, markiert sie fuer die Seite) und wirft zwei Bomben (linke Maustaste, 110 Schaden im Radius 62, fallen 0,8 s vor ihm), nachgeladen wird nur am Boden. Bild mit Schatten, drehendem Rotor und Pilot (Skins gehen). Nachschub DROPZONE: TRAGSCHRAUBER fuer 9 Punkte, nur Menschen am Steuer. Testmodus: Spawner TRAGSCHRAUBER und ABWURF: TRAGSCHRAUBER; Pruefungen in `tests/test_spiel.py`. **Netz/LAN: geaendert** - neue Fahrzeugart `tragschrauber`, Feld 20 traegt hier [fliegt, Hoehe, Bomben, fallende Bomben]; das Einrasten rechnet der Gastgeber (Eingabe unveraendert). Gastgeber und Gast brauchen 0.34.113. Karten: unveraendert. |
| 0.34.112 | **Werfer** (Steilfeuer, fuenfte Stufe des Plans, `docs/FAHRZEUGE.md`): Halbkette mit Raketengestell, nur 120 Leben. Rechte Maustaste baut ihn auf (im Stand, 2,5 s), die linke schiesst eine **Salve** von sechs Raketen (alle 0,5 s eine, Flugzeit 3,6 s, Streukreis 110, je 90 Schaden im Radius 46, 120 am Blech, Pause 14 s) auf 400 bis 3 200 Pixel. **Geschossen wird nur dorthin, wo die eigene Seite ein gueltiges Ziel hat** (im Umkreis 130): ein Gegner oder Fahrzeug, das ein Kamerad sieht (hoechstens 420 weit, freie Sicht) oder das markiert ist (Drohne, Horchposten, Funkwagen), und die Hotzone - weitere Objectives haengen sich in `Gefecht.werfer_ziele` an. Das Gestell dreht sich zum Zeiger, am Ziel zaehlen **rote Kreise** herunter (fuer alle zu sehen), Raketen fliegen im Bogen mit Rauchspur; der Zeiger zeigt seinen Streukreis (gruen gilt, rot nicht) und die Anzeige sagt warum nicht (ZU NAH, ZU WEIT, KEIN GÜLTIGES ZIEL). **Jede Salve verraet ihn** 6 s lang (markiert fuer die Gegner) mit eigenem Zeichen (Dreieck mit drei Punkten) auf Minikarte und Nachschubkarte, das die eigene Seite immer sieht. Wird er zerstoert, gibt es eine **grosse Explosion** (Radius 170, 400 Schaden), die alle daneben toetet. Nachschub DROPZONE: WERFER fuer 9 Punkte, nur Menschen am Steuer. Testmodus: Spawner WERFER und ABWURF: WERFER; Pruefungen in `tests/test_spiel.py`. **Netz/LAN: geaendert** - neue Fahrzeugart `werfer`, Feld 20 traegt hier [Salve bereit, Zielgrund, Gestellstufe, Raketen]; Gastgeber und Gast brauchen 0.34.112. Karten: unveraendert. |
| 0.34.111 | **Funkwagen** (vierte Stufe des Plans, `docs/FAHRZEUGE.md`): Kofferwagen mit Mast (300 Leben, 200 px/s). Rechte Maustaste baut ihn auf (im Stand, 3 s), **R** schaltet die Betriebsart. **PEILEN:** gegnerische Kaempfer und Fahrzeuge im Kreis von 470 Pixeln sind fuer die eigene Seite markiert (Raute, Karte, auch im Nebel) - damit sind sie Ziele fuer den kommenden Werfer. **STOEREN:** im Kreis von 420 Pixeln funken gegnerische Bots nicht, was der Gegner dort markiert hat verfaellt, Spaehdrohnen fallen aus, und kein gegnerischer Nachschub kommt an ("GESTÖRT") - dafuer steht der Funkwagen dabei auf der Karte der Gegner. Aufgebaut hoert er die Bots der eigenen Seite im Kreis von 900 Pixeln: **was sie sehen, geht ins Funknetz** (der Gegner ist fuer alle markiert), nur mit der Regel FUNKSPRUECHE DER BOTS. Kranz am Boden (tuerkis bzw. bernstein, mit Welle), Anzeige der Betriebsart. Nachschub DROPZONE: FUNKWAGEN fuer 7 Punkte, nur Menschen am Steuer. Gemeinsame Grundklasse `Aufbauwagen` fuer Wagen, die man aufbauen muss (auch der Werfer). Testmodus: Spawner FUNKWAGEN und ABWURF: FUNKWAGEN; Pruefungen in `tests/test_spiel.py`. **Netz/LAN: geaendert** - neue Fahrzeugart `funkwagen`, Fahrzeugeintrag Feld 20 (Zusatzwert: Betriebsart); Gastgeber und Gast brauchen 0.34.111. Karten: unveraendert. |
| 0.34.110 | **Spulenwagen** (dritte Stufe des Plans, `docs/FAHRZEUGE.md`): erbeutete Chor-Technik, 480 Leben, 180 px/s. Linke Maustaste: ein **schwacher Kettenblitz** (26 Schaden, springt bis zu viermal weiter). Rechte Maustaste: das **EMP-Feld** - der Wagen muss stehen und wird 2,5 s aufgebaut, dann pulsiert es 10 s am Ort (alle 1,2 s legt ein Puls jedes fremde Fahrzeug im Kreis von 250 Pixeln 2,2 s still, auch Technik wie Selbstschussanlagen), danach muss er 28 s laden (fahren geht, ein neues Feld nicht); erneutes Druecken bricht ab. Eigene Fahrzeuge bleiben verschont. Kranz am Boden (duenn beim Aufbauen, pulsierend mit Restzeit-Bogen) und Anzeige der Phase. Nachschub DROPZONE: SPULENWAGEN fuer 10 Punkte, nur Menschen am Steuer. **Die Nachschubtafel hat jetzt eine Zeile je Eintrag** (was der gewaehlte tut, steht darunter), damit sie auch mit mehr Eintraegen aufs Bild passt. Testmodus: Spawner SPULENWAGEN und ABWURF: SPULENWAGEN; Pruefungen in `tests/test_spiel.py`. **Netz/LAN: geaendert** - neue Fahrzeugart `spulenwagen`, Fahrzeugeintrag Feld 18 (Phase) und 19 (Restzeit); Gastgeber und Gast brauchen 0.34.110. Karten: unveraendert. |
| 0.34.109 | **Skins im Krad und im Jagdpanzer:** der Fahrer des Krads (und der Beifahrer, im Aussehen des Fahrers) und der Kommandant des Jagdpanzers erscheinen in ihrem gewaehlten Aussehen, nicht nur in den Teamfarben. Geprueft ausserdem: die Kanone des Jagdpanzers trifft ein Ziel in 1 300 Pixeln (der Panzer reicht 900), das Zielfernrohr (rechte Maustaste) gilt nur im Jagdpanzer, und die Kamera laeuft damit weit voraus. Pruefungen in `tests/test_spiel.py`. Netz/LAN: unveraendert (Aussehen ging schon ueber das Netz); Gastgeber und Gast sollten trotzdem dieselbe Version haben. Karten: unveraendert. |
| 0.34.108 | **Trosswagen** (zweite Stufe des Plans "Fahrzeuge fuer grosse Karten", `docs/FAHRZEUGE.md`): Nachschub faehrt mit zur Front. Niemand sitzt auf; wer **hinten dransteht** und E drueckt, bekommt Munition (Magazine voll, dazu ein Teil des Vorrats) und ein Medkit - zehn Entnahmen je Wagen, ein Spieler hoechstens alle 4 s, auch am Trosswagen der Gegner (plündern). **Eigene Fahrzeuge, die hinten dranstehen, werden repariert** (14 Leben je Sekunde, 600 je Wagen), auch im Stehen. Fahren wie der Panzerwagen, nur langsamer (210 px/s, 420 Leben); nur Menschen am Steuer, nicht zu kaufen - jede Basis hat einen, und er kommt nach 45 s wieder. Hinweis `[E] NACHSCHUB (n)` hinten am Wagen. Fix aus 0.34.107: Fahr-Bots laufen nicht mehr zum Jagdpanzer. Testmodus: Spawner TROSSWAGEN (OBJEKTE); Pruefungen in `tests/test_spiel.py`. **Netz/LAN: geaendert** - neue Fahrzeugart `trosswagen`, Fahrzeugeintrag Feld 17 (wie viele Entnahmen noch), neue Handlung E hinten am Wagen; Gastgeber und Gast brauchen 0.34.108. Karten: unveraendert. |
| 0.34.107 | **Zwei neue Fahrzeuge fuer die SCHLACHT: Krad und Jagdpanzer** (erste Stufe des Plans "Fahrzeuge fuer grosse Karten"). **Krad:** Motorrad mit Beiwagen, das schnellste Fahrzeug (290 px/s, 180 Leben), faehrt wie der Buggy; **kein Schutz fuer die Insassen** (jeder Treffer kommt bei Fahrer und Beifahrer ganz an), der Fahrer hat keine Waffe, ein Kamerad sitzt mit E im Beiwagen auf und schiesst mit seiner eigenen Waffe (trifft das eigene Krad nicht). Jede Basis bekommt eines dazu, Nachschub DROPZONE: KRAD fuer 3 Punkte. **Jagdpanzer:** Panzer ohne Turm - die Kanone sitzt fest im Bug (Schwenk 12 Grad), reicht 1 400 statt 900 Pixel (190 Schaden, 3,4 s Pause), vorn dicker als der Panzer (Faktor 0,5 statt 0,75), hinten duenner (1,6); kein Bug-MG, kleine Druckwelle (gegen Fahrzeuge, nicht gegen Gruppen); rechte Maustaste: Zielfernrohr. Nur fuer Menschen (Bots steigen nicht ein), Nachschub DROPZONE: JAGDPANZER fuer 10 Punkte. Die Nachschubtafel hat jetzt zehn Zeilen (enger gesetzt). Testmodus: Spawner KRAD, JAGDPANZER (OBJEKTE) und ABWURF: KRAD / JAGDPANZER (NACHSCHUB), Pruefungen in `tests/test_spiel.py`. Neu im Code: `dustfront/art_neue_fahrzeuge.py` (Bilder), Klassen `Krad` und `Jagdpanzer` in `dustfront/fahrzeug.py`, Werte `K.KRAD`, `K.JAGDPANZER`. **Netz/LAN: geaendert** - zwei neue Fahrzeugarten (`krad`, `jagdpanzer`) in der Fahrzeugmeldung, zwei neue Nachschub-Eintraege, Beifahrer im Krad (Feld `besetzt_mit`); Gastgeber und Gast brauchen 0.34.107. Karten: unveraendert. |
| 0.34.106 | **Gerade Fluege rechnet der Gast** (docs/CLIENTSEITE.md Stufe E): jede Kugel (auch Panzergranate) geht nur noch einmal hinaus - Start, Tempo, Uhrzeit des Gastgebers -, statt in jeder Meldung; aendert sie die Richtung (Abprallen), kommt sie neu. Der Gast rechnet die Lage zur Zeit der beiden letzten Meldungen, die Ueberblendung zeigt sie wie bisher - weiter als bis zur letzten bekannten Zeit nie, eine Kugel fliegt also nicht durch eine Mauer. Fehlen Meldungen (Gegendruck, Aussetzer), stimmt die Lage trotzdem. Granaten, Raketen und C4 wie bisher. Gezeichnet wird alles wie bisher. Kugeln kosten je Meldung rund 12 statt 93 Byte; SCHLACHT mit 24 Kaempfern rund 31 statt 39 KB/s je Gast. **Netz/LAN: Protokoll geaendert (Weltmeldung traegt "gs") - Gastgeber und Gast brauchen dieselbe Version.** |
| 0.34.105 | **Treffer-Rueckrechnung** (docs/CLIENTSEITE.md Stufe D): der Gast sagt in jeder Eingabe, welchen Zeitpunkt er gerade sieht ("sz"); der Gastgeber merkt sich, wo alle in der letzten 0,6 s standen, und prueft die Kugeln dieses Gasts gegen die Lage, die er gesehen hat - hoechstens 0,5 s zurueck. Waende gelten wie immer jetzt, Treffer und Statistik entscheidet weiter allein der Gastgeber. Gezeichnet wird alles wie bisher. Gemessen auf einen Gegner, der hin und her laeuft, 129-131 Schuesse: bei 60 ms Ping 46 statt 24 Treffer, bei 150 ms 48 statt 33, bei 300 ms 51 statt 29, bei 400 ms 41 statt 23. Der Preis (wie in jedem Spiel mit Rueckrechnung): wer von einem Gast mit schlechter Leitung beschossen wird, kann noch getroffen werden, obwohl er bei sich gerade hinter die Deckung gelaufen ist - hoechstens 0,5 s lang. **Netz/LAN: Protokoll geaendert (Eingabe traegt "sz") - Gastgeber und Gast brauchen dieselbe Version.** |
| 0.34.104 | **Eingabepuffer beim Gastgeber** (gastseite.WirtTeil): jede Eingabe sagt, wie viele Schritte die vorige beim Gast galt, und der Gastgeber wendet die Bewegung (Laufrichtung, Dash) genau so lange an. Damit stimmt die Vorhersage auch bei schwankender Leitung: gemessen bei 400 ms Ping +-80 ms keine Korrektur mehr, auch nicht beim Dash (vorher bis 30 px). Nur die Bewegung wartet - Zielen, Schiessen, Nachladen, Waffe, Medkit, E und alle anderen Tasten wirken weiter sofort. Die Figur laeuft beim Gastgeber dadurch hoechstens 0-17 ms spaeter los. Der Vorlauf passt sich selbst an, wird in ruhigen Phasen abgebaut und nach einem Haenger sofort auf hoechstens 200 ms gekuerzt (ein Dash darin geht nicht verloren). Im Fahrzeug, am Boden und wo die Vorhersage nicht rechnet, wirkt alles sofort wie bisher. Behoben: die Restdauer eines Dashs kommt gerundet, und schon die Rundung liess den vorhergesagten Stoss einen Schritt zu frueh enden. **Netz/LAN: Protokoll geaendert (Eingabe traegt "es") - Gastgeber und Gast brauchen dieselbe Version.** |
| 0.34.103 | **Der Gast rechnet mit** (docs/CLIENTSEITE.md, Stufen A und B; dustfront/gastseite.py). Die eigene Figur bewegt sich beim Gast sofort - mit derselben Formel wie beim Gastgeber, auch der Dash; jede Weltmeldung wird genau gegen den passenden Punkt der Vorhersage abgeglichen, kleine Abweichungen gleichen sich weich aus. Gemessen mit kuenstlichem Ping: von der Taste bis zur Bewegung rund 50-90 ms statt eines Hin- und Rueckwegs (bei 400 ms Ping vorher 558 ms), am Ende genau dort, wo der Gastgeber die Figur hat. Andere Figuren, Schuesse und Wirkungen spielt der Gast nach der Uhr des Gastgebers gleichmaessig ab, leicht verzoegert (30-150 ms, je nach gemessener Schwankung) - bei schwankender Leitung deutlich ruhiger. Sicherungen fuer schlechtes Internet: ohne Antwort bleibt die Vorhersage nach 0,75 s stehen (kein Zurueckspringen nach einem Aussetzer), im Fahrzeug, am Boden, im Sturz, am Schirm und auf einer anderen Ebene gilt wie bisher der Stand des Gastgebers, der Puffer spielt bei Stau sofort alles ab, und geht die Leitung zu, wird er zuerst geleert (Abbruch und Ende gehen nicht verloren). Eine neue Laufrichtung geht sofort hinaus statt mit dem naechsten Eingabetakt. **Netz/LAN: Protokoll geaendert (Uhrzeit "zt" in jeder Weltmeldung, Eingabenummer "en", dazu "ea", "tv", "lf" im eigenen Spielereintrag) - Gastgeber und Gast brauchen dieselbe Version.** |
| 0.34.102 | **Netz: viel weniger Last.** Gemessen in SCHLACHT mit 24 Kaempfern: vorher gut 1000 KB/s je Gast (18 KB je Weltmeldung, 60 je Sekunde), jetzt rund 40 KB/s; TEAM von 412 auf 8 KB/s. Die Leitung schickt jedem Gast nur, was sich seit seiner letzten Meldung geaendert hat (alle 10 s einmal alles), der Gast setzt die volle Meldung wieder zusammen - das Spiel merkt nichts davon. Weltmeldungen und Eingaben 30 statt 60 je Sekunde (der Gast ueberblendet nach dem gemessenen Abstand, Tastendruecke gehen sofort). Gegendruck: der Gast quittiert in seinen Eingaben die letzte Weltmeldung; sind zu viele unterwegs, faellt die naechste fuer ihn aus (ihre Explosionen und Klaenge kommen mit der folgenden) - kein Stau ueber Sekunden mehr. Auf einer kuenstlich langsamen Leitung: bei 50 KB/s 0,02 s Rueckstand (vorher 24 s), bei 20 KB/s unter 1 s, bei 10 KB/s gut 1 s, und der Gast bleibt verbunden. Behoben: nach einem Haenger kamen viele Weltmeldungen auf einmal, die Leitung galt als kaputt ("Nachricht zu lang") - und der Gast landete in der Lobby. **Netz/LAN: Protokoll geaendert (Weltmeldungen als Aenderungen "dl", Nummer "q", Quittung "wq") - Gastgeber und Gast brauchen dieselbe Version.** |
| 0.34.101 | Neu im NACHSCHUB: **NAPALM-ANGRIFF** (10 P). Erster Klick auf der Karte setzt den Start, der zweite die Richtung; die Bahn ist immer halb so lang wie die Karte hoch und wird schon vor dem zweiten Klick in voller Laenge gezeigt, auch ueber den Zeiger hinaus. Ein Flugzeug, das man nur hoert, wirft unregelmaessig Napalm: einzelne runde Feuer, die 16-24 s brennen, mit Luecken dazwischen - man kommt mit etwas Geschick durch. Bots meiden die Feuer und laufen hinaus. Rechtsklick nimmt den Startpunkt zurueck. Die Nachschubkarte zeigt ohne Wahl keinen Hinweis mehr und keinen Schleier - sie ist auch einfach die Karte. Munitions- und Sanitaetsabwurf kosten 3 statt 2 Punkte, der Buggy 5 statt 4. Feuer in Sicht stehen auf der Nachschubkarte. Schneller: Feuer ausserhalb des Bildes werden nicht mehr gezeichnet, und ab 24 Feuern wurde der Bildpuffer jedes Bild geleert. **Netz/LAN: Gefecht geaendert (Kauf mit zweitem Punkt "x2"/"y2", Weltmeldung "la" fuer die Bahnen, neue Klaenge "jet" und "napalm") - Gastgeber und Gast brauchen dieselbe Version.** |
| 0.34.100 | Minikarte und Nachschubkarte in **Fensteraufloesung** (bei 1080p dreimal so viele Pixel; nur wenn die Grafikkarte nicht selbst skaliert), neues Kartenbild (Boden nach Art, Mauern mit Licht und Schatten, Fels dunkler, Deckung als Quadrat), eigener Pfeil, Punkte mit Rand, runde Karte etwas groesser. NACHSCHUB (TAB) in zwei Schritten: erst links waehlen, dann auf der Karte den Ort; Rechtsklick zurueck. Solange das Menue offen ist, kommt keine Taste mehr ins Spiel (1-7 wechselten vorher nebenbei die Waffe). Mit dem Konto ADMIN gibt es dort den Schalter ALLES GRATIS. Fahrzeuge und Kisten kommen deutlich hoeher herein und sinken wie bisher; sie landen **nie auf etwas**: liegt unten ein Wagen, ein anderer Abwurf oder Fels, treiben sie am Schirm zur naechsten freien Stelle, und wer drunter steht, wird beiseite gestossen (kurz vorher blinkt der Fussabdruck rot). Die Aufklaerungsdrohne ist jetzt ein grosser Starrfluegler mit zwei Triebwerken am Heck, deutlich hoeher (Parallaxe, Schatten); auf der Nachschubkarte liegt Nebel, in ihrem Kreis und um die eigenen Leute nicht. Pings halten 20 s (vorher 15) und markieren auch Fahrzeuge - sie bewegen sich mit, auch im Nebel. Neu: FALLSCHIRMJÄGER (8 P) - fuenf Bots der eigenen Seite im Keil, nicht in Basen; in der Luft tun sie nichts, sehen aber schon; die Gegner sehen sie kommen, schiessen erst nach der Landung und gehen vorher in Deckung. Behoben: der Gastgeber stuerzte ab, wenn die Leitung zu einem haengenden Gast beim Senden zuging. **Netz/LAN: Gefecht geaendert (neue Felder "sh" je Spieler, Feld 16 je Fahrzeug, "gratis" im Kauf) - Gastgeber und Gast brauchen dieselbe Version.** |
| 0.34.99 | Nahkampf und Klassen: Wer vor 0.34.96 eine Nahkampfwaffe (Hammer, Speer, Messer ...) in einem Waffenplatz hatte, verlor sie still - jetzt wandert sie beim Laden auf F, der Platz bekommt eine Waffe der Klasse. NAHKÄMPFER schlaegt auf F 40 % haerter und 25 % schneller zu, SCHILDTRÄGER 15 % haerter, SPÄHER 15 % schneller; das Menue zeigt es. Veraltete Nahkampfwaffen aus den Waffenlisten der Klassen entfernt. NACHSCHUB-Karte: der Sperrkreis um die Feindbasis laeuft nicht mehr ueber den Rand; der Kreis der Aufklaerungsdrohne wird nicht mehr jedes Bild neu gebaut. **Netz/LAN: Gefecht geaendert (Nahkampfschaden der Klassen rechnet der Gastgeber) - Gastgeber und Gast brauchen dieselbe Version.** |
| 0.34.98 | Fehlersuche (Spielgefuehl, Kampf gegen GOAP-Bots, HUD, Menues): In der SCHLACHT blieben Gefallene ohne die Regel AUFHELFEN ewig am Boden - kaum Tode, Runden endeten nie; jetzt laeuft die Bodenzeit ab, und Kameraden koennen bergen. Nachschubpunkte beginnen jede Runde wieder bei 0. AUSRUESTUNG: Klassentext ueberlappte die AUSSEHEN-Zeile, veralteter Hinweis zum Brecheisen entfernt. GRAFIK: "GPU SKALIERT" statt abgeschnittenem Text. **Netz/LAN: Gefecht geaendert (SCHLACHT am Boden, Rundenwechsel) - Gastgeber und Gast brauchen dieselbe Version.** |
| 0.34.97 | Neues Menuebild fuer den REVOLVER (nach dem neu gefassten Prompt). Netz/LAN: unveraendert (nur ein Bild), Gastgeber und Gast sollten trotzdem dieselbe Version haben. |
| 0.34.96 | **SCHLACHT ausgebaut:** neue Karte **STAUBTAL - OFFEN** (grosse offene Wueste, Vorschlag fuer SCHLACHT); Fahrzeuge kommen an **Fallschirmen** in markierte **Dropzonen** an der Basis (Countdown, pulsierend kurz vor dem Abwurf); **Nachschub auf TAB**: mit Punkten (Kill 1, Fahrzeug 5, Aufhelfen 5) Munitions-/Sanitaetsabwurf, einmalige Dropzonen fuer Buggy, Panzerwagen, Panzer auf freiem Gelaende und eine grosse Aufklaerungsdrohne, die Gegner lange markiert; in SCHLACHT hilft man auf. Bots: Lagemeldungen ohne Funk, Front in Abschnitten ab 20 Bots je Seite, sie sitzen auf Panzerwagen auf und werden vor dem Kampf abgesetzt; Fahrzeuge fahren sicherer (Basisfahrzeuge nur, wo der Weg zur Mitte frei ist, besseres Freifahren); Panzer nehmen zuerst Fahrzeuge; viel weniger Panzerjaeger, meist Raketen plus normale Waffe. GOAP ist Vorgabe, FUNKSPRUECHE DER BOTS eine Regel; das Funkgeraet am Fahrzeug zeigt sich nur, wenn wirklich gefunkt wird. **Nahkampf auf F:** Hammer, Speer, Wurfmesser (F wirft), Schockstab, Schlagring, Kettensaege ersetzen das Brecheisen (Loadout NAHKAMPF (F)) statt einen Waffenplatz zu belegen; Brecheisen schwaecher, Hammer langsamer mit weitem Stoss, Speer weiter. **G** wirft sofort eine Granate. Panzerbuechse: Laser bis zum ersten Hindernis, der Schuss geht noch 80 px durch Mauer oder Panzerung. **Zielfernrohr** am Scharfschuetzengewehr (rechte Maustaste). Panzerwagen deutlich wendiger, Buggy ohne Anprallklang, Kanoneneinschlag mit Tiefe (Pilz, Druckwelle, Brocken). Drohne fliegt ueber allem, kreist um ihren Besitzer, stuerzt bei seinem Tod ab. Behoben: Rundentafel laeuft nicht mehr unter die Knoepfe (blaettert), Munition und Granaten nach dem Tod immer voll, Flackern beim langsamen Gehen, Minikarte zeigt die ganze Karte, Ziellinie/Streukegel reichen in den Nebel, Namen ueberlappen nicht. Netz/LAN: **geaendert** - Felder je Spieler `fu`, `nk`, `pk`, Weltmeldung `sl` (Dropzonen, Abwuerfe, Ueberfluege), Nachricht `belohnung`, Regel `funk`; Gastgeber und Gast brauchen 0.34.96; neue Karte staubtal_offen. |
| 0.34.95 | **Neue Spielart SCHLACHT:** zwei Armeen auf STAUBTAL, ROT von links, BLAU von rechts; jede Seite steht sofort mit JE SEITE Kaempfern da (Vorgabe 24, 12 bis 30), fehlende Spieler sind Bots. Gespielt nach Abschuessen (Vorgabe 150) oder Zeit. Jede Basis hat Panzer, Panzerwagen und zwei Buggys, die dort auch wiederkommen; vier Bots je Seite fahren. Bots ohne Gegner im Blick stossen erst zur Mitte, dann zur Basis der anderen vor, zu Fuss und im Fahrzeug (eigenes Wegenetz fuer Fahrzeuge, keine Luecken mehr, in denen ein Panzerwagen haengen bleibt). **Panzerwagen als Truppentransporter:** faehrt ein Kamerad, sitzen bis zu vier Spieler hinten auf (E), E steigt wieder ab; geht der Wagen hoch, fallen sie herunter. **Funkgeraet:** faehrt ein Bot, funkt der Wagen sichtbar (Wellen ueber der Antenne), bis er aussteigt. **Bots:** mehr verschiedene Waffen (MP, Unterhebel, Zwillinge, Doppelflinte, Praezision ...), und in Runden mit Fahrzeugen Panzerjaeger (Panzerbuechse plus Einweg-Raketenwerfer oder Raketenbuendel), die gegen Fahrzeuge zur Panzerabwehr greifen. **Panzerabwehr staerker:** Einweg-Raketenwerfer und Raketenbuendel (jetzt Hohlladungen) wirken vom Blech aus gemessen und mit eigenem Fahrzeugschaden, die Panzerbuechse macht mehr; der Panzerwagen haelt weniger aus (das Leben bleibt, Kugeln prallen weiter ab). **Flammenwerfer** wieder wie im Waffenpaket: eine Feuerzunge aus verschmelzenden Hitzeflecken statt Funken. **Spaehdrohne:** weiter Kreis (230 statt 90), sieht 340 weit; was sie markiert, steht fuer die eigene Seite als rote Raute im Bild (auch im Nebel und Rauch) und auf der Minikarte, und Markierungen laufen jetzt ab. **Weniger Nebel:** bis Zoom 1,5 ist alles klar. **Behoben:** Ruckeln von Gelaende und Figur beim Laufen (Kamera zwischen den Rechenschritten), und ein Druck auf eine Hotbar-Taste oder X zaehlte bei mehreren Rechenschritten im Bild doppelt (Waffen und Werkzeuge wurden uebersprungen). Netz/LAN: **geaendert** - neue Spielart und Regel `schlacht_seite`, Feld `mf` je Spieler (markiert fuer), Fahrzeugeintrag Feld 15 (wie viele aufsitzen), anderer Schaden an Fahrzeugen; Gastgeber und Gast brauchen 0.34.95. |
| 0.34.94 | **Beliebig viele Loadouts** (AUSRÜSTUNG: NEUER SATZ, LÖSCHEN), Namen frei waehlbar (NAME, bis 16 Zeichen, alles, was die Schrift zeigen kann); die Kontoseite behaelt beim Speichern alle Saetze samt Klasse und dritter Waffe. Bots ziehen das MG nur noch selten (der eine MG-Schuetze in GEMISCHT bleibt). Fahrzeuge ohne 3D. Anzeige: Faehigkeitsname in Bernstein, etwas weiter rechts oben; Loadout-Name etwas hoeher; Felder Brecheisen/Medkit groesser, Symbole passen immer hinein. Tests: die Verhaltensszenen laufen gleichzeitig auf allen Kernen (rund 4x schneller, gleiche Ergebnisse). Netz/LAN: unveraendert. |
| 0.34.93 | Anzeige verfeinert: die Ringe um Karte und Faehigkeit liegen direkt an, ohne Luecken (Platten nur durch feine Striche getrennt), etwas dicker. Neben der Hotbar, mit Abstand, ein Feld fuer das Brecheisen (F) und eines fuer Medkits (H, mit Zahl), je mit Symbol. Der grosse Waffenkasten unten rechts ist weg: das Magazin steht gross rechts unter dem Zeiger (gelb, wenn knapp, rot blinkend, wenn leer, Balken beim Nachladen; nach dem Wechsel kurz der Name). Nach dem Benutzen der Faehigkeit steht im Kreis ein grauer Countdown statt C. Netz/LAN: unveraendert. |
| 0.34.92 | **Neue Anzeige im Gefecht** (nach Skizze): oben links die Uhr (PVE: Welle), oben in der Mitte der Mannschaftsstand als geteilter Balken mit den Zahlen darunter, oben rechts die Ebenen wie bisher. Unten links die Minikarte als Kreis um die eigene Figur, die Panzerung als Bogen darum (in Platten wie vorher), daneben der Kreis der Faehigkeit (C) mit den Dashes als Bogen und den Medkits. Hotbar und Waffe wie bisher. Der Punktestand, Spielart und Karte stehen jetzt auf einer Tafel, solange TAB gehalten wird (Taste INVENTAR / PUNKTE). Werte unveraendert. Netz/LAN: unveraendert. |
| 0.34.91 | **Hauptwaffe und Seitenwaffe.** Jeder Satz hat eine Haupt- und eine Seitenwaffe (Pistolen, Werkzeug, leichter Nahkampf); Unterstuetzer, Pionier, Panzerjaeger, Grenadier, Flammentrupp, Nahkaempfer und Techniker haben dazu einen Platz fuer eine Spezialwaffe (Minigun, Raketen, Werfer, Flammenwerfer, Kettensaege, Speer, Spule, Kugelblitz), der Schildtraeger nur die Seitenwaffe. Alte Saetze werden umgestellt (aus der zweiten Hauptwaffe wird eine Seitenwaffe). Neue Regel **KLASSE PFLICHT** (Vorgabe an): mit Loadouts spielt jeder eine Klasse, wer ohne kommt, spielt SCHUETZE. Sturmgewehr streut mehr (3,0/4,6 statt 2,2/3,6), Schrot 11,5 statt 13 je Kugel. Testmodus: NEBEL als Vorgabe aus. Bots: ruhiger zielen beim Laden der Spule, Drehbremse ohne Gegner. **Netz/Gefecht: Gastgeber und Gast brauchen 0.34.91** (Regel und Loadouts). |
| 0.34.90 | **GRAFIKKARTE SKALIERT** (Einstellungen > Anzeige, aus als Vorgabe): die Grafikkarte vergroessert das 640x360-Bild aufs Fenster (pygame.SCALED) statt des Prozessors - spart bei grossen Fenstern und im Vollbild die meiste Zeit des Vergroesserns. Pixelraster gilt weiter (GANZE PIXEL: nur ganze Faktoren im Fenster, OHNE FLIMMERN: geglaettet). Ohne schnelle Grafikkarte, mit Touch-Steuerung und auf iOS bleibt es von selbst beim alten Weg; auf sehr schwachen Grafikchips einfach ausschalten. Netz/LAN: unveraendert. |
| 0.34.89 | **Leistungsrunde ohne Spielaenderung** (Spielzustand und Bild bitgenau wie vorher, gemessen an drei Szenen): gemessen etwa 10 % schneller im Team-Gefecht und in PVE, gut 6 % in der grossen Testmodus-Schlacht. Figuren ausserhalb des Bildes werden nicht mehr gezeichnet, der Ziffernblock des Testmodus ist eine gemerkte Flaeche, `deckung` antwortet bei freien kurzen Strecken sofort, die Gegnerliste der Bots wird je Durchgang einmal gesucht, die JEDER-HAT-ALLES-Hotbar merkt ihre Gruppen, Kamera.zu_bild rechnet ohne Zwischenvektoren. Netz/LAN: unveraendert. |
| 0.34.88 | Testmodus: der Beobachter hat immer eine Minikarte (MINIKARTE ALLWISSEND legt fest, ob jeder darauf ist); in ANSICHT WIE RUNDE nimmt der unsichtbare Ziffernblock weder Finger noch Mausklick weg. Netz/LAN: unveraendert. |
| 0.34.87 | **Waffen-Feinschliff.** Spulengewehr abgeschwaecht: 95 statt 150 Schaden, 2,1 s Laden, 3 Schuss, 760 Reichweite, und jede Mauer (-40 %) und jeder Koerper (-35 %) auf der Linie kostet Kraft; Ladelinie und Strahl werden ueber den Mauern gezeichnet. Revolver: GEZIELT praeziser, FAECHERN leert die restliche Trommel mit einem Klick; der Gast sieht die Betriebsart ("mo"), und beim Umschalten steht ein Hinweis da. Gruppen-Hotbar: die Taste wird sofort in eine Waffe umgerechnet, und eine angeforderte Waffe zaehlt als gehalten, bis der Gastgeber sie bestaetigt - so ist jede Waffe einer Gruppe erreichbar, auch bei schnellem Druecken als Gast; WFF (Touch) geht von Gruppe zu Gruppe. Kuller rollt 1,6-mal so weit wie gezielt und zuendet nach 6,5 statt 9 s. Granatwerfer fliegt ueber alles, was niedriger steht als seine Flughoehe (Mauer 24, Fels 30; `Welt.kachel_hoehe`), fliegt etwas langsamer (340 statt 400) und zuendet am Boden nach 0,4 statt 0,7 s. Drohne: echter Rotorklang (vier verstimmte Rotoren, Luft im Blatttakt, gleich laut). **Netz:** neues Feld "mo" je Spieler; gleiche Version noetig. |
| 0.34.86 | **Schild: Durchschlag.** Starke Waffen gehen teilweise durchs Schild, mit eigenem Klang `schild_durch` (`K.SCHILD["durchschlag"]`: Panzerbuechse 70 %, Spule 75 %, Scharfschuetze 45 %, Bolzer 50 %, Praezision 30 %, Revolver und Unterhebel 15 %; alles Panzerbrechende wie die Kanone wenigstens 70 %); sonst bleibt es bei 7 % und dem Abprallen. Die Waffe geht dazu mit dem Treffer mit (`entities.schaden_an(..., waffe=)`). **Insassen im neuen Stil:** wer ohne eigenes Aussehen im Buggy, im Panzerturm oder im Ring des Panzerwagens sitzt, ist jetzt die Standardfigur von 0.34.77 (Helm, Weste, Tarnung) statt der alten. Netz: unveraendert (beides rechnet bzw. zeichnet jeder selbst). |
| 0.34.85 | **JEDER HAT ALLES heisst jetzt wirklich alles.** Statt der zehn alten Waffen traegt man alle 41 (ohne Brecheisen, das auf F liegt, und den Raketenwerfer von der Karte), in neun Gruppen (`K.ALLES_GRUPPEN`): 1 Gewehre, 2 Pistolen/MP, 3 Schrot, 4 MG, 5 Schwer, 6 Energie, 7 Nahkampf, 8 Granaten, 9 Sprengstoff. Eine Zahl waehlt die Gruppe, noch einmal gedrueckt die naechste Waffe darin; zurueck in eine Gruppe kommt die, die man dort zuletzt hatte. Die Hotbar zeigt neun Felder mit Punkten fuer die Waffen der Gruppe. Dazu **jedes Werkzeug auf C** (`K.WERKZEUGE`: Sandsackwand, Munitionskiste, Sanitasche, Stacheldraht, Sprengfalle, Kraehenfuesse, Kanister, Horchposten, Drohne, Selbstschussanlage), neue Taste **X** schaltet weiter, jedes mit eigener Pause. Die Regel heisst FAEHIGKEITEN / WERKZEUGE und gilt auch ohne Loadouts. Ohne Konto bekommt man in EIGENES LOADOUT ebenfalls alles. **Netz:** gleiche Version noetig; je Spieler gehen "aw"/"wz" (Werkzeug) mit, und die Waffenlisten ("wl", "ml", "vl") sind laenger. |
| 0.34.84 | **Bots im Fahrzeug, nach einer grossen Fahrzeugschlacht.** Einsteigen: sie gehen an die Seite des Wagens (beim Panzerwagen reicht die Front ueber den Einstiegsradius, wer vorn stand, blieb haengen) und steigen auch ein, wenn sie einen Gegner sehen, solange der Wagen nah ist (`K.BOTS["fahren"]["einstieg_..."]`). Fahren: Bots lenken selbst (`bots._lenken`, Eingabe "gl", nur fuer Bots): liegt das Ziel hinten und weiter weg als 140 px, wenden sie vorwaerts statt rueckwaerts zu fahren; der Panzer dreht auf der Stelle; "festgefahren" misst den Weg statt das Tempo. Kanone: feuert, sobald der Einschlag nah genug am Ziel liegt (explosiv), auch auf einen, der eben hinter Deckung verschwand, wenn die Granate bis dicht an ihn kommt; Zielwechsel im Fahrzeug selten (kein Wechsel bei Treffern, Drehweg des Turms zaehlt). Bug-MG: ein haltender Panzer dreht die Wanne zum Gegner. Neu: Panzer und Panzerwagen (nicht der Buggy) fahren zwischen einen liegenden Kameraden und den Gegner, wenn sie geradewegs hinkommen; Testmodus INFO zeigt "DECKT LIEGENDEN". Netz: Bots rechnet nur der Gastgeber; das neue Feld "gl" nimmt der Gastgeber nur von Bots an. |
| 0.34.83 | Die drei fehlenden Menuebilder sind da (`assets/menue/stacheldraht.jpg`, `horchposten.jpg`, `raketenbuendel.jpg`) - alle 57 Waffen und Gegenstaende haben jetzt eines. Netz/LAN: unveraendert. |
| 0.34.82 | **Menue AUSRUESTUNG mit grossen Waffenbildern.** Die 54 Bilder aus dem Bildgenerator (Prompts in `docs/BILDPROMPTS.md`, ueber Google Takeout geholt) liegen verkleinert als `assets/menue/<kennung>.jpg` (zusammen 1,5 MB); rechts im Menue erscheint das Bild der gewaehlten Waffe oder Wurfwaffe (`dustfront/menuebilder.py`, `K.MENUEBILDER`). Fehlt eine Datei (Stacheldraht, Horchposten, Raketenbuendel - dort hat der Generator nichts geliefert), bleibt es beim Pixelbild. Im Spiel selbst aendert sich nichts. Netz/LAN: unveraendert. |
| 0.34.81 | `docs/BILDPROMPTS.md`: jeder Prompt komplett zum Kopieren (Stil, Motiv, was zu vermeiden ist und Format in einem Block) - nichts mehr zusammensetzen. Sonst nichts geaendert; Netz/LAN: unveraendert. |
| 0.34.80 | **Bots vergessen Gegner nicht mehr so schnell, gehen um Feuer herum, Feuerschutz fuer den Retter.** Wer einen Gegner aus dem Blick verliert, behaelt seine letzte Stelle als **Spur** (45 s, `K.BOTS["spur_..."]`) und sieht dort nach, sobald nichts anderes los ist - langsam und mit dem Blick darauf, je nach Mut (Draufgaenger ab 0,8 in vollem Tempo); was einer geprueft hat, gilt fuer die Kameraden daneben, im Trupp fuehrt der Anfuehrer hin. Trupp-Gedaechtnis 6 -> 12 s. Liegt Feuer, Gas, Draht oder eine sichtbare Falle auf dem Weg, geht der Bot aussen herum (`_um_gefahr`, bleibt bei seiner Seite) statt hinein und rueckwaerts wieder heraus. Feuerschutz beim Bergen: zuerst der Gegner mit freier Linie auf den Retter. Testmodus INFO zeigt die Spuren (Kreuze, gestrichelt die naechste). Neu: `docs/BILDPROMPTS.md`, Prompts fuer einen Bildgenerator fuer alle Waffen und Gegenstaende. Netz: unveraendert; im Gefecht verhalten sich die Bots so (rechnet der Gastgeber). |
| 0.34.79 | **Menues aufgeraeumt, Klassen und neue Waffen in der Lobby.** Hauptmenue neu: SPIELEN (Einzelspieler, Mehrspieler, Testmodus), dann AUSRUESTUNG, KONTO, EINSTELLUNGEN, SO SPIELST DU, BEENDEN - rechts zu jedem Punkt eine Erklaerkarte fuer Neue. Weg sind FORTSETZEN und Region/Schwierigkeit/Rufzeichen (wertete das Spiel nie aus) und die eigene Optionsseite: EINSTELLUNGEN, AUSRUESTUNG und KONTO oeffnen jetzt die Menues des Spiels, Roehrenbild, Intro und Menue-Brummen stehen dort (GRAFIK/AUDIO). Einstellungen ohne graue NICHT-VERFUEGBAR-Zeilen, der Erklaerkasten zeigt alle Zeilen. AUSRUESTUNG erklaert rechts die gewaehlte Klasse (Vorteile, Faehigkeit) bzw. Waffe (Werte, welche Klassen sie haben). Pause mit Erklaerung je Eintrag, AUFGEBEN heisst ZUM HAUPTMENUE / SPIEL BEENDEN; das Inventar heisst INVENTAR und zeigt statt leerer Panzerungsplaetze Leben, Medkits, Klasse. **Netz/Gefecht:** in der Lobby traegt jeder seinen Satz (Klasse, zwei Waffen, Wurfwaffe - auch die neuen) und eine Aenderung gilt dort sofort; neue Regel KLASSEN-FAEHIGKEITEN (an, nur mit Loadouts): Taste C wirkt auch im Gefecht, das Hingelegte geht als "geraete" an die Gaeste, dazu "kl" und "fh" je Spieler; Anzeige [C] ueber dem Lebensbalken. Gastgeber und Gast brauchen 0.34.79. |
| 0.34.78 | **Fenster rastet auf ganze Vielfache ein, PIXELRASTER OHNE FLIMMERN.** Liegt das Fenster bis 4 % neben einem ganzen Vielfachen von 640 x 360 (etwa 1919 x 1079), wird genau 3x vergroessert und der Rest abgeschnitten (`K.FENSTER_EINRASTEN`) - bei krummen Faktoren zeigte das Bild manche Pixelreihen doppelt statt dreifach, und beim Umschauen wurden Sandrillen dicker und duenner. Neu in GRAFIK, PIXELRASTER: FUELLT, OHNE FLIMMERN - fuer wirklich krumme Groessen (1440 x 900): erst ganzzahlig vergroessern, dann weich verkleinern; kostet einige Millisekunden je Bild. Nachgestellt mit den gemeldeten Bildern (hineingezoomt, Zoom 0,75): seit 0.34.77 aendert sich dort beim Umschauen kein Pixel mehr der Textur. Netz/LAN: unveraendert. |
| 0.34.77 | **Standardfigur im neuen Stil, kein Flimmern, Schild und Fahrzeug schuetzen mehr, Testmodus wie eine Runde.** Die Standardfigur (neutral, ROT, BLAU, mit jeder Waffe und im Schlag) wird jetzt wie die Skins gezeichnet: dieselben Farben, dazu Tarnflecken, Plattenweste, Helm mit Schutzbrille und die Neon-Markierung der Mannschaft. **Kein Flimmern mehr** (gemeldet: Gestruepp und anderes veraenderte beim Umschauen die Textur): die Etage darueber und darunter und das Bild beim Zoomen werden jetzt auf einem Raster abgetastet, das an der Welt haengt - die Textur bewegt sich nur noch, statt sich zu veraendern; Mauer-, Fels- und Kistendeckel haben eine feste Groesse und werden nur zugeschnitten. Schildtraeger: von vorn kommen 7 % statt 15 % an. **Im Fahrzeug gibt es keinen Schaden mehr** - weder Treffer am Wagen noch an der Figur (`K.FAHRZEUG["fahrer_geschuetzt"]`); geht der Wagen hoch, ist man draussen und bekommt wie bisher etwas ab. Panzer ohne Fahrer: liess sich mit Zeit, Bots, Mauern, Kanten und allen Zeitfaktoren nicht zum Zittern bringen - wahrscheinlich war es das Flimmern; ein Test haelt jetzt fest, dass er still steht. Testmodus: ANSICHT WIE RUNDE (Taste F2), MINIKARTE ALLWISSEND, NACHSCHUB AM KARTENRAND (docs/TESTMODUS.md). Netz/LAN: **geaendert** in der Wirkung - der Gastgeber rechnet den Schaden, Gaeste brauchen trotzdem dieselbe Version. |
| 0.34.76 | **Noch etwas schneller, wieder ohne Aenderung.** Gleiche Pruefsummen ueber Spielzustand und Bild wie 0.34.74. Zusammen mit 0.34.75 gegenueber 0.34.74 (STAUBTAL, TEAM 12 Bots / PVE / Testmodus-Schlacht 36 Bots): Rechenarbeit je Bild -38 % / -35 % / -20 %, Bilder je Sekunde am Server +36 % / +39 % / +11 % (mit dem Hochskalieren aufs Fenster, das gleich teuer bleibt). Neu: Schrift und Schatten in einem Blit, die Etage darueber wird leer auch nicht mehr ausgestanzt, gemerktes Bild fuer die Ueberblendung im Format des Bildes, Kollision stehender Buggys je Kreis gemerkt, MVP-Punkte der Anzeige nur neu, wenn sich ihre Werte aendern (`bestenliste.MVP_NAMEN`), Kollision ohne Umweg ueber `ebene()`, Bots ohne bekannte Gefahr pruefen keine. Tests im Abschnitt "Schneller, aber dasselbe". Netz/LAN: unveraendert. |
| 0.34.75 | **Schneller, ohne dass sich etwas aendert.** Gleiche Rechnung, gleiche Pixel - gemessen mit Pruefsumme ueber den ganzen Spielzustand und das Bild, Bild fuer Bild gleich. Gemessen auf STAUBTAL (TEAM mit 12 Bots, PVE, Testmodus-Schlacht mit 36 Bots, Panzer, Feuer, Rauch): Rechenarbeit je Bild (Instruktionen) -38 % / -35 % / -20 %, Bilder je Sekunde am Server +35 % / +44 % / +22 %. Zeichnen: Mauerseiten und -deckel je Spalte und Zeile statt je Kachel gerechnet, Schatten, Deckel und Figurenschichten in einem Aufruf (`fblits`), ganz deckende Bodenstuecke und Deckel ohne Alphakanal, Bodenstuecke mit Loechern als Flaeche mit Farbschluessel (RLE), Klippen nur nahe am Bild, die Etage darueber nur, wenn dort etwas zu sehen ist, Vignette nur am Rand, Anzeige-Kaesten und Minikartengrund gemerkt. Rechnen: Nachbarsuche ueber belegte Zellen, Kollision mit fertiger Kacheltafel, Physik und Kachelfrage stehender Fahrzeuge gemerkt, GOAP-Ausdruecke mit gemeinsamer Namenstafel, Waffenwerte ohne Kopie, wo nur gelesen wird. Test im Abschnitt "Schneller, aber dasselbe". Netz/LAN: unveraendert. |
| 0.34.74 | **Rauch ohne schwarzes Viereck.** Auf einem Intel-Mac stand jede Rauchwolke auf einem schwarzen Quadrat (gemeldet mit Bild). Die Wolke ist das einzige Bild, das aus rohen Bytes (RGBA) gebaut wird; jetzt wird sie ins Format des Fensters umgewandelt (`convert_alpha`), wie alle anderen Bilder. Netz/LAN: unveraendert. |
| 0.34.73 | **Balancing und Klassen.** Balancing (gemessen gegen das Sturmgewehr, `tests/test_spiel.py` "Balancing"): Minigun 12 -> 9 (300 Schaden je Sekunde bei voller Drehzahl), Autoschrot 9 -> 7, Doppelflinte 15 -> 11 je Kugel (ein Lauf toetete aus der Naehe), Panzerbuechse gegen Figuren 120 -> 70 und gegen Fahrzeuge 160 (sie toetete auf 1600 px mit einem Schuss), Praezisionsgewehr 38 -> 34 und Reichweite 1200 -> 900, Kugelblitz 13 -> 18 je Blitz; die Pistole bleibt, wie sie ist. **Klassen** (`K.KLASSEN`, `dustfront/klassen.py`): 13 Klassen - Schuetze, Sanitaeter, Unterstuetzer, Scharfschuetze, Pionier, Panzerjaeger, Grenadier, Flammentrupp, Spaeher, Nahkaempfer, Techniker, Schildtraeger, Fahrer -, jede mit eigener Auswahl an Waffen und Wurfwaffen (nicht alle) und Vorteilen (Leben, Tempo, Nachladen, Abkuehlen, Feuerschutz, Schaden an Fahrzeugen, Fahrzeugschutz, schnelleres Aufhelfen, Medkit, Granate mehr, Schild). In AUSRUESTUNG waehlt jeder Satz seine Klasse; FREI ist die alte Ausruestung ohne Klasse, alle gespeicherten Saetze bleiben gueltig. Neue Taste **C (FAEHIGKEIT)**: die Faehigkeit der Klasse (Sanitasche, Munitionskiste, Selbstschussanlage, Sprengfalle, Sandsackwand, Kraehenfuesse, Drohne, Horchposten, Stacheldraht, Kanister) - wie Bauen und Fallen erst im Testmodus; im Gefecht wirken die Vorteile. Netz/LAN: **geaendert** - der Satz traegt `klasse`, je Spieler das Feld `lm` (Hoechstleben), neuer Druck `faehigkeit`. |
| 0.34.72 | **Klaenge fuer alles Neue** (gemeldet: "Klaenge kannst du mal alle erzeugen"). 33 eigene Platzhalter in `audio.py`: die Schusswaffen aus dem Paket (Revolver, MP, Minigun, Panzerbuechse, Doppelflinte, Granatwerfer, Bolzer, Nagler), die Chor-Waffen (Spule mit Ladesummen, Kettenblitz, Spiegellaser, Kugelblitz, Plasma), Flammenwerfer, Kettensaege, Bodenschlag, Schockstab, Schlagring, der Knaller (ganz neue Boeller, wie im Paket verlangt), EMP, Piepen der Haftladung und EMP-Granate, Ankleben, Gas, Schneeball, Wurfmesser, Naegel, Sprengfalle, Drohne, Horchposten, Fahrzeug faellt aus, Reifen platzt, Kugel am Schild. Vorher liehen sie sich Klaenge alter Waffen. Aufnahmen in `assets/sfx/<name>/` gehen vor (Liste in `assets/sfx/LIESMICH.md`). Netz/LAN: **geaendert** - 15 neue Namen in den Klaengen, die der Gastgeber meldet (`NETZKLAENGE`). |
| 0.34.71 | **Bots am Steuer, Schildtraeger, Trupp-Vorlagen - im Testmodus.** Ein Bot, dem der Testmodus es erlaubt, faehrt Panzer, Panzerwagen oder Buggy: er faehrt zum Gegner (oder auf Streife), haelt seinen Abstand, dreht Turm bzw. Ring, schiesst mit Kanone, Bug-MG oder Ring-MG, setzt zurueck, wenn er feststeckt, und steigt aus, bevor der Wagen hochgeht; aus dem Fahrzeug sieht er weiter (Panzer 720 px). Ein Fahrer ohne Fahrzeug geht zum naechsten freien und steigt ein. Im Gefecht fahren Bots weiter nicht (so gemeldet). Der **Schildtraeger** haelt von vorn 85 % ab, ist langsamer und traegt eine Pistole. **Trupp-Vorlagen**: PANZERZUG (Panzer mit Fahrer, Offizier, Grenadier mit Granatwerfer, Pionier mit Haftladung, MG), MOT. SCHUETZEN (Panzerwagen), SCHILDWALL (zwei Schildtraeger), SPAEHTRUPP (Buggy, EMP), STURMTRUPP (mit Flammenwerfer) - jedes Mitglied in seinem eigenen Aussehen; der Standard-Trupp bleibt. Netz/LAN: unveraendert. |
| 0.34.70 | **Bots erkennen Gefahren und kaempfen mit allen Waffen.** Bots (klassisch und GOAP) sehen brennenden Boden (Molotow, Flammenwerfer, Kanister), Gaswolken, Sprengfallen, die sie entdeckt haben, Stacheldraht und scharfe Wuerfe: sie laufen nicht hinein, sondern herum, und wer drinsteht, geht zuerst heraus (gemessen in drei Schlachten mit brennendem Boden: 0,3 % statt 3,9 % der Zeit im Feuer). Blendgranate, Betaeubung, Kaelte und Festnageln wirkten schon und wirken weiter. Mit jeder Waffe aus dem Paket kann ein Bot jetzt kaempfen: mit Nahkampfwaffen geht er heran und schlaegt zu, die Spule laedt er voll und laesst dann los, den Kettenblitz haelt er, bis er springt, den Flammenwerfer nutzt er nur in Reichweite; Chor-Waffen kuehlen ab, Werfer und Flammenwerfer laedt er nach. Woraus Bots im Gefecht ihr Loadout ziehen, bleibt wie bisher (die Klassen kommen spaeter); im Testmodus gibt WAFFE ihnen jede. Netz/LAN: unveraendert (Bots rechnet der Gastgeber), aber das Verhalten der Bots im Gefecht aendert sich. |
| 0.34.69 | **Bauen, Fallen, Aufklaerung, Sanitasche und Munitionskiste - erst im Testmodus** (gemeldet: "erstmal nur fuer den Testmodus", `dustfront/ausruestung.py`). Spawner-Gruppen BAUEN (Sandsackwand: haelt Kugeln, bis sie zerfaellt; Stacheldraht: langsam und blutig), FALLEN (Sprengfalle mit Druckplatte oder Draht: versteckt, nur aus der Naehe zu sehen, ein Augenblick zum Wegspringen, ein Schlag mit dem Brecheisen entschaerft sie; Selbstschussanlage; Benzinkanister), AUFKLAERUNG (Spaehdrohne kreist und markiert, Horchposten hoert Bewegung durch Waende) und HILFE (Sanitasche heilt ueber 5 s, stehende Munitionskiste fuellt die Waffen). Im Testmenue das FERNGLAS: die gesteuerte Figur markiert im Kegel zum Mauszeiger. Markierte Gegner tragen eine rote Raute; INFO zeigt versteckte Fallen und Reichweiten. Der EMP legt Geschuetz und Horchposten still und holt die Drohne herunter. Netz/LAN: unveraendert - im Gefecht kommt nichts davon vor. |
| 0.34.68 | **Energiewaffen des Chors und der Flammenwerfer.** Neu waehlbar: **Spulengewehr** (halten laedt auf, die Linie sehen alle; loslassen feuert einen Strahl ohne Flugzeit durch Waende und jeden Koerper, voll geladen 150), **Kettenblitz** (kurz laden, dann springt der Blitz bis zu fuenfmal von Koerper zu Koerper, jedesmal schwaecher), **Spiegellaser** (prallt dreimal an Waenden ab, jedesmal 40 % staerker), **Kugelblitz** (eine langsame Kugel, die unterwegs Blitze in alle Richtungen schlaegt und am Ende tuerkis platzt) und **Flammenwerfer** (Feuerstrom im Kegel, brennende Streifen am Boden, frisst Rauch; wer mit vollem Tank faellt, dessen Tank geht hoch). Die Chor-Waffen werden heiss statt leer: in Ruhe kuehlen sie Ladung um Ladung ab, ganz leer ueberhitzen sie. Netz/LAN: **geaendert** - Wirkung `b` (Strahl und Blitz), Feld `ld` (Ladung) je Spieler, Explosionsart `plasma`, Bilder `laser_flug` und `kugelblitz_flug`, der Flammenwerfer als Schussknall. |
| 0.34.67 | **Wuerfe aus dem Waffenpaket.** Neu waehlbar: **Gasgranate** (eine gelbgruene Wolke, die langsam waechst und Figuren schadet - Zombies atmen nicht), **Kuller** (gerade gerollt, zuendet, sobald jemand nahe kommt), **Knaller** (knallt sechs Sekunden wie ein Gefecht, Bots hoeren hin und sehen nach), **Schneeball** (fliegt gerade, drei Treffer in vier Sekunden frieren ein), **Wurfmesser** (lautlos; links stechen, rechts werfen) und **Speer** (weiter Stoss, rechts werfen) - geworfen bleiben beide liegen, bis man darueberlaeuft, nach 45 s kommen sie von selbst zurueck. Haftladung und EMP-Granate nach dem Paket: weiterer Wurf, spaetere Zuendung (5 s bzw. 2 s), sie blinken immer schneller; der EMP reicht weiter (130). Netz/LAN: **geaendert** - neue Liste `gas` in der Welt-Meldung, neue Bilder im Flug (`wurfmesser_flug`, `speer_flug`, `schneeball_flug`, `gas_flug`, `teil_kuller_wurf`, `teil_knaller_wurf`, `haftladung_flug_an`, `emp_flug_an`), Schussknall `knaller`. |
| 0.34.66 | **Nahkampfwaffen, Bolzer, Nagler, Zustaende.** Neu waehlbar (Ausruestung, Testmodus): **Vorschlaghammer** (links ein schwerer Schlag, rechts ein Bodenschlag, der ringsum alles wegstoesst), **Schockstab** (wenig Schaden, betaeubt 1,4 s: kein Laufen, kein Schiessen), **Schlagring** (sehr schnell, aus dem Dash heraus 2,6-fach), **Kettensaege** (Dauerschaden, haelt fest, laut - Bots hoeren sie -, braucht Treibstoff), **Bolzenschussgeraet** (nur aus naechster Naehe, sehr stark, durch niedrige Deckung) und **Nagler** (langsame Naegel; wer vor einer Wand getroffen wird, haengt fest; die Naegel bleiben stecken). Dazu Zustaende fuer alle Figuren und Gegner: betaeubt, gefroren, fest (`K.ZUSTAENDE`, Bosse halten nur die Haelfte aus), ueber der Figur zu sehen. Korrektur: Nagelfelder (Nagelstreuer) wirken nur noch auf Reifen, nicht auf Wesen - so hat es der Besitzer fuer die Kraehenfuesse festgelegt. Netz/LAN: **geaendert** - Feld `zs` (Zustaende) je Spieler, Explosionsarten `nagel` und `boden`, Bild `nagel_flug`. |
| 0.34.65 | **Fahrzeuge: Panzerung, Schadensarten, Lebenspunkte, Haftladung, EMP, Hecknebel, Nagelstreuer.** Jeder Treffer an einem Fahrzeug hat eine Art - Kugel, panzerbrechend, Spreng, Hohlladung, Feuer, Nahkampf, Rammen -, und jede Fahrzeugart nimmt davon ihren Anteil (`K.PANZERUNG`): eine Kugel zerkratzt den Panzer nur, eine Hohlladung geht durch, Feuer macht Blech wenig. Hinten ist das Blech duenner als vorn (`K.PANZER_SEITEN`). Neue Lebenspunkte: Buggy 380, Panzerwagen 620, Panzer 950. Raketen, C4 und die neue **Haftladung** sind Hohlladungen; die Haftladung klebt an allem, was sie im Flug beruehrt, und faehrt mit. Die neue **EMP-Granate** legt jedes Fahrzeug im Kreis fuer 4,5 s still (kein Gas, keine Lenkung, Turm und Waffen schweigen), ohne Schaden. Beide sind in der Ausruestung waehlbar. Am Steuer wirft **R** einen **Hecknebel** (alle Fahrzeuge) und **F** den **Nagelstreuer** (Buggy, Panzerwagen): ein Nagelfeld, in dem Reifen platt gehen (langsam, Schaden) und Figuren langsam werden und bluten; Ketten rollen darueber. Je zwei Ladungen pro Leben des Wagens. Testmodus: Haftladung, EMP-Granate und NAGELFELD im Spawner, die INFO-Ansicht zeigt bei Fahrzeugen Leben, den letzten Treffer (Art, Seite, Anteil), EMP, platte Reifen und Ladungen. Netz/LAN: **geaendert** - neue Liste `naegel` in der Welt-Meldung, ein 15. Feld (EMP) je Fahrzeug, neue Bilder `haftladung_flug`, `emp_flug`, `nagel` und die Explosionsart `emp`. |
| 0.34.64 | **Granatwerfer-Bogen nach oben, erkennbare Raketen, Explosionsblitze, Buggy-Treffer.** Die Granate des Granatwerfers stieg im Bild nach unten (gemeldet); jetzt steht sie umso hoeher im Bild, je hoeher sie fliegt (`K.BOGEN`), und wird dabei groesser. Die Raketen des Raketenbuendels fliegen als eigenes Bild mit Flossen und Flamme (`minirakete_flug`) und explodieren als eigene Art `klein` (Funkenkranz, Ring, Brandfleck). Jede Explosion blitzt kurz hell auf (`K.LICHTBLITZ`), auch beim Gast. Ein Buggy wird an seiner ganzen Laenge getroffen, nicht nur 13 Pixel um die Mitte - ein fahrender Buggy war sonst kaum zu treffen (gefunden in einer Aufnahme). Netz/LAN: **geaendert** - neues Bild im Flug (`minirakete_flug`) und neue Explosionsart `klein` in der Wirkung `x`. |
| 0.34.63 | **Testmodus auf iPhone und iPad, und ein Skript, das die App vom Mac aufs Geraet bringt.** Der Testmodus steht jetzt auch auf iOS im Hauptmenue: der Ziffernblock wird angetippt (ein Finger darauf wird nie ein Stick), der linke Stick fliegt den Beobachter, der rechte bewegt den Zeiger; Spawner und Testmenue gehen mit dem Finger (eine Einstellung im linken Drittel antippen blaettert zurueck, zwei Finger blaettern in der Liste), in die Welt tippen setzt dort. Steuert man eine Figur, hat sie alle Touch-Knoepfe, und der Ziffernblock klappt unter die Taste NUM oben. Der Beobachter zeigt nur II und EBN. Dafuer kann eine Szene der Touch-Steuerung eigene Tippflaechen und die gueltigen Knoepfe nennen (`touch_tippen`, `touch_knoepfe`). **`ios/aufspielen.sh`** (nur Mac): baut das Projekt (ios/bauen.sh), sucht das angesteckte iPhone oder iPad (devicectl, ab Xcode 15), findet das Entwicklerteam im Schluesselbund oder in den Einstellungen von Xcode, signiert automatisch (xcodebuild -allowProvisioningUpdates), spielt die App auf und startet sie - ohne einen Klick in Xcode. `--testmodus` startet gleich im Testmodus (`DUSTFRONT_START=testmodus`), `--liste` zeigt die Geraete, `--nur-aufspielen` baut nicht neu, `--xcode` oeffnet wie bisher Xcode; Bundle-ID und Team werden gemerkt. Klappt das Signieren nicht, oeffnet es Xcode mit dem Projekt und sagt, woran es lag. Netz/LAN: unveraendert. |
| 0.34.62 | **Zwoelf Waffen aus dem Waffenpaket, spielbar.** Im Menue AUSRUESTUNG waehlbar: Revolver (Betriebsart FAECHERN leert die Trommel auf einen Druck), Zwillinge (rechte Maustaste die zweite Pistole), Maschinenpistole (flinker, Schaden faellt ab 160 px ab), Praezisionsgewehr (Kegel schliesst sich zur Linie, ein Schuss oeffnet ihn kaum, keine Mittellinie), Unterhebelgewehr (Patrone fuer Patrone, ein Schuss unterbricht das Laden), Panzerbuechse (durch drei Koerper und niedrige Deckung, voller Schaden am Fahrzeug, roter Ziellaser fuer alle), Doppelflinte (rechte Maustaste beide Laeufe), Autoschrot (drueckt zurueck), Minigun (Anlauf, fast stehend), Granatwerfer (Bogen bis zum Zeiger ueber niedrige Deckung, Hoehe nur als Groesse, Koerper zuenden sofort), Einweg-Raketenwerfer (ein Schuss, das Rohr liegt danach qualmend am Boden) und Raketenbuendel (sechs schlingernde Miniraketen auf einen Druck). Die Zahlen sind ein erster Vorschlag (das Paket laesst sie offen). Neue Schalter in K.WAFFEN statt Sonderfaellen im Code; LASER und ROHR in `config.py`. Behoben dabei: ein Loadout mit einer Waffe, die nicht in HOTBAR steht, verlor sie (`konto.hotbar_aus_loadout`); ein Waffenwechsel beendet jetzt eine angefangene Salve (vorher schoss sie mit der neuen Waffe weiter). Bots ziehen weiter nur die alten fuenf (`K.BOTS["waffen"]`), auch als zweite Waffe, wenn ihnen der Testmodus eine vorgibt. Testmodus: WAFFE fuer SPIELER, STEHT und SPIELER, ICH. Netz/LAN: **geaendert** - neue fliegende Bilder (`teil_granate40` mit Hoehe, `teil_minirakete`), die Wirkung `l` traegt auch das leere Rohr (ohne Blut), und die rechte Maustaste (`zielt`) ist bei Zwillingen und Doppelflinte ein zweiter Abzug. Alle Geraete brauchen dieselbe Version. |
| 0.34.61 | **Die Waffen aus dem Waffenpaket, als Bilder.** Alle 58 Eintraege des abgenommenen Pakets (`dustfront_waffen`, sechs Runden) sind gezeichnet (`dustfront/art_waffen.py`, die Zeichnungen des Pakets mit den Ueberarbeitungen der Runden 4 bis 6, Pixel fuer Pixel gleich mit seinen PNGs): 52 Waffen an der Hand - jede als Figur, je Mannschaft und mit jedem Aussehen - und 63 Zeichen fuer die Hotbar (dazu Munition, Fahrzeugteile, Fundwaffen), ausserdem Minirakete, 40-mm-Granate und das leere Rohr des Einweg-Raketenwerfers. Spielbar ist damit noch keine; das kommt mit der naechsten Version. Die Bildnamen: `spieler_[<team>_]<waffe>`, `waffe_<waffe>`, `teil_<name>` - jede Datei in `assets/` ersetzt ein Bild wie gewohnt. Testmodus: neue Gruppe WAFFENBILDER, FIGUR MIT WAFFE (jede der 52, Mannschaft, Richtung). Liste und Namen in `config.py` (PAKET_HAND, PAKET_SYMBOLE, PAKET_TEILE). Netz/LAN: unveraendert. |
| 0.34.60 | **Skins, NPCs und Tiere.** Aus dem abgenommenen Figurenpaket (`dustfront_figuren`, vier Runden): 14 Operators und 17 Soldaten, im Code nachgezeichnet (`dustfront/art_figuren.py`, Pixel fuer Pixel gleich mit den Sprites des Pakets). Im Menue AUSRÜSTUNG gibt es die Zeile **AUSSEHEN** mit einer Vorschau daneben (gross, darunter in ROT und BLAU, dazu die Beschreibung aus dem Paket); STANDARD ist die alte Figur. Waehlbar sind 29 - Schildtraeger und Panzerfahrer nicht, weil sie etwas Festes in der Hand halten und keine Waffe zeigen koennten. Das Aussehen gilt sofort (nur ein Bild, kein Vorteil), liegt in den Einstellungen (`aussehen`) und wandert mit dem Konto. **Alle sehen es**: jede Figur mit jeder Waffe, mit dem Medkit, im Schlag mit dem Brecheisen und als Insasse in Buggy, Panzerturm und MG-Ring. In Mannschaften zeigt die Figur ihre Seite mit zwei Neon-Streifen auf den Schultern und einem Leuchtfleck am Hinterkopf, umgefaerbt wird nichts. Am Boden und als Leiche bleibt es die Figur in Mannschaftsfarbe. **Bots** tragen einen Soldaten, zu ihrem Namen immer denselben. Testmodus: AUSSEHEN fuer BOT, SPIELER (STEHT) und SPIELER, ICH (Vorgabe: das eigene); neue Gruppen **NPC** (Haendler, Aerztin, Wissenschaftler, Fluechtling, Pilger, Schmuggler, Hirte, Ueberlebende mit sechs Stirnbaendern) und **TIERE** (Schaf, Ziege, Huhn in je drei Farben oder zufaellig). NPCs stehen, Tiere laufen herum (INFO zeigt wohin); beide nehmen Schaden und sterben, niemand greift sie an. Bildnamen `skin_<id>[_<team>][_<waffe>]` kommen aus einem Muster (`core.platzhalter_muster`) statt aus ueber tausend Eintraegen in BILD_MASS - jede Datei `assets/skin_....png` ersetzt die eine Figur trotzdem. Zahlen in `config.py` (FIGUREN, FIGUREN_NEON, STIRNBAND_FARBEN, TIERE, NPC, TIER_LAUFEN). Netz/LAN: **geaendert** - `hallo` und jeder Spieler in der Weltmeldung haben ein Feld `sk` (das Aussehen), neue Nachricht `aussehen` vom Gast an den Gastgeber. Alle Geraete brauchen dieselbe Version. |
| 0.34.59 | **Panzer und Panzerwagen.** Aus dem abgenommenen Fahrzeugpaket (`rustfront_fahrzeuge`): zwei schwere Fahrzeuge, gezeichnet wie der Buggy (vierfach gezeichnet, Licht von oben links, Groesse 1,4), mit Insassen in Spielergroesse. *Panzer* (Marke `P`, auf STAUBTAL im Hof des Forts): Kettenfahrzeug, rund 45 px/s, dreht auf der Stelle (80 Grad je Sekunde), driftet nicht, die Ketten laufen (in der Kurve die aeussere schneller, auf der Stelle gegeneinander) und lassen Spuren im Sand. Der Turm folgt der Maus mit 60 Grad je Sekunde, unabhaengig von der Wanne; linke Maustaste die Kanone (Granate mit dicker Leuchtspur, 2,6 s Nachladen, das Rohr faehrt zurueck, die Wanne ruckt, Staub am Boden vor der Muendung), rechte Maustaste das Bug-MG in Fahrtrichtung. Der Einschlag ist eine neue Explosionsart: Feuerball aus neun versetzten Glutballen, danach dunkler Rauch, Funken, Splitter und ein unregelmaessiger Krater im Boden - nichts davon rund. *Panzerwagen* (Marke `L`, auf der langen Piste westlich der Kreuzung): drei Achsen, Keilramme, MG-Ring auf dem Dach (dreht mit 120 Grad je Sekunde, linke Maustaste). Faehrt mit dem Einspurmodell des Buggys und eigenen Werten: zieht zaeh an (26 px/s nach 1,2 s), wird sehr schnell (bis 320 px/s, Buggy 250), lenkt sehr schlecht (Wenderadius 160 + Tempo); die Reifen laufen und verwischen ab 72 px/s. *Beide:* einer steuert - fahren mit W A S D, zielen mit der Maus, E steigt ein und aus. Ein Rechteck als Fussabdruck statt zweier Kreise (an Mauern, Loechern, anderen Wagen und beim Treffen); wer im Weg steht, wird an der naechsten Seite hinausgeschoben, ueber die Front und schnell genug mit Schaden (Panzer ab 20, Panzerwagen ab 40 px/s) - wer dabei stirbt, fliegt noch ein Stueck und hinterlaesst einen Spritzer. Kugeln zerkratzen das Blech nur (Panzer 12, Panzerwagen 35 Prozent), der Insasse bekommt seinen Teil voll ab (Panzer 20, Panzerwagen 45 Prozent); Granaten, Raketen, C4 und Kanonen wirken voll. Kaputt: ein Wrack, das brennt, spaeter steht an anderer Stelle ein neuer - derselben Art. Gezeichnet in drei Ebenen: Wanne, dann die Figuren, dann Turm und Ring. Klaenge als Platzhalter (Kanone, MGs, Einschlag, Motor im Takt, Rammen). *Buggy:* der Fahrer ist jetzt die Spielerfigur in Spielergroesse (gewuenscht fuer alle Fahrzeuge), das Cockpit etwas groesser. Testmodus: Spawner OBJEKTE PANZER und PANZERWAGEN; Aufnahmen `panzer` und `panzerwagen`. Zahlen in `config.py` (PANZER, PANZERWAGEN, RAMMEN, FEUERBALL, FAHRZEUG_WAFFEN). Netz/LAN: **geaendert** - je Fahrzeug in der Weltmeldung fuenf Werte mehr (Art, Turm- bzw. Ringwinkel, Ruecklauf, Drehtempo, Ladezeit der Kanone), neue Wirkung `l` (wer nach dem Rammen fliegt), neue Netzklaenge, und `karten/staubtal.txt` hat zwei neue Marken (`P`, `L`). Alle Geraete brauchen dieselbe Version und dieselbe Kartendatei. |
| 0.34.58 | **Trupps unterwegs wie echte Trupps, der Funk wieder zu sehen, kein Übermut, keine kurzen Einbrüche - und Klänge im richtigen Takt.** *Unterwegs ohne Gegner:* Statt einer breiten Linie vor dem Anführer - einer Front ohne Feind, und wer seitlich zu seinem Platz lief und dabei nach außen schaute, glitt - geht der Trupp im Keil hinter ihm. Jede Reihe folgt seiner Spur und biegt an einer Ecke dort ab, wo er abbog; wo es eng ist, gehen sie einer hinter dem anderen. Mehr als fünf gehen in kleinen Keilen hintereinander. Jeder geht so schnell wie der Anführer und dazu, was zu seinem Platz fehlt - kein Stop-and-Go - und schaut, wohin der Trupp geht, ein wenig zu seiner Seite. Der Anführer geht im Patrouillentempo, hält unterwegs und am Ziel kurz zum Sichern (die anderen schauen dann zur Seite und nach hinten) und sucht die Karte ab: lieber dorthin, wo der Trupp lange nicht war. Geht er eine Treppe hinauf, folgen sie ihm; vorher drückten sie unten gegen die Mauer. Kennt der Trupp Gegner, ist er nah am Angriffsziel oder hat der Anführer etwas gehört, entfaltet er sich zur Linie; eine Stellung halten heißt weiter Linie. Gemessen ohne Gegner, je drei Läufe: seitwärts gleiten bei sechs Mann 50 bis 94 → 4 bis 7 Prozent der Laufzeit; bei zehn Mann vor dem Anführer 37 bis 40 → 1 bis 5 Prozent. *Große Trupps im Gefecht:* An dieselbe Kiste stellt sich kein Zweiter mehr, auch nicht beim Feuerschutz fürs Bergen (das Bergen selbst bleibt, wie es ist); die Wellen beim Rückzug ziehen in die eigene Bahn. Zehn gegen zehn, acht Läufe: dicht beieinander (unter 22 Pixeln) 24 → 18 Prozent; Stellungen auf einem Fleck 28 → 6 bis 17 Prozent. Nebenbei behoben: Wen die Streuung eines Kameraden traf, der hielt ihn für einen Gegner, und ein Teil des Trupps schaute zu ihm. Kehrtwenden drehen zurück, wie sie kamen - zwei hintereinander wurden sonst eine ganze Drehung um sich selbst. *Funk:* Er kam im Gefecht kaum je durch - jede andere Aktion würgte den Spruch nach Sekunden ab. Wer funkt, bleibt jetzt dabei; nur während einer geborgen wird, gehen Rauch und Feuerschutz vor, außer der Spruch ist fast durch (das Bergen bleibt, wie es ist). Durch: ein eigener Klang (Rauschen und zwei Töne), ein Haken beim Funker und drei Ringe, die ausgehen. Abgebrochen: ein rotes Kreuz und ein Ring, der in sich zusammenfällt. Ein Spruch dauert weiter 6 Sekunden. *Übermut:* Die überlegene Seite ging bei hoher Zuversicht in „Druck“, verließ die Deckung und stellte sich in einer Linie vor die anderen. Das ist jetzt aus; Testmenü BOTS ÜBERMÜTIG schaltet es wieder ein, wie FLIEHEN. *Kurze Einbrüche auf 10 Bilder je Sekunde:* Alle Trupps dachten im selben Bild nach (jetzt jeder in seinem Takt), ein Wegfeld zu einer Stelle, die man nicht erreichen kann, suchte die ganze Karte ab (jetzt sofort „unerreichbar“), und die Kanten der Klippen und die Masken der oberen Ebenen wurden erst beim ersten Blick auf eine Ebene gezeichnet (auf STAUBTAL 440 ms, jetzt beim Laden). Hänger in einer großen Schlacht: 41 → 5. *Testmodus:* Bei ZEIT STEHT zitterten Lebende ein paar Pixel hin und her - das Bild mischte zwischen den letzten zwei Rechenständen, obwohl die Zeit stand. Als Beobachter rufen Liegende nicht mehr um Hilfe (kein Ausrufezeichen, kein Zittern, kein Ruf); wer selbst mitspielt, hört sie weiter. *Klänge ohne Hänger und im Takt, auch bei sehr wenigen Bildern je Sekunde.* *Ohne Hänger:* Jeder Klang wurde beim ersten Abspielen erst angelegt, und das kostete 50 bis 380 ms - der erste Schuss jeder Waffe hielt das Spiel spürbar an. Jetzt baut ein Hintergrundfaden alle Klänge, sobald das Hauptmenü steht (Schusswaffen zuerst, danach die dumpfen Fassungen), und jedes Spiel aus dem Menü bekommt sie fertig. Dazu rechnet das Anlegen selbst ein Fünftel schneller, Probe für Probe dasselbe. *Im Takt:* Die Rechenschritte eines Bildes laufen im Block, und alles, was sie abspielten, klang im selben Augenblick - bei wenigen Bildern je Sekunde kamen Schüsse gebündelt am Bildanfang, ein Feuerstoß stolperte (aufgenommen bei 8 Bildern je Sekunde: Abstand zwischen 255 und 523 ms, jetzt gleichmäßig 280 ms). Jetzt klingt jeder Schritt um seinen Anteil an der Dauer des Bildes später; der Mischer spielt dafür etwas Stille vorweg, probengenau, auch wenn das Spiel gerade hängt. Gleichzeitig klingt nur noch, was im selben Rechenschritt geschah. *Kein Klang fällt aus:* 64 statt 24 Kanäle, und sind alle belegt, weicht der älteste statt des neuen. Die Lautstärke gehört jetzt dem Kanal: vorher drehte ein ferner Schuss einen nahen, der noch nachhallte, mit leiser. Testmodus: Testmenü BILDRATE (KLÄNGE PRÜFEN) bremst auf 30, 15, 8 oder 4 Bilder je Sekunde. Netz/LAN: Das Gefecht (`mehrspieler.py`) ist geändert - Übermut der Bots ist aus, und die Bilder der Ebenen werden beim Laden gezeichnet. Über die Leitung geht nichts Neues; der Gast verteilt die Klänge mehrerer Weltmeldungen, die auf einmal ankommen, über die Zeit seit der letzten. Alle Geräte brauchen dieselbe Version. |
| 0.34.57 | **Schneller: 40 bis 75 Prozent mehr Bilder je Sekunde.** Gemessen in einem Fenster mit 1920 × 1080, je drei Szenen gemittelt, Bilder je Sekunde vorher → jetzt: Teamrunde 5 gegen 5 61 → 100, Teamrunde 8 gegen 8 62 → 87, PvE in der ersten Welle 79 → 139, zwei Trupps im Testmodus 46 → 67, große Schlacht mit 36 Bots 22 → 35. Was es war: Die Ausgabe ins Fenster legte jedes Bild eine neue Fläche in voller Fenstergröße an und kopierte sie noch einmal (6,5 ms je Bild, jetzt 1,9). Sicht und Deckung der Bots laufen in einer Verfolgung mit Tafeln, und die Deckung wird nur noch dort abgetastet, wo die Linie eine Kiste kreuzt (rund dreimal so schnell). Die Wegfelder der Bots rechnen erst, wonach gefragt wird (vorher 36 ms je Feld auf STAUBTAL). Der Boden wird aus vorgezeichneten Blöcken gelegt, die Farben der Mauerseiten werden gemerkt, und die billigen Prüfungen kommen zuerst (Schritte hören, Deckung beim Bergen). Nebenbei behoben: Auf der Ebene darunter konnte ein Bild die abgedunkelte Fassung eines anderen bekommen (zu sehen als Ring um ein Fass). Sonst ist jedes Bild pixelgleich, und Sicht und Deckung geben den Bots auf jede Frage dieselbe Antwort wie vorher. Netz/LAN: unverändert; trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.56 | **In Runden flieht kein Bot mehr in Panik.** Wegrennen sah für Spieler wie ein Fehler der KI aus. Panik gibt es weiter: wer in Deckung ist, verkriecht sich dort, wer im Freien steht, wechselt in eine bessere Deckung. Die Kampagne wird es wieder einschalten. Testmodus: Testmenü BOTS FLIEHEN IN PANIK (AUS wie in Runden, AN wie in der Kampagne). Neue Verhaltensprüfung `keine_flucht`. Netz/LAN: unverändert, nur der Gastgeber rechnet die Bots; trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.55 | **Flüssiger und schneller.** *Last:* Mit vielen Liegenden lief der Planer der Bots für Ziele ohne Weg jedes Mal bis an seine Grenze (400 Zustände, rund 3 ms), solange einer geborgen wurde - jetzt prüft er vorher, was überhaupt erreichbar ist, und probiert nur Aktionen durch, die zum Ziel beitragen (im Schnitt 1 bis 2 Zustände je Plan statt 170 bis 290). Dazu: Funken, Hülsen und Geschosse außerhalb des Bildes werden nicht mehr auf Mauern davor abgetastet, die Netzmeldung wird ohne Gast nicht gebaut, und Feuerschutz-Stellungen werden nicht jeden Takt neu gesucht. Gemessen in einem langen Gefecht mit 36 Bots: 20 bis 28 ms je Bild statt 39 bis 52. *Bergen:* Lag ein zweiter daneben, griff der Helfer den falschen, zog ihn ein Stück, ging zurück und griff wieder den falschen - jetzt sagt er, wen er meint. Wer schon aufhilft, plant nicht mehr mittendrin das Ziehen, bleibt bei dem, dem er hilft (auch wenn im eigenen Trupp ein anderer fällt), kniet und lässt sich nicht wegschieben und bringt es ab der Hälfte zu Ende, auch wenn ein Gegner auftaucht - dann warten Panik, Deckung und Flanke, nur einer Granate weicht er noch aus (vorher 6 bis 12 solcher Abbrüche in den Prüfszenen, jetzt höchstens einer). Für alle, auch Spieler: wer schon aufhilft, darf dabei 4 px über die Reichweite hinausrutschen, ohne dass es abbricht. Findet der Anführer für den Rauch in 3 s keine Stelle mit freier Wurfbahn, lässt er ihn eine Weile und gibt Feuerschutz (vorher lief er hinter einer langen Mauer bis zu 12 s herum). *Keine sinnlosen Drehungen:* Ohne Zielpunkt schaut ein Bot zum bekannten Gegner statt in die Laufrichtung, sonst in seinen Sektor, in die Richtung der Trupp-Linie oder dorthin, wo er etwas vermutet; dem Lauf folgt der Blick erst, wenn er eine Weile in eine Richtung geht; beim Ziehen und Aufhelfen schaut er nicht um, und wem einer aufhilft, den zieht kein anderer weg; Umschauen nur noch zur Flanke und nie, während er einen sichtbaren Gegner bekämpft; die Linie des Trupps dreht sich träge statt mit jedem Blick des Anführers (ganze Drehungen in den Prüfszenen 1 bis 2 statt 7 bis 8, auf der Stelle 0 bis 1 statt 4 bis 7). Neue Verhaltensprüfungen `planer`, `bergen_fluessig`, `drehen`. Netz/LAN: Die Eingabe kann jetzt sagen, wem man aufhilft oder wen man zieht (`wen`) - nur Bots nutzen es, ein Gast schickt es nicht; trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.54 | **Feuerschutz beim Bergen.** Während einer geborgen wird, ist Feuerschutz die Aufgabe aller anderen (vor Welle, Funk und Feuerkampf; Nachladen, Flanke, Panik und Granate gehen vor): sie halten den nieder, der den Retter oder den Liegenden treffen kann, und lehnen sich dafür halb aus der Deckung heraus - öfter und mit kürzeren Pausen als sonst. Wer getroffen wird, ruft es heraus: der Trupp weiß sofort, woher geschossen wurde; wer nur zu hören ist, wird trotzdem niedergehalten. Die gedeckten Plätze beim Bergen sind solche, von denen aus man schießen kann. Gemeldet: man konnte einen Retter nach dem anderen abschießen, ohne selbst beschossen zu werden. Neue Verhaltensprüfung `feuerschutz` (ein schießender Gegner): im Schnitt 1,2 Schuss je Sekunde auf ihn, mehr als die Hälfte der Zeit niedergehalten (vorher 0,44 Schuss je Sekunde, teils keiner). **Nicht mehr durch Mauern:** steht eine Mauer zwischen einem Bot und dem Punkt, auf den er zielt, schießt er nicht (vorher in 17 % aller Bilder, in denen sie feuerten); auf Kisten halten sie weiter nieder, und wer nur auf eine Mauer zielen könnte, lässt das Niederhalten und tut etwas anderes. Testmodus: Testmenü NEBEL (SICHTWEITE) - aus, und man sieht herausgezoomt alles bis an den Bildrand. Netz/LAN: unverändert; trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.53 | **Bergen ist keine Todesfalle mehr.** Nur noch einer holt den Verwundeten (vorher zwei, und oft liefen alle mit). Solange er geborgen wird, bleiben alle anderen in Deckung: wer gedeckt steht, bleibt; wer im Freien steht (etwa nach dem Rauchwurf), geht auf dem Weg zur nächsten Deckung zurück - nicht mehr nachsetzen, flankieren oder suchen, sondern Feuerschutz aus der Deckung. Neue Prüfungen in `tests/test_verhalten.py`: nur einer holt ihn, wer nicht holt und keinen Rauch wirft, steht nicht offen, der Rauchwerfer nur kurz. Netz/LAN: unverändert; trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.52 | **Bots: bestehende Systeme repariert, mit neuer Verhaltens-Suite** (`tests/test_verhalten.py`: ganze Szenen über mehrere Seeds, gemessen wird, was die Bots tun). Kein Feuer mehr auf Liegende: wer am Boden liegt, ist nirgends mehr ein Gegner (Ziel, Erinnerung, Zuruf, Lage), und auch ein laufender Feuerstoß auf ihn endet - vorher hielt ein Dauerfeuer vier Sekunden drauf, und das Niederhalten schoss Stoß um Stoß auf die Stelle, wo er lag. Kein Schuss mehr durch einen Kameraden in der Schusslinie. Geknickte Front: jeder Abschnitt schießt auf seine Gruppe (vorher behielt jeder das erste Ziel, und alle schossen in eine Richtung); wer schon einen Abschnitt hat, behält ihn; eine Gruppe gehört zu dem Abschnitt, zu dem sie näher liegt. Dicht an die Deckung: gedeckte Stellungen und Deckungsplätze rücken bis an das Hindernis heran, und dort steht er still statt hin und her. Bergen: der Rauch fliegt erst, wenn der Werfer zum Ziel schaut, und nicht über eine Mauerecke (vorher landete er drei Kacheln neben dem Verwundeten); der Gezogene rutscht an Ecken entlang; der Bergeplatz liegt sicher im Schatten, nicht auf der Kante, und bleibt, statt bei jedem Wackeln woandershin zu wechseln. Last: Liegende sieht niemand mehr an, und wer still liegt, kostet keine Bewegung; Deckungslinien und Wegefelder rechnen 2,7-mal schneller. Testmodus: mit festem Zufall jedes Mal dieselbe Aufstellung. Netz/LAN: unverändert; trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.51 | Geknickte Front, besser zu sehen und richtig gelebt: wer in einer geknickten Front steht, zählt für die Flanke nur die Gegner seines Abschnitts (den anderen hält ein Kamerad) - vorher hielt sich jeder für flankiert, und alle drängten in die Mitte. Die Abschnitte stehen weiter vorn (90 px statt 40), ein MG-Schütze geht erst an seine Stellung, bevor er stehend hält. Testmodus: die Trupp-Anzeige zeichnet jeden Abschnitt als eigene Linie mit Strich zu seiner Gruppe; Aufnahmen können die Trupps in der sauberen Ansicht zeigen. Neue Aufnahme `abschnitte`. Netz/LAN: unverändert; trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.50 | **Bots, Teil 8.** Nie von der Flanke: wer auf einen Bot schießt, wird sein Ziel; stehen Gegner von zwei Seiten (mehr als 80 Grad), stellt er sich um, bis alle vor ihm sind (Ziel FLANKE SICHERN). Die Front eines Trupps knickt: kommen Gegner aus mehreren Richtungen, schaut je ein Teil zu jeder Gruppe. Bergen: Gegner hinter Rauch sind nicht vergessen, Rauch fliegt nur noch gezielt (vorher warf der Anführer ihn bei der nächsten Aktion irgendwohin), nur einer zieht, die anderen geben Feuerschutz aus der Deckung, eine angefangene Bergung wird zu Ende gebracht. Rückzug und Panik bleiben beim Trupp. **Bots sprinten** (Ausdauer, Staub hinter ihnen) - weg von Granaten, in Panik, beim Umstellen unter Feuer; der Spieler nicht. **Zurufe**: jeder Bot sagt den Bots in seiner Nähe, wen er sieht - mit Sprechdauer; wer sucht, hört dann auf und hilft. Der Anführer gibt Funksprüche an seinen Trupp weiter. Funkwellen etwas größer. Testmodus: Testmenü BOTS SPRINTEN, Sprechblase über dem, der ruft, Zurufe unten links, INFO zeigt Ausdauer, FLANKIERT und wer schießt. Netz/LAN: **geändert** - neues Feld `sp` (sprintet) in der Weltmeldung; alle Geräte brauchen dieselbe Version. |
| 0.34.49 | Fehler aus den neuen Aufnahmen behoben: Der Anführer stand ewig bei RAUCH WERFEN hinter der Mauer (der Wurf wäre gegen sie gegangen) - jetzt geht er erst dorthin, wo er frei werfen kann. Bergeplatz und bessere Deckung unter Panik werden zu Fuß gemessen (um Mauern herum) und fein abgesucht; vorher fanden die Bots dahinter nie einen Platz und halfen im Freien auf oder rannten weg. Aufnahmen: das Wegenetz wird nach dem Bauen neu gerechnet. Netz/LAN: unverändert; trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.48 | **Bots, Teil 7.** In Deckung ist ein Bot nur noch dicht hinter ihr, nicht mehr weit dahinter; liegt eine Deckung zu nah am Gegner für seine Waffe, sucht er eine weiter hinten. Panik: bleiben (gesund, der Trupp rückt vor), in eine bessere Deckung wechseln (angeschlagen) oder fliehen (schwer getroffen, der Trupp zieht sich zurück). Verwundete werden erst hinter feste Deckung gezogen, nicht im Rauch wiederbelebt. **Wiederbeleben dauert 5,5 s (war 3)**: wer zieht oder aufhilft, hält den Gefallenen sichtbar mit beiden Armen (beim Aufhelfen mit Verband, der im Takt drückt), um ihn ein Ring, wie weit es ist - die Figur selbst (der Skin) bleibt, das Zieh-Bild aus 0.34.43 ist wieder weg. Funk (Testmodus): der Anführer zieht sich erst 300 px vom Gegner zurück, ein Spruch dauert 6 s, und wer ihn dabei trifft oder dicht vor ihm steht, unterbricht ihn. Funkwellen rot, gestrichelt und drehend. Neue Aufnahmen `mauer`, `panik`, `bergen_mauer`, `ueberfall`. Netz/LAN: **geändert** - das Wiederbeleben dauert länger (Regel AUFHELFEN), die Arme zeichnet auch der Gast; alle Geräte brauchen dieselbe Version. |
| 0.34.47 | Aufnahme `deckung`: Blau hat dreifaches Leben, sonst war die Szene nach acht Sekunden vorbei. Netz/LAN: unverändert; trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.46 | **Bots, Teil 6.** Wer am Boden liegt, ist kein Ziel mehr: Bots bringen höchstens den laufenden Feuerstoß zu Ende und nehmen dann den, der noch steht (das gilt auch im Spiel für liegende Spieler). Wer selbst zu Boden geht, denkt nicht weiter - im Testmodus steht über ihm VERWUNDET statt FLANKIEREN. Rauch kommt genau auf den Verwundeten (beim Rückzug auf den Trupp), nicht mehr zwischen ihn und den Gegner. Bots ziehen volle Deckung (Mauern) Fässern vor und setzen sich lieber an Mauerenden, von denen aus sie sich herauslehnen können. Steht die eigene Deckung direkt vor ihnen, schießen und werfen sie nicht hinein. Testmodus: Funkwellen rot, klein und am Boden unter dem Funker. Netz/LAN: über das Netz geht nichts Neues; Untertitel zeichnet auch der Gast nicht mehr. Das Verhalten der Bots ist anders, alle Geräte brauchen dieselbe Version. |
| 0.34.45 | Fehler behoben: Fiel ein Bot mitten im Sturm und stand wieder auf (Testmodus: wiederbelebt), hielt er den alten Sturm fest und stürmte nie wieder. Gefunden durch den neuen Test aus 0.34.44. Netz/LAN: unverändert; trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.44 | Bots stürmen nur noch in Überzahl (mindestens anderthalbmal so viele wie die Gegner, die sie kennen) - in der Aufnahme stürmten drei gegen drei aus ihrer Deckung. Testmodus: über einem Liegenden stand für den Beobachter weiter „[E] AUF [G] ZIEHEN“ (der Fix aus 0.34.42 traf nur die Randpfeile). Neue Aufnahme `deckung`. Netz/LAN: unverändert; die Bots rechnet nur der Gastgeber, trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.43 | **Ruhiger, wie in RimWorld.** Alle laufen langsamer (Spieler, Bots, Zombies, Bosse: 65 % des alten Tempos, das Verhältnis untereinander bleibt), Geschosse fliegen langsamer (80 %, gleiche Reichweite). Wer einen Gefallenen zieht, hat ein eigenes Bild: keine Waffe, beide Hände an ihm, der Blick zu ihm - und schießt nicht. Bots gehen zuerst in Deckung und kämpfen aus ihr heraus (drin warten, herauslehnen, ein Feuerstoß, zurück); nur die Mutigen, wer das MG am Laufen hat oder den Gegner gleich erledigt, greifen offen an. Trupp-Stellungen rücken hinter nahe Deckung. Panik in der Deckung: kein Wegrennen am Gegner vorbei, sondern in die beste gedeckte Ecke (im Haus die Ecke). Die Untertitel über den Bots sind aus. Testmodus: Funksprüche als Wellen, die vom Anführer ausgehen. Netz/LAN: **geändert im Gefecht** (Tempo von Figuren und Geschossen, Bots); über das Netz geht nichts Neues, aber alle Geräte brauchen dieselbe Version. |
| 0.34.42 | Testmodus: Über einem liegenden Bot stand für den Beobachter „[E] AUF [G] ZIEHEN“, als könne er helfen (gesehen in der Aufnahme). Die Szene `bergen` gibt den Gegnern mehr Leben, damit man die ganze Bergung sieht. Netz/LAN: unverändert; trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.41 | **Bots wie Menschen, Teil 4: Gelände.** Kommen die Gegner von allen Seiten, igelt sich ein Trupp ein: an einem Platz mit Deckung ringsum, im Ring, jeder schaut in seinen Sektor, der Anführer in der Mitte, und keiner verlässt den Ring. Gegen eine Zombie-Horde sucht der Trupp eine Engstelle zwischen sich und den Zombies und hält dahinter im Bogen. Testmodus: TRUPP: IGEL HIER, INFO zeigt Igelplatz, Engstelle und Blickrichtungen; Aufnahmen `igel` und `engstelle`. Netz/LAN: unverändert (Trupps nur im Testmodus); trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.40 | **Bots wie Menschen, Teil 3: Verwundete.** Im Testmodus (Testmenü VERWUNDETE BOTS, vorgegeben an) fallen Bots erst zu Boden. Der Trupp bestimmt ein, zwei Retter und holt den Verwundeten nur, wenn es sicher genug scheint; dafür legt der Anführer Rauch. Dann ziehen sie ihn in Deckung und helfen ihm auf, während die anderen decken. Das geht einmal: Danach ist er geschwächt (weniger Leben, langsamer, zielt schlechter, hält Abstand), und fällt er wieder, bleibt eine andere Leiche liegen, die nach ein paar Sekunden verschwindet. ENTF TÖTET legt einen Bot erst hin. Aufnahme `bergen`. Netz/LAN: unverändert; trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.39 | **Bots wie Menschen, Teil 2: Trupps.** Im Testmodus lassen sich ganze Trupps spawnen (Spawner TRUPPS), mit einem Anführer (Repetierer, Rauchgranate, auf Wunsch Funkgerät), der in der Mitte und hinten bleibt und den die anderen zuerst schützen. Der Trupp teilt, was einer in Sprechweite sagt, steht in Bahnen an einer Frontlinie statt in einer Reihe, zieht sich in Wellen zurück oder drückt mit Flanke nach vorn, sucht in breiter Linie und hält auf Befehl eine Stellung. Über Funk melden die Anführer die Lage und rufen um Hilfe; wer selbst wenig Gegner hat, sagt zu, erledigt seine und kommt. Alles bleibt GOAP: der Anführer ist ein Bot mit anderen Zielen und ohne Funk oder allein ein Bot wie jeder andere. Testmodus zeigt Front, Stellungen und Funk; Aufnahmen `trupp` und `hilferuf`. Netz/LAN: unverändert (Trupps nur im Testmodus); trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.38 | **Bots wie Menschen, Teil 1.** Das MG hält jetzt lange drauf (vorher kam es nie über seinen Anlauf hinaus), und ein MG-Schütze nimmt auch auf mittlere Weite sein MG. Mehrere Gegner beisammen: Flächenfeuer und die Granate in die Mitte. Wer einen Bot von der Seite trifft, wird sein Ziel. Keine Dashes mehr. Nach einem Wurf lädt kein Bot mehr die Granate „nach“. Mit GOAP dazu: **Stress und Zuversicht** (innenleben.py, nach *Days Gone*) mit Panik, Schreck und Übermut, **Bindung** an das laufende Ziel und eine kurze **Bedenkzeit** beim Wechsel, in Deckung erst, wenn sich Stress aufbaut (nicht bei jeder Kugel), **Hören** von Schüssen, Explosionen und Schritten, **Umschauen**, Deckung nicht mitten zwischen anderen Gegnern, **Granaten ausweichen**. Testmodus: Stress, Zuversicht und Gehörtes in INFO und GEDANKEN, Testmenü INNENLEBEN. Plan und Stand: `docs/KI.md` Abschnitt 11. Netz/LAN: unverändert, das Verhalten der Bots rechnet nur der Gastgeber; trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.37 | `docs/KI.md` hat einen neuen Abschnitt **10. Was wir aus den Quellen nutzen**: F.E.A.R., die Killzone-2-Arbeit, *Squad Coordination in Days Gone*, Guild Wars 2 (Nutzenkurven), Dual Utility und SquadSmart gelesen und zusammengefasst – Zuversicht nach dem Kräfteverhältnis, Frontlinie mit Bahnen gegen die „Ameisenreihe“, Rückzug in Wellen, Befehl nicht über dem Überleben, Zufall nur unter guten Möglichkeiten; dazu, was wir bewusst nicht übernehmen, wie wir messen und in welcher Reihenfolge wir bauen. Netz/LAN: unverändert, trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.36 | Zombies und Bosse bleiben vorerst klassisch – auch in den Szenen von `werkzeug_aufnahme.py` (Regel und Spawner standen schon auf KLASSISCH). `docs/KI.md` hat zwei neue Abschnitte: **8. Menschen im Gefecht** – wie die Bots menschlich kämpfen sollen (Stress und Zuversicht, Panik, Zögern, Übermut, Wut; die Waffe prägt die Rolle – das eingeschossene MG bleibt und hält nieder, die Schrotflinte geht vorne; Partner und Trupp statt Einzelrollen; Fehler aus dem Zustand statt aus dem Würfel), in vier Teilen zum Bauen – und **9. Lernmaterial** zu Planung, Utility, Trupp-KI, Stress und Weltbau. Netz/LAN: unverändert, trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.35 | **Aufnahmen mit Ton und in Zeitlupe.** `werkzeug_aufnahme.py` schreibt jetzt mit, welcher Klang wann wie laut gespielt würde (gehört vom Beobachter aus, mit derselben Entfernungsrechnung wie im Spiel), und mischt daraus die Tonspur. Mit `--zeitlupe` kommt zu jeder Szene eine Fassung in halbem Tempo dazu – echt doppelt so dicht gezeichnet, nicht verdoppelte Bilder, der Ton halb so schnell bei gleicher Tonhöhe. `--ohne-ton` lässt den Ton weg. Dazu ein Test, der wackelte: der herumirrende Zombie wird jetzt an seiner Strecke gemessen, nicht am Abstand zum Start. Netz/LAN: unverändert, trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.34 | **Tod schlichter, Figuren flach, Bots mit Rufnamen.** Die Todesanimation aus 0.34.33 ist wieder draußen: wer stirbt, hinterlässt sofort Spritzer und den Fleck im Blut seiner Art – und man hört es, mit einem neuen Todeslaut (`tod`, als Datei ersetzbar unter `assets/sfx/tod.wav`). Die Figuren – Spieler, Bots, Gegner, Bosse – sind wieder flach; nur Buggy und herumliegende Beute behalten ihre Höhe. Die Bots heißen jetzt wie Operators: `BOT-GHOST`, `BOT-CHIMERA`, `BOT-REAPER` … aus einer Liste von 380 Rufnamen (`config.py`, `BOTS["namen"]`). **Netz/LAN: geändert** (die Meldung `d` für einen Tod ist kürzer geworden), alle Geräte brauchen dieselbe Version. |
| 0.34.33 | **Jedes Wesen stirbt sichtbar.** Wer stirbt, verschwindet nicht mehr, sondern fällt um: ein kurzer Ruck beim Treffer, dann kippt er vom Schützen weg und liegt lang und flach da, dunkler, während unter ihm eine Lache wächst; nach ein paar Sekunden vergeht die Leiche, der Fleck bleibt. Je Art ein eigener Tod und eigenes Blut (`config.py`, `TOD` und `BLUT`): Menschen und Bots fallen um (rot), Läufer und Renner auch (braunrot), Brecher, Koloss und Mutter sacken schwer zusammen und wirbeln Staub auf (braunrot, fast schwarz, violett), der Speier zerläuft zu einer grünen Säurepfütze, der Bläher bläht sich auf und platzt (gelbe Galle), der Brandstifter glüht auf, verkohlt und zerfällt mit Glut zu Asche. Der Blutfleck ist jetzt eine Lache mit Spritzern statt verstreuter Punkte und liegt in acht Formen da. Wer nur verschwindet (Testmodus ENTF, ein Bot verlässt die Runde), hinterlässt nichts – daran sieht man den Unterschied. Testmodus: neue Zeile ENTF-TASTE (LÖSCHT / TÖTET). `werkzeug_aufnahme.py`: Szene `tod`, und die Kamera rutscht ohne Fenster nicht mehr nach links oben. **Netz/LAN: geändert** – der Gastgeber meldet jeden Tod (Wirkung `d`), der Gast legt Leiche, Lache und Spritzer selbst; vorher bekam ein Gast keinen einzigen Blutfleck zu sehen. Alle Geräte brauchen dieselbe Version. |
| 0.34.32 | **Gefechte als Video: `werkzeug_aufnahme.py`.** Rechnet fünf Szenen im Testmodus ohne Fenster (GOAP gegen klassisch, Flanke, Zombiewelle, Koloss, Hügel) und schreibt sie mit ffmpeg als MP4 nach `aufnahmen/` (1280 × 720, 30 Bilder je Sekunde). Dafür im Testmenü neu: **SAUBERE ANSICHT** – nur die Welt und über jedem Kopf, was er gerade tut (GOAP-Aktion oder Zustand der klassischen KI), ohne Ziffernblock, Tafeln, Linien und Funk; Beschriftungen in einem Rudel rücken auseinander. Herausgezoomt zeichnet sie das ganze Bild ohne Nebel – vorher fehlten am Rand Figuren ganz. Außerdem passt das Testmenü wieder in seinen Kasten, und drei Tests wackeln nicht mehr: der Schusstest am Anfang suchte seine Bahn noch ohne Rücksicht auf Kisten (die halten seit 0.34.26 Kugeln auf), der GOAP-Bot-Test fand neben einem zufälligen Einstiegsort manchmal keine freie Stelle, und der Speier-Vergleich hing an einem einzigen Lauf. Netz/LAN: unverändert, trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.31 | Zwei Fehler der GOAP-Bots, gefunden in aufgenommenen Testgefechten: Sah ein Bot seinen Gegner hinter einer Kiste, meldete „suchen“ sofort fertig, „angreifen“ ging nicht, und er stand im Feuer, während er immer wieder dasselbe plante – jetzt geht er zur Seite, bis die Bahn frei ist. Und in HÜGEL blieb er stehen und kämpfte, sobald er einen Gegner sah – jetzt geht draußen der Kreis vor (`wesen/bots.txt`: KREIS 82, NACHLADEN 85), gekämpft wird auf dem Weg. Netz/LAN: unverändert, trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.30 | **Zombies und Bosse mit zielorientierter KI** (Schritt 3 aus `docs/KI.md`). Neue Regel **GEGNER-KI: KLASSISCH / GOAP** (Spielarten mit Gegnern, erweitert): Zombies laufen hin und schlagen zu, Speier halten Abstand und spucken, ohne Ziel schlurfen sie herum statt zu stehen; ein Boss lauert, wenn sein Ziel auf einer anderen Ebene ist, und zieht angeschlagen seine Fähigkeit vor (mit vollem Vorlauf). Die Brut denkt wie ihre Mutter. Daten in `wesen/zombies.txt`; jede Spezies sagt jetzt mit `hirn:`, welche Verhalten sie benutzen darf, und die Prüfung achtet darauf. Testmodus: HIRN auch bei Gegnern und Bossen, Gedanken und KURZ-Ansicht auch für sie. Der Einzelspieler bleibt klassisch. **Netz/LAN: geändert** (neue Regel `gegner_ki`), alle Geräte brauchen dieselbe Version. |
| 0.34.29 | **Zielorientierte KI (GOAP), der Kern.** Wesen wählen das dringendste Ziel und planen dafür selbst eine Folge von Aktionen („erst in Deckung, dann nachladen“) – Ziele, Aktionen, Spezies und Merkmale (Mut, Disziplin) stehen als Text in `wesen/*.txt`, wie die Karten, und lassen sich ohne Programmieren ändern. Die Bots des Mehrspielers können ihn schon benutzen: neue Regel **BOT-KI: KLASSISCH / GOAP** (Rundentafel, erweitert); die klassische KI bleibt Vorgabe. Fairness wie bisher: Sehen, Zielen, Reaktion sind dieselben. Testmodus: Spawner-Einstellung HIRN, Gedankenansicht (Taste 8 zweimal), Ziel erzwingen, KI-Daten neu laden. Der ganze Plan bis zur Kampagne steht in `docs/KI.md`. **Netz/LAN: geändert** (neue Regel `bot_ki`), alle Geräte brauchen dieselbe Version. |
| 0.34.28 | **Testmodus.** Neuer Eintrag im Hauptmenü (nicht auf iOS): Beobachter, der mit hoher Geschwindigkeit über die Karte fliegt und von nichts in der Welt wahrgenommen oder getroffen wird; alle Spezialaktionen auf dem Ziffernblock, der immer sichtbar und anklickbar am Rand steht (Zeit anhalten, Einzelschritt, Zeitfaktor x0,1 bis x4, KI aus, alles weg, Ebene, KI-Ansicht mit Zielen, Flanken, Deckung und Sturm, Spawner, nochmal spawnen, Gottmodus, Bot, stehender Spieler, Figur übernehmen, löschen). Spawner für Figuren (Bot, stehender Spieler, selbst gesteuert), alle Gegner und Bosse, Zielpuppe, Buggy, Hotzone, Beute und Wurfwaffen, mit Anzahl, Streuung, Team, Waffe, Leben, KI und Zünder – auch bei angehaltener Zeit. Gottmodi: unverwundbar, unsterblich, unsichtbar für KI, unendlich Munition. Testmenü (Esc) mit Kartenwahl und allen Schaltern. Nichts wird gebucht. Neue Regel in `AGENTS.md`: jedes neue Feature gehört in den Testmodus und den Spawner (`docs/TESTMODUS.md`). Netz/LAN: unverändert, trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.27 | **Bots funken und spielen taktisch.** Kurz vor einer Aktion sagen Bots an, was sie vorhaben – als kleiner Untertitel über ihnen (KONTAKT!, ICH FLANKIERE!, HALTE IHN UNTEN!, FEUERSCHUTZ!, NACHLADEN!, GRANATE!, SAMMELN AM EINGANG!, REIN, REIN, REIN! …); mit Mannschaften sieht das nur die eigene. **Flankieren:** Steht ein Gegner hinter einer Kiste oder ist er hinter einer Mauer verschwunden, geht einer seitlich herum, an eine Stelle mit freier Schussbahn. **Niederhalten:** Ein anderer schießt derweil auf die Stelle direkt neben der Deckung (oder auf die Deckung), damit der Gegner unten bleibt; Bots, an denen Kugeln knapp vorbeifliegen, gehen selbst in Deckung und zielen schlechter. **Feuerschutz:** Gegner bei einem Kameraden, der nachlädt, angeschlagen ist, am Boden liegt oder flankiert, haben Vorrang – das gilt für Bots und Spieler. **Stürmen:** Zwei oder mehr Bots, die wissen, wo ein Gegner steckt, sammeln sich außer Sicht, auf REIN wirft der Erste seine Granate und alle gehen zugleich hinein. Zahlen in `config.py` unter `BOTS` (`funk`, `flanke_*`, `druck_*`, `sturm_*`), die Taktik steht in `dustfront/bottaktik.py`. **Netz/LAN: geändert** (je Spieler `fk`/`fr`, der Funkspruch) – Gastgeber und Gäste brauchen diese Version. |
| 0.34.26 | **Bots mit Team-Manager, Deckung, und Hindernisse halten Kugeln.** Bots haben jetzt zwei verschiedene Waffen und eine Granate, die sie einmal pro Leben werfen; sie heben weder Medkits noch Munition auf, haben immer begrenzte Munition und gehen in den Nahkampf, wenn alles verschossen ist. Zum Nachladen und angeschlagen gehen sie hinter die nächste Mauer oder Kiste, in eine Kiste in der Schusslinie schießen sie nicht. In HÜGEL geht der Kreis vor: sie kämpfen auf dem Weg dorthin. Neu ist der **Team-Manager** für den Gastgeber (Pausenmenü → TEAMS UND BOTS, auch aus der Rundentafel): Auffüllen bis, Bots fest in ROT und BLAU (ohne Mannschaften: Bots dazu), Spieler in eine Mannschaft setzen – in der Lobby für die nächste Runde, im Gefecht sofort. **Alle Hindernisse mit Bild halten jetzt Kugeln und Raketen auf** (Kisten, Fässer, Sandsäcke, Kakteen, Brocken, Schrott), an ihrer Grundfläche. Granaten, Raketen, C4 und platzende Buggys treffen hinter einem Hindernis abgeschwächt, hinter einer Mauer kaum noch; eine Blendgranate hinter einer Kiste blendet schwächer (Werte in `config.py` unter `DECKUNG`). **Netz/LAN: geändert** (neue Regeln, Kugeln halten an Hindernissen) – Gastgeber und Gäste brauchen diese Version. |
| 0.34.25 | **Figuren in 3D wie die Hindernisse.** Spieler, Mitspieler, Bots, Gegner und Bosse, die Zielpuppen, der Buggy und die Beute am Boden stehen jetzt in derselben Perspektive wie Kisten, Mauern und Plateaus: das Bild der Figur ist ihr Deckel und rückt mit ihrer Höhe von der Bildmitte weg, darunter steht eine Seitenwand in ihrer eigenen Farbe, unten dunkler, oben heller. Am Bildrand sieht man die Seite, in der Mitte steht man genau darüber. Bosse ragen höher als kleine Gegner. Höhen und Helligkeiten in `config.py` unter `FIGUREN_3D` (`an=False` schaltet es ab). Nur das Bild: getroffen wird wie bisher, Namen und Lebensbalken bleiben am Boden. Netz/LAN: unverändert (der Gast zeichnet gemeldete Gegner und Beute genauso), trotzdem brauchen alle Geräte dieselbe Version. |
| 0.34.24 | **iOS-Port in `multiplayer-test` übernommen.** Alles aus dem Branch `ios-port` (0.34.20 bis 0.34.23) gilt jetzt hier: die App für iPhone und iPad (`ios/bauen.sh`, Anleitung `ios/LIESMICH.md`), Touch-Steuerung, der Weg zum Online-Code ohne cloudflared. Am Rechner (Windows, macOS, Linux) startet das Spiel unverändert mit Maus und Tastatur: die Touch-Steuerung gilt nur auf iOS oder mit `DUSTFRONT_TOUCH=1`. Nur Doku geändert. Netz/LAN: unverändert gegenüber 0.34.23; Crossplay braucht auf allen Geräten 0.34.24 |
| 0.34.23 | **iOS: eigenes App-Symbol und Startbild.** Statt des Logos von pygame-ce zeigt die App jetzt ein eigenes Zeichen: den Stern mit seinen drei Umlaufbahnen aus dem Intro, ohne Uhr und Flügel, neu und größer gezeichnet mit den Pinseln des Intros (`ios/logo_bauen.py`, Bilder in `ios/bilder`). Der Startbildschirm zeigt das Zeichen mit dem Schriftzug in der Schrift des Hauptmenüs. `ios/bauen.sh` setzt beides ein, den Startbildschirm über `UILaunchScreen` in der Info.plist. Am Spiel ändert sich nichts. Netz/LAN: unverändert |
| 0.34.22 | **iPhone: Trefferzeichen, Auto, Zielen, Zoom, Hotbar.** Hinter dem Trefferzeichen stand auf dem iPhone ein schwarzes Viereck - derselbe Fehler wie beim schwarzen Bild in 0.34.21 (Alpha je Pixel und `set_alpha` zusammen). Jetzt geht das überall über `plattform.deckkraft`, auch bei Schneespuren, der ausblendenden oberen Etage, dem Kosmetikbild der Blendgranate und der Bodenschrift der Lobby. **Auto mit dem Stick:** fährt dorthin, wohin der Stick zeigt, statt W/A/S/D nachzuahmen; halb gedrückt halb Gas, genau entgegen erst bremsen, dann rückwärts (`Buggy.stick_steuern`, Werte in `K.FAHRZEUG`). **Zielen:** der rechte Stick zielt von der Figur aus statt über die Kamera - beim Laufen wackelte das Ziel, mit dem Scharfschützengewehr deutlich; mit ZIEL bleibt der Blick weit, auch wenn der Daumen loslässt. **Zoom mit zwei Fingern** auf derselben Seite. **Hotbar antippen** wählt die Waffe sofort. **Netz/LAN: geändert** - in der Eingabe des Gasts das neue Feld `rl` (die Richtung kommt von einem Stick); beide brauchen 0.34.22 |
| 0.34.21 | **iPhone: schwarzes Bild beim Spielen behoben.** Auf dem ersten echten iPhone (12 mini) waren Boden, Figuren, Schrift und Waffenbilder schwarz, solange Sticks und Knöpfe zu sehen waren; im Pausenmenü stimmte alles. Die Knöpfe lagen auf einer Ebene mit Alpha je Pixel und zusätzlich `set_alpha` - das rechnet pygame-ce 2.5.6 dort offenbar falsch. Jetzt steckt die Deckkraft in den Farben selbst (`touch.py`). Außerdem stellt `ios/bauen.sh` das Mindestziel auf iOS 15 (aktuelles Xcode baut 13 nicht mehr). Netz/LAN: unverändert; Crossplay braucht trotzdem auf beiden Seiten 0.34.21 |
| 0.34.20 | **Port auf iPhone und iPad (Branch `ios-port`).** Derselbe Python-Code läuft als App, mit pygame-ce 2.5.6 und Python 3.13 aus [pygame-ios](https://github.com/seekerluke/pygame-ios); gebaut wird auf dem Mac mit `ios/bauen.sh` (Anleitung: `ios/LIESMICH.md`). **Touch-Steuerung** (`dustfront/touch.py`, Masse in `K.TOUCH`): links ein Stick zum Laufen (analog), rechts einer zum Zielen, der ab halbem Weg schießt und mit seiner Weite die Wurfweite bestimmt, dazu Knöpfe für Dash, E, R, F, Medkit, nächste Waffe, Zielen, Pause, Ebenen und Inventar. In Menüs ist ein Finger die Maus, zwei Finger blättern, ein kleiner ESC-Knopf hilft, wo es sonst nur die Escape-Taste gibt. Auf dem Rechner zum Ausprobieren mit `DUSTFRONT_TOUCH=1`. **Bildschirmtastatur** öffnet sich in Textfeldern, Einfügen geht (`dustfront/plattform.py`). Einstellungen liegen auf iOS im Behälter der App. **Online-Code ohne cloudflared** (`dustfront/wszugang.py`): auf iOS darf keine App ein zweites Programm starten, darum baut der Gast den Weg zum Code selbst - ein WebSocket zu Cloudflare mit denselben Kopfzeilen wie cloudflared. Genauso überall, wo cloudflared fehlt (Linux). Gastgeber mit Code geht auf iOS nicht, im LAN schon. Geprüft mit nachgestellten Fingern und einer Attrappe von Cloudflare, die ganze Testreihe auch unter Python 3.13 mit pygame-ce 2.5.6; auf einem echten iPhone lief es noch nicht. **Netz/LAN: geändert** - das Protokoll im Spiel ist gleich, neu ist der Weg eines Gastes zum Online-Code ohne cloudflared; Gastgeber und Gast brauchen beide 0.34.20, also für Crossplay auch der Rechner diesen Branch |
| 0.34.19 | **Dash-Richtung, kleine Hindernisse, Ebenen der TESTKARTE.** **Dash:** Beim Gast zeigten die Windlinien eines Dashs immer nach rechts, egal wohin jemand dashte - die Richtung kam nie über das Netz. Jetzt kommt sie mit. **Hindernisse:** Kaktus, Brocken, Kisten und Fässer werfen keinen Schatten in Form der ganzen Kachel mehr (das dunkle Quadrat, das wie ein Block darunter aussah), sondern einen in ihrer eigenen Form. Sie halten auch nur noch mit ihrer Grundfläche auf, runde wie ein Kreis: an einen Kaktus kommt man bis an den Rand heran, statt schon an der Kachel stehen zu bleiben. Mauern und Fels halten weiter mit der ganzen Kachel auf (`Welt.huelle`, `K.KARTENSAETZE`). **TESTKARTE:** Die Stege der oberen Etage über einzelnen Mauern und Kisten galten als Plateau und blieben stehen, wenn die Etage ausblendete - schwebende Säulen und Streifen quer durchs Bild. Ein Plateau braucht jetzt mindestens 16 begehbare Kacheln (`K.PERSPEKTIVE["plateau_flaeche"]`); STAUBTAL und SCHNEEFELD bleiben, wie sie sind. **Netz/LAN: geändert** - je Spieler das neue Feld `dw` (Dash-Richtung), und die Kollision an Hindernissen ist eine andere; Gastgeber und Gast brauchen beide 0.34.19 |
| 0.34.18 | **Bots, Gegner auf der Minikarte, Buggys gehen kaputt.** **Bots:** neue Regel BOTS AUFFÜLLEN BIS (2 bis 12 Spieler) für alle Runden mit PVP-Anteil. Die Bots füllen gleichmässig auf und machen Platz, wenn ein Mensch kommt. Sie sind schwach, aber nicht dumm: Sie kämpfen mit zur Waffe passendem Abstand und seitlichem Ausweichen, gehen in HÜGEL in den Kreis, helfen in VERSUS auf, suchen sonst Gegner, nehmen Treppen und Aufzüge, laden nach, heilen und werfen. Ohne Munition nehmen sie das Brecheisen. Kein Aimbot: Sie benutzen dieselbe Eingabe wie ein Gast, haben nur Sicht auf die eigene Umgebung (nicht durch Wände und Rauch, Blendgranaten wirken), brauchen eine Reaktionszeit, haben ein begrenztes Drehtempo und Zielfehler, und sie halten nie vor. Zufälliges Loadout je Leben, nie C4, kein Raketenwerfer, kein Buggy. Keine Buchung, keine Bestenliste (`dustfront/bots.py`, `K.BOTS`). **Minikarte:** neue Regel GEGNER AUF DER MINIKARTE (aus). **Buggys:** gehen jetzt kaputt (420 Leben). Treffer gehen auf den Wagen, und der reicht sie an den Fahrer weiter (70 % wie bisher, Freundfeuer nicht). Ein leerer Wagen ist damit auch Deckung, Treffer am Blech zählen nicht in die Trefferstatistik. Bei null Leben explodiert er: Schaden im Umkreis, der Fahrer fliegt heraus und bekommt etwas ab. Das Wrack brennt 9 s, 12 s später steht irgendwo auf der Karte ein neuer Wagen, möglichst ausser Sicht. Neues Bild `buggy_wrack`, Lebensbalken über beschädigten Wagen. Wagen stossen jetzt auch an anderen Wagen an. Zur neuen Runde stehen wieder alle heil an ihrem Platz. **STAUBTAL hat 5 Buggys** (neu westlich der Kreuzung A und vor dem Fort). **Netz/LAN: geändert** - neue Regeln `bots` und `gegner_karte`, je Spieler das Feld `bo` (ein Bot), in `fahrzeuge` je Buggy ein neunter Wert (Leben 0 bis 1, 0 = Wrack), und `karten/staubtal.txt` hat zwei `F` mehr; Gastgeber und Gast brauchen beide 0.34.18 (0.34.17 ist der Autoball-Stand auf `rocket-liga`) |
| 0.34.16 | **Buggy fährt sich echter, mit Driften.** Neues Fahrmodell mit Reifen: vorne und hinten haftet jede Achse nur bis zu einer Grenze, darüber rutscht sie und greift schwächer (Schräglauf). Wer schnell voll einlenkt oder mit Vollgas aus der Kurve beschleunigt, bringt das Heck zum Ausbrechen und hält den Drift mit Gas und Lenkung; Heckantrieb, beim Anfahren drehen die Räder kurz durch. Neu **Shift = Handbremse** im Buggy: das Heck kommt herum, für enge Kehren. Ein leichtes automatisches Gegenlenken fängt den Wagen, lässt man die Lenkung los, richtet er sich wieder gerade aus. Beim Rutschen bleiben **Reifenspuren** im Sand liegen, und die Reifen quietschen (neuer Klang `buggy_rutschen`). Alle Werte in `K.FAHRZEUG` (die alten `gas`, `lenkung`, `lenk_ab`, `griff` sind ersetzt). **Netz/LAN: geändert** - der Gast schickt ein neues Feld `hb` (Handbremse) in seiner Eingabe, und in `fahrzeuge` steht je Buggy ein achter Wert (wie stark er rutscht, für Spuren und Staub beim Gast); beide brauchen 0.34.16 |
| 0.34.15 | **Trefferzeichen.** Trifft man einen Gegner, springt am Mauszeiger kurz ein weisses X auf und es tickt; erledigt oder umgeworfen heisst: ein grösseres rotes X und ein tieferer zweiter Ton. Nur der Schütze sieht und hört es, auch als Gast und im Einzelspiel; Treffer an sich selbst und an den eigenen Leuten zählen nicht, Feuer und Schrot tickt nicht dutzendfach (`K.TREFFERMARKE`). Zwei neue Klänge (`trefferzeichen`, `trefferzeichen_toedlich`). **Netz/LAN: geändert** - je Spieler zwei neue Felder in der Weltmeldung (`tz`, `tk`, die Zähler seiner Treffer); beide brauchen 0.34.15 |
| 0.34.14 | **Online-Code: englische Beispiele.** Die Wörter des Codes vergibt Cloudflare, und die sind englisch (z. B. `THERMAL-UNDERLYING-PROVIDERS-TOE`); deutsch waren nur die Beispiele in README, Hilfe und Testersatz - jetzt überall englisch, und die Hilfe unter EINSTELLUNGEN > NETZ sagt es. **Netz/LAN: nichts geändert** (Versionsnummer trotzdem neu, beide brauchen 0.34.14) |
| 0.34.13 | **Online spielen mit Code - ohne Router, ohne Firewall-Abfrage.** Jede eigene Lobby bekommt einen Code aus vier Wörtern (oben links in der Lobby und im Pausenmenü unter ONLINE-CODE, auswählen kopiert ihn). Wer ihn unter ANDERER LOBBY BEITRETEN eingibt (Strg+V fügt ein), kommt von überall herein. Dahinter steckt ein kostenloser Quick Tunnel von Cloudflare: beide Seiten bauen nur ausgehende Verbindungen auf, die Lobby lauscht nur auf 127.0.0.1 - so muss am Router nichts freigegeben werden, und die Windows-Firewall fragt nicht. Das Programm `cloudflared` 2026.10.0 liegt für Windows und macOS in `tools/cloudflared` bei (Apache-2.0-Lizenz, Prüfsummen in `K.ONLINE`), das Spiel packt es beim ersten Mal selbst aus. **LAN jetzt nur auf Wunsch:** neuer Reiter EINSTELLUNGEN > NETZ mit ONLINE-LOBBY (an) und IM LAN SICHTBAR (aus); erst damit lauscht die Lobby im LAN, antwortet auf die Suche - und die Firewall fragt. Beides gilt sofort, wer drin ist, bleibt drin. Neu auch: Strg+V in jedem Textfeld. **Netz/LAN: geändert** - Protokoll gleich, aber die Lobby ist im LAN ohne den Schalter nicht mehr zu finden; beide brauchen 0.34.13 |
| 0.34.12 | **C4 nach 3 s scharf, Loadout im Spiel ändern geht.** C4 lässt sich jetzt drei statt fünf Sekunden nach dem Aufkleben zünden (`K.C4["ladezeit"]`). Ein im Menü AUSRÜSTUNG geändertes Loadout kam bei einem Gast nie beim Gastgeber an - der kannte nur das vom Verbinden, und das galt auch beim nächsten Einstieg und in der nächsten Runde weiter. Jetzt geht jede Änderung sofort an den Gastgeber und gilt, wie im Menü angegeben, ab dem nächsten Einstieg (nicht mitten im Gefecht); beim Ändern steht kurz "AUSRÜSTUNG GILT AB DEM NÄCHSTEN EINSTIEG". **Netz/LAN: geändert** - neue Nachricht `loadout` vom Gast an den Gastgeber; beide brauchen 0.34.12 |
| 0.34.11 | **Buggy repariert, C4 klebt am Buggy.** Wurde eine Runde aus der Lobby gestartet (der Normalfall), räumte der Rundenstart die eben aufgestellten Buggys gleich wieder weg: beim Gastgeber waren sie verschwunden, bei den Gästen standen sie weiter da, und fahren ging bei niemandem. Jetzt bleiben sie und stehen zu jedem Rundenstart leer an ihrem Platz. Neu: **C4 bleibt am Buggy kleben**, fährt mit (auch durch die Kurve) und liegt oben auf dem Wagen. Geht sie hoch, bleibt der Buggy heil, der Fahrer bekommt wie sonst 70 % ab. **Netz/LAN: Gefecht geändert, keine neuen Felder** - der Gast sieht die Ladung über die gewohnte Meldung; beide brauchen 0.34.11 |
| 0.34.10 | **Minikarte: Kreis und Buggys immer zu sehen.** Der Kreis (HÜGEL) steht jetzt auch auf der Minikarte, wenn er auf einer anderen Ebene liegt - dann blasser und mit einem kleinen Dreieck daneben, das nach oben oder unten zeigt; in der Farbe des Teams, das ihn hält, wie der Pfeil am Bildrand. Die Buggys stehen immer darauf, auf jeder Ebene und auch, wenn jemand fährt (ein Punkt in der Farbe des Fahrers, weiss für einen selbst), als kleines längliches Zeichen in Fahrtrichtung. Grössen in `K.MINIKARTE`. **Netz/LAN: nichts geändert** - alles, was die Minikarte braucht, kam schon mit der Weltmeldung von 0.34.9 |
| 0.34.9 | **Ein Buggy auf STAUBTAL.** Drei kleine Wüstenbuggys stehen auf der Karte - an der Tankstelle, auf der Dorfstrasse von Westdorf und im Hof der Ranch (in der Karte ein `F`). E steigt ein und wieder aus; W gibt Gas, S bremst und fährt dann rückwärts, A/D lenken, aber nur, solange er rollt. Er rutscht in scharfen Kurven ein wenig, gleitet an Mauern entlang, prallt ab, wirbelt Staub auf und schiebt Leute und Zombies beiseite. Der Wagen ist **unzerstörbar** (Kugeln gehen an ihm vorbei); wer drin sitzt, bekommt **70 % vom Schaden** und wird nicht weggestossen. Am Steuer wird nicht geschossen. Zur neuen Runde stehen alle wieder leer an ihrem Platz. Neues Bild von oben in den Teamfarben des Fahrers, zwei neue Klänge (`buggy_tuer`, `buggy_aufprall`), Werte in `K.FAHRZEUG`. **Netz/LAN: geändert** - neue Felder in der Weltmeldung (`fahrzeuge`, je Spieler `fz`) und `karten/staubtal.txt` hat drei `F` bekommen; Gastgeber und Gast brauchen beide 0.34.9 |
| 0.34.8 | **Wo der Kreis ist und wohin er zieht.** Ist der Kreis (HÜGEL) nicht im Bild oder auf einer anderen Ebene, zeigt ein grosser Pfeil in seiner Farbe am Bildrand auf ihn - neutral, solange niemand hält, sonst in der Farbe des haltenden Teams -, dahinter sein Name und gegebenenfalls die Ebene ("A E0"). Im Kreis liegt ein ">" auf dem Boden, das zum nächsten Kreis zeigt und sacht in dessen Richtung vorrückt. Grösse und Deckkraft in `K.ZONE`. **Netz/LAN: nichts geändert** - der Gast kennt die Kreise aus seiner Kartendatei und die Nummer des aktuellen aus der gewohnten Meldung |
| 0.34.7 | **Zwei Plateaus aufeinander, vom Tal aus richtig.** Wer unten steht, sah von der hohen Tafel nur eine Wand, so hoch wie die der anderen Tafeln, und oben nackten Fels - ihren Sockel. Gezeichnet wurde immer nur eine Etage nach oben. Jetzt kommt eine hoehere Etage dazu, wo sie auf einem geschlossenen Felsblock steht und oben eine Flaeche hat (mindestens 16 begehbare Kacheln, `PERSPEKTIVE["turm_flaeche"]`): die hohe Tafel steht vom Tal aus als zwei Wandstufen uebereinander da, mit ihrer Oberflaeche. Alles andere bleibt wie bisher - kein Stapel aus allen Stockwerken, und auf der Testkarte schwebt kein Mauerrahmen. Kostet nah an der hohen Tafel 2 bis 3 ms je Bild, ganz herausgezoomt rund 12 ms; sonst nichts. Dabei gefunden: `werkzeug_staubtal.py` erzeugte je nach Hash-Saat von Python an zwei Stellen ein anderes Zeichen (Gleichstand beim Zuschuetten kleiner Luecken); jetzt immer dieselbe Karte, `tests/test_pruefung.py` prueft das mit einer zweiten Saat. Die Karte aendert sich dadurch an drei Kacheln. **Netz/LAN: kein Protokollwechsel; die Darstellung ist neu, und `karten/staubtal.txt` hat sich minimal geaendert - Gastgeber und Gast brauchen dieselbe Version und Kartendatei** |
| 0.34.6 | **STAUBTAL von Grund auf neu, wie von Hand gebaut.** Gemeldet: "Bereiche, wo 50 verschiedene Fässer nebeneinander stehen" - es sollte natürlich aussehen. Die Tafelberge haben jetzt gezeichnete Ränder mit Buchten und Nasen und gehen am Kartenrand in eine Schluchtwand aus Fels über (kein Randgang mehr); ein Grat führt von der Südost-Tafel zur hohen Tafel. Gebaut sind **Westdorf** (Saloon, Laden, Sheriff, Kapellenruine, Schmiede, Wasserturm, Bretterstege), die **Kreuzung um A** (Tankstelle, Buswrack, Felsnase, eingestürzter Wasserturm, zwei Kontrollposten aus Sandsäcken), die **Funkstation um B** (Funkhaus, Baracke, Mast, Hofmauer mit Toren und Wachtürmen, Sandsacknester), das **Fort um C** (Mauer mit vier Toren, Ecktürmen und drei Breschen, Kantine, Stall, Lager, Kommandantur, gepflasterter Platz, Marktstände, Schiessstand), dazu Steinbruch mit Stollen, Ranch, Schrottplatz, ein abgebrannter Hof, eine Landepiste mit Hangar und einem abgestürzten Flugzeug, eine Missionsruine, ein Aussichtsturm und Scharfschützennester auf der hohen Tafel. Dazwischen Pisten mit Trampelpfaden zu den Türen, ein trockenes Bachbett, Geröll am Fuss der Wände und Natur in Gruppen - Felsfelder, Kakteenfluren, Buschland, kahler Sand. Fässer nur noch zu zweit bis viert. Dafür **elf neue Kachelarten** (Fels, Brocken, Sandsack, Holzkiste, Kaktus, Schrott, Piste, Kies, Pflaster, Gestrüpp, Dielen) mit eigenen Bildern und Höhen; Piste und Kies fransen zum Sand hin aus statt eine Kachelkante zu ziehen; eine Marke (Kreis, Spawnstelle) liegt auf dem Boden um sie herum statt als Sandfleck. Gemessen: alle acht Aufzüge tragen Läufer und Brecher, in grossen Wellen kommen 130 von 144 Gegnern an (alte Karte 125), keiner bleibt hängen; Bildzeit gleich oder besser. **Netz/LAN: kein Protokollwechsel, aber die Karte und die Kachelarten sind neu - Gastgeber und Gast brauchen dieselbe Version und dieselbe `karten/staubtal.txt`** (eine ältere Version läse die neuen Zeichen als Sand) |
| 0.34.5 | **Alles verdeckt sich wie in einer echten 3D-Welt.** Gezeichnet wird je Ebene in dieser Reihenfolge: Boden (Zonenkreis, Feuer, Staubringe, Figuren mit Schatten), dann Mauern, Kisten, Faesser, dann was fliegt, dann Rauch, zuletzt Anzeige. Was fliegt (Geschosse, Raketen, Funken, Staub, Blut, Muendungsfeuer, was gerade faellt) hat eine Hoehe (`K.HOEHEN`, Laufhoehe 12, Mauern 24) und ist nur zu sehen, wenn vom Auge aus keine Mauer davorsteht - eine Kugel knapp hinter einer Mauer verschwindet, eine darueber nicht. Rauch quillt hoeher als jede Mauer und liegt darueber. Anzeige bleibt ueber allem: Lebensbalken (auch eines verdeckten Gegners), Beute- und Schadenszahlen, Namen, Ziellinie. **Gast:** gemeldete Gegner, Beute und Geschosse lagen bisher ueber der ganzen Welt, auch ueber Mauern und Plateaus; jetzt verdecken sie sich genau wie beim Gastgeber (`mehrspieler.py`, gleiche Daten, kein neues Feld). Kostet mit 400 Partikeln im Bild etwa 0,7 ms mehr. Netz: keine Aenderung |
| 0.34.4 | **Mauern verdecken, wer hinter ihnen steht.** Waende, Kisten und Faesser werden jetzt nach den Figuren gezeichnet: wer vom Bildmittelpunkt aus gesehen hinter einer Mauer steht, verschwindet ganz oder teilweise hinter ihrer Oberseite. Wer davor steht, bleibt immer ganz zu sehen - die Mauer reicht im Bild nur von ihrem Fuss nach aussen. Spielerisch: ein Gegner knapp hinter einer Mauer am Bildrand kann jetzt bis etwa eine halbe Kachel weit verdeckt sein, obwohl das Spiel ihn als sichtbar zaehlt; gewollt. Netz: keine Aenderung, nur Darstellung |
| 0.34.3 | **Waende und Barrikaden stehen.** Bis jetzt waren sie flache Kacheln wie der Boden - auf dem Plateau sah eine Lehmmauer aus wie ein Weg, von einer hoeheren Ebene aus war eine Wand unten nur ein dunkleres Feld. Jetzt haben sie eine Hoehe (Mauern 24, Faesser und Kisten 14 Welt-Pixel, `K.STEHEN`) und werden wie die Plateaus in Perspektive gezeichnet: die Oberseite rueckt vom Auge weg, dazwischen sieht man die Seiten, die zum Auge schauen - schattiert, mit Steinlagen bzw. Fassreifen. Von oben und von unten passt die Perspektive zur jeweiligen Ebene. Neue Draufsichten fuer Mauerkrone (Lehm, Blech, verschneiter Fels), Kistendeckel und Fassdeckel, mit einer Kante um die ganze Mauer statt um jede Kachel. Faesser sind runde Zylinder, um sie herum liegt Sand. Blutflecken liegen jetzt unter den Mauern statt darauf. Kostet je Bild etwa 1 bis 2 ms mehr (gemessen, am meisten ganz herausgezoomt im Hof). Netz: keine Aenderung, nur Darstellung |
| 0.34.2 | **STAUBTAL: Hotzone 2 gebaut.** Um den Kreis B auf dem langen Plateau steht jetzt der Aussenposten aus dem Lageplan: zwei Gebaeude mit Tueren, zwei Fassreihen als Gassen, zwei niedrige Mauern im Sueden; der Platz um den Kreis bleibt frei (naechste Deckung 7 Kacheln vom Mittelpunkt). Das Kartenwerkzeug hatte ihn auf Ebene 0 in den Fels gezeichnet. Der unerreichbare Plateaustreifen hinter dem hohen Plateau (8 Kacheln breit) ist entfernt; darunter ist jetzt Sand, der den Randgang im Osten verbreitert. `tests/test_pruefung.py` verlangt jetzt, dass auf jeder Karte jedes begehbare Feld erreichbar ist. Netz: kein Protokollwechsel, aber die Karte ist geaendert - Gastgeber und Gast brauchen dieselbe Version |
| 0.34.1 | **Pruefung nach den KI-Aenderungen.** STAUBTAL: drei der sechs unteren Aufzuege lagen im Fels und waren nicht zu erreichen - das Suedwest-Plateau samt zwei Spawnstellen war abgeschnitten; jetzt fuehrt ein kurzer Gang zur Tuer. Einzelne Bodenfelder im Fels (Tueren von Haeusern, die unter dem Plateau verschwunden sind) sind wieder Fels. Gegner nehmen den naechsten Aufzug statt immer den westlichsten (vorher bis 70 Kacheln Umweg). Der **Brecher** ist im Koerper wieder schmaler als eine Kachel (Radius 17 -> 15, das Bild bleibt gross): mit 17 kam er durch keine Tuer und keinen Aufzug. MG-Salve: die Salvenaufnahme klingt einmal je Abzug statt dreifach uebereinander. MG-Salve und C4 haben einen Klang auch ohne die CODEX-Aufnahmen. Hotbar mit zehn Waffen ragt nicht mehr in den Waffenkasten. `tools/soundboard.py` startet wieder. SCHNEEFELD: alle drei Plateaus sind erreichbar. Neu: `tests/test_pruefung.py`. Netz: kein Protokollwechsel, aber geaenderte Karten und Brecher - Gastgeber und Gast brauchen dieselbe Version |
| 0.34.0 | Aufzuege wieder als E-Treppen mit einem Ebenenschritt und freien Schutzbereichen; C4-Hotbar zeigt Lade- und Zuendestatus, unbewaffnete Spieler haben leere Zombiearme, der Schrotknall startet frueher. | Gastgeber und Gast brauchen dieselbe Version und `karten/staubtal.txt`; kein Protokollwechsel. |
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
