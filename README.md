# DUSTFRONT

Ein Top-Down-Actionspiel mit Einzelspieler und Mehrspieler. Erkunde
mehrstufige Karten, kämpfe gegen Gegner oder andere Spieler und passe
Ausrüstung, Steuerung und Darstellung an.

Geschrieben in Python mit pygame-ce. Schulprojekt, in Arbeit.

**Aktuell: Version 0.34.47, PRE-ALPHA.** Was das heisst, steht weiter unten
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
`ios/bauen.sh`, Schritt für Schritt in [`ios/LIESMICH.md`](ios/LIESMICH.md).
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
| `fahrzeug.py` | Der Buggy: Fahren, Anstossen, Staub, Kaputtgehen |
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
