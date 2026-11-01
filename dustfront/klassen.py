"""Klassen (seit 0.34.73, K.KLASSEN).

Eine Klasse steht im Satz der Ausruestung (`loadout["klasse"]`). Sie sagt,
woraus man Waffen und Wurfwaffen waehlen darf, und gibt Vorteile, die die
Figur traegt (Leben, Tempo, Nachladen, Feuerschutz, Schaden an Fahrzeugen,
Schild). Die Faehigkeit auf der Taste C legt etwas aus ausruestung.py hin
- wie Bauen und Fallen erst im Testmodus (`Gefecht.faehigkeiten_an`).

Die Vorteile rechnet der Gastgeber aus dem Satz, den er von jedem Gast
bei der Anmeldung bekommt - beim Gast selbst wird nichts angewendet.
"""
from __future__ import annotations

from . import config as K


def daten(klasse: str) -> dict:
    """Die Werte einer Klasse; FREI fuer "" und Unbekanntes."""
    return K.KLASSEN.get(klasse or "", K.KLASSE_FREI)


def name(klasse: str) -> str:
    return daten(klasse)["name"]


def waffen_von(klasse: str) -> tuple:
    """Woraus der Satz dieser Klasse Waffen waehlt."""
    lo = K.LOADOUT
    d = K.KLASSEN.get(klasse or "")
    if d is None:
        return tuple(lo["auswahl_waffen"])
    return tuple(w for w in d["waffen"] if w in lo["auswahl_waffen"])


def wuerfe_von(klasse: str) -> tuple:
    lo = K.LOADOUT
    d = K.KLASSEN.get(klasse or "")
    if d is None:
        return tuple(lo["auswahl_wuerfe"])
    return tuple(w for w in d["wuerfe"] if w in lo["auswahl_wuerfe"])


def anwenden(k) -> None:
    """Die Vorteile der Klasse an die Figur (bei jedem Einsteigen)."""
    lo = getattr(k, "loadout", None) or {}
    klasse = lo.get("klasse", "") if isinstance(lo, dict) else ""
    d = daten(klasse)
    k.klasse = klasse if klasse in K.KLASSEN else ""
    voll = K.SPIELER["leben"] * float(d.get("leben", 1.0))
    if abs(k.max_leben - voll) > 0.01:
        k.leben = voll if k.leben >= k.max_leben else min(k.leben, voll)
        k.max_leben = voll
    k.klassen_tempo = float(d.get("tempo", 1.0))
    k.nachlade_faktor = float(d.get("nachladen", 1.0))
    k.kuehl_faktor = float(d.get("kuehlen", 1.0))
    k.feuer_schutz = float(d.get("feuer", 1.0))
    k.fahrzeug_bonus = float(d.get("fahrzeug", 1.0))
    k.fahrzeug_schutz = float(d.get("fahrzeug_schutz", 1.0))
    k.aufhelf_faktor = float(d.get("aufhelfen", 1.0))
    k.schild = bool(d.get("schild", False)) or bool(getattr(k, "schild_fest", False))
    if d.get("medkits") and hasattr(k, "medkits"):
        k.medkits = max(k.medkits, K.MEDKIT.get("start", 1) + int(d["medkits"]))
    if d.get("granaten"):
        for w in getattr(k, "waffen", ()):
            if K.WAFFEN.get(w, {}).get("art") == "wurf" and hasattr(k, "vorrat"):
                k.vorrat[w] = k.vorrat.get(w, 0) + int(d["granaten"])
    k.faehigkeit_rest = {}


def faehigkeit_bereit(k):
    """Die erste Faehigkeit, deren Pause um ist - (Art, Pause) oder None."""
    d = daten(getattr(k, "klasse", ""))
    rest = getattr(k, "faehigkeit_rest", {})
    for art, pause in d.get("faehigkeit", ()):
        if rest.get(art, 0.0) <= 0.0:
            return art, pause
    return None


def faehigkeiten_schritt(k, dt: float) -> None:
    rest = getattr(k, "faehigkeit_rest", None)
    if rest:
        for art in list(rest):
            rest[art] = max(0.0, rest[art] - dt)


# Welcher Eintrag aus ausruestung.ARTEN zu welcher Faehigkeit gehoert.
FAEHIGKEIT_ARTEN = {
    "munitionskiste": "MUNITIONSKISTE (STEHT)",
    "sanitasche": "SANITASCHE",
    "geschuetz": "SELBSTSCHUSSANLAGE",
    "horchposten": "HORCHPOSTEN",
    "sprengfalle": "SPRENGFALLE (PLATTE)",
    "sandsackwand": "SANDSACKWAND",
    "kanister": "BENZINKANISTER",
    "drohne": "SPÄHDROHNE",
    "stacheldraht": "STACHELDRAHT",
}
FAEHIGKEIT_NAMEN = {
    "munitionskiste": "MUNITIONSKISTE", "sanitasche": "SANITASCHE",
    "geschuetz": "SELBSTSCHUSSANLAGE", "horchposten": "HORCHPOSTEN",
    "sprengfalle": "SPRENGFALLE", "sandsackwand": "SANDSACKWAND",
    "kanister": "BENZINKANISTER", "drohne": "SPÄHDROHNE",
    "stacheldraht": "STACHELDRAHT", "kraehenfuesse": "KRÄHENFÜSSE",
}


def faehigkeit_nutzen(gefecht, k) -> str:
    """Die Taste C: die naechste bereite Faehigkeit vor die Figur legen.
    Gibt den Namen zurueck, oder "" wenn nichts ging."""
    if not getattr(gefecht, "faehigkeiten_an", False) or not k.lebt or k.am_boden:
        return ""
    if getattr(k, "fahrzeug", None) is not None:
        return ""
    wahl = faehigkeit_bereit(k)
    if wahl is None:
        return ""
    art, pause = wahl
    import pygame
    from . import ausruestung
    from .entities import Nagelfeld
    vorn = k.pos + pygame.Vector2(26, 0).rotate(k.winkel)
    if art == "kraehenfuesse":
        gefecht.welt.naegel.append(Nagelfeld(vorn, k.ebene, von=k))
    else:
        for ding in ausruestung.bauen(FAEHIGKEIT_ARTEN[art], vorn, k.ebene, k.fraktion, k.winkel):
            gefecht.welt.dazu(ding)
    k.faehigkeit_rest[art] = pause
    gefecht.welt.klang("aufheben", 0.6, k.pos, k.ebene)
    return FAEHIGKEIT_NAMEN.get(art, art.upper())
