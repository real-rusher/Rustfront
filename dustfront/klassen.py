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


def plaetze_von(klasse: str) -> tuple:
    """Welche Plaetze ein Satz dieser Klasse hat (seit 0.34.91): Haupt-
    und Seitenwaffe, manche Klassen dazu eine Spezialwaffe, mit Schild
    nur die Seitenwaffe."""
    d = K.KLASSEN.get(klasse or "")
    if d is None:
        return tuple(K.PLAETZE_VORGABE)
    return tuple(d.get("plaetze", K.PLAETZE_VORGABE))


def platz_von(waffe: str) -> str:
    """Welcher Platz eine Waffe ist (K.WAFFEN_PLATZ), Vorgabe "haupt"."""
    return K.WAFFEN_PLATZ.get(waffe, "haupt")


def waffen_von(klasse: str, platz: str | None = None) -> tuple:
    """Woraus der Satz dieser Klasse Waffen waehlt - mit `platz` nur die
    fuer diesen Platz. Ohne Klasse jede Haupt- und Seitenwaffe; eine
    Spezialwaffe gibt es nur mit einer Klasse, die den Platz hat."""
    lo = K.LOADOUT
    d = K.KLASSEN.get(klasse or "")
    plaetze = plaetze_von(klasse)
    quelle = lo["auswahl_waffen"] if d is None else d["waffen"]
    return tuple(w for w in quelle if w in lo["auswahl_waffen"]
                 and platz_von(w) in plaetze
                 and (platz is None or platz_von(w) == platz))


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
    k.nahkampf_faktor = float(d.get("nahkampf", 1.0))
    k.nahkampf_takt_faktor = float(d.get("nahkampf_takt", 1.0))
    k.schild = bool(d.get("schild", False)) or bool(getattr(k, "schild_fest", False))
    if d.get("medkits") and hasattr(k, "medkits"):
        k.medkits = max(k.medkits, K.MEDKIT.get("start", 1) + int(d["medkits"]))
    if d.get("granaten"):
        for w in getattr(k, "waffen", ()):
            if K.WAFFEN.get(w, {}).get("art") == "wurf" and hasattr(k, "vorrat"):
                k.vorrat[w] = k.vorrat.get(w, 0) + int(d["granaten"])
    k.faehigkeit_rest = {}


# Wie ein Vorteil im Menue heisst (seit 0.34.79). Faktor > 1 heisst bei
# "leben", "tempo" und "fahrzeug" mehr; bei den anderen ist weniger
# besser (Nachladezeit, Feuerschaden ...), darum steht dort "kleiner".
_VORTEIL_TEXTE = (
    ("leben", "LEBEN", "groesser"),
    ("tempo", "TEMPO", "groesser"),
    ("nachladen", "SCHNELLER NACHLADEN", "kleiner"),
    ("kuehlen", "SCHNELLER ABKÜHLEN", "kleiner"),
    ("feuer", "WENIGER FEUERSCHADEN", "kleiner"),
    ("aufhelfen", "SCHNELLER AUFHELFEN", "kleiner"),
    ("nahkampf", "NAHKAMPFSCHADEN (F)", "groesser"),
    ("nahkampf_takt", "SCHNELLER ZUSCHLAGEN (F)", "kleiner"),
    ("fahrzeug", "SCHADEN AN FAHRZEUGEN", "groesser"),
    ("fahrzeug_schutz", "WENIGER SCHADEN AM EIGENEN FAHRZEUG", "kleiner"),
)


def vorteile(klasse: str) -> list:
    """Was die Klasse an der Figur aendert, als kurze Zeilen fuers Menue
    (AUSRUESTUNG zeigt sie, wenn die Zeile KLASSE gewaehlt ist). Ein
    Nachteil steht mit Minus da - wer eine Klasse waehlt, soll auch
    sehen, was sie kostet."""
    d = daten(klasse)
    raus = []
    for schluessel, text, richtung in _VORTEIL_TEXTE:
        f = float(d.get(schluessel, 1.0))
        if abs(f - 1.0) < 1e-6:
            continue
        prozent = int(round(abs(f - 1.0) * 100))
        gut = (f > 1.0) == (richtung == "groesser")
        if richtung == "groesser":
            raus.append("%s%d%% %s" % ("+" if f > 1.0 else "-", prozent, text))
        else:
            raus.append(("%d%% %s" % (prozent, text)) if gut
                        else ("-%d%% %s" % (prozent, text)))
    if d.get("medkits"):
        raus.append("+%d MEDKIT" % int(d["medkits"]))
    if d.get("granaten"):
        raus.append("+%d SCHUSS JE WURFWAFFE" % int(d["granaten"]))
    if d.get("schild"):
        raus.append("TRÄGT EIN GROSSES SCHILD VORN")
    return raus


def faehigkeiten_von(k) -> tuple:
    """((Art, Pause), ...) - was diese Figur auf C hat: die Faehigkeit
    ihrer Klasse, oder (JEDER HAT ALLES, seit 0.34.85) das gewaehlte
    Werkzeug aus K.WERKZEUGE."""
    d = daten(getattr(k, "klasse", ""))
    if d.get("faehigkeit"):
        return tuple(d["faehigkeit"])
    if getattr(k, "alle_werkzeuge", False):
        return (K.WERKZEUGE[getattr(k, "werkzeug", 0) % len(K.WERKZEUGE)],)
    return ()


def faehigkeit_gewaehlt(k):
    """Die gewaehlte Faehigkeit (Art, Pause) oder None. Seit 0.34.138
    waehlt X (WERKZEUG WECHSELN) auch zwischen den Faehigkeiten einer
    Klasse (gemeldet: "Faehigkeit wechseln funktioniert gar nicht" - C nahm
    immer die erste, die bereit war, und X wirkte nur ohne Klasse)."""
    liste = faehigkeiten_von(k)
    if not liste:
        return None
    if len(liste) == 1:
        return liste[0]
    return liste[getattr(k, "faehigkeit_wahl", 0) % len(liste)]


def faehigkeit_wechseln(k) -> str:
    """X: die naechste Faehigkeit der Klasse, oder - ohne Klasse, JEDER HAT
    ALLES - das naechste Werkzeug. Gibt den Namen zurueck oder ""."""
    d = daten(getattr(k, "klasse", ""))
    if d.get("faehigkeit"):
        liste = tuple(d["faehigkeit"])
        if len(liste) < 2:
            return ""
        k.faehigkeit_wahl = (getattr(k, "faehigkeit_wahl", 0) + 1) % len(liste)
    elif getattr(k, "alle_werkzeuge", False):
        k.werkzeug = (getattr(k, "werkzeug", 0) + 1) % len(K.WERKZEUGE)
    else:
        return ""
    wahl = faehigkeit_gewaehlt(k)
    return FAEHIGKEIT_NAMEN.get(wahl[0], wahl[0].upper()) if wahl else ""


def faehigkeit_bereit(k):
    """Die gewaehlte Faehigkeit, wenn ihre Pause um ist - (Art, Pause) oder None.
    Bots waehlen nicht: sie nehmen die erste, die bereit ist (wie bisher)."""
    rest = getattr(k, "faehigkeit_rest", {})
    if getattr(k, "ist_bot", False):
        for art, pause in faehigkeiten_von(k):
            if rest.get(art, 0.0) <= 0.0:
                return art, pause
        return None
    wahl = faehigkeit_gewaehlt(k)
    if wahl is None:
        return None
    rest = getattr(k, "faehigkeit_rest", {})
    return wahl if rest.get(wahl[0], 0.0) <= 0.0 else None


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
            ding.besitzer = k          # die Drohne kreist um ihn (seit 0.34.96)
            gefecht.welt.dazu(ding)
    k.faehigkeit_rest[art] = pause
    gefecht.welt.klang("aufheben", 0.6, k.pos, k.ebene)
    return FAEHIGKEIT_NAMEN.get(art, art.upper())
