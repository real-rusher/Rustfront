# Systematische Fehler- und Bug-Analyse
**Branch:** `ki/jules-multiplayer-test`
**Datum:** 3. Oktober 2024
**Projekt:** DUSTFRONT (Version 0.32.12, PRE-ALPHA)

---

## 1. Übersicht

Diese Dokumentation fasst alle bei der Inspektion der Codebasis sowie bei der Ausführung der erweiterten Testsuiten (`tests/test_bugs_erfassung.py`) identifizierten und behobenen Fehlerquellen, Randfälle und Unstimmigkeiten zusammen.

---

## 2. Identifizierte und Behobene Befunde

### A. Menüs & Benutzeroberfläche (UI / Layout)
1. **Kollision von Hinweistext und Fußzeile (`rustfront_menu.py`)**:
   * **Symptom**: In `MainPage` führte der Startabstand `py = 112` dazu, dass zweizeilige Hinweistexte (`draw_hint`) über die Fußzeilen-Trennlinie und den Fußzeilentext bei `y = 254` gezeichnet wurden.
   * **Ursache**: Der Vertikalabstand der Menübox war zu weit unten angesetzt.
   * **Behebung**: `py` in `MainPage` auf `100` korrigiert sowie eine Höhenschutzklausel in `Page.draw_hint` eingebaut (`if y + 7 >= VH - 20: break`).

2. **Überlappungsgefahr bei langen Dateipfaden und Fehlermeldungen (`dustfront/menues.py`)**:
   * **Symptom**: `pfade.beschreibung()` auf der Einstellungsseite und `konto.fehler` in der Anmeldemaske besaßen keine automatische Breitenbegrenzung.
   * **Ursache**: Unbegrenzte Zeilenausgabe bei variablen String-Längen.
   * **Behebung**: Absicherung durch `ui.kuerzen(..., max_breite)`.

3. **Gefahr von Textüberlappungen bei UI-Elementen (`dustfront/ui.py`)**:
   * **Symptom**: Bausteine wie `Knopf`, `Reiter`, `Wahl`, `Schalter`, `Regler`, `Platzhalter` und `spalteneintrag` nutzten unbegrenzten Textsatz.
   * **Ursache**: Wenn Bezeichnungen oder Werte breiter als das Element waren, ragten sie über Ränder oder Pfeile hinaus.
   * **Behebung**: Konsequente Absicherung der Beschriftungen durch `ui.kuerzen`.

4. **Kollision von Waffennamen und Waffenart im Inventar (`dustfront/inventar.py`)**:
   * **Symptom**: In der Detailansicht (`_angaben`) bestand bei langen Waffennamen die Gefahr einer Kollision mit der rechtsbündigen Typenbezeichnung (`SCHUSSWAFFE`, `WURFWAFFE`, `NAHKAMPF`).
   * **Behebung**: Waffennamen mit `ui.kuerzen(d["name"], r.width - 12 - art_w - 6)` dynamisch eingekürzt.

---

### B. Konfiguration & Regelwerk (`dustfront/config.py`, `regeln.py`)
1. **Waffenschaden bei Hilfswaffen**:
   * **Befund**: `WAFFEN["rauch"]["schaden"]` ist vertragsgemäß `0.0` (Rauchgranaten machen keinen Schaden). Testprüfungen müssen `schaden >= 0` erwarten.
2. **Robustheit von `R.saeubern` bei Fehlingaben**:
   * **Befund**: Bei ungültigen Spielmodi oder negativen Endwerten setzt `R.saeubern` Werte verlässlich auf gültige Vorgaben zurück.

---

### C. Konten & Journal (`dustfront/konto.py`, `ablage.py`)
1. **Namensvalidierung**:
   * **Befund**: `ablage.name_saeubern("   ")` ergibt eine leere Zeichenkette `""`. `ablage.name_pruefen("")` fängt leere Namen ab und meldet `"NAME ZU KURZ"`.
2. **Idempotenz im Journal**:
   * **Befund**: Mehrfaches Aufrufen von `j.abhaken([partie_id])` ist idempotent und führt zu keinen Doppelungen oder Inkonsistenzen.

---

### D. Netzwerk & Protokoll (`dustfront/netz.py`)
1. **Schutz gegen beschädigte JSON-Pakete**:
   * **Befund**: `netz.Leitung.holen()` fängt kaputtes JSON per `try-except` ab.
2. **Schutz gegen Pufferüberläufe**:
   * **Befund**: Überschreitet eine eingehende Zeile `K.NETZ["hoechstzeile"]`, schließt die Leitung automatisch, um DoS-Angriffe oder Speicherüberläufe zu verhindern.

---

## 3. Testabdeckung (`tests/test_bugs_erfassung.py`)

Zur dauerhaften Sicherstellung wurde die Testsuite `tests/test_bugs_erfassung.py` mit 15 gezielten Tests hinzugefügt:
* **Integrität**: Prüfung aller Waffen- und Bildmaße.
* **Datei-Toleranz**: Verhalten bei beschädigten JSON-Einstellungsdateien.
* **Tastenschutz**: Schutz fester Tasten vor Umbelegung.
* **Regeln**: Extremwert-Säuberung und Stufen-Grenzen.
* **Rundenplanung**: Durchsetzung der maximalen Rundenanzahl im Plan.
* **Konten & Journal**: Namensbereinigung und Idempotenz.
* **UI**: Verhalten von `ui.kuerzen` und Reglern bei Extremwerten.
* **Netzwerk**: Verhalten bei defektem JSON und unvollständigen Sockets.
