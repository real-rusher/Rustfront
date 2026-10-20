# Hinweise fuer KI-Assistenten (Jules, Gemini, Copilot, Claude ...)

DUSTFRONT: ein Top-Down-Spiel in Python mit pygame-ce. Wer hier Code
aendert, haelt sich an diese Regeln.

## Arbeitsweise

* **`main` bleibt geschuetzt:** Nie direkt auf `main` pushen.
* KI-Agenten, deren Name **nicht Jules** ist, arbeiten direkt auf
  `multiplayer-test` und pushen ihre fertigen Aenderungen dort als Commit.
  **Jules** arbeitet auf einem eigenen Branch (z. B. `ki/<thema>`) und
  stellt einen Pull Request gegen `multiplayer-test`; der Besitzer prueft
  und uebernimmt ihn.
* Kleine, gezielte Aenderungen. Nichts nebenbei umbauen oder umbenennen.
* **Niemals einen geheimen Schluessel (Supabase secret/service key) in
  eine Datei schreiben.** Der Schluessel im Code ist der oeffentliche
  (publishable) und darf dort stehen.

## Stil

* Namen und Kommentare auf **Deutsch**, ohne Umlaute im Code (ae, oe, ue,
  ss). Im Spiel angezeigter Text darf Umlaute haben.
* Den Stil der umliegenden Datei uebernehmen. Bei nicht offensichtlichen
  Entscheidungen einen Kommentar, der den Grund nennt (warum, nicht was).
* Zahlen zum Einstellen (Tempo, Schaden, Zeiten) gehoeren nach
  `dustfront/config.py`, nicht verstreut in den Code.
* Muss laufen mit **Python 3.8 bis 3.14**: keine Syntax, die neuer als 3.8
  ist (kein `match`, keine `X | Y`-Typen ausserhalb von Anmerkungen; die
  Module haben `from __future__ import annotations`).

## Version und Netz

* Jede Aenderung bekommt eine neue Version: `VERSION` in
  `rustfront_menu.py` erhoehen (letzte Stelle), die Zeile "Aktuell: Version"
  oben im `README.md` anpassen und in der Versionstabelle des README eine
  Zeile ergaenzen (die neueste steht zuoberst).
* Gastgeber und Gast muessen dieselbe Version haben. Was das Netz,
  das Gefecht (`dustfront/mehrspieler.py`, `netz.py`, `lan.py`) oder die
  Karten (`karten/*.txt`) betrifft, **in der README-Zeile ausdruecklich
  sagen** und in `docs/MEHRSPIELER.md` unter "Was im Netz wann dazukam"
  eintragen.
* Statistiken (Konto, Bestenliste) duerfen nie auseinanderlaufen.

## Testmodus: jedes neue Feature gehoert hinein

Seit 0.34.28 gibt es den **Testmodus** (`dustfront/testmodus.py`, im
Hauptmenue TESTMODUS, oder `python -m dustfront --testmodus`). Ab jetzt
gilt fuer **jedes neue Feature**:

* Was sich in die Welt setzen laesst (neue Gegner, Waffen, Wurfwaffen,
  Beute, Fahrzeuge, Objekte, Spielarten-Ziele wie der Kreis), bekommt
  einen **Eintrag im Spawner**: `eintraege()` in `testmodus.py`, mit den
  Einstellungen, die es braucht (`OPTIONEN`). Gegner, Bosse und
  Zielpuppen kommen von selbst aus den Tabellen in `config.py`.
* Was sich einschalten oder ausloesen laesst (neue Regeln, neue KI,
  neue Zustaende), bekommt eine **Zeile im Testmenue** (`_menue_zeilen` /
  `menue_wirken`) oder eine **Taste** auf dem Ziffernblock (`TASTEN`,
  `taste`). Auf jeder Taste steht, was sie tut.
* Was eine KI neu tut, zeigt die **INFO-Ansicht** (Taste 8,
  `_info_zeichnen`) - Linie oder Zustandstext.
* Der Beobachter darf von nichts wahrgenommen oder beeinflusst werden:
  er steht nie in `welt.wesen` und nie in `kaempfer`. Wer neue
  Wahrnehmung baut, fragt diese Listen (oder `ki_unsichtbar`) und nie
  `self.ich` des Gefechts.
* Dazu ein Test in `tests/test_spiel.py`, Abschnitt Testmodus, und eine
  Zeile in `docs/TESTMODUS.md`.

## KI der Wesen

Der Plan fuer die KI aller Wesen (zielorientiert, GOAP) steht in
`docs/KI.md`, mit allen Wuenschen des Besitzers und einem Fahrplan in
Schritten. Wer gesagt bekommt "bau jetzt Schritt N ein", liest dort
zuerst Abschnitt 2 und den Schritt. Ziele, Aktionen und Spezies gehoeren
in `wesen/*.txt`, nicht in den Code.

## Pruefen vor dem Pull Request

```
pip install pygame-ce
python tests/test_spiel.py      # endet mit "FEHLER: keine"
python tests/test_menues.py
python -m dustfront --kontoseite && python tests/test_konto.py
python tests/test_pruefung.py   # Syntax aller Dateien, Karten, Aufzuege
```

Alle vier muessen mit `FEHLER: keine` enden. Fuer neues Verhalten einen
Test in `tests/test_spiel.py` ergaenzen, im Stil der vorhandenen
(`pruef("was gelten soll", bedingung, zusatz)`). Tests nie abschalten
oder abschwaechen, damit sie gruen werden.
