"""
DUSTFRONT - Einstellungen und Tastenbelegung
============================================

Alles, was der Spieler einstellt, liegt in zwei JSON-Dateien im Benutzer-
ordner des Systems (siehe pfade.py), nicht im Spielordner. Damit ueberlebt
jede Einstellung ein Neuherunterladen des Spiels.

    einstellungen.json   Bild, Ton, Anzeige
    tasten.json          Tastenbelegung

Tasten werden als Namen gespeichert, nicht als Zahlen. In der Datei steht
also "w" und "left shift", nicht 119 und 1073742049. Das kann man von Hand
lesen und notfalls mit einem Texteditor reparieren.

Unbekannte Eintraege in den Dateien werden verworfen, fehlende durch die
Vorgabe ersetzt. Eine kaputte Datei kostet damit hoechstens die eine
Einstellung, die kaputt ist, nie den Start.
"""

from __future__ import annotations

import json

import pygame

from . import pfade

# ══════════════════════════════════════════════════ Vorgaben

VORGABE = {
    # Anzeige
    "fenstermodus": "fenster",     # fenster | randlos | vollbild
    "aufloesung": "1280x720",
    "bildrate": 0,                 # 0 = unbegrenzt, sonst Obergrenze
    "pixelraster": "gefuellt",     # gefuellt | ganzzahlig
    # Ton
    "ton_gesamt": 75,
    "ton_effekte": 85,
    "ton_musik": 60,
    # Grafik
    "vignette": True,             # noch ohne Wirkung, der Schalter steht bereit
    # Prozent der Staerke, 0 = das Bild steht vollkommen still. Die
    # Vorgabe ist absichtlich 100 und nicht weniger: schwach und selten
    # ist das Ruckeln schon in RUCKELN eingestellt, und zweimal
    # heruntergedreht bliebe von einer Explosion neben einem gar nichts
    # mehr uebrig. Der Regler ist der Griff des Spielers obendrauf.
    "bildschirm_ruckeln": 100,
    "partikel": "viel",            # wenig | normal | viel
    # Spiel
    "tracer": False,
    "tracer_weit": False,
    # Im Mehrspieler: ob die Etage ueber einem zu Beginn jeder Partie
    # gezeigt wird, wo sie ueber Spielflaeche liegt. Aus, weil sie dort
    # genau den Gang verdeckt, in dem geschossen wird; Q schaltet in der
    # Runde um. Plateaus ueber Fels bleiben immer sichtbar.
    "obere_ebenen": False,
}

# Welche Einstellungen zum **Spieler** gehoeren und nicht zum Geraet.
#
# Auf welcher Aufloesung jemand spielt, ist Sache des Rechners, vor dem er
# sitzt. Ob ihm vom Wackeln schlecht wird, ist es nicht - das gilt an
# jedem Rechner, an dem er sich anmeldet. Was hier steht, wandert darum
# spaeter mit dem Konto mit (siehe konto_werte / konto_uebernehmen); alles
# andere bleibt, wo es ist.
KONTO_WERTE = ("bildschirm_ruckeln", "vignette", "partikel",
               "tracer", "tracer_weit", "ton_gesamt", "ton_effekte",
               "ton_musik", "obere_ebenen")

AUFLOESUNGEN = ["960x540", "1280x720", "1600x900", "1920x1080", "2560x1440"]
FENSTERMODI = ["fenster", "randlos", "vollbild"]
PARTIKEL = ["wenig", "normal", "viel"]
RASTER = ["gefuellt", "ganzzahlig"]
BILDRATEN = [0, 60, 75, 90, 120, 144, 165, 240]

# Wie die Werte im Menue heissen sollen. Was hier fehlt, wird einfach
# grossgeschrieben angezeigt.
BESCHRIFTUNG = {
    "fenstermodus": {"fenster": "FENSTER", "randlos": "RANDLOS",
                     "vollbild": "VOLLBILD"},
    "pixelraster": {"gefuellt": "FUELLT DAS FENSTER", "ganzzahlig": "GANZE PIXEL"},
    "partikel": {"wenig": "WENIG", "normal": "NORMAL", "viel": "VIEL"},
    "bildrate": {0: "UNBEGRENZT"},
}

# ══════════════════════════════════════════════════ Tastenbelegung

# Reihenfolge ist zugleich die Reihenfolge im Menue.
TASTEN_VORGABE = [
    ("vor",         "VORWAERTS",        ["w", "up"]),
    ("zurueck",     "ZURUECK",          ["s", "down"]),
    ("links",       "LINKS",            ["a", "left"]),
    ("rechts",      "RECHTS",           ["d", "right"]),
    ("dash",        "DASH",             ["left shift", "right shift"]),
    # Am Boden heisst dieselbe Taste "rufen": wer liegt, kann nichts
    # benutzen, aber er kann auf sich aufmerksam machen.
    ("nutzen",      "BENUTZEN / RUFEN", ["e"]),
    ("ziehen",      "GEFALLENEN ZIEHEN", ["g"]),
    ("ebenen",      "OBERE EBENEN",     ["q"]),
    ("planen",      "RUNDEN EINSTELLEN", ["p"]),
    ("nachladen",   "NACHLADEN",        ["r"]),
    ("heilen",      "MEDKIT",           ["h"]),
    ("inventar",    "INVENTAR",         ["tab"]),
    ("waffe1",      "PLATZ 1",          ["1"]),
    ("waffe2",      "PLATZ 2",          ["2"]),
    ("waffe3",      "PLATZ 3",          ["3"]),
    ("waffe4",      "PLATZ 4",          ["4"]),
    ("waffe5",      "PLATZ 5",          ["5"]),
    ("waffe6",      "PLATZ 6",          ["6"]),
    ("waffe7",      "PLATZ 7",          ["7"]),
    ("waffe8",      "PLATZ 8",          ["8"]),
    ("waffe9",      "PLATZ 9",          ["9"]),
    ("feuermodus",  "FEUERART",         ["v"]),
    ("nahkampf",    "BRECHEISEN",       ["f"]),
    ("tracer",      "ZIELLINIE",        ["t"]),
    ("tracer_weit", "LINIE VERLAENGERN", ["z"]),
    ("pause",       "PAUSE",            ["escape"]),
    ("vollbild",    "VOLLBILD",         ["f11"]),
    ("debug",       "DEBUG-ANZEIGE",    ["f3"]),
]

# Diese Aktionen lassen sich nicht umlegen, sonst sperrt man sich aus.
FEST = {"pause"}


# Wie eine Taste im Menue heissen soll. SDL schreibt "left shift", das ist
# in einer Spalte von 100 Pixeln zu lang. Was hier fehlt, wird unveraendert
# und grossgeschrieben angezeigt.
KURZ = {
    "left shift": "L-SHIFT", "right shift": "R-SHIFT",
    "left ctrl": "L-STRG", "right ctrl": "R-STRG",
    "left alt": "L-ALT", "right alt": "ALT GR",
    "left meta": "L-META", "right meta": "R-META",
    "escape": "ESC", "return": "ENTER", "space": "LEER",
    "backspace": "RUECK", "tab": "TAB", "caps lock": "FESTST",
    "up": "HOCH", "down": "RUNTER", "left": "LINKS", "right": "RECHTS",
    "page up": "BILD HOCH", "page down": "BILD RUNTER",
    "insert": "EINFG", "delete": "ENTF", "home": "POS1", "end": "ENDE",
    "print screen": "DRUCK", "menu": "MENUE",
}


def taste_name(code: int) -> str:
    try:
        return pygame.key.name(code)
    except Exception:
        return "?"


def taste_kurz(name: str) -> str:
    """Anzeigename einer Taste, kurz genug fuer eine Menuespalte."""
    return KURZ.get(name.lower(), name).upper()


def belegung_text(namen) -> str:
    """Alle Tasten einer Aktion als eine Zeile, `-` wenn keine belegt ist."""
    kurz = [taste_kurz(n) for n in namen]
    return " / ".join(kurz) if kurz else "-"


def taste_code(name: str) -> int | None:
    try:
        c = pygame.key.key_code(name)
        return c if c > 0 else None
    except Exception:
        return None


# ══════════════════════════════════════════════════ Ablage

class Einstellungen:
    """Liest und schreibt beide Dateien. Faellt weich zurueck."""

    def __init__(self) -> None:
        self.werte = dict(VORGABE)
        self.tasten: dict[str, list[str]] = {
            name: list(vorgabe) for name, _, vorgabe in TASTEN_VORGABE
        }
        self.gelesen_von: str = "Vorgabe"
        self.laden()

    # ---- Zugriff -----------------------------------------------------
    def __getitem__(self, schluessel: str):
        return self.werte.get(schluessel, VORGABE.get(schluessel))

    def __setitem__(self, schluessel: str, wert) -> None:
        self.werte[schluessel] = wert

    def ruckel_anteil(self) -> float:
        """Wie stark das Bild wackeln darf, 0.0 bis 1.0.

        Die Einstellung gab es schon, sie hing nur an nichts: der Regler
        stand im Menue und liess sich ziehen, und die Kamera fragte ihn
        nie. Jetzt liest sie ihn bei jedem Bild.
        """
        try:
            wert = float(self["bildschirm_ruckeln"])
        except (TypeError, ValueError):
            wert = 100.0
        return max(0.0, min(1.0, wert / 100.0))

    # ---- Konto -------------------------------------------------------
    # Vorbereitung fuer die Anmeldung: was zum Spieler gehoert, soll auf
    # jedem Geraet gelten, an dem er sich anmeldet. Beide Richtungen sind
    # bewusst reine Woerterbucharbeit und kennen weder Netz noch Datenbank
    # - das haengt sich spaeter aussen an.

    def konto_werte(self) -> dict:
        """Die Einstellungen, die zum Spieler gehoeren, zum Hochladen."""
        return {k: self.werte.get(k, VORGABE[k]) for k in KONTO_WERTE}

    def konto_uebernehmen(self, werte) -> int:
        """Einstellungen aus einem Konto uebernehmen. Gibt die Anzahl zurueck.

        Geprueft wie beim Lesen der Datei: was nicht bekannt ist oder den
        falschen Typ hat, wird verworfen. Eine kaputte Antwort vom Server
        darf hoechstens die eine Einstellung kosten, die kaputt ist.
        """
        if not isinstance(werte, dict):
            return 0
        genommen = 0
        for k, v in werte.items():
            if k in KONTO_WERTE and isinstance(v, type(VORGABE[k])):
                self.werte[k] = v
                genommen += 1
        if genommen:
            self.speichern()
        return genommen

    def codes(self, aktion: str) -> list[int]:
        """Tastencodes einer Aktion, fuer den Vergleich im Spiel."""
        raus = []
        for name in self.tasten.get(aktion, ()):
            c = taste_code(name)
            if c is not None:
                raus.append(c)
        return raus

    def tastentabelle(self) -> dict[str, list[int]]:
        return {a: self.codes(a) for a in self.tasten}

    def belegen(self, aktion: str, code: int) -> str | None:
        """Legt eine Aktion auf eine Taste. Gibt die verdraengte Aktion zurueck.

        Eine Taste gehoert immer nur einer Aktion. War sie schon vergeben,
        wird sie dort entfernt, damit nichts doppelt belegt ist.
        """
        if aktion in FEST:
            return None
        name = taste_name(code)
        verdraengt = None
        for andere, liste in self.tasten.items():
            if andere == aktion or andere in FEST:
                continue
            if name in liste:
                liste.remove(name)
                verdraengt = andere
        self.tasten[aktion] = [name]
        self.speichern()
        return verdraengt

    def zuruecksetzen_tasten(self) -> None:
        self.tasten = {name: list(v) for name, _, v in TASTEN_VORGABE}
        self.speichern()

    def zuruecksetzen_werte(self) -> None:
        self.werte = dict(VORGABE)
        self.speichern()

    # ---- Datei -------------------------------------------------------
    def laden(self) -> None:
        d = pfade.datei("einstellungen.json")
        if d is not None and d.is_file():
            try:
                roh = json.loads(d.read_text(encoding="utf-8"))
                for k, v in roh.items():
                    # Nur bekannte Schluessel mit passendem Typ uebernehmen
                    if k in VORGABE and isinstance(v, type(VORGABE[k])):
                        self.werte[k] = v
                self.gelesen_von = str(d)
            except (OSError, ValueError):
                pass
        t = pfade.datei("tasten.json")
        if t is not None and t.is_file():
            try:
                roh = json.loads(t.read_text(encoding="utf-8"))
                # Der Sprint ist seit 0.27 der Dash. Wer ihn umgelegt
                # hatte, soll seine Taste behalten und nicht still auf
                # Shift zurueckfallen.
                if "sprint" in roh and "dash" not in roh:
                    roh["dash"] = roh.pop("sprint")
                bekannt = {name for name, _, _ in TASTEN_VORGABE}
                for k, v in roh.items():
                    if k in bekannt and isinstance(v, list):
                        namen = [str(x) for x in v if taste_code(str(x)) is not None]
                        if namen:
                            self.tasten[k] = namen
            except (OSError, ValueError):
                pass

    def speichern(self) -> bool:
        ok = True
        d = pfade.datei("einstellungen.json")
        if d is not None:
            try:
                d.write_text(json.dumps(self.werte, indent=2, ensure_ascii=False),
                             encoding="utf-8")
            except OSError:
                ok = False
        t = pfade.datei("tasten.json")
        if t is not None:
            try:
                t.write_text(json.dumps(self.tasten, indent=2, ensure_ascii=False),
                             encoding="utf-8")
            except OSError:
                ok = False
        return ok

    def aufloesung_paar(self) -> tuple[int, int]:
        try:
            b, h = str(self["aufloesung"]).lower().split("x")
            return max(320, int(b)), max(180, int(h))
        except (ValueError, AttributeError):
            return 1280, 720
