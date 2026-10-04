# assets/sfx — Klaenge

Lege pro Klang die Aufnahme in den gleichnamigen Unterordner, zum Beispiel
`assets/sfx/medkit/aufnahme.wav`. Der Dateiname darin ist frei; `.wav` und
`.ogg` werden erkannt. Mehrere Dateien im Ordner sind ebenfalls moeglich und
werden als zufaellige Fassungen verwendet. Ordneraufnahmen haben Vorrang vor
den bisherigen flachen Dateien wie `assets/sfx/medkit.wav`; diese bleiben
weiterhin unterstuetzt.

## Welche Namen es gibt

| Name | Wann er spielt |
| --- | --- |
| `schuss_repetierer` | Repetierer |
| `schuss_sturm` | Sturmgewehr |
| `schuss_schrot` | Schrot |
| `schuss_scharf` | Scharfschuetze |
| `schuss` | jede Schusswaffe, die keine eigene Datei hat |
| `schuss_lmg` | leichtes Maschinengewehr |
| `granate` | Einschlag der Granate |
| `wurf` | die Granate verlaesst die Hand |
| `nahkampf` | Brecheisen |
| `medkit` | Medkit angelegt |
| `aufheben` | etwas vom Boden genommen |
| `menue` | Auswahl wandert |
| `menue_ok` | Auswahl bestaetigt |
| `sturz` | Aufsetzen nach einem Fall |
| `molotov` | Glas zerbricht und Feuer faengt |
| `blend` | Knall der Blendgranate |
| `rakete` | Raketenabschuss |
| `erfasst` | Erfassung einer gelenkten Rakete steht |
| `blend_pfeifen` | Pfeifen nach dem Blendknall |
| `speien` | Speier spuckt |
| `boss_ansage` | Boss kuendigt seinen Angriff an |
| `dash` | kurzer Stoss beim Dash |
| `ruf` | Spieler am Boden ruft nach Hilfe |
| `herzschlag` | eigener Herzschlag bei wenig Leben |

Die Liste steht als `KLANG_NAMEN` in `dustfront/config.py`.
`python -m dustfront --assets` sagt, welcher Name gerade aus einer Datei
kommt.

## Gesucht wird in zwei Stufen

Fuer `schuss_repetierer` schaut das Spiel erst in `schuss_repetierer/`, dann
nach den bisherigen Dateien `schuss_repetierer.wav` und `schuss.wav`. Eine
einzige Datei `schuss.wav` deckt also weiterhin alle Schusswaffen ab, bis
eine eigene Aufnahme hinzukommt.

## Abwechslung

Dauerfeuer aus einer einzigen Kopie klingt nach Maschine. Deshalb darf jeder
Name mehrfach vorkommen:

    schuss_sturm.wav
    schuss_sturm_1.wav
    schuss_sturm_2.wav
    ...   bis _8

Das Spiel waehlt bei jedem Schuss zufaellig eine der Fassungen. Fehlen sie,
erzeugt es sich drei leicht verschiedene Kopien selbst.

## Format

44100 Hz, 16 Bit. Andere Raten nimmt pygame auch an, klingen aber
verstimmt, weil der Mischer fest auf 44100 Hz laeuft (`RATE` in
`dustfront/audio.py`).

Kurz halten und vorn ohne Stille anfangen: ein Schuss, der erst nach 50
Millisekunden losgeht, fuehlt sich im Spiel traege an.
