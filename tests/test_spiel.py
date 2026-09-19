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
szene = Spiel(app)
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
print()
print("FEHLER:", fails or "keine")
pygame.quit()
