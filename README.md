# DUSTFRONT

Ein Top-Down-Spiel auf dem Kontinent Veld. Du steuerst einen modularen
Wandler, baust ihn aus Schrott weiter aus und bewegst dich zwischen drei
Fraktionen: der Kolonne, dem Chor und den Freien Werften. Beide Spielmodi
teilen dieselbe 90-Grad-Draufsicht, du wechselst mit Tab zwischen "an Bord"
und "Fahr-Modus".

Geschrieben in Python mit pygame-ce. Schulprojekt, in Arbeit.

**Aktuell: Version 0.4.0, PRE-ALPHA.** Was das heisst, steht weiter unten
unter [Versionsnummern](#versionsnummern).

## Mitwirkende

Nicolas, Nikolaus, Marlon, Alfred.

## Stand

| Teil | Zustand |
| --- | --- |
| Splash-Sequenz | fertig, fuenf Karten mit eigenem Ton |
| Hauptmenue | fertig, inklusive Optionen und Spielstand |
| Spiel selbst | noch nicht begonnen, Platzhalter-Szene im Menue |

## Starten

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

Gebraucht werden Python 3.10 bis 3.14 und pygame-ce (getestet mit 2.5.8).
Sonst nichts: Schrift, Grafik und Ton entstehen zur Laufzeit, es gibt keine
Assets im Repo.

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

## Dateien

| Datei | Inhalt |
| --- | --- |
| `rustfront_menu.py` | Hauptmenue, Kaltstart, Optionen, Spielstand, Einstiegspunkt |
| `rustfront_splash.py` | Ablauf, Zeitdehnung und Klangsynthese der Splash-Sequenz |
| `splash_engine.py` | Zeichenwerk der Splash-Sequenz, portiert aus der Web-Fassung |

Zur Laufzeit entstehen `rustfront_settings.json` (Einstellungen) und
`rustfront_save.json` (Spielstand). Beide stehen in der `.gitignore` und
gehoeren nicht ins Repo.

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

## Anpassen

Alle Stellschrauben stehen oben in der jeweiligen Datei.

* **Spielname**: `SPIEL_TITEL` in `rustfront_menu.py`, `TEXTE["name"]` in
  `rustfront_splash.py`.
* **Version und Phase**: `VERSION` und `PHASE` in `rustfront_menu.py`.
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

Die Platzhalter-Szene am Ende von `rustfront_menu.py` wird spaeter durch die
echte Spielschleife ersetzt.
