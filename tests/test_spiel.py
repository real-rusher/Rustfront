# -*- coding: utf-8 -*-
"""Kurzer Funktionstest des Spiels: laeuft ohne Fenster, macht Bilder."""
import os, sys, math, time, random
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame
from dustfront import config as K
from dustfront.core import App
from dustfront.play import Spiel

app = App("test", None, headless=True)
# Fester Seed: sonst wuerfelt jede Runde eine andere Karte aus, und
# Pruefungen wie "Rueckweg vorhanden" faellt mal so und mal so aus.
szene = Spiel(app, seed=20250920)
app.schieben(szene)
held = szene.held
e = app.eingabe

def sim(sekunden, halten=(), maus=None, klicks=()):
    n = int(sekunden / K.FIXED_DT)
    for i in range(n):
        e.neues_bild()
        e._gehalten = set(halten)
        for k in klicks:
            if i % 30 == 0:
                e._gedrueckt.add(k)
        if maus: e.maus = pygame.Vector2(maus)
        szene.schritt(K.FIXED_DT)

def bild(name):
    app.flaeche.fill(K.C_VOID)
    szene.zeichnen(app.flaeche, 0.0)
    pygame.image.save(pygame.transform.scale(app.flaeche, (K.GAME_W*2, K.GAME_H*2)), name)
    print("gespeichert", name)

fails = []
def pruef(t, ok, zusatz=""):
    print(("  ok  " if ok else "FAIL  ") + t
          + (("   " + zusatz) if zusatz else ""))
    if not ok: fails.append(t)

pruef("Spieler lebt", held.lebt)
pruef("Drei Ebenen", len(szene.welt.ebenen) == 3)
pruef("Start begehbar", szene.welt.frei(held.pos, held.radius, 0))

# Welle startet
sim(3.0)
pruef("Welle 1 laeuft", szene.welle >= 1 and szene.gegner_uebrig > 0)

# Laufen nach rechts, dabei schiessen
held.pos.update(10*K.TILE+16, 12*K.TILE+16); held.tempo.update(0,0)
start = pygame.Vector2(held.pos)
sim(1.2, halten={"rechts", "feuer"}, maus=(620, 180))
pruef("Spieler bewegt sich", held.pos.distance_to(start) > 30)
pruef("Munition verbraucht", held.magazin["repetierer"] < K.WAFFEN["repetierer"]["magazin"])
pruef("Geschosse unterwegs oder eingeschlagen", len(szene.welt.partikel) > 0)
bild("spiel_1_gefecht.png")

# Nachladen
held.magazin["repetierer"] = 0
held.feuert = True
sim(2.0, halten={"feuer"}, maus=(620, 180))
pruef("hat automatisch nachgeladen", held.magazin["repetierer"] > 0)

# ── Die sechs Waffen ─────────────────────────────────────────────────
# Jede bekommt denselben Aufbau: freies Feld, ein Ziel in passender
# Entfernung, ein Schuss, dann so lange rechnen, bis es angekommen sein
# muss. Gemessen wird der Schaden am Ziel, nicht der Zustand irgendeiner
# internen Liste - was zaehlt, ist ob es trifft.
from dustfront.entities import Gegner

def freies_feld():
    """Ein Punkt mit viel Platz nach rechts, fuer die Schussbahnen."""
    for kx in range(4, szene.welt.ebene(0).breite - 12):
        p = pygame.Vector2(kx*K.TILE+16, 12*K.TILE+16)
        weit = pygame.Vector2(p.x + 260, p.y)
        if (szene.welt.frei(p, held.radius, 0)
                and szene.welt.frei(weit, 12, 0)
                and szene.welt.sicht_frei(p, weit, 0)):
            return p
    return pygame.Vector2(10*K.TILE+16, 12*K.TILE+16)

def probe(waffe, entfernung, dauer=1.4, halten=()):
    """Feuert einmal auf ein Ziel und gibt den angerichteten Schaden zurueck."""
    # Das Feld raeumen. Die Welt sammelt tote Wesen beim naechsten Schritt
    # selbst ein, es gibt also nichts zu loeschen.
    for g in list(szene.welt.wesen) + list(szene.welt.neue):
        if isinstance(g, Gegner):
            g.lebt = False
    szene.welt.schritt(K.FIXED_DT)
    held.unverwundbar = 999.0        # sonst misst man fremde Treffer mit
    start = freies_feld()
    held.pos.update(start); held.tempo.update(0, 0); held.ebene = 0
    held.takt = 0.0; held.nachlade_rest = 0.0; held.fokus = 0.0
    held.feuert = False; held.will.update(0, 0)   # kein Dauerfeuer von vorhin
    held.waffe = held.waffen.index(waffe)
    held.magazin[waffe] = max(1, K.WAFFEN[waffe]["magazin"])
    ziel = Gegner(start + pygame.Vector2(entfernung, 0), "laeufer", 0)
    ziel.leben = 9999.0
    szene.welt.dazu(ziel)
    vorher = ziel.leben

    def festhalten():
        """Das Ziel bleibt stehen, wo es hingehoert, und der Held auch.

        Sonst laeuft der Gegner in der Einzielzeit heran und schiebt den
        Schuetzen zur Seite - gemessen wuerde dann die Schubkraft, nicht die
        Treffsicherheit der Waffe.
        """
        held.pos.update(start)
        held.tempo.update(0, 0)
        ziel.pos.update(start + pygame.Vector2(entfernung, 0))
        ziel.tempo.update(0, 0)
        held.ziel = pygame.Vector2(ziel.pos)

    festhalten()
    # Ein Schritt, damit der Blickwinkel dem Ziel folgt: winkel wird in
    # schritt() gesetzt, und der Nahkampfkegel haengt daran.
    szene.welt.schritt(K.FIXED_DT)
    if halten:
        held.zielt = True
        for _ in range(int(1.6 / K.FIXED_DT)):
            festhalten()
            szene.welt.schritt(K.FIXED_DT)
    festhalten()
    held.feuern()
    for _ in range(int(dauer / K.FIXED_DT)):
        festhalten()
        szene.welt.schritt(K.FIXED_DT)
    held.zielt = False
    schaden = vorher - ziel.leben
    ziel.lebt = False
    return schaden

pruef("Hotbar hat sechs Plaetze", len(held.waffen) == 6)
pruef("Alle sechs Waffen sind bekannt",
      all(w in K.WAFFEN for w in held.waffen))

s = probe("repetierer", 150)
pruef("Repetierer trifft auf 150 px", s > 0, "%.0f Schaden" % s)
s = probe("sturm", 150)
pruef("Sturmgewehr trifft auf 150 px", s > 0, "%.0f Schaden" % s)
s = probe("schrot", 90)
pruef("Schrot trifft nah und mehrfach", s > K.WAFFEN["schrot"]["schaden"],
      "%.0f Schaden" % s)
s = probe("granate", 95)
pruef("Granate trifft auch nah", s > 0, "%.0f Schaden" % s)
s = probe("brecheisen", 30)
pruef("Brecheisen trifft auf Armlaenge", s > 0, "%.0f Schaden" % s)
s = probe("brecheisen", 120)
pruef("Brecheisen trifft nicht durch den Raum", s == 0, "%.0f Schaden" % s)

# Scharfschuetze: aus der Hueffte breit, im Fokus schmal
held.pos.update(freies_feld()); held.tempo.update(0, 0)
held.waffe = held.waffen.index("scharf")
held.fokus = 0.0
hueffte = held.streuung_jetzt
held.fokus = 1.0
eingezielt = held.streuung_jetzt
pruef("Scharfschuetze streut aus der Hueffte weit", hueffte > 10.0,
      "%.1f Grad" % hueffte)
pruef("und im Fokus kaum noch", eingezielt < 0.5, "%.2f Grad" % eingezielt)
held.fokus = 0.0
held.zielt = True
held.feuert = False        # ein Schuss wuerde das Einzielen zuruecksetzen
for _ in range(int(K.WAFFEN["scharf"]["fokus_dauer"] / K.FIXED_DT) + 4):
    szene.welt.schritt(K.FIXED_DT)
pruef("Fokus laeuft in der angegebenen Zeit voll", held.fokus >= 0.999,
      "%.2f" % held.fokus)
held.zielt = False
s = probe("scharf", 300, halten=("zweit",))
pruef("Scharfschuetze trifft eingezielt auf 300 px", s > 0, "%.0f Schaden" % s)

# Der eigentliche Punkt der Waffe: aus der Hueffte soll sie auf Entfernung
# unbrauchbar sein. Ein einzelner Schuss sagt dazu nichts, also zwoelf.
def trefferquote(einzielen, versuche=12):
    treffer = sum(1 for _ in range(versuche)
                  if probe("scharf", 300, dauer=0.9,
                           halten=("zweit",) if einzielen else ()) > 0)
    return treffer / float(versuche)

aus_der_hueffte = trefferquote(False)
eingezielt_quote = trefferquote(True)
pruef("Aus der Hueffte geht auf 300 px das meiste daneben",
      aus_der_hueffte <= 0.4, "%.0f%% Treffer" % (aus_der_hueffte * 100))
pruef("Eingezielt sitzt praktisch jeder Schuss",
      eingezielt_quote >= 0.9, "%.0f%% Treffer" % (eingezielt_quote * 100))

# Medkits
held.waffe = 0
held.leben = 40.0
held.medkits = 1
held.heilt_rest = 0.0
pruef("Medkit geht los", held.heilen())
pruef("Ohne Vorrat geht keins los", not held.heilen())
sim(K.MEDKIT["dauer"] + 0.3)
pruef("Medkit heilt", held.leben > 40.0, "%.0f Leben" % held.leben)
held.leben = held.max_leben
held.medkits = 1
held.heilt_rest = 0.0
pruef("Bei vollem Leben bleibt es liegen", not held.heilen())

# Neue Wesen landen erst beim naechsten Schritt in welt.wesen, bis dahin
# stehen sie in welt.neue. Also beide zaehlen.
def medkits_im_feld():
    return sum(1 for w in list(szene.welt.wesen) + list(szene.welt.neue)
               if getattr(w, "art", None) == "medkit")

vor_welle = medkits_im_feld()
szene.welle_starten()
nach_welle = medkits_im_feld()
pruef("Jede Welle legt Medkits aus", nach_welle > vor_welle,
      "%d -> %d" % (vor_welle, nach_welle))

# Ziellinie
held.tracer = held.tracer_weit = False
held.tracer = True
pruef("Ziellinie laesst sich einschalten", held.tracer)
held.waffe = 0

# Kollision: gegen die Wand laufen
held.pos.update(3*K.TILE, 3*K.TILE)
sim(1.5, halten={"links", "vor"})
pruef("bleibt in der Karte", szene.welt.frei(held.pos, held.radius, held.ebene))

# Ebenenwechsel ueber die Treppe
held.pos.update(22*K.TILE+16, 12*K.TILE+16)
held.ebene = 0
ziel = szene.welt.treppe_unter(held)
pruef("steht auf der Treppe", ziel == 1)
pruef("Wechsel klappt", szene.welt.ebene_wechseln(held, 1))
pruef("jetzt auf Ebene 1", held.ebene == 1)
sim(0.6)
bild("spiel_2_ebene1.png")
zurueck = szene.welt.treppe_unter(held)
pruef("Rueckweg vorhanden", zurueck == 0)

# Loch in Ebene 1: Ebene 0 scheint durch
e1 = szene.welt.ebene(1)
pruef("Ebene 1 hat Loecher", any(k == K.LEER for k in e1.kacheln[e1.breite:-e1.breite]))

# ── Sturz: nichts darf springen ──────────────────────────────────────
# Der Sturz ist die eine Stelle, an der sich 2D wie Tiefe anfuehlen muss.
# Frueher sprang die Figur beim Absprung um die volle Fallhoehe nach oben
# und schrumpfte auf den Massstab der Zielebene zusammen. Gemessen wird
# deshalb nicht der Zustand, sondern die Bildposition von Schritt zu
# Schritt: ein Teleport zeigt sich dort als grosser Sprung.

def bildpunkt_der_figur():
    """Wo die Figur im Bild sitzt - dieselbe Rechnung wie im Renderer.

    Das Kameraruckeln bleibt aussen vor: das ist gewolltes Feedback beim
    Aufschlag und haette mit der Sturzbewegung nichts zu tun.
    """
    pp = K.PERSPEKTIVE
    dz = szene.blick_hoehe - (szene.welt.hoehe(held.ebene) + held.flug)
    k = pp["brennweite"] / max(60.0, pp["brennweite"] + dz)
    m = szene.kamera.pos
    return pygame.Vector2(K.GAME_W / 2 + (held.pos.x - m.x) * k,
                          K.GAME_H / 2 + (held.pos.y - m.y) * k), k

def absprungstellen(grenze=8):
    """Feste Stellen auf Ebene 2, zwei Kacheln neben einem Loch."""
    eo = szene.welt.ebene(2)
    raus = []
    for ty in range(6, eo.hoehe - 6):
        for tx in range(10, eo.breite - 10):
            if eo.loch(tx, ty) and not eo.loch(tx - 2, ty):
                p = pygame.Vector2((tx - 2) * K.TILE + 16, ty * K.TILE + 16)
                if szene.welt.frei(p, held.radius, 2):
                    raus.append(p)
                    if len(raus) >= grenze:
                        return raus
    return raus

def sturz_messen(start):
    """Laeuft von start nach rechts ins Loch. Gibt den groessten Sprung
    der Bildposition zurueck, dazu ob ueberhaupt gefallen wurde."""
    held.ebene = 2
    held.pos.update(start); held.vorher.update(start)
    held.leben = held.max_leben; held.tempo.update(0, 0)
    held.unverwundbar = 999.0
    szene.blick = 2; szene._letzte_ebene = 2
    szene.blick_hoehe = float(szene.welt.hoehe(2))
    for _ in range(150):                     # Kamera zur Ruhe kommen lassen
        e.neues_bild(); e._gehalten = set(); szene.schritt(K.FIXED_DT)
    if held.ebene != 2:
        return 0.0, False
    vorige, _ = bildpunkt_der_figur()
    groesster, gefallen = 0.0, False
    for _ in range(320):
        e.neues_bild()
        e._gehalten = ({"rechts"} if held.ebene == 2 and held.sturz_rest <= 0
                       else set())
        szene.schritt(K.FIXED_DT)
        jetzt, _k = bildpunkt_der_figur()
        if gefallen or held.sturz_rest > 0:
            groesster = max(groesster, jetzt.distance_to(vorige))
        if held.sturz_rest > 0:
            gefallen = True
        vorige = jetzt
    return groesster, gefallen

stellen = absprungstellen()
pruef("Absprungstellen gefunden", len(stellen) >= 3, "%d" % len(stellen))
spruenge = []
for stelle in stellen:
    gross, gefallen = sturz_messen(stelle)
    if gefallen:
        spruenge.append(gross)
pruef("Es wurde wirklich gestuerzt", len(spruenge) >= 3, "%d Stuerze" % len(spruenge))
# Ein Bild bei 120 Hz traegt hoechstens ein paar Pixel Bewegung. Alles
# darueber waere ein Sprung, kein Fallen.
schlimmster = max(spruenge) if spruenge else 0.0
pruef("Kein Sprung der Bildposition im Sturz", schlimmster < 8.0,
      "schlimmster %.2f px" % schlimmster)
held.unverwundbar = 0.0
held.ebene = 0
held.pos.update(freies_feld()); held.vorher.update(held.pos)
held.leben = held.max_leben
szene.blick = 0; szene._letzte_ebene = 0
szene.blick_hoehe = 0.0
sim(0.4)

# ── Steuerung in der Luft ────────────────────────────────────────────
# Waehrend eines Sturzes behaelt man einen Teil der Bewegung (K.STURZ
# ["luftsteuerung"]). Das ist spaeter Spielmechanik, also wird es gemessen
# und nicht geglaubt: quer zur Fallrichtung ziehen, mit und ohne Taste.

def sturz_quer(tasten, start):
    """Laeuft ins Loch und haelt waehrend des Fluges 'tasten'.
    Gibt zurueck, wie weit sich die Figur im Flug quer bewegt hat."""
    held.ebene = 2
    held.pos.update(start); held.vorher.update(start)
    held.leben = held.max_leben; held.tempo.update(0, 0)
    held.unverwundbar = 999.0
    szene.blick = 2; szene._letzte_ebene = 2
    szene.blick_hoehe = float(szene.welt.hoehe(2))
    for _ in range(150):
        e.neues_bild(); e._gehalten = set(); szene.schritt(K.FIXED_DT)
    if held.ebene != 2:
        return None
    beim_absprung = None
    for _ in range(320):
        e.neues_bild()
        if held.ebene == 2 and held.sturz_rest <= 0:
            e._gehalten = {"rechts"}              # ins Loch laufen
        elif held.sturz_rest > 0:
            e._gehalten = set(tasten)             # im Flug steuern
            if beim_absprung is None:
                beim_absprung = pygame.Vector2(held.pos)
        else:
            e._gehalten = set()
        war = held.sturz_rest
        szene.schritt(K.FIXED_DT)
        if war > 0 >= held.sturz_rest and beim_absprung is not None:
            return held.pos - beim_absprung
    return None

quer_ohne, quer_mit = [], []
for stelle in stellen[:4]:
    a = sturz_quer((), stelle)
    b = sturz_quer(("zurueck",), stelle)
    if a is not None and b is not None:
        quer_ohne.append(abs(a.y)); quer_mit.append(abs(b.y))
pruef("Stuerze zum Messen der Luftsteuerung", len(quer_mit) >= 2,
      "%d" % len(quer_mit))
if quer_mit:
    schub = sum(quer_mit) / max(0.5, sum(quer_ohne))
    pruef("Im Sturz laesst sich die Figur steuern",
          min(quer_mit) > 4.0 and schub > 2.0,
          "mit Taste %.1f px, ohne %.1f px, also %.1f mal so weit"
          % (max(quer_mit), max(quer_ohne), schub))
    pruef("Aber langsamer als am Boden",
          K.STURZ["luftsteuerung"] < 1.0,
          "%.0f Prozent" % (K.STURZ["luftsteuerung"] * 100))

# Steht unter dem Loch etwas im Weg, rutscht die Figur dorthin ab. Das darf
# die Steuerung nur so lange ueberstimmen, wie es noeitg ist: sobald sie auf
# freiem Grund haengt, gehoert die Bewegung wieder dem Spieler.
if stellen:
    held.ebene = 2
    held.pos.update(stellen[0]); held.vorher.update(stellen[0])
    held.unverwundbar = 999.0
    szene.blick = 2; szene._letzte_ebene = 2
    szene.blick_hoehe = float(szene.welt.hoehe(2))
    for _ in range(150):
        e.neues_bild(); e._gehalten = set(); szene.schritt(K.FIXED_DT)
    for _ in range(320):
        e.neues_bild()
        e._gehalten = {"rechts"} if held.sturz_rest <= 0 else set()
        szene.schritt(K.FIXED_DT)
        if held.sturz_rest > 0:
            break
    if held.sturz_rest > 0:
        # Ein Ausweichplatz, obwohl hier gar keiner noetig ist
        held.sturz_ziel = pygame.Vector2(held.pos) + pygame.Vector2(60, 0)
        e.neues_bild(); e._gehalten = set(); szene.schritt(K.FIXED_DT)
        pruef("Auf freiem Grund endet das Abrutschen sofort",
              held.sturz_ziel is None)
held.unverwundbar = 0.0
held.ebene = 0
held.pos.update(freies_feld()); held.vorher.update(held.pos)
held.leben = held.max_leben
szene.blick = 0; szene._letzte_ebene = 0; szene.blick_hoehe = 0.0
sim(0.3)

# ── Handlungen sperren sich nicht gegenseitig ────────────────────────
held.waffe = held.waffen.index("repetierer")
held.magazin["repetierer"] = 0
held.nachladen()
pruef("Nachladen laeuft an", held.nachlade_rest > 0)
held.waffe_waehlen(held.waffen.index("schrot"))
pruef("Waffenwechsel bricht das Nachladen ab", held.nachlade_rest == 0.0)
pruef("und die Waffe ist wirklich gewechselt", held.waffe_name == "schrot")

held.waffe_waehlen(held.waffen.index("repetierer"))
held.nachladen()
held.leben = 40.0; held.medkits = 1; held.heilt_rest = 0.0
pruef("Medkit geht auch mitten im Nachladen los", held.heilen())
pruef("und das Nachladen laeuft dabei weiter", held.nachlade_rest > 0)
# So lange, bis beides durch sein muss - das Medkit ist schneller fertig
# als das Nachladen, gewartet wird auf den laengeren der beiden.
sim(max(K.MEDKIT["dauer"], K.WAFFEN["repetierer"]["nachladen"]) + 0.3)
pruef("Beides wird fertig", held.leben > 40.0 and held.magazin["repetierer"] > 0,
      "%.0f Leben, %d Schuss" % (held.leben, held.magazin["repetierer"]))

# Nachladen im Sturz: frueher stand die Zeit in der Luft still
held.ebene = 2
stelle = absprungstellen(1)
if stelle:
    held.pos.update(stelle[0]); held.vorher.update(stelle[0])
    held.unverwundbar = 999.0
    szene.blick = 2; szene._letzte_ebene = 2
    szene.blick_hoehe = float(szene.welt.hoehe(2))
    for _ in range(60):
        e.neues_bild(); e._gehalten = set(); szene.schritt(K.FIXED_DT)
    held.magazin["repetierer"] = 0
    held.waffe = held.waffen.index("repetierer")
    held.nachladen()
    vorrat = held.nachlade_rest
    for _ in range(40):
        e.neues_bild(); e._gehalten = {"rechts"}; szene.schritt(K.FIXED_DT)
        if held.sturz_rest > 0:
            break
    im_sturz = held.nachlade_rest
    for _ in range(30):
        e.neues_bild(); e._gehalten = set(); szene.schritt(K.FIXED_DT)
    pruef("Nachladen laeuft auch im Sturz weiter", held.nachlade_rest < im_sturz
          or held.magazin["repetierer"] > 0,
          "%.2f -> %.2f" % (vorrat, held.nachlade_rest))
held.unverwundbar = 0.0
held.ebene = 0
held.pos.update(freies_feld()); held.vorher.update(held.pos)
held.leben = held.max_leben
szene.blick = 0; szene._letzte_ebene = 0; szene.blick_hoehe = 0.0
sim(0.3)

# ── Die Figur zeigt, was sie traegt ──────────────────────────────────
gesehen = set()
for i, name in enumerate(held.waffen):
    held.waffe = i
    gesehen.add(held.bild)
    pruef("Figur fuer %s vorhanden" % name.upper(),
          held.bild in K.BILD_MASS and held.bild != "spieler",
          held.bild)
pruef("Jede Waffe hat ihre eigene Figur", len(gesehen) == len(held.waffen),
      "%d Figuren fuer %d Waffen" % (len(gesehen), len(held.waffen)))
held.waffe = 0

# Gegner draufwerfen und Tempo messen
from dustfront.entities import Gegner
from dustfront.world import freier_punkt
for _ in range(40):
    szene.welt.dazu(Gegner(freier_punkt(szene.welt, held.ebene, szene.rnd), "laeufer", held.ebene))
sim(0.5)
t0 = time.time(); n = 240
for i in range(n):
    szene.schritt(K.FIXED_DT)
sim_ms = (time.time()-t0)/n*1000
t0 = time.time()
for i in range(120):
    app.flaeche.fill(K.C_VOID); szene.zeichnen(app.flaeche, 0.5)
zeichen_ms = (time.time()-t0)/120*1000
print("  Simulation %.2f ms/Schritt, Zeichnen %.2f ms/Bild (%d Wesen, %d Partikel)"
      % (sim_ms, zeichen_ms, len(szene.welt.wesen), len(szene.welt.partikel)))
bild("spiel_3_masse.png")

# Tod und Neustart
held.leben = 1
held.unverwundbar = 0
held.schaden(50)
pruef("Tod erkannt", not held.lebt)
sim(1.5)
bild("spiel_4_tod.png")

# ── Aussenhaut: Dateien statt Platzhalter ────────────────────────────
# Das Versprechen lautet: eine Datei assets/<name>.png ersetzt das im Code
# gezeichnete Bild, ohne dass eine Zeile Code geaendert wird. Geprueft wird
# genau das, in einem Wegwerfordner, mit echten Dateien auf der Platte.
import shutil, tempfile, wave
from pathlib import Path
from dustfront.core import Bilder, _PLATZHALTER
from dustfront.audio import Klaenge

print()
GRUEN = (0, 255, 0, 255)

# Die Tabelle und die Zeichner muessen sich decken, sonst laedt jemand eine
# Datei auf ein Mass, das es gar nicht gibt.
fehlt_tabelle = [n for n in _PLATZHALTER if n not in K.BILD_MASS]
fehlt_zeichner = [n for n in K.BILD_MASS if n not in _PLATZHALTER]
pruef("Jeder Platzhalter steht in BILD_MASS", not fehlt_tabelle,
      ", ".join(fehlt_tabelle))
pruef("Jeder Eintrag in BILD_MASS hat einen Zeichner", not fehlt_zeichner,
      ", ".join(fehlt_zeichner))

roh = Bilder(None)
schief = ["%s: %s statt %s" % (n, roh.platzhalter(n).get_size(), K.BILD_MASS[n])
          for n in K.BILD_MASS if roh.platzhalter(n).get_size() != tuple(K.BILD_MASS[n])]
pruef("Jeder Platzhalter hat sein Sollmass", not schief, ", ".join(schief))

# Alles, was die Inhalte-Tabellen verlangen, muss es auch geben.
gebraucht = ([d["bild"] for d in K.KACHELN.values()]
             + [d["bild"] for d in K.GEGNER.values()]
             + ["waffe_" + w for w in K.WAFFEN]
             + ["spieler", "geschoss", "muendung", "medkit", "granate", "huelse"])
unbekannt = sorted({n for n in gebraucht if n not in K.BILD_MASS})
pruef("Alle im Spiel verlangten Bilder sind bekannt", not unbekannt,
      ", ".join(unbekannt))

weg = Path(tempfile.mkdtemp(prefix="dustfront_haut_"))
try:
    def gruene_datei(pfad, groesse):
        s = pygame.Surface(groesse, pygame.SRCALPHA)
        s.fill(GRUEN)
        pygame.image.save(s, str(pfad))

    # 1. Richtiges Mass: die Datei kommt Pixel fuer Pixel so an, wie sie ist.
    gruene_datei(weg / "wand.png", (K.TILE, K.TILE))
    # 2. Falsches Mass: wird auf das Sollmass gebracht, statt die Karte zu
    #    zerreissen.
    gruene_datei(weg / "boden.png", (K.TILE * 2, K.TILE * 2))
    # 3. Andere Endung: .bmp wird genauso genommen.
    gruene_datei(weg / "kiste.bmp", (K.TILE, K.TILE))
    # 4. Reihenfolge: .png gewinnt gegen .bmp beim selben Namen.
    gruene_datei(weg / "gitter.png", (K.TILE, K.TILE))
    (weg / "gitter.bmp").write_bytes(b"kein bild")
    # 5. Kaputte Datei: kostet den Platzhalter nicht.
    (weg / "luke.png").write_bytes(b"das ist kein PNG")

    b = Bilder(weg)
    w = b.bild("wand")
    pruef("Datei ersetzt den Platzhalter",
          w.get_at((5, 5)) == GRUEN and "wand" in b.aus_datei)
    pruef("Datei behaelt ihr Mass", w.get_size() == (K.TILE, K.TILE))

    bo = b.bild("boden")
    pruef("Zu grosse Datei wird auf das Sollmass gebracht",
          bo.get_size() == (K.TILE, K.TILE), str(bo.get_size()))
    pruef("und bleibt dabei die Datei", bo.get_at((5, 5)) == GRUEN)

    pruef("Auch .bmp wird genommen", b.bild("kiste").get_at((5, 5)) == GRUEN)
    pruef("Bei zwei Endungen gewinnt .png",
          b.bild("gitter").get_at((5, 5)) == GRUEN and not b.fehler)

    lu = b.bild("luke")
    pruef("Kaputte Datei faellt auf den Platzhalter zurueck",
          lu.get_at((5, 5)) != GRUEN and lu.get_size() == (K.TILE, K.TILE))
    pruef("und wird als Fehler vermerkt", any("luke" in f for f in b.fehler))

    # Ohne Ordner bleibt alles beim Alten: das ist der Zustand im Repo.
    ohne = Bilder(None)
    pruef("Ohne assets-Ordner kommt alles aus dem Code",
          not ohne.aus_datei and ohne.bild("wand").get_at((5, 5)) != GRUEN)

    # Drehen und Zwischenspeichern muessen mit der Datei genauso gehen.
    pruef("Gedrehte Fassung einer Datei klappt",
          b.gedreht("wand", 90).get_size() == (K.TILE, K.TILE))
    b.vergessen()
    pruef("Nach vergessen() wird neu geladen",
          not b.aus_datei and b.bild("wand").get_at((5, 5)) == GRUEN)

    # ── Dekale: Bilder ohne festes Mass ──────────────────────────────
    # Schatten, Blut und Brandfleck richten sich nach dem, was sie wirft.
    # Geprueft wird, dass sie aus ihrem Basismass wirklich mitwachsen und
    # dass eine Datei auch hier durchschlaegt.
    r = szene.renderer
    klein = r.schatten(K.SPIELER["radius"])
    gross = r.schatten(K.GEGNER["brecher"]["radius"])
    pruef("Schatten waechst mit dem Koerper", gross.get_width() > klein.get_width(),
          "%d gegen %d" % (klein.get_width(), gross.get_width()))
    pruef("In der Luft schrumpft er",
          r.schatten(K.SPIELER["radius"], 0.4).get_width() < klein.get_width())
    pruef("Blutfleck waechst mit dem Wesen",
          r.blutfleck(K.GEGNER["brecher"]["radius"]).get_width()
          > r.blutfleck(K.GEGNER["laeufer"]["radius"]).get_width())
    pruef("Brandfleck trifft im Wirkungskreis sein Basismass",
          r.brandfleck(K.DEKAL["brand_radius"]).get_size()
          == tuple(K.BILD_MASS["brandfleck"]), str(r.brandfleck(78.0).get_size()))
    pruef("Kleinere Sprengung, kleinerer Fleck",
          r.brandfleck(30.0).get_width() < r.brandfleck(78.0).get_width())

    # Auch die bildschirmgrossen kommen aus der Registratur.
    gruene_datei(weg / "vignette.png", (K.GAME_W, K.GAME_H))
    gruene_datei(weg / "schatten.png", K.BILD_MASS["schatten"])
    b2 = Bilder(weg)
    pruef("Vignette laesst sich durch eine Datei ersetzen",
          b2.bild("vignette").get_at((5, 5)) == GRUEN
          and b2.bild("vignette").get_size() == (K.GAME_W, K.GAME_H))
    from dustfront.render import Renderer
    r2 = Renderer(b2)
    pruef("Der Renderer nimmt die Dateifassung",
          r2.schatten(K.SPIELER["radius"]).get_at((5, 5))[1] > 200)

    # ── Klaenge ──────────────────────────────────────────────────────
    sfx = weg / K.ASSETS["sfx"]
    sfx.mkdir()
    with wave.open(str(sfx / "nahkampf.wav"), "wb") as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(44100)
        f.writeframes(b"\x00\x40" * 4410 * 2)
    kl = Klaenge(weg)
    if kl.ok:
        kl.klang("nahkampf")
        pruef("Klang kommt aus der Datei", "nahkampf" in kl.aus_datei)
        kl.klang("schuss_repetierer")
        pruef("Ohne Datei kommt der Klang aus dem Code",
              "schuss_repetierer" not in kl.aus_datei
              and len(kl.klang("schuss_repetierer")) > 0)
        alle = [n for n in K.KLANG_NAMEN if not kl.klang(n)]
        pruef("Jeder Name in KLANG_NAMEN gibt einen Klang", not alle,
              ", ".join(alle))
    else:
        print("  --    Mixer nicht verfuegbar, Klangproben uebersprungen")

    # ── Vorlagen ─────────────────────────────────────────────────────
    from dustfront.vorlagen import schreiben, namen
    ordner = weg / "vorlagen"
    anzahl = schreiben(ordner, melden=False)
    pruef("Vorlagen werden geschrieben", anzahl == len(K.BILD_MASS),
          "%d Stueck" % anzahl)
    lueckenhaft = [n for n in namen() if not (ordner / (n + ".png")).is_file()]
    pruef("Zu jedem Namen liegt eine Vorlage", not lueckenhaft,
          ", ".join(lueckenhaft))
    pruef("Uebersichtstafel entsteht", (ordner / "_uebersicht.png").is_file())
    # Die Vorlage muss zurueckgelesen genau das Sollmass haben, sonst taugt
    # sie nicht als Malvorlage.
    probe_bild = pygame.image.load(str(ordner / "spieler.png"))
    pruef("Vorlage hat das Sollmass",
          probe_bild.get_size() == tuple(K.BILD_MASS["spieler"]),
          str(probe_bild.get_size()))
finally:
    shutil.rmtree(weg, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════
# M1: Karten aus Dateien
# ══════════════════════════════════════════════════════════════════

print()
print("-- Karten aus Dateien " + "-" * 40)

from dustfront.karten import alle, lesen, pruefen, pruefen_welt, aus_text, KartenFehler
from dustfront.world import Welt, hoehen_staffel, testkarte

karten = alle()
pruef("Karten liegen im Ordner", len(karten) >= 4, "%d Stueck" % len(karten))

# Jede Karte muss laden und beide Pruefer bestehen. Das ist die eigentliche
# Zusage von M1: ein neuer Ort ist eine Textdatei, und wenn sie falsch ist,
# sagt es der Testlauf und nicht der Spieler.
schlecht = []
welten = {}
for name in karten:
    try:
        k = lesen(name)
        w = Welt.aus_karte(k)
        welten[name] = w
        f = pruefen(k) + pruefen_welt(w)
        if f:
            schlecht.append("%s: %s" % (name, f[0]))
    except KartenFehler as fehler:
        schlecht.append("%s: %s" % (name, fehler))
pruef("Jede Karte laedt und ist baulich in Ordnung", not schlecht,
      " | ".join(schlecht))

# Marken: der Spieler faengt da an, wo es in der Karte steht. Verlangt wird
# das von Orten - ein Rumpf ist kein Ort, in den man hineingeboren wird.
orte = [n for n in karten if lesen(n).text("art", "ort") == "ort"]
ohne_start = [n for n in orte if welten[n].marke("start") is None]
pruef("Jeder Ort hat eine Startmarke", not ohne_start, ", ".join(ohne_start))
pruef("Spiel startet auf der Marke, nicht auf einem Zufallspunkt",
      szene.welt.marke("start") is not None)

# Exaktes Uebernehmen: die Datei muss Kachel fuer Kachel dieselbe Karte
# ergeben wie die eingebaute. Sonst hat der Umzug etwas verschluckt.
alt_welt = testkarte()
neu_welt = welten.get("probehalle")
pruef("Probehalle ist Kachel fuer Kachel die alte Testkarte",
      neu_welt is not None
      and len(neu_welt.ebenen) == len(alt_welt.ebenen)
      and all(a.kacheln == b.kacheln
              for a, b in zip(alt_welt.ebenen, neu_welt.ebenen)))

# Loecher am Zeilenende sind Karte, keine Leerzeilen. Daran ist der Leser
# schon einmal gescheitert, und der Rumpf hat dabei seine Form verloren.
form = aus_text("grund: deck\n\n--- ebene 0 ---\n  ###  \n #...# \n  ###  \n")
pruef("Zeilen aus lauter Loechern bleiben erhalten",
      len(form.bloecke[0]) == 3 and form.bloecke[0][0].startswith("  "))

# Kaputte Karten fliegen mit einer Meldung, nicht mit einem Absturz.
try:
    aus_text("das ist kein kopf\n--- ebene 0 ---\n##\n")
    gemeldet = False
except KartenFehler:
    gemeldet = True
pruef("Ein kaputter Kopf wird gemeldet", gemeldet)

# Hoehenstaffel: die erzeugte muss die von Hand gesetzte treffen.
staffel = hoehen_staffel(4)
abweichung = max(abs(a - b) for a, b in zip(staffel, K.EBENEN_HOEHE))
pruef("Erzeugte Hoehenstaffel trifft die alte Tabelle", abweichung <= 1.5,
      "groesste Abweichung %.1f px" % abweichung)
tief = hoehen_staffel(10, mit_boden=False)
pruef("Auch zehn Decks ergeben eine steigende Staffel",
      len(tief) == 10 and all(b > a for a, b in zip(tief, tief[1:])))

# ══════════════════════════════════════════════════════════════════
# Das Beinwerk: die Bewegung kommt aus den Beinen
# ══════════════════════════════════════════════════════════════════

print()
print("-- Der Wandler " + "-" * 47)

from dustfront.wandler import Wandler, bauplan

def laufen(w, sekunden, schub=1.0, lenkung=0.0):
    """Laesst laufen und gibt das wirklich gefahrene Tempo zurueck."""
    w.steuern(schub, lenkung)
    start = pygame.Vector2(w.pos)
    for _ in range(int(sekunden / K.FIXED_DT)):
        w.schritt(K.FIXED_DT)
    return w.pos.distance_to(start) / sekunden

plaene = {}
for klasse in ("warhound", "reaver", "imperator"):
    plaene[klasse] = bauplan(klasse)
pruef("Alle drei Bauplaene laden",
      len(plaene) == 3 and all(p.beine for p in plaene.values()))

# Gangarten leiten sich aus der Bauart ab, ohne Tabelle je Beinzahl.
gruppen = {}
for klasse, plan in plaene.items():
    w = Wandler(plan, (3000, 3000))
    gruppen[klasse] = [b.gruppe for b in w.beine]
pruef("Zwei Beine gehen im Wechselschritt",
      sorted(gruppen["warhound"]) == [0, 1])
pruef("Vier Beine gehen im Kreuzgang",
      gruppen["reaver"].count(0) == 2 and gruppen["reaver"].count(1) == 2
      and gruppen["reaver"][0] != gruppen["reaver"][1]
      and gruppen["reaver"][0] != gruppen["reaver"][2])
pruef("Sechs Beine gehen im Dreifuss",
      gruppen["imperator"].count(0) == 3 and gruppen["imperator"].count(1) == 3)

# Der Kern des Modells: ein stehender Fuss ist in der Welt verankert und
# bewegt sich **nicht**. Rutscht er, ist die ganze Ursachenkette dahin.
w = Wandler(plaene["reaver"], (3000, 3000))
w.steuern(1.0, 0.0)
vorher = [pygame.Vector2(b.fuss) for b in w.beine]
stand = [b.steht for b in w.beine]
groesstes = 0.0
for _ in range(int(8.0 / K.FIXED_DT)):
    w.schritt(K.FIXED_DT)
    for i, b in enumerate(w.beine):
        if stand[i] and b.steht:
            groesstes = max(groesstes, b.fuss.distance_to(vorher[i]))
        vorher[i].update(b.fuss)
        stand[i] = b.steht
pruef("Ein stehender Fuss rutscht nie", groesstes < 1e-9,
      "groesste Bewegung %.9f px" % groesstes)

# Stillstand ist Stillstand: keine Drift, kein Zittern.
w = Wandler(plaene["reaver"], (3000, 3000))
start = pygame.Vector2(w.pos)
w.steuern(0.0, 0.0)
for _ in range(int(6.0 / K.FIXED_DT)):
    w.schritt(K.FIXED_DT)
pruef("Im Stand wandert der Rumpf nicht", w.pos.distance_to(start) < 0.5,
      "%.4f px in 6 s" % w.pos.distance_to(start))

# Tempo ist ein Ergebnis, kein Sollwert - es muss trotzdem herauskommen.
schief = []
for klasse, plan in plaene.items():
    for schub in (1.0, 0.5):
        w = Wandler(plan, (3000, 3000))
        laufen(w, 4.0, schub)                    # einschwingen
        v = laufen(w, 8.0, schub)
        soll = plan.tempo * schub
        if abs(v - soll) / soll > 0.12:
            schief.append("%s bei %.0f%%: %.0f statt %.0f"
                          % (klasse, schub * 100, v, soll))
pruef("Die Beine liefern das befohlene Tempo", not schief, " | ".join(schief))

# Beinverlust wirkt, ohne dass irgendwo ein Sonderfall steht.
w = Wandler(plaene["reaver"], (3000, 3000))
laufen(w, 4.0)
ganz = laufen(w, 6.0)
w.bein_verlieren(0)
w.bein_verlieren(1)
laufen(w, 4.0)
angeschlagen = laufen(w, 6.0)
pruef("Mit halben Beinen wankt der Rumpf", w.gangwerk.wank > 1.0,
      "%.2f Grad" % w.gangwerk.wank)
pruef("Mit halben Beinen laeuft er nicht schneller", angeschlagen <= ganz + 1.0,
      "%.0f gegen %.0f px/s" % (angeschlagen, ganz))

# Der Grenzfall: ein einziges Bein kann nicht tragen und treten zugleich.
w = Wandler(plaene["warhound"], (3000, 3000))
w.bein_verlieren(0)
gestrandet = laufen(w, 8.0)
pruef("Mit einem Bein geht gar nichts mehr", gestrandet < 1.0,
      "%.2f px/s" % gestrandet)
pruef("Und die Maschine sagt es", not w.fahrbereit)
pruef("Reparatur bringt sie zurueck",
      w.bein_richten(0) and w.fahrbereit and laufen(w, 6.0) > 20.0)

# Drehen auf der Stelle. Wer genug Beine hat, dreht sauber; wer zwei hat,
# schlurft dabei - und das ist keine Schwaeche des Modells, sondern seine
# Aussage: mit zwei Beinen steht beim Drehen genau ein Fuss, und ein
# einzelner Fuss legt keine Drehung fest. Ein Warhound muss sich
# herumtreten, ein Reaver dreht auf dem Absatz.
drift = {}
for klasse in ("warhound", "reaver", "imperator"):
    w = Wandler(plaene[klasse], (3000, 3000))
    start, kurs0 = pygame.Vector2(w.pos), w.kurs
    laufen(w, 6.0, schub=0.0, lenkung=1.0)
    drift[klasse] = (abs(w.kurs - kurs0), w.pos.distance_to(start))
pruef("Jede Maschine dreht auf der Stelle",
      all(d[0] > 45.0 for d in drift.values()),
      " ".join("%s %.0f Grad" % (k, d[0]) for k, d in drift.items()))
pruef("Mit vier und mehr Beinen bleibt sie dabei stehen",
      drift["reaver"][1] < 45.0 and drift["imperator"][1] < 45.0,
      "Reaver %.0f px, Imperator %.0f px"
      % (drift["reaver"][1], drift["imperator"][1]))
pruef("Mit zwei Beinen schlurft sie dabei",
      drift["warhound"][1] > drift["reaver"][1] * 2,
      "Warhound %.0f px" % drift["warhound"][1])

# Der Rumpf ist eine ganz normale Welt: begehbar, mit Treppen und Stationen.
w = Wandler(plaene["imperator"], (3000, 3000))
pruef("Der Rumpf hat so viele Decks wie die Datei",
      len(w.welt.ebenen) == plaene["imperator"].decks)
st = w.stationen()
pruef("Der Rumpf hat Stationen", len(st) >= 4, ", ".join(sorted(st)))
pruef("Jede Station steht auf einer begehbaren Kachel",
      all(w.welt.ebene(deck).begehbar(int(p.x // K.TILE), int(p.y // K.TILE))
          for deck, p in st.values()))

# Hin und her rechnen zwischen Rumpf und Welt muss sich schliessen.
w.gangwerk.kurs = 37.0
probe = pygame.Vector2(120, 88)
zurueck = w.nach_rumpf(w.nach_welt(probe))
pruef("Umrechnen Rumpf zu Welt und zurueck trifft wieder denselben Punkt",
      probe.distance_to(zurueck) < 0.01,
      "%.5f px Abweichung" % probe.distance_to(zurueck))

# Und die Maschine muss sich zeichnen lassen, ohne zu stolpern.
from dustfront.render import Kamera as ProbeKamera
probe_boden = welten.get("wasteland") or testkarte()
probe_kamera = ProbeKamera(sicht=(K.GAME_W * 2, K.GAME_H * 2))
probe_flaeche = pygame.Surface((K.GAME_W * 2, K.GAME_H * 2))
gemalt = True
try:
    for klasse, plan in plaene.items():
        wz = Wandler(plan, (1100, 700))
        laufen(wz, 3.0)
        probe_kamera.pos.update(wz.pos)
        szene.renderer.welt_zeichnen(probe_flaeche, probe_boden, probe_kamera,
                                     1.0, probe_boden.hoehe(0))
        szene.renderer.wandler_zeichnen(probe_flaeche, wz, probe_kamera)
except Exception as fehler:
    gemalt = False
    print("     ", type(fehler).__name__, fehler)
pruef("Alle drei Maschinen lassen sich zeichnen", gemalt)
pygame.image.save(probe_flaeche, "spiel_9_wandler.png")
print("gespeichert spiel_9_wandler.png")

print()
print("FEHLER:", fails or "keine")
pygame.quit()
