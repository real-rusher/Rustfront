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

# Der Rumpf. Kuehler und grauer als der Boden: Wasteland ist Staub und
# Rost, ein Deck ist Stahl. Der Unterschied muss auf einen Blick lesbar
# sein, auch wenn beide Kacheln nebeneinander liegen - sonst weiss man
# beim Absteigen nicht, wann man die Maschine verlassen hat.
C_DECK = (58, 55, 49)
C_DECK_2 = (50, 47, 42)
C_DECK_FUGE = (32, 30, 26)
C_DECK_HELL = (86, 81, 71)
C_RUMPF = (78, 72, 62)
C_RUMPF_OBEN = (116, 108, 93)
C_RUMPF_KANTE = (26, 24, 20)
C_STAHL = (96, 90, 78)
C_STAHL_HELL = (152, 143, 124)
C_STAHL_DUNKEL = (44, 41, 35)
C_GLUT = (226, 122, 48)       # was in einem Reaktor gluht
C_WARN = (204, 150, 52)       # Warnmarkierung, matter als C_AMBER

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
# Grundmass der Beinglieder. Steht hier oben, weil BILD_MASS es braucht;
# die vollstaendige Beintabelle K.BEIN weiter unten uebernimmt es.
BEIN_GRUNDMASS = dict(ober=78.0, unter=90.0, dicke_ober=13, dicke_unter=10,
                      fuss=18, huefte=17)

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
    # Rumpfkacheln. Gleiche Groesse wie jede andere Kachel: ein Deck ist
    # eine Karte wie jede andere, es sieht nur anders aus.
    "deck":             (TILE, TILE),
    "deck_2":           (TILE, TILE),
    "deck_3":           (TILE, TILE),
    "deck_4":           (TILE, TILE),
    "deck_gitter":      (TILE, TILE),
    "rumpfwand":        (TILE, TILE),
    "rampe":            (TILE, TILE),
    "modulschacht":     (TILE, TILE),
    "antrieb":          (TILE, TILE),
    "lager":            (TILE, TILE),
    "koje":             (TILE, TILE),
    "st_steuerstand":   (TILE, TILE),
    "st_geschuetz":     (TILE, TILE),
    "st_reaktor":       (TILE, TILE),
    "st_werkbank":      (TILE, TILE),
    "st_kartentisch":   (TILE, TILE),
    "st_funk":          (TILE, TILE),
    "st_werkstatt":     (TILE, TILE),
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
    "granate":          (10, 10),
    "huelse":           (4, 3),
    # Beinglieder. Sie liegen nach rechts und werden um ihre Mitte gedreht,
    # genau wie jede Figur. Das Mass ist ein **Grundmass**: eine Bauklasse
    # mit anderen Beinlaengen bekommt es hart umgerechnet, Pixel fuer
    # Pixel. Wer sie ersetzt, malt also eine Form, keine feste Groesse.
    "bein_ober":        (int(BEIN_GRUNDMASS["ober"]), BEIN_GRUNDMASS["dicke_ober"]),
    "bein_unter":       (int(BEIN_GRUNDMASS["unter"]), BEIN_GRUNDMASS["dicke_unter"]),
    "bein_fuss":        (BEIN_GRUNDMASS["fuss"], BEIN_GRUNDMASS["fuss"]),
    "bein_huefte":      (BEIN_GRUNDMASS["huefte"], BEIN_GRUNDMASS["huefte"]),
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
    # Der Wandler. "schritt" ist der wichtigste Klang im ganzen Spiel: er
    # ist das, was einen Gang zu einem Vorgang macht.
    "schritt",
    "servo",                # ein Bein schwingt durch
    "rumpf_stoss",          # die Maschine setzt hart auf
    "station_an",           # eine Station wird uebernommen
    "station_aus",
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


# ══════════════════════════════════════════════════ INHALTE: Rumpfkacheln
#
# Der Wandler ist eine begehbare Welt wie jede andere, nur besteht sein
# Boden aus Rumpfplatten statt aus Wasteland. Deshalb gibt es zu jeder
# Bodenkachel eine Rumpf-Entsprechung: gleiche Rolle, andere Textur.
#
#   BODEN   <->  DECK          worauf man steht
#   GITTER  <->  DECK_GITTER   Laufrost, man sieht hindurch
#   WAND    <->  RUMPFWAND     Aussenhaut und Schotten
#
# Welche der beiden Familien eine Karte benutzt, entscheidet die Kopfzeile
# `grund:` der Kartendatei. Die Zeichen im Text bleiben dieselben, ein
# Deck tippt sich also genau wie ein Stueck Wasteland.

(DECK, DECK_GITTER, RUMPFWAND, RAMPE,
 STEUERSTAND, GESCHUETZ, REAKTOR, WERKBANK, KARTENTISCH, FUNK,
 MODULSCHACHT, ANTRIEB, WERKSTATT, LAGER, KOJE) = range(8, 23)

# Stationen. `station` ist der Name, unter dem der Code sie findet; er ist
# zugleich die Marke, die der Kartenleser ablegt. Wer eine Station dazu
# erfinden will, braucht drei Zeilen: hier eine, in KACHELN eine, in
# KARTEN["marken"] eine.
STATIONEN = {
    "steuerstand": dict(name="STEUERSTAND", kachel=STEUERSTAND, deck="bruecke",
                        taste="steuern"),
    "geschuetz":   dict(name="GESCHUETZ",   kachel=GESCHUETZ,   deck="oberdeck",
                        taste="feuern"),
    "reaktor":     dict(name="MASCHINE",    kachel=REAKTOR,     deck="unterdeck",
                        taste="leistung"),
    "werkbank":    dict(name="WERKBANK",    kachel=WERKBANK,    deck="hauptdeck",
                        taste="bauen"),
    "kartentisch": dict(name="KARTENTISCH", kachel=KARTENTISCH, deck="bruecke",
                        taste="karte"),
    "funk":        dict(name="FUNK",        kachel=FUNK,        deck="bruecke",
                        taste="funk"),
    "werkstatt":   dict(name="WERKSTATT",   kachel=WERKSTATT,   deck="unterdeck",
                        taste="reparieren"),
}

KACHELN_RUMPF = {
    DECK:         dict(name="deck",     fest=False, sicht=False, bild="deck"),
    DECK_GITTER:  dict(name="rost",     fest=False, sicht=False, bild="deck_gitter"),
    RUMPFWAND:    dict(name="schott",   fest=True,  sicht=True,  bild="rumpfwand"),
    RAMPE:        dict(name="rampe",    fest=False, sicht=False, bild="rampe"),
    STEUERSTAND:  dict(name="steuerstand", fest=False, sicht=False,
                       bild="st_steuerstand", station="steuerstand"),
    GESCHUETZ:    dict(name="geschuetz", fest=False, sicht=False,
                       bild="st_geschuetz", station="geschuetz"),
    REAKTOR:      dict(name="reaktor",  fest=False, sicht=False,
                       bild="st_reaktor", station="reaktor"),
    WERKBANK:     dict(name="werkbank", fest=False, sicht=False,
                       bild="st_werkbank", station="werkbank"),
    KARTENTISCH:  dict(name="kartentisch", fest=False, sicht=False,
                       bild="st_kartentisch", station="kartentisch"),
    FUNK:         dict(name="funk",     fest=False, sicht=False,
                       bild="st_funk", station="funk"),
    MODULSCHACHT: dict(name="schacht",  fest=False, sicht=False,
                       bild="modulschacht"),
    ANTRIEB:      dict(name="antrieb",  fest=True,  sicht=True,  bild="antrieb"),
    WERKSTATT:    dict(name="werkstatt", fest=False, sicht=False,
                       bild="st_werkstatt", station="werkstatt"),
    LAGER:        dict(name="lager",    fest=True,  sicht=False, bild="lager"),
    KOJE:         dict(name="koje",     fest=False, sicht=False, bild="koje"),
}
KACHELN.update(KACHELN_RUMPF)

# ══════════════════════════════════════════════════ KARTEN AUS DATEIEN
#
# Eine Karte ist eine Textdatei in `karten/`. Kopf, dann je Ebene ein
# Block. Ein Zeichen ist eine Kachel, genau wie bisher - neu ist nur, dass
# der Text nicht mehr im Code steht.
#
#     name: Testhalle
#     grund: boden
#
#     --- ebene 0 ---
#     ##########
#     #...S....#
#     ##########
#
# Grossbuchstaben sind **Marken**: sie werden zu einer Kachel *und* legen
# ihre Position unter einem Namen ab. Damit muss kein Code mehr wissen, wo
# der Start, die Rampe oder der Steuerstand liegt - es steht in der Karte.

KARTEN = dict(
    ordner="karten",
    endung=".txt",
    trenner="---",            # Zeile, die einen Ebenenblock einleitet
    kommentar="#",            # nur im Kopf; in den Zeilen ist # eine Wand
    grund_voreinstellung="boden",
    start="probehalle",       # welche Karte eine Runde beginnt
    wandler="wandler/reaver", # welchen Rumpf der Probelauf zeigt
    boden="wasteland",        # worauf er laeuft
)

# Zeichen -> Kachel, getrennt nach Untergrund. Beides hat dieselben Rollen,
# damit ein Deck sich wie ein Stueck Boden tippt.
ZEICHEN_BODEN = {
    " ": LEER, ".": BODEN, ",": GITTER, "#": WAND, "X": KISTE,
    "<": TREPPE_RUNTER, ">": TREPPE_HOCH, "o": LUKE,
}
ZEICHEN_DECK = {
    " ": LEER, ".": DECK, ",": DECK_GITTER, "#": RUMPFWAND, "X": KISTE,
    "<": TREPPE_RUNTER, ">": TREPPE_HOCH, "o": LUKE,
}

# Marke -> (Name, Kachel oder None fuer "nimm den Untergrund").
# Ziffern 1 bis 9 kommen unten dazu, als punkt1 bis punkt9.
MARKEN = {
    "S": ("start",       None),
    "R": ("rampe",       RAMPE),
    "T": ("steuerstand", STEUERSTAND),
    "G": ("geschuetz",   GESCHUETZ),
    "E": ("reaktor",     REAKTOR),
    "W": ("werkbank",    WERKBANK),
    "K": ("kartentisch", KARTENTISCH),
    "F": ("funk",        FUNK),
    "M": ("modulschacht", MODULSCHACHT),
    "A": ("antrieb",     ANTRIEB),
    "Y": ("werkstatt",   WERKSTATT),
    "L": ("lager",       LAGER),
    "B": ("koje",        KOJE),
}
for _z in "123456789":
    MARKEN[_z] = ("punkt" + _z, None)

# ══════════════════════════════════════════════════ DER WANDLER
#
# Ein Wandler ist eine Kartendatei mit ein paar Kopfzeilen mehr. Alles
# hier sind **Voreinstellungen**: jede Zeile laesst sich in der Datei
# ueberschreiben, und die Datei laesst sich ohne eine Zeile Python
# austauschen. Nichts am Wandler steht im Code fest.

WANDLER = dict(
    # ---- Fahrt ----------------------------------------------------
    tempo=54.0,               # Pixel je Sekunde, die er hoechstens schafft
    schub_an=0.9,             # Sekunden, bis der Befehl voll anliegt
    schub_ab=1.4,             # Sekunden, bis er ausgelaufen ist
    dreh=26.0,                # Grad je Sekunde bei vollem Ausschlag
    dreh_an=1.6,              # Sekunden, bis die Lenkung voll anliegt
    ueberlast=1.45,           # Faktor auf Tempo und Takt bei SHIFT
    ueberlast_last=0.22,      # so viel Belastung je Sekunde auf die Beine

    # ---- Wie der Rumpf den Beinen folgt ---------------------------
    # Das ist die Stelle, an der sich entscheidet, ob die Maschine laeuft
    # oder schwebt. Der Rumpf bekommt **keine** eigene Geschwindigkeit: er
    # wird von den stehenden Fuessen getragen und zieht mit diesem Wert
    # nach. Hoch = straff und mechanisch, niedrig = weich und traege.
    koerper_zug=9.0,
    # Gemessen, nicht geraten: bei 6.0 wanderte ein Reaver beim Drehen auf
    # der Stelle 83 Pixel weit, bei 14.0 noch 26 - und er dreht dabei auch
    # noch schneller, ohne dass das Geradeauslaufen darunter leidet.
    kurs_zug=14.0,            # dasselbe fuer die Ausrichtung
    wanken=0.7,               # Grad Schraeglage je fehlendem Standbein
    wanken_zug=3.0,
    heben=1.4,                # Pixel, um die der Rumpf je Schritt atmet
    heben_zug=7.0,

    # ---- Masse ------------------------------------------------------
    radius=46.0,              # Rumpfradius fuer grobe Abfragen
    # Kameraruckeln je aufsetzendem Fuss. Klein, und das ist wichtig:
    # bei 2,3 Gruppen je Sekunde klingt ein Stoss nie ab, bevor der
    # naechste kommt. Gemessen lag das Ruckeln dauerhaft bei 4 Pixeln -
    # das ist kein Stampfen mehr, das ist ein flackerndes Bild.
    stoss=0.5,
    stoss_masse=0.25,         # Aufschlag je Gewichtsklasse
    # ---- Umkippen --------------------------------------------------
    # Eine Laufmaschine steht, solange ihr Schwerpunkt ueber der Flaeche
    # liegt, die ihre stehenden Fuesse aufspannen. Faellt er heraus, kippt
    # sie - und zwar unabhaengig davon, wie viele Beine noch heil sind.
    # Zwei Beine hinten tragen einen Rumpf nicht, dessen Masse davor liegt.
    kipp_zeit=1.1,            # so lange haelt sie sich noch, dann faellt sie
    kipp_wanken=14.0,         # Schraeglage beim Kippen, in Grad
    kipp_dauer=2.2,           # so lange dauert der Sturz
)

# Wie der Rumpf von aussen aussieht. Gebaut wird er aus dem Grundriss der
# Decks - keine zweite Karte noetig -, hier steht nur, wie kraeftig.
WANDLER_BILD = dict(
    panzer_dunkel=196,        # so hell ist das unterste Deck (255 = wie innen)
    stufe_hell=14,            # so viel heller wird jedes Deck darueber
    plattenstoss=4,           # alle so viele Kacheln ein grosser Stoss
    bug_tiefe=3,              # so viele Kachelreihen zaehlen als Bug
    winkel=2,                 # so viele Warnwinkel am Bug
    winkel_deckkraft=96,      # abgenutzt, nicht frisch lackiert
    zoom=2,                   # Aussenansicht: 1 Bildpunkt je so viele Weltpunkte
    zoom_grenzen=(1, 5),
)

# Gangarten. Der Takt sagt, wie viele Fuesse je Sekunde aufsetzen; die
# Ordnung sagt, in welcher Reihenfolge. Eine neue Gangart ist ein Eintrag.
#
# `ordnung` ist eine Liste von Gruppen. Jede Gruppe tritt gemeinsam an.
# Zwei Beine in einer Gruppe heisst Trab, eines heisst Schreiten.
GANG = dict(
    takt_ruhe=0.9,            # Gruppen je Sekunde im Schritttempo
    takt_voll=2.3,            # Gruppen je Sekunde bei vollem Schub
    schritt_dauer=0.34,       # Sekunden, die ein Fuss in der Luft ist
    schritt_dauer_voll=0.21,  # dasselbe bei vollem Schub
    # Schrittweite und Hub sind **Anteile der Beinreichweite**, keine festen
    # Pixel. Sonst schlurft ein Imperator mit 224 Pixeln Bein genauso weit
    # wie ein Warhound mit 134 - und sieht damit aus, als truege er zu
    # grosse Schuhe.
    schritt_anteil=0.42,      # so weit greift ein Fuss hoechstens
    schritt_min=9.0,          # darunter lohnt kein Schritt
    hub_anteil=0.075,         # so hoch hebt ein Fuss im Schritttempo
    hub_voll_anteil=0.115,    # dasselbe bei vollem Schub
    nachgreifen=0.34,         # so viel vom Schleppfehler holt ein Schritt auf
    # Die Schrittweite wird **geregelt**, nicht ausgerechnet. Wie weit der
    # Rumpf je Zyklus wirklich vorankommt, haengt an Dingen, die sich nicht
    # sauber in eine Formel bringen lassen: wie viele Fuesse gerade tragen,
    # wie alt ihre Standpunkte sind, wie straff der Rumpf nachzieht. Also
    # misst die Maschine ihr eigenes Tempo und greift entsprechend weiter
    # oder kuerzer - so, wie es ein Laeufer auch tut.
    #
    # Das ist nicht nur robuster, es ist richtiger: faellt ein Bein aus oder
    # zieht die Ueberlast an, regelt sie nach, ohne dass dafuer irgendwo ein
    # Sonderfall steht.
    regel_start=0.62,         # Startwert, nah am eingeschwungenen Zustand
    regelung=1.4,             # wie schnell nachgeregelt wird, je Sekunde
    regel_min=0.25,
    regel_max=2.40,
    zwang=1.9,                # ab diesem Vielfachen von schritt_max tritt ein
                              # Bein auch ausser der Reihe (Notschritt)
    stand_mindest=1,          # so viele Fuesse bleiben immer am Boden
    # Die eigentliche Bedingung ist aber nicht die Anzahl, sondern die
    # **Stuetzflaeche**: die Flaeche, die die stehenden Fuesse aufspannen,
    # verbreitert um die Auflage jedes Fusses. Ein Bein darf nur abheben,
    # wenn der Rumpf danach immer noch darueber liegt.
    fuss_halt=0.55,           # Auflage eines Fusses, Vielfaches der Fussbreite
    halt_mindest=0.02,        # so viel Rand bleibt, Anteil der Rumpfbreite
    # Faellt ein Bein aus, ruecken die uebrigen Fuesse nach - so weit sie
    # reichen. Eine beschaedigte Maschine verteilt ihr Gewicht um und
    # humpelt weiter, statt einzufrieren.
    #
    # Nur **teilweise**, und das ist der Punkt: voll nachgerueckt koennte
    # ein Sechsbeiner auf zwei hinteren Beinen weiterlaufen, indem er die
    # Fuesse ganz nach vorn unter die Masse stellt. Das tut eine Maschine
    # dieser Groesse nicht - sie kippt.
    ausgleich=0.5,            # so viel vom Fehlbetrag holen die Fuesse auf
    # Ab so vielen heilen Beinen gilt die Stuetzflaeche auch beim Treten.
    #
    # **Vier**, und das folgt zwingend: wer drei Beine hat und eines hebt,
    # steht auf zweien - auf einer Strecke, nicht auf einer Flaeche. Eine
    # Maschine mit drei Beinen kann also gar nicht statisch gehen, so wenig
    # wie eine mit zweien. Sie muss balancieren.
    #
    # Wer balanciert, den haelt nicht die Flaeche, sondern die Zeit: bleibt
    # er laenger als WANDLER["kipp_zeit"] ohne Halt, faellt er. Damit
    # humpelt ein angeschlagener Vierbeiner weiter, und ein Sechsbeiner mit
    # nur noch zwei hinteren Beinen kippt trotzdem - denn der bekommt
    # seinen Halt auch zwischen zwei Schritten nicht zurueck.
    statisch_ab=4,
    dreh_greifen=0.55,        # wie stark ein Schritt die Drehung vorwegnimmt
)

# Bein: Geometrie und Aussehen. Laengen in Pixeln, alles je Klasse
# ueberschreibbar.
BEIN = dict(
    # **Die Beinmasse sind Anteile der halben Rumpfbreite, keine festen
    # Pixel.** Das ist der Unterschied zwischen einem Tragwerk und
    # Spaghetti: ein Bein, das eine Maschine von 600 Pixeln Breite traegt,
    # ist keine 18 Pixel dick. Es ist ein riesiges mechanisches Bauteil,
    # so dick wie ein Viertel des Rumpfes und so lang wie dieser breit.
    #
    # Absolut gesetzte Werte in einer Kartendatei gewinnen weiterhin.
    **BEIN_GRUNDMASS,         # Rueckfall, falls nichts gerechnet wird
    ober_anteil=0.68,         # Huefte bis Knie, Anteil der halben Rumpfbreite
    unter_anteil=0.86,        # Knie bis Fuss
    dicke_anteil=0.27,        # Dicke des Oberschenkels
    dicke_unter_anteil=0.72,  # davon die Dicke des Schienbeins
    fuss_anteil=1.75,         # davon die Kantenlaenge der Fussplatte
    huefte_anteil=1.35,       # davon die Schulter
    knie_mindest=0.06,        # so weit bleibt das Bein vom Durchstrecken weg
    spreizen=0.58,            # Ruhepunkt des Fusses, Anteil der Reichweite
    schatten=0.62,            # Deckkraft des Beinschattens
    schatten_versatz=5,       # Pixel, die der Schatten nachhinkt
    hub_massstab=0.0042,      # so viel groesser wird ein Bein je Pixel Hub
    hub_hell=26,              # so viel heller wird es im Schwung
)

# Bauklassen. Sie legen nur Voreinstellungen fest - was in der Kartendatei
# steht, gewinnt. Decks und Beine kommen aus der Datei, hier steht, was
# eine Klasse *bedeutet*.
# Bauklassen. Jede ist eine **eigene Basis**, kein anders grosser Bauklotz:
# eigener Umriss, eigene Beinzahl, eigenes Fahrverhalten. Was hier steht,
# sind Voreinstellungen - was in der Kartendatei steht, gewinnt.
#
# Das Drehen unterscheidet sie am staerksten, und zwar um mehr als eine
# Zehnerpotenz. Ein Warhound dreht sich auf der Stelle um; ein Hundertfuss
# braucht dafuer Minuten und ist gebaut, um geradeaus zu gehen. Das ist
# keine Schikane, das ist die Bauform: Masse mal Hebel.
WANDLER_KLASSEN = {
    "warhound": dict(
        name="WARHOUND", gewicht=1,
        tempo=78.0, dreh=34.0, takt=1.25,
        umriss="raptor",
    ),
    "reaver": dict(
        name="REAVER", gewicht=2,
        tempo=54.0, dreh=11.0, takt=1.0,
        umriss="schlachtschiff",
    ),
    "imperator": dict(
        name="IMPERATOR", gewicht=3,
        tempo=33.0, dreh=3.5, takt=0.72,
        umriss="festung",
    ),
    "hundertfuss": dict(
        # Gebaut, um geradeaus zu gehen, und fuer sonst nichts. Eine volle
        # Drehung dauert ueber zwei Minuten - wer den Kurs aendern will,
        # plant ihn vorher.
        name="HUNDERTFUSS", gewicht=3,
        tempo=44.0, dreh=1.4, takt=0.9,
        umriss="wurm",
    ),
}

# ══════════════════════════════════════════════════ HOEHE JE RUMPF
#
# Die Tabelle EBENEN_HOEHE weiter oben ist keine willkuerliche Liste: sie
# kodiert einen gleichbleibenden Wahrnehmungsschritt. Steht man oben, ist
# jedes Deck darunter genau SCHRITT so gross wie das darueber - nur der
# Boden faellt bewusst aus der Reihe und sitzt tiefer, damit er sich
# absetzt.
#
#     hoehe(n) = brennweite * (SCHRITT**-n - 1)      n = Decks darunter
#
# Damit laesst sich die Staffel fuer **jede** Deckzahl erzeugen, und die
# ersten Werte sind auf den Pixel die von Hand gesetzten. Ein Warhound mit
# drei Decks und ein Imperator mit zehn sehen beide richtig aus.
HOEHEN = dict(
    schritt=0.895,            # scheinbare Groesse je Deck nach unten
    boden_schritt=0.836,      # der eine groessere Sprung hinunter zum Boden
    decks_hoechstens=12,
)



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
