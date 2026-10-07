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
SPIELER = dict(
    radius=9.0,
    tempo=108.0,              # Pixel pro Sekunde bei vollem Lauf (war 132)
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
    "blend",                # der Knall der Blendgranate
    "rakete",               # der Abschuss
    "erfasst",              # Ton, wenn die Erfassung steht
    "blend_pfeifen",        # das Pfeifen danach im Ohr
    "speien",               # der Spuck des Speiers
    "boss_ansage",          # ein Boss kuendigt an, was er gleich tut
    "dash",                 # der kurze Stoss
    "ruf",                  # wer am Boden liegt, ruft nach Hilfe

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
C4 = dict(wurfweite=76.0, wurftempo=260.0, ladezeit=5.0,
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
    massstab_schwelle=0.02,   # ab so viel Abweichung wird ein Wesen im Sturz
                              # ueberhaupt umgerechnet
)

# Die Felswand zwischen einem Plateau und dem Boden darunter (render.py,
# Renderer.klippen). Ein Plateau ist ein Felsblock, kein schwebender
# Deckel - bis 0.31 hing er versetzt und blass ueber seinem Sockel.
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
LEER, BODEN, GITTER, WAND, KISTE, TREPPE_HOCH, TREPPE_RUNTER, LUKE, \
    AUFZUG_HOCH, AUFZUG_RUNTER = range(10)

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
