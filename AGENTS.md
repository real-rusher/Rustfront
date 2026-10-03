# Hinweise fuer KI-Assistenten (Jules, Gemini, Copilot, Claude ...)

DUSTFRONT: ein Top-Down-Spiel in Python mit pygame-ce. Wer hier Code
aendert, haelt sich an diese Regeln.

## Arbeitsweise

* **Nie direkt auf `main` oder `multiplayer-test` pushen.** Immer auf einem
  eigenen Branch arbeiten (z. B. `ki/<thema>`) und einen Pull Request
  gegen `multiplayer-test` stellen. Der Besitzer prueft und uebernimmt.
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

## Pruefen vor dem Pull Request

```
pip install pygame-ce
python tests/test_spiel.py      # endet mit "FEHLER: keine"
python tests/test_menues.py
python -m dustfront --kontoseite && python tests/test_konto.py
```

Alle drei muessen mit `FEHLER: keine` enden. Fuer neues Verhalten einen
Test in `tests/test_spiel.py` ergaenzen, im Stil der vorhandenen
(`pruef("was gelten soll", bedingung, zusatz)`). Tests nie abschalten
oder abschwaechen, damit sie gruen werden.
