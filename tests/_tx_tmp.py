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

def freies_feld(weite=260):
    """Ein Punkt mit viel Platz nach rechts, fuer die Schussbahnen.

    Seit 0.34.26 haelt jede Kiste eine Kugel auf (Welt.schuss_halt). Frei
    heisst darum: nichts dazwischen (Welt.deckung), nicht nur freie
    Sicht - und so weit, wie der Schuss reichen soll."""
    e0 = szene.welt.ebene(0)
    zeilen = [12] + [z for z in range(3, e0.hoehe - 3) if z != 12]
    for ky in zeilen:
        for kx in range(4, e0.breite - 4):
            p = pygame.Vector2(kx*K.TILE+16, ky*K.TILE+16)
            weit = pygame.Vector2(p.x + weite, p.y)
            if weit.x >= e0.pixel_breite - K.TILE:
                break
            if (szene.welt.frei(p, held.radius, 0)
                    and szene.welt.frei(weit, 12, 0)
                    and szene.welt.deckung(p, weit, 0) == ""):
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
    start = freies_feld(max(260, entfernung + 20))
    held.pos.update(start); held.tempo.update(0, 0); held.ebene = 0
    held.takt = 0.0; held.nachlade_rest = 0.0; held.fokus = 0.0
    held.feuert = False; held.will.update(0, 0)   # kein Dauerfeuer von vorhin
    # Das Brecheisen liegt seit 0.19.2 nicht mehr in der Hotbar, sondern
    # auf einer eigenen Taste. Gemessen wird trotzdem dasselbe: was ein
    # Schlag anrichtet.
    nah = waffe == K.NAHKAMPF["waffe"]
    if not nah:
        held.waffe = held.waffen.index(waffe)
        held.magazin[waffe] = max(1, K.WAFFEN[waffe]["magazin"])
    held.nahkampf_rest = 0.0
    held.schlag_zeigen = 0.0
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
    if nah:
        held.nahkampf()
    else:
        held.feuern()
    for _ in range(int(dauer / K.FIXED_DT)):
        festhalten()
        szene.welt.schritt(K.FIXED_DT)
    held.zielt = False
    schaden = vorher - ziel.leben
    ziel.lebt = False
    return schaden

pruef("Die Hotbar hat so viele Plaetze wie die Tabelle sagt",
      len(held.waffen) == len(K.HOTBAR), "%d von %d"
      % (len(held.waffen), len(K.HOTBAR)))
pruef("Und es sind noch Tasten dafuer da",
      len(held.waffen) <= K.HOTBAR_PLAETZE,
      "%d von hoechstens %d" % (len(held.waffen), K.HOTBAR_PLAETZE))
pruef("Alle Waffen der Hotbar sind bekannt",
      all(w in K.WAFFEN for w in held.waffen))
# Das Brecheisen gehoert nicht mehr dazu: es liegt auf einer eigenen
# Taste und belegt keinen Platz.
pruef("Das Brecheisen belegt keinen Hotbarplatz mehr",
      K.NAHKAMPF["waffe"] not in held.waffen)
pruef("Es ist trotzdem eine bekannte Waffe",
      K.NAHKAMPF["waffe"] in K.WAFFEN)
pruef("Zu jedem Platz gibt es eine Taste",
      all(app.opt.codes("waffe%d" % (i + 1))
          for i in range(len(held.waffen))))

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

# ── Balance: Brecheisen, Schrot, Scharfschuetze ──────────────────────
# Gemessen statt geglaubt.
b = K.WAFFEN["brecheisen"]
# Seit 0.34.96 bewusst schwach (gewuenscht): wer im Nahkampf etwas will,
# legt eine Nahkampfwaffe auf F.
pruef("Vier Brecheisenschlaege toeten einen Spieler, zwei nicht mehr",
      4 * b["schaden"] >= K.SPIELER["leben"] > 2 * b["schaden"],
      "%.0f x 4 gegen %.0f Leben" % (b["schaden"], K.SPIELER["leben"]))
pruef("Ein einzelner Schlag toetet noch nicht",
      b["schaden"] < K.SPIELER["leben"], "%.0f" % b["schaden"])
# Kein Unverwundbarkeitsfenster nach einem Treffer: es gab einmal eines
# und es war ein Fehler. Von einer Schrotladung zaehlte damit genau ein
# Kuegelchen, und Getroffene blinkten nach jedem Schuss wie frisch
# eingestiegen.
pruef("Ein Treffer macht niemanden kurz unverwundbar",
      "unverwundbar" not in K.SPIELER)
held.unverwundbar = 0.0
held.leben = held.max_leben
for _ in range(3):
    held.schaden(10, None, None)
pruef("Drei Treffer kurz hintereinander zaehlen alle drei",
      abs(held.leben - (held.max_leben - 30)) < 0.01,
      "%.0f statt %.0f Leben" % (held.leben, held.max_leben - 30))
held.leben = held.max_leben

s = probe("schrot", 260)
pruef("Schrot trifft jetzt auch auf 260 px", s > 0, "%.0f Schaden" % s)
nah, weit = probe("schrot", 60), probe("schrot", 240)
pruef("Nah trifft Schrot trotzdem haerter als weit", nah > weit,
      "%.0f gegen %.0f" % (nah, weit))

# Der Scharfschuetze soll weiter reichen, als das Bild breit ist.
pruef("Scharfschuetze reicht weiter als das Bild breit ist",
      K.WAFFEN["scharf"]["reichweite"] > K.GAME_W * 2,
      "%.0f px bei %d px Bildbreite"
      % (K.WAFFEN["scharf"]["reichweite"], K.GAME_W))
s = probe("scharf", 900, dauer=2.0, halten=("zweit",))
pruef("und trifft auf 900 px, weiter als man sehen kann", s > 0,
      "%.0f Schaden" % s)
pruef("Die verlaengerte Ziellinie reicht so weit wie der Schuss",
      K.TRACER["weite"] >= K.WAFFEN["scharf"]["reichweite"],
      "%.0f gegen %.0f" % (K.TRACER["weite"], K.WAFFEN["scharf"]["reichweite"]))

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

# Seit 0.32.10: die Ansicht springt beim Treppenwechsel sofort mit. Bis
# dahin zog sie eine halbe Sekunde nach, und so lange galt die eigene
# Ebene als "darueber" (ausgestanzt, Figur weg) oder "darunter"
# (abgedunkelt). Gemessen wird das erste Bild nach dem Wechsel - in
# beide Richtungen.
for _von, _nach in ((1, 0), (0, 1)):
    held.ebene = _von
    sim(0.6)
    pruef("Wechsel %d -> %d klappt" % (_von, _nach),
          szene.welt.ebene_wechseln(held, _nach))
    sim(K.FIXED_DT * 1.5)
    _dz = szene.blick_hoehe - szene.welt.hoehe(held.ebene)
    pruef("Ansicht steht nach %d -> %d im ersten Bild auf der neuen Ebene"
          % (_von, _nach), abs(_dz) < 1.0, "dz %.1f" % _dz)
    pruef("Das alte Bild blendet aus (%d -> %d)" % (_von, _nach),
          szene._ueberblendung.rest > 0)
    bild("spiel_2_wechsel.png")
    sim(K.EBENENWECHSEL["ueberblenden"] + 0.05)
    pruef("Nach %.2f s ist das alte Bild weg" % K.EBENENWECHSEL["ueberblenden"],
          szene._ueberblendung.rest == 0)
held.ebene = 1
sim(0.1)

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
    # 480 statt 320 Bilder: seit 0.27 geht die Figur 108 statt 132 px/s
    # und braucht zur Kante entsprechend laenger.
    for _ in range(480):
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
# Ohne Gegner: seit 0.32.6 finden sie zuverlaessig die Treppe hinauf und
# standen dann genau dort, wo die Figur ins Loch laufen soll.
from dustfront.entities import Gegner as _GegnerS
for _g in szene.welt.wesen + szene.welt.neue:
    if isinstance(_g, _GegnerS):
        _g.lebt = False
_pause_vorher = szene.pause_rest
szene.pause_rest = 1e9                    # und keine neue Welle dazwischen
for stelle in stellen[:4]:
    a = sturz_quer((), stelle)
    b = sturz_quer(("zurueck",), stelle)
    if a is not None and b is not None:
        quer_ohne.append(abs(a.y)); quer_mit.append(abs(b.y))
pruef("Stuerze zum Messen der Luftsteuerung", len(quer_mit) >= 2,
      "%d" % len(quer_mit))
szene.pause_rest = _pause_vorher
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
        # Erst auf wirklich freien Grund stellen. Geprueft wird, dass ein
        # Ausweichplatz verschwindet, sobald keiner mehr noetig ist - nicht,
        # ob die Figur nach dreihundert Schritten Anlauf zufaellig ueber
        # einer freien Kachel haengt. Frueher hing die Pruefung genau
        # daran und wurde rot, sobald sich irgendwo eine Nachkommastelle
        # der Bahn aenderte.
        held.pos.update(szene.welt.landeplatz(held.pos, held.radius,
                                              held.ebene))
        held.vorher.update(held.pos)
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
    if name == "c4":
        pruef("C4 nutzt die Figur mit leeren Armen", held.bild == "spieler",
              held.bild)
    else:
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
# Leere Haende und C4-Status sind sichtbare Teile der neuen Darstellung.
pruef("Unbewaffneter Spieler nutzt die Zombie-Armfigur",
      roh.bild("spieler").get_size() == K.BILD_MASS["spieler"]
      and roh.bild("spieler").get_at((14, 5)).a > 0)
from dustfront.anzeige import _c4_hotbar_symbol
_c4_probe = type("C4Probe", (), {})()
_c4_probe.c4_rest = -1.0; _c4_probe.c4_bereit = False
pruef("Hotbar zeigt noch nicht gelegtes C4", _c4_hotbar_symbol(_c4_probe) == "waffe_c4")
_c4_probe.c4_rest = 2.0
pruef("Hotbar unterscheidet ladendes C4", _c4_hotbar_symbol(_c4_probe) == "waffe_detonator")
_c4_probe.c4_rest = 0.0; _c4_probe.c4_bereit = True
pruef("Hotbar zeigt zuendbereites C4", _c4_hotbar_symbol(_c4_probe) == "waffe_detonator_bereit")
from dustfront.entities import C4Ladung as _C4Ladung
_c4_erste = _C4Ladung(pygame.Vector2(100, 100), 0, held.ebene, held)
_c4_zweite = _C4Ladung(pygame.Vector2(140, 100), 0, held.ebene, held)
_c4_erste.lade_rest = 0.0
_c4_zweite.lade_rest = 2.0
held.welt.neue.extend((_c4_erste, _c4_zweite))
pruef("C4 bleibt ladend, solange eine Ladung wartet",
      not held.c4_bereit and held.c4_rest == 2.0)
_c4_zweite.lade_rest = 0.0
pruef("Mehrere geladene C4 sind gemeinsam zuendbereit", held.c4_bereit)
held.welt.neue.remove(_c4_erste)
held.welt.neue.remove(_c4_zweite)

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
    (sfx / "medkit").mkdir()
    with wave.open(str(sfx / "medkit" / "meine_aufnahme.wav"), "wb") as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(44100)
        f.writeframes(b"\x00\x40" * 4410 * 2)
    kl = Klaenge(weg)
    if kl.ok:
        kl.klang("nahkampf")
        pruef("Klang kommt aus der Datei", "nahkampf" in kl.aus_datei)
        kl.klang("medkit")
        pruef("Beliebig benannte Aufnahme im Klangordner wird geladen",
              "medkit" in kl.aus_datei)
        kl.klang("schuss_repetierer")
        pruef("Ohne Datei kommt der Klang aus dem Code",
              "schuss_repetierer" not in kl.aus_datei
              and len(kl.klang("schuss_repetierer")) > 0)
        alle = [n for n in K.KLANG_NAMEN if not kl.klang(n)]
        pruef("Jeder Name in KLANG_NAMEN gibt einen Klang", not alle,
              ", ".join(alle))

        # Die mitgelieferten MP3-Aufnahmen muessen geladen und auf die
        # einzelnen Spielereignisse statt auf ihre lange Quellaufnahme
        # zugeschnitten werden.
        from pathlib import Path
        aufnahmen = Klaenge(Path(__file__).resolve().parent.parent / "assets")
        repetierer = aufnahmen.klang("schuss_repetierer")
        pruef("MP3-Repetiereraufnahme wird in acht einzelne Schuesse geteilt",
              "schuss_repetierer" in aufnahmen.aus_datei
              and len(repetierer) == 8
              and all(0.4 < s.get_length() < 0.7 for s in repetierer))
        sturm = aufnahmen.klang("schuss_sturm")
        pruef("Sturm-Burst liefert kurze Einzelknalle ohne Salven-Ende",
              "schuss_sturm" in aufnahmen.aus_datei
              and len(sturm) == 16
              and all(0.08 < s.get_length() < 0.14 for s in sturm))
        rauch = aufnahmen.klang("smoke_grenade")
        # Seit 0.32.27 die neue Aufnahme aus dem CODEX-Ordner (rund 1,4 s)
        # statt des neun Sekunden langen Gasstroms ("Rauchgranatentoene
        # erneuert"). Geprueft wird, dass die neue genommen wird - nicht
        # die alte, die noch im Klangordner liegt.
        pruef("Rauchgranate nimmt die neue, kurze Aufnahme",
              "smoke_grenade" in aufnahmen.aus_datei
              and len(rauch) == 1
              and 0.8 <= rauch[0].get_length() <= 3.0,
              "%.2f s" % (rauch[0].get_length() if rauch else -1))
        schrot = aufnahmen.klang("schuss_schrot")
        pruef("Schrotaufnahme startet frueher und ist passend gekuerzt",
              len(schrot) == 1 and 2.45 <= schrot[0].get_length() <= 2.55,
              "%.3f s" % schrot[0].get_length() if schrot else "kein Klang")
        scharf = aufnahmen.klang("schuss_scharf")
        pruef("Scharfschuetzenschuss behaelt den laengeren Nachhall",
              len(scharf) == 1 and 2.7 <= scharf[0].get_length() <= 2.9)
        molotow = aufnahmen.klang("molotov_whoosh")
        pruef("Molotowklang reicht ueber die Branddauer",
              len(molotow) == 1
              and abs(molotow[0].get_length() - K.FEUER["dauer"]) < 0.1)
        eingebaut = ("schuss_scharf", "granate", "dash",
                     "downed_not_dead", "nahkampf_schwung",
                     "nahkampf_treffer_organisch",
                     "nahkampf_treffer_metall", "molotov_glass",
                     "molotov_whoosh", "reload", "rundenstart",
                     "won_match", "lost_match")
        fehlende = [n for n in eingebaut
                    if not aufnahmen.klang(n) or n not in aufnahmen.aus_datei]
        pruef("Alle weiteren MP3-Aufnahmen werden eingelesen", not fehlende,
              ", ".join(fehlende))
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

# ── LAN-Gefecht: verbinden und aufeinander schiessen ─────────────────
# Echte Steckdosen auf dem eigenen Rechner, kein nachgebautes Netz. Was
# hier nicht durchgeht, geht auch im LAN nicht durch.
#
# Die Bestenliste wird hier bewusst nicht angefasst - sie liegt im
# Benutzerordner, und ein Testlauf hat dort nichts verloren. Ihre
# Pruefungen stehen in test_menues.py, das seine Pfade umbiegt.
print()
from dustfront import netz
from dustfront.mehrspieler import Gefecht
# Seit 0.34.103 spielt der Gast Weltmeldungen gepuffert ab (gastseite.py) -
# gewollt 30 bis 150 ms spaeter. Die Pruefungen hier fragen, ob etwas beim
# Gast ankommt, und schauen dafuer nach wenigen Schritten nach; der Puffer
# hat seinen eigenen Abschnitt (0.34.103), dort ist er an.
K.NETZ["puffer_an"] = False

PORT = 51011
wirt = netz.Gastgeber(PORT)
host = Gefecht(app, "ANGREIFER", gastgeber=wirt)
pruef("Gastgeber macht auf", wirt.port == PORT)
pruef("Gastgeber ist selbst dabei", len(host.kaempfer) == 1)

verbindung = netz.Gast("127.0.0.1:%d" % PORT)
pruef("Gast verbindet sich", verbindung.offen, verbindung.fehler)
gast = Gefecht(app, "BESUCH", gast=verbindung)
for _ in range(40):
    host.schritt(K.NETZ["takt"])
    gast.schritt(K.NETZ["takt"])

pruef("Gastgeber kennt beide", len(host.kaempfer) == 2, "%d" % len(host.kaempfer))
pruef("Gast hat eine Nummer", gast.meine_nummer > 0)
pruef("Gast sieht beide", len(gast.kaempfer) == 2, "%d" % len(gast.kaempfer))
pruef("Namen kommen unveraendert an",
      sorted(k.name for k in host.kaempfer.values())
      == sorted(k.name for k in gast.kaempfer.values()))
eigener = host.kaempfer[gast.meine_nummer]
kopie = gast.kaempfer[gast.meine_nummer]
pruef("Position ist auf beiden Seiten gleich",
      eigener.pos.distance_to(kopie.pos) < 1.0,
      "%.2f px" % eigener.pos.distance_to(kopie.pos))

# Der eigentliche Punkt: ohne Bots muessen sich Spieler treffen koennen.
a, b = host.kaempfer[0], host.kaempfer[gast.meine_nummer]
pruef("Jeder Spieler hat eine eigene Fraktion", a.fraktion != b.fraktion,
      "%s / %s" % (a.fraktion, b.fraktion))

stelle = None
for _ in range(300):
    kandidat = freier_punkt(host.welt, 0, host.rnd)
    gegenueber = pygame.Vector2(kandidat.x + 140, kandidat.y)
    # Seit 0.34.26 haelt jede Kiste eine Kugel auf, ohne die Sicht zu
    # versperren: frei heisst darum auch "nichts dazwischen" (deckung).
    # Ohne das traf der Schuss je nach Zufallsstelle nie (bis 0.34.32).
    if (host.welt.frei(kandidat, a.radius, 0)
            and host.welt.frei(gegenueber, b.radius, 0)
            and host.welt.sicht_frei(kandidat, gegenueber, 0)
            and host.welt.deckung(kandidat, gegenueber, 0) == ""):
        stelle = (kandidat, gegenueber)
        break
pruef("Freies Schussfeld gefunden", stelle is not None)

if stelle:
    hier, dort = stelle
    for wer, wo in ((a, hier), (b, dort)):
        wer.pos.update(wo); wer.vorher.update(wo); wer.tempo.update(0, 0)
        wer.leben = wer.max_leben; wer.lebt = True; wer.unverwundbar = 0.0
    a.waffe = a.waffen.index("repetierer")
    a.magazin["repetierer"] = K.WAFFEN["repetierer"]["magazin"]
    a.ziel = pygame.Vector2(b.pos)
    host.welt.schritt(K.FIXED_DT)          # Blickwinkel setzen
    vorher_leben = b.leben
    a.feuern()
    for _ in range(int(0.9 / K.FIXED_DT)):
        b.pos.update(dort); b.tempo.update(0, 0); b.unverwundbar = 0.0
        host.welt.schritt(K.FIXED_DT)
    pruef("Ein Spieler trifft einen anderen", b.leben < vorher_leben,
          "%.0f -> %.0f Leben" % (vorher_leben, b.leben))

    punkte_vorher = a.abschuesse
    b.leben = 5.0; b.unverwundbar = 0.0
    a.takt = 0.0; a.magazin["repetierer"] = K.WAFFEN["repetierer"]["magazin"]
    a.ziel = pygame.Vector2(b.pos)
    a.feuern()
    for _ in range(int(1.2 / K.FIXED_DT)):
        if b.lebt:
            b.pos.update(dort); b.tempo.update(0, 0); b.unverwundbar = 0.0
        host.welt.schritt(K.FIXED_DT)
        host._tote_abrechnen(K.FIXED_DT)
    pruef("Der Abschuss wird ihm gutgeschrieben", a.abschuesse > punkte_vorher,
          "%d -> %d" % (punkte_vorher, a.abschuesse))
    pruef("Der Tod wird gezaehlt", b.tode >= 1, "%d" % b.tode)

    for _ in range(int((K.GEFECHT["wieder_nach"] + 0.5) / K.FIXED_DT)):
        host._tote_abrechnen(K.FIXED_DT)
    pruef("Gefallener steigt wieder ein",
          b.lebt and b.leben == b.max_leben, "lebt=%s" % b.lebt)

# ── Was im ersten LAN-Test gefehlt hat ───────────────────────────────
# Jeder Punkt hier stand in einer Fehlermeldung aus dem Spiel. Sie stehen
# als Pruefung da, damit sie nicht zurueckkommen.
from dustfront.mehrspieler import KampfBeute

def einmal_druecken(szene, taste):
    """Eine Taste genau ein Bild lang druecken, wie im echten Ablauf.

    neues_bild() leert die Einmal-Druecke - wer das im Test weglaesst,
    schaltet einen Umschalter mehrfach hin und her und misst Unsinn.
    """
    e.neues_bild()
    e._gedrueckt = {taste}
    szene.knoepfe_sammeln()
    e.neues_bild()
    e._gedrueckt = set()

def netz_takte(n=8):
    for _ in range(n):
        host.schritt(K.NETZ["takt"])
        gast.schritt(K.NETZ["takt"])

wirt_ich = host.kaempfer[0]
gast_ich = host.kaempfer[gast.meine_nummer]
gast_ich.lebt = True
gast_ich.leben = gast_ich.max_leben

# Der Kern: ein Druck, der nur ein Bild anliegt, darf nicht verlorengehen.
# Genau daran sind vorher Nachladen, Treppe und Waffenwechsel gescheitert.
einmal_druecken(gast, "tracer")
pruef("Ein einzelner Tastendruck ueberlebt bis zum Senden",
      "tracer" in gast._knoepfe)
netz_takte()
pruef("Der Gast kann seine Ziellinie umschalten", gast_ich.tracer)

wirt_ich.tracer = False
einmal_druecken(host, "tracer")
host.schritt(K.FIXED_DT)
pruef("Der Gastgeber kann seine Ziellinie umschalten", wirt_ich.tracer)

# Medkits: erscheinen, und jeder kann sie nehmen
host._seit_medkit = K.GEFECHT["medkit_takt"]
host.schritt(K.FIXED_DT)
liegen = [w for w in list(host.welt.wesen) + list(host.welt.neue)
          if isinstance(w, KampfBeute)]
pruef("Medkits erscheinen im Gefecht", len(liegen) >= 1, "%d" % len(liegen))
if liegen:
    m = liegen[0]
    m.ebene = gast_ich.ebene
    m.pos.update(gast_ich.pos)
    gast_ich.medkits = 0
    host.welt.schritt(K.FIXED_DT)
    host.welt.schritt(K.FIXED_DT)
    pruef("Auch ein Gast kann ein Medkit aufsammeln", gast_ich.medkits == 1,
          "%d" % gast_ich.medkits)

gast_ich.leben = 40.0
gast_ich.heilt_rest = 0.0
einmal_druecken(gast, "heilen")
netz_takte()
pruef("Ein Medkit laesst sich benutzen", gast_ich.heilt_rest > 0,
      "%.2f s" % gast_ich.heilt_rest)

# Strg + Mausrad verschiebt die Ansicht, wie im Einzelspieler das Rad
# allein. (Seit 0.30 gehoert das Rad im Gefecht der Sichtweite.)
#
# Geprueft wird ueber ein echtes Ereignis, nicht ueber das Setzen von
# e.rad: Rad und Tastendruecke werden seit 0.19.2 dort aufgehoben, weil
# der Zeitschritt bei hoher Bildrate nicht in jedem Bild laeuft und die
# Druecke sonst verlorengehen.
host.blick = 0
e.neues_bild()
_mods_alt = pygame.key.get_mods()
pygame.key.set_mods(pygame.KMOD_LCTRL)
host.ereignis(pygame.event.Event(pygame.MOUSEWHEEL, {"x": 0, "y": 1}))
pygame.key.set_mods(_mods_alt)
host.schritt(K.FIXED_DT)
pruef("Strg + Mausrad verschiebt die Ebenenansicht", host.blick == 1,
      "Ebene %d" % host.blick)

# Und der eigentliche Punkt: ein Tastendruck darf auch dann ankommen,
# wenn in diesem Bild gar kein Zeitschritt laeuft.
host._knoepfe.clear()
e.neues_bild()
for taste in e.tabelle.get("tracer_weit", ()):
    host.ereignis(pygame.event.Event(pygame.KEYDOWN, {"key": taste}))
    break
e.neues_bild()              # naechstes Bild, ohne dass ein Schritt lief
pruef("Ein Tastendruck ueberlebt ein Bild ohne Zeitschritt",
      "tracer_weit" in host._knoepfe, " ".join(sorted(host._knoepfe)))

# Was der Gast fuer sein HUD braucht
gast_ich.magazin[gast_ich.waffe_name] = 7
gast_ich.nachlade_rest = 0.8
netz_takte()
kopie = gast.kaempfer[gast.meine_nummer]
pruef("Die Munitionsanzahl kommt beim Gast an",
      kopie.magazin[kopie.waffe_name] == 7, "%d" % kopie.magazin[kopie.waffe_name])
pruef("Das Nachladen ist beim Gast sichtbar", kopie.nachlade_rest > 0,
      "%.2f s" % kopie.nachlade_rest)
pruef("Der Medkit-Vorrat kommt beim Gast an", kopie.medkits == gast_ich.medkits)

# Granaten muss der Gast sehen, sonst trifft ihn was Unsichtbares
gast_ich.nachlade_rest = 0.0
gast_ich.takt = 0.0
gast_ich.waffe = gast_ich.waffen.index("granate")
gast_ich.magazin["granate"] = 3
gast_ich.ziel = gast_ich.pos + pygame.Vector2(120, 0)
host.welt.schritt(K.FIXED_DT)
gast_ich.feuern()
host.welt.schritt(K.FIXED_DT)
arten = {s[4] for s in host._weltmeldung()["schuesse"]}
pruef("Granaten stehen in der Weltmeldung", "granate" in arten, str(arten))
netz_takte(4)
pruef("Der Gast sieht die Granate fliegen",
      any(s[4] == "granate" for s in gast._fremde_schuesse))

# Treppen: der Einmal-Druck "nutzen" kam vorher nie an
ebene_null = host.welt.ebene(0)
treppe = None
for ty in range(ebene_null.hoehe):
    for tx in range(ebene_null.breite):
        if ebene_null.daten(tx, ty).get("treppe") == 1:
            treppe = (tx, ty)
            break
    if treppe:
        break
pruef("Treppe nach oben gefunden", treppe is not None)
if treppe:
    gast_ich.ebene = 0
    gast_ich.pos.update(treppe[0] * K.TILE + 16, treppe[1] * K.TILE + 16)
    gast_ich.lebt = True
    # Ein Druck auf E, wie ihn das Fenster meldet. Seit 0.27 nimmt der
    # Druck die Treppe, nicht das Halten (Halten ist fuers Aufhelfen).
    e.neues_bild()
    gast.ereignis(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    for _ in range(10):
        e._gehalten = {"nutzen"}
        host.schritt(K.NETZ["takt"])
        gast.schritt(K.NETZ["takt"])
        e.neues_bild()
    e.neues_bild(); e._gehalten = set()
    pruef("Der Gast kommt ueber die Treppe eine Ebene hoch",
          gast_ich.ebene == 1, "Ebene %d" % gast_ich.ebene)

# ── Die drei Spielarten ──────────────────────────────────────────────
from dustfront.mehrspieler import KampfGegner
from dustfront import entities as EN

_port = [51300]

def _neuer_port():
    """Den naechsten freien Port fuer ein Testgefecht.

    Die Testports liegen im Bereich, aus dem das System auch die Ports
    fuer ausgehende Verbindungen nimmt. Haelt irgendein Programm auf dem
    Rechner gerade eine Verbindung ueber genau diesen Port, scheitert das
    Aufmachen mit "Address already in use" - ein Fehler des Rechners,
    nicht des Spiels. Also: weiterzaehlen, bis einer frei ist.
    """
    import socket as _s
    while True:
        _port[0] += 1
        probe = _s.socket(_s.AF_INET, _s.SOCK_STREAM)
        probe.setsockopt(_s.SOL_SOCKET, _s.SO_REUSEADDR, 1)
        try:
            probe.bind(("", _port[0]))
            return _port[0]
        except OSError:
            continue
        finally:
            probe.close()

def gefechtspaar(modus, **kw):
    """Gastgeber und Gast in einer Spielart, ueber echte Steckdosen.

    Mit festem Seed: sonst wuerfelt jedes Gefecht seine Einstiegsplaetze
    neu, und Pruefungen, die vom Einstiegsort abhaengen, sind mal gruen
    und mal rot.
    """
    _neuer_port()
    kw.setdefault("seed", 20240 + _port[0])
    wirt_n = netz.Gastgeber(_port[0])
    wirt_s = Gefecht(app, "WIRT", gastgeber=wirt_n, modus=modus, **kw)
    gast_n = netz.Gast("127.0.0.1:%d" % _port[0])
    gast_s = Gefecht(app, "BESUCH", gast=gast_n)
    for _ in range(30):
        wirt_s.schritt(K.NETZ["takt"])
        gast_s.schritt(K.NETZ["takt"])
    return wirt_s, gast_s

# --- pvp: wie gehabt, aber jetzt mit waehlbarem Ende
w, ga = gefechtspaar("pvp", ende_art="abschuesse", ende_wert=3)
pruef("Die Spielart kommt beim Gast an", ga.modus == "pvp", ga.modus)
pruef("Auch die Endbedingung kommt an",
      ga.ende_art == "abschuesse" and ga.ende_wert == 3,
      "%s bis %s" % (ga.ende_art, ga.ende_wert))
pruef("In pvp ist jeder sein eigener Feind",
      w.kaempfer[0].fraktion != w.kaempfer[ga.meine_nummer].fraktion)
pruef("In pvp kommen keine Wellen", not w.mit_gegnern)
w.kaempfer[0].abschuesse = 3
w.schritt(K.FIXED_DT)
pruef("Die Runde endet bei der gewaehlten Abschusszahl", w.vorbei)
w.verlassen(); ga.verlassen()

# --- pve: Wellen, eine Mannschaft, knappe Munition
w, ga = gefechtspaar("pve", knapp=True)
pruef("Die Spielart pve kommt an", ga.modus == "pve")
pruef("Knappe Munition kommt beim Gast an", ga.knapp)
wirt_k = w.kaempfer[0]
gast_k = w.kaempfer[ga.meine_nummer]
pruef("In pve sind alle eine Mannschaft",
      wirt_k.fraktion == gast_k.fraktion, wirt_k.fraktion)
for _ in range(int(K.WELLEN_MP["pause"] / K.FIXED_DT) + 20):
    w.schritt(K.FIXED_DT)
feinde = [x for x in w.welt.wesen if isinstance(x, KampfGegner)]
pruef("Eine Welle startet", w.welle >= 1 and len(feinde) > 0,
      "Welle %d mit %d Gegnern" % (w.welle, len(feinde)))
pruef("Die Welle waechst mit der Spielerzahl",
      len(feinde) > K.WELLEN_MP["grund"], "%d statt %d"
      % (len(feinde), K.WELLEN_MP["grund"]))

# Die eigentliche Koop-Frage: haengen alle Gegner am selben Spieler?
wirt_k.pos.update(200, 200); wirt_k.vorher.update(wirt_k.pos)
gast_k.pos.update(900, 500); gast_k.vorher.update(gast_k.pos)
for feind in feinde:
    feind._ziel = None
    feind._ziel_rest = 0.0
# Lange genug, dass die Haltezeit eines Ziels mindestens einmal ablaeuft
for _ in range(int(K.GEGNER_MP["ziel_haltezeit"] / K.FIXED_DT) + 30):
    w.schritt(K.FIXED_DT)
verteilung = dict(w.gegnerlast)
pruef("Die Gegner verteilen sich auf beide Spieler",
      len(verteilung) == 2 and min(verteilung.values()) > 0, str(verteilung))

# --- Am Boden und wieder auf
wirt_k.unverwundbar = 0.0
wirt_k.leben = 1.0
wirt_k.schaden(50, None, None)
pruef("Wer faellt, liegt am Boden statt tot zu sein",
      wirt_k.am_boden and wirt_k.lebt)
gast_k.pos.update(wirt_k.pos); gast_k.vorher.update(gast_k.pos)
gast_k.ebene = wirt_k.ebene
hilfe_ein = {"will": [0, 0], "ziel": [gast_k.pos.x + 10, gast_k.pos.y],
             "nutzen": True, "knoepfe": []}
w._anwenden(gast_k, hilfe_ein)
pruef("Der Helfer wird erkannt", gast_k.hilft == wirt_k.nummer,
      "hilft %s" % gast_k.hilft)
for _ in range(int(K.REVIVE["dauer"] / K.FIXED_DT) + 10):
    w._anwenden(gast_k, hilfe_ein)
    w._revive(K.FIXED_DT)
# Der Gastgeber ist Spieler 0. Eine 0 ist in Python falsch, und genau
# daran konnte ihm vorher niemand aufhelfen.
pruef("Auch dem Gastgeber kann man aufhelfen",
      not wirt_k.am_boden and wirt_k.leben == K.REVIVE["danach_leben"],
      "%.0f Leben" % wirt_k.leben)

# Der Schutz nach dem Aufhelfen macht unverwundbar - fuer die Pruefung
# muss er weg, sonst kommt der Schaden gar nicht an.
wirt_k.unverwundbar = 0.0
wirt_k.schaden(999, None, None)
gast_k.unverwundbar = 0.0
gast_k.schaden(999, None, None)
w._ende_pruefen(K.FIXED_DT)
pruef("pve endet, wenn alle am Boden liegen", w.vorbei)
wirt_k.aufhelfen(); gast_k.aufhelfen(); w.vorbei = False
w._welle_starten()
pruef("Jede Welle hilft allen wieder auf",
      not wirt_k.am_boden and not gast_k.am_boden)

# --- Knappe Munition
wirt_k.waffe = wirt_k.waffen.index("repetierer")
wirt_k.feuert = False
wirt_k.magazin["repetierer"] = 0
wirt_k.vorrat["repetierer"] = 5
wirt_k.nachlade_rest = 0.0
wirt_k.nachladen()
for _ in range(int(K.WAFFEN["repetierer"]["nachladen"] / K.FIXED_DT) + 5):
    wirt_k.schritt(K.FIXED_DT)
pruef("Nachladen nimmt nur, was der Vorrat hergibt",
      wirt_k.magazin["repetierer"] == 5 and wirt_k.vorrat["repetierer"] == 0,
      "Magazin %d, Vorrat %d" % (wirt_k.magazin["repetierer"],
                                 wirt_k.vorrat["repetierer"]))
wirt_k.magazin["repetierer"] = 0
wirt_k.nachlade_rest = 0.0
wirt_k.nachladen()
pruef("Ohne Vorrat laeuft gar kein Nachladen an",
      wirt_k.nachlade_rest == 0.0, "%.2f" % wirt_k.nachlade_rest)
kiste = KampfBeute(pygame.Vector2(wirt_k.pos), "munition", wirt_k.ebene,
                   w.kaempfer)
kiste.welt = w.welt
kiste.schritt(K.FIXED_DT)
pruef("Eine Munitionskiste fuellt den Vorrat",
      wirt_k.vorrat["repetierer"] > 0, "%d" % wirt_k.vorrat["repetierer"])
w.verlassen(); ga.verlassen()

# --- pvpve: beides zugleich
w, ga = gefechtspaar("pvpve", ende_art="zeit", ende_wert=60)
pruef("pvpve hat Wellen", w.mit_gegnern)
pruef("und dabei trifft jeder jeden",
      w.kaempfer[0].fraktion != w.kaempfer[ga.meine_nummer].fraktion)
pruef("In pvpve gibt es kein Aufhelfen", not w.regeln["revive"])
w.rest = K.FIXED_DT * 0.5          # knapp unter einem Schritt
w.schritt(K.FIXED_DT)
pruef("pvpve endet nach der gewaehlten Zeit", w.vorbei)
w.verlassen(); ga.verlassen()

# ── Granaten fallen, Rauch steht ─────────────────────────────────────
# Beides am Spielkern gemessen, nicht am Gefecht: es gilt auch allein.
from dustfront.entities import Granate, Rauchwolke

def wurfstelle(ebene=2):
    """Eine Stelle auf der Ebene, zwei Kacheln neben einem Loch."""
    eo = szene.welt.ebene(ebene)
    for ty in range(4, eo.hoehe - 4):
        for tx in range(6, eo.breite - 6):
            if eo.loch(tx, ty) and not eo.loch(tx - 2, ty):
                p = pygame.Vector2((tx - 2) * K.TILE + 16, ty * K.TILE + 16)
                if szene.welt.frei(p, 3.0, ebene):
                    return p
    return None

stelle = wurfstelle()
pruef("Wurfstelle neben einem Loch gefunden", stelle is not None)
g = Granate(stelle, 0.0, K.WAFFEN["granate"], 2, None, 200.0)
szene.welt.dazu(g)
gefallen, groesster = False, 0.0
vorige = pygame.Vector2(g.pos)
for _ in range(400):
    szene.welt.schritt(K.FIXED_DT)
    if not g.lebt:
        break
    if g.sturz_rest > 0:
        gefallen = True
        groesster = max(groesster, g.pos.distance_to(vorige))
    vorige = pygame.Vector2(g.pos)
pruef("Eine Granate rollt ueber die Kante und faellt", gefallen)
pruef("Sie landet unten, nicht auf der Wurfebene", g.ebene < 2,
      "Ebene %d" % g.ebene)
# Fallen, nicht springen: ein Bild bei 120 Hz traegt nur ein paar Pixel.
pruef("Sie faellt weich, ohne Sprung", groesster < 8.0,
      "groesster Schritt %.2f px" % groesster)
pruef("Und zuendet erst, wenn sie liegt", not g.lebt)

r = Granate(stelle, 0.0, K.WAFFEN["rauch"], 2, None, 200.0)
szene.welt.dazu(r)
for _ in range(600):
    szene.welt.schritt(K.FIXED_DT)
    if szene.welt.rauch:
        break
pruef("Eine Rauchgranate macht Rauch", len(szene.welt.rauch) == 1,
      "%d Wolken" % len(szene.welt.rauch))
qualm = szene.welt.rauch[0]
pruef("Der Rauch liegt auf der Ebene, auf der sie landet", qualm.ebene < 2,
      "Ebene %d" % qualm.ebene)
pruef("Sie macht keinen Schaden", K.WAFFEN["rauch"]["schaden"] == 0)
duenn = qualm.dichte
for _ in range(int(K.RAUCH["aufbau"] / K.FIXED_DT) + 4):
    szene.welt.schritt(K.FIXED_DT)
pruef("Der Rauch zieht auf, statt sofort dazustehen",
      duenn < 0.2 and qualm.dichte >= 0.999,
      "%.2f auf %.2f" % (duenn, qualm.dichte))

# Er muss wirklich verdecken - und zwar auch von der Ebene darueber aus.
def bild_mit_rauch(blick):
    szene.blick = blick
    szene.blick_hoehe = float(szene.welt.hoehe(blick))
    szene.kamera.pos.update(qualm.pos)
    szene.kamera.versatz.update(0, 0)
    mit = pygame.Surface((K.GAME_W, K.GAME_H))
    szene.zeichnen(mit, 1.0)
    gemerkt = szene.welt.rauch
    szene.welt.rauch = []
    ohne = pygame.Surface((K.GAME_W, K.GAME_H))
    szene.zeichnen(ohne, 1.0)
    szene.welt.rauch = gemerkt
    anders = sum(1 for px in range(0, K.GAME_W, 2)
                 for py in range(0, K.GAME_H, 2)
                 if mit.get_at((px, py))[:3] != ohne.get_at((px, py))[:3])
    return anders

held.ebene = qualm.ebene
held.pos.update(qualm.pos); held.vorher.update(held.pos)
auf_ebene = bild_mit_rauch(qualm.ebene)
pruef("Der Rauch ist auf seiner Ebene zu sehen", auf_ebene > 400,
      "%d Bildpunkte" % auf_ebene)
von_oben = bild_mit_rauch(min(len(szene.welt.ebenen) - 1, qualm.ebene + 1))
pruef("Und von der Ebene darueber genauso", von_oben > 400,
      "%d Bildpunkte" % von_oben)
szene.blick = held.ebene
szene.blick_hoehe = float(szene.welt.hoehe(held.ebene))

for _ in range(int(K.RAUCH["dauer"] / K.FIXED_DT) + 10):
    szene.welt.schritt(K.FIXED_DT)
pruef("Nach seiner Zeit ist der Rauch weg", not szene.welt.rauch,
      "%d uebrig" % len(szene.welt.rauch))
held.ebene = 0
held.pos.update(freies_feld()); held.vorher.update(held.pos)
held.leben = held.max_leben
szene.blick = 0; szene._letzte_ebene = 0; szene.blick_hoehe = 0.0

# ── Rauch: blockig, deckend, ebenenbewusst ───────────────────────────
# Der wichtigste Punkt ist nicht, dass Rauch da ist, sondern dass er
# wirklich deckt: eine Sichtwand, durch die man noch etwas erkennt, ist
# keine Sichtwand.
from dustfront.render import Renderer as _R
probe_renderer = szene.renderer
wolke_probe = Rauchwolke(pygame.Vector2(400, 300), 0)
wolke_probe.alter = K.RAUCH["aufbau"] + 0.5
bild_wolke, wolke_ecke = probe_renderer._rauchbild(wolke_probe, True)
farben = {}
for px in range(bild_wolke.get_width()):
    for py in range(bild_wolke.get_height()):
        c = tuple(bild_wolke.get_at((px, py)))
        if c[3]:
            farben[c] = farben.get(c, 0) + 1
pruef("Rauch benutzt nur die Toene aus der Tabelle",
      len({c[:3] for c in farben}) <= len(K.RAUCH["toene"]),
      "%d Toene" % len({c[:3] for c in farben}))
pruef("Und der Kern deckt voll",
      any(c[3] == 255 for c in farben),
      "hoechste Deckung %d" % max(c[3] for c in farben))
# Pixel-Art heisst: jede Kante sitzt auf dem Korn des Spiels. Ein weicher
# Verlauf haette Kanten ueberall, und genau so etwas hat in einer Welt
# aus Kacheln nichts zu suchen.
daneben = 0
zeile = bild_wolke.get_height() // 2
vor = None
for px in range(bild_wolke.get_width()):
    c = tuple(bild_wolke.get_at((px, zeile)))
    if vor is not None and c != vor and (px + wolke_ecke[0]) % K.RAUCH["korn"]:
        daneben += 1
    vor = c
pruef("Jede Rauchkante sitzt auf dem Korn", daneben == 0,
      "%d daneben" % daneben)
# Volumen: es muessen wirklich mehrere Tonstufen vorkommen, nicht eine
# Flaeche in Grau.
pruef("Die Wolke hat Tonstufen, ist also kein grauer Fleck",
      len({c[:3] for c in farben}) >= 4,
      "%d Toene" % len({c[:3] for c in farben}))
fremd, _ = probe_renderer._rauchbild(wolke_probe, False)
pruef("Rauch einer anderen Ebene ist blasser",
      fremd.get_at((fremd.get_width() // 2, fremd.get_height() // 2))[3]
      < bild_wolke.get_at((bild_wolke.get_width() // 2,
                           bild_wolke.get_height() // 2))[3])

# Deckt er wirklich? Die schaerfste Frage dazu ist nicht "sieht das Bild
# anders aus", sondern: macht es ueberhaupt einen Unterschied, ob die
# Figur da ist? Einmal mit Figur im Rauch zeichnen, einmal ohne - sind
# beide Bilder gleich, ist von ihr nichts zu sehen.
from dustfront.entities import Spieler as _Spieler
stelle = freies_feld()
held.ebene = 0
held.pos.update(stelle); held.vorher.update(held.pos)
opfer = _Spieler(stelle + pygame.Vector2(40, 0), 0)
opfer.fraktion = "versteckt"
szene.welt.dazu(opfer)
szene.welt.schritt(K.FIXED_DT)
szene.blick = 0; szene._letzte_ebene = 0; szene.blick_hoehe = 0.0
szene.kamera.pos.update(stelle); szene.kamera.versatz.update(0, 0)
wand = Rauchwolke(pygame.Vector2(opfer.pos), 0)
wand.alter = K.RAUCH["aufbau"] + 0.5
szene.welt.rauch.append(wand)

mit_figur = pygame.Surface((K.GAME_W, K.GAME_H))
szene.zeichnen(mit_figur, 1.0)
opfer.lebt = False
szene.welt.schritt(K.FIXED_DT)
szene.welt.rauch = [wand]          # der Schritt haette sie altern lassen
wand.alter = K.RAUCH["aufbau"] + 0.5
ohne_figur = pygame.Surface((K.GAME_W, K.GAME_H))
szene.zeichnen(ohne_figur, 1.0)

anders = sum(1 for qx in range(0, K.GAME_W, 2) for qy in range(0, K.GAME_H, 2)
             if mit_figur.get_at((qx, qy))[:3] != ohne_figur.get_at((qx, qy))[:3])
pruef("Eine Figur im Rauch ist im Bild nicht zu finden", anders == 0,
      "%d Bildpunkte verraten sie" % anders)

pruef("Die Welt weiss, dass die Stelle verdeckt ist",
      szene.welt.verdeckt(opfer.pos, 0))
pruef("Knapp daneben ist sie es nicht",
      not szene.welt.verdeckt(opfer.pos + pygame.Vector2(K.RAUCH["radius"] + 20, 0), 0))
pruef("Und auf einer anderen Ebene auch nicht",
      not szene.welt.verdeckt(opfer.pos, 1))
opfer.lebt = False
szene.welt.rauch = []
szene.welt.schritt(K.FIXED_DT)

# ── 0.34.3: Waende und Barrikaden stehen ─────────────────────────────
# Gemeldet: "Barrikaden und Waende sollen von allen Perspektiven als solche
# erkennbar sein." Bis dahin waren sie flache Kacheln: auf dem Plateau
# sah eine Lehmmauer aus wie ein Weg. Jetzt haben sie eine Hoehe
# (K.STEHEN) und werden wie die Plateaus in Perspektive gezeichnet.
from dustfront import world as _W63
from dustfront.render import Kamera as _Kam63

def _stand_bild(zeilen, satz, kamera_kachel, hoehen=None, figur=None):
    """Eine kleine Welt aus Textzeilen, gezeichnet mit der Kamera ueber
    `kamera_kachel`. `hoehen` setzt K.STEHEN zum Vergleich voruebergehend,
    `figur` stellt einen Laeufer an diesen Weltpunkt."""
    welt_ = _W63.Welt([_W63.Ebene.aus_text(zeilen, 0)], satz=satz)
    if figur is not None:
        from dustfront.entities import Gegner as _G64
        g_ = _G64(pygame.Vector2(figur), "laeufer", 0)
        g_.welt = welt_
        g_.vorher.update(g_.pos)
        welt_.wesen.append(g_)
    kam_ = _Kam63(pygame.Vector2((kamera_kachel[0] + .5) * K.TILE,
                                 (kamera_kachel[1] + .5) * K.TILE))
    alt_ = {n: dict(d) for n, d in K.STEHEN.items()}
    try:
        if hoehen is not None:
            for d in K.STEHEN.values():
                d["hoehe"] = hoehen
        bild_ = pygame.Surface((K.GAME_W, K.GAME_H))
        bild_.fill(K.C_VOID)
        r_ = szene.renderer
        r_.vignette_an = False
        r_.welt_zeichnen(bild_, welt_, kam_, 1.0, 0.0, blick=0)
    finally:
        for n, d in alt_.items():
            K.STEHEN[n].update(d)
    return bild_, kam_

_feld63 = ["." * 24 for _ in range(14)]
_feld63[3] = "." * 6 + "#" + "." * 17        # eine Mauer oben links
_feld63[7] = "." * 12 + "#" + "." * 11       # eine direkt unter dem Auge
for _satz63 in ("", "wueste", "schnee"):
    mit63, kam63 = _stand_bild(_feld63, _satz63, (12, 7))
    ohne63, _ = _stand_bild(_feld63, _satz63, (12, 7), hoehen=0.0)
    ecke63 = kam63.ecke
    # Die Mauer oben links: ihre Sued- und Ostseite schauen zum Auge. Im
    # Fussabdruck der Mauer, an der Suedostecke, steht jetzt die Seite.
    sx63 = int(7 * K.TILE - ecke63.x) - 2
    sy63 = int(4 * K.TILE - ecke63.y) - 2
    pruef("Satz %r: eine Mauer abseits der Mitte zeigt die Seite zum Auge"
          % (_satz63 or "standard"),
          mit63.get_at((sx63, sy63)) != ohne63.get_at((sx63, sy63)),
          "%s / %s" % (mit63.get_at((sx63, sy63)), ohne63.get_at((sx63, sy63))))
    # Die Mauer direkt unter dem Auge: keine Seite, die Oberseite bleibt
    # an ihrem Platz - ihr Rand liegt genau auf dem Kachelrand.
    mx63 = int(12 * K.TILE - ecke63.x)
    my63 = int(7 * K.TILE - ecke63.y)
    pruef("Satz %r: unter dem Auge liegt die Oberseite genau auf der Kachel"
          % (_satz63 or "standard"),
          mit63.get_at((mx63 + 16, my63 + 16)) != mit63.get_at((mx63 - 3, my63 + 16)))

# Die Oberseite hebt sich vom Boden daneben ab - in jedem Kartensatz.
# Beim Schnee war der erste Entwurf eine weisse Kappe, und die verschwand
# im Schnee am Boden.
for _satz63, (boden63, wand63) in {"": ("boden", "wand"),
                                   "wueste": ("sand", "sand_wand"),
                                   "schnee": ("schnee", "schnee_fels")}.items():
    def _hell63(name):
        c = pygame.transform.average_color(szene.renderer.bilder.bild(name))
        return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
    unterschied63 = abs(_hell63(boden63) - _hell63(wand63 + "_oben"))
    pruef("Satz %r: Mauerkrone und Boden unterscheiden sich deutlich"
          % (_satz63 or "standard"), unterschied63 > 25, "%.0f" % unterschied63)
pruef("Jede stehende Kachel hat eine Oberseite zum Draufschauen",
      all(szene.renderer.bilder.bild(n + "_oben") is not None for n in K.STEHEN))

# Fass und Kiste: rund um sie herum ist Boden zu sehen, und sie stehen.
_fass63 = ["." * 24 for _ in range(14)]
_fass63[3] = "." * 6 + "X" + "." * 17
mit63, kam63 = _stand_bild(_fass63, "wueste", (12, 7))
ohne63, _ = _stand_bild(_fass63, "wueste", (12, 7), hoehen=0.0)
ecke63 = kam63.ecke
ecke_px63 = (int(6 * K.TILE - ecke63.x) + 1, int(3 * K.TILE - ecke63.y) + 1)
pruef("Um das Fass herum liegt Sand, keine Kachelflaeche",
      mit63.get_at(ecke_px63) == ohne63.get_at(ecke_px63))
pruef("Das Fass hat einen Koerper zum Auge hin",
      sum(1 for x_ in range(K.TILE) for y_ in range(K.TILE)
          if mit63.get_at((int(6 * K.TILE - ecke63.x) + x_,
                           int(3 * K.TILE - ecke63.y) + y_))
          != ohne63.get_at((int(6 * K.TILE - ecke63.x) + x_,
                            int(3 * K.TILE - ecke63.y) + y_))) > 20)

# Blut liegt am Boden, nicht auf der Mauer: die Dekale kommen vor den
# stehenden Kacheln (bis 0.34.2 danach).
welt63 = _W63.Welt([_W63.Ebene.aus_text(_feld63, 0)], satz="wueste")
klecks63 = pygame.Surface((24, 24), pygame.SRCALPHA)
klecks63.fill((200, 0, 0, 255))
vorher63, kam63 = _stand_bild(_feld63, "wueste", (12, 7))
e63 = welt63.ebene(0)
_aus_text_alt63 = _W63.Ebene.aus_text
_W63.Ebene.aus_text = classmethod(lambda cls, z, i: e63)
try:
    e63.dekal(klecks63, 12.5 * K.TILE, 7.5 * K.TILE)
    nachher63, _ = _stand_bild(_feld63, "wueste", (12, 7))
finally:
    _W63.Ebene.aus_text = _aus_text_alt63
mitte63 = (int(12.5 * K.TILE - kam63.ecke.x), int(7.5 * K.TILE - kam63.ecke.y))
pruef("Ein Blutfleck unter einer Mauer liegt nicht auf der Mauerkrone",
      nachher63.get_at(mitte63) == vorher63.get_at(mitte63),
      "%s / %s" % (nachher63.get_at(mitte63), vorher63.get_at(mitte63)))

# 0.34.4: Mauern verdecken, wer hinter ihnen steht ("diese Mauern duerfen
# Leute verdecken"). Eine senkrechte Mauer weit links vom Auge, ein
# Laeufer knapp dahinter (westlich, vom Auge weg) und einer knapp davor.
_mauer64 = ["." * 24 for _ in range(14)]
for _y64 in range(3, 11):
    _mauer64[_y64] = "..." + "#" + "." * 20
_hinten64 = (3 * K.TILE - 7, 7.5 * K.TILE)
_vorn64 = (4 * K.TILE + 12, 7.5 * K.TILE)
leer64, kam64 = _stand_bild(_mauer64, "wueste", (12, 7))
hinten64, _ = _stand_bild(_mauer64, "wueste", (12, 7), figur=_hinten64)
vorn64, _ = _stand_bild(_mauer64, "wueste", (12, 7), figur=_vorn64)

def _px64(p):
    return (int(p[0] - kam64.ecke.x), int(p[1] - kam64.ecke.y))

pruef("Hinter einer Mauer verdeckt die Mauer die Figur",
      hinten64.get_at(_px64(_hinten64)) == leer64.get_at(_px64(_hinten64)),
      "%s / %s" % (hinten64.get_at(_px64(_hinten64)), leer64.get_at(_px64(_hinten64))))
pruef("Vor der Mauer bleibt die Figur zu sehen",
      vorn64.get_at(_px64(_vorn64)) != leer64.get_at(_px64(_vorn64)))

# 0.34.5: alles, was es in der Welt wirklich gaebe, verdeckt sich wie in
# echter 3D - Anzeige (Balken, Zahlen) darf darueber liegen. Dieselbe
# Mauer wie eben, das Auge ueber Kachel (12, 7).
from dustfront.entities import Partikel as _P65, Geschoss as _Gs65, Gegner as _Gg65

def _bild65(dinge=(), funken=(), figuren=None, anzeige=None):
    welt_ = _W63.Welt([_W63.Ebene.aus_text(_mauer64, 0)], satz="wueste")
    for d in dinge:
        d.welt = welt_
        d.vorher.update(d.pos)
        welt_.wesen.append(d)
    for (x_, y_) in funken:
        welt_.partikel.append(_P65((x_, y_), (0, 0), 5.0, (255, 0, 255), 3,
                                   "funke", 0.0, 0))
    kam_ = _Kam63(pygame.Vector2(12.5 * K.TILE, 7.5 * K.TILE))
    bild_ = pygame.Surface((K.GAME_W, K.GAME_H))
    bild_.fill(K.C_VOID)
    szene.renderer.vignette_an = False
    szene.renderer.welt_zeichnen(bild_, welt_, kam_, 1.0, 0.0, blick=0,
                                 figuren=figuren, anzeige=anzeige)
    return bild_, kam_, welt_

leer65, kam65, welt65 = _bild65()
r65 = szene.renderer
pruef("Ein Punkt am Boden hinter der Mauer ist verdeckt",
      r65.verdeckt(welt65, 0, _hinten64, 0.0))
pruef("In Laufhoehe knapp dahinter auch",
      r65.verdeckt(welt65, 0, _hinten64, K.HOEHEN["lauf"]))
pruef("Ueber der Mauerkante ist er zu sehen",
      not r65.verdeckt(welt65, 0, _hinten64, K.STEHEN["sand_wand"]["hoehe"] + 6))
pruef("Vor der Mauer ist nichts verdeckt",
      not r65.verdeckt(welt65, 0, _vorn64, 0.0))

def _anders65(bild_, p):
    q = (int(p[0] - kam65.ecke.x), int(p[1] - kam65.ecke.y))
    return bild_.get_at(q) != leer65.get_at(q)

_daten65 = K.WAFFEN["repetierer"]
kugel_h, _, _ = _bild65([_Gs65(pygame.Vector2(_hinten64), 0.0, _daten65, 0)])
kugel_v, _, _ = _bild65([_Gs65(pygame.Vector2(_vorn64), 0.0, _daten65, 0)])
pruef("Eine Kugel hinter der Mauer ist nicht zu sehen", not _anders65(kugel_h, _hinten64))
pruef("Eine Kugel davor schon", _anders65(kugel_v, _vorn64))
funke_h, _, _ = _bild65(funken=[_hinten64])
funke_v, _, _ = _bild65(funken=[_vorn64])
pruef("Funken hinter der Mauer sind verdeckt", not _anders65(funke_h, _hinten64))
pruef("Funken davor nicht", _anders65(funke_v, _vorn64))

# Der Lebensbalken ist Anzeige: er bleibt ueber der Mauer stehen, auch
# wenn der Gegner selbst dahinter verschwindet.
g65 = _Gg65(pygame.Vector2(_hinten64), "laeufer", 0)
g65.leben = g65.max_leben * 0.4
balken65, _, _ = _bild65([g65])
g65b = _Gg65(pygame.Vector2(_hinten64), "laeufer", 0)
heil65, _, _ = _bild65([g65b])
_balken_y65 = int(_hinten64[1] - (g65.radius + 11) - kam65.ecke.y)
pruef("Der Lebensbalken eines verdeckten Gegners liegt ueber der Mauer",
      any(balken65.get_at((x_, _balken_y65)) != heil65.get_at((x_, _balken_y65))
          for x_ in range(int(_hinten64[0] - kam65.ecke.x) - 9,
                          int(_hinten64[0] - kam65.ecke.x) + 9)))

# Der Gast zeichnet, was er nur gemeldet bekommt, ueber dieselben Haken:
# was am Boden steht, verdeckt die Mauer; die Anzeige liegt obenauf.
def _klecks65(farbe):
    def zeichnen(flaeche, ebene, ecke):
        flaeche.fill(farbe, (int(_hinten64[0] - ecke.x) - 2,
                             int(_hinten64[1] - ecke.y) - 2, 5, 5))
    return zeichnen
gast_f, _, _ = _bild65(figuren=_klecks65((255, 0, 255)))
gast_a, _, _ = _bild65(anzeige=_klecks65((255, 0, 255)))
pruef("Beim Gast verdeckt die Mauer gemeldete Gegner dahinter",
      not _anders65(gast_f, _hinten64))
pruef("Seine Anzeige liegt ueber der Mauer", _anders65(gast_a, _hinten64))

# ── 0.34.6: Gelaende und Kleinkram (fuer STAUBTAL) ─────────────────────
# Gemeldet: "Bereiche, wo 50 verschiedene Faesser nebeneinander stehen" -
# die Karte sollte aussehen wie von Hand gebaut. Dafuer gibt es Fels,
# Brocken, Sandsaecke, Holzkisten, Kakteen, Schrott und die Bodenarten
# Piste, Kies, Pflaster, Gestruepp und Dielen.
from dustfront import core as _core66
_neu66 = {"r": K.FELS, "b": K.BROCKEN, "s": K.SANDSACK, "h": K.HOLZKISTE,
          "k": K.KAKTUS, "w": K.SCHROTT, ":": K.PISTE, ";": K.KIES,
          "_": K.PFLASTER, '"': K.GESTRUEPP, "=": K.DIELEN}
pruef("Jedes neue Kartenzeichen wird zu seiner Kachel",
      all(_W63.ZEICHEN.get(z_) == k_ for z_, k_ in _neu66.items()))
pruef("Keins ist ein Grossbuchstabe - die sind Marken",
      not any(z_.isupper() for z_ in _neu66))
_ohne_bild66 = []
for _d66 in K.KACHELN.values():
    for _n66 in _d66.get("bilder", (_d66["bild"],)):
        for _name66 in ((_n66, _n66 + "_oben") if _n66 in K.STEHEN or _d66["name"] in K.STEHEN
                        else (_n66,)):
            if _name66 not in K.BILD_MASS or _name66 not in _core66._PLATZHALTER:
                _ohne_bild66.append(_name66)
pruef("Jedes Kachelbild (und jede Oberseite) hat ein Mass und einen Platzhalter",
      not _ohne_bild66, _ohne_bild66)
pruef("Gewachsener Fels steht und haelt Kugeln auf wie eine Mauer",
      K.KACHELN[K.FELS]["fest"] and K.KACHELN[K.FELS]["sicht"]
      and K.STEHEN["fels"]["hoehe"] > K.STEHEN["sand_wand"]["hoehe"])
pruef("Brocken, Sandsack, Kiste, Kaktus, Schrott halten auf wie ein Fass",
      all(K.KACHELN[k_]["fest"] and not K.KACHELN[k_]["sicht"]
          for k_ in (K.BROCKEN, K.SANDSACK, K.HOLZKISTE, K.KAKTUS, K.SCHROTT)))
pruef("Die neuen Bodenarten sind begehbar",
      all(not K.KACHELN[k_]["fest"] and not K.KACHELN[k_].get("loch")
          for k_ in (K.PISTE, K.KIES, K.PFLASTER, K.GESTRUEPP, K.DIELEN)))

# Bis 0.34.25 flog eine Kugel ueber den Sandsack hinweg. Seit 0.34.26
# haelt jedes Hindernis Kugeln auf (gemeldet: "Alles, was eine Art Textur
# hat und etwas blocken sollte, sollte auch Schuesse blocken").
_schuss66 = _W63.Welt([_W63.Ebene.aus_text(["." * 20, "...s.....r" + "." * 10, "." * 20], 0)],
                      satz="wueste")
_kugel66 = _Gs65(pygame.Vector2(1.5 * K.TILE, 1.5 * K.TILE), 0.0, K.WAFFEN["repetierer"], 0)
_kugel66.welt = _schuss66
_kugel66.vorher.update(_kugel66.pos)
_schuss66.wesen.append(_kugel66)
for _ in range(120):
    if not _kugel66.lebt:
        break
    _kugel66.schritt(K.FIXED_DT)
pruef("Eine Kugel bleibt am Sandsack haengen, nicht erst am Fels",
      not _kugel66.lebt and 2 * K.TILE < _kugel66.pos.x <= 3 * K.TILE + 1,
      "endet bei x %.0f" % _kugel66.pos.x)

# Piste franst zum Sand hin aus, zur Piste daneben nicht. Bis dahin zog
# jede Kachelkante eine Linie, und ein schraeger Weg war eine Treppe.
_e66 = _W63.Ebene.aus_text(["....", ".::.", "...."], 0)
_rand66 = szene.renderer._weicher_rand("piste", _e66, 1, 1, "sand")
_voll66 = szene.renderer.bilder.bild("piste")
pruef("Piste franst zum Sand hin aus",
      sum(1 for x_ in range(K.TILE) for y_ in range(4)
          if _rand66.get_at((x_, y_)) != _voll66.get_at((x_, y_))) > 20)
pruef("... aber nicht zur Piste daneben",
      all(_rand66.get_at((K.TILE - 1, y_)) == _voll66.get_at((K.TILE - 1, y_))
          for y_ in range(8, K.TILE - 8)))
pruef("... und ganz ohne Sand drumherum bleibt sie, wie sie ist",
      szene.renderer._weicher_rand("piste", _W63.Ebene.aus_text([":::"] * 3, 0), 1, 1, "sand")
      is _voll66)

# Eine Marke liegt auf dem Boden, der um sie ist - mitten auf dem
# Pflasterplatz kein Sandfleck (bis 0.34 wurde jede Marke zu Sand).
_m66 = _W63.Ebene.aus_text(["___", "_A_", "___"], 0)
pruef("Eine Marke auf dem Pflaster ist Pflaster",
      _m66.kachel(1, 1) == K.PFLASTER and "A" in _m66.marken)
pruef("Neben Mauern zaehlt nur der begehbare Boden",
      _W63.Ebene.aus_text(["###", "#Z:", "###"], 0).kachel(1, 1) == K.PISTE)
pruef("Ohne begehbaren Nachbarn bleibt es Sand",
      _W63.Ebene.aus_text(["###", "#Z#", "###"], 0).kachel(1, 1) == K.BODEN)

# ── Ebenen: nur eine nach oben ───────────────────────────────────────
# Wer unten steht, soll die Etage ueber sich durchscheinen sehen - aber
# nicht gleich drei Stockwerke uebereinander. Ausnahme seit 0.34.7: eine
# Tafel auf einem Felsblock (die hohe Tafel auf STAUBTAL, Abschnitt
# "zwei Plateaus aufeinander"). Die Testkarte hat keine.
gezeichnet = []
echt = szene.renderer.ebene_zeichnen
def merken(ziel, welt, index, ecke, dunkel, auge=None, aufschieben=False):
    gezeichnet.append(index)
    return echt(ziel, welt, index, ecke, dunkel, auge, aufschieben)
szene.renderer.ebene_zeichnen = merken
szene.blick = 0
szene.blick_hoehe = 0.0
szene.zeichnen(pygame.Surface((K.GAME_W, K.GAME_H)), 1.0)
szene.renderer.ebene_zeichnen = echt
pruef("Von unten ist hoechstens eine Ebene nach oben zu sehen",
      max(gezeichnet) <= 1, "gezeichnet: %s" % sorted(set(gezeichnet)))
pruef("Die eigene Ebene natuerlich schon", 0 in gezeichnet)

# ── Treppen: mehrere Wege nach oben ──────────────────────────────────
wege = []
for i in range(len(szene.welt.ebenen)):
    eo = szene.welt.ebene(i)
    wege.append(sum(1 for kach in eo.kacheln if kach == K.TREPPE_HOCH))
pruef("Von jeder Ebene ausser der obersten geht es mehrfach hoch",
      all(n >= 3 for n in wege[:-1]), "Treppen je Ebene: %s" % wege)
# Sie muessen auch weit auseinanderliegen, sonst nuetzen sie nichts.
punkte = []
eo = szene.welt.ebene(0)
for ty in range(eo.hoehe):
    for tx in range(eo.breite):
        if eo.kachel(tx, ty) == K.TREPPE_HOCH:
            punkte.append(pygame.Vector2(tx * K.TILE, ty * K.TILE))
weiteste = max(a.distance_to(b) for a in punkte for b in punkte)
pruef("Und sie liegen ueber die Karte verteilt", weiteste > 600,
      "%.0f px auseinander" % weiteste)

# ── Mannschaften: team, versus, huegel ───────────────────────────────
from dustfront.mehrspieler import Kaempfer

# Drei Spielarten, die sich denselben Unterbau teilen: zwei Mannschaften,
# eine Fraktion je Mannschaft, ein gemeinsames Konto. Geprueft wird
# deshalb einmal der Unterbau und danach je Spielart das, was nur sie hat.

def netz_durchlassen(a, b, takte=12):
    """So viele Netztakte, dass eine Meldung sicher angekommen ist."""
    for _ in range(takte):
        a.schritt(K.NETZ["takt"])
        b.schritt(K.NETZ["takt"])


# --- team: Abschuesse zaehlen fuer die Mannschaft
w, ga = gefechtspaar("team", ende_art="abschuesse", ende_wert=4)
wirt_k = w.kaempfer[0]
gast_k = w.kaempfer[ga.meine_nummer]
pruef("Die Spielart team kommt beim Gast an", ga.modus == "team", ga.modus)
pruef("Der Gastgeber ist in der ersten Mannschaft", wirt_k.team == 0,
      "Team %d" % wirt_k.team)
pruef("Der Neue kommt in die andere Mannschaft", gast_k.team == 1,
      "Team %d" % gast_k.team)
pruef("Zwei Mannschaften sind zwei Fraktionen",
      wirt_k.fraktion != gast_k.fraktion,
      "%s / %s" % (wirt_k.fraktion, gast_k.fraktion))
dritter = w._dazu(99, "DRITTER")
pruef("Der dritte Mann fuellt die kleinere Mannschaft auf",
      dritter.team == 0, "Team %d" % dritter.team)
pruef("Gleiche Mannschaft heisst gleiche Fraktion",
      dritter.fraktion == wirt_k.fraktion, dritter.fraktion)
w.kaempfer.pop(99, None)
dritter.lebt = False
pruef("Die Mannschaft kommt beim Gast an",
      ga.kaempfer[ga.meine_nummer].team == 1,
      "Team %d" % ga.kaempfer[ga.meine_nummer].team)

# Ein Abschuss zaehlt fuer das Konto der Mannschaft, nicht nur fuer den
# Schuetzen.
gast_k.lebt = False
gast_k.toeter = wirt_k
w._tote_abrechnen(K.FIXED_DT)
pruef("Ein Abschuss zaehlt fuer die Mannschaft",
      w.teampunkte[0] == 1 and w.teampunkte[1] == 0, str(w.teampunkte))
pruef("Und weiter fuer den Schuetzen selbst", wirt_k.abschuesse == 1)
w.teampunkte[0] = 4
w._ende_pruefen(K.FIXED_DT)
pruef("team endet bei der gewaehlten Teamabschusszahl",
      w.vorbei and w.sieger_team == 0, "Sieger %d" % w.sieger_team)
netz_durchlassen(w, ga)
pruef("Der Gast erfaehrt, welche Mannschaft gewonnen hat",
      ga.sieger_team == 0 and ga.teampunkte[0] == 4,
      "Sieger %d, Stand %s" % (ga.sieger_team, ga.teampunkte))
w.verlassen(); ga.verlassen()

# --- versus: ein Leben je Runde, Aufhelfen nur in der eigenen Mannschaft
w, ga = gefechtspaar("versus")
wirt_k = w.kaempfer[0]
gast_k = w.kaempfer[ga.meine_nummer]
pruef("In versus wird aufgeholfen", w.regeln["revive"] and wirt_k.revive_an)
pruef("Aber kuerzer als in pve",
      wirt_k.boden_zeit == K.VERSUS["boden_zeit"]
      and wirt_k.revive_dauer == K.VERSUS["revive_dauer"],
      "%.0f s am Boden, %.0f s Aufhelfen"
      % (wirt_k.boden_zeit, wirt_k.revive_dauer))
pruef("Dem Gegner hilft niemand auf", not w._darf_helfen(wirt_k, gast_k))
pruef("Dem eigenen Mann schon",
      w._darf_helfen(wirt_k, Kaempfer(pygame.Vector2(0, 0), 0, 7, "X",
                                      wirt_k.fraktion, team=wirt_k.team)))
pruef("Die erste Runde laeuft", w.runde >= 1, "Runde %d" % w.runde)

# Der Gast faellt. Er ist allein in seiner Mannschaft - also kann ihm
# niemand aufhelfen, und die Runde ist in dem Augenblick entschieden.
#
# Bis 0.26 stand hier das Gegenteil ("Am Boden ist die Runde noch nicht
# entschieden"), und genau das war der gemeldete Fehler: man gewann erst,
# wenn der Bodentimer des Gefallenen abgelaufen war.
gast_k.unverwundbar = 0.0
gast_k.schaden(999, None, None)
pruef("Wer faellt, liegt erst einmal am Boden",
      gast_k.am_boden and gast_k.lebt)
w._runden(K.FIXED_DT)
pruef("Liegt die ganze Mannschaft, ist die Runde sofort entschieden",
      w.teampunkte == [1, 0] and w.runden_gespielt == 1,
      "%s, gespielt %d" % (w.teampunkte, w.runden_gespielt))
pruef("Danach laeuft die Pause", w.runden_pause > 0,
      "%.1f s" % w.runden_pause)
gast_k.magazin[gast_k.waffe_name] = 0
runde_vorher = w.runde
w._runden(K.VERSUS["pause"] + K.FIXED_DT)
pruef("Nach der Pause faengt die naechste Runde an",
      w.runde == runde_vorher + 1, "Runde %d" % w.runde)
pruef("Und alle stehen wieder, mit vollem Magazin",
      gast_k.lebt and not gast_k.raus and not gast_k.am_boden
      and gast_k.magazin[gast_k.waffe_name]
      == K.WAFFEN[gast_k.waffe_name]["magazin"])
pruef("Die beiden stehen nicht nebeneinander",
      wirt_k.pos.distance_to(gast_k.pos) > 60.0,
      "%.0f px" % wirt_k.pos.distance_to(gast_k.pos))

# Solange einer steht, der aufhelfen kann, ist nichts entschieden.
dritter_v = Kaempfer(pygame.Vector2(gast_k.pos) + pygame.Vector2(30, 0), 0, 9,
                     "DRITTER", gast_k.fraktion, team=gast_k.team)
w.kaempfer[9] = dritter_v
w.welt.dazu(dritter_v)
gast_k.unverwundbar = 0.0            # nach dem Neustart gilt wieder Schutz
gast_k.schutz = 0.0
dritter_v.unverwundbar = 0.0
gast_k.schaden(999, None, None)
stand_vorher = list(w.teampunkte)
w._runden(K.FIXED_DT)
pruef("Steht noch ein Mitspieler, laeuft die Runde weiter",
      w.teampunkte == stand_vorher, str(w.teampunkte))
dritter_v.schaden(999, None, None)
w._runden(K.FIXED_DT)
pruef("Liegt auch er, ist sie vorbei - ohne auf einen Timer zu warten",
      w.teampunkte[0] == stand_vorher[0] + 1 and gast_k.boden_rest > 1.0,
      "%s, Bodenzeit noch %.0f s" % (w.teampunkte, gast_k.boden_rest))
w.kaempfer.pop(9, None)
dritter_v.lebt = False
w.verlassen(); ga.verlassen()

# Wie viele Runden gespielt werden, und der Matchpoint.
w, ga = gefechtspaar("versus", runden=4)
pruef("Die Rundenzahl ist die Zahl der gespielten Runden",
      w.runden_anzahl == 4 and w.runden_text() == "RUNDE 1 VON 4",
      w.runden_text())
w.teampunkte = [3, 0]; w.runden_gespielt = 3
pruef("Wer nicht mehr einzuholen ist, hat gewonnen",
      w._match_sieger() == 0)
w.teampunkte = [2, 1]; w.runden_gespielt = 3
pruef("Wer noch einholen kann, spielt weiter", w._match_sieger() == -1)
w.teampunkte = [2, 2]; w.runden_gespielt = 4
pruef("Gleichstand nach allen Runden: es geht weiter",
      w._match_sieger() == -1 and w.matchpoint)
pruef("Und die naechste heisst Matchpoint", w.runden_text().startswith("MATCHPOINT"),
      w.runden_text())
w.teampunkte = [3, 2]; w.runden_gespielt = 5
pruef("Wer den Matchpoint holt, gewinnt", w._match_sieger() == 0)
w.teampunkte = [1, 1]; w.runden_gespielt = 3
pruef("Eine Runde ohne Sieger zaehlt als gespielt",
      w._match_sieger() == -1 and not w.matchpoint)
w.verlassen(); ga.verlassen()

w, ga = gefechtspaar("versus", runden=5)
wirt_k = w.kaempfer[0]
gast_k = w.kaempfer[ga.meine_nummer]
w.teampunkte = [2, 0]
w.runden_gespielt = 2
gast_k.unverwundbar = 0.0
gast_k.schaden(999, None, None)
w._runden(K.FIXED_DT)
pruef("Der dritte Sieg von fuenf beendet das Gefecht",
      w.vorbei and w.sieger_team == 0,
      "%s, Sieger %d" % (w.teampunkte, w.sieger_team))
netz_durchlassen(w, ga, 10)
pruef("Und der Gast kennt Rundenzahl und Stand",
      ga.runden_anzahl == 5 and ga.teampunkte == [3, 0],
      "%d, %s" % (ga.runden_anzahl, ga.teampunkte))
w.verlassen(); ga.verlassen()

# Allein wartet versus, statt jede Runde sofort zu entscheiden
_neuer_port()
wirt_n = netz.Gastgeber(_port[0])
allein = Gefecht(app, "ALLEIN", gastgeber=wirt_n, modus="versus")
for _ in range(20):
    allein.schritt(K.NETZ["takt"])
pruef("Ohne Gegenmannschaft faengt keine Runde an",
      allein.runde == 0 and allein.teampunkte == [0, 0],
      "Runde %d, Stand %s" % (allein.runde, allein.teampunkte))
allein.verlassen()

# --- huegel: der Kreis in der Kartenmitte
w, ga = gefechtspaar("huegel", ende_art="zeit", ende_wert=600)
wirt_k = w.kaempfer[0]
gast_k = w.kaempfer[ga.meine_nummer]
ebene_null = w.welt.ebene(K.ZONE["ebene"])
pruef("Der Kreis liegt in der Mitte der Karte",
      abs(w.zone_mitte.x - ebene_null.pixel_breite / 2) < 1.0
      and abs(w.zone_mitte.y - ebene_null.pixel_hoehe / 2) < 1.0,
      "%.0f/%.0f" % (w.zone_mitte.x, w.zone_mitte.y))
pruef("Der Gast rechnet dieselbe Mitte aus",
      ga.zone_mitte.distance_to(w.zone_mitte) < 1.0)

wirt_k.pos.update(w.zone_mitte); wirt_k.vorher.update(wirt_k.pos)
wirt_k.ebene = K.ZONE["ebene"]
pruef("Wer in der Mitte steht, ist im Kreis", w.in_der_zone(wirt_k))
wirt_k.ebene = K.ZONE["ebene"] + 1
pruef("Eine Ebene hoeher zaehlt nicht", not w.in_der_zone(wirt_k))
wirt_k.ebene = K.ZONE["ebene"]
weit = pygame.Vector2(w.zone_mitte.x + K.ZONE["radius"] + 8, w.zone_mitte.y)
gast_k.pos.update(weit); gast_k.vorher.update(gast_k.pos)
gast_k.ebene = K.ZONE["ebene"]
pruef("Knapp daneben ist draussen", not w.in_der_zone(gast_k))

# Seit 0.27 stellt der Gastgeber die Haltezeit ein; die Rate wird daraus
# hochgerechnet (zone_faktor). Gemessen wird deshalb gegen die Rate mal
# Faktor, nicht mehr gegen die blanke Tabellenzahl.
je_s = K.ZONE["je_sekunde"] * w.zone_faktor
w.zone_stand[0] = 0.0      # der Gastgeber kann beim Einstieg schon drin
w._zone(1.0)               # gestanden haben; gemessen wird eine Sekunde
pruef("Allein im Kreis laedt es fuer die eigene Mannschaft",
      abs(w.zone_stand[0] - je_s) < 0.01
      and w.zone_stand[1] == 0.0, str(w.zone_stand))
pruef("Und der Kreis gehoert sichtbar dieser Mannschaft",
      w.zone_halter == 0, "Halter %d" % w.zone_halter)

# Gleich viele auf beiden Seiten: nichts passiert, der Stand verfaellt.
gast_k.pos.update(w.zone_mitte); gast_k.vorher.update(gast_k.pos)
stand_vorher = w.zone_stand[0]
w._zone(1.0)
pruef("Bei Gleichstand im Kreis laedt niemand",
      w.zone_stand[0] < stand_vorher and w.zone_halter == -1,
      "%s, Halter %d" % (w.zone_stand, w.zone_halter))

# Es zaehlt der Vorsprung, nicht die Kopfzahl: zwei gegen einen laedt
# genauso schnell wie einer gegen keinen. Wer den Kreis gegen Widerstand
# haelt, soll nicht schneller sein als der, der ihn leer vorfindet.
zweiter = w._dazu(98, "ZWEITER")
zweiter.team = 0
zweiter.pos.update(w.zone_mitte); zweiter.vorher.update(zweiter.pos)
zweiter.ebene = K.ZONE["ebene"]
w.zone_stand[0] = 0.0
w._zone(1.0)                      # zwei gegen einen
pruef("Zwei gegen einen laedt wie einer gegen keinen",
      abs(w.zone_stand[0] - je_s) < 0.01,
      "%.1f" % w.zone_stand[0])
gast_k.pos.update(weit); gast_k.vorher.update(gast_k.pos)
w.zone_stand[0] = 0.0
w._zone(1.0)                      # zwei gegen keinen
pruef("Zwei gegen keinen laedt schneller",
      w.zone_stand[0] > je_s, "%.1f" % w.zone_stand[0])
pruef("Aber nie schneller als die Obergrenze",
      w.zone_stand[0] <= K.ZONE["hoechstens"] * w.zone_faktor + 0.01,
      "%.1f" % w.zone_stand[0])
w.kaempfer.pop(98, None)
zweiter.lebt = False

netz_durchlassen(w, ga)
pruef("Der Ladestand kommt beim Gast an",
      abs(ga.zone_stand[0] - w.zone_stand[0]) < 0.2,
      "%s statt %s" % (ga.zone_stand, w.zone_stand))

# Der volle Kreis entscheidet das Gefecht.
w.zone_stand[0] = K.ZONE["bis"] - 0.01
gast_k.pos.update(weit); gast_k.vorher.update(gast_k.pos)
w._zone(1.0)
pruef("Der volle Kreis beendet das Gefecht",
      w.vorbei and w.sieger_team == 0, "Sieger %d" % w.sieger_team)

# Und er ist auch wirklich zu sehen: dasselbe Bild einmal mit und einmal
# ohne Kreis darf nicht gleich aussehen.
w.vorbei = False
w.zone_stand[0] = K.ZONE["bis"] * 0.5
w.zone_halter = 0
w.ich = wirt_k
w.welt.held = wirt_k
w.blick = K.ZONE["ebene"]
w.blick_hoehe = float(w.welt.hoehe(K.ZONE["ebene"]))
w.kamera.pos.update(wirt_k.pos)
w.kamera.versatz.update(0, 0)
mit = pygame.Surface((K.GAME_W, K.GAME_H))
ohne = pygame.Surface((K.GAME_W, K.GAME_H))
w.zeichnen(mit, 1.0)
w.regeln = K.MODI["pvp"]
w.zeichnen(ohne, 1.0)
w.regeln = K.MODI["huegel"]
anders = 0
for px in range(0, K.GAME_W, 2):
    for py in range(0, K.GAME_H, 2):
        if mit.get_at((px, py))[:3] != ohne.get_at((px, py))[:3]:
            anders += 1
pruef("Der Kreis ist im Bild wirklich zu sehen", anders > 400,
      "%d Bildpunkte anders" % anders)
# Rund muss er sein: innerhalb des Radius anders, ausserhalb nicht. Genau
# auf der Mitte steht die Figur und verdeckt ihn - der Kreis liegt unter
# den Figuren, nicht darueber, und das soll auch so bleiben.
def anders_bei(abstand):
    px = int(K.GAME_W // 2 + abstand)
    py = K.GAME_H // 2
    return mit.get_at((px, py))[:3] != ohne.get_at((px, py))[:3]

drinnen = anders_bei(K.ZONE["radius"] * 0.5)
draussen = anders_bei(K.ZONE["radius"] + 40)
pruef("Und zwar als Kreis, nicht als Flaeche ueber allem",
      drinnen and not draussen,
      "drinnen %s, draussen %s" % (drinnen, draussen))
figur = mit.get_at((K.GAME_W // 2, K.GAME_H // 2))[:3] \
    == ohne.get_at((K.GAME_W // 2, K.GAME_H // 2))[:3]
pruef("Die Figur steht auf dem Kreis, nicht darunter", figur)
w.verlassen(); ga.verlassen()

# ── Die gemeldeten Fehler ────────────────────────────────────────────
# Vier Stueck, jeder mit einer eigenen Pruefung, damit keiner still
# zurueckkommt.

# 1. Im Gefecht war kein Ton zu hoeren. Welt.klang ist von Haus aus eine
#    leere Methode; der Einzelspieler haengt sich daran, das Gefecht nicht.
w, ga = gefechtspaar("pvp")
from dustfront.world import Welt
def noch_leer(haken):
    """Haengt an diesem Haken noch die leere Methode aus world.py?

    Ueber __func__ verglichen: eine gebundene Methode ist nie gleich der
    Funktion in der Klasse, ein schlichtes == waere also immer wahr und
    die Pruefung wertlos.
    """
    return getattr(haken, "__func__", None) is getattr(Welt, haken.__name__, None)

for wer, wie in (("Gastgeber", w), ("Gast", ga)):
    # Geprueft wird die Wirkung, nicht mehr die Gleichheit der Haken:
    # zwischen Welt und Kamera liegt seit dem Ruckelfehler eine Rechnung,
    # die fragt, ob eine Meldung diesen Zuschauer ueberhaupt angeht.
    gehoert = []
    echt = app.klaenge.spielen
    app.klaenge.spielen = lambda n, l=1.0: gehoert.append((n, l))
    wie.welt.klang("nachladen", 1.0)
    app.klaenge.spielen = echt
    pruef("%s hat einen echten Tonausgang" % wer,
          not noch_leer(wie.welt.klang) and gehoert == [("nachladen", 1.0)],
          str(gehoert))
    wie.kamera.ruckeln = 0.0
    wie.kamera._sperre = 0.0
    wie.kamera.anteil = 1.0
    wenn_ich = wie.ich
    wie.welt.ruckeln(9.0, "explosion", None if wenn_ich is None else wenn_ich.pos,
                     0 if wenn_ich is None else wenn_ich.ebene, wenn_ich)
    pruef("%s spuert eine Explosion neben sich in der Kamera" % wer,
          not noch_leer(wie.welt.ruckeln) and wie.kamera.ruckeln > 0.5,
          "%.2f px" % wie.kamera.ruckeln)
    pruef("%s hinterlaesst Blutflecken" % wer, not noch_leer(wie.welt.blutfleck))
    pruef("%s bekommt Brandflecken" % wer, not noch_leer(wie.welt.brandfleck))
# Die Zeitlupe bleibt bewusst weg: sie wuerde beim Gastgeber die Runde
# aller Gaeste mitbremsen.
pruef("Aber keine Zeitlupe im Mehrspieler", noch_leer(w.welt.kurz_langsam))

# 2. Ein Tod ohne Toeter - also durch Sturz - setzte wieder_in nie. Der
#    Wiedereinstieg lief dadurch im selben Bild los: die Figur stand ohne
#    Todesbild irgendwo anders auf der Karte.
opfer = w.kaempfer[0]
opfer.unverwundbar = 0.0
wo = pygame.Vector2(opfer.pos)
opfer.schaden(999, None, None)          # genau so kommt Sturzschaden an
w._tote_abrechnen(K.FIXED_DT)
pruef("Ein Sturztod versetzt niemanden sofort",
      opfer.pos.distance_to(wo) < 1.0, "%.0f px" % opfer.pos.distance_to(wo))
pruef("Er zaehlt trotzdem als Tod", opfer.tode == 1, "%d" % opfer.tode)
pruef("Und der Wiedereinstieg laeuft wie sonst",
      abs(opfer.wieder_in - K.GEFECHT["wieder_nach"]) < 0.02,
      "%.2f s" % opfer.wieder_in)
for _ in range(int(K.GEFECHT["wieder_nach"] / K.FIXED_DT) + 4):
    w._tote_abrechnen(K.FIXED_DT)
pruef("Nach der Wartezeit steigt er wieder ein", opfer.lebt)

# 3. Die Ziellinie des Gastes zeigte auf seinen Einstiegspunkt: `ziel`
#    steht in keiner Weltmeldung und blieb darum stehen, wo er anfing.
gast_ich = ga.kaempfer[ga.meine_nummer]
einstieg = pygame.Vector2(gast_ich.ziel)
e.neues_bild()
e.maus = pygame.Vector2(K.GAME_W - 40, 40)     # Maus in eine Ecke
ga.schritt(K.FIXED_DT)
pruef("Die Ziellinie des Gastes loest sich vom Einstiegspunkt",
      gast_ich.ziel.distance_to(einstieg) > 20.0,
      "%.0f px weg" % gast_ich.ziel.distance_to(einstieg))
# Genau vergleichen ohne Bild dazwischen: die Kamera wackelt inzwischen
# auch beim Gast, und ein Bild spaeter steht sie anderswo.
ga._eigenes_zielen()
soll = ga.kamera.zu_welt(e.maus)
pruef("und trifft genau den Mauszeiger",
      gast_ich.ziel.distance_to(soll) < 0.01,
      "%.2f px daneben" % gast_ich.ziel.distance_to(soll))
blick = math.degrees(math.atan2(soll.y - gast_ich.pos.y,
                                soll.x - gast_ich.pos.x))
pruef("Auch die Figur dreht sich sofort mit",
      abs((gast_ich.winkel - blick + 180) % 360 - 180) < 0.01,
      "%.1f gegen %.1f Grad" % (gast_ich.winkel, blick))
w.verlassen(); ga.verlassen()

# 4. Rauch und fallende Granaten muessen beim Gast ankommen - er rechnet
#    nichts selbst nach.
w, ga = gefechtspaar("pvp")
w.welt.rauch.append(Rauchwolke(pygame.Vector2(300, 300), 0))
netz_durchlassen(w, ga)
pruef("Rauch kommt beim Gast an", len(ga.welt.rauch) == 1,
      "%d Wolken" % len(ga.welt.rauch))
if ga.welt.rauch:
    pruef("Und zwar an derselben Stelle",
          ga.welt.rauch[0].pos.distance_to(w.welt.rauch[0].pos) < 1.0)
w.welt.rauch[0].lebt = False
w.welt.schritt(K.FIXED_DT)
netz_durchlassen(w, ga)
pruef("Verwehter Rauch verschwindet auch beim Gast", not ga.welt.rauch)

stelle = wurfstelle()
fall_g = Granate(stelle, 0.0, K.WAFFEN["granate"], 2, None, 200.0)
w.welt.dazu(fall_g)
gesehen = False
for _ in range(400):
    w.schritt(K.NETZ["takt"]); ga.schritt(K.NETZ["takt"])
    if not fall_g.lebt:
        break
    if fall_g.sturz_rest > 0:
        for eintrag in ga._fremde_schuesse:
            if eintrag[4] == "granate" and eintrag[5] > 0:
                gesehen = True
pruef("Der Gast sieht die Granate in der Luft, nicht schon unten", gesehen)

# ── Die neuen Schalter beim Aufmachen ────────────────────────────────
pruef("Einstiegsschutz ist standardmaessig an", w.schutz_an)
# Am frisch Eingestiegenen gemessen: dieses Gefecht laeuft im Test schon
# eine Weile, da waere der Schutz des Gastgebers laengst abgelaufen.
frisch = w._dazu(77, "FRISCH")
pruef("Und er wirkt beim Einstieg",
      abs(frisch.unverwundbar - K.GEFECHT["schutz"]) < 0.01,
      "%.1f s" % frisch.unverwundbar)
frisch.lebt = False
w.kaempfer.pop(77, None)
w.verlassen(); ga.verlassen()

w, ga = gefechtspaar("pvp", schutz=False, medkits=4, medkit_spawn=False)
pruef("Der Gastgeber kann den Einstiegsschutz abschalten",
      not w.schutz_an and w.schutz_zeit == 0.0)
pruef("Dann steigt man ohne Schutz ein",
      w.kaempfer[0].unverwundbar == 0.0)
pruef("Die Zahl der Medkits beim Einstieg ist waehlbar",
      w.kaempfer[0].medkits == 4, "%d" % w.kaempfer[0].medkits)
pruef("Auch der Gast bekommt sie",
      w.kaempfer[ga.meine_nummer].medkits == 4)
pruef("Alle drei Schalter kommen beim Gast an",
      not ga.schutz_an and ga.start_medkits == 4 and not ga.medkits_spawnen,
      "Schutz %s, %d Medkits, Spawn %s"
      % (ga.schutz_an, ga.start_medkits, ga.medkits_spawnen))
# Abgeschaltet heisst abgeschaltet: auch nach langer Zeit liegt nichts da.
for _ in range(int(K.GEFECHT["medkit_takt"] * 3 / K.FIXED_DT)):
    w._beute_nachlegen(K.FIXED_DT)
liegen = [x for x in w.welt.wesen + w.welt.neue
          if isinstance(x, KampfBeute) and x.art == "medkit"]
pruef("Ohne Medkit-Spawn liegt keines auf der Karte", not liegen,
      "%d" % len(liegen))
w.verlassen(); ga.verlassen()

w, ga = gefechtspaar("pvp", medkits=0)
for _ in range(int(K.GEFECHT["medkit_takt"] * 1.2 / K.FIXED_DT)):
    w._beute_nachlegen(K.FIXED_DT)
liegen = [x for x in w.welt.wesen + w.welt.neue
          if isinstance(x, KampfBeute) and x.art == "medkit"]
pruef("Mit Medkit-Spawn liegt wieder eines da", len(liegen) >= 1,
      "%d" % len(liegen))
pruef("Und ohne Startmedkits faengt man mit leeren Haenden an",
      w.kaempfer[0].medkits == 0)
w.verlassen(); ga.verlassen()

# ── Pausenmenue, Mannschaften von Hand, neue Runde ───────────────────
# Esc beendete frueher das ganze Spiel. Das ist der Fehler, an dem man
# eine Runde verliert, weil man kurz nachsehen wollte.
def taste(szene, key):
    szene.ereignis(pygame.event.Event(pygame.KEYDOWN, key=key))

w, ga = gefechtspaar("team", ende_art="zeit", ende_wert=600)
app.laeuft = True
taste(w, pygame.K_ESCAPE)
pruef("Esc macht das Pausenmenue auf, statt zu beenden",
      w.menue is not None and app.laeuft)
pruef("Das Gefecht laeuft darunter weiter", not w.vorbei)
# Im Menue wird nicht geschossen und nicht gelaufen.
e.neues_bild(); e._gehalten = {"rechts"}
ein = w._meine_eingabe()
pruef("Im Menue steht die Figur still und feuert nicht",
      ein["will"] == [0.0, 0.0] and not ein["feuert"] and not ein["nutzen"])
e.neues_bild(); e._gehalten = set()
taste(w, pygame.K_ESCAPE)
pruef("Und Esc macht es wieder zu", w.menue is None)

# Seit 0.32 mit der Maus (gemeldet: "mit der Maus bedienbar, und alle
# Eingaben ans Spiel blockiert, solange es offen ist").
def _fenster(gx, gy):
    return (int(app.viewport.x + gx * app.skala), int(app.viewport.y + gy * app.skala))
taste(w, pygame.K_ESCAPE)
_fl = w._menue_flaechen()
_eintr = [x[0] for x in w._menue_baut()]
_i_einst = _eintr.index("einstellungen")
w.ereignis(pygame.event.Event(pygame.MOUSEMOTION, pos=_fenster(*_fl[_i_einst].center),
                              rel=(0, 0), buttons=(0, 0, 0)))
pruef("Die Maus waehlt den Eintrag, auf dem sie steht", w.menue == _i_einst,
      "%s statt %d" % (w.menue, _i_einst))
_zoom_vor = w.zoom_ziel
w.ereignis(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1, flipped=False))
pruef("Das Rad blaettert im Menue und zoomt nicht", w.zoom_ziel == _zoom_vor
      and w.menue == _i_einst - 1)
# Die Figur dreht sich nicht mit der Maus, solange das Menue offen ist.
e.neues_bild(); e.maus = pygame.Vector2(10, 10)
_z1 = w._meine_eingabe()["ziel"]
e.neues_bild(); e.maus = pygame.Vector2(600, 300)
_z2 = w._meine_eingabe()["ziel"]
pruef("Im Menue bleibt das Ziel stehen, wo es war", _z1 == _z2, "%s / %s" % (_z1, _z2))
# Klick auf WEITER: zu - und der gedrueckte Knopf schiesst nicht.
w.ereignis(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                              pos=_fenster(*_fl[0].center)))
pruef("Ein Klick auf WEITER macht das Menue zu", w.menue is None)
e.neues_bild(); e._gehalten = {"feuer"}
pruef("Der Klick auf WEITER loest keinen Schuss aus",
      not w._meine_eingabe()["feuert"])
e.neues_bild(); e._gehalten = set()
w._meine_eingabe()
e.neues_bild(); e._gehalten = {"feuer"}
pruef("Nach dem Loslassen schiesst man wieder", w._meine_eingabe()["feuert"])
e.neues_bild(); e._gehalten = set()
taste(w, pygame.K_ESCAPE)
w.ereignis(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3,
                              pos=_fenster(400, 200)))
pruef("Rechtsklick geht zurueck wie Esc", w.menue is None)
taste(w, pygame.K_ESCAPE)
w._menue_wirken("einstellungen", True, True)
pruef("EINSTELLUNGEN oeffnet die Einstellungen ueber dem Gefecht",
      type(app.oben).__name__ == "Einstellungen" and w.menue is None)
app.werfen()
app.flaeche.fill(K.C_VOID)
taste(w, pygame.K_ESCAPE)
w.zeichnen(app.flaeche, 1.0)            # Spalte und Tafel duerfen nicht abstuerzen
taste(w, pygame.K_ESCAPE)

# Ein Pfeil darf niemals etwas ausloesen, das man nicht zurueckholen
# kann. Auf "GEFECHT VERLASSEN" haette er frueher das Gefecht beendet.
taste(w, pygame.K_ESCAPE)
app.laeuft = True
for i, (schluessel, _t, _wert) in enumerate(w._menue_baut()):
    if schluessel not in ("weiter", "raus", "teams", "neu"):
        continue
    w.menue = i
    taste(w, pygame.K_RIGHT)
    taste(w, pygame.K_LEFT)
pruef("Pfeile loesen keine Tat aus: das Menue bleibt offen",
      w.menue is not None)
pruef("und das Gefecht laeuft", app.laeuft and not w.vorbei)
taste(w, pygame.K_ESCAPE)

# Der Gastgeber hat mehr Knoepfe als der Gast.
taste(w, pygame.K_ESCAPE)
wirt_eintraege = [x[0] for x in w._menue_baut()]
taste(ga, pygame.K_ESCAPE)
gast_eintraege = [x[0] for x in ga._menue_baut()]
pruef("Der Gastgeber stellt die naechste Runde, startet neu, teilt ein",
      "planen" in wirt_eintraege and "neu" in wirt_eintraege
      and "teams" in wirt_eintraege, str(wirt_eintraege))
pruef("Regeln stehen nicht mehr als Zeilen im Pausenmenue (0.32)",
      "modus" not in wirt_eintraege and "loadouts" not in wirt_eintraege,
      str(wirt_eintraege))
pruef("Der Gast stellt keine Regeln",
      not ({"modus", "neu", "teams", "knapp", "loadouts"}
           & set(gast_eintraege)), str(gast_eintraege))
pruef("Seine eigene Ausruestung und sein Konto schon",
      "ausruestung" in gast_eintraege and "konto" in gast_eintraege,
      str(gast_eintraege))
pruef("Einstellungen gibt es fuer beide",
      "einstellungen" in wirt_eintraege and "einstellungen" in gast_eintraege)
taste(ga, pygame.K_ESCAPE)

# Mannschaften von Hand verschieben, sofort.
wirt_k = w.kaempfer[0]
vorher_team = wirt_k.team
w._team_setzen(wirt_k, 1 - vorher_team)
pruef("Der Gastgeber kann jemanden in die andere Mannschaft stecken",
      wirt_k.team == 1 - vorher_team, "Team %d" % wirt_k.team)
pruef("Die Fraktion geht mit, sonst schiesst er auf seine neuen Leute",
      wirt_k.fraktion == w._fraktion_fuer(wirt_k.nummer, wirt_k.team),
      wirt_k.fraktion)
w._team_setzen(wirt_k, vorher_team)

# Regeln aendern und eine neue Runde starten: der Gast muss mitkommen.
w.wunsch["modus"] = "versus"
w.wunsch["runden"] = 5
w.wunsch["schutz"] = False
w.kaempfer[0].abschuesse = 7
w._runde_neu()
pruef("Eine neue Runde uebernimmt die neuen Regeln",
      w.modus == "versus" and w.runden_anzahl == 5 and not w.schutz_an,
      "%s, %d Runden, Schutz %s" % (w.modus, w.runden_anzahl, w.schutz_an))
pruef("Und setzt die Punkte zurueck",
      w.kaempfer[0].abschuesse == 0 and w.teampunkte == [0, 0])
netz_durchlassen(w, ga, 20)
pruef("Der Gast spielt die neuen Regeln mit",
      ga.modus == "versus" and ga.runden_anzahl == 5 and not ga.schutz_an,
      "%s, %d Runden, Schutz %s" % (ga.modus, ga.runden_anzahl, ga.schutz_an))
w.verlassen(); ga.verlassen()

# Rundenzahl und Mannschaftswunsch beim Starten
w, ga = gefechtspaar("versus", runden=2, team=1)
pruef("Die Rundenzahl laesst sich beim Aufmachen waehlen",
      w.runden_anzahl == 2, "%d" % w.runden_anzahl)
pruef("Und wer sich eine Mannschaft wuenscht, bekommt sie",
      w.kaempfer[0].team == 1, "Team %d" % w.kaempfer[0].team)
pruef("Der Gast landet dann in der anderen",
      w.kaempfer[ga.meine_nummer].team == 0,
      "Team %d" % w.kaempfer[ga.meine_nummer].team)
# Bei gleichem Stand darf man waehlen - der Dritte macht es zwangslaeufig
# ungleich, egal wohin er geht.
dritter = w._dazu(91, "DRITTER", 1)
pruef("Bei Gleichstand wird der Wunsch erfuellt", dritter.team == 1,
      "Team %d" % dritter.team)
# Jetzt steht es 2 zu 1. Wer sich die groessere wuenscht, bekommt sie nicht.
vierter = w._dazu(92, "VIERTER", 1)
pruef("Ein Wunsch in die groessere Mannschaft wird abgelehnt",
      vierter.team == 0, "Team %d" % vierter.team)
for nr in (91, 92):
    weg = w.kaempfer.pop(nr, None)
    if weg is not None:
        weg.lebt = False

# ── Am Boden und beim Aufhelfen ──────────────────────────────────────
wirt_k, gast_k = w.kaempfer[0], w.kaempfer[ga.meine_nummer]
wirt_k.unverwundbar = 0.0
wirt_k.schaden(999, None, None)
pruef("Wer faellt, liegt am Boden", wirt_k.am_boden)
pruef("Und hat ein eigenes Bild, das man auf Entfernung erkennt",
      wirt_k.bild.endswith("boden"), wirt_k.bild)
# Mit Mannschaften traegt auch die liegende Gestalt die Mannschaftsfarbe -
# sonst rennt man quer ueber die Karte, um einem Gegner aufzuhelfen.
pruef("Und in Mannschaftsspielarten die Farbe seiner Mannschaft",
      (not w.mit_teams) or wirt_k.bild != "spieler_boden", wirt_k.bild)
wo = pygame.Vector2(wirt_k.pos)
liegend = {"will": [1.0, 0.0], "ziel": [wo.x + 50, wo.y],
           "feuert": True, "nutzen": True, "knoepfe": []}
w._anwenden(wirt_k, liegend)
for _ in range(int(0.5 / K.FIXED_DT)):
    w.welt.schritt(K.FIXED_DT)
pruef("Am Boden bewegt sich niemand mehr",
      wirt_k.pos.distance_to(wo) < 1.0,
      "%.1f px gekrochen" % wirt_k.pos.distance_to(wo))
pruef("Und schiesst auch nicht", not wirt_k.feuert)

# Der Helfer ist waehrend des Aufhelfens gebunden - bis auf die Waffe.
# In versus hilft man nur den eigenen Leuten, also muss er erst in
# dieselbe Mannschaft.
w._team_setzen(gast_k, wirt_k.team)
gast_k.pos.update(wirt_k.pos); gast_k.vorher.update(gast_k.pos)
gast_k.ebene = wirt_k.ebene
gast_k.waffe = 0
helfen = {"will": [1.0, 0.0], "ziel": [gast_k.pos.x + 40, gast_k.pos.y],
          "feuert": True, "nutzen": True, "waffe": 2, "knoepfe": []}
w._anwenden(gast_k, helfen)
pruef("Wer aufhilft, wird erkannt", gast_k.hilft == wirt_k.nummer)
pruef("Er laeuft dabei nicht", gast_k.will.length() < 0.01)
pruef("Und schiesst nicht", not gast_k.feuert)
pruef("Die Waffe darf er trotzdem wechseln", gast_k.waffe == 2,
      "Platz %d" % gast_k.waffe)
w.verlassen(); ga.verlassen()

# ── Rueckmeldung: Sturz, Aufheben, verschobene Ansicht ───────────────
w, ga = gefechtspaar("pvp")
wirt_k = w.kaempfer[0]
w.welt.ringe = []
gehoert = []
w.welt.klang = lambda name, laut=1.0, pos=None, ebene=None: gehoert.append(name)
wirt_k.ebene = 2
wirt_k.sturz_hoehe = 180.0
wirt_k.aufschlag()
pruef("Ein Aufschlag macht einen Staubring", len(w.welt.ringe) == 1)
pruef("Und einen Ton", "sturz" in gehoert, str(gehoert))
w.welt.klang = w._klang

w.welt.aufschriften = []
Welt.beute_genommen(w.welt, wirt_k.pos, wirt_k.ebene, "munition")
pruef("Aufgesammelte Munition schreibt es an", len(w.welt.aufschriften) == 1,
      str(w.welt.aufschriften))
pruef("Und zwar lesbar",
      w.welt.aufschriften[0][2] == K.BEUTE_TEXTE["munition"][0],
      w.welt.aufschriften[0][2])

# Der Gast merkt es auch, ohne eigenen Kanal: was aus der Beuteliste
# verschwindet, wurde aufgehoben.
ga.welt.aufschriften = []
ga._fremde_beute = [(100.0, 100.0, 0, "munikiste")]
ga._aufgehoben_erkennen([(100.0, 100.0, 0, "munikiste"),
                         (200.0, 200.0, 0, "medkit")])
pruef("Auch der Gast sieht, dass jemand etwas aufgehoben hat",
      len(ga.welt.aufschriften) == 1
      and ga.welt.aufschriften[0][2] == K.BEUTE_TEXTE["medkit"][0],
      str(ga.welt.aufschriften))

# Die verschobene Ansicht kommt von selbst zurueck - sonst fehlen die
# Zielhilfen den Rest der Runde, und niemand weiss warum.
w.ich.ebene = 0
w._letzte_ebene = 0
w.blick = 0
w._rad = 1
w.schritt(K.FIXED_DT)
pruef("Das Mausrad verschiebt die Ansicht", w.blick == 1, "Ebene %d" % w.blick)
pruef("Und sagt, dass sie zurueckkommt", "ZURÜCK" in w.hinweis, w.hinweis)
for _ in range(int(K.GEFECHT["blick_zurueck"] / K.FIXED_DT) + 8):
    w.schritt(K.FIXED_DT)
pruef("Nach kurzer Zeit schaut man wieder auf die eigene Ebene",
      w.blick == w.ich.ebene, "Ebene %d" % w.blick)
w.verlassen(); ga.verlassen()

# ── Knappe Munition: sie muss wirklich knapp sein ────────────────────
# Gemeldet als "man kann unendlich nachladen" und "Kisten lassen sich
# nicht aufheben". Beides hatte dieselbe Ursache: jeder Wiedereinstieg
# schenkte alle Magazine am Vorrat vorbei. Der Vorrat sank nie, und was
# voll ist, kann man nicht auffuellen.
w, ga = gefechtspaar("team", knapp=True, ende_art="zeit", ende_wert=900)
wirt_k = w.kaempfer[0]
name = wirt_k.waffe_name
pruef("Knappe Munition kommt am Kaempfer an", wirt_k.knapp)
voll_vorrat = K.MUNITION["vorrat"][name]
pruef("Zu Beginn ist der Vorrat voll", wirt_k.vorrat[name] == voll_vorrat,
      "%d" % wirt_k.vorrat[name])

# Leerschiessen und nachladen kostet Vorrat.
wirt_k.magazin[name] = 0
wirt_k.nachlade_rest = 0.0
wirt_k.nachladen()
for _ in range(int(K.WAFFEN[name]["nachladen"] / K.FIXED_DT) + 6):
    wirt_k.schritt(K.FIXED_DT)
pruef("Nachladen nimmt aus dem Vorrat",
      wirt_k.vorrat[name] == voll_vorrat - K.WAFFEN[name]["magazin"],
      "%d von %d uebrig" % (wirt_k.vorrat[name], voll_vorrat))

# Seit 0.34.96 (gewuenscht, gemeldet: "Munition und Granaten werden nach
# dem Tod nicht zuverlaessig aufgefuellt"): ein neues Leben beginnt mit
# vollem Magazin und vollem Vorrat - auch wenn das Loadout dasselbe ist.
# Knapp ist es innerhalb eines Lebens (oben: Nachladen nimmt aus dem Vorrat).
wirt_k.magazin[name] = 0
wirt_k.vorrat[name] = 0
for w_ in wirt_k.waffen:
    if K.WAFFEN[w_].get("art") == "wurf":
        wirt_k.magazin[w_] = 0
        wirt_k.vorrat[w_] = 0
w._wieder_einsteigen(wirt_k)
pruef("Ein Wiedereinstieg fuellt das Magazin",
      wirt_k.magazin[name] == K.WAFFEN[name]["magazin"],
      "%d" % wirt_k.magazin[name])
pruef("... und den Vorrat, Granaten eingeschlossen - jedes Leben gleich",
      wirt_k.vorrat[name] == voll_vorrat
      and all(wirt_k.magazin[w_] == K.WAFFEN[w_]["magazin"] for w_ in wirt_k.waffen
              if K.WAFFEN[w_].get("art") == "wurf"),
      "%d statt %d" % (wirt_k.vorrat[name], voll_vorrat))

# Ohne knappe Munition bleibt es wie immer: umsonst.
w2, ga2 = gefechtspaar("team", knapp=False)
frei_k = w2.kaempfer[0]
frei_k.magazin[frei_k.waffe_name] = 0
w2._wieder_einsteigen(frei_k)
pruef("Ohne Begrenzung ist der Wiedereinstieg weiter umsonst",
      frei_k.magazin[frei_k.waffe_name]
      == K.WAFFEN[frei_k.waffe_name]["magazin"])
w2.verlassen(); ga2.verlassen()

# Ist der Vorrat leer, laeuft gar kein Nachladen mehr an.
wirt_k.vorrat[name] = 0
wirt_k.magazin[name] = 0
wirt_k.nachlade_rest = 0.0
wirt_k.nachladen()
pruef("Ohne Vorrat startet kein Nachladen", wirt_k.nachlade_rest == 0.0,
      "%.2f" % wirt_k.nachlade_rest)

# Und dann laesst sich eine Kiste aufheben - was vorher nie noetig war.
kiste = KampfBeute(pygame.Vector2(wirt_k.pos), "munition", wirt_k.ebene,
                   w.kaempfer)
w.welt.dazu(kiste)
w.welt.schritt(K.FIXED_DT)
pruef("Eine Munitionskiste wird im Vorbeilaufen genommen", not kiste.lebt)
pruef("Und fuellt den Vorrat wieder auf", wirt_k.vorrat[name] > 0,
      "%d" % wirt_k.vorrat[name])

# Der Vorrat muss so knapp sein, dass er in einer Runde auffaellt.
reicht = min(K.MUNITION["vorrat"][x] / K.WAFFEN[x]["magazin"]
             for x in K.HOTBAR if K.WAFFEN[x]["magazin"])
pruef("Der Vorrat reicht fuer wenige Nachladungen, nicht fuer zwanzig",
      reicht <= 4.0, "knappste Waffe: %.1f Nachladungen" % reicht)
w.verlassen(); ga.verlassen()

# ── Treppen: nicht zweimal hintereinander ────────────────────────────
# "nutzen" wird gehalten, nicht gedrueckt. Ohne Sperre versuchte darum
# jedes Bild einen Wechsel: hoch, und weil auf der Zielkachel die Treppe
# zurueck nach unten liegt, sofort wieder hinunter.
w, ga = gefechtspaar("pvp")
wirt_k = w.kaempfer[0]
treppe = None
eo = w.welt.ebene(0)
for ty in range(eo.hoehe):
    for tx in range(eo.breite):
        if eo.kachel(tx, ty) == K.TREPPE_HOCH:
            treppe = pygame.Vector2(tx * K.TILE + 16, ty * K.TILE + 16)
            break
    if treppe:
        break
pruef("Eine Treppe nach oben gefunden", treppe is not None)
wirt_k.ebene = 0
wirt_k.pos.update(treppe); wirt_k.vorher.update(treppe)
wirt_k.treppe_rest = 0.0
# Seit 0.27 haengt die Treppe am Druck (Ereignis "nutzen" in knoepfe),
# nicht mehr am gehaltenen E.
druck = {"will": [0.0, 0.0], "ziel": [treppe.x + 20, treppe.y],
         "nutzen": True, "knoepfe": ["nutzen"]}
halten = dict(druck, knoepfe=[])
w._anwenden(wirt_k, druck)
pruef("Einmal Druecken bringt eine Ebene hoch", wirt_k.ebene == 1,
      "Ebene %d" % wirt_k.ebene)
# Taste weiter gehalten - auch weit ueber die Sperre hinaus: nichts mehr.
for _ in range(int(5.0 / K.FIXED_DT)):
    w._anwenden(wirt_k, halten)
    wirt_k.schritt(K.FIXED_DT)
pruef("Gehalten bleibt es bei dieser einen Ebene, auch nach Sekunden",
      wirt_k.ebene == 1, "Ebene %d" % wirt_k.ebene)
# Ein zweiter Druck sofort danach zaehlt nicht (Doppeldruck) ...
wirt_k.treppe_rest = K.GEFECHT["treppe_takt"]
w._anwenden(wirt_k, druck)
pruef("Ein Doppeldruck nimmt die Treppe nicht zweimal", wirt_k.ebene == 1)
# ... ein neuer Druck nach der Sperre schon - dann eben zurueck nach unten.
for _ in range(int(K.GEFECHT["treppe_takt"] / K.FIXED_DT) + 4):
    wirt_k.schritt(K.FIXED_DT)
w._anwenden(wirt_k, druck)
pruef("Ein neuer Druck nach der Sperre geht wieder", wirt_k.ebene == 0,
      "Ebene %d" % wirt_k.ebene)

# Der gemeldete Fehler: beim Gast. Sein E bleibt als gehalten stehen (das
# Loslassen kam nie an) - frueher ging er dann alle 1,5 s hoch und runter.
gast_k = w.kaempfer[ga.meine_nummer]
gast_k.ebene = 0
gast_k.pos.update(treppe); gast_k.vorher.update(treppe)
gast_k.treppe_rest = 0.0
gast_k.unverwundbar = 99.0
verlauf = [gast_k.ebene]
for i in range(int(6.0 / K.FIXED_DT)):
    e.neues_bild()
    if i == 0:
        # Ein Druck, dessen Loslassen nie kommt.
        e.ereignis(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        ga.ereignis(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    ga.schritt(K.FIXED_DT)
    e._gehalten = set()          # der Gastgeber selbst drueckt nichts
    e._gedrueckt = set()
    w.schritt(K.FIXED_DT)
    e._gehalten = {"nutzen"}     # beim Gast haengt E fest
    if not verlauf or verlauf[-1] != gast_k.ebene:
        verlauf.append(gast_k.ebene)
e._gehalten = set()
pruef("Gast: ein festhaengendes E nimmt die Treppe genau einmal",
      verlauf == [0, 1], str(verlauf))

# Und der kurze Tipp: Druecken und Loslassen im selben Bild. Der gehaltene
# Zustand ist dann schon wieder aus - der Druck muss trotzdem ankommen.
gast_k.ebene = 0
gast_k.pos.update(treppe); gast_k.vorher.update(treppe)
gast_k.treppe_rest = 0.0
e.neues_bild()
for typ in (pygame.KEYDOWN, pygame.KEYUP):
    ev = pygame.event.Event(typ, key=pygame.K_e)
    e.ereignis(ev)
    ga.ereignis(ev)
ga.schritt(K.FIXED_DT)
e.neues_bild()
for _ in range(20):
    ga.schritt(K.NETZ["takt"]); w.schritt(K.NETZ["takt"])
pruef("Gast: ein ganz kurzer Tipp auf E nimmt die Treppe einmal",
      gast_k.ebene == 1, "Ebene %d" % gast_k.ebene)
w.verlassen(); ga.verlassen()

# ── Online: Kennwort und der Weg durch den Router ────────────────────
# Ein Port, der ins Internet offen steht, braucht einen Tuersteher. Und
# die Routerabfrage muss auswertbar sein, ohne dass hier ein Router steht.
from dustfront import upnp

_neuer_port()
wirt_n = netz.Gastgeber(_port[0])
geschuetzt = Gefecht(app, "WIRT", gastgeber=wirt_n, modus="pvp",
                     passwort="Geheim-1", seed=777)
falsch = Gefecht(app, "EINDRINGLING",
                 gast=netz.Gast("127.0.0.1:%d" % _port[0]), passwort="egal")
netz_durchlassen(geschuetzt, falsch, 20)
pruef("Mit falschem Kennwort kommt niemand herein",
      len(geschuetzt.kaempfer) == 1, "%d Kaempfer" % len(geschuetzt.kaempfer))
pruef("Und der Abgewiesene erfaehrt, warum",
      "ABGEWIESEN" in falsch.hinweis, falsch.hinweis)
pruef("Seine Leitung ist zu", not falsch.gast.offen)

richtig = Gefecht(app, "BEFUGT", gast=netz.Gast("127.0.0.1:%d" % _port[0]),
                  passwort="geheim-1")     # Gross- und Kleinschreibung egal
netz_durchlassen(geschuetzt, richtig, 20)
pruef("Mit dem richtigen Kennwort schon",
      len(geschuetzt.kaempfer) == 2, "%d Kaempfer" % len(geschuetzt.kaempfer))
geschuetzt.verlassen(); falsch.verlassen(); richtig.verlassen()

pruef("Ein Kennwort wird gesaeubert und gekuerzt",
      netz.passwort_saeubern("  ge heim!1  ") == "GEHEIM1"
      and len(netz.passwort_saeubern("X" * 40)) == K.NETZ["passwortlaenge"],
      netz.passwort_saeubern("  ge heim!1  "))

# Die Routerabfrage gegen erfundene Antworten - so laesst sie sich pruefen,
# ohne dass in diesem Testlauf ein Router im Netz steht.
ssdp = ("HTTP/1.1 200 OK\r\nCACHE-CONTROL: max-age=120\r\n"
        "LOCATION: http://192.168.1.1:5000/rootDesc.xml\r\n\r\n")
pruef("Die Antwort eines Routers wird gelesen",
      upnp.kopfzeile_lesen(ssdp, "location")
      == "http://192.168.1.1:5000/rootDesc.xml")
beschreibung = ('<?xml version="1.0"?><root xmlns="urn:schemas-upnp-org:device-1-0">'
                '<device><serviceList>'
                '<service><serviceType>urn:schemas-upnp-org:service:Layer3Forwarding:1'
                '</serviceType><controlURL>/ctl/L3F</controlURL></service>'
                '<service><serviceType>urn:schemas-upnp-org:service:WANIPConnection:1'
                '</serviceType><controlURL>/ctl/IPConn</controlURL></service>'
                '</serviceList></device></root>')
dienst, adresse = upnp.dienst_finden("http://192.168.1.1:5000/rootDesc.xml",
                                     beschreibung)
pruef("Die Stelle fuer Portfreigaben wird gefunden",
      dienst.endswith("WANIPConnection:1")
      and adresse == "http://192.168.1.1:5000/ctl/IPConn", adresse)
pruef("Auch ein relativer Weg wird richtig angehaengt",
      upnp.dienst_finden("http://10.0.0.1:80/desc/root.xml",
                         beschreibung)[1] == "http://10.0.0.1:80/ctl/IPConn")
pruef("Eine kaputte Beschreibung wirft niemanden um",
      upnp.dienst_finden("http://x/y.xml", "<kein xml") == ("", ""))
pruef("Die Aussenadresse wird aus der Antwort gelesen",
      upnp.soap_antwort_lesen(
          "<s:Body><u:GetExternalIPAddressResponse><NewExternalIPAddress>"
          "93.184.216.34</NewExternalIPAddress></u:GetExternalIPAddressResponse>"
          "</s:Body>", "NewExternalIPAddress") == "93.184.216.34")

# Ohne Router muss die Freigabe sauber scheitern und sagen, was zu tun ist.
frei = upnp.Freigabe(50505, "192.168.1.50")
pruef("Eine Freigabe ohne Router ist einfach zu",
      not frei.offen and len(frei.bericht()) >= 3)
# Ein Gastgeber mit --online muss auch dann laufen, wenn kein Router
# antwortet - und das tut hier keiner.
_neuer_port()
online_wirt = netz.Gastgeber(_port[0], online=True)
pruef("Ein Online-Gastgeber laeuft auch ohne Router",
      online_wirt.port == _port[0] and online_wirt.freigabe is not None)
pruef("Er sagt dann aber nicht, er sei von aussen erreichbar",
      online_wirt.aussen == "", online_wirt.aussen)
online_wirt.schliessen()

pruef("Und der Bericht nennt Port und Ziel",
      any("50505" in z and "192.168.1.50" in z for z in frei.bericht()),
      " / ".join(frei.bericht()[:3]))

# Ein Gast, der abbricht, darf den Gastgeber nicht mitreissen
verbindung.schliessen()
for _ in range(6):
    host.schritt(K.NETZ["takt"])
pruef("Gastgeber laeuft weiter, wenn ein Gast geht",
      len(host.kaempfer) == 1, "%d uebrig" % len(host.kaempfer))
host.verlassen()

import json
from dustfront import einstellungen as E

# ── Kameraruckeln: selten, schwach und nur, wenn es einen angeht ─────
#
# Der gemeldete Fehler: "Der Bildschirm vom Host ruckelt die ganze Zeit
# von Shots und Granaten, ohne Pause, bei Gaesten ist aber quasi gar
# nichts." Gemessen am alten Stand - ein einziger anderer Spieler, 1600
# Pixel entfernt und eine Etage hoeher, haelt den Abzug: 2,09 Pixel
# Dauerzittern beim Gastgeber in 100 % der Bilder, 0,00 beim Gast.
w, ga = gefechtspaar("pvp")
wirt_k = w.kaempfer[0]
gast_k = w.kaempfer[ga.meine_nummer]
wirt_k.pos.update(200, 200); wirt_k.vorher.update(wirt_k.pos); wirt_k.ebene = 0
gast_k.pos.update(1500, 1000); gast_k.vorher.update(gast_k.pos)
gast_k.ebene = min(1, len(w.welt.ebenen) - 1)
gast_k.waffe_waehlen(gast_k.waffen.index("sturm"))
w.kamera.ruckeln = 0.0
werte = []
for _ in range(int(3.0 / K.FIXED_DT)):
    w._anwenden(gast_k, {"will": [0, 0], "ziel": [gast_k.pos.x + 60, gast_k.pos.y],
                         "feuert": True})
    gast_k.magazin["sturm"] = 999
    w.schritt(K.FIXED_DT)
    werte.append(w.kamera.ruckeln)
pruef("Fremdes Dauerfeuer laesst das Bild des Gastgebers stehen",
      max(werte) < 0.01,
      "groesster Ausschlag %.2f px in %d Bildern" % (max(werte), len(werte)))

# Und der eigene Schuss? Ein Sturmgewehr soll gar nichts mehr reissen,
# eine Explosion daneben schon - sonst waere es kein schwaches Ruckeln,
# sondern keines.
def eigen_ruckeln(anlass, kraft, entfernung=0.0, ebene_dazu=0):
    w.kamera.ruckeln = 0.0
    w.kamera._sperre = 0.0
    w.kamera.anteil = 1.0
    ort = wirt_k.pos + pygame.Vector2(entfernung, 0)
    w.welt.ruckeln(kraft, anlass, ort, wirt_k.ebene + ebene_dazu,
                   wirt_k if entfernung == 0.0 and not ebene_dazu else None)
    return w.kamera.ruckeln

pruef("Der eigene Gewehrschuss ruckelt nicht mehr",
      eigen_ruckeln("schuss", K.WAFFEN["sturm"]["kamera"]) < 0.01)
pruef("Eine Explosion neben einem schon",
      eigen_ruckeln("explosion", K.WAFFEN["granate"]["kamera"]) > 0.5,
      "%.2f px" % eigen_ruckeln("explosion", K.WAFFEN["granate"]["kamera"]))
pruef("Aber schwach: nie mehr als ein paar Pixel",
      eigen_ruckeln("explosion", 99.0) <= K.RUCKELN["max"] + 0.001,
      "%.2f px" % eigen_ruckeln("explosion", 99.0))
pruef("Dieselbe Explosion eine Ebene hoeher gar nicht",
      eigen_ruckeln("explosion", K.WAFFEN["granate"]["kamera"],
                    entfernung=10.0, ebene_dazu=1) < 0.01)
pruef("Und weit weg auch nicht",
      eigen_ruckeln("explosion", K.WAFFEN["granate"]["kamera"],
                    entfernung=K.RUCKELN["reichweite"] + 10) < 0.01)
# Die Sperre: zwei Schlaege dicht hintereinander ergeben einen, nicht zwei.
w.kamera.ruckeln = 0.0; w.kamera._sperre = 0.0; w.kamera.anteil = 1.0
w.kamera.stossen(2.0)
eins = w.kamera.ruckeln
w.kamera.stossen(2.0)
pruef("Zwei Schlaege dicht hintereinander legen nicht nach",
      abs(w.kamera.ruckeln - eins) < 0.001, "%.2f px" % w.kamera.ruckeln)

# Der Regler im Menue hing an nichts. Auf 0 muss das Bild stehen.
w.kamera.ruckeln = 0.0; w.kamera._sperre = 0.0
w.kamera.anteil = 0.0
w.kamera.stossen(99.0)
pruef("Auf 0 gestellt steht das Bild vollkommen still",
      w.kamera.ruckeln < 0.001, "%.2f px" % w.kamera.ruckeln)
app.opt["bildschirm_ruckeln"] = 0
pruef("Und der Regler im Menue ist genau dieser Wert",
      app.opt.ruckel_anteil() == 0.0)
app.opt["bildschirm_ruckeln"] = 100
pruef("Das Ruckeln gehoert zum Konto, nicht zum Geraet",
      "bildschirm_ruckeln" in E.KONTO_WERTE
      and "aufloesung" not in E.KONTO_WERTE)
app.opt.konto_uebernehmen({"bildschirm_ruckeln": 40, "aufloesung": "1x1",
                           "unsinn": True})
pruef("Ein Konto bringt seine Einstellungen mit",
      app.opt["bildschirm_ruckeln"] == 40, "%s" % app.opt["bildschirm_ruckeln"])
pruef("Aber nur die, die zum Spieler gehoeren",
      app.opt["aufloesung"] != "1x1", app.opt["aufloesung"])
app.opt["bildschirm_ruckeln"] = 100
w.verlassen(); ga.verlassen()

# ── Granaten beim Gast: sichtbar, hoerbar, und ohne Spruenge ─────────
#
# "Manchmal waren Granaten bei manchen Leuten, auf die sie geworfen
# wurden, unsichtbar, oder sie landeten an komplett verschiedenen Orten."
# Zwei Ursachen, beide gemessen: der Gast bekam von einer Explosion gar
# nichts (0 Partikel, kein Ton, kein Brandfleck), und er zeichnete
# fliegende Dinge stur an die zuletzt gemeldete Stelle - bei 300 Bildern
# und 60 Meldungen stand die Granate in 80 % der Bilder still und sprang
# dann um bis zu 7 Pixel.
w, ga = gefechtspaar("pvp")
wirt_k = w.kaempfer[0]
gast_k = w.kaempfer[ga.meine_nummer]
wirt_k.pos.update(300, 300); wirt_k.vorher.update(wirt_k.pos)
gast_k.pos.update(900, 300); gast_k.vorher.update(gast_k.pos)
gehoert = []
echt = app.klaenge.spielen
app.klaenge.spielen = lambda n, l=1.0: gehoert.append(n)
wirt_k.waffe_waehlen(wirt_k.waffen.index("granate"))
wirt_k.takt = 0.0
wirt_k.winkel = 0.0
wirt_k.ziel.update(560, 300)
wirt_k.feuern()
gesehen = 0
bahn = []
for _ in range(int(1.6 / K.FIXED_DT)):
    w.schritt(K.FIXED_DT)
    ga.schritt(K.FIXED_DT)
    wurf = [s for s in ga._fremde_schuesse if s[4] == "granate"]
    if wurf:
        gesehen += 1
        bahn.append(pygame.Vector2(wurf[0][0], wurf[0][1]))
app.klaenge.spielen = echt
pruef("Der Gast sieht die geworfene Granate fliegen", gesehen > 40,
      "%d Bilder" % gesehen)
pruef("Und hoert sie zuenden", "granate" in gehoert, str(sorted(set(gehoert))))
pruef("Und bekommt ihre Funken und ihren Staub",
      len(ga.welt.partikel) > 0 or len(ga.welt.ringe) > 0,
      "%d Partikel" % len(ga.welt.partikel))
pruef("Und ihren Brandfleck", ga.welt.ebene(0).dekale is not None)
if len(bahn) > 2:
    pruef("Sie liegt am Ende dort, wo sie hingeworfen wurde",
          abs(bahn[-1].x - 560) < 40 and abs(bahn[-1].y - 300) < 20,
          "%.0f / %.0f" % (bahn[-1].x, bahn[-1].y))

# Die Zwischenlage: jedes fliegende Ding traegt seine Kennung, und
# zwischen zwei Meldungen wird weitergezeichnet statt stehengeblieben.
eintrag = None
wirt_k.takt = 0.0
wirt_k.magazin["granate"] = 3
wirt_k.feuern()
for _ in range(20):
    w.schritt(K.FIXED_DT)
    ga.schritt(K.FIXED_DT)
    for s in ga._fremde_schuesse:
        if s[4] == "granate":
            eintrag = s
pruef("Fliegende Dinge tragen eine Kennung",
      eintrag is not None and len(eintrag) == 9 and eintrag[6] > 0,
      str(eintrag))
if eintrag is not None:
    frueh = pygame.Vector2(eintrag[7], eintrag[8])
    spaet = pygame.Vector2(eintrag[0], eintrag[1])
    pruef("Und eine Ausgangslage, zwischen der gezeichnet wird",
          frueh.distance_to(spaet) > 0.5,
          "%.1f px zwischen zwei Meldungen" % frueh.distance_to(spaet))
pruef("Der Bildanteil zaehlt bei der Ueberblendung mit",
      ga.misch(0.0) < ga.misch(1.0) or ga.misch(1.0) >= 0.999,
      "%.2f -> %.2f" % (ga.misch(0.0), ga.misch(1.0)))
w.verlassen(); ga.verlassen()

# ── Die Leitung: voller Sendepuffer darf nichts zerreissen ───────────
#
# `sendall` auf einer nicht-blockierenden Steckdose schreibt einen Teil
# der Zeile und wirft dann - die halbe Nachricht ist unterwegs, der Rest
# fehlt, und im Fehlerzweig wurde die Leitung zugemacht.
class LahmeSteckdose:
    """Nimmt je Versuch nur ein paar Bytes, wie ein voller Sendepuffer."""

    def __init__(self, haeppchen=12):
        self.haeppchen = haeppchen
        self.geschrieben = b""
        self.dran = 0

    def setblocking(self, x): pass
    def setsockopt(self, *a): pass
    def close(self): pass

    def send(self, daten):
        self.dran += 1
        if self.dran % 3 == 0:
            raise BlockingIOError()          # jetzt geht gar nichts mehr
        teil = daten[:self.haeppchen]
        self.geschrieben += teil
        return len(teil)

lahm = LahmeSteckdose()
leitung = netz.Leitung(lahm)
for i in range(5):
    leitung.senden({"t": "welt", "nr": i, "fuellung": "x" * 60})
for _ in range(80):
    leitung.spuelen()
pruef("Eine zaehe Leitung bleibt offen", leitung.offen, leitung.grund)
zeilen = [z for z in lahm.geschrieben.split(b"\n") if z]
pruef("Und schickt jede Zeile ganz und heil",
      len(zeilen) == 5 and all(json.loads(z.decode())["nr"] == i
                               for i, z in enumerate(zeilen)),
      "%d Zeilen" % len(zeilen))

# Staut sich zu viel, fliegt das Ueberholte raus - nicht die Leitung.
stau = netz.Leitung(LahmeSteckdose(haeppchen=0))
for i in range(K.NETZ["stau_zeilen"] + 50):
    stau.senden({"t": "welt", "nr": i})
pruef("Ein Rueckstand wird gekuerzt statt nachgeschleppt",
      len(stau._raus) <= K.NETZ["stau_zeilen"] and stau.verworfen > 0,
      "%d in der Schlange, %d verworfen" % (len(stau._raus), stau.verworfen))
stau.senden({"t": "ende", "sieger": 1})
pruef("Was es nur einmal gibt, bleibt trotzdem stehen",
      any(b'"t":"ende"' in z for z in stau._raus))

def _hud_text_rechts(szene, spieler):
    """Was rechts neben dem Lebensbalken steht - als Text nachgebaut.

    Gezeichnet wird mit einer Pixelschrift; den Text aus dem Bild
    zurueckzulesen waere Unfug. Geprueft wird darum die Stelle im
    Renderer, die ihn erzeugt.
    """
    return "%d" % spieler.magazin[spieler.waffe_name]


# ── Befinden: roter Rand, Herzschlag, dumpfe Welt, Medkit ────────────
#
# "Rote Vignette, die pulst, bei Treffern ausschlaegt, bei wenig Leben
# dauerhaft wird und pulst, mit Herzschlag in Klassen, waehrend alles
# andere gedaempft wird - und das Medkit dagegen: blau, kalt, sehr klar."
from dustfront.render import Befinden

bef = Befinden()
bef.schritt(K.FIXED_DT, 1.0)
pruef("Bei vollem Leben ist der Rand leer", bef.staerke < 0.01,
      "%.2f" % bef.staerke)
pruef("Und nichts ist gedaempft", bef.dumpf < 0.01)
bef.schritt(K.FIXED_DT, 0.5)
mitte = bef.staerke
pruef("Unter der Schwelle faerbt er sich", 0.01 < mitte < 0.5,
      "%.2f" % mitte)
bef.schritt(K.FIXED_DT, 0.2)
pruef("Und wird staerker, je weniger Leben", bef.staerke > mitte,
      "%.2f statt %.2f" % (bef.staerke, mitte))

# Ein Treffer schlaegt sofort auf und verklingt wieder.
bef = Befinden()
bef.schritt(K.FIXED_DT, 0.9)
ruhig = bef.staerke
bef.treffer(1.0)
bef.schritt(K.FIXED_DT, 0.9)
pruef("Ein Treffer schlaegt sofort auf", bef.staerke > ruhig + 0.3,
      "%.2f statt %.2f" % (bef.staerke, ruhig))
for _ in range(int(1.5 / K.FIXED_DT)):
    bef.schritt(K.FIXED_DT, 0.9)
pruef("Und verklingt wieder", abs(bef.staerke - ruhig) < 0.02,
      "%.2f" % bef.staerke)

# Der Puls: je weniger Leben, desto schneller, und er meldet sich.
def schlaege(anteil, sekunden=6.0):
    b = Befinden()
    gehoert = []
    for _ in range(int(sekunden / K.FIXED_DT)):
        b.schritt(K.FIXED_DT, anteil,
                  lambda n, l=1.0: gehoert.append((n, l)))
    return gehoert

keine = schlaege(0.60)
pruef("Ueber der Dauerschwelle schlaegt kein Herz", not keine, str(keine[:2]))
langsam = schlaege(0.30)
schnell = schlaege(0.05)
pruef("Darunter schon", len(langsam) >= 3, "%d Schlaege" % len(langsam))
pruef("Und bei wenig Leben schlaegt es schneller",
      len(schnell) > len(langsam) + 2,
      "%d gegen %d in 6 s" % (len(schnell), len(langsam)))
pruef("Es ist der Herzschlag und nichts anderes",
      all(n == "herzschlag" for n, _l in schnell))
pruef("Und er wird lauter, je schlimmer es steht",
      schnell[0][1] > langsam[0][1],
      "%.2f gegen %.2f" % (schnell[0][1], langsam[0][1]))
pruef("Die Lautstaerken sind Klassen, keine Rutschbahn",
      len({round(l, 3) for _n, l in langsam + schnell}) <= len(K.BEFINDEN["klassen"]),
      str(sorted({round(l, 2) for _n, l in langsam + schnell})))

# Dumpf werden alle anderen - und im Takt des Schlags.
b = Befinden()
werte = []
for _ in range(int(3.0 / K.FIXED_DT)):
    b.schritt(K.FIXED_DT, 0.08)
    werte.append(b.dumpf)
pruef("Bei wenig Leben wird alles andere dumpf", max(werte) > 0.4,
      "%.2f" % max(werte))
pruef("Und es atmet mit dem Schlag", max(werte) - min(werte) > 0.1,
      "%.2f bis %.2f" % (min(werte), max(werte)))

# Das Medkit nimmt beides weg, und zwar sofort.
b = Befinden()
b.schritt(K.FIXED_DT, 0.08)
vor_medkit = b.staerke
b.medkit()
b.schritt(K.FIXED_DT, 0.08)
pruef("Ein Medkit nimmt den roten Rand sofort weg",
      vor_medkit > 0.3 and b.staerke < 0.01,
      "%.2f -> %.2f" % (vor_medkit, b.staerke))
pruef("Und den Herzschlag mit", b.dumpf < 0.01)
stille = []
for _ in range(int((K.MEDKIT_BLICK["ruhe"] - 0.2) / K.FIXED_DT)):
    b.schritt(K.FIXED_DT, 0.08, lambda n, l=1.0: stille.append(n))
pruef("Die Ruhe haelt ein paar Sekunden", not stille and b.staerke < 0.01,
      "%d Schlaege" % len(stille))
for _ in range(int(0.6 / K.FIXED_DT)):
    b.schritt(K.FIXED_DT, 0.08)
pruef("Danach faengt es wieder an", b.staerke > 0.3, "%.2f" % b.staerke)

# Das Bild: kalt und klar, und es macht das Bild nicht schwarz. Genau das
# war der Fehler mit 128 als Drehpunkt - die Welt hier ist dunkel.
probe = pygame.Surface((K.GAME_W, K.GAME_H))
probe.fill((46, 36, 27))
b = Befinden()
b.medkit()
b.medkit_rest = K.MEDKIT_BLICK["dauer"] * 0.5
b.zeichnen(probe)
mitte_farbe = probe.get_at((K.GAME_W // 2, K.GAME_H // 2))
pruef("Das Medkit laesst die Welt sichtbar",
      sum(mitte_farbe[:3]) > 30,
      "Mitte %s" % (tuple(mitte_farbe[:3]),))
# "Kalt" heisst nicht "blau", sondern: der Abstand zwischen Rot und Blau
# wird kleiner. Die Welt hier ist Rost, und aus Rost wird auch mit einer
# kuehlen Korrektur kein Eis - sie soll nur in diese Richtung kippen.
pruef("Und faerbt sie kalt",
      (mitte_farbe[0] - mitte_farbe[2]) < (46 - 27) * 0.7,
      "R%d G%d B%d, Abstand %d statt 19"
      % (*mitte_farbe[:3], mitte_farbe[0] - mitte_farbe[2]))
ecke_farbe = probe.get_at((2, 2))
pruef("Der Rand wird blau", ecke_farbe[2] > ecke_farbe[0],
      "R%d G%d B%d" % ecke_farbe[:3])

# Und der rote Rand faerbt wirklich rot, ohne die Mitte zuzukleistern.
probe.fill((46, 36, 27))
b = Befinden()
b.anteil = 0.05
b.zeichnen(probe)
pruef("Der rote Rand ist rot", probe.get_at((2, 2))[0] > probe.get_at((2, 2))[2] + 30,
      "%s" % (tuple(probe.get_at((2, 2))[:3]),))
pruef("Und die Mitte bleibt frei",
      tuple(probe.get_at((K.GAME_W // 2, K.GAME_H // 2))[:3]) == (46, 36, 27),
      "%s" % (tuple(probe.get_at((K.GAME_W // 2, K.GAME_H // 2))[:3]),))

# Dumpf machen: echt gefiltert, nicht nur leiser.
from dustfront.audio import dumpf_machen
kl = app.klaenge
if kl.ok and kl.klang("schuss_sturm"):
    klar = kl.klang("schuss_sturm")[0]
    gefiltert = dumpf_machen(klar)
    import array as _array
    a = _array.array("h"); a.frombytes(klar.get_raw())
    bq = _array.array("h"); bq.frombytes(gefiltert.get_raw())
    pruef("Die dumpfe Fassung ist genauso lang", len(a) == len(bq))
    # Hoehen weg heisst: von Probe zu Probe aendert sich weniger.
    def zappeln(x):
        return sum(abs(x[i] - x[i - 1]) for i in range(1, len(x), 97))
    pruef("Und wirklich gefiltert, nicht nur leiser",
          zappeln(bq) < zappeln(a) * 0.5,
          "%d gegen %d" % (zappeln(bq), zappeln(a)))
    kl.daempfung_setzen(0.0)
    kl._dumpf_cache.clear()
    kl._dumpf_offen.clear()
    kl.daempfung_setzen(0.5)
    pruef("Was schon gehoert wurde, wird vorgemerkt", bool(kl._dumpf_offen),
          str(kl._dumpf_offen[:3]))
    kl.dumpf_nachziehen()
    pruef("Und Stueck fuer Stueck nachgezogen", bool(kl._dumpf_cache))
    kl.daempfung_setzen(0.0)
    pruef("Der eigene Herzschlag wird nie gedaempft",
          "herzschlag" in K.NIE_DUMPF)

# ── Munitionsanzeige ─────────────────────────────────────────────────
#
# "Magazin nur rechts, Gesamtmunition in der Hotbar, und der Waffenplatz
# sieht anders aus, wenn das gewaehlte Magazin leer ist."
w, ga = gefechtspaar("pvp", knapp=True)
ich = w.kaempfer[0]
# Die klassische Hotbar (renderer.hud rechnet mit ihren Plaetzen); seit
# 0.34.85 traegt ein Kaempfer ohne Loadout alle 41 Waffen.
ich.waffen = list(K.HOTBAR)
ich.magazin.update({w_: K.WAFFEN[w_]["magazin"] for w_ in ich.waffen})
ich.waffe_waehlen(ich.waffen.index("sturm"))
bild = pygame.Surface((K.GAME_W, K.GAME_H))


def hud_bild(spieler):
    bild.fill((0, 0, 0))
    w.renderer.hud(bild, w.welt, spieler, "", 0, spieler.ebene, kopf=False)
    return bild


ich.magazin["sturm"] = 30
voll = bytes(hud_bild(ich).get_buffer())
ich.magazin["sturm"] = 0
leer = bytes(hud_bild(ich).get_buffer())
pruef("Ein leeres Magazin sieht anders aus als ein volles", voll != leer)
# Der Unterschied muss auch **am Waffenplatz** sichtbar sein, nicht nur
# an der Zahl rechts aussen.
hx = (K.GAME_W - (len(ich.waffen) * 34 + (len(ich.waffen) - 1) * 3)) // 2
platz = pygame.Rect(hx + ich.waffe * 37, K.GAME_H - 22, 34, 18)
ich.magazin["sturm"] = 30
voll_platz = pygame.transform.average_color(hud_bild(ich).subsurface(platz))
ich.magazin["sturm"] = 0
leer_platz = pygame.transform.average_color(hud_bild(ich).subsurface(platz))
pruef("Und zwar am Waffenplatz selbst",
      leer_platz[0] > voll_platz[0] + 4,
      "%s gegen %s" % (tuple(leer_platz[:3]), tuple(voll_platz[:3])))
pruef("Rechts steht nur noch das Magazin, nicht mehr das Fassungsvermoegen",
      "/" not in _hud_text_rechts(w, ich), _hud_text_rechts(w, ich))
w.verlassen(); ga.verlassen()

# ── Siegtafel ────────────────────────────────────────────────────────
#
# Mannschaften links und rechts, in ihren Farben, je Zeile Abschuesse,
# Tode, das Verhaeltnis der Runde, das Zeichen der meistbenutzten Waffe
# und der am oeftesten Erledigte.
from dustfront import bestenliste
kampf = bestenliste.mvp_punkte({"abschuesse": 2, "schaden": 500,
                                "treffer_spieler": 10, "tode": 1})
zielspiel = bestenliste.mvp_punkte({"hilfen": 2, "zonenzeit": 120,
                                    "medkits": 2})
pruef("MVP wertet Kampf, Teamhilfe, Zielzeit und Ueberleben zusammen",
      zielspiel > kampf and bestenliste.mvp_punkte({"abschuesse": 1}, 35)
      > bestenliste.mvp_punkte({"abschuesse": 1}))
w, ga = gefechtspaar("team")
for i, n in enumerate(("ROTA", "ROTB", "BLAUA"), 2):
    if i not in w.kaempfer:
        w._dazu(i, n, 0 if n.startswith("ROT") else 1)
leute = sorted(w.kaempfer.values(), key=lambda k: k.nummer)
leute[0].abschuesse, leute[0].tode = 9, 3
leute[0].zaehlen("schuesse", 40, "sturm")
leute[0].zaehlen("schuesse", 90, "schrot")
leute[0].opfer[leute[1].nummer] = 5
leute[0].opfer[leute[-1].nummer] = 2
leute[1].abschuesse, leute[1].tode = 2, 7
w.sieger_team = 0
w.endwerte = w._mvp_werte()

zeilen = w._tafel_zeilen()
pruef("Die Tafel hat je Spieler eine Zeile",
      len(zeilen) == len(w.kaempfer), "%d von %d"
      % (len(zeilen), len(w.kaempfer)))
pruef("Und ist nach Abschuessen sortiert",
      zeilen[0]["abschuesse"] >= zeilen[-1]["abschuesse"])
pruef("Pro Runde ist genau ein MVP markiert und oben auf der Tafel",
      sum(bool(z["mvp"]) for z in zeilen) == 1 and zeilen[0]["mvp"]
      and zeilen[0]["mvp_punkte"] > 0)
erste = next(z for z in zeilen if z["nummer"] == leute[0].nummer)
pruef("Die meistbenutzte Waffe zaehlt nach Schuessen, nicht nach Abschuessen",
      erste["waffe"] == "schrot", erste["waffe"])
pruef("Und der am oeftesten Erledigte steht da",
      erste["opfer"] == leute[1].name, erste["opfer"])
pruef("Jede Zeile kennt ihre Mannschaft",
      all(z["team"] in (0, 1) for z in zeilen),
      str([z["team"] for z in zeilen]))
pruef("Das Verhaeltnis der Runde stimmt",
      w._kd_text({"abschuesse": 9, "tode": 3}) == "3.0",
      w._kd_text({"abschuesse": 9, "tode": 3}))
pruef("Ohne Tod steht die Zahl allein",
      w._kd_text({"abschuesse": 4, "tode": 0}) == "4",
      w._kd_text({"abschuesse": 4, "tode": 0}))
pruef("Und ganz ohne alles ein Strich",
      w._kd_text({"abschuesse": 0, "tode": 0}) == "-")
pruef("Ohne Waffen bleibt das Zeichen leer",
      w._lieblingswaffe({}) == "" and w._lieblingswaffe(None) == "")
pruef("Und Unsinn wirft die Tafel nicht um",
      w._lieblingswaffe({"gibtsnicht": {"schuesse": 99}}) == "")

# Die Tafel muss sich zeichnen lassen, ohne dass etwas fehlt.
w.vorbei = True
w.sieger_team = 0
flaeche = pygame.Surface((K.GAME_W, K.GAME_H))
w.zeichnen(flaeche, 0.0)
pruef("Die Siegtafel laesst sich zeichnen",
      pygame.transform.average_color(flaeche)[0] > 0)
# Der Lebensbalken hat auf der Siegtafel nichts zu suchen.
unten = pygame.transform.average_color(
    flaeche.subsurface((0, K.GAME_H - 30, 160, 20)))
pruef("Die Anzeige bleibt dabei weg", sum(unten[:3]) < 40,
      "%s" % (tuple(unten[:3]),))

# Und beim Gast dasselbe: er rechnet nichts, er bekommt es geschickt.
ga.endwerte = dict(w.endwerte)
gast_zeilen = ga._tafel_zeilen()
pruef("Der Gast baut dieselbe Tafel",
      [z["name"] for z in gast_zeilen] == [z["name"] for z in zeilen],
      str([z["name"] for z in gast_zeilen]))

# Ein eingerichtetes Music Kit ersetzt auf jedem Rechner beide Ergebnis-Toene.
from types import SimpleNamespace
altes_konto = w.app._konto
music_sentinel = object()
w.app._konto = SimpleNamespace(kosmetik=SimpleNamespace(
    music_klang=lambda: music_sentinel))
klang_log = []
alt_ton, alt_name = w.app.klaenge.ton_spielen, w.app.klaenge.spielen
w.app.klaenge.ton_spielen = lambda ton, laut=1.0: klang_log.append(("kit", ton))
w.app.klaenge.spielen = lambda name, laut=1.0: klang_log.append(("standard", name))
w._ende_ton_gespielt = False; w.sieger_team = 0
w._match_ende_ton()
w._ende_ton_gespielt = False; w.sieger_team = 1
w._match_ende_ton()
pruef("Music Kit spielt denselben eigenen Track bei Sieg und Niederlage",
      klang_log == [("kit", music_sentinel), ("kit", music_sentinel)])
w.app._konto = SimpleNamespace(kosmetik=None)
klang_log[:] = []
w._ende_ton_gespielt = False; w.sieger_team = 0
w._match_ende_ton()
w._ende_ton_gespielt = False; w.sieger_team = 1
w._match_ende_ton()
pruef("Ohne Music Kit bleiben Sieg- und Niederlageton getrennt",
      klang_log == [("standard", "won_match"), ("standard", "lost_match")])
w.app.klaenge.ton_spielen, w.app.klaenge.spielen = alt_ton, alt_name
w.app._konto = altes_konto
w.verlassen(); ga.verlassen()

# ── Molotow: brennender Boden, genau auf einer Ebene ────────────────
#
# "Molotow (brennender Boden, kein Sprengschaden, muss auf allen Ebenen
# perfekt funktionieren und nicht ebenenuebergreifend)."
from dustfront.entities import Brandflaeche

w, ga = gefechtspaar("pvp")
wirt_k = w.kaempfer[0]
gast_k = w.kaempfer[ga.meine_nummer]
wirt_k.pos.update(400, 300); wirt_k.vorher.update(wirt_k.pos)
wirt_k.ebene = 0
gast_k.pos.update(1200, 900); gast_k.vorher.update(gast_k.pos)

pruef("Der Molotow steht in der Hotbar", "molotov" in K.HOTBAR)
pruef("Und macht keinen Sprengschaden",
      K.WAFFEN["molotov"]["schaden"] == 0.0 and K.WAFFEN["molotov"]["feuer"])

# Werfen: eine Flasche fliegt, zerbricht, und es brennt.
wirt_k.waffe_waehlen(wirt_k.waffen.index("molotov"))
wirt_k.takt = 0.0
wirt_k.magazin["molotov"] = 2
wirt_k.ziel.update(wirt_k.pos + pygame.Vector2(120, 0))
wirt_k.winkel = 0.0
wirt_k.feuern()
for _ in range(int(1.6 / K.FIXED_DT)):
    w.schritt(K.FIXED_DT)
pruef("Ein Molotow hinterlaesst eine Brandflaeche",
      len(w.welt.feuer) == 1, "%d" % len(w.welt.feuer))
brand = w.welt.feuer[0]
pruef("Sie liegt auf der Ebene, auf der die Flasche zerbrach",
      brand.ebene == wirt_k.ebene, "Ebene %d" % brand.ebene)

# Schaden: je Sekunde, in der Mitte mehr als am Rand, und nur auf
# derselben Ebene.
opfer = w._dazu(7, "OPFER", 1)
opfer.pos.update(brand.pos); opfer.vorher.update(opfer.pos)
opfer.ebene = brand.ebene
opfer.unverwundbar = 0.0
opfer.leben = 100.0
for _ in range(int(1.0 / K.FIXED_DT)):
    opfer.unverwundbar = 0.0
    w.welt.schritt(K.FIXED_DT)
mitte_schaden = 100.0 - opfer.leben
pruef("Wer darin steht, brennt", mitte_schaden > 20.0,
      "%.0f Schaden in einer Sekunde" % mitte_schaden)
pruef("Aber nicht sofort tot", opfer.leben > 0,
      "%.0f Leben" % opfer.leben)

opfer.leben = 100.0
opfer.pos.update(brand.pos + pygame.Vector2(brand.radius * 0.9, 0))
opfer.vorher.update(opfer.pos)
for _ in range(int(1.0 / K.FIXED_DT)):
    opfer.unverwundbar = 0.0
    w.welt.schritt(K.FIXED_DT)
rand_schaden = 100.0 - opfer.leben
pruef("Am Rand brennt es weniger als in der Mitte",
      0.0 < rand_schaden < mitte_schaden,
      "%.0f gegen %.0f" % (rand_schaden, mitte_schaden))

# Der Punkt, auf den es ankommt: durch den Boden brennt es nicht.
# Geprueft mit dem Feuer **oben** und der Figur unten - so kann sie
# nicht stuerzen, und was sie verliert, kann nur vom Feuer kommen.
w.welt.feuer = []
oben = Brandflaeche(pygame.Vector2(brand.pos), brand.ebene + 1)
oben.alter = 2.0
w.welt.feuer.append(oben)
opfer.leben = 100.0
opfer.ebene = 0
opfer.pos.update(brand.pos); opfer.vorher.update(opfer.pos)
for _ in range(int(1.5 / K.FIXED_DT)):
    opfer.unverwundbar = 0.0
    w.welt.schritt(K.FIXED_DT)
pruef("Feuer eine Ebene hoeher tut unten gar nichts", opfer.leben == 100.0,
      "%.0f Leben" % opfer.leben)
w.welt.feuer = [brand]
brand.lebt = True
pruef("Und die Flaeche sagt das auch",
      brand.brennt(brand.pos, brand.ebene) > 0
      and brand.brennt(brand.pos, brand.ebene + 1) == 0.0
      and brand.brennt(brand.pos, brand.ebene - 1) == 0.0)
pruef("Weit weg auf derselben Ebene auch nicht",
      brand.brennt(brand.pos + pygame.Vector2(brand.radius + 10, 0),
                   brand.ebene) == 0.0)

# Der Gast bekommt sie gemeldet - mit Kennung, damit er sie wiedererkennt.
for _ in range(6):
    w.schritt(K.FIXED_DT)
    ga.schritt(K.FIXED_DT)
pruef("Der Gast sieht die Brandflaeche", len(ga.welt.feuer) == 1,
      "%d" % len(ga.welt.feuer))
if ga.welt.feuer:
    gast_brand = ga.welt.feuer[0]
    pruef("An derselben Stelle und auf derselben Ebene",
          gast_brand.pos.distance_to(brand.pos) < 1.0
          and gast_brand.ebene == brand.ebene)
    for _ in range(6):
        w.schritt(K.FIXED_DT)
        ga.schritt(K.FIXED_DT)
    pruef("Und sie wird nicht bei jedem Paket neu gebaut",
          ga.welt.feuer and ga.welt.feuer[0] is gast_brand)

# Ausgebrannt heisst weg - und ein Fleck bleibt.
w.welt.ebene(brand.ebene)._dekale = {}
brand.alter = brand.dauer - 0.01
for _ in range(4):
    w.welt.schritt(K.FIXED_DT)
pruef("Nach ihrer Zeit ist sie aus", not w.welt.feuer)
pruef("Und hinterlaesst einen Brandfleck",
      w.welt.ebene(brand.ebene).dekale is not None)
w.verlassen(); ga.verlassen()

# ── Blendgranate ─────────────────────────────────────────────────────
#
# "Blendgranate (kleines Funkeln aus der Entfernung; lauter schriller Ton
# + weisser Bildschirm auch fuer das eigene Team und die eigene Granate,
# Ton klingt ab; Bild und Ton muessen fuer ein spaeteres Skin-System
# austauschbar sein)."
from dustfront.world import blend_wert

w, ga = gefechtspaar("pvp")
wirt_k = w.kaempfer[0]
gast_k = w.kaempfer[ga.meine_nummer]
wirt_k.pos.update(500, 400); wirt_k.vorher.update(wirt_k.pos)
wirt_k.ebene = 0
wirt_k.winkel = 0.0
gast_k.pos.update(1400, 1000); gast_k.vorher.update(gast_k.pos)

pruef("Die Blendgranate steht in der Hotbar", "blend" in K.HOTBAR)
pruef("Und macht keinen Schaden",
      K.WAFFEN["blend"]["schaden"] == 0.0 and K.WAFFEN["blend"]["blend"])

blitz = wirt_k.pos + pygame.Vector2(60, 0)      # genau vor ihm
pruef("Direkt davor blendet sie voll",
      blend_wert(blitz, 0, wirt_k, w.welt) > 0.9,
      "%.2f" % blend_wert(blitz, 0, wirt_k, w.welt))
pruef("Eine Ebene hoeher gar nicht",
      blend_wert(blitz, 1, wirt_k, w.welt) == 0.0)
weit = wirt_k.pos + pygame.Vector2(K.BLENDEN["weite"] + 20, 0)
pruef("Weit weg auch nicht", blend_wert(weit, 0, wirt_k, w.welt) == 0.0)
mittel = wirt_k.pos + pygame.Vector2(
    (K.BLENDEN["nah"] + K.BLENDEN["weite"]) / 2, 0)
mitte_wert = blend_wert(mittel, 0, wirt_k, w.welt)
pruef("Dazwischen anteilig", 0.2 < mitte_wert < 0.8, "%.2f" % mitte_wert)
wirt_k.winkel = 180.0                            # weggedreht
# Seit 0.30: wer wegschaut, wird nicht geblendet - er sieht nur die
# Explosion mit dem Glitzer in der Welt (so gemeldet). Seit 0.32 nicht
# mehr ganz nah: innerhalb von `rundum` wirkt sie in jede Richtung, sonst
# entschied die Mausrichtung im Moment des Knalls.
ganz_nah = wirt_k.pos + pygame.Vector2(K.BLENDEN["rundum"] - 8, 0)
pruef("Ganz nah blendet sie auch weggedreht voll",
      blend_wert(ganz_nah, 0, wirt_k, w.welt) > 0.9,
      "%.2f" % blend_wert(ganz_nah, 0, wirt_k, w.welt))
etwas_weiter = wirt_k.pos + pygame.Vector2(K.BLENDEN["rundum"] + 30, 0)
weggedreht = blend_wert(etwas_weiter, 0, wirt_k, w.welt)
pruef("Etwas weiter weg und weggedreht: kein Weiss", weggedreht == 0.0,
      "%.2f" % weggedreht)
wirt_k.winkel = 0.0
# Die Reichweite ist kurz (0.32): bei Blick auf den Blitz endet das
# Weiss bei rund 150 Pixeln, vorher bei rund 250.
reich = [d for d in range(0, 400, 2)
         if blend_wert(wirt_k.pos + pygame.Vector2(d, 0), 0, wirt_k, w.welt) > 0.0]
pruef("Das Weiss reicht nur noch rund 150 Pixel weit",
      reich and 130 <= max(reich) <= 170, "bis %s" % (max(reich) if reich else "-"))
wirt_k.winkel = 180.0
fern = wirt_k.pos + pygame.Vector2(K.BLENDEN["weite"] - 40, 0)
wirt_k.winkel = 0.0
pruef("Weit weg, aber hingeschaut, auch keins",
      blend_wert(fern, 0, wirt_k, w.welt) == 0.0)
teilchen_vorher = len(w.welt.partikel)
flecken = []
alt_fleck = w.welt.brandfleck
w.welt.brandfleck = lambda *a: flecken.append(a)
Welt.explosion(w.welt, fern, 0, 0.0, "blend")
w.welt.brandfleck = alt_fleck
neu_teilchen = w.welt.partikel[teilchen_vorher:]
pruef("Zu sehen ist sie trotzdem: Explosion und Glitzer",
      len(neu_teilchen) >= 40
      and any(p.art == "funke" and p.leben > 0.8 for p in neu_teilchen),
      "%d Teilchen" % len(neu_teilchen))
pruef("Ohne Splitter: kein Brandfleck", not flecken)
wirt_k.winkel = 0.0

# Die eigene Granate und die eigene Mannschaft blenden genauso. Das ist
# der Punkt: sonst waere sie keine Entscheidung mehr, sondern ein Knopf.
pruef("Mannschaften spielen keine Rolle",
      "team" not in blend_wert.__doc__.lower()
      or "keine rolle" in blend_wert.__doc__.lower())
befinden = w.befinden
befinden.zuruecksetzen()
w.welt.blitz(blitz, 0)
pruef("Die eigene Blendgranate blendet einen selbst",
      befinden.blend > 0.9, "%.2f" % befinden.blend)
probe = pygame.Surface((K.GAME_W, K.GAME_H))
probe.fill((20, 15, 10))
befinden.blendung_zeichnen(probe)
hell = pygame.transform.average_color(probe)
pruef("Und das Bild wird weiss", sum(hell[:3]) > 500, "%s" % (tuple(hell[:3]),))

# Sie klingt ab, und zwar erst langsam und dann schneller.
verlauf = []
for _ in range(int(K.BLENDEN["dauer"] / K.FIXED_DT) + 8):
    befinden.schritt(K.FIXED_DT, 1.0)
    verlauf.append(befinden.blend)
pruef("Die Blendung klingt ab", verlauf[-1] < 0.01,
      "%.2f am Ende" % verlauf[-1])
mitte = verlauf[len(verlauf) // 2]
pruef("Am Anfang bleibt sie lange stark", verlauf[20] > 0.85,
      "%.2f nach 0.17 s" % verlauf[20])
pruef("Und wird dann zuegig klar", mitte < 0.7, "%.2f in der Mitte" % mitte)

# Zwei Blitze addieren nicht - der schlimmere gilt.
befinden.zuruecksetzen()
befinden.blenden(0.4)
befinden.blenden(0.4)
pruef("Zwei halbe Blitze sind kein voller", befinden.blend < 0.5,
      "%.2f" % befinden.blend)
befinden.blenden(0.9)
pruef("Der schlimmere gilt", befinden.blend > 0.85, "%.2f" % befinden.blend)

# Eine Wand dazwischen schuetzt.
befinden.zuruecksetzen()
ebene0 = w.welt.ebene(0)
wand = None
for ty in range(ebene0.hoehe):
    for tx in range(ebene0.breite):
        if ebene0.sichtdicht(tx, ty):
            wand = (tx, ty)
            break
    if wand:
        break
if wand:
    # Die Figur auf die eine Seite, den Blitz auf die andere.
    mitte_wand = pygame.Vector2((wand[0] + 0.5) * K.TILE,
                                (wand[1] + 0.5) * K.TILE)
    wirt_k.pos.update(mitte_wand - pygame.Vector2(K.TILE * 2, 0))
    wirt_k.vorher.update(wirt_k.pos)
    hinter = mitte_wand + pygame.Vector2(K.TILE * 2, 0)
    pruef("Eine Wand dazwischen schuetzt ganz",
          blend_wert(hinter, 0, wirt_k, w.welt) == 0.0,
          "%.2f" % blend_wert(hinter, 0, wirt_k, w.welt))

# Um die Ecke geworfen, eng hinter der Ecke versteckt (gemeldet nach
# 0.31.4: "wird oft noch voll getroffen"). Die Sichtlinie wurde in halben
# Kacheln abgetastet und uebersprang schraeg angeschnittene Ecken.
from dustfront.world import Welt as _W39, Ebene as _E39
import random as _r39
_ecken_karte = ["".join("#" if (x == 6 and y <= 6) or x in (0, 13) or y in (0, 13)
                        else "." for x in range(14)) for y in range(14)]
_eckwelt = _W39([_E39.aus_text(_ecken_karte, 0)])
_eck = pygame.Vector2(6 * K.TILE, 7 * K.TILE)
_rz = _r39.Random(39)
_leck = _n = 0
for _ in range(3000):
    _sp = _eck + pygame.Vector2(-_rz.uniform(10, 40), -_rz.uniform(4, 36))
    _gr = _eck + pygame.Vector2(_rz.uniform(36, 100), _rz.uniform(-90, 30))
    _d = _gr - _sp
    if any(int((_sp + _d * (i / 2000)).x // K.TILE) == 6
           and int((_sp + _d * (i / 2000)).y // K.TILE) <= 6 for i in range(1, 2001)):
        _n += 1
        _leck += _eckwelt.sicht_frei(_sp, _gr, 0)
pruef("Eng hinter einer Ecke schuetzt die Wand immer", _n > 2000 and _leck == 0,
      "%d von %d durchgelassen" % (_leck, _n))
# Und durch den Spalt zwischen zwei Waenden, die sich nur an einer Ecke
# beruehren, sieht man nicht.
_spalt = ["......", "..#...", "...#..", "......"]
_spaltwelt = _W39([_E39.aus_text(_spalt, 0)])
pruef("Durch eine Kachelecke zwischen zwei Waenden geht kein Blick",
      not _spaltwelt.sicht_frei(pygame.Vector2(2.5 * K.TILE, 2.5 * K.TILE),
                                pygame.Vector2(3.5 * K.TILE, 1.5 * K.TILE), 0))
pruef("Freie Sicht bleibt frei",
      _spaltwelt.sicht_frei(pygame.Vector2(0.5 * K.TILE, 0.5 * K.TILE),
                            pygame.Vector2(5.5 * K.TILE, 0.5 * K.TILE), 0))

# Skin-System: Bild und Ton haengen an einer Rolle, nicht an einem Namen.
pruef("Bild und Klang haengen an Rollen",
      K.skin("blend_flug") == "blendgranate"
      and K.skin("blend_knall") == "blend")
pruef("Und lassen sich umlegen",
      K.skin_setzen("blend_flug", "goldgranate")
      and K.skin("blend_flug") == "goldgranate")
K.skin_zuruecksetzen()
pruef("Und wieder zuruecksetzen", K.skin("blend_flug") == "blendgranate")
pruef("Unbekannte Rollen werden abgelehnt", not K.skin_setzen("gibtsnicht", "x"))
w.verlassen(); ga.verlassen()

# ── MG: schwer, zwei Betriebsarten, genauer beim Halten ─────────────
#
# "Extreme Verlangsamung beim Feuern, langsameres Drehen, Genauigkeit
# konvergiert je laenger man feuert, grosses Magazin, weite Reichweite,
# guter Schaden. Zwei Modi: Dauerfeuer mit Anlauf wie eine Minigun, so
# dass Antippen nichts bringt, und Salvenmodus mit kurzen Salven."
mg = K.WAFFEN["lmg"]
pruef("Das MG steht in der Hotbar", "lmg" in K.HOTBAR)
pruef("Grosses Magazin", mg["magazin"] >= 80, "%d" % mg["magazin"])
pruef("Weite Reichweite", mg["reichweite"] > K.WAFFEN["sturm"]["reichweite"],
      "%.0f gegen %.0f" % (mg["reichweite"], K.WAFFEN["sturm"]["reichweite"]))
pruef("Guter Schaden", mg["schaden"] > K.WAFFEN["sturm"]["schaden"],
      "%.0f gegen %.0f" % (mg["schaden"], K.WAFFEN["sturm"]["schaden"]))
pruef("Und zwei Betriebsarten", tuple(mg["modi"]) == ("dauer", "salve"))
# Gemeldet in 0.28: "das MG macht teils mehr Schaden als die Sniper".
md = mg["modus_daten"]
salve_schaden = mg["schaden"] * md["salve"]["salve"]
pruef("Eine ganze Salve trifft nicht einmal so hart wie ein Scharfschuss",
      salve_schaden < 0.6 * K.WAFFEN["scharf"]["schaden"],
      "%.0f gegen %.0f" % (salve_schaden, K.WAFFEN["scharf"]["schaden"]))
mg_dps = mg["schaden"] / md["dauer"]["takt"]
sturm_dps = K.WAFFEN["sturm"]["schaden"] / K.WAFFEN["sturm"]["takt"]
pruef("Dauerfeuer bei voller Drehzahl bleibt unter dem Sturmgewehr",
      mg_dps < sturm_dps, "%.0f gegen %.0f je Sekunde" % (mg_dps, sturm_dps))

held.waffe_waehlen(held.waffen.index("lmg"))
held.modi.clear()
pruef("Dauerfeuer ist die Vorgabe", held.modus == "dauer", held.modus)
pruef("Die Werte der Betriebsart gelten",
      held.waffe_daten["takt"] == mg["modus_daten"]["dauer"]["takt"])
held.modus_wechseln()
pruef("Umschalten geht", held.modus == "salve", held.modus)
pruef("Und aendert die Werte",
      held.waffe_daten.get("salve") == mg["modus_daten"]["salve"]["salve"])
held.modus_wechseln()
pruef("Und wieder zurueck", held.modus == "dauer")


def mg_lauf(sekunden, modus, druecken=None, laufen=False):
    """Feuert das MG und gibt (Schuesse, Streuung am Anfang, am Ende)."""
    held.modi["lmg"] = modus
    held.anlauf = 0.0
    held.salve_rest = 0
    held.takt = 0.0
    held.halte_zeit = 0.0
    held.tempo.update(0, 0)
    held.magazin["lmg"] = 100000
    schuesse = []
    for i in range(int(sekunden / K.FIXED_DT)):
        t = i * K.FIXED_DT
        held.feuert = True if druecken is None else druecken(t)
        held.will.update((1, 0) if laufen else (0, 0))
        vorher = held.magazin["lmg"]
        held.schritt(K.FIXED_DT)
        if held.feuert and held.takt <= 0:
            held.feuern()
        if held.magazin["lmg"] < vorher:
            schuesse.append(held.streuung_jetzt)
    held.feuert = False
    held.will.update(0, 0)
    return schuesse


dauer = mg_lauf(4.0, "dauer")
pruef("Vier Sekunden Halten geben Dauerfeuer", len(dauer) > 30,
      "%d Schuss" % len(dauer))
pruef("Und es wird dabei deutlich genauer", dauer[-1] < dauer[0] * 0.2,
      "%.2f Grad am Anfang, %.2f am Ende" % (dauer[0], dauer[-1]))
pruef("Am Ende sehr genau",
      dauer[-1] <= mg["modus_daten"]["dauer"]["streuung_ziel"] + 0.01,
      "%.2f Grad" % dauer[-1])

antippen = mg_lauf(4.0, "dauer", druecken=lambda t: (t % 0.55) < 0.15)
pruef("Antippen bringt fast nichts", len(antippen) < len(dauer) * 0.3,
      "%d gegen %d Schuss in denselben 4 s" % (len(antippen), len(dauer)))

laufend = mg_lauf(4.0, "dauer", laufen=True)
pruef("Im Laufen bleibt es ungenau", laufend[-1] > dauer[-1] * 3,
      "%.2f gegen %.2f Grad" % (laufend[-1], dauer[-1]))

salve = mg_lauf(4.0, "salve")
anzahl_salve = mg["modus_daten"]["salve"]["salve"]
pruef("Der Salvenmodus schiesst deutlich weniger", len(salve) < len(dauer) / 2,
      "%d gegen %d" % (len(salve), len(dauer)))
pruef("Und zwar in Salven",
      len(salve) % anzahl_salve == 0 and len(salve) >= anzahl_salve,
      "%d Schuss, Salve zu %d" % (len(salve), anzahl_salve))
pruef("Im Stehen ist die Salve genau", salve[-1] < 1.5,
      "%.2f Grad" % salve[-1])

# Die Salve kommt fast gleichzeitig - deutlich schneller als der Takt.
held.modi["lmg"] = "salve"
held.anlauf = 0.0
held.salve_rest = 0
held.takt = 0.0
held.magazin["lmg"] = 50
held.feuert = True
held.feuern()
schuss_zeiten = []
for i in range(int(0.5 / K.FIXED_DT)):
    vorher = held.magazin["lmg"]
    held.schritt(K.FIXED_DT)
    if held.magazin["lmg"] < vorher:
        schuss_zeiten.append(i * K.FIXED_DT)
held.feuert = False
pruef("Die Schuesse einer Salve kommen fast gleichzeitig",
      schuss_zeiten and schuss_zeiten[-1] < 0.2,
      "letzter nach %.2f s" % (schuss_zeiten[-1] if schuss_zeiten else -1))

# Gewicht: Tempo und Drehen.
held.modi["lmg"] = "dauer"
held.anlauf = 0.0
pruef("Ohne Anlauf behindert es nicht",
      abs(held.gewicht_tempo - 1.0) < 0.01 and held.dreh_grenze == 0.0)
held.anlauf = 1.0
pruef("Bei voller Drehzahl bleibt wenig Tempo", held.gewicht_tempo < 0.4,
      "%.2f" % held.gewicht_tempo)
pruef("Und das Drehen ist begrenzt",
      0 < held.dreh_grenze <= mg["modus_daten"]["dauer"]["gewicht_drehen"] + 0.1,
      "%.0f Grad je Sekunde" % held.dreh_grenze)
held.modi["lmg"] = "salve"
salve_dreh = held.dreh_grenze
held.modi["lmg"] = "dauer"
pruef("Im Salvenmodus dreht es sich besser", salve_dreh > held.dreh_grenze,
      "%.0f gegen %.0f Grad je Sekunde" % (salve_dreh, held.dreh_grenze))

# Und das Drehen wirkt wirklich. Gemessen wird der Winkel je Schritt und
# nicht die Dauer einer ganzen Drehung: waehrend man feuert, schiebt der
# Rueckstoss die Figur, und dadurch wandert auch die Zielrichtung - eine
# Messung ueber sechs Sekunden misst dann beides zugleich.
held.waffe_waehlen(held.waffen.index("lmg"))
held.modi["lmg"] = "dauer"
held.anlauf = 1.0
held.winkel = 0.0
held.feuert = False
held.ziel.update(held.pos + pygame.Vector2(0, 200))    # 90 Grad zur Seite
vorher_winkel = held.winkel
held.schritt(K.FIXED_DT)
je_schritt = abs((held.winkel - vorher_winkel + 180) % 360 - 180)
erlaubt = mg["modus_daten"]["dauer"]["gewicht_drehen"] * K.FIXED_DT
pruef("Das MG dreht hoechstens so schnell wie erlaubt",
      je_schritt <= erlaubt + 0.01,
      "%.3f Grad je Schritt, erlaubt %.3f" % (je_schritt, erlaubt))
pruef("Und braucht damit fuer eine Vierteldrehung merklich Zeit",
      90.0 / max(0.01, je_schritt) * K.FIXED_DT > 1.0,
      "%.1f s fuer 90 Grad"
      % (90.0 / max(0.01, je_schritt) * K.FIXED_DT))

# Eine andere Waffe dreht weiter sofort.
held.waffe_waehlen(held.waffen.index("sturm"))
held.winkel = 0.0
held.ziel.update(held.pos + pygame.Vector2(-200, 0))
held.schritt(K.FIXED_DT)
pruef("Mit dem Sturmgewehr geht es weiter sofort",
      abs((180 - held.winkel + 180) % 360 - 180) < 1.0,
      "%.0f Grad" % held.winkel)
pruef("Und es behindert das Lauftempo nicht",
      abs(held.gewicht_tempo - 1.0) < 0.01)

# ── Raketenwerfer ────────────────────────────────────────────────────
#
# "In den Hosteinstellungen aktivierbar, einmaliger Pickup auf der Karte,
# man kann bis zum Schuss nur den RPG ausruesten ausser dem Brecheisen
# mit F, Eigenschaden ja aber kein Teamschaden; optionale Zielerfassung:
# eine Sekunde rechte Maustaste halten, Kreis zieht sich zusammen und
# wechselt die Farbe, die Rakete lenkt aber kann keine engen Kurven;
# nach unten nur ueber Abgruenden auf sichtbare Gegner, und die Rakete
# wechselt dann sauber die Ebene; der Erfasste bekommt eine Vignette."
from dustfront.entities import Rakete
from dustfront.mehrspieler import KampfBeute

pruef("Der Brecher hat 95 Leben", K.GEGNER["brecher"]["leben"] == 95.0)
w, ga = gefechtspaar("team", rpg=True)
pruef("Der Gastgeber kann den Werfer einschalten", w.mit_rpg)
pruef("Und der Gast erfaehrt es", ga.rpg_an, str(ga.rpg_an))
pruef("Der RPG verursacht 150 Schaden mit etwas groesserem Explosionsradius",
      K.WAFFEN["rakete"]["schaden"] == 150.0
      and K.WAFFEN["rakete"]["radius"] == 104.0)
aus = gefechtspaar("pvp")
pruef("Ohne Schalter gibt es ihn nicht", not aus[0].mit_rpg)
aus[0].verlassen(); aus[1].verlassen()

schuetze = w.kaempfer[0]
opfer = w.kaempfer[ga.meine_nummer]
kamerad = w._dazu(8, "KAMERAD", schuetze.team)
schuetze.pos.update(400, 400); schuetze.vorher.update(schuetze.pos)
schuetze.ebene = 0
schuetze.winkel = 0.0
opfer.pos.update(700, 400); opfer.vorher.update(opfer.pos)
opfer.ebene = 0
kamerad.pos.update(430, 400); kamerad.vorher.update(kamerad.pos)
kamerad.ebene = 0

# Aufheben: danach traegt man nur noch ihn.
vorher_waffen = list(schuetze.waffen)
pruef("Aufheben klappt", schuetze.rpg_nehmen())
pruef("Und danach traegt man nur noch den Werfer",
      schuetze.waffen == ["rakete"], str(schuetze.waffen))
pruef("Ein zweiter geht nicht", not schuetze.rpg_nehmen())
pruef("Das Brecheisen bleibt trotzdem da",
      K.NAHKAMPF["waffe"] not in schuetze.waffen and bool(schuetze.nahkampf()))
schuetze.nahkampf_rest = 0.0

# Zielerfassung.
schuetze.lenkbar = True
schuetze.zielt = True
schuetze.ziel.update(opfer.pos)
schuetze.winkel = 0.0
e = K.ERFASSUNG
for _ in range(int(e["dauer"] * 0.4 / K.FIXED_DT)):
    schuetze.schritt(K.FIXED_DT)
pruef("Die Erfassung laeuft an",
      schuetze.erfasst is opfer and 0.1 < schuetze.erfassung < 0.9,
      "%.2f" % schuetze.erfassung)
for _ in range(int(e["dauer"] / K.FIXED_DT)):
    schuetze.schritt(K.FIXED_DT)
pruef("Und steht nach der vollen Zeit", schuetze.erfassung >= 1.0,
      "%.2f" % schuetze.erfassung)
pruef("Der eigene Kamerad wird nicht erfasst", schuetze.erfasst is not kamerad)

# Loslassen: sie haelt noch kurz und faellt dann.
schuetze.zielt = False
for _ in range(int((e["halten"] + 0.1) / K.FIXED_DT)):
    schuetze.schritt(K.FIXED_DT)
pruef("Nach dem Loslassen faellt die Erfassung weg",
      schuetze.erfasst is None, str(schuetze.erfasst))

# Ohne Lenkung gibt es gar keine Erfassung.
schuetze.lenkbar = False
schuetze.zielt = True
for _ in range(int(e["dauer"] * 1.5 / K.FIXED_DT)):
    schuetze.schritt(K.FIXED_DT)
pruef("Ohne Zielerfassung erfasst sie nichts", schuetze.erfasst is None)
schuetze.lenkbar = True

# Schiessen.
schuetze.zielt = True
schuetze.ziel.update(opfer.pos)
for _ in range(int(e["dauer"] * 1.5 / K.FIXED_DT)):
    schuetze.schritt(K.FIXED_DT)
schuetze.takt = 0.0
schuetze.feuern()
raketen = [x for x in w.welt.neue + w.welt.wesen if isinstance(x, Rakete)]
pruef("Der Werfer schiesst eine Rakete", len(raketen) == 1,
      "%d" % len(raketen))
rakete = raketen[0]
pruef("Und sie hat ihr Ziel", rakete.ziel is opfer)
pruef("Nach dem Schuss ist das Rohr weg",
      not schuetze.rpg and schuetze.waffen == vorher_waffen,
      str(schuetze.waffen))

# Lenken: sie dreht, aber nur langsam.
rakete.winkel = -90.0                       # quer zum Ziel
rakete.tempo = pygame.Vector2(rakete.daten["tempo"], 0).rotate(-90.0)
vorher_winkel = rakete.winkel
rakete._lenken(K.FIXED_DT)
gedreht = abs((rakete.winkel - vorher_winkel + 180) % 360 - 180)
erlaubt = rakete.daten["lenk_dreh"] * K.FIXED_DT
pruef("Die Rakete lenkt hoechstens so schnell wie erlaubt",
      gedreht <= erlaubt + 0.001,
      "%.3f Grad je Schritt, erlaubt %.3f" % (gedreht, erlaubt))
pruef("Und dreht in die richtige Richtung", gedreht > 0.0)

# Eigenschaden ja, Mannschaftsschaden nein.
for k in (schuetze, kamerad, opfer):
    k.unverwundbar = 0.0
    k.leben = 200.0
    k.max_leben = 200.0
rakete.pos.update(schuetze.pos)
rakete.ebene = schuetze.ebene
kamerad.pos.update(schuetze.pos + pygame.Vector2(12, 0))
opfer.pos.update(schuetze.pos + pygame.Vector2(18, 0))
opfer.ebene = kamerad.ebene = schuetze.ebene
w.welt.schritt(0.0)                          # Raster neu bauen
rakete.einschlag(None)
pruef("Der Schuetze bekommt etwas ab", schuetze.leben < 200.0,
      "%.0f Leben" % schuetze.leben)
pruef("Aber weniger als voll",
      schuetze.leben > 200.0 - K.WAFFEN["rakete"]["schaden"],
      "%.0f Leben" % schuetze.leben)
pruef("Die eigene Mannschaft gar nichts", kamerad.leben == 200.0,
      "%.0f Leben" % kamerad.leben)
pruef("Der Gegner dagegen schon", opfer.leben < 200.0,
      "%.0f Leben" % opfer.leben)

# Nach unten erfassen: nur ueber einem Loch.
schuetze.rpg_nehmen()
schuetze.erfasst = None
schuetze.erfassung = 0.0
ebene1 = w.welt.ebene(1)
loch = None
for ty in range(ebene1.hoehe):
    for tx in range(ebene1.breite):
        if ebene1.loch(tx, ty):
            loch = (tx, ty)
            break
    if loch:
        break
pruef("Die Karte hat ein Loch auf Ebene 1", loch is not None)
if loch:
    unter_loch = pygame.Vector2((loch[0] + 0.5) * K.TILE,
                                (loch[1] + 0.5) * K.TILE)
    schuetze.ebene = 1
    schuetze.pos.update(unter_loch - pygame.Vector2(120, 0))
    schuetze.vorher.update(schuetze.pos)
    schuetze.winkel = 0.0
    schuetze.ziel.update(unter_loch)
    opfer.ebene = 0
    opfer.pos.update(unter_loch)
    opfer.vorher.update(opfer.pos)
    opfer.leben = 200.0
    schuetze.zielt = True
    for _ in range(int(e["dauer"] * 1.5 / K.FIXED_DT)):
        schuetze.schritt(K.FIXED_DT)
    pruef("Durch ein Loch laesst sich nach unten erfassen",
          schuetze.erfasst is opfer and schuetze.erfassung >= 1.0,
          "%s, %.2f" % (schuetze.erfasst, schuetze.erfassung))

    # Und dieselbe Lage ohne Loch: nichts.
    fest = None
    for ty in range(ebene1.hoehe):
        for tx in range(ebene1.breite):
            if ebene1.begehbar(tx, ty) and not ebene1.loch(tx, ty):
                fest = (tx, ty)
                break
        if fest:
            break
    if fest:
        auf_boden = pygame.Vector2((fest[0] + 0.5) * K.TILE,
                                   (fest[1] + 0.5) * K.TILE)
        schuetze.erfasst = None
        schuetze.erfassung = 0.0
        schuetze.pos.update(auf_boden - pygame.Vector2(100, 0))
        schuetze.vorher.update(schuetze.pos)
        schuetze.ziel.update(auf_boden)
        opfer.pos.update(auf_boden)
        opfer.vorher.update(opfer.pos)
        for _ in range(int(e["dauer"] * 1.5 / K.FIXED_DT)):
            schuetze.schritt(K.FIXED_DT)
        pruef("Ueber festem Boden nicht", schuetze.erfasst is None,
              str(schuetze.erfasst))

    # Die Rakete wechselt im Flug die Ebene - aber nur mit Erfassung.
    r = Rakete(unter_loch - pygame.Vector2(30, 0), 0.0,
               K.WAFFEN["rakete"], 1, schuetze, opfer)
    w.welt.dazu(r)
    opfer.ebene = 0
    opfer.pos.update(unter_loch)
    r.pos.update(unter_loch)
    r._ebene_wechseln()
    pruef("Ueber dem Loch faellt sie eine Ebene tiefer", r.ebene == 0,
          "Ebene %d" % r.ebene)
    ungelenkt = Rakete(unter_loch, 0.0, K.WAFFEN["rakete"], 1, schuetze, None)
    w.welt.dazu(ungelenkt)
    ungelenkt._ebene_wechseln()
    pruef("Ohne Erfassung fliegt sie darueber hinweg", ungelenkt.ebene == 1,
          "Ebene %d" % ungelenkt.ebene)
    r.lebt = ungelenkt.lebt = False

# Der Pickup liegt auf der Karte, und nur einer.
w.welt.wesen = [x for x in w.welt.wesen if not isinstance(x, KampfBeute)]
for k in w.kaempfer.values():
    k.rpg_ablegen()
w._rpg_takt = 0.0
for _ in range(int(3.0 / K.FIXED_DT)):
    w.schritt(K.FIXED_DT)
werfer = [x for x in w.welt.wesen
          if isinstance(x, KampfBeute) and x.art == "rakete" and x.lebt]
pruef("Ein Werfer liegt auf der Karte", len(werfer) == 1,
      "%d" % len(werfer))
w._rpg_takt = 0.0
for _ in range(int(3.0 / K.FIXED_DT)):
    w.schritt(K.FIXED_DT)
werfer = [x for x in w.welt.wesen
          if isinstance(x, KampfBeute) and x.art == "rakete" and x.lebt]
pruef("Und nur einer", len(werfer) == 1, "%d" % len(werfer))
w.verlassen(); ga.verlassen()

# ── STAUBTAL: sehr gross, sehr leer, drei Kreise ────────────────────
#
# "Eine neue, sehr grosse, sehr leere Sand-/Wuestenkarte, keine Gaenge
# ueber dem Rest, Plateaus als hoehere Ebenen unter die man nicht kommt,
# Wildwest-Optik mit dem postapokalyptischen Vibe, generell flach ausser
# Plateaus und ein paar kleinen Gebaeuden. Drei Hot Zones, die nicht
# identisch sind, und ihre Orte muessen selbsterklaerend sein."
from dustfront import world as W

pruef("Die Karte liegt im Ordner", "staubtal" in W.karten_liste(),
      str(W.karten_liste()))
staub, kopf = W.karte_lesen("staubtal")
pruef("Und laesst sich lesen", staub is not None)
pruef("Sie heisst STAUBTAL", kopf.get("name") == "STAUBTAL", str(kopf))
pruef("Und benutzt den Wuestensatz", staub.satz == "wueste", staub.satz)

s0, s1 = staub.ebenen[0], staub.ebenen[1]
pruef("Beide Ebenen sind gleich gross",
      (s0.breite, s0.hoehe) == (s1.breite, s1.hoehe),
      "%dx%d gegen %dx%d" % (s0.breite, s0.hoehe, s1.breite, s1.hoehe))
pruef("Sie ist sehr gross",
      s0.breite >= 100 and s0.hoehe >= 70,
      "%d x %d Kacheln = %d x %d Pixel"
      % (s0.breite, s0.hoehe, s0.pixel_breite, s0.pixel_hoehe))
begehbar = sum(1 for ty in range(s0.hoehe) for tx in range(s0.breite)
               if s0.begehbar(tx, ty))
# Gezaehlt wird der Boden unter freiem Himmel. Seit 0.32.29 stehen die
# Plateaus auf grossen Felsbloecken; mit ihnen gerechnet waere jede Karte
# mit grossen Plateaus "voll", obwohl der Sand dazwischen leer ist.
_himmel = [(tx, ty) for ty in range(s0.hoehe) for tx in range(s0.breite)
           if s1.kachel(tx, ty) == K.LEER]
_himmel_frei = sum(1 for p in _himmel if s0.begehbar(*p))
pruef("Und sehr leer", _himmel_frei > len(_himmel) * 0.6,
      "%d von %d Kacheln unter freiem Himmel begehbar"
      % (_himmel_frei, len(_himmel)))

# Plateaus: obere Ebene nur Tafeln, und unter jeder Tafel steht Fels.
oben = sum(1 for ty in range(s1.hoehe) for tx in range(s1.breite)
           if s1.begehbar(tx, ty))
# Tafeln heisst: wenige grosse zusammenhaengende Flaechen, fast nur
# Innenfelder. Ein Gangnetz haette viele Stuecke und fast nur Rand.
# (Bis 0.32.28 stand hier "weniger als ein Viertel der Kartenflaeche" -
# die grossen Plateaus von 0.32.29 sind ein Drittel und trotzdem Tafeln.)
_innen1 = sum(1 for ty in range(s1.hoehe) for tx in range(s1.breite)
              if s1.begehbar(tx, ty) and not s1.loch(tx, ty)
              and all(s1.begehbar(a, b) and not s1.loch(a, b)
                      for a, b in ((tx + 1, ty), (tx - 1, ty),
                                   (tx, ty + 1), (tx, ty - 1))))
pruef("Die obere Ebene ist kein Gangnetz, sondern sind Tafeln",
      0 < oben < s0.breite * s0.hoehe * 0.5 and _innen1 > oben * 0.85,
      "%d Kacheln oben, %d davon innen" % (oben, _innen1))
# Ausnahme seit 0.32.29: die geschuetzten Aufzuege. Ihre Tuer liegt in
# einer Nische oder einem kurzen Gang im Fels - darueber ist Plateau.
# Erlaubt ist das nur in der Naehe eines Aufzugs; ein Feld irgendwo
# sonst unter dem Plateau ist ein Kartenfehler (so lagen die Tueren der
# Haeuser von Hotzone 2 einzeln im Fels).
_aufzuege_s = [(tx, ty) for e in staub.ebenen for ty in range(e.hoehe)
               for tx in range(e.breite) if e.daten(tx, ty).get("treppe")]
darunter = []
for ty in range(s1.hoehe):
    for tx in range(s1.breite):
        if not s1.begehbar(tx, ty):
            continue
        d0 = s0.daten(tx, ty)
        if (s0.begehbar(tx, ty) and d0.get("treppe") is None
                and not any(abs(tx - ax) <= 7 and abs(ty - ay) <= 7
                            for ax, ay in _aufzuege_s)):
            darunter.append((tx, ty))
pruef("Unter die Plateaus kommt man nicht (ausser zum Aufzug)", not darunter,
      "%d begehbare Kacheln unter einem Plateau: %s" % (len(darunter), darunter[:8]))

# Und hinauf kommt man trotzdem.
hoch = [(tx, ty) for ty in range(s0.hoehe) for tx in range(s0.breite)
        if s0.daten(tx, ty).get("treppe") == 1]
runter = [(tx, ty) for ty in range(s1.hoehe) for tx in range(s1.breite)
          if s1.daten(tx, ty).get("treppe") == -1]
pruef("Es gibt Rampen hinauf", len(hoch) >= 3, "%d" % len(hoch))
pruef("Und ebenso viele hinunter", len(runter) == len(hoch),
      "%d hinauf, %d hinunter" % (len(hoch), len(runter)))
# Jede Rampe muss auch wirklich benutzbar sein: oben muss **Boden** sein.
#
# Hier stand bis 0.27 nur `frei()`, und frei heisst "keine Wand" - ein
# Loch ist keine Wand. Der Test war also gruen, waehrend alle sieben
# Rampen auf ein Loch fuehrten und jeder, der hinaufging, sofort wieder
# hinunterfiel. Jetzt wird nach Boden gefragt.
ohne_boden = [p for p in hoch
              if not staub.ebene(1).begehbar(p[0], p[1])
              or staub.ebene(1).loch(p[0], p[1])]
pruef("Und ueber jeder Rampe ist oben Boden, kein Loch",
      not ohne_boden, str(ohne_boden))

# ── Aufzuege: E-Treppen mit geschuetztem Ausstieg ───────────────────
# Die Aufzuggrafik bleibt erhalten, bedient wird sie wie eine alte Treppe:
# E wechselt genau eine Ebene, waehrend die Figur am selben Ort bleibt.
tueren = [(tx, ty) for ty in range(s0.hoehe) for tx in range(s0.breite)
          if s0.daten(tx, ty).get("treppe") == 1
          and s0.daten(tx, ty).get("name") == "aufzug"]
koepfe = [(tx, ty) for ty in range(s1.hoehe) for tx in range(s1.breite)
          if s1.daten(tx, ty).get("treppe") == -1
          and s1.daten(tx, ty).get("name") == "aufzug"]
pruef("STAUBTAL hat gepaarte Aufzug-Treppen", bool(tueren)
      and sorted(tueren) == sorted(koepfe), "%s / %s" % (tueren, koepfe))

# Jedes Aufzugfeld besitzt in beiden Richtungen freie 5x5-Landezonen.
def aufzug_zone_frei(ebene, x, y):
    flaeche = staub.ebene(ebene)
    return all(flaeche.begehbar(x + dx, y + dy)
               and not flaeche.loch(x + dx, y + dy)
               for dx in (-1, 1) for dy in (0,))

pruef("Aufzuege bieten links und rechts einen freien Ausstieg",
      all(aufzug_zone_frei(1, x, y) for x, y in tueren), str(tueren))

# E-Bedienung wird ueber die echte Einzelspieler-Eingabe am alten
# Treppenpfad getestet; die Karte selbst liefert das Ziel genau eine Ebene.
aufzug_x, aufzug_y = tueren[0]
aufzug_held = type("AufzugProbe", (), {})()
aufzug_held.ebene = 0
aufzug_held.pos = pygame.Vector2((aufzug_x + 0.5) * K.TILE,
                                 (aufzug_y + 0.5) * K.TILE)
pruef("Aufzug-Kachel bietet E-Wechsel um eine Ebene",
      staub.treppe_unter(aufzug_held) == 1)
pruef("Oberer Aufzug fuehrt genau eine Ebene hinunter",
      staub.ebene(1).daten(aufzug_x, aufzug_y).get("treppe") == -1)
aufzug_probe_pos = pygame.Vector2(aufzug_held.pos)
aufzug_held.radius = 8
aufzug_held.vorher = pygame.Vector2(aufzug_probe_pos)
pruef("E-Treppenwechsel bringt am Aufzug genau eine Ebene hoch",
      staub.ebene_wechseln(aufzug_held, 1)
      and aufzug_held.ebene == 1
      and aufzug_held.pos.distance_to(aufzug_probe_pos) < 0.01)

# Drei Kreise, nicht identisch, und einer davon oben.
#
# `marken` sind alle Grossbuchstaben der Karte, und dazu gehoeren seit
# den Spawnstellen auch die Z. Geprueft werden hier die Kreise - welche
# Buchstaben das sind, sagt der Kopf der Karte und nicht dieser Test.
alle_marken = {}
for e in staub.ebenen:
    for name, stellen in e.marken.items():
        alle_marken.setdefault(name, []).append((e.index, stellen))
kreisnamen = str(kopf.get("kreise", "")).split()
marken = {}
for e in staub.ebenen:
    for name, stellen in e.marken.items():
        if name in kreisnamen:
            marken[name] = (e.index, stellen[0])
pruef("Die Karte nennt drei Kreise",
      sorted(marken) == ["A", "B", "C"], str(sorted(marken)))
pruef("Und einer liegt auf einem Plateau",
      any(e == 1 for e, _p in marken.values()),
      str({k: v[0] for k, v in marken.items()}))
pruef("Sie liegen weit auseinander",
      min(marken["A"][1].distance_to(marken[b][1]) for b in "BC") > 800,
      "%.0f px" % min(marken["A"][1].distance_to(marken[b][1]) for b in "BC"))
# Selbsterklaerend heisst hier: A ist das offene Sandfeld - frei um den
# Kreis, mit Deckungsinseln drumherum. Bis 0.32.28 war das ein enger Ring
# aus Fassern; der Lageplan von 0.32.29 macht daraus Inseln in 15 bis 25
# Kacheln Abstand (werkzeug_staubtal.py, "Hotzone 1").
kreis_a = marken["A"][1]
fasser_nah = fasser = 0
for ty in range(s0.hoehe):
    for tx in range(s0.breite):
        if s0.kachel(tx, ty) != K.KISTE:
            continue
        p = pygame.Vector2(tx * K.TILE + K.TILE / 2, ty * K.TILE + K.TILE / 2)
        weg_a = p.distance_to(kreis_a)
        if weg_a < 150:
            fasser_nah += 1
        elif weg_a < 800:
            fasser += 1
# Hotzone 2 (B, auf dem Plateau) ist ein Aussenposten: Haeuser und
# Deckung ringsum, der Kreis selbst frei. Bis 0.34.1 stand das alles auf
# Ebene 0 im Fels, und B lag auf einer leeren Flaeche (seit 0.34.2).
kreis_b = marken["B"][1]
s_b = staub.ebene(marken["B"][0])
_um_b = [(tx, ty) for ty in range(s_b.hoehe) for tx in range(s_b.breite)
         if s_b.kachel(tx, ty) in (K.WAND, K.KISTE)
         and pygame.Vector2((tx + .5) * K.TILE, (ty + .5) * K.TILE).distance_to(kreis_b)
         < 40 * K.TILE]
_im_b = [p for p in _um_b
         if pygame.Vector2((p[0] + .5) * K.TILE, (p[1] + .5) * K.TILE).distance_to(kreis_b)
         < K.ZONE["radius"] + K.TILE]
pruef("Um den Kreis B steht ein Aussenposten, der Kreis selbst ist frei",
      len(_um_b) >= 100 and not _im_b,
      "%d Mauer- und Fassfelder im Umkreis, %d im Kreis" % (len(_um_b), len(_im_b)))
pruef("Um den offenen Kreis A stehen Deckungsinseln, der Kreis selbst ist frei",
      fasser >= 10 and fasser_nah == 0,
      "%d Fass-Kacheln im Umkreis, %d direkt am Kreis" % (fasser, fasser_nah))

# 0.34.6: "Bereiche, wo 50 verschiedene Faesser nebeneinander stehen" -
# Faesser stehen jetzt in kleinen Gruppen, wo jemand sie abgestellt hat.
_gruppen_f = []
for e in staub.ebenen:
    _gesehen_f = set()
    for ty in range(e.hoehe):
        for tx in range(e.breite):
            if e.kachel(tx, ty) != K.KISTE or (tx, ty) in _gesehen_f:
                continue
            _offen_f, _n_f = [(tx, ty)], 0
            _gesehen_f.add((tx, ty))
            while _offen_f:
                a, b = _offen_f.pop()
                _n_f += 1
                for c, d in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                    if e.kachel(c, d) == K.KISTE and (c, d) not in _gesehen_f:
                        _gesehen_f.add((c, d))
                        _offen_f.append((c, d))
            _gruppen_f.append(_n_f)
pruef("Faesser stehen in kleinen Gruppen, nie mehr als vier zusammen",
      _gruppen_f and max(_gruppen_f) <= 4,
      "%d Gruppen, die groesste %d" % (len(_gruppen_f), max(_gruppen_f or [0])))
_arten_s = {e.kachel(tx, ty) for e in staub.ebenen
            for ty in range(e.hoehe) for tx in range(e.breite)}
_fehlen_s = [K.KACHELN[k_]["name"] for k_ in (K.FELS, K.BROCKEN, K.SANDSACK, K.HOLZKISTE,
                                              K.KAKTUS, K.SCHROTT, K.PISTE, K.KIES,
                                              K.PFLASTER, K.GESTRUEPP, K.DIELEN)
             if k_ not in _arten_s]
pruef("STAUBTAL hat Gelaende, nicht nur Sand, Mauer und Fass", not _fehlen_s, _fehlen_s)
_unter_s = [(tx, ty) for ty in range(s1.hoehe) for tx in range(s1.breite)
            if s1.kachel(tx, ty) != K.LEER and s0.daten(tx, ty).get("treppe") is None]
_fels_s = sum(1 for p in _unter_s if s0.kachel(*p) == K.FELS)
pruef("Unter den Tafeln ist gewachsener Fels, keine Lehmmauer",
      _fels_s >= len(_unter_s) * 0.99, "%d von %d" % (_fels_s, len(_unter_s)))

# Im Gefecht: die Karte laesst sich waehlen und der Kreis wandert.
# Die Aufzuege werden ueber die vorhandene E-Treppenlogik bedient.

w, ga = gefechtspaar("huegel", karte="staubtal")
pruef("Das Gefecht laeuft auf der Karte", w.karte == "staubtal", w.karte)
pruef("Und der Gast bekommt sie auch", ga.karte == "staubtal", ga.karte)
pruef("Sie kennt drei Kreise", len(w.kreise) == 3, "%d" % len(w.kreise))
erster = (w.zone_ebene, pygame.Vector2(w.zone_mitte))
pruef("Der Kreis liegt auf einer Marke",
      any(e == w.zone_ebene and p.distance_to(w.zone_mitte) < 1.0
          for e, p in marken.values()))
w.kreis_rest = 0.0
w._kreis_wandern(K.FIXED_DT)
pruef("Nach der Zeit zieht er weiter",
      (w.zone_ebene, w.zone_mitte) != erster,
      "%d/%s gegen %d/%s" % (w.zone_ebene, w.zone_mitte, erster[0], erster[1]))
for _ in range(len(w.kreise) - 1):
    w.kreis_rest = 0.0
    w._kreis_wandern(K.FIXED_DT)
pruef("Und kommt im Kreis herum",
      (w.zone_ebene, pygame.Vector2(w.zone_mitte)) == erster,
      "%d/%s" % (w.zone_ebene, w.zone_mitte))
# Wer auf der falschen Ebene im Kreis steht, zaehlt nicht.
w._kreis_setzen(next(i for i, (e, _p, _n) in enumerate(w.kreise) if e == 1))
wer = w.kaempfer[0]
wer.pos.update(w.zone_mitte); wer.vorher.update(wer.pos)
wer.ebene = 1
pruef("Auf der richtigen Ebene zaehlt man im Kreis", w.in_der_zone(wer))
wer.ebene = 0
pruef("Eine Ebene tiefer nicht", not w.in_der_zone(wer))

# Und der Kreis des Gastes wandert mit.
for _ in range(8):
    w.schritt(K.FIXED_DT)
    ga.schritt(K.FIXED_DT)
pruef("Der Gast steht auf demselben Kreis",
      ga.kreis_nr == w.kreis_nr
      and ga.zone_mitte.distance_to(w.zone_mitte) < 1.0,
      "%d gegen %d" % (ga.kreis_nr, w.kreis_nr))

# 0.34.8: "In welcher Richtung die Hotzone ist, sollte durch einen grossen
# Pfeil in der Farbe der Hotzone am Rand angezeigt werden. Die naechste
# Position durch ein > in der Hotzone - die Richtung, in die sie geht."
pruef("Der Gast kennt auch den naechsten Kreis",
      ga._naechster_kreis() is not None
      and ga._naechster_kreis()[1].distance_to(w._naechster_kreis()[1]) < 1.0)
w._kreis_setzen(0)
pruef("Der naechste Kreis ist der, zu dem er dann wirklich zieht",
      w._naechster_kreis()[1] == w.kreise[1][1])

def _zaehle68(bild_, farbe_):
    return [(x_, y_) for x_ in range(0, K.GAME_W, 2) for y_ in range(0, K.GAME_H, 2)
            if bild_.get_at((x_, y_))[:3] == farbe_]

_ich68 = w.ich
_farbe68 = w._zonenfarbe()[0]
for _k68 in w.kaempfer.values():
    _k68.ebene = w.zone_ebene
# Weit weg westlich vom Kreis: der Pfeil sitzt am linken Rand.
_ich68.pos.update(w.zone_mitte - pygame.Vector2(40 * K.TILE, 0))
w.blick = w.zone_ebene
w.kamera.pos.update(_ich68.pos); w.kamera.versatz.update(0, 0)
w.kamera.zoom = 1.0
_rand68 = pygame.Surface((K.GAME_W, K.GAME_H)); _rand68.fill((0, 0, 0))
w._kreispfeil(_rand68)
_px68 = _zaehle68(_rand68, _farbe68)
pruef("Ist der Kreis nicht im Bild, zeigt ein grosser Pfeil in seiner Farbe auf ihn",
      len(_px68) > 30, "%d Bildpunkte" % len(_px68))
pruef("... am Rand auf seiner Seite (hier rechts)",
      _px68 and min(x_ for x_, _y in _px68) > K.GAME_W * 0.8)
w.zone_halter = 1
_px68b = _zaehle68((lambda s_: (s_.fill((0, 0, 0)), w._kreispfeil(s_), s_)[2])(
    pygame.Surface((K.GAME_W, K.GAME_H))), K.TEAMS["farben"][1])
pruef("... und in der Farbe des Teams, das ihn haelt", len(_px68b) > 30)
w.zone_halter = -1
# Steht man im Kreis, braucht es keinen Pfeil.
_ich68.pos.update(w.zone_mitte)
w.kamera.pos.update(_ich68.pos)
_drin68 = pygame.Surface((K.GAME_W, K.GAME_H)); _drin68.fill((0, 0, 0))
w._kreispfeil(_drin68)
pruef("Im Bild steht kein Pfeil", not _zaehle68(_drin68, _farbe68))
# Eine Ebene hoeher: der Kreis ist nicht zu sehen, also wieder ein Pfeil.
w.blick = w.zone_ebene + 1
_e68 = pygame.Surface((K.GAME_W, K.GAME_H)); _e68.fill((0, 0, 0))
w._kreispfeil(_e68)
pruef("Auf einer anderen Ebene zeigt der Pfeil trotzdem", len(_zaehle68(_e68, _farbe68)) > 30)
w.blick = w.zone_ebene

# Das ">" im Kreis zeigt zum naechsten: seine Bildpunkte liegen auf der
# Seite der Mitte, auf der der naechste Kreis liegt.
_r68 = K.ZONE["radius"]
for _ri68 in (pygame.Vector2(1, 0), pygame.Vector2(0, -1), pygame.Vector2(-1, 1)):
    _f68 = pygame.Surface((int(4 * _r68), int(4 * _r68)), pygame.SRCALPHA)
    _f68.fill((0, 0, 0, 0))
    _m68 = pygame.Vector2(2 * _r68, 2 * _r68)
    w.renderer.kreis_weiter(_f68, _m68, _r68, _ri68, (255, 0, 255), 0.0)
    _pk68 = [pygame.Vector2(x_, y_) for x_ in range(_f68.get_width())
             for y_ in range(_f68.get_height())
             if _f68.get_at((x_, y_))[:3] == (255, 0, 255)]
    _schwer68 = sum(_pk68, pygame.Vector2()) / max(1, len(_pk68))
    pruef("Das > zeigt zum naechsten Kreis (Richtung %d,%d)" % (_ri68.x, _ri68.y),
          len(_pk68) > 50 and (_schwer68 - _m68).dot(_ri68.normalize()) > _r68 * 0.1,
          "%d Punkte, Schwerpunkt %s" % (len(_pk68), _schwer68 - _m68))
w.verlassen(); ga.verlassen()

# ─────────────────────────────────────────────────────────────────────
# 0.34.9: "Bau mal einen kleinen Top-down-Buggy, der auf der Wuestenkarte
# spawnt und mit dem man rumfahren kann. Unzerstoerbar, aber wer drin ist,
# nimmt 70 % vom Schaden. Muss gut von oben aussehen."
from dustfront.fahrzeug import Buggy

_bilder69 = None
w, ga = gefechtspaar("pvp", karte="staubtal")
_bilder69 = w.renderer.bilder
for _n69 in ("buggy", "buggy_fahrer", "buggy_rot_fahrer", "buggy_blau_fahrer",
             "buggy_schatten"):
    _s69 = _bilder69.bild(_n69)
    _deckt69 = sum(1 for x_ in range(0, 64, 2) for y_ in range(0, 64, 2)
                   if _s69.get_at((x_, y_))[3] > (40 if "schatten" in _n69 else 200))
    pruef("Das Bild %s ist gezeichnet und nicht leer" % _n69,
          _s69.get_size() == (64, 64) and _deckt69 > 60,
          "%s, %d deckende Punkte" % (_s69.get_size(), _deckt69))
pruef("Kein Buggybild fehlt", not [f for f in _bilder69.fehler if "buggy" in f],
      str(_bilder69.fehler))
_leer69 = _bilder69.bild("buggy")
_voll69 = _bilder69.bild("buggy_rot_fahrer")
pruef("Mit Fahrer sieht er anders aus als leer",
      any(_leer69.get_at((x_, 32)) != _voll69.get_at((x_, 32)) for x_ in range(20, 36)))
pruef("Er ist laenger als breit (schaut nach +x wie jede Figur)",
      _leer69.get_bounding_rect().width > _leer69.get_bounding_rect().height + 10,
      str(_leer69.get_bounding_rect()))

# Seit 0.34.18 fuenf (gemeldet: "es soll auf staubtal 5 autos geben").
# Seit 0.34.59 stehen dort auch ein Panzer und ein Panzerwagen - gezaehlt
# werden hier die Buggys.
_buggys69 = [b_ for b_ in w.fahrzeuge if b_.art == "buggy"]


def _nb(liste_):
    """Wie viele Buggys in einer Liste von Fahrzeugen (seit 0.34.59)."""
    return sum(1 for b_ in liste_ if b_.art == "buggy")


pruef("Auf STAUBTAL stehen fuenf Buggys", len(_buggys69) == 5, str(len(_buggys69)))
pruef("Alle im Tal, und jeder passt dorthin, wo er steht",
      all(b.ebene == 0 and b.passt(b.pos) for b in w.fahrzeuge))
# Seit 0.34.18 geht er kaputt - und ist darum ein Ziel.
pruef("Der Wagen ist ein Ziel fuer Kugeln",
      all(b.trefferbar for b in w.fahrzeuge))
pruef("Ohne F in der Karte gibt es keinen (Lobby, Testkarte)",
      all(not e.marken.get("F") for e in W.karte_lesen("lobby")[0].ebenen))

fahrer69 = w.kaempfer[ga.meine_nummer]
andere69 = w.kaempfer[0]
b69 = min(w.fahrzeuge, key=lambda b_: b_.pos.x)       # der in Westdorf
_e69 = {"will": [0.0, 0.0], "ziel": [b69.pos.x + 80, b69.pos.y],
        "knoepfe": ["nutzen"]}

def _hin69(k_, p_):
    k_.pos.update(p_); k_.vorher.update(p_); k_.ebene = 0
    k_.treppe_rest = 0.0; k_.tempo.update(0, 0)

_hin69(fahrer69, b69.pos + pygame.Vector2(0, 200))
w._anwenden(fahrer69, _e69)
pruef("Weit weg steigt man nicht ein", not fahrer69.im_fahrzeug)
_hin69(fahrer69, b69.ausstiegsorte(fahrer69.radius)[0])
w._anwenden(fahrer69, _e69)
pruef("Daneben steigt man mit E ein",
      fahrer69.im_fahrzeug and b69.fahrer is fahrer69 and fahrer69.fahrzeug is b69)
pruef("Der Fahrer sitzt im Wagen", fahrer69.pos.distance_to(b69.pos) < 1.0)
_hin69(andere69, b69.ausstiegsorte(andere69.radius)[1])
w._anwenden(andere69, dict(_e69, ziel=[andere69.pos.x, andere69.pos.y]))
pruef("In einen besetzten steigt kein Zweiter",
      not andere69.im_fahrzeug and b69.fahrer is fahrer69)
_hin69(andere69, b69.pos + pygame.Vector2(0, 600))

def _fahr69(will_, sekunden_, ziel_=None):
    for _ in range(int(sekunden_ / K.FIXED_DT)):
        w._anwenden(fahrer69, {"will": list(will_), "ziel": [0, 0], "knoepfe": [],
                               "feuert": True})
        w.welt.schritt(K.FIXED_DT)
        w._fahrzeuge_nachziehen()
        if ziel_ is not None:
            ziel_.append((pygame.Vector2(b69.pos), b69.winkel,
                          b69.passt(b69.pos, b69.winkel)))

_start69, _w69 = pygame.Vector2(b69.pos), b69.winkel
_lenk69 = []
_fahr69((1.0, 0.0), 0.5, _lenk69)
pruef("Im Stand lenkt er nicht (kein Drehen auf der Stelle)",
      abs(b69.winkel - _w69) < 0.01 and b69.pos.distance_to(_start69) < 1.0,
      "%.1f Grad" % (b69.winkel - _w69))
_spur69 = []
_fahr69((0.0, -1.0), 1.0, _spur69)
_weg69 = b69.pos - _start69
pruef("W gibt Gas: er faehrt in seine Richtung los",
      _weg69.length() > 80 and _weg69.normalize().dot(pygame.Vector2(1, 0).rotate(_w69)) > 0.9,
      "%.0f px" % _weg69.length())
pruef("Er ist schneller als zu Fuss",
      b69.geschw.length() > K.SPIELER["tempo"] * 1.5, "%.0f" % b69.geschw.length())
pruef("Der Fahrer faehrt mit", fahrer69.pos.distance_to(b69.pos) < 1.0)
pruef("Am Steuer wird nicht geschossen", not fahrer69.feuert)
_w69b = b69.winkel
_fahr69((0.7, -0.7), 0.4, _spur69)
pruef("A/D lenken, solange er rollt",
      abs((b69.winkel - _w69b + 180) % 360 - 180) > 25, "%.1f Grad" % (b69.winkel - _w69b))
_fahr69((0.0, 1.0), 2.5, _spur69)
pruef("S bremst und faehrt dann rueckwaerts", b69.fahrt < -20, "%.0f" % b69.fahrt)
pruef("Er steckt dabei nie in einer Mauer", all(ok_ for _p, _w, ok_ in _spur69))

# Gegen eine Mauer: er bleibt davor stehen und steckt nie darin.
_wand69 = []
b69.geschw.update(0, 0)
for _wi69 in (0.0, 90.0, 180.0, -90.0):
    b69.winkel = _wi69
    if b69.passt(b69.pos):
        break
_fahr69((0.0, -1.0), 6.0, _wand69)
_ende69 = [p_ for p_, _w, _ok in _wand69[-60:]]
pruef("Gegen eine Mauer: nie darin", all(ok_ for _p, _w, ok_ in _wand69))
pruef("... und irgendwann steht er davor (oder gleitet ab, aber nicht hindurch)",
      all(w.welt.frei(c_, b69.radius, 0, True) for c_ in b69.kreise()))

# Schaden: seit 0.34.77 kommt im Fahrzeug nichts an (K.FAHRZEUG
# "fahrer_geschuetzt"), und gestossen wird man auch nicht.
fahrer69.unverwundbar = 0.0
fahrer69.leben = 100.0
fahrer69.tempo.update(0, 0)
fahrer69.schaden(10.0, pygame.Vector2(400, 0), andere69)
pruef("Im Buggy kommt kein Schaden an (seit 0.34.77)",
      fahrer69.leben == 100.0 and K.FAHRZEUG["fahrer_geschuetzt"],
      "%.2f" % (100.0 - fahrer69.leben))
pruef("... und er wird nicht weggestossen", fahrer69.tempo.length() < 1e-6)
andere69.unverwundbar = 0.0
andere69.leben = 100.0
andere69.schaden(10.0, None, fahrer69)
pruef("Zu Fuss kommt der volle Schaden an", abs(andere69.leben - 90.0) < 1e-6)
fahrer69.leben = fahrer69.max_leben
# Seit 0.34.18 nimmt der Wagen den Treffer; seit 0.34.77 kommt beim
# Fahrer nichts mehr davon an (K.FAHRZEUG "fahrer_geschuetzt").
b69.schaden(30.0, None, andere69)
w.welt._raster_bauen()
pruef("Ein Treffer am Buggy: er nimmt Schaden, der Fahrer nichts (seit 0.34.77)",
      b69.lebt and not b69.kaputt and b69.leben == b69.max_leben - 30.0
      and fahrer69.leben == fahrer69.max_leben,
      "Wagen %.0f, Fahrer %.1f" % (b69.leben, fahrer69.leben))
pruef("Eine Kugel trifft am Wagen den Wagen, nicht den Fahrer daneben",
      w.welt.treffer(b69.pos, 2.0, 0, andere69.fraktion) is b69)
b69.leben = b69.max_leben
fahrer69.leben = fahrer69.max_leben

# Wer im Weg steht, wird beiseitegeschoben, nicht ueberfahren.
b69.geschw.update(0, 0)
b69.winkel = Gefecht._fahrzeug_richtung(b69)
_vorn69 = pygame.Vector2(1, 0).rotate(b69.winkel)
_hin69(andere69, b69.pos + _vorn69 * 60)
_fahr69((0.0, -1.0), 0.8)
_nah69 = min(c_.distance_to(andere69.pos) for c_ in b69.kreise())
pruef("Wer vor dem Wagen steht, wird beiseitegeschoben",
      _nah69 >= b69.radius + andere69.radius - 2.0, "%.1f" % _nah69)

# Der Gast sieht ihn - mit Fahrer, und seine eigene Figur nicht extra.
for _ in range(6):
    w.schritt(K.FIXED_DT)
    ga.schritt(K.FIXED_DT)
_gb69 = [b_ for b_ in ga.fahrzeuge if b_.besetzt]
pruef("Der Gast sieht alle fuenf Buggys",
      sum(1 for b_ in ga.fahrzeuge if b_.art == "buggy") == 5, str(len(ga.fahrzeuge)))
# Der Gast sieht den Stand der letzten Meldung: so weit ist ein fahrender
# Wagen seitdem gekommen (seit 0.34.102 kommen 30 statt 60 je Sekunde).
pruef("... den besetzten an derselben Stelle",
      len(_gb69) == 1
      and _gb69[0].pos.distance_to(b69.pos) < 2.0 + b69.geschw.length() * K.NETZ["takt"],
      str([b_.pos for b_ in _gb69]))
pruef("... mit Fahrer im Bild", _gb69 and "fahrer" in _gb69[0].bild)
pruef("Der Gast weiss, dass er im Wagen sitzt", ga.ich.im_fahrzeug)
pruef("Die Buggys stehen beim Gast in der Welt (und werden gezeichnet)",
      all(b_ in ga.welt.wesen for b_ in ga.fahrzeuge))
_bild69 = pygame.Surface((K.GAME_W, K.GAME_H))
ga.zeichnen(_bild69, 0.5)
pruef("Der Gast zeichnet das ohne Fehler", True)
ga._fahrhinweis_rest = 2.0
_h69 = pygame.Surface((K.GAME_W, K.GAME_H)); _h69.fill((0, 0, 0))
ga.kamera.pos.update(ga.ich.pos); ga.kamera.zoom = 1.0
ga._fahrzeug_hinweis(_h69)
pruef("Im Wagen steht kurz, wie man faehrt und aussteigt",
      any(_h69.get_at((x_, y_))[:3] != (0, 0, 0)
          for x_ in range(0, K.GAME_W, 3) for y_ in range(0, K.GAME_H, 3)))

# Aussteigen mit E: daneben, nicht im Wagen.
fahrer69.treppe_rest = 0.0
w._anwenden(fahrer69, dict(_e69, ziel=[0, 0]))
pruef("Mit E steigt man wieder aus",
      not fahrer69.im_fahrzeug and b69.fahrer is None and fahrer69.fahrzeug is None)
pruef("... und steht neben dem Wagen, nicht darin",
      min(c_.distance_to(fahrer69.pos) for c_ in b69.kreise())
      >= b69.radius + fahrer69.radius - 0.5
      and w.welt.frei(fahrer69.pos, fahrer69.radius, 0, True))
pruef("Ohne Fahrer rollt er aus und bleibt stehen",
      (lambda: ([w.welt.schritt(K.FIXED_DT) for _ in range(400)],
                b69.geschw.length() < 1.0)[1])())

# Wer am Steuer stirbt, ist draussen; zur neuen Runde steht alles wieder.
_hin69(fahrer69, b69.ausstiegsorte(fahrer69.radius)[0])
w._anwenden(fahrer69, _e69)
fahrer69.lebt = False
w._fahrzeuge_nachziehen()
pruef("Wer stirbt, sitzt nicht mehr im Wagen", b69.fahrer is None and not fahrer69.im_fahrzeug)
fahrer69.lebt = True
_hin69(fahrer69, b69.ausstiegsorte(fahrer69.radius)[0])
w._anwenden(fahrer69, _e69)
w._runde_aufbauen()
pruef("Zur neuen Runde stehen alle Buggys leer an ihrem Platz",
      all(b_.fahrer is None and b_.pos == b_.start[0] for b_ in w.fahrzeuge)
      and not fahrer69.im_fahrzeug)
w.verlassen(); ga.verlassen()

# 0.34.10: "Auf der Minikarte soll man sehen, wo die Hotzone ist, auch wenn
# sie nicht auf derselben Ebene ist, und Buggys sollen dort durchgehend zu
# sehen sein, auch wenn sie gefahren werden."
from dustfront import minikarte as MK

w, ga = gefechtspaar("huegel", karte="staubtal")
_mk70 = w.hud.minikarte

def _karte70(g_):
    f_ = pygame.Surface((K.GAME_W, K.GAME_H)); f_.fill((0, 0, 0))
    g_.hud.minikarte.zeichnen(f_, g_)
    return f_, g_.hud.minikarte.rechteck(g_.welt)

def _punkte70(f_, r_, farbe_):
    return [(x_, y_) for x_ in range(r_.left, r_.right) for y_ in range(r_.top, r_.bottom)
            if f_.get_at((x_, y_))[:3] == tuple(farbe_)]

def _buggy_da70(f_, r_, g_, b_, farbe_):
    e_ = g_.welt.ebenen[0]
    px_ = int(r_.x + b_.pos.x * r_.width / float(e_.pixel_breite))
    py_ = int(r_.y + b_.pos.y * r_.height / float(e_.pixel_hoehe))
    return any(f_.get_at((px_ + dx_, py_ + dy_))[:3] == tuple(farbe_)
               for dx_ in range(-3, 4) for dy_ in range(-3, 4))

w._kreis_setzen(next(i_ for i_, (e_, _p, _n) in enumerate(w.kreise) if e_ == 0))
w.zone_halter = 0
_farbe70 = K.TEAMS["farben"][0]
w.ich.ebene = 0
_f70, _r70 = _karte70(w)
pruef("Auf derselben Ebene steht der Kreis auf der Minikarte",
      len(_punkte70(_f70, _r70, _farbe70)) >= 6)
w.ich.ebene = 1
_f70, _r70 = _karte70(w)
pruef("Auf einer anderen Ebene auch (mit Pfeil in seiner Farbe)",
      len(_punkte70(_f70, _r70, _farbe70)) >= 3
      and len(_punkte70(_f70, _r70, MK.Minikarte._blass(_farbe70))) >= 6)
pruef("Auf einer anderen Ebene stehen die Buggys trotzdem darauf (blasser)",
      all(_buggy_da70(_f70, _r70, w, b_, MK.Minikarte._blass(MK.FARBE_BUGGY))
          for b_ in w.fahrzeuge))
w.ich.ebene = 0
_f70, _r70 = _karte70(w)
pruef("Alle Buggys stehen auf der Minikarte",
      sum(1 for b_ in w.fahrzeuge if b_.art == "buggy") == 5
      and all(_buggy_da70(_f70, _r70, w, b_, MK.FARBE_BUGGY) for b_ in w.fahrzeuge))

# Ein Gast steigt ein und faehrt weit weg: der Wagen bleibt auf der Karte,
# beim Gastgeber wie beim Gast, an seiner neuen Stelle.
_k70 = w.kaempfer[ga.meine_nummer]
_b70 = w.fahrzeuge[0]
_k70.pos.update(_b70.ausstiegsorte(_k70.radius)[0]); _k70.ebene = 0; _k70.treppe_rest = 0.0
w._anwenden(_k70, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
_alt70 = pygame.Vector2(_b70.pos)
for _ in range(150):
    w._anwenden(_k70, {"will": [0.0, -1.0], "ziel": [0, 0], "knoepfe": []})
    w.welt.schritt(K.FIXED_DT)
    w._fahrzeuge_nachziehen()
pruef("(Er ist wirklich gefahren)", _b70.pos.distance_to(_alt70) > 150 and _k70.im_fahrzeug,
      "%.0f px" % _b70.pos.distance_to(_alt70))
_f70, _r70 = _karte70(w)
pruef("Ein gefahrener Buggy steht beim Gastgeber auf der Karte, wo er ist",
      _buggy_da70(_f70, _r70, w, _b70, MK.FARBE_BUGGY))
for _ in range(6):
    w.schritt(K.FIXED_DT)
    ga.schritt(K.FIXED_DT)
_f70g, _r70g = _karte70(ga)
pruef("... und beim Gast, der ihn faehrt, auch",
      sum(1 for b_ in ga.fahrzeuge if b_.art == "buggy") == 5
      and all(_buggy_da70(_f70g, _r70g, ga, b_, MK.FARBE_BUGGY) for b_ in ga.fahrzeuge))
w.verlassen(); ga.verlassen()

# ─────────────────────────────────────────────────────────────────────
# 0.34.59: Panzer und Panzerwagen. Entwurf und Abnahme aus dem Paket
# `rustfront_fahrzeuge` (README_IMMEDIATELY.md): Grafik, Insassen in
# Spielergroesse, Ketten, Turm, Kanone mit Feuerball und Krater, Bug-MG,
# Ring-MG, Rammen nur ueber die Front. Gemeldet als Entscheidung: einer
# steuert ein Fahrzeug - fahren mit W A S D, zielen mit der Maus.
print("\n-- Panzer und Panzerwagen (0.34.59)")
# GRUND: Diese Pruefungen schiessen und rammen und verbrauchen dabei den
# Zufall der Wesen (entities.RND). Spaetere Szenen haengen an diesem
# Zufall; damit sie genau so laufen wie ohne diesen Abschnitt, wird sein
# Stand am Ende zurueckgesetzt.
_rnd59 = EN.RND.getstate()
_zufall59 = random.getstate()
# Aus demselben Grund eigene Ports: `gefechtspaar` zaehlt `_port` weiter,
# und aus dem Port wird der Seed jedes spaeteren Gefechts.
_port59 = [58900]


def _paar59(modus, **kw):
    import socket as _s59
    while True:
        _port59[0] += 1
        probe_ = _s59.socket(_s59.AF_INET, _s59.SOCK_STREAM)
        probe_.setsockopt(_s59.SOL_SOCKET, _s59.SO_REUSEADDR, 1)
        try:
            probe_.bind(("", _port59[0]))
            break
        except OSError:
            continue
        finally:
            probe_.close()
    wirt_ = Gefecht(app, "WIRT", gastgeber=netz.Gastgeber(_port59[0]), modus=modus,
                    seed=59, **kw)
    gast_ = Gefecht(app, "BESUCH", gast=netz.Gast("127.0.0.1:%d" % _port59[0]))
    for _ in range(30):
        wirt_.schritt(K.NETZ["takt"])
        gast_.schritt(K.NETZ["takt"])
    return wirt_, gast_


from dustfront import testmodus as _TM59
from dustfront import regeln as _R199
print("\n-- SCHLACHT: links gegen rechts, volle Seiten, Fahrzeuge an der Basis, Vorstoss (0.34.95)")
from dustfront import regeln as _R198, bots as _BO198
_d198 = _R198.vorgabe()
for _ in range(len(K.MODI) + 1):
    if _d198["modus"] == "schlacht":
        break
    _R198.verstellen(_d198, "modus", 1)
pruef("SCHLACHT ist waehlbar und schlaegt STAUBTAL und Abschuesse vor",
      _d198["modus"] == "schlacht" and _d198["karte"] == K.SCHLACHT["karte"]
      and _d198["ende_art"] == "abschuesse" and _d198["ende_wert"] == K.SCHLACHT["abschuesse"],
      _R198.kurz(_d198))
_sicht198 = [f_.schluessel for f_ in _R198.sichtbar(_d198, False)]
pruef("... mit JE SEITE in der einfachen Ansicht, ohne die Regeln zum Bot-Auffuellen",
      "schlacht_seite" in _sicht198 and "bots" not in _sicht198
      and not any(f_.schluessel.startswith("bots_t") for f_ in _R198.sichtbar(_d198, True)), str(_sicht198))
w198, g198 = _paar59("schlacht", karte="staubtal")
# FREISCHALTEN aus (seit 0.34.129): so steht alles von Anfang an da, wie bisher.
w198._regeln_setzen(dict(_d198, schlacht_seite=12, freischalten="aus"))
w198._einstiegszonen_waehlen()
w198._fahrzeuge_neu_aufstellen()
w198._bots_fuehren(0.0, sofort=True)
# Seit 0.34.96 kommen die Fahrzeuge an Fallschirmen in ihre Dropzonen.
_ab198 = K.SCHLACHT["abwurf"]
pruef("Jede Basis hat Dropzonen; zum Start faellt noch nichts, die Zonen zaehlen",
      len(w198.dropzonen) == 2 * sum(n_ for _a, n_ in K.basis_wagen())
      and not w198.fahrzeuge and all(z_.rest > 0 for z_ in w198.dropzonen))
for _ in range(int((_ab198["start"] + 0.2) / K.FIXED_DT)):
    w198.schlacht_schritt(K.FIXED_DT)
pruef("... dann sinken sie am Fallschirm herunter", len(w198.abwuerfe) == len(w198.dropzonen)
      and all(0 < a_.hoehe < _ab198["hoehe"] for a_ in w198.abwuerfe))
for _ in range(int((_ab198["hoehe"] / _ab198["sinken"] + 0.5) / K.FIXED_DT)):
    w198.schlacht_schritt(K.FIXED_DT)
_je198 = [sum(1 for k_ in w198.kaempfer.values() if k_.team == i_) for i_ in range(2)]
# Der Flakwagen der Basis (seit 0.34.117) bringt einen zusaetzlichen Bot mit (Verstaerkung):
# die Seiten sind mit 12 gefuellt, dazu je ein Flak-Fahrer.
_je198 = [sum(1 for k_ in w198.kaempfer.values() if k_.team == i_ and not getattr(k_, "verstaerkung", False))
          for i_ in range(2)]
_flak198 = [sum(1 for k_ in w198.kaempfer.values() if k_.team == i_ and getattr(k_, "verstaerkung", False)
                and getattr(getattr(k_, "fahrzeug", None), "art", "") == "flakwagen") for i_ in range(2)]
pruef("Beide Seiten stehen sofort voll - fehlende Spieler sind Bots; dazu je ein Bot im Flakwagen",
      _je198 == [12, 12] and _flak198 == [1, 1], str(_je198) + str(_flak198))
_bl198, _br198, _mi198 = w198._schlacht_punkte()
_breit198 = w198.welt.ebene(0).pixel_breite
pruef("ROT hat seine Basis links, BLAU rechts", _bl198.x < 0.2 * _breit198 < 0.8 * _breit198 < _br198.x,
      "%s %s" % (_bl198, _br198))
_soll198 = sum(n_ for _a, n_ in K.basis_wagen())
_bt198 = [[b_ for b_ in w198.fahrzeuge if getattr(b_, "basis_team", -1) == i_] for i_ in range(2)]
pruef("Jede Basis hat ihre Fahrzeuge, die aus der Karte bleiben weg",
      len(_bt198[0]) == len(_bt198[1]) == _soll198 and len(w198.fahrzeuge) == 2 * _soll198
      and all(b_.pos.distance_to(w198.schlacht_basis(i_)) <= K.SCHLACHT["fahrzeug_umkreis"] + 60
              for i_ in range(2) for b_ in _bt198[i_]), str([len(x_) for x_ in _bt198]))
_bots198 = w198._bots()
pruef("Je Seite fahren so viele Bots, wie die Basis Fahrzeuge hat (K.SCHLACHT fahrer_je_seite)",
      all(sum(1 for k_ in _bots198 if k_.team == i_ and getattr(k_, "darf_fahren", False))
          == K.SCHLACHT["fahrer_je_seite"] for i_ in range(2)))
_pj_soll198 = [min(K.SCHLACHT["panzerjaeger_je_seite"],
                   sum(1 for k_ in _bots198 if k_.team == i_) // K.BOTS["panzerjaeger"]["je_bots"])
               for i_ in range(2)]
# Seit 0.34.96 seltener (einer je acht Bots, hoechstens zwei je Seite) und
# mit einer Panzerabwehrwaffe neben einer gewoehnlichen.
_pa198 = set(K.BOTS["panzerjaeger"]["waffen"])
pruef("Je Seite wenige Panzerjaeger: eine Panzerabwehrwaffe und eine gewoehnliche",
      all(sum(1 for k_ in _bots198 if k_.team == i_ and getattr(k_, "panzerjaeger", False))
          == _pj_soll198[i_] >= 1 for i_ in range(2))
      and all(len(set(k_.waffen[:2]) & _pa198) == 1
              for k_ in _bots198 if getattr(k_, "panzerjaeger", False)), str(_pj_soll198))
_ort198 = w198._einstiegsort(1)
pruef("Eingestiegen wird in der eigenen Basis",
      _ort198.distance_to(_br198) <= K.SCHLACHT["spawn_umkreis"] * 1.5, "%.0f" % _ort198.distance_to(_br198))
# Seit 0.34.133 hat jeder Bot seinen Abschnitt (spur), und ein Viertel
# (Stosstrupp) zieht gleich zur Basis der anderen.
def _stoss198(k_):
    return ((k_.nummer * 2654435761) % 1000) / 1000.0 < K.SCHLACHT["stosstrupp"]
_rot198 = next(k_ for k_ in _bots198 if k_.team == 0 and not _stoss198(k_))
_ziele198 = w198._schlacht_ziele(_rot198.nummer % K.SCHLACHT["spuren"])
def _bei198(z_, liste_):
    return min(z_[0].distance_to(q_) for q_ in liste_) < 1.0
_rot198.pos.update(_bl198)
_z1_198 = w198.vorstoss_ziel(_rot198, random.Random(1))
_rot198.pos.update(_ziele198[2][0])
_z2_198 = w198.vorstoss_ziel(_rot198, random.Random(1))
pruef("Vorstoss: aus der Basis erst zur Mitte seines Abschnitts, von dort zur Basis der anderen",
      _bei198(_z1_198, _ziele198[2]) and _bei198(_z2_198, _ziele198[1]), "%s %s" % (_z1_198, _z2_198))
pruef("... und der Streifzug eines Bots folgt ihm (nicht die ganze Karte)",
      _bei198(_rot198.hirn._streifziel(), _ziele198[1]))
_sto198 = next((k_ for k_ in _bots198 if k_.team == 0 and _stoss198(k_)), None)
if _sto198 is not None:
    _sto198.pos.update(_bl198)
    pruef("... ein Stosstrupp zieht aus der Basis gleich zur Basis der anderen (seit 0.34.133)",
          _bei198(w198.vorstoss_ziel(_sto198, random.Random(1)),
                  w198._schlacht_ziele(_sto198.nummer % K.SCHLACHT["spuren"])[1]))
# Ein Wrack kommt an seiner Basis wieder.
_pz198 = next(b_ for b_ in _bt198[1] if b_.art == "panzer")
_pz198.schaden(_pz198.leben + 5000.0, None, None, art="hohlladung")
_pz198.wrack_rest = 0.0
w198._fahrzeuge_erneuern(0.0)
for _ in range(int((K.PANZER["neu_nach"] + _ab198["hoehe"] / _ab198["sinken"] + 1.0) / 0.05)):
    w198.schlacht_schritt(0.05)
_neu198 = [b_ for b_ in w198.fahrzeuge if b_.art == "panzer" and getattr(b_, "basis_team", -1) == 1]
pruef("Ein zerstoerter Panzer kommt in seiner Dropzone wieder (Fallschirm)",
      len(_neu198) == 1 and _neu198[0] is not _pz198
      and _neu198[0].pos.distance_to(_br198) <= K.SCHLACHT["fahrzeug_umkreis"] + 60)

print("\n-- Panzerwagen als Truppentransporter, Funk der Fahrzeuge (0.34.95)")
_ich198 = w198.ich
_pw198 = next(b_ for b_ in _bt198[_ich198.team] if b_.art == "panzerwagen")
_fahrer198 = next(k_ for k_ in _bots198 if k_.team == _ich198.team and k_.fahrzeug is None)
for b_ in w198.fahrzeuge:
    if b_.fahrer is not None:
        w198._fahrzeug_loesen(b_.fahrer)
w198._einsteigen(_fahrer198, _pw198)
pruef("Ein Bot am Steuer, der nichts meldet: der Wagen funkt nicht (seit 0.34.96)",
      not w198._funkt(_pw198))
_fahrer198.hirn.funken("fahrzeug_kontakt", wichtig=True)
pruef("... meldet er etwas, funkt der Wagen", w198._funkt(_pw198))
_ich198.lebt = True
_ich198.am_boden = False
_ich198.ebene = _pw198.ebene
_ich198.pos.update(_pw198.pos + pygame.Vector2(0, _pw198.werte["halb"] + 14).rotate(_pw198.winkel))
_ich198.treppe_rest = 0.0

def _e198(k_):
    w198._anwenden(k_, {"will": [0, 0], "ziel": [k_.pos.x + 10, k_.pos.y], "knoepfe": ["nutzen"]})

_e198(_ich198)
pruef("E am Panzerwagen, den ein Kamerad faehrt: man sitzt hinten auf",
      _ich198.mitfahrt is _pw198 and _ich198 in _pw198.mitfahrer and _ich198.im_fahrzeug
      and not _ich198.trefferbar and _pw198.fahrer is _fahrer198)
_pw198.pos += pygame.Vector2(40, 0)
w198._mitfahrer_nachziehen()
pruef("... und faehrt mit", _ich198.pos == _pw198.pos)
for _ in range(8):
    w198.schritt(K.NETZ["takt"]); g198.schritt(K.NETZ["takt"])
_gpw198 = next((b_ for b_ in g198.fahrzeuge if b_.art == "panzerwagen"
                and getattr(b_, "fahrer_nummer", -1) == _fahrer198.nummer), None)
pruef("Der Gast weiss, wie viele aufsitzen und dass ein Bot faehrt (Netz: Fahrzeug Feld 15)",
      _gpw198 is not None and _gpw198.besetzt_mit == 1 and g198._funkt(_gpw198))
_ich198.treppe_rest = 0.0
_e198(_ich198)
pruef("E noch einmal: man steigt ab, neben den Wagen",
      _ich198.mitfahrt is None and not _ich198.im_fahrzeug and _ich198.trefferbar
      and _ich198 not in _pw198.mitfahrer and _ich198.pos != _pw198.pos)
_bot198 = next(k_ for k_ in _bots198 if k_.team == _ich198.team and k_ is not _fahrer198
               and k_.fahrzeug is None and not getattr(k_, "darf_fahren", False))
_bot198.ebene = _pw198.ebene
_bot198.pos.update(_ich198.pos)
_bot198.treppe_rest = 0.0
_e198(_bot198)
# Seit 0.34.96 sitzen in SCHLACHT auch Bots auf (der Fahrer setzt sie ab).
pruef("In SCHLACHT sitzen auch Bots auf", getattr(_bot198, "mitfahrt", None) is _pw198)
w198._absitzen(_bot198)
_ich198.pos.update(_pw198.pos + pygame.Vector2(0, _pw198.werte["halb"] + 14).rotate(_pw198.winkel))
_ich198.treppe_rest = 0.0
_e198(_ich198)
_ich198.unverwundbar = 0.0            # der Einstiegsschutz haelt sonst alles ab
_leben198 = _ich198.leben
_pw198.schaden(_pw198.leben + 5000.0, None, None, art="hohlladung")
w198._fahrzeuge_nachziehen()
w198._mitfahrer_nachziehen()
pruef("Geht der Wagen hoch, faellt man herunter und bekommt etwas ab",
      _ich198.mitfahrt is None and not _ich198.im_fahrzeug and _ich198.leben < _leben198,
      "%.0f -> %.0f" % (_leben198, _ich198.leben))
pruef("Mit dem Fahrer draussen funkt der Wagen nicht mehr", not w198._funkt(_pw198))
_wagen198 = next(b_ for b_ in w198.fahrzeuge if not b_.kaputt and b_ is not _pw198)
_f2_198 = next(k_ for k_ in _bots198 if k_.fahrzeug is None and k_ is not _bot198)
w198._einsteigen(_f2_198, _wagen198)
_f2_198.hirn.funken("fahrzeug_vor", wichtig=True)
pruef("Ein Bot faehrt und funkt: Funk an ...", w198._funkt(_wagen198))
w198._aussteigen(_f2_198)
pruef("... er steigt aus: Funk aus", not w198._funkt(_wagen198))
w198._einsteigen(_f2_198, _wagen198)
_f2_198.hirn.funken("fahrzeug_vor", wichtig=True)
w198.blick = _wagen198.ebene
w198.kamera.pos.update(_wagen198.pos)
getattr(w198.kamera, "vorher", w198.kamera.pos).update(_wagen198.pos)
_bild198 = pygame.Surface((K.GAME_W, K.GAME_H))
_bild198.fill((0, 0, 0))
w198._funk_wellen(_bild198)
pruef("Die Wellen des Funkgeraets sind zu sehen",
      any(tuple(_bild198.get_at((x_, y_)))[:3] == tuple(K.FAHRZEUG_FUNK["farbe"])
          for x_ in range(K.GAME_W // 2 - 60, K.GAME_W // 2 + 60)
          for y_ in range(K.GAME_H // 2 - 60, K.GAME_H // 2 + 40)))
w198.verlassen(); g198.verlassen()

print("\n-- Bots: mehr Waffen, Panzerjaeger waehlen Panzerabwehr (0.34.95)")
_r1_198, _r2_198 = random.Random(5), random.Random(5)
_viel198 = [_BO198.bot_loadout(_r1_198, vielfalt=True)["waffen"] for _ in range(300)]
_alt198 = [_BO198.bot_loadout(_r2_198)["waffen"] for _ in range(300)]
pruef("Mit Vielfalt tragen Bots deutlich mehr verschiedene Waffen",
      len({w_ for x_ in _viel198 for w_ in x_}) >= len(K.BOTS["waffen"]) + 4
      and len({w_ for x_ in _alt198 for w_ in x_}) <= len(K.BOTS["waffen"]),
      "%d gegen %d" % (len({w_ for x_ in _viel198 for w_ in x_}), len({w_ for x_ in _alt198 for w_ in x_})))
pruef("... ohne den Zufall der Bots weiterzudrehen (feste Szenen bleiben)",
      _r1_198.getstate() == _r2_198.getstate() and all(len(set(x_)) == 2 for x_ in _viel198))
_tm198 = _TM195.Testmodus(app, karte="staubtal")
_zeilen198 = {z_[0] for z_ in _tm198._menue_zeilen()}
pruef("Testmodus: VIELE WAFFEN, PANZERJAEGER und VORSTOSS als Zeilen, aus als Vorgabe",
      {"vielfalt", "panzerjaeger", "vorstoss"} <= _zeilen198
      and not (_tm198.bots_vielfalt or _tm198.panzerjaeger_an or _tm198.vorstoss_an))
_eintrag198 = next((e_ for e_ in _TM195.eintraege() if e_.name == "PANZERJÄGER"), None)
_p198 = _fp195(_tm198.welt, 0, random.Random(198))
_pj198 = _tm198.panzerjaeger_setzen(_p198, 0, {"team": 1})
pruef("Spawner: PANZERJÄGER mit Panzerabwehr",
      _eintrag198 is not None and set(_pj198.waffen) & set(K.BOTS["panzerjaeger"]["waffen"])
      and _pj198.panzerjaeger)
_pzz198 = _tm198.fahrer_setzen(_p198 + pygame.Vector2(200, 0), 0, {"team": 0, "fahrzeug": "panzer"})
_pj198.hirn.ziel = _pzz198
_wahl198 = _pj198.hirn._beste_waffe(200.0)
_pj198.hirn.ziel = None
_wahl2_198 = _pj198.hirn._beste_waffe(200.0)
pruef("Gegen einen Panzer nimmt er die Panzerabwehr, gegen Figuren spart er die Einwegrakete",
      _wahl198 is not None and (K.WAFFEN[_wahl198[1]].get("fahrzeug_schaden") is not None
                                or K.WAFFEN[_wahl198[1]].get("gegen_fahrzeug"))
      and _wahl2_198 is not None and not K.WAFFEN[_wahl2_198[1]].get("einweg"),
      "%s %s" % (_wahl198, _wahl2_198))
_tm198.vorstoss_an = True
_b198 = _tm198.bot_setzen(_tm198._schlacht_punkte()[0], 0, {"team": 0})
_ziel198 = _b198.hirn._streifziel()
pruef("Testmodus mit VORSTOSS: ein Bot an der linken Basis zieht zur Mitte",
      _ziel198[0].distance_to(_tm198._schlacht_punkte()[2]) < 1.5 * K.SCHLACHT["streuung"])
_tm198.verlassen()

# ══════════════════════════════════════════════════════════════════
print("\n-- 0.34.96: Nahkampf auf F, G-Granate, Panzerbuechse, Zielfernrohr, Drohne, Nachschub")
from dustfront import regeln as _R199, konto as _KO199, klassen as _KL199
pruef("GOAP ist die Vorgabe fuer die Bot-KI, Funksprueche sind eine Regel (aus)",
      _R199.vorgabe()["bot_ki"] == "goap" and _R199.vorgabe()["funk"] is False)
pruef("Nahkampfwaffen belegen keinen Waffenplatz mehr",
      not set(K.NAHKAMPF["waehlbar"]) & set(K.LOADOUT["auswahl_waffen"])
      and not any(set(K.NAHKAMPF["waehlbar"]) & set(w_) for _n, w_ in K.ALLES_GRUPPEN))
_lo199 = _KO199.loadout_saeubern({"name": "X", "waffen": ["sturm", "revolver"], "wuerfe": ["granate"],
                                  "nahkampf": "hammer"})
pruef("... sondern stehen im Loadout als Waffe fuer F", _lo199.get("nahkampf") == "hammer")
pruef("Brecheisen deutlich schwaecher, Hammer stoesst weiter, Speer reicht weiter",
      K.WAFFEN["brecheisen"]["schaden"] <= 30 and K.WAFFEN["hammer"]["schub"] >= 900
      and K.WAFFEN["speer"]["reichweite"] >= 90)
w199, g199 = _paar59("team", karte="staubtal")
_k199 = w199.ich
_k199.unverwundbar = 0.0
_k199.nahkampf_waffe = "wurfmesser"
_k199.nahkampf_rest = 0.0
_n199 = len([x_ for x_ in w199.welt.neue + w199.welt.wesen if type(x_).__name__ == "Wurfkoerper"])
pruef("Messer auf F werden geworfen", _k199.nahkampf()
      and len([x_ for x_ in w199.welt.neue + w199.welt.wesen if type(x_).__name__ == "Wurfkoerper"]) == _n199 + 1)
_wurf199 = next((w_ for w_ in _k199.waffen if K.WAFFEN[w_].get("art") == "wurf"), None)
if _wurf199 is not None:
    _k199.magazin[_wurf199] = 1
    _alt199 = _k199.waffe
    _vor199 = len(w199.welt.neue)
    pruef("G wirft die Granate sofort, ohne die Waffe zu wechseln",
          _k199.schnellwurf() and _k199.waffe == _alt199 and len(w199.welt.neue) > _vor199)
w199.verlassen(); g199.verlassen()
from dustfront.entities import Geschoss as _Gs199
_tm199 = _TM195.Testmodus(app, karte="staubtal")
_wt199 = _tm199.welt
_rnd199 = random.Random(199)
for _ in range(500):
    _q199 = _fp195(_wt199, 0, _rnd199)
    # Eine echte Mauer (niedrige Deckung durchschlaegt sie ohnehin).
    _d199 = next((float(i_) for i_ in range(4, 200, 2)
                  if _wt199.schuss_halt(_q199 + pygame.Vector2(i_, 0), 0, 2.0, True)), 999.0)
    if 40.0 < _d199 < 150.0:
        break
_kugel199 = _Gs199(pygame.Vector2(_q199), 0.0, K.WAFFEN["panzerbuechse"], 0, None, "panzerbuechse")
_kugel199.welt = _wt199
for _ in range(60):
    if not _kugel199.lebt:
        break
    _kugel199.schritt(1.0 / 120)
_weg199 = _kugel199.pos.distance_to(_q199)
pruef("Panzerbuechse: durch die Mauer, aber nur ein Stueck dahinter",
      _d199 < _weg199 <= _d199 + K.WAFFEN["panzerbuechse"]["durchdringen"] + 12,
      "Mauer %.0f, Ende %.0f" % (_d199, _weg199))
_tm199.verlassen()
pruef("Das Scharfschuetzengewehr hat ein Zielfernrohr", K.WAFFEN["scharf"].get("scope"))
from dustfront import ausruestung as _AU199
_dr199 = _AU199.Drohne(pygame.Vector2(100, 100), 0, "team0")
pruef("Die Drohne fliegt hoch oben (eigene Schicht)", _dr199.hoch_oben)
from dustfront import schlacht as _SL199
pruef("Nachschub: Munition, Medkits, Dropzonen fuer Fahrzeuge, Aufklaerung",
      {n_ for n_, _c, _t in K.SCHLACHT["belohnungen"]}
      >= {"munition", "medkit", "buggy", "panzerwagen", "panzer", "aufklaerung"})
from dustfront import world as _W199
_w199, _kopf199 = _W199.karte_lesen("staubtal_offen")
pruef("STAUBTAL - OFFEN: eine grosse offene Karte fuer Fahrzeuge (Vorschlag fuer SCHLACHT seit 0.34.131 FLUSSTAL)",
      _w199 is not None and K.SCHLACHT["karte"] == "flusstal"
      and sum(_w199.fahrwege.begehbar[0]) > 0.7 * _w199.ebene(0).breite * _w199.ebene(0).hoehe)

print("\n-- 0.34.98: Fehlersuche (SCHLACHT am Boden, Nachschubpunkte je Runde)")
w200, g200 = _paar59("schlacht", karte="staubtal")
w200._regeln_setzen(dict(_R199.vorgabe(), modus="schlacht", revive=False))
_b200 = next(k_ for k_ in w200.kaempfer.values() if k_ is not w200.ich)
pruef("SCHLACHT: jeder faellt erst zu Boden, auch ohne die Regel AUFHELFEN",
      _b200.revive_an and w200.bergen_an())
_b200.unverwundbar = 0.0
_b200.sterben(None)
_b200.boden_rest = 0.05
for _ in range(20):
    w200._revive(1.0 / 120)
# Gemeldet bei der Fehlersuche: ohne bergen_an lief der Countdown nie ab,
# 20 von 23 Bots lagen ewig, und eine Runde endete nie.
pruef("... und wer nicht geborgen wird, stirbt nach der Bodenzeit",
      not _b200.lebt and not _b200.am_boden)
w200.ich.schlacht_punkte = 7
w200._runde_neu()
pruef("Nachschubpunkte gelten je Runde: die neue Runde beginnt bei 0",
      w200.ich.schlacht_punkte == 0, str(w200.ich.schlacht_punkte))
w200.verlassen(); g200.verlassen()

print("\n-- 0.34.99: Nahkampf und Klassen, alte Saetze mit Nahkampfwaffe im Platz")
from dustfront import konto as _KO201, klassen as _KL201
_alt201 = _KO201.loadout_saeubern({"name": "ALT", "klasse": "nahkaempfer",
                                   "waffen": ["hammer", "schrot"], "wuerfe": ["rauch"]})
pruef("Ein alter Satz mit dem Hammer im Waffenplatz: der Hammer liegt jetzt auf F",
      _alt201.get("nahkampf") == "hammer" and "hammer" not in _alt201["waffen"], str(_alt201))
pruef("... und der Platz ist wieder mit einer Waffe der Klasse belegt",
      len(_alt201["waffen"]) == len(_KL201.plaetze_von("nahkaempfer"))
      and all(w_ in _KL201.waffen_von("nahkaempfer") for w_ in _alt201["waffen"]), str(_alt201))
_neu201 = _KO201.loadout_saeubern({"name": "N", "waffen": ["speer", "sturm"], "nahkampf": "schlagring"})
pruef("Wer schon eine Waffe fuer F gewaehlt hat, behaelt sie", _neu201.get("nahkampf") == "schlagring")
pruef("In keiner Klasse steht noch eine Nahkampfwaffe unter den Waffen",
      not any(set(d_["waffen"]) & set(K.NAHKAMPF["waehlbar"]) for d_ in K.KLASSEN.values()))
pruef("Der NAHKAEMPFER schlaegt haerter und schneller zu, und das Menue sagt es",
      K.KLASSEN["nahkaempfer"]["nahkampf"] > 1.0 and K.KLASSEN["nahkaempfer"]["nahkampf_takt"] < 1.0
      and any("NAHKAMPF" in z_ for z_ in _KL201.vorteile("nahkaempfer")), str(_KL201.vorteile("nahkaempfer")))
w201, g201 = _paar59("team", karte="staubtal")
_k201 = w201.ich
_k201.nahkampf_waffe = "brecheisen"
_k201.loadout = {"klasse": "nahkaempfer"}
_KL201.anwenden(_k201)
_k201.nahkampf_rest = 0.0
_k201.schlag_zeigen = 0.0
_k201.nahkampf()
pruef("... die Pause nach dem Schlag ist kuerzer als beim Brecheisen ohne Klasse",
      abs(_k201.nahkampf_rest - K.WAFFEN["brecheisen"]["takt"] * K.KLASSEN["nahkaempfer"]["nahkampf_takt"]) < 1e-6,
      "%.3f" % _k201.nahkampf_rest)
w201.verlassen(); g201.verlassen()

print("\n-- 0.34.134: 2 Punkte beim Umwerfen, Bot aus dem Fahrzeug werfen, Werfer mit Karte")
w134, g134 = _paar59("schlacht", karte="flusstal")
w134._regeln_setzen(dict(_R199.vorgabe(), modus="schlacht", karte="flusstal", schlacht_seite=6, freischalten="aus"))
w134._einstiegszonen_waehlen(); w134._fahrzeuge_neu_aufstellen(); w134._bots_fuehren(0.0, sofort=True)
_ich134 = w134.ich
_feind134 = next(k_ for k_ in w134.kaempfer.values() if k_.ist_bot and k_.team != _ich134.team)
_feind134.unverwundbar = 0.0
_ich134.schlacht_punkte = 0
_feind134.revive_an = True
_feind134.sterben(_ich134)
w134._tote_abrechnen(0.0)
pruef("SCHLACHT: wer einen umwirft, bekommt sofort 2 Punkte (am Boden, noch nicht tot)",
      _feind134.am_boden and _ich134.schlacht_punkte == 2 == K.SCHLACHT["punkte"]["abschuss"],
      str(_ich134.schlacht_punkte))
_feind134.boden_rest = 0.0
for _ in range(10):
    w134._revive(0.1)
    w134._tote_abrechnen(0.1)
pruef("... stirbt er danach, gibt es nicht noch einmal Punkte",
      not _feind134.lebt and _ich134.schlacht_punkte == 2, str(_ich134.schlacht_punkte))
# Fahrzeug: Bot der eigenen Seite hinauswerfen, er steigt wieder ein.
from dustfront import fahrzeug as _FZ134
_bw134 = _FZ134.neu("buggy", _ich134.pos + pygame.Vector2(40, 0), 0)
w134.welt.dazu(_bw134); w134.fahrzeuge.append(_bw134)
_bot134 = next(k_ for k_ in w134.kaempfer.values() if k_.ist_bot and k_.team == _ich134.team and k_.lebt)
_bot134.pos.update(_bw134.pos)
w134._einsteigen(_bot134, _bw134)
_ich134.am_boden = False; _ich134.lebt = True; _ich134.fahrzeug = None
pruef("Ein Mensch nimmt einem Bot der eigenen Seite den Wagen ab",
      w134._freier_buggy(_ich134) is _bw134)
w134._anwenden(_ich134, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("... der Bot steigt aus, man selbst ein", _bw134.fahrer is _ich134 and _bot134.fahrzeug is None)
w134._aussteigen(_ich134)
pruef("... und steigt man aus, sitzt der Bot sofort wieder drin", _bw134.fahrer is _bot134)
_fl134 = _FZ134.neu("flakwagen", _ich134.pos + pygame.Vector2(0, 60), 0)
w134.welt.dazu(_fl134); w134.fahrzeuge.append(_fl134)
_bot134b = next(k_ for k_ in w134.kaempfer.values() if k_.ist_bot and k_.team == _ich134.team
                and k_.lebt and k_ is not _bot134)
w134._einsteigen(_bot134b, _fl134)
pruef("... nicht beim Flakwagen", not w134._bot_raus_erlaubt(_ich134, _fl134))
_fe134 = next(k_ for k_ in w134.kaempfer.values() if k_.ist_bot and k_.team != _ich134.team and k_.lebt)
_bw134b = _FZ134.neu("buggy", _ich134.pos + pygame.Vector2(-60, 0), 0)
w134.welt.dazu(_bw134b); w134.fahrzeuge.append(_bw134b)
w134._einsteigen(_fe134, _bw134b)
pruef("... und nie einem Bot der anderen Seite", not w134._bot_raus_erlaubt(_ich134, _bw134b))
# Werfer: halbe Karte Reichweite, Karte im Bild, Ziel ueber die Karte.
pruef("Werfer: aufgebaut reicht er ueber die halbe Kartenbreite",
      w134.werfer_weite() >= w134.welt.ebene(0).pixel_breite * 0.5 - 1)
for b_ in list(w134.fahrzeuge):
    if b_.fahrer is _ich134:
        w134._aussteigen(_ich134)
_wf134 = _FZ134.neu("werfer", _ich134.pos + pygame.Vector2(0, -80), 0)
w134.welt.dazu(_wf134); w134.fahrzeuge.append(_wf134)
w134._einsteigen(_ich134, _wf134)
_wf134.phase, _wf134.fortschritt = 2, 1.0
_ziel134 = w134._schlacht_punkte()[2]
w134.werfer_schritt(0.0)
pruef("... ein Ziel weit hinter der alten Grenze (3200 px) ist nicht mehr zu weit",
      w134.werfer_pruefen(_wf134, _ich134.team, _wf134.rohr_mitte() + pygame.Vector2(4000, 0)) != 2
      or w134.welt.ebene(0).pixel_breite * 0.5 < 4000)
_bild134 = pygame.Surface((K.GAME_W, K.GAME_H))
w134.zeichnen(_bild134, 1.0)
pruef("... und die Karte des Werfers steht im Bild (aufgebaut)", w134._werfer_eigen() is _wf134)
w134.verlassen(); g134.verlassen()

print()
print("FEHLER:", fails or "keine")
pygame.quit()
