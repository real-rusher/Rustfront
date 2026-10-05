"""
DUSTFRONT - Bestenliste
=======================

MVP-Punkte und Auszeichnungen ueber alle Runden hinweg; Abschuesse und
Tode bleiben als Nebenwerte erhalten. Liegt neben den Einstellungen im
Benutzerordner (siehe pfade.py), nicht im Spielordner:
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
    return {"fassung": 2, "eintraege": []}


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
                "mvp_punkte": round(float(e.get("mvp_punkte", 0)), 1),
                "mvp_auszeichnungen": int(e.get(
                    "mvp_auszeichnungen", e.get("mvp_siege", 0))),
            })
        except (TypeError, ValueError):
            continue
    return {"fassung": 2, "eintraege": sauber}


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
            eintrag = {"name": name, "abschuesse": 0, "tode": 0, "runden": 0,
                       "mvp_punkte": 0.0, "mvp_auszeichnungen": 0}
            nach_name[name] = eintrag
        eintrag["abschuesse"] += int(erg.get("abschuesse", 0))
        eintrag["tode"] += int(erg.get("tode", 0))
        eintrag["runden"] += 1
        eintrag["mvp_punkte"] = round(
            eintrag.get("mvp_punkte", 0) + float(erg.get("mvp_punkte", 0)), 1)
        eintrag["mvp_auszeichnungen"] += int(bool(erg.get("mvp")))
    daten["eintraege"] = sortiert(list(nach_name.values()))[:HOECHSTENS]
    speichern(daten)
    return daten


def sortiert(eintraege: list[dict]) -> list[dict]:
    """MVP-Punkte zuerst, dann MVP-Auszeichnungen und Kampfwerte."""
    return sorted(eintraege,
                  key=lambda e: (-e.get("mvp_punkte", 0),
                                 -e.get("mvp_auszeichnungen", 0),
                                 -e.get("abschuesse", 0), e.get("tode", 0),
                                 e.get("name", "")))


def mvp_punkte(werte: dict, sieg_bonus: float = 0.0) -> float:
    """Rundenwertung: Kampf, Teamhilfe und Zielspiel zaehlen gemeinsam."""
    abschuesse = max(0, int(werte.get("abschuesse", 0) or 0))
    gegner = max(0, int(werte.get("gegner_abschuesse", 0) or 0))
    bosse = max(0, int(werte.get("boss_abschuesse", 0) or 0))
    schaden = max(0.0, float(werte.get("schaden", 0) or 0))
    treffer = max(0, int(werte.get("treffer_spieler", 0) or 0))
    schuesse = max(0, int(werte.get("schuesse", 0) or 0))
    trefferquote = (min(25.0, max(0, int(werte.get("treffer", 0) or 0))
                       / float(schuesse) * 25.0) if schuesse else 0.0)
    hilfen = max(0, int(werte.get("hilfen", 0) or 0))
    zone = max(0.0, float(werte.get("zonenzeit", 0) or 0))
    medkits = max(0, int(werte.get("medkits", 0) or 0))
    tode = max(0, int(werte.get("tode", 0) or 0))
    # Treffer werden klein gewichtet, damit Dauerfeuer nicht mehr zaehlt
    # als tatsaechlicher Schaden und Abschuesse.
    punkte = (abschuesse * 100 + gegner * 24 + bosse * 70
              + schaden * 0.12 + treffer * 2 + trefferquote + hilfen * 35
              + zone * 1.5 + medkits * 8 - tode * 18 + sieg_bonus)
    return round(max(0.0, punkte), 1)


def beschreibung() -> str:
    """Wo die Datei liegt, fuer die Anzeige."""
    pfad = pfade.datei(DATEI)
    return str(pfad) if pfad else "NICHT SCHREIBBAR"
