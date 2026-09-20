# assets/sfx — Klaenge

Dieselbe Regel wie bei den Bildern eine Ebene hoeher: eine Datei
`assets/sfx/<name>.wav` ersetzt den im Code berechneten Klang. Keine
Codeaenderung noetig. `.ogg` geht auch.

## Welche Namen es gibt

| Name | Wann er spielt |
| --- | --- |
| `schuss_repetierer` | Repetierer |
| `schuss_sturm` | Sturmgewehr |
| `schuss_schrot` | Schrot |
| `schuss_scharf` | Scharfschuetze |
| `schuss` | jede Schusswaffe, die keine eigene Datei hat |
| `granate` | Einschlag der Granate |
| `wurf` | die Granate verlaesst die Hand |
| `nahkampf` | Brecheisen |
| `medkit` | Medkit angelegt |
| `aufheben` | etwas vom Boden genommen |
| `menue` | Auswahl wandert |
| `menue_ok` | Auswahl bestaetigt |

Die Liste steht als `KLANG_NAMEN` in `dustfront/config.py`.
`python -m dustfront --assets` sagt, welcher Name gerade aus einer Datei
kommt.

## Gesucht wird in zwei Stufen

Fuer `schuss_repetierer` schaut das Spiel erst nach
`schuss_repetierer.wav`, dann nach `schuss.wav`. Eine einzige Datei
`schuss.wav` deckt also alle Schusswaffen ab, bis eine eigene danebenliegt.

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
