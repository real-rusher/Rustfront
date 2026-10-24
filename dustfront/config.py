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

# Der Wuestensatz. Heller, gelber, ohne Platten und ohne Nieten - Sand
# hat keine Fugen. Die Wand ist Lehm und Fels statt Blech: eine Karte im
# Freien darf nicht aussehen wie ein Gang im Rumpf, sonst haette man sie
# sich sparen koennen.
C_SAND = (96, 79, 54)
C_SAND_KORN = (116, 97, 66)
C_SAND_DUNKEL = (72, 58, 40)
C_FELS = (110, 92, 66)
C_FELS_OBEN = (146, 124, 90)
C_FELS_KANTE = (56, 44, 31)
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

# Tempo. Etwas langsamer als bis 0.26, und aus einem gemessenen Grund:
# auf Distanz war kaum zu treffen. Nachgebaut mit denselben Regeln wie
# Spieler.schritt(), ein Ziel, das Haken schlaegt, und ein Schuetze, der
# ideal vorhaelt - Trefferquote mit dem Sturmgewehr auf 470 Pixel:
#
#     bis 0.26, gehend (132)          20 %
#     bis 0.26, sprintend (205)       13 %
#     jetzt (108, kein Sprint)        23 %
#
# Der groesste Hebel war dabei nicht das Tempo, sondern der Sprint: er
# machte jedes flüchtende Ziel auf offenem Sand fast unerreichbar. Er ist
# darum durch den Dash ersetzt - schnell sein geht weiter, aber nur kurz
# und nur, wenn man es sich einteilt.
#
# Die Beschleunigung ist bewusst nur leicht gesenkt. Weniger davon macht
# Treffen gemessen **schwerer**, nicht leichter: das Ziel steckt dann
# laenger in einer Richtungsaenderung, und auf die kann man nicht
# vorhalten (110 px/s mit 600 Beschleunigung: 19,6 % gegen 23,4 % mit 1250).
# Tempo aller Figuren und Geschosse (seit 0.34.43). Gemeldet: "Das Ganze
# erscheint mir ein bisschen zu schnell, nicht wirklich erkennbar ... ich
# wollte, dass sich das ein bisschen wie RimWorld anschaut ... das
# Bewegungstempo ist viel zu schnell. Mach das Bewegungstempo bei allen
# langsamer, und dass die Shells ein kleines bisschen langsamer fliegen."
# Die Zahlen unten (SPIELER, GEGNER, BOSSE, WAFFEN) bleiben, wie sie
# abgestimmt sind; diese Faktoren gelten fuer alle zugleich, damit das
# Verhaeltnis (der Renner ist schneller als ein Spieler ...) bleibt.
BEWEGUNG = dict(
    lauf=0.65,                # x Lauftempo von Spielern, Bots, Gegnern und Bossen
    geschoss=0.8,             # x Tempo jedes Geschosses (die Reichweite bleibt)
)

# Zurufe (seit 0.34.50): jeder Bot sagt den Bots in Sprechweite
# (K.TRUPP["sprech_weite"]), was er sieht - nicht im selben Augenblick,
# ein Satz dauert. Daneben der Funk der Anfuehrer (K.TRUPP["funk_dauer"]).
# Gemeldet: "zwei separate Kommunikationssysteme ... alle Bots mit Bots in
# der Naehe sprechen ... Das Sprechen muss dabei nicht instant sein."
SPRECHEN = dict(
    dauer=(0.8, 1.4),         # so lange dauert ein Zuruf, bis die anderen ihn haben (s)
    wiederholen=6.0,          # denselben Gegner sagt er erst nach so langer Zeit wieder an
    gedaechtnis=6.0,          # so lange weiss einer, was ihm zugerufen wurde
    zeigen=12,                # so viele Zurufe zeigt der Testmodus unten links
)

# Sprinten (seit 0.34.50) - nur die Bots, der Spieler kann es (noch) nicht.
# Gemeldet: "ein nettes Feature waere, dass die Bots sprinten koennen ...
# mit einer bestimmten Sprintausdauer, in passenden Situationen, zum
# Beispiel unter Panik, wenn eine Granate eingeschlagen ist."
SPRINT = dict(
    faktor=1.5,               # x Lauftempo beim Sprinten
    dauer=3.0,                # so viele Sekunden reicht volle Ausdauer
    erholung=0.25,            # so viel Ausdauer (Anteil) kommt je Sekunde ohne Sprint zurueck
    mindest=0.35,             # so viel muss da sein, um einen Sprint zu beginnen
    staub_takt=0.08,          # so oft wirbelt er Staub auf (s)
)

SPIELER = dict(
    radius=9.0,
    # Pixel pro Sekunde bei vollem Lauf (war 132, dann 108; seit 0.34.43 mal
    # BEWEGUNG["lauf"])
    tempo=108.0 * BEWEGUNG["lauf"],
    beschleunigung=1150.0,    # wie schnell das Tempo erreicht wird (war 1250)
    bremsung=1400.0,          # wie schnell er steht, wenn man loslaesst (war 1500)
    leben=100.0,
    # Kein Unverwundbarkeitsfenster nach einem Treffer. Es gab einmal
    # eines (0.6 s) und es war ein Fehler: von einer Schrotladung zaehlte
    # genau ein Kuegelchen, und Getroffene blinkten wie frisch
    # eingestiegen. Schutz gibt es nur nach dem Einstieg, siehe
    # GEFECHT["schutz"].
    stiefel_abstand=26.0,     # Pixel zwischen zwei Staubwolken
)

# Der Dash ersetzt den Sprint.
#
# Zwei Ladungen, die sich **nacheinander** wieder fuellen: erst die eine,
# dann die andere. Wer beide verbraucht, wartet also doppelt so lange auf
# die zweite - das ist der Unterschied zum Sprint, den man einfach
# gedrueckt hielt. Ein Dash ist eine Entscheidung.
#
# Ein Stoss von 0,16 s auf 430 px/s bringt rund 70 Pixel - gut zwei
# Kacheln. Genug, um aus einem Feuer, einer Stampferwelle oder einer
# Schusslinie zu kommen; zu wenig, um damit ueber die Karte zu reisen.
DASH = dict(
    ladungen=3,               # seit 0.31 drei statt zwei
    nachladen=2.7,            # Sekunden je Ladung, eine nach der anderen (vorher 3.4)
    tempo=430.0,              # Pixel pro Sekunde waehrend des Stosses
    dauer=0.16,               # so lange haelt der Stoss
    sperre=0.30,              # frueher geht der naechste nicht
    auslauf=1.25,             # am Ende auf so viel Lauftempo abgefangen
    staub=10,                 # Staubwolken beim Absprung
    bild_ausklang=0.08,       # Windfahne verblasst kurz nach dem Stoss
    bild_wind_start=(0.0, 0.045, 0.090),
    bild_wind_aufbau=0.04,
    bild_wind_abstand=(22, 34, 46),
    bild_wind_laenge=(9, 7, 5),
    bild_wind_seite=(0, -4, 4),
    bild_wind_hell=(190, 190, 184),
    bild_wind_dunkel=(103, 99, 91),
)

MUENDUNGSFEUER = dict(
    versatz=10.0,             # Lichtkern liegt vor der Laufspitze
)

KAMERA = dict(
    # je hoeher, desto straffer klebt sie am Spieler. Bis 0.32.5 waren es
    # 11: beim Laufen hing das Bild 10 Pixel hinterher und zog nach dem
    # Anhalten sichtbar nach - mit Zoom vergroessert (gemeldet). Mit 15
    # sind es 7.
    nachlauf=15.0,
    maus_zug=0.26,            # wie weit sie in Blickrichtung vorlaeuft
    maus_max=54.0,
    # Experimentell, Barrierefreiheit "BLICK VORAUS" (seit 0.32, aus als
    # Vorgabe): ein unsichtbarer Punkt vor der Waffe, in Blickrichtung,
    # ist die Bildmitte. Wie weit vorn, stellt jeder selbst ein
    # (einstellungen.py, kamera_blick_weite; Vorgabe 70, bis 0.32.5 fest 110).
    blick_nachlauf=6.0,       # weicher als sonst: Drehen soll nicht reissen
)

# Sichtweite im Gefecht (Mausrad, seit 0.30). 1 ist das normale Bild; mehr
# heisst: mehr Welt im Bild, kleiner gezeichnet. Alles ausserhalb des
# normalen Bildes liegt im **Nebel**: man sieht das Gelaende gedaempft,
# aber keine Wesen - keine Gegner, keine Mitspieler, keine Granaten. Ein
# weiterer Blick ist damit Ueberblick, kein Vorteil.
ZOOM = dict(
    stufen=(0.75, 1.0, 1.25, 1.5, 1.75, 2.0),
    start=1.0,
    weich=12.0,               # wie schnell der Zoom nachzieht
    nebel=(14, 10, 8, 168),   # Farbe und Deckkraft des Nebels
    nebel_rand=(96, 78, 56),  # die Kante des normalen Bildes
)

# Kameraruckeln.
#
# Hier lag einer der haesslichsten gemeldeten Fehler: beim Gastgeber
# zitterte das Bild ununterbrochen, bei den Gaesten ruehrte sich fast
# nichts. Die Ursache war keine Kleinigkeit im Zahlenwerk, sondern der
# Aufbau. `Welt.ruckeln` war **eine einzige Rueckmeldung ohne Absender
# und ohne Ort**, und die Spielszene haengte sie stur an ihre eigene
# Kamera. Der Gastgeber rechnet aber die ganze Welt: jeder Schuss, jeder
# Treffer, jede Granate und jeder Sturz **aller** Spieler auf **allen**
# Ebenen lief bei ihm zusammen. Gemessen an einer Runde, in der ein
# einziger anderer Spieler 1600 Pixel entfernt und eine Etage hoeher den
# Abzug hielt: 2,09 Pixel Dauerzittern beim Gastgeber, in 100 % der
# Bilder, Spitzen bis 7,95 - und 0,00 beim Gast, der ja nichts rechnet.
#
# Darum entscheidet ab jetzt nicht mehr der Ausloeser, sondern der
# Zuschauer. Jede Meldung sagt, **was** passiert ist, **wo** und **wem**;
# die Szene rechnet daraus aus, ob es sie ueberhaupt angeht:
#
#   * eine andere Ebene ruckelt gar nicht,
#   * in der Ferne ruckelt nichts (`reichweite`),
#   * was ein anderer tut, zaehlt nur zum Teil (`fremd`),
#   * und zwischen zwei Schlaegen liegt eine Sperre, damit Dauerfeuer
#     kein Dauerzittern mehr ergibt.
#
# Dazu die zweite Haelfte des Auftrags: selten und schwach. `anlass`
# haelt je Vorgang einen Faktor auf den Wert, der in der Waffentabelle
# steht. Der eigene Gewehrschuss steht auf 0,10 und liegt damit unter
# `schwelle` - er ruckelt schlicht nicht mehr. Uebrig bleibt, was ein
# Ruckeln verdient: eine Explosion neben einem, ein Treffer, den man
# selbst abbekommt, und der eigene Sturz.
RUCKELN = dict(
    staerke=1.0,          # Gesamtfaktor, greift auf alles
    max=3.2,              # so weit reisst es das Bild hoechstens (vorher 9.0)
    abbau=6.4,            # wie schnell es verklingt (vorher 2.6)
    schwelle=0.40,        # darunter wird gar nicht erst geruckelt
    sperre=0.22,          # Mindestabstand zweier Schlaege in Sekunden
    fremd=0.55,           # was ein anderer ausloest, zaehlt nur zum Teil
    reichweite=240.0,     # ab hier ist fremdes Ruckeln ganz weg
    fremde_ebene=0.0,     # eine andere Etage ruckelt nicht mit
    anlass=dict(
        schuss=0.10,      # der Dauerkandidat: bleibt unter der Schwelle
        wurf=0.0,         # eine Granate zu werfen ruckelt nicht
        nahkampf=0.12,
        treffer=0.16,     # wenn es einen selbst trifft
        explosion=0.30,
        sturz=0.35,
        tod=0.0,          # dass jemand faellt, reisst niemandem das Bild
    ),
)

# Farbiger Schein an den Bildraendern, fuer Zustaende, die man dauernd
# sieht: beim Aufhelfen zum Beispiel. Die Mitte bleibt frei, sonst sieht
# man nicht mehr, wer von wo kommt.
GLUT = dict(
    breite=42,                # so weit reicht der Schein ins Bild
    stufen=7,                 # so viele Rahmen bilden den Verlauf
    deckung=64,               # Deckkraft des innersten Rahmens
)

TREFFER = dict(
    blitz=0.09,               # Sekunden, die ein Getroffener hell aufleuchtet
    rueckstoss=118.0,         # Schub, den ein Treffer dem Ziel gibt
    zeitlupe=0.045,           # kurze Verlangsamung beim Toeten
)

# Das Trefferzeichen (seit 0.34.15): trifft man einen Gegner, springt am
# Mauszeiger kurz ein X auf, und es tickt. Erledigt (oder umgeworfen)
# heisst: ein groesseres rotes X und ein tieferer Ton. Nur der Schuetze
# sieht und hoert es - es ist seine Rueckmeldung, nicht die des Ziels.
TREFFERMARKE = dict(
    dauer=0.20,               # Sekunden fuer ein gewoehnliches Zeichen
    dauer_toedlich=0.45,
    abstand=0.06,             # schneller hintereinander zaehlt nicht neu (Feuer, Schrot)
    luecke=6,                 # Abstand der Striche vom Zeiger, in Bildpixeln
    laenge=5,
    laenge_toedlich=7,
    pop=0.5,                  # so viel groesser springt es auf
    laut=0.55,                # Lautstaerke des Tons
)

# ══════════════════════════════════════════════════ BEFINDEN
#
# Wie es einem geht, ohne dass man auf eine Zahl schaut.
#
# Ein Lebensbalken ist eine Zahl in Balkenform: man muss hinsehen, um sie
# zu lesen, und im Gefecht sieht man nicht hin. Was hier steht, arbeitet
# am Rand des Blickfelds und im Ohr - dort, wo man etwas merkt, ohne es
# anzusehen.
#
# Der rote Schein setzt unterhalb von `ab` ein und waechst. Unter
# `dauerhaft_ab` bleibt er stehen und **pulst**, mit einem Herzschlag im
# Ohr; je weniger Leben, desto schneller. Und mit jedem Schlag wird alles
# andere dumpfer - Schuesse, Schritte, spaeter die Musik. Das ist der
# eigentliche Griff: nicht lauter werden, sondern die Welt wegnehmen.
#
# Der Herzschlag laeuft in **Klassen** und nicht stufenlos. Ein Ton, der
# sich unmerklich beschleunigt, merkt niemand; drei klar verschiedene
# Zustaende merkt jeder, und man weiss nach zwei Runden, in welchem man
# steckt.
BEFINDEN = dict(
    ab=0.70,              # ab diesem Lebensanteil faerbt sich der Rand
    dauerhaft_ab=0.38,    # darunter bleibt er stehen und pulst
    breite=64,            # so weit reicht der Schein ins Bild
    stufen=9,             # so viele Rahmen bilden den Verlauf
    deckung_max=132,      # Deckkraft des innersten Rahmens bei null Leben
    farbe=(148, 24, 18),
    # Ein Treffer schlaegt sofort auf und verklingt wieder. Ohne das
    # merkt man einen Treffer erst daran, dass der Balken kuerzer ist.
    treffer_stoss=0.55,
    treffer_abbau=2.1,
    # Puls. Sekunden je Schlag, von `dauerhaft_ab` bis null Leben.
    puls_langsam=1.20,
    puls_schnell=0.50,
    puls_tiefe=0.50,      # wie stark der Schein mit dem Schlag atmet
    puls_schaerfe=2.6,    # je hoeher, desto knapper der Schlag
    # Herzschlag im Ohr: drei Klassen, je Klasse eine Lautstaerke.
    klassen=(0.38, 0.24, 0.12),
    klassen_laut=(0.30, 0.52, 0.80),
    # Wie dumpf alles andere wird. 0 = unveraendert, 1 = ganz weggenommen.
    dumpf_max=0.85,
)

# Das Medkit. Der Gegenschlag zum roten Rand: **blau, kalt und sehr
# klar** - und danach ein paar Sekunden Ruhe.
#
# Nachgesehen, wie andere Spiele so etwas machen: der Adrenalinschuss in
# Left 4 Dead 2 dreht den Kontrast hoch, zieht die Farbe heraus und legt
# eine starke Vignette an - "tunnel vision through increased vignetting,
# maxes out the color correction to suck the color from the shot". Das
# ist genau die Sprache, die hier gebraucht wird, nur in die andere
# Richtung: nicht enger und rot, sondern weiter, kalt und scharf.
#
# Drei Griffe, alle drei ohne Shader, alle drei auf der fertigen Flaeche:
#
#   Kontrast   Bild verdoppeln, Mitte abziehen. out = 2*in - grau.
#              Das ist eine harte Kontrastkurve, und Kontrast ist das,
#              was das Auge als "scharf" liest - ohne dass ein einziger
#              Pixel schaerfer wird, was bei Pixelkunst auch nicht ginge.
#   Kaelte     mit einem kuehlen Ton multiplizieren. Der Rostton der
#              Welt faellt dabei zusammen, das Blau bleibt stehen.
#   Blitz      ein kurzer heller Anschlag, hart einsetzend und langsam
#              ausklingend. Er markiert den Augenblick.
MEDKIT_BLICK = dict(
    dauer=1.30,           # so lange ist es kalt und klar
    blitz=0.18,           # davon der helle Anschlag
    farbe=(104, 198, 236),
    rand_deckung=110,     # blauer Schein am Rand
    kontrast=0.80,        # 0 = wie sonst, 1 = volle Verdoppelung
    # Um welchen Grauwert der Kontrast dreht. **Nicht 128.** Die Welt von
    # DUSTFRONT ist dunkel: gemessen liegt ihre mittlere Helligkeit bei
    # 36 von 255. Mit 128 als Drehpunkt faellt alles unter der Mitte ins
    # Schwarze, und wer ein Medkit anlegt, sieht eine Sekunde lang gar
    # nichts mehr - ausgerechnet in dem Moment, in dem er getroffen wurde.
    # Der Drehpunkt gehoert also dorthin, wo das Bild wirklich liegt.
    kontrast_mitte=44,
    kaelte=0.60,          # wie weit es ins Kalte kippt
    kalt_ton=(196, 228, 255),   # damit wird multipliziert
    kalt_hebung=118,      # so viel Blau kommt dazu, hebt die Schatten
    ruhe=3.0,             # so lange bleiben roter Schein und Puls danach weg
)

# ══════════════════════════════════════════════════ AUSSENHAUT
#
# Texturen und Klaenge. Alles, was das Spiel zeigt und hoert, hat einen
# Namen. Zu jedem Namen sucht das Spiel zuerst eine Datei und zeichnet oder
# rechnet nur dann selbst, wenn keine da ist:
#
#     assets/<name>.png           Bild
#     assets/sfx/<name>/<datei>.wav, .ogg oder .mp3   Klang
#
# Eine hingelegte Datei ersetzt den Platzhalter, ohne dass eine Zeile Code
# geaendert wird. Welche Namen es gibt, steht in BILD_MASS und KLANG_NAMEN
# weiter unten; `python -m dustfront --vorlagen` schreibt von jedem Bild
# eine masshaltige Vorlage zum Uebermalen heraus.

ASSETS = dict(
    ordner="assets",              # Name des Ordners neben dem Paket
    sfx="sfx",                    # Unterordner fuer die Klaenge
    bild_endungen=(".png", ".webp", ".bmp"),
    ton_endungen=(".wav", ".ogg", ".mp3"),
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

# Blut je Art (seit 0.34.33). Gemeldet: "je nach Entity anderes Blut."
# `farbe` faerbt den Fleck am Boden (das Bild "blut" gibt die Form - wer es
# ersetzt, behaelt seine Form, die Farbe kommt von hier; "mensch" bleibt
# ungefaerbt, so wie gemalt), `spritzer` die Tropfen beim Tod, `groesse`
# macht den Fleck groesser als der Koerper allein.
BLUT = {
    "mensch":  dict(farbe=None,           spritzer=(128, 26, 20), groesse=1.15),
    "zombie":  dict(farbe=(78, 40, 24),   spritzer=(96, 52, 30),  groesse=1.1),
    "saeure":  dict(farbe=(88, 150, 40),  spritzer=(132, 196, 64), groesse=1.35),
    "galle":   dict(farbe=(170, 142, 44), spritzer=(214, 186, 70), groesse=1.6),
    "koloss":  dict(farbe=(52, 16, 14),   spritzer=(80, 24, 20),  groesse=1.25),
    "brut":    dict(farbe=(92, 50, 110),  spritzer=(136, 80, 156), groesse=1.3),
    "asche":   dict(farbe=(40, 36, 34),   spritzer=(255, 140, 40), groesse=1.2),
}

# Wie Wesen sterben (seit 0.34.33). Gemeldet: "gerade kann ich nie sicher
# sein, ob die einfach verschwinden oder ob die tot sind." Wer stirbt,
# hinterlaesst Spritzer, einen Fleck im Blut seiner Art und einen Todeslaut
# (Klang "tod"). Wer nur verschwindet (Testmodus ENTF, ein Bot verlaesst
# die Runde), hinterlaesst nichts. Die Leiche, die 0.34.33 noch umfallen
# liess, ist seit 0.34.34 wieder draussen ("Der Fleck reicht").
TOD = dict(
    # Wer welches Blut hat. Jede Art aus GEGNER und BOSSE muss hier stehen -
    # tests/test_spiel.py prueft das.
    wesen={
        "spieler": "mensch",
        "laeufer": "zombie",
        "renner": "zombie",
        "brecher": "zombie",
        "speier": "saeure",
        "blaeher": "galle",
        "koloss": "koloss",
        "mutter": "brut",
        "brandstifter": "asche",
    },
    spritzer=18,              # Tropfen beim Tod
    laut=0.7,                 # Lautstaerke des Todeslauts ...
    laut_gross=0.95,          # ... und bei einem grossen Wesen (Radius ab 14)
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
    # Der Wuestensatz. Dieselben Masse, eigener Name: wer eine
    # Karte im Freien baut, bekommt Sand statt Blech.
    "sand":             (TILE, TILE),
    "sand_2":           (TILE, TILE),
    "sand_3":           (TILE, TILE),
    "sand_4":           (TILE, TILE),
    "sand_wand":        (TILE, TILE),
    "sand_kiste":       (TILE, TILE),
    # Gelaende und Kleinkram (seit 0.34.6, siehe KACHELN). Die stehenden
    # davon haben ausserdem ein Bild "<name>_oben" weiter unten.
    "fels":             (TILE, TILE),
    "fels_2":           (TILE, TILE),
    "fels_3":           (TILE, TILE),
    "brocken":          (TILE, TILE),
    "brocken_2":        (TILE, TILE),
    "brocken_3":        (TILE, TILE),
    "sandsack":         (TILE, TILE),
    "holzkiste":        (TILE, TILE),
    "kaktus":           (TILE, TILE),
    "schrott":          (TILE, TILE),
    "schrott_2":        (TILE, TILE),
    "schrott_3":        (TILE, TILE),
    "piste":            (TILE, TILE),
    "piste_2":          (TILE, TILE),
    "piste_3":          (TILE, TILE),
    "piste_4":          (TILE, TILE),
    "kies":             (TILE, TILE),
    "kies_2":           (TILE, TILE),
    "kies_3":           (TILE, TILE),
    "kies_4":           (TILE, TILE),
    "pflaster":         (TILE, TILE),
    "pflaster_2":       (TILE, TILE),
    "pflaster_3":       (TILE, TILE),
    "gestruepp":        (TILE, TILE),
    "gestruepp_2":      (TILE, TILE),
    "gestruepp_3":      (TILE, TILE),
    "gestruepp_4":      (TILE, TILE),
    "dielen":           (TILE, TILE),
    "dielen_2":         (TILE, TILE),
    # Verschneiter Kachelsatz fuer die lokale Hoehenkarten-Demo.
    "schnee":           (TILE, TILE),
    "schnee_2":         (TILE, TILE),
    "schnee_3":         (TILE, TILE),
    "schnee_4":         (TILE, TILE),
    "schnee_fels":      (TILE, TILE),
    "gitter":           (TILE, TILE),
    "wand":             (TILE, TILE),
    "kiste":            (TILE, TILE),
    "treppe_hoch":      (TILE, TILE),
    "treppe_runter":    (TILE, TILE),
    "luke":             (TILE, TILE),
    "aufzug_tuer":      (TILE, TILE),
    "aufzug_schacht":   (TILE, TILE),
    # Figuren, quadratisch und nach rechts schauend. Die Figur mit Waffe
    # braucht mehr Flaeche als die Figur allein, sonst ragt der Lauf der
    # Scharfschuetzenwaffe hinaus.
    "spieler":          (28, 28),
    "spieler_repetierer": (56, 56),
    "spieler_sturm":      (56, 56),
    "spieler_schrot":     (56, 56),
    "spieler_scharf":     (56, 56),
    "spieler_lmg":        (56, 56),
    "spieler_rakete":     (56, 56),
    "spieler_granate":    (56, 56),
    "spieler_rauch":      (56, 56),
    "spieler_molotov":    (56, 56),
    "spieler_blend":      (56, 56),
    "spieler_brecheisen": (56, 56),
    "spieler_medkit":     (56, 56),   # waehrend des Anlegens
    "spieler_boden":      (28, 28),   # wer am Boden liegt
    "leiche":             (28, 28),   # eine Leiche, die bald verschwindet (Testmodus, 0.34.40)
    "gegner_laeufer":   (28, 28),
    "gegner_brecher":   (44, 44),
    "gegner_renner":    (24, 24),
    "gegner_speier":    (30, 30),
    "gegner_blaeher":   (34, 34),
    "puppe":            (28, 28),     # Zielpuppe im Schiessstand der Lobby
    # Bosse. Sie sind deutlich groesser als alles andere - man soll auf
    # den ersten Blick sehen, dass da etwas anderes steht.
    "boss_koloss":      (58, 58),
    "boss_mutter":      (48, 48),
    "boss_brandstifter": (46, 46),
    # Kleinkram
    "geschoss":         (8, 4),
    "speichel":         (10, 6),
    "muendung":         (20, 20),
    "medkit":           (16, 14),
    "munikiste":        (16, 14),
    "granate":          (10, 10),
    "c4_brick":         (12, 8),
    "rauchgranate":     (10, 10),
    "molotov":          (10, 10),
    "blendgranate":     (10, 10),
    "flugrakete":       (16, 8),
    "rpg_kiste":        (18, 14),
    "huelse":           (4, 3),
    # Waffensymbole fuer Hotbar und Inventar, Seitenansicht nach rechts
    "waffe_repetierer": (26, 11),
    "waffe_sturm":      (26, 11),
    "waffe_schrot":     (26, 11),
    "waffe_scharf":     (26, 11),
    "waffe_lmg":        (26, 11),
    "waffe_rakete":     (26, 11),
    "waffe_granate":    (26, 11),
    "waffe_c4":         (26, 11),
    "waffe_detonator":  (26, 11),
    "waffe_detonator_bereit": (26, 11),
    "waffe_rauch":      (26, 11),
    "waffe_molotov":    (26, 11),
    "waffe_blend":      (26, 11),
    "waffe_brecheisen": (26, 11),
    # Dekale und Schatten. Das Mass ist hier ein Basismass: das Spiel rechnet
    # die Flaeche auf die Groesse um, die es gerade braucht. Wer sie ersetzt,
    # malt also nicht fuer eine feste Groesse, sondern eine Form.
    "schatten":         (48, 24),
    "blut":             (26, 26),
    "brandfleck":       (156, 156),
    "wandschatten":     (TILE + DEKAL["wand_versatz"], TILE + DEKAL["wand_versatz"]),
    # Draufsicht auf die Oberseite stehender Kacheln (seit 0.34.3, siehe
    # STEHEN). Die Kachelbilder darueber sind halb von vorn gemalt.
    "wand_oben":        (TILE, TILE),
    "sand_wand_oben":   (TILE, TILE),
    "schnee_fels_oben": (TILE, TILE),
    "kiste_oben":       (24, 24),
    "sand_kiste_oben":  (22, 22),
    "fels_oben":        (TILE, TILE),
    "fels_2_oben":      (TILE, TILE),
    "fels_3_oben":      (TILE, TILE),
    "brocken_oben":     (24, 24),
    "brocken_2_oben":   (24, 24),
    "brocken_3_oben":   (24, 24),
    "sandsack_oben":    (TILE, TILE),
    "holzkiste_oben":   (26, 26),
    "kaktus_oben":      (18, 18),
    "schrott_oben":     (TILE, TILE),
    "schrott_2_oben":   (TILE, TILE),
    "schrott_3_oben":   (TILE, TILE),
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
    "lmg_salve",
    "lmg_dauer",
    "c4_explosion",
    "granate",
    "sturz",                # Aufsetzen nach einem Fall
    "nahkampf",
    "nahkampf_schwung",
    "nahkampf_treffer_organisch",
    "nahkampf_treffer_metall",
    "wurf",
    "medkit",
    "aufheben",
    "molotov",              # Glas zerbricht und Feuer faengt
    "molotov_glass",
    "molotov_whoosh",
    "smoke_grenade",
    "reload",
    "rundenstart",
    "won_match",
    "lost_match",
    "downed_not_dead",
    "tod",                  # wer stirbt (seit 0.34.34)
    "blend",                # der Knall der Blendgranate
    "rakete",               # der Abschuss
    "erfasst",              # Ton, wenn die Erfassung steht
    "blend_pfeifen",        # das Pfeifen danach im Ohr
    "speien",               # der Spuck des Speiers
    "boss_ansage",          # ein Boss kuendigt an, was er gleich tut
    "dash",                 # der kurze Stoss
    "ruf",                  # wer am Boden liegt, ruft nach Hilfe
    "trefferzeichen",       # eigener Treffer (seit 0.34.15)
    "trefferzeichen_toedlich",   # eigener Treffer, der erledigt
    "buggy_tuer",           # in den Buggy und wieder heraus (seit 0.34.9)
    "buggy_aufprall",       # der Buggy rumst gegen etwas
    "buggy_rutschen",       # die Reifen quietschen, wenn er rutscht (seit 0.34.16)

    # Der eigene Herzschlag bei wenig Leben. Wie jeder andere Name auch
    # ersetzbar: assets/sfx/herzschlag.wav gilt vor dem Platzhalter.
    "herzschlag",
    "menue",
    "menue_ok",
)

# Einige Aufnahmen sind absichtlich in Unterordnern nach Art sortiert.
# Der Spielcode fragt weiter nach einem lesbaren Ereignisnamen.
KLANG_ORDNER = {
    "nahkampf_schwung": "nahkampf/into_air",
    "nahkampf_treffer_organisch": "nahkampf/hit_organic",
    "nahkampf_treffer_metall": "nahkampf/hit_metal",
    "molotov_glass": "molotov/glass_shatter",
    "molotov_whoosh": "molotov/fire_whoosh",
}

# Klaenge, die **nicht** gedaempft werden, wenn es einem schlecht geht.
# Der eigene Herzschlag wird ja gerade lauter, nicht leiser, und die
# Menuetoene gehoeren nicht in die Welt.
NIE_DUMPF = ("herzschlag", "menue", "menue_ok")

AUDIO = dict(
    gesamt=0.75,              # Gesamtlautstaerke
    schuss=0.85,              # Lautstaerke der Schuesse
    # Wie ein Ton mit der Entfernung leiser wird. Bis `nah` ist er voll
    # zu hoeren, ab `weit` nicht mehr; dazwischen faellt er gleichmaessig
    # ab. `fremde_ebene` gilt fuer alles, was eine Etage hoeher oder
    # tiefer passiert - man hoert es, aber gedaempft durch den Boden.
    nah=190.0,
    weit=1150.0,
    leiseste=0.06,            # darunter wird nichts mehr abgespielt
    fremde_ebene=0.45,
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
    passwortlaenge=16,        # laenger wird abgeschnitten
    stumm_nach=8.0,           # ohne Lebenszeichen gilt ein Gast als weg
    # So viele Zeilen duerfen sich hoechstens stauen, wenn die Leitung
    # gerade nicht mehr annimmt. Darueber wird das Ueberholte weggeworfen
    # statt nachgeschickt: eine Weltmeldung von vorhin sagt nichts, was
    # die naechste nicht besser sagt. Zwei Sekunden Takt sind reichlich
    # und trotzdem klein genug, dass kein Rueckstand entsteht.
    stau_zeilen=120,
    # Lobbys im eigenen Netz finden (lan.py). Ein eigener UDP-Port neben
    # dem Spielport: der Spielport wandert, wenn auf einem Rechner zwei
    # Lobbys offen sind, der Suchport muss fuer alle derselbe sein.
    such_port=50504,
    such_takt=1.5,            # so oft fragt die offene Liste nach
    such_vergessen=5.0,       # so lange ohne Antwort, dann faellt sie raus
    port_versuche=8,          # so viele Spielports ab `port` probiert die Lobby
)

# Spielen ueber das Internet (seit 0.34.13, dustfront/online.py).
#
# Weder Router noch Firewall muessen etwas erlauben: niemand lauscht nach
# draussen. Der Gastgeber haengt seine Lobby an einen kostenlosen "Quick
# Tunnel" von Cloudflare (Programm cloudflared, liegt in tools/cloudflared
# bei) und bekommt dafuer einen Code aus vier Woertern. Wer den Code
# eingibt, verbindet sich ueber dasselbe Programm - beide Seiten bauen nur
# ausgehende Verbindungen auf, und was lokal lauscht, lauscht nur auf
# 127.0.0.1. Genau das loest weder eine Freigabe im Router noch die
# Abfrage der Windows-Firewall aus.
ONLINE = dict(
    version="2026.10.0",      # die mitgelieferte Fassung von cloudflared
    ordner="tools/cloudflared",
    # Was im Ordner liegt, je System: Archiv, Name darin, Pruefsumme des
    # ausgepackten Programms. Ausgepackt wird beim ersten Gebrauch in den
    # Datenordner (pfade.py) - so traegt die Datei keinen "aus dem Internet"-
    # Vermerk, und weder SmartScreen noch Gatekeeper halten sie an.
    pakete={
        "windows-amd64": ("cloudflared-windows-amd64.zip", "cloudflared.exe",
                          "86aee4017b26625cee8484c113558f48effa4cd47f7aa05fcf425604e5d2b23c"),
        "darwin-arm64": ("cloudflared-darwin-arm64.tgz", "cloudflared",
                         "72edfd3eea463aef4d5cb89e2e209cecb048cc756c2b01915de2e0ad7cb39830"),
        "darwin-amd64": ("cloudflared-darwin-amd64.tgz", "cloudflared",
                         "0560c9ab7281ac3f746055323623ed23bc0405b6dab9400474020cba33a978da"),
    },
    endung=".trycloudflare.com",
    start_frist=40.0,         # so lange darf der Tunnel brauchen, bis der Code steht
    zugang_frist=15.0,        # so lange darf der Zugang des Gastes brauchen
    neustart_nach=20.0,       # ein abgebrochener Tunnel wird so viel spaeter neu versucht
    neustart_hoechstens=3,    # so oft hintereinander, dann bleibt es beim Fehler
    # Der Weg eines Gastes ohne cloudflared (seit 0.34.20, wszugang.py):
    # dasselbe, was `cloudflared access tcp` tut, in Python. Auf iOS darf
    # ein Spiel kein zweites Programm starten.
    ws_frist=12.0,            # so lange darf der Handschlag mit Cloudflare dauern
    ws_block=16384,           # so viele Bytes liest der Weg je Durchgang
)

# Touch-Steuerung (seit 0.34.20, dustfront/touch.py). An auf iOS, auf dem
# Rechner mit DUSTFRONT_TOUCH=1 zum Ausprobieren. Masse in Pixeln der
# Spielflaeche (640 x 360); auf einem iPhone ist ein Pixel davon etwa ein
# Punkt, und Apple empfiehlt Ziele ab 44 Punkten.
TOUCH = dict(
    stick_radius=34.0,        # so weit reicht ein Stick bis zum Anschlag
    tot=0.18,                 # Anteil des Radius, der noch nichts tut
    voll_ab=0.72,             # ab diesem Anteil laeuft man mit voller Kraft
    feuer_ab=0.55,            # der rechte Stick schiesst ab diesem Anteil
    ziel_nah=55.0,            # Abstand des Zielpunkts bei leicht gedruecktem Stick
    ziel_weit=190.0,          # ... und am Anschlag (Wurfweite einer Granate)
    links_bis=0.42,           # der linke Stick nimmt Finger bis hier (Anteil der Breite)
    knopf_radius=19.0,
    deckkraft=110,            # 0 bis 255, so sichtbar liegen Sticks und Knoepfe
    zwei_finger_rad=22.0,     # so weit schieben zwei Finger im Menue fuer eine Rad-Raste
    zoom_schritt=26.0,        # so viel weiter oder enger zwei Finger fuer eine Zoomstufe
    hotbar_zugabe=14,         # so viel hoeher als gezeichnet nimmt ein Hotbar-Platz Finger an
    # In Menues ein kleiner ESC-Knopf oben rechts: manche Schirme (Inventar,
    # Rundentafel) verlaesst man sonst nur mit der Escape-Taste.
    esc_mitte=(624, 14),
    esc_radius=11.0,
    # Die Knoepfe: Aktion (wie in K.TASTEN der Einstellungen), Aufschrift,
    # Mitte auf der Spielflaeche, Art. Oben rechts bleibt frei: dort steht
    # die Ebenenanzeige (E0, E1, E2) und darunter der Punktestand.
    # "halten" haelt die Taste, solange der Finger liegt (Dash ist im Buggy
    # die Handbremse, Nutzen hilft auf);
    # "druck" ist ein kurzer Druck; "waffe" schaltet zur naechsten Waffe;
    # "umschalten" haelt die Taste bis zum naechsten Druck (Zielen mit dem
    # Scharfschuetzengewehr).
    knoepfe=(
        ("pause",     "II",   (568, 22),  "druck"),
        ("ebenen",    "EBN",  (526, 22),  "druck"),
        ("inventar",  "INV",  (484, 22),  "druck"),       # nur allein (Testkarte)
        ("dash",      "DASH", (596, 232), "halten"),
        ("nachladen", "R",    (552, 268), "druck"),
        ("nutzen",    "E",    (596, 186), "halten"),
        ("heilen",    "+",    (508, 290), "druck"),
        ("nahkampf",  "F",    (552, 222), "druck"),
        ("waffe",     "WFF",  (596, 278), "waffe"),
        ("zweit",     "ZIEL", (552, 176), "umschalten"),
    ),
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
# teams   = zwei Mannschaften statt jeder fuer sich
# runden  = ein Leben je Runde, wer zuerst genug Runden hat, gewinnt
# zone    = ein Kreis in der Kartenmitte, der erobert wird
MODI = {
    "pvp":    dict(name="PVP",    gegner=False, beute=True,  revive=False,
                   teams=False, runden=False, zone=False,
                   hinweis="Jeder gegen jeden."),
    "pve":    dict(name="PVE",    gegner=True,  beute=False, revive=True,
                   teams=False, runden=False, zone=False,
                   hinweis="Alle zusammen gegen die Wellen."),
    "pvpve":  dict(name="PVPVE",  gegner=True,  beute=True,  revive=False,
                   teams=False, runden=False, zone=False,
                   hinweis="Wellen, und dabei jeder gegen jeden."),
    "team":   dict(name="TEAM",   gegner=False, beute=True,  revive=False,
                   teams=True,  runden=False, zone=False,
                   hinweis="Zwei Mannschaften, Abschüsse zählen für das Team."),
    "versus": dict(name="VERSUS", gegner=False, beute=True,  revive=True,
                   teams=True,  runden=True,  zone=False,
                   hinweis="Ein Leben je Runde. Mitspieler können aufhelfen."),
    "huegel": dict(name="HÜGEL", gegner=False, beute=True,  revive=False,
                   teams=True,  runden=False, zone=True,
                   hinweis="Haltet den Kreis in der Mitte."),
    # Keine Spielart, die man waehlt, sondern der Ort dazwischen: hier
    # landet man beim Aufmachen und nach jeder Runde (siehe LOBBY).
    # "gegner" steht an, weil es im Gehege Zombies gibt - Wellen gibt es
    # keine, das Gefecht fragt vorher nach `lobby`.
    "lobby":  dict(name="LOBBY",  gegner=True,  beute=True,  revive=False,
                   teams=False, runden=False, zone=False, lobby=True,
                   hinweis="Rumlaufen, üben, auf die Runde warten."),
}
MODUS_VORGABE = "pvp"

# Die Standardrunde (seit 0.32): womit eine frische Lobby plant, und was
# der Knopf STANDARDRUNDE auf der Rundentafel einstellt. Gedacht fuer die,
# die zum ersten Mal dabei sind - zwei Mannschaften, damit niemand allein
# gegen alle steht, zehn Minuten auf der richtigen Karte, und jeder hat
# alles, damit man nicht vorher ein Loadout bauen muss. Was hier fehlt,
# bekommt die Vorgabe aus regeln.py.
STANDARDRUNDE = dict(modus="team", karte="staubtal", ende_art="zeit",
                     ende_wert=600, loadouts="alles")

# Zwei Mannschaften. Mehr waeren eine Zeile hier und sonst nichts - die
# Zuteilung, die Faerbung und die Punktetafel rechnen alle ueber die Laenge
# dieser Listen.
# Mannschaften und ihre Farben.
#
# Eine Mannschaft ist nicht eine Farbe, sondern eine **Kombination** aus
# dreien - und die Figur selbst traegt sie, nicht nur ihr Name. Das ist der
# Unterschied, auf den es im Gefecht ankommt: Namen werden ausgeblendet,
# sobald jemand im Rauch steht oder zu weit weg ist, und auf einer anderen
# Ebene sieht man von einer Gestalt nur noch ihren Umriss. Wer dann erst
# ueberlegen muss, ob der da drueben zu ihm gehoert, hat schon verloren.
#
#   rumpf    die grosse Flaeche. Sie entscheidet auf Entfernung.
#   kante    Schatten und Umriss. Sie haelt die Figur vom Boden getrennt.
#   akzent   der helle Punkt am Kopf. Er sagt, wohin sie schaut.
#   hud      dieselbe Farbe fuer Schrift und Balken, kraeftiger
#   hud_dunkel  dieselbe fuer die fremde Mannschaft, gedaempft
#
# Die beiden Kombinationen sind bewusst gegensaetzlich gewaehlt: warm
# gegen kalt. Auf dem staubbraunen Boden trennen sich Orange und Tuerkis
# noch dann, wenn beide klein und halb verdeckt sind.
TEAMS = dict(
    namen=("ROT", "BLAU"),
    farben=(C_ORANGE, C_TEAL),          # bleibt fuer bestehenden Code
    dunkel=(C_RUST, C_TEAL_DK),
    kombi=(
        dict(name="ROT",
             rumpf=(176, 88, 54), kante=(72, 30, 20), akzent=(248, 182, 92),
             hud=C_ORANGE, hud_dunkel=C_RUST),
        dict(name="BLAU",
             rumpf=(82, 126, 146), kante=(24, 50, 62), akzent=(126, 230, 216),
             hud=C_TEAL, hud_dunkel=C_TEAL_DK),
    ),
)

# Der Kreis in der Kartenmitte, nach dem Vorbild der Hot Zone.
#
# Wer drin steht, laedt fuer sein Team. Stehen beide Mannschaften drin,
# zaehlt nur die Mehrheit - bei Gleichstand passiert nichts, und genau das
# macht den Kreis zum Ort, an dem man sich trifft, statt ihn abwechselnd
# leerzuraeumen.
ZONE = dict(
    ebene=0,                  # auf welcher Ebene der Kreis liegt
    radius=96.0,              # in Welt-Pixeln
    bis=100.0,                # so weit muss ein Team laden
    je_sekunde=7.0,           # Fortschritt je Sekunde bei Mehrheit
    je_kopf=2.5,              # Aufschlag je Kopf Mehrheit
    hoechstens=18.0,          # mehr laedt niemand je Sekunde
    verfall=1.2,              # so schnell sinkt der Stand, wenn keiner haelt
    # Seit 0.27 stellt der Gastgeber ein, wie lange man den Kreis halten
    # muss - in Sekunden, allein und ohne Gegenwehr gerechnet, weil das
    # die Zahl ist, die man sich vorstellen kann. Die Rate oben wird
    # daraus hochgerechnet, der Verfall im selben Verhaeltnis: sonst
    # waere bei drei Minuten Haltezeit ein kurzer Ausfall mehr wert als
    # eine Minute im Kreis. Die Vorgabe entspricht dem alten Wert (100
    # bei 7 je Sekunde, gut 14 Sekunden).
    haltezeit=15,
    haltezeiten=(10, 15, 20, 30, 45, 60, 90, 120, 180),
    verfall_an=True,          # sinkt der Stand, wenn keiner haelt?
    ring=3,                   # Dicke des Rings in Pixeln
    fuellung=34,              # Deckkraft der Flaeche
    puls=0.9,                 # Sekunden fuer einen Pulsschlag des Rings
    # Hat eine Karte mehrere Kreise, zieht der Kampf nach dieser Zeit
    # zum naechsten weiter. Drei Kreise **zugleich** waeren auf einer
    # sehr grossen Karte keine grosse Karte, sondern drei kleine: die
    # Mannschaften teilen sich auf und treffen sich nie. Einer, der
    # weiterzieht, haelt sie beisammen - man muss den Weg gehen.
    wechsel=75.0,
    # Seit 0.34.8: wo der Kreis liegt und wohin er als naechstes zieht.
    # Ist er nicht im Bild (oder auf einer anderen Ebene), zeigt ein
    # grosser Pfeil in seiner Farbe am Bildrand auf ihn. Im Kreis liegt
    # ein ">" auf dem Boden, das zum naechsten Kreis zeigt.
    randpfeil=15.0,           # halbe Laenge des Pfeils am Rand, Bildpixel
    randpfeil_abstand=22,     # so weit bleibt seine Mitte vom Bildrand weg
    weiter_groesse=0.40,      # das ">" im Kreis, Anteil am Radius
    weiter_dicke=9.0,         # seine Strichstaerke, Welt-Pixel
    weiter_deckkraft=150,
)

# Der Buggy (seit 0.34.9, dustfront/fahrzeug.py). Steht, wo die Karte ein
# F hat - auf STAUBTAL an der Tankstelle, in Westdorf und auf der Ranch.
# Seit 0.34.18 zerstoerbar (siehe unten); wer drin sitzt, bekommt von jedem Schaden nur einen Teil
# ab und wird nicht weggestossen. Gelenkt wird wie ein Auto: W/S Gas und
# Bremse (rueckwaerts), A/D lenken, Shift ist die Handbremse (seit
# 0.34.16). Geschossen wird am Steuer nicht.
#
# Seit 0.34.16 faehrt er mit Reifen, die seitlich nur so viel halten,
# wie sie koennen (Einspurmodell, siehe Buggy._physik): wird es mehr,
# rutscht er. Alle Kraefte hier je Masse, also Pixel je Sekunde im
# Quadrat. Abgestimmt in einer Simulation gegen diese Ziele: voll
# eingelenkt bei Hoechstfahrt bricht das Heck langsam aus und faengt sich
# (kein Dreher), die Handbremse dreht ihn um gut 150 Grad, ohne dass er
# stehen bleibt, und in mittelschnellen Kurven haelt er.
FAHRZEUG = dict(
    marke="F",                # Buchstabe in der Karte, wo einer steht
    hoechst=250.0,            # bis hierher zieht der Motor (wirklich: ~220, Luft)
    rueckwaerts=95.0,
    motor=420.0,              # Antrieb hinten, im Stand; nimmt mit dem Tempo ab
    bremse=520.0,             # wenn man gegen die Fahrtrichtung drueckt
    rollen=55.0,              # so schnell wird er ohne Gas langsamer
    luft=0.0011,              # Luftwiderstand, waechst mit dem Tempo im Quadrat
    lenk_max=32.0,            # Grad Radeinschlag im Stand
    lenk_abfall=0.5,          # bei Hoechstfahrt nur noch die Haelfte davon
    lenk_tempo=290.0,         # so schnell drehen die Raeder ein (Grad je Sekunde)
    achse_vorn=12.0,          # Abstand der Achsen von der Mitte (Pixel)
    achse_hinten=12.0,
    traegheit=230.0,          # wie traege er sich um sich selbst dreht
    griff_vorn=420.0,         # so viel Seitenkraft halten die Vorderraeder
    griff_hinten=300.0,       # die hinteren weniger: das Heck kommt zuerst
    steif=3600.0,             # Seitenkraft je Radiant Schraeglauf, bis zur Grenze
    schlupf_spitze=9.0,       # Grad Schraeglauf, ab dem ein Reifen rutscht
    gleiten=0.75,             # so viel Griff bleibt beim Rutschen
    handbremse_griff=0.45,    # so viel Seitengriff haben die blockierten Hinterraeder
    handbremse_bremse=110.0,
    antrieb_kreis=1.0,        # wie sehr Gas den Seitengriff hinten kostet
    durchdrehen=1.0,          # mehr Antrieb als Griff x das: die Raeder drehen durch
    gegenlenken=0.5,          # so viel des Driftwinkels lenkt er selbst gegen
    # Ohne Lenktaste: mehr Gegenlenken und weniger Heckschub - losgelassen
    # heisst "geradeaus", sonst haelt das Gas ihn ewig im Drift (siehe 0.34.16).
    gegenlenken_los=1.2,
    antrieb_kreis_los=0.25,
    drift_grenze=29.0,        # ab diesem Driftwinkel (Grad) faengt ihn die Stuetze
    drift_grenze_hb=69.0,     # mit Handbremse erst hier
    drift_stuetze=30000.0,    # wie kraeftig sie zurueckdreht
    v_min=55.0,               # unter diesem Tempo rechnet der Schraeglauf ruhiger
    spur_ab=0.25,             # ab so viel Rutschen bleiben Reifenspuren (0 bis 1)
    spur_abstand=2.5,         # Pixel zwischen zwei Spurpunkten
    quietschen_ab=0.5,        # ab so viel Rutschen quietschen die Reifen
    quietschen_pause=0.6,
    kreis=13.0,               # Radius der beiden Kreise, mit denen er anstoesst
    achse=14.0,               # Abstand der Kreise von seiner Mitte
    einsteigen=46.0,          # so nah muss man dran sein
    schaden_anteil=0.7,       # so viel von jedem Schaden kommt beim Fahrer an
    aufprall=0.25,            # so viel Tempo bleibt nach einem Aufprall (rueckwaerts)
    aufprall_hart=140.0,      # ab diesem Tempo rumst es (Ton, Ruckeln)
    staub_ab=80.0,            # ab diesem Tempo wirbelt er Staub auf
    staub_takt=0.05,
    staub_farbe=(206, 184, 142),  # heller als der Schrittstaub: er soll hinter dem Wagen stehen
    staub_groesse=3,
    hinweis_zeit=3.0,         # so lange steht "[E] AUSSTEIGEN" nach dem Einsteigen
    # Mit einem Stick (Touch, seit 0.34.22) faehrt er dorthin, wohin der
    # Stick zeigt, statt W/A/S/D nachzuahmen (fahrzeug.Buggy.stick_steuern).
    stick_tot=0.2,            # so wenig gedrueckt tut noch nichts
    stick_voll_lenken=40.0,   # Grad Abweichung, ab der voll eingeschlagen wird
    stick_wenden=110.0,       # Grad: weiter weg wird nur halb Gas gegeben, er wendet
    stick_zurueck=150.0,      # Grad: fast entgegen heisst bremsen, im Stand rueckwaerts
    stick_bremsen_ab=50.0,    # bis zu diesem Tempo faehrt er dann rueckwaerts
    # Seit 0.34.18 geht er kaputt (gemeldet: "autos sollen kaputt gehen
    # koennen und dann respawnen random auf der map"). Ein Sturmgewehr
    # braucht ein Magazin und mehr, eine Granate rund sechs Treffer.
    leben=420.0,
    explosion_radius=70.0,    # wenn er hochgeht
    explosion_schaden=70.0,   # in der Mitte, nach aussen weniger
    fahrer_schaden=55.0,      # was der Fahrer abbekommt (vor den 70 %)
    wrack_zeit=9.0,           # so lange brennt das Wrack, dann ist er weg
    neu_nach=12.0,            # und so viel spaeter steht irgendwo ein neuer
    neu_abstand=320.0,        # so weit von jedem Spieler weg (Weltpixel)
    rauch_takt=0.12,          # Qualm aus dem Wrack
    balken_breite=26,         # Lebensbalken ueber einem beschaedigten Wagen
)

# Bots (seit 0.34.18, dustfront/bots.py). Gemeldet: "optionale schwache
# bots ... die gleichmaessig die teams auffuellen und objectives machen und
# versuchen gegner zu eliminieren ... keinen aimbot bzw unfaire Vorteile".
#
# Ein Bot spielt mit genau dem, was ein Mensch hat: er schickt dieselbe
# Eingabe wie ein Gast (Laufrichtung, Mauszeiger, Feuertaste ...), und der
# Gastgeber rechnet sie wie jede andere. Er sieht nur, was in Sichtweite
# und nicht hinter einer Wand oder im Rauch steht, braucht eine Weile, bis
# er reagiert, schwenkt sein Fadenkreuz nicht schneller als eine Hand die
# Maus und zielt erst ungenau, dann besser - nie vorhaltend. Das Spiel
# streut seine Schuesse wie die aller anderen.
BOTS = dict(
    nummer_ab=100,            # Spielernummern ab hier sind Bots
    auffuellen=(0, 2, 4, 6, 8, 10, 12),   # Regel "bots": 0 = keine
    je_team_hoechstens=8,     # Regeln "bots_t0" ... und "bots_dazu" (seit 0.34.26)
    # Rufnamen wie die Operators in Militaer-Shootern (seit 0.34.34,
    # gemeldet: "eine LANGE Liste von Namen ... so Tags wie Ghost,
    # Chimera"). Nur allgemeine Woerter - Tiere, Wetter, Waffen, Mythen,
    # das Funkalphabet -, keine Namen bestimmter Spielfiguren. Hoechstens
    # zehn Buchstaben, damit "BOT-" davor ueber den Kopf passt.
    namen=(
           "GHOST", "CHIMERA", "REAPER", "VIPER", "WRAITH", "SPECTRE",
           "PHANTOM", "NOMAD", "RONIN", "HAVOC", "RAVEN", "FALCON", "HAWK",
           "EAGLE", "KESTREL", "HARRIER", "OSPREY", "CONDOR", "VULTURE",
           "SHRIKE", "MERLIN", "TALON", "RAPTOR", "COBRA", "MAMBA", "ADDER",
           "ASP", "PYTHON", "KRAIT", "SIDEWINDER", "RATTLER", "SCORPION",
           "TARANTULA", "HORNET", "WASP", "MANTIS", "LOCUST", "JACKAL",
           "HYENA", "COYOTE", "WOLF", "LOBO", "WARG", "DINGO", "BADGER",
           "WOLVERINE", "GRIZZLY", "KODIAK", "BISON", "RHINO", "MAMMOTH",
           "BULL", "RAM", "STAG", "LYNX", "OCELOT", "JAGUAR", "PANTHER",
           "PUMA", "COUGAR", "LEOPARD", "TIGER", "SABRE", "FANG", "CLAW",
           "ORCA", "SHARK", "MAKO", "BARRACUDA", "PIRANHA", "KRAKEN",
           "LEVIATHAN", "HYDRA", "GORGON", "MEDUSA", "CERBERUS", "MINOTAUR",
           "GRIFFIN", "BASILISK", "MANTICORE", "WYVERN", "DRAKE", "WYRM",
           "GOLEM", "TITAN", "ATLAS", "ARES", "ODIN", "THOR", "LOKI",
           "FENRIR", "VALKYRIE", "BANSHEE", "REVENANT", "SHADE", "SHADOW",
           "SPOOK", "ECHO", "CROW", "ROOK", "MAGPIE", "NIGHTJAR", "OWL",
           "KITE", "HERON", "ALBATROSS", "STORM", "THUNDER", "BLITZ",
           "TEMPEST", "CYCLONE", "TYPHOON", "MONSOON", "BLIZZARD",
           "AVALANCHE", "GLACIER", "FROST", "RIME", "SLEET", "HAIL", "EMBER",
           "CINDER", "ASH", "SOOT", "BLAZE", "INFERNO", "PYRO", "SCORCH",
           "FLARE", "NAPALM", "MAGMA", "FLINT", "STEEL", "IRON", "COBALT",
           "CHROME", "TITANIUM", "TUNGSTEN", "CARBON", "ONYX", "OBSIDIAN",
           "GRANITE", "BASALT", "QUARTZ", "SLATE", "GRAVEL", "RUST", "DUST",
           "SANDSTORM", "MIRAGE", "DUNE", "SIROCCO", "RAMPART", "BASTION",
           "BULWARK", "AEGIS", "SENTRY", "WARDEN", "WATCHMAN", "SENTINEL",
           "VANGUARD", "OUTRIDER", "RANGER", "SCOUT", "TRACKER", "HUNTER",
           "STALKER", "PROWLER", "LURKER", "DEADEYE", "BULLSEYE",
           "CROSSHAIR", "TRIGGER", "HAMMER", "ANVIL", "MALLET", "SLEDGE",
           "HATCHET", "CLEAVER", "MACHETE", "DAGGER", "STILETTO", "KUKRI",
           "BAYONET", "SPEAR", "LANCE", "PIKE", "HALBERD", "ARROW", "BOLT",
           "DART", "JAVELIN", "HARPOON", "GRAPPLE", "ANCHOR", "RUDDER",
           "BALLAST", "TORPEDO", "SONAR", "RADAR", "VECTOR", "NEXUS",
           "CIPHER", "ENIGMA", "RIDDLE", "PARADOX", "ZERO", "NULL", "VOID",
           "NADIR", "ZENITH", "APEX", "PRIME", "OMEGA", "ALPHA", "SIGMA",
           "DELTA", "GAMMA", "KAPPA", "THETA", "ZETA", "TANGO", "FOXTROT",
           "BRAVO", "ROMEO", "SIERRA", "VICTOR", "WHISKEY", "XRAY", "YANKEE",
           "ZULU", "KILO", "LIMA", "OSCAR", "HOTEL", "JULIET", "QUEBEC",
           "NOVEMBER", "CHARLIE", "DOZER", "BULLDOZER", "TANK", "BRICK",
           "BOULDER", "CRATER", "MORTAR", "SHRAPNEL", "CORDITE", "SULFUR",
           "NITRO", "THERMITE", "FUSE", "DETONATOR", "BREACHER", "SAPPER",
           "MEDIC", "PADRE", "DOC", "PATCH", "STITCH", "SPLINT", "MAVERICK",
           "ROGUE", "OUTLAW", "BANDIT", "RENEGADE", "MARAUDER", "RAIDER",
           "CORSAIR", "BUCCANEER", "VIKING", "SPARTAN", "TROJAN",
           "CENTURION", "LEGION", "GLADIATOR", "SAMURAI", "SHOGUN",
           "SHINOBI", "KUNAI", "KATANA", "OUTCAST", "EXILE", "PILGRIM",
           "DRIFTER", "WANDERER", "VAGABOND", "HERMIT", "MONK", "PREACHER",
           "DEACON", "BISHOP", "KNIGHT", "JOKER", "JESTER", "ACE", "DEUCE",
           "SPADE", "CHAOS", "ANARCHY", "MAYHEM", "RIOT", "FURY", "WRATH",
           "RAGE", "SPITE", "MALICE", "VENOM", "TOXIN", "PLAGUE", "BLIGHT",
           "HUSK", "GRIM", "DIRGE", "REQUIEM", "ELEGY", "OMEN", "PROPHET",
           "ORACLE", "SAGE", "WARLOCK", "HEX", "SIGIL", "RUNE", "TOTEM",
           "RELIC", "NEON", "LASER", "PLASMA", "ION", "PHOTON", "QUANTUM",
           "FUSION", "ISOTOPE", "URANIUM", "RADIUM", "XENON", "ARGON",
           "KRYPTON", "OZONE", "STATIC", "GLITCH", "BYTE", "PIXEL", "VERTEX",
           "CIRCUIT", "DIODE", "SPARK", "VOLT", "DYNAMO", "TURBINE",
           "PISTON", "GEAR", "COG", "RIVET", "FORGE", "FOUNDRY", "CRUCIBLE",
           "POLARIS", "SIRIUS", "VEGA", "RIGEL", "ORION", "NOVA", "PULSAR",
           "QUASAR", "COMET", "METEOR", "ECLIPSE", "AURORA", "NEBULA",
           "GRAVITY", "HOLLOW", "WIDOW", "SPIDER", "HOUND", "MASTIFF",
           "MONGOOSE", "SKULL", "BONES"),
    takt=0.1,                 # so oft sieht und entscheidet er neu (s)
    sicht=330.0,              # so weit sieht er (halbe Bildbreite ist 320)
    reaktion=(0.45, 0.85),    # bis zum ersten Schuss auf ein neues Ziel (s)
    reaktion_hinten=0.35,     # dazu, wenn es von hinten kommt
    dreh=230.0,               # so schnell schwenkt er das Fadenkreuz (Grad/s)
    fehler_start=48.0,        # Zielfehler beim ersten Sehen, auf 250 px (px)
    fehler_min=13.0,          # bestenfalls, nach langem Verfolgen
    fehler_abbau=1.6,         # Sekunden, bis er sich deutlich gefangen hat
    feuerstoss=(0.25, 0.6),   # so lange haelt er den Abzug ...
    feuerpause=(0.3, 0.65),   # ... und so lange laesst er los
    # Je Waffe (seit 0.34.38): (Stoss, Pause, so oft steht er still).
    # Gemeldet: "das MG feuert gerade nie laenger als ein paar Schuesse".
    # Kein Wunder - im Dauerfeuer braucht es 1,15 s Anlauf, der Stoss war
    # hoechstens 0,6 s lang. Jetzt haelt er es, wie man ein MG haelt.
    feuer=dict(lmg=((1.8, 3.4), (0.35, 0.7), 1.0),
               sturm=((0.35, 0.9), (0.25, 0.55), 0.5)),
    dauerfeuer=1.7,           # x Stoss, wenn er auf eine Gruppe haelt
    flaeche_weite=95.0,       # so nah beieinander sind Gegner eine Gruppe (px)
    flaeche_schwenk=1.6,      # so schnell schwenkt er beim Flaechenfeuer hin und her (1/s)
    still_beim_schiessen=0.45,  # so oft bleibt er beim Schiessen stehen
    gehoer=460.0,             # Schuesse in dieser Entfernung hoert er
    gehoer_knall=820.0,       # Explosionen (seit 0.34.38)
    schritte=(150.0, 70.0),   # Schritte eines Gegners hoert er so weit: rennt er / geht er
    schritte_tempo=(95.0 * BEWEGUNG["lauf"], 25.0 * BEWEGUNG["lauf"]),   # ab so viel Tempo rennt / geht einer (px/s)
    schritte_wand=0.6,        # durch eine Wand nur so weit davon
    lagebild=6.0,             # so lange behaelt er einen gehoerten Ort im Kopf (s)
    granate_sieht=260.0,      # eine liegende Granate bemerkt er so weit (seit 0.34.38)
    # Aus der Deckung schiessen (seit 0.34.43): drin warten, herauslehnen,
    # ein Feuerstoss, zurueck.
    lehnen_versatz=(16.0, 22.0, 28.0, 36.0),   # so weit neben der Deckung lehnt er sich heraus
    lehnen_weite=48.0,        # so weit weg von seiner Deckung gilt er noch als darin
    lehnen_warten=(0.6, 1.5),  # so lange bleibt er drin, mal (1 + Stress) (s)
    schutz_warten=0.35,       # x lehnen_warten beim Feuerschutz fuer einen Retter (0.34.54)
    schutz_pause=0.4,         # x Pause zwischen zwei Stoessen dabei
    schutz_fremd=120.0,       # ... und so weit weg von den eigenen Leuten (px)
    schutz_hoeren=2.0,        # so frisch muss ein gehoerter Schuss sein, damit er dorthin niederhaelt (s)
    blick_gefahr_nah=30.0,    # naeher als so viel: nicht zur Gefahr schauen, der Winkel springt sonst (px, 0.34.55)
    lauf_blick_ruhe=0.4,      # so lange muss er in eine Richtung gehen, bevor er dorthin schaut (s, 0.34.55)
    lauf_blick_winkel=35.0,   # ... und so viel darf sie dabei schwanken (Grad)
    blick_linie_weit=110.0,   # ohne Kontakt in Richtung der Linie schauen, solange er nicht weiter davon weg geht (Grad)
    rauch_laufen=3.0,         # so lange geht er hoechstens zu einer Stelle, von der er Rauch werfen kann (s, 0.34.55)
    rauch_pause=8.0,          # ... findet er keine, laesst er den Rauch so lange (s)
    lehnen_raus=2.2,          # laenger bleibt er nicht draussen (s)
    ecke_radien=(14.0, 28.0, 42.0, 56.0, 70.0),   # Panik in Deckung: so weit sucht er eine Ecke
    # Volle Deckung vor halber (seit 0.34.46), in Pixeln Weg, die sie wert ist:
    deckung_wand=70.0,        # eine Mauer statt eines Fasses
    deckung_flanke_winkel=25.0,   # so weit seitlich darf der Gegner stehen ...
    deckung_flanke=80.0,      # ... sonst kostet es das, je Seite
    # Mehr als eine offene Flanke: am Mauerende sitzt er lieber als in der
    # Mitte, von wo aus er nicht schiessen kann.
    deckung_ecke=90.0,        # von hier aus kann er sich herauslehnen (Mauerende)
    deckung_belegt=20.0,      # so nah sitzt schon ein Kamerad ...
    deckung_belegt_strafe=60.0,   # ... und das kostet es
    deckung_trupp_weg=1.5,    # je Pixel weiter weg vom Trupp als K.TRUPP["zusammen"] (0.34.50)
    # Nie von der Flanke (seit 0.34.50):
    schuetze_merken=3.0,      # so lange weiss er, wer ihn getroffen hat (s)
    schuetze_bonus=260.0,     # so viel lieber nimmt er den, der auf ihn schiesst (px)
    flanke_spanne=80.0,       # stehen die Gegner weiter auseinander (Grad), ist er flankiert
    umstell_radien=(40.0, 80.0, 120.0, 160.0),   # so weit sucht er einen Platz, von dem aus alle vor ihm sind
    vorn_frei=56.0,           # so weit vor ihm muss frei sein, sonst kein Schuss, kein Wurf
    kamerad_linie=16.0,       # so nah an der Schusslinie steht ein Kamerad: nicht schiessen (px)
    # Seit 0.34.48: in Deckung ist nur, wer dicht dahinter steht.
    deckung_dicht=40.0,       # so nah vor ihm muss das Hindernis stehen
    deckung_mindest=0.6,      # x Wunschabstand der Waffe: naeher am Gegner ist eine Deckung zu nah ...
    deckung_zu_nah=1.5,       # ... und kostet je Pixel so viel
    wechsel_weg=(60.0, 300.0, 12.0),   # Panik: von - bis - in Schritten sucht er eine bessere Deckung
    wechsel_weiter=40.0,      # ... die so viel weiter vom Gegner weg ist
    granate_abstand=30.0,     # so weit ueber ihren Radius hinaus rennt er
    gedaechtnis=4.0,          # so lange sucht er dort, wo er einen zuletzt sah
    erinnerung=20.0,          # so lange weiss er noch, wo einer stand - fuers Bergen (0.34.50)
    wunschabstand=dict(repetierer=230.0, sturm=200.0, lmg=240.0,
                       schrot=105.0, scharf=320.0),
    # Wer ein MG hat, schiesst damit (seit 0.34.38): so viele Pixel
    # Abstand nimmt er hin, bevor er lieber die andere Waffe nimmt. Vorher
    # nahm der MG-Schuetze auf mittlere Weite das Sturmgewehr.
    waffe_vorzug=dict(lmg=90.0),
    reichweite=dict(repetierer=330.0, sturm=320.0, lmg=330.0,
                    schrot=185.0, scharf=330.0),
    nahkampf_ab=34.0,         # so nah, dann schlaegt er mit dem Brecheisen
    wurf_pause=(10.0, 18.0),  # zwischen zwei Wuerfen
    wurf_weite=(90.0, 230.0),
    wurf_winkel=8.0,          # so genau muss er zum Ziel schauen, bevor er wirft (Grad, 0.34.52)
    wurf_warten=1.0,          # ... hoechstens so lange wartet er darauf (s)
    wurf_breite=6.0,          # so viel Platz braucht eine Granate neben ihrer Bahn (px, 0.34.52)
    rauch_vor=18.0,           # Rauch liegt so weit vor dem Liegenden (zum Gegner hin, seit 0.34.46)
    # Seit 0.34.26: eine Granate je Leben, keine Medkits, nichts aufheben,
    # immer begrenzte Munition - ist alles weg, geht er in den Nahkampf.
    wurf_arten=("granate",),  # daraus wird seine eine Wurfwaffe gewuerfelt
    wuerfe_je_leben=1,
    vorrat_anteil=1.0,        # x der Reserve aus MUNITION["vorrat"]
    # Deckung (seit 0.34.26): zum Nachladen immer, angeschlagen kurz.
    deckung_leben=40.0,       # darunter, und gerade getroffen: weg aus der Linie
    deckung_zeit=2.5,         # so lange bleibt er dann versteckt ...
    deckung_pause=7.0,        # ... und so lange danach nicht wieder
    deckung_radien=(40.0, 70.0, 105.0, 150.0, 200.0),  # so weit sucht er, naechste zuerst
    # ── Funk (seit 0.34.27, bottaktik.py). Kurz vor einer Aktion sagt der
    # Bot an, was er vorhat - als Untertitel ueber ihm, mit Mannschaften
    # nur fuer die eigene. Je Anlass mehrere Saetze, damit es nicht wie
    # ein Automat klingt.
    funk=dict(
        kontakt=("KONTAKT!", "FEIND GESICHTET!", "DA VORNE!"),
        flanke=("ICH FLANKIERE!", "GEHE AUSSEN HERUM!", "NEHME DIE SEITE!"),
        druck=("HALTE IHN UNTEN!", "NIEDERHALTEN!", "BLEIB IN DECKUNG, DU!"),
        feuerschutz=("FEUERSCHUTZ!", "ICH DECKE DICH!", "GEH, ICH HAB IHN!"),
        nachladen=("NACHLADEN!", "LADE NACH - DECKT MICH!"),
        granate=("GRANATE!", "GRANATE RAUS!"),
        sammeln=("SAMMELN AM EINGANG!", "STAPELN - AUF MEIN ZEICHEN!"),
        bereit=("BEREIT!", "IN POSITION!"),
        rein=("REIN, REIN, REIN!", "LOS, STÜRMEN!"),
        getroffen=("BIN GETROFFEN!", "MUSS IN DECKUNG!"),
        beschuss=("UNTER BESCHUSS!", "KOPF RUNTER!"),
        leer=("KEINE MUNITION!", "NUR NOCH DAS EISEN!"),
        helfen=("ICH HOLE DICH!", "HALT DURCH!"),
        kreis=("ZUM KREIS!", "NEHMT DEN KREIS!"),
        # Seit 0.34.38: was er sagt, wenn das Innenleben ueberhand nimmt.
        granate_weg=("GRANATE! WEG HIER!", "IN DECKUNG!"),
        panik=("ICH BIN RAUS!", "WEG HIER!", "DAS SIND ZU VIELE!"),
        uebermut=("ICH HAB IHN!", "DER IST FÄLLIG!", "HINTERHER!"),
        gruppe=("DA SIND MEHRERE!", "GANZE GRUPPE!", "HALTET DRAUF!"),
        gehoert=("DA WAR WAS!", "HÖRT IHR DAS?"),
    ),
    # Seit 0.34.43 aus (gemeldet: "die Callouts gerade einmal rausnehmen,
    # die brauchen wir gerade nicht"). Gesprochen wird trotzdem - wer im
    # Trupp etwas sagt, teilt sein Wissen -, nur steht es nicht mehr ueber
    # dem Kopf. True holt die Untertitel zurueck.
    callouts=False,
    funk_dauer=1.9,           # so lange steht ein Spruch (s)
    funk_abstand=2.2,         # so lange schweigt er danach mindestens
    funk_wiederholen=7.0,     # derselbe Anlass erst wieder nach so langer Zeit
    funk_fuer_alle=False,     # True: auch die andere Mannschaft liest mit
    funk_laenge=32,           # laengster Spruch, den der Gast annimmt
    # ── Taktik (seit 0.34.27, bottaktik.py)
    flanke_radien=(130.0, 175.0, 220.0),  # so weit vom Gegner sucht er die Flanke
    flanke_zeit=7.0,          # laenger dauert kein Flankieren
    flanke_pause=8.0,         # danach so lange kein neues
    druck_zeit=2.6,           # so lange haelt er einen nieder
    druck_pause=3.5,
    druck_versatz=(14.0, 22.0, 30.0),  # neben der Deckung, auf die er schiesst
    druck_merken=0.25,        # so lange gilt die Stelle, ohne neu zu suchen (s, seit 0.34.52)
    druck_rest=0.35,          # niederhalten nur, solange mehr als so viel Munition bleibt
    gedaechtnis_taktik=3.5,   # so frisch muss ein gesehener Gegner sein
    feuerschutz_weite=230.0,  # so nah an einem Kameraden, der Schutz braucht
    feuerschutz_bonus=150.0,  # so viel lieber nimmt er dann diesen Gegner
    unterdrueckt_weite=26.0,  # so knapp muss eine Kugel an ihm vorbei
    unterdrueckt_zeit=1.4,    # so lange bleibt er dann unten und zielt schlechter
    unterdrueckt_fehler=1.8,  # x Zielfehler, solange er unterdrueckt ist
    sturm_takt=0.5,           # so oft planen die Bots einer Mannschaft gemeinsam
    sturm_weite=320.0,        # so nah muessen die Bots beieinander sein
    sturm_ueberzahl=1.5,      # so viel mehr muessen sie sein als die Gegner, die sie kennen
    sturm_sammel=(70.0, 110.0, 150.0),  # Sammelpunkt so weit vom Ziel, ausser Sicht
    sturm_sammeln_zeit=7.0,   # laenger wird nicht gewartet
    sturm_rein_zeit=4.5,      # so lange stuermen sie
    sturm_pause=12.0,         # danach so lange kein neuer Sturm in der Mannschaft
    stockt_nach=1.2,          # so lange kaum vom Fleck: er weicht aus
    verwalten_takt=1.0,       # so oft wird nachgezaehlt, ob Bots fehlen
)

# Der Testmodus (seit 0.34.28, testmodus.py): aus dem Hauptmenue, zum
# schnellen Ausprobieren neuer Sachen. Man fliegt als Beobachter, den
# nichts in der Welt wahrnimmt, und steuert alles ueber den Ziffernblock.
# Gemeldet: "ein temporaerer Testmodus, wo ich neue Features schneller
# testen kann ... alles mit Fokus auf Effizienz und Kontrolle statt auf
# Verstaendlichkeit und Gefuehl." Nicht auf iOS (kein Ziffernblock).
TESTMODUS = dict(
    port=50620,               # lauscht nur lokal, ab hier der erste freie Port
    flug=(500.0, 1100.0, 2400.0),   # Flugtempo des Beobachters (px/s), waehlbar
    turbo=3.0,                # x Flugtempo mit gehaltener Umschalttaste
    zeitfaktoren=(0.1, 0.25, 0.5, 1.0, 2.0, 4.0),
    einzelschritt=12,         # so viele Rechenschritte macht EIN SCHRITT (1/10 s)
    hoechstens_schritte=8,    # mehr Rechenschritte je Bild auch im Zeitraffer nicht
    anzahlen=(1, 2, 3, 4, 5, 8, 10, 15, 20, 30, 50),
    streuungen=(0, 16, 32, 64, 128, 256),
    leben=(1.0, 0.5, 0.25, 0.1, 2.0, 5.0, 10.0),
    greifen=40.0,             # so nah am Mauszeiger wird eine Figur genommen/geloescht
    figur_ab=300,             # Spielernummern der gespawnten Puppen und Figuren
    aktion_ausweichen=3,      # saubere Ansicht: so oft rueckt eine Aktion hoch, wenn es eng ist
    # Funkwellen (seit 0.34.43, seit 0.34.46 rot, klein und am Boden unter
    # dem Funker - gemeldet: "auf rot und deutlich kleiner ... als Teil des
    # Bots selber erkennbar ... mehr zum Design passend").
    # Seit 0.34.50 etwas groesser (war bis 26): "etwas groesser darf der
    # Funk schon sein".
    welle_takt=0.45,          # so oft geht ein neuer Ring los (s)
    welle_tempo=40.0,         # so schnell laeuft er nach aussen (px/s)
    welle_start=11.0,         # hier beginnt er (knapp ausserhalb der Figur)
    welle_weite=40.0,         # so weit, dann ist er weg
    empfang_zeigen=0.6,       # so lange laeuft beim Empfaenger ein Ring nach innen (s)
    welle_farben=((255, 72, 56), (226, 44, 40), (168, 26, 30)),   # innen hell, aussen tief
    welle_striche=6,          # so viele Striche hat ein Ring (seit 0.34.48)
    welle_dreh=1.6,           # so schnell drehen sie sich (Bogenmass je Sekunde)
)

# Zielorientierte KI (seit 0.34.29, goap.py, bot_goap.py, Daten in wesen/).
# Was spaeter noch kommt, steht in docs/KI.md.
GOAP = dict(
    tiefe=6,                  # hoechstens so viele Aktionen in einem Plan
    knoten=400,               # hoechstens so viele Zustaende je Planung
    neu_planen=0.6,           # spaetestens nach so vielen Sekunden neu planen (s)
    takt=0.1,                 # so oft denkt ein Wesen (s), dazwischen handelt es
    vorsprung=8.0,            # das laufende Ziel gewinnt bei Gleichstand um so viel
    sperre=2.0,               # eine gescheiterte Aktion so lange nicht einplanen (s)
    protokoll=40,             # so viele Zeilen merkt sich ein Gehirn (Testmodus)
    arten=("klassisch", "goap"),   # die Regeln BOT-KI und GEGNER-KI
    spezies_bot="mp_bot",     # welche Spezies aus wesen/ ein Bot des Mehrspielers ist
    # Gegner (seit 0.34.30, gegner_goap.py)
    gegner_angeschlagen=0.5,  # unter so viel seines Lebens ist ein Gegner angeschlagen
    wandern_weite=160.0,      # so weit schlurft ein Zombie ohne Ziel auf einmal (px)
    wandern_tempo=0.45,       # ... mit so viel seines Tempos
    # Dual Utility (seit 0.34.38): bei voller Unschaerfe kommt noch in die
    # Wahl, was so viel unter dem besten Ziel liegt (0.3 = 30 Prozent).
    unschaerfe_weite=0.3,
)

# Das Innenleben der Bots (seit 0.34.38, innenleben.py): Stress und
# Zuversicht, Panik und Schreck. Was ein Zustand bewirkt, steht als Ziel in
# wesen/bots.txt; hier stehen nur die Zahlen.
MORAL = dict(
    # So viel Stress (0 bis 1) bringt ein Ereignis, bevor Disziplin und
    # Drill daempfen. Negativ: es beruhigt.
    stress=dict(vorbei=0.07,       # eine Kugel knapp vorbei
                getroffen=0.16,    # selbst getroffen
                angeschlagen=0.08,  # ... und dabei schon angeschlagen, dazu
                seite=0.10,        # ... von der Seite oder von hinten, dazu
                kamerad=0.22,      # ein Kamerad faellt in seiner Naehe
                granate=0.30,      # eine Granate liegt neben ihm
                gehoert=0.03,      # ein Gegner ist zu hoeren, den er nicht sieht
                abschuss=-0.14),   # er (oder seine Seite in der Naehe) hat einen erwischt
    # So lange zaehlt dasselbe Ereignis nicht noch einmal (s) - sonst waere
    # eine MG-Garbe, die vorbeigeht, zwanzig Ereignisse.
    sperren=dict(vorbei=0.3, gehoert=1.5, granate=0.8),
    disziplin_daempft=0.45,   # bei Disziplin 1 kommt so viel weniger an
    drill_daempft=0.35,       # bei Drill 1 so viel weniger
    abbau=0.09,               # so viel Stress je Sekunde geht von selbst zurueck
    abbau_deckung=0.2,        # ... in Deckung
    drill_abbau=0.8,          # bei Drill 1 geht er so viel schneller zurueck (x 1,8)
    panik_ab=0.8,             # ab so viel Stress (plus Mut) bricht Panik aus
    panik_mut=0.15,
    panik_verzweifelt=0.2,    # weniger, wenn die eigene Seite klar verliert
    panik_dauer=(2.5, 4.5),   # so lange rennt er (s), vor Drill und Disziplin
    panik_drill=0.6,          # Drill 1 macht sie so viel kuerzer
    schreck_sprung=0.2,       # so viel Stress auf einmal: er erschrickt
    schreck=(0.25, 0.55),     # ... und tut so lange nichts (s)
    bedenkzeit=(0.12, 0.4),   # bevor er ein neues Ziel angeht (s), vor dem Stress
    eingeschossen_ab=1.0,     # so lange feuert er schon: er ist eingeschossen (s)
    eingeschossen_pause=1.2,  # so lange nicht gefeuert, und es ist vorbei
    # Zuversicht wie in Days Gone: Verhaeltnis der Staerken, fuenf Stufen.
    zuversicht_stufen=(0.45, 0.8, 1.45, 2.4),
    zuversicht_namen=("PANISCH", "BESORGT", "NEUTRAL", "ZUVERSICHTLICH", "HELDENHAFT"),
    zuversicht_faktor=(0.45, 0.75, 1.0, 1.2, 1.4),   # so zaehlt er fuer seine Seite
    zuversicht_weite=420.0,   # Kameraden so nah zaehlen mit
    staerke_waffe=dict(lmg=1.35, sturm=1.1, repetierer=1.0, schrot=0.95, scharf=1.1),
    staerke_unterdrueckt=0.6,  # niedergehalten zaehlt er so viel
    verlust_abbau=45.0,       # Abschuesse und Verluste klingen so langsam ab (s)
    # Umschauen (seit 0.34.38): ab und zu schaut er weg vom Ziel - zu einem
    # Geraeusch oder zur Seite. Unter Stress seltener (Tunnelblick).
    umschau=(2.5, 5.5),       # so oft (s)
    umschau_dauer=(0.3, 0.6),
    umschau_winkel=(70.0, 110.0),  # ... so weit neben die Gefahr (Grad; bis 0.34.54: 80 bis 150)
)

# Trupps (seit 0.34.39, trupp.py): was ein Trupp gemeinsam weiss, wo jeder
# steht, und der Funk zwischen den Anfuehrern. Bisher nur im Testmodus
# (Spawner TRUPP).
TRUPP = dict(
    takt=0.25,                # so oft frischt ein Trupp auf, was er weiss (s)
    sprech_weite=260.0,       # so weit hoert man einen, der spricht (px)
    gedaechtnis=6.0,          # so lange behaelt der Trupp einen gemeldeten Gegner (s)
    unterzahl=1.5,            # so viele Gegner je Mann: unterlegen
    zustand_halten=2.0,       # so lange bleibt ein Zustand mindestens (s)
    halten_weite=260.0,       # so nah an der Stellung: sie ist im Ruecken
    niemandsland=130.0,       # so tief ist der Streifen vor dem Gegner, den keiner betritt
    rand=40.0,                # so viel breiter als der Gegner ist die Front je Seite
    # Weit genug, dass eine Granate (Radius 78) nicht drei auf einmal
    # trifft - in den ersten Aufnahmen standen sie zu eng.
    bahn_min=72.0,            # so breit ist eine Bahn mindestens
    front_schwelle=40.0,      # erst ab so viel Weg ...
    front_winkel=20.0,        # ... oder so viel Drehung bewegt sich die Front
    fuehrer_tiefe=70.0,       # so viel weiter hinten steht der Anfuehrer
    geschwaecht_tiefe=80.0,   # so viel weiter hinten ein Geschwaechter (0.34.40)
    linie_abstand=68.0,       # ohne Kontakt: so weit auseinander in der Linie
    linie_vor=30.0,           # ... und so weit vor dem Anfuehrer
    linie_ruhe=25.0,          # ... ihre Richtung folgt erst ab so viel Grad Unterschied (0.34.55)
    linie_dreh=20.0,          # ... und dann hoechstens so viel Grad je Takt
    linie_warten=2.6,         # x Abstand: so weit zurueck, und der Anfuehrer wartet
    stellung_weite=28.0,      # so nah an seiner Stellung: er steht, wo er soll
    # Seit 0.34.43: steht eine Stellung im Freien, sucht der Trupp so weit
    # herum Deckung gegen den Gegner ("Bots blieben im Freien stehen").
    deckung_ringe=(20.0, 40.0, 64.0),
    deckung_nah=36.0,         # so nah muss das Hindernis vor ihm sein
    # Seit 0.34.52 rueckt eine gedeckte Stellung bis an das Hindernis heran,
    # in Schritten von `anruecken_schritt` px, und dort steht er genau
    # (`deckung_genau` px) - gemeldet: sie "haben sich wieder in einem
    # gewissen Abstand zu den Deckungen gestellt".
    anruecken_schritt=3.0,
    deckung_genau=6.0,
    flanke_vor=20.0,
    flanke_ab=90.0,           # so nah an der Linie, und die Aeusseren flankieren
    welle_zeit=2.6,           # so lange dauert eine Welle (s)
    welle_weite=85.0,         # so weit zieht eine Welle
    # Seit 0.34.50: wer im Trupp ist, bleibt bei ihm - auch in Panik.
    zusammen=170.0,           # so weit von der Mitte der anderen sucht er Deckung
    abschnitt_luecke=60.0,    # so viele Grad zwischen zwei Gegnern: zwei Gruppen, die Front knickt
    abschnitt_vor=90.0,       # so weit vor der Mitte steht jeder Abschnitt (war 40: man sah den Knick kaum)
    abschnitt_bonus=150.0,    # so viel lieber nimmt einer die Gegner in seinem Abschnitt (px)
    abschnitt_winkel=70.0,    # so weit neben seiner Blickrichtung ist es noch sein Abschnitt (Grad, 0.34.51)
    # Seit 0.34.52 schiesst er aus seinem Abschnitt heraus nur auf den, der
    # ihn beschiesst oder so nah ist (px) - sonst hielten alle auf die
    # naechste Gruppe, und die andere Seite war offen (gemeldet).
    abschnitt_nah=140.0,
    flucht_hinter=60.0,       # in Panik flieht er so weit hinter die Mitte der anderen
    fuehrer_bonus=120.0,      # so viel lieber nimmt man Gegner nahe dem Anfuehrer
    buendeln_bonus=40.0,      # ... und die, auf die ein Kamerad schon schiesst
    bergung_bonus=300.0,      # ... und waehrend einer geborgen wird, wer Retter oder Liegenden treffen kann (0.34.54)
    fuehrer_schutz=230.0,     # so nah am Anfuehrer: ein Gegner bedroht ihn
    # Funk zwischen den Anfuehrern.
    # Seit 0.34.48 viel laenger (war 2,2), und erst zieht er sich dafuer
    # zurueck - gemeldet: "Funken geht viel zu schnell. Der Offizier soll
    # sich eher wirklich zurueckziehen dafuer, so dass es moeglich ist, ein
    # Team zu ueberraschen, sodass es nicht funken kann."
    funk_dauer=6.0,           # so lange dauert ein Spruch (s) - er steht dabei
    funk_abstand=300.0,       # so weit weg von jedem bekannten Gegner funkt er
    funk_weg_radien=(60.0, 110.0, 160.0, 220.0),   # so weit sucht er dafuer einen Platz
    funk_weg_zeit=8.0,        # laenger geht er nicht, dann funkt er, wo er ist
    funk_stoer=150.0,         # sieht er einen Gegner so nah (oder schiesst einer auf ihn), bricht der Spruch ab
    funk_gedaechtnis=12,      # so viele Sprueche zeigt der Testmodus
    melden_pause=8.0,         # so lange nach einer Meldung keine neue (s)
    hilferuf_gilt=20.0,       # so lange gilt ein Hilferuf (s)
    helfen_bis_feinde=2,      # mit hoechstens so vielen eigenen Gegnern hilft man
    helfen_weite=1800.0,      # weiter weg hilft keiner
    hilfe_hoechstens=45.0,    # laenger ist niemand unterwegs zu einem anderen (s)
    angekommen=160.0,         # so nah dran: angekommen
    namen=("ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT", "GOLF", "HOTEL"),
    groessen=(2, 3, 4, 5, 6, 8),
    # Gemeldet: "Die Squad-Leader sollen nur einen Repetierer und eine
    # Rauchgranate haben."
    fuehrer_loadout=dict(waffen=["repetierer"], wuerfe=["rauch"]),
    # GEMISCHT im Spawner: die ersten Leute bekommen diese Waffen, der Rest
    # das Sturmgewehr - damit jede Rolle (8.4) einmal da ist.
    mischung=("lmg", "schrot", "scharf"),
    # Seit 0.34.41: Rundumverteidigung (Igel) und Engstellen.
    igel_ab=3,                # so viele Gegner muessen es mindestens sein
    igel_luecke=160.0,        # groesste Luecke zwischen ihren Richtungen: darunter umzingelt (Grad)
    igel_luecke_raus=220.0,   # ... und erst ab so viel ist man es nicht mehr
    igel_weite=420.0,         # Gegner so nah zaehlen
    igel_suche=170.0,         # so weit um den Trupp sucht er einen Platz zum Einigeln
    igel_raster=24.0,
    igel_platz_frei=22.0,     # so viel Platz muss dort sein
    igel_deckung=(34.0, 52.0, 70.0),   # so nah muss Deckung um den Platz stehen
    igel_feind_abstand=140.0,  # naeher an einem Gegner kein Platz zum Einigeln
    igel_ring=26.0,           # Ring um den Platz: so viel ...
    igel_ring_je=6.0,         # ... und so viel mehr je Mann
    platz_gilt=6.0,           # so lange gilt ein gefundener Platz, dann neu suchen (s)
    horde_ab=4,               # so viele Nahkaempfer (Zombies): eine Horde
    enge_suche=340.0,         # so weit Richtung Horde sucht er eine Engstelle
    enge_raster=24.0,
    enge_breite=84.0,         # schmaler als das: eine Engstelle (px)
    enge_offen=110.0,         # so weit muss es entlang des Durchgangs offen sein
    enge_abstand=120.0,       # so weit hinter der Engstelle halten sie
    enge_abstand_quer=40.0,   # so weit nebeneinander im Bogen
)

# Die Lobby: wo man beim Aufmachen landet und nach jeder Runde.
#
# Drei Bereiche, in der Kartendatei als Rechtecke im Kopf eingetragen:
# PVP (hier trifft jeder jeden), STAND (der Schiessstand mit Puppen) und
# PVE (das Gehege mit Zombies). Ausserhalb dieser Bereiche tut niemandem
# etwas weh - man soll dort stehen und reden koennen, waehrend der
# Gastgeber die naechste Runde einstellt. Nichts aus der Lobby wird
# gebucht: keine Runde, kein Abschuss, keine Statistik.
LOBBY = dict(
    karte="lobby",
    wieder_nach=1.5,          # so schnell steht man in der Lobby wieder auf
    puppe_heilt=2.5,          # Sekunden ohne Treffer, dann ist sie wieder voll
    gehege_grund=3,           # so viele Zombies im Gehege, wenn einer drin ist
    gehege_je_spieler=2,      # und so viele mehr je weiterem
    gehege_hoechstens=10,
    gehege_takt=1.4,          # Sekunden zwischen zwei neuen
    gehege_arten=("laeufer", "laeufer", "renner", "brecher", "speier",
                  "blaeher"),
    weiter_nach=12.0,         # so lange steht die Siegtafel vor der naechsten
    plan_hoechstens=12,       # mehr Runden plant niemand
)


# Versus: ein Leben je Runde, wie in einem Rundenschuetzen.
# Versus: ein Leben je Runde.
#
# Seit 0.27 stellt der Gastgeber ein, wie viele Runden **gespielt** werden,
# nicht mehr, wie viele gewonnen werden muessen. Das ist die Zahl, die man
# vorher wissen will ("wir spielen fuenf"). Wer nicht mehr einzuholen ist,
# gewinnt vorzeitig; steht es nach allen Runden gleich - bei einer geraden
# Zahl oder nach einer Runde ohne Sieger -, kommt eine Runde dazu, und die
# ist Matchpoint.
VERSUS = dict(
    runden=5,                 # so viele Runden werden gespielt
    runden_grenzen=(1, 15),   # so weit laesst der Gastgeber das verstellen
    pause=5.0,                # Sekunden zwischen zwei Runden
    boden_zeit=20.0,          # kuerzer als in pve: eine Runde soll laufen
    revive_dauer=4.0,         # und das Aufhelfen dauert laenger
)

# Wie eine Runde endet. Bei pvp und pvpve waehlt der Gastgeber; bei pve
# endet sie, wenn alle am Boden liegen.
ENDE_ARTEN = ("zeit", "abschuesse")

GEFECHT = dict(
    # Gelten Loadouts in dieser Runde? "alles" ist die Vorgabe: wer eine
    # Runde aufmacht, um zu spielen, soll nicht erst eine Ausruestung
    # zusammenstellen muessen. "eigenes" ist die Runde, in der die Wahl
    # der Waffe eine Wahl ist.
    # Seit 0.27 gibt es eine dritte: "gleich" - der Gastgeber waehlt eines
    # seiner Loadouts, und alle tragen genau das. Die Runde, in der nicht
    # die Ausruestung entscheidet, sondern wer besser damit umgeht.
    loadouts="alles",
    loadout_arten=("alles", "eigenes", "gleich"),
    # Der Raketenwerfer. Aus, wenn der Gastgeber ihn nicht will - er
    # veraendert eine Runde, und das soll eine Entscheidung sein.
    rpg=False,
    rpg_lenkung=True,     # mit Zielerfassung, oder ungelenkt
    rpg_takt=75.0,        # Sekunden, bis ein neuer auf der Karte liegt
    # Seit 0.31: eine Runde, die vor ihrem Ende abbricht (Fenster zu,
    # Verbindung weg, der Gastgeber beendet), wird trotzdem gebucht - als
    # "abgebrochen", getrennt von den regulaeren. Erst ab so vielen
    # Sekunden: wer eine Runde aufmacht und gleich wieder zu, hat nicht
    # gespielt, und eine Zeile voller Nullen sagt nichts.
    abbruch_ab=5.0,
    # So oft schickt der Gastgeber jedem Gast seine Zahlen. Bricht die
    # Verbindung, bucht der Gast den letzten Stand - hoechstens so viele
    # Sekunden fehlen dann.
    zwischenstand_takt=2.0,
    team_abschuesse=30,       # Teamabschuesse bis zum Sieg in "team"
    rundenzeit=300.0,         # Sekunden je Runde, wenn nach Zeit gespielt wird
    abschuesse_ziel=20,       # Abschuesse bis zum Sieg, wenn danach gespielt wird
    wieder_nach=3.0,          # Sekunden bis zum Wiedereinstieg nach dem Tod
    punkt_abschuss=1,
    punkt_selbst=-1,          # wer sich selbst erledigt, zahlt drauf
    schutz=2.0,               # Sekunden unverwundbar nach dem Einstieg
    schutz_an=True,           # Vorgabe: der Gastgeber kann ihn abschalten
    abstand=160.0,            # so weit weg von anderen wird eingestiegen
    medkit_takt=12.0,         # Sekunden zwischen zwei Medkits
    medkit_hoechstens=4,      # so viele liegen gleichzeitig herum
    medkits_spawnen=True,     # legt der Gastgeber beim Aufmachen fest
    start_medkits=1,          # so viele hat man beim Einstieg dabei
    start_medkits_hoechstens=9,   # mehr laesst der Gastgeber nicht zu
    tafel_oben=74,            # wo der Punktestand anfaengt, unter den Ebenen
    blick_zurueck=4.0,        # so lange bleibt die Ansicht auf einer fremden Ebene
    # So lange geht nach einem Ebenenwechsel keiner mehr. Seit 0.27 haengt
    # die Treppe am Druck, nicht am Halten - die Sperre faengt nur noch
    # einen versehentlichen Doppeldruck ab und darf darum kurz sein.
    treppe_takt=0.5,
    # Einstiegszonen: jede Mannschaft bekommt einmal je Runde eine Seite
    # und behaelt sie. Aus so vielen Proben wird das Paar mit dem groessten
    # Abstand gewaehlt.
    zonen_proben=40,
    zonen_zug=1.0,            # wie stark die eigene Zone den Platz bestimmt
)

# Am Boden liegen und wieder aufgeholfen werden. Nur in pve.
#
# Der Sinn: ein einzelner Fehler soll einen nicht aus der Runde nehmen,
# aber er soll die anderen etwas kosten - naemlich die Zeit, in der sie
# nicht schiessen, sondern helfen.
# Der Weg durch den Router, fuer Runden ueber das Internet. Siehe
# dustfront/upnp.py - dort steht auch, warum es nur diese eine Moeglichkeit
# ohne eigenen Server gibt.
UPNP = dict(
    gruppe="239.255.255.250",   # die Adresse, an die alle UPnP-Geraete hoeren
    port=1900,
    suchzeit=2.0,             # so lange wird auf Antworten gewartet
    wartezeit=3.0,            # Zeitlimit je Anfrage an den Router
    puffer=8192,
    hoechstens=6,             # so viele Antworten werden angesehen
    dauer=7200,               # Sekunden, die die Freigabe gilt
    beschriftung="DUSTFRONT",   # so heisst die Freigabe im Router
)

# Rufen am Boden (E). Der Gefallene kann sonst nichts - aber er kann
# sagen, wo er liegt. Wer ihn nicht im Bild hat, sieht den Randpfeil
# aufleuchten; wer ihn im Bild hat, sieht ueber ihm ein Zeichen und die
# Figur zucken.
RUFEN = dict(
    sperre=1.5,               # so oft darf man rufen
    zeigen=1.1,               # so lange leuchtet der Ruf nach
    zucken=2.2,               # Pixel, so weit zuckt die Figur beim Ruf
)

# Einen Gefallenen ziehen. Gleiche Reichweite wie beim Aufhelfen - wer
# ihn aufheben koennte, kann ihn auch wegziehen, und umgekehrt.
ZIEHEN = dict(
    tempo=0.52,               # so viel Lauftempo bleibt dem Ziehenden
    leine=20.0,               # so weit hinter ihm liegt der Gezogene
    reisst=64.0,              # weiter weg, und er laesst los
)

REVIVE = dict(
    boden_leben=0.0,          # damit faengt man am Boden an
    boden_zeit=45.0,          # so lange haelt man durch, dann ist es vorbei
    # Seit 0.34.48 laenger (war 3): gemeldet "dass das Wiederbeleben etwas
    # bis deutlich laenger dauert und klarer sichtbar ist".
    dauer=5.5,                # so lange muss ein Helfer danebenstehen
    takt=5.0,                 # so schnell drueckt er dabei (Bogenmass je Sekunde, _haende_zeichnen)
    reichweite=28.0,          # so nah muss er sein
    halten=4.0,               # wer schon hilft, darf so viel weiter weg sein (0.34.55)
    danach_leben=40.0,        # mit so viel Leben steht man wieder auf
    schutz=2.0,               # Sekunden unverwundbar nach dem Aufstehen
    kriechen=0.35,            # so viel Tempo hat man am Boden noch
)

# Verwundete Bots im Testmodus (seit 0.34.40, Testmenue VERWUNDETE BOTS).
# Gemeldet: "dass immer Leichen von toten Gegnern gedroppt werden, nur bei
# den Bots ... die auch wiederbelebt werden koennen, aber dass die Bots
# priorisieren, sie erst in Sicherheit zu ziehen ... das soll nur einmal
# gehen. Danach eine neue Leiche, die ein bisschen anders aussieht und nach
# ein paar Sekunden despawnt. Und ein reanimierter Bot soll schwaecher sein,
# sich langsamer bewegen."
VERWUNDET = dict(
    boden_zeit=45.0,          # so lange liegt einer, bis er verblutet (s)
    leiche_zeit=6.0,          # so lange liegt die zweite Leiche, dann ist sie weg (s)
    danach_max=0.6,           # x Hoechstleben nach dem Wiederbeleben
    danach_tempo=0.75,        # x Lauftempo
    danach_fehler=1.4,        # x Zielfehler
    danach_abstand=80.0,      # so viel mehr Abstand haelt er (Aufgaben auf Distanz)
    bedrohung=320.0,          # Gegner so nah an einem Liegenden, die ihn sehen, bedrohen die Bergung
    # Einer holt ihn (seit 0.34.52, war 2), die anderen bleiben in Deckung -
    # gemeldet: sonst "wuerden sie ja alle quasi einfach dann gekillt", und
    # das Bergen waere eine Todesfalle.
    retter=1,                 # hoechstens so viele ziehen und helfen
    halten_radien=(36.0, 64.0, 100.0, 140.0, 190.0),   # so weit sucht, wer waehrenddessen in Deckung geht
    halten_richtungen=16,
    schutz_ohne_schuss=150.0,  # so viel Weg (px) ist ihm ein Platz wert, von dem aus er Feuerschutz geben kann (0.34.54)
    schutz_halten=20.0,       # ... und so viel lieber bleibt er bei der vorigen Stelle
    deckung_radien=(60.0, 100.0, 140.0, 190.0, 240.0),   # so weit sucht ein Retter Deckung fuer den Liegenden
    rauch_nah=70.0,           # Rauch so nah am Liegenden: die Bergung ist gedeckt
    dranbleiben=12.0,         # so lange bringen die Retter eine angefangene Bergung zu Ende (0.34.50)
    zu_ende=0.5,              # ab so viel Fortschritt hilft er auf, auch wenn ein Gegner auftaucht (0.34.55)
    deckung_rand=8.0,         # so weit daneben muss die Deckung auch noch halten (px, 0.34.52)
    deckung_richtungen=24,    # in so vielen Richtungen je Ring sucht er (war 12: der Schatten einer Kiste fiel dazwischen)
)

# Wellen im Mehrspieler. Anders als im Einzelspieler waechst die Welle mit
# der Zahl der Spieler - sonst ist dieselbe Welle zu viert ein Spaziergang.
WELLEN_MP = dict(
    pause=6.0,                # Sekunden zwischen zwei Wellen
    grund=4,                  # so viele Gegner in Welle 1 bei einem Spieler
    je_welle=0.35,            # plus 35 Prozent je weiterer Welle
    je_spieler=0.6,           # plus 60 Prozent je weiterem Spieler
    hoechstens=40,            # mehr werden nie gleichzeitig unterwegs
    brecher_ab=3,             # nur noch fuer den Notfall, siehe MISCHUNG
    brecher_anteil=0.22,

    # ── Nachschub statt einer einzigen Lieferung.
    #
    # Bisher stand die ganze Welle auf einmal auf der Karte. Das hatte
    # zwei Folgen, und beide waren schlecht: der Druck kam einmal und war
    # dann vorbei, und bei vierzig Gegnern auf einmal fiel die Bildrate.
    # Jetzt kommt sie in Schueben. Der erste ist sofort da, der naechste,
    # sobald genug vom vorigen liegt - so bleibt der Druck stehen,
    # solange die Welle laeuft.
    schub=6,                  # so viele kommen auf einmal
    schub_pause=3.2,          # Sekunden zwischen zwei Schueben
    schub_ab=10,              # erst ab so vielen Gegnern wird geschoben
    gleichzeitig=22,          # so viele stehen hoechstens zugleich da

    # ── Bosse
    boss_alle=5,              # jede fuenfte Welle bringt einen
    boss_ab=5,                # die erste Bosswelle
    boss_leben_je_spieler=0.55,   # plus 55 Prozent Leben je weiterem Spieler
    boss_leben_je_runde=0.30,     # plus 30 Prozent je durchlaufener Bossrunde
    boss_begleitung=0.45,     # so viel der normalen Welle kommt dazu
)

# Schwierigkeit fuer alles mit Wellen, vom Gastgeber gewaehlt.
#
#   anzahl    so viel mehr Gegner je Welle
#   leben     so viel mehr Leben je Gegner
#   schaden   so viel mehr Schaden - Schlag, Spuck, Platzen, Stampfer
#   tempo     so viel schneller. Leicht bleibt bei 1: sonst waere der
#             Renner langsamer als ein gehender Spieler, und genau das
#             ist sein Sinn.
#   boss      so viel mehr Leben fuer den Boss
#   pause     Sekunden zwischen zwei Wellen
#   frueher   um so viele Wellen kommen neue Gegnerarten frueher
#
# NORMAL ist genau das Spiel bis 0.26 - an ihm ist alles gemessen.
SCHWIERIGKEIT = {
    "leicht":   dict(name="LEICHT",   anzahl=0.70, leben=0.75, schaden=0.60,
                     tempo=1.00, boss=0.70, pause=9.0, frueher=0),
    "normal":   dict(name="NORMAL",   anzahl=1.00, leben=1.00, schaden=1.00,
                     tempo=1.00, boss=1.00, pause=6.0, frueher=0),
    "schwer":   dict(name="SCHWER",   anzahl=1.30, leben=1.20, schaden=1.30,
                     tempo=1.05, boss=1.35, pause=5.0, frueher=0),
    "albtraum": dict(name="ALBTRAUM", anzahl=1.60, leben=1.45, schaden=1.60,
                     tempo=1.10, boss=1.70, pause=4.0, frueher=1),
}
SCHWIERIGKEIT_VORGABE = "normal"


def gegner_verstaerkt(daten: dict, stufe: dict) -> dict:
    """Die Werte eines Gegners, mit einer Schwierigkeit verrechnet.

    Eine Kopie: die Tabelle selbst bleibt, wie sie ist, sonst wuerde jede
    Welle auf SCHWER die naechste noch einmal verstaerken. Schaden wird
    ueberall verrechnet, wo er steht - auch im Spuck, im Platzen und in
    der Faehigkeit eines Bosses.
    """
    d = dict(daten)
    d["schaden"] = d.get("schaden", 0.0) * stufe["schaden"]
    d["tempo"] = d.get("tempo", 0.0) * stufe["tempo"]
    for teil in ("fern", "platzt", "faehigkeit"):
        if isinstance(d.get(teil), dict):
            d[teil] = dict(d[teil])
            if "schaden" in d[teil]:
                d[teil]["schaden"] = d[teil]["schaden"] * stufe["schaden"]
    return d


# Woraus eine Welle besteht. Je Eintrag: ab welcher Welle es den Gegner
# gibt, und mit welchem Gewicht er dann gezogen wird.
#
# Gelesen wird das so: in Welle 1 gibt es nur Laeufer. Ab Welle 2 kommen
# Renner dazu, ab 3 Brecher, ab 5 Blaeher, ab 6 Speier. Die Gewichte
# verschieben sich mit der Welle - `steigt` ist der Zuschlag je Welle
# nach dem Auftauchen. Laeufer haben einen negativen: sie bleiben, aber
# sie machen mit der Zeit Platz.
#
# Warum ueberhaupt gestaffelt: weil ein Spieler in Welle 1 nicht fuenf
# Gegnerarten lernen kann. Jede Welle bringt hoechstens eine neue dazu,
# und zwischen zwei neuen liegt immer mindestens eine Welle zum Ueben.
MISCHUNG = (
    dict(art="laeufer", ab=1, gewicht=10.0, steigt=-0.55, mindestens=1.5),
    dict(art="renner",  ab=2, gewicht=2.0,  steigt=0.55),
    dict(art="brecher", ab=3, gewicht=1.2,  steigt=0.40),
    # ab=4 und nicht 5: Welle 5 ist die erste Bosswelle, und die ist
    # schon die neue Sache. Zwei neue Dinge in derselben Welle sind
    # eines zu viel.
    dict(art="blaeher", ab=4, gewicht=1.0,  steigt=0.28),
    dict(art="speier",  ab=6, gewicht=1.0,  steigt=0.30),
)

# ── Wo Gegner auftauchen
#
# Das war der eigentliche Fehler, und er fiel erst mit STAUBTAL auf.
# Gemessen auf 3840 x 2560 Pixeln: ein Gegner landete im Mittel 1477
# Pixel vom naechsten Spieler entfernt, also **zwanzig Sekunden**
# Fussmarsch, der weiteste 27 Sekunden - und vier von sechs auf einer
# Ebene, auf der niemand stand. Eine Welle war damit zwanzig Sekunden
# nichts und danach ein Troepfeln. Auf der kleinen Testkarte fiel das
# nie auf (Median 420 Pixel, sechs Sekunden), weil die Karte so klein
# ist, dass ein zufaelliger Punkt zwangslaeufig nah liegt.
#
# Die Stelle wird jetzt gesucht und nicht gewuerfelt, nach vier Regeln:
SPAWN = dict(
    nah=260.0,          # naeher nicht: sonst steht er im Gesicht
    weit=620.0,         # weiter nicht: sonst laeuft man Welle statt Kampf
    weit_boss=760.0,    # ein Boss darf von weiter kommen, man soll ihn sehen
    eigene_ebene=0.85,  # so oft auf der Ebene eines Spielers
    verdeckt_versuche=14,   # so oft wird eine Stelle ausser Sicht gesucht
    versuche=60,        # danach: irgendeine freie Stelle im Band
    marken="Z",         # Buchstaben in der Karte, die Spawnstellen sind
    marke_band=1.6,     # eine Marke zaehlt bis zum 1,6-fachen von `weit`
    marke_anteil=0.55,  # so oft wird eine passende Marke genommen
)

# Gegner-KI im Mehrspieler: mehrere Ziele statt einem.
GEGNER_MP = dict(
    ziel_haltezeit=2.5,       # so lange bleibt ein Gegner bei seinem Ziel
    gedraenge=0.55,           # Aufschlag je Gegner, der schon an dem Ziel haengt
    ebenen_strafe=420.0,      # so viel "weiter weg" zaehlt eine fremde Ebene
    boden_strafe=900.0,       # wer am Boden liegt, zieht kaum noch Gegner an

    # ── Wer nicht ankommt, wird umgesetzt.
    #
    # Das Ausweichen ist ein Faecher aus Proben und kein Wegesucher. Das
    # reicht fuer eine Kiste und ein Mauerstueck - an einem Plateau von
    # 32 mal 19 Kacheln reicht es nicht. Gemessen auf STAUBTAL: ein
    # Laeufer stand nach 120 Sekunden immer noch 323 Pixel entfernt auf
    # **derselben** Ebene wie die Spieler und kam nicht heran. Weil eine
    # Welle erst endet, wenn alle liegen, stand damit die ganze Runde -
    # in 300 Sekunden wurde Welle 2 nicht fertig.
    #
    # Ein richtiger Wegesucher waere die saubere Antwort und ein eigenes
    # Stueck Arbeit. Das hier ist die ehrliche: wer eine Weile nicht
    # naeher kommt, wird an eine frische Stelle gesetzt. Er ist dabei
    # ohnehin ausser Sicht, und die Welle laeuft weiter.
    stockt_ab=7.0,            # so lange ohne Fortschritt gilt als Haenger
    stockt_schritt=16.0,      # weniger Naeherung als das zaehlt nicht
    stockt_pruefung=1.0,      # so oft wird nachgesehen
    # Umgesetzt wird nur, wen gerade niemand sehen kann - und zwar schon
    # eine Weile nicht (seit 0.32.6, gemeldet: "despawnen in Sicht, auch
    # wenn sie nur ganz kurz ausser Sicht geraten"). "Sehen" heisst: im
    # Bildausschnitt irgendeines Spielers bei groesster Sichtweite, egal
    # auf welcher Ebene - von einem Plateau sieht man auf den Sand.
    unsichtbar_ab=5.0,        # so lange ausser Sicht, dann erst umsetzen
    sicht_halb=(700.0, 400.0),  # halber Bildausschnitt bei Zoom 2, mit Rand
)

# Begrenzte Munition. Der Gastgeber schaltet sie beim Aufmachen an.
MUNITION = dict(
    # Rund drei Nachladungen je Waffe. Vorher war es das Doppelte, und
    # damit war die Begrenzung keine: 279 Schuss im Vorrat merkt in einer
    # Testrunde niemand, und ein Vorrat, der nie sinkt, macht auch jede
    # Munitionskiste nutzlos - man kann nichts aufnehmen, was man nicht
    # braucht.
    vorrat={"repetierer": 42, "sturm": 90, "schrot": 18, "scharf": 10,
            "lmg": 200, "granate": 3, "rauch": 2, "molotov": 2, "blend": 2,
            "c4": 2,
            "brecheisen": 0},
    kiste_takt=14.0,          # Sekunden zwischen zwei Munitionskisten
    kiste_hoechstens=4,
    kiste_gibt=0.5,           # so viel vom vollen Vorrat gibt eine Kiste
)

# C4 ist ein kurzer Wurf ohne Abprallen. Der Zaehler startet erst, wenn
# der Brick an Boden oder Wand klebt; so ist die Ladezeit sichtbar nutzbar.
# ladezeit: so lange nach dem Kleben, bis der Zuender sie hochgehen laesst
# (seit 0.34.12 drei statt fuenf Sekunden).
C4 = dict(wurfweite=76.0, wurftempo=260.0, ladezeit=3.0,
          radius=158.0, schaden=210.0, schub=420.0)

# ══════════════════════════════════════════════════ HOEHE

# Hoehe jeder Ebene in Welt-Pixeln. Der Abstand zwischen zwei Ebenen
# entscheidet ueber drei Dinge: wie klein die untere gezeichnet wird, wie
# lange ein Sturz dauert und wie weh er tut.
#
#   0 -> 1   Boden hinauf in die erste Mech-Etage, sehr weit
#   1 -> 2   eine Etage im selben Rumpf, deutlich enger
EBENEN_HOEHE = [0, 118, 182, 238, 288]

# Ebenenwechsel ueber Treppe, Luke oder Aufzug (nicht durch einen Sturz).
# Bis 0.32.9 zog die Ansicht in rund einer halben Sekunde zur neuen Hoehe
# nach. Solange sie unterwegs war, galt die eigene Ebene als "darueber"
# oder "darunter": hinauf wurde sie ausgestanzt - die Figur war weg, nur
# der Laser blieb -, hinab war sie abgedunkelt und wurde erst langsam
# hell. Jetzt springt die Ansicht sofort, und das letzte Bild der alten
# Ebene blendet ueber diese Zeit aus.
EBENENWECHSEL = dict(
    ueberblenden=0.22,    # Sekunden, bis das alte Bild ganz weg ist
)

PERSPEKTIVE = dict(
    brennweite=430.0,     # je kleiner, desto staerker schrumpft die Tiefe
    dunkel=128,           # Helligkeit der Ebene darunter (255 = unveraendert)
    dunst=(20, 17, 26),   # kalter Schleier, der mit der Tiefe zunimmt
    dunst_staerke=0.42,
    tiefe_sichtbar=8,     # so viele Ebenen nach unten werden gezeichnet
    ausblenden=150.0,     # so weit ueber der Ansicht verschwindet eine Ebene
    # Hoeher als eine Etage ueber der Ansicht wird nur gezeichnet, was auf
    # einem geschlossenen Felsblock steht und oben so viele begehbare
    # Kacheln hat - eine Tafel, kein Mauerrand (seit 0.34.7).
    turm_flaeche=16,
    # Ein Plateau braucht oben mindestens so viele begehbare Kacheln. Ein
    # kleineres Stueck Etage ueber einer Mauer oder Kiste (die Stege der
    # Testkarte) ist ein Steg und kein Felsblock: es blendet mit der Etage
    # aus, statt als schmale Saeule stehen zu bleiben (seit 0.34.19).
    # Die kleinsten echten Plateaus (SCHNEEFELD) haben ueber 100.
    plateau_flaeche=16,
    massstab_schwelle=0.02,   # ab so viel Abweichung wird ein Wesen im Sturz
                              # ueberhaupt umgerechnet
)

# Die Felswand zwischen einem Plateau und dem Boden darunter (render.py,
# Renderer.klippen). Ein Plateau ist ein Felsblock, kein schwebender
# Deckel - bis 0.31 hing er versetzt und blass ueber seinem Sockel.
# Waende und Barrikaden stehen (seit 0.34.3, render.Renderer.
# _stehende_zeichnen). Bis dahin waren sie flache Kacheln wie der Boden:
# von oben auf dem Plateau sah eine Lehmmauer aus wie ein Weg, und von
# einer hoeheren Ebene aus war eine Wand unten nur ein dunkleres Feld.
# Jetzt hat jede eine Hoehe in Welt-Pixeln und wird wie die Plateaus in
# Perspektive gezeichnet: Oberseite vom Auge weg verschoben, dazwischen die
# Seiten, die dem Auge zugewandt sind. Senkrecht unter dem Auge sieht man
# keine Seite - dort traegt die Oberseite (Bild "<name>_oben") mit Kante.
#
# Schluessel ist der Bildname (Kartensatz beachtet), dann die Kachelart.
#   hoehe    Welt-Pixel ueber dem Boden
#   rahmen   (x, y, b, h) der Grundflaeche in der Kachel; der Rest ist Boden.
#            Seit 0.34.19 haelt nur sie auf (world.Welt.frei): an einen
#            Kaktus kommt man so nah heran, wie er gross ist, nicht bis zur
#            Kachelkante. Ihr Schatten hat dieselbe Form.
#   form     "block" (Kanten) oder "rund" (Fass)
#   fugen    so viele Querlinien auf jeder Seite (Steinlagen, Fassreifen)
STEHEN = {
    "wand":       dict(hoehe=24.0, rahmen=(0, 0, 32, 32), form="block", fugen=2),
    "sand_wand":  dict(hoehe=24.0, rahmen=(0, 0, 32, 32), form="block", fugen=2),
    "schnee_fels": dict(hoehe=24.0, rahmen=(0, 0, 32, 32), form="block", fugen=2),
    "kiste":      dict(hoehe=14.0, rahmen=(4, 4, 24, 24), form="block", fugen=1),
    "sand_kiste": dict(hoehe=14.0, rahmen=(5, 5, 22, 22), form="rund", fugen=2),
    # Seit 0.34.6. Gewachsener Fels ist hoeher als eine Mauer - man sieht
    # an der Hoehe, was gebaut und was gewachsen ist. Varianten (fels_2,
    # schrott_3 ...) finden ihren Eintrag ueber den Namen der Kachelart.
    "fels":       dict(hoehe=30.0, rahmen=(0, 0, 32, 32), form="block", fugen=3),
    "brocken":    dict(hoehe=13.0, rahmen=(4, 4, 24, 24), form="rund", fugen=0),
    "sandsack":   dict(hoehe=12.0, rahmen=(0, 0, 32, 32), form="block", fugen=1),
    "holzkiste":  dict(hoehe=16.0, rahmen=(3, 3, 26, 26), form="block", fugen=2),
    "kaktus":     dict(hoehe=20.0, rahmen=(7, 7, 18, 18), form="rund", fugen=0),
    "schrott":    dict(hoehe=14.0, rahmen=(0, 0, 32, 32), form="block", fugen=1),
}

# Deckung (seit 0.34.26, world.Welt.schuss_halt / deckung). Jede feste
# Kachel haelt eine Kugel auf, mit ihrer Grundflaeche aus STEHEN - bis
# dahin nur Mauern und Fels. Gemeldet: "Alles, was eine Art Textur hat und
# etwas blocken sollte, sollte auch Schuesse blocken. So etwas wie die
# Explosion einer Granate sollte aber leicht durchgehen. Und eine
# Blendgranate sollte dadurch nur abgeschwaecht werden."
# Anteile dessen, was hinter einem Hindernis (Kiste, Sandsack, Fass) oder
# einer Mauer noch ankommt. Granate, Rakete, C4 und ein platzender Buggy;
# der Stampfer-Boss trifft weiter auch hinter Deckung (mit Absicht).
DECKUNG = dict(
    explosion_frei=1.0,
    explosion_hindernis=0.55,
    explosion_wand=0.2,       # bis 0.34.25 ging die Druckwelle ganz durch
    blend_hindernis=0.6,      # die Mauer haelt den Blitz weiter ganz ab
)

# Kartensaetze: welche Bilder eine Karte statt der gewoehnlichen nimmt
# (Kopf "satz:"). Seit 0.34.19 hier statt im Renderer: auch die Kollision
# braucht sie - eine Kiste ist in der Wueste ein rundes Fass und haelt
# darum rund auf (world.Welt.huelle).
KARTENSAETZE = {
    "": {},
    # "klippe": woraus die Wand zwischen Plateau und Boden ist. Seit
    # 0.35 in der Wueste gewachsener Fels, nicht die Lehmmauer.
    "wueste": {"boden": ("sand", "sand_2", "sand_3", "sand_4"),
               "wand": "sand_wand", "kiste": "sand_kiste", "klippe": "fels"},
    "schnee": {"boden": ("schnee", "schnee_2", "schnee_3", "schnee_4"),
               "wand": "schnee_fels"},
}

# Wie hoch ueber dem Boden etwas in der Welt ist, in Welt-Pixeln (seit
# 0.34.5). Gebraucht nur fuer die Frage, ob eine Mauer es verdeckt
# (render.Renderer.verdeckt): was tiefer ist als die Mauer und vom Auge
# aus dahinter liegt, ist nicht zu sehen; was darueber fliegt, schon.
# Gezeichnet wird alles weiter an seinem Fusspunkt, wie die Figuren -
# sonst saehe ein Treffer am Bildrand aus wie ein Fehlschuss.
HOEHEN = dict(
    lauf=12.0,            # Geschosse, Raketen, Muendungsfeuer: Laufhoehe
    funke=10.0,           # Funken fliegen um die Treffer- und Laufhoehe
    funke_dauer=10.0,
    glitzer_dauer=10.0,
    blut=6.0,
    staub=3.0,            # Staub wirbelt knapp ueber dem Boden
    huelse=0.0,           # Huelsen liegen am Boden
    partikel=6.0,         # alles uebrige
)

# Figuren mit Hoehe (seit 0.34.25, render.Renderer.figur_zeichnen): wie die
# stehenden Kacheln (STEHEN) in Perspektive - das Bild der Figur ist ihr
# Deckel und rueckt mit der Hoehe von der Bildmitte weg, darunter liegen
# dunklere Schichten als Seitenwand. Am Bildrand sieht man die Seite, in
# der Mitte steht man genau darueber. Hoehen in Welt-Pixeln wie bei STEHEN
# (Kiste 14, Kaktus 20). Nur das Bild: getroffen wird wie bisher.
# Seit 0.34.34 nur noch fuer Gegenstaende: Figuren (Spieler, Bots, Gegner,
# Bosse) sind wieder flach - gemeldet: "das ist doch nicht so gut".
FIGUREN_3D = dict(
    an=True,
    buggy=11.0,
    beute=4.0,                # Medkit und was sonst am Boden liegt
    seite_unten=0.45,         # Helligkeit der Seitenwand am Boden (x mittlere Farbe)
    seite_oben=0.85,          # ... und unter dem Deckel
    seite_stufen=4,           # so viele Helligkeiten dazwischen
    schichten_max=10,         # Seitenwand aus hoechstens so vielen Schichten (Tempo)
)

KLIPPEN = dict(
    schichten=4,          # so viele Gesteinsbaender von oben nach unten
    abdunkeln=0.42,       # um so viel ist das unterste dunkler als das oberste
    fuge=0.72,            # die Linie zwischen zwei Baendern, so viel dunkler
    kante=1.45,           # die Oberkante faengt Licht, so viel heller
)

STURZ = dict(
    schwerkraft=980.0,    # Pixel je Sekunde im Quadrat, bestimmt die Falldauer
    luftsteuerung=0.55,   # so viel Bewegung hat man waehrend des Sturzes
    schaden_je_100=9.0,   # Schaden pro 100 Pixel Fallhoehe
    min_schaden=3.0,
    staub=22,             # Partikel beim Aufsetzen
    ruckeln=2.4,          # Grundwert des Kameraschlags, dazu die Hoehe
    ring_dauer=0.34,      # so lange steht der Staubring am Boden
    ring_weite=34.0,      # so weit laeuft er auseinander
    abrutschen=140.0,     # Pixel je Sekunde, mit denen man im Flug an einem
                          # Hindernis unter sich zur Seite rutscht
)

# Zielhilfe: eine Linie von der Waffe zum Mauszeiger, mit Z auch darueber
# hinaus bis zur naechsten Wand.
TRACER = dict(
    # So weit wie der Scharfschuetze schiesst: die verlaengerte Linie soll
    # zeigen, wo der Schuss hingeht, und nicht vorher aufhoeren.
    weite=2200.0,
    farbe=(214, 64, 48),
    punkt=(255, 110, 86),  # der Fleck da, wo die Linie endet
    staerke=150,           # Deckkraft der Linie
)

# ══════════════════════════════════════════════════ INHALTE: Kacheln

# fest      blockiert Bewegung
# sicht     blockiert Schuesse und Sicht
# treppe    Zielebene relativ zur aktuellen, sonst None
# aufzug    Aufzugbild mit Treppenbedienung: E bringt eine Ebene weiter.
# bilder    mehrere Bilder einer Art, je Kachel eins nach ihrer Variante
#           (Ebene.variante) - sonst sieht man ein Muster
# weich     Bodenart ohne feste Kante (Piste, Kies): wo Sand angrenzt,
#           franst der Sand in sie hinein, statt dass eine Kachelkante
#           eine Linie zieht (render.Renderer._weicher_rand)
LEER, BODEN, GITTER, WAND, KISTE, TREPPE_HOCH, TREPPE_RUNTER, LUKE, \
    AUFZUG_HOCH, AUFZUG_RUNTER, FELS, BROCKEN, SANDSACK, HOLZKISTE, \
    KAKTUS, SCHROTT, PISTE, KIES, PFLASTER, GESTRUEPP, DIELEN = range(21)

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
    # Die alten Aufzugbilder bleiben, die Bedienung nutzt wieder E und
    # wechselt genau eine Ebene wie eine Treppe.
    AUFZUG_HOCH:   dict(name="aufzug",   fest=False, sicht=False, bild="aufzug_tuer",
                        treppe=+1),
    AUFZUG_RUNTER: dict(name="aufzug",   fest=False, sicht=False, bild="aufzug_schacht",
                        treppe=-1),
    # Seit 0.34.6 fuer STAUBTAL: Gelaende und Kleinkram, damit eine Karte
    # nicht nur aus Sand, Mauer und Fass besteht. Gewachsener Fels ist
    # hoch und sichtdicht wie eine Mauer; was niedriger ist als ein
    # Mensch (Brocken, Sandsack, Kiste, Kaktus, Schrott), haelt auf wie
    # das Fass und verdeckt nicht. Bis 0.34.25 schoss man darueber hinweg;
    # seit 0.34.26 haelt es Kugeln auf wie alles Feste (DECKUNG).
    FELS:          dict(name="fels",     fest=True,  sicht=True,  bild="fels",
                        bilder=("fels", "fels_2", "fels_3")),
    BROCKEN:       dict(name="brocken",  fest=True,  sicht=False, bild="brocken",
                        bilder=("brocken", "brocken_2", "brocken_3")),
    SANDSACK:      dict(name="sandsack", fest=True,  sicht=False, bild="sandsack"),
    HOLZKISTE:     dict(name="holzkiste", fest=True, sicht=False, bild="holzkiste"),
    KAKTUS:        dict(name="kaktus",   fest=True,  sicht=False, bild="kaktus"),
    SCHROTT:       dict(name="schrott",  fest=True,  sicht=False, bild="schrott",
                        bilder=("schrott", "schrott_2", "schrott_3")),
    PISTE:         dict(name="piste",    fest=False, sicht=False, bild="piste",
                        bilder=("piste", "piste_2", "piste_3", "piste_4"), weich=True),
    KIES:          dict(name="kies",     fest=False, sicht=False, bild="kies",
                        bilder=("kies", "kies_2", "kies_3", "kies_4"), weich=True),
    PFLASTER:      dict(name="pflaster", fest=False, sicht=False, bild="pflaster",
                        bilder=("pflaster", "pflaster_2", "pflaster_3")),
    GESTRUEPP:     dict(name="gestruepp", fest=False, sicht=False, bild="gestruepp",
                        bilder=("gestruepp", "gestruepp_2", "gestruepp_3", "gestruepp_4")),
    DIELEN:        dict(name="dielen",   fest=False, sicht=False, bild="dielen",
                        bilder=("dielen", "dielen_2")),
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
        # 0.32: 430 -> 560. Die genaueste Waffe nach dem Scharfschuetzen
        # reichte weniger weit als das Sturmgewehr (470) - damit hatte
        # sie keine Lage, in der sie die bessere Wahl war.
        reichweite=560.0,
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
        # Enger und weiter als frueher (7.5 Grad, 210 px). Sie bleibt die
        # Waffe fuer kurze Wege, trifft jetzt aber auch auf halber
        # Zimmerbreite noch mit mehr als zwei Kuegelchen.
        streuung=5.5,
        streuung_lauf=3.0,
        geschosse=7,
        tempo=560.0,
        reichweite=300.0,
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
        name="SCHARFSCHÜTZE",
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
        # Weiter, als man sehen kann: das Bild ist 640 Pixel breit, die
        # Karte diagonal rund 1600. Mit 2200 endet ein Schuss an einer
        # Wand oder am Kartenrand, nie an seiner eigenen Reichweite.
        reichweite=2200.0,
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
    "rauch": dict(
        art="wurf",
        name="RAUCHGRANATE",
        rauch=True,           # zuendet nicht, sondern qualmt
        schaden=0.0,
        radius=0.0,
        takt=0.9,
        magazin=2,
        nachladen=3.4,
        wurf_min=45.0,
        wurf_max=165.0,       # deutlich kuerzer als die Sprenggranate (260)
        reibung=1.8,          # und rollt schneller aus
        flugzeit=1.1,
        kamera=1.2,
        rueckstoss=0.0,
        huelsen=0,
    ),
    # ── MG ───────────────────────────────────────────────────────────
    #
    # Die schwerste Waffe im Spiel, und sie fuehlt sich auch so an. Wer
    # sie abfeuert, steht praktisch: das Lauftempo faellt auf ein Drittel,
    # und drehen laesst sie sich nur noch langsam. Dafuer wird sie, je
    # laenger man haelt, **genauer** - umgekehrt zu allem anderen hier.
    #
    # **Zwei Betriebsarten**, umschaltbar auf einer eigenen Taste. Was in
    # `modi` steht, ueberschreibt die Werte darueber; der Rest des Codes
    # sieht davon nichts und liest wie bisher `takt` und `streuung`.
    #
    #   dauer   Dauerfeuer mit Anlauf wie bei einer Minigun. Der erste
    #           Schuss kommt spaet, dann wird es schneller. Antippen
    #           bringt darum fast nichts - genau so gewollt: dieses Ding
    #           ist keine Waffe fuer einen Schuss.
    #   salve   Kurze Salven, vier Schuss fast gleichzeitig. Dazwischen
    #           kann man warten, im Stehen ist sie enger, und drehen geht
    #           ein Stueck besser. Die Betriebsart fuer den, der eine
    #           Stellung haelt statt einen Gang zu fegen.
    #
    # Abgeschwaecht in 0.29 (gemeldet: "macht teils mehr Schaden als die
    # Sniper"). So war es: 25 je Schuss, die Salve vier davon fast
    # gleichzeitig - 100 auf einen Klick, mehr als ein Scharfschuss (98) -,
    # und im Dauerfeuer 347 Schaden je Sekunde, fast doppelt so viel wie
    # das Sturmgewehr. Jetzt: 17 je Schuss (ein Hauch ueber dem
    # Sturmgewehr), die Salve zu dreien (51, rund ein halber Scharfschuss),
    # Dauerfeuer bei voller Drehzahl knapp unter dem Sturmgewehr. Was das
    # MG behaelt: das Magazin, die Reichweite, die Genauigkeit beim Halten.
    "lmg": dict(
        art="schuss",
        name="MG",
        # Je Schuss mehr als das Sturmgewehr (16) - so gewuenscht ("guter
        # Schaden"). Seine Staerke bezahlt es mit Anlauf, Gewicht und seit
        # 0.32 mit der kuerzeren Reichweite.
        schaden=17.0,
        tempo=1020.0,
        # 0.32: 1450 -> 1000. Mit dem engen Kegel nach dem Einschiessen
        # (0,9 Grad) war es auf 1450 Pixel ein zweiter Scharfschuetze mit
        # hundert Schuss. Jetzt bleibt die Weite dem Scharfschuetzen.
        reichweite=1000.0,
        magazin=100,
        nachladen=6.4,         # das dauert, und das soll es
        geschosse=1,
        huelsen=2,
        kamera=1.0,
        # 0.32: Das MG schiebt den Schuetzen kaum noch. Gemeldet: "dass das
        # MG einen so weit nach hinten drueckt, war so nicht gedacht ...
        # das ist ein sehr starkes Movement Tool". Es soll langsam machen
        # (gewicht_tempo), nicht schieben. Der alte Schub (30 je Schuss)
        # bleibt als erweiterte Rundenregel "MG-RUECKSTOSS SCHIEBT".
        rueckstoss=3.0,
        rueckstoss_voll=30.0,
        takt=0.075,
        streuung=7.0,
        streuung_lauf=5.0,
        # Was das MG ausmacht, unabhaengig von der Betriebsart.
        gewicht_tempo=0.32,    # so viel vom Lauftempo bleibt beim Feuern
        gewicht_drehen=64.0,   # Grad je Sekunde, mehr geht nicht
        modi=("dauer", "salve"),
        modus_daten={
            "dauer": dict(
                kurz="DAUER",
                takt=0.095,            # bei voller Drehzahl
                anlauf_takt=0.30,      # und am Anfang
                anlauf=1.15,           # Sekunden bis zur vollen Drehzahl
                anlauf_abbau=2.4,      # wie schnell sie wieder faellt
                streuung=7.5,
                streuung_ziel=0.9,     # so eng wird sie beim Halten
                streuung_dauer=2.6,    # so lange dauert das
                gewicht_tempo=0.28,
                gewicht_drehen=56.0,
            ),
            "salve": dict(
                kurz="SALVE",
                takt=0.9,              # zwischen zwei Salven
                salve=3,               # Schuesse je Salve
                salve_takt=0.032,      # fast gleichzeitig
                anlauf_takt=0.85,      # kein Anlauf: die erste Salve sitzt
                anlauf=0.01,
                anlauf_abbau=4.0,
                streuung=3.0,
                streuung_ziel=1.4,
                streuung_dauer=1.2,
                streuung_stand=0.55,   # im Stehen so viel davon
                gewicht_tempo=0.52,
                gewicht_drehen=92.0,
            ),
        },
    ),
    # ── Raketenwerfer ────────────────────────────────────────────────
    #
    # Kein Platz in der Hotbar: er liegt **einmal** auf der Karte, und wer
    # ihn aufhebt, traegt nur noch ihn - bis er geschossen hat. Das
    # Brecheisen bleibt auf F, sonst waere man voellig wehrlos.
    #
    # Eigenschaden ja, Mannschaftsschaden nein. Beides mit Absicht: wer
    # aus zwei Metern auf eine Wand schiesst, soll dafuer bezahlen, aber
    # niemand soll seine eigenen Leute mitnehmen koennen - eine Waffe,
    # die einmal in der Runde vorkommt, darf keine Runde ruinieren.
    "rakete": dict(
        art="rakete",
        name="RAKETENWERFER",
        schaden=150.0,
        radius=104.0,         # Wirkungskreis
        eigen_anteil=0.55,    # so viel davon bekommt man selbst ab
        takt=1.2,
        magazin=1,
        nachladen=0.0,        # nachgeladen wird nicht: eine ist eine
        tempo=330.0,          # langsam genug, dass man ausweichen kann
        reichweite=1800.0,
        flugzeit=5.0,
        kamera=8.0,
        rueckstoss=90.0,
        huelsen=0,
        streuung=0.6,
        # Lenkung. Nur, wenn der Gastgeber sie eingeschaltet hat.
        lenk_dreh=120.0,      # Grad je Sekunde, mehr schafft sie nicht
        lenk_ab=40.0,         # ab dieser Entfernung wird ueberhaupt gelenkt
    ),
    "blend": dict(
        art="wurf",
        name="BLENDGRANATE",
        # Sie macht keinen Schaden. Sie nimmt eine Sekunde - und eine
        # Sekunde ist in einem Gefecht sehr lang.
        blend=True,
        schaden=0.0,
        radius=0.0,
        takt=0.9,
        magazin=2,
        nachladen=3.2,
        wurf_min=60.0,
        wurf_max=260.0,
        reibung=1.2,
        flugzeit=1.35,        # laenger als eine Granate: man wirft sie voraus
        kamera=0.0,           # der Knall ruckelt nicht, er blendet
        rueckstoss=0.0,
        huelsen=0,
    ),
    "c4": dict(
        art="c4",
        name="C4",
        magazin=1,
        nachladen=0.0,
        takt=0.25,
        kamera=0.5,
        rueckstoss=0.0,
        huelsen=0,
    ),
    "molotov": dict(
        art="wurf",
        name="MOLOTOW",
        # Kein Sprengschaden. Das ist der ganze Punkt an dieser Waffe:
        # sie toetet niemanden im Wurf, sie **nimmt einen Ort weg**. Wer
        # durchlaeuft, brennt; wer wartet, verliert Zeit. Eine Granate
        # entscheidet einen Zweikampf, ein Molotow entscheidet, wo er
        # stattfindet.
        feuer=True,
        schaden=0.0,          # im Einschlag
        radius=0.0,
        takt=1.0,
        magazin=2,
        nachladen=3.6,
        wurf_min=55.0,
        wurf_max=225.0,
        reibung=1.5,
        flugzeit=0.95,        # zerbricht frueher als eine Granate zuendet
        kamera=1.4,
        rueckstoss=0.0,
        huelsen=0,
    ),
    "brecheisen": dict(
        art="nahkampf",
        name="BRECHEISEN",
        # Zwei Treffer toeten (2 x 60 > 100 Leben). Der Takt liegt knapp
        # ueber SPIELER["unverwundbar"] (0.6 s): mit den frueheren 0.40 s
        # lief jeder zweite Schlag in die Unverwundbarkeit des Getroffenen
        # und war umsonst - drei Schlaege fuer zwei Treffer. Jetzt sitzt
        # jeder Schlag, und ein Mann ist nach 0.62 s erledigt.
        schaden=60.0,
        takt=0.62,
        reichweite=36.0,
        winkel=80.0,          # Oeffnung des Schlags in Grad
        schwung=0.26,         # so lange dauert die Schlagbewegung im Bild
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
# Seit 0.34.43: jedes Geschoss fliegt mit BEWEGUNG["geschoss"] (siehe dort).
for _w in WAFFEN.values():
    if _w.get("art") == "schuss":
        _w["tempo"] = _w["tempo"] * BEWEGUNG["geschoss"]

WAFFEN_HAND = {
    "repetierer": dict(lauf=17, dicke=3, schaft=9, s_dicke=4, holz=True,
                       aufbau="kammer"),
    "sturm":      dict(lauf=14, dicke=4, schaft=8, s_dicke=5, holz=False,
                       aufbau="magazin"),
    "schrot":     dict(lauf=14, dicke=5, schaft=9, s_dicke=6, holz=True,
                       aufbau="doppel"),
    "scharf":     dict(lauf=22, dicke=3, schaft=9, s_dicke=4, holz=True,
                       aufbau="fernrohr"),
    # Lang wie der Scharfschuetze, aber viel dicker, mit Kastenmagazin
    # und Zweibein. Man soll an der Hand sehen, was jemand traegt.
    "lmg":        dict(lauf=21, dicke=6, schaft=11, s_dicke=7, holz=False,
                       aufbau="zweibein"),
    # Ein Rohr, dick und stumpf, mit dem Sprengkopf vorn. Die
    # unverwechselbarste Silhouette im ganzen Spiel - und das soll sie
    # sein: wer eine Rakete traegt, ist von weitem zu erkennen.
    "rakete":     dict(lauf=24, dicke=8, schaft=6, s_dicke=5, holz=False,
                       aufbau="rohr"),
    "granate":    dict(lauf=0,  dicke=0, schaft=0, s_dicke=0, holz=False,
                       aufbau="kugel"),
    "rauch":      dict(lauf=0,  dicke=0, schaft=0, s_dicke=0, holz=False,
                       aufbau="buechse"),
    "molotov":    dict(lauf=0,  dicke=0, schaft=0, s_dicke=0, holz=False,
                       aufbau="flasche"),
    "blend":      dict(lauf=0,  dicke=0, schaft=0, s_dicke=0, holz=False,
                       aufbau="walze"),
    "brecheisen": dict(lauf=15, dicke=2, schaft=5, s_dicke=2, holz=False,
                       aufbau="haken"),
    # Keine Waffe, aber etwas in der Hand: waehrend ein Medkit angelegt
    # wird, haelt die Figur es statt der Waffe. Steht hier, damit es wie
    # jede Waffe eine Figur je Mannschaft bekommt.
    "medkit":     dict(lauf=0,  dicke=0, schaft=0, s_dicke=0, holz=False,
                       aufbau="koffer"),
}

# Jede Mannschaft bekommt ihre eigene Fassung jeder Spielerfigur. Sie sind
# damit einzeln durch eine Datei ersetzbar - wer `assets/spieler_rot_sturm.png`
# hinlegt, bekommt genau die eine Figur ausgetauscht, und der Rest bleibt.
for _team in TEAMS["kombi"]:
    _kurz = _team["name"].lower()
    BILD_MASS["spieler_%s" % _kurz] = BILD_MASS["spieler"]
    BILD_MASS["spieler_%s_boden" % _kurz] = BILD_MASS["spieler_boden"]
    BILD_MASS["leiche_%s" % _kurz] = BILD_MASS["spieler_boden"]
    for _w in WAFFEN_HAND:
        BILD_MASS["spieler_%s_%s" % (_kurz, _w)] = BILD_MASS["spieler_" + _w]

# Der Schlag mit dem Brecheisen als Figur (seit 0.32.8): die Gestalt haelt
# das Eisen mit beiden Haenden und schwingt es - je ein Bild fuer einen
# Winkel des Schwungs. Groesser als die gewoehnliche Figur, weil das Eisen
# ueber sie hinausragt; gezeichnet wird mittig wie jede Figur.
SCHWUNG_BILDER = 9
for _i in range(SCHWUNG_BILDER):
    BILD_MASS["spieler_schwung_%d" % _i] = (64, 64)
    for _team in TEAMS["kombi"]:
        BILD_MASS["spieler_%s_schwung_%d" % (_team["name"].lower(), _i)] = (64, 64)

# Der Buggy (seit 0.34.9, siehe FAHRZEUG): leer, mit Fahrer und mit einem
# Fahrer im Helm seiner Mannschaft. Schaut wie jede Figur nach +x.
BILD_MASS["buggy"] = (64, 64)
BILD_MASS["buggy_fahrer"] = (64, 64)
BILD_MASS["buggy_schatten"] = (64, 64)
BILD_MASS["buggy_wrack"] = (64, 64)
for _team in TEAMS["kombi"]:
    BILD_MASS["buggy_%s_fahrer" % _team["name"].lower()] = (64, 64)

# Was der Spieler zu Beginn auf den Plaetzen 1 bis 6 traegt.
#
# Das Brecheisen steht **nicht** mehr darin. Es liegt auf einer eigenen
# Taste und ist damit immer da, ohne einen Platz zu belegen - siehe
# NAHKAMPF. Ein Werkzeug, das man im Gedraenge braucht, sollte keinen
# Waffenwechsel kosten.
HOTBAR = ["repetierer", "sturm", "schrot", "scharf", "lmg", "granate",
          "rauch", "molotov", "blend", "c4"]

# So viele Plaetze kann die Hotbar hoechstens haben. Es sind die Tasten 1
# bis 9 - mehr Plaetze sind keine Auswahl mehr, sondern eine Suche. Wer
# mehr Waffen will, als hier hineinpassen, spielt mit Loadouts: zwei
# Waffen und eine Wurfwaffe, und die Entscheidung faellt vor der Runde.
HOTBAR_PLAETZE = 10

# ══════════════════════════════════════════════════ AUSRUESTUNG
#
# Ein Loadout ist zwei Waffen und eine Wurfwaffe. Das Brecheisen steht
# bewusst nicht drin: es liegt auf F und ist immer da. Wer sich also
# ausruestet, entscheidet ueber drei Plaetze, nicht ueber sechs - das ist
# eine Entscheidung, die man noch ueberblickt, und sie kostet etwas.
#
# Der Gastgeber entscheidet, ob Loadouts ueberhaupt gelten:
#
#   "eigenes"   jeder traegt sein gewaehltes Loadout
#   "alles"     jeder hat alles, wie bisher
#
# Beides muss es geben. "Alles" ist die Runde, in der man einfach spielt;
# "eigenes" ist die, in der die Wahl der Waffe eine Wahl ist.
LOADOUT = dict(
    plaetze=3,                # so viele Loadouts kann man sich anlegen
    waffen=2,                 # so viele Waffen je Loadout
    wuerfe=1,                 # so viele Wurfwaffen je Loadout
    # Woraus gewaehlt werden darf. Bewusst als eigene Listen und nicht
    # aus WAFFEN abgeleitet: was waehlbar ist, ist eine Spielentscheidung
    # und nicht dasselbe wie das, was es gibt.
    auswahl_waffen=("repetierer", "sturm", "schrot", "scharf", "lmg"),
    auswahl_wuerfe=("granate", "rauch", "molotov", "blend", "c4"),
    # Womit ein neues Loadout vorbelegt wird. Drei Stueck, damit man nach
    # dem ersten Anmelden gleich drei brauchbare Saetze hat und nicht vor
    # drei leeren Plaetzen sitzt.
    vorlagen=(
        dict(name="STURM", waffen=("sturm", "schrot"), wuerfe=("granate",)),
        dict(name="JÄGER", waffen=("scharf", "repetierer"), wuerfe=("rauch",)),
        dict(name="NAHKAMPF", waffen=("schrot", "sturm"), wuerfe=("rauch",)),
    ),
    namenslaenge=12,
)

# ══════════════════════════════════════════════════ ZAHLEN, DIE MITLAUFEN
#
# Was von einer Runde festgehalten wird. Eine Liste an genau einer Stelle,
# damit die Statistik, die Siegtafel und der Abgleich mit dem Server
# dieselben Namen benutzen - drei Stellen mit je eigener Schreibweise
# waeren der sichere Weg in Zahlen, die nicht zueinander passen.
#
# **Nur harmlose Zahlen.** Was hier steht, entsteht im Spiel und sagt
# nichts ueber den Menschen davor: keine Adressen, keine Geraete, keine
# Zeiten, an denen jemand am Rechner sass. Ein Name, den man sich selbst
# gibt, und was die Figur getan hat.
WERTE = (
    # (Schluessel, Aufschrift, Art)
    #   "summe"   wird ueber Runden addiert
    #   "bestes"  nur der Hoechstwert zaehlt
    ("abschuesse",    "ABSCHÜSSE",        "summe"),     # Spieler
    ("gegner_abschuesse", "ZOMBIES",      "summe"),     # seit 0.31
    ("boss_abschuesse", "BOSSE",          "summe"),
    ("tode",          "TODE",             "summe"),
    ("hilfen",        "AUFGEHOLFEN",      "summe"),
    ("schaden",       "SCHADEN",          "summe"),
    ("schaden_ein",   "EINGESTECKT",      "summe"),
    ("schuesse",      "SCHÜSSE",          "summe"),
    ("treffer",       "TREFFER",          "summe"),
    # Getrennt nach Ziel (seit 0.31): ein Treffer auf einen Spieler oder
    # auf einen Zombie. Das geht in jeder Spielart, auch in PVPVE.
    ("treffer_spieler", "TREFFER SPIELER", "summe"),
    ("treffer_gegner", "TREFFER ZOMBIES",  "summe"),
    # Und nach der Art der Runde (MODUS_ART): Schuesse und Treffer in
    # PVP-Runden und in PVE-Runden. PVPVE steht in keinem von beiden -
    # dort laesst sich ein Schuss keiner Seite zuordnen; dafuer gibt es
    # die Trennung nach Ziel oben.
    ("schuesse_pvp",  "SCHÜSSE PVP",      "summe"),
    ("treffer_pvp",   "TREFFER PVP",      "summe"),
    ("schuesse_pve",  "SCHÜSSE PVE",      "summe"),
    ("treffer_pve",   "TREFFER PVE",      "summe"),
    ("kopftreffer",   "NAHKAMPFTREFFER",  "summe"),
    ("granaten",      "GRANATEN",         "summe"),
    ("rauchwolken",   "RAUCHWOLKEN",      "summe"),
    ("medkits",       "MEDKITS",          "summe"),
    ("beute",         "AUFGESAMMELT",     "summe"),
    ("strecke",       "GELAUFEN",         "summe"),
    ("stuerze",       "STÜRZE",           "summe"),
    ("zonenzeit",     "IM KREIS",         "summe"),
    ("runden",        "RUNDEN",           "summe"),
    # Runden, die vor ihrem Ende abbrachen (Fenster zu, Verbindung weg,
    # Gastgeber beendet). Sie werden hochgeladen, zaehlen aber nirgends
    # sonst mit - sonst stimmte "Abschuesse je Runde" nicht mehr.
    ("abgebrochen",   "ABGEBROCHEN",      "summe"),
    ("siege",         "SIEGE",            "summe"),
    ("spielzeit",     "SPIELZEIT",        "summe"),
    ("serie",         "BESTE SERIE",      "bestes"),
    ("abschuesse_r",  "BESTE RUNDE",      "bestes"),
    ("mvp_punkte",    "MVP-PUNKTE",       "summe"),
    ("mvp_auszeichnungen", "MVP-RUNDEN",   "summe"),
)

# Welche Spielart zu welcher Seite der Statistik gehoert (WERTE, *_pvp
# und *_pve). PVPVE ist beides und darum keines.
MODUS_ART = {"pvp": "pvp", "team": "pvp", "versus": "pvp", "huegel": "pvp",
             "pve": "pve", "pvpve": "pvpve"}

# Je Waffe wird getrennt gezaehlt, sonst laesst sich nie sagen, womit
# jemand wirklich spielt. Genau das braucht die Siegtafel spaeter fuer
# das Zeichen der meistbenutzten Waffe.
WAFFEN_WERTE = ("schuesse", "treffer", "abschuesse")

KONTO = dict(
    # So oft versucht das Spiel, sein Journal loszuwerden. Nicht oefter:
    # ein Abgleich, der nichts zu tun hat, kostet trotzdem eine Anfrage.
    abgleich_takt=45.0,
    journal_hoechstens=400,   # so viele Runden warten hoechstens
    # Wie lange ein fehlgeschlagener Versuch Ruhe gibt, damit ein Server,
    # der gerade nicht mag, nicht jede Sekunde neu gefragt wird.
    ruhe_nach_fehler=30.0,
)

# Der Schlag mit dem Brecheisen, jederzeit auf einer eigenen Taste.
#
# Die Waffe selbst bleibt in WAFFEN stehen: von dort kommen Schaden,
# Reichweite, Kegel und Schwungdauer. Was sich aendert, ist nur, wie man
# sie einsetzt - man waehlt sie nicht mehr aus, man schlaegt.
#
# **Gehalten wird sie nie sichtbar.** Waehrend des Schlags verschwindet
# die gewaehlte Waffe aus der Hand, und man sieht allein die Bewegung des
# Eisens; danach ist sie wieder da. Eine Figur, die dauerhaft ein
# Brecheisen traegt, waere eine Luege - sie traegt ein Gewehr.
NAHKAMPF = dict(
    waffe="brecheisen",       # welcher Eintrag aus WAFFEN den Schlag macht
    sperrt_feuer=True,        # waehrend des Schwungs wird nicht geschossen
    # So lange bleibt das Eisen nach dem Schwung noch in der Hand (seit
    # 0.32.8, gemeldet: "die Waffe soll frueher versteckt werden - gerade
    # sieht es aus, als haette man sie noch"). Der Schwung allein dauert
    # 0.26 s; mit dem Nachhalten sieht man ihn auch, wenn man nicht
    # gerade hinschaut.
    nachhalten=0.14,
)

# Rauchgranate: eine Wand, durch die niemand durchsieht - auch nicht von
# der Ebene darueber. Sie macht keinen Schaden, sie nimmt nur die Sicht.
#
# **Wie sie entsteht.** Nicht Block fuer Block gewuerfelt - das ergibt
# Rauschen, keine Wolke. Statt dessen ein glattes Dichtefeld: ein grobes
# Zufallsgitter, dazwischen weich ueberblendet, mal abfallend zum Rand hin.
# Das Feld wird dann in wenige Tonstufen zerlegt, und die Kanten liegen auf
# dem Pixelraster des Spiels. Dadurch bleibt es Pixel-Art und sieht
# trotzdem nach Rauch aus statt nach Konfetti.
#
# **Volumen** kommt aus dem Gefaelle des Feldes: wo die Wolke zum Licht hin
# dichter wird, ist sie hell, auf der Gegenseite dunkel. Licht von oben
# links, wie ueberall sonst im Spiel.
# Die Brandflaeche eines Molotow.
#
# Sie liegt auf **einer** Ebene und wirkt nur dort. Das ist keine
# Vereinfachung, sondern die Regel: Feuer auf Deck 2 brennt nicht durch
# den Boden auf Deck 1, und wer eine Etage tiefer steht, ist in
# Sicherheit. Faellt der Molotow selbst durch ein Loch, zerbricht er
# unten - dann brennt es eben dort.
#
# Der Schaden laeuft je Sekunde und nicht in Stufen: wer hindurchhechtet,
# soll dafuer bezahlen, aber weiterleben; wer stehenbleibt, nicht.
FEUER = dict(
    radius=62.0,              # so weit reicht die Flaeche
    dauer=7.5,                # so lange brennt sie
    aufbau=0.35,              # Sekunden, bis sie voll brennt
    abbau=1.6,                # Sekunden, in denen sie herunterbrennt
    schaden=34.0,             # Schaden je Sekunde in der Mitte
    rand_anteil=0.45,         # so viel davon ganz aussen
    korn=3,                   # Kantenlaenge eines Bildpunkts
    gitter=13.0,              # Maschenweite des Zufallsgitters
    schwelle=0.34,            # ab dieser Dichte brennt ueberhaupt etwas
    zunge=1.9,                # wie schnell die Flammen zuengeln
    # Von aussen nach innen: dunkles Glimmen, Rot, Orange, heller Kern.
    toene=((84, 22, 10), (172, 54, 16), (230, 122, 26), (250, 192, 92)),
    funken=2.0,               # Funken je Sekunde und Flaeche
    brandfleck=True,          # hinterlaesst einen Fleck, wenn es aus ist
)

# Die Minikarte oben links (minikarte.py), ein Versuch. Groesse in
# Spielpixeln: hoechstens so breit und hoch, die Seiten wie die Karte.
MINIKARTE = dict(
    an=True,
    breite=84,
    hoehe=56,
    oben=8,
    links=8,
    # Seit 0.34.10: der Kreis steht immer darauf, auch auf einer anderen
    # Ebene, und nie kleiner als dieser Radius in Pixeln - auf STAUBTAL
    # waere er sonst ein einzelner Punkt.
    kreis_mindest=3,
    # Die Buggys, als laengliches Zeichen in Fahrtrichtung (Pixel).
    buggy_laenge=5,
    buggy_breite=2.5,
)

# Spielerkosmetik: eigener Ton und eigenes Bild fuer die Blendgranate.
#
# Ein erster Versuch, wie Spieler selbst etwas ins Spiel bringen. Gemacht
# wird es in der Kontoseite (KONTO.html, Reiter KOSMETIK), abgelegt im
# Konto auf dem Server (Tabelle `kosmetik`, docs/KONTO.md 5.6), verteilt
# in der Lobby an alle Mitspieler (spielerkosmetik.py). Was hier steht,
# prueft das Spiel bei **jedem** Paket - auch bei dem, das ein anderer
# Rechner schickt. Eine veraenderte Kontoseite kommt damit nicht weiter
# als die echte.
SPIELERKOSMETIK = dict(
    ton_min=1.0,            # Sekunden. Kuerzer geht nicht: ein Klick ist kein Knall
    ton_max=4.0,            # Sekunden. Laenger blockiert es den Ton der Runde
    ton_bytes=400_000,      # so gross darf die WAV-Datei hoechstens sein
    ton_raten=(11025, 16000, 22050, 32000, 44100, 48000),
    # Der Ton muss immer leiser werden. Die Kontoseite rechnet es vor; das
    # Spiel sorgt trotzdem selbst dafuer, damit kein Paket daran vorbei
    # kommt. Gefuehrt wird eine Obergrenze, die nie steigt und am Ende
    # null ist (spielerkosmetik.ton_ausklingen).
    ton_abschnitt=0.02,     # Sekunden je Abschnitt beim Pruefen
    ton_anlauf=0.12,        # so lange darf es am Anfang noch anschwellen
    ton_ausklang=1.0,       # ueber diesen Anteil faellt die Grenze auf null
    ton_abfall=0.95,        # so weit folgt die Grenze je Abschnitt nach unten
    bild_bytes=150_000,     # so gross darf das PNG hoechstens sein
    bild_max=320,           # so breit und hoch hoechstens
    # Wo und wie gross es im Weiss steht, steht im PNG selbst (ein
    # tEXt-Abschnitt "dustfront", gesetzt von der Kontoseite): Mitte x, y
    # als Anteil am Bild, Hoehe h als Anteil an der Bildhoehe. Fehlt er,
    # fuellt das Bild den ganzen Schirm. Was darin steht, wird auf diese
    # Bereiche gekappt.
    lage_xy=(-0.5, 1.5),
    lage_h=(0.05, 4.0),
    teil=8000,              # Zeichen je Netzmeldung
    teile_je_schritt=2,     # so viele Teile gehen je Schritt hinaus
    teile_max=100,          # mehr Teile hat kein gueltiges Paket (groesstes: 92)
)

# Die Blendgranate.
#
# **Sie unterscheidet keine Mannschaften.** Wer hinsieht, ist geblendet -
# die eigenen Leute, man selbst, jeder. Das ist ausdruecklich so gewollt
# und nicht vergessen: eine Blendgranate, die nur Gegner trifft, ist
# keine Entscheidung mehr, sondern ein Knopf.
#
# Wie stark es trifft, rechnet **jeder Rechner fuer sich** aus der Lage
# des Blitzes. Nichts davon wird uebertragen, und darum kann auch nichts
# auseinanderlaufen: gleiche Lage, gleiche Rechnung, gleiches Ergebnis.
# Der Gastgeber entscheidet hier nichts - es ist eine Frage des Bildes
# und nicht des Spiels.
#
# Drei Dinge zaehlen, und alle drei kann man im Gefecht lernen:
#
#   Ebene       Ein Blitz auf einer anderen Etage blendet nicht.
#   Sicht       Steht eine Wand dazwischen, passiert nichts. Wegdrehen
#               hilft nicht ganz, aber deutlich (siehe `abgewandt`).
#   Entfernung  Nah voll, ab `weite` gar nicht.
BLENDEN = dict(
    # Seit 0.32 eine Waffe fuer die kurze Distanz (gemeldet: "soll wirklich
    # eher fuer Nahdistanz nutzbar sein"). Vorher reichte das Weiss bis
    # rund 250 Pixel, jetzt bis rund 150 - etwa fuenf Kacheln.
    weite=200.0,          # ab hier blendet sie nicht mehr (vorher 360)
    nah=70.0,             # bis hierhin blendet sie voll (vorher 90)
    # Ganz nah blendet sie auch den, der wegschaut. Man dreht sich im
    # Gefecht staendig; ob ein Blitz direkt neben einem wirkt, hing sonst
    # davon ab, wohin die Maus gerade zeigte - Glueck statt Spiel.
    rundum=64.0,          # so nah wirkt sie in jede Richtung (zwei Kacheln)
    dauer=2.6,            # so lange dauert die volle Blendung
    mindest=0.55,         # so lange mindestens, wenn sie ueberhaupt trifft
    # Ganz weiss und deckend: wer voll getroffen ist, sieht nichts mehr -
    # keine Welt, keine Anzeige. Gemeldet war, dass die alte Fassung
    # (90 % Deckkraft, leicht gelblich) zu durchsichtig und zu matt war.
    # Erst wenn die Blendung unter `deckend_ab` faellt, scheint das Bild
    # wieder durch. Ein schwacher Blitz (weit weg, weggedreht) kommt gar
    # nicht so hoch und bleibt darum durchsichtig.
    weiss=1.0,            # wie weiss das Bild wird, 0 bis 1
    deckend_ab=0.55,      # ab dieser Staerke ist nichts mehr zu sehen
    abklingen=1.8,        # je hoeher, desto schneller wird wieder klar
    abgewandt=0.35,       # so viel bleibt uebrig, wenn man weggedreht steht
    # Darunter kein Weiss, nur die Explosion in der Welt. Hoeher als
    # `abgewandt`: wer wegschaut, wird nicht geblendet - ausser innerhalb
    # von `rundum`. Bei Blick auf den Blitz endet das Weiss bei rund 150
    # Pixeln (nah + (1 - schwelle) * (weite - nah)).
    schwelle=0.4,
    glitzer_dauer=1.1,    # so lange leuchtet der Glitzer nach
    ring=1.3,             # Wucht des Druckrings
    kamera=2.5,           # Kameraschlag - weniger als bei der Granate
    blickwinkel=100.0,    # innerhalb dieses Kegels gilt man als hinsehend
    # Der Funke in der Welt: klein, hell, kurz. Aus der Entfernung soll
    # man ein Blitzen sehen und nicht eine Explosion.
    funke_dauer=0.22,
    funke_gross=13.0,
    ton_dauer=2.2,        # so lange klingt das Pfeifen im Ohr nach
    # Wie laut der Knall ist (seit 0.32.7, gemeldet: "deutlich leiser, wenn
    # man weiter weg ist oder nicht hinschaut - aber immer noch hoerbar").
    # Zur gewoehnlichen Entfernungsdaempfung (AUDIO) kommen zwei Faktoren:
    # bis `rundum` ist er voll; bis `ton_weite` sinkt er auf `ton_fern`,
    # und wer wegschaut, hoert ihn mit `ton_abgewandt`. Nie leiser als
    # `ton_mindest` - wer ihn ueberhaupt hoeren kann, soll ihn erkennen.
    ton_weite=500.0,
    ton_fern=0.45,
    ton_abgewandt=0.5,
    ton_mindest=0.12,
)

# ══════════════════════════════════════════════════ SKINS
#
# Vorbereitung fuer das, was spaeter kommt: austauschbare Bilder und
# Klaenge je Gegenstand, ohne dass eine Zeile Code sich aendert.
#
# Der Griff dazu ist eine **Rolle**. Der Code fragt nie nach einem
# Dateinamen, sondern nach einer Rolle - "das Bild, das fliegt", "der
# Knall" -, und diese Tabelle sagt, welcher Name gerade dahintersteht.
# Eine Skin aendert nur die Tabelle.
#
# Warum nicht einfach die Datei austauschen? Weil dann alle dieselbe
# Blendgranate haetten. Eine Skin gehoert einem Spieler, und zwei Spieler
# in derselben Runde sollen verschiedene tragen koennen - genau dafuer
# muss der Name zur Laufzeit umschaltbar sein und nicht im Ordner liegen.
SKIN_ROLLEN = {
    "blend_flug": "blendgranate",      # das Bild, das durch die Luft geht
    "blend_hand": "spieler_blend",     # die Figur, die sie traegt
    "blend_symbol": "waffe_blend",     # das Zeichen in der Hotbar
    "blend_knall": "blend",            # Klang beim Zuenden
    "blend_pfeifen": "blend_pfeifen",  # Klang danach im Ohr
    "molotov_flug": "molotov",
    "molotov_hand": "spieler_molotov",
    "molotov_symbol": "waffe_molotov",
    "molotov_knall": "molotov",
    # Die Figur selbst. `figur` ist die Gestalt ohne Waffe, `boden` die
    # liegende. Die Figuren mit Waffe entstehen daraus und aus der
    # Waffenrolle - deshalb steht hier nicht jede Kombination einzeln.
    "figur": "spieler",
    "figur_boden": "spieler_boden",
}

# Und je Schusswaffe dieselben drei Rollen. Als Schleife und nicht von
# Hand, damit eine neue Waffe nicht drei vergessene Zeilen bedeutet.
for _w in ("repetierer", "sturm", "schrot", "scharf", "lmg", "granate",
           "rauch", "brecheisen", "rakete"):
    SKIN_ROLLEN["%s_hand" % _w] = "spieler_%s" % _w
    SKIN_ROLLEN["%s_symbol" % _w] = "waffe_%s" % _w
    SKIN_ROLLEN["%s_knall" % _w] = ("schuss_%s" % _w
                                    if "schuss_%s" % _w in KLANG_NAMEN
                                    else "schuss")

# Seltenheitsstufen. **Noch nicht eingebaut** - sie stehen hier, weil
# die Farben an einer Stelle gehoeren und nicht in einem Entwurf.
#
# Die Reihenfolge ist die Reihenfolge: je weiter hinten, desto seltener.
# Die Wahrscheinlichkeiten sind ein Vorschlag und keine Zusage.
SELTENHEIT = (
    dict(name="GEBRAUCHT",  farbe=(132, 124, 110), anteil=0.60),
    dict(name="INSTAND",    farbe=(96, 150, 196),  anteil=0.25),
    dict(name="SELTEN",     farbe=(140, 108, 208), anteil=0.10),
    dict(name="RAR",        farbe=(206, 84, 168),  anteil=0.04),
    dict(name="LEGENDE",    farbe=(232, 168, 56),  anteil=0.01),
)

# Was gerade gewaehlt ist. Leer heisst: die Vorgabe aus SKIN_ROLLEN.
SKIN_WAHL: dict[str, str] = {}


def skin(rolle: str) -> str:
    """Welcher Name gerade hinter einer Rolle steht."""
    return SKIN_WAHL.get(rolle) or SKIN_ROLLEN.get(rolle, rolle)


def skin_setzen(rolle: str, name: str) -> bool:
    """Eine Rolle auf einen anderen Namen legen. False, wenn unbekannt."""
    if rolle not in SKIN_ROLLEN:
        return False
    if name:
        SKIN_WAHL[rolle] = str(name)
    else:
        SKIN_WAHL.pop(rolle, None)
    return True


def skin_zuruecksetzen() -> None:
    SKIN_WAHL.clear()


# Die Zielerfassung des Raketenwerfers.
#
# Rechte Maustaste halten, waehrend man auf jemanden zeigt. Ein Kreis
# zieht sich um ihn zusammen; ist er ganz zu, wechselt er die Farbe und
# die Erfassung steht. Danach lenkt die Rakete - aber sie kann keine
# engen Kurven, und daran scheitert sie an jeder Ecke.
#
# **Nach unten nur ueber einem Abgrund.** Wer eine Etage tiefer steht,
# laesst sich nur dann erfassen, wenn zwischen ihm und einem selbst ein
# Loch im Boden ist - man muss ihn ja sehen koennen. Die Rakete wechselt
# dann im Flug sauber die Ebene. Ohne Erfassung fliegt sie schlicht
# darueber hinweg, wie alles andere auch.
#
# Und: **der Erfasste merkt es.** Erst ein Zeichen, dass da jemand zielt,
# dann ein anderes, wenn die Rakete unterwegs ist. Eine Waffe, die ohne
# Vorwarnung um die Ecke kommt, waere keine Entscheidung mehr.
ERFASSUNG = dict(
    dauer=1.0,            # so lange muss man halten
    weite=900.0,          # weiter geht es nicht
    winkel=14.0,          # so nah muss der Zeiger am Ziel sein, in Grad
    halten=0.45,          # so lange haelt die Erfassung ohne Sicht
    ring_gross=34.0,      # Durchmesser des Kreises am Anfang
    ring_klein=13.0,      # und am Ende
    farbe=(236, 178, 62),
    farbe_fest=(96, 232, 150),
    warnung=(236, 96, 62),        # Rand beim Erfassten
    warnung_scharf=(255, 64, 40),  # und wenn die Rakete fliegt
)

RAUCH = dict(
    radius=78.0,              # so weit reicht die Wand in Weltpixeln
    dauer=14.0,               # so lange steht sie
    aufbau=0.9,               # Sekunden, bis sie dicht ist
    abbau=2.4,                # Sekunden, in denen sie sich wieder aufloest
    korn=3,                   # Kantenlaenge eines Bildpunkts der Wolke
    gitter=17.0,              # Maschenweite des Zufallsgitters in Pixeln
    lagen=2,                  # so viele Gitter uebereinander (grob bis fein)
    kern=0.70,                # bis hierhin deckt sie voll und verbirgt
    schwelle=0.30,            # ab dieser Dichte steht ueberhaupt Rauch
    licht=(-1.0, -1.0),       # woher das Licht kommt, wie im ganzen Spiel
    licht_weite=5.0,          # ueber so viele Pixel wird das Gefaelle gemessen
    # Helligkeit aus zwei Anteilen: wo die Wolke dick ist, streut sie
    # mehr Licht und ist heller - das gibt ihr den Koerper. Das Gefaelle
    # zum Licht hin kommt nur als leichte Kante dazu. Umgekehrt sah es
    # aus wie Gestein: harte Adern mit viel Kontrast.
    grund=0.20,               # Helligkeit am duennsten Rand
    dicke_hell=0.70,          # wie viel Helligkeit die Dicke dazugibt
    licht_staerke=1.1,        # wie stark das Gefaelle die Tonstufe verschiebt
    # Gedeckte Grautoene mit einem Stich ins Warme: reines Weiss steht in
    # einer Karte aus Rost und Braun wie ein Loch im Bild.
    toene=((206, 202, 195), (186, 182, 175), (166, 162, 156),
           (146, 143, 137), (126, 123, 118), (106, 104, 100),
           (88, 86, 83)),
    # Drei Stufen statt einer: eine einzige Kante zwischen deckend und
    # durchsichtig sieht man als gezeichneten Kreis, und das ist genau
    # das, was hier nicht sein soll.
    schichten=((0.70, 255), (0.86, 205), (1.30, 150)),
    # Rauch einer anderen Ebene muss anders aussehen, sonst weiss man im
    # Gefecht nicht, ob die Wand vor einem liegt oder eine Etage hoeher.
    fremde_ebene=0.55,        # so viel Deckkraft behaelt er dort
    puffer=24,                # so viele fertige Wolkenbilder werden gehalten
)

# Kurze Aufschrift ueber aufgesammelter Beute. Ohne sie verschwindet eine
# Munitionskiste im Vorbeilaufen einfach, und man weiss nicht, ob sie
# ueberhaupt gewirkt hat.
BEUTE_TEXTE = {
    "medkit":   ("+ MEDKIT", C_TEAL),
    "munition": ("+ MUNITION", C_AMBER),
}

BEUTE_ZEIGEN = dict(
    dauer=0.95,               # so lange steht die Aufschrift
    steigt=22.0,              # so weit steigt sie in dieser Zeit
    funken=14,                # Partikel beim Aufheben
)

MEDKIT = dict(
    name="MEDKIT",
    heilt=45.0,
    je_welle=2,           # so viele werden pro Welle abgeworfen
    hoechstens=3,         # so viele kann man tragen
    dauer=0.8,            # Sekunden, die das Anlegen braucht
    # Waehrend des Anlegens hat man das Medkit in der Hand und nicht die
    # Waffe - also geht man langsamer und schiesst nicht. Das ist der
    # Preis dafuer, dass es mitten im Gefecht geht.
    tempo=0.55,
)

# ══════════════════════════════════════════════════ INHALTE: Gegner

# Alle Gegnertempi seit 0.27 mit 0,85 malgenommen - im selben Verhaeltnis,
# in dem der Spieler langsamer wurde. So bleibt, was vorher galt: der
# Laeufer holt einen gehenden Spieler nicht ein, der Renner schon.
GEGNER = {
    "laeufer": dict(
        name="LÄUFER",
        leben=44.0,
        radius=9.0,
        tempo=63.0,
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
        leben=95.0,
        # 0.34.1: 17 -> 15. Das Bild bleibt gross (44 px), aber der Koerper
        # muss unter einer halben Kachel bleiben: mit 17 (34 px breit) passte
        # der Brecher durch keine einzige Tuer und keinen Aufzug (32 px) und
        # kam auf STAUBTAL nie auf ein Plateau.
        radius=15.0,
        tempo=44.0,
        beschleunigung=380.0,
        schaden=22.0,
        schlagtakt=1.3,
        reichweite=22.0,
        sicht=340.0,
        bild="gegner_brecher",
        punkte=30,
    ),
    # ── Die drei neuen. Jeder stellt eine andere Frage.
    #
    # Laeufer und Brecher fragen dieselbe: "kannst du treffen, bevor er
    # da ist?" Zwei Gegner, eine Frage - darum wurde eine Welle ab der
    # dritten Minute langweilig. Die folgenden fragen etwas anderes, und
    # darum aendert sich das Spiel, wenn sie dazukommen.
    "renner": dict(
        name="RENNER",
        leben=26.0,              # ein Schrotschuss, ein Treffer mit dem Gewehr
        radius=8.0,
        tempo=118.0,             # schneller als ein laufender Spieler (108)
        beschleunigung=900.0,
        schaden=7.0,
        schlagtakt=0.55,
        reichweite=16.0,
        sicht=420.0,
        bild="gegner_renner",
        punkte=15,
        # Frage: "kannst du dich noch umdrehen?" Stehenbleiben ist bei
        # ihm keine Stellung mehr, sondern ein Fehler.
    ),
    "speier": dict(
        name="SPEIER",
        leben=58.0,
        radius=10.0,
        tempo=34.0,              # langsam: er will gar nicht heran
        beschleunigung=300.0,
        schaden=14.0,            # Schaden des Spucks
        schlagtakt=2.4,
        reichweite=17.0,
        sicht=360.0,
        bild="gegner_speier",
        punkte=25,
        # Frage: "kommst du an ihn heran?" Er haelt Abstand und spuckt.
        # Wer in Deckung wartet, wartet vergeblich - er muss geholt werden.
        fern=dict(reichweite=230.0, halten=150.0, takt=2.4, tempo=250.0,
                  streuung=5.0, bild="speichel"),
    ),
    "blaeher": dict(
        name="BLÄHER",
        leben=90.0,
        radius=13.0,
        tempo=39.0,
        beschleunigung=300.0,
        schaden=0.0,             # Er schlaegt nicht. Er kommt nur naeher.
        schlagtakt=1.0,
        reichweite=20.0,
        sicht=340.0,
        bild="gegner_blaeher",
        punkte=25,
        # Frage: "wo steht ihr gerade?" Er platzt, wenn er stirbt - also
        # auch dann, wenn man ihn rechtzeitig erledigt, nur eben weiter
        # weg. Zusammenstehen wird dadurch teuer.
        platzt=dict(radius=76.0, schaden=46.0, zuendet=True),
    ),
}

# ══════════════════════════════════════════════════ INHALTE: Bosse
#
# Ein Boss ist ein Gegner mit drei Unterschieden: er hat sehr viel mehr
# Leben, er hat **eine** Faehigkeit, die man verstehen muss, und er steht
# oben im Bild mit Namen und Balken.
#
# Drei Stueck, und jeder zwingt zu etwas anderem:
#
#   KOLOSS        zwingt weg von ihm      (Nahkampf wird toedlich)
#   MUTTER        zwingt zu ihm hin       (Warten macht es schlimmer)
#   BRANDSTIFTER  zwingt in Bewegung      (Stehenbleiben wird toedlich)
#
# Mehr als einer davon zugleich waere Krach statt Druck - darum kommt
# je Bosswelle genau einer, reihum.
BOSSE = {
    "koloss": dict(
        name="KOLOSS",
        leben=1400.0,
        radius=22.0,
        tempo=38.0,               # langsamer als jeder Spieler. Mit Absicht.
        beschleunigung=260.0,
        schaden=40.0,
        schlagtakt=1.8,
        reichweite=30.0,
        sicht=600.0,
        bild="boss_koloss",
        punkte=400,
        # Der Stampfer: im Umkreis trifft es jeden, auch hinter Deckung.
        # Darum ist Weglaufen die Antwort und nicht eine Ecke.
        faehigkeit=dict(art="stampfer", takt=4.5, vorlauf=0.9,
                        radius=104.0, schaden=34.0, ruckeln=2.6),
        # Er faellt nicht um, wenn man ihn trifft - sonst schoebe ihn ein
        # Sturmgewehr durch die halbe Karte.
        unverschiebbar=True,
    ),
    "mutter": dict(
        name="MUTTER",
        leben=900.0,
        radius=18.0,
        tempo=50.0,
        beschleunigung=340.0,
        schaden=18.0,
        schlagtakt=1.2,
        reichweite=24.0,
        sicht=520.0,
        bild="boss_mutter",
        punkte=400,
        # Sie ruft nach. Wer sie stehenlaesst und die Brut abarbeitet,
        # arbeitet gegen einen Hahn, den er nicht zudreht.
        faehigkeit=dict(art="brut", takt=5.0, vorlauf=0.6,
                        anzahl=3, was="renner", hoechstens=14, streuung=40.0),
        unverschiebbar=False,
    ),
    "brandstifter": dict(
        name="BRANDSTIFTER",
        leben=1050.0,
        radius=17.0,
        tempo=54.0,
        beschleunigung=380.0,
        schaden=16.0,
        schlagtakt=1.4,
        reichweite=22.0,
        sicht=560.0,
        bild="boss_brandstifter",
        punkte=400,
        # Er wirft Feuer dorthin, wo jemand steht. Das nimmt Stellungen
        # weg, statt Leben - und genau deshalb wirkt es.
        faehigkeit=dict(art="brand", takt=3.6, vorlauf=0.7,
                        radius=58.0, wurfweite=300.0, vorhalt=0.55),
        unverschiebbar=False,
    ),
}

# Die Reihenfolge, in der die Bosse kommen. Reihum, damit man den
# naechsten kennt und sich darauf einrichten kann - eine Ueberraschung
# ist beim ersten Mal gut und beim fuenften Mal nur noch Zufall.
BOSS_FOLGE = ("koloss", "mutter", "brandstifter")


def gegner_daten(art: str) -> dict:
    """Die Werte eines Gegners, egal ob normaler oder Boss.

    Es gibt zwei Tabellen, weil ein Boss etwas anderes ist als ein
    Laeufer und das auch beim Lesen so aussehen soll. Fuer alles, was
    danach kommt - Klasse, Netz, Anzeige -, ist es aber ein Gegner wie
    jeder andere, und darum fragt dort niemand, aus welcher Tabelle er
    stammt.
    """
    if art in GEGNER:
        return GEGNER[art]
    if art in BOSSE:
        return BOSSE[art]
    if art in UEBUNG:
        return UEBUNG[art]
    return GEGNER["laeufer"]


def ist_boss(art: str) -> bool:
    return art in BOSSE

# Was nur im Schiessstand der Lobby steht. Eine eigene Tabelle und nicht
# GEGNER, damit sie nie in eine Welle geraet und keine Pruefung, die ueber
# "alle Gegner" geht, eine Puppe mitzaehlt, die sich nicht bewegt.
# Seit 0.34.43: alle Gegner und Bosse laufen mit BEWEGUNG["lauf"] (siehe dort).
for _g in list(GEGNER.values()) + list(BOSSE.values()):
    _g["tempo"] = _g["tempo"] * BEWEGUNG["lauf"]

UEBUNG = {
    "puppe": dict(
        name="PUPPE",
        leben=500.0,
        radius=11.0,
        tempo=0.0,
        beschleunigung=0.0,
        schaden=0.0,
        schlagtakt=99.0,
        reichweite=0.0,
        sicht=0.0,
        bild="puppe",
        punkte=0,
        unverschiebbar=True,
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
