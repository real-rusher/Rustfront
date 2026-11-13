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
    # Seit 0.34.135 1,3 mal so schnell (gewuenscht: "Spieler sind extrem langsam").
    tempo=108.0 * BEWEGUNG["lauf"] * 1.3,
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

# Beim Zeichnen dreht sich ein Wesen erst, wenn sein Blick sich um so viele
# Grad geaendert hat (seit 0.34.96, render._gezeigter_winkel) - kleiner als
# eine Drehstufe der Bilder (3 Grad), damit Zielen genau bleibt.
# Gedrehte Bilder (seit 0.34.141, core.drehen_mittig): pygame.transform.rotate
# liefert je nach Winkel gerade oder ungerade Breiten, und die Mitte des Bildes
# lag dann mal auf, mal zwischen zwei Pixeln - beim Drehen sprang alles um einen
# halben Spielpixel hin und her (gemeldet: "Fahrzeuge zittern stark"). Jetzt
# wird ein `fein`-fach vergroessertes Bild gedreht und genau um die Mitte herum
# wieder abgetastet: ungerade Breite und Hoehe, die Mitte immer auf demselben
# Pixel. `an`: aus = wie vor 0.34.141.
DREHEN = dict(an=True, fein=4)

# BESTE QUALITAET (core._welt_hoch_auflegen): die Anzeige wird in so vielen
# Stuecken hochgezogen, wie sie zusammenhaengende Flecken hat; sind es mehr,
# auf einmal das ganze Bild (seit 0.34.141).
ANZEIGE_STUECKE = 400

FIGUR_DREH_RUHE = 2.6

# Was hoch ueber allem fliegt (seit 0.34.96, die Spaehdrohne): so viele
# Pixel ueber ihrem Schatten, so viel groesser, Schatten so versetzt.
HOCH_OBEN = dict(hoehe=26, gross=1.25, schatten=(6, 10))

# Das Zielfernrohr (seit 0.34.96, Waffen mit scope=True): mit der rechten
# Maustaste laeuft das Bild weit zum Mauszeiger (zug, hoechstens weite),
# und um den Zeiger ist ein Kreis von `linse` Weltpixeln klar - auch im
# Nebel, aber nur bis zum Zeiger: die erste Mauer oder ein Fahrzeug auf
# dem Weg dorthin haelt den Blick an.
SCOPE = dict(zug=0.82, weite=1500.0, linse=72.0, ring=(36, 30, 24), fadenkreuz=(214, 64, 48))

# Sichtweite im Gefecht (Mausrad, seit 0.30). 1 ist das normale Bild; mehr
# heisst: mehr Welt im Bild, kleiner gezeichnet. Alles ausserhalb des
# normalen Bildes liegt im **Nebel**: man sieht das Gelaende gedaempft,
# aber keine Wesen - keine Gegner, keine Mitspieler, keine Granaten. Ein
# weiterer Blick ist damit Ueberblick, kein Vorteil.
# Aufs Fenster bringen (seit 0.34.77, core.App.viewport_rechnen): liegt das
# Fenster so nah an einem ganzen Vielfachen von 640 x 360, rastet die
# Vergroesserung darauf ein - der Rest wird abgeschnitten oder bleibt als
# schmaler Rand. Bei krummen Faktoren (1919 Pixel breit = 2,998) wurden
# sonst manche Pixelreihen doppelt statt dreifach gezeigt, an festen
# Stellen des Bildschirms, und alles, was darunter durchlief, veraenderte
# beim Umschauen seine Textur (gemeldet mit zwei Bildern).
FENSTER_EINRASTEN = 0.04

# Abtastraster fuer alles, was skaliert aufs Bild kommt (seit 0.34.77,
# render.Renderer._tiefen_plan und Gefecht._zoom_zeichnen): Breiten, die
# von der genauen um so viele Pixel abweichen duerfen, damit ein kleines
# Raster passt, und das groesste Raster in Weltpixeln. Groesser heisst:
# die Hilfsflaeche wird um so viel breiter.
TIEFENRASTER = dict(
    versuche=(0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6),
    groesstes=48,
    hoch_rand=2,              # BESTE QUALITAET: so viele Pixel Rand rund um die Leinwand (0.34.141)
)

ZOOM = dict(
    stufen=(0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75),
    start=1.0,
    weich=12.0,               # wie schnell der Zoom nachzieht
    hoechst=2.0,              # so weit hinaus ohne besonderes Fahrzeug
    # Bis zu diesem Zoom ist alles klar, erst dahinter liegt der Nebel
    # (seit 0.34.95; vorher 1, also schon direkt hinter dem normalen Bild;
    # seit 0.34.135 1,75 statt 1,5 - gewuenscht: "der Nebel soll noch etwas
    # zurueckgehen").
    klar=1.75,
    # Fahrzeuge, die weiter sehen (seit 0.34.135): Art -> (hoechster Zoom,
    # klar bis, wann). Der Funkwagen sieht aufgebaut seinen ganzen Peilkreis
    # (470 px Radius, also 940 px hoch: 2,75 * 360 = 990), der Tragschrauber
    # in der Luft weiter. Faellt der Zustand weg, springt der Zoom auf die
    # hoechste erlaubte Stufe zurueck; kommt er, zoomt das Bild einmal hinaus.
    fahrzeug={"funkwagen": (2.75, 2.75, "aufgebaut"), "tragschrauber": (2.5, 2.25, "luft")},
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

# Grosse Bilder fuer das Menue AUSRUESTUNG (seit 0.34.82): je Waffe oder
# Gegenstand eine Datei assets/menue/<kennung>.jpg, gemacht mit den Prompts
# aus docs/BILDPROMPTS.md. Fehlt eine, zeigt das Menue das Pixelbild.
MENUEBILDER = dict(
    ordner="menue",               # Unterordner von ASSETS["ordner"]
    endungen=(".jpg", ".png", ".webp"),
)

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
        # NPCs und Tiere im Testmodus (seit 0.34.60, testmodus.Bewohner).
        "zivil": "mensch",
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
    # Wasser und die Saetze gruen und stadt (seit 0.34.131, art_gelaende).
    "seicht":           (TILE, TILE),
    "seicht_2":         (TILE, TILE),
    "seicht_3":         (TILE, TILE),
    "wasser":           (TILE, TILE),
    "wasser_2":         (TILE, TILE),
    "wasser_3":         (TILE, TILE),
    "kanal":            (TILE, TILE),
    "kanal_2":          (TILE, TILE),
    "kanal_3":          (TILE, TILE),
    "gras":             (TILE, TILE),
    "gras_2":           (TILE, TILE),
    "gras_3":           (TILE, TILE),
    "gras_4":           (TILE, TILE),
    "feldstein":        (TILE, TILE),
    "moosfels":         (TILE, TILE),
    "moosfels_2":       (TILE, TILE),
    "moosfels_3":       (TILE, TILE),
    "baum":             (TILE, TILE),
    "feldweg":          (TILE, TILE),
    "feldweg_2":        (TILE, TILE),
    "feldweg_3":        (TILE, TILE),
    "feldweg_4":        (TILE, TILE),
    "ufer":             (TILE, TILE),
    "ufer_2":           (TILE, TILE),
    "ufer_3":           (TILE, TILE),
    "ufer_4":           (TILE, TILE),
    "wiese":            (TILE, TILE),
    "wiese_2":          (TILE, TILE),
    "wiese_3":          (TILE, TILE),
    "wiese_4":          (TILE, TILE),
    "steg":             (TILE, TILE),
    "steg_2":           (TILE, TILE),
    "asphalt":          (TILE, TILE),
    "asphalt_2":        (TILE, TILE),
    "asphalt_3":        (TILE, TILE),
    "asphalt_4":        (TILE, TILE),
    "schild_klasse":    (32, 32),       # das Schild des SCHILDTRAEGERS (seit 0.34.138)
    "hof":              (TILE, TILE),
    "hof_2":            (TILE, TILE),
    "hof_3":            (TILE, TILE),
    "hof_4":            (TILE, TILE),
    "ziegel":           (TILE, TILE),
    "beton":            (TILE, TILE),
    "beton_2":          (TILE, TILE),
    "beton_3":          (TILE, TILE),
    "truemmer":         (TILE, TILE),
    "truemmer_2":       (TILE, TILE),
    "truemmer_3":       (TILE, TILE),
    "wrack":            (TILE, TILE),
    "wrack_2":          (TILE, TILE),
    "wrack_3":          (TILE, TILE),
    "strasse":          (TILE, TILE),
    "strasse_2":        (TILE, TILE),
    "strasse_3":        (TILE, TILE),
    "strasse_4":        (TILE, TILE),
    "schutt":           (TILE, TILE),
    "schutt_2":         (TILE, TILE),
    "schutt_3":         (TILE, TILE),
    "schutt_4":         (TILE, TILE),
    "gehweg":           (TILE, TILE),
    "gehweg_2":         (TILE, TILE),
    "gehweg_3":         (TILE, TILE),
    "rasen":            (TILE, TILE),
    "rasen_2":          (TILE, TILE),
    "rasen_3":          (TILE, TILE),
    "rasen_4":          (TILE, TILE),
    "fliesen":          (TILE, TILE),
    "fliesen_2":        (TILE, TILE),
    "kasernenplatz":    (TILE, TILE),
    "kasernenplatz_2":  (TILE, TILE),
    "kasernenplatz_3":  (TILE, TILE),
    "kanal_seicht":     (TILE, TILE),
    "kanal_seicht_2":   (TILE, TILE),
    "kanal_seicht_3":   (TILE, TILE),
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
    "minirakete_flug":  (18, 8),    # Raketenbuendel im Flug (seit 0.34.64)
    "nagel_flug":       (9, 3),     # ein Nagel des Naglers im Flug (seit 0.34.66)
    "nagel_steckt":     (7, 3),     # und wo er stecken bleibt
    "wurfmesser_flug":  (13, 5),    # Wurfmesser im Flug und am Boden (seit 0.34.67)
    "speer_flug":       (30, 5),    # Speer im Flug und am Boden
    "schneeball_flug":  (7, 7),
    "gas_flug":         (9, 9),     # Gasgranate
    "laser_flug":       (14, 3),    # Spiegellaser (seit 0.34.68)
    "geschuetz_oben":   (20, 20),   # Selbstschussanlage (seit 0.34.69)
    "kanister":         (12, 16),
    "stacheldraht":     (64, 10),
    "sprengfalle_platte": (12, 12),
    "sprengfalle_draht": (10, 8),
    "sanitasche":       (12, 10),
    "kugelblitz_flug":  (15, 15),   # Kugelblitz
    "haftladung_flug":  (9, 9),     # Haftladung im Flug und klebend (seit 0.34.65)
    "emp_flug":         (9, 9),     # EMP-Granate im Flug (seit 0.34.65)
    "emp_flug_an":      (9, 9),     # ... mit Licht (Blinken, seit 0.34.67)
    "haftladung_flug_an": (9, 9),
    "nagel":            (5, 5),     # ein Kraehenfuss im Nagelfeld (seit 0.34.65)
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
    "feldstein_oben":   (TILE, TILE),
    "moosfels_oben":    (TILE, TILE),
    "moosfels_2_oben":  (TILE, TILE),
    "moosfels_3_oben":  (TILE, TILE),
    "baum_oben":        (22, 22),
    "ziegel_oben":      (TILE, TILE),
    "beton_oben":       (TILE, TILE),
    "beton_2_oben":     (TILE, TILE),
    "beton_3_oben":     (TILE, TILE),
    "truemmer_oben":    (26, 26),
    "truemmer_2_oben":  (26, 26),
    "truemmer_3_oben":  (26, 26),
    "wrack_oben":       (24, 30),
    "wrack_2_oben":     (24, 30),
    "wrack_3_oben":     (24, 30),
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
    "funk_durch",           # ein Funkspruch ist durch (seit 0.34.58)
    # Panzer und Panzerwagen (seit 0.34.59) - Platzhalter, bis es Aufnahmen gibt.
    "schuss_kanone",        # die Panzerkanone
    "schuss_bug_mg",        # das Bug-MG des Panzers
    "schuss_ring_mg",       # das MG im Ring des Panzerwagens
    "schuss_flak_kanone",   # der Flak-Vierling (seit 0.34.118)
    "flak_burst",           # eine Flakwolke platzt
    "fallschirm_riss",      # der Schirm eines Abwurfs reisst
    "absturz",              # ein Fahrzeug schlaegt nach dem Sturz auf
    "werfer_explosion",     # der Werfer geht hoch (seit 0.34.120)
    "bombe_ab",             # die Lunte der Schrottbombe wird gezuendet (seit 0.34.123)
    "bombe_fall",           # die zischende Lunte der fallenden Bombe
    "panzer_einschlag",     # die Granate der Kanone schlaegt ein
    "panzer_motor",         # Ketten und Motor, in einem Takt, solange er faehrt
    "panzerwagen_motor",
    "rammen",               # ein Fahrzeug rammt jemanden

    # Seit 0.34.72 (gemeldet: "Klaenge kannst du mal alle erzeugen"): die
    # Waffen aus dem Paket, Fahrzeuge und Ausruestung. Jeder hat einen
    # eigenen Platzhalter in audio.py, bis es Aufnahmen gibt.
    "schuss_revolver", "schuss_mp", "schuss_minigun", "schuss_panzerbuechse",
    "schuss_doppelflinte", "schuss_granatwerfer", "schuss_bolzer", "schuss_nagler",
    "schuss_spule", "spule_laden", "schuss_kettenblitz", "schuss_spiegellaser",
    "schuss_kugelblitz", "plasma", "flammenwerfer", "kettensaege", "hammer_boden",
    "schock", "schlag_faust", "knaller", "emp", "piepen", "klebt", "gas",
    "schneeball", "wurf_leise", "nagel_wand", "falle_klick", "drohne", "horchposten", "anflug", "platsch",
    "emp_aus", "reifen_platt", "schild", "schild_durch",
    "ueberhitzt",           # eine Chor-Waffe ueberhitzt und kuehlt ab (seit 0.34.130)
    "bomber",               # ein Stueck Triebwerk des Napalm-Bombers (seit 0.34.130)
    "napalm_fall",          # eine Napalmbombe pfeift im Fall (seit 0.34.130)

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
    # Mischerpuffer in Proben (seit 0.34.136, vorher 512 = 12 ms): mit 1024
    # (23 ms) laeuft er nicht leer, wenn der Klangfaden kurz die GIL haelt -
    # sonst wiederholte die Karte den letzten Puffer, ein lauter Pulston.
    # Gleich in rustfront_menu.MIX_PUFFER (wer zuerst oeffnet, gilt).
    puffer=1024,
    # So oft gibt der Klangfaden die GIL ab, solange er baut (s; Python
    # sonst 0.005). pygame braucht sie im Tonfaden, wenn ein Klang endet.
    werkstatt_wechsel=0.0005,
    schuss=0.85,              # Lautstaerke der Schuesse
    # Wie ein Ton mit der Entfernung leiser wird. Bis `nah` ist er voll
    # zu hoeren, ab `weit` nicht mehr; dazwischen faellt er gleichmaessig
    # ab. `fremde_ebene` gilt fuer alles, was eine Etage hoeher oder
    # tiefer passiert - man hoert es, aber gedaempft durch den Boden.
    nah=190.0,
    weit=1150.0,
    leiseste=0.06,            # darunter wird nichts mehr abgespielt
    fremde_ebene=0.45,
    # Klaenge eines Bildes zeitrichtig (seit 0.34.58): jeder Rechenschritt
    # klingt um seinen Anteil am Bild spaeter, statt alle auf einmal.
    versatz_ab=0.004,         # kuerzer wird nicht verzoegert (s)
    versatz_max=0.25,         # laenger auch nicht - so lang darf ein Bild hoechstens sein
    kanaele=64,               # so viele Klaenge zugleich; dann weicht der aelteste
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
    # Seit 0.34.102 je 30 statt 60 je Sekunde (gemeldet: Lag bis zum Rauswurf
    # auf langsamem Internet). Der Gast ueberblendet nach dem gemessenen
    # Abstand (Gefecht.misch), Tastendruecke gehen sofort hinaus.
    takt=1.0 / 30.0,          # so oft schickt der Gastgeber den Weltzustand
    eingabe_takt=1.0 / 30.0,  # so oft schickt ein Gast seine Eingaben
    eingabe_mindest=1.0 / 120.0,  # eine neue Laufrichtung geht sofort, aber nicht oefter
    # Weltmeldungen als Aenderungen (netz.Leitung._welt_senden, seit
    # 0.34.102): voll_alle - so oft kommt trotzdem alles (Meldungen);
    # welt_stau_bytes - liegt mehr ungesendet, faellt die naechste Meldung
    # fuer diesen Gast aus; wirkung_hoechstens - so viele Ereignisse
    # ausgelassener Meldungen werden nachgereicht.
    welt_aenderungen=True,
    voll_alle=300,
    welt_stau_bytes=24000,
    # Quittungen: so viele Weltmeldungen duerfen unbestaetigt unterwegs sein
    # (bei 30 je Sekunde gut eine Drittelsekunde), und hoechstens so viele
    # werden in Folge ausgelassen, falls keine Quittung mehr kommt.
    unterwegs_hoechstens=10,
    auslassen_hoechstens=30,
    wirkung_hoechstens=400,
    # Was der Gast selbst rechnet (gastseite.py, seit 0.34.103).
    # Puffer: Weltmeldungen nach der Uhr des Gastgebers abspielen, um
    # takt + puffer_schwankung x gemessene Schwankung verzoegert (zwischen puffer_mindest
    # und puffer_hoechstens s). Mehr als puffer_meldungen im Puffer: alles
    # sofort. uhr_drift: so schnell (s je s) wird der Uhrvergleich vergessen.
    puffer_an=True,
    puffer_mindest=0.03,
    # Nicht hoeher: Treffer rechnet der Gastgeber, wo die Gegner bei ihm
    # stehen - jede Verzoegerung hier heisst, man zielt weiter hinter ihnen
    # her (bis zur Treffer-Rueckrechnung, docs/CLIENTSEITE.md Stufe D).
    puffer_hoechstens=0.08,     # seit 0.34.135 (0.15): weniger Verzoegerung im Bild
    puffer_meldungen=20,
    puffer_schwankung=1.0,
    uhr_drift=0.01,
    # Vorhersage der eigenen Figur: ab vorhersage_sprung px Unterschied
    # springt sie, darunter gleitet sie mit vorhersage_glaetten (je s); ohne
    # Antwort des Gastgebers laenger als vorhersage_ohne_antwort s bleibt
    # sie stehen; vorhersage_spur: so viele Schritte merkt sie sich (120 = 1 s).
    vorhersage_an=True,
    vorhersage_sprung=72.0,
    vorhersage_glaetten=10.0,
    vorhersage_ohne_antwort=0.75,
    vorhersage_spur=480,
    vorhersage_nachrechnen=24,  # so viele Schritte rechnet der Abgleich hoechstens nach
    # Eingabepuffer beim Gastgeber (gastseite.WirtTeil, seit 0.34.104): die
    # Bewegung eines Gasts genau so viele Schritte, wie er sie gemeint hat.
    # Mehr als eingabe_vorlauf_hoechstens Schritte Vorlauf (200 ms) werden
    # sofort abgebaut; war eingabe_fenster Schritte (1 s) lang immer mehr als
    # eingabe_vorlauf_ruhig da, ein Schritt.
    # Seit 0.34.135 aus (gemeldet: "der Dash ist bei Gaesten extrem verzoegert",
    # "Laufen fuehlt sich schwammig an"): bis zu 200 ms Vorlauf hiess, jede
    # Bewegung und jeder Dash wirkten beim Gastgeber so viel spaeter, und die
    # Vorhersage des Gasts musste staendig nachziehen. Jetzt wirkt alles sofort.
    eingabe_puffer=False,
    eingabe_vorlauf_hoechstens=24,
    eingabe_vorlauf_ruhig=2,
    eingabe_fenster=120,
    # Treffer-Rueckrechnung (seit 0.34.105, docs/CLIENTSEITE.md Stufe D): die
    # Kugeln eines Gasts treffen, wo die Ziele standen, als er sie sah -
    # hoechstens rueck_hoechstens s zurueck. Gemessen sieht ein Gast bei
    # 300 ms Ping rund 0,4 s zurueck (Hin- und Rueckweg, Puffer,
    # Ueberblendung). Hoeher hiesse: wer beschossen wird, wird oefter noch
    # getroffen, obwohl er bei sich schon hinter der Deckung war.
    # rueck_lagen: so viele Schritte merkt sich der Gastgeber (72 = 0,6 s);
    # rueck_suchweite: so viel weiter sucht der Treffer nach Zielen, die
    # seitdem weitergelaufen sind.
    rueck_an=True,
    rueck_hoechstens=0.5,
    rueck_lagen=72,
    rueck_suchweite=220.0,
    rueck_tempo=450.0,        # px/s: so schnell bewegt sich hoechstens etwas
    # Gerade Fluege rechnet der Gast (seit 0.34.106): jede Kugel geht nur
    # einmal hinaus (Start, Tempo, Uhrzeit), nicht in jeder Meldung.
    flug_beim_gast=True,
    # Der Sendepuffer des Systems je Gast (Bytes). Klein, damit sich dort
    # nichts sekundenlang staut: was nicht hinausgeht, merkt der Gegendruck.
    sendepuffer=65536,
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
    # Seit 0.34.95: zwei Armeen auf einer grossen Karte, links gegen
    # rechts, mit Fahrzeugen in jeder Basis (K.SCHLACHT). Gewuenscht, ein
    # wenig nach Battlefront: keine Phasen, nur Abschuesse fuer die Seite.
    "schlacht": dict(name="SCHLACHT", gegner=False, beute=True, revive=False,
                     teams=True, runden=False, zone=False, schlacht=True,
                     hinweis="Zwei Armeen, links gegen rechts, mit Fahrzeugen. "
                             "Abschüsse zählen für die Seite."),
    # Keine Spielart, die man waehlt, sondern der Ort dazwischen: hier
    # landet man beim Aufmachen und nach jeder Runde (siehe LOBBY).
    # "gegner" steht an, weil es im Gehege Zombies gibt - Wellen gibt es
    # keine, das Gefecht fragt vorher nach `lobby`.
    "lobby":  dict(name="LOBBY",  gegner=True,  beute=True,  revive=False,
                   teams=False, runden=False, zone=False, lobby=True,
                   hinweis="Rumlaufen, üben, auf die Runde warten."),
}
MODUS_VORGABE = "pvp"

# Das Funkgeraet der Fahrzeuge (seit 0.34.95, gewuenscht): sitzt ein Bot
# am Steuer, funkt der Wagen sichtbar - Wellen ueber der Antenne, bis er
# aussteigt. `antenne` ist (vorn, quer) als Anteil von Laenge und Breite.
FAHRZEUG_FUNK = dict(takt=1.1, wellen=3, radius=(4.0, 15.0), antenne=(-0.75, -0.7),
                     farbe=(150, 232, 214))

# SCHLACHT (seit 0.34.95). Jede Seite hat von Anfang an `je_seite`
# Kaempfer; wo Menschen fehlen, stehen sofort Bots. Die Basis einer Seite
# ist ihr Rand der Karte: links ROT, rechts BLAU (`basis_x` der Breite vom
# Rand). Dort steigt man ein, und dort stehen die Fahrzeuge der Seite -
# die Fahrzeuge aus der Karte bleiben weg, sie stuenden ungleich verteilt.
# Bots ohne Gegner im Blick stossen erst zur Mitte vor, dann zur Basis
# der anderen (`vorstoss_ziel`), statt die ganze Karte abzusuchen.
SCHLACHT = dict(
    je_seite=24,
    # Seit 0.34.132 (gewuenscht: "von sehr wenig zu unglaublich viel", je
    # Karte): alle Stufen; welche eine Karte anbietet, sagt ihr Kopf
    # (`je_seite_bis:`, `je_seite:`) oder ihre Groesse (seite_je_kacheln).
    groessen=(1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 30, 36, 42, 50, 60, 75, 100, 125, 150),
    seite_je_kacheln=380,      # ohne Angabe: je so viele begehbare Kacheln ein Kaempfer je Seite
    seite_viel=42,             # ab so vielen je Seite steht VIEL! im Menue (gemessen: bis ~40 je Seite haelt ein
                               # gewoehnlicher Rechner die 120 Schritte je Sekunde, 100 je Seite braucht ~2,5 mal so lang)
    # Seit 0.34.96 die offene Karte (gewuenscht: Fahrzeuge sollen nutzbar sein).
    # Seit 0.34.131 FLUSSTAL: die erste Karte mit Front (Eroberungspunkte).
    karte="flusstal",
    abschuesse=150,            # Vorgabe, wenn nach Abschuessen gespielt wird
    basis_x=0.08,              # Anteil der Kartenbreite vom Rand
    basis_proben=160,          # so viele freie Punkte werden je Basis geprueft
    # Seit 0.34.117: zwei Trosswagen und ein Flakwagen (der kommt mit einem Bot am
    # Steuer, siehe K.FLAK konvoi_*). Seit 0.34.129 je Eintrag die Stufe, ab der
    # er an der Basis steht (FREISCHALTEN, siehe `freischalten`): erst die
    # leichten, dann Flak und der zweite Trosswagen, zuletzt der Panzer. Ist
    # FREISCHALTEN aus, steht alles von Anfang an da (wie vorher).
    fahrzeuge=(("buggy", 2, 0), ("krad", 1, 0), ("panzerwagen", 1, 0), ("trosswagen", 1, 0),
               ("trosswagen", 1, 1), ("flakwagen", 1, 1), ("panzer", 1, 2)),
    fahrzeug_umkreis=420.0,    # so weit um die Basis stehen die Wagen
    spawn_umkreis=340.0,       # so weit um die Basis steigt man ein
    fahrer_je_seite=4,         # so viele Bots jeder Seite duerfen fahren
    panzerjaeger_je_seite=2,   # hoechstens so viele Bots jeder Seite tragen Panzerabwehr
    mitte_nah=260.0,           # so nah an der Mitte gilt sie als erreicht
    streuung=180.0,            # Ziele des Vorstosses so weit gestreut
    ziele_je=4,                # so viele feste Punkte je Ziel (Wegfelder teilen)
    # Seit 0.34.96. Lage ohne Funk: wer einen Gegner sieht, meldet es seiner
    # Seite (alle `melde_takt` s); Bots ohne Ziel ziehen zum naechsten
    # frischen Kampf in `lage_weite`, der nicht aelter als `lage_alt` ist.
    melde_takt=1.0,
    lage_raster=256.0,         # Meldungen auf dieses Raster (Wegfelder teilen)
    lage_alt=10.0,
    lage_weite=1100.0,         # seit 0.34.133 kleiner (vorher 1600: fast jeder kam zu jedem Kampf)
    kampf_zulauf=3,            # so viele Bots gehen hoechstens zugleich zu einem gemeldeten Kampf
    fahrzeug_zuletzt=20.0,     # so lange nach dem Aussteigen gehoert ein Wagen noch der Seite seines Fahrers (Punkte)
    zulauf_halten=25.0,        # so lange gilt die Zusage eines Bots fuer einen Kampf (s)
    stosstrupp=0.25,           # dieser Anteil zieht ohne Umweg ueber die Mitte zur Basis der anderen
    # Front: mehr als `front_ab` Bots einer Seite teilen sich auf `spuren`
    # Abschnitte quer zur Karte, `spur_abstand` px auseinander.
    front_ab=4,                # seit 0.34.133 immer in Abschnitten (vorher erst ab 20)
    spur_tiefe=520.0,          # so weit liegt die Mitte eines Abschnitts vor oder hinter der Kartenmitte
    spuren=5,
    spur_abstand=620.0,
    # Aufsitzen: Bots gehen zu einem Panzerwagen in dieser Weite, der
    # Fahrer setzt so weit vor Gegnern oder einem gemeldeten Kampf ab und
    # faehrt danach mit hoechstens diesem Gas weiter.
    # Dropzonen und Abwuerfe (seit 0.34.96, schlacht.py). hoehe: so hoch
    # beginnt ein Abwurf, sinken: px/s, vorlauf: so lange vorher zaehlt die
    # Zone sichtbar herunter, start: Vorlauf zum Rundenstart, vorlauf_kauf:
    # nach einem Kauf. bild_hub: so viel der Hoehe sieht man als Versatz
    # nach oben. sperre_basis: so weit um die feindliche Basis nichts kaufen.
    # Seit 0.34.100 beginnt ein Abwurf deutlich hoeher (gewuenscht: "die
    # Fahrzeuge sollen was weiter oben spawnen und dann wie bisher
    # absinken") - er kommt von oben ins Bild, statt darin aufzutauchen.
    # Landung (seit 0.34.100): ausweichen_ab - unter dieser Hoehe treibt er zu
    # einer freien Stelle, wenn unter ihm ein Fahrzeug, ein anderer Abwurf
    # oder Fels liegt (mit treiben px/s, gesucht bis suche_weit px weit).
    # Wer bei der Landung darunter steht, wird beiseite gestossen (stoss) und
    # nimmt quetschen Schaden; warnen_ab: ab da blinkt der Schatten rot.
    abwurf=dict(hoehe=460.0, sinken=60.0, vorlauf=8.0, start=3.0, vorlauf_kauf=6.0,
                bild_hub=0.55, schirm=(64, 26), schirm_kiste=(30, 14), schirm_ueber=30, kisten=3,
                sperre_basis=1800.0, ausweichen_ab=300.0, treiben=70.0, suche_weit=420.0,
                stoss=520.0, quetschen=15.0, warnen_ab=160.0),
    # Seit 0.34.138 wie eine Evakuierungszone (XCOM 2, gewuenscht): ein Feld so
    # gross wie das Fahrzeug plus `rand` px (Kisten: `kiste` px), an den Ecken
    # blaue Fackeln; je Fackel `rauch` Wolken, die `steigen` px aufsteigen,
    # bis `rauch_gross` px wachsen und mit `wind` verwehen.
    # Seit 0.34.138: die Basiswagen stehen zum Rundenstart sofort da, und freie
    # Bot-Fahrer (darf_fahren) bis `basis_fahrer_weite` px sitzen gleich darin.
    basis_sofort=True, basis_fahrer_weite=900.0,
    fahrer_anteil=0.45,        # seit 0.34.138: so viel der Seite darf fahren (hoechstens so viele, wie die Basen Wagen haben)
    drop_frei_vorn=6,          # seit 0.34.138: so viele 8-px-Schritte muss ein Basiswagen zur Front frei losfahren koennen
    dropzone=dict(radius=40, radius_kiste=22, grund=46, grund_puls=60,
                  rand=10, kiste=40,
                  # Seit 0.34.140 Leuchtfackeln am Boden mit dichtem Rauch (schlacht._leuchtfackel):
                  # Wolken je Fackel, wie schnell sie nachkommen, wie hoch sie steigen und wie
                  # gross sie werden, wie sehr der Wind sie wegtraegt, wie dicht sie am Anfang sind.
                  rauch=22, rauch_tempo=0.26, steigen=64.0, rauch_gross=30, wind=0.65, rauch_deck=245.0,
                  rauch_freund=(120, 170, 255), rauch_feind=(240, 88, 72), rauch_alt=(150, 150, 160),
                  licht_freund=(110, 180, 255), licht_feind=(255, 96, 70),
                  zeichen=dict(buggy="B", flakwagen="A", tragschrauber="H", werfer="W", funkwagen="F", spulenwagen="S", krad="K", jagdpanzer="J", panzer="P", panzerwagen="L", munition="M",
                               medkit="+")),
    # Punkte (nur Menschen). Ein zerstoertes Fahrzeug bringt seit 0.34.129 die
    # Haelfte seines Kaufpreises (`fahrzeug_anteil`, mindestens `fahrzeug_min`),
    # was man nicht kaufen kann (Trosswagen) `fahrzeug` - vorher pauschal 5:
    # ein Krad brachte mehr, als es kostete.
    # Seit 0.34.134 gebucht schon beim Umwerfen (am Boden), egal ob er danach
    # wiederbelebt wird; seit 0.34.135 wieder 1 Punkt (gewuenscht).
    # Seit 0.34.138 (gewuenscht: "neue Arten, Punkte zu gewinnen ... man soll
    # nie Sachen aufgeben muessen, weil sie keine Punkte bringen, aber sich
    # eine Zeit lang bewusst auf etwas fokussieren koennen"):
    #   aufhelfen 3 statt 5,
    #   erobern     jeder Mensch im Kreis, wenn ein Punkt an seine Seite faellt,
    #   serie       ein Abschuss innerhalb `serie_zeit` s nach dem vorigen: so viel
    #               mehr (der dritte, vierte ... in Folge; bis `serie_hoechstens`),
    #   jagd        ein Fahrzeug innerhalb `jagd_zeit` s nach dem vorigen: so viel mehr,
    #   sold        alle `sold_takt` s jeder Mensch, `sold_halten` mehr, wenn die
    #               eigene Seite mehr Eroberungspunkte haelt als die andere.
    punkte=dict(abschuss=1, fahrzeug=3, fahrzeug_anteil=0.5, fahrzeug_min=2, aufhelfen=3,
                erobern=3, serie=1, serie_zeit=20.0, serie_ab=2, serie_hoechstens=3,
                jagd=2, jagd_zeit=90.0, sold=1, sold_halten=1, sold_takt=60.0),
    # Was man kaufen kann: (Kennung, Kosten, Name). Seit 0.34.129 billiger
    # (gewuenscht: "es kaufen ja nur Spieler, und es gibt nicht so viele").
    belohnungen=(
        ("munition", 2, "MUNITIONSABWURF"),
        ("medkit", 2, "SANITÄTSABWURF"),
        ("buggy", 3, "DROPZONE: BUGGY"),
        ("krad", 2, "DROPZONE: KRAD"),
        ("aufklaerung", 4, "AUFKLÄRUNGSDROHNE"),
        ("napalm", 7, "NAPALM-ANGRIFF"),
        ("fallschirmjaeger", 6, "FALLSCHIRMJÄGER"),
        ("panzerwagen", 6, "DROPZONE: PANZERWAGEN"),
        ("panzer", 9, "DROPZONE: PANZER"),
        ("jagdpanzer", 8, "DROPZONE: JAGDPANZER"),
        ("spulenwagen", 8, "DROPZONE: SPULENWAGEN"),
        ("funkwagen", 6, "DROPZONE: FUNKWAGEN"),
        ("werfer", 10, "DROPZONE: WERFER"),
        ("tragschrauber", 9, "DROPZONE: TRAGSCHRAUBER"),
        ("flakwagen", 5, "DROPZONE: FLAKWAGEN"),
    ),
    # FREISCHALTEN (seit 0.34.129, Regel der Runde): was man kaufen kann, kommt
    # in Stufen - nicht nach festen Minuten, sondern nach dem Spielverlauf,
    # damit es bei 5 wie bei 30 Minuten passt. Der Verlauf ist der Anteil der
    # abgelaufenen Rundenzeit (bei einer Runde nach Abschuessen der groessere
    # von: Abschuesse der fuehrenden Seite am Ziel, Laufzeit an `bezug`).
    # `stufen`: Anteil, ab dem Stufe 1, 2, 3 gilt; `hoechstens`: spaetestens
    # nach so vielen Sekunden (lange Runden warten sonst zu lange). AUS: alles sofort.
    stufe=dict(munition=0, medkit=0, krad=0, buggy=0, aufklaerung=0,
               panzerwagen=1, flakwagen=1, funkwagen=1, fallschirmjaeger=1, napalm=1,
               panzer=2, jagdpanzer=2, spulenwagen=2, tragschrauber=2,
               werfer=3),
    freischalten=dict(
        schnell=dict(stufen=(0.05, 0.12, 0.22), hoechstens=(60, 150, 270)),
        normal=dict(stufen=(0.10, 0.22, 0.35), hoechstens=(120, 270, 450)),
        langsam=dict(stufen=(0.15, 0.32, 0.50), hoechstens=(180, 420, 660)),
        bezug=900.0,              # Runde nach Abschuessen: so lange gilt als ganze Runde (s)
    ),
    # So viele gekaufte je Seite gleichzeitig (lebend oder noch im Anflug) -
    # seit 0.34.130 nur mit der Regel HÖCHSTENS JE SEITE (Vorgabe aus).
    hoechstens_je_seite=dict(panzerwagen=3, flakwagen=2, funkwagen=1, jagdpanzer=2,
                             spulenwagen=1, panzer=2, tragschrauber=1, werfer=1),
    # Nur in der eigenen Haelfte abzuwerfen: wirkt auf Entfernung, gehoert nach hinten.
    nur_eigene_haelfte=("funkwagen", "werfer", "tragschrauber"),
    belohnung_hilfe=dict(flakwagen="BOT-FLAK GEGEN FLIEGER", tragschrauber="FLIEGT, SIEHT ALLES, ZWEI BOMBEN", werfer="SALVEN AUF GESEHENE ZIELE, SEHR ZERBRECHLICH", funkwagen="PEILEN ODER STÖREN, NUR AUFGEBAUT", spulenwagen="BLITZ UND EMP-FELD, NUR AUFGEBAUT", krad="EINMAL, SCHNELL, KEIN SCHUTZ", jagdpanzer="EINMAL, WEIT, NUR VON VORN DICK",
                         munition="DREI KISTEN AM FALLSCHIRM", medkit="DREI MEDKITS AM FALLSCHIRM",
                         buggy="EINMAL, AUF FREIEM GELÄNDE", aufklaerung="DECKT AUF, MARKIERT LANGE",
                         panzerwagen="EINMAL, AUF FREIEM GELÄNDE", panzer="EINMAL, AUF FREIEM GELÄNDE",
                         fallschirmjaeger="FÜNF BOTS AM SCHIRM, IN FORMATION",
                         napalm="ZWEI KLICKS: START, DANN RICHTUNG"),
    # Napalm-Angriff (seit 0.34.101): ein Flugzeug, das man nicht sieht, nur
    # hoert, wirft entlang einer Bahn Napalm. Die Bahn ist immer gleich lang
    # (laenge_anteil der Kartenhoehe) - der zweite Klick gibt nur die
    # Richtung. Die Bomben fallen unregelmaessig: Abstand abstand (Faktor
    # zufaellig in streu), mit luecke_chance eine Luecke von luecke px,
    # seitlich bis seitlich px daneben. Jede hinterlaesst ein Feuer mit
    # radius px, das dauer s brennt. So brennt nie die ganze Bahn, und man
    # kommt mit etwas Geschick hindurch. vorlauf: so lange nach dem Kauf, bis
    # das Flugzeug den Start erreicht; tempo: px/s; fall: so lange faellt
    # eine Bombe.
    # Seit 0.34.130: das Napalm brennt deutlich laenger (vorher 16-24 s) und
    # anders als gewoehnliches Feuer (FEUER napalm_*); man hoert den Bomber
    # nur in seiner Naehe - alle `brumm_takt` s ein Stueck Triebwerk dort, wo
    # er ist (von `hoeren_ab` bis `hoeren_bis` der Bahn), und die Bomben fallen
    # sichtbar (`fall` s aus `bombe_hoehe` px, mit `bombe_schwung` seines Tempos).
    napalm=dict(laenge_anteil=0.5, tempo=950.0, vorlauf=2.5, fall=1.1, abstand=105.0,
                streu=(0.6, 1.7), luecke_chance=0.28, luecke=(110.0, 210.0), seitlich=46.0,
                radius=(40.0, 72.0), dauer=(30.0, 42.0), wenigstens_luecken=3,
                hoeren_ab=-0.7, hoeren_bis=1.7, brumm_takt=0.45, brumm_laut=1.4,
                bombe_hoehe=170.0, bombe_schwung=0.3),
    # Die Aufklaerungsdrohne (seit 0.34.100 ein grosser Starrfluegler, hoch
    # oben). markiert: so lange bleiben Pings ueber Gegnern und Fahrzeugen
    # (vorher 15 s). flug_hub: so hoch fliegt sie im Bild ueber ihrem
    # Schatten, parallaxe: so viel schneller als der Boden zieht sie vorbei.
    aufklaerung=dict(radius=650.0, markiert=20.0, dauer=7.0, anflug=1400.0,
                     flug_hub=96.0, parallaxe=0.45, spannweite=96),
    # Die Nachschubkarte (seit 0.34.100): Nebel ueberall, ausser so weit um die
    # eigenen Leute und im Kreis einer eigenen Drohne.
    karte_sicht=650.0,
    karte_nebel=(10, 8, 6, 170),
    # Fallschirmjaeger (seit 0.34.100): anzahl Bots der eigenen Seite, in einer
    # Keilformation (abstand px) innerhalb breite px um den Punkt, nie naeher
    # als nicht_basis an der eigenen Basis. Sie beginnen hoehe hoch und sinken
    # mit sinken px/s; in der Luft tun sie nichts, sehen aber schon.
    fallschirmjaeger_schirm=(30, 13),
    fallschirmjaeger=dict(anzahl=5, abstand=46.0, breite=140.0, nicht_basis=900.0,
                          hoehe=420.0, sinken=70.0, versatz=0.8, waffen=("sturm", "mp", "unterhebel",
                                                                          "sturm", "autoschrot")),
    aufsitzen_weite=260.0,
    absetzen_vor=650.0,
    nach_absetzen_tempo=70.0,   # px/s
)

# Auf Luftziele zielen (seit 0.34.135): liegt der Zeiger so viel ausserhalb
# ihres Radius noch auf dem Bild, rastet er trotzdem ein.
LUFT_ZIELEN = dict(
    volltreffer=6.0,          # so nah am Wagen (px) zaehlt ein Einschlag als Volltreffer (seit 0.34.138)
    fang_extra=12.0,
    treffer_extra=14.0)       # ... und eine Kugel trifft es so viel ausserhalb noch (Streuung)

# Ein Fahrzeug von einem Bot der eigenen Seite uebernehmen (seit 0.34.134):
# E am Wagen wirft ihn hinaus (nicht beim Flakwagen); steigt man aus, steigt er
# wieder ein, wenn er so nah ist.
# Seit 0.34.138: E so lange `halten` (s), um einen Bot vom Steuer zu holen;
# auf einen Panzerwagen sitzt auf, wer bis `aufsitzen_rand` px am Blech steht
# (vorher zaehlte der Abstand zur Mitte, am Heck war man zu weit weg).
FAHRZEUG_UEBERNEHMEN = dict(zurueck_weite=900.0, halten=0.6, aufsitzen_rand=18.0)

# Die Front in SCHLACHT (seit 0.34.131, dustfront/front.py). Gilt auf Karten,
# die ihre Basen, Eroberungspunkte und Wege im Kopf nennen (FLUSSTAL,
# KANALSTADT). Gewuenscht: Hotzonen, die "wenn eingenommen, keine Punkte
# bringen", sondern Einstiegspunkte werden; nach dem Tod eine Karte mit
# allen Einstiegen zur Wahl; Bots in kleinen Gruppen auf verschiedenen
# Wegen, in Formationen, verteilt auf die Einstiege - eine Front.
FRONT = dict(
    radius=210.0,              # Eroberungskreis eines Punktes (px)
    zeit=14.0,                 # so lange braucht einer allein von neutral bis ganz (s)
    mehr=0.4,                  # jeder weitere der Mehrheit macht es so viel schneller ...
    hoechstens=2.6,            # ... bis hoechstens so viel mal
    zurueck=0.06,              # niemand da: zurueck zum Stand des Besitzers (Anteil je s)
    einstieg_umkreis=150.0,    # so weit um einen Punkt steigt man ein (px)
    basis_umkreis=210.0,       # ... um eine Basis
    umkaempft=520.0,           # ein Gegner so nah am Punkt: dort steigt keiner ein (px)
    wieder_nach=7.0,           # Wiedereinstieg in SCHLACHT mit Front (s): Zeit zum Waehlen
    takt=1.5,                  # so oft plant die Front einer Seite neu (s)
    knoten_zusammen=96.0,      # Wegpunkte so nah beieinander sind ein Knoten (px)
    punkt_anschluss=420.0,     # so weit sucht ein Punkt den naechsten Wegknoten (px)
    # Gruppengroessen und wie oft: auch einmal einer allein oder zu zweit.
    gruppen=((1, 0.15), (2, 0.32), (3, 0.3), (4, 0.23)),
    sammeln=3.0,               # so lange wartet eine neue Gruppe am Einstieg auf ihre Leute (s)
    wegpunkt_nah=70.0,         # so nah am Wegpunkt: weiter zum naechsten (px)
    warten_ab=150.0,           # faellt einer weiter zurueck, geht der Anfuehrer langsamer (px)
    warten_tempo=0.55,
    form_abstand=46.0,         # Abstand in der Formation (px)
    spur_abstand=40.0,         # in der Reihe auf der Spur des Anfuehrers (px)
    halten_ring=(0.3, 0.85),   # am Punkt: so weit vom Mittelpunkt (Anteil des Radius)
    halten_neu=(14.0, 26.0),   # so lange haelt eine Gruppe einen sicheren Punkt, dann weiter (s)
    kampf_weite=520.0,         # ein gemeldeter Kampf so nah am Anfuehrer zieht die Gruppe an
    kampf_pause=14.0,          # ... danach so lange kein neuer Umweg (s)
    gewicht_angriff=1.0,       # Gewichte der Ziele: Punkt an der Front angreifen,
    gewicht_bedroht=1.7,       # eigenen Punkt verteidigen, der bedroht ist,
    gewicht_halten=0.3,        # eigenen Punkt an der Front halten,
    gewicht_basis=0.9,         # Basis der anderen (wenn alle Punkte uns gehoeren)
    bedroht=640.0,             # Gegner so nah: ein eigener Punkt gilt als bedroht (px)
    front_faktor=1.6,          # bis so viel weiter als der naechste gilt ein Punkt als Front
    weg_teilen=0.9,            # Aufschlag je Gruppe, die eine Kante zum selben Ziel nimmt
    einstieg_last=0.6,         # Aufschlag je Bot, der von dort schon zu diesem Ziel ging
    einstieg_weit=2.6,         # weiter als so viel mal der naechste: dorthin kein Bot
    anflug=(70.0, 150.0),      # der letzte Wegpunkt liegt so weit vor dem Punkt (px)
    fahrer=4,                  # so viele Bots je Seite fahren, wenn die Karte nichts sagt
    # Seit 0.34.133 (gewuenscht: "nicht alle Bots zum selben Fight, sondern
    # unabhaengige Ziele und Vorstoesse an verschiedenen Stellen"):
    kampf_gruppen=1,           # so viele Gruppen biegen hoechstens zugleich zu einem gemeldeten Kampf ab
    kampf_weg=520.0,           # ... und nur, wenn er so nah an ihrem eigenen Weg liegt (px)
    verdacht_weite=330.0,      # weiter weg gehoerte Schuesse lassen eine Gruppe nur hinschauen, nicht hingehen
    ziel_anteil=0.36,          # mehr als dieser Anteil der Bots einer Seite geht nie zum selben Ziel
    gewicht_vorstoss=0.32,     # Punkte hinter der Front: kleine Stosstrupps (1-2) gehen dorthin
    vorstoss_ab=8,             # ... wenn die Seite wenigstens so viele Bots hat
)


def basis_wagen(bis_stufe: int = 99) -> list:
    """Die Basis-Fahrzeuge der SCHLACHT bis zu dieser Stufe als (Art, Anzahl),
    je Art zusammengezaehlt (seit 0.34.129 haben die Eintraege eine Stufe)."""
    zusammen: dict = {}
    for eintrag in SCHLACHT["fahrzeuge"]:
        art, anzahl = eintrag[0], eintrag[1]
        stufe = eintrag[2] if len(eintrag) > 2 else 0
        if stufe <= bis_stufe:
            zusammen[art] = zusammen.get(art, 0) + anzahl
    return list(zusammen.items())


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
    rueckwaerts=145.0,         # seit 0.34.135 schneller (95)
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
    rueck_roll_grenze=60.0,   # rollt er so nah an gerade nach hinten (Grad), stuetzt sie nicht (0.34.140)
    v_min=55.0,               # unter diesem Tempo rechnet der Schraeglauf ruhiger
    spur_ab=0.25,             # ab so viel Rutschen bleiben Reifenspuren (0 bis 1)
    spur_abstand=2.5,         # Pixel zwischen zwei Spurpunkten
    kreis=13.0,               # Radius der beiden Kreise, mit denen er anstoesst
    achse=14.0,               # Abstand der Kreise von seiner Mitte
    einsteigen=46.0,          # so nah muss man dran sein
    schaden_anteil=0.7,       # so viel von jedem Schaden kommt beim Fahrer an
    # Seit 0.34.77 kommt im Fahrzeug gar nichts an (gemeldet: "Personen in
    # Fahrzeugen sollen keinen Schaden nehmen") - weder Treffer am Wagen noch
    # an der Figur selbst. Die Anteile (schaden_anteil, fahrer_anteil)
    # gelten nur, wenn das hier False ist. Geht der Wagen hoch, ist man
    # draussen: das zaehlt nicht (fahrer_schaden).
    fahrer_geschuetzt=True,
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
    # koennen und dann respawnen random auf der map"). Seit 0.34.65 mit
    # Panzerung (PANZERUNG): ein Sturmgewehr braucht rund 24 Treffer, eine
    # Granate fuenf, eine Rakete zwei.
    leben=380.0,
    explosion_radius=70.0,    # wenn er hochgeht
    explosion_schaden=70.0,   # in der Mitte, nach aussen weniger
    fahrer_schaden=55.0,      # was der Fahrer abbekommt (vor den 70 %)
    wrack_zeit=9.0,           # so lange brennt das Wrack, dann ist er weg
    neu_nach=12.0,            # und so viel spaeter steht irgendwo ein neuer
    neu_abstand=320.0,        # so weit von jedem Spieler weg (Weltpixel)
    rauch_takt=0.12,          # Qualm aus dem Wrack
    balken_breite=26,         # Lebensbalken ueber einem beschaedigten Wagen
)

# ── Panzer und Panzerwagen (seit 0.34.59) ──────────────────────────
#
# Entwurf aus dem Paket `rustfront_fahrzeuge` (README_IMMEDIATELY.md),
# Grafik und Verhalten vom Besitzer abgenommen. Bilder in
# dustfront/art_fahrzeuge.py, Fahren in dustfront/fahrzeug.py. Gemeldet
# als Entscheidung: "einer steuert ein Fahrzeug" - der Fahrer faehrt mit
# W A S D und zielt mit der Maus (Turm bzw. MG-Ring folgen ihr).
#
# Masse in Spielpixeln, ausser wo "Entwurf" steht (mal `groesse`).
FAHRZEUG_BILD = dict(
    # Wanne und Aufbau gegenueber dem ersten Entwurf. Der Besitzer hat
    # 1,0, 1,2 und 1,4 gesehen und 1,4 genommen: dann haben die Insassen
    # Spielergroesse. Kuppel, MG-Ring und Insasse wachsen NICHT mit.
    groesse=1.4,
    flaeche=128,              # Bildmass von Wanne und Turm
    ring_flaeche=64,          # Bildmass des MG-Rings
    kette_teilung=2.6,        # Entwurfspixel je Kettenglied
    phasen=12,                # Stufen je Kettenglied (im Video so)
    gedreht_speicher=96,      # so viele gedrehte Wannen und Tuerme merkt er sich
)

PANZER = dict(
    marke="P",                # Buchstabe in der Karte
    name="PANZER",
    # Fahren: ein Kettenfahrzeug, kein Einspurmodell. Dreht auf der
    # Stelle, driftet nicht. Zielwerte aus dem abgenommenen Video.
    hoechst=45.0,             # px/s vorwaerts
    rueckwaerts=44.0,          # seit 0.34.135 schneller (26)
    beschleunigung=55.0,
    bremse=120.0,             # gegen die Fahrtrichtung gedrueckt
    rollen=90.0,              # ohne Gas
    drehen=80.0,              # Grad je Sekunde auf der Stelle
    drehen_fahrt=0.55,        # bei Hoechstfahrt dreht er nur noch so viel davon
    dreh_beschl=320.0,        # Grad je Sekunde im Quadrat
    aufprall=0.0,             # so viel Tempo bleibt nach einem Aufprall (rueckwaerts)
    aufprall_hart=40.0,       # ab diesem Tempo rumst es
    # Fussabdruck als Rechteck (lokal, +x = vorn), aus dem Paket (RAMMEN)
    vorn=44.0, hinten=-44.0, halb=29.7,
    ketten_abstand=23.8,      # von der Mitte bis zur Kettenmitte (17 Entwurfspixel)
    kette_teilung=3.64,       # Spielpixel je Glied: Weg je Kettenphase
    spur_abstand=3.0,         # Kettenspuren im Sand, Pixel zwischen zwei Abdruecken
    spur_deckkraft=46,
    # Turm: dreht unabhaengig, ca. 50 bis 70 Grad je Sekunde
    turm_vor=2.8,             # Drehpunkt so weit vor der Wannenmitte (2 Entwurfspixel)
    turm_dreh=60.0,
    muendung=51.3,            # Muendung der Kanone vor der Turmmitte (44 Turmpixel)
    bug_mg=(46.9, 7.0),       # Muendung des Bug-MGs, in der Wanne (33,5 / 5)
    ruecklauf=5.0,            # das Rohr faehrt nach dem Schuss so weit zurueck
    ruecklauf_tempo=14.0,     # und kommt so schnell wieder vor (px/s)
    ruck=1.5,                 # die Wanne ruckt so weit zurueck
    ruck_tempo=10.0,
    # Was er aushaelt. Wie viel von welchem Treffer ankommt, steht seit
    # 0.34.65 in PANZERUNG (Kugeln zerkratzen nur den Lack).
    leben=950.0,
    fahrer_anteil=0.2,        # so viel von jedem Treffer kommt beim Kommandanten an
    explosion_radius=96.0,
    explosion_schaden=95.0,
    fahrer_schaden=40.0,
    wrack_zeit=14.0,
    neu_nach=30.0,
    einsteigen=60.0,          # so nah muss man an der Mitte sein
    balken_breite=40,
    motor_takt=0.42,          # so oft brummt der Motor, waehrend er faehrt (s)
    # Mit einem Stick (Touch): wie beim Buggy (fahrzeug.Buggy.stick_steuern).
    stick_tot=0.2,
    stick_voll_lenken=40.0,
    stick_wenden=110.0,
    stick_zurueck=150.0,
    stick_bremsen_ab=20.0,
    # Rammen: Schaden nur ueber die Front und ab der Schwelle, in Leben:
    # (Tempo - schwelle) * je_px. Im Paket in "Treffern" eines Laeufers
    # (4 je Laeufer, 44 Leben) - hier umgerechnet: 1/25 Treffer = 0,44.
    ramm_schwelle=20.0,
    ramm_je_px=0.44,
    ramm_stoss=1.2,
    ramm_extra=40.0,
)

PANZERWAGEN = dict(
    marke="L",
    name="PANZERWAGEN",
    # Gewuenscht "wie ein Striker": zieht zaeh an, wird dann sehr schnell,
    # ist sehr schlecht lenkbar. Faehrt mit dem Einspurmodell des Buggys
    # (Buggy._physik) - nur mit diesem zweiten Satz Werte. Abgestimmt
    # gegen die Zielwerte aus dem Paket:
    #   Beschleunigung a(v) = (motor + motor_wachsen * v) * (1 - (v/hoechst)^3)
    #   -> 26 px/s nach 1,2 s, rund 240 px/s nach 5 s, hoechstens 320
    #   Wenderadius wende_grund + wende_je_tempo * v (Buggy: rund 40)
    hoechst=320.0,
    rueckwaerts=110.0,
    # Seit 0.34.96 deutlich wendiger (gewuenscht): zieht frueher an,
    # wendet auf engerem Kreis, lenkt schneller ein, faehrt flotter zurueck.
    motor=28.0,
    motor_wachsen=0.75,
    bremse=260.0,
    rollen=34.0,
    luft=0.0,
    wende_grund=70.0,
    wende_je_tempo=0.45,
    lenk_max=24.0,            # nur fuer die Stick-Steuerung und als Grenze
    lenk_abfall=0.0,
    lenk_tempo=150.0,
    achse_vorn=25.2,          # Vorderachse 18 Entwurfspixel vor der Mitte
    achse_hinten=19.0,        # zwischen den beiden Hinterachsen
    traegheit=1100.0,
    griff_vorn=560.0,
    griff_hinten=500.0,
    steif=5200.0,
    schlupf_spitze=7.0,
    gleiten=0.8,
    handbremse_griff=0.55,
    handbremse_bremse=120.0,
    antrieb_kreis=0.6,
    durchdrehen=1.0,
    gegenlenken=0.4,
    gegenlenken_los=1.0,
    antrieb_kreis_los=0.25,
    drift_grenze=24.0,
    drift_grenze_hb=50.0,
    drift_stuetze=60000.0,
    v_min=55.0,
    spur_ab=0.3,
    spur_abstand=2.5,
    aufprall=0.2,
    aufprall_hart=120.0,
    staub_ab=70.0,
    staub_takt=0.05,
    staub_farbe=(206, 184, 142),
    staub_groesse=3,
    staub_hinten=34.0,        # Staub hinter den Hinterachsen, nicht aus der Mitte
    staub_quer=19.6,
    unscharf_ab=72.0,         # ab diesem Tempo sind die Reifen verwischt (0,4 Stollen je Bild)
    stick_tot=0.2,
    stick_voll_lenken=40.0,
    stick_wenden=110.0,
    stick_zurueck=150.0,
    stick_bremsen_ab=50.0,
    # Fussabdruck aus dem Paket (RAMMEN), +x = vorn
    vorn=47.6, hinten=-43.4, halb=24.5,
    reifen_abstand=19.6,      # Reifenmitte von der Mitte (14 Entwurfspixel)
    reifen_teilung=3.01,      # Spielpixel je Stollen
    # Der MG-Ring: Mitte (-12,5 Entwurfspixel), dreht mit ca. 120 Grad je s
    ring=(-17.5, 0.0),
    ring_dreh=120.0,
    ring_muendung=29.0,
    ring_ruecklauf=1.5,
    ring_ruecklauf_tempo=20.0,
    leben=620.0,              # wie viel ankommt: PANZERUNG
    fahrer_anteil=0.45,       # der Schuetze steht im Ring, Kopf und Schultern frei
    explosion_radius=84.0,
    explosion_schaden=85.0,
    fahrer_schaden=50.0,
    wrack_zeit=12.0,
    neu_nach=24.0,
    einsteigen=56.0,
    # Truppentransporter (seit 0.34.95): faehrt jemand, steigen bis zu so
    # viele Spieler hinten auf (E). Bots nicht.
    plaetze=4,
    balken_breite=36,
    motor_takt=0.36,
    ramm_schwelle=40.0,
    ramm_je_px=0.37,          # 1/30 Treffer eines Laeufers
    ramm_stoss=1.35,
    ramm_extra=30.0,
)

# ── Krad und Jagdpanzer (seit 0.34.107) ────────────────────────────
#
# Zwei der Fahrzeuge aus dem Konzept "Fahrzeuge fuer grosse Karten" (die
# Seite mit den Entscheidungen des Besitzers). Beide fuer die SCHLACHT.

# Das Krad: ein Motorrad mit Beiwagen, eine Abwandlung des Buggys (gleiches
# Einspurmodell, eigene Werte). Das schnellste Fahrzeug, aber ohne
# Panzerung: wer drinsitzt, bekommt jeden Treffer ganz ab. Der Fahrer hat
# keine Waffe (gewuenscht); der Beifahrer schiesst mit seiner eigenen.
KRAD = dict(
    FAHRZEUG,
    marke="K",
    name="KRAD",
    hoechst=290.0,
    rueckwaerts=125.0,         # seit 0.34.135 schneller (80)
    motor=520.0,
    bremse=560.0,
    traegheit=150.0,          # leichter: dreht sich schneller um sich selbst
    kreis=9.0,                # kleiner als der Buggy (13)
    achse=10.0,
    einsteigen=40.0,
    leben=180.0,
    # Im Gegensatz zu allen anderen Fahrzeugen kein Schutz der Insassen.
    fahrer_geschuetzt=False,
    schaden_anteil=1.0,
    fahrer_anteil=1.0,
    plaetze=1,                # der Beifahrer im Beiwagen
    beifahrer_streuung=2.0,   # so viel mal mehr Streuung seiner Waffe, wenn das Krad rollt
    # Der Beifahrer im Beiwagen (seit 0.34.121) dreht sich nur so weit: von
    # leicht links vorn bis schraeg nach hinten rechts (Grad zur Fahrtrichtung,
    # + = rechts). Ueber den Fahrer hinweg nach links schiesst er nicht.
    beifahrer_bogen=(-35.0, 150.0),
    beifahrer_sitz=(-3.9, 11.2),   # Mitte der Sitzmulde (Pixel, +x vorn, +y rechts)
    beifahrer_tempo=150.0,    # ... ab diesem Tempo (px/s) voll
    explosion_radius=48.0,
    explosion_schaden=40.0,
    fahrer_schaden=40.0,
    wrack_zeit=7.0,
    neu_nach=10.0,
    balken_breite=20,
)

# Der Jagdpanzer: kein Turm, eine starre Kanone im Bug (Schwenk nur wenige
# Grad), dafuer die dickste Front im Spiel und eine Kanone, die weiter reicht
# als die des Panzers. Eine grosse, von vorn gepanzerte Scharfschuetzenwaffe
# gegen Fahrzeuge; gegen Infanterie fast wirkungslos (kein Bug-MG, kleine
# Druckwelle). Rechte Maustaste: Zielfernrohr (wie beim Scharfschuetzen).
JAGDPANZER = dict(
    PANZER,
    marke="J",
    name="JAGDPANZER",
    hoechst=62.0,
    rueckwaerts=48.0,          # seit 0.34.135 schneller (30)
    beschleunigung=60.0,
    leben=800.0,
    vorn=46.0, hinten=-44.0, halb=29.0,
    ketten_abstand=23.1,
    turm_vor=0.0,             # die Kanone schwenkt um die Mitte der Wanne
    muendung=72.8,            # Muendung der Kanone vor der Mitte (Pixel)
    kanone="jagdkanone",      # welche Zeile von FAHRZEUG_WAFFEN
    schwenk=12.0,             # Grad, die die Kanone von der Wanne abweichen darf
    turm_dreh=40.0,           # Grad je Sekunde, mit denen sie schwenkt
    zielfernrohr=True,
    # Dicker vorn, duenner hinten als der Panzer (PANZER_SEITEN).
    seiten=dict(vorn=0.5, seite=1.1, hinten=1.6),
    fahrer_anteil=0.15,
    explosion_radius=100.0,
    explosion_schaden=100.0,
    fahrer_schaden=40.0,
    wrack_zeit=14.0,
    neu_nach=40.0,
    einsteigen=60.0,
    balken_breite=42,
)

# Der Trosswagen (seit 0.34.108): Munition, Medkits und Reparatur fahren mit
# zur Front. Niemand sitzt auf; man stellt sich HINTEN dran und drueckt E
# (einmal Munition und ein Medkit, bis der Vorrat des Wagens leer ist). Auch
# Trosswagen der Gegner lassen sich so plündern. Eigene Fahrzeuge, die hinten
# dranstehen, werden repariert - auch im Stehen, solange der Vorrat reicht.
# Er faehrt wie der Panzerwagen (Einspurmodell), nur langsamer. Nicht per
# Nachschub zu kaufen: an jeder Basis stehen welche (SCHLACHT "fahrzeuge")
# und kommen wieder. Nur fuer Menschen am Steuer.
TROSSWAGEN = dict(
    {k: v for k, v in dict(FAHRZEUG, **PANZERWAGEN).items()
     if k not in ("plaetze", "ring", "ring_dreh", "ring_muendung", "ring_ruecklauf",
                  "ring_ruecklauf_tempo", "vorn", "hinten", "halb", "reifen_abstand",
                  "reifen_teilung", "unscharf_ab", "ramm_schwelle", "ramm_je_px",
                  "ramm_stoss", "ramm_extra")},
    marke="T",
    name="TROSSWAGEN",
    hoechst=210.0,
    rueckwaerts=110.0,         # seit 0.34.135 schneller (70)
    motor=22.0,
    # Seit 0.34.117 ein Fuenftel groesser (gewuenscht): Bild, Kreise, Achsen
    # und die Zone hinten wuchsen mit.
    kreis=21.6,               # zwei Kreise von 21,6 Pixeln, 31 von der Mitte: 106 x 43
    achse=31.0,
    einsteigen=60.0,
    leben=420.0,
    explosion_radius=80.0,
    explosion_schaden=80.0,
    fahrer_schaden=50.0,
    wrack_zeit=10.0,
    neu_nach=45.0,
    balken_breite=34,
    motor_takt=0.4,
    # Hinten dran: Mitte der Zone `abstand` hinter der Mitte des Wagens,
    # Radius `radius`. Wer hier steht und E drueckt, bekommt Munition (wie
    # eine Munitionskiste) und ein Medkit; `entnahmen` Mal je Wagen, ein
    # Spieler hoechstens alle `pause` Sekunden.
    zone=dict(abstand=74.0, radius=40.0),
    entnahmen=10,
    pause=4.0,
    reparatur=dict(vorrat=600.0, je_sekunde=14.0),
)

# Der Spulenwagen (seit 0.34.110): erbeutete Chor-Technik. Linke Maustaste:
# ein schwacher Kettenblitz (der erste im Kegel zum Zeiger, dann von Koerper
# zu Koerper). Rechte Maustaste: das EMP-Feld. Dafuer muss er aufgebaut
# werden (`aufbau` Sekunden, er steht dabei), dann pulsiert es am Ort: alle
# `takt` Sekunden legt ein Puls jedes fremde Fahrzeug im Kreis `radius` fuer
# `emp` Sekunden still. Nur `dauer` Sekunden lang, danach muss er `laden`
# Sekunden laden (fahren geht wieder, ein neues Feld nicht). Eigene Fahrzeuge
# bleiben verschont. Nur fuer Menschen am Steuer.
SPULENWAGEN = dict(
    {k: v for k, v in TROSSWAGEN.items()
     if k not in ("zone", "entnahmen", "pause", "reparatur", "nur_mensch", "name", "marke")},
    marke="S",
    name="SPULENWAGEN",
    hoechst=180.0,
    kreis=22.0,               # zwei Kreise von 22 Pixeln, 26 von der Mitte: 96 x 44
    achse=26.0,
    einsteigen=56.0,
    leben=480.0,
    explosion_radius=84.0,
    explosion_schaden=85.0,
    fahrer_schaden=50.0,
    wrack_zeit=12.0,
    neu_nach=40.0,
    balken_breite=36,
    schiesst=True,
    spule=(-9.0 * 1.4, 0.0),  # Mitte der Spule (Pixel von der Mitte, +x = vorn)
    blitz=dict(schaden=26.0, reichweite=360.0, kegel=14.0, spruenge=4, sprung=110.0,
               abfall=0.7, takt=1.0, schadensart="kugel"),
    feld=dict(aufbau=2.5, dauer=10.0, laden=28.0, takt=1.2, radius=250.0, emp=2.2,
              stillstand=8.0),   # nur im Stand: so langsam (px/s) muss er sein
)

# Der Funkwagen (seit 0.34.111): Mast und Peilrahmen. Rechte Maustaste baut
# ihn auf (er steht dabei, `aufbau` Sekunden), R schaltet die Betriebsart:
#   PEILEN  gegnerische Kaempfer, Gegner und Fahrzeuge im Kreis `peilen`
#           werden fuer die eigene Seite markiert (Raute, Karte, auch im
#           Nebel) - und damit zum Ziel fuer den Werfer.
#   STOEREN im Kreis `stoeren` funken gegnerische Bots nicht, ihre
#           Markierungen verfallen, Spaehdrohnen fallen aus, und kein
#           gegnerischer Nachschub kommt an. Dafuer steht der Funkwagen
#           waehrenddessen auf der Karte der Gegner.
# Aufgebaut hoert er ausserdem die Bots der eigenen Seite im Kreis `funk`
# (nur mit der Regel FUNKSPRUECHE DER BOTS): was sie sehen, steht dann als
# Markierung im Funknetz der Seite. Nur fuer Menschen am Steuer.
FUNKWAGEN = dict(
    {k: v for k, v in TROSSWAGEN.items()
     if k not in ("zone", "entnahmen", "pause", "reparatur", "nur_mensch", "name", "marke")},
    marke="F2",
    name="FUNKWAGEN",
    hoechst=200.0,
    kreis=22.0,
    achse=24.0,
    einsteigen=54.0,
    leben=300.0,
    explosion_radius=70.0,
    explosion_schaden=60.0,
    fahrer_schaden=45.0,
    wrack_zeit=10.0,
    neu_nach=40.0,
    balken_breite=34,
    schiesst=True,
    mast=(-8.0 * 1.4, 0.0),   # Pixel von der Mitte, +x = vorn
    aufbau=3.0,
    stillstand=8.0,           # nur im Stand: so langsam (px/s) muss er sein
    takt=1.0,                 # so oft wirkt er (s)
    peilen=470.0,
    stoeren=420.0,
    funk=900.0,
    # Der Peilkopf auf dem Mast (seit 0.34.124 ein 3D-Modell, art_funkmast.py):
    # aufgebaut dreht er sich so schnell (Grad/s); beim Abbau dreht er erst
    # zurueck in Fahrtrichtung, damit er eingeklappt laengs auf dem Dach liegt.
    kopf_dreh=75.0,
)

# Der Werfer (seit 0.34.112): Steilfeuer ueber die halbe Karte. Rechte
# Maustaste baut ihn auf (im Stand, `aufbau` Sekunden), dann schiesst die
# linke eine SALVE: `raketen` Raketen im Abstand `abstand`, Flugzeit `flug`,
# Streukreis `streu`; jede wirkt im Kreis `radius`. Geschossen wird nur dorthin,
# wo ein gueltiges Ziel der eigenen Seite ist (im Umkreis `umkreis`): ein
# Gegner oder Fahrzeug, das jemand der Seite sieht (`sicht`) oder das markiert
# ist (Drohne, Horchposten, Funkwagen), die Hotzone, spaeter weitere
# Objectives (Gefecht.werfer_ziele). Am Ziel zaehlen rote Kreise herunter, und
# jede Salve verraet ihn `verraten` Sekunden (markiert fuer die Gegner, eigenes
# Zeichen auf Karte und Minikarte). Sehr leicht zu zerstoeren, dann eine
# grosse Explosion, die alle im Umkreis toetet. Nur fuer Menschen am Steuer.
WERFER = dict(
    {k: v for k, v in TROSSWAGEN.items()
     if k not in ("zone", "entnahmen", "pause", "reparatur", "nur_mensch", "name", "marke")},
    marke="W",
    name="WERFER",
    hoechst=170.0,
    kreis=22.0,
    achse=24.0,
    einsteigen=54.0,
    leben=120.0,
    schiesst=True,
    # Die groesste Explosion des Spiels (seit 0.34.120): wer bis `explosion_tot`
    # Pixel danebensteht - der Fahrer immer -, stirbt sofort; bis
    # `explosion_radius` reisst es noch Leben (Fahrzeuge `explosion_fahrzeug`).
    # Kein Wrack: `wrack_zeit` ist nur die Zeit, bis der Wagen aus der Welt ist.
    explosion_radius=330.0,
    explosion_tot=210.0,
    explosion_schaden=400.0,
    explosion_fahrzeug=700.0,
    fahrer_schaden=9999.0,
    wrack_zeit=0.6,
    neu_nach=60.0,
    balken_breite=30,
    aufbau=2.5,
    dreh=110.0,               # so schnell dreht sich das Gestell zum Zeiger (Grad/s)
    stillstand=8.0,
    rohr=(-15.0 * 1.4, 0.0),  # Mitte des Gestells (Pixel von der Mitte, +x = vorn)
    # Das Gestell (seit 0.34.123, art_werfer.py): so steil stehen die Rohre
    # bei einem Ziel ganz nah und ganz weit (Grad), so schnell richten sie sich
    # (Grad/s).
    hub=(56.0, 32.0),
    hub_dreh=28.0,
    # Seit 0.34.135 (gewuenscht: "jede soll was staerker sein und einen groesseren
    # Radius haben", "mehr spread out"): 6 Raketen in einem Ring um die Mitte
    # (`formation` mal streu weit, eine in die Mitte), je `wackeln` px versetzt.
    # Seit 0.34.138 deutlich staerker gegen Fahrzeuge (gewuenscht: "besonders
    # gegen gepanzerte, es ist schwer genug, sie ueberhaupt zu treffen"):
    # 240 statt 165, und ein Volltreffer auf dem Wagen `volltreffer`-fach.
    salve=dict(raketen=6, abstand=0.5, flug=3.6, streu=150.0, radius=66.0, schaden=120.0,
               fahrzeug=240.0, volltreffer=1.7, nachladen=14.0, nah=400.0, weit=3200.0, umkreis=130.0,
               formation=0.72, wackeln=22.0,
        weit_karte=0.5,      # seit 0.34.134: aufgebaut reicht er ueber die halbe Kartenbreite (mindestens weit)
               sicht=420.0, verraten=6.0, hoch=150.0, pruefen=0.4,
               # Die Rohre laden einzeln wieder (seit 0.34.120): das erste `nachladen_ab`
               # Sekunden nach dem letzten Start, dann je `nachladen_je` Sekunden eines.
               nachladen_ab=3.0, nachladen_je=1.75, reihenfolge=(0, 3, 1, 4, 2, 5)),
    # Wohin er schiessen darf (seit 0.34.135, gewuenscht: "ueberall in die
    # aufgedeckten Bereiche des ganzen Teams", etwas ueber die Sicht hinaus):
    # um jeden eigenen Kaempfer SCHLACHT karte_sicht + sicht_rand, um jeden
    # Eroberungspunkt und die Hotzone ihr Kreis + punkt_rand, um jeden
    # markierten Gegner `feind`, und wo Aufklaerung (Drohne, Tragschrauber)
    # vorbeikam, bleibt `spur_dauer` s lang ihr Kreis (alle `spur_takt` s ein
    # Fleck). Auf der Karte des Werfers tuerkis.
    zonen=dict(sicht_rand=220.0, punkt_rand=320.0, feind=420.0, spur_dauer=25.0, spur_takt=0.5),
)

# Der Tragschrauber (seit 0.34.113): fliegt ueber Mauern, Felsen und die Front.
# Am Boden ein kleiner schwacher Wagen; ab `abheben` px/s hebt er ab, fliegt
# mit `flug_min` bis `flug_hoechst` px/s (stehen bleiben geht nicht), E setzt
# zur Landung an. In der Luft treffen ihn nur Schuesse, die auf ihn gezielt
# sind (die Maus ueber seinem Bild, siehe luft.py), und Flak. Er sieht die
# Gegner unter sich (`aufklaerung` px, markiert sie fuer die Seite) und wirft
# `bomben` Bomben; nachgeladen wird nur am Boden. Nur fuer Menschen.
TRAGSCHRAUBER = dict(
    {k: v for k, v in dict(FAHRZEUG, **PANZERWAGEN).items()
     if k not in ("plaetze", "ring", "ring_dreh", "ring_muendung", "ring_ruecklauf",
                  "ring_ruecklauf_tempo", "vorn", "hinten", "halb", "reifen_abstand",
                  "reifen_teilung", "unscharf_ab", "ramm_schwelle", "ramm_je_px",
                  "ramm_stoss", "ramm_extra")},
    marke="H",
    name="TRAGSCHRAUBER",
    hoechst=110.0,            # am Boden
    kreis=14.0,
    achse=16.0,
    einsteigen=48.0,
    leben=140.0,
    schiesst=True,
    explosion_radius=60.0,
    explosion_schaden=60.0,
    fahrer_schaden=70.0,
    wrack_zeit=10.0,
    neu_nach=45.0,
    balken_breite=30,
    abheben=100.0,
    flug_hoechst=260.0,
    flug_reise=190.0,
    flug_min=140.0,
    flug_beschl=120.0,
    drehen=70.0,              # Grad je Sekunde (bei Hoechstfahrt)
    hoehe=64.0,               # so hoch im Bild ueber seinem Schatten
    steigen=2.0,
    sinken=44.0,              # px/s beim Landen
    landen_tempo=60.0,
    aufklaerung=300.0,
    aufklaerung_takt=1.0,
    bomben=2,
    bomben_nachladen=3.0,
    bomben_nachladen_luft=9.0,   # seit 0.34.135: in der Luft laedt er auch nach, langsamer
    # Seit 0.34.123 eine kleine Schrottbombe (Blechdose mit Lunte, art_bombe.py),
    # von Hand neben der Kanzel fallen gelassen (`abwurf`: Spielpixel, +x vorn,
    # +y rechts): senkrecht, ohne sein Tempo, eine nach der anderen; im Fall
    # ueberschlaegt sie sich (`ueberschlag` Grad je Sekunde).
    # volltreffer (seit 0.34.138): landet die Bombe auf einem Fahrzeug, schlaegt
    # sie durch die Panzerung - so viel mal den Fahrzeugschaden; daneben wie bisher.
    bombe=dict(fall=1.1, radius=62.0, schaden=110.0, fahrzeug=140.0, volltreffer=2.2, pause=0.6,
        schwung=0.5,             # seit 0.34.135: so viel vom Tempo des Tragschraubers behaelt die Bombe
               abwurf=(9.0, 8.0), ueberschlag=260.0),
    luft_radius=24.0,         # so gross ist er als Ziel (Pixel um sein Bild)
    # Abschuss in der Luft (seit 0.34.127, gewuenscht): die Insassen sind
    # sofort tot, das Wrack faellt mit seinem Schwung weiter (`bremse`: so
    # viel Tempo verliert es je Sekunde in der Luft, `schwere` in px/s^2),
    # dreht sich und brennt. Prallt es an etwas, das hoeher ist als es selbst
    # gerade (Mauer, Fels), verliert es den Schwung (`abprall`: so viel kommt
    # zurueck) und rutscht dort herunter. Am Boden schlaegt es auf.
    absturz=dict(schwere=230.0, bremse=0.35, drehen=150.0, rauch_takt=0.05, abprall=0.18,
                 zurueck=96.0),       # so weit (px) sucht es rueckwaerts einen Platz zum Liegen
)

# Der Flakwagen (seit 0.34.114): ein Laster mit einem Vierling auf der
# Pritsche - ein Panzerwagen, dessen Ring-MG gegen die Luft gebaut ist.
# Fahren duerfen ihn nur Bots (`nur_bot`; gewuenscht: ein Mensch koennte
# Boden- und Luftziel nicht auseinanderhalten - der Bot schon): ein Abwurf
# bringt einen Bot der Seite gleich mit. Der Vierling schiesst ueber die
# `flak_kanone`-Zeile (FAHRZEUG_WAFFEN) und rastet auf Luftziele ein (luft.py).
FLAKWAGEN = dict(
    {k: v for k, v in PANZERWAGEN.items() if k not in ("plaetze", "marke", "name")},
    marke="FL",
    name="FLAKWAGEN",
    # Seit 0.34.138 auch fuer Menschen (gewuenscht) - vorher nur_bot, und
    # er fiel mit einem Bot darin.
    flak=True,
    hoechst=240.0,
    leben=520.0,
    vorn=46.0, hinten=-44.0,
    # Die Lafette sitzt weiter hinten auf der Pritsche und dreht schneller als
    # der MG-Ring: sie muss einem Flieger folgen.
    ring=(-25.2, 0.0),
    ring_dreh=190.0,
    ring_muendung=38.0,
    explosion_radius=84.0,
    explosion_schaden=85.0,
    fahrer_schaden=50.0,
    neu_nach=40.0,
)

# Huellen genau wie die Bilder (seit 0.34.138, gemeldet: "mit unsichtbaren
# Teilen an Waenden stecken bleiben, durch Fahrzeuge durchlaufen, zum Teil in
# Waenden drin"). Gemessen an den Bildern (deckende Pixel): die Kastenwagen
# bekommen vorn/hinten/halb, die mit zwei Kreisen einen Radius = halbe Breite
# und eine Achse, mit der die Laenge stimmt; `mitte` schiebt beide Kreise
# entlang der Achse, wo das Bild nicht mittig sitzt. Vorher waren die meisten
# kleiner als ihr Bild (Trosswagen 105 x 43 gegen 122 x 62, Krad mit
# Beiwagen 38 x 18 gegen 52 x 45).
for _d, _h in ((PANZER, dict(vorn=48.0, hinten=-46.0, halb=31.0)),
               (PANZERWAGEN, dict(vorn=48.0, hinten=-48.0, halb=25.0)),
               (JAGDPANZER, dict(vorn=46.0, hinten=-48.0, halb=31.0)),
               (FLAKWAGEN, dict(vorn=47.0, hinten=-46.0, halb=26.0)),
               (FAHRZEUG, dict(kreis=18.0, achse=8.0, mitte=1.0)),
               (KRAD, dict(kreis=22.0, achse=4.0, mitte=0.0)),
               (TROSSWAGEN, dict(kreis=31.0, achse=30.0, mitte=-3.0)),
               (SPULENWAGEN, dict(kreis=26.0, achse=21.0, mitte=0.0)),
               (FUNKWAGEN, dict(kreis=25.0, achse=22.0, mitte=-2.0)),
               (WERFER, dict(kreis=26.0, achse=20.5, mitte=2.5)),
               (TRAGSCHRAUBER, dict(kreis=20.0, achse=18.0, mitte=-6.0))):
    _d.update(_h)

# Schieben (seit 0.34.138, gewuenscht: "leichte Fahrzeuge koennen gepusht
# werden, indem man dagegen faehrt, schwere von anderen schweren"): wer Gas
# gibt (mehr als `gas`) und an einen Wagen stoesst, schiebt ihn mit `tempo`
# px/s (mal Gas) - wenn sein `gewicht` mindestens so gross ist und der andere
# leicht (1) ist oder er selbst nicht leicht. Wracks auch.
# Abschleppen mit dem Trosswagen (seit 0.34.138): ein leerer Wagen bis `fang`
# px um die Zone hinten wird mit der rechten Maustaste angehaengt; er haengt
# `abstand` px hinter der Kupplung und reisst ab, wenn er weiter als `reissen`
# px zurueckbleibt (an einer Mauer festgehakt). Ziehen kann er Leichtes und
# Mittleres (K.SCHIEBEN gewicht), keinen Panzer.
ABSCHLEPPEN = dict(fang=30.0, abstand=6.0, reissen=70.0)

SCHIEBEN = dict(gas=0.3, tempo=70.0,
                gewicht=dict(buggy=1, krad=1, tragschrauber=1, trosswagen=2, funkwagen=2,
                             spulenwagen=2, werfer=2, flakwagen=2, panzerwagen=2,
                             panzer=3, jagdpanzer=3))

# Flak gegen Luftziele: wie viel mehr eine Flak-Kugel dort wiegt, und wie weit
# ein Bot einen Flieger sucht (ein Bot am Steuer; Tragschrauber, Drohnen,
# Abwuerfe, Fallschirmjaeger). `streu` ist der Bot-Fehler beim Vorhalten.
FLAK = dict(bot_reichweite=680.0, bot_winkel=7.0,
            # Die Wolke (seit 0.34.118): platzt eine Flakgranate nahe an einem
            # Luftziel - Zeitzuender am Zielpunkt oder Annaeherung auf `naeher`
            # Pixel -, trifft sie es immer, mit `luft_schaden` in der Mitte und
            # `luft_abfall` weniger am Rand von `luft_radius`. Am Boden ein
            # kleiner Splitterkreis.
            luft_schaden=75.0, luft_radius=64.0, luft_abfall=0.35, naeher=44.0,
            boden_radius=40.0, boden_fahrzeug=14.0,
            # Was an Fallschirmen haengt: Kisten und Medkits platzen mit einem
            # Treffer, Fahrzeuge halten `fahrzeug_leben` aus - dann reisst der
            # Schirm, sie stuerzen mit bis zu `riss_tempo` px/s (Beschleunigung
            # `riss_beschl`) und kommen mit `absturz_leben` ihrer Leben an.
            kiste_leben=60.0, fahrzeug_leben=200.0, riss_beschl=420.0, riss_tempo=620.0,
            absturz_leben=0.04,
            # Der Flakwagen einer Basis (seit 0.34.117) wartet, bis ein anderes
            # Fahrzeug seiner Seite mit Fahrer mehr als `konvoi_los` px von
            # seinem Startort weg ist, und faehrt dann hinter ihm her,
            # `konvoi_abstand` px dahinter. Ohne Vordermann steht er.
            konvoi_los=350.0, konvoi_abstand=240.0)

# Rammen und was danach fliegt (seit 0.34.59). Gilt fuer beide.
RAMMEN = dict(
    sperre=0.4,               # so lange kein zweiter Schaden vom selben Fahrzeug
    # Wer beim Rammen stirbt, fliegt noch ein Stueck mit Drehung weiter
    # und hinterlaesst einen Spritzer in Flugrichtung.
    flug_kurz=0.12,
    flug_lang=0.6,
    flug_je_tempo=1.0 / 500.0,
    flug_bremse=3.5,
    flug_dreh=700.0,
    wackeln=4.0,
)

# Der Einschlag der Panzerkanone (seit 0.34.59, entities.Feuerball). Aus
# dem abgenommenen Video: groesser als Granate und C4, nichts davon rund.
# Zeiten in Sekunden, Masse in Pixeln.
FEUERBALL = dict(
    ballen=9,                     # Glutballen, versetzt und zeitversetzt
    ballen_streuung=11.0,
    ballen_radius=(5.0, 12.0),
    ballen_start=0.09,            # so spaet geht der letzte auf
    ballen_dauer=(0.17, 0.34),
    # Innen hell, aussen dunkel: (Anteil am Radius, Farbe)
    glut=((1.0, (170, 70, 20)), (0.7, (240, 150, 50)), (0.38, (255, 238, 190))),
    wolken=10,                    # dunkler Rauch danach
    wolken_streuung=13.0,
    wolke_klein=(3.0, 6.0),
    wolke_gross=(9.0, 16.0),
    wolke_start=(0.07, 0.24),
    wolke_dauer=(1.15, 1.85),
    wolke_deckkraft=105,
    wind_x=(6.0, 12.0),           # Rauch treibt ab (px/s)
    wind_y=(-6.0, -2.0),
    rauch_farben=((52, 46, 42), (66, 58, 52), (40, 36, 33)),
    dauer=2.2,                    # danach ist alles verflogen
    krater=15.0,                  # Radius des Kraters im Boden
    funken=60,
    kamera=6.0,
    # Seit 0.34.96 mit Tiefe (gewuenscht: "etwas nach 3D"): die Glut steigt
    # als Pilz auf, der Rauch als Saeule, am Boden laeuft eine flache
    # Druckwelle (eine Ellipse wie von schraeg oben) aus, und Brocken
    # fliegen in Boegen hoch - mit Schatten am Boden, damit man sieht, wie
    # hoch sie sind.
    steigen=30.0,                 # so hoch steigt die Glut (px)
    rauch_steigen=26.0,           # so schnell steigt der Rauch (px/s)
    druckwelle=(0.32, 96.0, 0.55),  # Dauer, Radius, Hoehe der Ellipse (x Breite)
    druck_farbe=(255, 214, 160),
    brocken=16,
    brocken_tempo=(50.0, 150.0),  # zur Seite (px/s)
    brocken_hoch=(120.0, 230.0),  # nach oben (px/s)
    schwere=420.0,                # zieht sie wieder herunter (px/s^2)
    brocken_farben=((62, 50, 40), (96, 78, 58), (40, 32, 26), (138, 104, 66)),
)

# Die Waffen der Fahrzeuge. Nicht in WAFFEN: niemand traegt sie in der
# Hotbar, und das Loadout soll sie nicht anbieten. Geschossen wird ueber
# dieselben Geschosse und denselben Knall (Welt.schussknall).
# ── Panzerung und Schadensarten (seit 0.34.65) ─────────────────────
#
# Gemeldet: "verschiedenen Schaden, verschiedene Health Pools,
# verschiedene Panzerungen und die ganzen Waffen und Granaten gegen
# Fahrzeuge". Jeder Treffer an einem Fahrzeug hat eine Art, und jede
# Fahrzeugart nimmt davon ihren Anteil. Figuren kennen keine Arten: an
# ihnen kommt immer alles an.
#
#   kugel           Gewehre, MPs, MGs - zerkratzen Blech
#   panzerbrechend  Panzerbuechse, Kanone - gehen durch
#   spreng          Granaten, Druckwellen - wirken auf Flaeche, nicht durch
#   hohlladung      Raketen, Haftladung, C4 - dafuer gebaut
#   feuer           Molotow, brennender Boden - Blech brennt nicht
#   nahkampf        Brecheisen, Krallen
#   ramm            Rammen
#
# Ohne Art (alte Aufrufe, Testmodus, Befehle) kommt alles an.
PANZERUNG = {
    "buggy": dict(kugel=1.0, panzerbrechend=1.3, spreng=1.0, hohlladung=1.5,
                  feuer=0.6, nahkampf=0.5, ramm=1.0),
    # Seit 0.34.95 gegen Panzerabwehr empfindlicher (gemeldet: "kein so
    # unzerstoerbares Ding"); das Leben bleibt, Kugeln prallen weiter ab.
    "panzerwagen": dict(kugel=0.35, panzerbrechend=1.3, spreng=0.85, hohlladung=1.7,
                        feuer=0.25, nahkampf=0.15, ramm=0.6),
    "panzer": dict(kugel=0.12, panzerbrechend=0.85, spreng=0.45, hohlladung=1.35,
                   feuer=0.1, nahkampf=0.05, ramm=0.4),
    # Seit 0.34.107. Das Krad hat kein Blech (wie der Buggy, nur ohne Bonus
    # gegen Panzerbrechendes); der Jagdpanzer ist ein Panzer, nur noch dicker.
    "krad": dict(kugel=1.0, panzerbrechend=1.2, spreng=1.0, hohlladung=1.3,
                 feuer=0.8, nahkampf=0.7, ramm=1.0),
    # Der Trosswagen: Blech wie ein Laster, leicht gepanzert.
    "trosswagen": dict(kugel=0.7, panzerbrechend=1.2, spreng=1.0, hohlladung=1.4,
                       feuer=0.5, nahkampf=0.4, ramm=0.8),
    # Der Spulenwagen: Keramik und Blech, wie ein Panzerwagen.
    "spulenwagen": dict(kugel=0.4, panzerbrechend=1.2, spreng=0.9, hohlladung=1.5,
                        feuer=0.3, nahkampf=0.2, ramm=0.7),
    "funkwagen": dict(kugel=0.8, panzerbrechend=1.2, spreng=1.0, hohlladung=1.4,
                      feuer=0.5, nahkampf=0.4, ramm=0.9),
    # Der Werfer: ein duenner Laster, jeder Treffer zaehlt.
    "werfer": dict(kugel=1.0, panzerbrechend=1.2, spreng=1.2, hohlladung=1.5,
                   feuer=1.0, nahkampf=0.6, ramm=1.0),
    # Der Tragschrauber: dünnes Blech.
    "tragschrauber": dict(kugel=1.0, panzerbrechend=1.2, spreng=1.5, hohlladung=1.5,
                          feuer=1.2, nahkampf=0.8, ramm=1.0),
    # Der Flakwagen: Laster mit Schild, etwas weniger Blech als der Panzerwagen.
    "flakwagen": dict(kugel=0.5, panzerbrechend=1.3, spreng=0.95, hohlladung=1.7,
                      feuer=0.35, nahkampf=0.2, ramm=0.7),
    "jagdpanzer": dict(kugel=0.1, panzerbrechend=0.8, spreng=0.4, hohlladung=1.25,
                       feuer=0.1, nahkampf=0.05, ramm=0.35),
}
# Woher ein Treffer kommt: vorn ist das Blech am dicksten, hinten am
# duennsten. Gilt fuer Treffer, die eine Richtung haben (alles ausser
# Feuer); Grenzen in Grad zwischen Fahrtrichtung und Herkunft.
PANZER_SEITEN = dict(vorn=0.75, seite=1.0, hinten=1.4,
                     vorn_bis=50.0, hinten_ab=130.0,
                     ohne=("feuer",))

# EMP-Granate (seit 0.34.65): legt Motor, Lenkung und Waffen jedes
# Fahrzeugs im Kreis still. Kein Schaden, an Figuren nichts.
EMP = dict(radius=130.0, dauer=4.5, funken_takt=0.09)

# Was ein Fahrzeug hinten heraus werfen kann (seit 0.34.65). Der Fahrer
# loest es mit R (Hecknebel) bzw. F (Nagelstreuer) aus - die Tasten, die
# am Steuer sonst nichts tun. Ladungen je Leben des Fahrzeugs.
FAHRZEUG_HILFE = dict(
    hecknebel=dict(ladungen=2, takt=6.0, wolken=3, abstand=26.0, radius=58.0,
                   dauer=9.0, arten=("buggy", "panzerwagen", "panzer")),
    nagelstreuer=dict(ladungen=2, takt=4.0, arten=("buggy", "panzerwagen")),
)
# Das Nagelfeld hinter dem Wagen: Reifen gehen platt (der Wagen wird
# langsam). Ketten stoert es nicht, Wesen auch nicht (Waffenpaket,
# KRAEHENFUESSE: "kein Effekt bei Wesen").
NAEGEL = dict(radius=34.0, dauer=22.0,
              platt_dauer=6.0, platt_tempo=0.5, platt_schaden=30.0,
              ketten=("panzer",), anzahl=16)

FAHRZEUG_WAFFEN = {
    "kanone": dict(
        name="KANONE",
        schaden=150.0,        # bei einem Treffer, dazu die Druckwelle
        flaeche=95.0,         # Druckwelle in der Mitte
        radius=40.0,          # Flaechenschaden (im Paket 34 px)
        tempo=700.0,          # Granate, mit dicker Leuchtspur
        reichweite=900.0,
        geschosse=1,
        takt=2.6,             # Nachladen
        kamera=4.0,
        muendung=2.4,         # Muendungsblitz so viel groesser
        schub=300.0,
    ),
    # Die Kanone des Jagdpanzers (seit 0.34.107): weiter, haerter, langsamer
    # geladen; die Druckwelle klein - sie soll Blech knacken, keine Gruppen.
    "jagdkanone": dict(
        name="JAGDKANONE",
        schaden=190.0,
        flaeche=45.0,
        radius=26.0,
        tempo=900.0,
        reichweite=1400.0,
        geschosse=1,
        takt=3.4,
        kamera=4.5,
        muendung=2.6,
        schub=240.0,
    ),
    "bug_mg": dict(
        name="BUG-MG",
        schaden=13.0,
        tempo=520.0,
        reichweite=620.0,
        geschosse=1,
        takt=1.0 / 11.0,      # rund 11 Schuss je Sekunde
        streuung=2.5,
        kamera=0.6,
    ),
    # Der Vierling des Flakwagens: seit 0.34.118 keine MG-Kugeln mehr, sondern
    # langsam (gut zwei Schuss je Sekunde) abgefeuerte Granaten mit Zeitzuender,
    # die nach der Strecke bis zum Zielpunkt platzen (fahrzeug.Flakgranate,
    # K.FLAK). `schaden` gilt nur fuer die Splitter am Boden.
    "flak_kanone": dict(
        name="FLAK-VIERLING",
        schaden=26.0,
        tempo=780.0,
        reichweite=900.0,
        geschosse=1,
        takt=0.42,
        streuung=0.8,
        kamera=1.6,
        muendung=1.8,
        flak=True,
    ),
    "ring_mg": dict(
        name="RING-MG",
        schaden=13.0,
        tempo=520.0,
        reichweite=620.0,
        geschosse=1,
        takt=1.0 / 12.0,
        streuung=2.0,
        kamera=0.6,
    ),
}

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
    # Gestaffeltes Denken (seit 0.34.135, gewuenscht: "die Rechenleistung der
    # Bots aufteilen, muss aber fluessig laufen"): ab `staffel` [i][0] Bots
    # denkt jeder nur jeden [i][1]. Schritt (versetzt, mit der ganzen
    # vergangenen Zeit). Dazwischen gilt seine letzte Eingabe weiter -
    # Laufen, Zielen, Gas und Lenkung bleiben am Kaempfer stehen. Bei 120
    # Schritten je s sind das 60 oder 40 Entscheidungen je s und Bot.
    # Seit 0.34.142 (gewuenscht: "die Performance bei Schlacht deutlich
    # verbessern"): ab 30 Bots jeden 4. Schritt (30 Entscheidungen je s - gut
    # unter der Reaktionszeit eines Menschen), ab 100 jeden 6. Gemessen auf
    # FLUSSTAL mit 24 je Seite dachten die Bots 42 Prozent jedes Schritts.
    staffel=((30, 4), (100, 6)),
    # Und wer weiter als `fern_ab` px von jedem Menschen weg ist (gut
    # anderthalb Bildbreiten), denkt nur jeden `fern_jede`. Schritt - ab
    # `fern_ab_bots` Bots, und nur, wenn Menschen mitspielen (seit 0.34.142).
    fern_ab=1000.0, fern_jede=12, fern_ab_bots=16,
    # Luftziele (seit 0.34.138): ohne Gegner am Boden schiessen Bots auf
    # Tragschrauber und Drohnen bis `luft_weite` px (und Waffenreichweite),
    # suchen alle `luft_takt` s, reagieren `luft_reaktion` s langsamer als
    # auf Bodenziele, feuern in Stoessen (an, aus in s) und verfehlen im
    # Kreis von `luft_fehler` mal dem Zielradius (nicht zu stark).
    luft_weite=560.0, luft_takt=0.3, luft_reaktion=0.4, luft_stoss=(0.6, 0.9),
    luft_fehler=2.2,
    # So lange (s) geht ein Bot gegen gesehene Fallschirmjaeger in Deckung,
    # nachdem er sie zuletzt sah (seit 0.34.100).
    springer_merken=4.0,
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
    # Seit 0.34.135 um das neue Lauftempo kuerzer (vorher 0.45-0.85): alle
    # laufen 1,3 mal so schnell, ein Gegner steht also kuerzer offen - mit der
    # alten Zeit kam der Feuerschutz kaum noch zum Schuss (test_verhalten).
    reaktion=(0.35, 0.65),    # bis zum ersten Schuss auf ein neues Ziel (s)
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
    kehrt_winkel=150.0,       # weiter herum dreht er sich zurueck, wie er gekommen ist (Grad, 0.34.58)
    drall_zeit=3.0,           # ... gemerkt wird, wohin er sich drehte, so lange (s)
    drall_bremse=160.0,       # ohne Gegner nicht weiter herum als so viel (Drall, Grad; seit 0.34.91)
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
    # So lange gilt ein Gegner als im Kampf bekannt. Seit 0.34.80 ist er
    # danach nicht mehr vergessen (gemeldet: "Bots vergessen Gegner sehr
    # sehr schnell, was absolut unrealistisch ist"), sondern eine Spur,
    # die er vorsichtig prueft (spur_...). Laenger als 4 s hielt er sich
    # beim Bergen zu lange im Freien auf (tests/test_verhalten.py bergen).
    gedaechtnis=4.0,          # so lange sucht er dort, wo er einen zuletzt sah
    # Die letzten Stellen verschwundener Gegner (seit 0.34.80): erst
    # vorsichtig nachsehen, dann vergessen. Geprueft heisst: so nah dran,
    # oder in dieser Weite mit freier Sicht darauf. Was ein Kamerad
    # geprueft hat, gilt fuer alle in dieser Naehe.
    spur_dauer=45.0,          # so lange bleibt eine Spur offen (s)
    spur_nah=50.0,            # so nah heran, dann ist sie geprueft (px)
    spur_blick=160.0,         # ... oder so nah mit freier Sicht darauf
    spur_tempo=0.55,          # vorsichtig: so viel vom Lauftempo (bei Mut 0)
    spur_draufgaenger=0.8,    # ab so viel Mut geht er im vollen Tempo
    spur_zusammen=80.0,       # zwei Spuren so nah: eine
    spur_hoechstens=4,        # so viele merkt er sich
    erinnerung=20.0,          # so lange weiss er noch, wo einer stand - fuers Bergen (0.34.50)
    wunschabstand=dict(repetierer=230.0, sturm=200.0, lmg=240.0,
                       schrot=105.0, scharf=320.0,
                       # Aus dem Waffenpaket (seit 0.34.62) - fuer Bots, denen
                       # der Testmodus eine davon gibt (siehe `waffen`).
                       revolver=230.0, zwillinge=170.0, mp=150.0,
                       praezision=330.0, unterhebel=230.0, panzerbuechse=380.0,
                       doppelflinte=110.0, autoschrot=130.0, minigun=220.0,
                       # Seit 0.34.70: alle uebrigen Waffen, die ein Bot im
                       # Testmodus (spaeter: in seiner Klasse) bekommen kann.
                       granatwerfer=240.0, einwegwerfer=300.0, raketenbuendel=220.0,
                       bolzer=26.0, nagler=200.0, hammer=24.0, schockstab=22.0,
                       schlagring=16.0, kettensaege=20.0, wurfmesser=18.0, speer=44.0,
                       spule=330.0, kettenblitz=200.0, spiegellaser=260.0,
                       kugelblitz=240.0, flammenwerfer=90.0),
    # Wer ein MG hat, schiesst damit (seit 0.34.38): so viele Pixel
    # Abstand nimmt er hin, bevor er lieber die andere Waffe nimmt. Vorher
    # nahm der MG-Schuetze auf mittlere Weite das Sturmgewehr.
    waffe_vorzug=dict(lmg=90.0),
    reichweite=dict(repetierer=330.0, sturm=320.0, lmg=330.0,
                    schrot=185.0, scharf=330.0,
                    revolver=330.0, zwillinge=280.0, mp=260.0, praezision=330.0,
                    unterhebel=330.0, panzerbuechse=330.0, doppelflinte=170.0,
                    autoschrot=190.0, minigun=330.0,
                    granatwerfer=300.0, einwegwerfer=330.0, raketenbuendel=300.0,
                    bolzer=44.0, nagler=300.0, hammer=40.0, schockstab=36.0,
                    schlagring=26.0, kettensaege=32.0, wurfmesser=26.0, speer=62.0,
                    spule=330.0, kettenblitz=300.0, spiegellaser=330.0,
                    kugelblitz=330.0, flammenwerfer=125.0),
    # Womit ein Bot kaempfen kann (seit 0.34.70): alles ausser Wurf und C4,
    # die gehen ueber den Wurf (_werfen).
    kampf_arten=("schuss", "werfer", "rakete", "strahl", "kette", "kugel", "flamme",
                 "nahkampf"),
    # Seit 0.34.70: wovor er sich in Acht nimmt, und wie weit.
    gefahr_rand=12.0,         # so weit um Feuer, Gas und Fallen haelt er Abstand
    # Seit 0.34.80: liegt Feuer (Gas, eine Falle ...) auf dem Weg, geht er
    # aussen herum, statt hinein- und rueckwaerts wieder hinauszulaufen
    # (gemeldet). So weit voraus schaut er, so lange bleibt er bei der
    # gewaehlten Seite.
    gefahr_umweg_vor=110.0,
    # Feuerschutz beim Bergen (seit 0.34.80): so viel Pixel "naeher" zaehlt
    # ein Gegner mit freier Linie auf den Retter.
    schutz_retter_linie=250.0,
    gefahr_umweg_seite=2.5,
    gefahr_takt=0.15,         # so oft schaut er nach (s)
    spule_loslassen=0.92,     # bei so viel Ladung laesst er los
    spule_fehler=0.3,         # x Zielfehler, waehrend er die Spule laedt (seit 0.34.91)
    # Bots am Steuer (seit 0.34.71, nur wem der Testmodus es erlaubt -
    # im Gefecht fahren Bots weiter nicht, so gemeldet).
    fahren=dict(
        # Seit 0.34.138: wer in einem Wagen ohne Waffe sitzt (Buggy, Krad), jagt
        # keinen Gegner; kommt einer naeher als `unbewaffnet_aussteigen` px,
        # steigt er aus und sucht `unbewaffnet_pause` s lang keinen Wagen.
        unbewaffnet_aussteigen=300.0, unbewaffnet_pause=25.0,
        # Vorausschauend ausweichen (seit 0.34.138): ab `ausweichen_ab` px bis
        # zum Wegpunkt prueft er die Spur vor sich - so weit, wie er in
        # `ausweichen_zeit` s faehrt (zwischen min und max px) - und weicht in
        # diesen Winkeln aus; ist alles zu, faehrt er mit `ausweichen_gas`
        # weiter. Je Wagen hoechstens alle `ausweichen_takt` s neu gerechnet.
        # Steht in `ausweichen_nah` px vor der Nase etwas und ist er langsamer als
        # `ausweichen_rueck_tempo`, setzt er `ausweichen_rueck_zeit` s zurueck;
        # eine gewaehlte Seite haelt er `ausweichen_seite_halten` s.
        ausweichen_ab=20.0, ausweichen_zeit=0.9, ausweichen_min=40.0, ausweichen_max=220.0,
        ausweichen_winkel=(20.0, 40.0, 65.0, 90.0), ausweichen_gas=0.35, ausweichen_takt=0.12,
        ausweichen_nah=26.0, ausweichen_rueck_tempo=60.0, ausweichen_rueck_zeit=0.7,
        ausweichen_rueck_gas=0.7, ausweichen_seite_halten=2.0,
        # Wegpunkt dicht daneben (unter `ausweichen_ab`), mehr als `wand_rueck_winkel` Grad neben
        # der Nase, die an einer Wand steht, `wand_zeit` s lang langsamer als `wand_tempo` px/s und
        # um weniger als `wand_drehung` Grad gedreht: zurueck, bis vor der Nase Platz ist
        # (hoechstens `wand_rueck_max` s).
        # Kolonne (seit 0.34.140): faehrt ein besetzter Wagen vor ihm auf seiner Spur (seitlich
        # weniger als beide halben Breiten plus `kolonne_seite`), bleibt er `kolonne_abstand` px
        # dahinter und gibt erst auf `kolonne_auflauf` px mehr wieder Vollgas; steht der
        # Vordermann (unter `kolonne_steht` px/s), wartet er hoechstens `kolonne_warten` s.
        # Kommt er entgegen (mehr als `kolonne_gegen` px/s), halten sich beide `kolonne_rechts` Grad rechts.
        kolonne_abstand=34.0, kolonne_seite=10.0, kolonne_auflauf=70.0, kolonne_steht=12.0,
        kolonne_warten=4.0, kolonne_gegen=25.0, kolonne_rechts=28.0,
        kolonne_bremsweg=0.45,    # so viele Sekunden Annaeherung gehen zusaetzlich auf den Abstand
        kolonne_gleich=0.5,       # cos des Winkels zwischen beiden Nasen: darueber gleiche Richtung, unter minus entgegen
        wand_rueck_winkel=45.0, wand_tempo=20.0, wand_zeit=0.6, wand_drehung=4.0, wand_rueck_max=1.0,
        abstand=dict(panzer=300.0, panzerwagen=200.0, buggy=0.0, krad=0.0, flakwagen=260.0,
                     jagdpanzer=520.0, spulenwagen=230.0),  # so weit bleibt er stehen
        suchen=700.0,         # so weit sucht ein Fahrer ohne Fahrzeug nach einem
        # Seit 0.34.95 faehrt er nach einem eigenen Wegenetz: nur Kacheln,
        # um die so viele Kacheln frei sind (wege.Fahrwegenetz), und er
        # zielt so viele Kacheln voraus, wie die Strecke gerade frei ist.
        weg_rand=1,
        weg_voraus=4,
        # Der Panzer nimmt ein Fahrzeug so viel lieber als einen Fussgaenger
        # (seit 0.34.96, in Pixeln Abstand).
        panzer_blech_vorzug=900.0,
        nah_rueckwaerts=70.0,     # naeher liegt ein Wegpunkt hinter ihm: rueckwaerts hin
        mg_winkel=10.0,
        steckt_nach=1.2,      # so lange ohne Fahrt, dann setzt er zurueck
        zurueck=1.0,          # so lange
        raus_unter=0.15,      # unter so viel Leben ueberlegt er, auszusteigen (seit 0.34.135 nicht immer):
        wrack_bleiben=0.35,   # ... so oft bleibt er drin bis zum Schluss
        wrack_fliehen=0.35,   # ... so oft steigt er aus und laeuft weg (sonst: aus und in Stellung)
        wrack_flucht_zeit=7.0,
        wrack_meiden=0.25,    # einen Wagen mit weniger Leben nimmt kein Bot
        fehler=14.0,          # Zielfehler am Ziel (px)
        # Aus Turm und Ring sieht man weiter als zu Fuss (330): die Kanone
        # reicht 900, und ein Panzer, der seine Gegner nicht sieht, ist nur
        # ein Hindernis (gemessen: Gegner auf 730 px blieben ungesehen).
        sicht=dict(panzer=720.0, panzerwagen=560.0, buggy=380.0, krad=380.0, flakwagen=560.0,
                   jagdpanzer=900.0, spulenwagen=440.0, trosswagen=380.0, funkwagen=380.0,
                   werfer=380.0, tragschrauber=520.0),   # seit 0.34.131 fahren Bots alle
        # Seit 0.34.84 (gemeldet nach einer grossen Fahrzeugschlacht):
        # Liegt das Ziel hinter ihm und weiter weg als das, wendet er
        # vorwaerts, statt die ganze Strecke rueckwaerts zu fahren.
        wenden_ab=140.0,
        panzer_drehen_ab=35.0,    # so schief: der Panzer dreht erst (fast) auf der Stelle
        panzer_drehen_gas=0.3,    # ... und rollt dabei so langsam mit
        # Die Kanone ist explosiv: feuern, wenn der Einschlag so nah am Ziel
        # liegt (x Splash-Radius), statt auf 5 Grad genau zu warten - und
        # auf einen, der eben hinter Deckung verschwand, solange die
        # Granate bis dicht an ihn herankommt.
        splash_anteil=0.6,
        verdeckt_merken=3.0,      # so frisch muss die letzte Sicht sein (s)
        # Zielwechsel im Fahrzeug: je Grad, den Turm/Wanne sich drehen
        # muessten, zaehlt ein Gegner so viel Pixel weiter weg.
        dreh_kosten=2.5,
        # Bug-MG: steht der Panzer, dreht er die Wanne zum Gegner.
        mg_ausrichten=True,
        # Zum Einsteigen geht er an die Seite (beim Panzerwagen reicht die
        # Front ueber den Einstiegsradius hinaus) - und das auch, wenn er
        # einen Gegner sieht, solange der Wagen so nah ist.
        einstieg_seite=10.0,      # so weit neben der Wanne
        einstieg_trotz_feind=320.0,
        einstieg_feind_nah=140.0, # ... ausser ein Gegner steht naeher als das
        # Schutz fuer Liegende (nicht im Buggy): zwischen einen liegenden
        # Kameraden und den Gegner fahren, wenn das nicht weit ist.
        schutz_weite=380.0,       # so weit faehrt er dafuer hoechstens
        schutz_vor=70.0,          # so weit vor dem Liegenden haelt er
        schutz_leben=0.4,         # nur mit mehr als so viel Leben des Wagens
    ),
    # Woraus ein Bot sein Loadout zieht (seit 0.34.62). Nur die alten fuenf:
    # mit Zweithand, Doppellauf, Bogen oder Einwegrohr kann die KI noch
    # nicht umgehen - und ein Bot mit einem Granatwerfer, den er nie
    # benutzt, waere nur ein Bot mit einer Waffe weniger.
    waffen=("repetierer", "sturm", "schrot", "scharf", "lmg"),
    # Wie oft eine davon gezogen wird (seit 0.34.94, Vorgabe 1): das MG nur
    # selten - gewuenscht, ein Trupp voller MGs sah nicht gut aus.
    waffen_gewicht=dict(lmg=0.1),
    # Mehr Vielfalt im Gefecht (seit 0.34.95, gewuenscht): so oft wird eine
    # gezogene Waffe gegen eine verwandte getauscht. Nur in echten Runden -
    # im Testmodus nur, wenn es eingeschaltet ist (BOTS: VIELE WAFFEN):
    # die Szenen in tests/test_verhalten.py rechnen mit den fuenf.
    vielfalt=0.45,
    varianten=dict(
        sturm=("mp", "unterhebel", "zwillinge"),
        repetierer=("unterhebel", "revolver", "praezision"),
        schrot=("autoschrot", "doppelflinte"),
        scharf=("praezision", "bolzer"),
        lmg=("minigun",),
    ),
    # Panzerjaeger (seit 0.34.95): gibt es in der Runde Fahrzeuge, traegt
    # ein Teil der Bots Panzerbuechse und Raketen. Wer es wird, entscheidet
    # die Zahl, nicht der Zufall: je Mannschaft so viele, wie fehlen.
    # Seit 0.34.96 viel seltener (gemeldet: "viel zu viele mit
    # Panzerbuechse") und meist mit Raketen: eine Panzerabwehrwaffe (der
    # Reihe nach aus `waffen`, nach Spielernummer) und eine gewoehnliche.
    panzerjaeger=dict(waffen=("raketenbuendel", "einwegwerfer", "raketenbuendel", "panzerbuechse"),
                      je_team=1, je_bots=8),
    # Waffenwahl gegen Fahrzeuge (seit 0.34.95, bots._beste_waffe): so viel
    # lieber nimmt er dann eine Panzerabwehrwaffe, und so viel weniger
    # gern die Einwegrakete gegen Figuren (in Pixeln Wunschabstand).
    panzerabwehr=dict(vorzug=400.0, einweg_sparen=500.0),
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
        # Seit 0.34.96 aus dem Fahrzeug: daran haengt das Funkgeraet.
        fahrzeug_kontakt=("ZIEL ERFASST!", "FEINDKONTAKT, FEUER FREI!"),
        fahrzeug_getroffen=("WIR WERDEN BESCHOSSEN!", "TREFFER AM BLECH!"),
        fahrzeug_vor=("RÜCKEN VOR!", "FAHREN ZUR FRONT!"),
        absetzen=("ABSITZEN, ABSITZEN!", "ALLE RAUS!"),
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
    # Nachschub am Kartenrand (seit 0.34.77, Testmenue): alle `takt` Sekunden
    # ein Bot fuer die kleinere Seite, bis `hoechstens` Bots leben; `rand`
    # Kacheln vom Kartenrand entfernt.
    nachschub=dict(takt=3.0, hoechstens=24, rand=3, hirn="goap"),
    einzelschritt=12,         # so viele Rechenschritte macht EIN SCHRITT (1/10 s)
    hoechstens_schritte=8,    # mehr Rechenschritte je Bild auch im Zeitraffer nicht
    # Testmenue BILDRATE (seit 0.34.58): das Spiel kuenstlich bremsen, um zu
    # hoeren, ob die Klaenge auch bei wenigen Bildern im Takt kommen. 0 = wie
    # in den Einstellungen.
    bildraten=(0, 30, 15, 8, 4),
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
    funk_blitz=0.6,           # so lange laeufen die Ringe, wenn ein Spruch durch ist oder abbricht (s, 0.34.58)
    welle_farben=((255, 72, 56), (226, 44, 40), (168, 26, 30)),   # innen hell, aussen tief
    welle_striche=6,          # so viele Striche hat ein Ring (seit 0.34.48)
    welle_dreh=1.6,           # so schnell drehen sie sich (Bogenmass je Sekunde)
    # Auf iPhone und iPad (seit 0.34.63): steuert man eine Figur, liegt der
    # Ziffernblock unter den Knoepfen der Touch-Steuerung. Dann steht dort
    # nur diese eine Taste NUM, die ihn aufklappt (x, y, Breite, Hoehe).
    touch_num=(414, 10, 44, 24),
    # Im Spawner und im Testmenue: wer auf das linke Drittel einer
    # Einstellung tippt, blaettert zurueck (es gibt keine rechte Maustaste).
    touch_zurueck=0.35,
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
    gedaechtnis=12.0,         # so lange behaelt der Trupp einen gemeldeten Gegner (s; 6 bis 0.34.79)
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
    # Unterwegs ohne Kontakt (seit 0.34.58): ein Keil hinter dem Anfuehrer,
    # wo Platz ist, sonst einer hinter dem anderen auf seiner Spur. Vorher
    # eine breite Linie vor ihm - eine Front ohne Gegner, und wer seitlich
    # zu seinem Platz lief und dabei nach aussen schaute, glitt (gemeldet).
    marsch_abstand=32.0,      # im Keil: so weit hinter dem Vordermann je Reihe
    marsch_breite=28.0,       # ... und so weit zur Seite je Reihe
    spur_abstand=30.0,        # wo es eng ist: so weit hintereinander auf der Spur des Anfuehrers
    marsch_keil=5,            # so viele gehen hoechstens im Keil des Anfuehrers; sind es mehr, ...
    gruppe_abstand=110.0,     # ... folgen weitere kleine Keile (je bis zu 5) so weit dahinter auf seiner Spur
    marsch_kehrt=100.0,       # dreht der Anfuehrer um mehr Grad um, werden die Plaetze neu verteilt
    entfalten_weite=520.0,    # so nah am Angriffsziel (oder an einem Verdacht) entfaltet er sich zur Linie
    fleck=22.0,               # naeher: zwei saessen beim Feuerschutz fuers Bergen auf einem Fleck (px, 0.34.58)
    fleck_strafe=100.0,       # ... das kostet so viel Weg - weniger als ein Platz ohne Schuss (VERWUNDET["schutz_ohne_schuss"])
    spur_laenge=48,           # so viele Punkte seiner Spur werden gemerkt (je Takt einer)
    marsch_tempo=0.75,        # so schnell geht der Anfuehrer - die anderen holen auf, ohne zu rennen
    marsch_dreh=15.0,         # die Marschrichtung dreht hoechstens so viel Grad je Takt
    marsch_mindest=15.0,      # langsamer (px/s) gilt der Anfuehrer als stehend: die Richtung bleibt
    marsch_toleranz=60.0,     # so weit darf einer im Marsch von seinem Platz sein, ohne hinzurennen
    marsch_warten=95.0,       # ist einer weiter zurueck, geht der Anfuehrer langsamer
    folgen_weite=40.0,        # naeher am Platz: weich mitgehen statt hinlaufen (px)
    halt_zeit=(2.5, 4.5),     # am Ziel sichert der Trupp so lange, bevor er weiterzieht (s)
    halt_abstand=(14.0, 26.0),  # ... und unterwegs alle so viele Sekunden einmal
    besuch_zelle=10,          # die Karte absuchen: in Feldern von so vielen Kacheln ...
    besuch_alt=90.0,          # ... und wo der Trupp so lange nicht war, lohnt es wieder (s)
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
    # Gestoert (Funkwagen der Gegner, seit 0.34.115): der Spruch geht nicht
    # raus, und der Anfuehrer versucht es so lange nicht noch einmal (s).
    funk_gestoert_pause=8.0,
    funk_abstand=300.0,       # so weit weg von jedem bekannten Gegner funkt er
    funk_weg_radien=(60.0, 110.0, 160.0, 220.0),   # so weit sucht er dafuer einen Platz
    funk_weg_zeit=8.0,        # laenger geht er nicht, dann funkt er, wo er ist
    funk_stoer=150.0,         # sieht er einen Gegner so nah (oder schiesst einer auf ihn), bricht der Spruch ab
    funk_gedaechtnis=12,      # so viele Sprueche zeigt der Testmodus
    funk_zeichen=1.4,         # so lange zeigt der Funker, ob sein Spruch durch ist oder abbrach (s, seit 0.34.58)
    funk_rest_vorrang=2.0,    # waehrend einer geborgen wird, geht ein Spruch nur vor, wenn er so nah am Ende ist (s, 0.34.58)
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
    # Das MG bleibt hier (0.34.94 geprueft): der eine MG-Schuetze haelt
    # nieder, ohne ihn standen grosse Trupps dichter (test_verhalten,
    # grosse_trupps). Sonst ziehen Bots das MG nur noch selten (BOTS
    # waffen_gewicht).
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
    # Die Faehigkeiten der Klassen (Taste C) im Gefecht (seit 0.34.79, bis
    # dahin nur im Testmodus). Was sie hinlegen, geht seitdem mit der
    # Weltmeldung an die Gaeste ("geraete").
    faehigkeiten=True,
    # KLASSE PFLICHT (seit 0.34.91): mit Loadouts spielt jeder eine Klasse;
    # wer ohne kommt, spielt KLASSE_PFLICHT_ERSATZ.
    klasse_pflicht=True,
    # So lange gilt eine angeforderte Waffe als gehalten, bis der Gastgeber
    # sie bestaetigt (Gruppen-Hotbar, seit 0.34.87).
    waffe_soll_gilt=0.6,
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
    # Aufgeben (seit 0.34.129, gewuenscht): wer am Boden liegt, haelt R so
    # lange gedrueckt, dann ist er tot und kommt neu (wie nach dem Verbluten).
    # RESPAWN im Escape-Menue tut dasselbe sofort, auch im Stehen. Wer kurz
    # davor (`wertung` s) von einem Gegner getroffen wurde, zaehlt fuer den
    # als Abschuss - sonst entzoege man sich so jedem Abschuss.
    aufgeben=2.5,
    wertung=8.0,
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
            "brecheisen": 0,
            # Aus dem Waffenpaket (seit 0.34.62), ebenfalls rund drei
            # Nachladungen. Das Einwegrohr hat keinen Vorrat: eines ist eines.
            "revolver": 24, "zwillinge": 72, "mp": 96, "praezision": 30,
            "unterhebel": 28, "panzerbuechse": 6, "doppelflinte": 12,
            "autoschrot": 24, "minigun": 240, "granatwerfer": 6,
            "einwegwerfer": 0, "raketenbuendel": 12},
    kiste_takt=14.0,          # Sekunden zwischen zwei Munitionskisten
    kiste_hoechstens=4,
    kiste_gibt=0.5,           # so viel vom vollen Vorrat gibt eine Kiste
)

# Der Ziellaser der Panzerbuechse (seit 0.34.62), fuer alle sichtbar:
# Farbe und Deckkraft der Linie, der Punkt am Ende, wie weit vor der Figur
# er anfaengt und wie weit er hoechstens reicht.
LASER = dict(farbe=(232, 44, 32), staerke=120, punkt=(255, 96, 70), ab=30.0,
             weite=1600.0)            # 900 bis 0.34.95 - endete vor dem Bildrand

# Kurzer heller Blitz bei jeder Explosion (seit 0.34.64, gemeldet: die
# kleinen Explosionen des Raketenbuendels waren kaum zu erkennen). dauer
# in Sekunden, je_radius: so gross im Verhaeltnis zum Wirkungskreis,
# mindestens/hoechstens in Pixeln.
LICHTBLITZ = dict(dauer=0.11, je_radius=0.9, mindestens=22.0, hoechstens=120.0,
                  farbe=(255, 214, 150), kern=(255, 250, 230))

# Was im Bogen fliegt (seit 0.34.64): die Hoehe zeigt sich als Groesse UND
# als Versatz nach oben im Bild - gemeldet: "die Flugkurve geht nach unten
# auf dem Bildschirm, sollte nach oben gehen". `hoch` Pixel je Pixel Hoehe.
BOGEN = dict(bilder=("teil_granate40",), hoch=0.55)

# Das leere Rohr des Einweg-Raketenwerfers (seit 0.34.62): so lange liegt
# es nach dem Ausrutschen, so lange qualmt es hinten, wie oft eine
# Rauchflocke kommt und wie weit hinter der Mitte das offene Ende liegt.
ROHR = dict(liegen=8.0, qualm=2.5, qualm_takt=0.09, hinten=13.0)

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
    # Seit 0.34.131 (Saetze gruen und stadt): der Baum ist hoeher als jede
    # Mauer, haelt aber nur mit dem Stamm und dem dichten Teil der Krone.
    "feldstein":  dict(hoehe=22.0, rahmen=(0, 0, 32, 32), form="block", fugen=2),
    "moosfels":   dict(hoehe=30.0, rahmen=(0, 0, 32, 32), form="block", fugen=3),
    "baum":       dict(hoehe=28.0, rahmen=(5, 5, 22, 22), form="rund", fugen=0),
    "ziegel":     dict(hoehe=28.0, rahmen=(0, 0, 32, 32), form="block", fugen=2),
    "beton":      dict(hoehe=26.0, rahmen=(0, 0, 32, 32), form="block", fugen=2),
    "truemmer":   dict(hoehe=12.0, rahmen=(3, 3, 26, 26), form="block", fugen=0),
    "wrack":      dict(hoehe=15.0, rahmen=(4, 1, 24, 30), form="block", fugen=1),
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
    # Seit 0.34.131: FLUSSTAL - Wiesen, Feldwege, bemooster Granit, Baeume,
    # Feldsteinmauern, Stege ueber das Wasser.
    "gruen": {"boden": ("gras", "gras_2", "gras_3", "gras_4"),
              "wand": "feldstein", "kaktus": "baum", "klippe": "moosfels",
              "bilder": {"fels": ("moosfels", "moosfels_2", "moosfels_3"),
                         "piste": ("feldweg", "feldweg_2", "feldweg_3", "feldweg_4"),
                         "kies": ("ufer", "ufer_2", "ufer_3", "ufer_4"),
                         "gestruepp": ("wiese", "wiese_2", "wiese_3", "wiese_4"),
                         "pflaster": ("gehweg", "gehweg_2", "gehweg_3")}},
    # Seit 0.34.131: KANALSTADT - Asphalt, Ziegelhaeuser, Betontruemmer,
    # Autowracks, Kanaele mit Bruecken, Parks mit Rasen und Baeumen.
    # Seit 0.34.135 ist der Boden der Bloecke heller Kopfstein ("hof") und
    # nicht Asphalt (gemeldet: "nicht erkennbar, was Teil des Gebaeudes und
    # was Teil der Strasse ist") - die dunkle Fahrbahn hebt sich ab.
    "stadt": {"boden": ("hof", "hof_2", "hof_3", "hof_4"),
              "wand": "ziegel", "kaktus": "baum", "klippe": "beton",
              "bilder": {"fels": ("beton", "beton_2", "beton_3"),
                         "brocken": ("truemmer", "truemmer_2", "truemmer_3"),
                         "schrott": ("wrack", "wrack_2", "wrack_3"),
                         "piste": ("strasse", "strasse_2", "strasse_3", "strasse_4"),
                         "kies": ("schutt", "schutt_2", "schutt_3", "schutt_4"),
                         "pflaster": ("gehweg", "gehweg_2", "gehweg_3"),
                         "gestruepp": ("rasen", "rasen_2", "rasen_3", "rasen_4"),
                         "dielen": ("fliesen", "fliesen_2"),
                         "wasser": ("kanal", "kanal_2", "kanal_3"),
                         "seicht": ("kanal_seicht", "kanal_seicht_2", "kanal_seicht_3"),
                         "gitter": ("kasernenplatz", "kasernenplatz_2", "kasernenplatz_3")}},
}

# Kachelsaetze mit Varianten (seit 0.34.131): "bilder" ersetzt die
# Abwechslungsbilder einer Kachelart (KACHELN bilder) - in FLUSSTAL ist der
# Fels bemoost und die Piste ein Feldweg, ohne neue Kachelarten. Was ein
# Satz nicht nennt, bleibt, wie es ist.
def satz_bild(satz: dict, daten: dict, variante: int = 0) -> str:
    """Das Bild einer Kachelart in diesem Satz, mit Abwechslung."""
    bilder = satz.get("bilder", {}).get(daten["name"]) or daten.get("bilder")
    if bilder:
        return bilder[variante % len(bilder)]
    return satz.get(daten["bild"], daten["bild"])

# Wie hoch ueber dem Boden etwas in der Welt ist, in Welt-Pixeln (seit
# 0.34.5). Gebraucht nur fuer die Frage, ob eine Mauer es verdeckt
# (render.Renderer.verdeckt): was tiefer ist als die Mauer und vom Auge
# aus dahinter liegt, ist nicht zu sehen; was darueber fliegt, schon.
# Gezeichnet wird alles weiter an seinem Fusspunkt, wie die Figuren -
# sonst saehe ein Treffer am Bildrand aus wie ein Fehlschuss.
# So viele Effekt-Teilchen (effekte.py) gibt es hoechstens auf einmal; die
# aeltesten fallen weg. Die Werfer-Explosion allein braucht gut 3700 - und
# keiner davon darf fehlen, sonst fiele ihr Feuerball zuerst weg.
EFFEKTE_HOECHSTENS = 4500

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
    # Fahrzeuge flach (seit 0.34.94, gewuenscht): kein Aufbau in die Hoehe.
    buggy=0.0,
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
# seicht    (seit 0.34.131) Wasser bis zum Knie: begehbar und befahrbar,
#           aber so viel langsamer (Faktor auf das Tempo, K.WASSER)
# sperrt    (seit 0.34.131) tiefes Wasser: niemand geht oder faehrt hinein,
#           aber es ist kein Hindernis fuer Kugeln, Sicht und Wuerfe - man
#           schiesst ueber den Fluss, man geht nicht hindurch
LEER, BODEN, GITTER, WAND, KISTE, TREPPE_HOCH, TREPPE_RUNTER, LUKE, \
    AUFZUG_HOCH, AUFZUG_RUNTER, FELS, BROCKEN, SANDSACK, HOLZKISTE, \
    KAKTUS, SCHROTT, PISTE, KIES, PFLASTER, GESTRUEPP, DIELEN, \
    WASSER_SEICHT, WASSER_TIEF, BRUECKE = range(24)

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
    # Seit 0.34.131 fuer FLUSSTAL und KANALSTADT (gewuenscht: "gerne auch
    # seichtes Wasser"). Zeichen + und %.
    WASSER_SEICHT: dict(name="seicht",   fest=False, sicht=False, bild="seicht",
                        bilder=("seicht", "seicht_2", "seicht_3"), weich=True,
                        seicht=True),
    WASSER_TIEF:   dict(name="wasser",   fest=False, sicht=False, bild="wasser",
                        bilder=("wasser", "wasser_2", "wasser_3"), weich=True,
                        sperrt=True),
    # Bohlen einer Bruecke ueber das Wasser (Zeichen |): Boden, aber man
    # sieht durch die Fugen den Fluss darunter.
    BRUECKE:       dict(name="bruecke",  fest=False, sicht=False, bild="steg",
                        bilder=("steg", "steg_2")),
}

# Wasser (seit 0.34.131): wie sehr seichtes Wasser bremst. Tiefes sperrt
# ganz (KACHELN sperrt) - darum gibt es dort Furten und Bruecken.
WASSER = dict(
    seicht_tempo=0.62,        # zu Fuss
    seicht_fahrzeug=0.72,     # Fahrzeuge (Ketten und Raeder kommen besser durch)
    spritzer_takt=0.22,       # so oft spritzt es um einen, der im Wasser laeuft (s)
    # Schwimmen im tiefen Wasser (seit 0.34.140, gewuenscht): wer zu Fuss ist,
    # kommt hinein (Fahrzeuge weiter nicht), schwimmt langsam, kann dashen,
    # aber nicht schiessen, werfen oder schlagen. Ueber Wasser ist nur der
    # Kopf - nur der wird getroffen (`kopf_radius` statt des Koerpers).
    schwimmen=True,
    schwimm_tempo=0.45,       # Faktor auf das Lauftempo
    kopf_radius=5.0,          # so gross ist, was ueber Wasser getroffen werden kann (px)
    koerper_deck=165,         # wie deutlich der Koerper unter Wasser zu sehen ist (0 bis 255)
    koerper_farbe=(120, 170, 196), # so faerbt das Wasser ihn ein
    platsch_ring=(4.0, 26.0, 0.7), # der Ring beim Hineingehen: von, bis (px), Dauer (s)
)

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
        # 13 -> 11,5 je Kugel (seit 0.34.91, gewuenscht): neben den neuen
        # Waffen war sie zu stark - 80 statt 91 mit allen sieben.
        schaden=11.5,
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
        # Mehr Streuung (seit 0.34.91, gewuenscht: 2,2 / 3,6 vorher) - der
        # Allesgut-Griff sollte die neuen Waffen nicht ueberfluessig machen.
        streuung=3.0,
        streuung_lauf=4.6,
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
        scope=True,           # Zielfernrohr mit der rechten Maustaste (seit 0.34.96)
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
        # Seit 0.34.96 deutlich schwaecher (gewuenscht): das Brecheisen ist
        # nur noch der Notbehelf; wer im Nahkampf etwas will, waehlt eine
        # Nahkampfwaffe fuer F (Loadout, NAHKAMPF["waehlbar"]).
        schaden=26.0,
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

    # ── Aus dem Waffenpaket (seit 0.34.62) ─────────────────────────────
    #
    # Zwoelf Eintraege aus `dustfront_waffen` (Schusswaffen und Werfer).
    # Die Zahlen sind ein erster Vorschlag: das Paket laesst sie bewusst
    # offen ("Werte mit dem Besitzer entscheiden"). Neu gegenueber den
    # alten Waffen sind nur Schalter, die der Code liest:
    #
    #   klang            welcher Schussklang (sonst "schuss_<name>")
    #   zweite_hand      rechte Maustaste feuert die zweite Waffe (eigener Takt)
    #   beide_laeufe     rechte Maustaste feuert beide Laeufe auf einmal
    #   nachladen_einzeln  `nachladen` ist die Zeit je Patrone; ein Schuss
    #                    unterbricht das Laden
    #   abfall_ab, abfall_rest  ab dieser Strecke wird der Schaden kleiner,
    #                    bis auf diesen Anteil am Ende der Reichweite
    #   tempo_faktor     so viel schneller laeuft, wer sie traegt
    #   fokus_schuss     so viel vom Zielen bleibt nach einem Schuss (sonst 0.25)
    #   fokus_mittellinie  die helle Linie in der Mitte des Kegels
    #   durchschlag      durch so viele Koerper geht ein Schuss
    #   durch_deckung    niedrige Deckung (Kisten, Sandsaecke) haelt ihn nicht
    #   gegen_fahrzeug   voller Schaden am Blech statt kugel_anteil
    #   laser            ein Ziellaser, den alle sehen
    #   stoss            so viel staerker schiebt ein Treffer
    #   einweg           ein Schuss, danach liegt das Rohr am Boden
    #   schlingern       so viele Grad pendelt eine Rakete hin und her
    "revolver": dict(
        art="schuss",
        name="REVOLVER",
        # Wenige, schwere Schuesse. Fächern leert die Trommel auf einmal.
        schaden=40.0,
        takt=0.38,
        magazin=6,
        nachladen=2.6,        # das Nachladen dauert
        streuung=1.0,
        streuung_lauf=3.2,
        geschosse=1,
        tempo=740.0,
        reichweite=620.0,
        rueckstoss=55.0,
        kamera=2.6,
        huelsen=0,            # die Huelsen bleiben in der Trommel
        klang="schuss_revolver",
        modi=("gezielt", "faechern"),
        # Seit 0.34.138 faechert die rechte Maustaste immer (gemeldet: "mit der
        # Rechtstaste kann man immer noch nicht das komplette Magazin
        # abfeuern") - ohne erst den Feuermodus umzuschalten.
        zweit="faechern",
        # Seit 0.34.87 deutlicher getrennt (gemeldet: "die zwei Feuermodi
        # beim Revolver funktionieren nicht"): GEZIELT ist praezise,
        # FAECHERN leert die restliche Trommel in einem Zug.
        modus_daten={
            "gezielt": dict(kurz="GEZIELT", streuung=0.4, streuung_lauf=2.2),
            "faechern": dict(kurz="FÄCHERN", takt=0.9, salve=6, salve_trommel=True,
                             salve_takt=0.06, schaden=32.0,
                             streuung=9.0, streuung_lauf=10.0),
        },
    ),
    "zwillinge": dict(
        art="schuss",
        name="ZWILLINGE",
        # Eine Pistole je Maustaste, jede mit eigenem Takt. Wer abwechselnd
        # drueckt, schiesst doppelt so schnell - aber nie genau.
        schaden=17.0,
        takt=0.2,
        magazin=24,           # zwoelf je Pistole
        nachladen=2.2,
        streuung=3.0,
        streuung_lauf=3.6,
        geschosse=1,
        tempo=700.0,
        reichweite=420.0,
        rueckstoss=16.0,
        kamera=1.0,
        huelsen=1,
        klang="schuss",
        zweite_hand=True,
        hand_abstand=4.0,     # so weit liegt jede Muendung neben der Mitte
    ),
    "mp": dict(
        art="schuss",
        name="MASCHINENPISTOLE",
        # Fuer schnelle Vorstoesse: sehr schnell, im Laufen genau, macht
        # flinker - und verliert auf Distanz deutlich.
        schaden=11.0,
        takt=0.065,
        magazin=32,
        nachladen=1.8,
        streuung=3.0,
        streuung_lauf=1.2,
        geschosse=1,
        tempo=640.0,
        reichweite=400.0,
        abfall_ab=160.0,
        abfall_rest=0.45,
        rueckstoss=10.0,
        kamera=0.7,
        huelsen=1,
        klang="schuss_mp",
        tempo_faktor=1.08,
    ),
    "praezision": dict(
        art="schuss",
        name="PRÄZISIONSGEWEHR",
        # Halbautomat zwischen Repetierer und Scharfschuetze. Rechte
        # Maustaste schliesst den Kegel zu einer Linie; jeder Schuss
        # oeffnet ihn nur ein kleines Stueck (gemeldet in Runde 5 und 6).
        # 0.34.73: 38 -> 34, und die Reichweite 1200 -> 900 (siehe unten). Sie soll zwischen Repetierer und Scharfschuetze liegen, nicht neben dem Scharfschuetzen.
        schaden=34.0,
        takt=0.26,
        magazin=10,
        nachladen=2.3,
        streuung=7.0,
        fokus_streuung=0.0,
        fokus_dauer=0.9,
        fokus_tempo=0.6,
        fokus_schuss=0.88,
        fokus_mittellinie=False,
        streuung_lauf=3.0,
        geschosse=1,
        tempo=1000.0,
        reichweite=900.0,
        rueckstoss=45.0,
        kamera=2.2,
        huelsen=1,
        klang="schuss_repetierer",
    ),
    "unterhebel": dict(
        art="schuss",
        name="UNTERHEBELGEWEHR",
        # Patrone fuer Patrone geladen; wer schiesst, unterbricht das Laden.
        schaden=33.0,
        takt=0.48,
        magazin=7,
        nachladen=0.42,       # je Patrone
        nachladen_einzeln=True,
        streuung=1.3,
        streuung_lauf=3.0,
        geschosse=1,
        tempo=720.0,
        reichweite=600.0,
        rueckstoss=45.0,
        kamera=1.8,
        huelsen=1,
        klang="schuss_repetierer",
    ),
    "panzerbuechse": dict(
        art="schuss",
        name="PANZERBÜCHSE",
        # Durch leichte Deckung und mehrere Koerper, stark gegen Fahrzeuge.
        # Der Ziellaser verraet den Schuetzen, nach einem Fehlschuss ist er
        # lange wehrlos.
        # 0.34.73: 120 -> 70 gegen Figuren (zwei Treffer), gegen Fahrzeuge `fahrzeug_schaden`. Sie toetete auf 1600 px mit einem Schuss und war damit besser als der Scharfschuetze; gedacht ist sie gegen Fahrzeuge und grosse Gegner.
        schaden=70.0,
        takt=0.8,
        magazin=1,
        nachladen=3.2,
        streuung=0.3,
        streuung_lauf=6.0,
        geschosse=1,
        tempo=1500.0,
        reichweite=1600.0,
        rueckstoss=170.0,
        kamera=6.0,
        huelsen=1,
        muendung=1.6,
        klang="schuss_panzerbuechse",
        durchschlag=3,
        durch_deckung=True,
        # Seit 0.34.96: durch Mauern und Panzerung noch so viele Pixel
        # weiter (gewuenscht: "penetriert ein paar Meter"); der Laser endet
        # am ersten Hindernis.
        durchdringen=80.0,
        fahrzeug_schaden=220.0,   # 160 -> 220 (seit 0.34.95): Panzerabwehr soll wirken
        gegen_fahrzeug=True,
        laser=True,
    ),
    "doppelflinte": dict(
        art="schuss",
        name="DOPPELFLINTE",
        # Linke Maustaste ein Lauf, rechte beide auf einmal. Danach lange laden.
        # 0.34.73: 15 -> 11 je Kugel. Ein Lauf (8 x 15 = 120) toetete aus der Naehe mit einem Schuss; jetzt braucht es beide Laeufe.
        schaden=11.0,
        takt=0.22,
        magazin=2,
        nachladen=2.4,
        streuung=6.0,
        streuung_lauf=3.0,
        geschosse=8,
        tempo=560.0,
        reichweite=250.0,
        rueckstoss=150.0,     # je Lauf
        kamera=4.2,
        huelsen=0,
        muendung=1.3,
        klang="schuss_doppelflinte",
        beide_laeufe=True,
    ),
    "autoschrot": dict(
        art="schuss",
        name="AUTOSCHROT",
        # Halbautomatisch: schwaecher je Schuss als Schrot, dafuer schnell
        # hintereinander - Druck statt Wucht, eine Gruppe wird zurueckgedraengt.
        # 0.34.73: 9 -> 7 je Kugel. 225 je Sekunde aus der Naehe war mehr als jede Waffe ausser der Minigun.
        schaden=7.0,
        takt=0.24,
        magazin=8,
        nachladen=2.8,
        streuung=6.5,
        streuung_lauf=3.2,
        geschosse=6,
        tempo=540.0,
        reichweite=270.0,
        rueckstoss=60.0,
        kamera=2.6,
        huelsen=1,
        klang="schuss_schrot",
        stoss=2.4,
    ),
    "minigun": dict(
        art="schuss",
        name="MINIGUN",
        # Anlauf, dann Dauerfeuer. Der Traeger steht fast und dreht kaum.
        # Das Paket sagt "kein Nachladen": ein Gurt, der so lange haelt
        # wie ein Gefecht, und sein Wechsel dauert.
        # 0.34.73 (Balancing): 12 -> 9. Bei voller Drehzahl 300 Schaden je Sekunde, im Dauerfeuer 173 - fast doppelt so viel wie das Sturmgewehr.
        schaden=9.0,
        tempo=950.0,
        reichweite=700.0,
        magazin=240,
        nachladen=7.0,
        geschosse=1,
        huelsen=1,
        kamera=0.9,
        rueckstoss=2.0,
        takt=0.04,            # bei voller Drehzahl
        anlauf_takt=0.32,     # und am Anfang
        anlauf=1.5,
        anlauf_abbau=2.2,
        streuung=6.0,
        streuung_lauf=4.0,
        gewicht_tempo=0.2,
        gewicht_drehen=42.0,
        klang="schuss_minigun",
    ),
    "granatwerfer": dict(
        art="werfer",
        name="GRANATWERFER",
        # Granaten im Bogen bis zum Zeiger, ueber Kisten und Sandsaecke
        # hinweg, nie eine Ebene hinauf. Die Hoehe sieht man nur daran,
        # dass sie groesser wird. Ein Koerper laesst sie sofort zuenden.
        schaden=82.0,
        radius=72.0,
        takt=0.9,
        magazin=1,
        nachladen=2.0,
        wurf_min=70.0,
        wurf_max=430.0,
        reichweite=430.0,
        # 400 -> 340 (seit 0.34.87, gemeldet: "ein kleines bisschen
        # langsamer fliegen" - und dafuer frueher zuenden).
        tempo=340.0,          # Pixel je Sekunde ueber den Boden
        bogen=70.0,           # so hoch steigt sie in der Mitte
        koerper_hoehe=26.0,   # darunter trifft sie einen Koerper
        ueber_rand=2.0,       # so viel hoeher als die Kachel muss sie sein, um darueber zu gehen
        zuender=0.4,          # so lange liegt sie, bevor sie zuendet (0.7 bis 0.34.86)
        ausrollen=0.12,       # so viel vom Tempo bleibt beim Aufsetzen
        reibung=5.0,          # und so schnell rollt sie aus
        streuung=1.5,
        kamera=3.0,
        rueckstoss=70.0,
        huelsen=0,
        muendung=1.4,
        klang="schuss_granatwerfer",
    ),
    "einwegwerfer": dict(
        art="rakete",
        name="EINWEG-RAKETENWERFER",
        # Ungelenkt, ein einziger Schuss, danach liegt das Rohr am Boden.
        einweg=True,
        schaden=140.0,
        # Am Blech (seit 0.34.95): Hohlladung, gegen Fahrzeuge viel
        # staerker als gegen Figuren. Ein Panzerwagen haelt von vorn
        # oder der Seite einen Treffer aus, von hinten keinen; ein
        # Panzer zwei bis drei.
        fahrzeug_schaden=300.0,
        radius=96.0,
        eigen_anteil=0.55,
        takt=1.0,
        magazin=1,
        nachladen=0.0,
        tempo=360.0,
        reichweite=1600.0,
        flugzeit=4.6,
        kamera=8.0,
        rueckstoss=90.0,
        huelsen=0,
        streuung=0.8,
    ),
    "raketenbuendel": dict(
        art="rakete",
        name="RAKETENBÜNDEL",
        # Sechs kleine, ungelenkte Raketen kurz nacheinander, die unruhig
        # fliegen: nah verheerend, auf Distanz wild gestreut.
        schaden=38.0,
        radius=40.0,
        eigen_anteil=0.5,
        takt=1.4,
        magazin=6,
        nachladen=3.6,
        salve=6,
        salve_takt=0.11,
        tempo=300.0,
        reichweite=900.0,
        flugzeit=3.2,
        kamera=2.5,
        rueckstoss=30.0,
        huelsen=0,
        streuung=6.0,
        schlingern=16.0,      # Grad hin und her
        schlinger_takt=9.0,   # wie schnell (Bogenmass je Sekunde)
        # Im Flug groesser als das Teil im Paket, mit Flossen und Flamme -
        # gemeldet: "nicht wirklich als Raketen erkennbar" (0.34.64).
        bild="minirakete_flug",
        explosion="klein",
        # Seit 0.34.95 kleine Hohlladungen (vorher Spreng, gegen Blech
        # schwach): eine ganze Salve nimmt einem Panzerwagen fast alles.
        schadensart="hohlladung",
        fahrzeug_schaden=55.0,
    ),

    # ── Gegen Fahrzeuge (seit 0.34.65) ─────────────────────────────────
    #
    # `schadensart` sagt, welche Zeile von PANZERUNG gilt (ohne: Granaten
    # "spreng", Raketen "hohlladung", Kugeln "kugel"). `fahrzeug_schaden`
    # ersetzt `schaden`, wenn ein Fahrzeug getroffen wird.
    "haftladung": dict(
        art="wurf",
        name="HAFTLADUNG",
        # Klebt an allem, was sie im Flug beruehrt - Wagen, Figur, Boss -
        # und faehrt mit. Gegen Figuren eine kleine Granate, gegen Blech
        # das Staerkste, was man werfen kann.
        haftet=True,
        schaden=48.0,
        fahrzeug_schaden=190.0,
        schadensart="hohlladung",
        radius=46.0,
        takt=1.0,
        magazin=2,
        nachladen=3.8,
        # Seit 0.34.67 nach dem Paket: "viel laengere Zeit zur Explosion,
        # weiterer Flug ... primaer gegen Fahrzeuge". Sie blinkt immer
        # schneller (render, `blinkt`).
        wurf_min=40.0,
        wurf_max=240.0,
        reibung=2.2,          # und sie rollt kaum
        flugzeit=5.0,
        blinkt=True,
        kamera=5.0,
        rueckstoss=0.0,
        huelsen=0,
        explosion="klein",
    ),
    "emp": dict(
        art="wurf",
        name="EMP-GRANATE",
        # Kein Schaden. Jedes Fahrzeug im Kreis steht still (EMP), ohne
        # Motor, ohne Lenkung, ohne Waffen - Zeit fuer die Haftladung.
        emp=True,
        schaden=0.0,
        radius=0.0,
        takt=0.9,
        magazin=1,
        nachladen=4.5,
        # Paket: "laengerer Wurf, laengere Zeit zur Explosion, groesserer
        # Radius" (seit 0.34.67), mit schneller werdendem Blinken.
        wurf_min=60.0,
        wurf_max=300.0,
        reibung=1.3,
        flugzeit=2.0,
        blinkt=True,
        kamera=1.5,
        rueckstoss=0.0,
        huelsen=0,
    ),

    # ── Nahkampf und Werkzeug (seit 0.34.66) ───────────────────────────
    #
    # Aus dem Waffenpaket. Nahkampfwaffen liegen auf einem Platz der
    # Hotbar wie eine Schusswaffe (das Brecheisen bleibt auf F). Neue
    # Schalter:
    #
    #   zweit            was die rechte Maustaste tut ("bodenschlag")
    #   betaeubt         so lange ist der Getroffene gelaehmt (ZUSTAENDE)
    #   dash_faktor      so viel staerker trifft ein Schlag aus dem Dash
    #   saege            Dauerschaden, solange gehalten (Treibstoff = Magazin)
    #   nagelt           wer vor einer Wand getroffen wird, haengt fest
    #   bild_flug        das Bild im Flug statt der Leuchtspur
    "hammer": dict(
        art="nahkampf",
        name="VORSCHLAGHAMMER",
        # Langsam und schwer. Links ein Schlag, rechts auf den Boden: alles
        # ringsum fliegt weg, wie beim Stampfer des Koloss.
        # Seit 0.34.96 langsamer und stoesst weit weg (gewuenscht).
        schaden=72.0,
        takt=1.35,
        reichweite=44.0,
        winkel=80.0,
        schwung=0.48,
        schub=1100.0,
        kamera=3.5,
        rueckstoss=0.0,
        magazin=0,
        nachladen=0.0,
        huelsen=0,
        tempo_faktor=0.9,
        zweit="bodenschlag",
        boden_schaden=40.0,
        boden_radius=74.0,
        boden_schub=520.0,
        boden_takt=1.8,
    ),
    "schockstab": dict(
        art="nahkampf",
        name="SCHOCKSTAB",
        # Wenig Schaden, aber der Getroffene steht kurz still: kein
        # Schiessen, kein Ausweichen.
        schaden=14.0,
        takt=0.85,
        reichweite=38.0,
        winkel=60.0,
        schwung=0.22,
        schub=60.0,
        kamera=1.5,
        rueckstoss=0.0,
        magazin=0,
        nachladen=0.0,
        huelsen=0,
        betaeubt=1.4,
        tempo_faktor=1.04,
    ),
    "schlagring": dict(
        art="nahkampf",
        name="SCHLAGRING",
        # Sehr schnell und sehr nah. Aus dem Dash heraus trifft er hart.
        schaden=19.0,
        takt=0.28,
        reichweite=26.0,
        winkel=70.0,
        schwung=0.12,
        schub=120.0,
        kamera=1.2,
        rueckstoss=0.0,
        magazin=0,
        nachladen=0.0,
        huelsen=0,
        dash_faktor=2.6,
        dash_fenster=0.3,     # so lange nach dem Dash zaehlt er als "aus dem Dash"
        tempo_faktor=1.1,
    ),
    "kettensaege": dict(
        art="nahkampf",
        name="KETTENSÄGE",
        # Schadet, solange sie das Ziel beruehrt, und haelt es fest. Laut:
        # jeder in der Naehe hoert, wo sie laeuft. Braucht Treibstoff.
        saege=True,
        schaden=11.0,         # je Zug (`takt`)
        takt=0.1,
        reichweite=34.0,
        winkel=50.0,
        schwung=0.1,
        schub=30.0,
        kamera=0.6,
        rueckstoss=0.0,
        magazin=90,           # Treibstoff fuer 9 Sekunden
        nachladen=3.4,
        huelsen=0,
        laerm=620.0,          # so weit hoeren Bots sie
        tempo_faktor=0.92,
        f_schnitt=4.0,        # auf F ein Schnitt mit so viel x Schaden
        f_takt=0.55,
    ),
    "wurfmesser": dict(
        art="nahkampf",
        name="WURFMESSER",
        # Lautlos. Links zustechen, rechts werfen - geworfen bleibt es
        # liegen und muss wieder aufgehoben werden (`aufheben`).
        schaden=46.0,
        takt=0.42,
        reichweite=28.0,
        winkel=50.0,
        schwung=0.14,
        schub=80.0,
        kamera=0.8,
        rueckstoss=0.0,
        magazin=3,            # so viele Messer zum Werfen
        nachladen=0.0,
        huelsen=0,
        tempo_faktor=1.06,
        zweit="werfen",
        aufheben=True,
        wurf_schaden=62.0,
        wurf_tempo=520.0,
        wurf_weite=300.0,
        wurf_takt=0.5,
        bild_flug="wurfmesser_flug",
        lautlos=True,
        f_werfen=True,        # auf F immer geworfen (seit 0.34.96)
    ),
    "speer": dict(
        art="nahkampf",
        name="SPEER",
        # Grosse Reichweite, aber schmal. Geworfen liegt er am Boden, bis
        # man ihn holt.
        schaden=50.0,
        takt=0.75,
        reichweite=96.0,      # seit 0.34.96 grosse Reichweite (66 vorher)
        winkel=22.0,
        schwung=0.25,
        schub=200.0,
        kamera=1.6,
        rueckstoss=0.0,
        magazin=1,
        nachladen=0.0,
        huelsen=0,
        zweit="werfen",
        aufheben=True,
        wurf_schaden=95.0,
        wurf_tempo=470.0,
        wurf_weite=420.0,
        wurf_takt=0.8,
        bild_flug="speer_flug",
    ),
    "bolzer": dict(
        art="schuss",
        name="BOLZENSCHUSSGERÄT",
        # Aus dem Schlachthaus: nur aus allernaechster Naehe, dann sehr
        # stark und ohne Ruecksicht auf Deckung.
        schaden=105.0,
        takt=0.5,
        magazin=1,
        nachladen=1.3,
        streuung=0.0,
        streuung_lauf=0.0,
        geschosse=1,
        tempo=1600.0,
        reichweite=46.0,
        durch_deckung=True,
        rueckstoss=40.0,
        kamera=2.2,
        huelsen=0,
        stoss=2.0,
        klang="schuss_bolzer",
        muendung=0.4,
    ),
    "nagler": dict(
        art="schuss",
        name="NAGLER",
        # Langsame Naegel, denen man ausweichen kann. Wer dicht vor einer
        # Wand getroffen wird, haengt fest; die Naegel bleiben stecken.
        nagelt=True,
        schaden=20.0,
        takt=0.16,
        magazin=36,
        nachladen=2.8,
        streuung=2.2,
        streuung_lauf=3.0,
        geschosse=1,
        tempo=340.0,
        reichweite=520.0,
        rueckstoss=8.0,
        kamera=0.6,
        huelsen=0,
        klang="schuss_nagler",
        muendung=0.3,
        bild_flug="nagel_flug",
    ),
}

# ══════════════════════════════════════════════════ KLASSEN (seit 0.34.73)
#
# Gemeldet: "Klassensystem ... sehr viele Klassen, jede mit auswaehlbaren
# Waffen (nicht alle), Spezialfaehigkeiten/Buffs (Sanitaeter wirft
# Sanitaetstaschen, Supporter schwere stationaere Waffen + Munitionskisten)
# ... nicht jede Klasse nur eine Waffe/Granate."
#
# Jeder Satz der Ausruestung hat eine Klasse. FREI (Kennung "") ist die
# alte Ausruestung ohne Klasse: jede Waffe, kein Vorteil - so bleiben alle
# gespeicherten Saetze gueltig. Je Klasse:
#
#   waffen, wuerfe   woraus gewaehlt werden darf (je mehrere)
#   leben            x Leben          tempo     x Lauftempo
#   nachladen        x Nachladezeit   kuehlen   x Abkuehlzeit (Chor)
#   feuer            x Schaden durch Feuer      fahrzeug  x Schaden an Fahrzeugen
#   aufhelfen        x Zeit zum Aufhelfen       medkits   + Medkits
#   schild           traegt das Schild (SCHILD)
#   nahkampf         Faktor auf den Schaden der Waffe auf F (seit 0.34.99)
#   nahkampf_takt    Faktor auf die Pause zwischen zwei Schlaegen auf F
#   faehigkeit       was die Taste C hinlegt (ausruestung.py) und wie oft
#                    (Sekunden Pause). Seit 0.34.79 auch im Gefecht und in
#                    der Lobby (Regel KLASSEN-FAEHIGKEITEN).
# Seit 0.34.91 traegt jeder Satz eine Hauptwaffe und eine Seitenwaffe -
# gemeldet: "sidearms sind quasi irrelevant, weil man ja quasi auch zwei
# primarys nehmen kann". Manche Klassen haben dazu einen Platz fuer eine
# Spezialwaffe (`plaetze`); wer das Schild traegt, hat nur die
# Seitenwaffe (die zweite Hand haelt das Schild). Woraus je Platz gewaehlt
# wird, steht in `waffen` der Klasse; welcher Platz eine Waffe ist, in
# WAFFEN_PLATZ.
KLASSEN = {
    "schuetze": dict(name="SCHÜTZE", text="Allrounder, laedt schneller",
                     waffen=("sturm", "unterhebel", "mp", "repetierer", "revolver"),
                     wuerfe=("granate", "rauch", "blend"), nachladen=0.85,
                     faehigkeit=(("munitionskiste", 40.0),)),
    "sanitaeter": dict(name="SANITÄTER", text="Wirft Sanitaschen, hilft schneller auf",
                       waffen=("mp", "autoschrot", "repetierer", "revolver", "zwillinge"),
                       wuerfe=("rauch", "blend", "granate"), aufhelfen=0.6, medkits=1,
                       faehigkeit=(("sanitasche", 20.0),)),
    "unterstuetzer": dict(name="UNTERSTÜTZER", text="Schwere Waffen, Munitionskiste, Selbstschussanlage",
                          waffen=("lmg", "sturm", "autoschrot", "repetierer", "minigun",
                                  "raketenbuendel"),
                          plaetze=("haupt", "seite", "spezial"),
                          wuerfe=("granate", "rauch", "kuller"), tempo=0.94, leben=1.1,
                          faehigkeit=(("munitionskiste", 30.0), ("geschuetz", 60.0))),
    "scharfschuetze": dict(name="SCHARFSCHÜTZE", text="Weit und genau, markiert mit dem Fernglas",
                           waffen=("scharf", "praezision", "unterhebel", "repetierer", "revolver"),
                           wuerfe=("rauch", "knaller", "blend"), leben=0.9,
                           faehigkeit=(("horchposten", 45.0),)),
    "pionier": dict(name="PIONIER", text="Sprengt und baut: Fallen, Sandsaecke, mehr gegen Blech",
                    waffen=("schrot", "autoschrot", "sturm", "nagler", "bolzer", "einwegwerfer"),
                    plaetze=("haupt", "seite", "spezial"),
                    wuerfe=("c4", "haftladung", "granate"), fahrzeug=1.2,
                    faehigkeit=(("sprengfalle", 25.0), ("sandsackwand", 30.0))),
    "panzerjaeger": dict(name="PANZERJÄGER", text="Gegen Fahrzeuge gebaut",
                         waffen=("mp", "unterhebel", "repetierer", "panzerbuechse",
                                 "einwegwerfer", "raketenbuendel"),
                         plaetze=("haupt", "seite", "spezial"),
                         wuerfe=("haftladung", "emp", "granate"), fahrzeug=1.3, tempo=0.95,
                         faehigkeit=(("kraehenfuesse", 25.0),)),
    "grenadier": dict(name="GRENADIER", text="Werfer und Granaten, eine Granate mehr",
                      waffen=("sturm", "mp", "doppelflinte", "repetierer", "revolver",
                              "granatwerfer"),
                      plaetze=("haupt", "seite", "spezial"),
                      wuerfe=("granate", "kuller", "gas", "molotov"), granaten=1,
                      faehigkeit=(("sandsackwand", 35.0),)),
    "flammentrupp": dict(name="FLAMMENTRUPP", text="Feuer und Nahdistanz, haelt Feuer besser aus",
                         waffen=("doppelflinte", "schrot", "autoschrot", "repetierer",
                                 "flammenwerfer"),
                         plaetze=("haupt", "seite", "spezial"),
                         wuerfe=("molotov", "gas", "rauch"), feuer=0.4, leben=1.1,
                         faehigkeit=(("kanister", 25.0),)),
    "spaeher": dict(name="SPÄHER", text="Schnell, leise, mit Spaehdrohne",
                    waffen=("mp", "praezision", "zwillinge", "revolver"),
                    wuerfe=("blend", "knaller", "emp"), tempo=1.1, leben=0.9,
                    nahkampf_takt=0.85,
                    faehigkeit=(("drohne", 45.0),)),
    "nahkaempfer": dict(name="NAHKÄMPFER", text="Mehr Leben, starker Nahkampf auf F, Stacheldraht",
                        # Die Nahkampfwaffen liegen seit 0.34.96 auf F - jede
                        # Klasse waehlt dort frei. Damit der NAHKAEMPFER
                        # trotzdem der fuer den Nahkampf bleibt, schlaegt er
                        # seit 0.34.99 haerter und schneller zu.
                        nahkampf=1.4, nahkampf_takt=0.75,
                        waffen=("schrot", "doppelflinte", "autoschrot", "mp", "revolver",
                                "zwillinge", "flammenwerfer"),
                        plaetze=("haupt", "seite", "spezial"),
                        wuerfe=("rauch", "blend", "schneeball"), leben=1.25, tempo=1.05,
                        faehigkeit=(("stacheldraht", 30.0),)),
    "techniker": dict(name="TECHNIKER", text="Chor-Waffen kuehlen schneller, Horchposten",
                      waffen=("kettenblitz", "spiegellaser", "nagler", "repetierer", "spule",
                              "kugelblitz"),
                      plaetze=("haupt", "seite", "spezial"),
                      wuerfe=("emp", "blend", "haftladung"), kuehlen=0.75,
                      faehigkeit=(("horchposten", 35.0), ("geschuetz", 70.0))),
    "schildtraeger": dict(name="SCHILDTRÄGER", text="Grosses Schild vorn, nur Seitenwaffe",
                          waffen=("repetierer", "revolver", "bolzer"),
                          plaetze=("seite",), nahkampf=1.15,
                          wuerfe=("blend", "rauch", "granate"), schild=True, leben=1.1,
                          faehigkeit=(("sandsackwand", 30.0),)),
    "fahrer": dict(name="FAHRER", text="Fahrzeuge halten mehr aus, Kraehenfuesse",
                   waffen=("mp", "autoschrot", "repetierer", "zwillinge"),
                   wuerfe=("rauch", "emp", "granate"), fahrzeug_schutz=0.85,
                   faehigkeit=(("kraehenfuesse", 20.0),)),
}
KLASSE_FREI = dict(name="FREI", text="Ohne Klasse: Haupt- und Seitenwaffe frei, kein Vorteil")

# Welcher Platz im Satz eine Waffe ist (seit 0.34.91): "haupt" (die
# Hauptwaffe), "seite" (Seitenwaffe - Pistolen, Werkzeug, leichter
# Nahkampf) oder "spezial" (nur fuer Klassen mit dem Platz dafuer).
WAFFEN_PLATZ = dict(
    {w: "haupt" for w in ("sturm", "schrot", "scharf", "lmg", "mp", "praezision",
                          "unterhebel", "doppelflinte", "autoschrot",
                          "kettenblitz", "spiegellaser")},
    **{w: "seite" for w in ("repetierer", "revolver", "zwillinge", "bolzer", "nagler")},
    **{w: "spezial" for w in ("minigun", "panzerbuechse", "granatwerfer", "einwegwerfer",
                              "raketenbuendel", "spule", "kugelblitz", "flammenwerfer")})
# Wie die Plaetze im Menue heissen und welche ein Satz ohne Klasse hat.
PLATZ_NAMEN = dict(haupt="HAUPTWAFFE", seite="SEITENWAFFE", spezial="SPEZIALWAFFE")
PLAETZE_VORGABE = ("haupt", "seite")
# KLASSE PFLICHT (Regel, seit 0.34.91): wer ohne Klasse kommt, spielt
# diese - mit den Waffen seines Satzes, soweit sie zu ihr passen.
KLASSE_PFLICHT_ERSATZ = "schuetze"

# Der Schildtraeger (seit 0.34.71, erst im Testmodus): ein grosses Schild
# vorn. Was von vorn kommt (die Richtung zum Schuetzen), haelt es zum
# groessten Teil ab; dafuer ist er langsamer und traegt nur eine Pistole.
# anteil: was durchs Schild noch ankommt - seit 0.34.77 7 % statt 15 %
# (gemeldet: "Schildtraeger sollen auf ihr Schild noch weniger Schaden
# bekommen").
SCHILD = dict(winkel=60.0, anteil=0.07, tempo=0.82, waffe="repetierer",
              # Was durchschlaegt (seit 0.34.86): so viel kommt trotz Schild
              # an, mit eigenem Klang. Gemeldet: "das Schild soll bei high
              # penetration Waffen einen Durchschlags-Sound machen und mehr
              # Damage durchlassen". Panzerbrechend (Kanone, Spule) immer
              # wenigstens `panzerbrechend`.
              durchschlag=dict(scharf=0.45, praezision=0.3, panzerbuechse=0.7,
                               spule=0.75, bolzer=0.5, revolver=0.15, unterhebel=0.15),
              panzerbrechend=0.7)

# Trupp-Vorlagen fuer den Testmodus (seit 0.34.71). Gemeldet: "Trupp mit
# Panzer oder Armored Truck, Schildtraeger ... Skins fuer jedes
# Truppmitglied ... weiterhin Standard-Trupps". Je Mitglied: (Aussehen,
# Waffe, Wurfwaffe, Schild?); das erste fuehrt den Trupp (mit Funk). Ein
# Fahrzeug bekommt seinen eigenen Fahrer, der nicht zum Trupp gehoert.
TRUPP_VORLAGEN = {
    "PANZERZUG": dict(fahrzeug="panzer", fahrer="panzerfahrer", mitglieder=(
        ("offizier", "repetierer", "rauch", False), ("grenadier", "granatwerfer", "granate", False),
        ("pionier", "sturm", "haftladung", False), ("mg_schuetze", "lmg", "granate", False))),
    "MOT. SCHÜTZEN": dict(fahrzeug="panzerwagen", fahrer="panzerfahrer", mitglieder=(
        ("gefreiter", "sturm", "rauch", False), ("schuetze", "sturm", "granate", False),
        ("sanitaeter", "mp", "rauch", False), ("scharfschuetze", "scharf", "blend", False))),
    "SCHILDWALL": dict(fahrzeug="", fahrer="", mitglieder=(
        ("offizier", "repetierer", "rauch", False), ("schildtraeger", "repetierer", "blend", True),
        ("schildtraeger", "repetierer", "blend", True), ("stadtkaempfer", "schrot", "granate", False),
        ("grenadier", "granatwerfer", "granate", False))),
    "SPÄHTRUPP": dict(fahrzeug="buggy", fahrer="wuestenschuetze", mitglieder=(
        ("funker", "praezision", "rauch", False), ("scharfschuetze", "scharf", "rauch", False),
        ("wachposten", "mp", "emp", False))),
    "STURMTRUPP": dict(fahrzeug="", fahrer="", mitglieder=(
        ("fallschirmjaeger", "sturm", "blend", False), ("stadtkaempfer", "autoschrot", "granate", False),
        ("fallschirmjaeger", "mp", "granate", False), ("pionier", "flammenwerfer", "molotov", False),
        ("gebirgsjaeger", "lmg", "rauch", False))),
}

# Bauen, Fallen, Aufklaerung, Sanitasche, Munitionskiste (seit 0.34.69,
# dustfront/ausruestung.py). Gemeldet: "erstmal nur fuer den Testmodus" -
# darum stehen sie nur im Spawner und gehen nicht ueber das Netz.
AUSRUESTUNG = dict(
    sandsack=dict(leben=320.0, radius=11.0, stuecke=3, abstand=20.0),
    stacheldraht=dict(laenge=64.0, breite=10.0, tempo=0.35, schaden=12.0),
    sprengfalle=dict(radius=14.0, verzoegerung=0.45, spreng_radius=82.0,
                     schaden=95.0, draht=80.0, sehen=70.0),
    geschuetz=dict(leben=220.0, radius=10.0, reichweite=430.0, dreh=150.0,
                   kegel=6.0, takt=0.16, streuung=3.0, schaden=10.0, tempo=640.0,
                   magazin=60, nachladen=4.0),
    kanister=dict(leben=18.0, radius=7.0, brand_radius=74.0, schaden=40.0),
    # Seit 0.34.95 ein weiter Kreis und weiter Blick (vorher 90 und 260,
    # gemeldet: "bringt keinen Vorteil"): sie fliegt ueber ein ganzes
    # Viertel und markiert, wen sie unterwegs sieht. Das Tempo ist im
    # Bogenmass je Sekunde, am Rand also etwa 150 px/s.
    drohne=dict(leben=60.0, radius=9.0, kreis=230.0, tempo=0.65, sicht=340.0, fallen=1.2,
                such_takt=0.15, hinaus=110.0),   # px/s hinaus auf den Kreis
    horchposten=dict(leben=80.0, radius=8.0, weite=300.0, takt=1.0, bewegt=20.0),
    fernglas=dict(weite=700.0, kegel=18.0, kamera=0.45),
    markiert=2.5,             # so lange bleibt ein entdeckter Gegner markiert
    sanitasche=dict(radius=40.0, heilt=35.0, dauer=5.0, ladungen=3),
    munitionskiste=dict(radius=26.0, ladungen=4, pause=8.0),
)

# Wurfwaffen aus dem Paket (seit 0.34.67). Sie stehen in WAFFEN wie die
# Granate (art "wurf"); was sie besonders macht, steht hier.
WUERFE_PAKET = {
    "gas": dict(
        art="wurf", name="GASGRANATE",
        # Eine giftige Wolke, die langsam waechst und schadet, solange man
        # drinsteht. Zombies atmen nicht (Fraktion "feind").
        gas=True, schaden=0.0, radius=0.0, takt=0.9, magazin=1, nachladen=4.0,
        wurf_min=60.0, wurf_max=230.0, reibung=1.4, flugzeit=1.3,
        kamera=0.8, rueckstoss=0.0, huelsen=0, bild_flug="gas_flug"),
    "kuller": dict(
        art="wurf", name="KULLER",
        # Klein und unscheinbar, gerade gerollt. Zuendet, sobald jemand
        # nahe kommt, sonst nach einer Weile.
        # Seit 0.34.87: sie rollt ueber den Zeiger hinaus (`ueber_ziel`, sie
        # rollt eben) und zuendet etwas frueher (flugzeit 9 -> 6,5 s).
        kuller=True, schaden=72.0, radius=70.0, takt=0.9, magazin=2, nachladen=3.6,
        wurf_min=80.0, wurf_max=520.0, reibung=0.35, flugzeit=6.5, ueber_ziel=1.6,
        kamera=6.0, rueckstoss=0.0, huelsen=0, bild_flug="teil_kuller_wurf",
        scharf_nach=0.5, naehe=34.0),
    "knaller": dict(
        art="wurf", name="KNALLER",
        # Macht eine Weile Laerm wie ein Gefecht. Bots hoeren das und sehen
        # nach - so lockt oder taeuscht man sie.
        knaller=True, schaden=0.0, radius=0.0, takt=0.9, magazin=2, nachladen=3.0,
        wurf_min=60.0, wurf_max=260.0, reibung=1.4, flugzeit=1.2,
        kamera=0.3, rueckstoss=0.0, huelsen=0, bild_flug="teil_knaller_wurf",
        klang="knaller", muendung=0.5, knall_dauer=6.0,
        knall_takt=(0.08, 0.35), laerm=900.0),
    "schneeball": dict(
        art="wurf", name="SCHNEEBALL",
        # Harmlos, aber wer oft getroffen wird, friert kurz ein. Fliegt
        # gerade wie ein Messer.
        gerade=True, schaden=3.0, radius=0.0, takt=0.35, magazin=5, nachladen=1.6,
        wurf_min=40.0, wurf_max=330.0, wurf_tempo=430.0, reibung=0.0, flugzeit=2.0,
        kamera=0.2, rueckstoss=0.0, huelsen=0, bild_flug="schneeball_flug",
        kaelte=1, kaelte_bis=3, kaelte_fenster=4.0, gefroren=1.4),
}
WAFFEN.update(WUERFE_PAKET)

# Energiewaffen des Chors und der Flammenwerfer (seit 0.34.68). Statt
# eines Magazins werden die Chor-Waffen heiss (`kuehlt`): jeder Schuss
# macht Hitze (`magazin` Schuss passen hinein), in Ruhe kuehlt alle
# `abkuehlen` Sekunden ein Teil ab - seit 0.34.130 auch weggesteckt. Ist die
# Hitze voll, ueberhitzt sie: gesperrt fuer `ueberhitzt` Sekunden (laenger als
# ein Nachladen, gewuenscht wie die Quasar-Kanone: man nimmt solange eine
# andere Waffe), einmal der Kuehlton, danach ganz kalt. Nachladen gibt es
# fuer sie nicht mehr; `nachladen` bleibt fuer die Bots als Mass.
ENERGIE_PAKET = {
    "spule": dict(
        art="strahl", name="SPULENGEWEHR",
        # Halten laedt auf (die Linie ist fuer alle zu sehen), Loslassen
        # feuert einen Strahl ohne Flugzeit, der durch Waende geht.
        # Seit 0.34.87 abgeschwaecht (gemeldet: "komplett op"): 150 -> 95
        # Schaden, laenger laden, drei statt vier Schuss, und jede Mauer
        # und jeder Koerper auf der Linie kostet Kraft (`wand_verlust`,
        # `koerper_verlust`). Ein voll geladener Treffer ohne Hindernis
        # erledigt noch jeden, aber kaum mehr zwei hintereinander.
        # Seit 0.34.135 noch einmal schwaecher (gemeldet: "die Chor-Waffe, die
        # durch Waende schiesst, ist zu stark"): 95 -> 75 Schaden, jede Mauer
        # kostet 60 statt 40 Prozent, laenger laden.
        schaden=75.0, ladezeit=2.4, mindest=0.25, reichweite=760.0,
        wand_verlust=0.6, koerper_verlust=0.35,
        takt=0.9, magazin=3, nachladen=5.5, kuehlt=True, abkuehlen=3.4, ueberhitzt=7.5,
        tempo_beim_laden=0.55, kamera=5.0, rueckstoss=60.0, huelsen=0,
        streuung=0.0, streuung_lauf=0.0, geschosse=1, tempo=1.0,
        klang="schuss_spule", muendung=1.2, schadensart="panzerbrechend"),
    "kettenblitz": dict(
        art="kette", name="KETTENBLITZ",
        # Kurz aufladen, dann springt ein Blitz vom Getroffenen zum
        # naechsten und wird dabei schwaecher. Die Waffe gegen Horden.
        schaden=46.0, ladezeit=0.45, reichweite=320.0, kegel=14.0,
        spruenge=5, sprung=120.0, abfall=0.72,
        takt=0.25, magazin=8, nachladen=4.0, kuehlt=True, abkuehlen=1.2, ueberhitzt=5.5,
        tempo_beim_laden=0.8, kamera=2.0, rueckstoss=0.0, huelsen=0,
        streuung=0.0, streuung_lauf=0.0, geschosse=1, tempo=1.0,
        klang="schuss_kettenblitz", muendung=0.8, schadensart="kugel", tempo_faktor=0.92),
    "spiegellaser": dict(
        art="schuss", name="SPIEGELLASER",
        # Prallt an Waenden ab und wird mit jedem Abprall staerker - die
        # Waffe fuer Schuesse um die Ecke.
        schaden=24.0, takt=0.3, magazin=10, nachladen=3.5, kuehlt=True, abkuehlen=0.7, ueberhitzt=5.0,
        streuung=0.6, streuung_lauf=2.0, geschosse=1, tempo=900.0, reichweite=1300.0,
        rueckstoss=0.0, kamera=0.8, huelsen=0, klang="schuss_spiegellaser", muendung=0.6,
        abprall=3, abprall_faktor=1.4, bild_flug="laser_flug"),
    "kugelblitz": dict(
        art="kugel", name="KUGELBLITZ",
        # Eine langsame Kugel, die unterwegs staendig Blitze in mehrere
        # Richtungen schlaegt (auch ohne Ziel, bis an ihre Reichweite) und
        # am Ende gross platzt. Gut zu sehen, sperrt aber einen Gang.
        # Seit 0.34.130 stark abgeschwaecht (gemeldet: "viel zu OP"): Blitze
        # 18 -> 10 Schaden und 86 -> 58 px weit, 4 -> 3 Strahlen, das Platzen
        # 70 -> 40 Schaden in 96 -> 62 px.
        schaden=10.0, zap_radius=58.0, zap_takt=0.22, zap_strahlen=3,
        platzen_schaden=40.0, platzen_radius=62.0,
        takt=1.6, magazin=2, nachladen=5.0, kuehlt=True, abkuehlen=4.0, ueberhitzt=7.0,
        streuung=0.0, streuung_lauf=0.0, geschosse=1, tempo=120.0, reichweite=760.0,
        rueckstoss=20.0, kamera=2.5, huelsen=0, klang="schuss_kugelblitz", muendung=1.0,
        bild_flug="kugelblitz_flug"),
    "flammenwerfer": dict(
        art="flamme", name="FLAMMENWERFER",
        # Ein Feuerstrom auf kurze Distanz. Laesst brennende Streifen am
        # Boden, frisst Rauch, und wer den Traeger erwischt, bringt
        # vielleicht seinen Tank zur Explosion.
        # 4,5 je Zug, gut 75 je Sekunde, dazu der brennende Boden.
        flamme=True, schaden=4.5, reichweite=130.0, winkel=24.0,
        takt=0.06, magazin=120, nachladen=4.2,
        streuung=0.0, streuung_lauf=0.0, geschosse=1, tempo=1.0,
        rueckstoss=0.0, kamera=0.4, huelsen=0, muendung=0.0,
        streifen_takt=0.3, streifen_radius=20.0, streifen_dauer=4.0,
        rauch_fressen=1.0, tank_ab=0.2, tank_radius=64.0, tank_schaden=45.0,
        tempo_faktor=0.9),
}
WAFFEN.update(ENERGIE_PAKET)

# Wie der Flammenstrom aussieht (seit 0.34.95, wie im Waffenpaket,
# code/effekte/anim.js): viele Hitzeflecken, die aus der Duese fliegen,
# bremsen, wachsen und abkuehlen. Gezeichnet wird nicht jeder Fleck,
# sondern die Summe ihrer Hitze in Zellen zu 2 x 2 Pixeln - wo sie sich
# ueberlappen, verschmelzen sie zu einer Feuerzunge: innen fast weiss,
# aussen rot. Vorher flogen Funken, und genau das hatte der Besitzer im
# Paket schon einmal verworfen ("sieht eher aus wie Funken").
FLAMME = dict(
    dichte=180.0 / 170.0,     # Flecken je Sekunde je px/s Tempo (Paket: 180 bei 170)
    streuung=14.0,            # Grad, ganz (im Paket +-7)
    tempo_streuung=0.12,      # +- so viel vom Tempo (im Paket 150 bis 190)
    reibung=2.4,              # je Sekunde, wie im Paket
    weite=0.92,               # die Flecken kommen so weit wie die Reichweite mal das
    r_start=2.0, r_wachsen=16.0, r_max=(7.0, 10.0),
    dauer=(0.42, 0.54),       # so lange glueht ein Fleck
    zelle=2,                  # Pixel je Zelle
    gewicht=0.75,             # Hitze = (1 - d^2/r^2) * hitze^2 * gewicht
    rauschen=0.18,            # so viel zuengelt es, gewuerfelt 24-mal je Sekunde
    rausch_takt=24.0,
    # Ab welcher Hitze welche Farbe (heiss zuerst), wie PAL.flamme im Paket.
    stufen=((1.0, (255, 246, 204)), (0.74, (252, 214, 120)), (0.5, (240, 150, 44)),
            (0.3, (200, 82, 24)), (0.15, (120, 36, 14))),
    hoechstens=1500,          # mehr Flecken haelt die Welt nicht
)

# Wie Strahl, Blitz und Plasma aussehen (seit 0.34.68, render).
ENTLADUNG = dict(dauer={"spule": 0.22, "blitz": 0.16, "plasma": 0.3},
                 tuerkis=(90, 230, 220), kern=(230, 255, 252))

# Was gerade geworfen wird und liegen bleibt (seit 0.34.67): nach so
# vielen Sekunden kommt es von selbst zum Werfer zurueck.
WURFKOERPER = dict(zurueck=45.0)

# Die Gaswolke der Gasgranate (seit 0.34.67).
GAS = dict(radius=86.0, anfang=22.0, wachsen=3.0, dauer=13.0, schaden=9.0,
           farbe=(196, 214, 92), dunkel=(150, 170, 60), verschont="feind")

# Zustaende (seit 0.34.66, entities.zustand_setzen).
ZUSTAENDE = dict(
    boss_anteil=0.5,          # Bosse halten nur so viel davon aus
    genagelt=1.1,             # so lange haengt fest, wen der Nagler an die Wand naegelt
    nagel_wand=14.0,          # so nah muss die Wand hinter ihm sein
    saege_fest=0.25,          # so lange haelt die Kettensaege fest (je Zug erneuert)
)

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

# Die Waffen aus dem Waffenpaket (seit 0.34.61, `dustfront_waffen`, sechs
# Runden mit dem Besitzer abgestimmt). Gezeichnet in art_waffen.py. Jede
# bekommt eine Figur, die sie haelt (auch je Mannschaft und je Skin), und
# ein Zeichen fuer die Hotbar - auch die, die noch nicht spielbar sind:
# was davon schon schiesst, steht in WAFFEN. Die Hand zeichnet das Paket
# selbst (aufbau "paket"), darum stehen hier keine Masse, nur der Name
# (aus dem Paket; die drei Fraktionswaffen nach ihrer Fraktion).
PAKET_HAND = {
    "revolver": "REVOLVER", "zwillinge": "ZWILLINGE", "mp": "MASCHINENPISTOLE",
    "bolzer": "BOLZENSCHUSSGERÄT", "praezision": "PRÄZISIONSGEWEHR",
    "unterhebel": "UNTERHEBELGEWEHR", "nagler": "NAGLER", "doppelflinte": "DOPPELFLINTE",
    "autoschrot": "AUTOSCHROT", "panzerbuechse": "PANZERBÜCHSE", "minigun": "MINIGUN",
    "granatwerfer": "GRANATWERFER", "einwegwerfer": "EINWEG-RAKETENWERFER",
    "raketenbuendel": "RAKETENBÜNDEL",
    "spule": "SPULENGEWEHR", "kettenblitz": "KETTENBLITZ", "spiegellaser": "SPIEGELLASER",
    "kugelblitz": "KUGELBLITZ", "flammenwerfer": "FLAMMENWERFER",
    "gas": "GASGRANATE", "kuller": "KULLER", "haftladung": "HAFTLADUNG", "emp": "EMP-GRANATE",
    "knaller": "KNALLER", "wurfmesser": "WURFMESSER", "schneeball": "SCHNEEBALL",
    "hammer": "VORSCHLAGHAMMER", "speer": "SPEER", "kettensaege": "KETTENSÄGE",
    "schockstab": "SCHOCKSTAB", "schlagring": "SCHLAGRING",
    "sprengfalle": "SPRENGFALLE", "kraehenfuss": "KRÄHENFÜSSE", "geschuetz": "SELBSTSCHUSSANLAGE",
    "kanister": "BENZINKANISTER", "sandsack": "SANDSACKWAND", "stacheldraht": "STACHELDRAHT",
    "fernglas": "FERNGLAS", "spaehdrohne": "SPÄHDROHNE", "horcher": "HORCHPOSTEN",
    "sanitasche": "SANITASCHE", "munbeutel": "MUNITIONSKISTE",
    "auf_daempfer": "SCHALLDÄMPFER", "auf_fernrohr": "FERNROHR", "auf_trommel": "TROMMELMAGAZIN",
    "auf_zweibein": "ZWEIBEIN", "auf_laser": "LASER", "auf_unterlauf": "UNTERLAUF-GRANATWERFER",
    "goldene": "GOLDENE PISTOLE", "fraktion_k": "KOLONNE", "fraktion_c": "CHOR",
    "fraktion_w": "FREIE WERFTEN",
}
# Zeichen fuer die Hotbar gibt es auch fuer Munition, Fahrzeugteile und
# die Fundwaffen, die man nicht in der Hand haelt.
PAKET_SYMBOLE = tuple(PAKET_HAND) + (
    "mun_panzer", "mun_brand", "mun_hohl", "mun_leucht", "mun_leucht_rot",
    "mun_leucht_gruen", "mun_leucht_gelb", "mun_unterschall",
    "hecknebel", "nagelstreuer", "kartenwaffen",
)
# Was fliegt oder liegt: (Name, Mass). Nur, was schon gebraucht wird.
PAKET_TEILE = {
    "minirakete": (9, 5),       # Raketenbuendel
    "granate40": (7, 7),        # Granatwerfer
    "rohr_leer": (30, 9),       # das weggelegte Rohr des Einweg-Raketenwerfers
    "kuller_wurf": (8, 8),      # Kuller (seit 0.34.67)
    "knaller_wurf": (12, 12),   # Knaller (seit 0.34.67)
    # Bauen, Fallen, Aufklaerung (seit 0.34.69, erst im Testmodus)
    "horcher_k": (16, 16),
    "sackwand": (14, 34),
    "drohne_a": (22, 22),
    "drohne_b": (22, 22),
}
for _w in PAKET_HAND:
    WAFFEN_HAND[_w] = dict(aufbau="paket")
    BILD_MASS["spieler_" + _w] = BILD_MASS["spieler_sturm"]
for _w in PAKET_SYMBOLE:
    BILD_MASS["waffe_" + _w] = BILD_MASS["waffe_sturm"]
for _w, _m in PAKET_TEILE.items():
    BILD_MASS["teil_" + _w] = _m

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

# Panzer und Panzerwagen (seit 0.34.59, art_fahrzeuge.py). Wanne und Turm
# bzw. MG-Ring sind getrennte Bilder: der Aufbau dreht sich fuer sich.
# Leer, mit Insasse und mit einem Insassen je Mannschaft.
_fz_n = FAHRZEUG_BILD["flaeche"]
_fz_r = FAHRZEUG_BILD["ring_flaeche"]
for _name in ("panzer", "panzer_turm", "panzer_turm_fahrer", "panzer_wrack",
              "panzer_schatten", "panzerwagen", "panzerwagen_wrack",
              "panzerwagen_schatten"):
    BILD_MASS[_name] = (_fz_n, _fz_n)
BILD_MASS["panzerwagen_ring"] = (_fz_r, _fz_r)
BILD_MASS["panzerwagen_ring_fahrer"] = (_fz_r, _fz_r)
for _team in TEAMS["kombi"]:
    BILD_MASS["panzer_turm_%s_fahrer" % _team["name"].lower()] = (_fz_n, _fz_n)
    BILD_MASS["panzerwagen_ring_%s_fahrer" % _team["name"].lower()] = (_fz_r, _fz_r)
# Die Granate der Kanone, mit dicker Leuchtspur gezeichnet.
BILD_MASS["panzergranate"] = (12, 6)
BILD_MASS["flak_leer"] = (2, 2)          # die Flakgranate ist unsichtbar (Leuchtspur: effekte.py)
# Der Flakwagen (seit 0.34.114, art_neue_fahrzeuge.py): Wanne wie der Panzerwagen,
# die Lafette 128 gross (die Rohre ragen weit hinaus).
for _name in ("flakwagen", "flakwagen_wrack", "flakwagen_schatten"):
    BILD_MASS[_name] = (_fz_n, _fz_n)
for _name in ("flak_lafette", "flak_lafette_fahrer"):
    BILD_MASS[_name] = (128, 128)
for _team in TEAMS["kombi"]:
    BILD_MASS["flak_lafette_%s_fahrer" % _team["name"].lower()] = (128, 128)
# Dekale des Effektsystems (seit 0.34.122, effekte.py).
for _i, _n in enumerate((28, 44, 64, 96)):
    BILD_MASS["fx_brand_%d" % _i] = (_n, _n)
for _i in range(8):
    BILD_MASS["fx_teil_%d" % _i] = (24, 24)
for _i in range(6):
    BILD_MASS["rotor_schatten_%d" % _i] = (192, 192)
for _name in ("tragschrauber", "tragschrauber_fahrer", "tragschrauber_wrack", "tragschrauber_schatten"):
    BILD_MASS[_name] = (160, 160)
for _team in TEAMS["kombi"]:
    BILD_MASS["tragschrauber_%s_fahrer" % _team["name"].lower()] = (160, 160)
for _i in range(6):
    BILD_MASS["rotor_%d" % _i] = (192, 192)
for _name in ("werfer", "werfer_wrack", "werfer_schatten"):
    BILD_MASS[_name] = (FAHRZEUG_BILD["flaeche"], FAHRZEUG_BILD["flaeche"])
for _i in range(1, 9):
    BILD_MASS["werfer_stuetze_%d" % _i] = (FAHRZEUG_BILD["flaeche"], FAHRZEUG_BILD["flaeche"])
for _name in ("funkwagen", "funkwagen_wrack"):
    BILD_MASS[_name] = (160, 160)
BILD_MASS["funkwagen_schatten"] = (FAHRZEUG_BILD["flaeche"], FAHRZEUG_BILD["flaeche"])
for _name in ("spulenwagen", "spulenwagen_aktiv", "spulenwagen_wrack", "spulenwagen_schatten"):
    BILD_MASS[_name] = (FAHRZEUG_BILD["flaeche"], FAHRZEUG_BILD["flaeche"])
for _name in ("trosswagen", "trosswagen_wrack", "trosswagen_schatten"):
    BILD_MASS[_name] = (FAHRZEUG_BILD["flaeche"], FAHRZEUG_BILD["flaeche"])

# Krad und Jagdpanzer (seit 0.34.107, art_neue_fahrzeuge.py). Das Krad in
# vier Fassungen: leer, mit Fahrer, mit Fahrer und Beifahrer - je neutral
# und je Mannschaft. Beim Jagdpanzer ist die Kanone samt Kommandant der
# drehende Teil (`jagdpanzer_rohr`, groesser: das Rohr ragt weit hinaus).
for _name in ("krad", "krad_fahrer", "krad_beiwagen", "krad_beiwagen_fahrer", "krad_wrack",
              "krad_schatten"):
    BILD_MASS[_name] = (96, 96)
for _team in TEAMS["kombi"]:
    for _grund in ("krad", "krad_beiwagen"):
        BILD_MASS["%s_%s_fahrer" % (_grund, _team["name"].lower())] = (96, 96)
    BILD_MASS["jagdpanzer_rohr_%s_fahrer" % _team["name"].lower()] = (160, 160)
for _name in ("jagdpanzer", "jagdpanzer_wrack", "jagdpanzer_schatten"):
    BILD_MASS[_name] = (FAHRZEUG_BILD["flaeche"], FAHRZEUG_BILD["flaeche"])
for _name in ("jagdpanzer_rohr", "jagdpanzer_rohr_fahrer"):
    BILD_MASS[_name] = (160, 160)

# Was der Spieler zu Beginn auf den Plaetzen 1 bis 6 traegt.
#
# Das Brecheisen steht **nicht** mehr darin. Es liegt auf einer eigenen
# Taste und ist damit immer da, ohne einen Platz zu belegen - siehe
# NAHKAMPF. Ein Werkzeug, das man im Gedraenge braucht, sollte keinen
# Waffenwechsel kosten.
HOTBAR = ["repetierer", "sturm", "schrot", "scharf", "lmg", "granate",
          "rauch", "molotov", "blend", "c4"]

# "Jeder hat alles" als Kategorien-Hotbar (seit 0.34.85). Gemeldet: in
# JEDER HAT ALLES waren "bei weitem nicht alle Waffen oder Utilities
# drinnen" - es waren die zehn alten aus HOTBAR. Jetzt traegt man alle; die
# Tasten 1 bis 9 waehlen eine Gruppe, noch einmal gedrueckt die naechste
# Waffe darin (wie in alten Shootern). Das Brecheisen bleibt auf F, der
# Raketenwerfer kommt weiter nur von der Karte (Regel RAKETENWERFER).
ALLES_GRUPPEN = (
    ("GEWEHRE", ("sturm", "repetierer", "scharf", "praezision", "unterhebel", "panzerbuechse")),
    ("PISTOLEN, MP", ("mp", "revolver", "zwillinge")),
    ("SCHROT", ("schrot", "doppelflinte", "autoschrot")),
    ("MG", ("lmg", "minigun")),
    ("SCHWER", ("granatwerfer", "einwegwerfer", "raketenbuendel", "flammenwerfer")),
    ("ENERGIE", ("spule", "kettenblitz", "spiegellaser", "kugelblitz", "nagler", "bolzer")),
    ("GRANATEN", ("granate", "rauch", "blend", "molotov", "gas", "kuller", "knaller", "schneeball")),
    ("SPRENGSTOFF", ("c4", "haftladung", "emp")),
)


# Die Anzeige (seit 0.34.90).
ANZEIGE = dict(
    # GRAFIKKARTE SKALIERT auch dann, wenn SDL nur einen Ersatz ohne
    # Grafikkarte findet ("no fast renderer")? Nein: der waere langsamer
    # als das Vergroessern im Spiel. Die Tests schalten es ein, weil es im
    # Fenster ohne Bildschirm nur den Ersatz gibt.
    gpu_ohne_grafikkarte=False,
)

# Waffe -> Nummer ihrer Gruppe (seit 0.34.89; gefragt in jedem Bild).
ALLES_GRUPPE_VON = {w: i for i, (_n, waffen) in enumerate(ALLES_GRUPPEN) for w in waffen}

# So weit ausserhalb des Bildes wird ein Wesen noch gezeichnet (Pixel,
# seit 0.34.89): mehr, als das groesste Bild (Panzer samt Rohr) und seine
# Schichten hineinragen koennen - weiter draussen kostet es nur Zeit.
ZEICHNEN_RAND = 200


def alles_waffen() -> list:
    """Alle Waffen von "jeder hat alles", Gruppe fuer Gruppe."""
    return [w for _name, waffen in ALLES_GRUPPEN for w in waffen if w in WAFFEN]


# Werkzeuge auf C fuer alle (seit 0.34.85): in "jeder hat alles" legt jeder
# jedes Werkzeug, das sonst nur eine Klasse hat - X schaltet weiter. Je
# Werkzeug die Pause bis zum naechsten (s), wie bei den Klassen.
WERKZEUGE = (
    ("sandsackwand", 30.0), ("munitionskiste", 40.0), ("sanitasche", 25.0),
    ("stacheldraht", 30.0), ("sprengfalle", 25.0), ("kraehenfuesse", 25.0),
    ("kanister", 25.0), ("horchposten", 45.0), ("drohne", 45.0), ("geschuetz", 70.0),
)

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
    # Mit so vielen Saetzen faengt ein Konto an. Seit 0.34.94 kann man
    # beliebig viele dazu anlegen (gewuenscht) - `hoechstens` ist nur eine
    # Grenze gegen ein Profil, das ins Unendliche waechst.
    plaetze=3,
    hoechstens=999,
    waffen=2,                 # Waffen eines Satzes ohne Klasse (Haupt + Seite, seit 0.34.91 je Klasse: KLASSEN plaetze)
    wuerfe=1,                 # so viele Wurfwaffen je Loadout
    # Woraus gewaehlt werden darf. Bewusst als eigene Listen und nicht
    # aus WAFFEN abgeleitet: was waehlbar ist, ist eine Spielentscheidung
    # und nicht dasselbe wie das, was es gibt.
    auswahl_waffen=("repetierer", "sturm", "schrot", "scharf", "lmg",
                    # Aus dem Waffenpaket (seit 0.34.62)
                    "revolver", "zwillinge", "mp", "praezision", "unterhebel",
                    "panzerbuechse", "doppelflinte", "autoschrot", "minigun",
                    "granatwerfer", "einwegwerfer", "raketenbuendel",
                    # Nahkampf und Werkzeug (seit 0.34.66)
                    "bolzer", "nagler",
                    # Hammer, Schockstab, Schlagring, Kettensaege, Wurfmesser
                    # und Speer liegen seit 0.34.96 auf F (NAHKAMPF waehlbar).
                    # Energie und Feuer (seit 0.34.68)
                    "spule", "kettenblitz", "spiegellaser", "kugelblitz",
                    "flammenwerfer"),
    auswahl_wuerfe=("granate", "rauch", "molotov", "blend", "c4",
                    # Gegen Fahrzeuge (seit 0.34.65)
                    "haftladung", "emp",
                    # Aus dem Waffenpaket (seit 0.34.67)
                    "gas", "kuller", "knaller", "schneeball"),
    # Womit ein neues Loadout vorbelegt wird. Drei Stueck, damit man nach
    # dem ersten Anmelden gleich drei brauchbare Saetze hat und nicht vor
    # drei leeren Plaetzen sitzt.
    # Seit 0.34.91 mit Klasse (KLASSE PFLICHT ist die Vorgabe) und mit
    # Haupt- und Seitenwaffe.
    vorlagen=(
        dict(name="STURM", klasse="schuetze", waffen=("sturm", "repetierer"),
             wuerfe=("granate",)),
        dict(name="JÄGER", klasse="scharfschuetze", waffen=("scharf", "revolver"),
             wuerfe=("rauch",)),
        dict(name="NAHKAMPF", klasse="pionier", waffen=("schrot", "nagler", "einwegwerfer"),
             wuerfe=("granate",)),
    ),
    namenslaenge=16,          # seit 0.34.94 16 statt 12, Zeichen frei (was die Schrift kann)
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
    # Seit 0.34.96: was man im Loadout fuer F waehlen kann. Nahkampfwaffen
    # belegen keinen Waffenplatz mehr, sie ersetzen das Brecheisen.
    waehlbar=("brecheisen", "hammer", "speer", "wurfmesser", "schockstab",
              "schlagring", "kettensaege"),
    sperrt_feuer=True,        # waehrend des Schwungs wird nicht geschossen
    # So lange bleibt das Eisen nach dem Schwung noch in der Hand (seit
    # 0.32.8, gemeldet: "die Waffe soll frueher versteckt werden - gerade
    # sieht es aus, als haette man sie noch"). Der Schwung allein dauert
    # 0.26 s; mit dem Nachhalten sieht man ihn auch, wenn man nicht
    # gerade hinschaut.
    nachhalten=0.14,
)

# Der Schwung mit der gewaehlten Nahkampfwaffe in der Hand (seit 0.34.140,
# gemeldet: "bei F wird immer das Brecheisen angezeigt"): je Waffe eigene
# Bilder spieler[_<team>]_schwung_<i>_<waffe>; das Brecheisen bleibt ohne Zusatz.
for _nk in NAHKAMPF["waehlbar"]:
    if _nk == NAHKAMPF["waffe"]:
        continue
    for _i in range(SCHWUNG_BILDER):
        BILD_MASS["spieler_schwung_%d_%s" % (_i, _nk)] = (64, 64)
        for _team in TEAMS["kombi"]:
            BILD_MASS["spieler_%s_schwung_%d_%s" % (_team["name"].lower(), _i, _nk)] = (64, 64)

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
    # Napalm (seit 0.34.130, gewuenscht "aggressiver"): klebriges Feuer -
    # dunkler, roeter, mit schwarzem, oeligem Russ am Rand, einem gelbweissen
    # Kern, zuengelt schneller, mehr Funken und schwarzer Rauch steigt auf.
    napalm_toene=((52, 14, 8), (150, 26, 10), (220, 64, 14), (252, 150, 34), (255, 236, 150)),
    napalm_russ=(22, 14, 10),
    napalm_schwelle=0.27,     # brennt dichter als gewoehnliches Feuer
    napalm_zunge=2.8,         # und zuengelt schneller
    napalm_funken=6.0,
    napalm_rauch=1.6,         # schwarze Rauchwolken je Sekunde
)

# Die Minikarte oben links (minikarte.py), ein Versuch. Groesse in
# Spielpixeln: hoechstens so breit und hoch, die Seiten wie die Karte.
# Die Anzeige im Gefecht (seit 0.34.92, nach der Skizze): unten links die
# runde Karte mit der Panzerung als Bogen darum, daneben der Kreis der
# Faehigkeit mit den Dashes als Bogen. Pixel im 640x360-Bild.
HUD = dict(
    karte_d=84,               # Durchmesser der runden Karte (seit 0.34.100 groesser, vorher 72)
    karte_x=10,               # ihr linker Rand
    unten=6,                  # Abstand der Kreise vom unteren Bildrand
    karte_zoom=1.5,           # so viel groesser als die alte Karte oben links
    karte_ganz=1.0,           # die laengere Kartenseite = so viel vom Durchmesser (seit 0.34.96)
    bogen_abstand=0,          # der Ring liegt direkt am Kreis an (seit 0.34.93)
    bogen_dicke=5,
    bogen_von=200.0,          # Grad (0 = rechts, 90 = oben): von links unten ...
    bogen_bis=-20.0,          # ... ueber oben bis rechts unten
    segmente=18,              # die Platten der Panzerung, wie vorher
    faeh_d=30,                # Durchmesser des Kreises der Faehigkeit
    faeh_luft=14,             # Abstand zwischen Karte und Faehigkeit
    tafel_breite=300,         # die Tafel auf TAB
    extra_feld=28,            # Kantenlaenge der Felder BRECHEISEN und MEDKIT (seit 0.34.94)
    extra_rand=4,             # so viel Rand bleibt um ihr Symbol mindestens
    extra_abstand=10,         # Abstand der Felder BRECHEISEN und MEDKIT zur Hotbar (seit 0.34.93)
    waffe_zeigen=1.4,         # so lange steht nach dem Wechsel der Name am Zeiger (s)
)

# Das Kartenbild (kartenbild.py, seit 0.34.100): der Grundriss fuer die runde
# Karte und die Nachschubkarte, gross gemalt und weich verkleinert.
# ziel_pixel: so lang wird die laengere Seite ungefaehr (zwischen mindest
# und hoechstens Pixel je Kachel). rauschen: so viel heller oder dunkler
# ist eine Kachel als die naechste.
KARTENBILD = dict(
    ziel_pixel=2400, mindest=2, hoechstens=16, rauschen=5,   # seit 0.34.138 feiner (vorher 1500)
    sand=(92, 74, 52), piste=(118, 96, 66), kies=(86, 80, 70), gestruepp=(80, 82, 50),
    pflaster=(104, 98, 88), dielen=(108, 82, 56), gitter=(72, 72, 74),
    schatten=(44, 34, 24), treppe=(72, 170, 158),
    wand=(196, 170, 128), fels=(150, 128, 98), wand_licht=(214, 192, 150), wand_dunkel=(122, 100, 72),
    deckung=(176, 148, 104), deckung_rand=(52, 38, 26),
    seicht=(84, 116, 118), wasser=(40, 72, 96),
    # Seit 0.34.131: je Kachelsatz andere Farben (kartenbild._farben).
    saetze={
        "gruen": dict(sand=(66, 92, 48), piste=(108, 90, 62), kies=(100, 98, 84),
                      gestruepp=(80, 106, 54), pflaster=(108, 106, 100), dielen=(112, 84, 54),
                      seicht=(76, 118, 126), wasser=(38, 74, 104), schatten=(34, 50, 28),
                      wand=(178, 172, 156), fels=(122, 132, 110), wand_licht=(206, 202, 186),
                      wand_dunkel=(96, 100, 86), deckung=(150, 136, 104),
                      deckung_rand=(36, 44, 28), baum=(38, 70, 34)),
        "stadt": dict(sand=(118, 108, 94), piste=(44, 44, 48), kies=(100, 94, 88),
                      gestruepp=(74, 102, 56), pflaster=(122, 120, 116), dielen=(140, 136, 128),
                      seicht=(70, 100, 110), wasser=(34, 60, 76), schatten=(30, 30, 34),
                      wand=(176, 104, 80), fels=(156, 156, 150), wand_licht=(206, 140, 110),
                      wand_dunkel=(112, 64, 50), deckung=(150, 146, 140),
                      deckung_rand=(30, 30, 34), baum=(46, 82, 40)),
    },
)

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
    schwer_mass=1.6,          # Panzer und Panzerwagen so viel groesser (seit 0.34.59)
    # Fahrzeugzeichen (seit 0.34.138): das eigene Bild, so viel mal so lang wie
    # der Wagen auf der Karte waere, aber mindestens/hoechstens so viele Pixel
    # (mal dem Massstab der Karte). Gegner im Wagen nur, wenn ein Eigener
    # naeher als `sicht` px steht (oder er markiert ist).
    symbol_mass=2.2, symbol_mindest=5, symbol_hoechstens=16, sicht=650.0,
    # Im Stoerkreis eines gegnerischen Funkwagens (seit 0.34.115): Rauschen
    # statt Punkte - dicht, das Bild wechselt `takt` mal je Sekunde unter
    # `bilder` Stellungen; ein heller Streifen wandert `streifen_tempo` mal
    # je Sekunde ueber die Karte. Je Funkwagen im Kreis ein Ping (zwei Ringe,
    # `ping_dauer` Sekunden je Welle).
    gestoert=dict(dichte=0.42, bilder=6, takt=14.0, streifen_tempo=0.7, streifen_hoehe=0.12,
                  ping_dauer=1.4),
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

# Kosmetik im Spiel bearbeiten (seit 0.34.135, kosmetik_bearbeiten.py).
# Dateien liegen im Ordner `ordner` neben den Einstellungen oder werden ins
# Fenster gezogen; groesser als `datei_max` Bytes wird nichts gelesen, von
# einem Ton hoechstens `ton_quelle_max` s. Heraus kommt eine WAV mit `rate`.
# LAUTER geht von lauter[0] bis lauter[1] (mal), BASS mischt bis `bass` mal
# den Tiefpass unter `bass_grenze` Hz dazu, GROESSE ist die Hoehe des Bildes
# als Anteil am Schirm.
KOSMETIK_EDITOR = dict(
    ordner="kosmetik",
    datei_max=40_000_000,
    ton_quelle_max=600,
    rate=22050,
    lauter=(0.5, 3.0),
    bass=2.0,
    bass_grenze=160.0,
    groesse=(0.1, 2.0),
    vorschau_laut=0.8,
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
# Das Zeichen jeder anderen Waffe (seit 0.34.135, gemeldet: auf der
# Kontoseite und in der Kosmetik standen neue Waffen lila): dasselbe Bild
# wie in der Hotbar (inventar.symbol).
for _w in WAFFEN:
    SKIN_ROLLEN.setdefault("%s_symbol" % _w, "waffe_%s" % _w)

# ══════════════════════════════════════════════════ FIGUREN (seit 0.34.60)
#
# Die Figuren aus dem Paket `dustfront_figuren` (vier Runden mit dem
# Besitzer abgestimmt, alle auf "Behalten"): 14 Operators und 17 Soldaten
# als Aussehen fuer Spieler und Bots, 8 NPCs und 3 Tiere fuer die Welt.
# Gezeichnet in dustfront/art_figuren.py, im Stil von art._figur: 28 x 28,
# Blick nach +x, Schultern 14 x 16, Kopf r 5. Hier stehen nur die Daten -
# genau die Werte aus `designs.json` des Pakets.
#
#   rumpf, kante, akzent   wie bei art._figur
#   kopf                   Helm, Kappe, Kapuze ... (art_figuren._kopf)
#   kopffarbe, haut        Farben des Kopfes
#   weste, westenfarbe     platten, schwer, kreuz, bandelier, granaten
#   ruecken                Funkgeraet, Rucksack, Fallschirm ...
#   arme                   waffe (Vorgabe): haelt, was er traegt. Sonst
#                          etwas Festes (Schild, Pistole, Klemmbrett ...)
#   tarn                   Farben der Tarnflecken
#   ghillie, breit, rang, armbinde, offizier, brille, ausweis, nvg_an
#
# Gestaltungsregeln des Besitzers: Groesse wie die bestehenden Figuren,
# keine Pflichtwaffe, keine Maentel, Soldaten bleiben gruen - die
# Mannschaft zeigen helle Neon-Markierungen (FIGUREN_NEON), NPC-Haende
# vorn, Gegenstaende nicht fest an der Figur.
FIGUREN = {
    # OPERATOR
    "ghost": dict(name='GHOST', text='Totenkopf als Sichel vorn, nicht mehr nach oben schauend; Funkgerät', rumpf=(52, 54, 56), kante=(18, 18, 20), akzent=(226, 60, 44), kopf='totenkopf', ruecken='funk', weste='platten', westenfarbe=(36, 38, 40)),
    "spectre": dict(name='SPECTRE', text='Dreiröhren-Nachtsicht, leuchtet', rumpf=(44, 50, 66), kante=(16, 18, 26), akzent=(120, 255, 140), kopf='nvg', kopffarbe=(58, 64, 78), nvg_an=True, tarn=((40, 44, 56), (28, 30, 38), (60, 64, 78)), weste='platten', westenfarbe=(30, 34, 44)),
    "reaper": dict(name='REAPER', text='Kapuze, rote Augen, Plattenweste - ohne Umhang', rumpf=(72, 62, 58), kante=(22, 18, 18), akzent=(236, 50, 40), kopf='kapuze_augen', kopffarbe=(64, 54, 50), umhang=(54, 46, 44), weste='platten', westenfarbe=(46, 40, 38)),
    "viper": dict(name='VIPER', text='Shemagh, Waldtarn, Brille', rumpf=(76, 88, 52), kante=(28, 34, 20), akzent=(200, 230, 90), kopf='shemagh', kopffarbe=(140, 132, 96), tarn=((70, 84, 48), (52, 60, 36), (110, 100, 64)), weste='kreuz'),
    "nomad": dict(name='NOMAD', text='Boonie-Hut, großer Rucksack', rumpf=(168, 144, 102), kante=(66, 52, 32), akzent=(110, 170, 120), kopf='boonie', kopffarbe=(150, 128, 88), pack=(118, 104, 70), ruecken='rucksack', tarn=((170, 146, 102), (130, 106, 70), (186, 166, 124))),
    "ronin": dict(name='RONIN', text='Rotes Stirnband, Klinge auf dem Rücken', rumpf=(78, 74, 76), kante=(24, 22, 24), akzent=(206, 52, 40), haut=(164, 118, 82), kopf='stirnband', kopffarbe=(30, 26, 24), ruecken='schwert'),
    "havoc": dict(name='HAVOC', text='Schwere Panzerung, Visierhelm', rumpf=(78, 80, 74), kante=(24, 26, 24), akzent=(240, 160, 50), breit=True, kopf='visier', kopffarbe=(60, 62, 58), weste='schwer', westenfarbe=(46, 48, 44)),
    "raven": dict(name='RAVEN', text='Rabenschwarz, Zweiröhren-NVG, ohne Umhang', rumpf=(64, 60, 72), kante=(18, 16, 22), akzent=(170, 120, 230), kopf='nvg2', kopffarbe=(58, 54, 66), umhang=(46, 42, 54), weste='platten', westenfarbe=(40, 38, 46)),
    "falcon": dict(name='FALCON', text='Pilotenhelm, Fallschirm', rumpf=(104, 108, 92), kante=(38, 40, 32), akzent=(240, 190, 60), kopf='pilot', kopffarbe=(196, 196, 186), ruecken='fallschirm'),
    "cobra": dict(name='COBRA', text='Barett, Funk, Kreuzgurte', rumpf=(88, 96, 58), kante=(32, 36, 20), akzent=(240, 210, 90), haut=(122, 84, 58), kopf='barett', kopffarbe=(40, 70, 40), ruecken='funk', weste='kreuz'),
    "mantis": dict(name='MANTIS', text='Ghillie-Anzug, Scharfschütze', rumpf=(78, 90, 50), kante=(30, 36, 18), akzent=(200, 240, 120), ghillie=True, kopf='boonie', kopffarbe=(84, 92, 54), tarn=((70, 84, 48), (52, 60, 36), (110, 100, 64))),
    "jackal": dict(name='JACKAL', text='Kappe verkehrt, Wüstentarn', rumpf=(176, 150, 106), kante=(70, 56, 36), akzent=(230, 120, 60), kopf='kappe_rueck', kopffarbe=(110, 94, 70), tarn=((170, 146, 102), (130, 106, 70), (186, 166, 124)), weste='platten', westenfarbe=(132, 112, 78)),
    "wolf": dict(name='WOLF', text='Sturmhaube, Schneebrille, Headset - keine Haut', rumpf=(196, 200, 202), kante=(70, 74, 78), akzent=(90, 170, 230), kopf='headset_maske', kopffarbe=(214, 218, 220), tarn=((200, 204, 206), (150, 156, 160), (220, 222, 224)), weste='platten', westenfarbe=(150, 156, 160)),
    "kestrel": dict(name='KESTREL', text='Helmkamera, Stadttarn', rumpf=(100, 102, 104), kante=(32, 34, 36), akzent=(255, 120, 60), kopf='kamera_helm', kopffarbe=(78, 80, 82), tarn=((96, 98, 100), (60, 62, 66), (130, 132, 132)), weste='platten', westenfarbe=(56, 58, 60)),
    # SOLDAT
    "rekrut": dict(name='REKRUT', text='Einfacher Helm, sonst nichts', rumpf=(112, 114, 76), kante=(40, 42, 24), akzent=(210, 200, 150), kopf='helm', kopffarbe=(96, 100, 64)),
    "schuetze": dict(name='SCHÜTZE', text='Helm, Weste, Rucksack', rumpf=(104, 110, 70), kante=(38, 40, 22), akzent=(210, 200, 150), kopf='helm', kopffarbe=(90, 96, 60), ruecken='rucksack', tarn=((70, 84, 48), (52, 60, 36), (110, 100, 64)), weste='platten'),
    "gefreiter": dict(name='GEFREITER', text='Rangabzeichen an den Schultern', rumpf=(104, 110, 70), kante=(38, 40, 22), akzent=(210, 200, 150), kopf='helm', kopffarbe=(90, 96, 60), rang=2, tarn=((70, 84, 48), (52, 60, 36), (110, 100, 64)), weste='platten'),
    "mg_schuetze": dict(name='MG-SCHÜTZE', text='Breit, Patronengurt', rumpf=(98, 104, 66), kante=(34, 36, 20), akzent=(210, 200, 150), breit=True, kopf='helm', kopffarbe=(84, 90, 56), tarn=((70, 84, 48), (52, 60, 36), (110, 100, 64)), weste='bandelier'),
    "funker": dict(name='FUNKER', text='Funkgerät mit Peitschenantenne', rumpf=(104, 110, 70), kante=(38, 40, 22), akzent=(210, 200, 150), kopf='kopfhoerer', kopffarbe=(70, 52, 34), ruecken='funk', tarn=((70, 84, 48), (52, 60, 36), (110, 100, 64))),
    "sanitaeter": dict(name='SANITÄTER', text='Armbinde, Sanitätstasche', rumpf=(110, 112, 80), kante=(40, 42, 26), akzent=(230, 230, 220), armbinde=True, kopf='helm', kopffarbe=(96, 100, 66), ruecken='sani'),
    "pionier": dict(name='PIONIER', text='Weste, Sprengladungen und Zündschnur am Rucksack', rumpf=(104, 100, 70), kante=(38, 36, 22), akzent=(230, 160, 50), arme='waffe', kopf='helm', kopffarbe=(88, 86, 58), ruecken='sprengpack', weste='platten'),
    "grenadier": dict(name='GRENADIER', text='Granaten am Gurt', rumpf=(100, 106, 68), kante=(36, 38, 22), akzent=(220, 160, 60), kopf='helm', kopffarbe=(86, 92, 58), tarn=((70, 84, 48), (52, 60, 36), (110, 100, 64)), weste='granaten'),
    "scharfschuetze": dict(name='SCHARFSCHÜTZE', text='Boonie, halber Ghillie', rumpf=(92, 100, 60), kante=(32, 36, 20), akzent=(200, 220, 140), ghillie=True, kopf='boonie', kopffarbe=(100, 104, 66)),
    "offizier": dict(name='OFFIZIER', text='Feldmütze mit Abzeichen, Schulterklappen mit Sternen, Fernglas', rumpf=(104, 110, 70), kante=(38, 40, 22), akzent=(196, 196, 150), kopf='feldmuetze_offizier', kopffarbe=(84, 92, 58), offizier=True, ruecken='fernglas', tarn=((70, 84, 48), (52, 60, 36), (110, 100, 64)), weste='platten', westenfarbe=(76, 82, 52)),
    "schildtraeger": dict(name='SCHILDTRÄGER', text='Großes gewölbtes Schild mit Sichtfenster', rumpf=(104, 110, 70), kante=(38, 40, 22), akzent=(150, 200, 200), alt_id='rhino', arme='schild', breit=True, kopf='visier', kopffarbe=(90, 96, 60), schildfarbe=(78, 86, 64), tarn=((70, 84, 48), (52, 60, 36), (110, 100, 64)), weste='schwer', westenfarbe=(70, 76, 46)),
    "panzerfahrer": dict(name='PANZERFAHRER', text='Gepolsterte Haube, Brille', rumpf=(78, 76, 66), kante=(26, 24, 20), akzent=(140, 200, 220), arme='pistole', kopf='haube', kopffarbe=(84, 66, 46)),
    "fallschirmjaeger": dict(name='FALLSCHIRMJÄGER', text='Rundhelm, Schirmpack', rumpf=(118, 108, 78), kante=(42, 38, 24), akzent=(200, 200, 150), kopf='helm', kopffarbe=(80, 84, 60), ruecken='fallschirm', tarn=((96, 90, 60), (140, 128, 92))),
    "gebirgsjaeger": dict(name='GEBIRGSJÄGER', text='Winterweiß, Schlafrolle', rumpf=(200, 202, 200), kante=(72, 76, 78), akzent=(90, 140, 200), kopf='muetze', kopffarbe=(170, 172, 170), pack=(150, 150, 140), ruecken='rolle', tarn=((200, 204, 206), (150, 156, 160), (220, 222, 224))),
    "wuestenschuetze": dict(name='WÜSTENSCHÜTZE', text='Shemagh, Sandtarn', rumpf=(172, 146, 104), kante=(68, 54, 34), akzent=(220, 120, 60), kopf='shemagh', kopffarbe=(196, 180, 140), tarn=((170, 146, 102), (130, 106, 70), (186, 166, 124)), weste='platten', westenfarbe=(140, 118, 80)),
    "stadtkaempfer": dict(name='STADTKÄMPFER', text='Grautarn, Visier', rumpf=(100, 102, 104), kante=(34, 36, 38), akzent=(120, 200, 230), kopf='visier', kopffarbe=(70, 72, 76), tarn=((96, 98, 100), (60, 62, 66), (130, 132, 132)), weste='platten', westenfarbe=(60, 62, 66)),
    "wachposten": dict(name='WACHPOSTEN', text='Mütze, Lampe an der Schulter - ohne Mantel', rumpf=(104, 110, 70), kante=(38, 40, 22), akzent=(230, 200, 120), arme='waffe', kopf='muetze', kopffarbe=(70, 76, 50), mantel=(80, 84, 62), ruecken='schulterlampe', tarn=((70, 84, 48), (52, 60, 36), (110, 100, 64))),
    # NPC
    "haendler": dict(name='HÄNDLER', text='Turban, riesiger Packen', rumpf=(150, 92, 54), kante=(56, 32, 18), akzent=(60, 140, 160), arme='vorne', haut=(122, 84, 58), kopf='turban', kopffarbe=(196, 180, 140), ruecken='riesen'),
    "aerztin": dict(name='ÄRZTIN', text='OP-Kleidung, Armbinde, Klemmbrett, Tasche - ohne Kittel', rumpf=(92, 140, 132), kante=(30, 56, 52), akzent=(120, 180, 220), armbinde=True, arme='klemmbrett', kopf='zopf', kopffarbe=(110, 70, 40), mantel=(206, 202, 190), ruecken='sanitasche_klein'),
    "wissenschaftler": dict(name='WISSENSCHAFTLER', text='Helles Hemd, Ausweis, Brille, Messgerät - ohne Kittel', rumpf=(196, 198, 196), kante=(84, 84, 80), akzent=(120, 200, 160), arme='geigerzaehler', ausweis=True, brille=True, haut=(214, 176, 140), kopf='glatze', mantel=(214, 214, 208)),
    "fluechtling": dict(name='FLÜCHTLING', text='Kopftuch, Bündel auf dem Rücken', rumpf=(128, 102, 80), kante=(48, 36, 26), akzent=(200, 160, 110), arme='vorne', haut=(122, 84, 58), kopf='kopftuch', kopffarbe=(140, 70, 60), ruecken='buendel', umhang=(110, 86, 66)),
    "pilger": dict(name='PILGER', text='Kapuze, Laterne, Deckenrolle - ohne Mantel', rumpf=(140, 116, 86), kante=(52, 40, 28), akzent=(250, 200, 90), arme='laterne', kopf='kapuze_offen', kopffarbe=(124, 100, 72), mantel=(130, 106, 78), pack=(110, 92, 64), ruecken='rolle'),
    "schmuggler": dict(name='SCHMUGGLER', text='Lederjacke, Kappe, Kreuzgurte - ohne Kiste', rumpf=(84, 62, 48), kante=(28, 20, 16), akzent=(200, 160, 80), arme='vorne', haut=(122, 84, 58), kopf='kappe', kopffarbe=(44, 40, 38), mantel=(60, 52, 46), weste='kreuz'),
    "hirte": dict(name='HIRTE', text='Kopftuch, Hirtentasche an der Seite', rumpf=(150, 128, 96), kante=(56, 46, 30), akzent=(150, 60, 50), arme='halb_vorne', haut=(122, 84, 58), kopf='kopftuch', kopffarbe=(200, 186, 150), ruecken='tasche', umhang=(120, 96, 70)),
    "ueberlebende": dict(name='ÜBERLEBENDE', text='Senfgelbes Stirnband, Kanister', rumpf=(120, 96, 72), kante=(44, 34, 24), akzent=(206, 170, 64), arme='vorne', haut=(164, 118, 82), kopf='stirnband', kopffarbe=(70, 46, 30), ruecken='kanister'),
}

# Gruppen, in der Reihenfolge, in der das Paket sie zeigt.
FIGUREN_GRUPPEN = {
    "OPERATOR": ("ghost", "spectre", "reaper", "viper", "nomad", "ronin", "havoc", "raven",
                 "falcon", "cobra", "mantis", "jackal", "wolf", "kestrel"),
    "SOLDAT": ("rekrut", "schuetze", "gefreiter", "mg_schuetze", "funker", "sanitaeter",
               "pionier", "grenadier", "scharfschuetze", "offizier", "schildtraeger",
               "panzerfahrer", "fallschirmjaeger", "gebirgsjaeger", "wuestenschuetze",
               "stadtkaempfer", "wachposten"),
    "NPC": ("haendler", "aerztin", "wissenschaftler", "fluechtling", "pilger", "schmuggler",
            "hirte", "ueberlebende"),
}

# Die Mannschaft an der Figur: zwei Neon-Streifen auf den Schultern und ein
# Leuchtfleck am Hinterkopf, (Kern, Licht). Gemeldet: "Soldaten behalten
# ihren gruenen Look" - umgefaerbt wird nichts.
FIGUREN_NEON = {
    "ROT": ((255, 70, 52), (255, 186, 160)),
    "BLAU": ((52, 226, 255), (196, 250, 255)),
}

# Die UEBERLEBENDE bekommt ein zufaelliges Stirnband aus diesen Farben.
STIRNBAND_FARBEN = (("SENF", (206, 170, 64)), ("OLIV", (110, 124, 66)),
                    ("TÜRKIS", (64, 150, 150)), ("WEINROT", (140, 46, 56)),
                    ("SCHWARZ", (40, 38, 38)), ("WEISS", (222, 218, 204)))

# Die Tiere, je in drei Farben (die erste ist die Vorgabe). Eigene Masse:
# das Huhn ist bewusst klein, etwa so lang, wie eine Figur breit ist.
TIERE = {
    "schaf": dict(name="SCHAF", mass=(26, 20), leben=30.0, radius=8.0, farben=(
        ("WEISS", dict()),
        ("DUNKEL", dict(wolle=(96, 84, 74), gesicht=(30, 26, 24), seed=3)),
        ("GRAU", dict(wolle=(176, 172, 160), gesicht=(70, 62, 58), seed=5)))),
    "ziege": dict(name="ZIEGE", mass=(28, 18), leben=26.0, radius=7.0, farben=(
        ("BRAUN", dict()),
        ("SCHWARZ", dict(fell=(54, 48, 44), fleck=(210, 200, 182), seed=4)),
        ("SANDFARBEN", dict(fell=(196, 168, 120), fleck=(240, 232, 214), seed=6)))),
    "huhn": dict(name="HUHN", mass=(14, 11), leben=6.0, radius=4.0, farben=(
        ("BRAUN", dict()),
        ("WEISS", dict(gefieder=(232, 228, 216), fluegel=(196, 190, 176),
                       schwanz=(170, 164, 150))),
        ("SCHWARZ", dict(gefieder=(52, 54, 56), fluegel=(34, 36, 40),
                         schwanz=(24, 40, 36))))),
}

# NPCs in der Welt (Testmodus, seit 0.34.60): wie viel sie aushalten. Ihr
# Verhalten kommt mit der Kampagne (docs/KI.md).
NPC = dict(leben=60.0, radius=9.0)
# Wie die Tiere herumlaufen (Testmodus): ein Stueck in eine Richtung, dann
# eine Weile stehen. tempo in Pixeln je Sekunde, weite der Schritt, pause
# (von, bis) in Sekunden. reibung bremst einen Stoss (Treffer, Explosion).
TIER_LAUFEN = dict(tempo=(18.0, 30.0), weite=(16.0, 52.0), pause=(1.2, 4.5),
                   reibung=7.0)


def bild_kennung(text: str) -> str:
    """Ein angezeigter Name als Teil eines Bildnamens: klein, ohne Umlaute
    ("TÜRKIS" -> "tuerkis")."""
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.lower().replace(a, b)
    return text.replace(" ", "_").replace("-", "_")


# Die NPCs und Tiere sind feste Bilder (art_figuren.py). Die Skins der
# Spieler dagegen stehen nicht hier: sie kommen aus einem Muster
# (core.platzhalter_muster), sonst waeren es ueber tausend Eintraege.
for _skin in FIGUREN_GRUPPEN["NPC"]:
    BILD_MASS["npc_" + _skin] = BILD_MASS["spieler"]
for _band, _f in STIRNBAND_FARBEN:
    BILD_MASS["npc_ueberlebende_" + bild_kennung(_band)] = BILD_MASS["spieler"]
for _art, _t in TIERE.items():
    for _i, (_fn, _w) in enumerate(_t["farben"]):
        BILD_MASS["tier_%s" % _art if _i == 0
                  else "tier_%s_%s" % (_art, bild_kennung(_fn))] = _t["mass"]


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
        tempo=118.0 * 1.3,       # schneller als ein laufender Spieler (seit 0.34.135 mit ihm 1,3 mal so schnell)
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
