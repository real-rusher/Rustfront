"""
DUSTFRONT - Bestenliste
=======================

Wer wie viele Abschuesse hatte, ueber alle Runden hinweg. Liegt neben den
Einstellungen im Benutzerordner (siehe pfade.py), nicht im Spielordner:
wer das Spiel neu herunterlaedt, soll seine Liste behalten.

Gefuehrt wird sie beim Gastgeber - er ist der einzige, der alle Ergebnisse
sicher kennt. Ein Gast bekommt die Liste am Rundenende geschickt und legt
sie ebenfalls ab, damit jeder seine eigene Geschichte behaelt.

Eine beschaedigte Datei kostet hoechstens die Liste, nie den Start.
"""

from __future__ import annotations

import json

from . import pfade

DATEI = "bestenliste.json"
HOECHSTENS = 100          # so viele Eintraege werden behalten


def _leer() -> dict:
    return {"fassung": 1, "eintraege": []}


def laden() -> dict:
    pfad = pfade.datei(DATEI)
    if pfad is None or not pfad.is_file():
        return _leer()
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _leer()
    if not isinstance(daten, dict) or not isinstance(daten.get("eintraege"), list):
        return _leer()
    # Nur Eintraege behalten, die wirklich so aussehen, wie sie sollen.
    sauber = []
    for e in daten["eintraege"]:
        if not isinstance(e, dict):
            continue
        try:
            sauber.append({
                "name": str(e.get("name", "?"))[:32],
                "abschuesse": int(e.get("abschuesse", 0)),
                "tode": int(e.get("tode", 0)),
                "runden": int(e.get("runden", 1)),
            })
        except (TypeError, ValueError):
            continue
    return {"fassung": 1, "eintraege": sauber}


def speichern(daten: dict) -> bool:
    pfad = pfade.datei(DATEI)
    if pfad is None:
        return False
    try:
        pfad.write_text(json.dumps(daten, indent=1), encoding="utf-8")
        return True
    except OSError:
        return False


def eintragen(ergebnisse: list[dict]) -> dict:
    """Ein Rundenergebnis dazurechnen und die Liste zurueckgeben.

    ergebnisse ist eine Liste aus {"name", "abschuesse", "tode"}. Gleiche
    Namen werden zusammengezaehlt, damit die Liste ueber Runden hinweg
    etwas aussagt und nicht nur die letzte Partie zeigt.
    """
    daten = laden()
    nach_name = {e["name"]: e for e in daten["eintraege"]}
    for erg in ergebnisse:
        name = str(erg.get("name", "?"))[:32]
        eintrag = nach_name.get(name)
        if eintrag is None:
            eintrag = {"name": name, "abschuesse": 0, "tode": 0, "runden": 0}
            nach_name[name] = eintrag
        eintrag["abschuesse"] += int(erg.get("abschuesse", 0))
        eintrag["tode"] += int(erg.get("tode", 0))
        eintrag["runden"] += 1
    daten["eintraege"] = sortiert(list(nach_name.values()))[:HOECHSTENS]
    speichern(daten)
    return daten


def sortiert(eintraege: list[dict]) -> list[dict]:
    """Beste zuerst: viele Abschuesse, wenige Tode, dann nach Namen."""
    return sorted(eintraege,
                  key=lambda e: (-e.get("abschuesse", 0), e.get("tode", 0),
                                 e.get("name", "")))


def beschreibung() -> str:
    """Wo die Datei liegt, fuer die Anzeige."""
    pfad = pfade.datei(DATEI)
    return str(pfad) if pfad else "NICHT SCHREIBBAR"
