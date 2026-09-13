# DUSTFRONT

Ein Top-Down-Spiel auf dem Kontinent Veld. Du steuerst einen modularen
Wandler, baust ihn aus Schrott weiter aus und bewegst dich zwischen drei
Fraktionen: der Kolonne, dem Chor und den Freien Werften. Beide Spielmodi
teilen dieselbe 90-Grad-Draufsicht, du wechselst mit Tab zwischen "an Bord"
und "Fahr-Modus".

Geschrieben in Python mit pygame-ce. Schulprojekt, in Arbeit.

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

## Anpassen

Alle Stellschrauben stehen oben in der jeweiligen Datei.

* **Spielname**: `SPIEL_TITEL` in `rustfront_menu.py`, `TEXTE["name"]` in
  `rustfront_splash.py`.
* **Dauer des Intros**: `PHASEN` in `rustfront_splash.py`. Jede Karte hat drei
  Abschnitte (Aufbau, Standbild, Abblende) mit jeweils der echten Dauer in
  Sekunden. `TEMPO` skaliert alles auf einmal, 1.3 bringt die Sequenz von rund
  35 auf etwa 27 Sekunden.
* **Einzelne Karten abschalten**: `KARTEN_AN`.
* **Firmennamen und Untertitel**: `TEXTE`.
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

## Einbinden ins Spiel

```python
from rustfront_menu import run_menu

ergebnis = run_menu()
# {"action": "new_game" | "continue" | "quit",
#  "region": ..., "difficulty": ..., "callsign": ...}
```

Die Platzhalter-Szene am Ende von `rustfront_menu.py` wird spaeter durch die
echt Spielschleife ersetzt.
