# Systematische Gameplay-Bug-Analyse
**Branch:** `ki/jules-multiplayer-test`
**Datum:** 3. Oktober 2024
**Projekt:** DUSTFRONT (Version 0.32.12, PRE-ALPHA)

---

## 1. Übersicht

Diese Dokumentation fasst alle exklusiv im Spielverlauf (Gameplay, Einheiten, Physik, Waffen, Statuseffekte und Kartenränder) identifizierten Bugs und Unstimmigkeiten zusammen. Die Befunde wurden mithilfe der dedizierten Testsuite `tests/test_gameplay_bugs.py` nachgewiesen und ausgewertet.

---

## 2. Identifizierte Gameplay-Bugs (nach Schweregrad)

### 🔴 HOCH (Abstürze & Spielablauf-Inkonsistenzen)

1. **Absturz bei Geschoss-Einschlag ohne Geschwindigkeit (`dustfront/entities.py`)**
   * **Symptom:** Trifft ein Geschoss mit der Geschwindigkeit 0 (`self.tempo = (0, 0)`) ein Ziel, stürzt das Spiel ab.
   * **Fehlermeldung:** `ValueError: Can't normalize Vector of length zero` in `Geschoss.einschlag()`.
   * **Ursache:** `pygame.Vector2(self.tempo).normalize()` prüft vor der Normalisierung nicht, ob die Länge des Geschwindigkeitsvektors größer als Null ist.
   * **Fix-Empfehlung:** Vor der Normalisierung `self.tempo.length_squared() > 0.001` abfragen oder `schub = None` setzen, wenn der Vektor 0 ist.

2. **Wiederbelebung toter Spieler durch verzögerte Heilung (`dustfront/entities.py`)**
   * **Symptom:** Ein Spieler, der kurz vor seinem Tod ein Medkit ansetzt (`heilt_rest = 0.8`), erhält nach Ablauf der 0.8 Sekunden 45 Gesundheit zurück, selbst wenn er bereits gestorben (`lebt == False`) oder am Boden (`am_boden == True`) ist.
   * **Ursache:** In `Spieler.schritt()` wird beim Ablauf von `heilt_rest <= 0` nicht geprüft, ob `self.lebt` wahr ist und der Spieler auf den Beinen steht.
   * **Fix-Empfehlung:** In `Spieler.schritt()` `if self.lebt and not getattr(self, "am_boden", False):` ergänzen, bevor `self.leben` erhöht wird.

---

### 🟡 MITTEL (Physik, Bewegung & Waffensteuerung)

3. **Dash-Übersteuerung während eines Sturzes (`dustfront/entities.py`)**
   * **Symptom:** Wenn ein Spieler nahe einer Abgrundkante dasht und ins Loch stürzt (`stuerzen()`), behält er während des gesamten Sturzes in der Luft das volle Dash-Tempo von 430 px/s bei.
   * **Ursache:** `if self.dash_rest > 0:` überschreibt in `Spieler.schritt()` die normale Sturz-Luftsteuerung (`K.STURZ["luftsteuerung"]` = 55% = 59 px/s).
   * **Fix-Empfehlung:** Beim Auslösen von `stuerzen()` sollte `self.dash_rest = 0.0` zurückgesetzt werden.

4. **Fehlendes Abbrechen der Heilung bei Waffenwechsel (`dustfront/entities.py`)**
   * **Symptom:** Wenn ein Spieler ein Medkit ansetzt (`heilt_rest = 0.8`) und sofort mit 1-9 die Waffe wechselt, läuft der Heilungs-Timer im Hintergrund weiter und stellt nach 0.8s Leben wieder her.
   * **Ursache:** `Spieler.abbrechen()` setzt `nachlade_rest = 0.0` und `fokus = 0.0` zurück, setzt aber `heilt_rest` nicht auf `0.0`.
   * **Fix-Empfehlung:** `self.heilt_rest = 0.0` in `Spieler.abbrechen()` eintragen.

---

### 🟢 NIEDRIG (Kartenränder & Umgebungslogik)

5. **Kartenränder außerhalb des Gitters werden als Sturzlöcher gewertet (`dustfront/world.py`)**
   * **Symptom:** Koordinaten außerhalb der Kartengrenzen (z. B. `x < 0` oder `x >= breite * 32`) liefern bei `Ebene.loch(tx, ty)` den Wert `True`.
   * **Ursache:** `Ebene.kachel(tx, ty)` gibt für Positionen außerhalb des Feldes `K.LEER` (`0`) zurück. Kachel `0` hat in `K.KACHELN` die Eigenschaft `"loch": True`.
   * **Fix-Empfehlung:** `Ebene.loch(tx, ty)` so anpassen, dass außerhalb der Karte stehende Kacheln `False` zurückgeben oder als unpassierbar behandelt werden.

6. **Lenkraketen stürzen außerhalb der Karte automatisch ab (`dustfront/entities.py`)**
   * **Symptom:** Fliegt eine gelenkte Rakete (`Rakete`) außerhalb des sichtbaren Spielfeldes, wechselt sie bei `_ebene_wechseln()` fälschlicherweise automatisch auf die tiefere Ebene.
   * **Ursache:** Durch die obige Loch-Erkennung außerhalb der Kartengrenzen erkennt die Rakete außerhalb der Karte ein vermeintliches "Loch" und fällt hinunter.
   * **Fix-Empfehlung:** Kacheln außerhalb der Kartengrenzen bei `_ebene_wechseln()` nicht als Loch werten.

---

## 3. Testnachweise

Sämtliche Fehler sind in `tests/test_gameplay_bugs.py` als fehlschlagende Testfälle hinterlegt:
* `test_01_heilung_nach_tot_oder_am_boden` (FAIL)
* `test_02_waffenwechsel_bricht_heilung_nicht_ab` (FAIL)
* `test_03_dash_waehrend_sturz` (FAIL)
* `test_05_geschoss_einschlag_null_vektor` (FAIL)
* `test_06_rakete_ausserhalb_karte_ebenenwechsel` (FAIL)
* `test_07_kartenrand_loch_erkennung` (FAIL)
