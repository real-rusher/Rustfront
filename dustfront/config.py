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

# ══════════════════════════════════════════════════ AUSSENHAUT
#
# Texturen und Klaenge. Alles, was das Spiel zeigt und hoert, hat einen
# Namen. Zu jedem Namen sucht das Spiel zuerst eine Datei und zeichnet oder
# rechnet nur dann selbst, wenn keine da ist:
#
#     assets/<name>.png           Bild
#     assets/sfx/<name>.wav       Klang
#
# Eine hingelegte Datei ersetzt den Platzhalter, ohne dass eine Zeile Code
# geaendert wird. Welche Namen es gibt, steht in BILD_MASS und KLANG_NAMEN
# weiter unten; `python -m dustfront --vorlagen` schreibt von jedem Bild
# eine masshaltige Vorlage zum Uebermalen heraus.

ASSETS = dict(
    ordner="assets",              # Name des Ordners neben dem Paket
    sfx="sfx",                    # Unterordner fuer die Klaenge
    bild_endungen=(".png", ".webp", ".bmp"),
    ton_endungen=(".wav", ".ogg"),
    fassungen=8,                  # name_1 bis name_8 als Abwechslung
    platzhalter_fassungen=3,      # so viele Kopien je erzeugtem Klang
    vorlagen="assets_vorlage",    # dorthin schreibt --vorlagen
)

# Fehlt ein Bild ganz, also Datei und Platzhalter, zeigt das Spiel diese
# Flaeche. Grell und absichtlich haesslich, damit es niemand uebersieht.
C_FEHLT = (255, 0, 220, 180)

# Flaechen, die nicht auf einer Kachel sitzen, sondern sich nach der Groesse
# dessen richten, was sie wirft: der Schatten nach dem Koerper, der Blutfleck
# nach dem Wesen, der Brandfleck nach dem Wirkungskreis. Gemalt sind sie in
# einem Basismass (siehe BILD_MASS), und der Renderer rechnet sie von dort
# auf die gebrauchte Groesse. Hier steht, fuer welchen Wert das Basismass
# gilt.
DEKAL = dict(
    schatten_radius=20.0,     # Koerperradius, fuer den das Basisbild gilt
    schatten_breite=2.3,      # Faktor Radius -> Breite des Ovals
    schatten_hoehe=1.15,      # Faktor Radius -> Hoehe des Ovals
    schatten_luft=0.34,       # so klein wird er, wenn das Wesen hoch fliegt
    blut_radius=9.0,          # Wesensradius, fuer den das Basisbild gilt
    brand_radius=78.0,        # Wirkungskreis, fuer den das Basisbild gilt
    wand_versatz=7,           # so weit faellt der Schlagschatten einer Wand
)

# Sollmass jedes Bildes in Pixeln.
#
# Eine Datei darf in jeder Aufloesung gemalt sein: passt sie nicht auf das
# Mass, wird sie beim Laden darauf gebracht, und zwar hart Pixel fuer Pixel,
# ohne Weichzeichnen. Wer also in doppelter oder vierfacher Groesse malt,
# bekommt sauberes Herunterrechnen geschenkt. Wer ein anderes Mass will,
# aendert die Zahl hier, nicht den Code.
#
# Kacheln muessen TILE gross sein, sonst reissen Luecken in die Karte.
# Figuren sitzen mittig auf einer quadratischen Flaeche und schauen nach
# rechts, damit das Drehen stimmt.
BILD_MASS = {
    # Kacheln
    "leer":             (TILE, TILE),
    "boden":            (TILE, TILE),
    "boden_2":          (TILE, TILE),
    "boden_3":          (TILE, TILE),
    "boden_4":          (TILE, TILE),
    "gitter":           (TILE, TILE),
    "wand":             (TILE, TILE),
    "kiste":            (TILE, TILE),
    "treppe_hoch":      (TILE, TILE),
    "treppe_runter":    (TILE, TILE),
    "luke":             (TILE, TILE),
    # Figuren, quadratisch und nach rechts schauend. Die Figur mit Waffe
    # braucht mehr Flaeche als die Figur allein, sonst ragt der Lauf der
    # Scharfschuetzenwaffe hinaus.
    "spieler":          (28, 28),
    "spieler_repetierer": (56, 56),
    "spieler_sturm":      (56, 56),
    "spieler_schrot":     (56, 56),
    "spieler_scharf":     (56, 56),
    "spieler_granate":    (56, 56),
    "spieler_brecheisen": (56, 56),
    "gegner_laeufer":   (28, 28),
    "gegner_brecher":   (36, 36),
    # Kleinkram
    "geschoss":         (8, 4),
    "muendung":         (20, 20),
    "medkit":           (16, 14),
    "munikiste":        (16, 14),
    "granate":          (10, 10),
    "huelse":           (4, 3),
    # Waffensymbole fuer Hotbar und Inventar, Seitenansicht nach rechts
    "waffe_repetierer": (26, 11),
    "waffe_sturm":      (26, 11),
    "waffe_schrot":     (26, 11),
    "waffe_scharf":     (26, 11),
    "waffe_granate":    (26, 11),
    "waffe_brecheisen": (26, 11),
    # Dekale und Schatten. Das Mass ist hier ein Basismass: das Spiel rechnet
    # die Flaeche auf die Groesse um, die es gerade braucht. Wer sie ersetzt,
    # malt also nicht fuer eine feste Groesse, sondern eine Form.
    "schatten":         (48, 24),
    "blut":             (26, 26),
    "brandfleck":       (156, 156),
    "wandschatten":     (TILE + DEKAL["wand_versatz"], TILE + DEKAL["wand_versatz"]),
    "vignette":         (GAME_W, GAME_H),
}

# Klaenge liegen in assets/sfx. Gesucht wird erst unter dem vollen Namen,
# dann unter dem Teil vor dem Unterstrich: fuer "schuss_repetierer" also
# schuss_repetierer.wav, danach schuss.wav.
KLANG_NAMEN = (
    "schuss",               # Rueckfall fuer jede Schusswaffe ohne eigene Datei
    "schuss_repetierer",
    "schuss_sturm",
    "schuss_schrot",
    "schuss_scharf",
    "granate",
    "nahkampf",
    "wurf",
    "medkit",
    "aufheben",
    "menue",
    "menue_ok",
)

AUDIO = dict(
    gesamt=0.75,              # Gesamtlautstaerke
    schuss=0.85,              # Lautstaerke der Schuesse
)

# Mass der Uebersichtstafel, die `--vorlagen` neben die Einzelbilder legt.
VORLAGEN = dict(
    spalten=5,
    zelle=(104, 54),          # Breite mal Hoehe einer Zelle
    rand=8,
    kopf=22,                  # Platz fuer die Ueberschrift
    luft=16,                  # Platz unter dem Bild fuer Name und Mass
    lupe=2,                   # so oft wird die fertige Tafel hochskaliert
    karo=(26, 20, 15),        # Schachbrett hinter durchsichtigen Stellen
    karo_2=(34, 27, 20),
    karo_feld=4,
)

# ══════════════════════════════════════════════════ NETZ
#
# LAN-Mehrspieler. Ein Rechner rechnet (der Gastgeber), die anderen
# schicken ihre Eingaben und bekommen den Zustand zurueck.

NETZ = dict(
    port=50505,               # Standardport, frei waehlbar beim Start
    hoechstens=8,             # so viele Gaeste nimmt ein Gastgeber an
    warteschlange=8,
    puffer=65536,             # so viel wird je Versuch von der Leitung gelesen
    hoechstzeile=262144,      # laengere Nachricht = Leitung gilt als kaputt
    wartezeit=5.0,            # Sekunden, die ein Verbindungsversuch dauern darf
    takt=1.0 / 60.0,          # so oft schickt der Gastgeber den Weltzustand
    eingabe_takt=1.0 / 60.0,  # so oft schickt ein Gast seine Eingaben
    probe_ziel="10.255.255.255",   # nur um die eigene Adresse zu erfahren
    namenslaenge=10,
    stumm_nach=8.0,           # ohne Lebenszeichen gilt ein Gast als weg
)

# Die drei Spielarten im Mehrspieler.
#
#   pvp     nur Spieler gegeneinander, endet nach Zeit oder Abschuessen
#   pve     alle zusammen gegen Wellen, endet wenn alle am Boden liegen
#   pvpve   Wellen und Spieler gegeneinander, endet wie pvp
#
# gegner  = es kommen Wellen
# beute   = Spieler koennen sich gegenseitig treffen
# revive  = wer faellt, liegt am Boden und kann aufgeholfen bekommen
MODI = {
    "pvp":   dict(name="PVP",   gegner=False, beute=True,  revive=False,
                  hinweis="Jeder gegen jeden."),
    "pve":   dict(name="PVE",   gegner=True,  beute=False, revive=True,
                  hinweis="Alle zusammen gegen die Wellen."),
    "pvpve": dict(name="PVPVE", gegner=True,  beute=True,  revive=False,
                  hinweis="Wellen, und dabei jeder gegen jeden."),
}
MODUS_VORGABE = "pvp"

# Wie eine Runde endet. Bei pvp und pvpve waehlt der Gastgeber; bei pve
# endet sie, wenn alle am Boden liegen.
ENDE_ARTEN = ("zeit", "abschuesse")

GEFECHT = dict(
    rundenzeit=300.0,         # Sekunden je Runde, wenn nach Zeit gespielt wird
    abschuesse_ziel=20,       # Abschuesse bis zum Sieg, wenn danach gespielt wird
    wieder_nach=3.0,          # Sekunden bis zum Wiedereinstieg nach dem Tod
    punkt_abschuss=1,
    punkt_selbst=-1,          # wer sich selbst erledigt, zahlt drauf
    schutz=2.0,               # Sekunden unverwundbar nach dem Einstieg
    abstand=160.0,            # so weit weg von anderen wird eingestiegen
    medkit_takt=12.0,         # Sekunden zwischen zwei Medkits
    medkit_hoechstens=4,      # so viele liegen gleichzeitig herum
    tafel_oben=74,            # wo der Punktestand anfaengt, unter den Ebenen
)

# Am Boden liegen und wieder aufgeholfen werden. Nur in pve.
#
# Der Sinn: ein einzelner Fehler soll einen nicht aus der Runde nehmen,
# aber er soll die anderen etwas kosten - naemlich die Zeit, in der sie
# nicht schiessen, sondern helfen.
REVIVE = dict(
    boden_leben=0.0,          # damit faengt man am Boden an
    boden_zeit=45.0,          # so lange haelt man durch, dann ist es vorbei
    dauer=3.0,                # so lange muss ein Helfer danebenstehen
    reichweite=28.0,          # so nah muss er sein
    danach_leben=40.0,        # mit so viel Leben steht man wieder auf
    schutz=2.0,               # Sekunden unverwundbar nach dem Aufstehen
    kriechen=0.35,            # so viel Tempo hat man am Boden noch
)

# Wellen im Mehrspieler. Anders als im Einzelspieler waechst die Welle mit
# der Zahl der Spieler - sonst ist dieselbe Welle zu viert ein Spaziergang.
WELLEN_MP = dict(
    pause=6.0,                # Sekunden zwischen zwei Wellen
    grund=4,                  # so viele Gegner in Welle 1 bei einem Spieler
    je_welle=0.35,            # plus 35 Prozent je weiterer Welle
    je_spieler=0.6,           # plus 60 Prozent je weiterem Spieler
    hoechstens=40,            # mehr werden nie gleichzeitig losgeschickt
    brecher_ab=3,             # ab dieser Welle kommen auch Brecher
    brecher_anteil=0.22,
)

# Gegner-KI im Mehrspieler: mehrere Ziele statt einem.
GEGNER_MP = dict(
    ziel_haltezeit=2.5,       # so lange bleibt ein Gegner bei seinem Ziel
    gedraenge=0.55,           # Aufschlag je Gegner, der schon an dem Ziel haengt
    ebenen_strafe=420.0,      # so viel "weiter weg" zaehlt eine fremde Ebene
    boden_strafe=900.0,       # wer am Boden liegt, zieht kaum noch Gegner an
)

# Begrenzte Munition. Der Gastgeber schaltet sie beim Aufmachen an.
MUNITION = dict(
    vorrat={"repetierer": 70, "sturm": 150, "schrot": 32, "scharf": 20,
            "granate": 4, "brecheisen": 0},
    kiste_takt=18.0,          # Sekunden zwischen zwei Munitionskisten
    kiste_hoechstens=3,
    kiste_gibt=0.45,          # so viel vom vollen Vorrat gibt eine Kiste
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
    massstab_schwelle=0.02,   # ab so viel Abweichung wird ein Wesen im Sturz
                              # ueberhaupt umgerechnet
)

STURZ = dict(
    schwerkraft=980.0,    # Pixel je Sekunde im Quadrat, bestimmt die Falldauer
    luftsteuerung=0.55,   # so viel Bewegung hat man waehrend des Sturzes
    schaden_je_100=9.0,   # Schaden pro 100 Pixel Fallhoehe
    min_schaden=3.0,
    abrutschen=140.0,     # Pixel je Sekunde, mit denen man im Flug an einem
                          # Hindernis unter sich zur Seite rutscht
)

# Zielhilfe: eine Linie von der Waffe zum Mauszeiger, mit Z auch darueber
# hinaus bis zur naechsten Wand.
TRACER = dict(
    weite=900.0,
    farbe=(214, 64, 48),
    punkt=(255, 110, 86),  # der Fleck da, wo die Linie endet
    staerke=150,           # Deckkraft der Linie
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

# Wie eine Waffe in der Hand der Figur aussieht, von oben gesehen.
#
# In der Draufsicht sieht man von einer Waffe fast nur ihren Umriss, also
# zaehlen Laenge und Dicke. Genau das soll reichen, um auf einen Blick zu
# erkennen, was man gerade traegt - ohne in die Hotbar zu schauen.
#
#   lauf     wie weit sie ueber die Hand hinausragt, in Pixeln
#   dicke    Dicke des Laufs
#   schaft   wie weit sie hinter der Hand liegt
#   s_dicke  Dicke des Schafts
#   holz     True = brauner Schaft, False = Stahl
#   aufbau   ein Merkmal obendrauf, siehe art.py:
#            kammer | magazin | doppel | fernrohr | kugel | haken
WAFFEN_HAND = {
    "repetierer": dict(lauf=17, dicke=3, schaft=9, s_dicke=4, holz=True,
                       aufbau="kammer"),
    "sturm":      dict(lauf=14, dicke=4, schaft=8, s_dicke=5, holz=False,
                       aufbau="magazin"),
    "schrot":     dict(lauf=14, dicke=5, schaft=9, s_dicke=6, holz=True,
                       aufbau="doppel"),
    "scharf":     dict(lauf=22, dicke=3, schaft=9, s_dicke=4, holz=True,
                       aufbau="fernrohr"),
    "granate":    dict(lauf=0,  dicke=0, schaft=0, s_dicke=0, holz=False,
                       aufbau="kugel"),
    "brecheisen": dict(lauf=15, dicke=2, schaft=5, s_dicke=2, holz=False,
                       aufbau="haken"),
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
