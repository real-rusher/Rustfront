"""
DUSTFRONT - Konfiguration und Inhalte
=====================================

Hier stehen alle Zahlen und Tabellen. Im restlichen Code steht keine einzige
frei schwebende Zahl, die man zum Ausbalancieren suchen muesste.

Aufgeteilt in drei Bereiche:

    TECHNIK     Aufloesung, Zeitschritt, Fenster. Aendert man selten.
    GEFUEHL     Beschleunigung, Rueckstoss, Kameraruckeln. Daran schraubt man.
    INHALTE     Kacheln, Waffen, Gegner. Das waechst spaeter.

Neue Waffen, Gegner oder Kacheln kommen als Eintrag in die passende Tabelle,
nicht als neue Klasse.
"""

from __future__ import annotations

# ══════════════════════════════════════════════════ TECHNIK

GAME_W, GAME_H = 640, 360        # Aufloesung, in der gerechnet und gezeichnet wird
TILE = 32                        # Kantenlaenge einer Kachel in Pixeln
START_FENSTER = (1280, 720)

FIXED_DT = 1.0 / 120.0           # fester Simulationsschritt
MAX_SCHRITTE = 5                 # Notbremse, falls ein Bild sehr lange braucht
ZIEL_FPS = 0                     # 0 = unbegrenzt, Begrenzung kommt aus den Optionen

# Zeichenreihenfolge innerhalb einer Ebene
SCHICHT_BODEN, SCHICHT_DEKAL, SCHICHT_OBJEKT, SCHICHT_FLUG = 0, 1, 2, 3

# ══════════════════════════════════════════════════ FARBEN

# Uebernommen aus den Mockups, damit Menue und Spiel zusammenpassen.
C_VOID = (9, 6, 5)
C_BODEN = (46, 36, 27)
C_BODEN_2 = (39, 30, 22)
C_FUGE = (30, 22, 16)
C_WAND = (64, 52, 39)
C_WAND_OBEN = (92, 76, 56)
C_WAND_KANTE = (28, 21, 15)
C_CREAM = (238, 226, 203)
C_AMBER = (232, 163, 61)
C_ORANGE = (226, 98, 47)
C_RUST = (150, 60, 30)
C_TEAL = (63, 210, 192)
C_TEAL_DK = (28, 96, 90)
C_MUTED = (131, 108, 82)
C_MUTED_DK = (84, 66, 49)
C_RED = (203, 62, 42)
C_HULL = (170, 152, 112)
C_HULL_DK = (108, 94, 66)
C_HULL_SH = (58, 47, 32)
C_BLUT = (96, 30, 22)

# ══════════════════════════════════════════════════ GEFUEHL

SPIELER = dict(
    radius=9.0,
    tempo=132.0,              # Pixel pro Sekunde bei vollem Lauf
    beschleunigung=1250.0,    # wie schnell das Tempo erreicht wird
    bremsung=1500.0,          # wie schnell er steht, wenn man loslaesst
    sprint=1.55,              # Faktor auf das Tempo
    leben=100.0,
    unverwundbar=0.6,         # Sekunden nach einem Treffer
    stiefel_abstand=26.0,     # Pixel zwischen zwei Staubwolken
)

KAMERA = dict(
    nachlauf=11.0,            # je hoeher, desto straffer klebt sie am Spieler
    maus_zug=0.26,            # wie weit sie in Blickrichtung vorlaeuft
    maus_max=54.0,
    ruckeln_abbau=2.6,        # wie schnell das Zittern verklingt
    ruckeln_max=9.0,
)

TREFFER = dict(
    blitz=0.09,               # Sekunden, die ein Getroffener hell aufleuchtet
    rueckstoss=118.0,         # Schub, den ein Treffer dem Ziel gibt
    zeitlupe=0.045,           # kurze Verlangsamung beim Toeten
)

# ══════════════════════════════════════════════════ TON

# Klaenge liegen in assets/sfx. Fehlt eine Datei, erzeugt audio.py einen
# Platzhalter. Namen: schuss_repetierer, schuss_schrot, sonst schuss.
AUDIO = dict(
    gesamt=0.75,              # Gesamtlautstaerke
    schuss=0.85,              # Lautstaerke der Schuesse
)

# ══════════════════════════════════════════════════ HOEHE

# Hoehe jeder Ebene in Welt-Pixeln. Der Abstand zwischen zwei Ebenen
# entscheidet ueber drei Dinge: wie klein die untere gezeichnet wird, wie
# lange ein Sturz dauert und wie weh er tut.
#
#   0 -> 1   Boden hinauf in die erste Mech-Etage, sehr weit
#   1 -> 2   eine Etage im selben Rumpf, deutlich enger
EBENEN_HOEHE = [0, 118, 182, 238, 288]

PERSPEKTIVE = dict(
    brennweite=430.0,     # je kleiner, desto staerker schrumpft die Tiefe
    dunkel=128,           # Helligkeit der Ebene darunter (255 = unveraendert)
    dunst=(20, 17, 26),   # kalter Schleier, der mit der Tiefe zunimmt
    dunst_staerke=0.42,
    tiefe_sichtbar=8,     # so viele Ebenen nach unten werden gezeichnet
    ausblenden=150.0,     # so weit ueber der Ansicht verschwindet eine Ebene
)

STURZ = dict(
    schwerkraft=980.0,    # Pixel je Sekunde im Quadrat, bestimmt die Falldauer
    luftsteuerung=0.55,   # so viel Bewegung hat man waehrend des Sturzes
    schaden_je_100=9.0,   # Schaden pro 100 Pixel Fallhoehe
    min_schaden=3.0,
)

# Zielhilfe: eine Linie von der Waffe zum Mauszeiger, mit Z auch darueber
# hinaus bis zur naechsten Wand.
TRACER = dict(
    weite=900.0,
    farbe=(214, 64, 48),
    kern=(255, 196, 176),
    staerke=150,          # Deckkraft der Linie
)

# ══════════════════════════════════════════════════ INHALTE: Kacheln

# fest      blockiert Bewegung
# sicht     blockiert Schuesse und Sicht
# treppe    Zielebene relativ zur aktuellen, sonst None
LEER, BODEN, GITTER, WAND, KISTE, TREPPE_HOCH, TREPPE_RUNTER, LUKE = range(8)

KACHELN = {
    # Ein Loch: man kann darueber hinwegschiessen und hineinfallen, aber es
    # ist kein Boden. Wesen, die nicht fallen sollen, behandeln es als fest.
    LEER:          dict(name="leer",     fest=False, sicht=False, bild="leer",
                        loch=True),
    BODEN:         dict(name="boden",    fest=False, sicht=False, bild="boden"),
    GITTER:        dict(name="gitter",   fest=False, sicht=False, bild="gitter"),
    WAND:          dict(name="wand",     fest=True,  sicht=True,  bild="wand"),
    KISTE:         dict(name="kiste",    fest=True,  sicht=False, bild="kiste"),
    TREPPE_HOCH:   dict(name="treppe",   fest=False, sicht=False, bild="treppe_hoch",
                        treppe=+1),
    TREPPE_RUNTER: dict(name="treppe",   fest=False, sicht=False, bild="treppe_runter",
                        treppe=-1),
    LUKE:          dict(name="luke",     fest=False, sicht=False, bild="luke",
                        treppe=-1),
}

# ══════════════════════════════════════════════════ INHALTE: Waffen

# art: schuss | wurf | nahkampf. Alles Weitere haengt an dieser einen Zeile,
# eine neue Waffe ist ein Eintrag, keine neue Klasse.
WAFFEN = {
    "repetierer": dict(
        art="schuss",
        name="REPETIERER",
        schaden=26.0,
        takt=0.16,            # Sekunden zwischen zwei Schuessen
        magazin=14,
        nachladen=1.35,
        streuung=1.6,         # Grad
        streuung_lauf=3.4,    # Aufschlag, wenn man sich bewegt
        geschosse=1,
        tempo=690.0,
        reichweite=430.0,
        rueckstoss=38.0,      # Schub auf den Schuetzen
        kamera=1.6,           # Ruckeln
        huelsen=1,
    ),
    "schrot": dict(
        art="schuss",
        name="SCHROT",
        schaden=13.0,
        takt=0.62,
        magazin=6,
        nachladen=2.1,
        streuung=7.5,
        streuung_lauf=3.0,
        geschosse=7,
        tempo=560.0,
        reichweite=210.0,
        rueckstoss=150.0,
        kamera=4.2,
        huelsen=1,
    ),
    "sturm": dict(
        art="schuss",
        name="STURMGEWEHR",
        schaden=16.0,
        takt=0.085,           # rund 700 Schuss in der Minute
        magazin=30,
        nachladen=2.05,
        streuung=2.2,
        streuung_lauf=3.6,
        streuung_dauerfeuer=4.5,   # Aufschlag, wenn man den Abzug haelt
        geschosse=1,
        tempo=760.0,
        reichweite=470.0,
        rueckstoss=22.0,
        kamera=1.0,
        huelsen=1,
    ),
    "scharf": dict(
        art="schuss",
        name="SCHARFSCHUETZE",
        schaden=98.0,
        takt=1.20,
        magazin=5,
        nachladen=2.7,
        # Aus der Hueffte streut sie wild. Rechte Maustaste halten zieht den
        # Streifen ueber fokus_dauer bis auf fokus_streuung zusammen.
        streuung=14.0,
        fokus_streuung=0.3,
        fokus_dauer=1.5,
        fokus_tempo=0.45,     # so langsam laeuft man im Fokus
        streuung_lauf=6.0,
        geschosse=1,
        tempo=1150.0,
        reichweite=900.0,
        rueckstoss=190.0,
        kamera=6.5,
        huelsen=1,
    ),
    "granate": dict(
        art="wurf",
        name="GRANATE",
        schaden=78.0,
        radius=78.0,          # Wirkungskreis
        takt=0.85,
        magazin=3,
        nachladen=3.2,
        wurf_min=60.0,        # naeher wirft man nicht
        wurf_max=260.0,        # weiter auch nicht
        reibung=1.15,         # wie schnell sie ausrollt
        flugzeit=1.05,        # danach zuendet sie, egal wo sie liegt
        kamera=8.0,
        rueckstoss=0.0,
        huelsen=0,
    ),
    "brecheisen": dict(
        art="nahkampf",
        name="BRECHEISEN",
        schaden=46.0,
        takt=0.40,
        reichweite=36.0,
        winkel=80.0,          # Oeffnung des Schlags in Grad
        schub=280.0,          # Rueckstoss auf das Ziel
        kamera=2.6,
        rueckstoss=0.0,
        magazin=0,            # braucht keine Munition
        nachladen=0.0,
        huelsen=0,
    ),
}

# Was der Spieler zu Beginn auf den Plaetzen 1 bis 6 traegt
HOTBAR = ["repetierer", "sturm", "schrot", "scharf", "granate", "brecheisen"]

MEDKIT = dict(
    name="MEDKIT",
    heilt=45.0,
    je_welle=2,           # so viele werden pro Welle abgeworfen
    hoechstens=3,         # so viele kann man tragen
    dauer=0.8,            # Sekunden, die das Anlegen braucht
)

# ══════════════════════════════════════════════════ INHALTE: Gegner

GEGNER = {
    "laeufer": dict(
        name="LAEUFER",
        leben=44.0,
        radius=9.0,
        tempo=74.0,
        beschleunigung=560.0,
        schaden=9.0,
        schlagtakt=0.85,
        reichweite=17.0,      # Nahkampf
        sicht=300.0,
        bild="gegner_laeufer",
        punkte=10,
    ),
    "brecher": dict(
        name="BRECHER",
        leben=140.0,
        radius=13.0,
        tempo=52.0,
        beschleunigung=380.0,
        schaden=22.0,
        schlagtakt=1.3,
        reichweite=22.0,
        sicht=340.0,
        bild="gegner_brecher",
        punkte=30,
    ),
}

# Wellen: (Anzahl, Typ) je Welle, danach wird hochskaliert
WELLEN = [
    [(4, "laeufer")],
    [(6, "laeufer")],
    [(7, "laeufer"), (1, "brecher")],
    [(9, "laeufer"), (2, "brecher")],
]
WELLE_PAUSE = 4.0             # Sekunden zwischen zwei Wellen
WELLE_WACHSTUM = 0.22         # plus 22 Prozent Gegner je Welle nach der Liste


# ══════════════════════════════════════════════════════════════════
# Version
# ══════════════════════════════════════════════════════════════════
#
# Die eine Quelle der Wahrheit sind VERSION und PHASE in
# `rustfront_menu.py`, so wie es im README steht. Hier wird die Zeile
# ausgelesen statt das Modul zu importieren: ein Import wuerde das ganze
# Hauptmenue starten, und das Spiel soll auch ohne Menue laufen.
#
# Faellt das Auslesen aus, steht hier eine Notnummer. Die ist absichtlich
# als solche erkennbar, damit niemand eine falsche Version fuer echt haelt.

def _version_lesen() -> tuple[str, str]:
    import re
    from pathlib import Path
    quelle = Path(__file__).resolve().parent.parent / "rustfront_menu.py"
    werte = {}
    try:
        text = quelle.read_text(encoding="utf-8")
        for schluessel in ("VERSION", "PHASE"):
            treffer = re.search(r'^%s\s*=\s*"([^"]+)"' % schluessel, text, re.M)
            if treffer:
                werte[schluessel] = treffer.group(1)
    except OSError:
        pass
    return werte.get("VERSION", "0.0.0"), werte.get("PHASE", "UNBEKANNT")


VERSION, PHASE = _version_lesen()
